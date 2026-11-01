"""192 frozen paired injections on four fresh backgrounds; V1 versus V2."""
import csv,hashlib,json,sys,time,datetime
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(BASE/'code'),str(BASE/'v2/code')]
from harps_detector import read_spectrum,analyze_arrays as v1
from profile_detector import analyze_arrays as v2
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def nearest(w,c):
 d=np.abs(w-c);return int(np.flatnonzero(d<=d.min()+1e-9)[0])
def matched(r,c,k,method):
 if method=='v1':return any(e['status']=='PRELIMINARY_EMISSION_HIT' and max(e['start_index']-k,k-(e['end_index_exclusive']-1),0)<=2 for e in r['all_threshold_runs'])
 return any(e['status']=='PRELIMINARY_PROFILE_HIT' and abs(e['fitted_center_angstrom']-c)<=.02000001 for e in r['events'])
def main():
 plan=json.loads((BASE/'v2/validation/PLAN.json').read_text())
 for name,digest in plan['source_hashes'].items():assert sha(BASE/name)==digest,name
 for x in plan['backgrounds']:
  assert sha(BASE/x['path'])==x['sha256'],x['dp_id']
 out=BASE/'v2/validation/results';out.mkdir(parents=True,exist_ok=False)
 configs=[json.loads((BASE/'code/DETECTOR_CONFIG.json').read_text()),json.loads((BASE/'v2/code/CONFIG.json').read_text())]
 dump(out/'RUN_INPUTS.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha256=sha(BASE/'v2/validation/PLAN.json'),plan=plan))
 trials=[];controls=[];full=[];start=time.monotonic()
 for bi,x in enumerate(plan['backgrounds']):
  w,f,m=read_spectrum(BASE/x['path'])
  assert m['SPECSYS']=='BARYCENT' and m['wavelength_ucd']=='em.wl;obs.atmos'
  fullrow=dict(dp_id=x['dp_id'])
  for name,fun,cfg in zip(['v1','v2'],[v1,v2],configs):
   rr,_=fun(w,f,cfg);fullrow[name+'_hits']=rr['preliminary_hit_count'];dump(out/(f'background{bi}_{name}_full.json'),rr)
  full.append(fullrow)
  for ai,anchor in enumerate(plan['anchors_angstrom']):
   base=nearest(w,anchor);ww=w[base-500:base+501];ff=f[base-500:base+501]
   assert len(ww)==1001 and np.all(np.isfinite(ff)) and np.all(ff!=0)
   np.savez_compressed(out/f'background{bi}_anchor{ai}.npz',wave=ww,flux=ff)
   original=[fun(ww,ff,cfg)[0] for fun,cfg in zip([v1,v2],configs)]
   for phase in plan['phases']:
    center=float(ww[500]+phase*.01);k=nearest(ww,center);noise=float(np.std(ff[k-50:k+51],ddof=0))
    assert noise>0
    control=dict(background=bi,anchor_angstrom=anchor,phase=phase,center_angstrom=center,v1=matched(original[0],center,k,'v1'),v2=matched(original[1],center,k,'v2'))
    controls.append(control)
    for amp in plan['amplitudes']:
     sigma=center/115000/(2*np.sqrt(2*np.log(2)))
     added=amp*noise*np.exp(-.5*((ww-center)/sigma)**2);injected=ff+added
     results=[fun(ww,injected,cfg)[0] for fun,cfg in zip([v1,v2],configs)]
     row=dict(background=bi,dp_id=x['dp_id'],anchor_angstrom=anchor,phase=phase,amplitude=amp,center_angstrom=center,
      original_std_adu=noise,peak_added_adu=amp*noise,fwhm_angstrom=center/115000,
      v1_recovered=matched(results[0],center,k,'v1'),v2_recovered=matched(results[1],center,k,'v2'),
      v1_control_hit=control['v1'],v2_control_hit=control['v2'])
     trials.append(row)
     dump(out/(f'trial_{len(trials):03}.json'),dict(trial=row,v1=results[0],v2=results[1]))
 assert len(trials)==192 and len(controls)==48
 summary=dict(status='COMPLETED_NO_TUNING',evaluated_trials=len(trials),unique_unmodified_patches=16,paired_geometries=48,
  control_queries=len(controls),v1_control_matches=sum(x['v1'] for x in controls),v2_control_matches=sum(x['v2'] for x in controls),
  by_amplitude=[dict(amplitude=a,n=48,v1=sum(t['v1_recovered'] for t in trials if t['amplitude']==a),v2=sum(t['v2_recovered'] for t in trials if t['amplitude']==a)) for a in plan['amplitudes']],
  by_phase=[dict(phase=p,n=64,v1=sum(t['v1_recovered'] for t in trials if t['phase']==p),v2=sum(t['v2_recovered'] for t in trials if t['phase']==p)) for p in plan['phases']],
  full_background_counts=full,wall_seconds=time.monotonic()-start,
  limitation='Four spectra of one star; amplitudes and phases reuse backgrounds. Not independent trials, global completeness, full instrument sensitivity or calibrated false-alarm rate.')
 dump(out/'SUMMARY.json',summary);dump(out/'CONTROLS.json',controls)
 with (out/'TRIALS.csv').open('w',newline='') as h:
  writer=csv.DictWriter(h,fieldnames=list(trials[0]));writer.writeheader();writer.writerows(trials)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
