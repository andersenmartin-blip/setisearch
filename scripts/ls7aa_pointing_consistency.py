#!/usr/bin/env python3
"""Evaluate frozen LS7AA pointing consistency from audited LS7Z outputs only."""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
Z=ROOT/"results_ls7z_morphology"
OUT=ROOT/"results_ls7aa_pointing_consistency"

def vector_metrics(template, l2):
    tx,ty=map(float,template); lx,ly=map(float,l2)
    dn=[tx-lx,ty-ly]
    nt=math.hypot(tx,ty); nl=math.hypot(lx,ly); nd=math.hypot(*dn)
    cosine=(tx*lx+ty*ly)/(nt*nl) if nt>0 and nl>0 else None
    angle=None
    if cosine is not None:
        angle=math.degrees(math.acos(max(-1.0,min(1.0,cosine))))
    return {
      "D_template":[tx,ty],"D_L2":[lx,ly],
      "D_template_per_frame":[tx/3.0,ty/3.0],
      "D_L2_per_frame":[lx/3.0,ly/3.0],
      "template_norm":nt,"l2_norm":nl,
      "difference_vector":dn,"difference_norm":nd,
      "cosine_similarity":cosine,"angular_separation_deg":angle,
      "norm_ratio_template_over_l2":(nt/nl if nl>0 else None),
      "relative_vector_residual":(nd/nl if nl>0 else None),
    }

def main():
    assert not OUT.exists(),"refuse completed LS7AA overwrite"
    z=json.loads((Z/"summary.json").read_text())
    assert z["status"]=="COMPLETE_AUDITED"
    assert z["parent_cluster"]==1
    l2=[float(z["l2_components"]["CENTROID_X"]["event_excess"]),
        float(z["l2_components"]["CENTROID_Y"]["event_excess"])]
    result={
      "stage":"LS7AA_POINTING_CONSISTENCY",
      "status":"COMPLETE_UNAUDITED",
      "parent_stage":"LS7Z_CLUSTER1_MORPHOLOGY",
      "parent_cluster":1,
      "new_archive_science_bytes":0,
      "other_apertures_opened":False,
      "raw_imagettes_opened":False,
      "other_visits_opened":False,
      "l2_centroid_event_excess":l2,
      "conventions":{},
      "interpretation":"first-order pointing-consistency diagnostic only; no source classification or detection claim"
    }
    for label in ("C0","C1"):
        td=z["conventions"][label]["template_decomposition"]
        result["conventions"][label]={}
        for model in ("shift","combined"):
            names=td["models"][model]["names"]
            coeff=td["models"][model]["coefficients"]
            bx=float(coeff[names.index("Dx")]); by=float(coeff[names.index("Dy")])
            # Protocol: E ~= -delta_x Dx - delta_y Dy for a three-frame summed event map.
            dtemplate=[-bx,-by]
            result["conventions"][label][model]=vector_metrics(dtemplate,l2)
    OUT.mkdir()
    (OUT/"summary.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    lines=[
      "# LS7AA pointing-consistency check",
      "",
      "Frozen before evaluation. Uses only audited LS7Z and already published LS7X/LS7Y bytes.",
      "No new archive science bytes were opened.",
      "",
      f"L2 summed centroid event excess: **({l2[0]:.9g}, {l2[1]:.9g}) px**.",
      "",
      "| Convention/model | template displacement (sum px) | L2 displacement (sum px) | cosine | angle (deg) | norm ratio | relative vector residual |",
      "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for label in ("C0","C1"):
      for model in ("shift","combined"):
        m=result["conventions"][label][model]
        lines.append(
          f"| {label}/{model} | ({m['D_template'][0]:.6g}, {m['D_template'][1]:.6g}) | "
          f"({m['D_L2'][0]:.6g}, {m['D_L2'][1]:.6g}) | {m['cosine_similarity']:.6g} | "
          f"{m['angular_separation_deg']:.6g} | {m['norm_ratio_template_over_l2']:.6g} | "
          f"{m['relative_vector_residual']:.6g} |"
        )
    lines += [
      "",
      "The comparison is descriptive and threshold-free. It tests first-order consistency only.",
      "Independent publication requires the LS7AA audit.",
      ""
    ]
    (OUT/"REPORT.md").write_text("\n".join(lines))
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!="SHA256SUMS")
    (OUT/"SHA256SUMS").write_text("".join(
      f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files
    ))
    print(json.dumps(result,indent=2))

if __name__=="__main__":
    main()
