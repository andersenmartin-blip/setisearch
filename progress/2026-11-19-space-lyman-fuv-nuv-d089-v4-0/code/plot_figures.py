#!/usr/bin/env python3
"""
Generate the 4 publication-grade 220-DPI figures (fig31..fig34) for Phase D089:
  - fig31_d089_space_uv_gap_closure_and_coverage.png
  - fig32_d089_calibration_2697_and_fuse_dualchan.png
  - fig33_d089_panchromatic_26bridges_and_250star_limits.png
  - fig34_d089_allsky_comb_v41_284stacks_and_orbital80.png
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = Path(__file__).resolve().parent
RESULTS = WS / "results"
FIG_DIR = WS / "figures"


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.size": 9.8,
        "axes.titlesize": 10.8,
        "axes.labelsize": 10.0,
        "xtick.labelsize": 9.0,
        "ytick.labelsize": 9.0,
        "legend.fontsize": 8.0,
        "figure.dpi": 220,
    })

    summary = json.loads((RESULTS / "SUMMARY.json").read_text(encoding="utf-8"))
    diag = json.loads((RESULTS / "FORENSIC_D089_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    u250 = load_csv(RESULTS / "UNIFIED_PANCHROMATIC_V4_SYNTHESIS_250STARS.csv")
    br26 = load_csv(RESULTS / "PANCHROMATIC_BRIDGE_26STARS.csv")
    ul_rows = load_csv(RESULTS / "STAR_UPPER_LIMITS_D089.csv")
    allsky_u = load_csv(RESULTS / "ALLSKY_COMB_V4_1_UNIFIED_D079_D089.csv")
    comb_cal = load_csv(RESULTS / "COMB_V4_1_CALIBRATION_486.csv")
    inj = load_csv(RESULTS / "INJECTION_RECOVERY_1620.csv")
    kep = load_csv(RESULTS / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    g45 = load_csv(RESULTS / "DETECTOR_V40_G4G5_CALIBRATION_216.csv")
    g6 = load_csv(RESULTS / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    orb_rows = load_csv(RESULTS / "ORBITAL_CAMPAIGN_RESULTS_10.csv")

    inst_cols = {"FUSE_FUV": "#6a3d9a", "HST_COS_FUV": "#1f78b4", "HST_STIS_NUV": "#e31a1c"}

    # ---------------- Fig 31: 14-Spectrograph (16-Arm) Unbroken 4.797-Octave Coverage + D089 UV Limits ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.4, 6.2), constrained_layout=True)

    arms = [
        ("FUSE FUV (Space)", 0.0905, 0.1187, "#6a3d9a", "R=20k [D089 NEW <0.1um]"),
        ("HST COS G130M (Space)", 0.1125, 0.1450, "#1f78b4", "R=18k [D089 NEW]"),
        ("HST STIS E140M (Space)", 0.1145, 0.1710, "#4e79a7", "R=45.8k [D087]"),
        ("HST STIS NUV E230M/H", 0.1605, 0.3150, "#e31a1c", "R=30k/114k [D089 NEW: Closes UV Gap]"),
        ("VLT UVES NUV (Paranal)", 0.305, 0.456, "#59a14f", "R=41k-71k [D086]"),
        ("CFHT ESPaDOnS (Maunakea)", 0.370, 1.048, "#b15928", "R=65k-80k [D088]"),
        ("HARPS / HARPS-N", 0.378, 0.691, "#76b7b2", "R=115k [D079-D086]"),
        ("ESPRESSO HR/UHR", 0.379, 0.786, "#2c7fb8", "R=140k/190k [D080-D087]"),
        ("OHP SOPHIE / ELODIE", 0.387, 0.694, "#8c564b", "R=42k-75k [D088]"),
        ("CARMENES_VIS (CAHA)", 0.520, 0.960, "#edc948", "R=94.6k [D084]"),
        ("VLT UVES RED (Paranal)", 0.5655, 1.0425, "#e15759", "R=42k-107k [D087]"),
        ("NIRPS_HE (La Silla)", 0.980, 1.800, "#f28e2b", "R=70k [D082]"),
        ("CFHT SPIRou (Maunakea)", 0.955, 2.515, "#b07aa1", "R=70k [D085]"),
        ("VLT CRIRES+ K (Paranal)", 1.960, 2.480, "#9c755f", "R=86k [D083]"),
    ]
    ax1.axvspan(0.1710, 0.3050, color="#fde0dd", alpha=0.55, label="Prior 0.171-0.305 um UV gap (now 100% closed)")
    ax1.axvline(0.100, color="#6a3d9a", linestyle="--", linewidth=0.9, alpha=0.75)
    for yi, (lbl, w0, w1, col, note) in enumerate(arms):
        ax1.barh(yi, w1 - w0, left=w0, height=0.62, color=col, edgecolor="#222", linewidth=0.65, alpha=0.92)
        if w1 < 1.2:
            ax1.text(w1 * 1.05, yi, note, va="center", ha="left", fontsize=7.4, color="#111")
        else:
            ax1.text(w0 * 0.94, yi, note, va="center", ha="right", fontsize=7.4, color="#111")
    ax1.set_xscale("log")
    ax1.set_xlim(0.080, 3.6)
    ax1.set_yticks(range(len(arms)))
    ax1.set_yticklabels([a[0] for a in arms], fontsize=8.3)
    ax1.invert_yaxis()
    ax1.set_xlabel("Barycentric Vacuum/Standard Wavelength (um, log scale)")
    ax1.set_title("Unbroken 4.797-Octave Coverage: 0.0905-2.515 um (14 Spec / 16 Arms)")
    ax1.grid(True, axis="x", which="both", alpha=0.25)
    ax1.legend(loc="lower right", fontsize=7.8, framealpha=0.92)

    for inst in ("FUSE_FUV", "HST_COS_FUV", "HST_STIS_NUV"):
        sub = [r for r in ul_rows if r["instrument"] == inst]
        xs = [float(r["wave_bary_a"]) / 1e4 for r in sub]
        ys = [float(r["p_beam_10m_kw"]) for r in sub]
        ax2.scatter(xs, ys, s=34, color=inst_cols[inst], alpha=0.82, edgecolor="#111", linewidth=0.5, label=f"{inst} ({len(sub)} cells)")
    best_by_st = {}
    for r in ul_rows:
        st = r["star"]
        kw = float(r["p_beam_10m_kw"])
        if st not in best_by_st or kw < best_by_st[st][1]:
            best_by_st[st] = (float(r["wave_bary_a"]) / 1e4, kw, st)
    hl = [("ALPCENA", (8, -10)), ("EPSERI", (8, 8)), ("GJ832", (7, -8)), ("GJ876", (7, 8)), ("PROCYON", (-48, -10)), ("GJ667C", (-44, 10)), ("BETPIC", (7, -10))]
    for st, offs in hl:
        if st in best_by_st:
            x0, y0, lbl = best_by_st[st]
            ax2.annotate(lbl, (x0, y0), xytext=offs, textcoords="offset points", fontsize=7.6, fontweight="bold", arrowprops={"arrowstyle": "-", "lw": 0.6, "color": "#444"})
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Direct-FLAM Calibration Band Wavelength (um)")
    ax2.set_ylabel("8-sigma 10 m Laser Power Limit (kW)")
    ax2.set_title("D089 Direct-FLAM Space-UV Upper Limits (37 Stars, 0.096-0.295 um)")
    ax2.grid(True, which="both", alpha=0.24)
    ax2.legend(loc="upper left", framealpha=0.92)

    fig.savefig(FIG_DIR / "fig31_d089_space_uv_gap_closure_and_coverage.png", dpi=220)
    plt.close(fig)

    # ---------------- Fig 32: 2,697 Calibration Trials + FUSE Dual-Channel Coincidence ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.4), constrained_layout=True)

    sig_levels = sorted({float(r["sigma_mult"]) for r in inj})
    for inst in ("FUSE_FUV", "HST_COS_FUV", "HST_STIS_NUV"):
        for mode, ls in (("CHANNEL_T_TRANSIENT_1EPOCH", "-"), ("CHANNEL_P_PERSISTENT_COADD", "--")):
            sub = [r for r in inj if r["instrument"] == inst and r["mode"] == mode]
            ys = [np.mean([x["recovered"] == "True" for x in sub if abs(float(x["sigma_mult"]) - sv) < 1e-6]) * 100.0 for sv in sig_levels]
            ax1.plot(sig_levels, ys, marker="o", linestyle=ls, linewidth=1.8, color=inst_cols[inst], label=f"{inst} {'T' if 'CHANNEL_T' in mode else 'P'}")
    ax1.axvline(8.0, color="#222", linestyle=":", linewidth=1.0)
    ax1.set_xlabel("Injected Signal Amplitude (sigma_MAD)")
    ax1.set_ylabel("Recovery Rate (%)")
    ax1.set_ylim(-4, 106)
    ax1.set_title("1,620 Channel T & P Injection-Recovery Across Space-UV Arms")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="lower right", ncol=2, fontsize=7.6)

    k_td = np.mean([r["tdiff_uncomp_recovered"] == "True" for r in kep]) * 100.0
    k_kp = np.mean([r["kplanet_dedop_recovered"] == "True" for r in kep]) * 100.0
    g_tr = np.mean([r["g45_pass"] == "True" for r in g45 if r["trial_class"] == "TRUE_LSF_LASER"]) * 100.0
    g_cr = np.mean([r["g45_pass"] == "False" for r in g45 if r["trial_class"] == "COSMIC_RAY_HOT_PIXEL"]) * 100.0
    g_pl = np.mean([r["g45_pass"] == "False" for r in g45 if r["trial_class"] == "M_DWARF_PLATEAU_CORE"]) * 100.0
    fdc = diag["fuse_dual_channel_coincidence"]
    f_rej = (fdc["single_channel_vetoed_count"] / max(1, fdc["n_tested"])) * 100.0
    g6_t = np.mean([r["g6_v36_sparse_pass"] == "True" for r in g6 if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]) * 100.0
    g6_bg = np.mean([r["g6_v36_sparse_pass"] == "False" for r in g6 if r["trial_class"] != "TRUE_BARYCENTRIC_STELLAR_LASER"]) * 100.0
    c_rec = np.mean([r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]) * 100.0
    c_for4 = np.mean([r["comb_v4_hit"] == "True" for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]) * 100.0
    c_for41 = np.mean([r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]) * 100.0

    labels = ["Kep\nT_DIFF", "Kep\nK_PL", "G4/5\nTrue", "G4/5\nCR Rej", "G4/5\nPlat Rej", "FUSE\n1Ch Rej", "G6\nTrue", "G6\nGeo/Px", "Comb\n6-Tooth", "Forest\nV4 FPR", "Forest\nV4.1 FPR"]
    vals = [k_td, k_kp, g_tr, g_cr, g_pl, f_rej, g6_t, g6_bg, c_rec, c_for4, c_for41]
    cols = ["#aaa", "#2c7fb8", "#59a14f", "#59a14f", "#59a14f", "#6a3d9a", "#2b5c8f", "#2b5c8f", "#9467bd", "#e15759", "#2c7fb8"]
    bars = ax2.bar(range(len(labels)), vals, color=cols, edgecolor="#222", linewidth=0.6)
    for b_r, v in zip(bars, vals):
        ax2.text(b_r.get_x() + b_r.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=7.0)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=7.2)
    ax2.set_ylim(0, 114)
    ax2.set_ylabel("Rate (%)")
    ax2.set_title("Keplerian (135), G4_V40+G5 (216), G6 (240), & COMB_V4_1 (486)")
    ax2.grid(True, axis="y", alpha=0.25)

    fig.savefig(FIG_DIR / "fig32_d089_calibration_2697_and_fuse_dualchan.png", dpi=220)
    plt.close(fig)

    # ---------------- Fig 33: 250-Star / 121-<10pc Sensitivity Landscape + 26 Panchromatic Bridges ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 5.6), constrained_layout=True)

    d_all, p_all, d_10, p_10 = [], [], [], []
    for r in u250:
        if r.get("min_panchromatic_10m_kw"):
            dv, pv = float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"])
            if r["within_10pc"] == "True":
                d_10.append(dv)
                p_10.append(pv)
            else:
                d_all.append(dv)
                p_all.append(pv)
    ax1.scatter(d_all, p_all, s=18, color="#aab2bd", alpha=0.58, label=f"D079-D089 >10 pc (n={len(d_all)})")
    ax1.scatter(d_10, p_10, s=22, color="#2b5c8f", alpha=0.68, label="D079-D089 <10 pc (121 total)")

    best_d089: dict[str, tuple[float, float, str]] = {}
    for ur in ul_rows:
        st = ur["star"]
        kw = float(ur["p_beam_10m_kw"])
        dp_v = float(ur["dist_pc"])
        inst = ur["instrument"]
        if st not in best_d089 or kw < best_d089[st][1]:
            best_d089[st] = (dp_v, kw, inst)
    for inst in ("FUSE_FUV", "HST_COS_FUV", "HST_STIS_NUV"):
        pts = [(d, p) for s, (d, p, i) in best_d089.items() if i == inst]
        if pts:
            ax1.scatter([x[0] for x in pts], [x[1] for x in pts], s=48, color=inst_cols[inst], edgecolor="#111", linewidth=0.7, zorder=4, label=f"D089 {inst} (n={len(pts)})")

    for st, offs in [("ALPCENA", (7, -9)), ("GJ876", (7, -10)), ("GJ832", (-42, 8)), ("PROCYON", (8, -8)), ("TRAPPIST1", (-48, 8))]:
        if st in best_d089:
            ax1.annotate(st, (best_d089[st][0], best_d089[st][1]), xytext=offs, textcoords="offset points", fontsize=7.6, fontweight="bold")
    ax1.axvline(10.0, color="#555", linestyle="--", linewidth=0.9, alpha=0.75)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlabel("Distance (pc)")
    ax1.set_ylabel("Best 8-sigma 10 m CW Laser Power Limit (kW)")
    ax1.set_title("250-Star / 121-<10pc Panchromatic Sensitivity Landscape")
    ax1.grid(True, which="both", alpha=0.22)
    ax1.legend(loc="lower right", fontsize=7.6, framealpha=0.92)

    # Right panel: Panchromatic Bridge SED tracks across 26 bridges (highlighting D089 bridges)
    br_by_star: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in br26:
        br_by_star[r["star"]].append((float(r["wave_um"]), float(r["p_beam_10m_kw"])))
    for st, pts in br_by_star.items():
        pts_s = sorted(pts)
        if st not in ("BETPIC", "EPSERI", "GJ832", "GJ876", "55CNC", "HD189733", "HD209458", "PROXIMACEN"):
            ax2.plot([x[0] for x in pts_s], [x[1] for x in pts_s], color="#cbd5e1", linewidth=0.85, alpha=0.75, zorder=1)
    hl_bridges = [
        ("EPSERI", "#6a3d9a", "EPSERI (4-arm Lyman-NIR)"),
        ("BETPIC", "#d95f02", "BETPIC (4.77-oct Lyman-K)"),
        ("GJ832", "#1f78b4", "GJ832 (FUV+Optical <5pc)"),
        ("GJ876", "#17becf", "GJ876 (FUV+Optical <5pc)"),
        ("55CNC", "#e31a1c", "55CNC (NUV+Optical)"),
        ("HD209458", "#9467bd", "HD209458 (FUV+NUV+ESPRESSO)"),
        ("PROXIMACEN", "#2b5c8f", "PROXIMACEN (0.0973 W FUV)"),
    ]
    for st, col, lbl in hl_bridges:
        if st in br_by_star:
            pts_s = sorted(br_by_star[st])
            ax2.plot([x[0] for x in pts_s], [x[1] for x in pts_s], marker="o", markersize=3.8, linewidth=1.7, color=col, label=lbl, zorder=4)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Wavelength (um, log scale)")
    ax2.set_ylabel("8-sigma 10 m CW Laser Power Limit (kW)")
    ax2.set_title("26 Multi-Regime Panchromatic Bridges (0.0905-2.515 um)")
    ax2.grid(True, which="both", alpha=0.22)
    ax2.legend(loc="lower right", fontsize=7.4, framealpha=0.92)

    fig.savefig(FIG_DIR / "fig33_d089_panchromatic_26bridges_and_250star_limits.png", dpi=220)
    plt.close(fig)

    # ---------------- Fig 34: All-Sky COMB_V4_1 (284 Stacks / 1,759 Exp) + 10 Orbital Campaigns (#71-#80) ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.4, 5.5), constrained_layout=True)

    phases_order = [f"D0{k}" for k in range(79, 90)]
    v4_by_ph, v41_by_ph, exp_by_ph = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in allsky_u:
        ph = r["phase_id"]
        v4_by_ph[ph] += int(r["comb_v4_candidates"])
        v41_by_ph[ph] += int(r["comb_v41_candidates"])
        exp_by_ph[ph] += int(r["n_exposures"])
    x_ph = np.arange(len(phases_order))
    v4_vals = [v4_by_ph[p] for p in phases_order]
    v41_vals = [v41_by_ph[p] for p in phases_order]
    w_bar = 0.38
    b1 = ax1.bar(x_ph - w_bar / 2, v4_vals, width=w_bar, color="#f28e2b", edgecolor="#222", linewidth=0.6, label=f"COMB_V4 Automated ({sum(v4_vals)})")
    b2 = ax1.bar(x_ph + w_bar / 2, v41_vals, width=w_bar, color="#2c7fb8", edgecolor="#222", linewidth=0.6, label=f"COMB_V4_1 Automated ({sum(v41_vals)} -> 0 ETI)")
    ax1.set_yscale("symlog", linthresh=2.0)
    ax1.set_ylim(0, max(10, max(v4_vals)) * 2.2)
    for rect in b1:
        hv = int(rect.get_height())
        if hv > 0:
            ax1.text(rect.get_x() + rect.get_width() / 2, hv * 1.15 + 0.15, str(hv), ha="center", va="bottom", fontsize=7.0, color="#b35900")
    for rect in b2:
        hv = int(rect.get_height())
        if hv > 0:
            ax1.text(rect.get_x() + rect.get_width() / 2, hv * 1.15 + 0.15, str(hv), ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#1b4f72")
    ax1.set_xticks(x_ph)
    ax1.set_xticklabels([f"{p}\n({exp_by_ph[p]})" for p in phases_order], fontsize=7.6)
    ax1.set_ylabel("Automated Comb Candidates (symlog)")
    ax1.set_title("All-Sky COMB_V4_1 Sweep: 1,759 Exp / 284 Stacks (100% D079-D089)")
    ax1.grid(True, axis="y", alpha=0.25)
    ax1.legend(loc="upper left", framealpha=0.92)

    orb_sorted = sorted(orb_rows, key=lambda r: float(r["kp_kms"]))
    y_pos = np.arange(len(orb_sorted))
    for yi, r in enumerate(orb_sorted):
        kp = float(r["kp_kms"])
        dv = float(r["orbital_dv_span_kms"])
        is_ctrl = r["role"] == "CONTROL"
        c_main = "#888" if is_ctrl else "#1f78b4"
        ax2.barh(yi, kp, height=0.56, color=c_main, alpha=0.35, edgecolor=c_main, label="K_p" if yi == 0 else "")
        ax2.barh(yi, dv, height=0.32, color="#e31a1c" if not is_ctrl else "#555", edgecolor="#111", linewidth=0.5, label="IN_WINDOW dv span" if yi == 0 else "")
        ax2.text(max(kp, dv) + 2.0, yi, f"P={float(r['orbper_days']):.2f}d | {r['instrument'].replace('HST_','')} | 0 ETI", va="center", fontsize=7.4)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"{r['star']} ({'CTRL' if r['role']=='CONTROL' else 'SCI'})" for r in orb_sorted], fontsize=8.0)
    ax2.set_xlabel("Orbital Velocity Scale (km/s)")
    max_vel = max(max(float(r["kp_kms"]), float(r["orbital_dv_span_kms"])) for r in orb_sorted)
    ax2.set_xlim(0, max_vel * 1.46)
    ax2.set_title("10 D089 Orbital Campaigns (#71-#80 Cumulative) + 23/23 MM Closure")
    ax2.grid(True, axis="x", alpha=0.25)
    ax2.legend(loc="lower right", fontsize=7.8)

    fig.savefig(FIG_DIR / "fig34_d089_allsky_comb_v41_284stacks_and_orbital80.png", dpi=220)
    plt.close(fig)
    print("DONE: generated fig31..fig34 in", FIG_DIR, flush=True)


if __name__ == "__main__":
    main()
