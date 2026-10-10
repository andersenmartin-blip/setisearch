"""Prospective, ordinary bounded reader for one frozen six-scan radio pilot.

Preparation is inert. No HTTP/native import occurs at module import. The CLI
requires a pinned PASS validation summary and explicit run admission. It is not
a codec qualification or reconstruction of the historical runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import importlib.metadata
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import time
import urllib.error
import urllib.parse
import urllib.request

SOURCE_LIMIT = 2 * 1024 ** 3
ARTIFACT_LIMIT = 8 * 1024 ** 3
MEMORY_AS_LIMIT = 4 * 1024 ** 3
WALL_LIMIT = 1800
EXPECTED_PAYLOAD = 305133821
LOADED_INTERVAL = (159903921, 159911759)
PHYSICAL_INTERVAL = (159383552, 160432128)


def pinned_json(path, expected_sha256):
    raw = Path(path).read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or observed != expected_sha256:
        raise ValueError(f"Pinned JSON hash mismatch: {path}")
    return json.loads(raw), observed


def atomic_json(path, value):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(target)


def validate_source(source):
    if source["status"] != "METADATA_QUALIFIED_FOR_BOUNDED_PROSPECTIVE_ACQUISITION":
        raise ValueError("Source is not metadata-qualified")
    if source["spectral_values_read"] or source["spectral_payload_fetched"]:
        raise ValueError("Prospective source metadata must precede this value opening")
    if tuple(source["band"]["prospective_science_decode_interval_half_open"]) != LOADED_INTERVAL:
        raise ValueError("Different decode geometry requires new admission")
    if tuple(source["band"]["physical_chunk_channel_interval_half_open"]) != PHYSICAL_INTERVAL:
        raise ValueError("Unexpected physical frequency chunk")
    sources = source["sources"]
    if len(sources) != 6 or [x["role"] for x in sources] != ["on", "off"] * 3:
        raise ValueError("Six complete ordered ON/OFF scans required")
    if len({x["label"] for x in sources}) != 6:
        raise ValueError("Duplicate source label")
    total = 0
    for item in sources:
        url = urllib.parse.urlsplit(item["url"])
        if url.scheme != "https" or url.hostname != "bldata.berkeley.edu" or url.username or url.password:
            raise ValueError("Unexpected frozen source URL")
        if not re.fullmatch(r'"[^"\r\n]+"', item["etag"]):
            raise ValueError("A strong frozen ETag is required")
        header = item["current_header"]
        if header["dataset_shape"] != [16, 1, 264503296] or header["dataset_chunks"] != [1, 1, 1048576]:
            raise ValueError("Unexpected source shape or physical chunks")
        if item["dtype_exact"] != "<f4":
            raise ValueError("Original little-endian float32 type required")
        filters = header["hdf5_filters"]
        if len(filters) != 1 or filters[0][:3] != [32008, 1, [0, 3, 4, 0, 2]]:
            raise ValueError("Unexpected source filter pipeline")
        chunks = item["chunks"]
        if len(chunks) != 16 or [x["time_row"] for x in chunks] != list(range(16)):
            raise ValueError("Every declared time row requires one exact source chunk")
        for chunk in chunks:
            if chunk["chunk_origin"] != [chunk["time_row"], 0, PHYSICAL_INTERVAL[0]]:
                raise ValueError("Unexpected physical source origin")
            size, offset = chunk["stored_size"], chunk["byte_offset"]
            if not isinstance(size, int) or not 0 < size <= 5 * 1024 ** 2:
                raise ValueError("Unexpected stored chunk size")
            if offset < 0 or offset + size > item["source_file_bytes"]:
                raise ValueError("Source chunk outside frozen file size")
            if chunk["byte_range"] != f"bytes={offset}-{offset + size - 1}":
                raise ValueError("Frozen range is inconsistent")
            if chunk["filter_mask"] != 0 or chunk["decoded_size"] != 4194304:
                raise ValueError("Unexpected chunk mask or full decoded geometry")
            total += size
    if total != EXPECTED_PAYLOAD:
        raise ValueError("The complete frozen 96-range payload differs")
    return sources


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect refused; frozen source is required")


def acquire_chunk(item, chunk, ledger, ledger_path, receipts, opener):
    size, offset = chunk["stored_size"], chunk["byte_offset"]
    if ledger["source_body_bytes_charged_upper_bound"] + size + 1 > SOURCE_LIMIT:
        raise ValueError("Cumulative cadence source-byte ceiling would be exceeded")
    record = {"scan_id": item["label"], "time_row": chunk["time_row"],
              "request_range": chunk["byte_range"], "expected_etag": item["etag"],
              "status": "REQUEST_ADMITTED_SINGLE_ATTEMPT", "body_bytes_received": 0}
    receipts.append(record)
    ledger["new_value_requests_attempted"] += 1
    ledger["source_body_bytes_charged_upper_bound"] += size + 1
    atomic_json(ledger_path, ledger)
    request = urllib.request.Request(item["url"], headers={
        "Range": chunk["byte_range"], "If-Match": item["etag"],
        "Accept-Encoding": "identity", "User-Agent": "setisearch-bounded-pilot-reader/1"})
    pieces = []
    started = time.monotonic()
    try:
        with opener.open(request, timeout=60) as response:
            expected_range = f"bytes {offset}-{offset + size - 1}/{item['source_file_bytes']}"
            record["response_headers"] = {key: response.headers.get(key) for key in
                ("ETag", "Content-Range", "Content-Length", "Content-Encoding", "Last-Modified")}
            if response.status != 206 or response.geturl() != item["url"]:
                raise ValueError("Exact frozen URL and HTTP 206 required before reading a body")
            if response.headers.get("ETag") != item["etag"]:
                raise ValueError("Source ETag changed")
            if response.headers.get("Content-Range") != expected_range:
                raise ValueError("HTTP range or frozen complete-file length differs")
            if response.headers.get("Content-Length") != str(size):
                raise ValueError("Exact Content-Length required")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise ValueError("Encoded response body refused")
            while record["body_bytes_received"] <= size:
                try:
                    piece = response.read(min(65536, size + 1 - record["body_bytes_received"]))
                except http.client.IncompleteRead as error:
                    record["body_bytes_received"] += len(error.partial)
                    ledger["source_body_bytes_received"] += len(error.partial)
                    raise
                if not piece:
                    break
                pieces.append(piece)
                record["body_bytes_received"] += len(piece)
                ledger["source_body_bytes_received"] += len(piece)
            if record["body_bytes_received"] != size:
                raise ValueError("Incomplete or overlong chunk; no retry or resume")
        body = b"".join(pieces)
        record.update(status="EXACT_SOURCE_RANGE_RECEIVED", raw_sha256=hashlib.sha256(body).hexdigest())
        return body
    except BaseException as error:
        record.update(status="FAILED_CLOSED_NO_RETRY", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        record["wall_s"] = time.monotonic() - started
        atomic_json(ledger_path, ledger)


def current_codecs():
    # Called only after PASS validation/source admission, before any GET.
    import h5py
    import hdf5plugin
    import numpy as np
    if not hdf5plugin.register(filters="bshuf", force=True):
        raise ValueError("Official supported bitshuffle registration failed")
    if not hasattr(hdf5plugin, "from_filter_options"):
        raise ValueError("Official stored-filter parser is required; no private decoder")
    if not h5py.h5z.filter_avail(32008):
        raise ValueError("Official bitshuffle filter 32008 is unavailable")
    if not h5py.h5z.get_filter_info(32008) & h5py.h5z.FILTER_CONFIG_DECODE_ENABLED:
        raise ValueError("Bitshuffle decoding capability is unavailable")
    return h5py, hdf5plugin, np


def create_compact_dataset(handle, item, h5py, hdf5plugin):
    original = item["current_header"]["hdf5_filters"][0]
    # Stored CD values include three reserved fields; passing them directly as
    # user compression_opts is wrong. The official helper converts them.
    codec = hdf5plugin.from_filter_options(original[0], tuple(original[2]))
    data = handle.create_dataset("data", shape=(16, 1, 1048576), dtype="<f4",
                                 chunks=(1, 1, 1048576), compression=codec)
    actual = data.id.get_create_plist().get_filter(0)
    if data.id.get_create_plist().get_nfilters() != 1:
        raise ValueError("Unexpected local filter pipeline length")
    # Creation's supported codec stamps its current version in the first two
    # reserved fields. Semantic element size/block size/compressor must agree.
    if actual[0] != original[0] or actual[1] != original[1] or tuple(actual[2][2:]) != tuple(original[2][2:]):
        raise ValueError("Current codec altered filter semantics")
    data.attrs["original_source_frequency_chunk_origin"] = PHYSICAL_INTERVAL[0]
    data.attrs["original_source_url"] = item["url"]
    data.attrs["original_source_etag"] = item["etag"]
    return data, {"original_filter": original,
                  "current_filter": [actual[0], actual[1], list(actual[2]), actual[3].decode("utf8", "replace")],
                  "prefix_identity_claim": False, "semantic_parameters_preserved": True}


def run(args):
    if not args.admit_validated_pilot_value_read:
        raise ValueError("Explicit value-read admission is required")
    source, source_hash = pinned_json(args.source_manifest, args.source_manifest_sha256)
    summary, validation_hash = pinned_json(args.validation_summary, args.validation_summary_sha256)
    source_ledger, source_ledger_hash = pinned_json(args.source_ledger, args.source_ledger_sha256)
    if (summary.get("panel") not in ("VAL_A", "VAL_B") or not summary.get("complete") or
            summary.get("scientific_gate") != "PASS_EXPLORATORY_SCOPE_ONLY" or
            not summary.get("checks") or not all(summary["checks"].values())):
        raise ValueError("Fresh complete independent validation PASS is required before any pilot value read")
    sources = validate_source(source)
    initial_bytes = int(source_ledger["total_source_body_bytes"])
    if initial_bytes < 1158240 or initial_bytes + EXPECTED_PAYLOAD + 96 > SOURCE_LIMIT:
        raise ValueError("Spent metadata plus prospective payload exceeds cadence budget")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    started, cpu_started = time.monotonic(), time.process_time()
    receipts, decoded_files, pipeline_records = [], [], []
    ledger = {"source_body_bytes_received": initial_bytes, "source_body_bytes_charged_upper_bound": initial_bytes,
              "spent_metadata_body_bytes": initial_bytes,
              "new_value_requests_attempted": 0, "new_value_requests_limit": 96,
              "source_body_byte_ceiling": SOURCE_LIMIT, "complete": False}
    result = {"status": "VALUE_READ_ADMITTED_NOT_COMPLETE", "source_manifest_sha256": source_hash,
              "validation_summary_sha256": validation_hash, "source_ledger_sha256": source_ledger_hash,
              "loaded_source_channel_interval": list(LOADED_INTERVAL), "value_read_requests": receipts,
              "local_pipeline_records": pipeline_records, "decoded_files": decoded_files,
              "scientific_search_run": False}
    ledger_path = output / "source_byte_ledger.json"
    atomic_json(ledger_path, ledger)
    atomic_json(output / "value_read_result.json", result)
    def deadline(signum, frame):
        raise TimeoutError("Bounded value-read wall deadline exceeded")
    try:
        signal.signal(signal.SIGALRM, deadline)
        signal.alarm(WALL_LIMIT)
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_AS_LIMIT, MEMORY_AS_LIMIT))
        resource.setrlimit(resource.RLIMIT_FSIZE, (ARTIFACT_LIMIT, ARTIFACT_LIMIT))
        if shutil.disk_usage(output).free < 2 * (EXPECTED_PAYLOAD + 32 * 1024 ** 2):
            raise ValueError("Insufficient free space for bounded local artifacts")
        h5py, hdf5plugin, np = current_codecs()
        result["versions"] = {name: importlib.metadata.version(name) for name in ("h5py", "hdf5plugin", "numpy")}
        result["versions"]["hdf5"] = h5py.version.hdf5_version
        opener = urllib.request.build_opener(NoRedirect())
        local0, local1 = (x - PHYSICAL_INTERVAL[0] for x in LOADED_INTERVAL)
        # Verify the prospective current codec's creation properties before GET.
        compact = []
        try:
            for item in sources:
                path = output / f"{item['label']}.compact.h5"
                handle = h5py.File(path, "x", rdcc_nbytes=8 * 1024 ** 2)
                try:
                    dataset, pipeline = create_compact_dataset(handle, item, h5py, hdf5plugin)
                except BaseException:
                    handle.close()
                    raise
                pipeline_records.append({"scan_id": item["label"], **pipeline})
                compact.append((item, path, handle, dataset))
            for item, path, handle, dataset in compact:
                for chunk in item["chunks"]:
                    body = acquire_chunk(item, chunk, ledger, ledger_path, receipts, opener)
                    destination = (chunk["time_row"], 0, 0)
                    dataset.id.write_direct_chunk(destination, body, filter_mask=chunk["filter_mask"])
                    mask, retained_body = dataset.id.read_direct_chunk(destination)
                    if mask != chunk["filter_mask"] or retained_body != body:
                        raise ValueError("Compressed source bytes/filter mask changed in compact storage")
                    receipts[-1]["compact_raw_roundtrip_sha256"] = hashlib.sha256(retained_body).hexdigest()
                handle.flush()
                selected = np.empty((16, LOADED_INTERVAL[1] - LOADED_INTERVAL[0]), dtype="<f4")
                for row in range(16):
                    values = dataset[row, 0, local0:local1]
                    if values.shape != (7838,) or values.dtype != np.dtype("<f4") or not np.isfinite(values).all():
                        raise ValueError("Complete finite float32 selected row required")
                    selected[row] = values
                npy = output / f"{item['label']}.selected.npy"
                with npy.open("xb") as stream:
                    np.save(stream, selected, allow_pickle=False)
                decoded_files.append({"scan_id": item["label"], "path": npy.name, "shape": [16, 7838],
                                      "dtype": "<f4", "source_channel0": LOADED_INTERVAL[0],
                                      "decoded_array_sha256": hashlib.sha256(selected.tobytes(order="C")).hexdigest()})
                total_artifacts = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
                if total_artifacts > ARTIFACT_LIMIT:
                    raise ValueError("Total artifact-byte ceiling exceeded")
                atomic_json(output / "value_read_result.json", result)
        finally:
            for item, path, handle, dataset in compact:
                handle.close()
        if len(receipts) != 96 or len(decoded_files) != 6:
            raise ValueError("Six complete scans and 96 exact chunks required")
        ledger["complete"] = True
        result.update(status="PASS_BOUNDED_PILOT_VALUES_READ_NO_SEARCH", spectral_payload_bytes=EXPECTED_PAYLOAD,
                      selected_application_array_bytes=6 * 16 * 7838 * 4,
                      codec_full_physical_chunk_decode_bytes=96 * 4194304)
    except BaseException as error:
        result.update(status="FAILED_CLOSED_NO_RETRY", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        signal.alarm(0)
        result.update(wall_s=time.monotonic() - started, cpu_s=time.process_time() - cpu_started,
                      peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        atomic_json(ledger_path, ledger)
        atomic_json(output / "value_read_result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for argument in ("source-manifest", "source-manifest-sha256", "validation-summary",
                     "validation-summary-sha256", "source-ledger", "source-ledger-sha256", "output"):
        parser.add_argument("--" + argument, required=True)
    parser.add_argument("--admit-validated-pilot-value-read", action="store_true")
    parsed = parser.parse_args()
    outcome = run(parsed)
    print(json.dumps({key: outcome[key] for key in ("status", "spectral_payload_bytes", "wall_s", "cpu_s")}))
