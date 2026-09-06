#!/usr/bin/env python3
"""Frozen M43M inventory expansion through the unchanged M43H source gate."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError

import numpy as np
from m43g_reference import sorted_reference
from seti_repeater import source_m43h as src
from seti_repeater import transport_m43h as net

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43m_epoch_sources'
CONFIG = ROOT / 'config/m43m_epoch_sources.json'


def transient(error):
    if isinstance(error, HTTPError):
        return error.code in (408, 429) or 500 <= error.code <= 599
    if isinstance(error, URLError):
        return isinstance(error.reason, (TimeoutError, ConnectionError))
    return isinstance(error, (TimeoutError, ConnectionError))


def frozen():
    cfg = json.loads(CONFIG.read_text())
    for path, expected in cfg['pinned_sha256'].items():
        if src.file_hash(ROOT / path) != expected:
            raise ValueError('M43M frozen input changed: ' + path)
    _, contract, _, _ = src.frozen_inputs(ROOT)
    if contract != cfg['source_contract_sha256']:
        raise ValueError('M43H source contract changed')
    return cfg, src.file_hash(CONFIG)


def restart_gate(first, second, detail, counters):
    if first['receipt_sha256'] != second['receipt_sha256']:
        raise ValueError('restart source identity changed')
    if detail['resumed_rows'] != 16:
        raise ValueError('restart failed to reuse all rows')
    if any(counters[k] != 0 for k in ('range_attempts', 'range_completed', 'accepted_range_bytes')):
        raise ValueError('finished restart downloaded new ranges')


def delta(before):
    return {key: net.COUNTERS[key] - value for key, value in before.items()}


def one(work_root, label):
    cfg, contract = frozen()
    if label not in cfg['new_scans']:
        raise ValueError('scan outside M43M inventory')
    window = cfg['window']
    directory = work_root / 'live' / label / window
    attempts = []
    start = time.monotonic()
    for number in range(1, cfg['maximum_source_attempts'] + 1):
        before = dict(net.COUNTERS)
        record = {'scan': label, 'window': window, 'attempt': number}
        print(json.dumps({'begin': label, 'attempt': number}), flush=True)
        try:
            receipt, detail = src.extract_remote(ROOT, label, window, directory,
                work_root / 'mirrors', spectral_access_authorized=True)
            for row in range(16):
                native = np.load(directory / f'row{row:02d}.native.npy', allow_pickle=False, mmap_mode='r')
                actual = np.load(directory / f'row{row:02d}.normalized.npy', allow_pickle=False, mmap_mode='r')
                expected = sorted_reference(native[::-1].reshape(1, -1))[0]
                if actual.dtype != expected.dtype:
                    raise ValueError('normalization dtype differs')
                np.testing.assert_array_equal(actual, expected)
            restart_before = dict(net.COUNTERS)
            second, resumed = src.extract_remote(ROOT, label, window, directory,
                work_root / 'mirrors', spectral_access_authorized=True)
            restart_counts = delta(restart_before)
            restart_gate(receipt, second, resumed, restart_counts)
            receipt_path = OUT / f'{label}_{window}.telescope-source.json'
            plan_path = OUT / f'{label}_{window}.range-plan.json'
            src.atomic_json(receipt_path, receipt)
            plan_sha = src.old_transport.publish_range_plan(plan_path, detail['range_plan'])
            # Verify exact legacy encoding against the source receipt's proof.
            if plan_sha != receipt['transport']['range_plan_file_sha256']:
                raise ValueError('published range-plan bytes differ')
            record.update(status='telescope-source-attested', source_receipt_sha256=receipt['receipt_sha256'],
                receipt_path=str(receipt_path.relative_to(ROOT)), range_plan_file_sha256=plan_sha,
                telescope_rows=16, sorted_reference_rows_exact=16, resumed_rows=detail['resumed_rows'],
                finished_restart_rows=resumed['resumed_rows'], finished_restart_counters=restart_counts)
        except Exception as error:
            record.update(status='source-attempt-failed', error_type=type(error).__name__, reason=str(error),
                transient=transient(error), committed_partial_row_receipts=len(list(directory.glob('row??.json'))))
        record['transport_counters'] = delta(before)
        attempts.append(record)
        result = src.seal({'milestone': 'M43M', 'config_sha256': contract, 'scan': label,
            'status': record['status'], 'attempts': attempts, 'elapsed_seconds': time.monotonic() - start}, 'result_sha256')
        src.atomic_json(OUT / f'{label}.json', result)
        print(json.dumps(record), flush=True)
        if record['status'] == 'telescope-source-attested':
            return 0
        if not record['transient']:
            break
    return 1


def run(work_root):
    cfg, _ = frozen()
    OUT.mkdir(exist_ok=True)
    def launch(label):
        return subprocess.run([sys.executable, __file__, '--work-root', str(work_root), '--scan', label]).returncode
    with ThreadPoolExecutor(max_workers=cfg['parallel_sources']) as pool:
        codes = list(pool.map(launch, cfg['new_scans']))
    return int(any(codes))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work-root', type=Path, required=True)
    parser.add_argument('--scan')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    sys.exit(one(args.work_root, args.scan) if args.scan else run(args.work_root))
