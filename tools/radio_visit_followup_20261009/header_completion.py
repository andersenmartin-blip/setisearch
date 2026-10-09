"""Complete metadata from retained HDF5 heap/continuation pointer evidence.

All GET spans are listed and pinned before execution. Only cached metadata is
exposed to HDF5. The earlier prefix job and its failure receipts are preserved.
"""
import datetime
import hashlib
import json
import math
import resource
import struct
import time
import urllib.request
from pathlib import Path
from header_probe import NoRedirect, PrefixOnly, plain

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "tools/radio_visit_followup_20261009/completion_scope.json"
OUT = ROOT / "results/radio_visit_followup_20261009/header_completion"


class CachedOnly(PrefixOnly):
    def __init__(self, ranges, logical_size):
        self.ranges, self.size, self.position, self.reads = ranges, logical_size, 0, []

    def readinto(self, buffer):
        start, end, parts = self.position, self.position+len(buffer), []
        current = start
        while current < end:
            matches = [(offset, body) for offset, body in self.ranges
                       if offset <= current < offset+len(body)]
            if len(matches) != 1:
                raise ValueError(f"Missing/overlapping cached metadata at {current}; no GET")
            offset, body = matches[0]
            stop = min(end, offset+len(body))
            parts.append(body[current-offset:stop-offset])
            current = stop
        buffer[:] = b"".join(parts)
        self.reads.append([start, len(buffer)])
        self.position = end
        return len(buffer)


def run(item, opener, h5py):
    result = {"session": item["session"], "url": item["url"], "receipts": [],
              "spectral_values_read": False, "dataset_value_accesses": 0,
              "body_bytes_received": 0, "started_UTC": datetime.datetime.now(
                  datetime.timezone.utc).isoformat()}
    def save():
        (OUT / (item["session"]+"_result.json")).write_text(json.dumps(result, indent=2)+"\n")
    try:
        prefix = (ROOT / item["prefix_path"]).read_bytes()
        if len(prefix) != 4096 or hashlib.sha256(prefix).hexdigest() != item["prefix_sha256"]:
            raise ValueError("Retained prefix pin mismatch")
        heap = item["heap_offset"]
        if prefix[heap:heap+4] != b"GCOL" or struct.unpack_from("<Q", prefix, heap+8)[0] != 4096:
            raise ValueError("Heap pointer evidence mismatch")
        ranges = [(0, prefix)]
        for span in item["new_metadata_ranges"]:
            offset, length = span["offset"], span["length"]
            if span["kind"] == "object_header_continuation":
                pointer = struct.unpack_from("<QQ", prefix, span["pointer_payload_offset"])
                if pointer != (offset, length):
                    raise ValueError("Continuation pointer changed")
            elif span["kind"] == "global_heap_remainder":
                if offset != 4096 or length != heap+4096-4096:
                    raise ValueError("Heap remainder range changed")
            else:
                raise ValueError("Unknown metadata evidence kind")
            if not 0 < length <= 4096 or offset+length > item["file_size_bytes"]:
                raise ValueError("Invalid pinned metadata range")
            receipt = {**span, "state": "RESERVED", "body_bytes_received": 0,
                       "range": f"bytes={offset}-{offset+length-1}"}
            result["receipts"].append(receipt)
            save()
            request = urllib.request.Request(item["url"], headers={"Accept-Encoding": "identity",
                        "If-Match": item["etag"], "Range": receipt["range"]})
            with opener.open(request, timeout=20) as response:
                receipt.update(status=response.status, etag=response.headers.get("ETag"),
                               content_range=response.headers.get("Content-Range"))
                if (response.status != 206 or response.geturl() != item["url"] or
                    response.headers.get("ETag") != item["etag"] or
                    response.headers.get("Content-Range") != f"bytes {offset}-{offset+length-1}/{item['file_size_bytes']}" or
                    int(response.headers.get("Content-Length", -1)) != length or
                    response.headers.get("Content-Encoding", "identity") != "identity"):
                    raise ValueError("Pinned metadata range refused before body read")
                body = response.read(length)
                receipt["body_bytes_received"] = len(body)
                result["body_bytes_received"] += len(body)
            if len(body) != length:
                raise ValueError("Truncated metadata range")
            name = item["session"]+f"_{offset}_{length}.bin"
            (OUT / name).write_bytes(body)
            receipt.update(state="PASS", body_sha256=hashlib.sha256(body).hexdigest(), retained_file=name)
            ranges.append((offset, body))
            save()
        virtual = CachedOnly(ranges, item["file_size_bytes"])
        with h5py.File(virtual, "r") as handle:
            result["root_attributes"] = {k: plain(v) for k, v in handle.attrs.items()}
            dataset = handle["data"]
            a = {k: plain(v) for k, v in dataset.attrs.items()}
            result.update(data_attributes=a, shape=list(dataset.shape), dtype=str(dataset.dtype),
                          chunks=list(dataset.chunks))
        result["metadata_reader_ranges"] = virtual.reads
        if a["source_name"] != "HIP98505" or result["root_attributes"]["CLASS"] != "FILTERBANK":
            raise ValueError("Target/product identity mismatch")
        if result["shape"][2] != int(a["nchans"]) or int(a["nifs"]) != result["shape"][1]:
            raise ValueError("Channel/feed geometry mismatch")
        for key in ["fch1", "foff", "tstart", "tsamp", "src_raj", "src_dej"]:
            if not math.isfinite(float(a[key])):
                raise ValueError("Nonfinite frequency/time/position metadata")
        start = item["filename_MJD"]+item["filename_seconds"]/86400
        result["header_minus_filename_start_s"] = (float(a["tstart"])-start)*86400
        if abs(result["header_minus_filename_start_s"]) > 2 or float(a["tstart"]) < 58000:
            raise ValueError("Later visit time identity mismatch")
        first = float(a["fch1"])
        last = first+(int(a["nchans"])-1)*float(a["foff"])
        result["frequency_center_interval_MHz"] = [min(first, last), max(first, last)]
        result["covers_unresolved_1424_079069888_MHz"] = min(first, last) <= 1424.0790698880364 <= max(first, last)
        result["status"] = "TARGET_TIME_GEOMETRY_AND_FILE_COVERAGE_VERIFIED"
    except Exception as error:
        result.update(status="METADATA_INCOMPLETE_NO_RETRY", error_type=type(error).__name__, error=str(error))
    save()
    print(json.dumps({k: result.get(k) for k in ["session", "status", "frequency_center_interval_MHz",
                      "covers_unresolved_1424_079069888_MHz", "error"]}), flush=True)
    return result


def main():
    start, cpu = time.monotonic(), time.process_time()
    scope = json.loads(SCOPE.read_text())
    for name, pin in scope["code_pins"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != pin:
            raise ValueError("Completion reader pin mismatch")
    OUT.mkdir(exist_ok=False)
    import h5py
    opener = urllib.request.build_opener(NoRedirect())
    rows = [run(item, opener, h5py) for item in scope["sources"]]
    result = {"sources": rows, "scope_sha256": hashlib.sha256(SCOPE.read_bytes()).hexdigest(),
              "body_bytes_received": sum(r["body_bytes_received"] for r in rows),
              "GET_attempts": sum(len(r["receipts"]) for r in rows), "new_HEAD_attempts": 0,
              "process_cpu_s": time.process_time()-cpu, "wall_s": time.monotonic()-start,
              "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
              "spectral_values_read": False, "dataset_value_accesses": 0,
              "h5py_version": h5py.__version__, "HDF5_version": h5py.version.hdf5_version}
    (OUT / "COMPLETION_RESULT.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
