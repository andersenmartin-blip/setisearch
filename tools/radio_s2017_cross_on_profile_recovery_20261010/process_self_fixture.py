#!/usr/bin/env python3
"""Root-run metadata-only proc guard fixture; no source/science module import.

AST-extract only the SHA-pinned verify_no_live_owner_processes function. Test
actual procfs self exclusion and one fabricated live OTHER child. The child
runs isolated Python with only sys, treats a filename as an argv marker and
blocks on stdin until this parent closes it. No sleep, arrays, source GET,
scope/admission generation, profile kernel or scientific marker is involved.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    wall_start = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract-source',required=True)
    parser.add_argument('--expected-contract-sha256',required=True)
    parser.add_argument('--receipt',required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'[0-9a-f]{64}',args.expected_contract_sha256) is not None,'Source SHA required')
    source=Path(args.contract_source);receipt=Path(args.receipt)
    require(source.is_absolute() and source.resolve()==source and source.name=='profile_contract.py'
        and not source.is_symlink(),'Canonical contract Python source required')
    require(receipt.is_absolute() and receipt.parent.is_dir() and not receipt.exists(),'New fixture receipt required')
    resource.setrlimit(resource.RLIMIT_CPU,(10,12))
    resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824))
    def expired(signum,frame):
        raise TimeoutError('Proc fixture wall cap')
    signal.signal(signal.SIGALRM,expired);signal.alarm(30)
    raw=source.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==args.expected_contract_sha256,'Pinned source changed')
    tree=ast.parse(raw,filename=str(source))
    selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_no_live_owner_processes']
    require(len(selected)==1 and not selected[0].decorator_list and not selected[0].args.defaults,'Single plain guard required')
    forbidden={'exec','eval','compile','__import__','open','numpy','h5py','hdf5plugin','subprocess',
        'metadata_inventory','load_contract','compute','profile_kernel','main','urlopen','requests'}
    require(not any(isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.Name) and n.id in forbidden
        or isinstance(n,ast.Attribute) and (n.attr.startswith('__') or n.attr in
            {'write_bytes','write_text','unlink','rename','replace','open','system','popen'})
        for n in ast.walk(selected[0])),'Guard extraction gained nonmetadata operations')
    body=ast.Module(body=selected,type_ignores=[])
    safe={'__builtins__':{'int':int,'str':str,'any':any,'FileNotFoundError':FileNotFoundError,
        'ProcessLookupError':ProcessLookupError,'PermissionError':PermissionError},
        'Path':Path,'os':os,'require':require}
    exec(compile(ast.fix_missing_locations(body),'<proc-fixture-guard>','exec'),safe)
    guard=safe['verify_no_live_owner_processes']
    readlink_pid=int(os.readlink('/proc/self'))
    stat_pid=int(Path('/proc/self/stat').read_text().split()[0])
    require(readlink_pid==stat_pid,'Actual procfs self readlink/stat disagree')
    marker=Path(__file__).resolve()
    suffix=marker.name.encode()
    arguments=Path('/proc/self/cmdline').read_bytes().split(b'\0')
    require(any(a==suffix or a.endswith(b'/'+suffix) for a in arguments),'Fixture own argv marker absent')
    scope={'owner_scientific_command_paths':[marker.name]}
    guard(scope)
    child=None;blocked=False;child_usage_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        child=subprocess.Popen([sys.executable,'-I','-S','-c',
            "import sys; print('READY',flush=True); sys.stdin.read()",str(marker)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        require(child.stdout.readline()==b'READY\n','Fabricated metadata child not ready')
        try:
            guard(scope)
        except ValueError as error:
            require(str(error)=='An original scientific numeric/QA process remains active','Unexpected guard failure')
            blocked=True
        require(blocked,'Live OTHER with matching argv was not rejected')
        child.stdin.close()
        require(child.wait(timeout=5)==0,'Fabricated child did not close cleanly')
        guard(scope)
    finally:
        if child is not None:
            if child.poll() is None:
                if child.stdin is not None and not child.stdin.closed:child.stdin.close()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
            for stream in (child.stdout,child.stderr):
                if stream is not None:stream.close()
    child_usage_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    children_cpu=(child_usage_after.ru_utime+child_usage_after.ru_stime
        -child_usage_before.ru_utime-child_usage_before.ru_stime)
    use={'parent_process_CPU_seconds':time.process_time(),'fabricated_child_CPU_seconds':children_cpu,
        'total_CPU_seconds':time.process_time()+children_cpu,'wall_seconds':time.monotonic()-wall_start,
        'parent_peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'child_peak_RSS_bytes':child_usage_after.ru_maxrss*1024}
    require(use['total_CPU_seconds']<=10 and use['wall_seconds']<=30
        and max(use['parent_peak_RSS_bytes'],use['child_peak_RSS_bytes'])<=1073741824,'Proc fixture resource bound')
    require(source.read_bytes()==raw,'Contract source changed during fixture')
    value={'status':'PASS_ACTUAL_PROCFS_SELF_IGNORED_LIVE_OTHER_BLOCKED_AND_CLOSED_OTHER_RELEASED',
        'contract_source_sha256':args.expected_contract_sha256,'contract_source_bytes':len(raw),
        'fixture_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'guard_AST_sha256':hashlib.sha256(ast.dump(selected[0],include_attributes=False).encode()).hexdigest(),
        'os_getpid':os.getpid(),'procfs_self_readlink_PID':readlink_pid,'procfs_self_stat_PID':stat_pid,
        'procfs_namespace_mismatch_observed':os.getpid()!=readlink_pid,
        'actual_SELF_ignored':True,'fabricated_live_OTHER_rejected':blocked,'OTHER_closed_exit0':True,
        'after_OTHER_closed_guard_PASS':True,'target_contract_module_imported':False,
        'source_or_profile_helpers_called':False,'scientific_arrays_imported_or_read':False,
        'new_scientific_attempt_markers':0,'network_calls':0,'sleeps':0,
        'CPU_cap_s':10,'wall_cap_s':30,'memory_cap_bytes':1073741824,**use}
    with receipt.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    signal.alarm(0)
    print(json.dumps({'status':value['status'],**use}))


if __name__=='__main__':main()
