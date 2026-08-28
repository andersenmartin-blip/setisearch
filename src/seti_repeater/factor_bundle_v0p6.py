"""Persistent, independently verifiable M37 detector-v0.6 factor bundles.

The factor basis and template-factor table are derived entirely from frozen
metadata.  This module stores the small arrays in one atomic artifact so a
later process can use them without repeating an astronomy calculation.  It
does not import an HDF5 reader, open a remote object, or authorize spectral
access.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import struct
from typing import Any, Mapping, Sequence

import numpy as np

from . import search_v0p6 as core


_MAGIC = b"M37FB06\0"
_FORMAT_VERSION = 1
_HEADER = struct.Struct("<8sII32s")
_MAXIMUM_MANIFEST_BYTES = 1_048_576
_PAYLOAD_ORDER = ("times_mjd", "baseline", "orbital", "factors")
_HEX = frozenset("0123456789abcdef")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _frozen_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise core.V0P6ContractError(f"{label} is not a lowercase SHA-256")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise core.V0P6ContractError(
                f"factor-bundle manifest repeats key {key!r}"
            )
        result[key] = value
    return result


def _detached_json(value: Any, label: str) -> Any:
    try:
        return json.loads(core.canonical_json_bytes(value))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            f"{label} is not canonical finite JSON"
        ) from error


def _strict_digest_mapping(value: Mapping[str, Any], label: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise core.V0P6ContractError(f"{label} must be a non-empty mapping")
    result: dict[str, str] = {}
    for raw_key, raw_digest in value.items():
        if not isinstance(raw_key, str) or not raw_key:
            raise core.V0P6ContractError(f"{label} keys must be non-empty strings")
        result[raw_key] = _frozen_sha256(raw_digest, f"{label} {raw_key}")
    return dict(sorted(result.items()))


def _array_bytes(value: np.ndarray) -> tuple[np.ndarray, bytes]:
    array = np.ascontiguousarray(value, dtype="<f8")
    if not np.all(np.isfinite(array)):
        raise core.V0P6ContractError("factor-bundle arrays must be finite")
    return array, array.tobytes(order="C")


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset:])
        if written <= 0:
            raise OSError("short write while publishing factor bundle")
        offset += written


def _read_exact(descriptor: int, count: int, offset: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    cursor = offset
    while remaining:
        chunk = os.pread(descriptor, remaining, cursor)
        if not chunk:
            raise core.V0P6IncompleteError("factor-bundle file is truncated")
        chunks.append(chunk)
        remaining -= len(chunk)
        cursor += len(chunk)
    return b"".join(chunks)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class FactorBundleReceipt:
    """Independent identities returned by an atomic factor-bundle publish."""

    manifest_sha256: str
    file_sha256: str
    factor_basis_sha256: str
    factor_basis_labels_sha256: str
    factor_table_sha256: str
    analysis_contract_sha256: str
    environment_sha256: str
    source_metadata_sha256: str
    file_nbytes: int


@dataclass(frozen=True)
class FactorBundle:
    """A rehydrated M37 factor bundle and its trusted receipt."""

    basis: core.FactorBasis
    table: core.TemplateFactorTable
    template_bank: tuple[dict[str, Any], ...]
    scans: tuple[dict[str, Any], ...]
    environment: dict[str, Any]
    source_hashes: dict[str, str]
    receipt: FactorBundleReceipt


def _manifest_and_payloads(
    basis: core.FactorBasis,
    table: core.TemplateFactorTable,
    template_bank: Sequence[Mapping[str, Any]],
    scans: Sequence[Mapping[str, Any]],
    *,
    environment: Mapping[str, Any],
    source_hashes: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, bytes]]:
    core.validate_factor_basis(basis)
    bank = _detached_json(list(template_bank), "factor-bundle template bank")
    if not isinstance(bank, list):
        raise core.V0P6ContractError("factor-bundle template bank is invalid")
    scans_record = _detached_json(list(scans), "factor-bundle scan inventory")
    if not isinstance(scans_record, list):
        raise core.V0P6ContractError("factor-bundle scan inventory is invalid")
    core.validate_m37_factor_basis_scan_inventory(basis, scans_record)
    core.validate_template_factor_table(
        table,
        basis,
        bank,
        expected_template_bank_sha256=core.M37_BANK_SHA256,
    )
    scan_digest = core.scan_inventory_sha256(scans_record)
    if scan_digest != core.M37_SCAN_INVENTORY_SHA256:
        raise core.V0P6ContractError("factor-bundle scan inventory changed")

    environment_record = _detached_json(environment, "factor-bundle environment")
    if not isinstance(environment_record, dict) or not environment_record:
        raise core.V0P6ContractError(
            "factor-bundle environment must be a non-empty mapping"
        )
    environment_digest = _sha256_bytes(
        core.canonical_json_bytes(environment_record)
    )
    source_records = _strict_digest_mapping(source_hashes, "source hash")
    source_digest = _sha256_bytes(core.canonical_json_bytes(source_records))

    arrays = {
        "times_mjd": basis.times_mjd,
        "baseline": basis.baseline,
        "orbital": basis.orbital,
        "factors": table.factors,
    }
    payloads: dict[str, bytes] = {}
    payload_records: list[dict[str, Any]] = []
    offset = 0
    for name in _PAYLOAD_ORDER:
        array, payload = _array_bytes(arrays[name])
        payloads[name] = payload
        payload_records.append(
            {
                "name": name,
                "dtype": "<f8",
                "shape": list(array.shape),
                "offset": offset,
                "nbytes": len(payload),
                "sha256": _sha256_bytes(payload),
            }
        )
        offset += len(payload)

    labels = [label.as_record() for label in basis.labels]
    analysis_contract = core.factorized_analysis_contract_sha256(
        core.M37_EXPERIMENT_CONTRACT_SHA256,
        basis.basis_sha256,
        basis.labels_sha256,
        scan_digest,
        table.factor_table_sha256,
    )
    proxy_grid_sha256s = {
        window_id: core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(window_id)
        )
        for window_id in core.M37_WINDOW_IDS
    }
    manifest = {
        "schema_version": 1,
        "artifact_type": "m37-detector-v0p6-factor-bundle-v1",
        "detector_version": core.DETECTOR_VERSION,
        "spectral_access_authorized": False,
        "spectral_dataset_values_read": False,
        "experiment_contract_sha256": core.M37_EXPERIMENT_CONTRACT_SHA256,
        "analysis_contract_sha256": analysis_contract,
        "factor_basis_sha256": basis.basis_sha256,
        "factor_basis_labels_sha256": basis.labels_sha256,
        "factor_table_sha256": table.factor_table_sha256,
        "template_bank_sha256": table.template_bank_sha256,
        "scan_inventory_sha256": scan_digest,
        "factor_row_selection_sha256s": {
            kind: core.factor_row_selection_sha256(basis, scans_record, kind)
            for kind in ("on", "off")
        },
        "factor_scan_selection_sha256s": {
            scan["label"]: core.factor_scan_selection_sha256(
                basis, scans_record, str(scan["label"])
            )
            for scan in scans_record
        },
        "proxy_carrier_grid_sha256s": proxy_grid_sha256s,
        "scramble_table_sha256s": list(core.M37_SCRAMBLE_TABLE_SHA256S),
        "scramble_tables_aggregate_sha256": core.M37_SCRAMBLE_TABLES_SHA256,
        "environment": environment_record,
        "environment_sha256": environment_digest,
        "source_hashes": source_records,
        "source_metadata_sha256": source_digest,
        "labels": labels,
        "template_bank": bank,
        "scans": scans_record,
        "payloads": payload_records,
        "payload_nbytes": offset,
    }
    return manifest, payloads


def publish_m37_factor_bundle(
    path: str | os.PathLike[str],
    basis: core.FactorBasis,
    table: core.TemplateFactorTable,
    template_bank: Sequence[Mapping[str, Any]],
    scans: Sequence[Mapping[str, Any]],
    *,
    environment: Mapping[str, Any],
    source_hashes: Mapping[str, Any],
) -> FactorBundleReceipt:
    """Atomically publish one immutable M37 factor-bundle file.

    The destination must not already exist.  A hard-link publication step
    prevents an existing artifact from being silently replaced.
    """
    destination = Path(path)
    parent = destination.parent
    if not parent.is_dir():
        raise core.V0P6ContractError("factor-bundle parent directory is absent")
    if destination.exists():
        raise FileExistsError(destination)

    manifest, payloads = _manifest_and_payloads(
        basis,
        table,
        template_bank,
        scans,
        environment=environment,
        source_hashes=source_hashes,
    )
    manifest_bytes = core.canonical_json_bytes(manifest)
    if len(manifest_bytes) > _MAXIMUM_MANIFEST_BYTES:
        raise core.V0P6CapacityError("factor-bundle manifest exceeds its cap")
    manifest_digest = _sha256_bytes(manifest_bytes)
    header = _HEADER.pack(
        _MAGIC,
        _FORMAT_VERSION,
        len(manifest_bytes),
        bytes.fromhex(manifest_digest),
    )
    temporary = parent / (
        f".{destination.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        _write_all(descriptor, header)
        _write_all(descriptor, manifest_bytes)
        for name in _PAYLOAD_ORDER:
            _write_all(descriptor, payloads[name])
        os.fchmod(descriptor, 0o444)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, destination)
        except FileExistsError:
            raise FileExistsError(destination) from None
        os.unlink(temporary)
        _fsync_directory(parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()

    file_bytes = destination.read_bytes()
    return FactorBundleReceipt(
        manifest_sha256=manifest_digest,
        file_sha256=_sha256_bytes(file_bytes),
        factor_basis_sha256=manifest["factor_basis_sha256"],
        factor_basis_labels_sha256=manifest["factor_basis_labels_sha256"],
        factor_table_sha256=manifest["factor_table_sha256"],
        analysis_contract_sha256=manifest["analysis_contract_sha256"],
        environment_sha256=manifest["environment_sha256"],
        source_metadata_sha256=manifest["source_metadata_sha256"],
        file_nbytes=len(file_bytes),
    )


def _parse_manifest(raw: bytes, expected_sha256: str) -> dict[str, Any]:
    if _sha256_bytes(raw) != _frozen_sha256(
        expected_sha256, "expected factor-bundle manifest identity"
    ):
        raise core.V0P6IncompleteError("factor-bundle manifest identity changed")
    try:
        manifest = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError("factor-bundle manifest is invalid JSON") from error
    if core.canonical_json_bytes(manifest) != raw:
        raise core.V0P6ContractError("factor-bundle manifest is not canonical JSON")
    if not isinstance(manifest, dict):
        raise core.V0P6ContractError("factor-bundle manifest is not a mapping")
    return manifest


def _validate_manifest_envelope(manifest: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_type",
        "detector_version",
        "spectral_access_authorized",
        "spectral_dataset_values_read",
        "experiment_contract_sha256",
        "analysis_contract_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "factor_table_sha256",
        "template_bank_sha256",
        "scan_inventory_sha256",
        "factor_row_selection_sha256s",
        "factor_scan_selection_sha256s",
        "proxy_carrier_grid_sha256s",
        "scramble_table_sha256s",
        "scramble_tables_aggregate_sha256",
        "environment",
        "environment_sha256",
        "source_hashes",
        "source_metadata_sha256",
        "labels",
        "template_bank",
        "scans",
        "payloads",
        "payload_nbytes",
    }
    if set(manifest) != required:
        raise core.V0P6ContractError("factor-bundle manifest schema changed")
    if (
        manifest["schema_version"] != 1
        or manifest["artifact_type"] != "m37-detector-v0p6-factor-bundle-v1"
        or manifest["detector_version"] != core.DETECTOR_VERSION
        or manifest["spectral_access_authorized"] is not False
        or manifest["spectral_dataset_values_read"] is not False
        or manifest["experiment_contract_sha256"]
        != core.M37_EXPERIMENT_CONTRACT_SHA256
        or manifest["factor_basis_sha256"] != core.M37_FACTOR_BASIS_SHA256
        or manifest["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or manifest["template_bank_sha256"] != core.M37_BANK_SHA256
        or manifest["scan_inventory_sha256"] != core.M37_SCAN_INVENTORY_SHA256
        or manifest["scramble_table_sha256s"]
        != list(core.M37_SCRAMBLE_TABLE_SHA256S)
        or manifest["scramble_tables_aggregate_sha256"]
        != core.M37_SCRAMBLE_TABLES_SHA256
    ):
        raise core.V0P6IncompleteError("factor-bundle frozen M37 contract changed")
    if manifest["factor_row_selection_sha256s"] != core.M37_FACTOR_ROW_SELECTION_SHA256S:
        raise core.V0P6IncompleteError("factor-bundle row selections changed")
    if manifest["factor_scan_selection_sha256s"] != core.M37_FACTOR_SCAN_SELECTION_SHA256S:
        raise core.V0P6IncompleteError("factor-bundle scan selections changed")
    expected_grids = {
        window_id: core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(window_id)
        )
        for window_id in core.M37_WINDOW_IDS
    }
    if manifest["proxy_carrier_grid_sha256s"] != expected_grids:
        raise core.V0P6IncompleteError("factor-bundle proxy grids changed")
    environment = _detached_json(manifest["environment"], "bundle environment")
    if not isinstance(environment, dict) or not environment:
        raise core.V0P6ContractError("factor-bundle environment is invalid")
    if _sha256_bytes(core.canonical_json_bytes(environment)) != manifest[
        "environment_sha256"
    ]:
        raise core.V0P6IncompleteError("factor-bundle environment identity changed")
    source_hashes = _strict_digest_mapping(manifest["source_hashes"], "source hash")
    if _sha256_bytes(core.canonical_json_bytes(source_hashes)) != manifest[
        "source_metadata_sha256"
    ]:
        raise core.V0P6IncompleteError("factor-bundle source identity changed")


def open_m37_factor_bundle(
    path: str | os.PathLike[str],
    *,
    expected_manifest_sha256: str,
    expected_file_sha256: str,
    expected_factor_table_sha256: str,
) -> FactorBundle:
    """Rehydrate a bundle only against independent manifest and file digests."""
    bundle_path = Path(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(bundle_path, flags)
    try:
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(bundle_path, follow_symlinks=False)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(path_metadata.st_mode)
            or metadata.st_dev != path_metadata.st_dev
            or metadata.st_ino != path_metadata.st_ino
        ):
            raise core.V0P6IncompleteError("factor-bundle path identity changed")
        if metadata.st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise core.V0P6ContractError("factor-bundle file must be read-only")
        if metadata.st_size < _HEADER.size:
            raise core.V0P6IncompleteError("factor-bundle file is truncated")
        file_bytes = _read_exact(descriptor, metadata.st_size, 0)
    finally:
        os.close(descriptor)
    file_digest = _sha256_bytes(file_bytes)
    if file_digest != _frozen_sha256(
        expected_file_sha256, "expected factor-bundle file identity"
    ):
        raise core.V0P6IncompleteError("factor-bundle file identity changed")

    magic, version, manifest_size, encoded_manifest_digest = _HEADER.unpack_from(
        file_bytes
    )
    if magic != _MAGIC or version != _FORMAT_VERSION:
        raise core.V0P6ContractError("factor-bundle header changed")
    if manifest_size < 2 or manifest_size > _MAXIMUM_MANIFEST_BYTES:
        raise core.V0P6CapacityError("factor-bundle manifest size is invalid")
    manifest_start = _HEADER.size
    manifest_stop = manifest_start + manifest_size
    if manifest_stop > len(file_bytes):
        raise core.V0P6IncompleteError("factor-bundle manifest is truncated")
    manifest_bytes = file_bytes[manifest_start:manifest_stop]
    manifest_digest = _sha256_bytes(manifest_bytes)
    if manifest_digest != encoded_manifest_digest.hex():
        raise core.V0P6IncompleteError("factor-bundle header digest changed")
    manifest = _parse_manifest(manifest_bytes, expected_manifest_sha256)
    _validate_manifest_envelope(manifest)
    if manifest["factor_table_sha256"] != _frozen_sha256(
        expected_factor_table_sha256, "expected factor-table identity"
    ):
        raise core.V0P6IncompleteError("factor-bundle factor table changed")

    payload_records = manifest["payloads"]
    if not isinstance(payload_records, list) or len(payload_records) != len(
        _PAYLOAD_ORDER
    ):
        raise core.V0P6ContractError("factor-bundle payload inventory changed")
    arrays: dict[str, np.ndarray] = {}
    expected_offset = 0
    payload_base = manifest_stop
    for expected_name, record in zip(_PAYLOAD_ORDER, payload_records, strict=True):
        if not isinstance(record, dict) or set(record) != {
            "name",
            "dtype",
            "shape",
            "offset",
            "nbytes",
            "sha256",
        }:
            raise core.V0P6ContractError("factor-bundle payload schema changed")
        if record["name"] != expected_name or record["dtype"] != "<f8":
            raise core.V0P6ContractError("factor-bundle payload order changed")
        if isinstance(record["offset"], bool) or not isinstance(record["offset"], int):
            raise core.V0P6ContractError("factor-bundle payload offset is invalid")
        if record["offset"] != expected_offset:
            raise core.V0P6IncompleteError("factor-bundle payloads are not contiguous")
        shape = record["shape"]
        if (
            not isinstance(shape, list)
            or not shape
            or any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in shape)
        ):
            raise core.V0P6ContractError("factor-bundle payload shape is invalid")
        expected_nbytes = int(np.prod(shape, dtype=np.int64)) * 8
        if record["nbytes"] != expected_nbytes:
            raise core.V0P6IncompleteError("factor-bundle payload size changed")
        start = payload_base + expected_offset
        stop = start + expected_nbytes
        if stop > len(file_bytes):
            raise core.V0P6IncompleteError("factor-bundle payload is truncated")
        payload = file_bytes[start:stop]
        if _sha256_bytes(payload) != _frozen_sha256(
            record["sha256"], f"{expected_name} payload identity"
        ):
            raise core.V0P6IncompleteError("factor-bundle payload identity changed")
        array = np.frombuffer(payload, dtype="<f8").reshape(tuple(shape)).copy()
        array.setflags(write=False)
        arrays[expected_name] = array
        expected_offset += expected_nbytes
    if (
        manifest["payload_nbytes"] != expected_offset
        or payload_base + expected_offset != len(file_bytes)
    ):
        raise core.V0P6IncompleteError("factor-bundle trailing-byte accounting changed")

    basis = core.make_factor_basis_from_arrays(
        arrays["times_mjd"],
        manifest["labels"],
        arrays["baseline"],
        arrays["orbital"],
        expected_sha256=core.M37_FACTOR_BASIS_SHA256,
        expected_labels_sha256=core.M37_FACTOR_BASIS_LABELS_SHA256,
    )
    bank = tuple(_detached_json(manifest["template_bank"], "template bank"))
    scans = tuple(_detached_json(manifest["scans"], "scan inventory"))
    table = core.TemplateFactorTable(
        factors=arrays["factors"],
        template_bank_sha256=manifest["template_bank_sha256"],
        factor_basis_sha256=manifest["factor_basis_sha256"],
        factor_basis_labels_sha256=manifest["factor_basis_labels_sha256"],
        factor_table_sha256=manifest["factor_table_sha256"],
    )
    core.validate_m37_factor_basis_scan_inventory(basis, scans)
    core.validate_template_factor_table(
        table,
        basis,
        bank,
        expected_template_bank_sha256=core.M37_BANK_SHA256,
    )
    analysis_contract = core.factorized_analysis_contract_sha256(
        core.M37_EXPERIMENT_CONTRACT_SHA256,
        basis.basis_sha256,
        basis.labels_sha256,
        core.scan_inventory_sha256(scans),
        table.factor_table_sha256,
    )
    if analysis_contract != manifest["analysis_contract_sha256"]:
        raise core.V0P6IncompleteError("factor-bundle analysis contract changed")
    receipt = FactorBundleReceipt(
        manifest_sha256=manifest_digest,
        file_sha256=file_digest,
        factor_basis_sha256=basis.basis_sha256,
        factor_basis_labels_sha256=basis.labels_sha256,
        factor_table_sha256=table.factor_table_sha256,
        analysis_contract_sha256=analysis_contract,
        environment_sha256=manifest["environment_sha256"],
        source_metadata_sha256=manifest["source_metadata_sha256"],
        file_nbytes=len(file_bytes),
    )
    return FactorBundle(
        basis=basis,
        table=table,
        template_bank=bank,
        scans=scans,
        environment=_detached_json(manifest["environment"], "environment"),
        source_hashes=dict(manifest["source_hashes"]),
        receipt=receipt,
    )
