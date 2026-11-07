"""Human-facing source translations for the English handoff.

Apply only to SOURCE_FILES. Never apply these mappings to model prompts,
field_catalog.json, raw responses, trajectories, datasets, or frozen evidence.
The original frozen evidence must be preserved byte for byte separately.
"""

STUDY = "experiments/120_fresh_v0.6/"
SOURCE_FILES = [
    STUDY + "coprompt/formal.py",
    STUDY + "tools/analyze_fresh.py",
    STUDY + "tools/show_status.py",
    STUDY + "tests/test_formal.py",
    STUDY + "tests/test_fresh_analysis.py",
    STUDY + "work/build_catalog.py",
    STUDY + "work/freeze_fresh.py",
    STUDY + "work/prepare_budget_forecast.py",
    STUDY + "amendments/budget_precision_20261019/before/coprompt/formal.py",
    STUDY + "amendments/budget_precision_20261019/before/tools/analyze_fresh.py",
]

PATH_REPLACEMENTS = {
    "outputs/CoPrompt_\u6b63\u5f0f\u9a8c\u8bc1_v0.6.0": "outputs/CoPrompt_validation_v0.6.0",
    "outputs/120\u4f8b\u5168\u65b0\u5b9e\u9a8c\u5206\u6790": "outputs/fresh120_analysis",
    "\u8bc4\u5ba1\u5458{reviewer}_\u72ec\u7acb\u8bc4\u5206\u8868.json": "reviewer_{reviewer}_packet.json",
    "\u8bc4\u5ba1\u54581_\u72ec\u7acb\u8bc4\u5206\u8868.json": "reviewer_1_packet.json",
    "\u8bc4\u5ba1\u54582_\u72ec\u7acb\u8bc4\u5206\u8868.json": "reviewer_2_packet.json",
    "private/\u8bc4\u5ba1\u7b56\u7565\u6620\u5c04_\u4ec5\u534f\u8c03\u4eba.json": "private/reviewer_policy_mapping.json",
    "\u7ed3\u679c\u8bf4\u660e.txt": "results_summary.txt",
    "\u672c\u8f6e\u7ed3\u679c\u89e3\u8bfb.txt": "results_interpretation.txt",
    "120\u65b0\u6848\u4f8b\u76ee\u5f55.txt": "case_catalog.txt",
    "\u5f00\u59cb\u5168\u65b0120\u4f8b\u5b9e\u9a8c.command": "run_fresh120.command",
}

KEY_REPLACEMENTS = {
    "instructions_zh": "instructions_en",
    "limitations_zh": "limitations_en",
    "assumptions_zh": "assumptions_en",
}

REVIEW_INSTRUCTIONS = {
    "\u8bf7\u72ec\u7acb\u5b8c\u6210100\u4efd\u8f93\u51fa\u7684\u8bc4\u5206，\u4e0d\u67e5\u770b\u53e6\u4e00\u8bc4\u5ba1\u8868\u6216private\u6620\u5c04。":
        "Independently rate all 100 outputs without viewing the other reviewer packet or the private strategy mapping.",
    "\u7528\u9014、\u8fde\u8d2f\u6027、\u53d7\u4f17\u9002\u914d、\u53ef\u884c\u6027\u5404\u8bc41\u81f35\u5206，1\u6700\u4f4e、5\u6700\u9ad8；\u4e0d\u652f\u6301\u7684\u4e8b\u5b9e\u5047\u8bbe\u548c\u4e0d\u5fc5\u8981\u8ffd\u95ee\u586b\u5199\u975e\u8d1f\u6574\u6570。":
        "Rate usefulness, coherence, audience fit, and feasibility from 1 (lowest) to 5 (highest). Enter nonnegative integer counts for unsupported factual assumptions and unnecessary clarification questions.",
    "\u53ea\u4f9d\u636e\u7528\u6237\u539f\u59cb\u8bf7\u6c42、\u5df2\u5c55\u793a\u7684\u95ee\u7b54\u548c\u6700\u7ec8\u8f93\u51fa\u8bc4\u4ef7；\u53ef\u9009\u95ee\u9898\u4e0d\u81ea\u52a8\u89c6\u4e3a\u65e0\u7528。":
        "Judge only the original user request, the displayed exchanges, and the final output. An optional question is not automatically unnecessary.",
    "\u9047\u5230\u65e0\u6cd5\u5224\u65ad\u7684\u9879\u76ee\u4fdd\u7559null\u5e76\u5199\u5907\u6ce8；\u8bf7\u52ff\u628a\u7a7a\u767d\u5f53\u4f5c0。":
        "For any item you cannot judge, leave the value null and explain in the notes. Do not treat a blank as zero.",
    "\u7b56\u7565\u540d\u79f0\u4e0e\u81ea\u52a8\u8d28\u91cf\u5206\u5df2\u9690\u85cf；\u662f\u5426\u771f\u6b63\u76f2\u8bc4、\u8bc4\u5ba1\u8005\u662f\u5426\u770b\u8fc7\u539f\u8f93\u51fa\u4ee5\u53ca\u4f5c\u8005/\u4ea4\u53c9\u590d\u6838\u6392\u9664\u9700\u534f\u8c03\u4eba\u53e6\u884c\u786e\u8ba4。":
        "Strategy names and automatic quality scores are hidden. The coordinator must separately confirm actual blinding, prior exposure to the outputs, and the required authorship and cross-review exclusions.",
}

LIMITATIONS = {
    "\u8fd9\u662f\u5168\u65b0120\u6848\u4f8b\u5b9e\u9a8c；\u8bbe\u8ba140\u4f8b\u4ec5\u4f5c\u6d41\u7a0b\u68c0\u67e5，\u9a8c\u8bc120\u4f8b\u4ec5\u9009λ，\u4e3b\u8981\u6bd4\u8f83\u4ec5\u4f7f\u7528\u65b060\u6d4b\u8bd5\u6848\u4f8b。":
        "This study uses 120 newly authored cases: 40 design cases for workflow checks, 20 validation cases for selecting lambda, and 60 new test cases for the primary comparison.",
    "20\u4f8b\u8bca\u65ad\u662f60\u4f8b\u6d4b\u8bd5\u5b50\u96c6，\u4e0d\u80fd\u5f53\u4f5c\u989d\u5916\u72ec\u7acb\u91cd\u590d\u8bc1\u636e。":
        "The 20 diagnostic cases are a subset of the 60 test cases and are not additional independent replications.",
    "95%\u533a\u95f4\u4ec5\u53cd\u6620\u672c\u6848\u4f8b\u5206\u5e03\u53d8\u52a8，\u6bcf\u4e2a\u7cbe\u786e\u8f93\u5165\u53ea\u4fdd\u7559\u4e00\u6b21\u6a21\u578b\u9996\u54cd\u5e94；\u4e0d\u6db5\u76d6\u91cd\u65b0\u62bd\u6837\u6a21\u578b\u7684\u6ce2\u52a8，\u672a\u505a\u591a\u91cd\u6bd4\u8f83\u6821\u6b63。":
        "The 95% intervals reflect variation across this case distribution only. Each exact input retains one first model response; the intervals do not cover variability from new model samples. No multiple-comparison correction was applied.",
    "\u81ea\u52a8\u786c\u7ea6\u675f\u5206\u6570\u4e0d\u80fd\u4ee3\u8868\u5b8c\u6574\u5185\u5bb9\u8d28\u91cf\u6216\u771f\u5b9e\u7528\u6237\u6548\u7528；\u672a\u5b8c\u6210\u53cc\u4eba\u8bc4\u5ba1\u524d\u4e0d\u5f97\u62a5\u544a\u5176\u8bc4\u5206\u6216\u4e00\u81f4\u6027。":
        "Automatic hard-constraint scores do not establish overall content quality or actual user utility. Do not report human ratings or inter-rater agreement until the two-person review is completed.",
    "\u8bc4\u5ba1\u8005\u5b9e\u9645\u5206\u914d\u65f6\u95f4、\u4f5c\u8005\u548c\u4ea4\u53c9\u590d\u6838\u6392\u9664、\u72ec\u7acb\u6027\u53ca\u76f2\u8bc4\u72b6\u6001\u5747\u9700\u771f\u4eba\u786e\u8ba4；\u8eab\u4efd\u9690\u85cf\u6750\u6599\u672c\u8eab\u4e0d\u80fd\u8bc1\u660e\u8bc4\u5ba1\u8005\u672a\u89c1\u8fc7\u539f\u8f93\u51fa。":
        "Actual assignment timing, authorship and cross-review exclusions, reviewer independence, and blinding must be confirmed by people. Masked materials alone do not prove that reviewers have not previously seen the outputs.",
    "\u65b0\u6848\u4f8b\u7f16\u5199\u9694\u79bb\u4e0d\u7b49\u4e8e\u534f\u8c03\u8005\u5bf9\u5386\u53f2\u5b9e\u9a8c\u7ed3\u679c\u5b8c\u5168\u65e0\u77e5；\u5e94\u6309\u6ce8\u518c\u6587\u4ef6\u5982\u5b9e\u62a5\u544a\u8be5\u9650\u5236。":
        "Isolated authoring of new cases does not mean that the coordinator was unaware of historical results. Report this limitation as stated in the registration documents.",
}

ANALYSIS_MESSAGES = {
    "CoPrompt \u5168\u65b0120\u6848\u4f8b\u5206\u6790": "CoPrompt Fresh 120-Case Analysis",
    "\u5168\u65b040\u8bbe\u8ba1＋20\u9a8c\u8bc1＋60\u6d4b\u8bd5；12\u6848\u4f8bpilot\u5206\u4e24\u6bb5\u5b8c\u621048\u6761，\u5176\u4f5928\u8bbe\u8ba1\u5b8c\u6210112\u6761，\u5171160\u8bbe\u8ba1\u8f68\u8ff9。":
        "Fresh cases: 40 design, 20 validation, and 60 test. The two phases of the 12-case pilot produced 48 trajectories; the other 28 design cases produced 112, for 160 design trajectories in total.",
    "\u9a8c\u8bc160\u6761、\u6b63\u5f0f\u6d4b\u8bd5240\u6761\u53ca20\u6761\u8bca\u65ad\u5168\u90e8\u5b8c\u6210；\u6ca1\u6709\u5bfc\u5165\u65e7\u6848\u4f8b\u8f93\u51fa\u6216\u7f13\u5b58。":
        "All 60 validation, 240 formal test, and 20 diagnostic trajectories are complete. No previous case outputs or caches were imported.",
    "pilot\u95e8\u69db：{evidence['pilot_gate']['paired_scored_cases']}/12\u6848\u4f8b\u7684direct\u4e0eexhaustive\u6700\u7ec8\u683c\u5f0f\u5747\u53ef\u89e3\u6790\u5e76\u6210\u529f\u8bc4\u5206。":
        "Pilot gate: both direct and exhaustive outputs were parseable and scored successfully in {evidence['pilot_gate']['paired_scored_cases']}/12 cases.",
    "\u5b8c\u657420\u4f8b\u9a8c\u8bc1\u9009\u4e2d λ={selection['selected_lambda']:g}。":
        "All 20 validation cases selected lambda={selection['selected_lambda']:g}.",
    "\u5168\u65b060\u6d4b\u8bd5\u6848\u4f8b": "60 Fresh Test Cases",
    "{p}：\u786c\u7ea6\u675f\u5747\u5206 {s['mean_quality']:.4f}；\u5e73\u5747\u63d0\u95ee {s['mean_questions']:.3f}；\u5168\u901a\u8fc7 {s['full_pass']}/{s['n']}。":
        "{p}: mean hard-constraint score {s['mean_quality']:.4f}; mean questions {s['mean_questions']:.3f}; all constraints passed {s['full_pass']}/{s['n']}.",
    "\u4ee5\u4e0b\u5dee\u5f02\u5747\u4e3a\u4ef7\u503c\u7b56\u7565\u51cf\u53bb\u6bd4\u8f83\u7b56\u7565；\u95ee\u9898\u5dee\u4e3a\u8d1f\u8868\u793a\u4ef7\u503c\u7b56\u7565\u63d0\u95ee\u66f4\u5c11。":
        "The following differences are value_based minus the comparison strategy. A negative question difference means that value_based asked fewer questions.",
    "\u5bf9\u6bd4 {comparison['right']}：\u8d28\u91cf\u5dee {comparison['quality_difference']:.4f}，95%\u533a\u95f4 {comparison['quality_95pct_interval']}；\u63d0\u95ee\u5dee {comparison['question_difference']:.3f}，95%\u533a\u95f4 {comparison['question_95pct_interval']}。":
        "Versus {comparison['right']}: quality difference {comparison['quality_difference']:.4f}, 95% interval {comparison['quality_95pct_interval']}; question difference {comparison['question_difference']:.3f}, 95% interval {comparison['question_95pct_interval']}.",
    "20\u4f8b\u8bca\u65ad\u5728\u540c\u4e00\u6279\u6848\u4f8b\u4e0a\u6bd4\u8f83，\u4e0d\u662f\u989d\u5916\u72ec\u7acb\u91cd\u590d。":
        "The 20-case diagnostic comparison uses the same cases and is not an additional independent replication.",
    "{comparison['left']} \u51cf\u53bb {comparison['right']}：\u8d28\u91cf\u5dee {comparison['quality_difference']:.4f}，95%\u533a\u95f4 {comparison['quality_95pct_interval']}；\u63d0\u95ee\u5dee {comparison['question_difference']:.3f}，95%\u533a\u95f4 {comparison['question_95pct_interval']}。":
        "{comparison['left']} minus {comparison['right']}: quality difference {comparison['quality_difference']:.4f}, 95% interval {comparison['quality_95pct_interval']}; question difference {comparison['question_difference']:.3f}, 95% interval {comparison['question_95pct_interval']}.",
    "\u672c\u6b21\u5168\u65b0\u5b9e\u9a8c\u8bb0\u8d26 ${costs['fresh_accounted_usd']:.8f}；\u6b64\u524d ${costs['prior_accounted_usd']:.8f}；\u7d2f\u8ba1 ${costs['cumulative_accounted_usd']:.8f}；\u6388\u6743\u7d2f\u8ba1\u4e0a\u9650 ${costs['authorized_total_usd']:.8f}；\u5269\u4f59 ${costs['remaining_usd']:.8f}。":
        "Fresh study accounted cost ${costs['fresh_accounted_usd']:.8f}; prior cost ${costs['prior_accounted_usd']:.8f}; cumulative cost ${costs['cumulative_accounted_usd']:.8f}; authorized cumulative limit ${costs['authorized_total_usd']:.8f}; remaining ${costs['remaining_usd']:.8f}.",
    "\u5931\u8d25\u8c03\u7528\u672a\u77e5\u8d39\u7528\u9884\u7559\u4ecd\u4fdd\u7559；\u7f13\u5b58\u547d\u4e2d\u4e0d\u4ea7\u751f\u65b0\u7684\u4ed8\u8d39\u8c03\u7528\u6216\u72ec\u7acb\u6a21\u578b\u62bd\u6837。":
        "Reserves for unknown costs of failed calls remain included. Cache hits are neither new billed calls nor independent model samples.",
    "\u4eba\u8bc4\u6750\u6599：\u4e24\u4e2a\u5206\u522b\u968f\u673a\u6392\u5e8f\u7684100\u8f93\u51fa\u8bc4\u5206\u8868，\u9690\u85cf\u7b56\u7565\u540d\u79f0\u53ca\u81ea\u52a8\u8d28\u91cf\u5206；private\u6620\u5c04\u4ec5\u4f9b\u534f\u8c03\u4eba，\u4e0d\u53d1\u7ed9\u8bc4\u5ba1\u8005。":
        "Human review materials: two separately randomized packets with 100 outputs each. Strategy names and automatic quality scores are hidden. The private mapping is for the coordinator only and must not be given to reviewers.",
    "\u8bc4\u5206\u4e0e\u8bc4\u5ba1\u8005\u58f0\u660e\u9ed8\u8ba4\u7a7a\u767d。\u518d\u6b21\u8fd0\u884c\u5206\u6790\u4fdd\u7559\u5df2\u6709\u4eba\u5de5\u586b\u5199，\u4e0d\u5ba3\u79f0\u53cc\u4eba\u8bc4\u5ba1\u5df2\u5b8c\u6210\u6216\u771f\u6b63\u76f2\u8bc4\u5df2\u786e\u8ba4。":
        "Ratings and reviewer declarations are initially blank. Re-running the analysis preserves human-entered fields and does not claim that two-person review or actual blinding has been completed or confirmed.",
}

STATUS_MESSAGES = {
    "\u65b012\u6848\u4f8b：direct/exhaustive": "12 new pilot cases: direct/exhaustive",
    "\u65b012\u6848\u4f8b：prompt/value": "12 new pilot cases: prompt/value",
    "\u5176\u4f5928\u8bbe\u8ba1\u6848\u4f8b": "Remaining 28 design cases",
    "\u5b8c\u657420\u6848\u4f8b\u9a8c\u8bc1": "Full 20-case validation",
    "60\u6848\u4f8b\u6d4b\u8bd5\u53ca20\u6761\u8bca\u65ad": "60 test cases and 20 diagnostic trajectories",
    '{titles[stage]}：{item["completed"]}/{item["planned"]} \u6761；\u72b6\u6001 {item["status"]}':
        '{titles[stage]}: {item["completed"]}/{item["planned"]} trajectories; status {item["status"]}',
    "\u4e2d\u65ad\u4fe1\u606f：": "Interruption details: ",
    '\u4e24\u7b56\u7565\u5747\u53ef\u89e3\u6790\u5e76\u8bc4\u5206：{gate["paired_scored_cases"]}/12 \u6848\u4f8b；\u95e8\u69db 10；\u901a\u8fc7：{gate["passed"]}':
        'Both strategies parseable and scored: {gate["paired_scored_cases"]}/12 cases; threshold 10; passed: {gate["passed"]}',
    '\u5386\u53f2\u53ca\u672c\u8f6e\u7d2f\u8ba1\u8bb0\u8d26 ${budget["accounted_spend_usd"]:.8f}；\u7d2f\u8ba1\u4e0a\u9650 ${budget["authorized_total_usd"]:.2f}；\u5269\u4f59 ${budget["remaining_usd"]:.8f}':
        'Cumulative accounted cost, including history: ${budget["accounted_spend_usd"]:.8f}; cumulative limit ${budget["authorized_total_usd"]:.2f}; remaining ${budget["remaining_usd"]:.8f}',
    "\u4ee5\u4e0a\u4e3a\u4fdd\u5b58\u7684\u8fdb\u5ea6；\u7ee7\u7eed\u8fd0\u884c\u65f6\u4f1a\u91cd\u65b0\u6838\u9a8c\u5b8c\u6574\u8bc1\u636e\u4e0e\u9636\u6bb5\u95e8\u69db。":
        "The above is saved progress. Resuming will recheck the complete evidence and stage gates.",
}

CATALOG_MESSAGES = {
    "'design':'\u8bbe\u8ba1','validation':'\u9a8c\u8bc1','test':'\u6d4b\u8bd5'":
        "'design':'Design','validation':'Validation','test':'Test'",
    "'constrained_writing':'\u53d7\u7ea6\u675f\u5199\u4f5c','study_planning':'\u5b66\u4e60\u8ba1\u5212'":
        "'constrained_writing':'Constrained writing','study_planning':'Study planning'",
    "'complete':'\u4fe1\u606f\u5b8c\u6574','critical_omission':'\u5173\u952e\u5b57\u6bb5\u7f3a\u5931','critical_and_optional':'\u5173\u952e\u53ca\u53ef\u9009\u5b57\u6bb5\u7f3a\u5931','optional_only':'\u4ec5\u53ef\u9009\u5b57\u6bb5\u7f3a\u5931','unavailable_answer':'\u65e0\u6cd5\u63d0\u4f9b\u56de\u7b54','execute_now':'\u7acb\u5373\u6267\u884c'":
        "'complete':'Complete information','critical_omission':'Critical field omitted','critical_and_optional':'Critical and optional fields omitted','optional_only':'Only optional fields omitted','unavailable_answer':'Answer unavailable','execute_now':'Execute immediately'",
    "CoPrompt \u5168\u65b0120\u6848\u4f8b\u76ee\u5f55": "CoPrompt Fresh 120-Case Catalog",
    "\u65b0\u6848\u4f8b\u6e05\u5355\u4e0e\u521d\u59cb\u8bf7\u6c42，\u4e0d\u662f\u5b9e\u9a8c\u7ed3\u679c。\u5168\u90e8\u82f1\u6587\u8bf7\u6c42\u7531\u672c\u8f6e\u91cd\u65b0\u7f16\u5199，\u53c2\u8003\u65e5\u671f2027-02-01。":
        "New case inventory and initial requests; this is not a results report. All English requests were newly authored for this study, with reference date 2027-02-01.",
    "40\u8bbe\u8ba1 / 20\u9a8c\u8bc1 / 60\u6d4b\u8bd5；\u6bcf\u4e2a\u5206\u7ec4\u4e24\u4e2a\u9886\u57df\u5404\u534a。12\u8bd5\u8dd1\u5305\u542b\u4e8e\u8bbe\u8ba1\u96c6，20\u8bca\u65ad\u5305\u542b\u4e8e\u6d4b\u8bd5\u96c6。":
        "40 design / 20 validation / 60 test cases; each split has equal numbers from the two domains. The 12 pilot cases are included in the design split; the 20 diagnostic cases are included in the test split.",
    "\u672c\u76ee\u5f55\u4e0d\u5c55\u793a\u9690\u85cf\u8bc4\u5206\u7b54\u6848\u6216\u4f5c\u8005\u53ef\u884c\u793a\u4f8b。":
        "This catalog does not display hidden scoring answers or author-provided feasible examples.",
    "{splits[split]}\u96c6：{len(entries)}\u4f8b": "{splits[split]} split: {len(entries)} cases",
    "12\u4f8b\u8bd5\u8dd1\u4e4b\u4e00": "Included in the 12-case pilot",
    "20\u4f8b\u8bca\u65ad\u4e4b\u4e00": "Included in the 20-case diagnostic subset",
    "\u5bb6\u65cf：{e['family_id']}": "Family: {e['family_id']}",
    "{e['title_zh']}": "{titles[cid]}",
    "plan=json.loads((ROOT/'data/case_plan.json').read_text())":
        "plan=json.loads((ROOT/'data/case_plan.json').read_text())\ntitles=json.loads((ROOT/'data/case_titles_en.json').read_text())",
}

FORECAST_ASSUMPTIONS = {
    "\u53ea\u501f\u7528\u5386\u53f2\u9886\u57df\u5185\u6210\u672c\u7edf\u8ba1\u4f30\u8ba1\u8d39\u7528，\u4e0d\u7ee7\u627f\u4efb\u4f55\u6848\u4f8b\u6216\u54cd\u5e94；\u6240\u6709120\u90fd\u8981\u65b0\u8bf7\u6c42。":
        "Historical within-domain cost statistics are used only for cost estimation. No cases or responses are inherited; all 120 cases require new requests.",
    "\u4f4e\u60c5\u666f\u4f7f\u7528\u5355\u4f8b\u6210\u672c\u4e0b\u56db\u5206\u4f4d，\u5047\u8bbe\u8bca\u65ad\u5185\u90e8\u5b8c\u5168\u590d\u7528；\u4e2d\u60c5\u666f\u4f7f\u7528\u5747\u503c，\u8bbe\u8ba1\u52a025%、\u9a8c\u8bc1/\u6d4b\u8bd5\u52a010%，\u6bcf\u8bca\u65ad\u9884\u75591\u6b21\u51b3\u7b56、\u534a\u6b21\u751f\u6210\u53ca\u4fee\u590d。":
        "The low scenario uses the lower quartile of per-case cost and assumes complete internal reuse for diagnostics. The middle scenario uses the mean, adding 25% for design and 10% for validation/test, with one decision call and half a generation-and-repair allowance per diagnostic case.",
    "\u538b\u529b\u60c5\u666f\u4f7f\u7528\u5355\u4f8bp90\u4e581.35\u8bbe\u8ba1/1.2\u6b63\u5f0f\u9636\u6bb5，\u6bcf\u8bca\u65ad\u53e6\u52a02\u51b3\u7b56+1\u751f\u6210+1\u7ea6\u675f\u4fee\u590d，\u989d\u59165%\u5931\u8d25\u548c\u4fee\u590d\u989d\u5ea6。\u5b83\u4e0d\u662f\u603b\u8d39\u752890%\u5206\u4f4d、\u7f6e\u4fe1\u533a\u95f4\u6216\u4e25\u683c\u4e0a\u754c。":
        "The stress scenario uses per-case p90 times 1.35 for design or 1.2 for formal stages, adds two decision calls, one generation, and one constraint repair per diagnostic case, and adds a further 5% for failures and repairs. It is not the 90th percentile of total cost, a confidence interval, or a strict upper bound.",
    "\u5386\u53f2\u6d4b\u8bd5\u6309\u6848\u4f8b\u6c47\u603b\u53ef\u80fd\u5305\u542b\u8bca\u65ad\u6210\u672c，\u8fd9\u91cc\u8bca\u65ad\u53e6\u52a0\u989d\u5ea6\u6709\u90e8\u5206\u91cd\u590d\u4fdd\u5b88\u9884\u7559；\u65b0\u9898\u957f\u5ea6、\u9608\u503c、\u5931\u8d25\u91cd\u8bd5、\u5b9e\u9645\u670d\u52a1\u8d39\u7387\u548c\u5185\u90e8\u7f13\u5b58\u547d\u4e2d\u90fd\u5f71\u54cd\u6210\u672c。":
        "Historical test costs aggregated by case may include diagnostic costs, so the additional diagnostic allowance partly duplicates costs conservatively. New request length, thresholds, retries, actual provider rates, and internal cache hits all affect cost.",
    "\u5c1a\u4f590.16142615\u7f8e\u5143\u53ef\u80fd\u5b8c\u6210\u4e2d\u60c5\u666f，\u4f46\u4e0d\u80fd\u4fdd\u8bc1\u5168\u90e8\u5b8c\u6210。\u7a0b\u5e8f\u9010\u8bf7\u6c42\u6309\u539f\u7d2f\u8ba10.25\u7f8e\u5143\u4e0a\u9650\u62e6\u622a，\u4f59\u989d\u4e0d\u8db3\u5373\u4fdd\u5b58\u5e76\u505c\u6b62；\u7edd\u4e0d\u81ea\u52a8\u63d0\u9ad8\u6216\u6e05\u96f6。":
        "At forecast preparation time, the remaining USD 0.16142615 might cover the middle scenario, but completion was not guaranteed. The program enforced the then-authorized cumulative USD 0.25 limit before each request and saved progress and stopped when funds were insufficient; it never automatically raised or reset the limit.",
    "\u53ea\u8fd0\u884coffline\u811a\u672c，\u4e0d\u8054\u7f51、\u4e0d\u8bfb\u53d6\u5bc6\u94a5、\u4e0d\u65b0\u589eAPI\u652f\u51fa。":
        "Only offline scripts were run: no network access, no key reading, and no additional API spending.",
}

LAUNCHER_MESSAGES = {
    "\u9700\u8981 Python 3.10 \u6216\u66f4\u65b0\u7248\u672c。": "Python 3.10 or newer is required.",
    "\u6309\u56de\u8f66\u5173\u95ed。": "Press Enter to close.",
    "CoPrompt \u5168\u65b0120\u4f8b：40\u8bbe\u8ba1＋20\u9a8c\u8bc1＋60\u6d4b\u8bd5。":
        "CoPrompt Fresh 120 Cases: 40 design + 20 validation + 60 test.",
    "\u987a\u5e8f：12\u4f8b\u57fa\u7840\u8bd5\u8dd1→\u540c12\u4f8b\u53e6\u5916\u4e24\u7b56\u7565→\u5176\u4f5928\u8bbe\u8ba1→20\u9a8c\u8bc1→60\u6d4b\u8bd5\u4e0e20\u6761\u8bca\u65ad。":
        "Sequence: 12-case baseline pilot -> the other two strategies on the same 12 cases -> remaining 28 design cases -> 20 validation cases -> 60 test cases and 20 diagnostic trajectories.",
    "\u672c\u8f6e\u4e0d\u4f1a\u5bfc\u5165\u65e7\u6848\u4f8b\u6216\u65e7\u54cd\u5e94。\u65b0\u5b9e\u9a8c\u5185\u90e8\u7684\u7cbe\u786e\u9996\u54cd\u5e94\u53ef\u590d\u7528；\u7d2f\u8ba1\u8d26\u672c\u4fdd\u7559\u5168\u90e8\u5386\u53f2\u8d39\u7528。":
        "No previous cases or responses are imported. Exact first responses within this study may be reused; the cumulative ledger retains all historical costs.",
    "\u79bb\u7ebf\u68c0\u67e5\u672a\u901a\u8fc7，\u5c1a\u672a\u8bfb\u53d6\u5bc6\u94a5，\u4e5f\u6ca1\u6709\u8c03\u7528API。":
        "Offline checks failed. No key has been read and no API call has been made.",
    "\u8bf7\u5728\u4e0b\u4e00\u884c\u7684\u9690\u85cf\u8f93\u5165\u5904\u8f93\u5165\u672c\u673a API \u5bc6\u94a5，\u518d\u6309\u56de\u8f66；\u5c4f\u5e55\u4e0d\u4f1a\u663e\u793a\u5b57\u7b26。":
        "Enter your local API key at the next hidden prompt, then press Enter. Characters will not appear on screen.",
    "\u5bc6\u94a5\u53ea\u7528\u4e8e\u672c\u6b21\u8fdb\u7a0b，\u4e0d\u4fdd\u5b58。\u82e5\u76f4\u63a5\u56de\u8f66\u800c\u672a\u8f93\u5165，\u8bf7\u5173\u95ed\u5e76\u91cd\u65b0\u542f\u52a8，\u4e0d\u8981\u5728\u7ed3\u675f\u63d0\u793a\u5904\u8f93\u5165\u5bc6\u94a5。":
        "The key is used only by this process and is not saved. If you press Enter without entering it, close and restart. Do not enter a key at the final closing prompt.",
    "\u5168\u65b0120\u4f8b\u7684\u4e94\u9636\u6bb5\u8fd0\u884c\u548c\u81ea\u52a8\u5206\u6790\u5b8c\u6574\u5b8c\u6210。\u4eba\u5de5\u5185\u5bb9\u8bc4\u5ba1\u4ecd\u9700\u771f\u5b9e\u8bc4\u5ba1\u4eba\u586b\u5199。":
        "All five stages and automatic analysis of the fresh 120-case study are complete. Human content review still requires actual reviewers.",
    "\u8fd0\u884c\u9636\u6bb5\u5df2\u7ed3\u675f，\u4f46\u5206\u6790\u68c0\u67e5\u672a\u901a\u8fc7。\u4fdd\u7559\u5168\u90e8\u8bb0\u5f55\u5e76\u628a\u72b6\u6001\u53cd\u9988\u5230\u5f53\u524d\u5bf9\u8bdd。":
        "Execution stages finished, but analysis checks failed. Preserve all records and report this status to the project coordinator.",
    "\u5b9e\u9a8c\u5c1a\u672a\u5b8c\u6574\u5b8c\u6210；\u8fdb\u5ea6\u5df2\u4fdd\u5b58。\u8bf7\u628a\u72b6\u6001\u53cd\u9988\u5230\u5f53\u524d\u5bf9\u8bdd，\u4e0d\u8981\u5220\u9664\u7f13\u5b58\u6216\u91cd\u7f6e\u8d26\u672c。":
        "The experiment is not yet complete; progress is saved. Report this status to the project coordinator. Do not delete caches or reset the ledger.",
    "\u73b0\u5728\u4e0d\u518d\u63a5\u6536\u5bc6\u94a5。": "No further key input is accepted.",
    "\u6309\u56de\u8f66\u5173\u95ed\u7a97\u53e3。": "Press Enter to close the window.",
}


def translate_source(relative_path, text):
    """Apply explicit source-only substitutions; do not transform evidence."""
    mappings = [PATH_REPLACEMENTS, KEY_REPLACEMENTS, REVIEW_INSTRUCTIONS,
                LIMITATIONS, ANALYSIS_MESSAGES, STATUS_MESSAGES,
                FORECAST_ASSUMPTIONS]
    if relative_path.endswith("/work/build_catalog.py"):
        mappings.append(CATALOG_MESSAGES)
    if relative_path.endswith(".command"):
        mappings.append(LAUNCHER_MESSAGES)
    for mapping in mappings:
        for old, new in sorted(mapping.items(), key=lambda pair: len(pair[0]), reverse=True):
            text = text.replace(old, new)
    return text


def translate_metadata(value):
    """Localize only presentation metadata, never trajectory/model content.

    The caller must restrict use to analysis.json, reviewer packets, and the
    budget forecast document. This performs exact whole-string substitutions.
    """
    strings = {**REVIEW_INSTRUCTIONS, **LIMITATIONS, **FORECAST_ASSUMPTIONS}
    if isinstance(value, dict):
        return {KEY_REPLACEMENTS.get(k, k): translate_metadata(v) for k, v in value.items()}
    if isinstance(value, list):
        return [translate_metadata(v) for v in value]
    if isinstance(value, str):
        return strings.get(value, value)
    return value
