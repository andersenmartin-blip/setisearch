"""Focused scientific boundary cases for the frozen detector; no science input."""
from pathlib import Path
import copy, datetime, json
import detector
P=Path(__file__).resolve().parent
cfg=json.loads((P/'CONFIG.json').read_text())

def record(id_,visit,t,flux=1000.0,band='g',det='1'):
 r={'r:diaSourceId':str(id_),'r:diaObjectId':'99','r:visit':str(visit),'r:detector':det,'r:band':band,
    'r:midpointMjdTai':t,'r:scienceFlux':flux,'r:scienceFluxErr':1.0,'r:exposureTime':15.0,
    'r:timeWithdrawnMjdTai':None}
 for flag in cfg['critical_source_flags']:r['r:'+flag]=False
 return r

checks=[];t=61343.1
# Four unique visits represented by five detector measurements cannot satisfy five visits.
rows=[record(i,i,t-i)for i in range(1,5)]+[record(5,1,t-1,det='2')]+[record(10,10,t,500)]
normal,dups=detector.normalize(rows,'sources',cfg)
assert all('AMBIGUOUS_MULTIPLE_MEASUREMENTS_ONE_VISIT'in r['exclusion_reasons']for r in normal if r['visit']=='1')
out=detector.score(normal,cfg);test=next(r for r in out if r['measurement_id']=='10')
assert test['status']=='NO_USABLE_BASELINE'and test['baseline_visits']==3 and not test['hit']
checks.append({'test':'four_visits_five_detector_rows_are_ineligible_and_ambiguous_visit_excluded','pass':True,'remaining_baseline_visits':3})
# Also exercise scorer alone with five already-normalized rows across four visits.
for r in normal:r['exclusion_reasons']=[]
test=next(r for r in detector.score(normal,cfg)if r['measurement_id']=='10')
assert test['baseline_visits']==4 and test['status']=='NO_USABLE_BASELINE'
checks.append({'test':'scorer_counts_visit_id_not_visit_detector_pairs','pass':True,'baseline_visits':4})
# Exactly0.3mag plus high conservative score passes; same-day/future/filter rows do not define B.
rows=[record(i,i,t-i)for i in range(1,6)]+[record(10,10,t,1000*cfg['flux_ratio_threshold']),record(11,11,t+.01,1e9),record(12,12,t-.01,1e9),record(13,13,t-1,1e9,band='r')]
normal,_=detector.normalize(rows,'sources',cfg);test=next(r for r in detector.score(normal,cfg)if r['measurement_id']=='10')
assert test['hit']and test['baseline_visits']==5 and test['baseline_flux_njy']==1000.0
assert set(test['baseline_ids'])==set(map(str,range(1,6)))
checks.append({'test':'exact_depth_boundary_and_same_day_future_other_band_exclusion','pass':True})
# Signed nonpositive flux cannot be mapped to a finite magnitude.
normal=copy.deepcopy(normal)
next(r for r in normal if r['measurement_id']=='10')['flux_njy']=-1.0
test=next(r for r in detector.score(normal,cfg)if r['measurement_id']=='10')
assert test['hit']and test['depth_mag']is None and test['nonpositive_science_estimate']
checks.append({'test':'negative_direct_flux_retained_with_null_magnitude','pass':True})
# Unknown critical flag is not false; unknown withdrawal is retained only as unknown.
r=record(100,100,t);r.pop('r:pixelFlags');r.pop('r:timeWithdrawnMjdTai')
n,_=detector.normalize([r],'sources',cfg)
assert 'UNKNOWN_FLAG_pixelFlags'in n[0]['exclusion_reasons']and'WITHDRAWAL_STATUS_UNKNOWN'in n[0]['quality_notes']
checks.append({'test':'unknown_quality_and_withdrawal_not_treated_as_pass','pass':True})
# Conflicting same-ID versions are never selected by low flux.
a=record(200,200,t);b=copy.deepcopy(a);b['r:scienceFlux']=100
n,d=detector.normalize([a,b],'sources',cfg)
assert len(n)==1 and'CONFLICTING_MEASUREMENT_ID'in n[0]['exclusion_reasons']and len(d)==1
checks.append({'test':'conflicting_duplicate_identity_excluded','pass':True})
out={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','tests_passed':len(checks),'tests':checks,'config_sha256':detector.sha(P/'CONFIG.json'),'detector_sha256':detector.sha(P/'detector.py'),'script_sha256':detector.sha(Path(__file__)),'science_rows_read':0}
(P/'BOUNDARY_VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
