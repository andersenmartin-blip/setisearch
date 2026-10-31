"""Freeze the entire remaining q33..253 continuation from BU metadata."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,platform
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'work_bv'))
import partial_search as science
parentpath=ROOT/'work_bu/BU_PARTIAL_PLAN.json'
assert science.sha(parentpath)=='f681d59f37a205bf0448736137bdfce37e04a1e18e6a4654899f2e1df342aefd'
parent=science.read(parentpath); summarypath=ROOT/'work_bu/SUMMARY_BU.json'; prior=science.read(summarypath)
assert prior['q_list']==list(range(1,33)) and prior['status']=='COMPLETED_FIVE_SCAN_PARTIAL_EXPLORATORY_SEARCH'
plan=json.loads(json.dumps(parent)); plan.pop('prefreeze_metadata_update',None)
plan.update(schema='SETI_BV_PARTIAL_HIP44295_LOCAL_Q_ESS_V1',identity='BV_PARTIAL_HIP44295_REMAINING_SAFE_Q_V1',created_utc=datetime.now(timezone.utc).isoformat(),core_q_list=list(range(33,254)),batch_q_lists=science.BATCHES,scope_numerics=science.SCOPE_NUMERICS,isolation_root='/dev/shm/seti_bv_partial_20261031',overall_runtime_wall_seconds=3600)
plan['runtime']=dict(python_version=platform.python_version(),numpy_version=science.np.__version__,python_executable=sys.executable,python_executable_sha256=science.sha(sys.executable))
sources=science.required_source_pins()
for rel in ['work_bv/prepare_plan.py','work_bv/run_stage.py','work_bv/run_remaining.py','work_bv/review/audit_partial_bv.py','work_bo/src/capture.py','work_bt/isolated_worker.py','work_bu/partial_search.py']:
    p=ROOT/rel;sources[str(p)]=science.sha(p)
plan['source_sha256']=sources
for p in [parentpath,summarypath,ROOT/'work_bu/review/FINAL_CLOSURE_REVIEW_BU.json',ROOT.parent/'bu_delivery/SETI_BU_DELIVERY_INDEX_2026-10-31.json']:
    plan['metadata_evidence'].append(dict(path=str(p),sha256=science.sha(p)))
plan['parent_checkpoint']=dict(index_library_file_id='libfile_c06f4322c7d48191b299e5b0e579d663',result_commit='4d0b0d44d23575fa486ab8c69559c246edd865a3',result_tree='0a81c4ac53e513eb7c1e1b651c3fc23c41eaca95',completed_q=list(range(1,33)),original_coverage_credit=0)
plan['interpretation']['purpose']='First detector scoring of all remaining q33..253 carrier cores in five previously decoded and fully normalized 2016 scans; separate partial continuation.'
plan['interpretation']['q_selection']='All remaining safe q33..253 fixed before new scoring, ascending q, 27 eight-q batches and one five-q batch. No data-driven selection or tuning.'
plan['interpretation']['previous_power_contact']='BU normalized all native channels; this continuation is not unseen raw data or a holdout. BU q1..32 results are retained and not rescored.'
plan['interpretation']['full_power_authorization']='User requested autonomous full-power continuation on31 October2026; full remaining finite cached scope is selected.'
plan['execution_policy']=dict(serial_only=True,automatic_retry=False,stop_on_any_capture_or_review_failure=True,public_freeze_and_exact_readback_before_scoring=True,independent_review_after_each_batch=True,independent_normalization_review_first_batch=True,no_other_executor_commands_during_run=True,retain_all_closed_archives=True,overall_wall_cap_seconds=3600)
path=ROOT/'work_bv/BV_PARTIAL_PLAN.json'; science.write(path,plan);science.validate_plan(plan,path)
print(json.dumps(dict(plan_sha256=science.sha(path),source_count=len(sources),scans=len(plan['scans']),batches=len(science.BATCHES),first_q=33,last_q=253,scope=science.SCOPE_NUMERICS)))
