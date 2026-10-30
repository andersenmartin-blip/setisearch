"""Strict saved-NPY transport adapter for a separately activated BO family.

Importing this module performs no I/O.  This is not a telescope codec and does
not qualify historical M results.  All file/payload pins must be supplied before
opening an array.  NPY headers contain no astronomical geometry: a separately
authenticated metadata binding is mandatory for ``open_saved_scan``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
from dataclasses import dataclass
from typing import Any, Mapping
import zipfile

import numpy as np


FULL_SHAPE = (16, 1048576)
PAYLOAD_BYTES = 67108864
MAX_HEADER_BYTES = 65536
CHUNK_BYTES = 1048576
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_MAGIC = b"\x93NUMPY"


class AdapterError(ValueError):
    """A stable, fail-closed transport rejection, never a repaired input."""

    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


def _fail(code: str, detail: str) -> None:
    raise AdapterError(code, detail)


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        _fail("PIN_INVALID", f"{label} must be a lowercase SHA256")
    return value


def _integer(value: Any, label: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        _fail("PIN_INVALID", f"{label} must be an exact nonnegative integer")
    return value


@dataclass(frozen=True)
class NpyPin:
    file_bytes: int
    file_sha256: str
    powers_sha256: str
    shape: tuple[int, int] = FULL_SHAPE
    row_sha256: tuple[str, ...] | None = None

    def validate(self) -> None:
        _integer(self.file_bytes, "file_bytes", positive=True)
        _sha(self.file_sha256, "file_sha256")
        _sha(self.powers_sha256, "powers_sha256")
        if (type(self.shape) is not tuple or len(self.shape) != 2
                or any(type(n) is not int or n <= 0 for n in self.shape)
                or self.shape[0] > FULL_SHAPE[0]
                or self.shape[1] > FULL_SHAPE[1]):
            _fail("PIN_INVALID", "shape must be an explicit bounded 2-D tuple")
        if self.row_sha256 is not None:
            if type(self.row_sha256) is not tuple or len(self.row_sha256) != self.shape[0]:
                _fail("PIN_INVALID", "row pins must cover every row in order")
            for digest in self.row_sha256:
                _sha(digest, "row_sha256")


def _signature(s: os.stat_result) -> tuple[int, ...]:
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _open_regular(path: os.PathLike[str] | str) -> tuple[Path, int, os.stat_result]:
    p = Path(path).absolute()
    try:
        fd = os.open(p, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        _fail("FILE_OPEN", f"read-only regular-file open failed: {exc}")
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode):
        os.close(fd)
        _fail("FILE_TYPE", "input is not a regular file")
    return p, fd, s


def _unchanged(path: Path, fd: int, initial: os.stat_result) -> None:
    try:
        now = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        _fail("FILE_CHANGED", str(exc))
    if (not stat.S_ISREG(named.st_mode)
            or _signature(now) != _signature(initial)
            or _signature(named) != _signature(initial)):
        _fail("FILE_CHANGED", "opened file or its path identity changed")


def _read_exact(fd: int, count: int, offset: int, code: str) -> bytes:
    pieces = []
    remaining = count
    while remaining:
        block = os.pread(fd, min(remaining, CHUNK_BYTES), offset)
        if not block:
            _fail(code, "unexpected EOF")
        pieces.append(block)
        offset += len(block)
        remaining -= len(block)
    return b"".join(pieces)


def _digest(fd: int, offset: int, count: int) -> str:
    h = hashlib.sha256()
    while count:
        block = os.pread(fd, min(count, CHUNK_BYTES), offset)
        if not block:
            _fail("FILE_CHANGED", "unexpected EOF while hashing")
        h.update(block)
        offset += len(block)
        count -= len(block)
    return h.hexdigest()


def _parse_header(fd: int, pin: NpyPin) -> dict[str, Any]:
    prefix = _read_exact(fd, 8, 0, "HEADER_TRUNCATED")
    if prefix[:6] != _MAGIC:
        _fail("MAGIC", "not a NPY file")
    version = tuple(prefix[6:8])
    if version not in ((1, 0), (2, 0)):
        _fail("VERSION", "only exact NPY v1.0 and v2.0 are admitted")
    length_bytes = 2 if version == (1, 0) else 4
    raw_length = _read_exact(fd, length_bytes, 8, "HEADER_TRUNCATED")
    length = struct.unpack("<H" if length_bytes == 2 else "<I", raw_length)[0]
    if not 1 <= length <= MAX_HEADER_BYTES:
        _fail("HEADER_LENGTH", "header outside declared bounded size")
    offset = 8 + length_bytes + length
    raw = _read_exact(fd, length, 8 + length_bytes, "HEADER_TRUNCATED")
    if raw[-1:] != b"\n" or offset % 16:
        _fail("HEADER_LAYOUT", "header must end in newline and align to 16 bytes")
    try:
        header = raw.decode("ascii")
        node = ast.parse(header.strip(), mode="eval").body
    except (UnicodeError, SyntaxError, ValueError, RecursionError) as exc:
        _fail("HEADER_SYNTAX", str(exc))
    if not isinstance(node, ast.Dict):
        _fail("HEADER_KEYS", "header must be one literal dictionary")
    keys = []
    for key in node.keys:
        if not isinstance(key, ast.Constant) or type(key.value) is not str:
            _fail("HEADER_KEYS", "header keys must be literal strings")
        keys.append(key.value)
    if len(set(keys)) != len(keys):
        _fail("HEADER_KEYS", "duplicate header key")
    if set(keys) != {"descr", "fortran_order", "shape"}:
        _fail("HEADER_KEYS", "unexpected or missing header key")
    fields = dict(zip(keys, node.values))
    descr = fields["descr"]
    if not isinstance(descr, ast.Constant) or descr.value != "<f4" or type(descr.value) is not str:
        _fail("DTYPE", "only literal little-endian scalar '<f4' is admitted")
    order = fields["fortran_order"]
    if not isinstance(order, ast.Constant) or order.value is not False:
        _fail("ORDER", "only literal C order (False) is admitted")
    shape_node = fields["shape"]
    if (not isinstance(shape_node, ast.Tuple)
            or any(not isinstance(n, ast.Constant) or type(n.value) is not int or n.value <= 0
                   for n in shape_node.elts)):
        _fail("SHAPE", "shape must be a positive literal integer tuple")
    shape = tuple(n.value for n in shape_node.elts)
    if shape != pin.shape:
        _fail("SHAPE", "shape differs from the exact declared pin")
    payload_bytes = math.prod(shape) * 4
    if offset + payload_bytes != pin.file_bytes:
        _fail("PAYLOAD_SIZE", "exact header plus payload differs from file size")
    return {
        "version": list(version), "header_bytes": length,
        "header_sha256": hashlib.sha256(raw).hexdigest(),
        "header_ascii": header, "data_offset": offset, "shape": list(shape),
        "dtype_str": "<f4", "fortran_order": False,
        "payload_bytes": payload_bytes, "file_bytes": pin.file_bytes,
        "pickle_loader_used": False, "allow_pickle": False,
    }


def _verify_fd(path: Path, fd: int, initial: os.stat_result, pin: NpyPin) -> dict[str, Any]:
    pin.validate()
    if initial.st_size != pin.file_bytes:
        _fail("FILE_SIZE", "file size differs from the exact pin")
    info = _parse_header(fd, pin)
    file_hash = _digest(fd, 0, pin.file_bytes)
    if file_hash != pin.file_sha256:
        _fail("FILE_SHA256", "full NPY file differs from the exact pin")
    payload = hashlib.sha256()
    rows = []
    row_bytes = pin.shape[1] * 4
    for row in range(pin.shape[0]):
        raw = _read_exact(fd, row_bytes, info["data_offset"] + row * row_bytes, "FILE_CHANGED")
        payload.update(raw)
        rows.append(hashlib.sha256(raw).hexdigest())
    if payload.hexdigest() != pin.powers_sha256:
        _fail("POWERS_SHA256", "pure C-order payload differs from the exact pin")
    if pin.row_sha256 is not None and tuple(rows) != pin.row_sha256:
        _fail("ROW_SHA256", "one or more row bytes differ from their declared pins")
    _unchanged(path, fd, initial)
    info.update({"file_sha256": file_hash, "powers_sha256": payload.hexdigest(),
                 "row_sha256": rows, "read_only": True,
                 "file_identity": dict(zip(("device", "inode", "size", "mtime_ns", "ctime_ns"),
                                           _signature(initial)))})
    return info


class VerifiedNpy:
    """Own a read-only mapping and rehash the exact same file on phase exit.

    Array references must not be used after close.  ``verify_unchanged`` may be
    called at any additional phase boundary.  Hashes qualify transport only.
    """

    def __init__(self, path: os.PathLike[str] | str, pin: NpyPin,
                 *, require_nonnegative: bool = False):
        pin.validate()
        self.path, self._fd, self._initial = _open_regular(path)
        self.pin = pin
        self._array: np.memmap | None = None
        self._closed = False
        try:
            self.receipt = _verify_fd(self.path, self._fd, self._initial, pin)
            with os.fdopen(os.dup(self._fd), "rb") as source:
                self._array = np.memmap(source, dtype=np.dtype("<f4"), mode="r",
                                        offset=self.receipt["data_offset"], shape=pin.shape, order="C")
            if self._array.flags.writeable or not self._array.flags.c_contiguous:
                _fail("MAPPING", "mapping is not read-only C order")
            if require_nonnegative:
                for row in self._array:
                    if not bool(np.isfinite(row).all()) or not bool((row >= 0).all()):
                        _fail("VALUES", "nonfinite or negative powers; no masking or replacement")
            self.receipt["finite_nonnegative_checked"] = bool(require_nonnegative)
            self.verify_unchanged()
        except BaseException:
            self.close(verify=False)
            raise

    @property
    def array(self) -> np.memmap:
        if self._closed or self._array is None:
            _fail("MAPPING_CLOSED", "mapping has been closed")
        return self._array

    def verify_unchanged(self) -> dict[str, Any]:
        if self._closed:
            _fail("MAPPING_CLOSED", "mapping has been closed")
        result = _verify_fd(self.path, self._fd, self._initial, self.pin)
        if result != {k: v for k, v in self.receipt.items() if k != "finite_nonnegative_checked"}:
            _fail("FILE_CHANGED", "verification receipt changed")
        return result

    def close(self, *, verify: bool = True) -> None:
        if self._closed:
            return
        try:
            if verify:
                self.verify_unchanged()
        finally:
            if self._array is not None:
                self._array._mmap.close()
                self._array = None
            os.close(self._fd)
            self._closed = True

    def __enter__(self) -> "VerifiedNpy":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        self.close()
        return False


def open_verified_npy(path: os.PathLike[str] | str, pin: NpyPin,
                      *, require_nonnegative: bool = False) -> VerifiedNpy:
    """Open a pinned NPY; reduced shapes are exclusively for engineering fixtures."""
    return VerifiedNpy(path, pin, require_nonnegative=require_nonnegative)


_SCANS = (
    ("ON", "HIP45688", 64344, 57642.735972222225,
     "ca52b9508b4cce762586113ffa83fe4c5da026291a6d7d0444ae867bd565982c",
     "da74529faa7b288be9194dddce7be45c93446c554c97d143e8b01dab2df5073c"),
    ("OFF", "HIP44605", 64347, 57642.73994212963,
     "e8e135b4ab05abf0f8b36a1506a094a570279fdd91647f6c60ee984e80ef8b42",
     "78ac959b35902ef9687836f1bec4b9d48b6193e2dd70d0fa774ac7dfdcb1f502"),
    ("ON", "HIP45688", 64350, 57642.74390046296,
     "cdc8d50e34019d7dadab95522821465f66b3746deb755eee7fd1cf75484325bf",
     "62a4b7345e62602175e6816903ab61790dc608ac95ebe54af703667fe93b260e"),
    ("OFF", "HIP44646", 64353, 57642.74791666667,
     "747fd8b0bada7bd02b209b149104fc1de4782b428f674afd0bc7e108fc535b0d",
     "f525357d36117f10663c7d40bf811dbbdd9cf9f848cfac3510fdad6088caa198"),
    ("ON", "HIP45688", 64356, 57642.751921296294,
     "e1866b422d1beee7396da00c270a90fe5dfd2d350516b9247d67d5a4e7db196f",
     "7e1dc25401f73f2ffb784e040b4b4e24c722b7731e496de8759e90100b647070"),
    ("OFF", "HIP44707", 64359, 57642.75582175926,
     "4bfa5ea4609b61ed403ed983c9c4ca1365b052c2847ab15330ee21f005cd417a",
     "2b098e835a789ff7f31f96b312dc0128f749864e53e7c015957c3d1e85e24f2f"),
)


def expected_scan_binding(scan: int) -> dict[str, Any]:
    if type(scan) is not int or not 0 <= scan < 6:
        _fail("METADATA_BINDING", "scan must be an exact integer in [0,6)")
    role, target, archive_id, tstart, _, _ = _SCANS[scan]
    return {"scan": scan, "role": role, "target": target, "archive_id": archive_id,
            "header_tstart_mjd": tstart, "nrows": 16, "nchannels": 1048576,
            "channel_start": 180355072, "channel_stop_exclusive": 181403648,
            "fch1_slice_mhz": 1422.36328125, "df_hz": -2.7939677238464355,
            "dt_seconds": 18.253611008,
            "source_header_first_frequency_mhz": 1926.26953125,
            "source_nchannels": 322961408}


def verify_scan_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        _fail("METADATA_BINDING", "binding must be a mapping")
    expected = expected_scan_binding(binding.get("scan"))
    if set(binding) != set(expected) or any(type(binding[k]) is not type(v) or binding[k] != v
                                           for k, v in expected.items()):
        _fail("METADATA_BINDING", "metadata differs from fixed six-scan HIP45688 binding")
    return expected


def open_saved_scan(path: os.PathLike[str] | str, pin: NpyPin,
                    binding: Mapping[str, Any], *, require_nonnegative: bool = True) -> VerifiedNpy:
    """Later input activation only: fixed six native172 arrays, never BN geometry.

    Caller must authenticate metadata and the full ZIP member path separately.
    Neither a filename nor the NPY header establishes scan/source identity.
    No historical independent row receipt is claimed; newly derived rows are
    returned and may be pinned for subsequent phases.
    """
    verified = verify_scan_binding(binding)
    scan = verified["scan"]
    pin.validate()
    if pin.shape != FULL_SHAPE or (pin.file_sha256, pin.powers_sha256) != _SCANS[scan][4:6]:
        _fail("SCAN_PIN", "pin differs from the retained six-array identity")
    result = open_verified_npy(path, pin, require_nonnegative=require_nonnegative)
    result.metadata_binding = verified
    return result


@dataclass(frozen=True)
class ZipMemberPin:
    name: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ZipArchivePin:
    size_bytes: int
    sha256: str
    manifest_member: str
    manifest_bytes: int
    manifest_sha256: str
    member_root: str
    manifest_role: str
    members: tuple[ZipMemberPin, ...]  # All nonmanifest full names, not basenames.
    expected_member_count: int = 14


def _safe_name(name: Any) -> str:
    if (not isinstance(name, str) or not name or not name.isascii()
            or name.startswith("/") or "\\" in name or ":" in name
            or any(ord(c) < 32 or ord(c) == 127 for c in name)
            or any(part in ("", ".", "..") for part in name.split("/"))):
        _fail("ZIP_UNSAFE_NAME", "member name is not an exact safe relative POSIX path")
    return name


def _json_no_duplicates(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                _fail("MANIFEST_JSON", "duplicate JSON key")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda value: _fail("MANIFEST_JSON", f"nonfinite {value}"))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        _fail("MANIFEST_JSON", str(exc))


def verify_zip_manifest(path: os.PathLike[str] | str, pin: ZipArchivePin) -> dict[str, Any]:
    """Stream-verify an exact externally pinned ZIP and embedded manifest.

    This function never extracts or maps a member.  The external member pins
    must already be frozen; an unpinned manifest cannot authorize its own data.
    Production DATA activation remains a separate operation from E01 fixtures.
    The four-key M manifest schema below is authenticated by the recovered
    FORTSAETTELSE manifest, not yet by the unopened DATA_HIP45688 manifest.
    A mismatch in that future container fails closed; this implementation and
    E01 do not establish production DATA-manifest compatibility.
    """
    _integer(pin.size_bytes, "ZIP size", positive=True)
    _sha(pin.sha256, "ZIP SHA")
    _integer(pin.manifest_bytes, "manifest size", positive=True)
    if pin.manifest_bytes > CHUNK_BYTES:
        _fail("PIN_INVALID", "manifest exceeds the fixed 1 MiB metadata bound")
    _sha(pin.manifest_sha256, "manifest SHA")
    manifest_name = _safe_name(pin.manifest_member)
    root = _safe_name(pin.member_root)
    if not isinstance(pin.manifest_role, str) or not pin.manifest_role:
        _fail("PIN_INVALID", "explicit manifest role required")
    _integer(pin.expected_member_count, "member count", positive=True)
    if type(pin.members) is not tuple or len(pin.members) + 1 != pin.expected_member_count:
        _fail("PIN_INVALID", "external pins must cover every nonmanifest member")
    expected = {}
    for member in pin.members:
        name = _safe_name(member.name)
        _integer(member.size_bytes, "member size")
        _sha(member.sha256, "member SHA")
        if name == manifest_name or name in expected or not name.startswith(root + "/"):
            _fail("PIN_INVALID", "member names must be unique full names beneath fixed root")
        expected[name] = member
    p, fd, initial = _open_regular(path)
    try:
        if initial.st_size != pin.size_bytes:
            _fail("ZIP_SIZE", "ZIP size differs from external pin")
        if _digest(fd, 0, pin.size_bytes) != pin.sha256:
            _fail("ZIP_SHA256", "ZIP bytes differ from external pin")
        with os.fdopen(os.dup(fd), "rb") as source, zipfile.ZipFile(source, "r") as archive:
            infos = archive.infolist()
            names = []
            for info in infos:
                _safe_name(info.orig_filename)
                if info.orig_filename != info.filename:
                    _fail("ZIP_UNSAFE_NAME", "ZIP filename was transformed")
                names.append(info.filename)
                mode = info.external_attr >> 16
                if info.is_dir() or (info.external_attr & 0x10) or stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                    _fail("ZIP_MEMBER_TYPE", "only regular-file ZIP members are admitted")
                if info.flag_bits & 1:
                    _fail("ZIP_ENCRYPTED", "encrypted members are not admitted")
                if info.flag_bits & ~(0x800 | 0x8):
                    _fail("ZIP_FLAGS", "unsupported member flags")
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    _fail("ZIP_COMPRESSION", "unsupported compression method")
            if len(set(names)) != len(names):
                _fail("ZIP_DUPLICATE", "duplicate full member name")
            if len(names) != pin.expected_member_count or set(names) != set(expected) | {manifest_name}:
                _fail("ZIP_MEMBERS", "ZIP member set differs from exact external pins")
            manifest_info = archive.getinfo(manifest_name)
            if manifest_info.file_size != pin.manifest_bytes:
                _fail("MANIFEST_SIZE", "embedded manifest size differs from pin")
            with archive.open(manifest_info, "r") as entry:
                raw_manifest = entry.read(pin.manifest_bytes + 1)
            if len(raw_manifest) != pin.manifest_bytes:
                _fail("MANIFEST_SIZE", "embedded manifest length differs from pin")
            if hashlib.sha256(raw_manifest).hexdigest() != pin.manifest_sha256:
                _fail("MANIFEST_SHA256", "embedded manifest differs from external pin")
            manifest = _json_no_duplicates(raw_manifest)
            if (not isinstance(manifest, dict)
                    or set(manifest) != {"manifest_self_hash", "members", "role", "schema"}
                    or manifest["schema"] != "SETI_M_ARCHIVE_MEMBER_MANIFEST_V1"
                    or manifest["role"] != pin.manifest_role
                    or manifest["manifest_self_hash"] != "Bound separately in the archive-verification result."
                    or not isinstance(manifest["members"], list)):
                _fail("MANIFEST_SCHEMA", "embedded manifest schema/role/keys differ from contract")
            declared = {}
            for item in manifest["members"]:
                if not isinstance(item, dict) or set(item) != {"path", "size_bytes", "sha256"}:
                    _fail("MANIFEST_SCHEMA", "malformed manifest member")
                relative = _safe_name(item["path"])
                name = root + "/" + relative
                if name in declared:
                    _fail("MANIFEST_MEMBERS", "duplicate manifest member")
                if type(item["size_bytes"]) is not int or item["size_bytes"] < 0:
                    _fail("MANIFEST_SCHEMA", "invalid manifest member size")
                if not isinstance(item["sha256"], str) or _SHA.fullmatch(item["sha256"]) is None:
                    _fail("MANIFEST_SCHEMA", "invalid manifest member SHA")
                declared[name] = (item["size_bytes"], item["sha256"])
            if declared != {name: (m.size_bytes, m.sha256) for name, m in expected.items()}:
                _fail("MANIFEST_MEMBERS", "manifest declarations differ from external member pins")
            receipts = []
            for name, member in sorted(expected.items()):
                info = archive.getinfo(name)
                if info.file_size != member.size_bytes:
                    _fail("ZIP_MEMBER_SIZE", f"exact size mismatch: {name}")
                h = hashlib.sha256()
                total = 0
                with archive.open(info, "r") as entry:
                    while True:
                        block = entry.read(min(CHUNK_BYTES, member.size_bytes - total + 1))
                        if not block:
                            break
                        total += len(block)
                        if total > member.size_bytes:
                            _fail("ZIP_MEMBER_SIZE", f"stream exceeds exact size: {name}")
                        h.update(block)
                if total != member.size_bytes:
                    _fail("ZIP_MEMBER_SIZE", f"stream shorter than exact size: {name}")
                if h.hexdigest() != member.sha256:
                    _fail("ZIP_MEMBER_SHA256", f"member differs from exact pin: {name}")
                receipts.append({"name": name, "size_bytes": total, "sha256": h.hexdigest()})
        _unchanged(p, fd, initial)
        if _digest(fd, 0, pin.size_bytes) != pin.sha256:
            _fail("ZIP_SHA256", "ZIP changed during member verification")
        _unchanged(p, fd, initial)
        return {"status": "VERIFIED_BYTES_ONLY", "zip_sha256": pin.sha256,
                "zip_bytes": pin.size_bytes, "member_count": len(infos),
                "manifest_member": manifest_name, "manifest_sha256": pin.manifest_sha256,
                "manifest_bytes": pin.manifest_bytes, "manifest": manifest,
                "members": receipts, "extracted_members": 0,
                "telescope_decode_performed": False}
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError, OSError) as exc:
        _fail("ZIP_FORMAT", str(exc))
    finally:
        os.close(fd)
