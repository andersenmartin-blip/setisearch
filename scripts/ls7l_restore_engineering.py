#!/usr/bin/env python3
"""Bounded original-file restoration and complete engineering schema inventory."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

from astropy.io import fits
from astropy.io.fits.card import Undefined

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent/'ls7l-engineering-cache'
OUT = ROOT/'results_ls7l_engineering'
SIZES = {29: {'eng': 284840640, 'quat': 417271680},
         32: {'eng': 292800960, 'quat': 415068480}}


def one(product):
    kind = 'quat' if '-quat.' in product['name'] else 'eng'
    expected = SIZES[product['sector']][kind]
    assert expected < 500_000_000
    path = CACHE/product['name']
    sha = hashlib.sha256()
    if not path.exists():
        partial = path.with_suffix('.partial')
        with urlopen(Request(product['url']), timeout=30) as response, partial.open('wb') as output:
            assert response.status == 200
            assert int(response.headers['Content-Length']) == expected
            total = 0
            while data := response.read(4*1024*1024):
                total += len(data)
                assert total <= expected
                output.write(data)
            assert total == expected
        partial.replace(path)
    assert path.stat().st_size == expected
    with path.open('rb') as stream:
        while data := stream.read(4*1024*1024):
            sha.update(data)
    result = {**product, 'kind': kind, 'bytes': expected, 'sha256': sha.hexdigest(), 'hdus': []}
    with fits.open(path, memmap=True) as hdus:
        hdus.verify('exception')
        for i, hdu in enumerate(hdus):
            result['hdus'].append({'index': i, 'name': hdu.name,
                'cards': [{'key': c.keyword, 'value': None if isinstance(c.value, Undefined) else c.value,
                           'comment': c.comment} for c in hdu.header.cards]})
    (OUT/(product['name']+'.headers.json')).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'name':product['name'],'bytes':expected,'sha256':result['sha256'],
                      'hdus':len(result['hdus'])}),flush=True)
    return {k:v for k,v in result.items() if k!='hdus'}


def main():
    products = json.loads((ROOT/'results_ls7k_inputs/inventory.json').read_text())['engineering']['selected_links']
    assert sum(SIZES[p['sector']]['quat' if '-quat.' in p['name'] else 'eng'] for p in products) < 1_500_000_000
    CACHE.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True)
    assert not (OUT/'sources.json').exists(), 'refuse to overwrite the source manifest'
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(one, products))
    (OUT/'sources.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
