"""Read-only accounting of the closed batch case. No draw or live retry."""
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import time
OUT=Path(__file__).resolve().parent;ROOT=OUT.parent;started=time.monotonic()
def read(path):return json.loads(subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT))
def local(name):return json.loads((OUT/name).read_bytes())
def save(name,value):(OUT/name).write_text(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n')
r=local('run01/result.json');b=local('run01/broker_timing.json');events=local('run01/transport_receipts.json')
assert r['status']=='PASS_ENGINEERING_ARCHIVE'
assert len(r['case_timings'])==1 and r['case_timings'][0]['end_to_end_seconds']<80
assert len(r['publication_receipts'])==2
old=read('results_radio_whole_cadence_lossless_2026-09-28/postflight.json');pins=old['historical_invariant_pins']
for path,expected in pins.items():
 actual=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
 assert hashlib.sha256(actual).hexdigest()==expected,path
closed_paths=['src/seti_repeater/whole_cadence_remote_radio.py','src/seti_repeater/whole_cadence_lossless_radio.py',
 'results_radio_whole_cadence_remote_2026-09-28/live01/ledger.json','results_radio_whole_cadence_remote_2026-09-28/live02/ledger.json',
 'results_radio_whole_cadence_lossless_2026-09-28/live01/ledger.json']
closed={}
for path in closed_paths:
 prior=subprocess.check_output(['git','show','d30319338c1ae0be78b22ca4b80cd95aa8fe25b4:'+path],cwd=ROOT)
 now=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT);assert now==prior,path
 closed[path]=hashlib.sha256(now).hexdigest()
rows=collections.defaultdict(lambda:{'calls':0,'tool_seconds':0.,'roundtrip_seconds':0.,'returned_json_bytes':0})
for e,t in zip(events,b['timings'],strict=True):
 assert e['index']==t['id']+22
 x=rows[e['method']];x['calls']+=1;x['tool_seconds']+=t['tool_milliseconds']/1000
 x['roundtrip_seconds']+=e['ended_seconds']-e['started_seconds'];x['returned_json_bytes']+=e['response_json_bytes']
prior_case=read('results_radio_whole_cadence_lossless_2026-09-28/run01/result.json')['case_timings'][0]['end_to_end_seconds']
current_case=r['case_timings'][0]['end_to_end_seconds']
assessment={'schema':'radio-batch-latency-assessment-v1','source':'retained live receipts only; no new case',
 'methods':dict(rows),'case_seconds':current_case,'prior_fixed_same_size_archive_case_seconds':prior_case,
 'descriptive_reduction_fraction':1-current_case/prior_case,'not_a_controlled_benchmark':True,
 'broker_seconds':b['broker_elapsed_seconds'],'complete_worker_seconds':r['elapsed_seconds'],
 'first_call_roundtrip_including_supervisor_start_seconds':events[0]['ended_seconds']-events[0]['started_seconds'],
 'fits_fixed_engineering_80_seconds':True,'qualifies_scientific_calibration_40_seconds':False,
 'qualifies_full_scientific_evaluation_80_seconds':False,'remaining_calibration_timing_gap_seconds':current_case-40,
 'gaussian_native_physical_chain_not_measured':True,'phase_151_case_overhead_not_qualified':True,
 'next_risk':'Bounded concurrent immutable file readback; charge every request, retain all errors, independently hash/decode all files; no live retry here.',
 'scientific_execution_authorized':False}
save('timing_assessment.json',assessment)
disposition={'schema':'radio-batch-engineering-disposition-v1','scope':'batch-live01','status':'CLOSED_ENGINEERING_ARCHIVE_PASS_TIMING_NOT_SCIENTIFICALLY_QUALIFIED',
 'consumed_cases':1,'archived_cases':1,'case_milliseconds_nonrefundable':80000,'normal_bytes_nonrefundable':1048576,'failure_bytes_nonrefundable':8192,
 'ledger_history_reserve_bytes':65536,'scope_may_restart':False,'corrective_live_scope_authorized_here':False,
 'prior_three_scopes_closed_unchanged':True,'cumulative_remote_cases_consumed':4,'cumulative_remote_cases_archived':2,
 'cumulative_remote_expected_failures':1,'cumulative_remote_consumed_incomplete_cases':1,
 'cumulative_remote_case_milliseconds_nonrefundable':2000000,'cumulative_remote_case_normal_failure_bytes_nonrefundable':3170560,
 'scientific_execution_authorized':False,'proposal_status':'PROPOSED_NOT_ACTIVATED','plan_consolidation':'2026-10-09'}
save('disposition.json',disposition)
archive=r['accounting']['used_physical_bytes'];independent=local('independent_git_readback.json')
evidence={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='postflight.json'}
local_total=sum(v['bytes'] for v in evidence.values());freeze_size=(ROOT/'config/radio_whole_cadence_batch_runtime_20260929.json').stat().st_size
post={'schema':'radio-batch-postflight-v1','status':disposition['status'],'new_distinct_tests':22,'old_fixtures_replayed_as_progress':0,
 'historical_invariant_count':17,'historical_invariant_pins':pins,'five_closed_ledger_code_pins':closed,
 'freeze_commit':'2dd19d346157d77813c554bf20fb519d3c226e73','live_final_commit':r['final_branch_head'],
 'code_files':831,'runtime_files':1132,'new_live_git_calls':48,'calls_including_preflight':70,
 'returned_json_bytes_including_preflight':r['returned_json_bytes'],'preflight_seconds_charged':100,
 'live_seconds':r['elapsed_seconds'],'independent_git_verification_seconds':independent['verification_seconds'],
 'separate_post_live_git_fetch_and_metadata_conservative_seconds':30,'closure_reserve_seconds':240,'closure_reserve_calls':60,'closure_reserve_response_bytes':2*1024**2,
 'prior_scopes_conservative_calls':316,'prior_scopes_conservative_seconds':1636.04648012,
 'scope_limits':{'active_seconds':600,'github_calls':160,'returned_json_bytes':16*1024**2,'evidence_bytes':2*1024**2,'local_saved_bytes':16*1024**2,'peak_rss_bytes':512*1024**2,'branch_advances':6},
 'scope_branch_advances_before_report':3,'planned_scope_advances_including_report_main':5,
 'archive_and_all_ledger_versions_bytes':archive,'archive_bytes':sum(a['physical_bytes'] for a in r['accounting']['cases'][0]['artifacts'].values()),
 'ledger_history_bytes':r['accounting']['ledger_history_bytes'],'local_evidence_files':evidence,'local_saved_evidence_bytes_before_postflight':local_total,
 'physical_evidence_conservative_including_full_runtime_freeze_bytes':archive+local_total+freeze_size+65536,
 'postflight_and_small_report_allowance_bytes':65536,'raw_RPC_local_retained_bytes':3420804,'peak_live_rss_bytes':r['peak_rss_bytes'],
 'scientific_counters':{'development_closed':6,'failed_calibration_closed':3,'old_evaluation_allocation_closed':1,'old_evaluation_values_unopened_unusable':24,'retained_score_diagnosis_closed':1,'remedy':0,'pilot':0},
 'new_source_requests':0,'proposed_PRNG_constructions':0,'new_scientific_allocations':0,'external_messages':0,'scientific_execution_authorized':False}
post['postflight_generation_seconds']=time.monotonic()-started
post['active_seconds_charged_with_closure_reserve']=100+r['elapsed_seconds']+independent['verification_seconds']+30+240+post['postflight_generation_seconds']
post['github_calls_charged_with_closure_reserve']=130
post['returned_json_bytes_charged_with_closure_reserve']=r['returned_json_bytes']+2*1024**2
assert post['active_seconds_charged_with_closure_reserve']<=600
assert post['physical_evidence_conservative_including_full_runtime_freeze_bytes']<2*1024**2
assert local_total+3420804<16*1024**2
save('postflight.json',post)
print(json.dumps({k:post[k] for k in ('historical_invariant_count','active_seconds_charged_with_closure_reserve','github_calls_charged_with_closure_reserve','physical_evidence_conservative_including_full_runtime_freeze_bytes','local_saved_evidence_bytes_before_postflight')}))
