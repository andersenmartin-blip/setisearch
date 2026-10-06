"""Administrative compiler syntax check only; creates/loads no native module."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

HERE=Path(__file__).resolve().parent


def main():
    for name,maximum in ((resource.RLIMIT_CPU,15),(resource.RLIMIT_AS,256*1024**2),
                         (resource.RLIMIT_NOFILE,64),(resource.RLIMIT_FSIZE,1024**2)):
        resource.setrlimit(name,(maximum,maximum))
    source=HERE/'audit_collector.c';raw=source.read_bytes()
    command=['/usr/bin/cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fsyntax-only',str(source)]
    before=time.monotonic()
    result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=18,check=False,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
    elapsed=time.monotonic()-before
    # Exclusive result names: a failed check is never overwritten by a fix.
    number=1
    while (HERE/('syntax-%d.json'%number)).exists(): number+=1
    for suffix,body in [('stdout.log',result.stdout),('stderr.log',result.stderr)]:
        fd=os.open(HERE/('syntax-%d.%s'%(number,suffix)),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            if os.write(fd,body)!=len(body): raise ValueError('short retained compiler output')
            os.fsync(fd)
        finally: os.close(fd)
    receipt={'schema':'radio-N-c-syntax-administrative-v1','command':command,'returncode':result.returncode,
             'source_pin':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'seconds':elapsed,
             'child_peak_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
             'limits':{'external_wall_seconds':20,'child_timeout_seconds':18,'cpu_seconds':15,
                       'address_space_bytes':256*1024**2,'file_bytes':1024**2,'descriptors':64},
             'built_native_modules':0,'audit_module_loads':0,'target_executions':0,
             'native_collector_observations':0,'runtime_or_science_authority':False,
             'compiler_and_header_reads':'opaque administrative compiler; no runtime read-accounting qualification'}
    body=(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n').encode()
    fd=os.open(HERE/('syntax-%d.json'%number),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        if os.write(fd,body)!=len(body): raise ValueError('short compiler receipt')
        os.fsync(fd)
    finally: os.close(fd)
    print(json.dumps({'check':number,'returncode':result.returncode,'seconds':elapsed}))
    raise SystemExit(result.returncode)


if __name__=='__main__': main()
