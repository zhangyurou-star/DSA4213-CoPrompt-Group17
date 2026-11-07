"""Offline planning estimate, not authority or an upper bound; no API access."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
source=PROJECT/'work/expand120_budget_audit.json'
old=json.loads(source.read_text())
ledger=json.loads((PROJECT/'runs/authorized_pilot_budget.json').read_text())
case=old['historical_per_case_cost_at_price_caps_including_unknown_failure_reserves']
stage=old['formal_stage_cost_statistics_at_price_caps']
scenarios={}
for name,quant,design_factor,formal_factor in [('low','p25_usd',1,1),('middle','mean_usd',1.25,1.10),('stress','p90_usd',1.35,1.20)]:
 base_test=sum(case['test'][d][quant] for d in ('CW','SP'))
 base_val=sum(case['validation'][d][quant] for d in ('CW','SP'))
 design=20*base_test*design_factor
 validation=10*base_val*formal_factor
 test=30*base_test*formal_factor
 if name=='low': diagnostic=0;reserve=0
 elif name=='middle':
  diagnostic=20*(stage['value_decision']['mean_cost_at_caps_usd']+.5*stage['generation']['mean_cost_at_caps_usd']+.5*(21/92)*stage['constraint_repair']['mean_cost_at_caps_usd'])*1.10
  reserve=0
 else:
  diagnostic=20*(2*stage['value_decision']['p90_cost_at_caps_usd']+stage['generation']['p90_cost_at_caps_usd']+stage['constraint_repair']['p90_cost_at_caps_usd'])
  reserve=(design+validation+test+diagnostic)*.05
 total=design+validation+test+diagnostic+reserve
 scenarios[name]={'new_design40_all_four_policies_including_pilot_usd':round(design,8),'new_validation20_three_thresholds_usd':round(validation,8),'new_test60_four_policies_usd':round(test,8),'additional_diagnostic20_allowance_usd':round(diagnostic,8),'additional_failure_and_repair_stress_reserve_usd':round(reserve,8),'additional_accounted_usd':round(total,8),'projected_cumulative_accounted_usd':round(ledger['accounted_spend_usd']+total,8),'within_current_cap_in_this_scenario':ledger['accounted_spend_usd']+total<=ledger['authorized_total_usd']}
report={'created_utc':datetime.now(timezone.utc).isoformat(),'status':'offline_forecast_not_guarantee_or_spending_authorization','scope':'All120 newly authored; no historical case or cached-response reuse. Pilot12 is inside40 design, not added twice. Exact first-response reuse within fresh study is expected but not guaranteed.','model':old['model'],'history_used_for':'Cost planning only, not case selection or method tuning. Historical small-sample and previously cached operation may underestimate fresh-case needs.','source_cost_statistics_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'authorized_cumulative_total_usd':ledger['authorized_total_usd'],'prior_accounted_usd':ledger['accounted_spend_usd'],'remaining_usd':round(ledger['authorized_total_usd']-ledger['accounted_spend_usd'],8),'scenarios':scenarios,'assumptions_en':['Historical within-domain cost statistics are used only for cost estimation. No cases or responses are inherited; all 120 cases require new requests.','The low scenario uses the lower quartile of per-case cost and assumes complete internal reuse for diagnostics. The middle scenario uses the mean, adding 25% for design and 10% for validation/test, with one decision call and half a generation-and-repair allowance per diagnostic case.','The stress scenario uses per-case p90 times 1.35 for design or 1.2 for formal stages, adds two decision calls, one generation, and one constraint repair per diagnostic case, and adds a further 5% for failures and repairs. It is not the 90th percentile of total cost, a confidence interval, or a strict upper bound.','Historical test costs aggregated by case may include diagnostic costs, so the additional diagnostic allowance partly duplicates costs conservatively. New request length, thresholds, retries, actual provider rates, and internal cache hits all affect cost.','At forecast preparation time, the remaining USD 0.16142615 might cover the middle scenario, but completion was not guaranteed. The program enforced the then-authorized cumulative USD 0.25 limit before each request and saved progress and stopped when funds were insufficient; it never automatically raised or reset the limit.','Only offline scripts were run: no network access, no key reading, and no additional API spending.']}
(ROOT/'work/budget_forecast.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('prior_accounted_usd','remaining_usd','scenarios')},ensure_ascii=False))
