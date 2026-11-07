# Error Analysis

We examined the saved trajectories from the 60-case test set and the existing human assessments on the preselected 20-case subset. The four main systems contribute 240 test trajectories; the importance-one diagnostic adds 20 trajectories on the same subset. Human evidence comprises 100 outputs assessed by two reviewers. The eight illustrative cases below were selected after inspection to explain successes and failures, not as a new evaluation sample. No cases, models, thresholds, ratings, or experiments were added or revised.

## Constraint failures and overall comparison

Value-based Adaptive achieved mean hard-constraint satisfaction of 0.7989 with 1.183 questions per case, compared with 0.7072 and zero questions for Direct Response, 0.7878 and 1.183 for Exhaustive Clarification, and 0.7794 and 1.017 for Prompt-only Adaptive. Existing paired 95% bootstrap intervals support a higher hard-constraint score than Direct, but do not establish a score advantage over the two clarification baselines. All 240 main-test outputs were format-valid; remaining failures therefore concern constraints within valid outputs. No invalid or repeated-field ASK items were recorded. This runtime category differs from asking again for information already explicit in the initial request.

| Existing constraint check | Direct | Exhaustive | Prompt-only | Value-based |
|---|---:|---:|---:|---:|
| Whole-text word count | 17/30 | 15/30 | 15/30 | 14/30 |
| Required literal content | 9/30 | 6/30 | 6/30 | 5/30 |
| Date window | 5/30 | 0/30 | 2/30 | 0/30 |
| Daily total minutes | 2/30 | 2/30 | 1/30 | 3/30 |
| Topic coverage | 6/30 | 5/30 | 5/30 | 5/30 |
| Topic-specific minimum minutes | 3/17 | 1/17 | 2/17 | 1/17 |

Entries are failed checks divided by checks evaluated. Failures can overlap within a case, and topic-specific minimums can occur more than once per case; these counts do not replace the case-averaged primary metric. Domain results are descriptive: Value-based scored 0.6833 on writing and 0.9144 on planning, while Exhaustive scored 0.6500 and 0.9256. The ranking was therefore not uniform across domains.

## Obtaining missing information can help

In **NTSP13**, the request specified three peer-review topics and a 45-minute daily allowance, but omitted the final study date. Value-based asked for the deadline and received 5 February 2027. Its plan stayed within that window and scored 1.00. Direct and Prompt-only asked nothing, scheduled an item on 6 February, and scored 0.75. Exhaustive also obtained the deadline and scored 1.00. Both reviewers rated the visible Direct and Value-based outputs 5 on all four dimensions, and neither considered the deadline question unnecessary. The reviewers did not see the unasked deadline in the Direct trajectory; their ratings should not be retrospectively changed using that answer. This illustrates the benefit of obtaining an available critical requirement, without establishing an advantage over Exhaustive.

## State identification can produce both redundant and missed questions

In **NTSP02**, the initial request explicitly stated that the study window closed on 4 February and daily sessions must total no more than 35 minutes. The shared extractor selected those source passages, but deterministic semantic checks rejected them for lacking recognized endpoint and daily-allowance cues. The fields remained unresolved, and all three clarification systems asked for the same information again. All five variants scored 1.00; both reviewers gave Direct and Value-based 5 on all four content dimensions, while marking both Value-based questions unnecessary (R1-047 and R2-008). The trace locates the information loss in evidence filtering, followed by decisions that did not resolve the discrepancy with the original request.

Conversely, in **NTSP07**, a general description of interpreting-note practice and a minimum for Reformulation were accepted as a resolved topics field. Every field was nonempty, so the clarification systems and diagnostic stopped with no eligible questions; Direct acted under its fixed policy. None asked a question. The permitted topics answer could have supplied Idea Units and Note Symbols, but was never requested. The resulting plan used Reformulation and the broad label Note-Taking Techniques; topic coverage and an Idea Units minimum failed, yielding 0.60 for every variant. The two Value-based reviews gave usefulness 4 and feasibility 5, noting the broad topic label without applying the unasked syllabus to their judgments. This failure occurred before I/U scoring: a nonempty field was treated as sufficiently complete, so thresholding could not recover the omitted information.

## Acquiring information does not guarantee compliant generation

In **NTCW13**, Value-based and Exhaustive obtained a playful tone and a 50–80-word limit, but produced a 92-word counting rhyme under the frozen counting convention. The visible-constraint parser did not support the wording “at least 50 words and no more than 80 words,” so no word-count revision was triggered. Both systems scored 0.50, while Direct scored 1.00 and Prompt-only scored 1.00 after one tone question. Reviewers rated the Value-based output 3 on all four dimensions and 2 on all four dimensions, respectively, identifying awkward phrases such as “what a night of looms” and “what a dreamy troth.” Neither counted its questions unnecessary. Direct also received coherence ratings below 5 despite its perfect automatic score. The example shows both generation noncompliance and semantic limitations of automatic checks; it does not establish a general ranking from one case.

In **NTCW20**, the introduction to Ren had to contain “collecting odd buttons” verbatim. Value-based asked only for tone. A visible word-count revision shortened its draft from 95 to 86 words, but both drafts used “I collect odd buttons.” The literal requirement was absent from the mechanically extracted checklist even though it remained in the original generation input. All variants scored 0.50. Both reviewers gave Value-based (4, 5, 5, 4), describing an otherwise usable letter requiring a small literal edit. Correcting length did not ensure that all content constraints were checked, and a mechanical failure did not imply complete unusability.

## Correct stopping and content quality are separate

In **NTCW24**, Value-based received unknown for audience and declined for tone, then acted without asking either field again, as required by the stopping rules. Nevertheless, its clock critique contained 110 words against a 60–90-word limit and recommended a darker hour hand while asserting that the thin silver hands remained unchanged. Its automatic score was 0.50; both reviewers gave (3, 3, 4, 3) and zero unnecessary questions. Required-phrase checks could confirm that the words occurred, but could not establish logical consistency. Unavailable preferences should not be invented to repair this assessment.

In **NTSP28**, all systems obeyed the public execute-now instruction, asked zero questions, and produced the same fully passing stain-chemistry schedule. Daily totals stayed below the 60-minute allowance; topic totals were 45, 40, and 35 minutes. Both reviewers gave 5 on all dimensions and zero counts. This is evidence that the shared user-control rule worked, rather than evidence that I/U scoring independently learned to stop. Identical cached outputs are not independent successful replications.

## Human evidence adds semantic concerns and disagreement

In **NTCW08**, Value-based obtained the required fictional weather facts but also repeated an already specified audience question. Its output included the facts, yet contained 95 words against a 60–90-word limit and scored 0.50, compared with Direct’s 0.00. Both reviewers counted one unnecessary question. Their unsupported-assumption counts differed: reviewer 1 recorded zero, treating extra imagery as permissible fiction; reviewer 2 recorded one, interpreting “avoid direct exposure” as an unsupported implication of risk. We retain both interpretations rather than adjudicating them with a new judge. Fictional elaboration is not automatically an unsupported factual claim.

The original count anomaly is also retained: R2-002 assigns three unnecessary questions to the Direct output of NTCW13 despite its empty clarification trace. It remains in the pre-adjudication statistics but is not treated here as evidence that Direct actually asked questions.

## Why the value controller did not save questions

Value-based and Exhaustive had equal question counts in all 60 cases, totalling 71 each. Their field sets matched in 59 cases, orders in 56, and final outputs in 56. At the selected threshold of 0.25, all 112 candidate net-value entries were positive: 85 were 0.25 and 27 were 0.75. These are candidate ratings across steps, not 112 asked questions. Value-based stopped because no fields were eligible in 47 cases, the three-item allowance was exhausted in seven, or immediate execution was requested in six; no nonpositive-value decision stopped questioning early.

On the preselected diagnostic subset, Value-based, Importance-one and Exhaustive had identical per-case quality and question counts, with means of 0.805 and 1.25. This provides no observed additional benefit from importance on these cases, while not proving that importance is universally ineffective. Diagnostic trajectories and cache reuse do not add independent cases.

The benchmark’s noncritical-field question totals were 31, 30 and 31 for Exhaustive, Prompt-only and Value-based. These are burden proxies, not automatic counts of useless questions: the useful or declined preference questions above and the redundant questions in NTSP02 require different interpretations. Human means and comments remain descriptive of the 20-case subset. Both returned reviews document AI assistance and human confirmation, departing from the proposal’s no-LLM-judge plan; their provenance and blinding limitations remain disclosed. No new human scores, hypothesis tests, or model judgments were introduced.

Taken together, the saved evidence explains how clarification can improve hard-constraint satisfaction over Direct, while state identification, uniformly positive candidate ratings, and remaining generation failures limit the quality–question trade-off. It does not establish a question-efficiency advantage over Exhaustive, a clear advantage over Prompt-only, or real-user satisfaction. Stage-level explanations are grounded in observed traces, rather than causal effects estimated through new interventions.

*Evidence locator:* Exact case/variant scores and reviewer IDs are in `case_comparison.csv`; full selected traces and unchanged review records are in `selected_case_evidence.json`; all 200 assessment records are in `human_review_evidence.csv`. Source files and hashes are preserved in `inputs/` and `source_manifest.json`.
