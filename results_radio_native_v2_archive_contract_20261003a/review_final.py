#!/usr/bin/env python3
"""Independent machine review of one retained archive-only qualification.

Read selected engineering metadata and held source only. Reobserve current
copies and immutable old-spender refusals; never recreate original state.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).parent
CHECKPOINT = '53174aab9708ecb4969f952892aa25e63afe5fed'
SUITE_PIN = {'bytes': 184911, 'sha256': 'ac72adb462e29f533d5006b1fb924f6e4d5a745fb49afb395f1a69022e2ac41e'}
INPUT_PIN = {'bytes': 5329, 'sha256': '735e7ced5e69a46e084526406f188b09a83ce9060c09b1f4c4126d657ea2934d'}
PRIOR_PIN = {'bytes': 307709, 'sha256': '1c61c9bb242330010ea6576af31a7b643b9420091fcdfc0900615cb37ccf293a'}
PROVENANCE_PIN = {'bytes': 8547, 'sha256': 'aba63a04ad3bfa06477a43fb34f69e6ba88af088c0a70f0fe4cee3c962a28999'}
READ_PHASE = False
DENIED = []


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def held(path, expected=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 * 1024**2:
            raise ValueError('Bounded sole-link regular review source required')
        chunks = []
        while True:
            raw = os.read(fd, 65536)
            if not raw: break
            chunks.append(raw)
        raw = b''.join(chunks); after = os.fstat(fd)
        key = lambda info: (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        if key(before) != key(after) or key(after) != key(path.lstat()) or len(raw) != before.st_size:
            raise ValueError('Review source changed during held descriptor read')
        if expected is not None and pin(raw) != expected:
            raise ValueError('Review source differs from independently retained pin: ' + str(path))
        return raw
    finally: os.close(fd)


def audit(event, args):
    if not READ_PHASE: return
    denied = event in {'os.remove', 'os.unlink', 'os.rename', 'os.mkdir', 'os.rmdir',
        'os.link', 'os.symlink', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate',
        'os.fork', 'os.forkpty', 'os.exec', 'os.posix_spawn', 'os.system'}
    denied |= event.startswith(('subprocess.', 'socket.'))
    if event == 'open' and len(args) >= 3:
        denied |= bool(args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
    if denied:
        DENIED.append(event)
        raise RuntimeError('Read-only independent review denied ' + event)


def module(name, path, expected):
    value = types.ModuleType(name); value.__file__ = str(path)
    exec(compile(held(path, expected), str(path), 'exec'), value.__dict__)
    return value


def absence(inputs):
    original = Path(inputs['original_root']); paths = [original]
    for root in (original, ROOT):
        paths.extend(root / name for name in ('.radio-native-v2-invocation-ledger',
            '.radio-native-v2-invocation-ledger-20261002c',
            '.radio-native-v2-invocation-ledger-20261003d',
            'config/radio_native_v2_control_activation_20261003d.activate.json',
            'config/radio_native_v2_compact_control_launch_20261003d.launch.json',
            'results_radio_native_v2_compact_control_20261003d'))
    for path in paths:
        try: path.lstat()
        except FileNotFoundError: pass
        else: raise ValueError('Unavailable original/d authority unexpectedly exists')
    return {str(path): 'ABSENT' for path in paths}


def main():
    global READ_PHASE
    own_pin = pin(held(Path(__file__)))
    suite_raw = held(RESULTS / 'suite-attempt-2-summary.json', SUITE_PIN)
    suite = json.loads(suite_raw)
    inputs_raw = held(RESULTS / 'qualification-inputs.json', INPUT_PIN)
    inputs = json.loads(inputs_raw)
    prior = json.loads(held(ROOT / 'results_radio_native_v2_joint_history_20261003a/final-suite-attempt-2-summary.json', PRIOR_PIN))
    provenance = json.loads(held(RESULTS / 'review-provenance.json', PROVENANCE_PIN))
    if suite['status'] != 'PASSED' or suite['test_count'] != 635 or len(suite['test_modules']) != 24:
        raise ValueError('Exact selected complete passing suite required')
    for name in ('failures', 'errors', 'skipped', 'protected_control_invocations', 'new_spends', 'telescope_reads', 'rng_draws'):
        if type(suite[name]) is not int or suite[name] != 0: raise ValueError('Exact zero qualification counter required')
    for name in ('execution_authorized', 'scientific_execution_authorized',
            'whole_control_lifetime_qualified', 'complete_runtime_freeze_qualified'):
        if suite[name] is not False: raise ValueError('No qualification authority permitted')
    for name in ('source_snapshot_unchanged', 'qualification_inputs_unchanged', 'original_state_and_d_absence_unchanged'):
        if suite[name] is not True: raise ValueError('Required unchanged-state proof absent')
    pins = suite['source_and_test_pins']
    if len(pins) != 1190: raise ValueError('Exact complete selected source inventory required')
    observed_pins = {path: pin(held(ROOT / path, expected)) for path, expected in sorted(pins.items())}
    previous = prior['source_and_test_pins']
    added = sorted(set(pins) - set(previous)); removed = sorted(set(previous) - set(pins))
    changed = sorted(path for path in set(previous) & set(pins) if previous[path] != pins[path])
    if removed or added != [str(Path(__file__).relative_to(ROOT)).replace('review_final.py', 'qualify_archive.py'),
            'scripts/radio_native_v2_archive_storage_contract.py', 'tests/test_radio_native_v2_archive_storage_contract.py']:
        raise ValueError('Unexpected source inventory addition or removal')
    if changed != ['scripts/radio_native_v2_archival_closure.py', 'tests/test_radio_native_v2_archival_closure.py']:
        raise ValueError('Unexpected production source modification')
    guards = ['scripts/radio_native_v2_' + name + '.py' for name in (
        'historical_observation', 'historical_storage', 'invocation_spending', 'prospective_spending',
        'control_activation', 'worker_admission', 'compact_control_launch',
        'compact_eight_case_resource_fixture', 'resource_finalization')]
    environment = dict(os.environ); environment['GIT_NO_LAZY_FETCH'] = '1'
    environment['GIT_TERMINAL_PROMPT'] = '0'
    guard_rows = []
    for path in guards:
        archived = subprocess.check_output(['git', 'show', CHECKPOINT + ':' + path], cwd=ROOT, env=environment)
        current = held(ROOT / path, pins[path])
        if archived != current: raise ValueError('Production guard differs from immutable public base')
        guard_rows.append({'path': path, 'raw_pin': pin(current), 'unchanged_from_public_checkpoint': True})
    if provenance['source_checkpoint'] != CHECKPOINT or provenance['qualified_input_raw_pin'] != INPUT_PIN:
        raise ValueError('Prior independent provenance review differs from this selection')
    before = absence(inputs)
    if before != suite['absent_original_and_d_state_before'] or before != suite['absent_original_and_d_state_after']:
        raise ValueError('Current unavailable original/d state differs from selected qualification')
    sys.addaudithook(audit); READ_PHASE = True
    try:
        storage = module('radio_native_v2_historical_storage', ROOT / 'scripts/radio_native_v2_historical_storage.py', pins['scripts/radio_native_v2_historical_storage.py'])
        sys.modules['radio_native_v2_historical_storage'] = storage
        archive = module('reviewed_archive', ROOT / 'scripts/radio_native_v2_archive_storage_contract.py', pins['scripts/radio_native_v2_archive_storage_contract.py'])
        closure = module('reviewed_closure', ROOT / 'scripts/radio_native_v2_archival_closure.py', pins['scripts/radio_native_v2_archival_closure.py'])
        value = suite['archive_only_observation']; observations = value['observations']
        copies = {}; copy_count = 0; raw_bytes = 0
        for label in ('b', 'c'):
            root = Path(inputs['expected_archive_roots'][label]); copies[label] = {}
            for name, expected in inputs['expected_file_pins'][label].items():
                raw = held(root / name, expected); copies[label][name] = raw
                copy_count += 1; raw_bytes += len(raw)
            manifest = value['manifests'][label]
            observed = storage.observe_retained_scope(str(root), manifest, expected_manifest_pin=pin(storage.canonical(manifest)))
            if observed != observations[label]: raise ValueError('Current archival copy observation changed')
        joined = archive.join_archival_metadata_storage(observations,
            expected_archive_roots=inputs['expected_archive_roots'], expected_file_pins=inputs['expected_file_pins'],
            expected_observation_pins=value['retained_current_observation_pins'])
        if joined != value['joined_copy_storage']: raise ValueError('Pure archival accounting receipt differs')
        if any(item is not False for field, item in joined.items()
                if type(item) is bool and field not in ('charged_once', 'read_only', 'point_in_time_accounting_only')):
            raise ValueError('Archival accounting receipt grants authority or original custody')
        names = {'spend_record': 'public-spend-record-copy.json', 'launch_start': 'launch-start.json',
            'launch_terminal': 'launch-terminal.json', 'terminal_scope_inventory': 'public-terminal-scope-inventory.json',
            'source_preservation': 'source-preservation.json'}
        closed = closure.verify_archival_closure({name: copies['c'][file] for name, file in names.items()},
            expected_pins={name: inputs['expected_file_pins']['c'][file] for name, file in names.items()})
        if closed != value['c_archival_closure']: raise ValueError('Pure archival closure receipt differs')
        refusals = {}
        for label in ('b', 'c'):
            root = Path(inputs['expected_archive_roots'][label])
            spender = module('reviewed_old_spender_' + label, root / 'archived-spender.py', inputs['expected_file_pins'][label]['archived-spender.py'])
            receipt = json.loads(copies[label]['activation-receipt.json'])
            witness = json.loads(copies[label]['invocation-spending-witness.json'])
            kwargs = {'execution_scope': receipt['control_scope'], 'ledger_root': witness['ledger_root']}
            if label == 'c': kwargs['repository_root'] = inputs['original_root']
            try: spender.observe_spend_storage(witness, receipt, **kwargs)
            except FileNotFoundError as error:
                if error.errno != 2: raise ValueError('Unexpected unavailable original state error')
                refusals[label] = {'error_type': 'FileNotFoundError', 'errno': 2, 'original_path_component_unavailable': True}
            else: raise ValueError('Original historical journal unexpectedly admitted')
        if refusals != value['original_frozen_spender_refusals']:
            raise ValueError('Fresh old-spender refusals differ from selected observation')
        if value['current_observation_pins_are_historical_authority'] is not False or value['read_only_audit_denied_events']:
            raise ValueError('Current archival observation cannot become historical authority')
        after = absence(inputs)
        for path, expected in pins.items(): held(ROOT / path, expected)
        held(RESULTS / 'qualification-inputs.json', INPUT_PIN)
        held(RESULTS / 'suite-attempt-2-summary.json', SUITE_PIN)
        if before != after or pin(held(Path(__file__))) != own_pin:
            raise ValueError('Review source or unavailable state changed')
    finally: READ_PHASE = False
    review = {'schema': 'radio-native-v2-archive-contract-final-independent-review-v1',
        'status': 'PASS_ARCHIVE_ONLY_ORIGINAL_IDENTITY_UNAVAILABLE',
        'review_type': 'independent_machine_read_only_review', 'human_review': False,
        'selected_suite_raw_pin': SUITE_PIN, 'prior_suite_raw_pin': PRIOR_PIN,
        'prior_independent_provenance_review_disclosed': True, 'prior_provenance_review_raw_pin': PROVENANCE_PIN,
        'review_source_raw_pin': own_pin, 'qualification_inputs_raw_pin': INPUT_PIN,
        'selected_test_count': 635, 'selected_test_modules': 24,
        'selected_source_pins_rehashed_and_unchanged': len(observed_pins),
        'all_selected_source_and_test_pins': observed_pins,
        'source_inventory_added_paths': added, 'source_inventory_removed_paths': removed,
        'source_inventory_changed_paths': changed, 'public_base_unchanged_production_guards': guard_rows,
        'metadata_copy_files_rehashed_and_reobserved': copy_count, 'metadata_copy_raw_bytes': raw_bytes,
        'current_copy_storage_logical_bytes': joined['logical_bytes'], 'current_copy_storage_allocated_bytes': joined['allocated_bytes'],
        'current_copy_storage_entry_count': joined['entry_count'], 'current_copy_join_receipt_recomputed_exactly': True,
        'c_archival_closure_receipt_recomputed_exactly': True, 'original_frozen_spender_refusals_reobserved': refusals,
        'absent_original_and_d_state_before': before, 'absent_original_and_d_state_after': after,
        'read_only_audit_denied_events': DENIED, 'original_witnesses_rebound': False, 'original_journals_recreated': False,
        'original_identity_continuity_proved': False, 'complete_runtime_freeze_qualified': False,
        'whole_control_lifetime_qualified': False, 'storage_join_eligible': False, 'activation_authorized': False,
        'execution_authorized': False, 'retry_authorized': False, 'scientific_execution_authorized': False,
        'telescope_read_authorized': False, 'protected_control_invocations': 0, 'new_spends': 0, 'telescope_reads': 0}
    raw = canonical(review)
    with (RESULTS / 'review-final-local.json').open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'status': review['status'], 'raw_pin': pin(raw), 'sources': len(observed_pins),
        'copies': copy_count, 'current_copy_storage_entry_count': joined['entry_count']}))


if __name__ == '__main__': main()
