#!/usr/bin/env python3
"""Evaluate the frozen two-visit LS8F GJ 514 DEFAULT-L2 screen."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from astropy.io import fits

from seti_repeater.cheops_l2_stable import (
    DURATIONS, GUARD, SCREEN, SIDE, stable_score_window,
)

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "results_ls8f_l2_metadata"
OUT = ROOT / "results_ls8f_l2_screen"
BASE = "https://cheops-webapp-pg.obsuksprd2.unige.ch/"
KEYS = [
    "CH_PR100018_TG007501_V0300",
    "CH_PR100018_TG007502_V0300",
]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def dtype(header: fits.Header) -> np.dtype:
    fields = []
    for i in range(1, header["TFIELDS"] + 1):
        n, code = re.fullmatch(r"(\d*)([ADEJI])", header[f"TFORM{i}"]).groups()
        n = int(n or "1")
        name = header[f"TTYPE{i}"]
        if code == "A":
            fields.append((name, f"S{n}"))
        else:
            typ = {"D": ">f8", "E": ">f4", "J": ">i4", "I": ">i2"}[code]
            fields.append((name, typ, (n,)) if n != 1 else (name, typ))
    out = np.dtype(fields)
    assert out.itemsize == header["NAXIS1"]
    return out


def get_url(key: str) -> str:
    payload = {
        "fileType": "lightcurves",
        "filters": {"file_key": {"equal": [key]}},
        "aperture": "default",
    }
    with urlopen(Request(
        BASE + "download",
        data=json.dumps(payload).encode(),
        headers={"Accept": "application/json", "User-Agent": "dace-query/3.0.1"},
    ), timeout=45) as response:
        info = json.load(response)
    if not isinstance(info.get("key"), str) or not info["key"]:
        raise RuntimeError(f"exact DEFAULT lightcurve unavailable: {key}")
    return BASE + "download/photometry/" + info["key"] + "?compressed=false"


def read_table(key: str, meta: dict) -> tuple[bytes, dict]:
    start = int(meta["table_data_start"])
    count = int(meta["table_bytes_declared"])
    headers = {
        "Range": f"bytes={start}-{start + count - 1}",
        "If-Match": meta["etag"],
        "Accept": "application/octet-stream",
        "Accept-Encoding": "identity",
    }
    with urlopen(Request(get_url(key), headers=headers), timeout=45) as response:
        assert response.status == 206
        assert response.headers["Content-Range"] == (
            f"bytes {start}-{start + count - 1}/{meta['total_file_bytes']}"
        )
        assert int(response.headers["Content-Length"]) == count
        assert response.headers.get("ETag") == meta["etag"]
        assert response.headers.get("Content-Disposition") == meta["content_disposition"]
        raw = response.read(count + 1)
        assert len(raw) == count
        receipt = {
            "file_key": key,
            "start": start,
            "count": count,
            "sha256": sha(raw),
            "status": response.status,
            "etag": response.headers.get("ETag"),
            "content_range": response.headers.get("Content-Range"),
            "content_disposition": response.headers.get("Content-Disposition"),
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        }
    return raw, receipt


def signed_clusters(rows: list[dict], sign: int) -> list[dict]:
    selected = sorted(
        (r for r in rows if sign * r["score"] >= SCREEN),
        key=lambda r: (r["start"], r["start"] + r["duration"]),
    )
    groups = []
    for row in selected:
        end = row["start"] + row["duration"] - 1
        if not groups or row["start"] > groups[-1]["max_end"] + 1:
            groups.append({"min_start": row["start"], "max_end": end, "members": [row]})
        else:
            groups[-1]["max_end"] = max(groups[-1]["max_end"], end)
            groups[-1]["members"].append(row)
    result = []
    for i, group in enumerate(groups):
        representative = min(
            group["members"],
            key=lambda r: (-sign * r["score"], r["duration"], r["start"]),
        )
        result.append({
            "cluster_id": i,
            "min_start": group["min_start"],
            "max_end": group["max_end"],
            "representative": dict(representative),
            "members": [
                {"start": r["start"], "duration": r["duration"], "score": r["score"]}
                for r in group["members"]
            ],
        })
    return result


def evaluate_visit(key: str, meta: dict) -> dict:
    folder = OUT / key
    folder.mkdir()
    raw, receipt = read_table(key, meta)
    (folder / "lightcurve_table.bin").write_bytes(raw)
    save(folder / "source.json", receipt)

    header = fits.Header.fromstring(
        (META / key / "lightcurve_header.bin").read_bytes().decode("ascii"), sep=""
    )
    table = np.frombuffer(raw, dtype=dtype(header), count=meta["rows"])
    cadence = float(meta["keywords"]["TEXPTIME"])
    bjd = table["BJD_TIME"].astype(float)
    flux = table["FLUX"].astype(float)
    err = table["FLUXERR"].astype(float)
    status = table["STATUS"].astype(np.int64)
    event = table["EVENT"].astype(np.int64)

    rows = []
    for duration in DURATIONS:
        for start in range(len(table) - duration + 1):
            row = stable_score_window(
                bjd, flux, err, status, event, start, duration, cadence
            )
            if row is not None:
                rows.append(row)
    rows.sort(key=lambda r: (r["duration"], r["start"]))
    (folder / "ledger.jsonl.gz").write_bytes(gzip.compress(
        "".join(json.dumps(r, sort_keys=True, allow_nan=False) + "\n" for r in rows).encode(),
        mtime=0,
    ))

    positive = signed_clusters(rows, +1)
    negative = signed_clusters(rows, -1)
    save(folder / "clusters.json", {"positive": positive, "negative": negative})

    per_duration = []
    for duration in DURATIONS:
        selected = [r for r in rows if r["duration"] == duration]
        per_duration.append({
            "duration_rows": duration,
            "duration_seconds": duration * cadence,
            "eligible_windows": len(selected),
            "positive_windows": sum(r["score"] >= SCREEN for r in selected),
            "negative_windows": sum(r["score"] <= -SCREEN for r in selected),
            "maximum_score": max((r["score"] for r in selected), default=None),
            "minimum_score": min((r["score"] for r in selected), default=None),
        })
    union = {i for r in rows for i in r["event_indices"]}
    valid = (
        np.isfinite(bjd) & np.isfinite(flux) & np.isfinite(err)
        & (err > 0) & (status == 0)
    )
    result = {
        "file_key": key,
        "rows": len(table),
        "status_zero_finite_rows": int(valid.sum()),
        "cadence_seconds": cadence,
        "eligible_windows": len(rows),
        "duration_results": per_duration,
        "positive_windows": sum(r["score"] >= SCREEN for r in rows),
        "negative_windows": sum(r["score"] <= -SCREEN for r in rows),
        "positive_clusters": len(positive),
        "negative_clusters": len(negative),
        "maximum_score": max((r["score"] for r in rows), default=None),
        "minimum_score": min((r["score"] for r in rows), default=None),
        "unique_event_rows": len(union),
        "eligible_event_row_union_seconds": len(union) * cadence,
    }
    save(folder / "summary.json", result)
    return result


def manifest() -> None:
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text("".join(
        f"{sha(p.read_bytes())}  {p.relative_to(OUT)}\n" for p in files
    ))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", required=True)
    args = parser.parse_args()
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip() == args.freeze
    assert not subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT
    )
    assert (SIDE, GUARD, DURATIONS, SCREEN) == (12, 2, (1, 2, 3), 8.5)
    assert not OUT.exists(), "refuse completed LS8F screen overwrite"

    combined = json.loads((META / "summary.json").read_text())
    assert combined["status"] == "PASS_COMPATIBLE"
    assert combined["table_data_bytes_acquired"] == 0
    assert combined["selected_keys"] == KEYS
    by_key = {r["file_key"]: r for r in combined["products"]}

    OUT.mkdir()
    results = [evaluate_visit(key, by_key[key]) for key in KEYS]
    summary = {
        "stage": "LS8F_GJ514_TWO_VISIT_L2_SCREEN",
        "status": "COMPLETE_UNAUDITED",
        "evaluation_freeze_commit": args.freeze,
        "target": "GJ 514",
        "selected_keys": KEYS,
        "method": "prospective flux-centered implementation of unchanged LS7X/LS8A/LS8B DEFAULT-L2 rule",
        "sideband_rows_each_side": SIDE,
        "guard_rows": GUARD,
        "durations_rows": list(DURATIONS),
        "screen_threshold": SCREEN,
        "visits": results,
        "totals": {
            "rows": sum(r["rows"] for r in results),
            "eligible_windows": sum(r["eligible_windows"] for r in results),
            "positive_windows": sum(r["positive_windows"] for r in results),
            "negative_windows": sum(r["negative_windows"] for r in results),
            "positive_clusters": sum(r["positive_clusters"] for r in results),
            "negative_clusters": sum(r["negative_clusters"] for r in results),
            "science_table_bytes": sum(by_key[k]["table_bytes_declared"] for k in KEYS),
        },
        "other_apertures_opened": False,
        "image_bytes_acquired": 0,
        "raw_imagettes_opened": False,
        "detector_qualified": False,
        "candidate_claims": 0,
        "interpretation": "independent two-visit L2 screening; signed endpoints are descriptive controls, not Gaussian significances",
    }
    save(OUT / "summary.json", summary)
    manifest()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
