"""Preregisterable E01 deterministic transport fixtures; no scores or RNG.

The case contract is source data below.  Import performs no fixture generation
or I/O.  Execution requires the public engineering plan and runner admission;
this file does not authorize itself or activate astronomical DATA inputs.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
from typing import Any, Callable
import zipfile


BO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BO_ROOT / "src"))
from npy_adapter import (  # noqa: E402
    AdapterError, FULL_SHAPE, NpyPin, ZipArchivePin, ZipMemberPin,
    expected_scan_binding, open_saved_scan, open_verified_npy,
    verify_scan_binding, verify_zip_manifest,
)


# Exact outcomes, frozen before fixture generation.  Rejections must match the
# named adapter error, not merely raise any exception.  Every case is retained.
CASE_CONTRACT = (
    ("npy_small_v1_exact", "ACCEPT"),
    ("npy_small_v2_exact", "ACCEPT"),
    ("npy_full_v1_exact", "ACCEPT"),
    ("npy_full_v2_exact", "ACCEPT"),
    ("npy_readonly_write_and_setflags", "ACCEPT"),
    ("npy_magic", "MAGIC"),
    ("npy_version3", "VERSION"),
    ("npy_truncated_length", "HEADER_TRUNCATED"),
    ("npy_truncated_header", "HEADER_TRUNCATED"),
    ("npy_oversized_header", "HEADER_LENGTH"),
    ("npy_missing_newline", "HEADER_LAYOUT"),
    ("npy_nonliteral_header", "HEADER_KEYS"),
    ("npy_duplicate_key", "HEADER_KEYS"),
    ("npy_missing_key", "HEADER_KEYS"),
    ("npy_extra_key", "HEADER_KEYS"),
    ("npy_dtype_big_endian", "DTYPE"),
    ("npy_dtype_native_endian_alias", "DTYPE"),
    ("npy_dtype_float64", "DTYPE"),
    ("npy_dtype_integer", "DTYPE"),
    ("npy_dtype_object", "DTYPE"),
    ("npy_dtype_structured", "DTYPE"),
    ("npy_dtype_subarray", "DTYPE"),
    ("npy_fortran_order", "ORDER"),
    ("npy_wrong_rank", "SHAPE"),
    ("npy_wrong_shape", "SHAPE"),
    ("npy_boolean_dimension", "SHAPE"),
    ("npy_negative_dimension", "SHAPE"),
    ("npy_truncated_payload", "PAYLOAD_SIZE"),
    ("npy_extra_payload", "PAYLOAD_SIZE"),
    ("npy_file_size_pin", "FILE_SIZE"),
    ("npy_file_hash_pin", "FILE_SHA256"),
    ("npy_payload_hash_pin", "POWERS_SHA256"),
    ("npy_row_hash_pin", "ROW_SHA256"),
    ("npy_changed_payload", "FILE_SHA256"),
    ("npy_negative_value", "VALUES"),
    ("npy_nonfinite_value", "VALUES"),
    ("npy_replaced_path_after_open", "FILE_CHANGED"),
    ("npy_symlink", "FILE_OPEN"),
    ("npy_directory", "FILE_TYPE"),
    ("npy_fifo_nonblocking", "FILE_TYPE"),
    ("metadata_six_exact_bindings", "ACCEPT"),
    ("metadata_wrong_archive_id", "METADATA_BINDING"),
    ("metadata_wrong_role", "METADATA_BINDING"),
    ("metadata_wrong_target", "METADATA_BINDING"),
    ("metadata_wrong_time", "METADATA_BINDING"),
    ("metadata_wrong_origin", "METADATA_BINDING"),
    ("metadata_BN_frequency", "METADATA_BINDING"),
    ("metadata_wrong_scan", "METADATA_BINDING"),
    ("metadata_extra_key", "METADATA_BINDING"),
    ("saved_scan_rejects_fixture_pin", "SCAN_PIN"),
    ("zip_exact_14_members", "ACCEPT"),
    ("zip_whole_size_pin", "ZIP_SIZE"),
    ("zip_whole_hash_pin", "ZIP_SHA256"),
    ("zip_manifest_size_pin", "MANIFEST_SIZE"),
    ("zip_manifest_hash_pin", "MANIFEST_SHA256"),
    ("zip_missing_member", "ZIP_MEMBERS"),
    ("zip_extra_member", "ZIP_MEMBERS"),
    ("zip_duplicate_member", "ZIP_DUPLICATE"),
    ("zip_traversal_name", "ZIP_UNSAFE_NAME"),
    ("zip_absolute_name", "ZIP_UNSAFE_NAME"),
    ("zip_backslash_name", "ZIP_UNSAFE_NAME"),
    ("zip_symlink_member", "ZIP_MEMBER_TYPE"),
    ("zip_encrypted_member", "ZIP_ENCRYPTED"),
    ("zip_member_size", "ZIP_MEMBER_SIZE"),
    ("zip_member_hash", "ZIP_MEMBER_SHA256"),
    ("zip_duplicate_json_key", "MANIFEST_JSON"),
    ("zip_manifest_external_disagreement", "MANIFEST_MEMBERS"),
    ("zip_manifest_extra_key", "MANIFEST_SCHEMA"),
)

FIXTURE_CONTRACT = {
    "schema": "SETI_BO_E01_DETERMINISTIC_BYTES_CONTRACT_V1",
    "gate": "E01", "gate_name": "E01_BYTES",
    "case_count": len(CASE_CONTRACT),
    "cases": [{"id": case_id, "expected": expected} for case_id, expected in CASE_CONTRACT],
    "small_shape": [3, 17],
    "full_shape": [16, 1048576],
    "NPY_versions": [[1, 0], [2, 0]],
    "payload_recipe": "float32-le((131*row+17*(column%1024))%4096)/8; exact binary fractions",
    "independent_oracle": "stdlib struct.pack('<f',value); concatenate 1024-channel periods; SHA256 raw file/payload/each row independently of adapter",
    "header_recipe": "literal 3-key dict, ASCII, newline, shortest padding to 64-byte total alignment",
    "zip_recipe": "fixed 1980-01-01 timestamp, stored regular members, 13 deterministic data members plus one M-format manifest; no extraction",
    "pass_rule": "all exact predetermined outcomes, bit-exact full rows and read-only enforcement; no partial admission",
    "future_DATA_manifest_compatibility_established": False,
    "astronomical_powers": False, "RNG_draws": 0, "scores": 0,
    "historical_M_status_changed": False,
}


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for raw in iter(lambda: source.read(1048576), b""):
            h.update(raw)
    return h.hexdigest()


def _exclusive(path: Path, raw: bytes) -> None:
    with path.open("xb") as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())


def _header(version: int, shape: tuple[int, ...], *, text: str | None = None) -> bytes:
    if text is None:
        text = repr({"descr": "<f4", "fortran_order": False, "shape": shape})
    raw = text.encode("ascii")
    prefix_bytes = 10 if version == 1 else 12
    raw += b" " * ((-(prefix_bytes + len(raw) + 1)) % 64) + b"\n"
    length = struct.pack("<H" if version == 1 else "<I", len(raw))
    return b"\x93NUMPY" + bytes((version, 0)) + length + raw


def _row_bytes(row: int, columns: int) -> bytes:
    period = b"".join(struct.pack("<f", ((131 * row + 17 * c) % 4096) / 8.0)
                      for c in range(1024))
    complete, tail = divmod(columns, 1024)
    return period * complete + period[:tail * 4]


def _fixture(path: Path, shape: tuple[int, int], version: int) -> NpyPin:
    header = _header(version, shape)
    full = hashlib.sha256(header)
    payload = hashlib.sha256()
    rows = []
    with path.open("xb") as target:
        target.write(header)
        for row in range(shape[0]):
            raw = _row_bytes(row, shape[1])
            target.write(raw)
            full.update(raw)
            payload.update(raw)
            rows.append(_hash(raw))
        target.flush()
        os.fsync(target.fileno())
    return NpyPin(len(header) + shape[0] * shape[1] * 4, full.hexdigest(),
                  payload.hexdigest(), shape, tuple(rows))


def _exact(path: Path, pin: NpyPin) -> dict[str, Any]:
    with open_verified_npy(path, pin, require_nonnegative=True) as mapped:
        if (tuple(mapped.array.shape) != pin.shape or mapped.array.dtype.str != "<f4"
                or not mapped.array.flags.c_contiguous or mapped.array.flags.writeable):
            raise AssertionError("mapping shape/dtype/order/readonly differs")
        for row in range(pin.shape[0]):
            if mapped.array[row].tobytes(order="C") != _row_bytes(row, pin.shape[1]):
                raise AssertionError(f"independent exact row mismatch: {row}")
        if (tuple(mapped.receipt["row_sha256"]) != pin.row_sha256
                or mapped.receipt["file_sha256"] != pin.file_sha256
                or mapped.receipt["powers_sha256"] != pin.powers_sha256):
            raise AssertionError("independent hash pins differ")
        before = mapped.receipt
        mapped.verify_unchanged()
        return {"verified": before, "all_rows_bit_exact": True}


def _open_only(path: Path, pin: NpyPin, *, values: bool = False) -> dict[str, Any]:
    with open_verified_npy(path, pin, require_nonnegative=values) as mapped:
        return mapped.receipt


def _readonly(path: Path, pin: NpyPin) -> dict[str, bool]:
    with open_verified_npy(path, pin) as mapped:
        denied = []
        try:
            mapped.array[0, 0] = 1.0
        except ValueError:
            denied.append("assignment")
        try:
            mapped.array.setflags(write=True)
        except ValueError:
            denied.append("setflags")
        if denied != ["assignment", "setflags"]:
            raise AssertionError("read-only map allowed a mutation path")
    return {"assignment_rejected": True, "setflags_rejected": True}


def _pin_for_raw(raw: bytes, shape: tuple[int, int], base: NpyPin) -> NpyPin:
    # For malformed transport fixtures the expected powers pin remains fixed;
    # malformed headers/sizes must fail before any data repair is possible.
    return replace(base, file_bytes=len(raw), file_sha256=_hash(raw), shape=shape)


def _zip_base() -> tuple[list[tuple[str, bytes, int]], bytes, tuple[ZipMemberPin, ...]]:
    root = "fixture"
    entries = []
    for scan in range(6):
        entries.append((f"{root}/arrays/scan{scan}.npy", _header(1, (1, 1)) + struct.pack("<f", scan / 8.0), stat.S_IFREG | 0o444))
        entries.append((f"{root}/metadata/scan{scan}.json", _json_bytes({"fixture_scan": scan}), stat.S_IFREG | 0o444))
    entries.append((f"{root}/control/row7.txt", b"E01 deterministic transport fixture only\n", stat.S_IFREG | 0o444))
    members = tuple(ZipMemberPin(name, len(raw), _hash(raw)) for name, raw, _ in entries)
    manifest = {"schema": "SETI_M_ARCHIVE_MEMBER_MANIFEST_V1", "role": "E01_FIXTURE",
                "manifest_self_hash": "Bound separately in the archive-verification result.",
                "members": [{"path": m.name[len(root) + 1:], "size_bytes": m.size_bytes, "sha256": m.sha256}
                            for m in members]}
    return entries, _json_bytes(manifest), members


def _zip_fixture(path: Path, *, entries: list[tuple[str, bytes, int]] | None = None,
                 manifest: bytes | None = None, encrypt: bool = False) -> ZipArchivePin:
    original, original_manifest, members = _zip_base()
    if entries is None:
        entries = original
    if manifest is None:
        manifest = original_manifest
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw, mode in entries + [("fixture/_MANIFESTS/E01.json", manifest, stat.S_IFREG | 0o444)]:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, raw)
    raw = bytearray(stream.getvalue())
    if encrypt:
        # Set encryption on the first local and central records.  This is a
        # malformed fixture, never an actual encrypted telescope container.
        local = raw.index(b"PK\x03\x04")
        central = raw.index(b"PK\x01\x02")
        struct.pack_into("<H", raw, local + 6, struct.unpack_from("<H", raw, local + 6)[0] | 1)
        struct.pack_into("<H", raw, central + 8, struct.unpack_from("<H", raw, central + 8)[0] | 1)
    _exclusive(path, bytes(raw))
    return ZipArchivePin(len(raw), _hash(raw), "fixture/_MANIFESTS/E01.json", len(manifest),
                         _hash(manifest), "fixture", "E01_FIXTURE", members)


def _load_config(path: Path) -> tuple[dict[str, Any], str, dict[str, str]]:
    raw = path.read_bytes()
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate plan key")
            result[key] = value
        return result
    config = json.loads(raw, object_pairs_hook=pairs)
    if (config.get("schema") != "SETI_BO_ENGINEERING_PLAN_V1"
            or config.get("engineering_only") is not True
            or config.get("real_telescope_powers_authorized") is not False
            or config.get("rng_authorized") is not False
            or config.get("scientific_scores_authorized") is not False):
        raise ValueError("plan does not admit only deterministic engineering")
    pins = config.get("source_pins")
    if not isinstance(pins, list):
        raise ValueError("source_pins list required")
    found = {}
    for pin in pins:
        if not isinstance(pin, dict) or not isinstance(pin.get("path"), str) or not isinstance(pin.get("sha256"), str):
            raise ValueError("malformed source pin")
        relative = pin["path"]
        if relative in found or relative.startswith("/") or "\\" in relative or any(p in ("", ".", "..") for p in relative.split("/")):
            raise ValueError("ambiguous source path")
        target = BO_ROOT / relative
        if target.resolve() != target.absolute() or not target.is_file() or _file_hash(target) != pin["sha256"]:
            raise ValueError(f"source pin mismatch: {relative}")
        found[relative] = pin["sha256"]
    for required in ("src/npy_adapter.py", "gates/e01_bytes.py"):
        if required not in found:
            raise ValueError(f"missing source pin: {required}")
    return config, _hash(raw), found


def run(config_path: Path, output: Path) -> tuple[dict[str, Any], str]:
    config, config_sha, source_pins = _load_config(config_path)
    declared_output = config.get("gate_outputs", {}).get("E01")
    if not isinstance(declared_output, str) or output.resolve() != Path(declared_output).resolve():
        raise ValueError("output differs from the frozen E01 gate path")
    output.mkdir(parents=False, exist_ok=False)
    fixtures = output / "fixtures"
    fixtures.mkdir(exist_ok=False)
    results: list[dict[str, Any]] = []
    actions: dict[str, Callable[[], Any]] = {}
    small_shape = (3, 17)
    small = fixtures / "small_v1.npy"
    small_pin = _fixture(small, small_shape, 1)
    small_raw = small.read_bytes()
    for version in (1, 2):
        for label, shape in (("small", small_shape), ("full", FULL_SHAPE)):
            if label == "small" and version == 1:
                path, pin = small, small_pin
            else:
                path = fixtures / f"{label}_v{version}.npy"
                pin = _fixture(path, shape, version)
            actions[f"npy_{label}_v{version}_exact"] = lambda p=path, n=pin: _exact(p, n)
    actions["npy_readonly_write_and_setflags"] = lambda: _readonly(small, small_pin)

    malformed: dict[str, bytes] = {
        "npy_magic": b"X" + small_raw[1:],
        "npy_version3": small_raw[:6] + b"\x03\x00" + small_raw[8:],
        "npy_truncated_length": small_raw[:9],
        "npy_truncated_header": small_raw[:20],
        "npy_oversized_header": b"\x93NUMPY\x02\x00" + struct.pack("<I", 65537),
        "npy_missing_newline": small_raw[:127] + b" " + small_raw[128:],
        "npy_truncated_payload": small_raw[:-1],
        "npy_extra_payload": small_raw + b"X",
    }
    texts = {
        "npy_nonliteral_header": "dict(descr='<f4', fortran_order=False, shape=(3,17))",
        "npy_duplicate_key": "{'descr':'<f4','descr':'<f4','fortran_order':False,'shape':(3,17)}",
        "npy_missing_key": "{'descr':'<f4','shape':(3,17)}",
        "npy_extra_key": "{'descr':'<f4','fortran_order':False,'shape':(3,17),'other':1}",
        "npy_dtype_big_endian": "{'descr':'>f4','fortran_order':False,'shape':(3,17)}",
        "npy_dtype_native_endian_alias": "{'descr':'=f4','fortran_order':False,'shape':(3,17)}",
        "npy_dtype_float64": "{'descr':'<f8','fortran_order':False,'shape':(3,17)}",
        "npy_dtype_integer": "{'descr':'<i4','fortran_order':False,'shape':(3,17)}",
        "npy_dtype_object": "{'descr':'|O','fortran_order':False,'shape':(3,17)}",
        "npy_dtype_structured": "{'descr':[('x','<f4')],'fortran_order':False,'shape':(3,17)}",
        "npy_dtype_subarray": "{'descr':('<f4',(1,)),'fortran_order':False,'shape':(3,17)}",
        "npy_fortran_order": "{'descr':'<f4','fortran_order':True,'shape':(3,17)}",
        "npy_wrong_rank": "{'descr':'<f4','fortran_order':False,'shape':(51,)}",
        "npy_wrong_shape": "{'descr':'<f4','fortran_order':False,'shape':(17,3)}",
        "npy_boolean_dimension": "{'descr':'<f4','fortran_order':False,'shape':(True,17)}",
        "npy_negative_dimension": "{'descr':'<f4','fortran_order':False,'shape':(-3,17)}",
    }
    payload = small_raw[128:]
    for name, text in texts.items():
        malformed[name] = _header(1, small_shape, text=text) + payload
    for name, raw in malformed.items():
        path = fixtures / f"{name}.npy"
        _exclusive(path, raw)
        pin = _pin_for_raw(raw, small_shape, small_pin)
        actions[name] = lambda p=path, n=pin: _open_only(p, n)
    actions["npy_file_size_pin"] = lambda: _open_only(small, replace(small_pin, file_bytes=small_pin.file_bytes + 1))
    actions["npy_file_hash_pin"] = lambda: _open_only(small, replace(small_pin, file_sha256="0" * 64))
    actions["npy_payload_hash_pin"] = lambda: _open_only(small, replace(small_pin, powers_sha256="0" * 64))
    actions["npy_row_hash_pin"] = lambda: _open_only(small, replace(small_pin, row_sha256=("0" * 64,) + small_pin.row_sha256[1:]))
    changed = fixtures / "changed_payload.npy"
    _exclusive(changed, small_raw[:-1] + bytes((small_raw[-1] ^ 1,)))
    actions["npy_changed_payload"] = lambda: _open_only(changed, small_pin)
    for name, value in (("npy_negative_value", -1.0), ("npy_nonfinite_value", float("nan"))):
        raw_payload = struct.pack("<f", value) + payload[4:]
        raw = small_raw[:128] + raw_payload
        path = fixtures / f"{name}.npy"
        _exclusive(path, raw)
        pin = NpyPin(len(raw), _hash(raw), _hash(raw_payload), small_shape)
        actions[name] = lambda p=path, n=pin: _open_only(p, n, values=True)
    replace_path = fixtures / "path_replacement.npy"
    _exclusive(replace_path, small_raw)
    replacement = fixtures / "path_replacement_new.npy"
    _exclusive(replacement, small_raw)
    def replaced_path() -> None:
        mapped = open_verified_npy(replace_path, small_pin)
        try:
            os.replace(replacement, replace_path)
            mapped.verify_unchanged()
        finally:
            mapped.close(verify=False)
    actions["npy_replaced_path_after_open"] = replaced_path
    symlink = fixtures / "symlink.npy"
    symlink.symlink_to(small.name)
    actions["npy_symlink"] = lambda: _open_only(symlink, small_pin)
    actions["npy_directory"] = lambda: _open_only(fixtures, small_pin)
    fifo = fixtures / "nonblocking_fifo.npy"
    os.mkfifo(fifo, mode=0o600)
    actions["npy_fifo_nonblocking"] = lambda: _open_only(fifo, small_pin)
    def exact_bindings() -> dict[str, Any]:
        return {"bindings": [verify_scan_binding(expected_scan_binding(scan)) for scan in range(6)],
                "metadata_only": True, "astronomical_arrays_opened": 0}
    actions["metadata_six_exact_bindings"] = exact_bindings
    for name, key, value in (
        ("metadata_wrong_archive_id", "archive_id", 85030),
        ("metadata_wrong_role", "role", "OFF"),
        ("metadata_wrong_target", "target", "HIP98505"),
        ("metadata_wrong_time", "header_tstart_mjd", 57642.73597222223),
        ("metadata_wrong_origin", "channel_start", 0),
        ("metadata_BN_frequency", "fch1_slice_mhz", 2298.92578125),
        ("metadata_wrong_scan", "scan", 1),
        ("metadata_extra_key", "unapproved", True),
    ):
        binding = expected_scan_binding(0)
        binding[key] = value
        actions[name] = lambda b=binding: verify_scan_binding(b)
    actions["saved_scan_rejects_fixture_pin"] = lambda: open_saved_scan(small, small_pin, expected_scan_binding(0))

    zip_path = fixtures / "zip_exact.zip"
    zip_pin = _zip_fixture(zip_path)
    actions["zip_exact_14_members"] = lambda: verify_zip_manifest(zip_path, zip_pin)
    for name, pin in (
        ("zip_whole_size_pin", replace(zip_pin, size_bytes=zip_pin.size_bytes + 1)),
        ("zip_whole_hash_pin", replace(zip_pin, sha256="0" * 64)),
        ("zip_manifest_size_pin", replace(zip_pin, manifest_bytes=zip_pin.manifest_bytes + 1)),
        ("zip_manifest_hash_pin", replace(zip_pin, manifest_sha256="0" * 64)),
    ):
        actions[name] = lambda n=pin: verify_zip_manifest(zip_path, n)
    entries, manifest_raw, _ = _zip_base()
    zip_variants = {
        "zip_missing_member": entries[1:],
        "zip_extra_member": entries + [("fixture/extra.txt", b"extra", stat.S_IFREG | 0o444)],
        "zip_duplicate_member": entries + [entries[0]],
        "zip_traversal_name": [("fixture/../escape.npy", entries[0][1], entries[0][2])] + entries[1:],
        "zip_absolute_name": [("/escape.npy", entries[0][1], entries[0][2])] + entries[1:],
        "zip_backslash_name": [("fixture\\escape.npy", entries[0][1], entries[0][2])] + entries[1:],
        "zip_symlink_member": [(entries[0][0], entries[0][1], stat.S_IFLNK | 0o777)] + entries[1:],
        "zip_member_size": [(entries[0][0], entries[0][1] + b"X", entries[0][2])] + entries[1:],
        "zip_member_hash": [(entries[0][0], entries[0][1][:-1] + b"X", entries[0][2])] + entries[1:],
    }
    for name, variant in zip_variants.items():
        path = fixtures / f"{name}.zip"
        pin = _zip_fixture(path, entries=variant)
        actions[name] = lambda p=path, n=pin: verify_zip_manifest(p, n)
    encrypted = fixtures / "zip_encrypted_member.zip"
    encrypted_pin = _zip_fixture(encrypted, encrypt=True)
    actions["zip_encrypted_member"] = lambda: verify_zip_manifest(encrypted, encrypted_pin)
    duplicate_json = b'{"schema":"SETI_M_ARCHIVE_MEMBER_MANIFEST_V1",' + manifest_raw.lstrip()[1:]
    mismatch = json.loads(manifest_raw)
    mismatch["members"][0]["sha256"] = "0" * 64
    extra = json.loads(manifest_raw)
    extra["unapproved"] = True
    for name, raw in (("zip_duplicate_json_key", duplicate_json),
                      ("zip_manifest_external_disagreement", _json_bytes(mismatch)),
                      ("zip_manifest_extra_key", _json_bytes(extra))):
        path = fixtures / f"{name}.zip"
        pin = _zip_fixture(path, manifest=raw)
        actions[name] = lambda p=path, n=pin: verify_zip_manifest(p, n)

    if set(actions) != {name for name, _ in CASE_CONTRACT}:
        raise AssertionError("implemented actions differ from frozen case contract")
    _exclusive(output / "CASE_CONTRACT.json", _json_bytes(FIXTURE_CONTRACT))
    for case_id, expected in CASE_CONTRACT:
        row = {"id": case_id, "expected": expected}
        try:
            detail = actions[case_id]()
            row.update({"actual": "ACCEPT", "detail": detail})
        except AdapterError as exc:
            row.update({"actual": exc.code, "detail": str(exc)})
        except Exception as exc:
            row.update({"actual": "UNEXPECTED_EXCEPTION", "detail": f"{type(exc).__name__}: {exc}"})
        row["pass"] = row["actual"] == expected
        results.append(row)
    # Source and config are revalidated after every fixed case has completed.
    _, ending_config_sha, ending_pins = _load_config(config_path)
    pins_unchanged = ending_config_sha == config_sha and ending_pins == source_pins
    evidence = []
    stored_bytes = 0
    for path in sorted(output.rglob("*")):
        if path.is_symlink():
            evidence.append({"path": str(path.relative_to(output)), "symlink_target": os.readlink(path)})
        elif path.is_file():
            size = path.stat().st_size
            stored_bytes += size
            evidence.append({"path": str(path.relative_to(output)), "size_bytes": size, "sha256": _file_hash(path)})
        elif stat.S_ISFIFO(path.lstat().st_mode):
            evidence.append({"path": str(path.relative_to(output)), "file_type": "FIFO",
                             "mode": stat.S_IMODE(path.lstat().st_mode),
                             "payload_bytes": 0, "opened_only_nonblocking_then_rejected": True})
    status = "PASS" if pins_unchanged and all(row["pass"] for row in results) and stored_bytes < 536870912 else "FAIL"
    result = {"schema": "SETI_BO_E01_BYTES_RESULT_V1", "gate": "E01", "gate_name": "E01_BYTES", "status": status,
              "config_sha256": config_sha, "source_pins": source_pins,
              "source_and_config_pins_unchanged": pins_unchanged,
              "contract_sha256": _hash(_json_bytes(FIXTURE_CONTRACT)),
              "case_count": len(results), "passed_cases": sum(row["pass"] for row in results),
              "failed_cases": sum(not row["pass"] for row in results), "cases": results,
              "evidence": evidence, "stored_fixture_and_contract_bytes": stored_bytes,
              "no_partial_admission": True,
              "operations": {"astronomical_arrays_opened": 0, "raw_DATA_archives_opened": 0,
                             "RNG_draws": 0, "scores": 0, "telescope_decodes": 0},
              "qualification": "Deterministic saved-byte transport only; no future DATA manifest, astronomical value, normalization, numerical, paired synthetic or historical M qualification follows."}
    raw_result = _json_bytes(result)
    _exclusive(output / "RESULT.json", raw_result)
    return result, _hash(raw_result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result, digest = run(args.config.absolute(), args.out.absolute())
    print(json.dumps({"event": "GATE_TERMINAL_EOF", "status": result["status"],
                      "result_sha256": digest}, sort_keys=True), flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
