"""Freeze the prepared fresh study exactly once, before actual model execution."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from coprompt.formal import required_frozen_files, verify_case_plan

def main():
 target=ROOT/'data/formal_freeze_v0.6.0.json'
 if target.exists():raise SystemExit('Freeze already exists; never silently replace it.')
 if (ROOT/'runs').exists() and any((ROOT/'runs').rglob('*')):
  raise SystemExit('Fresh study must be frozen before any run/cache evidence.')
 plan=json.loads((ROOT/'data/case_plan.json').read_text())
 freeze={'version':'0.6.0','experiment_id':'fresh120-v0.6.0','frozen_utc':datetime.now(timezone.utc).isoformat(),'status':'frozen_before_pilot_outputs','pilot_case_ids':plan['pilot_case_ids'],'diagnostic_case_ids':plan['diagnostic_case_ids'],'selected_lambda':None,'files':{},'method_source':'Unchanged v0.4 inference modules; new scheduler, data, cache scope and analysis.','budget_note':'Budget ledger remains the original live cumulative ledger and is deliberately not frozen here.','data_history':'All120 newly authored; original80 and discarded40 excluded. Coordinator historical knowledge disclosed in protocol.'}
 verify_case_plan(ROOT,freeze)
 paths=[]
 for folder in ('data','config','coprompt','tools','tests','work'):
  paths += [p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.py','.json','.jsonl','.txt') and '__pycache__' not in p.parts and p != target]
 paths += [ROOT/'README.txt', ROOT/'run_fresh120.command']
 for p in sorted(set(paths)):
  freeze['files'][str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
 if not required_frozen_files().issubset(freeze['files']):raise SystemExit('Required frozen inputs missing')
 with target.open('x') as f:f.write(json.dumps(freeze,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':freeze['status'],'frozen_files':len(freeze['files']),'pilot_cases':len(plan['pilot_case_ids']),'diagnostic_cases':len(plan['diagnostic_case_ids'])}))

if __name__=='__main__':main()
