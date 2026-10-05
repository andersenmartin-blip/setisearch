"""Read-only administrative comparison; never invokes any recorded scope."""
import hashlib
import json
import os
from pathlib import Path
import stat

REPO = Path('/workspace/scratch/d804553c0e89/setisearch-status-20261004')
NEW = REPO / 'results_radio_runtime_bootstrap_preparation_20261005a'
A = 'results_radio_runtime_capture_preparation_20261004a'
B = 'results_radio_runtime_capture_preparation_20261004b'
CACHE = {}


def identity(s):
    return dict(device=s.st_dev, inode=s.st_ino, mode=f'{stat.S_IMODE(s.st_mode):04o}',
                bytes=s.st_size, allocated_bytes=s.st_blocks * 512,
                mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, links=s.st_nlink)


def read(path):
    path = Path(path)
    key = str(path)
    if key in CACHE:
        return CACHE[key]
    # Snapshot ancestor checks and held no-follow leaf; no symlinks admitted.
    for parent in reversed(path.parents):
        assert stat.S_ISDIR(os.lstat(parent).st_mode), ('ancestor', str(parent))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1, key
        chunks = []
        while True:
            part = os.read(fd, 1024 * 1024)
            if not part:
                break
            chunks.append(part)
        raw = b''.join(chunks)
        after = os.fstat(fd)
        assert identity(before) == identity(after) == identity(os.lstat(path)), key
        assert len(raw) == before.st_size, key
        pin = dict(path=key, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                   git_blob=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
                   identity=identity(before))
        CACHE[key] = raw, pin
        return raw, pin
    finally:
        os.close(fd)


def doc(path):
    raw, pin = read(path)
    return json.loads(raw), pin


def match_content(path, expected):
    raw, pin = read(path)
    for field in ('bytes', 'sha256', 'git_blob'):
        if field in expected:
            assert pin[field] == expected[field], (str(path), field, pin[field], expected[field])
    if 'mode' in expected:
        assert pin['identity']['mode'] == expected['mode'][-4:], (str(path), 'mode')
    return raw, pin


def root_check(path, expected, names):
    before = os.lstat(path)
    assert stat.S_ISDIR(before.st_mode), str(path)
    assert sorted(os.listdir(path)) == sorted(names), (str(path), 'members')
    after = os.lstat(path)
    observed = identity(before)
    assert observed == identity(after), (str(path), 'changed during listing')
    for field, value in expected.items():
        assert observed[field] == value, (str(path), field, observed[field], value)
    return dict(path=str(path), expected_identity=expected, observed_identity=observed,
                exact_member_names=sorted(names), recorded_fields_match=True)


def original_member(original_path, copy_path, expected_content, expected_identity):
    raw, pin = match_content(original_path, expected_content)
    for field, value in expected_identity.items():
        assert pin['identity'][field] == value, (str(original_path), field, pin['identity'][field], value)
    copied, copy_pin = match_content(copy_path, expected_content)
    assert copied == raw, (str(original_path), 'copy differs')
    return dict(original=pin, repository_copy=copy_pin, expected_original_identity=expected_identity,
                full_original_and_copy_bytes_equal=True, recorded_original_metadata_match=True)


def main():
    a_authority, a_pin = doc(REPO / B / 'administrative/original-a-post-observation-preservation.json')
    a_lossless, al_pin = doc(REPO / A / 'actual-lossless-manifest.json')
    b_review, br_pin = doc(REPO / B / 'actual-independent-review.json')
    b_lossless, bl_pin = doc(REPO / B / 'actual-lossless-manifest.json')
    prep_meta, pm_pin = doc(REPO.parent / 'capture-b-preparation-meta.json')
    prep_authority, pa_pin = doc(REPO / B / 'administrative/prepared-artifact-preservation.json')
    pilot_authority, pt_pin = doc(REPO / B / 'pilot-actual-historical-tail-preservation.json')
    original_a = []
    for row in a_authority['original_files']:
        expected = {key: row['original_' + key] for key in
                    ('device', 'inode', 'mode', 'mtime_ns', 'ctime_ns', 'allocated_bytes')}
        expected['bytes'] = row['bytes']
        copy_path = REPO / A / 'actual' / Path(row['path']).name
        original_a.append(original_member(row['path'], copy_path, row, expected))
    assert len(original_a) == 8
    a_root_expected = {key: a_lossless['original_root_' + key] for key in ('device', 'inode', 'mode')}
    a_root_expected.update(bytes=a_lossless['final_scope']['root_directory_bytes'],
                           allocated_bytes=a_lossless['final_scope']['root_directory_allocated_bytes'])
    a_root = root_check(a_lossless['original_root'], a_root_expected,
                        [Path(row['path']).name for row in a_authority['original_files']])
    original_b = []
    for row in b_lossless['original_members']:
        original_b.append(original_member(row['original_path'], REPO / row['repository_path'],
                                          row, row['original_identity']))
    assert len(original_b) == 8
    b_root = root_check(b_lossless['original_root'], b_lossless['original_root_identity'],
                        [row['name'] for row in b_lossless['original_members']])
    precision_differences = []
    old_review_rows = {row['name']: row for row in b_review['actual_original_scope']['members']}
    for row in b_lossless['original_members']:
        old = old_review_rows[row['name']]
        for field in ('bytes', 'sha256', 'git_blob', 'original_path', 'repository_path'):
            assert old[field] == row[field], (row['name'], field)
        for field, precise in row['original_identity'].items():
            rounded = old['original_identity'][field]
            if field in ('mtime_ns', 'ctime_ns'):
                if precise != rounded:
                    precision_differences.append(dict(member=row['name'], field=field,
                                                     raw_python_decimal=str(precise),
                                                     historical_review_decimal=str(rounded)))
            else:
                assert precise == rounded, (row['name'], field)
    for field, precise in b_lossless['original_root_identity'].items():
        rounded = b_review['actual_original_scope']['root_identity'][field]
        if field in ('mtime_ns', 'ctime_ns'):
            if precise != rounded:
                precision_differences.append(dict(member='root', field=field,
                                                 raw_python_decimal=str(precise),
                                                 historical_review_decimal=str(rounded)))
        else:
            assert precise == rounded, ('root', field)
    a_sources = [match_content(row['path'], row)[1] for row in a_authority['original_decoded_source_files']]
    assert len(a_sources) == 7
    a_extra = []
    for suffix, sha in [('freeze', a_authority['original_freeze_sha256']),
                        ('activate', a_authority['original_activation_sha256'])]:
        a_extra.append(match_content(REPO / 'config' / ('radio_runtime_metadata_capture_20261004a.' + suffix + '.json'),
                                    {'sha256': sha})[1])
    added = [row for row in prep_meta['files'] if row['status'] == 'A']
    assert len(added) == 52 and added == prep_authority['files']
    b_preparation = [match_content(REPO / row['path'], row)[1] for row in added]
    excluded = [row['path'] for row in prep_meta['files'] if row['status'] == 'M']
    assert sorted(excluded) == sorted(['PROJECT_DIRECTION.md', 'PROJECT_STATUS.md',
                                     'RADIO_PILOT_INTERIM_2026-10-03.md', 'RADIO_TWO_WEEK_PLAN_2026-09-26.md'])
    a_result = json.loads(read(Path(a_lossless['original_root']) / 'supervisor-result.json')[0])
    b_result = json.loads(read(Path(b_lossless['original_root']) / 'supervisor-result.json')[0])
    b_marker = match_content(REPO / 'config/radio_runtime_metadata_capture_20261004b.activate.json',
                             {'sha256': b_result['activation_sha256']})[1]
    assert a_result['status'] == 'CLOSED_FAILED' and a_result['failure'] == 'CHILD_NONZERO'
    assert b_result['status'] == 'OBSERVED_METADATA_ONLY' and b_result['failure'] is None
    for result in (a_result, b_result):
        assert result['spent_forever'] is True and result['retry_allowed'] is False
        assert result['engineering_reservation_spent'] is True
        assert all(value is False for value in result['authority'].values())
    stderr = read(Path(a_lossless['original_root']) / 'child.stderr.raw')[0]
    assert stderr == b'CLOSED_FAILED ElfMetadataError: dynamic string table has no unique file-backed PT_LOAD\n'
    plan_path = REPO / prep_meta['additional_full_readback_input']['path']
    plan_raw, plan_pin = match_content(plan_path, prep_meta['additional_full_readback_input'])
    plan = json.loads(plan_raw)
    pending = plan['remaining_authentic_receipt_requirements']['all_eleven_fields_still_pending']
    assert len(pending) == 11 and len(set(pending)) == 11
    assert len(plan['authority']) == 16 and all(value is False for value in plan['authority'].values())
    pilot_raw, _ = read(REPO / 'RADIO_PILOT_INTERIM_2026-10-03.md')
    marker = pilot_authority['historical_marker'].encode()
    assert pilot_raw.count(marker) == 1
    tail = pilot_raw[pilot_raw.index(marker):]
    assert len(tail) == pilot_authority['historical_tail_bytes']
    assert hashlib.sha256(tail).hexdigest() == pilot_authority['historical_tail_sha256']
    # Recheck the held-read metadata of immutable inputs before writing only NEW output.
    # The four current status documents are allowed updates; only the pilot's tail is bound.
    for path, (_, pin) in CACHE.items():
        if Path(path).name not in excluded:
            assert identity(os.lstat(path)) == pin['identity'], (path, 'changed after read')
    for root in (a_root, b_root):
        assert identity(os.lstat(root['path'])) == root['observed_identity'], root['path']
    report = dict(
        schema='radio-bootstrap-prior-scope-preservation-v1', date_utc='2026-10-05',
        verdict='ALL_RECORDED_ORIGINAL_BYTES_AND_COMPARABLE_METADATA_PRESERVED',
        review_scope='Read-only administrative local repository and closed A/B scope comparison; no imports, gate replay, new capture, runtime reads, network or scientific data reads.',
        metadata_method='Full held O_NOFOLLOW sole-link regular-file reads, pre/post fstat and named lstat equality; ancestor directory snapshots; final immutable input metadata recheck. Atime is excluded. This is an observation, not a filesystem locking or crash-durability certificate.',
        authority_pins=[a_pin, al_pin, br_pin, bl_pin, pm_pin, pa_pin, pt_pin],
        original_a=dict(capture_identity=a_authority['original_capture_identity'], root=a_root,
                        members=original_a, decoded_source_pins=a_sources, freeze_and_activation_pins=a_extra,
                        root_ns_comparison='UNQUALIFIED: retained A root authority has no exact mtime/ctime ns baseline; all recorded A root fields match, and exact file ns baselines match.',
                        status='CLOSED_FAILED', failure='CHILD_NONZERO', raw_stderr_bytes=87,
                        failure_provenance='Retained exact stderr records only the ElfMetadataError class/text. The failing ELF path was not retained; no exact-path attribution or reconstructed cause is claimed.',
                        reservation_spent_forever=True, retry_or_refund=False),
        original_b=dict(capture_identity=b_lossless['capture_identity'], root=b_root, members=original_b,
                        preparation_pins=b_preparation, activation_pin=b_marker,
                        exact_ns_authority=bl_pin['path'], exact_raw_python_ns_all_match=True,
                        historical_review_ns_comparison='UNQUALIFIED: actual-independent-review.json contains rounded JS numeric timestamps. It remains unchanged. The new exact comparison uses retained raw Python actual-lossless-manifest.json, without retroactively certifying the rounded review.',
                        historical_review_precision_differences=precision_differences,
                        status='OBSERVED_METADATA_ONLY', admission_status=b_lossless['admission_status'],
                        reservation_spent_forever=True, retry_or_refund=False),
        science_controls=dict(original_plan_pin=plan_pin, original_plan_authority=plan['authority'],
                              all_eleven_scientific_fields_pending=pending,
                              preserved_dispositions=plan['preserved_dispositions'],
                              historical_b_scientific_boundary=b_review['scientific_boundary'],
                              pilot_historical_tail=dict(marker=pilot_authority['historical_marker'],
                                                         bytes=len(tail), sha256=hashlib.sha256(tail).hexdigest(), unchanged=True),
                              four_current_status_documents_authorized_updates=excluded,
                              original_science_data_not_read=True, new_scientific_certificate_issued=False),
        all_sixteen_original_files_and_copies_full_bytes_match=True,
        all_recorded_original_file_dev_inode_mode_size_allocation_exact_ns_match=True,
        all_seven_a_sources_and_fifty_two_b_added_preparation_pins_match=True,
        original_files_modified=False, original_scopes_invoked=False,
        review_script_pin=read(NEW / 'administrative/review_prior_scopes.py')[1])
    output = NEW / 'administrative/prior-scope-preservation.json'
    raw = (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode()
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o644)
    try:
        view = memoryview(raw)
        while view:
            count = os.write(fd, view)
            assert count > 0
            view = view[count:]
    finally:
        os.close(fd)
    print(json.dumps(dict(verdict=report['verdict'], report=str(output), bytes=len(raw),
                          sha256=hashlib.sha256(raw).hexdigest(),
                          git_blob=hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
                          original_files=16, exact_copies=16, a_sources=7, b_preparation=52,
                          historical_b_precision_differences=len(precision_differences))))


if __name__ == '__main__':
    main()
