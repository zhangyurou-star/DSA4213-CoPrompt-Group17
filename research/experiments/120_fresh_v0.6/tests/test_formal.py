"""Offline tests for frozen selection, durable resume, and paid-call reuse."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from decimal import Decimal
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from coprompt import formal
from coprompt.provider import ProviderError


def score_fixture(domain, output, annotation):
    return {'status': 'scored', 'quality': 1.0, 'format_failure': False,
            'constraint_results': [{'passed': True, 'score': 1}], 'errors': []}


class RawClient:
    def __init__(self, responses=None, config=None):
        self.config = config or {'provider': 'fixture', 'base_url': 'https://fixture.invalid',
                                 'model': 'fixture', 'temperature': 0, 'top_p': 1, 'seed': 1,
                                 'max_output_tokens': {'decision': 32, 'generation': 32},
                                 'provider_routing': {'only': ['fixture']}}
        self.routing = self.config.get('provider_routing')
        self.responses = list(responses or ['raw response'])
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((deepcopy(messages), kwargs))
        response = self.responses.pop(0)
        if isinstance(response, BaseException): raise response
        return response


class SelectionTests(unittest.TestCase):
    def rows(self, quality=(.5, .5, .5), questions=(1, 1, 1)):
        return [{'case_id': cid, 'system_id': f'value_lambda_{lam:g}', 'lambda_value': lam,
                 'question_items': questions[i], 'score': {'quality': quality[i]}}
                for cid in ['A', 'B'] for i, lam in enumerate((0, .25, .5))]

    def test_ties_choose_less_questions_then_larger_lambda(self):
        self.assertEqual(formal.select_lambda(self.rows(), ['A', 'B'])['selected_lambda'], .5)
        result = formal.select_lambda(self.rows(questions=(2, 1, 2)), ['A', 'B'])
        self.assertEqual(result['selected_lambda'], .25)

    def test_quality_wins_within_burden_cap(self):
        result = formal.select_lambda(self.rows(quality=(.9, .8, .7), questions=(2, 1, 0)), ['A', 'B'])
        self.assertEqual(result['selected_lambda'], 0)

    def test_no_eligible_fewest_questions_then_quality_then_lambda(self):
        result = formal.select_lambda(self.rows(quality=(.2, .9, .9), questions=(3, 3, 3)), ['A', 'B'])
        self.assertFalse(result['target_met'])
        self.assertEqual(result['selected_lambda'], .5)
        rows = self.rows(quality=(1, .1, .1), questions=(3, 3, 3))
        next(r for r in rows if r['case_id'] == 'A' and r['lambda_value'] == .25)['question_items'] = 2
        self.assertEqual(formal.select_lambda(rows, ['A', 'B'])['selected_lambda'], .25)

    def test_constraint_fractions_prevent_float_tie_break_error(self):
        rows = self.rows()
        for row in rows:
            row['score'] = {'quality': 1/3 + (1e-16 if row['lambda_value'] == 0 else 0),
                            'constraint_results': [{'passed': True}, {'passed': False}, {'passed': False}]}
        self.assertEqual(formal.select_lambda(rows, ['A', 'B'])['selected_lambda'], .5)

    def test_missing_duplicate_extra_unscored_and_wrong_variant_refused(self):
        cases = []
        rows = self.rows(); cases.append(rows[:-1])
        rows = self.rows(); rows[-1] = deepcopy(rows[-2]); cases.append(rows)
        rows = self.rows(); rows.append(deepcopy(rows[0])); cases.append(rows)
        rows = self.rows(); rows[0]['score']['quality'] = None; cases.append(rows)
        rows = self.rows(); rows[0]['score']['quality'] = float('nan'); cases.append(rows)
        rows = self.rows(); rows[0]['question_items'] = True; cases.append(rows)
        rows = self.rows(); rows[0]['system_id'] = 'direct'; cases.append(rows)
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                formal.select_lambda(rows, ['A', 'B'])
        for ids in ([], ['A', 'A']):
            with self.assertRaises(ValueError): formal.select_lambda(self.rows(), ids)


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.messages = [{'role': 'user', 'content': 'visible only'}]
        self.kw = {'stage': 'decision', 'case_id': 'A', 'policy': 'value_based', 'repair': False}
        self.events = []

    def wrap(self, client):
        return formal.DecisionReuseClient(client, self.path, self.events.append)

    def test_same_input_reuses_across_variants_cases_and_restarts(self):
        raw = RawClient(['not valid json'])
        client = self.wrap(raw); client.variant = 'value_lambda_0'
        first = client.complete(self.messages, **self.kw)
        client = self.wrap(RawClient([])); client.variant = 'importance_one'
        self.assertEqual(client.complete(self.messages, **dict(self.kw, case_id='B')), first)
        self.assertEqual(len(raw.calls), 1)
        self.assertEqual(client.hits, 1)
        self.assertEqual(self.events[-1]['source_variant'], 'value_lambda_0')

    def test_message_settings_stage_and_repair_kind_isolate(self):
        raw = RawClient(['a', 'b', 'c', 'd', 'e'])
        client = self.wrap(raw)
        client.complete(self.messages, **self.kw)
        client.complete(self.messages + [{'role': 'assistant', 'content': 'other'}], **self.kw)
        client.complete(self.messages, **dict(self.kw, stage='generation'))
        client.complete(self.messages, **dict(self.kw, repair=True, repair_kind='constraint'))
        client.config['seed'] = 2
        client.complete(self.messages, **self.kw)
        self.assertEqual(len(raw.calls), 5)

    def test_bad_record_and_invalid_json_fail_closed_without_call(self):
        raw = RawClient(['first', 'should not be used'])
        client = self.wrap(raw); client.complete(self.messages, **self.kw)
        path = next(self.path.glob('*.json')); saved = formal.load(path)
        for bad in ('{}', '[]', 'bad JSON', json.dumps(dict(saved, raw='replaced'))):
            path.write_text(bad)
            with self.assertRaises(ValueError): client.complete(self.messages, **self.kw)
        self.assertEqual(len(raw.calls), 1)

    def test_transport_error_not_cached_but_initial_generation_is(self):
        raw = RawClient(['first draft', ProviderError('fixture interruption'), 'repaired draft'])
        client = self.wrap(raw)
        initial = dict(self.kw, stage='generation')
        repair = dict(initial, repair=True, repair_kind='constraint')
        self.assertEqual(client.complete(self.messages, **initial), 'first draft')
        with self.assertRaises(ProviderError): client.complete(self.messages, **repair)
        # Resume uses the original draft, and only the interrupted repair calls API.
        resumed = self.wrap(raw)
        self.assertEqual(resumed.complete(self.messages, **initial), 'first draft')
        self.assertEqual(resumed.complete(self.messages, **repair), 'repaired draft')
        self.assertEqual(len(raw.calls), 3)



class FreshExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runs = 0; self.api_calls = 0; self.fail_at = None
        self.score_fail = False; self.format_fail_ids = set()
        self.build_fixture()
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(redirect_stdout(io.StringIO()))
        self.stack.enter_context(patch.object(formal, 'ApiClient', self.make_api))
        self.stack.enter_context(patch.object(formal, 'PilotRunner', self.make_runner))
        self.stack.enter_context(patch.object(formal, 'score_output', self.score))
        self.stack.enter_context(patch.object(formal, 'CUMULATIVE_LEDGER', self.root / 'runs/budget_fixture.json'))

    def write(self, name, value): formal.dump(self.root / name, value)

    def write_rows(self, name, rows):
        path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def build_fixture(self):
        for split in ('design_all', 'validation', 'test'):
            requests = []; answers = []; annotations = []
            for cid in formal.expected_ids(split):
                domain = 'constrained_writing' if 'CW' in cid else 'study_planning'
                requests.append({'case_id': cid, 'domain': domain, 'initial_request': cid})
                answers.append({'case_id': cid, 'answers': {}})
                annotations.append({'case_id': cid, 'domain': domain, 'metadata': {'family_id': cid, 'omission_type': 'complete'}})
            for folder, kind, rows in [('public', 'requests', requests), ('private', 'answers', answers),
                                       ('private', 'annotations', annotations)]:
                self.write_rows(f'data/{folder}/{split}_{kind}.jsonl', rows)
        self.write('config/openrouter.v0.6.formal.json', {'provider': 'fixture', 'base_url': 'https://fixture.invalid',
                   'model': 'fixture', 'temperature': 0, 'seed': 1, 'max_cost_usd': .1,
                   'max_api_calls': 1000, 'provider_routing': {'max_price': {'prompt': 1, 'completion': 1}},
                   'budget_authority': '../../runs/authorized_pilot_budget.json',
                   'max_output_tokens': {'generation': 32, 'decision': 32}})
        self.write('data/public/field_catalog.json', {'domains': {'constrained_writing': {}, 'study_planning': {}}})
        for domain in ['constrained_writing', 'study_planning']:
            self.write(f'data/schemas/output_{domain}.schema.json', {})
        for name in ('formal',) + formal.METHOD_MODULES:
            target = self.root / f'coprompt/{name}.py'; target.parent.mkdir(exist_ok=True)
            target.write_text(f'# frozen {name} fixture\n')
        for name in formal.FRESH_ENTRYPOINTS:
            target = self.root / name; target.parent.mkdir(exist_ok=True)
            target.write_text('# frozen entrypoint fixture\n')
        self.diagnostic = [f'NT{domain}{index:02d}' for domain in ('CW', 'SP') for index in range(1, 11)]
        cases = [{'case_id': cid, 'split': 'design' if split == 'design_all' else split,
                  'domain': 'constrained_writing' if 'CW' in cid else 'study_planning',
                  'family_id': cid, 'omission_type': 'complete'}
                 for split in ('design_all', 'validation', 'test') for cid in formal.expected_ids(split)]
        plan = {'pilot_case_ids': list(formal.PILOT_IDS), 'diagnostic_case_ids': self.diagnostic, 'cases': cases}
        self.write('data/case_plan.json', plan)
        self.write('data/allocation_plan.json', plan)
        files = {str(path.relative_to(self.root)): formal.file_hash(path) for path in self.root.rglob('*') if path.is_file()}
        self.write('data/formal_freeze_v0.6.0.json', dict(plan, status='frozen_before_pilot_outputs', files=files))
        self.write_rows('runs/historical_cost_fixture.jsonl', [{'event_type': 'api_call', 'api_call_number': 1,
                         'accounted_call_cost_usd': .08857385, 'provider_actual_cost_usd': .08857385}])
        self.write('runs/budget_fixture.json', {'authorized_total_usd': .25,
                   'accounted_spend_usd': .08857385, 'source_session_logs': ['historical_cost_fixture.jsonl']})

    def score(self, domain, output, annotation):
        if self.score_fail:
            return {'status': 'unscored_pending_fix', 'quality': None, 'errors': ['fixture scorer failure']}
        if annotation['case_id'] in self.format_fail_ids:
            return {'status': 'format_failure', 'quality': 0.0, 'format_failure': True, 'constraint_results': [], 'errors': ['fixture malformed']}
        return {'status': 'scored', 'quality': 0.0, 'format_failure': False,
                'constraint_results': [{'passed': False, 'score': 0}], 'errors': []}

    def make_api(self, config, key, log):
        owner = self
        class API:
            def __init__(self):
                self.config = config; self.routing = config.get('provider_routing'); self.number = 0
            def complete(self, messages, **kwargs):
                owner.api_calls += 1; self.number += 1
                log({'event_type': 'api_call', 'api_call_number': self.number,
                     'status': 'success', 'accounted_call_cost_usd': .000001, 'provider_actual_cost_usd': .000001})
                return 'first fixture response'
        return API()

    def make_runner(self, client, *args, **kwargs):
        owner = self
        class Runner:
            def run_trajectory(self, request, policy, callback):
                owner.runs += 1
                if owner.fail_at == owner.runs: raise ProviderError('fixture pause')
                raw = client.complete([{'role': 'user', 'content': request['initial_request']}],
                                      stage='generation', case_id=request['case_id'], policy=policy)
                return {'case_id': request['case_id'], 'system_id': policy,
                        'question_items': 0, 'output': {'text': raw}}
        return Runner()

    def execute(self, stage='pilot_a'):
        return formal.execute(stage, 'fixture-key-not-a-credential', root=self.root)

    def through(self, stage):
        for current in formal.STAGES[:formal.STAGES.index(stage) + 1]:
            self.assertIn(self.execute(current)['status'], ('completed', 'already_completed'))

    def manifest(self, stage='pilot_a'):
        return self.root / f'runs/formal_v0.6.0_{stage}/manifest.json'

    def selection(self): return self.root / 'outputs/CoPrompt_validation_v0.6.0/lambda_selection.json'

    def test_all_120_new_cases_full_order_and_budget_carry_forward(self):
        self.through('test')
        self.assertEqual(self.runs, 480); self.assertEqual(self.api_calls, 120)
        self.assertEqual(sum(formal.load(self.manifest(stage))['completed_trajectories'] for stage in formal.STAGES[:3]), 160)
        self.assertEqual(formal.load(self.selection())['selected_lambda'], .5)
        self.assertEqual(formal.load(self.manifest('test'))['planned_trajectories'], 260)
        ledger = formal.load(self.root / 'runs/budget_fixture.json')
        self.assertEqual(Decimal(str(ledger['accounted_spend_usd'])), Decimal('.08869385'))
        self.assertEqual(ledger['authorized_total_usd'], .25)
        self.assertEqual(self.execute('test')['status'], 'already_completed')
        self.assertEqual(self.runs, 480)

    def test_every_later_stage_refuses_missing_predecessors_without_calls(self):
        for stage in formal.STAGES[1:]:
            with self.subTest(stage=stage), self.assertRaises((ValueError, FileNotFoundError)):
                self.execute(stage)
        self.assertEqual(self.api_calls, 0)

    def test_consistent_ledger_rollback_cannot_forget_completed_stage_charges(self):
        self.through('pilot_b')
        path = self.root / 'runs/budget_fixture.json'
        ledger = formal.load(path)
        ledger['source_session_logs'] = ['historical_cost_fixture.jsonl']
        ledger['accounted_spend_usd'] = .08857385
        formal.dump(path, ledger)
        calls = self.api_calls
        with self.assertRaisesRegex(formal.BudgetError, 'absent from the cumulative ledger'):
            self.execute('design')
        self.assertEqual(self.api_calls, calls)
        self.assertEqual(formal.load(path), ledger)

    def test_pilot_gate_accepts_ten_paired_scored_cases_with_zero_quality(self):
        self.format_fail_ids = set(formal.PILOT_IDS[:2])
        result = self.execute()
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['pilot_gate']['paired_scored_cases'], 10)
        self.assertTrue(result['pilot_gate']['passed'])
        self.assertEqual(self.execute('pilot_b')['status'], 'completed')
        self.assertEqual(self.runs, 48)
        self.assertFalse(self.selection().exists())

    def test_gate_failure_preserves_all_cells_and_never_resamples(self):
        self.format_fail_ids = set(formal.PILOT_IDS[:3])
        result = self.execute()
        self.assertEqual(result['status'], 'pilot_gate_failed')
        self.assertEqual(result['pilot_gate']['paired_scored_cases'], 9)
        self.assertEqual(self.execute()['status'], 'pilot_gate_failed')
        for stage in formal.STAGES[1:]:
            with self.subTest(stage=stage), self.assertRaises(ValueError): self.execute(stage)
        self.assertEqual(self.runs, 24); self.assertEqual(self.api_calls, 12)

    def test_partial_resume_preserves_completed_cells(self):
        self.fail_at = 4
        self.assertEqual(self.execute()['status'], 'interrupted')
        self.assertEqual(formal.load(self.manifest())['completed_trajectories'], 3)
        self.fail_at = None
        self.assertEqual(self.execute()['status'], 'completed')
        self.assertEqual(self.runs, 25); self.assertEqual(self.api_calls, 12)

    def test_scorer_failure_saves_first_raw_without_regeneration(self):
        self.score_fail = True
        self.assertEqual(self.execute()['status'], 'interrupted')
        self.assertIsNotNone(formal.load(self.manifest())['pending_cell'])
        self.score_fail = False
        self.assertEqual(self.execute()['status'], 'completed')
        self.assertEqual(self.runs, 24); self.assertEqual(self.api_calls, 12)

    def test_append_before_manifest_crash_recovers_matching_pending(self):
        self.fail_at = 4; self.execute(); self.fail_at = None
        path = self.manifest(); manifest = formal.load(path)
        trajectory = path.parent / 'trajectories.jsonl'; lines = trajectory.read_bytes().splitlines(keepends=True)
        last = formal.strict_json(lines[-1].decode())
        raw = {key: value for key, value in last.items() if key not in ('score', 'record_sha256')}
        manifest['row_hashes'].pop(); manifest['completed_trajectories'] = 2
        manifest['trajectory_sha256'] = formal.hashlib.sha256(b''.join(lines[:2])).hexdigest()
        manifest['pending_cell'] = {'trajectory': raw, 'sha256': formal.digest(raw)}
        formal.dump(path, manifest)
        self.assertEqual(self.execute()['status'], 'completed'); self.assertEqual(self.runs, 25)

    def test_completed_validation_selection_recovers_without_api_or_budget(self):
        self.through('validation'); self.selection().unlink()
        self.write('runs/budget_fixture.json', {'intentionally': 'unreadable budget fixture'})
        self.assertEqual(self.execute('validation')['status'], 'already_completed')
        self.assertTrue(self.selection().exists()); self.assertEqual(self.runs, 220)

    def test_test_refuses_rewritten_selection_or_incomplete_validation(self):
        self.through('validation')
        selection = formal.load(self.selection())
        formal.dump(self.selection(), dict(selection, selected_lambda=0))
        with self.assertRaises(ValueError): self.execute('test')
        formal.dump(self.selection(), selection)
        manifest = formal.load(self.manifest('validation')); manifest['status'] = 'interrupted'
        formal.dump(self.manifest('validation'), manifest)
        with self.assertRaises(ValueError): self.execute('test')
        self.assertEqual(self.runs, 220)

    def test_rehashed_row_tamper_cannot_bypass_manifest_or_prior_stage_check(self):
        self.execute(); path = self.manifest().parent / 'trajectories.jsonl'
        lines = path.read_text().splitlines(); row = json.loads(lines[0])
        row['question_items'] = 3
        row['record_sha256'] = formal.digest({key: value for key, value in row.items() if key != 'record_sha256'})
        lines[0] = json.dumps(row); path.write_text('\n'.join(lines) + '\n')
        for stage in ('pilot_a', 'pilot_b'):
            with self.assertRaises(ValueError): self.execute(stage)
        self.assertEqual(self.runs, 24)

    def test_fresh_cache_starts_empty_and_cannot_escape_project(self):
        cache = self.root / 'runs/formal_raw_response_cache'; cache.mkdir()
        (cache / 'unregistered.json').write_text('cached fixture content')
        with self.assertRaises(ValueError): self.execute()
        (cache / 'unregistered.json').unlink(); cache.rmdir()
        with tempfile.TemporaryDirectory() as external:
            cache.symlink_to(external, target_is_directory=True)
            with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.api_calls, 0)

    def test_registered_case_and_allocation_drift_refused_before_calls(self):
        freeze = formal.load(self.root / 'data/formal_freeze_v0.6.0.json')
        for name, changes in [('case_plan', {'family_id': 'wrong-family'}),
                              ('case_plan', {'split': 'test'}),
                              ('allocation_plan', {'omission_type': 'optional_only'}),
                              ('allocation_plan', {'domain': 'study_planning'})]:
            path = self.root / f'data/{name}.json'
            original = formal.load(path)
            changed = deepcopy(original); changed['cases'][0].update(changes)
            formal.dump(path, changed)
            with self.subTest(name=name, changes=changes), self.assertRaises(ValueError):
                formal.verify_case_plan(self.root, freeze)
            formal.dump(path, original)
        path = self.root / 'data/case_plan.json'; changed = formal.load(path)
        changed['cases'][-1] = deepcopy(changed['cases'][0]); formal.dump(path, changed)
        with self.assertRaises(ValueError): formal.verify_case_plan(self.root, freeze)
        self.assertEqual(self.api_calls, 0)

    def test_changed_source_or_pending_cell_fails_before_resampling(self):
        self.score_fail = True; self.execute(); self.score_fail = False
        manifest = formal.load(self.manifest())
        manifest['pending_cell']['trajectory']['output']['text'] = 'changed'
        formal.dump(self.manifest(), manifest)
        with self.assertRaises(ValueError): self.execute()
        (self.root / 'coprompt/prompts.py').write_text('changed')
        with self.assertRaises(ValueError): self.execute()
        self.assertEqual(self.runs, 1)


if __name__ == '__main__': unittest.main()
