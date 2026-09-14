#!/usr/bin/env python3
"""LS7K: restore timing/geometry and inspect calibration, without a detector fit."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def preserve(cfg):
    checks = 0
    for base, manifest in cfg['preserve_manifests']:
        for line in (ROOT / base / manifest).read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            assert sha(ROOT / base / name.strip()) == expected, name
            checks += 1
    assert not git('diff', '--name-only'), 'tracked files changed'
    return checks


def fetch(url, path, cap, timeout):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={'User-Agent': 'SETIsearch-LS7K-input-provenance/1.0'})
    try:
        with urlopen(req, timeout=timeout) as response, path.open('wb') as output:
            declared = response.headers.get('Content-Length')
            if declared is not None and int(declared) > cap:
                raise ValueError('response exceeds fixed byte cap')
            total = 0
            while chunk := response.read(256 * 1024):
                total += len(chunk)
                if total > cap:
                    raise ValueError('response exceeds fixed byte cap')
                output.write(chunk)
            record = {'url': url, 'final_url': response.url, 'bytes': total,
                      'sha256': sha(path), 'http_status': response.status}
        return record
    except Exception:
        path.unlink(missing_ok=True)
        raise


def cards(header):
    return [{'key': c.keyword,
             'value': c.value if isinstance(c.value, (str, bool, int, float)) else str(c.value),
             'comment': c.comment} for c in header.cards]


def stats(array):
    a = np.asarray(array, dtype=float)
    f = a[np.isfinite(a)]
    return {'shape': list(a.shape), 'values': int(a.size), 'finite': int(f.size),
            'negative': int((f < 0).sum()),
            'min': float(f.min()) if f.size else None,
            'max': float(f.max()) if f.size else None,
            'sum': float(f.sum()) if f.size else None}


def geometry(header, shape, ra, dec):
    ny, nx = shape
    corners = np.array([[0, 0], [nx - 1, 0], [0, ny - 1], [nx - 1, ny - 1]], dtype=float)
    result = {'array_shape_yx': list(shape), 'array_axis_order': ['row', 'column'],
              'physical_wcs_present': 'CTYPE1P' in header and 'CTYPE2P' in header,
              'offset_applied': False}
    if result['physical_wcs_present']:
        physical = WCS(header, key='P', naxis=2)
        result['corners_xy_zero_based'] = corners.tolist()
        result['corners_detector_xy'] = physical.all_pix2world(corners, 0).tolist()
        result['physical_ctype'] = list(physical.wcs.ctype)
        try:
            celestial = WCS(header, naxis=2)
            target = celestial.all_world2pix([[ra, dec]], 0)
            result['nominal_target_cutout_xy'] = target[0].tolist()
            result['nominal_target_detector_xy'] = physical.all_pix2world(target, 0)[0].tolist()
        except Exception as exc:
            result['nominal_target_error'] = str(exc)
    return result


def restore_lc(cfg, cache, out):
    datasets = {d['sector']: d for d in read(ROOT / cfg['datasets'])}
    inventory = []
    for product in cfg['products']:
        sector = product['sector']
        source = cache / product['name']
        if not source.exists():
            fetch(product['url'], source, product['bytes'], cfg['download_timeout_seconds'])
        assert source.stat().st_size == product['bytes'] and sha(source) == product['sha256']
        dataset = datasets[sector]
        assert sha(ROOT / dataset['contexts']) == dataset['contexts_sha256']
        with np.load(ROOT / dataset['contexts'], allow_pickle=False) as old, \
             np.load(ROOT / cfg['prior_auxiliary'] / f'auxiliary_s{sector:03d}.npz', allow_pickle=False) as aux, \
             fits.open(source, memmap=False) as hdus:
            hdus.verify('exception')
            h, table, ap = hdus[1].header, hdus[1].data, hdus['APERTURE']
            assert hdus[0].header['SECTOR'] == sector and hdus[0].header['TICID'] == 307210830
            assert hdus[0].header['CAMERA'] == product['camera'] and hdus[0].header['CCD'] == product['ccd']
            assert h['TIMESYS'] == 'TDB' and h['BJDREFI'] + h.get('BJDREFF', 0) == 2457000
            assert h['TIMEREF'] == 'SOLARSYSTEM'
            np.testing.assert_allclose(h['TIMEDEL'] * 86400, 20, rtol=1e-6)
            indices = np.asarray(old['anchors'], dtype=int)[:, None] + np.arange(-200, 201)
            cadence = np.asarray(table['CADENCENO'], dtype=np.int64)[indices]
            time = np.asarray(table['TIME'], dtype=np.float64)[indices]
            corr = np.asarray(table['TIMECORR'], dtype=np.float64)[indices]
            quality = np.asarray(table['QUALITY'], dtype=np.int64)[indices]
            position = np.stack([np.asarray(table[f], dtype=float)[indices] for f in ['POS_CORR2', 'POS_CORR1']], axis=-1)
            for a, b in [(cadence, old['context_cadence']), (cadence, aux['cadence']),
                         (time, aux['time']), (position, aux['position_yx']), (quality, aux['quality']),
                         ((ap.data & 2) != 0, old['aperture'])]:
                np.testing.assert_array_equal(a, b)
            assert time.shape == corr.shape == (10, 401) and np.isfinite(corr).all()
            spacecraft = time - corr
            np.savez_compressed(out / f'timing_s{sector:03d}.npz',
                                indices=indices, cadence=cadence, time_barycentric_btjd=time,
                                time_correction_days=corr, time_spacecraft_btjd=spacecraft,
                                quality=quality)
            header_path = out / f'headers_s{sector:03d}.json'
            dump(header_path, {'hdus': [{'index': i, 'name': x.name, 'cards': cards(x.header)}
                                       for i, x in enumerate(hdus)]})
            keys = ['TIMESYS', 'TIMEREF', 'TASSIGN', 'BJDREFI', 'BJDREFF', 'TIMEPIXR', 'TIMEDEL',
                    'INT_TIME', 'READTIME', 'FRAMETIM', 'NUM_FRM', 'DEADC', 'EXPOSURE', 'LIVETIME',
                    'DATA_REL', 'PROCVER', 'DATE-OBS', 'DATE-END']
            metadata = {k: h.get(k, hdus[0].header.get(k)) for k in keys}
            ra, dec = hdus[0].header['RA_OBJ'], hdus[0].header['DEC_OBJ']
            geo = geometry(ap.header, ap.data.shape, ra, dec)
            record = {**product, 'selected_rows': int(time.size),
                      'context_count': 10, 'context_length': 401, 'metadata': metadata,
                      'timing_column_units': {f: hdus[1].columns[f].unit for f in ['TIME', 'TIMECORR']},
                      'time_correction_seconds': stats(corr * 86400),
                      'spacecraft_spacing_seconds': stats(np.diff(spacecraft, axis=1) * 86400),
                      'geometry': geo,
                      'aperture_bit_counts': {str(bit): int(((ap.data & bit) != 0).sum()) for bit in [1, 2, 4, 8, 16]},
                      'missing_motion_uncertainty_columns': [f for f in ['POS_CORR1_ERR', 'POS_CORR2_ERR'] if f not in table.names],
                      'interpolation_applied': False,
                      'context_spacecraft_ranges_btjd': [[float(x.min()), float(x.max())] for x in spacecraft],
                      'timing_file': f'timing_s{sector:03d}.npz',
                      'headers_file': header_path.name}
            inventory.append(record)
        print(f'Sector {sector}: exact old cadence/time/motion join; 4010 timing rows restored', flush=True)
    return inventory


def prf_inputs(cfg, out):
    tasks = []
    for product in cfg['products']:
        for row in cfg['prf_rows']:
            for col in cfg['prf_cols']:
                name = f"{cfg['prf_stamp']}-prf-{product['camera']}-{product['ccd']}-row{row:04d}-col{col:04d}.fits"
                url = urljoin(cfg['prf_base'], f"cam{product['camera']}_ccd{product['ccd']}/{name}")
                tasks.append({'sector': product['sector'], 'camera': product['camera'], 'ccd': product['ccd'],
                              'grid_row': row, 'grid_col': col, 'name': name, 'url': url})
    def one(task):
        path = out / 'prf' / task['name']
        result = {**task, 'path': path.relative_to(out).as_posix()}
        try:
            result.update(fetch(task['url'], path, cfg['prf_max_bytes_per_file'], cfg['download_timeout_seconds']))
            result['status'] = 'downloaded'
            with fits.open(path, memmap=False) as hdus:
                hdus.verify('exception')
                result['hdus'] = [{'index': i, 'name': h.name, 'cards': cards(h.header),
                                   'array': stats(h.data) if h.data is not None else None}
                                  for i, h in enumerate(hdus)]
                result['expected_image_pair'] = bool(len(hdus) == 2 and all(
                    h.data is not None and list(h.data.shape) == cfg['prf_expected_shape'] and
                    np.isfinite(h.data).all() for h in hdus))
        except Exception as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)
            result['status'] = 'inspection_failed' if path.exists() else 'unavailable'
            result['expected_image_pair'] = False
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(one, tasks))
    print(f"PRF models: {sum(r['status'] == 'downloaded' for r in records)}/{len(records)} restored", flush=True)
    return records


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(v for k, v in attrs if k == 'href')


def supporting_sources(cfg, cache):
    records = []
    engineering = {'url': cfg['engineering_index'], 'time_series_downloaded': False,
                   'time_reference_verified': False, 'selected_links': []}
    try:
        temp = cache / 'engineering_index.html'
        engineering.update(fetch(cfg['engineering_index'], temp, cfg['engineering_index_max_bytes'],
                                 cfg['download_timeout_seconds']))
        parser = Links()
        parser.feed(temp.read_text(errors='replace'))
        for href in sorted(set(parser.hrefs)):
            url = urljoin(cfg['engineering_index'], href)
            name = urlsplit(url).path.rsplit('/', 1)[-1]
            match = re.search(r'sector0*(29|32)(?:[-_.])', name, re.I)
            if (match and url.startswith(cfg['engineering_index']) and
                    re.search(r'-(quat|eng)\.fits(?:\.gz)?$', name, re.I)):
                engineering['selected_links'].append({'sector': int(match.group(1)), 'name': name, 'url': url})
        engineering['status'] = 'listed' if engineering['selected_links'] else 'no_matching_links'
    except Exception as exc:
        engineering['status'] = 'unavailable'
        engineering['error'] = type(exc).__name__ + ': ' + str(exc)
    for name in ['00README.txt', 'export_mat2fits.m']:
        url = urljoin(cfg['prf_base'], name)
        try:
            records.append({'name': name, 'status': 'retrieved_for_provenance',
                            **fetch(url, cache / name, 2000000, cfg['download_timeout_seconds'])})
        except Exception as exc:
            records.append({'name': name, 'url': url, 'status': 'unavailable',
                            'error': type(exc).__name__ + ': ' + str(exc)})
    return engineering, records


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='results_ls7k_inputs')
    p.add_argument('--cache', default='data_ls7k_inputs')
    args = p.parse_args()
    cfg = read(ROOT / 'config/ls7k_inputs.json')
    out, cache = Path(args.output), Path(args.cache)
    assert not out.exists(), 'refuse to overwrite an existing result'
    checks = preserve(cfg)
    out.mkdir(parents=True)
    cache.mkdir(parents=True, exist_ok=True)
    source = {'source_commit': git('rev-parse', 'HEAD'), 'parent_commit': cfg['parent_commit'],
              'github_run_id': os.environ.get('GITHUB_RUN_ID'),
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': {name: sha(ROOT / name) for name in cfg['source_files']}}
    dump(out / 'source_freeze.json', source)
    lc = restore_lc(cfg, cache, out)
    prfs = prf_inputs(cfg, out)
    engineering, documentation = supporting_sources(cfg, cache)
    inventory = {'study': 'LS7K', 'scope': cfg['scope'], 'light_curves': lc, 'prf_models': prfs,
                 'engineering': engineering, 'documentation_retrieval': documentation,
                 'required_prf_models': 50,
                 'restored_prf_models': sum(r['status'] == 'downloaded' for r in prfs),
                 'expected_prf_image_pairs': sum(r['expected_image_pair'] for r in prfs),
                 'timing_rows': sum(x['selected_rows'] for x in lc),
                 'preserved_manifest_entries': checks,
                 'added_observing_days': 0, 'new_detector_decisions': 0,
                 'response_fit_performed': False, 'upstream_target_independence_established': False}
    dump(out / 'inventory.json', inventory)
    assert preserve(cfg) == checks
    print(json.dumps({k: inventory[k] for k in ['timing_rows', 'restored_prf_models',
                     'expected_prf_image_pairs', 'preserved_manifest_entries']}, indent=2), flush=True)
    print(json.dumps({'engineering': engineering}, indent=2), flush=True)


if __name__ == '__main__':
    main()
