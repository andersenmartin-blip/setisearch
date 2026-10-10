"""Once-only source-cell authenticity audit of all 18 fixed native-band patches.

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
COUNT = 1048576
CHUNKS = (158,)
SCRIPT_SHA = "b555254fe3ae14d1ad09169ce79060eae1cbb1b26406ea36a7093c452b288beb"
SCOPE_SHA = "2e3b2401d1295f0864d2a2e3f8030b5860c7352a6881e25dce81ff11a3f11c23"
FREEZE_COMMIT = "a8803167e7963a507454083bf116965253bfe83a"


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
    parser.add_argument("--root-go-after-both-complete", action="store_true", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    check(args.freeze_commit == FREEZE_COMMIT, "Exact public native-band freeze required")
    stage = root / "results/radio_native158_20261010"
    out = stage / "review"
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
        scope_path = root / "tools/radio_native158_20261010/scope.json"
        wrapper_path = root / "tools/radio_native158_20261010/native_search.py"
        check(digest(scope_path) == SCOPE_SHA and digest(wrapper_path) == SCRIPT_SHA,
              "Prospectively frozen native-band code/scope differs")
        scope = read_json(scope_path)
        check(scope["source_chunk_ids"] == list(CHUNKS), "Exact one native chunk required")
        metadata_pins = {scope_path: SCOPE_SHA, wrapper_path: SCRIPT_SHA}
        for name, sha in scope["pinned_dependency_files"].items():
            check(digest(root / name) == sha, "Pinned metadata/code differs: " + name)
            metadata_pins[root / name] = sha
        packages = {"numpy": "2.3.5", "h5py": "3.15.1", "hdf5plugin": "7.1.0"}
        for name, version in packages.items():
            check(importlib.metadata.version(name) == version, "Exact source codec package differs: " + name)
        contexts = []
        # Admit every acquisition and both COMPLETE/independent QA receipts before any H5 open.
        for chunk in CHUNKS:
            C0 = chunk * COUNT
            context = scope["chunk_contracts"][str(chunk)]
            source_path = root / context["source_manifest_path"]
            source = read_json(source_path)
            acquisition_path = root / context["acquisition_summary_path"]
            acquisition = read_json(acquisition_path)
            acquisition_sha = digest(acquisition_path)
            metadata_pins[acquisition_path] = acquisition_sha
            check(digest(source_path) == context["source_manifest_sha256"], "Exact native source manifest required")
            check(acquisition["status"] == "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
                  and acquisition["native_chunk_index"] == chunk and acquisition["source_channel0"] == C0
                  and acquisition["physical_channel_interval_half_open"] == [C0, C0 + COUNT]
                  and acquisition["scope_sha256"] == context["acquisition_scope_sha256"]
                  and acquisition["script_sha256"] == context["acquisition_script_sha256"]
                  and acquisition["source_manifest_sha256"] == context["source_manifest_sha256"],
                  "Exact completed acquisition required")
            compact_directory = stage / f"chunk{chunk}/arrays"
            acq_qa_path = compact_directory / "ACQUISITION_OUTPUT_QA_RECEIPT.json"
            acq_qa = read_json(acq_qa_path)
            metadata_pins[acq_qa_path] = digest(acq_qa_path)
            check(acq_qa["status"] == "PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS"
                  and acq_qa["source_chunk_id"] == chunk and acq_qa["freeze_commit"] == FREEZE_COMMIT
                  and acq_qa["acquisition_result_sha256"] == acquisition_sha
                  and acq_qa["common_two_batch_scope_sha256"] == SCOPE_SHA
                  and acq_qa["counts"] == {"source_requests": 96, "compact_files": 6,
                     "retained_compressed_chunks": 96, "decoded_rows": 96, "decoded_values_authenticated": 100663296},
                  "Exact completed acquisition independent QA required")
            decoded = acquisition["decoded_files"]
            check(len(decoded) == 6 and [r["scan_id"] for r in decoded] == list(SCANS)
                  and all(r["shape"] == [16, 1, COUNT] and r["source_channel0"] == C0
                          and [e["time_row"] for e in r["decoded_rows"]] == list(range(16)) for r in decoded),
                  "All six native compacts and96 row pins required")
            headers = {r["label"]: r for r in source["sources"]}
            anchor = min(r["current_header"]["data_attributes"]["tstart"] for r in source["sources"])
            check(tuple(headers) == SCANS, "Source scan order differs")
            families = []
            for batch in (1, 2):
                directory = stage / f"chunk{chunk}/batch_{batch:02d}/measurement"
                names = ("EXECUTION_RECEIPT.json", "DRIFT_TOP20.json", "FIXED_TOP3_PROFILES.json", "QA_RECEIPT.json", "INPUT_PINS.json")
                data = {name: read_json(directory / name) for name in names}
                file_shas = {name: digest(directory / name) for name in names}
                metadata_pins.update({directory / name: sha for name, sha in file_shas.items()})
                execution = data["EXECUTION_RECEIPT.json"]
                check(execution["status"] == "COMPLETE_127_NEW_NATIVE_CORE_BATCH_EXPLORATORY_ONLY"
                      and execution["source_chunk_id"] == chunk and execution["batch_id"] == batch
                      and execution["scope_sha256"] == SCOPE_SHA and execution["script_sha256"] == SCRIPT_SHA
                      and execution["acquisition_summary_sha256"] == acquisition_sha,
                      "Both original numeric batches must be complete and frozen")
                qa = data["QA_RECEIPT.json"]
                check(qa["status"] == "PASS_COMPLETE_SAVED_NATIVE_BATCH_OUTPUTS"
                      and qa["source_chunk_id"] == chunk and qa["batch_id"] == batch
                      and qa["freeze_commit"] == FREEZE_COMMIT and qa["public_scope_sha256"] == SCOPE_SHA
                      and qa["public_wrapper_sha256"] == SCRIPT_SHA
                      and qa["execution_receipt_sha256"] == file_shas["EXECUTION_RECEIPT.json"]
                      and qa["profile_JSON_sha256"] == file_shas["FIXED_TOP3_PROFILES.json"]
                      and qa["top20_sha256"] == file_shas["DRIFT_TOP20.json"]
                      and qa["INPUT_PINS_sha256"] == file_shas["INPUT_PINS.json"]
                      and qa["acquisition_summary_sha256"] == acquisition_sha
                      and qa["counts"] == {"maps": 381, "normalization_files": 381,
                         "carrier_maximum_records": 1560576, "top20_entries": 60, "patches": 9,
                         "scan_profiles": 54, "time_rows": 864, "retained_raw_patch_cells": 111456,
                         "binary_and_normalization_hashes": 771},
                      "Both independent saved-output QAs must be exact complete inputs")
                check(data["INPUT_PINS.json"]["compact_files_and_96_decoded_row_pins"] == decoded,
                      "Runtime compact and96 row pins differ")
                records = data["FIXED_TOP3_PROFILES.json"]
                tops = data["DRIFT_TOP20.json"]
                check(set(tops) == set(ONS) and all(len(tops[s]) == 20 for s in ONS)
                      and len(records) == 9 and [r["selected_track"] for r in records]
                      == [t for scan in ONS for t in tops[scan][:3]], "Exact nine fixed top3 patches required")
                families.append((batch, directory, records, file_shas["EXECUTION_RECEIPT.json"], file_shas["FIXED_TOP3_PROFILES.json"]))
            contexts.append((chunk, C0, acquisition, headers, anchor, compact_directory, families))

        import numpy as np
        import h5py
        import hdf5plugin  # Register the same exact source filter as prior stages.
        check(h5py.version.hdf5_version == "1.14.6", "Exact bundled HDF5 version differs")
        compact_pins = {}
        for chunk, C0, acquisition, headers, anchor, compact_directory, families in contexts:
          arrays = {}
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
            compact_pins[path] = observed_sha
            source_checks.append({"source_chunk_id": chunk, "scan_id": scan, "file_sha256": observed_sha,
                                  "bytes": path.stat().st_size, "decoded_rows_checked": 16})
            counts["compact_files"] += 1
          check(tuple(arrays) == SCANS, "Exactly six decoded source compacts required")

          offsets = np.arange(-64, 65)
          for batch, directory, records, execution_sha, profiles_sha in families:
            for record in records:
                track = record["selected_track"]
                check(track["source_chunk_id"] == chunk and track["batch_id"] == batch and record["fixed_frequency_shift_channels"] == 0,
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
                metadata_pins[patch] = record["patch"]["sha256"]
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
                patch_checks.append({"source_chunk_id": chunk, "batch_id": batch, "track_id": track["track_id"],
                                     "raw_cells": raw_power.size, "patch_sha256": record["patch"]["sha256"],
                                     "raw_cell_bytes_SHA256": hashlib.sha256(observed_bytes).hexdigest(),
                                     "independent_source_cell_bytes_SHA256": hashlib.sha256(expected_bytes).hexdigest(),
                                     "source_execution_receipt_sha256": execution_sha,
                                     "source_profiles_JSON_sha256": profiles_sha,
                                     "bitwise_identical": True})
                counts["patches"] += 1; counts["scan_profiles"] += 6; counts["time_rows"] += 96
                counts["raw_cells_bitwise_checked"] += raw_power.size
          del arrays
        check(counts == {"compact_files": 6, "decoded_rows": 96, "patches": 18,
                         "scan_profiles": 108, "time_rows": 1728, "raw_cells_bitwise_checked": 222912},
              "Joint18-patch source-cell audit is incomplete")
        check(digest(scope_path) == SCOPE_SHA and digest(wrapper_path) == SCRIPT_SHA,
              "Frozen code/scope changed during source audit")
        for path, sha in {**metadata_pins, **compact_pins}.items():
            check(digest(path) == sha, "Authenticated inputs changed during source-cell QA: " + str(path))
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
                    "wall_seconds": time.monotonic() - started,
                    "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(measured["process_CPU_seconds_including_imports"] <= CPU_CAP
              and measured["wall_seconds"] <= WALL_CAP and measured["peak_RSS_bytes"] <= MEMORY_CAP,
              "Measured source-cell QA resource cap exceeded")
        receipt = {"status": "PASS_18_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE",
                   "source_chunk_ids": list(CHUNKS), "profile_identity_fields": ["source_chunk_id", "batch_id", "track_id"],
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
