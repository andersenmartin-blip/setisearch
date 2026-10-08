"""Restore exact published B diagnostics/noise archives, never generate data."""
import base64,hashlib,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
index=json.loads((ROOT/'pilot_protocol_20261008/validation_b_upload_index.json').read_text())
records=[]
for i in range(86,142):
    name=f'case_{i:03d}.tar.gz'; record=next(x for x in index if x['path'].endswith('/'+name))
    b=base64.b64decode((ROOT/f'recovery/diagnostics/{name}.b64').read_bytes())
    assert len(b)==record['bytes'] and hashlib.sha256(b).hexdigest()==record['sha256']
    assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==record['git_blob_sha1']
    archive=ROOT/'recovery/diagnostics'/name; archive.write_bytes(b)
    with tarfile.open(archive,'r:gz') as t:
        for m in t.getmembers():
            dest=(ROOT/m.name).resolve(); assert dest.is_relative_to(ROOT/f'results/radio_pilot_val_b_20261008/case_{i:03d}') and m.isfile()
        t.extractall(ROOT,filter='data')
    records.append(record)
(OUT/'RESTORED_INPUTS.json').write_text(json.dumps({'source_commit':'13131757641c06d7bfcb10790a79811c750b1178','archives':records,'all_archive_sha256_git_sha1_and_lengths_verified':True,'originals_unchanged':True},indent=2)+'\n')
print(json.dumps({'archives':len(records),'compressed_bytes':sum(x['bytes'] for x in records)}))
