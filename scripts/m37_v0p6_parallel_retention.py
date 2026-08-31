#!/usr/bin/env python3
"""Parallel, artifact-compatible M37 retention window orchestrator.

The scientific work for each M37 window is independent.  This controller runs
up to four windows concurrently, publishes the exact same immutable window and
inventory artifacts as ``m37_v0p6_primary.retain``, and advances the canonical
run journal only after every window has completed successfully.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gc
import hashlib
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT / "src"), str(ROOT / "scripts")):
    if item not in sys.path:
        sys.path.insert(0, item)

import m37_v0p6_primary as primary
from seti_repeater import native_cache_v0p6 as native_cache
from seti_repeater import null_artifact_v0p6 as null_artifact
from seti_repeater import capacity_v0p6p1 as capacity_v0p6p1
from seti_repeater import search_v0p6 as core


def _open_global_null(root: Path, record: dict[str, Any]):
    receipt = record["artifacts"]["global_null"]
    return null_artifact.open_global_null_artifact(
        root / primary.GLOBAL_NULL_PATH,
        expected_file_sha256=receipt["file_sha256"],
        expected_threshold_certificate_sha256=receipt[
            "threshold_certificate_sha256"
        ],
        require_spectral_dataset_values_read=True,
    )


def _retain_window(root_text: str, kind: str, window_id: str) -> dict[str, Any]:
    root = Path(root_text)
    record = primary._status(root)
    global_null = _open_global_null(root, record)
    bundle = primary._bundle(root, record)
    manifest = primary._open_manifest(root, record, bundle)
    validator = native_cache.NativeFilterCacheValidationCache()
    path = primary._retention_artifact_path(root, window_id, kind)
    amendment = record.get("capacity_amendment")
    profile = (
        None
        if amendment is None
        else capacity_v0p6p1.validate_m37_v0p6p1_capacity_profile_record(
            amendment
        )
    )
    expected_maximum_records = (
        core.M37_MAXIMUM_RECORDS_PER_WINDOW
        if profile is None
        else profile.maximum_records_per_window
    )

    if path.exists():
        artifact = primary._read_canonical(path)
        certificate_sha256 = str(
            artifact["certificate"]["retention_certificate_sha256"]
        )
        records, certificate = primary._load_retention(
            path,
            expected_file_sha256=primary._sha256_file(path),
            expected_certificate_sha256=certificate_sha256,
        )
        if certificate["maximum_records"] != expected_maximum_records:
            raise core.V0P6IncompleteError(
                "retention artifact uses another capacity protocol"
            )
        return {
            "window_id": window_id,
            "path": path.relative_to(root).as_posix(),
            "file_sha256": primary._sha256_file(path),
            "certificate_sha256": certificate[
                "retention_certificate_sha256"
            ],
            "record_count": len(records),
            "reused": True,
        }

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
        products, mask = primary._template_products(
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
        if (template_index + 1) % 5 == 0 or (
            template_index + 1 == core.M37_TEMPLATE_COUNT
        ):
            primary._emit_progress(
                "parallel_retention_progress",
                scan_kind=kind,
                window_id=window_id,
                templates_complete=template_index + 1,
                templates_total=core.M37_TEMPLATE_COUNT,
            )
        del products, mask
        gc.collect()

    records = ledger.finalize()
    certificate = ledger.certificate()
    file_sha256, certificate_sha256 = primary._publish_retention(
        path, records=records, certificate=certificate
    )
    return {
        "window_id": window_id,
        "path": path.relative_to(root).as_posix(),
        "file_sha256": file_sha256,
        "certificate_sha256": certificate_sha256,
        "record_count": len(records),
        "reused": False,
    }


def _script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def retain_kind(
    root: Path, record: dict[str, Any], kind: str, workers: int
) -> dict[str, Any]:
    stage = f"{kind}_retention_complete"
    if primary._stage_at_least(record, stage):
        return record
    prerequisite = "threshold_complete" if kind == "on" else "on_retention_complete"
    if record["stage"] != prerequisite:
        raise core.V0P6IncompleteError(
            f"{kind.upper()} retention prerequisite is absent"
        )

    (root / "retention").mkdir(exist_ok=True)
    results: dict[str, dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_retain_window, str(root), kind, window_id): window_id
            for window_id in core.M37_WINDOW_IDS
        }
        for future in as_completed(futures):
            result = future.result()
            window_id = result.pop("window_id")
            results[window_id] = result
            primary._emit_progress(
                "parallel_retention_window_complete",
                scan_kind=kind,
                window_id=window_id,
                record_count=result["record_count"],
                reused=result.pop("reused"),
            )

    inventory = {window_id: results[window_id] for window_id in core.M37_WINDOW_IDS}
    inventory_basis = {
        "artifact_type": f"m37-detector-v0p6-{kind}-retention-inventory-v1",
        "run_id": record["run_id"],
        "windows": inventory,
    }
    inventory_path = root / "retention" / f"{kind}-inventory.json"
    inventory_sha256 = primary._publish_or_verify(inventory_path, inventory_basis)
    updated = primary._advance(
        root,
        record,
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
    primary._write_controller(root, updated)
    primary._publish_or_verify(
        root / "retention" / f"parallel-execution-{kind}.json",
        {
            "artifact_type": "m37-detector-v0p6-parallel-retention-execution-v1",
            "run_id": record["run_id"],
            "scan_kind": kind,
            "worker_count": workers,
            "orchestrator_sha256": _script_sha256(),
            "capacity_amendment": record.get("capacity_amendment"),
            "retention_inventory_sha256": inventory_sha256,
        },
    )
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    parser.add_argument(
        "--kinds", nargs="+", choices=("on", "off"), default=("on", "off")
    )
    args = parser.parse_args()
    record = primary._status(args.run_root)
    for kind in args.kinds:
        record = retain_kind(args.run_root, record, kind, args.workers)
    print(core.canonical_json_bytes(record).decode(), flush=True)


if __name__ == "__main__":
    main()
