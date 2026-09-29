#!/usr/bin/env python3
"""Fixed eight-case, one-invocation engineering chain; no scientific activation."""
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
from seti_repeater import native_chain_engineering_radio as e
from seti_repeater import gaussian_engineering_radio as gaussian
from seti_repeater import whole_cadence_compact_radio as compact
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_runtime_radio import capture, PublishedFreeze
from seti_repeater.whole_cadence_reference_radio import CadenceMaximum, digest
from seti_repeater.empty_null_radio import canonical

BASE = 'results_radio_native_chain_engineering_2026-09-29'
OUT = ROOT/BASE
SCOPE = 'RADIO_NATIVE_CHAIN_ENGINEERING_2026-09-29_SCOPE.md'
PROPOSAL = 'config/radio_whole_cadence_null_proposal_20260928.json'
CASE_MS = 240000
CASE_BYTES = 24*1024**2
CAPS = {**j.CAPS, 'active_milliseconds': 8*CASE_MS,
        'evidence_bytes': 208*1024**2, 'ledger_reserve_bytes': 8*1024**2}


def write(path, value):
    j.durable_write(path, canonical(value))


def prepare():
    c = context('validation'); plans = [e.make_plan(c, i) for i in range(8)]
    forbidden = json.loads((ROOT/PROPOSAL).read_bytes())['cases']
    # Single batch of historical JSON metadata, not holdout values or result arrays.
    paths = subprocess.check_output(['git', 'ls-files', '-z', '--', 'config/*.json'], cwd=ROOT).decode().split('\0')
    paths = sorted(filter(None, paths))
    paths += ['results_radio_gaussian_engineering_2026-09-29/plans.json']
    raw = subprocess.check_output(['git', 'cat-file', '--batch'], cwd=ROOT,
          input=''.join('HEAD:'+p+'\n' for p in paths).encode())
    offset = 0; inventory = []; seeds = set(); identities = set()
    def walk(v):
        if isinstance(v, dict):
            for k, x in v.items():
                if 'seed' in k.lower() and type(x) is int: seeds.add(x)
                if 'identity' in k.lower() and isinstance(x, str): identities.add(x)
                walk(x)
        elif isinstance(v, list):
            for x in v: walk(x)
    for p in paths:
        end = raw.index(b'\n', offset); header = raw[offset:end].split(); offset=end+1
        if len(header)!=3 or header[1]!=b'blob': raise ValueError('Missing pinned metadata: '+p)
        size=int(header[2]); data=raw[offset:offset+size]; offset+=size+1
        walk(json.loads(data)); inventory.append({'path': p, 'sha256': hashlib.sha256(data).hexdigest()})
    if offset != len(raw): raise ValueError('Batch framing differs')
    for p in plans:
        e.validate_plan(c, p, forbidden)
        if p['case']['seed'] in seeds or p['case']['identity'] in identities:
            raise ValueError('Historical seed/identity collision')
    if len({p['case']['seed'] for p in plans}) != 8: raise ValueError('Duplicate new seed')
    write(OUT/'plans.json', plans)
    write(OUT/'identity_inventory.json', {'metadata_files': inventory, 'collisions': [],
          'historical_seed_count': len(seeds), 'historical_identity_count': len(identities),
          'reserved_scientific_cases': 151, 'new_engineering_cases': 8,
          'random_independence_inferred': False, 'holdout_values_opened': False})
    allocation = {'namespace': e.NAMESPACE, 'mode': 'ENGINEERING_ONLY',
                  'cases': [e.binding(p) for p in plans], 'caps': CAPS,
                  'milliseconds_per_case': CASE_MS, 'artifact_bytes_per_case': CASE_BYTES,
                  'all_eight_reserved_before_first_draw': True,
                  'restart_or_refund_authorized': False, 'scientific_allocation_charged': False}
    write(OUT/'allocation.json', allocation)
    inputs = [*PINS, PROPOSAL, SCOPE, BASE+'/plans.json', BASE+'/identity_inventory.json',
              BASE+'/allocation.json', 'tests/test_radio_native_chain_engineering.py',
              BASE+'/preflight_tests.log']
    freeze = capture(ROOT, inputs); write(OUT/'runtime_freeze.json', freeze)
    print(json.dumps({'freeze_sha256': digest(freeze), 'code_files': len(freeze['code_sha256s']),
                      'runtime_files': len(freeze['runtime_sha256s']), 'new_random_values': 0}))


def run(commit, freeze_sha):
    started = time.monotonic(); target = OUT/'live01'; target.mkdir(exist_ok=False)
    lease = None; rows = []; units = []; threshold = None; store = None
    git_calls = 0; completed_draws = 0
    def budget():
        if time.monotonic()-started > 2010: raise TimeoutError('Whole live bound exceeded')
        if store is not None:
            ledger = sum(p.stat().st_size for p in (target/'journal').rglob('*') if p.is_file())
            if ledger > CAPS['ledger_reserve_bytes']: raise ValueError('Complete original journal history exceeds 8 MiB')
        if sum(p.stat().st_size for p in target.rglob('*') if p.is_file()) > CAPS['evidence_bytes']:
            raise ValueError('Whole uncompressed evidence budget exceeded')
    try:
        intent_raw = subprocess.check_output(['git','show',commit+':'+BASE+'/consumption_intent.json'],cwd=ROOT)
        git_calls += 1; intent = json.loads(intent_raw)
        if (intent.get('namespace') != e.NAMESPACE or intent.get('allocation_irrevocably_reserved') is not True
                or intent.get('restart_authorized') is not False or intent.get('freeze_sha256') != freeze_sha
                or intent.get('case_count') != 8):
            raise ValueError('Exact immutable eight-case public reservation required')
        verifier = PublishedFreeze(ROOT, intent['freeze_commit'], BASE+'/runtime_freeze.json', freeze_sha)
        git_calls += 2
        plans = json.loads((OUT/'plans.json').read_bytes()); allocation = json.loads((OUT/'allocation.json').read_bytes())
        if digest(allocation) != intent['allocation_sha256']: raise ValueError('Allocation differs')
        manifest = {'schema': j.SCHEMA, 'mode': 'engineering', 'namespace': e.NAMESPACE,
                    'execution_binding_sha256': freeze_sha, 'allocation_sha256': digest(allocation),
                    'cases': allocation['cases'], 'caps': CAPS, 'required_artifacts': e.ARTIFACTS}
        def verify(m):
            nonlocal git_calls
            # verify() performs exactly one local git ls-files invocation.
            git_calls += 1
            if git_calls > 16: raise ValueError('Live local Git cap exceeded')
            return verifier.verify(m)
        write(target/'preflight.json', {**verify(manifest), 'public_consumption_commit': commit,
                                       'intent_sha256': hashlib.sha256(intent_raw).hexdigest()})
        store = j.DirectoryStore.create(target/'journal', manifest)
        forbidden = json.loads((ROOT/PROPOSAL).read_bytes())['cases']; c = context('validation')
        def deadline(signum, frame): raise TimeoutError('Fixed engineering case deadline')
        signal.signal(signal.SIGALRM, deadline)
        for i, plan in enumerate(plans):
            budget(); before = store.read(); signal.setitimer(signal.ITIMER_REAL, CASE_MS/1000)
            lease = j.consume(store, expected_revision=before.revision, expected_manifest_sha256=digest(manifest),
                    binding=e.binding(plan), milliseconds=CASE_MS, artifact_bytes=CASE_BYTES, directory=target/f'case{i}')
            stage = {}; t = time.monotonic()
            native_run, receipt = e.render(c, plan, lease=lease, forbidden_cases=forbidden, verify_freeze=verify)
            completed_draws += 6*16*65536
            stage['render_seconds'] = time.monotonic()-t; t = time.monotonic()
            scores = native_run.build_store(); native_run.validate_store(scores); lease.budget(native_run.modelled_bytes)
            stage['score_seconds'] = time.monotonic()-t; t = time.monotonic()
            parts = gaussian.compact_parts(native_run, scores, plan, receipt)
            for name, data in parts.items(): lease.write_artifact(name, data)
            pins = {k: hashlib.sha256(v).hexdigest() for k,v in parts.items()}
            audit = compact.audit(c, {k:v for k,v in e.binding(plan).items() if k!='role'}, parts,
                                  expected_sha256s=pins, byte_cap=18*1024**2)
            lease.write_artifact('compact_audit.json', canonical(audit))
            unit = CadenceMaximum(parts['maximum.json'])
            stage['archive_audit_seconds'] = time.monotonic()-t; t = time.monotonic()
            if i < 4:
                units.append(unit)
                report = {'status': 'REFERENCE_ONLY_NO_PHYSICAL_EVALUATION', 'case_identity': plan['case']['identity']}
                gate = {'status': 'REFERENCE_ONLY_NO_GATE', 'scientific_candidate': False}
            else:
                report = e.run_physical(native_run, scores, threshold, plan)
                gate = e.evaluate(report, c, plan)
            # Exact uncompressed physical evidence is retained, including every member.
            lease.write_artifact('physical.json', canonical(report))
            lease.write_artifact('engineering_gate.json', canonical(gate))
            stage['physical_and_gate_seconds'] = time.monotonic()-t
            budget(); cp = lease.finish(); signal.setitimer(signal.ITIMER_REAL, 0)
            state = j.replay(cp.document)['cases'][i]
            rows.append({'ordinal': i, 'name': plan['case']['spec']['name'], 'case_identity': plan['case']['identity'],
                         'status': state['status'], 'elapsed_milliseconds': state['elapsed_milliseconds'],
                         'stage_seconds': stage, 'maximum': unit.record()['maximum'],
                         'artifact_bytes': sum(v['size'] for v in state['artifacts'].values()),
                         'engineering_gate_pass': gate.get('engineering_gate_pass'), 'counts': gate.get('counts'),
                         'retained_on': len(report.get('retention',{}).get('retained',{}).get('on',[])),
                         'retained_off': len(report.get('retention',{}).get('retained',{}).get('off',[])),
                         'archive_check': j.verify_archive(cp,target/f'case{i}',case_index=i)})
            print(json.dumps(rows[-1]), flush=True); lease = None
            if i == 3:
                threshold = e.bind_threshold(c, units); write(target/'threshold.json', threshold.record())
            del native_run, scores, receipt, parts, report, gate, audit
            gc.collect()
        verify(manifest); budget()
        status = 'CLOSED_ENGINEERING_PASS' if all(r['engineering_gate_pass'] for r in rows[4:]) else 'CLOSED_ENGINEERING_GATE_FAILURE'
        result = {'schema': 'radio-native-chain-engineering-result-v1', 'status': status, 'cases': rows,
                  'new_gaussian_values': completed_draws, 'normal_calls': 768, 'elapsed_seconds': time.monotonic()-started,
                  'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                  'live_local_git_invocations': git_calls, 'live_remote_calls': 0,
                  'original_journal_history_bytes': sum(p.stat().st_size for p in (target/'journal').rglob('*') if p.is_file()),
                  'uncompressed_live_bytes_before_result': sum(p.stat().st_size for p in target.rglob('*') if p.is_file()),
                  'public_consumption_commit': commit, 'freeze_sha256': freeze_sha,
                  'journal_state': j.replay(store.read().document), 'threshold_sha256': digest(threshold.record()),
                  'all_eight_allocation_remains_spent': True, 'retry_authorized': False,
                  'scientific_allocation_charged': False, 'telescope_values_opened': False,
                  'production_127_24_activated': False, 'production_physical_gate_qualified': False,
                  'per_artifact_remote_publication_qualified': False,
                  'source_arrays_restorable_from_compact_archive': False}
        write(target/'result.json', result); budget()
        print(json.dumps({k:v for k,v in result.items() if k not in ('cases','journal_state')}, indent=2), flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        failure = {'status': 'CLOSED_ENGINEERING_EXECUTION_FAILURE', 'error': repr(error), 'traceback': traceback.format_exc(),
                   'completed_cases': rows, 'completed_render_gaussian_values': completed_draws,
                   'partial_render_may_have_consumed_additional_values': True,
                   'elapsed_seconds': time.monotonic()-started, 'live_local_git_invocations': git_calls,
                   'all_eight_allocation_remains_spent': True, 'retry_authorized': False}
        # Preserve accumulated physical/retention evidence without calling the failed computation again.
        if hasattr(error, 'evidence'): write(target/'partial_physical_or_retention.json', error.evidence)
        if lease and not lease.closed and not lease.broken:
            try: lease.finish('failed', repr(error))
            except BaseException as nested: failure['finish_error'] = repr(nested)
        write(target/'error.json', failure); raise


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run'])
    p.add_argument('--consumption-commit');p.add_argument('--freeze-sha256');a=p.parse_args()
    if a.action=='prepare': prepare()
    elif not a.consumption_commit or not a.freeze_sha256: p.error('Immutable reservation and freeze required')
    else: run(a.consumption_commit,a.freeze_sha256)
