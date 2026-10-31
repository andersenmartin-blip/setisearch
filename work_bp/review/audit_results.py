"""Independent post-execution BP audit: saved bytes and scores only, no RNG/search.

This reviewer is outside the frozen execution source set. It never modifies
execution data or imports the BP generator/search code.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import time
import traceback
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
RUN=ROOT/'execution/BP_FIXED24_V1'
OUT=ROOT/'review/RESULT_REVIEW_BP.json'
Q=(63,64,65,127,129); WIDTHS=(1,3,9,33); STRIDES=(1,1,2,8)
RIS=(0,209,419,629,838); ON=(0,2,4); OFF=(1,3,5)
MJD=(57642.735972222225,57642.73994212963,57642.74390046296,
     57642.74791666667,57642.751921296294,57642.75582175926)
DF=-2.7939677238464355
START=time.monotonic()

def check(ok,message):
    if not ok: raise ValueError(message)
    if time.monotonic()-START>118: raise TimeoutError('Reviewer 118-second budget exceeded')

def read(path):return json.loads(Path(path).read_text())
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def powers(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()
def key(method,ri,width,q,kind):return f'{method}_r{ri}_w{width}_q{q}_{kind}'
def close_number(a,b):return a==b

def sorted_median(x):
    s=np.sort(x)
    n=len(s)
    return float((s[(n-1)//2]+s[n//2])/2)

def verify_sources(plan):
    for p in plan['source_pins']:
        path=REPO/p['path'];check(path.is_file() and not path.is_symlink(),'Missing/linked source')
        check(path.stat().st_size==p['bytes'] and sha(path)==p['sha256'],'Changed source '+p['path'])

def independently_force(score_arrays,method,candidate):
    width=candidate['width'];stride=STRIDES[WIDTHS.index(width)]
    ri=candidate['rate_index'];rate=-4.0+ri*(8.0/838.0)
    # np.linspace's exact rates are frozen in the plan; construct whole bank
    # only to avoid a different endpoint rounding expression for this constant.
    rate=float(np.linspace(-4.,4.,839,dtype=np.float64)[ri])
    source=candidate['source_scan'];measurements=[]
    for scan in range(6):
        gap=(MJD[scan]-MJD[source])*86400.0
        physical=float(candidate['center']+rate*gap/DF)
        center=int(np.rint(physical/stride))*stride
        radius=(math.ceil(1+.5*(8/838)*abs(gap)/abs(DF))+math.ceil(stride/2)) if scan in OFF else 0
        lo=math.ceil((center-radius)/stride)*stride
        hi=math.floor((center+radius)/stride)*stride
        points=list(range(lo,hi+1,stride));values=[];supported=True
        for c in points:
            q=c//4096
            if c%stride or q not in Q:
                supported=False;break
            a=score_arrays[scan].get(key(method,ri,width,q,'score'))
            i=(c%4096)//stride
            if a is None or not 0<=i<len(a):supported=False;break
            values.append(float(a[i]))
        measurements.append(dict(scan=scan,gap_seconds=gap,physical_center=physical,center=center,
            radius_channels=radius,points=points,supported=supported,
            ESS_values=values if supported else None,ESS=max(values) if supported else None))
    full=all(m['supported'] for m in measurements)
    on=all(measurements[s]['supported'] and measurements[s]['ESS']>=10 for s in ON)
    veto=any(measurements[s]['supported'] and measurements[s]['ESS']>=5 for s in OFF)
    flag=full and on and not veto
    status='PASS' if flag else ('UNSUPPORTED' if not full else ('THREE_ON_FAIL' if not on else 'OFF_VETO'))
    return dict(source=candidate,measurements=measurements,supported=full,three_ON_pass=on,
                OFF_veto=veto,flag=flag,status=status)

def truth_candidates(case):
    truth=case['truth'];center=truth['channel_scan0_at_row7p5'];result=[]
    for width,stride in zip(WIDTHS,STRIDES):
        radius=stride/2+1
        for j in range(math.ceil((center-radius)/stride),math.floor((center+radius)/stride)+1):
            c=j*stride
            result.append(dict(source_scan=0,rate_index=truth['rate_index'],width=width,stride=stride,
                q=c//4096,center=c,truth_offset_channels=c-center,truth_radius_channels=radius))
    return result

def load_and_verify_scores(case_root,case,counts):
    result_list=[];score_arrays=[]
    for scan in range(6):
        p=case_root/f'scan{scan}';r=read(p/'RESULT.json')
        check(r['status']=='PASS' and r['scan_index']==scan,'Wrong/unclosed scan result')
        check(sha(p/'arrays.npz')==r['evidence']['arrays.npz']['sha256'],'Score archive hash')
        with np.load(p/'arrays.npz',allow_pickle=False) as z:a={k:z[k] for k in z.files}
        lcal={(x['rate_index'],x['width']):x for x in r['calibrations'] if x['method']=='legacy_global'}
        ccal={(x['rate_index'],x['width'],x['q']):x for x in r['calibrations'] if x['method']=='current_local'}
        check(len(lcal)==20 and len(ccal)==100,'Wrong calibration domain count')
        expected_hits={'current':[],'legacy':[]};maxima=[]
        for width,stride in zip(WIDTHS,STRIDES):
            for ri in RIS:
                global_cal=lcal[(ri,width)]
                check(global_cal['domain']==[4096,1044480] and global_cal['count']==1040384//stride,'Legacy global domain shrunk')
                check(global_cal['sum_dtype']=='<f4' and len(global_cal['sum_sha256'])==64,'Legacy global digest/dtype')
                for q in Q:
                    cs=a[key('current',ri,width,q,'sum')];ls=a[key('legacy',ri,width,q,'sum')]
                    check(cs.dtype==np.float64 and ls.dtype==np.float32 and len(cs)==4096//stride and len(ls)==len(cs),'Sum type/domain')
                    cm=sorted_median(cs);scale=1.4826*sorted_median(np.abs(cs-cm))
                    check(cm==ccal[(ri,width,q)]['median'] and scale==ccal[(ri,width,q)]['MAD_scale'],'Independent sorted local calibration differs')
                    scores={'current':(cs-cm)/scale,'legacy':(ls-global_cal['median'])/global_cal['MAD_scale']}
                    for method,s in scores.items():
                        stored=a[key(method,ri,width,q,'score')]
                        check(s.dtype==stored.dtype and np.array_equal(s,stored),'ESS vector recomputation differs')
                        k=int(np.argmax(s));maxima.append(dict(method=method,rate_index=ri,width=width,q=q,center=q*4096+k*stride,ESS=float(s[k])))
                        for k in np.flatnonzero(s >= (10 if scan in ON else 5)):
                            expected_hits[method].append(dict(source_scan=scan,rate_index=ri,width=width,stride=stride,q=q,center=q*4096+int(k)*stride,ESS=float(s[k])))
                    counts['local_calibration_vectors_recomputed']+=1
                    counts['ESS_vectors_recomputed']+=2
        check(maxima==r['maxima'],'Maxima differ')
        check(expected_hits==r['hits'],'Hit catalogue differs from saved scores')
        check(len(r['oracles'])==300 and r['current_oracle_comparisons']==300 and r['legacy_staged_comparisons']==300,'Oracle counts')
        failures=0
        for o in r['oracles']:
            check(o['current_abs_error']==abs(o['current_sum']-o['current_fsum']) and o['current_abs_error']<=o['current_bound'],'Recorded current oracle bound')
            check(o['legacy_sum']==o['legacy_staged'] and o['legacy_staged_exact'],'Legacy staged oracle')
            error=abs(o['legacy_sum']-o['legacy_fsum'])
            check(error==o['legacy_abs_error'],'Legacy arithmetic error differs')
            check(o['legacy_original_guard']==('PASS' if error<=5e-5 else 'FAIL'),'Legacy guard relabeled')
            failures+=error>5e-5
        check(failures==r['legacy_original_guard_FAILs'],'Legacy fail count')
        counts['legacy_guard_FAILs_retained']+=failures
        counts['recorded_scalar_comparisons_checked']+=300
        result_list.append(r)
        score_arrays.append({k:v for k,v in a.items() if k.endswith('_score')})
    return result_list,score_arrays

def audit_case(case,body,saved_scores,base_scores,counts):
    method_values={}
    for method in ('current','legacy'):
        saved=body['method_results'][method]
        seeds=[hit for r in (body['records'][s]['scan_summary'] for s in ON) for hit in r['hits'][method]]
        check(len(seeds)==saved['source_ON_hits']==len(saved['associations']),'Source hit count differs')
        statuses={k:0 for k in ('PASS','UNSUPPORTED','THREE_ON_FAIL','OFF_VETO')}
        for source,record in zip(seeds,saved['associations']):
            force=independently_force(saved_scores,method,source)
            check(force==record,'Independent association differs')
            statuses[force['status']]+=1
            counts['six_scan_associations_recomputed']+=1
        check(statuses==saved['association_counts'] and statuses['PASS']==saved['flags'],'Association counts')
        truth=[]
        if case['truth'] is not None:
            candidates=truth_candidates(case)
            check(len(candidates)==len(saved['truth']),'Truth endpoint count')
            for candidate,record in zip(candidates,saved['truth']):
                f=independently_force(saved_scores,method,candidate)
                b=independently_force(base_scores,method,candidate) if base_scores is not None else None
                credit=f['flag'] and b is not None and b['supported'] and not b['flag']
                check(record==dict(injected=f,uninjected=b,recovery_credit=credit),'Independent truth credit differs')
                truth.append(record)
                counts['truth_endpoints_recomputed']+=1
        values=dict(flags=statuses['PASS'],recovered=any(x['recovery_credit'] for x in truth),
            supported_OFF=any(x['injected']['supported'] and x['injected']['OFF_veto'] for x in truth),
            all_three_fail=bool(truth) and all(x['injected']['supported'] and not x['injected']['three_ON_pass'] for x in truth))
        check(values['recovered']==saved['truth_recovered'],'Truth summary differs')
        method_values[method]=values
    c,l=method_values['current'],method_values['legacy'];status='PASS'
    if case['kind']=='null':status='FAIL' if c['flags'] else 'PASS'
    elif case['kind']=='positive':
        if case['amplitude']==256:status='PASS' if c['recovered'] else 'FAIL'
        else:status='REVIEW_REQUIRED' if l['recovered'] and not c['recovered'] else 'PASS'
    else:
        expected=(c['supported_OFF'] if case['case_id'] in ('A01','A02') else
                  c['all_three_fail'] if case['case_id']=='A03' else (c['supported_OFF'] or c['all_three_fail']))
        status='PASS' if not c['flags'] and expected else 'FAIL'
    check(status==body['status'],'Prospective gate status differs')
    return dict(case_id=case['id'],kind=case['kind'],amplitude=case['amplitude'],
        current_flags=c['flags'],legacy_flags=l['flags'],current_truth_recovered=c['recovered'],
        legacy_truth_recovered=l['recovered'],status=status)

def main():
    check(not OUT.exists(),'Do not overwrite reviewer result')
    terminal_path=RUN/'TERMINAL.json';check(terminal_path.is_file(),'Wait for terminal before audit')
    terminal_hash=sha(terminal_path);terminal=read(terminal_path)
    plan=read(ROOT/'BP_FIXED24_PLAN.json');freeze=read(ROOT/'PUBLIC_FREEZE_RECEIPT_BP.json')
    plan_hash=sha(ROOT/'BP_FIXED24_PLAN.json');check(plan_hash==freeze['plan_sha256'],'Plan/freeze binding')
    check(freeze['exact_readback_verified'] and freeze['before_execution'],'Missing public readback')
    verify_sources(plan)
    evidence=terminal['evidence_files'];expected={e['path']:e for e in evidence}
    check(len(expected)==len(evidence),'Duplicate evidence paths')
    actual={str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file() and p!=terminal_path}
    check(actual==set(expected),'Terminal evidence inventory changed')
    byte_count=0
    for relative,e in expected.items():
        p=RUN/relative;check(not p.is_symlink() and p.resolve().is_relative_to(RUN.resolve()),'Unsafe evidence path')
        check(p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],'Evidence mismatch '+relative)
        byte_count+=e['bytes']
    counts=dict(evidence_files_rehashed=len(evidence),evidence_bytes_rehashed=byte_count,
        base_arrays_verified=0,common_scan_inputs_verified=0,injected_arrays_reconstructed=0,
        local_calibration_vectors_recomputed=0,ESS_vectors_recomputed=0,
        recorded_scalar_comparisons_checked=0,legacy_guard_FAILs_retained=0,
        six_scan_associations_recomputed=0,truth_endpoints_recomputed=0)
    base_verified={}
    for p in sorted((RUN/'bases').glob('seed*/scan*.npy')):
        r=read(p.with_suffix('.json'));a=np.load(p,mmap_mode='r',allow_pickle=False)
        check(a.shape==(16,1048576) and a.dtype==np.dtype('<f4') and a.flags.c_contiguous and not a.flags.writeable,'Base structure')
        check(sha(p)==r['file_sha256'] and powers(a)==r['powers_sha256'],'Base payload differs')
        check(r['scan']==int(p.stem[4:]) and r['spawn_key']==[r['scan']] and r['seed']==2026103000+r['seed_index'],'RNG stream metadata')
        check(r['requested_variates']==16777216 and r['distribution_calls']==1 and r['primitive_draw_count'] is None,'Random variate accounting')
        base_verified[(r['seed_index'],r['scan'])]=r
        counts['base_arrays_verified']+=1
    summaries=[];baseline_cache={};capture_summaries=[]
    for i,entry in enumerate(terminal['case_receipts']):
        case=plan['cases'][i];check(case['id']==entry['case_id'],'Case order differs')
        case_root=RUN/case['id'];receipt=read(case_root/'ACTUAL_RECEIPT.json')
        check(receipt['context']['case_id']==case['id'] and receipt['context']['index']==i,'Receipt context')
        check(receipt['status']==entry['status'],'Receipt status differs')
        for field in ('child_wait_completed','stdout_eof','stdout_fully_preserved',
                      'descendant_cleanup_completed','source_pins_verified_before','source_pins_verified_after'):
            check(receipt[field], 'Closed receipt field false '+field)
        check(receipt['remaining_live_descendants']==[],'Descendants remain')
        log=case_root/'STDOUT.log';content=log.read_bytes();digest=sha(log)
        check(len(content)==receipt['log_bytes']==receipt['observed_stdout_bytes'],'Log bytes differ')
        check(digest==receipt['log_sha256']==receipt['observed_stdout_sha256'],'Log digest differs')
        result_path=case_root/'payload/RESULT.json'
        capture_summaries.append(dict(case_id=case['id'],status=receipt['status'],actual_exit_code=receipt['actual_exit_code'],
            natural_stdout_eof=receipt['natural_stdout_eof'],killed=receipt['killed'],reasons=receipt['reasons'],
            peak_tree_RSS_bytes=receipt['resources']['peak_tree_RSS_bytes'],max_child_RSS_bytes=receipt['resources']['max_child_RSS_bytes']))
        if not result_path.exists():
            check(case['id']=='A04' and receipt['status']=='FAIL' and receipt['actual_exit_code']==-9
                  and receipt['killed'] and not receipt['natural_stdout_eof'],'Unexpected missing case result')
            check('CHILD_TREE_RSS_CAP_EXCEEDED' in receipt['reasons'],'Missing RSS stop evidence')
            check(receipt['result_sha256'] is None and entry['result_sha256'] is None,'Invented result binding')
            log_events=[json.loads(line) for line in content.splitlines()]
            check([e.get('scan') for e in log_events if e.get('event')=='SCAN_COMPLETE']==list(range(6)),
                  'Incomplete scan event sequence')
            scans,scores=load_and_verify_scores(case_root/'payload',case,counts)
            for scan,sresult in enumerate(scans):
                baseline=base_verified[(case['base_seed_index'],scan)]
                base=np.load(RUN/'bases'/f'seed{case["base_seed_index"]:02d}'/f'scan{scan}.npy',mmap_mode='r',allow_pickle=False)
                dp=case_root/'payload'/f'delta_scan{scan}.npz'
                with np.load(dp,allow_pickle=False) as z:
                    rows=z['rows'];cols=z['channels'];delta=z['delta_float64'];rounded=z['resulting_float32']
                    rr,cc=np.meshgrid(np.arange(*case['row_interval'],dtype=np.int64),np.arange(*case['channel_interval'],dtype=np.int64),indexing='ij')
                    check(np.array_equal(rows,rr.ravel()) and np.array_equal(cols,cc.ravel()),'A04 sparse geometry differs')
                    check(np.array_equal(delta,(case['broad_gain']-1)*base[rows,cols].astype(np.float64)),'A04 broad delta recipe differs')
                    check(np.array_equal((base[rows,cols].astype(np.float64)+delta).astype(np.float32),rounded),'A04 rounding differs')
                    rebuilt=np.array(base,copy=True);rebuilt[rows,cols]=rounded
                    digest=powers(rebuilt);del rebuilt
                check(digest==sresult['input_powers_sha256_before']==sresult['input_powers_sha256_after'],'A04 shared input reconstruction mismatch')
                counts['injected_arrays_reconstructed']+=1;counts['common_scan_inputs_verified']+=1
            summaries.append(dict(case_id=case['id'],status='CAPTURE_FAIL_RSS',assessment_complete=False,
                completed_scans_verified=6,injection_receipts_present=False,
                verification='Declared immutable base+saved sparse deltas reconstructed and matched to all six scan input hashes; no absent receipt invented.',
                association_gate_status='NOT_COMPLETED',actual_exit_code=-9))
            continue
        check(sha(result_path)==receipt['result_sha256']==entry['result_sha256'],'Result digest binding')
        footer=json.loads(content.splitlines()[-1]);check(footer['result_sha256']==sha(result_path),'Footer result binding')
        body=read(result_path)
        if receipt['status']=='PASS':
            check(receipt['actual_exit_code']==0 and body['status']=='PASS' and receipt['natural_stdout_eof'],'Pass without successful natural exit/result')
        else:check(receipt['actual_exit_code']!=0 or receipt['reasons'],'Failed receipt lacks failure evidence')
        if body.get('schema')!='SETI_BP_CASE_RESULT_V1':
            summaries.append(dict(case_id=case['id'],status=body['status'],exception=body.get('exception'),assessment_complete=False))
            continue
        scans,scores=load_and_verify_scores(case_root/'payload',case,counts)
        for scan,(record,sresult) in enumerate(zip(body['records'],scans)):
            check(record['scan_summary']==sresult,'Case/scan duplicate differs')
            inj=record['injection_receipt'];baseline=base_verified[(case['base_seed_index'],scan)]
            check(record['base_receipt']==baseline,'Base receipt binding differs')
            check(inj['base_file_sha256']==baseline['file_sha256'] and inj['base_powers_sha256']==baseline['powers_sha256'],'Injection base binding')
            base=np.load(RUN/'bases'/f'seed{case["base_seed_index"]:02d}'/f'scan{scan}.npy',mmap_mode='r',allow_pickle=False)
            if inj['injected']:
                dp=Path(inj['delta_path']);check(dp.resolve().is_relative_to((case_root/'payload').resolve()) and sha(dp)==inj['delta_file_sha256'],'Delta binding')
                with np.load(dp,allow_pickle=False) as z:
                    rows=z['rows'];cols=z['channels'];delta=z['delta_float64'];rounded=z['resulting_float32']
                    check(delta.dtype==np.float64 and rounded.dtype==np.float32,'Delta dtype')
                    check(len(np.unique(rows*1048576+cols))==len(rows),'Duplicate delta pixels')
                    check(np.array_equal((base[rows,cols].astype(np.float64)+delta).astype(np.float32),rounded),'Delta rounding differs')
                    rebuilt=np.array(base,copy=True);rebuilt[rows,cols]=rounded
                    digest=powers(rebuilt);del rebuilt
                counts['injected_arrays_reconstructed']+=1
            else:digest=baseline['powers_sha256']
            check(digest==inj['common_input_powers_sha256']==sresult['input_powers_sha256_before']==sresult['input_powers_sha256_after'],'Common input reconstruction mismatch')
            counts['common_scan_inputs_verified']+=1
        if case['kind']=='null' and case['base_seed_index'] in (3,4):baseline_cache[case['base_seed_index']]=scores
        summary=audit_case(case,body,scores,baseline_cache.get(case['base_seed_index']) if case['kind']!='null' else None,counts)
        summaries.append(summary)
    all_pass=terminal['status']=='PASS'
    check(len(summaries)==terminal['completed_cases'] and sum(x['status']=='PASS' for x in capture_summaries)==terminal['passed_cases'],'Terminal totals differ')
    if all_pass:check(len(summaries)==24 and counts['base_arrays_verified']==48 and all(x['status']=='PASS' for x in summaries),'Invalid complete-phase PASS')
    else:check(any(x['status']!='PASS' for x in capture_summaries) and len(summaries)<=24,'Failed phase not preserved')
    check(terminal['historical_HIP45688_M_failures']==24 and terminal['historical_full_QA'] is False,'Historical status changed')
    check(all(terminal[k]==0 for k in ('astronomical_powers_opened','new_observations','new_archive_requests','new_coverage_credit')),'Unexpected science activation')
    verify_sources(plan);check(sha(terminal_path)==terminal_hash,'Terminal changed during review')
    result=dict(schema='SETI_BP_INDEPENDENT_RESULT_REVIEW_V1',
        status='PASS_INDEPENDENT_EVIDENCE_REVIEW',control_phase_status=terminal['status'],
        public_freeze_commit=freeze['public_commit_sha'],plan_sha256=plan_hash,terminal_sha256=terminal_hash,
        counts=counts,cases=summaries,capture=capture_summaries,
        all_started_identities_preserved=True,historical_failures_preserved=True,
        new_rng_calls=0,new_scan_searches=0,astronomical_inputs_opened=0,
        wall_seconds=time.monotonic()-START,completed_utc=datetime.now(timezone.utc).isoformat(),
        limitations=['Saved local ESS and six-scan endpoints were independently recalculated; numerical scalar checks were audited from recorded evidence, not rescored from full normalized matrices.',
                    'Legacy full-global vector hashes/domain/calibration are preserved; full-global medians were not independently recomputed in this postrun audit.',
                    'A04 lacks its case-level injection/result receipts. Its six saved scan inputs are reconstructed from known immutable base arrays and saved deltas, without inventing missing receipts or completing association.',
                    'This review does not change a failed control phase to PASS and does not authorize full839 or astronomical inputs.'])
    with OUT.open('x') as f:json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=result['status'],control_phase_status=result['control_phase_status'],counts=counts,wall_seconds=result['wall_seconds'],report_sha256=sha(OUT))),flush=True)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except BaseException as exc:
        if isinstance(exc,SystemExit):raise
        failure=dict(status='FAIL_REVIEW',exception=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),wall_seconds=time.monotonic()-START)
        path=ROOT/'review/REVIEW_ATTEMPT_FAILURE_BP.json'
        with path.open('x') as f:json.dump(failure,f,indent=2);f.write('\n')
        print(json.dumps(failure),flush=True);sys.exit(2)
