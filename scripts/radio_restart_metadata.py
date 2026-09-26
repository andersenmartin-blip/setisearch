#!/usr/bin/env python3
"""Bounded public radio-catalogue and HDF5-attribute inspection; no data indexing."""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.metadata
import io
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/radio_restart_metadata_20260926.json"
OUT = ROOT / "results_radio_restart_2026-09-26/attempt02"
API = "http://seti.berkeley.edu/opendata/api/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class Stop(RuntimeError):
    """A boundary/integrity failure, never a reason to skip a source."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Stop(f"Redirect refused: {req.full_url} -> {newurl}")


class Transport:
    def __init__(self, budgets, directory):
        self.b = budgets
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.start = time.monotonic()
        self.bytes = 0
        self.requests = 0
        self.receipts = []
        self.opener = build_opener(NoRedirect)

    def request(self, url, method="GET", headers=None, limit=None):
        parsed = urlparse(url)
        metadata_api = (parsed.scheme == "http" and parsed.hostname == "seti.berkeley.edu"
                        and parsed.path.startswith("/opendata/api/"))
        source_object = parsed.scheme == "https" and parsed.hostname == "bldata.berkeley.edu"
        if not (metadata_api or source_object) or parsed.username or parsed.password:
            raise Stop(f"Unapproved metadata endpoint: {url}")
        limit = self.b["per_json_bytes"] if limit is None else limit
        for attempt in range(1, self.b["attempts_per_request"] + 1):
            if (time.monotonic() - self.start > self.b["seconds"]
                    or self.requests >= self.b["requests"]
                    or self.bytes + limit > self.b["total_bytes"]):
                raise Stop("Metadata request/time/byte budget exhausted")
            self.requests += 1
            receipt = dict(url=url, method=method, attempt=attempt,
                           utc=datetime.now(timezone.utc).isoformat(),
                           request_headers=headers or {})
            transient = False
            try:
                request = Request(url, method=method, headers={
                    "User-Agent": "setisearch-radio-restart-metadata/1.0",
                    "Accept-Encoding": "identity", **(headers or {})})
                with self.opener.open(request, timeout=self.b["timeout_seconds"]) as r:
                    payload = b"" if method == "HEAD" else r.read(limit + 1)
                    self.bytes += len(payload)
                    receipt.update(status=r.status, final_url=r.geturl(),
                                   response_headers=dict(r.headers.items()),
                                   bytes=len(payload), sha256=digest(payload))
                    if len(payload) > limit:
                        raise Stop("Response exceeded predeclared byte cap")
                    receipt["body_base64"] = base64.b64encode(payload).decode()
                    if r.geturl() != url:
                        raise Stop("Response URL differs from request")
                    return payload, {k.lower(): v for k, v in r.headers.items()}, r.status
            except HTTPError as e:
                receipt.update(error=str(e), status=e.code)
                transient = e.code in {408, 429, 500, 502, 503, 504}
                if not transient or attempt == self.b["attempts_per_request"]:
                    raise Stop(str(e)) from e
            except (URLError, TimeoutError) as e:
                receipt["error"] = str(e)
                transient = True
                if attempt == self.b["attempts_per_request"]:
                    raise Stop(str(e)) from e
            except Exception as e:
                receipt["error"] = f"{type(e).__name__}: {e}"
                raise
            finally:
                self.receipts.append(receipt)
                save(self.directory / "transport_receipts.json", self.receipts)
            if transient:
                time.sleep(1)
        raise Stop("Request did not complete")

    def json(self, url):
        payload, _, status = self.request(url)
        if status != 200:
            raise Stop(f"JSON HTTP status {status}")
        obj = json.loads(payload)
        if isinstance(obj, list):
            rows = obj
        elif isinstance(obj, dict) and obj.get("result") == "success":
            rows = obj.get("data")
        else:
            raise Stop("Catalogue did not report success")
        if not isinstance(rows, list):
            raise Stop("Catalogue data is not a list")
        return rows


class RangeReader(io.RawIOBase):
    """Exact bounded metadata reads; h5py only receives an attribute-only caller."""
    def __init__(self, transport, url, size, etag):
        self.transport, self.url, self.size, self.etag = transport, url, size, etag
        self.position, self.transferred = 0, 0

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        pos = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if not 0 <= pos <= self.size:
            raise Stop("Metadata seek outside source")
        self.position = pos
        return pos

    def read(self, count=-1):
        if count < 0:
            raise Stop("Unbounded HDF5 read refused")
        count = min(count, self.size - self.position)
        if count == 0:
            return b""
        if self.transferred + count > self.transport.b["per_header_bytes"]:
            raise Stop("Per-header byte cap exceeded")
        start, end = self.position, self.position + count - 1
        payload, headers, status = self.transport.request(
            self.url, headers={"Range": f"bytes={start}-{end}", "If-Match": self.etag}, limit=count)
        self.transferred += len(payload)
        if (status != 206 or len(payload) != count
                or headers.get("content-range") != f"bytes {start}-{end}/{self.size}"
                or headers.get("etag") != self.etag):
            raise Stop("Range status, length, total size or source ETag changed")
        self.position += count
        return payload

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def native_json(value):
    if hasattr(value, "tolist"): value = value.tolist()
    if isinstance(value, bytes): return value.decode("utf-8")
    if isinstance(value, (list, tuple)): return [native_json(x) for x in value]
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    raise Stop(f"Unsupported header value {type(value)}")


def header(transport, url, expected=None):
    import h5py
    _, http, status = transport.request(url, method="HEAD", limit=0)
    if status != 200 or http.get("accept-ranges") != "bytes":
        raise Stop("Source does not advertise successful byte-range access")
    size, etag = int(http["content-length"]), http["etag"]
    if not etag or etag.startswith("W/"):
        raise Stop("Strong object identity unavailable")
    if expected and (size != expected["remote_size_bytes"] or etag != expected["etag"]):
        raise Stop("Previously pinned source size/ETag changed")
    with RangeReader(transport, url, size, etag) as remote:
        with h5py.File(remote, "r") as handle:
            dataset = handle["data"]
            # Attributes and geometry only. No dataset indexing, chunk fetch or normalization.
            attrs = {k: native_json(v) for k, v in dataset.attrs.items()}
            root_attrs = {k: native_json(v) for k, v in handle.attrs.items()}
            shape = list(dataset.shape)
            result = dict(url=url, remote_size_bytes=size, etag=etag,
                data_attributes=attrs, root_attributes=root_attrs,
                dataset_shape=shape, dataset_dtype=str(dataset.dtype),
                dataset_chunks=list(dataset.chunks) if dataset.chunks else None,
                metadata_bytes=remote.transferred, spectral_dataset_values_read=False)
    if expected:
        for key in ("data_attributes", "root_attributes", "dataset_shape", "dataset_dtype", "dataset_chunks"):
            if result[key] != expected[key]:
                raise Stop(f"Pinned header changed: {key}")
    return result


def fine_urls(rows):
    return sorted({r["url"] for r in rows if isinstance(r, dict)
        and isinstance(r.get("url"), str)
        and (r["url"].lower().endswith(".gpuspec.0000.h5")
             or r["url"].lower().endswith("_fine.h5"))})


def qualifying(headers, on):
    if len(headers) != 6: return False
    headers = sorted(headers, key=lambda x: x["data_attributes"]["tstart"])
    a = [x["data_attributes"] for x in headers]
    names = [x["source_name"] for x in a]
    geometry = {(tuple(h["dataset_shape"]), h["dataset_dtype"], x["tsamp"], x["foff"], x["fch1"], x["telescope_id"], x["machine_id"]) for h, x in zip(headers, a)}
    ranges = [sorted((x["fch1"], x["fch1"] + (h["dataset_shape"][-1] - 1) * x["foff"])) for h, x in zip(headers, a)]
    ends = [x["tstart"] + h["dataset_shape"][0] * x["tsamp"] / 86400 for h, x in zip(headers, a)]
    return (all(names[i] == on for i in (0, 2, 4))
            and all(names[i] != on for i in (1, 3, 5))
            and len(geometry) == 1 and a[-1]["tstart"] - a[0]["tstart"] <= .04
            and all(ends[i] <= a[i + 1]["tstart"] for i in range(5))
            and all(lo <= 1399.65 and hi >= 1425.85 for lo, hi in ranges))


def pilot(cfg, transport):
    expected = cfg["pilot"]
    rows = transport.json(API + "get-cadence/--71139")
    save(OUT / "pilot_catalogue.json", rows)
    urls = fine_urls(rows)
    if urls != sorted(expected["scan_urls"]):
        raise Stop("Pilot fine-product catalogue differs from frozen six-source identity")
    headers = []
    for old in expected["headers"]:
        headers.append(header(transport, old["url"], old))
        save(OUT / "pilot_headers.json", headers)
    if not qualifying(headers, cfg["archive_target"]):
        raise Stop("Pilot cadence eligibility failed")
    return dict(status="METADATA_ELIGIBLE_SPECTRA_UNOPENED", host=cfg["selected_host"],
                headers=headers, spectral_dataset_values_read=False)


def hd3651(cfg, transport):
    catalog = transport.json(API + "list-targets")
    save(OUT / "current_target_catalogue.json", catalog)
    if not all(isinstance(x, str) for x in catalog):
        raise Stop("Target catalogue schema changed")
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    aliases = sorted({x for x in catalog if norm(x) in cfg["hd3651"]["normalized_aliases"]})
    if not aliases:
        raise Stop("HD 3651 aliases absent from catalogue; coverage not established")
    rows = []
    limit = cfg["budgets"]["hd3651_query_limit"]
    for alias in aliases:
        found = transport.json(API + "query-files?" + urlencode({"target":alias,"telescope":"GBT","cadence":"True","primaryTarget":"True","grades":"fine","limit":str(limit)}))
        if len(found) >= limit:
            raise Stop("Target query reached row cap; availability incomplete")
        if any(norm(x.get("target", "")) not in cfg["hd3651"]["normalized_aliases"] for x in found):
            raise Stop("Target query returned another source")
        rows.extend(found)
    save(OUT / "hd3651_catalogue.json", dict(aliases=aliases, records=rows))
    ids = set()
    for row in rows:
        url = row.get("cadence_url")
        if not url: continue
        match = re.search(r"-([0-9]+)$", url)
        if not match: raise Stop("Unrecognized cadence identity")
        ids.add(int(match.group(1)))
    new = sorted(ids - set(cfg["hd3651"]["prior_cadence_ids"]))
    if len(new) > cfg["budgets"]["hd3651_new_cadences"]:
        return dict(status="ADDITIONAL_CATALOGUE_CADENCES_REQUIRE_SEPARATE_HEADER_SCOPE", aliases=aliases,
                    cadence_ids=sorted(ids), new_cadence_ids=new, header_checks=[])
    checks = []
    for cid in new:
        cr = transport.json(API + f"get-cadence/--{cid}")
        save(OUT / f"hd3651_cadence_{cid}.json", cr)
        urls = fine_urls(cr)
        if len(urls) != 6:
            checks.append(dict(cadence_id=cid, status="NOT_SIX_FINE_HDF5_PRODUCTS", fine_urls=urls))
            continue
        if set(urls) & set(cfg["hd3651"]["prior_scans"]):
            checks.append(dict(cadence_id=cid, status="OVERLAPS_PRIOR_M33_SCANS", fine_urls=urls))
            continue
        hh = [header(transport, u) for u in urls]
        save(OUT / f"hd3651_headers_{cid}.json", hh)
        different_date = all(int(h["data_attributes"]["tstart"]) != 57557 for h in hh)
        checks.append(dict(cadence_id=cid, status="ELIGIBLE_INDEPENDENT_DATE" if different_date and qualifying(hh,"HIP3093") else "NOT_ELIGIBLE_IN_SCOPE", headers=hh))
    return dict(status="BOUNDED_AVAILABILITY_CHECK_COMPLETE", aliases=aliases, cadence_ids=sorted(ids),
                new_cadence_ids=new, header_checks=checks,
                eligible_independent_cadences=[c["cadence_id"] for c in checks if c["status"]=="ELIGIBLE_INDEPENDENT_DATE"],
                scope="Current archive primary-target GBT fine-cadence listings for exact normalized HIP3093/HD3651 aliases; not other telescopes, formats or unpublished data")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    cfg = json.loads(CONFIG.read_text())
    for p in ["scripts/radio_restart_metadata.py", "config/radio_restart_metadata_20260926.json", "RADIO_RESTART_2026-09-26_PROTOCOL.md", "RADIO_RESTART_2026-09-26_ACCESS_AMENDMENT.md", "results_radio_restart_2026-09-26/metadata_result.json"]:
        if subprocess.check_output(["git","show",args.freeze_commit+":"+p],cwd=ROOT) != (ROOT/p).read_bytes():
            raise Stop("File differs from published freeze: " + p)
    for p,h in cfg["pinned_sha256"].items():
        if digest((ROOT/p).read_bytes()) != h: raise Stop("Pinned input changed: "+p)
    if (OUT/"metadata_result.json").exists(): raise Stop("Result already exists; refuse overwrite")
    transport = Transport(cfg["budgets"], OUT)
    prior = json.loads((OUT.parent/"metadata_result.json").read_text())
    if prior["spectral_dataset_values_read"] is not False or prior["transport"]["bytes"] != 0:
        raise Stop("Unexpected first-attempt boundary")
    transport.bytes = prior["transport"]["bytes"]
    transport.requests = prior["transport"]["requests"]
    transport.start -= prior["transport"]["seconds"]
    result = dict(freeze_commit=args.freeze_commit, source_commit=cfg["source_commit"],
                  utc=datetime.now(timezone.utc).isoformat(), spectral_dataset_values_read=False,
                  runtime={p:importlib.metadata.version(p) for p in ("numpy","h5py")})
    for key, operation in (("pilot",pilot),("hd3651",hd3651)):
        try:
            result[key] = operation(cfg, transport)
        except Exception as e:
            result[key] = dict(status="TECHNICAL_STOP", error=f"{type(e).__name__}: {e}")
        save(OUT/"metadata_result.json",result)
    result["transport"] = dict(requests=transport.requests, bytes=transport.bytes,
                               seconds=time.monotonic()-transport.start)
    save(OUT/"metadata_result.json",result)
    print(json.dumps({k:v if k not in ("pilot","hd3651") else {a:b for a,b in v.items() if a not in ("headers","header_checks")} for k,v in result.items()},indent=2))


if __name__ == "__main__":
    main()
