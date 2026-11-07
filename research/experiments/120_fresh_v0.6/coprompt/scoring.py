"""Deterministic CoPrompt v0.1 scoring; never constructs model prompts.

Call ``score_output`` after the runner has exhausted the permitted format repair.
The annotation is private evaluation data and must not be sent to a model.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import re
import unicodedata
from typing import Any


DOMAINS = {"constrained_writing", "study_planning"}
WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
CHECKS_BY_DOMAIN = {
    "constrained_writing": {"word_count", "contains_all"},
    "study_planning": {
        "date_window", "daily_minutes_cap", "topic_coverage", "topic_minutes_min"
    },
}


def normalize_text(value: str) -> str:
    """NFKC, case folding and whitespace folding, as fixed in the protocol."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def count_words(value: str) -> int:
    return len(WORD_PATTERN.findall(unicodedata.normalize("NFKC", value)))


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _integer(value: Any, minimum: int) -> bool:
    # bool is an int subclass in Python, but not an accepted duration/threshold.
    return type(value) is int and value >= minimum


def _parse_date(value: Any) -> date:
    if not isinstance(value, str) or DATE_PATTERN.fullmatch(value) is None:
        raise ValueError("expected YYYY-MM-DD")
    return date.fromisoformat(value)


def _object_keys(obj: dict, required: set[str], path: str) -> list[str]:
    errors = []
    for key in sorted(required - obj.keys()):
        errors.append(f"{path}.{key}: missing required property")
    for key in sorted(obj.keys() - required, key=str):
        errors.append(f"{path}.{key}: additional property is not allowed")
    return errors


def validate_output(domain: str, obj: Any) -> list[str]:
    """Validate a decoded JSON output against the two strict output formats.

    Returns an empty list for valid output. JSON decoding belongs to the runner;
    raw strings, Markdown fences, and null are invalid objects here.
    """
    if domain not in DOMAINS:
        return [f"Unsupported domain: {domain!r}"]
    if not isinstance(obj, dict):
        return ["$: expected an object"]
    if domain == "constrained_writing":
        errors = _object_keys(obj, {"text"}, "$")
        if "text" in obj and not _nonblank(obj["text"]):
            errors.append("$.text: expected a nonblank string")
        return errors

    errors = _object_keys(obj, {"schedule", "summary"}, "$")
    if "summary" in obj and not _nonblank(obj["summary"]):
        errors.append("$.summary: expected a nonblank string")
    if "schedule" not in obj:
        return errors
    schedule = obj["schedule"]
    if not isinstance(schedule, list) or not schedule:
        errors.append("$.schedule: expected a nonempty array")
        return errors
    for index, item in enumerate(schedule):
        path = f"$.schedule[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: expected an object")
            continue
        errors.extend(_object_keys(item, {"date", "topic", "minutes"}, path))
        if "date" in item:
            try:
                _parse_date(item["date"])
            except (TypeError, ValueError):
                errors.append(f"{path}.date: expected a real date in YYYY-MM-DD format")
        if "topic" in item and not _nonblank(item["topic"]):
            errors.append(f"{path}.topic: expected a nonblank string")
        if "minutes" in item and not _integer(item["minutes"], 1):
            errors.append(f"{path}.minutes: expected a positive integer (not boolean)")
    return errors


def _require_parameters(params: Any, required: set[str], optional: set[str] | None = None) -> None:
    if not isinstance(params, dict):
        raise ValueError("constraint parameters must be an object")
    optional = optional or set()
    if required - params.keys() or params.keys() - required - optional:
        raise ValueError("constraint has missing or unsupported parameters")


def _require_integer(value: Any, minimum: int, name: str) -> int:
    if not _integer(value, minimum):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _require_texts(values: Any, name: str) -> list[str]:
    if not isinstance(values, list) or not values or not all(_nonblank(v) for v in values):
        raise ValueError(f"{name} must be a nonempty list of nonblank strings")
    return values


def _check(output: dict, kind: str, params: Any) -> tuple[bool, dict]:
    if kind == "word_count":
        _require_parameters(params, {"min_words", "max_words"})
        low = _require_integer(params["min_words"], 0, "min_words")
        high = _require_integer(params["max_words"], 0, "max_words")
        if low > high:
            raise ValueError("min_words exceeds max_words")
        observed = count_words(output["text"])
        return low <= observed <= high, {"word_count": observed, "min_words": low, "max_words": high}

    if kind == "contains_all":
        _require_parameters(params, {"literals"})
        literals = _require_texts(params["literals"], "literals")
        text = normalize_text(output["text"])
        missing = [literal for literal in literals if normalize_text(literal) not in text]
        return not missing, {"missing_literals": missing}

    if kind == "date_window":
        _require_parameters(params, {"start_date", "end_date"})
        start = _parse_date(params["start_date"])
        end = _parse_date(params["end_date"])
        if start > end:
            raise ValueError("start_date exceeds end_date")
        outside = sorted({item["date"] for item in output["schedule"]
                          if not start <= _parse_date(item["date"]) <= end})
        return not outside, {"outside_dates": outside, "start_date": start.isoformat(), "end_date": end.isoformat()}

    if kind == "daily_minutes_cap":
        _require_parameters(params, {"max_minutes"})
        cap = _require_integer(params["max_minutes"], 1, "max_minutes")
        totals: dict[str, int] = defaultdict(int)
        for item in output["schedule"]:
            totals[item["date"]] += item["minutes"]
        over = {day: minutes for day, minutes in sorted(totals.items()) if minutes > cap}
        return not over, {"daily_totals": dict(sorted(totals.items())), "max_minutes": cap, "over_cap": over}

    totals = defaultdict(int)
    for item in output["schedule"]:
        totals[normalize_text(item["topic"])] += item["minutes"]

    if kind == "topic_coverage":
        _require_parameters(params, {"topics"}, {"min_minutes_each"})
        topics = _require_texts(params["topics"], "topics")
        names = [normalize_text(topic) for topic in topics]
        if len(set(names)) != len(names):
            raise ValueError("topics contain duplicate normalized names")
        minimum = _require_integer(params.get("min_minutes_each", 1), 1, "min_minutes_each")
        minutes = {topic: totals[normalize_text(topic)] for topic in topics}
        missing = [topic for topic, value in minutes.items() if value < minimum]
        return not missing, {"topic_minutes": minutes, "min_minutes_each": minimum, "below_minimum": missing}

    if kind == "topic_minutes_min":
        _require_parameters(params, {"topic", "min_minutes"})
        if not _nonblank(params["topic"]):
            raise ValueError("topic must be a nonblank string")
        minimum = _require_integer(params["min_minutes"], 1, "min_minutes")
        observed = totals[normalize_text(params["topic"])]
        return observed >= minimum, {"topic": params["topic"], "minutes": observed, "min_minutes": minimum}
    raise ValueError(f"unsupported check_type: {kind!r}")


def score_output(domain: str, output: Any, annotation: dict) -> dict:
    """Return equal-weight constraint quality with explicit failure categories.

    Invalid model output earns 0 only after the caller's repair policy. Invalid
    annotation or scorer faults return quality=None and unscored_pending_fix;
    callers must never average those cases as zero.
    """
    try:
        if domain not in DOMAINS:
            raise ValueError(f"unsupported scoring domain: {domain!r}")
        errors = validate_output(domain, output)
        if errors:
            return {"status": "format_failure", "quality": 0.0, "format_failure": True,
                    "constraint_results": [], "errors": errors}
        if not isinstance(annotation, dict) or annotation.get("domain", domain) != domain:
            raise ValueError("annotation is invalid or belongs to another domain")
        constraints = annotation.get("constraints")
        if not isinstance(constraints, list) or not constraints:
            raise ValueError("annotation must contain a nonempty constraints array")
        results = []
        seen = set()
        for constraint in constraints:
            if not isinstance(constraint, dict):
                raise ValueError("constraint must be an object")
            constraint_id = constraint.get("constraint_id")
            if not _nonblank(constraint_id) or constraint_id in seen:
                raise ValueError("constraint IDs must be nonblank and unique")
            seen.add(constraint_id)
            kind = constraint.get("check_type")
            if kind not in CHECKS_BY_DOMAIN[domain]:
                raise ValueError(f"unsupported {domain} check_type: {kind!r}")
            passed, details = _check(output, kind, constraint.get("parameters"))
            results.append({"constraint_id": constraint_id, "check_type": kind,
                            "passed": passed, "score": int(passed), "details": details})
        return {"status": "scored", "quality": sum(r["score"] for r in results) / len(results),
                "format_failure": False, "constraint_results": results, "errors": []}
    except Exception as exc:
        return {"status": "unscored_pending_fix", "quality": None, "format_failure": False,
                "constraint_results": [], "errors": [f"{type(exc).__name__}: {exc}"]}
