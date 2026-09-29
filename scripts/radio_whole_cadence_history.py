#!/usr/bin/env python3
"""Pack the closed two-case history, preserving all original revisions."""
import hashlib
import json
import subprocess
import time
from radio_receiver_adapter_common import ROOT
from seti_repeater import whole_cadence_history_radio as history
from seti_repeater.empty_null_radio import canonical

COMMIT='d201b56c12918073eb4d473a9f0215beff0493d6'
PREFIX='results_radio_gaussian_engineering_2026-09-29/live01/journal/revisions'


def main():
    start=time.monotonic()
    out=ROOT/'results_radio_journal_capacity_2026-09-29'
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',COMMIT,'--',PREFIX],cwd=ROOT).decode().splitlines()
    rows=[]
    for path in paths:
        raw=subprocess.check_output(['git','show',COMMIT+':'+path],cwd=ROOT)
        rows.append((len(json.loads(raw)['events']),path,raw))
    rows.sort();pins=[p.rsplit('/',1)[-1] for _,p,_ in rows]
    encoded=history.encode((raw for _,_,raw in rows),expected_revision_sha256s=pins)
    sha=hashlib.sha256(encoded).hexdigest()
    verified=history.verify(encoded,expected_sha256=sha,expected_revision_sha256s=pins)
    restored=[]
    for i,(_,path,raw) in enumerate(rows):
        decoded=verified.revision(i)
        if decoded!=raw:raise ValueError('Published revision bytes differ after restoration')
        restored.append({'event_count':i,'source_path':path,'sha256':pins[i],'bytes':len(raw),
                         'exact_original_bytes_restored':True})
    with (out/'closed_history.json').open('xb') as f:f.write(encoded)
    result={**verified.summary(),'status':'CLOSED_HISTORY_READONLY_RESTORATION_PASS',
            'source_commit':COMMIT,'original_revisions':restored,
            'old_revisions_deleted_or_rewritten':False,'new_journal_or_case_consumption':False,
            'new_random_values':0,'scientific_8_mib_budget_qualified':False,
            'incremental_remote_writer_qualified':False,'crash_restart_rights_created':False,
            'elapsed_seconds':time.monotonic()-start}
    with (out/'history_pack_result.json').open('xb') as f:f.write(canonical(result))
    print(json.dumps({k:v for k,v in result.items() if k!='original_revisions'},indent=2))


if __name__=='__main__':main()
