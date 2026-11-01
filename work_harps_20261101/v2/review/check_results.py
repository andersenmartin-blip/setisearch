"""Separate arithmetic checks, plus fresh-process repeats; not a second human review."""
from pathlib import Path
import csv,json,math,statistics,sys,hashlib,datetime
import numpy as np
BASE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(BASE/'code'),str(BASE/'v2/code')]
from harps_detector import read_spectrum
from profile_detector import analyze_arrays
rows=list(csv.DictReader((BASE/'v2/selection/MAIN100.csv').open()))
manifest={r['dp_id']:r for r in json.loads((BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json').read_text())}
cfg=json.loads((BASE/'v2/code/CONFIG.json').read_text());checks=[];errors=[];scalar_count=0;maximum=0.
for i,r in enumerate(rows):
 path=BASE/manifest[r['dp_id']]['relative_path'];saved=json.loads((BASE/'v2/production/spectra'/(r['dp_id'].replace(':','_')+'_v2.json')).read_text())['result']
 accepted=[e for e in saved['events'] if e['status']=='PRELIMINARY_PROFILE_HIT']
 if i not in [0,24,49,74,99] and not accepted:continue
 w,f,m=read_spectrum(path)
 if i in [0,24,49,74,99]:
  repeat,_=analyze_arrays(w,f,cfg)
  assert repeat==saved,(i,r['dp_id'])
  checks.append(dict(index=i,dp_id=r['dp_id'],whole_repeat='EXACT_SEMANTIC_MATCH'))
 for e in accepted:
  k=e['seed_index'];left=[float(f[k+j]) for j in range(-50,-12)];right=[float(f[k+j]) for j in range(13,51)]
  slope=(statistics.median(right)-statistics.median(left))/63
  xx=list(range(-50,-12))+list(range(13,51));side=left+right
  intercept=statistics.median([y-slope*x for x,y in zip(xx,side)])
  residual=[y-intercept-slope*x for x,y in zip(xx,side)];mid=statistics.median(residual)
  noise=1.4826*statistics.median([abs(y-mid) for y in residual])
  core=list(range(-12,13));yy=[float(f[k+j])-intercept-slope*j for j in core]
  sigma=float(w[k])/115000/(2*math.sqrt(2*math.log(2)))
  gg=[math.exp(-.5*((float(w[k+j])-e['fitted_center_angstrom'])/sigma)**2) for j in core]
  rg=math.fsum(a*b for a,b in zip(gg,yy));g2=math.fsum(a*a for a in gg)
  amplitude=max(0.,rg/g2);cosine=rg/math.sqrt(g2*math.fsum(y*y for y in yy))
  expected=[intercept,slope,noise,amplitude,cosine,amplitude/noise]
  observed=[e[k] for k in ['sideband_intercept_adu','sideband_slope_adu_per_pixel','sideband_mad_adu','amplitude_adu','profile_cosine','amplitude_over_sideband_mad']]
  for a,b in zip(expected,observed):
   err=abs(a-b)/max(1.,abs(a));maximum=max(maximum,err);assert err<1e-9,(e,err)
  assert amplitude/noise>=6 and cosine>=.8
  scalar_count+=1
trials=list(csv.DictReader((BASE/'v2/validation/results/TRIALS.csv').open()))
assert len(trials)==192 and len({(t['background'],t['anchor_angstrom'],t['phase'],t['amplitude']) for t in trials})==192
summary=json.loads((BASE/'v2/validation/results/SUMMARY.json').read_text())
for x in summary['by_amplitude']:
 rr=[t for t in trials if float(t['amplitude'])==x['amplitude']];assert len(rr)==48
 for method in ['v1','v2']:assert sum(t[method+'_recovered']=='True' for t in rr)==x[method]
result=dict(status='PASS',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),full_exposure_repeats=checks,
 accepted_events_scalar_checked=scalar_count,maximum_relative_scalar_difference=maximum,scalar_tolerance=1e-9,
 validation_design_and_tally_check='192_unique_combinations_and_all_counts_match',
 reviewer='Primary agent; arithmetic uses Python statistics.median/math.fsum rather than detector NumPy reductions. Same-agent checks are not an independent researcher or independent complete scan of all100.',
 source_hashes={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),BASE/'v2/code/profile_detector.py',BASE/'v2/code/CONFIG.json']})
assert scalar_count==333
(BASE/'v2/review/NUMERICAL_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
