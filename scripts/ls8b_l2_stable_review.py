#!/usr/bin/env python3
"""Retrospective numerical repair on closed LS8B bytes, against Decimal reference."""
import gzip
import hashlib
import json
import math
from pathlib import Path

from ls8a_l2_audit import parse
from seti_repeater.cheops_l2_stable import stable_score_window

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls8b_l2_suite'


def main():
    suite = json.loads((OUT/'summary.json').read_text())
    assert suite['status'] == 'COMPLETE_AUDIT_FAILED'
    decimal = [json.loads(line) for line in gzip.decompress((OUT/'decimal_reference.jsonl.gz').read_bytes()).splitlines()]
    lookup = {(r['file_key'], r['start'], r['duration']): r for r in decimal}
    failures, ledger = [], []
    maximum = {k: 0. for k in ['score', 'excess_electrons', 'sigma_electrons', 'denominator_electrons']}
    decisions = 0
    inputs = {}
    for visit in suite['visits']:
        key = visit['file_key']
        raw = (OUT/key/'lightcurve_table.bin').read_bytes()
        inputs[key] = hashlib.sha256(raw).hexdigest()
        data = parse(raw)
        old = [json.loads(line) for line in gzip.decompress((OUT/key/'ledger.jsonl.gz').read_bytes()).splitlines()]
        old_lookup = {(r['start'], r['duration']): r for r in old}
        new_keys = []
        for duration in (1, 2, 3):
            for start in range(len(data['flux'])-duration+1):
                r = stable_score_window(data['bjd'], data['flux'], data['err'], data['status'],
                                        data['event'], start, duration, visit['cadence_seconds'])
                if r is None:
                    continue
                new_keys.append((start, duration))
                original = old_lookup[(start, duration)]
                reference = lookup[(key, start, duration)]
                for field in maximum:
                    maximum[field] = max(maximum[field], abs(r[field]-reference[field]))
                    if not math.isclose(r[field], reference[field], rel_tol=2e-8, abs_tol=2e-10):
                        failures.append({'file_key': key, 'start': start, 'duration': duration, 'field': field,
                                         'stable': r[field], 'reference': reference[field]})
                decisions += int((r['score'] >= 8.5) != (original['score'] >= 8.5))
                decisions += int((r['score'] <= -8.5) != (original['score'] <= -8.5))
                for field in ['event_indices', 'context_start', 'context_stop', 'event_or', 'context_event_or', 'bjd_mid']:
                    assert r[field] == original[field]
                ledger.append({'file_key': key, **r})
        assert new_keys == [(r['start'], r['duration']) for r in old]
    (OUT/'stable_reference.jsonl.gz').write_bytes(gzip.compress(''.join(
        json.dumps(r, sort_keys=True)+'\n' for r in ledger).encode(), mtime=0))
    result = {'status': 'PASS' if not failures and decisions == 0 else 'FAIL',
              'scope': 'Retrospective arithmetic repair only; not a new held-out evaluation or detector qualification.',
              'original_frozen_audit_status': 'FAIL', 'original_ledger_modified': False,
              'window_count': len(ledger), 'numeric_comparisons': len(ledger)*4,
              'tolerances': {'relative': 2e-8, 'absolute': 2e-10},
              'maximum_absolute_differences_from_decimal': maximum,
              'changed_signed_threshold_decisions': decisions, 'disagreements': failures,
              'input_table_sha256': inputs,
              'source_sha256': hashlib.sha256((ROOT/'src/seti_repeater/cheops_l2_stable.py').read_bytes()).hexdigest()}
    (OUT/'stable_review.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
