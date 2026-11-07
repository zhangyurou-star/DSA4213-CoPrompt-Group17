"""No network: real provider parsing, durable reservations and crash recovery."""
from contextlib import contextmanager, ExitStack
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from coprompt import formal
from coprompt.provider import ProviderError
from tools.analyze_fresh import checked_costs
from tools import preflight_fresh, show_status

CONFIG = {'base_url': 'https://fixture.invalid', 'provider': 'fixture', 'model': 'fixture',
          'max_api_calls': 4, 'max_cost_usd': .1, 'max_output_tokens': {'generation': 32},
          'provider_routing': {'max_price': {'prompt': 1, 'completion': 1}}}
MESSAGES = [{'role': 'user', 'content': 'A synthetic transport fixture.'}]
KWARGS = {'stage': 'generation', 'case_id': 'NDCW01', 'policy': 'direct'}


class SimulatedCrash(BaseException): pass


class Response:
    def __init__(self, cost=.00005, interrupt=False):
        self.cost, self.interrupt = cost, interrupt
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self):
        if self.interrupt: raise KeyboardInterrupt('fixture: request dispatched, read interrupted')
        return json.dumps({'choices': [{'message': {'content': 'fixture output'}, 'finish_reason': 'stop'}],
                           'usage': {'cost': self.cost, 'prompt_tokens': 20, 'completion_tokens': 4}}).encode()


class Opener:
    def __init__(self, response): self.response, self.calls = response, 0
    def open(self, *args, **kwargs):
        self.calls += 1
        return self.response


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name).resolve()
        self.root = self.project / 'experiments/fresh'
        self.path = self.project / 'runs/authorized_pilot_budget.json'
        formal.dump(self.path, {'authorized_total_usd': .25, 'accounted_spend_usd': .01,
                               'source_session_logs': ['prior_fixture.jsonl']})
        formal.durable_text(self.path.parent / 'prior_fixture.jsonl', json.dumps({
            'event_type': 'api_call', 'api_call_number': 1, 'status': 'success',
            'provider_actual_cost_usd': .01, 'accounted_call_cost_usd': .01}) + '\n')

    @contextmanager
    def session(self, name='fixture'):
        with formal.FreshBudgetLedger(self.path, self.root) as ledger:
            path = self.root / f'runs/formal_{name}_session.jsonl'
            ledger.register_session(path)
            yield ledger, path

    def client(self, ledger, response):
        client = formal.ReservedApiClient(ledger.cap_config(CONFIG), 'offline-fixture', ledger)
        opener = Opener(response); client.client._opener = opener
        return client, opener

    def events(self, path): return [formal.strict_json(line) for line in path.read_text().splitlines()]

    def entrypoint(self, name):
        """Isolate readiness metadata; exercise real locked budget/recovery code."""
        with ExitStack() as stack:
            stack.enter_context(patch.object(formal, 'CUMULATIVE_LEDGER', self.path))
            stack.enter_context(patch.object(formal, 'ApiClient', side_effect=AssertionError('No API client in offline entrypoints')))
            if name == 'status': return show_status.status(self.root)
            original_load = formal.load
            def metadata_load(path):
                path = Path(path)
                if path.name == 'formal_freeze_v0.6.0.json':
                    return {'files': {name: 'fixture' for name in formal.required_frozen_files()}}
                if path.name in ('openrouter.v0.6.formal.json', 'openrouter.v0.4.formal.json'):
                    return {'fixture': True}
                return original_load(path)
            stack.enter_context(patch.object(formal, 'load', side_effect=metadata_load))
            for method in ('verify_freeze', 'verify_isolated_caches'):
                stack.enter_context(patch.object(formal, method))
            stack.enter_context(patch.object(formal, 'verify_case_plan', return_value={'diagnostic_case_ids': []}))
            stack.enter_context(patch.object(formal, 'load_dataset', return_value=({}, {}, {})))
            stack.enter_context(patch.object(formal, 'planned_jobs', return_value=[]))
            stack.enter_context(patch.object(formal, 'file_hash', return_value='fixture'))
            stack.enter_context(patch.object(preflight_fresh, 'verify_runtime_config'))
            return preflight_fresh.preflight(self.root)

    def register_manifest(self, path):
        formal.dump(self.root / 'runs/formal_v0.6.0_pilot_a/manifest.json',
                    {'session_logs': [str(path.relative_to(self.root))]})

    def test_completed_call_replaces_reserve_with_original_charge_once(self):
        with self.session() as (ledger, path):
            client, opener = self.client(ledger, Response())
            self.assertEqual(client.complete(MESSAGES, **KWARGS), 'fixture output')
            self.assertEqual(opener.calls, 1)
            self.assertEqual(ledger.spent, Decimal('.01005'))
            events = self.events(path)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]['provider_actual_cost_usd'], .00005)
            self.assertEqual(events[0]['accounted_call_cost_usd'], .00005)
            self.assertEqual(events[0]['status'], 'success')
        with formal.FreshBudgetLedger(self.path, self.root) as ledger:
            self.assertEqual(ledger.spent, Decimal('.01005'))
        self.assertFalse((self.root / formal.BUDGET_TRANSACTION).exists())

    def test_dispatch_interrupt_reserve_survives_and_next_session_does_not_double_count(self):
        with self.session() as (ledger, path):
            client, opener = self.client(ledger, Response(interrupt=True))
            with self.assertRaises(KeyboardInterrupt): client.complete(MESSAGES, **KWARGS)
            self.assertEqual(opener.calls, 1)
            reserve = self.events(path)[0]
            self.assertEqual(reserve['error_code'], 'unsettled_request_reservation')
            self.assertEqual(reserve['dispatch_status'], 'unconfirmed')
            self.assertEqual(reserve['status'], 'error')
            self.assertIsNone(reserve['provider_actual_cost_usd'])
            reserved_spend = ledger.spent
            self.assertGreater(reserved_spend, Decimal('.01'))
            with self.assertRaises(formal.BudgetError): client.complete(MESSAGES, **KWARGS)
            self.assertEqual(opener.calls, 1)
        with self.session('resumed') as (ledger, _):
            self.assertEqual(ledger.spent, reserved_spend)
            client, _ = self.client(ledger, Response())
            client.complete(MESSAGES, **KWARGS)
            self.assertEqual(ledger.spent, reserved_spend + Decimal('.00005'))
        with formal.FreshBudgetLedger(self.path, self.root) as ledger:
            self.assertEqual(ledger.spent, reserved_spend + Decimal('.00005'))
        self.assertEqual(len(self.events(path)), 1)

    def test_hard_process_exit_after_dispatch_keeps_the_reserve_without_double_charge(self):
        script = '''
import os, sys
from pathlib import Path
from coprompt import formal
ledger_path, root = map(Path, sys.argv[1:])
with formal.FreshBudgetLedger(ledger_path, root) as ledger:
    ledger.register_session(root / 'runs/formal_hard_exit_session.jsonl')
    client = formal.ReservedApiClient(ledger.cap_config(%r), 'offline-fixture', ledger)
    class HardExitOpener:
        def open(self, *args, **kwargs): os._exit(17)
    client.client._opener = HardExitOpener()
    client.complete(%r, **%r)
''' % (CONFIG, MESSAGES, KWARGS)
        result = subprocess.run([sys.executable, '-B', '-c', script, str(self.path), str(self.root)],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 17, result.stderr)
        path = self.root / 'runs/formal_hard_exit_session.jsonl'
        event = self.events(path)[0]
        expected = Decimal('.01') + Decimal(str(event['accounted_call_cost_usd']))
        for _ in range(2):
            with formal.FreshBudgetLedger(self.path, self.root) as ledger:
                self.assertEqual(ledger.spent, expected)
        self.assertEqual(len(self.events(path)), 1)

    def crash_at(self, ledger, kind, point):
        original_text, original_save = formal.durable_text, ledger._save
        def active():
            path = self.root / formal.BUDGET_TRANSACTION
            return path.exists() and formal.load(path)['kind'] == kind
        def write(path, value):
            if active() and point == 'before_log': raise SimulatedCrash()
            original_text(path, value)
            if active() and point == 'after_log': raise SimulatedCrash()
        def save():
            original_save()
            if active() and point == 'after_ledger': raise SimulatedCrash()
        return patch.multiple(formal, durable_text=write), patch.object(ledger, '_save', side_effect=save)

    def test_settlement_crash_windows_recover_known_charge_exactly_once(self):
        for point in ('before_log', 'after_log', 'after_ledger'):
            with self.subTest(point=point):
                with self.session(point) as (ledger, path):
                    before = ledger.spent
                    client, opener = self.client(ledger, Response())
                    p1, p2 = self.crash_at(ledger, 'settle', point)
                    with p1, p2, self.assertRaises(SimulatedCrash): client.complete(MESSAGES, **KWARGS)
                    self.assertEqual(opener.calls, 1)
                self.assertTrue((self.root / formal.BUDGET_TRANSACTION).exists())
                for _ in range(2):
                    with formal.FreshBudgetLedger(self.path, self.root) as ledger:
                        self.assertEqual(ledger.spent, before + Decimal('.00005'))
                self.assertEqual(len(self.events(path)), 1)
                self.assertEqual(self.events(path)[0]['status'], 'success')
                self.assertFalse((self.root / formal.BUDGET_TRANSACTION).exists())

    def test_reservation_crash_windows_conservatively_recover_even_without_dispatch(self):
        for point in ('before_log', 'after_log', 'after_ledger'):
            with self.subTest(point=point):
                with self.session(point) as (ledger, path):
                    before = ledger.spent
                    client, opener = self.client(ledger, Response())
                    p1, p2 = self.crash_at(ledger, 'reserve', point)
                    with p1, p2, self.assertRaises(SimulatedCrash): client.complete(MESSAGES, **KWARGS)
                    self.assertEqual(opener.calls, 0)
                for _ in range(2):
                    with formal.FreshBudgetLedger(self.path, self.root) as ledger:
                        event = self.events(path)[0]
                        self.assertEqual(ledger.spent, before + Decimal(str(event['accounted_call_cost_usd'])))
                self.assertEqual(event['dispatch_status'], 'unconfirmed')
                self.assertEqual(event['status'], 'error')
                self.assertEqual(len(self.events(path)), 1)

    def test_journal_cannot_repair_unrelated_historical_mismatch(self):
        with self.session() as (ledger, _):
            client, _ = self.client(ledger, Response())
            p1, p2 = self.crash_at(ledger, 'settle', 'before_log')
            with p1, p2, self.assertRaises(SimulatedCrash): client.complete(MESSAGES, **KWARGS)
        historical = self.path.parent / 'prior_fixture.jsonl'
        row = self.events(historical)[0]
        row['provider_actual_cost_usd'] = row['accounted_call_cost_usd'] = .02
        formal.durable_text(historical, json.dumps(row) + '\n')
        ledger_before = self.path.read_bytes()
        with self.assertRaisesRegex(formal.BudgetError, 'inconsistent historical costs'):
            with formal.FreshBudgetLedger(self.path, self.root): pass
        self.assertEqual(self.path.read_bytes(), ledger_before)
        self.assertTrue((self.root / formal.BUDGET_TRANSACTION).exists())

    def test_reservation_cannot_exceed_remaining_authorization_before_dispatch(self):
        saved = formal.load(self.path); saved['authorized_total_usd'] = .010001; formal.dump(self.path, saved)
        with self.session() as (ledger, path):
            client, opener = self.client(ledger, Response())
            with self.assertRaises(ProviderError): client.complete(MESSAGES, **KWARGS)
            self.assertEqual(opener.calls, 0)
            self.assertEqual(ledger.spent, Decimal('.01'))
            self.assertEqual(self.events(path), [])

    def test_actual_overrun_is_preserved_then_blocks_instead_of_altering_provider_charge(self):
        with self.session() as (ledger, path):
            client, _ = self.client(ledger, Response(cost=.3))
            with self.assertRaises(ProviderError): client.complete(MESSAGES, **KWARGS)
            self.assertEqual(ledger.spent, Decimal('.31'))
            self.assertEqual(self.events(path)[0]['provider_actual_cost_usd'], .3)
            self.assertEqual(self.events(path)[0]['accounted_call_cost_usd'], .3)
        with self.assertRaisesRegex(formal.BudgetError, 'exceeds the authorized'):
            with formal.FreshBudgetLedger(self.path, self.root): pass

    def test_analysis_reports_unconfirmed_reserve_as_unknown_cost_not_success(self):
        with self.session() as (ledger, path):
            client, _ = self.client(ledger, Response(interrupt=True))
            with self.assertRaises(KeyboardInterrupt): client.complete(MESSAGES, **KWARGS)
            reserve = self.events(path)[0]['accounted_call_cost_usd']
        stages = {'fixture': {'manifest': {'session_logs': [str(path.relative_to(self.root))]}}}
        report = checked_costs(self.root, self.project, stages)
        fresh = report['counts_and_costs']['fresh']
        self.assertEqual(fresh['successes'], 0)
        self.assertEqual(fresh['failures'], 1)
        self.assertEqual(fresh['unknown_reserve_usd'], reserve)
        self.assertEqual(fresh['provider_reported_usd'], 0)

    def test_offline_preflight_recovers_valid_settlement_before_budget_reconciliation(self):
        self.check_offline_recovery('preflight')

    def test_offline_status_recovers_valid_settlement_before_budget_reconciliation(self):
        self.check_offline_recovery('status')

    def check_offline_recovery(self, name):
        with self.session() as (ledger, path):
            self.register_manifest(path)
            client, _ = self.client(ledger, Response())
            p1, p2 = self.crash_at(ledger, 'settle', 'after_log')
            with p1, p2, self.assertRaises(SimulatedCrash): client.complete(MESSAGES, **KWARGS)
        report = self.entrypoint(name)
        self.assertEqual(report['api_calls'], 0)
        self.assertEqual(report['cumulative_budget']['accounted_spend_usd'], .01005)
        self.assertEqual(report['cumulative_budget']['recovered_fresh_budget_transaction'], 'settle')
        self.assertFalse((self.root / formal.BUDGET_TRANSACTION).exists())
        again = self.entrypoint(name)
        self.assertEqual(again['cumulative_budget']['accounted_spend_usd'], .01005)
        self.assertIsNone(again['cumulative_budget']['recovered_fresh_budget_transaction'])

    def test_both_offline_entrypoints_reject_rolled_back_session_registration(self):
        with self.session() as (_, path): self.register_manifest(path)
        saved = formal.load(self.path); saved['source_session_logs'] = ['prior_fixture.jsonl']
        formal.dump(self.path, saved)
        for name in ('status', 'preflight'):
            with self.subTest(entrypoint=name), self.assertRaisesRegex(formal.BudgetError, 'absent from the cumulative ledger'):
                self.entrypoint(name)
        self.assertEqual(formal.load(self.path), saved)


if __name__ == '__main__': unittest.main()
