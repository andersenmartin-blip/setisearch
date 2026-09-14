#!/usr/bin/env python3
"""Frozen selected TPF ranges and sparse-CR indexing, with resumable byte cache."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np
from astropy.io import fits

from ls7o_reference_metadata import Ranges, save, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls7p_inputs'
CACHE = ROOT.parent/'ls7p_work'/'ranges'


def table_dtype(h):
    fields = []
    for i in range(1, h['TFIELDS']+1):
        match = re.fullmatch(r'(\d*)([DEJI])', h[f'TFORM{i}'])
        assert match is not None
        count, code = match.groups()
        dtype = {'D': '>f8', 'E': '>f4', 'J': '>i4', 'I': '>i2'}[code]
        fields.append((h[f'TTYPE{i}'], dtype, (int(count),)) if count else (h[f'TTYPE{i}'], dtype))
    result = np.dtype(fields)
    assert result.itemsize == h['NAXIS1']
    return result


def get_cached(ranges, path, start, length):
    receipt = path.with_suffix('.json')
    if path.exists() and receipt.exists():
        raw = path.read_bytes(); r = json.loads(receipt.read_text())
        assert r['etag'] == ranges.etag and (r['start'], r['length']) == (start, length)
        assert len(raw) == length and sha(raw) == r['sha256']
        assert ranges.total+length <= ranges.budget
        ranges.total += length; ranges.records.append(r)
        return raw
    raw = ranges.get(start, length)
    path.write_bytes(raw); save(receipt, ranges.records[-1])
    return raw


def one(r):
    sector, tic = r['sector'], r['tic']; key = f's{sector:03d}_tic{tic}'
    dest = OUT/(key+'.json')
    if dest.exists(): return json.loads(dest.read_text())
    product = r['product']
    budget = sum(p['length'] for p in r['pixel_ranges'])+r['cosmic_ray_table']['length']
    ranges = Ranges(product['uri'], product['bytes'], etag=product['etag'], budget=budget)
    ranges.url = product['archive_url']
    blocks = [get_cached(ranges, CACHE/f'{key}_a{p["anchor"]:02d}.bin', p['start'], p['length'])
              for p in r['pixel_ranges']]
    raw = b''.join(blocks)
    h = fits.Header.fromstring((ROOT/'results_ls7p_metadata'/f'{r["header_prefix"]}_pixels.hdr').read_bytes().decode('ascii'))
    table = np.frombuffer(raw, dtype=table_dtype(h)).reshape(10, 401)
    old = np.load(ROOT/f'results_ls7o_inputs/references_s{sector:03d}.npz', allow_pickle=False)
    j = old['tic'].tolist().index(tic)
    np.testing.assert_array_equal(table['CADENCENO'], old['cadence'][j])
    np.testing.assert_array_equal(table['TIME'], old['time_barycentric_btjd'][j])
    np.testing.assert_array_equal(table['TIMECORR'], old['time_correction_days'][j])
    # Fetch the interleaved sparse table as an index. Only CADENCENO is interpreted
    # outside selected contexts; no outside-context coordinate/amplitude analysis.
    cr = r['cosmic_ray_table']
    cr_raw = get_cached(ranges, CACHE/f'{key}_cr.bin', cr['start'], cr['length'])
    cr_ids = np.ndarray((cr['rows'],), dtype='>i4', buffer=cr_raw, strides=(12,))
    chosen = np.flatnonzero(np.isin(cr_ids, table['CADENCENO'].ravel()))
    selected_cr = b''.join(cr_raw[i*12:(i+1)*12] for i in chosen)
    for suffix, value in [('pixels.bin.gz', raw), ('cr_index_payload.bin.gz', cr_raw),
                           ('selected_cr.bin.gz', selected_cr)]:
        (OUT/'raw'/f'{key}_{suffix}').write_bytes(gzip.compress(value, mtime=0))
    # Full sparse-index bytes are preserved to allow independent filtering audit.
    # Publication of bytes does not turn unselected amplitudes into evaluated data.
    record = {'sector': sector, 'tic': tic, 'product': product,
              'download_bytes': ranges.total, 'ranges': ranges.records,
              'pixel_raw_path': f'raw/{key}_pixels.bin.gz', 'pixel_raw_sha256': sha(raw),
              'cr_index_raw_path': f'raw/{key}_cr_index_payload.bin.gz', 'cr_index_raw_sha256': sha(cr_raw),
              'selected_cr_path': f'raw/{key}_selected_cr.bin.gz', 'selected_cr_sha256': sha(selected_cr),
              'selected_cr_rows': len(chosen), 'selected_cr_index_rows': chosen.tolist(),
              'pixel_rows': 4010, 'cadence_time_join_exact': True,
              'quality_mismatch_rows': int((table['QUALITY'] != old['quality'][j]).sum())}
    save(dest, record)
    print(f'{key}: 4010 exact joins; {len(chosen)} selected CR records; {ranges.total} bytes', flush=True)
    return record


def main():
    assert not (OUT/'sources.json').exists(), 'refuse completed output overwrite'
    cfg = json.loads((ROOT/'config/ls7p_pixels.json').read_text())
    for path, expected in cfg['input_sha256'].items():
        assert sha((ROOT/path).read_bytes()) == expected, path
    (OUT/'raw').mkdir(parents=True, exist_ok=True); CACHE.mkdir(parents=True, exist_ok=True)
    meta = json.loads((ROOT/'results_ls7p_metadata/inventory.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(one, meta['references']))
    total = sum(r['download_bytes'] for r in records)
    assert total == cfg['science_transfer_bytes']
    save(OUT/'sources.json', {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                             'download_bytes': total, 'selected_pixel_rows': 48120,
                             'selected_cr_rows': sum(r['selected_cr_rows'] for r in records),
                             'outside_context_cr_payload_used': False,
                             'whole_product_checksum_checked': False, 'records': records})
    paths = sorted(p for p in OUT.rglob('*') if p.is_file() and p.name != 'SHA256SUMS')
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT)}\n' for p in paths))


if __name__ == '__main__': main()
