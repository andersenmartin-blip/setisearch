#!/usr/bin/env python3
"""Bounded transport-only recovery; preserve first run, reuse unchanged science."""
import hashlib
import json
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError

import ls8v_l2_screen as runner
import ls8k_l2_audit as auditor
import ls8v_report as report

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls8v_l2_recovered'
LOG = ROOT / 'ls8v_transport_attempts.json'


def main():
    cfg = json.loads((ROOT/'config/ls8v_transport_recovery.json').read_text())
    for p,h in cfg['input_pins'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h, p
    old=ROOT/'results_ls8v_l2_screen'
    expected={'RUN_STATUS.json','environment.txt','ls8v_screen.log','ls8v_tests.log','SHA256SUMS'}
    assert {str(p.relative_to(old)) for p in old.rglob('*') if p.is_file()} == expected
    for line in (old/'SHA256SUMS').read_text().splitlines():
        h,p=line.split('  ',1)
        assert hashlib.sha256((old/p).read_bytes()).hexdigest()==h
    assert json.loads((old/'RUN_STATUS.json').read_text())['scientific_status']=='INCOMPLETE'
    assert 'The handshake operation timed out' in (old/'ls8v_screen.log').read_text()
    assert not OUT.exists() and not LOG.exists()
    original = runner.implementation.get_url
    attempts=[]

    def bounded_resolution(key):
        for attempt in range(1,4):
            entry={'file_key':key,'attempt':attempt,'started_utc':datetime.now(timezone.utc).isoformat()}
            try:
                url=original(key)
            except (URLError,TimeoutError) as exc:
                reason=getattr(exc,'reason',exc)
                timeout=isinstance(reason,(TimeoutError,socket.timeout))
                entry.update(outcome='TIMEOUT' if timeout else 'STOP_NON_TIMEOUT',error_type=type(reason).__name__)
                attempts.append(entry);LOG.write_text(json.dumps(attempts,indent=2)+'\n')
                if not timeout or attempt==3:
                    raise
                time.sleep(5)
            else:
                entry['outcome']='RESOLVED';attempts.append(entry)
                LOG.write_text(json.dumps(attempts,indent=2)+'\n')
                return url
        raise AssertionError('unreachable')

    runner.implementation.get_url=bounded_resolution
    runner.OUT=OUT
    try:
        runner.main()
        auditor.META=ROOT/'results_ls8v_l2_metadata'
        auditor.OUT=OUT
        auditor.KEYS=runner.KEYS
        auditor.main()
        report.OUT=OUT
        report.main()
    finally:
        if LOG.exists():
            OUT.mkdir(exist_ok=True)
            (OUT/'transport_attempts.json').write_bytes(LOG.read_bytes())
            LOG.unlink()


if __name__=='__main__':
    main()
