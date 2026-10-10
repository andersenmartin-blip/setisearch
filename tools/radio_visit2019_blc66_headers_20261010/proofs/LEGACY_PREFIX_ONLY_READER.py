"""One HEAD and one exactly bounded 4096-byte HDF5 prefix per frozen URL.

Only root/data attributes, dataspace and datatype are inspected. No dataset
index, slice, codec or power calculation is invoked. Missing prefix metadata
stops the probe without additional fetches.
"""
import datetime
import hashlib
import io
import json
import resource
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "tools/radio_visit_followup_20261009/header_scope.json"
OUT = ROOT / "results/radio_visit_followup_20261009/headers"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Exact header source redirects prohibited")


class PrefixOnly(io.RawIOBase):
    def __init__(self, prefix, logical_size):
        self.prefix, self.size, self.position = prefix, logical_size, 0
        self.reads = []

    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.position+offset if whence == 1 else self.size+offset
        if position < 0:
            raise ValueError("Negative metadata seek")
        self.position = position
        return position

    def tell(self):
        return self.position

    def readinto(self, buffer):
        n = len(buffer)
        if self.position+n > len(self.prefix):
            raise ValueError("HDF5 metadata outside retained prefix; no follow-up GET")
        self.reads.append([self.position, n])
        buffer[:] = self.prefix[self.position:self.position+n]
        self.position += n
        return n


def plain(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if hasattr(value, "tolist"):
        return plain(value.tolist())
    if isinstance(value, (list, tuple)):
        return [plain(x) for x in value]
    return value


def run(item, opener, h5py):
    started, cpu = time.monotonic(), time.process_time()
    r = {"session": item["session"], "url": item["url"], "selection": item["selection"],
         "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
         "requests_attempted": 0, "body_bytes_received": 0, "spectral_values_read": False,
         "retry_count": 0, "prefix_bytes_requested": 4096}
    try:
        r["requests_attempted"] += 1
        with opener.open(urllib.request.Request(item["url"], method="HEAD",
                         headers={"Accept-Encoding": "identity"}), timeout=20) as response:
            if response.status != 200 or response.geturl() != item["url"]:
                raise ValueError("HEAD exact source identity not returned")
            size = int(response.headers["Content-Length"])
            etag = response.headers["ETag"]
            r.update(file_size_bytes=size, etag=etag, head_status=response.status,
                     last_modified=response.headers.get("Last-Modified"))
        r["requests_attempted"] += 1
        request = urllib.request.Request(item["url"], headers={"Accept-Encoding": "identity",
                         "Range": "bytes=0-4095", "If-Match": etag})
        with opener.open(request, timeout=20) as response:
            r["get_status"] = response.status
            if (response.status != 206 or response.geturl() != item["url"] or
                response.headers.get("ETag") != etag or
                response.headers.get("Content-Range") != f"bytes 0-4095/{size}" or
                int(response.headers.get("Content-Length", -1)) != 4096 or
                response.headers.get("Content-Encoding", "identity") != "identity"):
                raise ValueError("Exact range/ETag/encoding rejected before reading body")
            body = response.read(4096)
            r["body_bytes_received"] = len(body)
        if len(body) != 4096 or body[:8] != b"\x89HDF\r\n\x1a\n":
            raise ValueError("Incomplete HDF5 prefix")
        r["prefix_sha256"] = hashlib.sha256(body).hexdigest()
        (OUT / (item["session"]+"_prefix.bin")).write_bytes(body)
        virtual = PrefixOnly(body, size)
        with h5py.File(virtual, "r") as handle:
            dataset = handle["data"]
            r["root_attributes"] = {k: plain(v) for k, v in handle.attrs.items()}
            r["data_attributes"] = {k: plain(v) for k, v in dataset.attrs.items()}
            r["shape"] = list(dataset.shape)
            r["dtype"] = str(dataset.dtype)
            r["chunks"] = list(dataset.chunks) if dataset.chunks else None
            a = r["data_attributes"]
            first = float(a["fch1"])
            last = first+(int(a["nchans"])-1)*float(a["foff"])
            r["frequency_center_interval_MHz"] = [min(first, last), max(first, last)]
            r["covers_unresolved_1424_079069888_MHz"] = min(first, last) <= 1424.0790698880364 <= max(first, last)
        r["metadata_reader_ranges"] = virtual.reads
        r["status"] = "HEADER_METADATA_READ"
    except Exception as error:
        r.update(status="METADATA_FAILED_NO_RETRY", error_type=type(error).__name__, error=str(error))
    finally:
        r.update(process_cpu_s=time.process_time()-cpu, wall_s=time.monotonic()-started)
        (OUT / (item["session"]+"_receipt.json")).write_text(json.dumps(r, indent=2)+"\n")
    print(json.dumps({k: r.get(k) for k in ["session", "status", "body_bytes_received",
          "frequency_center_interval_MHz", "covers_unresolved_1424_079069888_MHz", "error"]}), flush=True)
    return r


def main():
    started, cpu = time.monotonic(), time.process_time()
    scope = json.loads(SCOPE.read_text())
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != scope["reader_sha256"]:
        raise ValueError("Header reader differs from freeze")
    OUT.mkdir(exist_ok=False)
    import h5py
    opener = urllib.request.build_opener(NoRedirect())
    rows = [run(item, opener, h5py) for item in scope["sources"]]
    result = {"scope_sha256": hashlib.sha256(SCOPE.read_bytes()).hexdigest(), "sources": rows,
              "process_cpu_s": time.process_time()-cpu, "wall_s": time.monotonic()-started,
              "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
              "h5py_version": h5py.__version__, "HDF5_version": h5py.version.hdf5_version,
              "spectral_values_read": False, "dataset_value_accesses": 0,
              "body_bytes_received": sum(r["body_bytes_received"] for r in rows),
              "requests_attempted": sum(r["requests_attempted"] for r in rows)}
    (OUT / "HEADER_RESULT.json").write_text(json.dumps(result, indent=2)+"\n")


if __name__ == "__main__":
    main()
