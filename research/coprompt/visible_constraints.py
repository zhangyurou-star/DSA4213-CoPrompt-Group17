"""Conservative, deterministic checks of constraints actually visible to a model.

This module does not load files, case IDs, annotations, or simulated answers.
It recognizes a deliberately limited English grammar and preserves its evidence.
Unsupported or ambiguous requirements remain in the original user text; warnings
explain the limits of the mechanical contract rather than inventing hard values.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date
import json
import re

from .scoring import count_words, normalize_text, validate_output

CONSTRAINT_VERSION = "visible-constraints-0.4.0"
SUMMARY_VERSION = "schedule-summary-0.4.0"
_ISO = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
_FLAGS = re.I


def _sentences(text):
    """Keep quoted literal punctuation inside its source sentence."""
    start, quote = 0, False
    for index, char in enumerate(text):
        if char in '"“”':
            quote = not quote
        if (not quote and char in ".!?" and
                (index + 1 == len(text) or text[index + 1].isspace())):
            sentence = text[start:index + 1].strip()
            if sentence:
                yield sentence
            start = index + 1
    tail = text[start:].strip()
    if tail:
        yield tail


def _sources(request, exchanges):
    text = request.get("initial_request", "")
    if isinstance(text, str) and text.strip():
        yield {"source": "initial_request", "field_id": None, "quote": text}
    for index, exchange in enumerate(exchanges):
        if not isinstance(exchange, dict) or exchange.get("status") != "available":
            continue
        text = exchange.get("answer_text")
        if isinstance(text, str) and text.strip():
            yield {"source": "visible_exchange", "exchange_index": index,
                   "field_id": exchange.get("field_id"), "quote": text}


def _evidence(source, sentence):
    return {**source, "quote": sentence}


def _add(contract, kind, parameters, source):
    """Merge identical checks while retaining every supporting source."""
    sources = source if isinstance(source, list) else [source]
    for item in contract["constraints"]:
        if item["kind"] == kind and item["parameters"] == parameters:
            for evidence in sources:
                if evidence not in item["source"]:
                    item["source"].append(evidence)
            return
    contract["constraints"].append({"kind": kind, "parameters": parameters, "source": sources})


def _warn(contract, reason, source):
    warning = {"reason": reason, "source": source}
    if warning not in contract["warnings"]:
        contract["warnings"].append(warning)


def _hypothetical(text):
    return bool(re.search(r"\b(?:for example|examples?|if convenient|if possible|optional|might|perhaps|"
                          r"used to|previously|yesterday|last year|not sure|"
                          r"I (?:do not|don't) know)\b", text, _FLAGS))


def _unquoted(text):
    # Quoted requirements may themselves contain 'exactly 12 words' or a date;
    # those tokens are content, never a second independent numeric requirement.
    return re.sub(r'["“][^"“”]*["”]', lambda match: " " * len(match[0]), text)


def _writing(contract, sources):
    for source in sources:
        for sentence in _sentences(source["quote"]):
            evidence = _evidence(source, sentence)
            prose = _unquoted(sentence)
            # Only full-output counts; a body/paragraph count is not a count of
            # all headings and signatures, so it cannot use this output checker.
            scope_ambiguous = bool(re.search(r"\b(?:body|paragraph|section|subject line only)\b",
                                            prose, _FLAGS))
            instruction = bool(re.search(r"\b(?:must|should|keep|write|use|contain|total|"
                                         r"limit|exactly|between)\b", prose, _FLAGS))
            eligible = (instruction or source.get("field_id") == "length")
            ranges = list(re.finditer(r"\b(?P<low>\d+)\s*(?:to|[-–—]|and)\s*"
                                      r"(?P<high>\d+)\s+words\b", prose, _FLAGS))
            exact = list(re.finditer(r"\bexactly\s+(?P<count>\d+)\s+words\b", prose, _FLAGS))
            negative_count = bool(re.search(r"\b(?:do not|don't|must not|never|need not|not required)\b", prose, _FLAGS))
            if ranges or exact:
                if not eligible or scope_ambiguous or _hypothetical(prose) or negative_count:
                    _warn(contract, "word_count_not_clearly_a_full_output_requirement", evidence)
                else:
                    for match in ranges:
                        low, high = int(match["low"]), int(match["high"])
                        if low <= high:
                            _add(contract, "word_count", {"min_words": low, "max_words": high}, evidence)
                        else:
                            _warn(contract, "reversed_word_count_range", evidence)
                    if not ranges:
                        for match in exact:
                            count = int(match["count"])
                            _add(contract, "word_count", {"min_words": count, "max_words": count}, evidence)
            elif re.search(r"\d+\s+words\b", prose, _FLAGS):
                _warn(contract, "unsupported_or_nonbinding_word_count_expression", evidence)

            quotes = re.findall(r'["“]([^"“”]+)["”]', sentence)
            first_quote = re.search(r'["“]', sentence)
            prefix = sentence[:first_quote.start()] if first_quote else sentence
            verb = re.search(r"\b(?:include|preserve|retain|keep)\b", prefix, _FLAGS)
            directive = bool(re.search(r"^\s*(?:please\s+)?(?:include|preserve|retain|keep)\b|"
                                      r"\b(?:must|should|need to|needs to)\s+(?:include|preserve|retain|keep)\b", prefix, _FLAGS))
            explicit = (verb and directive) or re.search(r"^\s*(?:please\s+)?(?:use|reproduce)\b.*\b(?:exact|exactly|verbatim)\b", prefix, _FLAGS)
            negative = re.search(r"\b(?:do not|don't|must not|never|need not|not required)\b", prefix, _FLAGS)
            if quotes and explicit and not negative and not _hypothetical(prefix):
                _add(contract, "contains_all", {"literals": quotes}, evidence)
            elif quotes and (explicit or re.search(r"\b(?:exact|verbatim)\b", prefix, _FLAGS)):
                _warn(contract, "quoted_text_not_clearly_a_positive_literal_requirement", evidence)


def _real_date(value):
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _parse_dates(contract, rows):
    starts, ends = [], []
    for sentence, evidence in rows:
        sentence = _unquoted(sentence)
        if _hypothetical(sentence):
            if re.search(_ISO, sentence):
                _warn(contract, "nonbinding_date_expression", evidence)
            continue
        start_patterns = [
            rf"\b(?:start(?:ing)?|begin(?:ning)?)\s+(?:on\s+)?({_ISO})",
            rf"\bfirst\s+study\s+(?:day|date)\s+is\s+({_ISO})",
            rf"\b(?:plan|schedule|timetable)\s+from\s+({_ISO})",
        ]
        end_patterns = [
            rf"\b(?:finish(?:ed)?|end(?:ing)?)\s+(?:all\s+study\s+sessions\s+)?(?:by|on)\s+({_ISO})",
            rf"\b(?:last|final)\s+(?:available\s+)?(?:study\s+)?(?:day|date)\s+is\s+({_ISO})",
            rf"\bstudy\s+sessions\s+completed\s+by\s+({_ISO})",
        ]
        start_matches = [m for pattern in start_patterns for m in re.finditer(pattern, sentence, _FLAGS)]
        end_matches = [m for pattern in end_patterns for m in re.finditer(pattern, sentence, _FLAGS)]
        if start_matches:
            end_matches += list(re.finditer(rf"\band\s+the\s+last\s+is\s+({_ISO})", sentence, _FLAGS))
            for start_match in start_matches:
                adjacent_end = re.match(rf"\s+(?:through|to)\s+({_ISO})", sentence[start_match.end():], _FLAGS)
                if adjacent_end:
                    end_matches.append(adjacent_end)
        if evidence.get("field_id") == "deadline":
            match = re.fullmatch(rf"\s*({_ISO})(?:,?\s+inclusive)?[.!]?\s*", sentence, _FLAGS)
            if match:
                end_matches.append(match)
        for matches, target in ((start_matches, starts), (end_matches, ends)):
            for match in matches:
                value = _real_date(match[1])
                if value:
                    target.append((value, evidence))
                else:
                    _warn(contract, "invalid_calendar_date", evidence)
        if re.search(_ISO, sentence) and not start_matches and not end_matches:
            _warn(contract, "date_without_unambiguous_study_window_role", evidence)
    bounds, evidence = {}, []
    for key, values in (("start_date", starts), ("end_date", ends)):
        unique = {value for value, _ in values}
        if len(unique) == 1:
            bounds[key] = next(iter(unique))
            evidence.extend(item for _, item in values if item not in evidence)
        elif len(unique) > 1:
            _warn(contract, f"conflicting_{key}_values_not_resolved", [item for _, item in values])
    if ("start_date" in bounds and "end_date" in bounds and
            bounds["start_date"] > bounds["end_date"]):
        _warn(contract, "inverted_study_window_not_enforced", evidence)
    elif bounds:
        _add(contract, "date_window", bounds, evidence)


def _parse_daily_caps(contract, rows):
    frequency = r"\b(?:daily|per\s+day|each\s+day|every\s+day|on\s+any(?:\s+(?:one|single))?\s+day)\b"
    for sentence, evidence in rows:
        sentence = _unquoted(sentence)
        if not re.search(frequency, sentence, _FLAGS):
            continue
        if _hypothetical(sentence):
            if re.search(r"\d+\s+minutes", sentence, _FLAGS):
                _warn(contract, "nonbinding_daily_minutes_expression", evidence)
            continue
        patterns = [
            r"\b(?:at most|no more than|not schedule more than|a maximum of|maximum of)\s+(\d+)\s+minutes\b",
            r"\bdaily\s+study\s+allowance\s+of\s+(\d+)\s+minutes\b",
            r"\b(?:to|of)\s+(\d+)\s+minutes\s+or\s+less\b",
            r"\bI can study (?:for\s+)?(\d+)\s+minutes\s+(?:per|each|every)\s+day\b",
        ]
        matches = [m for pattern in patterns for m in re.finditer(pattern, sentence, _FLAGS)]
        for match in matches:
            if re.match(r"\s+(?:per|each)\s+(?:session|topic|week|month)\b", sentence[match.end():], _FLAGS):
                _warn(contract, "minutes_bound_has_nondaily_scope", evidence)
            else:
                _add(contract, "daily_minutes_cap", {"max_minutes": int(match[1])}, evidence)
        if not matches and re.search(r"\d+\s+(?:minutes|hours)\b", sentence, _FLAGS):
            _warn(contract, "unsupported_daily_time_expression", evidence)


def _topic_names(text):
    text = text.strip().rstrip(".!?")
    quoted = re.findall(r'["“]([^"“”]+)["”]', text)
    if quoted:
        residual = re.sub(r'["“][^"“”]+["”]', "", text)
        if re.sub(r"\b(?:and|or)\b|[,;\s]", "", residual, flags=_FLAGS):
            return []
        return quoted
    names = [part.strip() for part in re.split(r",\s*(?:and\s+)?|\s+and\s+", text) if part.strip()]
    # Reject unsupported clauses instead of creating a 'topic' from prose.
    if not names or any(len(name) > 100 or re.search(r"\b(?:will|later|separately|specify|"
                                                     r"needs|minutes|must|each|not|unknown|"
                                                     r"unspecified|undecided)\b", name, _FLAGS)
                        for name in names):
        return []
    return names


def _parse_topics(contract, sources):
    all_topics = []
    for source in sources:
        previous_topics = []
        for sentence in _sentences(source["quote"]):
            evidence = _evidence(source, sentence)
            if _hypothetical(sentence):
                continue
            names_text, minimum = None, 1
            if ":" in sentence:
                prefix, suffix = sentence.split(":", 1)
                if re.search(r"\b(?:cover|include|spend|give)\b", prefix, _FLAGS) and re.search(
                        r"\b(?:these\s+exact\s+topics|each\s+exact\s+topic)\b", prefix, _FLAGS):
                    names_text = suffix
                    minutes = re.search(r"\bat least\s+(\d+)\s+minutes\b", prefix, _FLAGS)
                    if minutes:
                        minimum = int(minutes[1])
            else:
                match = re.search(r"\b(?:the exact topics are|use the exact topic labels)\s+(.+)",
                                  sentence, _FLAGS)
                if match:
                    rest = match[1]
                    parts = re.split(r",\s*(?:and\s+each|with\s+at\s+least)\b", rest, maxsplit=1, flags=_FLAGS)
                    names_text = parts[0]
                    if len(parts) == 2:
                        minutes = re.search(r"(?:at least\s+)?(\d+)\s+minutes\b", parts[1], _FLAGS)
                        if minutes:
                            minimum = int(minutes[1])
            if names_text is not None:
                topics = _topic_names(names_text)
                if topics and minimum >= 1:
                    previous_topics = topics
                    for topic in topics:
                        if topic not in all_topics:
                            all_topics.append(topic)
                    _add(contract, "topic_coverage", {"topics": topics, "min_minutes_each": minimum}, evidence)
                else:
                    previous_topics = []
                    _warn(contract, "ambiguous_topic_list_or_minimum", evidence)
            else:
                followup = re.match(r"\s*(?:Give|Allow|Allocate)\s+each\s+at least\s+(\d+)\s+minutes\b",
                                    sentence, _FLAGS)
                if followup:
                    if previous_topics and int(followup[1]) >= 1:
                        _add(contract, "topic_coverage", {"topics": previous_topics,
                             "min_minutes_each": int(followup[1])}, evidence)
                    else:
                        _warn(contract, "each_topic_minimum_without_visible_topic_list", evidence)
    return all_topics


def _parse_priorities(contract, rows, topics):
    for sentence, evidence in rows:
        if _hypothetical(sentence):
            continue
        matches = [
            re.match(r"\s*(.+?)\s+is\s+(?:my|the)\s+priority\b.*?\bat least\s+(\d+)\s+minutes\b", sentence, _FLAGS),
            re.match(r"\s*Give\s+priority\s+to\s+(.+?)\s+with\s+at least\s+(\d+)\s+minutes\b", sentence, _FLAGS),
            re.match(r"\s*(.+?)\s+needs\s+extra\s+attention:\s*allocate\s+at least\s+(\d+)\s+minutes\b", sentence, _FLAGS),
        ]
        for match in matches:
            if match:
                topic, minutes = match[1].strip(), int(match[2])
                known = next((name for name in topics if normalize_text(name) == normalize_text(topic)), None)
                if known and minutes >= 1:
                    _add(contract, "topic_minutes_min", {"topic": known, "min_minutes": minutes}, evidence)
                else:
                    _warn(contract, "priority_minimum_without_unambiguous_visible_topic_label", evidence)


def build_constraints(request, exchanges):
    """Build an auditable JSON contract using only allowed visible text.

    A date window can have only one known bound. Word counts include all text;
    literal and topic matching use the protocol's NFKC/case/whitespace folding.
    Constraints do not specify what to do when essential information is absent.
    """
    contract = {"version": CONSTRAINT_VERSION, "domain": request.get("domain"),
                "constraints": [], "warnings": []}
    sources = list(_sources(request, exchanges))
    if request.get("domain") == "constrained_writing":
        _writing(contract, sources)
    elif request.get("domain") == "study_planning":
        rows = [(sentence, _evidence(source, sentence)) for source in sources
                for sentence in _sentences(source["quote"])]
        _parse_dates(contract, rows)
        _parse_daily_caps(contract, rows)
        topics = _parse_topics(contract, sources)
        _parse_priorities(contract, rows, topics)
    return contract


def check_constraints(domain, output, contract):
    """Return deterministic violations; malformed outputs belong to format repair."""
    if validate_output(domain, output):
        return []
    errors = []
    for constraint in contract.get("constraints", []):
        kind, params = constraint["kind"], constraint["parameters"]
        details = None
        if domain == "constrained_writing" and kind == "word_count":
            actual = count_words(output["text"])
            if not params["min_words"] <= actual <= params["max_words"]:
                details = {"observed_words": actual, **params}
        elif domain == "constrained_writing" and kind == "contains_all":
            normalized = normalize_text(output["text"])
            missing = [literal for literal in params["literals"] if normalize_text(literal) not in normalized]
            if missing:
                details = {"missing_literals": missing}
        elif domain == "study_planning" and kind == "date_window":
            outside = sorted({item["date"] for item in output["schedule"] if
                (params.get("start_date") and item["date"] < params["start_date"]) or
                (params.get("end_date") and item["date"] > params["end_date"])})
            if outside:
                details = {"outside_dates": outside, **params}
        elif domain == "study_planning" and kind == "daily_minutes_cap":
            totals = defaultdict(int)
            for item in output["schedule"]:
                totals[item["date"]] += item["minutes"]
            exceeded = {day: total for day, total in sorted(totals.items()) if total > params["max_minutes"]}
            if exceeded:
                details = {"daily_totals_over_cap": exceeded, **params}
        elif domain == "study_planning" and kind in {"topic_coverage", "topic_minutes_min"}:
            totals = defaultdict(int)
            for item in output["schedule"]:
                totals[normalize_text(item["topic"])] += item["minutes"]
            topics = params["topics"] if kind == "topic_coverage" else [params["topic"]]
            minimum = params["min_minutes_each"] if kind == "topic_coverage" else params["min_minutes"]
            under = {topic: totals[normalize_text(topic)] for topic in topics
                     if totals[normalize_text(topic)] < minimum}
            if under:
                details = {"topic_minutes_below_minimum": under, "required_minutes": minimum}
        if details is not None:
            errors.append(kind + ": " + json.dumps(details, ensure_ascii=False, sort_keys=True))
    return errors


def visible_measurements(domain, output, contract):
    """Measure a valid draft against the complete, already-visible contract.

    A repair sees passing requirements as well as failures, so fixing one bound
    cannot silently remove the other bounds from its context. This is reporting,
    not a scheduler, a factuality detector, or a private-score lookup.
    """
    if validate_output(domain, output):
        return None
    if domain == "constrained_writing":
        observed = {"full_text_words": count_words(output["text"])}
    else:
        daily, topics, labels = defaultdict(int), defaultdict(int), {}
        for item in output["schedule"]:
            daily[item["date"]] += item["minutes"]
            normalized = normalize_text(item["topic"])
            topics[normalized] += item["minutes"]
            labels.setdefault(normalized, item["topic"])
        observed = {
            "total_minutes": sum(daily.values()),
            "daily_minutes": dict(sorted(daily.items())),
            "topic_minutes": [{"topic": labels[name], "normalized_topic": name,
                               "minutes": topics[name]} for name in sorted(topics)],
        }
    return {"domain": domain, "observed": observed,
            "requirements": [{"kind": item["kind"], "parameters": deepcopy(item["parameters"])}
                             for item in contract.get("constraints", [])],
            "violations": check_constraints(domain, output, contract),
            "interpretation_warnings": deepcopy(contract.get("warnings", []))}


def derive_schedule_summary(domain, output, contract):
    """Replace only a valid plan's summary with calculations from its schedule.

    Raw model summaries remain in the returned provenance and in model attempts.
    Failed constraints are disclosed, never repaired or masked by this function.
    """
    final = deepcopy(output)
    if domain != "study_planning" or validate_output(domain, output):
        return final, None
    measured = visible_measurements(domain, output, contract)
    observed = measured["observed"]
    daily = "; ".join(f"{day}: {minutes} minutes" for day, minutes in observed["daily_minutes"].items())
    topics = "; ".join(f"{item['topic']}: {item['minutes']} minutes" for item in observed["topic_minutes"])
    summary = (f"Calculated from the schedule: {observed['total_minutes']} minutes in total. "
               f"Daily totals: {daily}. Topic totals: {topics}. ")
    if measured["violations"]:
        summary += "Recognized visible requirements remain unmet: " + "; ".join(measured["violations"]) + "."
    elif measured["requirements"]:
        summary += "Recognized visible constraint checks passed; this does not verify every user requirement."
    else:
        summary += "No recognized visible constraints were available to check."
    if measured["interpretation_warnings"]:
        summary += " Some requirements could not be interpreted mechanically."
    final["summary"] = summary
    return final, {"version": SUMMARY_VERSION, "original_summary": output["summary"],
                   "derived_summary": summary}
