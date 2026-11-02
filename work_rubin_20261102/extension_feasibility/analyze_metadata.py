"""Necessary temporal/quality conditions only; never reads science values."""
from pathlib import Path
import collections, csv, datetime, hashlib, json, math
from astropy.time import Time
from astropy.utils import iers
iers.conf.auto_download = False
OUT = Path(__file__).resolve().parent
BASE = OUT.parent

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def finite(value):
    try:
        return not isinstance(value, bool) and math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False

def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def write_csv(name, records, fallback):
    keys = list(dict.fromkeys(key for rec in records for key in rec)) or fallback
    with (OUT / name).open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows({key: json.dumps(value, separators=(',', ':')) if isinstance(value, (list, dict)) else value
                         for key, value in rec.items()} for rec in records)

def normalize_metadata(rows, flags):
    groups = collections.defaultdict(list)
    for index, row in enumerate(rows):
        groups[row['r:diaSourceId']].append((index, row))
    records, duplicates = [], []
    for source_id, group in groups.items():
        variants = {json.dumps(row, sort_keys=True, allow_nan=False) for _, row in group}
        conflict = len(variants) > 1
        row = group[0][1]
        for index, _ in group[1:]:
            duplicates.append({'row_index': index, 'source_id': source_id,
                               'reason': 'CONFLICTING_METADATA_ID' if conflict else 'EXACT_METADATA_DUPLICATE'})
        reasons, notes = [], []
        t = float(row['r:midpointMjdTai']) if finite(row.get('r:midpointMjdTai')) else None
        if t is None:
            reasons.append('MISSING_OR_NONFINITE_midpointMjdTai')
        if row.get('r:band') not in list('ugrizy'):
            reasons.append('INVALID_BAND')
        if conflict:
            reasons.append('CONFLICTING_MEASUREMENT_ID_METADATA')
        if 'r:timeWithdrawnMjdTai' not in row:
            notes.append('WITHDRAWAL_STATUS_UNKNOWN')
        elif row['r:timeWithdrawnMjdTai'] is not None:
            if finite(row['r:timeWithdrawnMjdTai']):
                reasons.append('WITHDRAWN_RECORD')
            else:
                notes.append('WITHDRAWAL_STATUS_UNKNOWN')
        for flag in flags:
            value = row.get('r:' + flag)
            if value is True:
                reasons.append('FLAG_' + flag)
            elif value is not False:
                reasons.append('UNKNOWN_FLAG_' + flag)
        day = int(math.floor(float(Time(t, format='mjd', scale='tai').utc.mjd))) if t is not None else None
        records.append({'source_id': source_id, 'object_id': row['r:diaObjectId'],
                        'band': row.get('r:band'), 'visit': row['r:visit'],
                        'detector': row.get('r:detector'), 'time_mjd_tai': t,
                        'utc_day': day,
                        'utc_date': str(Time(day, format='mjd', scale='utc').isot)[:10] if day is not None else None,
                        'exposure_seconds': float(row['r:exposureTime']) if finite(row.get('r:exposureTime')) and float(row['r:exposureTime']) > 0 else None,
                        'quality_notes': notes, 'exclusion_reasons': reasons,
                        'input_row_index': group[0][0], 'duplicate_rows': len(group) - 1})
    physical = collections.defaultdict(list)
    for rec in records:
        physical[rec['object_id'], rec['visit'], rec['band']].append(rec)
    for group in physical.values():
        if len(group) > 1:
            for rec in group:
                rec['exclusion_reasons'].append('AMBIGUOUS_MULTIPLE_MEASUREMENTS_ONE_VISIT')
    records.sort(key=lambda r: (int(r['object_id']), str(r['band']), r['time_mjd_tai'] or -1, int(r['source_id'])))
    return records, duplicates

def temporal_context(records, method):
    output = []
    start, end = method['tai_test_window']
    for row in records:
        t = row['time_mjd_tai']
        if t is None or not start <= t < end:
            continue
        rec = dict(row)
        rec.update(status='EXCLUDED_METADATA_QUALITY' if row['exclusion_reasons'] else 'INSUFFICIENT_PRIOR_VISITS_OR_DATES',
                   prior_source_ids=[], prior_visit_ids=[], prior_utc_dates=[],
                   prior_visit_count=0, prior_date_count=0,
                   temporal_quality_necessary_condition=False)
        if not row['exclusion_reasons']:
            context = [other for other in records if not other['exclusion_reasons']
                       and other['object_id'] == row['object_id'] and other['band'] == row['band']
                       and t - method['baseline_days'] <= other['time_mjd_tai'] < t
                       and other['utc_day'] < row['utc_day']]
            visits = sorted({other['visit'] for other in context}, key=int)
            dates = sorted({other['utc_date'] for other in context})
            rec.update(prior_source_ids=[other['source_id'] for other in context],
                       prior_visit_ids=visits, prior_utc_dates=dates,
                       prior_visit_count=len(visits), prior_date_count=len(dates),
                       prior_quality_notes=sorted({note for other in context for note in other['quality_notes']}))
            if len(visits) >= method['min_unique_prior_visits'] and len(dates) >= method['min_earlier_utc_dates']:
                rec.update(status='MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION', temporal_quality_necessary_condition=True)
        output.append(rec)
    return output

def main():
    plan = json.loads((OUT / 'PLAN.json').read_text())
    assert plan['analyzer_sha256'] == sha(__file__)
    for source in plan['frozen_sources']:
        assert sha(BASE / source['path']) == source['sha256'], source['path']
    cone = json.loads((OUT / 'CONE_RESULT.json').read_text())
    inputs = [{'path': 'PLAN.json', 'sha256': sha(OUT / 'PLAN.json')},
              {'path': 'CONE_RESULT.json', 'sha256': sha(OUT / 'CONE_RESULT.json')}]
    summary = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'scope': 'Metadata-only temporal and quality necessary conditions; original main188 unchanged.',
               'new_main_selection_made': False, 'Gaia_queried': False, 'science_values_requested_or_read': False,
               'future_additional_main_cap': 312, 'future_total_main_cap': 500,
               'cone_status': cone['status'],
               'limitations': ['Not a flux or baseline-precision evaluation; no anomaly, deficit, or trigger measurement.',
                               'No claim of 50 evaluable stars; future main selection still requires Gaia matching, development-counterpart exclusion, and original science checks.',
                               'Metadata-identical repeats could conceal photometric conflicts; this test cannot inspect those.',
                               'API n100 semantics and public service history completeness remain unverified; counts describe returned records only.',
                               'Near-position exclusion uses reported cone coordinates, not a new motion-aware counterpart analysis.'],
               'inputs': inputs}
    if cone['status'] != 'COMPLETE':
        summary['outcome'] = 'STOPPED_BEFORE_HISTORY_NO_FEASIBILITY_CONCLUSION'
        write_json('SUMMARY.json', summary)
        (OUT / 'README.md').write_text('The single bounded same-field extension stopped before source-history acquisition.\n\n'
            f"Cone status: `{cone['status']}`. No alternative field or cone was requested; original main188 remains unchanged.\n\n"
            'This failure gives no temporal, quality, stellar-association, or scientific-evaluability conclusion. See PLAN.json and CONE_RESULT.json for the exact frozen request and attempt receipts.\n')
        return
    selection = list(csv.DictReader((OUT / 'HISTORY_SELECTION.csv').open()))
    manifest = json.loads((OUT / 'HISTORY_MANIFEST.json').read_text())
    jobs = json.loads((OUT / 'HISTORY_JOBS.json').read_text())
    inputs.extend({'path': name, 'sha256': sha(OUT / name)} for name in
                  ['HISTORY_SELECTION.csv', 'HISTORY_MANIFEST.json', 'HISTORY_JOBS.json', 'HISTORY_SELECTION_FREEZE.json'])
    id_status, rows = {}, []
    for job, result in zip(jobs, manifest['jobs'], strict=True):
        assert job['job_id'] == result['job_id']
        for oid in job['object_ids']:
            id_status[oid] = result['status']
        if result['status'] == 'COMPLETE':
            path = OUT / result['path']
            assert sha(path) == result['sha256']
            incoming = json.loads(path.read_text(), parse_int=str)
            assert all(set(row) <= set(plan['history_columns']) for row in incoming)
            assert all(row['r:diaObjectId'] in job['object_ids'] for row in incoming)
            rows.extend(incoming)
            inputs.append({'path': result['path'], 'sha256': sha(path)})
    records, duplicates = normalize_metadata(rows, plan['feasibility_method']['critical_flags'])
    october = temporal_context(records, plan['feasibility_method'])
    objects = []
    for selected in selection:
        oid = selected['r:diaObjectId']
        all_rows = [row for row in records if row['object_id'] == oid]
        tests = [row for row in october if row['object_id'] == oid]
        eligible = [row for row in tests if row['temporal_quality_necessary_condition']]
        quality_admitted = [row for row in tests if not row['exclusion_reasons']]
        status = 'HISTORY_UNAVAILABLE_' + id_status[oid] if id_status[oid] != 'COMPLETE' else (
            'EMPTY_RETURNED_HISTORY' if not all_rows else 'NO_OCTOBER_RECORD' if not tests else
            'NO_QUALITY_ADMITTED_OCTOBER_RECORD' if not quality_admitted else
            'MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION' if eligible else 'INSUFFICIENT_PRIOR_VISITS_OR_DATES')
        objects.append({'object_id': oid, 'history_selection_index': selected['history_selection_index'],
                        'history_request_status': id_status[oid], 'status': status,
                        'unique_metadata_sources': len(all_rows), 'october_sources': len(tests),
                        'quality_admitted_october_sources': len(quality_admitted),
                        'necessary_condition_october_sources': len(eligible),
                        'necessary_condition_source_ids': [row['source_id'] for row in eligible],
                        'max_prior_visits_over_quality_admitted_october': max((row['prior_visit_count'] for row in quality_admitted), default=0),
                        'max_prior_dates_over_quality_admitted_october': max((row['prior_date_count'] for row in quality_admitted), default=0),
                        'metadata_exclusion_reason_counts': dict(collections.Counter(reason for row in all_rows for reason in row['exclusion_reasons']))})
    necessary_objects = sum(row['necessary_condition_october_sources'] > 0 for row in objects)
    summary.update(outcome='METADATA_FEASIBILITY_COMPLETE' if manifest['all_jobs_complete'] else 'PARTIAL_METADATA_FEASIBILITY',
                   cone_rows=cone['rows'], initial433_exact_overlap=cone['initial433_exact_overlap'],
                   position_overlap=cone['position_overlap'], new_distinct_eligible_pool=cone['new_distinct_eligible_pool'],
                   history_selected=len(selection), history_omitted_by_cap=cone['history_omitted_by_cap'],
                   history_jobs_complete=sum(row['status']=='COMPLETE' for row in manifest['jobs']),
                   history_charged_bytes=manifest['charged_bytes'], raw_metadata_rows=len(rows),
                   unique_metadata_sources=len(records), duplicate_rows=len(duplicates),
                   object_status_counts=dict(collections.Counter(row['status'] for row in objects)),
                   october_status_counts=dict(collections.Counter(row['status'] for row in october)),
                   all_history_exclusion_reason_counts=dict(collections.Counter(reason for row in records for reason in row['exclusion_reasons'])),
                   quality_note_counts=dict(collections.Counter(note for row in records for note in row['quality_notes'])),
                   necessary_condition_objects=necessary_objects,
                   necessary_condition_october_sources=sum(row['temporal_quality_necessary_condition'] for row in october),
                   future_additional_main_arithmetic_ceiling=min(312, necessary_objects),
                   unknown_history_objects=sum(row['history_request_status'] != 'COMPLETE' for row in objects),
                   original_main188_sha256=sha(BASE/'gaia_selection/MAIN_SELECTION.csv'))
    write_csv('NORMALIZED_METADATA.csv', records, ['source_id', 'object_id', 'status'])
    write_csv('DUPLICATE_LOG.csv', duplicates, ['row_index', 'source_id', 'reason'])
    write_csv('OCTOBER_TEMPORAL_CONTEXT.csv', october, ['source_id', 'object_id', 'status'])
    write_csv('OBJECT_FEASIBILITY.csv', objects, ['object_id', 'status'])
    summary['output_hashes'] = {name: sha(OUT/name) for name in
                               ['NORMALIZED_METADATA.csv', 'DUPLICATE_LOG.csv', 'OCTOBER_TEMPORAL_CONTEXT.csv', 'OBJECT_FEASIBILITY.csv']}
    write_json('SUMMARY.json', summary)
    (OUT/'README.md').write_text(
        f"The single same-center one-degree October 2026 cone returned {cone['rows']} metadata rows. "
        f"After all initial433 identities and positions within 2 arcsec were excluded, {cone['new_distinct_eligible_pool']} new objects remained; "
        f"{len(selection)} were frozen for metadata-only histories in numeric ID order.\n\n"
        f"{necessary_objects} objects have at least one returned, quality-admitted October source with the fixed necessary same-band prior baseline: "
        'at least 5 distinct visit IDs on at least 3 earlier UTC dates within 180 days. The whole tested UTC date is excluded; '
        'all ambiguous same-object/visit/band groups are excluded, including across detectors. Critical source flags must be explicit false.\n\n'
        f"The arithmetic ceiling among these metadata candidates is {min(312, necessary_objects)} additional main objects under the remaining cap of 312. "
        'This is not a stellar-selection, flux-quality, baseline-precision, or science-evaluability count. No 50-object evaluability claim follows. '
        'Gaia matching, development-counterpart exclusion, finite flux/error, and the original baseline-precision test remain necessary.\n\n'
        f"Unknown or failed history requests affect {summary['unknown_history_objects']} selected objects; "
        f"{cone['history_omitted_by_cap']} additional cone objects lie beyond the frozen 1000-ID history cap. "
        'API history completeness and n100 cone semantics remain unverified. Metadata-identical records may conceal photometric conflicts.\n\n'
        'Original main188 selection and results remain unchanged. No new main selection, Gaia request, flux request, anomaly score, or threshold change was made. '
        'Exact request bodies, response bytes, hashes, per-object exclusions, and baseline memberships are preserved alongside this report.\n')

if __name__ == '__main__':
    main()
