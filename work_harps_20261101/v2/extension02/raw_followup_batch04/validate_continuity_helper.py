"""Isolated continuity fixtures, never scientific classifications or live updates.

Exercise completed and unavailable-product outcomes plus preservation/concurrency
contracts. Synthetic evidence is created only in a TemporaryDirectory.
"""
from pathlib import Path
import collections, csv, hashlib, json, shutil, subprocess, sys, tempfile
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[3]
BASE_REL = Path('work_harps_20261101')
BATCH_REL = OUT.relative_to(REPO)

def read(path): return json.loads(path.read_text())
def rows(path):
    with path.open(newline='') as handle: return list(csv.DictReader(handle))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
def write_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dict.fromkeys(k for r in records for k in r)))
        writer.writeheader(); writer.writerows(records)

def main():
    plan = read(OUT/'PLAN.json'); old_summary = read(OUT/'inputs/CURRENT_SUMMARY.json')
    state = read(OUT/'inputs/CONTINUATION_STATE.json'); n = plan['selection_rule']['max_unique_exposures']
    queue = state['pending_raw_queue']['exposure_queue'][:n]
    selected_ids = [key for exposure in queue for key in exposure['pending_ids']]
    assert len(selected_ids) == 94 and len(queue) == 37
    main_by = {r['dp_id']: r for r in rows(REPO/BASE_REL/'v2/extension02/MAIN100.csv')}
    hit_by = {r['candidate_id']: r for r in rows(REPO/BASE_REL/'v2/extension02/production/V2_HITS.csv')}
    live_paths = [REPO/rel for rel in state['source_hashes']]
    actual_freeze = read(OUT/'FOLLOWUP_FREEZE.json') if (OUT/'FOLLOWUP_FREEZE.json').exists() else None
    if actual_freeze:
        assert str((OUT/'update_current.py').relative_to(REPO/BASE_REL)) not in actual_freeze['source_hashes']
        live_paths += [OUT/'FOLLOWUP_FREEZE.json'] + [REPO/BASE_REL/rel for rel in actual_freeze['source_hashes']]
    live_hashes = {str(p): sha(p) for p in live_paths}
    tests = []; scenarios = {}
    with tempfile.TemporaryDirectory(prefix='seti_batch04_continuity_') as temp:
        root = Path(temp); out = root/BATCH_REL; out.mkdir(parents=True)
        required = {Path(rel) for rel in state['source_hashes']}
        required.update(BASE_REL/'v2'/rel for rel in old_summary['source_hashes'])
        required.update([BASE_REL/'v2/extension02/MAIN100.csv', BASE_REL/'v2/extension02/production/V2_HITS.csv'])
        for rel in required:
            p = root/rel; p.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(REPO/rel, p)
        shutil.copy2(OUT/'update_current.py', out/'update_current.py')
        shutil.copy2(OUT/'PLAN.json', out/'PLAN.json')
        shutil.copytree(OUT/'inputs', out/'inputs')
        # Required current files are restored from the frozen predecessor each time.
        v2 = root/BASE_REL/'v2'; current = v2/'extension02/raw_followup'
        protected = [current/'CURRENT_V2_ALL336_DISPOSITIONS.csv', current/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',
                     current/'CURRENT_SUMMARY.json', v2/'CURRENT_STATUS.json', v2/'CURRENT_V2_DISPOSITIONS.csv']
        def reset_current():
            for name in ['CURRENT_V2_ALL336_DISPOSITIONS.csv', 'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv', 'CURRENT_SUMMARY.json']:
                shutil.copy2(out/'inputs'/name, current/name)
            shutil.copy2(out/'inputs/CURRENT_SUMMARY.json', v2/'CURRENT_STATUS.json')
            shutil.copy2(out/'inputs/CURRENT_V2_DISPOSITIONS.csv', v2/'CURRENT_V2_DISPOSITIONS.csv')
        reset_current()
        selection = []
        for key in selected_ids:
            h = hit_by[key]
            selection.append(dict(detector='V2', review_id=key, candidate_id=key, dp_id=h['dp_id'],
                                  target=h['canonical_target'], source_sha256=h['input_sha256']))
        write_csv(out/'SELECTED_EVENTS.csv', selection)
        write_csv(out/'SELECTED_EXPOSURES.csv', [main_by[r['dp_id']] for r in queue])
        (out/'figures').mkdir(); (out/'figures/SYNTHETIC.png').write_bytes(b'SYNTHETIC_FIXTURE_NOT_A_SCIENTIFIC_IMAGE')
        # A local README models the root's later report without changing the live report.
        (out/'README.md').write_text('Synthetic continuity fixture only.\n')
        freeze_paths = [out/'PLAN.json', out/'SELECTED_EVENTS.csv', out/'SELECTED_EXPOSURES.csv', out/'update_current.py'] + list((out/'inputs').glob('*'))
        write_json(out/'FOLLOWUP_FREEZE.json', dict(status='SYNTHETIC_TEST_FREEZE', source_hashes={str(p.relative_to(root/BASE_REL)): sha(p) for p in freeze_paths}))
        def set_decisions(overrides=None):
            overrides = overrides or {}; mapping = []; decisions = []
            for r in selection:
                code = overrides.get(r['review_id'], 'U'); supported = code not in ('M', 'N')
                mapping.append(dict(review_id=r['review_id'], mapping_supported=supported,
                    status='NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE' if code == 'N' else 'NATIVE_CONTEXT_EXTRACTED'))
                decisions.append(dict(candidate_id=r['review_id'], dp_id=r['dp_id'], code=code,
                    evidence='Synthetic continuity fixture, not a scientific disposition.',
                    all_covering_orders_mapping_verified=supported,
                    figure='' if code == 'N' else 'figures/SYNTHETIC.png'))
            write_json(out/'NATIVE_MAPPING.json', dict(events=mapping))
            write_json(out/'independent_audit/SUMMARY.json', dict(status='PASS',
                source_hashes={'NATIVE_MAPPING.json': sha(out/'NATIVE_MAPPING.json')}, scope='SYNTHETIC CONTINUITY FIXTURE ONLY'))
            write_csv(out/'ADOPTED_DISPOSITIONS.csv', decisions)
            write_json(out/'SUMMARY.json', dict(created_utc='2000-01-01T00:00:00+00:00',
                status='ROOT_ADOPTED_CONSERVATIVE_REVIEW', selected_events=len(selection), selected_exposures=len(queue),
                independent_numeric_audit='PASS', root_visual_review_complete=True, original_production_unchanged=True,
                adopted_counts=dict(collections.Counter(r['code'] for r in decisions)),
                source_hashes={'ADOPTED_DISPOSITIONS.csv': sha(out/'ADOPTED_DISPOSITIONS.csv')},
                scope='SYNTHETIC CONTINUITY FIXTURE ONLY'))
        def run(*args, ok=True):
            result = subprocess.run([sys.executable, str(out/'update_current.py'), *args], capture_output=True, text=True)
            if ok and result.returncode: raise RuntimeError(result.stderr)
            if not ok:
                assert result.returncode != 0; return result
            return json.loads(result.stdout)
        def verify_source_hashes():
            updated = read(out/'CONTINUATION_STATE.json')
            for rel, expected in updated['source_hashes'].items(): assert sha(root/rel) == expected, rel
            return updated
        set_decisions()
        before_hashes = {str(p): sha(p) for p in protected}
        dry = run(); assert dry['mode'] == 'DRY_RUN' and before_hashes == {str(p): sha(p) for p in protected}
        tests.append('default_dry_run_changes_no_current_tables')
        applied = run('--apply'); scenarios['all_94_synthetic_U'] = applied
        assert applied['new_counts'] == {'A': 142, 'O': 20, 'U': 155, 'M': 19, 'N': 0}
        assert applied['all_counts'] == {'A': 351, 'O': 45, 'U': 250, 'M': 23, 'N': 0}
        tests.append('all_remaining_records_can_complete_without_changing_cohort_coverage')
        assert applied['selected_rows'] == 342 and applied['pending_events'] == applied['pending_exposures'] == 0 and applied['next_event'] is None
        tests.append('complete_342_record_selected_master_and_empty_raw_queue')
        old_master = rows(out/'inputs/CURRENT_V2_DISPOSITIONS.csv'); new_master = rows(v2/'CURRENT_V2_DISPOSITIONS.csv')
        assert [r for r in old_master if r['cohort'] == 'V2_first100'] == [r for r in new_master if r['cohort'] == 'V2_first100']
        tests.append('all_333_older_master_rows_exactly_preserved')
        old_selected = rows(out/'inputs/CURRENT_SELECTED_EVENT_DISPOSITIONS.csv'); new_selected = rows(current/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
        assert len(old_selected) == 248 and all(all(new_selected[i][k] == v for k, v in r.items()) for i, r in enumerate(old_selected))
        tests.append('all_248_predecessor_selected_fields_preserved')
        before = rows(out/'inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv'); after = rows(current/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
        assert all(all(old[k] == new[k] for k in old) for old, new in zip(before, after) if old['candidate_id'] not in selected_ids)
        assert sum(r['current_code'] != 'N' for r in before) == 242
        tests.append('all_242_previous_new_V2_rows_preserved')
        after_by = {r['candidate_id']: r for r in after}
        assert all(after_by[k]['current_code'] == 'U' for k in ['V2E2-0050', 'V2E2-0235'])
        tests.append('earlier_root_conservative_decisions_0050_and_0235_preserved')
        assert all(r['figure'].startswith('../raw_followup_batch04/') for r in new_selected[len(old_selected):])
        tests.append('new_evidence_figures_resolve_under_correct_batch')
        updated = verify_source_hashes(); tests.append('all_source_hashes_valid_after_document_render')
        assert updated['science']['raw_review_complete'] is True
        assert updated['next_action']['kind'] == 'FOLLOW_UP_UNRESOLVED_CASES'
        assert updated['next_action']['directory_to_create'] is None and updated['next_action']['queue_head'] is None
        assert 'raw_followup_batch05' not in (root/'CONTINUE_SETI.md').read_text()
        tests.append('empty_queue_transitions_to_followup_without_an_empty_raw_batch')
        for label, code in [('mapping_limited', 'M'), ('unresolved_structure', 'U')]:
            expected = [r['review_id'] for r in new_master if r['current_code'] == code]
            actual = updated['followup_queues'][label]
            assert actual['events'] == len(expected) and [r['review_id'] for r in actual['records']] == expected
            assert actual['first_event'] == expected[0]
        assert updated['followup_queues']['mapping_limited']['events'] == 23
        assert updated['followup_queues']['unresolved_structure']['events'] == 250
        assert [r['queue'] for r in updated['followup_queues']['priorities']] == ['mapping_limited', 'unresolved_structure']
        tests.append('both_cohorts_have_complete_stable_U_M_queues_and_explicit_priorities')
        assert updated['science']['main_exposures'] == 300 and updated['science']['main_targets'] == 20
        assert updated['science']['V1_hits'] == 22 and updated['science']['V2_events'] == 669
        assert updated['completed_epoch_comparison'] == state['completed_epoch_comparison']
        assert updated['independent_epoch_audit'] == state['independent_epoch_audit']
        tests.append('survey_and_completed_epoch_context_unchanged')
        outputs = [root/p for p in applied['output_files']]; first_hashes = {str(p): sha(p) for p in outputs}
        run('--apply'); assert first_hashes == {str(p): sha(p) for p in outputs}
        tests.append('identical_reapplication_is_byte_identical')
        for p in protected:
            saved = p.read_bytes(); p.write_bytes(saved + b'CONCURRENT_CHANGE\n')
            failed = run('--apply', ok=False); assert 'Current file differs' in failed.stderr; p.write_bytes(saved)
        tests.append('all_five_live_table_concurrency_conflicts_rejected')
        figure = out/'figures/SYNTHETIC.png'; saved = figure.read_bytes(); figure.unlink()
        failed = run(ok=False); assert 'Adopted figure is missing' in failed.stderr; figure.write_bytes(saved)
        tests.append('missing_adopted_figure_rejected')
        evidence = out/'ADOPTED_DISPOSITIONS.csv'; saved = evidence.read_bytes(); evidence.write_bytes(saved + b'CHANGED\n')
        failed = run(ok=False); assert 'Changed adopted evidence' in failed.stderr; evidence.write_bytes(saved)
        tests.append('changed_root_adopted_evidence_rejected')
        # One unavailable complete exposure must remain on the N queue.
        reset_current(); missing_ids = queue[0]['pending_ids']; set_decisions({k: 'N' for k in missing_ids})
        partial = run('--apply'); scenarios['first_exposure_unavailable'] = partial
        assert partial['pending_events'] == len(missing_ids) == 1 and partial['pending_exposures'] == 1
        assert partial['next_event'] == missing_ids[0] == 'V2E2-0243'
        updated = verify_source_hashes()
        assert updated['science']['raw_review_complete'] is False
        assert updated['next_action']['kind'] == 'PREPARE_NEXT_BOUNDED_RAW_BATCH'
        assert updated['next_action']['queue_head'] == missing_ids[0]
        assert updated['pending_raw_queue']['exposure_queue'][0]['dp_id'] == queue[0]['dp_id']
        assert updated['followup_queues']['unresolved_structure']['events'] == 249
        tests.append('unavailable_pair_remains_N_with_exact_resume_queue_and_no_fake_completion')
        partial_master = rows(current/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
        partial_new = rows(current/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
        assert partial['selected_rows'] == len(partial_master) == 341
        assert {r['review_id'] for r in partial_master if r['detector'] == 'V2'} == {r['candidate_id'] for r in partial_new if r['current_code'] != 'N'}
        assert not set(missing_ids).intersection(r['review_id'] for r in partial_master)
        assert len(rows(out/'ADOPTED_DISPOSITIONS.csv')) == 94
        retained = [r for r in partial_new if r['candidate_id'] in missing_ids]
        assert len(retained) == 1 and all(r['current_code'] == 'N' and r['selected_for_raw_followup_batch04'] == 'True' and r['current_evidence'] for r in retained)
        assert all(all(partial_master[i][k] == value for k, value in record.items()) for i, record in enumerate(old_selected))
        tests.append('unavailable_records_keep_batch_evidence_but_are_excluded_from_cumulative_raw_review_master')
        # Run a real successor helper in another isolated batch using the produced
        # predecessor state. The old implementation failed its selected-ID invariant.
        retry = root/BASE_REL/'v2/extension02/raw_followup_batch05'; (retry/'inputs').mkdir(parents=True)
        shutil.copy2(out/'update_current.py', retry/'update_current.py')
        for name in ['CURRENT_V2_ALL336_DISPOSITIONS.csv', 'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv', 'CURRENT_SUMMARY.json']:
            shutil.copy2(current/name, retry/'inputs'/name)
        shutil.copy2(v2/'CURRENT_V2_DISPOSITIONS.csv', retry/'inputs/CURRENT_V2_DISPOSITIONS.csv')
        shutil.copy2(out/'CONTINUATION_STATE.json', retry/'inputs/CONTINUATION_STATE.json')
        retry_plan = read(out/'PLAN.json')
        retry_plan['selection_rule'].update(expected_V2_events=len(missing_ids), max_unique_exposures=1)
        write_json(retry/'PLAN.json', retry_plan)
        retry_selection = [r for r in selection if r['review_id'] in missing_ids]
        assert [r['review_id'] for r in retry_selection] == [r['candidate_id'] for r in updated['pending_raw_queue']['events']]
        write_csv(retry/'SELECTED_EVENTS.csv', retry_selection)
        write_csv(retry/'SELECTED_EXPOSURES.csv', [main_by[queue[0]['dp_id']]])
        (retry/'figures').mkdir(); shutil.copy2(out/'figures/SYNTHETIC.png', retry/'figures/SYNTHETIC.png')
        write_json(retry/'NATIVE_MAPPING.json', dict(events=[dict(review_id=k, mapping_supported=True, status='NATIVE_CONTEXT_EXTRACTED') for k in missing_ids]))
        write_json(retry/'independent_audit/SUMMARY.json', dict(status='PASS', source_hashes={'NATIVE_MAPPING.json': sha(retry/'NATIVE_MAPPING.json')}, scope='SYNTHETIC SUCCESSOR FIXTURE ONLY'))
        write_csv(retry/'ADOPTED_DISPOSITIONS.csv', [dict(candidate_id=r['review_id'], dp_id=r['dp_id'], code='U', evidence='Synthetic retry fixture, not a scientific disposition.', all_covering_orders_mapping_verified=True, figure='figures/SYNTHETIC.png') for r in retry_selection])
        write_json(retry/'SUMMARY.json', dict(created_utc='2000-01-02T00:00:00+00:00', status='ROOT_ADOPTED_CONSERVATIVE_REVIEW', selected_events=len(missing_ids), selected_exposures=1, independent_numeric_audit='PASS', root_visual_review_complete=True, original_production_unchanged=True, adopted_counts={'U': len(missing_ids)}, source_hashes={'ADOPTED_DISPOSITIONS.csv': sha(retry/'ADOPTED_DISPOSITIONS.csv')}, scope='SYNTHETIC SUCCESSOR FIXTURE ONLY'))
        retry_freeze = [retry/'PLAN.json', retry/'SELECTED_EVENTS.csv', retry/'SELECTED_EXPOSURES.csv'] + list((retry/'inputs').glob('*'))
        write_json(retry/'FOLLOWUP_FREEZE.json', dict(status='SYNTHETIC_SUCCESSOR_FREEZE', source_hashes={str(p.relative_to(root/BASE_REL)): sha(p) for p in retry_freeze}))
        retried = subprocess.run([sys.executable, str(retry/'update_current.py'), '--apply'], capture_output=True, text=True)
        assert retried.returncode == 0, retried.stderr
        retry_result = json.loads(retried.stdout)
        assert retry_result['pending_events'] == 0 and retry_result['selected_rows'] == 342
        successor_master = rows(current/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
        assert len(successor_master) == len({r['review_id'] for r in successor_master}) == 342
        assert all(all(successor_master[i][k] == value for k, value in record.items()) for i, record in enumerate(partial_master))
        tests.append('successor_can_select_only_pending_raw_retry_and_append_it_once_without_invariant_failure')
        # Match the actual frozen HEAD omission as a two-record administrative fixture.
        actual_selection = read(OUT/'SELECTION.json') if (OUT/'SELECTION.json').exists() else None
        omitted_dps = {r['dp_id'] for r in actual_selection['omitted_pairs']} if actual_selection else set()
        omitted_ids = [r['review_id'] for r in selection if r['dp_id'] in omitted_dps]
        if omitted_ids:
            reset_current(); set_decisions({key: 'N' for key in omitted_ids}); omitted = run('--apply')
            assert omitted['selected_rows'] == 248 + 94 - len(omitted_ids)
            assert omitted['pending_events'] == len(omitted_ids) and omitted['pending_exposures'] == len(omitted_dps)
            omitted_state = verify_source_hashes()
            assert [r['candidate_id'] for r in omitted_state['pending_raw_queue']['events']] == omitted_ids
            omitted_master = rows(current/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
            omitted_new = rows(current/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
            assert {r['review_id'] for r in omitted_master if r['detector'] == 'V2'} == {r['candidate_id'] for r in omitted_new if r['current_code'] != 'N'}
            scenarios['frozen_HEAD_omission'] = dict(omitted_ids=omitted_ids, selected_rows=omitted['selected_rows'], pending_events=omitted['pending_events'], pending_exposures=omitted['pending_exposures'])
            tests.append('frozen_HEAD_omission_produces_correct_reviewed_master_and_exact_pending_records')

        # A mapping limitation changes M bookkeeping but never becomes unresolved U.
        reset_current(); set_decisions({selected_ids[0]: 'M'}); mapped = run('--apply')
        assert mapped['new_counts']['M'] == 20 and mapped['new_counts']['U'] == 154 and mapped['pending_events'] == 0
        updated = verify_source_hashes(); assert updated['followup_queues']['mapping_limited']['events'] == 24
        tests.append('new_mapping_limitation_enters_mapping_queue_and_keeps_raw_queue_empty')
        # Saved archive metadata appends; historical identities are preserved.
        reset_current(); set_decisions()
        checkpoint = out/'checkpoints/LIBRARY_INPUTS.json'
        write_json(checkpoint, dict(archives=[dict(status='succeeded', library_file_id='libfile_SYNTHETIC_FIXTURE_ONLY', filename='synthetic.zip')]))
        run('--apply'); updated = verify_source_hashes()
        assert updated['input_archives'][:16] == state['input_archives'] and len(updated['input_archives']) == 17
        tests.append('new_saved_checkpoint_appends_without_replacing_16_earlier_archives')
        reset_current(); write_json(checkpoint, dict(archives=[dict(status='succeeded', library_file_id=state['input_archives'][0]['library_file_id'])]))
        failed = run(ok=False); assert 'Duplicate input archive identity' in failed.stderr
        tests.append('duplicate_saved_archive_identity_rejected')
    assert live_hashes == {str(p): sha(p) for p in live_paths}
    tests.append('all_live_science_status_and_document_hashes_unchanged_by_fixtures')
    result = dict(status='PASS_SYNTHETIC_HELPER_VALIDATION_ONLY', tests=tests, tests_passed=len(tests),
        script_sha256=sha(OUT/'update_current.py'), validation_script_sha256=sha(Path(__file__)),
        synthetic_selected_events=len(selection), synthetic_selected_exposures=len(queue),
        synthetic_completed_counts=scenarios['all_94_synthetic_U']['new_counts'],
        synthetic_completed_pending_events=0, synthetic_unavailable_pending_events=1,
        live_scientific_files_modified=False,
        administrative_change='Post-preregistration bookkeeping correction: unavailable N records remain in all selected batch dispositions and current336 evidence but are excluded from the cumulative raw-reviewed selected master. This preserves the successor invariant and prevents a later retry from failing or duplicating IDs. No frozen selection, acquisition, extraction, mapping rule or original scientific disposition is changed.',
        frozen_scientific_sources_unchanged=actual_freeze is not None,
        followup_freeze_sha256=sha(OUT/'FOLLOWUP_FREEZE.json') if actual_freeze else None,
        frozen_omission_fixture=scenarios.get('frozen_HEAD_omission'),
        limits='Only continuity contracts exercised on copied predecessor metadata and deliberately synthetic decisions. This does not validate scientific classifications, mapping calculations, Library persistence or publication and does not replace actual final continuity audit.')
    write_json(OUT/'CONTINUITY_HELPER_VALIDATION.json', result); print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
