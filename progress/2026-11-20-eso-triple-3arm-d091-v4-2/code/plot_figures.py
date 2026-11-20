#!/usr/bin/env python3
"""
Phase D091 Publication Figures (220 DPI):
  - fig39_d091_eso_triple_coverage_and_cascade.png
  - fig40_d091_calibration_2697_and_xshooter_dichroic.png
  - fig41_d091_panchromatic_35bridges_and_310star_limits.png
  - fig42_d091_allsky_comb_358stacks_and_orbital100.png
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = Path(__file__).resolve().parent
RES = WS / "results"
FIG = WS / "figures"

plt.rcParams.update({
    "font.size": 9.0,
    "axes.titlesize": 10.4,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.4,
    "xtick.labelsize": 8.4,
    "ytick.labelsize": 8.4,
    "legend.fontsize": 7.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _f(val: str | None) -> float:
    if val is None or val == "":
        return float("nan")
    return float(val)


def make_fig39(summary: dict, diag: dict, ledger_rows: list[dict[str, str]]) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 6.1), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # Panel A: 19 spectrographs / 22 arms across 0.0905 - 28.00 um (8.273 octaves)
    arms = [
        ("FUSE FUV (D089)", 0.0905, 0.1187, 20000, "#4c1d95"),
        ("HST COS FUV (D089)", 0.1140, 0.1750, 18000, "#6d28d9"),
        ("HST STIS NUV (D087/D089)", 0.1650, 0.3150, 30000, "#7c3aed"),
        ("VLT X-shooter 3-Arm (D091)", 0.2989, 2.4790, 18340, "#0284c7"),
        ("UVES NUV (D086)", 0.3050, 0.3910, 42000, "#2563eb"),
        ("MPG/ESO FEROS (D091)", 0.3527, 0.9216, 48000, "#059669"),
        ("CFHT ESPaDOnS (D088)", 0.3700, 1.0480, 68000, "#0ea5e9"),
        ("ESPRESSO (D081)", 0.3800, 0.7880, 140000, "#0d9488"),
        ("HARPS + HARPS-N (D079-D084)", 0.3780, 0.6910, 115000, "#10b981"),
        ("FLAMES/GIRAFFE HR (D091)", 0.5139, 0.8994, 26000, "#15803d"),
        ("CARMENES VIS (D084)", 0.5200, 0.9600, 94600, "#22c55e"),
        ("UVES RED (D087)", 0.5650, 1.0420, 45000, "#65a30d"),
        ("NIRPS HE (D082)", 0.9800, 1.8000, 80000, "#ca8a04"),
        ("CARMENES NIR (D085)", 0.9600, 1.7100, 80400, "#d97706"),
        ("CFHT SPIRou (D085)", 0.9800, 2.5100, 70000, "#ea580c"),
        ("VLT CRIRES+ K (D083)", 1.9700, 2.4800, 96000, "#dc2626"),
        ("JWST NIRSpec G235H (D090)", 1.6550, 3.0720, 2700, "#b91c1c"),
        ("JWST NIRSpec G395H (D090)", 2.8620, 5.1790, 2700, "#991b1b"),
        ("JWST MIRI MRS Ch1-4 (D090)", 4.9000, 28.0000, 2500, "#7f1d1d"),
    ]
    y_pos = np.arange(len(arms))
    for i, (lbl, lo, hi, rval, col) in enumerate(arms):
        lw = 6.0 if "D091" in lbl else 4.6
        ax1.plot([lo, hi], [i, i], color=col, lw=lw, solid_capstyle="round")
        if "D091" in lbl:
            ax1.scatter([lo, hi], [i, i], color=col, s=28, edgecolor="black", linewidth=0.5, zorder=5)
        ax1.text(hi * 1.07, i, f"R={rval//1000}k" if rval >= 10000 else f"R={rval/1000:.1f}k",
                 va="center", fontsize=7.3, color="#1f2937", fontweight="bold" if "D091" in lbl else "normal")
    ax1.axvspan(0.2989, 2.4790, color="#bae6fd", alpha=0.35, zorder=0, label="D091 ESO Triple Span (0.2989-2.4790 um)")
    ax1.axvline(10.60, color="#991b1b", ls="--", lw=1.1, alpha=0.8)
    ax1.text(10.60 * 0.92, 1.5, "10.60 um\nCO2 Laser", color="#7f1d1d", fontsize=7.4, ha="right", fontweight="bold")
    ax1.set_xscale("log")
    ax1.set_xlim(0.08, 68.0)
    ax1.set_ylim(-0.8, len(arms) - 0.1)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels([a[0] for a in arms], fontsize=7.6)
    ax1.invert_yaxis()
    ax1.set_xlabel("Vacuum Wavelength (micrometer, log scale)")
    ax1.set_title("19 Spectrographs / 22 Arms Across 0.0905-28.00 um (8.273 octaves)")
    ax1.grid(axis="x", which="both", alpha=0.25)
    ax1.legend(loc="lower left", frameon=True, framealpha=0.92)

    # Panel B: D091 False-Alarm Cascade + Forensic Triage Summary
    cas = diag["cascade"]
    stages = [
        ("V2 Legacy", int(cas["v2_legacy_false_alarms"])),
        ("V4.2 G1", int(cas["v42_total_ledger_g1_candidates"])),
        ("G2 Airglow", int(cas["v42_after_g2"])),
        ("G3 LSF", int(cas["v42_after_g3"])),
        ("G4 Coinc.", int(cas["v42_after_g4"])),
        ("Pre-G6 (G5)", int(cas["v42_pre_g6_passed_g1_to_g5"])),
        ("Auto Qual.", int(cas["automated_qualified_control"]) + int(cas["automated_qualified_science"])),
        ("Verified ETI", int(cas["verified_eti_detections"])),
    ]
    x = np.arange(len(stages))
    vals = [s[1] for s in stages]
    plot_vals = [max(v, 0.6) for v in vals]
    cols = ["#94a3b8", "#64748b", "#3b82f6", "#0284c7", "#0d9488", "#d97706", "#dc2626", "#16a34a"]
    bars = ax2.bar(x, plot_vals, color=cols, edgecolor="#1e293b", linewidth=0.7)
    ax2.set_yscale("log")
    ax2.set_ylim(0.4, max(plot_vals) * 14.0)
    for rect, raw_v in zip(bars, vals):
        ax2.text(rect.get_x() + rect.get_width() / 2.0, rect.get_height() * 1.18, f"{raw_v:,}",
                 ha="center", va="bottom", fontsize=7.9, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels([s[0] for s in stages], rotation=24, ha="right", fontsize=7.9)
    ax2.set_ylabel("Candidate Count (log scale)")
    ax2.set_title(f"D091 4-Gen False-Alarm Cascade ({cas['v2_legacy_false_alarms']:,} V2 -> 0 ETI)")
    ax2.grid(axis="y", which="both", alpha=0.25)

    fcls = diag.get("forensic_class_counts", {})
    n_qual_rows = sum(1 for r in ledger_rows if r.get("qualified_v42_laser") == "True")
    lines = ["Forensic Triage Summary:", f"Auto-qualified rows: {n_qual_rows:,}"]
    for k, v in list(fcls.items())[:4]:
        short_k = k[:28] + ("..." if len(k) > 28 else "")
        lines.append(f"  {short_k}: {v:,}")
    lines.append("Verified ETI Detections: 0")
    ax2.text(0.98, 0.96, "\n".join(lines), transform=ax2.transAxes, ha="right", va="top", fontsize=7.0,
             bbox=dict(boxstyle="round,pad=0.35", fc="#f8fafc", ec="#cbd5e1"))

    fig.tight_layout()
    out = FIG / "fig39_d091_eso_triple_coverage_and_cascade.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def make_fig40(summary: dict, comp_rows: list[dict[str, str]], diag: dict) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.6))

    inst_styles = [
        ("ESO_XSHOOTER_3ARM", "#0284c7", "o", "X-shooter 3-Arm (0.30-2.48 um)"),
        ("ESO_FEROS", "#059669", "s", "FEROS Echelle (0.35-0.92 um)"),
        ("ESO_GIRAFFE_HR", "#d97706", "^", "GIRAFFE HR (0.51-0.90 um)"),
    ]
    for inst, col, mrk, lbl in inst_styles:
        for mode, ls, mtag in [("CHANNEL_T_TRANSIENT_1EPOCH", "-", "Ch. T"), ("CHANNEL_P_STATIC_COADD", "--", "Ch. P")]:
            by_sig: dict[float, list[float]] = {}
            for r in comp_rows:
                if r["instrument"] == inst and r["mode"] == mode:
                    by_sig.setdefault(float(r["sigma_mult"]), []).append(float(r["completeness"]))
            if not by_sig:
                continue
            xs = sorted(by_sig.keys())
            ys = [100.0 * np.mean(by_sig[s]) for s in xs]
            ax1.plot(xs, ys, mrk + ls, color=col, lw=2.0, ms=5.5, label=f"{lbl} ({mtag})")
    ax1.axvline(8.0, color="#dc2626", ls=":", lw=1.4, label="8 sigma completeness threshold")
    ax1.set_xlim(3.0, 12.6)
    ax1.set_ylim(-4.0, 108.0)
    ax1.set_xlabel("Injected Signal Amplitude (sigma)")
    ax1.set_ylabel("Recovery Completeness (%)")
    ax1.set_title("1,620 Injection-Recovery Trials Across 15 ESO Bands")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="lower right", fontsize=7.3, frameon=True)

    cal = summary["synthetic_calibration_2697_trials"]
    xd = diag["xshooter_dual_arm_coincidence"]
    labels = [
        "Ch T >=8s\nRecov.", "Ch P >=8s\nRecov.", "Kep. T_DIFF\nBlur", "Kep. K_PLAN\nRecov.",
        "G45 True\nLaser", "G5 CR/HotPx\nReject", "G5 Plateau\nReject",
        "XSH Dual\nPass (8/8)", "XSH Single\nVeto (8/8)",
        "COMB v4.1\n6-Tooth", "COMB v4.0\nForest FPR", "COMB v4.1\nForest FPR",
    ]
    vals = [
        100.0 * cal["channel_t_ge_8sigma"],
        100.0 * cal["channel_p_ge_8sigma"],
        100.0 * cal["keplerian_tdiff_ge_6p5sigma"],
        100.0 * cal["keplerian_kplanet_ge_6p5sigma"],
        100.0 * cal["g45_true_laser_pass"],
        100.0 * cal["g5_cosmic_hotpx_rejection"],
        100.0 * cal["g5_plateau_rejection"],
        100.0 * xd["dual_arm_pass_count"] / max(1, xd["n_tested"]),
        100.0 * xd["single_arm_vetoed_count"] / max(1, xd["n_tested"]),
        100.0 * cal["comb_v41_6tooth_ge_3p8sigma_recovery"],
        100.0 * cal["comb_v4_dense_forest_fpr"],
        100.0 * cal["comb_v41_dense_forest_fpr"],
    ]
    cols = [
        "#059669", "#059669", "#dc2626", "#059669",
        "#0284c7", "#0284c7", "#0284c7", "#7c3aed",
        "#7c3aed", "#0d9488", "#f97316", "#059669",
    ]
    x = np.arange(len(labels))
    bars = ax2.bar(x, vals, color=cols, edgecolor="#1e293b", linewidth=0.6)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2.0, min(105.0, v + 2.2), f"{v:.0f}%",
                 ha="center", va="bottom", fontsize=7.4, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=32, ha="right", fontsize=7.2)
    ax2.set_ylim(0, 114)
    ax2.set_ylabel("Rate (%)")
    ax2.set_title("2,697-Trial Validation & X-Shooter Dual-Arm Coincidence")
    ax2.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    out = FIG / "fig40_d091_calibration_2697_and_xshooter_dichroic.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def make_fig41(bridge_rows: list[dict[str, str]], u310_rows: list[dict[str, str]]) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.7))

    showcase = [
        ("LAWD37", "LAWD 37 (0.36-23.5 um, NEW WD bridge)", "#7c3aed", 2.1),
        ("GJ849", "GJ 849 (0.36-2.10 um + Radio M17)", "#dc2626", 2.1),
        ("GJ674", "GJ 674 (0.36-2.10 um, NEW bridge)", "#0284c7", 1.9),
        ("HD20794", "HD 20794 (0.36-2.10 um, NEW bridge)", "#059669", 1.9),
        ("GJ436", "GJ 436 (0.55-2.35 um, NEW bridge)", "#d97706", 1.9),
        ("BETPIC", "bet Pic (0.092-23.5 um, 8.0 oct)", "#475569", 1.6),
        ("16CYGB", "16 Cyg B (0.395-23.5 um + GBT)", "#0d9488", 1.6),
    ]
    by_star: dict[str, list[tuple[float, float]]] = {}
    for r in bridge_rows:
        by_star.setdefault(r["star"], []).append((_f(r["wave_um"]), _f(r["p_beam_10m_kw"])))
    for st, lst in by_star.items():
        if st not in {s[0] for s in showcase}:
            lst_s = sorted(lst)
            ax1.plot([x[0] for x in lst_s], [x[1] for x in lst_s], color="#cbd5e1", lw=0.85, alpha=0.75, zorder=1)
    for st, lbl, col, lw in showcase:
        lst_s = sorted(by_star.get(st, []))
        if lst_s:
            ax1.plot([x[0] for x in lst_s], [x[1] for x in lst_s], "o-", color=col, lw=lw, ms=3.4, label=lbl, zorder=4)
    ax1.axvspan(0.2989, 2.4790, color="#e0f2fe", alpha=0.45, zorder=0, label="D091 X-shooter Band")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.08, 32.0)
    ax1.set_xlabel("Wavelength (micrometer)")
    ax1.set_ylabel("8 sigma 10 m-Transmitter Limit (kW)")
    ax1.set_title("35 Panchromatic Bridges Across 0.0905-28.00 um (+5 in D091)")
    ax1.grid(True, which="both", alpha=0.22)
    ax1.legend(loc="lower right", fontsize=7.0, frameon=True, framealpha=0.92)

    prior_d, prior_p = [], []
    d091_d, d091_p = [], []
    spot_pts = {}
    for r in u310_rows:
        d = _f(r["dist_pc"])
        p = _f(r["min_panchromatic_10m_kw"])
        if not (np.isfinite(d) and np.isfinite(p) and p > 0):
            continue
        if r["star"] in ("LAWD37", "GJ849", "K222", "GJ908"):
            spot_pts[r["star"]] = (d, p)
        if "D091" in r.get("phases", ""):
            d091_d.append(d)
            d091_p.append(p)
        else:
            prior_d.append(d)
            prior_p.append(p)

    ax2.scatter(prior_d, prior_p, s=20, color="#64748b", alpha=0.65, label=f"D079-D090 Prior Stars ({len(prior_d)})")
    ax2.scatter(d091_d, d091_p, s=42, color="#0284c7", edgecolor="#0c4a6e", linewidth=0.6, zorder=4,
                label=f"D091 ESO Triple Cohort ({len(d091_d)})")
    spot_off = {"LAWD37": (-6, -12), "GJ849": (7, -2), "GJ908": (-8, -12), "K222": (-8, -12)}
    for lb, pt in spot_pts.items():
        ax2.scatter([pt[0]], [pt[1]], s=65, marker="*", color="#dc2626", edgecolor="black", zorder=5)
        dx, dy = spot_off.get(lb, (5, 5))
        ax2.annotate(lb, pt, xytext=(dx, dy), textcoords="offset points",
                     ha="left" if dx > 0 else "right", fontsize=7.4, fontweight="bold", color="#991b1b")
    all_d = prior_d + d091_d
    ax2.axvline(10.0, color="#059669", ls="--", lw=1.2, label="10 pc Volume (135 unique stars)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Gaia / Trigonometric Distance (pc)")
    ax2.set_ylabel("Best Panchromatic 10 m Beam Limit (kW)")
    ax2.set_title(f"310 Unique Stars Limits ({min(all_d):.1f}-{max(all_d):.0f} pc, 135 within 10 pc)")
    ax2.grid(True, which="both", alpha=0.22)
    ax2.legend(loc="lower right", fontsize=7.2, frameon=True, framealpha=0.92)

    fig.tight_layout()
    out = FIG / "fig41_d091_panchromatic_35bridges_and_310star_limits.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def make_fig42(allsky_comb: list[dict[str, str]], orb10: list[dict[str, str]], mm_rows: list[dict[str, str]], summary: dict) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.8, 5.8))

    inst_order = []
    seen_i = set()
    for r in allsky_comb:
        ins = r["instrument"]
        if ins not in seen_i:
            seen_i.add(ins)
            inst_order.append(ins)
    v4_cnt, v41_cnt, stack_cnt = Counter(), Counter(), Counter()
    for r in allsky_comb:
        ins = r["instrument"]
        stack_cnt[ins] += 1
        v4_cnt[ins] += int(r["comb_v4_candidates"])
        v41_cnt[ins] += int(r["comb_v41_candidates"])

    y = np.arange(len(inst_order))
    v4_vals = [max(v4_cnt[i], 0) for i in inst_order]
    v41_vals = [max(v41_cnt[i], 0) for i in inst_order]
    ax1.barh(y - 0.18, v4_vals, height=0.34, color="#f97316", edgecolor="#7c2d12", label="COMB_V4 Automated")
    ax1.barh(y + 0.18, v41_vals, height=0.34, color="#0284c7", edgecolor="#0c4a6e", label="COMB_V4_1 Automated (0 ETI)")
    ax1.set_xscale("symlog", linthresh=1.0)
    ax1.set_xlim(0, max(max(v4_vals), 10) * 90.0)
    for idx, ins in enumerate(inst_order):
        ax1.text(max(v4_vals[idx], v41_vals[idx], 0.5) * 1.18 + 0.3, idx,
                 f"n={stack_cnt[ins]} | V4={v4_cnt[ins]} -> V4.1={v41_cnt[ins]}",
                 va="center", fontsize=6.9)
    ax1.set_yticks(y)
    ax1.set_yticklabels(inst_order, fontsize=7.2)
    ax1.invert_yaxis()
    ax1.set_xlabel("Automated Comb Candidates (symlog scale)")
    ax1.set_title(f"All-Sky COMB_V4_1 Sweep: {len(allsky_comb)} Stacks (D079-D091, 0 ETI)")
    ax1.grid(axis="x", alpha=0.25)
    ax1.legend(loc="center right", fontsize=7.3)

    offsets = {
        "K222": (7, 4), "GJ433": (-6, -8), "HD213885": (-6, 5),
        "HD220009": (7, 5), "HD107328": (-6, -9), "G29751": (7, -9),
        "GJ436": (7, -8), "OGLETR113": (-6, -10), "OGLETR111": (7, 4), "KEPLER156": (7, 4),
    }
    cmap = {"ESO_XSHOOTER_3ARM": "#dc2626", "ESO_FEROS": "#059669", "ESO_GIRAFFE_HR": "#0284c7"}
    for r in orb10:
        per = _f(r["orbper_days"])
        kp = _f(r["kp_kms"])
        is_ctrl = r["role"] == "CONTROL"
        col = "#64748b" if is_ctrl else cmap.get(r["instrument"], "#0284c7")
        mrk = "s" if is_ctrl else "o"
        ax2.scatter([per], [kp], color=col, marker=mrk, s=68, edgecolor="black", linewidth=0.7, zorder=4)
        dx, dy = offsets.get(r["star"], (6, 4))
        ax2.annotate(r["star"], (per, kp), xytext=(dx, dy), textcoords="offset points",
                     ha="left" if dx > 0 else "right", fontsize=7.4, fontweight="bold")

    ax2.scatter([], [], color="#64748b", marker="s", s=55, edgecolor="black", label="Null Controls (#91-#93)")
    ax2.scatter([], [], color="#dc2626", marker="o", s=55, edgecolor="black", label="X-shooter Planet (#94)")
    ax2.scatter([], [], color="#059669", marker="o", s=55, edgecolor="black", label="FEROS Planets (#95-#96)")
    ax2.scatter([], [], color="#0284c7", marker="o", s=55, edgecolor="black", label="GIRAFFE Planets (#97-#100)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Orbital Period P_orb (days)")
    ax2.set_ylabel("Keplerian Semi-Amplitude K_p (km/s)")
    ax2.set_title("Orbital Campaigns #91-#100 (Cumulative 100/100) & Multi-Messenger", fontsize=9.8)
    ax2.grid(True, which="both", alpha=0.22)
    ax2.legend(loc="upper right", fontsize=7.2)

    mm_n = len(mm_rows)
    n_over = sum(1 for r in mm_rows if r["multimessenger_overlap"] == "True")
    n_td = sum(int(r["qualified_tdiff_candidates"]) for r in orb10)
    n_kp = sum(int(r["qualified_kplanet_candidates"]) for r in orb10)
    box_txt = (
        f"D091 Orbital #91-#100: {n_td} T_DIFF / {n_kp} K_PLANET -> 0 ETI\n"
        f"Cumulative Orbital Campaigns: {summary['unified_310star_panchromatic_v4_2_synthesis']['cumulative_orbital_campaigns']}/100\n"
        f"Multi-Messenger: {mm_n} systems | 23/23 Radio Closure\n"
        f"Tri-Regime Systems: 16CYGB + GJ849 ({n_over} MM overlaps)"
    )
    ax2.text(0.03, 0.04, box_txt, transform=ax2.transAxes, ha="left", va="bottom", fontsize=7.3,
             bbox=dict(boxstyle="round,pad=0.35", fc="#f8fafc", ec="#cbd5e1"))

    fig.tight_layout()
    out = FIG / "fig42_d091_allsky_comb_358stacks_and_orbital100.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    diag = json.loads((RES / "FORENSIC_D091_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    ledger = _read_csv(RES / "V4_2_CANDIDATE_LEDGER.csv")
    comp = _read_csv(RES / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    bridges = _read_csv(RES / "PANCHROMATIC_BRIDGE_35STARS.csv")
    u310 = _read_csv(RES / "UNIFIED_PANCHROMATIC_V4_2_SYNTHESIS_310STARS.csv")
    allsky_comb = _read_csv(RES / "ALLSKY_COMB_V4_1_UNIFIED_D079_D091.csv")
    orb10 = _read_csv(RES / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    mm_rows = _read_csv(RES / "MULTIMESSENGER_ECHELLE_RADIO_TESS_310SYSTEMS.csv")

    p1 = make_fig39(summary, diag, ledger)
    p2 = make_fig40(summary, comp, diag)
    p3 = make_fig41(bridges, u310)
    p4 = make_fig42(allsky_comb, orb10, mm_rows, summary)
    for p in (p1, p2, p3, p4):
        print(f"Wrote {p.name} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
