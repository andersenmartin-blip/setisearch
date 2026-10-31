"""Posthoc BZ interpretation using sealed result arrays only; no new scoring."""
from pathlib import Path
import argparse
import hashlib
import json
import signal
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'work_bz'
ISOLATION=Path('/dev/shm/seti_bz_grid_20261031')
ON=(0,2,4)

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def read(path):return json.loads(Path(path).read_text())

def verify_capture(phase):
    """Authenticate every archive member and current extracted byte first."""
    result_path=HERE/'execution'/phase/'RESULT.json'
    zip_path=result_path.parent/'EVIDENCE.zip';result=read(result_path)
    require(result['status']=='PASS' and result['actual_exit_code']==0 and
            result['child_wait_completed'] and result['natural_stdout_eof'] and
            not result['killed'] and not result['errors'],'Unsuccessful capture')
    require(result['pins_before']==result['pins_after']==result['pins_after_export'],'Capture pins changed')
    receipt=result['archive']
    require(receipt['status']=='PASS' and receipt['all_member_CRCs_verified'],'Unverified capture export')
    require(zip_path.stat().st_size==receipt['bytes']<64*1024**2 and sha(zip_path)==receipt['sha256'],'ZIP bytes differ')
    pins={str(result_path):sha(result_path),str(zip_path):sha(zip_path)}
    with zipfile.ZipFile(zip_path) as archive:
        members=receipt['members'];names=[m['path'] for m in members]
        require(len(members)<=64 and len(archive.namelist())==len(set(archive.namelist())) and
                set(archive.namelist())==set(names)|{'ARCHIVE_MANIFEST.json'},'ZIP membership differs')
        require(archive.testzip() is None,'ZIP CRC mismatch')
        require(json.loads(archive.read('ARCHIVE_MANIFEST.json'))==
                {'schema':receipt['manifest_schema'],'members':members},'ZIP manifest differs')
        for member in members:
            require(not Path(member['path']).is_absolute() and '..' not in Path(member['path']).parts,'Unsafe member path')
            content=archive.read(member['path']);path=ISOLATION/phase/member['path']
            require(len(content)==member['bytes'] and hashlib.sha256(content).hexdigest()==member['sha256'],'Archived member differs')
            require(path.stat().st_size==member['bytes'] and sha(path)==member['sha256'],'Extracted member differs')
            pins[str(path)]=member['sha256']
        captured=json.loads(archive.read('CAPTURE.json'))
        require(captured=={k:v for k,v in result.items() if k not in ('archive','pins_after_export')},'Capture/export result differs')
    for name,digest in result['output_sha256'].items():
        require(pins[str(ISOLATION/phase/'outputs'/name)]==digest,'Output receipt binding differs')
    return result,pins

def run(out):
    require(not out.exists(),'Diagnostic output already exists')
    production,pins=verify_capture('production');audit,more=verify_capture('audit');pins.update(more)
    source=Path(__file__).resolve();pins[str(source)]=sha(source)
    summary_path=ISOLATION/'production/outputs/SUMMARY_BZ.json'
    arrays_path=ISOLATION/'production/outputs/RESULT_ARRAYS_BZ.npz'
    summary=read(summary_path);review=read(ISOLATION/'audit/outputs/REVIEW_BZ.json')
    require(summary['status']=='PASS_NESTED_GRID_ABLATION' and
            review['status']=='PASS_INDEPENDENT_NESTED_GRID_REVIEW','Scientific status differs')
    require(summary['arrays_sha256']==pins[str(arrays_path)],'Summary/array binding differs')
    require(audit['pins_before'][str(summary_path)]==pins[str(summary_path)] and
            audit['pins_before'][str(arrays_path)]==pins[str(arrays_path)],'Audit does not bind these outputs')
    with np.load(arrays_path,allow_pickle=False) as archive:
        required=('seed_case_index','seed_refined_index','seed_baseline_row','seed_center_native',
                  'seed_width','seed_drift_hz_s','center_scores','max_scores','candidate_status','valid')
        data={key:archive[key] for key in required}
    arms={arm['factor']:arm for arm in summary['arms']}
    selected={factor:[case for case in arms[factor]['cases']
                      if case['presence']=='ON_ONLY' and case['amplitude']==8.0] for factor in (1,8)}
    require(all(len(cases)==24 for cases in selected.values()),'Expected 24 A8 ON_ONLY geometries')

    def detail(case,factor):
        rows=np.flatnonzero(data['seed_case_index']==case['case_index'])
        rows=rows[np.isin(data['seed_refined_index'][rows],np.arange(0,17,8//factor))]
        require(len(rows)==case['matched_source_seed_rows'],'Case seed count differs')
        scores=data['center_scores'][rows][:,ON]
        passed=scores>=10.0
        common=passed.all(axis=1)
        require(bool(common.any())==case['three_ON_recovered'],'Stored score/summary recovery differs')
        require(data['valid'][rows][:,ON].all(),'Unsupported ON score')
        value={'matched_source_seed_rows':len(rows),'three_ON_recovered':bool(common.any()),
               'passing_seed_rows_by_ON_scan':{str(scan):int(passed[:,i].sum()) for i,scan in enumerate(ON)},
               'maximum_stored_center_score_by_ON_scan':{str(scan):float(scores[:,i].max()) if len(rows) else None for i,scan in enumerate(ON)},
               'common_three_ON_seed_rows':int(common.sum()),
               'all_ON_scans_individually_pass_but_no_common_seed':bool(len(rows) and passed.any(axis=0).all() and not common.any()),
               'ON_scans_without_any_passing_seed':[scan for i,scan in enumerate(ON) if not passed[:,i].any()]}
        if len(rows):
            local=int(np.argmax(scores.min(axis=1)));row=int(rows[local]);minimum=float(scores[local].min())
            value['best_common_seed']={'union_row':row,'refined_index':int(data['seed_refined_index'][row]),
                'baseline_row':int(data['seed_baseline_row'][row]),'width':int(data['seed_width'][row]),
                'center_native':int(data['seed_center_native'][row]),'drift_hz_s':float(data['seed_drift_hz_s'][row]),
                'minimum_ON_center_score':minimum,'limiting_ON_scans':[scan for i,scan in enumerate(ON) if scores[local,i]==minimum],
                'ON_center_scores':{str(scan):float(data['center_scores'][row,scan]) for scan in ON},
                'available_OFF_max_scores':{str(scan):float(data['max_scores'][row,scan]) for scan in (1,3)},
                'candidate_status':str(data['candidate_status'][row])}
        else:value['best_common_seed']=None
        return value

    results=[]
    for old,now in zip(selected[1],selected[8]):
        require(old['case_index']==now['case_index'],'Case order differs')
        metadata={key:now[key] for key in ('case_index','geometry','center_offset','base_drift_index','drift_grid_phase','carrier_phase')}
        results.append(dict(metadata,factor1=detail(old,1),factor8=detail(now,8)))
    rescued=[x for x in results if not x['factor1']['three_ON_recovered'] and x['factor8']['three_ON_recovered']]
    remaining=[x for x in results if not x['factor8']['three_ON_recovered']]
    source_absent=[x for x in remaining if x['factor8']['matched_source_seed_rows']==0]
    later_fail=[x for x in remaining if x['factor8']['matched_source_seed_rows']>0]
    require(sum(x['factor1']['three_ON_recovered'] for x in results)==11 and len(rescued)==4 and len(remaining)==9,'Unexpected approved diagnostic counts')
    strata={}
    for key in ('center_offset','base_drift_index','drift_grid_phase','carrier_phase'):
        strata[key]=[]
        for value in sorted({x[key] for x in results}):
            chosen=[x for x in results if x[key]==value]
            strata[key].append({'value':value,'geometries':len(chosen),
                'factor1_three_ON_recovered':sum(x['factor1']['three_ON_recovered'] for x in chosen),
                'factor8_three_ON_recovered':sum(x['factor8']['three_ON_recovered'] for x in chosen),
                'newly_rescued_case_indices':[x['case_index'] for x in rescued if x[key]==value],
                'remaining_failure_case_indices':[x['case_index'] for x in remaining if x[key]==value]})
    result={'schema':'SETI_BZ_POSTHOC_RECOVERY_DIAGNOSTIC_V1','status':'PASS_SEALED_OUTPUT_POSTHOC_DIAGNOSTIC',
        'scope':{'presence':'ON_ONLY','amplitude':8.0,'geometries':24,'factors':[1,8]},
        'input_sha256':pins,'captures_and_all_member_bytes_verified_before_array_read':True,
        'factor1_three_ON_recovered':11,'factor8_three_ON_recovered':15,
        'newly_rescued_cases':rescued,'geometry_strata':strata,'remaining_failure_cases':remaining,
        'remaining_failure_summary':{'total':len(remaining),'source_absent':len(source_absent),
            'source_absent_case_indices':[x['case_index'] for x in source_absent],
            'source_present_later_ON_failure':len(later_fail),
            'source_present_later_ON_failure_case_indices':[x['case_index'] for x in later_fail],
            'all_ON_scans_individually_pass_but_no_common_seed_case_indices':[x['case_index'] for x in later_fail if x['factor8']['all_ON_scans_individually_pass_but_no_common_seed']],
            'source_present_cases_without_any_passing_seed_by_ON_scan':{str(scan):sum(scan in x['factor8']['ON_scans_without_any_passing_seed'] for x in later_fail) for scan in ON},
            'best_common_seed_limiting_ON_scan_counts':{str(scan):sum(scan in x['factor8']['best_common_seed']['limiting_ON_scans'] for x in later_fail) for scan in ON}},
        'new_searches':0,'new_injections':0,'recomputed_calibrations':0,'recomputed_scores':0,
        'posthoc':True,'independent_validation':False,
        'limits':['Selected after the BZ result; descriptive interpretation, not validation or a prospective hypothesis test.',
                  'All rates and truth-matched seeds were already frozen and scored; only stored-score thresholding, minima, maxima and counts are aggregated here.',
                  'Best common seed is chosen posthoc by the largest minimum stored ON center score; limiting-scan counts include all exact ties.',
                  'Marginal passing seeds at each ON scan need not be the same seed; only a common seed constitutes three-ON recovery.',
                  'The deterministic exposed geometries are not independent population trials; overlapping strata must not be added.',
                  'No new observation, global false-alarm calibration, Jy sensitivity, blind search, or complete missing-OFF5 cadence qualification.']}
    require(all(sha(path)==digest for path,digest in pins.items()),'Bound bytes changed during diagnostic')
    with out.open('x') as stream:json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    return {'status':result['status'],'output':str(out),'output_sha256':sha(out),
            'rescued_case_indices':[x['case_index'] for x in rescued],'remaining_failure_summary':result['remaining_failure_summary'],'geometry_strata':strata}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=HERE/'POSTHOC_RECOVERY_DIAGNOSTIC_BZ.json')
    args=parser.parse_args()
    signal.signal(signal.SIGALRM,lambda signum,frame:(_ for _ in ()).throw(TimeoutError('Bounded diagnostic exceeded 30 seconds')))
    signal.alarm(30)
    print(json.dumps(run(args.out),indent=2,sort_keys=True))
