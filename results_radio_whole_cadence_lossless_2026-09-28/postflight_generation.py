"""Read-only closure/accounting of the fixed live run; never reruns a case."""
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import time
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(__file__).resolve().parent
def raw(p):return (ROOT/p).read_bytes()
def js(p):return json.loads(raw(p))
def save(name,x):(OUT/name).write_text(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
started=time.monotonic()
r=json.loads((OUT/'run01/result.json').read_bytes())
broker=json.loads((OUT/'run01/broker_timing.json').read_bytes())
independent=json.loads((OUT/'independent_git_readback.json').read_bytes())
old=js('results_radio_whole_cadence_remote_2026-09-28/postflight.json')
pins=old['historical_invariant_pins']
for p,h in pins.items():
    data=subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
    if hashlib.sha256(data).hexdigest()!=h:raise ValueError('Historical invariant changed: '+p)
if r['status']!='PASS_ENGINEERING_EXPECTED_FAILURE_RETAINED':raise ValueError('Cannot close as passing engineering')
state=r['accounting'];assert [c['status'] for c in state['cases']]==['archived','failed']
artifacts=sum(a['physical_bytes'] for c in state['cases'] for a in c['artifacts'].values())
assert artifacts+state['ledger_history_bytes']==state['used_physical_bytes']
timing={'schema':'radio-lossless-timing-admission-assessment-v1','mode':'METADATA_ONLY',
    'engineering_only':True,'new_data_or_rng_values':0,'live_seconds':r['elapsed_seconds'],
    'new_live_calls':broker['requests'],'api_seconds':sum(t['tool_milliseconds'] for t in broker['timings'])/1000,
    'broker_seconds':broker['broker_elapsed_seconds'],'methods':dict(collections.Counter(t['method'] for t in broker['timings'])),
    'case_end_to_end_seconds':[c['end_to_end_seconds'] for c in r['case_timings']],
    'inactive_scientific_caps_seconds':{'calibration':40,'evaluation':80},
    'timing_admission':'NOT_QUALIFIED_FOR_40_80_SECOND_CASES',
    'comparison_is_not_a_controlled_performance_benchmark':True,
    'non_api_time_includes_file_handoff_local_verification_scheduling_and_supervision':True,
    'physical_bytes_for_raw_18_mib_before_manifest':4*(18*1024**2//3),
    'raw_byte_cap_cannot_be_reused_as_physical_ascii_byte_cap':True,
    'complete_score_archive_gaussian_compressibility_unmeasured':True,
    'scientific_budget_milliseconds_unchanged':7200000,'scientific_evidence_cap_unchanged':1024**3,
    'scientific_execution_authorized':False}
save('timing_admission.json',timing)
disposition={'schema':'radio-lossless-engineering-disposition-v1','scope':'lossless-live01',
    'status':'CLOSED_ENGINEERING_PASS_WITH_EXPECTED_CAPACITY_FAILURE',
    'engineering_cases_consumed':2,'engineering_cases_archived':1,'expected_failure_cases_closed':1,
    'case_milliseconds_nonrefundable':420000,'case_normal_and_failure_bytes_nonrefundable':1065216,
    'ledger_history_reserved_bytes':65536,'new_scope_retries_allowed':False,
    'old_live01':'CLOSED_FAILED_BEFORE_CONSUMPTION','old_live02':'CLOSED_FAILED_CONSUMED_INCOMPLETE',
    'old_case_milliseconds_nonrefundable':1500000,'old_case_bytes_nonrefundable':1048576,
    'cumulative_remote_engineering_cases_consumed':3,'cumulative_remote_engineering_cases_archived':1,
    'cumulative_remote_case_milliseconds_reserved':1920000,'cumulative_remote_case_bytes_reserved':2113792,
    'scientific_execution_authorized':False,'source_requests':0,'proposed_prng_constructions':0,
    'scientific_proposal_status':'PROPOSED_NOT_ACTIVATED','two_week_plan_end':'2026-10-09',
    'next':'Reduce measured request/handoff/readback latency and bind physical ASCII byte caps; then qualify fresh engineering-only Gaussian/native/gate execution, never the reserved 127/24 identities.'}
assert disposition['case_normal_and_failure_bytes_nonrefundable']==1048576+256+2*8192
save('disposition.json',disposition)
evidence={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='postflight.json'}
post={'schema':'radio-lossless-postflight-v1','status':disposition['status'],
    'new_distinct_tests':29,'unchanged_old_fixtures_rerun':0,'historical_invariant_count':len(pins),'historical_invariant_pins':pins,
    'freeze_commit':'f2af6decef6516a1329d5f841020297054b7dec5','live_final_commit':r['final_branch_head'],
    'repository_python_files':827,'runtime_files':1132,'runtime_unavailable_optional_tk_extension_unchanged':True,
    'tool_calls_before_closure':r['tool_calls'],'returned_json_bytes_before_closure':r['returned_json_bytes'],
    'live_plus_conservative_preflight_seconds':r['cumulative_active_seconds'],
    'independent_git_verification_seconds':independent['verification_seconds'],
    'post_live_git_fetch_conservative_seconds':30,'final_report_main_publication_reserve_seconds':240,
    'final_report_main_publication_reserve_calls':80,'final_report_main_response_reserve_bytes':2*1024**2,
    'scope_active_seconds_ceiling':900,'scope_calls_ceiling':220,'scope_response_bytes_ceiling':16*1024**2,
    'archive_physical_bytes':artifacts,'all_ledger_versions_bytes':state['ledger_history_bytes'],
    'archive_and_ledger_bytes':state['used_physical_bytes'],'reserved_physical_bytes':state['reserved_physical_bytes'],
    'physical_evidence_ceiling':2*1024**2,'local_saved_evidence_ceiling':16*1024**2,
    'local_saved_evidence_files':evidence,'local_saved_evidence_bytes_before_postflight':sum(x['bytes'] for x in evidence.values()),
    'physical_archive_plus_local_support_evidence_conservative_bytes':state['used_physical_bytes']+sum(x['bytes'] for x in evidence.values()),
    'peak_live_rss_bytes':r['peak_rss_bytes'],'scope_branch_advances_before_report':5,'planned_total_advances_with_report_main':7,
    'scope_branch_advances_ceiling':8,'prior_remote_scopes_seconds_charged':964.719075146,'prior_remote_scopes_calls_charged':103,
    'new_scientific_trials':0,'new_source_requests':0,'proposed_prng_constructions':0,'external_messages':0,
    'scientific_counters':{'development_closed':6,'calibration_failed_closed':3,'old_evaluation_allocations_closed':1,
        'old_evaluation_values_unopened_unusable':24,'retained_score_diagnosis_closed':1,'remedies':0,'pilots':0},
    'scientific_execution_authorized':False,'historical_holds_and_dispositions_unchanged':True,
    'postflight_generation_seconds':time.monotonic()-started}
post['active_seconds_charged_with_final_reserve']=r['cumulative_active_seconds']+independent['verification_seconds']+30+240+post['postflight_generation_seconds']
post['calls_charged_with_final_reserve']=r['tool_calls']+80
post['response_bytes_charged_with_final_reserve']=r['returned_json_bytes']+2*1024**2
assert post['active_seconds_charged_with_final_reserve']<=900
assert post['calls_charged_with_final_reserve']<=220
assert post['physical_archive_plus_local_support_evidence_conservative_bytes']+65536<=2*1024**2
save('postflight.json',post)
print(json.dumps({k:post[k] for k in ('new_distinct_tests','historical_invariant_count','active_seconds_charged_with_final_reserve','calls_charged_with_final_reserve','physical_archive_plus_local_support_evidence_conservative_bytes')}))
