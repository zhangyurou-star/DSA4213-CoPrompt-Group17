"""Read-only coordinator check against prior authored data, never prior outcomes.

Uses exact request identity and text similarity to flag possible duplicates.
Similarity is a screening measure, not a semantic-independence certificate.
"""
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]

def read_rows(base):
 rows=[]
 for prefix in ('design_all','validation','test'):
  public=[json.loads(x) for x in (base/f'data/public/{prefix}_requests.jsonl').read_text().splitlines() if x.strip()]
  annotations={r['case_id']:r for r in (json.loads(x) for x in (base/f'data/private/{prefix}_annotations.jsonl').read_text().splitlines() if x.strip())}
  for row in public:
   row=dict(row);row['audit_family']=annotations[row['case_id']]['metadata']['family_id'];row['audit_split']=annotations[row['case_id']]['metadata']['split'];rows.append(row)
 return rows

def normalize(text):return ' '.join(re.findall(r"[a-z]+(?:'[a-z]+)?|\d+",text.casefold()))
def shingles(text,size=5):
 tokens=normalize(text).split();return set(zip(*(tokens[i:] for i in range(size))))
def similarity(a,b):
 aa,bb=shingles(a),shingles(b);return len(aa&bb)/len(aa|bb) if aa|bb else 0

def main():
 fresh=read_rows(ROOT)
 prior=read_rows(PROJECT/'experiments/120_v0.5')
 assert len(fresh)==len(prior)==120
 exact=[(n['case_id'],p['case_id']) for n in fresh for p in prior if normalize(n['initial_request'])==normalize(p['initial_request'])]
 duplicate_new=[(a['case_id'],b['case_id']) for i,a in enumerate(fresh) for b in fresh[i+1:] if normalize(a['initial_request'])==normalize(b['initial_request'])]
 oldfamilies={r['audit_family'] for r in prior}
 family_overlap=sorted({r['audit_family'] for r in fresh}&oldfamilies)
 assert not exact and not duplicate_new and not family_overlap
 closest=[]
 for n in fresh:
  candidates=[p for p in prior if p['domain']==n['domain']]
  p=max(candidates,key=lambda p:similarity(n['initial_request'],p['initial_request']))
  closest.append({'new_case_id':n['case_id'],'prior_case_id':p['case_id'],'new_family':n['audit_family'],'prior_family':p['audit_family'],'five_word_jaccard':round(similarity(n['initial_request'],p['initial_request']),5)})
 cross=[]
 for i,a in enumerate(fresh):
  for b in fresh[i+1:]:
   if a['audit_split']!=b['audit_split'] and a['domain']==b['domain']:
    cross.append({'a':a['case_id'],'b':b['case_id'],'a_family':a['audit_family'],'b_family':b['audit_family'],'five_word_jaccard':round(similarity(a['initial_request'],b['initial_request']),5)})
 report={'created_utc':datetime.now(timezone.utc).isoformat(),'status':'exact_reuse_checks_passed_similarity_flags_for_coordinator_review','api_calls':0,'prior_reference':'Discarded80+40 dataset, including all original80 and additional40; data texts only, no model outcomes.','new_case_count':120,'prior_reference_case_count':120,'exact_normalized_prior_request_matches':exact,'exact_normalized_within_fresh_request_matches':duplicate_new,'prior_family_id_overlap':family_overlap,'new_id_count':len({r['case_id'] for r in fresh}),'fresh_registered_family_count':len({r['audit_family'] for r in fresh}),'newness_scope':'Initial requests and registered family identities checked. Common field values, schema, English instruction phrases and constraint types may repeat legitimately.','nearest_prior_pairs':sorted(closest,key=lambda x:-x['five_word_jaccard'])[:20],'nearest_cross_split_pairs':sorted(cross,key=lambda x:-x['five_word_jaccard'])[:20],'limitations':['Text similarity is only a duplicate screen; changing family IDs alone is not enough.','Task families share domain-level templates; this check does not prove independent sampling or zero semantic overlap.','Coordinator may examine new data against prior texts to check reuse, but does not use performance outcomes for replacement or split selection.']}
 out=ROOT/'work/newness_audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('nearest_prior_pairs','nearest_cross_split_pairs','limitations')},ensure_ascii=False))
 print(json.dumps({'top_prior':report['nearest_prior_pairs'][:3],'top_cross_split':report['nearest_cross_split_pairs'][:3]},ensure_ascii=False))

if __name__=='__main__':main()
