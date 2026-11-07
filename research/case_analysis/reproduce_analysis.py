"""Describe saved CoPrompt test trajectories and unchanged returned reviews."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
POLICIES = ["direct", "exhaustive", "prompt_only", "value_based"]
VARIANTS = POLICIES + ["importance_one"]
CASES = ["NTSP13", "NTSP02", "NTSP07", "NTCW13", "NTCW20", "NTCW24", "NTCW08", "NTSP28"]
CHECKS = ["word_count", "contains_all", "date_window", "daily_minutes_cap",
          "topic_coverage", "topic_minutes_min"]
DIMS = ["usefulness_1_to_5", "coherence_1_to_5", "audience_fit_1_to_5",
        "feasibility_1_to_5", "unsupported_assumptions_count", "unnecessary_questions_count"]


def read(name):
    return json.loads((INPUTS / name).read_text(encoding="utf-8"))


def read_lines(name):
    return [json.loads(line) for line in (INPUTS / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def table(name, rows):
    with (ROOT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    manifest = json.loads((ROOT / "source_manifest.json").read_text(encoding="utf-8"))
    for source in manifest["sources"]:
        if hashlib.sha256((ROOT / source["copied_path"]).read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Source changed: " + source["copied_path"])
    trajectories = read_lines("test_trajectories.jsonl")
    requests = {row["case_id"]: row for row in read_lines("test_requests.jsonl")}
    answers = {row["case_id"]: row for row in read_lines("test_answers.jsonl")}
    annotations = {row["case_id"]: row for row in read_lines("test_annotations.jsonl")}
    official = read("official_analysis.json")
    human_stats = read("human_statistics.json")
    mapping = read("reviewer_policy_mapping.json")
    by_key = {(row["case_id"], row["system_id"]): row for row in trajectories}
    if len(by_key) != len(trajectories) or len(trajectories) != 260:
        raise ValueError("Expected 240 main and 20 diagnostic trajectories")
    diagnostic_ids = official["diagnostic"]["case_ids"]
    if len(requests) != 60 or len(diagnostic_ids) != 20 or not set(CASES) <= set(diagnostic_ids):
        raise ValueError("Unexpected cohort or case-study selection")
    if set(by_key) != {(cid, pol) for cid in requests for pol in POLICIES} | {
            (cid, "importance_one") for cid in diagnostic_ids}:
        raise ValueError("Test trajectory coverage mismatch")
    reviews = {}
    for slot in (1, 2):
        returned = read(f"reviewer_{slot}_returned.json")
        if returned["source_evidence_sha256"] != mapping["source_evidence_sha256"]:
            raise ValueError("Review source evidence mismatch")
        index = {item["review_item_id"]: item for item in mapping["reviewer_mappings"][str(slot)]}
        records = {(index[row["review_item_id"]]["case_id"], index[row["review_item_id"]]["variant"]): row
                   for row in returned["records"]}
        if set(records) != {(cid, variant) for cid in diagnostic_ids for variant in VARIANTS}:
            raise ValueError("Review coverage mismatch")
        for key, record in records.items():
            trajectory = by_key[key]
            request = requests[key[0]]
            for field in ("domain", "initial_request", "reference_date", "user_control"):
                if record[field] != request[field]:
                    raise ValueError("Review request differs from experiment")
            visible_exchanges = [{key: event[key] for key in ("question", "answer_text", "status")}
                                 for event in trajectory["visible_exchanges"]]
            if record["visible_exchanges"] != visible_exchanges or record["output"] != trajectory["output"]:
                raise ValueError("Review-visible trajectory differs from experiment")
            if any(type(record["ratings"][dimension]) is not int for dimension in DIMS):
                raise ValueError("Missing returned rating")
        reviews[slot] = records

    failures = []
    policy_rows = []
    domain_rows = []
    trace_rows = []
    for policy in POLICIES:
        rows = [row for row in trajectories if row["system_id"] == policy]
        totals = Counter()
        failed = Counter()
        failed_cases = {kind: set() for kind in CHECKS}
        for row in rows:
            checks = row["score"]["constraint_results"]
            if row["score"]["status"] != "scored" or abs(mean(int(x["passed"]) for x in checks) - row["score"]["quality"]) > 1e-12:
                raise ValueError("Saved score inconsistent with saved constraint checks")
            for check in checks:
                kind = check["check_type"]
                totals[kind] += 1
                if not check["passed"]:
                    failed[kind] += 1
                    failed_cases[kind].add(row["case_id"])
            trace_rows.append({
                "case_id": row["case_id"], "system": policy, "domain": row["domain"],
                "saved_quality": row["score"]["quality"], "questions": row["question_items"],
                "asked_fields": ";".join(event["field_id"] for event in row["visible_exchanges"]),
                "answer_statuses": ";".join(event["status"] for event in row["visible_exchanges"]),
                "failed_check_types": ";".join(x["check_type"] for x in checks if not x["passed"]),
                "failed_constraint_ids": ";".join(x["constraint_id"] for x in checks if not x["passed"]),
                "stop_reason": row["decisions"][-1].get("stop_reason", ""),
                "invalid_questions": row["invalid_question_items"],
                "generation_constraint_revision_attempted": row["generation"].get("constraint_repair_attempted", False),
            })
        for kind in CHECKS:
            failures.append({"system": policy, "check_type": kind,
                             "failed_checks": failed[kind], "evaluated_checks": totals[kind],
                             "cases_with_failure": len(failed_cases[kind]),
                             "case_ids": ";".join(sorted(failed_cases[kind]))})
        optional = sum(not annotations[row["case_id"]]["field_annotations"].get(
            event["field_id"], {"critical": True})["critical"]
            for row in rows for event in row["visible_exchanges"] if event["status"] != "error")
        summary = {"system": policy, "cases": len(rows),
                   "mean_quality": mean(row["score"]["quality"] for row in rows),
                   "mean_questions": mean(row["question_items"] for row in rows),
                   "total_questions": sum(row["question_items"] for row in rows),
                   "fully_passing_cases": sum(row["score"]["quality"] == 1 for row in rows),
                   "cases_with_failed_constraints": sum(row["score"]["quality"] < 1 for row in rows),
                   "noncritical_question_items": optional,
                   "format_failures": sum(row["score"]["format_failure"] for row in rows),
                   "invalid_question_items": sum(row["invalid_question_items"] for row in rows),
                   "generation_revision_trajectories": sum(bool(row["generation"].get("constraint_repair_attempted")) for row in rows)}
        registered = official["cohorts"]["fresh_test"]["statistics"][policy]
        for key, registered_key in [("mean_quality", "mean_quality"), ("mean_questions", "mean_questions"),
                                    ("total_questions", "total_questions"), ("fully_passing_cases", "full_pass"),
                                    ("noncritical_question_items", "noncritical_questions"), ("format_failures", "format_failures")]:
            if abs(summary[key] - registered[registered_key]) > 1e-12:
                raise ValueError("Summary differs from official frozen result: " + key)
        policy_rows.append(summary)
        for domain in ("constrained_writing", "study_planning"):
            subset = [row for row in rows if row["domain"] == domain]
            domain_rows.append({"system": policy, "domain": domain, "cases": len(subset),
                                "mean_quality": mean(row["score"]["quality"] for row in subset),
                                "mean_questions": mean(row["question_items"] for row in subset),
                                "fully_passing_cases": sum(row["score"]["quality"] == 1 for row in subset)})

    human_rows = []
    for cid in diagnostic_ids:
        for variant in VARIANTS:
            for slot in (1, 2):
                record = reviews[slot][(cid, variant)]
                row = {"case_id": cid, "system": variant, "reviewer_slot": slot,
                       "review_item_id": record["review_item_id"],
                       "saved_auto_quality": by_key[(cid, variant)]["score"]["quality"],
                       "actual_question_items": by_key[(cid, variant)]["question_items"]}
                row.update(record["ratings"])
                human_rows.append(row)

    case_rows = []
    evidence = []
    for cid in CASES:
        item = {"case_id": cid, "public_request": requests[cid],
                "scope": "Illustrative case selected after inspection, from the existing 20-case human/diagnostic subset; not a new evaluation cohort.",
                "variants": []}
        for variant in VARIANTS:
            trajectory = by_key[(cid, variant)]
            row = {"case_id": cid, "system": variant,
                   "saved_auto_quality": trajectory["score"]["quality"],
                   "question_items": trajectory["question_items"],
                   "failed_checks": ";".join(x["check_type"] for x in trajectory["score"]["constraint_results"] if not x["passed"])}
            for slot in (1, 2):
                rating = reviews[slot][(cid, variant)]
                row[f"reviewer_{slot}_item_id"] = rating["review_item_id"]
                row.update({f"reviewer_{slot}_{dimension}": rating["ratings"][dimension] for dimension in DIMS})
            case_rows.append(row)
            item["variants"].append({"trajectory": trajectory,
                                     "reviewer_1_original_record": reviews[1][(cid, variant)],
                                     "reviewer_2_original_record": reviews[2][(cid, variant)]})
        if cid == "NTSP07":
            item["offline_only_unasked_topic_answer"] = answers[cid]["answers"]["topics"]
            item["boundary_note"] = "This answer was available through a permitted ASK, but not visible in the observed trajectory. It explains offline scoring only and was not used to change human ratings or model state."
        evidence.append(item)

    value_rows = [by_key[(cid, "value_based")] for cid in requests]
    net_values = Counter(value for row in value_rows for decision in row["decisions"] for value in decision.get("values", {}).values())
    rating_pairs = Counter((rating["importance"], rating["uncertainty"])
                           for row in value_rows for decision in row["decisions"] for rating in decision.get("ratings", []))
    stops = Counter(row["decisions"][-1].get("stop_reason") for row in value_rows)
    matching_counts = sum(by_key[(cid, "value_based")]["question_items"] == by_key[(cid, "exhaustive")]["question_items"] for cid in requests)
    matching_sets = sum(set(event["field_id"] for event in by_key[(cid, "value_based")]["visible_exchanges"])
                        == set(event["field_id"] for event in by_key[(cid, "exhaustive")]["visible_exchanges"]) for cid in requests)
    matching_orders = sum([event["field_id"] for event in by_key[(cid, "value_based")]["visible_exchanges"]]
                          == [event["field_id"] for event in by_key[(cid, "exhaustive")]["visible_exchanges"]] for cid in requests)
    matching_outputs = sum(by_key[(cid, "value_based")]["output"] == by_key[(cid, "exhaustive")]["output"] for cid in requests)
    diagnostic_equal = all(
        by_key[(cid, "value_based")]["score"]["quality"] == by_key[(cid, "importance_one")]["score"]["quality"] == by_key[(cid, "exhaustive")]["score"]["quality"]
        and by_key[(cid, "value_based")]["question_items"] == by_key[(cid, "importance_one")]["question_items"] == by_key[(cid, "exhaustive")]["question_items"]
        for cid in diagnostic_ids)

    checks = {
        "main_trajectories": 240, "diagnostic_trajectories": 20,
        "reviewed_outputs": 100, "returned_assessments": 200,
        "illustrative_cases": CASES,
        "all_illustrations_within_existing_human_subset": True,
        "review_material_matches_saved_trajectories": True,
        "saved_scores_match_saved_constraint_checks": True,
        "main_summaries_match_official_analysis": True,
        "original_inputs_unchanged": True,
        "new_model_calls": 0, "new_ratings": 0, "new_gold_labels": 0,
        "new_significance_tests": 0, "disagreements_adjudicated": 0,
    }
    result = {
        "analysis_date": "2026-10-27", "timezone": "Asia/Singapore",
        "scope": "Proposal sections 1, 4.1, 5 and 6: descriptive analysis of saved successful/failed trajectories and existing human assessments; no experiment extension.",
        "main_test": policy_rows, "domain_descriptive": domain_rows,
        "constraint_failure_counts": failures,
        "threshold_diagnostic": {
            "selected_lambda": read("lambda_selection.json")["selected_lambda"],
            "candidate_net_values": {str(k): v for k, v in sorted(net_values.items())},
            "candidate_rating_pairs": [{"importance": key[0], "uncertainty": key[1], "count": count}
                                       for key, count in sorted(rating_pairs.items())],
            "stop_reasons": dict(stops),
            "equal_question_counts_value_vs_exhaustive_cases": matching_counts,
            "equal_question_sets_value_vs_exhaustive_cases": matching_sets,
            "equal_question_orders_value_vs_exhaustive_cases": matching_orders,
            "equal_final_outputs_value_vs_exhaustive_cases": matching_outputs,
            "diagnostic_20_all_equal_quality_and_question_count": diagnostic_equal,
            "paired_intervals_copied_from_existing_analysis": official["cohorts"]["fresh_test"]["paired_comparisons"],
        },
        "human_review_existing_results": {
            "system_summary": human_stats["system_summary"],
            "agreement": human_stats["agreement"],
            "unresolved_original_count_warning": human_stats["validation"]["semantic_count_warnings"],
        },
        "validation": checks,
        "interpretation_limits": [
            "Constraint-type failures may overlap within a case; topic-minimum checks can occur more than once per case. They do not replace the original case-averaged primary metric.",
            "Qualitative stage explanations are evidence-based interpretations, not causal effects estimated by new interventions.",
            "All detailed examples are a purposive selection from the original 20-case subset; their selection does not estimate error prevalence.",
            "Unasked answers are consulted only for offline scoring explanation, never applied to a reviewer who did not see them.",
            "Human scores/notes retain AI-assistance history, disagreement, and the original inconsistent unnecessary-question count. No new LLM judge is used.",
            "Cache-reused identical outputs and the importance-one diagnostic are not independent model replications.",
        ],
    }
    table("main_test_summary.csv", policy_rows)
    table("constraint_failures.csv", failures)
    table("domain_summary.csv", domain_rows)
    table("main_trajectory_index.csv", trace_rows)
    table("case_comparison.csv", case_rows)
    table("human_review_evidence.csv", human_rows)
    save("findings.json", result)
    save("selected_case_evidence.json", evidence)
    save("validation_receipt.json", checks)
    print(json.dumps({"status": "verified_saved_evidence_analysis", "validation": checks,
                      "threshold_diagnostic": result["threshold_diagnostic"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
