#!/usr/bin/env python3
"""Root GO received2026-10-12 for independent ranking QA only; no power arrays."""
import importlib.util,json,resource,time,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent/'independent_dc_qa.py'
spec=importlib.util.spec_from_file_location('independent_qa',p);qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
import numpy as np
qa.np=np
CPU,WALL,RAM=600,900,2*1024**3
resource.setrlimit(resource.RLIMIT_CPU,(CPU,CPU+1));resource.setrlimit(resource.RLIMIT_AS,(RAM,RAM))
wall,cpu=time.monotonic(),time.process_time();pins={};mismatches=[];checks=0;counts={}
def checked(p,d=None):
 actual=qa.pin(p)
 qa.require(d is None or all(actual[k]==d[k] for k in ('bytes','sha256')),'Input pin differs')
 qa.require(str(p) not in pins or actual==pins[str(p)],'Input changed');pins[str(p)]=actual;return p
def equal(a,b,label):
 global checks
 checks+=1
 ok=np.array_equal(np.asarray(a),np.asarray(b))
 if not ok:mismatches.append(label)
 return ok
def near(a,b,label):
 return equal(a,b,label)
qa.compare_ranking({},near,equal,checked,qa.read,counts)
for input_path,v in pins.items():qa.require(qa.pin(Path(input_path))==v,'Input changed during QA')
result={'status':'PASS_INDEPENDENT_TOP120_GEOMETRY_QA' if not mismatches else 'FAIL_MISMATCHES_PRESERVED','counts':counts,
        'checks':checks,'mismatches':mismatches,'input_pins':list(pins.values()),'qa_source_pin':qa.pin(Path(__file__)),
        'arithmetic_code_pin':qa.pin(p),'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-wall,
        'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'root_GO':'Parent root message authorized independent ranking QA after ready outputs; primary arrays not opened.',
        'detector_imported':False,'raw_power_arrays_opened':0,'new_telescope_requests':0,'reranked_records':0,
        'limitations':['Annotation preserves stored exposed rankings and checks geometric contact only. It does not provide physical source classification or calibrated search evidence.']}
qa.save(Path(__file__).resolve().parent/'RANKING_QA_RECEIPT.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','qa_source_pin','arithmetic_code_pin')}))
