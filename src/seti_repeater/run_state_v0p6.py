"""Fail-closed, append-only lifecycle journal for an M37 v0.6 run.

The journal is deliberately data-agnostic.  It binds stage artifacts and
their independent SHA-256 identities, but it cannot authorize telescope
access or manufacture a scientific result.  Every transition is a canonical
JSON line in a hash chain; ``invalid`` is permanent.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any, Mapping

from . import search_v0p6 as core


M37_RUN_STAGES = (
    "initialized",
    "factor_bundle_ready",
    "spectral_access_authorized",
    "extraction_complete",
    "cache_manifest_complete",
    "calibration_complete",
    "threshold_complete",
    "on_retention_complete",
    "off_retention_complete",
    "physical_disposition_complete",
    "significance_complete",
    "outcome_complete",
    "completeness_complete",
    "publication_ready",
    "published",
)
M37_INVALID_STAGE = "invalid"
M37_SPECTRAL_AUTHORIZATION_SCOPE = (
    "m37-hd156668-six-hdf5-extraction-only"
)
_ZERO_SHA256 = "0" * 64
_HEX = frozenset("0123456789abcdef")
_MAXIMUM_JOURNAL_BYTES = 16_777_216
_MAXIMUM_EVENT_BYTES = 262_144
_EVENT_FIELDS = {
    "schema_version",
    "artifact_type",
    "run_id",
    "sequence",
    "stage",
    "previous_event_sha256",
    "artifact_sha256",
    "metadata",
    "event_sha256",
}


def _sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise core.V0P6ContractError(f"{label} is not a lowercase SHA-256")
    return value


def _strict_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise core.V0P6ContractError(f"{label} must be an exact integer")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise core.V0P6ContractError(f"run journal repeats key {key!r}")
        result[key] = value
    return result


def _detached_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise core.V0P6ContractError("run journal metadata must be a mapping")
    try:
        detached = json.loads(core.canonical_json_bytes(dict(value)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "run journal metadata is not canonical finite JSON"
        ) from error
    if not isinstance(detached, dict):
        raise core.V0P6ContractError("run journal metadata must be a mapping")
    return detached


def _validate_stage_metadata(stage: str, metadata: Mapping[str, Any]) -> None:
    if stage in {"initialized", "factor_bundle_ready"}:
        if (
            metadata.get("spectral_access_authorized") is not False
            or metadata.get("spectral_dataset_values_read") is not False
        ):
            raise core.V0P6IncompleteError(
                "pre-authorization run stage crossed the spectral boundary"
            )
    elif stage == "spectral_access_authorized":
        if (
            metadata.get("spectral_access_authorized") is not True
            or metadata.get("spectral_dataset_values_read") is not False
            or metadata.get("authorization_scope")
            != M37_SPECTRAL_AUTHORIZATION_SCOPE
        ):
            raise core.V0P6IncompleteError(
                "spectral authorization stage lacks the frozen scope"
            )
        _sha256(
            metadata.get("authorization_receipt_sha256"),
            "spectral authorization receipt identity",
        )
    elif stage == "physical_disposition_complete":
        if (
            metadata.get("spectral_access_authorized") is not True
            or metadata.get("spectral_dataset_values_read") is not True
        ):
            raise core.V0P6IncompleteError(
                "post-extraction run stage lacks spectral-contact provenance"
            )
        for name in (
            "physical_disposition_manifest_sha256",
            "disposition_artifact_inventory_sha256",
            "on_retention_inventory_sha256",
            "cache_run_manifest_file_sha256",
            "factor_bundle_manifest_sha256",
        ):
            _sha256(metadata.get(name), name.replace("_", " "))
        window_count = _strict_int(
            metadata.get("window_count"), "physical-disposition window count"
        )
        final_count = _strict_int(
            metadata.get("total_final_record_count"),
            "physical-disposition final record count",
        )
        mapped_cap = _strict_int(
            metadata.get("maximum_process_mapped_bytes"),
            "physical-disposition mapped-byte cap",
        )
        mapped_peak = _strict_int(
            metadata.get("maximum_window_peak_mapped_bytes"),
            "physical-disposition mapped-byte peak",
        )
        handle_peak = _strict_int(
            metadata.get("maximum_window_peak_handle_count"),
            "physical-disposition handle peak",
        )
        batch_count = _strict_int(
            metadata.get("total_batch_count"),
            "physical-disposition batch count",
        )
        cache_count = _strict_int(
            metadata.get("total_opened_cache_count"),
            "physical-disposition opened-cache count",
        )
        amendment_sha256 = metadata.get("capacity_amendment_file_sha256")
        if amendment_sha256 is None:
            maximum_final_count = (
                len(core.M37_WINDOW_IDS)
                * core.M37_MAXIMUM_RECORDS_PER_WINDOW
            )
        else:
            from . import capacity_v0p6p1 as capacity

            if amendment_sha256 != capacity.M37_V0P6P1_AMENDMENT_FILE_SHA256:
                raise core.V0P6IncompleteError(
                    "physical-disposition capacity amendment changed"
                )
            maximum_final_count = (
                len(core.M37_WINDOW_IDS)
                * capacity.M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW
            )
        if (
            window_count != len(core.M37_WINDOW_IDS)
            or final_count < 0
            or final_count > maximum_final_count
            or mapped_cap != core.M37_LIVE_NDARRAY_CAP_BYTES
            or mapped_peak < 0
            or mapped_peak > mapped_cap
            or handle_peak < 1
            or batch_count < 1
            or cache_count < 1
        ):
            raise core.V0P6IncompleteError(
                "physical-disposition journal accounting is incomplete"
            )
    elif stage == "significance_complete":
        if (
            metadata.get("spectral_access_authorized") is not True
            or metadata.get("spectral_dataset_values_read") is not True
        ):
            raise core.V0P6IncompleteError(
                "significance stage lacks spectral-contact provenance"
            )
        from . import capacity_v0p6p1 as capacity

        if metadata.get("capacity_amendment_file_sha256") != (
            capacity.M37_V0P6P1_AMENDMENT_FILE_SHA256
        ):
            raise core.V0P6IncompleteError(
                "significance capacity amendment changed"
            )
        for name in (
            "significance_manifest_sha256",
            "significance_artifact_inventory_sha256",
            "threshold_certificate_sha256",
            "global_null_maxima_sha256",
        ):
            _sha256(metadata.get(name), name.replace("_", " "))
        window_count = _strict_int(
            metadata.get("window_count"), "significance window count"
        )
        record_count = _strict_int(
            metadata.get("total_record_count"),
            "significance record count",
        )
        eligible_count = _strict_int(
            metadata.get("total_scientifically_eligible_count"),
            "scientifically eligible record count",
        )
        maximum_records = (
            len(core.M37_WINDOW_IDS)
            * capacity.M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW
        )
        if (
            window_count != len(core.M37_WINDOW_IDS)
            or record_count < 0
            or record_count > maximum_records
            or eligible_count < 0
            or eligible_count > record_count
        ):
            raise core.V0P6IncompleteError(
                "significance journal accounting is incomplete"
            )
    elif stage == "outcome_complete":
        if (
            metadata.get("spectral_access_authorized") is not True
            or metadata.get("spectral_dataset_values_read") is not True
        ):
            raise core.V0P6IncompleteError(
                "outcome stage lacks spectral-contact provenance"
            )
        from . import capacity_v0p6p1 as capacity

        if metadata.get("capacity_amendment_file_sha256") != (
            capacity.M37_V0P6P1_AMENDMENT_FILE_SHA256
        ):
            raise core.V0P6IncompleteError("outcome capacity amendment changed")
        for name in (
            "outcome_result_sha256",
            "outcome_certificate_sha256",
            "threshold_certificate_sha256",
        ):
            _sha256(metadata.get(name), name.replace("_", " "))
        record_count = _strict_int(
            metadata.get("outcome_record_count"), "outcome record count"
        )
        unresolved_count = _strict_int(
            metadata.get("unresolved_candidate_count"),
            "unresolved candidate count",
        )
        state = metadata.get("global_search_state")
        global_outcome = metadata.get("global_outcome")
        is_open = unresolved_count > 0
        maximum_records = (
            len(core.M37_WINDOW_IDS)
            * capacity.M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW
        )
        if (
            record_count < 0
            or record_count > maximum_records
            or unresolved_count < 0
            or unresolved_count > record_count
            or state != ("open" if is_open else "closed")
            or global_outcome
            != (
                "open_unresolved_scientific_candidates"
                if is_open
                else "closed_no_unresolved_scientific_candidates"
            )
        ):
            raise core.V0P6IncompleteError(
                "outcome journal accounting is incomplete"
            )
    elif stage in M37_RUN_STAGES[3:]:
        if (
            metadata.get("spectral_access_authorized") is not True
            or metadata.get("spectral_dataset_values_read") is not True
        ):
            raise core.V0P6IncompleteError(
                "post-extraction run stage lacks spectral-contact provenance"
            )
    elif stage == M37_INVALID_STAGE:
        reason = metadata.get("reason_code")
        if not isinstance(reason, str) or not reason or len(reason) > 128:
            raise core.V0P6ContractError(
                "run invalidation event lacks a reason code"
            )


def _event_without_identity(
    *,
    run_id: str,
    sequence: int,
    stage: str,
    previous_event_sha256: str,
    artifact_sha256: str,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(run_id, str) or not run_id or len(run_id) > 128:
        raise core.V0P6ContractError("run journal ID is invalid")
    sequence = _strict_int(sequence, "run journal sequence")
    if sequence < 0:
        raise core.V0P6ContractError("run journal sequence is negative")
    stage = str(stage)
    if stage not in {*M37_RUN_STAGES, M37_INVALID_STAGE}:
        raise core.V0P6ContractError("run journal stage is unknown")
    detached_metadata = _detached_metadata(metadata)
    _validate_stage_metadata(stage, detached_metadata)
    return {
        "schema_version": 1,
        "artifact_type": "m37-detector-v0p6-run-journal-event-v1",
        "run_id": run_id,
        "sequence": sequence,
        "stage": stage,
        "previous_event_sha256": _sha256(
            previous_event_sha256, "previous run-journal event identity"
        ),
        "artifact_sha256": _sha256(
            artifact_sha256, "run-journal stage artifact identity"
        ),
        "metadata": detached_metadata,
    }


def _seal_event(**values: Any) -> dict[str, Any]:
    record = _event_without_identity(**values)
    record["event_sha256"] = hashlib.sha256(
        core.canonical_json_bytes(record)
    ).hexdigest()
    return record


@dataclass(frozen=True)
class RunJournalReceipt:
    path: str
    run_id: str
    event_count: int
    stage: str
    head_sha256: str
    invalid: bool
    complete: bool
    file_sha256: str
    file_nbytes: int


def _validate_event(
    raw: Mapping[str, Any],
    *,
    expected_run_id: str,
    expected_sequence: int,
    expected_previous: str,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or set(raw) != _EVENT_FIELDS:
        raise core.V0P6ContractError("run journal event schema changed")
    event = dict(raw)
    observed_identity = _sha256(
        event.pop("event_sha256"), "run-journal event identity"
    )
    reconstructed = _event_without_identity(
        run_id=event.get("run_id"),
        sequence=event.get("sequence"),
        stage=event.get("stage"),
        previous_event_sha256=event.get("previous_event_sha256"),
        artifact_sha256=event.get("artifact_sha256"),
        metadata=event.get("metadata"),
    )
    expected_identity = hashlib.sha256(
        core.canonical_json_bytes(reconstructed)
    ).hexdigest()
    if observed_identity != expected_identity:
        raise core.V0P6IncompleteError("run journal event identity changed")
    if reconstructed["run_id"] != expected_run_id:
        raise core.V0P6IncompleteError("run journal ID changed")
    if reconstructed["sequence"] != expected_sequence:
        raise core.V0P6IncompleteError("run journal sequence is missing or duplicated")
    if reconstructed["previous_event_sha256"] != expected_previous:
        raise core.V0P6IncompleteError("run journal hash chain changed")
    reconstructed["event_sha256"] = observed_identity
    return reconstructed


def _parse_journal_bytes(raw: bytes) -> tuple[dict[str, Any], ...]:
    if not raw or len(raw) > _MAXIMUM_JOURNAL_BYTES:
        raise core.V0P6CapacityError("run journal size is invalid")
    if not raw.endswith(b"\n"):
        raise core.V0P6IncompleteError("run journal lacks its final newline")
    lines = raw.splitlines(keepends=True)
    if not lines:
        raise core.V0P6IncompleteError("run journal is empty")
    parsed: list[dict[str, Any]] = []
    expected_run_id: str | None = None
    previous = _ZERO_SHA256
    invalid_seen = False
    for sequence, line in enumerate(lines):
        if len(line) > _MAXIMUM_EVENT_BYTES or not line.endswith(b"\n"):
            raise core.V0P6CapacityError("run journal event size is invalid")
        try:
            event = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise core.V0P6ContractError("run journal contains invalid JSON") from error
        if core.canonical_json_bytes(event) != line:
            raise core.V0P6ContractError("run journal event is not canonical JSON")
        if expected_run_id is None:
            if not isinstance(event, dict) or not isinstance(event.get("run_id"), str):
                raise core.V0P6ContractError("run journal first event lacks an ID")
            expected_run_id = event["run_id"]
        validated = _validate_event(
            event,
            expected_run_id=expected_run_id,
            expected_sequence=sequence,
            expected_previous=previous,
        )
        stage = validated["stage"]
        if sequence == 0:
            if stage != "initialized":
                raise core.V0P6IncompleteError(
                    "run journal does not start at initialized"
                )
        else:
            prior_stage = parsed[-1]["stage"]
            if prior_stage in {M37_INVALID_STAGE, "published"}:
                raise core.V0P6IncompleteError(
                    "run journal continued after a terminal state"
                )
            if stage == M37_INVALID_STAGE:
                invalid_seen = True
            else:
                expected_index = M37_RUN_STAGES.index(prior_stage) + 1
                if expected_index >= len(M37_RUN_STAGES) or stage != M37_RUN_STAGES[
                    expected_index
                ]:
                    raise core.V0P6IncompleteError(
                        "run journal stage was skipped, repeated, or reordered"
                    )
        if invalid_seen and stage != M37_INVALID_STAGE:
            raise core.V0P6IncompleteError(
                "run journal continued after invalidation"
            )
        parsed.append(validated)
        previous = validated["event_sha256"]
    return tuple(parsed)


def _receipt(path: Path, raw: bytes, events: tuple[dict[str, Any], ...]) -> RunJournalReceipt:
    last = events[-1]
    return RunJournalReceipt(
        path=str(path.absolute()),
        run_id=last["run_id"],
        event_count=len(events),
        stage=last["stage"],
        head_sha256=last["event_sha256"],
        invalid=last["stage"] == M37_INVALID_STAGE,
        complete=last["stage"] == "published",
        file_sha256=hashlib.sha256(raw).hexdigest(),
        file_nbytes=len(raw),
    )


def read_m37_run_journal(
    path: str | os.PathLike[str],
    *,
    expected_head_sha256: str | None = None,
) -> RunJournalReceipt:
    journal_path = Path(path)
    raw = journal_path.read_bytes()
    events = _parse_journal_bytes(raw)
    receipt = _receipt(journal_path, raw, events)
    if expected_head_sha256 is not None and receipt.head_sha256 != _sha256(
        expected_head_sha256, "expected run-journal head identity"
    ):
        raise core.V0P6IncompleteError(
            "run journal differs from its independently supplied head"
        )
    return receipt


def _atomic_create(path: Path, payload: bytes) -> None:
    parent = path.parent
    if not parent.is_dir():
        raise core.V0P6ContractError("run journal parent directory is absent")
    if path.exists():
        raise FileExistsError(path)
    temporary = parent / f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(8)}"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short write while creating run journal")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise FileExistsError(path) from None
        temporary.unlink()
        directory_descriptor = os.open(
            parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def create_m37_run_journal(
    path: str | os.PathLike[str],
    *,
    run_id: str,
    initialization_sha256: str,
    metadata: Mapping[str, Any],
) -> RunJournalReceipt:
    """Create the immutable first event of a new M37 run journal."""
    event = _seal_event(
        run_id=run_id,
        sequence=0,
        stage="initialized",
        previous_event_sha256=_ZERO_SHA256,
        artifact_sha256=initialization_sha256,
        metadata=metadata,
    )
    payload = core.canonical_json_bytes(event)
    if len(payload) > _MAXIMUM_EVENT_BYTES:
        raise core.V0P6CapacityError("run journal initial event exceeds its cap")
    journal_path = Path(path)
    _atomic_create(journal_path, payload)
    return read_m37_run_journal(
        journal_path, expected_head_sha256=event["event_sha256"]
    )


def _append_event(
    path: Path,
    *,
    expected_head_sha256: str,
    stage: str,
    artifact_sha256: str,
    metadata: Mapping[str, Any],
) -> RunJournalReceipt:
    expected_head = _sha256(
        expected_head_sha256, "expected run-journal head identity"
    )
    descriptor = os.open(path, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        raw = b""
        while True:
            chunk = os.read(descriptor, 1_048_576)
            if not chunk:
                break
            raw += chunk
            if len(raw) > _MAXIMUM_JOURNAL_BYTES:
                raise core.V0P6CapacityError("run journal exceeds its byte cap")
        events = _parse_journal_bytes(raw)
        current = _receipt(path, raw, events)
        if current.head_sha256 != expected_head:
            raise core.V0P6IncompleteError(
                "run journal changed since the supplied restart receipt"
            )
        if current.stage in {M37_INVALID_STAGE, "published"}:
            raise core.V0P6IncompleteError(
                "run journal is already in a terminal state"
            )
        if stage == M37_INVALID_STAGE:
            next_stage = M37_INVALID_STAGE
        else:
            expected_index = M37_RUN_STAGES.index(current.stage) + 1
            if expected_index >= len(M37_RUN_STAGES):
                raise core.V0P6IncompleteError("run journal has no next stage")
            next_stage = M37_RUN_STAGES[expected_index]
            if str(stage) != next_stage:
                raise core.V0P6IncompleteError(
                    "run journal transition tried to skip, repeat, or reorder a stage"
                )
        event = _seal_event(
            run_id=current.run_id,
            sequence=current.event_count,
            stage=next_stage,
            previous_event_sha256=current.head_sha256,
            artifact_sha256=artifact_sha256,
            metadata=metadata,
        )
        payload = core.canonical_json_bytes(event)
        if len(payload) > _MAXIMUM_EVENT_BYTES:
            raise core.V0P6CapacityError("run journal event exceeds its cap")
        os.lseek(descriptor, 0, os.SEEK_END)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError("short write while advancing run journal")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return read_m37_run_journal(
        path, expected_head_sha256=event["event_sha256"]
    )


def advance_m37_run_journal(
    path: str | os.PathLike[str],
    *,
    expected_head_sha256: str,
    stage: str,
    artifact_sha256: str,
    metadata: Mapping[str, Any],
) -> RunJournalReceipt:
    """Append exactly the next frozen stage against a trusted restart head."""
    if str(stage) == M37_INVALID_STAGE:
        raise core.V0P6ContractError("use invalidate_m37_run_journal")
    return _append_event(
        Path(path),
        expected_head_sha256=expected_head_sha256,
        stage=str(stage),
        artifact_sha256=artifact_sha256,
        metadata=metadata,
    )


def advance_m37_physical_disposition_from_manifest(
    path: str | os.PathLike[str],
    *,
    expected_head_sha256: str,
    manifest_path: str | os.PathLike[str],
    expected_manifest_file_sha256: str,
    expected_manifest_sha256: str,
    expected_run_id: str,
    expected_cache_run_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_on_retention_inventory_sha256: str,
) -> RunJournalReceipt:
    """Advance only from a fully reopened exact five-window disposition run."""
    from . import physical_disposition_manifest_v0p6 as disposition_run

    current = read_m37_run_journal(
        path, expected_head_sha256=expected_head_sha256
    )
    if current.run_id != expected_run_id:
        raise core.V0P6IncompleteError(
            "physical-disposition manifest run differs from the journal"
        )
    opened = disposition_run.open_m37_physical_disposition_run_manifest(
        manifest_path,
        expected_file_sha256=expected_manifest_file_sha256,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_run_id=expected_run_id,
        expected_cache_run_manifest_file_sha256=(
            expected_cache_run_manifest_file_sha256
        ),
        expected_factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_on_retention_inventory_sha256=(
            expected_on_retention_inventory_sha256
        ),
    )
    receipt = opened.receipt
    return advance_m37_run_journal(
        path,
        expected_head_sha256=current.head_sha256,
        stage="physical_disposition_complete",
        artifact_sha256=receipt.file_sha256,
        metadata={
            "spectral_access_authorized": True,
            "spectral_dataset_values_read": True,
            "physical_disposition_manifest_sha256": receipt.manifest_sha256,
            "disposition_artifact_inventory_sha256": (
                receipt.disposition_artifact_inventory_sha256
            ),
            "on_retention_inventory_sha256": (
                receipt.on_retention_inventory_sha256
            ),
            "cache_run_manifest_file_sha256": (
                receipt.cache_run_manifest_file_sha256
            ),
            "factor_bundle_manifest_sha256": (
                receipt.factor_bundle_manifest_sha256
            ),
            "window_count": receipt.window_count,
            "total_final_record_count": receipt.total_final_record_count,
            "maximum_process_mapped_bytes": (
                receipt.maximum_process_mapped_bytes
            ),
            "maximum_window_peak_mapped_bytes": (
                receipt.maximum_window_peak_mapped_bytes
            ),
            "maximum_window_peak_handle_count": (
                receipt.maximum_window_peak_handle_count
            ),
            "total_batch_count": receipt.total_batch_count,
            "total_opened_cache_count": receipt.total_opened_cache_count,
        },
    )


def invalidate_m37_run_journal(
    path: str | os.PathLike[str],
    *,
    expected_head_sha256: str,
    evidence_sha256: str,
    reason_code: str,
    metadata: Mapping[str, Any] | None = None,
) -> RunJournalReceipt:
    """Permanently invalidate a non-terminal run."""
    if not isinstance(reason_code, str) or not reason_code or len(reason_code) > 128:
        raise core.V0P6ContractError("run invalidation reason code is invalid")
    details = dict(metadata or {})
    if "reason_code" in details:
        raise core.V0P6ContractError("run invalidation metadata repeats reason_code")
    details["reason_code"] = reason_code
    return _append_event(
        Path(path),
        expected_head_sha256=expected_head_sha256,
        stage=M37_INVALID_STAGE,
        artifact_sha256=evidence_sha256,
        metadata=details,
    )
