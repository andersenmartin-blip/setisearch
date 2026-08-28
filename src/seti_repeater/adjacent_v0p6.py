"""Sparse native gathers and the detector-v0.6 adjacent-OFF veto.

The retained-ON ledger is intentionally independent of this module.  This
pass consumes that sealed ledger, evaluates only each member's exact
``(q, template, width)`` track in the three paired OFF scans, and emits a
separate evidence product keyed by retained-record ID.  A later disposition
pass can therefore apply the frozen precedence without rewriting retention
evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from . import search_v0p6 as core


M37_SINGLE_ADJACENT_OFF_SNR_FLOOR = 5.5
M37_MAXIMUM_SINGLE_ADJACENT_OFF_QUERIES = (
    3 * core.M37_MAXIMUM_RECORDS_PER_WINDOW
)

_PRIOR_OFF_DISPOSITIONS = frozenset(
    {
        "rfi_veto_matched_off_same_hypothesis",
        "rfi_veto_local_off_track",
    }
)

_ADJACENT_EVIDENCE_FIELDS = frozenset(
    {
        "record_id",
        "template_index",
        "spectral_width_index",
        "spectral_width_channels",
        "proxy_carrier_index",
        "proxy_carrier_hz",
        "active_epochs_zero_based",
        "single_epoch_snr_floor",
        "comparison",
        "exact_same_q_template_width",
        "exclusion_mask_applied",
        "frequency_neighborhood_hz",
        "paired_adjacent_off_measurements",
        "matching_active_epochs_zero_based",
        "maximum_active_epoch_snr",
        "vetoed",
        "recommended_member_disposition",
    }
)

_ADJACENT_MEASUREMENT_FIELDS = frozenset(
    {
        "epoch_zero_based",
        "paired_on_scan_label",
        "paired_off_scan_label",
        "snr",
        "meets_single_epoch_floor",
    }
)


def _finite_json_number(value: Any, label: str) -> float:
    """Require a JSON numeric scalar without accepting bools or strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise core.V0P6ContractError(f"{label} must be a finite JSON number")
    converted = float(value)
    if not math.isfinite(converted):
        raise core.V0P6ContractError(f"{label} must be a finite JSON number")
    return converted


def _score_indices(values: Sequence[int] | np.ndarray, count: int) -> np.ndarray:
    """Return exact, bounded score-grid indices without float truncation."""
    if isinstance(values, np.ndarray):
        if values.ndim != 1:
            raise core.V0P6ContractError(
                "sparse q indices must be one-dimensional"
            )
        original = tuple(values)
    else:
        try:
            original = tuple(values)
        except TypeError as error:
            raise core.V0P6ContractError(
                "sparse q indices must be an exact-integer sequence"
            ) from error
    exact = np.empty(len(original), dtype=np.int64)
    for ordinal, value in enumerate(original):
        exact[ordinal] = core._strict_int(value, "sparse q index")
    if exact.size and (
        int(np.min(exact)) < 0 or int(np.max(exact)) >= count
    ):
        raise core.V0P6ContractError(
            "sparse q index is outside the score grid"
        )
    return exact


def gather_filtered_native_at_score_indices(
    cache: Any,
    factors: np.ndarray,
    grid: core.ProxyCarrierGrid,
    score_indices: Sequence[int] | np.ndarray,
    *,
    chunk_bins: int = 131_072,
) -> np.ndarray:
    """Gather selected score-grid cells from an in-memory or disk cache.

    Output order is exactly input order and duplicate indices remain
    duplicate.  Accumulation across integrations uses the same float32 order
    as :func:`search_v0p6.gather_filtered_native`, but neither the complete q
    mapping nor the complete q score vector is materialized.
    """
    plan, cache_values = core._cache_values_for_gather(cache)
    if core.proxy_carrier_grid_sha256(grid) != plan.proxy_grid_sha256:
        raise core.V0P6ContractError(
            "cache and proxy-grid identities differ"
        )
    factor = np.asarray(factors, dtype=np.float64)
    if factor.shape != (plan.integration_count,):
        raise core.V0P6ContractError(
            "factor count does not match the filter cache"
        )
    if not np.all(np.isfinite(factor)) or np.any(factor <= 0.0):
        raise core.V0P6ContractError(
            "all track factors must be finite and positive"
        )
    if core.float64_vector_sha256(factor) not in plan.factor_row_sha256s:
        raise core.V0P6ContractError(
            "requested factor row is absent from the planned template table"
        )
    chunk_bins = core._strict_int(chunk_bins, "q-gather chunk size")
    if chunk_bins < 1:
        raise core.V0P6ContractError(
            "q-gather chunk size must be positive"
        )
    selected = _score_indices(score_indices, grid.score_bin_count)
    accumulator = np.zeros(selected.size, dtype=np.float32)
    support_indices = selected + core._strict_int(
        grid.support_guard_bins, "proxy-grid support guard"
    )
    if support_indices.size and (
        int(np.min(support_indices)) < 0
        or int(np.max(support_indices)) >= grid.support_bin_count
    ):
        raise core.V0P6ContractError(
            "score grid is not a valid crop of its support grid"
        )

    for integration_index in range(plan.integration_count):
        row_factor = float(factor[integration_index])
        nominal_step = (
            float(grid.channel_width_hz)
            * row_factor
            / float(plan.geometry.channel_width_hz)
        )
        if not math.isfinite(nominal_step) or not 1.0 <= nominal_step <= 2.0:
            raise core.V0P6ContractError(
                "q-to-raw mapping step is outside the frozen {1,2} contract: "
                f"integration={integration_index}"
            )
        # Arbitrary requested indices cannot themselves be passed to the
        # monotonic full-vector validator.  Check every selected cell together
        # with its immediate support-grid neighbours instead.  The nominal
        # affine-step gate above covers skipped intervals without constructing
        # the complete q mapping.
        if support_indices.size:
            local_support = np.unique(
                np.concatenate(
                    (
                        support_indices,
                        np.maximum(support_indices - 1, 0),
                        np.minimum(
                            support_indices + 1,
                            grid.support_bin_count - 1,
                        ),
                    )
                )
            )
            local_mapping = core.nearest_native_indices(
                plan.geometry,
                grid.support_hz[local_support] * row_factor,
            )
            adjacent = np.diff(local_support) == 1
            adjacent_steps = np.diff(local_mapping)[adjacent]
            if np.any(~np.isin(adjacent_steps, (1, 2))):
                raise core.V0P6ContractError(
                    "q-to-raw nearest-channel mapping is not injective and "
                    f"monotonic: integration={integration_index}"
                )
        for start in range(0, selected.size, chunk_bins):
            stop = min(start + chunk_bins, selected.size)
            indices = core.nearest_native_indices(
                plan.geometry,
                grid.support_hz[support_indices[start:stop]] * row_factor,
            )
            if (
                int(np.min(indices)) < plan.raw_center_start
                or int(np.max(indices)) >= plan.raw_center_stop
            ):
                raise core.V0P6CoverageError(
                    "native filter cache does not cover the requested q track"
                )
            accumulator[start:stop] += cache_values[
                integration_index, indices - plan.raw_center_start
            ]
    accumulator /= np.float32(math.sqrt(plan.integration_count))
    return accumulator


def disposition_after_single_adjacent_off(
    prior_disposition: str,
    vetoed: bool,
) -> str:
    """Apply only this stage of the frozen physical-disposition precedence."""
    if not isinstance(vetoed, (bool, np.bool_)):
        raise core.V0P6ContractError(
            "single-adjacent-OFF veto state must be boolean"
        )
    prior = str(prior_disposition)
    if prior in _PRIOR_OFF_DISPOSITIONS:
        return prior
    if prior not in {
        "pending_physical_veto_evaluation",
        "pending_receiver_alias_evaluation",
    }:
        raise core.V0P6ContractError(
            "single-adjacent-OFF pass received an unknown prior disposition"
        )
    if bool(vetoed):
        return "rfi_veto_single_adjacent_off"
    return "pending_receiver_alias_evaluation"


def _normalise_cache_inventory(
    off_caches_by_width: Mapping[int, Mapping[str, Any]],
    widths: tuple[int, ...],
    off_labels: tuple[str, ...],
) -> dict[int, dict[str, Any]]:
    if not isinstance(off_caches_by_width, Mapping):
        raise core.V0P6ContractError(
            "adjacent OFF caches must be mapped by spectral width"
        )
    normalised: dict[int, dict[str, Any]] = {}
    for raw_width, raw_caches in off_caches_by_width.items():
        width = core._strict_int(raw_width, "OFF cache spectral width")
        if width in normalised:
            raise core.V0P6IncompleteError(
                "adjacent OFF cache inventory has duplicate widths"
            )
        if not isinstance(raw_caches, Mapping):
            raise core.V0P6ContractError(
                "adjacent OFF scan caches must be a mapping"
            )
        labels: dict[str, Any] = {}
        for raw_label, cache in raw_caches.items():
            label = str(raw_label)
            if label in labels:
                raise core.V0P6IncompleteError(
                    "adjacent OFF cache inventory has duplicate scan labels"
                )
            labels[label] = cache
        normalised[width] = labels
    if set(normalised) != set(widths):
        raise core.V0P6IncompleteError(
            "adjacent OFF cache width inventory is incomplete or contains extras"
        )
    expected_labels = set(off_labels)
    for width in widths:
        if set(normalised[width]) != expected_labels:
            raise core.V0P6IncompleteError(
                "adjacent OFF scan-cache inventory is incomplete or contains extras"
            )
    return normalised


def _validate_off_cache_inventory(
    caches: Mapping[int, Mapping[str, Any]],
    widths: tuple[int, ...],
    off_definitions: tuple[Mapping[str, Any], ...],
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    grid: core.ProxyCarrierGrid,
    *,
    window_id: str,
) -> tuple[list[dict[str, Any]], tuple[np.ndarray, ...]]:
    scan_factor_tables = tuple(
        core.factor_table_for_scan(
            factor_table, factor_basis, str(definition["label"])
        )
        for definition in off_definitions
    )
    grid_sha256 = core.proxy_carrier_grid_sha256(grid)
    inventory: list[dict[str, Any]] = []
    scan_digest = core.scan_inventory_sha256(scan_definitions)
    for width in widths:
        for epoch, (definition, scan_table) in enumerate(
            zip(off_definitions, scan_factor_tables, strict=True)
        ):
            label = str(definition["label"])
            cache = caches[width][label]
            plan, _ = core._cache_values_for_gather(cache)
            expected_integration_count = core._strict_int(
                definition["expected_header"]["dataset_shape"][0],
                "integration count",
            )
            if (
                plan.window_id != window_id
                or plan.scan_label != label
                or plan.scan_kind != "off"
                or plan.width_channels != width
                or plan.integration_count != expected_integration_count
                or plan.proxy_grid_sha256 != grid_sha256
                or plan.factor_basis_sha256 != factor_basis.basis_sha256
                or plan.factor_basis_labels_sha256
                != factor_basis.labels_sha256
                or plan.scan_inventory_sha256 != scan_digest
                or plan.factor_scan_selection_sha256
                != core.factor_scan_selection_sha256(
                    factor_basis, scan_definitions, label
                )
                or plan.template_bank_sha256
                != factor_table.template_bank_sha256
                or plan.factor_table_sha256
                != core.factor_table_sha256(scan_table)
            ):
                raise core.V0P6ContractError(
                    "adjacent OFF cache identity differs from the requested search"
                )
            inventory.append(
                {
                    "spectral_width_channels": width,
                    "epoch_zero_based": epoch,
                    "scan_label": label,
                    "cache_plan_sha256": plan.plan_sha256,
                    "cache_payload_sha256": cache.payload_sha256,
                }
            )
    return inventory, scan_factor_tables


def evaluate_single_adjacent_off_veto(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    off_caches_by_width: Mapping[int, Mapping[str, Any]],
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    template_bank: Sequence[Mapping[str, Any]],
    grid: core.ProxyCarrierGrid,
    *,
    single_epoch_snr_floor: float,
    maximum_records: int,
    maximum_queries: int,
    maximum_evidence_canonical_bytes: int,
    expected_on_certificate_sha256: str | None = None,
    chunk_bins: int = 131_072,
) -> dict[str, Any]:
    """Evaluate every retained ON member on its exact paired OFF tracks.

    The cache inventory must contain exactly one cache for every certified
    width and each of the three OFF scans.  No exclusion mask and no local
    frequency neighbourhood is used.
    """
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    if cert["scan_kind"] != "on":
        raise core.V0P6ContractError(
            "single-adjacent-OFF evaluation requires an ON retention product"
        )
    maximum_records = core._strict_int(
        maximum_records, "single-adjacent-OFF record capacity"
    )
    maximum_queries = core._strict_int(
        maximum_queries, "single-adjacent-OFF query capacity"
    )
    maximum_evidence_canonical_bytes = core._strict_int(
        maximum_evidence_canonical_bytes,
        "single-adjacent-OFF evidence-byte capacity",
    )
    if min(maximum_records, maximum_queries) < 0 or (
        maximum_evidence_canonical_bytes < 1
    ):
        raise core.V0P6ContractError(
            "single-adjacent-OFF capacities must be non-negative"
        )
    floor = float(single_epoch_snr_floor)
    if (
        not math.isfinite(floor)
        or floor != M37_SINGLE_ADJACENT_OFF_SNR_FLOOR
    ):
        raise core.V0P6ContractError(
            "single-adjacent-OFF S/N floor changed from the frozen 5.5"
        )
    chunk_bins = core._strict_int(chunk_bins, "q-gather chunk size")
    if chunk_bins < 1:
        raise core.V0P6ContractError(
            "q-gather chunk size must be positive"
        )

    core.validate_factor_basis(factor_basis)
    core.validate_factor_basis_scan_inventory(factor_basis, scan_definitions)
    core.validate_template_factor_table(
        factor_table,
        factor_basis,
        template_bank,
        expected_template_bank_sha256=cert["template_bank_sha256"],
    )
    scan_digest = core.scan_inventory_sha256(scan_definitions)
    if (
        factor_basis.basis_sha256 != cert["factor_basis_sha256"]
        or factor_basis.labels_sha256
        != cert["factor_basis_labels_sha256"]
        or factor_table.factor_table_sha256 != cert["factor_table_sha256"]
        or scan_digest != cert["scan_inventory_sha256"]
        or core.factor_row_selection_sha256(
            factor_basis, scan_definitions, "on"
        )
        != cert["factor_row_selection_sha256"]
    ):
        raise core.V0P6ContractError(
            "retention and adjacent-OFF factor contracts differ"
        )
    template_count = int(factor_table.factors.shape[0])
    records = core._validated_retained_records(
        on_records,
        cert,
        grid,
        expected_kind="on",
        expected_template_count=template_count,
        template_bank=template_bank,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    if len(records) > maximum_records:
        raise core.V0P6CapacityError(
            "single-adjacent-OFF record capacity exceeded"
        )

    widths = tuple(core._strict_widths(cert["spectral_widths"]))
    off_indices = core.m37_scan_indices_for_kind(scan_definitions, "off")
    on_indices = core.m37_scan_indices_for_kind(scan_definitions, "on")
    off_definitions = tuple(scan_definitions[index] for index in off_indices)
    off_labels = tuple(str(item["label"]) for item in off_definitions)
    on_labels = tuple(str(scan_definitions[index]["label"]) for index in on_indices)
    caches = _normalise_cache_inventory(
        off_caches_by_width, widths, off_labels
    )
    cache_inventory, scan_factor_tables = _validate_off_cache_inventory(
        caches,
        widths,
        off_definitions,
        scan_definitions,
        factor_basis,
        factor_table,
        grid,
        window_id=str(cert["window_id"]),
    )

    query_inventory: list[dict[str, Any]] = []
    groups: dict[tuple[int, int, int], list[tuple[int, int]]] = {}
    for record_ordinal, record in enumerate(records):
        width_index = core._strict_int(
            record["spectral_width_index"], "spectral-width index"
        )
        template_index = core._strict_int(
            record["template_index"], "template index"
        )
        score_index = core._strict_int(
            record["proxy_carrier_index"], "proxy-carrier index"
        )
        active_epochs = core.canonical_activity_subsets(
            (record["active_epochs_zero_based"],)
        )[0]
        for epoch in active_epochs:
            groups.setdefault((width_index, template_index, epoch), []).append(
                (record_ordinal, score_index)
            )
            query_inventory.append(
                {
                    "record_id": str(record["record_id"]),
                    "epoch_zero_based": epoch,
                    "paired_off_scan_label": off_labels[epoch],
                    "template_index": template_index,
                    "spectral_width_index": width_index,
                    "proxy_carrier_index": score_index,
                }
            )
    if len(query_inventory) > maximum_queries:
        raise core.V0P6CapacityError(
            "single-adjacent-OFF query capacity exceeded"
        )

    measured: dict[tuple[int, int], np.float32] = {}
    for width_index, template_index, epoch in sorted(groups):
        requests = groups[(width_index, template_index, epoch)]
        width = widths[width_index]
        cache = caches[width][off_labels[epoch]]
        factors = scan_factor_tables[epoch][template_index]
        values = gather_filtered_native_at_score_indices(
            cache,
            factors,
            grid,
            np.asarray([item[1] for item in requests], dtype=np.int64),
            chunk_bins=chunk_bins,
        )
        if values.shape != (len(requests),) or not np.all(np.isfinite(values)):
            raise core.V0P6IncompleteError(
                "single-adjacent-OFF sparse gather returned incomplete evidence"
            )
        for (record_ordinal, _), value in zip(requests, values, strict=True):
            key = (record_ordinal, epoch)
            if key in measured:
                raise core.V0P6IncompleteError(
                    "single-adjacent-OFF query was evaluated more than once"
                )
            measured[key] = np.float32(value)
    if len(measured) != len(query_inventory):
        raise core.V0P6IncompleteError(
            "single-adjacent-OFF query inventory was not evaluated exactly once"
        )

    evidence: list[dict[str, Any]] = []
    for record_ordinal, record in enumerate(records):
        active_epochs = core.canonical_activity_subsets(
            (record["active_epochs_zero_based"],)
        )[0]
        measurements = []
        matching_epochs: list[int] = []
        for epoch in active_epochs:
            value = float(measured[(record_ordinal, epoch)])
            matched = bool(value >= floor)
            if matched:
                matching_epochs.append(epoch)
            measurements.append(
                {
                    "epoch_zero_based": epoch,
                    "paired_on_scan_label": on_labels[epoch],
                    "paired_off_scan_label": off_labels[epoch],
                    "snr": value,
                    "meets_single_epoch_floor": matched,
                }
            )
        vetoed = bool(matching_epochs)
        item = {
            "record_id": str(record["record_id"]),
            "template_index": core._strict_int(
                record["template_index"], "template index"
            ),
            "spectral_width_index": core._strict_int(
                record["spectral_width_index"], "spectral-width index"
            ),
            "spectral_width_channels": core._strict_int(
                record["spectral_width_channels"], "spectral width"
            ),
            "proxy_carrier_index": core._strict_int(
                record["proxy_carrier_index"], "proxy-carrier index"
            ),
            "proxy_carrier_hz": float(record["proxy_carrier_hz"]),
            "active_epochs_zero_based": list(active_epochs),
            "single_epoch_snr_floor": floor,
            "comparison": "native_gathered_snr >= single_epoch_snr_floor",
            "exact_same_q_template_width": True,
            "exclusion_mask_applied": False,
            "frequency_neighborhood_hz": 0.0,
            "paired_adjacent_off_measurements": measurements,
            "matching_active_epochs_zero_based": matching_epochs,
            "maximum_active_epoch_snr": max(
                item["snr"] for item in measurements
            ),
            "vetoed": vetoed,
            "recommended_member_disposition": (
                "rfi_veto_single_adjacent_off"
                if vetoed
                else "pending_receiver_alias_evaluation"
            ),
        }
        if len(core.canonical_json_bytes(item)) > core._strict_int(
            cert["maximum_record_canonical_bytes"],
            "canonical record-byte capacity",
        ):
            raise core.V0P6CapacityError(
                "single-adjacent-OFF evidence record exceeds the byte capacity"
            )
        evidence.append(item)

    evidence_bytes = core.canonical_json_bytes(evidence)
    if len(evidence_bytes) > maximum_evidence_canonical_bytes:
        raise core.V0P6CapacityError(
            "single-adjacent-OFF evidence exceeds the byte capacity"
        )
    evidence_sha256 = hashlib.sha256(evidence_bytes).hexdigest()
    cache_inventory_sha256 = hashlib.sha256(
        core.canonical_json_bytes(cache_inventory)
    ).hexdigest()
    query_inventory_sha256 = hashlib.sha256(
        core.canonical_json_bytes(query_inventory)
    ).hexdigest()
    certificate = {
        "window_id": str(cert["window_id"]),
        "contract": "exact paired adjacent OFF q/template/width native gather",
        "comparison": "any active-epoch S/N >= single_epoch_snr_floor",
        "single_epoch_snr_floor": floor,
        "exact_same_q_template_width": True,
        "exclusion_mask_applied": False,
        "frequency_neighborhood_hz": 0.0,
        "on_retention_certificate_sha256": cert[
            "retention_certificate_sha256"
        ],
        "on_records_sha256": cert["records_sha256"],
        "proxy_grid_sha256": cert["proxy_grid_sha256"],
        "template_bank_sha256": cert["template_bank_sha256"],
        "factor_basis_sha256": cert["factor_basis_sha256"],
        "factor_basis_labels_sha256": cert[
            "factor_basis_labels_sha256"
        ],
        "scan_inventory_sha256": cert["scan_inventory_sha256"],
        "on_factor_row_selection_sha256": cert[
            "factor_row_selection_sha256"
        ],
        "off_factor_row_selection_sha256": (
            core.factor_row_selection_sha256(
                factor_basis, scan_definitions, "off"
            )
        ),
        "factor_table_sha256": cert["factor_table_sha256"],
        "cache_inventory": cache_inventory,
        "cache_inventory_sha256": cache_inventory_sha256,
        "cache_count": len(cache_inventory),
        "query_inventory_sha256": query_inventory_sha256,
        "query_count": len(query_inventory),
        "maximum_queries": maximum_queries,
        "input_record_count": len(records),
        "evidence_record_count": len(evidence),
        "maximum_records": maximum_records,
        "maximum_evidence_record_canonical_bytes": core._strict_int(
            cert["maximum_record_canonical_bytes"],
            "canonical record-byte capacity",
        ),
        "maximum_evidence_canonical_bytes": (
            maximum_evidence_canonical_bytes
        ),
        "evidence_canonical_bytes": len(evidence_bytes),
        "all_input_records_evaluated_exactly_once": True,
        "all_active_epoch_queries_evaluated_exactly_once": True,
        "truncation_permitted": False,
        "evidence_sha256": evidence_sha256,
    }
    certificate["single_adjacent_off_certificate_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(certificate)
    ).hexdigest()
    result = {
        "evidence": json.loads(evidence_bytes),
        "certificate": json.loads(core.canonical_json_bytes(certificate)),
    }
    validate_single_adjacent_off_result(
        result["evidence"], result["certificate"]
    )
    return result


def validate_single_adjacent_off_result(
    evidence: Sequence[Mapping[str, Any]],
    certificate: Mapping[str, Any],
    *,
    expected_certificate_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a persisted adjacent-OFF product and its exact query replay."""
    try:
        items = json.loads(core.canonical_json_bytes(list(evidence)))
        cert = json.loads(core.canonical_json_bytes(dict(certificate)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "single-adjacent-OFF result is not canonical finite JSON"
        ) from error
    required_certificate_fields = {
        "window_id",
        "contract",
        "comparison",
        "single_epoch_snr_floor",
        "exact_same_q_template_width",
        "exclusion_mask_applied",
        "frequency_neighborhood_hz",
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "proxy_grid_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "off_factor_row_selection_sha256",
        "factor_table_sha256",
        "cache_inventory",
        "cache_inventory_sha256",
        "cache_count",
        "query_inventory_sha256",
        "query_count",
        "maximum_queries",
        "input_record_count",
        "evidence_record_count",
        "maximum_records",
        "maximum_evidence_record_canonical_bytes",
        "maximum_evidence_canonical_bytes",
        "evidence_canonical_bytes",
        "all_input_records_evaluated_exactly_once",
        "all_active_epoch_queries_evaluated_exactly_once",
        "truncation_permitted",
        "evidence_sha256",
        "single_adjacent_off_certificate_sha256",
    }
    if frozenset(cert) != frozenset(required_certificate_fields):
        raise core.V0P6ContractError(
            "single-adjacent-OFF certificate fields do not match the schema"
        )
    observed_certificate_sha256 = core._frozen_sha256(
        cert.pop("single_adjacent_off_certificate_sha256"),
        "single-adjacent-OFF certificate identity",
    )
    calculated_certificate_sha256 = hashlib.sha256(
        core.canonical_json_bytes(cert)
    ).hexdigest()
    if observed_certificate_sha256 != calculated_certificate_sha256:
        raise core.V0P6IncompleteError(
            "single-adjacent-OFF certificate SHA-256 changed"
        )
    if expected_certificate_sha256 is not None and (
        observed_certificate_sha256
        != core._frozen_sha256(
            expected_certificate_sha256,
            "expected single-adjacent-OFF certificate identity",
        )
    ):
        raise core.V0P6ContractError(
            "single-adjacent-OFF certificate differs from its receipt"
        )
    cert["single_adjacent_off_certificate_sha256"] = (
        observed_certificate_sha256
    )
    for name in (
        "on_retention_certificate_sha256",
        "on_records_sha256",
        "proxy_grid_sha256",
        "template_bank_sha256",
        "factor_basis_sha256",
        "factor_basis_labels_sha256",
        "scan_inventory_sha256",
        "on_factor_row_selection_sha256",
        "off_factor_row_selection_sha256",
        "factor_table_sha256",
        "cache_inventory_sha256",
        "query_inventory_sha256",
        "evidence_sha256",
    ):
        core._frozen_sha256(cert[name], name.replace("_", "-"))
    floor = _finite_json_number(
        cert["single_epoch_snr_floor"], "adjacent single-epoch S/N floor"
    )
    if (
        floor != M37_SINGLE_ADJACENT_OFF_SNR_FLOOR
        or cert["contract"]
        != "exact paired adjacent OFF q/template/width native gather"
        or cert["comparison"]
        != "any active-epoch S/N >= single_epoch_snr_floor"
        or cert["exact_same_q_template_width"] is not True
        or cert["exclusion_mask_applied"] is not False
        or _finite_json_number(
            cert["frequency_neighborhood_hz"],
            "adjacent frequency neighborhood",
        )
        != 0.0
        or cert["all_input_records_evaluated_exactly_once"] is not True
        or cert["all_active_epoch_queries_evaluated_exactly_once"] is not True
        or cert["truncation_permitted"] is not False
    ):
        raise core.V0P6ContractError(
            "single-adjacent-OFF certificate semantics changed"
        )
    record_count = core._strict_int(
        cert["input_record_count"], "adjacent-OFF input-record count"
    )
    evidence_count = core._strict_int(
        cert["evidence_record_count"], "adjacent-OFF evidence-record count"
    )
    record_cap = core._strict_int(
        cert["maximum_records"], "adjacent-OFF record capacity"
    )
    query_count = core._strict_int(
        cert["query_count"], "adjacent-OFF query count"
    )
    query_cap = core._strict_int(
        cert["maximum_queries"], "adjacent-OFF query capacity"
    )
    evidence_record_byte_cap = core._strict_int(
        cert["maximum_evidence_record_canonical_bytes"],
        "adjacent-OFF evidence-record byte capacity",
    )
    evidence_byte_cap = core._strict_int(
        cert["maximum_evidence_canonical_bytes"],
        "adjacent-OFF evidence byte capacity",
    )
    if (
        record_count != evidence_count
        or evidence_count != len(items)
        or record_count > record_cap
        or query_count > query_cap
        or min(record_cap, query_cap) < 0
        or min(evidence_record_byte_cap, evidence_byte_cap) < 1
    ):
        raise core.V0P6IncompleteError(
            "single-adjacent-OFF certificate counts are inconsistent"
        )
    if not all(isinstance(item, dict) for item in items):
        raise core.V0P6ContractError(
            "single-adjacent-OFF evidence must contain objects"
        )
    items.sort(
        key=lambda item: (
            core._strict_int(item["template_index"], "template index"),
            core._strict_int(
                item["spectral_width_index"], "spectral-width index"
            ),
            tuple(
                core._strict_int(epoch, "active epoch")
                for epoch in item["active_epochs_zero_based"]
            ),
            core._strict_int(
                item["proxy_carrier_index"], "proxy-carrier index"
            ),
            str(item["record_id"]),
        )
    )
    seen_ids: set[str] = set()
    reconstructed_queries: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or frozenset(item) != (
            _ADJACENT_EVIDENCE_FIELDS
        ):
            raise core.V0P6ContractError(
                "single-adjacent-OFF evidence fields do not match the schema"
            )
        record_id = core._frozen_sha256(
            item["record_id"], "retained record identity"
        )
        if record_id in seen_ids:
            raise core.V0P6IncompleteError(
                "single-adjacent-OFF evidence repeats a record ID"
            )
        seen_ids.add(record_id)
        template_index = core._strict_int(
            item["template_index"], "template index"
        )
        width_index = core._strict_int(
            item["spectral_width_index"], "spectral-width index"
        )
        core._strict_widths((item["spectral_width_channels"],))
        proxy_index = core._strict_int(
            item["proxy_carrier_index"], "proxy-carrier index"
        )
        proxy_hz = _finite_json_number(
            item["proxy_carrier_hz"], "adjacent proxy carrier"
        )
        active_epochs = core.canonical_activity_subsets(
            (item["active_epochs_zero_based"],)
        )[0]
        if (
            not math.isfinite(proxy_hz)
            or _finite_json_number(
                item["single_epoch_snr_floor"],
                "adjacent evidence single-epoch S/N floor",
            )
            != floor
            or item["comparison"]
            != "native_gathered_snr >= single_epoch_snr_floor"
            or item["exact_same_q_template_width"] is not True
            or item["exclusion_mask_applied"] is not False
            or _finite_json_number(
                item["frequency_neighborhood_hz"],
                "adjacent evidence frequency neighborhood",
            )
            != 0.0
        ):
            raise core.V0P6ContractError(
                "single-adjacent-OFF evidence semantics changed"
            )
        measurements = item["paired_adjacent_off_measurements"]
        if not isinstance(measurements, list) or len(measurements) != len(
            active_epochs
        ):
            raise core.V0P6IncompleteError(
                "single-adjacent-OFF measurements are incomplete"
            )
        matching_epochs: list[int] = []
        observed_snrs: list[float] = []
        for expected_epoch, measurement in zip(
            active_epochs, measurements, strict=True
        ):
            if not isinstance(measurement, dict) or frozenset(measurement) != (
                _ADJACENT_MEASUREMENT_FIELDS
            ):
                raise core.V0P6ContractError(
                    "single-adjacent-OFF measurement schema changed"
                )
            epoch = core._strict_int(
                measurement["epoch_zero_based"], "adjacent-OFF epoch"
            )
            snr = _finite_json_number(
                measurement["snr"], "adjacent measurement S/N"
            )
            if (
                epoch != expected_epoch
                or not isinstance(measurement["paired_on_scan_label"], str)
                or not measurement["paired_on_scan_label"]
                or not isinstance(measurement["paired_off_scan_label"], str)
                or not measurement["paired_off_scan_label"]
                or not isinstance(
                    measurement["meets_single_epoch_floor"], bool
                )
                or measurement["meets_single_epoch_floor"] != (snr >= floor)
            ):
                raise core.V0P6ContractError(
                    "single-adjacent-OFF measurement does not reproduce"
                )
            if snr >= floor:
                matching_epochs.append(epoch)
            observed_snrs.append(snr)
            reconstructed_queries.append(
                {
                    "record_id": record_id,
                    "epoch_zero_based": epoch,
                    "paired_off_scan_label": str(
                        measurement["paired_off_scan_label"]
                    ),
                    "template_index": template_index,
                    "spectral_width_index": width_index,
                    "proxy_carrier_index": proxy_index,
                }
            )
        vetoed = bool(matching_epochs)
        if (
            item["matching_active_epochs_zero_based"] != matching_epochs
            or _finite_json_number(
                item["maximum_active_epoch_snr"],
                "adjacent maximum active-epoch S/N",
            )
            != max(observed_snrs)
            or not isinstance(item["vetoed"], bool)
            or item["vetoed"] != vetoed
            or item["recommended_member_disposition"]
            != (
                "rfi_veto_single_adjacent_off"
                if vetoed
                else "pending_receiver_alias_evaluation"
            )
            or len(core.canonical_json_bytes(item))
            > evidence_record_byte_cap
        ):
            raise core.V0P6IncompleteError(
                "single-adjacent-OFF evidence does not reproduce"
            )
    evidence_bytes = core.canonical_json_bytes(items)
    if (
        hashlib.sha256(evidence_bytes).hexdigest() != cert["evidence_sha256"]
        or len(evidence_bytes)
        != core._strict_int(
            cert["evidence_canonical_bytes"],
            "adjacent-OFF evidence byte count",
        )
        or len(evidence_bytes) > evidence_byte_cap
        or len(reconstructed_queries) != query_count
        or hashlib.sha256(
            core.canonical_json_bytes(reconstructed_queries)
        ).hexdigest()
        != cert["query_inventory_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "single-adjacent-OFF evidence or query inventory changed"
        )
    cache_inventory = cert["cache_inventory"]
    if not isinstance(cache_inventory, list) or len(cache_inventory) != (
        core._strict_int(cert["cache_count"], "adjacent-OFF cache count")
    ):
        raise core.V0P6IncompleteError(
            "single-adjacent-OFF cache inventory is incomplete"
        )
    seen_cache_keys: set[tuple[int, int, str]] = set()
    for cache_record in cache_inventory:
        if not isinstance(cache_record, dict) or frozenset(cache_record) != {
            "spectral_width_channels",
            "epoch_zero_based",
            "scan_label",
            "cache_plan_sha256",
            "cache_payload_sha256",
        }:
            raise core.V0P6ContractError(
                "single-adjacent-OFF cache inventory schema changed"
            )
        key = (
            core._strict_int(
                cache_record["spectral_width_channels"], "spectral width"
            ),
            core._strict_int(cache_record["epoch_zero_based"], "OFF epoch"),
            str(cache_record["scan_label"]),
        )
        if not key[2] or key in seen_cache_keys:
            raise core.V0P6IncompleteError(
                "single-adjacent-OFF cache inventory repeats an identity"
            )
        seen_cache_keys.add(key)
        core._frozen_sha256(
            cache_record["cache_plan_sha256"], "cache-plan identity"
        )
        core._frozen_sha256(
            cache_record["cache_payload_sha256"], "cache-payload identity"
        )
    if hashlib.sha256(
        core.canonical_json_bytes(cache_inventory)
    ).hexdigest() != cert["cache_inventory_sha256"]:
        raise core.V0P6IncompleteError(
            "single-adjacent-OFF cache inventory changed"
        )
    return cert


def evaluate_m37_single_adjacent_off_veto(
    on_records: Sequence[Mapping[str, Any]],
    on_certificate: Mapping[str, Any],
    off_caches_by_width: Mapping[int, Mapping[str, Any]],
    scan_definitions: Sequence[Mapping[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
    grid: core.ProxyCarrierGrid,
    *,
    expected_on_certificate_sha256: str | None = None,
    chunk_bins: int = 131_072,
) -> dict[str, Any]:
    """Run the non-configurable M37 single-adjacent-OFF pass."""
    cert = core.validate_retention_certificate(
        on_certificate,
        expected_certificate_sha256=expected_on_certificate_sha256,
    )
    window_id = str(cert["window_id"])
    if window_id not in core.M37_WINDOW_IDS or (
        core.proxy_carrier_grid_sha256(grid)
        != core.proxy_carrier_grid_sha256(
            core.make_m37_proxy_carrier_grid(window_id)
        )
    ):
        raise core.V0P6ContractError(
            "single-adjacent-OFF pass did not receive the M37 q grid"
        )
    core.validate_m37_factor_basis_scan_inventory(
        factor_basis, scan_definitions
    )
    bank = core.make_line_template_bank()
    core.validate_template_factor_table(
        factor_table,
        factor_basis,
        bank,
        expected_template_bank_sha256=core.M37_BANK_SHA256,
    )
    if (
        tuple(cert["spectral_widths"]) != core.M37_SPECTRAL_WIDTHS
        or tuple(tuple(item) for item in cert["activity_subsets"])
        != core.M37_ACTIVITY_SUBSETS
        or core._strict_int(cert["epoch_count"], "epoch count") != 3
        or core._strict_int(cert["expected_hypotheses"], "hypothesis count")
        != 2_976
        or core._strict_int(cert["hypotheses_replayed"], "hypothesis count")
        != 2_976
        or core._strict_int(cert["expected_score_cells"], "score-cell count")
        != 2_976 * grid.score_bin_count
        or core._strict_int(cert["score_cells_replayed"], "score-cell count")
        != 2_976 * grid.score_bin_count
        or core._strict_int(cert["maximum_records"], "retention capacity")
        != core.M37_MAXIMUM_RECORDS_PER_WINDOW
        or core._strict_int(
            cert["maximum_record_canonical_bytes"],
            "canonical record-byte capacity",
        )
        != core.M37_MAXIMUM_RECORD_CANONICAL_BYTES
        or core._strict_int(
            cert["maximum_evidence_canonical_bytes"],
            "canonical evidence-byte capacity",
        )
        != core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        or not bool(cert["require_epoch_vector_product"])
        or not bool(cert["require_mask_product"])
        or cert["minimum_active_epoch_snr"]
        != core.M37_MINIMUM_ACTIVE_EPOCH_SNR
        or cert["stack_statistic"] != "minimum_epoch"
        or cert["experiment_contract_sha256"]
        != core.M37_EXPERIMENT_CONTRACT_SHA256
        or cert["factor_basis_sha256"] != core.M37_FACTOR_BASIS_SHA256
        or cert["factor_basis_labels_sha256"]
        != core.M37_FACTOR_BASIS_LABELS_SHA256
        or cert["scan_inventory_sha256"]
        != core.M37_SCAN_INVENTORY_SHA256
        or cert["factor_row_selection_sha256"]
        != core.M37_FACTOR_ROW_SELECTION_SHA256S["on"]
        or cert["template_bank_sha256"] != core.M37_BANK_SHA256
    ):
        raise core.V0P6IncompleteError(
            "single-adjacent-OFF pass received a non-canonical M37 ledger"
        )
    return evaluate_single_adjacent_off_veto(
        on_records,
        cert,
        off_caches_by_width,
        scan_definitions,
        factor_basis,
        factor_table,
        bank,
        grid,
        single_epoch_snr_floor=M37_SINGLE_ADJACENT_OFF_SNR_FLOOR,
        maximum_records=core.M37_MAXIMUM_RECORDS_PER_WINDOW,
        maximum_queries=M37_MAXIMUM_SINGLE_ADJACENT_OFF_QUERIES,
        maximum_evidence_canonical_bytes=(
            core.M37_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        ),
        expected_on_certificate_sha256=expected_on_certificate_sha256,
        chunk_bins=chunk_bins,
    )
