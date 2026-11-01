"""Inventory canonical products and excluded transfer remnants without using them.

Unlike historical one-off inventory, counts and retries derive from actual
receipts. A clean restoration may have zero temporary files. No data is deleted.
"""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
BASE = BATCH.parent.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = HERE / 'SUPPLEMENTAL_INVENTORY.json'
    assert not destination.exists(), 'Preserve previous inventory; use a separate restored copy'
    read = lambda path: json.loads(path.read_text())
    manifest_path = BATCH / 'products/MANIFEST.json'
    mapping_path = BATCH / 'NATIVE_MAPPING.json'
    summary_path = HERE / 'SUMMARY.json'
    manifest, mapping, summary = read(manifest_path), read(mapping_path), read(summary_path)
    frozen = read(BATCH / 'FOLLOWUP_FREEZE.json')
    before_summary = sha(summary_path)
    assert summary['status'] == 'PASS'
    assert summary['source_hashes']['products/MANIFEST.json'] == sha(manifest_path)
    assert summary['source_hashes']['NATIVE_MAPPING.json'] == sha(mapping_path)
    products = manifest['products']
    assert len(products) <= 64
    successful_products = [p for p in products if p['status'] == 'DOWNLOADED']
    canonical = []
    product_by_name = {}
    for record in successful_products:
        path = BASE / record['relative_path']
        assert path.parent == BATCH / 'products'
        assert path.name == record['filename'] and not path.name.endswith('.part')
        digest = sha(path)
        assert digest == record['sha256']
        assert path.stat().st_size == record['bytes'] == record['advertised_bytes']
        assert path.name not in product_by_name
        product_by_name[path.name] = record
        canonical.append(dict(relative_path=record['relative_path'], bytes=path.stat().st_size,
                              sha256=digest, matches_manifest=True))
    partials = []
    for path in sorted((BATCH / 'products').glob('*.part')):
        stat = path.stat()
        counterpart = path.with_name(path.name.removesuffix('.part'))
        partial_bytes = path.read_bytes()
        known_counterpart = counterpart.name in product_by_name
        prefix_match = complete_duplicate = None
        if known_counterpart:
            with counterpart.open('rb') as stream:
                prefix_match = partial_bytes == stream.read(len(partial_bytes))
            complete_duplicate = prefix_match and stat.st_size == counterpart.stat().st_size
        partials.append(dict(relative_path=str(path.relative_to(BASE)), bytes=stat.st_size,
            sha256=hashlib.sha256(partial_bytes).hexdigest(), mtime_ns=stat.st_mtime_ns,
            canonical_relative_path=str(counterpart.relative_to(BASE)) if known_counterpart else None,
            canonical_sha256=product_by_name[counterpart.name]['sha256'] if known_counterpart else None,
            exact_canonical_prefix_match=prefix_match, complete_canonical_duplicate=complete_duplicate,
            included_as_manifest_product=False, included_as_extraction_input=False))
    manifest_paths = {record['relative_path'] for record in successful_products}
    assert not manifest_paths.intersection(record['relative_path'] for record in partials)
    completed_spectra = unavailable_spectra = 0
    for spectrum in mapping['spectra']:
        pair = [record for record in successful_products if record['dp_id'] == spectrum['dp_id']]
        if len(pair) != 2 or {r['kind'] for r in pair} != {'RAW', 'ANCILLARY'}:
            assert spectrum['status'] == 'PRODUCT_PAIR_UNAVAILABLE'
            unavailable_spectra += 1
            continue
        for kind, key in [('RAW', 'raw_sha256'), ('ANCILLARY', 'ancillary_sha256')]:
            assert spectrum[key] == next(r for r in pair if r['kind'] == kind)['sha256']
        completed_spectra += 1
    assert completed_spectra + unavailable_spectra == 32
    extractor = BATCH / 'extract_native.py'
    assert sha(extractor) == frozen['source_hashes'][str(extractor.relative_to(BASE))]
    assert all(sha(BASE / relative) == digest for relative, digest in frozen['source_hashes'].items())
    attempts = [dict(filename=r['filename'], attempt_index=i + 1, **attempt)
                for r in products for i, attempt in enumerate(r['attempts'])]
    failed = [a for a in attempts if a['outcome'] != 'SUCCESS']
    succeeded = [a for a in attempts if a['outcome'] == 'SUCCESS']
    assert len(succeeded) == len(successful_products)
    known = sum(a['known_returned_payload_bytes'] for a in attempts)
    charged = sum(a['charged_payload_bytes'] for a in attempts)
    assert known == manifest['known_returned_payload_bytes']
    assert charged == manifest['charged_payload_bytes'] <= manifest['payload_cap_bytes']
    assert charged - known == manifest['unknown_bytes_conservatively_charged']
    assert manifest['reserved_bytes'] == 0
    assert sha(summary_path) == before_summary
    report = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='CANONICAL_INPUTS_VERIFIED_AND_NON_INPUT_FILES_INVENTORIED',
        original_numerical_audit_summary_unchanged=True,
        original_numerical_audit_summary_sha256=before_summary,
        planned_product_receipts=len(products), canonical_product_count=len(canonical),
        failed_product_receipts=len(products)-len(canonical),
        canonical_products_all_match_manifest=True,
        canonical_product_bytes=sum(r['bytes'] for r in canonical),
        completed_exposure_pairs=completed_spectra, unavailable_exposure_pairs=unavailable_spectra,
        residual_partial_file_count=len(partials), residual_partial_file_bytes=sum(r['bytes'] for r in partials),
        all_residual_files_are_exact_canonical_prefixes=all(r['exact_canonical_prefix_match'] is True for r in partials),
        full_duplicate_count=sum(r['complete_canonical_duplicate'] is True for r in partials),
        excluded_from_analysis=True, residual_files_preserved_without_modification=True,
        partial_file_origin='Not inferred. Presence or prefix equality alone does not establish how a file was created or imply additional network bytes.',
        extraction_input_verification='Every completed spectrum records hashes of its canonical RAW and ANCILLARY products; unavailable pairs remain explicit. Frozen extractor reads only canonical manifest relative paths. Independent numerical audit reconstructed saved cutouts from those inputs.',
        acquisition_attempts=dict(total=len(attempts),successful=len(succeeded),failed=len(failed),
            failed_attempts=failed,known_returned_payload_bytes=known,charged_payload_bytes=charged,
            unknown_bytes_conservatively_charged=manifest['unknown_bytes_conservatively_charged'],reserved_bytes=0),
        source_hashes={'products/MANIFEST.json':sha(manifest_path),'NATIVE_MAPPING.json':sha(mapping_path),
                       'extract_native.py':sha(extractor),'FOLLOWUP_FREEZE.json':sha(BATCH/'FOLLOWUP_FREEZE.json')},
        script_sha256=sha(Path(__file__)), canonical_products=canonical, residual_partial_files=partials)
    destination.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['canonical_products','residual_partial_files','source_hashes','acquisition_attempts']},indent=2))


if __name__ == '__main__':
    main()
