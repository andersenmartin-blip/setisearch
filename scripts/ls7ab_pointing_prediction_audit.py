#!/usr/bin/env python3
"""Independent scalar/array audit of frozen LS7AB."""
import json, math, struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
L2=ROOT/"results_ls7x_l2_pilot"; Z=ROOT/"results_ls7z_morphology"; OUT=ROOT/"results_ls7ab_pointing_prediction"
ROW=struct.Struct(">26sddddii7d4f"); SIDE=np.r_[np.arange(171,183),np.arange(190,202)]; EVENT=np.arange(185,188)
def excess(t,y):
 t0=float(np.mean(t[EVENT])); x=(t[SIDE]-t0)*86400.; xe=(t[EVENT]-t0)*86400.; ys=y[SIDE]
 n=float(len(x)); sx=float(sum(x)); sxx=float(np.dot(x,x)); sy=float(sum(ys)); sxy=float(np.dot(x,ys)); det=n*sxx-sx*sx
 b0=(sy*sxx-sx*sxy)/det; b1=(n*sxy-sx*sy)/det
 return float(sum(y[EVENT]-(b0+b1*xe)))
def cos(a,b):
 den=math.sqrt(float(np.dot(a,a))*float(np.dot(b,b))); return float(np.dot(a,b)/den) if den>0 else None
def compare(a,b,p="",d=None):
 if d is None:d={}
 n=0
 if isinstance(a,dict):
  assert set(a)==set(b),(p,set(a)^set(b))
  for k in a:n+=compare(a[k],b[k],p+"."+k,d)
 elif isinstance(a,list):
  assert len(a)==len(b)
  for i,(x,y) in enumerate(zip(a,b)):n+=compare(x,y,f"{p}[{i}]",d)
 elif isinstance(a,(bool,str)) or a is None: assert a==b,(p,a,b)
 elif isinstance(a,(int,float)):
  q=abs(float(a)-float(b));d[p]=max(d.get(p,0.),q);assert math.isclose(float(a),float(b),rel_tol=2e-9,abs_tol=2e-7),(p,a,b);n+=1
 else: assert a==b
 return n
def main():
 saved=json.loads((OUT/"summary.json").read_text()); z=json.loads((Z/"summary.json").read_text())
 rows=list(ROW.iter_unpack((L2/"lightcurve_table.bin").read_bytes())); assert len(rows)==432
 t=np.array([r[2] for r in rows],float); cx=np.array([r[16] for r in rows],float); cy=np.array([r[17] for r in rows],float)
 dl2=np.array([excess(t,cx),excess(t,cy)],float)
 with np.load(Z/"cluster1_morphology_arrays.npz") as a:
  E=np.asarray(a["cor_event_excess"],float); ok=np.asarray(a["eligible"],bool); mean=np.asarray(a["sideband_mean_cor"],float)
 expected={"l2_centroid_event_excess":[float(x) for x in dl2],"conventions":{}}
 for label in ("C0","C1"):
  tx,ty=map(float,z["conventions"][label]["target_center_xy"]); yy,xx=np.mgrid[0:200,0:200]; dist=np.sqrt((xx-tx)**2+(yy-ty)**2)
  ann=(dist>30)&(dist<=40)&ok&np.isfinite(mean); bg=float(np.median(mean[ann]))
  P=np.full((200,200),np.nan);P[ok]=mean[ok]-bg
  dx=np.full_like(P,np.nan);dy=np.full_like(P,np.nan)
  for y in range(200):
   for x in range(1,199):
    if np.isfinite(P[y,x-1]) and np.isfinite(P[y,x+1]):dx[y,x]=(P[y,x+1]-P[y,x-1])/2
  for y in range(1,199):
   for x in range(200):
    if np.isfinite(P[y-1,x]) and np.isfinite(P[y+1,x]):dy[y,x]=(P[y+1,x]-P[y-1,x])/2
  use=(dist<=25)&ok&np.isfinite(E)&np.isfinite(P)&np.isfinite(dx)&np.isfinite(dy)
  ev=E[use]; pv=-dl2[0]*dx[use]-dl2[1]*dy[use]; rv=ev-pv; e2=float(np.dot(ev,ev));p2=float(np.dot(pv,pv));r2=float(np.dot(rv,rv))
  alpha=float(np.dot(ev,pv)/p2); sr=ev-alpha*pv
  m={"pixels":int(len(ev)),"unit_prediction":{
    "explained_fraction":float(1-r2/e2),"event_rms":float(math.sqrt(e2/len(ev))),"prediction_rms":float(math.sqrt(p2/len(ev))),"residual_rms":float(math.sqrt(r2/len(ev))),
    "cosine_similarity":cos(ev,pv),"prediction_energy_fraction":float(p2/e2),
    "event_signed_sum":float(sum(ev)),"prediction_signed_sum":float(sum(pv)),"residual_signed_sum":float(sum(rv)),
    "event_absolute_l1":float(sum(abs(ev))),"prediction_absolute_l1":float(sum(abs(pv))),"residual_absolute_l1":float(sum(abs(rv))),
    "residual_cosine":{"P":cos(rv,P[use]),"Dx":cos(rv,dx[use]),"Dy":cos(rv,dy[use])}},
    "amplitude_diagnostic":{"alpha":alpha,"scaled_prediction_explained_fraction":float(1-np.dot(sr,sr)/e2),"scaled_residual_rms":float(math.sqrt(np.dot(sr,sr)/len(ev)))},
    "background_annulus_median":bg,"radial_residual":{}}
  for rr in (5.,12.,25.):
   u=use&(dist<=rr); e=E[u]; p=-dl2[0]*dx[u]-dl2[1]*dy[u]; r=e-p; l1=float(sum(abs(e)))
   m["radial_residual"][str(int(rr))]={"pixels":int(u.sum()),"residual_signed_sum":float(sum(r)),"residual_absolute_l1":float(sum(abs(r))),"event_absolute_l1":l1,"residual_to_event_absolute_l1_ratio":float(sum(abs(r))/l1)}
  expected["conventions"][label]=m
 target={"l2_centroid_event_excess":saved["l2_centroid_event_excess"],"conventions":saved["conventions"]}
 diffs={};n=compare(expected,target,"LS7AB",diffs)
 audit={"status":"PASS","numeric_comparisons":n,"maximum_absolute_differences":diffs,"method":"independent fixed-struct centroid regression plus explicit pixel-gradient prediction and residual arithmetic","new_archive_science_bytes":0}
 (OUT/"audit.json").write_text(json.dumps(audit,indent=2,allow_nan=False)+"\n")
 saved["status"]="COMPLETE_AUDITED";saved["audit_status"]="PASS";saved["audit_comparisons"]=n
 (OUT/"summary.json").write_text(json.dumps(saved,indent=2,allow_nan=False)+"\n")
 (OUT/"REPORT.md").write_text((OUT/"REPORT.md").read_text().replace("Independent publication requires the LS7AB audit.",f"Independent audit: **PASS** ({n:,} numerical comparisons)."))
 print(json.dumps(audit,indent=2))
if __name__=="__main__":main()
