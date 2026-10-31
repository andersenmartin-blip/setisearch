"""Create the prospective BZ binding without loading any numerical arrays."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'work_bz'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
spec=importlib.util.spec_from_file_location('bz_config',HERE/'grid_recovery.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
parent_path=HERE/'parent_by/PLAN_BY.json'
parent=read(parent_path)
baseline={}
for key,name in [('summary','SUMMARY_BY.json'),('arrays','RESULT_ARRAYS_BY.npz'),('cases','CASES_BY.json'),('review','REVIEW_BY.json')]:
    p=HERE/'parent_by'/name
    baseline[key+'_path']=str(p);baseline[key+'_sha256']=sha(p)
paths=[HERE/name for name in ['grid_recovery.py','review_grid.py','test_grid.py','test_review_grid.py',
    'run_phase_bz.py','prepare_plan_bz.py','SCOPE_BZ.md','SOURCE_REVIEW_BZ.json','DATA_SOURCE_SEARCH_BZ.json','PARENT_RESTORE_BZ.json']]
paths += [parent_path]+[Path(v) for k,v in baseline.items() if k.endswith('_path')]
paths += [ROOT/p for p in ['work_by/inject_recover.py','work_bo/vendor/current/kernel_v.py','work_bu/partial_search.py','work_bt/isolated_worker.py']]
paths += [Path(sys.executable).resolve()]
plan=dict(schema='SETI_BZ_NESTED_DRIFT_GRID_V1',config=module.CONFIG,
    created_utc=datetime.now(timezone.utc).isoformat(),scans=parent['scans'],inputs=parent['inputs'],
    parent_BY_plan_path=str(parent_path),parent_BY_plan_sha256=sha(parent_path),baseline=baseline,
    source_sha256={str(p):sha(p) for p in sorted(paths)},
    parent_BY_index_library_file_id='libfile_61d90f3bc0048191b063af7a6dd488fe',
    parent_BY_evidence_sha256='631a4200def77523e288ef52a89dad27d8e803932bfad71c70957c9c5be900d7',
    execution=dict(exclusive_tmpfs='/dev/shm/seti_bz_grid_20261031',wall_seconds_per_child=600,
        CPU_seconds_per_child=600,address_space_bytes=2*1024**3,file_size_bytes=64*1024**2,
        stdout_bytes_checked_after_natural_close=1024**2,automatic_retry=False,
        executor_and_agent_filesystem_activity_paused_during_children=True),
    interpretation=dict(method_development_on_previously_exposed_backgrounds=True,
        hypothesis_informed_by_BY_posthoc_diagnostics=True,independent_validation_set=False,
        new_observations=0,new_SETI_searches=0,astronomical_sensitivity_calibrated=False,
        full_cadence_status='NOT_EVALUABLE_MISSING_OFF5',queue_advanced=False),
    original_authority=dict(unique_archive_ids=486,technical_MHz_visits=268.50128173828125,
        qualified_astronomical_sensitivity=0,missing_scan='HIP43223/65143',
        recovery_spec='work_bw/recovery/RESUME_SPEC_BW.json'))
for item in plan['inputs']:
    p=Path(item['path']);assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
with (HERE/'PLAN_BZ.json').open('x') as f:json.dump(plan,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
print(json.dumps({'plan_sha256':sha(HERE/'PLAN_BZ.json'),'source_pins':len(paths),'input_pins':len(plan['inputs'])}))
