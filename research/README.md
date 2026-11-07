# Group 17 CoPrompt v0.6 research artifacts

This package contains the completed experiment's code, saved outputs, evaluation evidence, returned human assessments and existing case analysis. The 28 October 2026 revision improves navigation and documentation and adds already completed evidence. It does not change experimental code, prompts, data, model outputs, scores, thresholds or results. No new model requests or reviewer ratings were generated.

The presentation PDF and UI5.1 r4 Streamlit demo are separate artifacts. The HTML viewer here displays saved research trajectories; it is not the Streamlit demo or live generation. `README.txt` is a retained historical handoff guide. Use this README for the current workflow.

## Start with the evidence

Extract the whole ZIP and keep its directory structure. These paths are relative to the extracted root:

1. Open `submission/evidence/trace_viewer.html` in a desktop browser. It is a self-contained viewer for 240 main-test and 20 diagnostic trajectories. Select a domain, system and case to inspect the request, saved questions, replies, final output, score and source line. No server, API key or installation is required for this file.
2. Read `submission/EVALUATION_EVIDENCE.md` for the original results and interpretation boundaries, and `submission/ERROR_ANALYSIS.md` for the post-hoc automatic diagnostics.
3. Read `human_review/README.txt`, then `human_review/statistics.json`, `system_summary.csv` and `agreement.csv`. The two original returned JSONs are in `human_review/inputs/`.
4. Read `case_analysis/case_error_analysis_en.md` for the previously completed analysis combining saved results and returned assessments. Its tables, full selected records and unchanged reproduction inputs are alongside it.
5. Use `delivery/DIRECTORY_GUIDE_EN.txt` for every directory and `delivery/FILE_INVENTORY_EN.txt` or `FILE_INVENTORY.json` for every delivered file. `delivery/FILE_REVIEW_EN.txt` distinguishes necessary files, optional historical records and duplicate copies.

## Check integrity first

Open a terminal in this extracted root, the folder containing `submission.py`. Run:

macOS, Linux or Windows WSL:

```sh
python3 --version
python3 -B submission.py verify
```

Native Windows PowerShell or Command Prompt:

```powershell
py -3.12 --version
py -3.12 -B submission.py verify
```

Python 3.12 or 3.13 is recommended. Use an installed interpreter explicitly if `python3` or `py` points elsewhere. The offline Python commands use the standard library; no `pip install`, GPU, notebook or credential is needed. See `submission/requirements.txt`.

A successful integrity check returns `english_handoff_hashes_verified` and a final `submission_files_verified` count. The historical source manifest checks 1,179 entries; the current submission count includes the added review and case evidence. A successful hash check is not a certificate of scientific correctness or a Windows test.

## Reproduce the saved experiment offline

From the root, on macOS, Linux or WSL:

```sh
python3 -B submission.py reproduce
```

This uses temporary copies to run the original and English-edition 65-test suites, replay scoring and the existing analysis, check 120 cases and 480 logical trajectories, and retain lambda 0.25. These are two runs of the same 65 tests, not 130 independent tests or new model experiments. The delivered files are not rewritten.

The historical verifier can still print `human_review: pending_actual_reviewers`. That field describes the earlier experiment snapshot. The subsequently returned assessments and their completed statistics are now supplied separately under `human_review/`; the old evidence and verifier have not been rewritten to make history appear different.

The original full-reproduction runtime imports `fcntl`. Native Windows supports the integrity-only `verify` entry; use WSL, macOS or Linux for `reproduce`. Actual environments checked for this revision are recorded in `delivery/VALIDATION_SUMMARY.json`; native Windows and Linux/WSL are not certified as executed environments here.

## Inspect or export without changing the submission

From the root, with a supported interpreter:

```sh
python3 -B submission.py inspect --case NTSP13 --system value_based
python3 -B submission.py export --out ../coprompt_evidence_export
python3 -B submission.py reproduce --out ../coprompt_recomputed_analysis
python3 -B -m unittest discover -s submission/tests -v
```

The two output folders must not already exist. Exports create separate copies of derived evidence, not new model results. Existing destinations are refused. Run `python3 -B submission.py --help` for all options. The optional `verify_package.command` is a retained macOS helper; the explicit commands above are the documented entry.

## Reproduce the completed review and case summaries

Both evidence folders contain their original source manifests, unchanged input copies and standard-library reproduction scripts. Each script rebuilds derived summaries inside its own folder. To keep the submitted copies unchanged, first copy the whole evidence folder to a new working folder outside this package.

In a disposable copy of `human_review/`, run:

```sh
python3 -B reproduce_statistics.py
```

In a disposable copy of `case_analysis/`, run:

```sh
python3 -B reproduce_analysis.py
```

These recompute existing numeric summaries from supplied records. They do not call a model, change ratings, resolve disagreements or generate a new qualitative analysis. Some original tables, metadata, comments and returns contain Chinese; their saved bytes are retained. The current reader guides and English case report are the submission-facing explanations.

## Study and interpretation boundaries

The two domains are constrained writing and study planning. The dataset has 40 design, 20 validation and 60 test cases. Four main policies share extraction and generation: Direct, Exhaustive, Prompt-only and Value-based. Importance=1 is a diagnostic on 20 of the test cases. Cache reuse means 480 logical trajectories are not 480 independent model samples.

The selected threshold is lambda 0.25 and the question cap is three. The actual hosted model is Qwen3-30B-A3B-Instruct-2507 on the recorded OpenRouter provider route. Full settings are in `experiments/120_fresh_v0.6/config/openrouter.v0.6.formal.json` and the method documents.

Value-based has the highest mean registered hard-constraint score in the 60-case test, but the evidence does not establish an advantage over the two asking baselines or question savings over Exhaustive. Hard-constraint scores do not measure overall quality or real-user satisfaction. Preserve all failures and uncertainty qualifications.

The retained method includes documented public-constraint revision and derived plan summaries in addition to format repair. These are historical departures from the original proposal, shared across policies; this delivery does not add or hide them. The trace viewer separates saved final outputs from drafts and processing records.

The human-assessment subset contains 20 cases, five variants, 100 outputs and 200 assessments. The retained R2-002 unnecessary-question count conflicts with its empty Direct trace; it is flagged, not corrected. See `human_review/README.txt` for descriptive means and agreement.

## Source identity and changes

Three identities must be distinguished:

- The historical source inventory `submission/provenance/input_files.json` describes an earlier 1,180-file input with archive SHA-256 `c8e0dcfef7de7485d4f96c277092ccbdcf71be75448ed3c627d318763b9db27d`.
- The Windows-verification-fixed ZIP supplied for this revision has SHA-256 `be838170593a97734946cba007889115cfcaacd3b484c3699e9bcd8f638f7e07`. Compared with that historical inventory, 1,178 files match. `PACKAGE_MANIFEST.json` and `handoff/verify_handoff.py` differ. They must not be described as all 1,180 original files being unchanged.
- This 28 October documentation/evidence revision retains that supplied ZIP's experiment and verifier bytes. Only the documented submission guides and current `SUBMISSION_MANIFEST.json` are changed; existing review/case evidence and role guides are added. `delivery/SOURCE_PRESERVATION.json` lists every source-file treatment. No source files are deleted.

`PACKAGE_MANIFEST.json`, the freeze files, `LOCALIZATION.json`, the nested original-evidence archive and the historical input inventory remain unchanged from the supplied Windows-fixed ZIP. Only the current `SUBMISSION_MANIFEST.json` is regenerated for this delivery. It excludes itself. The old manifests remain records of their own scope, not new declarations of historical preregistration.

The earlier supplied edition was postprocessed with updated provenance fingerprints. `submission/provenance/historical_content_comparison.json` records the existing comparison scope. Hash consistency does not establish that revised fingerprints were present on the original execution date.

## File retention and responsible use

The root historical modules, older study records, `work/`, caches, budget records and old verification logs remain as source evidence or verifier dependencies. Some documentation/build copies are duplicates, and 15 old stdout/stderr files are empty. They are identified in `delivery/FILE_REVIEW_EN.txt`; they are not extra independent results. Do not delete `work/` wholesale: the optional reviewer-form check references it and the historical manifest covers its files.

Use the offline `submission.py` commands above for this submission. Historical `run_fresh120.command` and model-run code are preserved research sources, not instructions to launch new paid experiments. Original Chinese fields, model-visible inputs, returned notes and nested archive names are immutable records; they are not silently translated or removed to give an all-English appearance.

See the current validation record for executed checks and limits.
