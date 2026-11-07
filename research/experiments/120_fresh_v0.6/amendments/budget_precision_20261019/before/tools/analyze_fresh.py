"""Offline, fail-closed analysis and two masked reviewer packets for the fresh 120-case experiment.

Reads the original cumulative ledger without acquiring or creating its lock.
Never instantiates a provider, repairs run records, or replaces human ratings.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import random
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coprompt.formal import (cell_metadata, file_hash, load_dataset, planned_jobs,
                             select_lambda, verify_freeze, verify_manifest, verify_case_plan,
                             verify_isolated_caches, required_frozen_files, pilot_gate, STAGES, expected_ids)
from coprompt.runner import POLICIES, digest, strict_json
from coprompt.scoring import score_output

DOMAINS = ('constrained_writing', 'study_planning')
SEED = 20261013
RESAMPLES = 10000
FREEZE_NAME = 'data/formal_freeze_v0.6.0.json'
SELECTION_NAME = 'outputs/CoPrompt_validation_v0.6.0/lambda_selection.json'
OUT_NAME = 'outputs/fresh120_analysis'
RATING_FIELDS = ('usefulness_1_to_5', 'coherence_1_to_5', 'audience_fit_1_to_5',
                 'feasibility_1_to_5', 'unsupported_assumptions_count',
                 'unnecessary_questions_count', 'notes', 'rated_utc')


def read(path):
    return strict_json(Path(path).read_text(encoding='utf-8'))


def json_text(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def percentile(values, p):
    values = sorted(values)
    x = (len(values) - 1) * p
    i = int(x)
    return values[i] + (values[min(i + 1, len(values) - 1)] - values[i]) * (x - i)


def paired_interval(rows, left, right, *, resamples=RESAMPLES, seed=SEED):
    pairs = defaultdict(dict)
    for row in rows:
        if row['system_id'] not in (left, right):
            continue
        if row['system_id'] in pairs[row['case_id']]:
            raise ValueError('Duplicate comparison cell')
        pairs[row['case_id']][row['system_id']] = row
    if not pairs or any(set(p) != {left, right} for p in pairs.values()):
        raise ValueError('Every comparison needs complete matched cases')
    groups = defaultdict(list)
    families = set()
    for cid in sorted(pairs):
        a, b = pairs[cid][left], pairs[cid][right]
        if a['domain'] != b['domain'] or a['family_id'] != b['family_id']:
            raise ValueError('Unmatched comparison metadata')
        if a['family_id'] in families:
            raise ValueError('Repeated families require a different resampling unit')
        families.add(a['family_id'])
        groups[a['domain']].append((a['score']['quality'] - b['score']['quality'],
                                    a['question_items'] - b['question_items']))
    n = len(pairs)
    rng = random.Random(seed)
    boot = [[], []]
    ordered = [groups[d] for d in sorted(groups)]
    for _ in range(resamples):
        sampled = [rng.choice(g) for g in ordered for _ in g]
        for j in (0, 1):
            boot[j].append(sum(x[j] for x in sampled) / n)
    differences = [x for g in ordered for x in g]
    return {'left': left, 'right': right, 'matched_cases': n,
            'quality_difference': statistics.mean(x[0] for x in differences),
            'quality_95pct_interval': [percentile(boot[0], .025), percentile(boot[0], .975)],
            'question_difference': statistics.mean(x[1] for x in differences),
            'question_95pct_interval': [percentile(boot[1], .025), percentile(boot[1], .975)],
            'method': 'domain-stratified matched-case percentile bootstrap; one family per case',
            'resamples': resamples, 'seed': seed,
            'limitation': 'Case variation only, no independent model repeats or multiplicity correction; diagnostic subset contrasts are not independent evidence.'}


def balanced(ids, requests, n):
    if len(ids) != n or len(set(ids)) != n or not set(ids).issubset(requests):
        raise ValueError('Unexpected cohort case count or membership')
    if Counter(requests[c]['domain'] for c in ids) != {d: n // 2 for d in DOMAINS}:
        raise ValueError('Cohort is not balanced by domain')


def checked_stage(root, stage, freeze, selected):
    """Verify complete committed evidence, without calling mutating restore_rows."""
    requests, answers, annotations = load_dataset(root, stage)
    jobs = planned_jobs(stage, requests, selected, freeze['diagnostic_case_ids'])
    folder = root / f'runs/formal_v0.6.0_{stage}'
    manifest = read(folder / 'manifest.json')
    frozen_hash = file_hash(root / FREEZE_NAME)
    plan_hash = digest({'freeze': frozen_hash, 'stage': stage, 'jobs': jobs})
    verify_manifest(manifest, stage, jobs, frozen_hash, plan_hash,
                    freeze['diagnostic_case_ids'], freeze, selected)
    if manifest['status'] != 'completed' or manifest.get('pending_cell') is not None:
        raise ValueError(f'{stage}: incomplete runs must not be published as complete')
    path = folder / 'trajectories.jsonl'
    contents = path.read_bytes()
    lines = contents.splitlines(keepends=True)
    if any(not line.endswith(b'\n') or not line.strip() for line in lines):
        raise ValueError('Truncated or blank trajectory record')
    rows = [strict_json(line.decode('utf-8')) for line in lines]
    if (len(rows) != len(jobs) or manifest.get('completed_trajectories') != len(jobs)
            or manifest.get('trajectory_sha256') != file_hash(path)
            or len(manifest.get('row_hashes', [])) != len(jobs)):
        raise ValueError('Trajectory count/hash disagrees with complete manifest')
    for i, (row, job) in enumerate(zip(rows, jobs)):
        expected = cell_metadata(job, stage, frozen_hash, annotations)
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError('Unexpected trajectory order, case, variant, lambda or frozen version')
        if type(row.get('question_items')) is not int or not 0 <= row['question_items'] <= 3:
            raise ValueError('Invalid question count')
        payload = {k: v for k, v in row.items() if k != 'record_sha256'}
        if (row.get('record_sha256') != digest(payload)
                or manifest['row_hashes'][i] != row['record_sha256']):
            raise ValueError('Trajectory record hash changed')
        replay = score_output(row['domain'], row['output'], annotations[row['case_id']])
        if replay['quality'] is None or row.get('score') != replay:
            raise ValueError('Scoring replay mismatch')
    return {'rows': rows, 'manifest': manifest, 'requests': requests,
            'annotations': annotations, 'answers': answers, 'folder': folder}


def checked_selection(root, freeze, validation):
    saved = read(root / SELECTION_NAME)
    calculated = select_lambda(validation['rows'], validation['requests'])
    expected = dict(calculated, freeze_sha256=file_hash(root / FREEZE_NAME),
                    validation_run='runs/formal_v0.6.0_validation',
                    validation_trajectories_sha256=file_hash(validation['folder'] / 'trajectories.jsonl'))
    if set(saved) != set(expected) | {'selected_utc'} or any(saved.get(k) != v for k, v in expected.items()):
        raise ValueError('Lambda selection does not reproduce the complete 20-case validation')
    return saved


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Invalid monetary amount')
    return Decimal(str(value))


def checked_costs(root, project_root, stages):
    """Reconcile every parent-ledger log; classify fresh logs by actual path."""
    ledger_path = project_root / 'runs/authorized_pilot_budget.json'
    ledger_hash = file_hash(ledger_path)
    ledger = read(ledger_path)
    references = ledger.get('source_session_logs')
    if not isinstance(references, list) or any(not isinstance(s, str) for s in references):
        raise ValueError('Invalid cumulative ledger log references')
    paths = [(ledger_path.parent / s).resolve() for s in references]
    if len(paths) != len(set(paths)) or any(not p.is_relative_to(project_root) for p in paths):
        raise ValueError('Duplicate or out-of-project cumulative ledger logs')
    stage_paths = {}
    for stage, data in stages.items():
        stage_paths[stage] = {(root / s).resolve() for s in data['manifest']['session_logs']}
        if any(not p.is_relative_to(root / 'runs') for p in stage_paths[stage]):
            raise ValueError('Stage session log escapes fresh runs')
        if not stage_paths[stage].issubset(paths):
            raise ValueError('A formal stage log is missing from the real cumulative ledger')
    known_stage_paths = set().union(*stage_paths.values())
    if len(known_stage_paths) != sum(map(len, stage_paths.values())):
        raise ValueError('One session log cannot belong to multiple stages')
    fresh_paths = {p for p in paths if p.is_relative_to(root / 'runs')}
    if fresh_paths != known_stage_paths:
        raise ValueError('Unattributed fresh API session: reconcile its manifest first')
    totals = {k: {'attempts': 0, 'successes': 0, 'failures': 0,
                  'input_tokens_reported': 0, 'output_tokens_reported': 0,
                  'calls_missing_token_counts': 0, 'api_latency_seconds_reported': 0.0,
                  'calls_missing_latency': 0, 'accounted': Decimal(0),
                  'provider_reported': Decimal(0), 'unknown_reserve': Decimal(0)}
              for k in ('cumulative', 'fresh', 'prior', *stages)}
    hashes = {}
    for path in paths:
        before = file_hash(path)
        events = [strict_json(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
        numbers = set()
        groups = ['cumulative', 'fresh' if path in fresh_paths else 'prior']
        groups += [k for k, ps in stage_paths.items() if path in ps]
        for event in events:
            if event.get('event_type') != 'api_call':
                continue
            n = event.get('api_call_number')
            if type(n) is not int or n < 1 or n in numbers:
                raise ValueError('Invalid or duplicate API event number')
            numbers.add(n)
            accounted = number(event.get('accounted_call_cost_usd'))
            actual = event.get('provider_actual_cost_usd')
            if actual is not None and number(actual) != accounted:
                raise ValueError('Provider-reported and accounted event cost disagree')
            tokens = [event.get('input_tokens'), event.get('output_tokens')]
            for value in tokens:
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError('Invalid recorded token count')
            latency = event.get('latency_seconds')
            if latency is not None and (type(latency) not in (int, float)
                                       or not math.isfinite(latency) or latency < 0):
                raise ValueError('Invalid recorded API latency')
            for k in groups:
                totals[k]['attempts'] += 1
                totals[k]['successes'] += event.get('status') == 'success'
                totals[k]['failures'] += event.get('status') != 'success'
                totals[k]['input_tokens_reported'] += tokens[0] or 0
                totals[k]['output_tokens_reported'] += tokens[1] or 0
                totals[k]['calls_missing_token_counts'] += any(v is None for v in tokens)
                totals[k]['api_latency_seconds_reported'] += latency or 0
                totals[k]['calls_missing_latency'] += latency is None
                totals[k]['accounted'] += accounted
                totals[k]['provider_reported' if actual is not None else 'unknown_reserve'] += accounted
        if file_hash(path) != before:
            raise ValueError('Session log changed during analysis; retry after runs stop')
        hashes[str(path.relative_to(project_root))] = before
    spent = number(ledger.get('accounted_spend_usd'))
    cap = number(ledger.get('authorized_total_usd'))
    if spent != totals['cumulative']['accounted'] or spent > cap or file_hash(ledger_path) != ledger_hash:
        raise ValueError('Cumulative ledger is inconsistent or changed during analysis')
    return {'authorized_total_usd': float(cap), 'cumulative_accounted_usd': float(spent),
            'remaining_usd': float(cap - spent),
            'fresh_accounted_usd': float(totals['fresh']['accounted']),
            'prior_accounted_usd': float(totals['prior']['accounted']),
            'counts_and_costs': {k: {name + ('_usd' if isinstance(v, Decimal) else ''):
                                     float(v) if isinstance(v, Decimal) else v
                                     for name, v in values.items()} for k, values in totals.items()},
            'ledger_path': str(ledger_path), 'ledger_sha256': ledger_hash, 'session_sha256': hashes,
            'note': 'Unknown-cost failures retain conservative reserves. Tokens and latency sum only reported API events, not cache hits, full elapsed run time or missing usage. Costs are by execution stage, not a fair strategy cost ranking. Logical cache-replayed trajectories are not new billed calls or independent draws.'}


def statistics_for(rows, annotations, variants=POLICIES):
    result = {}
    for variant in variants:
        group = [r for r in rows if r['system_id'] == variant]
        if not group:
            raise ValueError('Missing strategy in analysis cohort')
        result[variant] = {'n': len(group),
            'mean_quality': statistics.mean(r['score']['quality'] for r in group),
            'mean_questions': statistics.mean(r['question_items'] for r in group),
            'total_questions': sum(r['question_items'] for r in group),
            'full_pass': sum(r['score']['quality'] == 1 for r in group),
            'format_failures': sum(r['score']['status'] != 'scored' for r in group),
            'noncritical_questions': sum(not annotations[r['case_id']]['field_annotations'].get(
                e['field_id'], {'critical': True})['critical'] for r in group
                for e in r['visible_exchanges'] if e['status'] != 'error'),
            'domains': {d: {'n': sum(r['domain'] == d for r in group),
                'mean_quality': statistics.mean(r['score']['quality'] for r in group if r['domain'] == d),
                'mean_questions': statistics.mean(r['question_items'] for r in group if r['domain'] == d)} for d in DOMAINS}}
    return result


def cache_evidence(root, project_root, stages):
    frozen_hash = file_hash(root / FREEZE_NAME)
    marker = root / 'runs/fresh_cache_scope.json'
    if not marker.is_file():
        raise ValueError('Completed fresh runs require their cache scope marker')
    verify_isolated_caches(root, frozen_hash)
    marker_hash = file_hash(marker)
    ids = set().union(*(set(expected_ids(split)) for split in ('design_all', 'validation', 'test')))
    raw_records = {}
    for path in sorted((root / 'runs/formal_raw_response_cache').glob('*.json')):
        cached = read(path)
        key = path.stem
        identity = cached.get('request_identity', {})
        if (len(key) != 64 or any(char not in '0123456789abcdef' for char in key)
                or cached.get('key') != key or not isinstance(cached.get('raw'), str)
                or digest(cached['raw']) != cached.get('response_sha256') or digest(identity) != key
                or identity.get('version') != 'fresh120-v0.6.0-first-raw-response-1'
                or cached.get('source_case_id') not in ids):
            raise ValueError('Raw-response cache is not valid evidence from this fresh experiment')
        raw_records[key] = cached
    summary = {}
    for stage, data in stages.items():
        path = data['folder'] / 'cache_reuse.jsonl'
        before = file_hash(path) if path.exists() else None
        events = [strict_json(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if before else []
        for event in events:
            if not isinstance(event, dict) or any(key.startswith('legacy_') for key in event):
                raise ValueError('Fresh cache events cannot contain an external import source')
        hits = [event for event in events if event.get('event_type') == 'raw_response_cache_hit']
        for event in hits:
            cached = raw_records.get(event.get('cache_key'))
            if (cached is None or event.get('case_id') not in data['requests']
                    or event.get('source_case_id') != cached['source_case_id']
                    or event.get('source_variant') != cached.get('source_variant')
                    or event.get('stage') != cached['request_identity'].get('stage')
                    or event.get('repair', False) != cached['request_identity'].get('repair', False)
                    or event.get('repair_kind') != cached['request_identity'].get('repair_kind')):
                raise ValueError('Fresh cache-hit event does not match its exact first-response record')
        if path.exists() and file_hash(path) != before:
            raise ValueError('Cache event log changed during analysis')
        summary[stage] = {'event_log_sha256': before, 'event_count': len(events),
                          'raw_response_hit_events': len(hits),
                          'raw_hit_events_by_stage': dict(Counter(event.get('stage') for event in hits))}
    if file_hash(marker) != marker_hash:
        raise ValueError('Fresh cache scope changed during analysis')
    return {'scope_marker_sha256': marker_hash, 'verified_raw_records': len(raw_records), 'stages': summary,
            'scope': 'Only this fresh experiment; exact first-response records and their hit references verified. Complete generation-pipeline hits bypass raw-event logging; cache reuse is not an independent model repeat or a new billed call.'}


def reviewer_documents(test, diagnostic, source_hash):
    """Separate masked packets and private mapping; no fabricated blind ratings."""
    rows = [r for r in test['rows'] if r['case_id'] in diagnostic]
    if len(rows) != 100:
        raise ValueError('Reviewer material requires exactly 20 cases x five variants')
    documents = {}
    mapping = {'source_evidence_sha256': source_hash, 'confidentiality':
               'Coordinator only. Contains strategy identities and must not accompany reviewer packets.',
               'reviewer_mappings': {}}
    for reviewer in (1, 2):
        order = list(rows)
        random.Random(SEED + reviewer).shuffle(order)
        records, private = [], []
        for i, row in enumerate(order, 1):
            item_id = f'R{reviewer}-{i:03d}'
            req = test['requests'][row['case_id']]
            records.append({'review_item_id': item_id, 'domain': row['domain'],
                'initial_request': req['initial_request'], 'reference_date': req.get('reference_date'),
                'user_control': req.get('user_control'),
                'visible_exchanges': [{k: e.get(k) for k in ('question', 'answer_text', 'status')}
                                      for e in row['visible_exchanges']],
                'output': deepcopy(row['output']),
                'unparsed_generation_text': (row.get('generation', {}).get('attempts') or [{}])[-1].get('raw')
                                            if row['output'] is None else None,
                'ratings': {key: None for key in RATING_FIELDS}})
            private.append({'review_item_id': item_id, 'case_id': row['case_id'],
                            'variant': row['system_id'], 'trajectory_record_sha256': row['record_sha256'],
                            'hard_quality': row['score']['quality']})
        documents[f'reviewer_{reviewer}_packet.json'] = {
            'source_evidence_sha256': source_hash, 'reviewer_slot': reviewer,
            'status': 'prepared_unrated_identity_masked_actual_blinding_not_confirmed',
            'instructions_en': ['Independently rate all 100 outputs without viewing the other reviewer packet or the private strategy mapping.',
                'Rate usefulness, coherence, audience fit, and feasibility from 1 (lowest) to 5 (highest). Enter nonnegative integer counts for unsupported factual assumptions and unnecessary clarification questions.',
                'Judge only the original user request, the displayed exchanges, and the final output. An optional question is not automatically unnecessary.',
                'For any item you cannot judge, leave the value null and explain in the notes. Do not treat a blank as zero.',
                'Strategy names and automatic quality scores are hidden. The coordinator must separately confirm actual blinding, prior exposure to the outputs, and the required authorship and cross-review exclusions.'],
            'reviewer_declaration': {'reviewer_name_or_id': None, 'assigned_utc': None,
                'assignment_timing': None,
                'source_outputs_seen_before_assignment': None,
                'authorship_and_crossreview_exclusion_confirmed_by_coordinator': None,
                'actual_blinding_confirmed': None, 'reviewed_independently': None, 'completed_utc': None},
            'records': records}
        mapping['reviewer_mappings'][str(reviewer)] = private
    documents['private/reviewer_policy_mapping.json'] = mapping
    return documents


def preserve_review_packets(out, documents):
    """Validate every existing packet first; never overwrite human-entered fields."""
    for name, fresh in documents.items():
        path = out / name
        if not path.exists():
            continue
        current = read(path)
        if name.startswith('private/'):
            if current != fresh:
                raise ValueError('Existing private review mapping differs; preserve and resolve explicitly')
            continue
        stripped = deepcopy(current)
        if not isinstance(stripped.get('records'), list):
            raise ValueError('Invalid existing reviewer packet')
        for row in stripped['records']:
            row['ratings'] = {key: None for key in RATING_FIELDS}
        stripped['reviewer_declaration'] = fresh['reviewer_declaration']
        if stripped != fresh:
            raise ValueError('Existing review material belongs to different source outputs; do not overwrite')
    for name, document in documents.items():
        path = out / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8') as handle:
                handle.write(json_text(document))


def analyze(root=ROOT, *, project_root=None, resamples=RESAMPLES):
    root = Path(root).resolve()
    project_root = Path(project_root).resolve() if project_root else root.parents[1]
    if not root.is_relative_to(project_root):
        raise ValueError('Fresh experiment must be inside its cumulative-budget project')
    freeze = read(root / FREEZE_NAME)
    verify_freeze(root, freeze)
    if not required_frozen_files().issubset(freeze['files']):
        raise ValueError('Analysis requires all frozen fresh datasets, settings, plan and method/runtime sources')
    plan = verify_case_plan(root, freeze)
    stages = {}
    for stage in STAGES[:-1]:
        stages[stage] = checked_stage(root, stage, freeze, None if stage == 'validation' else .25)
        if stage == 'pilot_a' and not pilot_gate(stages[stage]['rows'])['passed']:
            raise ValueError('Pilot A did not pass the fixed paired parsing/scoring gate')
    validation = stages['validation']
    selection = checked_selection(root, freeze, validation)
    test = checked_stage(root, 'test', freeze, selection['selected_lambda'])
    stages['test'] = test
    annotations = test['annotations']
    design_requests, _, design_annotations = load_dataset(root, 'design_all')
    design_rows = [row for stage in STAGES[:3] for row in stages[stage]['rows']]
    expected_design_cells = {(cid, policy) for cid in design_requests for policy in POLICIES}
    if (len(design_rows) != 160
            or {(row['case_id'], row['system_id']) for row in design_rows} != expected_design_cells):
        raise ValueError('Pilot A, pilot B and remaining design must form exactly 40 cases by four policies')
    all_ids = sorted(test['requests'])
    cohorts = {'fresh_test': all_ids}
    balanced(all_ids, test['requests'], 60)
    diagnostic = freeze['diagnostic_case_ids']
    balanced(diagnostic, test['requests'], 20)
    costs = checked_costs(root, project_root, stages)
    cache = cache_evidence(root, project_root, stages)
    evidence = {'status': 'complete_fresh_120_analysis', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'freeze_sha256': file_hash(root / FREEZE_NAME),
        'dataset_cases': {'design': 40, 'validation': 20, 'test': 60, 'total': 120},
        'completed_trajectories': {'pilot_a': 24, 'pilot_b': 24, 'remaining_design': 112,
                                   'all_design': 160, 'validation': 60, 'main_test': 240, 'diagnostic': 20, 'total': 480},
        'pilot_gate': pilot_gate(stages['pilot_a']['rows']),
        'design_statistics_descriptive_only': statistics_for(design_rows, design_annotations),
        'validation_selection': selection, 'cohorts': {}, 'costs': costs, 'cache_evidence': cache,
        'checks': {'freeze_verified': True, 'complete_committed_manifests_verified': True,
                   'all_scores_replayed': True, 'all_120_registered_cases_verified': True,
                   'one_case_per_family_all_120': True, 'pilot_gate_verified': True,
                   'parent_cumulative_ledger_reconciled': True},
        'source_evidence_sha256': {str(data['folder'].relative_to(root)) + '/' + name:
                                  file_hash(data['folder'] / name)
                                  for data in stages.values() for name in ('manifest.json', 'trajectories.jsonl')},
        'human_review_status': 'Two independently ordered, identity-masked packets for 100 outputs are prepared or preserved. No human ratings, reviewer eligibility, actual blinding or inter-rater agreement are certified by this analysis.',
        'limitations_en': ['This study uses 120 newly authored cases: 40 design cases for workflow checks, 20 validation cases for selecting lambda, and 60 new test cases for the primary comparison.',
            'The 20 diagnostic cases are a subset of the 60 test cases and are not additional independent replications.',
            'The 95% intervals reflect variation across this case distribution only. Each exact input retains one first model response; the intervals do not cover variability from new model samples. No multiple-comparison correction was applied.',
            'Automatic hard-constraint scores do not establish overall content quality or actual user utility. Do not report human ratings or inter-rater agreement until the two-person review is completed.',
            'Actual assignment timing, authorship and cross-review exclusions, reviewer independence, and blinding must be confirmed by people. Masked materials alone do not prove that reviewers have not previously seen the outputs.',
            'Isolated authoring of new cases does not mean that the coordinator was unaware of historical results. Report this limitation as stated in the registration documents.']}
    for name, ids in cohorts.items():
        rows = [r for r in test['rows'] if r['case_id'] in ids and r['system_id'] in POLICIES]
        evidence['cohorts'][name] = {'case_ids': ids, 'independent_case_count': len(ids),
            'statistics': statistics_for(rows, annotations),
            'paired_comparisons': [paired_interval(rows, 'value_based', p, resamples=resamples)
                                   for p in ('direct', 'exhaustive', 'prompt_only')]}
    diag_rows = [r for r in test['rows'] if r['case_id'] in diagnostic]
    evidence['diagnostic'] = {'case_ids': diagnostic, 'matched_cases': 20,
        'statistics_on_same_20': statistics_for(diag_rows, annotations, (*POLICIES, 'importance_one')),
        'paired_comparisons': [paired_interval(diag_rows, left, right, resamples=resamples)
                               for left, right in [('value_based', 'importance_one'), ('importance_one', 'exhaustive')]],
        'not_independent_repeats': True}
    source_hash = digest(evidence['source_evidence_sha256'])
    documents = reviewer_documents(test, diagnostic, source_hash)
    out = root / OUT_NAME
    out.mkdir(parents=True, exist_ok=True)
    preserve_review_packets(out, documents)
    (out / 'analysis.json').write_text(json_text(evidence), encoding='utf-8')
    lines = ['CoPrompt Fresh 120-Case Analysis', '',
             'Fresh cases: 40 design, 20 validation, and 60 test. The two phases of the 12-case pilot produced 48 trajectories; the other 28 design cases produced 112, for 160 design trajectories in total.',
             'All 60 validation, 240 formal test, and 20 diagnostic trajectories are complete. No previous case outputs or caches were imported.',
             f"Pilot gate: both direct and exhaustive outputs were parseable and scored successfully in {evidence['pilot_gate']['paired_scored_cases']}/12 cases.",
             f"All 20 validation cases selected lambda={selection['selected_lambda']:g}."]
    for name, title in [('fresh_test', '60 Fresh Test Cases')]:
        c = evidence['cohorts'][name]
        lines += ['', title]
        for p, s in c['statistics'].items():
            lines.append(f"{p}: mean hard-constraint score {s['mean_quality']:.4f}; mean questions {s['mean_questions']:.3f}; all constraints passed {s['full_pass']}/{s['n']}.")
        lines.append('The following differences are value_based minus the comparison strategy. A negative question difference means that value_based asked fewer questions.')
        for comparison in c['paired_comparisons']:
            lines.append(f"Versus {comparison['right']}: quality difference {comparison['quality_difference']:.4f}, 95% interval {comparison['quality_95pct_interval']}; question difference {comparison['question_difference']:.3f}, 95% interval {comparison['question_95pct_interval']}.")
    lines += ['', 'The 20-case diagnostic comparison uses the same cases and is not an additional independent replication.']
    for comparison in evidence['diagnostic']['paired_comparisons']:
        lines.append(f"{comparison['left']} minus {comparison['right']}: quality difference {comparison['quality_difference']:.4f}, 95% interval {comparison['quality_95pct_interval']}; question difference {comparison['question_difference']:.3f}, 95% interval {comparison['question_95pct_interval']}.")
    lines += ['',
              f"Fresh study accounted cost ${costs['fresh_accounted_usd']:.8f}; prior cost ${costs['prior_accounted_usd']:.8f}; cumulative cost ${costs['cumulative_accounted_usd']:.8f}; authorized cumulative limit ${costs['authorized_total_usd']:.8f}; remaining ${costs['remaining_usd']:.8f}.", 
              'Reserves for unknown costs of failed calls remain included. Cache hits are neither new billed calls nor independent model samples.', '',
              'Human review materials: two separately randomized packets with 100 outputs each. Strategy names and automatic quality scores are hidden. The private mapping is for the coordinator only and must not be given to reviewers.',
              'Ratings and reviewer declarations are initially blank. Re-running the analysis preserves human-entered fields and does not claim that two-person review or actual blinding has been completed or confirmed.', '', *evidence['limitations_en']]
    (out / 'results_summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--project-root', type=Path)
    args = parser.parse_args(argv)
    result = analyze(args.root, project_root=args.project_root)
    print(json.dumps({'status': result['status'], 'dataset_cases': result['dataset_cases'],
                      'output': str(args.root / OUT_NAME)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
