"""Prepare then execute36 fixed digital injections on DEV source-science curves."""
from pathlib import Path
import collections, copy, datetime, hashlib, itertools, json, sys
import detector
from run_development import inputs
HERE=Path(__file__).resolve().parent

def dump(name,obj):
 (HERE/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def prepare():
 assert not (HERE/'RECOVERY_PLAN.json').exists(), 'Preserve existing prospective controls'
 cfg=json.loads((HERE/'CONFIG.json').read_text())
 norm,dups=detector.normalize(inputs()['sources'],'sources',cfg)
 scored=detector.score(norm,cfg)
 eligible=[r for r in scored if r['status']=='NUMERICALLY_EVALUABLE']
 by=collections.defaultdict(list)
 for r in eligible:by[(r['object_id'],r['band'])].append(r)
 # All eligible rows retained, then deterministic identity/time order only.
 observed=sorted(eligible,key=lambda r:(int(r['object_id']),r['band'],r['time_mjd_tai'],int(r['measurement_id'])))
 gaps=[]
 for key,rs in sorted(by.items(),key=lambda p:(int(p[0][0]),p[0][1])):
  alltimes=sorted({r['time_mjd_tai']for r in norm if (r['object_id'],r['band'])==key and cfg['window_start_mjd_tai']<=r['time_mjd_tai']<cfg['window_end_mjd_tai_exclusive']})
  edges=[cfg['window_start_mjd_tai']]+alltimes+[cfg['window_end_mjd_tai_exclusive']]
  choices=sorted(zip(edges[:-1],edges[1:]),key=lambda ab:(-(ab[1]-ab[0]),ab[0]))
  a,b=choices[0]
  ref=min(rs,key=lambda r:r['time_mjd_tai'])
  for fraction in (1/3,2/3):
   gaps.append({'object_id':key[0],'band':key[1],'time_mjd_tai':a+(b-a)*fraction,
                'baseline_flux_njy':ref['baseline_flux_njy'],'baseline_reference_id':ref['measurement_id'],
                'gap_start_mjd_tai':a,'gap_end_mjd_tai':b,'gap_fraction':fraction})
 assert len(observed)>=18 and len(gaps)>=18, 'Insufficient distinct predefined placements; do not silently replace'
 cases=[];ia=ig=0
 for depth,duration in itertools.product([0.3,0.6,1.0],[60.0,3600.0,86400.0]):
  for placement in range(4):
   isgap=placement>=2
   anchor=gaps[ig]if isgap else observed[ia]
   if isgap:ig+=1
   else:ia+=1
   cases.append({'case_id':f'R{len(cases)+1:02d}','depth_mag':depth,'duration_seconds':duration,
                 'placement_kind':'gap_challenge'if isgap else 'observation_centered',
                 'object_id':anchor['object_id'],'band':anchor['band'],
                 'center_mjd_tai':anchor['time_mjd_tai'],'injection_baseline_njy':anchor['baseline_flux_njy'],
                 'baseline_reference_id':anchor.get('baseline_reference_id',anchor.get('measurement_id')),
                 'anchor_metadata':{k:anchor[k]for k in ['measurement_id','gap_start_mjd_tai','gap_end_mjd_tai','gap_fraction']if k in anchor}})
 assert len(cases)==36 and len({(r['object_id'],r['band'],r['center_mjd_tai'])for r in cases})==36
 plan={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FROZEN_BEFORE_ANY_INJECTED_CURVE_EVALUATION',
       'dev_only':True,'main_flux_read':False,'cases':cases,'total':36,'depths_mag':[0.3,0.6,1.0],
       'durations_seconds':[60.0,3600.0,86400.0],'duration_basis':'DEV source exposure times15–30s; within-band cadence about20–40s; largest between-night gapabout0.93days. Fixed durations probe one-minute,hour,andday events; no outcomes used.',
       'placement_rule':'First18 eligible DEV primary-window source rows in numeric objectID/band/time/measurementID order. Gap challenges: first18 thirds/two-thirds points of longest primary-window gap per eligible object-band pair in numeric objectID/band order, including month boundaries. Every position distinct. Eligibility means original fixed baseline sufficient; no sorting by measured depth,score,noise or injection outcome.',
       'placement_bias':'The50/50observed/gap design is a deliberate challenge set, not uniform phase sampling or a survey duty-cycle estimator. Same objects/bands are reused and are not statistically independent.',
       'injection_rule':'Subtract alpha*B*(1-10**(-0.4*depth)) from signed scienceFlux only for matchingobject/band. alpha=overlapofvisitexposurewithtop-hat/exposuretime. Retain all errors,flags,IDs,times. Rerun frozen detector including baseline eligibility.',
       'recovery_rule':'At least one newly flagged hit among measurements with positive exposure overlap and admitted by frozen quality rules; original hits at those measurements count as confounded rather than recovery. Preserve all alteredcurve target-band score rows.',
       'unchanged_control':'Same normalized original20DEV source curves; zero injectedflux; all original hits retained.',
       'eligibility_objects':len({r['object_id']for r in eligible}),'eligibility_object_band_pairs':len(by),
       'case_objects':len({r['object_id']for r in cases}),'case_object_band_pairs':len({(r['object_id'],r['band'])for r in cases}),
       'source_files':{str(p.relative_to(HERE.parent.parent)):detector.sha(p)for p in [HERE/'CONFIG.json',HERE/'detector.py',HERE/'run_development.py',HERE/'recovery_control.py',HERE.parent/'access_pilot/DEVELOPMENT_FREEZE.json',HERE.parent/'access_pilot/raw/development_sources.json',HERE.parent/'access_pilot/metadata/development_quality_supplement.json']}}
 dump('RECOVERY_PLAN.json',plan)
 print('Frozen36cases across',plan['case_objects'],'objects',plan['case_object_band_pairs'],'object-bandpairs')

def run():
 assert not (HERE/'RECOVERY_RESULTS.json').exists(),'Preserve existing control outputs'
 cfg=json.loads((HERE/'CONFIG.json').read_text());plan=json.loads((HERE/'RECOVERY_PLAN.json').read_text())
 for rel,h in plan['source_files'].items():assert detector.sha(HERE.parent.parent/rel)==h,rel
 norm,dups=detector.normalize(inputs()['sources'],'sources',cfg)
 unaltered=detector.score(norm,cfg);oldhits={r['measurement_id']for r in unaltered if r['hit']}
 results=[]
 for case in plan['cases']:
  injected=copy.deepcopy(norm);affected=[]
  half=case['duration_seconds']/86400/2
  start,end=case['center_mjd_tai']-half,case['center_mjd_tai']+half
  for row in injected:
   if (row['object_id'],row['band'])!=(case['object_id'],case['band']):continue
   if row['exposure_seconds'] is None:
    alpha = 1.0 if start <= row['time_mjd_tai'] < end else 0.0
    integration_method = 'MIDPOINT_APPROXIMATION_EXPOSURE_DURATION_UNAVAILABLE'
   else:
    expdays=row['exposure_seconds']/86400
    alpha=max(0.0,min(row['time_mjd_tai']+expdays/2,end)-max(row['time_mjd_tai']-expdays/2,start))/expdays
    alpha=min(1.0,alpha)
    integration_method = 'KNOWN_EXPOSURE_FRACTION'
   if alpha<=0:continue
   delta=alpha*case['injection_baseline_njy']*(1-10**(-0.4*case['depth_mag']))
   row['flux_njy']-=delta
   affected.append({'measurement_id':row['measurement_id'],'overlap_fraction':alpha,'integration_method':integration_method,'subtracted_njy':delta,'quality_admitted':not row['exclusion_reasons']})
  scored=detector.score(injected,cfg)
  affected_ids={r['measurement_id']for r in affected}
  newhits=[r['measurement_id']for r in scored if r['hit']and r['measurement_id']in affected_ids and r['measurement_id']not in oldhits]
  ev=[r for r in scored if r['measurement_id']in affected_ids and r['status']=='NUMERICALLY_EVALUABLE']
  if not affected:status='NO_SAMPLED_EXPOSURE'
  elif not ev:status='SAMPLED_BUT_NOT_EVALUABLE'
  elif newhits:status='RECOVERED'
  else:status='SAMPLED_EVALUABLE_MISSED'
  results.append({**case,'status':status,'recovered':bool(newhits),'affected_measurements':affected,
                  'sampled_exposures':len(affected),'evaluable_impacted_visits':len(ev),
                  'new_recovered_hit_ids':newhits,'confounded_original_hit_ids':sorted(affected_ids&oldhits),
                  'target_band_scored_rows':[r for r in scored if(r['object_id'],r['band'])==(case['object_id'],case['band'])]})
 agg=[]
 for depth,dur in itertools.product(plan['depths_mag'],plan['durations_seconds']):
  rs=[r for r in results if r['depth_mag']==depth and r['duration_seconds']==dur]
  sampled=sum(r['sampled_exposures']>0 for r in rs);evaln=sum(r['evaluable_impacted_visits']>0 for r in rs);recovered=sum(r['recovered']for r in rs)
  agg.append({'depth_mag':depth,'duration_seconds':dur,'total':len(rs),'sampled':sampled,'sampled_evaluable':evaln,'recovered':recovered,
              'unconditional_recovery':recovered/len(rs),'conditional_on_sampled_recovery':recovered/sampled if sampled else None,
              'conditional_on_sampled_evaluable_recovery':recovered/evaln if evaln else None,'status_counts':dict(collections.Counter(r['status']for r in rs))})
 summary={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'COMPLETE_36_FROZEN_DEVELOPMENT_INJECTIONS_NO_TUNING',
          'plan_sha256':detector.sha(HERE/'RECOVERY_PLAN.json'),'control_original_hits':sorted(oldhits),'total':len(results),
          'sampled':sum(r['sampled_exposures']>0 for r in results),'sampled_evaluable':sum(r['evaluable_impacted_visits']>0 for r in results),
          'recovered':sum(r['recovered']for r in results),'status_counts':dict(collections.Counter(r['status']for r in results)),
          'by_depth_duration':agg,'case_objects':plan['case_objects'],'case_object_band_pairs':plan['case_object_band_pairs'],
          'independent_trials_claimed':False,'global_sensitivity_claimed':False,'upstream_alert_completeness_measured':False,
          'quoted_errors_changed':False,'detector_config_changed_after_controls':False,'cases':results}
 dump('RECOVERY_RESULTS.json',summary)
 print(json.dumps({k:v for k,v in summary.items()if k not in ['cases','by_depth_duration']},indent=2))
if __name__=='__main__':
 {'prepare':prepare,'run':run}[sys.argv[1]]()
