"""Summarize sealed BZ outputs; never rerun numerical science."""
from pathlib import Path
import hashlib, importlib.util, json, sys
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'work_bz'
TMP=Path('/dev/shm/seti_bz_grid_20261031')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def main():
    spec=importlib.util.spec_from_file_location('bz_archive_check',ROOT/'work_bt/isolated_worker.py')
    helper=importlib.util.module_from_spec(spec);sys.modules[spec.name]=helper;spec.loader.exec_module(helper)
    captures=[]
    for phase in ['production','audit']:
        folder=HERE/'execution'/phase;r=read(folder/'RESULT.json')
        assert r['status']=='PASS' and r['actual_exit_code']==0 and r['child_wait_completed'] and r['natural_stdout_eof']
        assert not r['killed'] and not r['errors'] and r['pins_before']==r['pins_after']==r['pins_after_export']
        assert helper.verify_archive(folder/'EVIDENCE.zip',r['archive']['members'])==r['archive']
        for name,digest in r['output_sha256'].items():assert sha(TMP/phase/'outputs'/name)==digest
        captures.append(dict(phase=phase,actual_exit_code=0,natural_stdout_eof=True,wall_seconds=r['wall_seconds'],
            capture_sha256=sha(folder/'RESULT.json'),archive_sha256=r['archive']['sha256'],archive_bytes=r['archive']['bytes']))
    source=TMP/'production/outputs/SUMMARY_BZ.json';review=TMP/'audit/outputs/REVIEW_BZ.json'
    s=read(source);a=read(review)
    assert a['production_summary_sha256']==sha(source) and a['arrays_sha256']==s['arrays_sha256']
    assert a['arms']==[{k:v for k,v in arm.items() if k!='cases'} for arm in s['arms']]
    for p,dest in [(source,HERE/'GRID_SUMMARY_BZ.json'),(review,HERE/'REVIEW_BZ.json')]:
        with dest.open('xb') as f:f.write(p.read_bytes())
        assert sha(p)==sha(dest)
    result=dict(schema='SETI_BZ_FINAL_RESULT_V1',status='NESTED_GRID_COMPLETE_INDEPENDENT_AUDIT_PASS',
        parent_BY_index_library_file_id='libfile_61d90f3bc0048191b063af7a6dd488fe',
        public_freeze=read(HERE/'PUBLIC_FREEZE_BZ.json'),plan_sha256=sha(HERE/'PLAN_BZ.json'),
        production_summary_sha256=sha(source),independent_review_sha256=sha(review),captures=captures,
        arms=[{k:v for k,v in arm.items() if k!='cases'} for arm in s['arms']],
        experiment_counts={k:s[k] for k in ['case_count','geometry_count','injected_matrices_verified_exactly',
          'coarse_seed_rows_reused','new_matched_seed_rows','union_matched_seed_rows','new_calibration_vectors',
          'reused_calibration_vectors','new_correlated_track_combinations','reused_baseline_track_combinations',
          'union_nominal_track_combinations']},
        independent_audit={k:v for k,v in a.items() if k not in ['arms','limits']},
        limits=s['limits'],fresh_data_search=read(HERE/'DATA_SOURCE_SEARCH_BZ.json'),
        independent_audits_completed=True,new_original_telescope_power_files=0,new_SETI_searches=0,
        new_original_unique_archive_ids=0,new_original_technical_MHz_visits=0,
        original_SETI_authority=dict(unique_archive_ids=486,technical_MHz_visits=268.50128173828125,
          qualified_astronomical_sensitivity_MHz_visits=0,full_cadence_status='NOT_EVALUABLE_MISSING_OFF5',
          BU_BV_BW_q='1..254',BU_BV_BW_partial_carrier_width_MHz=2.90679931640625),
        queue_advanced=False,background_jobs_running=False,
        next_action='Prioritize an eligible complete new original ON/OFF power dataset or normal permitted archive access to missing HIP43223/65143 OFF5 with full BB/BC/BE gates. BZ narrows the explanation of BY losses: denser rates improve some cross-scan associations but not source recovery. Diagnose remaining failures from sealed outputs before any separately frozen new experiment; do not rerun closed BZ or adopt a detector without independent data and false-alarm calibration.')
    save(HERE/'FINAL_SUMMARY_BZ.json',result)
    print(json.dumps({'status':result['status'],'production_summary_sha256':sha(source),'final_summary_sha256':sha(HERE/'FINAL_SUMMARY_BZ.json')}))
if __name__=='__main__':main()
