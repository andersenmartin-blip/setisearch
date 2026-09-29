#!/usr/bin/env python3
"""Two one-shot engineering draws, after a separately published reservation.

prepare writes plans/runtime only; run cannot be resumed or repeated. Public
reservation admission is attested by the caller's fresh immutable Git fetch;
the local journal is not advertised as a scientific remote publication store.
"""
import argparse
import gc
import hashlib
import json
import resource
import signal
import subprocess
import time
import traceback
from pathlib import Path
from radio_receiver_adapter_common import ROOT, PINS, context
from seti_repeater import gaussian_engineering_radio as e
from seti_repeater import whole_cadence_compact_radio as compact
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_runtime_radio import capture, PublishedFreeze
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest

BASE = 'results_radio_gaussian_engineering_2026-09-29'
OUT = ROOT / BASE
PROPOSAL = 'config/radio_whole_cadence_null_proposal_20260928.json'
SCOPE = 'RADIO_GAUSSIAN_ENGINEERING_2026-09-29_SCOPE.md'
CAPS = {**j.CAPS, 'active_milliseconds': 360000,
        'evidence_bytes': 20*1024**2, 'ledger_reserve_bytes': 2*1024**2}
CASE_MS = 180000
CASE_BYTES = 8*1024**2


def write(path, value):
    j.durable_write(path, canonical(value))


def prepare():
    plans = [e.make_plan(context(s['role']), i) for i, s in enumerate(e.SPECS)]
    forbidden = json.loads((ROOT/PROPOSAL).read_bytes())['cases']
    for i, p in enumerate(plans): e.validate_plan(context(e.SPECS[i]['role']), p, forbidden)
    # Metadata configurations only, including prior M43 identities. Never open
    # old holdout values. Keep the exact compared inventory, not an independence claim.
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--', 'config/*.json'], cwd=ROOT).decode().split('\0')
    inventory = []; seeds = set(); identities = set()
    def walk(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if 'seed' in k.lower() and type(v) is int: seeds.add(v)
                if 'identity' in k.lower() and isinstance(v, str): identities.add(v)
                walk(v)
        elif isinstance(value, list):
            for v in value: walk(v)
    for path in sorted(filter(None, paths)):
        raw = subprocess.check_output(['git', 'show', 'HEAD:'+path], cwd=ROOT)
        walk(json.loads(raw)); inventory.append({'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
    for p in plans:
        if p['case']['seed'] in seeds or p['case']['identity'] in identities:
            raise ValueError('Historical metadata identity/seed collision')
    write(OUT/'plans.json', plans)
    write(OUT/'identity_inventory.json', {'schema': 'radio-engineering-identity-comparison-v1',
          'historical_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
          'metadata_files': inventory, 'distinct_integer_seed_values': sorted(seeds),
          'identity_string_count': len(identities), 'reserved_scientific_cases': len(forbidden),
          'fresh_cases': [p['case'] for p in plans], 'collisions': [],
          'random_independence_inferred': False, 'holdout_values_opened': False})
    allocation = {'schema': 'radio-gaussian-native-engineering-allocation-v1',
                  'namespace': e.NAMESPACE, 'mode': 'ENGINEERING_ONLY',
                  'cases': [e.binding(p) for p in plans], 'caps': CAPS,
                  'milliseconds_per_case': CASE_MS, 'artifact_bytes_per_case': CASE_BYTES,
                  'restart_or_refund_authorized': False, 'scientific_allocation_charged': False}
    write(OUT/'allocation.json', allocation)
    inputs = [*PINS, PROPOSAL, SCOPE, BASE+'/plans.json', BASE+'/identity_inventory.json',
              BASE+'/allocation.json', 'tests/test_radio_gaussian_engineering.py',
              'tests/test_radio_whole_cadence_compact.py', BASE+'/preflight_tests.log']
    freeze = capture(ROOT, inputs)
    write(OUT/'runtime_freeze.json', freeze)
    print(json.dumps({'plans': [p['case']['identity'] for p in plans],
                      'code_files': len(freeze['code_sha256s']), 'runtime_files': len(freeze['runtime_sha256s']),
                      'freeze_sha256': digest(freeze), 'draws': 0}))


def run(commit, freeze_sha):
    start = time.monotonic()
    # A retained invocation directory refuses repeats even before journal creation.
    target = OUT/'live01'; target.mkdir(exist_ok=False)
    lease = None; rows = []; verifier = None
    try:
        intent_raw = subprocess.check_output(['git','show',commit+':'+BASE+'/consumption_intent.json'],cwd=ROOT)
        intent = json.loads(intent_raw)
        if (intent.get('namespace') != e.NAMESPACE or intent.get('allocation_irrevocably_reserved') is not True
                or intent.get('restart_authorized') is not False or intent.get('freeze_sha256') != freeze_sha
                or intent.get('case_count') != 2):
            raise ValueError('Exact published, spent, non-resumable reservation required')
        verifier = PublishedFreeze(ROOT, intent['freeze_commit'], BASE+'/runtime_freeze.json', freeze_sha)
        plans = json.loads((OUT/'plans.json').read_bytes())
        allocation = json.loads((OUT/'allocation.json').read_bytes())
        if intent.get('allocation_sha256') != digest(allocation):
            raise ValueError('Published consumption allocation differs')
        manifest = {'schema': j.SCHEMA, 'mode': 'engineering', 'namespace': e.NAMESPACE,
                    'execution_binding_sha256': freeze_sha, 'allocation_sha256': digest(allocation),
                    'cases': allocation['cases'], 'caps': CAPS, 'required_artifacts': e.ARTIFACTS}
        preflight = verifier.verify(manifest)
        write(target/'preflight.json', {**preflight, 'public_consumption_commit': commit,
                                       'intent_sha256': hashlib.sha256(intent_raw).hexdigest()})
        store = j.DirectoryStore.create(target/'journal', manifest)
        forbidden = json.loads((ROOT/PROPOSAL).read_bytes())['cases']
        def deadline(signum, frame): raise TimeoutError('Prospective engineering case deadline')
        signal.signal(signal.SIGALRM, deadline)
        for i, plan in enumerate(plans):
            ctx = context(e.SPECS[i]['role']); before = store.read()
            signal.setitimer(signal.ITIMER_REAL, CASE_MS/1000)
            lease = j.consume(store, expected_revision=before.revision,
                    expected_manifest_sha256=digest(manifest), binding=e.binding(plan),
                    milliseconds=CASE_MS, artifact_bytes=CASE_BYTES, directory=target/f'case{i}')
            stages = {}; t = time.monotonic()
            native_run, receipt = e.render(ctx, plan, lease=lease, forbidden_cases=forbidden,
                                           verify_freeze=verifier.verify)
            stages['gaussian_normalization_seconds'] = time.monotonic()-t; t = time.monotonic()
            scores = native_run.build_store(); lease.budget(native_run.modelled_bytes)
            native_run.validate_store(scores)
            stages['native_scores_seconds'] = time.monotonic()-t; t = time.monotonic()
            parts = e.compact_parts(native_run, scores, plan, receipt)
            for name, payload in parts.items(): lease.write_artifact(name, payload)
            pins = {name: hashlib.sha256(payload).hexdigest() for name, payload in parts.items()}
            result = compact.audit(ctx, {k:v for k,v in e.binding(plan).items() if k!='role'},
                                   parts, expected_sha256s=pins, byte_cap=CASE_BYTES)
            lease.write_artifact('compact_audit.json', canonical(result))
            stages['maximum_archive_audit_seconds'] = time.monotonic()-t
            cp = lease.finish()
            signal.setitimer(signal.ITIMER_REAL, 0)
            state = j.replay(cp.document)['cases'][i]
            rows.append({'ordinal': i, 'case_identity': plan['case']['identity'],
                         'status': state['status'], 'elapsed_milliseconds': state['elapsed_milliseconds'],
                         'stage_seconds': stages, 'compact_bytes': result['total_bytes'],
                         'maximum': json.loads(parts['maximum.json']),
                         'artifact_sha256s': pins, 'score_vectors': result['score_vectors'],
                         'score_values': result['score_values'], 'modelled_array_bytes': native_run.modelled_bytes,
                         'archive_check': j.verify_archive(cp,target/f'case{i}',case_index=i)})
            lease = None
            del scores, native_run, receipt, parts, result
            gc.collect()
        verifier.verify(manifest)
        if time.monotonic()-start > 420: raise TimeoutError('Prospective total live deadline')
        result = {'schema': 'radio-gaussian-native-engineering-result-v1', 'status': 'CLOSED_ENGINEERING_PASS',
                  'cases': rows, 'new_gaussian_values': 2*6*16*65536, 'normal_calls': 192,
                  'elapsed_seconds': time.monotonic()-start,
                  'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                  'public_consumption_commit': commit, 'freeze_sha256': freeze_sha,
                  'journal_state': j.replay(store.read().document),
                  'scientific_allocation_charged': False, 'telescope_values_opened': False,
                  'full_physical_recovery_rfi_null_gates_qualified': False,
                  'external_per_artifact_scientific_publication_qualified': False,
                  'source_arrays_restorable_from_compact_archive': False,
                  'automatic_retry_authorized': False}
        write(target/'result.json', result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('cases','journal_state')}, indent=2))
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        details = {'status': 'CLOSED_ENGINEERING_FAILED', 'error': repr(error),
                   'traceback': traceback.format_exc(), 'elapsed_seconds': time.monotonic()-start,
                   'completed_cases': rows, 'reservation_remains_spent': True, 'retry_authorized': False}
        if lease and not lease.closed and not lease.broken:
            try: lease.finish('failed', repr(error))
            except BaseException as nested: details['finish_error'] = repr(nested)
        write(target/'error.json', details)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['prepare','run'])
    p.add_argument('--consumption-commit'); p.add_argument('--freeze-sha256')
    args = p.parse_args()
    if args.action == 'prepare': prepare()
    else:
        if not args.consumption_commit or not args.freeze_sha256: p.error('Immutable intent and freeze required')
        run(args.consumption_commit, args.freeze_sha256)
