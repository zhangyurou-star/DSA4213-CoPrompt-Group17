CoPrompt Fresh-120 English Handoff
Package: CoPrompt_Fresh120_v0.6.0_EN1_2026-10-20
Experiment: v0.6.0+budget-precision-1
Presentation edition: EN1
Handoff date: 20 October 2026 (Asia/Singapore)

This package hands over a completed clarification-policy comparison on 120 newly authored cases. It includes the code, data, records, automatic analysis, pending human-review materials, and explanations needed to understand the experiment without the earlier 80-case project.

Automatic execution and analysis are complete. Actual human content review, review aggregation, and the final course report remain outstanding. Reading, integrity checking, and offline reproduction require no API key and no new model spending.

1. Start here

1) Extract the entire package. Keep the directory structure intact.
2) Read this file, then experiments/120_fresh_v0.6/docs/METHODS.txt and experiments/120_fresh_v0.6/outputs/fresh120_analysis/results_interpretation.txt.
3) For structured method details, read experiments/120_fresh_v0.6/data/protocol_reading_edition.json. For statistics, read outputs/fresh120_analysis/analysis.json within that experiment.
4) Verify the package using the root verify_package.command on macOS, or the Python instructions below.
5) Assign each real reviewer only their own HTML file and the review instructions. Do not send the whole package, results reports, or private policy mapping to a reviewer intended to be blind.
6) Collect each reviewer's latest JSON export, check declarations and completeness, then aggregate human scores and prepare the final report.

The recorded experiment is already complete. The English run_fresh120.command entry verifies the completed-stage evidence and runs offline analysis without requesting an API key. It does not launch a new paid experiment. The original paid-execution launcher remains in the audit archive. Do not delete caches, reset the ledger, reselect parameters on test results, or replace recorded outputs with preferred reruns.

2. What EN1 changes and preserves

EN1 localizes the handoff's active reading materials, reviewer interface, progress messages, and output names into English. This occurred after execution. It is not a new experiment, a new preregistration, or evidence that the original execution environment used only English.

The original unmodified evidence is preserved in audit/original_evidence.zip. It includes the frozen protocol and code, original paths and wording, exact response records, cache evidence, earlier amendment snapshots, and original verification materials. Chinese wording in that archive is historical evidence, not the interface for ordinary review. It must remain unchanged so original fingerprints and reconstruction remain checkable.

In particular, the original field catalog contained Chinese descriptions visible to the model. These descriptions are not retroactively translated in the original evidence. English explanations are supplied for readers, but historical prompts must not be presented as having been different from what the model actually received.

The English presentation and source copies are not the original frozen files. Offline reproduction uses an isolated temporary copy of original evidence and compares the saved study data/results with the English view. Do not update a freeze manifest simply to make a translated source file appear historically unchanged.

LOCALIZATION.json records separate original and English hashes for each of the 71 frozen files. The English runtime checks this declared mapping against the original archive; it does not pretend that translated code has the original hash. The original freeze keeps its historical names, while the mapping identifies their current English counterparts. The English index in experiments/ACTIVE_STUDY.json points to the translated files and records the corresponding analysis hash.

Method development incorporated prior experience, and the coordinator had seen historical results. New case construction and current results were isolated: no earlier cases, model outputs, response caches, or selected threshold entered the current execution or primary comparison. Historical expenses remain in the cumulative budget only. This package states the complete current method rather than asking the reader to infer it from an earlier version.

3. Method in brief

The two domains are constrained English writing and study planning. Writing fields are audience, tone, length, and required_content; planning fields are deadline, available_time, topics, and priorities.

One shared extraction asks the model to cite numbered source units. The program checks their provenance and limited semantics. Unconfirmed fields remain unresolved. A clarification can ask only an unresolved field that has not been asked or marked unanswerable. A deterministic simulator releases only that field's prewritten available, unknown, or declined answer.

Four main policies:

  direct: ask nothing and generate.
  exhaustive: ask eligible fields in catalog order.
  prompt_only: the model directly chooses ASK+field_id or ACT.
  value_based: the model rates importance I in {0, 0.5, 1} and uncertainty U in {0.5, 1}; the controller asks the field maximizing I*U-lambda only when that net value is strictly positive. Ties use catalog order.

All clarification policies have the same three-item limit. Invalid/repeated ASK requests also count. Shared stopping conditions include ACT, no eligible fields, immediate execution, exhausted allowance, and a decision that remains invalid after one format repair. The diagnostic importance_one variant fixes effective I to 1 while retaining U, selected lambda, and the allowance.

All policies use qwen/qwen3-30b-a3b-instruct-2507 through OpenRouter with a fixed nebius/fp8 route, temperature=0, top_p=1, and seed=20261013. The generator receives only public inputs and released interactions. It has at most one format repair and one additional revision for detectable public-constraint violations, for at most three generation-stage calls. A format-valid revision is adopted without consulting its hidden score. Final plan summaries are deterministically derived from final schedule details.

The 40 design cases check the workflow. The 20 validation cases compare lambda={0,0.25,0.5}: keep candidates averaging at most two questions, then prefer higher hard-constraint score, fewer questions, and larger lambda. Validation selected 0.25, which is fixed for the 60 test cases.

The common private scorer measures each case's passed fraction of critical hard constraints. Writing checks word counts and required wording; planning checks dates, daily totals, coverage, and topic minimum durations. Main comparisons are paired within cases, with 10,000 domain-stratified case-bootstrap samples and 95% percentile intervals. Full details, edge cases, information boundaries, and proposal deviations appear in METHODS.txt.

4. Completion status and key results

Cases: 40 design + 20 validation + 60 test = 120, split equally by domain.
Design: 48 trajectories on the 12 pilot cases + 112 on the other 28 = 160.
Validation: 20 cases x three thresholds = 60 trajectories.
Test: 60 cases x four policies = 240 main trajectories.
Diagnostic: 20 preselected test cases x one variant = 20 trajectories.
Total: 480 logical trajectories. The diagnostic subset adds no independent cases.

Main results on the fresh 60-case test set:

Policy          Hard-constraint mean  Mean question items  Fully passing cases
direct                 0.7072                0.000                30/60
exhaustive             0.7878                1.183                35/60
prompt_only            0.7794                1.017                35/60
value_based            0.7989                1.183                36/60

value_based minus direct: +0.0917 score, paired 95% interval [0.0306,0.1569].
value_based minus exhaustive: +0.0111, interval [-0.0111,0.0389]; equal question counts case by case, 71 total per policy.
value_based minus prompt_only: +0.0194, interval [-0.0236,0.0625]; 0.167 more questions on average.

The evidence supports better hard-constraint scores than direct generation for this case distribution. It does not establish that value_based is better than exhaustive while asking fewer questions. All recorded candidate I*U values were 0.5 or 1, above the selected 0.25 threshold, so that threshold filtered out no questions. The 20-case diagnostic showed no extra score or question-count benefit and is not independent success evidence.

Automatic scores do not establish factual correctness or complete usability. The intervals reflect case variation, not independently repeated model sampling; no multiple-comparison adjustment was made. Exact first-response reuse within this study is allowed, and cache hits are not independent repetitions.

Recorded costs:
  Current study:                    US$0.08404924
  Earlier costs:                    US$0.08857385
  Cumulative:                       US$0.17262309
  Authorized cumulative cap:        US$2.00
  Remaining recorded allowance:     US$1.82737691

Current-study accounting includes US$0.08305670 reported by the provider and approximately US$0.00099254 conservatively reserved for one unconfirmed request. The reserve is not a confirmed charge. Keep it in the records.

5. Package map

README.txt
  This handoff guide.

experiments/120_fresh_v0.6/
  The English presentation of the current study. Important paths relative to it:

  docs/METHODS.txt
    Standalone methods, information boundaries, scoring, statistics, and proposal deviations.

  data/protocol_reading_edition.json
    Post-run structured explanation. It is not the original frozen protocol.

  data/case_catalog.txt
    Human-readable catalog of the 120 cases.

  data/public/
    Initial requests and public field/schema materials.

  data/private/*_answers.jsonl
    Prewritten simulated-user answers, released only when their field is asked.

  data/private/*_annotations.jsonl
    Hidden hard constraints and feasible examples for checking/scoring, not model inputs.

  data/schemas/
    Request, answer, decision, and output schemas.

  config/
    Model, routing, request settings, and output limits; no API key.

  coprompt/
    Source modules for orchestration, prompts, evidence grounding, policy execution, public-constraint checks, scoring, provider requests, and budgets.

  runs/formal_v0.6.0_*/
    Five-stage trajectories, completion records, fingerprints, and summaries.

  runs/*_session.jsonl
    Six current-study request-session logs, including usage, costs, and failures.

  runs/formal_raw_response_cache/
    642 raw first-response cache files.

  runs/extraction_cache/
    120 shared extraction cache files.

  runs/generation_cache/
    223 bounded generation-process cache files.

  outputs/fresh120_analysis/analysis.json
    Statistics, paired intervals, costs, provenance fingerprints, and verification flags.

  outputs/CoPrompt_validation_v0.6.0/lambda_selection.json
    The selected threshold and complete validation-selection evidence.

  outputs/fresh120_analysis/results_summary.txt
  outputs/fresh120_analysis/results_interpretation.txt
    Concise generated results and the fuller interpretation.

  outputs/fresh120_analysis/reviewer_1_packet.json
  outputs/fresh120_analysis/reviewer_2_packet.json
    Anonymous review packets with pending ratings.

  outputs/fresh120_analysis/review_forms/reviewer_1.html
  outputs/fresh120_analysis/review_forms/reviewer_2.html
    Standalone English review interfaces for reading, rating, confirming, and exporting.

  outputs/fresh120_analysis/private/reviewer_policy_mapping.json
    Coordinator-only mapping; never include with blind-review materials.

  tools/
    Data checks, preflight, progress reporting, analysis, and review-packet creation.

  tests/
    Offline regression tests. The original suite contains 65 tests using simulated responses; these are not 65 real experiments.

  work/
    Authoring provenance, allocations, feasibility/novelty checks, and cost forecast sources. These are audit/construction utilities, not steps to rerun over a completed frozen dataset.

  run_fresh120.command
    Completed-stage verification and offline analysis; no key input or new model calls.

audit/original_evidence.zip
  Immutable original package evidence, including original-language files and historical amendment snapshots. Reproduction takes place in an isolated temporary extraction. The Chinese wording in this archive is deliberately preserved as historical evidence.

handoff/verify_handoff.py
  Portable offline package verifier. See the execution instructions below.

verify_package.command
  macOS entry point for the verifier.

references/Group17_CoPrompt_Proposal_Final_edited.pdf
  The original proposal.

PACKAGE_MANIFEST.json
  File sizes and SHA-256 fingerprints for detecting changes or omissions. This is an integrity inventory, not a digital signature or independent proof of authenticity.

Build and localization sources supplied elsewhere in the package explain how the English presentation and review pages were produced. Original method dependencies, 16 historical fee sessions, budget amendments, novelty-reference data, and earlier documentation are preserved in the audit evidence; they are not a second set of current-study findings.

To rebuild an English handoff in a working copy, run work/handoff_fresh120/build_package.py stage. The builder uses the included audit/original_evidence.zip and supplied English sources; it does not require an earlier external package. Verify the newly staged package with its handoff/verify_handoff.py, saving the JSON receipt as work/handoff_fresh120/verification_receipt.json beside the builder, then run build_package.py seal. Existing target directories are not overwritten. Build scripts are for coordinators and must not be run over the immutable evidence archive.

6. Code responsibilities

Within experiments/120_fresh_v0.6/coprompt/:

  formal.py: five-stage orchestration, version/data checks, threshold selection, resume behavior, and precise cumulative-budget accounting.
  runner.py: shared execution for the four policies and diagnostic.
  prompts.py: extraction, decision, generation, and repair prompts.
  grounding.py: field states and public-request evidence checks.
  visible_constraints.py: checks of model-visible requirements only.
  scoring.py: hard-constraint scores from private annotations.
  provider.py: service requests, parameters, usage, costs, and errors.
  budget.py: ledger and locking; FreshBudgetLedger in formal.py supplies the recorded precision correction.

The flow is public request -> evidence extraction -> ASK/ACT decision -> release only the asked answer -> shared generation/limited repairs -> private-annotation scoring -> save the complete trajectory.

English source presentation is a post-run localization. For exact historical execution behavior and prompt bytes, use the original evidence and the isolated offline verifier.

7. Handing over human review

Each reviewer assesses 100 outputs: five variants of 20 preselected test cases. Preserve each packet's random order and anonymous IDs.

The HTML files are standalone and require no Python, Node, server, or API key. Open one in a browser. Read the complete materials, enter four scores from 1 to 5 and two nonnegative counts, and use the unable-to-assess option with notes when appropriate. Such values remain null rather than becoming zero.

Complete the reading checkboxes and confirm each assessment. Editing a confirmed assessment returns it to draft. Unconfirmed drafts remain in the JSON backup state and do not populate the final rating columns.

Export a JSON backup at the end of every session. Browser-local storage depends on the browser and file location and is not a transferable backup. Export before moving computers. Keep both reviewers' returned JSON files unchanged; CSV is useful for inspection, but JSON is the recovery source for drafts and interface state.

The coordinator must check reviewer_slot, source fingerprints, all 100 IDs and their order, reviewer identity, independence, prior exposure, author/cross-check exclusions, and actual blinding. Distinguish confirmed unable-to-assess items, unreviewed items, and explicit zero counts.

No human judgment has been prefilled. Preparing materials, checks, and interface logic tests do not constitute human review. Use only confirmed ratings after checking their source and declarations. review_form_state stores drafts, checkboxes, and confirmation history; ratings contains the original six dimensions.

After both independent reviews and before resolving disagreements, the proposal calls for linearly weighted Cohen's kappa per five-level scale, with NA and exact agreement when undefined. Count items require exact agreement and mean absolute difference. This aggregation and the final report remain to be done.

8. Offline verification on another computer

Reading reports and using HTML requires no development environment. Full experimental replay/verification requires Python 3.10+ on macOS, Linux, or Windows WSL. The original runtime uses POSIX fcntl locking and does not support complete execution under native Windows Python. The verifier requires no API key and makes no model calls.

From the extracted package root:

  python3 -B handoff/verify_handoff.py

For transfer-integrity checking only:

  python3 -B handoff/verify_handoff.py --manifest-only

To save recomputed analysis outside the package in a new directory:

  python3 -B handoff/verify_handoff.py --export-analysis ../coprompt_recomputed_analysis

For optional review-interface logic checks with Node 18+:

  python3 -B handoff/verify_handoff.py --node node

Use --help for the precise options supported by this verifier.

Full verification checks file integrity, reconstructs the original evidence in a temporary directory, checks the original freeze and records, rescoring/selection/statistics/cost accounting, and checks consistency with the English presentation. Temporary replay protects the delivered package from analysis rewrites. Consult the included verification receipt for the actual checks completed for this package.

Do not treat an altered filename, translation, or new path as a reason to overwrite the original freeze. Investigate unexpected fingerprint changes instead.

9. Boundaries and remaining limitations

The existing experiment needs no further API execution. New model repetitions, changed prompts/scoring, or a different threshold-selection rule need a separately identified study version that preserves these data and failures.

budget-precision-1 corrected decimal accounting reconciliation and preserved the original costs, freeze snapshots, and failure evidence. Earlier one-time amendment/build scripts must not be rerun in place over historical evidence.

Novelty checks used old text only as exclusion references. Distinct strings or family IDs do not prove semantic independence. New-data/result isolation does not erase historical influence on method development.

Any recipient planning new API work must use their own key and explicitly authorize their own budget. The existing US$2 figure records the original user's historical cumulative authorization; it is not fresh spending permission for the recipient. Multiple copied ledgers do not provide a shared global cap, and historical expenses or unknown-cost reserves must not be reset.

The package excludes credentials, chat logs, terminal history, bytecode, operating-system clutter, and runtime locks. Integrity checks and recorded source comparisons support the handoff. The earlier review form received offline logic/content checks, but browser security policy prevented a browser-based preview; it was not certified by that earlier check for native downloads or browser-local storage. Consult the EN1 verification receipt for the checks actually run on the English form, and confirm opening/export behavior in the recipient's browser.

Final submission should explain the complete method and disclose the actual human-review status, method-development provenance, synthetic/template limitations, cache reuse, and statistical boundaries. English localization does not add experiment outcomes or change the conclusions.
