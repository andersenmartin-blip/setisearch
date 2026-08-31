#!/usr/bin/env python3
"""Restartable production controller for the preregistered M37 v0.6 search.

The controller keeps transport mirrors, native-filter caches and immutable
science handoffs in one run directory.  It never crosses the spectral boundary
before an explicit authorization artifact has been appended to the run journal.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import gc
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for item in (str(ROOT / "src"), str(SCRIPTS)):
    if item not in sys.path:
        sys.path.insert(0, item)

import numpy as np

import m37_v0p6_bootstrap as bootstrap_cli
import m37_v0p6_hdf5_extract as extractor
from seti_repeater import cache_manifest_v0p6 as cache_manifest
from seti_repeater import capacity_v0p6p1 as capacity_v0p6p1
from seti_repeater import factor_bundle_v0p6 as factor_io
from seti_repeater import native_cache_v0p6 as native_cache
from seti_repeater import null_artifact_v0p6 as null_artifact
from seti_repeater import run_state_v0p6 as state
from seti_repeater import runner_v0p6 as bootstrap_runner
from seti_repeater import search_v0p6 as core
from seti_repeater import source_v0p6 as source


DEFAULT_RUN_ROOT = ROOT / "results_m37_v0p6_primary_003"
DEFAULT_RUN_ID = "m37-v0p6-primary-003"
CONTROLLER_PATH = "run-controller.json"
AUTHORIZATION_PATH = "spectral-authorization.json"
CACHE_MANIFEST_PATH = "cache-run-manifest.json"
EXTRACTION_INVENTORY_PATH = "extraction-inventory.json"
CALIBRATION_INVENTORY_PATH = "calibration-inventory.json"
GLOBAL_NULL_PATH = "global-null.json"
CALIBRATION_ADOPTION_PATH = "calibration-adoption.json"
SOURCE_CALIBRATION_INVENTORY_PATH = "source-calibration-inventory.json"
M37_PRODUCT_WIDTH_WORKERS = 2
CAPACITY_AMENDMENT_PATH = (
    ROOT / "config/hd156668b_m37_v0p6p1_capacity_amendment.json"
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def _emit_progress(event: str, **values: Any) -> None:
    print(
        core.canonical_json_bytes(
            {"event": event, "monotonic_seconds": time.monotonic(), **values}
        ).decode(),
        flush=True,
    )


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("short artifact write")
        offset += written


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_or_verify(path: Path, value: Mapping[str, Any]) -> str:
    payload = core.canonical_json_bytes(dict(value))
    if path.exists():
        if path.read_bytes() != payload:
            raise core.V0P6IncompleteError(
                f"existing immutable artifact differs: {path.name}"
            )
        return _sha256_bytes(payload)
    temporary = path.parent / f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
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
    _fsync_directory(path.parent)
    return _sha256_bytes(payload)


def _write_controller(root: Path, record: Mapping[str, Any]) -> None:
    payload = core.canonical_json_bytes(dict(record))
    destination = root / CONTROLLER_PATH
    temporary = root / f".{CONTROLLER_PATH}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, destination)
    _fsync_directory(root)


def _read_canonical(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(f"invalid JSON artifact: {path.name}") from error
    if not isinstance(value, dict) or core.canonical_json_bytes(value) != raw:
        raise core.V0P6ContractError(f"noncanonical JSON artifact: {path.name}")
    return value


def _status(root: Path) -> dict[str, Any]:
    record = _read_canonical(root / CONTROLLER_PATH)
    if (
        record.get("schema_version") != 1
        or record.get("artifact_type") != "m37-detector-v0p6-primary-controller-v1"
        or not isinstance(record.get("run_id"), str)
        or record.get("stage") not in state.M37_RUN_STAGES
    ):
        raise core.V0P6ContractError("primary controller schema changed")
    journal = state.read_m37_run_journal(
        root / "run.journal.jsonl",
        expected_head_sha256=str(record["journal_head_sha256"]),
    )
    if journal.run_id != record["run_id"] or journal.stage != record["stage"]:
        raise core.V0P6IncompleteError("controller and journal differ")
    amendment = record.get("capacity_amendment")
    if amendment is not None:
        capacity_v0p6p1.validate_m37_v0p6p1_capacity_profile_record(amendment)
    return record


def _stage_index(stage: str) -> int:
    return state.M37_RUN_STAGES.index(stage)


def _stage_at_least(record: Mapping[str, Any], stage: str) -> bool:
    return _stage_index(str(record["stage"])) >= _stage_index(stage)


def _source_hashes() -> dict[str, str]:
    paths = {
        **bootstrap_cli.SOURCE_PATHS,
        "hdf5_extractor": ROOT / "scripts/m37_v0p6_hdf5_extract.py",
        "http_range_transport": ROOT / "src/seti_repeater/http_range_v0p6.py",
        "native_cache": ROOT / "src/seti_repeater/native_cache_v0p6.py",
        "capacity_amendment_v0p6p1": (
            ROOT / "src/seti_repeater/capacity_v0p6p1.py"
        ),
        "capacity_amendment_config_v0p6p1": CAPACITY_AMENDMENT_PATH,
        "primary_controller": ROOT / "scripts/m37_v0p6_primary.py",
        "source_boundary": ROOT / "src/seti_repeater/source_v0p6.py",
    }
    return {name: _sha256_file(path) for name, path in sorted(paths.items())}


def _environment(*, capacity_amendment: bool = False) -> dict[str, Any]:
    return {
        **bootstrap_cli.environment_record(),
        "purpose": (
            "m37-detector-v0p6p1-authorized-primary-analysis"
            if capacity_amendment
            else "m37-detector-v0p6-authorized-primary-analysis"
        ),
        "post_contact_capacity_amendment": capacity_amendment,
        "spectral_access_authorized": False,
        "spectral_dataset_values_read": False,
        "range_workers": extractor.transport.DEFAULT_WORKERS,
        "product_width_workers": M37_PRODUCT_WIDTH_WORKERS,
    }


def prepare(
    root: Path, run_id: str, *, capacity_amendment: bool = False
) -> dict[str, Any]:
    if root.exists():
        record = _status(root)
        if record["run_id"] != run_id:
            raise core.V0P6ContractError("existing run ID differs")
        if (record.get("capacity_amendment") is not None) != capacity_amendment:
            raise core.V0P6ContractError(
                "existing run capacity protocol differs"
            )
        return record
    profile = (
        capacity_v0p6p1.open_m37_v0p6p1_capacity_amendment(
            CAPACITY_AMENDMENT_PATH
        )
        if capacity_amendment
        else None
    )
    upstream = json.loads(bootstrap_cli.UPSTREAM.read_text())
    bank_result = json.loads(bootstrap_cli.BANK_RESULT.read_text())
    receipt = bootstrap_runner.bootstrap_m37_run(
        root,
        run_id=run_id,
        upstream_metadata=upstream,
        bank_preflight_result=bank_result,
        environment=_environment(capacity_amendment=capacity_amendment),
        source_hashes=_source_hashes(),
    )
    record = {
        "schema_version": 1,
        "artifact_type": "m37-detector-v0p6-primary-controller-v1",
        "run_id": run_id,
        "stage": "factor_bundle_ready",
        "journal_head_sha256": receipt.journal_head_sha256,
        "bootstrap": receipt.__dict__,
        "artifacts": {},
    }
    if profile is not None:
        record["capacity_amendment"] = profile.as_record()
    _write_controller(root, record)
    _emit_progress("primary_prepared", run_id=run_id, root=str(root))
    return record


def _bundle(root: Path, record: Mapping[str, Any]) -> factor_io.FactorBundle:
    bootstrap = record["bootstrap"]
    return factor_io.open_m37_factor_bundle(
        root / "factor_bundle.v0p6",
        expected_manifest_sha256=bootstrap["factor_bundle_manifest_sha256"],
        expected_file_sha256=bootstrap["factor_bundle_file_sha256"],
        expected_factor_table_sha256=bootstrap["factor_table_sha256"],
    )


def _advance(
    root: Path,
    record: dict[str, Any],
    *,
    stage: str,
    artifact_sha256: str,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    journal = state.advance_m37_run_journal(
        root / "run.journal.jsonl",
        expected_head_sha256=record["journal_head_sha256"],
        stage=stage,
        artifact_sha256=artifact_sha256,
        metadata={
            "spectral_access_authorized": True,
            "spectral_dataset_values_read": stage != "spectral_access_authorized",
            **dict(metadata),
        },
    )
    updated = dict(record)
    updated["stage"] = journal.stage
    updated["journal_head_sha256"] = journal.head_sha256
    _write_controller(root, updated)
    return updated


def authorize(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    if _stage_at_least(record, "spectral_access_authorized"):
        return record
    if record["stage"] != "factor_bundle_ready":
        raise core.V0P6IncompleteError("authorization stage is not reachable")
    bundle = _bundle(root, record)
    basis = {
        "schema_version": 1,
        "artifact_type": "m37-detector-v0p6-spectral-authorization-v1",
        "run_id": record["run_id"],
        "authorization_scope": state.M37_SPECTRAL_AUTHORIZATION_SCOPE,
        "spectral_access_authorized": True,
        "spectral_dataset_values_read": False,
        "source_scan_definitions_sha256": source.M37_SOURCE_SCAN_DEFINITIONS_SHA256,
        "scan_inventory_sha256": core.M37_SCAN_INVENTORY_SHA256,
        "factor_bundle_manifest_sha256": bundle.receipt.manifest_sha256,
        "remote_identities": [
            {
                "label": scan["label"],
                "url": scan["url"],
                "expected_remote_size_bytes": scan["expected_remote_size_bytes"],
                "expected_etag": scan["expected_etag"],
            }
            for scan in bundle.scans
        ],
        "transport": {
            "workers": extractor.transport.DEFAULT_WORKERS,
            "maximum_workers": extractor.transport.MAXIMUM_WORKERS,
            "metadata_prefix_bytes": extractor.transport.HDF5_METADATA_PREFIX_BYTES,
            "on_demand_read_ahead_bytes": extractor.transport.ON_DEMAND_READ_AHEAD_BYTES,
        },
    }
    if record.get("capacity_amendment") is not None:
        basis["capacity_amendment"] = record["capacity_amendment"]
    authorization_sha256 = _publish_or_verify(root / AUTHORIZATION_PATH, basis)
    updated = _advance(
        root,
        record,
        stage="spectral_access_authorized",
        artifact_sha256=authorization_sha256,
        metadata={
            "authorization_scope": state.M37_SPECTRAL_AUTHORIZATION_SCOPE,
            "authorization_receipt_sha256": authorization_sha256,
        },
    )
    artifacts = dict(updated["artifacts"])
    artifacts["authorization"] = {"file_sha256": authorization_sha256}
    updated["artifacts"] = artifacts
    _write_controller(root, updated)
    _emit_progress("spectral_access_authorized", artifact_sha256=authorization_sha256)
    return updated


def _cache_paths(root: Path, window_id: str, scan_label: str, width: int) -> tuple[Path, Path]:
    directory = root / "caches" / window_id / scan_label
    return directory / f"width-{width}.nfc", directory / f"width-{width}.json"


def _load_sidecar(root: Path, path: Path) -> cache_manifest.CacheManifestEntry:
    record = _read_canonical(path)
    if set(record) != {"artifact_type", "entry", "source_product"} or record[
        "artifact_type"
    ] != "m37-detector-v0p6-cache-sidecar-v1":
        raise core.V0P6ContractError("cache sidecar schema changed")
    entry = cache_manifest._validate_entry(record["entry"])
    candidate = (root / entry.relative_path).resolve()
    if root.resolve() not in candidate.parents or not candidate.is_file():
        raise core.V0P6IncompleteError("cache sidecar points outside the run")
    return entry


def _publish_product_width(
    root: Path,
    product: source.M37NormalizedScanProduct,
    width: int,
    bundle: factor_io.FactorBundle,
) -> cache_manifest.CacheManifestEntry:
    cache_path, sidecar_path = _cache_paths(root, product.window_id, product.scan_label, width)
    if sidecar_path.exists():
        return _load_sidecar(root, sidecar_path)
    if cache_path.exists():
        raise core.V0P6IncompleteError("cache exists without its immutable sidecar")
    grid = core.make_m37_proxy_carrier_grid(product.window_id)
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
    relative_path = cache_path.relative_to(root).as_posix()
    entry = cache_manifest.make_cache_manifest_entry(relative_path, plan, receipt)
    _publish_or_verify(
        sidecar_path,
        {
            "artifact_type": "m37-detector-v0p6-cache-sidecar-v1",
            "entry": entry.as_record(),
            "source_product": {
                "product_sha256": product.product_sha256,
                "extraction_receipt_sha256": product.extraction_receipt_sha256,
                "normalized_values_sha256": product.normalized_values_sha256,
            },
        },
    )
    return entry


def _all_sidecars(root: Path) -> tuple[cache_manifest.CacheManifestEntry, ...]:
    entries: list[cache_manifest.CacheManifestEntry] = []
    for window_id, scan_label, width in cache_manifest.m37_cache_keys():
        _, sidecar = _cache_paths(root, window_id, scan_label, width)
        if not sidecar.exists():
            raise core.V0P6IncompleteError("M37 cache-sidecar inventory is incomplete")
        entries.append(_load_sidecar(root, sidecar))
    return tuple(entries)


def build_caches(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    if _stage_at_least(record, "cache_manifest_complete"):
        return record
    if record["stage"] != "spectral_access_authorized":
        raise core.V0P6IncompleteError("cache build requires spectral authorization")
    bundle = _bundle(root, record)
    (root / "ranges").mkdir(exist_ok=True)
    (root / "caches").mkdir(exist_ok=True)
    for scan in bundle.scans:
        scan_label = str(scan["label"])
        missing_windows = []
        for window_id in core.M37_WINDOW_IDS:
            if not all(
                _cache_paths(root, window_id, scan_label, width)[1].exists()
                for width in core.M37_SPECTRAL_WIDTHS
            ):
                missing_windows.append(window_id)
        if not missing_windows:
            _emit_progress("scan_cache_restart_hit", scan_label=scan_label)
            continue
        products = extractor.iter_m37_normalized_scan_products(
            bundle.scans,
            scan_label=scan_label,
            window_ids=missing_windows,
            spectral_access_authorized=True,
            range_mirror_root=root / "ranges",
            range_workers=extractor.transport.DEFAULT_WORKERS,
        )
        for product in products:
            cache_directory = root / "caches" / product.window_id / scan_label
            cache_directory.mkdir(parents=True, exist_ok=True)
            missing_widths = tuple(
                width
                for width in core.M37_SPECTRAL_WIDTHS
                if not _cache_paths(root, product.window_id, scan_label, width)[1].exists()
            )
            with ThreadPoolExecutor(max_workers=M37_PRODUCT_WIDTH_WORKERS) as pool:
                entries = tuple(
                    pool.map(
                        lambda width: _publish_product_width(
                            root, product, width, bundle
                        ),
                        missing_widths,
                    )
                )
            _emit_progress(
                "window_caches_complete",
                scan_label=scan_label,
                window_id=product.window_id,
                cache_count=len(entries),
            )
            del product
            gc.collect()

    entries = _all_sidecars(root)
    extraction_sources = [
        {
            "window_id": entry.window_id,
            "scan_label": entry.scan_label,
            "source_sha256": entry.source_sha256,
        }
        for entry in entries
        if entry.width_channels == core.M37_SPECTRAL_WIDTHS[0]
    ]
    extraction_record = {
        "artifact_type": "m37-detector-v0p6-extraction-inventory-v1",
        "run_id": record["run_id"],
        "spectral_dataset_values_read": True,
        "product_count": len(extraction_sources),
        "products": extraction_sources,
    }
    extraction_sha256 = _publish_or_verify(
        root / EXTRACTION_INVENTORY_PATH, extraction_record
    )
    updated = _advance(
        root,
        record,
        stage="extraction_complete",
        artifact_sha256=extraction_sha256,
        metadata={"product_count": len(extraction_sources)},
    )
    manifest_path = root / CACHE_MANIFEST_PATH
    if manifest_path.exists():
        manifest_file_sha256 = _sha256_file(manifest_path)
        opened = cache_manifest.open_cache_run_manifest(
            manifest_path,
            expected_file_sha256=manifest_file_sha256,
            expected_factor_bundle_manifest_sha256=bundle.receipt.manifest_sha256,
            expected_keys=cache_manifest.m37_cache_keys(),
        )
        manifest_receipt = opened.receipt
    else:
        manifest_receipt = cache_manifest.publish_m37_cache_run_manifest(
            manifest_path,
            entries,
            run_id=record["run_id"],
            factor_bundle_manifest_sha256=bundle.receipt.manifest_sha256,
        )
    verified_inventory = cache_manifest.verify_cache_run_files(
        root,
        cache_manifest.open_cache_run_manifest(
            manifest_path,
            expected_file_sha256=manifest_receipt.file_sha256,
            expected_factor_bundle_manifest_sha256=bundle.receipt.manifest_sha256,
            expected_keys=cache_manifest.m37_cache_keys(),
        ),
    )
    updated = _advance(
        root,
        updated,
        stage="cache_manifest_complete",
        artifact_sha256=manifest_receipt.file_sha256,
        metadata={
            "cache_entry_count": manifest_receipt.entry_count,
            "cache_payload_nbytes": manifest_receipt.payload_nbytes,
            "cache_inventory_sha256": manifest_receipt.inventory_sha256,
            "verified_cache_inventory_sha256": verified_inventory,
        },
    )
    artifacts = dict(updated["artifacts"])
    artifacts["extraction_inventory"] = {"file_sha256": extraction_sha256}
    artifacts["cache_manifest"] = {
        **manifest_receipt.__dict__,
        "verified_inventory_sha256": verified_inventory,
    }
    updated["artifacts"] = artifacts
    _write_controller(root, updated)
    _emit_progress(
        "cache_manifest_complete",
        cache_count=manifest_receipt.entry_count,
        payload_nbytes=manifest_receipt.payload_nbytes,
    )
    return updated


def _open_manifest(
    root: Path, record: Mapping[str, Any], bundle: factor_io.FactorBundle
) -> cache_manifest.CacheRunManifest:
    receipt = record["artifacts"]["cache_manifest"]
    return cache_manifest.open_cache_run_manifest(
        root / CACHE_MANIFEST_PATH,
        expected_file_sha256=receipt["file_sha256"],
        expected_factor_bundle_manifest_sha256=bundle.receipt.manifest_sha256,
        expected_keys=cache_manifest.m37_cache_keys(),
    )


def _template_products(
    root: Path,
    manifest: cache_manifest.CacheRunManifest,
    bundle: factor_io.FactorBundle,
    validation_cache: native_cache.NativeFilterCacheValidationCache,
    *,
    window_id: str,
    kind: str,
    template_index: int,
) -> tuple[dict[int, core.EpochVectorProduct], core.MaskProduct]:
    entries = {
        (entry.window_id, entry.scan_label, entry.width_channels): entry
        for entry in manifest.entries
    }
    labels = tuple(scan["label"] for scan in bundle.scans if scan["kind"] == kind)
    arena = native_cache.NativeFilterCacheArena(core.M37_LIVE_NDARRAY_CAP_BYTES)

    def build(width: int) -> tuple[int, core.EpochVectorProduct]:
        with ExitStack() as stack:
            caches = {}
            for label in labels:
                entry = entries[(window_id, label, width)]
                plan = core.native_filter_cache_plan_from_record(
                    entry.plan_record,
                    expected_plan_sha256=entry.plan_sha256,
                )
                handle = stack.enter_context(
                    native_cache.open_native_filter_cache(
                        root / entry.relative_path,
                        expected_plan=plan,
                        expected_plan_sha256=entry.plan_sha256,
                        expected_manifest_sha256=entry.cache_manifest_sha256,
                        arena=arena,
                        validation_cache=validation_cache,
                    )
                )
                caches[label] = handle
            product = core.build_m37_epoch_vector_product(
                caches,
                bundle.scans,
                bundle.basis,
                bundle.table,
                template_index,
                core.make_m37_proxy_carrier_grid(window_id),
                width,
                window_id=window_id,
                kind=kind,
            )
        return width, product

    try:
        with ThreadPoolExecutor(max_workers=M37_PRODUCT_WIDTH_WORKERS) as pool:
            unordered = dict(pool.map(build, core.M37_SPECTRAL_WIDTHS))
        products = {width: unordered[width] for width in core.M37_SPECTRAL_WIDTHS}
        mask = core.build_m37_mask_product(products)
        return products, mask
    finally:
        if arena.handle_count or arena.mapped_bytes:
            arena.close()
        if arena.handle_count or arena.mapped_bytes:
            raise core.V0P6IncompleteError("cache arena did not release all mappings")


def calibrate(
    root: Path,
    record: dict[str, Any],
    validation_cache: native_cache.NativeFilterCacheValidationCache | None = None,
) -> tuple[dict[str, Any], null_artifact.GlobalNullArtifact]:
    if _stage_at_least(record, "threshold_complete"):
        receipt = record["artifacts"]["global_null"]
        opened = null_artifact.open_global_null_artifact(
            root / GLOBAL_NULL_PATH,
            expected_file_sha256=receipt["file_sha256"],
            expected_threshold_certificate_sha256=receipt[
                "threshold_certificate_sha256"
            ],
            require_spectral_dataset_values_read=True,
        )
        return record, opened
    if record["stage"] != "cache_manifest_complete":
        raise core.V0P6IncompleteError("calibration requires the complete cache manifest")
    bundle = _bundle(root, record)
    manifest = _open_manifest(root, record, bundle)
    validator = validation_cache or native_cache.NativeFilterCacheValidationCache()
    scrambles = core.load_m37_scramble_tables()
    calibrations: list[core.CalibrationAccumulator] = []
    summaries: list[dict[str, Any]] = []
    for window_index, window_id in enumerate(core.M37_WINDOW_IDS):
        accumulator = core.make_m37_calibration(
            window_id,
            scrambles[window_index],
            factor_table_sha256_value=bundle.table.factor_table_sha256,
        )
        for template_index in range(core.M37_TEMPLATE_COUNT):
            products, mask = _template_products(
                root,
                manifest,
                bundle,
                validator,
                window_id=window_id,
                kind="on",
                template_index=template_index,
            )
            for width_index, width in enumerate(core.M37_SPECTRAL_WIDTHS):
                core.update_m37_calibration(
                    accumulator,
                    products[width],
                    exclusion_mask=mask,
                )
            if (template_index + 1) % 5 == 0 or template_index + 1 == core.M37_TEMPLATE_COUNT:
                _emit_progress(
                    "calibration_progress",
                    window_id=window_id,
                    templates_complete=template_index + 1,
                    templates_total=core.M37_TEMPLATE_COUNT,
                    observed_maximum=float(accumulator.observed_maximum),
                )
            del products, mask
            gc.collect()
        summary = accumulator.finalize()
        calibrations.append(accumulator)
        summaries.append(summary)
        _emit_progress(
            "calibration_window_complete",
            window_id=window_id,
            observed_maximum=float(accumulator.observed_maximum),
            null_maxima_sha256=accumulator.null_maxima_sha256,
        )
    threshold = core.finalize_m37_threshold(calibrations)
    global_null = np.max(
        np.stack([item.null_maxima for item in calibrations], axis=0), axis=0
    )
    global_null = np.ascontiguousarray(global_null, dtype="<f8")
    global_null.setflags(write=False)
    calibration_record = {
        "artifact_type": "m37-detector-v0p6-calibration-inventory-v1",
        "run_id": record["run_id"],
        "window_count": len(summaries),
        "windows": summaries,
    }
    calibration_sha256 = _publish_or_verify(
        root / CALIBRATION_INVENTORY_PATH, calibration_record
    )
    updated = _advance(
        root,
        record,
        stage="calibration_complete",
        artifact_sha256=calibration_sha256,
        metadata={"window_count": len(summaries)},
    )
    global_receipt = null_artifact.publish_m37_global_null_artifact(
        root / GLOBAL_NULL_PATH,
        threshold,
        global_null,
        metadata={
            "run_id": record["run_id"],
            "calibration_inventory_sha256": calibration_sha256,
        },
    )
    updated = _advance(
        root,
        updated,
        stage="threshold_complete",
        artifact_sha256=global_receipt.file_sha256,
        metadata={
            "threshold_certificate_sha256": threshold.certificate_sha256,
            "global_null_maxima_sha256": threshold.global_null_maxima_sha256,
            "operational_threshold_snr": threshold.operational_threshold_snr,
        },
    )
    artifacts = dict(updated["artifacts"])
    artifacts["calibration_inventory"] = {"file_sha256": calibration_sha256}
    artifacts["global_null"] = global_receipt.__dict__
    updated["artifacts"] = artifacts
    _write_controller(root, updated)
    opened = null_artifact.open_global_null_artifact(
        root / GLOBAL_NULL_PATH,
        expected_file_sha256=global_receipt.file_sha256,
        expected_threshold_certificate_sha256=threshold.certificate_sha256,
        require_spectral_dataset_values_read=True,
    )
    _emit_progress(
        "threshold_complete",
        operational_threshold_snr=threshold.operational_threshold_snr,
        inclusive_rank_p_at_threshold=threshold.inclusive_rank_p_at_threshold,
    )
    return updated, opened


def adopt_run_004_calibration(
    root: Path,
    record: dict[str, Any],
    invalid_run_root: Path,
) -> tuple[dict[str, Any], null_artifact.GlobalNullArtifact]:
    """Adopt the unchanged sealed Run-004 threshold into amended Run 005."""
    if _stage_at_least(record, "threshold_complete"):
        return calibrate(root, record)
    if record["stage"] != "cache_manifest_complete":
        raise core.V0P6IncompleteError(
            "calibration adoption requires the complete cache manifest"
        )
    amendment = record.get("capacity_amendment")
    if amendment is None:
        raise core.V0P6IncompleteError(
            "calibration adoption requires the v0.6.1 capacity amendment"
        )
    profile = capacity_v0p6p1.validate_m37_v0p6p1_capacity_profile_record(
        amendment
    )
    source_record = _read_canonical(invalid_run_root / CONTROLLER_PATH)
    if (
        source_record.get("schema_version") != 1
        or source_record.get("artifact_type")
        != "m37-detector-v0p6-primary-controller-v1"
        or source_record.get("run_id") != "m37-v0p6-primary-004"
        or source_record.get("stage") != state.M37_INVALID_STAGE
        or source_record.get("journal_head_sha256")
        != capacity_v0p6p1.M37_V0P6P1_INVALID_RUN_JOURNAL_HEAD_SHA256
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption source is not sealed Run 004"
        )
    source_journal = state.read_m37_run_journal(
        invalid_run_root / "run.journal.jsonl",
        expected_head_sha256=source_record["journal_head_sha256"],
    )
    if (
        source_journal.run_id != source_record["run_id"]
        or source_journal.stage != state.M37_INVALID_STAGE
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption source journal changed"
        )
    failure_receipt = source_record["artifacts"].get(
        "retention_capacity_failure"
    )
    failure_path = invalid_run_root / "retention-capacity-failure.json"
    if (
        not isinstance(failure_receipt, Mapping)
        or failure_receipt.get("evidence_sha256")
        != capacity_v0p6p1.M37_V0P6P1_CAPACITY_FAILURE_EVIDENCE_SHA256
        or _sha256_file(failure_path) != failure_receipt.get("file_sha256")
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption failure ancestry changed"
        )
    failure = _read_canonical(failure_path)
    detached_failure = dict(failure)
    failure_evidence_sha256 = detached_failure.pop("evidence_sha256", None)
    if (
        failure_evidence_sha256
        != capacity_v0p6p1.M37_V0P6P1_CAPACITY_FAILURE_EVIDENCE_SHA256
        or _sha256_bytes(core.canonical_json_bytes(detached_failure))
        != failure_evidence_sha256
        or failure.get("failure_outcome") != "M37_INVALID_NO_CONCLUSION"
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption failure evidence changed"
        )

    current_bundle = _bundle(root, record)
    source_bundle = _bundle(invalid_run_root, source_record)
    if (
        current_bundle.receipt.factor_basis_sha256
        != source_bundle.receipt.factor_basis_sha256
        or current_bundle.receipt.factor_basis_labels_sha256
        != source_bundle.receipt.factor_basis_labels_sha256
        or current_bundle.receipt.factor_table_sha256
        != source_bundle.receipt.factor_table_sha256
        or current_bundle.receipt.analysis_contract_sha256
        != source_bundle.receipt.analysis_contract_sha256
        or current_bundle.table.template_bank_sha256
        != source_bundle.table.template_bank_sha256
        or core.canonical_json_bytes(list(current_bundle.scans))
        != core.canonical_json_bytes(list(source_bundle.scans))
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption scientific factor inventory differs"
        )
    current_manifest = _open_manifest(root, record, current_bundle)
    source_manifest = _open_manifest(
        invalid_run_root, source_record, source_bundle
    )
    current_cache = record["artifacts"]["cache_manifest"]
    source_cache = source_record["artifacts"]["cache_manifest"]
    required_cache_fields = (
        "inventory_sha256",
        "verified_inventory_sha256",
        "entry_count",
        "payload_nbytes",
    )
    if (
        any(current_cache[field] != source_cache[field]
            for field in required_cache_fields)
        or current_cache["factor_bundle_manifest_sha256"]
        != current_bundle.receipt.manifest_sha256
        or source_cache["factor_bundle_manifest_sha256"]
        != source_bundle.receipt.manifest_sha256
        or current_manifest.receipt.inventory_sha256
        != source_manifest.receipt.inventory_sha256
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption cache inventory differs"
        )

    calibration_receipt = source_record["artifacts"].get(
        "calibration_inventory"
    )
    source_calibration_path = invalid_run_root / CALIBRATION_INVENTORY_PATH
    if (
        not isinstance(calibration_receipt, Mapping)
        or _sha256_file(source_calibration_path)
        != calibration_receipt.get("file_sha256")
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption inventory identity changed"
        )
    source_calibration = _read_canonical(source_calibration_path)
    global_receipt = source_record["artifacts"].get("global_null")
    if not isinstance(global_receipt, Mapping):
        raise core.V0P6IncompleteError(
            "calibration adoption global-null receipt is absent"
        )
    source_global = null_artifact.open_global_null_artifact(
        invalid_run_root / GLOBAL_NULL_PATH,
        expected_file_sha256=global_receipt["file_sha256"],
        expected_threshold_certificate_sha256=global_receipt[
            "threshold_certificate_sha256"
        ],
        require_spectral_dataset_values_read=True,
    )
    summaries = source_calibration.get("windows")
    threshold = source_global.threshold
    if (
        source_calibration.get("artifact_type")
        != "m37-detector-v0p6-calibration-inventory-v1"
        or source_calibration.get("run_id") != source_record["run_id"]
        or source_calibration.get("window_count") != len(core.M37_WINDOW_IDS)
        or not isinstance(summaries, list)
        or [item.get("window_id") for item in summaries]
        != list(core.M37_WINDOW_IDS)
        or [item.get("null_maxima_sha256") for item in summaries]
        != list(threshold.null_maxima_sha256s)
        or [item.get("cache_provenance_inventory_sha256") for item in summaries]
        != list(threshold.calibration_cache_provenance_inventory_sha256s)
        or threshold.operational_threshold_snr != 126.20158386230469
    ):
        raise core.V0P6IncompleteError(
            "calibration adoption scientific inventory changed"
        )

    copied_calibration_sha256 = _publish_or_verify(
        root / SOURCE_CALIBRATION_INVENTORY_PATH, source_calibration
    )
    if copied_calibration_sha256 != calibration_receipt["file_sha256"]:
        raise core.V0P6IncompleteError(
            "calibration adoption copy identity changed"
        )
    source_global_record = _read_canonical(invalid_run_root / GLOBAL_NULL_PATH)
    copied_global_sha256 = _publish_or_verify(
        root / GLOBAL_NULL_PATH, source_global_record
    )
    if copied_global_sha256 != global_receipt["file_sha256"]:
        raise core.V0P6IncompleteError(
            "calibration adoption global-null copy changed"
        )
    adoption = {
        "artifact_type": "m37-detector-v0p6p1-calibration-adoption-v1",
        "run_id": record["run_id"],
        "source_run_id": source_record["run_id"],
        "capacity_amendment_file_sha256": profile.amendment_file_sha256,
        "source_invalid_journal_head_sha256": source_record[
            "journal_head_sha256"
        ],
        "source_capacity_failure_evidence_sha256": failure_evidence_sha256,
        "current_factor_bundle_manifest_sha256": (
            current_bundle.receipt.manifest_sha256
        ),
        "source_factor_bundle_manifest_sha256": (
            source_bundle.receipt.manifest_sha256
        ),
        "shared_factor_basis_sha256": current_bundle.receipt.factor_basis_sha256,
        "shared_factor_basis_labels_sha256": (
            current_bundle.receipt.factor_basis_labels_sha256
        ),
        "shared_factor_table_sha256": current_bundle.receipt.factor_table_sha256,
        "shared_analysis_contract_sha256": (
            current_bundle.receipt.analysis_contract_sha256
        ),
        "current_cache_run_manifest_file_sha256": current_cache[
            "file_sha256"
        ],
        "source_cache_run_manifest_file_sha256": source_cache["file_sha256"],
        "verified_cache_inventory_sha256": current_cache[
            "verified_inventory_sha256"
        ],
        "source_calibration_inventory_file_sha256": (
            copied_calibration_sha256
        ),
        "global_null_file_sha256": copied_global_sha256,
        "threshold_certificate_sha256": threshold.certificate_sha256,
        "operational_threshold_snr": threshold.operational_threshold_snr,
        "calibration_recomputed": False,
        "scientific_contract_changed": False,
    }
    adoption_sha256 = _publish_or_verify(
        root / CALIBRATION_ADOPTION_PATH, adoption
    )
    updated = _advance(
        root,
        record,
        stage="calibration_complete",
        artifact_sha256=adoption_sha256,
        metadata={
            "window_count": len(summaries),
            "calibration_adopted_from_run_id": source_record["run_id"],
            "calibration_adoption_sha256": adoption_sha256,
        },
    )
    updated = _advance(
        root,
        updated,
        stage="threshold_complete",
        artifact_sha256=copied_global_sha256,
        metadata={
            "threshold_certificate_sha256": threshold.certificate_sha256,
            "global_null_maxima_sha256": threshold.global_null_maxima_sha256,
            "operational_threshold_snr": threshold.operational_threshold_snr,
            "calibration_adopted_from_run_id": source_record["run_id"],
        },
    )
    artifacts = dict(updated["artifacts"])
    artifacts["calibration_adoption"] = {
        "file_sha256": adoption_sha256,
        "source_run_id": source_record["run_id"],
    }
    artifacts["calibration_inventory"] = {
        "file_sha256": copied_calibration_sha256,
        "path": SOURCE_CALIBRATION_INVENTORY_PATH,
        "adopted_from_run_id": source_record["run_id"],
    }
    artifacts["global_null"] = dict(global_receipt)
    updated["artifacts"] = artifacts
    _write_controller(root, updated)
    opened = null_artifact.open_global_null_artifact(
        root / GLOBAL_NULL_PATH,
        expected_file_sha256=global_receipt["file_sha256"],
        expected_threshold_certificate_sha256=global_receipt[
            "threshold_certificate_sha256"
        ],
        require_spectral_dataset_values_read=True,
    )
    _emit_progress(
        "calibration_adopted",
        source_run_id=source_record["run_id"],
        operational_threshold_snr=threshold.operational_threshold_snr,
        artifact_sha256=adoption_sha256,
    )
    return updated, opened


def _retention_artifact_path(root: Path, window_id: str, kind: str) -> Path:
    return root / "retention" / f"{window_id}-{kind}.json"


def _publish_retention(
    path: Path,
    *,
    records: Sequence[Mapping[str, Any]],
    certificate: Mapping[str, Any],
) -> tuple[str, str]:
    basis = {
        "artifact_type": "m37-detector-v0p6-retention-artifact-v1",
        "records": list(records),
        "certificate": dict(certificate),
    }
    file_sha256 = _publish_or_verify(path, basis)
    return file_sha256, str(certificate["retention_certificate_sha256"])


def _load_retention(
    path: Path, *, expected_file_sha256: str, expected_certificate_sha256: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if _sha256_file(path) != expected_file_sha256:
        raise core.V0P6IncompleteError("retention artifact identity changed")
    artifact = _read_canonical(path)
    certificate = core.validate_retention_certificate(
        artifact["certificate"],
        expected_certificate_sha256=expected_certificate_sha256,
    )
    records = artifact["records"]
    if not isinstance(records, list):
        raise core.V0P6ContractError("retention records are not a list")
    return records, certificate


def retain(
    root: Path,
    record: dict[str, Any],
    global_null: null_artifact.GlobalNullArtifact,
    validation_cache: native_cache.NativeFilterCacheValidationCache | None = None,
    *,
    kinds: Sequence[str] = ("on", "off"),
) -> dict[str, Any]:
    bundle = _bundle(root, record)
    manifest = _open_manifest(root, record, bundle)
    validator = validation_cache or native_cache.NativeFilterCacheValidationCache()
    (root / "retention").mkdir(exist_ok=True)
    updated = record
    amendment = record.get("capacity_amendment")
    profile = (
        None
        if amendment is None
        else capacity_v0p6p1.validate_m37_v0p6p1_capacity_profile_record(
            amendment
        )
    )
    for kind in kinds:
        stage = f"{kind}_retention_complete"
        if _stage_at_least(updated, stage):
            continue
        prerequisite = "threshold_complete" if kind == "on" else "on_retention_complete"
        if updated["stage"] != prerequisite:
            raise core.V0P6IncompleteError(f"{kind.upper()} retention prerequisite is absent")
        inventory: dict[str, Any] = {}
        for window_id in core.M37_WINDOW_IDS:
            if profile is None:
                ledger = core.make_m37_retention_ledger(
                    window_id,
                    kind,
                    global_null.threshold,
                    bundle.template_bank,
                    bundle.basis,
                    bundle.table,
                )
            else:
                ledger = capacity_v0p6p1.make_m37_v0p6p1_retention_ledger(
                    profile,
                    window_id,
                    kind,
                    global_null.threshold,
                    bundle.template_bank,
                    bundle.basis,
                    bundle.table,
                )
            for template_index, template in enumerate(bundle.template_bank):
                products, mask = _template_products(
                    root,
                    manifest,
                    bundle,
                    validator,
                    window_id=window_id,
                    kind=kind,
                    template_index=template_index,
                )
                for width_index, width in enumerate(core.M37_SPECTRAL_WIDTHS):
                    for subset in core.M37_ACTIVITY_SUBSETS:
                        ledger.add_hypothesis(
                            products[width],
                            subset,
                            template=template,
                            width_index=width_index,
                            width_channels=width,
                            exclusion_mask=mask,
                        )
                if (template_index + 1) % 5 == 0 or template_index + 1 == core.M37_TEMPLATE_COUNT:
                    _emit_progress(
                        "retention_progress",
                        scan_kind=kind,
                        window_id=window_id,
                        templates_complete=template_index + 1,
                        templates_total=core.M37_TEMPLATE_COUNT,
                    )
                del products, mask
                gc.collect()
            records = ledger.finalize()
            certificate = ledger.certificate()
            path = _retention_artifact_path(root, window_id, kind)
            file_sha256, certificate_sha256 = _publish_retention(
                path, records=records, certificate=certificate
            )
            inventory[window_id] = {
                "path": path.relative_to(root).as_posix(),
                "file_sha256": file_sha256,
                "certificate_sha256": certificate_sha256,
                "record_count": len(records),
            }
            _emit_progress(
                "retention_window_complete",
                scan_kind=kind,
                window_id=window_id,
                record_count=len(records),
            )
        inventory_basis = {
            "artifact_type": f"m37-detector-v0p6-{kind}-retention-inventory-v1",
            "run_id": updated["run_id"],
            "windows": inventory,
        }
        inventory_path = root / "retention" / f"{kind}-inventory.json"
        inventory_sha256 = _publish_or_verify(inventory_path, inventory_basis)
        updated = _advance(
            root,
            updated,
            stage=stage,
            artifact_sha256=inventory_sha256,
            metadata={
                "window_count": len(inventory),
                "record_count": sum(item["record_count"] for item in inventory.values()),
            },
        )
        artifacts = dict(updated["artifacts"])
        artifacts[f"retention_{kind}"] = {
            "inventory_file_sha256": inventory_sha256,
            "windows": inventory,
        }
        updated["artifacts"] = artifacts
        _write_controller(root, updated)
    return updated


def run_cache(
    root: Path, run_id: str, *, capacity_amendment: bool = False
) -> dict[str, Any]:
    record = prepare(
        root, run_id, capacity_amendment=capacity_amendment
    )
    record = authorize(root, record)
    return build_caches(root, record)


def analyze(
    root: Path, run_id: str, *, capacity_amendment: bool = False
) -> dict[str, Any]:
    record = run_cache(
        root, run_id, capacity_amendment=capacity_amendment
    )
    validator = native_cache.NativeFilterCacheValidationCache()
    record, global_null = calibrate(root, record, validator)
    record = retain(root, record, global_null, validator)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "prepare",
            "authorize",
            "build-caches",
            "calibrate",
            "adopt-calibration",
            "retain-on",
            "retain-off",
            "run-cache",
            "analyze",
            "status",
        ),
    )
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--capacity-amendment-v0p6p1",
        action="store_true",
        help="use the frozen post-contact capacity-only v0.6.1 amendment",
    )
    parser.add_argument(
        "--invalid-calibration-run-root",
        type=Path,
        help="sealed invalid Run-004 root used only by adopt-calibration",
    )
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.run_root,
            args.run_id,
            capacity_amendment=args.capacity_amendment_v0p6p1,
        )
    elif args.command == "status":
        result = _status(args.run_root)
    elif args.command == "run-cache":
        result = run_cache(
            args.run_root,
            args.run_id,
            capacity_amendment=args.capacity_amendment_v0p6p1,
        )
    elif args.command == "analyze":
        result = analyze(
            args.run_root,
            args.run_id,
            capacity_amendment=args.capacity_amendment_v0p6p1,
        )
    else:
        result = prepare(
            args.run_root,
            args.run_id,
            capacity_amendment=args.capacity_amendment_v0p6p1,
        )
        if args.command in {
            "authorize",
            "build-caches",
            "calibrate",
            "adopt-calibration",
            "retain-on",
            "retain-off",
        }:
            result = authorize(args.run_root, result)
        if args.command in {
            "build-caches",
            "calibrate",
            "adopt-calibration",
            "retain-on",
            "retain-off",
        }:
            result = build_caches(args.run_root, result)
        if args.command == "adopt-calibration":
            if args.invalid_calibration_run_root is None:
                parser.error(
                    "adopt-calibration requires "
                    "--invalid-calibration-run-root"
                )
            result, global_null = adopt_run_004_calibration(
                args.run_root,
                result,
                args.invalid_calibration_run_root,
            )
        if args.command in {"calibrate", "retain-on", "retain-off"}:
            result, global_null = calibrate(args.run_root, result)
        if args.command == "retain-on":
            result = retain(args.run_root, result, global_null, kinds=("on",))
        if args.command == "retain-off":
            result = retain(args.run_root, result, global_null, kinds=("on", "off"))
    print(core.canonical_json_bytes(result).decode(), flush=True)


if __name__ == "__main__":
    main()
