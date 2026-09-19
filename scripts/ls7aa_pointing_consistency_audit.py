#!/usr/bin/env python3
"""Independent audit of frozen LS7AA pointing-consistency metrics."""
from __future__ import annotations
import json, math, struct
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
L2=ROOT/"results_ls7x_l2_pilot"
Z=ROOT/"results_ls7z_morphology"
OUT=ROOT/"results_ls7aa_pointing_consistency"
ROW=struct.Struct(">26sddddii7d4f")
SIDE=np.r_[np.arange(171,183),np.arange(190,202)]
EVENT=np.arange(185,188)

def line_event_excess(t,y):
    t0=float(np.mean(t[EVENT]))
    x=(t[SIDE]-t0)*86400.0
    xe=(t[EVENT]-t0)*86400.0
    ys=y[SIDE]
    n=float(len(x)); sx=float(np.sum(x)); sxx=float(np.dot(x,x))
    sy=float(np.sum(ys)); sxy=float(np.dot(x,ys))
    det=n*sxx-sx*sx
    b0=(sy*sxx-sx*sxy)/det
    b1=(n*sxy-sx*sy)/det
    pred=b0+b1*xe
    return float(np.sum(y[EVENT]-pred))

def metrics(d,l2):
    tx,ty=d; lx,ly=l2
    dx=tx-lx; dy=ty-ly
    nt=math.hypot(tx,ty); nl=math.hypot(lx,ly); nd=math.hypot(dx,dy)
    c=(tx*lx+ty*ly)/(nt*nl)
    c=max(-1.0,min(1.0,c))
    return {
      "D_template":[tx,ty],"D_L2":[lx,ly],
      "D_template_per_frame":[tx/3,ty/3],"D_L2_per_frame":[lx/3,ly/3],
      "template_norm":nt,"l2_norm":nl,
      "difference_vector":[dx,dy],"difference_norm":nd,
      "cosine_similarity":c,"angular_separation_deg":math.degrees(math.acos(c)),
      "norm_ratio_template_over_l2":nt/nl,
      "relative_vector_residual":nd/nl
    }

def compare(a,b,path="",diffs=None):
    if diffs is None: diffs={}
    count=0
    if isinstance(a,dict):
      assert set(a)==set(b),(path,set(a)^set(b))
      for k in a: count+=compare(a[k],b[k],f"{path}.{k}",diffs)
    elif isinstance(a,list):
      assert len(a)==len(b),path
      for i,(x,y) in enumerate(zip(a,b)): count+=compare(x,y,f"{path}[{i}]",diffs)
    elif isinstance(a,bool) or a is None or isinstance(a,str):
      assert a==b,(path,a,b)
    elif isinstance(a,(int,float)):
      da=abs(float(a)-float(b)); diffs[path]=max(diffs.get(path,0.0),da)
      assert math.isclose(float(a),float(b),rel_tol=5e-10,abs_tol=5e-10),(path,a,b)
      count+=1
    else:
      assert a==b
    return count

def main():
    saved=json.loads((OUT/"summary.json").read_text())
    assert saved["status"]=="COMPLETE_UNAUDITED"
    raw=(L2/"lightcurve_table.bin").read_bytes()
    rows=list(ROW.iter_unpack(raw))
    assert len(rows)==432
    t=np.array([r[2] for r in rows],float)
    # Fixed struct indices copied independently from the FITS row declaration.
    cx=np.array([r[16] for r in rows],float)
    cy=np.array([r[17] for r in rows],float)
    l2=[line_event_excess(t,cx),line_event_excess(t,cy)]
    z=json.loads((Z/"summary.json").read_text())
    expected={
      "l2_centroid_event_excess":l2,
      "conventions":{}
    }
    for label in ("C0","C1"):
      expected["conventions"][label]={}
      td=z["conventions"][label]["template_decomposition"]
      for model in ("shift","combined"):
        names=td["models"][model]["names"]; coeff=td["models"][model]["coefficients"]
        bx=float(coeff[names.index("Dx")]); by=float(coeff[names.index("Dy")])
        expected["conventions"][label][model]=metrics([-bx,-by],l2)
    target={
      "l2_centroid_event_excess":saved["l2_centroid_event_excess"],
      "conventions":saved["conventions"]
    }
    diffs={}
    n=compare(expected,target,"LS7AA",diffs)
    audit={
      "status":"PASS",
      "numeric_comparisons":n,
      "maximum_absolute_differences":diffs,
      "method":"independent fixed-struct L2 decoding, scalar sideband normal equations, and direct vector arithmetic from audited LS7Z coefficients",
      "new_archive_science_bytes":0
    }
    (OUT/"audit.json").write_text(json.dumps(audit,indent=2,allow_nan=False)+"\n")
    saved["status"]="COMPLETE_AUDITED"
    saved["audit_status"]="PASS"
    saved["audit_comparisons"]=n
    (OUT/"summary.json").write_text(json.dumps(saved,indent=2,allow_nan=False)+"\n")
    report=(OUT/"REPORT.md").read_text().replace(
      "Independent publication requires the LS7AA audit.",
      f"Independent audit: **PASS** ({n:,} numerical comparisons)."
    )
    (OUT/"REPORT.md").write_text(report)
    print(json.dumps(audit,indent=2))

if __name__=="__main__":
    main()
