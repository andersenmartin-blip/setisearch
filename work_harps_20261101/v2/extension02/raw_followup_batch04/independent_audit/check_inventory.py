"""Inventory canonical products and excluded transfer remnants without using them.

Unlike historical one-off inventory, counts and retries derive from actual
receipts. A clean restoration may have zero temporary files. No data is deleted.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
BASE = BATCH.parent.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='SUPPLEMENTAL_INVENTORY.json')
    parser.add_argument('--check-packages', action='store_true')
    args = parser.parse_args()
    assert Path(args.output).name == args.output, 'Output must be a filename in the audit directory'
    destination = HERE / args.output
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
    assert len(products) <= 74
    successful_products = [p for p in products if p['status'] == 'DOWNLOADED']
    canonical = []
    product_by_name = {}
    for record in successful_products:
        path = BASE / record['relative_path']
        assert path.parent == BATCH / 'products'
        assert path.name == record['filename'] and not path.name.endswith('.part') and not path.is_symlink()
        digest = sha(path)
        assert digest == record['sha256']
        assert path.stat().st_size == record['bytes'] == record['advertised_bytes']
        assert path.name not in product_by_name
        product_by_name[path.name] = record
        canonical.append(dict(relative_path=record['relative_path'], bytes=path.stat().st_size,
                              sha256=digest, matches_manifest=True))
    # Exact metadata whitelist: do not hide unknown JSON files or dot-prefixed
    # transient copies behind a broad suffix exclusion.
    metadata_names = {'MANIFEST.json'} | {record['filename'] + '.json' for record in products}
    for record in products:
        assert read(BATCH / 'products' / (record['filename'] + '.json')) == record
    partials = []
    for path in sorted((BATCH / 'products').iterdir()):
        if path.name in product_by_name or path.name in metadata_names:
            continue
        stat = path.lstat()
        assert path.is_file() and not path.is_symlink(), 'Unexpected nonregular noncanonical path: ' + str(path)
        payload = path.read_bytes()
        counterparts = [name for name in product_by_name
                        if path.name == name + '.part' or path.name.startswith('.' + name + '.')
                        or path.name.startswith(name + '.')]
        assert len(counterparts) <= 1, 'Ambiguous transient counterpart'
        name = counterparts[0] if counterparts else None
        counterpart = BATCH / 'products' / name if name else None
        prefix_match = complete_duplicate = None
        if counterpart:
            with counterpart.open('rb') as stream:
                prefix_match = payload == stream.read(len(payload))
            complete_duplicate = prefix_match and stat.st_size == counterpart.stat().st_size
        partials.append(dict(relative_path=str(path.relative_to(BASE)), filename=path.name,
            file_kind='PART_SUFFIX' if path.name.endswith('.part') else 'OTHER_NONCANONICAL_PAYLOAD',
            bytes=stat.st_size, sha256=hashlib.sha256(payload).hexdigest(), mtime_ns=stat.st_mtime_ns,
            canonical_relative_path=str(counterpart.relative_to(BASE)) if counterpart else None,
            canonical_sha256=product_by_name[name]['sha256'] if counterpart else None,
            exact_canonical_prefix_match=prefix_match, complete_canonical_duplicate=complete_duplicate,
            included_as_manifest_product=False, included_as_extraction_input=False,
            origin='UNKNOWN', additional_network_byte_attribution='UNKNOWN'))
    payload_like = [p for p in BATCH.rglob('*') if p.is_file() and
                    (p.name.endswith(('.fits.Z', '.fits', '.tar', '.part')) or '.fits.Z.' in p.name)]
    assert all(p.parent == BATCH / 'products' for p in payload_like), 'Product-like file outside canonical products directory'
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
    assert completed_spectra + unavailable_spectra == 37
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
    log = BATCH / 'acquisition.log'
    log_coverage = dict(status='LOG_NOT_PRESENT', cause='No cause inferred.')
    if log.exists():
        lines = log.read_text().splitlines()
        status_lines = [line for line in lines if line.endswith((' DOWNLOADED', ' FAILED'))]
        logged = []
        for line in status_lines:
            dp, kind, status = line.split()
            assert any(r['dp_id'] == dp and r['kind'] == kind and r['status'] == status for r in products)
            logged.append((dp, kind))
        assert len(logged) == len(set(logged))
        missing = [dict(dp_id=r['dp_id'], kind=r['kind']) for r in products
                   if (r['dp_id'], r['kind']) not in set(logged)]
        log_coverage = dict(path='acquisition.log', sha256=sha(log), physical_lines=len(lines),
                            status_lines=len(status_lines), manifest_receipts=len(products),
                            receipt_identities_absent_from_log=missing,
                            complete_summary_line_present=any(line.startswith('COMPLETE ') for line in lines),
                            cause='UNKNOWN; log is preserved, never reconstructed. Per-product receipts and canonical manifest are authoritative for acquisition accounting.')
    package_checks = dict(requested=args.check_packages, status='NOT_REQUESTED',
                          limits='Exclusion from packaged artifacts is not claimed by this inventory unless --check-packages is used.')
    if args.check_packages:
        input_index_path = BATCH / 'checkpoints/INPUT_ARCHIVES.json'
        evidence_index_path = BATCH / 'EVIDENCE_ARCHIVE.json'
        input_index, evidence_index = read(input_index_path), read(evidence_index_path)
        assert input_index['source_manifest_sha256'] == sha(manifest_path)
        expected_packaged = {p['relative_path']:p for p in successful_products
                            if sum(q['dp_id'] == p['dp_id'] for q in successful_products) == 2}
        packaged_paths = []
        archive_checks = []
        metadata_relatives = ['products/MANIFEST.json', 'JOBS.json', 'FOLLOWUP_FREEZE.json',
                              'SELECTED_EXPOSURES.csv', 'SELECTED_EVENTS.csv', 'PREREGISTRATION_RECEIPT.json',
                              'SELECTION.json', 'REMOTE_PRODUCT_METADATA.json', 'PLAN.json']
        shared_metadata = {str((BATCH / name).relative_to(BASE)): (BATCH / name).read_bytes()
                           for name in metadata_relatives}
        for archive in input_index['archives']:
            path = Path(archive['local_path'])
            assert path.stat().st_size == archive['bytes'] and sha(path) == archive['sha256']
            declared = {p['relative_path']:p for p in archive['products']}
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                assert len(names) == len(set(names))
                receipts = {name + '.json' for name in declared}
                assert set(names) == set(declared) | receipts | set(shared_metadata) | {'RESTORE_BATCH04_INPUTS.txt'}
                for name in declared:
                    assert name in expected_packaged and name not in {p['relative_path'] for p in partials}
                    assert z.getinfo(name).file_size == declared[name]['bytes'] == expected_packaged[name]['bytes']
                    assert declared[name]['sha256'] == expected_packaged[name]['sha256']
                for name in receipts:
                    assert z.read(name) == (BASE / name).read_bytes()
                for name, data in shared_metadata.items():
                    assert z.read(name) == data
                instructions = z.read('RESTORE_BATCH04_INPUTS.txt').decode('utf8')
                assert instructions.startswith('Members are relative to work_harps_20261101.')
                assert 'All noncanonical payload files' in instructions
                assert not {p['relative_path'] for p in partials}.intersection(names)
            packaged_paths.extend(declared)
            archive_checks.append(dict(filename=path.name, bytes=path.stat().st_size,
                                       sha256=archive['sha256'], members=len(names), canonical_payload_members=len(declared),
                                       only_canonical_payloads_and_verified_restoration_metadata=True))
        assert len(packaged_paths) == len(set(packaged_paths)) and set(packaged_paths) == set(expected_packaged)
        evidence_zip = BATCH / evidence_index['archive_filename']
        assert evidence_zip.stat().st_size == evidence_index['bytes'] and sha(evidence_zip) == evidence_index['sha256']
        with zipfile.ZipFile(evidence_zip) as z:
            names = z.namelist()
            assert len(names) == len(set(names)) == evidence_index['member_count']
            assert set(names) == {r['path'] for r in evidence_index['members']}
            assert all(name.startswith(('native/','reference/')) for name in names)
            assert not {Path(r['relative_path']).name for r in partials}.intersection(Path(name).name for name in names)
        package_checks = dict(requested=True, status='PASS', input_archives=archive_checks,
                              packaged_canonical_products=len(packaged_paths), evidence_members=len(names),
                              evidence_sha256=evidence_index['sha256'], all_noncanonical_paths_excluded=True,
                              method='Direct ZIP-member enumeration, whole archive SHA256/length and canonical member identities/declared hashes. Package CRC and full member hash checks are preserved separately by the packager.',
                              source_hashes={'checkpoints/INPUT_ARCHIVES.json':sha(input_index_path),
                                             'EVIDENCE_ARCHIVE.json':sha(evidence_index_path)})
    report = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='CANONICAL_INPUTS_VERIFIED_AND_NON_INPUT_FILES_INVENTORIED',
        original_numerical_audit_summary_unchanged=True,
        original_numerical_audit_summary_sha256=before_summary,
        planned_product_receipts=len(products), canonical_product_count=len(canonical),
        failed_product_receipts=len(products)-len(canonical),
        canonical_products_all_match_manifest=True,
        canonical_product_bytes=sum(r['bytes'] for r in canonical),
        completed_exposure_pairs=completed_spectra, unavailable_exposure_pairs=unavailable_spectra,
        noncanonical_payload_file_count=len(partials), noncanonical_payload_file_bytes=sum(r['bytes'] for r in partials),
        residual_partial_file_count=sum(r['file_kind'] == 'PART_SUFFIX' for r in partials),
        residual_partial_file_bytes=sum(r['bytes'] for r in partials if r['file_kind'] == 'PART_SUFFIX'),
        other_transient_file_count=sum(r['file_kind'] != 'PART_SUFFIX' for r in partials),
        all_residual_files_are_exact_canonical_prefixes=all(r['exact_canonical_prefix_match'] is True for r in partials),
        full_duplicate_count=sum(r['complete_canonical_duplicate'] is True for r in partials),
        excluded_from_analysis=True, residual_files_preserved_without_modification=True,
        partial_file_origin='UNKNOWN. Presence or prefix equality alone does not establish how a file was created or imply additional network bytes.',
        additional_network_byte_attribution='UNKNOWN', package_exclusion_checks=package_checks,
        acquisition_log_coverage=log_coverage,
        extraction_input_verification='Every completed spectrum records hashes of its canonical RAW and ANCILLARY products; unavailable pairs remain explicit. Frozen extractor reads only canonical manifest relative paths. Independent numerical audit reconstructed saved cutouts from those inputs.',
        acquisition_attempts=dict(total=len(attempts),successful=len(succeeded),failed=len(failed),
            failed_attempts=failed,known_returned_payload_bytes=known,charged_payload_bytes=charged,
            unknown_bytes_conservatively_charged=manifest['unknown_bytes_conservatively_charged'],reserved_bytes=0),
        source_hashes={'products/MANIFEST.json':sha(manifest_path),'NATIVE_MAPPING.json':sha(mapping_path),
                       'extract_native.py':sha(extractor),'FOLLOWUP_FREEZE.json':sha(BATCH/'FOLLOWUP_FREEZE.json')},
        script_sha256=sha(Path(__file__)), canonical_products=canonical, noncanonical_payload_files=partials)
    destination.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['canonical_products','noncanonical_payload_files','source_hashes','acquisition_attempts','package_exclusion_checks']},indent=2))


if __name__ == '__main__':
    main()
