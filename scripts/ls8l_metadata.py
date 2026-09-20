#!/usr/bin/env python3
"""Acquire only named CAL/COR headers and exposure metadata for LS8L."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import ls7r_acquire as acquisition

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8l_metadata'
KEYS = ['CH_PR100041_TG000201_V0300', 'CH_PR100041_TG000202_V0300']
KINDS = ('SCI_CAL_SubArray', 'SCI_COR_SubArray')


def main():
    assert not OUT.exists(), 'refuse completed LS8L metadata overwrite'
    OUT.mkdir()
    acquisition.ALLOWED_TABLES = {'SCI_CAL_ImageMetadata', 'SCI_COR_ImageMetadata'}
    for key in KEYS:
        acquisition.KEY = key
        acquisition.OUT = OUT / key
        acquisition.OUT.mkdir(exist_ok=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(acquisition.acquire, KINDS))
        for kind in KINDS:
            receipt = json.loads((acquisition.OUT / f'{kind}_ranges.json').read_text())
            for item in receipt['ranges']:
                disposition = next(v for k, v in item['headers'].items() if k.lower() == 'content-disposition')
                assert key[:-6] + '_' in disposition and '_' + kind + '_V0300.fits' in disposition
    print('Metadata-only acquisition complete; all image arrays skipped.', flush=True)


if __name__ == '__main__':
    main()
