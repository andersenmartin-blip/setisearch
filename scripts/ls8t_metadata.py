#!/usr/bin/env python3
"""Acquire only named CAL/COR headers and exposure metadata for LS8T."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import subprocess
from pathlib import Path
import ls7r_acquire as acquisition

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8t_metadata'
KEYS = ['CH_PR300046_TG000101_V0300', 'CH_PR100031_TG015701_V0300']
KINDS = ('SCI_CAL_SubArray', 'SCI_COR_SubArray')


class BudgetReader(acquisition.Reader):
    def read(self, start, count):
        assert self.bytes_read + count <= 20_000_000, 'metadata budget exceeded before transfer'
        return super().read(start, count)


def main():
    assert os.environ.get('GITHUB_SHA')==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip()
    cfg=json.loads((ROOT/'config/ls8t_representatives.json').read_text())
    for name,digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    assert json.loads((ROOT/'results_ls8s_l2_screen/audit.json').read_text())['status']=='PASS'
    for line in (ROOT/'results_ls8s_l2_screen/SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256((ROOT/'results_ls8s_l2_screen'/name).read_bytes()).hexdigest()==digest,name
    expected=[]
    for key in KEYS:
        clusters=json.loads((ROOT/'results_ls8s_l2_screen'/key/'clusters.json').read_text())
        for sign in ('positive','negative'):
            for c in clusters[sign]:
                rep=c['representative'];expected.append([key,sign,c['cluster_id'],rep['start'],rep['duration']])
    assert cfg['representatives']==expected and len(expected)==2
    assert sum(28+r[4] for r in expected)==cfg['expected_context_rows']==60
    assert cfg['expected_cal_cor_joins']==120
    assert not OUT.exists(), 'refuse completed LS8T metadata overwrite'
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
