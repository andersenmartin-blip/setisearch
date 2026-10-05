"""Independent artifact custody verification; never opens wheel members."""
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'verified-package-source'
REPO = 'andersenmartin-blip/setisearch'
RUN = 37337067481
ACTIVATION = '8f05d8b92ac0880d3f6b0b49dc6a399bd2437359'
PREPARATION = '06b3f7ec212b33fbe69bc37b8d2a5ad5cb5851e8'
TREE = '9f61d1d2a967b46f453b53702c937d8a8bd6ce2a'
FREEZE_PATH = 'config/radio_package_source_20261005a.freeze.json'
MARKER_PATH = 'config/radio_package_source_20261005a.activate.json'
FREEZE_HASH = '64e4f1051169d5f3e5f38407632e6a3255654004c0b6ad0730808924a3cc1eb5'
IDENTITY = 'radio-hosted-package-source-20261005a'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def safe_entries(archive, size_cap):
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    require(len(names) == len(set(names)), 'duplicate ZIP names')
    require(sum(e.file_size for e in entries) <= size_cap, 'ZIP expanded size cap')
    for entry in entries:
        p = PurePosixPath(entry.filename)
        mode = entry.external_attr >> 16
        require(not p.is_absolute() and '..' not in p.parts and '\\' not in entry.filename,
                'unsafe ZIP path')
        require(not entry.is_dir() and not (entry.flag_bits & 1), 'directory/encrypted ZIP')
        require(stat.S_IFMT(mode) in (0, stat.S_IFREG), 'nonregular ZIP member')
        require(entry.compress_type == zipfile.ZIP_STORED, 'unexpected ZIP compression')
    return names

def main():
    evidence = json.loads((ROOT / 'hosted-run-evidence.json').read_text())
    run = evidence['run']
    require(run['id'] == RUN and run['head_sha'] == ACTIVATION and run['run_attempt'] == 1,
            'wrong run identity')
    require(run['path'] == '.github/workflows/radio-package-source-20261005a.yml' and
            run['event'] == 'push' and run['head_branch'] == 'm43-support-qualification' and
            run['repository']['full_name'] == REPO and run['status'] == 'completed' and
            run['conclusion'] == 'success', 'run authority')
    require(len(evidence['jobs']) == 1 and evidence['jobs'][0]['conclusion'] == 'success',
            'job authority')
    steps = {s['name']: s for s in evidence['jobs'][0]['steps']}
    require(steps['Acquire unchanged wheel bytes once']['conclusion'] == 'success' and
            steps['Require complete package-source result']['conclusion'] == 'success',
            'acquisition/final step authority')
    admission = evidence['activation']
    require(admission['ok'] is True and admission['commit'] == ACTIVATION and
            [p['sha'] for p in admission['parents']] == [PREPARATION] and
            admission['markerExact'] is True and admission['head'] == PREPARATION,
            'prospective activation admission')
    freeze_raw = (ROOT / FREEZE_PATH).read_bytes()
    require(sha(freeze_raw) == FREEZE_HASH, 'independent freeze hash')
    freeze = json.loads(freeze_raw)
    marker_raw = (ROOT / MARKER_PATH).read_bytes()
    expected_identity = dict(identity=IDENTITY, repository=REPO, run_id=str(RUN),
            run_attempt=1, github_sha=ACTIVATION, prepared_commit=PREPARATION,
            prepared_tree=TREE, freeze_sha256=FREEZE_HASH, marker_sha256=sha(marker_raw),
            source_sha256=freeze['sources'])
    groups = {'receipt', 'numpy', 'h5py', 'hdf5plugin-part000', 'hdf5plugin-part001'}
    artifacts = evidence['artifacts']
    require(len(artifacts) == 5 and {a['name'] for a in artifacts} ==
            {IDENTITY.replace('radio-hosted-', 'radio-') + '-' + g for g in groups},
            'exact five artifacts')
    by_group = {}
    archive_evidence = []
    for a in artifacts:
        path = Path(a['local_path'])
        raw = path.read_bytes()
        require(not a['expired'] and 0 < len(raw) == a['size_in_bytes'] < 24 * 1024 * 1024,
                'artifact size or expiration')
        require('sha256:' + sha(raw) == a['digest'], 'GitHub ZIP digest')
        require(a['workflow_run']['id'] == RUN and
                a['workflow_run']['head_sha'] == ACTIVATION, 'artifact run binding')
        group = a['name'].removeprefix('radio-package-source-20261005a-')
        by_group[group] = path
        archive_evidence.append({k: a[k] for k in
            ('id', 'name', 'size_in_bytes', 'digest', 'created_at', 'expires_at')})
    with zipfile.ZipFile(by_group['receipt']) as archive:
        names = safe_entries(archive, 1024 * 1024)
        expected_sources = set(freeze['sources']) | {FREEZE_PATH, MARKER_PATH}
        require(set(names) == {'manifest.json', 'spent.json'} |
                {'sources/' + p for p in expected_sources}, 'receipt member set')
        receipt_files = {p: archive.read(p) for p in names}
    for source in expected_sources:
        raw = receipt_files['sources/' + source]
        require(raw == (ROOT / source).read_bytes(), 'source bytes differ: ' + source)
        if source in freeze['sources']:
            require(sha(raw) == freeze['sources'][source], 'frozen source hash')
    manifest = json.loads(receipt_files['manifest.json'])
    spent = json.loads(receipt_files['spent.json'])
    require(manifest['schema'] == 'radio-hosted-package-source-receipt-v1' and
            manifest['identity'] == expected_identity and
            manifest['status'] == 'EXACT_THREE_ORIGINAL_ARCHIVES' and
            manifest['limits'] == freeze['limits'] and
            'finalization_error' not in manifest and manifest['skipped_wheels'] == [] and
            manifest['received_bytes'] == manifest['retained_original_archive_bytes'] == 68409067,
            'complete receipt')
    require(manifest['package_only'] is True and manifest['runtime_qualified'] is False and
            manifest['scientific_authority'] is False and manifest['automatic_successor'] is False,
            'receipt scope')
    require(spent['schema'] == 'radio-hosted-package-source-spent-v1' and
            spent['identity'] == expected_identity and
            all(spent[x] is True for x in ('spent', 'single_use', 'package_only', 'before_first_request'))
            and spent['automatic_successor'] is False, 'spent identity')
    require(len(manifest['requests']) == 3, 'request count')
    parts_all = []
    verified = []
    raw_wheels = []
    for n, (wheel, request) in enumerate(zip(freeze['wheels'], manifest['requests']), 1):
        require(request['request_number'] == n and request['attempts'] == 1 and
                request['http_status'] == 200 and request['method'] == 'GET' and
                request['status'] == 'EXACT_ORIGINAL_ARCHIVE' and request['error'] is None,
                'request completion')
        for key in ('name', 'filename', 'url'):
            require(request[key] == wheel[key], 'wheel request identity')
        for prefix in ('expected', 'received', 'retained'):
            require(request[prefix + '_bytes'] == wheel['bytes'] and
                    request[prefix + '_sha256'] == wheel['sha256'], 'wheel request custody')
        expected_sizes = [wheel['bytes']] if wheel['name'] != 'hdf5plugin' else [24117248, 22280483]
        require(len(request['exports']) == len(expected_sizes), 'part count')
        raw = b''
        for index, (part, length) in enumerate(zip(request['exports'], expected_sizes)):
            group = wheel['name'] if wheel['name'] != 'hdf5plugin' else 'hdf5plugin-part%03d' % index
            basename = wheel['filename'] + '.part%03d' % index
            require(part['artifact_group'] == group and part['index'] == index and
                    part['path'] == 'exports/' + group + '/' + basename and
                    part['bytes'] == length, 'part path or sequence')
            with zipfile.ZipFile(by_group[group]) as archive:
                require(safe_entries(archive, 24117248) == [basename], 'wheel ZIP member set')
                data = archive.read(basename)
            require(len(data) == length and sha(data) == part['sha256'], 'raw part integrity')
            raw += data
            parts_all.append(part)
        require(len(raw) == wheel['bytes'] and sha(raw) == wheel['sha256'], 'whole wheel integrity')
        raw_wheels.append((wheel['filename'], raw))
        verified.append({k: wheel[k] for k in ('name', 'version', 'filename', 'bytes', 'sha256')})
    require(parts_all == manifest['artifacts'], 'top-level exports consistency')
    result = dict(schema='radio-package-source-independent-verification-v1',
            status='EXACT_THREE_ORIGINAL_ARCHIVES_VERIFIED', repository=REPO,
            run_id=RUN, run_attempt=1, activation_commit=ACTIVATION,
            prepared_commit=PREPARATION, prepared_tree=TREE, freeze_sha256=FREEZE_HASH,
            total_original_bytes=68409067, wheels=verified, artifacts=archive_evidence,
            all_zip_digests_match=True, all_source_bytes_match=True,
            all_part_and_whole_hashes_match=True, no_wheel_members_opened=True,
            runtime_qualified=False, scientific_authority=False)
    OUTPUT.mkdir(exist_ok=False)
    (OUTPUT / 'originals').mkdir()
    for filename, raw in raw_wheels:
        (OUTPUT / 'originals' / filename).write_bytes(raw)
    for name, raw in receipt_files.items():
        destination = OUTPUT / 'receipt' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    (OUTPUT / 'independent-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
