#!/usr/bin/env python3
"""Rehydrate and deeply verify the six M37 1412.5 MHz source products.

The command requires explicit spectral-read authorization.  It downloads only
the HDF5 metadata and allocated chunks needed by the frozen 1412.5 MHz
hyperslab, stores those ranges as immutable blobs, persists independently
rehydratable raw/normalized products, and publishes all 48 native-filter
caches.  Every stage is restartable and refuses a changed existing artifact.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for item in (str(ROOT / "src"), str(SCRIPTS)):
    if item not in sys.path:
        sys.path.insert(0, item)

import numpy as np

import m37_v0p6_hdf5_extract as extractor
from seti_repeater import cache_manifest_v0p6 as cache_manifest
from seti_repeater import factor_bundle_v0p6 as factor_io
from seti_repeater import http_range_v0p6 as transport
from seti_repeater import native_cache_v0p6 as native_cache
from seti_repeater import search_v0p6 as core
from seti_repeater import source_v0p6 as source
from seti_repeater.immutable_range_store_v0p6 import ImmutableRangeStore


WINDOW_ID = "m37_1412p5"
RUN_ID = "m37-v0p6p1-primary-006"
SOURCE_MANIFEST = "m39-source-manifest.json"
CACHE_MANIFEST = "m39-cache-manifest.v0p6"
COMPLETION = "m39-rehydration-completion.json"
WIDTH_WORKERS = 2


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def sha256_json(value: Any) -> str:
    return _sha256_bytes(core.canonical_json_bytes(value))


def _emit(event: str, **values: Any) -> None:
    print(
        core.canonical_json_bytes(
            {"event": event, "monotonic_seconds": time.monotonic(), **values}
        ).decode(),
        flush=True,
    )


def _write_all(descriptor: int, payload: memoryview) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("short write while publishing M39 artifact")
        offset += written


def _publish_bytes(path: Path, payload: bytes) -> str:
    if path.exists():
        if path.read_bytes() != payload:
            raise core.V0P6IncompleteError(
                f"existing immutable M39 artifact differs: {path}"
            )
        return _sha256_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        _write_all(descriptor, memoryview(payload))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return _sha256_bytes(payload)


def _publish_json(path: Path, value: Mapping[str, Any]) -> str:
    return _publish_bytes(path, core.canonical_json_bytes(dict(value)))


def _publish_array(path: Path, values: np.ndarray, dtype: str) -> str:
    array = np.ascontiguousarray(values, dtype=np.dtype(dtype))
    payload = memoryview(array).cast("B")
    if path.exists():
        if path.stat().st_size != len(payload) or sha256_file(path) != hashlib.sha256(
            payload
        ).hexdigest():
            raise core.V0P6IncompleteError(
                f"existing immutable M39 array differs: {path}"
            )
        return sha256_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(payload).hexdigest()


def _read_canonical(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(f"invalid JSON artifact: {path}") from error
    if not isinstance(value, dict) or core.canonical_json_bytes(value) != raw:
        raise core.V0P6ContractError(f"non-canonical JSON artifact: {path}")
    return value


def open_bundle(run_root: Path) -> factor_io.FactorBundle:
    bootstrap = _read_canonical(run_root / "bootstrap.json")
    if (
        bootstrap.get("run_id") != RUN_ID
        or bootstrap.get("spectral_access_authorized") is not False
        or bootstrap.get("spectral_dataset_values_read") is not False
    ):
        raise core.V0P6ContractError("M39 bootstrap run identity changed")
    bundle = factor_io.open_m37_factor_bundle(
        run_root / "factor_bundle.v0p6",
        expected_manifest_sha256=bootstrap["factor_bundle_manifest_sha256"],
        expected_file_sha256=bootstrap["factor_bundle_file_sha256"],
        expected_factor_table_sha256=bootstrap["factor_table_sha256"],
    )
    if (
        bundle.receipt.factor_basis_sha256 != core.M37_FACTOR_BASIS_SHA256
        or bundle.receipt.factor_basis_labels_sha256
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or bundle.receipt.analysis_contract_sha256
        != "726571e7b56b684f06ff69bbd6ae70b4c191268d25db8eadfcb8b6e841dc9f2e"
    ):
        raise core.V0P6IncompleteError("M39 factor ancestry changed")
    return bundle


def _source_paths(run_root: Path, scan_label: str) -> tuple[Path, Path, Path]:
    directory = run_root / "sources" / WINDOW_ID
    return (
        directory / f"{scan_label}.raw-native.f4",
        directory / f"{scan_label}.normalized.f4",
        directory / f"{scan_label}.product.json",
    )


def persist_product(
    run_root: Path,
    product: source.M37NormalizedScanProduct,
) -> dict[str, Any]:
    raw_path, normalized_path, receipt_path = _source_paths(
        run_root, product.scan_label
    )
    raw_native = np.ascontiguousarray(product.raw_values[:, ::-1], dtype="<f4")
    raw_digest = _publish_array(raw_path, raw_native, "<f4")
    normalized_digest = _publish_array(
        normalized_path, product.normalized_values, "<f4"
    )
    extraction_record = json.loads(product.extraction_receipt_record_json)
    product_record = source.normalized_scan_product_record(
        product,
        expected_product_sha256=product.product_sha256,
        expected_extraction_receipt_sha256=product.extraction_receipt_sha256,
    )
    receipt = {
        "artifact_type": "m39-m37-normalized-source-product-v1",
        "run_id": RUN_ID,
        "window_id": WINDOW_ID,
        "scan_label": product.scan_label,
        "raw_native": {
            "relative_path": raw_path.relative_to(run_root).as_posix(),
            "dtype": "<f4",
            "shape": list(raw_native.shape),
            "nbytes": raw_native.nbytes,
            "sha256": raw_digest,
        },
        "normalized": {
            "relative_path": normalized_path.relative_to(run_root).as_posix(),
            "dtype": "<f4",
            "shape": list(product.normalized_values.shape),
            "nbytes": product.normalized_values.nbytes,
            "sha256": normalized_digest,
        },
        "extraction_receipt": extraction_record,
        "normalized_product": product_record,
        "extraction_receipt_sha256": product.extraction_receipt_sha256,
        "product_sha256": product.product_sha256,
    }
    _publish_json(receipt_path, receipt)
    return receipt


def load_product(
    run_root: Path,
    scans: tuple[dict[str, Any], ...],
    scan_label: str,
) -> source.M37NormalizedScanProduct:
    _, _, receipt_path = _source_paths(run_root, scan_label)
    receipt = _read_canonical(receipt_path)
    if (
        receipt.get("artifact_type")
        != "m39-m37-normalized-source-product-v1"
        or receipt.get("run_id") != RUN_ID
        or receipt.get("window_id") != WINDOW_ID
        or receipt.get("scan_label") != scan_label
    ):
        raise core.V0P6IncompleteError("M39 source receipt identity changed")
    arrays: list[np.ndarray] = []
    for key in ("raw_native", "normalized"):
        record = receipt[key]
        path = run_root / record["relative_path"]
        if (
            not path.is_file()
            or path.stat().st_size != record["nbytes"]
            or sha256_file(path) != record["sha256"]
        ):
            raise core.V0P6IncompleteError("M39 source payload changed")
        values = np.fromfile(path, dtype=np.dtype(record["dtype"]))
        values = np.ascontiguousarray(values.reshape(record["shape"]))
        values.setflags(write=False)
        arrays.append(values)
    return source.rehydrate_m37_normalized_scan_product(
        arrays[0],
        None,
        arrays[1],
        scans,
        receipt["extraction_receipt"],
        receipt["normalized_product"],
        expected_extraction_receipt_sha256=receipt[
            "extraction_receipt_sha256"
        ],
        expected_product_sha256=receipt["product_sha256"],
    )


def extract_product(
    run_root: Path,
    bundle: factor_io.FactorBundle,
    scan_label: str,
) -> source.M37NormalizedScanProduct:
    extractor._require_frozen_implementation()
    definitions = [item for item in bundle.scans if item["label"] == scan_label]
    if len(definitions) != 1:
        raise core.V0P6IncompleteError("M39 scan inventory changed")
    definition = definitions[0]
    identity = transport.remote_identity(str(definition["url"]))
    if (
        identity.size != definition["expected_remote_size_bytes"]
        or identity.etag != definition["expected_etag"]
    ):
        raise core.V0P6IncompleteError("M39 remote source identity changed")
    import h5py
    import hdf5plugin  # noqa: F401

    store_root = run_root / "ranges" / f"{scan_label}.store"
    store_root.parent.mkdir(parents=True, exist_ok=True)
    interval = source.m37_extraction_interval(WINDOW_ID)
    with ImmutableRangeStore(
        store_root,
        identity,
        workers=transport.DEFAULT_WORKERS,
    ) as store:
        store.prefetch(
            (
                transport.ByteRange(
                    0,
                    min(identity.size, transport.HDF5_METADATA_PREFIX_BYTES),
                ),
            )
        )
        store.seek(0)
        with h5py.File(store, "r") as handle:
            dataset, _ = extractor._validated_dataset(handle, definition)
            ranges = transport.discover_hdf5_chunk_ranges(dataset, (interval,))
            plan = transport.range_plan_record(
                identity,
                dataset_shape=dataset.shape,
                dataset_chunks=dataset.chunks,
                channel_intervals=(interval,),
                ranges=ranges,
            )
        transport.publish_range_plan(
            run_root / "ranges" / f"{scan_label}.range-plan.json", plan
        )
        store.prefetch(ranges)
        store.seek(0)
        with h5py.File(store, "r") as handle:
            products = extractor._iter_handle_products(
                handle,
                definition=definition,
                scan_definitions=bundle.scans,
                scan_label=scan_label,
                requested_windows=(WINDOW_ID,),
                remote_size=identity.size,
                etag=identity.etag,
            )
            product = next(products)
            try:
                next(products)
            except StopIteration:
                pass
            else:
                raise core.V0P6IncompleteError("M39 extractor yielded extra product")
    return product


def _cache_paths(
    run_root: Path, scan_label: str, width: int
) -> tuple[Path, Path]:
    directory = run_root / "caches" / WINDOW_ID / scan_label
    return directory / f"width-{width}.nfc", directory / f"width-{width}.json"


def _load_cache_sidecar(
    run_root: Path, path: Path
) -> cache_manifest.CacheManifestEntry:
    record = _read_canonical(path)
    if (
        set(record) != {"artifact_type", "entry", "source_product"}
        or record["artifact_type"] != "m39-m37-cache-sidecar-v1"
    ):
        raise core.V0P6IncompleteError("M39 cache sidecar schema changed")
    entry = cache_manifest._validate_entry(record["entry"])
    candidate = (run_root / entry.relative_path).resolve()
    if run_root.resolve() not in candidate.parents or not candidate.is_file():
        raise core.V0P6IncompleteError("M39 cache sidecar path changed")
    return entry


def publish_cache(
    run_root: Path,
    product: source.M37NormalizedScanProduct,
    width: int,
    bundle: factor_io.FactorBundle,
) -> cache_manifest.CacheManifestEntry:
    cache_path, sidecar_path = _cache_paths(run_root, product.scan_label, width)
    if sidecar_path.exists():
        return _load_cache_sidecar(run_root, sidecar_path)
    if cache_path.exists():
        raise core.V0P6IncompleteError("M39 cache exists without sidecar")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    grid = core.make_m37_proxy_carrier_grid(WINDOW_ID)
    plan = source.plan_m37_production_native_filter_cache(
        product,
        bundle.basis,
        bundle.table,
        bundle.scans,
        grid,
        width,
        expected_product_sha256=product.product_sha256,
        expected_extraction_receipt_sha256=product.extraction_receipt_sha256,
    )
    cache = source.build_m37_production_native_filter_cache(
        product,
        plan,
        bundle.basis,
        bundle.table,
        bundle.scans,
        grid,
        expected_product_sha256=product.product_sha256,
        expected_extraction_receipt_sha256=product.extraction_receipt_sha256,
    )
    receipt = native_cache.publish_native_filter_cache(cache_path, cache)
    entry = cache_manifest.make_cache_manifest_entry(
        cache_path.relative_to(run_root).as_posix(), plan, receipt
    )
    _publish_json(
        sidecar_path,
        {
            "artifact_type": "m39-m37-cache-sidecar-v1",
            "entry": entry.as_record(),
            "source_product": {
                "product_sha256": product.product_sha256,
                "extraction_receipt_sha256": product.extraction_receipt_sha256,
                "normalized_values_sha256": product.normalized_values_sha256,
            },
        },
    )
    return entry


def _cache_keys() -> tuple[tuple[str, str, int], ...]:
    return tuple(
        (WINDOW_ID, label, width)
        for _, _, label in core.M37_SCAN_ROLE_ORDER
        for width in core.M37_SPECTRAL_WIDTHS
    )


def execute_one_scan(
    run_root: Path,
    scan_label: str,
    *,
    authorized: bool,
) -> dict[str, Any]:
    if authorized is not True:
        raise RuntimeError(
            "M39 spectral read is not authorized; no remote request made"
        )
    run_root.mkdir(parents=True, exist_ok=True)
    bundle = open_bundle(run_root)
    labels = tuple(str(scan["label"]) for scan in bundle.scans)
    if scan_label not in labels:
        raise core.V0P6ContractError("requested M39 scan label is unknown")
    _, _, receipt_path = _source_paths(run_root, scan_label)
    if receipt_path.exists():
        product = load_product(run_root, bundle.scans, scan_label)
        restart_hit = True
    else:
        product = extract_product(run_root, bundle, scan_label)
        persist_product(run_root, product)
        restart_hit = False
    with ThreadPoolExecutor(max_workers=WIDTH_WORKERS) as pool:
        entries = tuple(
            pool.map(
                lambda width: publish_cache(
                    run_root, product, width, bundle
                ),
                core.M37_SPECTRAL_WIDTHS,
            )
        )
    result = {
        "status": "scan-complete",
        "scan_label": scan_label,
        "restart_hit": restart_hit,
        "cache_count": len(entries),
        "product_sha256": product.product_sha256,
    }
    _emit("independent_scan_complete", **result)
    return result


def execute(run_root: Path, *, authorized: bool) -> dict[str, Any]:
    if authorized is not True:
        raise RuntimeError(
            "M39 spectral read is not authorized; no remote request made"
        )
    run_root.mkdir(parents=True, exist_ok=True)
    bundle = open_bundle(run_root)
    source_records: list[dict[str, Any]] = []
    entries: list[cache_manifest.CacheManifestEntry] = []
    for scan in bundle.scans:
        label = str(scan["label"])
        _, _, receipt_path = _source_paths(run_root, label)
        if receipt_path.exists():
            product = load_product(run_root, bundle.scans, label)
            _emit("source_restart_hit", scan_label=label)
        else:
            product = extract_product(run_root, bundle, label)
            persist_product(run_root, product)
            _emit("source_product_complete", scan_label=label)
        with ThreadPoolExecutor(max_workers=WIDTH_WORKERS) as pool:
            built = tuple(
                pool.map(
                    lambda width: publish_cache(
                        run_root, product, width, bundle
                    ),
                    core.M37_SPECTRAL_WIDTHS,
                )
            )
        entries.extend(built)
        receipt = _read_canonical(receipt_path)
        source_records.append(
            {
                "scan_label": label,
                "receipt_path": receipt_path.relative_to(run_root).as_posix(),
                "receipt_sha256": sha256_file(receipt_path),
                "product_sha256": receipt["product_sha256"],
                "extraction_receipt_sha256": receipt[
                    "extraction_receipt_sha256"
                ],
            }
        )
        _emit("scan_caches_complete", scan_label=label, cache_count=len(built))
        del product
        gc.collect()

    source_manifest_record = {
        "artifact_type": "m39-m37-source-manifest-v1",
        "run_id": RUN_ID,
        "window_id": WINDOW_ID,
        "spectral_dataset_values_read": True,
        "product_count": len(source_records),
        "products": source_records,
        "product_inventory_sha256": sha256_json(source_records),
    }
    source_manifest_sha256 = _publish_json(
        run_root / SOURCE_MANIFEST, source_manifest_record
    )
    manifest_path = run_root / CACHE_MANIFEST
    expected_keys = _cache_keys()
    if manifest_path.exists():
        cache_manifest_file_sha256 = sha256_file(manifest_path)
        manifest = cache_manifest.open_cache_run_manifest(
            manifest_path,
            expected_file_sha256=cache_manifest_file_sha256,
            expected_factor_bundle_manifest_sha256=(
                bundle.receipt.manifest_sha256
            ),
            expected_keys=expected_keys,
        )
    else:
        receipt = cache_manifest.publish_cache_run_manifest(
            manifest_path,
            entries,
            run_id=RUN_ID,
            factor_bundle_manifest_sha256=bundle.receipt.manifest_sha256,
            expected_keys=expected_keys,
        )
        manifest = cache_manifest.open_cache_run_manifest(
            manifest_path,
            expected_file_sha256=receipt.file_sha256,
            expected_factor_bundle_manifest_sha256=(
                bundle.receipt.manifest_sha256
            ),
            expected_keys=expected_keys,
        )
    verified_cache_inventory_sha256 = cache_manifest.verify_cache_run_files(
        run_root, manifest
    )
    verified_source_records = []
    for scan in bundle.scans:
        product = load_product(run_root, bundle.scans, str(scan["label"]))
        verified_source_records.append(
            {
                "scan_label": product.scan_label,
                "product_sha256": product.product_sha256,
                "normalized_values_sha256": product.normalized_values_sha256,
            }
        )
        del product
        gc.collect()
    completion = {
        "artifact_type": "m39-m37-rehydration-completion-v1",
        "status": "complete",
        "run_id": RUN_ID,
        "window_id": WINDOW_ID,
        "source_product_count": len(source_records),
        "cache_entry_count": manifest.receipt.entry_count,
        "cache_payload_nbytes": manifest.receipt.payload_nbytes,
        "source_manifest_sha256": source_manifest_sha256,
        "cache_manifest_file_sha256": manifest.receipt.file_sha256,
        "source_deep_verification_sha256": sha256_json(
            verified_source_records
        ),
        "cache_deep_verification_sha256": verified_cache_inventory_sha256,
        "factor_bundle_file_sha256": bundle.receipt.file_sha256,
        "factor_bundle_manifest_sha256": bundle.receipt.manifest_sha256,
        "factor_table_sha256": bundle.receipt.factor_table_sha256,
        "analysis_contract_sha256": bundle.receipt.analysis_contract_sha256,
        "source_metadata_sha256": bundle.receipt.source_metadata_sha256,
        "all_six_sources_verified": len(source_records) == 6,
        "all_48_caches_verified": manifest.receipt.entry_count == 48,
    }
    completion["completion_sha256"] = sha256_json(completion)
    _publish_json(run_root / COMPLETION, completion)
    return completion


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--authorize-spectral-read", action="store_true")
    parser.add_argument(
        "--scan-label",
        choices=tuple(label for _, _, label in core.M37_SCAN_ROLE_ORDER),
    )
    arguments = parser.parse_args()
    if arguments.scan_label is None:
        result = execute(
            arguments.run_root.resolve(),
            authorized=arguments.authorize_spectral_read,
        )
    else:
        result = execute_one_scan(
            arguments.run_root.resolve(),
            arguments.scan_label,
            authorized=arguments.authorize_spectral_read,
        )
    print(core.canonical_json_bytes(result).decode(), flush=True)


if __name__ == "__main__":
    main()
