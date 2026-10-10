"""Serialize and package completed saved results; no telescope reads or scoring."""
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/radio_stationary_family_20261010'
ARCHIVE = ROOT.parent / 'SETI_STATIONARY_FAMILY_2026-10-10.zip'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def main():
    started = time.monotonic()
    public = OUT / 'public'
    public.mkdir(exist_ok=False)
    replacements = []
    for p in sorted((OUT / 'measurement').glob('*')):
        if p.is_file() and p.suffix in ('.json', '.csv') and p.stat().st_size > 100000:
            raw = p.read_bytes()
            compressed = gzip.compress(raw, compresslevel=1, mtime=0)
            target = public / (p.name + '.gz')
            target.write_bytes(compressed)
            assert gzip.decompress(compressed) == raw
            replacements.append({'original': str(p.relative_to(ROOT)),
                'public': str(target.relative_to(ROOT)), 'original_sha256': sha(raw),
                'public_sha256': sha(compressed), 'original_bytes': len(raw),
                'public_bytes': len(compressed), 'decompression_byte_exact': True})
    save(OUT / 'PUBLICATION_LAYOUT.json', {
        'large_metadata_lossless_gzip_replacements': replacements,
        'full_NPZ_in_saved_archive': 'SETI_STATIONARY_FAMILY_2026-10-10.zip',
        'full_NPZ_original_relative_path': 'results/radio_stationary_family_20261010/measurement/ALL_120_FIXED_STATIONARY_PATCHES.npz',
        'three_display_copies_are_existing_plot_layout_repairs': True,
        'original_scientific_plots_preserved': True})
    inputs = [ROOT / 'RADIO_STATIONARY_FAMILY_REPORT_2026-10-10.md']
    inputs += sorted((ROOT / 'tools/radio_stationary_family_20261010').glob('*'))
    inputs += [ROOT / p for p in (
        'tools/radio_fresh_band_20261009/source_manifest.json',
        'tools/radio_fresh_band_20261009/analysis_scope.json',
        'tools/radio_fresh_band_20261009/fresh_search.py',
        'results/radio_fresh_band_20261009/arrays/ACQUISITION_RESULT.json',
        'results/radio_fresh_band_20261009/stationary/STATIONARY_TOP20.json',
        'results/radio_fresh_band_20261009/stationary/NORMALIZATION.json',
        'results/radio_fresh_band_20261009/profiles/FIXED_TOP3_PROFILES.json')]
    inputs += sorted(OUT.rglob('*'))
    inputs = [p for p in inputs if p.is_file() and p.name not in ('ARCHIVE_RECEIPT.json', 'BUNDLE_MANIFEST.json')]
    assert len(inputs) == len(set(inputs))
    manifest = {'schema': 'SETI_STATIONARY_SELECTED_FAMILY_ARCHIVE_V1',
        'pre_execution_freeze_commit': '03de4adda318905f3c0685af827e62a8d1af72a3',
        'source_compacts_available_in_prior_saved_raw_archive': 'SETI_FRESH_BAND151_RAW_2026-10-09.zip',
        'nine_original_reused_patch_files_available_in_prior_saved_result_archive': 'SETI_FRESH_BAND151_RESULTS_2026-10-09.zip',
        'all_selected_patch_raw_values_and_derived_arrays_included': True,
        'no_new_source_data_or_scientific_measurements_during_packaging': True,
        'files': [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size,
                   'sha256': sha(p.read_bytes())} for p in inputs]}
    save(OUT / 'BUNDLE_MANIFEST.json', manifest)
    with zipfile.ZipFile(ARCHIVE, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for p in inputs:
            z.write(p, str(p.relative_to(ROOT)))
        z.write(OUT / 'BUNDLE_MANIFEST.json', str((OUT / 'BUNDLE_MANIFEST.json').relative_to(ROOT)))
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        for entry in manifest['files']:
            data = z.read(entry['path'])
            assert len(data) == entry['bytes'] and sha(data) == entry['sha256']
    receipt = {'path': str(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
        'sha256': sha(ARCHIVE.read_bytes()), 'file_count': len(inputs)+1,
        'all_manifest_member_hashes_and_sizes_verified': True,
        'ZIP_CRC_verified': True, 'process_CPU_s': time.process_time(),
        'wall_s': time.monotonic()-started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'receipt_outside_archive_to_avoid_self_reference': True}
    save(OUT / 'ARCHIVE_RECEIPT.json', receipt)
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
