#!/usr/bin/env python3
"""
Stage 2 Live IPv4 Acquisition for Spor N3 (1,800 zero-overlap Gaia DDF stars):
- Verifies METHOD_LOCK & IMPLEMENTATION_LOCK BEFORE any photometry download
- Forces IPv4 (socket.AF_INET) to avoid broken IPv6 route to CC-IN2P3
- Downloads 72 sequential batches x 25 objects from Fink LSST /api/v1/sources & /api/v1/fp
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import socket
import time
import urllib.request
from pathlib import Path
from typing import Any

# Critical IPv4 force helper
_orig_gai = socket.getaddrinfo
def _ipv4_gai(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_gai(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_gai

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n3_20261127_rubin_v3_1800ddf"
INP = ROOT / "inputs_n3_20261127"
RES = WS / "results"
FINK_BASE = "https://api.lsst.fink-portal.org"

SOURCES_COLS = ",".join([
    "r:diaObjectId", "r:diaSourceId", "r:midpointMjdTai", "r:band", "r:ra", "r:dec",
    "r:scienceFlux", "r:scienceFluxErr", "r:psfFlux", "r:psfFluxErr",
    "r:pixelFlags_saturated", "r:pixelFlags_saturatedCenter",
    "r:pixelFlags_cr", "r:pixelFlags_crCenter",
    "r:pixelFlags_bad", "r:pixelFlags_edge", "r:pixelFlags_offimage",
    "r:pixelFlags_nodata", "r:pixelFlags_interpolatedCenter", "r:isDipole",
    "r:forced_PsfFlux_flag", "r:forced_PsfFlux_flag_edge", "r:forced_PsfFlux_flag_noGoodPixels",
    "r:timeWithdrawnMjdTai", "r:reliability", "r:snr",
])
FP_COLS = ",".join([
    "r:diaObjectId", "r:diaForcedSourceId", "r:midpointMjdTai", "r:band",
    "r:scienceFlux", "r:scienceFluxErr", "r:psfFlux", "r:psfFluxErr",
    "r:timeWithdrawnMjdTai",
])


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def post_fink(ep: str, payload: dict[str, Any], timeout: int = 45, max_attempts: int = 6) -> tuple[bytes, dict[str, Any]]:
    url = FINK_BASE + ep
    body = json.dumps(payload).encode("utf-8")
    last_err = None
    for att in range(1, max_attempts + 1):
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "User-Agent": "SETI-Rubin-V3/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                rec = {"utc": _now(), "url": url, "attempt": att, "http_status": r.status, "elapsed_s": round(time.monotonic() - t0, 3), "bytes": len(raw), "sha256": _sha256_bytes(raw)}
                return raw, rec
        except Exception as exc:
            last_err = repr(exc)
            time.sleep(min(20, 1.5 * (2 ** (att - 1))))
    raise RuntimeError(f"Failed {url}: {last_err}")


def fetch_batches_seq(batches: list[list[str]], ep: str, cols: str, out_dir: Path, prefix: str) -> tuple[int, int]:
    total_rows = total_bytes = 0
    n_tot = len(batches)
    for idx, batch in enumerate(batches):
        out_p = out_dir / f"{prefix}_{idx:03d}.json"
        if out_p.exists():
            rows = json.loads(out_p.read_text(encoding="utf-8"), parse_int=str)
            total_rows += len(rows)
            total_bytes += out_p.stat().st_size
            continue
        try:
            raw, rec = post_fink(ep, {"diaObjectId": ",".join(batch), "columns": cols, "output-format": "json"})
        except Exception:
            # Fallback: split dense 25-object batch into 5-object micro-batches
            merged: list[Any] = []
            for j in range(0, len(batch), 5):
                sub_raw, rec = post_fink(ep, {"diaObjectId": ",".join(batch[j:j + 5]), "columns": cols, "output-format": "json"})
                merged.extend(json.loads(sub_raw.decode("utf-8"), parse_int=str))
                time.sleep(0.1)
            raw = json.dumps(merged).encode("utf-8")
            rec["split_microbatches"] = True
            rec["sha256"] = _sha256_bytes(raw)
            rec["bytes"] = len(raw)
        out_p.write_bytes(raw)
        out_p.with_suffix(".json.receipt.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        rows = json.loads(raw.decode("utf-8"), parse_int=str)
        total_rows += len(rows)
        total_bytes += len(raw)
        if (idx + 1) % 12 == 0 or (idx + 1) == n_tot:
            print(f"  [{prefix}] batch {idx+1}/{n_tot}: {len(rows)} rows (cum={total_rows:,})", flush=True)
        time.sleep(0.15)
    return total_rows, total_bytes


def main() -> int:
    ml = json.loads((RES / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    il = json.loads((RES / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    assert _sha256_file(RES / "METHOD_LOCK.json") == il["method_lock_sha256"], "METHOD_LOCK mismatch!"
    for rel, exp in ml["sha256"].items():
        assert _sha256_file(WS / rel) == exp, f"Locked file tampered before Stage 2: {rel}"

    started_p = RES / "STAGE2_STARTED.json"
    if not started_p.exists():
        started_p.write_text(json.dumps({"utc": _now(), "method_lock_utc": ml["locked_utc"]}, indent=2) + "\n", encoding="utf-8")

    cohort = list(csv.DictReader((RES / "N3_COHORT_1800_FROZEN.csv").open(encoding="utf-8")))
    oids = [r["diaObjectId"] for r in cohort]
    batches = [oids[i:i + 25] for i in range(0, len(oids), 25)]
    assert len(batches) == 72

    print(f"Downloading sequential /sources & /fp for {len(oids)} stars ({len(batches)} batches x 25, IPv4 forced)...", flush=True)
    src_rows, src_bytes = fetch_batches_seq(batches, "/api/v1/sources", SOURCES_COLS, INP / "fink_sources", "n3_sources")
    fp_rows, fp_bytes = fetch_batches_seq(batches, "/api/v1/fp", FP_COLS, INP / "fink_fp", "n3_fp")

    manifest = {
        "completed_utc": _now(),
        "stars": len(oids),
        "batches_per_stream": len(batches),
        "batch_size": 25,
        "sources_rows": src_rows,
        "sources_bytes": src_bytes,
        "fp_rows": fp_rows,
        "fp_bytes": fp_bytes,
    }
    (INP / "STAGE2_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE 2 COMPLETE: sources={src_rows:,} rows ({src_bytes:,} B), fp={fp_rows:,} rows ({fp_bytes:,} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
