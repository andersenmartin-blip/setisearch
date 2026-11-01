"""Characterize all original selected Voyager hit-stamps; no survey claim."""
from pathlib import Path
import hashlib
import json
import platform
import time

import capnp
import numpy as np

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    started = time.monotonic()
    raw = (ROOT / 'voyager.hits').read_bytes()
    scope = json.loads((ROOT / 'SCOPE_CA_VOYAGER.json').read_text())
    assert hashlib.sha256(raw).hexdigest() == scope['input_sha256']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == scope['source_blob']
    schema = capnp.load(str(ROOT / 'hit.capnp'))
    meta = json.loads((ROOT / 'metadata.json').read_text())
    records = []
    with (ROOT / 'voyager.hits').open('rb') as f:
        for i, hit in enumerate(schema.Hit.read_multiple(f)):
            fb = hit.filterbank
            a = np.array(fb.data, dtype='<f4').reshape(fb.numTimesteps, fb.numChannels)
            assert np.isfinite(a).all()
            assert (a >= 0).all()
            nt, nf = a.shape
            assert a.size == meta[i]['sample_count']
            np.save(ROOT / f'stamp_{i}.npy', a, allow_pickle=False)
            baseline_rows = np.median(a.astype(np.float64), axis=1)
            baseline = float(baseline_rows.sum())
            span = (nt - 1) * fb.tsamp
            seen = set()
            shifts_all = []
            endpoints_all = []
            sums_all = []
            valid_counts = []
            best = None
            best_excess = -np.inf
            for q in range(-8 * (nf - 1), 8 * (nf - 1) + 1):
                endpoint = q / 8
                rate = endpoint * fb.foff * 1e6 / span
                if abs(rate) > 4:
                    continue
                shift = np.rint(np.arange(nt) * q / (8 * (nt - 1))).astype(np.int64)
                key = shift.tobytes()
                if key in seen:
                    continue
                seen.add(key)
                first = max(0, -int(shift.min()))
                stop = min(nf, nf - int(shift.max()))
                starters = np.arange(first, stop)
                if not len(starters):
                    continue
                values = a[np.arange(nt)[:, None], shift[:, None] + starters[None, :]]
                raw_sums = values.astype(np.float64).sum(axis=0)
                excess = raw_sums - baseline
                all_sums = np.full(nf, np.nan)
                all_sums[starters] = raw_sums
                shifts_all.append(shift)
                endpoints_all.append(q)
                sums_all.append(all_sums)
                valid_counts.append(len(starters))
                j = int(np.argmax(excess))
                if excess[j] > best_excess:
                    best_excess = float(excess[j])
                    best = {'endpoint_shift_eighth': q,
                            'endpoint_shift_channels': endpoint,
                            'start_channel': int(starters[j]),
                            'drift_rate_Hz_s': float(rate),
                            'f_start_MHz': float(fb.fch1 + int(starters[j]) * fb.foff),
                            'selected_channels': (shift + starters[j]).tolist(),
                            'raw_sum': float(raw_sums[j]),
                            'excess_sum_above_row_medians': best_excess}
            assert best is not None
            ref = hit.signal.to_dict()
            ref_start = (ref['frequency'] - fb.fch1) / fb.foff
            ref_endpoint = ref['driftRate'] * span / (fb.foff * 1e6)
            errors = {'start_channels': float(best['start_channel'] - ref_start),
                      'start_Hz': float((best['f_start_MHz'] - ref['frequency']) * 1e6),
                      'endpoint_channels': float(best['endpoint_shift_channels'] - ref_endpoint),
                      'drift_Hz_s': float(best['drift_rate_Hz_s'] - ref['driftRate'])}
            consistent = abs(errors['start_channels']) <= 2 and abs(errors['endpoint_channels']) <= 2
            arrays = dict(endpoint_shift_eighth=np.array(endpoints_all, dtype=np.int64),
                          shifts=np.stack(shifts_all), raw_sums=np.stack(sums_all),
                          row_medians=baseline_rows,
                          valid_counts=np.array(valid_counts, dtype=np.int64))
            np.savez_compressed(ROOT / f'search_{i}.npz', **arrays)
            selected_values = a[np.arange(nt), best['selected_channels']].astype(np.float64)
            records.append({'hit': i, 'shape': list(a.shape),
                            'samples': a.size,
                            'sample_min': float(a.min()), 'sample_max': float(a.max()),
                            'negative_samples': int((a < 0).sum()),
                            'nonfinite_samples': int((~np.isfinite(a)).sum()),
                            'zero_samples': int((a == 0).sum()),
                            'filterbank': meta[i]['filterbank'],
                            'reference_signal': ref,
                            'unique_shift_sequences': len(seen),
                            'full_support_track_count': sum(valid_counts),
                            'baseline_sum_row_medians': baseline,
                            'best': best,
                            'selected_row_excess': (selected_values - baseline_rows).tolist(),
                            'rows_above_own_median': int((selected_values > baseline_rows).sum()),
                            'reference_comparison': errors,
                            'within_predeclared_reference_tolerances': bool(consistent),
                            'array_sha256': digest(ROOT / f'stamp_{i}.npy'),
                            'search_arrays_sha256': digest(ROOT / f'search_{i}.npz')})
    assert len(records) == 5
    assert sum(r['samples'] for r in records) == 9344
    assert len({r['filterbank']['tstart'] for r in records}) == 1
    result = {'schema': 'SETI_CA_VOYAGER_CHARACTERIZATION_V1',
              'status': 'COMPLETED_AWAITING_INDEPENDENT_REVIEW',
              'source': {k: scope[k] for k in ('source_repo', 'source_commit', 'source_blob', 'input_sha256')},
              'scope_sha256': digest(ROOT / 'SCOPE_CA_VOYAGER.json'),
              'program_sha256': digest(Path(__file__)),
              'schema_sha256': digest(ROOT / 'hit.capnp'),
              'python': platform.python_version(), 'numpy': np.__version__, 'pycapnp': capnp.__version__,
              'selected_stamps': len(records), 'observations': 1,
              'total_power_samples': sum(r['samples'] for r in records),
              'integration_duration_seconds': records[0]['shape'][0] * records[0]['filterbank']['tsamp'],
              'first_to_last_sample_span_seconds': (records[0]['shape'][0]-1) * records[0]['filterbank']['tsamp'],
              'total_full_support_tracks': sum(r['full_support_track_count'] for r in records),
              'reference_consistent_stamps': sum(r['within_predeclared_reference_tolerances'] for r in records),
              'records': records, 'limitations': scope['limitations'],
              'wall_seconds': time.monotonic() - started}
    (ROOT / 'RESULT_CA_VOYAGER.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k:result[k] for k in ('status','selected_stamps','total_power_samples','total_full_support_tracks','reference_consistent_stamps','wall_seconds')}))
    for r in records:
        print(json.dumps({'hit':r['hit'], 'best':r['best'], 'reference_errors':r['reference_comparison'], 'positive_rows':r['rows_above_own_median']}))


if __name__ == '__main__':
    main()
