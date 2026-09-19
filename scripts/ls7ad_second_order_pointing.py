#!/usr/bin/env python3
"""Evaluate frozen LS7AD second-order pointing expansion."""
import hashlib,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
Z=ROOT/"results_ls7z_morphology"; AC=ROOT/"results_ls7ac_finite_pointing"; OUT=ROOT/"results_ls7ad_second_order_pointing"

def cos(a,b):
 d=float(np.linalg.norm(a)*np.linalg.norm(b)); return float(np.dot(a,b)/d) if d>0 else None

def metrics(e,p):
 r=e-p;e2=float(np.dot(e,e));p2=float(np.dot(p,p));r2=float(np.dot(r,r))
 alpha=float(np.dot(e,p)/p2) if p2>0 else None; sr=e-alpha*p if alpha is not None else e
 return {
  "explained_fraction":float(1-r2/e2),"cosine_similarity":cos(e,p),
  "prediction_rms":float(math.sqrt(p2/len(e))),"residual_rms":float(math.sqrt(r2/len(e))),
  "prediction_energy_fraction":float(p2/e2),
  "residual_to_event_absolute_l1_ratio":float(np.sum(np.abs(r))/np.sum(np.abs(e))),
  "amplitude_diagnostic":{"alpha":alpha,"scaled_prediction_explained_fraction":float(1-np.dot(sr,sr)/e2)}
 }

def main():
 assert not OUT.exists(),"refuse completed LS7AD overwrite"
 z=json.loads((Z/"summary.json").read_text()); ac=json.loads((AC/"summary.json").read_text())
 assert z["status"]=="COMPLETE_AUDITED" and ac["status"]=="COMPLETE_AUDITED"
 disp=np.asarray(ac["event_displacements"],float); assert disp.shape==(3,2)
 with np.load(Z/"cluster1_morphology_arrays.npz") as a:
  E=np.asarray(a["cor_event_excess"],float); ok=np.asarray(a["eligible"],bool); mean=np.asarray(a["sideband_mean_cor"],float)
 yy,xx=np.mgrid[0:200,0:200]
 result={"stage":"LS7AD_SECOND_ORDER_POINTING","status":"COMPLETE_UNAUDITED","parent_cluster":1,
 "new_archive_science_bytes":0,"other_apertures_opened":False,"raw_imagettes_opened":False,"other_visits_opened":False,
 "event_displacements":[[float(x),float(y)] for x,y in disp],"conventions":{},
 "interpretation":"fixed first-vs-second-order pointing expansion diagnostic only; no source classification"}
 arrays={}
 for label in ("C0","C1"):
  cx,cy=map(float,z["conventions"][label]["target_center_xy"]);dist=np.sqrt((xx-cx)**2+(yy-cy)**2)
  ann=(dist>30)&(dist<=40)&ok&np.isfinite(mean);bg=float(np.median(mean[ann]))
  P=np.full((200,200),np.nan);P[ok]=mean[ok]-bg
  Px=np.full_like(P,np.nan);Py=np.full_like(P,np.nan);Pxx=np.full_like(P,np.nan);Pyy=np.full_like(P,np.nan);Pxy=np.full_like(P,np.nan)
  core=np.s_[1:-1,1:-1]
  C=P[1:-1,1:-1];L=P[1:-1,:-2];R=P[1:-1,2:];U=P[:-2,1:-1];D=P[2:,1:-1]
  UL=P[:-2,:-2];UR=P[:-2,2:];DL=P[2:,:-2];DR=P[2:,2:]
  good=np.isfinite(C)&np.isfinite(L)&np.isfinite(R)&np.isfinite(U)&np.isfinite(D)&np.isfinite(UL)&np.isfinite(UR)&np.isfinite(DL)&np.isfinite(DR)
  tx=(R-L)/2;ty=(D-U)/2;txx=R-2*C+L;tyy=D-2*C+U;txy=(DR-DL-UR+UL)/4
  for arr,val in ((Px,tx),(Py,ty),(Pxx,txx),(Pyy,tyy),(Pxy,txy)):
   v=arr[core];v[good]=val[good]
  use=(dist<=25)&ok&np.isfinite(E)&np.isfinite(Px)&np.isfinite(Py)&np.isfinite(Pxx)&np.isfinite(Pyy)&np.isfinite(Pxy)
  e=E[use];e1=np.zeros(len(e));e2=np.zeros(len(e))
  for dx,dy in disp:
   first=-dx*Px[use]-dy*Py[use]
   second=first+0.5*dx*dx*Pxx[use]+dx*dy*Pxy[use]+0.5*dy*dy*Pyy[use]
   e1+=first;e2+=second
  m1=metrics(e,e1);m2=metrics(e,e2)
  res2=np.full(P.shape,np.nan);res2[use]=e-e2
  radial={}
  for rr in (5.,12.,25.):
   u=use&(dist<=rr);den=float(np.sum(np.abs(E[u])))
   radial[str(int(rr))]={"pixels":int(u.sum()),"residual_to_event_absolute_l1_ratio":float(np.sum(np.abs(res2[u]))/den) if den>0 else None}
  result["conventions"][label]={"pixels":int(use.sum()),"background_annulus_median":bg,"first_order":m1,"second_order":m2,
   "second_minus_first_explained_fraction":float(m2["explained_fraction"]-m1["explained_fraction"]),
   "second_minus_first_residual_rms":float(m2["residual_rms"]-m1["residual_rms"]),"radial_residual":radial}
  a1=np.full(P.shape,np.nan);a2=np.full(P.shape,np.nan);a1[use]=e1;a2[use]=e2
  arrays[label+"_first"]=a1;arrays[label+"_second"]=a2;arrays[label+"_mask"]=use
 OUT.mkdir();(OUT/"summary.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n");np.savez_compressed(OUT/"pointing_expansion_maps.npz",**arrays)
 lines=["# LS7AD second-order pointing expansion","","Frozen before evaluation; zero new archive science bytes.","",
 "| Convention | pixels | first explained | second explained | delta explained | first residual RMS | second residual RMS | second alpha | second scaled explained |",
 "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
 for label in ("C0","C1"):
  q=result["conventions"][label];a=q["first_order"];b=q["second_order"]
  lines.append(f"| {label} | {q['pixels']} | {a['explained_fraction']:.6g} | {b['explained_fraction']:.6g} | {q['second_minus_first_explained_fraction']:.6g} | {a['residual_rms']:.6g} | {b['residual_rms']:.6g} | {b['amplitude_diagnostic']['alpha']:.6g} | {b['amplitude_diagnostic']['scaled_prediction_explained_fraction']:.6g} |")
 lines+=["","No pointing parameter is fitted in the primary first- or second-order predictions. Independent publication requires the LS7AD audit.",""]
 (OUT/"REPORT.md").write_text("\n".join(lines));files=sorted(p for p in OUT.iterdir() if p.is_file() and p.name!="SHA256SUMS");(OUT/"SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files));print(json.dumps(result,indent=2))
if __name__=="__main__":main()
