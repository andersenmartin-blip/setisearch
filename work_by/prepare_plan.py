"""Bind the complete BY method before reading observation arrays or CSV rows."""
from pathlib import Path
import hashlib, importlib.util, json, platform, sys
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'work_by'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    assert (HERE/'SOURCE_REVIEW_BY.json').is_file()
    assert (HERE/'SOURCE_REVIEW_RFI_BY.json').is_file()
    spec=importlib.util.spec_from_file_location('by_configuration_only',HERE/'inject_recover.py')
    code=importlib.util.module_from_spec(spec);spec.loader.exec_module(code)
    parent_path=HERE/'provenance/BW_PARTIAL_PLAN.json';parent=read(parent_path)
    inputs=read(HERE/'INPUTS_BY.json')
    paths=[p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py','.json')
           and not any(x in p.parts for x in ('__pycache__','execution'))
           and p.name not in ('PLAN_BY.json','PUBLIC_FREEZE_BY.json')]
    paths += [ROOT/'work_bo/vendor/current/kernel_v.py',ROOT/'work_bu/partial_search.py',
              ROOT/'work_bt/isolated_worker.py',Path(sys.executable).resolve()]
    plan={'schema':'SETI_BY_CONDITIONAL_INJECTION_V1','config':code.CONFIG,
          'parent_BX_index':'libfile_34ec6b3c28b88191a3acd913f13ed030',
          'parent_BW_plan_path':str(parent_path),'parent_BW_plan_sha256':sha(parent_path),
          'parent_closed_archive_sha256':inputs['parent_archive_sha256'],
          'scans':parent['scans'],'inputs':inputs['inputs'],
          'source_sha256':{str(p):sha(p) for p in sorted(set(paths))},
          'runtime':{'python':platform.python_version(),'numpy':code.np.__version__},
          'secondary_derived_data_scope':{'path':str(HERE/'rfi_scope.json'),'sha256':sha(HERE/'rfi_scope.json'),
              'newly_acquired_original_powers':False,'rows_not_read_before_freeze':True},
          'execution':{'exclusive_root':'/dev/shm/seti_by_20261031','serial_phases':['rfi','rfi_audit','injection','audit'],
              'cpu_seconds_per_child':600,'wall_seconds_per_child':600,'address_space_bytes':2*1024**3,
              'max_file_bytes':64*1024**2,'stdout_size_verified_after_close_max_bytes':1024**2,
              'rfi_child_scope_has_stricter_limits':True,'limits_exclude_subsequent_archive_and_export':True,
              'one_execution_per_identity':True,'automatic_retry':False,'active_outputs_on_tmpfs':True,
              'archive_member_CRC_size_SHA_verified_before_and_after_export':True},
          'qualification':{'conditional_reduced_bank':True,'amplitudes_are_not_flux_density':True,
              'normalizer_response_to_injections_tested':False,'independent_observations':False,
              'new_SETI_searches':0,'new_original_coverage_credit':0,'full_cadence_status':'NOT_EVALUABLE_MISSING_OFF5'}}
    with (HERE/'PLAN_BY.json').open('x') as f:json.dump(plan,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps({'plan_sha256':sha(HERE/'PLAN_BY.json'),'source_pins':len(paths),
                      'inputs':len(plan['inputs']),'cases':264,'new_SETI_searches':0}))
if __name__=='__main__':main()
