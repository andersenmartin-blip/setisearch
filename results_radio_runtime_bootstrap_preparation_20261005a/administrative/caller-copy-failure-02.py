"""Retain finished caller streams; identity excludes read-updated access time."""
from pathlib import Path
import hashlib
import json
import os
import stat

BASE=Path('/workspace/scratch/d804553c0e89')
REPO=BASE/'setisearch-status-20261004'
NS=REPO/'results_radio_runtime_bootstrap_preparation_20261005a'

def identity(s):
    return dict(device=s.st_dev,inode=s.st_ino,mode='%04o'%stat.S_IMODE(s.st_mode),
        nlink=s.st_nlink,bytes=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,
        allocated_bytes=s.st_blocks*512)

def main():
    rows=[]
    for kind in ('stdout','stderr'):
        source=BASE/('bootstrap-A-caller.'+kind+'.raw')
        fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:
                raise ValueError('sole-link regular caller stream required')
            raw=bytearray()
            while len(raw)<before.st_size:
                chunk=os.read(fd,min(65536,before.st_size-len(raw)))
                if not chunk: raise ValueError('truncated caller stream')
                raw.extend(chunk)
            if os.read(fd,1) or identity(before)!=identity(os.fstat(fd)) or identity(before)!=identity(source.stat(follow_symlinks=False)):
                raise ValueError('caller stream identity changed')
        finally:os.close(fd)
        raw=bytes(raw);destination=NS/'administrative'/('caller.'+kind+'.raw')
        with destination.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if destination.read_bytes()!=raw:raise ValueError('caller full copy mismatch')
        rows.append(dict(source_path=str(source),repository_path=str(destination.relative_to(REPO)),
            bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
            git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
            source_identity=identity(before),source_before_after_equal=True,
            copy_full_body_equal=True,access_time_outside_identity=True))
    obj=json.loads((BASE/'bootstrap-A-caller.stdout.raw').read_bytes())
    result=dict(streams=rows,caller_complete_json=True,semantic_status=obj['report']['status'],
        selected_whole_scope_elapsed_seconds=obj['selected_whole_scope_elapsed_seconds'],
        final_scope={k:obj['final_scope'][k] for k in ['files','directories','logical_bytes','allocated_bytes','complete']})
    with (BASE/'bootstrap-A-caller-copies.json').open('x') as stream:
        stream.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
