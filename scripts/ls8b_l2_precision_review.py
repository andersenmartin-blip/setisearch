#!/usr/bin/env python3
"""Post-failure 60-decimal reference; original LS8B values/tolerances stay fixed."""
import gzip
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
from ls8a_l2_audit import parse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8b_l2_suite'


def median(values):
    values = sorted(values)
    n = len(values)
    return values[n//2] if n % 2 else (values[n//2-1] + values[n//2]) / 2


def reference(xs, side_flux, side_error, xe, event_flux):
    """Same OLS definition, exact conversion of input binary64, 60 decimal digits."""
    with localcontext() as context:
        context.prec = 60
        D = lambda x: Decimal.from_float(float(x))
        x, y, e, xt, yt = [list(map(D, values)) for values in [xs, side_flux, side_error, xe, event_flux]]
        n = Decimal(len(x))
        sx, sy = sum(x), sum(y)
        sxx, sxy = sum(a*a for a in x), sum(a*b for a, b in zip(x, y))
        determinant = n*sxx - sx*sx
        intercept = (sy*sxx - sx*sxy) / determinant
        slope = (n*sxy - sx*sy) / determinant
        residuals = [b-intercept-slope*a for a, b in zip(x, y)]
        med = median(residuals)
        sigma = max(D(1.4826)*median([abs(r-med) for r in residuals]), median(e),
                    D(1e-12)*abs(median(y)), D(1e-12))
        excess = sum(b-intercept-slope*a for a, b in zip(xt, yt))
        d, tx = Decimal(len(xt)), sum(xt)
        leverage = (d*d*sxx - 2*d*tx*sx + tx*tx*n) / determinant
        denominator = sigma * (d+leverage).sqrt()
        return {'score': float(excess/denominator), 'excess_electrons': float(excess),
                'sigma_electrons': float(sigma), 'denominator_electrons': float(denominator)}


def main():
    suite = json.loads((OUT/'summary.json').read_text())
    assert suite['status'] == 'COMPLETE_AUDIT_FAILED'
    failures, ledgers = [], []
    differences = {k: 0. for k in ['score', 'excess_electrons', 'sigma_electrons', 'denominator_electrons']}
    decision_changes = 0
    for visit in suite['visits']:
        directory = OUT / visit['file_key']
        data = parse((directory/'lightcurve_table.bin').read_bytes())
        rows = [json.loads(line) for line in gzip.decompress((directory/'ledger.jsonl.gz').read_bytes()).splitlines()]
        for row in rows:
            i, d = row['start'], row['duration']
            side = np.r_[np.arange(i-14, i-2), np.arange(i+d+2, i+d+14)]
            event = np.arange(i, i+d)
            t0 = float(np.mean(data['bjd'][event]))
            xs = (data['bjd'][side]-t0)*86400.
            xe = (data['bjd'][event]-t0)*86400.
            computed = reference(xs, data['flux'][side], data['err'][side], xe, data['flux'][event])
            for field, value in computed.items():
                differences[field] = max(differences[field], abs(value-row[field]))
                if not math.isclose(value, row[field], rel_tol=2e-8, abs_tol=2e-10):
                    failures.append({'file_key': visit['file_key'], 'start': i, 'duration': d,
                                     'field': field, 'producer': row[field], 'decimal_reference': value,
                                     'difference': row[field]-value})
            decision_changes += int((computed['score'] >= 8.5) != (row['score'] >= 8.5))
            decision_changes += int((computed['score'] <= -8.5) != (row['score'] <= -8.5))
            ledgers.append({'file_key': visit['file_key'], 'start': i, 'duration': d, **computed})
    (OUT/'decimal_reference.jsonl.gz').write_bytes(gzip.compress(''.join(
        json.dumps(r, sort_keys=True) + '\n' for r in ledgers).encode(), mtime=0))
    summary = {'status': 'POST_FAILURE_DIAGNOSTIC_COMPLETE', 'decimal_digits': 60,
               'window_count': len(ledgers), 'changed_signed_threshold_decisions': decision_changes,
               'maximum_absolute_differences_from_frozen_producer': differences,
               'disagreements_at_unchanged_frozen_tolerance': failures,
               'original_science_ledger_modified': False, 'original_frozen_audit_status': 'FAIL',
               'interpretation': 'Numerical cancellation diagnosis only; does not waive the frozen failed gate.'}
    (OUT/'precision_review.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
