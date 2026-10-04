import hashlib
import json
import os
import pathlib
import stat

REPO = pathlib.Path('/workspace/scratch/d804553c0e89/setisearch-status-20261004')
NS = REPO / 'results_radio_runtime_capture_preparation_20261004b'
ROOT = pathlib.Path('/workspace/scratch/d804553c0e89/radio-runtime-metadata-capture-20261004b')
NAMES = {'spent.json', 'selected-runtime-before.json', 'selected-runtime-after.json',
         'admission-witness.json', 'child.stdout.raw', 'child.stderr.raw',
         'procfs-samples.json', 'supervisor-result.json'}

def identity(st):
    return dict(device=st.st_dev, inode=st.st_ino, mode=format(stat.S_IMODE(st.st_mode), '04o'),
                bytes=st.st_size, allocated_bytes=st.st_blocks * 512,
                mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)

def digest(b):
    return dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest(),
                git_blob=hashlib.sha1(b'blob ' + str(len(b)).encode() + bytes([0]) + b).hexdigest())

assert {p.name for p in ROOT.iterdir()} == NAMES
root_before = identity(ROOT.stat())
assert root_before['device'] == 27 and root_before['inode'] == 1575156 and root_before['mode'] == '0700'
dest = NS / 'actual'
dest.mkdir(exist_ok=False)
rows = []
for name in sorted(NAMES):
    source = ROOT / name
    before = identity(source.lstat())
    assert stat.S_ISREG(source.lstat().st_mode)
    raw = source.read_bytes()
    with (dest / name).open('xb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    assert identity(source.lstat()) == before
    assert (dest / name).read_bytes() == raw
    rows.append(dict(name=name, original_path=str(source), original_identity=before,
                     repository_path=str((dest / name).relative_to(REPO)),
                     copied_bytes_equal=True, **digest(raw)))
assert identity(ROOT.stat()) == root_before
caller = json.loads((NS / 'administrative/caller.stdout.raw').read_bytes())
report = json.loads((ROOT / 'supervisor-result.json').read_bytes())
child = json.loads((ROOT / 'child.stdout.raw').read_bytes())
assert caller['report'] == report
assert caller['final_scope']['logical_bytes'] == root_before['bytes'] + sum(r['bytes'] for r in rows)
assert caller['final_scope']['allocated_bytes'] == root_before['allocated_bytes'] + sum(r['original_identity']['allocated_bytes'] for r in rows)
assert report['engineering_child_dispatches'] == 1 and report['child_reaped'] and report['child_exit_code'] == 0
assert report['status'] == child['status'] == 'OBSERVED_METADATA_ONLY'
assert child['admission_status'] == 'PENDING_MISSING_INPUTS'
assert (ROOT / 'selected-runtime-before.json').read_bytes() == (ROOT / 'selected-runtime-after.json').read_bytes()
manifest = dict(schema='radio-runtime-capture-b-lossless-originals-v1',
    capture_identity=report['capture_identity'], original_root=str(ROOT),
    original_root_identity=root_before, original_members=rows,
    original_members_unmodified=True, full_copies_verified=True,
    file_count=len(rows), file_bytes=sum(r['bytes'] for r in rows),
    directory_inclusive_logical_bytes=caller['final_scope']['logical_bytes'],
    directory_inclusive_allocated_bytes=caller['final_scope']['allocated_bytes'],
    whole_scope_elapsed_seconds=caller['whole_scope_elapsed_seconds'],
    prepared_commit=report['prepared_commit'], activation_commit=report['activation_commit'],
    child_status=child['status'], admission_status=child['admission_status'],
    scientific_certificate_issued=False, retry_allowed=False)
(NS / 'actual-lossless-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
print(json.dumps({k:v for k,v in manifest.items() if k != 'original_members'}, sort_keys=True))
