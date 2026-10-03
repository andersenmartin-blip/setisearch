#!/usr/bin/env python3
"""Run metadata preparation/preflight under the exact outer launcher guard.

No marker, claim, journal, scope, dispatch, source payload or telescope access is
created here. Three independently supplied SHA256 pins bind the guard source,
the metadata helper and the resolved isolated Python executable before spawn.
The inherited process-security domain then matches the prospective launcher.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import types


ROOT=Path(__file__).resolve().parents[1]
GUARD=ROOT/'scripts/radio_native_v3_process_tree_supervisor.py'
HELPER=Path(__file__).resolve().parent/'qualify-successor-execution-preparation.py'


def held(path,expected):
    if type(expected) is not str or not re.fullmatch('[0-9a-f]{64}',expected):
        raise ValueError('Independent lowercase SHA256 required')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>32*1024**2:
            raise ValueError('Bounded regular preparation dependency required')
        raw=b''
        while True:
            block=os.read(fd,65536)
            if not block:break
            raw+=block
        after=os.fstat(fd);named=os.stat(path,follow_symlinks=False)
        key=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns)
        if key(before)!=key(after) or key(after)!=key(named):raise ValueError('Preparation dependency changed')
    finally:os.close(fd)
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Independent preparation dependency pin differs')
    return raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt',type=int,required=True)
    parser.add_argument('--supervisor-sha256',required=True)
    parser.add_argument('--helper-sha256',required=True)
    parser.add_argument('--python-sha256',required=True)
    parser.add_argument('--preflight-only',action='store_true')
    args=parser.parse_args()
    if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise ValueError('Guarded preparation parent requires -I -S -B')
    guard_raw=held(GUARD,args.supervisor_sha256)
    helper_raw=held(HELPER,args.helper_sha256)
    python=str(Path(sys.executable).resolve());held(python,args.python_sha256)
    guard=types.ModuleType('held_preparation_guard');guard.__file__=str(GUARD)
    exec(compile(guard_raw,str(GUARD),'exec'),guard.__dict__)
    argv=[python,'-I','-S','-B',str(HELPER),'--attempt',str(args.attempt)]
    if args.preflight_only:argv.append('--preflight-only')
    completed=subprocess.run(argv,env=dict(os.environ),
        preexec_fn=guard.install_child_escape_guard,check=False,timeout=60)
    if held(GUARD,args.supervisor_sha256)!=guard_raw or held(HELPER,args.helper_sha256)!=helper_raw:
        raise ValueError('Guarded preparation source changed through child lifetime')
    raise SystemExit(completed.returncode)


if __name__=='__main__':main()
