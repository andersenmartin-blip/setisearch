#!/usr/bin/env python3
"""Post-contact, non-normative M37 above-threshold capacity census.

This diagnostic replays every frozen ON and OFF hypothesis against the sealed
Run-004 threshold.  It counts and localizes all above-threshold score cells but
does not retain candidate records, alter the invalid run journal, apply vetoes,
or make a scientific claim.  Window/kind children are immutable and
restartable; the final manifest is published only after all ten children pass
cross-total and provenance checks.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT / "src"), str(ROOT / "scripts")):
    if item not in sys.path:
        sys.path.insert(0, item)

import numpy as np

import m37_v0p6_primary as primary
from seti_repeater import native_cache_v0p6 as native_cache
from seti_repeater import null_artifact_v0p6 as null_artifact
from seti_repeater import run_state_v0p6 as state
from seti_repeater import search_v0p6 as core


DIAGNOSTIC_ID = "m37-v0p6-capacity-census-001"
CHILD_ARTIFACT_TYPE = "m37-detector-v0p6-capacity-census-child-v1"
MANIFEST_ARTIFACT_TYPE = "m37-detector-v0p6-capacity-census-manifest-v1"
FREQUENCY_BUCKET_HZ = 10_000
RATIO_EDGES = (
    1.0,
    1.05,
    1.1,
    1.25,
    1.5,
    2.0,
    4.0,
    8.0,
    16.0,
    32.0,
    64.0,
    128.0,
    256.0,
)
KINDS = ("on", "off")
CHILD_CLAIM_BOUNDARY = {
    "diagnostic_only": True,
    "run_004_modified": False,
    "candidate_records_retained": False,
    "physical_vetoes_applied": False,
    "scientific_conclusion_permitted": False,
}
MANIFEST_CLAIM_BOUNDARY = {
    "diagnostic_only": True,
    "run_004_modified": False,
    "scientific_conclusion_permitted": False,
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _total_score_cells() -> int:
    hypotheses = (
        core.M37_TEMPLATE_COUNT
        * len(core.M37_SPECTRAL_WIDTHS)
        * len(core.M37_ACTIVITY_SUBSETS)
    )
    return 2 * hypotheses * sum(
        core.make_m37_proxy_carrier_grid(window_id).score_bin_count
        for window_id in core.M37_WINDOW_IDS
    )


def _script_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _open_global_null(root: Path, record: Mapping[str, Any]):
    receipt = record["artifacts"]["global_null"]
    return null_artifact.open_global_null_artifact(
        root / primary.GLOBAL_NULL_PATH,
        expected_file_sha256=receipt["file_sha256"],
        expected_threshold_certificate_sha256=receipt[
            "threshold_certificate_sha256"
        ],
        require_spectral_dataset_values_read=True,
    )


def _validate_invalid_run(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    record = primary._read_canonical(root / primary.CONTROLLER_PATH)
    if (
        record.get("schema_version") != 1
        or record.get("artifact_type")
        != "m37-detector-v0p6-primary-controller-v1"
        or not isinstance(record.get("run_id"), str)
        or record.get("stage") != state.M37_INVALID_STAGE
    ):
        raise core.V0P6IncompleteError(
            "capacity census requires the permanently invalid Run 004"
        )
    journal = state.read_m37_run_journal(
        root / "run.journal.jsonl",
        expected_head_sha256=record["journal_head_sha256"],
    )
    if journal.stage != state.M37_INVALID_STAGE:
        raise core.V0P6IncompleteError("capacity census journal is not invalid")
    final_line = (root / "run.journal.jsonl").read_bytes().splitlines()[-1]
    final_event = json.loads(final_line)
    failure_receipt = record["artifacts"].get("retention_capacity_failure")
    if not isinstance(failure_receipt, Mapping):
        raise core.V0P6IncompleteError(
            "capacity census lacks the Run-004 failure receipt"
        )
    failure_path = root / "retention-capacity-failure.json"
    if primary._sha256_file(failure_path) != failure_receipt["file_sha256"]:
        raise core.V0P6IncompleteError(
            "capacity census failure-evidence file changed"
        )
    failure = primary._read_canonical(failure_path)
    detached = dict(failure)
    evidence_sha256 = detached.pop("evidence_sha256")
    if (
        _sha256_bytes(core.canonical_json_bytes(detached)) != evidence_sha256
        or evidence_sha256 != failure_receipt["evidence_sha256"]
        or failure["failure_outcome"] != "M37_INVALID_NO_CONCLUSION"
        or final_event["stage"] != state.M37_INVALID_STAGE
        or final_event["metadata"]["reason_code"]
        != "retention-capacity-overflow"
        or final_event["artifact_sha256"] != failure_receipt["file_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "capacity census Run-004 invalidation ancestry changed"
        )
    return record, failure


def _ratio_histogram(values: np.ndarray, threshold: float) -> list[dict[str, Any]]:
    exact = np.asarray(values, dtype=np.float64)
    if exact.ndim != 1 or not np.all(np.isfinite(exact)):
        raise core.V0P6ContractError("capacity-census S/N values are invalid")
    if exact.size and np.any(exact < threshold):
        raise core.V0P6IncompleteError(
            "capacity-census histogram received a sub-threshold value"
        )
    edges = np.asarray(
        (*(threshold * value for value in RATIO_EDGES), np.inf),
        dtype=np.float64,
    )
    counts, _ = np.histogram(exact, bins=edges)
    return [
        {
            "lower_threshold_multiplier_inclusive": float(RATIO_EDGES[index]),
            "upper_threshold_multiplier_exclusive": (
                None
                if index + 1 == len(RATIO_EDGES)
                else float(RATIO_EDGES[index + 1])
            ),
            "count": int(count),
        }
        for index, count in enumerate(counts)
    ]


def _validate_child(
    value: Mapping[str, Any],
    *,
    expected_run_id: str,
    expected_window_id: str,
    expected_kind: str,
    expected_script_sha256: str,
    expected_source_metadata_sha256: str,
    expected_failure_evidence_sha256: str,
    expected_threshold_certificate_sha256: str,
    expected_operational_threshold_snr: float,
    expected_cache_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_journal_head_sha256: str,
    expected_line_indices: Sequence[int],
) -> dict[str, Any]:
    detached = json.loads(core.canonical_json_bytes(dict(value)))
    artifact_sha256 = detached.pop("artifact_sha256", None)
    calculated = _sha256_bytes(core.canonical_json_bytes(detached))
    if artifact_sha256 != calculated:
        raise core.V0P6IncompleteError(
            "capacity-census child artifact identity changed"
        )
    if (
        detached.get("artifact_type") != CHILD_ARTIFACT_TYPE
        or detached.get("diagnostic_id") != DIAGNOSTIC_ID
        or detached.get("run_id") != expected_run_id
        or detached.get("window_id") != expected_window_id
        or detached.get("scan_kind") != expected_kind
        or detached.get("diagnostic_orchestrator_sha256")
        != expected_script_sha256
        or detached.get("source_metadata_sha256")
        != expected_source_metadata_sha256
        or detached.get("capacity_failure_evidence_sha256")
        != expected_failure_evidence_sha256
        or detached.get("threshold_certificate_sha256")
        != expected_threshold_certificate_sha256
        or detached.get("operational_threshold_snr")
        != expected_operational_threshold_snr
        or detached.get("cache_run_manifest_file_sha256")
        != expected_cache_manifest_file_sha256
        or detached.get("factor_bundle_manifest_sha256")
        != expected_factor_bundle_manifest_sha256
        or detached.get("invalid_run_journal_head_sha256")
        != expected_journal_head_sha256
        or detached.get("claim_boundary") != CHILD_CLAIM_BOUNDARY
        or detached.get("proxy_grid_sha256")
        != core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(expected_window_id)
        )
        or detached.get("frequency_bucket_hz") != FREQUENCY_BUCKET_HZ
    ):
        raise core.V0P6IncompleteError(
            "capacity-census child provenance or claim boundary changed"
        )
    expected_hypotheses = (
        core.M37_TEMPLATE_COUNT
        * len(core.M37_SPECTRAL_WIDTHS)
        * len(core.M37_ACTIVITY_SUBSETS)
    )
    expected_cells = (
        expected_hypotheses
        * core.make_m37_proxy_carrier_grid(expected_window_id).score_bin_count
    )
    if len(expected_line_indices) != core.M37_TEMPLATE_COUNT:
        raise core.V0P6IncompleteError(
            "capacity-census template-bank dimensions changed"
        )
    total = core._strict_int(
        detached.get("above_threshold_record_count"),
        "capacity-census above-threshold count",
    )
    if total < 0:
        raise core.V0P6IncompleteError(
            "capacity-census child has a negative count"
        )
    template_counts = detached.get("counts_by_template")
    width_counts = detached.get("counts_by_width")
    subset_counts = detached.get("counts_by_activity_subset")
    frequency_counts = detached.get("frequency_buckets")
    histogram = detached.get("snr_ratio_histogram")
    nonzero = detached.get("nonzero_hypotheses")
    expected_templates = [
        {
            "template_index": index,
            "line_index": int(line_index),
        }
        for index, line_index in enumerate(expected_line_indices)
    ]
    expected_widths = [
        {"width_index": index, "width_channels": width}
        for index, width in enumerate(core.M37_SPECTRAL_WIDTHS)
    ]
    expected_subsets = [
        {"active_epochs_zero_based": list(subset)}
        for subset in core.M37_ACTIVITY_SUBSETS
    ]
    expected_histogram = [
        {
            "lower_threshold_multiplier_inclusive": float(RATIO_EDGES[index]),
            "upper_threshold_multiplier_exclusive": (
                None
                if index + 1 == len(RATIO_EDGES)
                else float(RATIO_EDGES[index + 1])
            ),
        }
        for index in range(len(RATIO_EDGES))
    ]
    if (
        not isinstance(template_counts, list)
        or [{key: item[key] for key in ("template_index", "line_index")}
            for item in template_counts] != expected_templates
        or not isinstance(width_counts, list)
        or [{key: item[key] for key in ("width_index", "width_channels")}
            for item in width_counts] != expected_widths
        or not isinstance(subset_counts, list)
        or [{"active_epochs_zero_based": item["active_epochs_zero_based"]}
            for item in subset_counts] != expected_subsets
        or not isinstance(histogram, list)
        or [
            {
                key: item[key]
                for key in (
                    "lower_threshold_multiplier_inclusive",
                    "upper_threshold_multiplier_exclusive",
                )
            }
            for item in histogram
        ] != expected_histogram
        or not isinstance(frequency_counts, list)
        or not isinstance(nonzero, list)
    ):
        raise core.V0P6IncompleteError(
            "capacity-census child dimensions or ordering changed"
        )
    if any(
        item.get("bucket_index") != bucket
        or item.get("lower_frequency_hz_inclusive")
        != bucket * FREQUENCY_BUCKET_HZ
        or item.get("upper_frequency_hz_exclusive")
        != (bucket + 1) * FREQUENCY_BUCKET_HZ
        or core._strict_int(item.get("count"), "frequency-bucket count") <= 0
        for item, bucket in zip(
            frequency_counts,
            sorted({item["bucket_index"] for item in frequency_counts}),
            strict=True,
        )
    ):
        raise core.V0P6IncompleteError(
            "capacity-census frequency buckets changed"
        )
    nonzero_keys = []
    for item in nonzero:
        template_index = core._strict_int(
            item.get("template_index"), "nonzero template index"
        )
        width_index = core._strict_int(
            item.get("width_index"), "nonzero width index"
        )
        subset = tuple(item.get("active_epochs_zero_based", ()))
        try:
            subset_index = core.M37_ACTIVITY_SUBSETS.index(subset)
        except ValueError as exc:
            raise core.V0P6IncompleteError(
                "capacity-census nonzero activity subset changed"
            ) from exc
        if (
            not 0 <= template_index < core.M37_TEMPLATE_COUNT
            or item.get("line_index")
            != int(expected_line_indices[template_index])
            or not 0 <= width_index < len(core.M37_SPECTRAL_WIDTHS)
            or item.get("width_channels")
            != core.M37_SPECTRAL_WIDTHS[width_index]
            or core._strict_int(item.get("count"), "nonzero count") <= 0
            or not isinstance(item.get("maximum_snr"), float)
            or not math.isfinite(item["maximum_snr"])
            or item["maximum_snr"] < expected_operational_threshold_snr
        ):
            raise core.V0P6IncompleteError(
                "capacity-census nonzero hypothesis changed"
            )
        nonzero_keys.append((template_index, width_index, subset_index))
    if nonzero_keys != sorted(set(nonzero_keys)):
        raise core.V0P6IncompleteError(
            "capacity-census nonzero hypothesis ordering changed"
        )
    maximum_snr = detached.get("maximum_snr")
    expected_maximum = (
        None if not nonzero else max(item["maximum_snr"] for item in nonzero)
    )
    if (
        detached.get("hypotheses_evaluated") != expected_hypotheses
        or detached.get("score_cells_evaluated") != expected_cells
        or detached.get("retention_capacity")
        != core.M37_MAXIMUM_RECORDS_PER_WINDOW
        or detached.get("capacity_exceeded")
        != (total > core.M37_MAXIMUM_RECORDS_PER_WINDOW)
        or maximum_snr != expected_maximum
        or sum(item["count"] for item in template_counts)
        != total
        or sum(item["count"] for item in width_counts)
        != total
        or sum(item["count"] for item in subset_counts)
        != total
        or sum(item["count"] for item in frequency_counts)
        != total
        or sum(item["count"] for item in histogram)
        != total
        or sum(item["count"] for item in nonzero)
        != total
        or detached.get("nonzero_hypothesis_count")
        != len(nonzero)
    ):
        raise core.V0P6IncompleteError(
            "capacity-census child cross-total accounting changed"
        )
    detached["artifact_sha256"] = artifact_sha256
    return detached


def _existing_child(
    path: Path,
    **expected: Any,
) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _validate_child(primary._read_canonical(path), **expected)


def _scan_child(
    run_root_text: str,
    output_root_text: str,
    window_id: str,
    kind: str,
) -> dict[str, Any]:
    run_root = Path(run_root_text)
    output_root = Path(output_root_text)
    record, failure = _validate_invalid_run(run_root)
    bundle = primary._bundle(run_root, record)
    manifest = primary._open_manifest(run_root, record, bundle)
    global_null = _open_global_null(run_root, record)
    child_path = output_root / "children" / f"{window_id}-{kind}.json"
    expected = {
        "expected_run_id": record["run_id"],
        "expected_window_id": window_id,
        "expected_kind": kind,
        "expected_script_sha256": _script_sha256(),
        "expected_source_metadata_sha256": record["bootstrap"][
            "source_metadata_sha256"
        ],
        "expected_failure_evidence_sha256": failure["evidence_sha256"],
        "expected_threshold_certificate_sha256": (
            global_null.threshold.certificate_sha256
        ),
        "expected_operational_threshold_snr": float(
            global_null.threshold.operational_threshold_snr
        ),
        "expected_cache_manifest_file_sha256": record["artifacts"][
            "cache_manifest"
        ]["file_sha256"],
        "expected_factor_bundle_manifest_sha256": bundle.receipt.manifest_sha256,
        "expected_journal_head_sha256": record["journal_head_sha256"],
        "expected_line_indices": tuple(
            int(template["line_index"]) for template in bundle.template_bank
        ),
    }
    existing = _existing_child(child_path, **expected)
    if existing is not None:
        primary._emit_progress(
            "capacity_census_child_reused",
            window_id=window_id,
            scan_kind=kind,
            above_threshold_record_count=existing[
                "above_threshold_record_count"
            ],
        )
        return {
            "window_id": window_id,
            "scan_kind": kind,
            "relative_path": child_path.relative_to(output_root).as_posix(),
            "file_sha256": primary._sha256_file(child_path),
            "artifact_sha256": existing["artifact_sha256"],
            "above_threshold_record_count": existing[
                "above_threshold_record_count"
            ],
            "nonzero_hypothesis_count": existing["nonzero_hypothesis_count"],
            "maximum_snr": existing["maximum_snr"],
            "capacity_exceeded": existing["capacity_exceeded"],
        }

    validator = native_cache.NativeFilterCacheValidationCache()
    threshold = float(global_null.threshold.operational_threshold_snr)
    grid = core.make_m37_proxy_carrier_grid(window_id)
    template_counts = [0] * core.M37_TEMPLATE_COUNT
    width_counts = [0] * len(core.M37_SPECTRAL_WIDTHS)
    subset_counts = [0] * len(core.M37_ACTIVITY_SUBSETS)
    frequency_counts: dict[int, int] = {}
    ratio_histogram_counts = [0] * len(RATIO_EDGES)
    nonzero_hypotheses: list[dict[str, Any]] = []
    total = 0
    score_cells = 0
    maximum_snr: float | None = None

    for template_index, template in enumerate(bundle.template_bank):
        products, mask = primary._template_products(
            run_root,
            manifest,
            bundle,
            validator,
            window_id=window_id,
            kind=kind,
            template_index=template_index,
        )
        try:
            for width_index, width in enumerate(core.M37_SPECTRAL_WIDTHS):
                for subset_index, subset in enumerate(core.M37_ACTIVITY_SUBSETS):
                    score = core.stack_hypothesis(
                        products[width].values,
                        subset,
                        minimum_active_epoch_snr=(
                            core.M37_MINIMUM_ACTIVE_EPOCH_SNR
                        ),
                        stack_statistic="minimum_epoch",
                        exclusion_mask=mask.values,
                    )
                    score_cells += int(score.size)
                    eligible = np.flatnonzero(
                        np.isfinite(score) & (score >= threshold)
                    )
                    count = int(eligible.size)
                    if count == 0:
                        continue
                    values = np.asarray(score[eligible], dtype=np.float64)
                    local_maximum = float(np.max(values))
                    maximum_snr = (
                        local_maximum
                        if maximum_snr is None
                        else max(maximum_snr, local_maximum)
                    )
                    total += count
                    template_counts[template_index] += count
                    width_counts[width_index] += count
                    subset_counts[subset_index] += count
                    frequency_bucket_indices = np.floor(
                        np.asarray(grid.score_hz[eligible], dtype=np.float64)
                        / FREQUENCY_BUCKET_HZ
                    ).astype(np.int64)
                    buckets, bucket_counts = np.unique(
                        frequency_bucket_indices, return_counts=True
                    )
                    for bucket, bucket_count in zip(
                        buckets.tolist(), bucket_counts.tolist(), strict=True
                    ):
                        exact_bucket = int(bucket)
                        frequency_counts[exact_bucket] = (
                            frequency_counts.get(exact_bucket, 0)
                            + int(bucket_count)
                        )
                    local_histogram = _ratio_histogram(values, threshold)
                    for index, item in enumerate(local_histogram):
                        ratio_histogram_counts[index] += item["count"]
                    nonzero_hypotheses.append(
                        {
                            "template_index": template_index,
                            "line_index": int(template["line_index"]),
                            "width_index": width_index,
                            "width_channels": width,
                            "active_epochs_zero_based": list(subset),
                            "count": count,
                            "maximum_snr": local_maximum,
                        }
                    )
        finally:
            del products, mask
        if (template_index + 1) % 5 == 0 or (
            template_index + 1 == core.M37_TEMPLATE_COUNT
        ):
            primary._emit_progress(
                "capacity_census_progress",
                window_id=window_id,
                scan_kind=kind,
                templates_complete=template_index + 1,
                templates_total=core.M37_TEMPLATE_COUNT,
                above_threshold_record_count=total,
            )

    snr_histogram = [
        {
            "lower_threshold_multiplier_inclusive": float(RATIO_EDGES[index]),
            "upper_threshold_multiplier_exclusive": (
                None
                if index + 1 == len(RATIO_EDGES)
                else float(RATIO_EDGES[index + 1])
            ),
            "count": int(count),
        }
        for index, count in enumerate(ratio_histogram_counts)
    ]
    basis = {
        "artifact_type": CHILD_ARTIFACT_TYPE,
        "diagnostic_id": DIAGNOSTIC_ID,
        "run_id": record["run_id"],
        "window_id": window_id,
        "scan_kind": kind,
        "claim_boundary": CHILD_CLAIM_BOUNDARY,
        "diagnostic_orchestrator_sha256": _script_sha256(),
        "source_metadata_sha256": record["bootstrap"][
            "source_metadata_sha256"
        ],
        "invalid_run_journal_head_sha256": record["journal_head_sha256"],
        "capacity_failure_evidence_sha256": failure["evidence_sha256"],
        "threshold_certificate_sha256": (
            global_null.threshold.certificate_sha256
        ),
        "operational_threshold_snr": threshold,
        "cache_run_manifest_file_sha256": record["artifacts"]["cache_manifest"][
            "file_sha256"
        ],
        "factor_bundle_manifest_sha256": bundle.receipt.manifest_sha256,
        "proxy_grid_sha256": core.proxy_carrier_grid_sha256(grid),
        "frequency_bucket_hz": FREQUENCY_BUCKET_HZ,
        "hypotheses_evaluated": (
            core.M37_TEMPLATE_COUNT
            * len(core.M37_SPECTRAL_WIDTHS)
            * len(core.M37_ACTIVITY_SUBSETS)
        ),
        "score_cells_evaluated": score_cells,
        "above_threshold_record_count": total,
        "nonzero_hypothesis_count": len(nonzero_hypotheses),
        "maximum_snr": maximum_snr,
        "retention_capacity": core.M37_MAXIMUM_RECORDS_PER_WINDOW,
        "capacity_exceeded": total > core.M37_MAXIMUM_RECORDS_PER_WINDOW,
        "counts_by_template": [
            {
                "template_index": index,
                "line_index": int(bundle.template_bank[index]["line_index"]),
                "count": count,
            }
            for index, count in enumerate(template_counts)
        ],
        "counts_by_width": [
            {
                "width_index": index,
                "width_channels": width,
                "count": width_counts[index],
            }
            for index, width in enumerate(core.M37_SPECTRAL_WIDTHS)
        ],
        "counts_by_activity_subset": [
            {
                "active_epochs_zero_based": list(subset),
                "count": subset_counts[index],
            }
            for index, subset in enumerate(core.M37_ACTIVITY_SUBSETS)
        ],
        "frequency_buckets": [
            {
                "bucket_index": bucket,
                "lower_frequency_hz_inclusive": bucket * FREQUENCY_BUCKET_HZ,
                "upper_frequency_hz_exclusive": (
                    (bucket + 1) * FREQUENCY_BUCKET_HZ
                ),
                "count": frequency_counts[bucket],
            }
            for bucket in sorted(frequency_counts)
        ],
        "snr_ratio_histogram": snr_histogram,
        "nonzero_hypotheses": nonzero_hypotheses,
    }
    basis["artifact_sha256"] = _sha256_bytes(core.canonical_json_bytes(basis))
    validated = _validate_child(basis, **expected)
    file_sha256 = primary._publish_or_verify(child_path, validated)
    primary._emit_progress(
        "capacity_census_child_complete",
        window_id=window_id,
        scan_kind=kind,
        above_threshold_record_count=total,
        capacity_exceeded=validated["capacity_exceeded"],
    )
    return {
        "window_id": window_id,
        "scan_kind": kind,
        "relative_path": child_path.relative_to(output_root).as_posix(),
        "file_sha256": file_sha256,
        "artifact_sha256": validated["artifact_sha256"],
        "above_threshold_record_count": total,
        "nonzero_hypothesis_count": len(nonzero_hypotheses),
        "maximum_snr": maximum_snr,
        "capacity_exceeded": validated["capacity_exceeded"],
    }


def _validate_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    detached = json.loads(core.canonical_json_bytes(dict(value)))
    manifest_sha256 = detached.pop("manifest_sha256", None)
    if _sha256_bytes(core.canonical_json_bytes(detached)) != manifest_sha256:
        raise core.V0P6IncompleteError(
            "capacity-census manifest identity changed"
        )
    entries = detached.get("entries")
    expected_order = [
        (window_id, kind)
        for window_id in core.M37_WINDOW_IDS
        for kind in KINDS
    ]
    if (
        detached.get("artifact_type") != MANIFEST_ARTIFACT_TYPE
        or detached.get("diagnostic_id") != DIAGNOSTIC_ID
        or detached.get("claim_boundary") != MANIFEST_CLAIM_BOUNDARY
        or detached.get("window_count") != len(core.M37_WINDOW_IDS)
        or detached.get("scan_kind_count") != len(KINDS)
        or detached.get("entry_count") != len(expected_order)
        or not isinstance(entries, list)
        or [(item["window_id"], item["scan_kind"]) for item in entries]
        != expected_order
        or detached.get("total_above_threshold_records")
        != sum(item["above_threshold_record_count"] for item in entries)
        or detached.get("total_score_cells_evaluated")
        != _total_score_cells()
    ):
        raise core.V0P6IncompleteError(
            "capacity-census manifest accounting changed"
        )
    detached["manifest_sha256"] = manifest_sha256
    return detached


def run_census(run_root: Path, output_root: Path, workers: int) -> dict[str, Any]:
    record, failure = _validate_invalid_run(run_root)
    bundle = primary._bundle(run_root, record)
    global_null = _open_global_null(run_root, record)
    (output_root / "children").mkdir(parents=True, exist_ok=True)
    results: dict[tuple[str, str], dict[str, Any]] = {}
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _scan_child,
                str(run_root),
                str(output_root),
                window_id,
                kind,
            ): (window_id, kind)
            for window_id in core.M37_WINDOW_IDS
            for kind in KINDS
        }
        for future in as_completed(futures):
            result = future.result()
            results[(result["window_id"], result["scan_kind"])] = result

    entries = [
        results[(window_id, kind)]
        for window_id in core.M37_WINDOW_IDS
        for kind in KINDS
    ]
    manifest = {
        "artifact_type": MANIFEST_ARTIFACT_TYPE,
        "diagnostic_id": DIAGNOSTIC_ID,
        "run_id": record["run_id"],
        "claim_boundary": MANIFEST_CLAIM_BOUNDARY,
        "diagnostic_orchestrator_sha256": _script_sha256(),
        "invalid_run_journal_head_sha256": record["journal_head_sha256"],
        "capacity_failure_evidence_sha256": failure["evidence_sha256"],
        "threshold_certificate_sha256": (
            global_null.threshold.certificate_sha256
        ),
        "cache_run_manifest_file_sha256": record["artifacts"]["cache_manifest"][
            "file_sha256"
        ],
        "factor_bundle_manifest_sha256": bundle.receipt.manifest_sha256,
        "worker_count": workers,
        "window_count": len(core.M37_WINDOW_IDS),
        "scan_kind_count": len(KINDS),
        "entry_count": len(entries),
        "total_score_cells_evaluated": _total_score_cells(),
        "total_above_threshold_records": sum(
            item["above_threshold_record_count"] for item in entries
        ),
        "entries": entries,
    }
    manifest["manifest_sha256"] = _sha256_bytes(
        core.canonical_json_bytes(manifest)
    )
    validated = _validate_manifest(manifest)
    primary._publish_or_verify(output_root / "capacity-census-manifest.json", validated)
    return validated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    result = run_census(args.run_root, args.output_root, args.workers)
    print(core.canonical_json_bytes(result).decode(), flush=True)


if __name__ == "__main__":
    main()
