"""Supplemental read-only inventory of residual temporary transfer files.

Never treats .part files as data inputs, deletes them, or changes the original
numerical audit. Only hashes/compares bytes and records filesystem evidence.
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
    if destination.exists():
        raise RuntimeError('Preserve the prior inventory; use a separate restored copy for reproduction')
    manifest_path = BATCH / 'products/MANIFEST.json'
    mapping_path = BATCH / 'NATIVE_MAPPING.json'
    summary_path = HERE / 'SUMMARY.json'
    manifest = json.loads(manifest_path.read_text())
    mapping = json.loads(mapping_path.read_text())
    summary = json.loads(summary_path.read_text())
    frozen = json.loads((BATCH / 'FOLLOWUP_FREEZE.json').read_text())
    before_summary = sha(summary_path)
    assert summary['status'] == 'PASS'
    assert summary['source_hashes']['products/MANIFEST.json'] == sha(manifest_path)
    assert summary['source_hashes']['NATIVE_MAPPING.json'] == sha(mapping_path)
    products = manifest['products']
    assert len(products) == 32
    canonical = []
    product_by_name = {}
    for record in products:
        assert record['status'] == 'DOWNLOADED'
        path = BASE / record['relative_path']
        assert path.parent == BATCH / 'products'
        assert path.name == record['filename'] and not path.name.endswith('.part')
        digest = sha(path)
        assert digest == record['sha256']
        assert path.stat().st_size == record['bytes'] == record['advertised_bytes']
        assert path.name not in product_by_name
        product_by_name[path.name] = record
        canonical.append(dict(relative_path=record['relative_path'], bytes=path.stat().st_size, sha256=digest, expected_sha256=record['sha256'], matches_manifest=True))
    partials = []
    for path in sorted((BATCH / 'products').glob('*.part')):
        stat = path.stat()
        counterpart = path.with_name(path.name.removesuffix('.part'))
        assert counterpart.name in product_by_name
        partial_bytes = path.read_bytes()
        with counterpart.open('rb') as stream:
            canonical_prefix = stream.read(len(partial_bytes))
        partials.append(dict(relative_path=str(path.relative_to(BASE)), bytes=stat.st_size, sha256=hashlib.sha256(partial_bytes).hexdigest(), mtime_ns=stat.st_mtime_ns, ctime_ns=stat.st_ctime_ns, inode=stat.st_ino, canonical_relative_path=str(counterpart.relative_to(BASE)), canonical_bytes=counterpart.stat().st_size, canonical_sha256=product_by_name[counterpart.name]['sha256'], canonical_prefix_sha256=hashlib.sha256(canonical_prefix).hexdigest(), exact_canonical_prefix_match=partial_bytes == canonical_prefix, complete_canonical_duplicate=partial_bytes == canonical_prefix and stat.st_size == counterpart.stat().st_size, included_as_manifest_product=False, included_as_extraction_input=False))
    assert len(partials) == 5
    assert all(record['exact_canonical_prefix_match'] for record in partials)
    manifest_paths = {record['relative_path'] for record in products}
    assert not manifest_paths.intersection(record['relative_path'] for record in partials)
    for spectrum in mapping['spectra']:
        pair = [record for record in products if record['dp_id'] == spectrum['dp_id']]
        assert len(pair) == 2
        for kind, key in [('RAW', 'raw_sha256'), ('ANCILLARY', 'ancillary_sha256')]:
            record = next(record for record in pair if record['kind'] == kind)
            assert spectrum[key] == record['sha256']
    extractor = BATCH / 'extract_native.py'
    assert sha(extractor) == frozen['source_hashes'][str(extractor.relative_to(BASE))]
    assert all(sha(BASE / relative) == digest for relative, digest in frozen['source_hashes'].items())
    attempts = [dict(filename=record['filename'], attempt_index=i + 1, **attempt) for record in products for i, attempt in enumerate(record['attempts'])]
    failed = [attempt for attempt in attempts if attempt['outcome'] != 'SUCCESS']
    successful = [attempt for attempt in attempts if attempt['outcome'] == 'SUCCESS']
    assert len(attempts) == 33 and len(successful) == 32 and len(failed) == 1
    assert failed[0]['known_returned_payload_bytes'] == failed[0]['charged_payload_bytes'] == 0
    known = sum(attempt['known_returned_payload_bytes'] for attempt in attempts)
    charged = sum(attempt['charged_payload_bytes'] for attempt in attempts)
    assert known == manifest['known_returned_payload_bytes']
    assert charged == manifest['charged_payload_bytes'] == 423684432
    assert sum(record['bytes'] for record in products) == charged
    assert sha(summary_path) == before_summary
    report = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='CANONICAL_INPUTS_VERIFIED_TEMPORARY_FILE_ANOMALY_DOCUMENTED', original_numerical_audit_summary_unchanged=True, original_numerical_audit_summary_sha256=before_summary, canonical_product_count=32, canonical_products_all_match_manifest=True, canonical_product_bytes=sum(record['bytes'] for record in products), residual_partial_file_count=len(partials), residual_partial_file_bytes=sum(record['bytes'] for record in partials), all_residual_files_are_exact_canonical_prefixes=True, full_duplicate_count=sum(record['complete_canonical_duplicate'] for record in partials), excluded_from_analysis=True, residual_files_preserved_without_modification=True, partial_file_origin='Undetermined. Files remain despite the documented rename/cleanup path. Prefix equality does not establish how these files were created or imply additional network bytes. No unsupported transport explanation is inferred.', extraction_input_verification='All32 extraction receipt hashes match canonical manifest products; every spectrum records the correct RAW and ANCILLARY hashes. Frozen extractor reads only those manifest relative_path values. The earlier independent audit reconstructed every saved cutout from canonical paths, not .part paths.', acquisition_attempts=dict(total=33,successful=32,failed=1,failed_attempts=failed,known_returned_payload_bytes=known,charged_payload_bytes=charged,unknown_bytes_conservatively_charged=manifest['unknown_bytes_conservatively_charged'],reserved_bytes=manifest['reserved_bytes'],correction='Acquisition succeeded for all32 products with one HTTP503 failure before any response-body bytes, followed by a successful retry. Describing this acquisition as having no retries was incorrect.'), source_hashes={'products/MANIFEST.json':sha(manifest_path),'NATIVE_MAPPING.json':sha(mapping_path),'extract_native.py':sha(extractor),'FOLLOWUP_FREEZE.json':sha(BATCH/'FOLLOWUP_FREEZE.json')}, script_sha256=sha(Path(__file__)), canonical_products=canonical, residual_partial_files=partials)
    destination.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({key:value for key,value in report.items() if key not in ['canonical_products','residual_partial_files','source_hashes','acquisition_attempts']},indent=2))


if __name__ == '__main__':
    main()
