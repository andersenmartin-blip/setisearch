#!/usr/bin/env python3
"""Stage 3 Forensic Vetting for Spor N14 (268 New Milky Way Confirmed Exoplanet Hosts, 2,144 HARPS Spectra)."""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from astropy.io import fits
import numpy as np
from scipy.ndimage import gaussian_filter1d, median_filter

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n14_20261128_300star_harps_transient_comb"
INP = ROOT / "inputs_n14_20261128"
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


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def download_fits(star: str, dp_id: str) -> Path:
    sdir = FOLLOW_DIR / star
    sdir.mkdir(parents=True, exist_ok=True)
    fpath = sdir / f"{dp_id}.fits"
    if fpath.exists() and fpath.stat().st_size >= 1_000_000:
        return fpath
    url = DL_BASE + urllib.parse.quote(dp_id)
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N14-Stage3/1.0"})
            tmp = fpath.with_suffix(".fits.part")
            with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as out:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
            if tmp.stat().st_size < 1_000_000:
                tmp.unlink(missing_ok=True)
                raise ValueError(f"Small FITS for {dp_id}")
            tmp.replace(fpath)
            return fpath
        except Exception as exc:
            last_err = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Failed download {dp_id}: {last_err}")


def read_fits_wf_rv(fpath: Path) -> tuple[np.ndarray, np.ndarray, float | None, float, str]:
    with fits.open(fpath, memmap=False) as hdul:
        hdr = hdul[0].header
        rv = None
        if hdr.get("HIERARCH ESO DRS CCF RVC") is not None:
            try:
                rv = float(hdr["HIERARCH ESO DRS CCF RVC"])
                if not math.isfinite(rv):
                    rv = None
            except (TypeError, ValueError):
                rv = None
        spec_res = float(hdr.get("SPEC_RES", 115000.0) or 115000.0)
        ins_mode = str(hdr.get("HIERARCH ESO INS MODE", "HARPS") or "HARPS").strip()
        d = hdul[1].data
        w = np.asarray(d["WAVE"], dtype=np.float64).ravel()
        f = np.asarray(d["FLUX"], dtype=np.float64).ravel()
    order = np.argsort(w)
    return w[order], f[order], rv, spec_res, ins_mode


def query_adjacent_harps(star: str, ra: float, dec: float, trigger_dp: str, mjd_obs: float) -> list[dict[str, object]]:
    sql = (
        "SELECT TOP 60 dp_id, target_name, t_min, t_exptime, snr "
        "FROM ivoa.ObsCore "
        "WHERE instrument_name = 'HARPS' AND dataproduct_type = 'spectrum' "
        f"AND t_min BETWEEN {mjd_obs - 1.5:.6f} AND {mjd_obs + 1.5:.6f} "
        f"AND 1=CONTAINS(POINT('ICRS', s_ra, s_dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, 0.05))"
    )
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": sql})
    url = f"{TAP_URL}?{params}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETIsearch-N14-Stage3/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                rows = list(csv.DictReader(resp.read().decode("utf-8", errors="replace").splitlines()))
            cands: list[dict[str, object]] = []
            for r in rows:
                dp = (r.get("dp_id") or "").strip()
                if not dp.startswith("ADP.") or dp == trigger_dp:
                    continue
                try:
                    t_m = float(r["t_min"])
                    expt = float(r.get("t_exptime") or 0.0)
                    snr = float(r.get("snr") or 0.0)
                except (ValueError, TypeError):
                    continue
                if expt < 10.0:
                    continue
                cands.append({"dp_id": dp, "target_name": (r.get("target_name") or "").strip(), "mjd": t_m, "dt_hours": abs(t_m - mjd_obs) * 24.0, "snr": snr})
            cands.sort(key=lambda c: float(c["dt_hours"]))
            return cands
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return []


def compute_followup_metrics(
    lam_bary: float,
    wf: tuple[np.ndarray, np.ndarray],
    ref_wfs: list[tuple[np.ndarray, np.ndarray]],
) -> tuple[float, float, float, float]:
    """Return (Z_mf, sig, max_excess_over_ref, local_norm_peak) around lam_bary."""
    grid = np.linspace(lam_bary - 8.0, lam_bary + 8.0, 1601, dtype=np.float64)

    def norm_patch(w: np.ndarray, f: np.ndarray) -> np.ndarray:
        m = (w >= lam_bary - 10.0) & (w <= lam_bary + 10.0) & np.isfinite(f) & (f > 0)
        if int(np.sum(m)) < 50:
            raise ValueError(f"Insufficient coverage near {lam_bary:.2f}")
        fg = np.interp(grid, w[m], f[m])
        cont = median_filter(fg, size=201, mode="nearest")
        return fg / np.maximum(cont, 1e-6)

    y_fol = norm_patch(*wf)
    y_ref = np.median([norm_patch(*rw) for rw in ref_wfs], axis=0)
    res = y_fol - y_ref
    sig = max(1.4826 * float(np.median(np.abs(res))), 1e-4)
    spx = lam_bary / HARPS_R / (2.35482 * DLAM)
    zmf = gaussian_filter1d(res / sig, sigma=spx) * math.sqrt(2.0 * math.sqrt(math.pi) * spx)
    cwin = (grid >= lam_bary - 0.08) & (grid <= lam_bary + 0.08)
    return float(np.max(zmf[cwin])), float(sig), float(np.max(res[cwin])), float(np.max(y_fol[cwin]))


def measure_continuum_step(lam_bary: float, w: np.ndarray, f: np.ndarray) -> float:
    ml = (w >= lam_bary - 1.5) & (w <= lam_bary - 0.5) & np.isfinite(f) & (f > 0)
    mr = (w >= lam_bary + 0.5) & (w <= lam_bary + 1.5) & np.isfinite(f) & (f > 0)
    if int(np.sum(ml)) < 20 or int(np.sum(mr)) < 20:
        return 0.0
    ml_v = float(np.median(f[ml]))
    mr_v = float(np.median(f[mr]))
    return (mr_v - ml_v) / max(ml_v, 1e-6)


def main() -> int:
    t0 = time.time()
    FOLLOW_DIR.mkdir(parents=True, exist_ok=True)
    triggers = load_csv(RES / "N14_STAGE2_TRIGGERS.csv")
    diags = load_csv(RES / "N14_PEAK_DIAGNOSTICS.csv")
    stars_rows = load_csv(RES / "N14_STAR_SUMMARY.csv")
    epochs = load_csv(INP / "n14_epoch_receipts.csv")

    star_meta = {r["star"]: {"ra": float(r["ra_deg"]), "dec": float(r["dec_deg"]), "sp_type": r["sp_type"], "dist_pc": float(r["dist_pc"])} for r in stars_rows}
    ep_map = {(r["star"], r["dp_id"]): r for r in epochs}
    by_star_ep: dict[str, list[dict[str, str]]] = {}
    star_med_ha: dict[str, float] = {}
    star_med_hb: dict[str, float] = {}
    for r in epochs:
        by_star_ep.setdefault(r["star"], []).append(r)
    for st, eps in by_star_ep.items():
        star_med_ha[st] = float(np.median([float(e["ha_ratio"]) for e in eps]))
        star_med_hb[st] = float(np.median([float(e["hb_ratio"]) for e in eps]))

    # Cross-star topocentric coincidences across all 5,472 Z>=10 peaks
    diag_stars = np.array([d["star"] for d in diags], dtype=object)
    diag_lt = np.array([float(d["lam_bary_a"]) / (1.0 + (float(d["berv_kms"]) if d["berv_kms"] else 0.0) / C_KMS) for d in diags], dtype=np.float64)

    # Pre-scan triggers + peaks per exposure against canonical Ar I / Th I calibration lamp lines
    thar_hits_by_exp: dict[tuple[str, str], set[str]] = {}
    for row in triggers + diags:
        lb = float(row["lam_bary_a"])
        bv = float(row["berv_kms"]) if row["berv_kms"] else 0.0
        lt = lb / (1.0 + bv / C_KMS)
        key = (row["star"], row["dp_id"])
        for tname, tlam in THAR_LINES_A.items():
            if abs(lt - tlam) <= 0.08:
                thar_hits_by_exp.setdefault(key, set()).add(tname)
    thar_contaminated_exps = {k: sorted(v) for k, v in thar_hits_by_exp.items() if len(v) >= 2}

    # Pass 1: Fast local physics triage (ThAr, Terrestrial Airglow/Telluric, WAVE-bleed, Flare)
    pre_vetted: list[dict[str, object] | None] = [None] * len(triggers)
    need_followup: list[int] = []
    for idx, tr in enumerate(triggers):
        star = tr["star"]
        ch = tr["channel"]
        dp_id = tr["dp_id"]
        lb = float(tr["lam_bary_a"])
        bv = float(tr["berv_kms"]) if tr["berv_kms"] else 0.0
        lt = float(tr["lam_topo_a"]) if tr.get("lam_topo_a") else (lb / (1.0 + bv / C_KMS))
        emeta = ep_map[(star, dp_id)]
        dpr = emeta.get("dpr_type", "")
        ha_r = float(tr.get("ha_ratio") or emeta.get("ha_ratio") or 1.0)
        hb_r = float(tr.get("hb_ratio") or emeta.get("hb_ratio") or 1.0)
        d_ha = ha_r - star_med_ha[star]
        d_hb = hb_r - star_med_hb[star]

        if (star, dp_id) in thar_contaminated_exps:
            pre_vetted[idx] = (
                "MISLABELED_THAR_LAMP_CONTAMINATED_EXPOSURE",
                "FALSE_POSITIVE_INSTRUMENTAL_THAR",
                f"dpr={dpr}, matched_ThAr={thar_contaminated_exps[(star, dp_id)]}",
            )
            continue

        if ch == "T2_OPTICAL_COMB":
            teeth_str = tr.get("comb_teeth", "")
            teeth_lams = [float(x.split("@")[0]) for x in teeth_str.split(";") if "@" in x]
            if ha_r >= 2.2 or hb_r >= 2.2 or d_ha >= 0.35 or d_hb >= 0.45:
                pre_vetted[idx] = (
                    "CHROMOSPHERIC_FLARE_COMB",
                    "FALSE_POSITIVE_STELLAR_FLARE",
                    f"Ha={ha_r:.2f}(+{d_ha:.2f}), Hb={hb_r:.2f}(+{d_hb:.2f}), teeth={len(teeth_lams)}",
                )
            elif "WAVE" in dpr.upper():
                pre_vetted[idx] = (
                    "SIMCAL_FIBER_B_WAVE_BLEED_COMB",
                    "FALSE_POSITIVE_INSTRUMENTAL",
                    f"dpr={dpr}, teeth={len(teeth_lams)}",
                )
            else:
                need_followup.append(idx)
        else:
            sky_hit = [k for k, v in SKY_LINES_A.items() if abs(lt - v) <= 0.18]
            cross_count = int(np.sum((diag_stars != star) & (np.abs(diag_lt - lt) <= 0.08)))
            in_telluric = (5880.0 <= lt <= 5960.0) or (6275.0 <= lt <= 6325.0) or (6465.0 <= lt <= 6595.0) or (6845.0 <= lt <= 6900.0)
            if sky_hit or cross_count > 0 or in_telluric:
                pre_vetted[idx] = (
                    "TERRESTRIAL_AIRGLOW_OR_TELLURIC",
                    "FALSE_POSITIVE_ATMOSPHERIC",
                    f"sky={sky_hit}, cross={cross_count}, telluric={in_telluric}, lam_topo={lt:.3f}",
                )
            elif "WAVE" in dpr.upper():
                pre_vetted[idx] = (
                    "SIMCAL_FIBER_B_WAVE_BLEED",
                    "FALSE_POSITIVE_INSTRUMENTAL",
                    f"dpr={dpr}",
                )
            elif ha_r >= 2.2 or hb_r >= 2.2 or d_ha >= 0.35 or d_hb >= 0.45:
                pre_vetted[idx] = (
                    "CHROMOSPHERIC_STELLAR_FLARE",
                    "FALSE_POSITIVE_STELLAR_FLARE",
                    f"Ha={ha_r:.2f}(+{d_ha:.2f}), Hb={hb_r:.2f}(+{d_hb:.2f})",
                )
            else:
                need_followup.append(idx)

    print(f"[N14 Stage 3] Fast triage done: {len(triggers) - len(need_followup)} vetoed locally, {len(need_followup)} queued for live ESO/RV follow-up.")

    # Pass 2: Parallel TAP + FITS cache for unresolved triggers
    unique_tap_keys = sorted({(triggers[i]["star"], triggers[i]["dp_id"], float(triggers[i]["mjd_obs"])) for i in need_followup})
    tap_cache: dict[tuple[str, str], list[dict[str, object]]] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {
            ex.submit(query_adjacent_harps, st, star_meta[st]["ra"], star_meta[st]["dec"], dp, mjd): (st, dp)
            for st, dp, mjd in unique_tap_keys
        }
        for fut in as_completed(futs):
            tap_cache[futs[fut]] = fut.result()

    # Determine which FITS need downloading: trigger dp_ids (for CCF RVC), up to 3 clean refs per needed star, up to 2 adj cands
    dl_jobs: set[tuple[str, str]] = set()
    ref_dp_by_star: dict[str, list[str]] = {}
    for idx in need_followup:
        tr = triggers[idx]
        st = tr["star"]
        dp = tr["dp_id"]
        dl_jobs.add((st, dp))
        if st not in ref_dp_by_star:
            # Prefer STAR,DARK / STAR,SKY over STAR,WAVE when picking reference epochs
            cands_ref = sorted(
                by_star_ep[st],
                key=lambda e: (1 if "WAVE" in e.get("dpr_type", "").upper() else 0, -float(e.get("snr_hdr") or 0.0)),
            )
            ref_dp_by_star[st] = [e["dp_id"] for e in cands_ref if e["dp_id"] != dp][:3]
        for rdp in ref_dp_by_star[st]:
            if rdp != dp:
                dl_jobs.add((st, rdp))
        cands = tap_cache[(st, dp)]
        max_adj = 1 if tr["channel"] == "T2_OPTICAL_COMB" else 2
        for cd in cands[:max_adj]:
            dl_jobs.add((st, str(cd["dp_id"])))

    print(f"[N14 Stage 3] Caching {len(dl_jobs)} FITS into {FOLLOW_DIR} ...")
    wf_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray, float | None, float, str]] = {}

    def _fetch_and_load(job: tuple[str, str]) -> tuple[tuple[str, str], tuple[np.ndarray, np.ndarray, float | None, float, str] | None]:
        st, dp = job
        try:
            p = download_fits(st, dp)
            return job, read_fits_wf_rv(p)
        except Exception:
            return job, None

    with ThreadPoolExecutor(max_workers=6) as ex:
        for job, val in ex.map(_fetch_and_load, sorted(dl_jobs)):
            if val is not None:
                wf_cache[job] = val

    # Pass 3: Resolve each remaining trigger cleanly
    for idx in need_followup:
        tr = triggers[idx]
        star = tr["star"]
        ch = tr["channel"]
        dp_id = tr["dp_id"]
        lb = float(tr["lam_bary_a"])
        mjd = float(tr["mjd_obs"])
        ha_r = float(tr.get("ha_ratio") or 1.0)
        hb_r = float(tr.get("hb_ratio") or 1.0)

        trig_dat = wf_cache.get((star, dp_id))
        rv_kms = trig_dat[2] if trig_dat is not None else None
        trig_res = trig_dat[3] if trig_dat is not None else 115000.0
        trig_mode = trig_dat[4] if trig_dat is not None else "HARPS"
        all_ref_dats = [wf_cache[(star, rdp)] for rdp in ref_dp_by_star.get(star, []) if rdp != dp_id and (star, rdp) in wf_cache]
        same_res_refs = [rd for rd in all_ref_dats if abs(rd[3] - trig_res) < 5000.0]
        ref_dats = same_res_refs if same_res_refs else all_ref_dats
        ref_wfs = [(rd[0], rd[1]) for rd in ref_dats]
        ref_med_res = float(np.median([rd[3] for rd in all_ref_dats])) if all_ref_dats else 115000.0

        # Instrument mode / resolving power mismatch (e.g. HARPS EGGS R=80,000 vs HAM R=115,000)
        if abs(trig_res - ref_med_res) >= 10000.0:
            pre_vetted[idx] = (
                "INSTRUMENT_MODE_RESOLUTION_MISMATCH",
                "FALSE_POSITIVE_INSTRUMENTAL_MODE",
                f"mode={trig_mode}(R={trig_res:.0f}) vs ref_R={ref_med_res:.0f}",
            )
            continue

        if ch == "T2_OPTICAL_COMB":
            teeth_str = tr.get("comb_teeth", "")
            teeth_lams = [float(x.split("@")[0]) for x in teeth_str.split(";") if "@" in x]
            cands = tap_cache.get((star, dp_id), [])
            rep_count = 0
            checked_f = False
            detail = ""
            for cd in cands[:1]:
                fdp = str(cd["dp_id"])
                if (star, fdp) not in wf_cache or not ref_wfs:
                    continue
                checked_f = True
                fol_wf = (wf_cache[(star, fdp)][0], wf_cache[(star, fdp)][1])
                z_teeth: list[float] = []
                for tlam in teeth_lams:
                    try:
                        zf, _s, _ex, _pk = compute_followup_metrics(tlam, fol_wf, ref_wfs)
                        z_teeth.append(zf)
                        if zf >= 4.0:
                            rep_count += 1
                    except Exception:
                        pass
                detail = f"adj_dp={fdp}, rep_teeth={rep_count}/{len(teeth_lams)}, max_Z={max(z_teeth) if z_teeth else 0:.2f}"
            if checked_f and rep_count == 0:
                pre_vetted[idx] = ("NONREPEATING_COMB_NOISE_EXCURSION", "FALSE_POSITIVE_COSMIC_OR_NOISE", detail)
            elif checked_f and rep_count >= 2:
                pre_vetted[idx] = ("UNRESOLVED_CORROBORATED_COMB", "UNRESOLVED_ETI_CANDIDATE", detail)
            elif checked_f:
                pre_vetted[idx] = ("AMBIGUOUS_SINGLE_TOOTH_FOLLOWUP", "FALSE_POSITIVE_COSMIC_OR_NOISE", detail)
            else:
                max_other_rep = 0
                for o_wf in ref_wfs:
                    other_refs = [rw for rw in ref_wfs if rw is not o_wf]
                    if not other_refs:
                        continue
                    c_rep = 0
                    for tlam in teeth_lams:
                        try:
                            zf, _, _, _ = compute_followup_metrics(tlam, o_wf, other_refs)
                            if zf >= 4.0:
                                c_rep += 1
                        except Exception:
                            pass
                    max_other_rep = max(max_other_rep, c_rep)
                pre_vetted[idx] = (
                    "ISOLATED_UNCORROBORATED_COMB_EXCURSION" if max_other_rep <= 1 else "UNRESOLVED_MULTI_EPOCH_COMB",
                    "FALSE_POSITIVE_COSMIC_OR_NOISE" if max_other_rep <= 1 else "UNRESOLVED_ETI_CANDIDATE",
                    f"no_eso_adj_1.5d, teeth={len(teeth_lams)}, other_cube_rep={max_other_rep}",
                )
        else:
            # Check stellar-rest chromospheric emission lines if RV known
            ch_hit: list[str] = []
            if rv_kms is not None:
                l_star = lb / (1.0 + rv_kms / C_KMS)
                ch_hit = [k for k, v in CHROMOSPHERIC_LINES_A.items() if abs(l_star - v) <= 0.40]
            if ch_hit:
                pre_vetted[idx] = (
                    "CHROMOSPHERIC_STELLAR_FLARE",
                    "FALSE_POSITIVE_STELLAR_FLARE",
                    f"lines={ch_hit}, rv={rv_kms:.2f}, Ha={ha_r:.2f}, Hb={hb_r:.2f}",
                )
                continue

            # Check echelle order-overlap discontinuous continuum step artifact (e.g. HARPS_3.8 order merge step)
            if trig_dat is not None and ref_wfs:
                t_step = measure_continuum_step(lb, trig_dat[0], trig_dat[1])
                r_step = float(np.median([measure_continuum_step(lb, rw[0], rw[1]) for rw in ref_wfs]))
                if abs(t_step) >= 0.05 and abs(t_step - r_step) >= 0.05:
                    pre_vetted[idx] = (
                        "ECHELLE_ORDER_STITCH_STEP_ARTIFACT",
                        "FALSE_POSITIVE_INSTRUMENTAL_ORDER_EDGE",
                        f"order_step={t_step:+.4f} vs ref_step={r_step:+.4f}",
                    )
                    continue

            trig_ex = 0.0
            trig_pk = 1.0
            if trig_dat is not None and ref_wfs:
                _, _, trig_ex, trig_pk = compute_followup_metrics(lb, (trig_dat[0], trig_dat[1]), ref_wfs)

            cands = tap_cache.get((star, dp_id), [])
            checked_vals: list[tuple[str, float, float, float, float]] = []
            for cd in cands[:2]:
                fdp = str(cd["dp_id"])
                if (star, fdp) not in wf_cache or not ref_wfs:
                    continue
                try:
                    z_fol, _sig_fol, ex_fol, pk_fol = compute_followup_metrics(lb, (wf_cache[(star, fdp)][0], wf_cache[(star, fdp)][1]), ref_wfs)
                    checked_vals.append((fdp, float(cd["dt_hours"]), z_fol, ex_fol, pk_fol))
                except Exception:
                    continue

            if checked_vals:
                z_best = min(v[2] for v in checked_vals)
                z_max_f = max(v[2] for v in checked_vals)
                _dp0, _dt0, z0, ex0, pk0 = checked_vals[0]
                amp_ratio = ex0 / max(trig_ex, 1e-6) if trig_ex > 0 else 1.0
                summary_f = ", ".join(f"{d}(dt={t:.2f}h,Z={z:.2f},ex={ex:+.3f},pk={pk:.3f})" for d, t, z, ex, pk in checked_vals)
                if z0 < 3.5 or z_best < 3.0 or (z0 < 5.0 and amp_ratio < 0.45):
                    pre_vetted[idx] = (
                        "SINGLE_EXPOSURE_COSMIC_RAY_NONREPEATING",
                        "FALSE_POSITIVE_COSMIC_RAY",
                        f"amp_ratio={amp_ratio:.3f}, {summary_f}",
                    )
                elif amp_ratio < 0.25 and ex0 < 0.08:
                    pre_vetted[idx] = (
                        "SINGLE_EXPOSURE_SPIKE_DECAYED_NONREPEATING",
                        "FALSE_POSITIVE_COSMIC_RAY",
                        f"trig_ex={trig_ex:+.3f}->adj_ex={ex0:+.3f} (amp_ratio={amp_ratio:.3f}), {summary_f}",
                    )
                elif z_max_f >= 5.0 and z0 >= 5.0:
                    pre_vetted[idx] = ("UNRESOLVED_CORROBORATED_TRANSIENT", "UNRESOLVED_ETI_CANDIDATE", f"CORROBORATED {summary_f}")
                else:
                    pre_vetted[idx] = ("AMBIGUOUS_FOLLOWUP_CHECK", "UNRESOLVED_ETI_CANDIDATE", summary_f)
            else:
                same_star = [x for x in by_star_ep[star] if x["dp_id"] != dp_id]
                same_star.sort(key=lambda x: abs(float(x["mjd_obs"]) - mjd))
                nearest = same_star[0]
                pre_vetted[idx] = (
                    "ISOLATED_SINGLE_EXP_COSMIC_RAY_UNCORROBORATED",
                    "FALSE_POSITIVE_COSMIC_RAY",
                    f"no_eso_adj_1.5d; 1_of_8_epochs_only; nearest_cube_dt={abs(float(nearest['mjd_obs']) - mjd):.1f}d",
                )

    vetted: list[dict[str, object]] = []
    counts_by_veto: dict[str, int] = {}
    for idx, tr in enumerate(triggers):
        res_t = pre_vetted[idx]
        assert res_t is not None
        veto_reason, eti_status, detail = res_t
        counts_by_veto[veto_reason] = counts_by_veto.get(veto_reason, 0) + 1
        vetted.append({
            **tr,
            "veto_reason": veto_reason,
            "eti_status": eti_status,
            "forensic_detail": detail,
        })

    base_cols = list(triggers[0].keys()) if triggers else []
    cols = base_cols + ["veto_reason", "eti_status", "forensic_detail"]
    with (RES / "N14_CANDIDATES_VETTED.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(vetted)

    diag_counts: dict[str, int] = {}
    for d in diags:
        st = d["stage2_status"]
        diag_counts[st] = diag_counts.get(st, 0) + 1

    verified_eti = sum(1 for v in vetted if v["eti_status"] == "UNRESOLVED_ETI_CANDIDATE")
    summary = {
        "campaign": "SPOR_N14_300STAR_HARPS_TRANSIENT_LASER_AND_COMB",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - t0, 2),
        "peaks_z10_before_shape_veto": len(diags),
        "stage2_diag_breakdown": diag_counts,
        "stage2_triggers_vetted": len(vetted),
        "followup_fits_cached": len(wf_cache),
        "veto_breakdown": counts_by_veto,
        "verified_eti_candidates": verified_eti,
        "external_contacts": 0,
    }
    (RES / "N14_STAGE3_VETTING.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[N14 Stage 3 Complete] Vetted {len(vetted)} triggers -> {verified_eti} verified ETI in {summary['elapsed_s']}s")
    print(json.dumps(counts_by_veto, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
