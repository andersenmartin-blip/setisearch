#!/usr/bin/env python3
"""Acquire only named CAL/COR headers and exposure metadata for LS8O."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import ls7r_acquire as acquisition

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8o_metadata'
KEYS = ['CH_PR100041_TG000401_V0300', 'CH_PR100041_TG000403_V0300']
KINDS = ('SCI_CAL_SubArray', 'SCI_COR_SubArray')


class BudgetReader(acquisition.Reader):
    def read(self, start, count):
        assert self.bytes_read + count <= 20_000_000, 'metadata budget exceeded before transfer'
        return super().read(start, count)


def main():
    cfg=json.loads((ROOT/'config/ls8o_representatives.json').read_text())
    for name,digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    assert json.loads((ROOT/'results_ls8n_l2_screen/audit.json').read_text())['status']=='PASS'
    for line in (ROOT/'results_ls8n_l2_screen/SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256((ROOT/'results_ls8n_l2_screen'/name).read_bytes()).hexdigest()==digest,name
    assert not OUT.exists(), 'refuse completed LS8O metadata overwrite'
    OUT.mkdir()
    acquisition.Reader = BudgetReader
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
