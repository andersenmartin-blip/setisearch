"""One finite serial BW continuation; stop and preserve evidence on any failure.

This controller never changes search rules. Every production and independent
review child is observed through the frozen exact-exit/EOF capture mechanism.
There is no retry, overwrite, resume, or alternate archive-access path.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os
import sys
import time
import traceback

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_stage as stage

REVIEW_SOURCE = HERE / 'review/audit_partial_bw.py'
REVIEW_CAPTURE = HERE / 'audit_execution'
SERIAL_RESULT = stage.EXECUTION / 'SERIAL_RUN_RESULT.json'
SERIAL_START = stage.EXECUTION / 'SERIAL_RUN_START.json'
AUDIT_CAPS = {'wall_seconds': 120, 'cpu_seconds': 120,
              'rss_bytes': 2 * 1024**3, 'stored_bytes': 128 * 1024**2}


def audit_worker(batch):
    """No numerical implementation here; import the independent review only."""
    stage.require(type(batch) is int and 1 <= batch <= stage.BATCH_COUNT,
                  'Review batch must be 1')
    output = REVIEW_CAPTURE / f'batch{batch}' / 'payload'
    output.mkdir(exist_ok=False)
    archive = stage.archive_tools()
    result = {'schema': 'SETI_BW_INDEPENDENT_CAPTURE_RESULT_V1',
              'status': 'FAIL', 'batch': batch, 'errors': []}
    try:
        _, sources, inputs = stage.binding_pins()
        stage.require(str(Path(__file__).resolve()) in sources and str(REVIEW_SOURCE) in sources,
                      'Controller and independent reviewer must be source-pinned')
        before_sources = stage.checked_bindings(archive, sources)
        before_inputs = stage.checked_bindings(archive, inputs)
        audit = stage.module_at('bw_standalone_independent_reviewer', REVIEW_SOURCE)
        value = audit.audit(stage.PLAN, stage.ISOLATION / f'batch{batch}' / 'contents',
                            check_normalization=batch == 1)
        stage.require(value.get('status') == 'PASS_BOUNDED_INDEPENDENT_REVIEW',
                      'Independent bounded review did not pass')
        published = archive.save_json(output / 'INDEPENDENT_REVIEW.json', value)
        result['review'] = published
        result['review_status'] = value['status']
        stage.require(stage.checked_bindings(archive, sources) == before_sources,
                      'Sources changed during independent review')
        stage.require(stage.checked_bindings(archive, inputs) == before_inputs,
                      'Inputs changed during independent review')
        result['source_and_input_pins_unchanged'] = True
        result['status'] = 'PASS'
    except BaseException as exc:
        result['errors'].append({'error': type(exc).__name__ + ': ' + str(exc),
                                 'traceback': traceback.format_exc()})
    result['completed_utc'] = datetime.now(timezone.utc).isoformat()
    published = archive.save_json(output / 'RESULT.json', result)
    print(json.dumps({'event': 'GATE_TERMINAL_EOF', 'status': result['status'],
                      'result_sha256': published['sha256']}), flush=True)
    return 0 if result['status'] == 'PASS' else 1


def run_audit(batch, sources, overall_deadline):
    capture = stage.module_at('bw_independent_exact_capture', stage.CAPTURE_SOURCE)
    REVIEW_CAPTURE.mkdir(mode=0o700, exist_ok=True)
    folder = REVIEW_CAPTURE / f'batch{batch}'
    resultpath = folder / 'payload/RESULT.json'
    receipt = capture.capture_child(
        [sys.executable, str(Path(__file__).resolve()), '--audit-worker', '--batch', str(batch)],
        folder, resultpath, AUDIT_CAPS, sources,
        {'stage': 'BW', 'batch': batch, 'operation': 'independent_saved_output_review'},
        stdout_limit=1024*1024, poll_seconds=.1,
        group={'storage_roots': stage.storage_roots(),
               'stored_bytes': stage.OVERALL_STORED_BYTES,
               'deadline_monotonic': overall_deadline})
    stage.require(receipt['status'] == 'PASS', 'Independent review capture failed; no retry')
    stage.require(stage.sha(resultpath) == receipt['result_sha256'], 'Review wrapper result changed')
    wrapped = stage.read(resultpath)
    reviewpath = folder / 'payload/INDEPENDENT_REVIEW.json'
    stage.require(stage.sha(reviewpath) == wrapped['review']['sha256'], 'Independent review bytes changed')
    review = stage.read(reviewpath)
    stage.require(review['status'] == 'PASS_BOUNDED_INDEPENDENT_REVIEW', 'Independent review status differs')
    target = HERE / f'review/BATCH{batch}_INDEPENDENT_REVIEW.json'
    archive = stage.archive_tools()
    published = archive.save_json(target, review)
    stage.require(published['sha256'] == wrapped['review']['sha256'], 'Published review differs from captured bytes')
    stage.require(time.monotonic() <= overall_deadline, 'Overall wall cap exceeded after independent review')
    capture.verify_pins(sources)
    return receipt, review, published


def run_all():
    started = time.monotonic()
    deadline = started + stage.OVERALL_RUNTIME_WALL_SECONDS
    plan, sources, inputs = stage.binding_pins()
    stage.require(str(Path(__file__).resolve()) in sources and str(REVIEW_SOURCE) in sources,
                  'Serial controller and independent reviewer must be pinned')
    archive = stage.archive_tools()
    stage.checked_bindings(archive, sources)
    stage.checked_bindings(archive, inputs)
    stage.EXECUTION.mkdir(mode=0o700, exist_ok=True)
    stage.require(not SERIAL_START.exists() and not SERIAL_RESULT.exists(),
                  'This serial execution identity was already used; no retry or resume')
    stage.require(not any((stage.EXECUTION / f'batch{n}').exists() or
                          (stage.ISOLATION / f'batch{n}').exists() or
                          (REVIEW_CAPTURE / f'batch{n}').exists()
                          for n in range(1, stage.BATCH_COUNT + 1)),
                  'Serial run requires entirely unused production and audit identities')
    lock = HERE / '.serial_execution_lock'
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    result = {'schema': 'SETI_BW_SERIAL_RUN_RESULT_V1', 'status': 'FAIL',
              'plan_sha256': stage.sha(stage.PLAN), 'completed_batches': [],
              'planned_batch_count': stage.BATCH_COUNT, 'errors': [],
              'attempted_batches': [],
              'overall_runtime_wall_seconds': stage.OVERALL_RUNTIME_WALL_SECONDS,
              'no_retry_or_resume': True, 'complete_OFF_support': False,
              'original_coverage_credit': 0}
    try:
        os.write(descriptor, (str(os.getpid())+'\n').encode()); os.fsync(descriptor)
        archive.save_json(SERIAL_START, {'schema': 'SETI_BW_SERIAL_START_V1',
            'started_utc': datetime.now(timezone.utc).isoformat(),
            'plan_sha256': result['plan_sha256'], 'batch_q_lists': plan['batch_q_lists'],
            'overall_runtime_wall_seconds': stage.OVERALL_RUNTIME_WALL_SECONDS})
        for batch, qs in enumerate(plan['batch_q_lists'], 1):
            stage.require(time.monotonic() < deadline, 'Overall finite wall budget exhausted')
            result['attempted_batches'].append(batch)
            print(json.dumps({'event': 'BW_BATCH_START', 'batch': batch, 'q_list': qs,
                              'completed_batches': len(result['completed_batches'])}), flush=True)
            code = stage.run_parent(batch, overall_deadline=deadline)
            stage.require(code == 0, 'Production batch failed; serial execution stops without retry')
            capture, review, published = run_audit(batch, sources, deadline)
            record = {'batch': batch, 'q_list': qs, 'production_status': 'PASS',
                      'independent_capture_status': capture['status'],
                      'independent_review_status': review['status'],
                      'independent_review_sha256': published['sha256'],
                      'ON_seed_rows': review['ON_seed_rows_all_semantically_reviewed'],
                      'status_counts': review['status_counts'],
                      'elapsed_seconds': time.monotonic()-started}
            result['completed_batches'].append(record)
            print(json.dumps({'event': 'BW_BATCH_COMPLETE', **record}), flush=True)
        stage.checked_bindings(archive, sources)
        stage.checked_bindings(archive, inputs)
        stage.require(time.monotonic() <= deadline, 'Overall wall cap exceeded at closure')
        result['status'] = 'PASS'
    except BaseException as exc:
        result['errors'].append({'error': type(exc).__name__ + ': ' + str(exc),
                                 'traceback': traceback.format_exc()})
    finally:
        os.close(descriptor)
        lock.unlink()
    result['wall_seconds'] = time.monotonic()-started
    result['completed_utc'] = datetime.now(timezone.utc).isoformat()
    result['all_planned_batches_completed'] = len(result['completed_batches']) == stage.BATCH_COUNT
    published = archive.save_json(SERIAL_RESULT, result)
    print(json.dumps({'event': 'BW_SERIAL_CLOSED', 'status': result['status'],
                      'completed_batches': len(result['completed_batches']),
                      'wall_seconds': result['wall_seconds'],
                      'result_sha256': published['sha256']}), flush=True)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--batch', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    stage.require(args.audit_worker == (args.batch is not None), 'Batch argument is only for a review worker')
    raise SystemExit(audit_worker(args.batch) if args.audit_worker else run_all())
