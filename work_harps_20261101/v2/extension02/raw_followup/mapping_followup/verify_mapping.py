"""Fresh-process reconstruction of all four exposures; no import of run_mapping.

Reopens original products, recomputes all thirteen broader-reference audits and
all sixteen new cutouts, and verifies unchanged original samples/coordinates.
Only a new VERIFICATION.json is written in this followup directory.
"""
from pathlib import Path
import csv
import datetime
import gc
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import time
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
OLD = OUT.parent
EXT = OLD.parent
BASE = EXT.parents[1]
PLAN_SHA = 'd0f6934a5c5bde5850a230b24b340c582024ce5b0cc61570d8526924c4d67b7a'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def polynomial(header, prefix, order, degree, pixels):
    coefficients = [header[prefix + str(order * (degree + 1) + i)] for i in range(degree + 1)]
    return np.polynomial.polynomial.polyval(pixels, coefficients)


def columns(header, order, pixels, orientation):
    argument = 4095 - pixels if orientation['argument_flip'] else pixels
    result = polynomial(header, 'ESO DRS CAL LOC CTR', order, int(header['ESO DRS CAL LOC DEG CTR']), argument)
    return 4095 - result if orientation['column_flip'] else result


def reconstruct_reference(raw, native, header, order, orientation, candidates):
    windows = []
    for lower, upper in ((128, 768), (896, 1536), (1664, 2304), (2432, 3072), (3200, 3968)):
        pixels = np.arange(lower, upper)
        yy = 4095 - pixels if orientation['row_flip'] else pixels
        center = columns(header, order, pixels, orientation)
        bounded = (center >= 9) & (center < 4086)
        valid = bounded.copy()
        excluded = []
        for candidate in candidates:
            if candidate['order'] == order:
                near = abs(pixels - candidate['native_pixel']) <= 80
                if near.any():
                    excluded.append(candidate['review_id'])
                valid &= ~near
        window = dict(pixel_interval_half_open=[lower, upper], samples=int(valid.sum()), excluded_ids=excluded, correlation=None, peak_offset=None, profile=None)
        if valid.sum() >= 200 and bounded.all():
            samples = []
            for offset in range(-8, 9):
                floating = center + offset
                integer = np.floor(floating).astype(int)
                fraction = floating - integer
                samples.append(raw[yy, integer] * (1 - fraction) + raw[yy, integer + 1] * fraction)
            samples = np.stack(samples)
            profile = np.median(samples[:, valid], axis=1)
            profile -= np.median(profile[np.r_[0:2, 15:17]])
            aperture = samples[5:12].sum(axis=0)
            spectral = native[order, pixels]
            correlation = float(np.corrcoef((spectral - median_filter(spectral, size=31, mode='nearest'))[valid], (aperture - median_filter(aperture, size=31, mode='nearest'))[valid])[0, 1])
            location = int(np.argmax(profile))
            offset = float(location - 8)
            if 0 < location < 16:
                a, b, c = profile[location - 1:location + 2]
                denominator = a - 2 * b + c
                if denominator:
                    offset += float(.5 * (a - c) / denominator)
            window.update(correlation=correlation if np.isfinite(correlation) else None, peak_offset=offset, profile=profile.tolist(), peak_above_outer_baseline=float(profile.max()))
        windows.append(window)
    usable = [window for window in windows if window['correlation'] is not None]
    correlation = float(np.median([window['correlation'] for window in usable])) if usable else None
    offset = float(np.median([abs(window['peak_offset']) for window in usable])) if usable else None
    within_one = sum(abs(window['peak_offset']) <= 1 for window in usable)
    return dict(order=order, valid_reference_windows=len(usable), median_correlation=correlation, median_abs_peak_offset=offset, windows_within_one_pixel=within_one, mapping_supported=bool(len(usable) >= 3 and correlation > .8 and offset <= .75 and within_one >= 3), windows=windows)


def main():
    started = time.monotonic()
    require(not (OUT / 'VERIFICATION.json').exists(), 'Verification already exists')
    require(sha(OUT / 'PLAN.json') == PLAN_SHA, 'Fixed followup plan changed')
    plan = read(OUT / 'PLAN.json')
    audit = read(OUT / 'MAPPING_AUDIT.json')
    baseline = read(OLD / 'NATIVE_MAPPING.json')
    products = read(OLD / 'products/MANIFEST.json')['products']
    selected = rows(OUT / 'SELECTED_EVENTS.csv')
    all_events = rows(OLD / 'SELECTED_EVENTS.csv')
    preserved = read(OUT / 'PRESERVED_INPUT_HASHES.json')
    require(audit['plan_sha256'] == PLAN_SHA and audit['script_sha256'] == sha(OUT / 'run_mapping.py'), 'Audit code/plan provenance mismatch')
    require(audit['selected_events_sha256'] == sha(OUT / 'SELECTED_EVENTS.csv'), 'Audit selection hash mismatch')
    require([event['review_id'] for event in selected] == plan['review_ids'], 'Selected record membership/order')
    require(len(all_events) == 65 and audit['candidate_exclusion_population_records'] == 65, 'All-candidate exclusion population')
    protect = dict(preserved)
    protect.update(plan['input_hashes'])
    for path in [OUT / 'MAPPING_AUDIT.json', OUT / 'SUMMARY.json', *sorted((OUT / 'native').glob('*.npz')), *sorted((OUT / 'reference').glob('*.json'))]:
        protect[str(path.relative_to(BASE))] = sha(path)
    for relative, digest in protect.items():
        require(sha(BASE / relative) == digest, 'Protected input hash mismatch')
    by_order = {(record['review_id'], record['order']): record for record in audit['orders']}
    require(len(by_order) == len(audit['orders']) == 16, 'Covering-order accounting')
    old_by_order = {(record['review_id'], record['order']): record for record in baseline['orders']}
    by_reference = {(record['dp_id'], record['order']): record for record in audit['reference_audit']}
    require(len(by_reference) == len(audit['reference_audit']) == 13, 'Reference accounting')
    exposure_records = []
    all_keys, reconstructed_keys, reference_keys = set(), set(), set()
    for dp in dict.fromkeys(event['dp_id'] for event in selected):
        print('VERIFY_ALL_ORDERS ' + dp, flush=True)
        pair = {record['kind']: record for record in products if record['dp_id'] == dp}
        require(set(pair) == {'RAW', 'ANCILLARY'}, 'Product pair missing')
        for product in pair.values():
            require(product['status'] == 'DOWNLOADED' and sha(BASE / product['relative_path']) == product['sha256'], 'Verified product hash/status')
        with fits.open(io.BytesIO(subprocess.run(['gzip', '-cd', str(BASE / pair['RAW']['relative_path'])], capture_output=True, check=True).stdout), memmap=False) as hdus:
            raw_header = hdus[0].header.copy()
            raw = np.hstack((hdus[1].data[:, 50:2098], hdus[2].data[:, 50:2098])).astype(float)
        with tarfile.open(BASE / pair['ANCILLARY']['relative_path']) as archive:
            members = [member for member in archive if member.name.endswith('_e2ds_A.fits')]
            require(len(members) == 1 and Path(members[0].name).name == pair['RAW']['raw_id'] + '_e2ds_A.fits', 'TAR parent identity')
            with fits.open(io.BytesIO(archive.extractfile(members[0]).read()), memmap=False) as hdus:
                header = hdus[0].header.copy()
                native = hdus[0].data.astype(float)
        require(raw_header['ARCFILE'].removesuffix('.fits') == pair['RAW']['raw_id'] == pair['ANCILLARY']['raw_id'], 'Raw archive identity')
        require(raw_header['DATE-OBS'] == header['DATE-OBS'] == pair['RAW']['source_date_obs'], 'Raw/native identity date')
        require(raw.shape == (4096, 4096) and native.shape == (72, 4096), 'Source dimensions')
        old_spectrum = next(record for record in baseline['spectra'] if record['dp_id'] == dp)
        new_spectrum = next(record for record in audit['spectra'] if record['dp_id'] == dp)
        orientation = old_spectrum['grid_best']
        require(new_spectrum['orientation'] == orientation, 'Orientation changed')
        berv = float(header['ESO DRS BERV'])
        require(new_spectrum['berv_km_s'] == old_spectrum['berv_km_s'] == berv, 'Native BERV mismatch')
        wave_degree = int(header['ESO DRS CAL TH DEG LL'])
        waves = np.array([polynomial(header, 'ESO DRS CAL TH COEFF LL', order, wave_degree, np.arange(4096)) for order in range(72)])
        require(np.isfinite(waves).all() and (np.diff(waves, axis=1) > 0).all(), 'Finite increasing wavelength precondition')
        rederived = {}
        for event in [event for event in all_events if event['dp_id'] == dp]:
            center = float(event['fitted_center_bary_air_angstrom']) / (1 + berv / 299792.458)
            for order in np.flatnonzero((waves[:, 0] < center) & (waves[:, -1] > center)).tolist():
                rederived[(event['review_id'], order)] = int(np.argmin(abs(waves[order] - center)))
        candidates = [record for record in baseline['orders'] if record['dp_id'] == dp]
        require(rederived == {(record['review_id'], record['order']): record['native_pixel'] for record in candidates}, 'Reconstructed all-candidate positions/covering orders differ')
        needed = new_spectrum['orders']
        for order in needed:
            recreated = dict(dp_id=dp, **reconstruct_reference(raw, native, header, order, orientation, candidates))
            require(recreated == by_reference[(dp, order)], 'Full broader reference mismatch')
            reference_keys.add((dp, order))
        saved_reference = read(OUT / 'reference' / (dp.replace(':', '_') + '.json'))
        require(saved_reference['orientation'] == orientation and saved_reference['reference_audit'] == [by_reference[(dp, order)] for order in needed], 'Per-exposure reference copy mismatch')
        count = 0
        for event in [event for event in selected if event['dp_id'] == dp]:
            review_id = event['review_id']
            for key, k in rederived.items():
                if key[0] != review_id:
                    continue
                order = key[1]
                all_keys.add(key)
                saved = by_order[key]
                old = old_by_order[key]
                cy = 4095 - k if orientation['row_flip'] else k
                cx = float(columns(header, order, np.array(k), orientation))
                icx = round(cx)
                require(saved['native_pixel'] == old['native_pixel'] == k and saved['raw_column'] == old['raw_column'] == cx and saved['raw_row'] == old['raw_row'] == cy, 'Coordinate preservation mismatch')
                full = 20 <= k < 4076 and 16 <= icx < 4080 and 15 <= cy < 4081
                require(saved['status'] == ('EXTRACTED' if full else 'EDGE_TRUNCATED'), 'Wide-edge support mismatch')
                require(saved['reference_mapping_supported'] == by_reference[(dp, order)]['mapping_supported'], 'Reference flag copy mismatch')
                if not full:
                    continue
                cutout = raw[cy - 15:cy + 16, icx - 16:icx + 17]
                background = np.median(cutout[np.r_[0:10, 21:31]], axis=0)
                expected = dict(raw_cutout=cutout, raw_background=background, raw_excess=cutout - background[None, :], native_wave=waves[order, k - 20:k + 21], native_flux=native[order, k - 20:k + 21])
                with np.load(OUT / saved['cutout'], allow_pickle=False) as bundle:
                    require(set(bundle.files) == set(expected), 'Saved NPZ field set')
                    for name, array in expected.items():
                        require(np.array_equal(bundle[name], array), 'Full independent NPZ reconstruction mismatch: ' + name)
                with np.load(OLD / old['cutout'], allow_pickle=False) as original:
                    require(np.array_equal(original['raw_cutout'], cutout[5:26, 4:29]), 'Original 21x25 raw window not preserved')
                    require(np.array_equal(original['native_wave'], expected['native_wave']) and np.array_equal(original['native_flux'], expected['native_flux']), 'Original 41-point native arrays not preserved')
                reconstructed_keys.add(key)
                count += 1
        exposure_records.append(dict(dp_id=dp, source_products_reopened=2, unique_reference_orders_exact=len(needed), full_cutouts_all_five_arrays_exact=count, all_original_raw_native_samples_and_coordinates_exact=True, all_candidate_covering_orders_independently_rederived=len(rederived)))
        del raw, native, waves
        gc.collect()
    require(all_keys == set(by_order) and reference_keys == set(by_reference), 'Independent verification coverage incomplete')
    require(len(exposure_records) == 4 and len(reconstructed_keys) == 16, 'All-four/all-sixteen reconstruction incomplete')
    require(len(list((OUT / 'native').glob('*.npz'))) == 16, 'Unexpected NPZ inventory')
    for event in audit['events']:
        related = [record for record in audit['orders'] if record['review_id'] == event['review_id']]
        full = [record for record in related if record['status'] == 'EXTRACTED']
        require(event['mapping_supported'] == bool(full and all(record['reference_mapping_supported'] for record in full)), 'Event support aggregation mismatch')
        require(event['origin_status'] == 'UNREVIEWED', 'Unexpected automatic origin assignment')
    summary = read(OUT / 'SUMMARY.json')
    require(summary['supported_records'] == sum(event['mapping_supported'] for event in audit['events']) == 8 and summary['supported_exposure_orders'] == 12, 'Summary support totals')
    require(summary['mapping_limited_records'] == ['V2E2-0225'], 'Remaining mapping limitation')
    for relative, digest in protect.items():
        require(sha(BASE / relative) == digest, 'Protected input/output changed during reconstruction')
    require(sha(OUT / 'PLAN.json') == PLAN_SHA, 'Plan changed during reconstruction')
    for freeze_file in (EXT / 'FREEZE.json', OLD / 'FOLLOWUP_FREEZE.json'):
        for relative, digest in read(freeze_file)['source_hashes'].items():
            require(sha(BASE / relative) == digest, 'Original/followup frozen source changed')
    result = dict(status='PASS_EXACT_FRESH_PROCESS_RECONSTRUCTION_ALL_FOUR_EXPOSURES', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), verification_code_sha256=sha(Path(__file__)), mapping_code_sha256=sha(OUT / 'run_mapping.py'), plan_sha256=PLAN_SHA, mapping_audit_sha256=sha(OUT / 'MAPPING_AUDIT.json'), source_products_reopened=8, unique_reference_orders_exactly_reconstructed=13, individual_reference_windows_exactly_reconstructed=65, wider_npz_all_five_arrays_exactly_reconstructed=16, original_raw_native_samples_and_coordinates_preserved=16, all_65_baseline_candidates_used_for_exclusion=True, exposures=exposure_records, protected_file_hashes_unchanged=len(protect), network_calls=0, origin_assignments=0, elapsed_seconds=time.monotonic() - started, limitations=['Separate reconstruction code and process reproduce the same frozen geometry method; not an independent detector or physical-origin test.', 'Posthoc mapping only on nine previously limited records, not a homogeneous reapplication to all65 or336.', 'One event remains mapping-limited because a covering order fails the fixed spectral-reference correlation threshold; centered trace profiles do not override that gate.', 'The previously disclosed raw-acquisition partial-prefix provenance anomaly remains unresolved; only verified final product paths were used.'])
    (OUT / 'VERIFICATION.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
