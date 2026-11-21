#!/usr/bin/env python3
r"""
Phase D095 Stage-2 Download Completion & Manifest Writer.

Leaves all 7 Stage-1 files hashed in `METHOD_LOCK.json` (including `download_inputs.py`)
100% unmodified, verifies `FIRST_SCIENCE_DOWNLOAD_RECEIPT.json` chronology lag >= 3.0s,
validates the 38 already-downloaded files in `<ROOT>/inputs_d095_v5_3/`, completes the
remaining 16 Spitzer IRS Enhanced `.tbl` downloads (checking the full 4096-byte IPAC header
+ `|order|wavelength|` table signature where `\TELESCOP = 'Spitzer'` can fall past byte 512),
and seals `FULL_D095_INPUT_MANIFEST.json`.
r"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import time
import urllib.request
from typing import Any

WS = pathlib.Path(__file__).resolve().parent
ROOT = WS.parent.parent
INP_DIR = ROOT / "inputs_d095_v5_3"


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _is_valid_payload_stage2(path: pathlib.Path, inst: str) -> bool:
    if not path.exists():
        return False
    sz = path.stat().st_size
    if inst == "SPITZER_IRS":
        if sz < 2048:
            return False
        txt = path.read_text(encoding="utf-8", errors="replace")
        head = txt[:4096]
        return ("\\" in head or "|" in head) and ("SPITZER" in head.upper()) and ("|order|wavelength|" in txt)
    if sz < 16384:
        return False
    with path.open("rb") as chk:
        return chk.read(9) == b"SIMPLE  ="


def _download_with_retry(url: str, dst: pathlib.Path, inst: str, timeout_s: float = 90.0) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    last_err: Exception | None = None
    for att in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-D095/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_s) as resp, tmp.open("wb") as out:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            if not _is_valid_payload_stage2(tmp, inst):
                hdr = tmp.read_bytes()[:64]
                raise RuntimeError(f"Invalid payload ({inst}) header {hdr!r} from {url}")
            tmp.replace(dst)
            return
        except Exception as exc:
            last_err = exc
            if tmp.exists():
                tmp.unlink()
            time.sleep(2.0 * (att + 1))
    raise RuntimeError(f"Failed download {url}: {last_err}")


def main() -> None:
    lock_path = WS / "METHOD_LOCK.json"
    rec_path = WS / "LOCK_RECEIPT.json"
    dl_rec_path = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    coh_path = WS / "FROZEN_COHORT_D095.csv"
    if not (lock_path.exists() and rec_path.exists() and dl_rec_path.exists() and coh_path.exists()):
        raise RuntimeError("Missing Stage-1 lock/receipt/cohort files.")

    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for fname, exp_sha in lock["locked_file_hashes"].items():
        got = sha256_file(WS / fname)
        if got != exp_sha:
            raise RuntimeError(f"Stage-1 immutability violation in {fname}: {got} != {exp_sha}")

    dl_rec = json.loads(dl_rec_path.read_text(encoding="utf-8"))
    min_lag = float(lock["hard_caps"]["min_chronology_lag_seconds"])
    if float(dl_rec["chronology_lag_seconds"]) < min_lag:
        raise RuntimeError(f"Chronology lag {dl_rec['chronology_lag_seconds']}s < {min_lag}s")

    rows = list(csv.DictReader(coh_path.open("r", encoding="utf-8")))
    seen_rel: set[str] = set()
    manifest_rows: list[dict[str, Any]] = []
    tot_dl_bytes = 0
    n_existing = 0
    n_newly_fetched = 0

    for idx, r in enumerate(rows, 1):
        rel = r["f1_rel"]
        url = r["f1_url"]
        inst = r["instrument"]
        dst = INP_DIR / rel
        if rel not in seen_rel:
            seen_rel.add(rel)
            if _is_valid_payload_stage2(dst, inst):
                n_existing += 1
            else:
                _download_with_retry(url, dst, inst)
                n_newly_fetched += 1
            sz = dst.stat().st_size
            sha = sha256_file(dst)
            tot_dl_bytes += sz
            print(f"[{idx:02d}/{len(rows)}] {rel} ({sz / 1048576:.3f} MiB)", flush=True)
        else:
            sz = dst.stat().st_size
            sha = sha256_file(dst)

        manifest_rows.append({
            "instrument": inst,
            "canonical_target": r["canonical_target"],
            "dp_id": r["dp_id"],
            "f1_rel": rel,
            "f1_url": url,
            "bytes": sz,
            "sha256": sha,
            "mjd_obs": float(r["mjd_obs"]),
            "t_exptime": float(r["t_exptime"]),
        })

    tot_mib = tot_dl_bytes / 1048576.0
    if tot_mib > float(lock["hard_caps"]["max_download_mib"]):
        raise RuntimeError(f"Actual download {tot_mib:.3f} MiB exceeds {lock['hard_caps']['max_download_mib']} MiB")
    post_free_gib = shutil.disk_usage(ROOT).free / (1024 ** 3)
    if post_free_gib < float(lock["hard_caps"]["min_free_disk_gib"]):
        raise RuntimeError(f"Free disk below {lock['hard_caps']['min_free_disk_gib']} GiB: {post_free_gib:.3f}")

    manifest = {
        "schema": "FULL_D095_INPUT_MANIFEST",
        "phase_id": "D095",
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_files": len(seen_rel),
        "total_bytes": tot_dl_bytes,
        "total_mib": round(tot_mib, 3),
        "post_download_free_gib": round(post_free_gib, 3),
        "method_lock_sha256": sha256_file(lock_path),
        "note": "Completed Spitzer IRS .tbl downloads using 4096-byte IPAC header check while keeping Stage-1 download_inputs.py SHA-256 untouched.",
        "files": manifest_rows,
    }
    (WS / "FULL_D095_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"DONE: verified {len(seen_rel)} files ({n_existing} existing, {n_newly_fetched} fetched; "
        f"{tot_mib:.2f} MiB <= 125.0 MiB), free disk {post_free_gib:.2f} GiB.",
        flush=True,
    )


if __name__ == "__main__":
    main()
