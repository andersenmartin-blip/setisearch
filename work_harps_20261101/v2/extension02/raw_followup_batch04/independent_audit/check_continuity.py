"""Independent final continuity audit; reads current science, never rewrites it.

This audit writes only its own report. Local saved ZIPs are required; use
--archive-directory when the recorded scratch paths differ after restoration.
"""
from pathlib import Path
import argparse, collections, csv, datetime, hashlib, json, re, subprocess, urllib.parse
OUT = Path(__file__).resolve().parents[1]
EXT = OUT.parent
BASE = EXT.parents[1]
V2 = BASE/'v2'
REPO = BASE.parent
CURRENT = EXT/'raw_followup'
INPUT = OUT/'inputs'
AUDIT = Path(__file__).resolve().parent
CODES = 'AOUMN'
UNAVAILABLE = {'V2E2-0332', 'V2E2-0333'}
UNAVAILABLE_DP = 'ADP.2023-07-07T01:08:58.252'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024*1024), b''): h.update(block)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def rows(path):
    with Path(path).open(newline='') as handle: return list(csv.DictReader(handle))
def counts(records, key):
    values = collections.Counter(r[key] for r in records)
    return {key: values[key] for key in CODES}
def all_hashes(root, mapping):
    return all((root/path).is_file() and sha(root/path) == value for path, value in mapping.items())
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive-directory', type=Path)
    args = parser.parse_args()
    checks = []; failures = []
    def check(name, ok, detail=None):
        result = dict(name=name, passed=bool(ok))
        if detail is not None: result['detail'] = detail
        checks.append(result)
        if not ok: failures.append(name)
    current = rows(CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
    before = rows(INPUT/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
    master = rows(V2/'CURRENT_V2_DISPOSITIONS.csv')
    prior_master = rows(INPUT/'CURRENT_V2_DISPOSITIONS.csv')
    selected_master = rows(CURRENT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
    prior_selected = rows(INPUT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
    selected = rows(OUT/'SELECTED_EVENTS.csv'); exposures = rows(OUT/'SELECTED_EXPOSURES.csv')
    decisions = rows(OUT/'ADOPTED_DISPOSITIONS.csv'); summary = read(OUT/'SUMMARY.json')
    state = read(OUT/'CONTINUATION_STATE.json'); old_state = read(INPUT/'CONTINUATION_STATE.json')
    current_summary = read(CURRENT/'CURRENT_SUMMARY.json'); status = read(V2/'CURRENT_STATUS.json')
    plan = read(OUT/'PLAN.json')
    old = {r['candidate_id']: r for r in before}; new = {r['candidate_id']: r for r in current}
    by_decision = {r['candidate_id']: r for r in decisions}; selected_ids = {r['review_id'] for r in selected}
    reviewed_ids = selected_ids - UNAVAILABLE
    check('unique_new_cohort_336', len(new) == len(current) == len(old) == len(before) == 336)
    check('unique_combined_master_669', len(master) == len({r['review_id'] for r in master}) == 669)
    check('selected_scope_94_records_37_exposures', len(selected) == len(selected_ids) == len(decisions) == len(by_decision) == 94 and len(exposures) == 37 and set(by_decision) == selected_ids)
    check('all_94_predecessor_N_records_selected', selected_ids == {r['candidate_id'] for r in before if r['current_code'] == 'N'})
    adopted_counts = counts(decisions, 'code')
    expected_new_counts = counts(before, 'current_code')
    for key in selected_ids:
        expected_new_counts[old[key]['current_code']] -= 1
        expected_new_counts[by_decision[key]['code']] += 1
    older = [r for r in master if r['cohort'] == 'V2_first100']; older_before = [r for r in prior_master if r['cohort'] == 'V2_first100']
    expected_all_counts = {key: expected_new_counts[key] + counts(older_before, 'current_code')[key] for key in CODES}
    check('new_counts_match_adopted_overlay', counts(current, 'current_code') == expected_new_counts, counts(current, 'current_code'))
    check('all_counts_match_preserved_older_plus_current_new', counts(master, 'current_code') == expected_all_counts, counts(master, 'current_code'))
    check('adopted_counts_match_summary_and_two_unavailable', adopted_counts == {key: summary['adopted_counts'].get(key, 0) for key in CODES} and adopted_counts['N'] == 2, adopted_counts)
    check('root_adoption_and_numerical_audit_complete', summary['status'] == 'ROOT_ADOPTED_CONSERVATIVE_REVIEW' and summary['root_visual_review_complete'] is True and summary['independent_numeric_audit'] == 'PASS')
    changed = [key for key in old if old[key]['current_code'] != new[key]['current_code']]
    check('exactly_92_available_selected_N_codes_changed', set(changed) == reviewed_ids and all(old[key]['current_code'] == 'N' for key in changed))
    check('all_242_prior_reviewed_new_V2_fields_preserved', sum(r['current_code'] != 'N' for r in before) == 242 and all(all(new[key][field] == value for field, value in r.items()) for key, r in old.items() if r['current_code'] != 'N'))
    check('all_unselected_original_fields_preserved', all(all(new[key][field] == value for field, value in r.items()) for key, r in old.items() if key not in selected_ids))
    mutable = {'current_code', 'current_disposition', 'current_evidence', 'current_evidence_table', 'final_physical_origin_confirmed'}
    check('all_selected_historical_fields_preserved', all(all(new[key][field] == value for field, value in old[key].items() if field not in mutable) for key in selected_ids))
    check('all_94_current_decisions_match_batch_evidence', all(new[key]['current_code'] == by_decision[key]['code'] and new[key]['current_evidence'] == by_decision[key]['evidence'] and new[key]['selected_for_raw_followup_batch04'].lower() == 'true' for key in selected_ids))
    check('unavailable_evidence_preserved_without_reclassification', {key for key, r in by_decision.items() if r['code'] == 'N'} == UNAVAILABLE and all(new[key]['current_code'] == 'N' and new[key]['current_evidence'] for key in UNAVAILABLE))
    check('older_333_master_rows_exactly_preserved', older == older_before and len(older) == 333)
    old_master_by = {r['review_id']: r for r in prior_master}; master_by = {r['review_id']: r for r in master}
    check('all_unselected_combined_master_rows_preserved', all(master_by[key] == r for key, r in old_master_by.items() if key not in selected_ids))
    master_mutable = {'current_code', 'current_disposition', 'final_physical_origin_confirmed'}
    check('selected_combined_master_provenance_preserved', all(all(master_by[key][field] == value for field, value in old_master_by[key].items() if field not in master_mutable) for key in selected_ids))
    check('combined_master_new_cohort_matches_each_current_record', all(master_by[key]['current_code'] == record['current_code'] and master_by[key]['current_disposition'] == record['current_disposition'] and master_by[key]['dp_id'] == record['dp_id'] and master_by[key]['input_sha256'] == record['source_input_sha256'] for key, record in new.items()))
    check('earlier_root_U_decisions_0050_and_0235_preserved', all(new[key]['current_code'] == old[key]['current_code'] == 'U' for key in ['V2E2-0050', 'V2E2-0235']))
    check('all_248_prior_selected_fields_preserved', len(prior_selected) == 248 and all(all(selected_master[index][key] == value for key, value in r.items()) for index, r in enumerate(prior_selected)))
    check('selected_master_exact340_unique_6V1_334V2', len(selected_master) == len({r['review_id'] for r in selected_master}) == 340 and collections.Counter(r['detector'] for r in selected_master) == {'V1': 6, 'V2': 334} and {r['review_id'] for r in selected_master[248:]} == reviewed_ids)
    check('successor_selected_master_invariant', {r['review_id'] for r in selected_master if r['detector'] == 'V2'} == {r['candidate_id'] for r in current if r['current_code'] != 'N'} and not UNAVAILABLE.intersection(r['review_id'] for r in selected_master))
    check('new_reviewed_master_codes_and_evidence_match_each_adoption', all(r['current_code'] == by_decision[r['review_id']]['code'] and r['current_evidence'] == by_decision[r['review_id']]['evidence'] and r['dp_id'] == by_decision[r['review_id']]['dp_id'] for r in selected_master[248:]))
    figure_paths = [r['figure'] for r in selected_master[248:]]
    check('all_92_new_figure_links_point_to_batch04', len(figure_paths) == 92 and all(path.startswith('../raw_followup_batch04/') and (CURRENT/path).is_file() for path in figure_paths))
    evidence_tables = [r['current_evidence_table'] for r in current if r['candidate_id'] in selected_ids]
    check('all_94_batch_evidence_tables_resolve', all(path == '../raw_followup_batch04/ADOPTED_DISPOSITIONS.csv' and (CURRENT/path).is_file() for path in evidence_tables))
    check('current_summary_equals_status', current_summary == status)
    latest = status['latest_raw_batch']
    check('current_summaries_counts_and_latest_batch', status['current_new_V2_counts'] == counts(current, 'current_code') and status['current_all_V2_counts'] == counts(master, 'current_code') and status['V2_raw_reviewed'] == 667 and status['V2_raw_unreviewed'] == 2 and latest['selected_events'] == 94 and latest['selected_exposures'] == 37 and latest['raw_reviewed_events'] == 92 and latest['unavailable_events'] == 2)
    pending = [r for r in current if r['current_code'] == 'N']; queue = []
    for r in rows(EXT/'MAIN100.csv'):
        ids = [item['candidate_id'] for item in pending if item['dp_id'] == r['dp_id']]
        if ids:
            queue.append(dict(dp_id=r['dp_id'], target=r['canonical_target'], selection_index=int(r['selection_index']), pending_ids=ids, raw_progenitor_id=r['raw_progenitor_id'], ancillary_archive_id=r['ancillary_archive_id'], raw_source_url=r['raw_source_url'], ancillary_source_url=r['ancillary_source_url']))
    q = state['pending_raw_queue']
    check('exact_pending_event_queue_0332_0333', q['events'] == [{key: r[key] for key in ['candidate_id', 'dp_id', 'target', 'source_input_sha256']} for r in pending] and [r['candidate_id'] for r in pending] == ['V2E2-0332', 'V2E2-0333'])
    check('exact_MAIN100_pending_exposure_queue', q['exposure_queue'] == queue and len(queue) == 1 and len(pending) == 2)
    check('next_queue_head_0332_HD141937', q['first_event'] == 'V2E2-0332' and q['first_exposure'] == queue[0] and queue[0]['target'] == 'HD141937' and queue[0]['dp_id'] == UNAVAILABLE_DP and queue[0]['selection_index'] == 99 and q['pending_events'] == 2 and q['pending_exposures'] == 1)
    check('queue_source_hash', q['source_sha256'] == sha(CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv'))
    check('concrete_pending_batch05_without_false_completion', state['next_action']['kind'] == 'PREPARE_NEXT_BOUNDED_RAW_BATCH' and state['next_action']['directory_to_create'].endswith('/raw_followup_batch05') and state['next_action']['queue_head'] == 'V2E2-0332' and state['science']['raw_review_complete'] is False)
    check('state_unresolved_and_limited_IDs_exact', state['science']['new_V2_unresolved_ids'] == [r['candidate_id'] for r in current if r['current_code'] == 'U'] and state['science']['new_V2_mapping_limited_ids'] == [r['candidate_id'] for r in current if r['current_code'] == 'M'])
    followup = state['followup_queues']; followup_ok = followup['source_sha256'] == sha(V2/'CURRENT_V2_DISPOSITIONS.csv')
    for label, code in [('mapping_limited', 'M'), ('unresolved_structure', 'U')]:
        expected = [r['review_id'] for r in master if r['current_code'] == code]
        actual = followup[label]
        followup_ok = followup_ok and actual['events'] == len(expected) and [r['review_id'] for r in actual['records']] == expected and actual['first_event'] == (expected[0] if expected else None)
        for record in actual['records']:
            followup_ok = followup_ok and record['input_sha256'] == master_by[record['review_id']]['input_sha256'] and (REPO/record['current_evidence_table']).is_file()
    check('exact_stable_M_U_followup_queues_both_cohorts', followup_ok)
    check('followup_priorities_preserved', [r['queue'] for r in followup['priorities']] == ['mapping_limited', 'unresolved_structure'])
    check('survey_scope_and_completed_epoch_state_preserved', all(state['science'][key] == old_state['science'][key] for key in ['main_exposures', 'main_targets', 'main_exposure_seconds', 'main_exposure_hours', 'V1_exposures', 'V1_hits', 'V2_exposures', 'V2_events', 'new_V2_events']) and state['completed_epoch_comparison'] == old_state['completed_epoch_comparison'] and state['independent_epoch_audit'] == old_state['independent_epoch_audit'])
    frozen = read(OUT/'FOLLOWUP_FREEZE.json'); prereg = read(OUT/'PREREGISTRATION_RECEIPT.json')
    check('all_33_frozen_source_hashes_and_prereg_freeze', len(frozen['source_hashes']) == 33 and all_hashes(BASE, frozen['source_hashes']) and prereg['freeze_sha256'] == sha(OUT/'FOLLOWUP_FREEZE.json'), len(frozen['source_hashes']))
    check('all_current_state_source_hashes', all_hashes(REPO, state['source_hashes']), len(state['source_hashes']))
    check('all_current_summary_source_hashes', all_hashes(V2, current_summary['source_hashes']), len(current_summary['source_hashes']))
    check('all_adoption_summary_source_hashes', all_hashes(OUT, summary['source_hashes']), len(summary['source_hashes']))
    check('latest_batch_summary_and_adopted_hashes', latest['summary_sha256'] == sha(OUT/'SUMMARY.json') and latest['adopted_dispositions_sha256'] == sha(OUT/'ADOPTED_DISPOSITIONS.csv'))
    primary = read(OUT/'PRIMARY_VISUAL_REVIEW.json'); secondary = read(OUT/'SECONDARY_VISUAL_REVIEW.json')
    primary_records = primary.get('events', primary.get('records', []))
    secondary_records = secondary.get('events', secondary.get('records', []))
    pa = {r['review_id']: r for r in primary_records}; sa = {r['review_id']: r for r in secondary_records}
    check('both_visual_reviews_cover_all94_records', len(primary_records) == len(secondary_records) == 94 and set(pa) == set(sa) == selected_ids)
    root_adjudication = read(OUT/'ROOT_ADJUDICATION.json'); adjudications = {r['review_id']: r for r in root_adjudication['adjudications']}
    disagreements = {key for key in selected_ids if pa[key]['code'] != sa[key]['code']}
    check('all_review_disagreements_have_explicit_root_decisions', disagreements <= set(adjudications) <= selected_ids and root_adjudication['root_visual_review_complete'] is True, sorted(disagreements))
    check('every_adopted_code_matches_agreement_or_explicit_adjudication', all(by_decision[key]['code'] == adjudications[key]['code'] if key in adjudications else by_decision[key]['code'] == pa[key]['code'] == sa[key]['code'] for key in selected_ids))
    review_hash_count = 0; review_hash_pass = True
    for report in [primary, secondary, root_adjudication]:
        for name in ['source_sha256', 'source_hashes', 'figure_sha256', 'review_sha256']:
            hashes = report.get(name, {})
            review_hash_count += len(hashes)
            review_hash_pass = review_hash_pass and all_hashes(OUT, hashes)
    check('review_and_root_evidence_hashes', review_hash_pass, review_hash_count)
    mapping_data = read(OUT/'NATIVE_MAPPING.json')
    mapping = {r['review_id']: r for r in mapping_data['events']}
    expected_cutouts = sorted((r['review_id'], r['order'], r['cutout'], r['cutout_sha256']) for r in mapping_data['orders'] if r['status'] == 'EXTRACTED')
    declared_secondary_cutouts = secondary.get('extracted_orders_reviewed')
    secondary_cutouts_ok = isinstance(declared_secondary_cutouts, list) and secondary.get('extracted_orders_reviewed_count') == len(expected_cutouts) == 122
    if secondary_cutouts_ok:
        secondary_cutouts_ok = sorted((r['review_id'], r['order'], r['cutout'], r['cutout_sha256']) for r in declared_secondary_cutouts) == expected_cutouts
    check('secondary_122_explicit_cutout_id_order_path_hash_records_match_mapping', secondary_cutouts_ok)
    check('primary_available_cutout_and_edge_counts_match_mapping', primary['extracted_order_cutouts_inspected'] == len(expected_cutouts) == 122 and primary['covering_order_records'] == len(mapping_data['orders']) == 124 and primary['missing_full_cutouts'] == 2 and primary['unavailable_events'] == 2)
    expected_pages = sorted({r['page'] for r in read(OUT/'FIGURE_INDEX.json')})
    check('both_reviews_cover_all_atlas_pages', primary['atlas_pages_inspected'] == secondary['atlas_pages_inspected'] == expected_pages)
    expected_orders_by_id = {key: sorted(r['order'] for r in mapping_data['orders'] if r['review_id'] == key and r['status'] == 'EXTRACTED') for key in selected_ids}
    record_mapping_ok = True
    for report_records in [primary_records, secondary_records]:
        for record in report_records:
            key = record['review_id']; mapped = mapping[key]
            record_mapping_ok = record_mapping_ok and record['dp_id'] == by_decision[key]['dp_id'] and record['covering_orders'] == mapped['covering_orders'] and record['all_covering_orders_mapping_verified'] == mapped['mapping_supported']
            seen = record.get('orders_seen', record.get('extracted_orders_reviewed'))
            if seen is not None:
                record_mapping_ok = record_mapping_ok and sorted(seen) == expected_orders_by_id[key]
    check('both_reviews_per_record_exposure_order_mapping_accounting_matches', record_mapping_ok)
    unavailable_mapping = {key for key, r in mapping.items() if r['status'] == 'NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE'}
    limited_mapping = {key for key, r in mapping.items() if not r['mapping_supported'] and key not in unavailable_mapping}
    check('exact12_M_and2_N_mapping_outcomes_preserved', set(mapping) == selected_ids and unavailable_mapping == UNAVAILABLE and len(limited_mapping) == 12 and limited_mapping == {key for key, r in by_decision.items() if r['code'] == 'M'})
    numeric = read(OUT/'independent_audit/SUMMARY.json')
    check('numerical_audit_still_valid', numeric['status'] == 'PASS' and numeric['completed_exposures'] == 36 and numeric['unavailable_exposures'] == 1 and all_hashes(OUT, numeric['source_hashes']))
    helper_validation = read(OUT/'CONTINUITY_HELPER_VALIDATION.json')
    check('administrative_N_fix_documented_and_validated', helper_validation['status'] == 'PASS_SYNTHETIC_HELPER_VALIDATION_ONLY' and helper_validation['tests_passed'] >= 24 and helper_validation['script_sha256'] == sha(OUT/'update_current.py') and helper_validation['followup_freeze_sha256'] == sha(OUT/'FOLLOWUP_FREEZE.json') and helper_validation['frozen_omission_fixture']['selected_rows'] == 340 and bool(helper_validation['administrative_change']))
    check('no_final_physical_origin_claims', all(r['final_physical_origin_confirmed'].lower() == 'false' for r in decisions) and summary['all_origins_provisional'] is True and summary['qualified_laser_candidates'] == 0)
    checkpoint = read(OUT/'checkpoints/LIBRARY_INPUTS.json'); archives = checkpoint['archives']; input_manifest = read(OUT/'checkpoints/INPUT_ARCHIVES.json')
    check('all25_archive_identities_unique_and_prior16_preserved', len(state['input_archives']) == 25 and len({r['library_file_id'] for r in state['input_archives']}) == 25 and state['input_archives'][:len(old_state['input_archives'])] == old_state['input_archives'] and len(old_state['input_archives']) == 16)
    check('new9_archive_metadata_saved_and_in_state', len(archives) == 9 and state['input_archives'][16:] == archives and all(r['status'] == 'succeeded' and r['local_metadata_applied'] is True and r['library_url'] == 'https://chatgpt.com/library?file_id=' + r['library_file_id'] + '&account_id=personal' for r in archives))
    check('input_manifest_hash_matches', checkpoint['input_archives_manifest_sha256'] == sha(OUT/'checkpoints/INPUT_ARCHIVES.json'))
    check('new9_archive_metadata_matches_packaging', len(input_manifest['archives']) == 9 and all(all(a[key] == b[key] for key in ['filename', 'bytes', 'sha256', 'products', 'complete_exposures']) for a, b in zip(archives, input_manifest['archives'])))
    local_zip_checks = []
    for record in input_manifest['archives']:
        path = args.archive_directory/record['filename'] if args.archive_directory else Path(record['local_path'])
        actual_size = path.stat().st_size if path.is_file() else None
        actual_hash = sha(path) if path.is_file() else None
        local_zip_checks.append(dict(filename=record['filename'], local_path=str(path), bytes=actual_size, sha256=actual_hash, passed=actual_size == record['bytes'] and actual_hash == record['sha256']))
    check('all9_local_saved_archive_hashes_and_sizes', all(r['passed'] for r in local_zip_checks), len(local_zip_checks))
    archive_products = [product for archive in archives for product in archive['products']]
    manifest = read(OUT/'products/MANIFEST.json'); product_by = {r['relative_path']: r for r in manifest['products']}
    check('new_archives_cover_exact72_canonical_products', len(archive_products) == len({r['relative_path'] for r in archive_products}) == len(product_by) == 72 and {r['relative_path'] for r in archive_products} == set(product_by) and all(all(r[key] == product_by[r['relative_path']][key] for key in ['sha256', 'bytes', 'dp_id', 'archive_id', 'kind']) for r in archive_products))
    check('all36_canonical_pairs_complete', len({r['dp_id'] for r in archive_products}) == 36 and all(collections.Counter(r['kind'] for r in archive_products if r['dp_id'] == dp) == {'RAW': 1, 'ANCILLARY': 1} for dp in {r['dp_id'] for r in archive_products}) and all(r['status'] == 'DOWNLOADED' for r in manifest['products']))
    check('no_noncanonical_payload_archive_members', not any(r['relative_path'].endswith('.part') or Path(r['relative_path']).name.startswith('.') for r in archive_products) and input_manifest['residual_part_files_included'] == 0 and input_manifest['noncanonical_payload_files_included'] == 0)
    check('unavailable_pair_excluded_but_metadata_retained', len(input_manifest['excluded_pairs']) == 1 and input_manifest['excluded_pairs'][0]['dp_id'] == UNAVAILABLE_DP and not any(r['dp_id'] == UNAVAILABLE_DP for r in archive_products))
    evidence = read(OUT/'EVIDENCE_ARCHIVE.json'); parts = read(OUT/'EVIDENCE_PARTS.json'); restored = read(OUT/'EVIDENCE_RESTORE_VALIDATION.json')
    check('evidence_manifest_and_restore_receipt_agree', parts['archive_manifest_sha256'] == sha(OUT/'EVIDENCE_ARCHIVE.json') and evidence['sha256'] == parts['sha256'] == restored['archive_sha256'] and evidence['bytes'] == parts['bytes'] == restored['archive_bytes'] and evidence['member_count'] == restored['member_count'] == 158 and evidence['native_cutouts'] == 122 and evidence['reference_grids'] == 36 and restored['status'] == 'PASS')
    check('all_evidence_parts_hashes_and_lengths', all((OUT/r['path']).stat().st_size == r['bytes'] and sha(OUT/r['path']) == r['sha256'] for r in parts['parts']) and sum(r['bytes'] for r in parts['parts']) == parts['bytes'])
    # Current root header is audited; unchanged historical archive links are out of scope.
    root_text = (REPO/'README.md').read_text(); predecessor = plan['queue_snapshot']['source_revision']
    old_root = subprocess.check_output(['git', 'show', predecessor + ':README.md'], cwd=REPO).decode()
    root_prefix = root_text[:-len(old_root)] if root_text.endswith(old_root) else root_text
    check('root_historical_README_unchanged', root_text.endswith(old_root))
    docs = [(REPO/'README.md', root_prefix), (REPO/'CONTINUE_SETI.md', (REPO/'CONTINUE_SETI.md').read_text()), (V2/'RESTORE.md', (V2/'RESTORE.md').read_text()), (CURRENT/'CURRENT_RESULTS.md', (CURRENT/'CURRENT_RESULTS.md').read_text()), (OUT/'README.md', (OUT/'README.md').read_text()), (OUT/'checkpoints/SAVED_INPUTS.md', (OUT/'checkpoints/SAVED_INPUTS.md').read_text())]
    links = []; broken = []
    for file, content in docs:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', content):
            target = target.strip().split(' "')[0].strip('<>')
            if not target or target.startswith(('#', 'http:', 'https:', 'mailto:')): continue
            relative = urllib.parse.unquote(target.split('#', 1)[0]); path = (file.parent/relative).resolve()
            links.append(dict(source=str(file.relative_to(REPO)), target=target))
            if not path.exists(): broken.append(links[-1])
    check('all_current_documentation_relative_links_resolve', not broken, dict(checked=len(links), broken=broken))
    check('root_current_header_counts_and_next_record', all(token in root_prefix for token in ['94', '37', '667', '669', 'V2E2-0332']) and 'raw_followup_batch04' in root_prefix)
    publication = state['publication']; publication_state = publication['state']
    if publication_state == 'AWAITING_FINAL_PUBLICATION_READBACK':
        publication_ok = publication['publication_success_must_be_verified_separately'] is True
    elif publication_state == 'PUBLISHED_AND_REMOTE_READBACK_VERIFIED':
        receipt_path = REPO/publication['receipt']
        publication_ok = publication['publication_success_must_be_verified_separately'] is False and receipt_path.is_file()
        if publication_ok:
            receipt = read(receipt_path)
            publication_ok = receipt.get('status') == 'PUBLISHED_AND_REMOTE_READBACK_VERIFIED'
            if publication.get('receipt_sha256'): publication_ok = publication_ok and sha(receipt_path) == publication['receipt_sha256']
    else: publication_ok = False
    check('publication_state_is_explicit_and_locally_consistent', publication_ok, publication_state)
    check('no_unattended_worker_claim', state['execution']['active_science_workers'] == 0 and state['execution']['automatic_background_search'] is False)
    audited = [OUT/'CONTINUATION_STATE.json', OUT/'SUMMARY.json', OUT/'ADOPTED_DISPOSITIONS.csv', CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv', CURRENT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv', V2/'CURRENT_V2_DISPOSITIONS.csv', CURRENT/'CURRENT_SUMMARY.json', V2/'CURRENT_STATUS.json', REPO/'README.md', REPO/'CONTINUE_SETI.md', V2/'RESTORE.md', OUT/'README.md', OUT/'checkpoints/LIBRARY_INPUTS.json', OUT/'CONTINUITY_HELPER_VALIDATION.json']
    result = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='PASS' if not failures else 'FAIL', scope='Independent continuity, provenance, metadata and documentation audit; not a new raw-array or morphology review.', checks_passed=sum(r['passed'] for r in checks), checks_total=len(checks), blocking_findings=failures, checks=checks, script_sha256=sha(Path(__file__)), audited_file_hashes={str(path.relative_to(REPO)): sha(path) for path in audited}, local_zip_checks=local_zip_checks, limits='GitHub publication remains a separate root readback gate. Only the newly prepended current root README header is link-audited; unchanged historical archive links are not revalidated. Library persistence status comes from saved successful receipts; this audit independently verifies local archive hashes and published metadata, not remote Library bytes. Local archive restoration can use --archive-directory.')
    (AUDIT/'CONTINUITY_AUDIT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], checks_passed=result['checks_passed'], checks_total=result['checks_total'], blocking_findings=failures, relative_links_checked=len(links), report=str((AUDIT/'CONTINUITY_AUDIT.json').relative_to(REPO))), indent=2))
    if failures: raise SystemExit(1)

if __name__ == '__main__': main()
