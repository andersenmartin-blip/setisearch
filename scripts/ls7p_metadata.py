#!/usr/bin/env python3
"""Read only headers and aperture masks for the twelve fixed LS7O FAST-TPs."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from ls7o_reference_metadata import Ranges, save, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls7p_metadata'


def inspect(old):
    sector, tic = old['sector'], old['tic']
    prefix = f's{sector:03d}_tic{tic}'
    checkpoint = OUT / (prefix + '.json')
    if checkpoint.exists():
        return json.loads(checkpoint.read_text())
    product = dict(old['available_tpf'])
    ranges = Ranges(product['uri'], product['bytes'], budget=160_000)
    # The documented MAST archive hierarchy addresses the same immutable product.
    ident = f'{tic:016d}'
    url = ('https://archive.stsci.edu/missions/tess/tid/' + f's{sector:04d}/'
           + '/'.join(ident[i:i+4] for i in range(0, 16, 4)) + '/' + product['name'])
    ranges.url = url
    h0, b0 = ranges.header(0)
    h1, b1 = ranges.header(len(b0))
    assert (h0['SECTOR'], h0['CAMERA'], h0['CCD'], h0['TICID']) == (sector, 4, old['ccd'], tic)
    assert h1['EXTNAME'] == 'PIXELS' and h1['PCOUNT'] == 0
    assert h1['NAXIS2'] == old['rows'] and h1['TFIELDS'] == 11
    table_start = len(b0) + len(b1)
    aperture_start = table_start + ((h1['NAXIS1']*h1['NAXIS2']+2879)//2880)*2880
    h2, b2 = ranges.header(aperture_start)
    assert h2['EXTNAME'] == 'APERTURE' and h2['BITPIX'] == 32
    n = h2['NAXIS1']*h2['NAXIS2']
    mask_raw = ranges.get(aperture_start+len(b2), 4*n)
    assert mask_raw == (ROOT/'results_ls7o_metadata'/f'{old["header_prefix"]}_aperture.bin').read_bytes()
    cr_header_start = aperture_start + len(b2) + ((4*n+2879)//2880)*2880
    h3, b3 = ranges.header(cr_header_start)
    assert h3['EXTNAME'] == 'TARGET COSMIC RAY' and h3['PCOUNT'] == 0 and h3['NAXIS1'] == 12
    cr_start = cr_header_start + len(b3)
    assert cr_start + ((h3['NAXIS1']*h3['NAXIS2']+2879)//2880)*2880 == product['bytes']
    for suffix, raw in [('primary.hdr', b0), ('pixels.hdr', b1), ('aperture.hdr', b2),
                        ('aperture.bin', mask_raw), ('cosmic_rays.hdr', b3)]:
        (OUT/'headers'/f'{prefix}_{suffix}').write_bytes(raw)
    origin = [h1['1CRV5P']+(1-h1['1CRP5P'])*h1['1CDL5P'],
              h1['2CRV5P']+(1-h1['2CRP5P'])*h1['2CDL5P']]
    assert origin == old['geometry']['corners_detector_xy'][0]
    timing = {k: h1.get(k, h0.get(k)) for k in old['timing']}
    assert timing == old['timing']
    product.update({'etag': ranges.etag, 'archive_url': url})
    indices = np.load(ROOT/f'results_ls7k_inputs/timing_s{sector:03d}.npz')['indices']
    plans = []
    for anchor, ix in enumerate(indices):
        assert len(ix) == 401 and np.all(np.diff(ix) == 1)
        plans.append({'anchor': anchor, 'first_row': int(ix[0]), 'rows': 401,
                      'start': table_start+int(ix[0])*h1['NAXIS1'], 'length': 401*h1['NAXIS1']})
    record = {'sector': sector, 'tic': tic, 'ccd': old['ccd'], 'product': product,
              'header_prefix': 'headers/'+prefix, 'table_start': table_start,
              'row_bytes': h1['NAXIS1'], 'rows': h1['NAXIS2'],
              'shape_yx': [h2['NAXIS2'], h2['NAXIS1']], 'origin_xy': origin,
              'columns': [{'name': h1[f'TTYPE{i}'], 'format': h1[f'TFORM{i}'],
                           'unit': h1.get(f'TUNIT{i}'), 'dimensions': h1.get(f'TDIM{i}')}
                          for i in range(1, 12)], 'timing': timing,
              'cr_mitigation': {k: h0.get(k) for k in ['CRMITEN', 'CRBLKSZ', 'CRSPOC']},
              'cosmic_ray_table': {'start': cr_start, 'rows': h3['NAXIS2'],
                                   'length': 12*h3['NAXIS2'], 'row_bytes': 12},
              'pixel_ranges': plans, 'metadata_ranges': ranges.records,
              'metadata_download_bytes': ranges.total}
    save(checkpoint, record)
    print(f'Metadata s{sector:03d} TIC {tic}: {h1["NAXIS1"]} bytes/pixel row; {h3["NAXIS2"]} CR index records', flush=True)
    return record


def main():
    assert not (OUT/'inventory.json').exists(), 'refuse completed output overwrite'
    (OUT/'headers').mkdir(parents=True, exist_ok=True)
    old = json.loads((ROOT/'results_ls7o_metadata/inventory.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(inspect, old['references']))
    pixel_bytes = sum(p['length'] for r in records for p in r['pixel_ranges'])
    cr_bytes = sum(r['cosmic_ray_table']['length'] for r in records)
    save(OUT/'inventory.json', {'references': records, 'pixel_bytes_planned': pixel_bytes,
                              'cr_index_bytes_planned': cr_bytes, 'pixel_rows_inspected': 0,
                              'cr_records_inspected': 0, 'full_product_bytes': sum(r['product']['bytes'] for r in records),
                              'metadata_download_bytes': sum(r['metadata_download_bytes'] for r in records)})
    paths = sorted(p for p in OUT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT)}\n' for p in paths))


if __name__ == '__main__':
    main()
