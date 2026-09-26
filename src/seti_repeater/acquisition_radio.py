"""Write-ahead session reservations and append-only radio request accounting.

A store must durably compare-and-swap a whole-session reservation before a
Budget can exist. Reservations are never refunded or resumed. A new process
obtains a new reservation, including after uncertain publication or a crash.
The store adapter is a trust boundary: read() must fetch the current durable
revision and publish() must enforce its expected revision and content digest.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import time
import uuid

from . import source_radio as source
from . import source_m43h as rows
from . import transport_radio as transport

POLICY = "radio-irrevocable-session-reservations-v1"
ZERO = "0"*64
LIMIT_KEYS = ("max_requests", "max_bytes", "max_seconds")
_NEW_SESSION_PERMIT = object()


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def limits(value):
    if set(value) != set(LIMIT_KEYS):
        raise ValueError("exact request/byte/time limits required")
    if (type(value["max_seconds"]) not in (int, float)
            or not math.isfinite(value["max_seconds"])):
        raise ValueError("finite positive time limit required")
    transport.Budget(**value)
    return dict(value)


def genesis(contract_sha256, source_inventory_sha256, total_limits):
    rows.core._frozen_sha256(contract_sha256, "source contract")
    rows.core._frozen_sha256(source_inventory_sha256, "source inventory")
    return {"policy": POLICY, "contract_sha256": contract_sha256,
            "source_inventory_sha256": source_inventory_sha256,
            "total_limits": limits(total_limits), "reservations": []}


def validate_ledger(document, expected_sha256):
    if digest(document) != expected_sha256:
        raise ValueError("reservation ledger differs from independent checkpoint")
    if set(document) != {"policy", "contract_sha256", "source_inventory_sha256", "total_limits", "reservations"}:
        raise ValueError("invalid reservation ledger schema")
    expected = genesis(document["contract_sha256"], document["source_inventory_sha256"], document["total_limits"])
    if document["policy"] != expected["policy"]:
        raise ValueError("reservation policy changed")
    charged = {k: 0 for k in LIMIT_KEYS}
    ids = set()
    for index, reservation in enumerate(document["reservations"]):
        if set(reservation) != {"ordinal", "session_id", "prior_ledger_sha256", "reserved_limits", "created_utc"}:
            raise ValueError("invalid reservation schema")
        if (reservation["ordinal"] != index or type(reservation["ordinal"]) is not int
                or reservation["prior_ledger_sha256"] != digest(expected)
                or reservation["session_id"] in ids
                or str(uuid.UUID(reservation["session_id"])) != reservation["session_id"]
                or not isinstance(reservation["created_utc"], str)):
            raise ValueError("reservation order, parent or identity changed")
        reserved = limits(reservation["reserved_limits"])
        for key in LIMIT_KEYS:
            charged[key] += reserved[key]
            if charged[key] > document["total_limits"][key]:
                raise ValueError("cumulative reservation budget exhausted")
        ids.add(reservation["session_id"])
        expected["reservations"].append(reservation)
    return {"charged_limits": charged,
            "remaining_limits": {k: document["total_limits"][k]-charged[k] for k in LIMIT_KEYS},
            "sessions": len(ids)}


@dataclass(frozen=True)
class Checkpoint:
    document: dict
    revision: str
    location: dict

    @property
    def sha256(self):
        return digest(self.document)


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class SessionJournal:
    """Exclusive, fsynced JSON-lines evidence; incomplete tails are never repaired."""
    def __init__(self, directory, start):
        self.directory = Path(directory)
        # Existing session paths are evidence, never an implicit fresh start.
        self.directory.mkdir(parents=True, exist_ok=False)
        self.path = self.directory/"attempts.jsonl"
        self.stream = self.path.open("xb", buffering=0)
        fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.head, self.count, self.broken = ZERO, 0, False
        _sync_directory(self.directory.parent)
        _sync_directory(self.directory)
        try:
            self.append({"type": "session_start", **start})
        except BaseException:
            self.stream.close()
            raise

    def append(self, event):
        if self.broken or self.stream.closed:
            raise ValueError("session journal unavailable")
        record = {"index": self.count, "previous_sha256": self.head, "event": event}
        record["sha256"] = digest(record)
        data = encode(record)+b"\n"
        try:
            written = self.stream.write(data)
            if written != len(data):
                raise OSError("short journal write")
            os.fsync(self.stream.fileno())
        except BaseException:
            self.broken = True
            raise
        self.head, self.count = record["sha256"], self.count+1

    def close(self):
        self.stream.close()


def read_journal(path, *, expected_head, expected_reservation):
    """Read-only replay from an independently supplied final head/lease receipt."""
    payload = Path(path).read_bytes()
    if not payload or not payload.endswith(b"\n"):
        raise ValueError("missing or torn journal tail")
    head, attempts, reserved, accepted, ended = ZERO, 0, 0, 0, False
    last_size, last_accepted, scope = None, False, None
    events = []
    for index, line in enumerate(payload.splitlines()):
        record = json.loads(line)
        if set(record) != {"index", "previous_sha256", "event", "sha256"}:
            raise ValueError("invalid journal record")
        stated = record.pop("sha256")
        if (type(record["index"]) is not int or record["index"] != index
                or record["previous_sha256"] != head or digest(record) != stated):
            raise ValueError("journal hash chain changed")
        head = stated
        event = record["event"]
        if index == 0:
            if event.get("type") != "session_start" or event.get("reservation") != expected_reservation:
                raise ValueError("journal reservation changed")
            cap = limits(expected_reservation["reserved_limits"])
        elif ended:
            raise ValueError("journal continues after close")
        elif event["type"] == "scope":
            scope = event["scope"]
        elif event["type"] == "reserve":
            size = event["reserved_bytes"]
            if scope is None or type(size) is not int or size < 0 or event["attempt"] != attempts+1:
                raise ValueError("invalid attempt reservation")
            attempts += 1
            reserved += size
            last_size, last_accepted = size, False
        elif event["type"] == "accepted_body":
            size = event["bytes"]
            if (last_size is None or last_size == 0 or last_accepted
                    or event["attempt"] != attempts or type(size) is not int or size != last_size-1):
                raise ValueError("accepted body differs from its reservation")
            accepted += size
            last_accepted = True
        elif event["type"] == "session_end":
            if event["outcome"] not in ("completed", "error", "interrupted"):
                raise ValueError("invalid session outcome")
            ended = True
        else:
            raise ValueError("unknown journal event")
        if index and (attempts > cap["max_requests"] or reserved > cap["max_bytes"]):
            raise ValueError("journal exceeds session reservation")
        events.append(event)
    if head != expected_head:
        raise ValueError("journal differs from independently retained head")
    return {"head_sha256": head, "reserved_attempts": attempts, "reserved_bytes": reserved,
            "accepted_bytes": accepted, "closed": ended, "events": events,
            "reservation_remains_fully_charged": True}


class DurableBudget:
    """Transport-compatible budget for one newly published, non-resumable lease."""
    def __init__(self, checkpoint, reservation, directory, *, clock=time.monotonic, _permit=None):
        if _permit is not _NEW_SESSION_PERMIT or checkpoint.document["reservations"][-1] != reservation:
            raise ValueError("only a newly published reservation can start a session")
        self.checkpoint = Checkpoint(json.loads(encode(checkpoint.document)), checkpoint.revision,
                                     json.loads(encode(checkpoint.location)))
        self.checkpoint_sha256 = checkpoint.sha256
        self.reservation = json.loads(encode(reservation))
        self._limits = limits(reservation["reserved_limits"])
        self.reservation_sha256 = digest(self.reservation)
        self.clock, self.started = clock, clock()
        self._attempts = self._reserved_bytes = self._accepted = 0
        self.last_size, self.last_accepted, self.scope = None, False, None
        self.closed = False
        self.journal = SessionJournal(directory, {"reservation": reservation,
            "ledger_sha256": checkpoint.sha256, "publication_revision": checkpoint.revision,
            "publication_location": checkpoint.location})

    def remaining_seconds(self):
        if self.closed or self.journal.broken:
            raise ValueError("acquisition session closed or journal failed")
        validate_ledger(self.checkpoint.document, self.checkpoint_sha256)
        if self.limits != self.reservation["reserved_limits"] or digest(self.reservation) != self.reservation_sha256:
            raise ValueError("session limits changed")
        elapsed = self.clock()-self.started
        remaining = self.max_seconds-elapsed
        if not math.isfinite(elapsed) or elapsed < 0 or remaining <= 0:
            raise ValueError("acquisition session time budget exhausted")
        return remaining

    def bind_scope(self, scope):
        self.remaining_seconds()
        self.journal.append({"type": "scope", "scope": scope})
        self.scope = json.loads(encode(scope))

    def reserve(self, size):
        self.remaining_seconds()
        if self.scope is None:
            raise ValueError("source scope must be recorded before any request")
        if (type(size) is not int or size < 0 or self.attempts >= self.max_requests
                or self.reserved_bytes+size > self.max_bytes):
            raise ValueError("acquisition session request/byte budget exhausted")
        self.journal.append({"type": "reserve", "attempt": self.attempts+1, "reserved_bytes": size,
                             "elapsed_seconds": self.clock()-self.started})
        self._attempts += 1
        self._reserved_bytes += size
        self.last_size, self.last_accepted = size, False

    @property
    def limits(self):
        return dict(self._limits)

    @property
    def max_requests(self):
        return self._limits["max_requests"]

    @property
    def max_bytes(self):
        return self._limits["max_bytes"]

    @property
    def max_seconds(self):
        return self._limits["max_seconds"]

    @property
    def attempts(self):
        return self._attempts

    @property
    def reserved_bytes(self):
        return self._reserved_bytes

    @property
    def accepted_bytes(self):
        return self._accepted

    @accepted_bytes.setter
    def accepted_bytes(self, value):
        size = value-self._accepted
        if (type(value) is not int or self.last_size is None or self.last_size == 0
                or self.last_accepted or size != self.last_size-1):
            raise ValueError("accepted body differs from its reservation")
        self.journal.append({"type": "accepted_body", "attempt": self.attempts, "bytes": size})
        self._accepted, self.last_accepted = value, True

    def close(self, outcome):
        if outcome not in ("completed", "error", "interrupted"):
            raise ValueError("invalid acquisition outcome")
        if self.closed:
            raise ValueError("session already closed")
        try:
            self.journal.append({"type": "session_end", "outcome": outcome,
                                 "elapsed_seconds": self.clock()-self.started})
        finally:
            self.closed = True
            self.journal.close()

    def record(self):
        return {"attempts": self.attempts, "reserved_bytes": self.reserved_bytes,
                "accepted_bytes": self.accepted_bytes, "elapsed_seconds": self.clock()-self.started,
                "limits": self.limits, "journal_head_sha256": self.journal.head,
                "session_id": self.reservation["session_id"], "ledger_sha256": self.checkpoint.sha256,
                "publication_revision": self.checkpoint.revision, "closed": self.closed,
                "cumulative": validate_ledger(self.checkpoint.document, self.checkpoint_sha256)}


def start_session(store, *, expected_revision, expected_ledger_sha256, session_limits, directory,
                  clock=time.monotonic):
    """Publish full quota, reread it, then create a fresh process-local budget.

    No supported API restores an old session's permission to make requests.
    Publication ambiguity, a read-back race or a local failure consumes the
    reservation if publication landed. Never refund automatically.
    """
    before = store.read()
    if before.revision != expected_revision:
        raise ValueError("reservation store revision changed")
    summary = validate_ledger(before.document, expected_ledger_sha256)
    requested = limits(session_limits)
    if any(requested[k] > summary["remaining_limits"][k] for k in LIMIT_KEYS):
        raise ValueError("cumulative reservation budget exhausted")
    document = json.loads(encode(before.document))
    reservation = {"ordinal": len(document["reservations"]), "session_id": str(uuid.uuid4()),
                   "prior_ledger_sha256": expected_ledger_sha256, "reserved_limits": requested,
                   "created_utc": datetime.now(timezone.utc).isoformat()}
    document["reservations"].append(reservation)
    validate_ledger(document, digest(document))
    store.publish(expected_revision, expected_ledger_sha256, document)
    after = store.read()
    if (after.revision == before.revision or after.sha256 != digest(document)
            or after.location != before.location):
        raise ValueError("reservation publication not confirmed; session remains closed")
    return DurableBudget(after, reservation, directory, clock=clock, _permit=_NEW_SESSION_PERMIT)


def start_source_session(root, contract_path, contract_sha256, store, *, expected_revision,
                         expected_ledger_sha256, directory, spectral_access_authorized=False):
    """Live entry point: all science gates before journal publication or networking."""
    if spectral_access_authorized is not True:
        raise ValueError("spectral access not authorized")
    cfg, readiness = source.load_contract(root, contract_path, contract_sha256)
    if readiness["blockers"]:
        raise ValueError("source contract blocked: "+"; ".join(readiness["blockers"]))
    path = "src/seti_repeater/acquisition_radio.py"
    if (cfg["pinned_files"].get(path) != rows.file_hash(__file__)
            or cfg.get("acquisition_policy") != POLICY or cfg["hdf5_runtime"] != source.runtime()):
        raise ValueError("durable acquisition code/policy/runtime not frozen")
    before = store.read()
    validate_ledger(before.document, expected_ledger_sha256)
    if (before.document["contract_sha256"] != contract_sha256
            or before.document["source_inventory_sha256"] != cfg["source_inventory_sha256"]
            or before.document["total_limits"] != cfg["cumulative_limits"]
            or before.location != cfg["reservation_store"] or before.location.get("kind") != "github"):
        raise ValueError("durable reservation store differs from source contract")
    return start_session(store, expected_revision=expected_revision, expected_ledger_sha256=expected_ledger_sha256,
                         session_limits=cfg["session_limits"], directory=directory)


def extract_source(root, contract_path, contract_sha256, scan_label, window_name,
                   directory, mirror_root, budget, *, spectral_access_authorized=False):
    if spectral_access_authorized is not True:
        raise ValueError("spectral access not authorized")
    if type(budget) is not DurableBudget:
        raise ValueError("durable budget required")
    cfg, readiness = source.load_contract(root, contract_path, contract_sha256)
    if readiness["blockers"]:
        raise ValueError("source contract blocked: "+"; ".join(readiness["blockers"]))
    if (budget.checkpoint.location != cfg["reservation_store"]
            or budget.checkpoint.location.get("kind") != "github"
            or budget.checkpoint.document["contract_sha256"] != contract_sha256
            or budget.checkpoint.document["source_inventory_sha256"] != cfg["source_inventory_sha256"]):
        raise ValueError("session is not bound to this telescope contract")
    budget.remaining_seconds()
    if (budget.checkpoint.document["total_limits"] != cfg["cumulative_limits"]
            or budget.limits != cfg["session_limits"] or cfg.get("acquisition_policy") != POLICY
            or cfg["pinned_files"].get("src/seti_repeater/acquisition_radio.py") != rows.file_hash(__file__)):
        raise ValueError("durable acquisition limits/policy/code binding differs")
    definition = next((s for s in cfg["scans"] if s["label"] == scan_label), None)
    window = next((w for w in cfg["windows"] if w["name"] == window_name), None)
    if definition is None or window is None:
        raise ValueError("unknown acquisition scope")
    budget.bind_scope({"scan": scan_label, "window": window_name, "url": definition["url"],
                      "source_definition_sha256": digest(definition), "extraction": window["archive_interval"]})
    return source.extract_remote(root, contract_path, contract_sha256, scan_label, window_name,
        directory, mirror_root, budget, spectral_access_authorized=spectral_access_authorized)
