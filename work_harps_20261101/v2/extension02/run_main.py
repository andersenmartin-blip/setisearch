#!/usr/bin/env python3
"""Original immutable V1 and V2, on extension02 only; never alters prior results."""
import importlib.metadata
import json
import sys
import time

sys.dont_write_bytecode = True
from common import BASE, HERE, ROLE, csvout, dump, now, require, sha, verified_scope, verify_publication


def main():
    rows, previous, protocol, freeze = verified_scope()
    acquisition = HERE / 'acquisition'
    publication = json.loads((acquisition / 'PUBLICATION.json').read_text())
    verify_publication(publication['freeze_commit'], publication['freeze_sha256'])
    scope = json.loads((acquisition / 'ACQUISITION_SCOPE.json').read_text())
    require(scope['selection_sha256'] == sha(HERE / 'MAIN100.csv'), 'Acquisition selection changed')
    require(scope['freeze_sha256'] == sha(HERE / 'FREEZE.json'), 'Acquisition freeze changed')
    receipts = json.loads((acquisition / 'DOWNLOAD_MANIFEST.json').read_text())
    require([r['dp_id'] for r in receipts] == [r['dp_id'] for r in rows], 'Acquisition manifest order or membership changed')
    require(len({r['dp_id'] for r in receipts}) == 100, 'Duplicate acquisition manifest row')
    from acquire import context, header_module, inspect
    ctx = context(previous)
    parser = header_module()
    checked, omitted = [], []
    for row, receipt in zip(rows, receipts):
        require(receipt['role'] == ROLE, 'Wrong acquisition role')
        if receipt.get('header_status') != 'PASS_METADATA_ONLY' or not all(receipt.get('checks', {}).values()):
            omitted.append(dict(dp_id=row['dp_id'], canonical_target=row['canonical_target'],
                                input_status='NOT_ANALYZED_ACQUISITION_OR_HEADER_FAILURE', acquisition_status=receipt.get('header_status', receipt['download_status'])))
            continue
        path = BASE / receipt['relative_path']
        require(path.resolve().parent == (HERE / 'data/main').resolve(), 'Input outside this cohort')
        require(sha(path) == receipt['sha256'], 'Downloaded file hash changed: ' + row['dp_id'])
        checked_header = inspect(path, row, ctx, parser)
        require(checked_header['header_status'] == 'PASS_METADATA_ONLY', 'Header recheck failed: ' + row['dp_id'])
        checked.append((row, receipt, path))
    require(bool(checked), 'No valid inputs; no production run created')
    versions = {name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'astropy')}
    require(versions == freeze['numerical_versions'], 'Numerical dependency versions changed')
    sys.path[:0] = [str(BASE / 'code'), str(BASE / 'v2/code')]
    from harps_detector import read_spectrum, analyze_arrays as v1
    from profile_detector import analyze_arrays as v2
    cfg1 = json.loads((BASE / 'code/DETECTOR_CONFIG.json').read_text())
    cfg2 = json.loads((BASE / 'v2/code/CONFIG.json').read_text())
    out = HERE / 'production'
    out.mkdir(exist_ok=False)
    (out / 'spectra').mkdir()
    dump(out / 'RUN_INPUTS.json', dict(started_utc=now(), runner_sha256=sha(__file__),
                                      freeze_sha256=sha(HERE / 'FREEZE.json'), freeze=freeze, publication=publication,
                                      selection_sha256=sha(HERE / 'MAIN100.csv'), manifest_sha256=sha(acquisition / 'DOWNLOAD_MANIFEST.json'),
                                      numerical_versions=versions, selected_exposures=100, admitted_exposures=len(checked),
                                      scope='Only the prospectively frozen extension02 cohort; originals remain separate.'))
    csvout(out / 'NOT_ANALYZED.csv', omitted)
    exposures, events1, events2, hits1, hits2 = [], [], [], [], []
    started = time.monotonic()
    try:
        for row, receipt, path in checked:
            wave, flux, meta = read_spectrum(path)
            require(meta['sha256'] == receipt['sha256'], 'Input changed during read')
            result1, _ = v1(wave, flux, cfg1)
            result2, _ = v2(wave, flux, cfg2)
            common = dict(dp_id=row['dp_id'], canonical_target=row['canonical_target'], date_obs=meta['DATE-OBS'],
                          selection_index=int(row['selection_index']), raw_progenitor_id=row['raw_progenitor_id'],
                          input_sha256=receipt['sha256'], cohort='extension02')
            for result, name in [(result1, 'v1'), (result2, 'v2')]:
                dump(out / 'spectra' / (row['dp_id'].replace(':', '_') + '_' + name + '.json'),
                     dict(**common, input=meta, result=result))
            for event in result1['all_threshold_runs']:
                value = dict(**common, **event)
                if event['status'] == 'PRELIMINARY_EMISSION_HIT':
                    value['candidate_id'] = f'V1E2-{len(hits1) + 1:04d}'
                    hits1.append(value)
                events1.append(value)
            for event in result2['events']:
                value = dict(**common, **event)
                if event['status'] == 'PRELIMINARY_PROFILE_HIT':
                    value['candidate_id'] = f'V2E2-{len(hits2) + 1:04d}'
                    hits2.append(value)
                events2.append(value)
            exposures.append(dict(**common, exposure_seconds=float(row['t_exptime']),
                                  v1_searched=result1['searched_samples'], v2_searched=result2['searched_samples'],
                                  v1_hits=result1['preliminary_hit_count'], v2_hits=result2['preliminary_hit_count'],
                                  v2_screened=result2['screened_events']))
            dump(out / 'PROGRESS.json', dict(finished_inputs=len(exposures), admitted_inputs=len(checked), last_dp_id=row['dp_id']))
            print(json.dumps(exposures[-1]), flush=True)
    except Exception as exc:
        dump(out / 'FAILED_RUN.json', dict(status='INCOMPLETE_NO_SILENT_RERUN', failed_utc=now(),
                                           completed_exposures=len(exposures), error_type=type(exc).__name__, error=str(exc)))
        raise
    for name, records in [('EXPOSURES.csv', exposures), ('V1_ALL_RUNS.csv', events1), ('V2_ALL_SCREENED_EVENTS.csv', events2),
                          ('V1_HITS.csv', hits1), ('V2_HITS.csv', hits2),
                          ('V2_DISPOSITIONS.csv', [dict(**r, origin_status='UNREVIEWED') for r in hits2])]:
        csvout(out / name, records)
    # Recheck all original catalogs and algorithm sources after computation.
    verified_scope()
    summary = dict(status='COMPLETED' if not omitted else 'COMPLETED_AVAILABLE_INPUTS_WITH_EXCLUSIONS', finished_utc=now(),
                   selected_exposures=100, analyzed_exposures=len(exposures), not_analyzed_exposures=len(omitted),
                   targets=len({r['canonical_target'] for r in exposures}), exposure_seconds=sum(r['exposure_seconds'] for r in exposures),
                   v1_hits=len(hits1), v2_hits=len(hits2), v2_screened=len(events2),
                   v1_searched_samples=sum(r['v1_searched'] for r in exposures), v2_searched_samples=sum(r['v2_searched'] for r in exposures),
                   wall_seconds=time.monotonic() - started, candidate_id_rule='Accepted events in frozen exposure order and unchanged detector event order.',
                   prior_main_exposures=200, prior_development_validation_excluded=9,
                   interpretation='Every accepted event is unreviewed. A profile match is not a laser identification. V1 and V2 have different selection functions; prior 192 injection trials are conditional, not extension02 sensitivity.',
                   search_overlap_limit='No match in the pinned ADP/raw reference inventory does not establish that nobody previously searched these exposures.')
    dump(out / 'SUMMARY.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
