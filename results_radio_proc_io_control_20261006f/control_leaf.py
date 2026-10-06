"""One harmless deterministic IO control; no science or installed package import."""
import argparse,hashlib,json,os,stat,sys,time
from pathlib import Path

AUTHORITY={k:False for k in ('scientific_execution_authorized','spectral_access_authorized',
    'runtime_qualified','source_closure_qualified','native_custody_qualified','cas_qualified','certificate_issued')}
def proc_io():
    fd=os.open('/proc/self/io',os.O_RDONLY|os.O_CLOEXEC)
    try:
        raw=os.read(fd,16385)
        if len(raw)>16384:raise ValueError('bounded own proc IO')
    finally:os.close(fd)
    values={}
    for line in raw.decode('ascii').splitlines():
        key,value=line.split(': ',1)
        if key in values or not value.isdecimal():raise ValueError('own proc IO syntax')
        values[key]=int(value)
    if set(values)!={'rchar','wchar','syscr','syscw','read_bytes','write_bytes','cancelled_write_bytes'}:
        raise ValueError('complete own proc IO fields')
    return {'values':values,'raw':raw.decode('ascii'),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def main():
    parser=argparse.ArgumentParser()
    for option in ('payload','payload-sha256','output'):parser.add_argument('--'+option,required=True)
    args=parser.parse_args()
    if not(sys.flags.isolated and sys.flags.dont_write_bytecode and sys.flags.no_site):
        raise ValueError('isolated stdlib-only -I -B -S required')
    if sys.prefix!=sys.base_prefix:raise ValueError('installed venv is forbidden for this control')
    payload=Path(args.payload)
    if payload.resolve()!=payload:raise ValueError('canonical payload required')
    # Bounded startup interval lets the sole owner bind this still-live process.
    time.sleep(0.25)
    fd=os.open(payload,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size!=131072 or before.st_nlink!=1:
            raise ValueError('exact regular deterministic payload required')
        own_before=proc_io();charged=0;digests=[]
        for _ in range(8):
            os.lseek(fd,0,os.SEEK_SET);digest=hashlib.sha256();left=131072
            while left:
                raw=os.read(fd,min(left,32768))
                if not raw:raise ValueError('short control payload')
                charged+=len(raw);left-=len(raw);digest.update(raw)
            if digest.hexdigest()!=args.payload_sha256:raise ValueError('control payload hash mismatch')
            digests.append(digest.hexdigest())
        after=os.fstat(fd);named=payload.stat(follow_symlinks=False)
        facts=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if not facts(before)==facts(after)==facts(named):raise ValueError('payload identity changed')
        own_after=proc_io()
    finally:os.close(fd)
    if charged!=1048576 or own_after['values']['rchar']-own_before['values']['rchar']<charged:
        raise ValueError('own logical counter cannot cover deterministic reads')
    if any(name in sys.modules for name in ('numpy','h5py','hdf5plugin')):
        raise ValueError('scientific package unexpectedly imported')
    result=dict(schema='radio-proc-io-control-leaf-v1',status='DETERMINISTIC_READ_CONTROL_COMPLETED',
        authority=AUTHORITY,pid=os.getpid(),python_version=sys.version,executable=sys.executable,
        isolated=True,no_site=True,dont_write_bytecode=True,installed_python_launched=False,
        workload_explicit_read_bytes=charged,passes=8,payload_bytes=131072,
        payload_sha256=args.payload_sha256,pass_sha256=digests,
        own_io_before=own_before,own_io_after=own_after,scientific_modules_imported=False,
        limitation='Self counters and parent kernel observations do not identify every loader/file operation.')
    raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    if len(raw)>65536:raise ValueError('leaf report cap')
    out=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    try:
        view=memoryview(raw)
        while view:
            n=os.write(out,view)
            if n<=0:raise ValueError('report write progress')
            view=view[n:]
        os.fsync(out)
    finally:os.close(out)
    print(json.dumps({'status':result['status'],'output_sha256':hashlib.sha256(raw).hexdigest(),
                      'workload_explicit_read_bytes':charged},sort_keys=True))
    return 0
if __name__=='__main__':raise SystemExit(main())
