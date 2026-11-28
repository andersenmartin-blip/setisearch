#!/usr/bin/env python3
"""Stage 1 for Spor N12: Acquire and verify 20 BERV-diverse HARPS Phase-3 1D spectra x 24 <9.5 pc G/K/M hosts (480 total)."""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from astropy.io import fits
import numpy as np

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
INP = ROOT / "inputs_n12_20261128"
FITS_DIR = INP / "fits"

TAP_URL = "https://archive.eso.org/tap_obs/sync"
DL_BASE = "https://dataportal.eso.org/dataportal_new/file/"

TARGETS = [
    {"star": "EPSERI", "common_name": "eps Eri", "ra_deg": 53.2249, "dec_deg": -9.4559, "dist_pc": 3.2026, "n_pl": 1, "vmag": 3.72, "sp_type": "K2V", "rv": 16.0, "alias_ok": ("EPSERI", "EPSE", "HD22049", "HR1084", "HIP16537", "GJ144"), "bad": ()},
    {"star": "HD217987", "common_name": "Lacaille 9352", "ra_deg": 346.5102, "dec_deg": -35.8457, "dist_pc": 3.2868, "n_pl": 4, "vmag": 7.56, "sp_type": "M1V", "rv": 8.2, "alias_ok": ("217987", "GJ887", "GL887", "LAC9352", "HIP114046"), "bad": ()},
    {"star": "TAUCET", "common_name": "tau Cet", "ra_deg": 26.0061, "dec_deg": -15.9306, "dist_pc": 3.6030, "n_pl": 3, "vmag": 3.50, "sp_type": "G8.5V", "rv": -17.1, "alias_ok": ("TAUCET", "HD10700", "HR509", "HIP8102", "GJ71"), "bad": ()},
    {"star": "HD209100", "common_name": "eps Ind A", "ra_deg": 330.8512, "dec_deg": -56.7881, "dist_pc": 3.6386, "n_pl": 1, "vmag": 4.69, "sp_type": "K5V", "rv": -40.7, "alias_ok": ("209100", "EPSIND", "HR8387", "HIP108870", "GJ845"), "bad": ("INDB", "INDC")},
    {"star": "GJ191", "common_name": "Kapteyn's Star", "ra_deg": 77.9674, "dec_deg": -45.0478, "dist_pc": 3.9331, "n_pl": 1, "vmag": 8.86, "sp_type": "M2.0V", "rv": 245.0, "alias_ok": ("191", "KAPTEYN", "HD33793", "HIP24186"), "bad": ()},
    {"star": "WOLF1061", "common_name": "Wolf 1061", "ra_deg": 247.5749, "dec_deg": -12.6687, "dist_pc": 4.3059, "n_pl": 3, "vmag": 10.10, "sp_type": "M3.5V", "rv": -21.0, "alias_ok": ("WOLF1061", "GJ628", "GL628", "HIP80824", "BD-124523"), "bad": ()},
    {"star": "GJ9066", "common_name": "GJ 9066", "ra_deg": 30.0579, "dec_deg": 13.0396, "dist_pc": 4.4710, "n_pl": 1, "vmag": 12.71, "sp_type": "M5.0V", "rv": -28.8, "alias_ok": ("9066", "GL83.1", "GJ83.1", "G003-033", "LHS11", "TZARI"), "bad": ()},
    {"star": "GJ674", "common_name": "GJ 674", "ra_deg": 262.1603, "dec_deg": -46.8984, "dist_pc": 4.5490, "n_pl": 1, "vmag": 9.38, "sp_type": "M2.5V", "rv": -2.9, "alias_ok": ("674", "HIP85523", "CD-4611540", "LHS449"), "bad": ()},
    {"star": "GJ876", "common_name": "GJ 876", "ra_deg": 343.3241, "dec_deg": -14.2667, "dist_pc": 4.6752, "n_pl": 4, "vmag": 10.16, "sp_type": "M2.5V", "rv": -1.6, "alias_ok": ("876", "ILAQR", "HIP113020", "BD-156290"), "bad": ()},
    {"star": "GJ832", "common_name": "GJ 832", "ra_deg": 323.3844, "dec_deg": -49.0143, "dist_pc": 4.9644, "n_pl": 1, "vmag": 8.66, "sp_type": "M2V", "rv": 12.5, "alias_ok": ("832", "HD204961", "HIP106440", "LHS3685"), "bad": ()},
    {"star": "GJ682", "common_name": "GJ 682", "ra_deg": 264.2565, "dec_deg": -44.3288, "dist_pc": 5.0067, "n_pl": 2, "vmag": 10.94, "sp_type": "M3.5V", "rv": -60.0, "alias_ok": ("682", "HIP86214", "CD-4411909", "LHS451"), "bad": ()},
    {"star": "GJ3323", "common_name": "GJ 3323", "ra_deg": 75.4850, "dec_deg": -6.9487, "dist_pc": 5.3748, "n_pl": 2, "vmag": 12.57, "sp_type": "M4V", "rv": 42.5, "alias_ok": ("3323", "LHS1723", "LP656-38"), "bad": ()},
    {"star": "HD42581", "common_name": "GJ 229 A", "ra_deg": 92.6450, "dec_deg": -21.8664, "dist_pc": 5.7562, "n_pl": 2, "vmag": 8.15, "sp_type": "M1.5V", "rv": 4.0, "alias_ok": ("42581", "GJ229", "GL229", "HIP29295"), "bad": ("229B",)},
    {"star": "GJ752A", "common_name": "Wolf 1055", "ra_deg": 289.2277, "dec_deg": 5.1653, "dist_pc": 5.9106, "n_pl": 1, "vmag": 9.12, "sp_type": "M2.5V", "rv": 35.7, "alias_ok": ("752", "180617", "HIP94761", "WOLF1055"), "bad": ("752B", "VB10")},
    {"star": "HD20794", "common_name": "82 G. Eridani", "ra_deg": 50.0053, "dec_deg": -43.0656, "dist_pc": 6.0028, "n_pl": 4, "vmag": 4.26, "sp_type": "G8V", "rv": 87.9, "alias_ok": ("20794", "82ERI", "82GERI", "HR1008", "HIP15510", "GJ139"), "bad": ()},
    {"star": "GJ581", "common_name": "GJ 581", "ra_deg": 229.8541, "dec_deg": -7.7269, "dist_pc": 6.2981, "n_pl": 3, "vmag": 10.57, "sp_type": "M3.0V", "rv": 9.8, "alias_ok": ("581", "HIP74995", "HO LIB", "HOLIB", "BD-074003"), "bad": ()},
    {"star": "LTT1445A", "common_name": "LTT 1445 A", "ra_deg": 45.4609, "dec_deg": -16.5955, "dist_pc": 6.8693, "n_pl": 2, "vmag": 10.59, "sp_type": "M3.0V", "rv": -5.4, "alias_ok": ("1445", "TOI455", "GJ3192", "LP771-95"), "bad": ("1445B", "1445C", "1445BC")},
    {"star": "GJ393", "common_name": "GJ 393", "ra_deg": 157.2288, "dec_deg": 0.8377, "dist_pc": 7.0315, "n_pl": 1, "vmag": 9.65, "sp_type": "M2.0V", "rv": 8.3, "alias_ok": ("393", "HIP51317", "BD+012447", "LHS2272"), "bad": ()},
    {"star": "GJ514", "common_name": "GJ 514", "ra_deg": 202.5061, "dec_deg": 10.3681, "dist_pc": 7.6178, "n_pl": 1, "vmag": 9.05, "sp_type": "M1.0V", "rv": 14.6, "alias_ok": ("514", "HIP65859", "BD+112576", "LHS352"), "bad": ()},
    {"star": "HD115617", "common_name": "61 Virginis", "ra_deg": 199.6013, "dec_deg": -18.3112, "dist_pc": 8.5033, "n_pl": 3, "vmag": 4.70, "sp_type": "G5V", "rv": -8.2, "alias_ok": ("115617", "61VIR", "HR5019", "HIP64924", "GJ506"), "bad": ()},
    {"star": "GJ849", "common_name": "GJ 849", "ra_deg": 332.4247, "dec_deg": -4.6407, "dist_pc": 8.8006, "n_pl": 2, "vmag": 10.41, "sp_type": "M3.5V", "rv": -15.3, "alias_ok": ("849", "HIP109388", "BD-055715", "LHS517"), "bad": ()},
    {"star": "HD192310", "common_name": "82 G. Ceti / HD 192310", "ra_deg": 303.8257, "dec_deg": -27.0333, "dist_pc": 8.7969, "n_pl": 2, "vmag": 5.73, "sp_type": "K3V", "rv": -54.2, "alias_ok": ("192310", "HR7722", "HIP99825", "GJ785"), "bad": ()},
    {"star": "GJ433", "common_name": "GJ 433", "ra_deg": 173.8619, "dec_deg": -32.5437, "dist_pc": 9.0646, "n_pl": 3, "vmag": 9.81, "sp_type": "M2V", "rv": 17.5, "alias_ok": ("433", "HIP56528", "CD-319113", "LHS2429"), "bad": ()},
    {"star": "GJ367", "common_name": "GJ 367", "ra_deg": 146.1203, "dec_deg": -45.7801, "dist_pc": 9.4126, "n_pl": 3, "vmag": 10.15, "sp_type": "M1.0V", "rv": 47.9, "alias_ok": ("367", "TOI731", "HIP47780", "CD-455378"), "bad": ()},
]


def query_eso_tap(ra_deg: float, dec_deg: float, radius_deg: float = 0.08) -> list[dict[str, str]]:
    """Query ESO ObsCore TAP cleanly without ORDER BY."""
    sql = (
        "SELECT TOP 2000 dp_id, target_name, t_min, t_exptime, s_ra, s_dec, snr "
        "FROM ivoa.ObsCore "
        "WHERE instrument_name = 'HARPS' AND dataproduct_type = 'spectrum' "
        f"AND 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra_deg:.6f}, {dec_deg:.6f}, {radius_deg:.4f}))"
    )
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": sql})
    url = f"{TAP_URL}?{params}"
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N12/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            return list(csv.DictReader(text.splitlines()))
        except Exception as exc:
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"TAP query failed after retries: {last_err}")


def norm_name(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum() or ch in "+-.")


def select_stratified_candidates(
    target: dict[str, object], raw_rows: list[dict[str, str]], n_strata: int = 20
) -> list[list[dict[str, object]]]:
    seen: set[str] = set()
    clean: list[dict[str, object]] = []
    aliases = tuple(norm_name(a) for a in target["alias_ok"])  # type: ignore[index]
    bads = tuple(norm_name(b) for b in target["bad"])  # type: ignore[index]

    for r in raw_rows:
        dp_id = (r.get("dp_id") or "").strip()
        if not dp_id.startswith("ADP.") or dp_id in seen:
            continue
        tname = norm_name(r.get("target_name") or "")
        if any(b in tname for b in bads):
            continue
        try:
            mjd = float(r["t_min"])
            expt = float(r.get("t_exptime") or 0.0)
            snr = float(r.get("snr") or 0.0)
        except (ValueError, TypeError):
            continue
        if expt < 10.0:
            continue
        name_match = any(al in tname for al in aliases) if tname else True
        seen.add(dp_id)
        clean.append({
            "dp_id": dp_id,
            "target_name": r.get("target_name") or "",
            "t_min": mjd,
            "exptime": expt,
            "snr": snr,
            "name_match": name_match,
        })

    preferred = [c for c in clean if c["name_match"] and float(c["snr"]) >= 8.0]
    if len(preferred) < n_strata + 5:
        preferred = [c for c in clean if c["name_match"]]
    if len(preferred) < n_strata:
        preferred = clean

    preferred.sort(key=lambda c: float(c["t_min"]))
    if len(preferred) < n_strata:
        raise RuntimeError(f"{target['star']}: only {len(preferred)} HARPS candidates found (< {n_strata})")

    strata: list[list[dict[str, object]]] = []
    tot = len(preferred)
    for k in range(n_strata):
        i0 = (k * tot) // n_strata
        i1 = ((k + 1) * tot) // n_strata
        bucket = sorted(preferred[i0:i1], key=lambda c: (float(c["snr"]), float(c["exptime"])), reverse=True)
        strata.append(bucket)
    return strata


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_harps_fits(path: Path) -> dict[str, object]:
    with fits.open(path, memmap=False) as hdul:
        hdr = hdul[0].header
        tab = hdul[1].data
        cols = set(tab.names or [])
        if not {"WAVE", "FLUX", "ERR"}.issubset(cols):
            raise ValueError(f"Missing columns in {path.name}: {cols}")
        wave = np.asarray(tab["WAVE"], dtype=np.float64).ravel()
        flux = np.asarray(tab["FLUX"], dtype=np.float64).ravel()
        if wave.size < 250000:
            raise ValueError(f"Short spectrum {wave.size} in {path.name}")
        mask = (wave >= 4800.0) & (wave <= 6900.0) & np.isfinite(flux) & (flux > 0)
        if int(np.sum(mask)) < 180000:
            raise ValueError(f"Insufficient valid 4800-6900 A pixels in {path.name}")
        med_flux = float(np.median(flux[mask]))
        berv = hdr.get("HIERARCH ESO DRS BERV", hdr.get("HIERARCH ESO QC BERV", np.nan))
        sn50 = hdr.get("HIERARCH ESO DRS SPE EXT SN50", hdr.get("SNR", np.nan))
        return {
            "mjd_obs": float(hdr.get("MJD-OBS", 0.0)),
            "exptime_s": float(hdr.get("EXPTIME", 0.0)),
            "snr_hdr": float(sn50) if sn50 is not None else float("nan"),
            "berv_kms": float(berv) if berv is not None else float("nan"),
            "dpr_type": str(hdr.get("HIERARCH ESO DPR TYPE", "")),
            "object_hdr": str(hdr.get("OBJECT", "")),
            "n_pix": int(wave.size),
            "med_flux": med_flux,
        }


def download_and_verify_stratum(star: str, s_idx: int, bucket: list[dict[str, object]]) -> dict[str, object]:
    star_dir = FITS_DIR / star
    star_dir.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for cand in bucket[:5]:
        dp_id = str(cand["dp_id"])
        dest = star_dir / f"{dp_id}.fits"
        for attempt in range(3):
            try:
                if not dest.exists() or dest.stat().st_size < 1_000_000:
                    url = DL_BASE + urllib.parse.quote(dp_id)
                    req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N12/1.0"})
                    tmp = dest.with_suffix(".fits.part")
                    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
                        while True:
                            chunk = resp.read(1 << 16)
                            if not chunk:
                                break
                            out.write(chunk)
                    tmp.replace(dest)
                meta = verify_harps_fits(dest)
                return {
                    "star": star,
                    "stratum": s_idx,
                    "dp_id": dp_id,
                    "tap_target": cand["target_name"],
                    "tap_snr": round(float(cand["snr"]), 2),
                    "mjd_obs": round(float(meta["mjd_obs"]), 6),
                    "exptime_s": round(float(meta["exptime_s"]), 2),
                    "snr_hdr": round(float(meta["snr_hdr"]), 2) if np.isfinite(float(meta["snr_hdr"])) else cand["snr"],
                    "berv_kms": round(float(meta["berv_kms"]), 5) if np.isfinite(float(meta["berv_kms"])) else "",
                    "dpr_type": meta["dpr_type"],
                    "object_hdr": meta["object_hdr"],
                    "bytes": int(dest.stat().st_size),
                    "sha256": sha256_file(dest),
                    "local_path": str(dest.relative_to(ROOT)),
                }
            except Exception as exc:
                last_err = exc
                if dest.exists():
                    dest.unlink(missing_ok=True)
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{star} stratum {s_idx} failed: {last_err}")


def main() -> int:
    t0 = time.time()
    INP.mkdir(parents=True, exist_ok=True)
    FITS_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_tap_for_target(tgt: dict[str, object]) -> tuple[str, int, list[list[dict[str, object]]]]:
        star = str(tgt["star"])
        raw = query_eso_tap(float(tgt["ra_deg"]), float(tgt["dec_deg"]))
        strata = select_stratified_candidates(tgt, raw, n_strata=20)
        return star, len(raw), strata

    jobs: list[tuple[str, int, list[dict[str, object]]]] = []
    tap_counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=8) as tpool:
        for star, n_raw, strata in tpool.map(fetch_tap_for_target, TARGETS):
            tap_counts[star] = n_raw
            print(f"[N12 Stage 1 TAP] {star}: {n_raw} raw rows -> 20 strata")
            for s_idx, bucket in enumerate(strata):
                jobs.append((star, s_idx, bucket))

    verified_rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(download_and_verify_stratum, st, idx, bkt): (st, idx) for st, idx, bkt in jobs}
        done_cnt = 0
        for fut in as_completed(futs):
            row = fut.result()
            verified_rows.append(row)
            done_cnt += 1
            if done_cnt % 80 == 0 or done_cnt == len(jobs):
                print(f"[N12 Stage 1 DL] Verified {done_cnt}/{len(jobs)} HARPS FITS ({time.time()-t0:.1f}s)")

    verified_rows.sort(key=lambda r: (str(r["star"]), int(r["stratum"])))
    csv_path = INP / "n12_harps_epochs.csv"
    cols = ["star", "stratum", "dp_id", "tap_target", "tap_snr", "mjd_obs", "exptime_s", "snr_hdr", "berv_kms", "dpr_type", "object_hdr", "bytes", "sha256", "local_path"]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(verified_rows)

    total_bytes = sum(int(r["bytes"]) for r in verified_rows)
    log = {
        "campaign": "SPOR_N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_AND_COMB",
        "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "stars": len(TARGETS),
        "epochs_per_star": 20,
        "epochs_verified": len(verified_rows),
        "total_bytes": total_bytes,
        "total_mib": round(total_bytes / (1 << 20), 2),
        "tap_raw_counts": tap_counts,
        "external_contacts": 0,
    }
    (INP / "stage1_acquisition_log.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(f"[N12 Stage 1 Complete] Verified {len(verified_rows)}/480 HARPS FITS ({log['total_mib']} MiB) in {log['elapsed_s']}s")
    return 0 if len(verified_rows) == 480 else 1


if __name__ == "__main__":
    raise SystemExit(main())
