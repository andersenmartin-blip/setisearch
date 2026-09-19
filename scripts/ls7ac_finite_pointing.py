#!/usr/bin/env python3
"""Evaluate frozen LS7AC finite-displacement pointing prediction."""
import hashlib, json, math, struct
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
L2=ROOT/"results_ls7x_l2_pilot"
Z=ROOT/"results_ls7z_morphology"
AB=ROOT/"results_ls7ab_pointing_prediction"
OUT=ROOT/"results_ls7ac_finite_pointing"
ROW=struct.Struct(">26sddddii7d4f")
SIDE=np.r_[np.arange(171,183),np.arange(190,202)]
EVENT=np.arange(185,188)

def fit_predict(t,y):
    t0=float(np.mean(t[EVENT]))
    xs=(t[SIDE]-t0)*86400.; xe=(t[EVENT]-t0)*86400.
    X=np.column_stack([np.ones(len(xs)),xs]); XE=np.column_stack([np.ones(len(xe)),xe])
    beta=np.linalg.lstsq(X,y[SIDE],rcond=None)[0]
    pred=XE@beta
    return pred, y[EVENT]-pred, [float(beta[0]),float(beta[1])]

def bilinear(P,dx,dy):
    yy,xx=np.mgrid[0:P.shape[0],0:P.shape[1]]
    sx=xx-dx; sy=yy-dy
    x0=np.floor(sx).astype(int); y0=np.floor(sy).astype(int); x1=x0+1; y1=y0+1
    inb=(x0>=0)&(y0>=0)&(x1<P.shape[1])&(y1<P.shape[0])
    out=np.full(P.shape,np.nan); good=np.zeros(P.shape,bool)
    yi,xi=np.where(inb)
    if len(yi):
        a=P[y0[yi,xi],x0[yi,xi]]; b=P[y0[yi,xi],x1[yi,xi]]
        c=P[y1[yi,xi],x0[yi,xi]]; d=P[y1[yi,xi],x1[yi,xi]]
        finite=np.isfinite(a)&np.isfinite(b)&np.isfinite(c)&np.isfinite(d)
        yi=yi[finite]; xi=xi[finite]
        if len(yi):
            fx=sx[yi,xi]-x0[yi,xi]; fy=sy[yi,xi]-y0[yi,xi]
            aa=P[y0[yi,xi],x0[yi,xi]]; bb=P[y0[yi,xi],x1[yi,xi]]
            cc=P[y1[yi,xi],x0[yi,xi]]; dd=P[y1[yi,xi],x1[yi,xi]]
            out[yi,xi]=(1-fx)*(1-fy)*aa+fx*(1-fy)*bb+(1-fx)*fy*cc+fx*fy*dd
            good[yi,xi]=True
    return out,good

def cos(a,b):
    den=float(np.linalg.norm(a)*np.linalg.norm(b))
    return float(np.dot(a,b)/den) if den>0 else None

def metric(E,p):
    r=E-p; e2=float(np.dot(E,E)); p2=float(np.dot(p,p)); r2=float(np.dot(r,r))
    return {
      "explained_fraction":float(1-r2/e2),"cosine_similarity":cos(E,p),
      "prediction_rms":float(math.sqrt(p2/len(E))),"residual_rms":float(math.sqrt(r2/len(E))),
      "prediction_energy_fraction":float(p2/e2),
      "residual_to_event_absolute_l1_ratio":float(np.sum(np.abs(r))/np.sum(np.abs(E)))
    }

def main():
    assert not OUT.exists(),"refuse completed LS7AC overwrite"
    rows=list(ROW.iter_unpack((L2/"lightcurve_table.bin").read_bytes())); assert len(rows)==432
    t=np.array([r[2] for r in rows],float)
    cx=np.array([r[16] for r in rows],float); cy=np.array([r[17] for r in rows],float)
    px,dx,bx=fit_predict(t,cx); py,dy,by=fit_predict(t,cy)
    disp=np.column_stack([dx,dy])
    z=json.loads((Z/"summary.json").read_text()); ab=json.loads((AB/"summary.json").read_text())
    assert z["status"]=="COMPLETE_AUDITED" and ab["status"]=="COMPLETE_AUDITED"
    assert np.allclose(np.sum(disp,axis=0),ab["l2_centroid_event_excess"],rtol=1e-10,atol=1e-10)
    with np.load(Z/"cluster1_morphology_arrays.npz") as a:
        E2=np.asarray(a["cor_event_excess"],float); ok=np.asarray(a["eligible"],bool); mean=np.asarray(a["sideband_mean_cor"],float)
    result={
      "stage":"LS7AC_FINITE_POINTING_PREDICTION","status":"COMPLETE_UNAUDITED",
      "parent_cluster":1,"new_archive_science_bytes":0,"other_apertures_opened":False,
      "raw_imagettes_opened":False,"other_visits_opened":False,
      "event_rows":[185,186,187],
      "centroid_sideband_coefficients":{"x":bx,"y":by},
      "event_displacements":[[float(a),float(b)] for a,b in disp],
      "summed_displacement":[float(x) for x in np.sum(disp,axis=0)],
      "conventions":{},
      "interpretation":"finite-vs-first-order pointing approximation diagnostic only; no source classification"
    }
    arr={}
    yy,xx=np.mgrid[0:200,0:200]
    for label in ("C0","C1"):
        tx,ty=map(float,z["conventions"][label]["target_center_xy"])
        dist=np.sqrt((xx-tx)**2+(yy-ty)**2)
        ann=(dist>30)&(dist<=40)&ok&np.isfinite(mean); bg=float(np.median(mean[ann]))
        P=np.full((200,200),np.nan);P[ok]=mean[ok]-bg
        Dx=np.full_like(P,np.nan);Dy=np.full_like(P,np.nan)
        vx=np.isfinite(P[:,:-2])&np.isfinite(P[:,2:]); vy=np.isfinite(P[:-2,:])&np.isfinite(P[2:,:])
        tmp=(P[:,2:]-P[:,:-2])/2;Dx[:,1:-1][vx]=tmp[vx]
        tmp=(P[2:,:]-P[:-2,:])/2;Dy[1:-1,:][vy]=tmp[vy]
        finite_sum=np.zeros_like(P); valid_all=np.ones(P.shape,bool)
        for ddx,ddy in disp:
            shifted,v=bilinear(P,float(ddx),float(ddy))
            valid_all&=v
            finite_sum += np.where(np.isfinite(shifted)&np.isfinite(P),shifted-P,0.0)
        use=(dist<=25)&ok&np.isfinite(E2)&np.isfinite(P)&np.isfinite(Dx)&np.isfinite(Dy)&valid_all
        # finite_sum was accumulated only where each term was finite; valid_all enforces all terms.
        E=E2[use]; pred_f=finite_sum[use]
        sx=float(np.sum(disp[:,0])); sy=float(np.sum(disp[:,1]))
        pred_1=-sx*Dx[use]-sy*Dy[use]
        mf=metric(E,pred_f); m1=metric(E,pred_1)
        p2=float(np.dot(pred_f,pred_f)); alpha=float(np.dot(E,pred_f)/p2)
        sr=E-alpha*pred_f; e2=float(np.dot(E,E))
        radial={}
        residual2=np.full(P.shape,np.nan); residual2[use]=E-pred_f
        for rr in (5.,12.,25.):
            u=use&(dist<=rr); l1=float(np.sum(np.abs(E2[u])))
            radial[str(int(rr))]={
              "pixels":int(u.sum()),
              "residual_to_event_absolute_l1_ratio":float(np.sum(np.abs(residual2[u]))/l1) if l1>0 else None
            }
        result["conventions"][label]={
          "pixels":int(use.sum()),"background_annulus_median":bg,
          "finite_prediction":mf,"first_order_same_domain":m1,
          "finite_minus_first_order_explained_fraction":float(mf["explained_fraction"]-m1["explained_fraction"]),
          "finite_minus_first_order_residual_rms":float(mf["residual_rms"]-m1["residual_rms"]),
          "amplitude_diagnostic":{"alpha":alpha,"scaled_prediction_explained_fraction":float(1-np.dot(sr,sr)/e2)},
          "radial_residual":radial
        }
        pred2=np.full(P.shape,np.nan);pred2[use]=pred_f
        arr[label+"_finite_prediction"]=pred2;arr[label+"_common_mask"]=use;arr[label+"_residual"]=residual2
    OUT.mkdir()
    (OUT/"summary.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    np.savez_compressed(OUT/"finite_prediction_residual_maps.npz",**arr)
    lines=["# LS7AC finite-displacement pointing prediction","","Frozen before evaluation; zero new archive science bytes.",
           "The three event-frame centroid displacements are used independently with fixed bilinear interpolation.","",
           "| Convention | pixels | finite explained | first-order explained | delta explained | finite cos | finite residual RMS | alpha diagnostic | scaled explained |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for label in ("C0","C1"):
      q=result["conventions"][label];f=q["finite_prediction"];o=q["first_order_same_domain"];a=q["amplitude_diagnostic"]
      lines.append(f"| {label} | {q['pixels']} | {f['explained_fraction']:.6g} | {o['explained_fraction']:.6g} | {q['finite_minus_first_order_explained_fraction']:.6g} | {f['cosine_similarity']:.6g} | {f['residual_rms']:.6g} | {a['alpha']:.6g} | {a['scaled_prediction_explained_fraction']:.6g} |")
    lines+=["","No amplitude scale is applied to the primary finite prediction. Independent publication requires the LS7AC audit.",""]
    (OUT/"REPORT.md").write_text("\n".join(lines))
    files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!="SHA256SUMS")
    (OUT/"SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
