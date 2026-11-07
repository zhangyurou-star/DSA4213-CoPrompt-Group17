"""Fresh learning cases. Local authored witnesses only; no API or history access."""
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
from collections import Counter, defaultdict
from copy import deepcopy
import importlib.util
import json
import sys
import types
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[1]

def load_rule_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import only the approved scorer and validator definitions, never validate()/main().
scorer = load_rule_module('fresh_planning_scoring', PROJECT/'coprompt/scoring.py')
# Supply the approved scorer directly so importing validator does not read package helpers.
package = types.ModuleType('coprompt')
package.__path__ = []
sys.modules['coprompt'] = package
sys.modules['coprompt.scoring'] = scorer
validator = load_rule_module('fresh_planning_validator', PROJECT/'tools/validate_design.py')
validate_contract, violation = validator.validate_contract, validator.violation
normalize, score_output = scorer.normalize_text, scorer.score_output
plan = json.loads((BASE/'work/planning_family_plan.json').read_text())
allocation = json.loads((BASE/'data/allocation_plan.json').read_text())
allocated = {r['case_id']: r for r in allocation['cases'] if r['domain']=='study_planning'}
fields = json.loads((BASE/'data/public/field_catalog.json').read_text())['domains']['study_planning']['field_order']
schemas = {key:json.loads((BASE/'data/schemas'/f'{key}.schema.json').read_text())
           for key in ['request','answer','annotation','output_study_planning']}
exclusions = json.loads((BASE/'work/prior_family_exclusions.json').read_text())['entries']
START = '2027-02-01'
CONTEXTS = {
 'NDSP01': 'Before I join an apiary observation session, help me organize a short course in seasonal hive inspection.',
 'NDSP02': 'I am using a model railway to understand why trains are kept apart. Turn my signalling reading into a study schedule.',
 'NDSP03': 'I have volunteered to help a small collection team read its pest-monitoring records. Build me a preparation plan.',
 'NDSP04': 'A theatre induction includes a paper-based rigging quiz. Arrange my theory revision into manageable sessions.',
 'NDSP05': 'I want to read introductory Braille exercises more confidently. Lay out a compact learning timetable.',
 'NDSP06': 'I am attending a coffee tasting and want to recognize the vocabulary in the tasting notes. Plan my preparation.',
 'NDSP07': 'A waterworks visitor course gives me several process diagrams to learn. Divide that learning into study sessions.',
 'NDSP08': 'I will critique a pedestrian-street design in class. Please create a focused preparation schedule for the design concepts.',
 'NDSP09': 'I keep losing my place in origami diagrams. Give me a study sequence for recognizing the folds.',
 'NDSP10': 'Before a supervised bicycle workshop, I need to understand the drivetrain terminology. Map out my theory study.',
 'NDSP11': 'Our maritime-history club is trying a semaphore-reading exercise. I need a short practice plan.',
 'NDSP12': 'I am preparing to discuss which records an archive should keep. Build a revision timetable for records appraisal.',
 'NDSP13': 'A local-history transcription group has given me an unfamiliar handwritten page. Organize my palaeography preparation.',
 'NDSP14': 'I want to follow a leather hand-stitching demonstration without losing track of the terms. Arrange my learning sessions.',
 'NDSP15': 'Before a tea-ceremony demonstration, I would like to recognize the utensils and their handling conventions. Plan my study.',
 'NDSP16': 'I have to evaluate a workstation mock-up in a human-factors class. Set out a short study timetable.',
 'NDSP17': 'I am starting to copy Morse by ear and need a structured listening-practice schedule.',
 'NDSP18': 'An art-history seminar will compare illuminated manuscript pages. Please arrange my study of the workshop techniques.',
 'NDSP19': 'I want to work through a beginner Go problem booklet. Help me divide the life-and-death study into small sessions.',
 'NDSP20': 'I am taking a diagram-based course on dry-stone walls. Organize the construction theory into a study plan.',
 'NVSP01': 'For a knot-identification activity, I need to distinguish several rope knots from photographs. Make a learning timetable.',
 'NVSP02': 'I am preparing for a classroom discussion of edible mushroom cultivation. Schedule my reading of the production stages.',
 'NVSP03': 'My graphic-design assignment asks me to diagnose awkward lettering. Give me a study plan for type anatomy and spacing.',
 'NVSP04': 'I am learning to annotate recorded bat calls for a natural-history exercise. Arrange a compact study schedule.',
 'NVSP05': 'I have a seminar on comparing the language of anonymous documents. Plan my introductory authorship-analysis study.',
 'NVSP06': 'Battery diagrams in my chemistry workbook still confuse me. Put the cell-theory revision into a timetable.',
 'NVSP07': 'A drama workshop will use neutral masks. I would like a study-and-practice schedule for the preparatory concepts.',
 'NVSP08': 'I want to understand how social dancers share a crowded floor. Break the floorcraft learning into short sessions.',
 'NVSP09': 'I inherited a box of old coins and want to learn how cataloguers describe them. Create a study schedule for identification.',
 'NVSP10': 'I am learning a three-ball cascade from lesson clips. Make a compact practice timetable.',
 'NTSP01': 'I am reading an illustrated introduction to volcanoes. Arrange revision of the eruption processes for me.',
 'NTSP02': 'A geography lesson includes photographs of moving ice. Build a study timetable for glacier dynamics.',
 'NTSP03': 'I need to interpret groundwater diagrams in an environmental course. Organize the relevant study into sessions.',
 'NTSP04': 'I would like to identify the components of heraldic shields on a heritage walk. Plan my preparation.',
 'NTSP05': 'I am observing a canine scent-work class and want to understand its training terms. Set up a theory-study plan.',
 'NTSP06': 'Before a supervised CNC class, I need to read toolpath illustrations. Lay out my study of the milling concepts.',
 'NTSP07': 'I am practising consecutive interpreting with short recordings. Help me schedule the note-taking skills.',
 'NTSP08': 'I want to follow the stages shown in a traditional upholstery manual. Prepare a compact learning schedule.',
 'NTSP09': 'A horology club has shared diagrams of mechanical clock movements. Plan my study of how the parts relate.',
 'NTSP10': 'I have a tooth-identification worksheet for an anatomy class. Arrange a short revision schedule.',
 'NTSP11': 'I want to make sense of a beginner contract-bridge bidding lesson. Divide the revision into study sessions.',
 'NTSP12': 'A tabletop coordination exercise uses unfamiliar incident-management roles. Give me a study timetable for the concepts.',
 'NTSP13': 'I will discuss sample referee reports in a research-skills seminar. Structure my preparation for scientific peer review.',
 'NTSP14': 'I am studying an introductory insurance glossary for class. Make a revision schedule for the core concepts.',
 'NTSP15': 'I want to understand the assembly drawings in a stained-glass course. Schedule the theory learning before the demonstration.',
 'NTSP16': 'A craft group is comparing coiled baskets. I need a study plan for recognizing how they are constructed.',
 'NTSP17': 'I am reviewing lesson diagrams about laminated pastry. Arrange the preparation as a few study sessions.',
 'NTSP18': 'I want to understand the vocabulary used in a cheese-affinage lecture. Build a compact reading schedule.',
 'NTSP19': 'A perfume appreciation class asks me to describe a fragrance as it changes. Organize my study of its composition structure.',
 'NTSP20': 'I am trying to make my brush strokes more deliberate in calligraphy practice. Please schedule the mechanics I need to study.',
 'NTSP21': 'A dance-history course includes notation examples that I cannot yet read. Lay out a study timetable for the symbols.',
 'NTSP22': 'I am following a rugby officiating lesson and need to revise its decision categories. Make a study schedule.',
 'NTSP23': 'I am working through a sign-language lesson on using space to convey meaning. Plan short revision sessions.',
 'NTSP24': 'I need to understand a training workbook about retail stock control. Arrange the learning into a timetable.',
 'NTSP25': 'A ground-operations classroom exercise uses aircraft-marshalling diagrams. Organize my theory revision.',
 'NTSP26': 'I will help run a classroom usability study. Prepare a learning schedule for facilitating the sessions.',
 'NTSP27': 'I want to understand the steps described in an acoustic drum-tuning lesson. Create a short study-and-practice plan.',
 'NTSP28': 'A household-science class compares the chemistry of different laundry stains. Schedule my revision of those concepts.',
 'NTSP29': 'I am reviewing ice-hockey game diagrams before a tactics discussion. Build a compact study timetable.',
 'NTSP30': 'A repair-history workshop has diagrams of vintage fountain pens. Plan my study of their restoration concepts.',
}
# Distinct missing-field combinations are declared before any outcomes exist.
MISSING = {
 'NDSP02':['deadline'], 'NDSP10':['available_time'],
 'NDSP11':['topics','priorities'], 'NDSP12':['deadline','available_time','topics'],
 'NVSP03':['priorities'], 'NVSP04':['deadline','topics'],
 'NTSP07':['topics'], 'NTSP08':['available_time','priorities'],
 'NTSP09':['deadline','available_time'], 'NTSP10':['priorities'],
 'NTSP11':['deadline','topics','priorities'], 'NTSP12':['available_time','topics'],
 'NDSP03':['available_time','priorities'], 'NDSP13':['deadline','priorities'],
 'NDSP14':['topics','priorities'], 'NDSP15':['deadline','available_time','priorities'],
 'NVSP05':['deadline','topics','priorities'], 'NVSP06':['available_time','topics','priorities'],
 'NTSP13':['deadline','priorities'], 'NTSP14':['available_time','priorities'],
 'NTSP15':['topics','priorities'], 'NTSP16':['deadline','available_time','priorities'],
 'NTSP17':['deadline','topics','priorities'], 'NTSP18':['available_time','topics','priorities'],
}
DATE_FORMS = [
 'Use only dates from 2027-02-01 through {end}, including the final date.',
 'My study window closes on {end}; that date is still available.',
 'Finish all scheduled study no later than {end}, inclusive.',
 'The last usable study date is {end}, and sessions may fall on that day.',
 'Keep the timetable within the window ending {end}, with the end date included.',
 'I can still study on {end}, but no study should be scheduled after it.',
]
CAP_FORMS = [
 'The total of all sessions on any one date must not exceed {cap} minutes.',
 'I can spare at most {cap} minutes per day, counting every topic together.',
 'Keep each daily total at or below {cap} minutes across all study blocks.',
 'My daily study allowance is {cap} minutes maximum, not {cap} minutes per topic.',
 'There is a firm ceiling of {cap} study minutes on each date.',
 'Even if a day has several short sessions, their combined length must stay within {cap} minutes.',
]
TOPIC_FORMS = [
 'Cover these exact topic labels: {labels}. Give each one at least {minimum} minutes over the whole plan.',
 'The syllabus consists of {labels}; each named topic needs a minimum of {minimum} minutes in total.',
 'Include {labels}, using those topic names. Allocate at least {minimum} cumulative minutes to every topic.',
 'I need {minimum} minutes or more in total on each of {labels}. Those are the required topic labels.',
 'Required coverage is {labels}. The minimum study allocation for each topic is {minimum} minutes across all dates.',
 'Use the exact labels {labels} in the schedule, with at least {minimum} total minutes assigned to each.',
]
PRIORITY_FORMS = [
 'Give "{topic}" at least {minimum} minutes in total; this is a firm extra requirement.',
 'My priority is "{topic}": its cumulative study time must reach {minimum} minutes or more.',
 'I specifically require a minimum of {minimum} minutes altogether on "{topic}".',
 'One extra condition matters: allocate no less than {minimum} total minutes to "{topic}".',
]
SOFT_FORMS = [
 'If it fits, start with "{topic}". That is only a preference, with no extra time minimum.',
 'I have no preferred topic order and no additional minimum-time requirements.',
 'A little variety in the ordering would be nice, but it is optional and adds no minimum-time requirements.',
 'I would prefer to encounter "{topic}" early; treat that as a suggestion only, not a time requirement.',
]
ORDERS = [
 ['deadline','available_time','topics','priorities'],
 ['topics','deadline','priorities','available_time'],
 ['available_time','topics','deadline','priorities'],
 ['topics','priorities','available_time','deadline'],
 ['deadline','topics','available_time','priorities'],
 ['available_time','deadline','topics','priorities'],
]

def constraints_for(cid, values, missing):
    rules=[]
    def add(field,kind,params):
        rules.append({'constraint_id':f'{cid}_{len(rules)+1:02d}', 'check_type':kind,
          'parameters':params,'source_field':field,
          'source_stage':'field_answer' if field in missing else 'initial_request'})
    add('deadline','date_window',{'start_date':START,'end_date':values['end']})
    add('available_time','daily_minutes_cap',{'max_minutes':values['cap']})
    add('topics','topic_coverage',{'topics':values['topics'],'min_minutes_each':values['base']})
    if values['extra_topic_min']:
        add('topics','topic_minutes_min',{'topic':values['topics'][0],'min_minutes':values['extra_topic_min']})
    if values['priority_min']:
        add('priorities','topic_minutes_min',{'topic':values['topics'][-1],'min_minutes':values['priority_min']})
    return rules

def witness(values, index):
    totals={topic:values['base'] for topic in values['topics']}
    if values['extra_topic_min']: totals[values['topics'][0]]=values['extra_topic_min']
    if values['priority_min']: totals[values['topics'][-1]]=values['priority_min']
    # Fill successive days without exceeding the cap. A topic may span dates.
    order=list(values['topics'])
    if not values['priority_min'] and index % 4 == 3:
        order=[order[-1]]+order[:-1]
    entries=[];day=0;used=0
    for topic in order:
        remaining=totals[topic]
        while remaining:
            if used==values['cap']: day+=1;used=0
            part=min(remaining,values['cap']-used)
            entries.append({'date':(date.fromisoformat(START)+timedelta(days=day)).isoformat(),
                            'topic':topic,'minutes':part})
            remaining-=part;used+=part
    assert day < values['days']
    return {'schedule':entries,'summary':'Deterministic authored feasibility witness; satisfies the stated study requirements. This is not an experiment model response.'}

rows=[];value_by_id={}
for index,fam in enumerate(plan['families']):
    cid=fam['case_id']; alloc=allocated[cid]; kind=alloc['omission_type']
    assert fam['split']==alloc['split'] and fam['omission_type']==kind
    missing=MISSING.get(cid, [] if kind=='complete' else ['priorities'])
    missing=[f for f in fields if f in missing]
    hard_priority=(kind=='critical_omission' and 'priorities' in missing) or (kind=='complete' and index%2==0)
    # Some critical cases with other omissions also carry a resolved priority minimum.
    hard_priority=hard_priority or (kind=='critical_omission' and index%3==0)
    base=[10,15,20,25][index%4]
    extra=base+[10,15,20][index%3] if index%3==0 else 0
    pmin=base+[15,20,25][index%3] if hard_priority else 0
    days=3+(index%5)
    cap=[25,35,45,30,50,40,55,60,65,70][index%10]
    # Offline pre-freeze review found NTSP30 structurally duplicated NDSP20
    # after topic renaming. Distinguish its complete public timing contract;
    # keep its registered family, split, omission category and topic set.
    if cid == 'NTSP30':
        days, cap, base = 4, 45, 30
    required=len(fam['topics'])*base+max(0,extra-base)+max(0,pmin-base)
    # Numeric parameters are selected before authoring; a short window stays feasible.
    cap=max(cap, 5*((required+days*5-1)//(days*5)))
    assert 25<=cap<=70
    vals={'topics':fam['topics'],'base':base,'extra_topic_min':extra,'priority_min':pmin,
          'days':days,'cap':cap,'end':(date.fromisoformat(START)+timedelta(days=days-1)).isoformat()}
    labels=', '.join('"'+t+'"' for t in vals['topics'])
    texts={
      'deadline':DATE_FORMS[index%len(DATE_FORMS)].format(end=vals['end']),
      'available_time':CAP_FORMS[(index*5+1)%len(CAP_FORMS)].format(cap=cap),
      'topics':TOPIC_FORMS[(index*5+2)%len(TOPIC_FORMS)].format(labels=labels,minimum=base),
      'priorities':(PRIORITY_FORMS[index%4].format(topic=vals['topics'][-1],minimum=pmin)
                    if pmin else SOFT_FORMS[index%4].format(topic=vals['topics'][-1])),
    }
    if extra:
        texts['topics']+=f' Within that coverage, "{vals["topics"][0]}" needs at least {extra} total minutes.'
    initial=CONTEXTS[cid]+f' Start on {START}. '
    initial+=' '.join(texts[f] for f in ORDERS[index%len(ORDERS)] if f not in missing)
    if kind=='execute_now':
        initial+=' Please produce the schedule now without asking me follow-up questions.'
    req={'schema_version':'0.1.0','case_id':cid,'domain':'study_planning',
         'initial_request':initial,'reference_date':START,
         'user_control':'execute_now' if kind=='execute_now' else 'continue'}
    replies={f:{'status':'available','text':texts[f]} for f in fields}
    if kind=='unavailable_answer':
        replies['priorities']={'status':'unknown' if index%2==0 else 'declined',
          'text': ('I do not know what topic order would suit me, and I cannot supply a preference.' if index%2==0
                   else 'I would rather not specify a topic-order preference; please use your judgement.')}
    ans={'schema_version':'0.1.0','case_id':cid,'answers':replies}
    rules=constraints_for(cid,vals,missing)
    critical={r['source_field'] for r in rules}
    ann={'schema_version':'0.1.0','case_id':cid,'domain':'study_planning',
      'metadata':{'title_zh':fam['title_zh'],'split':alloc['split'],
        'is_pilot':cid in allocation['pilot_case_ids'],'synthetic':True,'family_id':fam['family_id'],
        'omission_type':kind,'initial_unresolved_fields':missing,
        'review_status':'fresh_authored_offline_schema_provenance_feasibility_checked'},
      'field_annotations':{f:{'initial_status':'unresolved' if f in missing else 'resolved',
                              'critical':f in critical} for f in fields},
      'constraints':rules,'feasible_example':witness(vals,index),
      'case_notes':f'Fresh family: {fam["subject"]}. The window is {days} days and the aggregate daily cap is {cap} minutes. '
        +'Topic labels and numeric minima are literal source requirements. '
        +('Priority has a hard cumulative topic minimum. ' if hard_priority else 'Priority is optional and has no scored time requirement. ')
        +'All unresolved critical values have available answers. Unavailable and execute-now cases have every hard requirement in the initial request. '
        +'The deterministic schedule is an authored data-feasibility check, never model output.'}
    rows.append([req,ans,ann]);value_by_id[cid]=vals

assert set(allocated)=={r[0]['case_id'] for r in rows}
assert len({f['family_id'] for f in plan['families']})==60
old_family_ids={r['family_id'] for r in exclusions}
old_topic_names={normalize(t) for r in exclusions for t in r['topics']}
new_topic_names=[normalize(t) for r in plan['families'] for t in r['topics']]
assert not ({f['family_id'] for f in plan['families']} & old_family_ids)
assert not (set(new_topic_names) & old_topic_names)
assert len(new_topic_names)==len(set(new_topic_names)), 'A topic label is reused between new families'
assert len({r[0]['initial_request'] for r in rows})==60

case_results=[];seen_rule_ids=set()
for req,ans,ann in rows:
    cid=req['case_id'];vals=value_by_id[cid];meta=ann['metadata'];kind=meta['omission_type']
    for name,value in [('request',req),('answer',ans),('annotation',ann),('output_study_planning',ann['feasible_example'])]:
        validate_contract(schemas[name],value)
    assert req['reference_date']==START and f'Start on {START}.' in req['initial_request']
    assert set(fields)==set(ans['answers'])==set(ann['field_annotations'])
    missing=[f for f in fields if ann['field_annotations'][f]['initial_status']=='unresolved']
    assert missing==meta['initial_unresolved_fields'] and len(missing)<=3
    critical={f for f in fields if ann['field_annotations'][f]['critical']}
    unresolved_hard=set(missing)&critical
    unresolved_soft=set(missing)-critical
    if kind=='complete': assert not missing
    else: assert 1<=len(missing)<=3
    if kind=='critical_omission': assert unresolved_hard and not unresolved_soft
    if kind=='critical_and_optional': assert unresolved_hard and unresolved_soft
    if kind=='optional_only': assert unresolved_soft and not unresolved_hard and all(ans['answers'][f]['status']=='available' for f in missing)
    if kind=='unavailable_answer':
        assert not unresolved_hard
        assert any(ans['answers'][f]['status'] in ['unknown','declined'] for f in missing)
    if kind=='execute_now':
        assert req['user_control']=='execute_now' and not unresolved_hard
    for f,reply in ans['answers'].items():
        if reply['status']!='available': assert f in unresolved_soft
    checks=[];scored_fields=set()
    for rule in ann['constraints']:
        rid=rule['constraint_id'];field=rule['source_field'];stage=rule['source_stage']
        p=rule['parameters'];k=rule['check_type']
        assert rid not in seen_rule_ids;seen_rule_ids.add(rid);scored_fields.add(field)
        assert field in critical
        if stage=='initial_request':
            assert field not in missing;source=req['initial_request']
        else:
            assert field in missing and ans['answers'][field]['status']=='available'
            assert req['user_control']!='execute_now';source=ans['answers'][field]['text']
        if k=='date_window': assert p['end_date'] in source and p['start_date'] in req['initial_request']
        elif k=='daily_minutes_cap': assert str(p['max_minutes']) in source
        elif k=='topic_coverage':
            assert all(normalize(t) in normalize(source) for t in p['topics'])
            assert str(p['min_minutes_each']) in source
        elif k=='topic_minutes_min': assert normalize(p['topic']) in normalize(source) and str(p['min_minutes']) in source
        mutant=violation(ann['feasible_example'],rule)
        validate_contract(schemas['output_study_planning'],mutant)
        score=score_output('study_planning',mutant,ann)
        assert score['status']=='scored'
        target=next(r for r in score['constraint_results'] if r['constraint_id']==rid)
        assert not target['passed']
        extras=[]
        if k=='daily_minutes_cap':
            mutant=deepcopy(ann['feasible_example'])
            first=mutant['schedule'][0]
            first['minutes']=p['max_minutes']//2+1
            mutant['schedule'].append(dict(first))
            assert all(s['minutes']<=p['max_minutes'] for s in mutant['schedule'])
            score=score_output('study_planning',mutant,ann)
            assert not next(r for r in score['constraint_results'] if r['constraint_id']==rid)['passed']
            extras.append('multiple_rows_aggregate_over_cap_detected')
        if k=='date_window':
            mutant=deepcopy(ann['feasible_example'])
            mutant['schedule'][0]['date']=(date.fromisoformat(p['end_date'])+timedelta(days=1)).isoformat()
            score=score_output('study_planning',mutant,ann)
            assert not next(r for r in score['constraint_results'] if r['constraint_id']==rid)['passed']
            extras.append('after_end_date_detected')
        if k=='topic_coverage':
            mutant=deepcopy(ann['feasible_example'])
            for session in mutant['schedule']:
                if normalize(session['topic'])==normalize(p['topics'][0]): session['topic']+=' review'
            score=score_output('study_planning',mutant,ann)
            assert not next(r for r in score['constraint_results'] if r['constraint_id']==rid)['passed']
            extras.append('substring_topic_label_does_not_count_as_exact_coverage')
        checks.append({'constraint_id':rid,'source_field':field,'source_stage':stage,
          'provenance_checked':True,'targeted_violation_detected':True,'additional_checks':extras})
    assert scored_fields==critical
    output=ann['feasible_example'];result=score_output('study_planning',output,ann)
    assert result['status']=='scored' and result['quality']==1
    daily=defaultdict(int);topic_totals=defaultdict(int)
    for session in output['schedule']:
        daily[session['date']]+=session['minutes'];topic_totals[session['topic']]+=session['minutes']
        assert START<=session['date']<=vals['end']
    minimums={t:vals['base'] for t in vals['topics']}
    if vals['extra_topic_min']: minimums[vals['topics'][0]]=vals['extra_topic_min']
    if vals['priority_min']: minimums[vals['topics'][-1]]=vals['priority_min']
    assert set(topic_totals)==set(vals['topics'])
    assert all(topic_totals[t]>=minimums[t] for t in minimums)
    assert all(n<=vals['cap'] for n in daily.values())
    assert sum(minimums.values())<=vals['days']*vals['cap']
    case_results.append({'case_id':cid,'split':meta['split'],'family_id':meta['family_id'],
      'omission_type':kind,'unresolved_fields':missing,'unresolved_critical_fields':[f for f in fields if f in unresolved_hard],
      'unresolved_optional_fields':[f for f in fields if f in unresolved_soft],
      'schema_valid':True,'source_valid':True,'classification_valid':True,'witness_pass':True,
      'window_days':vals['days'],'daily_cap':vals['cap'],'daily_totals':dict(sorted(daily.items())),
      'topic_totals':dict(topic_totals),'required_topic_minima':minimums,
      'minimum_required_minutes':sum(minimums.values()),'capacity_minutes':vals['days']*vals['cap'],
      'schedule_rows':len(output['schedule']),'constraint_checks':checks})

out=BASE/'work/planning_rows.json'
out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
report={'status':'passed_offline_validation','domain':'study_planning','authored_utc':datetime.now(timezone.utc).isoformat(),
 'family_plan_registered_utc':plan['registered_utc'],'api_calls':0,'historical_requests_read':0,'historical_outputs_read':0,
 'case_count':60,'split_counts':dict(Counter(r['split'] for r in case_results)),
 'omission_counts':dict(Counter(r['omission_type'] for r in case_results)),
 'unresolved_count_distribution':dict(Counter(len(r['unresolved_fields']) for r in case_results)),
 'constraint_count':len(seen_rule_ids),'targeted_violations_detected':len(seen_rule_ids),
 'schema_validation':'Original validate_contract definitions against all new study schemas; no main/validate execution.',
 'novelty_checks':{'unique_family_ids':60,'unique_topic_labels':len(new_topic_names),'prior_exact_topic_overlap':0,
   'prior_exact_family_overlap':0,'cross_split_exact_topic_overlap':0,
   'semantic_scope_review':'All 60 are distinct subtopics; related broad disciplines use different named concepts, tasks and scenarios.'},
 'limitation':'Authored deterministic feasibility witnesses are synthetic validation data, never experiment model responses.',
 'case_results':case_results}
(BASE/'work/planning_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['case_results']},ensure_ascii=False))
