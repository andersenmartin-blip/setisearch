"""Frozen batch02 native/raw extraction with prospective full-order trace audit.

The original 24-region global grid fixes orientation. The inherited local
candidate-excluded check is preserved descriptively. Every covering order also
receives the inherited five-window check. No coordinate adjustment or origin
classification is performed. Source arrays are opened only by main().
"""
import gc
import io
import subprocess
import tarfile

import numpy as np
from astropy.io import fits

from common import BASE, EXT, OUT, csvrows, dump, now, read, require, sha, verify_freeze, verify_native_identity, verify_plan
from registration import evaluate_reference_grid
from local_registration import evaluate_local_trace
from mapping_quality import METHOD_CONFIGURATION, poly, reference_order, verify_method_configuration


def context(header):
    return {key: value for key, value in header.items()
            if any(token in key for token in ['DPR', 'INS OPTI', 'LAMP', 'DRIFT', 'CAL TH FILE', 'CAL LOC FILE'])
            and isinstance(value, (str, int, float, bool))}


def main():
    plan = verify_plan()
    verify_method_configuration(plan)
    freeze = verify_freeze()
    require(not (OUT / 'NATIVE_MAPPING.json').exists(), 'Existing extraction must not be silently replaced')
    require(not list((OUT / 'native').glob('*.npz')), 'Partial extraction must not be silently replaced')
    require(not list((OUT / 'reference').glob('*.json')), 'Partial reference audit must not be silently replaced')
    events = csvrows(OUT / 'SELECTED_EVENTS.csv')
    selected = csvrows(OUT / 'SELECTED_EXPOSURES.csv')
    products = read('products/MANIFEST.json')['products']
    import json
    source = {record['dp_id']: record for record in json.loads((EXT / 'acquisition/DOWNLOAD_MANIFEST.json').read_text())}
    require(len({event['review_id'] for event in events}) == len(events), 'Duplicate selected event')
    require(set(event['dp_id'] for event in events) == set(record['dp_id'] for record in selected), 'Exposure/event selection mismatch')
    native_dir = OUT / 'native'
    native_dir.mkdir(exist_ok=True)
    (OUT / 'reference').mkdir(exist_ok=True)
    spectra, orders, local_audit, fiber_inventory, event_summary, reference_audit = [], [], [], [], [], []
    for selection in selected:
        dp = selection['dp_id']
        hits = [event for event in events if event['dp_id'] == dp]
        pair = [record for record in products if record['dp_id'] == dp and record['status'] == 'DOWNLOADED']
        if len(pair) != 2 or {record['kind'] for record in pair} != {'RAW', 'ANCILLARY'}:
            spectra.append(dict(dp_id=dp, status='PRODUCT_PAIR_UNAVAILABLE'))
            event_summary.extend(dict(review_id=hit['review_id'], detector=hit['detector'], dp_id=dp,
                                      covering_orders=[], mapping_supported=False,
                                      status='NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE', origin_status='NOT_RAW_REVIEWED') for hit in hits)
            continue
        raw_product = next(record for record in pair if record['kind'] == 'RAW')
        ancillary = next(record for record in pair if record['kind'] == 'ANCILLARY')
        for product in pair:
            require(sha(BASE / product['relative_path']) == product['sha256'], 'Product hash mismatch')
        require(sha(BASE / source[dp]['relative_path']) == source[dp]['sha256'], 'Source spectrum hash mismatch')
        compressed = subprocess.run(['gzip', '-cd', str(BASE / raw_product['relative_path'])], check=True, capture_output=True).stdout
        with fits.open(io.BytesIO(compressed), memmap=False) as hdus:
            raw_header = hdus[0].header.copy()
            require(raw_header['ARCFILE'].removesuffix('.fits') == selection['raw_progenitor_id'], 'Raw archive identity mismatch')
            require(raw_header['DATE-OBS'] == source[dp]['primary_header']['DATE-OBS'], 'Raw date mismatch')
            require(raw_header['INSTRUME'] == 'HARPS', 'Raw instrument mismatch')
            raw = np.hstack([hdus[1].data[:, 50:2098], hdus[2].data[:, 50:2098]]).astype(float)
        del compressed
        with tarfile.open(BASE / ancillary['relative_path']) as archive:
            members = [member for member in archive if member.name.endswith('_e2ds_A.fits')]
            require(len(members) == 1, 'Native fiber A member must be unique')
            member = members[0]
            with fits.open(io.BytesIO(archive.extractfile(member).read()), memmap=False) as hdus:
                verify_native_identity(hdus[0].header, member.name, ancillary, source[dp]['primary_header'])
                native = hdus[0].data.astype(float)
                header = hdus[0].header.copy()
            inventory = dict(dp_id=dp, raw_context=context(raw_header), members=archive.getnames(), fiber_headers={})
            for fiber in ['A', 'B']:
                fiber_members = [entry for entry in archive if entry.name.endswith('_e2ds_' + fiber + '.fits')]
                if not fiber_members:
                    inventory['fiber_headers'][fiber] = dict(status='MISSING')
                    continue
                require(len(fiber_members) == 1, 'Native fiber member must be unique')
                with fits.open(io.BytesIO(archive.extractfile(fiber_members[0]).read()), memmap=False) as hdus:
                    inventory['fiber_headers'][fiber] = dict(status='PRESENT', context=context(hdus[0].header), member=fiber_members[0].name)
            inventory['independent_sky_fiber_available'] = raw_header.get('ESO DPR TYPE', '').split(',')[1:2] == ['SKY'] and inventory['fiber_headers']['B']['status'] == 'PRESENT'
            fiber_inventory.append(inventory)
        require(header['DATE-OBS'] == raw_header['DATE-OBS'], 'Native date mismatch')
        berv = float(header['ESO DRS BERV'])
        require(abs(berv - source[dp]['primary_header']['HIERARCH ESO DRS BERV']) < 1e-8, 'Native/science BERV mismatch')
        require(raw.shape == (4096, 4096) and native.shape == (72, 4096), 'Unexpected raw/native shape')
        degree = int(header['ESO DRS CAL TH DEG LL'])
        trace_degree = int(header['ESO DRS CAL LOC DEG CTR'])
        pixels = np.arange(4096)
        waves = np.array([poly(header, 'ESO DRS CAL TH COEFF LL', degree, order, pixels) for order in range(72)])
        candidates = []
        for hit in hits:
            center = float(hit['fitted_center_bary_air_angstrom']) / (1 + berv / 299792.458)
            for order in np.flatnonzero((waves[:, 0] < center) & (waves[:, -1] > center)):
                candidates.append(dict(review_id=hit['review_id'], order=int(order), native_pixel=int(np.argmin(abs(waves[order] - center)))))
        grid = evaluate_reference_grid(raw, native, header, candidates)
        best = grid['orientation_summaries'][0]
        global_ok = bool(best['median_correlation'] is not None and best['median_correlation'] > .8
                         and best['valid_regions'] >= 18 and best['valid_orders'] >= 5
                         and best['median_abs_continuum_peak_offset'] <= 1)
        name = dp.replace(':', '_') + '.json'
        dump('reference/' + name, grid)
        needed_orders = sorted({candidate['order'] for candidate in candidates})
        reference_by_order = {}
        for order in needed_orders:
            reference_by_order[order] = dict(dp_id=dp, **reference_order(raw, native, header, order, best, candidates, METHOD_CONFIGURATION['reference_windows_half_open']))
            reference_audit.append(reference_by_order[order])
        spectra.append(dict(dp_id=dp, status='REGISTERED' if global_ok else 'MAPPING_UNCERTAIN', raw_sha256=raw_product['sha256'],
                            ancillary_sha256=ancillary['sha256'], date_obs=raw_header['DATE-OBS'], berv_km_s=berv,
                            native_member=member.name, reference_grid='reference/' + name, grid_best=best,
                            covering_order_count=len(needed_orders), five_window_supported_orders=sum(reference_by_order[order]['mapping_supported'] for order in needed_orders)))
        for hit in hits:
            center = float(hit['fitted_center_bary_air_angstrom']) / (1 + berv / 299792.458)
            covering = np.flatnonzero((waves[:, 0] < center) & (waves[:, -1] > center)).tolist()
            event_orders = []
            for order in covering:
                k = int(np.argmin(abs(waves[order] - center)))
                raw_row = 4095 - k if best['row_flip'] else k
                argument = 4095 - k if best['argument_flip'] else k
                raw_column = float(poly(header, 'ESO DRS CAL LOC CTR', trace_degree, order, argument))
                raw_column = 4095 - raw_column if best['column_flip'] else raw_column
                rounded_column = round(raw_column)
                five_window_ok = bool(reference_by_order[order]['mapping_supported'])
                local = evaluate_local_trace(raw, native, header, order, k, best, candidates)
                local.update(review_id=hit['review_id'], order=order, dp_id=dp, global_reference_mapping_verified=global_ok)
                local_audit.append(local)
                record = dict(review_id=hit['review_id'], detector=hit['detector'], dp_id=dp, target=hit['target'], order=order,
                              native_pixel=k, topocentric_air_angstrom=center, native_nearest_wave_angstrom=float(waves[order, k]),
                              raw_row=int(raw_row), raw_column=raw_column, grid_mapping_usable=global_ok,
                              local_mapping_usable=bool(local['local_mapping_usable']),
                              baseline_mapping_verified=bool(global_ok and local['local_mapping_usable']),
                              five_window_mapping_supported=five_window_ok, reference_correlation=best['median_correlation'],
                              origin_status='UNREVIEWED')
                if not (20 <= k < 4076 and 16 <= rounded_column < 4080 and 15 <= raw_row < 4081):
                    record.update(status='EDGE_TRUNCATED', mapping_verified=False)
                    orders.append(record)
                    event_orders.append(record)
                    continue
                cutout = raw[raw_row - 15:raw_row + 16, rounded_column - 16:rounded_column + 17].copy()
                background = np.median(cutout[np.r_[0:10, 21:31]], axis=0)
                excess = cutout - background[None, :]
                baseline_cutout = raw[raw_row - 10:raw_row + 11, rounded_column - 12:rounded_column + 13].copy()
                require(np.array_equal(baseline_cutout, cutout[5:26, 4:29]), 'Nested original cutout differs')
                baseline_background = np.median(baseline_cutout[np.r_[0:5, 16:21]], axis=0)
                native_slice = slice(k - 20, k + 21)
                filename = hit['review_id'] + '_o' + str(order).zfill(2) + '.npz'
                path = native_dir / filename
                require(not path.exists(), 'Cutout must not be silently replaced')
                np.savez_compressed(path, raw_cutout=cutout, raw_background=background, raw_excess=excess,
                                    baseline_raw_cutout=baseline_cutout, baseline_raw_background=baseline_background,
                                    baseline_raw_excess=baseline_cutout - baseline_background[None, :],
                                    native_wave=waves[order, native_slice], native_flux=native[order, native_slice])
                record.update(status='EXTRACTED', cutout='native/' + filename, cutout_sha256=sha(path),
                              mapping_verified=bool(global_ok and five_window_ok))
                orders.append(record)
                event_orders.append(record)
            all_full = bool(event_orders) and all(record['status'] == 'EXTRACTED' for record in event_orders)
            event_mapping_ok = bool(all_full and all(record['mapping_verified'] for record in event_orders))
            event_summary.append(dict(review_id=hit['review_id'], detector=hit['detector'], dp_id=dp, covering_orders=covering,
                                      status='NATIVE_CONTEXT_EXTRACTED' if all_full else 'NO_USABLE_COMPLETE_CUTOUT_SET',
                                      mapping_supported=event_mapping_ok,
                                      baseline_all_orders_mapping_verified=bool(all_full and all(record['baseline_mapping_verified'] for record in event_orders)),
                                      edge_truncated_orders=[record['order'] for record in event_orders if record['status'] == 'EDGE_TRUNCATED'],
                                      unsupported_orders=[record['order'] for record in event_orders if not record['mapping_verified']],
                                      origin_status='UNREVIEWED'))
        print(dp, len(hits), 'events;', len(needed_orders), 'unique orders;', sum(reference_by_order[o]['mapping_supported'] for o in needed_orders), 'five-window supported', flush=True)
        del raw, native
        gc.collect()
    require(len(event_summary) == len(events), 'Event accounting incomplete')
    require([event['review_id'] for event in event_summary] == [event['review_id'] for event in events], 'Event accounting order changed')
    verify_freeze()
    stamp = now()
    dump('FIVE_WINDOW_MAPPING_AUDIT.json', dict(created_utc=stamp, method_configuration=METHOD_CONFIGURATION,
                                               candidate_exclusion_population_records=len(events), reference_audit=reference_audit,
                                               coordinates_changed=False, local_check_role='Preserved descriptive baseline; prospective final gate uses global AND five-window support for every covering order, with full cutouts.',
                                               origin_assignments=0))
    dump('NATIVE_MAPPING.json', dict(created_utc=stamp, spectra=spectra, orders=orders, events=event_summary,
                                    hits=len(events), extracted_orders=sum(record['status'] == 'EXTRACTED' for record in orders),
                                    plan_sha256=sha(OUT / 'PLAN.json'), freeze_sha256=sha(OUT / 'FOLLOWUP_FREEZE.json'),
                                    method='Frozen global-grid orientation; inherited local flags preserved; inherited five-window geometry check prospectively applied to EVERY covering order. Fixed 31x33 raw snippets retain exact nested21x25 baseline pixels and both background conventions. Native41 samples. No classification performed.'))
    dump('LOCAL_TRACE_AUDIT.json', dict(method='Unchanged candidate-excluded two-sided local continuum check; preserved descriptively', orders=local_audit))
    dump('FIBER_INVENTORY.json', fiber_inventory)


if __name__ == '__main__':
    main()
