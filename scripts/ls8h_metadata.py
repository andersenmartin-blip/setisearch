#!/usr/bin/env python3
"""Acquire only GJ 849 CAL/COR headers and image-metadata tables for LS8H."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import ls7r_acquire as acquisition

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls8h_metadata'
KEY='CH_PR100018_TG032401_V0300'
KINDS=('SCI_CAL_SubArray','SCI_COR_SubArray')

def main():
    assert not OUT.exists(), 'refuse completed LS8H metadata overwrite'
    OUT.mkdir()
    acquisition.ALLOWED_TABLES={'SCI_CAL_ImageMetadata','SCI_COR_ImageMetadata'}
    acquisition.KEY=KEY
    acquisition.OUT=OUT/KEY
    acquisition.OUT.mkdir()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(acquisition.acquire,KINDS))
    for kind in KINDS:
        receipt=json.loads((acquisition.OUT/f'{kind}_ranges.json').read_text())
        for item in receipt['ranges']:
            disposition=next(v for k,v in item['headers'].items() if k.lower()=='content-disposition')
            assert kind in disposition and 'V0300.fits' in disposition
    print('LS8H metadata-only acquisition complete; image arrays skipped.',flush=True)

if __name__=='__main__': main()
