"""Read-only fresh-process reconstruction, with outputs restricted to audit/.

Do not invoke until the parent signals root-verified publication, acquisition,
and extraction completion. This never invokes acquisition or extraction and
makes no network request. It does not determine physical origin.
"""
from pathlib import Path
import argparse
import collections
import csv
import datetime
import gc
import hashlib
import importlib.metadata
import io
import json
import re
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True
AUDIT = Path(__file__).resolve().parent
FOLLOW = AUDIT.parent
EXT = FOLLOW.parent
BASE = EXT.parents[1]


def require(ok, detail):
    if not ok:
        raise RuntimeError(detail)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def write(name, value):
    require(Path(name).name == name and name.endswith('.json'), 'Audit output name')
    path = AUDIT / name
    require(not path.exists(), 'Audit output already exists: ' + name)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def verify_frozen(plan):
    require(sha(FOLLOW / 'FOLLOWUP_FREEZE.json') == plan['followup_freeze_sha256'], 'Follow-up freeze hash')
    require(sha(FOLLOW / 'INDEPENDENT_PREFLIGHT_REVIEW.json') == plan['independent_preflight_sha256'], 'Independent preflight hash')
    freeze = read(FOLLOW / 'FOLLOWUP_FREEZE.json')
    require(freeze['status'] == 'READY_FOR_ROOT_PUBLICATION_VERIFICATION', 'Follow-up freeze state')
    for relative, digest in freeze['source_hashes'].items():
        require(sha(BASE / relative) == digest, 'Follow-up frozen source changed: ' + relative)
    extension = read(EXT / 'FREEZE.json')
    for relative, digest in extension['source_hashes'].items():
        require(sha(BASE / relative) == digest, 'Original frozen source changed: ' + relative)
    for relative, digest in read(FOLLOW / 'PLAN.json')['immutable_scope_hashes'].items():
        require(sha(EXT / relative) == digest, 'Immutable scope changed: ' + relative)
    return freeze, extension


def mapping_ok(best):
    return (best['median_correlation'] is not None and best['median_correlation'] > .8
            and best['valid_regions'] >= 18 and best['valid_orders'] >= 5
            and best['median_abs_continuum_peak_offset'] <= 1)


def context(header):
    return {key: value for key, value in header.items()
            if any(part in key for part in ['DPR', 'INS OPTI', 'LAMP', 'DRIFT', 'CAL TH FILE', 'CAL LOC FILE'])
            and isinstance(value, (str, int, float, bool))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verified-published-commit', required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'[0-9a-f]{40}', args.verified_published_commit) is not None, 'Full independently verified commit required')
    require(not (AUDIT / 'NUMERIC_SUMMARY.json').exists(), 'Completed audit cannot be overwritten')
    started = time.monotonic()
    import numpy as np
    from astropy.io import fits
    # These two frozen modules are import-safe; never import extraction/acquisition.
    sys.path.insert(0, str(FOLLOW))
    from registration import evaluate_reference_grid, REFERENCE_ORDERS, REFERENCE_WINDOWS
    from local_registration import evaluate_local_trace

    plan = read(AUDIT / 'PLAN.json')
    plan_hash = sha(AUDIT / 'PLAN.json')
    freeze, extension_freeze = verify_frozen(plan)
    versions = {name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'astropy')}
    require(versions == extension_freeze['numerical_versions'], 'Frozen numerical versions differ')
    selected = rows(FOLLOW / 'SELECTED_EXPOSURES.csv')
    events = rows(FOLLOW / 'SELECTED_EVENTS.csv')
    require(len(selected) == len({r['dp_id'] for r in selected}) == 8, 'Expected eight unique selected exposures')
    require(len(events) == len({r['review_id'] for r in events}) == 65, 'Expected 65 unique selected events')
    require(collections.Counter(r['detector'] for r in events) == {'V1': 6, 'V2': 59}, 'Selected detector counts differ')
    positions = sorted({0, len(selected) // 2, len(selected) - 1})
    fixed = [{'selected_position': i + 1, 'dp_id': selected[i]['dp_id']} for i in positions]
    require(fixed == plan['reconstruction_exposures'] and len(fixed) == 3, 'Fixed reconstruction selection changed')
    reconstruct = {row['dp_id'] for row in fixed}

    all_main = rows(EXT / 'MAIN100.csv')
    hits = {name: rows(EXT / 'production' / (name + '_HITS.csv')) for name in ('V1', 'V2')}
    expected_selected = [r for r in all_main if r['dp_id'] in {h['dp_id'] for h in hits['V1']}][:8]
    used = {r['dp_id'] for r in expected_selected}
    expected_selected += [r for r in all_main if r['dp_id'] not in used and r['dp_id'] in {h['dp_id'] for h in hits['V2']}][:8 - len(expected_selected)]
    require(selected == expected_selected, 'Fixed priority/fill selection mismatch')
    selected_ids = {r['dp_id'] for r in selected}
    expected_event_ids = [h['candidate_id'] for name in ('V1', 'V2') for h in hits[name] if h['dp_id'] in selected_ids]
    require([r['review_id'] for r in events] == expected_event_ids, 'Accepted event membership/order mismatch')
    hit_lookup = {h['candidate_id']: h for group in hits.values() for h in group}
    for event in events:
        source_hit = hit_lookup[event['review_id']]
        key = 'wave_peak_angstrom' if event['detector'] == 'V1' else 'fitted_center_angstrom'
        require(event['fitted_center_bary_air_angstrom'] == source_hit[key], 'Candidate center mismatch')
        require(event['dp_id'] == source_hit['dp_id'] and event['source_sha256'] == source_hit['input_sha256'], 'Event source mismatch')
    unreviewed = rows(AUDIT / 'UNREVIEWED_V2_EVENTS.csv')
    selected_v2_ids = {event['review_id'] for event in events if event['detector'] == 'V2'}
    expected_unreviewed = [dict(hit, raw_review_status='NOT_SELECTED_FOR_BOUNDED_RAW_FOLLOWUP', origin_status='UNREVIEWED') for hit in hits['V2'] if hit['candidate_id'] not in selected_v2_ids]
    require(unreviewed == expected_unreviewed and len(unreviewed) == 277, 'Unreviewed V2 ledger/fields mismatch')
    unreviewed_ids = {event['candidate_id'] for event in unreviewed}
    require(not selected_v2_ids.intersection(unreviewed_ids) and selected_v2_ids.union(unreviewed_ids) == {hit['candidate_id'] for hit in hits['V2']}, 'V2 disjoint union incomplete')

    # Hash existing immutable production/extraction outputs; later visual files are
    # deliberately outside this snapshot so the separate visual review may proceed.
    protected = set()
    for folder in (EXT / 'production', EXT / 'acquisition', FOLLOW / 'products', FOLLOW / 'reference', FOLLOW / 'native'):
        protected.update(path for path in folder.rglob('*') if path.is_file())
    for name in ('NATIVE_MAPPING.json', 'LOCAL_TRACE_AUDIT.json', 'FIBER_INVENTORY.json', 'DOWNLOAD_STARTED.json', 'INDEPENDENT_PREFLIGHT_REVIEW.json'):
        protected.add(FOLLOW / name)
    protected.add(FOLLOW / 'PARTIAL_FILE_ANOMALY.json')
    protected.update(path for path in (FOLLOW / 'diagnostics/stale_partial_files').rglob('*') if path.is_file())
    protected.add(AUDIT / 'UNREVIEWED_V2_EVENTS.csv')
    protected.add(AUDIT / 'NUMERIC_UNREVIEWED_LEDGER_CHECK.json')
    protected.add(AUDIT / 'NUMERIC_PARTIAL_ANOMALY_CHECK.json')
    snapshot = {str(path.relative_to(BASE)): sha(path) for path in sorted(protected)}
    job_list = read(FOLLOW / 'JOBS.json')
    ledger = read(FOLLOW / 'products/MANIFEST.json')
    receipts = ledger['products']
    initiation = read(FOLLOW / 'DOWNLOAD_STARTED.json')
    require(len(job_list) == len(receipts) == 16, 'Expected exactly 16 product receipts')
    require(ledger['publication'] == initiation['publication'], 'Publication receipt mismatch')
    require(ledger['publication']['commit'] == args.verified_published_commit, 'Root-verified commit mismatch')
    require(ledger['publication']['freeze_sha256'] == plan['followup_freeze_sha256'], 'Published freeze mismatch')
    require(datetime.datetime.fromisoformat(initiation['started_utc']) >= datetime.datetime.fromisoformat(plan['created_utc']), 'Acquisition predates audit plan')
    require(datetime.datetime.fromisoformat(ledger['publication']['verified_utc']) >= datetime.datetime.fromisoformat(freeze['created_utc']), 'Publication confirmation predates freeze')
    cap = read(FOLLOW / 'PLAN.json')['acquisition_bounds']['payload_cap_bytes']
    require(cap == ledger['payload_cap_bytes'] == initiation['payload_cap_bytes'], 'Payload cap mismatch')
    require(ledger['reserved_bytes'] == 0 and ledger['replacements'] == 0, 'Outstanding reservation or replacement')
    expected_keys = [(job['dp_id'], job['kind']) for job in job_list]
    require([(r['dp_id'], r['kind']) for r in receipts] == expected_keys and len(set(expected_keys)) == 16, 'Product identity/order mismatch')
    science = {r['dp_id']: r for r in read(EXT / 'acquisition/DOWNLOAD_MANIFEST.json')}
    product_records, byte_total, charged, known = [], 0, 0, 0
    for job, receipt in zip(job_list, receipts):
        require(receipt['status'] == 'DOWNLOADED', 'Incomplete product: ' + job['filename'])
        for key, value in job.items():
            require(receipt['metadata_attempts' if key == 'attempts' else key] == value, 'Frozen job/receipt field mismatch: ' + key)
        require(read(FOLLOW / 'products' / (job['filename'] + '.json')) == receipt, 'Per-product receipt mismatch')
        product = BASE / receipt['relative_path']
        require(product.resolve() == (FOLLOW / 'products' / job['filename']).resolve(), 'Unexpected product path')
        require(product.stat().st_size == receipt['bytes'] == job['advertised_bytes'], 'Product byte count mismatch')
        require(sha(product) == receipt['sha256'], 'Product hash mismatch')
        require(receipt['metadata_check'] == 'PASS_RAW_OR_NATIVE_ID_DATE_AND_CONTAINER', 'Missing metadata acceptance')
        attempts = receipt['attempts']
        require(1 <= len(attempts) <= 2 and [a['timeout_seconds'] for a in attempts] == [20, 60][:len(attempts)], 'Payload attempt limits/order')
        require(attempts[-1]['outcome'] == 'SUCCESS' and all(a['outcome'] == 'FAILED' for a in attempts[:-1]), 'Attempt outcome ordering')
        for attempt in attempts:
            require(0 <= attempt['known_returned_payload_bytes'] <= attempt['charged_payload_bytes'], 'Attempt accounting inequality')
            charged += attempt['charged_payload_bytes']
            known += attempt['known_returned_payload_bytes']
        require(attempts[-1]['known_returned_payload_bytes'] == attempts[-1]['charged_payload_bytes'] == receipt['bytes'], 'Successful transfer accounting')
        byte_total += receipt['bytes']
        product_records.append(dict(dp_id=job['dp_id'], kind=job['kind'], bytes=receipt['bytes'], sha256=receipt['sha256'], attempts=len(attempts), status='HASH_LENGTH_AND_RECEIPT_EXACT'))
    require(charged == ledger['charged_payload_bytes'] and known == ledger['known_returned_payload_bytes'], 'Attempt/ledger totals disagree')
    require(0 <= byte_total <= known <= charged <= cap, 'Payload bound inequality')
    require(charged - known == ledger['unknown_bytes_conservatively_charged'], 'Unknown byte charge mismatch')
    anomaly = read(FOLLOW / 'PARTIAL_FILE_ANOMALY.json')
    require(anomaly['status'] == 'UNEXPLAINED_STALE_PARTIAL_PREFIXES_PRESERVED_AND_EXCLUDED', 'Unexpected anomaly disposition')
    require(len(anomaly['files']) == 3 and not list((FOLLOW / 'products').glob('*.part')), 'Partial-file quarantine incomplete')
    receipt_by_name = {Path(receipt['relative_path']).name: receipt for receipt in receipts}
    prefix_checks = []
    for record in anomaly['files']:
        prefix_path = FOLLOW / record['preserved_relative_path']
        final_path = FOLLOW / record['final_relative_path']
        require(prefix_path.resolve().parent == (FOLLOW / 'diagnostics/stale_partial_files').resolve(), 'Unexpected quarantine path')
        require(final_path.resolve().parent == (FOLLOW / 'products').resolve() and final_path.name in receipt_by_name, 'Unknown final prefix counterpart')
        require(not (FOLLOW / record['original_relative_path']).exists(), 'Stale partial still in products')
        prefix = prefix_path.read_bytes()
        with final_path.open('rb') as stream:
            final_prefix = stream.read(len(prefix))
        require(len(prefix) == record['bytes'] and sha(prefix_path) == record['sha256'] and prefix == final_prefix, 'Preserved partial prefix mismatch')
        require(record['final_sha256'] == receipt_by_name[final_path.name]['sha256'] == sha(final_path), 'Partial counterpart hash mismatch')
        mtime = datetime.datetime.fromtimestamp(prefix_path.stat().st_mtime, datetime.timezone.utc)
        require(mtime.isoformat() == record['mtime_utc'] and mtime < datetime.datetime.fromisoformat(ledger['created_utc']), 'Partial timestamp discrepancy')
        prefix_checks.append(dict(preserved_relative_path=record['preserved_relative_path'], bytes=len(prefix), sha256=record['sha256'], final_relative_path=record['final_relative_path'], final_sha256=record['final_sha256'], exact_prefix=True, mtime_utc=record['mtime_utc'], mtime_predates_manifest=True, excluded_from_product_manifest=True))
    require(sum(record['bytes'] for record in prefix_checks) == anomaly['combined_bytes'] == 4194304, 'Preserved partial byte total')
    require({FOLLOW / record['preserved_relative_path'] for record in anomaly['files']} == set((FOLLOW / 'diagnostics/stale_partial_files').glob('*')), 'Extra/missing preserved partial evidence')

    mapping = read(FOLLOW / 'NATIVE_MAPPING.json')
    local_table = read(FOLLOW / 'LOCAL_TRACE_AUDIT.json')['orders']
    inventory = read(FOLLOW / 'FIBER_INVENTORY.json')
    require(mapping['hits'] == len(events), 'Mapping event count')
    spectrum_by_id = {r['dp_id']: r for r in mapping['spectra']}
    require(len(spectrum_by_id) == len(mapping['spectra']) == 8 and set(spectrum_by_id) == selected_ids, 'Mapping exposure accounting')
    event_by_id = {r['review_id']: r for r in mapping['events']}
    require(len(event_by_id) == len(mapping['events']) == 65 and set(event_by_id) == set(expected_event_ids), 'Mapping event identities')
    order_by_key = {(r['review_id'], r['order']): r for r in mapping['orders']}
    require(len(order_by_key) == len(mapping['orders']), 'Duplicate event/order rows')
    local_by_key = {(r['review_id'], r['order']): r for r in local_table}
    require(len(local_by_key) == len(local_table), 'Duplicate local audit rows')
    inventory_by_id = {r['dp_id']: r for r in inventory}
    require(len(inventory_by_id) == len(inventory) == 8 and set(inventory_by_id) == selected_ids, 'Fibre inventory accounting')
    shape_spec = dict(raw_cutout=(21, 25), raw_background=(25,), raw_excess=(21, 25), native_wave=(41,), native_flux=(41,))
    checked_orders, checked_exposures, reconstructed_records = [], [], []
    expected_order_keys, expected_local_keys, expected_npz_paths = set(), set(), set()
    expected_mapping_event_order = []

    def polynomial(header, prefix, degree, order, pixel):
        coefficients = [header[prefix + str(order * (degree + 1) + i)] for i in range(degree + 1)]
        return np.polynomial.polynomial.polyval(pixel, coefficients)

    def same_arrays(left, right, detail):
        require(left.shape == right.shape and np.array_equal(left, right, equal_nan=True), detail)

    for selected_row in selected:
        dp = selected_row['dp_id']
        print('AUDIT_EXPOSURE ' + dp + (' FULL_RAW_RECONSTRUCTION' if dp in reconstruct else 'NATIVE_AND_HEADER_CHECK'), flush=True)
        tick = time.monotonic()
        source_receipt = science[dp]
        require(sha(BASE / source_receipt['relative_path']) == source_receipt['sha256'], 'Merged science source hash')
        source_header = source_receipt['primary_header']
        pair = {r['kind']: r for r in receipts if r['dp_id'] == dp}
        require(set(pair) == {'RAW', 'ANCILLARY'}, 'Product pair coverage')
        rr, tr = pair['RAW'], pair['ANCILLARY']
        require(rr['raw_id'] == tr['raw_id'] == selected_row['raw_progenitor_id'], 'Parent exposure mismatch')
        for receipt in pair.values():
            require(receipt['source_science_sha256'] == source_receipt['sha256'] and receipt['source_date_obs'] == source_header['DATE-OBS'], 'Merged/product identity mismatch')
        raw_payload = subprocess.run(['gzip', '-cd', str(BASE / rr['relative_path'])], check=True, capture_output=True).stdout
        with fits.open(io.BytesIO(raw_payload), memmap=False) as hdus:
            rh = hdus[0].header.copy()
            require(rh.get('ARCFILE', '').removesuffix('.fits') == rr['raw_id'], 'Raw ARCFILE identity')
            require(rh.get('DATE-OBS') == source_header['DATE-OBS'] and rh.get('INSTRUME') == 'HARPS', 'Raw date/instrument identity')
            require(len(hdus) >= 3, 'Raw detector extensions missing')
            for extension in (1, 2):
                require(hdus[extension].header['NAXIS2'] == 4096 and hdus[extension].header['NAXIS1'] >= 2098, 'Raw detector header dimensions')
            raw = np.hstack((hdus[1].data[:, 50:2098], hdus[2].data[:, 50:2098])).astype(float) if dp in reconstruct else None
        del raw_payload
        if raw is not None:
            require(raw.shape == (4096, 4096), 'Reconstructed raw dimensions')
        with tarfile.open(BASE / tr['relative_path']) as archive:
            members = archive.getmembers()
            native_members = [m for m in members if m.name.endswith('_e2ds_A.fits')]
            require(len(native_members) == 1, 'Ambiguous native-A TAR membership')
            member = native_members[0]
            require(Path(member.name).name == rr['raw_id'] + '_e2ds_A.fits', 'Native raw-parent member identity')
            with fits.open(io.BytesIO(archive.extractfile(member).read()), memmap=False) as hdus:
                header = hdus[0].header.copy()
                native = hdus[0].data.astype(float)
            require(header.get('INSTRUME') == 'HARPS' and header.get('DATE-OBS') == rh['DATE-OBS'], 'Native date/instrument identity')
            normalize = lambda value: re.sub('[^A-Z0-9]', '', str(value).upper())
            require(bool(normalize(source_header['OBJECT'])) and normalize(header.get('OBJECT', '')) == normalize(source_header['OBJECT']), 'Native object identity')
            berv = float(header['ESO DRS BERV'])
            require(np.isfinite(berv) and abs(berv - source_header['HIERARCH ESO DRS BERV']) < 1e-8, 'Native/science BERV identity')
            require(native.shape == (72, 4096), 'Native array shape')
            reproduced_inventory = dict(dp_id=dp, raw_context=context(rh), members=[m.name for m in members], fiber_headers={})
            for fiber in ('A', 'B'):
                available = [m for m in members if m.name.endswith('_e2ds_' + fiber + '.fits')]
                if not available:
                    reproduced_inventory['fiber_headers'][fiber] = dict(status='MISSING')
                else:
                    require(len(available) == 1, 'Ambiguous native fibre membership')
                    with fits.open(io.BytesIO(archive.extractfile(available[0]).read()), memmap=False) as hdus:
                        reproduced_inventory['fiber_headers'][fiber] = dict(status='PRESENT', context=context(hdus[0].header), member=available[0].name)
            reproduced_inventory['independent_sky_fiber_available'] = rh.get('ESO DPR TYPE', '').split(',')[1:2] == ['SKY'] and reproduced_inventory['fiber_headers']['B']['status'] == 'PRESENT'
            require(reproduced_inventory == inventory_by_id[dp], 'Fibre/header inventory mismatch')
        degree = int(header['ESO DRS CAL TH DEG LL'])
        location_degree = int(header['ESO DRS CAL LOC DEG CTR'])
        x = np.arange(4096)
        waves = np.array([polynomial(header, 'ESO DRS CAL TH COEFF LL', degree, order, x) for order in range(72)])
        require(np.isfinite(waves).all() and (np.diff(waves, axis=1) > 0).all(), 'Native wavelengths must be finite and increasing')
        exposure_events = [r for r in events if r['dp_id'] == dp]
        candidates, covers = [], {}
        for event in exposure_events:
            center = float(event['fitted_center_bary_air_angstrom']) / (1 + berv / 299792.458)
            covering = np.flatnonzero((waves[:, 0] < center) & (waves[:, -1] > center)).tolist()
            covers[event['review_id']] = (center, covering)
            for order in covering:
                candidates.append(dict(review_id=event['review_id'], order=order, native_pixel=int(np.argmin(abs(waves[order] - center)))))
        saved_spectrum = spectrum_by_id[dp]
        grid_path = FOLLOW / saved_spectrum['reference_grid']
        require(grid_path.resolve().parent == (FOLLOW / 'reference').resolve(), 'Unexpected reference path')
        grid = read(grid_path)
        best = grid['orientation_summaries'][0]
        good_mapping = mapping_ok(best)
        require(saved_spectrum['grid_best'] == best and saved_spectrum['status'] == ('REGISTERED' if good_mapping else 'MAPPING_UNCERTAIN'), 'Global mapping flag mismatch')
        require(saved_spectrum['raw_sha256'] == rr['sha256'] and saved_spectrum['ancillary_sha256'] == tr['sha256'], 'Mapping source hash mismatch')
        require(saved_spectrum['date_obs'] == rh['DATE-OBS'] and saved_spectrum['berv_km_s'] == berv and saved_spectrum['native_member'] == member.name, 'Mapping source metadata mismatch')
        expected_regions = [(order, window) for order in REFERENCE_ORDERS for window in REFERENCE_WINDOWS]
        require(len(grid['reference_regions']) == len(expected_regions), 'Reference region count')
        for saved_region, (order, (lo, hi)) in zip(grid['reference_regions'], expected_regions):
            pixels = np.arange(lo, hi)
            mask = np.ones(len(pixels), dtype=bool)
            excluded = []
            for candidate in candidates:
                if candidate['order'] == order:
                    nearby = abs(pixels - candidate['native_pixel']) <= 80
                    if nearby.any():
                        excluded.append(candidate['review_id'])
                    mask &= ~nearby
            require(saved_region['order'] == order and saved_region['pixel_interval_half_open'] == [lo, hi], 'Reference grid coordinates')
            require(saved_region['samples'] == int(mask.sum()) and saved_region['excluded_candidate_ids'] == excluded, 'All-candidate reference exclusion mismatch')
            require(saved_region['status'] == ('VALID' if mask.sum() >= 100 else 'INSUFFICIENT_REFERENCE_SAMPLES'), 'Reference sample validity')
        if dp in reconstruct:
            regenerated_grid = evaluate_reference_grid(raw, native, header, candidates)
            require(regenerated_grid == grid, 'Entire reference grid not exactly reproduced: ' + dp)
        extracted_count, edge_count, reconstructed_count = 0, 0, 0
        for event in exposure_events:
            review_id = event['review_id']
            expected_mapping_event_order.append(review_id)
            center, covering = covers[review_id]
            saved_event = event_by_id[review_id]
            require(saved_event['dp_id'] == dp and saved_event['detector'] == event['detector'] and saved_event['covering_orders'] == covering and saved_event['origin_status'] == 'UNREVIEWED', 'Event/order coverage metadata mismatch')
            event_extracted = False
            for order in covering:
                key = (review_id, order)
                expected_order_keys.add(key)
                require(key in order_by_key, 'Missing covering order')
                saved = order_by_key[key]
                require(saved['dp_id'] == dp and saved['detector'] == event['detector'], 'Order identity mismatch')
                k = int(np.argmin(abs(waves[order] - center)))
                cy = 4095 - k if best['row_flip'] else k
                argument = 4095 - k if best['argument_flip'] else k
                cx = float(polynomial(header, 'ESO DRS CAL LOC CTR', location_degree, order, argument))
                if best['column_flip']:
                    cx = 4095 - cx
                icx = round(cx)
                require(saved['native_pixel'] == k, 'Nearest native pixel mismatch')
                complete = 20 <= k < 4076 and 12 <= icx < 4084 and 10 <= cy < 4086
                if not complete:
                    require(saved['status'] == 'EDGE_TRUNCATED', 'Missing edge limitation')
                    edge_count += 1
                    checked_orders.append(dict(review_id=review_id, order=order, dp_id=dp, status='EDGE_TRUNCATION_REPRODUCED'))
                    continue
                require(saved['status'] == 'EXTRACTED' and saved['origin_status'] == 'UNREVIEWED', 'Order extraction/origin status')
                expected_local_keys.add(key)
                require(key in local_by_key, 'Missing local audit')
                local = local_by_key[key]
                require(local['dp_id'] == dp and local['global_reference_mapping_verified'] == good_mapping, 'Local audit exposure/global mapping')
                # The inherited gate uses offsets only. Correlation remains descriptive.
                local_usable = all(window['peak_offset'] is not None and abs(window['peak_offset']) <= 1 for window in local['windows'])
                require(local['local_mapping_usable'] == local_usable and local['visual_local_mapping_warning'] == (not local_usable), 'Offset-only local gate mismatch')
                for saved_window, (lo, hi) in zip(local['windows'], [(-280, -80), (81, 281)]):
                    pixels = np.arange(max(0, k + lo), min(4096, k + hi))
                    for candidate in candidates:
                        if candidate['order'] == order:
                            pixels = pixels[abs(pixels - candidate['native_pixel']) > 80]
                    args_for_trace = 4095 - pixels if best['argument_flip'] else pixels
                    columns = polynomial(header, 'ESO DRS CAL LOC CTR', location_degree, order, args_for_trace)
                    if best['column_flip']:
                        columns = 4095 - columns
                    integer_columns = np.rint(columns).astype(int)
                    expected_samples = int(((integer_columns >= 5) & (integer_columns < 4091)).sum())
                    require(saved_window['relative_interval_half_open'] == [lo, hi] and saved_window['samples'] == expected_samples, 'All-candidate local exclusion mismatch')
                    if expected_samples < 60:
                        require(saved_window['peak_offset'] is None and saved_window['correlation'] is None, 'Insufficient local samples accepted')
                require(len(local['windows']) == 2, 'Two local windows required')
                if dp in reconstruct:
                    recreated_local = evaluate_local_trace(raw, native, header, order, k, best, candidates)
                    recreated_local.update(review_id=review_id, order=order, dp_id=dp, global_reference_mapping_verified=good_mapping)
                    require(recreated_local == local, 'Entire local audit not exactly reproduced')
                expected_fields = dict(topocentric_air_angstrom=center, native_nearest_wave_angstrom=float(waves[order, k]), raw_row=cy, raw_column=cx, mapping_verified=good_mapping and local_usable, grid_mapping_usable=good_mapping, local_mapping_usable=local_usable, reference_correlation=best['median_correlation'], target=event['target'])
                require(all(saved[field] == value for field, value in expected_fields.items()), 'Reconstructed order coordinates/flags mismatch')
                expected_name = review_id + '_o' + str(order).zfill(2) + '.npz'
                require(saved['cutout'] == 'native/' + expected_name, 'NPZ filename mismatch')
                npz_path = FOLLOW / saved['cutout']
                expected_npz_paths.add(npz_path)
                with np.load(npz_path, allow_pickle=False) as bundle:
                    require(set(bundle.files) == set(shape_spec), 'NPZ field set mismatch')
                    arrays = {name: bundle[name] for name in bundle.files}
                for name, shape in shape_spec.items():
                    require(arrays[name].shape == shape and arrays[name].dtype == np.dtype('float64'), 'NPZ shape/dtype mismatch: ' + name)
                background = np.median(arrays['raw_cutout'][np.r_[0:5, 16:21]], axis=0)
                same_arrays(arrays['raw_background'], background, 'Saved raw background algebra mismatch')
                same_arrays(arrays['raw_excess'], arrays['raw_cutout'] - background[None, :], 'Saved raw excess algebra mismatch')
                same_arrays(arrays['native_wave'], waves[order, k - 20:k + 21], 'Native wavelength reconstruction mismatch')
                same_arrays(arrays['native_flux'], native[order, k - 20:k + 21], 'Native flux correspondence mismatch')
                if dp in reconstruct:
                    cutout = raw[cy - 10:cy + 11, icx - 12:icx + 13]
                    same_arrays(arrays['raw_cutout'], cutout, 'Raw cutout reconstruction mismatch')
                    fresh_background = np.median(cutout[np.r_[0:5, 16:21]], axis=0)
                    same_arrays(arrays['raw_background'], fresh_background, 'Reconstructed background mismatch')
                    same_arrays(arrays['raw_excess'], cutout - fresh_background[None, :], 'Reconstructed excess mismatch')
                    reconstructed_count += 1
                    reconstructed_records.append(dict(dp_id=dp, review_id=review_id, order=order, fields=list(shape_spec), status='ALL_FIVE_ARRAYS_EXACT_WITH_NAN_EQUALITY'))
                checked_orders.append(dict(review_id=review_id, order=order, dp_id=dp, status='ALL_SHAPES_ALGEBRA_NATIVE_AND_COORDINATES_EXACT', raw_reconstructed=dp in reconstruct, npz_sha256=sha(npz_path), mapping_verified=saved['mapping_verified'], local_peak_offsets=[w['peak_offset'] for w in local['windows']], local_correlations=[w['correlation'] for w in local['windows']], nonfinite_samples={name: int((~np.isfinite(array)).sum()) for name, array in arrays.items()}))
                extracted_count += 1
                event_extracted = True
            require(saved_event['status'] == ('NATIVE_CONTEXT_EXTRACTED' if event_extracted else 'NO_USABLE_FULL_CUTOUT'), 'Event extraction status mismatch')
        checked_exposures.append(dict(dp_id=dp, event_count=len(exposure_events), covering_order_count=sum(len(covers[e['review_id']][1]) for e in exposure_events), extracted_orders=extracted_count, edge_truncated_orders=edge_count, reconstructed_raw_orders=reconstructed_count, entire_reference_grid_recomputed=dp in reconstruct, all_local_diagnostics_recomputed=dp in reconstruct, raw_native_identity='PASS', fibre_inventory_exact=True, native_all_orders_finite_increasing_wavelengths=True, global_mapping_verified=good_mapping, elapsed_seconds=time.monotonic() - tick))
        del raw, native, waves
        gc.collect()

    require(expected_order_keys == set(order_by_key), 'Extra or missing mapping orders')
    require(expected_local_keys == set(local_by_key), 'Extra or missing local diagnostics')
    require(expected_npz_paths == set((FOLLOW / 'native').glob('*.npz')), 'Extra or missing NPZ files')
    require(expected_mapping_event_order == [r['review_id'] for r in mapping['events']], 'Extraction event order mismatch')
    extracted_total = sum(r['extracted_orders'] for r in checked_exposures)
    require(extracted_total == mapping['extracted_orders'] == len(expected_npz_paths), 'Extracted order counts disagree')
    require({r['dp_id'] for r in checked_exposures if r['entire_reference_grid_recomputed']} == reconstruct, 'Fixed reconstruction coverage incomplete')
    verify_frozen(plan)
    require(sha(AUDIT / 'PLAN.json') == plan_hash, 'Audit plan changed')
    for relative, digest in snapshot.items():
        require(sha(BASE / relative) == digest, 'Protected input/output changed during audit: ' + relative)
    report = dict(
        status='PASS_INDEPENDENT_NUMERIC_RAW_AUDIT', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        audit_plan_sha256=plan_hash, audit_code_sha256=sha(Path(__file__)), followup_freeze_sha256=plan['followup_freeze_sha256'],
        verified_published_commit=args.verified_published_commit, numerical_versions=versions,
        selected_exposures=8, selected_events=65, detector_event_counts={'V1': 6, 'V2': 59},
        unreviewed_v2_events_outside_selected_exposures=277, all_336_v2_events_accounted_for_by_disjoint_union=True,
        all_products_hash_length_identity_verified=16, product_bytes=byte_total,
        charged_payload_bytes=charged, known_returned_payload_bytes=known, unknown_bytes_conservatively_charged=charged - known, payload_cap_bytes=cap,
        recorded_payload_ledger_internally_consistent=True, wire_transfer_independently_verified=False,
        unresolved_stale_partial_file_anomaly=True, preserved_partial_files=prefix_checks,
        all_event_covering_orders=len(expected_order_keys), all_npz_checked=extracted_total,
        edge_truncated_orders=sum(r['edge_truncated_orders'] for r in checked_exposures),
        fixed_reconstruction_exposures=fixed, raw_orders_exactly_reconstructed=len(reconstructed_records),
        native_array_correspondence_exposures=8, entire_reference_grids_exactly_recomputed=3,
        entire_local_audits_exactly_recomputed=len(reconstructed_records),
        protected_files_unchanged=len(snapshot), original_frozen_source_hashes_verified=len(extension_freeze['source_hashes']), followup_frozen_source_hashes_verified=len(freeze['source_hashes']),
        local_gate='Two candidate-excluded continuum peak offsets within one pixel, at least 60 samples in each window. Local correlation is reported but does not enter the inherited pass rule. This is not the mapping43 broader-reference gate.',
        comparison='Exact numeric array equality with corresponding NaNs allowed; nonfinite counts retained per NPZ. Entire saved JSON grid/local diagnostics match on the three fixed reconstruction exposures.',
        network_calls=0, downloads=0, source_or_extraction_files_modified=0, elapsed_seconds=time.monotonic() - started,
        limitations=[
            'Fresh-process reconstruction of the same frozen conventions and registration algorithms; not an independent detector implementation.',
            'All eight native spectra were reopened for sample correspondence; original raw pixel arrays were reconstructed only for the three preselected exposures. Other raw cutouts received algebra, shape, hash and coordinate checks.',
            'All sixteen containers received archive/date/header identity checks, but metadata identity does not independently establish pointing or photon origin.',
            'Header-based wavelength mapping uses the frozen classical inverse-BERV convention; this is not a new reduction or absolute wavelength calibration.',
            'No visual/origin classification, physical-origin validation, false-alarm calibration or sensitivity claim follows from this numeric audit.',
            'Publication correctness is rooted in the parent/root verification signal and matching local receipt; this audit performs no remote verification.'
            , 'Three unexplained stale partial-name files totaling 4194304 bytes are exact prefixes of verified final products, predate the manifest, and are preserved outside the science product inventory. Their cause and network provenance remain unknown. Reconciliation of the recorded 210108924-byte ledger does not independently prove the absence or presence of additional wire transfers or requests.'
        ])
    write('NUMERIC_PRODUCT_CHECKS.json', product_records)
    write('NUMERIC_ORDER_CHECKS.json', checked_orders)
    write('NUMERIC_RECONSTRUCTIONS.json', dict(exposures=checked_exposures, reconstructed_arrays=reconstructed_records))
    write('NUMERIC_INPUT_HASHES.json', snapshot)
    write('NUMERIC_SUMMARY.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'selected_events', 'all_event_covering_orders', 'all_npz_checked', 'raw_orders_exactly_reconstructed', 'charged_payload_bytes', 'elapsed_seconds')}), flush=True)


if __name__ == '__main__':
    main()
