#!/usr/bin/env python3
"""Read-only recovery of the closed timed-out terminal archive; no retry rights."""
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from seti_repeater import event_archive_remote_radio as r
from seti_repeater import physical_evidence_v2_radio as e
from seti_repeater import whole_cadence_event_store_radio as s
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical

OUT=ROOT/'results_radio_v2_parent_2026-09-30'

def main():
    started=time.monotonic()
    failed=json.loads((OUT/'remote01/result.json').read_bytes())
    if failed['status']!='TERMINAL_ENGINEERING_ARCHIVE_STOPPED':raise ValueError('Closed failed archive scope required')
    commit=r.git_sha(failed['publication']['candidate'])
    freeze_raw=(OUT/'remote_freeze.json').read_bytes();freeze=json.loads(freeze_raw)
    if hashlib.sha256(freeze_raw).hexdigest()!=failed['remote_freeze_sha256']:
        raise ValueError('Original prospective freeze differs')
    inventory=freeze['bundle']['files'];paths=sorted(inventory)
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
        input=''.join(commit+':'+p+'\n' for p in paths).encode())
    files={};offset=0
    for path in paths:
        end=raw.index(b'\n',offset);header=raw[offset:end].split()
        if len(header)!=3 or header[1]!=b'blob':raise ValueError('Missing immutable blob: '+path)
        size=int(header[2]);data=raw[end+1:end+1+size];offset=end+size+2
        pin=inventory[path]
        if (len(data)!=size or raw[offset-1:offset]!=b'\n' or size!=pin['bytes']
                or hashlib.sha256(data).hexdigest()!=pin['sha256']
                or r.git_object('blob',data)!=pin['blob'] or header[0].decode()!=pin['blob']):
            raise ValueError('Immutable original blob differs: '+path)
        files[path]=data
    if offset!=len(raw):raise ValueError('Trailing Git framing bytes')
    manifest=json.loads(files[r.PREFIX+'/manifest.json']);pins=manifest['pins']
    originals=r.restore_original_files(files,expected_manifest_sha256=freeze['bundle']['manifest_sha256'])
    def group(label):
        prefix=r.PREFIX+'/archive/'+label+'/'
        return {p[len(prefix):]:data for p,data in originals.items() if p.startswith(prefix)}
    physical,journal,base=group('physical'),group('journal'),group('base')
    summary=r._validated_maps(physical,journal,base,pins)
    view=e.inspect_files(physical,expected_config_sha256=pins['config_sha256'],
        expected_last_checkpoint_sha256=pins['last_checkpoint_sha256'])
    local=json.loads((OUT/'integration01/result.json').read_bytes())
    snapshots=[]
    for index,pin in enumerate(local['restored_snapshots']):
        h=hashlib.sha256();size=0
        for piece in view.iter_snapshot(index):h.update(piece);size+=len(piece)
        if size!=pin['bytes'] or h.hexdigest()!=pin['sha256']:raise ValueError('Original snapshot differs')
        snapshots.append({'bytes':size,'sha256':h.hexdigest()})
    history=s.restore(journal,expected_genesis_sha256=pins['genesis_sha256'],
        expected_pointer_sha256=pins['pointer_sha256'])
    final=json.loads(history.revision_bytes[-1])
    for index,data in enumerate(history.revision_bytes):
        if data!=canonical({**final,'events':final['events'][:index]}):
            raise ValueError('Original journal revision differs')
        j.replay(json.loads(data))
    result={'schema':'radio-v2-terminal-archive-readonly-recovery-v1',
        'status':'EXACT_PUBLISHED_BYTES_VERIFIED_READ_ONLY','commit':commit,
        'archive_stored_files':len(files),'archive_stored_bytes':sum(map(len,files.values())),
        'original_files_restored':len(originals),'source_summary':summary,
        'snapshots':snapshots,'journal_versions':len(history.revision_bytes),
        'git_cat_file_batch_operations':1,'read_only_audit_seconds':time.monotonic()-started,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'original_live_scope_status':failed['status'],'original_live_usage':failed['publication']['usage'],
        'original_scope_failure_reversed':False,'new_publication':False,'new_allocations':0,
        'new_random_values':0,'new_receiver_measurements':0,'new_telescope_reads':0,
        'execution_restart_authorized':False,'scientific_admission_authorized':False}
    with (OUT/'readonly_recovery01.json').open('xb') as f:f.write(canonical(result))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
