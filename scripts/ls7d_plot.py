#!/usr/bin/env python3
"""Plot the sealed LS7D noise accounting; no detector decisions."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT/"results_ls7d_noise"
    w = json.loads((out/"windows.json").read_text())
    anchors = sorted({r["anchor"] for r in w})
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "savefig.facecolor": "white"})
    fig, axs = plt.subplots(2, 2, figsize=(12, 8.7), constrained_layout=True)
    colors = ["#167a8b", "#bd5b2a", "#6d59a6"]
    labels = ["Archived error floor", "Pixel MAD / aperture MAD", "Local / run aperture MAD"]
    keys = ["archived_error_floor", "marginal_mad_to_aperture_mad", "local_to_run_aperture_mad"]
    for key, label, color in zip(keys, labels, colors):
        values = [np.median([r["multiplicative_factors"][key] for r in w if r["anchor"] == a]) for a in anchors]
        axs[0, 0].plot(anchors, values, marker="o", label=label, color=color)
    axs[0, 0].axhline(1, color="#9ca3af", lw=.8, ls="--")
    axs[0, 0].set(title="Which factor drives the mismatch?", xlabel="Closed background anchor", ylabel="Multiplicative noise factor", ylim=(0, 7))
    axs[0, 0].legend(fontsize=8, loc="upper left")
    for stream, label, color in zip(["restored", "corrected"], ["Ground correction restored", "Mission corrected"], colors):
        values = [np.median([r[stream]["covariance_sum_to_diagonal_variance_ratio"] for r in w if r["anchor"] == a]) for a in anchors]
        axs[0, 1].plot(anchors, values, marker="o", color=color, label=label)
    axs[0, 1].axhline(1, color="#9ca3af", lw=.8, ls="--", label="No net covariance contribution")
    axs[0, 1].set(yscale="log", title="Measured covariance changes the sum", xlabel="Closed background anchor", ylabel="Aperture variance / diagonal variance", ylim=(.01, 10))
    axs[0, 1].legend(fontsize=8)
    for name, label, color in zip(["quadrature_ls7c_sigma", "quadrature_supplied_sigma", "run_aperture_mad_sigma"],
                                   ["LS7C pixel quadrature", "Archived pixel errors", "Run aperture MAD"], colors):
        values = [np.median([r[name] for r in w if r["anchor"] == a]) for a in anchors]
        axs[1, 0].plot(anchors, values, marker="o", label=label, color=color)
    axs[1, 0].set(title="Pixel noise versus summed-light noise", xlabel="Closed background anchor", ylabel="Noise scale (electrons / second)", ylim=(0, 330))
    axs[1, 0].legend(fontsize=8)
    for stream, label, color in zip(["restored", "corrected"], ["Ground correction restored", "Mission corrected"], colors):
        levels = []
        for idx, width in enumerate([1, 2, 3, 5]):
            levels.append(np.median([r["block_scales"][idx][stream+"_aperture_mad_sigma"] / r["block_scales"][0][stream+"_aperture_mad_sigma"]*np.sqrt(width) for r in w]))
        axs[1, 1].plot([20, 40, 60, 100], levels, marker="o", color=color, label=label)
    axs[1, 1].axhline(1, color="#9ca3af", lw=.8, ls="--", label="White-noise scaling reference")
    axs[1, 1].set(title="Noise scaling across pulse durations", xlabel="Block duration (seconds)", ylabel="MAD(width) × √width / MAD(1)", ylim=(0, 1.4))
    axs[1, 1].legend(fontsize=8)
    for ax in axs.flat:
        ax.grid(axis="y", alpha=.18)
    fig.suptitle("LS7D · The diagonal pixel model misses substantial noise cancellation\nL 98-59 / TESS sector 32 · 34 recorded windows in 10 shared backgrounds", fontsize=14, fontweight="bold")
    fig.savefig(out/"noise_accounting.svg")
    fig.savefig(out/"noise_accounting.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
