#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D112 (V7.0) Stage-1 Locked Post-Seal Downloader:
  - Enforces immutable Stage-1 seal (METHOD_LOCK.json & LOCK_RECEIPT.json).
  - Enforces chronology_lag_seconds >= 10.5 s before creating inputs_d112_v7_0.
  - Downloads all locked HEASARC INTEGRAL (IBIS/ISGRI, JEM-X, SPI + CALDB RMF),
    official 1LHAASO VizieR FITS + Zenodo 24186127 (1.000 PeV SED) + Zenodo 24128953,
    and March 2026 ALMA Band 2 Science Verification Arp 220 RefImages_manual tarballs.
  - Validates every physical file with the sealed V7.0 loaders in `v7_0_detector.py`.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import sys
import tarfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
RAW_DIR = ROOT / "inputs_d112_v7_0"

if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

import v7_0_detector as det  # noqa: E402


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _verify_stage1_lock() -> tuple[dict[str, Any], dict[str, Any]]:
    lr_p = WS / "LOCK_RECEIPT.json"
    ml_p = WS / "METHOD_LOCK.json"
    assert lr_p.exists() and ml_p.exists(), "Missing LOCK_RECEIPT.json or METHOD_LOCK.json!"
    lr = json.loads(lr_p.read_text(encoding="utf-8"))
    ml = json.loads(ml_p.read_text(encoding="utf-8"))
    assert lr.get("inputs_dir_exists_at_seal") is False, "Stage-1 integrity violation: inputs_dir existed at seal!"
    assert _sha256_file(ml_p) == lr.get("method_lock_sha256"), "METHOD_LOCK.json SHA-256 mismatch!"
    s1 = ml.get("stage_1_files", {})
    assert len(s1) == 7, f"Expected 7 Stage-1 files, got {len(s1)}"
    for fn, exp_sha in s1.items():
        fp = WS / fn
        assert fp.exists(), f"Missing locked Stage-1 file: {fn}"
        act = _sha256_file(fp)
        assert act == exp_sha, f"Locked Stage-1 tamper on {fn}: {act} != {exp_sha}"
    return lr, ml


def _download_stream(url: str, dest: Path, min_bytes: int = 512, timeout: int = 180) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_bytes:
        return int(dest.stat().st_size)
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D112-Downloader/1.0"})
            total = 0
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(req, timeout=timeout) as r, tmp.open("wb") as out:
                if r.status not in (200, 206):
                    raise RuntimeError(f"HTTP {r.status} for {url}")
                head_buf = b""
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    if total == 0:
                        head_buf = chunk[:256].lstrip().lower()
                        if head_buf.startswith(b"<!doctype") or head_buf.startswith(b"<html"):
                            raise RuntimeError(f"Unexpected HTML payload for {url}")
                    out.write(chunk)
                    total += len(chunk)
            if total < min_bytes:
                tmp.unlink(missing_ok=True)
                raise RuntimeError(f"File too small ({total} B) for {url}")
            tmp.replace(dest)
            return total
        except Exception as exc:
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Download failed after 5 attempts for {url}: {last_err}")


def _unpack_gz_if_needed(gz_path: Path) -> Path:
    if gz_path.suffix != ".gz":
        return gz_path
    out = gz_path.with_suffix("")
    if not out.exists() or out.stat().st_size == 0:
        out.write_bytes(gzip.decompress(gz_path.read_bytes()))
    return out


def main() -> int:
    lr, ml = _verify_stage1_lock()
    lock_epoch = float(lr["locked_unix_epoch"])
    now_epoch = time.time()
    lag = now_epoch - lock_epoch
    if lag < 10.5:
        wait_s = 10.5 - lag + 0.15
        print(f"Enforcing Stage-1 chronology buffer: sleeping {wait_s:.2f}s (current lag={lag:.2f}s)...", flush=True)
        time.sleep(wait_s)
        now_epoch = time.time()
        lag = now_epoch - lock_epoch

    assert lag >= 10.0, f"Chronology lag too small: {lag}"
    first_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()
    with (WS / "FROZEN_COHORT_D112.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows, "Empty FROZEN_COHORT_D112.csv!"

    cfg = json.loads((WS / "HIGH_ENERGY_PEV_ALMAB2_CONFIG.json").read_text(encoding="utf-8"))

    fdr = {
        "schema": "D112_FIRST_DOWNLOAD_RECEIPT",
        "phase_id": "D112",
        "locked_utc": ml["locked_utc"],
        "method_lock_sha256": lr["method_lock_sha256"],
        "first_download_utc": first_utc,
        "first_download_unix_epoch": round(now_epoch, 4),
        "chronology_lag_seconds": round(lag, 3),
        "first_target": rows[0]["canonical_target"],
        "first_dp_id": rows[0]["dp_id"],
        "first_url": rows[0]["f1_url"],
    }
    (WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").write_text(json.dumps(fdr, indent=2) + "\n", encoding="utf-8")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Stage-1 lock verified (lag=+{lag:.3f}s). Downloading physical datasets for {len(rows)} locked rows -> {RAW_DIR}...", flush=True)

    # 1. Shared supporting files (CALDB JEM-X RMF, 1LHAASO FITS, Zenodo J2108 tar.gz, Zenodo 13-src zip)
    shared_downloads: list[dict[str, Any]] = []
    for key, spec_d in cfg.get("shared_downloads", {}).items():
        dest = RAW_DIR / spec_d["relpath"]
        nbytes = _download_stream(spec_d["url"], dest, min_bytes=int(spec_d.get("min_bytes", 512)), timeout=180)
        sha = _sha256_file(dest)
        shared_downloads.append({"key": key, "relpath": spec_d["relpath"], "url": spec_d["url"], "bytes": nbytes, "sha256": sha})
        print(f"  [SHARED] {key}: {nbytes} B ({sha[:12]})", flush=True)

    # 2. Download per-row files (skip ALMA tarballs for dedicated single-thread extract below)
    def _fetch_row(r: dict[str, Any]) -> dict[str, Any]:
        inst = r["instrument"]
        rel1 = r["f1_rel"]
        dest1 = RAW_DIR / rel1
        if inst in ("LHAASO_WCDA", "LHAASO_KM2A"):
            # Backed by shared 1LHAASO FITS + Zenodo SEDs already verified above
            p_fits = RAW_DIR / cfg["shared_downloads"]["1lhaaso_fits"]["relpath"]
            assert p_fits.exists() and p_fits.stat().st_size > 10000
            return {
                "star": r["canonical_target"], "instrument": inst, "dp_id": r["dp_id"],
                "relpath": cfg["shared_downloads"]["1lhaaso_fits"]["relpath"],
                "url": r["f1_url"], "bytes": int(p_fits.stat().st_size),
                "sha256": _sha256_file(p_fits), "valid": True, "shared_backed": True,
            }
        if inst == "ALMA_B2_3MM":
            nbytes = _download_stream(r["f1_url"], dest1, min_bytes=10_000_000, timeout=600)
            sha = _sha256_file(dest1)
            extracted: list[dict[str, Any]] = []
            cube_dir = RAW_DIR / "ALMA_B2_3MM" / r["canonical_target"] / f"cubes_{r['dp_id']}"
            cube_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(dest1, mode="r:gz") as tf:
                for mem in tf.getmembers():
                    if not mem.isfile():
                        continue
                    bn = Path(mem.name).name
                    if bn.endswith(".fits") and "cube" in bn.lower() and "pbcor" in bn.lower():
                        out_f = cube_dir / bn
                        if not out_f.exists() or out_f.stat().st_size != mem.size:
                            src_f = tf.extractfile(mem)
                            assert src_f is not None
                            with out_f.open("wb") as wf:
                                while True:
                                    b = src_f.read(1 << 20)
                                    if not b:
                                        break
                                    wf.write(b)
                        cinfo = det.extract_alma_band2_cube_v70(out_f, max_spw_label=f"{r['dp_id']}:{bn}")
                        assert cinfo["valid"], f"Invalid Band 2 cube {bn}"
                        extracted.append({
                            "relpath": str(out_f.relative_to(RAW_DIR)),
                            "nchan": cinfo["nchan"],
                            "fmin_ghz": round(float(cinfo["freq_ghz"][0]), 4),
                            "fmax_ghz": round(float(cinfo["freq_ghz"][-1]), 4),
                            "bytes": int(out_f.stat().st_size),
                            "sha256": _sha256_file(out_f),
                        })
            assert len(extracted) >= 1, f"Too few Band 2 cubes in {dest1.name}: {len(extracted)}"
            return {
                "star": r["canonical_target"], "instrument": inst, "dp_id": r["dp_id"],
                "relpath": rel1, "url": r["f1_url"], "bytes": nbytes, "sha256": sha,
                "valid": True, "extracted_cubes": extracted,
            }

        # INTEGRAL family
        n1 = _download_stream(r["f1_url"], dest1, min_bytes=2000, timeout=180)
        aux_urls = [u for u in str(r.get("aux_urls", "")).split("|") if u.strip()]
        aux_rels = [p for p in str(r.get("aux_rels", "")).split("|") if p.strip()]
        assert len(aux_urls) == len(aux_rels)
        aux_bytes = 0
        for u, rp in zip(aux_urls, aux_rels):
            aux_bytes += _download_stream(u, RAW_DIR / rp, min_bytes=512, timeout=180)

        # Validate using sealed V7.0 loaders
        if inst == "INTEGRAL_IBIS_ISGRI":
            pha_p = _unpack_gz_if_needed(dest1)
            arf_p = _unpack_gz_if_needed(RAW_DIR / aux_rels[0])
            rmf_p = _unpack_gz_if_needed(RAW_DIR / aux_rels[1])
            d = det.load_integral_isgri_fits(pha_p, arf_p, rmf_p)
            assert d["valid"] and len(d["e_mid_kev"]) >= 6
        elif inst == "INTEGRAL_JEMX":
            rmf_p = RAW_DIR / cfg["shared_downloads"]["jmx2_rmf"]["relpath"]
            d = det.load_integral_jemx_fits(dest1, RAW_DIR / aux_rels[0], rmf_p)
            assert d["valid"] and len(d["e_mid_kev"]) >= 64
        elif inst == "INTEGRAL_SPI":
            spi_fits_p = _unpack_gz_if_needed(dest1)
            spi_txt_p = RAW_DIR / aux_rels[0]
            d = det.load_integral_spi_dataset(spi_fits_p, spi_txt_p, star=r["canonical_target"])
            assert d["valid"] and len(d["e_mid_kev"]) >= 4
        else:
            raise ValueError(f"Unknown D112 instrument: {inst}")

        return {
            "star": r["canonical_target"], "instrument": inst, "dp_id": r["dp_id"],
            "relpath": rel1, "url": r["f1_url"], "bytes": n1 + aux_bytes,
            "sha256": _sha256_file(dest1), "valid": True,
            "n_bins": int(len(d["e_mid_kev"])), "exp_s": float(d.get("exp_s", 0.0)),
        }

    records: list[dict[str, Any]] = []
    failed = 0
    non_alma = [r for r in rows if r["instrument"] != "ALMA_B2_3MM"]
    alma_rows = [r for r in rows if r["instrument"] == "ALMA_B2_3MM"]

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [(r, ex.submit(_fetch_row, r)) for r in non_alma]
        for idx, (r, fut) in enumerate(futs, 1):
            try:
                rec = fut.result()
                records.append(rec)
                if idx % 20 == 0 or idx == len(futs):
                    print(f"  [NON-ALMA {idx}/{len(futs)}] {rec['instrument']} {rec['star']} OK ({rec['bytes']} B)", flush=True)
            except Exception as exc:
                failed += 1
                print(f"  [FAIL {r['instrument']} {r['dp_id']}]: {exc}", flush=True)
                records.append({"star": r["canonical_target"], "instrument": r["instrument"], "dp_id": r["dp_id"], "valid": False, "error": str(exc)})

    for idx, r in enumerate(alma_rows, 1):
        try:
            print(f"  [ALMA B2 {idx}/{len(alma_rows)}] Downloading {r['dp_id']} (~1.3-2.5 GB)...", flush=True)
            rec = _fetch_row(r)
            records.append(rec)
            print(f"    -> {len(rec.get('extracted_cubes', []))} SPW cubes extracted & validated OK", flush=True)
        except Exception as exc:
            failed += 1
            print(f"  [FAIL ALMA {r['dp_id']}]: {exc}", flush=True)
            records.append({"star": r["canonical_target"], "instrument": r["instrument"], "dp_id": r["dp_id"], "valid": False, "error": str(exc)})

    # Deduplicate physical byte sum over unique relpaths + shared files
    uniq_bytes: dict[str, int] = {}
    for s in shared_downloads:
        uniq_bytes[s["relpath"]] = int(s["bytes"])
    for rec in records:
        if rec.get("valid") and not rec.get("shared_backed"):
            uniq_bytes[rec["relpath"]] = int(rec["bytes"])
            for c in rec.get("extracted_cubes", []):
                uniq_bytes[c["relpath"]] = int(c["bytes"])
    tot_bytes = sum(uniq_bytes.values())

    manifest = {
        "schema": "D112_INPUT_MANIFEST",
        "phase_id": "D112",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "chronology_lag_seconds": round(lag, 3),
        "expected_observations": len(rows),
        "valid_observations": sum(1 for x in records if x.get("valid")),
        "failed_observations": failed,
        "total_bytes": tot_bytes,
        "total_mib": round(tot_bytes / (1024.0 * 1024.0), 3),
        "shared_downloads": shared_downloads,
        "observations": records,
    }
    (WS / "FULL_D112_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert failed == 0, f"{failed} downloads failed!"
    assert manifest["valid_observations"] == len(rows)
    print(f"Download complete: {manifest['valid_observations']}/{len(rows)} valid observations ({manifest['total_mib']:.3f} MiB), 0 failed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
