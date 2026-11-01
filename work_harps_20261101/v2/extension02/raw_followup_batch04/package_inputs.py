"""Checkpoint verified canonical raw batch04 product pairs; never read noncanonical payloads.

Run only after root confirms acquisition completion. Missing/incomplete pairs are
listed without replacement. All archive paths remain relative to science BASE.
"""
from pathlib import Path, PurePosixPath
import argparse
import csv
import datetime
import hashlib
import json
import zipfile

from common import verify_freeze

OUT = Path(__file__).resolve().parent
BASE = OUT.parent.parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def canonical_path(record):
    relative = PurePosixPath(record['relative_path'])
    require(not relative.is_absolute() and '..' not in relative.parts,
            'Unsafe manifest path')
    path = BASE.joinpath(*relative.parts)
    expected_suffix = '.fits.Z' if record['kind'] == 'RAW' else '.tar'
    require(record['kind'] in ('RAW', 'ANCILLARY') and path.name.endswith(expected_suffix),
            'Unexpected canonical product suffix')
    require(path.name == record['filename'] == record['archive_id'].replace(':', '_') + expected_suffix
            and not path.name.startswith('.'), 'Unexpected canonical filename')
    require(path.parent == OUT / 'products' and not path.is_symlink(),
            'Product not in this batch canonical directory')
    return path


def add_bytes(archive, name, data):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    verify_freeze()
    manifest = read(OUT / 'products/MANIFEST.json')
    products = manifest['products']
    jobs = read(OUT / 'JOBS.json')
    selection_record = read(OUT / 'SELECTION.json')
    metadata_omissions = {r['dp_id']: r for r in selection_record['omitted_pairs']}
    with (OUT / 'SELECTED_EXPOSURES.csv').open(newline='') as handle:
        selected = list(csv.DictReader(handle))
    require(len(selected) == len({r['dp_id'] for r in selected}) == 37,
            'Selected batch04 scope changed')
    require(len(products) == len(jobs) <= 74, 'Acquisition/job accounting differs')
    require({(r['dp_id'], r['kind'], r['filename']) for r in products} ==
            {(r['dp_id'], r['kind'], r['filename']) for r in jobs},
            'Manifest product identities differ from fixed jobs')
    require(all(r['dp_id'] in {s['dp_id'] for s in selected} for r in products),
            'Unselected product present')
    complete_pairs = []
    excluded_pairs = []
    for selection in selected:
        pair = [r for r in products if r['dp_id'] == selection['dp_id']]
        successful = [r for r in pair if r['status'] == 'DOWNLOADED']
        if len(successful) != 2 or {r['kind'] for r in successful} != {'RAW', 'ANCILLARY'}:
            excluded_pairs.append(dict(dp_id=selection['dp_id'],
                reason='NO_COMPLETE_VERIFIED_CANONICAL_PAIR',
                selection_index=int(selection['selection_index']), target=selection['canonical_target'],
                raw_progenitor_id=selection['raw_progenitor_id'],
                ancillary_archive_id=selection['ancillary_archive_id'],
                metadata_omission=metadata_omissions.get(selection['dp_id']),
                statuses=[dict(kind=r['kind'], archive_id=r['archive_id'], status=r['status']) for r in pair],
                successful_but_unpaired=[dict(kind=r['kind'], archive_id=r['archive_id'],
                    relative_path=r['relative_path'], sha256=r['sha256'], bytes=r['bytes']) for r in successful],
                replaced=False))
            continue
        pair = sorted(successful, key=lambda r: r['kind'] != 'RAW')
        for record in pair:
            path = canonical_path(record)
            require(path.is_file() and path.stat().st_size == record['bytes'] and sha(path) == record['sha256'],
                    'Canonical product hash/length mismatch: ' + str(path))
            receipt_path = path.with_name(path.name + '.json')
            require(receipt_path.is_file() and not receipt_path.is_symlink(),
                    'Canonical receipt must be a regular file')
            receipt = read(receipt_path)
            for key in ['archive_id', 'dp_id', 'kind', 'status', 'bytes', 'sha256', 'relative_path']:
                require(receipt[key] == record[key], 'Receipt/manifest mismatch: ' + key)
        complete_pairs.append(pair)
    require(bool(complete_pairs), 'No complete pairs available for checkpoint')
    groups = [complete_pairs[i:i + 4] for i in range(0, len(complete_pairs), 4)]
    paths = [destination / f'SETI_HARPS_RAW_BATCH04_INPUTS_PART{i}_2026-11-02.zip'
             for i in range(1, len(groups) + 1)]
    require(all(not path.exists() and not path.is_symlink() for path in paths),
            'Existing checkpoint archive cannot be replaced')
    require(not (OUT / 'checkpoints/INPUT_ARCHIVES.json').exists(),
            'Existing checkpoint manifest cannot be replaced')
    archives = []
    metadata_names = ['products/MANIFEST.json', 'JOBS.json', 'FOLLOWUP_FREEZE.json',
                      'SELECTED_EXPOSURES.csv', 'SELECTED_EVENTS.csv', 'PREREGISTRATION_RECEIPT.json',
                      'SELECTION.json', 'REMOTE_PRODUCT_METADATA.json', 'PLAN.json']
    metadata = [(str((OUT / name).relative_to(BASE)), (OUT / name).read_bytes()) for name in metadata_names]
    instructions = (
        'Members are relative to work_harps_20261101. Extract into a separate staging directory. '
        'Verify archive and product SHA-256 values against checkpoint manifests, then copy only '
        'verified canonical payloads/receipts into the current worktree. Do not overwrite current '
        'status, plans or newer evidence with historical metadata copies. '
        f'This checkpoint contains {len(complete_pairs) * 2} original ESO products in '
        f'{len(complete_pairs)} complete exposure pairs, distributed over {len(groups)} ZIP files. '
        f'{len(excluded_pairs)} selected exposure pairs are not included; consult INPUT_ARCHIVES.json. '
        'All noncanonical payload files, including hidden transient copies and .part files, are excluded from checkpoint members and analysis inputs. No observing time was added.\n'
    )
    for path, group in zip(paths, groups):
        members = []
        with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for pair in group:
                for record in pair:
                    source = canonical_path(record)
                    data = source.read_bytes()
                    require(len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256'],
                            'Canonical product changed during checkpoint')
                    add_bytes(archive, record['relative_path'], data)
                    members.append({key: record[key] for key in
                                    ['relative_path', 'sha256', 'bytes', 'dp_id', 'archive_id', 'kind']})
                    receipt = source.with_name(source.name + '.json')
                    add_bytes(archive, str(receipt.relative_to(BASE)), receipt.read_bytes())
            for name, data in metadata:
                add_bytes(archive, name, data)
            add_bytes(archive, 'RESTORE_BATCH04_INPUTS.txt', instructions.encode())
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, 'Checkpoint CRC failure')
            for member in members:
                data = archive.read(member['relative_path'])
                require(len(data) == member['bytes'] and hashlib.sha256(data).hexdigest() == member['sha256'],
                        'Checkpoint member hash mismatch')
        archives.append(dict(filename=path.name, local_path=str(path), bytes=path.stat().st_size,
                             sha256=sha(path), complete_exposures=len(group), products=members))
        print(path.name, path.stat().st_size, flush=True)
    checkpoint = OUT / 'checkpoints'
    checkpoint.mkdir(exist_ok=True)
    (checkpoint / 'INPUT_ARCHIVES.json').write_text(json.dumps(dict(
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        selected_exposures=37, accepted_jobs=len(jobs), complete_exposures=len(complete_pairs),
        raw_products=len(complete_pairs), ancillary_products=len(complete_pairs),
        excluded_pairs=excluded_pairs, replacements=0, residual_part_files_included=0,
        noncanonical_payload_files_included=0,
        source_manifest_sha256=sha(OUT / 'products/MANIFEST.json'), archives=archives), indent=2) + '\n')
    (destination / 'upload_request.json').write_text(json.dumps({'uploads': [dict(
        local_path=r['local_path'], purpose='create_library_file', library_artifact_type='other')
        for r in archives]}, indent=2) + '\n')


if __name__ == '__main__':
    main()
