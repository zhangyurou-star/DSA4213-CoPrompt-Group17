"""Offline fresh plan, gate, CLI, and settings checks."""
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from coprompt import formal
from tools.preflight_fresh import verify_runtime_config


class FreshPlanTests(unittest.TestCase):
    def requests(self, split):
        return {cid: {'domain': 'constrained_writing' if 'CW' in cid else 'study_planning'}
                for cid in formal.expected_ids(split)}

    def test_design_partition_is_exactly_160_distinct_cells(self):
        all_requests = self.requests('design_all')
        pilot = {cid: all_requests[cid] for cid in formal.PILOT_IDS}
        remaining = {cid: row for cid, row in all_requests.items() if cid not in pilot}
        jobs = {stage: formal.planned_jobs(stage, pilot if stage.startswith('pilot_') else remaining, .25, [])
                for stage in formal.STAGES[:3]}
        self.assertEqual([len(jobs[stage]) for stage in formal.STAGES[:3]], [24, 24, 112])
        cells = [job for group in jobs.values() for job in group]
        self.assertEqual(len({(job[0], job[1]) for job in cells}), 160)
        self.assertEqual({job[3] for job in cells}, {.25})

    def test_validation_requires_all_twenty_and_diagnostic_is_balanced(self):
        validation = self.requests('validation')
        self.assertEqual(len(formal.planned_jobs('validation', validation, None, [])), 60)
        with self.assertRaises(ValueError): formal.planned_jobs('validation', dict(list(validation.items())[:-1]), None, [])
        test = self.requests('test')
        balanced = [f'NT{domain}{index:02d}' for domain in ('CW', 'SP') for index in range(1, 11)]
        jobs = formal.planned_jobs('test', test, .5, balanced)
        self.assertEqual(len(jobs), 260)
        self.assertEqual(sum(job[1] == 'importance_one' for job in jobs), 20)
        for diagnostic in (balanced[:-1], balanced[:-1] + [balanced[0]], list(test)[:20]):
            with self.assertRaises(ValueError): formal.planned_jobs('test', test, .5, diagnostic)

    def test_pilot_gate_requires_pairs_not_twenty_individually_scored_cells(self):
        rows = [{'case_id': cid, 'system_id': policy,
                 'score': {'status': 'scored', 'format_failure': False, 'quality': 0}}
                for cid in formal.PILOT_IDS for policy in formal.POLICIES[:2]]
        for index in (0, 2, 4):
            rows[index]['score'] = {'status': 'format_failure', 'format_failure': True, 'quality': 0}
        self.assertEqual(sum(row['score']['status'] == 'scored' for row in rows), 21)
        self.assertFalse(formal.pilot_gate(rows)['passed'])
        with self.assertRaises(ValueError): formal.pilot_gate(rows[:-1])

    def test_single_shared_cumulative_authority(self):
        self.assertEqual(formal.CUMULATIVE_LEDGER, formal.ROOT.parents[1] / 'runs/authorized_pilot_budget.json')
        self.assertNotEqual(formal.CUMULATIVE_LEDGER, formal.CUMULATIVE_LEDGER.parent / 'new_budget.json')

    def test_all_entry_runs_every_stage_in_order_and_stops_at_gate(self):
        for outcomes, expected in (([{'status': 'completed'}] * 5, list(formal.STAGES)),
                                   ([{'status': 'pilot_gate_failed'}], ['pilot_a']),
                                   ([{'status': 'completed'}, {'status': 'interrupted'}], ['pilot_a', 'pilot_b'])):
            with (patch.object(formal, 'execute', side_effect=outcomes) as execute,
                  patch.object(formal.getpass, 'getpass', return_value='offline-fixture'),
                  patch('sys.argv', ['formal', '--stage', 'all', '--key-stdin']), redirect_stdout(io.StringIO())):
                code = formal.main()
            self.assertEqual([call.args[0] for call in execute.call_args_list], expected)
            self.assertEqual(code, 0 if len(expected) == 5 else 1)


class RuntimeConfigTests(unittest.TestCase):
    def test_inference_settings_and_original_authority_are_fixed(self):
        old = {'model': 'fixed', 'temperature': 0, 'seed': 1, 'max_cost_usd': .1,
               'authorized_total_budget_usd': .1, 'status': 'old'}
        new = {key: value for key, value in old.items() if key != 'authorized_total_budget_usd'}
        new.update(budget_authority='../../runs/authorized_pilot_budget.json',
                   authorized_total_budget_usd_at_preparation=.25, status='fresh')
        verify_runtime_config(old, new)
        for changes in ({'seed': 2}, {'model': 'different'}, {'temperature': .1},
                        {'budget_authority': 'runs/budget.json'}, {'authorized_total_budget_usd': .25}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): verify_runtime_config(old, dict(new, **changes))


if __name__ == '__main__': unittest.main()
