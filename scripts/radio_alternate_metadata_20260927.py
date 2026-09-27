#!/usr/bin/env python3
"""Owner-authorized, prospectively bounded alternate-source metadata screen."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener

import radio_restart_metadata as previous

ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/radio_alternate_metadata_20260927.json"
PROTOCOL = "RADIO_ALTERNATE_DATA_2026-09-27_PROTOCOL.md"
SCRIPT = "scripts/radio_alternate_metadata_20260927.py"
TEST = "tests/test_radio_alternate_metadata.py"
INVENTORY = "results_radio_alternate_2026-09-27/prior_source_inventory.json"
OUT = ROOT / "results_radio_alternate_2026-09-27/attempt01"
FROZEN_PATHS = (CONFIG, PROTOCOL, SCRIPT, TEST, INVENTORY)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n")


class BudgetStop(previous.Stop):
    pass


class Transport:
    """Exact URL allowlist and a single non-resettable metadata allocation."""
    def __init__(self, cfg, directory):
        self.b = cfg["budgets"]
        self.directory = directory
        self.allowed = {e[k] for e in cfg["shortlist"]
                        for k in ("catalogue_url", "official_metadata_url")}
        self.start = time.monotonic()
        self.requests = self.bytes = 0
        self.receipts = []
        self.opener = build_opener(previous.NoRedirect)

    def summary(self):
        return {"requests": self.requests, "bytes_charged": self.bytes,
                "seconds": time.monotonic() - self.start,
                "counts_are_body_bytes_not_total_wire_bytes": True}

    def request(self, url, method="GET", headers=None, limit=None):
        if url not in self.allowed or method not in ("GET", "HEAD"):
            raise previous.Stop("URL or method is outside frozen metadata scope")
        limit = self.b["per_json_bytes"] if limit is None else limit
        reserve = 0 if method == "HEAD" else limit + 1
        remaining = self.b["seconds"] - (time.monotonic() - self.start)
        if remaining <= 0 or self.requests >= self.b["requests"] or self.bytes + reserve > self.b["total_bytes"]:
            raise BudgetStop("New metadata allocation exhausted; no reset allowed")
        self.requests += 1
        receipt = {"url": url, "method": method, "request_headers": headers or {},
                   "attempt": 1, "utc": datetime.now(timezone.utc).isoformat(),
                   "state": "REQUEST_CHARGED_BEFORE_TRANSPORT", "reserved_body_bytes": reserve}
        self.receipts.append(receipt)
        save(self.directory / "transport_receipts.json", self.receipts)
        observed = None
        try:
            req = Request(url, method=method, headers={"Accept-Encoding": "identity",
                          "User-Agent": "setisearch-alternate-metadata/1.0", **(headers or {})})
            try:
                response = self.opener.open(req, timeout=min(self.b["timeout_seconds"], remaining))
            except HTTPError as error:
                response = error
            with response:
                payload = b"" if method == "HEAD" else response.read(limit + 1)
                observed = len(payload)
                status = response.status
                http = dict(response.headers.items())
                final_url = response.geturl()
            self.bytes += observed
            receipt.update(state="RESPONSE_RETAINED", status=status, final_url=final_url,
                           response_headers=http, body_bytes_observed=observed,
                           bytes_charged=observed, body_sha256=sha(payload),
                           body_base64=base64.b64encode(payload).decode())
            if observed > limit or final_url != url:
                raise previous.Stop("Response byte limit or URL identity failed")
            return payload, {k.lower(): v for k, v in http.items()}, status
        except Exception as error:
            if observed is None:
                self.bytes += reserve
                receipt.update(body_bytes_observed=None, bytes_charged=reserve,
                               accounting="Unknown partial body conservatively charged full reserved cap")
            receipt.update(state="STOP_RETAINED", error=f"{type(error).__name__}: {error}")
            raise
        finally:
            receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
            save(self.directory / "transport_receipts.json", self.receipts)
            save(self.directory / "budget_state.json", self.summary())

    def json(self, url):
        payload, _, status = self.request(url)
        if status != 200:
            raise previous.Stop(f"Metadata HTTP status {status}")
        parsed = json.loads(payload)
        if isinstance(parsed, dict) and parsed.get("result") == "success":
            parsed = parsed.get("data")
        if not isinstance(parsed, list):
            raise previous.Stop("Metadata response is not a successful list")
        return parsed


def validate_catalogue(rows, entry, denied):
    urls = previous.fine_urls(rows)
    if len(urls) != 6 or entry["primary_url"] not in urls:
        raise previous.Stop("Cadence is not six fine products including the frozen primary")
    if any(not u.startswith(entry["session_prefix"]) or "/../" in u
           or not u.endswith(".gpuspec.0000.h5") for u in urls):
        raise previous.Stop("Fine product lies outside the frozen session/format")
    if set(urls) & set(denied):
        raise previous.Stop("New cadence overlaps the conservative prior/reserved URL inventory")
    return urls


def header(transport, url):
    import h5py
    _, http, status = transport.request(url, method="HEAD", limit=0)
    if status != 200 or http.get("accept-ranges") != "bytes":
        raise previous.Stop("Source does not advertise byte-range access")
    size, etag = int(http["content-length"]), http["etag"]
    if size <= 0 or not etag or etag.startswith("W/"):
        raise previous.Stop("Strong source identity unavailable")
    with previous.RangeReader(transport, url, size, etag) as remote:
        with h5py.File(remote, "r") as handle:
            dataset = handle["data"]
            dcpl = dataset.id.get_create_plist()
            result = {"url": url, "remote_size_bytes": size, "etag": etag,
                      "data_attributes": {k: previous.native_json(v) for k, v in dataset.attrs.items()},
                      "root_attributes": {k: previous.native_json(v) for k, v in handle.attrs.items()},
                      "dataset_shape": list(dataset.shape), "dataset_dtype": str(dataset.dtype),
                      "dataset_chunks": list(dataset.chunks) if dataset.chunks else None,
                      "hdf5_filters": [previous.native_json(list(dcpl.get_filter(i))) for i in range(dcpl.get_nfilters())],
                      "metadata_bytes": remote.transferred, "spectral_dataset_values_read": False}
    return result


def separation_arcsec(ra1, dec1, ra2, dec2):
    if not all(math.isfinite(float(v)) for v in (ra1, dec1, ra2, dec2)):
        raise previous.Stop("Nonfinite direction")
    if not (0 <= ra1 < 360 and 0 <= ra2 < 360 and -90 <= dec1 <= 90 and -90 <= dec2 <= 90):
        raise previous.Stop("Direction outside declared degree units/range")
    a, b, c, d = map(math.radians, (ra1, dec1, ra2, dec2))
    q = math.sin((d-b)/2)**2 + math.cos(b)*math.cos(d)*math.sin((c-a)/2)**2
    return math.degrees(2*math.asin(math.sqrt(min(1., max(0., q))))) * 3600


def pointing_checks(headers, records, entry, tolerance):
    norm = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    if len(records) != 1:
        raise previous.Stop("Official selected-planet response is not exactly one row")
    record = records[0]
    if (record.get("pl_name") != entry["planet_name"] or record.get("hostname") != entry["host"]
            or norm(record.get("hip_name")) != norm(entry["archive_target"])):
        raise previous.Stop("Official source identity mismatch")
    ra, dec = record.get("ra"), record.get("dec")
    if isinstance(ra, bool) or isinstance(dec, bool) or not isinstance(ra, (int,float)) or not isinstance(dec, (int,float)):
        raise previous.Stop("Official position missing/non-numeric")
    checks = []
    for h in headers:
        attrs = h["data_attributes"]
        if attrs["source_name"] == entry["archive_target"]:
            sep = separation_arcsec(float(attrs["src_raj"])*15, float(attrs["src_dej"]), ra, dec)
            checks.append({"url": h["url"], "separation_arcsec": sep,
                           "within_fixed_proximity": sep <= tolerance,
                           "epoch_propagated": False, "coordinates_corrected": False})
    if len(checks) != 3:
        raise previous.Stop("Expected three ON directions")
    return checks


def inspect(entry, cfg, transport, denied, directory):
    rows = transport.json(entry["catalogue_url"])
    save(directory / "catalogue.json", rows)
    urls = validate_catalogue(rows, entry, denied)
    transport.allowed.update(urls)
    headers = []
    for url in urls:
        headers.append(header(transport, url))
        save(directory / "headers.json", headers)
    headers.sort(key=lambda h: h["data_attributes"]["tstart"])
    save(directory / "headers.json", headers)
    identity = all(h["root_attributes"].get("CLASS") == "FILTERBANK"
                   and h["data_attributes"].get("telescope_id") == 6
                   and h["dataset_dtype"] == "float32" for h in headers)
    if not identity or not previous.qualifying(headers, entry["archive_target"]):
        return {"status": "HEADER_GEOMETRY_NOT_ELIGIBLE", "headers_retained": len(headers)}
    records = transport.json(entry["official_metadata_url"])
    save(directory / "official_metadata.json", records)
    checks = pointing_checks(headers, records, entry, cfg["pointing_proximity_arcsec"])
    save(directory / "pointing_checks.json", checks)
    passed = all(c["within_fixed_proximity"] for c in checks)
    return {"status": "METADATA_CONSISTENT_PREPARATION_ONLY" if passed else "HOLD_NEW_TARGET_POINTING_DISCREPANCY",
            "headers_retained": len(headers), "pointing_checks": checks,
            "full_physical_model_qualified": False, "spectral_access_authorized": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    cfg = json.loads((ROOT / CONFIG).read_text())
    snapshot = {}
    for path in FROZEN_PATHS:
        raw = (ROOT / path).read_bytes()
        if subprocess.check_output(["git", "show", args.freeze_commit+":"+path], cwd=ROOT) != raw:
            raise previous.Stop("Code/protocol differs from published freeze: " + path)
        snapshot[path] = sha(raw)
    for path, expected in {**cfg["pinned_sha256"], **cfg["unchanged_science_pins"]}.items():
        raw = subprocess.check_output(["git", "show", cfg["source_commit"]+":"+path], cwd=ROOT) if path != INVENTORY else (ROOT/path).read_bytes()
        if sha(raw) != expected:
            raise previous.Stop("Pinned prior input mismatch: " + path)
        if path == "scripts/radio_restart_metadata.py" and raw != (ROOT/path).read_bytes():
            raise previous.Stop("Imported range/qualification source changed")
    OUT.mkdir(exist_ok=False)
    save(OUT / "source_snapshot.json", {"freeze_commit": args.freeze_commit, "sha256": snapshot})
    inv = json.loads((ROOT / INVENTORY).read_text())
    denied = {s["url"] for s in inv["sources"]}
    transport = Transport(cfg, OUT)
    result = {"freeze_commit": args.freeze_commit, "started_utc": datetime.now(timezone.utc).isoformat(),
              "attempts": [], "selected": None, "spectral_dataset_values_read": False,
              "external_messages_sent": 0, "scientific_trials": 0, "prior_source_screen_usage": cfg["preceding_source_screen_usage"]}
    for entry in cfg["shortlist"]:
        directory = OUT / str(entry["cadence_id"])
        directory.mkdir()
        stop_all = False
        try:
            observed = inspect(entry, cfg, transport, denied, directory)
        except Exception as error:
            observed = {"status": "TECHNICAL_STOP", "error": f"{type(error).__name__}: {error}"}
            stop_all = isinstance(error, BudgetStop)
        observed.update(host=entry["host"], archive_target=entry["archive_target"], cadence_id=entry["cadence_id"])
        result["attempts"].append(observed)
        if observed["status"] == "METADATA_CONSISTENT_PREPARATION_ONLY":
            result["selected"] = {k: entry[k] for k in ("host", "archive_target", "planet_name", "cadence_id", "rank")}
        save(OUT / "result.json", result)
        if result["selected"] or stop_all:
            break
    result["new_metadata_usage"] = transport.summary()
    prior = cfg["preceding_source_screen_usage"]
    result["combined_source_screen_usage"] = {"requests": prior["requests"]+transport.requests,
        "bytes_charged": prior["bytes"]+transport.bytes,
        "seconds": prior["seconds"]+result["new_metadata_usage"]["seconds"]}
    result["untouched_alternatives"] = [e["cadence_id"] for e in cfg["shortlist"] if e["cadence_id"] not in {a["cadence_id"] for a in result["attempts"]}]
    result["status"] = "NEW_SOURCE_PREPARATION_SELECTED" if result["selected"] else "NO_SOURCE_SELECTED_WITHIN_FIXED_ALTERNATIVES"
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    import h5py
    result["runtime"] = {"h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version}
    save(OUT / "result.json", result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
