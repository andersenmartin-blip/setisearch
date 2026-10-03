"""Bounded local engineering ledger and strict read-only original-journal replay.

This adapter qualifies no remote store, telescope permission, hostile concurrent
filesystem ownership, or whole-process resource lifetime.  The unchanged source
acquisition module remains the only supported creator of a process-local budget.
An existing reservation can be read as evidence, never restored as permission.
"""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import stat
import sys
import uuid
from urllib.parse import quote, urlsplit

FROZEN_SOURCE = Path(__file__).resolve().parent.parent / "frozen-project" / "src"
sys.path.insert(0, str(FROZEN_SOURCE))
from seti_repeater import acquisition_radio as acquisition

MAX_LEDGER_BYTES = 128 * 1024
MAX_DB_BYTES = 64 * 1024 * 1024
MAX_HISTORY_ROWS = 256
MAX_JOURNAL_BYTES = 2 * 1024 * 1024
MAX_JOURNAL_RECORD_BYTES = 16 * 1024
MAX_JOURNAL_RECORDS = 4096
STORE_POLICY = "local-engineering-sqlite-irrevocable-v1"
_META_SQL = "CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), store_id TEXT NOT NULL, policy TEXT NOT NULL)"
_HISTORY_SQL = "CREATE TABLE history (revision INTEGER PRIMARY KEY, ledger_sha256 TEXT NOT NULL, document BLOB NOT NULL)"


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _parse(payload):
    return json.loads(payload, object_pairs_hook=_object_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON number")))


def _encode(value):
    return acquisition.encode(value)


def _equal(left, right):
    # Canonical bytes preserve bool/int/float distinctions lost by Python ==.
    return _encode(left) == _encode(right)


def _sha(value, label):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(label + " must be a lowercase SHA256")


def _bounded_ledger(document):
    payload = _encode(document)
    if not payload or len(payload) > MAX_LEDGER_BYTES:
        raise ValueError("ledger exceeds bounded size")
    if type(document) is not dict or type(document.get("reservations")) is not list:
        raise ValueError("ledger object/list types changed")
    if len(document["reservations"]) >= MAX_HISTORY_ROWS:
        raise ValueError("ledger reservation history exceeds bound")
    acquisition.validate_ledger(document, acquisition.digest(document))
    # Original limits already reject bool/integer aliases for request/byte caps.
    # Enforce exact container/string types before SQLite publication as well.
    if type(document["total_limits"]) is not dict:
        raise ValueError("ledger limits object required")
    for item in document["reservations"]:
        if type(item) is not dict or type(item["reserved_limits"]) is not dict:
            raise ValueError("reservation object required")
        if type(item["session_id"]) is not str or type(item["created_utc"]) is not str:
            raise ValueError("reservation identity/time string required")
    return payload


def _append_only(previous, following):
    _bounded_ledger(previous)
    _bounded_ledger(following)
    old = previous["reservations"]
    new = following["reservations"]
    if len(new) != len(old) + 1 or not _equal(new[:-1], old):
        raise ValueError("exactly one permanent reservation must be appended")
    for key in ("policy", "contract_sha256", "source_inventory_sha256", "total_limits"):
        if not _equal(previous[key], following[key]):
            raise ValueError("ledger ancestry or cumulative limits changed")
    if new[-1]["prior_ledger_sha256"] != acquisition.digest(previous):
        raise ValueError("reservation parent differs")


def _sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _guard_regular(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        details = os.fstat(fd)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or not 0 < details.st_size <= maximum:
            raise ValueError("bounded regular sole-link file required")
        return (details.st_dev, details.st_ino)
    finally:
        os.close(fd)


def _connection(path, *, writing):
    identity = _guard_regular(path, MAX_DB_BYTES)
    uri = "file:" + quote(str(path), safe="/") + ("?mode=rw" if writing else "?mode=ro")
    db = sqlite3.connect(uri, uri=True, timeout=1, isolation_level=None)
    try:
        if _guard_regular(path, MAX_DB_BYTES) != identity:
            raise ValueError("database path identity changed during open")
        db.execute("PRAGMA busy_timeout=1000")
        if writing:
            if db.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
                raise ValueError("rollback journal mode differs")
            db.execute("PRAGMA synchronous=FULL")
            if db.execute("PRAGMA synchronous").fetchone() != (2,):
                raise ValueError("full synchronization unavailable")
        else:
            db.execute("PRAGMA query_only=ON")
        schema = db.execute("SELECT name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        if schema != [("history", _HISTORY_SQL), ("metadata", _META_SQL)]:
            raise ValueError("engineering database schema differs")
        return db
    except BaseException:
        db.close()
        raise


def _current(db, path):
    meta_sizes = db.execute("SELECT singleton,length(store_id),typeof(store_id),length(policy),typeof(policy) FROM metadata LIMIT 2").fetchall()
    if meta_sizes != [(1, 36, "text", len(STORE_POLICY), "text")]:
        raise ValueError("engineering metadata exceeds exact field bounds")
    meta = db.execute("SELECT singleton,store_id,policy FROM metadata").fetchall()
    if len(meta) != 1 or meta[0][0] != 1 or meta[0][2] != STORE_POLICY:
        raise ValueError("engineering metadata differs")
    store_id = meta[0][1]
    if type(store_id) is not str or str(uuid.UUID(store_id)) != store_id:
        raise ValueError("engineering store identity differs")
    history_sizes = db.execute("SELECT revision,length(ledger_sha256),typeof(ledger_sha256),length(document),typeof(document) FROM history ORDER BY revision LIMIT ?", (MAX_HISTORY_ROWS + 1,)).fetchall()
    if not history_sizes or len(history_sizes) > MAX_HISTORY_ROWS:
        raise ValueError("engineering history exceeds bound")
    for index, (revision, digest_length, digest_type, payload_length, payload_type) in enumerate(history_sizes):
        if (type(revision) is not int or revision != index or digest_length != 64 or digest_type != "text"
                or payload_type != "blob" or type(payload_length) is not int or not 0 < payload_length <= MAX_LEDGER_BYTES):
            raise ValueError("engineering history fields exceed exact bounds")
    history = db.execute("SELECT revision,ledger_sha256,document FROM history ORDER BY revision LIMIT ?", (MAX_HISTORY_ROWS + 1,)).fetchall()
    previous = None
    for index, (revision, expected, payload) in enumerate(history):
        if type(revision) is not int or revision != index or type(payload) is not bytes or len(payload) > MAX_LEDGER_BYTES:
            raise ValueError("engineering history revision/payload differs")
        document = _parse(payload)
        if _bounded_ledger(document) != payload:
            raise ValueError("engineering history is not canonical JSON")
        _sha(expected, "ledger digest")
        acquisition.validate_ledger(document, expected)
        if previous is None:
            if document["reservations"]:
                raise ValueError("engineering store must begin at fresh genesis")
        else:
            _append_only(previous, document)
        previous = document
    return acquisition.Checkpoint(previous, "engineering-sqlite:" + str(len(history)-1),
                                  {"kind": "local-engineering-sqlite", "path": str(path), "store_id": store_id})


class EngineeringSqliteStore:
    """Whole-ledger exact CAS; committed reservations never receive a refund."""
    def __init__(self, path):
        self.path = Path(path).absolute()

    @classmethod
    def create(cls, path, genesis_document):
        payload = _bounded_ledger(genesis_document)
        if genesis_document["reservations"]:
            raise ValueError("fresh engineering genesis required")
        store = cls(path)
        # Parent must already exist. Existing files, including failed creations,
        # are evidence and are never implicitly replaced or repaired.
        fd = os.open(store.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        _sync_directory(store.path.parent)
        db = sqlite3.connect(str(store.path), timeout=1, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("PRAGMA synchronous=FULL")
            if db.execute("PRAGMA synchronous").fetchone() != (2,):
                raise ValueError("full synchronization unavailable")
            db.execute("BEGIN IMMEDIATE")
            db.execute(_META_SQL)
            db.execute(_HISTORY_SQL)
            db.execute("INSERT INTO metadata VALUES (1,?,?)", (str(uuid.uuid4()), STORE_POLICY))
            db.execute("INSERT INTO history VALUES (0,?,?)", (acquisition.digest(genesis_document), payload))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        _sync_directory(store.path.parent)
        store.read()
        return store

    @classmethod
    def open(cls, path):
        store = cls(path)
        store.read()
        return store

    def read(self):
        db = _connection(self.path, writing=False)
        try:
            db.execute("BEGIN")
            return _current(db, self.path)
        finally:
            if db.in_transaction:
                db.execute("ROLLBACK")
            db.close()

    def publish(self, expected_revision, expected_sha256, document):
        payload = _bounded_ledger(document)
        _sha(expected_sha256, "expected ledger digest")
        if type(expected_revision) is not str:
            raise ValueError("exact revision string required")
        db = _connection(self.path, writing=True)
        try:
            db.execute("BEGIN IMMEDIATE")
            before = _current(db, self.path)
            if before.revision != expected_revision or before.sha256 != expected_sha256:
                raise ValueError("engineering reservation compare-and-swap refused")
            _append_only(before.document, document)
            next_revision = len(document["reservations"])
            db.execute("INSERT INTO history VALUES (?,?,?)", (next_revision, acquisition.digest(document), payload))
            db.execute("COMMIT")
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
        # Failure here deliberately reports uncertainty even though COMMIT may
        # already have charged the whole reservation. The caller must reread.
        _sync_directory(self.path.parent)
        _guard_regular(self.path, MAX_DB_BYTES)


def _scope(scope):
    if type(scope) is not dict or set(scope) != {"scan", "window", "url", "source_definition_sha256", "extraction"}:
        raise ValueError("exact engineering source scope required")
    for field in ("scan", "window"):
        if type(scope[field]) is not str or not 0 < len(scope[field]) <= 256:
            raise ValueError("source label/window string required")
    url = scope["url"]
    parsed = urlsplit(url) if type(url) is str and len(url) <= 2048 else None
    if parsed is None or parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".invalid") or parsed.username or parsed.password:
        raise ValueError("engineering source URL must use the synthetic .invalid domain")
    _sha(scope["source_definition_sha256"], "source definition")
    interval = scope["extraction"]
    if type(interval) is not list or len(interval) != 2 or any(type(x) is not int for x in interval) or not 0 <= interval[0] < interval[1]:
        raise ValueError("exact integer extraction interval required")
    if len(_encode(scope)) > MAX_JOURNAL_RECORD_BYTES // 2:
        raise ValueError("engineering scope exceeds bound")


def _read_journal_payload(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        details = os.fstat(fd)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or not 0 < details.st_size <= MAX_JOURNAL_BYTES:
            raise ValueError("bounded regular sole-link journal required")
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        chunks, count = [], 0
        while True:
            chunk = os.read(fd, min(65536, MAX_JOURNAL_BYTES + 1 - count))
            if not chunk:
                break
            count += len(chunk)
            if count > MAX_JOURNAL_BYTES:
                raise ValueError("journal exceeds bound")
            chunks.append(chunk)
        after = os.fstat(fd)
        if (details.st_size, details.st_mtime_ns, details.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("journal changed during replay")
        return b"".join(chunks)
    finally:
        os.close(fd)


def strict_read_journal(path, *, expected_checkpoint, expected_reservation, expected_head,
                        ordered_scopes, require_closed=True):
    """Replay bounded original bytes against independently supplied join pins.

    Accounting is evidence only: this function never creates a budget or grants
    request permission. Recorded elapsed samples bound recorded events; they do
    not certify the complete lifetime between records or remote durability.
    """
    if type(expected_checkpoint) is not acquisition.Checkpoint:
        raise ValueError("independent original Checkpoint required")
    _bounded_ledger(expected_checkpoint.document)
    _sha(expected_head, "independent journal head")
    if not expected_checkpoint.document["reservations"] or not _equal(expected_checkpoint.document["reservations"][-1], expected_reservation):
        raise ValueError("independent reservation/checkpoint join differs")
    location = expected_checkpoint.location
    if (expected_checkpoint.revision != "engineering-sqlite:" + str(len(expected_checkpoint.document["reservations"]))
            or type(location) is not dict or set(location) != {"kind", "path", "store_id"}
            or location["kind"] != "local-engineering-sqlite" or type(location["path"]) is not str
            or not Path(location["path"]).is_absolute() or type(location["store_id"]) is not str
            or str(uuid.UUID(location["store_id"])) != location["store_id"]):
        raise ValueError("engineering publication checkpoint required")
    if type(ordered_scopes) is not list or len(ordered_scopes) > 1000 or type(require_closed) is not bool:
        raise ValueError("bounded ordered scope inventory required")
    for scope in ordered_scopes:
        _scope(scope)
    cap = acquisition.limits(expected_reservation["reserved_limits"])
    payload = _read_journal_payload(path)
    if not payload.endswith(b"\n"):
        raise ValueError("missing or torn journal tail")
    lines = payload.splitlines()
    if payload != b"\n".join(lines) + b"\n":
        raise ValueError("original journal requires exact LF record separators")
    if len(lines) > MAX_JOURNAL_RECORDS:
        raise ValueError("journal record count exceeds bound")
    head, attempts, reserved, accepted = acquisition.ZERO, 0, 0, 0
    scope_count, last_size, last_accepted, ended = 0, None, False, False
    unaccepted_get_attempts = 0
    last_elapsed, outcome = 0, None
    events = []
    for index, line in enumerate(lines):
        if not line or len(line) > MAX_JOURNAL_RECORD_BYTES:
            raise ValueError("journal record exceeds bound")
        record = _parse(line)
        if type(record) is not dict or set(record) != {"index", "previous_sha256", "event", "sha256"}:
            raise ValueError("exact journal record fields required")
        if _encode(record) != line:
            raise ValueError("journal record is not original canonical JSON")
        stated = record.pop("sha256")
        _sha(stated, "record digest")
        if type(record["index"]) is not int or record["index"] != index or record["previous_sha256"] != head or acquisition.digest(record) != stated:
            raise ValueError("journal chain or exact index changed")
        head, event = stated, record["event"]
        if type(event) is not dict or type(event.get("type")) is not str:
            raise ValueError("exact event object required")
        if index == 0:
            start = {"type": "session_start", "reservation": expected_reservation,
                     "ledger_sha256": expected_checkpoint.sha256,
                     "publication_revision": expected_checkpoint.revision,
                     "publication_location": expected_checkpoint.location}
            if not _equal(event, start):
                raise ValueError("session start differs from independent publication checkpoint")
        elif ended:
            raise ValueError("journal continues after close")
        elif event["type"] == "scope":
            if set(event) != {"type", "scope"} or scope_count >= len(ordered_scopes) or not _equal(event["scope"], ordered_scopes[scope_count]):
                raise ValueError("ordered source scope differs")
            _scope(event["scope"])
            scope_count += 1
            if last_size is not None and last_size > 0 and not last_accepted:
                unaccepted_get_attempts += 1
            last_size, last_accepted = None, False
        elif event["type"] == "reserve":
            if set(event) != {"type", "attempt", "reserved_bytes", "elapsed_seconds"}:
                raise ValueError("exact reservation event fields required")
            size = event["reserved_bytes"]
            if scope_count == 0 or type(event["attempt"]) is not int or event["attempt"] != attempts+1 or type(size) is not int or size < 0:
                raise ValueError("invalid exact request reservation")
            if last_size is not None and last_size > 0 and not last_accepted:
                unaccepted_get_attempts += 1
            attempts += 1
            reserved += size
            last_size, last_accepted = size, False
        elif event["type"] == "accepted_body":
            if set(event) != {"type", "attempt", "bytes"}:
                raise ValueError("exact body event fields required")
            size = event["bytes"]
            if type(event["attempt"]) is not int or event["attempt"] != attempts or type(size) is not int or last_size is None or last_size == 0 or last_accepted or size != last_size-1:
                raise ValueError("accepted body differs from exact request reservation")
            accepted += size
            last_accepted = True
        elif event["type"] == "session_end":
            if set(event) != {"type", "outcome", "elapsed_seconds"} or event["outcome"] not in ("completed", "error", "interrupted"):
                raise ValueError("exact session end fields/outcome required")
            outcome, ended = event["outcome"], True
        else:
            raise ValueError("unknown journal event")
        if "elapsed_seconds" in event:
            elapsed = event["elapsed_seconds"]
            if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not last_elapsed <= elapsed <= cap["max_seconds"]:
                raise ValueError("recorded elapsed time is nonfinite, regressed or exceeds cap")
            last_elapsed = elapsed
        if attempts > cap["max_requests"] or reserved > cap["max_bytes"]:
            raise ValueError("journal accounting exceeds permanently charged reservation")
        events.append(event)
    if head != expected_head or (require_closed and not ended):
        raise ValueError("journal differs from retained closed final head")
    if last_size is not None and last_size > 0 and not last_accepted:
        unaccepted_get_attempts += 1
    if outcome == "completed" and (scope_count != len(ordered_scopes) or scope_count == 0 or attempts == 0 or accepted == 0):
        raise ValueError("completed journal did not visit the full ordered scope inventory")
    if outcome == "completed" and unaccepted_get_attempts:
        raise ValueError("completed engineering product contains an unaccepted GET reservation")
    return {"schema": "engineering-strict-session-replay-v1", "head_sha256": head,
            "ledger_sha256": expected_checkpoint.sha256, "publication_revision": expected_checkpoint.revision,
            "publication_location": expected_checkpoint.location,
            "reservation_sha256": acquisition.digest(expected_reservation),
            "session_id": expected_reservation["session_id"], "reserved_attempts": attempts,
            "reserved_bytes": reserved, "accepted_bytes": accepted, "scope_count": scope_count,
            "unaccepted_get_attempts": unaccepted_get_attempts,
            "closed": ended, "outcome": outcome, "last_recorded_elapsed_seconds": last_elapsed,
            "reservation_remains_fully_charged": True, "restored_request_permission": False,
            "hosted_or_scientific_qualification": False, "events": events}
