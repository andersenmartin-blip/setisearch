"""Fresh local engineering session/import/receiver join, without scientific execution.

Reuses externally pinned attempt03 synthetic HDF5 bytes. No new random draw or
independent row oracle is claimed. Existing project acquisition/source/receiver
modules are unchanged; only transport.open_response is simulated.
"""
import argparse
import ast
import copy
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
import sys
import time
import traceback
from unittest.mock import patch

BASE = Path('/workspace/scratch/fb4056c33767')
ROOT = BASE / 'frozen-project'
RUNTIME = Path('/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a/venv')
PROBE_SHA = '3ef05fd6c5a065b244341256f7afe50e117c753246122100925af6b702e57e0b'
BRIDGE_SHA = '72a8b4fbfdc3aad809b079523022def77bbfdc44e71408ddfc13ba79e0d7a090'
SNAPSHOT_SHA = '3bedb78fd53d8e49a08d945d0664dbdb90f7cc0855e45bf08d94b998515d0ca6'
PRIOR_RUNTIME_SHA = '6a39c29b14f9fa00e995b8e3ff566def37bc13936bf6d99353332469e276bee4'
LIMITS = {'seconds': 60, 'peak_rss_bytes': 512 * 1024**2,
          'generated_file_bytes': 384 * 1024**2}
SESSION_LIMITS = {'max_requests': 32, 'max_bytes': 32 * 1024**2, 'max_seconds': 10}
TOTAL_LIMITS = {'max_requests': 1000, 'max_bytes': 1024**3, 'max_seconds': 600}
START = time.monotonic()
OUT = None
FORBIDDEN = []
SOCKET_ATTEMPTS = []


def audit(event, args):
    if event.startswith('socket.') and event != 'socket.__new__':
        SOCKET_ATTEMPTS.append({'event': event, 'argument_types': [type(a).__name__ for a in args]})
        raise RuntimeError('socket operation denied by integrated session candidate')


sys.addaudithook(audit)
if not sys.flags.isolated or not sys.dont_write_bytecode or Path(sys.prefix).resolve() != RUNTIME.resolve():
    raise RuntimeError('isolated pinned HDF5 interpreter -I -B required')
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts'), str(BASE / 'receiver-candidate'), str(Path(__file__).parent)]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def budget():
    if time.monotonic() - START > LIMITS['seconds']:
        raise RuntimeError('session handoff candidate time ceiling')
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > LIMITS['peak_rss_bytes']:
        raise RuntimeError('session handoff candidate RSS ceiling')
    if OUT is not None and OUT.exists() and generated_bytes() > LIMITS['generated_file_bytes']:
        raise RuntimeError('session handoff candidate output ceiling')


def generated_bytes():
    return sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())


def pin(path, maximum=512 * 1024**2):
    path = Path(path).resolve()
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= maximum:
            raise ValueError('bounded regular input required: ' + str(path))
        h = hashlib.sha256()
        count = 0
        while chunk := handle.read(1024**2):
            count += len(chunk)
            if count > before.st_size:
                raise ValueError('input grew during hash: ' + str(path))
            h.update(chunk)
            if time.monotonic() - START > LIMITS['seconds']:
                raise RuntimeError('session handoff input hashing time ceiling')
        if count != before.st_size:
            raise ValueError('input changed size during hash: ' + str(path))
    return {'path': str(path), 'bytes': count, 'sha256': h.hexdigest()}


def write(path, value):
    data = canonical(value)
    budget()
    if generated_bytes() + len(data) > LIMITS['generated_file_bytes']:
        raise RuntimeError('prospective session output ceiling')
    with Path(path).open('xb') as handle:
        if handle.write(data) != len(data):
            raise OSError('short evidence write')
        handle.flush()
        os.fsync(handle.fileno())
    budget()
    return pin(path)


def bound_json(path, sha, maximum=8 * 1024**2):
    path = Path(path)
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum:
            raise ValueError('bounded regular sole-link JSON input required')
        payload = handle.read(maximum + 1)
    if len(payload) != before.st_size or hashlib.sha256(payload).hexdigest() != sha:
        raise ValueError('externally supplied JSON file digest differs: ' + str(path))
    actual = {'path': str(path.resolve()), 'bytes': len(payload), 'sha256': sha}
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError('duplicate JSON field in bound input')
            result[key] = value
        return result
    value = json.loads(payload, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON input')))
    return value, actual


def import_pinned(name, path, sha):
    actual = pin(path, 64 * 1024)
    if actual['sha256'] != sha:
        raise ValueError('candidate module pin differs: ' + name)
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, actual


probe, PROBE_PIN = import_pinned('retained_acquisition_probe', BASE / 'acquisition-candidate/acquisition_probe_attempt03.py', PROBE_SHA)
bridge, BRIDGE_PIN = import_pinned('local_receipt_receiver', BASE / 'receiver-candidate/local_receipt_receiver.py', BRIDGE_SHA)
import numpy as np
from seti_repeater import acquisition_radio as acquisition
from radio_receiver_adapter_common import context, PINS as CONTEXT_PINS
import engineering_session_store as session_store


def forbid(name):
    def refused(*args, **kwargs):
        FORBIDDEN.append(name)
        raise RuntimeError('forbidden candidate capability: ' + name)
    return refused


def scope_for(definition, window):
    return {'scan': definition['label'], 'window': window['name'], 'url': definition['url'],
            'source_definition_sha256': acquisition.digest(definition),
            'extraction': list(window['archive_interval'])}


def retain_session(b, scope, server, call_start, response_start, receipt, detail, role, label, outcome):
    b.close(outcome)
    record = b.record()
    checkpoint = asdict(b.checkpoint)
    report = session_store.strict_read_journal(b.journal.path, expected_checkpoint=b.checkpoint,
        expected_reservation=b.reservation, expected_head=b.journal.head,
        ordered_scopes=[scope], require_closed=True)
    # Independently replay simulated HEAD/GET intervals and accepted bodies;
    # the request journal's accounting must match both transport and budget.
    calls = server.calls[call_start:]
    responses = server.responses[response_start:]
    reserves = []
    accepted = 0
    for call, response in zip(calls, responses):
        if call['method'] == 'HEAD':
            reserves.append(0)
            if response.reads:
                raise ValueError('HEAD unexpectedly read a body')
        elif call['method'] == 'GET':
            first, last = map(int, call['range'].removeprefix('bytes=').split('-'))
            reserves.append(last - first + 2)
            if response.reads != 1:
                raise ValueError('successful body did not have one bounded read')
            accepted += len(response.payload)
        else:
            raise ValueError('unexpected simulated request method')
    if len(calls) != len(responses):
        raise ValueError('simulated transcript response count differs')
    parsed = report
    journal_reserves = [e['reserved_bytes'] for e in parsed['events'] if e['type'] == 'reserve']
    if (journal_reserves != reserves or record['attempts'] != len(calls)
            or record['reserved_bytes'] != sum(reserves) or record['accepted_bytes'] != accepted
            or parsed['reserved_attempts'] != len(calls) or parsed['reserved_bytes'] != sum(reserves)
            or parsed['accepted_bytes'] != accepted):
        raise ValueError('journal, budget and independent simulated transcript accounting differ')
    stem = role + '-' + label
    checkpoint_pin = write(OUT / (stem + '-checkpoint.json'), checkpoint)
    reservation_pin = write(OUT / (stem + '-reservation.json'), b.reservation)
    journal_pin = pin(b.journal.path, 1024**2)
    strict_pin = write(OUT / (stem + '-strict-replay.json'), report)
    evidence = {'label': label, 'role': role, 'scope': scope, 'checkpoint': checkpoint,
        'reservation': b.reservation, 'final_head': b.journal.head, 'journal': journal_pin,
        'strict_receipt_file': strict_pin, 'checkpoint_file': checkpoint_pin,
        'reservation_file': reservation_pin, 'outcome': outcome, 'budget': record,
        'request_reserved_byte_sequence': reserves, 'simulated_calls': calls,
        'simulated_accepted_bytes': accepted, 'transcript_matches_budget_and_journal': True,
        'reservation_remains_fully_charged': True,
        'product_receipt_sha256': None if receipt is None else receipt['receipt_sha256'],
        'product_source_file': None if receipt is None else pin(OUT / 'products' / role / label / 'source.json'),
        'transport_detail': detail}
    evidence_pin = write(OUT / (stem + '-session-evidence.json'), evidence)
    return evidence, evidence_pin


def joined_fixture_run(path, trusted_sha256, c, directories):
    """Read-only journal/product join completed before receiver construction.

    Expected checkpoint, reservation, head and file hashes come from the caller's
    bound manifest rather than being inferred from journal content. This grants
    no source request or scientific permission and never creates a budget.
    """
    joined, joined_pin = bound_json(path, trusted_sha256, 2 * 1024**2)
    if (set(joined) != {'schema', 'bridge_manifest', 'sessions', 'final_checkpoint', 'final_checkpoint_file', 'scientific_admission',
                       'hosted_transport_qualified', 'public_authentication_established'}
            or joined['schema'] != 'radio-session-joined-receiver-manifest-candidate-v1'
            or any(joined[k] is not False for k in ('scientific_admission',
                        'hosted_transport_qualified', 'public_authentication_established'))):
        raise ValueError('exact engineering joined-manifest authority required')
    manifest, evidence = joined['bridge_manifest'], joined['sessions']
    if (type(evidence) is not list or len(evidence) != 6
            or tuple(e['label'] for e in evidence) != bridge.received.LABELS
            or tuple(e['label'] for e in manifest['scans']) != bridge.received.LABELS
            or set(directories) != set(bridge.received.LABELS)):
        raise ValueError('exact ordered six-session receiver join required')
    inventory_sha = acquisition.digest([entry['scope']['definition'] for entry in manifest['scans']])
    final_checkpoint = acquisition.Checkpoint(**joined['final_checkpoint'])
    final_summary = acquisition.validate_ledger(final_checkpoint.document, final_checkpoint.sha256)
    final_stated = joined['final_checkpoint_file']
    final_value, final_pin = bound_json(final_stated['path'], final_stated['sha256'], 128 * 1024)
    if (final_pin != final_stated or canonical(final_value) != canonical(joined['final_checkpoint'])
            or final_checkpoint.document['contract_sha256'] != manifest['fixture_source_contract_sha256']
            or final_checkpoint.document['source_inventory_sha256'] != inventory_sha
            or canonical(final_checkpoint.document['total_limits']) != canonical(TOTAL_LIMITS)
            or final_summary['sessions'] != 19
            or any(final_summary['charged_limits'][k] != 19 * SESSION_LIMITS[k] for k in SESSION_LIMITS)):
        raise ValueError('joined final nineteen-session cumulative checkpoint differs')
    joined_reports, observed_paths = [], {}
    observed_paths[final_pin['path']] = final_pin
    shared_location, previous_reservations, seen_session_ids = None, None, set()
    for entry, session in zip(manifest['scans'], evidence, strict=True):
        label = entry['label']
        source_scope = entry['scope']
        expected_scope = {'scan': label, 'window': source_scope['window'],
            'url': source_scope['definition']['url'],
            'source_definition_sha256': acquisition.digest(source_scope['definition']),
            'extraction': source_scope['archive_interval']}
        checkpoint = acquisition.Checkpoint(**session['checkpoint'])
        if (session['role'] != manifest['role'] or canonical(session['scope']) != canonical(expected_scope)
                or session['outcome'] != 'completed'
                or session['product_receipt_sha256'] != entry['receipt_sha256']
                or checkpoint.document['contract_sha256'] != manifest['fixture_source_contract_sha256']
                or checkpoint.document['source_inventory_sha256'] != inventory_sha
                or canonical(checkpoint.document['total_limits']) != canonical(TOTAL_LIMITS)
                or canonical(session['reservation']['reserved_limits']) != canonical(SESSION_LIMITS)):
            raise ValueError('session/product/descriptor/inventory ancestry differs')
        reservations = checkpoint.document['reservations']
        if (canonical(checkpoint.location) != canonical(final_checkpoint.location)
                or canonical(final_checkpoint.document['reservations'][:len(reservations)]) != canonical(reservations)):
            raise ValueError('source session checkpoint is not a prefix of the final cumulative ledger')
        if shared_location is None:
            shared_location = checkpoint.location
        elif canonical(checkpoint.location) != canonical(shared_location):
            raise ValueError('joined sessions came from different cumulative reservation stores')
        if (session['reservation']['session_id'] in seen_session_ids
                or (previous_reservations is not None and (
                    len(reservations) <= len(previous_reservations)
                    or canonical(reservations[:len(previous_reservations)]) != canonical(previous_reservations)))):
            raise ValueError('joined sessions are not unique increasing prefixes of one cumulative ledger')
        seen_session_ids.add(session['reservation']['session_id'])
        previous_reservations = reservations
        for field, expected_value in (('checkpoint_file', session['checkpoint']),
                                      ('reservation_file', session['reservation'])):
            stated = session[field]
            actual_value, actual_pin = bound_json(stated['path'], stated['sha256'], 128 * 1024)
            if actual_pin != stated or canonical(actual_value) != canonical(expected_value):
                raise ValueError('externally retained session join file differs: ' + field)
            observed_paths[actual_pin['path']] = actual_pin
        stated_journal = session['journal']
        actual_journal = pin(stated_journal['path'], session_store.MAX_JOURNAL_BYTES)
        if actual_journal != stated_journal:
            raise ValueError('joined journal file bytes differ')
        replay = session_store.strict_read_journal(stated_journal['path'],
            expected_checkpoint=checkpoint, expected_reservation=session['reservation'],
            expected_head=session['final_head'], ordered_scopes=[expected_scope], require_closed=True)
        actual_journal_after = pin(stated_journal['path'], session_store.MAX_JOURNAL_BYTES)
        if actual_journal_after != stated_journal:
            raise ValueError('joined journal changed during strict replay')
        stated_report = session['strict_receipt_file']
        old_report, old_report_pin = bound_json(stated_report['path'], stated_report['sha256'], 1024**2)
        if old_report_pin != stated_report or canonical(old_report) != canonical(replay):
            raise ValueError('retained strict journal replay differs')
        pending_body = False
        for event in replay['events']:
            if event['type'] in ('reserve', 'scope', 'session_end') and pending_body:
                raise ValueError('completed source session has unaccepted body reservation')
            if event['type'] == 'reserve':
                pending_body = event['reserved_bytes'] > 0
            elif event['type'] == 'accepted_body':
                if not pending_body:
                    raise ValueError('completed source session accepted an unreserved body')
                pending_body = False
        if replay['outcome'] != 'completed' or replay['accepted_bytes'] <= 0:
            raise ValueError('closed completed source body acquisition required')
        journal_reserves = [e['reserved_bytes'] for e in replay['events'] if e['type'] == 'reserve']
        simulated_reserves, simulated_accepted = [], 0
        for request in session['simulated_calls']:
            if request['url'] != expected_scope['url']:
                raise ValueError('simulated request URL differs from ordered scope')
            if request['method'] == 'HEAD':
                simulated_reserves.append(0)
            elif request['method'] == 'GET':
                first, last = map(int, request['range'].removeprefix('bytes=').split('-'))
                simulated_reserves.append(last - first + 2)
                simulated_accepted += last - first + 1
            else:
                raise ValueError('unsupported simulated request in product join')
        if (journal_reserves != session['request_reserved_byte_sequence']
                or journal_reserves != simulated_reserves
                or replay['reserved_attempts'] != session['budget']['attempts']
                or replay['reserved_bytes'] != session['budget']['reserved_bytes']
                or replay['accepted_bytes'] != session['budget']['accepted_bytes']
                or replay['accepted_bytes'] != session['simulated_accepted_bytes']
                or replay['accepted_bytes'] != simulated_accepted):
            raise ValueError('joined simulated transcript/journal/budget accounting differs')
        source_path = Path(directories[label]) / 'source.json'
        stated_source = session['product_source_file']
        if str(source_path.resolve()) != stated_source['path']:
            raise ValueError('fresh source receipt path differs from bound product')
        source_receipt, actual_source = bound_json(source_path, stated_source['sha256'], bridge.MAX_SOURCE_JSON_BYTES)
        if (actual_source != stated_source or canonical(source_receipt['scope']) != canonical(source_scope)
                or source_receipt['receipt_sha256'] != entry['receipt_sha256']):
            raise ValueError('fresh source receipt file/semantic scope differs')
        bridge.rows.verify(source_receipt)
        observed_paths[actual_journal['path']] = actual_journal
        observed_paths[old_report_pin['path']] = old_report_pin
        observed_paths[actual_source['path']] = actual_source
        joined_reports.append({'label': label, 'journal_file': actual_journal,
            'journal_head': replay['head_sha256'], 'ledger_sha256': replay['ledger_sha256'],
            'publication_revision': replay['publication_revision'], 'session_id': replay['session_id'],
            'reservation_sha256': replay['reservation_sha256'], 'source_file': actual_source,
            'source_receipt_sha256': source_receipt['receipt_sha256'], 'accepted_bytes': replay['accepted_bytes'],
            'completed_body_reservations_all_accepted': True})
    # Every source metadata receipt and journal is validated before source arrays
    # cross the receiver boundary, then the unchanged bridge reads the rows.
    binding = bridge.bind(manifest, bridge.rows.digest(manifest), c)
    run, handoff = bridge.fixture_run(c, binding, directories)
    for path, expected in observed_paths.items():
        if pin(path, 2 * 1024**2) != expected:
            raise ValueError('joined input file bytes changed during receiver construction')
    return run, handoff, {'schema': 'radio-read-only-session-product-receiver-join-replay-v1',
        'joined_manifest_file': joined_pin, 'bridge_binding_sha256': binding.identity,
        'role': manifest['role'], 'sessions': joined_reports,
        'final_cumulative_checkpoint_file': final_pin, 'final_cumulative_ledger_sha256': final_checkpoint.sha256,
        'shared_cumulative_publication_location': shared_location,
        'unique_increasing_reservation_prefixes_verified': True,
        'all_journals_and_source_receipts_validated_before_receiver': True,
        'restored_request_permission': False, 'scientific_admission': False,
        'hosted_transport_qualified': False, 'public_authentication_established': False}


def main(args):
    global OUT
    OUT = Path(args.output).resolve()
    OUT.mkdir(exist_ok=False)
    probe.OUT = OUT
    probe.START = START
    probe.LIMITS = dict(LIMITS)
    write(OUT / 'observation-identity.json', {'schema': 'radio-candidate-procfs-observation-identity-v1',
        'procfs_pid': int(os.readlink('/proc/self')), 'namespace_pid': os.getpid(),
        'driver_path': str(Path(__file__).resolve()), 'observed_after_module_imports': True,
        'whole_lifetime_certificate': False})
    driver_pin = pin(__file__, 64 * 1024)
    store_pin = pin(session_store.__file__, 64 * 1024)
    if store_pin['sha256'] != args.trusted_store_sha256:
        raise ValueError('session store candidate bytes differ from prospective pin')
    prior_path = Path(args.acquisition_index).resolve()
    prior, prior_pin = bound_json(prior_path, args.trusted_acquisition_sha256)
    if (prior.get('status') != 'PASS' or prior.get('full_scan_window_pairs') != 18
            or prior.get('row_products') != 288 or prior.get('source_or_scientific_admission') is not False):
        raise ValueError('pinned previous complete local source candidate required')
    original_descriptor, prior_descriptor_pin = bound_json(prior_path.parent / 'fixture-descriptor.json',
        prior['fixture_descriptor_pin']['sha256'])
    definitions = copy.deepcopy(original_descriptor['scans'])
    windows = copy.deepcopy(original_descriptor['windows'])
    fixtures = [Path(f['path']).resolve() for f in original_descriptor['fixture_files']]
    fixture_pins = [pin(p, 32 * 1024**2) for p in fixtures]
    for actual, declared in zip(fixture_pins, original_descriptor['fixture_files']):
        if any(actual[k] != declared[k] for k in ('path', 'bytes', 'sha256')):
            raise ValueError('reused synthetic HDF5 file differs from trusted descriptor')
    for i, d in enumerate(definitions):
        d['url'] = 'https://' + d['label'] + '.invalid/fresh-session-source.h5'
        d['expected_etag'] = '"fresh-durable-session-candidate-1-' + str(i) + '"'
        d['expected_remote_size_bytes'] = fixture_pins[i]['bytes']
    forecast = {'six_fresh_sparse_mirror_bounds': 6 * 32 * 1024**2,
        '288_native_and_normalized_npy_bounds': 288 * 2 * (65536 * 4 + 4096),
        'all_metadata_sessions_sqlite_reports_allowance': 20 * 1024**2}
    if sum(forecast.values()) > LIMITS['generated_file_bytes']:
        raise ValueError('prospective generated-byte forecast exceeds fixed cap')
    write(OUT / 'prospective-file-forecast.json', {'bounds': forecast,
        'total_logical_bytes': sum(forecast.values()), 'fixed_limit_bytes': LIMITS['generated_file_bytes'],
        'reused_fixture_bytes_not_generated_again': sum(p['bytes'] for p in fixture_pins),
        'counts_sparse_logical_extents': True})
    snapshot, snapshot_pin = bound_json(ROOT / 'snapshot.json', SNAPSHOT_SHA)
    prior_runtime, prior_runtime_pin = bound_json(BASE / 'runtime-before.json', PRIOR_RUNTIME_SHA)
    input_before = {p['path']: p for p in [driver_pin, store_pin, PROBE_PIN, BRIDGE_PIN, prior_pin,
                                         prior_descriptor_pin, snapshot_pin, prior_runtime_pin, *fixture_pins]}
    for expected in snapshot['files']:
        actual = pin(ROOT / expected['path'])
        if actual['bytes'] != expected['bytes'] or actual['sha256'] != expected['sha256']:
            raise ValueError('static project snapshot input differs: ' + expected['path'])
        input_before[actual['path']] = actual
    for expected in prior_runtime['files']:
        runtime_path = RUNTIME / expected['path']
        actual = pin(runtime_path)
        if actual['bytes'] != expected['bytes'] or actual['sha256'] != expected['sha256']:
            raise ValueError('previous held runtime file differs: ' + expected['path'])
        details = runtime_path.stat()
        if (details.st_dev, details.st_ino, details.st_mtime_ns, details.st_ctime_ns) != (
                expected['device'], expected['inode'], expected['mtime_ns'], expected['ctime_ns']):
            raise ValueError('held runtime file identity/time differs: ' + expected['path'])
        input_before[actual['path']] = actual
    observed_before = probe.runtime_snapshot()
    for expected in observed_before['files']:
        input_before[expected['path']] = {k: expected[k] for k in ('path', 'bytes', 'sha256')}
    write(OUT / 'positive-inputs-before.json', {'files': [input_before[p] for p in sorted(input_before)],
        'observed_runtime': observed_before, 'whole_execution_runtime_qualification': False})
    for name, expected in CONTEXT_PINS.items():
        if input_before[str(ROOT / name)]['sha256'] != expected:
            raise ValueError('receiver context input changed: ' + name)
    descriptor = {'schema': 'radio-fresh-durable-session-fixture-descriptor-candidate-v1',
        'prior_acquisition_index_pin': prior_pin, 'prior_fixture_descriptor_pin': prior_descriptor_pin,
        'scans': definitions, 'windows': windows, 'fixture_files': fixture_pins,
        'original_header_label_role_chunks_filters_preserved': True,
        'only_definition_changes': ['url', 'expected_etag', 'expected_remote_size_bytes'],
        'source_filter_pipeline': original_descriptor['source_filter_pipeline'],
        'current_encoder_filter_pipeline': original_descriptor['current_encoder_filter_pipeline'],
        'current_encoder_is_original_archive_encoder': False,
        'synthetic_fixture_bytes_reused': True, 'new_independent_draws': False,
        'new_independent_row_oracle': False, 'random_draws': 0,
        'telescope_provenance': False, 'scientific_allocation': False}
    descriptor_pin = write(OUT / 'fixture-descriptor.json', descriptor)
    fixture_contract = descriptor_pin['sha256']
    inventory_sha = acquisition.digest(definitions)
    genesis = acquisition.genesis(fixture_contract, inventory_sha, TOTAL_LIMITS)
    write(OUT / 'genesis.json', genesis)
    store = session_store.EngineeringSqliteStore.create(OUT / 'reservations.sqlite3', genesis)
    prior_by_key = {(p['role'], p['label']): p for p in prior['products']}
    products, sessions = [], []
    server = probe.SyntheticServer(definitions, fixtures)
    with ExitStack() as stack:
        stack.enter_context(patch.object(probe.net, 'open_response', side_effect=server))
        for name in ('build_store', 'cache', 'receiver', 'calibrate', 'execute'):
            stack.enter_context(patch.object(bridge.pipeline.NativeRun, name, side_effect=forbid('NativeRun.' + name)))
        for name in ('build_synthetic_cache', 'gather_bank_slice'):
            stack.enter_context(patch.object(bridge.native, name, side_effect=forbid('native.' + name)))
        for name in ('default_rng', 'RandomState', 'seed', 'random', 'normal'):
            stack.enter_context(patch.object(np.random, name, side_effect=forbid('numpy.random.' + name)))
        for definition in definitions:
            for window in windows:
                role, label = window['role'], definition['label']
                destination = OUT / 'products' / role / label
                before = store.read()
                b = acquisition.start_session(store, expected_revision=before.revision,
                    expected_ledger_sha256=before.sha256, session_limits=SESSION_LIMITS,
                    directory=OUT / 'sessions' / (role + '-' + label))
                scope = scope_for(definition, window)
                b.bind_scope(scope)
                call_start, response_start = len(server.calls), len(server.responses)
                try:
                    receipt, detail = probe.source._extract_bound_source(definition, window,
                        fixture_contract, destination, OUT / 'mirrors' / label, b, kind='local-fixture')
                except BaseException:
                    if not b.closed:
                        b.close('error')
                    raise
                if detail['resumed_rows'] != 0:
                    raise ValueError('fresh session unexpectedly resumed an old product')
                row_oracles = prior_by_key[role, label]['row_oracles']
                for row, oracle in enumerate(row_oracles):
                    if (receipt['rows'][row]['native_sha256'] != oracle['native_sha256']
                            or receipt['rows'][row]['normalized_sha256'] != oracle['normalized_sha256']):
                        raise ValueError('fresh acquisition bytes differ from externally pinned prior synthetic product')
                evidence, evidence_pin = retain_session(b, scope, server, call_start, response_start,
                    receipt, detail, role, label, 'completed')
                sessions.append(evidence)
                products.append({'label': label, 'role': role, 'window': window['name'],
                    'directory': str(destination), 'receipt_sha256': receipt['receipt_sha256'],
                    'scope_sha256': bridge.rows.digest(receipt['scope']), 'scope': receipt['scope'],
                    'source_file': evidence['product_source_file'], 'session_evidence_file': evidence_pin,
                    'row_oracles': row_oracles, 'comparison_is_reproduction_of_pinned_prior_bytes': True,
                    'new_independent_row_oracle': False})
                budget()
        write(OUT / 'positive-http-transcript.json', server.receipt())
        # A fresh, fully charged session reaches bad strong ETag at HEAD and
        # refuses before body reads, sparse mirror creation or product receipt.
        negative_actual = copy.deepcopy(definitions[0])
        negative_actual['url'] = 'https://epoch1_on.invalid/fresh-session-bad-etag.h5'
        negative_actual['expected_etag'] = '"actual-negative-session-1"'
        negative_definition = copy.deepcopy(negative_actual)
        negative_definition['expected_etag'] = '"expected-negative-session-1"'
        negative_server = probe.SyntheticServer([negative_actual], [fixtures[0]])
        before = store.read()
        b = acquisition.start_session(store, expected_revision=before.revision,
            expected_ledger_sha256=before.sha256, session_limits=SESSION_LIMITS,
            directory=OUT / 'sessions' / 'negative-bad-etag')
        negative_scope = scope_for(negative_definition, windows[0])
        b.bind_scope(negative_scope)
        with patch.object(probe.net, 'open_response', side_effect=negative_server):
            try:
                probe.source._extract_bound_source(negative_definition, windows[0], fixture_contract,
                    OUT / 'negative' / 'product', OUT / 'negative' / 'mirror', b, kind='local-fixture')
            except ValueError as error:
                if str(error) != 'live source differs from contract':
                    raise
                negative_reason = str(error)
            else:
                raise ValueError('bad ETag unexpectedly accepted')
        negative_evidence, negative_evidence_pin = retain_session(b, negative_scope, negative_server,
            0, 0, None, None, 'negative', 'bad-etag', 'error')
        if (negative_evidence['budget']['accepted_bytes'] != 0 or len(negative_server.calls) != 1
                or negative_server.calls[0]['method'] != 'HEAD' or any(r.reads for r in negative_server.responses)
                or (OUT / 'negative' / 'product' / 'source.json').exists()):
            raise ValueError('bad HEAD ETag produced body access or source receipt')
        write(OUT / 'negative-http-transcript.json', negative_server.receipt())
        final_checkpoint = store.read()
        final_ledger_summary = acquisition.validate_ledger(final_checkpoint.document, final_checkpoint.sha256)
        if final_ledger_summary['sessions'] != 19 or any(
                final_ledger_summary['charged_limits'][k] != 19 * SESSION_LIMITS[k] for k in SESSION_LIMITS):
            raise ValueError('nineteen full reservations were not permanently charged')
        all_session_ids = set()
        for retained in [*sessions, negative_evidence]:
            checkpoint = retained['checkpoint']
            reservations = checkpoint['document']['reservations']
            session_id = retained['reservation']['session_id']
            if (canonical(checkpoint['location']) != canonical(final_checkpoint.location)
                    or canonical(final_checkpoint.document['reservations'][:len(reservations)]) != canonical(reservations)
                    or session_id in all_session_ids):
                raise ValueError('all nineteen sessions do not join the same final cumulative ledger')
            all_session_ids.add(session_id)
        final_checkpoint_pin = write(OUT / 'final-checkpoint.json', asdict(final_checkpoint))
        roles = []
        for role in bridge.ROLES:
            c = context(role)
            provenance = json.loads(c.factor_contract.factors.provenance_json)
            chosen = [next(p for p in products if p['role'] == role and p['label'] == label)
                      for label in bridge.received.LABELS]
            bridge_manifest = {'schema': bridge.SCHEMA, 'domain': 'local-fixture', **bridge.receiver_window(c),
                'context_sha256': c.identity, 'receiver_factor_bank_sha256': c.factor_contract.factors.identity,
                'receiver_source_contract_sha256': provenance['source_contract_sha256'],
                'fixture_source_contract_sha256': fixture_contract, 'runtime': probe.source.runtime(),
                'scans': [{'label': p['label'], 'scope': p['scope'], 'receipt_sha256': p['receipt_sha256']} for p in chosen]}
            joined = {'schema': 'radio-session-joined-receiver-manifest-candidate-v1',
                'bridge_manifest': bridge_manifest,
                'final_checkpoint': asdict(final_checkpoint), 'final_checkpoint_file': final_checkpoint_pin,
                'sessions': [next(s for s in sessions if s['role'] == role and s['label'] == label)
                             for label in bridge.received.LABELS],
                'scientific_admission': False, 'hosted_transport_qualified': False,
                'public_authentication_established': False}
            joined_pin = write(OUT / (role + '-joined-manifest.json'), joined)
            directories = {p['label']: p['directory'] for p in chosen}
            run, handoff, joined_report = joined_fixture_run(
                OUT / (role + '-joined-manifest.json'), joined_pin['sha256'], c, directories)
            count = 0
            for p in chosen:
                for row, oracle in enumerate(p['row_oracles']):
                    if bridge.native.array_hash(run.sources[p['label']].values[row]) != oracle['normalized_sha256']:
                        raise ValueError('receiver array differs from externally pinned reused synthetic bytes')
                    count += 1
            bridge.rows.verify(handoff)
            handoff_pin = write(OUT / (role + '-handoff.json'), handoff)
            joined_report_pin = write(OUT / (role + '-session-join-replay.json'), joined_report)
            roles.append({'role': role, 'joined_manifest': joined_pin, 'joined_replay': joined_report_pin,
                'handoff_file': handoff_pin, 'handoff_receipt_sha256': handoff['receipt_sha256'],
                'normalized_rows_compared_to_pinned_prior_products': count,
                'unique_raw_payloads': handoff['unique_raw_payloads'],
                'unique_normalized_payloads': handoff['unique_normalized_payloads'],
                'modelled_array_bound_bytes': handoff['modelled_array_bound_bytes']})
            del run, handoff, c
            budget()
    input_after = {p: pin(p) for p in sorted(input_before)}
    if input_after != input_before:
        raise ValueError('bound project, candidate, runtime or reused fixture file bytes changed')
    observed_after = probe.runtime_snapshot()
    additions = [p for p in observed_after['files'] if p['path'] not in input_before]
    write(OUT / 'positive-inputs-after.json', {'files': [input_after[p] for p in sorted(input_after)],
        'observed_runtime': observed_after, 'additional_observed_runtime_files': additions,
        'whole_execution_runtime_qualification': False})
    metadata = ROOT / 'src/seti_repeater/prospective_source_metadata_radio.py'
    missing = next(ast.literal_eval(n.value) for n in ast.parse(metadata.read_bytes()).body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MISSING_FIELDS' for t in n.targets))
    if len(missing) != 11 or canonical(missing) != canonical(prior['scientific_missing_fields_unchanged']):
        raise ValueError('eleven scientific missing fields changed')
    if SOCKET_ATTEMPTS or probe.SOCKET_ATTEMPTS or FORBIDDEN:
        raise ValueError('forbidden capability was attempted')
    generated = [pin(p) for p in sorted(OUT.rglob('*')) if p.is_file()]
    report = {'schema': 'radio-durable-session-source-receiver-join-candidate-v1', 'status': 'PASS',
        'authority': 'synthetic local engineering only', 'driver_pin': driver_pin, 'store_pin': store_pin,
        'source_probe_pin': PROBE_PIN, 'receiver_bridge_pin': BRIDGE_PIN,
        'prior_acquisition_index_pin': prior_pin, 'fixture_descriptor_pin': descriptor_pin,
        'static_project_file_count': len(snapshot['files']), 'held_runtime_file_count': len(prior_runtime['files']),
        'bound_input_bytes_unchanged': True, 'positive_sessions': 18, 'negative_sessions': 1,
        'scan_window_products': 18, 'row_products': 288, 'receiver_contexts_constructed': 3,
        'normalized_rows_compared_to_pinned_prior_products': sum(p['normalized_rows_compared_to_pinned_prior_products'] for p in roles),
        'synthetic_fixture_bytes_reused': True, 'new_independent_row_oracle': False,
        'sessions': sessions, 'products': products, 'roles': roles,
        'negative_bad_etag_reason': negative_reason, 'negative_session_evidence_pin': negative_evidence_pin,
        'negative_session_body_bytes': 0, 'negative_completed_source_receipts': 0,
        'final_checkpoint_pin': final_checkpoint_pin, 'final_ledger_summary': final_ledger_summary,
        'session_limits': SESSION_LIMITS, 'cumulative_limits': TOTAL_LIMITS,
        'reservations_never_refunded_or_resumed': True,
        'simulated_transcript_accounting_joined_to_all_session_journals': True,
        'session_journals_replayed_before_receiver_construction': True,
        'resource_limits': LIMITS, 'prospective_logical_file_forecast': forecast,
        'observed_seconds': time.monotonic() - START,
        'observed_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'generated_file_bytes_before_index': sum(p['bytes'] for p in generated), 'generated_files': generated,
        'scientific_missing_fields_unchanged': missing, 'socket_attempts': SOCKET_ATTEMPTS + probe.SOCKET_ATTEMPTS,
        'forbidden_invocations': FORBIDDEN, 'network_requests': 0, 'telescope_or_holdout_files_opened': 0,
        'rng_draws': 0, 'scoring_invoked': False, 'cache_invoked': False, 'reduction_invoked': False,
        'controls_invoked': False, 'control_activation': False, 'source_or_scientific_admission': False,
        'source_specific_executable_contract_created': False, 'telescope_provenance_established': False,
        'public_authentication_established': False, 'hosted_transport_qualified': False,
        'receiver_scoring_qualified': False, 'native_127_24_qualification': False,
        'whole_execution_runtime_qualification': False, 'complete_execution_runtime_freeze': False,
        'externally_observed_complete_lifetime': False,
        'coverage_limitations': [
            'Local SQLite reservation store and simulated .invalid HTTP; no hosted authenticated publication.',
            'Low-level start_session plus explicit scope and local-fixture extraction; gated telescope entrypoints remain unused.',
            'Synthetic HDF5 bytes and row hashes are reused from externally pinned prior engineering evidence, without a fresh draw or oracle.',
            'No scientific score, cache, reduction, control, native8 allocation, held spectrum or telescope data access.',
            'Observed file snapshots do not certify complete runtime, process or resource lifetime.',
            'Inherited source rehydrate reopens file paths; hostile concurrent filesystem mutation remains outside qualification.',
        ]}
    report_pin = write(OUT / 'index.json', report)
    budget()
    print(json.dumps({'status': 'PASS', 'sessions': 19, 'products': 18, 'rows': 288,
        'seconds': report['observed_seconds'], 'peak_rss_bytes': report['observed_peak_rss_bytes'],
        'report': report_pin}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquisition-index', required=True)
    parser.add_argument('--trusted-acquisition-sha256', required=True)
    parser.add_argument('--trusted-store-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        main(args)
    except BaseException as error:
        if OUT is not None and OUT.exists() and not (OUT / 'failure.json').exists():
            # The fixed output cap also applies to failure metadata. If already
            # exhausted, the external supervisor retains stderr evidence.
            data = canonical({'schema': 'radio-durable-session-join-candidate-failure-v1',
                'error': repr(error), 'traceback': traceback.format_exc(),
                'seconds': time.monotonic() - START, 'automatic_retry': False,
                'source_or_scientific_admission': False})
            if len(data) <= 64 * 1024 and generated_bytes() + len(data) <= LIMITS['generated_file_bytes']:
                with (OUT / 'failure.json').open('xb') as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            else:
                print(data.decode(), file=sys.stderr)
        raise
