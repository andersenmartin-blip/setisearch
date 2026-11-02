"""Reconstruct extension feasibility from returned metadata using independent arithmetic.

No requests or photometry files are read. Angular distances use vector cross/dot
products rather than the acquisition haversine; UTC dates use ERFA directly.
"""
from pathlib import Path
import collections, csv, datetime, hashlib, json, math
import erfa
import numpy as np

OUT=Path(__file__).resolve().parent
BASE=OUT.parent
ROOT=BASE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(name):return json.loads((BASE/name).read_text())
def raw(name):return json.loads((BASE/name).read_text(),parse_int=str)
def table(name):return list(csv.DictReader((BASE/name).open()))
def finite(value):
    try:return not isinstance(value,bool) and math.isfinite(float(value))
    except (TypeError,ValueError,OverflowError):return False
def vector(ra,dec):
    ra,dec=math.radians(float(ra)),math.radians(float(dec))
    return np.array([math.cos(dec)*math.cos(ra),math.cos(dec)*math.sin(ra),math.sin(dec)])
def angular(v,others):
    return np.degrees(np.arctan2(np.linalg.norm(np.cross(v,others),axis=1),others@v))*3600
def day(t):
    u1,u2=erfa.taiutc(2400000.5,t)
    return math.floor((u1-2400000.5)+u2)
def date(d):return (datetime.date(1858,11,17)+datetime.timedelta(days=d)).isoformat()
checks=0; failures=[]
def same(label,left,right):
    global checks
    checks+=1
    if left!=right:failures.append({'check':label,'expected':left,'observed':right})
def save(report):
    report.update(status='PASS' if not failures else 'FAIL',check_count=checks,failures=failures,
                  checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  code_sha256=sha(__file__),network_requests_made=0,
                  scope='Independent reconstruction of metadata-only necessary conditions; no science values or new selection.')
    (OUT/'RESULTS_AUDIT.json').write_text(json.dumps(report,indent=2,allow_nan=False,default=list)+'\n')
    print(json.dumps({key:report[key] for key in ['status','check_count']}))
    assert not failures,failures[:5]

plan=read('PLAN.json');pre=read('independent_review/PREFLIGHT.json')
same('Reviewed plan immutable',pre['plan_sha256'],sha(BASE/'PLAN.json'))
same('Reviewed transport immutable',pre['script_sha256'],sha(BASE/'feasibility.py'))
same('Reviewed analyzer immutable',pre['analyzer_sha256'],sha(BASE/'analyze_metadata.py'))
for source in plan['frozen_sources']:same('Frozen source '+source['path'],source['sha256'],sha(ROOT/source['path']))
cone=read('CONE_RESULT.json');summary=read('SUMMARY.json')
same('Cone attempt bound',True,len(cone['attempts'])<=2)
charged=0
for attempt in cone['attempts']:
    data=(BASE/attempt['path']).read_bytes()
    same('Cone attempt body hash',attempt['sha256'],hashlib.sha256(data).hexdigest())
    same('Cone attempt saved bytes',attempt['bytes_saved'],len(data))
    same('Cone payload fixed',plan['cone_job']['payload'],attempt['payload'])
    same('Cone bounded bytes',True,len(data)<=3000000)
    charged+=3000000 if attempt['unknown_remaining_bytes'] else len(data)
same('Cone charged bytes',charged,cone['charged_bytes'])
same('Cone charge budget',True,charged<=6000000)
same('Original188 unchanged',plan['frozen_sources'][2]['sha256'],sha(ROOT/'gaia_selection/MAIN_SELECTION.csv'))
if cone['status']!='COMPLETE':
    same('No inference after cone stop','STOPPED_BEFORE_HISTORY_NO_FEASIBILITY_CONCLUSION',summary['outcome'])
    same('No history started after cone stop',False,(BASE/'HISTORY_STARTED.json').exists())
    save({'cone_status':cone['status'],'outcome':'BOUND_AND_STOP_AUDITED_NO_FEASIBILITY_CONCLUSION'})
    raise SystemExit

rows=raw(cone['path'])
same('Cone hash',cone['sha256'],sha(BASE/cone['path']))
same('Cone row count',len(rows),cone['rows'])
same('No duplicate cone objects',len(rows),len({row['r:diaObjectId'] for row in rows}))
prior=[]
for name in ['DEVELOPMENT_SELECTION.csv','MAIN_METADATA_CANDIDATES_UNMATCHED.csv']:
    prior.extend(csv.DictReader((ROOT/'access_pilot'/name).open()))
same('Initial comparison population',433,len(prior))
priorids={row['r:diaObjectId'] for row in prior}
priorvectors=np.array([vector(row['r:ra'],row['r:dec']) for row in prior])
center=vector(plan['cone_job']['payload']['ra'],plan['cone_job']['payload']['dec'])
dispositions={row['r:diaObjectId']:row for row in table('CONE_DISPOSITIONS.csv')}
pending=[];overlap=0;position_overlap=0;max_sep=0.
for row in sorted(rows,key=lambda x:int(x['r:diaObjectId'])):
    oid=row['r:diaObjectId'];v=vector(row['r:ra'],row['r:dec'])
    same('Cone field member '+oid,True,float(angular(center,np.array([v]))[0])<=3600+3.6e-6)
    same('Valid cone coordinate '+oid,True,0<=float(row['r:ra'])<360 and -90<=float(row['r:dec'])<=90)
    separations=angular(v,priorvectors)
    near=[prior[i]['r:diaObjectId'] for i in range(len(prior)) if separations[i]<=2]
    reasons=[]
    if oid in priorids:reasons.append('EXACT_INITIAL433_ID');overlap+=1
    if near:reasons.append('WITHIN_2_ARCSEC_INITIAL433_POSITION');position_overlap+=1
    if not reasons:pending.append(oid)
    same('All near initial IDs '+oid,';'.join(near),dispositions[oid]['near_initial_ids'])
    if reasons:same('Cone exclusion '+oid,';'.join(reasons),dispositions[oid]['exclusion_reasons'])
selected=pending[:1000]
selection=table('HISTORY_SELECTION.csv')
same('Exact stable history IDs',selected,[row['r:diaObjectId'] for row in selection])
same('History cap',True,len(selected)<=1000)
same('All selected new identities',True,not(priorids&set(selected)))
for oid in pending[1000:]:same('Overflow logged '+oid,'BEYOND_FROZEN1000_ID_HISTORY_CAP',dispositions[oid]['exclusion_reasons'])
for key,value in [('initial433_exact_overlap',overlap),('position_overlap',position_overlap),('new_distinct_eligible_pool',len(pending)),('history_selected',len(selected)),('history_omitted_by_cap',max(0,len(pending)-1000))]:
    same('Cone '+key,value,cone[key]);same('Summary '+key,value,summary[key])
freeze=read('HISTORY_SELECTION_FREEZE.json')
same('Frozen history selection hash',freeze['selection_sha256'],sha(BASE/'HISTORY_SELECTION.csv'))
same('Frozen jobs hash',freeze['jobs_sha256'],sha(BASE/'HISTORY_JOBS.json'))
same('Frozen selected IDs',selected,freeze['ids'])
jobs=read('HISTORY_JOBS.json');manifest=read('HISTORY_MANIFEST.json')
same('Job cap',True,len(jobs)<=10)
same('Flattened exact jobs IDs',selected,[oid for job in jobs for oid in job['object_ids']])
history=[];idstatus={};charged=0
for job,result in zip(jobs,manifest['jobs'],strict=True):
    same('Matching job ID',job['job_id'],result['job_id'])
    same('History columns only',','.join(plan['history_columns']),job['payload']['columns'])
    same('Exact requested IDs',','.join(job['object_ids']),job['payload']['diaObjectId'])
    same('Batch bound',True,len(job['object_ids'])<=100)
    same('Attempt bound',True,len(result['attempts'])<=2)
    idstatus.update({oid:result['status'] for oid in job['object_ids']})
    for attempt in result['attempts']:
        data=(BASE/attempt['path']).read_bytes()
        same('History attempt body hash',attempt['sha256'],hashlib.sha256(data).hexdigest())
        same('History attempt saved bytes',attempt['bytes_saved'],len(data))
        same('History attempt fixed payload',job['payload'],attempt['payload'])
        same('History per-attempt byte cap',True,len(data)<=4000000)
        charged+=4000000 if attempt['unknown_remaining_bytes'] else len(data)
    if result['status']=='COMPLETE':
        same('Canonical history body hash',result['sha256'],sha(BASE/result['path']))
        incoming=raw(result['path'])
        for row in incoming:
            same('Only requested metadata fields',True,set(row)<=set(plan['history_columns']))
            same('Only requested object identity',True,row['r:diaObjectId'] in job['object_ids'])
        history.extend(incoming)
same('Charged history bytes',charged,manifest['charged_bytes'])
same('Total charged byte cap',True,charged<=20000000)
same('No outstanding reservations',0,manifest['reserved_bytes'])

groups=collections.defaultdict(list)
for index,row in enumerate(history):groups[row['r:diaSourceId']].append((index,row))
records=[];duplicates=[]
for source_id,group in groups.items():
    variants={json.dumps(row,sort_keys=True,allow_nan=False) for _,row in group}
    row=group[0][1];reasons=[];notes=[]
    if len(variants)>1:reasons.append('CONFLICTING_MEASUREMENT_ID_METADATA')
    t=float(row['r:midpointMjdTai']) if finite(row.get('r:midpointMjdTai')) else None
    if t is None:reasons.append('MISSING_OR_NONFINITE_midpointMjdTai')
    if row.get('r:band') not in list('ugrizy'):reasons.append('INVALID_BAND')
    if 'r:timeWithdrawnMjdTai' not in row:notes.append('WITHDRAWAL_STATUS_UNKNOWN')
    elif row['r:timeWithdrawnMjdTai'] is not None:
        if finite(row['r:timeWithdrawnMjdTai']):reasons.append('WITHDRAWN_RECORD')
        else:notes.append('WITHDRAWAL_STATUS_UNKNOWN')
    for flag in plan['feasibility_method']['critical_flags']:
        value=row.get('r:'+flag)
        if value is True:reasons.append('FLAG_'+flag)
        elif value is not False:reasons.append('UNKNOWN_FLAG_'+flag)
    records.append(dict(source_id=source_id,object_id=row['r:diaObjectId'],band=row.get('r:band'),visit=row['r:visit'],
                        time=t,day=day(t) if t is not None else None,reasons=reasons,notes=notes,
                        duplicates=len(group)-1,index=group[0][0]))
    for index,_ in group[1:]:duplicates.append((index,source_id,'CONFLICTING_METADATA_ID' if len(variants)>1 else 'EXACT_METADATA_DUPLICATE'))
physical=collections.defaultdict(list)
for r in records:physical[r['object_id'],r['visit'],r['band']].append(r)
for group in physical.values():
    if len(group)>1:
        for r in group:r['reasons'].append('AMBIGUOUS_MULTIPLE_MEASUREMENTS_ONE_VISIT')
records.sort(key=lambda r:(int(r['object_id']),str(r['band']),r['time'] or -1,int(r['source_id'])))
reported={r['source_id']:r for r in table('NORMALIZED_METADATA.csv')}
same('All normalized source identities',set(reported),{r['source_id'] for r in records})
for r in records:
    s=reported[r['source_id']]
    for key in ['object_id','band','visit']:same('Normalized '+key+' '+r['source_id'],r[key],s[key])
    same('Normalized exclusion '+r['source_id'],sorted(r['reasons']),sorted(json.loads(s['exclusion_reasons'])))
    same('Normalized notes '+r['source_id'],r['notes'],json.loads(s['quality_notes']))
    same('Independent UTC day '+r['source_id'],r['day'],int(s['utc_day']) if s['utc_day'] else None)
    same('Duplicate count '+r['source_id'],r['duplicates'],int(s['duplicate_rows']))
tests=[];method=plan['feasibility_method'];start,end=method['tai_test_window']
for r in records:
    if r['time'] is None or not start<=r['time']<end:continue
    context=[]
    if not r['reasons']:
        context=[other for other in records if not other['reasons'] and other['object_id']==r['object_id'] and other['band']==r['band'] and r['time']-180<=other['time']<r['time'] and other['day']<r['day']]
    visits=sorted({other['visit'] for other in context},key=int)
    dates=sorted({date(other['day']) for other in context})
    admitted=not r['reasons'] and len(visits)>=5 and len(dates)>=3
    status='EXCLUDED_METADATA_QUALITY' if r['reasons'] else 'MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION' if admitted else 'INSUFFICIENT_PRIOR_VISITS_OR_DATES'
    tests.append(dict(record=r,context=context,visits=visits,dates=dates,admitted=admitted,status=status))
reported_tests={r['source_id']:r for r in table('OCTOBER_TEMPORAL_CONTEXT.csv')}
same('Exact October identities',{t['record']['source_id'] for t in tests},set(reported_tests))
for test in tests:
    sid=test['record']['source_id'];r=reported_tests[sid]
    same('October status '+sid,test['status'],r['status'])
    same('Exact baseline source memberships '+sid,[x['source_id'] for x in test['context']],json.loads(r['prior_source_ids']))
    same('Exact distinct visit memberships '+sid,test['visits'],json.loads(r['prior_visit_ids']))
    same('Exact prior UTC dates '+sid,test['dates'],json.loads(r['prior_utc_dates']))
    same('Prior visit count '+sid,len(test['visits']),int(r['prior_visit_count']))
    same('Prior date count '+sid,len(test['dates']),int(r['prior_date_count']))
    same('Necessary condition '+sid,test['admitted'],r['temporal_quality_necessary_condition']=='True')
reported_objects={r['object_id']:r for r in table('OBJECT_FEASIBILITY.csv')}
same('All selected objects accounted',set(selected),set(reported_objects))
statuses=[]
for oid in selected:
    allrows=[r for r in records if r['object_id']==oid]
    ts=[t for t in tests if t['record']['object_id']==oid]
    good=[t for t in ts if not t['record']['reasons']]
    admitted=[t for t in ts if t['admitted']]
    status='HISTORY_UNAVAILABLE_'+idstatus[oid] if idstatus[oid]!='COMPLETE' else 'EMPTY_RETURNED_HISTORY' if not allrows else 'NO_OCTOBER_RECORD' if not ts else 'NO_QUALITY_ADMITTED_OCTOBER_RECORD' if not good else 'MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION' if admitted else 'INSUFFICIENT_PRIOR_VISITS_OR_DATES'
    statuses.append(status);observed=reported_objects[oid]
    same('Object disposition '+oid,status,observed['status'])
    for key,value in [('unique_metadata_sources',len(allrows)),('october_sources',len(ts)),('quality_admitted_october_sources',len(good)),('necessary_condition_october_sources',len(admitted)),('max_prior_visits_over_quality_admitted_october',max([len(t['visits']) for t in good],default=0)),('max_prior_dates_over_quality_admitted_october',max([len(t['dates']) for t in good],default=0))]:same('Object '+key+' '+oid,value,int(observed[key]))
    same('Object exact necessary source IDs '+oid,[t['record']['source_id'] for t in admitted],json.loads(observed['necessary_condition_source_ids']))
    same('Object exclusions '+oid,dict(collections.Counter(reason for r in allrows for reason in r['reasons'])),json.loads(observed['metadata_exclusion_reason_counts']))
necessary=sum(s=='MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION' for s in statuses)
expected={'raw_metadata_rows':len(history),'unique_metadata_sources':len(records),'duplicate_rows':len(duplicates),
          'object_status_counts':dict(collections.Counter(statuses)),
          'october_status_counts':dict(collections.Counter(t['status'] for t in tests)),
          'all_history_exclusion_reason_counts':dict(collections.Counter(reason for r in records for reason in r['reasons'])),
          'quality_note_counts':dict(collections.Counter(note for r in records for note in r['notes'])),
          'necessary_condition_objects':necessary,'necessary_condition_october_sources':sum(t['admitted'] for t in tests),
          'future_additional_main_arithmetic_ceiling':min(312,necessary),
          'unknown_history_objects':sum(idstatus[oid]!='COMPLETE' for oid in selected)}
for key,value in expected.items():same('Summary '+key,value,summary[key])
same('No new main selection',False,summary['new_main_selection_made'])
same('No Gaia query',False,summary['Gaia_queried'])
same('Future total cap',500,summary['future_total_main_cap'])
save({'cone_rows':len(rows),'selected_metadata_objects':len(selected),**expected,
      'history_charged_bytes':charged,'limitations':['Counts are necessary conditions for returned metadata only. No flux, uncertainty, baseline precision, anomaly, Gaia association, or 50-star evaluability inference follows.']})
