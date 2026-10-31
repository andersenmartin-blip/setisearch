"""Close verified BY results without awarding original survey coverage."""
from pathlib import Path
import hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'work_by';TMP=Path('/dev/shm/seti_by_20261031')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def main():
    spec=importlib.util.spec_from_file_location('by_seal',ROOT/'work_bt/isolated_worker.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    captures=[]
    for phase in ('rfi','rfi_audit','injection','audit'):
        loc=HERE/'execution'/phase;r=read(loc/'RESULT.json')
        assert r['status']=='PASS' and r['actual_exit_code']==0 and r['child_wait_completed'] and r['natural_stdout_eof'] and not r['killed'] and not r['errors']
        assert r['pins_before']==r['pins_after']==r['pins_after_export']
        assert helper.verify_archive(loc/'EVIDENCE.zip',r['archive']['members'])==r['archive']
        for name,digest in r['output_sha256'].items():assert sha(TMP/phase/'outputs'/name)==digest
        captures.append({'phase':phase,'actual_exit_code':0,'natural_stdout_eof':True,'wall_seconds':r['wall_seconds'],
                         'capture_sha256':sha(loc/'RESULT.json'),'archive_sha256':r['archive']['sha256'],
                         'archive_bytes':r['archive']['bytes'],'archive_members':r['archive']['members']})
    inj=read(TMP/'injection/outputs/SUMMARY_BY.json');audit=read(TMP/'audit/outputs/REVIEW_BY.json')
    rfi=read(TMP/'rfi/outputs/SUMMARY_RFI_BY.json');ra=read(TMP/'rfi_audit/outputs/REVIEW_RFI_BY.json')
    assert audit['status']=='PASS_INDEPENDENT_INJECTION_REVIEW' and audit['groups']==inj['groups']
    assert audit['production_summary_sha256']==sha(TMP/'injection/outputs/SUMMARY_BY.json')
    assert ra['status']=='PASS_INDEPENDENT_RFI_REVIEW' and ra['summary_sha256']==sha(TMP/'rfi/outputs/SUMMARY_RFI_BY.json')
    assert ra['all_original_count_cells_checked']==sum(v['total_count_cells'] for v in rfi['datasets'].values())==340340
    assert audit['cases_checked']==inj['case_count']==264 and audit['calibration_track_sums_checked']==42577920
    for name,phase,filename in [('REVIEW_INJECTION_BY.json','audit','REVIEW_BY.json'),('REVIEW_RFI_BY.json','rfi_audit','REVIEW_RFI_BY.json'),('SUMMARY_RFI_BY.json','rfi','SUMMARY_RFI_BY.json')]:
        with (HERE/name).open('xb') as f:f.write((TMP/phase/'outputs'/filename).read_bytes())
    summary={'schema':'SETI_BY_COMBINED_RESULT_V1','status':'DERIVED_RFI_AND_CONDITIONAL_RECOVERY_COMPLETE_AUDITS_PASS',
      'parent_BX_index':'libfile_34ec6b3c28b88191a3acd913f13ed030','public_freeze':read(HERE/'PUBLIC_FREEZE_BY.json'),
      'plan_sha256':sha(HERE/'PLAN_BY.json'),'captures':captures,
      'injection':{k:inj[k] for k in ('case_count','geometry_count','matched_seed_rows','computed_correlated_track_combinations','groups','limits')},
      'injection_review':{k:v for k,v in audit.items() if k!='groups'},
      'rfi':rfi,'rfi_review':ra,'independent_audits_completed':True,
      'new_derived_data_files':2,'new_original_telescope_power_files':0,'new_SETI_searches':0,
      'new_original_unique_archive_ids':0,'new_original_technical_MHz_visits':0,
      'original_SETI_authority':{'unique_archive_ids':486,'technical_MHz_visits':268.50128173828125,'qualified_astronomical_sensitivity_MHz_visits':0,
         'full_cadence_status':'NOT_EVALUABLE_MISSING_OFF5','BU_BV_BW_q':'1..254','BU_BV_BW_partial_carrier_width_MHz':2.90679931640625},
      'queue_advanced':False,'background_jobs_running':False,
      'next_action':'Prioritize an eligible complete new ON/OFF power dataset or normal permitted access to original OFF5 with full BB/BC/BE checks. RFI tables are unpaired under the frozen identifier rules. Any new pairing or broader injection tests need separately declared methods; do not call synthetic recoveries candidates or infer clean sky from notch-region zero counts.'}
    save(HERE/'SUMMARY_BY.json',summary)
    print(json.dumps({'status':summary['status'],'phases_closed':4,'new_count_cells':340340,'injection_cases':264,'new_SETI_searches':0,'summary_sha256':sha(HERE/'SUMMARY_BY.json')}))
if __name__=='__main__':main()
