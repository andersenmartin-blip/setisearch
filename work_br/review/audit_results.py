"""Independent saved-score BR stream audit; never RNG or scan scoring."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import time
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
RUN=ROOT/'execution/BR_A04_ASSOC_V1'
BP=REPO/'work_bp/execution/BP_FIXED24_V1'
OUT=ROOT/'review/RESULT_REVIEW_BR.json'
START=time.monotonic()
helper_path=REPO/'work_bp/review/audit_results.py'
spec=importlib.util.spec_from_file_location('independent_bp_saved_score_review',helper_path)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def check(ok,message):
    if not ok:raise ValueError(message)
    if time.monotonic()-START>118:raise TimeoutError('BR reviewer118second bound exceeded')
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify_pins(pins):
    for row in pins:
        p=REPO/row['path'];check(p.resolve().is_relative_to(REPO) and not p.is_symlink(),'Unsafe pin')
        check(p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'Changed pin '+row['path'])
def verify_bp(terminal):
    check(terminal['status']=='FAIL' and terminal['passed_cases']==23 and terminal['completed_cases']==24,'BP failed identity changed')
    count=0;size=0
    actual={str(p.relative_to(BP)) for p in BP.rglob('*') if p.is_file() and p.name!='TERMINAL.json'}
    expected={row['path'] for row in terminal['evidence_files']}
    check(actual==expected,'BP evidence inventory changed')
    for row in terminal['evidence_files']:
        p=BP/row['path'];check(not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'BP evidence changed '+row['path'])
        count+=1;size+=row['bytes']
    return count,size

def load_scores(identity):
    results=[];arrays=[]
    for scan in range(6):
        folder=BP/identity/'payload'/f'scan{scan}';r=read(folder/'RESULT.json')
        check(r['status']=='PASS' and r['scan_index']==scan,'Wrong closed scan')
        check(sha(folder/'arrays.npz')==r['evidence']['arrays.npz']['sha256'],'Score archive mismatch')
        with np.load(folder/'arrays.npz',allow_pickle=False) as z:
            arrays.append({k:z[k] for k in z.files if k.endswith('_score')})
        results.append(r)
    return results,arrays

def main():
    check(not OUT.exists(),'No review overwrite')
    plan_path=ROOT/'BR_POSTPROCESSING_PLAN.json';plan=read(plan_path)
    freeze=read(ROOT/'PUBLIC_FREEZE_RECEIPT_BR.json')
    check(freeze['exact_readback_verified'] and freeze['before_execution'] and freeze['plan_sha256']==sha(plan_path),'Public freeze binding')
    pins=plan['source_pins']+plan['input_pins'];verify_pins(pins)
    terminal_path=RUN/'TERMINAL_BR.json';terminal=read(terminal_path);terminal_hash=sha(terminal_path)
    check(terminal['status']=='PASS' and terminal['actual_exit_code']==0 and terminal['BP_original_status']=='FAIL','BR closure status')
    evidence=terminal['files'];expected={r['path'] for r in evidence}
    actual={str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file() and p!=terminal_path}
    check(actual==expected and len(expected)==len(evidence),'BR evidence inventory changed')
    new_bytes=0
    for row in evidence:
        p=RUN/row['path'];check(not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'BR evidence hash mismatch')
        new_bytes+=row['bytes']
    receipt_path=RUN/'A04_POSTPROCESSING/ACTUAL_RECEIPT.json';receipt=read(receipt_path)
    check(sha(receipt_path)==terminal['receipt_sha256'],'Capture receipt binding')
    check(receipt['status']=='PASS' and receipt['actual_exit_code']==0 and receipt['reasons']==[],'Unsuccessful capture')
    for key in ('child_wait_completed','stdout_eof','natural_stdout_eof','stdout_fully_preserved','descendant_cleanup_completed',
                'source_pins_verified_before','source_pins_verified_after','process_namespace_mapping_verified'):
        check(receipt[key],'False capture field '+key)
    check(not receipt['killed'] and receipt['remaining_live_descendants']==[],'Unclean process tree')
    resource=receipt['resources'];caps=plan['caps']
    check(resource['max_child_RSS_bytes']<=caps['rss_bytes'] and resource['peak_tree_RSS_bytes']<=caps['rss_bytes'],'RSS cap exceeded')
    check(resource['wall_seconds']<=caps['wall_seconds'],'Wall cap exceeded')
    check(resource['child_user_cpu_seconds']+resource['child_system_cpu_seconds']+resource['capture_parent_cpu_seconds']<=caps['cpu_seconds'],'CPU cap exceeded')
    check(new_bytes+terminal_path.stat().st_size<=caps['stored_bytes'],'Stored byte cap exceeded')
    log=RUN/'A04_POSTPROCESSING/STDOUT.log';logbytes=log.read_bytes();loghash=sha(log)
    check(len(logbytes)==receipt['observed_stdout_bytes']==receipt['log_bytes'],'Capture log size differs')
    check(loghash==receipt['observed_stdout_sha256']==receipt['log_sha256'],'Capture log digest differs')
    payload=RUN/'A04_POSTPROCESSING/payload';result_path=payload/'RESULT.json';result=read(result_path)
    check(sha(result_path)==receipt['result_sha256']==terminal['result_sha256'],'Result hash binding')
    footer=json.loads(logbytes.splitlines()[-1]);check(footer['event']=='GATE_TERMINAL_EOF' and footer['status']=='PASS' and footer['result_sha256']==sha(result_path),'Terminal stdout differs')
    check(result['status']=='PASS' and result['execution_identity']=='BR_A04_ASSOC_V1','Wrong result identity')
    check(result['BP_original_status']=='FAIL' and result['BP_original_passed_cases']==23 and result['BP_terminal_status_preserved']=='FAIL','Original BP status relabeled')
    for field in ('new_RNG_calls','RNG_calls','new_scan_searches','new_scan_scores','astronomical_powers_opened','new_archive_requests'):
        check(result[field]==0,'Unexpected operation '+field)
    bp_terminal_path=BP/'TERMINAL.json';bp_terminal=read(bp_terminal_path);bp_terminal_hash=sha(bp_terminal_path)
    bp_files,bp_bytes=verify_bp(bp_terminal)
    scan_results,scores=load_scores('A04');_,baseline=load_scores('N04')
    case=plan['case'];case0=read(REPO/'work_bp/BP_FIXED24_PLAN.json')['cases'][-1]
    check(case==case0 and case['id']=='A04','Changed A04 recipe')
    summaries={};total=0;truth_count=0
    for method in ('current','legacy'):
        saved=result['method_results'][method];stream=saved['association_stream'];p=payload/stream['path']
        check(p.resolve().is_relative_to(payload) and p.stat().st_size==stream['bytes'] and sha(p)==stream['sha256'],'Association stream binding')
        counts={k:0 for k in ('PASS','UNSUPPORTED','THREE_ON_FAIL','OFF_VETO')}
        n=0
        with p.open('rb') as f:
            for scan in (0,2,4):
                for candidate in scan_results[scan]['hits'][method]:
                    line=f.readline();check(bool(line) and line.endswith(b'\n'),'Truncated association stream')
                    record=json.loads(line);expected_record=helper.independently_force(scores,method,candidate)
                    check(record==expected_record,'Independent streamed association mismatch')
                    counts[record['status']]+=1;n+=1
            check(f.read(1)==b'','Extra association lines')
        check(n==stream['records']==saved['source_ON_hits'] and n<=50000 and counts==saved['association_counts'],'Association count/order differs')
        check(stream['complete'] and saved['flags']==counts['PASS'],'Incomplete stream/flags')
        truth=[];candidates=helper.truth_candidates(case)
        check(len(candidates)==len(saved['truth']),'Wrong truth list')
        for candidate,record in zip(candidates,saved['truth']):
            a=helper.independently_force(scores,method,candidate)
            b=helper.independently_force(baseline,method,candidate)
            credit=a['flag'] and b['supported'] and not b['flag']
            expected_record=dict(injected=a,uninjected=b,recovery_credit=credit)
            check(record==expected_record,'Truth endpoint mismatch')
            truth.append(record);truth_count+=1
        recovered=any(t['recovery_credit'] for t in truth)
        supported_off=any(t['injected']['supported'] and t['injected']['OFF_veto'] for t in truth)
        three_fail=bool(truth) and all(t['injected']['supported'] and not t['injected']['three_ON_pass'] for t in truth)
        check(recovered==saved['truth_recovered'] and supported_off==saved['truth_any_supported_OFF_veto']
              and three_fail==saved['truth_all_supported_fail_three_ON'],'Truth summaries differ')
        summaries[method]=dict(source_ON_hits=n,association_counts=counts,stream_bytes=stream['bytes'],
            stream_sha256=stream['sha256'],truth_recovered=recovered,supported_truth_OFF_veto=supported_off,
            all_truth_supported_three_ON_rejection=three_fail)
        total+=n
    current=summaries['current'];expected_gate=current['association_counts']['PASS']==0 and (current['supported_truth_OFF_veto'] or current['all_truth_supported_three_ON_rejection'])
    check(expected_gate and result['current_flags']==current['association_counts']['PASS'],'Original A04 gate differs')
    child_closure=result['child_stream_closure'];parent_closures=terminal['parent_stream_closure']
    check(result['output_bindings_verified'] and result['original_computation_status_preserved']=='PASS','Child output closure missing')
    check(child_closure['status']=='PASS' and child_closure['effective_status']=='PASS' and child_closure['stage']=='child_end','Child stream fence failed')
    check(len(parent_closures)==2 and terminal['capture_status']=='PASS' and terminal['closing_errors']==[] and terminal['final_inventory_matches_result_manifests'],'Parent stream closure or final inventory binding missing')
    for fence in parent_closures:
        check(fence['stage']=='parent_end' and fence['status']=='PASS' and fence['effective_status']=='PASS','Parent stream fence failed')
        check(fence['verification']==child_closure['verification'],'Cross-fence metadata differs')
    for entry in child_closure['verification']['streams']:
        p=payload/entry['path'];st=p.stat();method=entry['method'];sm=summaries[method]
        check(st.st_dev==entry['file_device'] and st.st_ino==entry['file_inode'] and st.st_mtime_ns==entry['mtime_ns'] and st.st_ctime_ns==entry['ctime_ns'],'Stream identity changed after parent closure')
        check(entry['bytes']==sm['stream_bytes'] and entry['sha256']==sm['stream_sha256'] and entry['records']==sm['source_ON_hits'] and entry['status_counts']==sm['association_counts'],'Stream closure content differs')
        check(st.st_mode & 0o222 == 0,'Published stream not read-only')
    check(terminal['total_cpu_seconds_including_parent_closure']<=plan['caps']['cpu_seconds'] and terminal['wall_seconds_including_parent_closure']<=plan['caps']['wall_seconds'],'Parent-inclusive resource limit')
    bq_effective=read(REPO/'work_bq/EFFECTIVE_STATUS_BQ.json')
    check(bq_effective['status']=='EVIDENCE_FAIL' and bq_effective['cause']=='UNESTABLISHED','BQ evidence failure relabeled')
    check(terminal['BQ_effective_status']=='EVIDENCE_FAIL' and result['BQ_effective_status']=='EVIDENCE_FAIL' and result['BQ_effective_failure_preserved'],'BR failed to preserve BQ failure')
    prior_bq=read(REPO/'work_bq/execution/BQ_A04_ASSOC_V1/A04_POSTPROCESSING/payload/RESULT.json')
    for method in ('current','legacy'):
        original=prior_bq['method_results'][method]['association_stream']
        summaries[method]['matches_prior_BQ_declared_full_stream']=(summaries[method]['stream_sha256']==original['sha256'] and summaries[method]['stream_bytes']==original['bytes'] and summaries[method]['source_ON_hits']==original['records'])
    verify_pins(pins);bp_files2,bp_bytes2=verify_bp(bp_terminal)
    check(sha(bp_terminal_path)==bp_terminal_hash and sha(terminal_path)==terminal_hash,'Terminal changed during audit')
    check((bp_files,bp_bytes)==(bp_files2,bp_bytes2),'BP inventory changed during audit')
    report=dict(schema='SETI_BR_INDEPENDENT_RESULT_REVIEW_V1',status='PASS_INDEPENDENT_STREAM_REVIEW',
        BR_control_status='PASS',BP_original_control_status='FAIL',BP_original_passed_cases=23,BQ_effective_status_preserved='EVIDENCE_FAIL',child_closure_verified=True,parent_closure_checks_verified=2,
        public_freeze_commit=freeze['public_commit_sha'],plan_sha256=sha(plan_path),BR_terminal_sha256=terminal_hash,
        BP_terminal_sha256=bp_terminal_hash,reviewer_source_sha256=sha(Path(__file__)),
        independent_helper_source_sha256=sha(helper_path),
        BR_evidence_files_rehashed=len(evidence),BR_evidence_bytes_rehashed=new_bytes,
        BP_evidence_files_rehashed_twice=bp_files,BP_evidence_bytes_per_pass=bp_bytes,
        complete_six_scan_associations_recomputed=total,truth_endpoints_recomputed=truth_count,methods=summaries,
        source_pins_verified=len(plan['source_pins']),input_pins_verified=len(plan['input_pins']),execution_resources=resource,actual_execution_exit_code=receipt['actual_exit_code'],exact_child_wait=True,natural_EOF=True,cleanup_complete=True,
        reviewer_new_RNG_calls=0,reviewer_new_scan_searches=0,astronomical_powers_opened=0,
        wall_seconds=time.monotonic()-START,completed_utc=datetime.now(timezone.utc).isoformat(),
        qualification='A04 saved-score association completed under separate BR identity with original endpoints. BP resource failure remainsFAIL and BQ evidence failure remainsEVIDENCE_FAIL with causeUNESTABLISHED. No full839,DATAadmission,astronomical search,FAP or sensitivity qualification.')
    with OUT.open('x') as f:json.dump(report,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=report['status'],associations=total,truth_endpoints=truth_count,methods=summaries,
        wall_seconds=report['wall_seconds'],report_sha256=sha(OUT))),flush=True)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except BaseException as exc:
        if isinstance(exc,SystemExit):raise
        import traceback
        failure=dict(status='FAIL_REVIEW',exception=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),wall_seconds=time.monotonic()-START)
        with (ROOT/'review/REVIEW_ATTEMPT_FAILURE_BR.json').open('x') as f:json.dump(failure,f,indent=2);f.write('\n')
        print(json.dumps(failure),flush=True);sys.exit(2)
