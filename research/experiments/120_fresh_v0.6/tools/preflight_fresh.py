"""Offline readiness check for the new 120-case experiment; never reads a key or calls a model."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from coprompt import formal


def verify_runtime_config(old_config, new_config):
    if (new_config.get('budget_authority') != '../../runs/authorized_pilot_budget.json'
            or 'authorized_total_budget_usd' in new_config):
        raise ValueError('Only the original cumulative ledger may authorize spending')
    metadata = {'status', 'setup_change_note', 'authorized_total_budget_usd', 'budget_authority',
                'authorized_total_budget_usd_at_preparation', 'authorization_note', 'experiment_version'}
    if {k: v for k, v in old_config.items() if k not in metadata} != {k: v for k, v in new_config.items() if k not in metadata}:
        raise ValueError('Fresh experiment must preserve the frozen v0.4 inference settings')


def preflight(root=ROOT):
    root = Path(root).resolve()
    freeze_path = root / 'data/formal_freeze_v0.6.0.json'
    freeze = formal.load(freeze_path)
    formal.verify_freeze(root, freeze)
    if not formal.required_frozen_files().issubset(freeze['files']):
        raise ValueError('The freeze is missing fresh data, settings, or runtime/method sources')
    plan = formal.verify_case_plan(root, freeze)
    formal.verify_isolated_caches(root, formal.file_hash(freeze_path))
    datasets = {split: formal.load_dataset(root, split) for split in ('design_all', 'validation', 'test')}
    jobs = {stage: formal.planned_jobs(stage, formal.load_dataset(root, stage)[0],
            .25 if stage != 'validation' else None, plan['diagnostic_case_ids']) for stage in formal.STAGES}
    for name in formal.METHOD_MODULES:
        if formal.file_hash(root / f'coprompt/{name}.py') != formal.file_hash(formal.PROJECT_ROOT / f'coprompt/{name}.py'):
            raise ValueError('The inherited v0.4 method changed: ' + name)
    static_method_files = ('data/public/field_catalog.json',
                           'data/schemas/output_constrained_writing.schema.json',
                           'data/schemas/output_study_planning.schema.json')
    for name in static_method_files:
        if formal.file_hash(root / name) != formal.file_hash(formal.PROJECT_ROOT / name):
            raise ValueError('The inherited field catalog or output schema changed: ' + name)
    old_config = formal.load(formal.PROJECT_ROOT / 'config/openrouter.v0.4.formal.json')
    new_config = formal.load(root / 'config/openrouter.v0.6.formal.json')
    verify_runtime_config(old_config, new_config)
    with formal.FreshBudgetLedger(formal.CUMULATIVE_LEDGER, root) as ledger:
        formal.verify_registered_stage_sessions(root, ledger)
        budget = {'path': str(formal.CUMULATIVE_LEDGER), 'authorized_total_usd': float(ledger.authorized),
                  'accounted_spend_usd': float(ledger.spent), 'remaining_usd': float(ledger.authorized - ledger.spent),
                  'reconciled_session_logs': len(ledger.document['source_session_logs']),
                  'recovered_fresh_budget_transaction': ledger.recovered_transaction}
    return {'status': 'offline_preflight_passed', 'api_calls': 0,
            'case_counts': {split: len(data[0]) for split, data in datasets.items()},
            'stage_order': list(formal.STAGES), 'pilot_case_ids': list(formal.PILOT_IDS),
            'planned_trajectories': {stage: len(value) for stage, value in jobs.items()},
            'design_total_trajectories': sum(len(jobs[stage]) for stage in formal.STAGES[:3]),
            'test_main_trajectories': 240, 'test_diagnostic_trajectories': 20,
            'test_lambda': 'Selected only from the complete new 20-case validation across all three candidates.',
            'pilot_gate': 'At least 10 of 12 cases have both direct and exhaustive final outputs parsed and scored; quality need not equal 1.',
            'unchanged_method_modules': list(formal.METHOD_MODULES),
            'unchanged_method_data': list(static_method_files),
            'cache_scope': 'Fresh experiment only; starts empty; exact first responses may be reused internally.',
            'cumulative_budget': budget,
            'caution': 'Readiness does not imply the remaining cumulative budget can finish every trajectory.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(preflight(), ensure_ascii=False, indent=2))
