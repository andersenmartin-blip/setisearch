"""Prepare new F sources from immutable E; never executes a child."""
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'runtime-metadata-preparation-E'

def main():
    gate=(OLD/'runtime_gate.py').read_text()
    gate=gate.replace('One distinct capture of installed native package metadata.','One distinct harmless direct-child kernel IO control.')
    gate=gate.replace('radio-runtime-metadata-capture','radio-proc-io-control').replace('20261005e','20261006f')
    gate=gate.replace('MAX_PARENT_READ = 1536 * 1024**2','MAX_PARENT_READ = 512 * 1024**2')
    gate=gate.replace('MAX_GATE_READ = 1408 * 1024**2','MAX_GATE_READ = 448 * 1024**2')
    gate=gate.replace('MAX_STORAGE = 64 * 1024**2','MAX_STORAGE = 16 * 1024**2')
    begin=gate.index('LIMITS = dict(');end=gate.index('\ndef admit(',begin)
    gate=gate[:begin]+'''LIMITS = dict(wall_seconds=30,operation_seconds=20,child_wall_seconds=10,child_cpu_seconds=5,
    parent_address_space_bytes=256*1024**2,child_address_space_bytes=128*1024**2,
    parent_read_bytes=MAX_PARENT_READ,root_explicit_read_bytes=MAX_GATE_READ,
    supervisor_pin_read_bytes=32*1024**2,supervisor_proc_read_bytes=16*1024**2,
    misc_stream_read_bytes=16*1024**2,opaque_child_read_reserve_bytes=16*1024**2,
    joined_read_bytes=528*1024**2,artifact_bytes=MAX_STORAGE,terminal_reserve_bytes=1024**2,
    output_file_bytes=1024**2,input_file_bytes=128*1024**2,stdout_bytes=65536,
    stderr_bytes=65536,file_count=2000,directory_count=128,child_dispatches=1,
    child_cleanup_seconds=2,child_sample_interval_seconds=0.02)
''' +gate[end:]
    begin=gate.index('    executable_paths=');end=gate.index('\ndef inventory(',begin)
    gate=gate[:begin]+'''    executable_paths={freeze[k] for k in ('gate_source_path','launcher_source_path','supervisor_source_path',
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
''' +gate[end:]
    gate=re.sub(r'(?<!\d)8\*1024\*\*2','1024**2',gate)
    gate=gate.replace('(512*1024**2,512*1024**2)','(256*1024**2,256*1024**2)')
    gate=gate.replace('(180,180)','(30,30)').replace('ITIMER_REAL,180','ITIMER_REAL,30')
    gate=gate.replace('started+150','started+20').replace('reserved_wall_seconds=180','reserved_wall_seconds=30')
    gate=gate.replace('opaque_child_read_reserve_bytes=512*1024**2','opaque_child_read_reserve_bytes=16*1024**2')
    gate=gate.replace(' E ',' F ').replace('E identity','F identity').replace('fresh E root','fresh F root')
    begin=gate.index('        manifest_raw=');end=gate.index('    except Exception as exc:',begin)
    gate=gate[:begin]+'''        by_path={p['path']:p for p in freeze['source_pins']}
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
''' +gate[end:]
    gate=gate.replace("                    if manifest is not None:result['installed_inputs_after']=check_installed_tree(manifest,reads)\n",'')
    gate=gate.replace('total+512*1024**2','total+16*1024**2').replace('joined_read_reservation_bytes=2*1024**3','joined_read_reservation_bytes=528*1024**2')
    gate=gate.replace('proc_reads<=32*1024**2','proc_reads<=16*1024**2').replace('stream_reads<=64*1024**2','stream_reads<=16*1024**2')
    gate=gate.replace("']>=180:","']>=30:").replace("OBSERVED_METADATA_ONLY_","OBSERVED_KERNEL_IO_ONLY_")
    gate=gate.replace('All eleven scientific fields remain pending; no spectrum/source session/trial is admitted.',
        'Original scientific production gates remain pending; no spectrum/source session/trial is admitted.')
    (HERE/'runtime_gate.py').write_text(gate)
    launcher=(OLD/'launch_scope.py').read_text().replace('radio-runtime-metadata-capture','radio-proc-io-control')
    launcher=launcher.replace('(512*1024**2,512*1024**2)','(256*1024**2,256*1024**2)')
    launcher=launcher.replace('(180,180)','(30,30)')
    launcher=re.sub(r'(?<!\d)8\*1024\*\*2','1024**2',launcher)
    launcher=launcher.replace('>=180','>=30').replace('>=190','>=40').replace('completed<180','completed<30')
    launcher=re.sub(r'(?<!\d)4\*1024\*\*2','128*1024',launcher)
    launcher=launcher.replace('64*1024**2','16*1024**2')
    launcher=launcher.replace('OBSERVED_METADATA_ONLY_','OBSERVED_KERNEL_IO_ONLY_')
    (HERE/'launch_scope.py').write_text(launcher)
    print('new F gate/launcher sources written; no dispatch')
if __name__=='__main__':main()
