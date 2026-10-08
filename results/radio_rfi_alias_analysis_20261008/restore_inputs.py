"""Restore exactly two published archives; verify hashes before extraction."""
import base64, hashlib, json, tarfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
index=json.loads((ROOT/'pilot_protocol_20261008/validation_b_upload_index.json').read_text())
records=[]
for i in (64,65):
    name=f'case_{i:03d}.tar.gz'; record=next(x for x in index if x['path'].endswith('/'+name))
    b=base64.b64decode((ROOT/f'recovery/case_{i}.tar.gz.b64').read_text())
    assert len(b)==record['bytes']
    assert hashlib.sha256(b).hexdigest()==record['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==record['git_blob_sha1']
    archive=ROOT/'recovery'/name; archive.write_bytes(b)
    with tarfile.open(archive,'r:gz') as t:
        for member in t.getmembers():
            dest=(ROOT/member.name).resolve()
            assert dest.is_relative_to(ROOT/'results/radio_pilot_val_b_20261008') and member.isfile()
        t.extractall(ROOT,filter='data')
    records.append(record)
(ROOT/'results/radio_rfi_alias_analysis_20261008/RESTORED_INPUTS.json').write_text(json.dumps({'source_commit':'6b8259099721b3acdb98b604fb5c9ea192577d68','archives':records,'all_archive_sha256_git_sha1_and_lengths_verified':True,'original_data_unchanged':True},indent=2)+'\n')
print(json.dumps(records))
