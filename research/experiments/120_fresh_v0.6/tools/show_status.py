"""Show this fresh experiment's saved stage counts and shared budget without API calls."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coprompt import formal


def status(root=ROOT):
    root = Path(root).resolve()
    stages = {}
    for stage, expected in formal.PLANNED_TRAJECTORIES.items():
        path = root / f'runs/formal_v0.6.0_{stage}/manifest.json'
        saved = formal.load(path) if path.exists() else {}
        stages[stage] = {'completed': saved.get('completed_trajectories', 0), 'planned': expected,
                         'status': saved.get('status', 'not_started'), 'error': saved.get('error')}
        if stage == 'pilot_a' and 'pilot_gate' in saved:
            stages[stage]['pilot_gate'] = saved['pilot_gate']
    with formal.FreshBudgetLedger(formal.CUMULATIVE_LEDGER, root) as ledger:
        formal.verify_registered_stage_sessions(root, ledger)
        budget = {'accounted_spend_usd': float(ledger.spent), 'authorized_total_usd': float(ledger.authorized),
                  'remaining_usd': float(ledger.authorized - ledger.spent),
                  'recovered_fresh_budget_transaction': ledger.recovered_transaction}
    return {'stages': stages, 'cumulative_budget': budget, 'api_calls': 0}


def main():
    result = status()
    titles = {'pilot_a': '12 new pilot cases: direct/exhaustive', 'pilot_b': '12 new pilot cases: prompt/value',
              'design': 'Remaining 28 design cases', 'validation': 'Full 20-case validation', 'test': '60 test cases and 20 diagnostic trajectories'}
    for stage, item in result['stages'].items():
        print(f'{titles[stage]}: {item["completed"]}/{item["planned"]} trajectories; status {item["status"]}')
        if item.get('error'):
            print('Interruption details: ' + json.dumps(item['error'], ensure_ascii=False))
        if item.get('pilot_gate'):
            gate = item['pilot_gate']
            print(f'Both strategies parseable and scored: {gate["paired_scored_cases"]}/12 cases; threshold 10; passed: {gate["passed"]}')
    budget = result['cumulative_budget']
    print(f'Cumulative accounted cost, including history: ${budget["accounted_spend_usd"]:.8f}; cumulative limit ${budget["authorized_total_usd"]:.2f}; remaining ${budget["remaining_usd"]:.8f}')
    print('The above is saved progress. Resuming will recheck the complete evidence and stage gates.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
