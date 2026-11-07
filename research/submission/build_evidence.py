"""Derive navigation and diagnostics from saved v0.6 records, without model calls."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / 'experiments/120_fresh_v0.6'
sys.path.insert(0, str(STUDY))
from coprompt.scoring import score_output

POLICIES = ('direct', 'exhaustive', 'prompt_only', 'value_based')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_csv(path, rows, columns):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def collect():
    requests_path = STUDY / 'data/public/test_requests.jsonl'
    annotations_path = STUDY / 'data/private/test_annotations.jsonl'
    records_path = STUDY / 'runs/formal_v0.6.0_test/trajectories.jsonl'
    analysis_path = STUDY / 'outputs/fresh120_analysis/analysis.json'
    requests = {row['case_id']: row for row in read_rows(requests_path)}
    annotations = {row['case_id']: row for row in read_rows(annotations_path)}
    rows = read_rows(records_path)
    analysis = read_json(analysis_path)
    by_key = {(r['case_id'], r['system_id']): r for r in rows}
    expected = {(cid, p) for cid in requests for p in POLICIES}
    expected |= {(cid, 'importance_one') for cid in analysis['diagnostic']['case_ids']}
    if len(rows) != 260 or set(by_key) != expected or len(by_key) != len(rows):
        raise ValueError('Incomplete or duplicate main-test/diagnostic evidence')
    for row in rows:
        if score_output(row['domain'], row['output'], annotations[row['case_id']]) != row['score']:
            raise ValueError('Saved score differs from the unchanged scorer')
    main = [row for row in rows if row['system_id'] in POLICIES]
    fields, failed, table, candidate_ratings, output_rows = [], [], [], [], []
    for cid in sorted(requests):
        first = by_key[cid, 'direct']['extraction']
        if any(by_key[cid, p]['extraction'] != first for p in POLICIES):
            raise ValueError('Policies do not share identical extraction')
        for field, value in first['field_values'].items():
            known = annotations[cid]['field_annotations'][field]['initial_status'] == 'resolved'
            raw = first['raw_field_evidence'][field]
            accepted = value is not None
            reasons = [r['reason'] for r in first['grounding_rejections'] if r['field_id'] == field]
            fields.append({'case_id': cid, 'domain': requests[cid]['domain'], 'field': field,
                'annotation_known': known, 'raw_nonempty_evidence': bool(raw),
                'final_known': accepted, 'annotated_known_missed': known and not accepted,
                'annotated_unresolved_accepted': not known and accepted,
                'raw_evidence_ids': json.dumps(raw), 'rejection_reasons': json.dumps(reasons),
                'accepted_value': value or '',
                'asked_by': ','.join(p for p in POLICIES if any(e['field_id'] == field
                    for e in by_key[cid, p]['visible_exchanges']))})
    for row in rows:
        for constraint in row['score']['constraint_results']:
            if not constraint['passed']:
                failed.append({'case_id': row['case_id'], 'system_id': row['system_id'],
                    'domain': row['domain'], 'constraint_id': constraint['constraint_id'],
                    'check_type': constraint['check_type'],
                    'details': json.dumps(constraint['details'], ensure_ascii=False)})
        output_rows.append({'case_id': row['case_id'], 'system_id': row['system_id'],
            'domain': row['domain'], 'question_items': row['question_items'],
            'hard_constraint_score': row['score']['quality'],
            'final_format_failure': row['score']['format_failure'],
            'output_json': json.dumps(row['output'], ensure_ascii=False),
            'record_sha256': row['record_sha256']})
    for policy in POLICIES:
        group = [r for r in main if r['system_id'] == policy]
        saved = analysis['cohorts']['fresh_test']['statistics'][policy]
        quality = statistics.mean(r['score']['quality'] for r in group)
        if not math.isclose(quality, saved['mean_quality'], abs_tol=1e-12):
            raise ValueError('Aggregate quality differs from saved analysis')
        known_asks = sum(annotations[r['case_id']]['field_annotations'][e['field_id']]['initial_status'] == 'resolved'
                        for r in group for e in r['visible_exchanges'])
        table.append({'system_id': policy, 'cases': len(group), 'mean_quality': quality,
            'mean_questions': statistics.mean(r['question_items'] for r in group),
            'total_questions': sum(r['question_items'] for r in group),
            'full_pass_cases': sum(r['score']['quality'] == 1 for r in group),
            'format_failures': sum(r['score']['format_failure'] for r in group),
            'questions_on_annotated_known_fields': known_asks,
            'invalid_question_items': sum(r['invalid_question_items'] for r in group),
            'within_trace_repeated_field_questions': sum(len(r['visible_exchanges']) -
                len({e['field_id'] for e in r['visible_exchanges']}) for r in group),
            'constraint_revision_trajectories': sum(r['generation']['constraint_repair_attempted'] for r in group),
            'public_check_violation_trajectories': sum(bool(r['generation']['constraint_checks_final']) for r in group)})
    for row in main:
        if row['system_id'] != 'value_based':
            continue
        for index, decision in enumerate(row['decisions'], 1):
            for rating in decision.get('ratings', []):
                product = rating['importance'] * rating['uncertainty']
                candidate_ratings.append({'case_id': row['case_id'], 'decision_index': index,
                    'field_id': rating['field_id'], 'importance': rating['importance'],
                    'uncertainty': rating['uncertainty'], 'product': product,
                    'lambda': decision['lambda_value'], 'net_value': product - decision['lambda_value'],
                    'above_threshold': product > decision['lambda_value'], 'reason': rating['reason']})
    pairs = [(by_key[c, 'value_based'], by_key[c, 'exhaustive']) for c in sorted(requests)]
    same_counts = sum(a['question_items'] == b['question_items'] for a, b in pairs)
    same_order = sum([e['field_id'] for e in a['visible_exchanges']] ==
                     [e['field_id'] for e in b['visible_exchanges']] for a, b in pairs)
    field_summary = []
    for domain, field in sorted({(f['domain'], f['field']) for f in fields}):
        group = [f for f in fields if (f['domain'], f['field']) == (domain, field)]
        field_summary.append({'domain': domain, 'field': field, 'cases': len(group),
            'annotated_known': sum(f['annotation_known'] for f in group),
            'annotated_unresolved': sum(not f['annotation_known'] for f in group),
            'raw_empty_on_annotated_known': sum(f['annotation_known'] and not f['raw_nonempty_evidence'] for f in group),
            'known_missed_after_validation': sum(f['annotated_known_missed'] for f in group),
            'unresolved_accepted_after_validation': sum(f['annotated_unresolved_accepted'] for f in group)})
    summary = {'scope': 'Post-hoc offline description of supplied v0.6 test evidence; no new model runs or human review.',
        'case_count': len(requests), 'main_trajectories': len(main), 'diagnostic_trajectories': len(rows)-len(main),
        'policy_summary': table, 'field_summary': field_summary,
        'known_field_misses': sum(f['annotated_known_missed'] for f in fields),
        'known_misses_with_model_evidence_then_rejection': sum(f['annotated_known_missed'] and f['raw_nonempty_evidence'] for f in fields),
        'unresolved_field_acceptances': sum(f['annotated_unresolved_accepted'] for f in fields),
        'candidate_rating_observations': len(candidate_ratings),
        'candidate_products': dict(sorted(Counter(str(r['product']) for r in candidate_ratings).items())),
        'candidates_not_exceeding_threshold': sum(not r['above_threshold'] for r in candidate_ratings),
        'value_vs_exhaustive_equal_question_counts_cases': same_counts,
        'value_vs_exhaustive_identical_asked_field_order_cases': same_order,
        'failed_constraint_instances_main': dict(Counter(f['check_type'] for f in failed if f['system_id'] in POLICIES)),
        'paired_comparisons': analysis['cohorts']['fresh_test']['paired_comparisons'],
        'diagnostic': analysis['diagnostic'], 'costs': analysis['costs']['counts_and_costs']['fresh'],
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (requests_path, annotations_path, records_path, analysis_path)}}
    traces = [{'request': requests[r['case_id']], 'trajectory': r,
               'source_file': str(records_path.relative_to(ROOT)), 'source_line': i}
              for i, r in enumerate(rows, 1)]
    return summary, fields, failed, candidate_ratings, output_rows, traces


def export(out):
    summary, fields, failed, ratings, outputs, traces = collect()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'diagnostics.json', summary)
    write_json(out / 'test_traces.json', traces)
    for name, rows in [('policy_summary', summary['policy_summary']), ('field_summary', summary['field_summary']),
                       ('field_diagnostics', fields), ('failed_constraints', failed),
                       ('value_ratings', ratings), ('system_outputs', outputs)]:
        write_csv(out / (name + '.csv'), rows, list(rows[0]))
    template = (ROOT / 'submission/trace_template.html').read_text(encoding='utf-8')
    data = json.dumps(traces, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    (out / 'trace_viewer.html').write_text(template.replace('__TRACE_DATA__', data), encoding='utf-8')
    return summary
