"""Public-state controller; simulator replies are exposed only after ASK."""

import copy
import hashlib
import json
from pathlib import Path

from . import prompts
from .grounding import GROUNDING_VERSION, evidence_errors, resolve_evidence, source_units
from .scoring import validate_output
from .visible_constraints import (CONSTRAINT_VERSION, SUMMARY_VERSION, build_constraints,
                                  check_constraints, derive_schedule_summary, visible_measurements)

POLICIES = ("direct", "exhaustive", "prompt_only", "value_based")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def read_jsonl(path):
    rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    ids = [r["case_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate case_id")
    return {r["case_id"]: r for r in rows}


def extraction_errors(obj, fields):
    if not isinstance(obj, dict) or set(obj) != {"field_values"}:
        return ["Object must contain only field_values"]
    values = obj["field_values"]
    if not isinstance(values, dict) or set(values) != set(fields):
        return ["field_values must contain exactly all four listed fields"]
    return ["Each field value must be null or a non-empty string"] if any(
        v is not None and (not isinstance(v, str) or not v.strip()) for v in values.values()) else []


def decision_errors(obj):
    if not isinstance(obj, dict):
        return ["Decision must be an object"]
    if obj == {"action": "ACT"}:
        return []
    if (set(obj) == {"action", "field_id"} and obj["action"] == "ASK"
            and isinstance(obj["field_id"], str) and obj["field_id"].strip()):
        return []  # Invalid/repeated IDs are valid ASK items and still consume budget.
    return ["Use ACT only, or ASK plus one non-empty field_id"]


def rating_errors(obj, eligible):
    if not isinstance(obj, dict) or set(obj) != {"ratings"} or not isinstance(obj["ratings"], list):
        return ["Object must contain only a ratings array"]
    ids = []
    for r in obj["ratings"]:
        if not isinstance(r, dict) or set(r) != {"field_id", "importance", "uncertainty", "reason"}:
            return ["Each rating needs field_id, importance, uncertainty and reason"]
        if (type(r["importance"]) not in (int, float) or r["importance"] not in (0, .5, 1)
                or type(r["uncertainty"]) not in (int, float) or r["uncertainty"] not in (.5, 1)
                or not isinstance(r["field_id"], str)
                or not isinstance(r["reason"], str) or not r["reason"].strip()):
            return ["Invalid rating level, field_id or reason"]
        ids.append(r["field_id"])
    return [] if len(ids) == len(set(ids)) and set(ids) == set(eligible) else ["Cover every eligible field exactly once"]


def strict_json(text):
    def invalid_constant(value):
        raise ValueError("Non-standard JSON constant")
    def unique_object(pairs):
        result = {}
        for key, val in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = val
        return result
    return json.loads(text, parse_constant=invalid_constant, object_pairs_hook=unique_object)


class PilotRunner:
    def __init__(self, client, catalog, schemas, *, cache_dir=None,
                 generation_cache_dir=None, lambda_value=.25, budget=3,
                 importance_override=None):
        if importance_override is not None and (type(importance_override) is not int or importance_override != 1):
            raise ValueError("importance_override must be None or integer 1")
        self.client, self.catalog, self.schemas = client, catalog, schemas
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = {}
        self.generation_cache_dir = Path(generation_cache_dir) if generation_cache_dir else None
        if self.generation_cache_dir:
            self.generation_cache_dir.mkdir(parents=True, exist_ok=True)
        self.generation_cache = {}
        self.lambda_value, self.budget = lambda_value, budget
        self.importance_override = importance_override

    def formatted_call(self, messages, validator, *, stage, case_id, policy):
        attempts = []
        for attempt in range(2):
            raw = self.client.complete(messages, stage=stage, case_id=case_id, policy=policy, repair=bool(attempt))
            try:
                obj = strict_json(raw)
                errors = validator(obj)
            except (ValueError, TypeError):
                obj, errors = None, ["Response is not one strict JSON object"]
            attempts.append({"raw": raw, "parsed": obj, "format_errors": errors})
            if not errors:
                return obj, {"attempts": attempts, "repaired": bool(attempt), "failed": False}
            if attempt == 0:
                messages = prompts.repair_messages(messages, raw, errors)
        return None, {"attempts": attempts, "repaired": True, "failed": True}

    def extract(self, request):
        cat = self.catalog[request["domain"]]
        msg = prompts.extraction_messages(request, cat)
        model_settings = {k: self.client.config.get(k) for k in
                          ("provider", "base_url", "model", "temperature", "top_p", "seed", "max_output_tokens", "provider_routing")}
        model_input = {"messages": msg, "model_settings": model_settings,
                       "prompt_version": prompts.PROMPT_VERSION}
        key = digest({**model_input, "grounding_version": GROUNDING_VERSION})
        cache_file = self.cache_dir / (key + ".json") if self.cache_dir else None
        if key in self.cache:
            return copy.deepcopy(self.cache[key]), True
        if cache_file and cache_file.exists():
            cached = json.loads(cache_file.read_text())
            if (cached.get("cache_key") != key or cached.get("grounding_version") != GROUNDING_VERSION
                    or evidence_errors({"field_evidence": cached.get("raw_field_evidence")},
                                       cat["field_order"], source_units(request))):
                raise ValueError("Invalid extraction cache; inspect before continuing")
            state, evidence, rejections = resolve_evidence(request, cached["raw_field_evidence"])
            if (cached.get("source_units") != source_units(request)
                    or cached.get("field_values") != state or cached.get("evidence") != evidence
                    or cached.get("grounding_rejections") != rejections):
                raise ValueError("Invalid extraction cache; inspect before continuing")
            self.cache[key] = cached
            return copy.deepcopy(cached), True
        # Recompute derived evidence after a guard-only change using the same
        # original model response. No retry, gold lookup or best-result selection.
        previous = []
        if self.cache_dir:
            for path in self.cache_dir.glob("*.json"):
                old = json.loads(path.read_text())
                version = old.get("grounding_version")
                if (version and version != GROUNDING_VERSION
                        and old.get("cache_key") == digest({**model_input, "grounding_version": version})):
                    previous.append(old)
        source_cache_key = None
        if previous:
            outcomes = {digest(p["attempts"]) for p in previous}
            if len(outcomes) != 1:
                raise ValueError("Conflicting original extraction responses; inspect before continuing")
            old = previous[0]
            record = {k: copy.deepcopy(old[k]) for k in ("attempts", "repaired", "failed")}
            obj = None if record["failed"] else strict_json(record["attempts"][-1]["raw"])
            if obj is not None and evidence_errors(obj, cat["field_order"], source_units(request)):
                raise ValueError("Invalid original extraction response")
            source_cache_key = old["cache_key"]
        else:
            obj, record = self.formatted_call(msg, lambda v: evidence_errors(v, cat["field_order"], source_units(request)),
                                              stage="extraction", case_id=request["case_id"], policy="shared")
        raw_evidence = obj["field_evidence"] if obj else {f: [] for f in cat["field_order"]}
        state, evidence, rejections = resolve_evidence(request, raw_evidence)
        cached = {"cache_key": key, "grounding_version": GROUNDING_VERSION,
                  "raw_field_evidence": raw_evidence, "source_units": source_units(request), "field_values": state,
                  "evidence": evidence, "grounding_rejections": rejections, **record}
        if source_cache_key:
            cached["raw_response_source_cache_key"] = source_cache_key
        self.cache[key] = cached
        if cache_file:
            cache_file.write_text(json.dumps(cached, ensure_ascii=False, indent=2) + "\n")
        return copy.deepcopy(cached), bool(source_cache_key)

    def _generation_cache_key(self, messages):
        # Include every transport setting that can affect model output, but no
        # policy/case identity, credentials, budgets or private annotations.
        config = self.client.config
        settings = {
            "provider": config.get("provider"), "base_url": config.get("base_url"),
            "model": config.get("model"), "temperature": config.get("temperature", 0),
            "top_p": config.get("top_p", 1), "seed": config.get("seed"),
            "max_output_tokens": config.get("max_output_tokens", {}).get("generation"),
            "provider_routing": getattr(self.client, "routing", config.get("provider_routing")),
            "stream": False,
        }
        return digest({"messages": messages, "model_settings": settings,
                       "prompt_version": prompts.GENERATION_PROMPT_VERSION,
                       "constraint_version": CONSTRAINT_VERSION, "summary_version": SUMMARY_VERSION,
                       "generation_cache_version": 3})

    @staticmethod
    def _validate_generation_cache(cached, key, domain, contract):
        error = "Invalid generation cache; inspect before continuing"
        expected = {"cache_key", "source_case_id", "source_policy", "output",
                    "attempts", "repaired", "failed", "constraint_version", "constraint_contract",
                    "constraint_checks_initial", "constraint_checks_final",
                    "constraint_repair_attempted", "constraint_repair", "visible_measurements_initial",
                    "visible_measurements_final", "summary_derivation"}
        if (not isinstance(cached, dict) or set(cached) != expected
                or cached["cache_key"] != key
                or not isinstance(cached["source_case_id"], str) or not cached["source_case_id"].strip()
                or cached["source_policy"] not in POLICIES
                or type(cached["repaired"]) is not bool or type(cached["failed"]) is not bool
                or not isinstance(cached["attempts"], list) or len(cached["attempts"]) not in (1, 2)
                or cached["repaired"] != (len(cached["attempts"]) == 2)
                or cached["constraint_version"] != CONSTRAINT_VERSION
                or cached["constraint_contract"] != contract
                or type(cached["constraint_repair_attempted"]) is not bool):
            raise ValueError(error)
        last_parsed, last_errors = None, []
        for index, attempt in enumerate(cached["attempts"]):
            if (not isinstance(attempt, dict) or set(attempt) != {"raw", "parsed", "format_errors"}
                    or not isinstance(attempt["raw"], str)):
                raise ValueError(error)
            try:
                parsed = strict_json(attempt["raw"])
                errors = validate_output(domain, parsed)
            except (TypeError, ValueError):
                parsed, errors = None, ["Response is not one strict JSON object"]
            if attempt["parsed"] != parsed or attempt["format_errors"] != errors:
                raise ValueError(error)
            if index < len(cached["attempts"]) - 1 and not errors:
                raise ValueError(error)
            last_parsed, last_errors = parsed, errors
        if cached["failed"]:
            if len(cached["attempts"]) != 2 or not last_errors or cached["output"] is not None:
                raise ValueError(error)
        elif last_errors:
            raise ValueError(error)
        initial = None if cached["failed"] else last_parsed
        issues = check_constraints(domain, initial, contract) if initial is not None else []
        if cached["constraint_checks_initial"] != issues or cached["constraint_repair_attempted"] != bool(issues):
            raise ValueError(error)
        if cached["visible_measurements_initial"] != visible_measurements(domain, initial, contract):
            raise ValueError(error)
        final = initial
        repair = cached["constraint_repair"]
        if issues:
            if not isinstance(repair, dict) or set(repair) != {"raw", "parsed", "format_errors", "accepted"}:
                raise ValueError(error)
            if not isinstance(repair["raw"], str) or type(repair["accepted"]) is not bool:
                raise ValueError(error)
            parsed, errors = PilotRunner._parse_generation(domain, repair["raw"])
            if repair["parsed"] != parsed or repair["format_errors"] != errors or repair["accepted"] != (not errors):
                raise ValueError(error)
            if not errors:
                final = parsed
        elif repair is not None:
            raise ValueError(error)
        final, derivation = derive_schedule_summary(domain, final, contract)
        final_issues = check_constraints(domain, final, contract) if final is not None else []
        if (cached["output"] != final or cached["constraint_checks_final"] != final_issues
                or cached["summary_derivation"] != derivation
                or cached["visible_measurements_final"] != visible_measurements(domain, final, contract)):
            raise ValueError(error)

    @staticmethod
    def _parse_generation(domain, raw):
        try:
            parsed = strict_json(raw)
            return parsed, validate_output(domain, parsed)
        except (TypeError, ValueError):
            return None, ["Response is not one strict JSON object"]

    def generate(self, request, exchanges, policy):
        domain = request["domain"]
        contract = build_constraints(request, exchanges)
        messages = prompts.generation_messages(request, exchanges, self.schemas[domain], contract)
        key = self._generation_cache_key(messages)
        cache_file = self.generation_cache_dir / (key + ".json") if self.generation_cache_dir else None
        if key in self.generation_cache:
            cached = copy.deepcopy(self.generation_cache[key])
            return cached["output"], cached, True
        if cache_file and cache_file.exists():
            try:
                cached = strict_json(cache_file.read_text())
                self._validate_generation_cache(cached, key, domain, contract)
            except (ValueError, TypeError, KeyError):
                raise ValueError("Invalid generation cache; inspect before continuing") from None
            self.generation_cache[key] = copy.deepcopy(cached)
            return cached["output"], cached, True
        output, record = self.formatted_call(messages, lambda v: validate_output(request["domain"], v),
                                             stage="generation", case_id=request["case_id"], policy=policy)
        initial_issues = check_constraints(domain, output, contract) if output is not None else []
        initial_measurements = visible_measurements(domain, output, contract)
        constraint_repair = None
        if initial_issues:
            # One shared, bounded revision based exclusively on already-visible
            # requirements. No private score, reference answer or output ranking.
            repair_messages = prompts.constraint_repair_messages(messages, record["attempts"][-1]["raw"],
                                                                 initial_issues, initial_measurements)
            raw = self.client.complete(repair_messages, stage="generation", case_id=request["case_id"],
                                       policy=policy, repair=True, repair_kind="constraint")
            parsed, errors = self._parse_generation(domain, raw)
            constraint_repair = {"raw": raw, "parsed": parsed, "format_errors": errors, "accepted": not errors}
            # A malformed revision does not destroy a valid first draft. A valid
            # revision is always used, even if it still violates constraints.
            if not errors:
                output = parsed
        output, derivation = derive_schedule_summary(domain, output, contract)
        cached = {"cache_key": key, "source_case_id": request["case_id"], "source_policy": policy,
                  "output": output, **record, "constraint_version": CONSTRAINT_VERSION,
                  "constraint_contract": contract, "constraint_checks_initial": initial_issues,
                  "constraint_checks_final": check_constraints(domain, output, contract) if output is not None else [],
                  "constraint_repair_attempted": bool(initial_issues), "constraint_repair": constraint_repair,
                  "visible_measurements_initial": initial_measurements,
                  "visible_measurements_final": visible_measurements(domain, output, contract),
                  "summary_derivation": derivation}
        # Cache the first complete bounded pipeline, including unresolved failures.
        # Scores never influence selection and identical inputs get no new draw.
        self.generation_cache[key] = copy.deepcopy(cached)
        if cache_file:
            temporary = cache_file.with_suffix(".tmp")
            temporary.write_text(json.dumps(cached, ensure_ascii=False, indent=2) + "\n")
            temporary.replace(cache_file)
        return cached["output"], cached, False

    def run_trajectory(self, request, policy, answer_callback):
        if policy not in POLICIES:
            raise ValueError("Unknown policy")
        cat = self.catalog[request["domain"]]
        fields = cat["field_order"]
        templates = {f["field_id"]: f["question_template"] for f in cat["fields"]}
        extraction, cache_hit = self.extract(request)
        state = copy.deepcopy(extraction["field_values"])
        asked, unavailable, exchanges, decisions = set(), set(), [], []
        question_count = invalid_count = 0
        while True:
            eligible = [f for f in fields if state[f] is None and f not in asked and f not in unavailable]
            if policy == "direct":
                stop = "direct_policy"
            elif request["user_control"] == "execute_now":
                stop = "execute_now"
            elif question_count >= self.budget:
                stop = "question_budget_exhausted"
            elif not eligible:
                stop = "no_eligible_fields"
            else:
                stop = None
            if stop:
                decisions.append({"action": "ACT", "stop_reason": stop, "decision_call_skipped": True})
                break
            record = {"step": len(decisions) + 1, "eligible_fields": eligible,
                      "budget_before": self.budget - question_count}
            if policy == "exhaustive":
                action = {"action": "ASK", "field_id": eligible[0]}
            else:
                msg = prompts.decision_messages(request, exchanges, state, eligible, self.budget - question_count, cat, policy)
                validator = decision_errors if policy == "prompt_only" else lambda v: rating_errors(v, eligible)
                obj, call = self.formatted_call(msg, validator, stage="decision", case_id=request["case_id"], policy=policy)
                record["model_call"] = call
                if obj is None:
                    record.update(action="ACT", stop_reason="controller_failure")
                    decisions.append(record)
                    break
                if policy == "prompt_only":
                    action = obj
                else:
                    ratings = {r["field_id"]: r for r in obj["ratings"]}
                    effective_importance = {f: (ratings[f]["importance"] if self.importance_override is None
                                                 else self.importance_override) for f in eligible}
                    scores = {f: effective_importance[f] * ratings[f]["uncertainty"] - self.lambda_value for f in eligible}
                    best = max(eligible, key=lambda f: scores[f])
                    record.update(ratings=obj["ratings"], values=scores, lambda_value=self.lambda_value,
                                  importance_override=self.importance_override, effective_importance=effective_importance)
                    action = {"action": "ASK", "field_id": best} if scores[best] > 0 else {"action": "ACT"}
            record.update(action)
            if action["action"] == "ACT":
                record["stop_reason"] = "policy_act"
                decisions.append(record)
                break
            question_count += 1
            field = action["field_id"]
            if field not in eligible:
                invalid_count += 1
                record["error"] = "invalid_or_repeated_field"
                exchange = {"field_id": field, "question": templates.get(field, "Invalid field request"),
                            "status": "error", "answer_text": "This field is invalid or already resolved or requested. Choose an eligible field or ACT."}
            else:
                reply = answer_callback(field)
                if set(reply) != {"status", "text"} or reply["status"] not in ("available", "unknown", "declined") or not isinstance(reply["text"], str) or not reply["text"].strip():
                    raise ValueError("Invalid simulator answer")
                asked.add(field)
                if reply["status"] == "available":
                    state[field] = reply["text"]
                else:
                    unavailable.add(field)
                exchange = {"field_id": field, "question": templates[field], "status": reply["status"], "answer_text": reply["text"]}
            record["budget_after"] = self.budget - question_count
            decisions.append(record)
            exchanges.append(exchange)
        output, generation, generation_cache_hit = self.generate(request, exchanges, policy)
        return {"case_id": request["case_id"], "domain": request["domain"], "system_id": policy,
                "prompt_version": prompts.PROMPT_VERSION, "extraction": extraction, "extraction_cache_hit": cache_hit,
                "decisions": decisions, "visible_exchanges": exchanges, "question_items": question_count,
                "valid_question_items": question_count - invalid_count, "invalid_question_items": invalid_count,
                "generation": generation, "generation_cache_hit": generation_cache_hit, "output": output}
