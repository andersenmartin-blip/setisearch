"""Read-only static prospectus; does not admit or invoke a transport or installer."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

OUT = Path('/workspace/scratch/66170938f826/bootstrap-b-inputs')
BASE = Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/python')
OLD = Path('/workspace/scratch/a5b2addacbd5/setisearch-20261005/results_radio_runtime_bootstrap_preparation_20261005a')
META = Path('/workspace/scratch/d804553c0e89/setisearch-status-20261004/results_radio_runtime_capture_preparation_20261004b')
ADAPTER = Path('/workspace/scratch/66170938f826/setisearch/results_radio_proxy_transport_integration_20261005a')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pin(path):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 64*1024**2:
            raise ValueError('sole-link bounded regular file required: ' + str(path))
        chunks = []
        left = before.st_size
        while left:
            chunk = os.read(fd, min(left, 1024**2))
            if not chunk:
                raise ValueError('short read')
            chunks.append(chunk)
            left -= len(chunk)
        if os.read(fd, 1):
            raise ValueError('growth')
        after = os.fstat(fd)
        named = path.lstat()
        keys = ('st_dev','st_ino','st_mode','st_size','st_nlink','st_mtime_ns','st_ctime_ns')
        identity = lambda st: tuple(getattr(st,k) for k in keys)
        if identity(before) != identity(after) or identity(before) != identity(named):
            raise ValueError('file changed')
        raw = b''.join(chunks)
        return {'path':str(path),'bytes':len(raw),'sha256':sha(raw),
                'mode':format(before.st_mode&0o7777,'04o'),
                'file_identity':{k:getattr(before,k) for k in keys},
                'ancestral_custody_claimed':False}, raw
    finally:
        os.close(fd)

preread_raw = (OLD/'installer-preread.json').read_bytes()
preread = json.loads(preread_raw)
runtime = []
changes = []
for old in preread['runtime_selected_files']:
    row, _ = pin(old['path'])
    runtime.append(row)
    oldmode = old.get('filesystem_mode', old['mode'][-4:])
    if any(row[k] != old[k] for k in ('path','bytes','sha256')) or row['mode'] != oldmode:
        changes.append({'old':{k:old[k] for k in ('path','bytes','sha256','mode')},'current':row})

installer = []
installer_changes = []
for old in preread['installer_source_files']:
    row, _ = pin(old['path'])
    installer.append(row)
    oldmode = old.get('filesystem_mode', old['mode'][-4:])
    if any(row[k] != old[k] for k in ('path','bytes','sha256')) or row['mode'] != oldmode:
        installer_changes.append({'old':{k:old[k] for k in ('path','bytes','sha256','mode')},'current':row})

source_paths = [ADAPTER/name for name in ('proxy_opener.py','proxy_contract.py','native_bindings.py','wheel_io.py','original-plan.json')]
source_paths += [OLD/name for name in ('prepare_installer_preread.py','build_contracts.py','bootstrap_gate.py','capture_basis.py','wheel_io.py')]
source_paths += [META/name for name in ('prepare_runtime_preread.py','elf_metadata.py','runtime-preread-pins.json')]
sources = [pin(p)[0] for p in source_paths]
certpath = os.environ['PIP_CERT']
cert, certraw = pin(certpath)
elfns = {'__name__':'static_elf_metadata_prospectus'}
elfraw = (META/'elf_metadata.py').read_bytes()
exec(compile(elfraw, str(META/'elf_metadata.py'),'exec'),elfns)
binary, binaryraw = pin(BASE/'bin/python3.12')
elf = elfns['parse_elf'](binaryraw)

native_rows = [pin(BASE/'lib/python3.12'/name)[0] for name in ('ssl.py','socket.py','selectors.py','_sysconfigdata__linux_x86_64-linux-gnu.py')]
loader_rows = [row for row in runtime if row['path'].startswith('/usr/lib/x86_64-linux-gnu/')]
env_keys = ('CODEX_PRIMARY_RUNTIME_BUNDLE_VERSION','CODEX_PRIMARY_RUNTIME_ROOT','CODEX_PRIMARY_RUNTIME_PYTHON','PIP_PROXY','PIP_CERT','SSL_CERT_FILE','SSL_CERT_DIR','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy','NO_PROXY','no_proxy')
report = {
    'schema':'radio-bootstrap-b-current-static-input-prospectus-v1',
    'status':'STATIC_METADATA_ONLY_NO_NATIVE_ADMISSION',
    'time_unix_ns':time.time_ns(),
    'operations':{'actual_connect':0,'SSLContext':0,'h5py_import':0,'installation':0,'telescope_read':0,'network_probe':0},
    'primary_python':{'sys_version':sys.version,'sys_executable':sys.executable,'binary':binary,
                      'builtin_relevant':[n for n in sys.builtin_module_names if n in ('_ssl','_socket','select','_hashlib','zlib','_bz2','_lzma','_ctypes')],
                      'elf_metadata_only':elf},
    'explicit_environment_observed_in_this_command':{k:os.environ.get(k) for k in env_keys},
    'previous_commands_observed_proxy_urls':['http://127.0.0.1:37445','http://127.0.0.1:45781'],
    'proxy_binding':{'dynamic_across_commands_observed':True,'fixed_cross_command_endpoint_proven':False,
                     'required_path':'Capture exact endpoint in one still-live command/session, publish and read back its freeze while alive, then invoke once from that same process; lifecycle/reachability remains unproven.'},
    'trust_file':cert,
    'native_python_source_files':native_rows,
    'prior_selected_runtime_comparison':{'basis_path':str(OLD/'installer-preread.json'),'basis_sha256':sha(preread_raw),
                                        'file_count':len(runtime),'bytes':sum(r['bytes'] for r in runtime),'changed_rows':changes,
                                        'cohort_reenumerated':False,'meaning':'Existing declared cohort only; this is not proof that it is dependency-complete.'},
    'prior_installer_source_comparison':{'file_count':len(installer),'bytes':sum(r['bytes'] for r in installer),'changed_rows':installer_changes,
                                        'cohort_reenumerated':False,'installer_version_from_retained_manifest':preread['pip_version_static']},
    'selected_native_loader_files':loader_rows,
    'source_helper_files':sources,
    'pending_provenance':[
        'Exact static hashes are prospective pins, not evidence of actual native socket/TLS/loader custody.',
        'This reader uses no-follow final descriptors and checks file identities but does not hold every ancestor; fresh B preparation should use predecessor Guard/read_regular for full declared ancestor custody.',
        'DT_NEEDED metadata is not observed runtime loader dependency resolution or custody; native code built into Python is covered only by binary bytes.',
        'Certificate bytes/hash/path are explicit; origin, authoritativeness, validity and actual peer chain verification are not certified.',
        'Platform proxy port changes between commands and service lifetime/routing is outside this process; exporting a captured URL alone does not prove a later listener remains alive.',
        'Resource accounting covers selected file content reads only, excluding interpreter bootstrap, filesystem metadata, kernel/provider and future TLS ciphertext IO.',
        'Actual B source/runtime/trust publication pins, fresh output root, spend marker, immutable admission readback and complete finite live resource scope are still required.'
    ],
    'scientific_authority':False,'old_spent_allocations_untouched':True,
}
out = OUT/'current-input-metadata.json'
with out.open('x') as f:
    json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'report_path':str(out),'report_sha256':sha(out.read_bytes()),'runtime_files':len(runtime),'runtime_bytes':sum(r['bytes'] for r in runtime),'runtime_changes':len(changes),'installer_files':len(installer),'installer_bytes':sum(r['bytes'] for r in installer),'installer_changes':len(installer_changes),'python_elf':elf,'proxy':os.environ['PIP_PROXY'],'cert':cert},indent=2))
