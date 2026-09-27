"""Fail-closed execution envelope for the prospective HD 1461 radio search.

The envelope binds evidence that already exists, records missing qualification
without filling it by assertion, and exposes no spectral acquisition entry
point.  Its resource namespace is new and unactivated; it is not a reset or
continuation of the exhausted synthetic demonstration ledger.
"""
from dataclasses import dataclass, replace
import fcntl
import json
import os
from pathlib import Path
import tempfile
import uuid

from . import acquisition_radio as acquisition
from .detector_m43u import digest

SCHEMA = "radio-hd1461-execution-envelope-v1"
RESOURCE_SCHEMA = "radio-hd1461-prospective-resource-contract-v1"
RESOURCE_POLICY = "radio-irrevocable-role-reservations-v2"
EXPECTED_ROLES = ("calibration", "validation", "pilot")
TOTAL_LIMITS = {"max_requests": 1500, "max_bytes": 1610612736,
                "max_seconds": 3600}
SESSION_LIMITS = {"max_requests": 500, "max_bytes": 536870912,
                  "max_seconds": 1200}
REQUIRED_GATES = (
    "pointing_provenance",
    "exact_window_identities",
    "fresh_control_panel",
    "runtime_manifest",
    "prospective_resource_namespace",
    "local_durable_role_controller",
    "local_codec_receipt_path",
    "telescope_codec_receipt_handoff",
    "direct_factor_arithmetic",
    "physical_motion_bank",
    "cross_window_numeric_transfer",
    "recovery_rfi_null_evaluation",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False)


def ledger_digest(value):
    """Ledger-chain digest retains the acquisition subsystem's no-newline JSON."""
    return acquisition.digest(value)


def sha(value, label):
    if (not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)):
        raise ValueError("invalid " + label)
    return value


def validate_limits(value, expected, label):
    if value != expected:
        raise ValueError(label + " changed")


def validate_total_limits(value):
    if (set(value) != set(acquisition.LIMIT_KEYS)
            or type(value["max_requests"]) is not int
            or type(value["max_bytes"]) is not int
            or type(value["max_seconds"]) not in (int, float)
            or any(value[key] <= 0 for key in acquisition.LIMIT_KEYS)):
        raise ValueError("invalid cumulative limits")
    return dict(value)


@dataclass(frozen=True)
class ResourceContract:
    source_inventory_sha256: str
    cross_window_contract_sha256: str
    prior_closed_ledger_file_sha256: str
    identity: str

    def record(self):
        return {
            "schema": RESOURCE_SCHEMA,
            "namespace": "radio-hd1461-cadence71139-prospective-telescope-v1",
            "source_inventory_sha256": self.source_inventory_sha256,
            "cross_window_contract_sha256": self.cross_window_contract_sha256,
            "roles": list(EXPECTED_ROLES),
            "one_session_per_role": True,
            "session_limits": SESSION_LIMITS,
            "cumulative_limits": TOTAL_LIMITS,
            "reservation_policy": RESOURCE_POLICY,
            "retry_policy": "No automatic retry or reservation refund; a failed or uncertain reservation remains fully spent.",
            "scientific_attempt_limits": {
                "calibration_realizations": 3,
                "evaluation_cases": 24,
                "evaluation_runs": 1,
                "post_freeze_remedy_attempts": 0,
                "pilot_runs_before_all_gates_pass": 0,
            },
            "prior_synthetic_demonstration": {
                "ledger_file_sha256": self.prior_closed_ledger_file_sha256,
                "status": "CLOSED_EXHAUSTED_NOT_PARENT_NOT_RESET",
            },
            "status": "FROZEN_NOT_ACTIVATED",
            "reservations": 0,
            "telescope_requests": 0,
            "telescope_values_opened": False,
        }

    def validate(self):
        sha(self.source_inventory_sha256, "source inventory hash")
        sha(self.cross_window_contract_sha256, "cross-window contract hash")
        sha(self.prior_closed_ledger_file_sha256, "closed ledger file hash")
        record = self.record()
        validate_limits(record["session_limits"], SESSION_LIMITS, "session limits")
        validate_limits(record["cumulative_limits"], TOTAL_LIMITS, "cumulative limits")
        acquisition.limits(record["session_limits"])
        validate_total_limits(record["cumulative_limits"])
        if (record["roles"] != list(EXPECTED_ROLES)
                or record["prior_synthetic_demonstration"]["status"]
                != "CLOSED_EXHAUSTED_NOT_PARENT_NOT_RESET"
                or self.identity != digest(record)):
            raise ValueError("prospective resource contract changed")

    def genesis(self):
        self.validate()
        return {"policy": RESOURCE_POLICY,
                "resource_contract_sha256": self.identity,
                "source_inventory_sha256": self.source_inventory_sha256,
                "total_limits": TOTAL_LIMITS,
                "roles": list(EXPECTED_ROLES), "reservations": []}


def build_resource_contract(config):
    initial = ResourceContract(
        config["source_inventory_sha256"],
        config["cross_window_contract_sha256"],
        config["prior_closed_ledger_file_sha256"], "")
    result = replace(initial, identity=digest(initial.record()))
    result.validate()
    return result


def validate_resource_ledger(document, expected_sha256):
    if ledger_digest(document) != expected_sha256:
        raise ValueError("prospective resource ledger differs from checkpoint")
    if set(document) != {"policy", "resource_contract_sha256",
                         "source_inventory_sha256", "total_limits", "roles",
                         "reservations"}:
        raise ValueError("invalid prospective resource ledger schema")
    sha(document["resource_contract_sha256"], "resource contract hash")
    sha(document["source_inventory_sha256"], "source inventory hash")
    if (document["policy"] != RESOURCE_POLICY
            or document["roles"] != list(EXPECTED_ROLES)):
        raise ValueError("prospective resource policy or roles changed")
    validate_limits(document["total_limits"], TOTAL_LIMITS, "cumulative limits")
    validate_total_limits(document["total_limits"])
    expected = {**document, "reservations": []}
    charged = {key: 0 for key in acquisition.LIMIT_KEYS}
    ids = set()
    for index, reservation in enumerate(document["reservations"]):
        if set(reservation) != {"ordinal", "role", "session_id",
                               "prior_ledger_sha256", "reserved_limits",
                               "created_utc"}:
            raise ValueError("invalid prospective reservation schema")
        if (index >= len(EXPECTED_ROLES)
                or reservation["ordinal"] != index
                or reservation["role"] != EXPECTED_ROLES[index]
                or reservation["prior_ledger_sha256"] != ledger_digest(expected)
                or reservation["session_id"] in ids
                or str(uuid.UUID(reservation["session_id"])) != reservation["session_id"]
                or not isinstance(reservation["created_utc"], str)):
            raise ValueError("reservation role, order, parent or identity changed")
        acquisition.limits(reservation["reserved_limits"])
        if reservation["reserved_limits"] != SESSION_LIMITS:
            raise ValueError("role session limits changed")
        for key in acquisition.LIMIT_KEYS:
            charged[key] += reservation["reserved_limits"][key]
            if charged[key] > document["total_limits"][key]:
                raise ValueError("cumulative reservation budget exhausted")
        ids.add(reservation["session_id"])
        expected["reservations"].append(reservation)
    return {"charged_limits": charged,
            "remaining_limits": {key: document["total_limits"][key]-charged[key]
                                 for key in acquisition.LIMIT_KEYS},
            "sessions": len(ids)}


class LocalRoleStore:
    """Fsynced local CAS evidence store for v2 controller qualification only."""
    def __init__(self, path):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    @classmethod
    def initialize(cls, path, document):
        store = cls(path)
        store.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"revision": "0", "location": {
            "kind": "local-v2-qualification-only",
            "path": str(store.path.resolve())}, "document": document}
        validate_resource_ledger(document, ledger_digest(document))
        with store.path.open("xb", buffering=0) as stream:
            data = (canonical(payload) + "\n").encode()
            if stream.write(data) != len(data):
                raise OSError("short role-store genesis write")
            os.fsync(stream.fileno())
        store.lock_path.touch(exist_ok=True)
        _sync_directory(store.path.parent)
        return store

    def _load(self):
        value = json.loads(self.path.read_text())
        if set(value) != {"revision", "location", "document"}:
            raise ValueError("invalid local role-store record")
        validate_resource_ledger(value["document"], ledger_digest(value["document"]))
        if (not value["revision"].isdigit()
                or value["location"].get("kind") != "local-v2-qualification-only"
                or value["location"].get("path") != str(self.path.resolve())):
            raise ValueError("local role-store identity changed")
        return value

    def read(self):
        with self.lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            value = self._load()
        return acquisition.Checkpoint(value["document"], value["revision"],
                                      value["location"])

    def publish(self, expected_revision, expected_sha256, document):
        with self.lock_path.open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            current = self._load()
            if (current["revision"] != expected_revision
                    or ledger_digest(current["document"]) != expected_sha256):
                raise ValueError("local role-store compare-and-swap failed")
            validate_resource_ledger(document, ledger_digest(document))
            value = {"revision": str(int(expected_revision) + 1),
                     "location": current["location"], "document": document}
            data = (canonical(value) + "\n").encode()
            descriptor, temporary = tempfile.mkstemp(
                prefix=self.path.name + ".", dir=self.path.parent)
            try:
                with os.fdopen(descriptor, "wb", buffering=0) as stream:
                    if stream.write(data) != len(data):
                        raise OSError("short role-store update")
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
                _sync_directory(self.path.parent)
            except BaseException:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass
                raise


def _sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def reserve_role(store, *, expected_revision, expected_ledger_sha256, role,
                 session_id, created_utc):
    """Persist one ordered full-role reservation; returns no network budget."""
    before = store.read()
    if (before.revision != expected_revision
            or ledger_digest(before.document) != expected_ledger_sha256):
        raise ValueError("prospective reservation checkpoint changed")
    summary = validate_resource_ledger(before.document, expected_ledger_sha256)
    ordinal = summary["sessions"]
    if ordinal >= len(EXPECTED_ROLES) or role != EXPECTED_ROLES[ordinal]:
        raise ValueError("prospective reservation role out of order")
    if str(uuid.UUID(session_id)) != session_id or not isinstance(created_utc, str):
        raise ValueError("invalid prospective reservation identity")
    document = json.loads(canonical(before.document))
    reservation = {"ordinal": ordinal, "role": role,
        "session_id": session_id, "prior_ledger_sha256": expected_ledger_sha256,
        "reserved_limits": SESSION_LIMITS, "created_utc": created_utc}
    document["reservations"].append(reservation)
    expected_after = ledger_digest(document)
    validate_resource_ledger(document, expected_after)
    store.publish(expected_revision, expected_ledger_sha256, document)
    after = store.read()
    if (after.revision == before.revision
            or ledger_digest(after.document) != expected_after
            or after.location != before.location):
        raise ValueError("role reservation publication not confirmed; quota may be spent")
    return {"ledger_sha256": expected_after, "revision": after.revision,
            "location": after.location, "reservation": reservation,
            "network_budget_issued": False, "spectral_access_authorized": False}


@dataclass(frozen=True)
class Envelope:
    config_sha256: str
    runtime_manifest_sha256: str
    codec_evidence_sha256: str
    motion_evidence_sha256: str
    resource_contract_sha256: str
    resource_ledger_genesis_sha256: str
    evidence_json: str
    identity: str

    @property
    def evidence(self):
        return json.loads(self.evidence_json)

    def record(self):
        evidence = self.evidence
        gates = evidence["gates"]
        blockers = [name for name in REQUIRED_GATES if gates[name]["passed"] is False]
        return {
            "schema": SCHEMA,
            "config_sha256": self.config_sha256,
            "cross_window_contract_sha256": evidence["cross_window_contract_sha256"],
            "control_freeze_sha256": evidence["control_freeze_sha256"],
            "blocked_source_contract_sha256": evidence["blocked_source_contract_sha256"],
            "source_inventory_sha256": evidence["source_inventory_sha256"],
            "runtime_manifest_sha256": self.runtime_manifest_sha256,
            "codec_evidence_sha256": self.codec_evidence_sha256,
            "motion_evidence_sha256": self.motion_evidence_sha256,
            "resource_contract_sha256": self.resource_contract_sha256,
            "resource_ledger_genesis_sha256": self.resource_ledger_genesis_sha256,
            "gates": gates,
            "blockers": blockers,
            "status": "BLOCKED" if blockers else "READY_FOR_SEPARATE_AUTHORIZATION",
            "primary": "neighbor9",
            "original_preparation_contract_rewritten": False,
            "scientific_candidate_selection_authorized": False,
            "spectral_access_authorized": False,
            "telescope_values_opened": False,
            "telescope_requests": 0,
        }

    def validate(self):
        for value, label in (
                (self.config_sha256, "envelope config hash"),
                (self.runtime_manifest_sha256, "runtime manifest hash"),
                (self.codec_evidence_sha256, "codec evidence hash"),
                (self.motion_evidence_sha256, "motion evidence hash"),
                (self.resource_contract_sha256, "resource contract hash"),
                (self.resource_ledger_genesis_sha256, "resource genesis hash")):
            sha(value, label)
        evidence = self.evidence
        if set(evidence["gates"]) != set(REQUIRED_GATES):
            raise ValueError("execution gate inventory changed")
        for name, gate in evidence["gates"].items():
            if set(gate) != {"passed", "evidence", "claim"} or type(gate["passed"]) is not bool:
                raise ValueError("invalid execution gate: " + name)
        expected_passed = {
            "pointing_provenance": False,
            "exact_window_identities": True,
            "fresh_control_panel": True,
            "runtime_manifest": True,
            "prospective_resource_namespace": True,
            "local_durable_role_controller": True,
            "local_codec_receipt_path": True,
            "telescope_codec_receipt_handoff": False,
            "direct_factor_arithmetic": True,
            "physical_motion_bank": False,
            "cross_window_numeric_transfer": False,
            "recovery_rfi_null_evaluation": False,
        }
        if {k: v["passed"] for k, v in evidence["gates"].items()} != expected_passed:
            raise ValueError("qualification claims changed")
        record = self.record()
        if (record["status"] != "BLOCKED" or len(record["blockers"]) != 5
                or self.evidence_json != canonical(evidence)
                or self.identity != digest(record)):
            raise ValueError("execution envelope changed")


def build_envelope(config, *, runtime_manifest, codec_evidence,
                   motion_evidence, resource_contract, resource_genesis):
    resource_contract.validate()
    validate_resource_ledger(resource_genesis, ledger_digest(resource_genesis))
    evidence = {
        "cross_window_contract_sha256": config["cross_window_contract_sha256"],
        "control_freeze_sha256": config["control_freeze_sha256"],
        "blocked_source_contract_sha256": config["blocked_source_contract_sha256"],
        "source_inventory_sha256": config["source_inventory_sha256"],
        "gates": config["gates"],
    }
    initial = Envelope(
        config["config_sha256"], digest(runtime_manifest), digest(codec_evidence),
        digest(motion_evidence), resource_contract.identity,
        ledger_digest(resource_genesis), canonical(evidence), "")
    result = replace(initial, identity=digest(initial.record()))
    result.validate()
    return result
