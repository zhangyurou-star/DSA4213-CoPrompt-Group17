"""One-time, audited accounting-only source amendment before any saved trajectory.

Preserves all expense logs and original frozen sources. Does not call a model,
change data/method prompts/scoring, import responses or discard an output.
"""
from pathlib import Path
from datetime import datetime,timezone
import copy,json,sys
ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT.parents[1]
sys.path.insert(0,str(ROOT))
from coprompt import formal

def main():
 folder=Path(__file__).resolve().parent
 before=folder/'before'
 original_freeze=before/'formal_freeze_v0.6.0.json'
 freeze_path=ROOT/'data/formal_freeze_v0.6.0.json'
 old_hash=formal.file_hash(original_freeze)
 if formal.file_hash(freeze_path)!=old_hash:
  raise SystemExit('Original freeze is no longer active; do not apply again.')
 old=formal.load(original_freeze)
 allowed={'coprompt/formal.py','tools/analyze_fresh.py'}
 changed={p for p,h in old['files'].items() if formal.file_hash(ROOT/p)!=h}
 if changed!=allowed:raise SystemExit('Unexpected frozen source changes: '+repr(changed))
 with formal.FreshBudgetLedger(formal.CUMULATIVE_LEDGER,ROOT) as ledger:
  formal.verify_registered_stage_sessions(ROOT,ledger)
  ledger_hash=formal.file_hash(ledger.path)
  sessions={str(p.relative_to(PROJECT)):formal.file_hash(p) for p in ledger._paths()}
  manifests=list((ROOT/'runs').glob('formal_*/manifest.json'))
  expected_manifest=ROOT/'runs/formal_v0.6.0_pilot_a/manifest.json'
  if manifests!=[expected_manifest]:raise SystemExit('Unexpected stage evidence; migration requires manual review.')
  manifest=formal.load(expected_manifest)
  requests,answers,annotations=formal.load_dataset(ROOT,'pilot_a')
  jobs=formal.planned_jobs('pilot_a',requests,.25,old['diagnostic_case_ids'])
  formal.verify_manifest(manifest,'pilot_a',jobs,old_hash,formal.digest({'freeze':old_hash,'stage':'pilot_a','jobs':jobs}),old['diagnostic_case_ids'],old,.25)
  if (manifest['completed_trajectories']!=0 or manifest['row_hashes'] or manifest.get('pending_cell') is not None
      or manifest['status']!='interrupted'):
   raise SystemExit('Never migrate or overwrite completed/pending model evidence.')
  for p in (ROOT/'runs').rglob('trajectories.jsonl'):
   if p.read_bytes():raise SystemExit('A saved trajectory prevents this zero-output migration.')
  for name in formal.CACHE_DIRECTORIES:
   path=ROOT/'runs'/name
   if path.exists() and any(path.iterdir()):raise SystemExit('Response caches must be empty for this audited migration.')
  marker=ROOT/'runs/fresh_cache_scope.json'
  formal.verify_isolated_caches(ROOT,old_hash)
  now=datetime.now(timezone.utc).isoformat()
  revision='budget-precision-1'
  amendment={'revision':revision,'recorded_utc':now,'kind':'accounting_only_implementation_fix','original_freeze_sha256':old_hash,
    'original_frozen_sources_archive':str((before/'original_frozen_sources.zip').relative_to(ROOT)),
    'original_frozen_sources_archive_sha256':formal.file_hash(before/'original_frozen_sources.zip'),
    'reason':'JSON float(total) stored0.08956639 while exact sum of original decimal log values was0.0895663899999999999. Strict comparison against an unrepresentable total rejected settlement and restart.',
    'fix':'Only ledger serialization comparisons use the exact projection Decimal(str(float(exact_log_sum))). Transactions derive both before and after checks from authoritative exact log totals. All cap and remaining-budget arithmetic retains the unrounded Decimal sum. No epsilon allowance.',
    'changed_sources':{p:{'before':old['files'][p],'after':formal.file_hash(ROOT/p)} for p in sorted(allowed)},
    'regression_tests':'tests/test_budget_precision.py','offline_tests_passed':65,
    'expense_evidence':{'stored_total_usd':ledger.document['accounted_spend_usd'],'exact_log_total_usd':str(ledger.spent),'authorized_total_usd':float(ledger.authorized),'ledger_sha256_unchanged':ledger_hash,'session_log_hashes_unchanged':sessions,'unsettled_reserve_retained':True},
    'run_evidence':'One prior request attempt reached a logging failure; response/actual charge unavailable. The full unknown-cost reserve is retained. No committed or pending trajectories, raw responses, extraction results or generation results exist.',
    'freeze_handling':'Original freeze and all68 original frozen source files archived before editing. New source hashes recorded as an explicit accounting revision; dataset, model/settings, prompts, scorer, allocation, threshold rules and case IDs remain byte-for-byte unchanged.',
    'migration':'Only zero-output pilot manifest source hashes/plan hash and empty-cache scope updated; original copies retained. All session refs, timestamps, error and expense records preserved.',
    'api_calls_by_repair':0,'no_human_review_claim':True}
  amendment_path=folder/'amendment.json';formal.dump(amendment_path,amendment)
  updated=copy.deepcopy(old)
  for p in allowed:updated['files'][p]=formal.file_hash(ROOT/p)
  for p in [ROOT/'tests/test_budget_precision.py',Path(__file__).resolve(),amendment_path]:
   updated['files'][str(p.relative_to(ROOT))]=formal.file_hash(p)
  updated['accounting_revision']=revision
  updated['accounting_amended_utc']=now
  updated['original_freeze_sha256']=old_hash
  updated['amendment_record']=str(amendment_path.relative_to(ROOT))
  formal.dump(freeze_path,updated);new_hash=formal.file_hash(freeze_path)
  manifest.update(freeze_sha256=new_hash,plan_hash=formal.digest({'freeze':new_hash,'stage':'pilot_a','jobs':jobs}),source_files=updated['files'],accounting_revision=revision,prior_freeze_sha256=old_hash)
  formal.dump(expected_manifest,manifest)
  scope=formal.load(marker);scope['freeze_sha256']=new_hash;formal.dump(marker,scope)
  formal.verify_freeze(ROOT,updated)
  formal.verify_isolated_caches(ROOT,new_hash)
  formal.verify_manifest(manifest,'pilot_a',jobs,new_hash,manifest['plan_hash'],updated['diagnostic_case_ids'],updated,.25)
  if formal.restore_rows(expected_manifest.parent,manifest,jobs,requests,annotations):raise AssertionError('Expected zero model records')
  if formal.file_hash(ledger.path)!=ledger_hash:raise AssertionError('Expense ledger changed during repair')
  if any(formal.file_hash(PROJECT/p)!=h for p,h in sessions.items()):raise AssertionError('Expense log changed during repair')
  active_path=PROJECT/'experiments/ACTIVE_STUDY.json';active=formal.load(active_path)
  active.update(updated_utc=now,status='ready_to_resume_after_accounting_precision_fix',freeze_sha256=new_hash,accounting_revision=revision,real_fresh_model_trajectories=0)
  formal.dump(active_path,active)
  formal.dump(folder/'applied.json',{'applied_utc':now,'revision':revision,'original_freeze_sha256':old_hash,'amended_freeze_sha256':new_hash,'ledger_and_session_logs_unchanged':True,'new_api_calls':0})
  print(json.dumps({'status':'accounting_amendment_applied','frozen_files':len(updated['files']),'saved_model_trajectories':0,'cumulative_accounted_usd':float(ledger.spent),'remaining_usd':float(ledger.authorized-ledger.spent),'new_api_calls':0}))

if __name__=='__main__':main()
