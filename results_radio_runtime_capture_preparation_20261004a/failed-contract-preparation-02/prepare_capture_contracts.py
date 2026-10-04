"""Preparation-only frozen contracts; this script never dispatches a capture."""
import hashlib
import json
import os
import stat
from pathlib import Path

REPO = Path('/workspace/scratch/d804553c0e89/setisearch-status-20261004')
HERE = REPO / 'results_radio_runtime_capture_preparation_20261004a'
OUTPUT = Path('/workspace/scratch/d804553c0e89/radio-runtime-metadata-capture-20261004a')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def pin(path, role=None):
    path = path.resolve(strict=True)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    assert before == after and stat.S_ISREG(before.st_mode) and before.st_nlink == 1
    mode = format(stat.S_IMODE(before.st_mode), '04o')
    assert mode in ('0644', '0755')
    value = {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw), 'mode': mode}
    if role:
        value.update(role=role, mode='100644' if mode == '0644' else '100755')
    return value

def save(path, value):
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        raise
    return raw

def main():
    preread = json.loads((HERE / 'runtime-preread-pins.json').read_bytes())
    plan = REPO / 'results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json'
    protocol = REPO / 'RADIO_RUNTIME_METADATA_CAPTURE_2026-10-04_PROTOCOL.md'
    collector = HERE / 'collector.py'
    helper = HERE / 'elf_metadata.py'
    gate = HERE / 'capture_gate.py'
    child_path = REPO / 'config/radio_runtime_metadata_capture_20261004a.collector.json'
    supervisor_path = REPO / 'config/radio_runtime_metadata_capture_20261004a.freeze.json'
    assert not list(OUTPUT.iterdir())
    info = OUTPUT.stat()
    assert (info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode)) == (27, 1572892, 0o700)
    files = [{k: row[k] for k in ('path', 'role', 'bytes', 'sha256', 'mode')}
             for row in preread['selected_files']]
    files.extend(pin(path, role) for path, role in
                 ((collector, 'code'), (helper, 'code'), (gate, 'code'), (protocol, 'input'), (plan, 'input')))
    files.sort(key=lambda row: row['path'])
    python = next(row for row in files if row['path'] == preread['python_path'])
    plan_pin = pin(plan)
    child = {
        'schema': 'radio-runtime-metadata-capture-contract-v1',
        'evidence_domain': 'metadata-capture-only',
        'capture_identity': preread['capture_identity'], 'capture_authorized': True,
        'externally_bound_publication_required': True, 'activation_required': True,
        'plan_sha256': plan_pin['sha256'], 'python_path': python['path'],
        'python_sha256': python['sha256'], 'files': files, 'imports': [], 'import_paths': [],
        'loader_paths': preread['loader_paths'], 'distributions': preread['distributions'],
        'missing_paths': preread['missing_paths'],
        'limits': {'files': 1024, 'per_file_bytes': 64*1024**2, 'read_bytes': 140*1024**2,
                   'maps_bytes': 1024**2, 'module_count': 4096, 'result_bytes': 1024**2,
                   'elf_program_headers': 1024, 'elf_dynamic_entries': 4096,
                   'elf_strings': 512, 'elf_string_bytes': 65536}}
    child_raw = save(child_path, child)
    assert len(child_raw) <= 262144
    source_paths = [collector, helper, gate, protocol, plan, child_path, HERE/'runtime-preread-pins.json']
    sources = sorted((pin(path) for path in source_paths), key=lambda row: row['path'])
    runtimes = [{k: row[k] for k in ('path', 'bytes', 'sha256')} |
                {'mode': row['filesystem_mode']} for row in preread['selected_files']]
    runtimes.sort(key=lambda row: row['path'])
    supervisor = {
        'schema': 'radio-runtime-metadata-capture-supervisor-v1',
        'capture_identity': preread['capture_identity'], 'evidence_domain': 'metadata-capture-only',
        'source_pins': sources, 'runtime_pins': runtimes,
        'python_executable': python['path'], 'python_sha256': python['sha256'],
        'collector_path': str(collector), 'collector_contract_path': str(child_path),
        'collector_contract_sha256': sha(child_raw), 'plan_path': str(plan), 'plan_sha256': plan_pin['sha256'],
        'output_root': str(OUTPUT), 'output_root_identity': {'device': 27, 'inode': 1572892, 'mode': '0700'},
        'spent_path': str(OUTPUT/'spent.json'),
        'activation_path': str(REPO/'config/radio_runtime_metadata_capture_20261004a.activate.json'),
        'limits': {'wall_seconds':60,'child_seconds':50,'reap_seconds':5,'artifact_bytes':8*1024**2,
                   'rss_bytes':512*1024**2,'read_bytes':256*1024**2,'stream_bytes':1024**2,'sample_count':1200}}
    supervisor_raw = save(supervisor_path, supervisor)
    # Execute only the modules' pure validators; no local backend or supervisor run.
    namespaces = []
    for path in (collector, gate):
        namespace = {'__name__':'_preparation_pure_validation','__file__':str(path)}
        exec(compile(path.read_bytes(), str(path), 'exec'), namespace)
        namespaces.append(namespace)
    namespaces[0]['validate_inputs'](child_raw, sha(child_raw), plan.read_bytes(), plan_pin['sha256'])
    namespaces[1]['validate_contract'](supervisor_raw, sha(supervisor_raw))
    print(json.dumps({'status':'PURE_CONTRACTS_VALIDATED_NO_CAPTURE',
        'collector_contract':{'bytes':len(child_raw),'sha256':sha(child_raw)},
        'supervisor_contract':{'bytes':len(supervisor_raw),'sha256':sha(supervisor_raw)},
        'selected_child_files':len(files),'selected_runtime_files':len(runtimes),'source_pins':len(sources),
        'known_parent_two_pass_bytes':2*sum(row['bytes'] for row in sources+runtimes),
        'parent_read_remaining_bytes':116*1024**2}, sort_keys=True))

if __name__ == '__main__':
    main()
