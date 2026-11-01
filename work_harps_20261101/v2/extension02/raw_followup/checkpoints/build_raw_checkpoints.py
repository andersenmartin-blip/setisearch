"""Preserve completed bounded raw_followup products without interpreting arrays.

No networking or publication. Uses the final product manifest and frozen selection.
Two fixed four-exposure partitions contain every downloaded raw/TAR product and
all selected job receipts exactly once. Any explicitly quarantined unexpected
partial prefixes are retained exactly once as non-science diagnostic evidence. Frozen inputs and acquisition metadata
are repeated identically. Existing extension02 1D-input checkpoints are untouched.
"""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile

OUT = Path(__file__).resolve().parent
FOLLOW = OUT.parent
EXT = FOLLOW.parent
BASE = EXT.parents[1]
DELIVERY = BASE.parents[1] / 'harps_long_delivery'
STAMP = (2026, 11, 1, 0, 0, 0)
PER_PART = 4
MAX_PART_BYTES = 150_000_000


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path):
    return dict(path=str(path.relative_to(BASE)), bytes=path.stat().st_size, sha256=sha(path))


def write_zip(path, members):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for source in members:
            info = zipfile.ZipInfo(str(source.relative_to(BASE)), STAMP)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info._compresslevel = 6
            with source.open('rb') as src, archive.open(info, 'w') as dst:
                shutil.copyfileobj(src, dst, length=1_048_576)


def main():
    manifest_path = FOLLOW / 'products/MANIFEST.json'
    assert manifest_path.is_file(), 'Final acquisition manifest required'
    manifest = json.loads(manifest_path.read_text())
    products = manifest['products']
    freeze_path = FOLLOW / 'FOLLOWUP_FREEZE.json'
    freeze = json.loads(freeze_path.read_text())
    jobs = json.loads((FOLLOW / 'JOBS.json').read_text())
    selected = list(csv.DictReader((FOLLOW / 'SELECTED_EXPOSURES.csv').open()))
    events = list(csv.DictReader((FOLLOW / 'SELECTED_EVENTS.csv').open()))
    ids = [r['dp_id'] for r in selected]
    key = lambda r: (r['dp_id'], r['kind'], r['filename'])
    assert len(ids) == len(set(ids)) == freeze['selected_exposures'] == 8
    assert len(events) == freeze['selected_events'] == 65
    assert len(products) == len(jobs) == freeze['planned_products'] == 16
    assert len(set(map(key, jobs))) == len(jobs)
    assert list(map(key, products)) == list(map(key, jobs)), 'Job order/coverage mismatch'
    assert {r['dp_id'] for r in products} == set(ids)
    assert manifest['known_returned_payload_bytes'] <= manifest['charged_payload_bytes'] <= manifest['payload_cap_bytes']
    assert manifest['reserved_bytes'] == 0

    common = []
    for relative, digest in freeze['source_hashes'].items():
        source = BASE / relative
        assert source.resolve().is_relative_to(BASE.resolve())
        assert sha(source) == digest, relative
        common.append(source)
    # These records are static once the final acquisition manifest exists.
    common += [freeze_path, FOLLOW / 'DOWNLOAD_STARTED.json', manifest_path,
               FOLLOW / 'PREPARATION_AUDIT.json',
               Path(__file__), OUT / 'RESTORE.md']
    for name in ['GUARD_TEST_RESULTS.json', 'PREPUBLICATION_AMENDMENT.json', 'INDEPENDENT_CODE_REVIEW.json',
                 'ROOT_PUBLICATION_VERIFICATION.json']:
        p = FOLLOW / name
        if p.is_file():
            common.append(p)
    common = sorted(set(common), key=lambda p: str(p.relative_to(BASE)))
    common_records = [record(p) for p in common]

    # Quarantined transfer leftovers remain distinct from admitted scientific inputs.
    quarantine_files = []
    quarantine_record = None
    for candidate in [FOLLOW / 'quarantine', FOLLOW / 'diagnostics/stale_partial_files']:
        if candidate.exists():
            quarantine_files.extend(sorted(p for p in candidate.rglob('*') if p.is_file() and not p.name.endswith('.json')))
    quarantine_files = sorted(set(quarantine_files), key=lambda p: str(p.relative_to(BASE)))
    if quarantine_files:
        candidates = [FOLLOW / 'quarantine/ANOMALY.json', FOLLOW / 'PARTIAL_FILE_ANOMALY.json', FOLLOW / 'diagnostics/PARTIAL_FILE_ANOMALY.json']
        present = [p for p in candidates if p.is_file()]
        assert len(present) == 1, 'Exactly one explicit anomaly record required'
        quarantine_record = present[0]
        common.append(quarantine_record)
        common.append(OUT / 'ATTEMPT01_PRE_QUARANTINE.log')
        common = sorted(set(common), key=lambda p: str(p.relative_to(BASE)))
        common_records = [record(p) for p in common]
        assert len(quarantine_files) == 3
        assert sum(p.stat().st_size for p in quarantine_files) == 4_194_304
        anomaly = json.loads(quarantine_record.read_text())
        assert anomaly['combined_bytes'] == 4_194_304
        assert {str((FOLLOW / r['preserved_relative_path']).resolve()) for r in anomaly['files']} == {str(p.resolve()) for p in quarantine_files}
        for r in anomaly['files']:
            part = FOLLOW / r['preserved_relative_path']
            final = FOLLOW / r['final_relative_path']
            assert part.stat().st_size == r['bytes'] and sha(part) == r['sha256']
            assert sha(final) == r['final_sha256']
            with final.open('rb') as stream:
                assert stream.read(r['bytes']) == part.read_bytes()
    quarantine_records = [record(p) for p in quarantine_files]

    grouped = {}
    downloaded = []
    failed = []
    for dp_id in ids:
        rows = [r for r in products if r['dp_id'] == dp_id]
        assert len(rows) == 2 and {r['kind'] for r in rows} == {'RAW', 'ANCILLARY'}
        members = []
        for r in rows:
            source = FOLLOW / 'products' / r['filename']
            receipt = source.with_name(source.name + '.json')
            assert json.loads(receipt.read_text()) == r
            if r['status'] == 'DOWNLOADED':
                assert str(source.relative_to(BASE)) == r['relative_path']
                assert source.stat().st_size == r['bytes'] == r['advertised_bytes']
                assert sha(source) == r['sha256']
                members.append(source)
                downloaded.append(r)
            else:
                assert r['status'] == 'FAILED'
                assert not source.exists(), 'Unexpected failed-product bytes must be reviewed'
                failed.append(r)
            members.append(receipt)
        grouped[dp_id] = members
    actual_data = {str(p.relative_to(BASE)) for p in (FOLLOW / 'products').iterdir()
                   if p.is_file() and not p.name.endswith('.json')}
    assert actual_data == {r['relative_path'] for r in downloaded}, 'Unmanifested data or partial files'
    assert sum(r['bytes'] for r in downloaded) <= manifest['known_returned_payload_bytes']
    # Previously created 1D checkpoints are read-only and checked again at completion.
    main_index = DELIVERY / 'INPUT_CHECKPOINTS.json'
    main_index_sha = sha(main_index)
    prior_parts = [(Path(r['local_path']), r['sha256']) for r in json.loads(main_index.read_text())['parts']]
    for path, digest in prior_parts:
        assert sha(path) == digest

    inventory_path = DELIVERY / 'RAW_INPUT_CHECKPOINTS.json'
    assert not inventory_path.exists() and not (OUT / 'RAW_INPUT_CHECKPOINTS.json').exists()
    assert not list(DELIVERY.glob('SETI_HARPS_EXTENSION02_RAW_INPUTS_PART*_2026-11-01.zip'))
    parts = []
    archived_products = []
    archived_receipts = []
    for offset in range(0, len(ids), PER_PART):
        chosen = ids[offset:offset + PER_PART]
        filename = f'SETI_HARPS_EXTENSION02_RAW_INPUTS_PART{len(parts)+1}_2026-11-01.zip'
        dest = DELIVERY / filename
        temp = DELIVERY / (filename + '.partial')
        diagnostic_members = quarantine_files if offset == 0 else []
        members = [p for dp_id in chosen for p in grouped[dp_id]] + common + diagnostic_members
        assert len(members) == len(set(members))
        records = [record(p) for p in members]
        write_zip(temp, members)
        assert temp.stat().st_size <= MAX_PART_BYTES
        with zipfile.ZipFile(temp) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == [r['path'] for r in records]
            for r in records:
                assert archive.getinfo(r['path']).file_size == r['bytes']
                with archive.open(r['path']) as stream:
                    assert hashlib.file_digest(stream, 'sha256').hexdigest() == r['sha256']
        temp.replace(dest)
        part_products = [r for r in downloaded if r['dp_id'] in chosen]
        archived_products.extend(r['relative_path'] for r in part_products)
        archived_receipts.extend(key(r) for r in products if r['dp_id'] in chosen)
        part = dict(filename=filename, local_path=str(dest), bytes=dest.stat().st_size,
                    sha256=sha(dest), files=len(records), selected_exposures=len(chosen),
                    downloaded_products=len(part_products), quarantined_non_science_files=len(diagnostic_members),
                    failed_products=sum(r['dp_id'] in chosen for r in failed),
                    exposure_ids=chosen, members=records)
        parts.append(part)
        (DELIVERY / 'RAW_INPUT_CHECKPOINTS_PROGRESS.json').write_text(json.dumps(
            dict(complete=False, exposures_packaged=offset + len(chosen), parts=parts), indent=2) + '\n')
        print(json.dumps({k: part[k] for k in ['filename', 'bytes', 'sha256', 'files', 'selected_exposures', 'downloaded_products']}), flush=True)
    assert len(archived_products) == len(set(archived_products)) == len(downloaded)
    assert set(archived_products) == actual_data
    assert sorted(archived_receipts) == sorted(map(key, jobs))
    assert sum(p['quarantined_non_science_files'] for p in parts) == len(quarantine_files)
    for r in quarantine_records:
        assert sha(BASE / r['path']) == r['sha256']
    for r in common_records:
        assert sha(BASE / r['path']) == r['sha256'], r['path']
    assert sha(main_index) == main_index_sha
    for path, digest in prior_parts:
        assert sha(path) == digest
    summary = dict(complete=True, selected_exposures=len(ids), selected_event_records=len(events),
        planned_products=len(jobs), downloaded_products=len(downloaded), failed_products=len(failed),
        source_product_bytes=sum(r['bytes'] for r in downloaded),
        quarantined_non_science_files=quarantine_records,
        quarantined_bytes=sum(r['bytes'] for r in quarantine_records),
        acquisition_anomaly_record=str(quarantine_record.relative_to(BASE)) if quarantine_record else None,
        anomaly_interpretation='Three unexpected partial prefixes are preserved as excluded diagnostic bytes. Their cause is unknown; recorded transfer ledger is not asserted to explain their presence.' if quarantine_files else None,
        acquisition_manifest_sha256=sha(manifest_path), followup_freeze_sha256=sha(freeze_path),
        packaging_script_sha256=sha(Path(__file__)), prior_1d_index_sha256=main_index_sha,
        prior_1d_checkpoint_files_unchanged=True, array_values_interpreted_by_packager=False,
        max_exposures_per_part=PER_PART, max_part_bytes=MAX_PART_BYTES, archive_timestamp=list(STAMP),
        reproducibility='Fixed ZIP timestamp, permissions, compression level6, source bytes and member order.',
        coverage='All selected raw/TAR product receipts and successful source products exactly once; quarantined partials exactly once as non-science evidence; shared frozen metadata repeated in each part.',
        verification='Every source file SHA256; all ZIP member SHA256 and sizes plus testzip CRC; complete job/manifest/on-disk product coverage.',
        parts=parts)
    text = json.dumps(summary, indent=2) + '\n'
    inventory_path.write_text(text)
    (OUT / 'RAW_INPUT_CHECKPOINTS.json').write_text(text)
    print(json.dumps(dict(complete=True, parts=len(parts), products=len(downloaded),
                         bytes=sum(r['bytes'] for r in parts), inventory=str(inventory_path))), flush=True)


if __name__ == '__main__':
    main()
