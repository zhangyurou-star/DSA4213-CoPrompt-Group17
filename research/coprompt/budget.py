"""Durable cumulative spending guard for explicitly authorized pilot runs."""

from __future__ import annotations

from decimal import Decimal
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile


class BudgetError(Exception):
    """Fail closed when budget evidence is inconsistent or already in use."""


def _money(value, label):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0):
        raise BudgetError(f"{label} must be a finite nonnegative dollar amount.")
    return Decimal(str(value))


def _json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        raise BudgetError("Cannot read valid budget evidence; no new API calls are allowed.") from None


class BudgetLedger:
    """Hold an exclusive lock from reconciliation through the final API event.

    Session logs are authoritative, including conservative reserves for calls
    with unknown actual cost. A mismatch requires explicit offline repair; it
    is never silently reset or granted another spending allowance.
    """

    def __init__(self, path):
        self.path = Path(path).resolve()
        self._lock = None
        self.document = None
        self.session_log = None

    def __enter__(self):
        try:
            self._lock = self.path.with_suffix(self.path.suffix + ".lock").open("a")
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            if self._lock is not None:
                self._lock.close()
                self._lock = None
            raise BudgetError("Budget ledger is unavailable or already used by another run.") from None
        try:
            self.document = _json(self.path)
            if not isinstance(self.document, dict):
                raise BudgetError("Budget ledger must be an object.")
            self.authorized = _money(self.document.get("authorized_total_usd"), "Authorized budget")
            saved = _money(self.document.get("accounted_spend_usd"), "Recorded spending")
            self.spent = self._reconcile()
            if saved != self.spent:
                raise BudgetError("Budget ledger and persisted API costs disagree; reconcile before running.")
            if self.spent > self.authorized:
                raise BudgetError("Recorded spending exceeds the authorized budget.")
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *exc):
        if self._lock is not None:
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_UN)
            self._lock.close()
            self._lock = None

    def _paths(self):
        refs = self.document.get("source_session_logs")
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
            raise BudgetError("Budget ledger must list its session logs.")
        paths = [(self.path.parent / ref).resolve() for ref in refs]
        if len(set(paths)) != len(paths):
            raise BudgetError("Budget ledger contains duplicate session log paths.")
        return paths

    def _reconcile(self):
        total = Decimal(0)
        for path in self._paths():
            numbers = set()
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                raise BudgetError("A recorded session log is missing or unreadable.") from None
            for line in lines:
                try:
                    event = json.loads(line)
                except ValueError:
                    raise BudgetError("A recorded session log contains invalid JSON.") from None
                if not isinstance(event, dict):
                    raise BudgetError("A recorded session log contains an invalid event.")
                if event.get("event_type") != "api_call":
                    continue
                number = event.get("api_call_number")
                if (isinstance(number, bool) or not isinstance(number, int)
                        or number < 1 or number in numbers):
                    raise BudgetError("A session log has invalid or duplicate API call numbers.")
                numbers.add(number)
                cost = _money(event.get("accounted_call_cost_usd"), "Accounted API call cost")
                known = event.get("provider_actual_cost_usd")
                if known is not None and _money(known, "Known API call cost") != cost:
                    raise BudgetError("Known API cost does not match its accounted cost.")
                total += cost
        return total

    def cap_config(self, config):
        remaining = self.authorized - self.spent
        if remaining <= 0:
            raise BudgetError("The cumulative authorized budget is exhausted.")
        configured = config.get("max_cost_usd")
        if configured is not None:
            remaining = min(remaining, _money(configured, "Configured run budget"))
        if remaining <= 0:
            raise BudgetError("The configured run budget is exhausted.")
        limit = float(remaining)
        if Decimal(str(limit)) > remaining:
            limit = math.nextafter(limit, 0)
        return dict(config, max_cost_usd=limit)

    def _save(self):
        descriptor, temporary = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(self.document, handle, ensure_ascii=False, indent=2, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def register_session(self, session_log):
        if self._lock is None or self.session_log is not None:
            raise BudgetError("Register one session while holding the budget lock.")
        path = Path(session_log).resolve()
        if path in self._paths():
            raise BudgetError("The new session is already registered.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        reference = os.path.relpath(path, self.path.parent)
        self.document["source_session_logs"].append(reference)
        self._save()
        self.session_log = path

    def record_event(self, event):
        if self._lock is None or self.session_log is None:
            raise BudgetError("A locked session must be registered before saving API events.")
        with self.session_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.spent = self._reconcile()
        self.document["accounted_spend_usd"] = float(self.spent)
        self._save()
        if self.spent > self.authorized:
            raise BudgetError("Recorded cost exceeded the authorization; the run must stop.")
