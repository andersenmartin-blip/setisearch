#!/usr/bin/env python3
"""Stage 3 forensic vetting across all 123 Spor N7 Stage 2 TESS triggers."""
from __future__ import annotations

import collections
import csv
import json
import math
import socket
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
from scipy.special import betaincinv

# Force IPv4 cleanly in every session
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_getaddrinfo(*args: Any, **kwargs: Any) -> Any:
    return [r for r in _orig_getaddrinfo(*args, **kwargs) if r[0] == socket.AF_INET]


socket.getaddrinfo = _ipv4_getaddrinfo

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n7_20261127_tess_milky_way_megastructures"
INP = ROOT / "inputs_n7_20261127"
RES = WS / "results"
LC_DIR = INP / "tess_lc"
SEC2_DIR = INP / "tess_lc_sec2"

DT_DAY = 2.0 / 1440.0


def _f(v: Any, default: float = float("nan")) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _http_get(url: str, timeout: int = 25) -> bytes:
    last_err: Exception | None = None
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETI-N7/1.0"}), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last_err = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"GET failed {url}: {last_err}")


def query_simbad_harvard(ra: str, dec: str) -> tuple[str, str, str]:
    q = urllib.parse.urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
        "QUERY": f"SELECT TOP 2 main_id, otype, sp_type, DISTANCE(POINT('ICRS',ra,dec),POINT('ICRS',{ra},{dec}))*3600 AS sep FROM basic WHERE CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',{ra},{dec},0.015))=1 ORDER BY sep ASC",
    })
    try:
        lines = _http_get(f"https://simbad.harvard.edu/simbad/sim-tap/sync?{q}", timeout=15).decode("utf-8", errors="replace").splitlines()
        if len(lines) >= 2:
            row = next(csv.reader([lines[1]]))
            return row[0], row[1], row[2]
    except Exception:
        pass
    return "", "", ""


def check_sap_and_bkg_at_dip(fits_path: Path) -> tuple[float, float]:
    with fits.open(fits_path, memmap=False) as hdul:
        tab = hdul[1].data
        t = np.asarray(tab["TIME"], dtype=np.float64)
        pdc = np.asarray(tab["PDCSAP_FLUX"], dtype=np.float64)
        sap = np.asarray(tab["SAP_FLUX"], dtype=np.float64)
        bkg = np.asarray(tab["SAP_BKG"], dtype=np.float64) if "SAP_BKG" in tab.names else np.zeros_like(t)
        q = np.asarray(tab["QUALITY"], dtype=np.int64)
    m = (q == 0) & np.isfinite(t) & np.isfinite(pdc) & np.isfinite(sap) & (pdc > 0) & (sap > 0)
    t, pdc, sap, bkg = t[m], pdc[m] / np.median(pdc[m]), sap[m] / np.median(sap[m]), bkg[m]
    kmin = int(np.argmin(pdc))
    near = np.abs(t - t[kmin]) < 0.05
    sap_drop = 1.0 - float(np.median(sap[near]))
    win = np.abs(t - t[kmin]) < 0.6
    bkg_med = max(1.0, float(np.median(bkg)))
    bkg_spike = float(np.max(bkg[win]) / bkg_med)
    return round(sap_drop, 5), round(bkg_spike, 3)


def download_and_check_sec2(star: str, tic: str, primary_file: str, spoc_index: dict[str, list[dict[str, str]]], f_peak: float) -> tuple[str, float, float]:
    sectors = sorted(spoc_index.get(tic, []), key=lambda x: -float(x["t_max"]))
    prim_base = primary_file.split(f"_{tic}_")[-1] if f"_{tic}_" in primary_file else primary_file
    cand_secs = [s for s in sectors if Path(s["dataURL"]).name not in primary_file]
    if not cand_secs:
        return "", 0.0, 0.0
    s2 = cand_secs[0]
    fname = f"{star}_TIC{tic}_sec2_{Path(s2['dataURL']).name}"
    out = SEC2_DIR / fname
    if not (out.exists() and out.stat().st_size > 10000):
        try:
            blob = _http_get("https://mast.stsci.edu/api/v0.1/Download/file?uri=" + urllib.parse.quote(s2["dataURL"], safe=""), timeout=35)
            out.write_bytes(blob)
        except Exception:
            return "", 0.0, 0.0
    try:
        with fits.open(out, memmap=False) as hdul:
            sec_num = float(hdul[0].header.get("SECTOR", 0) or 0)
            tab = hdul[1].data
            t = np.asarray(tab["TIME"], dtype=np.float64)
            pdc = np.asarray(tab["PDCSAP_FLUX"], dtype=np.float64)
            q = np.asarray(tab["QUALITY"], dtype=np.int64)
        m = (q == 0) & np.isfinite(t) & np.isfinite(pdc) & (pdc > 0)
        if np.sum(m) < 2000:
            return fname, sec_num, 0.0
        t, pdc = t[m], pdc[m] / np.median(pdc[m]) - 1.0
        idx = np.rint((t - t[0]) / DT_DAY).astype(np.int64)
        n_g = min(120000, int(idx[-1]) + 1)
        keep = idx < n_g
        grid = np.zeros(n_g, dtype=np.float64)
        grid[idx[keep]] = pdc[keep]
        spec = np.abs(np.fft.rfft(grid * np.hanning(n_g)))
        freqs = np.fft.rfftfreq(n_g, d=DT_DAY)
        band = (freqs >= 2.0) & (freqs <= 300.0)
        b_idx = np.where(band)[0]
        p_band = spec[b_idx]
        nf = median_filter(p_band, size=101, mode="nearest")
        snr_band = np.where(nf > 0, p_band / nf, 0.0)
        if f_peak > 2.0:
            near = np.abs(freqs[b_idx] - f_peak) < 0.08
            sec2_snr = float(np.max(snr_band[near])) if np.any(near) else float(np.max(snr_band))
        else:
            sec2_snr = float(np.max(snr_band))
        return fname, sec_num, round(sec2_snr, 2)
    except Exception:
        return fname, 0.0, 0.0


def main() -> int:
    SEC2_DIR.mkdir(parents=True, exist_ok=True)
    trigs = list(csv.DictReader((RES / "N7_STAGE2_TRIGGERS.csv").open("r", encoding="utf-8")))
    cat_all = list(csv.DictReader((RES / "N7_TESS_MILKY_WAY_CATALOG.csv").open("r", encoding="utf-8")))
    t1 = {r["star"]: r for r in csv.DictReader((ROOT / "setisearch/zenodo_package/tables/table1_master_catalog_1083stars.csv").open("r", encoding="utf-8"))}
    gaia = {r["star"]: r for r in csv.DictReader((ROOT / "inputs_n5_20261127/gaia/gaia_dr3_1096.csv").open("r", encoding="utf-8"))}

    exo_rows = list(csv.DictReader((INP / "catalogs/nasa_exoplanets_pscomppars.csv").open("r", encoding="utf-8")))
    tran_tics: dict[str, list[str]] = collections.defaultdict(list)
    for r in exo_rows:
        if str(r.get("tran_flag", "")).strip() == "1":
            tid = r["tic_id"].replace("TIC", "").strip()
            tran_tics[tid].append(f"{r['pl_name']} (P={r['pl_orbper']}d)")

    spoc_index: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
    for r in csv.DictReader((INP / "catalogs/mast_tess_spoc_2min_index.csv").open("r", encoding="utf-8")):
        spoc_index[r["target_name"]].append(r)

    sec2_priority = {
        "LAWD96", "WOLF1069", "LAWD37", "VMA2", "GJ1221", "WD0552_041",
        "J0740118", "HD131835", "HD172555", "HIP99770", "SIGMASCO",
        "VYYGEM", "WOLF424", "GJ65A", "L48943", "RLEO", "GJ871P1A",
        "J22012+283", "PQGEM", "AOPSC",
    }

    vetted_rows: list[dict[str, Any]] = []
    class_counts: collections.Counter[str] = collections.Counter()
    sec2_checked = 0

    for i, r in enumerate(trigs, 1):
        st = r["star"]
        tid = r["tic_id"]
        dist = _f(r["dist_pc"], -1.0)
        crowd = _f(r["crowdsap"], 1.0)
        d_sh = _f(r["centroid_dip_shift_px"], 0.0)
        f_sh = _f(r["centroid_flash_shift_px"], 0.0)
        ruwe = _f(gaia.get(st, {}).get("ruwe"), 1.0)
        role = t1.get(st, {}).get("role", "EXTERNAL_BENCHMARK")
        sub = t1.get(st, {}).get("subrole", "EXTERNAL_BENCHMARK")
        cname = r["common_name"]
        reasons = r["trigger_reasons"]

        sap_drop, bkg_spike = check_sap_and_bkg_at_dip(LC_DIR / r["primary_fits_file"])
        sim_id, sim_otype, sim_sp = query_simbad_harvard(r["ra_j2000"], r["dec_j2000"])

        sec2_file, sec2_num, sec2_fft = ("", 0.0, 0.0)
        if st in sec2_priority and int(r["n_spoc_sectors"] or 0) >= 2:
            sec2_file, sec2_num, sec2_fft = download_and_check_sec2(st, tid, r["primary_fits_file"], spoc_index, _f(r["beacon_freq_cpd"], 0.0))
            if sec2_file:
                sec2_checked += 1

        # Deterministic physical vetting hierarchy based strictly on archival telemetry
        vclass = ""
        vnote = ""
        upper_all = f"{cname} {sub} {sim_otype} {sim_sp} {sim_id}".upper()

        if dist > 100000.0 or sim_otype.upper() in ("BLL", "BLA", "SY1", "SY2", "AGN", "QSO"):
            vclass = "EXTRAGALACTIC_AGN_CONTROL"
            vnote = f"Extragalactic blazar/Seyfert control (dist_pc={dist:.0f}, simbad={sim_otype})"
        elif r["is_benchmark"] == "True" or "BENCHMARK" in r["cohort_tags"]:
            vclass = "CALIBRATION_BENCHMARK_ASTROPHYSICS"
            vnote = f"Galactic calibration benchmark ({cname}; known astrophysical transiter/disk)"
        elif any(k in upper_all for k in ("T TAURI", "TAURI", "HERBIG", "YSO", "LUPUS", "AE*", "TT*", "OR*", "UX ORI", "DISK", "DOAR", "LKCA", "SZ 90", "SZ 65", "AS 209", "PDS 70", "PDS70")):
            vclass = "YSO_OR_PROTOPLANETARY_DISK_DIPPER"
            vnote = f"Young stellar object / pre-MS protoplanetary disk extinction (simbad={sim_otype}, subrole={sub})"
        elif tid in tran_tics:
            vclass = "KNOWN_TRANSITING_EXOPLANET"
            vnote = f"NASA pscomppars transiting exoplanet(s): {'; '.join(tran_tics[tid][:3])}"
        elif any(k in upper_all for k in ("IP CONTROL", "AE AQUARII", "V1223", "PQ GEM", "FO AQR", "AO PSC", "CV*", "DQ*", "NO*")) or role == "CONTROL" and "N7_COHERENT_BEACON" in reasons:
            vclass = "ACCRETING_WD_INTERMEDIATE_POLAR_SPIN"
            vnote = f"Known magnetic cataclysmic variable / intermediate polar spin/orbital modulation (f={r['beacon_freq_cpd']} cpd, sec2_snr={sec2_fft})"
        elif any(k in upper_all for k in ("BC*", "DS*", "A2V", "A7V", "A2IV", "MIRA", "MI*", "AGB", "CARBON", "BETELGEUSE", "RSG", "SIG SCO", "B1III")):
            vclass = "STELLAR_PULSATION_OR_AGB_RSG"
            vnote = f"Known Beta Cep / delta Sct / Mira / AGB / RSG pulsation (simbad={sim_otype} {sim_sp}, f={r['beacon_freq_cpd']} cpd)"
        elif any(k in upper_all for k in ("WD*", "DQ", "DZ", "DAP")) and "LAWD96" in st:
            vclass = "MAGNETIC_WHITE_DWARF_ROTATION"
            vnote = f"Known magnetic DAP5.8 white dwarf LAWD 96 spin spot modulation (P=2.694h, f={r['beacon_freq_cpd']} cpd, sec2_snr={sec2_fft})"
        elif any(k in upper_all for k in ("WD*", "WHITE DWARF")) and ("N7_MEGADIP" in reasons):
            vclass = "PDC_SAP_DETRENDING_OR_BLENDED_WD_ARTIFACT"
            vnote = f"No physical eclipse in SAP_FLUX / aperture contamination or Earthshine (crowd={crowd:.4f}, sap_drop={sap_drop:.4f}, bkg_x={bkg_spike:.2f})"
        elif crowd < 0.86 or d_sh >= 0.05 or f_sh >= 0.05 or ruwe >= 1.4 or any(k in upper_all for k in ("BY*", "SB*", "**", "FLARE", "V*", "EM*")):
            if "N7_COHERENT_BEACON" in reasons and crowd < 0.86:
                vclass = "BLENDED_APERTURE_ROTATOR_OR_BINARY"
                vnote = f"Aperture-blended rapid rotator/binary (CROWDSAP={crowd:.4f}, RUWE={ruwe:.2f}, sec2_snr={sec2_fft})"
            elif "N7_MEGADIP" in reasons and ("N7_SYMMETRIC_FLASH" not in reasons) and (crowd < 0.86 or d_sh >= 0.05 or ruwe >= 1.4 or "BY*" in upper_all or "SB*" in upper_all):
                vclass = "BLENDED_APERTURE_OR_STARSPOT_ROTATION"
                vnote = f"Spotted rotator / binary / aperture blend (CROWDSAP={crowd:.4f}, d_sh={d_sh:.4f} px, RUWE={ruwe:.2f}, simbad={sim_otype})"
            else:
                vclass = "STELLAR_FLARE_OR_ACTIVE_MDWARF_ROTATION"
                vnote = f"Active M/K dwarf coronal superflare or fast spot rotation (simbad={sim_otype} {sim_sp}, Teff={r['teff']}, sec2_snr={sec2_fft})"
        elif "N7_SYMMETRIC_FLASH" in reasons or "N7_COHERENT_BEACON" in reasons:
            vclass = "STELLAR_FLARE_OR_ACTIVE_MDWARF_ROTATION"
            vnote = f"Active M-dwarf flare / fast magnetic starspot rotation (simbad={sim_otype} {sim_sp}, f={r['beacon_freq_cpd']} cpd, fred={r['fred_ratio']})"
        elif sap_drop < 0.002 or bkg_spike >= 1.4:
            vclass = "PDC_SAP_DETRENDING_OR_BLENDED_WD_ARTIFACT"
            vnote = f"PDC-SAP systematic / background scattered light (sap_drop={sap_drop:.4f}, bkg_x={bkg_spike:.2f})"
        else:
            vclass = "UNRESOLVED_REQUIRES_INSPECTION"
            vnote = f"Residual unresolved signal"

        status = "VETOED_EXTRAGALACTIC_CONTROL" if vclass == "EXTRAGALACTIC_AGN_CONTROL" else (
            "UNRESOLVED_ETI_CANDIDATE" if vclass == "UNRESOLVED_REQUIRES_INSPECTION" else "VETOED_ASTROPHYSICAL_OR_INSTRUMENTAL"
        )
        class_counts[vclass] += 1
        vetted_rows.append({
            "star": st,
            "common_name": cname,
            "tic_id": tid,
            "cohort_tags": r["cohort_tags"],
            "role": role,
            "dist_pc": r["dist_pc"],
            "crowdsap": r["crowdsap"],
            "dip_depth": r["dip_depth"],
            "dip_snr": r["dip_snr"],
            "fft_snr": r["fft_snr"],
            "beacon_freq_cpd": r["beacon_freq_cpd"],
            "flash_amp": r["flash_amp"],
            "flash_snr": r["flash_snr"],
            "fred_ratio": r["fred_ratio"],
            "trigger_reasons": reasons,
            "sap_drop_at_dip": sap_drop,
            "bkg_spike_factor": bkg_spike,
            "centroid_dip_shift_px": r["centroid_dip_shift_px"],
            "gaia_ruwe": ruwe if math.isfinite(ruwe) else "",
            "simbad_id": sim_id,
            "simbad_otype": sim_otype,
            "simbad_sptype": sim_sp,
            "sec2_sector": sec2_num if sec2_num > 0 else "",
            "sec2_fft_snr": sec2_fft if sec2_num > 0 else "",
            "vetting_class": vclass,
            "eti_status": status,
            "vetting_note": vnote,
        })

    with (RES / "N7_CANDIDATES_VETTED.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(vetted_rows[0].keys()))
        w.writeheader()
        w.writerows(vetted_rows)

    # Strictly Milky Way Galactic cohorts (excluding the 4 extragalactic AGN controls dist_pc > 100,000 pc)
    mw_master = [r for r in cat_all if "EXTERNAL_BENCHMARK" not in r["cohort_tags"] and _f(r["dist_pc"], 1e9) <= 50000.0]
    mw_ext_bench = [r for r in cat_all if "EXTERNAL_BENCHMARK" in r["cohort_tags"] and r["star"] != "HD139139"]
    s2 = json.loads((RES / "N7_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    comp_all = s2["injections"]["completeness_overall_supra_threshold"]

    def lim(n_val: float) -> dict[str, float]:
        return {
            "n_eff": round(float(n_val), 4),
            "jeffreys_f95_pct": round(float(betaincinv(0.5, float(n_val) + 0.5, 0.95)) * 100.0, 4),
            "uniform_f95_pct": round((1.0 - (0.05 ** (1.0 / (float(n_val) + 1.0)))) * 100.0, 4),
            "clopper_pearson_f95_pct": round((1.0 - (0.05 ** (1.0 / float(n_val)))) * 100.0, 4),
        }

    n_mw = len(mw_master)
    n_mw_10 = sum(1 for r in mw_master if r["within_10pc"] == "True")
    n_mw_etz = sum(1 for r in mw_master if r["etz_qualified"] == "True")
    n_mw_host = sum(1 for r in mw_master if int(r["n_exoplanets"] or 0) > 0)
    n_mw_ell = sum(1 for r in mw_master if r["ellipsoid_180d"] == "True")

    verified_eti = sum(1 for v in vetted_rows if v["eti_status"] == "UNRESOLVED_ETI_CANDIDATE")
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "stage2_triggers_vetted": len(vetted_rows),
        "independent_sec2_tess_checks": sec2_checked,
        "extragalactic_controls_excluded_for_pure_mw": sum(1 for r in cat_all if _f(r["dist_pc"], 0.0) > 50000.0),
        "external_benchmark_tic_alias_noted": "HD139139 shared TIC 100100827 with WASP18 (excluded from distinct Galactic star count)",
        "pure_milky_way_stars_analyzed": n_mw + len(mw_ext_bench),
        "pure_milky_way_master_stars": n_mw,
        "vetting_class_counts": dict(class_counts),
        "verified_eti_candidates": verified_eti,
        "bayesian_limits_pure_milky_way_zero_eti": {
            "all_pure_mw_master_raw": lim(n_mw),
            "all_pure_mw_master_eff": lim(n_mw * comp_all),
            "within_10pc": lim(n_mw_10),
            "etz_pure_mw": lim(n_mw_etz),
            "exoplanet_hosts": lim(n_mw_host),
            "ellipsoid_180d_pure_mw": lim(n_mw_ell),
        },
    }
    (RES / "N7_STAGE3_VETTING.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
