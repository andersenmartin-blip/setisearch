#!/usr/bin/env python3
"""Independent scalar audit of LS7AD."""
import json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];Z=ROOT/"results_ls7z_morphology";AC=ROOT/"results_ls7ac_finite_pointing";OUT=ROOT/"results_ls7ad_second_order_pointing"
def cs(a,b):
 d=math.sqrt(sum(x*x for x in a)*sum(y*y for y in b));return sum(x*y for x,y in zip(a,b))/d
def met(e,p):
 r=[a-b for a,b in zip(e,p)];e2=sum(x*x for x in e);p2=sum(x*x for x in p);r2=sum(x*x for x in r);alpha=sum(x*y for x,y in zip(e,p))/p2;sr=[x-alpha*y for x,y in zip(e,p)]
 return {"explained_fraction":1-r2/e2,"cosine_similarity":cs(e,p),"prediction_rms":math.sqrt(p2/len(e)),"residual_rms":math.sqrt(r2/len(e)),"prediction_energy_fraction":p2/e2,"residual_to_event_absolute_l1_ratio":sum(abs(x) for x in r)/sum(abs(x) for x in e),"amplitude_diagnostic":{"alpha":alpha,"scaled_prediction_explained_fraction":1-sum(x*x for x in sr)/e2}}
def cmp(a,b,p="",d=None):
 if d is None:d={}
 n=0
 if isinstance(a,dict):
  assert set(a)==set(b),(p,set(a)^set(b))
  for k in a:n+=cmp(a[k],b[k],p+"."+k,d)
 elif isinstance(a,list):
  assert len(a)==len(b)
  for i,(x,y) in enumerate(zip(a,b)):n+=cmp(x,y,f"{p}[{i}]",d)
 elif isinstance(a,(bool,str)) or a is None:assert a==b,(p,a,b)
 elif isinstance(a,(int,float)):
  z=abs(float(a)-float(b));d[p]=max(d.get(p,0),z);assert math.isclose(float(a),float(b),rel_tol=5e-8,abs_tol=5e-6),(p,a,b);n+=1
 else:assert a==b
 return n
def main():
 saved=json.loads((OUT/"summary.json").read_text());z=json.loads((Z/"summary.json").read_text());ac=json.loads((AC/"summary.json").read_text());disp=[tuple(map(float,q)) for q in ac["event_displacements"]]
 with np.load(Z/"cluster1_morphology_arrays.npz") as a:E=np.asarray(a["cor_event_excess"],float);ok=np.asarray(a["eligible"],bool);mean=np.asarray(a["sideband_mean_cor"],float)
 expected={"event_displacements":[list(q) for q in disp],"conventions":{}}
 for label in ("C0","C1"):
  cx,cy=map(float,z["conventions"][label]["target_center_xy"]);ev=[];f1=[];f2=[];coords=[];bgvals=[]
  yy,xx=np.mgrid[0:200,0:200];dist=np.sqrt((xx-cx)**2+(yy-cy)**2);ann=(dist>30)&(dist<=40)&ok&np.isfinite(mean);bg=float(np.median(mean[ann]));P=np.where(ok,mean-bg,np.nan)
  for y in range(1,199):
   for x in range(1,199):
    if dist[y,x]>25 or not ok[y,x] or not math.isfinite(float(E[y,x])):continue
    vals=[P[y,x],P[y,x-1],P[y,x+1],P[y-1,x],P[y+1,x],P[y-1,x-1],P[y-1,x+1],P[y+1,x-1],P[y+1,x+1]]
    if not all(math.isfinite(float(v)) for v in vals):continue
    c,l,r,u,d,ul,ur,dl,dr=map(float,vals);px=(r-l)/2;py=(d-u)/2;pxx=r-2*c+l;pyy=d-2*c+u;pxy=(dr-dl-ur+ul)/4
    q1=q2=0.
    for dx,dy in disp:
     a=-dx*px-dy*py;q1+=a;q2+=a+0.5*dx*dx*pxx+dx*dy*pxy+0.5*dy*dy*pyy
    ev.append(float(E[y,x]));f1.append(q1);f2.append(q2);coords.append((y,x))
  m1=met(ev,f1);m2=met(ev,f2);rad={}
  for rr in (5.,12.,25.):
   inds=[i for i,(y,x) in enumerate(coords) if dist[y,x]<=rr];den=sum(abs(ev[i]) for i in inds);rad[str(int(rr))]={"pixels":len(inds),"residual_to_event_absolute_l1_ratio":sum(abs(ev[i]-f2[i]) for i in inds)/den}
  expected["conventions"][label]={"pixels":len(ev),"background_annulus_median":bg,"first_order":m1,"second_order":m2,"second_minus_first_explained_fraction":m2["explained_fraction"]-m1["explained_fraction"],"second_minus_first_residual_rms":m2["residual_rms"]-m1["residual_rms"],"radial_residual":rad}
 target={"event_displacements":saved["event_displacements"],"conventions":saved["conventions"]};d={};n=cmp(expected,target,"LS7AD",d);audit={"status":"PASS","numeric_comparisons":n,"maximum_absolute_differences":d,"method":"explicit scalar central first/second differences and per-event centroid-driven Taylor expansion","new_archive_science_bytes":0}
 (OUT/"audit.json").write_text(json.dumps(audit,indent=2,allow_nan=False)+"\n");saved["status"]="COMPLETE_AUDITED";saved["audit_status"]="PASS";saved["audit_comparisons"]=n;(OUT/"summary.json").write_text(json.dumps(saved,indent=2,allow_nan=False)+"\n");(OUT/"REPORT.md").write_text((OUT/"REPORT.md").read_text().replace("Independent publication requires the LS7AD audit.",f"Independent audit: **PASS** ({n:,} numerical comparisons)."));print(json.dumps(audit,indent=2))
if __name__=="__main__":main()
