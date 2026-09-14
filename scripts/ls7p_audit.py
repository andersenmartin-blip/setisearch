#!/usr/bin/env python3
"""Independent raw-byte/scalar centroid audit and SciPy PRF reconstruction.

No producer, pixel-centroid operator, acquisition parser or PRF operator import.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from ls7o_audit_inputs import header
from ls7l_review_inputs import image_hdus, verify_manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls7p_response'
CHECKS = 0
DIFFERENCES = {}


def read(path): return json.loads(path.read_text())
def sha(raw): return hashlib.sha256(raw).hexdigest()


def close(a, b, label, atol=2e-10, rtol=2e-8):
    global CHECKS
    a, b = np.asarray(a), np.asarray(b)
    np.testing.assert_allclose(a, b, rtol=rtol, atol=atol, equal_nan=True, err_msg=label)
    delta = abs(a.astype(float)-b.astype(float)); delta = delta[np.isfinite(delta)]
    DIFFERENCES[label] = max(DIFFERENCES.get(label, 0), float(delta.max()) if delta.size else 0)
    CHECKS += a.size


def scalar_moment(f, e, xy):
    total = math.fsum(f)
    good = all(math.isfinite(v) for v in f+e) and min(e) > 0 and total > 0
    if not good: return False, math.nan, [math.nan]*2, [math.nan]*2, [[math.nan]*2]*2, [math.nan]*2, [math.nan]*2
    center = [xy[0][k]+math.fsum(v*(p[k]-xy[0][k]) for v, p in zip(f, xy))/total for k in range(2)]
    g = [[(p[k]-center[k])/total for k in range(2)] for p in xy]
    cov = [[math.fsum(s*s*p[k]*p[l] for s, p in zip(e, g)) for l in range(2)] for k in range(2)]
    sigma = [math.sqrt(cov[k][k]) for k in range(2)]
    bound = [math.fsum(s*abs(p[k]) for s, p in zip(e, g)) for k in range(2)]
    rounding = [.5*float(np.spacing(np.float32(abs(v)))) for v in f]
    quant = [math.fsum(u*abs(p[k]-center[k]) for u, p in zip(rounding, xy))/(total-math.fsum(rounding))+2e-11 for k in range(2)]
    return True, total, center, sigma, cov, bound, quant


def unpacker(h):
    names, starts, lengths, codes = [], [], [], []
    index = 0
    for i in range(1, h['TFIELDS']+1):
        repeat, code = re.fullmatch(r'(\d*)([DEJI])', h[f'TFORM{i}']).groups()
        count = int(repeat or '1')
        names.append(h[f'TTYPE{i}']); starts.append(index); lengths.append(count)
        codes.append(str(count)+{'D': 'd', 'E': 'f', 'J': 'i', 'I': 'h'}[code]); index += count
    parser = struct.Struct('>'+''.join(codes))
    assert parser.size == h['NAXIS1']
    return parser, {name: (start, length) for name, start, length in zip(names, starts, lengths)}


def raw_reference(r, receipt):
    key = f's{r["sector"]:03d}_tic{r["tic"]}'
    prefix = ROOT/'results_ls7p_metadata'/r['header_prefix']
    h = header(Path(str(prefix)+'_pixels.hdr').read_bytes())
    hm = header(Path(str(prefix)+'_aperture.hdr').read_bytes())
    hcr = header(Path(str(prefix)+'_cosmic_rays.hdr').read_bytes())
    h0 = header(Path(str(prefix)+'_primary.hdr').read_bytes())
    assert r['table_start'] == len(Path(str(prefix)+'_primary.hdr').read_bytes())+len(Path(str(prefix)+'_pixels.hdr').read_bytes())
    ap_start = r['table_start']+((h['NAXIS1']*h['NAXIS2']+2879)//2880)*2880
    cr_start = ap_start+len(Path(str(prefix)+'_aperture.hdr').read_bytes())+((hm['NAXIS1']*hm['NAXIS2']*4+2879)//2880)*2880+len(Path(str(prefix)+'_cosmic_rays.hdr').read_bytes())
    assert cr_start == r['cosmic_ray_table']['start']
    assert cr_start+((hcr['NAXIS1']*hcr['NAXIS2']+2879)//2880)*2880 == r['product']['bytes']
    assert (h0['SECTOR'], h0['CAMERA'], h0['CCD'], h0['TICID']) == (r['sector'], 4, r['ccd'], r['tic'])
    assert h0['CRMITEN'] is False and h0['CRSPOC'] is True
    assert h['TIMESYS'] == 'TDB' and h['NUM_FRM'] == 10 and h['TIMEPIXR'] == .5
    assert h['1CDL5P'] == h['2CDL5P'] == 1 and h['1CRP5P'] == h['2CRP5P'] == 1
    shape = (hm['NAXIS2'], hm['NAXIS1']); cols = shape[1]
    mask_raw = Path(str(prefix)+'_aperture.bin').read_bytes()
    assert mask_raw == (ROOT/'results_ls7o_metadata'/f'headers/{key}_aperture.bin').read_bytes()
    mask = struct.unpack('>'+str(shape[0]*cols)+'i', mask_raw)
    selected = [i for i, m in enumerate(mask) if m & 8]
    xy = [(i % cols+h['1CRV5P'], i//cols+h['2CRV5P']) for i in selected]
    raw = gzip.decompress((ROOT/'results_ls7p_inputs'/receipt['pixel_raw_path']).read_bytes())
    assert sha(raw) == receipt['pixel_raw_sha256'] and len(raw) == 4010*h['NAXIS1']
    timing = np.load(ROOT/f'results_ls7k_inputs/timing_s{r["sector"]:03d}.npz', allow_pickle=False)
    for anchor, (plan, sent) in enumerate(zip(r['pixel_ranges'], receipt['ranges'][:10], strict=True)):
        assert plan['start'] == r['table_start']+int(timing['indices'][anchor, 0])*h['NAXIS1'] == sent['start']
        assert plan['length'] == sent['length'] == 401*h['NAXIS1'] and sent['etag'] == r['product']['etag']
        assert sha(raw[anchor*sent['length']:(anchor+1)*sent['length']]) == sent['sha256']
    old_prefix = ROOT/'results_ls7o_metadata'/f'headers/{key}'
    lc_h = header(Path(str(old_prefix)+'_lightcurve.hdr').read_bytes())
    lp, lf = unpacker(lc_h)
    lc_raw = gzip.decompress((ROOT/'results_ls7o_inputs'/f'raw/{key}.bin.gz').read_bytes())
    lc_rows = list(lp.iter_unpack(lc_raw)); cadences = {int(row[lf['CADENCENO'][0]]) for row in lc_rows}
    cr_raw = gzip.decompress((ROOT/'results_ls7p_inputs'/receipt['cr_index_raw_path']).read_bytes())
    assert sha(cr_raw) == receipt['cr_index_raw_sha256'] == receipt['ranges'][10]['sha256']
    assert len(cr_raw) == 12*hcr['NAXIS2'] == r['cosmic_ray_table']['length']
    assert receipt['ranges'][10]['start'] == r['cosmic_ray_table']['start']
    chosen = []
    for i in range(hcr['NAXIS2']):
        if struct.unpack_from('>i', cr_raw, 12*i)[0] in cadences: chosen.append(i)
    assert chosen == receipt['selected_cr_index_rows']
    selected_raw = b''.join(cr_raw[i*12:(i+1)*12] for i in chosen)
    assert sha(selected_raw) == receipt['selected_cr_sha256']
    assert selected_raw == gzip.decompress((ROOT/'results_ls7p_inputs'/receipt['selected_cr_path']).read_bytes())
    additions = {}; counts = {}
    for cadence, x, y, value in struct.iter_unpack('>ihhf', selected_raw):
        ix, iy = x-int(h['1CRV5P']), y-int(h['2CRV5P'])
        assert 0 <= ix < cols and 0 <= iy < shape[0] and math.isfinite(value)
        at = iy*cols+ix
        additions.setdefault(cadence, {}).setdefault(at, []).append(value)
        counts.setdefault(cadence, {}).setdefault(at, 0); counts[cadence][at] += 1
    archived = np.load(OUT/f'{key}.npz', allow_pickle=False)
    rebuilt = {k: [] for k in archived.files}
    parser, fields = unpacker(h)
    for values, lc in zip(parser.iter_unpack(raw), lc_rows, strict=True):
        def field(name):
            start, length = fields[name]
            return values[start] if length == 1 else values[start:start+length]
        def old(name): return lc[lf[name][0]]
        cadence = field('CADENCENO')
        assert (cadence, field('TIME'), field('TIMECORR')) == (old('CADENCENO'), old('TIME'), old('TIMECORR'))
        f = [field('FLUX')[i] for i in selected]; e = [field('FLUX_ERR')[i] for i in selected]
        b = [field('FLUX_BKG')[i] for i in selected]
        ok, total, center, sigma, cov, bound, quant = scalar_moment(f, e, xy)
        delta = [math.fsum(additions.get(cadence, {}).get(i, [])) for i in selected]
        restored = scalar_moment([v+d for v, d in zip(f, delta)], e, xy)[2]
        background = scalar_moment([v+d for v, d in zip(f, b)], e, xy)[2]
        difference = [center[k]-old(f'MOM_CENTR{k+1}') for k in range(2)]
        record = {'cadence': cadence, 'quality_lc': old('QUALITY'), 'quality_tpf': field('QUALITY'), 'valid': ok,
                  'total': total, 'center_xy': center, 'sigma_xy': sigma, 'covariance_xy': cov,
                  'correlation_bound_xy': bound, 'binary32_bound_xy': quant, 'centroid_difference_xy': difference,
                  'reconstruction_within_rounding': all(abs(difference[k]) <= quant[k] for k in range(2)),
                  'archive_to_diagonal_error_ratio_xy': [old(f'MOM_CENTR{k+1}_ERR')/sigma[k] for k in range(2)],
                  'cr_shift_xy': [restored[k]-center[k] for k in range(2)],
                  'background_shift_xy': [background[k]-center[k] for k in range(2)],
                  'background_fraction': math.fsum(b)/total,
                  'negative_moment_pixels': sum(v < 0 for v in f),
                  'cr_stamp_records': sum(counts.get(cadence, {}).values()),
                  'cr_moment_records': sum(n for i, n in counts.get(cadence, {}).items() if mask[i] & 8),
                  'cr_optimal_records': sum(n for i, n in counts.get(cadence, {}).items() if mask[i] & 2)}
        for k, value in record.items(): rebuilt[k].append(value)
    for k, values in rebuilt.items():
        a = np.asarray(values).reshape(archived[k].shape)
        if archived[k].dtype.kind in 'biu': close(a, archived[k], k, atol=0, rtol=0)
        else: close(a, archived[k], k, atol=2e-10, rtol=2e-8)
    return {k: np.asarray(v) for k, v in rebuilt.items()}, len(chosen)


def check_groups(d, saved):
    q = d['quality_lc'].astype(int)
    for name, report in saved.items():
        if name == 'all': select = np.ones(q.shape, bool)
        elif name == 'quality_zero': select = q == 0
        elif name.startswith('bit_'): select = (q & int(name[4:])) != 0
        else: select = q == int(name.removeprefix('quality_equals_'))
        good = select & d['valid']; assert int(select.sum()) == report['rows']
        assert int(good.sum()) == report['valid_moment_rows']
        assert int((good & d['reconstruction_within_rounding']).sum()) == report['centroid_within_binary32_bound_rows']
        for kind in ['stamp', 'moment', 'optimal']:
            assert int((select & (d[f'cr_{kind}_records'] > 0)).sum()) == report[f'cr_{kind}_rows']
        vals = {'centroid_difference_pixels': np.linalg.norm(d['centroid_difference_xy'][good], axis=-1),
                'archive_to_diagonal_error_ratio': d['archive_to_diagonal_error_ratio_xy'][good],
                'unknown_correlation_to_diagonal_ratio': d['correlation_bound_xy'][good]/d['sigma_xy'][good],
                'cr_shift_pixels': np.linalg.norm(d['cr_shift_xy'][good], axis=-1),
                'cr_shift_over_processed_diagonal_sigma': abs(d['cr_shift_xy'][good])/d['sigma_xy'][good],
                'background_restore_shift_pixels': np.linalg.norm(d['background_shift_xy'][good], axis=-1),
                'background_to_net_flux_ratio': d['background_fraction'][good]}
        for metric, value in vals.items():
            finite = value.ravel()[np.isfinite(value.ravel())]; r = report[metric]
            assert len(finite) == r['finite_values']
            if len(finite): close([finite.min(), np.median(finite), np.quantile(finite, .95), finite.max()],
                                  [r[k] for k in ['minimum', 'median', 'p95', 'maximum']], 'summary_'+metric, atol=2e-8, rtol=2e-8)
            else: assert all(r[k] is None for k in ['minimum', 'median', 'p95', 'maximum'])


def audit_calibration(cfg, meta):
    inv = read(ROOT/'results_ls7k_inputs/inventory.json'); original = read(ROOT/'results_ls7m_prf_inputs/inventory.json')
    old = read(ROOT/'results_ls7o_metadata/inventory.json')
    images = {(m['ccd'], m['grid_row'], m['grid_col']): image_hdus(ROOT/'results_ls7k_inputs'/m['path'])[0] for m in inv['prf_models']}
    saved = read(OUT/'calibration_response.json')['models']; case_count = 0
    for item in saved:
        r = next(v for v in meta['references'] if (v['sector'], v['tic']) == (item['sector'], item['tic']))
        o = next(v for v in old['references'] if (v['sector'], v['tic']) == (item['sector'], item['tic']))
        field = np.array(o['geometry']['nominal_target_detector_xy']); source = field-r['origin_xy']
        ccd = r['ccd']; ys = sorted({y for c, y, x in images if c == ccd}); xs = sorted({x for c, y, x in images if c == ccd})
        bank = np.array([[images[(ccd, y, x)] for x in xs] for y in ys])
        field = field+[item['column_offset'], 0]
        support_reason = None
        if not (xs[0] <= field[0] <= xs[-1] and ys[0] <= field[1] <= ys[-1]):
            support_reason = 'field position outside the calibration grid'
        else:
            ix = min(max(np.searchsorted(xs, field[0], side='right')-1, 0), len(xs)-2)
            iy = min(max(np.searchsorted(ys, field[1], side='right')-1, 0), len(ys)-2)
            for x in xs[ix:ix+2]:
                for y in ys[iy:iy+2]:
                    entry = next(m for m in original['models'] if (m['ccd'], m['grid_row'], m['grid_col']) == (ccd, y, x))['field_descriptions']
                    if entry['rowShift']['values'] != 0 or entry['columnShift']['values'] != 0:
                        support_reason = 'original nonzero shift annotation requires interpretation'
        if support_reason is not None:
            assert item['available'] is False and item['reason'] == support_reason
            assert [c['shift_xy'] for c in item['cases']] == cfg['calibration_shifts_xy']
            assert not any(c['available'] for c in item['cases'])
            case_count += len(item['cases'])
            continue
        local = RegularGridInterpolator((ys, xs), bank)([field[::-1]])[0]
        desc = next(m for m in original['models'] if m['ccd'] == ccd)['field_descriptions']
        render = RegularGridInterpolator((desc['prfRow']['values'], desc['prfColumn']['values']), local, bounds_error=False, fill_value=np.nan)
        raw = (ROOT/'results_ls7p_metadata'/f'{r["header_prefix"]}_aperture.bin').read_bytes()
        mask = np.array(struct.unpack('>'+str(len(raw)//4)+'i', raw)).reshape(r['shape_yx'])
        y, x = np.where((mask & 8) != 0); pixels = np.column_stack([x, y])
        def centroid(shift):
            f = render((pixels-source-shift)[:, ::-1])
            return np.array([math.fsum((f*pixels[:, k]).tolist())/math.fsum(f.tolist()) for k in range(2)])
        zero = centroid([0., 0.]); step = cfg['calibration_derivative_step_pixels']
        jac = np.column_stack([(centroid(np.eye(2)[k]*step)-centroid(-np.eye(2)[k]*step))/(2*step) for k in range(2)])
        available = np.isfinite(jac).all() and np.isfinite(zero).all()
        assert bool(available) == item['available']
        if available:
            close(jac, item['jacobian'], 'calibration_jacobian', atol=2e-10)
            close(np.linalg.svd(jac, compute_uv=False), item['singular_values'], 'calibration_singular')
            close(np.linalg.cond(jac), item['condition'], 'calibration_condition')
            close(np.linalg.norm(jac-np.eye(2), 2), item['unit_response_operator_error'], 'calibration_unit_error')
        for row in item['cases']:
            change = centroid(row['shift_xy'])-zero
            assert row['available'] == bool(available and np.isfinite(change).all())
            if row['available']:
                close(change, row['centroid_change_xy'], 'calibration_centroid')
                close(np.linalg.norm(change-row['shift_xy']), row['unit_mapping_error_pixels'], 'calibration_unit_mapping')
                close(np.linalg.norm(np.linalg.inv(jac)@change-row['shift_xy']), row['local_inverse_error_pixels'], 'calibration_inverse')
            case_count += 1
    return case_count


def main():
    assert not (OUT/'audit.json').exists(), 'refuse completed audit overwrite'
    cfg = read(ROOT/'config/ls7p_pixels.json')
    for path, expected in cfg['input_sha256'].items(): assert sha((ROOT/path).read_bytes()) == expected, path
    verified = {name: verify_manifest(ROOT/name) for name in cfg['audit_manifests']}
    meta = read(ROOT/'results_ls7p_metadata/inventory.json'); receipts = read(ROOT/'results_ls7p_inputs/sources.json')
    summary = read(OUT/'summary.json'); data = {29: [], 32: []}; cr_total = 0
    for r, receipt, report in zip(meta['references'], receipts['records'], summary['references'], strict=True):
        d, count = raw_reference(r, receipt); cr_total += count; check_groups(d, report['groups'])
        q = d['quality_lc'].astype(int); a = report['attribution']
        assert a['bit64_without_optimal_cr_rows'] == int((((q & 64) != 0) & (d['cr_optimal_records'] == 0)).sum())
        assert a['optimal_cr_without_bit64_rows'] == int((((q & 64) == 0) & (d['cr_optimal_records'] > 0)).sum())
        assert a['moment_cr_without_bit64_rows'] == int((((q & 64) == 0) & (d['cr_moment_records'] > 0)).sum())
        assert a['lc_tpf_quality_different_rows'] == int((q != d['quality_tpf']).sum())
        assert a['negative_moment_pixel_rows'] == int((d['negative_moment_pixels'] > 0).sum())
        assert a['selected_cr_records'] == count
        data[r['sector']].append(d)
        print(f'Independent scalar audit s{r["sector"]:03d} TIC {r["tic"]}: 4010 rows', flush=True)
    for sector in summary['sectors']:
        joined = {k: np.concatenate([v[k] for v in data[sector['sector']]]) for k in data[sector['sector']][0]}
        check_groups(joined, sector['groups'])
    cases = audit_calibration(cfg, meta)
    assert cases == 216 and cr_total == receipts['selected_cr_rows'] and summary['selected_rows'] == 48120
    assert summary['new_target_corrections'] == summary['new_native_prediction_windows'] == summary['new_pulse_transfer_cases'] == 0
    result = {'status': 'PASS', 'raw_pixel_rows': 48120, 'selected_cr_records': cr_total,
              'calibration_cases': cases, 'numeric_comparisons': CHECKS,
              'maximum_absolute_differences': DIFFERENCES, 'verified_manifests': verified,
              'method': 'raw FITS cards and struct rows; scalar fsum moments; independent sparse-cadence filter; raw PRF FITS and SciPy field/spatial interpolation',
              'outside_context_cr_payload_interpreted': False}
    (OUT/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__': main()
