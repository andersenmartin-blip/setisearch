#!/usr/bin/env python3
"""Fresh engineering restoration and saved-result QA; original cohort stays closed."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,os,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parents[1];WORKSPACE=SOURCE.parent
IDENTITY='SETI_B06_SAVED_PAYLOAD_RESTORATION_QA_20261016_V1'
MIB=1024**2;TOTAL_CPU=760;PHASE_CAP=64*MIB;LOG_CAP=MIB;META_CAP=MIB;OUTPUT_CAP=512*MIB
RESERVED=2*PHASE_CAP+2*LOG_CAP+META_CAP
GUARD_SHA='d02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492'
EXPECTED_SHA='b96e21059e3d5480c55aad7788488ba5a49f1f4c05bb59ac14224b5cd09a143a'
CORRUPT_SHA='f5332374aff54027ea8e1cfa25738deee7631a61d5a83f88e556b68f4e3f3bed'

def require(ok,message):
 if not ok:raise ValueError(message)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(MIB),b''):h.update(b)
 return h.hexdigest()

def pin(path):
 p=Path(path).resolve();return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))

def check(p):
 path=Path(p['path']);require(path.is_file() and not path.is_symlink() and path.stat().st_size==p['bytes'] and sha(path)==p['sha256'],'Pinned prerequisite changed: '+p['path'])

def sync(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def save(path,data):
 path=Path(path);raw=(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n').encode();require(len(raw)<=META_CAP//2,'Bounded receipt required')
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 sync(path.parent)

def size(path):
 p=Path(path)
 if not p.exists():return 0
 require(not p.is_symlink(),'Symlink rejected')
 if p.is_file():return p.stat().st_size
 return sum(q.stat().st_size for q in p.rglob('*') if q.is_file())

def sources():
 old=json.loads((SOURCE/'analysis/real_fullscan_cohort_20261016/scopes/B06.json').read_text())
 paths={p['path'] for p in old['source_pins']}
 paths.update('tools/saved_payload_restore_20261016/'+x for x in ('run.py','restore.py','verify.py','PLAN.md'))
 return [dict(path=p,bytes=(SOURCE/p).stat().st_size,sha256=sha(SOURCE/p)) for p in sorted(paths)]

def claimpath():return WORKSPACE/'work/SAVED_PAYLOAD_CLAIMS_20261016'/(IDENTITY+'.json')

def freeze(scope_path,output_root):
 root=Path(output_root).resolve();scope_path=Path(scope_path).resolve()
 require(not root.exists() and not claimpath().exists(),'Fresh restoration/verification identity required')
 origin=WORKSPACE/'work/SETI_REAL_FULLSCAN_COHORT_DESCRIPTIVE_20261016_V1/B06'
 producer=json.loads((origin/'observation/PRODUCER.json').read_text());manifest=json.loads((origin/'observation/payload/MANIFEST.json').read_text())
 target=manifest['members']['science_arrays.npz'];require(target==dict(bytes=8723230,sha256=EXPECTED_SHA),'Original before-failure target pin required')
 corrupt=pin(origin/'observation/payload/science_arrays.npz');require(corrupt['bytes']==7378998 and corrupt['sha256']==CORRUPT_SHA,'Exact retained failed bytes required')
 oldscope=SOURCE/'analysis/real_fullscan_cohort_20261016/scopes/B06.json';old=json.loads(oldscope.read_text())
 require(json.loads((origin/'RESULT.json').read_text())['status']=='STOPPED_RETAINED_NO_RETRY','Original case must remain failed and closed')
 require(json.loads((origin.parent/'RESULT.json').read_text())['status']=='INCOMPLETE_COHORT_RETAINED_NO_RETRY','Original cohort must remain incomplete')
 receipts=[origin/'RESULT.json',origin.parent/'RESULT.json',oldscope,origin/'FROZEN_SCOPE.json',origin/'QA_REPORT.json',origin/'PHASE_primary.json',origin/'FAILURE_qa.json',origin/'process_primary/WAIT4_RECEIPT.json',origin/'process_qa/WAIT4_RECEIPT.json',origin/'observation/PRODUCER.json',origin/'observation/DESCRIPTIVE_CLAIM.json']+[origin/'observation/payload'/n for n in manifest['members'] if n!='science_arrays.npz']+[origin/'observation/payload/MANIFEST.json']
 receipts=sorted(set(receipts+[p for phase in ('primary','qa') for p in (origin/('process_'+phase)).iterdir() if p.is_file()]+[origin/'CLAIM_primary.json',origin/'CLAIM_qa.json']))
 scope=dict(schema='SETI_EXACT_SAVED_PAYLOAD_RESTORATION_AND_SEPARATE_QA_SCOPE_V1',identity=IDENTITY,
  mode='SAVED_RESULT_VERIFICATION_ONLY',
  output_root=str(root),origin_folder=str(origin/'observation'),restored_folder=str(root/'observation'),
  original_scope_sha256=sha(oldscope),target_npz_bytes=8723230,target_npz_sha256=EXPECTED_SHA,
  restore_receipt_path=str(root/'RESTORATION_REPORT.json'),
  original_scope=pin(oldscope),original_case_result=pin(origin/'RESULT.json'),original_cohort_result=pin(origin.parent/'RESULT.json'),
  origin_evidence_pins=[pin(p) for p in receipts],truncated_array_archive=corrupt,
  expected_restored_array_archive=dict(bytes=8723230,sha256=EXPECTED_SHA),
  source_archive=old['source_archive'],source_metadata=old['source_metadata'],source_pins=sources(),
  source_band=old['band'],canonical_index=6,original_case_id=old['identity'],
  restoration_rule='Preserve all454 complete derived compressed entries verbatim. Recreate only six original raw input ZIP members and ZIP directory from independently authenticated source bytes. Accept exclusively exact pre-failure full archive size/SHA; no search, fit, threshold, selection or result changes.',
  original_failure_retained=True,original_cohort_status='INCOMPLETE_COHORT_RETAINED_NO_RETRY',
  separate_saved_result_QA_does_not_reopen_original_scope=True,no_primary_detector_invocation=True,
  no_retry=True,reservations_refunded=False,
  resources=dict(restoration_CPU_s=60,qa_CPU_s=600,metadata_CPU_s=100,total_reserved_CPU_s=TOTAL_CPU,
   phase_output_cap_bytes=PHASE_CAP,phase_log_receipt_cap_bytes=LOG_CAP,metadata_cap_bytes=META_CAP,
   reserved_output_bytes=RESERVED,total_output_cap_bytes=OUTPUT_CAP,child_wall_s=1800,child_address_space_bytes=1024**3),
  scientific_bank_admission=False,qualified_SETI_detection=False,rank_status='NOT_APPLIED_NO_CALIBRATION',
  calibrated_SNR_or_FAP=False,new_observation=False,new_telescope_requests=0,new_telescope_bytes=0,cost_DKK=0,
  original_A_B='FAIL_CLOSED',protected_2016_closed=True,unavailable_2019_closed=True,checkpoint='2026-10-20')
 save(scope_path,scope);return dict(status='FROZEN_SAVED_PAYLOAD_RESTORATION_ONLY',scope_sha256=sha(scope_path))

def run(scope_path):
 scope_path=Path(scope_path).resolve();scope=json.loads(scope_path.read_text());root=Path(scope['output_root'])
 require(scope['identity']==IDENTITY and scope['source_pins']==sources(),'Exact frozen sources required')
 for p in scope['origin_evidence_pins']+[scope['truncated_array_archive'],scope['source_archive']]:check(p)
 require(not root.exists() and root.parent.is_dir() and shutil.disk_usage(root.parent).free>=RESERVED,'Fresh root and all future output headroom required')
 c=claimpath();c.parent.mkdir(exist_ok=True);sync(c.parent.parent)
 save(c,dict(identity=IDENTITY,scope_sha256=sha(scope_path),status='CLAIMED_BEFORE_ANY_SOURCE_ARRAY_DECODE',reserved_CPU_s=TOTAL_CPU,reserved_output_bytes=RESERVED,no_retry=True,reservations_refunded=False))
 root.mkdir();sync(root.parent);save(root/'FROZEN_SCOPE.json',scope)
 gp=SOURCE/'tools/whole_child_guard_20261015/guard.py';require(sha(gp)==GUARD_SHA,'Guard differs')
 spec=importlib.util.spec_from_file_location('saved_payload_guard',gp);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 events=[];status='RUNNING_SAVED_PAYLOAD_RESTORATION_ONLY'
 for phase,cpu,report,expected in [('restore',60,root/'RESTORATION_REPORT.json','RESTORED_EXACT_ORIGINAL_PAYLOAD_BYTES_ONLY'),('qa',600,root/'SAVED_QA_REPORT.json','PASS_RESTORED_SAVED_DESCRIPTIVE_SEARCH_QA_ONLY')]:
  receipt=None;attempt=root/('process_'+phase)
  try:
   require(scope['source_pins']==sources() and sha(scope_path)==sha(root/'FROZEN_SCOPE.json'),'Frozen source/scope changed')
   for p in scope['origin_evidence_pins']+[scope['truncated_array_archive']]:check(p)
   require(size(root)+PHASE_CAP+LOG_CAP+META_CAP<=OUTPUT_CAP and shutil.disk_usage(root).free>=PHASE_CAP+LOG_CAP+META_CAP,'Next reserved output headroom required')
   save(root/('CLAIM_'+phase+'.json'),dict(identity=IDENTITY,phase=phase,CPU_reserved_s=cpu,output_reserved_bytes=PHASE_CAP+LOG_CAP,no_retry=True))
   cmd=[sys.executable,str(HERE/('restore.py' if phase=='restore' else 'verify.py')),'--scope',str(scope_path),'--output-root',str(root)]
   before=size(root);receipt=guard.run_once(cmd,attempt,guard.policy(cpu,1800,1024**3))
   require(receipt['resource_acceptance'] is True,'Whole-child resource/process closure failed')
   data=json.loads(report.read_text());require(data['status']==expected and data['scientific_bank_admission'] is False,'Exact complete engineering/savedQA report required')
   added=size(root)-before;logs=size(attempt);data_bytes=added-logs
   require(0<=data_bytes<=PHASE_CAP and logs<=LOG_CAP,'Phase physical output/log cap exceeded')
   event=dict(phase=phase,status='ACCEPTED_SEPARATE_RESTORATION_STUDY_PHASE',receipt=receipt,report_sha256=sha(report),added_output_bytes=added,data_output_bytes=data_bytes,log_receipt_bytes=logs,reservations_refunded=False)
   save(root/('PHASE_'+phase+'.json'),event);events.append(event)
   print(json.dumps(dict(phase=phase,status='ACCEPTED',CPU_s=receipt['whole_child_CPU_s'])),flush=True)
  except BaseException as e:
   event=dict(phase=phase,status='FAILED_RETAINED_NO_RETRY',receipt=receipt,error=dict(type=type(e).__name__,message=str(e)[:1024]),reservations_refunded=False)
   save(root/('FAILURE_'+phase+'.json'),event);events.append(event);status='STOPPED_RETAINED_NO_RETRY';break
 if len(events)==2 and all(e['status']=='ACCEPTED_SEPARATE_RESTORATION_STUDY_PHASE' for e in events):status='COMPLETE_EXACT_RESTORATION_AND_SEPARATE_SAVED_QA'
 final_errors=[]
 try:
  require(scope['source_pins']==sources(),'Source pins changed at closure')
  for p in scope['origin_evidence_pins']+[scope['truncated_array_archive']]:check(p)
 except BaseException as e:final_errors.append(str(e)[:1024]);status='STOPPED_RETAINED_NO_RETRY'
 values=[e['receipt'].get('whole_child_CPU_s') if e['receipt'] else None for e in events];known=[x for x in values if type(x) in (int,float) and math.isfinite(x)]
 result=dict(identity=IDENTITY,status=status,phases=events,scope_sha256=sha(scope_path),whole_children_CPU_s=math.fsum(known) if len(known)==len(values) else None,known_whole_children_CPU_s=math.fsum(known),unknown_measurements=len(values)-len(known),
  reserved_CPU_s=TOTAL_CPU,reserved_output_bytes=RESERVED,reservations_refunded=False,original_cohort_status='INCOMPLETE_COHORT_RETAINED_NO_RETRY',original_failure_retained=True,no_primary_detector_invocation=True,
  scientific_bank_admission=False,qualified_SETI_detection=False,rank_status='NOT_APPLIED_NO_CALIBRATION',original_A_B='FAIL_CLOSED',finalization_errors=final_errors)
 result['actual_output_bytes_before_final_receipt']=size(root)
 if size(root)+META_CAP>OUTPUT_CAP:
  result['status']='STOPPED_RETAINED_NO_RETRY';result['finalization_errors'].append('Final output ceiling exceeded')
 save(root/'RESULT.json',result);return dict(status=result['status'],whole_children_CPU_s=result['whole_children_CPU_s'])

def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
 p=sub.add_parser('freeze');p.add_argument('--scope',required=True);p.add_argument('--output-root',required=True)
 p=sub.add_parser('run');p.add_argument('--scope',required=True)
 a=ap.parse_args();r=freeze(a.scope,a.output_root) if a.command=='freeze' else run(a.scope);print(json.dumps(r),flush=True)
 return 0 if r['status'] in ('FROZEN_SAVED_PAYLOAD_RESTORATION_ONLY','COMPLETE_EXACT_RESTORATION_AND_SEPARATE_SAVED_QA') else 1
if __name__=='__main__':raise SystemExit(main())
