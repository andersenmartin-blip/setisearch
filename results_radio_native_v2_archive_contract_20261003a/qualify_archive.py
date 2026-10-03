#!/usr/bin/env python3
"""Qualify archived metadata copies, never replace unavailable original journals.

Use a separate engineering-only receipt. Production history admission, activation,
spending, and the original witnesses remain unchanged. All outputs are exclusive.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = Path(__file__).parent
PRIOR = ROOT / 'results_radio_native_v2_joint_history_20261003a/verify_checkpoint.py'
PRIOR_PIN = {'bytes': 11284, 'sha256': 'ee79bc692e9de7bb174955332065a64250f2be468a5a8e028b9d2e44fa5744c7'}
ORIGINAL = '/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002'
INPUT_PIN = {'bytes': 5329, 'sha256': '735e7ced5e69a46e084526406f188b09a83ce9060c09b1f4c4126d657ea2934d'}
SOURCE_CHECKPOINT = '53174aab9708ecb4969f952892aa25e63afe5fed'
READ_PHASE = False
DENIED = []


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def checked_inputs(launcher):
    # These literals are independently retained from the public Git recovery and
    # separate provenance review; current observations cannot choose their pins.
    _, raw = launcher.read_pinned(RESULTS / 'qualification-inputs.json',
        expected=INPUT_PIN, maximum=2 * 1024**2, retain=True)
    value = json.loads(raw)
    if (canonical(value) != raw or value['source_checkpoint'] != SOURCE_CHECKPOINT
            or value['original_root'] != ORIGINAL
            or any(value[name] is not False for name in ('original_private_journals_recreated',
                'original_scope_recreated', 'activation_authorized'))):
        raise ValueError('Exact independently retained non-authorizing archive inputs required')
    for label in ('b', 'c'):
        provenance = value['immutable_source_provenance'][label]
        expected = value['expected_file_pins'][label]
        if set(provenance) != set(expected): raise ValueError('Exact immutable source provenance required')
        for name, record in provenance.items():
            _, source = launcher.read_pinned(ROOT / record['path'], expected=expected[name],
                maximum=2 * 1024**2, retain=True)
            blob = hashlib.sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()
            if blob != record['git_blob_sha']:
                raise ValueError('Archived source differs from independently recovered Git blob')
    return value, raw


def write(name, value):
    with (RESULTS / name).open('xb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())


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
        raise RuntimeError('Read-only archival observation denied ' + event)


def absence_state():
    # An absent ORIGINAL is a blocker, never an invitation to recreate it.
    paths = [Path(ORIGINAL)]
    for root in (Path(ORIGINAL), ROOT):
        paths.extend(root / name for name in ('.radio-native-v2-invocation-ledger',
            '.radio-native-v2-invocation-ledger-20261002c',
            '.radio-native-v2-invocation-ledger-20261003d',
            'config/radio_native_v2_control_activation_20261003d.activate.json',
            'config/radio_native_v2_compact_control_launch_20261003d.launch.json',
            'results_radio_native_v2_compact_control_20261003d'))
    result = {}
    for path in paths:
        try: path.lstat()
        except FileNotFoundError: result[str(path)] = 'ABSENT'
        else: raise ValueError('This archive-only qualification requires absent original/d authority: ' + str(path))
    return result


def bootstrap():
    # Reuse held import/environment primitives, not the old protected-state check.
    raw = PRIOR.read_bytes()
    if pin(raw) != PRIOR_PIN: raise ValueError('Prior reviewed bootstrap source changed')
    prior = types.ModuleType('archive_prior_preparation'); prior.__file__ = str(PRIOR)
    exec(compile(raw, str(PRIOR), 'exec'), prior.__dict__)
    helper, launcher, modules, paths, initial, proof, imports = prior.setup()
    paths.add(str(Path(__file__).relative_to(ROOT)))
    initial = helper.current_source_pins(launcher, paths)
    if initial[str(PRIOR.relative_to(ROOT))] != PRIOR_PIN:
        raise ValueError('Executed prior helper differs from independently pinned source')
    return prior, helper, launcher, (*modules, 'test_radio_native_v2_archive_storage_contract'), paths, initial, proof, imports


def manifest(storage, root, expected):
    rows = []
    for path in [root, *sorted(root.rglob('*'))]:
        info = path.lstat()
        relative = '.' if path == root else str(path.relative_to(root))
        if stat.S_ISDIR(info.st_mode): kind = 'directory'
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1: kind = 'file'
        else: raise ValueError('Ordinary sole-link archival copy required')
        row = {'path': relative, 'kind': kind, 'metadata': storage._metadata(info)}
        if kind == 'file': row['raw_pin'] = expected[relative]
        rows.append(row)
    return {'schema': storage.MANIFEST_SCHEMA, 'role': 'historical_scope',
        'scope': str(root), 'rows': sorted(rows, key=lambda row: row['path'])}


def observe(launcher, inputs, initial):
    global READ_PHASE
    storage = importlib.import_module('radio_native_v2_historical_storage')
    contract = importlib.import_module('radio_native_v2_archive_storage_contract')
    closure = importlib.import_module('radio_native_v2_archival_closure')
    observations = {}; manifests = {}; observation_pins = {}
    READ_PHASE = True
    try:
        for label in ('b', 'c'):
            root = Path(inputs['expected_archive_roots'][label])
            expected = inputs['expected_file_pins'][label]
            value = manifest(storage, root, expected)
            raw = storage.canonical(value)
            observed = storage.observe_retained_scope(str(root), value, expected_manifest_pin=pin(raw))
            manifests[label] = value; observations[label] = observed
            observation_pins[label] = pin(storage.canonical(observed))
        joined = contract.join_archival_metadata_storage(observations,
            expected_archive_roots=inputs['expected_archive_roots'],
            expected_file_pins=inputs['expected_file_pins'],
            expected_observation_pins=observation_pins)
        croot = Path(inputs['expected_archive_roots']['c'])
        names = {'spend_record': 'public-spend-record-copy.json',
            'launch_start': 'launch-start.json', 'launch_terminal': 'launch-terminal.json',
            'terminal_scope_inventory': 'public-terminal-scope-inventory.json',
            'source_preservation': 'source-preservation.json'}
        files = {label: (croot / name).read_bytes() for label, name in names.items()}
        closure_result = closure.verify_archival_closure(files,
            expected_pins={label: inputs['expected_file_pins']['c'][name] for label, name in names.items()})
        failures = {}
        for label in ('b', 'c'):
            root = Path(inputs['expected_archive_roots'][label])
            source = root / 'archived-spender.py'
            raw = source.read_bytes()
            if pin(raw) != inputs['expected_file_pins'][label]['archived-spender.py']:
                raise ValueError('Immutable historical spender copy differs')
            module = types.ModuleType('held_original_' + label); module.__file__ = str(source)
            exec(compile(raw, str(source), 'exec'), module.__dict__)
            receipt = json.loads((root / 'activation-receipt.json').read_bytes())
            witness = json.loads((root / 'invocation-spending-witness.json').read_bytes())
            kwargs = {'execution_scope': receipt['control_scope'], 'ledger_root': witness['ledger_root']}
            if label == 'c': kwargs['repository_root'] = ORIGINAL
            try: module.observe_spend_storage(witness, receipt, **kwargs)
            except FileNotFoundError as error:
                failures[label] = {'error_type': type(error).__name__, 'errno': error.errno,
                    'original_path_component_unavailable': True}
            else: raise ValueError('Missing original journal unexpectedly observed')
        if set(failures) != {'b', 'c'}: raise ValueError('Both original frozen spenders must refuse unavailable state')
        # Bracket the entire read-only phase with freshly reobserved exact copies.
        for label in ('b', 'c'):
            value = manifests[label]
            after = storage.observe_retained_scope(value['scope'], value,
                expected_manifest_pin=pin(storage.canonical(value)))
            if after != observations[label]: raise ValueError('Current archival copies changed across observation')
        return {'schema': 'radio-native-v2-archive-only-observation-qualification-v1',
            'status': 'ARCHIVE_METADATA_VERIFIED_ORIGINAL_HISTORY_UNAVAILABLE',
            'joined_copy_storage': joined, 'c_archival_closure': closure_result,
            'original_frozen_spender_refusals': failures,
            'manifests': manifests, 'observations': observations,
            'retained_current_observation_pins': observation_pins,
            'current_observation_pins_are_historical_authority': False,
            'read_only_audit_denied_events': list(DENIED),
            'original_witnesses_rebound': False, 'original_journals_recreated': False,
            'production_history_adapter_changed': False,
            'protected_control_invocations': 0, 'new_spends': 0, 'telescope_reads': 0,
            'scientific_execution_authorized': False, 'activation_authorized': False,
            'complete_runtime_freeze_qualified': False}
    finally: READ_PHASE = False


def run(attempt):
    started = time.monotonic()
    prior, helper, launcher, modules, paths, initial, proof, imports = bootstrap()
    inputs, inputs_raw = checked_inputs(launcher)
    before = absence_state()
    class TestFinder:
        def find_spec(self, fullname, path=None, target=None):
            if fullname == 'tests':
                spec = importlib.util.spec_from_loader(fullname, loader=None, is_package=True)
                spec.submodule_search_locations = [str(ROOT / 'tests')]; return spec
            relative = (fullname.replace('.', '/') + '.py' if fullname.startswith('tests.')
                else 'tests/' + fullname + '.py' if fullname.startswith('test_') else None)
            if relative is None: return None
            if relative not in initial: raise ImportError('Unpinned test source: ' + fullname)
            loader = launcher._PinnedSourceLoader(str(ROOT / relative), initial[relative]['sha256'])
            return importlib.util.spec_from_loader(fullname, loader, is_package=False)
    finder = TestFinder(); sys.meta_path.insert(0, finder)
    os.environ['RUN_RUNTIME_CUSTODY_HOST_AUDIT'] = '1'
    try:
        suite = unittest.TestSuite()
        for name in modules:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module('tests.' + name)))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        os.environ.pop('RUN_RUNTIME_CUSTODY_HOST_AUDIT', None); sys.meta_path.remove(finder)
    sys.addaudithook(audit)
    observation = observe(launcher, inputs, initial)
    after = absence_state()
    _, inputs_after = checked_inputs(launcher)
    if inputs_after != inputs_raw:
        raise ValueError('Independently retained archive inputs changed during qualification')
    final = helper.current_source_pins(launcher, paths)
    passed = result.wasSuccessful() and not result.skipped and initial == final and before == after
    summary = {'schema': 'radio-native-v2-archive-contract-preparation-suite-v1',
        'attempt': attempt, 'status': 'PASSED' if passed else 'FAILED',
        'test_count': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped), 'seconds': round(time.monotonic() - started, 6),
        'test_modules': list(modules), 'source_snapshot_unchanged': initial == final,
        'source_and_test_pins': final, 'test_bootstrap': proof, 'test_import_policy': imports,
        'qualification_inputs_raw_pin': pin(inputs_raw), 'absent_original_and_d_state_before': before,
        'qualification_inputs_unchanged': inputs_after == inputs_raw,
        'public_archive_provenance_separately_verified_at_checkpoint': SOURCE_CHECKPOINT,
        'absent_original_and_d_state_after': after, 'original_state_and_d_absence_unchanged': before == after,
        'archive_only_observation': observation,
        'protected_control_invocations': 0, 'new_spends': 0, 'telescope_reads': 0, 'rng_draws': 0,
        'execution_authorized': False, 'scientific_execution_authorized': False,
        'whole_control_lifetime_qualified': False, 'complete_runtime_freeze_qualified': False}
    write(f'suite-attempt-{attempt}-summary.json', summary)
    print(json.dumps({key: summary[key] for key in ('status', 'test_count', 'failures', 'errors', 'skipped', 'seconds')}))
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--attempt', type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.attempt <= 1_000_000: raise ValueError('Fresh bounded attempt required')
    if (RESULTS / f'suite-attempt-{args.attempt}-summary.json').exists():
        raise FileExistsError('Existing qualification attempts are immutable')
    raise SystemExit(run(args.attempt))
