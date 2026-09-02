#!/usr/bin/env python3
"""Run the three frozen M39 real-data exhaustive anchor comparisons.

Each anchor injects one predeclared completeness trial into the rehydrated
M37 1412.5 MHz ON background, publishes 24 immutable injected caches, then
compares the bounded truth-local adapter with a complete 93-template replay.
Existing cache sidecars and completed anchor results are immutable restart
checkpoints.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import gc
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import sys
import time
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
for item in (str(ROOT / "src"), str(SCRIPTS)):
    if item not in sys.path:
        sys.path.insert(0, item)

import numpy as np

from seti_repeater import cache_manifest_v0p6 as cache_manifest
from seti_repeater import completeness_v0p6 as completeness
from seti_repeater import native_cache_v0p6 as native_cache
from seti_repeater import search_v0p6 as core
from seti_repeater.truth_local_v0p6 import (
    evaluate_truth_local_scores,
    plan_truth_local_template_scores_interval,
)


REHYDRATE_PATH = SCRIPTS / "m39_m37_rehydrate_1412p5.py"
SPEC = importlib.util.spec_from_file_location("m39_rehydrate", REHYDRATE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("M39 rehydration adapter is unavailable")
rehydrate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehydrate)


CONFIG_PATH = ROOT / "config/m39_m37_truth_local_qualification.json"
AGGREGATE_PATH = "m39-anchor-equivalence.json"


def sha256_json(value: Any) -> str:
    return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def _emit(event: str, **values: Any) -> None:
    print(
        core.canonical_json_bytes(
            {"event": event, "monotonic_seconds": time.monotonic(), **values}
        ).decode(),
        flush=True,
    )


def _publish_json(path: Path, value: Mapping[str, Any]) -> str:
    payload = core.canonical_json_bytes(dict(value))
    if path.exists():
        if path.read_bytes() != payload:
            raise core.V0P6IncompleteError(
                f"existing immutable M39 anchor artifact differs: {path}"
            )
        return hashlib.sha256(payload).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while publishing anchor artifact")
            view = view[written:]
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
        record = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(f"invalid anchor JSON: {path}") from error
    if not isinstance(record, dict) or core.canonical_json_bytes(record) != raw:
        raise core.V0P6ContractError(f"non-canonical anchor JSON: {path}")
    return record


def _anchor_trials(config: Mapping[str, Any]) -> tuple[tuple[dict[str, Any], Any], ...]:
    plan = completeness.make_m37_prospective_completeness_plan()
    trials = {
        (trial.level_index, trial.truth.truth_ordinal): trial
        for trial in completeness.iter_m37_completeness_trials(plan)
    }
    result = []
    for anchor in config["real_m37_anchor_inventory"]:
        record = json.loads(core.canonical_json_bytes(anchor))
        trial = trials[(record["level_index"], record["truth_ordinal"])]
        if (
            record["trial_id"] != trial.trial_id
            or record["truth_id"] != trial.truth.truth_id
            or record["proxy_carrier_index"]
            != trial.truth.proxy_carrier_index
        ):
            raise core.V0P6IncompleteError("frozen anchor inventory changed")
        result.append((record, trial))
    return tuple(result)


def _source_receipts(
    run_root: Path, labels: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    product_sha256s = []
    extraction_sha256s = []
    for label in labels:
        _, _, path = rehydrate._source_paths(run_root, label)
        receipt = rehydrate._read_canonical(path)
        product_sha256s.append(receipt["product_sha256"])
        extraction_sha256s.append(receipt["extraction_receipt_sha256"])
    return tuple(product_sha256s), tuple(extraction_sha256s)


def _product_stream(
    run_root: Path,
    scans: tuple[dict[str, Any], ...],
    labels: tuple[str, ...],
) -> Iterator[Any]:
    for label in labels:
        product = rehydrate.load_product(run_root, scans, label)
        yield product
        del product
        gc.collect()


def _injected_cache_paths(
    anchor_root: Path, scan_label: str, width: int
) -> tuple[Path, Path]:
    directory = anchor_root / "caches" / scan_label
    return directory / f"width-{width}.nfc", directory / f"width-{width}.json"


def _publish_injected_cache(
    anchor_root: Path,
    scan: Any,
    width: int,
    bundle: Any,
) -> cache_manifest.CacheManifestEntry:
    cache_path, sidecar_path = _injected_cache_paths(
        anchor_root, scan.scan_label, width
    )
    if sidecar_path.exists():
        sidecar = _read_canonical(sidecar_path)
        if sidecar.get("artifact_type") != "m39-injected-anchor-cache-v1":
            raise core.V0P6IncompleteError("injected cache sidecar changed")
        entry = cache_manifest._validate_entry(sidecar["entry"])
        if entry.source_sha256 != scan.scan_sha256:
            raise core.V0P6IncompleteError("injected cache source changed")
        return entry
    if cache_path.exists():
        raise core.V0P6IncompleteError("injected cache exists without sidecar")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    grid = core.make_m37_proxy_carrier_grid(rehydrate.WINDOW_ID)
    plan = core.plan_m37_native_filter_cache(
        scan.geometry,
        bundle.basis,
        bundle.table,
        bundle.scans,
        grid,
        width,
        window_id=rehydrate.WINDOW_ID,
        scan_label=scan.scan_label,
        source_sha256=scan.scan_sha256,
    )
    matches = [
        definition
        for definition in bundle.scans
        if str(definition["label"]) == scan.scan_label
    ]
    if len(matches) != 1:
        raise core.V0P6IncompleteError("injected scan definition changed")
    header = matches[0]["expected_header"]
    start, stop = rehydrate.source.m37_extraction_interval(
        rehydrate.WINDOW_ID
    )
    frequency_mhz = np.ascontiguousarray(
        (
            float(header["fch1_mhz"])
            + np.arange(start, stop, dtype="<f8")
            * float(header["foff_mhz"])
        )[::-1],
        dtype="<f8",
    )
    cache = core.build_native_filter_cache(
        scan.normalized, frequency_mhz, plan
    )
    receipt = native_cache.publish_native_filter_cache(cache_path, cache)
    entry = cache_manifest.make_cache_manifest_entry(
        cache_path.relative_to(anchor_root).as_posix(), plan, receipt
    )
    _publish_json(
        sidecar_path,
        {
            "artifact_type": "m39-injected-anchor-cache-v1",
            "entry": entry.as_record(),
            "injected_scan_sha256": scan.scan_sha256,
        },
    )
    return entry


def _build_injected_caches(
    anchor_root: Path, injected: Any, bundle: Any
) -> dict[tuple[int, int], cache_manifest.CacheManifestEntry]:
    entries: dict[tuple[int, int], cache_manifest.CacheManifestEntry] = {}
    for epoch, scan in enumerate(injected.scans):
        for width in core.M37_SPECTRAL_WIDTHS:
            entries[(epoch, width)] = _publish_injected_cache(
                anchor_root, scan, width, bundle
            )
        _emit(
            "anchor_scan_caches_complete",
            anchor_id=anchor_root.name,
            scan_label=scan.scan_label,
            cache_count=len(core.M37_SPECTRAL_WIDTHS),
        )
    return entries


def _array_inventory_sha256(
    arrays: Mapping[tuple[Any, ...], np.ndarray]
) -> str:
    records = []
    for key in sorted(arrays):
        array = np.ascontiguousarray(arrays[key])
        digest = hashlib.sha256(
            b"" if array.size == 0 else memoryview(array).cast("B")
        ).hexdigest()
        records.append(
            {
                "key": list(key),
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "sha256": digest,
            }
        )
    return sha256_json(records)


class AnchorCacheOpener:
    def __init__(
        self,
        anchor_root: Path,
        entries: Mapping[tuple[int, int], cache_manifest.CacheManifestEntry],
    ) -> None:
        self.anchor_root = anchor_root
        self.entries = dict(entries)
        self.validation_cache = native_cache.NativeFilterCacheValidationCache()

    @contextmanager
    def open(self, epoch: int, width: int):
        entry = self.entries[(epoch, width)]
        plan = core.native_filter_cache_plan_from_record(
            entry.plan_record,
            expected_plan_sha256=entry.plan_sha256,
        )
        with native_cache.open_native_filter_cache(
            self.anchor_root / entry.relative_path,
            expected_plan=plan,
            expected_plan_sha256=entry.plan_sha256,
            expected_manifest_sha256=entry.cache_manifest_sha256,
            validation_cache=self.validation_cache,
        ) as cache:
            yield cache


def _exhaustive_reference(
    anchor_id: str,
    plans: tuple[Any, ...],
    grid: Any,
    factor_matrices: tuple[np.ndarray, ...],
    opener: AnchorCacheOpener,
) -> dict[str, Any]:
    masks: dict[tuple[int], np.ndarray] = {}
    scores: dict[tuple[int, int, int], np.ndarray] = {}
    best: tuple[float, int, int, int, int] | None = None
    score_cells = 0
    for plan in plans:
        template = plan.template_index
        candidates = plan.candidate_indices.indices
        dense_by_width: dict[int, np.ndarray] = {}
        for width in core.M37_SPECTRAL_WIDTHS:
            epoch_vectors = []
            for epoch in range(3):
                with opener.open(epoch, width) as cache:
                    epoch_vectors.append(
                        core.gather_filtered_native(
                            cache,
                            factor_matrices[epoch][template],
                            grid,
                        )
                    )
            dense_by_width[width] = np.ascontiguousarray(
                np.stack(epoch_vectors, axis=0), dtype="<f4"
            )
        mask = np.ascontiguousarray(
            core.build_m37_two_pass_template_mask(
                lambda width: dense_by_width[width]
            )[:, candidates],
            dtype=bool,
        )
        masks[(template,)] = mask
        for width_index, width in enumerate(core.M37_SPECTRAL_WIDTHS):
            vectors = dense_by_width[width][:, candidates]
            for subset_index, subset in enumerate(core.M37_ACTIVITY_SUBSETS):
                score = np.ascontiguousarray(
                    core.stack_hypothesis(
                        vectors,
                        subset,
                        minimum_active_epoch_snr=3.0,
                        stack_statistic="minimum_epoch",
                        exclusion_mask=mask,
                    ),
                    dtype="<f4",
                )
                scores[(template, width_index, subset_index)] = score
                score_cells += score.size
                for ordinal, raw_value in enumerate(score):
                    value = float(raw_value)
                    if not math.isfinite(value):
                        continue
                    candidate = (
                        value,
                        template,
                        width_index,
                        subset_index,
                        int(candidates[ordinal]),
                    )
                    if best is None or value > best[0]:
                        best = candidate
        del dense_by_width
        gc.collect()
        completed = template + 1
        if completed % 10 == 0 or completed == len(plans):
            _emit(
                "exhaustive_anchor_progress",
                anchor_id=anchor_id,
                completed_template_count=completed,
                template_count=len(plans),
            )
    return {
        "candidate_score_cell_count": score_cells,
        "mask_inventory_sha256": _array_inventory_sha256(masks),
        "score_inventory_sha256": _array_inventory_sha256(scores),
        "best_truth_local_score_snr": None if best is None else best[0],
        "best_truth_local_score_float32_bits": None
        if best is None
        else int(np.float32(best[0]).view(np.uint32)),
        "best_hypothesis": None
        if best is None
        else {
            "template_index": best[1],
            "spectral_width_index": best[2],
            "spectral_width_channels": core.M37_SPECTRAL_WIDTHS[best[2]],
            "activity_subset_index": best[3],
            "active_epochs_zero_based": list(
                core.M37_ACTIVITY_SUBSETS[best[3]]
            ),
            "proxy_carrier_index": best[4],
            "proxy_carrier_hz": float(grid.score_hz[best[4]]),
        },
    }


def _comparison(
    adapter: Mapping[str, Any], reference: Mapping[str, Any]
) -> dict[str, Any]:
    adapter_score = adapter["best_truth_local_score_snr"]
    adapter_bits = (
        None
        if adapter_score is None
        else int(np.float32(adapter_score).view(np.uint32))
    )
    left = adapter["best_hypothesis"]
    right = reference["best_hypothesis"]
    checks = {
        "best-truth-local-score-float32-bits": (
            adapter_bits == reference["best_truth_local_score_float32_bits"]
        ),
        "best-template-index": (
            left is None and right is None
        ) or (
            left is not None
            and right is not None
            and left["template_index"] == right["template_index"]
        ),
        "best-spectral-width-index": (
            left is None and right is None
        ) or (
            left is not None
            and right is not None
            and left["spectral_width_index"]
            == right["spectral_width_index"]
        ),
        "best-activity-subset-index": (
            left is None and right is None
        ) or (
            left is not None
            and right is not None
            and left["activity_subset_index"]
            == right["activity_subset_index"]
        ),
        "best-proxy-carrier-index": (
            left is None and right is None
        ) or (
            left is not None
            and right is not None
            and left["proxy_carrier_index"]
            == right["proxy_carrier_index"]
        ),
        "two-pass-mask-candidate-bits": (
            adapter["mask_inventory_sha256"]
            == reference["mask_inventory_sha256"]
        ),
        "full-local-score-inventory": (
            adapter["score_inventory_sha256"]
            == reference["score_inventory_sha256"]
        ),
        "candidate-score-cell-count": (
            adapter["candidate_score_cell_count"]
            == reference["candidate_score_cell_count"]
        ),
    }
    return {"checks": checks, "passed": all(checks.values())}


def run_anchor(
    run_root: Path,
    bundle: Any,
    anchor: Mapping[str, Any],
    trial: Any,
) -> dict[str, Any]:
    anchor_id = str(anchor["anchor_id"])
    anchor_root = run_root / "anchors" / anchor_id
    result_path = anchor_root / "result.json"
    if result_path.exists():
        result = _read_canonical(result_path)
        if (
            result.get("anchor_id") != anchor_id
            or result.get("trial_id") != trial.trial_id
            or result.get("equivalence_passed") is not True
        ):
            raise core.V0P6IncompleteError("completed anchor result changed")
        _emit("anchor_complete", anchor_id=anchor_id, restart_hit=True)
        return result

    on_labels = ("epoch1_on", "epoch2_on", "epoch3_on")
    expected_products, expected_extractions = _source_receipts(
        run_root, on_labels
    )
    background = completeness.seal_m37_native_trial_background(
        trial,
        _product_stream(run_root, bundle.scans, on_labels),
        factor_basis=bundle.basis,
        factor_table=bundle.table,
        expected_product_sha256s=expected_products,
        expected_extraction_receipt_sha256s=expected_extractions,
        context={"anchor_id": anchor_id, "run_id": rehydrate.RUN_ID},
    )
    injected = completeness.inject_native_before_filter(background, trial)
    entries = _build_injected_caches(anchor_root, injected, bundle)
    opener = AnchorCacheOpener(anchor_root, entries)
    grid = core.make_m37_proxy_carrier_grid(rehydrate.WINDOW_ID)
    factor_matrices = tuple(
        np.ascontiguousarray(
            core.factor_table_for_scan(
                bundle.table, bundle.basis, label
            ),
            dtype="<f8",
        )
        for label in on_labels
    )
    truth_factors = np.ascontiguousarray(
        np.concatenate(
            tuple(
                core.template_factors_from_basis(
                    bundle.basis,
                    {
                        "coefficient_x": trial.truth.coefficient_x,
                        "coefficient_y": trial.truth.coefficient_y,
                    },
                    scan_label=label,
                )
                for label in on_labels
            )
        ),
        dtype="<f8",
    )
    distance_matrix = np.ascontiguousarray(
        np.concatenate(factor_matrices, axis=1), dtype="<f8"
    )
    plans = plan_truth_local_template_scores_interval(
        grid,
        distance_matrix,
        trial.truth.proxy_carrier_hz,
        truth_factors,
        tolerance_hz=completeness.M37_COMPLETENESS_RECOVERY_TOLERANCE_HZ,
    )
    source_sha256s = tuple(scan.scan_sha256 for scan in injected.scans)
    adapter = evaluate_truth_local_scores(
        plans,
        grid,
        factor_matrices,
        opener.open,
        expected_scan_labels=on_labels,
        expected_source_sha256s=source_sha256s,
        window_id=rehydrate.WINDOW_ID,
    )
    reference = _exhaustive_reference(
        anchor_id, plans, grid, factor_matrices, opener
    )
    comparison = _comparison(adapter, reference)
    if comparison["passed"] is not True:
        raise core.V0P6IncompleteError(
            f"M39 real-data anchor mismatch: {anchor_id}"
        )
    plan_records = [item.as_record() for item in plans]
    result = {
        "artifact_type": "m39-m37-real-anchor-equivalence-result-v1",
        "status": "passed",
        "run_id": rehydrate.RUN_ID,
        "window_id": rehydrate.WINDOW_ID,
        "anchor_id": anchor_id,
        "trial_id": trial.trial_id,
        "truth_id": trial.truth.truth_id,
        "ideal_single_epoch_snr": trial.ideal_single_epoch_snr,
        "spectral_width_channels": trial.truth.spectral_width_channels,
        "active_epochs_zero_based": list(
            trial.truth.active_epochs_zero_based
        ),
        "proxy_carrier_index": trial.truth.proxy_carrier_index,
        "injected_native_sha256": injected.injected_native_sha256,
        "background_sha256": background.background_sha256,
        "injected_cache_count": len(entries),
        "template_count": len(plans),
        "template_plan_inventory_sha256": sha256_json(plan_records),
        "candidate_proxy_cell_count": sum(
            item.candidate_indices.indices.size for item in plans
        ),
        "adapter": adapter,
        "exhaustive_reference": reference,
        "comparison": comparison,
        "equivalence_passed": True,
        "anchor_success_is_global_equivalence_proof": False,
    }
    result["result_sha256"] = sha256_json(result)
    _publish_json(result_path, result)
    _emit("anchor_complete", anchor_id=anchor_id, restart_hit=False)
    return result


def execute(run_root: Path, *, authorized: bool) -> dict[str, Any]:
    if authorized is not True:
        raise RuntimeError(
            "M39 anchor injections are not authorized; no injection executed"
        )
    completion = _read_canonical(run_root / rehydrate.COMPLETION)
    if (
        completion.get("status") != "complete"
        or completion.get("all_six_sources_verified") is not True
        or completion.get("all_48_caches_verified") is not True
    ):
        raise core.V0P6IncompleteError("M39 rehydration is incomplete")
    bundle = rehydrate.open_bundle(run_root)
    config = json.loads(CONFIG_PATH.read_text())
    results = [
        run_anchor(run_root, bundle, anchor, trial)
        for anchor, trial in _anchor_trials(config)
    ]
    aggregate = {
        "artifact_type": "m39-m37-real-anchor-equivalence-aggregate-v1",
        "status": "passed",
        "run_id": rehydrate.RUN_ID,
        "window_id": rehydrate.WINDOW_ID,
        "anchor_count": len(results),
        "passed_anchor_count": sum(
            item["equivalence_passed"] is True for item in results
        ),
        "anchors": [
            {
                "anchor_id": item["anchor_id"],
                "result_sha256": item["result_sha256"],
                "candidate_proxy_cell_count": item[
                    "candidate_proxy_cell_count"
                ],
                "equivalence_passed": item["equivalence_passed"],
            }
            for item in results
        ],
        "anchor_result_inventory_sha256": sha256_json(
            [item["result_sha256"] for item in results]
        ),
        "all_required_comparisons_passed": True,
        "anchor_success_is_global_equivalence_proof": False,
        "all_6144_calibration_trials_authorized": True,
        "calibration_trials_executed": 0,
    }
    aggregate["aggregate_sha256"] = sha256_json(aggregate)
    _publish_json(run_root / AGGREGATE_PATH, aggregate)
    return aggregate


def execute_one_anchor(
    run_root: Path,
    anchor_id: str,
    *,
    authorized: bool,
) -> dict[str, Any]:
    if authorized is not True:
        raise RuntimeError(
            "M39 anchor injections are not authorized; no injection executed"
        )
    completion = _read_canonical(run_root / rehydrate.COMPLETION)
    if (
        completion.get("status") != "complete"
        or completion.get("all_six_sources_verified") is not True
        or completion.get("all_48_caches_verified") is not True
    ):
        raise core.V0P6IncompleteError("M39 rehydration is incomplete")
    config = json.loads(CONFIG_PATH.read_text())
    selected = [
        (anchor, trial)
        for anchor, trial in _anchor_trials(config)
        if anchor["anchor_id"] == anchor_id
    ]
    if len(selected) != 1:
        raise core.V0P6ContractError("requested M39 anchor is unknown")
    bundle = rehydrate.open_bundle(run_root)
    return run_anchor(run_root, bundle, *selected[0])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--authorize-anchor-injections", action="store_true")
    parser.add_argument("--anchor-id")
    arguments = parser.parse_args()
    if arguments.anchor_id is None:
        result = execute(
            arguments.run_root.resolve(),
            authorized=arguments.authorize_anchor_injections,
        )
    else:
        result = execute_one_anchor(
            arguments.run_root.resolve(),
            arguments.anchor_id,
            authorized=arguments.authorize_anchor_injections,
        )
    print(core.canonical_json_bytes(result).decode(), flush=True)


if __name__ == "__main__":
    main()
