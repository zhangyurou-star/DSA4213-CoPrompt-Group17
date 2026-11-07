"""Conservative public-text evidence checks; never consult private annotations.

This checks quotation provenance and narrow English field contracts, not full
semantic correctness. Unsupported fields become unresolved without another call.
"""

import re

GROUNDING_VERSION = "source-unit-evidence-0.3.0"
ENDPOINT = re.compile(
    r"\b(?:finish(?:ed|ing)?|end(?:s|ing)?|complete(?:d)?|until|through|deadline|due)\b"
    r"|\b(?:last|final)\b[^.!?\n]{0,35}\b(?:date|day)\b|\bno later than\b"
    # A coordinated endpoint may omit the repeated noun: "first study day ...
    # and the last is ...". Require the earlier day/date in the same sentence.
    r"|\bfirst(?:\s+[A-Za-z]+){0,3}\s+(?:day|date)\b[^.!?\n]{0,100}"
    r"\band\s+(?:the\s+)?(?:last|final)(?:\s+one)?\s+is\b", re.I)
DAILY = re.compile(
    r"\b(?:daily|per day|each day|a day|every day|on any(?: one)? day)\b", re.I)
DURATION = re.compile(r"\b(?:minutes?|hours?)\b", re.I)
UNLIMITED = re.compile(r"\b(?:unlimited|no (?:daily )?(?:limit|restriction)|any amount)\b", re.I)
AUDIENCE_CUE = re.compile(
    r"\b(?:for|to|audience|readers?|recipients?|dear|thank(?:ing)?|address(?:ed|ing)?)\b"
    r"|^(?:please\s+)?(?:email|notify|inform|invite)\s+"
    # Reader groups can be the subject rather than the object of "for/to".
    r"|\b(?:will|shall)\s+read\s+(?:this|the|my|our)\s+"
    r"(?:notice|message|letter|announcement|invitation|caption|blurb|reminder|text|document)\b", re.I)
UNSPECIFIED_TOPICS = re.compile(
    r"\b(?:topics?|subjects?)\s+(?:(?:that|which)\s+)?I\s+(?:will\s+)?(?:specify|provide|choose|select|list|name)\b"
    r"|\b(?:topics?|subjects?)\s+(?:to be|will be)\s+(?:specified|provided|chosen|selected|listed|named)\b"
    r"|\bI\s+will\s+(?:specify|provide|choose|select|list|name)\s+"
    r"(?:(?:the|my|exact|specific|study|revision)\s+)*(?:topics?|subjects?)\b"
    r"|\bI\s+have\s+not\s+(?:yet\s+)?(?:specified|provided|chosen|selected|listed|named)\s+"
    r"(?:(?:the|my|exact|specific|study|revision)\s+)*(?:topics?|subjects?)\b", re.I)


def source_units(request):
    """Return deterministic, lossless references into the public request.

    Units end after sentence punctuation (including closing quotes), or at a
    newline. This is a reference scheme, not a linguistic sentence parser.
    Whitespace between units is omitted; every non-whitespace character belongs
    to exactly one unit and all text is recoverable from its original offsets.
    """
    source = request["initial_request"]
    boundaries = [match.end() for match in re.finditer(r'''[.!?]["”’')\]]*(?=\s)|\n+''', source)]
    boundaries.append(len(source))
    units, start = [], 0
    for boundary in boundaries:
        raw = source[start:boundary]
        left = start + len(raw) - len(raw.lstrip())
        right = boundary - (len(raw) - len(raw.rstrip()))
        if left < right:
            units.append({"id": f"S{len(units) + 1}", "start": left,
                          "end": right, "text": source[left:right]})
        start = boundary
    return units


def _selection_error(selection, unit_order):
    if not isinstance(selection, list):
        return "evidence_must_be_a_list"
    if any(not isinstance(unit_id, str) or unit_id not in unit_order for unit_id in selection):
        return "unknown_source_unit_id"
    if len(selection) != len(set(selection)):
        return "duplicate_source_unit_id"
    if selection != sorted(selection, key=unit_order.__getitem__):
        return "source_unit_ids_not_in_source_order"
    return None


def evidence_errors(obj, fields, units):
    """Validate only the output contract; semantic checks happen on resolution."""
    if not isinstance(obj, dict) or set(obj) != {"field_evidence"}:
        return ["Object must contain only field_evidence"]
    evidence = obj["field_evidence"]
    if not isinstance(evidence, dict) or set(evidence) != set(fields):
        return ["field_evidence must contain exactly all four listed fields"]
    unit_order = {unit["id"]: index for index, unit in enumerate(units)}
    errors = []
    for field, selection in evidence.items():
        reason = _selection_error(selection, unit_order)
        if reason:
            errors.append(f"{field}: {reason}; use [] or valid, unique source unit IDs in source order")
    return errors


def _semantic_rejection(request, field, value):
    if request["domain"] == "constrained_writing" and field == "audience" and not AUDIENCE_CUE.search(value):
        return "quote_has_no_explicit_reader_relation_cue"
    if request["domain"] == "study_planning":
        if field == "deadline" and not ENDPOINT.search(value):
            return "quote_has_no_explicit_endpoint_cue"
        if field == "available_time" and not (
                DAILY.search(value) and (DURATION.search(value) or UNLIMITED.search(value))):
            return "quote_has_no_daily_time_allowance_cue"
        if (field == "topics" and all(UNSPECIFIED_TOPICS.search(line) for line in value.splitlines())
                and not re.search(r"[:：]|\b(?:namely|such as|including)\b", value, re.I)):
            return "quote_only_refers_to_unspecified_topics"
    return None


def resolve_evidence(request, field_evidence):
    """Resolve IDs to original text; invalid fields stay unresolved and logged."""
    units = source_units(request)
    unit_map = {unit["id"]: unit for unit in units}
    unit_order = {unit["id"]: index for index, unit in enumerate(units)}
    values, evidence, rejections = {}, {}, []
    for field, selection in field_evidence.items():
        reason = _selection_error(selection, unit_order)
        proposed = None
        if not reason and selection:
            proposed = "\n".join(unit_map[unit_id]["text"] for unit_id in selection)
            reason = _semantic_rejection(request, field, proposed)
        if reason:
            rejections.append({"field_id": field, "proposed_evidence": selection,
                               "proposed_value": proposed, "reason": reason})
            values[field] = None
        else:
            values[field] = proposed
            if selection:
                evidence[field] = [{"source": "initial_request", "unit_id": unit_id,
                                    "start": unit_map[unit_id]["start"],
                                    "end": unit_map[unit_id]["end"],
                                    "quote": unit_map[unit_id]["text"]} for unit_id in selection]
    return values, evidence, rejections


def ground_fields(request, field_values):
    source = request["initial_request"]
    grounded, evidence, rejections = {}, {}, []
    for field, value in field_values.items():
        reason = None
        if value is not None:
            if value not in source:
                reason = "not_an_exact_initial_request_quote"
            else:
                reason = _semantic_rejection(request, field, value)
        if reason:
            rejections.append({"field_id": field, "proposed_value": value, "reason": reason})
            grounded[field] = None
        else:
            grounded[field] = value
            if value is not None:
                start = source.index(value)
                evidence[field] = {"source": "initial_request", "start": start,
                                   "end": start + len(value), "quote": value}
    return grounded, evidence, rejections
