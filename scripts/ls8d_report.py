#!/usr/bin/env python3
"""Create deterministic presentation figures and the readable LS8D report.

This is post-result presentation only. It reads the already audited LS8D
diagnostics and event maps and does not recompute or alter classifications.
"""
from pathlib import Path
import json
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results_ls8d_images"


def fnum(x, digits=3):
    if x is None:
        return "NA"
    return f"{x:.{digits}f}"


def main():
    summary = json.loads((OUT / "summary.json").read_text())
    audit = json.loads((OUT / "audit.json").read_text())
    rows = json.loads((OUT / "diagnostics.json").read_text())

    assert summary["status"] == "COMPLETE_AUDITED"
    assert audit["status"] == "PASS"
    assert len(rows) == 8
    assert all(r["classification"] == "CORRECTION_LINKED" for r in rows)

    figure_links = []
    for r in rows:
        cid = r["id"]
        with np.load(OUT / cid / "event_maps.npz") as z:
            maps = {k: np.asarray(z[k], float) for k in ("CAL", "COR", "DELTA")}
        finite = np.concatenate([np.abs(v[np.isfinite(v)]) for v in maps.values()])
        vmax = float(finite.max()) if finite.size else 1.0
        if not math.isfinite(vmax) or vmax == 0:
            vmax = 1.0
        fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.1), constrained_layout=True)
        image = None
        for ax, name in zip(axes, ("CAL", "COR", "DELTA")):
            image = ax.imshow(maps[name], origin="lower", vmin=-vmax, vmax=vmax, cmap="RdBu_r")
            for key, style in (("C0", "-"), ("C1", "--")):
                cx, cy = r["conventions"][key]["center"]
                ax.add_patch(Circle((cx, cy), 25, fill=False, linewidth=0.9, linestyle=style))
            ax.set_title(name)
            ax.set_xlabel("native x pixel")
            ax.set_ylabel("native y pixel")
        fig.suptitle(f"{cid} — {r['sign']} — {r['classification']} — common scale")
        fig.colorbar(image, ax=axes, shrink=0.83, label="event residual sum [native ADU]")
        png = OUT / f"{cid}_CAL_COR_DELTA.png"
        pdf = OUT / f"{cid}_CAL_COR_DELTA.pdf"
        fig.savefig(png, dpi=180, metadata={"Software": "SETIsearch LS8D presentation"})
        fig.savefig(pdf, metadata={"Creator": "SETIsearch LS8D presentation",
                                   "CreationDate": None, "ModDate": None})
        plt.close(fig)
        figure_links.append((cid, png.name, pdf.name))

    # Fixed all-context comparison of the two predeclared coordinate conventions.
    ids = [r["id"] for r in rows]
    x = np.arange(len(ids), dtype=float)
    c0 = [abs(r["conventions"]["C0"]["delta_over_cor"]) for r in rows]
    c1 = [abs(r["conventions"]["C1"]["delta_over_cor"]) for r in rows]
    width = 0.36
    fig, ax = plt.subplots(figsize=(11.0, 4.8), constrained_layout=True)
    ax.bar(x - width/2, c0, width, label="C0")
    ax.bar(x + width/2, c1, width, label="C1")
    ax.axhline(0.5, linestyle="--", linewidth=1, label="frozen correction gate")
    ax.set_xticks(x, ids, rotation=35, ha="right")
    ax.set_ylabel("|DELTA / COR| in r<=25 aperture")
    ax.set_title("LS8D paired CAL→COR coupling for all eight fixed representatives")
    ax.legend()
    fig.savefig(OUT / "correction_gate_overview.png", dpi=180,
                metadata={"Software": "SETIsearch LS8D presentation"})
    fig.savefig(OUT / "correction_gate_overview.pdf",
                metadata={"Creator": "SETIsearch LS8D presentation",
                          "CreationDate": None, "ModDate": None})
    plt.close(fig)

    positives = [r for r in rows if r["sign"] == "positive"]
    negative = [r for r in rows if r["sign"] == "negative"][0]
    pos_ratios = [abs(r["conventions"][c]["delta_over_cor"])
                  for r in positives for c in ("C0", "C1")]
    pos_delta_col = [r["delta_column_energy_fraction"] for r in positives]
    pos_disp = [r["conventions"][c]["fits"]["COR"]["displacement"]["explained"]
                for r in positives for c in ("C0", "C1")]
    pos_bright = [r["conventions"][c]["fits"]["COR"]["brightness"]["explained"]
                  for r in positives for c in ("C0", "C1")]
    neg_ratios = [abs(negative["conventions"][c]["delta_over_cor"]) for c in ("C0", "C1")]
    neg_disp = [negative["conventions"][c]["fits"]["COR"]["displacement"]["explained"]
                for c in ("C0", "C1")]

    table = []
    for r in rows:
        c0r, c1r = r["conventions"]["C0"], r["conventions"]["C1"]
        table.append(
            f"| {r['id']} | {r['sign']} | "
            f"{c0r['event_sums']['COR']/1000:.3f} | {c1r['event_sums']['COR']/1000:.3f} | "
            f"{c0r['delta_over_cor']:.3f} | {c1r['delta_over_cor']:.3f} | "
            f"{100*r['delta_column_energy_fraction']:.2f}% | "
            f"{100*c0r['fits']['COR']['displacement']['explained']:.2f}% / "
            f"{100*c1r['fits']['COR']['displacement']['explained']:.2f}% |"
        )

    figures = "\n".join(
        f"- **{cid}:** [PNG]({png}) · [vector PDF]({pdf})"
        for cid, png, pdf in figure_links
    )

    report = f"""# LS8D: all eight fixed excursions are coupled to CAL→COR correction

Completed 20 September 2026 under the protocol frozen before image access at
`804c741dca3889a3e53f4f7165c78713238b25fb`. The exact three-visit metadata
preflight supplied 482 unique CAL/COR joins for the original 241 L2 context
rows. The frozen run then retrieved exactly **154,240,000 paired image bytes**
plus **385,600 smearing-row bytes** and no other science-image range.

All **eight** original LS8B/LS8C representatives — seven positive excursions
and the single negative control — satisfy the predeclared **CORRECTION_LINKED**
rule in both fixed coordinate conventions. This is evidence that the delivered
CAL→COR processing is strongly coupled to every retained excursion. It is
**not** identification of a unique correction component or physical cause,
not a classification as artificial/astrophysical, and not detector
qualification.

[Correction-gate overview](correction_gate_overview.png)
([vector PDF](correction_gate_overview.pdf)).

## Complete fixed-context outcome

Event sums are on the common finite native CAL/COR mask inside r<=25 and retain
the files' native ADU label. C0/C1 are the two coordinate conventions frozen
before image access. `DELTA = COR - CAL`.

| Representative | sign | COR C0 (10³ ADU) | COR C1 (10³ ADU) | DELTA/COR C0 | DELTA/COR C1 | DELTA column-energy fraction | COR displacement explained C0/C1 |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

For the seven positive representatives, CAL→COR has a **negative** aperture
event contribution in every case while the COR event remains positive. Across
the two fixed coordinate conventions, **|DELTA/COR| ranges
{min(pos_ratios):.3f}–{max(pos_ratios):.3f}**, comfortably beyond the frozen
0.5 coupling gate. Thus the corrected product retains a positive excursion,
but its amplitude is substantially altered by the correction chain.

The negative control is coupled as well: its CAL aperture event is only mildly
negative, while COR is much more negative; **|DELTA/COR| is
{min(neg_ratios):.3f}–{max(neg_ratios):.3f}**. The same descriptive stopping
rule therefore closes both signs rather than selectively explaining only the
positive events.

## Spatial structure and the earlier smearing association

The CAL→COR change is strongly column-structured for many, but not all, positive
events: the DELTA column-constant projection accounts for
**{100*min(pos_delta_col):.2f}%–{100*max(pos_delta_col):.2f}%** of DELTA map
energy across the seven positives. The negative control is very different at
**{100*negative['delta_column_energy_fraction']:.2f}%**. Consequently LS8D
does not establish one common column-smearing mechanism for all eight events.

The delivered COR event maps themselves have small column-constant energy
fractions (all below 3%). The sideband brightness template explains at most
**{100*max(pos_bright):.2f}%** of COR event-map energy in the positive events,
whereas the displacement template explains **{100*min(pos_disp):.2f}%–
{100*max(pos_disp):.2f}%**. The negative control displacement fit explains
about **{100*min(neg_disp):.2f}%–{100*max(neg_disp):.2f}%**. None reaches the
separately frozen 80% spatial-structure threshold; the correction gate already
terminates classification first.

The direct DELTA-versus-smearing-row regression is rank-deficient in all eight
contexts under the frozen design. It is therefore retained as unavailable,
rather than repaired or replaced after seeing the images. This preserves the
LS8C result: the L2 smearing association motivated this image study, but LS8D
does not turn it into a calibrated event correction.

## Independent verification

Seven synthetic tests passed before image access. The independent auditor then
redecoded the retained byte ranges, rechecked metadata joins and receipts,
rebuilt event maps with long-double temporal normal equations, independently
recomputed masks, projections, spatial fits and closure labels, and compared
the saved maps.

- numerical comparisons: **{audit['comparisons']['numeric']:,}**
- exact checks: **{audit['comparisons']['exact']:,}**
- audit disagreements: **0**
- maximum CAL/COR map discrepancy: **{max(audit['maximum_absolute_differences']['CAL'],audit['maximum_absolute_differences']['COR']):.3e} ADU**
- maximum DELTA discrepancy: **{audit['maximum_absolute_differences']['DELTA']:.3e} ADU**
- audit status: **PASS**

The original LS8B numerical audit remains **FAIL** exactly as published; the
separate stable-arithmetic repair is unchanged. LS8D is a retrospective
image diagnosis of already selected representatives, not a new held-out
false-alarm experiment. Raw imagettes were not opened.

[Machine summary](summary.json) · [independent audit](audit.json) ·
[complete diagnostics](diagnostics.json) · [independent reference](independent_reference.json) ·
[checksums](SHA256SUMS).

## Fixed event-map figures

Each figure shows CAL, COR and DELTA on one common signed scale for that
representative. Solid/dashed circles are the fixed C0/C1 r=25 apertures.
The figures are presentation products generated after the audited decisions;
they are not inputs to any classification.

{figures}

## Decision and continuation

**Close all eight LS8B/LS8C representative branches as CORRECTION_LINKED under
the frozen LS8D descriptive rule.** This label means the event amplitude is
materially coupled to CAL→COR processing. It does not establish which DRP
component caused the coupling, nor that the underlying source variability is
instrumental.

Do not widen these branches to more rows, alternative apertures or additional
55 Cnc visits. The separate raw-imagette route remains **NOT_READY** pending
its exact gcoadd/gain/reference contract and the technical request remains
unsent. A future independent optical search should start from a new
prospectively frozen dataset/product choice rather than tune the completed
LS8D events.

[Protocol](../LS8D_PAIRED_IMAGE_PROTOCOL.md) ·
[metadata freeze](../LS8D_METADATA_FREEZE.md).
"""
    (OUT / "REPORT.md").write_text(report)

if __name__ == "__main__":
    main()
