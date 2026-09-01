#!/usr/bin/env python3
"""Restartable physical disposition for the amended M37 Run 006.

The committed Run 006 cache manifest can be reconstructed from a deterministic
cache replay because its ordered entry inventory is run independent.  This
controller requires the reconstructed manifest to reproduce the exact
committed file SHA-256 before any physical child is accepted.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
for item in (str(ROOT / "src"), str(ROOT / "scripts")):
    if item not in sys.path:
        sys.path.insert(0, item)

import m37_v0p6_primary as primary
from seti_repeater import cache_manifest_v0p6 as cache_manifest
from seti_repeater import capacity_v0p6p1 as capacity
from seti_repeater import physical_disposition_manifest_v0p6 as run_manifest
from seti_repeater import physical_v0p6p1 as physical
from seti_repeater import search_v0p6 as core
from seti_repeater.cache_stream_v0p6 import CacheWidthStream


PHYSICAL_DIRECTORY = "physical-disposition"
PHYSICAL_MANIFEST_PATH = "physical-disposition-manifest.json"
RECONSTRUCTED_CACHE_MANIFEST_PATH = "official-cache-run-manifest.json"


def _canonical_artifact_bytes(path: Path, maximum_bytes: int) -> bytes:
    if path.is_file():
        raw = path.read_bytes()
    else:
        compressed = Path(f"{path}.gz")
        if not compressed.is_file():
            raise core.V0P6IncompleteError(
                f"artifact is absent: {path}"
            )
        with gzip.open(compressed, "rb") as stream:
            raw = stream.read(maximum_bytes + 1)
    if len(raw) > maximum_bytes:
        raise core.V0P6CapacityError(
            f"artifact exceeds its byte cap: {path.name}"
        )
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise core.V0P6ContractError(
            f"artifact is invalid JSON: {path.name}"
        ) from error
    if core.canonical_json_bytes(parsed) != raw:
        raise core.V0P6ContractError(
            f"artifact is not canonical JSON: {path.name}"
        )
    return raw


def _load_retention(
    run_root: Path,
    run_record: Mapping[str, Any],
    window_id: str,
    kind: str,
    profile: capacity.M37V0P6P1CapacityProfile,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    receipt = run_record["artifacts"][f"retention_{kind}"]["windows"][
        window_id
    ]
    path = run_root / receipt["path"]
    raw = _canonical_artifact_bytes(
        path,
        profile.maximum_retention_evidence_canonical_bytes_per_window
        + 16_777_216,
    )
    if hashlib.sha256(raw).hexdigest() != receipt["file_sha256"]:
        raise core.V0P6IncompleteError(
            f"{window_id} {kind.upper()} retention file identity changed"
        )
    artifact = json.loads(raw)
    if set(artifact) != {"artifact_type", "records", "certificate"}:
        raise core.V0P6ContractError("retention artifact schema changed")
    records = artifact["records"]
    if not isinstance(records, list) or len(records) != receipt["record_count"]:
        raise core.V0P6IncompleteError("retention record count changed")
    certificate = physical.validate_m37_v0p6p1_retention_certificate(
        artifact["certificate"],
        profile,
        expected_kind=kind,
        expected_certificate_sha256=receipt["certificate_sha256"],
    )
    return records, certificate


def reconstruct_official_cache_manifest(
    cache_root: Path,
    official_record: Mapping[str, Any],
) -> tuple[Path, cache_manifest.CacheRunManifest]:
    """Reproduce the exact Run 006 manifest from replayed cache entries."""
    replay_record = primary._read_canonical(
        cache_root / primary.CONTROLLER_PATH
    )
    replay_bundle = primary._bundle(cache_root, replay_record)
    replay_manifest = primary._open_manifest(
        cache_root, replay_record, replay_bundle
    )
    replay_manifest_path = cache_root / primary.CACHE_MANIFEST_PATH
    manifest_record = primary._read_canonical(replay_manifest_path)
    official_cache = official_record["artifacts"]["cache_manifest"]
    if (
        replay_manifest.receipt.inventory_sha256
        != official_cache["inventory_sha256"]
        or replay_manifest.receipt.entry_count != official_cache["entry_count"]
        or replay_manifest.receipt.payload_nbytes
        != official_cache["payload_nbytes"]
    ):
        raise core.V0P6IncompleteError(
            "cache replay does not reproduce the official Run 006 inventory"
        )
    manifest_record["factor_bundle_manifest_sha256"] = official_record[
        "bootstrap"
    ]["factor_bundle_manifest_sha256"]
    official_path = cache_root / RECONSTRUCTED_CACHE_MANIFEST_PATH
    observed_sha256 = primary._publish_or_verify(
        official_path, manifest_record
    )
    if observed_sha256 != official_cache["file_sha256"]:
        raise core.V0P6IncompleteError(
            "reconstructed cache manifest does not reproduce Run 006 bytes"
        )
    opened = cache_manifest.open_cache_run_manifest(
        official_path,
        expected_file_sha256=official_cache["file_sha256"],
        expected_factor_bundle_manifest_sha256=official_record["bootstrap"][
            "factor_bundle_manifest_sha256"
        ],
        expected_keys=cache_manifest.m37_cache_keys(),
    )
    verified = cache_manifest.verify_cache_run_files(cache_root, opened)
    if verified != official_cache["verified_inventory_sha256"]:
        raise core.V0P6IncompleteError(
            "replayed cache payloads do not reproduce official verification"
        )
    return official_path, opened


def _streams(
    cache_root: Path,
    manifest: cache_manifest.CacheRunManifest,
    official_record: Mapping[str, Any],
    window_id: str,
    profile: capacity.M37V0P6P1CapacityProfile,
) -> tuple[CacheWidthStream, CacheWidthStream]:
    labels = {
        kind: tuple(
            label
            for label in cache_manifest.M37_SCAN_LABELS
            if cache_manifest.M37_SCAN_KINDS[label] == kind
        )
        for kind in ("on", "off")
    }
    official_cache = official_record["artifacts"]["cache_manifest"]

    def make(kind: str) -> CacheWidthStream:
        return CacheWidthStream(
            cache_root,
            manifest,
            expected_manifest_file_sha256=official_cache["file_sha256"],
            expected_inventory_sha256=official_cache["inventory_sha256"],
            expected_factor_bundle_manifest_sha256=official_record[
                "bootstrap"
            ]["factor_bundle_manifest_sha256"],
            expected_keys=cache_manifest.m37_cache_keys(),
            window_id=window_id,
            scan_kind=kind,
            scan_labels=labels[kind],
            spectral_widths=core.M37_SPECTRAL_WIDTHS,
            maximum_mapped_bytes=profile.maximum_live_ndarray_bytes,
        )

    return make("on"), make("off")


def _open_existing_child(
    run_root: Path,
    official_record: Mapping[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    window_id: str,
    on_certificate_sha256: str,
):
    relative = f"{PHYSICAL_DIRECTORY}/{window_id}.json"
    path = run_root / relative
    raw = _canonical_artifact_bytes(
        path,
        physical.M37_V0P6P1_PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES,
    )
    result = json.loads(raw)
    certificate_sha256 = result["certificate"][
        "physical_disposition_certificate_sha256"
    ]
    opened = physical.open_m37_v0p6p1_physical_disposition_artifact(
        path,
        profile,
        expected_file_sha256=hashlib.sha256(raw).hexdigest(),
        expected_physical_disposition_certificate_sha256=(
            certificate_sha256
        ),
        expected_run_id=official_record["run_id"],
        expected_window_id=window_id,
        expected_cache_run_manifest_file_sha256=official_record["artifacts"][
            "cache_manifest"
        ]["file_sha256"],
        expected_factor_bundle_manifest_sha256=official_record["bootstrap"][
            "factor_bundle_manifest_sha256"
        ],
        expected_on_retention_certificate_sha256=on_certificate_sha256,
    )
    return run_manifest.make_physical_disposition_run_entry(relative, opened)


def dispose_window(
    run_root_text: str,
    cache_root_text: str,
    official_manifest_text: str,
    window_id: str,
) -> dict[str, Any]:
    run_root = Path(run_root_text)
    cache_root = Path(cache_root_text)
    official_manifest_path = Path(official_manifest_text)
    official_record = primary._status(run_root)
    profile = capacity.validate_m37_v0p6p1_capacity_profile_record(
        official_record["capacity_amendment"]
    )
    on_records, on_certificate = _load_retention(
        run_root, official_record, window_id, "on", profile
    )
    on_certificate_sha256 = on_certificate["retention_certificate_sha256"]
    path = run_root / PHYSICAL_DIRECTORY / f"{window_id}.json"
    if path.exists() or Path(f"{path}.gz").exists():
        entry = _open_existing_child(
            run_root,
            official_record,
            profile,
            window_id,
            on_certificate_sha256,
        )
        return {"entry": entry.as_record(), "reused": True}

    off_records, off_certificate = _load_retention(
        run_root, official_record, window_id, "off", profile
    )
    official_cache = official_record["artifacts"]["cache_manifest"]
    manifest = cache_manifest.open_cache_run_manifest(
        official_manifest_path,
        expected_file_sha256=official_cache["file_sha256"],
        expected_factor_bundle_manifest_sha256=official_record["bootstrap"][
            "factor_bundle_manifest_sha256"
        ],
        expected_keys=cache_manifest.m37_cache_keys(),
    )
    replay_record = primary._read_canonical(
        cache_root / primary.CONTROLLER_PATH
    )
    bundle = primary._bundle(cache_root, replay_record)
    grid = core.make_m37_proxy_carrier_grid(window_id)
    on_stream, off_stream = _streams(
        cache_root, manifest, official_record, window_id, profile
    )
    evidence = physical.execute_m37_v0p6p1_physical_evidence_streams(
        profile,
        on_records,
        on_certificate,
        on_stream,
        off_stream,
        bundle.scans,
        bundle.basis,
        bundle.table,
        grid,
        expected_on_retention_certificate_sha256=on_certificate_sha256,
    )
    off_result = physical.match_m37_v0p6p1_retained_off_tracks(
        profile,
        on_records,
        on_certificate,
        off_records,
        off_certificate,
        bundle.basis,
        bundle.table,
        bundle.scans,
        expected_on_certificate_sha256=on_certificate_sha256,
        expected_off_certificate_sha256=off_certificate[
            "retention_certificate_sha256"
        ],
    )
    receiver_result = evidence["receiver_result"]
    receiver_certificate = receiver_result["certificate"]
    adjacent_result = evidence["adjacent_result"]
    adjacent_certificate = adjacent_result["certificate"]
    off_match_certificate = off_result["certificate"]
    alias_result = physical.match_m37_v0p6p1_receiver_frame_aliases(
        profile,
        off_result["records"],
        on_certificate,
        bundle.basis,
        bundle.table,
        bundle.scans,
        receiver_result,
        off_match_certificate=off_match_certificate,
        single_adjacent_off_evidence=adjacent_result["evidence"],
        single_adjacent_off_certificate=adjacent_certificate,
        expected_off_match_certificate_sha256=off_match_certificate[
            "off_match_certificate_sha256"
        ],
        expected_single_adjacent_off_certificate_sha256=(
            adjacent_certificate[
                "single_adjacent_off_certificate_sha256"
            ]
        ),
        expected_receiver_signature_certificate_sha256=(
            receiver_certificate[
                "receiver_signature_certificate_sha256"
            ]
        ),
        expected_on_certificate_sha256=on_certificate_sha256,
    )
    result = physical.seal_m37_v0p6p1_physical_disposition_result(
        profile,
        evidence,
        off_result,
        alias_result,
        expected_physical_evidence_execution_result_sha256=evidence[
            "execution_result_sha256"
        ],
        expected_off_match_certificate_sha256=off_match_certificate[
            "off_match_certificate_sha256"
        ],
        expected_receiver_alias_certificate_sha256=alias_result[
            "certificate"
        ]["receiver_alias_certificate_sha256"],
    )
    certificate_sha256 = result["certificate"][
        "physical_disposition_certificate_sha256"
    ]
    receipt = physical.publish_m37_v0p6p1_physical_disposition_artifact(
        path,
        result,
        profile,
        expected_physical_disposition_certificate_sha256=(
            certificate_sha256
        ),
    )
    opened = physical.open_m37_v0p6p1_physical_disposition_artifact(
        path,
        profile,
        expected_file_sha256=receipt.file_sha256,
        expected_physical_disposition_certificate_sha256=(
            receipt.physical_disposition_certificate_sha256
        ),
        expected_run_id=official_record["run_id"],
        expected_window_id=window_id,
        expected_cache_run_manifest_file_sha256=(
            official_cache["file_sha256"]
        ),
        expected_factor_bundle_manifest_sha256=official_record["bootstrap"][
            "factor_bundle_manifest_sha256"
        ],
        expected_on_retention_certificate_sha256=on_certificate_sha256,
    )
    entry = run_manifest.make_physical_disposition_run_entry(
        f"{PHYSICAL_DIRECTORY}/{window_id}.json", opened
    )
    return {"entry": entry.as_record(), "reused": False}


def finalize(
    run_root: Path,
    official_record: dict[str, Any],
    profile: capacity.M37V0P6P1CapacityProfile,
    entries: tuple[run_manifest.PhysicalDispositionRunEntry, ...],
) -> dict[str, Any]:
    retention_inventory_sha256 = run_manifest.on_retention_inventory_sha256(
        entries
    )
    path = run_root / PHYSICAL_MANIFEST_PATH
    if path.exists():
        raw = _canonical_artifact_bytes(
            path, run_manifest.PHYSICAL_DISPOSITION_RUN_MANIFEST_MAXIMUM_BYTES
        )
        parsed = json.loads(raw)
        manifest_receipt = (
            physical.open_m37_v0p6p1_physical_disposition_run_manifest(
                path,
                profile,
                expected_file_sha256=hashlib.sha256(raw).hexdigest(),
                expected_manifest_sha256=parsed["manifest_sha256"],
                expected_run_id=official_record["run_id"],
                expected_cache_run_manifest_file_sha256=official_record[
                    "artifacts"
                ]["cache_manifest"]["file_sha256"],
                expected_factor_bundle_manifest_sha256=official_record[
                    "bootstrap"
                ]["factor_bundle_manifest_sha256"],
                expected_on_retention_inventory_sha256=(
                    retention_inventory_sha256
                ),
            ).receipt
        )
    else:
        manifest_receipt = (
            physical.publish_m37_v0p6p1_physical_disposition_run_manifest(
                path,
                entries,
                profile,
                expected_run_id=official_record["run_id"],
                expected_cache_run_manifest_file_sha256=official_record[
                    "artifacts"
                ]["cache_manifest"]["file_sha256"],
                expected_factor_bundle_manifest_sha256=official_record[
                    "bootstrap"
                ]["factor_bundle_manifest_sha256"],
                expected_on_retention_inventory_sha256=(
                    retention_inventory_sha256
                ),
            )
        )
    if official_record["stage"] == "off_retention_complete":
        journal = (
            physical.advance_m37_v0p6p1_physical_disposition_from_manifest(
                run_root / "run.journal.jsonl",
                profile,
                expected_head_sha256=official_record[
                    "journal_head_sha256"
                ],
                manifest_path=path,
                expected_manifest_file_sha256=manifest_receipt.file_sha256,
                expected_manifest_sha256=manifest_receipt.manifest_sha256,
                expected_run_id=official_record["run_id"],
                expected_cache_run_manifest_file_sha256=official_record[
                    "artifacts"
                ]["cache_manifest"]["file_sha256"],
                expected_factor_bundle_manifest_sha256=official_record[
                    "bootstrap"
                ]["factor_bundle_manifest_sha256"],
                expected_on_retention_inventory_sha256=(
                    retention_inventory_sha256
                ),
            )
        )
        official_record = dict(official_record)
        official_record["stage"] = journal.stage
        official_record["journal_head_sha256"] = journal.head_sha256
        artifacts = dict(official_record["artifacts"])
        artifacts["physical_disposition"] = manifest_receipt.__dict__
        official_record["artifacts"] = artifacts
        primary._write_controller(run_root, official_record)
    return primary._status(run_root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3, choices=range(1, 5))
    parser.add_argument(
        "--windows",
        nargs="+",
        choices=core.M37_WINDOW_IDS,
        default=core.M37_WINDOW_IDS,
    )
    args = parser.parse_args()
    official_record = primary._status(args.run_root)
    if official_record["stage"] not in {
        "off_retention_complete",
        "physical_disposition_complete",
    }:
        raise core.V0P6IncompleteError(
            "physical disposition requires complete ON/OFF retention"
        )
    profile = capacity.validate_m37_v0p6p1_capacity_profile_record(
        official_record["capacity_amendment"]
    )
    official_manifest_path, _ = reconstruct_official_cache_manifest(
        args.cache_root, official_record
    )
    (args.run_root / PHYSICAL_DIRECTORY).mkdir(exist_ok=True)
    selected = tuple(args.windows)
    results: dict[str, run_manifest.PhysicalDispositionRunEntry] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                dispose_window,
                str(args.run_root),
                str(args.cache_root),
                str(official_manifest_path),
                window_id,
            ): window_id
            for window_id in selected
        }
        for future in as_completed(futures):
            window_id = futures[future]
            value = future.result()
            entry = run_manifest.PhysicalDispositionRunEntry(
                **value["entry"]
            )
            results[window_id] = entry
            primary._emit_progress(
                "physical_disposition_window_complete",
                window_id=window_id,
                final_record_count=sum(
                    entry.final_disposition_counts.values()
                ),
                reused=value["reused"],
            )
    if selected != core.M37_WINDOW_IDS:
        print(
            core.canonical_json_bytes(
                {
                    "stage": "partial_physical_disposition",
                    "completed_windows": sorted(results),
                }
            ).decode(),
            flush=True,
        )
        return
    entries = tuple(results[window_id] for window_id in core.M37_WINDOW_IDS)
    result = finalize(args.run_root, official_record, profile, entries)
    print(core.canonical_json_bytes(result).decode(), flush=True)


if __name__ == "__main__":
    main()
