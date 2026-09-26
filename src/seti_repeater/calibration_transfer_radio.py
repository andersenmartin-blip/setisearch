"""Identity-only contract for prospective disjoint-window radio calibration.

This module never reads spectral values and deliberately exposes no operation
that can authorize a cross-window threshold transfer.  It freezes the proposed
payload identities and makes the difference between an exact-context
certificate and a future, independently qualified transfer certificate
machine-checkable.
"""
from dataclasses import dataclass, replace
import json
import math

from .detector_m43u import digest

SCHEMA = "radio-cross-window-calibration-contract-v1"
WINDOW_SCHEMA = "radio-prospective-window-identity-v1"
REQUEST_SCHEMA = "radio-cross-window-transfer-request-v1"
ROLES = ("calibration", "validation", "pilot")
BLOCKS = ((0, 4096), (4096, 8192), (8192, 12288), (12288, 16384))


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def _sha(value, label):
    if not isinstance(value, str) or len(value) != 64 or any(
            c not in "0123456789abcdef" for c in value):
        raise ValueError(f"invalid {label}")
    return value


@dataclass(frozen=True)
class WindowIdentity:
    role: str
    name: str
    archive_chunk_index: int
    archive_interval: tuple
    native_channel_count: int
    native_frequency_low_hz: float
    native_frequency_high_hz: float
    carrier_center_hz: float
    normalization_blocks: tuple
    payload_keys_json: str
    payload_keys_sha256: str
    identity: str

    @property
    def payload_keys(self):
        return json.loads(self.payload_keys_json)

    def record(self):
        return {
            "schema": WINDOW_SCHEMA,
            "role": self.role,
            "name": self.name,
            "archive_chunk_index": self.archive_chunk_index,
            "archive_interval": list(self.archive_interval),
            "native_channel_count": self.native_channel_count,
            "native_frequency_low_hz": self.native_frequency_low_hz,
            "native_frequency_high_hz": self.native_frequency_high_hz,
            "proposed_first_on_midpoint_carrier_center_hz": self.carrier_center_hz,
            "normalization_blocks_native_channels": [list(x) for x in self.normalization_blocks],
            "payload_keys_sha256": self.payload_keys_sha256,
            "payload_keys": self.payload_keys,
            "spectral_values_included": False,
        }

    def validate(self):
        if self.role not in ROLES or not self.name:
            raise ValueError("invalid prospective window role or name")
        if (not isinstance(self.archive_chunk_index, int)
                or self.native_channel_count != 16384
                or tuple(tuple(x) for x in self.normalization_blocks) != BLOCKS):
            raise ValueError("prospective window geometry changed")
        if (len(self.archive_interval) != 2
                or self.archive_interval[1] - self.archive_interval[0] != 16384):
            raise ValueError("prospective archive interval changed")
        frequencies = (self.native_frequency_low_hz, self.native_frequency_high_hz,
                       self.carrier_center_hz)
        if (not all(math.isfinite(x) for x in frequencies)
                or not frequencies[0] < frequencies[2] < frequencies[1]):
            raise ValueError("invalid prospective frequency geometry")
        payloads = self.payload_keys
        if len(payloads) != 6:
            raise ValueError("exact six-source prospective inventory required")
        for payload in payloads:
            coordinates = payload.get("chunk_coordinates_time_feed_frequency")
            if (not isinstance(payload.get("source_url"), str)
                    or coordinates != [[i, 0, self.archive_chunk_index] for i in range(16)]):
                raise ValueError("prospective decoded payload identity changed")
        if len({item["source_url"] for item in payloads}) != 6:
            raise ValueError("prospective source URL inventory is not unique")
        if (self.payload_keys_json != _canonical(payloads)
                or self.payload_keys_sha256 != digest(payloads)
                or self.identity != digest(self.record())):
            raise ValueError("prospective window identity changed")


def build_window(record):
    payload_json = _canonical(record["payload_keys"])
    initial = WindowIdentity(
        role=str(record["role"]), name=str(record["name"]),
        archive_chunk_index=int(record["archive_chunk_index"]),
        archive_interval=tuple(record["archive_interval"]),
        native_channel_count=int(record["native_channel_count"]),
        native_frequency_low_hz=float(record["native_frequency_low_hz"]),
        native_frequency_high_hz=float(record["native_frequency_high_hz"]),
        carrier_center_hz=float(record["proposed_first_on_midpoint_carrier_center_hz"]),
        normalization_blocks=BLOCKS, payload_keys_json=payload_json,
        payload_keys_sha256=digest(json.loads(payload_json)), identity="")
    result = replace(initial, identity=digest(initial.record()))
    result.validate()
    return result


@dataclass(frozen=True)
class Contract:
    prospective_design_sha256: str
    blocked_source_contract_sha256: str
    grid_sha256: str
    windows_json: str
    required_evidence_json: str
    identity: str

    @property
    def windows(self):
        return tuple(WindowIdentity(**item) for item in json.loads(self.windows_json))

    @property
    def required_evidence(self):
        return json.loads(self.required_evidence_json)

    def record(self):
        windows = self.windows
        return {
            "schema": SCHEMA,
            "prospective_design_sha256": self.prospective_design_sha256,
            "blocked_source_contract_sha256": self.blocked_source_contract_sha256,
            "grid_sha256": self.grid_sha256,
            "windows": {item.role: item.identity for item in windows},
            "window_payload_keys": {item.role: item.payload_keys_sha256 for item in windows},
            "normalization_blocks_native_channels": [list(x) for x in BLOCKS],
            "allowed_sequence": ["calibration", "validation", "pilot"],
            "exact_context_certificate_reuse_across_windows": "FORBIDDEN",
            "calibration_to_pilot_shortcut": "FORBIDDEN",
            "required_evidence": self.required_evidence,
            "status": "IDENTITIES_FROZEN_TRANSFER_NOT_QUALIFIED",
            "primary": "neighbor9",
            "roles_are_independent_observations": False,
            "scientific_candidate_selection_authorized": False,
            "spectral_access_authorized": False,
            "telescope_values_opened": False,
        }

    def validate(self):
        _sha(self.prospective_design_sha256, "prospective design hash")
        _sha(self.blocked_source_contract_sha256, "blocked source contract hash")
        _sha(self.grid_sha256, "grid hash")
        windows = self.windows
        if tuple(item.role for item in windows) != ROLES:
            raise ValueError("prospective roles or ordering changed")
        for item in windows:
            item.validate()
        if len({item.archive_chunk_index for item in windows}) != 3:
            raise ValueError("window archive chunks overlap")
        intervals = [set(range(*item.archive_interval)) for item in windows]
        if any(intervals[i] & intervals[j] for i in range(3) for j in range(i)):
            raise ValueError("window archive intervals overlap")
        payload_ids = []
        for item in windows:
            payload_ids += [(p["source_url"], tuple(map(tuple,
                p["chunk_coordinates_time_feed_frequency"]))) for p in item.payload_keys]
        if len(set(payload_ids)) != 18:
            raise ValueError("decoded payload identities cross window boundaries")
        evidence = self.required_evidence
        if set(evidence) != {
                "pointing_provenance_ready_contract_sha256",
                "qualified_motion_bank_sha256", "codec_receipt_contract_sha256",
                "runtime_manifest_sha256", "fresh_control_panel_sha256",
                "cumulative_resource_ledger_sha256"}:
            raise ValueError("required transfer evidence slots changed")
        if any(value is not None for value in evidence.values()):
            raise ValueError("unqualified evidence must not be fabricated into this freeze")
        if (self.windows_json != _canonical([item.__dict__ for item in windows])
                or self.required_evidence_json != _canonical(evidence)
                or self.identity != digest(self.record())):
            raise ValueError("cross-window calibration contract changed")


def build_contract(design):
    if (design.get("artifact_type") != "radio-prospective-design-draft-v1"
            or design.get("status") != "NOT_FROZEN_NOT_EXECUTABLE"
            or design.get("spectral_access_authorized") is not False
            or design.get("calibration_transfer_qualified") is not False
            or design.get("calibration_transfer_contract") is not None):
        raise ValueError("prospective design is not the closed pre-access draft")
    windows = tuple(build_window(item) for item in design["windows"])
    grid = dict(design["proposed_grid"])
    evidence = {
        "pointing_provenance_ready_contract_sha256": None,
        "qualified_motion_bank_sha256": None,
        "codec_receipt_contract_sha256": None,
        "runtime_manifest_sha256": None,
        "fresh_control_panel_sha256": None,
        "cumulative_resource_ledger_sha256": None,
    }
    initial = Contract(
        prospective_design_sha256=digest(design),
        blocked_source_contract_sha256=design["source_contract_sha256"],
        grid_sha256=digest(grid),
        windows_json=_canonical([item.__dict__ for item in windows]),
        required_evidence_json=_canonical(evidence), identity="")
    result = replace(initial, identity=digest(initial.record()))
    result.validate()
    return result


@dataclass(frozen=True)
class ExactContextCertificate:
    window_sha256: str
    context_sha256: str
    receipt_sha256: str
    source_domain: str

    def validate_for_exact_context(self, window_sha256, context_sha256):
        _sha(self.window_sha256, "certificate window hash")
        _sha(self.context_sha256, "certificate context hash")
        _sha(self.receipt_sha256, "certificate receipt hash")
        if self.source_domain not in ("synthetic", "telescope"):
            raise ValueError("invalid calibration source domain")
        if self.window_sha256 != window_sha256 or self.context_sha256 != context_sha256:
            raise ValueError("exact-context calibration certificate reuse refused")


def prepare_transfer_request(contract, certificate, *, source_role,
                             destination_role, source_context_sha256,
                             destination_context_sha256):
    """Bind a future request, without granting threshold-transfer authority."""
    contract.validate()
    by_role = {item.role: item for item in contract.windows}
    if source_role != "calibration" or destination_role != "validation":
        raise ValueError("only calibration-to-validation may be prepared first")
    if source_context_sha256 == destination_context_sha256:
        raise ValueError("source and destination contexts must be distinct")
    certificate.validate_for_exact_context(by_role[source_role].identity,
                                           source_context_sha256)
    blockers = [key for key, value in contract.required_evidence.items() if value is None]
    blockers += ["independent_observing_realizations_unavailable",
                 "cross_window_numeric_transfer_not_qualified"]
    record = {
        "schema": REQUEST_SCHEMA,
        "contract_sha256": contract.identity,
        "source_role": source_role,
        "source_window_sha256": by_role[source_role].identity,
        "source_context_sha256": source_context_sha256,
        "source_certificate_receipt_sha256": certificate.receipt_sha256,
        "source_domain": certificate.source_domain,
        "destination_role": destination_role,
        "destination_window_sha256": by_role[destination_role].identity,
        "destination_context_sha256": destination_context_sha256,
        "blockers": blockers,
        "threshold_transfer_authorized": False,
        "scientific_evaluation_authorized": False,
        "spectral_access_authorized": False,
    }
    record["request_sha256"] = digest(record)
    return record
