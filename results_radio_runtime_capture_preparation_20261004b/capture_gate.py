"""One-shot, separately pinned, metadata-only Linux child observer.

No invocation is authorized by importing this module.  The caller supplies the
already-published contract and detached immutable readback proof pins.  Those
external pins are trust inputs, never hashes manufactured by the collector.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time

SCHEMA = "radio-runtime-metadata-capture-supervisor-v1"
PROOF_SCHEMA = "radio-runtime-metadata-capture-publication-readback-v1"
MARKER_SCHEMA = "radio-runtime-metadata-capture-activation-v1"
AUTHORITY = dict.fromkeys((
    "acquisition_authorized", "allocation_created", "cas_qualified",
    "certificate_issued", "download_authorized", "execution_authorized",
    "hosted_transport_qualified", "installation_authorized",
    "reservation_authorized", "rng_authorized", "runtime_qualified",
    "scientific_execution_authorized", "source_contract_admitted",
    "spectral_access_authorized"), False)
CONTRACT_KEYS = {
    "schema", "capture_identity", "evidence_domain", "source_pins", "runtime_pins",
    "python_executable", "python_sha256", "collector_path", "collector_contract_path",
    "collector_contract_sha256", "plan_path", "plan_sha256", "output_root", "output_root_identity",
    "spent_path", "activation_path", "limits"}
LIMIT_KEYS = {"wall_seconds", "child_seconds", "reap_seconds", "artifact_bytes",
              "rss_bytes", "read_bytes", "stream_bytes", "sample_count"}
PIN_KEYS = {"path", "bytes", "sha256", "mode"}
PROOF_KEYS = {"schema", "repository", "branch", "prepared_commit", "prepared_tree",
              "activation_commit", "activation_tree", "activation_parent",
              "activation_changed_path", "contract_sha256", "publication_files",
              "activation_sha256", "capture_identity", "collector_contract_sha256", "plan_sha256", "provenance"}
MARKER_KEYS = {"schema", "capture_identity", "prepared_commit", "prepared_tree",
               "contract_sha256", "engineering_only", "single_use"}
GROUP_EVIDENCE_BYTES = 128 * 1024
GROUP_NEXT_RECORD_BYTES = 32 * 1024
PROC_SAMPLE_RESERVE_BYTES = 512 * 1024
TERMINAL_REPORT_RESERVE_BYTES = 512 * 1024
ARTIFACT_ACCOUNTING_SLACK_BYTES = 64 * 1024
COLLECTOR_SOURCE_BYTES = 64 * 1024
TERMINAL_PIDFD_READ_BYTES = 16385
PIN_EOF_READ_ALLOWANCE_BYTES = 1


class Refusal(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _hex(value, length=64):
    return type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value)


def _absolute(value):
    if type(value) is not str or not value.startswith("/") or str(Path(value)) != value:
        raise Refusal("noncanonical absolute path")
    if ".." in Path(value).parts or "\x00" in value:
        raise Refusal("unsafe path")
    return value


def _json(raw, expected):
    if type(raw) is not bytes or not _hex(expected) or digest(raw) != expected:
        raise Refusal("external raw pin mismatch")
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise Refusal("duplicate JSON field")
            obj[key] = value
        return obj
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(Refusal("nonfinite JSON")))
    except (UnicodeError, ValueError) as exc:
        raise Refusal("invalid pinned JSON") from exc


class Reads:
    def __init__(self, limit):
        self.limit = limit
        self.bytes = 0
        self.terminal_regular_reserved_bytes = 0
        self.terminal_pidfd_reserved_bytes = 0
        self.terminal_reservation = None

    def reserve_terminal(self, pin_bytes):
        regular = pin_bytes + PIN_EOF_READ_ALLOWANCE_BYTES
        if self.bytes + regular + TERMINAL_PIDFD_READ_BYTES > self.limit:
            raise Refusal("mandatory terminal read reservation cannot fit")
        self.terminal_regular_reserved_bytes = regular
        self.terminal_pidfd_reserved_bytes = TERMINAL_PIDFD_READ_BYTES
        self.terminal_reservation = {"pin_pass_reserved_bytes": pin_bytes,
            "pin_eof_syscall_allowance_bytes": PIN_EOF_READ_ALLOWANCE_BYTES,
            "terminal_pidfd_read_reserved_bytes": TERMINAL_PIDFD_READ_BYTES,
            "total_initial_floor_bytes": regular + TERMINAL_PIDFD_READ_BYTES,
            "phase": "optional-observations",
            "optional_proc_reads_cannot_consume_terminal_floor": True}

    def begin_terminal_pidfd(self):
        self.terminal_pidfd_reserved_bytes = 0
        if self.terminal_reservation is not None:
            self.terminal_reservation["phase"] = "terminal-pidfd"

    def begin_terminal_files(self):
        self.terminal_regular_reserved_bytes = 0
        self.terminal_pidfd_reserved_bytes = 0
        if self.terminal_reservation is not None:
            self.terminal_reservation["phase"] = "terminal-pins"

    def file(self, path, cap):
        path = _absolute(path)
        parts = Path(path).parts[1:]
        if len(parts) > 64:
            raise Refusal("finite path component cap")
        dirs = [os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)]
        bindings = []
        fd = None
        try:
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dirs[-1])
                item = os.fstat(child)
                bindings.append((dirs[-1], part, item.st_dev, item.st_ino))
                dirs.append(child)
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dirs[-1])
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > cap:
                raise Refusal("file type or finite read cap")
            if self.bytes + before.st_size > self.limit:
                raise Refusal("aggregate read cap")
            chunks = []
            remaining = cap + 1
            while remaining:
                allocation = (self.limit - self.bytes - self.terminal_regular_reserved_bytes
                              - self.terminal_pidfd_reserved_bytes)
                if allocation <= 0:
                    raise Refusal("aggregate read cap before syscall")
                chunk = os.read(fd, min(65536, remaining, allocation))
                if not chunk:
                    break
                self.bytes += len(chunk)
                if self.bytes > self.limit:
                    raise Refusal("aggregate read cap")
                chunks.append(chunk)
                remaining -= len(chunk)
                if before.st_size > 0 and sum(len(c) for c in chunks) == before.st_size:
                    break
            after = os.fstat(fd)
            named = os.stat(parts[-1], dir_fd=dirs[-1], follow_symlinks=False)
            for parent_fd, part, device, inode in bindings:
                observed = os.stat(part, dir_fd=parent_fd, follow_symlinks=False)
                if not stat.S_ISDIR(observed.st_mode) or (observed.st_dev, observed.st_ino) != (device, inode):
                    raise Refusal("ancestor namespace drift")
            raw = b"".join(chunks)
            if len(raw) > cap or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) or (named.st_dev, named.st_ino, named.st_mode, named.st_nlink) != (after.st_dev, after.st_ino, after.st_mode, 1):
                raise Refusal("file changed during read")
            return raw, before
        finally:
            if fd is not None:
                os.close(fd)
            for directory in reversed(dirs):
                os.close(directory)

    def proc(self, path, cap):
        # Kernel procfs records are ephemeral observations, not sealed files.
        parts = Path(_absolute(path)).parts
        if len(parts) != 4 or parts[1] != "proc" or not parts[2].isdigit() or parts[3] not in ("status", "stat"):
            raise Refusal("procfs path scope")
        directory = os.open("/proc/" + parts[2], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            return self.proc_at(directory, parts[3], cap)
        finally:
            os.close(directory)

    def proc_at(self, directory, leaf, cap):
        # Only held process/status/stat or held parent fdinfo records.  Every
        # returned byte (including an over-cap probe byte) is charged.
        if leaf not in ("status", "stat") and not (type(leaf) is str and leaf.isdecimal()):
            raise Refusal("held procfs leaf scope")
        if type(cap) is not int or not 0 < cap <= 16384:
            raise Refusal("finite held procfs cap")
        fd = None
        chunks = []
        began_read_bytes = self.bytes
        try:
            fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise Refusal("procfs regular observation required")
            remaining = cap + 1
            while remaining:
                allocation = (self.limit - self.bytes - self.terminal_regular_reserved_bytes
                              - self.terminal_pidfd_reserved_bytes)
                if allocation <= 0:
                    raise Refusal("aggregate procfs read cap before syscall")
                chunk = os.read(fd, min(65536, remaining, allocation))
                self.bytes += len(chunk)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > cap:
                raise Refusal("procfs finite observation cap")
            return raw
        except (Refusal, OSError) as exc:
            exc.proc_read_evidence = {"held_directory": _object_identity(os.fstat(directory)),
                                      "leaf": leaf, "cap": cap,
                                      "raw_received_base64": base64.b64encode(b"".join(chunks)).decode(),
                                      "charged_bytes": self.bytes - began_read_bytes,
                                      "error": type(exc).__name__ + ":" + str(exc)[:300]}
            raise
        finally:
            if fd is not None:
                os.close(fd)


def _pin_file(pin, reads, *, verified_objects=None, verified_contents=None):
    if type(pin) is not dict or set(pin) != PIN_KEYS or type(pin["bytes"]) is not int or pin["bytes"] < 0 or not _hex(pin["sha256"]):
        raise Refusal("invalid pin")
    if type(pin["mode"]) is not str or len(pin["mode"]) != 4 or any(c not in "01234567" for c in pin["mode"]):
        raise Refusal("invalid mode pin")
    raw, observed = reads.file(pin["path"], pin["bytes"])
    result = {"path": pin["path"], "bytes": len(raw), "sha256": digest(raw), "mode": format(observed.st_mode & 0o7777, "04o")}
    if result != pin:
        raise Refusal("selected source/runtime pin changed")
    if verified_objects is not None:
        # Same stat that belongs to the held, hash-verified read; never a fresh
        # named lookup after admission. Prevents unverified inode substitution.
        verified_objects[pin["path"]] = _object_identity(observed)
    if verified_contents is not None and pin["path"] in verified_contents:
        verified_contents[pin["path"]] = raw
    return result


def validate_contract(raw, expected):
    obj = _json(raw, expected)
    if type(obj) is not dict or set(obj) != CONTRACT_KEYS or obj["schema"] != SCHEMA:
        raise Refusal("supervisor exact schema")
    if obj["evidence_domain"] not in ("metadata-capture-only", "synthetic-test-fixture") or not _hex(obj["capture_identity"]):
        raise Refusal("domain or fresh identity")
    for field in ("python_sha256", "collector_contract_sha256", "plan_sha256"):
        if not _hex(obj[field]):
            raise Refusal("raw hash law")
    for field in ("python_executable", "collector_path", "collector_contract_path", "plan_path", "output_root", "spent_path", "activation_path"):
        _absolute(obj[field])
    root = Path(obj["output_root"])
    identity = obj["output_root_identity"]
    if type(identity) is not dict or set(identity) != {"device", "inode", "mode"} or type(identity["device"]) is not int or type(identity["inode"]) is not int or identity["mode"] != "0700":
        raise Refusal("externally pinned artifact directory identity")
    if Path(obj["spent_path"]).parent != root or Path(obj["activation_path"]) == Path(obj["spent_path"]):
        raise Refusal("spent path scope")
    if Path(obj["spent_path"]).name in {"selected-runtime-before.json", "selected-runtime-after.json", "child.stdout.raw", "child.stderr.raw", "procfs-samples.json", "supervisor-result.json", "admission-witness.json"}:
        raise Refusal("spent path collides with fixed artifact member")
    if type(obj["limits"]) is not dict or set(obj["limits"]) != LIMIT_KEYS:
        raise Refusal("finite limit schema")
    limits = obj["limits"]
    if any(type(v) is not int or v <= 0 for v in limits.values()):
        raise Refusal("finite positive integer limits")
    ceilings = {"wall_seconds": 60, "child_seconds": 50, "reap_seconds": 5,
                "artifact_bytes": 8 * 1024**2, "rss_bytes": 512 * 1024**2,
                "read_bytes": 256 * 1024**2, "stream_bytes": 1024**2,
                "sample_count": 1200}
    if any(limits[k] > ceilings[k] for k in limits) or limits["child_seconds"] + limits["reap_seconds"] + 2 > limits["wall_seconds"]:
        raise Refusal("bounded engineering ceiling")
    if limits["stream_bytes"] * 2 + 65536 > limits["artifact_bytes"]:
        raise Refusal("insufficient stream/report envelope")
    pins = obj["source_pins"] + obj["runtime_pins"] if type(obj["source_pins"]) is list and type(obj["runtime_pins"]) is list else None
    if not pins or len(pins) > 1024 or any(type(p) is not dict or set(p) != PIN_KEYS for p in pins):
        raise Refusal("explicit selected file inventory")
    paths = [p["path"] for p in pins]
    if len(set(paths)) != len(paths) or paths != sorted(paths[:len(obj["source_pins"])]) + sorted(paths[len(obj["source_pins"]):]):
        raise Refusal("pin inventory order or duplicates")
    selected = {p["path"]: p for p in pins}
    required = {str(Path(__file__).resolve()), obj["collector_path"], obj["collector_contract_path"], obj["plan_path"], obj["python_executable"]}
    if not required.issubset(selected) or selected[obj["python_executable"]]["sha256"] != obj["python_sha256"]:
        raise Refusal("parent/child executable/contract source pin absent")
    if selected[obj["collector_contract_path"]]["sha256"] != obj["collector_contract_sha256"] or selected[obj["plan_path"]]["sha256"] != obj["plan_sha256"]:
        raise Refusal("child contract or plan pin mismatch")
    for p in pins:
        if p["path"] in required - {obj["python_executable"]} and p not in obj["source_pins"]:
            raise Refusal("source classified as runtime")
    return obj


def verify_publication(contract, contract_sha256, proof_raw, proof_sha256, marker_raw, marker_sha256):
    proof = _json(proof_raw, proof_sha256)
    marker = _json(marker_raw, marker_sha256)
    if type(proof) is not dict or set(proof) != PROOF_KEYS or proof["schema"] != PROOF_SCHEMA:
        raise Refusal("detached publication exact schema")
    if proof["repository"] != "andersenmartin-blip/setisearch" or proof["branch"] != "m43-support-qualification":
        raise Refusal("publication scope")
    for k in ("prepared_commit", "prepared_tree", "activation_commit", "activation_tree", "activation_parent"):
        if not _hex(proof[k], 40):
            raise Refusal("publication Git identity")
    if proof["activation_parent"] != proof["prepared_commit"] or proof["activation_commit"] == proof["prepared_commit"] or proof["activation_tree"] == proof["prepared_tree"]:
        raise Refusal("fresh marker-only activation parent")
    if proof["activation_changed_path"] != "config/radio_runtime_metadata_capture_20261004b.activate.json" or proof["contract_sha256"] != contract_sha256 or proof["activation_sha256"] != marker_sha256:
        raise Refusal("frozen activation path or contract")
    if proof["capture_identity"] != contract["capture_identity"] or proof["collector_contract_sha256"] != contract["collector_contract_sha256"] or proof["plan_sha256"] != contract["plan_sha256"]:
        raise Refusal("child detached witness identity bindings")
    if type(proof["provenance"]) is not str or not proof["provenance"] or len(proof["provenance"]) > 2048:
        raise Refusal("external readback provenance required")
    if type(marker) is not dict or set(marker) != MARKER_KEYS or marker["schema"] != MARKER_SCHEMA:
        raise Refusal("activation marker schema")
    expected_marker = {"schema": MARKER_SCHEMA, "capture_identity": contract["capture_identity"],
                       "prepared_commit": proof["prepared_commit"], "prepared_tree": proof["prepared_tree"],
                       "contract_sha256": contract_sha256, "engineering_only": True, "single_use": True}
    if marker != expected_marker:
        raise Refusal("activation immutable bindings")
    files = proof["publication_files"]
    if type(files) is not list or len(files) != len(contract["source_pins"]):
        raise Refusal("complete source fullcontent readback")
    for observed, pin in zip(files, contract["source_pins"]):
        if type(observed) is not dict or set(observed) != PIN_KEYS | {"content_base64", "git_blob", "repository_path"}:
            raise Refusal("publication fullcontent row")
        if {k: observed[k] for k in PIN_KEYS} != pin or not _hex(observed["git_blob"], 40):
            raise Refusal("publication pin row mismatch")
        rp = observed["repository_path"]
        if type(rp) is not str or rp.startswith("/") or ".." in Path(rp).parts or "\\" in rp:
            raise Refusal("publication repository path")
        try:
            contents = base64.b64decode(observed["content_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise Refusal("fullcontent base64") from exc
        if len(contents) != pin["bytes"] or digest(contents) != pin["sha256"] or hashlib.sha1(b"blob " + str(len(contents)).encode() + b"\0" + contents).hexdigest() != observed["git_blob"]:
            raise Refusal("publication exact bytes mismatch")
    return proof


def _write_new(path, raw, root_fd=None, mode=0o600, *, artifact_limit=None, spent_basename=None):
    if artifact_limit is not None:
        if root_fd is None or spent_basename is None:
            raise Refusal("artifact write guard requires held scope")
        scope = _scope_inventory(None, spent_basename, root_fd)
        if max(scope["logical_bytes"], scope["allocated_bytes"]) + len(raw) + ARTIFACT_ACCOUNTING_SLACK_BYTES > artifact_limit:
            raise Refusal("artifact prospective write envelope exceeded")
    name = Path(path).name if root_fd is not None else path
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode, dir_fd=root_fd)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.dup(root_fd) if root_fd is not None else os.open(str(Path(path).parent), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    if artifact_limit is not None:
        scope = _scope_inventory(None, spent_basename, root_fd)
        if max(scope["logical_bytes"], scope["allocated_bytes"]) > artifact_limit:
            raise Refusal("artifact actual write accounting exceeded")


def _artifact_reservation(proof_raw, before, spent, limits):
    # A two-pass pin inventory is identical or a small null failure value.
    # Reserve both full streams including each actually received probe byte.
    inventory_bytes = max(len(canonical(before)), len(canonical(None)))
    fixed = (len(proof_raw) + 2 * inventory_bytes + len(canonical(spent))
             + 2 * (limits["stream_bytes"] + 1) + TERMINAL_REPORT_RESERVE_BYTES
             + ARTIFACT_ACCOUNTING_SLACK_BYTES + 16)
    sample_bytes = limits["artifact_bytes"] - fixed
    if len(canonical([])) + PROC_SAMPLE_RESERVE_BYTES + 16 > sample_bytes:
        raise Refusal("artifact first-sample/report reservation cannot fit")
    return {"fixed_reserved_bytes": fixed, "samples_reserved_bytes": sample_bytes,
            "next_sample_reserved_bytes": PROC_SAMPLE_RESERVE_BYTES,
            "terminal_report_reserved_bytes": TERMINAL_REPORT_RESERVE_BYTES,
            "filesystem_accounting_slack_bytes": ARTIFACT_ACCOUNTING_SLACK_BYTES,
            "full_stream_reservations_include_probe_bytes": True}


def _sample_room(samples, reservation):
    # A new list member adds its delimiters in addition to the standalone JSON.
    if len(canonical(samples)) + PROC_SAMPLE_RESERVE_BYTES + 16 > reservation["samples_reserved_bytes"]:
        raise Refusal("artifact next-sample reservation cannot fit")


def _collector_bootstrap(raw, path, expected_sha256):
    # Frozen bytes already passed the parent's held read, exact size and SHA.
    # No pathname reread selects dispatch source. Original __file__/argv bind
    # collector helper paths and CLI inputs; the bounded bootstrap is itself
    # part of this gate's externally published source hash.
    if type(raw) is not bytes or len(raw) > COLLECTOR_SOURCE_BYTES or digest(raw) != expected_sha256:
        raise Refusal("frozen collector byte dispatch pin or finite source cap")
    encoded = base64.b64encode(raw).decode("ascii")
    bootstrap = ("import base64,hashlib,sys\n"
                 "_raw=base64.b64decode(" + repr(encoded) + ",validate=True)\n"
                 "if hashlib.sha256(_raw).hexdigest()!=" + repr(expected_sha256) + ":raise RuntimeError('frozen collector bytes mismatch')\n"
                 "sys.argv[0]=" + repr(path) + "\n"
                 "globals().update({'__name__':'__main__','__file__':" + repr(path) + ", '__package__':None,'__cached__':None,'__spec__':None,'__loader__':None})\n"
                 "exec(compile(_raw," + repr(path) + ",'exec'),globals())\n")
    if len(bootstrap.encode("utf-8")) >= 131072:
        raise Refusal("finite collector bootstrap argument cap")
    return bootstrap


def _scope_inventory(root, spent_basename, root_fd):
    entries = []
    logical = allocated = 0
    names = os.listdir(root_fd)
    allowed = {spent_basename, "selected-runtime-before.json", "selected-runtime-after.json",
               "child.stdout.raw", "child.stderr.raw", "procfs-samples.json", "supervisor-result.json", "admission-witness.json"}
    if len(names) > len(allowed) or any(p not in allowed for p in names):
        raise Refusal("undeclared artifact member")
    for name in sorted(names):
        item = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
            raise Refusal("artifact must be sole-link regular file")
        logical += item.st_size
        allocated += item.st_blocks * 512
        entries.append({"path": name, "mode": format(item.st_mode & 0o7777, "04o"), "bytes": item.st_size, "allocated_bytes": item.st_blocks * 512, "kind": "file"})
    item = os.fstat(root_fd)
    logical += item.st_size
    allocated += item.st_blocks * 512
    return {"entries": entries, "logical_bytes": logical, "allocated_bytes": allocated,
            "root_directory_bytes": item.st_size, "root_directory_allocated_bytes": item.st_blocks * 512}


def _root_matches(root, root_fd, expected):
    held = os.fstat(root_fd)
    named = os.stat(root, follow_symlinks=False)
    actual = {"device": held.st_dev, "inode": held.st_ino, "mode": format(held.st_mode & 0o7777, "04o")}
    if actual != expected or not stat.S_ISDIR(named.st_mode) or (named.st_dev, named.st_ino) != (held.st_dev, held.st_ino):
        raise Refusal("artifact root held/named identity drift")


def _fields(raw):
    try:
        lines = raw.decode("ascii", "strict").splitlines()
    except UnicodeError as exc:
        raise Refusal("non-ASCII kernel observation") from exc
    result = {}
    for line in lines:
        if ":" not in line:
            raise Refusal("malformed kernel field")
        key, value = line.split(":", 1)
        if key in result:
            raise Refusal("duplicate kernel observation field")
        result[key] = value.split()
    return result


def _numbers(fields, key, count=None, positive=True):
    values = fields.get(key)
    if not values or len(values) > 32 or (count is not None and len(values) != count):
        raise Refusal("missing or multiple kernel identity field:" + key)
    if any(len(v) > 20 or not v.isdecimal() or (positive and int(v) <= 0) for v in values):
        raise Refusal("nonpositive kernel identity field:" + key)
    return [int(v) for v in values]


def _stat_identity(raw):
    # comm may contain spaces and parentheses; its final ')' closes field 2.
    try:
        left, close = raw.index(b" ("), raw.rindex(b")")
        if left > 20:
            raise ValueError("finite stat PID integer")
        pid = int(raw[:left])
        fields = raw[close + 2:].split()
        if len(fields) < 20 or len(fields[0]) != 1 or raw[close + 1:close + 2] != b" ":
            raise ValueError("stat fields")
        if any(len(fields[index]) > 20 for index in (1, 2, 3, 17, 19)):
            raise ValueError("finite stat identity integers")
        values = {"pid": pid, "state": fields[0].decode("ascii"),
                  "ppid": int(fields[1]), "pgrp": int(fields[2]),
                  "session": int(fields[3]), "threads": int(fields[17]),
                  "starttime": int(fields[19])}
        if min(values[k] for k in ("pid", "starttime", "threads")) <= 0:
            raise ValueError("stat positivity")
        return values
    except (ValueError, UnicodeError, IndexError) as exc:
        raise Refusal("malformed kernel stat identity") from exc


def _fdinfo_identity(raw):
    fields = _fields(raw)
    pid = _numbers(fields, "Pid", 1)[0]
    nspid = _numbers(fields, "NSpid")
    if nspid[0] != pid:
        raise Refusal("pidfd proc-visible identity mismatch")
    return {"pid": pid, "nspid": nspid}


def _candidate_identity(status_raw, stat_raw, fdinfo, parent, child_pid,
                        namespace, executable, expected_executable, previous=None):
    """Pure check: numeric tails alone never supply an identity authority."""
    fields = _fields(status_raw)
    item = _stat_identity(stat_raw)
    pid = fdinfo["pid"]
    nspid = _numbers(fields, "NSpid")
    if (_numbers(fields, "Pid", 1) != [pid] or _numbers(fields, "Tgid", 1) != [pid]
            or nspid != fdinfo["nspid"] or nspid[0] != pid
            or len(nspid) != len(parent["nspid"]) or nspid[-1] != child_pid):
        raise Refusal("pidfd/status/local namespace mismatch")
    if namespace != parent["namespace"]:
        raise Refusal("child PID namespace differs from held parent namespace")
    if _numbers(fields, "PPid", 1) != [parent["pid"]] or item["ppid"] != parent["pid"]:
        raise Refusal("kernel child parent mismatch")
    if (item["pid"] != pid or item["pgrp"] != pid or item["session"] != pid
            or _numbers(fields, "NSpgid") != nspid or _numbers(fields, "NSsid") != nspid):
        raise Refusal("child new-session/process-group mismatch")
    if item["threads"] != 1 or _numbers(fields, "Threads", 1) != [1]:
        raise Refusal("selected single-thread child identity required")
    if item["state"] == "Z":
        raise Refusal("child terminated before authentic live sample")
    if item["starttime"] < parent["starttime"]:
        raise Refusal("child start predates own parent")
    if executable != expected_executable:
        raise Refusal("child executable differs from pinned interpreter inode")
    result = {"pid": pid, "nspid": nspid, "ppid": item["ppid"],
              "pgrp": item["pgrp"], "session": item["session"], "starttime": item["starttime"],
              "namespace": namespace, "executable": executable}
    if previous is not None and result != previous:
        raise Refusal("held child identity drift or PID reuse")
    return result


def _object_identity(value):
    return {"device": value.st_dev, "inode": value.st_ino}


def _group_observations(proc_root_fd, group_pid, reads, deadline, *, retained=None):
    # A bounded visible snapshot, never an all-descendant/aggregate absence law.
    names = []
    members, records, unavailable = [], [], []
    snapshot = {"observed_process_group_members": members,
                "visible_process_ids": names, "visible_process_stat_records": records,
                "unavailable_process_records": unavailable,
                "membership_scan_complete": False,
                "aggregate_descendant_absence_certified": False,
                "remaining_process_records_unobserved": True,
                "evidence_limit_bytes": GROUP_EVIDENCE_BYTES}
    if retained is not None:
        retained["group_snapshot"] = snapshot
    with os.scandir(proc_root_fd) as inventory:
        for entry in inventory:
            if time.monotonic_ns() >= deadline:
                raise Refusal("child identity observation deadline")
            if entry.name.isdecimal():
                if len(entry.name) > 10 or len(canonical(snapshot)) + len(canonical(entry.name)) + 32 > GROUP_EVIDENCE_BYTES:
                    raise Refusal("finite process group evidence exceeded before inventory entry")
                names.append(entry.name)
                if len(names) > 4096:
                    raise Refusal("finite process group inventory exceeded")
    names.sort()
    for name in names:
        if time.monotonic_ns() >= deadline:
            raise Refusal("child identity observation deadline")
        # 16,385 received bytes can require 21,848 base64 bytes. 32 KiB also
        # covers the bounded row and membership/error updates before any read.
        if len(canonical(snapshot)) + GROUP_NEXT_RECORD_BYTES > GROUP_EVIDENCE_BYTES:
            raise Refusal("finite process group evidence exceeded before next read")
        directory = None
        try:
            directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                dir_fd=proc_root_fd)
            raw = reads.proc_at(directory, "stat", 16384)
            records.append({"procfs_pid": int(name), "stat_base64": base64.b64encode(raw).decode()})
            item = _stat_identity(raw)
            if item["pid"] != int(name):
                raise Refusal("process inventory PID binding mismatch")
            if item["pgrp"] == group_pid:
                members.append(int(name))
        except OSError as exc:
            row = {"procfs_pid": int(name), "error": type(exc).__name__, "errno": exc.errno,
                   "unread_suffix_unobserved": True}
            if hasattr(exc, "proc_read_evidence"):
                row["proc_read_evidence"] = exc.proc_read_evidence
            unavailable.append(row)
        finally:
            if directory is not None:
                os.close(directory)
        if len(canonical(snapshot)) > GROUP_EVIDENCE_BYTES:
            raise Refusal("finite process group evidence accounting exceeded")
    snapshot["membership_scan_complete"] = not unavailable
    snapshot["remaining_process_records_unobserved"] = False
    return snapshot


class KernelChild:
    """Held pidfd + held proc directory; numeric namespace IDs are annotations.

    Child creation and all wait4 calls belong to this single isolated parent.
    waitid(P_PIDFD, WNOWAIT) authenticates waitable parentage without reaping.
    A reaped/closed handle can never be sampled or rebound to a reused PID.
    """
    def __init__(self, pid, verified_executable, reads, deadline):
        self.pid, self.deadline = pid, deadline
        self.fds, self.closed, self.reaped = [], False, False
        self.previous = None
        self.receipt = {"schema": "radio-kernel-child-attribution-v2", "child_namespace_pid": pid,
                        "aggregate_descendant_absence_certified": False, "descriptors_closed": False}
        try:
            if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
                raise Refusal("exclusive default SIGCHLD ownership required")
            self.proc_root = self._hold(os.open("/proc", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC))
            parent_name = os.readlink("self", dir_fd=self.proc_root)
            if not parent_name.isdecimal():
                raise Refusal("kernel self proc-visible identity")
            self.parent_dir = self._hold(os.open(parent_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                                dir_fd=self.proc_root))
            self.fdinfo_dir = self._hold(os.open("fdinfo", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                                dir_fd=self.parent_dir))
            self.parent_namespace = self._hold(os.open("ns/pid", os.O_RDONLY | os.O_CLOEXEC, dir_fd=self.parent_dir))
            parent_status = reads.proc_at(self.parent_dir, "status", 16384)
            self.receipt["parent_status_base64"] = base64.b64encode(parent_status).decode()
            parent_stat = reads.proc_at(self.parent_dir, "stat", 16384)
            self.receipt["parent_stat_base64"] = base64.b64encode(parent_stat).decode()
            fields, item = _fields(parent_status), _stat_identity(parent_stat)
            vector = _numbers(fields, "NSpid")
            if (_numbers(fields, "Pid", 1) != [int(parent_name)] or item["pid"] != int(parent_name)
                    or vector[0] != int(parent_name) or vector[-1] != os.getpid()
                    or _numbers(fields, "Threads", 1) != [1]):
                raise Refusal("parent kernel namespace/process ownership binding")
            self.parent = {"pid": item["pid"], "nspid": vector, "starttime": item["starttime"],
                           "namespace": _object_identity(os.fstat(self.parent_namespace))}
            self.receipt["parent_anchor"] = {**self.parent, "status_base64": base64.b64encode(parent_status).decode(),
                                             "stat_base64": base64.b64encode(parent_stat).decode()}
            # Must precede every wait/reap. No handler/thread may reap this child.
            self.pidfd = self._hold(os.pidfd_open(pid, 0))
            self.pidfd_token = _object_identity(os.fstat(self.pidfd))
            self.receipt["pidfd_object"] = self.pidfd_token
            self._waitable()
            raw, self.mapping = self._fdinfo(reads)
            self.receipt["initial_pidfd_fdinfo_base64"] = base64.b64encode(raw).decode()
            if self.mapping["nspid"][-1] != pid or len(self.mapping["nspid"]) != len(vector):
                raise Refusal("pidfd own-child namespace mapping")
            self.receipt["procfs_pid"] = self.mapping["pid"]
            self.proc_name = str(self.mapping["pid"])
            self.proc_dir = self._hold(os.open(self.proc_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                              dir_fd=self.proc_root))
            self.proc_token = _object_identity(os.fstat(self.proc_dir))
            self.child_namespace = self._hold(os.open("ns/pid", os.O_RDONLY | os.O_CLOEXEC, dir_fd=self.proc_dir))
            if (type(verified_executable) is not dict or set(verified_executable) != {"device", "inode"}
                    or any(type(v) is not int or v < 0 for v in verified_executable.values())):
                raise Refusal("verified interpreter object required")
            self.expected_executable = dict(verified_executable)
            self.receipt["expected_executable_from_verified_before_read"] = self.expected_executable
            self.receipt["held_proc_directory"] = self.proc_token
        except BaseException as exc:
            if hasattr(exc, "proc_read_evidence"):
                self.receipt["proc_read_failure"] = exc.proc_read_evidence
            self.close()
            exc.process_receipt = self.receipt
            raise

    def _hold(self, fd):
        self.fds.append(fd)
        return fd

    def _active(self):
        if self.closed or self.reaped:
            raise Refusal("closed or reaped kernel child cannot be sampled")
        if time.monotonic_ns() >= self.deadline:
            raise Refusal("child identity observation deadline")
        if _object_identity(os.fstat(self.pidfd)) != self.pidfd_token:
            raise Refusal("pidfd descriptor substituted")

    def _waitable(self):
        # The kernel rejects a nonchild pidfd with ECHILD. WNOWAIT preserves the
        # direct child's wait4 receipt and prevents namespace-PID reuse.
        item = os.waitid(os.P_PIDFD, self.pidfd, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if item is not None:
            if item.si_pid != self.pid:
                raise Refusal("kernel pidfd wait ownership mismatch")
            raise Refusal("child exited before authentic live observation")

    def _fdinfo(self, reads):
        self._active()
        raw = reads.proc_at(self.fdinfo_dir, str(self.pidfd), 16384)
        # Retain malformed/duplicate/missing identity records before parsing.
        self.receipt["last_pidfd_fdinfo_read_base64"] = base64.b64encode(raw).decode()
        identity = _fdinfo_identity(raw)
        self._active()
        return raw, identity

    def observe(self, reads):
        self._active()
        self._waitable()
        attempt = {}
        # Successful raw records go to procfs-samples.json. Only a partial
        # failed attempt remains here, avoiding unbounded duplicate retention.
        self.receipt["partial_sampling_attempt"] = attempt
        before_raw, mapping = self._fdinfo(reads)
        attempt["pidfd_fdinfo_before_base64"] = base64.b64encode(before_raw).decode()
        if mapping != self.mapping:
            raise Refusal("pidfd mapping changed during lifetime")
        named = os.stat(self.proc_name, dir_fd=self.proc_root, follow_symlinks=False)
        if _object_identity(named) != self.proc_token or _object_identity(os.fstat(self.proc_dir)) != self.proc_token:
            raise Refusal("held/named child proc directory drift")
        status_raw = reads.proc_at(self.proc_dir, "status", 16384)
        attempt["status_base64"] = base64.b64encode(status_raw).decode()
        stat_raw = reads.proc_at(self.proc_dir, "stat", 16384)
        attempt["stat_base64"] = base64.b64encode(stat_raw).decode()
        # ns/pid and exe are intentional kernel magic links. Bind their inode
        # identities, never a user-provided pathname or a numeric namespace tail.
        namespace = _object_identity(os.stat("ns/pid", dir_fd=self.proc_dir))
        if namespace != _object_identity(os.fstat(self.child_namespace)):
            raise Refusal("held/named child PID namespace drift")
        executable = _object_identity(os.stat("exe", dir_fd=self.proc_dir))
        identity = _candidate_identity(status_raw, stat_raw, mapping, self.parent, self.pid,
                                       namespace, executable, self.expected_executable, self.previous)
        group = _group_observations(self.proc_root, mapping["pid"], reads, self.deadline, retained=attempt)
        after_raw, after_mapping = self._fdinfo(reads)
        attempt["pidfd_fdinfo_after_base64"] = base64.b64encode(after_raw).decode()
        self._waitable()
        if mapping != after_mapping:
            raise Refusal("pidfd changed across sample")
        after_status = reads.proc_at(self.proc_dir, "status", 16384)
        attempt["status_after_base64"] = base64.b64encode(after_status).decode()
        after_stat = reads.proc_at(self.proc_dir, "stat", 16384)
        attempt["stat_after_base64"] = base64.b64encode(after_stat).decode()
        _candidate_identity(after_status, after_stat, after_mapping, self.parent, self.pid,
                            _object_identity(os.stat("ns/pid", dir_fd=self.proc_dir)),
                            _object_identity(os.stat("exe", dir_fd=self.proc_dir)),
                            self.expected_executable, identity)
        self.previous = identity
        self.receipt["identity"] = identity
        attempt["identity"] = identity
        attempt["attribution_authenticated"] = True
        values, fields = {}, _fields(status_raw)
        for key in ("VmRSS", "VmHWM"):
            observed = fields.get(key)
            if not observed or len(observed) != 2 or observed[1] != "kB" or not observed[0].isdecimal():
                raise Refusal("missing authenticated live RSS observation:" + key)
            values[key + "_bytes"] = int(observed[0]) * 1024
        del self.receipt["partial_sampling_attempt"]
        return {"observed": True, "attribution_authenticated": True,
                "child_namespace_pid": self.pid, "procfs_pid": mapping["pid"], "identity": identity,
                "pidfd_fdinfo_before_base64": base64.b64encode(before_raw).decode(),
                "pidfd_fdinfo_after_base64": base64.b64encode(after_raw).decode(),
                "status_base64": base64.b64encode(status_raw).decode(),
                "stat_base64": base64.b64encode(stat_raw).decode(),
                "status_after_base64": base64.b64encode(after_status).decode(),
                "stat_after_base64": base64.b64encode(after_stat).decode(), **group, **values}

    def mark_reaped(self, waited, reads):
        if self.closed or self.reaped or waited != self.pid:
            raise Refusal("unexpected or repeated own-child reap")
        self.reaped = True
        self.receipt["reaped_namespace_pid"] = waited
        if _object_identity(os.fstat(self.pidfd)) != self.pidfd_token:
            raise Refusal("pidfd substituted before reap receipt")
        reads.begin_terminal_pidfd()
        raw = reads.proc_at(self.fdinfo_dir, str(self.pidfd), 16384)
        self.receipt["reaped_pidfd_fdinfo_base64"] = base64.b64encode(raw).decode()
        fields = _fields(raw)
        if fields.get("Pid") != ["-1"] or fields.get("NSpid") != ["-1"]:
            raise Refusal("kernel pidfd not terminal after own-child reap")
        self.receipt["pidfd_terminal_observed"] = True

    def close(self):
        if not self.closed:
            for fd in reversed(self.fds):
                os.close(fd)
            self.fds.clear()
            self.closed = True
            self.receipt["descriptors_closed"] = True


def _proc_observation(child, reads):
    if not isinstance(child, KernelChild):
        raise Refusal("held kernel child identity required; numeric PID alone refused")
    return child.observe(reads)


def _kill_child_group(child, kernel_child):
    # The sole parent does not reap before this call. A reaped numeric PID is
    # never signalled. pidfd additionally targets the exact held direct child.
    if child.returncode is not None:
        return
    if kernel_child is not None and not kernel_child.closed:
        try:
            signal.pidfd_send_signal(kernel_child.pidfd, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run(contract_raw, contract_sha256, proof_raw, proof_sha256, marker_raw, marker_sha256, *, initial_read_bytes=0, started_monotonic_ns=None):
    """Spend once and observe one child; exact supplied pins are exogenous inputs."""
    began = time.monotonic_ns() if started_monotonic_ns is None else started_monotonic_ns
    if type(initial_read_bytes) is not int or initial_read_bytes < 0 or type(began) is not int or began > time.monotonic_ns():
        raise Refusal("selected startup accounting")
    contract = validate_contract(contract_raw, contract_sha256)
    if str(Path(sys.executable).resolve()) != contract["python_executable"] or not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise Refusal("running parent executable or -I -B -S isolation differs from prospective pin")
    proof = verify_publication(contract, contract_sha256, proof_raw, proof_sha256, marker_raw, marker_sha256)
    limits = contract["limits"]
    deadline = began + limits["wall_seconds"] * 10**9
    reads = Reads(limits["read_bytes"])
    reads.bytes = initial_read_bytes
    child_contract_pin = next(p for p in contract["source_pins"] if p["path"] == contract["collector_contract_path"])
    child_contract_raw, _ = reads.file(contract["collector_contract_path"], child_contract_pin["bytes"])
    child_contract = _json(child_contract_raw, contract["collector_contract_sha256"])
    if child_contract.get("capture_identity") != contract["capture_identity"]:
        raise Refusal("child capture identity mismatch before spend")
    if contract["evidence_domain"] == "metadata-capture-only":
        if child_contract.get("evidence_domain") != "metadata-capture-only" or child_contract.get("capture_authorized") is not True or child_contract.get("externally_bound_publication_required") is not True or child_contract.get("activation_required") is not True or child_contract.get("plan_sha256") != contract["plan_sha256"] or child_contract.get("python_path") != contract["python_executable"] or child_contract.get("python_sha256") != contract["python_sha256"] or child_contract.get("imports") != [] or child_contract.get("import_paths") != []:
            raise Refusal("metadata-only child contract linkage or import policy")
    child_read_reserved = child_contract.get("limits", {}).get("read_bytes") if type(child_contract) is dict else None
    if type(child_read_reserved) is not int or child_read_reserved <= 0 or child_read_reserved >= limits["read_bytes"]:
        raise Refusal("separately pinned child read reservation")
    reads.limit -= child_read_reserved
    if reads.bytes + 2 * sum(p["bytes"] for p in contract["source_pins"] + contract["runtime_pins"]) + 2 * 1024**2 > reads.limit:
        raise Refusal("joined parent/child read reservation cannot cover known two-pass inventory")
    root = Path(contract["output_root"])
    # Root is created by the caller before publication and must be empty at admission.
    if root.is_symlink() or not root.is_dir() or list(root.iterdir()):
        raise Refusal("fresh empty owned artifact scope required")
    if format(root.stat().st_mode & 0o7777, "04o") != "0700":
        raise Refusal("owned artifact scope mode required")
    if root.resolve() != root:
        raise Refusal("artifact ancestor symlink")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        _root_matches(root, root_fd, contract["output_root_identity"])
        verified_objects = {}
        verified_contents = {contract["collector_path"]: None}
        before = [_pin_file(p, reads, verified_objects=verified_objects,
                           verified_contents=verified_contents) for p in contract["source_pins"] + contract["runtime_pins"]]
        collector_pin = next(p for p in contract["source_pins"] if p["path"] == contract["collector_path"])
        bootstrap = _collector_bootstrap(verified_contents[contract["collector_path"]],
                                         contract["collector_path"], collector_pin["sha256"])
        _root_matches(root, root_fd, contract["output_root_identity"])
        if time.monotonic_ns() + (limits["child_seconds"] + limits["reap_seconds"] + 1) * 10**9 >= deadline:
            raise Refusal("startup spent too much finite wall allowance")
        marker_local, _ = reads.file(contract["activation_path"], len(marker_raw))
        if marker_local != marker_raw:
            raise Refusal("local activation marker differs from immutable pinned bytes")
        reads.reserve_terminal(sum(p["bytes"] for p in contract["source_pins"] + contract["runtime_pins"]))
        spent = {"schema": "radio-runtime-metadata-capture-spent-v1", "capture_identity": contract["capture_identity"],
                 "contract_sha256": contract_sha256, "proof_sha256": proof_sha256, "activation_sha256": marker_sha256,
                 "prepared_commit": proof["prepared_commit"], "activation_commit": proof["activation_commit"],
                 "began_monotonic_ns": began, "spent_monotonic_ns": time.monotonic_ns(), "limits": limits,
                 "irreversible": True, "retry_allowed": False, "authority": AUTHORITY}
        spent["authority_scope"] = "scientific-and-source-certificates-only"
        spent["engineering_capture_authorized"] = True
        spent["engineering_reservation_spent"] = True
        artifact_reservation = _artifact_reservation(proof_raw, before, spent, limits)
        def write_artifact(path, raw, mode=0o600):
            _write_new(path, raw, root_fd, mode, artifact_limit=limits["artifact_bytes"],
                       spent_basename=Path(contract["spent_path"]).name)
        write_artifact(contract["spent_path"], canonical(spent))
        # A terminal report is attempted after every spent launch failure. Marker stays.
        write_artifact(str(root / "selected-runtime-before.json"), canonical(before))
        write_artifact(str(root / "admission-witness.json"), proof_raw, 0o644)
        stdout = bytearray()
        stderr = bytearray()
        samples = []
        child = None
        kernel_child = None
        process_receipt = None
        child_status = usage = None
        failure = None
        selected = selectors.DefaultSelector()
        try:
            def setup():
                resource.setrlimit(resource.RLIMIT_AS, (limits["rss_bytes"], limits["rss_bytes"]))
                resource.setrlimit(resource.RLIMIT_FSIZE, (limits["stream_bytes"], limits["stream_bytes"]))
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                resource.setrlimit(resource.RLIMIT_CPU, (limits["child_seconds"], limits["child_seconds"] + 1))
            command = [contract["python_executable"], "-I", "-B", "-S", "-c", bootstrap,
                       "--contract", contract["collector_contract_path"], "--contract-sha256", contract["collector_contract_sha256"],
                       "--plan", contract["plan_path"], "--plan-sha256", contract["plan_sha256"],
                       "--admission-witness", str(root / "admission-witness.json"), "--admission-witness-sha256", proof_sha256]
            child = subprocess.Popen(command, cwd=str(root), env={"LANG": "C", "LC_ALL": "C", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"},
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     close_fds=True, start_new_session=True, preexec_fn=setup)
            launched = time.monotonic_ns()
            child_deadline = min(deadline - (limits["reap_seconds"] + 1) * 10**9, launched + limits["child_seconds"] * 10**9)
            kernel_child = KernelChild(child.pid, verified_objects[contract["python_executable"]], reads, child_deadline)
            process_receipt = kernel_child.receipt
            _sample_room(samples, artifact_reservation)
            initial_observation = _proc_observation(kernel_child, reads)
            initial_observation["monotonic_ns"] = time.monotonic_ns()
            if len(canonical(initial_observation)) > PROC_SAMPLE_RESERVE_BYTES:
                raise Refusal("finite complete sample evidence exceeded")
            if len(canonical(samples + [initial_observation])) > artifact_reservation["samples_reserved_bytes"]:
                raise Refusal("artifact prospective initial sample cannot fit")
            samples.append(initial_observation)
            if (not initial_observation["membership_scan_complete"] or
                    initial_observation["observed_process_group_members"] != [initial_observation["procfs_pid"]] or
                    initial_observation["VmRSS_bytes"] > limits["rss_bytes"]):
                raise Refusal("initial descendant/RSS/unavailable process snapshot")
            for stream, output in ((child.stdout, stdout), (child.stderr, stderr)):
                os.set_blocking(stream.fileno(), False)
                selected.register(stream, selectors.EVENT_READ, output)
            next_sample = launched + 50_000_000
            killed = False
            while child_status is None or selected.get_map():
                now = time.monotonic_ns()
                if now > child_deadline and not killed:
                    failure = failure or "CHILD_DEADLINE"
                    _kill_child_group(child, kernel_child)
                    killed = True
                if now > deadline - 10**9:
                    failure = failure or "WHOLE_SCOPE_DEADLINE"
                    break
                if child_status is None:
                    waited, status, current_usage = os.wait4(child.pid, os.WNOHANG)
                    if waited:
                        child_status, usage = status, current_usage
                        child.returncode = os.waitstatus_to_exitcode(status)
                        kernel_child.mark_reaped(waited, reads)
                for key, _ in selected.select(0.02):
                    chunk = os.read(key.fileobj.fileno(), min(65536, limits["stream_bytes"] + 1 - len(key.data)))
                    if not chunk:
                        selected.unregister(key.fileobj)
                        key.fileobj.close()
                    else:
                        key.data.extend(chunk)
                        if len(key.data) > limits["stream_bytes"]:
                            failure = failure or "RAW_STREAM_CAP"
                            selected.unregister(key.fileobj)
                            key.fileobj.close()
                            if child_status is None and not killed:
                                _kill_child_group(child, kernel_child)
                                killed = True
                if child_status is None and now >= next_sample:
                    if len(samples) >= limits["sample_count"]:
                        failure = failure or "PROCFS_SAMPLE_CAP"
                        _kill_child_group(child, kernel_child)
                        killed = True
                    else:
                        _sample_room(samples, artifact_reservation)
                        observation = _proc_observation(kernel_child, reads)
                        observation["monotonic_ns"] = now
                        if len(canonical(observation)) > PROC_SAMPLE_RESERVE_BYTES:
                            raise Refusal("finite complete sample evidence exceeded")
                        if len(canonical(samples + [observation])) > artifact_reservation["samples_reserved_bytes"]:
                            raise Refusal("artifact prospective sample cannot fit")
                        samples.append(observation)
                        if (not observation["membership_scan_complete"] or observation["observed_process_group_members"] != [observation["procfs_pid"]] or observation["VmRSS_bytes"] > limits["rss_bytes"]):
                            failure = failure or "DESCENDANT_OR_SAMPLED_RSS"
                            _kill_child_group(child, kernel_child)
                            killed = True
                    next_sample = now + 50_000_000
                if len(canonical(samples)) > artifact_reservation["samples_reserved_bytes"]:
                    failure = failure or "ARTIFACT_ENVELOPE"
                    if child_status is None and not killed:
                        _kill_child_group(child, kernel_child)
                        killed = True
            if child_status is None:
                _kill_child_group(child, kernel_child)
                reap_deadline = min(deadline - 500_000_000, time.monotonic_ns() + limits["reap_seconds"] * 10**9)
                while time.monotonic_ns() < reap_deadline:
                    waited, status, current_usage = os.wait4(child.pid, os.WNOHANG)
                    if waited:
                        child_status, usage = status, current_usage
                        child.returncode = os.waitstatus_to_exitcode(status)
                        kernel_child.mark_reaped(waited, reads)
                        break
                    time.sleep(0.01)
                if child_status is None:
                    failure = failure or "REAP_DEADLINE"
        except BaseException as exc:
            process_receipt = getattr(exc, "process_receipt", process_receipt)
            if process_receipt is not None and hasattr(exc, "proc_read_evidence"):
                process_receipt["proc_read_failure"] = exc.proc_read_evidence
            if isinstance(exc, Refusal) and str(exc) == "child identity observation deadline":
                failure = failure or "CHILD_DEADLINE"
            elif isinstance(exc, Refusal) and str(exc).startswith("artifact "):
                failure = failure or "ARTIFACT_ENVELOPE"
            elif isinstance(exc, Refusal) and str(exc).startswith("finite process group evidence"):
                failure = failure or "PROCFS_EVIDENCE_CAP"
            else:
                failure = failure or "SUPERVISOR_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:500]
            if child is not None and child_status is None:
                try:
                    _kill_child_group(child, kernel_child)
                    exception_reap_deadline = min(deadline - 500_000_000, time.monotonic_ns() + limits["reap_seconds"] * 10**9)
                    while time.monotonic_ns() < exception_reap_deadline:
                        waited, status, current_usage = os.wait4(child.pid, os.WNOHANG)
                        if waited:
                            child_status, usage = status, current_usage
                            child.returncode = os.waitstatus_to_exitcode(child_status)
                            if kernel_child is not None:
                                kernel_child.mark_reaped(waited, reads)
                            break
                        time.sleep(0.01)
                except (OSError, ChildProcessError, Refusal) as reap_exc:
                    if process_receipt is not None:
                        process_receipt["terminal_attribution_error"] = type(reap_exc).__name__ + ":" + str(reap_exc)[:300]
                        if hasattr(reap_exc, "proc_read_evidence"):
                            # Preserve terminal bytes separately from an earlier
                            # refused sampling read; neither prefix is replaced.
                            process_receipt["terminal_proc_read_failure"] = reap_exc.proc_read_evidence
        finally:
            if kernel_child is not None:
                kernel_child.close()
            selected.close()
            for stream in (getattr(child, "stdout", None), getattr(child, "stderr", None)):
                if stream is not None and not stream.closed:
                    stream.close()
        after = None
        reads.begin_terminal_files()
        try:
            after = [_pin_file(p, reads) for p in contract["source_pins"] + contract["runtime_pins"]]
        except (Refusal, OSError) as exc:
            failure = failure or "TERMINAL_PIN_DRIFT:" + str(exc)[:300]
        if child_status is not None and os.waitstatus_to_exitcode(child_status) != 0:
            failure = failure or "CHILD_NONZERO"
        child_read_observed = None
        child_receipt = None
        if not failure:
            try:
                child_receipt = _json(bytes(stdout), digest(bytes(stdout)))
                if type(child_receipt) is not dict or child_receipt.get("schema") != "radio-runtime-metadata-capture-observation-v1" or child_receipt.get("status") != "OBSERVED_METADATA_ONLY":
                    raise Refusal("child metadata receipt shape")
                if child_receipt.get("capture_identity") != contract["capture_identity"] or child_receipt.get("contract_sha256") != contract["collector_contract_sha256"] or child_receipt.get("plan_sha256") != contract["plan_sha256"]:
                    raise Refusal("child metadata receipt external bindings")
                authority = child_receipt.get("authority")
                if type(authority) is not dict or not authority or any(type(v) is not bool or v is not False for v in authority.values()):
                    raise Refusal("child metadata receipt promoted authority")
                child_read_observed = child_receipt.get("read_ledger", {}).get("read_bytes")
                if type(child_read_observed) is not int or not 0 <= child_read_observed <= child_read_reserved:
                    raise Refusal("child selected read accounting")
            except (Refusal, ValueError) as exc:
                failure = "CHILD_RECEIPT:" + str(exc)[:300]
        # Guard the complete prospective final output before writing any of it.
        pending_artifacts = [("child.stdout.raw", bytes(stdout)), ("child.stderr.raw", bytes(stderr)),
                             ("procfs-samples.json", canonical(samples)),
                             ("selected-runtime-after.json", canonical(after))]
        current_scope = _scope_inventory(root, Path(contract["spent_path"]).name, root_fd)
        if (max(current_scope["logical_bytes"], current_scope["allocated_bytes"])
                + sum(len(raw) for _, raw in pending_artifacts)
                + TERMINAL_REPORT_RESERVE_BYTES + ARTIFACT_ACCOUNTING_SLACK_BYTES > limits["artifact_bytes"]):
            raise Refusal("artifact prospective terminal evidence cannot fit; spent scope retained")
        for name, raw in pending_artifacts:
            write_artifact(str(root / name), raw)
        _root_matches(root, root_fd, contract["output_root_identity"])
        before_report = _scope_inventory(root, Path(contract["spent_path"]).name, root_fd)
        if max(before_report["logical_bytes"], before_report["allocated_bytes"]) + 16384 > limits["artifact_bytes"]:
            failure = failure or "TERMINAL_STORAGE_CAP"
        report = {"schema": "radio-runtime-metadata-capture-supervisor-result-v1", "capture_identity": contract["capture_identity"],
                  "status": "CLOSED_FAILED" if failure else "OBSERVED_METADATA_ONLY", "failure": failure,
                  "contract_sha256": contract_sha256, "publication_proof_sha256": proof_sha256,
                  "activation_sha256": marker_sha256, "prepared_commit": proof["prepared_commit"], "activation_commit": proof["activation_commit"],
                  "started_monotonic_ns": began, "before_report_monotonic_ns": time.monotonic_ns(),
                  "elapsed_before_final_report_seconds": (time.monotonic_ns() - began) / 1e9,
                  "child_pid": child.pid if child else None, "wait_status": child_status,
                  "child_exit_code": os.waitstatus_to_exitcode(child_status) if child_status is not None else None,
                  "child_reaped": child_status is not None,
                  "process_attribution": process_receipt,
                  "authenticated_procfs_samples": sum(p.get("attribution_authenticated") is True for p in samples),
                  "aggregate_descendant_absence_certified": False,
                  "wait4_child_ru_maxrss_bytes": int(usage.ru_maxrss * 1024) if usage else None,
                  "parent_lifetime_ru_maxrss_bytes_at_selected_call": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024),
                  "selected_before_after_equal": before == after, "charged_read_bytes": reads.bytes,
                  "child_read_reserved_bytes": child_read_reserved, "child_read_observed_bytes": child_read_observed,
                  "joined_selected_read_observed_bytes": reads.bytes + child_read_observed if child_read_observed is not None else None,
                  "joined_selected_read_conservative_bytes": reads.bytes + child_read_reserved,
                  "raw_stdout_bytes": len(stdout), "raw_stderr_bytes": len(stderr), "procfs_samples": len(samples),
                  "selected_scope_before_final_report": before_report, "limits": limits,
                  "artifact_reservation": artifact_reservation,
                  "terminal_read_reservation": reads.terminal_reservation,
                  "collector_dispatch": {"kind": "frozen-verified-bytes-bootstrap-v1",
                      "source_path": contract["collector_path"], "source_bytes": collector_pin["bytes"],
                      "source_sha256": collector_pin["sha256"],
                      "bootstrap_bytes": len(bootstrap.encode("utf-8")),
                      "bootstrap_sha256": digest(bootstrap.encode("utf-8")),
                      "source_path_reopened_for_dispatch": False,
                      "interpreter_implicit_loader_closure_qualified": False},
                  "spent_forever": True, "retry_allowed": False, "authority": AUTHORITY,
                  "authority_scope": "scientific-and-source-certificates-only",
                  "engineering_capture_authorized": True, "engineering_reservation_spent": True,
                  "engineering_child_dispatches": 1 if child is not None else 0,
                  "observation_limits": ["procfs samples do not prove absence between samples", "RLIMIT_AS is address space, not an aggregate RSS certificate", "wait4 peak covers direct child only", "parent ru_maxrss is the process lifetime maximum at a selected call, not current RSS or the capture scope peak", "read accounting covers explicit regular-file reads and procfs bytes, not kernel/dynamic-loader implicit reads", "raw stream cap failure retains exactly received bytes; unread pipe suffix is not certified", "publication proof provenance is supplied and externally pinned, not reauthenticated over network here"]}
        report_raw = canonical(report)
        if len(report_raw) > TERMINAL_REPORT_RESERVE_BYTES:
            raise Refusal("artifact finite terminal report evidence exceeded; spent scope retained")
        write_artifact(str(root / "supervisor-result.json"), report_raw)
        _root_matches(root, root_fd, contract["output_root_identity"])
        final_scope = _scope_inventory(root, Path(contract["spent_path"]).name, root_fd)
        completed = time.monotonic_ns()
        if completed > deadline or max(final_scope["logical_bytes"], final_scope["allocated_bytes"]) > limits["artifact_bytes"]:
            raise Refusal("spent capture terminal deadline/storage exceeded; raw evidence retained")
        return {"report": report, "final_scope": final_scope, "completed_monotonic_ns": completed,
                "whole_scope_elapsed_seconds": (completed - began) / 1e9}
    finally:
        os.close(root_fd)


def main():
    began = time.monotonic_ns()
    parser = argparse.ArgumentParser()
    for name in ("contract", "contract-sha256", "publication-proof", "publication-proof-sha256", "activation", "activation-sha256"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    # CLI input reads are a small separate pre-admission envelope; the prospective
    # contract must include their source pin rows and selected read observations.
    reads = Reads(32 * 1024**2)
    contract, _ = reads.file(args.contract, 8 * 1024**2)
    proof, _ = reads.file(args.publication_proof, 16 * 1024**2)
    marker, _ = reads.file(args.activation, 65536)
    result = run(contract, args.contract_sha256, proof, args.publication_proof_sha256, marker, args.activation_sha256,
                 initial_read_bytes=reads.bytes, started_monotonic_ns=began)
    sys.stdout.buffer.write(canonical(result))


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError) as exc:
        sys.stderr.write("CLOSED_FAILED: " + str(exc) + "\n")
        raise SystemExit(1)
