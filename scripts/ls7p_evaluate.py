#!/usr/bin/env python3
"""Fixed pixel-moment reconstruction, CR attribution and calibration response."""
import gzip
import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np
from astropy.io import fits

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from seti_repeater.tess_pixel_centroid import moments, additive_shift, cr_additions
from seti_repeater.tess_prf_response import PRFCatalog
from ls7o_reference_metadata import save, sha
from ls7p_acquire import table_dtype

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls7p_response'


def stats(value):
    a = np.asarray(value, float).ravel(); a = a[np.isfinite(a)]
    return {'finite_values': len(a), 'minimum': float(a.min()) if len(a) else None,
            'median': float(np.median(a)) if len(a) else None,
            'p95': float(np.quantile(a, .95)) if len(a) else None,
            'maximum': float(a.max()) if len(a) else None}


def aggregate(d, select):
    good = select & d['valid']
    count = int(select.sum())
    return {'rows': count, 'valid_moment_rows': int(good.sum()),
            'centroid_within_binary32_bound_rows': int((good & d['reconstruction_within_rounding']).sum()),
            'centroid_difference_pixels': stats(np.linalg.norm(d['centroid_difference_xy'][good], axis=-1)),
            'archive_to_diagonal_error_ratio': stats(d['archive_to_diagonal_error_ratio_xy'][good]),
            'unknown_correlation_to_diagonal_ratio': stats(d['correlation_bound_xy'][good]/d['sigma_xy'][good]),
            'cr_stamp_rows': int((select & (d['cr_stamp_records'] > 0)).sum()),
            'cr_moment_rows': int((select & (d['cr_moment_records'] > 0)).sum()),
            'cr_optimal_rows': int((select & (d['cr_optimal_records'] > 0)).sum()),
            'cr_shift_pixels': stats(np.linalg.norm(d['cr_shift_xy'][good], axis=-1)),
            'cr_shift_over_processed_diagonal_sigma': stats(abs(d['cr_shift_xy'][good])/d['sigma_xy'][good]),
            'background_restore_shift_pixels': stats(np.linalg.norm(d['background_shift_xy'][good], axis=-1)),
            'background_to_net_flux_ratio': stats(d['background_fraction'][good])}


def groups(d):
    q = d['quality_lc']
    selections = [('all', np.ones(q.shape, bool)), ('quality_zero', q == 0)]
    selections += [(f'bit_{bit}', (q & bit) != 0) for bit in [64, 512, 1024, 4096]]
    selections += [(f'quality_equals_{int(value)}', q == value) for value in np.unique(q) if value]
    return {name: aggregate(d, select) for name, select in selections}


def measurement(record, source):
    sector, tic = record['sector'], record['tic']; key = f's{sector:03d}_tic{tic}'
    raw = gzip.decompress((ROOT/'results_ls7p_inputs'/source['pixel_raw_path']).read_bytes())
    prefix = ROOT/'results_ls7p_metadata'/record['header_prefix']
    h = fits.Header.fromstring(Path(str(prefix)+'_pixels.hdr').read_bytes().decode('ascii'))
    table = np.frombuffer(raw, dtype=table_dtype(h)).reshape(10, 401)
    mask = np.frombuffer(Path(str(prefix)+'_aperture.bin').read_bytes(), dtype='>i4').reshape(record['shape_yx'])
    moment_mask = (mask & 8) != 0; optimal_mask = (mask & 2) != 0
    yy, xx = np.where(moment_mask); xy = np.column_stack([xx, yy])+record['origin_xy']
    shape = (10, 401)+tuple(record['shape_yx'])
    f = table['FLUX'].reshape(shape)[..., moment_mask].astype(float)
    e = table['FLUX_ERR'].reshape(shape)[..., moment_mask].astype(float)
    b = table['FLUX_BKG'].reshape(shape)[..., moment_mask].astype(float)
    m = moments(f, e, xy)
    old = np.load(ROOT/f'results_ls7o_inputs/references_s{sector:03d}.npz', allow_pickle=False)
    j = old['tic'].tolist().index(tic)
    cr_raw = gzip.decompress((ROOT/'results_ls7p_inputs'/source['selected_cr_path']).read_bytes())
    cr_records = list(struct.iter_unpack('>ihhf', cr_raw))
    addition, counts = cr_additions(table['CADENCENO'], cr_records, record['origin_xy'], record['shape_yx'])
    d = addition[..., moment_mask]
    restored = moments(f+d, e, xy)
    with_background = moments(f+b, e, xy)
    cr_shift = restored['center_xy']-m['center_xy']
    background_shift = with_background['center_xy']-m['center_xy']
    difference = m['center_xy']-old['centroid_xy'][j]
    # These are algebraic checks, not claims about the truth of a CR label.
    np.testing.assert_allclose(cr_shift, additive_shift(f, d, xy), atol=2e-11, rtol=1e-9, equal_nan=True)
    np.testing.assert_allclose(background_shift, additive_shift(f, b, xy), atol=2e-11, rtol=1e-9, equal_nan=True)
    np.testing.assert_allclose(moments(2*f, e, xy)['center_xy'], m['center_xy'], atol=2e-11, rtol=0, equal_nan=True)
    output = {'cadence': table['CADENCENO'].astype(np.int64), 'quality_lc': old['quality'][j],
              'quality_tpf': table['QUALITY'].astype(np.int64), 'valid': m['valid'],
              'total': m['total'], 'center_xy': m['center_xy'], 'sigma_xy': m['sigma_xy'],
              'covariance_xy': m['covariance_xy'], 'correlation_bound_xy': m['correlation_unknown_bound_xy'],
              'binary32_bound_xy': m['binary32_centroid_bound_xy'], 'centroid_difference_xy': difference,
              'reconstruction_within_rounding': (abs(difference) <= m['binary32_centroid_bound_xy']).all(-1),
              'archive_to_diagonal_error_ratio_xy': old['error_xy'][j]/m['sigma_xy'],
              'cr_shift_xy': cr_shift, 'background_shift_xy': background_shift,
              'background_fraction': b.sum(-1)/m['total'], 'negative_moment_pixels': (f < 0).sum(-1),
              'cr_stamp_records': counts.sum(axis=(-2, -1)),
              'cr_moment_records': counts[..., moment_mask].sum(-1),
              'cr_optimal_records': counts[..., optimal_mask].sum(-1)}
    np.savez_compressed(OUT/f'{key}.npz', **output)
    flags = output['quality_lc']
    attribution = {'bit64_without_optimal_cr_rows': int((((flags & 64) != 0) & (output['cr_optimal_records'] == 0)).sum()),
                   'optimal_cr_without_bit64_rows': int((((flags & 64) == 0) & (output['cr_optimal_records'] > 0)).sum()),
                   'moment_cr_without_bit64_rows': int((((flags & 64) == 0) & (output['cr_moment_records'] > 0)).sum()),
                   'lc_tpf_quality_different_rows': int((flags != output['quality_tpf']).sum()),
                   'negative_moment_pixel_rows': int((output['negative_moment_pixels'] > 0).sum()),
                   'selected_cr_records': len(cr_records),
                   'moment_pixels': int(moment_mask.sum()), 'optimal_pixels': int(optimal_mask.sum()),
                   'moment_and_optimal_masks_identical': bool(np.array_equal(moment_mask, optimal_mask)),
                   'duplicate_cr_pixel_records': int((counts-1).clip(min=0).sum())}
    return {'sector': sector, 'tic': tic, 'groups': groups(output), 'attribution': attribution}, output


def calibration(cfg, metadata):
    catalog = PRFCatalog(ROOT)
    old = json.loads((ROOT/'results_ls7o_metadata/inventory.json').read_text())
    results = []
    step = cfg['calibration_derivative_step_pixels']
    for r in metadata['references']:
        record = next(v for v in old['references'] if (v['sector'], v['tic']) == (r['sector'], r['tic']))
        source = np.asarray(record['geometry']['nominal_target_detector_xy'])
        mask = np.frombuffer((ROOT/'results_ls7p_metadata'/f'{r["header_prefix"]}_aperture.bin').read_bytes(), dtype='>i4').reshape(r['shape_yx'])
        yy, xx = np.where((mask & 8) != 0)
        # Use stamp-local coordinates to avoid subtraction of large centroids.
        pixels = np.column_stack([xx, yy]).astype(float); source_local = source-r['origin_xy']
        for origin in cfg['calibration_column_offsets']:
            try:
                model, nodes = catalog.local(r['ccd'], source, calibration_column_offset=origin)
            except ValueError as exc:
                if str(exc) not in ['original nonzero shift annotation requires interpretation', 'field position outside the calibration grid']:
                    raise
                results.append({'sector': r['sector'], 'tic': r['tic'], 'column_offset': origin,
                                'available': False, 'reason': str(exc),
                                'cases': [{'shift_xy': shift, 'available': False} for shift in cfg['calibration_shifts_xy']]})
                continue
            def response(delta):
                sample = model.sample(pixels, source_local+delta)
                if not sample.covered.all() or not np.isfinite(sample.flux).all() or sample.flux.sum() <= 0:
                    return None
                return (sample.flux[:, None]*pixels).sum(0)/sample.flux.sum()
            c0 = response(np.zeros(2)); columns = []
            for axis in range(2):
                shift = np.eye(2)[axis]*step
                plus, minus = response(shift), response(-shift)
                columns.append(None if plus is None or minus is None else (plus-minus)/(2*step))
            available = c0 is not None and all(c is not None for c in columns)
            jacobian = np.column_stack(columns) if available else None
            item = {'sector': r['sector'], 'tic': r['tic'], 'column_offset': origin,
                    'calibration_nodes': nodes, 'available': available, 'cases': []}
            if available:
                item.update({'jacobian': jacobian.tolist(), 'singular_values': np.linalg.svd(jacobian, compute_uv=False).tolist(),
                             'condition': float(np.linalg.cond(jacobian)),
                             'unit_response_operator_error': float(np.linalg.norm(jacobian-np.eye(2), 2))})
            for shift in cfg['calibration_shifts_xy']:
                delta = np.asarray(shift); value = response(delta)
                row = {'shift_xy': shift, 'available': value is not None and available}
                if row['available']:
                    measured = value-c0
                    row.update({'centroid_change_xy': measured.tolist(),
                                'unit_mapping_error_pixels': float(np.linalg.norm(measured-delta)),
                                'local_inverse_error_pixels': float(np.linalg.norm(np.linalg.solve(jacobian, measured)-delta))})
                item['cases'].append(row)
            results.append(item)
    return results


def main():
    assert not OUT.exists(), 'refuse completed output overwrite'
    cfg = json.loads((ROOT/'config/ls7p_pixels.json').read_text())
    for path, expected in cfg['input_sha256'].items(): assert sha((ROOT/path).read_bytes()) == expected, path
    meta = json.loads((ROOT/'results_ls7p_metadata/inventory.json').read_text())
    sources = json.loads((ROOT/'results_ls7p_inputs/sources.json').read_text())
    OUT.mkdir()
    records = []; stacks = {29: [], 32: []}
    for r, source in zip(meta['references'], sources['records'], strict=True):
        assert (r['sector'], r['tic']) == (source['sector'], source['tic'])
        report, data = measurement(r, source)
        records.append(report); stacks[r['sector']].append(data)
        print(f's{r["sector"]:03d} TIC {r["tic"]}: {report["groups"]["all"]["centroid_within_binary32_bound_rows"]}/4010 centroid reconstructions within binary32 bound', flush=True)
    sectors = []
    for s, values in stacks.items():
        joined = {k: np.concatenate([d[k].reshape((-1,)+d[k].shape[2:]) for d in values]) for k in values[0]}
        sectors.append({'sector': s, 'groups': groups(joined)})
    models = calibration(cfg, meta)
    assert models == json.loads((ROOT/'results_ls7p_preflight/calibration_response.json').read_text())['models']
    save(OUT/'calibration_response.json', {'models': models,
                                          'interpretation': 'isolated effective PRF and fixed aperture; conditional model response, not native astrometry qualification'})
    save(OUT/'summary.json', {'source_commit': sources['source_commit'], 'evaluation_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                            'reference_products': 12, 'selected_rows': 48120,
                            'pixel_measurement_evaluated': True, 'new_target_corrections': 0,
                            'new_native_prediction_windows': 0, 'new_pulse_transfer_cases': 0,
                            'quality_policy_changed': False, 'sectors': sectors, 'references': records})
    paths = sorted(p for p in OUT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT)}\n' for p in paths))


if __name__ == '__main__': main()
