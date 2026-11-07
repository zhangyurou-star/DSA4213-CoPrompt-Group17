"""Reproduce the proposal-specified human-review summaries from unchanged inputs."""
import csv
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
POLICIES = ["direct", "exhaustive", "prompt_only", "value_based", "importance_one"]
SCALES = {
    "usefulness_1_to_5": "有用性",
    "coherence_1_to_5": "连贯性",
    "audience_fit_1_to_5": "受众适配",
    "feasibility_1_to_5": "可行性",
}
COUNTS = {
    "unsupported_assumptions_count": "无依据假设数",
    "unnecessary_questions_count": "不必要提问数",
}
DIMENSIONS = dict(SCALES, **COUNTS)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(name, value):
    (ROOT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def save_csv(name, rows):
    with (ROOT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def linear_kappa(left, right):
    """Five fixed levels; agreement weight = 1 - abs(i-j)/4."""
    size = len(left)
    matrix = [[0] * 5 for _ in range(5)]
    for a, b in zip(left, right):
        matrix[a - 1][b - 1] += 1
    row_totals = [sum(row) for row in matrix]
    col_totals = [sum(matrix[i][j] for i in range(5)) for j in range(5)]
    observed = sum(
        Fraction(abs(i - j), 4) * matrix[i][j] / size
        for i in range(5) for j in range(5)
    )
    expected = sum(
        Fraction(abs(i - j), 4) * row_totals[i] * col_totals[j] / (size * size)
        for i in range(5) for j in range(5)
    )
    kappa = 1 - observed / expected if expected else None
    return kappa, observed, expected, matrix


def main():
    source_manifest = load(ROOT / "source_manifest.json")
    for source in source_manifest["sources"]:
        path = ROOT / source["copied_path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
            raise ValueError("Changed input: " + source["copied_path"])

    mapping = load(INPUTS / "reviewer_policy_mapping.json")
    compatibility = load(INPUTS / "packet_compatibility.json")
    evidence_hash = mapping["source_evidence_sha256"]
    reviews = {}
    declarations = {}
    assistance = {}
    warnings = []
    confirmation_count = 0

    for slot in (1, 2):
        returned = load(INPUTS / f"reviewer_{slot}_returned.json")
        original = load(INPUTS / f"reviewer_{slot}_source_packet.json")
        if returned["reviewer_slot"] != slot:
            raise ValueError("Reviewer slot mismatch")
        if not returned["source_evidence_sha256"] == original["source_evidence_sha256"] == evidence_hash:
            raise ValueError("Evidence fingerprint mismatch")
        expected_hash = compatibility["reviewer_slots"][str(slot)]["source_packet_sha256"]
        if returned["review_form"]["source_packet_sha256"] != expected_hash:
            raise ValueError("Source packet fingerprint mismatch")
        state = returned["review_form_state"]
        if (state["source_packet_sha256"] != expected_hash
                or state["source_evidence_sha256"] != evidence_hash
                or state["reviewer_slot"] != slot):
            raise ValueError("Review form state fingerprint mismatch")
        if returned["reviewer_declaration"] != state["declaration"]:
            raise ValueError("Reviewer declaration/state mismatch")
        originals = {item["review_item_id"]: item for item in original["records"]}
        identities = {
            item["review_item_id"]: item
            for item in mapping["reviewer_mappings"][str(slot)]
        }
        ids = [item["review_item_id"] for item in returned["records"]]
        if (len(ids) != 100 or len(set(ids)) != 100
                or ids != [item["review_item_id"] for item in original["records"]]
                or set(ids) != set(identities)):
            raise ValueError("Record IDs/order mismatch")
        reviews[slot] = {}
        for record in returned["records"]:
            item_id = record["review_item_id"]
            unchanged = {k: v for k, v in record.items() if k != "ratings"}
            expected = {k: v for k, v in originals[item_id].items() if k != "ratings"}
            if unchanged != expected:
                raise ValueError("Source material changed: " + item_id)
            item_state = state["items"][item_id]
            if (not item_state["confirmed_at"] or item_state["unable"]
                    or not all(item_state["checks"].get(k) for k in ("request", "questions", "output"))):
                raise ValueError("Unconfirmed/incomplete item: " + item_id)
            if item_state["confirmed_by"] != returned["reviewer_declaration"]["reviewer_name_or_id"]:
                raise ValueError("Confirmation identity mismatch: " + item_id)
            for dimension in DIMENSIONS:
                value = record["ratings"][dimension]
                if type(value) is not int:
                    raise ValueError("Missing/noninteger rating: " + item_id)
                if dimension in SCALES and not 1 <= value <= 5:
                    raise ValueError("Rating outside fixed scale: " + item_id)
                if dimension in COUNTS and value < 0:
                    raise ValueError("Negative count: " + item_id)
                if str(value) != item_state["values"][dimension]:
                    raise ValueError("Confirmed rating/state mismatch: " + item_id)
            if record["ratings"]["notes"] != item_state["note"]:
                raise ValueError("Note/state mismatch: " + item_id)
            identity = identities[item_id]
            key = (identity["case_id"], identity["variant"])
            if key in reviews[slot]:
                raise ValueError("Duplicate matched output")
            reviews[slot][key] = record
            confirmation_count += 1
            count = record["ratings"]["unnecessary_questions_count"]
            actual_questions = len(record["visible_exchanges"])
            if count > actual_questions:
                warnings.append({
                    "reviewer_slot": slot, "review_item_id": item_id,
                    "case_id": key[0], "variant": key[1],
                    "dimension": "unnecessary_questions_count",
                    "reported_value": count, "visible_question_items": actual_questions,
                    "treatment": "Original value retained in every statistic; no adjudication or correction.",
                })
        declarations[str(slot)] = returned["reviewer_declaration"]
        assistance[str(slot)] = {
            "ai_assistance_metadata": returned.get("ai_assistance"),
            "records_with_AI_in_notes": sum(
                "AI" in item["ratings"]["notes"] for item in returned["records"]
            ),
            "review_revision_metadata_present": "review_revision" in returned,
        }

    keys = sorted(reviews[1])
    if set(keys) != set(reviews[2]):
        raise ValueError("Unpaired outputs")
    if len({key[0] for key in keys}) != 20 or len(keys) != 100:
        raise ValueError("Expected 20 cases x five variants")
    for policy in POLICIES:
        if sum(key[1] == policy for key in keys) != 20:
            raise ValueError("Variant coverage mismatch")
    for key in keys:
        for field in ("domain", "initial_request", "reference_date", "user_control",
                      "visible_exchanges", "output", "unparsed_generation_text"):
            if reviews[1][key][field] != reviews[2][key][field]:
                raise ValueError("Matched materials differ: " + str(key))

    system_rows = []
    reviewer_rows = []
    for policy in POLICIES:
        policy_keys = [key for key in keys if key[1] == policy]
        row = {"system": policy, "cases": 20, "outputs": 20, "reviewers": 2,
               "assessments": 40}
        for dimension in DIMENSIONS:
            per_output = [Fraction(reviews[1][key]["ratings"][dimension]
                                   + reviews[2][key]["ratings"][dimension], 2)
                          for key in policy_keys]
            value = mean(per_output)
            pooled = mean(Fraction(reviews[slot][key]["ratings"][dimension])
                          for slot in (1, 2) for key in policy_keys)
            if value != pooled:
                raise ValueError("Aggregation verification failed")
            row[dimension + "_mean"] = float(value)
        system_rows.append(row)
        for slot in (1, 2):
            detail = {"reviewer_slot": slot, "system": policy, "outputs": 20}
            detail.update({dimension + "_mean": float(mean(
                Fraction(reviews[slot][key]["ratings"][dimension]) for key in policy_keys
            )) for dimension in DIMENSIONS})
            reviewer_rows.append(detail)

    agreement_rows = []
    agreement_detail = {}
    confusion_rows = []
    for dimension in DIMENSIONS:
        left = [reviews[1][key]["ratings"][dimension] for key in keys]
        right = [reviews[2][key]["ratings"][dimension] for key in keys]
        exact_count = sum(a == b for a, b in zip(left, right))
        mad = mean(Fraction(abs(a - b)) for a, b in zip(left, right))
        row = {"dimension": dimension, "dimension_zh": DIMENSIONS[dimension],
               "paired_outputs": 100, "linearly_weighted_kappa": "",
               "exact_agreement_count": exact_count,
               "exact_agreement_proportion": exact_count / 100,
               "mean_absolute_difference_count_items_only": ""}
        details = dict(row)
        if dimension in SCALES:
            kappa, observed, expected, matrix = linear_kappa(left, right)
            row["linearly_weighted_kappa"] = float(kappa) if kappa is not None else "NA"
            details.update(row)
            details.update({
                "fixed_levels": [1, 2, 3, 4, 5],
                "agreement_weight": "1 - abs(i-j)/4",
                "observed_weighted_disagreement": float(observed),
                "expected_weighted_disagreement": float(expected),
                "kappa_exact_fraction": str(kappa) if kappa is not None else None,
                "undefined_reason": "Expected weighted disagreement is zero" if kappa is None else None,
                "confusion_matrix_rows_reviewer1_columns_reviewer2": matrix,
            })
            # Check the matrix implementation with distances computed directly from raw vectors.
            observed_distance = sum(abs(a - b) for a, b in zip(left, right))
            expected_distance = sum(abs(a - b) for a in left for b in right)
            independent = 1 - Fraction(100 * observed_distance, expected_distance) if expected_distance else None
            if independent != kappa:
                raise ValueError("Kappa verification failed")
            for i in range(5):
                for j in range(5):
                    confusion_rows.append({"dimension": dimension, "reviewer_1_rating": i + 1,
                                           "reviewer_2_rating": j + 1, "paired_outputs": matrix[i][j]})
        else:
            row["mean_absolute_difference_count_items_only"] = float(mad)
            details.update(row)
        agreement_rows.append(row)
        agreement_detail[dimension] = details

    paired_rows = []
    for key in keys:
        row = {"case_id": key[0], "system": key[1], "domain": reviews[1][key]["domain"]}
        for slot in (1, 2):
            record = reviews[slot][key]
            row[f"reviewer_{slot}_item_id"] = record["review_item_id"]
            row.update({f"reviewer_{slot}_{dimension}": record["ratings"][dimension]
                        for dimension in DIMENSIONS})
        paired_rows.append(row)

    validation = {
        "returned_records": 200, "confirmed_complete_assessments": confirmation_count,
        "numeric_ratings_checked": 1200, "missing_numeric_ratings": 0,
        "matched_outputs": 100, "distinct_cases": 20, "variants": 5,
        "cases_per_domain": dict(Counter(reviews[1][(case, "direct")]["domain"]
                                         for case in sorted({key[0] for key in keys}))),
        "immutable_materials_IDs_and_order_match_original_packets": True,
        "packet_and_evidence_fingerprints_match": True,
        "matching_key": ["case_id", "variant"],
        "original_files_and_scores_modified": False,
        "aggregation_crosscheck": "Per-output two-reviewer average equals pooled rating mean exactly.",
        "kappa_crosscheck": "Exact-fraction confusion-matrix calculation equals direct-vector distance calculation.",
        "semantic_count_warnings": warnings,
        "warnings_do_not_change_input_ratings": True,
    }
    result = {
        "analysis_date_local": "2026-10-27", "timezone": "Asia/Singapore",
        "stage": "Supplied returned versions; no inter-reviewer adjudication performed in this statistical analysis. Prior AI-assisted revisions remain documented in the unchanged input files.",
        "source_evidence_sha256": evidence_hash,
        "proposal_scope": "20 preselected test cases x five variants x two reviewers; 100 outputs, 200 assessments.",
        "system_aggregation": "Average the two returned ratings per output, then average the 20 matched outputs per variant; dimensions remain separate.",
        "agreement_method": "Linear weighted Cohen kappa for each fixed five-level rating; exact agreement and mean absolute difference for count items. Undefined kappa is NA with exact agreement.",
        "no_additional_hypothesis_tests_or_composite_score": True,
        "system_summary": system_rows, "reviewer_system_summary": reviewer_rows,
        "agreement": agreement_detail, "validation": validation,
        "reviewer_declarations_as_returned": declarations,
        "AI_assistance_disclosure_as_recorded": assistance,
        "limitations": [
            "These results concern only the preselected 20-case subset, not the full 60-case main test.",
            "The same 20 cases contribute all five variants; duplicate contents remain as originally assigned. Assessments are not independent cases.",
            "AI-assisted suggestions and human confirmation are documented in both returns. This departs from the proposal's no-LLM-judge plan; agreement does not establish unaided independent human judgment.",
            "Reviewer declarations report independent completion and blinding. Reviewer 1 AI metadata also says actual blinding was not certified. Statistical checking cannot resolve that provenance limitation.",
            "One unnecessary-question count exceeds the visible question count. It is flagged and retained, as agreement is calculated before resolving disagreements.",
            "No disagreements were resolved, ratings altered, missing values imputed, or new model calls made.",
        ],
    }
    save_csv("system_summary.csv", system_rows)
    save_csv("reviewer_system_summary.csv", reviewer_rows)
    save_csv("agreement.csv", agreement_rows)
    save_csv("paired_ratings.csv", paired_rows)
    save_csv("confusion_matrices.csv", confusion_rows)
    save_json("statistics.json", result)
    save_json("validation_receipt.json", validation)

    lines = [
        "# CoPrompt 人工评审统计（分歧处理前）", "",
        "统计日期：2026-10-27（Asia/Singapore）。本交付只完成人评汇总和一致性统计。", "",
        "## 样本与计算口径", "",
        "按 proposal 第 5 节：20 个预选测试案例，每个案例含四个主系统及一个重要性诊断版本，"
        "共 100 份输出。两位评审员各评 100 份，共 200 次评价。两领域各 10 个案例。"
        "每份评价含四个分别报告的 1–5 分维度，以及两项非负整数计数。", "",
        "两份回传文件的全部 200 项均已确认，1,200 个数值均完整。材料、原始编号、顺序、"
        "证据指纹及表单状态均已核对。两份表的随机顺序不同，因此使用“案例 ID＋系统版本”配对，"
        "没有按行号配对。原始文件和评分保留不变。", "",
        "每个系统的每个维度先对同一输出的两位评分取均值，再对 20 个案例取均值。"
        "下表每行是 20 份输出、40 次评价；四个评分维度分别报告，不合成为一个总分。", "",
        "## 按系统汇总", "",
        "| 系统 | 有用性 | 连贯性 | 受众适配 | 可行性 | 无依据假设数／输出 | 不必要提问数／输出 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in system_rows:
        lines.append("| " + row["system"] + " | " + " | ".join(
            f"{row[d + '_mean']:.3f}" for d in DIMENSIONS
        ) + " |")
    lines += [
        "", "前四行为主系统，importance_one 是相同 20 个案例上的诊断版本。"
        "它不是额外独立样本。计数列也是两位原始计数的平均值。", "",
        "## 四项评分的一致性", "",
        "严格使用预先固定的五级尺度 {1,2,3,4,5}，线性权重为 w(i,j)=1−|i−j|/4。"
        "每个维度都在 100 对原始评分上单独计算 Cohen’s κ；若期望加权分歧为零，"
        "κ 记为 NA，并报告完全一致率。本次四个 κ 均有定义。", "",
        "| 评分维度 | 配对输出数 | 线性加权 κ | 完全一致率 |",
        "|---|---:|---:|---:|",
    ]
    for row in agreement_rows[:4]:
        kappa = row["linearly_weighted_kappa"]
        lines.append(f"| {row['dimension_zh']} | 100 | {kappa:.4f} | {row['exact_agreement_count']}/100（{row['exact_agreement_proportion']:.0%}） |")
    lines += [
        "", "## 两项计数的一致性", "",
        "按 proposal 对计数项报告完全一致率和平均绝对差（MAD），不另用 κ 替代。"
        "MAD 为 100 对计数差的绝对值的平均。", "",
        "| 计数项目 | 配对输出数 | 完全一致率 | 平均绝对差（项／输出） |",
        "|---|---:|---:|---:|",
    ]
    for row in agreement_rows[4:]:
        lines.append(f"| {row['dimension_zh']} | 100 | {row['exact_agreement_count']}/100（{row['exact_agreement_proportion']:.0%}） | {row['mean_absolute_difference_count_items_only']:.3f} |")
    lines += [
        "", "## 原值保留及方法说明", "",
        "1. 一项计数存在轨迹冲突：评审员 2 的 R2-002（NTCW13，direct）记录了 3 个不必要提问，"
        "但材料中提问轨迹为 0。所有表格和一致性统计均保留原值 3，没有自动改成 0、删除或用另一位评分替换。"
        "因此 direct 的平均不必要提问数 0.075 是原始评审计数结果，不能解释为 Direct Response 实际进行了提问。"
        "这项记录可在统计完成后由协调人核实；任何更正应另存修订版，并保留本次分歧处理前结果。", "",
        "2. 两份回传均记录了 AI 辅助和真人确认。评审员 1 的元数据记录了 AI 建议、批量接受的修订，"
        "并注明独立无辅助人评及实际盲评未获认证；评审员 2 的 100 条评语均标注 AI 二次审查建议及真人确认。"
        "评审声明同时记录了独立完成和盲评确认。应如实披露这些记录及限制，不能用本统计证明实际独立性或盲评。"
        "这与 proposal 的“不使用 LLM judge”原计划存在方法差异。计算仍按 proposal 规定进行。", "",
        "3. 原始记录、重复输出及两个随机顺序全部保留。统计限于预选的 20 个案例；"
        "200 次评价不是 200 个独立案例。没有添加显著性检验、额外置信区间、综合分数，"
        "没有调分或解决分歧，也没有新增模型调用。", "",
        "## 可用于英文报告的统计描述", "",
        "The preselected human-assessment subset comprised 20 test cases, each with the four main systems and the importance-one diagnostic, giving 100 outputs and 200 completed assessments by two reviewers. "
        "Returned records were matched by case and variant rather than randomized row order. "
        "Without resolving disagreements during this analysis, linearly weighted Cohen’s kappa on the fixed five-point scale was "
        + ", ".join(f"{agreement_rows[i]['linearly_weighted_kappa']:.4f} for {name}" for i, name in enumerate(["usefulness", "coherence", "audience fit", "feasibility"]))
        + ". Exact agreement was 84%, 96%, 75%, and 80%, respectively. For unsupported-assumption counts, exact agreement was 90% and mean absolute difference was 0.150; for unnecessary-question counts, these were 99% and 0.030. "
        "Each system summary averages the two ratings per output and then the 20 outputs, with all four rating dimensions reported separately.", "",
        "These are AI-assisted assessments confirmed by human reviewers, a departure from the proposal’s no-LLM-judge plan. Reviewer declarations and AI-assistance metadata do not independently establish blinding or unaided judgment. "
        "One returned unnecessary-question count (reviewer 2, R2-002, direct) is 3 despite an empty clarification trace; it was flagged and retained in all pre-adjudication summaries and agreement statistics. "
        "The findings apply to this 20-case subset; repeated contents and the diagnostic do not add independent cases. "
        "The supplied reviewer-1 version includes previously accepted AI-assisted amendments; their history is retained rather than described as an unaided first-pass judgment.", "",
        "## 交付文件", "",
        "- system_summary.csv：五个系统的六项均值。",
        "- reviewer_system_summary.csv：两位评审员分别按系统汇总，便于核对评分差异。",
        "- agreement.csv：四项线性加权 κ、完全一致率及两项计数 MAD。",
        "- paired_ratings.csv：100 对原始数值，保留各自的评审编号。",
        "- confusion_matrices.csv：四项评分的 5×5 配对频数矩阵，包含零频数单元。",
        "- statistics.json、validation_receipt.json：完整精度结果、口径、声明和核对记录。",
        "- inputs/：原样复制的两份回传、两份原始评分包、协调人映射及兼容性记录。",
        "- source_manifest.json：全部输入的 SHA-256 及原始来源。",
        "- reproduce_statistics.py：无需第三方库的复算程序；运行后重建统计文件。", "",
        "档案包含评审身份与协调人映射，供项目组统计及复核使用。",
    ]
    (ROOT / "human_review_statistics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete_original_ratings_before_adjudication",
                      "validation": validation, "agreement": agreement_rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
