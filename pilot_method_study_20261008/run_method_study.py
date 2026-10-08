#!/usr/bin/env python3
"""Once-only exploratory method cells; no scientific import or RNG at import.

This wrapper never qualifies a telescope pilot and never overrides failed A/B.
The original scientific functions, generator and geometry are unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time
import traceback

STARTED = time.monotonic()
BASE = Path(__file__).resolve().parent.parent
CLAIMS = BASE/'pilot_protocol_20261008/method_study_claims'
OUTPUT = BASE/'results/radio_pilot_method_study_20261008'
FROZEN = {
    'detector':'1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    'dev_helpers':'d64aa962c585f536ea969fb09bcc6e16df4289f6fd4e69f396684b94bd995f49',
    'generator':'3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693',
    'contract':'44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c',
    'summarizer':'6f9153d8c598eb6bb897d0a00dc632906a00ed203c876902fca955b1b7e4b361',
    'development_cases':'1f72ab1086a2220da1617aca6dadedc66a6d121359129c90db54ede294fd41df',
    'validation_a_cases':'1edb1ab43c0ff025662de6ce7f6bd5a00cb3c902e275fa5e38d56794c1b86ad1',
    'validation_b_cases':'93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c',
    'runtime_cases':'2bef79ec3c17568243672c1ec65c9ca2baeb8066dcc4ab6842039f6d4f2a94d1',
    'a_summary':'6e270a49b9094eac26e4d02e152990869374c7f056dc4e0b63d61675d443f67c',
    'a_outcomes':'234c10b30162165e1d34c6e95a889c36e3bbb7796ac14b562f40754f14faed0c',
    'method_cases':'554a54d9ddfa1c0f82f0932ee93ba2bb652542588c65fbd4be56c144b7c4d2f4',
    'science_protocol':'a2291901ef3b197f331503d00c24e29f45038339d80c205e87797302c79afd22',
    'scope':'332639995371ddec566e6a2898829997b2a2421749bb8741e67112dd1b0f478f',
}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def durable_json(path,value,exclusive=False):
    path=Path(path);tmp=path.with_name(path.name+'.tmp')
    with (path if exclusive else tmp).open('x' if exclusive else 'w') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n');stream.flush();os.fsync(stream.fileno())
    if not exclusive:tmp.replace(path)
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,Path(path))
    if spec is None or spec.loader is None:raise ValueError('Missing original module')
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value

def check_bank(cases,panel,count):
    if len(cases)!=count or any(c['panel']!=panel for c in cases):raise ValueError('Wrong fixed bank')
    ids={c['case_id'] for c in cases};seeds={c['seed_sha256'] for c in cases}
    if len(ids)!=count or len(seeds)!=count:raise ValueError('Duplicate identity/seed')
    for c in cases:
        if f'_{panel}:' not in c['case_id'] or hashlib.sha256(c['case_id'].encode('ascii')).hexdigest()!=c['seed_sha256']:
            raise ValueError('Full SHA256 identity/seed binding required')
    return ids,seeds

def check_method_grid(cases):
    expected=set(itertools.product((10.,12.,16.,24.),(-4.,-1.25,1.25,4.),(1,3),((4,),(0,2,4))))
    observed=[]
    placements=(.25,4094.75,1024.25,3070.75)
    for index,c in enumerate(cases):
        cell=(float(c['nominal_ideal_box_score']),float(c['drift_hz_s']),
              int(c['intrinsic_width_channels']),tuple(c['active_scan_indices']))
        if (c['noise_law']!='gamma16' or c['reference_native_offset']!=placements[index%4]
            or c['family']!='method_signal' or c.get('eligibility_case') is not False
            or any(key in c for key in ('transient_row','off_only_nuisance','diagnostic_off_frequency_offset_channels'))):
            raise ValueError('Only the frozen ordinary full-row Gamma16 method cells are allowed')
        observed.append(cell)
    if len(observed)!=64 or set(observed)!=expected:raise ValueError('Exact fresh64-cell method grid required')

def admission(admission_path):
    """Read-only gate; loads only the original stdlib outcome summarizer."""
    admission_path=Path(admission_path);a=json.loads(admission_path.read_text())
    if (a.get('status') not in ('ADMITTED_METHOD_STUDY_ROLLING','ADMITTED_METHOD_STUDY_SINGLE_CASE')
        or a.get('scientific_change') is not False or a.get('qualification_override') is not False
        or a.get('telescope_values_opened') is not False or a.get('study_mode')!='EXPLORATORY_ONLY'):
        raise ValueError('Method exploration only; failed validation remains binding')
    if not re.fullmatch('[0-9a-f]{40}',a.get('public_commit_sha','')):raise ValueError('Public method freeze required')
    required={'detector','dev_helpers','generator','contract','summarizer','development_cases','validation_a_cases',
              'validation_b_cases','runtime_cases','method_cases','a_summary','a_outcomes','b_summary','b_outcomes',
              'b_resource_receipt','b_completion','b_integrity_review','scope','science_protocol','post_b_ledger','post_development_ledger'}
    if not required.issubset(a['paths']):raise ValueError('Incomplete method prerequisites')
    paths={k:(Path(v) if Path(v).is_absolute() else admission_path.parent/v).resolve() for k,v in a['paths'].items()}
    hashes={k:digest(p) for k,p in paths.items()}
    for key,value in hashes.items():
        if a['sha256'].get(key)!=value or (key in FROZEN and FROZEN[key]!=value):raise ValueError('Prerequisite changed: '+key)
    if a['sha256'].get('runner')!=digest(Path(__file__)):raise ValueError('Method worker not frozen')
    expected_paths={'detector':BASE/'pilot_engine_20261008/detector.py',
        'dev_helpers':BASE/'pilot_engine_20261008/run_dev.py','generator':BASE/'pilot_controls_20261008/generator.py',
        'contract':BASE/'pilot_controls_20261008/control_contract.json','summarizer':BASE/'pilot_controls_20261008/summarize.py'}
    if any(paths[k]!=p for k,p in expected_paths.items()):raise ValueError('Use unchanged original science files')
    banks={k:json.loads(paths[k].read_text()) for k in ('development_cases','validation_a_cases','validation_b_cases','runtime_cases','method_cases')}
    sets=[check_bank(banks[key],panel,count) for key,panel,count in
        (('development_cases','DEV',24),('validation_a_cases','VAL_A',142),('validation_b_cases','VAL_B',142),
         ('runtime_cases','DEV_RUNTIME',2),('method_cases','METHOD_STUDY',64))]
    for i in range(len(sets)):
        for j in range(i+1,len(sets)):
            if sets[i][0]&sets[j][0] or sets[i][1]&sets[j][1]:raise ValueError('Method seeds/IDs overlap historical banks')
    check_method_grid(banks['method_cases'])
    summarizer=load(paths['summarizer'],'original_method_prerequisite_summarizer')
    for panel,prefix,bank in (('VAL_A','a','validation_a_cases'),('VAL_B','b','validation_b_cases')):
        outcomes=json.loads(paths[prefix+'_outcomes'].read_text());summary=json.loads(paths[prefix+'_summary'].read_text())
        if summarizer.summarize(banks[bank],outcomes,panel)!=summary:raise ValueError('Closed failed validation evidence differs')
        if summary['scientific_gate']!='FAIL_CLOSED' or summary['case_count_observed']!=142:
            raise ValueError('Both complete closed A and B must remain failed before method generation')
    b_receipt=json.loads(paths['b_resource_receipt'].read_text());b_marker=json.loads(paths['b_completion'].read_text())
    if (b_marker.get('status')!='CLOSED_FAIL' or b_marker.get('panel')!='VAL_B'
        or b_marker.get('case_count_expected')!=142 or b_marker.get('case_count_observed')!=142
        or b_marker.get('all_children_reaped') is not True or b_marker.get('no_retry_or_redraw') is not True
        or b_receipt.get('all_children_reaped') is not True
        or b_marker.get('outcomes_SHA256')!=hashes['b_outcomes'] or b_marker.get('summary_SHA256')!=hashes['b_summary']
        or b_marker.get('resource_receipt_SHA256')!=hashes['b_resource_receipt']):
        raise ValueError('Full B must close and reap all children before any method draw')
    review=json.loads(paths['b_integrity_review'].read_text())
    if (review.get('review_status')!='FAIL_CLOSED_NO_PILOT_ADMISSION'
        or review.get('integrity_review_status')!='PASS_RETAINED_COMPLETE_OUTPUT_INTEGRITY'
        or review.get('panel')!='VAL_B' or review.get('independent_audit') is not True
        or review.get('case_count_expected')!=142 or review.get('case_count_observed')!=142
        or review.get('complete') is not True or review.get('complete_maps_verified')!=852):
        raise ValueError('Independent complete retained B integrity audit required; scientific failure stays binding')
    expected_review_hashes={'b_cases':hashes['validation_b_cases'],**{key:hashes[key] for key in
        ('b_outcomes','b_summary','b_resource_receipt','b_completion')}}
    if any(review.get('sha256',{}).get(key)!=value for key,value in expected_review_hashes.items()):
        raise ValueError('B integrity audit is not bound to the closed failed panel')
    ledger=json.loads(paths['post_b_ledger'].read_text())
    if (ledger.get('scientific_files_unchanged') is not True or ledger.get('A_remains_FAIL_CLOSED') is not True
        or ledger.get('B_remains_FAIL_CLOSED') is not True or ledger.get('telescope_values_opened') is not False):
        raise ValueError('Actual post-B failed-gate ledger required')
    budget=a['budget'];allocation=float(budget['aggregate_cpu_allocation_seconds'])
    if (float(ledger['remaining_CPU_after_closed_B_s'])!=float(budget['remaining_cpu_seconds'])
        or float(ledger['method_aggregate_CPU_allocation_s'])!=allocation
        or float(ledger['retained_report_reproduction_CPU_s'])!=float(budget['retained_report_reproduction_cpu_seconds'])
        or ledger.get('b_prerequisite_sha256')!={key:hashes[key] for key in
            ('b_summary','b_outcomes','b_resource_receipt','b_completion')}
        or ledger.get('post_development_ledger_sha256')!=hashes['post_development_ledger']):
        raise ValueError('Method admission capacity must equal the bound actual post-B ledger')
    if (float(budget['global_cpu_ceiling_seconds'])!=43200 or not 280<=allocation<=6000
        or float(budget['retained_report_reproduction_cpu_seconds'])<2000
        or float(budget['remaining_cpu_seconds'])<allocation+float(budget['retained_report_reproduction_cpu_seconds'])
        or float(budget['max_wall_seconds_per_job'])!=1800 or int(budget['max_rss_bytes'])!=4*1024**3):
        raise ValueError('Bounded actual remaining method allocation and report reserve required')
    return a,paths,hashes,banks

def describe(cases,outcomes):
    """Descriptive counts only; recovery thresholds never qualify this study."""
    identities={c['case_id'] for c in cases};observed={}
    for value in outcomes:
        if value['case_id'] not in identities or value['case_id'] in observed:raise ValueError('Unexpected or repeated method outcome')
        observed[value['case_id']]=value
    failed=[c['case_id'] for c in cases if c['case_id'] in observed and
        (not observed[c['case_id']].get('data_integrity_ok') or observed[c['case_id']].get('failure'))]
    missing=[c['case_id'] for c in cases if c['case_id'] not in observed]
    def counts(members):
        values=[observed[c['case_id']] for c in members if c['case_id'] in observed]
        valid=[v for v in values if v.get('data_integrity_ok') and not v.get('failure')]
        return {'expected':len(members),'observed':len(values),'integrity_valid':len(valid),
            'pre_OFF_all_active_recovery':sum(bool(v.get('pre_OFF_all_active_recovery')) for v in valid),
            'final_all_active_recovery':sum(bool(v.get('all_active_on_recovered')) for v in valid),
            'final_any_active_recovery':sum(bool(v.get('any_localized_on_recovered')) for v in valid),
            'all_active_recovery_lost_after_OFF':sum(bool(v.get('pre_OFF_all_active_recovery')) and
                not bool(v.get('all_active_on_recovered')) for v in valid)}
    grouped={}
    for label,key in (('declared_ideal_score','nominal_ideal_box_score'),('drift_hz_s','drift_hz_s'),
                      ('intrinsic_width_channels','intrinsic_width_channels'),('active_scan_indices','active_scan_indices'),
                      ('reference_native_offset','reference_native_offset')):
        groups={}
        for c in cases:groups.setdefault(json.dumps(c[key],separators=(',',':')),[]).append(c)
        grouped[label]={name:counts(group) for name,group in groups.items()}
    cell_records=[]
    for c in cases:
        cell_records.append({'case_id':c['case_id'],'declared_ideal_score':c['nominal_ideal_box_score'],
            'drift_hz_s':c['drift_hz_s'],'intrinsic_width_channels':c['intrinsic_width_channels'],
            'active_scan_indices':c['active_scan_indices'],'reference_native_offset':c['reference_native_offset'],
            'outcome':observed.get(c['case_id'])})
    return {'panel':'METHOD_STUDY','scientific_gate':'EXPLORATORY_METHOD_STUDY_ONLY','qualification':False,
        'A_remains_FAIL_CLOSED':True,'B_remains_FAIL_CLOSED':True,'telescope_values_opened':False,
        'complete':not failed and not missing,'case_count_expected':len(cases),'case_count_observed':len(observed),
        'failed_case_ids':failed,'missing_case_ids':missing,'counts':counts(cases),'groups':grouped,'cells':cell_records,
        'interpretation':'One fresh synthetic realization per grid cell; descriptive recovery counts, not calibration or confidence bounds.',
        'strength_definition':'Declared noise-free ideal box projection in Gamma16 sigma=.25 units; not measured detector SNR.'}

def main():
    def watchdog(_sig,_frame):raise TimeoutError('Whole-case method watchdog; no redraw')
    for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[variable]='1'
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(250,250))
    signal.signal(signal.SIGALRM,watchdog);signal.signal(signal.SIGPROF,watchdog)
    signal.setitimer(signal.ITIMER_REAL,max(.01,1790-(time.monotonic()-STARTED)))
    r=resource.getrusage(resource.RUSAGE_SELF);signal.setitimer(signal.ITIMER_PROF,max(.01,235-r.ru_utime-r.ru_stime))
    parser=argparse.ArgumentParser();parser.add_argument('--admission',type=Path,required=True)
    parser.add_argument('--case',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    a,paths,hashes,banks=admission(args.admission)
    if a['status']!='ADMITTED_METHOD_STUDY_SINGLE_CASE' or a['allowed_case_ids']!=[args.case]:raise ValueError('One admitted method identity required')
    cases=banks['method_cases'];selected=[c for c in cases if c['case_id']==args.case]
    if len(selected)!=1:raise ValueError('Unknown method identity')
    case=selected[0];index=cases.index(case)
    if Path(a['claim_directory']).resolve()!=CLAIMS or args.output.exists() or args.output.resolve()!=OUTPUT/f'case_{index:03d}':
        raise ValueError('Fresh canonical method claim/output required')
    if float(a['budget']['exclusive_cpu_allocation_seconds'])!=250:raise ValueError('Fixed250 whole-child partition required')
    reservation_path=OUTPUT/f'reservation_{index:03d}.json';closure_path=OUTPUT/f'closure_{index:03d}.json'
    if Path(a['reservation_path']).resolve()!=reservation_path or Path(a['closure_path']).resolve()!=closure_path or closure_path.exists():
        raise ValueError('Once-only canonical exclusive reservation required')
    reservation=json.loads(reservation_path.read_text())
    if (reservation['case_id']!=args.case or reservation['status']!='RESERVED_BEFORE_CHILD_SUBMIT'
        or reservation['cpu_reserved_seconds']!=250 or Path(reservation['output_directory']).resolve()!=args.output.resolve()):
        raise ValueError('Durable250 partition must precede child work')
    CLAIMS.mkdir(parents=True,exist_ok=True);claim_path=CLAIMS/(hashlib.sha256(args.case.encode('ascii')).hexdigest()+'.json')
    claim={'case_id':args.case,'panel':'METHOD_STUDY','status':'CLAIMED_BEFORE_ARRAY_GENERATION',
        'admission_SHA256':digest(args.admission),'exclusive_cpu_allocation_seconds':250,
        'output_directory':str(args.output.resolve()),'no_retry_or_redraw':True,'qualification':False}
    durable_json(claim_path,claim,exclusive=True);args.output.mkdir(parents=True,exist_ok=False)
    outcome={'case_id':args.case,'panel':'METHOD_STUDY','family':case['family'],'data_integrity_ok':False,
        'all_active_on_recovered':False,'any_localized_on_recovered':False,'pre_OFF_all_active_recovery':False,
        'pre_OFF_any_active_recovery':False,'survivor_count':0,'failure':None,'qualification':False}
    failed=True
    try:
        detector=load(paths['detector'],'detector');helpers=load(paths['dev_helpers'],'original_method_helpers')
        generator=load(paths['generator'],'original_method_generator')
        import numpy as np
        import scipy
        if np.__version__!='2.3.5' or scipy.__version__!='1.17.0' or sys.platform!='linux':raise ValueError('Original scientific environment required')
        contract=json.loads(paths['contract'].read_text());durable_json(args.output/'admission.json',{'admission':a,'observed_SHA256':hashes,'selected_case_id':args.case})
        durable_json(args.output/'case_definition.json',case);arrays,truth=generator.generate_case(case,contract)
        durable_json(args.output/'truth.json',truth);durable_json(args.output/'synthetic_array_hashes.json',[
            {'scan_id':h['scan_id'],'shape':list(v.shape),'dtype':str(v.dtype),'C_order_bytes_SHA256':hashlib.sha256(v.tobytes(order='C')).hexdigest()}
            for v,h in zip(arrays,contract['geometry']['scan_metadata'])])
        scans,frequencies=detector.control_inputs(arrays,contract);cfg=detector.Config()
        result=detector.search_cadence(scans,frequencies,cfg)
        helpers.save_result(args.output,result);recovery=detector.recovery_matches(result,truth)
        durable_json(args.output/'localized_recovery.json',recovery);measured=helpers.snapshot(STARTED,0.)
        if measured['wall_s']>1800 or measured['cpu_s']>250 or measured['peak_rss_bytes']>4*1024**3:raise ValueError('Whole-child method cap exceeded')
        outcome.update(measured,data_integrity_ok=True,all_active_on_recovered=recovery['final_all_active_recovery'],
            any_localized_on_recovered=recovery['final_any_active_recovery'],pre_OFF_all_active_recovery=recovery['pre_OFF_all_active_recovery'],
            pre_OFF_any_active_recovery=recovery['pre_OFF_any_active_recovery'],survivor_count=result['surviving_ON_threshold_carrier_count'],
            ON_threshold_carrier_count=len(result['all_ON_threshold_carriers']))
        maxima={m['scan_id']:float(np.max(m['maximum_robust_box_track_score'])) for m in result['scan_maps'] if m['role']=='ON'}
        on_hits={scan_id:[h for h in result['all_ON_threshold_carriers'] if h['scan_id']==scan_id] for scan_id in maxima}
        stages={}
        for scan_id,localized in recovery['per_active_ON_scan'].items():
            stages[scan_id]=('LOCALIZED_SURVIVOR' if localized['final_localized_recovery'] else
                'LOCALIZED_HITS_OFF_VETOED' if localized['pre_OFF_localized_recovery'] else
                'NO_ON_THRESHOLD_HIT' if maxima[scan_id]<cfg.on_threshold else 'ON_HITS_NOT_LOCALIZED')
        outcome.update(per_active_ON_scan=recovery['per_active_ON_scan'],
            ON_global_maximum_robust_score_by_scan=maxima,loss_stage_by_active_ON_scan=stages,
            ON_threshold_carrier_count_by_scan={key:len(hits) for key,hits in on_hits.items()},
            ON_surviving_carrier_count_by_scan={key:sum(h['disposition']=='SURVIVOR_EXPLORATORY' for h in hits) for key,hits in on_hits.items()})
        durable_json(args.output/'outcome.json',outcome);durable_json(args.output/'outcomes.json',[outcome])
        durable_json(args.output/'resource_receipt.json',{**measured,'caps_passed':True,'caps':{'wall_s':1800,'cpu_s_available':250,'exclusive_cpu_allocation_seconds':250,'peak_rss_bytes':4*1024**3}})
        durable_json(args.output/'single_case_status.json',{'status':'CLOSED_PENDING_DURABLE_COMMIT','panel':'METHOD_STUDY','case_id':args.case,'qualification':False,'no_retry_or_redraw':True})
        manifest={}
        for file in sorted(args.output.iterdir()):
            if file.is_file():
                with file.open('rb') as handle:os.fsync(handle.fileno())
                manifest[file.name]={'SHA256':digest(file),'size_bytes':file.stat().st_size}
        durable_json(args.output/'artifact_manifest.json',manifest);claim.update(status='CLOSED_PENDING_DURABLE_COMMIT',whole_job_cpu_s=measured['cpu_s']);durable_json(claim_path,claim)
        durable_json(args.output/'COMMITTED.json',{'status':'COMPLETED_CASE_ONLY','panel':'METHOD_STUDY','case_id':args.case,
            'artifact_manifest_SHA256':digest(args.output/'artifact_manifest.json'),'caps_passed':True,'no_retry_or_redraw':True,
            'qualification':False,'scientific_gate':'EXPLORATORY_METHOD_STUDY_ONLY','A_remains_FAIL_CLOSED':True,'B_remains_FAIL_CLOSED':True})
        failed=False
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0);signal.setitimer(signal.ITIMER_PROF,0);(args.output/'COMMITTED.json').unlink(missing_ok=True)
        r=resource.getrusage(resource.RUSAGE_SELF);outcome.update(data_integrity_ok=False,failure={'type':type(error).__name__,'message':str(error)},
            wall_s=time.monotonic()-STARTED,cpu_s=r.ru_utime+r.ru_stime,peak_rss_bytes=r.ru_maxrss*1024)
        try:
            durable_json(args.output/'outcome.json',outcome);durable_json(args.output/'outcomes.json',[outcome]);(args.output/'failure_traceback.txt').write_text(traceback.format_exc())
            claim.update(status='FAILED_CLOSED');durable_json(claim_path,claim)
        except BaseException:pass
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.setitimer(signal.ITIMER_PROF,0)
    print(json.dumps({k:outcome.get(k) for k in ('case_id','data_integrity_ok','all_active_on_recovered','pre_OFF_all_active_recovery','survivor_count','wall_s','cpu_s','peak_rss_bytes','failure')}),flush=True)
    return 1 if failed else 0

if __name__=='__main__':raise SystemExit(main())
