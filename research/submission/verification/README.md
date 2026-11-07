# Verification scope

`source_verification.stdout.txt` is the first full check of the team's uploaded archive, before additions. It passed the source verifier, original and English 65-test suites, all 480 recorded trajectories, threshold selection, score/analysis replay and freeze consistency checks. This establishes internal consistency of that supplied edition; see the separate historical-content comparison for its relation to older archives.

The `py312_*` and `py313_*` files record checks actually run for this supplemented submission on macOS. The summary identifies each command and exit status. There are five supplemental exporter tests; they test complete source correspondence, duplicate/missing-row rejection, score-tampering rejection, deterministic/no-overwrite export and safe embedding of conversation text.

`browser_check.json` records a blocked attempt to open the local HTML viewer: the browser tool disallowed file URLs. No successful browser rendering or button interaction is claimed. JavaScript syntax and data checks are separate offline checks. Native Windows, Linux/WSL and live-model interaction were not tested for this delivery.

No model requests, new outputs, new parameter selection or human ratings were generated. Any recomputed analysis is produced in temporary copies or explicitly new output directories. Original input files and their original manifests are retained unchanged.

The source handoff's older verification receipts are historical, not evidence of checks performed on 27 October. Test failures encountered during development, if any, are retained rather than overwritten with successful logs.

## Current documentation/evidence revision

The files in this directory retain the earlier 27 October check history. Checks newly executed for the 28 October packaging revision are summarized separately in `../../delivery/VALIDATION_SUMMARY.json`. Do not treat old timestamps or old source-preservation statements as newly executed checks. The current README explains the two changes already present in the supplied Windows-fixed ZIP and the newly added completed review evidence.
