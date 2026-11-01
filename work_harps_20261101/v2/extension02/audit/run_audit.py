"""Read-only numerical audit; writes only this audit directory, no network."""
from pathlib import Path
import collections
import csv
import datetime
import hashlib
import importlib.metadata
import json
import sys
import time

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError('Audit requires Python assertions enabled; do not use -O or PYTHONOPTIMIZE.')
OUT = Path(__file__).resolve().parent
EXT = OUT.parent
BASE = EXT.parents[1]
sys.path.insert(0, str(EXT))
from common import verified_scope, sha
from acquire import context, header_module, inspect


def readj(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def serialized(value):
    return json.dumps(value) if isinstance(value, (dict, list)) else ('' if value is None else str(value))


def exact_csv(path, expected):
    fields = sorted({k for row in expected for k in row}) or ['status']
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        actual = list(reader)
        assert reader.fieldnames == fields, (path.name, 'fields')
    normalized = [{k: serialized(row.get(k, '')) for k in fields} for row in expected]
    assert actual == normalized, (path.name, 'rows')
    return dict(filename=path.name, rows=len(actual), sha256=sha(path), exact_serialization=True)


def main():
    started = time.monotonic()
    plan = readj(OUT / 'PLAN.json')
    selected, previous, protocol, freeze = verified_scope()
    assert sha(EXT / 'FREEZE.json') == plan['frozen_sha256']
    assert len(freeze['source_hashes']) == 55
    prod, acq = EXT / 'production', EXT / 'acquisition'
    summary = readj(prod / 'SUMMARY.json')
    assert summary['status'] in ('COMPLETED', 'COMPLETED_AVAILABLE_INPUTS_WITH_EXCLUSIONS')
    assert not (prod / 'FAILED_RUN.json').exists()
    snapshot = {str(p.relative_to(BASE)): sha(p) for folder in (prod, acq) for p in sorted(folder.rglob('*')) if p.is_file()}
    manifest = readj(acq / 'DOWNLOAD_MANIFEST.json')
    result = readj(acq / 'ACQUISITION_RESULT.json')
    publication = readj(acq / 'PUBLICATION.json')
    acquisition_scope = readj(acq / 'ACQUISITION_SCOPE.json')
    run_inputs = readj(prod / 'RUN_INPUTS.json')
    assert publication['freeze_commit'] == plan['published_commit']
    assert publication['freeze_sha256'] == sha(EXT / 'FREEZE.json')
    assert acquisition_scope['publication'] == publication == run_inputs['publication']
    for record in (acquisition_scope, run_inputs):
        assert record['selection_sha256'] == sha(EXT / 'MAIN100.csv')
        assert record['freeze_sha256'] == sha(EXT / 'FREEZE.json')
    assert run_inputs['manifest_sha256'] == sha(acq / 'DOWNLOAD_MANIFEST.json')
    assert run_inputs['runner_sha256'] == sha(EXT / 'run_main.py')
    assert run_inputs['freeze'] == freeze
    assert datetime.datetime.fromisoformat(publication['confirmed_utc']) >= datetime.datetime.fromisoformat(freeze['frozen_utc'])
    assert run_inputs['numerical_versions'] == freeze['numerical_versions'] == {name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'astropy')}
    assert len(selected) == len(manifest) == len({r['dp_id'] for r in manifest}) == 100
    assert [r['dp_id'] for r in manifest] == [r['dp_id'] for r in selected]
    assert len(previous['adp_ids']) == len(previous['raw_ids']) == len(previous['target_start_keys']) == 209
    old_keys = {(r[0], float(r[1])) for r in previous['target_start_keys']}
    assert not {r['dp_id'] for r in selected}.intersection(previous['adp_ids'])
    assert not {r['raw_progenitor_id'] for r in selected}.intersection(previous['raw_ids'])
    assert not {(r['canonical_target'], float(r['t_min'])) for r in selected}.intersection(old_keys)
    ctx, parser = context(previous), header_module()
    raw_counts = collections.Counter(raw for r in manifest for raw in r.get('raw_progenitor_ids', []))
    headers, admitted, omitted, total_returned, downloaded_bytes = [], [], [], 0, 0
    header_metadata = {}
    for row, receipt in zip(selected, manifest):
        assert readj(acq / 'receipts' / (row['dp_id'].replace(':', '_') + '.json')) == receipt
        assert receipt['canonical_target'] == row['canonical_target'] and receipt['role'] == row['role']
        assert receipt['selection_index'] == int(row['selection_index'])
        assert receipt['source_url'] == row['source_url']
        assert receipt['expected_raw_progenitor_id'] == row['raw_progenitor_id']
        assert receipt['array_values_inspected'] is False
        assert datetime.datetime.fromisoformat(receipt['started_utc']) >= datetime.datetime.fromisoformat(publication['confirmed_utc'])
        assert datetime.datetime.fromisoformat(receipt['finished_utc']) <= datetime.datetime.fromisoformat(run_inputs['started_utc'])
        assert len(receipt['attempts']) <= protocol['maximum_attempts_per_file']
        assert [a['timeout_seconds'] for a in receipt['attempts']] == protocol['attempt_timeouts_seconds'][:len(receipt['attempts'])]
        total_returned += sum(a['returned_payload_bytes'] for a in receipt['attempts'])
        path = BASE / receipt['relative_path']
        assert path.resolve().parent == (EXT / 'data/main').resolve()
        passes = receipt.get('header_status') == 'PASS_METADATA_ONLY' and all(receipt.get('checks', {}).values())
        check = dict(dp_id=row['dp_id'], canonical_target=row['canonical_target'], selection_index=int(row['selection_index']), receipt_pass=passes, local_file_present=path.exists())
        if path.exists():
            assert path.stat().st_size == receipt['bytes'] <= protocol['per_file_byte_cap']
            assert sha(path) == receipt['sha256']
            downloaded_bytes += receipt['bytes']
            check.update(bytes=receipt['bytes'], sha256=receipt['sha256'])
            try:
                reviewed = inspect(path, row, ctx, parser)
            except Exception as exc:
                if passes:
                    raise
                check.update(recheck_status='REPRODUCED_INSPECTION_ERROR', error_type=type(exc).__name__, error=str(exc))
            else:
                reviewed['checks']['unique_raw_within_extension02'] = all(raw_counts[x] == 1 for x in reviewed['raw_progenitor_ids'])
                reproduced_pass = all(reviewed['checks'].values())
                assert reviewed['checks'] == receipt['checks']
                assert reviewed['raw_progenitor_ids'] == receipt['raw_progenitor_ids']
                if passes:
                    assert reviewed['raw_progenitor_ids'] == [row['raw_progenitor_id']]
                assert reproduced_pass == passes
                check.update(recheck_status='PASS' if reproduced_pass else 'REPRODUCED_METADATA_EXCLUSION', checks=reviewed['checks'], raw_progenitor_ids=reviewed['raw_progenitor_ids'])
        else:
            assert not passes
            check['recheck_status'] = 'NO_DOWNLOADED_INPUT'
        if passes:
            with path.open('rb') as stream:
                primary = parser.old.read_header(stream)
                extension = parser.old.read_header(stream)
            wave_col = next(k[5:] for k, v in extension.items() if k.startswith('TTYPE') and v == 'WAVE')
            flux_col = next(k[5:] for k, v in extension.items() if k.startswith('TTYPE') and v == 'FLUX')
            meta = {k: primary.get(k) for k in ['OBJECT', 'DATE-OBS', 'MJD-OBS', 'EXPTIME', 'SPECSYS', 'PROCSOFT', 'ORIGFILE', 'ARCFILE', 'WAVELMIN', 'WAVELMAX']}
            meta.update(wavelength_unit=extension.get('TUNIT' + wave_col), wavelength_ucd=extension.get('TUCD1'), flux_unit=extension.get('TUNIT' + flux_col), sha256=receipt['sha256'], input_filename=path.name, raw_progenitors={k: v for k, v in primary.items() if k.startswith('PROV')}, berv_km_s=primary.get('HIERARCH ESO DRS BERV'))
            header_metadata[row['dp_id']] = meta
            check['independently_read_input_header_metadata'] = meta
            admitted.append((row, receipt, path))
        else:
            omitted.append(dict(dp_id=row['dp_id'], canonical_target=row['canonical_target'], input_status='NOT_ANALYZED_ACQUISITION_OR_HEADER_FAILURE', acquisition_status=receipt.get('header_status', receipt['download_status'])))
        headers.append(check)
    expected_fits = {str((BASE / r['relative_path']).resolve()) for r in manifest if (BASE / r['relative_path']).exists()}
    assert expected_fits == {str(p.resolve()) for p in (EXT / 'data/main').glob('*.fits')}
    expected_statuses = dict(collections.Counter(r.get('header_status', r['download_status']) for r in manifest))
    assert expected_statuses == result['result_counts']
    assert result['selected_files'] == 100
    assert total_returned == result['returned_payload_bytes']
    assert downloaded_bytes <= total_returned <= result['conservative_charged_payload_bytes'] <= protocol['total_payload_byte_cap']
    assert result['payload_budget_bytes'] == protocol['total_payload_byte_cap']
    assert result['array_values_inspected'] is False and acquisition_scope['array_values_inspected'] is False
    assert run_inputs['selected_exposures'] == 100 and run_inputs['admitted_exposures'] == len(admitted)
    if len(admitted) < 3:
        raise RuntimeError('Three distinct admitted inputs are required for the planned numerical audit.')
    table_checks = [exact_csv(acq / 'DOWNLOAD_MANIFEST.csv', manifest), exact_csv(prod / 'NOT_ANALYZED.csv', omitted)]
    exposures, all1, all2, hits1, hits2 = [], [], [], [], []
    for row, receipt, path in admitted:
        dp = row['dp_id']
        s1, s2 = (readj(prod / 'spectra' / (dp.replace(':', '_') + '_' + name + '.json')) for name in ('v1', 'v2'))
        assert s1['input'] == s2['input'] and s1['input']['sha256'] == receipt['sha256']
        assert set(s1['input']) == set(header_metadata[dp]) | {'finite_error_samples'}
        assert {k: s1['input'][k] for k in header_metadata[dp]} == header_metadata[dp], (dp, 'input header metadata')
        common = dict(dp_id=dp, canonical_target=row['canonical_target'], date_obs=s1['input']['DATE-OBS'], selection_index=int(row['selection_index']), raw_progenitor_id=row['raw_progenitor_id'], input_sha256=receipt['sha256'], cohort='extension02')
        for saved in (s1, s2):
            assert {k: saved[k] for k in common} == common
        r1, r2 = s1['result'], s2['result']
        assert r1['config'] == readj(BASE / 'code/DETECTOR_CONFIG.json')
        assert r2['config'] == readj(BASE / 'v2/code/CONFIG.json')
        for event in r1['all_threshold_runs']:
            value = dict(**common, **event)
            if event['status'] == 'PRELIMINARY_EMISSION_HIT':
                value['candidate_id'] = f'V1E2-{len(hits1) + 1:04d}'
                hits1.append(value)
            all1.append(value)
        for event in r2['events']:
            value = dict(**common, **event)
            if event['status'] == 'PRELIMINARY_PROFILE_HIT':
                value['candidate_id'] = f'V2E2-{len(hits2) + 1:04d}'
                hits2.append(value)
            all2.append(value)
        assert r1['preliminary_hit_count'] == sum(e['status'] == 'PRELIMINARY_EMISSION_HIT' for e in r1['all_threshold_runs'])
        assert r2['preliminary_hit_count'] == sum(e['status'] == 'PRELIMINARY_PROFILE_HIT' for e in r2['events'])
        assert r2['screened_events'] == len(r2['events'])
        exposures.append(dict(**common, exposure_seconds=float(row['t_exptime']), v1_searched=r1['searched_samples'], v2_searched=r2['searched_samples'], v1_hits=r1['preliminary_hit_count'], v2_hits=r2['preliminary_hit_count'], v2_screened=r2['screened_events']))
    for name, records in [('EXPOSURES.csv', exposures), ('V1_ALL_RUNS.csv', all1), ('V2_ALL_SCREENED_EVENTS.csv', all2), ('V1_HITS.csv', hits1), ('V2_HITS.csv', hits2), ('V2_DISPOSITIONS.csv', [dict(**r, origin_status='UNREVIEWED') for r in hits2])]:
        table_checks.append(exact_csv(prod / name, records))
    expected_summary = dict(selected_exposures=100, analyzed_exposures=len(exposures), not_analyzed_exposures=len(omitted), targets=len({r['canonical_target'] for r in exposures}), exposure_seconds=sum(r['exposure_seconds'] for r in exposures), v1_hits=len(hits1), v2_hits=len(hits2), v2_screened=len(all2), v1_searched_samples=sum(r['v1_searched'] for r in exposures), v2_searched_samples=sum(r['v2_searched'] for r in exposures), prior_main_exposures=200, prior_development_validation_excluded=9)
    assert all(summary[k] == v for k, v in expected_summary.items())
    progress = readj(prod / 'PROGRESS.json')
    assert progress['finished_inputs'] == progress['admitted_inputs'] == len(admitted)
    assert progress['last_dp_id'] == admitted[-1][0]['dp_id']
    # Fixed sample positions depend only on admission and frozen ordering.
    chosen = [admitted[i] for i in sorted({0, len(admitted) // 2, len(admitted) - 1})]
    sys.path[:0] = [str(BASE / 'code'), str(BASE / 'v2/code')]
    from harps_detector import read_spectrum, analyze_arrays as v1
    from profile_detector import analyze_arrays as v2
    reruns = []
    for row, receipt, path in chosen:
        print('RERUN ' + row['dp_id'], flush=True)
        wave, flux, meta = read_spectrum(path)
        for name, algorithm, cfgpath in [('v1', v1, BASE / 'code/DETECTOR_CONFIG.json'), ('v2', v2, BASE / 'v2/code/CONFIG.json')]:
            tick = time.monotonic()
            regenerated, _ = algorithm(wave, flux, readj(cfgpath))
            saved = readj(prod / 'spectra' / (row['dp_id'].replace(':', '_') + '_' + name + '.json'))
            assert regenerated == saved['result'] and meta == saved['input'], (row['dp_id'], name)
            digest = hashlib.sha256(json.dumps(regenerated, sort_keys=True, allow_nan=False).encode()).hexdigest()
            reruns.append(dict(dp_id=row['dp_id'], selection_index=int(row['selection_index']), detector=name, status='EXACT_MATCH_ENTIRE_RESULT_AND_INPUT_METADATA', canonical_result_sha256=digest, searched_samples=regenerated['searched_samples'], preliminary_hit_count=regenerated['preliminary_hit_count'], elapsed_seconds=time.monotonic() - tick))
    verified_scope()
    assert all(sha(BASE / p) == digest for p, digest in snapshot.items())
    dump('HEADER_RECHECKS.json', headers)
    dump('PRODUCTION_AND_ACQUISITION_HASHES.json', snapshot)
    report = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='PASS_INDEPENDENT_NUMERICAL_AUDIT', plan_sha256=sha(OUT / 'PLAN.json'), audit_code_sha256=sha(Path(__file__)), freeze_sha256=sha(EXT / 'FREEZE.json'), published_commit=publication['freeze_commit'], source_hashes_verified=55, prior_overlap=dict(ADP=0, raw=0, target_start=0), downloaded_files=sum(r['local_file_present'] for r in headers), admitted_headers_rechecked=len(admitted), all_saved_input_header_metadata_independently_verified=True, finite_error_samples_recomputed_for='The three fixed-position full science rereads only; ERR counts are not used by either detector.', input_bytes_verified=downloaded_bytes, returned_payload_bytes_verified=total_returned, conservative_payload_charge=result['conservative_charged_payload_bytes'], header_status_counts=expected_statuses, exact_csv_checks=table_checks, totals=expected_summary, v1_status_counts=dict(collections.Counter(r['status'] for r in all1)), v2_status_counts=dict(collections.Counter(r['status'] for r in all2)), rerun_selection='First, middle and last admitted exposures in frozen metadata order; not selected by hits.', exact_reruns=reruns, production_and_acquisition_files_unchanged=len(snapshot), original_frozen_sources_unchanged=True, network_calls=0, newly_downloaded_files=0, elapsed_seconds=time.monotonic() - started, limitations=['Independent rerun of the same frozen algorithms, not an independently implemented detector.', 'No physical-origin claim, calibrated false-alarm rate, or extension02 sensitivity follows from this audit.', 'Remote commit publication is rooted in the parent agent verification receipt; this audit itself makes no network request.'])
    dump('SUMMARY.json', report)
    text = f'''# Uafhængig numerisk kontrol af extension02

Kontrollen bestod. {len(admitted)} af de 100 fastlagte eksponeringer er analyseret; {len(omitted)} er eksplicit udeladt. Alle downloadede filhashes, de godkendte headers og 55 fastlåste kildefiler er kontrolleret. Ingen ADP-, rå-ID- eller mål/starttids-overlap med de tidligere 209 inputs blev fundet.

De gemte per-spektrumresultater genskaber samtlige katalogtabeller præcist: **{len(hits1)} foreløbige V1-træf og {len(hits2)} foreløbige V2-profiltræf**. V2-træffene står fortsat som `UNREVIEWED`. De tilsammen gennemsøgte samples er {expected_summary['v1_searched_samples']} for V1 og {expected_summary['v2_searched_samples']} for V2.

Første, midterste og sidste godkendte eksponering i den fastlagte metadatarækkefølge blev kørt igen med begge uændrede algoritmer. Alle seks komplette resultater og inputmetadata stemmer præcist. De øvrige eksponeringers detektorberegning blev ikke genkørt i denne kontrol.

Ingen oprindelige eller nye produktionsfiler er ændret, og kontrollen hentede ingen nye data. Dette er reproduktion af de samme algoritmer og filidentiteter; den fastslår ikke signalernes ophav eller udvidelsens følsomhed.

[Maskinlæsbar kontrol](SUMMARY.json) · [headerkontrol](HEADER_RECHECKS.json) · [kontrolkode](run_audit.py) · [fastlagt plan](PLAN.json)
'''
    (OUT / 'README.md').write_text(text)
    print(json.dumps(dict(status=report['status'], totals=expected_summary, exact_reruns=len(reruns))), flush=True)


if __name__ == '__main__':
    main()
