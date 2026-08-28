"""Fail-closed width streaming for detector-v0.6 native cache artifacts.

The physical-evidence stages must not keep all eight widths mapped at once.
This module opens exactly one width-by-three-scan batch from a trusted cache
run manifest, accounts every mapped payload byte through
``NativeFilterCacheArena``, closes the batch before the next width, and emits
an evidence-bound resource receipt.

Importing this module does not open telescope data or cache files.
"""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Iterator, Mapping, Sequence

from . import cache_manifest_v0p6 as run_cache
from . import native_cache_v0p6 as disk_cache
from . import search_v0p6 as core


STREAM_RESOURCE_ARTIFACT_TYPE = (
    "seti_repeater.detector_v0p6_width_stream_resource_receipt"
)
STREAM_RESOURCE_SCHEMA_VERSION = 2


def _expected_keys(
    values: Sequence[tuple[str, str, int]],
) -> tuple[tuple[str, str, int], ...]:
    result: list[tuple[str, str, int]] = []
    for window_id, scan_label, width in values:
        if not isinstance(window_id, str) or not window_id:
            raise core.V0P6ContractError("cache-stream window ID is invalid")
        if not isinstance(scan_label, str) or not scan_label:
            raise core.V0P6ContractError("cache-stream scan label is invalid")
        result.append(
            (
                window_id,
                scan_label,
                core._strict_int(width, "cache-stream spectral width"),
            )
        )
    if len(set(result)) != len(result):
        raise core.V0P6IncompleteError(
            "cache-stream expected-key inventory contains duplicates"
        )
    return tuple(result)


def _validate_manifest_object(
    manifest: run_cache.CacheRunManifest,
    *,
    expected_file_sha256: str,
    expected_inventory_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    expected_keys: tuple[tuple[str, str, int], ...],
) -> tuple[run_cache.CacheManifestEntry, ...]:
    if not isinstance(manifest, run_cache.CacheRunManifest):
        raise core.V0P6ContractError(
            "cache stream requires a validated CacheRunManifest"
        )
    file_digest = core._frozen_sha256(
        expected_file_sha256, "cache-stream manifest file identity"
    )
    inventory_digest = core._frozen_sha256(
        expected_inventory_sha256, "cache-stream inventory identity"
    )
    factor_digest = core._frozen_sha256(
        expected_factor_bundle_manifest_sha256,
        "cache-stream factor-bundle identity",
    )
    entries = tuple(
        run_cache._validate_entry(entry.as_record())
        for entry in manifest.entries
    )
    observed_keys = tuple(
        (entry.window_id, entry.scan_label, entry.width_channels)
        for entry in entries
    )
    records = [entry.as_record() for entry in entries]
    observed_inventory = hashlib.sha256(
        core.canonical_json_bytes(records)
    ).hexdigest()
    payload_nbytes = sum(entry.payload_nbytes for entry in entries)
    receipt = manifest.receipt
    manifest_payload = core.canonical_json_bytes(
        {
            "schema_version": 1,
            "artifact_type": "m37-detector-v0p6-cache-run-manifest-v1",
            "detector_version": core.DETECTOR_VERSION,
            "run_id": manifest.run_id,
            "factor_bundle_manifest_sha256": factor_digest,
            "entry_count": len(entries),
            "payload_nbytes": payload_nbytes,
            "inventory_sha256": observed_inventory,
            "entries": records,
        }
    )
    if (
        receipt.file_sha256 != file_digest
        or receipt.inventory_sha256 != inventory_digest
        or receipt.factor_bundle_manifest_sha256 != factor_digest
        or receipt.entry_count != len(entries)
        or receipt.payload_nbytes != payload_nbytes
        or receipt.file_nbytes != len(manifest_payload)
        or observed_inventory != inventory_digest
        or hashlib.sha256(manifest_payload).hexdigest() != file_digest
        or observed_keys != expected_keys
    ):
        raise core.V0P6IncompleteError(
            "cache-stream manifest object differs from its trusted inventory"
        )
    return entries


class CacheWidthStream:
    """Open complete scan batches in exact width order under one byte cap."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        manifest: run_cache.CacheRunManifest,
        *,
        expected_manifest_file_sha256: str,
        expected_inventory_sha256: str,
        expected_factor_bundle_manifest_sha256: str,
        expected_keys: Sequence[tuple[str, str, int]],
        window_id: str,
        scan_kind: str,
        scan_labels: Sequence[str],
        spectral_widths: Sequence[int],
        maximum_mapped_bytes: int,
    ) -> None:
        self.window_id = str(window_id)
        self.scan_kind = str(scan_kind)
        if self.scan_kind not in {"on", "off"}:
            raise core.V0P6ContractError(
                "cache-stream scan kind must be 'on' or 'off'"
            )
        self.scan_labels = tuple(str(label) for label in scan_labels)
        if (
            not self.scan_labels
            or any(not label for label in self.scan_labels)
            or len(set(self.scan_labels)) != len(self.scan_labels)
        ):
            raise core.V0P6ContractError(
                "cache-stream scan-label inventory is invalid"
            )
        self.spectral_widths = tuple(
            core._strict_widths(tuple(spectral_widths))
        )
        self.maximum_mapped_bytes = core._strict_int(
            maximum_mapped_bytes, "cache-stream mapped-byte cap"
        )
        if self.maximum_mapped_bytes < 1:
            raise core.V0P6ContractError(
                "cache-stream mapped-byte cap must be positive"
            )
        expected = _expected_keys(expected_keys)
        entries = _validate_manifest_object(
            manifest,
            expected_file_sha256=expected_manifest_file_sha256,
            expected_inventory_sha256=expected_inventory_sha256,
            expected_factor_bundle_manifest_sha256=(
                expected_factor_bundle_manifest_sha256
            ),
            expected_keys=expected,
        )
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise core.V0P6ContractError(
                "cache-stream run root is not a directory"
            )
        self.manifest = manifest
        self._entries = {
            (entry.window_id, entry.scan_label, entry.width_channels): entry
            for entry in entries
        }
        selected_keys = tuple(
            (self.window_id, label, width)
            for width in self.spectral_widths
            for label in self.scan_labels
        )
        missing = [key for key in selected_keys if key not in self._entries]
        if missing:
            raise core.V0P6IncompleteError(
                "cache-stream selected width-by-scan inventory is incomplete"
            )
        for key in selected_keys:
            entry = self._entries[key]
            if entry.scan_kind != self.scan_kind:
                raise core.V0P6ContractError(
                    "cache-stream selected entry has the wrong scan kind"
                )
        self._next_width_ordinal = 0
        self._active = False
        self._invalid = False
        self._sealed = False
        self._batch_inventory: list[dict[str, Any]] = []
        self._peak_mapped_bytes = 0
        self._peak_handle_count = 0

    @classmethod
    def from_manifest_file(
        cls,
        root: str | os.PathLike[str],
        manifest_path: str | os.PathLike[str],
        *,
        expected_manifest_file_sha256: str,
        expected_factor_bundle_manifest_sha256: str,
        expected_keys: Sequence[tuple[str, str, int]],
        window_id: str,
        scan_kind: str,
        scan_labels: Sequence[str],
        spectral_widths: Sequence[int],
        maximum_mapped_bytes: int,
    ) -> CacheWidthStream:
        expected = _expected_keys(expected_keys)
        manifest = run_cache.open_cache_run_manifest(
            manifest_path,
            expected_file_sha256=expected_manifest_file_sha256,
            expected_factor_bundle_manifest_sha256=(
                expected_factor_bundle_manifest_sha256
            ),
            expected_keys=expected,
        )
        return cls(
            root,
            manifest,
            expected_manifest_file_sha256=expected_manifest_file_sha256,
            expected_inventory_sha256=manifest.receipt.inventory_sha256,
            expected_factor_bundle_manifest_sha256=(
                expected_factor_bundle_manifest_sha256
            ),
            expected_keys=expected,
            window_id=window_id,
            scan_kind=scan_kind,
            scan_labels=scan_labels,
            spectral_widths=spectral_widths,
            maximum_mapped_bytes=maximum_mapped_bytes,
        )

    @contextmanager
    def open_width(self, width: int) -> Iterator[Mapping[str, Any]]:
        """Yield one complete scan batch and close it before returning."""
        width = core._strict_int(width, "cache-stream spectral width")
        if self._sealed or self._invalid:
            raise core.V0P6IncompleteError(
                "cache stream is sealed or permanently invalid"
            )
        if self._active:
            self._invalid = True
            raise core.V0P6IncompleteError(
                "cache stream does not permit overlapping width batches"
            )
        if self._next_width_ordinal >= len(self.spectral_widths) or (
            width != self.spectral_widths[self._next_width_ordinal]
        ):
            self._invalid = True
            raise core.V0P6IncompleteError(
                "cache widths were opened out of order, repeated, or skipped"
            )
        entries = tuple(
            self._entries[(self.window_id, label, width)]
            for label in self.scan_labels
        )
        planned_payload_nbytes = sum(entry.payload_nbytes for entry in entries)
        if planned_payload_nbytes > self.maximum_mapped_bytes:
            self._invalid = True
            raise core.V0P6CapacityError(
                "cache width batch exceeds the mapped-byte cap"
            )

        self._active = True
        arena = disk_cache.NativeFilterCacheArena(self.maximum_mapped_bytes)
        batch_peak_bytes = 0
        batch_peak_handles = 0
        completed = False
        try:
            with ExitStack() as stack:
                opened: dict[str, Any] = {}
                for entry in entries:
                    candidate = (self.root / entry.relative_path).resolve()
                    if self.root not in candidate.parents:
                        raise core.V0P6ContractError(
                            "cache-stream path escapes the run root"
                        )
                    plan = core.native_filter_cache_plan_from_record(
                        entry.plan_record,
                        expected_plan_sha256=entry.plan_sha256,
                    )
                    handle = stack.enter_context(
                        disk_cache.open_native_filter_cache(
                            candidate,
                            expected_plan=plan,
                            expected_plan_sha256=entry.plan_sha256,
                            expected_manifest_sha256=(
                                entry.cache_manifest_sha256
                            ),
                            arena=arena,
                        )
                    )
                    if handle.payload_sha256 != entry.payload_sha256:
                        raise core.V0P6IncompleteError(
                            "cache-stream payload receipt changed"
                        )
                    opened[entry.scan_label] = handle
                    batch_peak_bytes = max(
                        batch_peak_bytes, arena.mapped_bytes
                    )
                    batch_peak_handles = max(
                        batch_peak_handles, arena.handle_count
                    )
                if tuple(opened) != self.scan_labels:
                    raise core.V0P6IncompleteError(
                        "cache-stream scan batch order changed"
                    )
                yield opened
                completed = True
        except Exception:
            self._invalid = True
            raise
        finally:
            arena.close()
            self._active = False
            if arena.mapped_bytes != 0 or arena.handle_count != 0:
                self._invalid = True
                raise core.V0P6IncompleteError(
                    "cache-stream batch did not release every mapping"
                )

        if not completed:
            self._invalid = True
            raise core.V0P6IncompleteError(
                "cache-stream width batch did not complete"
            )
        self._peak_mapped_bytes = max(
            self._peak_mapped_bytes, batch_peak_bytes
        )
        self._peak_handle_count = max(
            self._peak_handle_count, batch_peak_handles
        )
        self._batch_inventory.append(
            {
                "width_ordinal": self._next_width_ordinal,
                "spectral_width_channels": width,
                "scan_labels": list(self.scan_labels),
                "cache_count": len(entries),
                "cache_receipts": [
                    {
                        "scan_label": entry.scan_label,
                        "relative_path": entry.relative_path,
                        "source_sha256": entry.source_sha256,
                        "cache_plan_sha256": entry.plan_sha256,
                        "cache_manifest_sha256": (
                            entry.cache_manifest_sha256
                        ),
                        "cache_payload_sha256": entry.payload_sha256,
                        "payload_nbytes": entry.payload_nbytes,
                    }
                    for entry in entries
                ],
                "planned_payload_nbytes": planned_payload_nbytes,
                "observed_peak_mapped_bytes": batch_peak_bytes,
                "observed_peak_handle_count": batch_peak_handles,
                "all_handles_closed_after_batch": True,
            }
        )
        self._next_width_ordinal += 1

    def seal(
        self,
        *,
        evidence_artifact_type: str,
        evidence_sha256: str,
    ) -> dict[str, Any]:
        """Bind complete stream accounting to one evidence product."""
        if self._sealed:
            raise core.V0P6IncompleteError("cache stream is already sealed")
        if self._active or self._invalid:
            raise core.V0P6IncompleteError(
                "cache stream is active or permanently invalid"
            )
        if self._next_width_ordinal != len(self.spectral_widths):
            raise core.V0P6IncompleteError(
                "cache stream cannot seal an incomplete width inventory"
            )
        if not isinstance(evidence_artifact_type, str) or not evidence_artifact_type:
            raise core.V0P6ContractError(
                "cache-stream evidence artifact type is invalid"
            )
        evidence_digest = core._frozen_sha256(
            evidence_sha256, "cache-stream evidence identity"
        )
        batch_bytes = core.canonical_json_bytes(self._batch_inventory)
        payload = {
            "artifact_type": STREAM_RESOURCE_ARTIFACT_TYPE,
            "schema_version": STREAM_RESOURCE_SCHEMA_VERSION,
            "detector_version": core.DETECTOR_VERSION,
            "run_id": self.manifest.run_id,
            "cache_run_manifest_file_sha256": (
                self.manifest.receipt.file_sha256
            ),
            "cache_run_inventory_sha256": (
                self.manifest.receipt.inventory_sha256
            ),
            "factor_bundle_manifest_sha256": (
                self.manifest.receipt.factor_bundle_manifest_sha256
            ),
            "window_id": self.window_id,
            "scan_kind": self.scan_kind,
            "scan_labels": list(self.scan_labels),
            "spectral_widths": list(self.spectral_widths),
            "batch_inventory": self._batch_inventory,
            "batch_inventory_sha256": hashlib.sha256(batch_bytes).hexdigest(),
            "batch_count": len(self._batch_inventory),
            "opened_cache_count": sum(
                item["cache_count"] for item in self._batch_inventory
            ),
            "maximum_mapped_bytes": self.maximum_mapped_bytes,
            "peak_mapped_bytes": self._peak_mapped_bytes,
            "peak_handle_count": self._peak_handle_count,
            "one_width_open_at_a_time": True,
            "all_widths_opened_exactly_once_in_order": True,
            "all_handles_closed_before_seal": True,
            "truncation_permitted": False,
            "evidence_artifact_type": evidence_artifact_type,
            "evidence_sha256": evidence_digest,
        }
        certificate = json.loads(core.canonical_json_bytes(payload))
        certificate["stream_resource_certificate_sha256"] = hashlib.sha256(
            core.canonical_json_bytes(payload)
        ).hexdigest()
        validate_stream_resource_certificate(
            certificate,
            expected_evidence_sha256=evidence_digest,
        )
        self._sealed = True
        return certificate


def validate_stream_resource_certificate(
    certificate: Mapping[str, Any],
    *,
    expected_certificate_sha256: str | None = None,
    expected_evidence_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate persisted width-stream accounting and evidence binding."""
    try:
        cert = json.loads(core.canonical_json_bytes(dict(certificate)))
    except (TypeError, ValueError) as error:
        raise core.V0P6ContractError(
            "cache-stream resource certificate is not canonical finite JSON"
        ) from error
    required_fields = {
        "artifact_type",
        "schema_version",
        "detector_version",
        "run_id",
        "cache_run_manifest_file_sha256",
        "cache_run_inventory_sha256",
        "factor_bundle_manifest_sha256",
        "window_id",
        "scan_kind",
        "scan_labels",
        "spectral_widths",
        "batch_inventory",
        "batch_inventory_sha256",
        "batch_count",
        "opened_cache_count",
        "maximum_mapped_bytes",
        "peak_mapped_bytes",
        "peak_handle_count",
        "one_width_open_at_a_time",
        "all_widths_opened_exactly_once_in_order",
        "all_handles_closed_before_seal",
        "truncation_permitted",
        "evidence_artifact_type",
        "evidence_sha256",
        "stream_resource_certificate_sha256",
    }
    if frozenset(cert) != frozenset(required_fields):
        raise core.V0P6ContractError(
            "cache-stream resource certificate fields differ from the schema"
        )
    observed_digest = core._frozen_sha256(
        cert.pop("stream_resource_certificate_sha256"),
        "cache-stream resource certificate identity",
    )
    calculated_digest = hashlib.sha256(
        core.canonical_json_bytes(cert)
    ).hexdigest()
    if observed_digest != calculated_digest:
        raise core.V0P6IncompleteError(
            "cache-stream resource certificate SHA-256 changed"
        )
    if expected_certificate_sha256 is not None and observed_digest != (
        core._frozen_sha256(
            expected_certificate_sha256,
            "expected cache-stream resource certificate identity",
        )
    ):
        raise core.V0P6ContractError(
            "cache-stream resource certificate differs from its receipt"
        )
    cert["stream_resource_certificate_sha256"] = observed_digest

    for name in (
        "cache_run_manifest_file_sha256",
        "cache_run_inventory_sha256",
        "factor_bundle_manifest_sha256",
        "batch_inventory_sha256",
        "evidence_sha256",
    ):
        core._frozen_sha256(cert[name], name.replace("_", "-"))
    if expected_evidence_sha256 is not None and cert["evidence_sha256"] != (
        core._frozen_sha256(
            expected_evidence_sha256,
            "expected cache-stream evidence identity",
        )
    ):
        raise core.V0P6ContractError(
            "cache-stream resource certificate binds different evidence"
        )
    if (
        cert["artifact_type"] != STREAM_RESOURCE_ARTIFACT_TYPE
        or core._strict_int(cert["schema_version"], "stream schema version")
        != STREAM_RESOURCE_SCHEMA_VERSION
        or cert["detector_version"] != core.DETECTOR_VERSION
        or cert["scan_kind"] not in {"on", "off"}
        or cert["one_width_open_at_a_time"] is not True
        or cert["all_widths_opened_exactly_once_in_order"] is not True
        or cert["all_handles_closed_before_seal"] is not True
        or cert["truncation_permitted"] is not False
    ):
        raise core.V0P6ContractError(
            "cache-stream resource semantics changed"
        )
    for name in ("run_id", "window_id", "evidence_artifact_type"):
        if not isinstance(cert[name], str) or not cert[name]:
            raise core.V0P6ContractError(
                f"cache-stream {name.replace('_', ' ')} is invalid"
            )

    raw_labels = cert["scan_labels"]
    if not isinstance(raw_labels, list):
        raise core.V0P6ContractError(
            "cache-stream scan labels must be a JSON array"
        )
    labels = tuple(raw_labels)
    if (
        not labels
        or any(not isinstance(label, str) or not label for label in labels)
        or len(set(labels)) != len(labels)
    ):
        raise core.V0P6ContractError(
            "cache-stream scan-label inventory is invalid"
        )
    widths = tuple(core._strict_widths(cert["spectral_widths"]))
    maximum_bytes = core._strict_int(
        cert["maximum_mapped_bytes"], "cache-stream mapped-byte cap"
    )
    peak_bytes = core._strict_int(
        cert["peak_mapped_bytes"], "cache-stream peak mapped bytes"
    )
    peak_handles = core._strict_int(
        cert["peak_handle_count"], "cache-stream peak handle count"
    )
    if (
        maximum_bytes < 1
        or peak_bytes < 0
        or peak_bytes > maximum_bytes
        or peak_handles < 0
        or peak_handles > len(labels)
    ):
        raise core.V0P6CapacityError(
            "cache-stream resource peaks exceed the certified capacity"
        )

    batches = cert["batch_inventory"]
    if not isinstance(batches, list):
        raise core.V0P6ContractError(
            "cache-stream batch inventory must be a JSON array"
        )
    if len(batches) != len(widths):
        raise core.V0P6IncompleteError(
            "cache-stream batch count differs from its width inventory"
        )
    batch_fields = {
        "width_ordinal",
        "spectral_width_channels",
        "scan_labels",
        "cache_count",
        "cache_receipts",
        "planned_payload_nbytes",
        "observed_peak_mapped_bytes",
        "observed_peak_handle_count",
        "all_handles_closed_after_batch",
    }
    cache_receipt_fields = {
        "scan_label",
        "relative_path",
        "source_sha256",
        "cache_plan_sha256",
        "cache_manifest_sha256",
        "cache_payload_sha256",
        "payload_nbytes",
    }
    observed_batch_peak_bytes = 0
    observed_batch_peak_handles = 0
    observed_relative_paths: set[str] = set()
    for ordinal, (batch, width) in enumerate(zip(batches, widths, strict=True)):
        if not isinstance(batch, dict) or frozenset(batch) != frozenset(
            batch_fields
        ):
            raise core.V0P6ContractError(
                "cache-stream batch fields differ from the schema"
            )
        batch_bytes = core._strict_int(
            batch["observed_peak_mapped_bytes"],
            "cache-stream batch peak mapped bytes",
        )
        batch_handles = core._strict_int(
            batch["observed_peak_handle_count"],
            "cache-stream batch peak handle count",
        )
        planned_bytes = core._strict_int(
            batch["planned_payload_nbytes"],
            "cache-stream planned batch payload bytes",
        )
        cache_receipts = batch["cache_receipts"]
        if (
            not isinstance(cache_receipts, list)
            or len(cache_receipts) != len(labels)
        ):
            raise core.V0P6IncompleteError(
                "cache-stream batch cache receipts are incomplete"
            )
        receipt_payload_nbytes = 0
        for label, cache_receipt in zip(
            labels, cache_receipts, strict=True
        ):
            relative_path = (
                cache_receipt.get("relative_path")
                if isinstance(cache_receipt, dict)
                else None
            )
            canonical_path = (
                PurePosixPath(relative_path)
                if isinstance(relative_path, str) and relative_path
                else None
            )
            if (
                not isinstance(cache_receipt, dict)
                or frozenset(cache_receipt)
                != frozenset(cache_receipt_fields)
                or cache_receipt["scan_label"] != label
                or canonical_path is None
                or canonical_path.is_absolute()
                or canonical_path.as_posix() != relative_path
                or any(
                    part in {"", ".", ".."} for part in canonical_path.parts
                )
                or relative_path in observed_relative_paths
            ):
                raise core.V0P6ContractError(
                    "cache-stream batch cache-receipt schema changed"
                )
            observed_relative_paths.add(relative_path)
            for digest_name in (
                "source_sha256",
                "cache_plan_sha256",
                "cache_manifest_sha256",
                "cache_payload_sha256",
            ):
                core._frozen_sha256(
                    cache_receipt[digest_name],
                    f"cache-stream {digest_name.replace('_', ' ')}",
                )
            payload_nbytes = core._strict_int(
                cache_receipt["payload_nbytes"],
                "cache-stream cache payload bytes",
            )
            if payload_nbytes < 1:
                raise core.V0P6ContractError(
                    "cache-stream cache payload bytes must be positive"
                )
            receipt_payload_nbytes += payload_nbytes
        if (
            core._strict_int(batch["width_ordinal"], "stream width ordinal")
            != ordinal
            or core._strict_int(
                batch["spectral_width_channels"], "stream spectral width"
            )
            != width
            or batch["scan_labels"] != list(labels)
            or core._strict_int(batch["cache_count"], "stream cache count")
            != len(labels)
            or planned_bytes < 1
            or receipt_payload_nbytes != planned_bytes
            or batch_bytes != planned_bytes
            or batch_bytes > maximum_bytes
            or batch_handles != len(labels)
            or batch["all_handles_closed_after_batch"] is not True
        ):
            raise core.V0P6IncompleteError(
                "cache-stream batch accounting is incomplete or inconsistent"
            )
        observed_batch_peak_bytes = max(
            observed_batch_peak_bytes, batch_bytes
        )
        observed_batch_peak_handles = max(
            observed_batch_peak_handles, batch_handles
        )
    if (
        core._strict_int(cert["batch_count"], "stream batch count")
        != len(widths)
        or core._strict_int(
            cert["opened_cache_count"], "stream opened-cache count"
        )
        != len(widths) * len(labels)
        or peak_bytes != observed_batch_peak_bytes
        or peak_handles != observed_batch_peak_handles
        or hashlib.sha256(core.canonical_json_bytes(batches)).hexdigest()
        != cert["batch_inventory_sha256"]
    ):
        raise core.V0P6IncompleteError(
            "cache-stream aggregate accounting is incomplete or inconsistent"
        )
    return json.loads(core.canonical_json_bytes(cert))


def open_m37_cache_width_stream(
    root: str | os.PathLike[str],
    manifest_path: str | os.PathLike[str],
    *,
    expected_manifest_file_sha256: str,
    expected_factor_bundle_manifest_sha256: str,
    window_id: str,
    scan_kind: str,
) -> CacheWidthStream:
    """Open the non-configurable M37 width stream under the 512-MiB cap."""
    if window_id not in core.M37_WINDOW_IDS:
        raise core.V0P6ContractError(
            "M37 cache stream received an unknown window"
        )
    if scan_kind == "on":
        labels = tuple(
            label
            for label in run_cache.M37_SCAN_LABELS
            if run_cache.M37_SCAN_KINDS[label] == "on"
        )
    elif scan_kind == "off":
        labels = tuple(
            label
            for label in run_cache.M37_SCAN_LABELS
            if run_cache.M37_SCAN_KINDS[label] == "off"
        )
    else:
        raise core.V0P6ContractError(
            "M37 cache-stream scan kind must be 'on' or 'off'"
        )
    return CacheWidthStream.from_manifest_file(
        root,
        manifest_path,
        expected_manifest_file_sha256=expected_manifest_file_sha256,
        expected_factor_bundle_manifest_sha256=(
            expected_factor_bundle_manifest_sha256
        ),
        expected_keys=run_cache.m37_cache_keys(),
        window_id=window_id,
        scan_kind=scan_kind,
        scan_labels=labels,
        spectral_widths=core.M37_SPECTRAL_WIDTHS,
        maximum_mapped_bytes=core.M37_LIVE_NDARRAY_CAP_BYTES,
    )
