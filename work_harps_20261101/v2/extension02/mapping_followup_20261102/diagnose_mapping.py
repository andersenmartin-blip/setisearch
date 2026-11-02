"""Posthoc decomposition of the frozen 35-record M queue; no reclassification.

Uses committed numerical summaries and 17-value reference profiles, not raw
FITS arrays. All writes stay in this new directory. Standard-library scalar
checks independently reconstruct gate arithmetic and profile peak estimates.
"""
from pathlib import Path
import collections
import csv
import datetime
import hashlib
import json
import math
import statistics

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
BASE = ROOT / 'work_harps_20261101'
V2 = BASE / 'v2'
STATE = V2 / 'extension02/raw_followup_batch04/CONTINUATION_STATE.json'
SOURCE_HASHES = {}


def load(path):
    path = Path(path)
    SOURCE_HASHES[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def csv_save(name, records):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def scalar_peak(profile):
    k = max(range(len(profile)), key=lambda i: profile[i])
    result = k - 8.
    if 0 < k < 16:
        a, b, c = profile[k-1:k+2]
        denominator = a - 2*b + c
        if denominator:
            result += .5*(a-c)/denominator
    return result


def recompute(ref):
    valid = [w for w in ref['windows'] if w['correlation'] is not None]
    for window in valid:
        assert window['samples'] >= 200
        assert len(window['profile']) == 17
        assert math.isclose(scalar_peak(window['profile']), window['peak_offset'], abs_tol=1e-12)
        assert math.isclose(max(window['profile']), window['peak_above_outer_baseline'], abs_tol=1e-10)
    corr = statistics.median([w['correlation'] for w in valid]) if valid else None
    offset = statistics.median([abs(w['peak_offset']) for w in valid]) if valid else None
    within = sum(abs(w['peak_offset']) <= 1 for w in valid)
    values = {'valid_reference_windows': len(valid), 'median_correlation': corr,
              'median_abs_peak_offset': offset, 'windows_within_one_pixel': within}
    for key, value in values.items():
        previous = ref[key]
        assert (previous is None and value is None) or math.isclose(previous, value, abs_tol=1e-12), key
    failures = []
    if len(valid) < 3: failures.append('valid_windows_below_3')
    if corr is None or corr <= .8: failures.append('median_correlation_not_above_0.8')
    if offset is None or offset > .75: failures.append('median_abs_peak_offset_above_0.75_or_missing')
    if within < 3: failures.append('centered_windows_below_3')
    assert ref['mapping_supported'] == (not failures)
    return failures


def main():
    plan = load(OUT / 'PLAN.json')
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == plan['script_sha256']
    assert hashlib.sha256(STATE.read_bytes()).hexdigest() == plan['source_state_sha256']
    state = load(STATE)
    records = state['followup_queues']['mapping_limited']['records']
    assert len(records) == 35
    assert [r['review_id'] for r in records] == plan['review_ids']
    assert all(r['current_code'] == 'M' for r in records)
    # Explicit five source families, preserving the current state's evidence routes.
    sources = {}
    for r in records:
        if r['cohort'] == 'V2_first100':
            source = V2 / 'mapping43_followup'
        elif r['review_id'] == 'V2E2-0225':
            source = V2 / 'extension02/raw_followup/mapping_followup'
        else:
            source = V2 / r['current_raw_batch']
        if source not in sources:
            combined = (source / 'MAPPING_AUDIT.json').exists()
            mapping = load(source / ('MAPPING_AUDIT.json' if combined else 'NATIVE_MAPPING.json'))
            audit = mapping if combined else load(source / 'FIVE_WINDOW_MAPPING_AUDIT.json')
            refs = {(x['dp_id'], x['order']): x for x in audit['reference_audit']}
            assert len(refs) == len(audit['reference_audit'])
            for ref in refs.values(): recompute(ref)
            sources[source] = (mapping, refs)
        r['_source'] = source
    events, order_rows, profiles = [], [], []
    seen_refs = set()
    for r in records:
        source = r['_source']
        mapping, refs = sources[source]
        orders = [x for x in mapping['orders'] if x['review_id'] == r['review_id']]
        assert orders and all(x['dp_id'] == r['dp_id'] for x in orders)
        global_record = next(x for x in mapping['spectra'] if x['dp_id'] == r['dp_id'])
        global_supported = global_record.get('status', 'REGISTERED') == 'REGISTERED'
        failures, missing, failed_orders = set(), [], []
        for order in orders:
            ref = refs[(r['dp_id'], order['order'])]
            gates = recompute(ref)
            if gates: failed_orders.append(order['order'])
            failures.update(gates)
            if order['status'] != 'EXTRACTED':
                assert order['status'] == 'EDGE_TRUNCATED'
                missing.append(order['order'])
                failures.add('full_cutout_unavailable')
            if not global_supported: failures.add('global_registration_unsupported')
            k, y, x = order['native_pixel'], order['raw_row'], order['raw_column']
            ix = round(x)
            geometry = []
            if not 20 <= k < 4076: geometry.append('41_sample_native_snippet_crosses_edge')
            if not 16 <= ix < 4080: geometry.append('33_column_raw_cutout_crosses_edge')
            if not 15 <= y < 4081: geometry.append('31_row_raw_cutout_crosses_edge')
            assert (order['status'] == 'EDGE_TRUNCATED') == bool(geometry)
            order_rows.append(dict(review_id=r['review_id'], target=r['target'], dp_id=r['dp_id'],
                source=str(source.relative_to(ROOT)), order=order['order'], status=order['status'],
                native_pixel=k, raw_row=y, raw_column=x, global_supported=global_supported,
                reference_mapping_supported=ref['mapping_supported'],
                valid_reference_windows=ref['valid_reference_windows'],
                median_correlation=ref['median_correlation'],
                median_abs_peak_offset=ref['median_abs_peak_offset'],
                windows_within_one_pixel=ref['windows_within_one_pixel'],
                failed_gates=';'.join(gates), edge_causes=';'.join(geometry)))
            ref_key = (str(source), r['dp_id'], order['order'])
            if ref_key not in seen_refs:
                seen_refs.add(ref_key)
                profiles.append(dict(source=str(source.relative_to(ROOT)), dp_id=r['dp_id'],
                    target=r['target'], order=order['order'], gates_failed=gates,
                    reference=ref))
        assert failures, 'Current M record has no reconstructed limitation: ' + r['review_id']
        events.append(dict(review_id=r['review_id'], cohort=r['cohort'], target=r['target'],
            dp_id=r['dp_id'], unchanged_code='M', source=str(source.relative_to(ROOT)),
            covering_orders=';'.join(str(x['order']) for x in orders),
            failed_reference_orders=';'.join(map(str,failed_orders)),
            missing_cutout_orders=';'.join(map(str,missing)),
            failed_gates=';'.join(sorted(failures)),
            category='edge_and_reference' if missing and failed_orders else 'edge_only' if missing else 'reference_only'))
    all_refs = [ref for _, refs in sources.values() for ref in refs.values()]
    selected_refs = [x['reference'] for x in profiles]
    failed_refs = [x for x in profiles if x['gates_failed']]
    summary = dict(schema='SETI_MAPPING35_DIAGNOSTIC_V1', created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status='PASS_RECORDED_SCALAR_RECONSTRUCTION_NO_RECLASSIFICATION',
        records=len(events), exposures=len({r['dp_id'] for r in events}), targets=len({r['target'] for r in events}),
        source_families=len(sources), covering_order_records=len(order_rows),
        unique_exposure_orders=len(selected_refs), full_cutout_records=sum(r['status']=='EXTRACTED' for r in order_rows),
        missing_full_cutout_records=sum(r['status']!='EXTRACTED' for r in order_rows),
        failed_unique_exposure_orders=len(failed_refs),
        category_counts=dict(collections.Counter(e['category'] for e in events)),
        event_failure_counts=dict(collections.Counter(g for e in events for g in e['failed_gates'].split(';'))),
        unique_reference_failure_counts=dict(collections.Counter(g for p in failed_refs for g in p['gates_failed'])),
        failed_reference_order_counts=dict(collections.Counter(str(p['order']) for p in failed_refs)),
        missing_edge_causes=dict(collections.Counter(g for r in order_rows for g in r['edge_causes'].split(';') if g)),
        selected_reference_median_correlation_range=[min(r['median_correlation'] for r in selected_refs),max(r['median_correlation'] for r in selected_refs)],
        failed_reference_median_correlation_range=[min(r['reference']['median_correlation'] for r in failed_refs),max(r['reference']['median_correlation'] for r in failed_refs)],
        maximum_selected_reference_median_abs_peak_offset=max(r['median_abs_peak_offset'] for r in selected_refs),
        selected_reference_valid_window_counts=dict(collections.Counter(str(r['valid_reference_windows']) for r in selected_refs)),
        selected_reference_centered_window_counts=dict(collections.Counter(str(r['windows_within_one_pixel']) for r in selected_refs)),
        independently_recomputed_reference_summaries=len(all_refs),
        independently_recomputed_reference_profile_peaks=sum(sum(w['correlation'] is not None for w in r['windows']) for r in all_refs),
        science_fits_arrays_opened=0, new_network_calls=0, origin_assignments=0, current_dispositions_changed=False,
        limitations=[
            'Posthoc selected M queue, not a blind or independent population and not a new signal search.',
            'Recomputes medians, flags and profile peak estimates from committed diagnostics; does not recompute raw/native correlations from original FITS pixels.',
            'Low reference correlation alone does not identify its cause; centered reference profiles do not establish complete mapping or physical origin.',
            'No threshold or coordinate tuning. Missing cutouts and failed references remain M.',
            'Historical mapping methods differ. Counts of reference families are a diagnostic coverage inventory, not a homogeneous survey denominator.'
        ])
    csv_save('EVENT_LIMITATIONS.csv', events)
    csv_save('ORDER_LIMITATIONS.csv', order_rows)
    save('REFERENCE_PROFILES.json', profiles)
    save('SUMMARY.json', summary)
    # Re-read bytes rather than trusting cached hashes after computation.
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest()==digest for path,digest in SOURCE_HASHES.items())
    save('SOURCE_HASHES.json', SOURCE_HASHES)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__': main()
