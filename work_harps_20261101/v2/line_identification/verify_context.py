from pathlib import Path
import csv,json,hashlib,datetime,collections,itertools
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
P=Path(__file__).resolve().parent;B=P.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save_csv(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rows=list(csv.DictReader((P/'CANDIDATE_CONTEXT_95.csv').open()));assert len(rows)==len({r['review_id'] for r in rows})==95
plan=json.load((P/'PLAN.json').open());assert sha(B/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv')==plan['input_table_sha256']
manifest={r['dp_id']:r for r in json.load((B/'v2/acquisition/DOWNLOAD_MANIFEST.json').open())}
checks=[]
for r in rows:
 m=manifest[r['dp_id']];path=B/m['relative_path'];assert sha(path)==r['adp_sha256']==m['sha256']
 with fits.open(path) as h:
  wave=h[1].data['WAVE'][0].astype(float);flux=h[1].data['FLUX'][0].astype(float);err=h[1].data['ERR'][0].astype(float)
 center=float(r['center_bary_air_angstrom']);rest=center/(1+float(r['rvc_km_s'])/299792.458)
 assert abs(rest-float(r['approx_stellar_air_angstrom']))<1e-10
 off=wave-center;core=abs(off)<=.025;peak=abs(off)<=.06
 core_median=np.median(flux[core]);peak3=np.max(median_filter(flux,size=3,mode='nearest')[peak])
 assert np.isclose(core_median,float(r['core_median_adu']),rtol=0,atol=1e-8)
 assert np.isclose(peak3,float(r['central_median3_peak_adu']),rtol=0,atol=1e-8)
 for lo,hi in [(1,5),(3,10)]:
  level=np.percentile(flux[(abs(off)>=lo)&(abs(off)<=hi)],95)
  assert np.isclose(level,float(r[f'context_{lo}_{hi}_p95_adu']),rtol=0,atol=1e-8)
  assert np.isclose(peak3/level,float(r[f'peak_over_context_{lo}_{hi}_p95']),rtol=0,atol=1e-10)
 checks.append(dict(review_id=r['review_id'],hash_matches=True,rest_coordinate_recomputed=True,core_and_peak_recomputed=True,p95_both_scales_recomputed=True))
save_csv(P/'VERIFICATION_95.csv',checks)
pairs=list(csv.DictReader((P/'CROSS_TARGET_PROFILE_PAIRS.csv').open()));groups=json.load((P/'GROUPS_95.json').open());cs={x['cluster_id']:x for x in groups['clusters']}
pairgroups=collections.defaultdict(list)
for r in pairs:
 key=tuple(sorted([r['target1'],r['target2']]));pairgroups[key].append(r)
summary=[]
for (a,b),rr in pairgroups.items():
 if len(rr)<2:continue
 deltas=[abs(float(r['group_center_difference_angstrom']))/cs[r['cluster_id']]['rest_center']*299792.458 for r in rr]
 summary.append(dict(target1=a,target2=b,shared_feature_clusters=len(rr),cluster_ids=';'.join(r['cluster_id'] for r in rr),maximum_absolute_residual_velocity_km_s=max(deltas),median_absolute_residual_velocity_km_s=float(np.median(deltas)),interpretation='Residual after independent exposure CCF correction; descriptive agreement, not a fit or physical transition identity.'))
save_csv(P/'MULTIFEATURE_TARGET_PAIRS.csv',summary)
(P/'VERIFICATION.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checked_events=95,all_checks_passed=True,source_table_unchanged=True,all95_have_ccf_rvc=True,multifeature_target_pairs=len(summary),formal_errors='All95 saved local ERR arrays contain no finite positive uncertainty samples; no formal flux significance computed.',verification_script_sha256=sha(Path(__file__))),indent=2)+'\n')
print(json.dumps(dict(events_verified=95,pair_summaries=summary),indent=2))
