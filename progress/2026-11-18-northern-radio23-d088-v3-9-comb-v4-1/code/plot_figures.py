#!/usr/bin/env python3
"""
Generate the 4 publication-grade 220-DPI figures (fig27..fig30) for Phase D088:
  - fig27_d088_12spec_panchromatic_and_220star_limits.png
  - fig28_d088_allsky_comb_v4_1_1567exp_and_radio23_closure.png
  - fig29_d088_synthetic_calibration_2697_trials.png
  - fig30_d088_kinematics_berv_rv_and_orbital10.png
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
        "font.size": 10,
        "axes.titlesize": 11.2,
        "axes.labelsize": 10.2,
        "xtick.labelsize": 9.2,
        "ytick.labelsize": 9.2,
        "legend.fontsize": 8.4,
        "figure.dpi": 220,
    })

    summary = json.loads((RESULTS / "SUMMARY.json").read_text(encoding="utf-8"))
    u220 = load_csv(RESULTS / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_220STARS.csv")
    ul_rows = load_csv(RESULTS / "STAR_UPPER_LIMITS_D088.csv")
    allsky_u = load_csv(RESULTS / "ALLSKY_COMB_V4_1_UNIFIED_D079_D088.csv")
    allsky_c = load_csv(RESULTS / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D088.csv")
    mm220 = load_csv(RESULTS / "MULTIMESSENGER_ECHELLE_RADIO_TESS_220SYSTEMS.csv")
    comb_cal = load_csv(RESULTS / "COMB_V4_1_CALIBRATION_486.csv")
    inj = load_csv(RESULTS / "INJECTION_RECOVERY_1620.csv")
    kep = load_csv(RESULTS / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    g45 = load_csv(RESULTS / "DETECTOR_V38_G4G5_CALIBRATION_216.csv")
    g6 = load_csv(RESULTS / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    prov = load_csv(RESULTS / "EXPOSURE_PROVENANCE_176.csv")
    rv_sum = load_csv(RESULTS / "STAR_RV_SUMMARY_25.csv")
    orb_rows = load_csv(RESULTS / "ORBITAL_CAMPAIGN_RESULTS_10.csv")

    # ---------------- Figure 27: 12-Spectrograph Coverage + 220-Star / 117-<10pc Limits ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.8), constrained_layout=True)

    arms = [
        ("HST_STIS E140M (Space)", 0.1145, 0.1710, "#4e79a7", "R=45.8k [D087]"),
        ("UVES_NUV (Paranal)", 0.305, 0.456, "#59a14f", "R=41k-71k [D086]"),
        ("CFHT ESPaDOnS (Maunakea)", 0.370, 1.048, "#d62728", "R=65k-80k [D088 New]"),
        ("HARPS / HARPS-N", 0.378, 0.691, "#76b7b2", "R=115k [D079-D086]"),
        ("ESPRESSO HR/UHR", 0.379, 0.786, "#2c7fb8", "R=140k/190k [D080-D087]"),
        ("OHP SOPHIE (France)", 0.387, 0.694, "#9467bd", "R=75k [D088 New]"),
        ("OHP ELODIE (France)", 0.400, 0.680, "#8c564b", "R=42k [D088 New]"),
        ("CARMENES_VIS (CAHA)", 0.520, 0.960, "#edc948", "R=94.6k [D084]"),
        ("UVES_RED (Paranal)", 0.5655, 1.0425, "#e15759", "R=42k-107k [D087]"),
        ("NIRPS_HE (La Silla)", 0.980, 1.800, "#f28e2b", "R=70k [D082]"),
        ("CFHT SPIRou (Maunakea)", 0.955, 2.515, "#b07aa1", "R=70k [D085]"),
        ("VLT CRIRES+ (Paranal)", 1.960, 2.480, "#9c755f", "R=86k [D083]"),
    ]
    for yi, (lbl, w0, w1, col, note) in enumerate(arms):
        ax1.barh(yi, w1 - w0, left=w0, height=0.64, color=col, edgecolor="#222", linewidth=0.7, alpha=0.90)
        if w1 < 1.5:
            ax1.text(w1 * 1.05, yi, note, va="center", ha="left", fontsize=7.8, color="#111")
        else:
            ax1.text(w0 * 0.95, yi, note, va="center", ha="right", fontsize=7.8, color="#111")
    ax1.set_xscale("log")
    ax1.set_xlim(0.095, 3.6)
    ax1.set_yticks(range(len(arms)))
    ax1.set_yticklabels([a[0] for a in arms])
    ax1.invert_yaxis()
    ax1.set_xlabel("Barycentric Wavelength (microns, log scale)")
    ax1.set_title("12-Spectrograph (13-Arm) Coverage: 0.1145-2.515 um (4.457 Octaves)")
    ax1.grid(True, axis="x", which="both", alpha=0.25)

    d_all, p_all, d_10, p_10 = [], [], [], []
    for r in u220:
        if r.get("min_panchromatic_10m_kw"):
            dv, pv = float(r["dist_pc"]), float(r["min_panchromatic_10m_kw"])
            if r["within_10pc"] == "True":
                d_10.append(dv)
                p_10.append(pv)
            else:
                d_all.append(dv)
                p_all.append(pv)
    ax2.scatter(d_all, p_all, s=20, color="#9aa4b2", alpha=0.58, label=f"D079-D088 >10 pc (n={len(d_all)})")
    ax2.scatter(d_10, p_10, s=24, color="#2b5c8f", alpha=0.72, label=f"D079-D088 <10 pc (117 total)")

    best_d088: dict[str, tuple[float, float, str]] = {}
    for ur in ul_rows:
        st = ur["star"]
        kw = float(ur["p_beam_10m_kw"])
        dp_v = float(ur["dist_pc"])
        inst = ur["instrument"]
        if st not in best_d088 or kw < best_d088[st][1]:
            best_d088[st] = (dp_v, kw, inst)
    col_inst = {"OHP_SOPHIE": "#9467bd", "OHP_ELODIE": "#8c564b", "CFHT_ESPADONS": "#d62728"}
    for inst in ("OHP_SOPHIE", "OHP_ELODIE", "CFHT_ESPADONS"):
        pts = [(d, p, s) for s, (d, p, i) in best_d088.items() if i == inst]
        if pts:
            ax2.scatter([x[0] for x in pts], [x[1] for x in pts], s=48, color=col_inst[inst], edgecolor="#111", linewidth=0.7, zorder=4, label=f"D088 {inst} (n={len(pts)})")

    annotate_stars = [("61CYGA", (8, -7)), ("GJ625", (8, -9)), ("47UMA", (7, -9)), ("BETUMI", (-46, 6)), ("GJ687", (-36, -12))]
    for st, offs in annotate_stars:
        if st in best_d088:
            d_s, p_s, _ = best_d088[st]
            ax2.annotate(st, (d_s, p_s), xytext=offs, textcoords="offset points", fontsize=7.6, fontweight="bold", color="#222")

    ax2.axvline(10.0, color="#555", linestyle="--", linewidth=0.9, alpha=0.7)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Gaia DR3 / Hipparcos Distance (pc)")
    ax2.set_ylabel("Best 8-sigma 10 m CW Laser Power Limit (kW)")
    ax2.set_title("220-Star / 117-<10pc Panchromatic Sensitivity Landscape")
    ax2.grid(True, which="both", alpha=0.22)
    ax2.legend(loc="lower right", framealpha=0.92)

    fig.savefig(FIG_DIR / "fig27_d088_12spec_panchromatic_and_220star_limits.png", dpi=220)
    plt.close(fig)

    # ---------------- Figure 28: All-Sky COMB_V4_1 (1,567 exp) + 23/23 Radio-Echelle Closure ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 5.6), constrained_layout=True)

    phases_order = [f"D0{k}" for k in range(79, 89)]
    v4_by_ph = defaultdict(int)
    v41_by_ph = defaultdict(int)
    exp_by_ph = defaultdict(int)
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
    ax1.set_ylim(0, max(v4_vals) * 2.2)
    for rect in b1:
        hv = int(rect.get_height())
        if hv > 0:
            ax1.text(rect.get_x() + rect.get_width() / 2, hv * 1.15 + 0.15, str(hv), ha="center", va="bottom", fontsize=7.2, color="#b35900")
    for rect in b2:
        hv = int(rect.get_height())
        if hv > 0:
            ax1.text(rect.get_x() + rect.get_width() / 2, hv * 1.15 + 0.15, str(hv), ha="center", va="bottom", fontsize=7.4, fontweight="bold", color="#1b4f72")
    ax1.set_xticks(x_ph)
    ax1.set_xticklabels([f"{p}\n({exp_by_ph[p]})" for p in phases_order], fontsize=8.0)
    ax1.set_ylabel("Automated Comb Candidates (symlog)")
    ax1.set_title("All-Sky COMB_V4_1 Sweep: 1,567 Exp / 247 Stacks (100% D079-D088)", fontsize=10.4)
    ax1.grid(True, axis="y", alpha=0.25)
    ax1.legend(loc="upper left", framealpha=0.92)

    # Right panel: 220-system Multi-Messenger + 23/23 Radio-Echelle Closure
    d088_radio = {"47UMA", "HD154345", "HD33564", "HD127506", "PSI1DRAB", "BETUMI"}
    prior_rad, new_rad, tess_sys, single_echelle = [], [], [], []
    for r in mm220:
        d_pc = float(r["dist_pc"]) if r.get("dist_pc") else 10.0
        n_exp = int(r["echelle_exposures"]) if r.get("echelle_exposures") else 0
        if r["system_id"] in d088_radio:
            new_rad.append((d_pc, n_exp, r["system_id"]))
        elif r["multimessenger_overlap"] == "True" and r.get("radio_milestone"):
            prior_rad.append((d_pc, n_exp, r["system_id"]))
        elif r["multimessenger_overlap"] == "True":
            tess_sys.append((d_pc, n_exp, r["system_id"]))
        else:
            single_echelle.append((d_pc, n_exp))

    ax2.scatter([x[0] for x in single_echelle], [x[1] for x in single_echelle], s=20, color="#aab2bd", alpha=0.62, label=f"Optical/NIR/UV Echelle Only (n={len(single_echelle)})")
    ax2.scatter([x[0] for x in prior_rad], [x[1] for x in prior_rad], s=52, color="#2b5c8f", marker="D", edgecolor="#111", linewidth=0.6, zorder=3, label=f"Prior Radio+Echelle D079-D087 ({len(prior_rad)}/23)")
    ax2.scatter([x[0] for x in new_rad], [x[1] for x in new_rad], s=80, color="#e15759", marker="*", edgecolor="#111", linewidth=0.6, zorder=4, label="D088 Northern Radio Closure (6/23 -> 23/23=100%)")
    ax2.scatter([x[0] for x in tess_sys], [x[1] for x in tess_sys], s=60, color="#59a14f", marker="^", edgecolor="#111", linewidth=0.6, zorder=4, label="TESS Lightsail+Echelle (L 98-59)")
    rad_offsets = {
        "47UMA": (-42, 18),
        "HD154345": (8, -14),
        "HD33564": (-44, -18),
        "HD127506": (-10, 26),
        "PSI1DRAB": (10, -24),
        "BETUMI": (-8, 22),
    }
    for d_pc, n_e, sid in new_rad:
        offs = rad_offsets.get(sid, (6, 6))
        ax2.annotate(sid, (d_pc, n_e), xytext=offs, textcoords="offset points", fontsize=7.6, fontweight="bold", color="#900", arrowprops={"arrowstyle": "-", "lw": 0.65, "color": "#900"})
    ax2.set_xscale("log")
    ax2.set_ylim(2.5, 28.0)
    ax2.set_xlabel("Distance (pc)")
    ax2.set_ylabel("Total Echelle Exposures Across Survey")
    ax2.set_title("220-System Multi-Messenger: 23/23 Radio Closure (0 ETI)", fontsize=10.4)
    ax2.grid(True, which="both", alpha=0.22)
    ax2.legend(loc="upper left", fontsize=8.0, framealpha=0.92)

    fig.savefig(FIG_DIR / "fig28_d088_allsky_comb_v4_1_1567exp_and_radio23_closure.png", dpi=220)
    plt.close(fig)

    # ---------------- Figure 29: 2,697 Synthetic Calibration Trials ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.3), constrained_layout=True)

    inst_cols = {"OHP_SOPHIE": "#9467bd", "OHP_ELODIE": "#8c564b", "CFHT_ESPADONS": "#d62728"}
    sig_levels = sorted({float(r["sigma_mult"]) for r in inj})
    for inst in ("OHP_SOPHIE", "OHP_ELODIE", "CFHT_ESPADONS"):
        for mode, ls in (("CHANNEL_T_TRANSIENT_1EPOCH", "-"), ("CHANNEL_P_PERSISTENT_COADD", "--")):
            sub = [r for r in inj if r["instrument"] == inst and r["mode"] == mode]
            ys = [np.mean([x["recovered"] == "True" for x in sub if abs(float(x["sigma_mult"]) - sv) < 1e-6]) * 100.0 for sv in sig_levels]
            ax1.plot(sig_levels, ys, marker="o", linestyle=ls, linewidth=1.8, color=inst_cols[inst], label=f"{inst} {'T' if 'CHANNEL_T' in mode else 'P'}")
    ax1.axvline(8.0, color="#222", linestyle=":", linewidth=1.0)
    ax1.set_xlabel("Injected Signal Amplitude (sigma_MAD)")
    ax1.set_ylabel("Recovery Rate (%)")
    ax1.set_ylim(-4, 106)
    ax1.set_title("1,620 Channel T & P Injection-Recovery Curves (100% at >=8 sigma)")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="lower right", ncol=2, fontsize=7.6)

    # Right panel: Keplerian, G4_V38+G5, G6 Sparse, COMB_V4 vs V4.1 summary rates
    k_td = np.mean([r["tdiff_uncomp_recovered"] == "True" for r in kep]) * 100.0
    k_kp = np.mean([r["kplanet_dedop_recovered"] == "True" for r in kep]) * 100.0
    g_tr = np.mean([r["g45_pass"] == "True" for r in g45 if r["trial_class"] == "TRUE_LSF_LASER"]) * 100.0
    g_cr = np.mean([r["g45_pass"] == "False" for r in g45 if r["trial_class"] == "COSMIC_RAY_HOT_PIXEL"]) * 100.0
    g_pl = np.mean([r["g45_pass"] == "False" for r in g45 if r["trial_class"] == "M_DWARF_PLATEAU_CORE"]) * 100.0
    g6_t = np.mean([r["g6_v36_sparse_pass"] == "True" for r in g6 if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]) * 100.0
    g6_bg = np.mean([r["g6_v36_sparse_pass"] == "False" for r in g6 if r["trial_class"] != "TRUE_BARYCENTRIC_STELLAR_LASER"]) * 100.0
    c_rec = np.mean([r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]) * 100.0
    c_for4 = np.mean([r["comb_v4_hit"] == "True" for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]) * 100.0
    c_for41 = np.mean([r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]) * 100.0

    labels = ["Kep\nT_DIFF", "Kep\nK_PL", "G4/5\nTrue", "G4/5\nCR Rej", "G4/5\nPlat Rej", "G6\nTrue", "G6\nSky/Px", "Comb\n6-Tooth", "Forest\nV4 FPR", "Forest\nV4.1 FPR"]
    vals = [k_td, k_kp, g_tr, g_cr, g_pl, g6_t, g6_bg, c_rec, c_for4, c_for41]
    cols = ["#aaa", "#2c7fb8", "#59a14f", "#59a14f", "#59a14f", "#2b5c8f", "#2b5c8f", "#9467bd", "#e15759", "#2c7fb8"]
    bars = ax2.bar(range(len(labels)), vals, color=cols, edgecolor="#222", linewidth=0.6)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.1f}%", ha="center", va="bottom", fontsize=7.4)
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels, fontsize=7.6)
    ax2.set_ylim(0, 114)
    ax2.set_ylabel("Rate (%)")
    ax2.set_title("Keplerian (135), G4/G5 (216), G6 (240), and COMB_V4_1 (486) Gates")
    ax2.grid(True, axis="y", alpha=0.25)

    fig.savefig(FIG_DIR / "fig29_d088_synthetic_calibration_2697_trials.png", dpi=220)
    plt.close(fig)

    # ---------------- Figure 30: Stdlib BERV/RV Validation + 10 Orbital Campaigns (#61-#70) ----------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.3), constrained_layout=True)

    rv_by_star = {r["star"]: float(r["empirical_minus_prior_kms"]) for r in rv_sum}
    for inst in ("OHP_SOPHIE", "OHP_ELODIE", "CFHT_ESPADONS"):
        sub = [r for r in prov if r["instrument"] == inst]
        xs = [float(r["berv_kms"]) for r in sub]
        ys = [float(r["berv_diff_stdlib_kms"]) for r in sub]
        ax1.scatter(xs, ys, s=26, color=inst_cols[inst], alpha=0.82, edgecolor="#111", linewidth=0.4, label=f"{inst} (n={len(sub)}, max={max(abs(y) for y in ys):.3f})")
    ax1.axhline(0.50, color="#c00", linestyle="--", linewidth=1.0, label="Gate bound +/-0.50 km/s")
    ax1.axhline(-0.50, color="#c00", linestyle="--", linewidth=1.0)
    ax1.axhline(0.0, color="#666", linestyle=":", linewidth=0.8)
    ax1.set_xlabel("Observatory BERV (km/s)")
    ax1.set_ylabel("Pipeline BERV - Pure-Stdlib Ephemeris (km/s)")
    ax1.set_ylim(-0.62, 0.62)
    ax1.set_title("176-Exposure OHP & Maunakea BERV Stdlib Frame Verification")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="upper right", fontsize=8.0)

    # Right panel: 10 Orbital Campaigns (#61-#70)
    y_pos = np.arange(len(orb_rows))
    orb_sorted = sorted(orb_rows, key=lambda r: float(r["kp_kms"]))
    for yi, r in enumerate(orb_sorted):
        kp = float(r["kp_kms"])
        dv = float(r["orbital_dv_span_kms"])
        is_ctrl = r["role"] == "CONTROL"
        c_main = "#888" if is_ctrl else "#2c7fb8"
        ax2.barh(yi, kp, height=0.55, color=c_main, alpha=0.35, edgecolor=c_main, label="K_p" if yi == 0 else "")
        ax2.barh(yi, dv, height=0.32, color="#e15759" if not is_ctrl else "#555", edgecolor="#111", linewidth=0.5, label="IN_WINDOW dv span" if yi == 0 else "")
        ax2.text(max(kp, dv) + 1.5, yi, f"P={float(r['orbper_days']):.1f}d | {r['instrument'].replace('OHP_','').replace('CFHT_','')} | 0 ETI", va="center", fontsize=7.6)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"{r['star']} ({'CTRL' if r['role']=='CONTROL' else 'SCI'})" for r in orb_sorted], fontsize=8.2)
    ax2.set_xlabel("Orbital Velocity Scale (km/s)")
    max_vel = max(max(float(r["kp_kms"]), float(r["orbital_dv_span_kms"])) for r in orb_sorted)
    ax2.set_xlim(0, max_vel * 1.44)
    ax2.set_title("10 D088 Orbital Campaigns (#61-#70 Cumulative, 4 IN + 4 OUT Each)")
    ax2.grid(True, axis="x", alpha=0.25)
    ax2.legend(loc="lower right", fontsize=8.0)

    fig.savefig(FIG_DIR / "fig30_d088_kinematics_berv_rv_and_orbital10.png", dpi=220)
    plt.close(fig)
    print("DONE: generated fig27..fig30 in", FIG_DIR, flush=True)


if __name__ == "__main__":
    main()
