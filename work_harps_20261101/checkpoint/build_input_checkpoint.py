#!/usr/bin/env python3
"""Build and verify a deterministic byte-only HARPS input checkpoint."""
import hashlib
import json
import pathlib
import shutil
import zipfile

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE.parents[1] / 'harps_checkpoint_delivery'
OUT.mkdir(parents=True, exist_ok=True)
ARCHIVE = OUT / 'SETI_HARPS_INPUT_CHECKPOINT_2026-11-01.zip'
FIXED_TIME = (2026, 11, 1, 0, 0, 0)
CHUNK = 1024 * 1024

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()

selected = []
counts = {}
for role in ('main', 'development', 'validation'):
    files = sorted((BASE / 'data' / role).glob('*.fits*'))
    counts[role] = len(files)
    selected.extend(files)
assert counts == {'main': 100, 'development': 2, 'validation': 3}, counts
probes = sorted((BASE / 'access_probe').glob('DEV_HD203608*.fits*'))
assert len(probes) == 2
selected.extend(probes)
data_files = set(selected)
selected.extend(sorted((BASE / 'acquisition' / 'receipts').glob('*.json')))
assert len(list((BASE / 'acquisition' / 'receipts').glob('*.json'))) == 105
for rel in (
    'acquisition/DOWNLOAD_MANIFEST.json',
    'acquisition/DOWNLOAD_MANIFEST.csv',
    'acquisition/ACQUISITION_SCOPE.json',
    'acquisition/ACQUISITION_RESULT.json',
    'selection/MAIN100.csv',
    'selection/DEVELOPMENT_AND_VALIDATION.csv',
    'selection/SELECTION.json',
    'access_probe/development_download_receipt.json',
    'access_probe/development_raw_download_receipt.json',
    'access_probe/harps_post2019_metadata.csv',
    'access_probe/harps_post2019_metadata_receipt.json',
    'literature/upstream_referenced_exposure_ids.json',
    'literature/UPSTREAM_REFERENCED_IDS.json',
    'literature/upstream_sources.json',
    'literature/UPSTREAM_REVIEW.json',
    'literature/UPSTREAM_REVIEW.md',
):
    selected.append(BASE / rel)
selected = sorted(set(selected), key=lambda p: p.relative_to(BASE).as_posix())
assert all(p.is_file() and not p.is_symlink() for p in selected)
assert not any('/upstream/' in str(p) or p.suffix == '.py' for p in selected)
records = [
    {'path': p.relative_to(BASE).as_posix(), 'bytes': p.stat().st_size,
     'sha256': sha256(p)}
    for p in selected
]
by_path = {r['path']: r for r in records}
acquisition = json.loads((BASE / 'acquisition/DOWNLOAD_MANIFEST.json').read_text())
assert len(acquisition) == 105
expected = []
for receipt in acquisition:
    relative = pathlib.Path(receipt['path']).relative_to(BASE).as_posix()
    expected.append(relative)
    assert by_path[relative]['sha256'] == receipt['sha256'], relative
    assert by_path[relative]['bytes'] == receipt['bytes'], relative
for rel in ('access_probe/development_download_receipt.json',
            'access_probe/development_raw_download_receipt.json'):
    receipt = json.loads((BASE / rel).read_text())
    relative = pathlib.Path(receipt['path']).relative_to(BASE).as_posix()
    expected.append(relative)
    assert by_path[relative]['sha256'] == receipt['sha256'], relative
    assert by_path[relative]['bytes'] == receipt['bytes'], relative
assert set(expected) == {p.relative_to(BASE).as_posix() for p in data_files}

readme = '''# HARPS optical SETI input checkpoint — 1 November 2026

This archive preserves the exact public input bytes used for the project's
initial HARPS week: 100 main sample spectra (20 selected target groups × 5
epochs), two HD100508 development spectra, three reserved validation background
spectra, and the HD203608 development spectrum plus its compressed raw control.
There are 107 FITS/FITS.Z files in total. These roles describe input selection,
not completion or scientific validation of a technosignature search.

The inputs were obtained from the ESO Science Archive Facility:
https://archive.eso.org/ . They are HARPS observations from the ESO 3.6-m
telescope at La Silla. Individual public source URLs, product IDs, raw progenitor
IDs, download timestamps and SHA-256 values are retained in the acquisition
manifest and receipts. Original programme attribution and reduction provenance
remain in the unmodified FITS headers. When using these observations, retain
the ESO archive and original observing-programme acknowledgements.

Selection CSVs and the bounded 5,000-row catalogue metadata snapshot are included
to preserve the actual selection inputs. Literature ID inventories, source
metadata and the upstream review are factual provenance, not upstream software.
No third-party source code, result arrays, candidate tables, or production
analysis outputs are included. Absence from a referenced-ID inventory is not
proof that an observation has never previously been searched.

All archive member paths are relative to work_harps_20261101. Historical absolute
paths inside original JSON receipts identify the original workspace only; use
the archive-relative paths when restoring. The raw .fits.Z control stays in its
original compression. No FITS array was decoded or interpreted while packaging.

Restore by extracting the ZIP into an empty work_harps_20261101 directory. Check
the archive's external SHA-256 first, then run `sha256sum -c SHA256SUMS` from the
extracted directory. INPUTS_MANIFEST.json supplies exact sizes and SHA-256 values
for every original payload file. The manifest and this README are also covered
by SHA256SUMS; SHA256SUMS intentionally does not hash itself.

Packaging is deterministic for a fixed Python/zlib implementation: sorted
relative paths, ZIP DEFLATED level 1, timestamp 2026-11-01 00:00:00, Unix mode
0644, UTF-8 generated metadata with LF line endings. The build verifies original
download receipt hashes for all 107 binary inputs, validates all ZIP CRCs, and
recomputes each member SHA-256 from the archived bytes. The ZIP and delivery
receipt are stored outside the Git repository.
'''
manifest = {
    'schema_version': 1,
    'checkpoint_date': '2026-11-01',
    'purpose': 'Exact byte-level input checkpoint; not a scientific result',
    'binary_counts': {**counts, 'HD203608_access_probe': 2, 'total': len(data_files)},
    'binary_bytes': sum(p.stat().st_size for p in data_files),
    'packaging_reads_fits_arrays': False,
    'original_download_hashes_checked': len(expected),
    'source_archive': 'https://archive.eso.org/',
    'upstream_source_code_included': False,
    'payload_files': records,
}
generated = {
    'README.md': readme.encode(),
    'INPUTS_MANIFEST.json': (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode(),
}
hashes = {r['path']: r['sha256'] for r in records}
hashes.update({name: hashlib.sha256(data).hexdigest() for name, data in generated.items()})
generated['SHA256SUMS'] = ''.join(f'{hashes[name]}  {name}\n' for name in sorted(hashes)).encode()

def info(name):
    item = zipfile.ZipInfo(name, FIXED_TIME)
    item.create_system = 3
    item.external_attr = 0o100644 << 16
    item.compress_type = zipfile.ZIP_DEFLATED
    item._compresslevel = 1
    return item

with zipfile.ZipFile(ARCHIVE, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1,
                     allowZip64=True) as archive:
    for name in sorted([p.relative_to(BASE).as_posix() for p in selected] + list(generated)):
        if name in generated:
            archive.writestr(info(name), generated[name])
        else:
            with (BASE / name).open('rb') as source, archive.open(info(name), 'w', force_zip64=True) as target:
                shutil.copyfileobj(source, target, CHUNK)

with zipfile.ZipFile(ARCHIVE) as archive:
    assert archive.testzip() is None, 'ZIP CRC failure'
    assert len(archive.namelist()) == len(records) + len(generated)
    for name, expected_sha in hashes.items():
        h = hashlib.sha256()
        with archive.open(name) as source:
            for block in iter(lambda: source.read(CHUNK), b''):
                h.update(block)
        assert h.hexdigest() == expected_sha, name

report = {
    'archive_path': str(ARCHIVE),
    'archive_bytes': ARCHIVE.stat().st_size,
    'archive_sha256': sha256(ARCHIVE),
    'archive_members': len(records) + len(generated),
    'binary_counts': manifest['binary_counts'],
    'binary_bytes': manifest['binary_bytes'],
    'payload_files': len(records),
    'payload_bytes': sum(r['bytes'] for r in records),
    'original_download_receipt_hashes_verified': len(expected),
    'zip_crc_verified': True,
    'member_sha256_verified': len(hashes),
    'packaging_fits_arrays_opened': False,
    'upstream_source_code_included': False,
}
(OUT / (ARCHIVE.name + '.sha256')).write_text(f"{report['archive_sha256']}  {ARCHIVE.name}\n")
(BASE / 'checkpoint/README.md').write_text(readme)
(BASE / 'checkpoint/INPUT_CHECKPOINT.json').write_text(json.dumps(report, indent=2) + '\n')
(OUT / 'INPUT_CHECKPOINT.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
