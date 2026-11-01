"""Archive all completed extension02 input bytes without interpreting FITS arrays.

Requires a final acquisition result and manifest. Two fixed 50-exposure partitions
retain original frozen selection order. All existing input bytes, including any
header-excluded FITS files, and each selected exposure's final receipt are archived
exactly once. Frozen code/metadata and final acquisition records are repeated in
each part. Archive members preserve paths relative to work_harps_20261101.
No network, scientific analysis, or publication occurs here.
"""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile

OUT = Path(__file__).resolve().parent
EXT = OUT.parent
BASE = EXT.parents[1]
DELIVERY = BASE.parents[1] / 'harps_long_delivery'
STAMP = (2026, 11, 1, 0, 0, 0)
MAX_PART_BYTES = 250_000_000
PART_EXPOSURES = 50


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path):
    return dict(path=str(path.relative_to(BASE)), bytes=path.stat().st_size,
                sha256=sha(path))


def write_zip(dest, members):
    with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED,
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
    acquisition = EXT / 'acquisition'
    manifest_path = acquisition / 'DOWNLOAD_MANIFEST.json'
    result_path = acquisition / 'ACQUISITION_RESULT.json'
    assert manifest_path.is_file() and result_path.is_file(), 'Final acquisition records required'
    manifest = json.loads(manifest_path.read_text())
    result = json.loads(result_path.read_text())
    selected = list(csv.DictReader((EXT / 'MAIN100.csv').open()))
    freeze = json.loads((EXT / 'FREEZE.json').read_text())
    ids = [row['dp_id'] for row in selected]
    assert len(ids) == len(set(ids)) == len(manifest) == result['selected_files'] == 100
    assert [row['dp_id'] for row in manifest] == ids
    assert sum(result['result_counts'].values()) == 100
    assert result['conservative_charged_payload_bytes'] <= result['payload_budget_bytes']
    assert result['array_values_inspected'] is False

    common = []
    for relative, expected in freeze['source_hashes'].items():
        source = BASE / relative
        assert source.resolve().is_relative_to(BASE.resolve())
        assert sha(source) == expected, relative
        common.append(source)
    common.extend([EXT / 'FREEZE.json', EXT / 'INDEPENDENT_CODE_REVIEW.json',
                   Path(__file__), OUT / 'RESTORE.md'])
    common.extend(sorted(p for p in acquisition.iterdir() if p.is_file()))
    common = sorted(set(common), key=lambda p: str(p.relative_to(BASE)))
    common_records = [record(p) for p in common]
    grouped = {}
    existing = []
    missing = []
    admitted = []
    excluded_existing = []
    for row in manifest:
        dp_id = row['dp_id']
        receipt = acquisition / 'receipts' / (dp_id.replace(':', '_') + '.json')
        assert json.loads(receipt.read_text()) == row, dp_id
        paths = []
        source = BASE / row['relative_path']
        assert source.resolve().is_relative_to((EXT / 'data').resolve())
        if source.exists():
            assert source.stat().st_size == row['bytes'], dp_id
            assert sha(source) == row['sha256'], dp_id
            assert row['download_status'].startswith('DOWNLOADED'), dp_id
            paths.append(source)
            existing.append(row)
            if row.get('header_status') == 'PASS_METADATA_ONLY':
                assert all(row['checks'].values()), dp_id
                admitted.append(row)
            else:
                excluded_existing.append(row)
        else:
            assert row['download_status'] == 'FAILED', dp_id
            missing.append(row)
        paths.append(receipt)
        grouped[dp_id] = paths
    on_disk = {str(p.relative_to(BASE)) for p in (EXT / 'data').rglob('*') if p.is_file()}
    assert on_disk == {r['relative_path'] for r in existing}, 'Unexpected or unmanifested data bytes'
    assert sum(row['bytes'] for row in existing) <= result['returned_payload_bytes']

    DELIVERY.mkdir(exist_ok=True)
    inventory_path = DELIVERY / 'INPUT_CHECKPOINTS.json'
    assert not inventory_path.exists() and not (OUT / 'INPUT_CHECKPOINTS.json').exists()
    assert not list(DELIVERY.glob('SETI_HARPS_EXTENSION02_INPUTS_PART*_2026-11-01.zip'))
    parts = []
    archived_data = []
    archived_receipts = []
    for offset in range(0, len(ids), PART_EXPOSURES):
        chosen = ids[offset:offset + PART_EXPOSURES]
        filename = f'SETI_HARPS_EXTENSION02_INPUTS_PART{len(parts)+1}_2026-11-01.zip'
        destination = DELIVERY / filename
        temporary = DELIVERY / (filename + '.partial')
        members = [p for dp_id in chosen for p in grouped[dp_id]] + common
        assert len(members) == len(set(members))
        records = [record(p) for p in members]
        write_zip(temporary, members)
        assert temporary.stat().st_size <= MAX_PART_BYTES, 'Part exceeds documented bound'
        with zipfile.ZipFile(temporary) as archive:
            assert archive.testzip() is None
            assert archive.namelist() == [r['path'] for r in records]
            for r in records:
                assert archive.getinfo(r['path']).file_size == r['bytes']
                with archive.open(r['path']) as stream:
                    assert hashlib.file_digest(stream, 'sha256').hexdigest() == r['sha256']
        temporary.replace(destination)
        part_data = [r for r in existing if r['dp_id'] in chosen]
        archived_data.extend(r['relative_path'] for r in part_data)
        archived_receipts.extend(chosen)
        part = dict(filename=filename, local_path=str(destination), bytes=destination.stat().st_size,
                    sha256=sha(destination), files=len(records), selected_exposures=len(chosen),
                    fits_files=len(part_data), admitted_files=sum(r in admitted for r in part_data),
                    header_excluded_existing_files=sum(r in excluded_existing for r in part_data),
                    missing_files=sum(r['dp_id'] in chosen for r in missing), exposure_ids=chosen, members=records)
        parts.append(part)
        (DELIVERY / 'INPUT_CHECKPOINTS_PROGRESS.json').write_text(json.dumps(
            dict(complete=False, selected_packaged=offset + len(chosen), parts=parts), indent=2) + '\n')
        print(json.dumps({k: part[k] for k in ['filename', 'bytes', 'sha256', 'files', 'selected_exposures', 'fits_files']}), flush=True)

    assert len(archived_data) == len(set(archived_data)) == len(existing)
    assert set(archived_data) == on_disk
    assert archived_receipts == ids
    # Recheck the source acquisition records and immutable source bytes after packaging.
    assert sha(manifest_path) == next(r['sha256'] for r in common_records if r['path'] == str(manifest_path.relative_to(BASE)))
    for r in common_records:
        assert sha(BASE / r['path']) == r['sha256'], r['path']
    inventory = dict(complete=True, selected_exposures=len(ids), fits_files=len(existing),
        admitted_files=len(admitted), header_excluded_existing_files=len(excluded_existing),
        missing_files=len(missing), input_fits_bytes=sum(r['bytes'] for r in existing),
        acquisition_manifest_sha256=sha(manifest_path), acquisition_result_sha256=sha(result_path),
        freeze_sha256=sha(EXT / 'FREEZE.json'), packaging_script_sha256=sha(Path(__file__)),
        prospective_commit=json.loads((acquisition / 'PUBLICATION.json').read_text()),
        science_arrays_interpreted_by_packager=False, max_exposures_per_part=PART_EXPOSURES,
        max_part_bytes=MAX_PART_BYTES, archive_timestamp=list(STAMP),
        reproducibility='Fixed ZIP timestamp, permissions, compression level6, source bytes and member order.',
        coverage='All manifest-selected receipts and all existing FITS data archived exactly once; shared frozen code/metadata repeated in each part.',
        verification='Every source file SHA256; all ZIP member SHA256 and sizes plus testzip CRC; complete manifest and on-disk data coverage.',
        parts=parts)
    text = json.dumps(inventory, indent=2) + '\n'
    inventory_path.write_text(text)
    (OUT / 'INPUT_CHECKPOINTS.json').write_text(text)
    print(json.dumps(dict(complete=True, parts=len(parts), fits_files=len(existing),
                         bytes=sum(r['bytes'] for r in parts), inventory=str(inventory_path))), flush=True)


if __name__ == '__main__':
    main()
