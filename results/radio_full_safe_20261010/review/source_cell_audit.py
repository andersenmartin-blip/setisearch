"""Once-only source-cell authenticity audit of all 18 fixed full-safe patches.

After explicit GO and both completed batches, decode each exact compact once,
verify its file identity and all 96 source-row identities, independently rebuild
the frozen native-channel geometry, and compare every saved raw cell bitwise.
No search, scoring, normalization, ranking, profile optimization or HTTP occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import signal
import time

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

CPU_CAP, WALL_CAP, MEMORY_CAP = 20, 120, 4 * 1024**3
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
C0, COUNT = 158334976, 1048576
SCRIPT_SHA = "8758f48de05e139431196c958c9e20b4bd6c24200fc57906245cc91ac4cfe56f"
SCOPE_SHA = "1e77f78f5c957082da3eebdb1c70641b6ba7687ce2996578ccb5a9caf0287d22"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "results/radio_full_safe_20261010/review"
    receipt_path = out / "SOURCE_CELL_QA_RECEIPT.json"
    failure_path = out / "SOURCE_CELL_QA_FAILURE_RECEIPT.json"
    lock_path = out / "SOURCE_CELL_QA_STARTED.json"
    check(not receipt_path.exists() and not failure_path.exists() and not lock_path.exists(),
          "This joint source-cell audit is authorized once only")
    with lock_path.open("x") as stream:
        json.dump({"status": "STARTED_ONCE_ONLY_SOURCE_CELL_QA", "freeze_commit": args.freeze_commit,
                   "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
                   "script_sha256": digest(Path(__file__))}, stream, indent=2)
        stream.write("\n")

    def deadline(signum, frame):
        raise TimeoutError("Source-cell audit CPU/wall limit")

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    counts = {"compact_files": 0, "decoded_rows": 0, "patches": 0,
              "scan_profiles": 0, "time_rows": 0, "raw_cells_bitwise_checked": 0}
    source_checks, patch_checks = [], []
    try:
        scope_path = root / "tools/radio_full_safe_20261010/scope.json"
        wrapper_path = root / "tools/radio_full_safe_20261010/full_safe_search.py"
        check(digest(scope_path) == SCOPE_SHA and digest(wrapper_path) == SCRIPT_SHA,
              "Prospectively frozen full-safe code/scope differs")
        scope = read_json(scope_path)
        for name, sha in scope["pinned_dependency_files"].items():
            check(digest(root / name) == sha, "Pinned metadata/code differs: " + name)
        packages = {"numpy": "2.3.5", "h5py": "3.15.1", "hdf5plugin": "7.1.0"}
        for name, version in packages.items():
            check(importlib.metadata.version(name) == version, "Exact source codec package differs: " + name)
        import numpy as np
        import h5py
        import hdf5plugin  # Register the same exact source filter as prior stages.

        source = read_json(root / "tools/radio_fresh_band_20261009/source_manifest.json")
        acquisition = read_json(root / "results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json")
        check(acquisition["decoded_files"] == scope["compact_files_and_96_decoded_row_pins"],
              "Source compact/row pins differ from public common scope")
        headers = {r["label"]: r for r in source["sources"]}
        anchor = min(r["current_header"]["data_attributes"]["tstart"] for r in source["sources"])
        check(tuple(headers) == SCANS, "Source scan order differs")
        families = []
        for batch in (1, 2):
            directory = root / f"results/radio_full_safe_20261010/batch_{batch:02d}/measurement"
            execution_path = directory / "EXECUTION_RECEIPT.json"
            execution = read_json(execution_path)
            check(execution["status"] == "COMPLETE_107_FULL_SAFE_CORE_BATCH_EXPLORATORY_ONLY"
                  and execution["batch_id"] == batch and execution["scope_sha256"] == SCOPE_SHA
                  and execution["script_sha256"] == SCRIPT_SHA,
                  "Both original numeric batches must be complete and frozen")
            tops = read_json(directory / "DRIFT_TOP20.json")
            profiles_path = directory / "FIXED_TOP3_PROFILES.json"
            records = read_json(profiles_path)
            check(len(records) == 9 and [r["selected_track"] for r in records]
                  == [t for scan in ONS for t in tops[scan][:3]], "Exact nine fixed top3 patches required")
            families.append((batch, directory, records, digest(execution_path), digest(profiles_path)))

        arrays = {}
        compact_directory = root / "results/radio_fresh_band_20261009/arrays"
        for record in acquisition["decoded_files"]:
            scan = record["scan_id"]
            path = compact_directory / record["array_file"]
            check(path.resolve().is_relative_to(compact_directory.resolve()), "Compact filename escapes pinned directory")
            observed_sha = digest(path)
            check(observed_sha == record["file_sha256"] and path.stat().st_size == record["bytes"],
                  "Exact compact file identity differs")
            item = headers[scan]
            with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as handle:
                dataset = handle["data"]
                check(dataset.shape == (16, 1, COUNT) and dataset.dtype == np.dtype("<f4"),
                      "Exact compact source schema differs")
                check(int(dataset.attrs["original_source_frequency_chunk_origin"]) == C0
                      and dataset.attrs["original_source_url"] == item["url"]
                      and dataset.attrs["original_source_etag"] == item["etag"],
                      "Retained compact source provenance differs")
                arrays[scan] = dataset[:, 0, :]  # Exactly one full decode per compact file.
            check(np.isfinite(arrays[scan]).all() and (arrays[scan] >= 0).all(), "Invalid source power")
            check([r["time_row"] for r in record["decoded_rows"]] == list(range(16)), "Exactly16 source-row pins required")
            for row, evidence in enumerate(record["decoded_rows"]):
                raw = arrays[scan][row].tobytes(order="C")
                check(len(raw) == evidence["decoded_bytes"] == COUNT * 4
                      and hashlib.sha256(raw).hexdigest() == evidence["decoded_sha256"],
                      "Decoded compact row identity differs")
                counts["decoded_rows"] += 1
            source_checks.append({"scan_id": scan, "file_sha256": observed_sha,
                                  "bytes": path.stat().st_size, "decoded_rows_checked": 16})
            counts["compact_files"] += 1
        check(tuple(arrays) == SCANS, "Exactly six decoded source compacts required")

        offsets = np.arange(-64, 65)
        for batch, directory, records, execution_sha, profiles_sha in families:
            for record in records:
                track = record["selected_track"]
                check(track["batch_id"] == batch and record["fixed_frequency_shift_channels"] == 0,
                      "Frozen track identity/shift differs")
                fch1 = scope["fch1_hz"]; df = scope["df_hz"]; tsamp = scope["tsamp_s"]
                check(track["reference_frequency_hz"] == fch1 + df * int(track["source_reference_channel"]),
                      "Frozen scalar source frequency differs")
                dt = np.asarray([(headers[scan]["current_header"]["data_attributes"]["tstart"] - anchor) * 86400
                                 + (np.arange(16) + .5) * tsamp - track["reference_seconds_from_anchor"]
                                 for scan in SCANS])
                base = (track["reference_frequency_hz"] - fch1) / df
                centers = np.rint(base + track["drift_hz_s"] * dt / df).astype(np.int64)
                indices = centers[:, :, None] - C0 + offsets[None, None, :]
                check(indices.min() >= 0 and indices.max() < COUNT, "Independent source-cell geometry is out of bounds")
                patch = directory / record["patch"]["path"]
                check(patch.resolve().is_relative_to(directory.resolve())
                      and patch.stat().st_size == record["patch"]["bytes"]
                      and digest(patch) == record["patch"]["sha256"], "Saved patch file identity differs")
                with np.load(patch, allow_pickle=False) as saved:
                    raw_power = saved["raw_power"]
                    check(np.array_equal(saved["scans"], np.asarray(SCANS))
                          and np.array_equal(saved["source_channel_offsets"], offsets)
                          and np.array_equal(saved["frozen_source_channel_centers"], centers)
                          and np.array_equal(saved["times_seconds_from_reference"], dt),
                          "Saved patch native geometry differs from independent reconstruction")
                expected = np.asarray([arrays[scan][np.arange(16)[:, None], indices[i]]
                                       for i, scan in enumerate(SCANS)])
                check(raw_power.dtype == expected.dtype == np.dtype("<f4")
                      and raw_power.shape == expected.shape == (6, 16, 129), "Raw cell dtype/shape differs")
                expected_bytes = expected.tobytes(order="C")
                observed_bytes = raw_power.tobytes(order="C")
                check(observed_bytes == expected_bytes, "Saved raw power differs bitwise from authenticated source cells")
                patch_checks.append({"batch_id": batch, "track_id": track["track_id"],
                                     "raw_cells": raw_power.size, "patch_sha256": record["patch"]["sha256"],
                                     "raw_cell_bytes_SHA256": hashlib.sha256(observed_bytes).hexdigest(),
                                     "independent_source_cell_bytes_SHA256": hashlib.sha256(expected_bytes).hexdigest(),
                                     "source_execution_receipt_sha256": execution_sha,
                                     "source_profiles_JSON_sha256": profiles_sha,
                                     "bitwise_identical": True})
                counts["patches"] += 1; counts["scan_profiles"] += 6; counts["time_rows"] += 96
                counts["raw_cells_bitwise_checked"] += raw_power.size
        check(counts == {"compact_files": 6, "decoded_rows": 96, "patches": 18,
                         "scan_profiles": 108, "time_rows": 1728, "raw_cells_bitwise_checked": 222912},
              "Joint18-patch source-cell audit is incomplete")
        check(digest(scope_path) == SCOPE_SHA and digest(wrapper_path) == SCRIPT_SHA,
              "Frozen code/scope changed during source audit")
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
                    "wall_seconds": time.monotonic() - started,
                    "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(measured["process_CPU_seconds_including_imports"] <= CPU_CAP
              and measured["wall_seconds"] <= WALL_CAP and measured["peak_RSS_bytes"] <= MEMORY_CAP,
              "Measured source-cell QA resource cap exceeded")
        receipt = {"status": "PASS_18_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE",
                   "freeze_commit": args.freeze_commit, "audit_script_sha256": digest(Path(__file__)),
                   "public_scope_sha256": SCOPE_SHA, "public_wrapper_sha256": SCRIPT_SHA,
                   "runtime_package_versions": packages,
                   "runtime_package_paths": {"numpy": np.__file__, "h5py": h5py.__file__, "hdf5plugin": hdf5plugin.__file__},
                   "counts": counts, "source_checks": source_checks, "patch_checks": patch_checks,
                   "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
                   **measured, "source_HDF5_files_read_once": 6,
                   "source_HDF5_decoded_rows": 96, "detector_or_score_runs": 0,
                   "profile_optimization_or_new_measurement_runs": 0,
                   "new_HTTP_requests": 0, "new_SOURCE_BODY_bytes": 0,
                   "geometry_operation": "Reconstruct exact frozen absolute-source rounding and header times only; gather reference cells for bitwise QA.",
                   "scientific_limit": "Confirms retained raw-cell authenticity and alignment; one selected historical visit, no calibrated significance or origin validation."}
        save(receipt_path, receipt)
        print(json.dumps({"status": receipt["status"], "counts": counts, **measured,
                          "receipt_path": str(receipt_path), "receipt_sha256": digest(receipt_path)}, allow_nan=False), flush=True)
    except BaseException as exc:
        save(failure_path, {"status": "SOURCE_CELL_QA_INCOMPLETE_OR_FAILED_NO_RETRY",
                            "error_type": type(exc).__name__, "error": str(exc), "partial_counts": counts,
                            "process_CPU_seconds_including_imports": time.process_time(),
                            "wall_seconds": time.monotonic() - started,
                            "retry_authorized": False, "detector_or_score_runs": 0})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
