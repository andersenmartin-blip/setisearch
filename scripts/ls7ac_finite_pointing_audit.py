#!/usr/bin/env python3
"""Independent audit of LS7AC finite-displacement prediction."""
import json,math,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];L2=ROOT/"results_ls7x_l2_pilot";Z=ROOT/"results_ls7z_morphology";OUT=ROOT/"results_ls7ac_finite_pointing"
ROW=struct.Struct(">26sddddii7d4f");SIDE=list(range(171,183))+list(range(190,202));EVENT=[185,186,187]
def reg(t,y):
 t0=sum(t[i] for i in EVENT)/3; xs=[(t[i]-t0)*86400 for i in SIDE]; xe=[(t[i]-t0)*86400 for i in EVENT]; ys=[y[i] for i in SIDE]
 n=len(xs);sx=sum(xs);sxx=sum(x*x for x in xs);sy=sum(ys);sxy=sum(x*v for x,v in zip(xs,ys));det=n*sxx-sx*sx;b0=(sy*sxx-sx*sxy)/det;b1=(n*sxy-sx*sy)/det
 pred=[b0+b1*x for x in xe];return pred,[y[i]-p for i,p in zip(EVENT,pred)],[b0,b1]
def sample(P,x,y):
 x0=math.floor(x);y0=math.floor(y);x1=x0+1;y1=y0+1
 if x0<0 or y0<0 or x1>=200 or y1>=200:return None
 vals=[P[y0,x0],P[y0,x1],P[y1,x0],P[y1,x1]]
 if not all(math.isfinite(float(v)) for v in vals):return None
 fx=x-x0;fy=y-y0;a,b,c,d=map(float,vals)
 return (1-fx)*(1-fy)*a+fx*(1-fy)*b+(1-fx)*fy*c+fx*fy*d
def cosine(a,b):
 den=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b));return sum(x*y for x,y in zip(a,b))/den
def met(e,p):
 r=[a-b for a,b in zip(e,p)];e2=sum(x*x for x in e);p2=sum(x*x for x in p);r2=sum(x*x for x in r)
 return {"explained_fraction":1-r2/e2,"cosine_similarity":cosine(e,p),"prediction_rms":math.sqrt(p2/len(e)),"residual_rms":math.sqrt(r2/len(e)),"prediction_energy_fraction":p2/e2,"residual_to_event_absolute_l1_ratio":sum(abs(x) for x in r)/sum(abs(x) for x in e)}
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
  z=abs(float(a)-float(b));d[p]=max(d.get(p,0),z);assert math.isclose(float(a),float(b),rel_tol=3e-8,abs_tol=3e-6),(p,a,b);n+=1
 else:assert a==b
 return n
def main():
 saved=json.loads((OUT/"summary.json").read_text());z=json.loads((Z/"summary.json").read_text())
 rows=list(ROW.iter_unpack((L2/"lightcurve_table.bin").read_bytes()));t=[float(r[2]) for r in rows];cx=[float(r[16]) for r in rows];cy=[float(r[17]) for r in rows]
 _,dx,bx=reg(t,cx);_,dy,by=reg(t,cy);disp=list(zip(dx,dy))
 with np.load(Z/"cluster1_morphology_arrays.npz") as a:E=np.asarray(a["cor_event_excess"],float);ok=np.asarray(a["eligible"],bool);mean=np.asarray(a["sideband_mean_cor"],float)
 yy,xx=np.mgrid[0:200,0:200];expected={"event_rows":[185,186,187],"centroid_sideband_coefficients":{"x":bx,"y":by},"event_displacements":[[float(a),float(b)] for a,b in disp],"summed_displacement":[sum(dx),sum(dy)],"conventions":{}}
 for label in ("C0","C1"):
  tx,ty=map(float,z["conventions"][label]["target_center_xy"]);dist=np.sqrt((xx-tx)**2+(yy-ty)**2);ann=(dist>30)&(dist<=40)&ok&np.isfinite(mean);bg=float(np.median(mean[ann]));P=np.full((200,200),np.nan);P[ok]=mean[ok]-bg
  rec=[]; finite=[]; first=[]
  for y in range(200):
   for x in range(200):
    if dist[y,x]>25 or not ok[y,x] or not math.isfinite(float(E[y,x])) or not math.isfinite(float(P[y,x])):continue
    if x==0 or x==199 or y==0 or y==199:continue
    vx0=float(P[y,x-1]);vx1=float(P[y,x+1]);vy0=float(P[y-1,x]);vy1=float(P[y+1,x])
    if not all(math.isfinite(v) for v in [vx0,vx1,vy0,vy1]):continue
    pred=0.;valid=True
    for ddx,ddy in disp:
      q=sample(P,x-ddx,y-ddy)
      if q is None:valid=False;break
      pred+=q-float(P[y,x])
    if not valid:continue
    rec.append((y,x,float(E[y,x]),pred));first.append(-(sum(dx))*((vx1-vx0)/2)-(sum(dy))*((vy1-vy0)/2))
  ev=[q[2] for q in rec];pf=[q[3] for q in rec];mf=met(ev,pf);m1=met(ev,first);p2=sum(q*q for q in pf);alpha=sum(a*b for a,b in zip(ev,pf))/p2;sr=[a-alpha*b for a,b in zip(ev,pf)];e2=sum(a*a for a in ev)
  radial={}
  for rr in (5.,12.,25.):
   vals=[q for q in rec if dist[q[0],q[1]]<=rr];l1=sum(abs(q[2]) for q in vals)
   radial[str(int(rr))]={"pixels":len(vals),"residual_to_event_absolute_l1_ratio":sum(abs(q[2]-q[3]) for q in vals)/l1}
  expected["conventions"][label]={"pixels":len(rec),"background_annulus_median":bg,"finite_prediction":mf,"first_order_same_domain":m1,"finite_minus_first_order_explained_fraction":mf["explained_fraction"]-m1["explained_fraction"],"finite_minus_first_order_residual_rms":mf["residual_rms"]-m1["residual_rms"],"amplitude_diagnostic":{"alpha":alpha,"scaled_prediction_explained_fraction":1-sum(v*v for v in sr)/e2},"radial_residual":radial}
 target={k:saved[k] for k in ("event_rows","centroid_sideband_coefficients","event_displacements","summed_displacement","conventions")}
 d={};n=cmp(expected,target,"LS7AC",d);audit={"status":"PASS","numeric_comparisons":n,"maximum_absolute_differences":d,"method":"independent fixed-struct centroid regression, scalar bilinear interpolation and explicit pixel loops","new_archive_science_bytes":0}
 (OUT/"audit.json").write_text(json.dumps(audit,indent=2,allow_nan=False)+"\n");saved["status"]="COMPLETE_AUDITED";saved["audit_status"]="PASS";saved["audit_comparisons"]=n;(OUT/"summary.json").write_text(json.dumps(saved,indent=2,allow_nan=False)+"\n")
 (OUT/"REPORT.md").write_text((OUT/"REPORT.md").read_text().replace("Independent publication requires the LS7AC audit.",f"Independent audit: **PASS** ({n:,} numerical comparisons)."));print(json.dumps(audit,indent=2))
if __name__=="__main__":main()
