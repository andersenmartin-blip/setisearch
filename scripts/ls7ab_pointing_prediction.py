#!/usr/bin/env python3
"""Evaluate frozen LS7AB external pointing prediction from published bytes."""
import hashlib, json, math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
Z=ROOT/"results_ls7z_morphology"
AA=ROOT/"results_ls7aa_pointing_consistency"
OUT=ROOT/"results_ls7ab_pointing_prediction"

RADII=(5.0,12.0,25.0)

def cos(a,b):
    den=float(np.linalg.norm(a)*np.linalg.norm(b))
    return float(np.dot(a,b)/den) if den>0 else None

def metrics(E,pred,P,Dx,Dy):
    res=E-pred
    e2=float(np.dot(E,E)); p2=float(np.dot(pred,pred)); r2=float(np.dot(res,res))
    alpha=float(np.dot(E,pred)/p2) if p2>0 else None
    scaled=alpha*pred if alpha is not None else pred*0
    sr=E-scaled
    return {
      "pixels":int(len(E)),
      "unit_prediction":{
        "explained_fraction":float(1-r2/e2) if e2>0 else None,
        "event_rms":float(np.sqrt(e2/len(E))),
        "prediction_rms":float(np.sqrt(p2/len(E))),
        "residual_rms":float(np.sqrt(r2/len(E))),
        "cosine_similarity":cos(E,pred),
        "prediction_energy_fraction":float(p2/e2) if e2>0 else None,
        "event_signed_sum":float(np.sum(E)),
        "prediction_signed_sum":float(np.sum(pred)),
        "residual_signed_sum":float(np.sum(res)),
        "event_absolute_l1":float(np.sum(np.abs(E))),
        "prediction_absolute_l1":float(np.sum(np.abs(pred))),
        "residual_absolute_l1":float(np.sum(np.abs(res))),
        "residual_cosine":{"P":cos(res,P),"Dx":cos(res,Dx),"Dy":cos(res,Dy)}
      },
      "amplitude_diagnostic":{
        "alpha":alpha,
        "scaled_prediction_explained_fraction":float(1-np.dot(sr,sr)/e2) if e2>0 else None,
        "scaled_residual_rms":float(np.sqrt(np.dot(sr,sr)/len(E)))
      }
    }

def build_templates(E2,side_mean,eligible,cx,cy):
    yy,xx=np.mgrid[0:200,0:200]
    d=np.sqrt((xx-cx)**2+(yy-cy)**2)
    ann=(d>30)&(d<=40)&eligible&np.isfinite(side_mean)
    bg=float(np.median(side_mean[ann]))
    P=np.full((200,200),np.nan); P[eligible]=side_mean[eligible]-bg
    Dx=np.full_like(P,np.nan); Dy=np.full_like(P,np.nan)
    vx=np.isfinite(P[:,:-2])&np.isfinite(P[:,2:])
    vy=np.isfinite(P[:-2,:])&np.isfinite(P[2:,:])
    tmp=(P[:,2:]-P[:,:-2])/2; Dx[:,1:-1][vx]=tmp[vx]
    tmp=(P[2:,:]-P[:-2,:])/2; Dy[1:-1,:][vy]=tmp[vy]
    use=(d<=25)&eligible&np.isfinite(E2)&np.isfinite(P)&np.isfinite(Dx)&np.isfinite(Dy)
    return d,P,Dx,Dy,use,bg

def main():
    assert not OUT.exists(),"refuse completed LS7AB overwrite"
    z=json.loads((Z/"summary.json").read_text())
    aa=json.loads((AA/"summary.json").read_text())
    assert z["status"]=="COMPLETE_AUDITED" and aa["status"]=="COMPLETE_AUDITED"
    d_l2=np.asarray(aa["l2_centroid_event_excess"],float)
    with np.load(Z/"cluster1_morphology_arrays.npz") as a:
        E2=np.asarray(a["cor_event_excess"],float)
        eligible=np.asarray(a["eligible"],bool)
        side_mean=np.asarray(a["sideband_mean_cor"],float)
    result={
      "stage":"LS7AB_INDEPENDENT_POINTING_PREDICTION",
      "status":"COMPLETE_UNAUDITED","parent_cluster":1,
      "new_archive_science_bytes":0,"other_apertures_opened":False,
      "raw_imagettes_opened":False,"other_visits_opened":False,
      "l2_centroid_event_excess":[float(x) for x in d_l2],
      "conventions":{},
      "interpretation":"threshold-free external pointing prediction and residual diagnostic only"
    }
    arrays={}
    for label in ("C0","C1"):
        cx,cy=z["conventions"][label]["target_center_xy"]
        d,P,Dx,Dy,use,bg=build_templates(E2,side_mean,eligible,float(cx),float(cy))
        E=E2[use]; px=Dx[use]; py=Dy[use]; pp=P[use]
        pred=-d_l2[0]*px-d_l2[1]*py
        m=metrics(E,pred,pp,px,py)
        res2=np.full((200,200),np.nan); pred2=np.full((200,200),np.nan)
        res2[use]=E-pred; pred2[use]=pred
        radial={}
        for rr in RADII:
            u=use&(d<=rr)
            ev=E2[u]; rv=res2[u]
            l1=float(np.sum(np.abs(ev)))
            radial[str(int(rr))]={
              "pixels":int(u.sum()),"residual_signed_sum":float(np.sum(rv)),
              "residual_absolute_l1":float(np.sum(np.abs(rv))),
              "event_absolute_l1":l1,
              "residual_to_event_absolute_l1_ratio":float(np.sum(np.abs(rv))/l1) if l1>0 else None
            }
        m["background_annulus_median"]=bg
        m["radial_residual"]=radial
        result["conventions"][label]=m
        arrays[label+"_prediction"]=pred2; arrays[label+"_residual"]=res2; arrays[label+"_fit_mask"]=use
    OUT.mkdir()
    (OUT/"summary.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    np.savez_compressed(OUT/"prediction_residual_maps.npz",**arrays)
    lines=["# LS7AB independent pointing prediction","","Frozen before evaluation; zero new archive science bytes.",
           f"Independent summed L2 centroid displacement: **({d_l2[0]:.9g}, {d_l2[1]:.9g}) px**.","",
           "| Convention | external prediction explained | cos(E,pred) | prediction energy / event energy | residual RMS | alpha diagnostic | scaled explained |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for label in ("C0","C1"):
      u=result["conventions"][label]["unit_prediction"]; a=result["conventions"][label]["amplitude_diagnostic"]
      lines.append(f"| {label} | {u['explained_fraction']:.6g} | {u['cosine_similarity']:.6g} | {u['prediction_energy_fraction']:.6g} | {u['residual_rms']:.6g} | {a['alpha']:.6g} | {a['scaled_prediction_explained_fraction']:.6g} |")
    lines += ["","The unit-amplitude prediction uses only the independently measured L2 centroid excursion; alpha is reported but not applied to the primary residual.","Independent publication requires the LS7AB audit.",""]
    (OUT/"REPORT.md").write_text("\n".join(lines))
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!="SHA256SUMS")
    (OUT/"SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
