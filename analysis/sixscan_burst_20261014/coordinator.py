"""Bounded once-only case execution; complete wait4 resource accounting."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

def dump(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    tmp.replace(path)

def regular_bytes(directory):
    total=0
    for p in directory.rglob('*'):
        try:
            if p.is_file() and not p.is_symlink():total+=p.stat().st_size
        except FileNotFoundError:
            # A worker can atomically rename its temporary file during census.
            continue
    return total

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase',choices=['primary_calibration','primary_validation','qa','exposed','qa_exposed'],required=True)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--workers',type=int,default=4)
    args=ap.parse_args()
    root=args.root.resolve()
    scope=json.loads((root/'SCOPE.json').read_text())
    go=json.loads((root/'GO.json').read_text())
    assert go['status']=='ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK'
    assert go['scope_sha256']==hashlib.sha256((root/'SCOPE.json').read_bytes()).hexdigest()
    for pin in scope['code_pins']:
        data=(root/pin['path']).read_bytes()
        assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256'],pin['path']
    cap=scope['resources']['aggregate_new_CPU_s_cap']
    reservation=scope['resources']['per_case_CPU_s_cap']
    assert 1<=args.workers<=scope['resources']['max_concurrent_workers']
    cases=json.loads((root/'case_bank.json').read_text())
    if args.phase=='primary_validation':
        prior=json.loads((root/'PRIMARY_CALIBRATION_RUN_STATE.json').read_text())
        assert prior['status']=='COMPLETE' and not prior['running'] and not prior['unsubmitted']
        assert len(prior['jobs'])==63 and all(j['exit_code']==0 for j in prior['jobs'])
        assert (root/'results/CALIBRATION.json').is_file(),'Close the fixed calibration before validation generation'
    if args.phase=='qa':
        for phase in ('PRIMARY_CALIBRATION','PRIMARY_VALIDATION'):
            prior=json.loads((root/(phase+'_RUN_STATE.json')).read_text())
            assert prior['status']=='COMPLETE' and not prior['running'] and not prior['unsubmitted']
    if args.phase in ('exposed','qa_exposed'):
        real=json.loads((root/'real_baselines.json').read_text())
        cases=real if isinstance(real,list) else real['cases']
    if args.phase=='primary_calibration':indices=[i for i,c in enumerate(cases) if c['family']=='calibration']
    elif args.phase=='primary_validation':indices=[i for i,c in enumerate(cases) if c['family']!='calibration']
    elif args.phase=='qa':indices=list(range(len(cases)))
    else:indices=list(range(9))
    statefile=root/f'{args.phase.upper()}_RUN_STATE.json'
    if statefile.exists():raise RuntimeError('Once-only phase already has a durable state; no implicit rerun')
    previous=[]
    for p in root.glob('*_RUN_STATE.json'):
        s=json.loads(p.read_text());previous.append(s.get('charged_complete_child_CPU_s',0))
        if s.get('running'):raise RuntimeError('Previous phase still running; reconcile it first')
    initial=scope['resources']['metadata_and_delivery_reserved_CPU_s']+sum(previous)
    state={'schema':'SETI_SIXSCAN_ONCE_ONLY_COORDINATOR_V1','phase':args.phase,
      'started_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
      'initial_prior_charge_and_metadata_reservation_CPU_s':initial,
      'aggregate_new_CPU_s_cap':cap,'per_live_child_reservation_CPU_s':reservation,
      'jobs':[],'running':[],'charged_complete_child_CPU_s':0,'unsubmitted':indices.copy()}
    dump(statefile,state)
    running={}
    charge=0.0
    nextindex=0
    stop=False
    last_print=0
    while running or nextindex<len(indices):
        while not stop and nextindex<len(indices) and len(running)<args.workers:
            workspace_bytes=regular_bytes(root.parent)
            stage_bytes=regular_bytes(root/'results') if (root/'results').exists() else 0
            if workspace_bytes >= scope['resources']['workspace_cap_bytes']-536870912 or stage_bytes >= scope['resources']['new_output_payload_cap_bytes']-536870912:
                stop=True;state['stop_reason']='workspace_or_output_capacity_margin_exhausted';break
            if initial+charge+(len(running)+1)*reservation>cap:
                stop=True;state['stop_reason']='aggregate_CPU_reservation_capacity_exhausted';break
            idx=indices[nextindex]
            if args.phase=='qa_exposed':
                command=[sys.executable,str(root/'qa.py'),'--exposed-index',str(idx),'--output-root',str(root/'results')]
            elif args.phase=='qa':
                command=[sys.executable,str(root/'qa.py'),'--case-index',str(idx),'--output-root',str(root/'results')]
            elif args.phase=='exposed':
                command=[sys.executable,str(root/'worker.py'),'--exposed-index',str(idx),'--output-root',str(root/'results')]
            else:
                command=[sys.executable,str(root/'worker.py'),'--case-index',str(idx),'--output-root',str(root/'results')]
            logs=root/'logs';logs.mkdir(exist_ok=True)
            stem=f'{args.phase}_{idx:04d}'
            stdout=(logs/(stem+'.stdout.log')).open('wb')
            stderr=(logs/(stem+'.stderr.log')).open('wb')
            proc=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True,
                env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
            running[proc.pid]=(proc,idx,time.monotonic(),stdout,stderr,command)
            state['running'].append({'pid':proc.pid,'index':idx,'reserved_CPU_s':reservation})
            state['unsubmitted'].remove(idx)
            nextindex+=1
            dump(statefile,state)
        completed=[]
        for pid,(proc,idx,start,out,err,command) in list(running.items()):
            waited,status,usage=os.wait4(pid,os.WNOHANG)
            if not waited:continue
            code=os.waitstatus_to_exitcode(status)
            proc.returncode=code
            out.close();err.close()
            actual=usage.ru_utime+usage.ru_stime
            charge+=actual
            record={'index':idx,'case_id':cases[idx]['case_id'],
                'pid':pid,'command':command,'exit_code':code,'whole_child_CPU_s':actual,
                'wall_s':time.monotonic()-start,'peak_RSS_bytes':usage.ru_maxrss*1024,
                'exclusive_reservation_before_submit_CPU_s':reservation,'wait4_reaped':True}
            state['jobs'].append(record)
            state['running']=[r for r in state['running'] if r['pid']!=pid]
            state['charged_complete_child_CPU_s']=charge
            state['current_committed_or_live_reserved_CPU_s']=initial+charge+(len(running)-1)*reservation
            completed.append(pid)
            print(json.dumps({'phase':args.phase,'completed':len(state['jobs']),'planned':len(indices),
              'case_index':idx,'exit':code,'CPU_s':round(actual,3),'total_phase_CPU_s':round(charge,3)}),flush=True)
            if code!=0:
                # Keep the failed attempt; no retry or replacement identity.
                stop=True;state['stop_reason']='numerical_or_integrity_failure_no_further_submission'
            dump(statefile,state)
        for pid in completed:del running[pid]
        if stop and not running:break
        if time.monotonic()-last_print>=30:
            print(json.dumps({'phase':args.phase,'running':len(running),'completed':len(state['jobs']),
                'remaining_unsubmitted':len(state['unsubmitted'])}),flush=True)
            last_print=time.monotonic()
        if running:time.sleep(.2)
    state['completed_UTC']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    state['status']='COMPLETE' if not state['unsubmitted'] and all(j['exit_code']==0 for j in state['jobs']) else 'STOPPED_RETAINED_NO_RETRY'
    state['current_committed_or_live_reserved_CPU_s']=initial+charge
    dump(statefile,state)
    print(json.dumps({'phase':args.phase,'status':state['status'],'completed':len(state['jobs']),
        'planned':len(indices),'whole_child_CPU_s':charge}),flush=True)
    return 0 if state['status']=='COMPLETE' else 1

if __name__=='__main__':raise SystemExit(main())
