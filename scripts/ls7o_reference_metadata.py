#!/usr/bin/env python3
"""Metadata-only selection of six same-CCD fast reference stars per closed sector.

Reads mission lists, MAST catalog records, FITS headers and aperture masks.
It never requests light-curve table rows. No native response score is read.
"""
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from scipy.spatial import Delaunay

from ls7k_instrument_inputs import geometry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls7o_metadata'
STAGE = ROOT.parent / 'ls7o_work'
TARGET = (124.531756290083, -68.3129998725044)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def query(request, path):
    url = 'https://mast.stsci.edu/api/v0/invoke?' + urllib.parse.urlencode({'request': json.dumps(request)})
    if path.exists():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read(4_000_001)
        assert len(data) <= 4_000_000
        path.write_bytes(data)
    value = json.loads(data)
    assert value['status'] == 'COMPLETE', value.get('msg')
    assert value['paging']['pagesFiltered'] == 1
    return value


class Ranges:
    def __init__(self, uri, size, etag=None, budget=160_000):
        self.url = 'https://mast.stsci.edu/api/v0.1/Download/file?' + urllib.parse.urlencode({'uri': uri})
        self.size = size
        self.etag = etag
        self.budget = budget
        self.total = 0
        self.records = []

    def get(self, start, length):
        assert 0 <= start < start + length <= self.size
        assert self.total + length <= self.budget, 'frozen byte budget exceeded'
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={start}-{start+length-1}'})
        if self.etag:
            request.add_header('If-Match', self.etag)
        with urllib.request.urlopen(request, timeout=45) as response:
            assert response.status == 206, 'server must honor exact ranges'
            assert response.headers['Content-Range'] == f'bytes {start}-{start+length-1}/{self.size}'
            etag = response.headers['ETag']
            assert self.etag is None or etag == self.etag, 'product changed'
            self.etag = etag
            # Reuse the resolved product URL within this process; do not log
            # transient signed redirect URLs or re-query MAST for each block.
            self.url = response.geturl()
            data = response.read(length + 1)
            assert len(data) == length
            self.records.append({'start': start, 'length': length, 'sha256': sha(data),
                                 'etag': etag, 'last_modified': response.headers.get('Last-Modified')})
        self.total += length
        return data

    def header(self, start):
        blocks = []
        for block in range(20):
            data = self.get(start + block*2880, 2880)
            blocks.append(data)
            if any(data[i:i+8] == b'END     ' for i in range(0, 2880, 80)):
                raw = b''.join(blocks)
                return fits.Header.fromstring(raw.decode('ascii')), raw
        raise ValueError('header exceeds declared 20-block limit')


def main():
    assert not (OUT/'inventory.json').exists(), 'refuse to overwrite completed metadata'
    OUT.mkdir(exist_ok=True)
    (OUT/'headers').mkdir(exist_ok=True)
    (OUT/'archive').mkdir(exist_ok=True)
    selected = []
    inventories = []
    for sector, ccd in [(29, 3), (32, 4)]:
        name = f'all_targets_20s_S{sector:03d}_v1.txt'
        if not (STAGE/name).exists():
            STAGE.mkdir(exist_ok=True)
            with urllib.request.urlopen('https://tess.mit.edu/public/target_lists/20s/'+name, timeout=45) as response:
                data = response.read(1_000_001)
            assert len(data) <= 1_000_000
            (STAGE/name).write_bytes(data)
        raw = (STAGE/name).read_bytes()
        (OUT/'archive'/name).write_bytes(raw)
        values = np.loadtxt(STAGE/name)
        assert len(values) == len(set(values[:, 0])) == 1000
        distance = SkyCoord(*TARGET, unit='deg').separation(SkyCoord(values[:, 4], values[:, 5], unit='deg')).deg
        eligible = ((values[:, 1] == 4) & (values[:, 2] == ccd) &
                    (values[:, 3] >= 8) & (values[:, 3] <= 12) &
                    (distance >= .25) & (distance <= 3) & (values[:, 0] != 307210830))
        order = sorted(np.flatnonzero(eligible), key=lambda i: (distance[i], int(values[i, 0])))
        assert len(order) >= 6
        request = {'service': 'Mast.Caom.Filtered', 'params': {
            'columns': 'obsid,obs_id,target_name,s_ra,s_dec,t_exptime,t_min,t_max,sequence_number,dataURL',
            'filters': [{'paramName': 'obs_collection', 'values': ['TESS']},
                        {'paramName': 'sequence_number', 'values': [{'min': sector, 'max': sector}]},
                        {'paramName': 't_exptime', 'values': [{'min': 20, 'max': 20}]}]},
            'format': 'json', 'pagesize': 2000, 'page': 1}
        path = OUT/'archive'/f'mast_s{sector}.json'
        if (STAGE/path.name).exists():
            path.write_bytes((STAGE/path.name).read_bytes())
        observed = query(request, path)['data']
        inventories.append({'sector': sector, 'ccd': ccd, 'list_url': 'https://tess.mit.edu/public/target_lists/20s/'+name,
                            'list_count': 1000, 'same_ccd_count': int(((values[:, 1] == 4) & (values[:, 2] == ccd)).sum()),
                            'eligible_within_3_deg': len(order), 'observation_count': len(observed), 'request': request,
                            'eligible_ranked': [{'tic': int(values[i, 0]), 'tmag': float(values[i, 3]),
                                                'separation_deg': float(distance[i])} for i in order]})
        for i in order[:6]:
            tic = int(values[i, 0])
            matches = [o for o in observed if o['target_name'] == str(tic)]
            assert len(matches) == 1, (sector, tic, matches)
            selected.append({'sector': sector, 'camera': 4, 'ccd': ccd, 'tic': tic,
                             'tmag': float(values[i, 3]), 'separation_deg': float(distance[i]), 'observation': matches[0]})

    def inspect(record):
        s, tic = record['sector'], record['tic']
        path = OUT/'archive'/f'products_{s}_{tic}.json'
        if (STAGE/path.name).exists():
            path.write_bytes((STAGE/path.name).read_bytes())
        req = {'service': 'Mast.Caom.Products', 'params': {'obsid': str(record['observation']['obsid'])},
               'format': 'json', 'pagesize': 1000, 'page': 1}
        products = query(req, path)['data']
        pp = [p for p in products if p['dataURI'] == record['observation']['dataURL']]
        assert len(pp) == 1
        product = pp[0]
        tpf = [p for p in products if p['productFilename'] == product['productFilename'].replace('fast-lc', 'fast-tp')]
        assert len(tpf) == 1
        ranges = Ranges(product['dataURI'], product['size'])
        h0, b0 = ranges.header(0)
        h1, b1 = ranges.header(len(b0))
        table_start = len(b0) + len(b1)
        assert h0['TICID'] == tic and h0['SECTOR'] == s and h0['CAMERA'] == 4 and h0['CCD'] == record['ccd']
        assert h1['EXTNAME'] == 'LIGHTCURVE' and h1['PCOUNT'] == 0 and h1['NAXIS1'] == 100
        assert abs(h1['TIMEDEL']*86400-20) < 2e-5
        assert h1['TIMESYS'] == 'TDB' and h1['TIMEREF'] == 'SOLARSYSTEM' and h1['BJDREFI'] == 2457000
        next_start = table_start + ((h1['NAXIS1']*h1['NAXIS2']+2879)//2880)*2880
        h2, b2 = ranges.header(next_start)
        assert h2['EXTNAME'] == 'APERTURE' and h2['BITPIX'] == 32
        mask_raw = ranges.get(next_start+len(b2), h2['NAXIS1']*h2['NAXIS2']*4)
        mask = np.frombuffer(mask_raw, dtype='>i4').reshape(h2['NAXIS2'], h2['NAXIS1'])
        assert (mask & 8).any(), 'no documented moment-centroid footprint'
        prefix = f's{s:03d}_tic{tic}'
        for name, raw in [('primary.hdr', b0), ('lightcurve.hdr', b1), ('aperture.hdr', b2), ('aperture.bin', mask_raw)]:
            (OUT/'headers'/f'{prefix}_{name}').write_bytes(raw)
        geo = geometry(h2, mask.shape, h0['RA_OBJ'], h0['DEC_OBJ'])
        old = next(r for r in json.loads((ROOT/'results_ls7k_inputs/inventory.json').read_text())['light_curves'] if r['sector'] == s)
        target = old['geometry']['nominal_target_detector_xy']
        origin = np.array([h2['CRVAL1P']+1-h2['CRPIX1P'], h2['CRVAL2P']+1-h2['CRPIX2P']])
        yy, xx = np.where((mask & 8) != 0)
        moment_pixels = np.stack([xx, yy], -1) + origin
        min_distance = np.linalg.norm(moment_pixels - target, axis=1).min()
        assert min_distance > 40
        columns = [{'name': h1[f'TTYPE{i}'], 'format': h1[f'TFORM{i}'], 'unit': h1.get(f'TUNIT{i}')}
                   for i in range(1, h1['TFIELDS']+1)]
        timing = {k: h1.get(k, h0.get(k)) for k in ['TIMESYS','TIMEREF','TASSIGN','BJDREFI','BJDREFF','TIMEPIXR','TIMEDEL','INT_TIME','READTIME','FRAMETIM','NUM_FRM','DEADC','TSTART','TSTOP','DATA_REL','PROCVER']}
        record.update({'product': {'name': product['productFilename'], 'uri': product['dataURI'], 'bytes': product['size'], 'etag': ranges.etag},
                       'available_tpf': {'name': tpf[0]['productFilename'], 'uri': tpf[0]['dataURI'], 'bytes': tpf[0]['size']},
                       'table_start': table_start, 'row_bytes': h1['NAXIS1'], 'rows': h1['NAXIS2'],
                       'geometry': geo, 'timing': timing, 'columns': columns, 'metadata_download_bytes': ranges.total,
                       'metadata_ranges': ranges.records, 'moment_centroid_pixels': int((mask & 8 != 0).sum()),
                       'minimum_target_to_centroid_pixel_distance': float(min_distance), 'header_prefix': 'headers/'+prefix,
                       'products_request': req})
        print(f'Metadata sector {s} TIC {tic}: {record["rows"]} rows, {record["moment_centroid_pixels"]} centroid pixels', flush=True)
        return record

    with ThreadPoolExecutor(max_workers=4) as executor:
        records = list(executor.map(inspect, selected))
    spatial = []
    for s in [29, 32]:
        old = next(r for r in json.loads((ROOT/'results_ls7k_inputs/inventory.json').read_text())['light_curves'] if r['sector'] == s)
        target = np.array(old['geometry']['nominal_target_detector_xy'])
        xy = np.array([r['geometry']['nominal_target_detector_xy'] for r in records if r['sector'] == s])
        x = np.column_stack([np.ones(6), (xy-target)/1024])
        assert np.linalg.matrix_rank(x) == 3
        inside = bool(Delaunay(xy).find_simplex(target) >= 0)
        spatial.append({'sector': s, 'target_detector_xy': target.tolist(), 'reference_design': x.tolist(),
                        'unweighted_condition': float(np.linalg.cond(x)), 'target_inside_reference_hull': inside})
        assert inside, 'do not extrapolate to target'
    save(OUT/'inventory.json', {'selection': {'same_camera_and_ccd': True, 'tmag_inclusive': [8,12], 'separation_deg_inclusive': [.25,3],
                                           'per_sector': 6, 'ranking': 'angular distance then TIC', 'selected_before_time_series': True},
                               'mission_lists': inventories, 'references': records, 'spatial': spatial,
                               'time_series_rows_inspected': 0, 'metadata_download_bytes': sum(r['metadata_download_bytes'] for r in records)})
    paths = sorted(p for p in OUT.rglob('*') if p.is_file())
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT)}\n' for p in paths))


if __name__ == '__main__':
    main()
