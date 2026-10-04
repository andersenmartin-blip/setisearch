"""Bounded metadata observations only; never a scientific runtime certificate.

Only an externally pinned explicit fresh contract enters capture. Importing this
module performs no capture. Native package imports are deferred until a separate
complete authenticated pre-import closure exists; this module never opens a dataset, fetches a wheel or executes a command.
"""
from __future__ import annotations
import argparse
import csv
import io
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
import sys

SCHEMA = "radio-runtime-metadata-capture-contract-v1"
PLAN_SCHEMA = "radio-source-bound-runtime-materialization-plan-v1"
AUTHORITY_KEYS = (
    "acquisition_authorized", "allocation_created", "cas_qualified", "certificate_issued",
    "download_authorized", "execution_authorized", "hosted_transport_qualified",
    "installation_authorized", "metadata_capture_dispatch_authorized", "reservation_authorized",
    "rng_authorized", "runtime_import_authorized", "runtime_qualified",
    "scientific_execution_authorized", "source_contract_admitted", "spectral_access_authorized",
)
PACKAGE_VERSIONS = {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5plugin": "7.1.0"}
MAXIMA = {"files": 2048, "per_file_bytes": 67108864, "read_bytes": 536870912,
          "maps_bytes": 1048576, "module_count": 4096, "result_bytes": 4194304,
          "elf_program_headers": 1024, "elf_dynamic_entries": 4096,
          "elf_strings": 512, "elf_string_bytes": 65536}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")

class CaptureError(ValueError):
    pass

class ElfCaptureError(CaptureError):
    """One selected ELF rejected; no observation/certificate was produced."""
    def __init__(self, message, context):
        super().__init__(message)
        self.context = context


def _bounded_parser_context(value):
    """Copy small primitive context only; no arbitrary exception-object dump."""
    nodes = 0
    def copy(item, depth):
        nonlocal nodes
        nodes += 1
        if nodes > 512 or depth > 5:
            raise ValueError("context structural bound")
        if item is None or type(item) is bool:
            return item
        if type(item) is int and -(1 << 64) < item < (1 << 64):
            return item
        if type(item) is str and len(item) <= 512:
            return item
        if type(item) is list and len(item) <= 16:
            return [copy(child, depth + 1) for child in item]
        if type(item) is dict and len(item) <= 32 and all(type(key) is str and len(key) <= 64 for key in item):
            return {key: copy(child, depth + 1) for key, child in item.items()}
        raise ValueError("context primitive bound")
    try:
        context = copy(value, 0)
        if type(context) is not dict or context.get("schema") != "radio-elf-metadata-error-context-v1":
            return None
        if len(_canonical(context)) > 24576:
            return None
        return context
    except (ValueError, TypeError, RecursionError):
        return None


def _selected_elf_failure(entry, exc, *, parser_pin=None, collector_pin=None, injected=False):
    context = _bounded_parser_context(getattr(exc, "context", None))
    record = {"schema": "radio-selected-elf-error-context-v1",
              "status": "CLOSED_FAILED", "path": entry["path"],
              "file_bytes": entry["bytes"], "file_sha256": entry["sha256"],
              "role": entry["role"], "parser_exception": type(exc).__name__[:128],
              "parser_source_sha256": None if parser_pin is None else parser_pin["sha256"],
              "parser_source_bytes": None if parser_pin is None else parser_pin["bytes"],
              "collector_source_sha256": None if collector_pin is None else collector_pin["sha256"],
              "parser_injected_synthetic_only": injected,
              "parser_reason": str(exc)[:512],
              "parser_context_status": "SUPPORTED_BOUNDED_STRUCTURED" if context is not None else "UNAVAILABLE_OR_UNSUPPORTED",
              "parser_context": context, "observation_adopted": False,
              "authority": {key: False for key in AUTHORITY_KEYS}}
    # Path admission bounds4096 code points, parser context24576 ASCII bytes;
    # the complete deterministic JSON record remains within this fixed ceiling.
    if len(_canonical(record)) > 65536:
        record["parser_context"] = None
        record["parser_context_status"] = "UNAVAILABLE_OR_UNSUPPORTED"
    return ElfCaptureError("selected ELF metadata rejected", record)

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def _json(raw, pin, cap, name):
    if type(raw) is not bytes or len(raw) > cap or not HEX64.fullmatch(pin or ""):
        raise CaptureError(name + " raw bytes/pin/cap")
    if hashlib.sha256(raw).hexdigest() != pin:
        raise CaptureError(name + " outer pin mismatch")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise CaptureError(name + " duplicate key")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(CaptureError("nonfinite JSON")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CaptureError(name + " malformed JSON") from exc

def _path(value):
    if type(value) is not str or not value.startswith("/") or len(value) > 4096 or "\x00" in value:
        raise CaptureError("absolute path required")
    p = PurePosixPath(value)
    if str(p) != value or ".." in p.parts or value == "/":
        raise CaptureError("noncanonical absolute path")
    return value

def _exact(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise CaptureError(name + " exact fields required")

def _integer(value, maximum, name):
    if type(value) is not int or value < 1 or value > maximum:
        raise CaptureError(name + " finite positive cap")
    return value

def validate_inputs(contract_raw, contract_pin, plan_raw, plan_pin):
    """Pure pin/schema admission; does not authenticate a service or grant science."""
    contract = _json(contract_raw, contract_pin, 262144, "contract")
    plan = _json(plan_raw, plan_pin, 262144, "plan")
    _exact(contract, ("schema", "evidence_domain", "capture_identity", "capture_authorized",
                     "externally_bound_publication_required", "activation_required", "plan_sha256", "python_path",
                     "python_sha256", "files", "imports", "import_paths", "loader_paths",
                     "distributions", "missing_paths", "limits"), "contract")
    if contract["schema"] != SCHEMA or contract["evidence_domain"] not in (
            "metadata-capture-only", "synthetic-test-fixture") or contract["capture_authorized"] is not True:
        raise CaptureError("explicit metadata capture contract required")
    for key in ("capture_identity", "python_sha256"):
        if not HEX64.fullmatch(contract[key] if type(contract[key]) is str else ""):
            raise CaptureError(key + " pin")
    if contract["externally_bound_publication_required"] is not True or contract["activation_required"] is not True:
        raise CaptureError("detached publication and fresh activation required")
    if contract["plan_sha256"] != plan_pin:
        raise CaptureError("plan linkage")
    if plan.get("schema") != PLAN_SCHEMA or plan.get("status") != "PENDING" or plan.get("evidence_domain") != "inert-metadata-preparation-only":
        raise CaptureError("inert PENDING original plan required")
    if plan.get("authority") != {key: False for key in AUTHORITY_KEYS}:
        raise CaptureError("original plan authority drift")
    expected = {"python": "3.12.14", **PACKAGE_VERSIONS, "hdf5": "2.0.0"}
    if plan.get("materialization", {}).get("required_historical_versions") != expected:
        raise CaptureError("retained target version drift")
    platform_requirements = plan["materialization"].get("platform_requirements")
    if platform_requirements != {"endianness": "little", "machine": "x86_64",
                                 "minimum_glibc_for_all_selected_wheels": "2.28", "python_abi": "cp312"}:
        raise CaptureError("retained platform requirement drift")
    _path(contract["python_path"])
    _exact(contract["limits"], MAXIMA, "limits")
    for key, maximum in MAXIMA.items():
        _integer(contract["limits"][key], maximum, key)
    files = contract["files"]
    if type(files) is not list or not files or len(files) > contract["limits"]["files"]:
        raise CaptureError("file inventory cap")
    paths = set()
    for entry in files:
        _exact(entry, ("path", "role", "bytes", "sha256", "mode"), "file pin")
        path = _path(entry["path"])
        if path in paths or entry["role"] not in ("code", "input", "runtime", "elf", "plugin"):
            raise CaptureError("file duplicate/role")
        paths.add(path)
        if type(entry["bytes"]) is not int or entry["bytes"] < 0 or entry["bytes"] > contract["limits"]["per_file_bytes"]:
            raise CaptureError("file size finite nonnegative exact integer")
        if not HEX64.fullmatch(entry["sha256"] if type(entry["sha256"]) is str else ""):
            raise CaptureError("file sha256")
        if entry["mode"] not in ("100644", "100755"):
            raise CaptureError("regular file mode")
    if sum(x["bytes"] for x in files) * 2 + contract["limits"]["maps_bytes"] * 2 > contract["limits"]["read_bytes"]:
        raise CaptureError("before/after inventory exceeds read allocation")
    python = [x for x in files if x["path"] == contract["python_path"]]
    if len(python) != 1 or python[0]["sha256"] != contract["python_sha256"]:
        raise CaptureError("interpreter must be an exact selected file")
    for key in ("import_paths", "loader_paths"):
        if type(contract[key]) is not list or len(contract[key]) > 32 or len(set(contract[key])) != len(contract[key]):
            raise CaptureError(key + " finite unique paths")
        for path in contract[key]:
            _path(path)
    if type(contract["imports"]) is not list or len(contract["imports"]) > 3:
        raise CaptureError("optional exact package imports")
    if contract["evidence_domain"] != "synthetic-test-fixture" and contract["imports"]:
        raise CaptureError("native imports deferred pending preauthenticated complete closure")
    order = []
    for package in contract["imports"]:
        _exact(package, ("name", "origin", "version"), "package import")
        name = package["name"]
        if name not in PACKAGE_VERSIONS or package["version"] != PACKAGE_VERSIONS[name]:
            raise CaptureError("retained package import version")
        origin = _path(package["origin"])
        if origin not in paths or not contract["import_paths"]:
            raise CaptureError("package origin must be pinned under explicit paths")
        order.append(name)
    if order != [x for x in PACKAGE_VERSIONS if x in order] or len(order) != len(set(order)):
        raise CaptureError("fixed unique package import order")
    if type(contract["distributions"]) is not list or len(contract["distributions"]) > 3:
        raise CaptureError("static distribution count")
    distributions = set()
    for distribution in contract["distributions"]:
        _exact(distribution, ("name", "metadata_path", "wheel_path", "record_path", "expected_version"), "static distribution")
        name = distribution["name"]
        if name not in PACKAGE_VERSIONS or name in distributions or distribution["expected_version"] != PACKAGE_VERSIONS[name]:
            raise CaptureError("static distribution name/version")
        distributions.add(name)
        for key in ("metadata_path", "wheel_path", "record_path"):
            if _path(distribution[key]) not in paths:
                raise CaptureError("static distribution bytes must be pinned")
    if type(contract["missing_paths"]) is not list or len(contract["missing_paths"]) > 16 or len(set(contract["missing_paths"])) != len(contract["missing_paths"]):
        raise CaptureError("finite exact missing paths")
    for path in contract["missing_paths"]:
        if _path(path) in paths:
            raise CaptureError("missing path overlaps pinned existing path")
    return contract, plan

def validate_witness(raw, pin, contract_pin, plan_pin, capture_identity):
    """Consume an externally authenticated detached gate witness, not a CAS law.

The parent gate checks complete public byte readback and one-shot activation.
This child binds its own raw input pin to that already authenticated witness;
these JSON fields alone are not an independent authentication mechanism.
"""
    witness = _json(raw, pin, 2097152, "admission witness")
    _exact(witness, ("schema", "repository", "branch", "prepared_commit", "prepared_tree",
                     "activation_commit", "activation_tree", "activation_parent", "activation_changed_path",
                     "contract_sha256", "publication_files", "capture_identity", "collector_contract_sha256",
                     "plan_sha256", "activation_sha256", "provenance"), "detached witness")
    if witness.get("schema") != "radio-runtime-metadata-capture-publication-readback-v1":
        raise CaptureError("detached witness schema")
    for key in ("prepared_commit", "prepared_tree", "activation_commit", "activation_tree"):
        if not HEX40.fullmatch(witness.get(key, "") if type(witness.get(key)) is str else ""):
            raise CaptureError("detached witness " + key)
    if witness.get("activation_parent") != witness["prepared_commit"]:
        raise CaptureError("detached activation parent")
    if witness.get("repository") != "andersenmartin-blip/setisearch" or witness.get("branch") != "m43-support-qualification":
        raise CaptureError("detached witness repository/branch")
    if witness.get("capture_identity") != capture_identity or witness.get("plan_sha256") != plan_pin:
        raise CaptureError("detached capture identity/plan linkage")
    if not HEX64.fullmatch(witness.get("contract_sha256", "") if type(witness.get("contract_sha256")) is str else ""):
        raise CaptureError("detached supervisor contract pin")
    if type(witness["publication_files"]) is not list or not any(type(item) is dict and item.get("sha256") == contract_pin for item in witness["publication_files"]):
        raise CaptureError("detached collector contract publication missing")
    if witness.get("collector_contract_sha256") != contract_pin:
        raise CaptureError("detached collector contract linkage")
    if not HEX64.fullmatch(witness.get("activation_sha256", "") if type(witness.get("activation_sha256")) is str else ""):
        raise CaptureError("detached activation raw pin")
    return {"witness_sha256": pin, "prepared_commit": witness["prepared_commit"],
            "prepared_tree": witness["prepared_tree"], "activation_commit": witness["activation_commit"],
            "activation_tree": witness["activation_tree"], "activation_sha256": witness["activation_sha256"],
            "collector_contract_sha256": contract_pin, "supervisor_contract_sha256": witness["contract_sha256"],
            "plan_sha256": plan_pin, "capture_identity": capture_identity, "parent_gate_authentication_required": True}

class ReadLedger:
    def __init__(self, limit):
        self.limit = limit
        self.read_bytes = 0
        self.regular_file_read_bytes = 0
        self.proc_maps_read_bytes = 0
        self.cli_input_read_bytes = 0
    def charge(self, count, category):
        if type(count) is not int or count < 0 or self.read_bytes + count > self.limit:
            raise CaptureError("read byte allocation exhausted")
        self.read_bytes += count
        setattr(self, category, getattr(self, category) + count)
    def report(self):
        return {"read_bytes": self.read_bytes, "regular_file_read_bytes": self.regular_file_read_bytes,
                "proc_maps_read_bytes": self.proc_maps_read_bytes, "cli_input_read_bytes": self.cli_input_read_bytes,
                "accounting_scope": "explicit selected application reads only; implicit Python loader, kernel and provider IO excluded",
                "read_limit_bytes": self.limit, "retained_artifact_bytes_are_separate": True}

def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)

def read_selected_file(entry, ledger, *, keep_bytes=False, after_read=None, require_hash=True):
    """Held nofollow descriptor with every named directory checked for drift."""
    path = _path(entry["path"])
    descriptors = []
    bindings = []
    try:
        parent = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(parent)
        for name in PurePosixPath(path).parts[1:-1]:
            descriptor = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                 dir_fd=parent)
            descriptors.append(descriptor)
            held = os.fstat(descriptor)
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if _identity(held) != _identity(named):
                raise CaptureError("directory named identity mismatch")
            bindings.append((parent, name, descriptor, _identity(held)))
            parent = descriptor
        name = PurePosixPath(path).name
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        expected_mode = 0o644 if entry["mode"] == "100644" else 0o755
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) != expected_mode:
            raise CaptureError("selected file regular/mode/sole-link law")
        if before.st_size != entry["bytes"]:
            raise CaptureError("selected file size mismatch")
        digest = hashlib.sha256()
        remaining = before.st_size
        chunks = []
        while remaining:
            count = min(65536, remaining)
            if ledger.read_bytes + count > ledger.limit:
                raise CaptureError("read allocation before syscall")
            chunk = os.read(descriptor, count)
            ledger.charge(len(chunk), "regular_file_read_bytes")
            if not chunk:
                raise CaptureError("selected file short read")
            remaining -= len(chunk)
            digest.update(chunk)
            if keep_bytes:
                chunks.append(chunk)
        if after_read is not None:
            after_read(path)
        after = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if _identity(before) != _identity(after) or _identity(before) != _identity(named):
            raise CaptureError("selected file held/named drift")
        for directory_parent, directory_name, directory_fd, identity in bindings:
            if _identity(os.fstat(directory_fd)) != identity or _identity(os.stat(
                    directory_name, dir_fd=directory_parent, follow_symlinks=False)) != identity:
                raise CaptureError("selected directory held/named drift")
        observed_hash = digest.hexdigest()
        if require_hash and observed_hash != entry["sha256"]:
            raise CaptureError("selected file hash mismatch")
        result = {"path": path, "role": entry["role"], "bytes": before.st_size,
                  "sha256": observed_hash, "mode": entry["mode"], "device": before.st_dev,
                  "inode": before.st_ino, "mtime_ns": before.st_mtime_ns, "ctime_ns": before.st_ctime_ns}
        return result, b"".join(chunks) if keep_bytes else None
    except OSError as exc:
        raise CaptureError("selected file unavailable: " + str(exc.errno)) from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)

def parse_maps(raw, max_bytes=1048576, max_entries=16384):
    """Parse actual Linux proc map lines; keep file identity and unknown mappings."""
    if type(raw) is not bytes or len(raw) > max_bytes:
        raise CaptureError("maps bytes cap")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise CaptureError("maps encoding") from exc
    result = []
    for line in text.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 5 or len(result) >= max_entries:
            raise CaptureError("maps malformed/count cap")
        addresses, permissions, offset, device, inode = parts[:5]
        pathname = parts[5] if len(parts) == 6 else None
        if not re.fullmatch(r"[0-9a-f]+-[0-9a-f]+", addresses) or not re.fullmatch(r"[r-][w-][x-][ps]", permissions):
            raise CaptureError("maps address/permissions")
        if not re.fullmatch(r"[0-9a-f]+", offset) or not re.fullmatch(r"[0-9a-f]+:[0-9a-f]+", device) or not inode.isdecimal():
            raise CaptureError("maps offset/device/inode")
        start, end = [int(x, 16) for x in addresses.split("-")]
        if start >= end or end > 2 ** 64 - 1 or int(offset, 16) > 2 ** 64 - 1:
            raise CaptureError("maps numeric extent")
        major, minor = [int(x, 16) for x in device.split(":")]
        result.append({"start": start, "end": end, "permissions": permissions, "offset": int(offset, 16),
                       "device_major": major, "device_minor": minor, "inode": int(inode), "path": pathname,
                       "deleted": bool(pathname and pathname.endswith(" (deleted)"))})
    return result

def resolve_dependencies(elf_inventory, mappings, file_inventory, loader_paths):
    """Report compatible loaded candidates without inventing loader search traces.

RUNPATH is direct-dependency metadata only. Supplied paths are an explicit
allowlist, not a claim about LD_LIBRARY_PATH, ld.so.cache or default ordering.
"""
    selected = {x["path"]: x for x in file_inventory}
    loaded = set()
    for mapping in mappings:
        path = mapping["path"]
        entry = selected.get(path)
        if entry and not mapping["deleted"] and mapping["inode"] == entry["inode"] and (
                mapping["device_major"], mapping["device_minor"]) == (os.major(entry["device"]), os.minor(entry["device"])):
            loaded.add(path)
    result = []
    for path, metadata in sorted(elf_inventory.items()):
        needed = metadata.get("needed", [])
        for library in needed:
            candidates = []
            for candidate, candidate_metadata in elf_inventory.items():
                if candidate in loaded and (PurePosixPath(candidate).name == library or candidate_metadata.get("soname") == library):
                    candidates.append(candidate)
            candidates = sorted(set(candidates))
            supplied = [str(PurePosixPath(directory) / library) for directory in loader_paths
                        if str(PurePosixPath(directory) / library) in selected]
            result.append({"consumer": path, "needed": library, "loaded_compatible_candidates": candidates,
                           "allowlisted_selected_candidates": supplied,
                           "status": "UNIQUE_OBSERVED_COMPATIBLE_CANDIDATE" if len(candidates) == 1 else (
                               "AMBIGUOUS_OBSERVED_CANDIDATES" if candidates else "UNRESOLVED"),
                           "rpath": metadata.get("rpath"), "runpath": metadata.get("runpath"),
                           "runpath_direct_dependencies_only": True, "observed_loader_edge_proven": False,
                           "complete_loader_search_order_proven": False})
    return result

def observe_distribution(distribution, raw_inventory):
    """Read only pinned static METADATA/WHEEL/RECORD text, never RECORD paths."""
    headers = {}
    for key in ("metadata_path", "wheel_path"):
        raw = raw_inventory[distribution[key]]
        if len(raw) > 2097152:
            raise CaptureError("static distribution metadata cap")
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeError as exc:
            raise CaptureError("static distribution encoding") from exc
        fields = {}
        for line in text.splitlines():
            if not line:
                break
            if line.startswith((" ", "\t")):
                continue
            name, separator, value = line.partition(":")
            if not separator:
                raise CaptureError("static distribution malformed header")
            fields.setdefault(name, []).append(value.strip())
        headers[key] = fields
    metadata = headers["metadata_path"]
    if metadata.get("Name") != [distribution["name"]] or len(metadata.get("Version", [])) != 1:
        raise CaptureError("static distribution identity headers")
    version = metadata["Version"][0]
    wheel = headers["wheel_path"]
    if len(wheel.get("Wheel-Version", [])) != 1 or not wheel.get("Tag"):
        raise CaptureError("static WHEEL required headers")
    record_raw = raw_inventory[distribution["record_path"]]
    if len(record_raw) > 2097152:
        raise CaptureError("static RECORD cap")
    try:
        rows = list(csv.reader(io.StringIO(record_raw.decode("utf-8", "strict"))))
    except (UnicodeError, csv.Error) as exc:
        raise CaptureError("static RECORD encoding/CSV") from exc
    if len(rows) > 65536 or any(len(row) != 3 for row in rows):
        raise CaptureError("static RECORD row shape/cap")
    # RECORD contents are counted and hashed only. No member path is traversed.
    return {"name": distribution["name"], "observed_static_version": version,
            "required_version": distribution["expected_version"],
            "version_matches_retained_target": version == distribution["expected_version"],
            "wheel_version": wheel["Wheel-Version"][0], "wheel_tags": wheel["Tag"],
            "record_rows": len(rows), "record_member_files_opened": 0,
            "package_imported": False, "complete_package_custody_proven": False,
            "metadata_path": distribution["metadata_path"], "wheel_path": distribution["wheel_path"],
            "record_path": distribution["record_path"]}

class LocalCaptureBackend:
    """Only used by an explicitly admitted capture; no constructor IO."""
    def host(self):
        uname = os.uname()
        libc = os.confstr("CS_GNU_LIBC_VERSION") if "CS_GNU_LIBC_VERSION" in os.confstr_names else None
        return {"python": ".".join(str(x) for x in sys.version_info[:3]), "python_full": sys.version,
                "implementation": sys.implementation.name, "cache_tag": sys.implementation.cache_tag,
                "executable": sys.executable, "executable_realpath": os.path.realpath(sys.executable),
                "system": uname.sysname, "release": uname.release, "machine": uname.machine,
                "endianness": sys.byteorder, "libc": libc,
                "isolated": bool(sys.flags.isolated), "no_site": bool(sys.flags.no_site),
                "dont_write_bytecode": bool(sys.dont_write_bytecode), "import_paths": list(sys.path)}
    def file(self, entry, ledger, keep_bytes):
        return read_selected_file(entry, ledger, keep_bytes=keep_bytes)
    def maps(self, ledger, limit):
        # procfs has no trustworthy regular-file size. Never follow its leaf link.
        descriptor = os.open("/proc/self/maps", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            pieces = []
            used = 0
            while True:
                remaining = min(limit - used, ledger.limit - ledger.read_bytes)
                if remaining <= 0:
                    raise CaptureError("proc maps allocation exhausted before EOF")
                piece = os.read(descriptor, min(65536, remaining))
                ledger.charge(len(piece), "proc_maps_read_bytes")
                if not piece:
                    break
                pieces.append(piece)
                used += len(piece)
            return b"".join(pieces)
        finally:
            os.close(descriptor)
    def modules(self):
        return {name: getattr(module, "__file__", None) for name, module in tuple(sys.modules.items())}
    def availability(self, paths):
        result = []
        for path in paths:
            try:
                info = os.stat(path, follow_symlinks=False)
                result.append({"path": path, "status": "PRESENT_AT_EXACT_PATH", "mode": info.st_mode,
                               "inode": info.st_ino, "device": info.st_dev})
            except FileNotFoundError:
                result.append({"path": path, "status": "MISSING_AT_EXACT_PATH"})
            except OSError as exc:
                result.append({"path": path, "status": "UNAVAILABLE_AT_EXACT_PATH", "errno": exc.errno})
        return result
    def import_packages(self, packages, paths):
        raise CaptureError("native imports deferred pending preauthenticated complete closure")

def capture(contract_raw, contract_pin, plan_raw, plan_pin, *, admission_witness_raw=None,
            admission_witness_pin=None, backend=None, elf_parser=None, initial_cli_read_bytes=0):
    """Produce detached PENDING observations; external supervision remains required."""
    contract, plan = validate_inputs(contract_raw, contract_pin, plan_raw, plan_pin)
    witness_binding = validate_witness(admission_witness_raw, admission_witness_pin, contract_pin, plan_pin, contract["capture_identity"])
    if backend is not None and contract["evidence_domain"] != "synthetic-test-fixture":
        raise CaptureError("injected backend only in explicit synthetic fixture")
    backend = backend if backend is not None else LocalCaptureBackend()
    limits = contract["limits"]
    ledger = ReadLedger(limits["read_bytes"])
    if type(initial_cli_read_bytes) is not int or initial_cli_read_bytes < 0 or initial_cli_read_bytes > 262144 * 2 + 2097152:
        raise CaptureError("finite CLI admission read count")
    if initial_cli_read_bytes + sum(entry["bytes"] for entry in contract["files"]) * 2 + limits["maps_bytes"] * 2 > ledger.limit:
        raise CaptureError("CLI plus complete selected read allocation")
    ledger.charge(initial_cli_read_bytes, "cli_input_read_bytes")
    before_host = backend.host()
    mismatches = []
    if before_host.get("executable_realpath") != contract["python_path"]:
        raise CaptureError("running interpreter differs from pinned path")
    if before_host.get("python") != "3.12.14":
        mismatches.append({"identity": "python", "required": "3.12.14", "observed": before_host.get("python")})
    for key, target in (("machine", "x86_64"), ("endianness", "little"), ("cache_tag", "cpython-312"), ("system", "Linux")):
        if before_host.get(key) != target:
            mismatches.append({"identity": key, "required": target, "observed": before_host.get(key)})
    libc = before_host.get("libc")
    match = re.fullmatch(r"glibc ([0-9]+)\.([0-9]+)", libc or "")
    if match is None or tuple(int(x) for x in match.groups()) < (2, 28):
        mismatches.append({"identity": "libc", "required": "glibc>=2.28", "observed": libc})
    if any(before_host.get(x) is not True for x in ("isolated", "no_site", "dont_write_bytecode")):
        raise CaptureError("isolated no-site no-bytecode interpreter required")
    maps_before_raw = backend.maps(ledger, limits["maps_bytes"])
    maps_before = parse_maps(maps_before_raw, limits["maps_bytes"])
    before_files = []
    elf_inventory = {}
    raw_inventory = {}
    distribution_paths = {distribution[key] for distribution in contract["distributions"]
                          for key in ("metadata_path", "wheel_path", "record_path")}
    helper_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "elf_metadata.py")
    for entry in contract["files"]:
        wants_elf = entry["role"] in ("elf", "plugin") or entry["path"] == contract["python_path"]
        observation, raw = backend.file(entry, ledger, wants_elf or entry["path"] == helper_path or entry["path"] in distribution_paths)
        before_files.append(observation)
        if raw is not None:
            raw_inventory[entry["path"]] = raw
    parser = elf_parser
    injected_parser = parser is not None
    parser_pin = next((entry for entry in contract["files"] if entry["path"] == helper_path), None)
    collector_pin = next((entry for entry in contract["files"] if entry["path"] == os.path.abspath(__file__)), None)
    if parser is None:
        if helper_path not in raw_inventory or not any(entry["path"] == os.path.abspath(__file__) for entry in contract["files"]):
            raise CaptureError("collector and ELF helper must be externally pinned selected code")
        namespace = {"__name__": "_pinned_capture_elf_metadata", "__file__": helper_path}
        exec(compile(raw_inventory[helper_path], helper_path, "exec"), namespace)
        parser = namespace.get("parse_elf")
        if not callable(parser):
            raise CaptureError("pinned ELF helper interface")
    elif contract["evidence_domain"] != "synthetic-test-fixture":
        raise CaptureError("injected ELF parser only in synthetic fixture")
    for entry in contract["files"]:
        wants_elf = entry["role"] in ("elf", "plugin") or entry["path"] == contract["python_path"]
        if wants_elf:
            try:
                elf_inventory[entry["path"]] = parser(raw_inventory[entry["path"]], max_bytes=limits["per_file_bytes"],
                    max_program_headers=limits["elf_program_headers"], max_dynamic_entries=limits["elf_dynamic_entries"],
                    max_strings=limits["elf_strings"], max_string_bytes=limits["elf_string_bytes"])
            except Exception as exc:
                raise _selected_elf_failure(entry, exc,
                    parser_pin=None if injected_parser else parser_pin,
                    collector_pin=collector_pin, injected=injected_parser) from exc
    static_distributions = [observe_distribution(distribution, raw_inventory) for distribution in contract["distributions"]]
    for distribution in static_distributions:
        if not distribution["version_matches_retained_target"]:
            mismatches.append({"identity": "static_distribution:" + distribution["name"],
                               "required": distribution["required_version"],
                               "observed": distribution["observed_static_version"]})
    availability_before = backend.availability(contract["missing_paths"])
    before_modules = backend.modules()
    if len(before_modules) > limits["module_count"]:
        raise CaptureError("before module count cap")
    if any(name in before_modules for name in PACKAGE_VERSIONS):
        raise CaptureError("ambient native package present before capture")
    packages = {name: {"status": "MISSING_OR_NOT_IMPORTED", "version": None} for name in (*PACKAGE_VERSIONS, "hdf5")}
    # Host mismatch is recorded honestly and prevents incompatible native import.
    if contract["imports"] and not mismatches:
        observed_packages, imported_modules = backend.import_packages(contract["imports"], contract["import_paths"])
        packages.update(observed_packages)
        if imported_modules and len(imported_modules) > limits["module_count"]:
            raise CaptureError("import module count cap")
    after_modules = backend.modules()
    if len(after_modules) > limits["module_count"]:
        raise CaptureError("after module count cap")
    selected_paths = {entry["path"] for entry in contract["files"]}
    unexpected_module_files = sorted({path for name, path in after_modules.items()
        if name.split(".", 1)[0] in PACKAGE_VERSIONS and type(path) is str and path not in selected_paths})
    for name, target in {**PACKAGE_VERSIONS, "hdf5": "2.0.0"}.items():
        observed = packages[name]["version"]
        if observed != target:
            mismatches.append({"identity": name, "required": target, "observed": observed})
    after_files = []
    for entry in contract["files"]:
        observation, _ = backend.file(entry, ledger, False)
        after_files.append(observation)
    if before_files != after_files:
        raise CaptureError("before/after selected inventory drift")
    maps_after_raw = backend.maps(ledger, limits["maps_bytes"])
    maps_after = parse_maps(maps_after_raw, limits["maps_bytes"])
    availability_after = backend.availability(contract["missing_paths"])
    if availability_before != availability_after:
        raise CaptureError("exact path availability drift")
    after_host = backend.host()
    if before_host != after_host:
        raise CaptureError("host identity drift")
    selected_elf_paths = set(elf_inventory)
    loaded_unselected = sorted({mapping["path"] for mapping in maps_after if mapping["path"] and
        mapping["path"].startswith("/") and mapping["path"] not in selected_elf_paths})
    result = {"schema": "radio-runtime-metadata-capture-observation-v1", "status": "OBSERVED_METADATA_ONLY",
        "admission_status": "PENDING_MISSING_INPUTS" if mismatches else "PENDING_FULL_CLOSURE",
        "evidence_domain": contract["evidence_domain"], "capture_identity": contract["capture_identity"],
        "contract_sha256": contract_pin, "plan_sha256": plan_pin,
        "detached_admission_binding": witness_binding,
        "authority": {key: False for key in AUTHORITY_KEYS},
        "authority_scope": "unchanged original materialization plan scientific authority",
        "original_materialization_plan_authority": {key: False for key in AUTHORITY_KEYS},
        "engineering_capture_authorized": contract["evidence_domain"] == "metadata-capture-only",
        "engineering_authorization_authentication_owner": "external one-shot parent gate",
        "host_before": before_host, "host_after": after_host,
        "required_target_versions": plan["materialization"]["required_historical_versions"],
        "packages": packages, "static_distributions": static_distributions,
        "exact_path_availability_before": availability_before, "exact_path_availability_after": availability_after,
        "static_distribution_metadata_does_not_prove_loaded_package": True,
        "mismatches": mismatches, "selected_files_before": before_files,
        "selected_files_after": after_files, "elf_metadata": elf_inventory,
        "mappings_before": maps_before, "mappings_after": maps_after,
        "maps_raw_before_utf8": maps_before_raw.decode("utf-8"),
        "maps_raw_after_utf8": maps_after_raw.decode("utf-8"),
        "maps_raw_before_sha256": hashlib.sha256(maps_before_raw).hexdigest(),
        "maps_raw_after_sha256": hashlib.sha256(maps_after_raw).hexdigest(),
        "module_origins_before": before_modules, "module_origins_after": after_modules,
        "unexpected_package_module_files": unexpected_module_files,
        "loaded_unselected_file_paths": loaded_unselected,
        "dependency_observations": resolve_dependencies(elf_inventory, maps_after, after_files, contract["loader_paths"]),
        "read_ledger": ledger.report(),
        "limitations": {"complete_runtime_closure_qualified": False, "full_transitive_loader_trace_proven": False,
            "observed_hashes_are_not_external_trust_anchors": True, "parent_supervision_required": True,
            "peak_memory_certified": False, "hdf5_filter_case_laws_run": False,
            "dataset_or_spectrum_opened": False, "wheel_downloaded_or_installed": False,
            "scientific_freeze_issued": False}}
    if len(_canonical(result)) > limits["result_bytes"]:
        raise CaptureError("result artifact cap")
    # JSON roundtrip detaches observations from all caller/backend-owned containers.
    return json.loads(_canonical(result))

def _raw_cli_file(path, cap):
    path = _path(path)
    info = os.stat(path, follow_symlinks=False)
    if info.st_size < 1 or info.st_size > cap:
        raise CaptureError("CLI input cap")
    entry = {"path": path, "role": "input", "bytes": info.st_size,
             "sha256": "0" * 64, "mode": "100644"}
    _, raw = read_selected_file(entry, ReadLedger(cap), keep_bytes=True, require_hash=False)
    # The outer raw SHA256 is checked immediately by validate_inputs. This
    # bounded read does not manufacture an expected trust pin from observed data.
    return raw

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--admission-witness", required=True)
    parser.add_argument("--admission-witness-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        contract_raw = _raw_cli_file(args.contract, 262144)
        plan_raw = _raw_cli_file(args.plan, 262144)
        witness_raw = _raw_cli_file(args.admission_witness, 2097152)
        result = capture(contract_raw, args.contract_sha256, plan_raw, args.plan_sha256,
                         admission_witness_raw=witness_raw, admission_witness_pin=args.admission_witness_sha256,
                         initial_cli_read_bytes=len(contract_raw) + len(plan_raw) + len(witness_raw))
        sys.stdout.buffer.write(_canonical(result) + b"\n")
        return 0
    except Exception as exc:
        sys.stderr.write("CLOSED_FAILED " + type(exc).__name__ + ": " + str(exc)[:512] + "\n")
        if isinstance(exc, ElfCaptureError):
            sys.stderr.write("ELF_ERROR_CONTEXT " + _canonical(exc.context).decode("ascii") + "\n")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
