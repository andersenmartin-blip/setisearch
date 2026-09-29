import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import lzma
import time

started=time.monotonic()
root=Path('/workspace/scratch/ad45775dff93/setisearch')
scratch=Path('/workspace/scratch/70dbfdecd017')
expected=json.loads((scratch/'pe_expected.json').read_bytes())
science='dfded6130acedfae15dc28f0f793b3ed48b6d46a'
main='14c86b724ddc73cba6606610f9b9820d8239c9df'
names=['refs/remotes/origin/m43-support-qualification','refs/remotes/origin/main']
names += [science+':'+p for p in expected['files']]+[main+':README.md']
raw=subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=''.join(p+'\n' for p in names).encode())
off=0;objects=[]
for name in names:
    end=raw.index(b'\n',off);header=raw[off:end].split();off=end+1
    assert len(header)==3,(name,header)
    n=int(header[2]);data=raw[off:off+n];assert raw[off+n:off+n+1]==b'\n';off+=n+1
    objects.append((header[0].decode(),header[1].decode(),data))
assert off==len(raw)
assert objects[0][0]==science and objects[1][0]==main
assert objects[0][2].splitlines()[0]==b'tree '+expected['tree'].encode()
assert b'parent 82db4e905a8f9efb2cd7d349bd8b1acb5f64bf5d\n' in objects[0][2]
readback={}
for path,obj in zip(expected['files'],objects[2:-1]):
    assert obj[1]=='blob' and obj[2]==(root/path).read_bytes(),path
    readback[path]=obj[2]
main_expected=(scratch/'pe_expected_main.md').read_bytes()
# apply_patch adds one line terminator after the source's existing trailing LF.
if main_expected==objects[-1][2]+b'\n':main_expected=main_expected[:-1]
assert main_expected==objects[-1][2]
assert objects[-1][0]=='350ff6809e005da223b944fa249563777991f18e'
base='results_radio_physical_evidence_2026-09-29/'
m=json.loads(readback[base+'archive_manifest.json']);pieces=[]
for row in m['parts']:
    data=readback[base+row['path']]
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    pieces.append(data)
xz=base64.b64decode(b''.join(pieces),validate=True)
assert hashlib.sha256(xz).hexdigest()==m['xz_sha256'] and len(xz)==m['xz_bytes']
decoded={}
with tarfile.open(fileobj=io.BytesIO(lzma.decompress(xz)),mode='r:') as tar:
    for member in tar:
        assert member.isfile() and member.name not in decoded
        decoded[member.name]=tar.extractfile(member).read()
assert set(decoded)=={r['path'] for r in m['files']}
for row in m['files']:
    data=decoded[row['path']]
    assert data==(root/base/row['path']).read_bytes()
    assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
result={'status':'PASS_INDEPENDENT_IMMUTABLE_GIT_READBACK','science_commit':science,
    'science_tree':expected['tree'],'main_commit':main,'main_readme_blob':objects[-1][0],
    'package_files_exact':len(expected['files']),'all_original_archive_files_exact':len(decoded),
    'original_archive_bytes':sum(map(len,decoded.values())),
    'git_object_batch_invocations':1,'batch_response_bytes':len(raw),
    'verification_seconds':time.monotonic()-started,
    'no_native_or_storage_fixture_reexecution':True}
out=root/base/'publication_readback.json'
with out.open('xb') as f:f.write(json.dumps(result,sort_keys=True,separators=(',',':')).encode())
print(json.dumps(result))
