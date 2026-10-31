"""Read-only independent review of BR failed publication and retained prefixes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,time,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
RUN=ROOT/'execution/BR_A04_ASSOC_V1';BP=REPO/'work_bp/execution/BP_FIXED24_V1'
OUT=ROOT/'review/BR_FAILURE_REVIEW.json';START=time.monotonic()
hp=REPO/'work_bp/review/audit_results.py';spec=importlib.util.spec_from_file_location('br_failure_independent_formulas',hp)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def check(ok,msg):
 if not ok:raise ValueError(msg)
 if time.monotonic()-START>118:raise TimeoutError('Review118second cap')
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def pins(plan):
 for pin in plan['source_pins']+plan['input_pins']:
  p=REPO/pin['path'];check(not p.is_symlink() and p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],'Changed source/input '+pin['path'])
def main():
 check(not OUT.exists(),'No overwrite of failure review')
 plan=read(ROOT/'BR_POSTPROCESSING_PLAN.json');freeze=read(ROOT/'PUBLIC_FREEZE_RECEIPT_BR.json')
 check(freeze['exact_readback_verified'] and freeze['before_execution'] and freeze['plan_sha256']==sha(ROOT/'BR_POSTPROCESSING_PLAN.json'),'Public freeze binding')
 pins(plan)
 tp=RUN/'TERMINAL_BR.json';terminal=read(tp);th=sha(tp)
 check(terminal['status']=='FAIL' and terminal['capture_status']=='FAIL' and terminal['actual_exit_code']==2,'Failure status changed')
 check(terminal['BP_original_status']=='FAIL' and terminal['BQ_effective_status']=='EVIDENCE_FAIL','Prior failures changed')
 check(not terminal['final_inventory_matches_result_manifests'] and terminal['parent_stream_closure']==[],'False closure pass')
 expected={e['path']:e for e in terminal['files']};actual={str(p.relative_to(RUN)) for p in RUN.rglob('*') if p.is_file() and p!=tp}
 check(actual==set(expected) and len(expected)==len(terminal['files']),'Terminal inventory changed')
 byte_total=0
 for rel,e in expected.items():
  p=RUN/rel;check(not p.is_symlink() and p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],'Retained artifact differs')
  byte_total+=e['bytes']
 cp=RUN/'A04_POSTPROCESSING/ACTUAL_RECEIPT.json';capture=read(cp)
 check(sha(cp)==terminal['receipt_sha256'] and capture['actual_exit_code']==2 and capture['status']=='FAIL','Capture binding')
 for field in ['child_wait_completed','stdout_eof','natural_stdout_eof','stdout_fully_preserved','descendant_cleanup_completed','source_pins_verified_before','source_pins_verified_after']:
  check(capture[field],'Closed failure missing '+field)
 check(capture['remaining_live_descendants']==[] and not capture['killed'],'Unclean failure process')
 payload=RUN/'A04_POSTPROCESSING/payload';rp=payload/'RESULT.json';result=read(rp);rh=sha(rp)
 check(result['status']=='FAIL' and result['exception']=='ClosureError: Stream changed while its closed receipt was being verified','Unexpected failed guard')
 check('stream_closure.py' in result['traceback'] and '_verify_named_stream(self.directory_fd,{**receipt,\'path\':self.pending})' in result['traceback'],'Wrong failure stage')
 check(rh==terminal['result_sha256']==capture['result_sha256'],'Failure result binding')
 log=RUN/'A04_POSTPROCESSING/STDOUT.log';lb=log.read_bytes();lh=sha(log)
 check(lh==capture['log_sha256']==capture['observed_stdout_sha256'] and len(lb)==capture['log_bytes']==capture['observed_stdout_bytes'],'Failure log differs')
 footer=json.loads(lb.splitlines()[-1]);check(footer==dict(event='GATE_TERMINAL_EOF',status='FAIL',result_sha256=rh),'Failure EOF differs')
 check('ACTUAL_CHILD_EXIT_NOT_ZERO' in capture['reasons'],'Missing exit failure reason')
 results=[];scores=[]
 for scan in range(6):
  p=BP/'A04/payload'/f'scan{scan}';r=read(p/'RESULT.json');results.append(r)
  check(r['status']=='PASS' and r['scan_index']==scan and sha(p/'arrays.npz')==r['evidence']['arrays.npz']['sha256'],'Saved scan differs')
  with np.load(p/'arrays.npz',allow_pickle=False) as z:scores.append({k:z[k] for k in z.files if k.endswith('_score')})
 old=read(REPO/'work_bq/execution/BQ_A04_ASSOC_V1/A04_POSTPROCESSING/payload/RESULT.json')
 methods={}
 for method,name in [('current','current_associations.jsonl'),('legacy','.legacy_associations.jsonl.pending')]:
  p=payload/name;ph=sha(p);size=p.stat().st_size
  expected_count=sum(len(results[s]['hits'][method]) for s in (0,2,4));check(expected_count==old['method_results'][method]['association_stream']['records'],'Source count differs')
  counts={k:0 for k in ('PASS','UNSUPPORTED','THREE_ON_FAIL','OFF_VETO')};n=0;partial_bytes=0;stop=False;last=None
  with p.open('rb') as f:
   for scan in (0,2,4):
    for candidate in results[scan]['hits'][method]:
     line=f.readline()
     if not line:stop=True;break
     if not line.endswith(b'\n'):
      partial_bytes=len(line);check(f.read(1)==b'','Unterminated record not final');stop=True;break
     record=json.loads(line);reference=h.independently_force(scores,method,candidate)
     check(record==reference,'Retained association not exact expected prefix')
     n+=1;counts[record['status']]+=1;last=candidate
    if stop:break
   check(f.read(1)==b'','Extra data beyond expected stream')
  full=n==expected_count and partial_bytes==0
  if method=='current':
   declared=old['method_results'][method]['association_stream']
   check(full and size==declared['bytes'] and ph==declared['sha256'],'Published current stream not complete expected bytes')
  else:check(not (payload/'legacy_associations.jsonl').exists(),'Unexpected published legacy name after failure')
  check(sha(p)==ph and p.stat().st_size==size,'Retained stream changed during review')
  methods[method]=dict(path=name,expected_records=expected_count,retained_complete_records_verified=n,
    incomplete_final_record_bytes=partial_bytes,missing_complete_records=expected_count-n,
    complete_stream=full,retained_records_form_exact_ordered_prefix=True,
    status_counts_for_retained_records=counts,bytes=size,sha256=ph,last_retained_source=last)
 pins(plan);check(sha(tp)==th and sha(rp)==rh,'Failure closure changed during review')
 report=dict(schema='SETI_BR_INDEPENDENT_FAILED_CLOSURE_REVIEW_V1',status='PASS_FAILED_EVIDENCE_VERIFICATION',
  BR_effective_status='FAIL',BP_original_status='FAIL',BQ_effective_status='EVIDENCE_FAIL',cause='UNESTABLISHED',
  closure_guard_detected_change=True,captured_exception=result['exception'],
  source_guard_code='POSTCLOSE_MUTATION',source_guard_code_basis='Inferred from exact frozen stream_closure.py guard identified in saved traceback; child JSON did not serialize exception.code separately.',
  failure_stage='Legacy pending-stream verification before final-path publication',
  exact_child_exit=2,natural_EOF=True,exact_wait=True,cleanup_complete=True,capture_reasons=capture['reasons'],
  terminal_sha256=th,result_sha256=rh,source_pins_verified=len(plan['source_pins']),input_pins_verified=len(plan['input_pins']),
  evidence_files_rehashed=len(expected),evidence_bytes_rehashed=byte_total,methods=methods,
  prior_input_and_source_pins_unchanged=True,no_false_effective_PASS=True,
  operations=dict(new_RNG_calls=0,new_scan_scores=0,new_saved_association_results=0,missing_records_filled=0,historical_execution_mutations=0),
  full_pair_evidence_qualified=False,
  qualifications=['Complete retained current stream is independently verified against saved arrays, but no successful BR pair closure exists.','Retained legacy pending records are verified only as an ordered prefix; missing records are not supplied.','The closure guard correctly refused qualification. File-change cause remains unestablished. No full839,DATAadmission or astronomical science activation.'],
  reviewer_source_sha256=sha(Path(__file__)),independent_helper_sha256=sha(hp),
  wall_seconds=time.monotonic()-START,completed_utc=datetime.now(timezone.utc).isoformat())
 with OUT.open('x') as f:json.dump(report,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 print(json.dumps(dict(status=report['status'],BR_effective_status=report['BR_effective_status'],methods=methods,wall_seconds=report['wall_seconds'],report_sha256=sha(OUT))),flush=True)
 return 0
if __name__=='__main__':sys.exit(main())
