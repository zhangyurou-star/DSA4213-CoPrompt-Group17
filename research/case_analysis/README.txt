CoPrompt: Case Error Analysis
Date: 2026-10-27, Asia/Singapore

Read case_error_analysis_en.md for the existing English report section.
The earlier Chinese narrative is not included in this submission-facing folder.

Scope: the existing 60 test cases x four main systems, the original
20-case importance diagnostic, and the two returned assessments of
100 outputs. All eight illustrations come from that same 20-case
human-review subset. They were selected after inspecting results to
explain mechanisms; their composition is not an error-prevalence estimate.

No new model calls, cases, thresholds, scores, gold labels, significance
tests or adjudication were introduced. Existing scores and all reviewer
comments, including disagreement and the R2-002
count anomaly, remain unchanged. The analysis does not modify the earlier
human-review statistics package.

Tables:
  main_test_summary.csv: four policies, 60 cases each.
  constraint_failures.csv: failures and denominators for existing checks.
  domain_summary.csv: descriptive results only.
  main_trajectory_index.csv: all 240 main trajectories.
  case_comparison.csv: all five variants for the eight illustrations.
  human_review_evidence.csv: all 200 returned assessments and notes.

Evidence:
  selected_case_evidence.json: 40 full saved trajectories and their reviews.
  findings.json: full-precision results and interpretation boundaries.
  validation_receipt.json: scope and consistency verification.
  inputs/: unchanged source copies.
  source_manifest.json: source paths and SHA-256 fingerprints.

The included private mappings, unasked answers and reviewer identities
are for project-coordinator verification. Unasked answers were used only
to explain offline benchmark scoring, not to change visible-context human
assessments or model states.

Optional numeric reproduction requires Python 3.10+ and no third-party
packages. From this folder run:
  python3 -B reproduce_analysis.py

The program checks source hashes, reconstructs numeric tables and evidence
indices, and verifies the saved primary results against the prior analysis.
It does not generate or rewrite the qualitative reports.

Packaging note (28 October 2026): source inputs, scores, returned ratings, numeric results and analysis code were copied unchanged. Some inputs are duplicated with the experiment or human-review folder so each original reproduction script keeps its relative paths and source hashes. Run reproduction only in an external working copy.
