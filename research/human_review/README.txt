CoPrompt completed human-assessment evidence
Existing records and statistics, assembled into this package on 28 October 2026.

Coverage: 20 preselected test cases x five variants x two reviewers = 100 outputs and 200 assessments. The diagnostic is not an independent sample.

Read statistics.json for full precision, system_summary.csv for means, agreement.csv for agreement, paired_ratings.csv for original pairs, and inputs/reviewer_1_returned.json plus reviewer_2_returned.json for the unchanged returns.

Descriptive means: usefulness / coherence / audience fit / feasibility / unsupported-assumption count / unnecessary-question count.
direct: 4.425 / 4.675 / 4.600 / 4.525 / 0.075 / 0.075
exhaustive: 4.400 / 4.675 / 4.550 / 4.475 / 0.075 / 0.450
prompt_only: 4.475 / 4.750 / 4.675 / 4.600 / 0.075 / 0.450
value_based: 4.400 / 4.675 / 4.575 / 4.475 / 0.075 / 0.450
importance_one: 4.400 / 4.675 / 4.575 / 4.475 / 0.075 / 0.450

Linear weighted kappa and exact agreement, per 100 paired outputs:
usefulness_1_to_5: kappa 0.7906; exact agreement 84%.
coherence_1_to_5: kappa 0.9227; exact agreement 96%.
audience_fit_1_to_5: kappa 0.5992; exact agreement 75%.
feasibility_1_to_5: kappa 0.7305; exact agreement 80%.

Prompt-only has the highest descriptive mean in the four content dimensions on this subset. Value-based has no demonstrated content-rating advantage. These means and agreement do not establish a population-level strategy ranking. No composite score or new hypothesis test is added.

Reviewer declarations do not certify unaided independence or actual blinding.

R2-002 reports three unnecessary questions for Direct despite an empty trace. The original count remains in every statistic; it is not evidence that Direct asked questions. Read validation_receipt.json and statistics.json for the recorded warnings. No adjudication or score correction was performed.

Source integrity: source_manifest.json lists the seven unchanged input copies. Original Chinese notes and dimension labels remain in the source and computed tables. This English guide replaces the need to read the earlier Chinese narrative summary; it does not replace original evidence.

Optional reproduction: copy this entire folder to a new external working folder, then run python3 -B reproduce_statistics.py in that copy. It rebuilds numeric summaries in its own folder; do not run it in the submitted evidence directory. No model calls or rating changes are made.

The earlier experiment analysis and verifier can still say review pending. That historical state is retained; the completed returned evidence is supplied here rather than rewriting that record.
