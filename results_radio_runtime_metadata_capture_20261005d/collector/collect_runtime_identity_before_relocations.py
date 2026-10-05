"""Prospective, metadata-only NumPy/HDF5 identity input collector.

Importing this file imports stdlib only. Native package imports are confined to
the explicit CLI activation path. This is not a scientific admission gate,
custody certificate, installer, acquisition tool, or supervisor.
"""
import argparse
import base64
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import struct
import sys
import time

SCHEMA = "seti-runtime-identity-inputs-v1"
COHORT = {"numpy": "2.3.5", "h5py": "3.16.0", "hdf5plugin": "7.1.0"}
MAX_READ_BYTES = 512 * 1024 * 1024
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_MAP_BYTES = 2 * 1024 * 1024
MAX_FILES = 12000
NO_AUTHORITY = {key: False for key in (
    "scientific_execution_authorized", "spectral_access_authorized",
    "runtime_qualified", "source_closure_qualified", "native_custody_qualified",
    "cas_qualified", "certificate_issued")}


class Refusal(Exception):
    pass


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"


def identity(st):
    return {"device": st.st_dev, "inode": st.st_ino, "mode": st.st_mode,
            "links": st.st_nlink, "bytes": st.st_size,
            "mtime_ns": st.st_mtime_ns, "ctime_ns": st.st_ctime_ns}


class BoundedReader:
    """Explicit reads only; loader/import reads are owned by the supervisor."""
    def __init__(self, limit=MAX_READ_BYTES):
        self.limit = limit
        self.charged_bytes = 0
        self.cache = {}

    def file(self, path, *, cap=None):
        path = Path(path)
        flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
        fd = os.open(path, flags)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise Refusal("regular metadata/native file required")
            if cap is not None and before.st_size > cap:
                raise Refusal("per-file read cap")
            if before.st_size > self.limit - self.charged_bytes:
                raise Refusal("explicit read budget cannot fit file")
            chunks, received = [], 0
            while received < before.st_size:
                remaining = self.limit - self.charged_bytes
                if remaining <= 0:
                    raise Refusal("explicit read budget exhausted")
                chunk = os.read(fd, min(1024 * 1024, remaining, before.st_size - received))
                self.charged_bytes += len(chunk)
                if not chunk:
                    break
                chunks.append(chunk)
                received += len(chunk)
                if cap is not None and received > cap:
                    raise Refusal("per-file read cap exceeded")
            after = os.fstat(fd)
            named = os.stat(path, follow_symlinks=False)
            if identity(before) != identity(after) or identity(named) != identity(after):
                raise Refusal("file identity changed during read")
            raw = b"".join(chunks)
            if len(raw) != before.st_size:
                raise Refusal("file size mismatch")
            return raw, identity(after)
        finally:
            os.close(fd)

    def native(self, path, *, require_elf=True):
        """Hash full named ELF bytes once; later observations recheck identity.

        Reuse is reported, never described as another complete byte read. Named
        identity is not protection against changes in ancestor directories.
        """
        path = str(Path(path).resolve(strict=True))
        current = identity(os.stat(path, follow_symlinks=False))
        cached = self.cache.get(path)
        if cached is not None and cached["identity"] == current:
            if require_elf and cached["elf"] is None:
                raise Refusal("named native file is not ELF")
            return {**cached, "hash_reused_after_identity_recheck": True}
        raw, observed = self.file(path)
        is_elf = raw.startswith(b"\x7fELF")
        if require_elf and not is_elf:
            raise Refusal("named native file is not ELF")
        obj = {"path": path, "identity": observed, "bytes": len(raw),
               "sha256": hashlib.sha256(raw).hexdigest(),
               "elf": elf_dynamic(raw) if is_elf else None,
               "hash_reused_after_identity_recheck": False}
        self.cache[path] = obj
        return dict(obj)


def _file_backed_virtual_bytes(raw, loads, address, length):
    """Resolve one contiguous virtual interval through exact file-backed spans.

    PT_LOAD boundaries need not coincide with a dynamic string-table boundary.
    Every virtual byte must have exactly one file-offset translation. Overlapping
    headers are allowed only when those translations are identical; equal bytes
    at different offsets do not remove an ambiguity. Zero-filled memory is not
    a source of file bytes. The caller already validated all segment bounds.
    """
    if (type(address) is not int or type(length) is not int or address < 0 or
            length <= 0 or length > len(raw)):
        raise Refusal("dynamic string table interval outside finite file bound")
    end = address + length
    boundaries = {address, end}
    for va, file_size, file_offset in loads:
        if (type(va) is not int or type(file_size) is not int or
                type(file_offset) is not int or min(va, file_size, file_offset) < 0 or
                file_offset + file_size > len(raw)):
            raise Refusal("ELF file-backed load bounds invalid")
        for value in (va, va + file_size):
            if address < value < end:
                boundaries.add(value)
    chunks = []
    ordered = sorted(boundaries)
    for left, right in zip(ordered, ordered[1:]):
        locations = {file_offset + left - va for va, file_size, file_offset in loads
                     if va <= left and right <= va + file_size}
        if not locations:
            raise Refusal("dynamic string table has a non-file-backed virtual gap")
        if len(locations) != 1:
            raise Refusal("dynamic string table has conflicting file-offset translations")
        location = locations.pop()
        count = right - left
        if location < 0 or location + count > len(raw):
            raise Refusal("dynamic string span outside complete file bytes")
        chunks.append(raw[location:location + count])
    table = b"".join(chunks)
    if len(table) != length:
        raise Refusal("dynamic string table exact byte coverage failed")
    return table


def elf_dynamic(raw):
    """Parse exact ELF header and PT_DYNAMIC strings without running a tool."""
    if len(raw) < 16 or raw[:4] != b"\x7fELF":
        raise Refusal("named native file is not ELF")
    elf_class, data_encoding = raw[4], raw[5]
    if elf_class not in (1, 2) or data_encoding not in (1, 2):
        raise Refusal("unsupported ELF class/byte order")
    endian = "<" if data_encoding == 1 else ">"
    fmt = endian + ("HHIQQQIHHHHHH" if elf_class == 2 else "HHIIIIIHHHHHH")
    size = 64 if elf_class == 2 else 52
    if len(raw) < size:
        raise Refusal("truncated ELF header")
    fields = struct.unpack_from(fmt, raw, 16)
    e_type, e_machine, _, _, phoff, _, _, ehsize, phsize, phnum, _, _, _ = fields
    expected_phsize = 56 if elf_class == 2 else 32
    if ehsize != size or phsize != expected_phsize or phnum == 65535:
        raise Refusal("unsupported ELF header/program table")
    if phnum > 1024 or phoff + phnum * phsize > len(raw):
        raise Refusal("ELF program table outside file")
    loads, dynamic = [], []
    for i in range(phnum):
        p = struct.unpack_from(endian + ("IIQQQQQQ" if elf_class == 2 else "IIIIIIII"),
                               raw, phoff + i * phsize)
        if elf_class == 2:
            p_type, _, off, va, _, filesz, memsz, _ = p
        else:
            p_type, off, va, _, filesz, memsz, _, _ = p
        if off + filesz > len(raw):
            raise Refusal("ELF segment outside file")
        if p_type == 1:
            if filesz > memsz or va + memsz > (1 << (64 if elf_class == 2 else 32)):
                raise Refusal("ELF load file/memory extent is invalid")
            loads.append((va, filesz, off))
        elif p_type == 2:
            dynamic.append((off, filesz))
    if len(dynamic) > 1:
        raise Refusal("multiple dynamic tables unsupported")
    entries, terminated = [], not dynamic
    width = 16 if elf_class == 2 else 8
    for off, filesz in dynamic:
        if filesz % width:
            raise Refusal("unaligned dynamic table")
        for pos in range(off, off + filesz, width):
            tag, val = struct.unpack_from(endian + ("qQ" if elf_class == 2 else "iI"), raw, pos)
            if tag == 0:
                terminated = True
                break
            entries.append((tag, val))
    if not terminated:
        raise Refusal("unterminated ELF dynamic table")
    strtab = [v for t, v in entries if t == 5]
    strsize = [v for t, v in entries if t == 10]
    string_entries = [(t, v) for t, v in entries if t in (1, 14, 15, 29)]
    strings = []
    if string_entries:
        if len(strtab) != 1 or len(strsize) != 1:
            raise Refusal("dynamic string table is ambiguous")
        if strtab[0] + strsize[0] > (1 << (64 if elf_class == 2 else 32)):
            raise Refusal("dynamic string virtual extent overflows ELF address width")
        table = _file_backed_virtual_bytes(raw, loads, strtab[0], strsize[0])
        for tag, offset in string_entries:
            if offset >= len(table):
                raise Refusal("dynamic string offset outside table")
            end = table.find(b"\0", offset)
            if end < 0:
                raise Refusal("unterminated dynamic string")
            value = table[offset:end]
            strings.append({"tag": tag, "text": value.decode("utf-8", "surrogateescape"),
                            "raw_base64": base64.b64encode(value).decode("ascii")})
    return {"class_bits": 64 if elf_class == 2 else 32,
            "byte_order": "little" if data_encoding == 1 else "big",
            "type": e_type, "machine": e_machine,
            "header_base64": base64.b64encode(raw[:size]).decode("ascii"),
            "program_header_count": phnum,
            "dynamic_strings": strings,
            "needed": [s["text"] for s in strings if s["tag"] == 1],
            "soname": [s["text"] for s in strings if s["tag"] == 14],
            "rpath": [s["text"] for s in strings if s["tag"] == 15],
            "runpath": [s["text"] for s in strings if s["tag"] == 29]}


def maps_snapshot(reader):
    """Retain exact bounded maps bytes; not a certificate of loader history."""
    # procfs size is zero and changes naturally: unlike regular input files it
    # cannot use the stable-file reader. Every actually returned byte is charged.
    fd = os.open("/proc/self/maps", os.O_RDONLY | os.O_CLOEXEC)
    chunks = []
    try:
        while True:
            remaining = min(MAX_MAP_BYTES + 1 - sum(map(len, chunks)),
                            reader.limit - reader.charged_bytes)
            if remaining <= 0:
                raise Refusal("maps read cap or explicit budget")
            chunk = os.read(fd, min(65536, remaining))
            reader.charged_bytes += len(chunk)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_MAP_BYTES:
            raise Refusal("maps read cap")
    finally:
        os.close(fd)
    records, paths = parse_maps(raw)
    native = []
    for path in paths:
        native.append(reader.native(path, require_elf=False))
    return {"observed_monotonic_ns": time.monotonic_ns(),
            "raw_bytes": len(raw), "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_base64": base64.b64encode(raw).decode("ascii"),
            "records": records, "mapped_file_identities": native}


def parse_maps(raw):
    records, paths = [], set()
    for line in raw.decode("utf-8", "surrogateescape").splitlines():
        fields = line.split(None, 5)
        if len(fields) < 5:
            raise Refusal("malformed maps line")
        path = fields[5] if len(fields) == 6 else None
        rec = {"address": fields[0], "permissions": fields[1],
               "offset": fields[2], "device": fields[3], "inode": fields[4], "path": path}
        records.append(rec)
        if path and path.startswith("/"):
            if path.endswith(" (deleted)"):
                raise Refusal("deleted mapped file cannot be identified")
            # All file-backed maps are retained. ELF qualification below checks
            # magic rather than relying on names/extensions.
            paths.add(path)
    return records, sorted(paths)


def distribution_inventory(name, distribution, venv_root, reader):
    files = distribution.files
    if files is None or len(files) > MAX_FILES:
        raise Refusal("complete finite distribution RECORD inventory required")
    root = Path(venv_root).resolve(strict=True)
    rows, native = [], []
    for item in sorted(files, key=str):
        located = Path(distribution.locate_file(item))
        resolved = located.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise Refusal("distribution file escapes isolated venv")
        st = os.stat(located, follow_symlinks=False)
        if not stat.S_ISREG(st.st_mode):
            raise Refusal("distribution inventory contains nonregular file")
        h = item.hash
        rows.append({"record_path": str(item), "located_path": str(located),
                     "resolved_path": str(resolved), "identity": identity(st),
                     "record_size": item.size,
                     "record_hash": None if h is None else {"mode": h.mode, "value": h.value}})
        if ".so" in resolved.name:
            native.append(reader.native(resolved))
    return {"name": name, "version": distribution.version,
            "file_count": len(rows), "files": rows, "declared_native_elf": native,
            "record_hashes_are_expectations_not_verified_non_native_file_hashes": True}


def filter_snapshot(h5z, filter_ids):
    rows = []
    for name, number in sorted(filter_ids.items()):
        if type(name) is not str or type(number) is not int or not 0 <= number <= 65535:
            raise Refusal("invalid declared filter input")
        available = bool(h5z.filter_avail(number))
        info = int(h5z.get_filter_info(number)) if available else None
        rows.append({"name": name, "id": number, "available": available,
                     "get_filter_info": info,
                     "encode_enabled": None if info is None else bool(info & 1),
                     "decode_enabled": None if info is None else bool(info & 2)})
    return rows


def module_identity(module, venv_root):
    path = Path(module.__file__).resolve(strict=True)
    site = (Path(venv_root) / "lib/python3.12/site-packages").resolve(strict=True)
    roots = [Path(p).resolve(strict=True) for p in getattr(module, "__path__", ())]
    if not path.is_relative_to(site) or any(not p.is_relative_to(site) for p in roots):
        raise Refusal("imported package escapes expected isolated site-packages")
    return {"file": str(path), "package_roots": [str(p) for p in roots]}


def collect(venv_root, filter_ids, *, importer, distribution_getter,
            snapshotter, inventory, module_observer):
    """Injectable orchestration. Offline tests substitute all native observers."""
    result = {"schema": SCHEMA, "authority": dict(NO_AUTHORITY),
              "cohort": dict(COHORT), "status": "INCOMPLETE",
              "explicit_native_calls": ["h5py.h5z.filter_avail", "h5py.h5z.get_filter_info"],
              "plugin_import_may_execute_implicit_native_filter_registration": True,
              "no_dataset_file_source_or_rng_operation_in_collector": True,
              "limits_of_evidence": [
                  "Only sampled mappings, not complete native load history.",
                  "ELF hashes identify named bytes, not all executed code or memory.",
                  "Distribution RECORD hashes for nonnative files are unverified expectations.",
                  "Ancestor namespace closure and complete scientific runtime admission remain pending."]}
    result["maps_before_packages"] = snapshotter()
    distributions = {}
    for name, expected in COHORT.items():
        dist = distribution_getter(name)
        if dist.version != expected:
            raise Refusal("distribution version differs from pinned cohort: " + name)
        distributions[name] = dist
    result["distributions_before"] = {n: inventory(n, d) for n, d in distributions.items()}
    numpy = importer("numpy")
    h5py = importer("h5py")
    if numpy.__version__ != COHORT["numpy"] or h5py.__version__ != COHORT["h5py"]:
        raise Refusal("imported package versions differ from pinned cohort")
    result["maps_after_numpy_h5py"] = snapshotter()
    result["filters_before_plugin"] = filter_snapshot(h5py.h5z, filter_ids)
    plugin = importer("hdf5plugin")
    actual_filters = dict(plugin.FILTERS)
    if actual_filters != filter_ids:
        raise Refusal("plugin FILTERS differs from source-derived declared input")
    result["filters_after_plugin"] = filter_snapshot(h5py.h5z, filter_ids)
    result["versions"] = {"numpy": str(numpy.__version__), "h5py": str(h5py.__version__),
                          "hdf5plugin_distribution": distributions["hdf5plugin"].version,
                          "hdf5plugin_module": str(plugin.version),
                          "hdf5_runtime": str(h5py.version.hdf5_version),
                          "hdf5_runtime_tuple": list(h5py.version.hdf5_version_tuple),
                          "hdf5_built_version_tuple": list(h5py.version.hdf5_built_version_tuple)}
    if result["versions"]["hdf5_runtime"] != "2.0.0" or result["versions"]["hdf5_built_version_tuple"] != [2, 0, 0]:
        raise Refusal("HDF5 runtime/build version differs from exact h5py wheel expectation")
    result["package_roots"] = {"numpy": module_observer(numpy),
                               "h5py": module_observer(h5py), "hdf5plugin": module_observer(plugin)}
    result["plugin_path"] = str(plugin.PLUGIN_PATH)
    result["declared_plugin_filters"] = actual_filters
    result["distributions_after"] = {n: inventory(n, d) for n, d in distributions.items()}
    result["distribution_before_after_equal"] = {
        name: result["distributions_before"][name]["files"] == result["distributions_after"][name]["files"]
        for name in COHORT}
    result["maps_after_plugin_and_inventory"] = snapshotter()
    result["status"] = "COLLECTED_IDENTITY_INPUTS_ONLY"
    return result


def _read_filter_input(path, reader):
    raw, ident = reader.file(path, cap=65536)
    value = json.loads(raw)
    if set(value) != {"schema", "filters", "source_members"} or value["schema"] != "seti-plugin-filter-source-input-v1":
        raise Refusal("invalid filter input schema")
    if not value["filters"] or len(value["filters"]) > 64:
        raise Refusal("finite source-derived filters required")
    return value, {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                   "identity": ident}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activate-native-metadata", action="store_true")
    parser.add_argument("--venv-root", required=True)
    parser.add_argument("--filter-input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not args.activate_native_metadata:
        raise Refusal("explicit collector activation flag required")
    if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
        raise Refusal("isolated -I -B Python required")
    if sys.version_info[:2] != (3, 12) or Path(sys.prefix).resolve() != Path(args.venv_root).resolve():
        raise Refusal("isolated cp312 venv required")
    if Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve():
        raise Refusal("prospective venv must differ from base interpreter")
    expected_site = (Path(args.venv_root) / "lib/python3.12/site-packages").resolve(strict=True)
    expected_stdlib_root = Path(sys.base_prefix).resolve(strict=True)
    for entry in sys.path:
        resolved = Path(entry).resolve()
        if "site-packages" in resolved.parts and resolved != expected_site:
            raise Refusal("unrelated site-packages in isolated sys.path")
        if not resolved.is_relative_to(expected_stdlib_root) and resolved != expected_site:
            raise Refusal("unrelated path in isolated sys.path")
    if any(os.environ.get(k) for k in ("LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH", "PYTHONHOME")):
        raise Refusal("unapproved native/Python search-path environment")
    plugin_search = os.environ.get("HDF5_PLUGIN_PATH", "")
    expected_plugin = expected_site / "hdf5plugin/plugins"
    if plugin_search and Path(plugin_search).resolve() != expected_plugin.resolve():
        raise Refusal("HDF5 plugin path must be empty or isolated package plugin directory")
    if os.environ.get("HDF5_PLUGIN_PRELOAD") != "::":
        raise Refusal("disable HDF5 automatic plugin search with HDF5_PLUGIN_PRELOAD=::")
    if any(os.environ.get(k) != "1" for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")):
        raise Refusal("single-thread numerical-library environment required")
    reader = BoundedReader()
    filter_input, input_pin = _read_filter_input(args.filter_input, reader)
    result = collect(args.venv_root, filter_input["filters"], importer=importlib.import_module,
                     distribution_getter=importlib.metadata.distribution,
                     snapshotter=lambda: maps_snapshot(reader),
                     inventory=lambda n, d: distribution_inventory(n, d, args.venv_root, reader),
                     module_observer=lambda m: module_identity(m, args.venv_root))
    if Path(result["plugin_path"]).resolve() != expected_plugin.resolve():
        raise Refusal("imported plugin directory differs from expected isolated package")
    bshuf = [row for row in result["filters_after_plugin"] if row["id"] == 32008]
    if len(bshuf) != 1 or not bshuf[0]["available"] or not bshuf[0]["decode_enabled"]:
        raise Refusal("required bitshuffle 32008 decode metadata absent")
    result["required_bitshuffle_decode_metadata_observed"] = True
    result["filter_input"] = input_pin
    result["filter_source_members"] = filter_input["source_members"]
    result["process"] = {"pid": os.getpid(), "executable": sys.executable,
                         "prefix": sys.prefix, "base_prefix": sys.base_prefix,
                         "python_version": sys.version, "isolated": bool(sys.flags.isolated),
                         "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
                         "sys_path": list(sys.path), "expected_site_packages": str(expected_site)}
    result["explicit_read_bytes"] = reader.charged_bytes
    result["explicit_read_limit"] = reader.limit
    result["loader_and_import_implicit_reads_not_counted_here"] = True
    raw = canonical(result)
    if len(raw) > MAX_OUTPUT_BYTES:
        raise Refusal("metadata output exceeds 8 MiB")
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise Refusal("zero-progress output write")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)
    print(json.dumps({"schema": SCHEMA, "status": result["status"],
                      "output": args.output, "bytes": len(raw),
                      "sha256": hashlib.sha256(raw).hexdigest(),
                      "explicit_read_bytes": reader.charged_bytes}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"schema": SCHEMA, "status": "FAILED_INCOMPLETE",
                          "error_type": type(exc).__name__, "error": str(exc)[:500],
                          "authority": NO_AUTHORITY}, sort_keys=True), file=sys.stderr)
        sys.exit(2)
