import argparse,json,hashlib,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('result');a=p.parse_args()
result=Path(a.result).resolve();root=result.parent
data=json.loads(result.read_text());rows=data['results'];assert rows
out=root/'SAVED_ACKS';out.mkdir(exist_ok=True)
failures=[]
for row in rows:
    if row.get('status')!='succeeded' or row.get('local_metadata_applied') is not True:
        failures.append(row);continue
    local=Path(row['local_path']);assert local.parent==root
    receipt_path=root/(local.name+'.receipt.json');receipt=json.loads(receipt_path.read_text())
    assert receipt['local_archive_readback_verified'] is True
    assert receipt['path']==str(local)
    assert local.stat().st_size==receipt['bytes']
    ack={'sequence':receipt['sequence'],'phase':receipt['phase'],'new_complete_job_indices':receipt['new_complete_job_indices'],
         'archive_name':local.name,'archive_bytes':receipt['bytes'],'archive_sha256':receipt['sha256'],
         'original_local_receipt_sha256':hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
         'library_file_id':row['library_file_id'],'file_id':row['file_id'],'saved_path':row['path'],
         'current_version_number':row['current_version_number'],'local_metadata_applied':True,'save_status':'succeeded',
         'persistence_claim':'Library helper confirmed the save of this previously hash-verified local archive; remote payload was not downloaded again.'}
    target=out/f"{receipt['sequence']:04d}.json"
    if target.exists():assert json.loads(target.read_text())==ack
    else:
        with target.open('x') as f:json.dump(ack,f,indent=2,sort_keys=True);f.write('\n')
acks=[json.loads(x.read_text()) for x in sorted(out.glob('*.json'))]
index={'schema':'SETI_SAVED_CHECKPOINT_INDEX_V1','study':'SETI_SIXSCAN_BURST_20261015_RECOVERY_V1',
       'saved_checkpoints':acks,'total_saved_archive_bytes':sum(x['archive_bytes'] for x in acks),
       'copied_payloads_are_not_additional_scientific_trials':True,'metadata_update_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
(root/'SAVED_CHECKPOINT_INDEX.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
print(json.dumps({'saved_checkpoints':len(acks),'last_sequences':[x['sequence'] for x in acks[-4:]],'failed_items':failures}))
raise SystemExit(1 if failures else 0)
