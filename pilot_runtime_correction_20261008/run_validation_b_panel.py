#!/usr/bin/env python3
"""Once-only B coordinator with rolling exclusive whole-child CPU partitions.

No science imports, arrays or RNG at preparation/import. All new B admissions
derive from one public root admission, closed A and fresh committed DEV proof.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

STARTED=time.monotonic()
BASE=Path(__file__).resolve().parent.parent
CLAIMS=BASE/'pilot_protocol_20261008/validation_b_claims'
OUTPUT=BASE/'results/radio_pilot_val_b_20261008'
PARTITION=1800.
FINAL_MARGIN=30.

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise ValueError('Missing operational worker')
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value

def controller_cpu():
    r=resource.getrusage(resource.RUSAGE_SELF)
    return float(r.ru_utime+r.ru_stime)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--admission',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args()
    worker_path=Path(__file__).with_name('run_validation_b.py')
    worker=module(worker_path,'prospective_b_worker_no_rng')
    master,paths,hashes,banks,summarizer=worker.admission(args.admission)
    if master['status']!='ADMITTED_VAL_B_ROLLING': raise ValueError('Whole B rolling admission required')
    if master['sha256'].get('coordinator')!=worker.digest(Path(__file__)):
        raise ValueError('Coordinator source not bound to root public freeze')
    cases=banks['validation_b_cases']
    if master['allowed_case_ids']!=[c['case_id'] for c in cases]:
        raise ValueError('Exactly142 prespecified B identities in original order required')
    budget=float(master['budget']['aggregate_cpu_allocation_seconds'])
    if not PARTITION+FINAL_MARGIN<=budget<=22000 or float(master['budget']['remaining_cpu_seconds'])<budget:
        raise ValueError('Root must admit enough aggregate capacity, never more than22000 CPU seconds')
    if int(master['budget']['max_concurrent_children'])!=8:
        raise ValueError('Exactly bounded maximum eight children required')
    if args.output.resolve()!=OUTPUT or OUTPUT.exists() or Path(master['claim_directory']).resolve()!=CLAIMS:
        raise ValueError('Canonical new B panel output/claims required')
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    CLAIMS.mkdir(parents=True,exist_ok=True)
    worker.durable_json(CLAIMS/'controller_claim.json',{'status':'ONCE_ONLY_B_PANEL_CLAIMED',
        'master_admission_SHA256':worker.digest(args.admission),'case_ids':[c['case_id'] for c in cases],
        'no_restart_or_redraw':True},exclusive=True)
    OUTPUT.mkdir(parents=True,exist_ok=False)
    slots=[{'case_index':i,'case_id':c['case_id'],'maximum_whole_child_cpu_seconds':PARTITION,
            'status':'PLANNED_IDENTITY_SLOT_NOT_CPU_RESERVED','output_directory':str(OUTPUT/f'case_{i:03d}')}
           for i,c in enumerate(cases)]
    worker.durable_json(OUTPUT/'full_panel_plan.json',{'case_count':142,'all_slots':slots,
        'aggregate_cpu_allocation_seconds':budget,'max_concurrent_children':8,
        'slots_are_not_simultaneous_142_case_cpu_reservations':True},exclusive=True)
    running={};outcomes={};reaps=[];charged=0.;next_case=0;failure=None
    master_hash=worker.digest(args.admission)
    env=os.environ.copy()
    for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        env[variable]='1'
    def ledger():
        held=PARTITION*len(running)
        return {'status':'RUNNING_ROLLING_EXCLUSIVE','aggregate_cpu_allocation_seconds':budget,
            'cpu_charged_closed_children':charged,'controller_cpu_s_observed':controller_cpu(),
            'cpu_reserved_live_children':held,'controller_finalization_cpu_margin':FINAL_MARGIN,
            'cpu_available_for_new_partition':budget-charged-held-controller_cpu()-FINAL_MARGIN,
            'live_case_ids':[v['case']['case_id'] for v in running.values()],
            'completed_reaped_count':len(reaps),'next_frozen_case_index':next_case}
    def persist(): worker.durable_json(OUTPUT/'rolling_cpu_ledger.json',ledger())
    def failed_outcome(case,error):
        return {'case_id':case['case_id'],'panel':'VAL_B','family':case['family'],
            'data_integrity_ok':False,'all_active_on_recovered':False,'any_localized_on_recovered':False,
            'pre_OFF_all_active_recovery':False,'pre_OFF_any_active_recovery':False,'survivor_count':0,
            'failure':{'type':'OperationalFailure','message':str(error)}}
    try:
        persist()
        while next_case<142 or running:
            while (failure is None and next_case<142 and len(running)<8 and
                   ledger()['cpu_available_for_new_partition']>=PARTITION):
                index=next_case;case=cases[index];next_case+=1
                reservation_path=OUTPUT/f'reservation_{index:03d}.json'
                closure_path=OUTPUT/f'closure_{index:03d}.json'
                case_output=OUTPUT/f'case_{index:03d}'
                reservation={'case_id':case['case_id'],'case_index':index,
                    'status':'RESERVED_BEFORE_CHILD_SUBMIT','cpu_reserved_seconds':PARTITION,
                    'master_admission_SHA256':master_hash,'output_directory':str(case_output)}
                worker.durable_json(reservation_path,reservation,exclusive=True)
                single=copy.deepcopy(master);single['status']='ADMITTED_VAL_B_SINGLE_CASE'
                single['allowed_case_ids']=[case['case_id']]
                single['reservation_path']=str(reservation_path);single['closure_path']=str(closure_path)
                single['budget']['exclusive_cpu_allocation_seconds']=PARTITION
                single['budget']['remaining_cpu_seconds']=PARTITION
                admission_path=OUTPUT/f'admission_{index:03d}.json'
                worker.durable_json(admission_path,single,exclusive=True)
                log_path=OUTPUT/f'case_{index:03d}.log'
                log=log_path.open('xb')
                command=[sys.executable,'-u',str(worker_path),'--admission',str(admission_path),
                         '--case',case['case_id'],'--output',str(case_output)]
                worker.durable_json(OUTPUT/f'command_{index:03d}.json',{'argv':command,'case_id':case['case_id']},exclusive=True)
                # The exclusive partition enters durable accounting BEFORE submit.
                token=-index-1
                running[token]={'case':case,'index':index,'reservation':reservation,'closure_path':closure_path}
                persist()
                try:
                    start=time.monotonic()
                    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,
                                              start_new_session=True)
                except BaseException as error:
                    del running[token];log.close()
                    # No reliable whole-child meter on a spawn failure: charge
                    # the entire allocation, never an assumed zero/refund.
                    charged+=PARTITION
                    outcome=failed_outcome(case,error);outcome.update(cpu_s=PARTITION,wall_s=0.,peak_rss_bytes=0)
                    outcomes[index]=outcome
                    closure={'case_id':case['case_id'],'status':'FAILED_CLOSED_SPAWN',
                             'cpu_charged_seconds':PARTITION,'unused_reservation_refunded_seconds':0.}
                    worker.durable_json(closure_path,closure,exclusive=True);reaps.append(closure);persist()
                    continue
                del running[token]
                running[process.pid]={'case':case,'index':index,'process':process,'log':log,
                    'started':start,'case_output':case_output,'closure_path':closure_path}
                persist()
            if not running:
                if next_case<142:
                    failure='Insufficient remaining capacity for another full1800-CPU-second exclusive partition'
                break
            for pid,item in list(running.items()):
                waited,status,usage=os.wait4(pid,os.WNOHANG)
                if waited==0:
                    if time.monotonic()-item['started']>1800:
                        try: os.killpg(pid,signal.SIGKILL)
                        except ProcessLookupError: pass
                    continue
                item['process'].returncode=os.waitstatus_to_exitcode(status)
                item['log'].close()
                measured_cpu=float(usage.ru_utime+usage.ru_stime)
                measured_wall=time.monotonic()-item['started']
                output=item['case_output'];case=item['case'];index=item['index']
                try:
                    outcome=json.loads((output/'outcome.json').read_text())
                    marker=json.loads((output/'COMMITTED.json').read_text())
                    resource_receipt=json.loads((output/'resource_receipt.json').read_text())
                    if (item['process'].returncode!=0 or marker.get('status')!='COMPLETED_CASE_ONLY'
                        or marker.get('case_id')!=case['case_id'] or marker.get('panel')!='VAL_B'
                        or marker.get('caps_passed') is not True or not resource_receipt['caps_passed']
                        or marker['artifact_manifest_SHA256']!=worker.digest(output/'artifact_manifest.json')):
                        raise ValueError('Child has no complete durable successful commit')
                    manifest=json.loads((output/'artifact_manifest.json').read_text())
                    for name,value in manifest.items():
                        if worker.digest(output/name)!=value['SHA256']: raise ValueError('Committed child bytes changed')
                    required=[f'scan_{i:02d}_full_map.npz' for i in range(6)]+['localized_recovery.json','outcome.json']
                    if any(name not in manifest for name in required): raise ValueError('Full scientific outputs absent')
                except BaseException as error:
                    raw_path=output/'outcome.json'
                    try:
                        outcome=json.loads(raw_path.read_text())
                        if not isinstance(outcome,dict): raise ValueError('Outcome is not an object')
                    except (OSError,ValueError,TypeError):
                        outcome=failed_outcome(case,error)
                    outcome['data_integrity_ok']=False
                    if outcome.get('failure') is None: outcome['failure']={'type':type(error).__name__,'message':str(error)}
                try:
                    snapshot_cpu=float(outcome['cpu_s'])
                    snapshot_wall=float(outcome['wall_s'])
                    snapshot_rss=int(outcome['peak_rss_bytes'])
                    if (not math.isfinite(snapshot_cpu) or snapshot_cpu<0 or not math.isfinite(snapshot_wall)
                        or snapshot_wall<0 or snapshot_rss<0): raise ValueError('Invalid child resource snapshot')
                except (KeyError,ValueError,TypeError,OverflowError):
                    # The wait4 meter remains authoritative. An untrusted child
                    # snapshot never earns an assumed unused-capacity refund.
                    snapshot_cpu=PARTITION;snapshot_wall=measured_wall;snapshot_rss=usage.ru_maxrss*1024
                    outcome['data_integrity_ok']=False
                    outcome['failure']={'type':'InvalidChildResourceSnapshot','message':'Full partition charged without refund'}
                charge=max(measured_cpu,snapshot_cpu)
                if measured_cpu>PARTITION or measured_wall>1800 or usage.ru_maxrss*1024>4*1024**3:
                    outcome['data_integrity_ok']=False
                    outcome['failure']={'type':'WholeChildResourceLimit','message':'Authoritative reap exceeded corrected cap'}
                outcome.update(worker_snapshot_cpu_s=snapshot_cpu,cpu_s=charge,
                    wall_s=max(snapshot_wall,measured_wall),
                    peak_rss_bytes=max(snapshot_rss,usage.ru_maxrss*1024))
                closure={'case_id':case['case_id'],'status':'REAPED_AND_CHARGED',
                    'child_exit_code':item['process'].returncode,'wait4_whole_child_cpu_s':measured_cpu,
                    'wait4_peak_rss_bytes':usage.ru_maxrss*1024,'whole_child_wall_s':measured_wall,
                    'cpu_charged_seconds':charge,'unused_reservation_refunded_seconds':max(0.,PARTITION-charge),
                    'case_integrity_passed':outcome['data_integrity_ok']}
                # Durable closure precedes removing this live reservation; this
                # is the only point at which unused held capacity is released.
                worker.durable_json(item['closure_path'],closure,exclusive=True)
                charged+=charge;del running[pid];reaps.append(closure);outcomes[index]=outcome
                persist()
                print(json.dumps({k:outcome.get(k) for k in ('case_id','data_integrity_ok','all_active_on_recovered',
                    'pre_OFF_all_active_recovery','survivor_count','wall_s','cpu_s','peak_rss_bytes','failure')}),flush=True)
                if ledger()['cpu_available_for_new_partition']<0:
                    failure='Aggregate charged/live/controller CPU allocation exceeded; no more admissions'
            worker.durable_json(OUTPUT/'outcomes.json',[outcomes[i] for i in sorted(outcomes)])
            time.sleep(.1)
    except BaseException as error:
        failure=f'{type(error).__name__}: {error}'
        for pid in running:
            if pid>0:
                try: os.killpg(pid,signal.SIGKILL)
                except ProcessLookupError: pass
        # No refund for unknown/unclosed meters. Retain all live partitions as
        # consumed on controller failure; this panel can never be restarted.
        charged+=PARTITION*len(running)
        for pid,item in list(running.items()):
            if pid>0:
                try:
                    _,status,usage=os.wait4(pid,0)
                    item['process'].returncode=os.waitstatus_to_exitcode(status);item['log'].close()
                except ChildProcessError: pass
        running.clear()
    ordered=[outcomes[i] for i in sorted(outcomes)]
    worker.durable_json(OUTPUT/'outcomes.json',ordered)
    summary=summarizer.summarize(cases,ordered,'VAL_B')
    if failure is not None:
        summary['scientific_gate']='FAIL_CLOSED';summary['controller_failure']=failure
    own=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
    resource_receipt={'controller_wall_s':time.monotonic()-STARTED,'controller_cpu_s':own.ru_utime+own.ru_stime,
        'controller_peak_rss_bytes':own.ru_maxrss*1024,'children_cpu_s_reaped':children.ru_utime+children.ru_stime,
        'conservative_children_cpu_s_charged':charged,'aggregate_cpu_allocation_seconds':budget,
        'global_cpu_ceiling_seconds':43200,'all_children_reaped':not running,
        'max_concurrent_children':8,'closures':reaps,'controller_failure':failure,
        'cpu_budget_passed':charged+own.ru_utime+own.ru_stime<=budget}
    if not resource_receipt['cpu_budget_passed']:
        summary['scientific_gate']='FAIL_CLOSED'
        summary['controller_failure']='Aggregate whole-child and controller CPU budget exceeded'
    worker.durable_json(OUTPUT/'summary.json',summary)
    worker.durable_json(OUTPUT/'resource_receipt.json',resource_receipt)
    final=ledger();final['status']='CLOSED_NO_RETRY';final['controller_failure']=failure
    worker.durable_json(OUTPUT/'rolling_cpu_ledger.json',final)
    # A PASS is usable only with this final durable panel commit and exit zero.
    # Any failed final write/hash leaves the panel uncommitted, never qualified.
    final_cpu=controller_cpu()
    if charged+final_cpu>budget:
        summary['scientific_gate']='FAIL_CLOSED'
        summary['controller_failure']='Aggregate CPU exceeded during final durable flush'
        resource_receipt.update(controller_cpu_s=final_cpu,cpu_budget_passed=False)
        worker.durable_json(OUTPUT/'summary.json',summary)
        worker.durable_json(OUTPUT/'resource_receipt.json',resource_receipt)
    success=summary['scientific_gate']=='PASS_EXPLORATORY_SCOPE_ONLY' and resource_receipt['cpu_budget_passed']
    worker.durable_json(OUTPUT/'COMMITTED_PANEL.json',{'status':'COMPLETE_PASS_EXPLORATORY_SCOPE_ONLY' if success else 'CLOSED_FAIL',
        'panel':'VAL_B','case_count_expected':142,'case_count_observed':len(ordered),
        'outcomes_SHA256':worker.digest(OUTPUT/'outcomes.json'),'summary_SHA256':worker.digest(OUTPUT/'summary.json'),
        'resource_receipt_SHA256':worker.digest(OUTPUT/'resource_receipt.json'),
        'no_retry_or_redraw':True,'all_children_reaped':not running,'cpu_budget_passed':resource_receipt['cpu_budget_passed']},exclusive=True)
    print(json.dumps({'status':'CLOSED_NO_RETRY','observed_case_count':len(ordered),
        'scientific_gate':summary['scientific_gate'],'charged_children_cpu_s':charged,
        'controller_cpu_s':resource_receipt['controller_cpu_s']}),flush=True)
    return 0 if success else 1

if __name__=='__main__': raise SystemExit(main())
