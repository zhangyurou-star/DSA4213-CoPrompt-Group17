"""Fresh 120-case experiment: gated pilot, complete design, validation and test."""
from __future__ import annotations
import argparse
import copy
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import fcntl
import getpass
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from .budget import BudgetLedger, BudgetError
from .provider import ApiClient, ProviderError
from .runner import PilotRunner, POLICIES, digest, read_jsonl, strict_json
from .scoring import score_output

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[1]
CUMULATIVE_LEDGER = PROJECT_ROOT / 'runs/authorized_pilot_budget.json'
VERSION = 'v0.6.0'
STAGES = ('pilot_a', 'pilot_b', 'design', 'validation', 'test')
EXPECTED_CASES = {'design_all': 40, 'pilot_a': 12, 'pilot_b': 12, 'design': 28, 'validation': 20, 'test': 60}
PLANNED_TRAJECTORIES = {'pilot_a': 24, 'pilot_b': 24, 'design': 112, 'validation': 60, 'test': 260}
PILOT_IDS = tuple(f'ND{domain}{index:02d}' for domain in ('CW', 'SP') for index in range(1, 7))
CACHE_DIRECTORIES = ('formal_raw_response_cache', 'extraction_cache', 'generation_cache')
METHOD_MODULES = ('__init__', 'budget', 'grounding', 'prompts', 'provider', 'runner', 'scoring', 'visible_constraints')
BUDGET_TRANSACTION = 'runs/fresh_budget_transaction.json'
FRESH_ENTRYPOINTS = ('tools/preflight_fresh.py', 'tools/show_status.py')


def expected_ids(split):
    prefix, count = {'design_all': ('ND', 20), 'validation': ('NV', 10), 'test': ('NT', 30)}[split]
    return tuple(f'{prefix}{domain}{index:02d}' for domain in ('CW', 'SP') for index in range(1, count + 1))


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def dump(path, obj):
    """Atomic, durable metadata/cache writes (never expose a half JSON file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def append(path, obj):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + '\n')
        f.flush(); os.fsync(f.fileno())
    sync_directory(path.parent)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return strict_json(path.read_text(encoding='utf-8'))


def rooted(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError('Evidence paths must be relative to the project')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes the project')
    return path


def verify_freeze(root, freeze):
    from .localization import verify_localized_freeze
    if verify_localized_freeze(root, freeze):
        return
    if not isinstance(freeze, dict) or freeze.get('status') != 'frozen_before_pilot_outputs':
        raise ValueError('A complete freeze before the fresh pilot is required.')
    if not isinstance(freeze.get('files'), dict) or not freeze['files']:
        raise ValueError('Frozen files must be a nonempty hash mapping')
    for name, expected in freeze['files'].items():
        path = rooted(root, name)
        if not path.is_file() or file_hash(path) != expected:
            raise ValueError('Frozen source or dataset changed: ' + name)


def money(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise BudgetError('Expected a finite nonnegative monetary amount')
    return Decimal(str(value))


def canonical_money(value):
    """Exact projection into the ledger's existing JSON-number representation.

    Log sums remain Decimal for all spending and cap arithmetic. The ledger
    stores float(total), so its persisted number must match that one projection,
    not an epsilon range and not the unrepresentable exact sum itself.
    """
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise BudgetError('Expected a finite nonnegative exact monetary total')
    return money(float(value))


def durable_text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            handle.write(value); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path); sync_directory(path.parent)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def session_rows(value):
    if not isinstance(value, str) or (value and not value.endswith('\n')):
        raise BudgetError('Invalid fresh budget transaction session text')
    rows = [strict_json(line) for line in value.splitlines()]
    if any(not isinstance(row, dict) for row in rows):
        raise BudgetError('Invalid fresh budget transaction session event')
    return rows


def verify_budget_transaction(root, ledger, transaction):
    """Accept only one registered fresh session's exact reserve/settle transition."""
    keys = {'version', 'kind', 'ledger_path', 'session', 'before_ledger', 'after_ledger',
            'before_session', 'after_session', 'payload_sha256'}
    if (not isinstance(transaction, dict) or set(transaction) != keys
            or transaction['version'] != 1
            or transaction['kind'] not in ('reserve', 'settle')
            or transaction['ledger_path'] != str(ledger.path)
            or transaction['payload_sha256'] != digest({k: v for k, v in transaction.items() if k != 'payload_sha256'})):
        raise BudgetError('Invalid fresh budget recovery transaction')
    session = rooted(root, transaction['session'])
    if (session.parent != (root / 'runs').resolve() or session.is_symlink()
            or not session.name.startswith('formal_') or not session.name.endswith('_session.jsonl')):
        raise BudgetError('Budget recovery is limited to a fresh formal session')
    before, after = transaction['before_ledger'], transaction['after_ledger']
    if (not isinstance(before, dict) or not isinstance(after, dict)
            or {k: v for k, v in before.items() if k != 'accounted_spend_usd'} !=
               {k: v for k, v in after.items() if k != 'accounted_spend_usd'}):
        raise BudgetError('Budget recovery cannot alter authorization or historical session registration')
    references = before.get('source_session_logs')
    if (not isinstance(references, list) or any(not isinstance(ref, str) for ref in references)
            or session not in {(ledger.path.parent / ref).resolve() for ref in references}):
        raise BudgetError('Budget recovery session is not registered in the cumulative ledger')
    old, new = session_rows(transaction['before_session']), session_rows(transaction['after_session'])
    if transaction['kind'] == 'reserve':
        if len(new) != len(old) + 1 or new[:-1] != old:
            raise BudgetError('A reserve may only append one event')
        reservation, final = new[-1], None
        delta = money(reservation.get('accounted_call_cost_usd'))
    else:
        if not old or len(new) != len(old) or new[:-1] != old[:-1]:
            raise BudgetError('A settlement may only replace its last reservation')
        reservation, final = old[-1], new[-1]
        delta = money(final.get('accounted_call_cost_usd')) - money(reservation.get('accounted_call_cost_usd'))
        if (final.get('event_type') != 'api_call' or final.get('api_call_number') != reservation.get('api_call_number')
                or final.get('status') not in ('success', 'error')
                or final.get('error_code') == 'unsettled_request_reservation'
                or any(key in final and final[key] != reservation[key] for key in ('case_id', 'policy', 'stage', 'repair', 'repair_kind'))):
            raise BudgetError('A settlement does not identify the reserved call')
        actual = final.get('provider_actual_cost_usd')
        if actual is not None and money(actual) != money(final.get('accounted_call_cost_usd')):
            raise BudgetError('A settlement must preserve the provider-reported charge')
    if (reservation.get('event_type') != 'api_call' or type(reservation.get('api_call_number')) is not int
            or reservation['api_call_number'] < 1 or reservation.get('status') != 'error'
            or reservation.get('error_code') != 'unsettled_request_reservation'
            or reservation.get('dispatch_status') != 'unconfirmed'
            or reservation.get('provider_actual_cost_usd') is not None
            or reservation.get('cost_basis') != 'estimated_upper_bound'
            or money(reservation.get('estimated_call_cost_usd')) != money(reservation.get('accounted_call_cost_usd'))):
        raise BudgetError('Invalid conservative reservation event')
    numbers = [row.get('api_call_number') for row in new if row.get('event_type') == 'api_call']
    if any(type(n) is not int or n < 1 for n in numbers) or len(numbers) != len(set(numbers)):
        raise BudgetError('Fresh budget transaction has duplicate or invalid call numbers')
    before_spend, after_spend = money(before.get('accounted_spend_usd')), money(after.get('accounted_spend_usd'))
    live_ledger, live_session = load(ledger.path), session.read_text(encoding='utf-8')
    if live_ledger not in (before, after) or live_session not in (transaction['before_session'], transaction['after_session']):
        raise BudgetError('Budget evidence changed outside the saved fresh transaction')
    # Validate all prior costs in the BEFORE state. This cannot repair a general
    # mismatch or drop a historical charge merely because a journal is present.
    saved = ledger.document
    try:
        ledger.document = before
        total = Decimal(0)
        for path in ledger._paths():
            text = transaction['before_session'] if path == session else path.read_text(encoding='utf-8')
            seen = set()
            for row in session_rows(text):
                if row.get('event_type') != 'api_call': continue
                number = row.get('api_call_number')
                if type(number) is not int or number < 1 or number in seen:
                    raise BudgetError('Invalid prior API event in budget recovery')
                seen.add(number)
                cost = money(row.get('accounted_call_cost_usd'))
                actual = row.get('provider_actual_cost_usd')
                if actual is not None and money(actual) != cost:
                    raise BudgetError('Prior API charge disagrees with its recorded actual cost')
                total += cost
        if canonical_money(total) != before_spend:
            raise BudgetError('A fresh transaction cannot repair inconsistent historical costs')
        if canonical_money(total + delta) != after_spend:
            raise BudgetError('Budget recovery charge delta disagrees with the one call')
    finally:
        ledger.document = saved
    return session


def apply_budget_transaction(root, ledger, transaction):
    session = verify_budget_transaction(root, ledger, transaction)
    durable_text(session, transaction['after_session'])
    ledger.document = copy.deepcopy(transaction['after_ledger'])
    ledger._save()
    ledger.spent = ledger._reconcile()
    path = rooted(root, BUDGET_TRANSACTION)
    path.unlink(); sync_directory(path.parent)


class FreshBudgetLedger(BudgetLedger):
    """The unchanged cumulative ledger, with narrowly journaled fresh recovery."""
    def __init__(self, path, root):
        super().__init__(path)
        self.root = Path(root).resolve()
        self.recovered_transaction = None

    def __enter__(self):
        # Acquire the same cross-experiment lock before inspecting any journal.
        # Reuse all inherited accounting/session methods and reconciliation.
        try:
            self._lock = self.path.with_suffix(self.path.suffix + '.lock').open('a')
            fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError):
            if self._lock is not None: self._lock.close(); self._lock = None
            raise BudgetError('Budget ledger is unavailable or already used by another run') from None
        try:
            self.document = load(self.path)
            if not isinstance(self.document, dict): raise BudgetError('Budget ledger must be an object')
            self.authorized = money(self.document.get('authorized_total_usd'))
            journal = rooted(self.root, BUDGET_TRANSACTION)
            if journal.exists():
                if journal.is_symlink(): raise BudgetError('Budget transaction cannot be a symbolic link')
                transaction = load(journal)
                apply_budget_transaction(self.root, self, transaction)
                self.recovered_transaction = transaction['kind']
            self.spent = self._reconcile()
            if money(self.document.get('accounted_spend_usd')) != canonical_money(self.spent):
                raise BudgetError('Budget ledger and persisted API costs disagree; reconcile before running')
            if self.spent > self.authorized: raise BudgetError('Recorded spending exceeds the authorized budget')
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def transaction(self, kind, event):
        if self._lock is None or self.session_log is None:
            raise BudgetError('A locked registered session is required for a reservation')
        journal = rooted(self.root, BUDGET_TRANSACTION)
        if journal.exists(): raise BudgetError('An earlier fresh budget transaction must be recovered first')
        before_text = self.session_log.read_text(encoding='utf-8')
        old = session_rows(before_text)
        if kind == 'reserve':
            new = [*old, event]
            delta = money(event.get('accounted_call_cost_usd'))
            if self.spent + delta > self.authorized:
                raise BudgetError('The next request exceeds the remaining cumulative authorization')
        elif kind == 'settle' and old:
            new = [*old[:-1], event]
            delta = money(event.get('accounted_call_cost_usd')) - money(old[-1].get('accounted_call_cost_usd'))
        else:
            raise BudgetError('Invalid budget transition')
        after = dict(self.document, accounted_spend_usd=float(self.spent + delta))
        transaction = {'version': 1, 'kind': kind, 'ledger_path': str(self.path),
            'session': str(self.session_log.relative_to(self.root)), 'before_ledger': copy.deepcopy(self.document),
            'after_ledger': after, 'before_session': before_text,
            'after_session': ''.join(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n' for row in new)}
        transaction['payload_sha256'] = digest(transaction)
        verify_budget_transaction(self.root, self, transaction)
        dump(journal, transaction)
        apply_budget_transaction(self.root, self, transaction)
        if self.spent > self.authorized:
            raise BudgetError('Recorded cost exceeded the authorization; the run must stop')


class ReservedApiClient:
    """Reserve the provider's unchanged upper bound before any HTTP dispatch."""
    def __init__(self, config, key, ledger):
        self.ledger = ledger
        self.active = None
        self.calls = 0
        self.accounted = 0.0
        self.client = ApiClient(config, key, self.settle)
        self.config, self.routing = self.client.config, self.client.routing

    def settle(self, event):
        if (self.active is None or event.get('event_type') != 'api_call'
                or event.get('api_call_number') != self.active['api_call_number']):
            raise BudgetError('Provider event does not match the pending reservation')
        event = dict(event, timestamp_utc=datetime.now(timezone.utc).isoformat())
        self.ledger.transaction('settle', event)
        self.accounted += float(money(event['accounted_call_cost_usd']))
        self.active = None

    def complete(self, messages, **kwargs):
        if self.active is not None:
            raise BudgetError('An unsettled request cannot be followed by another call in the same session')
        stage = kwargs['stage']
        limit = self.config.get('max_api_calls')
        tokens = self.config.get('max_output_tokens', {}).get(stage)
        if type(limit) is not int or self.calls >= limit or type(tokens) is not int or tokens < 1:
            raise ProviderError('Invalid or exhausted request allowance; no request was sent', code='call_limit_reached')
        # Exactly the provider.py conservative estimate; no rates are changed.
        json.dumps(messages, ensure_ascii=False, allow_nan=False)
        prices = self.routing.get('max_price', {}) if self.routing else {}
        if not {'prompt', 'completion'}.issubset(prices):
            raise BudgetError('A fresh request requires both configured maximum prices')
        input_bound = len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) + 1024
        estimate = (input_bound * prices['prompt'] + tokens * prices['completion']) / 1_000_000
        if self.accounted + estimate > self.config['max_cost_usd']:
            raise ProviderError('The next request exceeds the configured conservative cap; no request was sent', code='cost_limit_reached')
        reservation = {'event_type': 'api_call', 'api_call_number': self.calls + 1,
            'case_id': kwargs['case_id'], 'policy': kwargs['policy'], 'stage': stage,
            'repair': kwargs.get('repair', False),
            'repair_kind': (kwargs.get('repair_kind') or 'format') if kwargs.get('repair') else None,
            'status': 'error', 'error_code': 'unsettled_request_reservation', 'dispatch_status': 'unconfirmed',
            'provider_actual_cost_usd': None, 'estimated_call_cost_usd': estimate,
            'accounted_call_cost_usd': estimate, 'cost_basis': 'estimated_upper_bound',
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'note': 'Conservative reservation only; request dispatch and provider charge are not confirmed.'}
        self.ledger.transaction('reserve', reservation)
        self.active = reservation; self.calls += 1
        # KeyboardInterrupt/process death deliberately leaves the durable reserve.
        # A normal provider response/error replaces this same numbered event.
        return self.client.complete(messages, **kwargs)


def verify_registered_stage_sessions(root, ledger):
    registered = set(ledger._paths())
    for stage in STAGES:
        path = rooted(root, f'runs/formal_v0.6.0_{stage}/manifest.json')
        if not path.exists(): continue
        manifest = load(path)
        refs = manifest.get('session_logs')
        if not isinstance(refs, list): raise BudgetError('Invalid formal manifest session references')
        for ref in refs:
            session = rooted(root, ref)
            if not session.is_file() or session not in registered:
                raise BudgetError('A fresh formal session is absent from the cumulative ledger; no new API calls are allowed')


def select_lambda(trajectories, expected_ids, candidates=(0, .25, .5), target=2):
    stats = []
    exact = {}
    ids = list(expected_ids); expected = set(ids)
    if not expected or len(ids) != len(expected) or len(candidates) != len(set(candidates)):
        raise ValueError('Selection needs unique nonempty cases and candidates')
    if (not candidates or any(type(c) not in (int, float) or not math.isfinite(c) for c in candidates)
            or type(target) not in (int, float) or not math.isfinite(target) or target < 0):
        raise ValueError('Invalid selection candidates or target')
    if len(trajectories) != len(expected) * len(candidates):
        raise ValueError('Unexpected, missing or duplicate validation cells')
    for row in trajectories:
        quality = row.get('score', {}).get('quality')
        questions = row.get('question_items')
        value = row.get('lambda_value')
        if (type(value) not in (int, float) or value not in candidates
                or row.get('system_id') != f'value_lambda_{value:g}'
                or type(quality) not in (int, float) or not math.isfinite(quality) or not 0 <= quality <= 1
                or type(questions) is not int or not 0 <= questions <= 3):
            raise ValueError('Invalid or unscored validation cell')
    for value in candidates:
        rows = [t for t in trajectories if t.get('lambda_value') == value]
        if (len(rows) != len(expected) or {t['case_id'] for t in rows} != expected
                or any(t['score']['quality'] is None for t in rows)):
            raise ValueError('Every validation candidate must cover all cases exactly once.')
        stats.append({'lambda_value': value,
                      'mean_quality': sum(t['score']['quality'] for t in rows) / len(rows),
                      'mean_question_items': sum(t['question_items'] for t in rows) / len(rows),
                      'case_count': len(rows)})
        def exact_quality(row):
            checks = row['score'].get('constraint_results')
            if checks and all(type(c.get('passed')) is bool for c in checks):
                fraction = Fraction(sum(c['passed'] for c in checks), len(checks))
                if not math.isclose(float(fraction), row['score']['quality'], abs_tol=1e-12):
                    raise ValueError('Quality disagrees with constraint results')
                return fraction
            return Fraction(str(row['score']['quality']))
        exact[value] = (sum(map(exact_quality, rows), Fraction()) / len(rows),
                        Fraction(sum(t['question_items'] for t in rows), len(rows)))
    eligible = [s for s in stats if s['mean_question_items'] <= target]
    if eligible:
        selected = min(eligible, key=lambda x: (-exact[x['lambda_value']][0], exact[x['lambda_value']][1], -x['lambda_value']))
    else:
        selected = min(stats, key=lambda x: (exact[x['lambda_value']][1], -exact[x['lambda_value']][0], -x['lambda_value']))
    return {'selected_lambda': selected['lambda_value'], 'target_mean_questions': target,
            'target_met': bool(eligible), 'candidate_statistics': stats,
            'arithmetic': 'exact fractions from per-case constraint passes; decimal-exact fallback for quality-only fixtures',
            'selection_rule': f'quality_desc, questions_asc, lambda_desc among questions<={target:g}; otherwise questions_asc, quality_desc, lambda_desc'}


class DecisionReuseClient:
    """Reuse first successful raw response for exactly identical public calls.

    Includes malformed replies, but not transport exceptions. All stages are
    persisted so a generation-repair interruption cannot redraw its first draft.
    Generation also retains PilotRunner's complete-pipeline cache. The historical
    class name is retained; `hits` counts decisions and `raw_hits` all stages.
    """
    def __init__(self, client, directory, on_event):
        self.client, self.config, self.routing = client, client.config, client.routing
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.on_event = on_event
        self.variant = None
        self.hits = 0
        self.raw_hits = 0

    def complete(self, messages, **kwargs):
        external = dict(kwargs, policy=self.variant or kwargs['policy'])
        settings = {k: self.config.get(k) for k in ('provider','base_url','model','temperature','top_p','seed','max_output_tokens','provider_routing')}
        settings['effective_routing'] = self.routing
        request_identity = {'version': 'fresh120-v0.6.0-first-raw-response-1', 'stage': kwargs['stage'],
                            'repair': kwargs.get('repair', False), 'repair_kind': kwargs.get('repair_kind'),
                            'messages': messages, 'settings': settings}
        key = digest(request_identity)
        path = self.directory / (key + '.json')
        if path.exists():
            cached = load(path)
            if (not isinstance(cached, dict) or set(cached) != {'key','raw','source_case_id','source_variant','response_sha256','request_identity'}
                    or cached['key'] != key or not isinstance(cached['raw'], str)
                    or cached['request_identity'] != request_identity
                    or digest(cached['raw']) != cached['response_sha256']):
                raise ValueError('Invalid raw-response reuse record')
            self.hits += kwargs['stage'] == 'decision'
            self.raw_hits += 1
            self.on_event({'event_type':'raw_response_cache_hit','stage':kwargs['stage'],
                           'repair':kwargs.get('repair',False),'repair_kind':kwargs.get('repair_kind'),
                           'cache_key':key,'case_id':kwargs['case_id'],
                           'variant':self.variant,'source_case_id':cached['source_case_id'],
                           'source_variant':cached['source_variant']})
            return cached['raw']
        raw = self.client.complete(messages, **external)
        if not isinstance(raw, str):
            raise ValueError('Provider must return a raw string')
        dump(path, {'key':key,'raw':raw,'source_case_id':kwargs['case_id'],
                    'source_variant':self.variant,'response_sha256':digest(raw),
                    'request_identity':request_identity})
        return raw


def planned_jobs(stage, requests, selected, diagnostic):
    if stage not in STAGES or len(requests) != EXPECTED_CASES[stage]:
        raise ValueError('Incorrect fresh experiment stage or case count')
    if stage in ('pilot_a', 'pilot_b', 'design'):
        expected = set(PILOT_IDS) if stage.startswith('pilot_') else set(expected_ids('design_all')) - set(PILOT_IDS)
        if set(requests) != expected:
            raise ValueError('Pilot/design must use its fixed fresh case IDs')
        policies = POLICIES[:2] if stage == 'pilot_a' else POLICIES[2:] if stage == 'pilot_b' else POLICIES
        return [(cid, policy, policy, .25, None) for cid in requests for policy in policies]
    if stage == 'validation':
        if set(requests) != set(expected_ids('validation')):
            raise ValueError('Validation must use all 20 fresh cases')
        return [(cid, f'value_lambda_{value:g}', 'value_based', value, None)
                for cid in requests for value in (0, .25, .5)]
    if (set(requests) != set(expected_ids('test')) or type(selected) not in (int, float)
            or selected not in (0, .25, .5)):
        raise ValueError('Test requires all 60 fresh cases and a validation-selected lambda')
    if (not isinstance(diagnostic, list) or len(diagnostic) != 20 or len(set(diagnostic)) != 20
            or not set(diagnostic).issubset(requests)):
        raise ValueError('Diagnostic must contain 20 distinct preselected fresh test cases')
    if Counter(requests[cid]['domain'] for cid in diagnostic) != {'constrained_writing': 10, 'study_planning': 10}:
        raise ValueError('Diagnostic requires 10 preselected fresh cases per domain')
    jobs = []
    for cid in requests:
        jobs.extend((cid, policy, policy, selected, None) for policy in POLICIES)
        if cid in diagnostic:
            jobs.append((cid, 'importance_one', 'value_based', selected, 1))
    return jobs


def summarize(rows):
    result={}
    for variant in dict.fromkeys(r['system_id'] for r in rows):
        group=[r for r in rows if r['system_id']==variant]
        scores=[r['score']['quality'] for r in group]
        result[variant]={'n':len(group),'quality':sum(scores)/len(scores) if all(s is not None for s in scores) else None,
                         'questions':sum(r['question_items'] for r in group)/len(group),
                         'fully_passed':sum(s==1 for s in scores)}
    return result


def load_dataset(root, stage):
    if stage not in EXPECTED_CASES:
        raise ValueError('Unknown fresh dataset split')
    prefix = 'design_all' if stage in ('pilot_a', 'pilot_b', 'design') else stage
    data = tuple(read_jsonl(rooted(root, f'data/{folder}/{prefix}_{kind}.jsonl')) for folder, kind in
                 [('public', 'requests'), ('private', 'answers'), ('private', 'annotations')])
    requests, answers, annotations = data
    ids = expected_ids(prefix)
    if any(set(table) != set(ids) for table in data):
        raise ValueError('Incomplete fresh dataset or unexpected case IDs')
    for cid in ids:
        domain = 'constrained_writing' if 'CW' in cid else 'study_planning'
        if requests[cid].get('domain') != domain or annotations[cid].get('domain') != domain:
            raise ValueError('Fresh dataset domain disagrees with its registered case ID')
    if stage in ('pilot_a', 'pilot_b'):
        ids = PILOT_IDS
    elif stage == 'design':
        ids = tuple(cid for cid in ids if cid not in PILOT_IDS)
    return tuple({cid: table[cid] for cid in ids} for table in data)


def required_frozen_files():
    required = {f'data/{folder}/{split}_{kind}.jsonl' for split in ('design_all', 'validation', 'test')
                for folder, kind in [('public', 'requests'), ('private', 'answers'), ('private', 'annotations')]}
    required |= {'config/openrouter.v0.6.formal.json', 'data/case_plan.json', 'data/allocation_plan.json', 'data/public/field_catalog.json',
                 'data/schemas/output_constrained_writing.schema.json', 'data/schemas/output_study_planning.schema.json'}
    required |= {f'coprompt/{name}.py' for name in ('formal',) + METHOD_MODULES}
    required |= set(FRESH_ENTRYPOINTS)
    return required


def verify_case_plan(root, freeze):
    plan = load(rooted(root, 'data/case_plan.json'))
    allocation = load(rooted(root, 'data/allocation_plan.json'))
    if (plan.get('pilot_case_ids') != list(PILOT_IDS)
            or freeze.get('pilot_case_ids') != list(PILOT_IDS)
            or allocation.get('pilot_case_ids') != list(PILOT_IDS)
            or plan.get('diagnostic_case_ids') != freeze.get('diagnostic_case_ids')
            or allocation.get('diagnostic_case_ids') != plan.get('diagnostic_case_ids')):
        raise ValueError('Frozen pilot and diagnostic lists disagree with the registered allocation')
    datasets = {split: load_dataset(root, split) for split in ('design_all', 'validation', 'test')}
    families = [row['metadata']['family_id'] for _, _, annotations in datasets.values() for row in annotations.values()]
    if len(families) != 120 or len(set(families)) != 120:
        raise ValueError('Fresh design, validation and test must have 120 distinct families')
    all_ids = {cid for requests, _, _ in datasets.values() for cid in requests}
    registered = {}
    for label, document in (('case plan', plan), ('allocation', allocation)):
        cases = document.get('cases')
        if (not isinstance(cases, list) or len(cases) != 120
                or any(not isinstance(row, dict) for row in cases)
                or {row.get('case_id') for row in cases} != all_ids):
            raise ValueError(f'The {label} must register every fresh case exactly once')
        registered[label] = {row['case_id']: row for row in cases}
    for split, (requests, answers, annotations) in datasets.items():
        for cid, request in requests.items():
            entry, assigned = registered['case plan'][cid], registered['allocation'][cid]
            annotation = annotations[cid]
            expected = {'case_id': cid, 'split': 'design' if split == 'design_all' else split,
                        'domain': request['domain'], 'omission_type': annotation['metadata']['omission_type']}
            if (any(entry.get(key) != value or assigned.get(key) != value for key, value in expected.items())
                    or entry.get('family_id') != annotation['metadata']['family_id']
                    or ('domain' in answers[cid] and answers[cid]['domain'] != request['domain'])):
                raise ValueError('Fresh data disagrees with its registered family/domain/split/omission allocation')
    planned_jobs('test', datasets['test'][0], .25, plan['diagnostic_case_ids'])
    return plan


def verify_isolated_caches(root, frozen_hash, *, initialize=False):
    scope = {'experiment': 'fresh120-v0.6.0', 'freeze_sha256': frozen_hash,
             'directories': list(CACHE_DIRECTORIES)}
    if any((root / 'runs' / name).is_symlink() for name in (*CACHE_DIRECTORIES, 'fresh_cache_scope.json')):
        raise ValueError('Fresh cache directories and scope marker cannot be symbolic links')
    marker = rooted(root, 'runs/fresh_cache_scope.json')
    paths = [rooted(root, 'runs/' + name) for name in CACHE_DIRECTORIES]
    for path in paths:
        if path.exists() and (not path.is_dir() or any(p.is_symlink() for p in path.rglob('*'))):
            raise ValueError('Fresh cache must be an independent local directory without symbolic links')
    if marker.exists():
        if load(marker) != scope:
            raise ValueError('Fresh cache belongs to another experiment or frozen version')
    elif any(path.exists() and any(path.iterdir()) for path in paths):
        raise ValueError('Fresh cache must start empty; unregistered cached responses cannot be adopted')
    if initialize and not marker.exists():
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
        dump(marker, scope)
    return scope


def pilot_gate(rows):
    expected = {(cid, policy) for cid in PILOT_IDS for policy in POLICIES[:2]}
    actual = [(row.get('case_id'), row.get('system_id')) for row in rows]
    if len(actual) != 24 or set(actual) != expected:
        raise ValueError('Pilot A gate requires all 24 distinct fixed cells')
    good = {(row['case_id'], row['system_id']) for row in rows
            if row.get('score', {}).get('status') == 'scored'
            and row['score'].get('format_failure') is False
            and type(row['score'].get('quality')) in (int, float)
            and math.isfinite(row['score']['quality']) and 0 <= row['score']['quality'] <= 1}
    passed = [cid for cid in PILOT_IDS if all((cid, policy) in good for policy in POLICIES[:2])]
    return {'passed': len(passed) >= 10, 'paired_scored_cases': len(passed), 'required_cases': 10,
            'total_cases': 12, 'passed_case_ids': passed,
            'rule': 'Both direct and exhaustive final outputs parse and score successfully; no minimum quality.'}


def stage_lambda(stage):
    return .25 if stage in ('pilot_a', 'pilot_b', 'design') else None


def verified_stage(root, stage, freeze_path, freeze, selected=None):
    requests, _, annotations = load_dataset(root, stage)
    selected = stage_lambda(stage) if stage != 'test' else selected
    jobs = planned_jobs(stage, requests, selected, freeze['diagnostic_case_ids'])
    frozen_hash = file_hash(freeze_path)
    plan_hash = digest({'freeze': frozen_hash, 'stage': stage, 'jobs': jobs})
    out = rooted(root, f'runs/formal_v0.6.0_{stage}')
    manifest = load(out / 'manifest.json')
    verify_manifest(manifest, stage, jobs, frozen_hash, plan_hash, freeze['diagnostic_case_ids'], freeze, selected)
    if manifest['status'] != 'completed':
        raise ValueError(f'{stage} must be completed before later stages')
    for reference in manifest['session_logs']:
        if not rooted(root, reference).is_file():
            raise ValueError('A completed stage session log is missing')
    rows = restore_rows(out, manifest, jobs, requests, annotations)
    if stage == 'pilot_a' and not pilot_gate(rows)['passed']:
        raise ValueError('Pilot A gate failed: fewer than 10 paired cases parse and score successfully')
    return rows


def verify_predecessors(root, stage, freeze_path, freeze):
    for previous in STAGES[:STAGES.index(stage)]:
        verified_stage(root, previous, freeze_path, freeze)


def completion_result(stage, status, out, rows, manifest):
    result = {'status': status, 'output': str(out), 'error': manifest.get('error')}
    if stage == 'pilot_a':
        gate = pilot_gate(rows)
        result['pilot_gate'] = gate
        if not gate['passed']:
            result['status'] = 'pilot_gate_failed'
        if manifest.get('pilot_gate') != gate:
            manifest['pilot_gate'] = gate
            dump(out / 'manifest.json', manifest)
    return result


def cell_metadata(job, stage, frozen_hash, annotations):
    cid, label, policy, lam, override = job
    return {'case_id': cid, 'system_id': label, 'underlying_policy': policy,
            'lambda_value': lam, 'importance_override': override, 'split': stage,
            'freeze_sha256': frozen_hash, 'family_id': annotations[cid]['metadata']['family_id'],
            'domain': annotations[cid]['domain']}


def verify_cell(t, job, stage, frozen_hash, annotations):
    if not isinstance(t, dict) or any(t.get(k) != v for k, v in
                                    cell_metadata(job, stage, frozen_hash, annotations).items()):
        raise ValueError('Saved cell belongs to another plan or frozen version')
    if type(t.get('question_items')) is not int or not 0 <= t['question_items'] <= 3:
        raise ValueError('Invalid question count in saved cell')


def commit_pending(out, manifest, rows, jobs, requests, annotations):
    """Score only the durable first trajectory; never redraw on scorer failure."""
    pending = manifest.get('pending_cell')
    if pending is None:
        return
    if (not isinstance(pending, dict) or set(pending) != {'trajectory', 'sha256'}
            or digest(pending['trajectory']) != pending['sha256']):
        raise ValueError('Invalid pending trajectory evidence')
    if len(rows) >= len(jobs):
        raise ValueError('Unexpected pending cell after the planned stage')
    raw = pending['trajectory']
    verify_cell(raw, jobs[len(rows)], manifest['stage'], manifest['freeze_sha256'], annotations)
    if 'score' in raw or 'record_sha256' in raw:
        raise ValueError('Pending cell must contain only the unscored first trajectory')
    cid = raw['case_id']
    score = score_output(requests[cid]['domain'], raw['output'], annotations[cid])
    if score['quality'] is None:
        append(out / 'scoring_errors.jsonl', {'case_id': cid, 'system_id': raw['system_id'],
               'trajectory_sha256': pending['sha256'], 'score': score,
               'timestamp_utc': datetime.now(timezone.utc).isoformat()})
        raise ValueError('Scoring error; first trajectory is saved and must not be resampled')
    t = dict(raw, score=score)
    t['record_sha256'] = digest(t)
    append(out / 'trajectories.jsonl', t)
    rows.append(t)
    manifest['pending_cell'] = None
    manifest['row_hashes'].append(t['record_sha256'])
    manifest['completed_trajectories'] = len(rows)
    manifest['trajectory_sha256'] = file_hash(out / 'trajectories.jsonl')
    dump(out / 'manifest.json', manifest)


def restore_rows(out, manifest, jobs, requests, annotations):
    """Check all anchors; recover only the append-before-manifest crash window."""
    path = out / 'trajectories.jsonl'
    content = path.read_bytes() if path.exists() else b''
    lines = content.splitlines(keepends=True)
    if any(not line.endswith(b'\n') or not line.strip() for line in lines):
        raise ValueError('Truncated or blank formal trajectory record')
    rows = [strict_json(line.decode('utf-8')) for line in lines]
    anchors = manifest.get('row_hashes')
    if (not isinstance(anchors, list) or len(anchors) > len(rows)
            or len(rows) > len(jobs) or len(rows) - len(anchors) > 1
            or manifest.get('completed_trajectories') != len(anchors)):
        raise ValueError('Manifest and trajectory counts disagree')
    prior_content = b''.join(lines[:len(anchors)])
    expected_file_hash = hashlib.sha256(prior_content).hexdigest() if anchors else None
    if manifest.get('trajectory_sha256') != expected_file_hash:
        raise ValueError('Persisted trajectory file hash changed')
    for index, (row, job) in enumerate(zip(rows, jobs)):
        verify_cell(row, job, manifest['stage'], manifest['freeze_sha256'], annotations)
        payload = {k: v for k, v in row.items() if k != 'record_sha256'}
        if row.get('record_sha256') != digest(payload):
            raise ValueError('Trajectory record hash changed')
        if index < len(anchors) and anchors[index] != row['record_sha256']:
            raise ValueError('Trajectory differs from its manifest anchor')
        cid = row['case_id']
        expected_score = score_output(requests[cid]['domain'], row['output'], annotations[cid])
        if expected_score['quality'] is None or row.get('score') != expected_score:
            raise ValueError('Persisted score does not reproduce under the frozen rubric')
    if len(rows) > len(anchors):
        pending = manifest.get('pending_cell')
        last_raw = {k: v for k, v in rows[-1].items() if k not in ('score', 'record_sha256')}
        if (not isinstance(pending, dict) or set(pending) != {'trajectory', 'sha256'}
                or pending['trajectory'] != last_raw or digest(last_raw) != pending['sha256']):
            raise ValueError('Unanchored appended cell has no matching saved first trajectory')
        if manifest['status'] == 'completed':
            raise ValueError('Completed stage has uncommitted rows')
        manifest['row_hashes'].append(rows[-1]['record_sha256'])
        manifest['completed_trajectories'] = len(rows)
        manifest['trajectory_sha256'] = file_hash(path)
        manifest['pending_cell'] = None
        append(out / 'cache_reuse.jsonl', {'event_type': 'recover_committed_cell',
                                          'case_id': rows[-1]['case_id'], 'variant': rows[-1]['system_id']})
        dump(out / 'manifest.json', manifest)
    if manifest['status'] == 'completed' and (len(rows) != len(jobs) or manifest.get('pending_cell') is not None):
        raise ValueError('Completed manifest does not have every planned trajectory')
    return rows


def verify_manifest(manifest, stage, jobs, frozen_hash, plan_hash, diagnostic, freeze, selected):
    expected = {'manifest_version': 2, 'stage': stage, 'plan_hash': plan_hash,
                'freeze_sha256': frozen_hash, 'planned_trajectories': len(jobs),
                'case_ids': list(dict.fromkeys(j[0] for j in jobs)),
                'diagnostic_case_ids': diagnostic if stage == 'test' else [],
                'selected_lambda': selected, 'source_files': freeze['files']}
    if not isinstance(manifest, dict) or any(manifest.get(k) != v for k, v in expected.items()):
        raise ValueError('Existing formal manifest belongs to another plan or version')
    sessions = manifest.get('session_logs')
    if (manifest.get('status') not in ('prepared', 'running', 'interrupted', 'completed')
            or not isinstance(sessions, list) or any(not isinstance(s, str) for s in sessions)
            or len(sessions) != len(set(sessions))):
        raise ValueError('Invalid or duplicate formal manifest records')


def save_selection(root, freeze_path, out, rows, requests):
    path = root / 'outputs/CoPrompt_validation_v0.6.0/lambda_selection.json'
    selection = select_lambda(rows, requests)
    selection.update(freeze_sha256=file_hash(freeze_path), validation_run=str(out.relative_to(root)),
                     validation_trajectories_sha256=file_hash(out / 'trajectories.jsonl'))
    if path.exists():
        existing = load(path)
        if not isinstance(existing, dict) or {k: v for k, v in existing.items() if k != 'selected_utc'} != selection:
            raise ValueError('Existing lambda selection disagrees with verified validation')
        return existing
    selection['selected_utc'] = datetime.now(timezone.utc).isoformat()
    dump(path, selection)
    return selection


def verified_selected_lambda(root, freeze_path, freeze):
    path = root / 'outputs/CoPrompt_validation_v0.6.0/lambda_selection.json'
    selection = load(path)
    if (not isinstance(selection, dict) or selection.get('freeze_sha256') != file_hash(freeze_path)
            or selection.get('validation_run') != 'runs/formal_v0.6.0_validation'):
        raise ValueError('Test requires a selection from this frozen validation')
    requests, _, annotations = load_dataset(root, 'validation')
    jobs = planned_jobs('validation', requests, None, freeze['diagnostic_case_ids'])
    plan_hash = digest({'freeze': file_hash(freeze_path), 'stage': 'validation', 'jobs': jobs})
    out = root / selection['validation_run']
    manifest = load(out / 'manifest.json')
    verify_manifest(manifest, 'validation', jobs, file_hash(freeze_path), plan_hash,
                    freeze['diagnostic_case_ids'], freeze, None)
    if manifest['status'] != 'completed':
        raise ValueError('Validation must be completed before test')
    rows = restore_rows(out, manifest, jobs, requests, annotations)
    if selection.get('validation_trajectories_sha256') != file_hash(out / 'trajectories.jsonl'):
        raise ValueError('Validation trajectories changed after selection')
    calculated = select_lambda(rows, requests)
    expected_keys = set(calculated) | {'freeze_sha256', 'validation_run', 'validation_trajectories_sha256', 'selected_utc'}
    if set(selection) != expected_keys or any(selection.get(k) != v for k, v in calculated.items()):
        raise ValueError('Saved selection does not reproduce the predefined rule')
    return calculated['selected_lambda']


def execute(stage, key, *, root=ROOT):
    root = Path(root).resolve()
    if stage not in STAGES:
        raise ValueError('Unknown fresh formal stage')
    freeze_path = rooted(root, 'data/formal_freeze_v0.6.0.json')
    freeze = load(freeze_path); verify_freeze(root, freeze)
    if not required_frozen_files().issubset(freeze['files']):
        raise ValueError('All fresh data, configuration and method/runtime sources must be frozen')
    verify_case_plan(root, freeze)
    verify_isolated_caches(root, file_hash(freeze_path))
    verify_predecessors(root, stage, freeze_path, freeze)
    selected = verified_selected_lambda(root, freeze_path, freeze) if stage == 'test' else stage_lambda(stage)
    requests, answers, annotations = load_dataset(root, stage)
    diagnostic = freeze['diagnostic_case_ids']
    # Validate the diagnostic subset even before validation begins.
    test_requests, _, _ = load_dataset(root, 'test')
    planned_jobs('test', test_requests, selected if selected is not None else .25, diagnostic)
    jobs = planned_jobs(stage, requests, selected, diagnostic)
    frozen_hash = file_hash(freeze_path)
    plan_hash = digest({'freeze': frozen_hash, 'stage': stage, 'jobs': jobs})
    out = rooted(root, f'runs/formal_v0.6.0_{stage}')
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'manifest.json'
    if manifest_path.exists():
        manifest = load(manifest_path)
        verify_manifest(manifest, stage, jobs, frozen_hash, plan_hash, diagnostic, freeze, selected)
    else:
        if (out / 'trajectories.jsonl').exists():
            raise ValueError('Orphan trajectory evidence cannot be silently adopted')
        manifest = {'manifest_version': 2, 'stage': stage, 'status': 'prepared', 'plan_hash': plan_hash,
                    'freeze_sha256': frozen_hash, 'started_utc': datetime.now(timezone.utc).isoformat(),
                    'planned_trajectories': len(jobs), 'completed_trajectories': 0,
                    'case_ids': list(requests), 'diagnostic_case_ids': diagnostic if stage == 'test' else [],
                    'selected_lambda': selected, 'source_files': freeze['files'], 'session_logs': [],
                    'row_hashes': [], 'trajectory_sha256': None, 'pending_cell': None,
                    'decision_reuse': 'first_raw_response_for_identical_public_messages_and_settings_including_malformed',
                    'partial_call_recovery': 'all_stages_first_successful_raw_response_including_malformed; transport_errors_not_cached',
                    'generation_reuse': 'first_complete_bounded_pipeline_for_identical_public_input',
                    'completion_order': 'case then fixed variant order; preserve first generated cell before scoring; never resample completed cells'}
        dump(manifest_path, manifest)
    for session_ref in manifest['session_logs']:
        if not rooted(root, session_ref).is_file():
            raise ValueError('A formal session log is missing')
    rows = restore_rows(out, manifest, jobs, requests, annotations)
    # A completed run with a missing selection is a recoverable post-run write,
    # and needs neither an API client nor remaining paid budget.
    if manifest['status'] == 'completed':
        if stage == 'validation': save_selection(root, freeze_path, out, rows, requests)
        return completion_result(stage, 'already_completed', out, rows, manifest)
    commit_pending(out, manifest, rows, jobs, requests, annotations)
    if len(rows) == len(jobs):
        manifest.update(status='completed', error=None, ended_utc=datetime.now(timezone.utc).isoformat())
        dump(manifest_path, manifest)
        if stage == 'validation': save_selection(root, freeze_path, out, rows, requests)
        return completion_result(stage, 'completed', out, rows, manifest)
    if (root.parents[1] / 'LOCALIZATION.json').is_file():
        raise ValueError('EN1 is a completed-study replay. New paid experiments require a new version and authorization.')
    config = load(root / 'config/openrouter.v0.6.formal.json')
    catalog = load(root / 'data/public/field_catalog.json')['domains']
    schemas = {d: load(root / f'data/schemas/output_{d}.schema.json') for d in catalog}
    error = None
    expected_manifest_hash = file_hash(manifest_path)
    with FreshBudgetLedger(CUMULATIVE_LEDGER, root) as ledger:
        if file_hash(manifest_path) != expected_manifest_hash:
            raise ValueError('Formal stage changed while acquiring the budget lock; reload before resuming')
        verify_freeze(root, freeze)
        verify_predecessors(root, stage, freeze_path, freeze)
        verify_registered_stage_sessions(root, ledger)
        verify_isolated_caches(root, frozen_hash, initialize=True)
        config = ledger.cap_config(config)
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        session = root / f'runs/formal_{stage}_{timestamp}_session.jsonl'
        ledger.register_session(session)
        manifest['session_logs'].append(str(session.relative_to(root)))
        manifest['status'] = 'running'; dump(manifest_path, manifest)
        def cache_log(event): append(out / 'cache_reuse.jsonl', event)
        try:
            rawclient = ReservedApiClient(config, key, ledger)
            client = DecisionReuseClient(rawclient, root / 'runs/formal_raw_response_cache', cache_log)
            runners = {}
            for job in jobs[len(rows):]:
                cid, label, policy, lam, override = job
                runner_key = (lam, override)
                if runner_key not in runners:
                    runners[runner_key] = PilotRunner(client, catalog, schemas, lambda_value=lam, budget=3,
                        importance_override=override, cache_dir=root / 'runs/extraction_cache',
                        generation_cache_dir=root / 'runs/generation_cache')
                client.variant = label; hits = client.hits; raw_hits = client.raw_hits
                t = runners[runner_key].run_trajectory(requests[cid], policy,
                                    lambda field: copy.deepcopy(answers[cid]['answers'][field]))
                t.update(cell_metadata(job, stage, frozen_hash, annotations))
                t['decision_cache_hits'] = client.hits - hits
                t['raw_response_cache_hits'] = client.raw_hits - raw_hits
                manifest['pending_cell'] = {'trajectory': t, 'sha256': digest(t)}
                dump(manifest_path, manifest)
                commit_pending(out, manifest, rows, jobs, requests, annotations)
                print(f"{cid} {label}: quality={rows[-1]['score']['quality']:.4f}, questions={t['question_items']}", flush=True)
        except (Exception, KeyboardInterrupt) as exc:
            error = {'type': type(exc).__name__, 'code': getattr(exc, 'code', None)}
        finally:
            complete = len(rows) == len(jobs) and not error
            manifest.update(status='completed' if complete else 'interrupted', completed_trajectories=len(rows),
                            error=error, ended_utc=datetime.now(timezone.utc).isoformat())
            dump(manifest_path, manifest)
            dump(out / 'summary.json', {'status': manifest['status'], 'statistics': summarize(rows),
                  'completed_trajectories': len(rows), 'planned_trajectories': len(jobs),
                  'cumulative_accounted_usd': float(ledger.spent), 'remaining_usd': float(ledger.authorized - ledger.spent)})
    if complete and stage == 'validation': save_selection(root, freeze_path, out, rows, requests)
    if complete:
        return completion_result(stage, 'completed', out, rows, manifest)
    return {'status': manifest['status'], 'output': str(out), 'error': error}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=[*STAGES, 'all'], required=True)
    parser.add_argument('--key-stdin', action='store_true')
    args = parser.parse_args()
    key = getpass.getpass('API key (hidden, not persisted): ') if args.key_stdin else os.environ.get('COPROMPT_API_KEY', '')
    if not key:
        parser.error('A session-only API key is required.')
    for stage in STAGES if args.stage == 'all' else (args.stage,):
        result = execute(stage, key)
        print(json.dumps(result, ensure_ascii=False))
        if result['status'] not in ('completed', 'already_completed'):
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
