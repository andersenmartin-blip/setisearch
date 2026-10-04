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
                allocation = self.limit - self.bytes
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
        fd = None
        try:
            fd = os.open(parts[3], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise Refusal("procfs regular observation required")
            chunks = []
            remaining = cap + 1
            while remaining:
                allocation = self.limit - self.bytes
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
        finally:
            if fd is not None:
                os.close(fd)
            os.close(directory)


def _pin_file(pin, reads):
    if type(pin) is not dict or set(pin) != PIN_KEYS or type(pin["bytes"]) is not int or pin["bytes"] < 0 or not _hex(pin["sha256"]):
        raise Refusal("invalid pin")
    if type(pin["mode"]) is not str or len(pin["mode"]) != 4 or any(c not in "01234567" for c in pin["mode"]):
        raise Refusal("invalid mode pin")
    raw, observed = reads.file(pin["path"], pin["bytes"])
    result = {"path": pin["path"], "bytes": len(raw), "sha256": digest(raw), "mode": format(observed.st_mode & 0o7777, "04o")}
    if result != pin:
        raise Refusal("selected source/runtime pin changed")
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
    if proof["activation_changed_path"] != "config/radio_runtime_metadata_capture_20261004a.activate.json" or proof["contract_sha256"] != contract_sha256 or proof["activation_sha256"] != marker_sha256:
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


def _write_new(path, raw, root_fd=None, mode=0o600):
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


def _proc_observation(pid, reads):
    # /proc mount may expose host IDs while wait4 uses the namespace child ID.
    candidates = [str(pid)] + [p.name for p in Path("/proc").iterdir() if p.name.isdigit() and p.name != str(pid)]
    if len(candidates) > 4096:
        raise Refusal("finite procfs inventory exceeded")
    match = None
    for name in candidates:
        try:
            raw = reads.proc("/proc/" + name + "/status", 16384)
        except OSError:
            continue
        lines = raw.decode("ascii", "replace").splitlines()
        nspid = next((line.split()[1:] for line in lines if line.startswith("NSpid:")), [])
        if nspid and nspid[-1] == str(pid):
            match = (name, raw, lines)
            break
    if match is None:
        return {"observed": False, "child_namespace_pid": pid}
    name, raw, lines = match
    try:
        stat_raw = reads.proc("/proc/" + name + "/stat", 16384)
    except FileNotFoundError:
        return {"observed": False, "child_namespace_pid": pid, "status_base64": base64.b64encode(raw).decode(), "terminal_disappearance_during_sample": True}
    rest = stat_raw[stat_raw.rfind(b")") + 2:].split()
    group = rest[2].decode()
    members = []
    members_paths = [p for p in Path("/proc").iterdir() if p.name.isdigit()]
    if len(members_paths) > 4096:
        raise Refusal("finite process group inventory exceeded")
    for p in members_paths:
        try:
            member_raw = reads.proc(str(p / "stat"), 16384)
            member_rest = member_raw[member_raw.rfind(b")") + 2:].split()
            if member_rest[2].decode() == group:
                members.append(int(p.name))
        except (OSError, IndexError):
            continue
    values = {}
    for key in ("VmRSS", "VmHWM"):
        selected = next((line.split()[1:] for line in lines if line.startswith(key + ":")), [])
        values[key + "_bytes"] = int(selected[0]) * 1024 if selected and selected[-1] == "kB" else None
    return {"observed": True, "child_namespace_pid": pid, "procfs_pid": int(name),
            "status_base64": base64.b64encode(raw).decode(), "stat_base64": base64.b64encode(stat_raw).decode(),
            "observed_process_group_members": sorted(members), **values}


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
        before = [_pin_file(p, reads) for p in contract["source_pins"] + contract["runtime_pins"]]
        _root_matches(root, root_fd, contract["output_root_identity"])
        if time.monotonic_ns() + (limits["child_seconds"] + limits["reap_seconds"] + 1) * 10**9 >= deadline:
            raise Refusal("startup spent too much finite wall allowance")
        marker_local, _ = reads.file(contract["activation_path"], len(marker_raw))
        if marker_local != marker_raw:
            raise Refusal("local activation marker differs from immutable pinned bytes")
        spent = {"schema": "radio-runtime-metadata-capture-spent-v1", "capture_identity": contract["capture_identity"],
                 "contract_sha256": contract_sha256, "proof_sha256": proof_sha256, "activation_sha256": marker_sha256,
                 "prepared_commit": proof["prepared_commit"], "activation_commit": proof["activation_commit"],
                 "began_monotonic_ns": began, "spent_monotonic_ns": time.monotonic_ns(), "limits": limits,
                 "irreversible": True, "retry_allowed": False, "authority": AUTHORITY}
        spent["authority_scope"] = "scientific-and-source-certificates-only"
        spent["engineering_capture_authorized"] = True
        spent["engineering_reservation_spent"] = True
        _write_new(contract["spent_path"], canonical(spent), root_fd)
        # A terminal report is attempted after every spent launch failure. Marker stays.
        _write_new(str(root / "selected-runtime-before.json"), canonical(before), root_fd)
        _write_new(str(root / "admission-witness.json"), proof_raw, root_fd, 0o644)
        stdout = bytearray()
        stderr = bytearray()
        samples = []
        child = None
        child_status = usage = None
        failure = None
        selected = selectors.DefaultSelector()
        try:
            def setup():
                resource.setrlimit(resource.RLIMIT_AS, (limits["rss_bytes"], limits["rss_bytes"]))
                resource.setrlimit(resource.RLIMIT_FSIZE, (limits["stream_bytes"], limits["stream_bytes"]))
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                resource.setrlimit(resource.RLIMIT_CPU, (limits["child_seconds"], limits["child_seconds"] + 1))
            command = [contract["python_executable"], "-I", "-B", "-S", contract["collector_path"],
                       "--contract", contract["collector_contract_path"], "--contract-sha256", contract["collector_contract_sha256"],
                       "--plan", contract["plan_path"], "--plan-sha256", contract["plan_sha256"],
                       "--admission-witness", str(root / "admission-witness.json"), "--admission-witness-sha256", proof_sha256]
            child = subprocess.Popen(command, cwd=str(root), env={"LANG": "C", "LC_ALL": "C", "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"},
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     close_fds=True, start_new_session=True, preexec_fn=setup)
            launched = time.monotonic_ns()
            child_deadline = min(deadline - (limits["reap_seconds"] + 1) * 10**9, launched + limits["child_seconds"] * 10**9)
            for stream, output in ((child.stdout, stdout), (child.stderr, stderr)):
                os.set_blocking(stream.fileno(), False)
                selected.register(stream, selectors.EVENT_READ, output)
            next_sample = launched
            killed = False
            while child_status is None or selected.get_map():
                now = time.monotonic_ns()
                if now > child_deadline and not killed:
                    failure = failure or "CHILD_DEADLINE"
                    os.killpg(child.pid, signal.SIGKILL)
                    killed = True
                if now > deadline - 10**9:
                    failure = failure or "WHOLE_SCOPE_DEADLINE"
                    break
                if child_status is None:
                    waited, status, current_usage = os.wait4(child.pid, os.WNOHANG)
                    if waited:
                        child_status, usage = status, current_usage
                        child.returncode = os.waitstatus_to_exitcode(status)
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
                                os.killpg(child.pid, signal.SIGKILL)
                                killed = True
                if child_status is None and now >= next_sample:
                    if len(samples) >= limits["sample_count"]:
                        failure = failure or "PROCFS_SAMPLE_CAP"
                        os.killpg(child.pid, signal.SIGKILL)
                        killed = True
                    else:
                        observation = _proc_observation(child.pid, reads)
                        observation["monotonic_ns"] = now
                        samples.append(observation)
                        if observation.get("observed") and ((observation["observed_process_group_members"] and observation["observed_process_group_members"] != [observation["procfs_pid"]]) or observation.get("VmRSS_bytes", 0) > limits["rss_bytes"]):
                            failure = failure or "DESCENDANT_OR_SAMPLED_RSS"
                            os.killpg(child.pid, signal.SIGKILL)
                            killed = True
                    next_sample = now + 50_000_000
                if len(stdout) + len(stderr) + len(canonical(samples)) + 65536 > limits["artifact_bytes"]:
                    failure = failure or "ARTIFACT_ENVELOPE"
                    if child_status is None and not killed:
                        os.killpg(child.pid, signal.SIGKILL)
                        killed = True
            if child_status is None:
                os.killpg(child.pid, signal.SIGKILL)
                reap_deadline = min(deadline - 500_000_000, time.monotonic_ns() + limits["reap_seconds"] * 10**9)
                while time.monotonic_ns() < reap_deadline:
                    waited, status, current_usage = os.wait4(child.pid, os.WNOHANG)
                    if waited:
                        child_status, usage = status, current_usage
                        child.returncode = os.waitstatus_to_exitcode(status)
                        break
                    time.sleep(0.01)
                if child_status is None:
                    failure = failure or "REAP_DEADLINE"
        except BaseException as exc:
            failure = failure or "SUPERVISOR_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:500]
            if child is not None and child_status is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                    exception_reap_deadline = min(deadline - 500_000_000, time.monotonic_ns() + limits["reap_seconds"] * 10**9)
                    while time.monotonic_ns() < exception_reap_deadline:
                        waited, status, current_usage = os.wait4(child.pid, os.WNOHANG)
                        if waited:
                            child_status, usage = status, current_usage
                            child.returncode = os.waitstatus_to_exitcode(child_status)
                            break
                        time.sleep(0.01)
                except (OSError, ChildProcessError):
                    pass
        finally:
            selected.close()
            for stream in (getattr(child, "stdout", None), getattr(child, "stderr", None)):
                if stream is not None and not stream.closed:
                    stream.close()
        after = None
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
        _write_new(str(root / "child.stdout.raw"), bytes(stdout), root_fd)
        _write_new(str(root / "child.stderr.raw"), bytes(stderr), root_fd)
        _write_new(str(root / "procfs-samples.json"), canonical(samples), root_fd)
        _write_new(str(root / "selected-runtime-after.json"), canonical(after), root_fd)
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
                  "wait4_child_ru_maxrss_bytes": int(usage.ru_maxrss * 1024) if usage else None,
                  "parent_lifetime_ru_maxrss_bytes_at_selected_call": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024),
                  "selected_before_after_equal": before == after, "charged_read_bytes": reads.bytes,
                  "child_read_reserved_bytes": child_read_reserved, "child_read_observed_bytes": child_read_observed,
                  "joined_selected_read_observed_bytes": reads.bytes + child_read_observed if child_read_observed is not None else None,
                  "joined_selected_read_conservative_bytes": reads.bytes + child_read_reserved,
                  "raw_stdout_bytes": len(stdout), "raw_stderr_bytes": len(stderr), "procfs_samples": len(samples),
                  "selected_scope_before_final_report": before_report, "limits": limits,
                  "spent_forever": True, "retry_allowed": False, "authority": AUTHORITY,
                  "authority_scope": "scientific-and-source-certificates-only",
                  "engineering_capture_authorized": True, "engineering_reservation_spent": True,
                  "engineering_child_dispatches": 1 if child is not None else 0,
                  "observation_limits": ["procfs samples do not prove absence between samples", "RLIMIT_AS is address space, not an aggregate RSS certificate", "wait4 peak covers direct child only", "parent ru_maxrss is the process lifetime maximum at a selected call, not current RSS or the capture scope peak", "read accounting covers explicit regular-file reads and procfs bytes, not kernel/dynamic-loader implicit reads", "raw stream cap failure retains exactly received bytes; unread pipe suffix is not certified", "publication proof provenance is supplied and externally pinned, not reauthenticated over network here"]}
        _write_new(str(root / "supervisor-result.json"), canonical(report), root_fd)
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
