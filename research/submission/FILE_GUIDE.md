# File guide

Paths below are relative to the package root. Read `../README.md` for commands and platform limits.

| Location | Current purpose |
|---|---|
| `submission.py` | Offline verify, reproduce, export and inspect entry |
| `submission/build_evidence.py` | Existing exporter; reads saved records and the unchanged scorer |
| `submission/trace_template.html` | Existing HTML template; conversation text is display data |
| `submission/evidence/trace_viewer.html` | Self-contained viewer for all 260 saved test/diagnostic trajectories |
| `submission/evidence/test_traces.json` | All requests and saved trajectories with original source line and hash |
| `submission/evidence/system_outputs.csv` | Final outputs, scores, questions and record identities |
| Other `submission/evidence/` tables | Existing field, question, value and failed-constraint diagnostics |
| `human_review/` | Completed returned assessments, fixed statistics, source packets, mapping and reproduction script |
| `case_analysis/` | Existing English case analysis, tables and unchanged reproduction inputs |
| `experiments/120_fresh_v0.6/` | Active frozen study source, configuration, data, caches and original stage results |
| `experiments/120_v0.5/` | Historical provenance only; not the current evaluation |
| Root `coprompt/`, `config/`, `data/`, `runs/` | Retained historical source/records; not a second current study |
| `audit/original_evidence.zip` | Unchanged nested original evidence with its historical language and names |
| `handoff/verify_handoff.py` | Supplied Windows-fixed historical integrity/full-replay verifier |
| `work/` | Retained construction/history; optional form check has a live dependency here |
| `submission/tests/` | Existing five supplemental-exporter tests |
| `submission/verification/` | Original 27 October checks and limits, retained unchanged except its guide |
| `submission/provenance/` | Original input inventory and earlier content-comparison records |
| `delivery/SOURCE_PRESERVATION.json` | Treatments and hashes for every file in the supplied Windows-fixed ZIP |
| `delivery/VALIDATION_SUMMARY.json` | Checks actually executed for this documentation/evidence revision |
| `delivery/DIRECTORY_GUIDE_EN.txt` | Every directory, its purpose and file count |
| `delivery/FILE_INVENTORY_EN.txt` / `.json` | Every file, role, retention class and duplicate relation |
| `delivery/FILE_REVIEW_EN.txt` | Redundancy candidates, legitimate duplication and dependency reasons |

The HTML, JSON and CSV exports are intentionally different reading formats, not extra samples. Review/case inputs are intentionally self-contained for their existing scripts. Original manifests and source inventories describe their historical scope; the regenerated `SUBMISSION_MANIFEST.json` covers the current package.
