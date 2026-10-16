#!/usr/bin/env python3
"""Frozen once-only parallel continuation of eight exposed historical bands."""
from __future__ import annotations
import argparse, concurrent.futures, copy, hashlib, importlib.util, json, math, os
from pathlib import Path
import shutil, sys, threading, time
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]
WORKSPACE=SOURCE.parent
IDENTITY='SETI_REAL_FULLSCAN_COHORT_DESCRIPTIVE_20261016_V1'
MODE='DESCRIPTIVE_POSTSELECTED_2017'
SCHEMA='SETI_FIXED_RETAINED_BAND_COMPLETE_DESCRIPTIVE_SCOPE_V1'
MIB=1024**2
PRIMARY_CAP=800*MIB; QA_CAP=64*MIB; LOG_CAP=MIB; METADATA_CAP=MIB
PAYLOAD_CAP=768*MIB; OUTPUT_CAP=2*1024**3
COHORT_CAP=8*1024**3
CASE_RESERVE=PRIMARY_CAP+QA_CAP+2*LOG_CAP+METADATA_CAP
COHORT_META_RESERVE=4*MIB
TOTAL_CPU=10500  # 8*(600 primary+600 QA+100 metadata)+100 shared coordination
GUARD_SHA='d02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492'
ARCHIVE_SHA='52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'
GROUPS=[[170,131],[170,252],[171,55],[171,231],[172,12],[172,48],[172,81],[172,94],[172,168]]
PIN_PATHS=tuple('analysis/real_fullscan_cohort_20261016/'+p for p in
 ('run.py','reader.py','producer.py','verifier.py','build_metadata.py','SOURCE_SELECTION.json','PLAN.md'))+(
 'tools/science_payload_20261016/payload.py','tools/bounded_payload_20261015/payload_store.py',
 'tools/fullcase_payload_20261015/array_adapter.py','tools/whole_child_guard_20261015/guard.py',
 'analysis/sixscan_burst_20261015/worker.py','analysis/sixscan_burst_20261015/detector.py',
 'analysis/sixscan_burst_20261015/qa.py','analysis/sixscan_burst_20261015/contract.json')
LOCK=threading.Lock()

def require(ok,message):
 if not ok: raise ValueError(message)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(MIB),b''):h.update(block)
 return h.hexdigest()

def sync(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def save(path,value):
 path=Path(path);raw=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
 require(len(raw)<=METADATA_CAP//2,'Bounded parent metadata required')
 with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 sync(path.parent)

def size(path):
 path=Path(path)
 if not path.exists():return 0
 require(not path.is_symlink(),'Output symlink rejected')
 if path.is_file():return path.stat().st_size
 total=0
 for p in path.rglob('*'):
  require(not p.is_symlink(),'Output symlink rejected')
  try:
   if p.is_file():total+=p.stat().st_size
  except FileNotFoundError:
   # Another child atomically renamed its temporary receipt; the reserved
   # running-phase slot already covers its bytes. Other errors still fail.
   continue
 return total

def pins():
 return [dict(path=p,bytes=(SOURCE/p).stat().st_size,sha256=sha(SOURCE/p)) for p in PIN_PATHS]

def check_pin(pin):
 p=Path(pin['path']);require(p.is_file() and not p.is_symlink() and p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],'Pinned prerequisite differs')

def claims():return WORKSPACE/'work'/'REAL_DESCRIPTIVE_CLAIMS_20261016'

def freeze(scope_path,output_root,archive,engineering):
 scope_path=Path(scope_path).resolve();root=Path(output_root).resolve();archive=Path(archive).resolve()
 engineering=Path(engineering).resolve()
 require(not root.exists() and root.parent.is_dir(),'Fresh cohort root required')
 require(archive.stat().st_size==48468705 and sha(archive)==ARCHIVE_SHA,'Original archive differs')
 require(sha(SOURCE/'tools/whole_child_guard_20261015/guard.py')==GUARD_SHA,'Guard differs')
 previous=SOURCE/'analysis/real_fullscan_20261016/SCOPE.json'
 template=json.loads(previous.read_text());require(template['identity'].endswith('_B00'),'Original B00 scope required')
 prior=WORKSPACE/'work/SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00/RESULT.json'
 require(json.loads(prior.read_text())['status']=='COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED','B00 closure required')
 epin=dict(path=str(engineering),bytes=engineering.stat().st_size,sha256=sha(engineering))
 require(json.loads(engineering.read_text())['status']=='PASS_COMPLETE_SEARCH_ENGINEERING_ONLY','Engineering prerequisite required')
 selection=json.loads((HERE/'SOURCE_SELECTION.json').read_text())
 require([[c['native_chunk_index'],c['core_q']] for c in selection['canonical_nine_band_order']]==GROUPS and
  [c['canonical_index'] for c in selection['canonical_nine_band_order']]==list(range(9)) and
  [c['canonical_index'] for c in selection['cases']]==list(range(1,9)),'Exact original remaining order required')
 frozen_pins=pins();cases=[]
 for selected in selection['cases']:
  i=selected['canonical_index'];ident=f'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B{i:02}'
  require(selected['identity']==ident and not (claims()/(ident+'.json')).exists(),'Fresh band identity required')
  scope=copy.deepcopy(template)
  scope.update(identity=ident,canonical_index=i,output_root=str(root/f'B{i:02}'),source_pins=frozen_pins,
   band=selected['band'],source_archive=dict(path=str(archive),bytes=48468705,sha256=ARCHIVE_SHA),integration_acceptance=epin,
   selection='All remaining canonical indices1..8 in original metadata order, fixed together before new numerical execution; no outcomes select or replace a band.',
   cohort_identity=IDENTITY,cohort_reserved_total_CPU_s=TOTAL_CPU,
   cohort_failure_policy='Independent reserved bands continue after a band-local failure; failed identities are retained without retry or replacement. Shared aggregate/output/source-integrity failure prevents further phase admission.',
   reservations_refunded=False)
  target=HERE/'scopes'/f'B{i:02}.json';save(target,scope)
  cases.append(dict(canonical_index=i,identity=ident,scope_path=str(target),scope_sha256=sha(target),output_root=scope['output_root']))
 require(8*CASE_RESERVE+COHORT_META_RESERVE<=COHORT_CAP,'All future output reservations fit aggregate cap')
 cohort=dict(schema='SETI_EIGHT_REMAINING_BANDS_PARALLEL_DESCRIPTIVE_SCOPE_V1',identity=IDENTITY,mode=MODE,
  output_root=str(root),cases=cases,source_pins=frozen_pins,
  source_archive=dict(path=str(archive),bytes=48468705,sha256=ARCHIVE_SHA),integration_acceptance=epin,
  B00_complete_prerequisite=dict(path=str(prior),bytes=prior.stat().st_size,sha256=sha(prior)),
  excluded_canonical_index=0,canonical_group_order=GROUPS,maximum_parallel_children=8,
  resources=dict(primary_phases=8,qa_phases=8,each_whole_child_CPU_s=600,per_case_metadata_CPU_s=100,
   shared_metadata_CPU_s=100,reserved_total_CPU_s=TOTAL_CPU,per_case_reserved_output_bytes=CASE_RESERVE,
   shared_metadata_bytes=COHORT_META_RESERVE,reserved_output_bytes=8*CASE_RESERVE+COHORT_META_RESERVE,
   aggregate_output_cap_bytes=COHORT_CAP,per_case_output_cap_bytes=OUTPUT_CAP,
   metadata_CPU_reserves_are_prospective_not_claimed_measured=True),
  failure_policy=scope['cohort_failure_policy'],reservations_refunded=False,no_retries=True,
  scientific_bank_admission=False,qualified_SETI_detection=False,rank_status='NOT_APPLIED_NO_CALIBRATION',
  original_A_B='FAIL_CLOSED',new_observation=False,new_telescope_requests=0,new_telescope_bytes=0,cost_DKK=0,
  checkpoint='2026-10-20')
 save(scope_path,cohort)
 return dict(status='FROZEN_EIGHT_BANDS_DESCRIPTIVE_ONLY',scope_sha256=sha(scope_path),cases=8)

def case_run(entry,guard,cohort,shared):
 scope_path=Path(entry['scope_path']);scope=json.loads(scope_path.read_text());root=Path(entry['output_root'])
 folder=root/'observation';qa_report=root/'QA_REPORT.json'
 state=dict(identity=entry['identity'],canonical_index=entry['canonical_index'],status='RUNNING_DESCRIPTIVE_ONLY',scope_sha256=entry['scope_sha256'],phases=[],
  resource_reservation=dict(CPU_s=1300,output_bytes=CASE_RESERVE),reservations_refunded=False,
  rank_status='NOT_APPLIED_NO_CALIBRATION',scientific_bank_admission=False,qualified_SETI_detection=False,original_A_B='FAIL_CLOSED',new_observation=False)
 phases=(('primary',[sys.executable,str(HERE/'producer.py'),'--folder',str(folder),'--scope',str(scope_path),'--scope-sha256',entry['scope_sha256'],'--payload-cap',str(PAYLOAD_CAP)],folder,PRIMARY_CAP,folder/'PRODUCER.json','PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY'),
 ('qa',[sys.executable,str(HERE/'verifier.py'),'--folder',str(folder),'--report',str(qa_report)],qa_report,QA_CAP,qa_report,'PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY'))
 for phase,command,output,bound,report,expected in phases:
  attempt=root/('process_'+phase);receipt=None
  try:
   with LOCK:
    try:
     require(not shared['stop'],'Shared cohort stop prevents further phase admission')
     require(sha(scope_path)==entry['scope_sha256'] and scope['source_pins']==pins(),'Frozen sources/scope changed')
     require(size(root)+bound+LOG_CAP+METADATA_CAP<=OUTPUT_CAP,'Per-case output headroom unavailable')
     # Keep enough actual free bytes for every phase's remaining prospective reservation.
     outstanding=sum(shared['remaining'].values())+COHORT_META_RESERVE
     require(shutil.disk_usage(root).free>=outstanding,'All outstanding aggregate output reservations require live free space')
     require(size(Path(cohort['output_root']))+outstanding<=COHORT_CAP,'Aggregate reserved output ceiling exceeded')
     check_pin(scope['source_archive'])
    except BaseException:
     shared['stop']=True
     raise
    save(root/('CLAIM_'+phase+'.json'),dict(phase=phase,identity=entry['identity'],scope_sha256=entry['scope_sha256'],CPU_reserved_s=600,output_reserved_bytes=bound+LOG_CAP,no_retry=True))
   receipt=guard.run_once(command,attempt,guard.policy(600,1800,1024**3))
   require(receipt.get('resource_acceptance') is True,'Whole-child resource/process closure failed')
   report_data=json.loads(report.read_text())
   require(report_data['status']==expected and report_data.get('scientific_bank_admission') is False,'Complete descriptive phase report required')
   output_bytes,log_bytes=size(output),size(attempt)
   require(output_bytes<=bound and log_bytes<=LOG_CAP,'Phase output/log cap exceeded')
   event=dict(phase=phase,status='ACCEPTED_DESCRIPTIVE_PHASE_ONLY',receipt=receipt,output_bytes=output_bytes,log_receipt_bytes=log_bytes,report_sha256=sha(report),reservations_refunded=False)
   save(root/('PHASE_'+phase+'.json'),event);state['phases'].append(event)
   with LOCK:
    # Occupied bytes remain counted by size(root); this only releases future physical headroom, not the immutable reservation or CPU charge.
    shared['remaining'][(entry['canonical_index'],phase)]=0
    print(json.dumps(dict(band=entry['canonical_index'],phase=phase,status='ACCEPTED',CPU_s=receipt['whole_child_CPU_s'])),flush=True)
  except BaseException as error:
   event=dict(phase=phase,status='FAILED_RETAINED_NO_RETRY',receipt=receipt,output_bytes=size(output),log_receipt_bytes=size(attempt),error=dict(type=type(error).__name__,message=str(error)[:1024]),reservations_refunded=False)
   save(root/('FAILURE_'+phase+'.json'),event);state['phases'].append(event);state['status']='STOPPED_RETAINED_NO_RETRY'
   with LOCK:print(json.dumps(dict(band=entry['canonical_index'],phase=phase,status='FAILED_RETAINED',error=event['error'])),flush=True)
   break
 if state['status']=='RUNNING_DESCRIPTIVE_ONLY':
  if scope['source_pins']==pins() and len(state['phases'])==2:state['status']='COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED'
  else:state['status']='STOPPED_RETAINED_NO_RETRY'
 values=[p['receipt'].get('whole_child_CPU_s') if p['receipt'] else None for p in state['phases']]
 known=[v for v in values if type(v) in (int,float) and math.isfinite(v) and v>=0]
 state['known_whole_children_CPU_s']=math.fsum(known);state['unknown_CPU_measurement_count']=len(values)-len(known)
 state['whole_children_CPU_s']=math.fsum(known) if len(known)==len(values) else None
 state['actual_output_bytes_before_final_receipt']=size(root)
 save(root/'RESULT.json',state)
 return state

def run(scope_path):
 scope_path=Path(scope_path).resolve();cohort=json.loads(scope_path.read_text());root=Path(cohort['output_root'])
 require(cohort['identity']==IDENTITY and cohort['source_pins']==pins(),'Exact frozen cohort sources required')
 require(not root.exists() and root.parent.is_dir(),'Fresh cohort output root required')
 require(sha(cohort['source_archive']['path'])==ARCHIVE_SHA,'Original archive changed')
 check_pin(cohort['integration_acceptance']);check_pin(cohort['B00_complete_prerequisite'])
 require(cohort['resources']['reserved_total_CPU_s']==TOTAL_CPU and cohort['resources']['reserved_output_bytes']==8*CASE_RESERVE+COHORT_META_RESERVE,'Complete prospective resource reservation required')
 require(shutil.disk_usage(root.parent).free>=8*CASE_RESERVE+COHORT_META_RESERVE,'Aggregate reservation unavailable')
 require([e['canonical_index'] for e in cohort['cases']]==list(range(1,9)),'Exactly eight fixed cases required')
 for entry in cohort['cases']:
  require(sha(entry['scope_path'])==entry['scope_sha256'],'Case scope pin differs')
  require(not (claims()/(entry['identity']+'.json')).exists(),'Case already claimed; no retry')
 claims().mkdir(parents=True,exist_ok=True);sync(claims().parent)
 save(claims()/(IDENTITY+'.json'),dict(identity=IDENTITY,scope_sha256=sha(scope_path),status='ALL_EIGHT_BANDS_RESERVED_BEFORE_ANY_CHILD_IMPORT_OR_RAW_DECODE',cases=cohort['cases'],CPU_reserved_s=TOTAL_CPU,output_reserved_bytes=8*CASE_RESERVE+COHORT_META_RESERVE,reservations_refunded=False,no_retry=True))
 root.mkdir();sync(root.parent);save(root/'FROZEN_COHORT_SCOPE.json',cohort)
 for entry in cohort['cases']:
  save(claims()/(entry['identity']+'.json'),dict(identity=entry['identity'],scope_sha256=entry['scope_sha256'],cohort_identity=IDENTITY,no_retry=True,reserved_CPU_s=1300,reserved_output_bytes=CASE_RESERVE,reservations_refunded=False))
  case_root=Path(entry['output_root']);case_root.mkdir();sync(root);save(case_root/'FROZEN_SCOPE.json',json.loads(Path(entry['scope_path']).read_text()))
 gp=SOURCE/'tools/whole_child_guard_20261015/guard.py';require(sha(gp)==GUARD_SHA,'Guard changed')
 spec=importlib.util.spec_from_file_location('cohort_guard',gp);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 shared=dict(stop=False,remaining={(e['canonical_index'],phase):bound+LOG_CAP+METADATA_CAP//2 for e in cohort['cases'] for phase,bound in [('primary',PRIMARY_CAP),('qa',QA_CAP)]})
 states=[];parent_start=time.process_time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
  futures={pool.submit(case_run,e,guard,cohort,shared):e for e in cohort['cases']}
  for future in concurrent.futures.as_completed(futures):
   try:states.append(future.result())
   except BaseException as error:
    with LOCK:shared['stop']=True
    states.append(dict(identity=futures[future]['identity'],status='PARENT_EXCEPTION_RETAINED_NO_RETRY',error=str(error)[:1024],whole_children_CPU_s=None))
 finalization_errors=[]
 try:
  require(cohort['source_pins']==pins(),'Sources changed at final closure')
 except BaseException as error:
  finalization_errors.append(str(error)[:1024])
 passed=sum(s['status']=='COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED' for s in states)
 values=[s.get('whole_children_CPU_s') for s in states];known=[x for x in values if type(x) in (int,float) and math.isfinite(x) and x>=0]
 result=dict(identity=IDENTITY,status='COMPLETE_EIGHT_BAND_DESCRIPTIVE_COHORT_QA_VERIFIED' if passed==8 else 'INCOMPLETE_COHORT_RETAINED_NO_RETRY',
  completed_verified_bands=passed,planned_bands=8,scope_sha256=sha(scope_path),cases=sorted(states,key=lambda s:s['identity']),
  whole_children_CPU_s=math.fsum(known) if len(known)==8 else None,known_children_CPU_s=math.fsum(known),unknown_case_CPU_measurement_count=8-len(known),
  coordinator_CPU_s_since_claims=time.process_time()-parent_start,resource_reservation=cohort['resources'],reservations_refunded=False,
  actual_output_bytes_before_final_receipt=size(root),scientific_bank_admission=False,qualified_SETI_detection=False,rank_status='NOT_APPLIED_NO_CALIBRATION',original_A_B='FAIL_CLOSED')
 if size(root)+COHORT_META_RESERVE>COHORT_CAP:finalization_errors.append('Final aggregate output cap exceeded')
 if finalization_errors:
  result['status']='INCOMPLETE_COHORT_RETAINED_NO_RETRY';result['finalization_errors']=finalization_errors
 save(root/'RESULT.json',result)
 return dict(status=result['status'],completed_verified_bands=passed,whole_children_CPU_s=result['whole_children_CPU_s'])

def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
 p=sub.add_parser('freeze');p.add_argument('--scope',required=True);p.add_argument('--output-root',required=True);p.add_argument('--source-archive',required=True);p.add_argument('--engineering-result',required=True)
 p=sub.add_parser('run');p.add_argument('--scope',required=True)
 a=ap.parse_args();r=freeze(a.scope,a.output_root,a.source_archive,a.engineering_result) if a.command=='freeze' else run(a.scope)
 print(json.dumps(r,sort_keys=True),flush=True)
 return 0 if r['status'] in ('FROZEN_EIGHT_BANDS_DESCRIPTIVE_ONLY','COMPLETE_EIGHT_BAND_DESCRIPTIVE_COHORT_QA_VERIFIED') else 1
if __name__=='__main__':raise SystemExit(main())
