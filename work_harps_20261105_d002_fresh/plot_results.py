#!/usr/bin/env python3
"""Fixed all-hit 1D atlas and controls split by target, wavelength and strength."""
import csv
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import HERE, dump, gates, sha


def main():
    gates()
    out=HERE / "figures"
    out.mkdir(exist_ok=False)
    hits=json.loads((HERE / "production/HITS.json").read_text())
    pages=[]
    for start in range(0,len(hits),12):
        fig,axes=plt.subplots(4,3,figsize=(13,12),layout="constrained")
        for ax,hit in zip(axes.flat,hits[start:start+12]):
            with np.load(HERE / "production" / hit["evidence_window"],allow_pickle=False) as z:
                w,f=z["wave"],z["flux"]
            x=w-hit["fitted_center_angstrom"]
            ax.plot(x,f,".-",color="#263b50",lw=.8,ms=2,label="Original flux")
            center=hit["fitted_center_angstrom"]
            # Exact saved sideband line is defined at the original seed, not the fitted center.
            step=float(np.median(np.diff(w)))
            background=hit["sideband_intercept_adu"]+hit["sideband_slope_adu_per_pixel"]*(w-hit["seed_wave_angstrom"])/step
            sigma=hit["fwhm_model_angstrom"]/(2*np.sqrt(2*np.log(2)))
            model=background+hit["amplitude_adu"]*np.exp(-.5*((w-center)/sigma)**2)
            ax.plot(x,model,color="#d47b20",lw=1,label="Fixed-width fit")
            ax.axvline(0,color="#999999",lw=.5)
            ax.set_xlim(-.75,.75)
            ax.set_title(f"{hit['candidate_id']} · {hit['target']}\n{center:.4f} air Å",fontsize=9)
            ax.set_xlabel("Offset from fitted barycentric center (Å)",fontsize=8)
            ax.set_ylabel("Uncalibrated ADU",fontsize=8)
            ax.tick_params(labelsize=7)
        for ax in list(axes.flat)[len(hits[start:start+12]):]:ax.set_visible(False)
        fig.suptitle("D002 · all accepted 1D triggers in fixed order · raw origin unreviewed",fontsize=13)
        name=f"MAIN_ATLAS_{len(pages)+1:02d}.png"
        fig.savefig(out / name,dpi=135)
        plt.close(fig)
        pages.append(dict(path=name,first=hits[start]["candidate_id"],last=hits[min(len(hits),start+12)-1]["candidate_id"],sha256=sha(out / name)))
    with (HERE / "controls/RECOVERY_BY_TARGET_ANCHOR_STRENGTH.csv").open() as f:
        recovery=list(csv.DictReader(f))
    targets=sorted({r["target"] for r in recovery if r["target"]!="ALL_CONTROL_TARGETS"})
    anchors=sorted({float(r["anchor_angstrom"]) for r in recovery})
    strengths=[4,8,16,32]
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout="constrained")
    for ax,target in zip(axes,targets):
        data=np.full((len(anchors),4),np.nan)
        labels={}
        for r in recovery:
            if r["target"]!=target:continue
            i,j=anchors.index(float(r["anchor_angstrom"])),strengths.index(int(r["amplitude"]))
            n,k=int(r["evaluated"]),int(r["recovered_without_control_match"])
            data[i,j]=k/n if n else np.nan
            labels[i,j]=f"{k}/{n}"+(" *" if int(r["not_evaluable"]) else "")
        image=ax.imshow(data,vmin=0,vmax=1,cmap="YlGnBu",aspect="auto")
        for (i,j),label in labels.items():ax.text(j,i,label,ha="center",va="center",color="white" if data[i,j]>.6 else "black")
        ax.set_xticks(range(4),[str(x)+"×" for x in strengths])
        ax.set_yticks(range(len(anchors)),[f"{x:.2f}" for x in anchors])
        ax.set_title(target)
        ax.set_xlabel("Added peak / original local standard deviation")
        ax.set_ylabel("Barycentric air wavelength (Å)")
    fig.suptitle("Conditional recovery without an existing control match · shared geometries",fontsize=12)
    fig.colorbar(image,ax=axes,label="Recovered / evaluable; * means incomplete support",shrink=.85)
    fig.savefig(out / "CONTROL_RECOVERY.png",dpi=150)
    plt.close(fig)
    dump(out / "INDEX.json",dict(atlas_pages=pages,all_main_hits_plotted=len(hits),
                                  control_figure="CONTROL_RECOVERY.png",control_figure_sha256=sha(out / "CONTROL_RECOVERY.png"),
                                  qualification="All original signed 1D samples retained; visual model overlays do not classify raw origin."))
    print(json.dumps(dict(main_atlas_pages=len(pages),all_main_hits_plotted=len(hits))))


if __name__=="__main__":main()
