from pathlib import Path
import json,hashlib,os,stat
base=Path('/workspace/scratch/d804553c0e89');repo=base/'setisearch-status-20261004';ns=repo/'results_radio_runtime_bootstrap_preparation_20261005a';rows=[]
for kind in ('stdout','stderr'):
 source=base/('bootstrap-A-caller.'+kind+'.raw');before=source.stat();raw=source.read_bytes();after=source.stat();assert before==after and before.st_nlink==1 and stat.S_ISREG(before.st_mode)
 destination=ns/'administrative'/('caller.'+kind+'.raw')
 with destination.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 assert destination.read_bytes()==raw
 rows.append(dict(source_path=str(source),repository_path=str(destination.relative_to(repo)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),source_identity=dict(device=before.st_dev,inode=before.st_ino,mode=oct(stat.S_IMODE(before.st_mode)),nlink=before.st_nlink,mtime_ns=before.st_mtime_ns,ctime_ns=before.st_ctime_ns,allocated_bytes=before.st_blocks*512),source_before_after_equal=True,copy_full_body_equal=True))
obj=json.loads((base/'bootstrap-A-caller.stdout.raw').read_bytes());print(json.dumps(dict(streams=rows,caller_complete_json=True,semantic_status=obj['report']['status'],selected_whole_scope_elapsed_seconds=obj['selected_whole_scope_elapsed_seconds'],final_scope={k:obj['final_scope'][k] for k in ['files','directories','logical_bytes','allocated_bytes','complete']})))
with (base/'bootstrap-A-caller-copies.json').open('x') as f:f.write(json.dumps(rows,sort_keys=True,indent=2)+'\n')
