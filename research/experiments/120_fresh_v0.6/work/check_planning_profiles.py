"""Detect exact normalized planning contracts, not general semantic independence."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import json
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'work/planning_rows.json').read_text())
plans={f['case_id']:f for f in json.loads((ROOT/'work/planning_family_plan.json').read_text())['families']}
groups=defaultdict(list)
for req,ans,ann in rows:
 rules=[{k:v for k,v in rule.items() if k!='constraint_id'} for rule in ann['constraints']]
 identity={'rules':rules,'fields':ann['field_annotations'],'control':req['user_control'],'answer_statuses':{k:v['status'] for k,v in ans['answers'].items()}}
 encoded=json.dumps(identity,sort_keys=True)
 for i,topic in sorted(enumerate(plans[req['case_id']]['topics']),key=lambda pair:-len(pair[1])):
  encoded=encoded.replace(topic,f'<topic{i}>')
 groups[encoded].append({'case_id':req['case_id'],'split':ann['metadata']['split']})
duplicates=[v for v in groups.values() if len(v)>1]
report={'created_utc':datetime.now(timezone.utc).isoformat(),'status':'passed' if not duplicates else 'duplicate_contracts','cases':60,'unique_normalized_contracts':len(groups),'duplicate_groups':duplicates,'normalization':'Replace each case topic label by its ordinal position; retain complete hard-rule parameters/source fields/source stages, field states and criticality, control and answer statuses.','correction_record':'work/data_corrections_before_freeze.json','limitation':'No exact normalized duplicates does not remove shared task templates or establish semantic/statistical independence.','api_calls':0}
(ROOT/'work/planning_profile_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
if duplicates:raise SystemExit(1)
