"""Versioned public-only prompts, shared by all experimental policies."""

import json

from .grounding import source_units
from .visible_constraints import build_constraints

PROMPT_VERSION = "pilot-0.2.3"
GENERATION_PROMPT_VERSION = "pilot-0.4.0"
EXTRACT = """Identify explicit evidence for the four listed fields using the numbered source_units.
Return exactly one JSON object: {"field_evidence": {<each field ID>: [<source unit IDs>]}}.
Include every listed field and no other keys. Each value must be [] or a list such as ["S2", "S4"].
Use only IDs from the supplied source_units, without duplicates, in source order. Do not copy or rewrite text.
Choose the units that explicitly supply that field; the same unit can support more than one field.
Choose all units needed to retain the stated requirement, including relevant coverage and minimum times.
Use [] when not stated. Reference_date is context, never a deadline. Missing information stays missing.
Do not infer a specific audience from a genre or infer a preference from silence.
An explicit statement of no preference/no requirement is resolved: select its source unit.
For audience, an explicitly named group being addressed or thanked is evidence of the intended reader.
An institution, location or industry modifying a document type is not an explicit reader group.
For example, "a company newsletter" does not specify employees, customers or investors as its audience.
For tone, explicit style adjectives describing the requested writing count even when the word 'tone' is absent.
Evaluate each field independently: one sentence can explicitly supply both audience and tone.
For length, select an explicit full-text word count/range or an explicit statement of no length requirement.
For required_content, a topic or genre alone is insufficient: specific required facts or literal phrases are needed.
An announcement about an event does not by itself supply concrete required facts about that event.
For deadline, select evidence of an explicit finish/end/last study date or deadline.
A start date is NOT a deadline. If only a starting date is given, deadline MUST be [].
For available_time, select evidence of a daily study allowance/limit including duration and daily frequency.
A topic's minimum total minutes and the output instruction to use integer minutes are NOT a daily allowance.
For topics, select actual specified topic names with their coverage/minimum-time requirements.
A course title or a promise to specify topics later does NOT supply the topics: use [].
For priorities, select explicit priority requirements or an explicit statement of no priority preference.
Never invent dates, daily time limits, topic lists or hidden answers. Choose [] rather than a plausible guess.

The following independent examples illustrate the rule. For the actual request, inspect only its own source_units:
Study example: S1="Plan revision for my geology course, beginning on 2033-02-05."
S2="I have no topic priority preference."
Output: {"field_evidence":{"deadline":[],"available_time":[],"topics":[],"priorities":["S2"]}}
Writing example: S1="Draft a notice to tenants about elevator repairs."
Output: {"field_evidence":{"audience":["S1"],"tone":[],"length":[],"required_content":[]}}
If that writing example adds S2='Include the exact phrases "Lift B" and "closed on 12 May".',
the output becomes {"field_evidence":{"audience":["S1"],"tone":[],"length":[],"required_content":["S2"]}}.
Another writing example: S1="Write a formal invitation for donors."
Output: {"field_evidence":{"audience":["S1"],"tone":["S1"],"length":[],"required_content":[]}}
Another writing example: S1="Draft a company newsletter about a forthcoming reorganization."
Output: {"field_evidence":{"audience":[],"tone":[],"length":[],"required_content":[]}}
No Markdown fences or commentary."""
GENERATE = """Complete the user's task using only the original request, public context and the visible clarification exchanges.
Do not ask more questions. Honor all available requirements, including exact phrases and the full-text word count.
visible_constraints is a deterministic, partial checklist derived only from that visible text, not new user requirements.
Always honor the original visible text as well; absence from the checklist does not remove a requirement.
Do not invent event details, promises, historical facts or beneficiary groups. Omit unavailable specifics or use clearly marked placeholders.
Treat concrete dates, clock times, addresses, names, contact details, links, services and free-access claims as facts requiring visible support.
Plausibility is not evidence. Do not add these details to make a notice sound complete or to reach its minimum word count.
Do not claim a link is provided when none is available. Use neutral connective wording without adding factual commitments.
Return exactly one JSON object matching the supplied output schema, without Markdown fences or surrounding commentary.
For writing, put ALL headings, greetings, body and signature inside text.
Copy required literal phrases unchanged. Draft near the middle of the full-text word range, then check the complete text length.
When revising a length failure, rewrite the whole text toward the range midpoint while retaining every required literal; do not merely append or trim a final sentence.
Word counting includes every heading and signature: letter/digit sequences, with internal apostrophes or hyphens, count as words.
For study plans, each schedule item has one complete topic name, a real ISO date and positive integer minutes;
first compute each topic's required total, then allocate those minutes across the permitted days without exceeding any day's combined limit.
A topic-specific minimum replaces a smaller general minimum for that topic; it is not an extra requirement to add twice.
Split a topic across days when needed. Use a compact schedule with only necessary sessions; do not repeat every topic on every day.
Check the sum of ALL sessions per date and the sum per exact topic label before returning. Keep summary short and consistent with schedule.
If a deadline or daily allowance is unknown, use a short conservative plan without claiming a guessed bound was supplied.
Never add an unsupported numeric constraint. If visible requirements conflict, explain the conflict in the output rather than claim compliance.
Write in English."""
PROMPT_ONLY = """Choose whether to clarify one unresolved field or act now to complete the user's task.
Ask only when its likely benefit to the result justifies another question. Optional preferences may have reasonable defaults.
Consider only the public request, visible exchanges, current field state, eligible fields and remaining question budget.
Return exactly {"action":"ASK","field_id":"one_field_id"} or {"action":"ACT"}.
No explanation, extra keys or Markdown. Do not predict unavailable hidden answers."""
VALUE_BASED = """Rate EVERY eligible unresolved field using the public request and visible interaction only.
Importance I: 0 = little effect; 0.5 = local preference; 1 = could change core content or feasibility.
Uncertainty U: 0.5 = a reasonable default exists; 1 = different possible answers may materially change the result.
These are heuristic levels, not calibrated probabilities. Never inspect or infer hidden answer availability or grading labels.
Return exactly {"ratings":[{"field_id":"...","importance":0.5,"uncertainty":1,"reason":"brief rationale"}, ...]}.
Cover each eligible field exactly once. Importance must be 0, 0.5 or 1. Uncertainty must be 0.5 or 1.
No action recommendation, extra keys or Markdown."""


def public_context(request):
    return {k: request[k] for k in ("domain", "initial_request", "reference_date", "user_control")}


def messages(system, content):
    return [{"role": "system", "content": system},
            {"role": "user", "content": json.dumps(content, ensure_ascii=False)}]


def extraction_messages(request, catalog):
    return messages(EXTRACT, {**public_context(request), "fields": catalog["fields"],
                              "source_units": source_units(request)})


def generation_messages(request, exchanges, schema, contract=None):
    # Deliberately no case IDs, policy, extractor guesses, ratings, gold or thresholds.
    contract = build_constraints(request, exchanges) if contract is None else contract
    return messages(GENERATE, {**public_context(request), "clarifications": exchanges,
                              "visible_constraints": contract, "output_schema": schema})


def constraint_repair_messages(original, raw, errors, measurements=None):
    report = (" Complete measurements of the same visible requirements, including passing requirements: "
              + json.dumps(measurements, ensure_ascii=False)) if measurements is not None else ""
    return original + [{"role": "assistant", "content": raw},
                       {"role": "user", "content":
                        "A deterministic check of requirements already visible above found these issues: "
                        + json.dumps(errors, ensure_ascii=False) + report +
                        ". Return one corrected complete JSON object. Fix the listed issues while preserving all other visible requirements. "
                        "No new facts or requirements have been added. Recheck word count and verbatim phrases for writing; "
                        "rewrite toward the word-range midpoint without inventing dates, addresses, times, services or other facts. "
                        "For schedules, jointly satisfy date bounds, combined daily sums and all topic minimum totals. "
                        "A topic minimum is a total across dates; reducing a daily excess must not make that topic total too small. "
                        "This is the only constraint revision. Return your complete best effort even if some requirements remain unmet; "
                        "do not claim compliance with a requirement that still fails. Keep the output compact."}]


def decision_messages(request, exchanges, state, eligible, remaining, catalog, policy):
    return messages(PROMPT_ONLY if policy == "prompt_only" else VALUE_BASED,
                    {**public_context(request), "clarifications": exchanges,
                     "field_values": state, "eligible_fields": eligible,
                     "remaining_question_items": remaining, "fields": catalog["fields"]})


def repair_messages(original, raw, errors):
    return original + [{"role": "assistant", "content": raw},
                       {"role": "user", "content": "Your reply did not match the required JSON format. "
                        "Return a corrected complete JSON object only. Do not add new user requirements. "
                        "Format errors: " + "; ".join(errors)}]
