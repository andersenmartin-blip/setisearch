"""Post-contact capacity-only amendment for the M37 detector-v0.6 run.

The original v0.6 constants remain frozen in :mod:`search_v0p6`.  This module
admits exactly one separately published v0.6.1 profile whose ancestry is the
complete Run-004 capacity census.  It changes resource envelopes only; the
threshold, search grid, template bank, score and veto semantics are unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import search_v0p6 as core


M37_V0P6P1_PROTOCOL_LABEL = (
    "detector-v0.6.1-post-contact-capacity-amendment"
)
M37_V0P6P1_AMENDMENT_FILE_SHA256 = (
    "50a1e14427afe0949aeb1c7c028b8d1ed88755f7c94a78e8da46249131620bab"
)
M37_V0P6P1_INVALID_RUN_JOURNAL_HEAD_SHA256 = (
    "d13d03a5d8430b5c48dd7c9de24158659ce810bfcc44ffbf13f7cac29f3b8e61"
)
M37_V0P6P1_CAPACITY_FAILURE_EVIDENCE_SHA256 = (
    "e7a21d172939a54933b762a6afa96670365d6e6eeb57a7a45a98777622265ded"
)
M37_V0P6P1_CAPACITY_CENSUS_MANIFEST_SHA256 = (
    "a0c847907278b1317d8fb98f3797896c2d6700c006551d662cb3679f31ca0199"
)
M37_V0P6P1_CAPACITY_CENSUS_MANIFEST_FILE_SHA256 = (
    "fd30e71981b20424f34ad0b404d3af91127fe88c8e97fd1c38ede031735b5923"
)

M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW = 50_000
M37_V0P6P1_MAXIMUM_CLUSTERS_PER_WINDOW = 50_000
M37_V0P6P1_MAXIMUM_ALIAS_BUCKET_ENTRIES = 150_000
M37_V0P6P1_MAXIMUM_ADJACENT_OR_RECEIVER_QUERIES = 150_000
M37_V0P6P1_MAXIMUM_OFF_BUCKET_ENTRIES = 150_000
M37_V0P6P1_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS = 125_000_000
M37_V0P6P1_MAXIMUM_ALIAS_DISTINCT_CANDIDATE_VISITS = 125_000_000
M37_V0P6P1_MAXIMUM_OFF_EXACT_CANDIDATE_VISITS = 125_000_000
M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES = 480_000_000
M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES_TOTAL = 2_400_000_000
M37_V0P6P1_MAXIMUM_SINGLE_COMPRESSED_OUTPUT_FILE_BYTES = 475_000_000
M37_V0P6P1_DERIVED_RETENTION_EVIDENCE_BYTES = 417_647_424


@dataclass(frozen=True)
class M37V0P6P1CapacityProfile:
    amendment_file_sha256: str
    maximum_records_per_window: int
    maximum_clusters_per_window: int
    maximum_alias_bucket_entries_per_window: int
    maximum_adjacent_or_receiver_queries_per_window: int
    maximum_off_bucket_entries_per_window: int
    maximum_alias_identity_track_comparisons_per_window: int
    maximum_alias_distinct_candidate_visits_per_window: int
    maximum_off_exact_candidate_visits_per_window: int
    maximum_record_canonical_bytes: int
    maximum_retention_evidence_canonical_bytes_per_window: int
    maximum_retention_evidence_canonical_bytes_total: int
    maximum_single_compressed_output_file_bytes: int
    maximum_live_ndarray_bytes: int

    def as_record(self) -> dict[str, Any]:
        return {
            "artifact_type": (
                "m37-detector-v0p6p1-capacity-profile-receipt-v1"
            ),
            "protocol_label": M37_V0P6P1_PROTOCOL_LABEL,
            "amendment_file_sha256": self.amendment_file_sha256,
            "invalid_run_journal_head_sha256": (
                M37_V0P6P1_INVALID_RUN_JOURNAL_HEAD_SHA256
            ),
            "capacity_failure_evidence_sha256": (
                M37_V0P6P1_CAPACITY_FAILURE_EVIDENCE_SHA256
            ),
            "capacity_census_manifest_sha256": (
                M37_V0P6P1_CAPACITY_CENSUS_MANIFEST_SHA256
            ),
            "capacity_census_manifest_file_sha256": (
                M37_V0P6P1_CAPACITY_CENSUS_MANIFEST_FILE_SHA256
            ),
            "capacities": {
                "maximum_records_per_window": self.maximum_records_per_window,
                "maximum_clusters_per_window": self.maximum_clusters_per_window,
                "maximum_alias_bucket_entries_per_window": (
                    self.maximum_alias_bucket_entries_per_window
                ),
                "maximum_adjacent_or_receiver_queries_per_window": (
                    self.maximum_adjacent_or_receiver_queries_per_window
                ),
                "maximum_off_bucket_entries_per_window": (
                    self.maximum_off_bucket_entries_per_window
                ),
                "maximum_alias_identity_track_comparisons_per_window": (
                    self.maximum_alias_identity_track_comparisons_per_window
                ),
                "maximum_alias_distinct_candidate_visits_per_window": (
                    self.maximum_alias_distinct_candidate_visits_per_window
                ),
                "maximum_off_exact_candidate_visits_per_window": (
                    self.maximum_off_exact_candidate_visits_per_window
                ),
                "maximum_record_canonical_bytes": (
                    self.maximum_record_canonical_bytes
                ),
                "maximum_retention_evidence_canonical_bytes_per_window": (
                    self.maximum_retention_evidence_canonical_bytes_per_window
                ),
                "maximum_retention_evidence_canonical_bytes_total": (
                    self.maximum_retention_evidence_canonical_bytes_total
                ),
                "maximum_single_compressed_output_file_bytes": (
                    self.maximum_single_compressed_output_file_bytes
                ),
                "maximum_live_ndarray_bytes": self.maximum_live_ndarray_bytes,
            },
        }


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def _expected_capacities() -> dict[str, int]:
    return {
        "maximum_records_per_window": M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW,
        "maximum_clusters_per_window": M37_V0P6P1_MAXIMUM_CLUSTERS_PER_WINDOW,
        "maximum_alias_bucket_entries_per_window": (
            M37_V0P6P1_MAXIMUM_ALIAS_BUCKET_ENTRIES
        ),
        "maximum_adjacent_or_receiver_queries_per_window": (
            M37_V0P6P1_MAXIMUM_ADJACENT_OR_RECEIVER_QUERIES
        ),
        "maximum_off_bucket_entries_per_window": (
            M37_V0P6P1_MAXIMUM_OFF_BUCKET_ENTRIES
        ),
        "maximum_alias_identity_track_comparisons_per_window": (
            M37_V0P6P1_MAXIMUM_ALIAS_IDENTITY_TRACK_COMPARISONS
        ),
        "maximum_alias_distinct_candidate_visits_per_window": (
            M37_V0P6P1_MAXIMUM_ALIAS_DISTINCT_CANDIDATE_VISITS
        ),
        "maximum_off_exact_candidate_visits_per_window": (
            M37_V0P6P1_MAXIMUM_OFF_EXACT_CANDIDATE_VISITS
        ),
        "maximum_record_canonical_bytes": core.M37_MAXIMUM_RECORD_CANONICAL_BYTES,
        "maximum_retention_evidence_canonical_bytes_per_window": (
            M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        ),
        "maximum_retention_evidence_canonical_bytes_total": (
            M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES_TOTAL
        ),
        "maximum_single_compressed_output_file_bytes": (
            M37_V0P6P1_MAXIMUM_SINGLE_COMPRESSED_OUTPUT_FILE_BYTES
        ),
        "maximum_live_ndarray_bytes": core.M37_LIVE_NDARRAY_CAP_BYTES,
    }


def open_m37_v0p6p1_capacity_amendment(
    path: Path,
) -> M37V0P6P1CapacityProfile:
    """Open the sole frozen amendment and reject any resealed substitution."""
    if _sha256_file(path) != M37_V0P6P1_AMENDMENT_FILE_SHA256:
        raise core.V0P6ContractError("M37 v0.6.1 capacity amendment changed")
    try:
        value = json.loads(path.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise core.V0P6ContractError(
            "M37 v0.6.1 capacity amendment is invalid JSON"
        ) from exc
    capacities = value.get("capacities") if isinstance(value, dict) else None
    if (
        value.get("schema_version") != 1
        or value.get("artifact_type")
        != "m37-detector-v0p6p1-post-contact-capacity-amendment-v1"
        or value.get("protocol_label") != M37_V0P6P1_PROTOCOL_LABEL
        or value.get("basis")
        != {
            "invalid_run_id": "m37-v0p6-primary-004",
            "invalid_run_outcome": "M37_INVALID_NO_CONCLUSION",
            "invalid_run_reason_code": "retention-capacity-overflow",
            "invalid_run_journal_head_sha256": (
                M37_V0P6P1_INVALID_RUN_JOURNAL_HEAD_SHA256
            ),
            "capacity_failure_evidence_sha256": (
                M37_V0P6P1_CAPACITY_FAILURE_EVIDENCE_SHA256
            ),
            "capacity_census_diagnostic_id": (
                "m37-v0p6-capacity-census-001"
            ),
            "capacity_census_manifest_sha256": (
                M37_V0P6P1_CAPACITY_CENSUS_MANIFEST_SHA256
            ),
            "capacity_census_manifest_file_sha256": (
                M37_V0P6P1_CAPACITY_CENSUS_MANIFEST_FILE_SHA256
            ),
            "complete_maximum_records_in_one_window_kind": 41_640,
        }
        or capacities != _expected_capacities()
        or value.get("derived_checks")
        != {
            "observed_headroom_records": 8_360,
            "derived_worst_case_retention_evidence_bytes_per_window": (
                M37_V0P6P1_DERIVED_RETENTION_EVIDENCE_BYTES
            ),
            "record_capacity_scale_from_v0p6": 5,
            "pairwise_capacity_scale_from_v0p6": 25,
        }
        or value.get("unchanged_scientific_contract")
        != {
            "threshold": True,
            "proxy_carrier_grid": True,
            "template_bank": True,
            "spectral_widths": True,
            "activity_subsets": True,
            "minimum_active_epoch_snr": True,
            "stack_statistic": True,
            "off_and_receiver_vetoes": True,
            "global_rank_significance": True,
        }
        or value.get("rules")
        != {
            "new_run_required": True,
            "reuse_invalid_run_journal_permitted": False,
            "truncation_permitted": False,
            "threshold_adaptation_permitted": False,
            "mid_run_capacity_adaptation_permitted": False,
            "capacity_failure_outcome": "M37_INVALID_NO_CONCLUSION",
        }
        or value.get("claim_boundary")
        != {
            "post_contact": True,
            "capacity_only": True,
            "scientific_conclusion": False,
        }
    ):
        raise core.V0P6ContractError(
            "M37 v0.6.1 capacity amendment contract changed"
        )
    return M37V0P6P1CapacityProfile(
        amendment_file_sha256=M37_V0P6P1_AMENDMENT_FILE_SHA256,
        **capacities,
    )


def validate_m37_v0p6p1_capacity_profile_record(
    value: Mapping[str, Any],
) -> M37V0P6P1CapacityProfile:
    """Validate a persisted receipt without accepting caller-selected caps."""
    detached = json.loads(core.canonical_json_bytes(dict(value)))
    profile = M37V0P6P1CapacityProfile(
        amendment_file_sha256=M37_V0P6P1_AMENDMENT_FILE_SHA256,
        **_expected_capacities(),
    )
    if detached != profile.as_record():
        raise core.V0P6ContractError(
            "M37 v0.6.1 capacity profile receipt changed"
        )
    return profile


def make_m37_v0p6p1_retention_ledger(
    profile: M37V0P6P1CapacityProfile,
    window_id: str,
    scan_kind: str,
    threshold_certificate: core.ThresholdCertificate,
    template_bank: Sequence[dict[str, Any]],
    factor_basis: core.FactorBasis,
    factor_table: core.TemplateFactorTable,
) -> core.ExhaustiveRetentionLedger:
    """Create the unchanged M37 ledger under the amended resource envelope."""
    if profile.as_record() != M37V0P6P1CapacityProfile(
        amendment_file_sha256=M37_V0P6P1_AMENDMENT_FILE_SHA256,
        **_expected_capacities(),
    ).as_record():
        raise core.V0P6ContractError("M37 v0.6.1 capacity profile changed")
    return core._make_m37_retention_ledger_with_capacities(
        window_id,
        scan_kind,
        threshold_certificate,
        template_bank,
        factor_basis,
        factor_table,
        maximum_records=profile.maximum_records_per_window,
        maximum_evidence_canonical_bytes=(
            profile.maximum_retention_evidence_canonical_bytes_per_window
        ),
    )
