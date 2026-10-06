"""Bounded normalized loader-event validator. No collector or execution authority.

The proposed events are fixtures until an independently authenticated live
collector produces them. Neither self-reported hashes nor a chain establish
file custody, syscall completeness or the origin of events.
"""
import hashlib
import json
from pathlib import PurePosixPath

MAX_RECORD = 8192
MAX_BYTES = 8 * 1024 ** 2
MAX_EVENTS = 4096
MAX_OBJECTS = 256
AUTHORITY = "71d0073faac7cd1a487e950f28a6f74b7daf75ab"
SOURCE_FREEZE_SHA256 = "b3703a81c37668b404badca02301a6a5930d39c149a5ff8c47029e09a1f08d10"
ZERO = "0" * 64
COMMON = {"sequence", "previous_sha256", "monotonic_ns", "process", "kind", "payload"}
IDENTITY = {"local_pid", "outer_pid", "starttime_ticks", "namespace_device", "namespace_inode"}


class Refusal(ValueError):
    pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def members(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise Refusal("exact record members required")


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise Refusal("bounded exact integer required")


def sha(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise Refusal("lowercase SHA256 required")


def identity(value):
    members(value, IDENTITY)
    for key in IDENTITY:
        integer(value[key], 1, 2 ** 64 - 1)


def path(value):
    if (type(value) is not str or value == "/" or not value.startswith("/") or "\0" in value
            or len(value.encode()) > 2048 or str(PurePosixPath(value)) != value
            or ".." in PurePosixPath(value).parts or value.startswith("//")):
        raise Refusal("canonical absolute object path required")


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise Refusal("duplicate JSON member")
        value[key] = item
    return value


def decode(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RECORD or not raw.endswith(b"\n"):
        raise Refusal("bounded complete raw event required")
    try:
        value = json.loads(raw, object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(Refusal("nonfinite JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Refusal("invalid event JSON") from exc
    try:
        same = canonical(value) == raw
    except (ValueError, TypeError, RecursionError) as exc:
        raise Refusal("invalid canonical event") from exc
    if not same:
        raise Refusal("canonical raw body required")
    return value


class LoaderLedger:
    """One proposed guarded process. No file reads, dispatch or native import.

    File pins are external expectations, not authentication. All observed object
    generations are retained even if no objects remain at the final snapshot.
    New namespaces, kernel pseudo-objects and symbol bindings require separate
    qualified support; this restricted component refuses them.
    """
    def __init__(self, process, executable, expected_files):
        identity(process)
        path(executable)
        if type(expected_files) is not dict or not 0 < len(expected_files) <= MAX_OBJECTS:
            raise Refusal("finite external file expectations required")
        for name, pin in expected_files.items():
            path(name)
            members(pin, {"bytes", "sha256"})
            integer(pin["bytes"], 1, 2 ** 40)
            sha(pin["sha256"])
        if executable not in expected_files:
            raise Refusal("executable expectation required")
        # Canonical copies prevent a caller from mutating expectations midstream.
        self.process = json.loads(canonical(process))
        self.expected = json.loads(canonical(expected_files))
        self.executable = executable
        self.previous = ZERO
        self.count = self.bytes = self.time = 0
        self.phase = "new"
        self.poisoned = False
        self.objects = {}
        self.live = set()
        self.main = None

    def consume(self, raw):
        if self.poisoned or self.phase == "ended":
            raise Refusal("failed or closed event stream cannot resume")
        # Refused/truncated input still consumes its attempted raw-byte charge.
        if type(raw) is not bytes:
            self.poisoned = True
            raise Refusal("raw bytes required")
        self.bytes += len(raw)
        try:
            if self.bytes > MAX_BYTES or self.count >= MAX_EVENTS:
                raise Refusal("aggregate event envelope exceeded")
            value = decode(raw)
            members(value, COMMON)
            integer(value["sequence"], 0, MAX_EVENTS - 1)
            integer(value["monotonic_ns"], 1, 2 ** 64 - 1)
            sha(value["previous_sha256"])
            identity(value["process"])
            if (value["sequence"] != self.count or value["previous_sha256"] != self.previous
                    or value["monotonic_ns"] < self.time
                    or canonical(value["process"]) != canonical(self.process)):
                raise Refusal("event sequence/hash/time/process identity drift")
            self._transition(value["kind"], value["payload"], value["monotonic_ns"])
            self.count += 1
            self.time = value["monotonic_ns"]
            self.previous = digest(raw)
        except Exception:
            self.poisoned = True
            raise

    def _transition(self, kind, payload, at):
        if kind == "handshake":
            members(payload, {"source_freeze_sha256", "loader_interface_version"})
            integer(payload["loader_interface_version"], 2, 2)
            if self.phase != "new" or payload["source_freeze_sha256"] != SOURCE_FREEZE_SHA256:
                raise Refusal("one exact source-bound handshake required")
            self.phase = "startup"
        elif kind == "object_open":
            if self.phase not in ("startup", "running"):
                raise Refusal("object outside loader lifetime")
            members(payload, {"object_id", "namespace_id", "loader_name", "resolved_path", "file_pin"})
            integer(payload["object_id"], 1, MAX_OBJECTS)
            integer(payload["namespace_id"], 0, 0)
            oid = payload["object_id"]
            if oid in self.objects or len(self.objects) >= MAX_OBJECTS:
                raise Refusal("object generation reused or cap exceeded")
            name = payload["loader_name"]
            if type(name) is not str:
                raise Refusal("loader name must be text")
            resolved = payload["resolved_path"]
            path(resolved)
            pin = payload["file_pin"]
            members(pin, {"bytes", "sha256"})
            integer(pin["bytes"], 1, 2 ** 40)
            sha(pin["sha256"])
            if resolved not in self.expected or canonical(pin) != canonical(self.expected[resolved]):
                raise Refusal("unlisted object or file expectation drift")
            if not name:
                if self.main is not None or self.phase != "startup" or resolved != self.executable:
                    raise Refusal("ambiguous empty main-executable loader name")
                self.main = oid
            elif name != resolved:
                # Relative spellings and symlinks need held descriptor attribution.
                raise Refusal("unqualified loader-name resolution")
            self.objects[oid] = {**json.loads(canonical(payload)), "opened_event": self.count,
                                 "closed_event": None, "opened_ns": at, "closed_ns": None}
            self.live.add(oid)
        elif kind == "preinit":
            members(payload, {"main_object_id"})
            integer(payload["main_object_id"], 1, MAX_OBJECTS)
            if self.phase != "startup" or self.main not in self.live or payload["main_object_id"] != self.main:
                raise Refusal("unique startup/main binding required")
            self.phase = "running"
        elif kind == "object_close":
            members(payload, {"object_id"})
            integer(payload["object_id"], 1, MAX_OBJECTS)
            oid = payload["object_id"]
            if self.phase != "running" or oid not in self.live:
                raise Refusal("unknown/double/early object close")
            self.live.remove(oid)
            self.objects[oid]["closed_event"] = self.count
            self.objects[oid]["closed_ns"] = at
        elif kind == "collector_end":
            members(payload, {"event_loss_count", "exit_code"})
            integer(payload["event_loss_count"], 0, 0)
            integer(payload["exit_code"], 0, 0)
            if self.phase != "running":
                raise Refusal("terminal event without complete startup")
            self.phase = "ended"
        else:
            raise Refusal("unsupported event kind")

    def finish(self):
        if self.poisoned or self.phase != "ended":
            raise Refusal("incomplete/failed stream cannot produce a receipt")
        receipt = {"schema": "radio-loader-lifetime-source-component-J-v1",
                "status": "STRUCTURAL_EVENT_CHECK_ONLY_NO_AUTHENTICATED_COLLECTION",
                "authority_commit": AUTHORITY, "source_freeze_sha256": SOURCE_FREEZE_SHA256,
                "events_checked": self.count, "raw_event_bytes_charged": self.bytes,
                "terminal_chain_sha256": self.previous, "process": self.process,
                "object_generations": [self.objects[oid] for oid in sorted(self.objects)],
                "live_at_terminal": sorted(self.live),
                "transient_generations_retained": sum(oid not in self.live for oid in self.objects),
                "collector_authentication": False, "continuous_file_custody": False,
                "full_syscall_or_loader_coverage": False, "descendant_or_terminal_io_qualification": False,
                "runtime_qualified": False, "codec_certificate_issued": False,
                "execution_authorized": False, "spectra_authorized": False}
        return json.loads(canonical(receipt))


def dispatch(*args, **kwargs):
    raise Refusal("source component has no collector or dispatch authority")
