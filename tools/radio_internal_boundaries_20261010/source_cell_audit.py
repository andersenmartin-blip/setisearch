"""Once-only streamed source-cell authentication for27 joined-boundary patches.

After all three frozen numerical families and saved QAs pass, authenticate each
of30 unique native compacts and480 rows once using the unchanged source loader.
Gather only the fixed absolute-channel cells into small expected-patch buffers.
No detector, ranking, profile projection, source median, or HTTP is rerun.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import resource
import signal
import time
from types import SimpleNamespace

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"

CPU_CAP, WALL_CAP, MEMORY_CAP = 60, 300, 4 * 1024**3
SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
ONS = SCANS[::2]
PAIRS = {"pair153_154": (153, 154), "pair154_155": (154, 155), "pair157_158": (157, 158)}
CHUNKS, N = (153, 154, 155, 157, 158), 1048576
FCH1, DF, TSAMP = 1876464843.75, -2.835503418452676, 17.986224128
FRESH_PATH = "tools/radio_fresh_band_20261009/fresh_search.py"
FRESH_SHA = "1a04ab1ea0d8b79b66ebc2a59a5c72b9c17b235f1a331ac19efeba90bade7102"
RESULTS = "results/radio_internal_boundaries_20261010"
QA_COUNTS = {"maps": 6, "normalization_files": 6, "carrier_maximum_records": 24576,
             "top20_entries": 60, "patches": 9, "scan_profiles": 54, "time_rows": 864,
             "retained_raw_patch_cells": 111456, "binary_and_normalization_hashes": 21}
AUDIT_COUNTS = {"compact_files": 30, "decoded_rows": 480, "patches": 27,
                "scan_profiles": 162, "time_rows": 2592, "raw_cells_bitwise_checked": 334368}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--expected-scope-sha256", required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--root-go-after-all-three-complete", action="store_true", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    review = root / RESULTS / "review"
    review.mkdir(parents=True, exist_ok=True)
    receipt_path, failure_path, lock = (review / name for name in
        ("SOURCE_CELL_QA_RECEIPT.json", "SOURCE_CELL_QA_FAILURE_RECEIPT.json", "SOURCE_CELL_QA_STARTED.json"))
    check(not any(path.exists() for path in (receipt_path, failure_path, lock)), "Joint source audit is authorized once only")
    check(len(args.freeze_commit) == 40 and all(c in "0123456789abcdef" for c in args.freeze_commit),
          "Exact new public freeze commit required")
    with lock.open("x") as stream:
        json.dump({"status": "STARTED_ONCE_ONLY_JOINED_BOUNDARY_SOURCE_CELL_QA", "freeze_commit": args.freeze_commit,
                   "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
                   "script_sha256": digest(Path(__file__))}, stream)
        stream.write("\n")

    def deadline(signum, frame):
        raise TimeoutError("Joined-boundary source-cell QA CPU/wall limit")

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    counts = {key: 0 for key in AUDIT_COUNTS}
    json_pins, source_pins, patch_pins = {}, {}, {}

    def confined(path):
        path = path.resolve()
        check(path.is_relative_to(root), "Reference escapes project root")
        return path

    def read_json(path, sha=None, size=None):
        path = confined(path)
        raw = path.read_bytes()
        pin = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        check(sha is None or pin["sha256"] == sha, "Admitted JSON SHA differs: " + str(path))
        check(size is None or pin["bytes"] == size, "Admitted JSON size differs: " + str(path))
        check(path not in json_pins or json_pins[path] == pin, "Conflicting JSON admission")
        json_pins[path] = pin
        return json.loads(raw)

    try:
        scope_path = confined(args.scope)
        scope_sha = args.expected_scope_sha256
        check(len(scope_sha) == 64 and all(c in "0123456789abcdef" for c in scope_sha), "Exact frozen scope SHA required")
        scope = read_json(scope_path, scope_sha)
        check(scope["source_audit_CPU_cap_s"] == CPU_CAP and scope["source_audit_wall_cap_s"] == WALL_CAP
              and scope["source_audit_memory_cap_bytes"] == MEMORY_CAP, "Frozen source-audit caps differ")
        check(scope["saved_QA_CPU_cap_s_per_pair"] == 20 and scope["saved_QA_wall_cap_s_per_pair"] == 300
              and scope["saved_QA_memory_cap_bytes_per_pair"] == 2 * 1024**3, "Frozen saved-QA caps differ")
        dependencies = scope["pinned_dependency_files"]
        own_path, own_sha = Path(__file__).resolve(), digest(Path(__file__))
        own_name = own_path.relative_to(root).as_posix()
        check(dependencies[own_name] == {"sha256": own_sha, "bytes": own_path.stat().st_size}
              and scope["source_audit_script_sha256"] == own_sha, "Source-audit code differs from freeze")
        for name, pin in dependencies.items():
            path = confined(root / name)
            check(path.suffix.lower() not in (".h5", ".hdf5", ".npz", ".npy"), "Admission dependencies must be metadata or code")
            check(set(pin) == {"sha256", "bytes"} and path.stat().st_size == pin["bytes"]
                  and digest(path) == pin["sha256"], "Frozen metadata/code differs: " + name)
        check(set(scope["pair_contracts"]) == set(PAIRS)
              and set(scope["chunk_contracts"]) == {str(c) for c in CHUNKS}, "Only fixed retained pairs/native chunks allowed")
        wrapper_sha = scope["script_sha256"]
        check(dependencies[scope["script_path"]]["sha256"] == wrapper_sha
              and dependencies[FRESH_PATH]["sha256"] == FRESH_SHA, "Frozen wrapper/source loader identities differ")
        contexts, sources, acquisitions = {}, {}, {}
        for chunk in CHUNKS:
            context = scope["chunk_contracts"][str(chunk)]
            source = read_json(root / context["source_manifest_path"], context["source_manifest_sha256"])
            a = read_json(root / context["acquisition_summary_path"], context["acquisition_summary_sha256"])
            q = read_json(root / context["acquisition_QA_path"], context["acquisition_QA_sha256"])
            check(source["native_chunk_index"] == chunk
                  and source["physical_channel_interval_half_open"] == [chunk * N, (chunk + 1) * N]
                  and [s["label"] for s in source["sources"]] == list(SCANS), "Native source manifest identity differs")
            check(a["status"] == "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
                  and a["source_manifest_sha256"] == context["source_manifest_sha256"]
                  and a["source_channel0"] == chunk * N and a["physical_channel_interval_half_open"] == [chunk * N, (chunk + 1) * N]
                  and a["decoded_files"] == context["compact_files_and_96_decoded_row_pins"], "Frozen acquisition differs")
            check(q["status"] == "PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS" and q["source_chunk_id"] == chunk
                  and q["acquisition_result_sha256"] == context["acquisition_summary_sha256"]
                  and q["source_manifest_sha256"] == context["source_manifest_sha256"]
                  and q["counts"] == {"source_requests": 96, "compact_files": 6, "retained_compressed_chunks": 96,
                                       "decoded_rows": 96, "decoded_values_authenticated": 100663296}, "Frozen acquisition independent QA differs")
            files = a["decoded_files"]
            check(len(files) == 6 and [f["scan_id"] for f in files] == list(SCANS)
                  and all(f["shape"] == [16, 1, N] and f["source_channel0"] == chunk * N
                          and [r["time_row"] for r in f["decoded_rows"]] == list(range(16))
                          and all(r["decoded_bytes"] == N * 4 for r in f["decoded_rows"]) for f in files),
                  "Exact30 native compacts and480 declared rows required")
            contexts[chunk], sources[chunk], acquisitions[chunk] = context, source, a
        families = []
        six_names = ("EXECUTION_RECEIPT.json", "INPUT_PINS.json", "DRIFT_CHECKPOINT.json", "DRIFT_TOP20.json",
                     "FIXED_TOP3_PROFILES.json", "NORMALIZATION.json")
        # Every completed family and its saved QA is admitted before NumPy/H5.
        for pair_id, chunks in PAIRS.items():
            pair = scope["pair_contracts"][pair_id]
            directory = root / RESULTS / pair_id / "measurement"
            check(root / pair["measurement_directory"] == directory and pair["source_chunk_ids"] == list(chunks)
                  and pair["source_channel0"] == chunks[0] * N and pair["source_channel_count"] == 2 * N
                  and pair["joined_reference_core_q"] == [255, 256], "Exact joined family identity differs")
            check(not (directory / "FAILURE_RECEIPT.json").exists(), "An original boundary failure cannot be audited as COMPLETE")
            qpath = root / pair["QA_receipt_path"]
            qa = read_json(qpath)
            check(qpath.resolve() == (root / RESULTS / pair_id / "review/QA_RECEIPT.json").resolve(), "Isolated saved-QA path differs")
            check(qa["status"] == "PASS_COMPLETE_SAVED_JOINED_BOUNDARY_OUTPUTS" and qa["pair_id"] == pair_id
                  and qa["freeze_commit"] == args.freeze_commit and qa["public_scope_sha256"] == scope_sha
                  and qa["public_wrapper_sha256"] == wrapper_sha and qa["qa_script_sha256"] == scope["qa_script_sha256"]
                  and qa["cap_CPU_s_this_QA"] == 20 and qa["cap_wall_s_this_QA"] == 300
                  and qa["cap_memory_bytes"] == 2 * 1024**3
                  and qa["counts"] == QA_COUNTS and 0 < qa["process_CPU_seconds_including_imports"] <= 20
                  and 0 < qa["wall_seconds"] <= 300 and 0 < qa["peak_RSS_bytes"] <= 2 * 1024**3,
                  "All three exact completed independent saved QAs required")
            expected_names = {(directory / name).relative_to(root).as_posix() for name in six_names}
            check(set(qa["input_json_sha256"]) == expected_names, "Exactly six completed measurement JSON pins required")
            data = {name: read_json(directory / name, qa["input_json_sha256"][(directory / name).relative_to(root).as_posix()])
                    for name in six_names}
            e, inputs = data["EXECUTION_RECEIPT.json"], data["INPUT_PINS.json"]
            esha = json_pins[(directory / "EXECUTION_RECEIPT.json").resolve()]["sha256"]
            psha = json_pins[(directory / "FIXED_TOP3_PROFILES.json").resolve()]["sha256"]
            check(e["status"] == "COMPLETE_TWO_JOINED_BOUNDARY_CORES_EXPLORATORY_ONLY" and e["pair_id"] == pair_id
                  and e["scope_sha256"] == scope_sha and e["script_sha256"] == wrapper_sha
                  and e["public_freeze_commit"] == args.freeze_commit and e["fixed_pair_q"] == [255, 256]
                  and e["search_summary"]["completed_scan_tiles"] == 6 and e["fixed_profile_summary"]["profile_count"] == 9
                  and qa["execution_receipt_sha256"] == esha and qa["profile_JSON_sha256"] == psha,
                  "All three exact frozen numerical families must be COMPLETE")
            for field, cap in (("process_CPU_seconds_including_imports", 120), ("wall_seconds_including_imports", 1800),
                               ("peak_RSS_bytes", 4 * 1024**3)):
                check(0 < e[field] <= cap, "Original boundary execution resource cap differs")
            expected_inputs = {str(c): {"source_manifest_sha256": contexts[c]["source_manifest_sha256"],
                "acquisition_summary_sha256": contexts[c]["acquisition_summary_sha256"],
                "acquisition_QA_sha256": contexts[c]["acquisition_QA_sha256"],
                "compact_files_and_96_decoded_row_pins": acquisitions[c]["decoded_files"]} for c in chunks}
            check(inputs["pair_id"] == pair_id and inputs["scope_sha256"] == scope_sha and inputs["script_sha256"] == wrapper_sha
                  and inputs["public_freeze_commit"] == args.freeze_commit and inputs["source_inputs"] == expected_inputs
                  and e["source_inputs"] == expected_inputs and e["runtime_admission_receipts"] == inputs["runtime_admission_receipts"],
                  "Exact native file/row and runtime receipt pins differ")
            admission = inputs["runtime_admission_receipts"]
            if pair_id == "pair157_158":
                gate = scope["runtime_158_admission"]
                expected = {j[k] for j in gate["jobs"] for k in ("execution_receipt_path", "QA_receipt_path")}
                expected.add(gate["source_audit_receipt_path"])
                check(len(gate["jobs"]) == 2 and {j["batch_id"] for j in gate["jobs"]} == {1, 2}
                      and len(expected) == 5 and set(admission) == expected, "Both original158 COMPLETE/QA/source-audit receipts required")
                for name, pin in admission.items():
                    read_json(root / name, pin["sha256"], pin["bytes"])
            else:
                check(admission == {}, "Unexpected original158 admission in another pair")
            left, right = (sources[c] for c in chunks)
            for a, b in zip(left["sources"], right["sources"]):
                check(all(a[k] == b[k] for k in ("label", "role", "url", "etag", "source_file_bytes", "current_header")),
                      "Pair source identities and full headers differ")
            headers = {s["label"]: s["current_header"]["data_attributes"] for s in left["sources"]}
            anchor = min(h["tstart"] for h in headers.values())
            check(e["MJD_anchor"] == anchor, "Exact source header anchor differs")
            tops, records = data["DRIFT_TOP20.json"], data["FIXED_TOP3_PROFILES.json"]
            check(set(tops) == set(ONS) and all(len(tops[s]) == 20 for s in ONS)
                  and len(records) == 9 and [r["selected_track"] for r in records] == [t for s in ONS for t in tops[s][:3]],
                  "Exactly the27 frozen top3 selected profiles required")
            families.append((pair_id, chunks, directory, records, headers, anchor, esha, psha))
        packages = {"numpy": "2.3.5", "h5py": "3.15.1", "hdf5plugin": "7.1.0"}
        for name, version in packages.items():
            check(importlib.metadata.version(name) == version, "Pinned source codec package differs: " + name)
        import numpy as np
        import h5py
        import hdf5plugin
        check(h5py.version.hdf5_version == "1.14.6", "Pinned HDF5 runtime differs")
        offsets = np.arange(-64, 65)
        buffers = []
        # Reconstruct all geometry before opening any native H5 file.
        for pair_id, chunks, directory, records, headers, anchor, esha, psha in families:
            for record in records:
                track = record["selected_track"]
                check(track["pair_id"] == pair_id and track["originating_scan"] in ONS
                      and record["fixed_frequency_shift_channels"] == 0, "Fixed selected track identity differs")
                path = confined(directory / record["patch"]["path"])
                check(path.is_relative_to(directory.resolve()), "Patch escapes pair directory")
                raw_bytes = path.read_bytes()
                pin = {"sha256": hashlib.sha256(raw_bytes).hexdigest(), "bytes": len(raw_bytes)}
                check(pin == {"sha256": record["patch"]["sha256"], "bytes": record["patch"]["bytes"]}
                      and path not in patch_pins, "Unique saved patch byte identity differs")
                patch_pins[path] = pin
                dt = np.asarray([(headers[s]["tstart"] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP
                                 - track["reference_seconds_from_anchor"] for s in SCANS])
                base = (track["reference_frequency_hz"] - FCH1) / DF
                centers = np.rint(base + track["drift_hz_s"] * dt / DF).astype(np.int64)
                channels = centers[:, :, None] + offsets[None, None, :]
                check(channels.min() >= chunks[0] * N and channels.max() < (chunks[1] + 1) * N,
                      "Fixed patch geometry leaves retained native pair")
                with np.load(io.BytesIO(raw_bytes), allow_pickle=False) as z:
                    raw = z["raw_power"]
                    check(raw.shape == (6, 16, 129) and raw.dtype == np.dtype("<f4")
                          and np.isfinite(raw).all() and (raw >= 0).all(), "Saved raw patch shape/precision differs")
                    check(np.array_equal(z["frozen_source_channel_centers"], centers)
                          and np.array_equal(z["source_channel_offsets"], offsets)
                          and np.array_equal(z["times_seconds_from_reference"], dt)
                          and np.array_equal(z["scans"], np.asarray(SCANS))
                          and z["source_channel0"].shape == () and z["source_channel0"].item() == chunks[0] * N,
                          "Saved absolute/header-time geometry differs")
                buffers.append({"pair_id": pair_id, "chunks": chunks, "track_id": track["track_id"],
                                "channels": channels, "observed": raw, "expected": np.empty_like(raw),
                                "filled": np.zeros(raw.shape, dtype=bool), "patch_sha256": pin["sha256"],
                                "source_execution_receipt_sha256": esha, "source_profiles_JSON_sha256": psha})
        check(len(buffers) == 27 and len({(b["pair_id"], b["track_id"]) for b in buffers}) == 27,
              "All27 composite patch identities must be unique")
        spec = importlib.util.spec_from_file_location("unchanged_streaming_boundary_source_loader", root / FRESH_PATH)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        fresh.np, fresh.COUNT = np, N
        source_checks = []
        for chunk in CHUNKS:
            context, source, acquisition = contexts[chunk], sources[chunk], acquisitions[chunk]
            compact = confined(root / context["compact_directory"])
            fresh.C0 = chunk * N
            for f in acquisition["decoded_files"]:
                scan = f["scan_id"]
                index = SCANS.index(scan)
                path = confined(compact / f["array_file"])
                check(path.is_relative_to(compact) and path not in source_pins, "Each of30 unique retained native compacts may decode once only")
                check(path.stat().st_size == f["bytes"] and digest(path) == f["file_sha256"], "Native source file bytes differ before decode")
                source_pins[path] = {"sha256": f["file_sha256"], "bytes": f["bytes"]}
                arrays, proof = fresh.load_power(SimpleNamespace(compact_dir=str(compact)), source, acquisition, labels=(scan,))
                check(proof[scan] == {"path": f["array_file"], "file_sha256": f["file_sha256"], "bytes": f["bytes"]},
                      "Pinned loader source proof differs")
                data = arrays[scan]
                for b in buffers:
                    if chunk not in b["chunks"]:
                        continue
                    local = b["channels"][index] - chunk * N
                    mask = (local >= 0) & (local < N)
                    check(not b["filled"][index][mask].any(), "A profile cell cannot be authenticated twice")
                    rows = np.broadcast_to(np.arange(16)[:, None], local.shape)
                    b["expected"][index][mask] = data[rows[mask], local[mask]]
                    b["filled"][index][mask] = True
                source_checks.append({"source_chunk_id": chunk, "scan_id": scan, "path": path.relative_to(root).as_posix(),
                    "file_sha256": f["file_sha256"], "bytes": f["bytes"], "decoded_rows_checked": 16,
                    "decoded_row_sha256": [r["decoded_sha256"] for r in f["decoded_rows"]], "decoded_once": True})
                counts["compact_files"] += 1
                counts["decoded_rows"] += 16
                del data, arrays, proof
        patch_checks = []
        for b in buffers:
            check(b["filled"].all(), "Every fixed profile source cell must be authenticated exactly once")
            observed_bytes, expected_bytes = b["observed"].tobytes(order="C"), b["expected"].tobytes(order="C")
            check(observed_bytes == expected_bytes, "Retained raw patch differs bitwise from authenticated native source cells")
            patch_checks.append({"pair_id": b["pair_id"], "track_id": b["track_id"], "raw_cells": b["observed"].size,
                "patch_sha256": b["patch_sha256"], "raw_cell_bytes_SHA256": hashlib.sha256(observed_bytes).hexdigest(),
                "independent_source_cell_bytes_SHA256": hashlib.sha256(expected_bytes).hexdigest(),
                "source_execution_receipt_sha256": b["source_execution_receipt_sha256"],
                "source_profiles_JSON_sha256": b["source_profiles_JSON_sha256"], "bitwise_identical": True})
            counts["patches"] += 1
            counts["scan_profiles"] += 6
            counts["time_rows"] += 96
            counts["raw_cells_bitwise_checked"] += b["observed"].size
        check(counts == AUDIT_COUNTS and len(source_pins) == 30 and len(patch_pins) == 27, "Unique streamed source audit incomplete")
        for path, pin in {**json_pins, **source_pins, **patch_pins}.items():
            check(path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"], "Admitted metadata/source/patch changed during audit")
        for name, pin in dependencies.items():
            path = confined(root / name)
            check(path.stat().st_size == pin["bytes"] and digest(path) == pin["sha256"], "Frozen code/metadata changed during audit")
        check(digest(own_path) == own_sha, "Source-audit script changed")
        measured = {"process_CPU_seconds_including_imports": time.process_time(), "wall_seconds": time.monotonic() - started,
                    "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(0 < measured["process_CPU_seconds_including_imports"] <= CPU_CAP
              and 0 < measured["wall_seconds"] <= WALL_CAP and 0 < measured["peak_RSS_bytes"] <= MEMORY_CAP,
              "Measured source-cell audit resource cap exceeded")
        receipt = {"status": "PASS_27_FIXED_RAW_PATCHES_AUTHENTICATED_BITWISE_TO_SOURCE", "freeze_commit": args.freeze_commit,
            "pair_ids": list(PAIRS), "source_chunk_ids": list(CHUNKS), "profile_identity_fields": ["pair_id", "track_id"],
            "public_scope_sha256": scope_sha, "public_wrapper_sha256": wrapper_sha, "audit_script_sha256": own_sha,
            "runtime_package_versions": packages, "runtime_package_paths": {"numpy": np.__file__, "h5py": h5py.__file__, "hdf5plugin": hdf5plugin.__file__},
            "counts": counts, "source_checks": source_checks, "patch_checks": patch_checks,
            "opened_json_pins": [{"path": p.relative_to(root).as_posix(), **pin} for p, pin in sorted(json_pins.items())],
            "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP, **measured,
            "cap_stage_QA_allocation_CPU_s": 120, "combined_three_saved_QA_process_caps_s": 60,
            "separate_joint_source_QA_process_cap_s": CPU_CAP,
            "source_HDF5_files_read_once": 30, "source_HDF5_decoded_rows": 480,
            "compact_file_input_occurrences": 36, "decoded_row_input_occurrences": 576,
            "detector_or_score_runs": 0, "profile_optimization_or_new_measurement_runs": 0, "source_profile_normalization_remeasured": False,
            "new_HTTP_requests": 0, "new_SOURCE_BODY_bytes": 0, "original_scopes_terminal_statuses_and_outputs_modified": False,
            "geometry_operation": "Independent exact absolute np.rint/header-time geometry; stream authenticated native rows and gather each retained raw-cell occurrence once.",
            "normalization_authenticity_limit": "The saved joined profile denominator is not independently remeasured; source cells and geometry only are authenticated.",
            "scientific_limit": "One exposed historical visit, selected pair profiles and shared controls; no calibrated significance or origin qualification."}
        with receipt_path.open("x") as stream:
            stream.write(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"status": receipt["status"], "counts": counts, "receipt_path": str(receipt_path),
                          **measured}, allow_nan=False), flush=True)
    except BaseException as exc:
        failure = {"status": "SOURCE_CELL_QA_INCOMPLETE_OR_FAILED_NO_RETRY", "error_type": type(exc).__name__,
                   "error": str(exc), "partial_counts": counts, "process_CPU_seconds_including_imports": time.process_time(),
                   "wall_seconds": time.monotonic() - started, "retry_authorized": False, "detector_or_score_runs": 0}
        with failure_path.open("x") as stream:
            stream.write(json.dumps(failure, indent=2, allow_nan=False) + "\n")
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
