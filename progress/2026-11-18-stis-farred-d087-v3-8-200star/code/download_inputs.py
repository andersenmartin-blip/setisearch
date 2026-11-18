#!/usr/bin/env python3
"""
Post-Lock Multi-Archive FITS Downloader for Phase D087
(SPACE_UV_STIS_AND_FARRED_V3_8).

Enforces prospective methodology lock (METHOD_LOCK.json + LOCK_RECEIPT.json
strictly >= 3s prior to download), verifies free disk >= 10 GiB and projected
size <= 6.0 GiB, writes FIRST_SCIENCE_DOWNLOAD_RECEIPT.json before streaming
the first FITS binary, and populates:
  - inputs_d087_v3_8/hst_stis/x1d/{safe_dp}_x1d.fits
  - inputs_d087_v3_8/uves_red/s1d/{safe_dp}_s1d.fits
  - inputs_d087_v3_8/espresso/s1d_a/{safe_dp}_s1d_a.fits
  - inputs_d087_v3_8/espresso/s1d_b/{safe_dp}_s1d_b.fits
  - inputs_d087_v3_8/FULL_D087_INPUT_MANIFEST.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(".")
WS = ROOT / "analysis_workspace" / "work_stis_farred_20261118_d087_v3_8_space_uv_and_200star"
IN_DIR = ROOT / "inputs_d087_v3_8"

MAX_TOTAL_GIB = 6.0
MIN_POST_FREE_GIB = 10.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_dp(dp_id: str) -> str:
    return dp_id.replace(":", "_")


def _download_one(job: tuple[str, Path, int]) -> tuple[str, int, str]:
    url, dst, expected_bytes = job
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 10000:
        with dst.open("rb") as f:
            head = f.read(9)
        if head.startswith(b"SIMPLE"):
            return str(dst.relative_to(IN_DIR)), dst.stat().st_size, sha256_file(dst)

    tmp = dst.with_suffix(".fits.part")
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D087-Downloader/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with tmp.open("wb") as out:
                    shutil.copyfileobj(resp, out, length=1 << 18)
            with tmp.open("rb") as chk:
                hdr = chk.read(9)
            if not hdr.startswith(b"SIMPLE"):
                raise RuntimeError(f"Non-FITS payload downloaded from {url}: {hdr!r}")
            sz = tmp.stat().st_size
            if expected_bytes > 0 and sz < int(0.85 * expected_bytes):
                raise RuntimeError(f"Truncated FITS from {url}: got {sz} vs expected {expected_bytes}")
            tmp.replace(dst)
            return str(dst.relative_to(IN_DIR)), sz, sha256_file(dst)
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed downloading {url}: {last_err}")


def main() -> None:
    lock_p = WS / "METHOD_LOCK.json"
    rec_p = WS / "LOCK_RECEIPT.json"
    cohort_p = WS / "FROZEN_COHORT_D087.csv"
    if not (lock_p.exists() and rec_p.exists() and cohort_p.exists()):
        raise RuntimeError("Missing METHOD_LOCK.json, LOCK_RECEIPT.json, or FROZEN_COHORT_D087.csv")

    lock = json.loads(lock_p.read_text(encoding="utf-8"))
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    if lock.get("inputs_directory_existed_at_lock_time") or rec.get("inputs_directory_present_at_lock"):
        raise RuntimeError("Invalid lock: inputs directory existed at lock time!")

    for rel, exp_sha in lock["locked_file_hashes"].items():
        fp = WS / rel
        if not fp.exists() or sha256_file(fp) != exp_sha:
            raise RuntimeError(f"Method lock SHA-256 mismatch for {rel}!")

    t_lock = datetime.strptime(lock["locked_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now_dt = datetime.now(timezone.utc)
    dt_s = (now_dt - t_lock).total_seconds()
    if dt_s < 3.0:
        raise RuntimeError(f"Chronology guard failed: dt={dt_s:.2f}s < 3.0s since lock")

    with cohort_p.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    proj_bytes = sum(int(r["this_bytes"]) + int(r["aux_bytes"] or 0) for r in rows)
    proj_gib = proj_bytes / (1024.0 ** 3)
    if proj_gib > MAX_TOTAL_GIB:
        raise RuntimeError(f"Cohort projected download {proj_gib:.3f} GiB exceeds {MAX_TOTAL_GIB:.1f} GiB safety cap")

    free_bytes = shutil.disk_usage(ROOT).free
    post_free_gib = (free_bytes - proj_bytes) / (1024.0 ** 3)
    if post_free_gib < MIN_POST_FREE_GIB:
        raise RuntimeError(
            f"Insufficient free disk: free={free_bytes/(1024**3):.2f} GiB, "
            f"projected={proj_gib:.2f} GiB -> remaining {post_free_gib:.2f} < {MIN_POST_FREE_GIB:.1f} GiB"
        )

    IN_DIR.mkdir(parents=True, exist_ok=True)
    dl_receipt = {
        "schema": "SETI_D087_FIRST_DOWNLOAD_RECEIPT_V1",
        "phase_id": "D087",
        "method_lock_sha256": sha256_file(lock_p),
        "locked_utc": lock["locked_utc"],
        "first_science_download_utc": now_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_after_lock_seconds": round(dt_s, 3),
        "projected_bytes": proj_bytes,
    }
    receipt_txt = json.dumps(dl_receipt, indent=2, allow_nan=False) + "\n"
    (IN_DIR / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(receipt_txt, encoding="utf-8")
    (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(receipt_txt, encoding="utf-8")

    jobs: list[tuple[str, Path, int]] = []
    job_meta: list[dict[str, Any]] = []
    for r in rows:
        inst = r["instrument"]
        dp = r["dp_id"]
        sdp = safe_dp(dp)
        if inst == "HST_STIS":
            p_this = IN_DIR / "hst_stis" / "x1d" / f"{sdp}_x1d.fits"
            p_aux: Path | None = None
        elif inst == "UVES_RED":
            p_this = IN_DIR / "uves_red" / "s1d" / f"{sdp}_s1d.fits"
            p_aux = None
        else:
            p_this = IN_DIR / "espresso" / "s1d_a" / f"{sdp}_s1d_a.fits"
            p_aux = IN_DIR / "espresso" / "s1d_b" / f"{sdp}_s1d_b.fits"

        jobs.append((r["this_url"], p_this, int(r["this_bytes"])))
        if p_aux is not None:
            jobs.append((r["aux_url"], p_aux, int(r["aux_bytes"] or 0)))
        job_meta.append({
            "instrument": inst,
            "star": r["canonical_target"],
            "dp_id": dp,
            "this_rel": str(p_this.relative_to(IN_DIR)),
            "aux_rel": str(p_aux.relative_to(IN_DIR)) if p_aux is not None else "",
        })

    print(f"[download_inputs] Downloading {len(jobs)} FITS files across {len(rows)} exposures ({proj_gib:.3f} GiB)...", flush=True)
    with ThreadPoolExecutor(6) as ex:
        dl_results = list(ex.map(_download_one, jobs))

    by_rel = {rel: (sz, sh) for rel, sz, sh in dl_results}
    total_actual_bytes = sum(sz for _, sz, _ in dl_results)
    manifest_rows = []
    for jm in job_meta:
        t_sz, t_sha = by_rel[jm["this_rel"]]
        a_sz, a_sha = by_rel[jm["aux_rel"]] if jm["aux_rel"] else (0, "")
        manifest_rows.append({
            **jm,
            "this_bytes": t_sz,
            "this_sha256": t_sha,
            "aux_bytes": a_sz,
            "aux_sha256": a_sha,
        })

    manifest = {
        "schema": "FULL_D087_INPUT_MANIFEST_V1",
        "phase_id": "D087",
        "downloaded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_exposures": len(manifest_rows),
        "n_files": len(dl_results),
        "total_bytes": total_actual_bytes,
        "total_gib": round(total_actual_bytes / (1024.0 ** 3), 4),
        "files": manifest_rows,
    }
    (IN_DIR / "FULL_D087_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[download_inputs] Completed {len(dl_results)} FITS files ({manifest['total_gib']:.3f} GiB).", flush=True)


if __name__ == "__main__":
    main()
