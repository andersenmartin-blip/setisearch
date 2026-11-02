"""Independent semantic boundaries for final pre-main detector; synthetic rows only."""
from pathlib import Path
import json,hashlib,datetime,copy,importlib.util
from astropy.time import Time
P=Path(__file__).resolve().parent;M=P.parent/'method_review'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 spec=importlib.util.spec_from_file_location('reviewed_rubin_detector',M/'detector.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
 cfg=json.loads((M/'CONFIG.json').read_text());freeze=json.loads((M/'METHOD_FREEZE.json').read_text())
 for p,h in freeze['source_hashes'].items():assert sha(M/p)==h,p
 assert cfg['flux_ratio_threshold']==10**(-.4*cfg['depth_mag_min']) and cfg['depth_mag_min']==.3 and cfg['conservative_deficit_score_min']==5
 checks=[]
 def mjd(day,hour=12):return float(Time(f'2026-10-{day:02d}T{hour:02d}:00:00',scale='utc').tai.mjd)
 def row(id_,visit,detector,day,flux=1000,hour=12):
  t=mjd(day,hour);return dict(measurement_id=str(id_),object_id='9007199254741999',stream='sources',band='r',visit=str(visit),detector=str(detector),time_mjd_tai=t,utc_day=d.utc_day(t),flux_njy=flux,flux_error_njy=10.,exposure_seconds=30.,quality_notes=[],exclusion_reasons=[])
 baseline=[row(i+1,i+1,1,day) for i,day in enumerate([1,2,3,4,4])];target=row(9,9,1,15,500)
 r=next(r for r in d.score(baseline+[target],cfg) if r['measurement_id']=='9');assert r['status']=='NUMERICALLY_EVALUABLE' and r['baseline_visits']==5 and r['hit'];checks.append('five_distinct_visits_four_earlier_dates_eligible')
 repeated=copy.deepcopy(baseline);repeated[-1]['visit']=repeated[-2]['visit'];repeated[-1]['detector']='2'
 r=next(r for r in d.score(repeated+[target],cfg) if r['measurement_id']=='9');assert r['baseline_visits']==4 and r['status']=='NO_USABLE_BASELINE';checks.append('four_visits_five_detector_rows_ineligible')
 same_day=row(10,10,1,15,1,hour=1);future=row(11,11,1,16,1)
 r=next(r for r in d.score(baseline+[same_day,target,future],cfg) if r['measurement_id']=='9');assert r['baseline_ids']==[str(i) for i in range(1,6)] and r['baseline_flux_njy']==1000;checks.append('same_UTC_date_and_future_rows_excluded_from_baseline')
 different_band=row(12,12,1,2,1);different_band['band']='g'
 r=next(r for r in d.score(baseline+[different_band,target],cfg) if r['measurement_id']=='9');assert r['baseline_ids']==[str(i) for i in range(1,6)];checks.append('same_band_context_only')
 two_dates=copy.deepcopy(baseline)
 for i,r in enumerate(two_dates):r['time_mjd_tai']=mjd(1+i%2);r['utc_day']=d.utc_day(r['time_mjd_tai'])
 r=next(r for r in d.score(two_dates+[target],cfg) if r['measurement_id']=='9');assert r['baseline_visits']==5 and r['baseline_dates']==2 and not r['hit'];checks.append('five_visits_only_two_dates_ineligible')
 raw=[]
 for id_,detector in [(101,1),(102,2)]:
  r={'r:diaSourceId':str(id_),'r:diaObjectId':'9007199254741999','r:visit':'99','r:detector':str(detector),'r:band':'r','r:midpointMjdTai':mjd(15),'r:scienceFlux':1000.,'r:scienceFluxErr':10.,'r:exposureTime':30.,'r:timeWithdrawnMjdTai':None}
  r.update({'r:'+k:False for k in cfg['critical_source_flags']});raw.append(r)
 n,dup=d.normalize(raw,'sources',cfg);assert len(n)==2 and all('AMBIGUOUS_MULTIPLE_MEASUREMENTS_ONE_VISIT' in r['exclusion_reasons'] for r in n);checks.append('same_object_visit_band_alternate_detectors_exclude_all')
 unknown=copy.deepcopy(raw[0]);unknown['r:pixelFlags']=None;n,_=d.normalize([unknown],'sources',cfg);assert 'UNKNOWN_FLAG_pixelFlags' in n[0]['exclusion_reasons'];checks.append('missing_primary_quality_flag_excluded')
 forced=copy.deepcopy(raw[0]);forced['r:diaForcedSourceId']=forced.pop('r:diaSourceId');n,_=d.normalize([forced],'forced',cfg);assert 'FORCED_MEASUREMENT_FLAGS_UNAVAILABLE' in n[0]['quality_notes'];checks.append('forced_stream_quality_limitation_explicit')
 assert not cfg['merge_streams'];checks.append('primary_secondary_streams_not_merged')
 assert sha(M/'detector.py')==freeze['source_hashes']['detector.py']
 report=dict(status='PASS_FINAL_METHOD_BOUNDARIES',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,checks_passed=len(checks),resolved_blocker='Distinct visit IDs now counted; multiple detector measurements for same object/visit/band all excluded.',no_main_flux_read=True,reviewed_hashes={p:sha(M/p) for p in ['detector.py','CONFIG.json','METHOD_FREEZE.json','RECOVERY_PLAN.json']},scope='Synthetic boundary checks plus code review. Independent DEV arithmetic and recovery reviewed separately by rubin_main_audit.',remaining_blockers=[],script_sha256=sha(Path(__file__)))
 (P/'DETECTOR_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
