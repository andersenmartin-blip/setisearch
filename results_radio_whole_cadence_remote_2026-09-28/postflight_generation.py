from pathlib import Path
import subprocess,json,hashlib,gzip,math
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater import whole_cadence_journal_radio as j
root=Path.cwd();out=root/'results_radio_whole_cadence_remote_2026-09-28'
old=json.loads(subprocess.check_output(['git','show','HEAD:results_radio_whole_cadence_compact_2026-09-28/postflight.json']))
pins=old['historical_invariant_pins']
for p,h in pins.items():
 raw=(root/p).read_bytes() if (root/p).exists() else subprocess.check_output(['git','show','HEAD:'+p])
 assert hashlib.sha256(raw).hexdigest()==h,p
for attempt,offset in (('run01',0),('run02',8)):
 tape=json.loads(gzip.decompress((out/attempt/'broker_transcript.json.gz').read_bytes()))
 events=json.loads((out/attempt/'transport_receipts.json').read_bytes());assert all('index' in e for e in events)
 for i,e in enumerate(events,1):
  req=tape[f'request{i:04d}.json'];res=tape[f'response{i:04d}.json'];assert e['index']==i+offset
  assert req['method']==e['method'];assert e['request_sha256']==digest(req['params'])
  assert e['response_sha256']==digest(res['result']);assert e['response_json_bytes']==len(canonical(res['result']))
 result=json.loads((out/attempt/'result.json').read_bytes())
 assert result['tool_calls']==len(events)+offset
 assert result['returned_json_bytes']==sum(e['response_json_bytes'] for e in events)+(500000 if offset else 0)
state=j.replay(json.loads((out/'live02/ledger.json').read_bytes()));case=state['cases'][0]
assert case['status']=='consumed' and not case['rng_started'] and set(case['artifacts'])=={'witness.json'}
assert (out/'live01/ledger.json').read_bytes()==subprocess.check_output(['git','show','b0574d0c1ebaa9a68d8da52828ba888889906d47:results_radio_whole_cadence_remote_2026-09-28/live01/ledger.json'])
result=json.loads((out/'run02/result.json').read_bytes())
readback_gap=((out/'independent_git_readback.json').stat().st_mtime_ns-(out/'run02/result.json').stat().st_mtime_ns)/1e9
assert readback_gap>0
files={str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.rglob('*') if p.is_file() and p.name!='postflight.json'}
used=sum(v['bytes'] for v in files.values());assert used<32*1024**2
r={'status':'LIVE_TRANSPORT_FAILED_CLOSED_ASCII_PREPARED_OFFLINE_ONLY','new_distinct_tests':55,
'new_test_breakdown':{'initial_and_corrected_remote_phase_runtime':40,'retained_corrupt_response':2,'ascii_envelope':12,'missing_git_inventory_guard':1},
'existing_journal_regression_tests':32,'repeated_runtime_guard_regressions':8,'historical_invariant_pins':pins,'historical_invariant_count':len(pins),
'live01':'closed_failed_before_consumption','live02':'closed_failed_consumed_incomplete',
'engineering_cases_consumed':1,'engineering_cases_completed':0,'reserved_case_milliseconds':case['milliseconds'],
'reserved_case_artifact_bytes':case['artifact_bytes'],'registered_artifact_bytes':146,'unregistered_preserved_payload_bytes':262161,
'new_scientific_trials':0,'new_source_requests':0,'proposed_prng_constructions':0,'external_messages':0,
'scientific_execution_authorized':False,'prior_scientific_counters_unchanged':True,
'live_tool_calls_charged':102,'additional_poststop_branch_inspection_calls':1,'total_live_and_diagnostic_tool_calls_charged':103,
'live_returned_json_bytes_charged':2793476,'additional_poststop_response_bytes_conservatively_charged':16384,
'live_time_charged_seconds':result['cumulative_elapsed_seconds'],'poststop_verification_wall_gap_seconds':readback_gap,
'ascii_preparation_conservative_seconds':60,'combined_time_charge_seconds':result['cumulative_elapsed_seconds']+math.ceil(readback_gap)+60,
'live_time_ceiling_seconds':1800,'local_evidence_bytes_before_postflight':used,'evidence_byte_cap':32*1024**2,
'peak_live_rss_bytes':result['peak_rss_bytes'],'current_science_head_before_report':'b49a315e6312839d423a3be65b08a7935c759b74',
'science_branch_advances_before_report':6,'planned_total_advances_including_final_science_and_main':8,
'freeze02_is_historical_only_after_new_ascii_module_and_inventory_guard':True,
'old_freeze_covers_materialized_inventory_not_complete_git_inventory':True,'evidence_files':files}
assert r['combined_time_charge_seconds']<1800
(out/'postflight.json').write_bytes(canonical(r));print(json.dumps({k:v for k,v in r.items() if k not in ('evidence_files','historical_invariant_pins')}))
