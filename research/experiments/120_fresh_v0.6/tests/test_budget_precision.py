"""Offline regressions for exact costs stored in a JSON-number ledger."""
from decimal import Decimal
import json
import math
import unittest

from coprompt import formal
from tools.analyze_fresh import checked_costs
import test_fresh_budget as fixtures


CONFIG = dict(fixtures.CONFIG, provider_routing={
    'max_price': {'prompt': .11, 'completion': .35}})


class BudgetPrecisionTests(unittest.TestCase):
    # Reuse the existing isolated ledger and transport fixtures, without
    # inheriting their test cases or ever constructing a live HTTP transport.
    setUp = fixtures.ReservationTests.setUp
    session = fixtures.ReservationTests.session
    events = fixtures.ReservationTests.events
    crash_at = fixtures.ReservationTests.crash_at
    register_manifest = fixtures.ReservationTests.register_manifest
    entrypoint = fixtures.ReservationTests.entrypoint

    def client(self, ledger, response):
        client = formal.ReservedApiClient(ledger.cap_config(CONFIG), 'offline-fixture', ledger)
        opener = fixtures.Opener(response)
        client.client._opener = opener
        return client, opener

    def estimate(self):
        byte_bound = len(json.dumps(fixtures.MESSAGES, ensure_ascii=False).encode('utf-8')) + 1024
        estimate = (byte_bound * .11 + CONFIG['max_output_tokens']['generation'] * .35) / 1_000_000
        return Decimal(str(estimate))

    def seed_history(self, costs, cap=.25):
        rows = [{'event_type': 'api_call', 'api_call_number': index,
                 'status': 'success', 'provider_actual_cost_usd': cost,
                 'accounted_call_cost_usd': cost}
                for index, cost in enumerate(costs, 1)]
        formal.durable_text(self.path.parent / 'prior_fixture.jsonl',
                            ''.join(json.dumps(row) + '\n' for row in rows))
        exact = sum((Decimal(str(cost)) for cost in costs), Decimal(0))
        saved = formal.load(self.path)
        saved.update(accounted_spend_usd=float(exact), authorized_total_usd=cap)
        formal.dump(self.path, saved)
        return exact

    def test_real_price_tail_can_settle_then_reopen_exactly(self):
        before = self.seed_history([.08857385])
        reserved = before + self.estimate()
        self.assertNotEqual(reserved, Decimal(str(float(reserved))))
        with self.session() as (ledger, path):
            client, opener = self.client(ledger, fixtures.Response())
            self.assertEqual(client.complete(fixtures.MESSAGES, **fixtures.KWARGS), 'fixture output')
            self.assertEqual(opener.calls, 1)
            self.assertEqual(ledger.spent, before + Decimal('.00005'))
            event, = self.events(path)
            self.assertEqual(event['status'], 'success')
            self.assertEqual(event['provider_actual_cost_usd'], .00005)
            self.assertEqual(event['accounted_call_cost_usd'], .00005)
        with formal.FreshBudgetLedger(self.path, self.root) as ledger:
            self.assertEqual(ledger.spent, before + Decimal('.00005'))
        self.assertFalse((self.root / formal.BUDGET_TRANSACTION).exists())

    def test_tail_reserve_restart_and_successive_calls_are_counted_once(self):
        expected = self.seed_history([.08857385]) + self.estimate()
        with self.session('interrupted') as (ledger, interrupted):
            client, opener = self.client(ledger, fixtures.Response(interrupt=True))
            with self.assertRaises(KeyboardInterrupt):
                client.complete(fixtures.MESSAGES, **fixtures.KWARGS)
            self.assertEqual(opener.calls, 1)
            self.assertEqual(ledger.spent, expected)
        for _ in range(2):
            with formal.FreshBudgetLedger(self.path, self.root) as ledger:
                self.assertEqual(ledger.spent, expected)
        with self.session('resumed') as (ledger, resumed):
            self.assertEqual(ledger.spent, expected)
            cost = .00005000000000000001
            client, opener = self.client(ledger, fixtures.Response(cost=cost))
            for _ in range(3):
                client.complete(fixtures.MESSAGES, **fixtures.KWARGS)
                expected += Decimal(str(cost))
                self.assertEqual(ledger.spent, expected)
            self.assertEqual(opener.calls, 3)
        for _ in range(2):
            with formal.FreshBudgetLedger(self.path, self.root) as ledger:
                self.assertEqual(ledger.spent, expected)
        reserve, = self.events(interrupted)
        self.assertEqual(reserve['dispatch_status'], 'unconfirmed')
        self.assertIsNone(reserve['provider_actual_cost_usd'])
        self.assertEqual([event['api_call_number'] for event in self.events(resumed)], [1, 2, 3])

    def test_tail_reservation_and_settlement_recover_every_commit_window(self):
        for kind in ('reserve', 'settle'):
            for point in ('before_log', 'after_log', 'after_ledger'):
                with self.subTest(kind=kind, point=point):
                    with self.session(kind + '_' + point) as (ledger, path):
                        before = ledger.spent
                        client, opener = self.client(ledger, fixtures.Response())
                        p1, p2 = self.crash_at(ledger, kind, point)
                        with p1, p2, self.assertRaises(fixtures.SimulatedCrash):
                            client.complete(fixtures.MESSAGES, **fixtures.KWARGS)
                        self.assertEqual(opener.calls, 0 if kind == 'reserve' else 1)
                    expected = before + (self.estimate() if kind == 'reserve' else Decimal('.00005'))
                    for _ in range(2):
                        with formal.FreshBudgetLedger(self.path, self.root) as ledger:
                            self.assertEqual(ledger.spent, expected)
                    event, = self.events(path)
                    self.assertEqual(event['status'], 'error' if kind == 'reserve' else 'success')
                    self.assertFalse((self.root / formal.BUDGET_TRANSACTION).exists())

    def test_settlement_projects_exact_log_sum_instead_of_rounded_before_total(self):
        before = self.seed_history([.01, 1e-19])
        cost = 5.000000000000068e-05
        reserved = before + self.estimate()
        delta = Decimal(str(cost)) - self.estimate()
        expected = before + Decimal(str(cost))
        # These two results intentionally straddle a float rounding boundary.
        self.assertNotEqual(float(expected), float(Decimal(str(float(reserved))) + delta))
        with self.session('rounding_boundary') as (ledger, path):
            client, opener = self.client(ledger, fixtures.Response(cost=cost))
            p1, p2 = self.crash_at(ledger, 'settle', 'before_log')
            with p1, p2, self.assertRaises(fixtures.SimulatedCrash):
                client.complete(fixtures.MESSAGES, **fixtures.KWARGS)
            self.assertEqual(opener.calls, 1)
        for _ in range(2):
            with formal.FreshBudgetLedger(self.path, self.root) as ledger:
                self.assertEqual(ledger.spent, expected)
                self.assertEqual(ledger.document['accounted_spend_usd'], float(expected))
        event, = self.events(path)
        self.assertEqual(event['provider_actual_cost_usd'], cost)
        self.assertEqual(event['accounted_call_cost_usd'], cost)

    def test_ledger_rejects_adjacent_float_and_real_mismatches(self):
        exact = self.seed_history([.01, 1e-19])
        canonical = float(exact)
        with formal.FreshBudgetLedger(self.path, self.root) as ledger:
            self.assertEqual(ledger.spent, exact)
        for bad in (math.nextafter(canonical, math.inf),
                    math.nextafter(canonical, 0), canonical + .000001):
            with self.subTest(recorded=bad):
                saved = formal.load(self.path)
                saved['accounted_spend_usd'] = bad
                formal.dump(self.path, saved)
                before = self.path.read_bytes()
                with self.assertRaisesRegex(formal.BudgetError, 'disagree'):
                    with formal.FreshBudgetLedger(self.path, self.root):
                        self.fail('A noncanonical recorded total was accepted')
                self.assertEqual(self.path.read_bytes(), before)

    def test_exact_sum_over_cap_is_blocked_even_when_projection_equals_cap(self):
        exact = self.seed_history([.01, 1e-19], cap=.01)
        self.assertGreater(exact, Decimal('.01'))
        self.assertEqual(float(exact), .01)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(formal.BudgetError, 'exceeds the authorized'):
            with formal.FreshBudgetLedger(self.path, self.root):
                self.fail('The rounded display value must never grant additional budget')
        self.assertEqual(self.path.read_bytes(), before)

    def test_analysis_accepts_canonical_projection_but_rejects_other_totals(self):
        exact = self.seed_history([.01, 1e-19])
        report = checked_costs(self.root, self.project, {})
        self.assertEqual(report['cumulative_accounted_usd'], float(exact))
        self.assertEqual(report['remaining_usd'], float(Decimal('.25') - exact))
        for bad in (math.nextafter(float(exact), math.inf), float(exact) + .000001):
            with self.subTest(recorded=bad):
                saved = formal.load(self.path)
                saved['accounted_spend_usd'] = bad
                formal.dump(self.path, saved)
                with self.assertRaisesRegex(ValueError, 'inconsistent'):
                    checked_costs(self.root, self.project, {})

    def test_analysis_rejects_exact_sum_over_cap_even_when_projection_matches(self):
        exact = self.seed_history([.01, 1e-19], cap=.01)
        self.assertEqual(float(exact), .01)
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            checked_costs(self.root, self.project, {})

    def test_offline_entrypoints_accept_precision_tail_without_new_calls(self):
        with self.session('offline') as (ledger, path):
            self.register_manifest(path)
            client, opener = self.client(ledger, fixtures.Response(interrupt=True))
            with self.assertRaises(KeyboardInterrupt):
                client.complete(fixtures.MESSAGES, **fixtures.KWARGS)
            exact = ledger.spent
        before = self.path.read_bytes()
        for name in ('preflight', 'status'):
            with self.subTest(entrypoint=name):
                report = self.entrypoint(name)
                self.assertEqual(report['api_calls'], 0)
                self.assertEqual(report['cumulative_budget']['accounted_spend_usd'], float(exact))
        self.assertEqual(opener.calls, 1)
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
