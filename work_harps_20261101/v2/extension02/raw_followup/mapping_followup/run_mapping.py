"""Posthoc fixed mapping43 reference method for nine baseline-limited records.

No detector, orientation, coordinate, baseline disposition or source is changed.
All writes are restricted to this new mapping_followup directory.
"""
from pathlib import Path
import collections
import csv
import datetime
import gc
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
OLD = OUT.parent
EXT = OLD.parent
BASE = EXT.parents[1]
EXPECTED_PLAN_SHA256 = 'd0f6934a5c5bde5850a230b24b340c582024ce5b0cc61570d8526924c4d67b7a'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


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
    path = OUT / name
    require(path.resolve().is_relative_to(OUT.resolve()), 'Output outside followup')
    require(not path.exists(), 'Refusing output overwrite: ' + name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def verify_inputs():
    require(sha(OUT / 'PLAN.json') == EXPECTED_PLAN_SHA256, 'Fixed posthoc plan changed')
    plan = read(OUT / 'PLAN.json')
    require(sha(BASE / plan['prior_method_plan']) == plan['prior_method_plan_sha256'], 'Prior mapping43 plan changed')
    require(plan['reference_windows_half_open'] == [[128, 768], [896, 1536], [1664, 2304], [2432, 3072], [3200, 3968]], 'Fixed reference windows changed')
    require(plan['candidate_exclusion_half_width_pixels'] == 80 and plan['minimum_samples_per_reference_window'] == 200, 'Fixed reference exclusions/sample rule changed')
    for relative, digest in plan['input_hashes'].items():
        require(sha(BASE / relative) == digest, 'Plan input changed: ' + relative)
    for freeze_path in (EXT / 'FREEZE.json', OLD / 'FOLLOWUP_FREEZE.json'):
        for relative, digest in read(freeze_path)['source_hashes'].items():
            require(sha(BASE / relative) == digest, 'Frozen source changed: ' + relative)
    return plan


# These arithmetic functions reproduce mapping43 exactly, including sample order,
# interpolation, high-pass filtering and the fixed peak interpolation convention.
def poly(header, prefix, degree, order, x):
    return np.polynomial.polynomial.polyval(x, [header[prefix + str(order * (degree + 1) + j)] for j in range(degree + 1)])


def trace(header, order, x, flips):
    argument = 4095 - x if flips['argument_flip'] else x
    column = poly(header, 'ESO DRS CAL LOC CTR', int(header['ESO DRS CAL LOC DEG CTR']), order, argument)
    return 4095 - column if flips['column_flip'] else column


def interp(raw, yy, columns):
    low = np.floor(columns).astype(int)
    fraction = columns - low
    return raw[yy, low] * (1 - fraction) + raw[yy, low + 1] * fraction


def hp(array):
    return array - median_filter(array, size=31, mode='nearest')


def peak(profile):
    k = int(np.argmax(profile))
    position = float(k - 8)
    if 0 < k < 16:
        a, b, c = profile[k - 1:k + 2]
        denominator = a - 2 * b + c
        if denominator:
            position += float(.5 * (a - c) / denominator)
    return position


def reference_order(raw, native, header, order, flips, candidates, windows):
    results = []
    for lo, hi in windows:
        x = np.arange(lo, hi)
        yy = 4095 - x if flips['row_flip'] else x
        columns = trace(header, order, x, flips)
        bounds = (columns >= 9) & (columns < 4086)
        mask = bounds.copy()
        excluded = []
        for candidate in candidates:
            if candidate['order'] == order:
                near = abs(x - candidate['native_pixel']) <= 80
                if near.any():
                    excluded.append(candidate['review_id'])
                mask &= ~near
        result = dict(pixel_interval_half_open=[lo, hi], samples=int(mask.sum()), excluded_ids=excluded, correlation=None, peak_offset=None, profile=None)
        if mask.sum() >= 200 and bounds.all():
            values = np.stack([interp(raw, yy, columns + offset) for offset in range(-8, 9)])
            profile = np.median(values[:, mask], axis=1)
            profile -= np.median(profile[np.r_[0:2, 15:17]])
            correlation = float(np.corrcoef(hp(native[order, x])[mask], hp(values[5:12].sum(axis=0))[mask])[0, 1])
            result.update(correlation=correlation if np.isfinite(correlation) else None, peak_offset=peak(profile), profile=profile.tolist(), peak_above_outer_baseline=float(profile.max()))
        results.append(result)
    good = [result for result in results if result['correlation'] is not None]
    correlation = float(np.median([result['correlation'] for result in good])) if good else None
    offset = float(np.median([abs(result['peak_offset']) for result in good])) if good else None
    within_one = sum(abs(result['peak_offset']) <= 1 for result in good)
    usable = bool(len(good) >= 3 and correlation > .8 and offset <= .75 and within_one >= 3)
    return dict(order=order, valid_reference_windows=len(good), median_correlation=correlation, median_abs_peak_offset=offset, windows_within_one_pixel=within_one, mapping_supported=usable, windows=results)


def load_exposure(dp, products, mapping, science):
    pair = {record['kind']: record for record in products if record['dp_id'] == dp}
    require(set(pair) == {'RAW', 'ANCILLARY'}, 'Exposure product pair missing')
    rr, tr = pair['RAW'], pair['ANCILLARY']
    for product in (rr, tr):
        require(product['status'] == 'DOWNLOADED' and sha(BASE / product['relative_path']) == product['sha256'], 'Source product status/hash mismatch')
    with fits.open(io.BytesIO(subprocess.run(['gzip', '-cd', str(BASE / rr['relative_path'])], check=True, capture_output=True).stdout), memmap=False) as hdus:
        raw = np.hstack([hdus[1].data[:, 50:2098], hdus[2].data[:, 50:2098]]).astype(float)
        raw_header = hdus[0].header.copy()
    with tarfile.open(BASE / tr['relative_path']) as archive:
        members = [member for member in archive if member.name.endswith('_e2ds_A.fits')]
        require(len(members) == 1 and Path(members[0].name).name == rr['raw_id'] + '_e2ds_A.fits', 'Native parent member identity')
        with fits.open(io.BytesIO(archive.extractfile(members[0]).read()), memmap=False) as hdus:
            native = hdus[0].data.astype(float)
            header = hdus[0].header.copy()
    require(raw.shape == (4096, 4096) and native.shape == (72, 4096), 'Raw/native dimensions')
    require(raw_header['ARCFILE'].removesuffix('.fits') == rr['raw_id'] == tr['raw_id'], 'Raw parent identity')
    require(raw_header['DATE-OBS'] == header['DATE-OBS'] == science[dp]['primary_header']['DATE-OBS'], 'Raw/native/science date identity')
    require(raw_header['INSTRUME'] == header['INSTRUME'] == 'HARPS', 'Raw/native instrument identity')
    old_spectrum = next(record for record in mapping['spectra'] if record['dp_id'] == dp)
    require(old_spectrum['status'] == 'REGISTERED', 'Baseline global mapping was not registered')
    require(abs(header['ESO DRS BERV'] - old_spectrum['berv_km_s']) < 1e-8 and abs(header['ESO DRS BERV'] - science[dp]['primary_header']['HIERARCH ESO DRS BERV']) < 1e-8, 'Native/science BERV mismatch')
    return raw, native, header, raw_header, old_spectrum, rr, tr


def main():
    require(not (OUT / 'MAPPING_AUDIT.json').exists(), 'Mapping followup already completed')
    plan = verify_inputs()
    hits = rows(OUT / 'SELECTED_EVENTS.csv')
    all_events = rows(OLD / 'SELECTED_EVENTS.csv')
    mapping = read(OLD / 'NATIVE_MAPPING.json')
    products = read(OLD / 'products/MANIFEST.json')['products']
    science = {record['dp_id']: record for record in read(EXT / 'acquisition/DOWNLOAD_MANIFEST.json')}
    require([hit['review_id'] for hit in hits] == plan['review_ids'] and len(hits) == 9, 'Selected posthoc record order mismatch')
    require(len(all_events) == 65 and len(mapping['events']) == 65 and len(mapping['orders']) == 86, 'Baseline exclusion population incomplete')
    require(hits == [event for event in all_events if event['review_id'] in set(plan['review_ids'])], 'Followup records differ from original selection')
    require(len({hit['dp_id'] for hit in hits}) == plan['exposures'] == 4, 'Posthoc exposure count')
    local = read(OLD / 'LOCAL_TRACE_AUDIT.json')['orders']
    for reason in plan['old_local_failure_reasons']:
        failed = [record for record in local if record['review_id'] == reason['review_id'] and not record['local_mapping_usable']]
        require([record['order'] for record in failed] == reason['failed_orders'], 'Baseline failed orders differ')
        require(all(any(window['samples'] < 60 for window in record['windows']) for record in failed), 'Baseline failure is not insufficient local samples')
        require(not any(window['peak_offset'] is not None and abs(window['peak_offset']) > 1 for record in failed for window in record['windows']), 'Unexpected measured local displacement')
    preserved_paths = {OUT / 'PLAN.json', OUT / 'SELECTED_EVENTS.csv'}
    for old in mapping['orders']:
        if old['review_id'] in plan['review_ids'] and old['status'] == 'EXTRACTED':
            preserved_paths.add(OLD / old['cutout'])
    dp_ids = {hit['dp_id'] for hit in hits}
    for product in products:
        if product['dp_id'] in dp_ids:
            preserved_paths.add(BASE / product['relative_path'])
    preserved = {str(path.relative_to(BASE)): sha(path) for path in sorted(preserved_paths)}
    (OUT / 'native').mkdir(exist_ok=True)
    (OUT / 'reference').mkdir(exist_ok=True)
    require(not list((OUT / 'native').glob('*.npz')), 'Refusing to overwrite an earlier partial extraction')
    spectra, orders, references = [], [], []
    for dp in dict.fromkeys(hit['dp_id'] for hit in hits):
        print('BEGIN ' + dp, flush=True)
        raw, native, header, raw_header, old_spectrum, rr, tr = load_exposure(dp, products, mapping, science)
        flips = old_spectrum['grid_best']
        dp_hits = [hit for hit in hits if hit['dp_id'] == dp]
        dp_hit_ids = {hit['review_id'] for hit in dp_hits}
        # All 65 baseline records in their original order contribute exclusions,
        # including V1/V2 coincidences; only this exposure's covering orders apply.
        candidates = [record for record in mapping['orders'] if record['dp_id'] == dp]
        needed = sorted({record['order'] for record in candidates if record['review_id'] in dp_hit_ids})
        audit = {}
        for order in needed:
            audit[order] = dict(dp_id=dp, **reference_order(raw, native, header, order, flips, candidates, plan['reference_windows_half_open']))
            references.append(audit[order])
        write('reference/' + dp.replace(':', '_') + '.json', dict(dp_id=dp, orientation=flips, reference_audit=list(audit.values()), excluded_candidate_population='All65 selected V1/V2 records across their covering orders; restricted to this exposure for geometry.'))
        for hit in dp_hits:
            for old in [record for record in candidates if record['review_id'] == hit['review_id']]:
                order, k = old['order'], old['native_pixel']
                cx = float(trace(header, order, np.array(k), flips))
                cy = int(4095 - k if flips['row_flip'] else k)
                icx = round(cx)
                record = dict(review_id=hit['review_id'], detector=hit['detector'], dp_id=dp, target=hit['target'], order=order, native_pixel=k, raw_row=cy, raw_column=cx, previous_status=old['status'], previous_mapping_verified=old.get('mapping_verified'), reference_mapping_supported=audit[order]['mapping_supported'])
                if not (20 <= k < 4076 and 16 <= icx < 4080 and 15 <= cy < 4081):
                    record['status'] = 'EDGE_TRUNCATED'
                    orders.append(record)
                    continue
                cutout = raw[cy - 15:cy + 16, icx - 16:icx + 17].copy()
                background = np.median(cutout[np.r_[0:10, 21:31]], axis=0)
                excess = cutout - background[None, :]
                pixels = np.arange(k - 20, k + 21)
                wave = poly(header, 'ESO DRS CAL TH COEFF LL', int(header['ESO DRS CAL TH DEG LL']), order, pixels)
                center = float(hit['fitted_center_bary_air_angstrom']) / (1 + float(header['ESO DRS BERV']) / 299792.458)
                path = OUT / 'native' / (hit['review_id'] + '_o' + str(order).zfill(2) + '.npz')
                require(not path.exists(), 'Wider cutout already exists')
                np.savez_compressed(path, raw_cutout=cutout, raw_background=background, raw_excess=excess, native_wave=wave, native_flux=native[order, pixels])
                if old['status'] == 'EXTRACTED':
                    with np.load(OLD / old['cutout'], allow_pickle=False) as original:
                        require(np.array_equal(original['raw_cutout'], cutout[5:26, 4:29]), 'Original raw pixels not preserved')
                        require(np.array_equal(original['native_flux'], native[order, pixels]) and np.array_equal(original['native_wave'], wave), 'Original native samples not preserved')
                    require(cx == old['raw_column'] and cy == old['raw_row'], 'Original coordinates changed')
                record.update(status='EXTRACTED', cutout=str(path.relative_to(OUT)), topocentric_air_angstrom=center, native_side_median=float(np.median(native[order, pixels][np.r_[0:8, 33:41]])))
                orders.append(record)
        spectra.append(dict(dp_id=dp, date_obs=raw_header['DATE-OBS'], berv_km_s=float(header['ESO DRS BERV']), orientation=flips, input_raw_sha256=rr['sha256'], input_ancillary_sha256=tr['sha256'], orders=needed))
        print(json.dumps(dict(dp_id=dp, unique_orders=len(needed), supported=sum(record['mapping_supported'] for record in audit.values()))), flush=True)
        del raw, native
        gc.collect()
    verify_inputs()
    require(all(sha(BASE / relative) == digest for relative, digest in preserved.items()), 'Original source/cutout changed')
    events = []
    for hit in hits:
        related = [record for record in orders if record['review_id'] == hit['review_id']]
        full = [record for record in related if record['status'] == 'EXTRACTED']
        usable = bool(full and all(record['reference_mapping_supported'] for record in full))
        events.append(dict(review_id=hit['review_id'], detector=hit['detector'], mapping_supported=usable, covering_orders=[record['order'] for record in related], edge_truncated_orders=[record['order'] for record in related if record['status'] == 'EDGE_TRUNCATED'], unsupported_extracted_orders=[record['order'] for record in full if not record['reference_mapping_supported']], original_origin_status='INSUFFICIENT_RAW_MAPPING', origin_status='UNREVIEWED'))
    require(len(orders) == 16 and len(references) == 13, 'Covering order accounting differs')
    record = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), plan_sha256=sha(OUT / 'PLAN.json'), script_sha256=sha(Path(__file__)), selected_events_sha256=sha(OUT / 'SELECTED_EVENTS.csv'), spectra=spectra, reference_audit=references, orders=orders, events=events, original_hashes_unchanged=True, coordinates_changed=False, candidate_exclusion_population_records=65, candidate_exclusion_population_covering_orders=86, original_local_failures=dict(insufficient_samples=9, measured_displacement=0))
    write('MAPPING_AUDIT.json', record)
    write('PRESERVED_INPUT_HASHES.json', preserved)
    summary = dict(status='MAPPING_ONLY_POSTHOC_FOLLOWUP_COMPLETE', created_utc=record['created_utc'], exposures=4, source_products_verified=8, records=9, detector_counts=dict(collections.Counter(hit['detector'] for hit in hits)), covering_order_records=16, unique_exposure_orders=13, supported_exposure_orders=sum(ref['mapping_supported'] for ref in references), supported_records=sum(event['mapping_supported'] for event in events), mapping_limited_records=[event['review_id'] for event in events if not event['mapping_supported']], original_failures_insufficient_local_samples=9, original_failures_measured_offset=0, all_original_coordinates_and_hashes_preserved=True, new_raw_shape=[31, 33], original_raw_shape_preserved=[21, 25], original_native_samples_preserved=41, plan_sha256=record['plan_sha256'], mapping_audit_sha256=sha(OUT / 'MAPPING_AUDIT.json'), new_network_calls=0, original_catalogs_or_dispositions_changed=False, origin_assignments=0, interpretation='Broader fixed candidate-excluded reference support is geometry evidence only. This posthoc nine-record subset is not homogeneous reprocessing of all65 or336. Baseline statuses remain preserved; no origin inference or detector tuning.')
    write('SUMMARY.json', summary)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
