"""Prospective GitHub rehearsal contract and LOCAL-ONLY attempt accounting.

This module has no connector, credential, live activation or telescope entry
point. A local fixture journal demonstrates write-ahead call accounting; it
does not establish a globally durable grant or a pre-decode transport limit.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
import time
import uuid

from .acquisition_radio import SessionJournal, ZERO, digest, encode

PHASES = ("initialization", "normal_append", "lost_reply_append",
          "readonly_recovery", "closure")
CAPS = {
    "initialization": (12, 4194304, 120),
    "normal_append": (44, 8388608, 300),
    "lost_reply_append": (44, 8388608, 300),
    "readonly_recovery": (40, 8388608, 300),
    "closure": (20, 4194304, 180),
}
LIMIT_KEYS = ("max_tool_calls", "max_response_utf8_bytes", "max_wall_seconds")
GATES = ("immutable_publication_readback", "separate_namespace_absence_at_expected_head",
         "irrevocable_remote_whole_phase_grants", "typed_connector_adapter_qualification",
         "transport_unknowns_explicitly_dispositioned", "durable_attempt_journal_integration",
         "readonly_recovery_protocol_qualification")
LOCATION = {"kind": "github", "repository": "andersenmartin-blip/setisearch",
            "branch": "m43-support-qualification",
            "path": "results_radio_github_v2_live_rehearsal_2026-09-27_01/model_ledger.json"}
NAMESPACE = "radio-github-v2-rehearsal-20260927-01"
MUTATIONS = ("create_tree", "create_commit", "update_ref")


def strict_json(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("non-finite JSON constant: " + value)
    return json.loads(payload, object_pairs_hook=pairs, parse_constant=invalid)


def sha(value, size=64):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{%d}" % size, value):
        raise ValueError("invalid independent identity")
    return value


def uuid4(value):
    if not isinstance(value, str):
        raise ValueError("UUID4 required")
    parsed = uuid.UUID(value)
    if parsed.version != 4 or str(parsed) != value:
        raise ValueError("canonical UUID4 required")
    return value


def positive_int(value):
    if type(value) is not int or value <= 0:
        raise ValueError("positive integer required (not bool)")
    return value


def validate_config(cfg):
    if (cfg["schema"] != "radio-github-v2-rehearsal-contract-config-v1"
            or cfg["namespace_id"] != NAMESPACE or cfg["location"] != LOCATION
            or cfg["phase_order"] != list(PHASES)
            or cfg["required_activation_evidence"] != list(GATES)
            or cfg["status"] != "PROSPECTIVE_PREPARATION_ONLY"
            or cfg["expiry_date"] != "2026-10-09"):
        raise ValueError("frozen preparation identity changed")
    for key in ("automatic_retry", "refund", "live_execution_authorized",
                "namespace_initialization_authorized", "telescope_access_authorized"):
        if cfg[key] is not False:
            raise ValueError("preparation grants no authority")
    if type(cfg["new_scientific_evaluations"]) is not int or cfg["new_scientific_evaluations"] != 0:
        raise ValueError("no scientific evaluations")
    if set(cfg["phase_limits"]) != set(PHASES):
        raise ValueError("phase namespace changed")
    for phase in PHASES:
        limits = cfg["phase_limits"][phase]
        if set(limits) != set(LIMIT_KEYS):
            raise ValueError("phase limit keys changed")
        for key, expected in zip(LIMIT_KEYS, CAPS[phase]):
            if positive_int(limits[key]) != expected:
                raise ValueError("phase limit changed")
    if set(cfg["total_limits"]) != set(LIMIT_KEYS):
        raise ValueError("total limit keys changed")
    for key in LIMIT_KEYS:
        if positive_int(cfg["total_limits"][key]) != sum(cfg["phase_limits"][p][key] for p in PHASES):
            raise ValueError("cumulative limits changed")
    for key, expected in (("max_single_reply_utf8_bytes", 2097152),
                          ("max_request_utf8_bytes", 262144),
                          ("max_journal_utf8_bytes", 8388608),
                          ("max_attempts_per_mutating_phase", 1)):
        if positive_int(cfg[key]) != expected:
            raise ValueError("fixed bound changed")
    sha(cfg["source_commit"], 40)
    for value in cfg["input_sha256"].values():
        sha(value)
    return deepcopy(cfg)


def prepare(cfg, telescope_genesis):
    """Produce inactive, domain-separated templates, never publish/initialize."""
    cfg = validate_config(cfg)
    contract_id = digest(cfg)
    model = deepcopy(telescope_genesis)
    if model["reservations"]:
        raise ValueError("only an empty reference shape may be used")
    # v2 payload SHAPE is exercised; neither identity names telescope resources.
    model["resource_contract_sha256"] = digest({"namespace": NAMESPACE,
        "contract": contract_id, "kind": "NO_SOURCE_RIGHTS_MODEL_RESOURCE"})
    model["source_inventory_sha256"] = digest({"namespace": NAMESPACE,
        "contract": contract_id, "kind": "NO_SOURCE_OBJECTS_MODEL_INVENTORY"})
    grants = {"schema": "radio-github-rehearsal-phase-grants-v1", "namespace_id": NAMESPACE,
        "contract_sha256": contract_id, "phase_order": list(PHASES),
        "total_limits": cfg["total_limits"], "grants": [], "closed": False,
        "telescope_access_authorized": False}
    return {"schema": "radio-github-rehearsal-preparation-v1", "contract_sha256": contract_id,
        "config": cfg, "model_genesis": model, "model_genesis_sha256": digest(model),
        "grant_genesis": grants, "grant_genesis_sha256": digest(grants),
        "activation_gates": {name: False for name in GATES},
        "live_execution_authorized": False, "telescope_access_authorized": False}


def activation_state(prepared, *, today):
    # Even booleans set by a caller cannot turn a preparation file into a permit.
    validate_config(prepared["config"])
    if prepared["contract_sha256"] != digest(prepared["config"]):
        raise ValueError("contract identity changed")
    if prepared["activation_gates"] != dict.fromkeys(GATES, False):
        raise ValueError("preparation cannot be rewritten to ready")
    if prepared["live_execution_authorized"] is not False or prepared["telescope_access_authorized"] is not False:
        raise ValueError("preparation cannot authorize execution")
    return {"status": "BLOCKED", "missing": list(GATES),
            "expired": today > date.fromisoformat(prepared["config"]["expiry_date"]),
            "live_execution_authorized": False, "telescope_access_authorized": False}


class AttemptStopped(RuntimeError):
    pass


def fixture_grant(cfg, phase, expected_head, expected_model_sha256, attempt_id=None):
    """An explicitly local fixture receipt; not a remote grant or source permit."""
    validate_config(cfg)
    if phase not in PHASES:
        raise ValueError("unknown phase")
    return {"schema": "radio-github-rehearsal-local-fixture-grant-v1",
        "authority": "LOCAL_FIXTURE_ONLY", "contract_sha256": digest(cfg),
        "namespace_id": NAMESPACE, "phase": phase,
        "attempt_id": uuid4(attempt_id or str(uuid.uuid4())),
        "expected_head": sha(expected_head, 40), "expected_model_sha256": sha(expected_model_sha256),
        "reserved_limits": deepcopy(cfg["phase_limits"][phase]),
        "telescope_access_authorized": False, "remote_grant_confirmed": False}


def validate_grant(cfg, grant):
    expected = fixture_grant(cfg, grant["phase"], grant["expected_head"],
                             grant["expected_model_sha256"], grant["attempt_id"])
    if grant != expected or encode(grant) != encode(expected):
        raise ValueError("fixture grant changed")


class FixtureAttemptJournal:
    """Single-process write-ahead boundary with read-only crash recovery.

    Existing contract/phase paths can never be reopened for dispatch. A fixture
    provider is trusted code, not a sandbox. No live connector is accepted.
    """
    def __init__(self, root, cfg, grant, provider, *, clock=time.monotonic):
        self.cfg = validate_config(cfg)
        validate_grant(cfg, grant)
        if getattr(provider, "kind", None) != "local-rehearsal-call-fixture":
            raise ValueError("local fixture provider required; no live adapter")
        self.grant = deepcopy(grant)
        self.provider, self.clock = provider, clock
        self.started = self.clock()
        self.last_elapsed = 0.0
        self._elapsed()
        self.calls, self.reserved_bytes, self.journal_bytes = 0, 0, 0
        self.mutations, self.stopped = [], False
        self.terminal_recorded = False
        directory = Path(root)/grant["contract_sha256"]/grant["phase"]
        directory.parent.mkdir(parents=True, exist_ok=True)
        self.journal = SessionJournal(directory, {"grant": grant, "policy": "never_resume_never_refund"})
        self.journal_bytes = self.journal.path.stat().st_size

    def _elapsed(self):
        elapsed = self.clock()-self.started
        if not math.isfinite(elapsed) or elapsed < self.last_elapsed:
            raise AttemptStopped("invalid monotonic clock")
        self.last_elapsed = elapsed
        return elapsed

    def _append(self, event):
        record = {"index": self.journal.count, "previous_sha256": self.journal.head, "event": event}
        record["sha256"] = digest(record)
        size = len(encode(record))+1
        if self.journal_bytes+size > self.cfg["max_journal_utf8_bytes"]:
            raise AttemptStopped("journal size exhausted")
        try:
            self.journal.append(event)
        except BaseException:
            self.journal.broken = True
            raise
        self.journal_bytes += size
        if (event["type"] in ("call_error", "session_stop", "session_end")
                or (event["type"] == "call_result" and event["accepted"] is False)):
            self.terminal_recorded = True

    def call(self, operation, request, *, reserve_reply_bytes):
        if self.stopped:
            raise AttemptStopped("attempt permanently stopped; no retry")
        try:
            positive_int(reserve_reply_bytes)
            payload = encode(request)
            if len(payload) > self.cfg["max_request_utf8_bytes"]:
                raise AttemptStopped("request size exceeded")
            if operation not in ("read", *MUTATIONS):
                raise AttemptStopped("unknown operation")
            if operation != "read":
                if self.grant["phase"] == "readonly_recovery":
                    raise AttemptStopped("recovery is read only")
                if len(self.mutations) >= 3 or operation != MUTATIONS[len(self.mutations)]:
                    raise AttemptStopped("one ordered mutation sequence only")
                if operation == "update_ref" and request.get("force") is not False:
                    raise AttemptStopped("explicit force=false required")
            cap = self.grant["reserved_limits"]
            elapsed = self._elapsed()
            if (reserve_reply_bytes > self.cfg["max_single_reply_utf8_bytes"]
                    or self.calls+1 > cap["max_tool_calls"]
                    or self.reserved_bytes+reserve_reply_bytes > cap["max_response_utf8_bytes"]
                    or elapsed >= cap["max_wall_seconds"]):
                raise AttemptStopped("phase allowance exhausted")
            call_id = str(uuid.uuid4())
            self._append({"type": "call_intent", "ordinal": self.calls,
                "call_id": call_id, "attempt_id": self.grant["attempt_id"],
                "operation": operation, "request": request, "request_sha256": digest(request),
                "reserved_reply_utf8_bytes": reserve_reply_bytes, "elapsed_seconds": elapsed})
            # Dispatch happens only AFTER the intent is fsynced. No refund.
            self.calls += 1
            self.reserved_bytes += reserve_reply_bytes
            if operation != "read":
                self.mutations.append(operation)
            try:
                reply = self.provider.dispatch(operation, request)
            except BaseException as error:
                self._append({"type": "call_error", "call_id": call_id,
                    "error_class": type(error).__name__, "elapsed_seconds": self._elapsed()})
                raise
            if type(reply) is not str:
                raise AttemptStopped("fixture must return exact tool-visible text")
            body = reply.encode("utf-8")
            elapsed = self._elapsed()
            accepted = len(body) <= reserve_reply_bytes and elapsed <= cap["max_wall_seconds"]
            self._append({"type": "call_result", "call_id": call_id,
                "response_utf8_bytes": len(body), "response_sha256": hashlib.sha256(body).hexdigest(),
                "elapsed_seconds": elapsed, "accepted": accepted})
            if not accepted:
                raise AttemptStopped("late or oversized response; allowance remains spent")
            return reply
        except BaseException as error:
            self.stopped = True
            # Preserve pre-dispatch vetoes too. A broken/full journal cannot be
            # repaired: if this append fails, retain the last confirmed prefix.
            if not self.terminal_recorded and not self.journal.broken:
                try:
                    self._append({"type": "session_stop", "error_class": type(error).__name__,
                        "reason": str(error)[:256], "elapsed_seconds": self.last_elapsed})
                except BaseException:
                    pass
            raise

    def close(self):
        if not self.stopped:
            try:
                self._append({"type": "session_end", "elapsed_seconds": self._elapsed()})
            finally:
                self.stopped = True
                self.journal.close()
        else:
            self.journal.close()


def replay(path, cfg, grant, *, expected_head):
    """Validate evidence only. Returns NO remaining dispatch rights after restart."""
    validate_config(cfg)
    validate_grant(cfg, grant)
    sha(expected_head)
    path = Path(path)
    if path.stat().st_size > cfg["max_journal_utf8_bytes"]:
        raise ValueError("journal exceeds size bound")
    payload = path.read_bytes()
    if not payload or not payload.endswith(b"\n"):
        raise ValueError("missing or torn journal tail")
    head, pending, calls, reserved, returned = ZERO, None, 0, 0, 0
    ended, failed, last_elapsed, stop_reason = False, False, 0.0, None
    ids, mutations = set(), []
    cap = grant["reserved_limits"]
    for index, line in enumerate(payload.splitlines()):
        record = strict_json(line)
        if set(record) != {"index", "previous_sha256", "event", "sha256"}:
            raise ValueError("journal record schema changed")
        stated = record.pop("sha256")
        if (type(record["index"]) is not int or record["index"] != index
                or record["previous_sha256"] != head or digest(record) != stated):
            raise ValueError("journal chain changed")
        head, event = stated, record["event"]
        if index == 0:
            if encode(event) != encode({"type": "session_start", "grant": grant, "policy": "never_resume_never_refund"}):
                raise ValueError("start/grant binding changed")
            continue
        if ended or failed:
            raise ValueError("journal continued after stop")
        elapsed = event["elapsed_seconds"]
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < last_elapsed:
            raise ValueError("elapsed time regressed")
        last_elapsed = elapsed
        if event["type"] == "call_intent":
            if set(event) != {"type", "ordinal", "call_id", "attempt_id", "operation", "request",
                              "request_sha256", "reserved_reply_utf8_bytes", "elapsed_seconds"}:
                raise ValueError("intent schema changed")
            ident = uuid4(event["call_id"])
            size = positive_int(event["reserved_reply_utf8_bytes"])
            op = event["operation"]
            if (pending is not None or ident in ids or type(event["ordinal"]) is not int
                    or event["ordinal"] != calls or event["attempt_id"] != grant["attempt_id"]
                    or digest(event["request"]) != event["request_sha256"]
                    or len(encode(event["request"])) > cfg["max_request_utf8_bytes"]
                    or op not in ("read", *MUTATIONS) or elapsed >= cap["max_wall_seconds"]):
                raise ValueError("intent binding/order changed")
            if op != "read":
                if (grant["phase"] == "readonly_recovery" or len(mutations) >= 3
                        or op != MUTATIONS[len(mutations)]
                        or (op == "update_ref" and event["request"].get("force") is not False)):
                    raise ValueError("mutation sequence changed")
                mutations.append(op)
            calls += 1
            reserved += size
            if (size > cfg["max_single_reply_utf8_bytes"] or calls > cap["max_tool_calls"]
                    or reserved > cap["max_response_utf8_bytes"]):
                raise ValueError("recorded allowance exceeded")
            pending = event
            ids.add(ident)
        elif event["type"] in ("call_result", "call_error"):
            if pending is None or event["call_id"] != pending["call_id"]:
                raise ValueError("reply without matching intent")
            if event["type"] == "call_error":
                if set(event) != {"type", "call_id", "error_class", "elapsed_seconds"} or not isinstance(event["error_class"], str):
                    raise ValueError("error schema changed")
                failed = True
            else:
                if set(event) != {"type", "call_id", "response_utf8_bytes", "response_sha256", "elapsed_seconds", "accepted"}:
                    raise ValueError("reply schema changed")
                size = event["response_utf8_bytes"]
                if type(size) is not int or size < 0:
                    raise ValueError("invalid response size")
                sha(event["response_sha256"])
                accepted = size <= pending["reserved_reply_utf8_bytes"] and elapsed <= cap["max_wall_seconds"]
                if event["accepted"] is not accepted:
                    raise ValueError("incorrect response acceptance")
                returned += size
                failed = not accepted
            pending = None
        elif event["type"] == "session_end":
            if set(event) != {"type", "elapsed_seconds"} or pending is not None:
                raise ValueError("invalid session end")
            ended = True
        elif event["type"] == "session_stop":
            if (set(event) != {"type", "error_class", "reason", "elapsed_seconds"}
                    or not isinstance(event["error_class"], str) or not isinstance(event["reason"], str)
                    or len(event["reason"]) > 256):
                raise ValueError("invalid stop record")
            failed, stop_reason = True, event["reason"]
        else:
            raise ValueError("unknown journal event")
    if head != expected_head:
        raise ValueError("journal differs from independent head checkpoint")
    return {"verified_head": head, "calls_intended": calls, "reserved_response_utf8_bytes": reserved,
        "returned_response_utf8_bytes": returned, "pending_call_id": pending["call_id"] if pending else None,
        "closed": ended, "failed": failed, "stop_reason": stop_reason, "full_phase_charged": deepcopy(cap),
        "remaining_dispatch_rights": 0, "replay_dispatches": 0,
        "global_durability_proven": False, "telescope_access_authorized": False}
