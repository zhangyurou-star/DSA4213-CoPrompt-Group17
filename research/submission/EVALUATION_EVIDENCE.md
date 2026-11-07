# Evaluation evidence for the selected v0.6 study

This is a navigation and interpretation supplement to the saved experiment, prepared on 27 October 2026. Values below come from the uploaded package's `experiments/120_fresh_v0.6/outputs/fresh120_analysis/analysis.json` and are checked against the recorded trajectories. No new model experiment was run.

## Coverage and settings

| Item | Recorded evidence |
|---|---|
| Dataset | 120 cases: 40 design, 20 validation, 60 test; equal domain counts in each split |
| Main test | 60 matched cases × 4 policies = 240 trajectories |
| Diagnostic | Importance fixed to 1 on 20 preselected test cases = 20 additional trajectories |
| All stages | 480 logical trajectories, including pilot/design/validation |
| Model | `qwen/qwen3-30b-a3b-instruct-2507`, OpenRouter, fixed `nebius/fp8` route |
| Inference | temperature 0, top_p 1, seed 20261013 where supported |
| Asking | At most three requested information items; invalid requests also consume budget |
| Selection | Validation candidates 0, 0.25, 0.5; selected lambda **0.25** |
| Scoring | Mean passed fraction of registered critical hard constraints per case, averaged over cases |
| Uncertainty | 10,000 domain-stratified paired case-bootstrap resamples; 95% percentile intervals |

## Main test results

| Policy | Mean hard-constraint score | Mean questions | Total questions | Fully passing cases | Final format failures |
|---|---:|---:|---:|---:|---:|
| Direct | 0.7072 | 0.000 | 0 | 30/60 | 0 |
| Exhaustive | 0.7878 | 1.183 | 71 | 35/60 | 0 |
| Prompt-only | 0.7794 | 1.017 | 61 | 35/60 | 0 |
| Value-based | 0.7989 | 1.183 | 71 | 36/60 | 0 |

Values are rounded for reading. Full precision is in `evidence/policy_summary.csv` and the original analysis JSON. Zero format failures does not imply zero content or constraint failures.

| Paired contrast | Score difference [95% interval] | Mean question difference [95% interval] |
|---|---|---|
| Value-based − direct | +0.0917 [0.0306, 0.1569] | +1.183 [0.933, 1.450] |
| Value-based − exhaustive | +0.0111 [-0.0111, 0.0389] | 0.000 [0.000, 0.000] |
| Value-based − prompt-only | +0.0194 [-0.0236, 0.0625] | +0.167 [0.067, 0.283] |

The sampled cases support a higher hard-constraint score than direct generation at the cost of more questions. They do not establish a quality advantage over exhaustive or prompt-only, and they show **no question reduction against exhaustive**. An interval spanning zero is inconclusive, not evidence of equivalence. The diagnostic has zero score/question differences on its matched 20-case comparison; it is not independent confirmation of a benefit.

## Costs, failures and response reuse

The current 120-case study records 643 API attempts: 642 successes and one attempt with unconfirmed cost. Accounted study cost is **USD 0.08404924**, comprising USD 0.08305670 reported by the provider and approximately USD 0.00099254 conservatively reserved. The source ledger also contains USD 0.08857385 from earlier work, for a historical cumulative total of USD 0.17262309. Do not call the reserve a confirmed charge or the cumulative number the cost of this study alone.

The final test stage has 338 successful billed attempts in the saved accounting; logical trajectories and cache hits are not additional independent calls. Provider failures, reservations and first responses are retained in the source logs. The supplement makes zero API calls. Costs are by execution stage, not a fair per-policy cost ranking.

## Where to inspect evidence

- **All 260 test/diagnostic trajectories:** open `evidence/trace_viewer.html`. It displays the original request, saved ASK/ACT sequence, visible answers, final output, recorded score, extraction evidence and model drafts. Use the source line number and record hash to locate the original JSONL row.
- **Machine-readable outputs:** `evidence/system_outputs.csv` and `evidence/test_traces.json` contain all test/diagnostic records, including failures. There is no best-response selection.
- **Full stage records:** `../experiments/120_fresh_v0.6/runs/formal_v0.6.0_*/trajectories.jsonl` and their manifests.
- **Raw replies and cost logs:** caches and session JSONL files under the same experiment's `runs/` directory.
- **Original aggregate analysis:** `../experiments/120_fresh_v0.6/outputs/fresh120_analysis/analysis.json`.
- **New diagnostic calculation:** `build_evidence.py` and `evidence/diagnostics.json`; these only read saved records and use the original scorer.

## Boundaries of the evidence

One principal trajectory per case/system, a single hosted model and synthetic simulated users limit generalization. Bootstrap intervals represent case variation, not repeated model-sampling uncertainty; comparisons are not adjusted for multiplicity. Domain results are descriptive. Literal checks do not assess semantic adequacy or unsupported assumptions. Private annotations are used for offline scoring and diagnosis only.

The retained v0.6 generator performs the documented public-constraint revision and summary derivation. Their effects cannot be separated causally from this study alone; do not claim results for a format-repair-only pipeline. Human review, real-user satisfaction, unseen-model robustness and a live-model browser demonstration are not certified by these materials.

## Completed returned assessments supplied with this revision

The preceding automatic results and original analysis are unchanged. The subsequently completed returns and existing descriptive statistics are now in `../human_review/`; read its English README and unchanged source files. The existing human-informed case analysis is in `../case_analysis/case_error_analysis_en.md`. These additions do not certify review independence or blinding and add no new model experiment or rating. Historical pending-review fields remain in the original records.
