"""One prospective offline package installation and native metadata observation.

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

IDENTITY = 'radio-offline-runtime-materialization-20261005c'
SCHEMA = 'radio-offline-runtime-materialization-freeze-v1'
MAX_PARENT_READ = 3 * 1024**3
MAX_GATE_READ = 624 * 1024**2
MAX_STORAGE = 1536 * 1024**2

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

def admit(freeze, proof, marker, freeze_hash, marker_hash):
    require(freeze['schema'] == SCHEMA and freeze['identity'] == IDENTITY and
            freeze['single_use'] is True and freeze['automatic_successor'] is False and
            freeze['engineering_only'] is True and freeze['network'] is False and
            freeze['hdf5_dataset_access'] is False and freeze['scientific_authority'] is False,
            'distinct engineering scope required')
    require(marker['schema'] == 'radio-offline-runtime-materialization-activation-v1' and
            marker['identity'] == IDENTITY and marker['freeze_sha256'] == freeze_hash and
            marker['single_use'] is True and marker['automatic_successor'] is False,
            'activation marker scope')
    require(proof['schema'] == 'radio-offline-runtime-materialization-publication-proof-v1' and
            proof['repository'] == 'andersenmartin-blip/setisearch' and
            proof['branch'] == 'm43-support-qualification' and
            proof['preparation_commit'] == marker['prepared_commit'] and
            proof['preparation_tree'] == marker['prepared_tree'] and
            isinstance(proof['activation_commit'],str) and len(proof['activation_commit']) == 40 and
            proof['marker_sha256'] == marker_hash and
            proof['sole_parent'] == marker['prepared_commit'] and
            proof['changed_paths'] == [freeze['marker_repository_path']] and
            proof['full_preparation_readback_exact'] is True and
            proof['marker_readback_exact'] is True and
            proof['source_readbacks'] == freeze['published_sources'], 'immutable publication proof')
    require(freeze['limits'] == dict(wall_seconds=300, operation_seconds=270,
            child_wall_seconds=120, child_cpu_seconds=100, parent_address_space_bytes=512*1024**2,
            child_address_space_bytes=512*1024**2, artifact_bytes=MAX_STORAGE,
            parent_read_bytes=MAX_PARENT_READ, child_read_reserve_bytes=1024**3,
            joined_read_bytes=4*1024**3, stream_bytes=4*1024**2,
            root_explicit_read_bytes=MAX_GATE_READ,installer_explicit_read_bytes=2304*1024**2,
            supervisor_explicit_pin_read_bytes=64*1024**2,
            supervisor_explicit_proc_read_bytes=64*1024**2,misc_stream_read_bytes=16*1024**2,
            child_sample_interval_seconds=0.02, child_cleanup_seconds=10,
            file_bytes=128*1024**2, file_count=20000, directory_count=4096,
            child_dispatches=2, terminal_reserve_bytes=8*1024**2), 'finite frozen envelope')

def load_module(path, name, raw):
    module = types.ModuleType(name)
    module.__file__ = path
    sys.modules[name] = module
    exec(compile(raw,path,'exec'),module.__dict__)
    return module

def inventory(root, reads, cap=MAX_STORAGE):
    entries = []
    logical = allocated = directories = 0
    for directory, names, files in os.walk(root, followlinks=False):
        directories += 1
        require(directories <= 4096 and not Path(directory).is_symlink(), 'directory inventory cap/kind')
        directory_stat=Path(directory).stat(follow_symlinks=False)
        logical += directory_stat.st_size
        allocated += directory_stat.st_blocks*512
        require(max(logical,allocated) <= cap, 'directory storage allocation cap')
        for name in names:
            require(not (Path(directory)/name).is_symlink(), 'symlink directory refused')
        for name in sorted(files):
            path = Path(directory)/name
            st = path.lstat()
            require(stat.S_ISREG(st.st_mode) and st.st_size <= 128*1024**2, 'regular artifact file cap')
            logical += st.st_size
            allocated += st.st_blocks*512
            require(max(logical,allocated) <= cap and len(entries) < 20000, 'artifact storage/file count cap')
            raw = reads.raw(path)
            entries.append(dict(path=path.relative_to(root).as_posix(),bytes=len(raw),
                                sha256=sha(raw),mode=stat.S_IMODE(st.st_mode),allocated_bytes=st.st_blocks*512))
    return dict(entries=entries,files=len(entries),directories=directories,
                logical_bytes=logical,allocated_bytes=allocated,
                final_inventory_not_transient_storage_peak=True)

def run(args):
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(300,300))
    resource.setrlimit(resource.RLIMIT_FSIZE,(128*1024**2,128*1024**2))
    deadline = started + 300
    operation_deadline = started + 270
    def expired(signum, frame):
        raise Refusal('whole-scope deadline')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL,300)
    reads = Reads()
    freeze_raw = reads.raw(args.freeze, 1024**2)
    proof_raw = reads.raw(args.proof, 2*1024**2)
    marker_raw = reads.raw(args.marker, 65536)
    freeze = json_checked(freeze_raw, args.freeze_sha256)
    proof = json_checked(proof_raw, args.proof_sha256)
    marker = json_checked(marker_raw, args.marker_sha256)
    admit(freeze, proof, marker, args.freeze_sha256, args.marker_sha256)
    require(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode,
            'fresh isolated parent required')
    require(str(Path(sys.executable).resolve()) == freeze['python_executable'] and
            list(sys.version_info[:3]) == [3,12,14], 'actual current interpreter required')
    root = Path(freeze['output_root'])
    st = root.stat(follow_symlinks=False)
    require(stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode) == 0o700 and
            [st.st_dev,st.st_ino] == freeze['output_root_identity'] and not list(root.iterdir()),
            'fresh frozen owned root required')
    # Source/runtime admission is before scope mutations or child dispatch.
    for pin in freeze['source_pins'] + freeze['runtime_pins']:
        reads.pin(pin)
    installer_raw = reads.pin(freeze['installer_plan_pin'])
    installer_plan = json.loads(installer_raw)
    require(sha(installer_raw) == freeze['installer_plan_sha256'] and
            installer_plan['output_root'] == str(root/'installer'), 'installer input binding')
    write_new(root/'spent.json', canonical(dict(identity=IDENTITY,spent=True,single_use=True,
        freeze_sha256=args.freeze_sha256,automatic_successor=False,engineering_only=True,
        reserved_wall_seconds=300,reserved_artifact_bytes=MAX_STORAGE,child_read_reserve_bytes=1024**3)))
    root_fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    def recheck_root():
        held=os.fstat(root_fd)
        named=root.stat(follow_symlinks=False)
        require([held.st_dev,held.st_ino] == freeze['output_root_identity'] == [named.st_dev,named.st_ino]
                and stat.S_IMODE(held.st_mode)==stat.S_IMODE(named.st_mode)==0o700,
                'held frozen output root mismatch')
    result = dict(schema='radio-offline-runtime-materialization-result-v1',identity=IDENTITY,
        status='FAILED_CLOSED',runtime_qualified=False,scientific_authority=False,
        network_requests=0,hdf5_dataset_reads=0,automatic_successor=False,children=[],
        full_native_io_custody_qualified=False,full_scientific_closure_qualified=False)
    installer = None
    try:
        write_new(root/'admission/freeze.json',freeze_raw)
        write_new(root/'admission/proof.json',proof_raw)
        write_new(root/'admission/marker.json',marker_raw)
        source_by_path={pin['path']:pin for pin in freeze['source_pins']}
        installer = load_module(freeze['installer_source_path'],'seti_offline_installer',
                               reads.pin(source_by_path[freeze['installer_source_path']]))
        supervisor = load_module(freeze['supervisor_source_path'],'seti_leaf_supervisor',
                                reads.pin(source_by_path[freeze['supervisor_source_path']]))
        recheck_root()
        prepared = installer.prepare(installer_raw,freeze['installer_plan_sha256'],root/'installer',
                                     absolute_operation_deadline=operation_deadline)
        result['installer_parent_read_charged_bytes'] = prepared.get('parent_read_charged_bytes',0)
        require(prepared['status'] == 'OFFLINE_INSTALL_PREPARED_NOT_EXECUTED', 'static installer preparation failed')
        (root/'processes').mkdir(mode=0o700)
        child_limits = dict(child_wall_seconds=120,cpu_seconds=100,address_space_bytes=512*1024**2,
            per_file_bytes=128*1024**2,stdout_bytes=2*1024**2,stderr_bytes=2*1024**2,
            read_reserve_bytes=512*1024**2,pin_read_budget_bytes=32*1024**2,artifact_bytes=MAX_STORAGE,
            proc_metadata_budget_bytes=32*1024**2,
            sample_interval_seconds=0.02,cleanup_seconds=10)
        child_limits.update(guard_path=freeze['guard_path'],guard_sha256=freeze['guard_sha256'],
            exec_seal_path=freeze['exec_seal_path'],exec_seal_sha256=freeze['exec_seal_sha256'],
            phase2_path=freeze['phase2_path'],phase2_sha256=freeze['phase2_sha256'],
            python_path=freeze['python_executable'],python_sha256=freeze['python_sha256'],
            artifact_root=str(root))
        install = supervisor.run_leaf(prepared['pinned_python_argv'],prepared['child_env'],str(root/'installer'),
                                      str(root/'processes/install'),child_limits,operation_deadline)
        result['children'].append(install)
        installed = installer.verify_installed(prepared,install,absolute_operation_deadline=operation_deadline)
        write_new(root/'installed-byte-evidence.json',canonical(installed))
        venv = root/'installer/venv'
        collector_output = root/'native-metadata.json'
        env = dict(prepared['child_env'],OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',
                   MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',HDF5_PLUGIN_PRELOAD='::',
                   HDF5_PLUGIN_PATH=str(venv/'lib/python3.12/site-packages/hdf5plugin/plugins'))
        argv = [str(venv/'bin/python'),'-I','-B',freeze['collector_source_path'],
                '--activate-native-metadata','--output',str(collector_output),
                '--filter-input',freeze['filter_input_path'],'--venv-root',str(venv)]
        child_limits['python_path'] = str(venv/'bin/python')
        capture = supervisor.run_leaf(argv,env,str(root/'installer'),str(root/'processes/capture'),
                                      child_limits,operation_deadline)
        result['children'].append(capture)
        require(capture['child_exit_code'] == 0 and capture['child_reaped'] is True and
                capture['guarded_leaf'] is True and capture['failure'] is None, 'native metadata child failed')
        metadata_raw = reads.raw(collector_output,8*1024**2)
        metadata = json.loads(metadata_raw)
        require(metadata['status'] == 'COLLECTED_IDENTITY_INPUTS_ONLY' and
                metadata['versions']['numpy'] == '2.3.5' and
                metadata['versions']['h5py'] == '3.16.0' and
                metadata['versions']['hdf5plugin_distribution'] == '7.1.0' and
                metadata['versions']['hdf5_runtime'] == '2.0.0', 'native cohort identities')
        result['metadata_sha256'] = sha(metadata_raw)
        result['runtime_identity'] = metadata['versions']
        result['installed_original_members'] = installed['verified_original_members']
        result['installer_parent_read_charged_bytes'] = installed['parent_read_charged_bytes']
        result['status'] = 'MATERIALIZED_OBSERVED_METADATA_ONLY_PENDING_RUNTIME_QUALIFICATION'
    except Exception as exc:
        result['failure_type'] = type(exc).__name__
        result['failure'] = str(exc)[:1000] if isinstance(exc, (Refusal,ValueError,RuntimeError)) else type(exc).__name__
    finally:
        try:
            recheck_root()
            for pin in freeze['source_pins'] + freeze['runtime_pins']:
                reads.pin(pin)
            result['selected_source_runtime_pins_after_match'] = True
            result['artifact_inventory'] = inventory(root,reads)
            result['artifact_inventory']['excludes_terminal_result_file'] = 'result.json'
            installed_reads = result.get('installer_parent_read_charged_bytes',0)
            if 'prepared' in locals():
                installed_reads=max(installed_reads,prepared.get('verification_parent_read_charged_bytes',0))
            supervisor_reads=sum(c.get('pin_read_charge_bytes',0) for c in result['children'])
            proc_reads=sum(c.get('proc_metadata_read_charge_bytes',0) for c in result['children'])
            stream_reads=sum(sum(o.get('bytes',0) for o in c.get('output',{}).values())
                             for c in result['children'])
            result['explicit_parent_read_charged_bytes'] = reads.charged + installed_reads + supervisor_reads + proc_reads + stream_reads
            result['root_explicit_reads_charged_bytes']=reads.charged
            result['installer_explicit_reads_charged_bytes']=installed_reads
            result['supervisor_explicit_pin_reads_charged_bytes']=supervisor_reads
            result['supervisor_proc_metadata_reads_charged_bytes']=proc_reads
            result['retained_leaf_stream_reads_charged_bytes']=stream_reads
            result['joined_conservative_read_reservation_bytes'] = 4*1024**3
            result['read_reservation_fully_spent_no_refund'] = True
            result['opaque_child_read_reserved_bytes_per_eligible_leaf'] = 512*1024**2
            require(result['explicit_parent_read_charged_bytes'] <= MAX_PARENT_READ, 'joined explicit parent read ceiling')
            result['parent_kernel_highwater_before_terminal_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            peaks = [c.get('wait4_direct_child_ru_maxrss_bytes') for c in result['children']]
            complete = all(type(p) is int and p >= 0 for p in peaks)
            result['child_peak_custody_complete'] = complete
            result['conservative_joined_rss_upper_bound_before_parent_terminal_bytes'] = (
                result['parent_kernel_highwater_before_terminal_bytes'] + max(peaks,default=0)
                if complete else None)
            if not complete:
                result['status'] = 'FAILED_CLOSED'
                result['missing_child_peak_custody'] = True
            result['joined_rss_is_conservative_upper_bound_not_measured_simultaneous_peak'] = True
        except Exception as exc:
            result['status'] = 'FAILED_CLOSED'
            result['finalization_failure'] = str(exc)[:300]
        result['elapsed_whole_scope_seconds'] = time.monotonic()-started
        if result['elapsed_whole_scope_seconds'] >= 300:
            result['status'] = 'FAILED_CLOSED'
            result['finalization_failure'] = 'whole-scope deadline exceeded'
        result['limits'] = freeze['limits']
        result['measurement_limits'] = [
            'Opaque child read reserve is fully charged; loader/page-fault/provider bytes are not certified.',
            'Kernel wait4 supplies direct-leaf lifetime RSS; joined RSS is a conservative upper bound.',
            'Final storage inventory does not measure transient storage peak.',
            'Selected native dependency identities and loader edges remain observations.',
            'All eleven original scientific fields remain pending; no source session is activated.']
        write_new(root/'result.json',canonical(result))
        os.close(root_fd)
        signal.setitimer(signal.ITIMER_REAL,0)
    print(result['status'])
    return 0 if result['status'].startswith('MATERIALIZED_') else 1

def main():
    parser=argparse.ArgumentParser()
    for name in ('freeze','freeze-sha256','proof','proof-sha256','marker','marker-sha256'):
        parser.add_argument('--'+name,required=True)
    return run(parser.parse_args())

if __name__ == '__main__':
    raise SystemExit(main())
