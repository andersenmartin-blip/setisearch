"""One bounded administrative self snapshot; no foreign PID or target launcher."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
import time

HERE=Path(__file__).resolve().parent
AUTHORITY='33f543de37ad6e66fac46d35d892024aa7b1776c'
LIMITS={'wall_seconds':20,'cpu_seconds':10,'address_space_bytes':256*1024**2,
        'artifact_bytes':1024**2,'explicit_read_bytes':4*1024**2,'descriptors':64}


def canonical(value): return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def pin(raw): return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def ordinary(path):
    if not path.is_absolute(): raise ValueError('absolute path required')
    for part in (path,*path.parents):
        if part.is_symlink(): raise ValueError('ordinary source/output path component required')


class Budget:
    def __init__(self): self.start=time.monotonic();self.read=self.written=0
    def check(self,read=0,written=0):
        if (time.monotonic()-self.start>LIMITS['wall_seconds'] or self.read+read>LIMITS['explicit_read_bytes']
                or self.written+written>LIMITS['artifact_bytes']): raise ValueError('administrative envelope exceeded')
    def body(self,fd,maximum,offset=None):
        self.check(read=maximum)
        raw=os.read(fd,maximum) if offset is None else os.pread(fd,maximum,offset)
        self.read+=len(raw);self.check();return raw
    def write(self,path,raw):
        self.check(written=len(raw))
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        try:
            amount=os.write(fd,raw);self.written+=amount
            if amount!=len(raw): raise ValueError('short retained artifact write')
            os.fsync(fd)
        finally: os.close(fd)


def preflight(expected_freeze,budget):
    freeze_path=HERE/'SOURCE_FREEZE.json';ordinary(freeze_path)
    if not stat.S_ISREG(freeze_path.lstat().st_mode) or freeze_path.stat().st_size>65536:
        raise ValueError('bounded ordinary freeze required')
    fd=os.open(freeze_path,os.O_RDONLY|os.O_NOFOLLOW)
    try: raw=budget.body(fd,65536)
    finally: os.close(fd)
    if pin(raw)['sha256']!=expected_freeze: raise ValueError('exact publicly read-back freeze required')
    f=json.loads(raw)
    if f['status']!='SOURCE_PLUS_ONE_ADMINISTRATIVE_SELF_SNAPSHOT_NO_TARGET_AUTHORITY' or f['authority_parent']!=AUTHORITY or f['limits']!=LIMITS:
        raise ValueError('exact M administrative contract required')
    if not {'mapping.py','capture_self.py'}<=set(f['source_files']): raise ValueError('both executable sources required')
    for name,expected in f['source_files'].items():
        if Path(name).name!=name or name in ('.','..'): raise ValueError('flat source member required')
        p=HERE/name;ordinary(p)
        if not stat.S_ISREG(p.lstat().st_mode) or p.stat().st_size!=expected['bytes'] or expected['bytes']>256*1024:
            raise ValueError('bounded original source member required')
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        try: body=budget.body(fd,expected['bytes']+1)
        finally: os.close(fd)
        if pin(body)!=expected: raise ValueError('frozen source body differs')
    spec=importlib.util.spec_from_file_location('m_mapping',HERE/'mapping.py')
    component=importlib.util.module_from_spec(spec);spec.loader.exec_module(component)
    return component,pin(raw)


def read_proc(proc,name,cap,budget):
    # Fixed names only; no generic caller-controlled proc path or foreign PID.
    if name not in ('maps','auxv','stat'): raise ValueError('fixed metadata proc file required')
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=proc)
    try:
        chunks=[];size=0
        while True:
            raw=budget.body(fd,min(65536,cap+1-size))
            size+=len(raw)
            if size>cap: raise ValueError('proc body cap')
            if not raw: return b''.join(chunks)
            chunks.append(raw)
    finally: os.close(fd)


def process_identity(proc,pid,budget):
    raw=read_proc(proc,'stat',4096,budget)
    close=raw.rfind(b')')
    if close<0 or int(raw.split(b'(',1)[0].strip())!=pid: raise ValueError('proc pid identity differs')
    fields=raw[close+2:].split()
    if len(fields)<20: raise ValueError('short proc stat')
    ticks=int(fields[19]);ns=os.stat('ns/pid',dir_fd=proc)
    if ticks<=0 or ns.st_ino<=0: raise ValueError('bounded positive start/namespace required')
    return {'local_pid':pid,'starttime_ticks':ticks,'namespace_device':ns.st_dev,'namespace_inode':ns.st_ino}


def held_identity(st):
    return [st.st_dev,st.st_ino,st.st_mode,st.st_nlink,st.st_size,st.st_mtime_ns,st.st_ctime_ns]


def snapshot(component,root,budget,freeze_pin):
    pid=os.getpid();proc=os.open('/proc/'+str(pid),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    exe=mem=None
    try:
        before=process_identity(proc,pid,budget)
        maps1=read_proc(proc,'maps',component.MAX_MAP_BYTES,budget)
        aux1=read_proc(proc,'auxv',component.MAX_AUX_BYTES,budget)
        budget.write(root/'PRE.maps.txt',maps1);budget.write(root/'PRE.auxv.hex',aux1.hex().encode()+b'\n')
        aux=component.parse_auxv(aux1);page=aux[6]
        if page!=os.sysconf('SC_PAGE_SIZE'): raise ValueError('actual page size differs')
        rows=component.parse_maps(maps1,page)
        # These are explicit kernel-link exceptions, not general symlink admission.
        exe=os.open('exe',os.O_RDONLY|os.O_CLOEXEC,dir_fd=proc);info=os.fstat(exe)
        if not stat.S_ISREG(info.st_mode): raise ValueError('ordinary actual administrative executable required')
        path=os.readlink('exe',dir_fd=proc)
        prefix=budget.body(exe,min(info.st_size,component.MAX_ELF_PREFIX),0)
        budget.write(root/'ADMIN_EXECUTABLE_PREFIX.hex',prefix.hex().encode()+b'\n')
        elf=component.parse_elf(prefix,info.st_size)
        base=component.administrative_main_base(elf,aux)
        binding1=component.executable_binding(rows,elf,base,{'device':info.st_dev,'inode':info.st_ino,'bytes':info.st_size},page)
        region=component.vdso_region(rows,aux);length=region['end']-region['start']
        mem=os.open('mem',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW,dir_fd=proc)
        first=budget.body(mem,length,region['start'])
        budget.write(root/'VDSO.first.hex',first.hex().encode()+b'\n')
        second=budget.body(mem,length,region['start'])
        budget.write(root/'VDSO.second.hex',second.hex().encode()+b'\n')
        witness=component.vdso_witness(rows,aux,first,second)
        maps2=read_proc(proc,'maps',component.MAX_MAP_BYTES,budget)
        aux2=read_proc(proc,'auxv',component.MAX_AUX_BYTES,budget)
        budget.write(root/'POST.maps.txt',maps2);budget.write(root/'POST.auxv.hex',aux2.hex().encode()+b'\n')
        after=process_identity(proc,pid,budget)
        if before!=after or aux1!=aux2 or held_identity(info)!=held_identity(os.fstat(exe)):
            raise ValueError('administrative process/auxv/held executable identity drift')
        post_rows=component.parse_maps(maps2,page)
        binding2=component.executable_binding(post_rows,elf,base,{'device':info.st_dev,'inode':info.st_ino,'bytes':info.st_size},page)
        if canonical(binding1)!=canonical(binding2) or component.vdso_region(post_rows,aux)!=region:
            raise ValueError('selected executable/kernel mapping drift')
        kernel_other=[row for row in rows if bytes.fromhex(row['raw_name_hex']) in (b'[vvar]',b'[vvar_vclock]',b'[vsyscall]')]
        return {'schema':'radio-M-administrative-self-snapshot-v1','status':'SELF_MAPPING_AND_VDSO_OBSERVED_TARGET_UNQUALIFIED',
                'authority_parent':AUTHORITY,'source_freeze_pin':freeze_pin,'process':before,
                'administrative_executable':path,'held_executable_identity':held_identity(info),'executable_elf':elf,
                'executable_mapping_before':binding1,'executable_mapping_after':binding2,'vdso':witness,
                'whole_maps_equal':maps1==maps2,'other_kernel_mappings_unread_and_unqualified':kernel_other,
                'raw_maps_pins':[pin(maps1),pin(maps2)],'auxv_pins':[pin(aux1),pin(aux2)],
                'complete_executable_body_hash_checked':False,'full_native_graph_qualified':False,
                'observer_kernel_mapping_interval_qualified':False,'target_vdso_admitted':False,
                'L_native_collector_activated':False,'recovered_target_executions':0,'target_package_imports':0,
                'codec_or_science_allocation':False,'spectra_opened':False,'runtime_qualified':False}
    finally:
        for fd in (mem,exe,proc):
            if fd is not None: os.close(fd)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--new-output',required=True);parser.add_argument('--freeze-sha256',required=True)
    args=parser.parse_args()
    for kind,maximum in ((resource.RLIMIT_CPU,LIMITS['cpu_seconds']),(resource.RLIMIT_AS,LIMITS['address_space_bytes']),
                         (resource.RLIMIT_NOFILE,LIMITS['descriptors']),(resource.RLIMIT_FSIZE,LIMITS['artifact_bytes'])):
        resource.setrlimit(kind,(maximum,maximum))
    budget=Budget();component,freeze_pin=preflight(args.freeze_sha256,budget)
    root=Path(args.new_output);ordinary(root);root.mkdir(mode=0o700,exist_ok=False)
    budget.write(root/'START.json',canonical({'schema':'radio-M-admin-start-v1','self_pid_only':os.getpid(),'freeze':freeze_pin,'limits':LIMITS,'target_authority':False}))
    try:
        result=snapshot(component,root,budget,freeze_pin)
        result.update(explicit_read_bytes=budget.read,written_bytes_before_result=budget.written,
                      measured_seconds_before_result=time.monotonic()-budget.start,
                      controller_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,limits=LIMITS)
        budget.write(root/'RESULT.json',canonical(result))
        print(json.dumps({'status':result['status'],'read_bytes':budget.read,'seconds':result['measured_seconds_before_result'],'output':str(root)}))
    except BaseException as exc:
        failure={'schema':'radio-M-admin-failure-v1','status':'FAILED_CLOSED_NO_RETRY','type':type(exc).__name__,'reason':str(exc),
                 'errno':getattr(exc,'errno',None),'explicit_read_bytes':budget.read,'written_bytes':budget.written,
                 'source_freeze_pin':freeze_pin,'runtime_or_native_or_science_authority':False}
        try: budget.write(root/'FAILURE.json',canonical(failure))
        except BaseException as secondary: exc.add_note('failure retention: '+repr(secondary))
        raise


if __name__=='__main__': main()
