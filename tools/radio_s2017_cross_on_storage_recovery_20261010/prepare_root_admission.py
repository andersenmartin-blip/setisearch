#!/usr/bin/env python3
"""Root metadata and opaque-byte admission. Never opens scientific arrays."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time

ROOT = Path('/workspace/scratch/a8d1e29996d0')
OWNER = Path('/workspace/scratch/5bf3860dacd6')
PROJECT = ROOT / 'setisearch_fullpower'
FAMILY = 'radio_s2017_cross_on_storage_recovery_20261010'
STAGE = PROJECT / 'results' / FAMILY
CAP = 12884901888
RESERVE = 67108864

def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve() == path and not path.is_symlink()
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1048576), b''):
            h.update(block)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': h.hexdigest()}

def save(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n'); handle.flush(); os.fsync(handle.fileno())

def main():
    started = time.process_time()
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    assert list(STAGE.iterdir()) == []
    prior_stage = PROJECT / 'results/radio_s2017_cross_on_recovery_20261010'
    original_stage = PROJECT / 'results/radio_s2017_cross_on_20261010'
    prior = json.loads((prior_stage / 'ROOT_ADMISSION.json').read_bytes())
    previous_scope = json.loads((PROJECT / 'tools/radio_s2017_cross_on_recovery_20261010/scope.json').read_bytes())
    assert not (original_stage / 'measurement').exists() and not (prior_stage / 'measurement').exists()
    assert not (PROJECT / 'tools' / FAMILY / 'SCOPE_PREPARATION_STARTED.json').exists()
    failures = [pin(original_stage / 'PRE_ARRAY_STARTUP_FAILURE_EVIDENCE.json'),
                pin(prior_stage / 'PRE_ARRAY_SHARED_DISK_FAILURE_EVIDENCE.json')]
    assert failures[0]['sha256'] == 'cf07e1b1f64c4c089e38be5434ac88fb0abf58924091552ccd47099691b6bf5b'
    assert failures[1]['sha256'] == 'b2250ca4fe91ea24de14e164d13c434572147dabb07c51b6a6c905b0508c23b1'
    guards = []
    try:
        for name in previous_scope['owner_kernel_guard_paths']:
            fd = os.open(name, os.O_RDONLY)
            guards.append(fd); fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        relevant = []
        patterns = [str(OWNER / x) for x in previous_scope['owner_scientific_command_paths']]
        patterns += ['/match_saved.py', '/run_frozen_once.py']
        for directory in Path('/proc').iterdir():
            if not directory.name.isdigit() or int(directory.name) == os.getpid():
                continue
            try:
                command = (directory / 'cmdline').read_bytes().split(b'\0')
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
            arguments = [x.decode(errors='replace') for x in command if x]
            if any(arg.endswith(pattern) for arg in arguments for pattern in patterns):
                relevant.append({'PID': int(directory.name), 'command_paths': arguments[:3]})
        assert not relevant, 'Actual original science or association process active'
        checked = []; hits = []
        excluded = {PROJECT / 'results' / f for f in [
            'radio_s2017_cross_on_20261010', 'radio_s2017_cross_on_recovery_20261010', FAMILY]}
        pattern = re.compile(r'cross[ _-]?ON|saved.maxima.*mutual|mutual.*cross', re.I)
        for root in [OWNER / 'analysis', PROJECT / 'results']:
            for directory, children, files in os.walk(root):
                if Path(directory) in excluded:
                    children[:] = []; continue
                for name in files:
                    path = Path(directory) / name
                    if path.suffix.lower() not in ('.json', '.md', '.txt') or not re.search(r'SCOPE|PLAN|REGISTRY|STATUS|NEXT', name, re.I):
                        continue
                    if path.is_symlink() or path.stat().st_size > 262144:
                        continue
                    item = pin(path); checked.append(item)
                    if pattern.search(path.read_text(errors='replace')):
                        hits.append(item)
        assert not hits, 'Registry mention requires classification before admission'
        for proof in prior['durability_proofs']:
            assert pin(proof['pin']['path']) == proof['pin'] and proof['verified'] is True
        for item in prior['original_execution_and_QA_pins']:
            assert pin(item['path']) == item
        maps = [item['map_pin'] for item in previous_scope['maps']]
        assert len(maps) == 762
        for item in maps:
            assert pin(item['path']) == item
        ordered_hash = hashlib.sha256(json.dumps(maps, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert ordered_hash == prior['ordered_map_pins_sha256']
        size = 0
        for root in [ROOT, OWNER]:
            for directory, children, files in os.walk(root):
                for name in files:
                    try:
                        size += (Path(directory) / name).lstat().st_size
                    except FileNotFoundError:
                        pass
        free = os.statvfs(STAGE).f_bavail * os.statvfs(STAGE).f_frsize
        assert size + RESERVE + 134217728 <= CAP and free >= RESERVE + 134217728
        registry = {'status': 'PASS_FINITE_REGISTRY_NO_OTHER_MATCHER_BOTH_PRE_ARRAY_FAILURES_RETIRED',
                    'created_utc': timestamp, 'checked_metadata_file_pins': checked,
                    'matching_hits_outside_three_own_namespaces': hits,
                    'previous_failure_pins': failures, 'previous_scientific_array_intakes': 0,
                    'previous_families_retired_without_retry': True,
                    'relevant_active_original_science_or_matching_processes': relevant,
                    'actual_seven_owner_guards_readonly_exclusively_probed': True,
                    'scientific_arrays_opened': False,
                    'finite_scan_limits': 'JSON/MD/TXT names SCOPE|PLAN|REGISTRY|STATUS|NEXT, at most262144B, OWNER analysis plus OUR results; not an exhaustive global registry.'}
        save(STAGE / 'ROOT_FRESH_DUPLICATE_CHECK.json', registry)
        resources = {'status': 'PASS_PROSPECTIVE_12GiB_SHARED_STORAGE_ADMISSION', 'created_utc': timestamp,
                     'shared_workspace_roots': [str(ROOT), str(OWNER)], 'observed_tree_bytes': size,
                     'workspace_cap_bytes': CAP, 'output_reservation_bytes': RESERVE,
                     'extra_preparation_cushion_bytes': 134217728, 'physical_free_bytes': free,
                     'headroom_after_output_reservation_bytes': CAP - size - RESERVE,
                     'old_failed_cap_bytes': 8589934592,
                     'reason': 'Concurrent owner native170/172 raw archive and new numeric outputs grew the shared roots after exact duplicate release. The third family is still ungenerated, unfrozen and unattempted. Only its prospective disk budget changes; CPU, wall, memory, output and mathematics remain fixed.',
                     'source_HTTP_requests': 0, 'cost_DKK': 0, 'scientific_arrays_opened': False}
        save(STAGE / 'ROOT_RESOURCE_ADMISSION.json', resources)
        admission = {**prior, 'created_utc': timestamp,
                     'fresh_registry_proof_pin': pin(STAGE / 'ROOT_FRESH_DUPLICATE_CHECK.json'),
                     'root_resource_admission_pin': pin(STAGE / 'ROOT_RESOURCE_ADMISSION.json'),
                     'previous_failure_pins': failures, 'recovery_family': FAMILY,
                     'recovery_reason': resources['reason'], 'shared_workspace_cap_bytes': CAP,
                     'matching_not_previously_executed': True,
                     'maps_fresh_opaque_byte_verified': len(maps)}
        save(STAGE / 'ROOT_ADMISSION.json', admission)
        print(json.dumps({'status': admission['status'], 'admission_pin': pin(STAGE / 'ROOT_ADMISSION.json'),
                          'metadata_files_checked': len(checked), 'map_files_opaque_verified': len(maps),
                          'headroom_bytes': CAP - size - RESERVE, 'process_CPU_seconds': time.process_time() - started}))
    finally:
        for fd in guards:
            os.close(fd)

if __name__ == '__main__':
    main()
