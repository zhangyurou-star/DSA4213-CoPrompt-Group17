"""Offline complete fixtures exercise publication gates and masked human packets."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from coprompt import formal
from coprompt.runner import digest
from coprompt.scoring import score_output

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fresh_analysis', ROOT / 'tools/analyze_fresh.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def lines(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


class CompleteFixture:
    def __init__(self, project):
        self.project = Path(project)
        self.root = self.project / 'experiments/120_fresh_v0.6'
        self.datasets = {}
        registered = []
        for split, count, prefix in [('design_all', 40, 'ND'), ('validation', 20, 'NV'), ('test', 60, 'NT')]:
            requests, answers, annotations = [], [], []
            for tag, domain in [('CW', 'constrained_writing'), ('SP', 'study_planning')]:
                for n in range(1, count // 2 + 1):
                    cid = f'{prefix}{tag}{n:02d}'
                    req = {'case_id': cid, 'domain': domain, 'initial_request': 'Fixture only: prepare a short response.',
                           'reference_date': '2026-10-19', 'user_control': 'default'}
                    rule = {'constraint_id': cid + '-C1', 'check_type': 'word_count' if tag == 'CW' else 'daily_minutes_cap',
                            'parameters': {'min_words': 2, 'max_words': 3} if tag == 'CW' else {'max_minutes': 30}}
                    annotation = {'case_id': cid, 'domain': domain, 'constraints': [rule], 'field_annotations': {},
                                  'metadata': {'family_id': 'fixture_' + cid, 'omission_type': 'complete'}}
                    requests.append(req); answers.append({'case_id': cid, 'domain': domain}); annotations.append(annotation)
                    registered.append({'case_id': cid, 'domain': domain, 'split': 'design' if split == 'design_all' else split,
                                           **annotation['metadata']})
            self.datasets[split] = (requests, answers, annotations)
        for split, triple in self.datasets.items():
            for group, folder, kind in zip(triple, ('public', 'private', 'private'), ('requests', 'answers', 'annotations')):
                lines(self.root / f'data/{folder}/{split}_{kind}.jsonl', group)
        self.diag = [f'NT{tag}{n:02d}' for tag in ('CW', 'SP') for n in range(1, 11)]
        plan = {'pilot_case_ids': list(formal.PILOT_IDS), 'diagnostic_case_ids': self.diag, 'cases': registered}
        write(self.root / 'data/case_plan.json', plan)
        write(self.root / 'data/allocation_plan.json', plan)
        write(self.root / 'config/openrouter.v0.6.formal.json', {'fixture': True})
        write(self.root / 'data/public/field_catalog.json', {'fixture': True})
        for domain in analysis.DOMAINS:
            write(self.root / f'data/schemas/output_{domain}.schema.json', {'fixture': True})
        for name in ('formal',) + formal.METHOD_MODULES:
            path = self.root / f'coprompt/{name}.py'; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / f'coprompt/{name}.py').read_bytes())
        for name in formal.FRESH_ENTRYPOINTS:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        files = [p for parent in ('data', 'config', 'coprompt', 'tools') for p in (self.root / parent).rglob('*') if p.is_file()]
        self.freeze = {'status': 'frozen_before_pilot_outputs', 'diagnostic_case_ids': self.diag,
                       'pilot_case_ids': list(formal.PILOT_IDS),
                       'files': {str(p.relative_to(self.root)): formal.file_hash(p) for p in files}}
        write(self.root / analysis.FREEZE_NAME, self.freeze)
        formal.verify_isolated_caches(self.root, formal.file_hash(self.root / analysis.FREEZE_NAME), initialize=True)
        self.stages = {}
        old_log = self.project / 'runs/old.jsonl'
        lines(old_log, [{'event_type': 'api_call', 'api_call_number': 1, 'status': 'success',
                         'accounted_call_cost_usd': .08, 'provider_actual_cost_usd': .08}])
        sessions = ['old.jsonl']
        for stage, selected in [('pilot_a', .25), ('pilot_b', .25), ('design', .25), ('validation', None), ('test', .5)]:
            requests, _, annotations = formal.load_dataset(self.root, stage)
            jobs = formal.planned_jobs(stage, requests, selected, self.diag)
            rows = []
            for job in jobs:
                cid, label = job[:2]
                domain = requests[cid]['domain']
                output = {'text': 'Two words'} if domain == 'constrained_writing' else {
                    'schedule': [{'date': '2026-10-20', 'topic': 'A', 'minutes': 20}], 'summary': 'Plan.'}
                row = dict(formal.cell_metadata(job, stage, formal.file_hash(self.root / analysis.FREEZE_NAME), annotations),
                           question_items=0 if label.startswith('value') else 1,
                           visible_exchanges=[], output=output, generation={})
                row['score'] = score_output(domain, output, annotations[cid])
                row['record_sha256'] = digest(row)
                rows.append(row)
            out = self.root / f'runs/formal_v0.6.0_{stage}'
            lines(out / 'trajectories.jsonl', rows)
            session = self.root / f'runs/formal_{stage}_fixture_session.jsonl'
            lines(session, [{'event_type': 'api_call', 'api_call_number': 1, 'status': 'success',
                             'accounted_call_cost_usd': .001, 'provider_actual_cost_usd': .001,
                             'input_tokens': 100, 'output_tokens': 20, 'latency_seconds': .5}])
            sessions.append(os.path.relpath(session, old_log.parent))
            manifest = {'manifest_version': 2, 'stage': stage, 'status': 'completed',
                'plan_hash': digest({'freeze': formal.file_hash(self.root / analysis.FREEZE_NAME), 'stage': stage, 'jobs': jobs}),
                'freeze_sha256': formal.file_hash(self.root / analysis.FREEZE_NAME), 'planned_trajectories': len(jobs),
                'completed_trajectories': len(jobs), 'case_ids': list(requests),
                'diagnostic_case_ids': self.diag if stage == 'test' else [], 'selected_lambda': selected,
                'source_files': self.freeze['files'], 'session_logs': [str(session.relative_to(self.root))],
                'row_hashes': [r['record_sha256'] for r in rows], 'trajectory_sha256': formal.file_hash(out / 'trajectories.jsonl'),
                'pending_cell': None}
            write(out / 'manifest.json', manifest)
            self.stages[stage] = {'rows': rows, 'manifest': manifest, 'out': out}
        validation = self.stages['validation']
        selection = formal.select_lambda(validation['rows'], formal.load_dataset(self.root, 'validation')[0])
        selection.update(freeze_sha256=formal.file_hash(self.root / analysis.FREEZE_NAME),
                         validation_run='runs/formal_v0.6.0_validation',
                         validation_trajectories_sha256=formal.file_hash(validation['out'] / 'trajectories.jsonl'),
                         selected_utc='fixture')
        write(self.root / analysis.SELECTION_NAME, selection)
        self.ledger = self.project / 'runs/authorized_pilot_budget.json'
        write(self.ledger, {'authorized_total_usd': .25, 'accounted_spend_usd': .085, 'source_session_logs': sessions})

    def recommit_test_rows(self, name='test'):
        stage = self.stages[name]
        for row in stage['rows']:
            row['record_sha256'] = digest({k: v for k, v in row.items() if k != 'record_sha256'})
        lines(stage['out'] / 'trajectories.jsonl', stage['rows'])
        stage['manifest'].update(row_hashes=[r['record_sha256'] for r in stage['rows']],
                                 completed_trajectories=len(stage['rows']),
                                 trajectory_sha256=formal.file_hash(stage['out'] / 'trajectories.jsonl'))
        write(stage['out'] / 'manifest.json', stage['manifest'])


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.fx = CompleteFixture(self.tmp.name)

    def run_analysis(self):
        return analysis.analyze(self.fx.root, project_root=self.fx.project, resamples=40)

    def test_complete_counts_cohorts_diagnostic_costs_and_no_fabricated_ratings(self):
        result = self.run_analysis()
        self.assertEqual(result['dataset_cases']['total'], 120)
        self.assertEqual(set(result['cohorts']), {'fresh_test'})
        self.assertEqual(result['cohorts']['fresh_test']['independent_case_count'], 60)
        self.assertEqual(result['completed_trajectories']['all_design'], 160)
        self.assertEqual(result['completed_trajectories']['total'], 480)
        self.assertEqual(result['diagnostic']['matched_cases'], 20)
        self.assertEqual(result['costs']['fresh_accounted_usd'], .005)
        self.assertEqual(result['costs']['prior_accounted_usd'], .08)
        self.assertEqual(result['costs']['cumulative_accounted_usd'], .085)
        costs = result['costs']['counts_and_costs']['fresh']
        self.assertEqual(costs['input_tokens_reported'], 500)
        self.assertEqual(costs['output_tokens_reported'], 100)
        self.assertEqual(costs['api_latency_seconds_reported'], 2.5)
        self.assertEqual(costs['failures'], 0)
        self.assertEqual(result['costs']['counts_and_costs']['prior']['calls_missing_token_counts'], 1)
        out = self.fx.root / analysis.OUT_NAME
        mapping = analysis.read(out / 'private/reviewer_policy_mapping.json')
        orders = []
        for reviewer in (1, 2):
            packet = analysis.read(out / f'reviewer_{reviewer}_packet.json')
            self.assertEqual(len(packet['records']), 100)
            self.assertIsNone(packet['reviewer_declaration']['actual_blinding_confirmed'])
            for record in packet['records']:
                self.assertNotIn('variant', record); self.assertNotIn('hard_quality', record)
                self.assertNotIn('case_id', record); self.assertNotIn('score', record)
                self.assertTrue(all(v is None for v in record['ratings'].values()))
            orders.append([(r['case_id'], r['variant']) for r in mapping['reviewer_mappings'][str(reviewer)]])
        self.assertNotEqual(orders[0], orders[1]); self.assertEqual(set(orders[0]), set(orders[1]))

    def test_incomplete_stage_never_publishes_analysis(self):
        self.fx.stages['test']['rows'].pop(); self.fx.recommit_test_rows()
        with self.assertRaises(ValueError): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_score_mismatch_detected_even_with_consistent_new_record_hashes(self):
        row = self.fx.stages['test']['rows'][0]
        row['output'] = {'text': 'Only'}
        self.fx.recommit_test_rows()
        with self.assertRaisesRegex(ValueError, 'Scoring replay'): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_wrong_lambda_does_not_pass_reanchored_hashes(self):
        self.fx.stages['test']['rows'][0]['lambda_value'] = .25
        self.fx.recommit_test_rows()
        with self.assertRaisesRegex(ValueError, 'Unexpected trajectory'): self.run_analysis()

    def test_parent_ledger_mismatch_fails_without_writing_results(self):
        ledger = analysis.read(self.fx.ledger); ledger['accounted_spend_usd'] = .082
        write(self.fx.ledger, ledger)
        with self.assertRaisesRegex(ValueError, 'ledger is inconsistent'): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_one_session_cannot_be_attributed_to_two_stages(self):
        test = self.fx.stages['test']
        test['manifest']['session_logs'].append(self.fx.stages['design']['manifest']['session_logs'][0])
        write(test['out'] / 'manifest.json', test['manifest'])
        with self.assertRaisesRegex(ValueError, 'multiple stages'): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_external_cache_import_event_prevents_publication(self):
        log = self.fx.stages['test']['out'] / 'cache_reuse.jsonl'
        lines(log, [{'event_type': 'raw_response_cache_hit', 'stage': 'decision',
                     'cache_key': 'a' * 64, 'legacy_source': '/not/the/recorded/cache',
                     'legacy_source_sha256': 'b' * 64}])
        with self.assertRaisesRegex(ValueError, 'external import source'): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_every_pilot_and_design_stage_is_required_for_publication(self):
        for name in ('pilot_a', 'pilot_b', 'design'):
            stage = self.fx.stages[name]
            stage['manifest']['status'] = 'interrupted'
            write(stage['out'] / 'manifest.json', stage['manifest'])
            with self.assertRaisesRegex(ValueError, 'incomplete runs'): self.run_analysis()
            stage['manifest']['status'] = 'completed'
            write(stage['out'] / 'manifest.json', stage['manifest'])
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_failed_pilot_gate_blocks_even_complete_replayed_evidence(self):
        annotations = formal.load_dataset(self.fx.root, 'pilot_a')[2]
        for row in self.fx.stages['pilot_a']['rows']:
            if row['case_id'] in formal.PILOT_IDS[:3]:
                row['output'] = None
                row['score'] = score_output(row['domain'], None, annotations[row['case_id']])
        self.fx.recommit_test_rows('pilot_a')
        with self.assertRaisesRegex(ValueError, 'Pilot A'): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_wrong_or_missing_cache_scope_blocks_complete_evidence(self):
        marker = self.fx.root / 'runs/fresh_cache_scope.json'
        saved = analysis.read(marker)
        write(marker, dict(saved, experiment='other-experiment'))
        with self.assertRaisesRegex(ValueError, 'another experiment'): self.run_analysis()
        marker.unlink()
        with self.assertRaisesRegex(ValueError, 'scope marker'): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())

    def test_existing_ratings_and_identity_declaration_are_preserved(self):
        self.run_analysis()
        packet_path = self.fx.root / analysis.OUT_NAME / 'reviewer_1_packet.json'
        packet = analysis.read(packet_path)
        packet['records'][0]['ratings']['usefulness_1_to_5'] = 4
        packet['reviewer_declaration']['reviewer_name_or_id'] = 'Fixture reviewer'
        write(packet_path, packet); before = packet_path.read_bytes()
        self.run_analysis()
        self.assertEqual(packet_path.read_bytes(), before)

    def test_altered_review_source_is_not_overwritten(self):
        self.run_analysis()
        path = self.fx.root / analysis.OUT_NAME / 'reviewer_2_packet.json'
        packet = analysis.read(path); packet['records'][0]['output'] = {'text': 'Altered'}
        write(path, packet); before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'different source outputs'): self.run_analysis()
        self.assertEqual(path.read_bytes(), before)

    def test_changed_freeze_input_fails_before_publication(self):
        path = self.fx.root / 'config/openrouter.v0.6.formal.json'
        write(path, {'fixture': 'changed'})
        with self.assertRaisesRegex(ValueError, 'Frozen source'): self.run_analysis()
        self.assertFalse((self.fx.root / analysis.OUT_NAME).exists())


class PairedTests(unittest.TestCase):
    def rows(self):
        return [{'case_id': f'C{i}', 'family_id': f'F{i}', 'domain': d, 'system_id': p,
                 'score': {'quality': 1.0 if p == 'a' else .5}, 'question_items': 0 if p == 'a' else 1}
                for i, d in enumerate(analysis.DOMAINS) for p in ('a', 'b')]

    def test_constant_pair_difference_has_exact_interval_and_stable_order(self):
        rows = self.rows()
        result = analysis.paired_interval(rows, 'a', 'b', resamples=100)
        self.assertEqual(result['quality_95pct_interval'], [.5, .5])
        self.assertEqual(result['question_95pct_interval'], [-1, -1])
        self.assertEqual(result, analysis.paired_interval(list(reversed(rows)), 'a', 'b', resamples=100))

    def test_missing_duplicate_and_repeated_family_are_not_independent_samples(self):
        rows = self.rows()
        with self.assertRaises(ValueError): analysis.paired_interval(rows[:-1], 'a', 'b')
        with self.assertRaises(ValueError): analysis.paired_interval(rows + [rows[0]], 'a', 'b')
        rows[2]['family_id'] = rows[3]['family_id'] = 'F0'
        with self.assertRaises(ValueError): analysis.paired_interval(rows, 'a', 'b')


if __name__ == '__main__':
    unittest.main()
