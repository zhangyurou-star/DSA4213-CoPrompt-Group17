"""Assemble only the two fresh authors' triplets; no old case data is read."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_text())
def save(name,obj):
 path=ROOT/name;path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def assemble():
 if (ROOT/'data/formal_freeze_v0.6.0.json').exists():
  raise SystemExit('This dataset is frozen. Do not regenerate it in place.')
 allocation=read('data/allocation_plan.json')
 rowgroups={d:read('work/'+d+'_rows.json') for d in ('writing','planning')}
 familyplans={d:read('work/'+d+'_family_plan.json') for d in ('writing','planning')}
 rows=[row for group in rowgroups.values() for row in group]
 assert len(rows)==120 and all(isinstance(r,list) and len(r)==3 for r in rows)
 byid={r[0]['case_id']:r for r in rows};assert len(byid)==120
 families=[f for p in familyplans.values() for f in p['families']]
 familybyid={f['case_id']:f for f in families}
 assert len(familybyid)==len({f['family_id'] for f in families})==120
 assert set(byid)==set(familybyid)=={p['case_id'] for p in allocation['cases']}
 cases=[];registry=[]
 for p in allocation['cases']:
  cid=p['case_id'];req,ans,ann=byid[cid];fam=familybyid[cid]
  assert all(r['case_id']==cid for r in (req,ans,ann))
  assert req['domain']==ann['domain']==p['domain']
  for k in ('split','omission_type'):assert ann['metadata'][k]==p[k]
  assert ann['metadata']['family_id']==fam['family_id']
  assert fam['split']==p['split'] and fam['omission_type']==p['omission_type']
  cases.append(dict(fam,**{k:v for k,v in p.items() if k not in fam}))
  registry.append({'family_id':fam['family_id'],'title_zh':fam['title_zh'],'domain':p['domain'],'split':p['split'],'case_ids':[cid]})
 for split in ('design','validation','test'):
  ids=[p['case_id'] for p in cases if p['split']==split]
  assert len(ids)=={'design':40,'validation':20,'test':60}[split]
  assert Counter(byid[c][0]['domain'] for c in ids)=={'constrained_writing':len(ids)//2,'study_planning':len(ids)//2}
  prefix='design_all' if split=='design' else split
  for index,(folder,kind) in enumerate((('public','requests'),('private','answers'),('private','annotations'))):
   target=ROOT/'data'/folder/f'{prefix}_{kind}.jsonl'
   target.write_text(''.join(json.dumps(byid[c][index],ensure_ascii=False)+'\n' for c in ids))
 plan=dict(allocation,cases=cases,assembled_utc=datetime.now(timezone.utc).isoformat(),status='all120_new_cases_assembled_before_model_outputs',author_family_plan_sha256={f'work/{d}_family_plan.json':digest(ROOT/f'work/{d}_family_plan.json') for d in familyplans})
 save('data/case_plan.json',plan)
 save('data/family_registry.json',{'version':'fresh120-0.6.0','registered_families':registry,'limitation':'One case per registered task family. Registration is a partitioning convention, not proof of semantic independence.'})
 return {'cases':len(cases),'families':len(registry),'split_counts':dict(Counter(p['split'] for p in cases))}

if __name__=='__main__':print(json.dumps(assemble(),ensure_ascii=False))
