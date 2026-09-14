#!/usr/bin/env python3
"""Independent raw-file checks and completion report for the LS7K input packet."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def audit(out, cache):
    cfg = json.loads((ROOT / 'config/ls7k_inputs.json').read_text())
    inv = json.loads((out / 'inventory.json').read_text())
    source = json.loads((out / 'source_freeze.json').read_text())
    for name, expected in source['source_sha256'].items():
        assert digest(ROOT / name) == expected
    assert source['source_commit'] == subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    checks, raw_rows, raw_motion, geometry_checks, files_checked = 0, 0, 0, 0, 0
    max_geometry_error = 0.
    datasets = {d['sector']: d for d in json.loads((ROOT / cfg['datasets']).read_text())}
    for record in inv['light_curves']:
        sector = record['sector']
        path = cache / record['name']
        assert digest(path) == record['sha256'] and path.stat().st_size == record['bytes']
        with fits.open(path, memmap=False) as hdus, \
             np.load(out / record['timing_file'], allow_pickle=False) as timing, \
             np.load(ROOT / datasets[sector]['contexts'], allow_pickle=False) as old, \
             np.load(ROOT / cfg['prior_auxiliary'] / f'auxiliary_s{sector:03d}.npz', allow_pickle=False) as aux:
            table, header = hdus[1].data, hdus['APERTURE'].header
            index = np.arange(-200, 201)[None, :] + old['anchors'][:, None]
            np.testing.assert_array_equal(timing['indices'], index)
            for target, field in [('cadence', 'CADENCENO'), ('time_barycentric_btjd', 'TIME'),
                                  ('time_correction_days', 'TIMECORR'), ('quality', 'QUALITY')]:
                np.testing.assert_array_equal(timing[target], np.asarray(table[field])[index])
            np.testing.assert_array_equal(timing['cadence'], old['context_cadence'])
            np.testing.assert_array_equal(timing['time_barycentric_btjd'], aux['time'])
            for column, field in enumerate(['POS_CORR2', 'POS_CORR1']):
                np.testing.assert_array_equal(aux['position_yx'][..., column], np.asarray(table[field])[index])
                raw_motion += index.size
            expected_time = np.array([math.fsum([float(table['TIME'][i]), -float(table['TIMECORR'][i])])
                                      for i in index.ravel()]).reshape(index.shape)
            np.testing.assert_array_equal(timing['time_spacecraft_btjd'], expected_time)
            np.testing.assert_array_equal((hdus['APERTURE'].data & 2) != 0, old['aperture'])
            stored_headers = json.loads((out / record['headers_file']).read_text())['hdus']
            assert len(stored_headers) == len(hdus)
            for stored, hdu in zip(stored_headers, hdus):
                assert len(stored['cards']) == len(hdu.header.cards)
                for saved_card, original in zip(stored['cards'], hdu.header.cards):
                    assert saved_card['key'] == original.keyword and saved_card['comment'] == original.comment
                    v = original.value
                    v = v if isinstance(v, (str, bool, int, float)) else str(v)
                    assert saved_card['value'] == v
            geo = record['geometry']
            if geo['physical_wcs_present']:
                crval = np.array([header['CRVAL1P'], header['CRVAL2P']])
                crpix = np.array([header['CRPIX1P'], header['CRPIX2P']])
                pc = np.array([[header.get(f'PC{i}_{j}P', float(i == j)) for j in [1, 2]] for i in [1, 2]])
                if any(f'CD{i}_{j}P' in header for i in [1, 2] for j in [1, 2]):
                    matrix = np.array([[header.get(f'CD{i}_{j}P', 0.) for j in [1, 2]] for i in [1, 2]])
                else:
                    matrix = np.diag([header['CDELT1P'], header['CDELT2P']]) @ pc
                x = np.array(geo['corners_xy_zero_based']) + 1 - crpix
                expected_world = x @ matrix.T + crval
                error = float(np.max(np.abs(expected_world - np.array(geo['corners_detector_xy']))))
                max_geometry_error = max(error, max_geometry_error)
                assert error < 1e-8
                geometry_checks += len(x)
            raw_rows += index.size
    expected_grid = {(p['sector'], row, col) for p in cfg['products']
                     for row in cfg['prf_rows'] for col in cfg['prf_cols']}
    assert {(r['sector'], r['grid_row'], r['grid_col']) for r in inv['prf_models']} == expected_grid
    assert len(inv['prf_models']) == len(expected_grid) == 50
    for record in inv['prf_models']:
        path = out / record['path']
        if record['status'] != 'downloaded':
            assert record.get('error') and not record['expected_image_pair']
            continue
        assert digest(path) == record['sha256'] and path.stat().st_size == record['bytes']
        with fits.open(path, memmap=False) as hdus:
            hdus.verify('exception')
            assert len(hdus) == len(record['hdus'])
            pair = len(hdus) == 2 and all(h.data is not None and list(h.data.shape) == [117, 117]
                                        and np.isfinite(h.data).all() for h in hdus)
            assert bool(pair) == record['expected_image_pair']
            for hdu, item in zip(hdus, record['hdus']):
                if hdu.data is not None:
                    data = np.asarray(hdu.data, dtype=float)
                    info = item['array']
                    assert list(data.shape) == info['shape'] and data.size == info['values']
                    assert np.isfinite(data).sum() == info['finite']
                    finite = data[np.isfinite(data)]
                    assert (finite < 0).sum() == info['negative']
                    assert float(finite.min()) == info['min'] and float(finite.max()) == info['max']
                    np.testing.assert_allclose(math.fsum(finite.ravel()), info['sum'], rtol=1e-12, atol=1e-12)
        files_checked += 1
    for base, manifest in cfg['preserve_manifests']:
        for line in (ROOT / base / manifest).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            assert digest(ROOT / base / name.strip()) == expected, name
            checks += 1
    assert not subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, text=True).strip()
    assert raw_rows == inv['timing_rows'] == 8020 and raw_motion == 16040
    assert files_checked == inv['restored_prf_models']
    assert checks == inv['preserved_manifest_entries']
    result = {'audit_pass': True, 'raw_timing_rows': raw_rows,
              'timing_and_quality_scalar_checks': 5 * raw_rows, 'raw_motion_scalar_checks': raw_motion,
              'prf_files_checked': files_checked, 'physical_wcs_corner_checks': geometry_checks,
              'physical_wcs_max_abs_error_pixels': max_geometry_error,
              'preserved_manifest_entries': checks,
              'historical_tracked_files_unchanged': True,
              'engineering_time_series_audited': False,
              'scientific_detector_qualification': False}
    save(out / 'AUDIT.json', result)
    print(json.dumps(result, indent=2), flush=True)
    report = [
        '# LS7K instrument-response input inventory', '',
        'Completed 14 September 2026. This is a checked input packet for the same closed sectors.', '',
        f"**{raw_rows:,} timing rows and {files_checked}/50 PRF files restored; raw-input audit PASS.**",
        f"Expected finite 117-by-117 primary/uncertainty pairs: **{inv['expected_prf_image_pairs']}/50**.",
        'No response was fitted or detector evaluated.', '',
        '| Sector | Camera/CCD | Timing rows | TIMECORR range (seconds) | Nominal detector x/y |',
        '|---|---|---:|---:|---|'
    ]
    for record in inv['light_curves']:
        correction = record['time_correction_seconds']
        xy = record['geometry'].get('nominal_target_detector_xy')
        xy_text = ', '.join(f'{v:.6f}' for v in xy) if xy is not None else 'unresolved'
        report.append(f"| {record['sector']} | {record['camera']}/{record['ccd']} | {record['selected_rows']} | "
                      f"{correction['min']:.6f} to {correction['max']:.6f} | {xy_text} |")
    engineering = inv['engineering']
    report.extend([
        '', 'Timing extracts include original TIME, TIMECORR, their spacecraft-time difference,',
        'cadence IDs and quality values. Full FITS headers preserve the time and WCS conventions.',
        'The raw light-curve bytes match LS7J, including every reused motion value.',
        'This does not identify a timing defect in LS7J, which already used the same cadence IDs.',
        '', f"Engineering index status: **{engineering['status']}**; "
        f"**{len(engineering['selected_links'])}** matching sector-29/32 links recorded.",
        'These are an availability inventory. No engineering samples or time-reference claims',
        'are included in this stage.', '',
        'PRFs are preserved as original FITS files in prf/. SHA-256 identifies every acquired',
        'file. The complete inventory includes failed retrievals, image dimensions, finite and',
        'negative counts, normalization diagnostics and headers. No array was shifted, clipped,',
        'normalized or chosen using a signal/control outcome.', '',
        'The [provenance assessment](../LS7K_PROVENANCE.md) supplies primary references and the',
        'remaining response contract: coordinate conventions, temporal averaging, calibration',
        'uncertainty and upstream target dependence. The configured grid covers both CCDs without',
        'claiming a verified calibration-to-science coordinate conversion.', '',
        'Next prepare a separately specified coordinate/PRF forward-model benchmark using these',
        'closed inputs. Resolve the 44-column convention and subpixel layout from actual headers',
        'before applying a model; expose any unverified motion-estimator assumptions.',
        'LS7J remains closed. There is no new candidate, observing coverage or unused-data study.',
        '', '## Reproducibility', '',
        f"Source freeze: {source['source_commit']}.",
        f"Execution: [GitHub run {source['github_run_id']}](https://github.com/andersenmartin-blip/setisearch/actions/runs/{source['github_run_id']}).",
        '', '[Protocol](../LS7K_INPUT_PROTOCOL.md), [complete inventory](inventory.json),',
        '[audit](AUDIT.json), [source checksums](source_freeze.json), [result checksums](SHA256SUMS).',
        'The audit independently reopens both old light curves, compares 16,040 motion values,',
        'recomputes the timing subtraction, checks the physical WCS by direct arithmetic,',
        'and verifies all acquired PRFs and the historical manifests.'
    ])
    (out / 'REPORT.md').write_text('\n'.join(report) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='results_ls7k_inputs')
    p.add_argument('--cache', default='data_ls7k_inputs')
    p.add_argument('--seal', action='store_true')
    args = p.parse_args()
    out = Path(args.output)
    if args.seal:
        paths = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
        (out / 'SHA256SUMS').write_text(''.join(f'{digest(path)}  {path.relative_to(out).as_posix()}\n' for path in paths))
    else:
        audit(out, Path(args.cache))


if __name__ == '__main__':
    main()
