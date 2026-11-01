"""Independent metadata-only preregistration audit; no network or raw arrays."""
from pathlib import Path
import collections
import csv
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
EXT = BATCH.parent
BASE = EXT.parents[1]
REPO = BASE.parent
PREVIOUS = EXT / 'raw_followup_batch03'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    with Path(path).open(newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    checks = []
    def check(name, condition, evidence=None):
        checks.append(dict(name=name, passed=bool(condition), evidence=evidence))
        if not condition:
            raise AssertionError(name)
    plan = read(BATCH / 'PLAN.json')
    freeze = read(BATCH / 'FOLLOWUP_FREEZE.json')
    check('all_frozen_hashes_match', all(sha(BASE / p) == h for p, h in freeze['source_hashes'].items()), len(freeze['source_hashes']))
    check('fixed_predecessor_revision', plan['queue_snapshot']['source_revision'] == 'cb176a288874bc2d0658c40dfab191a21b30dda4')
    check('all_five_live_and_copied_snapshots_match', len(plan['queue_snapshot']['sources']) == 5 and all(sha(REPO / r['source_path']) == sha(BATCH / r['snapshot_path']) == r['sha256'] for r in plan['queue_snapshot']['sources']))
    check('immutable_survey_scope_hashes_match', all(sha(EXT / p) == h for p, h in plan['immutable_scope_hashes'].items()))
    state = read(BATCH / 'inputs/CONTINUATION_STATE.json')
    current = rows(BATCH / 'inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv')
    previous_selected = rows(BATCH / 'inputs/CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
    master = rows(BATCH / 'inputs/CURRENT_V2_DISPOSITIONS.csv')
    check('predecessor_all336_counts', len(current) == 336 and collections.Counter(r['current_code'] for r in current) == dict(A=142, O=20, U=61, M=19, N=94))
    check('predecessor_selected248_and_reviewed242', len(previous_selected) == 248 and sum(r['current_code'] != 'N' for r in current) == 242)
    older = [r for r in master if r['cohort'] == 'V2_first100']
    check('older333_preserved_scope', len(master) == 669 and len(older) == 333 and collections.Counter(r['current_code'] for r in older) == dict(A=209, O=25, U=95, M=4))
    pending = [r for r in current if r['current_code'] == 'N']
    pending_ids = {r['candidate_id'] for r in pending}
    queue = state['pending_raw_queue']
    main_rows = rows(EXT / 'MAIN100.csv')
    pending_dp = {r['dp_id'] for r in pending}
    expected_exposures = [r for r in main_rows if r['dp_id'] in pending_dp]
    check('exact_remaining_queue94_and37', len(pending_ids) == queue['pending_events'] == 94 and len(expected_exposures) == queue['pending_exposures'] == 37)
    check('queue_source_hash', queue['source_sha256'] == sha(BATCH / 'inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv'))
    check('queue_all_event_identities', queue['events'] == [{k:r[k] for k in ['candidate_id','dp_id','target','source_input_sha256']} for r in pending])
    check('queue_original_MAIN100_exposure_order', [r['dp_id'] for r in queue['exposure_queue']] == [r['dp_id'] for r in expected_exposures])
    for q, row in zip(queue['exposure_queue'], expected_exposures):
        assert q['pending_ids'] == [r['candidate_id'] for r in pending if r['dp_id'] == row['dp_id']]
        assert q['raw_progenitor_id'] == row['raw_progenitor_id'] and q['ancillary_archive_id'] == row['ancillary_archive_id']
    selected = rows(BATCH / 'SELECTED_EXPOSURES.csv')
    events = rows(BATCH / 'SELECTED_EVENTS.csv')
    check('all_remaining_exposures_selected_unchanged', selected == expected_exposures)
    hits = [r for r in rows(EXT / 'production/V2_HITS.csv') if r['dp_id'] in pending_dp]
    check('all94_accepted_V2_events_in_production_order', len(hits) == len(events) == 94 and [r['review_id'] for r in events] == [r['candidate_id'] for r in hits] and {r['review_id'] for r in events} == pending_ids)
    check('no_selected_V1_records', not any(r['dp_id'] in pending_dp for r in rows(EXT / 'production/V1_HITS.csv')))
    science = {r['dp_id']:r for r in read(EXT / 'acquisition/DOWNLOAD_MANIFEST.json')}
    by_id = {r['candidate_id']:r for r in current}
    for e, h in zip(events, hits):
        assert e['dp_id'] == h['dp_id'] == by_id[e['review_id']]['dp_id']
        assert e['source_sha256'] == h['input_sha256'] == by_id[e['review_id']]['source_input_sha256'] == science[e['dp_id']]['sha256']
        assert float(e['fitted_center_bary_air_angstrom']) == float(h['fitted_center_angstrom'])
    check('selected_source_identity_and_centers_match', True)
    check('all37_merged_science_file_hashes_verified_without_arrays', all(sha(BASE / science[r['dp_id']]['relative_path']) == science[r['dp_id']]['sha256'] for r in selected), 37)
    metadata_rows = rows(BASE / 'v2/next_sample/PRODUCT_METADATA.csv')
    provenance = rows(BASE / 'v2/next_sample/RAW_PROVENANCE.csv')
    expected_products = []
    for r in selected:
        parents = [x for x in provenance if x['product_id'] == r['dp_id']]
        companions = [x for x in metadata_rows if x['product_id'] == r['dp_id'] and x['extension'] == 'TAR']
        assert len(parents) == len(companions) == 1
        assert parents[0]['source_file'] == r['raw_progenitor_id']
        assert companions[0]['archive_id'] == r['ancillary_archive_id'] and companions[0]['access_url'] == r['ancillary_source_url']
        expected_products.extend([(r['dp_id'], 'RAW', r['raw_progenitor_id'], r['raw_source_url']), (r['dp_id'], 'ANCILLARY', r['ancillary_archive_id'], r['ancillary_source_url'])])
    check('all74_original_product_identities_unambiguous', len(expected_products) == len({r[2] for r in expected_products}) == 74)
    prior_manifests = [EXT / name / 'products/MANIFEST.json' for name in ['raw_followup','raw_followup_batch02','raw_followup_batch03']]
    prior_products = [r for p in prior_manifests for r in read(p)['products'] if r['status'] == 'DOWNLOADED']
    prior_ids = {r['archive_id'] for r in prior_products}
    selected_ids = {r[2] for r in expected_products}
    check('all112_prior_canonical_products_and56_exposures_considered', len(prior_products) == len(prior_ids) == 112 and len({r['dp_id'] for r in prior_products}) == 56)
    check('no_selected_product_in_prior_canonical_cache', not selected_ids & prior_ids)
    cache = read(BATCH / 'CACHE_CHECK.json')
    check('cache_manifest_matches_independent_count', cache['prior_cached_products'] == 112 and cache['prior_cached_exposures'] == 56 and cache['selected_products'] == 74 and cache['selected_cached_archive_ids'] == [])
    check('cache_source_hashes_match', all(sha(REPO / r['path']) == r['sha256'] for r in cache['prior_manifests']))
    expected_names = {archive.replace(':','_') + ('.fits.Z' if kind == 'RAW' else '.tar')
                      for _, kind, archive, _ in expected_products}
    retained_matches = [str(p.relative_to(REPO)) for p in REPO.rglob('*') if p.is_file() and
                        (p.name in expected_names or any(p.name == name + '.part' or p.name.startswith('.' + name + '.') for name in expected_names))]
    check('no_selected_canonical_or_transient_product_retained_locally', not retained_matches, retained_matches)
    metadata = read(BATCH / 'REMOTE_PRODUCT_METADATA.json')
    check('HEAD_metadata_coverage_and_original_URLs', [(r['dp_id'],r['kind'],r['archive_id'],r['url']) for r in metadata] == expected_products and all(r['url'] == 'https://dataportal.eso.org/dataPortal/file/' + r['archive_id'] for r in metadata))
    cap = 1_600_000_000
    selected_jobs, omitted, charged_plan = [], [], 0
    for r in selected:
        pair = [m for m in metadata if m['dp_id'] == r['dp_id']]
        if len(pair) != 2 or not all(m['metadata_status'] == 'VERIFIED' for m in pair):
            omitted.append(r['dp_id'])
        elif charged_plan + sum(m['advertised_bytes'] for m in pair) > cap:
            omitted.append(r['dp_id'])
        else:
            selected_jobs.extend(pair); charged_plan += sum(m['advertised_bytes'] for m in pair)
    jobs = read(BATCH / 'JOBS.json')
    selection = read(BATCH / 'SELECTION.json')
    check('jobs_are_original_complete_pairs_within_fixed_cap', jobs == selected_jobs and charged_plan <= cap and [r['dp_id'] for r in selection['omitted_pairs']] == omitted)
    check('no_selection_replacements', selection['selection_replacements'] == 0 and selection['selected_V2_events'] == 94 and selection['pending_before'] == 94 and selection['pending_outside_selected'] == 0)
    check('planned_byte_accounting', charged_plan == selection['planned_payload_bytes'] == freeze['planned_payload_bytes'] and len(jobs) == freeze['planned_products'])
    bounds = plan['acquisition_bounds']
    check('fixed_transport_bounds', bounds['payload_cap_bytes'] == cap and bounds['workers'] == 3 and bounds['max_attempts_per_product'] == 2 and bounds['max_raw_products'] == bounds['max_ancillary_products'] == 37 and bounds['replacement_prohibited'] is True)
    identical = ['common.py','extract_native.py','mapping_quality.py','registration.py','local_registration.py','transfer_guards.py']
    check('unchanged_extraction_mapping_and_transport_modules', all((BATCH / p).read_bytes() == (PREVIOUS / p).read_bytes() for p in identical), identical)
    check('plot_label_only_change', (BATCH / 'plot_review.py').read_text() == (PREVIOUS / 'plot_review.py').read_text().replace('batch03','batch04'))
    check('acquisition_capacity_docstring_only_change', (BATCH / 'acquire.py').read_text() == (PREVIOUS / 'acquire.py').read_text().replace('At most32 raw+32 ancillary', 'At most 37 raw + 37 ancillary'))
    check('test_job_capacity_only_change', (BATCH / 'test_transfer_guards.py').read_text() == (PREVIOUS / 'test_transfer_guards.py').read_text().replace('<=64', '<=74'))
    guards = read(BATCH / 'GUARD_TEST_RESULTS.json')
    check('13_actual_job_offline_guards_passed', guards['tests_passed'] == 13 and guards['actual_frozen_jobs_verified'] == len(jobs) and guards['jobs_file_present'] is True and guards['network_calls'] == guards['science_payload_downloads'] == 0)
    check('guard_result_code_hashes_match', guards['script_sha256'] == sha(BATCH/'test_transfer_guards.py') and guards['guards_sha256'] == sha(BATCH/'transfer_guards.py') and guards['acquire_sha256'] == sha(BATCH/'acquire.py'))
    check('no_acquisition_marker_or_product_manifest_before_publication', not (BATCH/'DOWNLOAD_STARTED.json').exists() and not (BATCH/'products/MANIFEST.json').exists())
    check('fixed_all_order_mapping_thresholds', plan['mapping_quality'] == read(PREVIOUS/'PLAN.json')['mapping_quality'])
    check('frozen_hashes_still_unchanged', all(sha(BASE / p) == h for p, h in freeze['source_hashes'].items()))
    report = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), reviewer='Independent batch04_preflight agent', status='PASS_OFFLINE_PREFLIGHT_NO_BLOCKING_FINDINGS', scope='All remaining94 events in37 exposures, all canonical prior caches, original product identities, metadata-only publication preparation and unchanged every-covering-order numerical method. This script makes no network calls and opens no raw/native arrays.', checks_passed=len(checks), checks=checks, selected_exposures=37, selected_events=94, source_science_hashes_verified=37, expected_products=74, accepted_metadata_jobs=len(jobs), verified_metadata_products=sum(r['metadata_status'] == 'VERIFIED' for r in metadata), omitted_pairs=omitted, omitted_event_ids=[r['review_id'] for r in events if r['dp_id'] in omitted], expected_raw_reviewable_events=sum(r['dp_id'] not in omitted for r in events), planned_payload_bytes=charged_plan, fixed_payload_cap_bytes=cap, cached_canonical_products_considered=112, cached_canonical_exposures_considered=56, freeze_sha256=sha(BATCH/'FOLLOWUP_FREEZE.json'), reviewed_file_hashes={str(p.relative_to(BATCH)):sha(p) for p in [BATCH/'PLAN.json',BATCH/'FOLLOWUP_FREEZE.json',BATCH/'JOBS.json',BATCH/'SELECTED_EVENTS.csv',BATCH/'SELECTED_EXPOSURES.csv',BATCH/'GUARD_TEST_RESULTS.json',BATCH/'CACHE_CHECK.json',BATCH/'VISUAL_REVIEW_PLAN.json']}, script_sha256=sha(Path(__file__)), findings=[], blocking_findings=[], root_follow_through=['Publish and independently read back the exact frozen source package before any payload acquisition.', 'Unavailable selected pairs remain N; any unsupported covering order remains M.', 'Only after extraction run independent numerical reconstruction and two separate visual reviews.', 'Preserve all 248 prior selected records, all 242 reviewed new V2 rows and the older333 cohort.', 'Preserve selected records in omitted pairs as N. With the frozen omission unchanged, V2E2-0332 and V2E2-0333 remain pending even if every accepted download succeeds; any later availability attempt requires a separate documented step.'], limitations=['HEAD availability/size claims are checked from receipts, not independently requested again.', 'No new raw arrays or payloads were read. Acquisition and numerical/visual audits remain separate gates.', 'Independent AI/script review is not external or human scientific validation.'])
    (HERE/'PREFLIGHT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','checks_passed','selected_exposures','selected_events','accepted_metadata_jobs','omitted_pairs','planned_payload_bytes','freeze_sha256']},indent=2))


if __name__ == '__main__':
    main()
