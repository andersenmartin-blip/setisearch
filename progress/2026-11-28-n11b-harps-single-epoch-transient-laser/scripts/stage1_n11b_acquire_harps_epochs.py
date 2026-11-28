#!/usr/bin/env python3
"""Stage 1 for Spor N11B: Acquire and verify 20 BERV-diverse high-SNR HARPS Phase-3 1D spectra x 8 <11 pc M-dwarfs."""
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
INP = ROOT / "inputs_n11b_20261128"
FITS_DIR = INP / "fits"

TAP_URL = "https://archive.eso.org/tap_obs/sync"
DL_BASE = "https://dataportal.eso.org/dataportal_new/file/"

TARGETS = [
    {"star": "PROXIMACEN", "common_name": "Proxima Centauri", "ra_deg": 217.384988, "dec_deg": -62.675580, "dist_pc": 1.3020, "n_pl": 2, "vmag": 11.13, "alias_ok": ("PROXIMA", "GJ551", "HIP70890", "ALPHACENC")},
    {"star": "BARNARDSSTAR", "common_name": "Barnard's Star", "ra_deg": 269.447597, "dec_deg": 4.749680, "dist_pc": 1.8282, "n_pl": 4, "vmag": 9.51, "alias_ok": ("BARNARD", "GJ699", "HIP87937", "HD163993", "GL699")},
    {"star": "ROSS128", "common_name": "Ross 128", "ra_deg": 176.938157, "dec_deg": 0.797370, "dist_pc": 3.3749, "n_pl": 1, "vmag": 11.15, "alias_ok": ("ROSS128", "GJ447", "HIP57548", "FI VIR", "FIVIR", "GL447")},
    {"star": "GJ1061", "common_name": "GJ 1061", "ra_deg": 54.003394, "dec_deg": -44.514362, "dist_pc": 3.6743, "n_pl": 3, "vmag": 13.09, "alias_ok": ("GJ1061", "GL1061", "LHS1565")},
    {"star": "YZCET", "common_name": "YZ Cet (GJ 54.1)", "ra_deg": 18.133254, "dec_deg": -16.996155, "dist_pc": 3.7167, "n_pl": 3, "vmag": 12.07, "alias_ok": ("YZCET", "GJ54.1", "GL54.1", "HIP5643", "LHS138")},
    {"star": "GJ273", "common_name": "Luyten's Star", "ra_deg": 111.854844, "dec_deg": 5.207330, "dist_pc": 3.7861, "n_pl": 2, "vmag": 9.87, "alias_ok": ("GJ273", "GL273", "LUYTEN", "HIP36208", "BD+051668")},
    {"star": "GJ667C", "common_name": "GJ 667 C", "ra_deg": 259.751267, "dec_deg": -34.997772, "dist_pc": 7.2429, "n_pl": 5, "vmag": 10.22, "alias_ok": ("GJ667C", "GL667C", "HD156384C", "HIP84709C")},
    {"star": "L9859", "common_name": "L 98-59", "ra_deg": 124.524584, "dec_deg": -68.315490, "dist_pc": 10.6194, "n_pl": 5, "vmag": 11.68, "alias_ok": ("L98-59", "L9859", "TOI-175", "TOI175", "TIC307210830", "CD-68475")},
]


def query_eso_tap(ra_deg: float, dec_deg: float, radius_deg: float = 0.08) -> list[dict[str, str]]:
    """Query ESO ObsCore TAP synchronously without ORDER BY to prevent gateway timeouts."""
    sql = (
        "SELECT TOP 900 dp_id, target_name, t_min, t_exptime, s_ra, s_dec, snr "
        "FROM ivoa.ObsCore "
        "WHERE instrument_name = 'HARPS' AND dataproduct_type = 'spectrum' "
        f"AND 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra_deg:.6f}, {dec_deg:.6f}, {radius_deg:.4f}))"
    )
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": sql})
    url = f"{TAP_URL}?{params}"
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N11B/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            rows = list(csv.DictReader(text.splitlines()))
            return rows
        except Exception as exc:
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"TAP query failed after retries: {last_err}")


def norm_name(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum() or ch in "+-.")


def select_stratified_candidates(
    target: dict[str, object], raw_rows: list[dict[str, str]], n_strata: int = 20
) -> list[list[dict[str, object]]]:
    """Filter HARPS candidates and split into 20 time strata for diverse BERV baselines."""
    seen: set[str] = set()
    clean: list[dict[str, object]] = []
    aliases = tuple(norm_name(a) for a in target["alias_ok"])  # type: ignore[index]
    is_gj667c = target["star"] == "GJ667C"

    for r in raw_rows:
        dp_id = (r.get("dp_id") or "").strip()
        if not dp_id.startswith("ADP.") or dp_id in seen:
            continue
        tname = norm_name(r.get("target_name") or "")
        if is_gj667c and any(bad in tname for bad in ("667A", "667B", "667AB")) and "667C" not in tname:
            continue
        if is_gj667c and "667" in tname and "C" not in tname:
            continue
        try:
            mjd = float(r["t_min"])
            expt = float(r.get("t_exptime") or 0.0)
            snr = float(r.get("snr") or 0.0)
        except (ValueError, TypeError):
            continue
        if expt < 120.0:
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

    # Prefer strict name match and t_exptime >= 300s if >= 25 available
    preferred = [c for c in clean if c["name_match"] and float(c["exptime"]) >= 300.0 and float(c["snr"]) >= 8.0]
    if len(preferred) < n_strata + 5:
        preferred = [c for c in clean if c["name_match"] and float(c["exptime"]) >= 120.0]
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
        mask = (wave >= 4000.0) & (wave <= 6900.0) & np.isfinite(flux) & (flux > 0)
        if int(np.sum(mask)) < 200000:
            raise ValueError(f"Insufficient valid 4000-6900 A pixels in {path.name}")
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
    for cand in bucket[:4]:
        dp_id = str(cand["dp_id"])
        dest = star_dir / f"{dp_id}.fits"
        for attempt in range(3):
            try:
                if not dest.exists() or dest.stat().st_size < 1_000_000:
                    url = DL_BASE + urllib.parse.quote(dp_id)
                    req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N11B/1.0"})
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

    jobs: list[tuple[str, int, list[dict[str, object]]]] = []
    tap_counts: dict[str, int] = {}
    for tgt in TARGETS:
        star = str(tgt["star"])
        raw = query_eso_tap(float(tgt["ra_deg"]), float(tgt["dec_deg"]))
        tap_counts[star] = len(raw)
        strata = select_stratified_candidates(tgt, raw, n_strata=20)
        print(f"[N11B Stage 1 TAP] {star}: {len(raw)} raw rows -> 20 strata prepared")
        for s_idx, bucket in enumerate(strata):
            jobs.append((star, s_idx, bucket))

    verified_rows: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(download_and_verify_stratum, st, idx, bkt): (st, idx) for st, idx, bkt in jobs}
        for fut in as_completed(futs):
            row = fut.result()
            verified_rows.append(row)

    verified_rows.sort(key=lambda r: (str(r["star"]), int(r["stratum"])))
    csv_path = INP / "n11b_harps_epochs.csv"
    cols = ["star", "stratum", "dp_id", "tap_target", "tap_snr", "mjd_obs", "exptime_s", "snr_hdr", "berv_kms", "dpr_type", "object_hdr", "bytes", "sha256", "local_path"]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(verified_rows)

    total_bytes = sum(int(r["bytes"]) for r in verified_rows)
    log = {
        "campaign": "SPOR_N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER",
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
    print(f"[N11B Stage 1] Verified {len(verified_rows)}/160 HARPS FITS ({log['total_mib']} MiB) in {log['elapsed_s']}s")
    return 0 if len(verified_rows) == 160 else 1


if __name__ == "__main__":
    raise SystemExit(main())
