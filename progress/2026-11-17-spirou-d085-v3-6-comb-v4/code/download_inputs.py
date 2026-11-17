#!/usr/bin/env python3
"""Post-lock parallel archival science FITS downloader for Phase D085 (SPIROU_V3_6_AND_COMB_V4).

Verifies METHOD_LOCK.json & LOCK_RECEIPT.json first, stamps FIRST_SCIENCE_DOWNLOAD_RECEIPT.json
strictly after lock_utc, and downloads 177 public CFHT SPIRou APERO `*t.fits` exposures
into ../../inputs_d085_v3_6/spirou/ with SHA-256 verification and FITS integrity checks.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Any
import urllib.request

from astropy.io import fits

WS = Path(__file__).resolve().parent
INPUTS_DIR = WS.parent.parent / "inputs_d085_v3_6"
SPIROU_DIR = INPUTS_DIR / "spirou"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    lrcpt = json.loads((WS / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    mlock = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    if sha256_file(WS / "METHOD_LOCK.json") != lrcpt["method_lock_sha256"]:
        raise RuntimeError("METHOD_LOCK hash mismatch")
    for fn, exp_sha in mlock["locked_file_hashes"].items():
        if sha256_file(WS / fn) != exp_sha:
            raise RuntimeError(f"Pre-download lock violation on {fn}")

    t_lock = dt.datetime.fromisoformat(lrcpt["lock_utc"].replace("Z", "+00:00"))
    while dt.datetime.now(dt.timezone.utc) <= t_lock + dt.timedelta(seconds=2):
        time.sleep(1.0)

    cohort_rows = list(csv.DictReader((WS / "FROZEN_COHORT_D085.csv").open("r", encoding="utf-8")))
    if len(cohort_rows) != 177:
        raise RuntimeError(f"Expected 177 cohort rows, got {len(cohort_rows)}")

    SPIROU_DIR.mkdir(parents=True, exist_ok=True)
    rcpt_path = WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    receipt_lock = threading.Lock()
    progress_lock = threading.Lock()
    done_cnt = [0]

    def stamp_first_receipt(first_dp: str, first_url: str) -> None:
        with receipt_lock:
            if rcpt_path.is_file():
                return
            now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            rcpt = {
                "schema": "D085_FIRST_SCIENCE_DOWNLOAD_RECEIPT",
                "phase_id": "D085",
                "lock_utc": lrcpt["lock_utc"],
                "first_download_utc": now_utc,
                "first_dp_id": first_dp,
                "first_access_url": first_url,
            }
            rcpt_path.write_text(json.dumps(rcpt, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    def download_one(row: dict[str, str]) -> dict[str, Any]:
        dp = row["dp_id"].strip()
        st = row["canonical_target"].strip()
        url = row["access_url"].strip()
        rel = f"spirou/{dp}.fits"
        dest = INPUTS_DIR / rel
        part = INPUTS_DIR / f"spirou/.{dp}.fits.part"

        stamp_first_receipt(dp, url)

        if not dest.is_file() or dest.stat().st_size < 1_000_000:
            last_err: Exception | None = None
            for attempt in range(4):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "ANDERSEN-SETI-D085/1.0"})
                    with urllib.request.urlopen(req, timeout=90.0) as resp:
                        with part.open("wb") as out_f:
                            while True:
                                buf = resp.read(1024 * 1024)
                                if not buf:
                                    break
                                out_f.write(buf)
                    part.replace(dest)
                    break
                except Exception as exc:
                    last_err = exc
                    part.unlink(missing_ok=True)
                    time.sleep(1.5 * (attempt + 1))
            else:
                raise RuntimeError(f"Failed downloading {dp} ({url}): {last_err}")

        # Verify APERO `*t.fits` integrity before completing
        with fits.open(dest, memmap=False) as hdul:
            if hdul["FluxAB"].data.shape != (49, 4088):
                raise RuntimeError(f"Bad FluxAB shape on {dp}: {hdul['FluxAB'].data.shape}")
        f_sha = sha256_file(dest)
        f_sz = dest.stat().st_size
        with progress_lock:
            done_cnt[0] += 1
            if done_cnt[0] % 20 == 0 or done_cnt[0] == len(cohort_rows):
                print(f"  [download] {done_cnt[0]}/{len(cohort_rows)} SPIRou *t.fits verified ({dp})", flush=True)
        return {
            "dp_id": dp,
            "star": st,
            "access_url": url,
            "fits_relpath": rel,
            "fits_bytes": f_sz,
            "fits_sha256": f_sha,
        }

    print(f"[download_inputs] Downloading & verifying 177 CFHT SPIRou APERO `*t.fits` into {SPIROU_DIR}...", flush=True)
    with ThreadPoolExecutor(8) as ex:
        exp_items = list(ex.map(download_one, cohort_rows))

    man = {
        "schema": "D085_FULL_SPIROU_INPUT_MANIFEST_V1",
        "phase_id": "D085",
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "total_exposures": len(exp_items),
        "total_bytes": sum(x["fits_bytes"] for x in exp_items),
        "exposures": exp_items,
    }
    (INPUTS_DIR / "FULL_SPIROU_INPUT_MANIFEST.json").write_text(json.dumps(man, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[download_inputs] DONE: {len(exp_items)} files, {man['total_bytes']/(1024**3):.3f} GiB verified.", flush=True)


if __name__ == "__main__":
    main()
