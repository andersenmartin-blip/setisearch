"""Verify retained BQ streams only; do not fill, overwrite or rescore anything."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,importlib.util,json,time,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
RUN=ROOT/'execution/BQ_A04_ASSOC_V1';BP=REPO/'work_bp/execution/BP_FIXED24_V1'
OUT=ROOT/'review/FORENSIC_REVIEW_BQ.json';START=time.monotonic()
helper_path=REPO/'work_bp/review/audit_results.py'
spec=importlib.util.spec_from_file_location('forensic_independent_formula',helper_path)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def check(ok,msg):
 if not ok:raise ValueError(msg)
 if time.monotonic()-START>118:raise TimeoutError('Forensic review budget118seconds')
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify_pins(plan):
 for pin in plan['source_pins']+plan['input_pins']:
  p=REPO/pin['path'];check(p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'],'Changed bound source/input')
def main():
 check(not OUT.exists(),'Forensic report already exists')
 plan=read(ROOT/'BQ_POSTPROCESSING_PLAN.json');verify_pins(plan)
 terminal_path=RUN/'TERMINAL_BQ.json';terminal=read(terminal_path);terminal_hash=sha(terminal_path)
 check(terminal['status']=='PASS','Historical capture record unexpectedly changed')
 payload=RUN/'A04_POSTPROCESSING/payload';body=read(payload/'RESULT.json');result_hash=sha(payload/'RESULT.json')
 bound={e['path']:e for e in terminal['files']}
 results=[];scores=[]
 for scan in range(6):
  p=BP/'A04/payload'/f'scan{scan}';r=read(p/'RESULT.json');results.append(r)
  check(r['status']=='PASS' and r['scan_index']==scan and sha(p/'arrays.npz')==r['evidence']['arrays.npz']['sha256'],'Changed scan')
  with np.load(p/'arrays.npz',allow_pickle=False) as z:scores.append({k:z[k] for k in z.files if k.endswith('_score')})
 methods={}
 for method in ['current','legacy']:
  declaration=body['method_results'][method]['association_stream'];p=payload/declaration['path']
  actual_size=p.stat().st_size;actual_sha=sha(p);tb=bound[str(p.relative_to(RUN))]
  check(tb['bytes']==actual_size and tb['sha256']==actual_sha,'Terminal no longer binds current bytes')
  expected_count=sum(len(results[s]['hits'][method]) for s in [0,2,4])
  check(expected_count==declaration['records']==body['method_results'][method]['source_ON_hits'],'Source count differs')
  counts={k:0 for k in ['PASS','UNSUPPORTED','THREE_ON_FAIL','OFF_VETO']};line_count=0;exhausted=False;last_source=None
  with p.open('rb') as f:
   for scan in [0,2,4]:
    for candidate in results[scan]['hits'][method]:
     line=f.readline()
     if not line:exhausted=True;break
     check(line.endswith(b'\n'),'Partial final JSONL line')
     record=json.loads(line);expected=h.independently_force(scores,method,candidate)
     check(record==expected,'Retained record not exact expected prefix')
     counts[record['status']]+=1;line_count+=1;last_source=candidate
    if exhausted:break
   check(f.read(1)==b'','Unexpected trailing bytes')
  missing=expected_count-line_count
  if method=='current':
   check(expected_count==43306 and line_count==36857 and missing==6449,'Unexpected current truncation identity')
   check(actual_size==71236624 and actual_sha=='f5c46abc1a3d4347fc35e7cdef958ab84227f2f8b05d183b66287b734afd9bb4','Current bytes changed')
   check(declaration['bytes']==82645873 and declaration['sha256']=='c2ac481a772ade86eaeabc3b5fab401faa970cddee0edd261d1cced8e26b163d','Original close claim changed')
  else:
   check(expected_count==43845 and missing==0 and actual_size==declaration['bytes'] and actual_sha==declaration['sha256'],'Legacy not complete')
   check(counts==body['method_results'][method]['association_counts'],'Legacy counts differ')
  check(sha(p)==actual_sha and p.stat().st_size==actual_size,'Stream changed during audit')
  methods[method]=dict(expected_records=expected_count,retained_records_verified=line_count,missing_records=missing,
   retained_records_form_exact_ordered_prefix=True,retained_status_counts=counts,last_retained_source=last_source,
   actual_bytes=actual_size,actual_sha256=actual_sha,declared_closed_bytes=declaration['bytes'],declared_closed_sha256=declaration['sha256'],
   matches_closed_declaration=(actual_size==declaration['bytes'] and actual_sha==declaration['sha256']))
 verify_pins(plan);check(sha(terminal_path)==terminal_hash and sha(payload/'RESULT.json')==result_hash,'Closure evidence changed')
 report=dict(schema='SETI_BQ_FORENSIC_REVIEW_V1',status='PASS_RETAINED_BYTES_VERIFICATION',effective_evidence_status='FAIL',
  cause='UNESTABLISHED',historical_capture_status='PASS',historical_result_status='PASS',historical_statuses_unchanged=True,
  current_association_gate_qualified=False,BP_original_status='FAIL',methods=methods,
  discrepancy='Result close receipt binds a complete43306record currentstream but terminal/file bind only its first36857records.6449requiredrecords are absent. Legacy43845recordstream is complete and matches every saved-score endpoint.',
  terminal_sha256=terminal_hash,result_sha256=result_hash,reviewer_source_sha256=sha(Path(__file__)),independent_helper_sha256=sha(helper_path),
  operations=dict(new_RNG_calls=0,new_scan_scores=0,new_saved_association_results=0,missing_records_reconstructed_or_saved=0,execution_files_mutated=0),
  qualifications=['Verified only retained ordered records against fixed saved-score arrays.','No missing current records were supplied or silently inferred as passing.','Original BQ cannot receive complete evidence credit; BP remains failed.'],
  wall_seconds=time.monotonic()-START,completed_utc=datetime.now(timezone.utc).isoformat())
 with OUT.open('x') as f:json.dump(report,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
 print(json.dumps(dict(status=report['status'],effective_evidence_status=report['effective_evidence_status'],methods=methods,wall_seconds=report['wall_seconds'],report_sha256=sha(OUT))),flush=True)
 return 0
if __name__=='__main__':sys.exit(main())
