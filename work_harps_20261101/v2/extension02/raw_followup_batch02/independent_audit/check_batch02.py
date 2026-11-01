"""Independent source reconstruction and numerical audit of batch02.

No project analysis modules are imported. Reads new raw arrays only when main is
explicitly invoked after root's publication/acquisition gate. Writes only here.
"""
from pathlib import Path
import csv
import datetime
import hashlib
import io
import itertools
import json
import re
import subprocess
import sys
import tarfile

import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
EXT = BATCH.parent
BASE = EXT.parents[1]
WINDOWS = [(128, 768), (896, 1536), (1664, 2304), (2432, 3072), (3200, 3968)]
GRID_ORDERS = [10, 30, 50, 62, 63, 69]
GRID_WINDOWS = [(600, 900), (1400, 1700), (2200, 2500), (3000, 3300)]
ORIENTATIONS = list(itertools.product([False, True], repeat=3))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def numeric(actual, expected, message, atol=1e-9):
    if expected is None:
        require(actual is None, message + ': expected unavailable')
    else:
        require(actual is not None, message + ': unexpectedly unavailable')
        require(np.allclose(actual, expected, rtol=1e-11, atol=atol, equal_nan=False), message)


def coefficients(header, prefix, degree_key, order):
    degree = int(header[degree_key])
    return [float(header[prefix + str(order * (degree + 1) + i)]) for i in range(degree + 1)]


def polynomial(coeffs, x):
    # Direct powers/sum, independent of production's NumPy polynomial.polyval.
    x = np.asarray(x, dtype=float)
    return sum(value * x ** power for power, value in enumerate(coeffs))


def trace(header, order, x, orientation):
    _, column_flip, argument_flip = orientation
    x = 4095 - x if argument_flip else x
    values = polynomial(coefficients(header, 'ESO DRS CAL LOC CTR', 'ESO DRS CAL LOC DEG CTR', order), x)
    return 4095 - values if column_flip else values


def residual(values):
    return values - median_filter(values, size=31, mode='nearest')


def pearson(a, b):
    # Centered dot products instead of production's corrcoef.
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    a, b = a - np.mean(a), b - np.mean(b)
    denominator = np.sqrt(np.dot(a, a) * np.dot(b, b))
    if denominator == 0:
        return None
    value = float(np.dot(a, b) / denominator)
    return value if np.isfinite(value) else None


def exclusion(x, order, candidates):
    mask = np.ones(len(x), dtype=bool)
    excluded = []
    for hit in candidates:
        if hit['order'] != order:
            continue
        near = (x >= hit['pixel'] - 80) & (x <= hit['pixel'] + 80)
        if near.any():
            excluded.append(hit['id'])
        mask &= ~near
    return mask, excluded


def audit_global(raw, native, header, candidates, stored):
    expected_keys = [(o, list(w)) for o in GRID_ORDERS for w in GRID_WINDOWS]
    require([(r['order'], r['pixel_interval_half_open']) for r in stored['reference_regions']] == expected_keys, 'Global reference region coverage')
    by_orientation = {orientation: [] for orientation in ORIENTATIONS}
    for record in stored['reference_regions']:
        order = record['order']
        x = np.arange(*record['pixel_interval_half_open'])
        mask, excluded = exclusion(x, order, candidates)
        require(record['samples'] == int(mask.sum()) and record['excluded_candidate_ids'] == excluded, 'Global exclusion mismatch')
        require(record['status'] == ('VALID' if mask.sum() >= 100 else 'INSUFFICIENT_REFERENCE_SAMPLES'), 'Global sample status')
        native_hp = residual(native[order, x])
        require(len(record['options']) == 8, 'Global orientation count')
        for orientation, option in zip(ORIENTATIONS, record['options']):
            require(orientation == (option['row_flip'], option['column_flip'], option['argument_flip']), 'Global orientation sequence')
            y = 4095 - x if orientation[0] else x
            cx = np.rint(trace(header, order, x, orientation)).astype(int)
            bounded = bool(np.all((cx >= 8) & (cx < 4088)))
            require(option['valid_spatial_support'] == bounded, 'Global spatial bounds')
            if mask.sum() >= 100 and bounded:
                aperture = sum(raw[y, cx + offset] for offset in range(-3, 4))
                correlation = pearson(native_hp[mask], residual(aperture)[mask])
                profile = np.array([np.median(raw[y[mask], cx[mask] + offset]) for offset in range(-8, 9)])
                peak = int(np.argmax(profile)) - 8
                numeric(option['continuum_profile'], profile, 'Global profile')
                require(option['continuum_peak_integer_offset'] == peak, 'Global integer offset')
                if correlation is not None:
                    by_orientation[orientation].append((order, correlation, peak))
            else:
                correlation = None
                require(option['continuum_profile'] is None and option['continuum_peak_integer_offset'] is None, 'Invalid global region output')
            numeric(option['correlation'], correlation, 'Global correlation')
    summaries = []
    for orientation in ORIENTATIONS:
        items = by_orientation[orientation]
        cs = [item[1] for item in items]
        offsets = [abs(item[2]) for item in items]
        summaries.append(dict(orientation=orientation, valid_regions=len(items), valid_orders=len({item[0] for item in items}), median_correlation=float(np.median(cs)) if cs else None, min_correlation=min(cs) if cs else None, max_correlation=max(cs) if cs else None, median_abs_continuum_peak_offset=float(np.median(offsets)) if offsets else None, max_abs_continuum_peak_offset=max(offsets) if offsets else None, regions_above_original_0p8_threshold=sum(v > .8 for v in cs), regions_peak_within_one_pixel=sum(v <= 1 for v in offsets)))
    summaries.sort(key=lambda item: item['median_correlation'] if item['median_correlation'] is not None else -2, reverse=True)
    require(len(stored['orientation_summaries']) == 8, 'Global summary count')
    for actual, expected in zip(stored['orientation_summaries'], summaries):
        require((actual['row_flip'], actual['column_flip'], actual['argument_flip']) == expected['orientation'], 'Global orientation ranking')
        for key, value in expected.items():
            if key == 'orientation':
                continue
            numeric(actual[key], value, 'Global summary ' + key)
    best = summaries[0]
    usable = (best['median_correlation'] is not None and best['median_correlation'] > .8 and best['valid_regions'] >= 18 and best['valid_orders'] >= 5 and best['median_abs_continuum_peak_offset'] <= 1)
    return best['orientation'], bool(usable)


def audit_five(raw, native, header, order, orientation, candidates, stored):
    require([r['pixel_interval_half_open'] for r in stored['windows']] == [list(w) for w in WINDOWS], 'Five-window bounds')
    correlations, offsets = [], []
    for record, (lo, hi) in zip(stored['windows'], WINDOWS):
        x = np.arange(lo, hi)
        y = 4095 - x if orientation[0] else x
        columns = trace(header, order, x, orientation)
        mask, excluded = exclusion(x, order, candidates)
        bounds = (columns >= 9) & (columns < 4086)
        mask &= bounds
        require(record['samples'] == int(mask.sum()) and record['excluded_ids'] == excluded, 'Five-window exclusions')
        if mask.sum() >= 200 and bounds.all():
            samples = []
            for offset in range(-8, 9):
                c = columns + offset
                low = np.floor(c).astype(int)
                fraction = c - low
                samples.append(raw[y, low] + fraction * (raw[y, low + 1] - raw[y, low]))
            samples = np.array(samples)
            profile = np.array([np.median(s[mask]) for s in samples])
            profile -= np.median([*profile[:2], *profile[-2:]])
            peak = int(np.argmax(profile))
            peak_offset = float(peak - 8)
            if 0 < peak < 16:
                a, b, c = profile[peak - 1:peak + 2]
                denominator = a - 2 * b + c
                if denominator != 0:
                    peak_offset += .5 * (a - c) / denominator
            correlation = pearson(residual(native[order, x])[mask], residual(samples[5:12].sum(axis=0))[mask])
            numeric(record['profile'], profile, 'Five-window profile', atol=1e-7)
            numeric(record['peak_offset'], peak_offset, 'Five-window peak', atol=1e-8)
            numeric(record['peak_above_outer_baseline'], float(profile.max()), 'Five-window peak amplitude', atol=1e-7)
            if correlation is not None:
                correlations.append(correlation)
                offsets.append(abs(peak_offset))
        else:
            correlation = None
            require(record['profile'] is None and record['peak_offset'] is None, 'Unavailable five-window output')
        numeric(record['correlation'], correlation, 'Five-window correlation', atol=1e-8)
    median_correlation = float(np.median(correlations)) if correlations else None
    median_offset = float(np.median(offsets)) if offsets else None
    within = sum(offset <= 1 for offset in offsets)
    usable = bool(len(correlations) >= 3 and median_correlation > .8 and median_offset <= .75 and within >= 3)
    require(stored['valid_reference_windows'] == len(correlations), 'Five-window valid count')
    require(stored['windows_within_one_pixel'] == within, 'Five-window offset count')
    numeric(stored['median_correlation'], median_correlation, 'Five-window median correlation', atol=1e-8)
    numeric(stored['median_abs_peak_offset'], median_offset, 'Five-window median offset', atol=1e-8)
    require(stored['mapping_supported'] == usable, 'Five-window final gate')
    return usable


def main():
    require(not (HERE / 'SUMMARY.json').exists(), 'Preserve the existing audit result; run reproductions in a separate working copy')
    plan = read(BATCH / 'PLAN.json')
    freeze = read(BATCH / 'FOLLOWUP_FREEZE.json')
    source_hashes = {relative: sha(BASE / relative) for relative in freeze['source_hashes']}
    require(source_hashes == freeze['source_hashes'], 'Frozen source/code hash mismatch')
    events = rows(BATCH / 'SELECTED_EVENTS.csv')
    selected = rows(BATCH / 'SELECTED_EXPOSURES.csv')
    require(len(events) == 68 and len(selected) == 16, 'Selected 16/68 count')
    require([int(row['selection_index']) for row in selected] == list(range(3, 14)) + list(range(15, 20)), 'Selection order')
    require([event['review_id'] for event in events] == [f'V2E2-{i:04d}' for i in [*range(11, 59), *range(65, 85)]], 'Event selection sequence')
    prior = {row['candidate_id']: row for row in rows(BATCH / 'inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv')}
    require(all(prior[event['review_id']]['current_code'] == 'N' for event in events), 'Selection included previous review')
    manifest = read(BATCH / 'products/MANIFEST.json')
    require(manifest['charged_payload_bytes'] <= plan['acquisition_bounds']['payload_cap_bytes'] and manifest['reserved_bytes'] == 0, 'Payload bounds')
    products = manifest['products']
    require(len(products) <= 32 and len({(p['dp_id'], p['kind']) for p in products}) == len(products), 'Product identity count')
    source = {row['dp_id']: row for row in read(EXT / 'acquisition/DOWNLOAD_MANIFEST.json')}
    mapping = read(BATCH / 'NATIVE_MAPPING.json')
    require(mapping['freeze_sha256'] == sha(BATCH / 'FOLLOWUP_FREEZE.json') and mapping['plan_sha256'] == sha(BATCH / 'PLAN.json'), 'Mapping provenance')
    require([row['review_id'] for row in mapping['events']] == [row['review_id'] for row in events], 'Mapping event accounting')
    mapping_events = {row['review_id']: row for row in mapping['events']}
    require(len(mapping_events) == 68, 'Unique mapping event count')
    require(len(mapping['spectra']) == 16 and len({r['dp_id'] for r in mapping['spectra']}) == 16, 'Mapping exposure accounting')
    spectra = {row['dp_id']: row for row in mapping['spectra']}
    order_map = {(row['review_id'], row['order']): row for row in mapping['orders']}
    require(len(order_map) == len(mapping['orders']), 'Duplicate event/order mapping')
    five = read(BATCH / 'FIVE_WINDOW_MAPPING_AUDIT.json')
    five_map = {(row['dp_id'], row['order']): row for row in five['reference_audit']}
    require(len(five_map) == len(five['reference_audit']), 'Duplicate order reference')
    local = read(BATCH / 'LOCAL_TRACE_AUDIT.json')['orders']
    local_map = {(row['review_id'], row['order']): row for row in local}
    require(set(local_map) == set(order_map) and len(local) == len(order_map), 'Local audit coverage')
    report = []
    seen_orders = set()
    seen_five = set()
    cutouts = 0
    inputs_checked = 0
    global_regions = 0
    for selection in selected:
        dp = selection['dp_id']
        hits = [event for event in events if event['dp_id'] == dp]
        pair = [p for p in products if p['dp_id'] == dp and p['status'] == 'DOWNLOADED']
        if len(pair) != 2 or {p['kind'] for p in pair} != {'RAW', 'ANCILLARY'}:
            require(spectra[dp]['status'] == 'PRODUCT_PAIR_UNAVAILABLE', 'Unavailable exposure status')
            for hit in hits:
                event = mapping_events[hit['review_id']]
                require(event['status'] == 'NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE' and not event['mapping_supported'] and event['covering_orders'] == [], 'Unavailable event status')
            report.append(dict(dp_id=dp, events=len(hits), status='UNAVAILABLE_PAIR_RETAINED'))
            continue
        raw_product = next(p for p in pair if p['kind'] == 'RAW')
        anc_product = next(p for p in pair if p['kind'] == 'ANCILLARY')
        for product in pair:
            path = BASE / product['relative_path']
            require(sha(path) == product['sha256'] and path.stat().st_size == product['bytes'] == product['advertised_bytes'], 'Product bytes/hash')
            require(product['archive_id'] == (selection['raw_progenitor_id'] if product['kind'] == 'RAW' else selection['ancillary_archive_id']), 'Product archive identity')
            inputs_checked += 1
        science = source[dp]
        require(sha(BASE / science['relative_path']) == science['sha256'], 'Science source hash')
        inputs_checked += 1
        raw_bytes = subprocess.run(['gzip', '-cd', str(BASE / raw_product['relative_path'])], check=True, capture_output=True).stdout
        with fits.open(io.BytesIO(raw_bytes), memmap=False) as hdus:
            raw_header = hdus[0].header.copy()
            # Allocate independently and copy detector halves into their destination.
            raw = np.empty((4096, 4096), dtype=float)
            raw[:, :2048] = hdus[1].data[:, 50:2098]
            raw[:, 2048:] = hdus[2].data[:, 50:2098]
        del raw_bytes
        require(raw_header['ARCFILE'].removesuffix('.fits') == selection['raw_progenitor_id'], 'Raw ARCFILE')
        require(raw_header['DATE-OBS'] == science['primary_header']['DATE-OBS'], 'Raw DATE-OBS')
        require(raw_header['INSTRUME'] == 'HARPS', 'Raw instrument')
        with tarfile.open(BASE / anc_product['relative_path']) as archive:
            native_members = [member for member in archive.getmembers() if member.name.endswith('_e2ds_A.fits')]
            require(len(native_members) == 1, 'Ancillary native member uniqueness')
            member = native_members[0]
            require(Path(member.name).name == selection['raw_progenitor_id'] + '_e2ds_A.fits', 'Native parent filename')
            with fits.open(io.BytesIO(archive.extractfile(member).read()), memmap=False) as hdus:
                native, header = hdus[0].data.astype(float), hdus[0].header.copy()
        require(native.shape == (72, 4096), 'Native array shape')
        require(header['DATE-OBS'] == science['primary_header']['DATE-OBS'] and header['INSTRUME'] == 'HARPS', 'Native metadata')
        normalize = lambda value: re.sub('[^A-Z0-9]', '', str(value).upper())
        require(normalize(header['OBJECT']) == normalize(science['primary_header']['OBJECT']) != '', 'Native target')
        berv = float(header['ESO DRS BERV'])
        numeric(berv, science['primary_header']['HIERARCH ESO DRS BERV'], 'Native/science BERV', atol=1e-8)
        pixels = np.arange(4096)
        waves = np.array([polynomial(coefficients(header, 'ESO DRS CAL TH COEFF LL', 'ESO DRS CAL TH DEG LL', order), pixels) for order in range(72)])
        require(np.all(np.diff(waves, axis=1) > 0), 'Wavelength order monotonicity')
        candidates = []
        covers = {}
        for hit in hits:
            center = float(hit['fitted_center_bary_air_angstrom']) / (1 + berv / 299792.458)
            cover = [o for o in range(72) if waves[o, 0] < center < waves[o, -1]]
            covers[hit['review_id']] = (center, cover)
            for order in cover:
                pixel = int(np.argmin(np.abs(waves[order] - center)))
                candidates.append(dict(id=hit['review_id'], order=order, pixel=pixel))
        grid = read(BATCH / spectra[dp]['reference_grid'])
        orientation, global_ok = audit_global(raw, native, header, candidates, grid)
        global_regions += 24 * 8
        require(spectra[dp]['status'] == ('REGISTERED' if global_ok else 'MAPPING_UNCERTAIN'), 'Exposure global status')
        require(spectra[dp]['grid_best'] == grid['orientation_summaries'][0], 'Stored best orientation consistency')
        unique_orders = sorted({hit['order'] for hit in candidates})
        require(spectra[dp]['covering_order_count'] == len(unique_orders), 'Covering order count')
        five_gates = {}
        for order in unique_orders:
            key = (dp, order)
            require(key in five_map, 'Missing five-window covering order')
            seen_five.add(key)
            five_gates[order] = audit_five(raw, native, header, order, orientation, candidates, five_map[key])
        require(spectra[dp]['five_window_supported_orders'] == sum(five_gates.values()), 'Five-window exposure count')
        for hit in hits:
            id_ = hit['review_id']
            center, covering = covers[id_]
            event = mapping_events[id_]
            require(event['covering_orders'] == covering, 'All covering orders ' + id_)
            event_records = []
            for order in covering:
                key = (id_, order)
                require(key in order_map, 'Missing event/order ' + str(key))
                seen_orders.add(key)
                record = order_map[key]
                pixel = int(np.argmin(np.abs(waves[order] - center)))
                y = 4095 - pixel if orientation[0] else pixel
                col = float(trace(header, order, np.array(pixel), orientation))
                cx = round(col)
                require(record['native_pixel'] == pixel and record['raw_row'] == y, 'Event pixel mapping ' + str(key))
                numeric(record['raw_column'], col, 'Event trace column', atol=1e-8)
                numeric(record['topocentric_air_angstrom'], center, 'Event inverse BERV')
                numeric(record['native_nearest_wave_angstrom'], waves[order, pixel], 'Event nearest wave')
                require(record['grid_mapping_usable'] == global_ok and record['five_window_mapping_supported'] == five_gates[order], 'Order gates')
                local_record = local_map[key]
                local_usable = all(window['peak_offset'] is not None and abs(window['peak_offset']) <= 1 for window in local_record['windows'])
                require(record['local_mapping_usable'] == local_record['local_mapping_usable'] == local_usable, 'Preserved local gate')
                require(record['baseline_mapping_verified'] == bool(global_ok and local_usable), 'Baseline gate')
                full = 20 <= pixel < 4076 and 16 <= cx < 4080 and 15 <= y < 4081
                require(record['status'] == ('EXTRACTED' if full else 'EDGE_TRUNCATED'), 'Cutout edge status')
                require(record['mapping_verified'] == bool(full and global_ok and five_gates[order]), 'Final order mapping')
                if full:
                    path = BATCH / record['cutout']
                    require(sha(path) == record['cutout_sha256'], 'Cutout file hash')
                    with np.load(path) as arrays:
                        wider = np.array([[raw[y + dy, cx + dx] for dx in range(-16, 17)] for dy in range(-15, 16)])
                        baseline = np.array([[raw[y + dy, cx + dx] for dx in range(-12, 13)] for dy in range(-10, 11)])
                        bg = np.median(np.concatenate([wider[:10], wider[-10:]]), axis=0)
                        oldbg = np.median(np.concatenate([baseline[:5], baseline[-5:]]), axis=0)
                        expected = dict(raw_cutout=wider, raw_background=bg, raw_excess=wider - bg, baseline_raw_cutout=baseline, baseline_raw_background=oldbg, baseline_raw_excess=baseline - oldbg, native_flux=native[order, pixel - 20:pixel + 21])
                        require(set(arrays.files) == set(expected) | {'native_wave'}, 'Cutout array names')
                        for name, value in expected.items():
                            require(np.array_equal(arrays[name], value), 'Exact reconstruction ' + str(key) + ' ' + name)
                        require(np.array_equal(arrays['baseline_raw_cutout'], arrays['raw_cutout'][5:26, 4:29]), 'Nested baseline cutout')
                        numeric(arrays['native_wave'], waves[order, pixel - 20:pixel + 21], 'Independent native wavelengths', atol=1e-9)
                    cutouts += 1
                event_records.append(record)
            all_full = bool(event_records) and all(r['status'] == 'EXTRACTED' for r in event_records)
            supported = bool(all_full and all(r['mapping_verified'] for r in event_records))
            require(event['mapping_supported'] == supported, 'Every-order event mapping')
            require(event['baseline_all_orders_mapping_verified'] == bool(all_full and all(r['baseline_mapping_verified'] for r in event_records)), 'Every-order baseline mapping')
            require(event['edge_truncated_orders'] == [r['order'] for r in event_records if r['status'] == 'EDGE_TRUNCATED'], 'Event edge accounting')
            require(event['unsupported_orders'] == [r['order'] for r in event_records if not r['mapping_verified']], 'Event unsupported-order accounting')
            require(event['status'] == ('NATIVE_CONTEXT_EXTRACTED' if all_full else 'NO_USABLE_COMPLETE_CUTOUT_SET'), 'Event extraction status')
        report.append(dict(dp_id=dp, events=len(hits), event_orders=len(candidates), unique_orders=len(unique_orders), global_supported=global_ok, five_window_supported_orders=sum(five_gates.values()), status='PASS'))
        print(dp, 'PASS', len(hits), 'events', len(candidates), 'orders', flush=True)
        del raw, native
    require(seen_orders == set(order_map), 'Unexpected or missing event orders')
    require(seen_five == set(five_map), 'Unexpected or missing five-window orders')
    require(cutouts == mapping['extracted_orders'], 'Extracted order total')
    require({p.name for p in (BATCH / 'native').glob('*.npz')} == {Path(r['cutout']).name for r in mapping['orders'] if r['status'] == 'EXTRACTED'}, 'Native evidence file completeness')
    require({relative: sha(BASE / relative) for relative in freeze['source_hashes']} == source_hashes, 'Frozen source/code changed during audit')
    summary = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='PASS', selected_exposures=len(selected), selected_events=len(events), completed_exposures=sum(r['status'] == 'PASS' for r in report), unavailable_exposures=sum(r['status'] != 'PASS' for r in report), input_files_hash_verified=inputs_checked, reconstructed_event_order_cutouts=cutouts, event_order_records=len(order_map), unique_exposure_orders=len(five_map), independently_recomputed_global_region_orientations=global_regions, independently_recomputed_five_windows=5 * len(five_map), frozen_source_files=len(source_hashes), mapping_supported_events=sum(r['mapping_supported'] for r in mapping['events']), script_sha256=sha(__file__), source_hashes={str(p.relative_to(BATCH)):sha(p) for p in [BATCH/'NATIVE_MAPPING.json',BATCH/'FIVE_WINDOW_MAPPING_AUDIT.json',BATCH/'LOCAL_TRACE_AUDIT.json',BATCH/'products/MANIFEST.json',BATCH/'FOLLOWUP_FREEZE.json']}, coverage='Independent source-product identity/hash checks, raw join, direct-power wavelength/trace polynomials, every cutout/background/native profile, all global grid orientations and every five-window reference with centered-dot-product correlations. No project analysis modules imported. Preserved local check is audited for coverage and gate arithmetic only, not full numerical reconstruction. NumPy/SciPy/Astropy primitives shared. No visual/origin adjudication.', exposures=report, runtime={'python':sys.version.split()[0],'numpy':np.__version__})
    (HERE / 'SUMMARY.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    (HERE / 'README.md').write_text('# Independent batch02 numerical audit\n\nStatus: **PASS**. See `SUMMARY.json` for exact coverage and source hashes.\n\nAll available input products and selected science files were verified by hash and identity. Every saved event/order array was reconstructed from original products; raw counts, backgrounds, excess and native flux were compared exactly. Wavelengths and detector traces used independently implemented direct-power polynomials with explicit numerical tolerances. All global-grid orientation correlations/profiles and all five-window reference tests were recomputed without importing the production analysis modules.\n\nThe preserved two-sided local check was checked for coverage and gate arithmetic only; its full numerical reconstruction is not claimed. Shared numerical dependencies remain NumPy/SciPy/Astropy. This audit verifies extraction and accounting, not physical origin or visual classifications.\n\nRun `python3 independent_audit/check_batch02.py` from the batch directory in a separate restored working copy without an existing audit summary. Original source products are required; preserve the published audit result.\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['exposures','source_hashes','coverage']}, indent=2))


if __name__ == '__main__':
    main()
