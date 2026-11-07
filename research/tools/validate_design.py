"""Offline schema, provenance and per-constraint feasibility audit; no API calls."""
from pathlib import Path
from datetime import date, timedelta
from collections import Counter
from copy import deepcopy
import argparse, hashlib, json, re, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from coprompt.scoring import score_output, count_words, normalize_text

def validate_contract(schema, value):
    if 'oneOf' in schema:
        count = 0
        for branch in schema['oneOf']:
            try:
                validate_contract(branch, value)
                count += 1
            except (AssertionError, ValueError, TypeError):
                pass
        assert count == 1, ('oneOf', count, value)
        return
    if 'const' in schema:
        assert value == schema['const']
    if 'enum' in schema:
        assert value in schema['enum']
    typ = schema.get('type')
    if isinstance(typ, list):
        assert any((t == 'null' and value is None or (t == 'string' and isinstance(value, str)) for t in typ))
        return
    if typ == 'object':
        assert isinstance(value, dict)
        assert all((k in value for k in schema.get('required', [])))
        assert len(value) >= schema.get('minProperties', 0) and len(value) <= schema.get('maxProperties', 10 ** 9)
        props = schema.get('properties', {})
        extra = schema.get('additionalProperties', True)
        for k, v in value.items():
            if k in props:
                validate_contract(props[k], v)
            elif extra is False:
                raise AssertionError(('extra key', k))
            elif isinstance(extra, dict):
                validate_contract(extra, v)
    elif typ == 'array':
        assert isinstance(value, list) and len(value) >= schema.get('minItems', 0) and (len(value) <= schema.get('maxItems', 10 ** 9))
        if schema.get('uniqueItems'):
            assert len({json.dumps(x, sort_keys=True) for x in value}) == len(value)
        for item in value:
            validate_contract(schema['items'], item)
    elif typ == 'string':
        assert isinstance(value, str) and len(value) >= schema.get('minLength', 0)
        if 'pattern' in schema:
            assert re.search(schema['pattern'], value)
        if schema.get('format') == 'date':
            assert date.fromisoformat(value).isoformat() == value
    elif typ == 'integer':
        assert isinstance(value, int) and (not isinstance(value, bool)) and (value >= schema.get('minimum', -10 ** 9))
    elif typ == 'boolean':
        assert isinstance(value, bool)


def load_rows(path):
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()]


def violation(output, rule):
    value = deepcopy(output)
    p, kind = rule['parameters'], rule['check_type']
    if kind == 'word_count':
        value['text'] = ' '.join(['word'] * (p['max_words'] + 1))
    elif kind == 'contains_all':
        value['text'] = 'This deliberately omits the required details.'
    elif kind == 'date_window':
        value['schedule'][0]['date'] = (date.fromisoformat(p['start_date']) - timedelta(days=1)).isoformat()
    elif kind == 'daily_minutes_cap':
        value['schedule'][0]['minutes'] = p['max_minutes'] + 1
    elif kind in ('topic_coverage', 'topic_minutes_min'):
        topic = p['topics'][0] if kind == 'topic_coverage' else p['topic']
        value['schedule'] = [s for s in value['schedule'] if normalize_text(s['topic']) != normalize_text(topic)]
    return value


def validate(prefix):
    paths = [ROOT/'data/public'/f'{prefix}_requests.jsonl',
             ROOT/'data/private'/f'{prefix}_answers.jsonl',
             ROOT/'data/private'/f'{prefix}_annotations.jsonl']
    datasets = [load_rows(p) for p in paths]
    ids = [[r['case_id'] for r in rows] for rows in datasets]
    assert ids[0] == ids[1] == ids[2] and len(set(ids[0])) == len(ids[0])
    schemas = {k:json.loads((ROOT/'data/schemas'/f'{k}.schema.json').read_text())
               for k in ('request','answer','annotation','output_constrained_writing','output_study_planning')}
    catalog = json.loads((ROOT/'data/public/field_catalog.json').read_text())['domains']
    registry = json.loads((ROOT/'data/family_registry.json').read_text())['registered_families']
    registered = {cid:r for r in registry for cid in r['case_ids']}
    assert len(registered) == sum(len(r['case_ids']) for r in registry)
    assert len({r['family_id'] for r in registry}) == len(registry)
    results, constraint_ids = [], set()
    for request, answer, ann in zip(*datasets):
        cid, domain = request['case_id'], request['domain']
        assert ann['domain'] == domain
        for key,value in (('request',request),('answer',answer),('annotation',ann),
                          ('output_'+domain,ann['feasible_example'])):
            validate_contract(schemas[key], value)
        field_order = catalog[domain]['field_order']
        fields = ann['field_annotations']
        assert set(field_order) == set(fields) == set(answer['answers'])
        unresolved = [f for f in field_order if fields[f]['initial_status']=='unresolved']
        assert unresolved == ann['metadata']['initial_unresolved_fields'] and len(unresolved)<=3
        family = registered[cid]
        assert family['family_id'] == ann['metadata']['family_id'] and family['domain'] == domain and family['split']==ann['metadata']['split']
        for field,reply in answer['answers'].items():
            if reply['status'] != 'available':
                assert not fields[field]['critical'] and field in unresolved
        scored_fields = set()
        checks=[]
        for rule in ann['constraints']:
            assert rule['constraint_id'] not in constraint_ids
            constraint_ids.add(rule['constraint_id'])
            field = rule['source_field'];scored_fields.add(field)
            assert field in fields and fields[field]['critical']
            if rule['source_stage']=='initial_request':
                assert fields[field]['initial_status']=='resolved'
                source=request['initial_request']
            else:
                assert fields[field]['initial_status']=='unresolved'
                assert answer['answers'][field]['status']=='available' and request['user_control']!='execute_now'
                source=answer['answers'][field]['text']
            p,k=rule['parameters'],rule['check_type']
            if k=='contains_all':assert all(normalize_text(s) in normalize_text(source) for s in p['literals'])
            elif k=='word_count':assert all(str(p[key]) in source for key in ('min_words','max_words'))
            elif k=='date_window':assert p['end_date'] in source and p['start_date'] in request['initial_request']
            elif k=='daily_minutes_cap':assert str(p['max_minutes']) in source
            elif k=='topic_coverage':
                assert all(normalize_text(s) in normalize_text(source) for s in p['topics'])
                if 'min_minutes_each' in p:assert str(p['min_minutes_each']) in source
            elif k=='topic_minutes_min':assert normalize_text(p['topic']) in normalize_text(source) and str(p['min_minutes']) in source
            bad=violation(ann['feasible_example'],rule)
            validate_contract(schemas['output_'+domain],bad)
            bad_score=score_output(domain,bad,ann)
            assert bad_score['status']=='scored'
            target=next(c for c in bad_score['constraint_results'] if c['constraint_id']==rule['constraint_id'])
            assert not target['passed']
            checks.append({'constraint_id':rule['constraint_id'],'provenance_checked':True,'targeted_violation_detected':True})
        assert scored_fields == {f for f,a in fields.items() if a['critical']}
        witness=score_output(domain,ann['feasible_example'],ann)
        assert witness['status']=='scored' and witness['quality']==1
        results.append({'case_id':cid,'domain':domain,'unresolved_fields':unresolved,
                        'witness_pass':True,'constraint_checks':checks,
                        'witness_word_count':count_words(ann['feasible_example']['text']) if domain=='constrained_writing' else None})
    report={'dataset':prefix,'status':'passed_offline_validation','api_calls':0,
            'case_count':len(results),'domain_counts':dict(Counter(r['domain'] for r in results)),
            'constraint_count':len(constraint_ids),'targeted_violations_detected':len(constraint_ids),
            'schema_validation':'all JSON-schema features used in these project contracts; standard-library validator',
            'file_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            'case_results':results,'limitation':'Feasible examples are authored data checks, never real model outputs.'}
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix',choices=['pilot','design_extension','design_all','validation','test'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=validate(args.prefix)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('case_results','file_hashes')},ensure_ascii=False))
