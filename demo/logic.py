"""Pure, testable helpers for the offline CoPrompt demo."""
from __future__ import annotations
from typing import Any, Iterable

POLICY_LABELS = {
    "direct": "Direct response",
    "exhaustive": "Exhaustive clarification",
    "prompt_only": "Prompt-only adaptive",
    "value_based": "Value-based adaptive",
    "importance_one": "Importance=1 diagnostic",
}
FIELD_LABELS = {
    "audience": "Audience", "tone": "Tone", "length": "Length",
    "required_content": "Required content", "deadline": "Deadline",
    "available_time": "Available time", "topics": "Study topics",
    "priorities": "Priorities",
}
DOMAIN_LABELS = {"constrained_writing": "Constrained writing", "study_planning": "Study planning"}
OMISSION_LABELS = {
    "complete": "Complete request", "critical_omission": "Critical field missing",
    "critical_and_optional": "Critical and optional fields missing", "optional_only": "Optional field only",
    "unavailable_answer": "Answer unavailable", "execute_now": "Immediate execution requested",
}

def value_score(importance: float, uncertainty: float, lambda_value: float) -> float:
    """Return the controller's net value I * U - lambda."""
    return round(float(importance) * float(uncertainty) - float(lambda_value), 10)

def sandbox_comparison(fields: Iterable[dict[str, Any]], lambda_value: float, budget: int) -> list[dict[str, Any]]:
    """Explain four policies with a fixed-state, no-LLM sandbox."""
    rows = list(fields)
    eligible = [row for row in rows if row.get("status") == "missing"]
    limit = min(3, max(0, int(budget)))
    exhaustive_fields = [row["field_id"] for row in eligible[:limit]]
    prompt_fields = [row["field_id"] for row in eligible if bool(row.get("prompt_only_ask"))][:limit]
    scored = []
    for order, row in enumerate(eligible):
        net = value_score(row["importance"], row["uncertainty"], lambda_value)
        scored.append((net, -order, row["field_id"]))
    scored.sort(reverse=True)
    value_fields = [field_id for net, _, field_id in scored if net > 0][:limit]
    return [
        {"policy": "direct", "action": "ACT", "questions": 0, "fields": [], "reason": "Generate immediately without asking a question."},
        {"policy": "exhaustive", "action": "ASK" if exhaustive_fields else "ACT", "questions": len(exhaustive_fields), "fields": exhaustive_fields, "reason": "Ask every unresolved field in catalog order until the question budget is exhausted."},
        {"policy": "prompt_only", "action": "ASK" if prompt_fields else "ACT", "questions": len(prompt_fields), "fields": prompt_fields, "reason": "The offline sandbox uses your selections to simulate the model's ASK/ACT choices."},
        {"policy": "value_based", "action": "ASK" if value_fields else "ACT", "questions": len(value_fields), "fields": value_fields, "reason": "Ask only fields with I×U−λ>0, ordered by net value."},
    ]

def output_text(output: Any) -> str:
    if isinstance(output, str): return output
    if not isinstance(output, dict): return str(output)
    if isinstance(output.get("text"), str): return output["text"]
    return ""

def field_label(field_id: str) -> str:
    return FIELD_LABELS.get(field_id, field_id)
