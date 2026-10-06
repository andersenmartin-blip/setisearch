"""One distinct harmless direct-child kernel IO control.

This gate never opens a telescope/HDF5 dataset and issues no runtime certificate.
"""
import argparse
import hashlib
import types
import json
import os
from pathlib import Path
import resource
import signal
import stat
import sys
import time

IDENTITY = 'radio-proc-io-control-20261006f'
SCHEMA = 'radio-proc-io-control-freeze-v1'
MAX_PARENT_READ = 512 * 1024**2
MAX_GATE_READ = 448 * 1024**2
MAX_STORAGE = 16 * 1024**2

class Refusal(Exception):
    pass

def require(ok, message):
    if not ok:
        raise Refusal(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

class Reads:
    def __init__(self):
        self.charged = 0
    def raw(self, path, cap=128*1024**2, expected=None):
        path = Path(path)
        require(str(path.resolve()) == str(path), 'canonical held path required')
        fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, 'regular bounded input required')
            self.charged += before.st_size
            require(self.charged <= MAX_GATE_READ, 'root explicit read reservation')
            chunks = []
            left = before.st_size
            while left:
                data = os.read(fd, min(1024**2, left))
                require(bool(data), 'short held read')
                left -= len(data)
                chunks.append(data)
            after = os.fstat(fd)
            named = path.stat(follow_symlinks=False)
            facts = lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            require(facts(before) == facts(after) == facts(named), 'input custody changed during read')
            raw = b''.join(chunks)
            if expected is not None:
                require(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'] and
                        stat.S_IMODE(before.st_mode) == expected['mode'], 'current input pin mismatch')
            return raw
        finally:
            os.close(fd)
    def pin(self, pin):
        return self.raw(pin['path'], expected=pin)

def write_new(path, raw, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, mode)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            require(count > 0, 'output write failed')
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)

def json_checked(raw, expected_sha):
    require(sha(raw) == expected_sha, 'external raw hash mismatch')
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=unique)
    require(type(result) is dict, 'JSON object required')
    return result

LIMITS = dict(wall_seconds=30,operation_seconds=20,child_wall_seconds=10,child_cpu_seconds=5,
    parent_address_space_bytes=256*1024**2,child_address_space_bytes=128*1024**2,
    parent_read_bytes=MAX_PARENT_READ,root_explicit_read_bytes=MAX_GATE_READ,
    supervisor_pin_read_bytes=32*1024**2,supervisor_proc_read_bytes=16*1024**2,
    misc_stream_read_bytes=16*1024**2,opaque_child_read_reserve_bytes=16*1024**2,
    joined_read_bytes=528*1024**2,artifact_bytes=MAX_STORAGE,terminal_reserve_bytes=1024**2,
    output_file_bytes=1024**2,input_file_bytes=128*1024**2,stdout_bytes=65536,
    stderr_bytes=65536,file_count=2000,directory_count=128,child_dispatches=1,
    child_cleanup_seconds=2,child_sample_interval_seconds=0.02)

def admit(freeze,proof,marker,freeze_hash,marker_hash):
    require(freeze['schema']==SCHEMA and freeze['identity']==IDENTITY and freeze['limits']==LIMITS,
            'distinct exact bounded metadata scope required')
    for key,value in dict(single_use=True,automatic_successor=False,engineering_only=True,network=False,
                          install=False,hdf5_dataset_access=False,scientific_authority=False).items():
        require(freeze[key] is value,'metadata-only authority flags')
    require(marker['schema']=='radio-proc-io-control-activation-v1' and
            marker['identity']==IDENTITY and marker['freeze_sha256']==freeze_hash and
            marker['single_use'] is True and marker['automatic_successor'] is False,'activation scope')
    require(proof['schema']=='radio-proc-io-control-publication-proof-v1' and
            proof['repository']=='andersenmartin-blip/setisearch' and
            proof['branch']=='m43-support-qualification' and
            proof['preparation_commit']==marker['prepared_commit'] and
            proof['preparation_tree']==marker['prepared_tree'] and
            type(proof['activation_commit']) is str and len(proof['activation_commit'])==40 and
            proof['sole_parent']==marker['prepared_commit'] and
            proof['changed_paths']==[freeze['marker_repository_path']] and
            proof['marker_sha256']==marker_hash and proof['full_preparation_readback_exact'] is True and
            proof['marker_readback_exact'] is True and proof['source_readbacks']==freeze['published_sources'],
            'immutable publication proof')
    source_paths={p['path'] for p in freeze['source_pins']}
    published_paths={p['local_path'] for p in freeze['published_sources'].values()}
    require(len(source_paths)==len(freeze['source_pins']) and source_paths <= published_paths,
            'unique source publication coverage')
    published_by_local={p['local_path']:p for p in freeze['published_sources'].values()}
    require(len(published_by_local)==len(freeze['published_sources']),'unique source representation')
    for pin in freeze['source_pins']:
        representation=published_by_local[pin['path']]
        require(pin['bytes']==representation['raw_bytes'] and pin['sha256']==representation['raw_sha256'],
                'published raw source bytes bind executed inputs')
    executable_paths={freeze[k] for k in ('gate_source_path','launcher_source_path','supervisor_source_path',
          'observer_source_path','control_source_path','payload_path','phase2_path')}
    require(executable_paths <= source_paths,'all source/driver inputs pinned')
    all_paths=source_paths|{p['path'] for p in freeze['runtime_pins']}
    require({freeze['python_executable'],freeze['guard_path'],freeze['exec_seal_path']} <= all_paths,
            'all executed binaries pinned')

def validate_control(metadata,capture,payload_sha256,python_executable):
    authority_keys={'scientific_execution_authorized','spectral_access_authorized','runtime_qualified',
        'source_closure_qualified','native_custody_qualified','cas_qualified','certificate_issued'}
    require(metadata['schema']=='radio-proc-io-control-leaf-v1' and
        metadata['status']=='DETERMINISTIC_READ_CONTROL_COMPLETED' and
        metadata['workload_explicit_read_bytes']==1048576 and metadata['passes']==8 and
        metadata['payload_bytes']==131072 and metadata['payload_sha256']==payload_sha256 and
        metadata['pass_sha256']==[payload_sha256]*8 and
        metadata['scientific_modules_imported'] is False and
        metadata['installed_python_launched'] is False and
        metadata['isolated'] is True and metadata['no_site'] is True and
        metadata['dont_write_bytecode'] is True and metadata['executable']==python_executable and
        set(metadata['authority'])==authority_keys and
        all(v is False for v in metadata['authority'].values()),'exact harmless deterministic control')
    terminal=capture.get('terminal_proc')
    require(type(terminal) is dict and terminal.get('available') is True and
        terminal.get('terminal_observed') is True and terminal.get('wnowait_requested') is True,
        'terminal child kernel IO must be observed, never replaced by zero')
    binding=capture.get('proc_resolution');snapshot=terminal.get('snapshot')
    require(type(binding) is dict and type(snapshot) is dict and
        metadata['pid']==capture['pid']==terminal['waitid_pid']==snapshot['local_wait_pid']==binding['local_wait_pid'] and
        snapshot['outer_proc_pid']==binding['outer_proc_pid'] and
        snapshot['starttime_ticks']==binding['child_starttime_ticks'] and
        snapshot['held_proc_directory_identity']==binding['held_child_directory_identity'],
        'same kernel-observed waitable child and retained leaf report')
    io=terminal.get('io');required={'rchar','wchar','syscr','syscw','read_bytes','write_bytes','cancelled_write_bytes'}
    require(type(io) is dict and set(io)==required and
        all(type(n) is int and n>=0 for n in io.values()),'complete terminal kernel IO fields')
    before=metadata['own_io_before']['values'];after=metadata['own_io_after']['values']
    require(after['rchar']-before['rchar']>=1048576 and io['rchar']>=after['rchar'] and
        io['rchar']>=1048576,'parent terminal counter covers known logical reads')
    return dict(workload_explicit_read_bytes=1048576,child_self_rchar_delta=after['rchar']-before['rchar'],
        terminal_kernel_io=io,terminal_kernel_rchar_covers_known_workload=True,
        namespace_binding=capture.get('proc_resolution'),
        no_per_file_attribution_claim=True,no_runtime_or_scientific_certificate=True)

def inventory(root,reads):
    entries=[];logical=allocated=directories=0
    for directory,names,files in os.walk(root,followlinks=False):
        st=Path(directory).lstat();directories+=1
        require(stat.S_ISDIR(st.st_mode) and directories<=128,'artifact directory limit/kind')
        logical+=st.st_size;allocated+=st.st_blocks*512
        for name in names:require(not (Path(directory)/name).is_symlink(),'artifact directory symlink')
        for name in sorted(files):
            path=Path(directory)/name;st=path.lstat()
            require(stat.S_ISREG(st.st_mode) and st.st_size<=1024**2 and len(entries)<2000,
                    'artifact regular file limit')
            raw=reads.raw(path,1024**2);logical+=st.st_size;allocated+=st.st_blocks*512
            entries.append(dict(path=path.relative_to(root).as_posix(),bytes=len(raw),sha256=sha(raw),
                                mode=stat.S_IMODE(st.st_mode),allocated_bytes=st.st_blocks*512))
        require(max(logical,allocated)<=MAX_STORAGE-1024**2,'artifact terminal reservation')
    return dict(entries=entries,files=len(entries),directories=directories,logical_bytes=logical,
                allocated_bytes=allocated,excludes_terminal_result_file='result.json',
                final_inventory_not_transient_storage_peak=True)

def load_module(path,name,raw):
    module=types.ModuleType(name);module.__file__=path;sys.modules[name]=module
    exec(compile(raw,path,'exec'),module.__dict__)
    return module

def run(args):
    started=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
    def expired(signum,frame):raise Refusal('whole metadata-scope deadline')
    signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,30)
    operation_deadline=started+20
    reads=Reads();root_fd=None;freeze=None;root=None;spent=False
    result=dict(schema='radio-proc-io-control-result-v1',identity=IDENTITY,status='FAILED_CLOSED',
        runtime_qualified=False,scientific_authority=False,full_native_io_custody_qualified=False,
        full_scientific_closure_qualified=False,automatic_successor=False,network_requests=0,
        installations=0,hdf5_dataset_reads=0,children=[])
    manifest=None
    def recheck_root():
        held=os.fstat(root_fd);named=root.stat(follow_symlinks=False)
        require([held.st_dev,held.st_ino]==freeze['output_root_identity']==[named.st_dev,named.st_ino]
                and stat.S_IMODE(held.st_mode)==stat.S_IMODE(named.st_mode)==0o700,'held fresh F root')
    try:
        freeze_raw=reads.raw(args.freeze,1024**2);freeze=json_checked(freeze_raw,args.freeze_sha256)
        require(freeze['identity']==IDENTITY,'F identity required')
        root=Path(freeze['output_root']);st=root.lstat()
        require(root.resolve()==root and stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode)==0o700 and
                [st.st_dev,st.st_ino]==freeze['output_root_identity'] and not any(root.iterdir()),
                'fresh empty frozen F root')
        root_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        proof_raw=reads.raw(args.proof,2*1024**2);marker_raw=reads.raw(args.marker,65536)
        proof=json_checked(proof_raw,args.proof_sha256);marker=json_checked(marker_raw,args.marker_sha256)
        admit(freeze,proof,marker,args.freeze_sha256,args.marker_sha256)
        require(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and
                str(Path(sys.executable).resolve())==freeze['python_executable'] and
                list(sys.version_info[:3])==[3,12,14],'fresh pinned isolated parent')
        recheck_root()
        write_new(root/'spent.json',canonical(dict(identity=IDENTITY,spent=True,single_use=True,
            freeze_sha256=args.freeze_sha256,automatic_successor=False,engineering_only=True,
            reserved_wall_seconds=30,reserved_artifact_bytes=MAX_STORAGE,
            opaque_child_read_reserve_bytes=16*1024**2)))
        spent=True
        for name,raw in [('freeze',freeze_raw),('proof',proof_raw),('marker',marker_raw)]:
            write_new(root/'admission'/(name+'.json'),raw)
        for pin in freeze['source_pins']+freeze['runtime_pins']:reads.pin(pin)
        by_path={p['path']:p for p in freeze['source_pins']}
        load_module(freeze['observer_source_path'],'proc_custody',reads.pin(by_path[freeze['observer_source_path']]))
        supervisor=load_module(freeze['supervisor_source_path'],'seti_proc_f_supervisor',
                               reads.pin(by_path[freeze['supervisor_source_path']]))
        python=freeze['python_executable']
        (root/'processes').mkdir(mode=0o700);(root/'tmp').mkdir(mode=0o700)
        env=dict(LANG='C',LC_ALL='C',PYTHONDONTWRITEBYTECODE='1',PYTHONHASHSEED='0',TMPDIR=str(root/'tmp'),
            OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        argv=[python,'-I','-B','-S',freeze['control_source_path'],'--payload',freeze['payload_path'],
            '--payload-sha256',freeze['payload_sha256'],'--output',str(root/'control-result.json')]
        limits=dict(child_wall_seconds=10,cpu_seconds=5,address_space_bytes=128*1024**2,
            per_file_bytes=1024**2,stdout_bytes=65536,stderr_bytes=65536,
            read_reserve_bytes=16*1024**2,artifact_bytes=MAX_STORAGE,
            pin_read_budget_bytes=32*1024**2,proc_metadata_budget_bytes=16*1024**2,
            sample_interval_seconds=0.02,cleanup_seconds=2,artifact_root=str(root),
            python_path=python,python_sha256=freeze['python_sha256'])
        for name in ('guard','exec_seal','phase2'):
            limits[name+'_path']=freeze[name+'_path'];limits[name+'_sha256']=freeze[name+'_sha256']
        recheck_root();require(time.monotonic()<operation_deadline,'operation cutoff before child')
        capture=supervisor.run_leaf(argv,env,str(root),str(root/'processes/control'),limits,operation_deadline)
        result['children'].append(capture)
        require(capture['child_dispatches']==1 and capture['child_reaped'] is True and
                capture['child_exit_code']==0 and capture['guarded_leaf'] is True and capture['failure'] is None,
                'guarded control child failed')
        raw=reads.raw(root/'control-result.json',65536);metadata=json.loads(raw)
        control=validate_control(metadata,capture,freeze['payload_sha256'],python)
        result.update(control_result_sha256=sha(raw),control=control,
            status='OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION')
    except Exception as exc:
        result.update(failure_type=type(exc).__name__,failure=str(exc)[:1000])
    finally:
        if root_fd is not None:
            try:
                recheck_root()
                if spent:
                    for pin in freeze['source_pins']+freeze['runtime_pins']:reads.pin(pin)
                    result['selected_source_runtime_pins_after_match']=True
                result['artifact_inventory']=inventory(root,reads)
            except Exception as exc:
                result.update(status='FAILED_CLOSED',finalization_failure=str(exc)[:500])
            # Read/RSS evidence remains available even if a postcheck fails.
            result['root_explicit_reads_charged_bytes']=reads.charged
            try:
                pin_reads=sum(c.get('pin_read_charge_bytes',0) for c in result['children'])
                proc_reads=sum(c.get('proc_metadata_read_charge_bytes',0) for c in result['children'])
                stream_reads=sum(sum(v.get('bytes',0) for v in c.get('output',{}).values()) for c in result['children'])
                total=reads.charged+pin_reads+proc_reads+stream_reads
                result.update(root_explicit_reads_charged_bytes=reads.charged,
                    supervisor_explicit_pin_reads_charged_bytes=pin_reads,
                    supervisor_proc_metadata_reads_charged_bytes=proc_reads,
                    retained_leaf_stream_reads_charged_bytes=stream_reads,
                    explicit_parent_read_charged_bytes=total,
                    joined_conservative_charged_bytes=total+16*1024**2,
                    joined_read_reservation_bytes=528*1024**2,read_reservation_fully_spent_no_refund=True)
                require(total<=MAX_PARENT_READ and pin_reads<=32*1024**2 and proc_reads<=16*1024**2 and
                        stream_reads<=16*1024**2,'joined explicit parent envelope')
                peaks=[c.get('wait4_direct_child_ru_maxrss_bytes') for c in result['children']]
                complete=all(type(p) is int and p>=0 for p in peaks)
                result['child_peak_custody_complete']=complete
                parent_peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
                result['parent_kernel_highwater_before_terminal_bytes']=parent_peak
                result['conservative_joined_rss_upper_bound_before_parent_terminal_bytes']=(parent_peak+max(peaks,default=0) if complete else None)
                require(complete,'missing direct-child RSS custody')
            except Exception as exc:
                result.update(status='FAILED_CLOSED',accounting_failure=str(exc)[:500])
            result['elapsed_before_terminal_seconds']=time.monotonic()-started
            if result['elapsed_before_terminal_seconds']>=30:result.update(status='FAILED_CLOSED',finalization_failure='whole-scope deadline')
            result['limits']=freeze['limits'];result['spent_marker_written']=spent
            result['measurement_limits']=[
                'Opaque child reserve is not complete native IO measurement.',
                'Input pre/post checks are selected integrity, not continuous namespace/loader custody.',
                'Lifetime RSS sums are conservative bounds, not simultaneous tree peaks.',
                'Final stored bytes are observations, not transient storage peaks.',
                'Original scientific production gates remain pending; no spectrum/source session/trial is admitted.']
            write_new(root/'result.json',canonical(result));os.close(root_fd)
        signal.setitimer(signal.ITIMER_REAL,0)
    print(result['status'])
    return 0 if result['status'].startswith('OBSERVED_KERNEL_IO_ONLY_') else 1

def main():
    parser=argparse.ArgumentParser()
    for name in ('freeze','freeze-sha256','proof','proof-sha256','marker','marker-sha256'):
        parser.add_argument('--'+name,required=True)
    return run(parser.parse_args())
if __name__=='__main__':raise SystemExit(main())
