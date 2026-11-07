# Post-hoc error analysis of the saved v0.6 test

This analysis uses all 60 main-test cases and all four saved policy trajectories, with the diagnostic kept separate. It is a software-assisted inspection of existing evidence, not a new experiment, independent annotation exercise or human evaluation. No cases, labels, prompts or outputs were changed. Reproduce the tables using `python3 -B submission.py export --out ../new_evidence_directory` from the package root.

## 1. Distinguish model extraction from rule validation

Each initial extraction is shared by the policies. Count it once per case: **60 × 4 = 240 field states**, not 960 independent observations. The stored annotations mark 164 fields resolved and 76 unresolved.

| Field | Annotated known | Annotated unresolved | Known missed after validation | Annotated unresolved accepted |
|---|---:|---:|---:|---:|
| Writing audience | 21 | 9 | 3 | 0 |
| Writing tone | 17 | 13 | 0 | 0 |
| Writing length | 22 | 8 | 0 | 0 |
| Writing required content | 22 | 8 | 0 | 4 |
| Planning deadline | 25 | 5 | 10 | 0 |
| Planning available time | 24 | 6 | 7 | 0 |
| Planning topics | 24 | 6 | 0 | 5 |
| Planning priorities | 9 | 21 | 1 | 8 |

Of **21 annotated-known fields left unresolved**, 20 had nonempty model-selected evidence that the program rejected. One (`NTSP06/priorities`) had no model-selected evidence. This distinguishes rejection after selection from a raw omission; it does not, by itself, prove every selected span was semantically correct.

There are **17 accepted states that disagree with the stored unresolved label**. Four concern required content, five topics and eight priorities. The priority cases can involve a real interpretive ambiguity: a minimum time or sequencing instruction may also imply a preference. These are label/state disagreements, not 17 newly human-confirmed mistakes. No labels were revised to make the model look better. Nonempty raw evidence is not a semantic-accuracy metric.

Full rows: `evidence/field_diagnostics.csv`. It retains case ID, field, stored label, raw evidence IDs, accepted value, rejection reason and policies that asked the field. `evidence/field_summary.csv` supplies the denominators above.

## 2. Asking again about already-provided information

| Policy | Questions in total | Questions on fields annotated known initially | Repeated field within the same conversation | Invalid requested items |
|---|---:|---:|---:|---:|
| Direct | 0 | 0 | 0 | 0 |
| Exhaustive | 71 | 19 | 0 | 0 |
| Prompt-only | 61 | 18 | 0 | 0 |
| Value-based | 71 | 19 | 0 | 0 |

These are two different notions of repetition. The controller did not ask the same field twice within a main-test conversation, but extraction/validation errors led it to ask about some information already present in the initial request. The annotation-based counts are a diagnostic proxy, not ratings of all unnecessary questions. An optional question is not automatically useless.

## 3. Why value-based did not ask less

Across value-based main-test decisions, there are **112 candidate-rating observations**: 85 products `I*U=0.5` and 27 products `I*U=1`. At selected lambda 0.25, **zero candidate observations were excluded by the threshold**. These repeated decision observations are not 112 independent fields or cases.

Value-based and exhaustive have identical question counts in all 60 cases (71 total each). Asked-field order is identical in 56 cases and differs in four, so equal totals must not be described as completely identical trajectories. See `evidence/value_ratings.csv` for I, U, product, threshold, net value and the model's recorded reason.

The observed candidate ratings and permissive selected threshold explain the lack of threshold-based stopping on this test. Shared extraction errors also create unnecessary candidates for both strategies. These logs do not establish that a larger threshold would preserve quality, nor that a new rubric would improve results. The saved validation choice is retained; no post-test parameter search was performed.

## 4. Constraint execution and checker coverage

Across the 240 main trajectories, failed registered constraint instances are: **61 word-count, 26 required-wording, 21 topic-coverage, 8 daily-cap, 7 topic-minimum and 7 date-window checks**. These are constraint instances; one output can fail more than one. All failures, including diagnostic failures, are listed separately by system in `evidence/failed_constraints.csv`.

All main final outputs parse, yet only 30/60 direct, 35/60 exhaustive, 35/60 prompt-only and 36/60 value-based outputs fully satisfy their registered constraints. Format validity therefore does not imply task success.

The public checker reports remaining violations in 4, 5, 4 and 4 main trajectories respectively. This differs from private scoring because the public checker recognizes only some visible expressions and cannot access unreleased constraints. An empty public violation list must not be treated as a complete quality certificate. Revision was attempted in 8, 12, 10 and 11 logical trajectories respectively; response-cache reuse means these counts are not counts of unique paid revision calls.

## 5. Concrete trace walkthroughs

All examples are selected after seeing results, illustrate mechanisms, and are not representative samples or independent tests. Open the viewer and select the ID/system, or use `submission.py inspect`.

**NTCW07 / value_based — correct-looking evidence rejected.** The request says “Aim the wording at actors speaking the invented language Orin.” The model selects source S2 for audience. The rule rejects it with `quote_has_no_explicit_reader_relation_cue`, and the system asks “Who is the intended audience?” The answer repeats that source text. This is evidence of a rule limitation causing an avoidable clarification, rather than the model failing to find the audience. The final hard-constraint score is 1.0; that score does not penalize this interaction burden.

**NTSP02 / value_based — deadline and daily-cap rejection.** The extractor selects evidence for the closing date and combined daily time cap, but the recorded reasons are `quote_has_no_explicit_endpoint_cue` and `quote_has_no_daily_time_allowance_cue`. The original quotes, source IDs, follow-up questions and answers are available in the viewer. This illustrates the limited natural-language coverage of the rule layer.

**NTSP07 / value_based — a partial topic requirement accepted as complete.** The request names a note-taking task and an extra minimum for “Reformulation.” The extractor and rule layer accept this as resolved topics. No clarification occurs. The recorded output omits “Idea Units” and “Note Symbols,” which were obtainable through the permitted topics answer. It fails topic coverage and the Idea Units minimum, scoring 0.6. This connects a state-completeness problem to skipped information gathering; it is not merely a scheduling-format error.

**NTCW03 / value_based — explicit length constraint missed by the public parser.** The request states “Use at least 55 words and no more than 85 words in total.” All initial fields are accepted; the system acts without questions. The saved final output has 101 words and scores 0.5. The public check lists no final violation. This shows that a constraint may be known to the extractor and still not be covered by the separate public checker. The private scorer catches the length failure.

**NTSP01 / value_based — a successful comparison example.** The saved plan satisfies all five registered checks (date window, daily cap, coverage and two topic minima). Its 1.0 score establishes those mechanical properties only. This example does not validate the plan's pedagogical quality.

## 6. Limits and implications

The confirmed scope is the selected v0.6 implementation on this synthetic case distribution. Field-label disagreement counts are post-hoc and contain interpretation-sensitive priorities. Neither these diagnostics nor the score measures factual hallucination, style, usefulness or real-user satisfaction. The derived plan summary and extra revision are part of this version and are disclosed departures from the proposal.

Future changes could broaden the source rules, distinguish complete topic lists from isolated minima, and improve public-constraint parsing. They would require a separately identified version and appropriate new evidence. **No such changes are made in this submission.** The present result supports a bounded account of where clarification helped, where the heuristic failed to save questions, and where the shared pipeline limited all strategies.

## Existing human-informed case analysis

This automatic diagnostic report is unchanged in its numerical findings. The previously completed case analysis combining the returned assessments and saved experiments is supplied separately at `../case_analysis/case_error_analysis_en.md`. Its original tables and source inputs are alongside it; the completed reviewer statistics and returns are in `../human_review/`. These are existing evidence additions, not new experimental cases, labels, scores or adjudication.
