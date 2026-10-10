"""Once-only byte/hash/row QA of a COMPLETE new native-chunk acquisition.

No HTTP or detector search. Before reading any source arrays, require the exact
public scope/script/manifest identities and COMPLETE acquisition plus ledger.
Check all retained compressed source bytes and all decoded row identities.
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

SCANS = ("epoch1_on", "epoch1_off", "epoch2_on", "epoch2_off", "epoch3_on", "epoch3_off")
COUNT = 1048576
CPU_CAP, WALL_CAP, MEMORY_CAP = 20, 120, 2 * 1024**3
COMMON_SCOPE_SHA = "60ec39a777575ba25352e2eeb0b6db3ec21e3aed84fb92d534b82b5ded3f74b4"
ACQUIRER_SHA = "ab198efe36eb45a0abde0feadcf18898f31d47b05c691c379cea1cc024b61c19"
SCOPE_SHAS = {153: "a812f9a0736f9a198f6ec43053e654351addd5bc4633077788e8154cfa22fe65",
              154: "35b2acbaf162a1ff508b96914bb15aed5469d1a2323b979bd46e556e64071b23"}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


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
    parser.add_argument("--chunk", type=int, choices=(153, 154), required=True)
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    here = root / "tools/radio_next_bands_20261010"
    out = root / f"results/radio_next_bands_20261010/chunk{args.chunk}/arrays"
    receipt_path = out / "ACQUISITION_OUTPUT_QA_RECEIPT.json"
    failure_path = out / "ACQUISITION_OUTPUT_QA_FAILURE.json"
    lock = out / "ACQUISITION_OUTPUT_QA_STARTED.json"
    check(not any(p.exists() for p in (receipt_path, failure_path, lock)), "Acquisition QA is once only")

    def deadline(signum, frame):
        raise TimeoutError("Completed-acquisition QA CPU/wall limit")

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    counts = {"source_requests": 0, "compact_files": 0, "retained_compressed_chunks": 0,
              "decoded_rows": 0, "decoded_values_authenticated": 0}
    try:
        scope_path = here / f"acquisition_scope_chunk{args.chunk}.json"
        check(digest(scope_path) == SCOPE_SHAS[args.chunk] and digest(here / "acquire.py") == ACQUIRER_SHA,
              "Frozen acquisition code/scope differs")
        check(digest(here / "scope.json") == COMMON_SCOPE_SHA, "Common four-batch scope differs")
        scope = read_json(scope_path)
        for name, sha in scope["pinned_files"].items():
            check(digest(root / name) == sha, "Acquisition pin differs: " + name)
        manifest_path = root / scope["source_manifest"]
        manifest = read_json(manifest_path)
        check(scope["native_chunk_index"] == args.chunk
              and manifest["physical_channel_interval_half_open"] == [args.chunk * COUNT, (args.chunk + 1) * COUNT],
              "Wrong native source chunk")
        check((root / scope["output_directory"]).resolve() == out.resolve(), "Wrong fixed output directory")
        result_path = out / "ACQUISITION_RESULT.json"
        ledger_path = out / "SOURCE_BODY_LEDGER.json"
        result_sha = digest(result_path)
        ledger_sha = digest(ledger_path)
        result = read_json(result_path)
        ledger = read_json(ledger_path)
        check(result["status"] == "COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY"
              and ledger["complete"], "Never audit partial acquisition files")
        check(result["native_chunk_index"] == args.chunk and result["source_channel0"] == args.chunk * COUNT
              and result["physical_channel_interval_half_open"] == manifest["physical_channel_interval_half_open"],
              "Completed acquisition source frame differs")
        check(result["scope_sha256"] == SCOPE_SHAS[args.chunk] and result["script_sha256"] == ACQUIRER_SHA
              and result["source_manifest_sha256"] == digest(manifest_path)
              and result["standard_reader_sha256"] == scope["standard_reader_sha256"],
              "Completed acquisition provenance differs")
        check(result["qualification"] == "FAIL_CLOSED_UNCHANGED" and result["cost_DKK"] == 0
              and not result["whole_original_telescope_MD5_verified"] and not result["new_observation_visit"],
              "Acquisition scientific status differs")
        guard = result["completion_resource_guard"]
        check(guard["status"] == "PASS_BEFORE_COMPLETE"
              and result["end_of_run_pinned_file_readback"] == "PASS_SCOPE_SCRIPT_MANIFEST_HELPER_AND_ALL_OTHER_SCOPE_PINS",
              "Resource/input completion guards missing")
        for usage in (result, guard):
            check(0 < usage["cpu_s"] <= 60 and 0 < usage["wall_s"] <= 1200
                  and 0 < usage["peak_rss_bytes"] <= 4294967296, "Actual acquisition resource limits differ")
        expected_bytes = scope["expected_new_spectral_BODY_bytes"]
        check(result["new_spectral_BODY_bytes"] == expected_bytes
              and result["new_spectral_BODY_charged_upper_bound"] == expected_bytes + 96,
              "Completed acquisition activity BODY differs")
        check(ledger["new_value_requests_attempted"] == 96
              and ledger["prior_body_bytes"] == scope["prior_same_cadence_source_plus_metadata_BODY_bytes"]
              and ledger["prior_charged_upper_bound_bytes"] == scope["prior_same_cadence_charged_upper_bound_bytes"]
              and ledger["source_body_bytes_received"] - ledger["prior_body_bytes"] == expected_bytes
              and ledger["source_body_bytes_charged_upper_bound"] - ledger["prior_charged_upper_bound_bytes"] == expected_bytes + 96
              and ledger["source_body_bytes_charged_upper_bound"] <= 2147483648,
              "Actual/conservative acquisition ledger differs")
        check(result["versions"] == {"h5py": "3.15.1", "hdf5plugin": "7.1.0", "numpy": "2.3.5", "hdf5": "1.14.6"},
              "Acquisition exact codec versions differ")
        requests = result["value_read_requests"]
        expected_rows = [(item, ch) for item in manifest["sources"] for ch in item["chunks"]]
        check(len(requests) == 96 and [(r["scan_id"], r["time_row"]) for r in requests]
              == [(item["label"], ch["time_row"]) for item, ch in expected_rows], "All96 unique ordered GET receipts required")
        for request, (item, ch) in zip(requests, expected_rows):
            check(request["status"] == "EXACT_SOURCE_RANGE_RECEIVED"
                  and request["request_range"] == ch["byte_range"]
                  and request["expected_etag"] == item["etag"]
                  and request["body_bytes_received"] == ch["stored_size"], "Strict range GET receipt differs")
            headers = request["response_headers"]
            check(headers["ETag"] == item["etag"]
                  and headers["Content-Range"] == f"bytes {ch['byte_offset']}-{ch['byte_offset'] + ch['stored_size'] - 1}/{item['source_file_bytes']}"
                  and headers["Content-Length"] == str(ch["stored_size"])
                  and (headers["Content-Encoding"] or "identity").lower() == "identity",
                  "Exact received source headers differ")
        decoded = result["decoded_files"]
        check(len(decoded) == 6 and [r["scan_id"] for r in decoded] == list(SCANS), "Six ordered decoded compacts required")
        check(len(result["local_pipeline_records"]) == 6, "Six local filter pipeline receipts required")
        check(set(result["decoded_row_progress"]) == set(SCANS), "Six completed row-progress records required")
        for name, version in (("numpy", "2.3.5"), ("h5py", "3.15.1"), ("hdf5plugin", "7.1.0")):
            check(importlib.metadata.version(name) == version, "QA codec environment differs: " + name)
        # Admission above intentionally happens before importing codecs or opening any H5.
        with lock.open("x") as stream:
            json.dump({"status": "STARTED_ONCE_ONLY_COMPLETE_ACQUISITION_QA", "chunk": args.chunk,
                       "freeze_commit": args.freeze_commit, "script_sha256": digest(Path(__file__))}, stream)
            stream.write("\n")
        import numpy as np
        import h5py
        import hdf5plugin
        check(h5py.version.hdf5_version == "1.14.6", "Bundled HDF5 differs")
        files = []
        for record, item, pipeline in zip(decoded, manifest["sources"], result["local_pipeline_records"]):
            scan = item["label"]
            path = out / record["array_file"]
            check(path.resolve().is_relative_to(out.resolve()) and path.stat().st_size == record["bytes"]
                  and digest(path) == record["file_sha256"], "Retained compact file identity differs")
            check(record["shape"] == [16, 1, COUNT] and record["source_channel0"] == args.chunk * COUNT,
                  "Retained compact receipt geometry differs")
            check(record["decoded_rows"] == result["decoded_row_progress"][scan]
                  and [r["time_row"] for r in record["decoded_rows"]] == list(range(16)),
                  "All16 decoded-row receipts required")
            with h5py.File(path, "r", rdcc_nbytes=8 * 1024**2) as handle:
                dataset = handle["data"]
                check(dataset.shape == (16, 1, COUNT) and dataset.dtype == np.dtype("<f4")
                      and dataset.chunks == (1, 1, COUNT), "Retained HDF5 schema differs")
                check(int(dataset.attrs["original_source_frequency_chunk_origin"]) == args.chunk * COUNT
                      and dataset.attrs["original_source_url"] == item["url"]
                      and dataset.attrs["original_source_etag"] == item["etag"], "Retained HDF5 source provenance differs")
                actual = dataset.id.get_create_plist().get_filter(0)
                check(dataset.id.get_create_plist().get_nfilters() == 1 and pipeline["scan_id"] == scan
                      and pipeline["original_filter"] == item["current_header"]["hdf5_filters"][0]
                      and pipeline["current_filter"] == [actual[0], actual[1], list(actual[2]), actual[3].decode("utf8", "replace")]
                      and pipeline["semantic_parameters_preserved"] and not pipeline["prefix_identity_claim"],
                      "Saved/current filter pipeline differs")
                original = item["current_header"]["hdf5_filters"][0]
                check(actual[0] == original[0] and actual[1] == original[1]
                      and tuple(actual[2][2:]) == tuple(original[2][2:]), "Original filter semantics differ")
                for row, ch in enumerate(item["chunks"]):
                    request = requests[list(SCANS).index(scan) * 16 + row]
                    mask, compressed = dataset.id.read_direct_chunk((row, 0, 0))
                    check(mask == 0 and len(compressed) == ch["stored_size"]
                          and hashlib.sha256(compressed).hexdigest() == request["raw_sha256"],
                          "Retained compressed source bytes differ")
                    counts["retained_compressed_chunks"] += 1
                values = dataset[:, 0, :]  # One full decode per completed compact.
            check(np.isfinite(values).all() and (values >= 0).all(), "Invalid decoded power")
            for row, evidence in enumerate(record["decoded_rows"]):
                payload = values[row].tobytes(order="C")
                check(len(payload) == evidence["decoded_bytes"] == COUNT * 4
                      and hashlib.sha256(payload).hexdigest() == evidence["decoded_sha256"],
                      "Decoded source row identity differs")
                counts["decoded_rows"] += 1; counts["decoded_values_authenticated"] += COUNT
            files.append({"scan_id": scan, "file_sha256": record["file_sha256"], "bytes": record["bytes"],
                          "retained_compressed_chunks_checked": 16, "decoded_rows_checked": 16})
            counts["compact_files"] += 1
            del values
        counts["source_requests"] = len(requests)
        check(counts == {"source_requests": 96, "compact_files": 6, "retained_compressed_chunks": 96,
                         "decoded_rows": 96, "decoded_values_authenticated": 100663296}, "Completed acquisition QA incomplete")
        check(digest(result_path) == result_sha, "Acquisition receipt changed during QA")
        check(digest(ledger_path) == ledger_sha and digest(scope_path) == SCOPE_SHAS[args.chunk], "Ledger/scope changed during QA")
        check(digest(here / "scope.json") == COMMON_SCOPE_SHA, "Common four-batch scope changed during QA")
        for name, sha in scope["pinned_files"].items():
            check(digest(root / name) == sha, "Frozen acquisition metadata/code changed during QA")
        measured = {"process_CPU_seconds_including_imports": time.process_time(),
                    "wall_seconds": time.monotonic() - started,
                    "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        check(measured["process_CPU_seconds_including_imports"] <= CPU_CAP
              and measured["wall_seconds"] <= WALL_CAP and measured["peak_RSS_bytes"] <= MEMORY_CAP,
              "Acquisition QA measured cap exceeded")
        receipt = {"status": "PASS_COMPLETE_SOURCE_BYTES_AND_ALL96_DECODED_ROWS", "source_chunk_id": args.chunk,
                   "freeze_commit": args.freeze_commit, "qa_script_sha256": digest(Path(__file__)),
                   "acquisition_scope_sha256": SCOPE_SHAS[args.chunk], "acquisition_script_sha256": ACQUIRER_SHA,
                   "source_manifest_sha256": digest(manifest_path), "common_four_batch_scope_sha256": COMMON_SCOPE_SHA,
                   "acquisition_result_sha256": digest(result_path), "source_BODY_ledger_sha256": digest(ledger_path),
                   "counts": counts, "files": files, "actual_new_BODY_bytes": expected_bytes,
                   "new_BODY_charged_upper_bound": expected_bytes + 96,
                   "CPU_cap_s": CPU_CAP, "wall_cap_s": WALL_CAP, "memory_cap_bytes": MEMORY_CAP,
                   **measured, "source_HDF5_files_decoded_once": 6, "new_HTTP_requests": 0,
                   "detector_or_profile_measurement_runs": 0, "whole_original_source_MD5_verified": False,
                   "scientific_limit": "Authenticates exact retained source parts; does not qualify origin, significance, sensitivity or an independent visit."}
        save(receipt_path, receipt)
        print(json.dumps({"status": receipt["status"], "source_chunk_id": args.chunk, "counts": counts,
                          **measured, "receipt_path": str(receipt_path), "receipt_sha256": digest(receipt_path)}), flush=True)
    except BaseException as exc:
        save(failure_path, {"status": "ACQUISITION_OUTPUT_QA_INCOMPLETE_OR_FAILED_NO_RETRY",
                            "source_chunk_id": args.chunk, "error_type": type(exc).__name__, "error": str(exc),
                            "partial_counts": counts, "process_CPU_seconds_including_imports": time.process_time(),
                            "wall_seconds": time.monotonic() - started, "new_HTTP_requests": 0})
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
