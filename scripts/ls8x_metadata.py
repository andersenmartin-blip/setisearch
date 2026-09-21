#!/usr/bin/env python3
"""Acquire only named CAL/COR headers and exposure metadata for LS8X."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from seti_repeater.cheops_url_timeout import resolve_url
import hashlib
import json
import os
import subprocess
from pathlib import Path
import ls7r_acquire as acquisition

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8x_metadata'
SEARCH_KEYS = ['CH_PR100041_TG000302_V0300', 'CH_PR100041_TG001301_V0300']
KEYS = ['CH_PR100041_TG000302_V0300']
KINDS = ('SCI_CAL_SubArray', 'SCI_COR_SubArray')


class BudgetReader(acquisition.Reader):
    def read(self, start, count):
        assert self.bytes_read + count <= 20_000_000, 'metadata budget exceeded before transfer'
        return super().read(start, count)


def main():
    assert os.environ.get('GITHUB_SHA')==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip()
    cfg=json.loads((ROOT/'config/ls8x_representatives.json').read_text())
    for name,digest in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    assert json.loads((ROOT/'results_ls8w_l2_screen/audit.json').read_text())['status']=='PASS'
    for line in (ROOT/'results_ls8w_l2_screen/SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256((ROOT/'results_ls8w_l2_screen'/name).read_bytes()).hexdigest()==digest,name
    expected=[]
    for key in SEARCH_KEYS:
        clusters=json.loads((ROOT/'results_ls8w_l2_screen'/key/'clusters.json').read_text())
        for sign in ('positive','negative'):
            for c in clusters[sign]:
                rep=c['representative'];expected.append([key,sign,c['cluster_id'],rep['start'],rep['duration']])
    assert cfg['representatives']==expected and len(expected)==1
    assert sum(28+r[4] for r in expected)==cfg['expected_context_rows']==29
    assert cfg['expected_cal_cor_joins']==58
    assert not OUT.exists(), 'refuse completed LS8X metadata overwrite'
    OUT.mkdir()
    attempts=[];lock=Lock();original_resolver=acquisition.get_url
    def record(entry):
        with lock:
            attempts.append(entry)
            (OUT/'transport_attempts.json').write_text(json.dumps(attempts,indent=2)+'\n')
    def bounded_resolver(kind):
        return resolve_url(acquisition.KEY+':'+kind,lambda _:original_resolver(kind),record)
    acquisition.get_url=bounded_resolver
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
