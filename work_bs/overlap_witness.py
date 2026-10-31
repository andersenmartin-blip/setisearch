"""One bounded, read-only overlapping view of diagnostic payload files.

Writes only its own exclusive witness receipt outside the payload. This
controlled overlap tests a possible execution/workspace interaction; it does
not deliberately mutate any writer output.
"""
from pathlib import Path
import hashlib
import json
import os
import time

ROOT = Path(__file__).resolve().parent
TRIAL = ROOT/'execution/BS_FILE_STABILITY_V1/br_overlap'
PAYLOAD = TRIAL/'payload/payload'
OUT = TRIAL.parent/'OVERLAP_WITNESS.json'


def snapshot():
    items = []
    if PAYLOAD.exists():
        for p in sorted(PAYLOAD.glob('*')):
            if not p.is_file():
                continue
            try:
                a = p.stat()
                with p.open('rb') as f:
                    opened = os.fstat(f.fileno())
                    digest = hashlib.file_digest(f,'sha256').hexdigest()
                    closed = os.fstat(f.fileno())
                b = p.stat()
            except FileNotFoundError:
                items.append(dict(path=p.name,observation='Path disappeared during observation; possible normal pending unlink'))
                continue
            def meta(s):
                return dict(device=s.st_dev,inode=s.st_ino,bytes=s.st_size,mode=oct(s.st_mode & 0o777),
                            mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
            items.append(dict(path=p.name,path_before=meta(a),fd_before=meta(opened),
                              fd_after=meta(closed),path_after=meta(b),read_sha256=digest))
    return dict(time_ns=time.time_ns(),monotonic_ns=time.monotonic_ns(),files=items)


def main():
    if OUT.exists():
        raise FileExistsError('Witness already executed')
    start=time.monotonic()
    while not PAYLOAD.exists() and time.monotonic()-start<5:
        time.sleep(.05)
    first=snapshot()
    time.sleep(6)
    last=snapshot()
    result=dict(schema='SETI_BS_READONLY_OVERLAP_WITNESS_V1',first=first,last=last,
                writer_payload_mutations_by_witness=0,wait_seconds=6,
                limitation='Two process views are observations; they do not alone attribute a historical mutation.')
    with OUT.open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps(dict(witness=str(OUT),files_first=len(first['files']),files_last=len(last['files']),
                         sha256=hashlib.sha256(OUT.read_bytes()).hexdigest())),flush=True)


if __name__=='__main__':
    main()
