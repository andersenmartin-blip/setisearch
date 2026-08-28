"""Restartable, non-spectral bootstrap for the M37 detector-v0.6 runner.

This module closes only the metadata/bootstrap portion of the operational
runner.  It creates a factor bundle and an initialized hash-chained journal in
one run directory.  It cannot advance the journal to spectral authorization
and imports no telescope extractor.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
from typing import Any, Mapping

from . import factor_bundle_v0p6 as factor_io
from . import run_state_v0p6 as state
from . import search_v0p6 as core


M37_BOOTSTRAP_ARTIFACT = "m37-detector-v0p6-non-spectral-bootstrap-v1"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(value: Any, label: str) -> str:
    return core._frozen_sha256(value, label)


def _detached_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise core.V0P6ContractError(f"{label} must be a mapping")
    try:
        result = json.loads(core.canonical_json_bytes(dict(value)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            f"{label} is not canonical finite JSON"
        ) from error
    if not isinstance(result, dict) or not result:
        raise core.V0P6ContractError(f"{label} must be a non-empty mapping")
    return result


def _write_read_only(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short write while publishing M37 bootstrap")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@dataclass(frozen=True)
class M37BootstrapReceipt:
    run_directory: str
    run_id: str
    bootstrap_sha256: str
    initialization_contract_sha256: str
    factor_bundle_manifest_sha256: str
    factor_bundle_file_sha256: str
    factor_table_sha256: str
    analysis_contract_sha256: str
    journal_head_sha256: str
    journal_file_sha256: str
    environment_sha256: str
    source_metadata_sha256: str
    spectral_access_authorized: bool
    spectral_dataset_values_read: bool


@dataclass(frozen=True)
class M37Bootstrap:
    factor_bundle: factor_io.FactorBundle
    journal: state.RunJournalReceipt
    receipt: M37BootstrapReceipt


def _bootstrap_record(
    *,
    run_id: str,
    initialization_contract_sha256: str,
    factor_receipt: factor_io.FactorBundleReceipt,
    journal_receipt: state.RunJournalReceipt,
) -> dict[str, Any]:
    record = {
        "schema_version": 1,
        "artifact_type": M37_BOOTSTRAP_ARTIFACT,
        "run_id": run_id,
        "initialization_contract_sha256": initialization_contract_sha256,
        "factor_bundle_path": "factor_bundle.v0p6",
        "factor_bundle_manifest_sha256": factor_receipt.manifest_sha256,
        "factor_bundle_file_sha256": factor_receipt.file_sha256,
        "factor_table_sha256": factor_receipt.factor_table_sha256,
        "analysis_contract_sha256": factor_receipt.analysis_contract_sha256,
        "environment_sha256": factor_receipt.environment_sha256,
        "source_metadata_sha256": factor_receipt.source_metadata_sha256,
        "journal_path": "run.journal.jsonl",
        "journal_event_count": journal_receipt.event_count,
        "journal_stage": journal_receipt.stage,
        "journal_head_sha256": journal_receipt.head_sha256,
        "journal_file_sha256": journal_receipt.file_sha256,
        "spectral_access_authorized": False,
        "spectral_dataset_values_read": False,
    }
    record["bootstrap_sha256"] = _sha256_bytes(core.canonical_json_bytes(record))
    return record


def _validate_bootstrap_record(record: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "artifact_type",
        "run_id",
        "initialization_contract_sha256",
        "factor_bundle_path",
        "factor_bundle_manifest_sha256",
        "factor_bundle_file_sha256",
        "factor_table_sha256",
        "analysis_contract_sha256",
        "environment_sha256",
        "source_metadata_sha256",
        "journal_path",
        "journal_event_count",
        "journal_stage",
        "journal_head_sha256",
        "journal_file_sha256",
        "spectral_access_authorized",
        "spectral_dataset_values_read",
        "bootstrap_sha256",
    }
    if not isinstance(record, Mapping) or set(record) != required:
        raise core.V0P6ContractError("M37 bootstrap receipt schema changed")
    detached = json.loads(core.canonical_json_bytes(dict(record)))
    observed = _sha256(detached.pop("bootstrap_sha256"), "bootstrap identity")
    expected = _sha256_bytes(core.canonical_json_bytes(detached))
    if observed != expected:
        raise core.V0P6IncompleteError("M37 bootstrap receipt identity changed")
    detached["bootstrap_sha256"] = observed
    if (
        detached["schema_version"] != 1
        or detached["artifact_type"] != M37_BOOTSTRAP_ARTIFACT
        or detached["factor_bundle_path"] != "factor_bundle.v0p6"
        or detached["journal_path"] != "run.journal.jsonl"
        or detached["journal_event_count"] != 2
        or detached["journal_stage"] != "factor_bundle_ready"
        or detached["spectral_access_authorized"] is not False
        or detached["spectral_dataset_values_read"] is not False
    ):
        raise core.V0P6IncompleteError("M37 bootstrap boundary changed")
    for key in (
        "initialization_contract_sha256",
        "factor_bundle_manifest_sha256",
        "factor_bundle_file_sha256",
        "factor_table_sha256",
        "analysis_contract_sha256",
        "environment_sha256",
        "source_metadata_sha256",
        "journal_head_sha256",
        "journal_file_sha256",
    ):
        _sha256(detached[key], key.replace("_", " "))
    if not isinstance(detached["run_id"], str) or not detached["run_id"]:
        raise core.V0P6ContractError("M37 bootstrap run ID is invalid")
    return detached


def bootstrap_m37_run(
    run_directory: str | os.PathLike[str],
    *,
    run_id: str,
    upstream_metadata: Mapping[str, Any],
    bank_preflight_result: Mapping[str, Any],
    environment: Mapping[str, Any],
    source_hashes: Mapping[str, Any],
) -> M37BootstrapReceipt:
    """Atomically create a metadata-only M37 run bootstrap directory."""
    destination = Path(run_directory)
    parent = destination.parent
    if not parent.is_dir():
        raise core.V0P6ContractError("M37 bootstrap parent directory is absent")
    if destination.exists():
        raise FileExistsError(destination)
    upstream = _detached_mapping(upstream_metadata, "M37 upstream metadata")
    bank_result = _detached_mapping(bank_preflight_result, "M37 bank preflight")
    environment_record = _detached_mapping(environment, "M37 execution environment")
    source_records = _detached_mapping(source_hashes, "M37 source hashes")
    bank = bank_result.get("template_bank", {}).get("records")
    if not isinstance(bank, list):
        raise core.V0P6ContractError("M37 bank preflight lacks its records")

    temporary = parent / (
        f".{destination.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    )
    temporary.mkdir(mode=0o700)
    try:
        basis = core.make_factor_basis_from_metadata(upstream)
        core.validate_m37_factor_basis_scan_inventory(basis, upstream["scans"])
        table = core.make_template_factor_table(
            basis,
            bank,
            expected_template_bank_sha256=core.M37_BANK_SHA256,
        )
        factor_receipt = factor_io.publish_m37_factor_bundle(
            temporary / "factor_bundle.v0p6",
            basis,
            table,
            bank,
            upstream["scans"],
            environment=environment_record,
            source_hashes=source_records,
        )
        initialization = {
            "schema_version": 1,
            "artifact_type": "m37-detector-v0p6-run-initialization-v1",
            "run_id": run_id,
            "experiment_contract_sha256": core.M37_EXPERIMENT_CONTRACT_SHA256,
            "factor_bundle_manifest_sha256": factor_receipt.manifest_sha256,
            "factor_table_sha256": factor_receipt.factor_table_sha256,
            "analysis_contract_sha256": factor_receipt.analysis_contract_sha256,
            "environment_sha256": factor_receipt.environment_sha256,
            "source_metadata_sha256": factor_receipt.source_metadata_sha256,
            "stage_order": list(state.M37_RUN_STAGES),
            "spectral_access_authorized": False,
            "spectral_dataset_values_read": False,
        }
        initialization_sha256 = _sha256_bytes(
            core.canonical_json_bytes(initialization)
        )
        journal = state.create_m37_run_journal(
            temporary / "run.journal.jsonl",
            run_id=run_id,
            initialization_sha256=initialization_sha256,
            metadata={
                "spectral_access_authorized": False,
                "spectral_dataset_values_read": False,
                "initialization_contract": initialization,
            },
        )
        journal = state.advance_m37_run_journal(
            temporary / "run.journal.jsonl",
            expected_head_sha256=journal.head_sha256,
            stage="factor_bundle_ready",
            artifact_sha256=factor_receipt.manifest_sha256,
            metadata={
                "spectral_access_authorized": False,
                "spectral_dataset_values_read": False,
                "factor_bundle_manifest_sha256": factor_receipt.manifest_sha256,
                "factor_bundle_file_sha256": factor_receipt.file_sha256,
                "factor_table_sha256": factor_receipt.factor_table_sha256,
                "analysis_contract_sha256": factor_receipt.analysis_contract_sha256,
            },
        )
        record = _bootstrap_record(
            run_id=run_id,
            initialization_contract_sha256=initialization_sha256,
            factor_receipt=factor_receipt,
            journal_receipt=journal,
        )
        _write_read_only(
            temporary / "bootstrap.json", core.canonical_json_bytes(record)
        )
        os.rename(temporary, destination)
        parent_descriptor = os.open(
            parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    opened = open_m37_bootstrap(
        destination,
        expected_bootstrap_sha256=record["bootstrap_sha256"],
    )
    return opened.receipt


def open_m37_bootstrap(
    run_directory: str | os.PathLike[str],
    *,
    expected_bootstrap_sha256: str,
) -> M37Bootstrap:
    """Reopen a bootstrap only against an independently supplied root digest."""
    root = Path(run_directory)
    raw = (root / "bootstrap.json").read_bytes()
    try:
        record = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError("M37 bootstrap receipt is invalid JSON") from error
    if core.canonical_json_bytes(record) != raw:
        raise core.V0P6ContractError("M37 bootstrap receipt is not canonical JSON")
    validated = _validate_bootstrap_record(record)
    expected = _sha256(expected_bootstrap_sha256, "expected bootstrap identity")
    if validated["bootstrap_sha256"] != expected:
        raise core.V0P6IncompleteError(
            "M37 bootstrap differs from its independent identity"
        )
    factor_bundle = factor_io.open_m37_factor_bundle(
        root / validated["factor_bundle_path"],
        expected_manifest_sha256=validated["factor_bundle_manifest_sha256"],
        expected_file_sha256=validated["factor_bundle_file_sha256"],
        expected_factor_table_sha256=validated["factor_table_sha256"],
    )
    journal = state.read_m37_run_journal(
        root / validated["journal_path"],
        expected_head_sha256=validated["journal_head_sha256"],
    )
    if (
        journal.file_sha256 != validated["journal_file_sha256"]
        or journal.run_id != validated["run_id"]
        or journal.event_count != validated["journal_event_count"]
        or journal.stage != validated["journal_stage"]
        or factor_bundle.receipt.analysis_contract_sha256
        != validated["analysis_contract_sha256"]
        or factor_bundle.receipt.environment_sha256
        != validated["environment_sha256"]
        or factor_bundle.receipt.source_metadata_sha256
        != validated["source_metadata_sha256"]
    ):
        raise core.V0P6IncompleteError("M37 bootstrap cross-artifact join changed")
    receipt = M37BootstrapReceipt(
        run_directory=str(root.absolute()),
        run_id=validated["run_id"],
        bootstrap_sha256=validated["bootstrap_sha256"],
        initialization_contract_sha256=validated[
            "initialization_contract_sha256"
        ],
        factor_bundle_manifest_sha256=validated[
            "factor_bundle_manifest_sha256"
        ],
        factor_bundle_file_sha256=validated["factor_bundle_file_sha256"],
        factor_table_sha256=validated["factor_table_sha256"],
        analysis_contract_sha256=validated["analysis_contract_sha256"],
        journal_head_sha256=validated["journal_head_sha256"],
        journal_file_sha256=validated["journal_file_sha256"],
        environment_sha256=validated["environment_sha256"],
        source_metadata_sha256=validated["source_metadata_sha256"],
        spectral_access_authorized=False,
        spectral_dataset_values_read=False,
    )
    return M37Bootstrap(
        factor_bundle=factor_bundle,
        journal=journal,
        receipt=receipt,
    )
