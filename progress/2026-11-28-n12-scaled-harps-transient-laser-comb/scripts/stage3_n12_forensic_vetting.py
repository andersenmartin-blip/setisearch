#!/usr/bin/env python3
"""Stage 3 Forensic Vetting for Spor N12 (24 New <9.5 pc G/K/M Stars, 480 HARPS Spectra, Channels T1 + T2)."""
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
WS = ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb"
INP = ROOT / "inputs_n12_20261128"
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

THAR_LINES_A = {
    "ArI_5912": 5912.085,
    "ArI_6032": 6032.127,
    "ArI_6043": 6043.223,
    "ArI_6145": 6145.441,
    "ArI_6416": 6416.307,
    "ThI_6457": 6457.282,
    "ArI_6677": 6677.282,
    "ArI_6753": 6752.834,
    "ArI_6871": 6871.289,
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
    "EPSERI": {"ra": 53.2249, "dec": -9.4559, "rv": 16.0},
    "HD217987": {"ra": 346.5102, "dec": -35.8457, "rv": 8.2},
    "TAUCET": {"ra": 26.0061, "dec": -15.9306, "rv": -17.1},
    "HD209100": {"ra": 330.8512, "dec": -56.7881, "rv": -40.7},
    "GJ191": {"ra": 77.9674, "dec": -45.0478, "rv": 245.0},
    "WOLF1061": {"ra": 247.5749, "dec": -12.6687, "rv": -21.0},
    "GJ9066": {"ra": 30.0579, "dec": 13.0396, "rv": -28.8},
    "GJ674": {"ra": 262.1603, "dec": -46.8984, "rv": -2.9},
    "GJ876": {"ra": 343.3241, "dec": -14.2667, "rv": -1.6},
    "GJ832": {"ra": 323.3844, "dec": -49.0143, "rv": 12.5},
    "GJ682": {"ra": 264.2565, "dec": -44.3288, "rv": -60.0},
    "GJ3323": {"ra": 75.4850, "dec": -6.9487, "rv": 42.5},
    "HD42581": {"ra": 92.6450, "dec": -21.8664, "rv": 4.0},
    "GJ752A": {"ra": 289.2277, "dec": 5.1653, "rv": 35.7},
    "HD20794": {"ra": 50.0053, "dec": -43.0656, "rv": 87.9},
    "GJ581": {"ra": 229.8541, "dec": -7.7269, "rv": 9.8},
    "LTT1445A": {"ra": 45.4609, "dec": -16.5955, "rv": -5.4},
    "GJ393": {"ra": 157.2288, "dec": 0.8377, "rv": 8.3},
    "GJ514": {"ra": 202.5061, "dec": 10.3681, "rv": 14.6},
    "HD115617": {"ra": 199.6013, "dec": -18.3112, "rv": -8.2},
    "GJ849": {"ra": 332.4247, "dec": -4.6407, "rv": -15.3},
    "HD192310": {"ra": 303.8257, "dec": -27.0333, "rv": -54.2},
    "GJ433": {"ra": 173.8619, "dec": -32.5437, "rv": 17.5},
    "GJ367": {"ra": 146.1203, "dec": -45.7801, "rv": 47.9},
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
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N12-Stage3/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                rows = list(csv.DictReader(resp.read().decode("utf-8", errors="replace").splitlines()))
            cands: list[dict[str, object]] = []
            for r in rows:
                dp = (r.get("dp_id") or "").strip()
                if not dp.startswith("ADP.") or dp == trigger_dp:
                    continue
                tname = (r.get("target_name") or "").upper()
                if star == "HD209100" and any(b in tname for b in ("IND B", "IND C", "INDB", "INDC")):
                    continue
                if star == "LTT1445A" and any(b in tname for b in ("1445B", "1445C")):
                    continue
                try:
                    t_m = float(r["t_min"])
                    expt = float(r.get("t_exptime") or 0.0)
                    snr = float(r.get("snr") or 0.0)
                except (ValueError, TypeError):
                    continue
                if expt < 10.0:
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
    sdir = FOLLOW_DIR / star
    sdir.mkdir(parents=True, exist_ok=True)
    fpath = sdir / f"{follow_dp}.fits"
    if not fpath.exists() or fpath.stat().st_size < 1_000_000:
        url = DL_BASE + urllib.parse.quote(follow_dp)
        req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N12-Stage3/1.0"})
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
    return float(np.max(zmf[cwin])), float(sig), str(fpath.relative_to(ROOT))


def main() -> int:
    t0 = time.time()
    FOLLOW_DIR.mkdir(parents=True, exist_ok=True)
    triggers = load_csv(RES / "N12_STAGE2_TRIGGERS.csv")
    diags = load_csv(RES / "N12_PEAK_DIAGNOSTICS.csv")
    epochs = load_csv(INP / "n12_harps_epochs.csv")
    ep_map = {(r["star"], r["dp_id"]): r for r in epochs}
    by_star_ep: dict[str, list[dict[str, str]]] = {}
    for r in epochs:
        by_star_ep.setdefault(r["star"], []).append(r)

    topo_peaks: list[tuple[str, str, float]] = []
    for d in diags:
        lb = float(d["lam_bary_a"])
        bv = float(d["berv_kms"]) if d["berv_kms"] else 0.0
        topo_peaks.append((d["star"], d["dp_id"], lb / (1.0 + bv / C_KMS)))

    # Pre-scan triggers per exposure against canonical Ar I / Th I calibration lamp lines (physics-based ThAr exposure unmasking)
    thar_hits_by_exp: dict[tuple[str, str], set[str]] = {}
    for tr in triggers:
        lb = float(tr["lam_bary_a"])
        bv = float(tr["berv_kms"]) if tr["berv_kms"] else 0.0
        lt = lb / (1.0 + bv / C_KMS)
        key = (tr["star"], tr["dp_id"])
        for tname, tlam in THAR_LINES_A.items():
            if abs(lt - tlam) <= 0.08:
                thar_hits_by_exp.setdefault(key, set()).add(tname)
    thar_contaminated_exps = {k: sorted(v) for k, v in thar_hits_by_exp.items() if len(v) >= 2}

    flare_cache: dict[tuple[str, str], tuple[float, float]] = {}
    tap_cache: dict[tuple[str, str], list[dict[str, object]]] = {}
    vetted: list[dict[str, object]] = []
    counts_by_veto: dict[str, int] = {}

    for tr in triggers:
        star = tr["star"]
        ch = tr["channel"]
        dp_id = tr["dp_id"]
        lb = float(tr["lam_bary_a"])
        bv = float(tr["berv_kms"]) if tr["berv_kms"] else 0.0
        lt = lb / (1.0 + bv / C_KMS)
        mjd = float(tr["mjd_obs"])
        emeta = ep_map[(star, dp_id)]
        dpr = emeta.get("dpr_type", "")
        fpath = ROOT / emeta["local_path"]

        if (star, dp_id) not in flare_cache:
            flare_cache[(star, dp_id)] = flare_ratios(fpath)
        ha_r, hb_r = flare_cache[(star, dp_id)]

        veto_reason = "UNRESOLVED_ETI_CANDIDATE"
        eti_status = "UNRESOLVED_ETI_CANDIDATE"
        detail = ""

        if (star, dp_id) in thar_contaminated_exps:
            veto_reason = "MISLABELED_THAR_LAMP_CONTAMINATED_EXPOSURE"
            eti_status = "FALSE_POSITIVE_INSTRUMENTAL_THAR"
            detail = f"dpr={dpr}, matched_ThAr={thar_contaminated_exps[(star, dp_id)]}"
        elif ch == "T2_OPTICAL_COMB":
            teeth_str = tr.get("comb_teeth", "")
            teeth_lams = [float(x.split("@")[0]) for x in teeth_str.split(";") if "@" in x]
            if ha_r >= 2.2 or hb_r >= 2.2:
                veto_reason = "CHROMOSPHERIC_FLARE_COMB"
                eti_status = "FALSE_POSITIVE_STELLAR_FLARE"
                detail = f"Ha={ha_r:.2f}, Hb={hb_r:.2f}, teeth={len(teeth_lams)}"
            else:
                if (star, dp_id) not in tap_cache:
                    tap_cache[(star, dp_id)] = query_adjacent_harps(star, dp_id, mjd)
                cands = tap_cache[(star, dp_id)]
                ref_cands = [ROOT / x["local_path"] for x in by_star_ep[star] if x["dp_id"] != dp_id]
                rep_count = 0
                checked_f = False
                for cd in cands[:1]:
                    checked_f = True
                    z_teeth: list[float] = []
                    for tlam in teeth_lams:
                        try:
                            zf, _s, _p = check_followup_spectrum(star, str(cd["dp_id"]), tlam, ref_cands)
                            z_teeth.append(zf)
                            if zf >= 4.0:
                                rep_count += 1
                        except Exception:
                            pass
                    detail = f"adj_dp={cd['dp_id']}, rep_teeth={rep_count}/{len(teeth_lams)}, max_Z={max(z_teeth) if z_teeth else 0:.2f}"
                if checked_f and rep_count == 0:
                    veto_reason = "NONREPEATING_COMB_NOISE_EXCURSION"
                    eti_status = "FALSE_POSITIVE_COSMIC_OR_NOISE"
                elif not checked_f:
                    veto_reason = "ISOLATED_UNCORROBORATED_COMB_EXCURSION"
                    eti_status = "FALSE_POSITIVE_COSMIC_OR_NOISE"
                    detail = f"no_eso_adj_1.5d, teeth={len(teeth_lams)}"
        else:
            sky_hit = [k for k, v in SKY_LINES_A.items() if abs(lt - v) <= 0.18]
            cross_match = [(s2, d2) for s2, d2, lt2 in topo_peaks if s2 != star and abs(lt - lt2) <= 0.08]
            in_telluric = (5880.0 <= lt <= 5960.0) or (6275.0 <= lt <= 6325.0) or (6465.0 <= lt <= 6595.0) or (6845.0 <= lt <= 6900.0)
            if sky_hit or cross_match or in_telluric:
                veto_reason = "TERRESTRIAL_AIRGLOW_OR_TELLURIC"
                eti_status = "FALSE_POSITIVE_ATMOSPHERIC"
                detail = f"sky={sky_hit}, cross={len(cross_match)}, telluric={in_telluric}, lam_topo={lt:.3f}"
            elif "WAVE" in dpr.upper():
                veto_reason = "SIMCAL_FIBER_B_WAVE_BLEED"
                eti_status = "FALSE_POSITIVE_INSTRUMENTAL"
                detail = f"dpr={dpr}"
            else:
                rv = STAR_META[star]["rv"]
                l_star = lb / (1.0 + rv / C_KMS)
                ch_hit = [k for k, v in CHROMOSPHERIC_LINES_A.items() if abs(l_star - v) <= 0.40]
                if ch_hit or ha_r >= 2.2 or hb_r >= 2.2:
                    veto_reason = "CHROMOSPHERIC_STELLAR_FLARE"
                    eti_status = "FALSE_POSITIVE_STELLAR_FLARE"
                    detail = f"lines={ch_hit}, Ha={ha_r:.2f}, Hb={hb_r:.2f}"
                else:
                    if (star, dp_id) not in tap_cache:
                        tap_cache[(star, dp_id)] = query_adjacent_harps(star, dp_id, mjd)
                    cands = tap_cache[(star, dp_id)]
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
                        _dp0, _dt0, z0 = checked_vals[0]
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
        print(f"[N12 Stage 3] {star:10s} {ch:14s} lam={lb:.3f} z={tr['z_mf']} -> {veto_reason} ({detail})")

    base_cols = list(triggers[0].keys()) if triggers else ["star", "channel", "epoch_idx", "dp_id", "mjd_obs", "berv_kms", "lam_bary_a", "z_mf", "n_epochs_gt5", "fit_sigma_px", "psf_sigma_px", "fwhm_ratio", "r_gauss", "n_pix_gt3", "min_neg_ratio", "stage2_status", "comb_teeth"]
    cols = base_cols + ["lam_topo_a", "dpr_type", "ha_ratio", "veto_reason", "eti_status", "forensic_detail"]
    with (RES / "N12_CANDIDATES_VETTED.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(vetted)

    diag_counts: dict[str, int] = {}
    for d in diags:
        st = d["stage2_status"]
        diag_counts[st] = diag_counts.get(st, 0) + 1

    verified_eti = sum(1 for v in vetted if v["eti_status"] == "UNRESOLVED_ETI_CANDIDATE")
    summary = {
        "campaign": "SPOR_N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_AND_COMB",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "peaks_z10_before_shape_veto": len(diags),
        "stage2_diag_breakdown": diag_counts,
        "stage2_triggers_vetted": len(vetted),
        "veto_breakdown": counts_by_veto,
        "verified_eti_candidates": verified_eti,
        "external_contacts": 0,
    }
    (RES / "N12_STAGE3_VETTING.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[N12 Stage 3 Complete] Vetted {len(vetted)} triggers -> {verified_eti} verified ETI in {summary['elapsed_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
