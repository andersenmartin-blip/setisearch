"""Synthetic-only normalization and temporal-baseline audit; no requests/data reads."""
from pathlib import Path
import collections,copy,datetime,hashlib,importlib.util,json,math,sys
from astropy.time import Time
from astropy.utils import iers
iers.conf.auto_download=False
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;EXT=OUT.parent;BASE=EXT.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def main():
 analyzer=module('metadata_analyzer_synthetic_audit',EXT/'analyze_metadata.py')
 detector=module('frozen_detector_synthetic_audit',BASE/'method_review/detector.py')
 plan=json.loads((EXT/'PLAN.json').read_text());config=json.loads((BASE/'method_review/CONFIG.json').read_text());method=plan['feasibility_method']
 initial={str(p.relative_to(BASE)):sha(p) for p in [EXT/'analyze_metadata.py',EXT/'PLAN.json',BASE/'method_review/detector.py',BASE/'method_review/CONFIG.json']}
 tests=[]
 def check(name,ok,detail=None):
  tests.append({'name':name,'pass':bool(ok),**({'detail':detail} if detail else {})})
 check('analyzer_plan_hash',sha(EXT/'analyze_metadata.py')==plan['analyzer_sha256'])
 frozen={r['path']:r['sha256'] for r in plan['frozen_sources']}
 check('frozen_method_hashes',all(sha(BASE/p)==frozen[p] for p in ['method_review/detector.py','method_review/CONFIG.json']))
 check('exact_method_configuration',method['critical_flags']==config['critical_source_flags']==detector.CRITICAL_SOURCE_FLAGS and method['tai_test_window']==[config['window_start_mjd_tai'],config['window_end_mjd_tai_exclusive']] and method['baseline_days']==config['baseline_lookback_days']==180 and method['min_unique_prior_visits']==config['baseline_min_unique_visits']==5 and method['min_earlier_utc_dates']==config['baseline_min_earlier_utc_dates']==3 and method['same_band'] and method['whole_test_UTC_day_excluded']==config['exclude_entire_tested_utc_date'])
 flags=method['critical_flags'];t=float(Time('2026-10-20T12:00:00',scale='utc').tai.mjd)
 def row(sid='90071992547409931',visit='80071992547409931',time=t,band='r',detector_id='4',oid='10071992547409931'):
  r={'r:diaSourceId':str(sid),'r:diaObjectId':str(oid),'r:visit':str(visit),'r:detector':str(detector_id),'r:midpointMjdTai':time,'r:band':band,'r:exposureTime':30.,'r:timeWithdrawnMjdTai':None}
  r.update({'r:'+f:False for f in flags});return r
 def compare(label,rs):
  meta,dups=analyzer.normalize_metadata(copy.deepcopy(rs),flags)
  # Explicit synthetic values solely permit frozen scorer comparison; no photometry files are read.
  synthetic=[dict(r,**{'r:scienceFlux':100.,'r:scienceFluxErr':1.}) for r in rs]
  norm,olddups=detector.normalize(synthetic,'sources',config)
  correct=len(meta)==len(norm) and len(dups)==len(olddups)
  for a,b in zip(meta,norm):
   correct &= str(a['source_id'])==b['measurement_id'] and str(a['object_id'])==b['object_id'] and str(a['visit'])==b['visit'] and str(a['detector'])==b['detector'] and a['band']==b['band'] and a['time_mjd_tai']==b['time_mjd_tai'] and a['utc_day']==b['utc_day'] and a['quality_notes']==b['quality_notes'] and a['duplicate_rows']==b['duplicate_rows'] and a['exposure_seconds']==b['exposure_seconds']
   reasons=[x.replace('CONFLICTING_MEASUREMENT_ID_METADATA','CONFLICTING_MEASUREMENT_ID') for x in a['exclusion_reasons']]
   correct &= reasons==b['exclusion_reasons']
  check(label+'_normalization_matches_frozen',correct)
  context=analyzer.temporal_context(meta,method);scores=detector.score(norm,config)
  correct=len(context)==len(scores)
  for a,b in zip(context,scores):
   correct &= str(a['source_id'])==b['measurement_id'] and [str(x) for x in a['prior_source_ids']]==b['baseline_ids'] and a['prior_visit_count']==b['baseline_visits'] and a['prior_date_count']==b['baseline_dates'] and a['temporal_quality_necessary_condition']==(b['status']=='NUMERICALLY_EVALUABLE')
  check(label+'_context_matches_frozen',correct)
  return meta,context,dups
 _,base,_=compare('clean_single',[row()]);check('single_has_no_baseline',base[0]['status']=='INSUFFICIENT_PRIOR_VISITS_OR_DATES')
 for flag in flags:
  for label,value in [('true',True),('false',False),('none',None),('zero',0),('string_false','false'),('absent',None)]:
   r=row();r.pop('r:'+flag) if label=='absent' else r.update({'r:'+flag:value})
   meta,_,_=compare('flag_'+flag+'_'+label,[r]);expected=[] if label=='false' else [('FLAG_' if label=='true' else 'UNKNOWN_FLAG_')+flag]
   check('flag_'+flag+'_'+label+'_expected',meta[0]['exclusion_reasons']==expected)
 for label,value in [('missing',None),('finite',t-1),('zero',0),('none',None),('nonfinite_string','NaN'),('boolean',True)]:
  r=row();r.pop('r:timeWithdrawnMjdTai') if label=='missing' else r.update({'r:timeWithdrawnMjdTai':value})
  meta,_,_=compare('withdrawal_'+label,[r]);check('withdrawal_'+label+'_expected',('WITHDRAWN_RECORD' in meta[0]['exclusion_reasons'])==(label in ['finite','zero']) and ('WITHDRAWAL_STATUS_UNKNOWN' in meta[0]['quality_notes'])==(label in ['missing','nonfinite_string','boolean']))
 for label,value in [('none',None),('boolean',True),('nan_string','NaN'),('inf_string','Infinity'),('bad_string','bad')]:
  r=row();r['r:midpointMjdTai']=value;meta,ctx,_=compare('bad_time_'+label,[r]);check('bad_time_'+label+'_excluded',meta[0]['exclusion_reasons']==['MISSING_OR_NONFINITE_midpointMjdTai'] and not ctx)
 for invalid in ['R','',None,'q']:
  r=row();r['r:band']=invalid;meta,_,_=compare('bad_band_'+str(invalid),[r]);check('bad_band_'+str(invalid)+'_excluded','INVALID_BAND' in meta[0]['exclusion_reasons'])
 original=row();meta,_,dups=compare('exact_duplicate',[original,copy.deepcopy(original)]);check('exact_duplicate_collapses',len(meta)==1 and len(dups)==1 and not meta[0]['exclusion_reasons'] and dups[0]['reason']=='EXACT_METADATA_DUPLICATE')
 changed=copy.deepcopy(original);changed['r:detector']='9';meta,_,dups=compare('conflicting_same_source',[original,changed]);check('conflicting_same_source_excluded',len(meta)==1 and 'CONFLICTING_MEASUREMENT_ID_METADATA' in meta[0]['exclusion_reasons'] and dups[0]['reason']=='CONFLICTING_METADATA_ID')
 for label,detector_id in [('same_detector','4'),('different_detector','9')]:
  a=row(sid='1',visit='5');b=row(sid='2',visit='5',detector_id=detector_id);meta,_,_=compare('ambiguous_'+label,[a,b]);check('ambiguous_'+label+'_all_excluded',all('AMBIGUOUS_MULTIPLE_MEASUREMENTS_ONE_VISIT' in r['exclusion_reasons'] for r in meta))
 a=row(sid='1',visit='5');b=row(sid='2',visit='5',band='g');meta,_,_=compare('same_visit_other_band',[a,b]);check('other_band_not_ambiguous',all(not r['exclusion_reasons'] for r in meta))
 a=row(sid='1',visit='5');b=row(sid='2',visit='5',oid='8');meta,_,_=compare('same_visit_other_object',[a,b]);check('other_object_not_ambiguous',all(not r['exclusion_reasons'] for r in meta))
 baseline=[row(sid=str(i+1),visit=str(i+1),time=t-d) for i,d in enumerate([10,9.9,8,7.9,6])]
 test=row(sid='100',visit='100')
 def target_case(label,rs,visits,dates,passes):
  _,ctx,_=compare(label,rs+[test]);r=next(r for r in ctx if r['source_id']=='100');check(label+'_expected_counts',r['prior_visit_count']==visits and r['prior_date_count']==dates and r['temporal_quality_necessary_condition']==passes)
  return r
 target_case('five_visits_three_dates',baseline,5,3,True)
 target_case('four_visits_three_dates',[baseline[i] for i in [0,1,2,4]],4,3,False)
 two_dates=[row(sid=str(i+1),visit=str(i+1),time=t-d) for i,d in enumerate([10,9.9,9.8,8,7.9])];target_case('five_visits_two_dates',two_dates,5,2,False)
 dupvisit=copy.deepcopy(baseline);dupvisit[1]['r:visit']=dupvisit[0]['r:visit'];dupvisit[1]['r:detector']='5';target_case('same_visit_cannot_inflate_count',dupvisit,3,2,False)
 same_day=row(sid='200',visit='200',time=float(Time('2026-10-20T00:00:01',scale='utc').tai.mjd));r=target_case('whole_test_day_exclusion',baseline+[same_day],5,3,True);check('same_day_source_not_baseline','200' not in r['prior_source_ids'])
 midnight=float(Time('2026-10-20T00:00:00',scale='utc').tai.mjd);day_before=row(sid='201',visit='201',time=midnight-1/86400);r=target_case('previous_UTC_date_last_second',baseline+[day_before],6,4,True);check('previous_UTC_date_expected','2026-10-19' in r['prior_utc_dates'])
 lower=row(sid='202',visit='202',time=t-180);outside=row(sid='203',visit='203',time=math.nextafter(t-180,-math.inf));r=target_case('180_day_lower_bound',baseline+[lower,outside],6,4,True);check('180_day_membership_exact','202' in r['prior_source_ids'] and '203' not in r['prior_source_ids'])
 future=row(sid='204',visit='204',time=t+1);equal=row(sid='205',visit='205',time=t);other_band=row(sid='206',visit='206',time=t-2,band='g');other_obj=row(sid='207',visit='207',time=t-2,oid='3');r=target_case('prior_strict_time_object_band',baseline+[future,equal,other_band,other_obj],5,3,True)
 flagged=copy.deepcopy(baseline);flagged[0]['r:pixelFlags']=True;target_case('bad_prior_removed',flagged,4,3,False)
 unknown=copy.deepcopy(baseline);unknown[0].pop('r:timeWithdrawnMjdTai');r=target_case('unknown_withdrawal_note_retained',unknown,5,3,True);check('unknown_prior_note_propagates',r['prior_quality_notes']==['WITHDRAWAL_STATUS_UNKNOWN'])
 start,end=method['tai_test_window'];window_rows=[row(sid=str(i+300),visit=str(i+300),time=x) for i,x in enumerate([math.nextafter(start,-math.inf),start,math.nextafter(end,-math.inf),end])];_,ctx,_=compare('half_open_test_window',window_rows);check('half_open_window_expected',[r['source_id'] for r in ctx]==['301','302'])
 # Exercise exact serialized identifier route used by analyzer.main.
 large=row();large['r:diaSourceId']=9223372036854775807;large['r:diaObjectId']=9223372036854775806;large['r:visit']=9223372036854775805
 parsed=json.loads(json.dumps([large]),parse_int=str);meta,_,_=compare('large_integer_JSON_parse_route',parsed);check('large_identifiers_preserved',meta[0]['source_id']=='9223372036854775807' and meta[0]['object_id']=='9223372036854775806' and meta[0]['visit']=='9223372036854775805')
 check('files_unchanged',all(sha(BASE/p)==h for p,h in initial.items()))
 result={'schema':'RUBIN_EXTENSION_METADATA_SYNTHETIC_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if all(t['pass'] for t in tests) else 'FAIL','checks_passed':sum(t['pass'] for t in tests),'checks_total':len(tests),'failures':[t for t in tests if not t['pass']],'checks':tests,'reviewed_hashes':initial,'auditor_script_sha256':sha(Path(__file__)),'science_flux_files_read':0,'network_requests':0,'synthetic_flux_values_only':True,'limitations':['Synthetic validation of metadata normalization and necessary temporal conditions only. No returned API metadata, real flux, image or Gaia rows inspected.','Canonical string identities tested through the same json.loads(parse_int=str) route used by analyzer.main; arbitrary unvalidated mixed-type identity input is outside this API path.','Metadata-identical repeats cannot reveal photometric conflicts. Passing temporal conditions does not establish baseline precision or scientific evaluability.']}
 (OUT/'SYNTHETIC_AUDIT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['checks','reviewed_hashes','limitations']},indent=2))
if __name__=='__main__':main()
