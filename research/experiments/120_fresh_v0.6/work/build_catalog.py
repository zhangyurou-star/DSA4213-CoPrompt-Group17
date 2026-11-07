"""Readable catalog of new initial requests; no hidden answers or model outputs."""
from pathlib import Path
from collections import Counter
import json
ROOT=Path(__file__).resolve().parents[1]
plan=json.loads((ROOT/'data/case_plan.json').read_text())
titles=json.loads((ROOT/'data/case_titles_en.json').read_text())
public={r['case_id']:r for prefix in ('design_all','validation','test') for r in (json.loads(line) for line in (ROOT/f'data/public/{prefix}_requests.jsonl').read_text().splitlines() if line)}
splits={'design':'Design','validation':'Validation','test':'Test'}
domains={'constrained_writing':'Constrained writing','study_planning':'Study planning'}
omissions={'complete':'Complete information','critical_omission':'Critical field omitted','critical_and_optional':'Critical and optional fields omitted','optional_only':'Only optional fields omitted','unavailable_answer':'Answer unavailable','execute_now':'Execute immediately'}
lines=['CoPrompt Fresh 120-Case Catalog','','New case inventory and initial requests; this is not a results report. All English requests were newly authored for this study, with reference date 2027-02-01.','40 design / 20 validation / 60 test cases; each split has equal numbers from the two domains. The 12 pilot cases are included in the design split; the 20 diagnostic cases are included in the test split.','This catalog does not display hidden scoring answers or author-provided feasible examples.','']
for split in splits:
 entries=[e for e in plan['cases'] if e['split']==split];counts=Counter(e['omission_type'] for e in entries)
 lines += [f'{splits[split]} split: {len(entries)} cases',' / '.join(f'{omissions[k]} {counts[k]}' for k in omissions),'']
 for e in entries:
  cid=e['case_id'];marks=[]
  if cid in plan['pilot_case_ids']:marks.append('Included in the 12-case pilot')
  if cid in plan['diagnostic_case_ids']:marks.append('Included in the 20-case diagnostic subset')
  lines += [f"{cid}  {titles[cid]}  | {domains[e['domain']]} | {omissions[e['omission_type']]}"+(' | '+', '.join(marks) if marks else ''),f"Family: {e['family_id']}",public[cid]['initial_request'],'']
(ROOT/'data/case_catalog.txt').write_text('\n'.join(lines)+'\n')
print('Readable catalog:120 cases.')
