#!/usr/bin/env python3
"""Retrieve the frozen HARPS sample; inspect FITS headers, never spectral arrays."""
import concurrent.futures
import csv
import datetime
import hashlib
import json
import math
import pathlib
import re
import threading
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "acquisition"
START = time.monotonic()
LOCK = threading.Lock()
TOTAL_BYTES = 0
BYTE_CAP = 1_000_000_000
FILE_CAP = 12_000_000


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def value(text):
    text = text.strip()
    if text.startswith("'"):
        result = ""
        i = 1
        while i < len(text):
            if text[i] == "'":
                if i + 1 < len(text) and text[i + 1] == "'":
                    result += "'"
                    i += 2
                    continue
                break
            result += text[i]
            i += 1
        return result.strip()
    text = text.split("/", 1)[0].strip()
    if text in ("T", "F"):
        return text == "T"
    try:
        return float(text.replace("D", "E")) if any(x in text for x in ".EeDd") else int(text)
    except ValueError:
        return text


def read_header(stream):
    """Read 2880-byte header blocks only, stopping before the data payload."""
    result = {}
    for _ in range(512):
        block = stream.read(2880)
        if len(block) != 2880:
            raise ValueError("Incomplete FITS header block")
        ended = False
        for pos in range(0, 2880, 80):
            card = block[pos:pos + 80].decode("ascii")
            key = card[:8].strip()
            if key == "END":
                ended = True
                break
            if key == "HIERARCH" and "=" in card:
                k, v = card.split("=", 1)
                result[k.strip()] = value(v)
            elif card[8:10] == "= ":
                result[key] = value(card[10:])
        if ended:
            return result
    raise ValueError("FITS header exceeded bound")


def numeric_delta(actual, expected):
    return abs(float(actual) - float(expected))


def inspect(path, row, upstream):
    with path.open("rb") as stream:
        primary = read_header(stream)
        if primary.get("NAXIS") != 0:
            raise ValueError("Unexpected primary array; no flux read attempted")
        extension = read_header(stream)
    normalize = lambda s: re.sub(r"[^A-Z0-9]", "", str(s).upper())
    provenance = {k: v for k, v in primary.items() if k.startswith("PROV") or k == "ARCFILE"}
    raw_ids = sorted(set(re.findall(r"HARPS\.\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}", " ".join(map(str, provenance.values())))))
    raw_matches = sorted(set(raw_ids) & set(upstream["HARPS"]))
    ra_delta = ((float(primary["RA"]) - float(row["s_ra"]) + 180) % 360 - 180) * math.cos(math.radians(float(row["s_dec"])))
    dec_delta = float(primary["DEC"]) - float(row["s_dec"])
    sep = 3600 * math.hypot(ra_delta, dec_delta)
    checks = {
        "target_name_matches": normalize(primary.get("OBJECT")) == normalize(row["canonical_target"]),
        "instrument_harps": primary.get("INSTRUME") == "HARPS",
        "mjd_matches_within_0p00864_s": numeric_delta(primary["MJD-OBS"], row["t_min"]) <= 1e-7,
        "exptime_matches_within_0p02_s": numeric_delta(primary["EXPTIME"], row["t_exptime"]) <= 0.02,
        "position_matches_within_1_arcsec": sep <= 1.0,
        "single_spectrum_table": extension.get("NAXIS2") == 1,
        "has_raw_provenance": bool(raw_ids),
        "no_upstream_adp_match": row["dp_id"] not in upstream["ADP"],
        "no_upstream_raw_match": not raw_matches,
    }
    keyset = {"OBJECT", "INSTRUME", "DATE-OBS", "MJD-OBS", "EXPTIME", "RA", "DEC", "SNR", "SPECSYS", "WAVELMIN", "WAVELMAX", "SPEC_BIN", "SPEC_RES", "FLUXCAL", "NCOMBINE", "IMAGETYP", "HIERARCH ESO DRS BERV", "HIERARCH ESO DRS BERVMX", "HIERARCH ESO DPR TYPE"}
    ext = {k: v for k, v in extension.items() if k.startswith(("TTYPE", "TFORM", "TUNIT", "TUCD", "TCOMM")) or k in {"NAXIS1", "NAXIS2", "EXTNAME"}}
    return {
        "checks": checks,
        "header_status": "PASS_METADATA_ONLY" if all(checks.values()) else "EXCLUDED_PENDING_REVIEW",
        "position_difference_arcsec": sep,
        "primary_header": {k: v for k, v in primary.items() if k in keyset},
        "extension_header": ext,
        "provenance_header": provenance,
        "raw_progenitor_ids": raw_ids,
        "upstream_raw_matches": raw_matches,
        "array_values_inspected": False,
    }


def fetch(row, upstream):
    global TOTAL_BYTES
    role = row["role"]
    folder = "main" if role == "main_unopened" else ("development" if role == "development" else "validation")
    data_dir = ROOT / "data" / folder
    data_dir.mkdir(parents=True, exist_ok=True)
    filename = row["dp_id"].replace(":", "_") + ".fits"
    path = data_dir / filename
    receipt_path = OUT / "receipts" / (row["dp_id"].replace(":", "_") + ".json")
    url = "https://dataportal.eso.org/dataPortal/file/" + row["dp_id"]
    receipt = {"dp_id": row["dp_id"], "canonical_target": row["canonical_target"], "role": role, "source_url": url, "path": str(path), "started_utc": now(), "attempts": []}
    if path.exists() and receipt_path.exists():
        previous = json.loads(receipt_path.read_text())
        if previous.get("sha256") == hashlib.sha256(path.read_bytes()).hexdigest():
            previous["cached_reuse"] = True
            return previous
        raise RuntimeError("Existing file changed: " + str(path))
    for timeout in (20, 60):
        if time.monotonic() - START > 540:
            receipt["download_status"] = "NOT_RUN_WALL_BOUND"
            break
        attempt = {"started_utc": now(), "timeout_seconds": timeout}
        t0 = time.monotonic()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "SETI-HARPS-pilot/1.0 (public archive research)"})
            chunks = []
            size = 0
            with urllib.request.urlopen(request, timeout=timeout) as response:
                attempt["http_status"] = response.status
                attempt["response_headers"] = {k: response.headers.get(k) for k in ("Content-Type", "Content-Length", "Content-Disposition", "Last-Modified")}
                while True:
                    block = response.read(1_048_576)
                    if not block:
                        break
                    size += len(block)
                    with LOCK:
                        TOTAL_BYTES += len(block)
                        if TOTAL_BYTES > BYTE_CAP:
                            raise RuntimeError("Total input byte cap exceeded")
                    if size > FILE_CAP:
                        raise RuntimeError("Single-file byte cap exceeded")
                    chunks.append(block)
            payload = b"".join(chunks)
            if not payload.startswith(b"SIMPLE  ") or len(payload) % 2880:
                raise ValueError("Response not a complete padded FITS file")
            expected_length = attempt["response_headers"]["Content-Length"]
            if expected_length and int(expected_length) != len(payload):
                raise ValueError("Content-Length mismatch")
            partial = path.with_suffix(".part")
            partial.write_bytes(payload)
            partial.replace(path)
            receipt.update({"download_status": "DOWNLOADED", "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
            receipt.update(inspect(path, row, upstream))
            attempt["outcome"] = "SUCCESS"
            attempt["elapsed_seconds"] = time.monotonic() - t0
            receipt["attempts"].append(attempt)
            break
        except Exception as exc:
            attempt.update({"outcome": "FAILED", "error_type": type(exc).__name__, "error": str(exc), "elapsed_seconds": time.monotonic() - t0})
            receipt["attempts"].append(attempt)
            receipt["download_status"] = "FAILED"
            if path.exists():
                receipt["download_status"] = "DOWNLOADED_HEADER_REVIEW_FAILED"
                receipt["header_status"] = "EXCLUDED_PENDING_REVIEW"
                break
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403, 404):
                break
    receipt["finished_utc"] = now()
    dump(receipt_path, receipt)
    print(json.dumps({"dp_id": receipt["dp_id"], "role": role, "download_status": receipt["download_status"], "header_status": receipt.get("header_status"), "path": str(path)}), flush=True)
    return receipt


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "receipts").mkdir(exist_ok=True)
    files = [ROOT / "selection" / "DEVELOPMENT_AND_VALIDATION.csv", ROOT / "selection" / "MAIN100.csv"]
    rows = []
    for file in files:
        rows.extend(csv.DictReader(file.open()))
    upstream_path = ROOT / "literature" / "UPSTREAM_REFERENCED_IDS.json"
    upstream = json.loads(upstream_path.read_text())
    dump(OUT / "ACQUISITION_SCOPE.json", {"created_utc": now(), "selected_rows": len(rows), "input_selection_hashes": {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}, "upstream_id_list_sha256": hashlib.sha256(upstream_path.read_bytes()).hexdigest(), "code_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(), "max_workers": 3, "attempt_timeouts_seconds": [20, 60], "input_byte_cap": BYTE_CAP, "per_file_byte_cap": FILE_CAP, "array_values_inspected": False})
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        receipts = list(pool.map(lambda row: fetch(row, upstream), rows))
    dump(OUT / "DOWNLOAD_MANIFEST.json", receipts)
    fields = ["dp_id", "canonical_target", "role", "download_status", "header_status", "bytes", "sha256", "path", "source_url", "raw_progenitor_ids", "upstream_raw_matches"]
    with (OUT / "DOWNLOAD_MANIFEST.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for receipt in receipts:
            writer.writerow({k: json.dumps(receipt[k]) if isinstance(receipt.get(k), (dict, list)) else receipt.get(k, "") for k in fields})
    counts = {}
    for receipt in receipts:
        key = receipt.get("header_status", receipt["download_status"])
        counts[key] = counts.get(key, 0) + 1
    summary = {"finished_utc": now(), "elapsed_seconds": time.monotonic() - START, "network_payload_bytes": TOTAL_BYTES, "selected_files": len(rows), "result_counts": counts, "array_values_inspected": False}
    dump(OUT / "ACQUISITION_RESULT.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
