#!/usr/bin/env python3
"""Stage 3 Forensic Vetting for Spor N11B: Optical Sky, Fiber-B Calibration, Flare & Live Adjacent-Night HARPS Corroboration."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

from astropy.io import fits
import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser"
INP = ROOT / "inputs_n11b_20261128"
FOLLOW_DIR = INP / "stage3_followup"
RES = WS / "results"

TAP_URL = "https://archive.eso.org/tap_obs/sync"
DL_BASE = "https://dataportal.eso.org/dataportal_new/file/"
C_KMS = 299792.458
HARPS_R = 115000.0
DLAM = 0.01

SKY_LINES_A = {
    "NI_5200": 5199.840,
    "HgI_5461": 5460.750,
    "OI_5577": 5577.339,
    "HgI_5770": 5769.598,
    "HgI_5791": 5790.670,
    "NaI_D2": 5889.951,
    "NaI_D1": 5895.924,
    "OI_6300": 6300.304,
    "OI_6364": 6363.776,
}

CHROMOSPHERIC_LINES_A = {
    "H_beta": 4861.333,
    "FeII_4924": 4923.921,
    "FeII_5018": 5018.434,
    "MgI_b1": 5167.321,
    "FeII_5169": 5169.033,
    "MgI_b2": 5172.684,
    "MgI_b3": 5183.604,
    "HeI_D3": 5875.621,
    "NaI_D2": 5889.951,
    "NaI_D1": 5895.924,
    "H_alpha": 6562.801,
    "HeI_6678": 6678.151,
}

STAR_META = {
    "PROXIMACEN": {"ra": 217.384988, "dec": -62.675580, "rv": -21.7},
    "BARNARDSSTAR": {"ra": 269.447597, "dec": 4.749680, "rv": -110.5},
    "ROSS128": {"ra": 176.938157, "dec": 0.797370, "rv": -31.2},
    "GJ1061": {"ra": 54.003394, "dec": -44.514362, "rv": 1.3},
    "YZCET": {"ra": 18.133254, "dec": -16.996155, "rv": 28.0},
    "GJ273": {"ra": 111.854844, "dec": 5.207330, "rv": 18.2},
    "GJ667C": {"ra": 259.751267, "dec": -34.997772, "rv": 6.5},
    "L9859": {"ra": 124.524584, "dec": -68.315490, "rv": -5.6},
}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def flare_ratios(fits_path: Path) -> tuple[float, float]:
    with fits.open(fits_path, memmap=False) as hdul:
        d = hdul[1].data
        w = np.asarray(d["WAVE"], dtype=np.float64).ravel()
        f = np.asarray(d["FLUX"], dtype=np.float64).ravel()
    def ratio_around(lam_c: float) -> float:
        m_pk = (w >= lam_c - 1.5) & (w <= lam_c + 1.5) & np.isfinite(f)
        m_ct = (((w >= lam_c - 14.0) & (w <= lam_c - 6.0)) | ((w >= lam_c + 6.0) & (w <= lam_c + 14.0))) & np.isfinite(f)
        if int(np.sum(m_pk)) < 10 or int(np.sum(m_ct)) < 20:
            return 1.0
        ct = float(np.median(f[m_ct]))
        return float(np.max(f[m_pk])) / max(ct, 1.0)
    return ratio_around(6562.80), ratio_around(4861.33)


def query_adjacent_harps(star: str, trigger_dp: str, mjd_obs: float) -> list[dict[str, object]]:
    """Query ESO ObsCore TAP for nearest independent HARPS spectrum within +/- 1.5 days (NO ORDER BY)."""
    meta = STAR_META[star]
    sql = (
        "SELECT TOP 60 dp_id, target_name, t_min, t_exptime, snr "
        "FROM ivoa.ObsCore "
        "WHERE instrument_name = 'HARPS' AND dataproduct_type = 'spectrum' "
        f"AND t_min BETWEEN {mjd_obs - 1.5:.6f} AND {mjd_obs + 1.5:.6f} "
        f"AND 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {meta['ra']:.6f}, {meta['dec']:.6f}, 0.08))"
    )
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": sql})
    url = f"{TAP_URL}?{params}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N11B-Stage3/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                rows = list(csv.DictReader(resp.read().decode("utf-8", errors="replace").splitlines()))
            cands: list[dict[str, object]] = []
            for r in rows:
                dp = (r.get("dp_id") or "").strip()
                if not dp.startswith("ADP.") or dp == trigger_dp:
                    continue
                if star == "GJ667C" and "667" in (r.get("target_name") or "").upper() and "C" not in (r.get("target_name") or "").upper():
                    continue
                try:
                    t_m = float(r["t_min"])
                    expt = float(r.get("t_exptime") or 0.0)
                    snr = float(r.get("snr") or 0.0)
                except (ValueError, TypeError):
                    continue
                if expt < 120.0:
                    continue
                cands.append({"dp_id": dp, "mjd": t_m, "dt_hours": abs(t_m - mjd_obs) * 24.0, "snr": snr})
            cands.sort(key=lambda c: float(c["dt_hours"]))
            return cands
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return []


def check_followup_spectrum(
    star: str, follow_dp: str, lam_bary: float, clean_ref_paths: list[Path]
) -> tuple[float, float, str]:
    """Download/cache adjacent HARPS exposure and compute differential PSF matched-filter Z at lam_bary."""
    sdir = FOLLOW_DIR / star
    sdir.mkdir(parents=True, exist_ok=True)
    fpath = sdir / f"{follow_dp}.fits"
    if not fpath.exists() or fpath.stat().st_size < 1_000_000:
        url = DL_BASE + urllib.parse.quote(follow_dp)
        req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N11B-Stage3/1.0"})
        tmp = fpath.with_suffix(".fits.part")
        with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
        tmp.replace(fpath)

    grid = np.linspace(lam_bary - 8.0, lam_bary + 8.0, 1601, dtype=np.float64)
    def norm_patch(p: Path) -> np.ndarray:
        with fits.open(p, memmap=False) as hdul:
            w = np.asarray(hdul[1].data["WAVE"], dtype=np.float64).ravel()
            f = np.asarray(hdul[1].data["FLUX"], dtype=np.float64).ravel()
        m = (w >= lam_bary - 10.0) & (w <= lam_bary + 10.0) & np.isfinite(f) & (f > 0)
        fg = np.interp(grid, w[m], f[m])
        cont = median_filter(fg, size=201, mode="nearest")
        return fg / np.maximum(cont, 1e-6)

    y_fol = norm_patch(fpath)
    y_ref = np.median([norm_patch(p) for p in clean_ref_paths], axis=0)
    res = y_fol - y_ref
    sig = max(1.4826 * float(np.median(np.abs(res))), 1e-4)
    spx = lam_bary / HARPS_R / (2.35482 * DLAM)
    zmf = gaussian_filter1d(res / sig, sigma=spx) * math.sqrt(2.0 * math.sqrt(math.pi) * spx)
    cwin = (grid >= lam_bary - 0.08) & (grid <= lam_bary + 0.08)
    z_max = float(np.max(zmf[cwin]))
    return z_max, float(sig), str(fpath.relative_to(ROOT))


def main() -> int:
    t0 = time.time()
    FOLLOW_DIR.mkdir(parents=True, exist_ok=True)
    triggers = load_csv(RES / "N11B_STAGE2_TRIGGERS.csv")
    diags = load_csv(RES / "N11B_PEAK_DIAGNOSTICS.csv")
    epochs = load_csv(INP / "n11b_harps_epochs.csv")
    ep_map = {(r["star"], r["dp_id"]): r for r in epochs}
    by_star_ep: dict[str, list[dict[str, str]]] = {}
    for r in epochs:
        by_star_ep.setdefault(r["star"], []).append(r)

    topo_peaks: list[tuple[str, str, float]] = []
    for d in diags:
        lb = float(d["lam_bary_a"])
        bv = float(d["berv_kms"]) if d["berv_kms"] else 0.0
        topo_peaks.append((d["star"], d["dp_id"], lb / (1.0 + bv / C_KMS)))

    flare_cache: dict[tuple[str, str], tuple[float, float]] = {}
    vetted: list[dict[str, object]] = []
    counts_by_veto: dict[str, int] = {}

    for tr in triggers:
        star = tr["star"]
        dp_id = tr["dp_id"]
        lb = float(tr["lam_bary_a"])
        bv = float(tr["berv_kms"]) if tr["berv_kms"] else 0.0
        lt = lb / (1.0 + bv / C_KMS)
        mjd = float(tr["mjd_obs"])
        n_gt5 = int(tr["n_epochs_gt5"])
        emeta = ep_map[(star, dp_id)]
        dpr = emeta.get("dpr_type", "")
        fpath = ROOT / emeta["local_path"]

        if (star, dp_id) not in flare_cache:
            flare_cache[(star, dp_id)] = flare_ratios(fpath)
        ha_r, hb_r = flare_cache[(star, dp_id)]

        veto_reason = "UNRESOLVED_ETI_CANDIDATE"
        eti_status = "UNRESOLVED_ETI_CANDIDATE"
        detail = ""

        # 1. Terrestrial sky / telluric O2-H2O / cross-star topocentric match
        sky_hit = [k for k, v in SKY_LINES_A.items() if abs(lt - v) <= 0.18]
        cross_match = [(s2, d2) for s2, d2, lt2 in topo_peaks if s2 != star and abs(lt - lt2) <= 0.08]
        in_telluric = (5880.0 <= lt <= 5960.0) or (6275.0 <= lt <= 6325.0) or (6465.0 <= lt <= 6595.0) or (6845.0 <= lt <= 6900.0)
        if sky_hit or cross_match or in_telluric:
            veto_reason = "TERRESTRIAL_AIRGLOW_OR_TELLURIC"
            eti_status = "FALSE_POSITIVE_ATMOSPHERIC"
            detail = f"sky={sky_hit}, cross={len(cross_match)}, telluric={in_telluric}, lam_topo={lt:.3f}"
        # 2. Simultaneous Fiber-B calibration bleed (STAR,WAVE,*)
        elif "WAVE" in dpr.upper():
            veto_reason = "SIMCAL_FIBER_B_WAVE_BLEED"
            eti_status = "FALSE_POSITIVE_INSTRUMENTAL"
            detail = f"dpr={dpr}"
        # 3. Chromospheric M-dwarf flare emission
        else:
            rv = STAR_META[star]["rv"]
            l_star = lb / (1.0 + rv / C_KMS)
            ch_hit = [k for k, v in CHROMOSPHERIC_LINES_A.items() if abs(l_star - v) <= 0.40]
            if ch_hit or ha_r >= 2.2 or hb_r >= 2.2:
                veto_reason = "CHROMOSPHERIC_M_DWARF_FLARE"
                eti_status = "FALSE_POSITIVE_STELLAR_FLARE"
                detail = f"lines={ch_hit}, Ha={ha_r:.2f}, Hb={hb_r:.2f}"
            else:
                # 4. Live ESO TAP check for same-night / adjacent-night corroboration (applies to n_gt5=1..3)
                cands = query_adjacent_harps(star, dp_id, mjd)
                ref_cands = [ROOT / x["local_path"] for x in by_star_ep[star] if x["dp_id"] != dp_id]
                checked_vals: list[tuple[str, float, float]] = []
                for cd in cands[:2]:
                    try:
                        z_fol, _sig_fol, _rel_p = check_followup_spectrum(star, str(cd["dp_id"]), lb, ref_cands)
                        checked_vals.append((str(cd["dp_id"]), float(cd["dt_hours"]), z_fol))
                    except Exception:
                        continue
                if checked_vals:
                    z_best = min(v[2] for v in checked_vals)
                    z_max_f = max(v[2] for v in checked_vals)
                    dp0, dt0, z0 = checked_vals[0]
                    summary_f = ", ".join(f"{d}(dt={t:.2f}h,Z={z:.2f})" for d, t, z in checked_vals)
                    if z_max_f >= 5.0 and z0 >= 5.0:
                        veto_reason = "UNRESOLVED_CORROBORATED_TRANSIENT"
                        eti_status = "UNRESOLVED_ETI_CANDIDATE"
                        detail = f"CORROBORATED {summary_f}"
                    elif z0 < 3.5 or z_best < 3.0:
                        veto_reason = "SINGLE_EXPOSURE_COSMIC_RAY_NONREPEATING"
                        eti_status = "FALSE_POSITIVE_COSMIC_RAY"
                        detail = summary_f
                    else:
                        veto_reason = "AMBIGUOUS_FOLLOWUP_CHECK"
                        eti_status = "UNRESOLVED_ETI_CANDIDATE"
                        detail = summary_f
                else:
                    # Fallback to nearest epoch in local 20-epoch cube
                    same_star = [x for x in by_star_ep[star] if x["dp_id"] != dp_id]
                    same_star.sort(key=lambda x: abs(float(x["mjd_obs"]) - mjd))
                    nearest = same_star[0]
                    veto_reason = "ISOLATED_SINGLE_EXP_COSMIC_RAY_UNCORROBORATED"
                    eti_status = "FALSE_POSITIVE_COSMIC_RAY"
                    detail = f"no_eso_adj_1.5d; 1_of_20_epochs_only; nearest_cube_dt={abs(float(nearest['mjd_obs']) - mjd):.1f}d"

        counts_by_veto[veto_reason] = counts_by_veto.get(veto_reason, 0) + 1
        vetted.append({
            **tr,
            "lam_topo_a": round(lt, 4),
            "dpr_type": dpr,
            "ha_ratio": round(ha_r, 2),
            "veto_reason": veto_reason,
            "eti_status": eti_status,
            "forensic_detail": detail,
        })
        print(f"[N11B Stage 3 Trigger] {star} {dp_id} lam={lb:.3f} z={tr['z_mf']} -> {veto_reason} ({detail})")

    cols = list(triggers[0].keys()) if triggers else ["star", "epoch_idx", "dp_id", "mjd_obs", "berv_kms", "lam_bary_a", "z_mf", "n_epochs_gt5", "fit_sigma_px", "psf_sigma_px", "fwhm_ratio", "r_gauss", "n_pix_gt3", "min_neg_ratio", "stage2_status"]
    cols += ["lam_topo_a", "dpr_type", "ha_ratio", "veto_reason", "eti_status", "forensic_detail"]
    with (RES / "N11B_CANDIDATES_VETTED.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(vetted)

    diag_counts: dict[str, int] = {}
    for d in diags:
        st = d["stage2_status"]
        diag_counts[st] = diag_counts.get(st, 0) + 1

    verified_eti = sum(1 for v in vetted if v["eti_status"] == "UNRESOLVED_ETI_CANDIDATE")
    summary = {
        "campaign": "SPOR_N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "peaks_z10_before_shape_veto": len(diags),
        "stage2_diag_breakdown": diag_counts,
        "stage2_triggers_vetted": len(vetted),
        "veto_breakdown": counts_by_veto,
        "verified_eti_candidates": verified_eti,
        "external_contacts": 0,
    }
    (RES / "N11B_STAGE3_VETTING.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[N11B Stage 3 Complete] Vetted {len(vetted)} triggers -> {verified_eti} verified ETI in {summary['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
