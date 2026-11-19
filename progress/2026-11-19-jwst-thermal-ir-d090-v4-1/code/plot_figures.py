#!/usr/bin/env python3
"""
Phase D090 Publication Figures (220 DPI):
  - fig35_d090_thermal_ir_coverage_and_cascade.png
  - fig36_d090_calibration_2697_and_miri_dualband.png
  - fig37_d090_panchromatic_30bridges_and_280star_limits.png
  - fig38_d090_allsky_comb_321stacks_and_orbital90.png
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
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.labelsize": 9.5,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8.0,
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


def make_fig35(summary: dict, diag: dict, ledger_rows: list[dict[str, str]]) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.8), gridspec_kw={"width_ratios": [1.15, 1.0]})

    # Panel A: 16 spectrographs / 19 arms across 0.0905 - 28.00 um (8.273 octaves)
    arms = [
        ("FUSE FUV (D089)", 0.0905, 0.1187, 20000, "#4c1d95"),
        ("HST COS FUV (D089)", 0.1140, 0.1750, 18000, "#6d28d9"),
        ("HST STIS NUV (D087/D089)", 0.1650, 0.3150, 30000, "#7c3aed"),
        ("UVES NUV (D086)", 0.3050, 0.3910, 42000, "#2563eb"),
        ("CFHT ESPaDOnS (D088)", 0.3700, 1.0480, 68000, "#0284c7"),
        ("ESPRESSO (D081)", 0.3800, 0.7880, 140000, "#0d9488"),
        ("HARPS + HARPS-N (D079-D084)", 0.3780, 0.6910, 115000, "#059669"),
        ("CARMENES VIS (D084)", 0.5200, 0.9600, 94600, "#16a34a"),
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
        ax1.plot([lo, hi], [i, i], color=col, lw=5.5, solid_capstyle="round")
        if "D090" in lbl:
            ax1.scatter([lo, hi], [i, i], color=col, s=26, zorder=5)
        ax1.text(hi * 1.07, i, f"R={rval//1000}k" if rval >= 10000 else f"R={rval/1000:.1f}k",
                 va="center", fontsize=7.6, color="#1f2937")
    ax1.axvline(10.60, color="#991b1b", ls="--", lw=1.2, alpha=0.85)
    ax1.text(10.60 * 0.94, 1.5, "Townes (1983)\n10.60 um CO2", color="#7f1d1d", fontsize=7.6,
             ha="right", fontweight="bold", bbox=dict(boxstyle="round,pad=0.2", fc="#fef2f2", ec="#fca5a5"))
    ax1.axvspan(1.655, 28.00, color="#fee2e2", alpha=0.35, zorder=0, label="D090 JWST Thermal-IR (4.080 oct)")
    ax1.set_xscale("log")
    ax1.set_xlim(0.08, 68.0)
    ax1.set_ylim(-0.8, len(arms) - 0.1)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels([a[0] for a in arms], fontsize=8.0)
    ax1.invert_yaxis()
    ax1.set_xlabel("Vacuum Wavelength (micrometer, log scale)")
    ax1.set_title("Unbroken 8.273-Octave Span (0.0905-28.00 um, 16 Spectrographs / 19 Arms)")
    ax1.grid(axis="x", which="both", alpha=0.25)
    ax1.legend(loc="lower left", frameon=True, framealpha=0.92)

    # Panel B: D090 False-Alarm Cascade + Forensic Classes
    cas = diag["cascade"]
    stages = [
        ("V2 Legacy", int(cas["v2_legacy_false_alarms"])),
        ("V4.1 G1", int(cas["v41_total_ledger_g1_candidates"])),
        ("G2 Airglow", int(cas["v41_after_g2"])),
        ("G3 LSF", int(cas["v41_after_g3"])),
        ("G4 Coinc.", int(cas["v41_after_g4"])),
        ("Pre-G6 (G5)", int(cas["v41_pre_g6_passed_g1_to_g5"])),
        ("Auto Qual.", int(cas["automated_qualified_control"]) + int(cas["automated_qualified_science"])),
        ("Verified ETI", int(cas["verified_eti_detections"])),
    ]
    x = np.arange(len(stages))
    vals = [s[1] for s in stages]
    plot_vals = [max(v, 0.6) for v in vals]
    cols = ["#94a3b8", "#64748b", "#3b82f6", "#0284c7", "#0d9488", "#d97706", "#dc2626", "#16a34a"]
    bars = ax2.bar(x, plot_vals, color=cols, edgecolor="#1e293b", linewidth=0.7)
    ax2.set_yscale("log")
    ax2.set_ylim(0.4, max(plot_vals) * 9.0)
    for idx, (rect, raw_v) in enumerate(zip(bars, vals)):
        ax2.text(rect.get_x() + rect.get_width() / 2.0, rect.get_height() * 1.18, f"{raw_v:,}",
                 ha="center", va="bottom", fontsize=8.0, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels([s[0] for s in stages], rotation=24, ha="right", fontsize=8.0)
    ax2.set_ylabel("Candidate Count (log scale)")
    ax2.set_title(f"D090 4-Generation False-Alarm Cascade ({cas['v2_legacy_false_alarms']:,} V2 -> 0 ETI)")
    ax2.grid(axis="y", which="both", alpha=0.25)

    # Forensic class summary inset box
    fcls = diag.get("forensic_class_counts", {})
    n_qual_rows = sum(1 for r in ledger_rows if r.get("qualified_v41_laser") == "True")
    lines = ["Forensic Triage Summary:", f"Auto-qualified rows: {n_qual_rows}"]
    for k, v in list(fcls.items())[:4]:
        short_k = k[:34] + ("..." if len(k) > 34 else "")
        lines.append(f"  {short_k}: {v}")
    lines.append("Hephaistos Obj D/E & Verified ETI: 0")
    ax2.text(0.98, 0.96, "\n".join(lines), transform=ax2.transAxes, ha="right", va="top", fontsize=7.5,
             bbox=dict(boxstyle="round,pad=0.35", fc="#f8fafc", ec="#cbd5e1"))

    fig.tight_layout()
    out = FIG / "fig35_d090_thermal_ir_coverage_and_cascade.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def make_fig36(summary: dict, comp_rows: list[dict[str, str]], diag: dict) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.5))

    # Panel A: Injection-recovery completeness curves across 3 JWST instruments
    inst_styles = [
        ("JWST_NIRSPEC_G235H", "#0284c7", "o-", "NIRSpec G235H (1.66-3.07 um)"),
        ("JWST_NIRSPEC_G395H", "#d97706", "s-", "NIRSpec G395H (2.86-5.18 um)"),
        ("JWST_MIRI_MRS", "#dc2626", "^-", "MIRI MRS (4.90-28.00 um)"),
    ]
    for inst, col, fmt, lbl in inst_styles:
        for mode, ls, mtag in [("CHANNEL_T_TRANSIENT_1EPOCH", "-", "Ch. T"), ("CHANNEL_P_STATIC_COADD", "--", "Ch. P")]:
            by_sig: dict[float, list[float]] = {}
            for r in comp_rows:
                if r["instrument"] == inst and r["mode"] == mode:
                    by_sig.setdefault(float(r["sigma_mult"]), []).append(float(r["completeness"]))
            if not by_sig:
                continue
            xs = sorted(by_sig.keys())
            ys = [100.0 * np.mean(by_sig[s]) for s in xs]
            ax1.plot(xs, ys, fmt[0] + ls, color=col, lw=2.0, ms=5.5,
                     label=f"{lbl} ({mtag})")
    ax1.axvline(8.0, color="#16a34a", ls=":", lw=1.4, label="8 sigma completeness threshold")
    ax1.set_xlim(3.0, 12.6)
    ax1.set_ylim(-4.0, 108.0)
    ax1.set_xlabel("Injected Signal Amplitude (sigma)")
    ax1.set_ylabel("Recovery Completeness (%)")
    ax1.set_title("1,620 Injection-Recovery Trials Across 15 Thermal-IR Bands")
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc="lower right", fontsize=7.4, frameon=True)

    # Panel B: Gate calibration summary bars (Keplerian 135, G4/G5 216, MIRI Dual 8/8, COMB 486)
    cal = summary["synthetic_calibration_2697_trials"]
    miri = diag["miri_dual_subband_coincidence"]
    labels = [
        "Ch T >=8s\nRecov.",
        "Ch P >=8s\nRecov.",
        "Kep. T_DIFF\nBlur",
        "Kep. K_PLAN\nRecov.",
        "G45 True\nLaser",
        "G5 CR/HotPx\nReject",
        "G5 Plateau\nReject",
        "MIRI Dual\nPass (8/8)",
        "MIRI Single\nVeto (8/8)",
        "COMB v4.1\n6-Tooth",
        "COMB v4.0\nForest FPR",
        "COMB v4.1\nForest FPR",
    ]
    vals = [
        100.0 * cal["channel_t_ge_8sigma"],
        100.0 * cal["channel_p_ge_8sigma"],
        100.0 * cal["keplerian_tdiff_ge_6p5sigma"],
        100.0 * cal["keplerian_kplanet_ge_6p5sigma"],
        100.0 * cal["g45_true_laser_pass"],
        100.0 * cal["g5_cosmic_hotpx_rejection"],
        100.0 * cal["g5_plateau_rejection"],
        100.0 * miri["dual_subband_pass_count"] / max(1, miri["n_tested"]),
        100.0 * miri["single_subband_vetoed_count"] / max(1, miri["n_tested"]),
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
                 ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=32, ha="right", fontsize=7.3)
    ax2.set_ylim(0, 114)
    ax2.set_ylabel("Rate (%)")
    ax2.set_title("2,697-Trial Validation & MIRI Dual-Subband Coincidence")
    ax2.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    out = FIG / "fig36_d090_calibration_2697_and_miri_dualband.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def make_fig37(bridge_rows: list[dict[str, str]], u280_rows: list[dict[str, str]], summary: dict) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.6))

    # Panel A: Panchromatic SED-to-EIRP curves across 0.0905-28.00 um
    showcase = [
        ("BETPIC", "bet Pic (0.092-23.5 um, 8.0 oct)", "#dc2626", 2.2),
        ("EPSERI", "eps Eri (0.096-5.00 um, 5.7 oct)", "#0284c7", 2.1),
        ("16CYGB", "16 Cyg B (0.395-23.5 um + GBT)", "#059669", 2.1),
        ("HD42581", "GJ 229 (0.384-2.90 um)", "#7c3aed", 1.8),
        ("HD172555", "HD 172555 (0.240-23.5 um)", "#d97706", 1.8),
        ("HD209100", "eps Ind A (0.384-5.00 um)", "#0d9488", 1.8),
        ("PDS70", "PDS 70 (1.98-23.5 um)", "#9333ea", 1.6),
    ]
    by_star: dict[str, list[tuple[float, float]]] = {}
    for r in bridge_rows:
        by_star.setdefault(r["star"], []).append((_f(r["wave_um"]), _f(r["p_beam_10m_kw"])))
    for st, lst in by_star.items():
        if st not in {s[0] for s in showcase}:
            lst_s = sorted(lst)
            ax1.plot([x[0] for x in lst_s], [x[1] for x in lst_s], color="#cbd5e1", lw=0.9, alpha=0.8, zorder=1)
    for st, lbl, col, lw in showcase:
        lst_s = sorted(by_star.get(st, []))
        if lst_s:
            ax1.plot([x[0] for x in lst_s], [x[1] for x in lst_s], "o-", color=col, lw=lw, ms=3.5, label=lbl, zorder=4)
    ax1.axvline(10.60, color="#7f1d1d", ls="--", lw=1.2)
    ax1.text(10.60 * 0.90, 2.5e6, "10.60 um\nCO2 Laser", color="#7f1d1d", ha="right", va="top", fontsize=7.6, fontweight="bold")
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_xlim(0.08, 32.0)
    ax1.set_xlabel("Wavelength (micrometer)")
    ax1.set_ylabel("8 sigma 10 m-Transmitter Limit (kW)")
    ax1.set_title("30 Panchromatic Bridges Across 0.0905-28.00 um")
    ax1.grid(True, which="both", alpha=0.22)
    ax1.legend(loc="lower right", fontsize=7.2, frameon=True, framealpha=0.92)

    # Panel B: 280-star min_panchromatic_10m_kw vs Distance
    prior_d, prior_p = [], []
    d090_d, d090_p = [], []
    heph_d, heph_p, heph_lbl = [], [], []
    wise_pt = None
    for r in u280_rows:
        d = _f(r["dist_pc"])
        p = _f(r["min_panchromatic_10m_kw"])
        if not (np.isfinite(d) and np.isfinite(p) and p > 0):
            continue
        if r["star"] in ("OBJECT_D", "OBJECT_E"):
            heph_d.append(d)
            heph_p.append(p)
            heph_lbl.append(r["star"])
        elif r["star"] == "WISE0855":
            wise_pt = (d, p)
        elif "D090" in r.get("phases", ""):
            d090_d.append(d)
            d090_p.append(p)
        else:
            prior_d.append(d)
            prior_p.append(p)
    ax2.scatter(prior_d, prior_p, s=20, color="#64748b", alpha=0.68, label=f"D079-D089 Prior Stars ({len(prior_d)})")
    ax2.scatter(d090_d, d090_p, s=42, color="#dc2626", edgecolor="#7f1d1d", linewidth=0.6, zorder=4,
                label=f"D090 JWST IR Targets ({len(d090_d)})")
    if heph_d:
        ax2.scatter(heph_d, heph_p, s=78, marker="D", color="#7c3aed", edgecolor="black", zorder=5,
                    label="Project Hephaistos (Obj D & E)")
        for xd, xp, lb in zip(heph_d, heph_p, heph_lbl):
            ax2.annotate(lb, (xd, xp), xytext=(-6, 6), textcoords="offset points", ha="right", fontsize=7.4, fontweight="bold")
    if wise_pt:
        ax2.scatter([wise_pt[0]], [wise_pt[1]], s=75, marker="*", color="#0284c7", edgecolor="black", zorder=5,
                    label="WISE J0855-0714 (2.28 pc Y dwarf)")
        ax2.annotate("WISE0855", wise_pt, xytext=(6, 4), textcoords="offset points", fontsize=7.4, fontweight="bold", color="#0369a1")
    all_d = prior_d + d090_d + heph_d + ([wise_pt[0]] if wise_pt else [])
    d_min = min(all_d) if all_d else 1.3
    d_max = max(all_d) if all_d else 280.0
    ax2.axvline(10.0, color="#059669", ls="--", lw=1.2, label="10 pc Volume (125 unique stars)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Gaia / Trigonometric Distance (pc)")
    ax2.set_ylabel("Best Panchromatic 10 m Beam Limit (kW)")
    ax2.set_title(f"280 Unique Stars Cumulative Limits ({d_min:.1f}-{d_max:.0f} pc, 125 within 10 pc)")
    ax2.grid(True, which="both", alpha=0.22)
    ax2.legend(loc="lower right", fontsize=7.2, frameon=True, framealpha=0.92)

    fig.tight_layout()
    out = FIG / "fig37_d090_panchromatic_30bridges_and_280star_limits.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def make_fig38(allsky_comb: list[dict[str, str]], orb10: list[dict[str, str]], mm_rows: list[dict[str, str]], summary: dict) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.6, 5.5))

    # Panel A: All-sky 321-stack COMB_V4_1 sweep (D079-D090) grouped by instrument
    inst_order = []
    seen_i = set()
    for r in allsky_comb:
        ins = r["instrument"]
        if ins not in seen_i:
            seen_i.add(ins)
            inst_order.append(ins)
    v4_cnt = Counter()
    v41_cnt = Counter()
    stack_cnt = Counter()
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
    ax1.set_xlim(0, max(max(v4_vals), 10) * 8.0)
    for idx, ins in enumerate(inst_order):
        ax1.text(max(v4_vals[idx], v41_vals[idx], 0.5) * 1.18 + 0.3, idx,
                 f"n={stack_cnt[ins]} | V4={v4_cnt[ins]} -> V4.1={v41_cnt[ins]}",
                 va="center", fontsize=7.2)
    ax1.set_yticks(y)
    ax1.set_yticklabels(inst_order, fontsize=7.6)
    ax1.invert_yaxis()
    ax1.set_xlabel("Automated Comb Candidates (symlog scale)")
    ax1.set_title(f"All-Sky COMB_V4_1 Sweep: {len(allsky_comb)} Stacks (D079-D090, 0 ETI)")
    ax1.grid(axis="x", alpha=0.25)
    ax1.legend(loc="center right", fontsize=7.5)

    # Panel B: Orbital Campaigns #81-#90 (Kp vs P_orb + Multi-messenger 280 closure)
    offsets = {"BETPIC": (-6, -10), "HD163466": (7, 3), "HD2811": (7, 4), "P330E": (7, -10)}
    for r in orb10:
        per = _f(r["orbper_days"])
        kp = _f(r["kp_kms"])
        is_ctrl = r["role"] == "CONTROL"
        col = "#64748b" if is_ctrl else ("#dc2626" if r["instrument"] == "JWST_MIRI_MRS" else "#0284c7")
        mrk = "s" if is_ctrl else "o"
        ax2.scatter([per], [kp], color=col, marker=mrk, s=68, edgecolor="black", linewidth=0.7, zorder=4)
        dx, dy = offsets.get(r["star"], (6, 4))
        ha = "left" if dx > 0 else "right"
        ax2.annotate(r["star"], (per, kp), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=7.6, fontweight="bold")

    ax2.scatter([], [], color="#64748b", marker="s", s=55, edgecolor="black", label="Null Controls (#81-#83)")
    ax2.scatter([], [], color="#dc2626", marker="o", s=55, edgecolor="black", label="MIRI MRS Planets (#84-#85)")
    ax2.scatter([], [], color="#0284c7", marker="o", s=55, edgecolor="black", label="NIRSpec G395H Planets (#86-#90)")
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_xlabel("Orbital Period P_orb (days)")
    ax2.set_ylabel("Keplerian Semi-Amplitude K_p (km/s)")
    ax2.set_title("Orbital Campaigns #81-#90 (Cumulative 90/90) & Multi-Messenger Closure", fontsize=9.5)
    ax2.grid(True, which="both", alpha=0.22)
    ax2.legend(loc="upper right", fontsize=7.4)

    mm_n = len(mm_rows)
    n_radio = sum(1 for r in mm_rows if "RADIO" in r["modalities_searched"])
    n_over = sum(1 for r in mm_rows if r["multimessenger_overlap"] == "True")
    n_td = sum(int(r["qualified_tdiff_candidates"]) for r in orb10)
    n_kp = sum(int(r["qualified_kplanet_candidates"]) for r in orb10)
    box_txt = (
        f"D090 Orbital #81-#90: {n_td} T_DIFF / {n_kp} K_PLANET -> 0 ETI\n"
        f"Cumulative Orbital Campaigns: {summary['unified_280star_panchromatic_v4_1_synthesis']['cumulative_orbital_campaigns']}\n"
        f"Multi-Messenger: {mm_n} systems | 23/23 Radio Closure\n"
        f"Direct MM Overlaps: {n_over} (incl. 16CYGB Radio+Opt+MIRI)"
    )
    ax2.text(0.03, 0.04, box_txt, transform=ax2.transAxes, ha="left", va="bottom", fontsize=7.5,
             bbox=dict(boxstyle="round,pad=0.35", fc="#f8fafc", ec="#cbd5e1"))

    fig.tight_layout()
    out = FIG / "fig38_d090_allsky_comb_321stacks_and_orbital90.png"
    fig.savefig(out, dpi=220)
    plt.close(fig)
    return out


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    summary = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))
    diag = json.loads((RES / "FORENSIC_D090_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    ledger = _read_csv(RES / "V4_1_CANDIDATE_LEDGER.csv")
    comp = _read_csv(RES / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    bridges = _read_csv(RES / "PANCHROMATIC_BRIDGE_30STARS.csv")
    u280 = _read_csv(RES / "UNIFIED_PANCHROMATIC_V4_1_SYNTHESIS_280STARS.csv")
    allsky_comb = _read_csv(RES / "ALLSKY_COMB_V4_1_UNIFIED_D079_D090.csv")
    orb10 = _read_csv(RES / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    mm_rows = _read_csv(RES / "MULTIMESSENGER_ECHELLE_RADIO_TESS_280SYSTEMS.csv")

    p1 = make_fig35(summary, diag, ledger)
    p2 = make_fig36(summary, comp, diag)
    p3 = make_fig37(bridges, u280, summary)
    p4 = make_fig38(allsky_comb, orb10, mm_rows, summary)
    for p in (p1, p2, p3, p4):
        print(f"Wrote {p.name} ({p.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
