"""Small, auditable OpenAI-compatible transport; no automatic retries."""

from __future__ import annotations

import json
import http.client
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from typing import Any, Callable


class ProviderError(Exception):
    """A sanitized error safe to display or record in a run log."""

    def __init__(self, message: str, *, code: str = "provider_error") -> None:
        super().__init__(message)
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward a bearer token, even to another HTTPS origin.
        return None


def _positive_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _safe_cost(body: dict) -> float | None:
    # These are explicit provider-reported dollar fields; never infer a price.
    for container in (body, body.get("usage")):
        if isinstance(container, dict):
            keys = ("cost_usd", "cost") if container is body.get("usage") else ("cost_usd",)
            for key in keys:
                value = container.get(key)
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0
                ):
                    return float(value)
    return None


class ApiClient:
    """A single-run client with a hard cap on attempted HTTP requests.

    The caller supplies credentials directly; this module never reads them from
    files or environment variables. Each call records the public request and
    response. The bearer value is recursively redacted from every log string.
    """

    def __init__(
        self,
        config: dict,
        api_key: str,
        log_callback: Callable[[dict], None] | None = None,
    ) -> None:
        self.config = deepcopy(config)
        self._api_key = api_key
        self._log_callback = log_callback
        self.calls_made = 0
        self.accounted_cost_usd = 0.0
        self.known_cost_usd = 0.0
        self.estimated_cost_usd = 0.0
        base_url = config.get("base_url")
        try:
            if not isinstance(base_url, str) or any(c.isspace() for c in base_url):
                raise ValueError
            parsed = urllib.parse.urlsplit(base_url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or "?" in base_url
                or "#" in base_url
            ):
                raise ValueError
            _ = parsed.port
        except (TypeError, ValueError):
            raise ProviderError(
                "base_url must be HTTPS without credentials, query, or fragment.",
                code="invalid_endpoint",
            ) from None
        if not isinstance(api_key, str) or not api_key or any(c in api_key for c in "\r\n"):
            raise ProviderError("A nonempty API key is required.", code="invalid_api_key")
        model = config.get("model")
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("An explicit model ID is required.", code="invalid_config")
        self.max_api_calls = config.get("max_api_calls")
        if not _positive_integer(self.max_api_calls):
            raise ProviderError("max_api_calls must be a positive integer.", code="invalid_config")
        timeout = config.get("timeout_seconds", 60)
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ProviderError("timeout_seconds must be positive and finite.", code="invalid_config")
        self.timeout_seconds = timeout
        limits = config.get("max_output_tokens")
        if not isinstance(limits, dict):
            raise ProviderError("max_output_tokens must define stage token limits.", code="invalid_config")
        self.routing = deepcopy(config.get("provider_routing"))
        if self.routing is not None:
            allowed = {"order", "only", "allow_fallbacks", "require_parameters", "max_price"}
            if not isinstance(self.routing, dict) or set(self.routing) - allowed:
                raise ProviderError("Unsupported provider routing settings.", code="invalid_config")
            for key in ("order", "only"):
                value = self.routing.get(key)
                if value is not None and (
                    not isinstance(value, list) or not value
                    or any(not isinstance(item, str) or not item for item in value)
                ):
                    raise ProviderError("Provider routing lists must contain provider names.", code="invalid_config")
            for key in ("allow_fallbacks", "require_parameters"):
                if key in self.routing and not isinstance(self.routing[key], bool):
                    raise ProviderError("Provider routing flags must be boolean.", code="invalid_config")
            prices = self.routing.get("max_price")
            if prices is not None and (
                not isinstance(prices, dict) or set(prices) - {"prompt", "completion"}
                or any(isinstance(v, bool) or not isinstance(v, (float, int))
                       or not math.isfinite(v) or v < 0 for v in prices.values())
            ):
                raise ProviderError("Provider maximum prices must be finite dollar rates.", code="invalid_config")
        self.max_cost_usd = config.get("max_cost_usd")
        if self.max_cost_usd is not None:
            if (
                isinstance(self.max_cost_usd, bool)
                or not isinstance(self.max_cost_usd, (int, float))
                or not math.isfinite(self.max_cost_usd)
                or self.max_cost_usd <= 0
                or self.routing is None
                or not {"prompt", "completion"}.issubset(self.routing.get("max_price", {}))
            ):
                raise ProviderError(
                    "A positive cost cap requires explicit maximum prompt and completion prices.",
                    code="invalid_config",
                )
        self.endpoint = base_url.rstrip("/") + "/chat/completions"
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _redact(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(self._api_key, "[REDACTED]")
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, dict):
            return {self._redact(key): self._redact(item) for key, item in value.items()}
        return value

    def _emit(self, event: dict) -> None:
        if self._log_callback is not None:
            try:
                self._log_callback(self._redact(event))
            except Exception:
                raise ProviderError(
                    "API event could not be saved; stop the run and check the log destination.",
                    code="logging_failed",
                ) from None

    def _availability_diagnostic(self, error: urllib.error.HTTPError) -> dict:
        """Keep only bounded, allowlisted rate-limit/service diagnostics."""
        def safe_text(value: Any, limit: int) -> str | None:
            if not isinstance(value, str):
                return None
            # Redact before truncation so a boundary cannot expose a partial key.
            value = " ".join(self._redact(value).split())
            return value[:limit] if value else None

        diagnostic = {}
        retry_after = safe_text(error.headers.get("Retry-After") if error.headers else None, 128)
        if retry_after is not None:
            diagnostic["retry_after"] = retry_after
        try:
            body = json.loads(error.read(16384))
            details = body.get("error") if isinstance(body, dict) else None
            if not isinstance(details, dict):
                return diagnostic
            message = safe_text(details.get("message"), 512)
            if message is not None:
                diagnostic["message"] = message
            metadata = details.get("metadata")
            if isinstance(metadata, dict):
                for key in ("limit_source", "provider_name"):
                    value = safe_text(metadata.get(key), 128)
                    if value is not None:
                        diagnostic[key] = value
        except (ValueError, TypeError, UnicodeDecodeError, OSError, http.client.HTTPException):
            # Raw or malformed bodies are never copied into diagnostics.
            pass
        return diagnostic

    def _finish(self, event: dict, estimated_cost: float | None) -> None:
        actual = event.get("provider_actual_cost_usd")
        accounted = actual if actual is not None else estimated_cost
        event["estimated_call_cost_usd"] = estimated_cost
        event["accounted_call_cost_usd"] = accounted
        event["cost_basis"] = (
            "provider_reported" if actual is not None else
            "estimated_upper_bound" if estimated_cost is not None else "unavailable"
        )
        if accounted is not None:
            self.accounted_cost_usd += accounted
            if actual is not None:
                self.known_cost_usd += accounted
            else:
                self.estimated_cost_usd += accounted
        event["accounted_run_cost_usd"] = self.accounted_cost_usd
        self._emit(event)

    def complete(
        self,
        messages: list[dict],
        *,
        stage: str,
        case_id: str,
        policy: str,
        repair: bool = False,
        repair_kind: str | None = None,
    ) -> str:
        if self.calls_made >= self.max_api_calls:
            raise ProviderError(
                "The configured API call limit has been reached; no request was sent.",
                code="call_limit_reached",
            )
        max_tokens = self.config.get("max_output_tokens", {}).get(stage)
        if not _positive_integer(max_tokens):
            raise ProviderError("This stage has no positive output token limit.", code="invalid_stage")
        payload = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": self.config.get("temperature", 0),
            "top_p": self.config.get("top_p", 1),
            "max_tokens": max_tokens,
            "stream": False,
        }
        if self.config.get("seed") is not None:
            payload["seed"] = self.config["seed"]
        if self.routing is not None:
            payload["provider"] = self.routing
        try:
            data = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
            price_caps = self.routing.get("max_price", {}) if self.routing else {}
            estimate = None
            if {"prompt", "completion"}.issubset(price_caps):
                input_upper_bound = len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) + 1024
                estimate = (input_upper_bound * price_caps["prompt"]
                            + max_tokens * price_caps["completion"]) / 1_000_000
            if self.max_cost_usd is not None and self.accounted_cost_usd + estimate > self.max_cost_usd:
                raise ProviderError(
                    "The next request would exceed the configured conservative cost cap; no request was sent.",
                    code="cost_limit_reached",
                )
            request = urllib.request.Request(
                self.endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": "Bearer " + self._api_key,
                },
                method="POST",
            )
        except (TypeError, ValueError):
            raise ProviderError("Request data is not valid JSON.", code="invalid_request") from None
        self.calls_made += 1
        event = {
            "event_type": "api_call",
            "api_call_number": self.calls_made,
            "provider": self.config.get("provider"),
            "case_id": case_id,
            "policy": policy,
            "stage": stage,
            "repair": repair,
            "repair_kind": (repair_kind or "format") if repair else None,
            "requested_model": self.config["model"],
            "request_settings": {key: value for key, value in payload.items() if key != "messages"},
            "messages": deepcopy(messages),
            "response_id": None,
            "response_model": None,
            "response_provider": None,
            "system_fingerprint": None,
            "usage": None,
            "input_tokens": None,
            "output_tokens": None,
            "finish_reason": None,
            "provider_actual_cost_usd": None,
            "raw_content": None,
        }
        started = time.monotonic()
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            diagnostic = self._availability_diagnostic(error) if status in (429, 503) else {}
            error.close()
            if 300 <= status < 400:
                code = "redirect_blocked"
                message = "API redirect blocked; configure the provider's final HTTPS endpoint."
            elif status in (401, 403):
                code = "authentication_failed"
                message = f"API authorization failed (HTTP {status}); check key and model access."
            else:
                code = "http_error"
                message = f"API request failed (HTTP {status}); inspect provider status or configuration."
            event.update(status="error", error_code=code, http_status=status,
                         latency_seconds=time.monotonic() - started)
            if diagnostic:
                event["provider_error_diagnostic"] = diagnostic
                message += " " + "; ".join(f"{key}: {value}" for key, value in diagnostic.items())
            self._finish(event, estimate)
            raise ProviderError(message, code=code) from None
        except (urllib.error.URLError, OSError, TimeoutError, ValueError, http.client.HTTPException):
            event.update(status="error", error_code="transport_error",
                         latency_seconds=time.monotonic() - started)
            self._finish(event, estimate)
            raise ProviderError(
                "API transport failed; check network, endpoint, and timeout.",
                code="transport_error",
            ) from None
        event["latency_seconds"] = time.monotonic() - started
        try:
            body = json.loads(raw)
            if not isinstance(body, dict) or body.get("error") is not None:
                raise ValueError
            choices = body.get("choices")
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                raise ValueError
            choice = choices[0]
            message = choice.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ValueError
            content = message["content"]
            usage = body.get("usage")
            if usage is not None and not isinstance(usage, dict):
                raise ValueError
            event.update(
                status="success",
                response_id=body.get("id"),
                response_model=body.get("model"),
                response_provider=body.get("provider"),
                system_fingerprint=body.get("system_fingerprint"),
                usage=usage,
                input_tokens=usage.get("prompt_tokens") if usage else None,
                output_tokens=usage.get("completion_tokens") if usage else None,
                finish_reason=choice.get("finish_reason"),
                provider_actual_cost_usd=_safe_cost(body),
                raw_content=content,
            )
        except (ValueError, TypeError, UnicodeDecodeError):
            event.update(status="error", error_code="invalid_response_envelope")
            self._finish(event, estimate)
            raise ProviderError(
                "API returned an invalid chat completion envelope; no output was accepted.",
                code="invalid_response_envelope",
            ) from None
        self._finish(event, estimate)
        return content
