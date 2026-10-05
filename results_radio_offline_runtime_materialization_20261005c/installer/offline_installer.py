#!/usr/bin/env python3
"""Prepare one offline installation; execute no child and import no wheel.

Static inspector functions are copied byte-for-byte from the retained 20261005b
wheel_io.py static-inspection subset. Acquisition/transport functions are omitted.
Original wheel_io.py SHA256: 6675431fbb2e5ed8f7ded7df7113742d40a021e58e1f7f612069674ca9a93e77

Root owns prospective source admission, activation, guarded child execution,
wait4 accounting and later source/native/runtime qualification.
"""
import argparse
import base64
import configparser
import csv
import email.parser
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import sysconfig
import time
import unicodedata
import urllib.parse
import zipfile
import zlib

CHUNK = 1024 * 1024
CENTRAL_MAX = 2 * 1024 * 1024
ENTRY_MAX = 8192
MEMBER_MAX = 128 * 1024 * 1024
PAYLOAD_MAX = 512 * 1024 * 1024
METADATA_MAX = 2 * 1024 * 1024
SUPPORTED_METHODS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)

class WheelIOError(RuntimeError):
    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.receipt = receipt or {}


def _fail(message):
    raise WheelIOError(message)


def _tick(budget, deadline_callback):
    budget.check()
    return deadline_callback()


def _received(budget, n, kind):
    record = getattr(budget, "record_received", None)
    if record is not None:
        record(n, kind=kind)


def _identity(st):
    return {"dev": st.st_dev, "ino": st.st_ino, "mode": stat.S_IMODE(st.st_mode),
            "nlink": st.st_nlink, "bytes": st.st_size}


def _safe_path(name, directory=False):
    if not isinstance(name, str) or not name or len(name.encode("utf-8")) > 4096:
        _fail("invalid or oversized archive path")
    if any(ord(c) < 32 or ord(c) == 127 for c in name) or "\\" in name or ":" in name:
        _fail("archive path contains control, backslash or drive separator")
    if unicodedata.normalize("NFC", name) != name or name.startswith("/"):
        _fail("archive path is absolute or has a normalization alias")
    stripped = name[:-1] if directory and name.endswith("/") else name
    if not stripped or (not directory and name.endswith("/")):
        _fail("invalid directory/file path spelling")
    for part in stripped.split("/"):
        if not part or part in (".", "..") or part.endswith((".", " ")):
            _fail("archive path has unsafe component")
        if re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part):
            _fail("archive path has reserved portable component")
    return stripped


def _spec(wheel):
    required = ("filename", "url", "bytes", "sha256", "name", "version", "tags")
    if not isinstance(wheel, dict) or any(k not in wheel for k in required):
        _fail("wheel spec is incomplete")
    if (not isinstance(wheel["name"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", wheel["name"]) or
            not isinstance(wheel["version"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+]*", wheel["version"]) or
            not isinstance(wheel["url"], str)):
        _fail("wheel distribution/version/URL fields are not canonical text")
    filename = _safe_path(wheel["filename"])
    if "/" in filename or not filename.endswith(".whl"):
        _fail("wheel output must be one fixed .whl filename")
    if type(wheel["bytes"]) is not int or not 0 < wheel["bytes"] <= PAYLOAD_MAX:
        _fail("wheel expected byte length is outside cap")
    if not isinstance(wheel["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", wheel["sha256"]):
        _fail("wheel SHA256 is not canonical")
    u = urllib.parse.urlsplit(wheel["url"])
    if (u.scheme != "https" or u.netloc != "files.pythonhosted.org" or
            u.username is not None or u.password is not None or u.port is not None or
            u.query or u.fragment or not u.path.startswith("/packages/") or
            u.path.rsplit("/", 1)[-1] != filename or urllib.parse.unquote(u.path) != u.path):
        _fail("wheel URL is not the exact pinned HTTPS files.pythonhosted.org URL")
    _safe_path(u.path[1:])
    parts = filename[:-4].split("-")
    if len(parts) not in (5, 6):
        _fail("wheel filename has unsupported fields")
    if len(parts) == 6 and not re.fullmatch(r"[0-9][A-Za-z0-9_]*", parts[2]):
        _fail("wheel build tag is invalid")
    norm = lambda s: re.sub(r"[-_.]+", "_", s).lower()
    if norm(parts[0]) != norm(wheel["name"]) or parts[1] != wheel["version"]:
        _fail("wheel filename distribution/version differs from pinned spec")
    expanded = sorted("-".join(x) for x in itertools.product(*(p.split(".") for p in parts[-3:])))
    if (not isinstance(wheel["tags"], list) or sorted(wheel["tags"]) != expanded or
            len(set(wheel["tags"])) != len(expanded) or
            any(not re.fullmatch(r"[A-Za-z0-9_]+-[A-Za-z0-9_]+-[A-Za-z0-9_]+", x) for x in expanded)):
        _fail("wheel filename tags differ from pinned expanded tags")
    return wheel


class _ArchiveReader(io.RawIOBase):
    def __init__(self, fd, budget, deadline_callback):
        self.fd, self.budget, self.deadline_callback = fd, budget, deadline_callback
        self.position = 0
        self.initial = os.fstat(fd)
        self.size = self.initial.st_size
        self.actual_reads = 0
        self.charged_reads = 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if self.position < 0 or self.position > self.size:
            _fail("archive seek is outside held file")
        return self.position
    def check_identity(self):
        _tick(self.budget, self.deadline_callback)
        st = os.fstat(self.fd)
        a, b = self.initial, st
        if (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns, a.st_nlink) != (
                b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns, b.st_nlink):
            _fail("held wheel archive changed during static preflight")
    def read(self, size=-1):
        if size < 0: size = self.size - self.position
        if size > CENTRAL_MAX or size < 0:
            _fail("archive read exceeds per-operation bound")
        self.check_identity()
        self.budget.debit_read(size)
        self.charged_reads += size
        result = os.pread(self.fd, size, self.position)
        _received(self.budget, len(result), "zip")
        self.actual_reads += len(result)
        self.position += len(result)
        return result
    def at(self, offset, count):
        self.seek(offset)
        result = self.read(count)
        if len(result) != count:
            _fail("truncated held wheel archive")
        return result


def _extras(raw):
    cursor = 0
    while cursor < len(raw):
        if len(raw) - cursor < 4:
            _fail("truncated ZIP extra-field header")
        kind, length = struct.unpack_from("<HH", raw, cursor)
        cursor += 4
        if cursor + length > len(raw):
            _fail("truncated ZIP extra-field value")
        if kind in (0x0001, 0x7075, 0x6375):
            _fail("ZIP64 or Unicode path/comment alias extra is refused")
        cursor += length


def _structure(reader):
    if reader.size < 22:
        _fail("archive has no bounded EOCD")
    tail_start = max(0, reader.size - 65557)
    tail = reader.at(tail_start, reader.size - tail_start)
    candidates = []
    for i in range(len(tail) - 21):
        if tail[i:i+4] == b"PK\x05\x06":
            fields = struct.unpack_from("<4s4H2IH", tail, i)
            if i + 22 + fields[-1] == len(tail):
                candidates.append((tail_start + i, fields))
    if len(candidates) != 1:
        _fail("archive lacks one unambiguous terminal EOCD")
    eocd, f = candidates[0]
    _, disk, cd_disk, disk_count, count, cd_size, cd_offset, _ = f
    if disk or cd_disk or count != disk_count or count == 65535 or cd_size == 0xffffffff or cd_offset == 0xffffffff:
        _fail("ZIP64/multidisk archive is refused")
    if not 0 < count <= ENTRY_MAX or not 0 < cd_size <= CENTRAL_MAX:
        _fail("ZIP central directory count/bytes exceeds bound")
    if cd_offset + cd_size != eocd:
        _fail("central directory does not end at terminal EOCD")
    central = reader.at(cd_offset, cd_size)
    entries = []
    cursor = 0
    aliases = {}
    names = {}
    payload = 0
    for _ in range(count):
        if cursor + 46 > len(central):
            _fail("truncated central directory entry")
        f = struct.unpack_from("<4s6H3I5H2I", central, cursor)
        if f[0] != b"PK\x01\x02":
            _fail("bad central directory signature")
        (_, made, needed, flags, method, mtime, mdate, crc, compressed, size,
         name_len, extra_len, comment_len, start_disk, internal, external, local) = f
        end = cursor + 46 + name_len + extra_len + comment_len
        if end > len(central) or not name_len:
            _fail("central directory variable fields exceed declared span")
        raw_name = central[cursor+46:cursor+46+name_len]
        extra = central[cursor+46+name_len:cursor+46+name_len+extra_len]
        _extras(extra)
        if start_disk or 0xffffffff in (compressed, size, local) or needed > 20:
            _fail("ZIP64/multidisk/new ZIP feature is refused")
        if flags & ~(0x800 | 8) or method not in SUPPORTED_METHODS:
            _fail("encrypted/unsupported ZIP flags or compression")
        if method == zipfile.ZIP_STORED and compressed != size:
            _fail("stored ZIP member has differing compressed/uncompressed lengths")
        try:
            name = raw_name.decode("utf-8" if flags & 0x800 else "ascii")
        except UnicodeDecodeError:
            _fail("noncanonical archive filename encoding")
        directory = name.endswith("/")
        clean = _safe_path(name, directory)
        alias = clean.casefold()
        if name in names or alias in aliases:
            _fail("duplicate or aliased archive path")
        names[name] = directory
        aliases[alias] = directory
        mode = external >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or (kind == stat.S_IFDIR) != directory and kind != 0:
            _fail("archive symlink/special file or inconsistent directory kind")
        if external & 0x10 and not directory:
            _fail("DOS directory flag differs from path")
        if size > MEMBER_MAX or directory and size != 0:
            _fail("archive member declared size exceeds cap or directory is nonempty")
        payload += size
        if payload > PAYLOAD_MAX:
            _fail("archive declared aggregate payload exceeds cap")
        if clean.endswith((".dist-info/RECORD.jws", ".dist-info/RECORD.p7s")):
            _fail("deprecated wheel RECORD signatures are refused")
        entries.append({"path": name, "kind": "directory" if directory else "file", "bytes": size,
                        "compressed_bytes": compressed, "crc32": crc, "local_offset": local,
                        "flags": flags, "method": method, "needed": needed,
                        "mtime": mtime, "mdate": mdate, "raw_name": raw_name})
        cursor = end
    if cursor != len(central):
        _fail("central directory has unparsed records or count disagreement")
    for name, directory in names.items():
        clean = name.rstrip("/")
        parts = clean.split("/")
        for i in range(1, len(parts)):
            prefix = "/".join(parts[:i]).casefold()
            if prefix in aliases and aliases[prefix] is False:
                _fail("archive file/directory prefix collision")
    prefix_spellings = {}
    for name in names:
        parts = name.rstrip("/").split("/")
        for i in range(1, len(parts) + 1):
            prefix = "/".join(parts[:i])
            alias = prefix.casefold()
            if alias in prefix_spellings and prefix_spellings[alias] != prefix:
                _fail("archive implicit directory prefix has a case alias")
            prefix_spellings[alias] = prefix
    regions = []
    for row in entries:
        local = row["local_offset"]
        if local + 30 > cd_offset:
            _fail("local header overlaps central directory")
        f = struct.unpack("<4s5H3I2H", reader.at(local, 30))
        sig, needed, flags, method, mtime, mdate, crc, compressed, size, name_len, extra_len = f
        if (sig != b"PK\x03\x04" or (needed, flags, method, mtime, mdate) !=
                (row["needed"], row["flags"], row["method"], row["mtime"], row["mdate"])):
            _fail("local and central ZIP header metadata differs")
        variable_end = local + 30 + name_len + extra_len
        if variable_end > cd_offset:
            _fail("local variable header overlaps central directory")
        variable = reader.at(local + 30, name_len + extra_len)
        if variable[:name_len] != row["raw_name"]:
            _fail("local and central filenames differ")
        _extras(variable[name_len:])
        expected = (row["crc32"], row["compressed_bytes"], row["bytes"])
        if flags & 8:
            if any(got not in (0, want) for got, want in zip((crc, compressed, size), expected)):
                _fail("local descriptor placeholders differ from central values")
        elif (crc, compressed, size) != expected:
            _fail("local and central CRC/length differs")
        data_end = variable_end + row["compressed_bytes"]
        if data_end > cd_offset:
            _fail("compressed member overlaps central directory")
        end = data_end
        if flags & 8:
            if data_end + 12 > cd_offset:
                _fail("truncated ZIP data descriptor")
            probe = reader.at(data_end, 4)
            signed = probe == b"PK\x07\x08"
            descriptor = reader.at(data_end + (4 if signed else 0), 12)
            if struct.unpack("<3I", descriptor) != expected:
                _fail("ZIP data descriptor disagrees with central values")
            end += 16 if signed else 12
            if end > cd_offset:
                _fail("ZIP data descriptor overlaps central directory")
        row["data_offset"] = variable_end
        row["region_end"] = end
        regions.append((local, end))
    cursor = 0
    for start, end in sorted(regions):
        if start != cursor:
            _fail("archive local regions overlap or leave an unparsed gap/preamble")
        cursor = end
    if cursor != cd_offset:
        _fail("archive local regions do not meet central directory")
    return entries, payload


def _payload_chunks(reader, row):
    """Checks actual raw DEFLATE end/consumption; ZipExtFile trims declared size."""
    remaining = row["compressed_bytes"]
    offset = row["data_offset"]
    produced = 0
    decompressor = zlib.decompressobj(-15) if row["method"] == zipfile.ZIP_DEFLATED else None
    while remaining:
        raw = reader.at(offset, min(CHUNK, remaining))
        remaining -= len(raw)
        offset += len(raw)
        if decompressor is None:
            produced += len(raw)
            if produced > row["bytes"]:
                _fail("stored payload exceeds declared length")
            yield raw
            continue
        pending = raw
        while pending:
            _tick(reader.budget, reader.deadline_callback)
            limit = min(CHUNK, row["bytes"] - produced + 1)
            chunk = decompressor.decompress(pending, limit)
            produced += len(chunk)
            if produced > row["bytes"]:
                _fail("DEFLATE payload exceeds declared length by bounded +1")
            if decompressor.unused_data or decompressor.eof and remaining:
                _fail("DEFLATE stream has trailing declared compressed bytes")
            next_pending = decompressor.unconsumed_tail
            if not chunk and next_pending == pending:
                _fail("DEFLATE stream made no progress")
            pending = next_pending
            if chunk:
                yield chunk
    if decompressor is not None:
        while not decompressor.eof:
            _tick(reader.budget, reader.deadline_callback)
            chunk = decompressor.decompress(b"", min(CHUNK, row["bytes"] - produced + 1))
            produced += len(chunk)
            if produced > row["bytes"]:
                _fail("DEFLATE payload exceeds declared length by bounded +1")
            if not chunk:
                _fail("DEFLATE stream lacks exact end marker")
            yield chunk
        if decompressor.unused_data or decompressor.unconsumed_tail:
            _fail("DEFLATE stream did not consume its exact compressed span")
    if produced != row["bytes"]:
        _fail("streamed archive member length differs from declaration")


def _metadata(content, wheel, entries):
    norm = lambda s: re.sub(r"[-_.]+", "_", s).lower()
    dist = norm(wheel["name"]) + "-" + wheel["version"] + ".dist-info"
    record = dist + "/RECORD"
    metadata = dist + "/METADATA"
    wheel_path = dist + "/WHEEL"
    regular = {r["path"]: r for r in entries if r["kind"] == "file"}
    if any(p not in regular for p in (record, metadata, wheel_path)):
        _fail("wheel lacks its one pinned METADATA/WHEEL/RECORD set")
    roots = {p.split("/", 1)[0] for p in regular if p.split("/", 1)[0].endswith(".dist-info")}
    if roots != {dist}:
        _fail("wheel has an additional or mismatched dist-info root")
    for path in regular:
        parts = path.split("/")
        if parts[0].endswith(".data"):
            if (parts[0] != dist[:-10] + ".data" or len(parts) < 3 or
                    parts[1] not in ("purelib", "platlib", "headers", "scripts", "data")):
                _fail("wheel .data path has wrong distribution root or scheme")
    parsed = email.parser.BytesParser().parsebytes(content[metadata])
    for field, expected in (("Name", wheel["name"]), ("Version", wheel["version"])):
        values = parsed.get_all(field, [])
        if len(values) != 1 or (norm(values[0]) != norm(expected) if field == "Name" else values[0] != expected):
            _fail("METADATA name/version differs from pinned spec")
    wh = email.parser.BytesParser().parsebytes(content[wheel_path])
    if wh.get_all("Wheel-Version", []) != ["1.0"]:
        _fail("only sole Wheel-Version 1.0 is supported")
    pure = wh.get_all("Root-Is-Purelib", [])
    if pure not in (["true"], ["false"]):
        _fail("Root-Is-Purelib must be one canonical boolean")
    tags = wh.get_all("Tag", [])
    if len(tags) != len(set(tags)) or sorted(tags) != sorted(wheel["tags"]):
        _fail("WHEEL expanded tags differ from pinned tags")
    if pure == ["true"] and any(t.split("-")[1:] != ["none", "any"] for t in tags):
        _fail("purelib wheel has non-pure pinned ABI/platform tags")
    try:
        rows = list(csv.reader(io.StringIO(content[record].decode("utf-8"), newline=""), strict=True))
    except (UnicodeDecodeError, csv.Error) as exc:
        _fail("RECORD is not strict UTF8 CSV: " + str(exc))
    seen = set()
    for row in rows:
        if len(row) != 3:
            _fail("RECORD row must contain exactly three columns")
        path, encoded, size = row
        _safe_path(path)
        if path in seen or path not in regular:
            _fail("RECORD duplicates or names a missing/nonregular member")
        seen.add(path)
        if path == record:
            if encoded or size:
                _fail("RECORD self row must have blank hash and size")
            continue
        if not re.fullmatch(r"sha256=[A-Za-z0-9_-]{43}", encoded):
            _fail("RECORD hash must be canonical unpadded URL-safe SHA256")
        raw = base64.urlsafe_b64decode(encoded[7:] + "=")
        if base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != encoded[7:]:
            _fail("RECORD hash has noncanonical trailing bits")
        if not re.fullmatch(r"0|[1-9][0-9]*", size):
            _fail("RECORD size is not canonical decimal")
        if int(size) != regular[path]["bytes"] or raw.hex() != regular[path]["sha256"]:
            _fail("RECORD member hash or length differs from streamed content")
    if seen != set(regular):
        _fail("RECORD does not cover exactly every regular archive member")
    entry_path = dist + "/entry_points.txt"
    entrypoints = content.get(entry_path)
    if entrypoints is not None:
        try:
            entrypoints = entrypoints.decode("utf-8")
        except UnicodeDecodeError:
            _fail("entry_points.txt is not UTF8")
    return {"name": parsed["Name"], "version": parsed["Version"],
            "requires_python": parsed.get_all("Requires-Python", []),
            "requires_dist": parsed.get_all("Requires-Dist", []),
            "metadata_version": parsed.get_all("Metadata-Version", []),
            "wheel_version": "1.0", "root_is_purelib": pure == ["true"],
            "tags": sorted(tags), "dist_info": dist, "entry_points_utf8": entrypoints,
            "data_paths_remapped": False}


def inspect_wheel(held_fd, wheel, budget, deadline_callback):
    """Statically verifies a held archive; no extraction, install, import or ELF parse."""
    _spec(wheel)
    st = os.fstat(held_fd)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size != wheel["bytes"]:
        _fail("held wheel is not a sole regular file with pinned length")
    reader = _ArchiveReader(held_fd, budget, deadline_callback)
    receipt = {"schema": "setisearch-wheel-static-preflight-v1", "filename": wheel["filename"],
               "status": "STARTING", "archive_bytes": st.st_size, "file_identity": _identity(st),
               "archive_sha256": None, "payload_bytes": None, "members": [],
               "native_elf_parsed": False, "installed": False, "packages_imported": False}
    try:
        digest = hashlib.sha256()
        while reader.tell() < reader.size:
            digest.update(reader.read(min(CHUNK, reader.size - reader.tell())))
        receipt["archive_sha256"] = digest.hexdigest()
        if receipt["archive_sha256"] != wheel["sha256"]:
            _fail("held archive SHA256 differs from pinned spec")
        entries, payload = _structure(reader)
        receipt["payload_bytes"] = payload
        contents = {}
        with zipfile.ZipFile(reader, "r", allowZip64=False) as archive:
            infos = archive.infolist()
            if len(infos) != len(entries) or [i.filename for i in infos] != [r["path"] for r in entries]:
                _fail("ZipFile view differs from bounded central directory preflight")
            actual_payload = 0
            for info, row in zip(infos, entries):
                if (info.CRC, info.file_size, info.compress_size, info.header_offset, info.flag_bits, info.compress_type) != (
                        row["crc32"], row["bytes"], row["compressed_bytes"], row["local_offset"], row["flags"], row["method"]):
                    _fail("ZipFile entry fields differ from bounded structural preflight")
                sha = hashlib.sha256()
                count = 0
                crc = 0
                capture = (row["path"].endswith((".dist-info/METADATA", ".dist-info/WHEEL",
                                                ".dist-info/RECORD", ".dist-info/entry_points.txt")))
                raw = bytearray()
                if capture and row["bytes"] > METADATA_MAX:
                    _fail("wheel metadata/RECORD/entrypoints exceeds bounded capture")
                for chunk in _payload_chunks(reader, row):
                    _tick(budget, deadline_callback)
                    count += len(chunk)
                    actual_payload += len(chunk)
                    if count > row["bytes"] or count > MEMBER_MAX or actual_payload > PAYLOAD_MAX:
                        _fail("streamed archive payload exceeds declared or scope cap")
                    sha.update(chunk)
                    crc = zlib.crc32(chunk, crc)
                    if capture:
                        raw.extend(chunk)
                if count != row["bytes"]:
                    _fail("streamed archive member length differs from declaration")
                if crc != row["crc32"]:
                    _fail("streamed archive member CRC32 differs from declaration")
                row["sha256"] = sha.hexdigest()
                if capture:
                    contents[row["path"]] = bytes(raw)
                receipt["members"].append({k: row[k] for k in ("path", "kind", "bytes", "sha256", "compressed_bytes", "crc32")})
            if actual_payload != payload:
                _fail("streamed aggregate payload differs from central declarations")
        receipt["metadata"] = _metadata(contents, wheel, entries)
        receipt["native_member_paths"] = [r["path"] for r in entries if r["kind"] == "file" and
                                           re.search(r"(?:\.so(?:\.[0-9]+)*|\.dll|\.dylib|\.pyd)$", r["path"], re.I)]
        reader.check_identity()
        receipt["status"] = "STATIC_WHEEL_PREFLIGHT_VERIFIED"
        return receipt
    except Exception as exc:
        receipt["status"] = "CLOSED_FAILED"
        receipt["failure_type"] = type(exc).__name__
        receipt["failure"] = str(exc)[:4096]
        raise WheelIOError("wheel static preflight failed: " + str(exc), receipt) from exc
    finally:
        receipt["actual_archive_read_bytes"] = reader.actual_reads
        receipt["charged_archive_read_bytes"] = reader.charged_reads


SCHEMA = 'radio-offline-runtime-installer-plan-v1'
IDENTITY = 'radio-offline-runtime-materialization-20261005c'
ORIGINAL_SHA256 = 'fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25'
EXPECTED_VERSIONS = {'numpy': '2.3.5', 'h5py': '3.16.0', 'hdf5plugin': '7.1.0'}
PIN_KEYS = {'path', 'bytes', 'sha256', 'mode'}
CEILINGS = {'wall_seconds': 300, 'cpu_seconds': 240,
            'address_space_bytes': 1024**3, 'artifact_bytes': 1536*1024**2,
            'parent_read_bytes': 3*1024**3, 'child_read_reserve_bytes': 1024**3,
            'joined_read_bytes': 4*1024**3, 'stream_bytes': 4*1024**2,
            'file_bytes': 128*1024**2, 'file_count': 20000,
            'directory_count': 4096, 'terminal_reserve_bytes': 8*1024**2}
PLAN_KEYS = {'schema', 'identity', 'purpose', 'single_use', 'network', 'compile',
             'native_imports', 'original_plan_pin', 'source_pins', 'runtime_pins',
             'python_executable', 'python_version', 'stdlib_root', 'guard_path',
             'seed_pins', 'wheels', 'wheel_lock_utf8', 'limits', 'output_root'}


class Refusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')


def absolute(value):
    require(isinstance(value, str) and value.startswith('/') and
            not any(ord(c) < 32 or ord(c) == 127 for c in value) and
            str(Path(value)) == value and '..' not in Path(value).parts and
            str(Path(value).resolve()) == value, 'canonical_absolute_path_required')
    return value


def relative(value):
    try:
        return _safe_path(value)
    except WheelIOError:
        raise Refusal('safe_relative_path_required') from None


def pinned_json(raw, expected):
    require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected) and
            digest(raw) == expected, 'externally_expected_plan_sha256_mismatch')
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate_json_key')
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise Refusal('invalid_plan_json') from None
    require(type(value) is dict, 'plan_object_required')
    return value


def validate_pin(pin, file_limit):
    require(type(pin) is dict and set(pin) == PIN_KEYS, 'exact_file_pin_fields_required')
    absolute(pin['path'])
    require(type(pin['bytes']) is int and 0 <= pin['bytes'] <= file_limit and
            isinstance(pin['sha256'], str) and re.fullmatch('[0-9a-f]{64}', pin['sha256']) and
            type(pin['mode']) is int and 0 <= pin['mode'] <= 0o777, 'invalid_file_pin')


def validate_plan(raw, expected):
    plan = pinned_json(raw, expected)
    require(set(plan) == PLAN_KEYS and plan['schema'] == SCHEMA and plan['identity'] == IDENTITY and
            plan['purpose'] == 'offline-package-install-only' and plan['single_use'] is True and
            plan['network'] is False and plan['compile'] is False and plan['native_imports'] is False,
            'distinct_offline_installer_scope_required')
    limits = plan['limits']
    require(type(limits) is dict and set(limits) == set(CEILINGS) and
            all(type(v) is int and 0 < v <= CEILINGS[k] for k, v in limits.items()),
            'finite_exact_limits_required')
    require(limits['parent_read_bytes'] + limits['child_read_reserve_bytes'] <= limits['joined_read_bytes'],
            'joined_read_reservation_mismatch')
    require(limits['terminal_reserve_bytes'] >= 1024**2 and
            2 * limits['stream_bytes'] + limits['terminal_reserve_bytes'] < limits['artifact_bytes'],
            'terminal_storage_reservation_mismatch')
    for key in ('python_executable', 'stdlib_root', 'guard_path', 'output_root'):
        absolute(plan[key])
    require(type(plan['python_version']) is list and len(plan['python_version']) == 3 and
            all(type(v) is int and v >= 0 for v in plan['python_version']) and
            plan['python_version'][:2] == [3, 12], 'cp312_interpreter_required')
    validate_pin(plan['original_plan_pin'], limits['file_bytes'])
    require(plan['original_plan_pin']['sha256'] == ORIGINAL_SHA256, 'unchanged_original_plan_pin_required')
    selected = {}
    for collection in ('source_pins', 'runtime_pins'):
        pins = plan[collection]
        require(type(pins) is list and 0 < len(pins) <= 8192, 'finite_source_runtime_inventory_required')
        require([p.get('path') for p in pins if type(p) is dict] ==
                sorted(p.get('path') for p in pins if type(p) is dict), 'pin_inventory_must_be_sorted')
        for pin in pins:
            validate_pin(pin, limits['file_bytes'])
            require(pin['path'] not in selected, 'duplicate_selected_pin')
            selected[pin['path']] = pin
    require(str(Path(__file__).resolve()) in {p['path'] for p in plan['source_pins']},
            'installer_source_pin_required')
    require(plan['python_executable'] in selected and plan['guard_path'] in selected and
            any(p['path'] == plan['python_executable'] for p in plan['runtime_pins']) and
            any(p['path'] == plan['guard_path'] for p in plan['runtime_pins']),
            'actual_python_and_guard_runtime_pins_required')
    require(selected[plan['python_executable']]['mode'] & 0o111 and
            selected[plan['guard_path']]['mode'] & 0o111, 'executable_runtime_pin_required')
    require(plan['original_plan_pin']['path'] in selected and
            selected[plan['original_plan_pin']['path']] == plan['original_plan_pin'],
            'original_plan_source_inventory_required')
    seeds = plan['seed_pins']
    require(type(seeds) is list and 0 < len(seeds) <= 4096, 'finite_pure_pip_seed_required')
    paths = []
    for seed in seeds:
        require(type(seed) is dict and set(seed) == {'relative_path', 'pin'}, 'exact_seed_fields_required')
        path = relative(seed['relative_path'])
        validate_pin(seed['pin'], limits['file_bytes'])
        require((path.startswith('pip/') or re.match(r'pip-[0-9][^/]*\.dist-info/', path)) and
                not path.endswith(('.pyc', '.pyo', '.pth', '.so', '.dll', '.dylib', '.pyd')) and
                selected.get(seed['pin']['path']) == seed['pin'] and
                seed['pin'] in plan['runtime_pins'], 'pure_pinned_pip_source_required')
        paths.append(path)
    require(paths == sorted(paths) and len(set(paths)) == len(paths) and
            {'pip/__main__.py', 'pip/__init__.py'} <= set(paths) and
            sum(s['pin']['bytes'] for s in seeds) <= 64*1024**2, 'complete_finite_pip_seed_required')
    require(type(plan['wheels']) is list and len(plan['wheels']) == 3, 'exact_three_wheels_required')
    for wheel in plan['wheels']:
        require(type(wheel) is dict and set(wheel) == {'path', 'spec'}, 'exact_offline_wheel_fields_required')
        absolute(wheel['path'])
        require(type(wheel['spec']) is dict and set(wheel['spec']) ==
                {'name', 'version', 'filename', 'bytes', 'sha256', 'url', 'tags'},
                'exact_official_wheel_spec_required')
        _spec(wheel['spec'])
        require(Path(wheel['path']).name == wheel['spec']['filename'], 'original_archive_filename_required')
    require({w['spec']['name']: w['spec']['version'] for w in plan['wheels']} == EXPECTED_VERSIONS and
            sum(w['spec']['bytes'] for w in plan['wheels']) == 68409067,
            'unchanged_package_cohort_required')
    require(isinstance(plan['wheel_lock_utf8'], str) and
            len(plan['wheel_lock_utf8'].encode()) <= 65536, 'finite_hash_lock_required')
    return plan


class ReadBudget:
    def __init__(self, limits, deadline, clock=time.monotonic):
        self.limits, self.deadline, self.clock = limits, deadline, clock
        self.charged = 0
        self.received = 0

    def check(self):
        require(self.clock() < self.deadline, 'offline_preparation_wall_deadline')

    def debit_read(self, amount):
        self.check()
        require(type(amount) is int and amount >= 0 and
                self.charged + amount <= self.limits['parent_read_bytes'], 'parent_read_budget_exhausted')
        self.charged += amount

    def record_received(self, amount, kind='regular'):
        self.received += amount


def read_verified(pin, budget, keep=False):
    path = Path(pin['path'])
    for parent in (path, *path.parents):
        require(not parent.is_symlink(), 'selected_symlink_refused')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                before.st_size == pin['bytes'] and stat.S_IMODE(before.st_mode) == pin['mode'],
                'selected_file_identity_mismatch')
        count, hashed, contents = 0, hashlib.sha256(), bytearray()
        while count < pin['bytes']:
            requested = min(CHUNK, pin['bytes'] - count)
            budget.debit_read(requested)
            chunk = os.read(fd, requested)
            budget.record_received(len(chunk))
            require(chunk, 'selected_file_truncated')
            count += len(chunk)
            hashed.update(chunk)
            if keep:
                contents.extend(chunk)
        budget.debit_read(1)
        suffix = os.read(fd, 1)
        budget.record_received(len(suffix))
        require(not suffix and hashed.hexdigest() == pin['sha256'], 'selected_file_sha256_mismatch')
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                'selected_file_changed_while_reading')
        return bytes(contents) if keep else None
    finally:
        os.close(fd)


def stdlib_inventory(root, budget):
    paths = set()
    for dirname, dirs, files in os.walk(root, followlinks=False):
        budget.check()
        # -B prevents bytecode writes, not reads. Existing stdlib bytecode is
        # part of the admitted executable inventory, including __pycache__.
        dirs[:] = [d for d in dirs if d != 'site-packages']
        for directory in dirs:
            require(not (Path(dirname) / directory).is_symlink(), 'stdlib_symlink_refused')
        for filename in files:
            path = Path(dirname) / filename
            require(not path.is_symlink() and path.is_file(), 'stdlib_nonregular_file_refused')
            paths.add(str(path))
            require(len(paths) <= 8192, 'stdlib_inventory_count_limit')
    return paths


def write_new(path, raw, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:offset+CHUNK])
            require(written > 0, 'artifact_write_no_progress')
            offset += written
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def scope_inventory(root, limits, budget, hashes=False):
    files, directories, logical, allocated, rows = 0, 0, 0, 0, []
    for dirname, dirs, names in os.walk(root, followlinks=False):
        budget.check()
        directories += 1
        require(directories <= limits['directory_count'], 'artifact_directory_count_limit')
        for directory in dirs:
            require(not (Path(dirname)/directory).is_symlink(), 'artifact_symlink_refused')
        for name in sorted(names):
            path = Path(dirname)/name
            st = path.lstat()
            require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
                    st.st_size <= limits['file_bytes'], 'artifact_file_kind_or_size_limit')
            files += 1
            logical += st.st_size
            allocated += st.st_blocks * 512
            require(files <= limits['file_count'] and max(logical, allocated) <= limits['artifact_bytes'],
                    'artifact_count_or_storage_limit')
            row = {'path': str(path.relative_to(root)), 'bytes': st.st_size, 'mode': stat.S_IMODE(st.st_mode)}
            if hashes:
                pin = dict(row, path=str(path), sha256='0'*64)
                hashed = hashlib.sha256()
                fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW)
                try:
                    remaining = st.st_size
                    while remaining:
                        requested = min(CHUNK, remaining)
                        budget.debit_read(requested)
                        chunk = os.read(fd, requested)
                        budget.record_received(len(chunk))
                        require(chunk, 'artifact_hash_read_truncated')
                        hashed.update(chunk)
                        remaining -= len(chunk)
                    row['sha256'] = hashed.hexdigest()
                finally:
                    os.close(fd)
            rows.append(row)
    return {'files': files, 'directories': directories, 'logical_bytes': logical,
            'allocated_file_bytes': allocated, 'entries': rows,
            'full_peak_certified': False}


def install_preflight(inspections, seed_bytes, python_bytes, limits, filesystem_unit=4096):
    require(4096 <= filesystem_unit <= 65536, 'filesystem_allocation_unit_not_supported')
    members, scripts, generated = {}, [], []
    for inspection in inspections:
        require(inspection['status'] == 'STATIC_WHEEL_PREFLIGHT_VERIFIED', 'verified_static_inspection_required')
        for member in inspection['members']:
            path = relative(member['path'].rstrip('/') if member['kind'] == 'directory' else member['path'])
            require(not any(part.endswith('.data') for part in path.split('/')), 'wheel_data_remap_not_admitted')
            require(not path.endswith(('.pyc', '.pyo', '.pth')), 'bytecode_or_pth_member_not_admitted')
            if member['kind'] == 'file':
                require(path not in members, 'cross_wheel_member_collision')
                members[path] = member
        metadata = inspection['metadata']
        dist = metadata['dist_info']
        generated.extend([dist+'/INSTALLER', dist+'/REQUESTED', dist+'/RECORD'])
        entrypoints = metadata.get('entry_points_utf8')
        if entrypoints:
            parser = configparser.ConfigParser(interpolation=None, strict=True, delimiters=('=',))
            parser.optionxform = str
            try:
                parser.read_string(entrypoints)
            except configparser.Error:
                raise Refusal('invalid_generated_entrypoints') from None
            for section in ('console_scripts', 'gui_scripts'):
                if parser.has_section(section):
                    for name in parser[section]:
                        name = relative(name)
                        require('/' not in name, 'entrypoint_basename_required')
                        scripts.append('bin/'+name)
    for path in members:
        parts = path.split('/')
        require(not any('/'.join(parts[:i]) in members for i in range(1, len(parts))),
                'cross_wheel_file_directory_collision')
    spellings = {}
    for path in list(members) + scripts + generated:
        parts = path.split('/')
        for count in range(1, len(parts)+1):
            prefix = '/'.join(parts[:count])
            alias = prefix.casefold()
            require(alias not in spellings or spellings[alias] == prefix,
                    'cross_wheel_case_alias')
            spellings[alias] = prefix
    require(len(scripts) == len(set(scripts)) and not set(scripts) & set(members),
            'generated_script_collision')
    payload = sum(item['payload_bytes'] for item in inspections)
    require(payload <= PAYLOAD_MAX, 'joined_wheel_payload_limit')
    directories = {''}
    for path in list(members) + scripts + generated:
        parts = path.split('/')
        directories.update('/'.join(parts[:i]) for i in range(1, len(parts)))
    predicted_files = 3*len(members)+len(scripts)+len(generated)+4096
    predicted_dirs = 3*len(directories)+512
    require(predicted_files <= limits['file_count'] and predicted_dirs <= limits['directory_count'],
            'prospective_file_directory_budget_cannot_fit')
    archive = sum(item['archive_bytes'] for item in inspections)
    planned = (3*payload + archive + seed_bytes + python_bytes + 32*1024**2 +
               (limits['file_count']+limits['directory_count'])*filesystem_unit)
    require(planned <= limits['artifact_bytes'], 'prospective_payload_temp_evidence_budget_cannot_fit')
    return {'payload_bytes': payload, 'archive_bytes': archive, 'seed_bytes': seed_bytes,
            'conservative_storage_upper_bytes': planned, 'temporary_payload_factor': 3,
            'predicted_files': predicted_files, 'predicted_directories': predicted_dirs,
            'site_member_pins': members, 'generated_paths': sorted(set(generated+scripts)),
            'filesystem_unit_bytes': filesystem_unit, 'full_peak_certified': False}


def original_cohort(plan, original_raw):
    require(digest(original_raw) == ORIGINAL_SHA256, 'original_plan_changed')
    original = json.loads(original_raw)
    materialization = original['materialization']
    keys = ('name', 'version', 'filename', 'url', 'bytes', 'sha256', 'tags')
    expected = [{key: wheel[key] for key in keys} for wheel in materialization['official_wheels']]
    require([row['spec'] for row in plan['wheels']] == expected and
            plan['wheel_lock_utf8'] == materialization['offline_hash_lock_utf8'],
            'exact_original_wheels_and_lock_required')


def pip_argv(plan, root):
    installer = str(root/'pip-seed')
    site = str(root/'venv/lib/python3.12/site-packages')
    args = ['pip', '--isolated', '--disable-pip-version-check', 'install', '--no-index',
            '--no-deps', '--no-cache-dir', '--require-hashes', '--only-binary=:all:',
            '--no-compile', '--progress-bar', 'off', '--target', site,
            '--find-links', str(root/'wheelhouse'), '-r', str(root/'wheel-lock.txt')]
    bootstrap = ('import sys,runpy;sys.path.insert(0,'+repr(installer)+');sys.argv='+repr(args)+
                 ';runpy.run_module("pip",run_name="__main__")')
    # Root's supervisor performs the C-guard/status-fd/exec-fd handoff once.
    return [plan['python_executable'], '-I', '-B', '-S', '-c', bootstrap]


def child_environment(root):
    return {'LANG': 'C', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1',
            'PYTHONHASHSEED': '0', 'PIP_CONFIG_FILE': '/dev/null',
            'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
            'TMPDIR': str(root/'tmp')}


def prepare(plan_raw, expected_plan_sha256, output_root, absolute_operation_deadline=None):
    """Prepare only; root must supervise the returned guarded argv once."""
    started = time.monotonic()
    plan = validate_plan(plan_raw, expected_plan_sha256)
    limits = plan['limits']
    private_deadline = started + limits['wall_seconds'] - 30
    if absolute_operation_deadline is not None:
        require(type(absolute_operation_deadline) in (int, float), 'absolute_operation_deadline_number_required')
        private_deadline = min(private_deadline, absolute_operation_deadline)
    budget = ReadBudget(limits, private_deadline)
    root = Path(absolute(str(output_root)))
    require(str(root) == plan['output_root'], 'frozen_output_root_mismatch')
    require(root.parent.is_dir(), 'existing_output_parent_required')
    try:
        root.mkdir(mode=0o700, exist_ok=False)
    except FileExistsError:
        raise Refusal('existing_output_refused') from None
    report = {'schema': 'radio-offline-installer-preparation-receipt-v1',
              'identity': plan['identity'], 'plan_sha256': expected_plan_sha256,
              'status': 'FAILED_CLOSED', 'output_root': str(root),
              'installer_child_dispatches_here': 0, 'package_imports': 0,
              'network_requests': 0, 'hdf5_dataset_reads': 0,
              'runtime_qualified': False, 'scientific_authority': False,
              'retry_allowed': False, 'inspections': [], 'limits': limits}
    write_new(root/'spent.json', canonical({'identity': plan['identity'], 'plan_sha256': expected_plan_sha256,
                                          'spent': True, 'single_use': True, 'retry_allowed': False}))
    try:
        budget.check()
        require(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
                'isolated_no_site_no_bytecode_parent_required')
        require(str(Path(sys.executable).resolve()) == plan['python_executable'] and
                list(sys.version_info[:3]) == plan['python_version'], 'actual_interpreter_identity_mismatch')
        require(str(Path(sysconfig.get_path('stdlib')).resolve()) == plan['stdlib_root'],
                'actual_stdlib_root_mismatch')
        selected = {p['path']: p for p in plan['source_pins']+plan['runtime_pins']}
        for pin in selected.values():
            read_verified(pin, budget)
        actual_stdlib = stdlib_inventory(plan['stdlib_root'], budget)
        pinned_stdlib = {p['path'] for p in plan['runtime_pins'] if
                         Path(p['path']).is_relative_to(plan['stdlib_root']) and
                         'site-packages' not in Path(p['path']).parts}
        require(actual_stdlib == pinned_stdlib, 'complete_current_stdlib_inventory_required')
        original = read_verified(plan['original_plan_pin'], budget, keep=True)
        original_cohort(plan, original)
        for wheel in plan['wheels']:
            path = Path(wheel['path'])
            require(not path.is_symlink(), 'wheel_symlink_refused')
            fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try:
                inspection = inspect_wheel(fd, wheel['spec'], budget, budget.check)
            except WheelIOError as exc:
                report['inspections'].append(exc.receipt)
                raise
            finally:
                os.close(fd)
            report['inspections'].append(inspection)
        seed_bytes = sum(seed['pin']['bytes'] for seed in plan['seed_pins'])
        preflight = install_preflight(report['inspections'], seed_bytes,
                                      selected[plan['python_executable']]['bytes'], limits,
                                      max(4096, os.statvfs(root).f_frsize))
        report['preflight'] = preflight
        # Make a new venv without launching ensurepip, running site initialization,
        # following a system-site path, or compiling any installed source.
        for directory in ('venv/bin', 'venv/lib/python3.12/site-packages', 'pip-seed', 'wheelhouse', 'tmp'):
            (root/directory).mkdir(parents=True, exist_ok=True)
        python_raw = read_verified(selected[plan['python_executable']], budget, keep=True)
        write_new(root/'venv/bin/python', python_raw, 0o755)
        cfg = ('home = '+str(Path(plan['python_executable']).parent)+'\n'+
               'include-system-site-packages = false\n'+
               'version = '+'.'.join(map(str, plan['python_version']))+'\n'+
               'executable = '+plan['python_executable']+'\n')
        write_new(root/'venv/pyvenv.cfg', cfg.encode(), 0o644)
        for seed in plan['seed_pins']:
            raw = read_verified(seed['pin'], budget, keep=True)
            write_new(root/'pip-seed'/seed['relative_path'], raw, 0o644)
        for wheel in plan['wheels']:
            path, spec = Path(wheel['path']), wheel['spec']
            pin = {'path': str(path), 'bytes': spec['bytes'], 'sha256': spec['sha256'],
                   'mode': stat.S_IMODE(path.stat().st_mode)}
            raw = read_verified(pin, budget, keep=True)
            write_new(root/'wheelhouse'/spec['filename'], raw, 0o444)
        write_new(root/'wheel-lock.txt', plan['wheel_lock_utf8'].encode(), 0o444)
        report['pinned_python_argv'] = pip_argv(plan, root)
        report['child_env'] = child_environment(root)
        report['selected_files_before_child'] = scope_inventory(root, limits, budget, hashes=True)
        report['parent_read_charged_bytes'] = budget.charged
        report['parent_read_received_bytes'] = budget.received
        report['joined_read_conservative_charged_bytes'] = budget.charged + limits['child_read_reserve_bytes']
        report['status'] = 'OFFLINE_INSTALL_PREPARED_NOT_EXECUTED'
    except Exception as exc:
        report['failure_type'] = type(exc).__name__
        report['failure'] = str(exc)[:300] if isinstance(exc, (Refusal, WheelIOError)) else type(exc).__name__
    finally:
        report['elapsed_preparation_seconds'] = time.monotonic() - started
        report['parent_read_charged_bytes'] = budget.charged
        report['parent_read_received_bytes'] = budget.received
        raw = canonical(report)
        require(len(raw) <= limits['terminal_reserve_bytes'], 'preparation_receipt_reserve_exhausted')
        write_new(root/'preparation-receipt.json', raw)
    return report


def verify_installed(prepared, child_receipt, absolute_operation_deadline=None):
    """Byte evidence only; requires root's separately supervised child receipt."""
    require(prepared.get('status') == 'OFFLINE_INSTALL_PREPARED_NOT_EXECUTED', 'prepared_scope_required')
    require(type(child_receipt) is dict and child_receipt.get('child_exit_code') == 0 and
            child_receipt.get('child_reaped') is True and child_receipt.get('child_dispatches') == 1 and
            child_receipt.get('guarded_leaf') is True and child_receipt.get('failure') is None and
            type(child_receipt.get('wait4_direct_child_ru_maxrss_bytes')) is int and
            child_receipt['wait4_direct_child_ru_maxrss_bytes'] > 0, 'successful_guarded_wait4_child_receipt_required')
    limits = prepared['limits']
    private_deadline = time.monotonic()+30
    if absolute_operation_deadline is not None:
        require(type(absolute_operation_deadline) in (int, float), 'absolute_operation_deadline_number_required')
        private_deadline = min(private_deadline, absolute_operation_deadline)
    budget = ReadBudget(limits, private_deadline)
    budget.charged = prepared['parent_read_charged_bytes']
    try:
        root = Path(prepared['output_root'])
        inventory = scope_inventory(root, limits, budget, hashes=True)
        rows = {r['path']: r for r in inventory['entries']}
        before = {r['path']: r for r in prepared['selected_files_before_child']['entries']}
        site_prefix = 'venv/lib/python3.12/site-packages/'
        for path, row in before.items():
            require(rows.get(path) == row, 'prepared_non_site_artifact_changed')
        require(all(path in before or path == 'preparation-receipt.json' or path.startswith(site_prefix)
                    for path in rows), 'unexpected_non_site_artifact')
        allowed = set(prepared['preflight']['generated_paths'])
        members = prepared['preflight']['site_member_pins']
        for path, member in members.items():
            if path.endswith('.dist-info/RECORD'):
                continue
            observed = rows.get(site_prefix+path)
            require(observed and observed['bytes'] == member['bytes'] and
                    observed['sha256'] == member['sha256'], 'installed_member_whole_bytes_mismatch')
        site_paths = {path[len(site_prefix):] for path in rows if path.startswith(site_prefix)}
        require(site_paths <= set(members) | allowed and
                not any(path.endswith(('.pyc', '.pyo', '.pth')) for path in rows),
                'unexpected_installed_member_or_bytecode')
        require(all(site_prefix+inspection['metadata']['dist_info']+'/METADATA' in rows
                    for inspection in prepared['inspections']), 'all_three_installed_metadata_required')
        require(all(site_prefix+inspection['metadata']['dist_info']+'/RECORD' in rows
                    for inspection in prepared['inspections']), 'installed_record_required')
        return {'schema': 'radio-offline-installed-byte-evidence-v1', 'identity': prepared['identity'],
                'plan_sha256': prepared['plan_sha256'], 'status': 'INSTALLED_BYTES_VERIFIED_NO_PACKAGE_IMPORT',
                'verified_original_members': len(members), 'package_imports': 0, 'hdf5_dataset_reads': 0,
                'runtime_qualified': False, 'scientific_authority': False,
                'inventory': inventory, 'child_receipt': child_receipt,
                'parent_read_charged_bytes': budget.charged,
                'joined_read_conservative_charged_bytes': budget.charged + limits['child_read_reserve_bytes'],
                'wait4_is_direct_child_lifetime_peak': True,
                'observation_limits': ['Parent source admission and guard execution are root responsibilities.',
                                       'Artifact inventory is selected final storage, not full storage peak.',
                                       'No native/source/scientific runtime qualification is conferred.']}
    finally:
        prepared['verification_parent_read_charged_bytes'] = budget.charged
        prepared['verification_parent_read_received_bytes'] = budget.received


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        with Path(absolute(args.plan)).open('rb') as stream:
            raw = stream.read(8*1024**2+1)
        require(len(raw) <= 8*1024**2, 'plan_size_limit')
        report = prepare(raw, args.plan_sha256, args.output)
        print(report['status'])
        return 0 if report['status'] == 'OFFLINE_INSTALL_PREPARED_NOT_EXECUTED' else 1
    except (Refusal, WheelIOError) as exc:
        print('REFUSED: '+str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
