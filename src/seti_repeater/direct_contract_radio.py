"""Versioned downstream identities for a literal DirectFactors bank.

This is deliberately not a FactorBasis and never constructs one.  The v0.6
retention kernels retain historical field names for their identity slots; the
record below declares exactly how those slots are populated by this contract.
"""
from dataclasses import dataclass
import json
import numpy as np

from . import factors_radio as direct
from . import search_v0p6 as core
from .detector_m43u import digest

SCHEMA = "radio-direct-downstream-factor-contract-v1"


def _bank(bank):
    inputs = json.loads(bank.inputs_json)
    records = []
    for item in inputs["templates"]:
        i = core._strict_int(item["template_index"], "direct template index")
        scale = float(item["projected_scale"])
        phase = float(item["phase_cycles"])
        records.append({
            "template_index": i,
            "line_index": i,
            "line_coefficient": scale,
            "projected_scale": scale,
            "phase_cycles": phase,
            "direct_factor_bank_sha256": bank.identity,
            "schema": "radio-direct-template-v1",
            "line_fields_are_retention_compatibility_metadata": True,
        })
    return json.loads(core.canonical_json_bytes(records))


def labels_sha256(bank):
    direct.validate(bank)
    return digest({
        "schema": "radio-direct-midpoint-labels-v1",
        "direct_factor_bank_sha256": bank.identity,
        "scan_labels": list(direct.LABELS),
        "integrations_per_scan": 16,
        "factor_sample": "midpoint",
    })


def row_selection_sha256(bank, scans, kind):
    direct.validate(bank)
    indices = core.m37_scan_indices_for_kind(scans, kind)
    return digest({
        "schema": "radio-direct-row-selection-v1",
        "direct_factor_bank_sha256": bank.identity,
        "labels_sha256": labels_sha256(bank),
        "scan_inventory_sha256": core.scan_inventory_sha256(scans),
        "scan_kind": str(kind).lower(),
        "scan_indices": list(indices),
        "factor_sample": "midpoint",
    })


def for_scan(bank, label):
    return direct.for_scan(bank, str(label), sample="midpoint")


def matrix_for_kind(bank, scans, kind):
    indices = core.m37_scan_indices_for_kind(scans, kind)
    pieces = [for_scan(bank, scans[i]["label"]) for i in indices]
    payload = np.ascontiguousarray(np.concatenate(pieces, axis=1), dtype="<f8").tobytes()
    return np.frombuffer(payload, dtype="<f8").reshape(bank.template_count, 48)


@dataclass(frozen=True)
class DirectFactorContract:
    factors: direct.DirectFactors
    scans_json: str
    bank_json: str
    labels_sha256: str
    factor_table_sha256: str
    identity: str

    @property
    def scans(self):
        return json.loads(self.scans_json)

    @property
    def bank(self):
        return json.loads(self.bank_json)

    def record(self):
        return {
            "schema": SCHEMA,
            "direct_factor_bank_sha256": self.factors.identity,
            "factor_provider_kind": "literal-midpoint-table-not-factor-basis",
            "labels_sha256": self.labels_sha256,
            "factor_table_sha256": self.factor_table_sha256,
            "template_bank_sha256": core.template_bank_sha256(self.bank),
            "scan_inventory_sha256": core.scan_inventory_sha256(self.scans),
            "on_row_selection_sha256": row_selection_sha256(self.factors, self.scans, "on"),
            "off_row_selection_sha256": row_selection_sha256(self.factors, self.scans, "off"),
            "legacy_certificate_slot_mapping": {
                "factor_basis_sha256": "direct_factor_bank_sha256",
                "factor_basis_labels_sha256": "direct midpoint labels_sha256",
            },
            "old_factor_basis_constructed": False,
        }

    def validate(self):
        direct.validate(self.factors)
        scans = self.scans
        core.m37_scan_indices_for_kind(scans, "on")
        if tuple(s["label"] for s in scans) != direct.LABELS:
            raise ValueError("direct scan labels differ from the factor bank")
        if self.bank != _bank(self.factors):
            raise ValueError("direct downstream template catalogue changed")
        matrix = np.ascontiguousarray(self.factors.factors[:, :, 1], dtype="<f8")
        if (self.labels_sha256 != labels_sha256(self.factors)
                or self.factor_table_sha256 != core.factor_table_sha256(matrix)
                or self.identity != digest(self.record())):
            raise ValueError("direct downstream factor contract changed")

    def for_scan(self, label):
        self.validate()
        return for_scan(self.factors, label)

    def matrix_for_kind(self, kind):
        self.validate()
        return matrix_for_kind(self.factors, self.scans, kind)

    def row_selection_sha256(self, kind):
        self.validate()
        return row_selection_sha256(self.factors, self.scans, kind)


def build(factors, scans):
    direct.validate(factors)
    scans_json = core.canonical_json_bytes(list(scans)).decode()
    normalized = json.loads(scans_json)
    core.m37_scan_indices_for_kind(normalized, "on")
    if tuple(s["label"] for s in normalized) != direct.LABELS:
        raise ValueError("direct factor bank requires its exact six scan labels")
    bank_json = core.canonical_json_bytes(_bank(factors)).decode()
    table_sha = core.factor_table_sha256(factors.factors[:, :, 1])
    initial = DirectFactorContract(factors, scans_json, bank_json,
                                   labels_sha256(factors), table_sha, "")
    result = DirectFactorContract(**{**initial.__dict__, "identity": digest(initial.record())})
    result.validate()
    return result
