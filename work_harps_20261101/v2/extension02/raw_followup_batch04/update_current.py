"""Adopt verified batch04 decisions while preserving every predecessor decision.

Default is read-only dry-run. --apply requires an explicit root-adopted summary,
independent audit, complete event decisions and unchanged frozen inputs. Published
historical state and evidence are never rewritten. New status text is derived
from the frozen predecessor and actual selected/adopted records.
"""
from pathlib import Path, PurePosixPath
import argparse, collections, copy, csv, hashlib, io, json

OUT = Path(__file__).resolve().parent
EXT = OUT.parent
V2 = EXT.parent
BASE = V2.parent
REPO = BASE.parent
CURRENT = EXT / 'raw_followup'
INPUT = OUT / 'inputs'
BATCH_NAME = OUT.name
BATCH_PATH = str(OUT.relative_to(REPO))
NEXT_BATCH = 'raw_followup_batch05'
CODES = {'A': 'PROVISIONAL_DETECTOR_ARTIFACT', 'O': 'PROVISIONAL_ATMOSPHERIC_OI',
         'U': 'UNRESOLVED_SPECTRAL_FEATURE', 'M': 'INSUFFICIENT_RAW_MAPPING',
         'N': 'UNREVIEWED_RAW_FOLLOWUP'}
LABELS = {'A': 'Provisional detector artefact', 'O': 'O I-compatible',
          'U': 'Unresolved spectral structure', 'M': 'Insufficient raw mapping',
          'N': 'No raw review yet'}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def rows(path):
    with Path(path).open(newline='') as handle: return list(csv.DictReader(handle))
def require(ok, message):
    if not ok: raise RuntimeError(message)
def flag(value): return str(value).lower() == 'true'
def jsontext(value): return json.dumps(value, indent=2, allow_nan=False) + '\n'
def count(records, key='current_code'):
    values = collections.Counter(r[key] for r in records)
    require(set(values) <= set(CODES), 'Unknown disposition code')
    return {k: values[k] for k in CODES}
def csvtext(records):
    columns = list(dict.fromkeys(k for r in records for k in r))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader(); writer.writerows(records)
    return output.getvalue()
def batch_figure(name):
    if not name: return ''
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in name,
            'Figure must be a safe batch-relative path')
    require((OUT / name).is_file(), 'Adopted figure is missing: ' + name)
    return '../' + BATCH_NAME + '/' + name

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    freeze = read(OUT / 'FOLLOWUP_FREEZE.json')
    for rel, expected in freeze['source_hashes'].items():
        require(sha(BASE / rel) == expected, 'Changed frozen input/code: ' + rel)
    plan = read(OUT / 'PLAN.json')
    before = rows(INPUT / 'CURRENT_V2_ALL336_DISPOSITIONS.csv')
    prior_selected = rows(INPUT / 'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
    prior_master = rows(INPUT / 'CURRENT_V2_DISPOSITIONS.csv')
    prior_summary = read(INPUT / 'CURRENT_SUMMARY.json')
    state = read(INPUT / 'CONTINUATION_STATE.json')
    selected = rows(OUT / 'SELECTED_EVENTS.csv')
    exposures = rows(OUT / 'SELECTED_EXPOSURES.csv')
    summary = read(OUT / 'SUMMARY.json')
    prior_counts = count(before)
    cohort_size = prior_summary['new_V2_events']
    combined_size = prior_summary['V2_events']
    require(len(before) == len({r['candidate_id'] for r in before}) == cohort_size,
            'Predecessor new cohort coverage mismatch')
    require(prior_counts == {k: prior_summary['current_new_V2_counts'].get(k, 0) for k in CODES}
            == {k: state['science']['new_V2_current_codes'].get(k, 0) for k in CODES},
            'Predecessor science counts disagree')
    require(len(prior_master) == len({r['review_id'] for r in prior_master}) == combined_size,
            'Predecessor master coverage mismatch')
    require(count(prior_master) == {k: prior_summary['current_all_V2_counts'].get(k, 0) for k in CODES},
            'Predecessor master counts disagree')
    require(len(prior_selected) == len({r['review_id'] for r in prior_selected}), 'Duplicate prior selected record')
    require({r['review_id'] for r in prior_selected if r['detector'] == 'V2'} ==
            {r['candidate_id'] for r in before if r['current_code'] != 'N'},
            'Prior selected V2 records differ from reviewed predecessor cohort')
    for rel, expected in prior_summary['source_hashes'].items():
        require(sha(V2 / rel) == expected, 'Changed historical source: ' + rel)
    expected_events = plan['selection_rule']['expected_V2_events']
    expected_exposures = plan['selection_rule']['max_unique_exposures']
    require(len(selected) == len({r['review_id'] for r in selected}) == expected_events,
            'Batch event selection mismatch')
    require(len(exposures) == len({r['dp_id'] for r in exposures}) == expected_exposures,
            'Batch exposure selection mismatch')
    require(all(r['detector'] == 'V2' for r in selected), 'Unexpected selected detector')
    queue_before = state['pending_raw_queue']
    require(queue_before['source_sha256'] == sha(INPUT / 'CURRENT_V2_ALL336_DISPOSITIONS.csv'),
            'Predecessor queue hash mismatch')
    expected_queue = queue_before['exposure_queue'][:expected_exposures]
    require([r['dp_id'] for r in exposures] == [r['dp_id'] for r in expected_queue],
            'Selected exposures are not the next frozen pending group')
    selected_ids = [r['review_id'] for r in selected]
    require(selected_ids == [k for r in expected_queue for k in r['pending_ids']],
            'Selected event order differs from predecessor queue')
    require(summary['status'] == 'ROOT_ADOPTED_CONSERVATIVE_REVIEW', 'Root adoption missing')
    require(summary['independent_numeric_audit'] == 'PASS', 'Independent audit not passed')
    require(summary['root_visual_review_complete'] is True, 'Root visual review not complete')
    require(summary['original_production_unchanged'] is True, 'Original catalog integrity not confirmed')
    require(summary['selected_events'] == expected_events and summary['selected_exposures'] == expected_exposures,
            'Adopted summary selection mismatch')
    for rel, expected in summary.get('source_hashes', {}).items():
        require(sha(OUT / rel) == expected, 'Changed adopted evidence: ' + rel)
    audit = read(OUT / 'independent_audit/SUMMARY.json')
    require(audit['status'] == 'PASS', 'Independent numeric audit file not PASS')
    for rel, expected in audit.get('source_hashes', {}).items():
        require(sha(OUT / rel) == expected, 'Changed audited source: ' + rel)
    mapping = {r['review_id']: r for r in read(OUT / 'NATIVE_MAPPING.json')['events']}
    require(set(mapping) == set(selected_ids), 'Mapping event coverage mismatch')
    by_id = {r['candidate_id']: r for r in before}
    source_selected = {r['review_id']: r for r in selected}
    decisions = []
    for original in rows(OUT / 'ADOPTED_DISPOSITIONS.csv'):
        r = dict(original); key = r.get('candidate_id') or r.get('review_id')
        code = r.get('code') or r.get('current_code')
        evidence = r.get('evidence') or r.get('current_evidence') or r.get('note')
        require(key in source_selected and code in CODES, 'Unexpected adopted event/code')
        require(r['dp_id'] == by_id[key]['dp_id'] == source_selected[key]['dp_id'], 'Adopted exposure mismatch')
        require(by_id[key]['current_code'] == 'N', 'Cannot replace a previously reviewed event')
        require(bool(evidence and evidence.strip()), 'Missing adopted evidence')
        mapped = flag(r.get('all_covering_orders_mapping_verified'))
        require(mapped == mapping[key]['mapping_supported'], 'Adopted mapping differs from audited mapping')
        require(not flag(r.get('final_physical_origin_confirmed')), 'All origins must remain provisional')
        if code in ('A', 'O', 'U'): require(mapped, 'Morphology decision without all-order mapping')
        if code == 'M': require(not mapped, 'Mapping-limited record marked mapped')
        if mapping[key]['status'] == 'NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE':
            require(code == 'N', 'Unavailable pair must remain N, not a reviewed disposition')
        if code == 'N':
            require(mapping[key]['status'] == 'NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE',
                    'N requires an explicitly unavailable product pair')
        decisions.append(dict(r, candidate_id=key, code=code, evidence=evidence,
                              all_covering_orders_mapping_verified=mapped))
    require(len(decisions) == len({r['candidate_id'] for r in decisions}) == expected_events,
            'Duplicate or missing adopted event')
    decision_by = {r['candidate_id']: r for r in decisions}
    require(set(decision_by) == set(selected_ids), 'Adopted selection coverage mismatch')
    adopted_counts = count(decisions, 'code')
    require(adopted_counts == {k: summary['adopted_counts'].get(k, 0) for k in CODES}, 'Adopted counts mismatch')
    timestamp = summary['created_utc']
    evidence_table = '../' + BATCH_NAME + '/ADOPTED_DISPOSITIONS.csv'
    new = copy.deepcopy(before)
    batch_flag = 'selected_for_' + BATCH_NAME
    for r in new:
        key = r['candidate_id']; r[batch_flag] = str(key in decision_by)
        if key in decision_by:
            d = decision_by[key]
            r.update(current_code=d['code'], current_disposition=CODES[d['code']],
                     current_evidence=d['evidence'], current_evidence_table=evidence_table,
                     final_physical_origin_confirmed='False')
    mutable = {'current_code', 'current_disposition', 'current_evidence', 'current_evidence_table',
               'final_physical_origin_confirmed', batch_flag}
    for old, current in zip(before, new):
        require(all(old[k] == current[k] for k in old if k not in mutable), 'Historical field changed')
        if old['candidate_id'] not in decision_by:
            require(all(old[k] == current[k] for k in old), 'Unselected predecessor row changed')
    # This cumulative master contains completed raw reviews, not attempted N records.
    # Unavailable cases remain fully documented in the batch decisions and new336
    # table, and can therefore be selected in a later retry without duplicate IDs.
    reviewed_ids = [key for key in selected_ids if decision_by[key]['code'] != 'N']
    all_selected = copy.deepcopy(prior_selected)
    for key in reviewed_ids:
        d = decision_by[key]; source = source_selected[key]
        all_selected.append(dict(review_id=key, detector='V2', dp_id=d['dp_id'], target=source['target'],
            note=d['evidence'], figure=batch_figure(d.get('figure', '')), figure_row=d.get('figure_row', ''),
            all_covering_orders_mapping_verified=str(d['all_covering_orders_mapping_verified']),
            topocentric_air_angstrom=d.get('topocentric_air_angstrom', ''),
            nearest_OI_air_angstrom=d.get('nearest_OI_air_angstrom', ''),
            nearest_OI_offset_angstrom=d.get('nearest_OI_offset_angstrom', ''),
            original_production_unchanged='True', final_physical_origin_confirmed='False',
            baseline_code='N', baseline_disposition='UNREVIEWED_RAW_FOLLOWUP',
            second_review_agrees=d.get('second_review_agrees', d.get('primary_review_agrees', '')),
            review_scope=BATCH_NAME + ' prospective all-order raw mapping; provisional morphology',
            current_code=d['code'], current_disposition=CODES[d['code']], wider_followup_applied='False',
            current_evidence=d['evidence'], current_evidence_table=evidence_table,
            current_raw_batch='extension02/' + BATCH_NAME))
    require(len(all_selected) == len({r['review_id'] for r in all_selected}) == len(prior_selected) + len(reviewed_ids),
            'Raw-reviewed selected master duplicates or omissions')
    require({r['review_id'] for r in all_selected if r['detector'] == 'V2'} ==
            {r['candidate_id'] for r in new if r['current_code'] != 'N'},
            'Successor selected-master invariant failed')
    master = copy.deepcopy(prior_master)
    new_by = {r['candidate_id']: r for r in new}
    old_master = [r for r in prior_master if r['cohort'] == 'V2_first100']
    require(len(old_master) == prior_summary['older_V2_events'], 'Older cohort coverage mismatch')
    hits = {r['candidate_id']: r for r in rows(EXT / 'production/V2_HITS.csv')}
    for r in master:
        if r['cohort'] == 'V2_extension02':
            key = r['review_id']; before_row = by_id[key]; hit = hits[key]
            require(r['dp_id'] == hit['dp_id'] == before_row['dp_id'] and
                    r['input_sha256'] == hit['input_sha256'] == before_row['source_input_sha256'],
                    'Master/source provenance mismatch')
            if key in decision_by:
                updated = new_by[key]
                r.update(current_code=updated['current_code'], current_disposition=updated['current_disposition'],
                         final_physical_origin_confirmed='False')
        else: require(r['cohort'] == 'V2_first100', 'Unknown master cohort')
    require([r for r in master if r['cohort'] == 'V2_first100'] == old_master, 'Older master rows changed')
    require(len(master) == combined_size, 'Combined master coverage changed')
    counts = count(new); total_counts = count(master); older_counts = count(old_master)
    require(all(total_counts[k] == older_counts[k] + counts[k] for k in CODES), 'Cohort count mismatch')
    outputs = {}
    def put(path, content): outputs[path] = content
    def digest(path): return hashlib.sha256(outputs[path].encode()).hexdigest() if path in outputs else sha(path)
    put(CURRENT / 'CURRENT_V2_ALL336_DISPOSITIONS.csv', csvtext(new))
    put(CURRENT / 'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv', csvtext(all_selected))
    put(V2 / 'CURRENT_V2_DISPOSITIONS.csv', csvtext(master))
    current_summary = copy.deepcopy(prior_summary)
    current_summary.update(created_utc=timestamp, status='ROOT_ADOPTED_BATCH04_OVERLAY',
        basis=f'All {len(prior_selected)} predecessor raw-reviewed selected decisions preserved; {len(reviewed_ids)} new raw reviews adopted after independent numerical audit and visual review. The batch accounts for all {expected_events} selected records, including {adopted_counts["N"]} unavailable records retained as N in the current336 table and pending queue. All origins remain provisional.',
        current_new_V2_counts=counts, current_all_V2_counts=total_counts,
        V2_raw_reviewed=combined_size-counts['N'], V2_raw_unreviewed=counts['N'],
        latest_raw_batch=dict(directory='extension02/' + BATCH_NAME, selected_events=expected_events,
            selected_exposures=expected_exposures, raw_reviewed_events=len(reviewed_ids),
            unavailable_events=adopted_counts['N'], adopted_counts=adopted_counts,
            summary_sha256=sha(OUT / 'SUMMARY.json'), adopted_dispositions_sha256=sha(OUT / 'ADOPTED_DISPOSITIONS.csv')),
        all_original_and_baseline_files_unchanged=True)
    current_summary['source_hashes'].update({str(p.relative_to(V2)): sha(p) for p in
        [INPUT/'CURRENT_V2_ALL336_DISPOSITIONS.csv', INPUT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',
         INPUT/'CURRENT_V2_DISPOSITIONS.csv', INPUT/'CURRENT_SUMMARY.json', OUT/'SUMMARY.json', OUT/'ADOPTED_DISPOSITIONS.csv']})
    put(CURRENT / 'CURRENT_SUMMARY.json', jsontext(current_summary))
    put(V2 / 'CURRENT_STATUS.json', jsontext(current_summary))
    pending = [r for r in new if r['current_code'] == 'N']; queue = []
    for source in rows(EXT / 'MAIN100.csv'):
        ids = [r['candidate_id'] for r in pending if r['dp_id'] == source['dp_id']]
        if ids:
            queue.append(dict(dp_id=source['dp_id'], target=source['canonical_target'],
                selection_index=int(source['selection_index']), pending_ids=ids,
                raw_progenitor_id=source['raw_progenitor_id'], ancillary_archive_id=source['ancillary_archive_id'],
                raw_source_url=source['raw_source_url'], ancillary_source_url=source['ancillary_source_url']))
    require(sum(len(r['pending_ids']) for r in queue) == len(pending), 'Pending queue omission')
    state['schema'] = 'SETI_CONTINUATION_STATE_V3'; state['created_utc'] = timestamp
    state['science'].update(new_V2_current_codes=counts,
        new_V2_unresolved_ids=[r['candidate_id'] for r in new if r['current_code'] == 'U'],
        new_V2_mapping_limited_ids=[r['candidate_id'] for r in new if r['current_code'] == 'M'])
    state['latest_raw_batch'] = current_summary['latest_raw_batch']
    state['pending_raw_queue'] = dict(source=str((CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv').relative_to(REPO)),
        source_sha256=digest(CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv'),
        selection='Rows where current_code == N; exposure order follows frozen MAIN100.',
        pending_events=len(pending), pending_exposures=len(queue), first_event=pending[0]['candidate_id'] if pending else None,
        first_exposure=queue[0] if queue else None,
        events=[{k:r[k] for k in ['candidate_id','dp_id','target','source_input_sha256']} for r in pending], exposure_queue=queue)
    # Morphology queues remain explicit after raw availability is exhausted.
    # Preserve master order: no ranking by line strength, apparent interest or origin.
    selected_by_id = {r['review_id']: r for r in all_selected}
    followup = {}
    for code, label in [('M', 'mapping_limited'), ('U', 'unresolved_structure')]:
        members = []
        for record in master:
            if record['current_code'] != code:
                continue
            member = {k: record[k] for k in ['cohort', 'review_id', 'dp_id', 'target',
                'fitted_center_bary_air_angstrom', 'input_sha256', 'current_code', 'evidence_table']}
            if record['cohort'] == 'V2_extension02':
                current = new_by[record['review_id']]
                member['current_evidence_table'] = str(
                    (CURRENT / current['current_evidence_table']).resolve().relative_to(REPO))
                member['current_evidence'] = current['current_evidence']
                selected_row = selected_by_id.get(record['review_id'])
                if selected_row:
                    member['all_covering_orders_mapping_verified'] = flag(
                        selected_row['all_covering_orders_mapping_verified'])
                    member['current_raw_batch'] = selected_row.get('current_raw_batch', '')
            else:
                member['current_evidence_table'] = str(
                    (V2 / record['evidence_table']).resolve().relative_to(REPO))
            members.append(member)
        followup[label] = dict(code=code, events=len(members),
            first_event=members[0]['review_id'] if members else None, records=members)
    state['followup_queues'] = dict(
        source=str((V2/'CURRENT_V2_DISPOSITIONS.csv').relative_to(REPO)),
        source_sha256=digest(V2/'CURRENT_V2_DISPOSITIONS.csv'),
        order='Stable current master order within each code; no morphology or score ranking.',
        priorities=[
            dict(priority=1, queue='mapping_limited',
                action='Prepare a separate, bounded mapping investigation of the listed M records. Diagnose failed covering orders or missing edge cutouts and preregister any revised geometry/reference method before new calculations. Keep all original mapping outcomes and thresholds; do not relax a gate to promote an origin.'),
            dict(priority=2, queue='unresolved_structure',
                action='Prepare a separate bounded interpretation study of listed U records, using existing epoch profiles, raw cutouts and calibration-fiber metadata first. Compare repeatability and instrumental/natural hypotheses with explicit controls; do not repeat the completed epoch calculation merely to resume or use epoch metrics as an origin veto.')],
        **followup)
    state['science']['all_V2_current_codes'] = total_counts
    state['science']['raw_review_complete'] = not pending
    state['next_action'] = dict(
        kind='PREPARE_NEXT_BOUNDED_RAW_BATCH' if pending else 'FOLLOW_UP_UNRESOLVED_CASES',
        directory_to_create=str((EXT/NEXT_BATCH).relative_to(REPO)) if pending else None,
        action=('Prepare a separate bounded batch from the remaining N queue in MAIN100 order. Freeze selected IDs, original product identities and limits before new raw arrays. Reuse hash-verified products; preserve failures and omissions without replacements.'
            if pending else 'The first raw review is complete. Start the mapping-limited queue, then investigate the unresolved-structure queue using the explicit priorities and retained evidence. Preregister each bounded follow-up before new calculations; do not create an empty raw batch or treat completion as a calibrated null.'),
        queue_head=pending[0]['candidate_id'] if pending else None,
        first_mapping_record=followup['mapping_limited']['first_event'],
        first_unresolved_record=followup['unresolved_structure']['first_event'],
        reproduction_is_not_new_science=True,
        no_fixed_batch_selection_has_been_made_in_this_handoff=True)
    older_limited = [r['review_id'] for r in old_master if r['current_code'] == 'M']
    state['after_pending_raw_review'] = [
        'Investigate the explicit mapping-limited queue first, including older records ' + ', '.join(older_limited) + '.',
        'Follow up the explicit unresolved-structure queue using existing epoch context; continuous epoch metrics are context, not an origin veto.',
        'Continue approved Rubin week (8–14 November); no Rubin analysis completed at this checkpoint.']
    state['previous_continuation_state'] = dict(path=str((INPUT/'CONTINUATION_STATE.json').relative_to(REPO)),
        sha256=sha(INPUT/'CONTINUATION_STATE.json'), historical_predecessor_state=str((EXT/'raw_followup_batch03/CONTINUATION_STATE.json').relative_to(REPO)))
    archive_manifest = OUT/'checkpoints/LIBRARY_INPUTS.json'
    if archive_manifest.exists():
        archives = read(archive_manifest)
        if isinstance(archives, dict): archives = archives.get('archives', archives.get('files', []))
        require(isinstance(archives, list) and archives, 'Unrecognized new input archive manifest')
        require(all(r.get('status') == 'succeeded' and r.get('library_file_id') for r in archives), 'Incomplete input checkpoint')
        old_library_ids = {r.get('library_file_id') for r in state['input_archives']}
        require(not old_library_ids.intersection(r['library_file_id'] for r in archives), 'Duplicate input archive identity')
        state['input_archives'].extend(copy.deepcopy(archives))
    else:
        state[BATCH_NAME + '_raw_input_checkpoint'] = 'NOT_YET_SAVED; original product URLs and hashes remain in products/MANIFEST.json. Do not claim input checkpoint saved.'
    state['publication'] = dict(authorization=state['publication']['authorization'],
        authorization_quote=state['publication']['authorization_quote'], state='AWAITING_FINAL_PUBLICATION_READBACK',
        previous_verified_content_commit=state['publication'].get('verified_content_commit'),
        publication_success_must_be_verified_separately=True, receipt=BATCH_PATH+'/PUBLICATION_RECEIPT.json')
    state['execution'] = dict(active_science_workers=0, automatic_background_search=False,
        meaning_of_continuity='Durable evidence and exact queue, not an unattended scheduled science job.')
    unresolved = ', '.join(state['science']['new_V2_unresolved_ids']) or 'none'
    limited = ', '.join(state['science']['new_V2_mapping_limited_ids']) or 'none'
    table = '\n'.join(f'| {LABELS[k]} | {counts[k]} |' for k in CODES)
    adopted_text = ' / '.join(f"{adopted_counts[k]} {k}" for k in CODES)
    older_text = ' / '.join(f"{older_counts[k]} {k}" for k in CODES)
    current_text = ' / '.join(f"{counts[k]} {k}" for k in CODES)
    combined_text = ' / '.join(f"{total_counts[k]} {k}" for k in CODES)
    science = state['science']; n_main=science['main_exposures']; n_targets=science['main_targets']
    hours=science['main_exposure_hours']; n_v1=science['V1_exposures']; hits_v1=science['V1_hits']; n_v2=science['V2_exposures']
    first = queue[0] if queue else None
    next_text = (f"Next: **{pending[0]['candidate_id']}**, exposure **{first['dp_id']}**, target **{first['target']}**." if pending else 'No pending raw records remain; the first raw review is complete, while origin follow-up remains open.')
    mapping_head = followup['mapping_limited']['first_event'] or 'none'
    unresolved_head = followup['unresolved_structure']['first_event'] or 'none'
    mapping_total = followup['mapping_limited']['events']
    unresolved_total = followup['unresolved_structure']['events']
    next_action_text = (
        f"{next_text} The exact pending queue contains **{len(pending)} records in {len(queue)} exposures**. Prepare a separate `{NEXT_BATCH}/` using frozen MAIN100 order. Freeze selection, original raw/ancillary identities, limits and methods before new raw-array reads. Reuse verified cached pairs. Do not replace failures or omitted pairs with more interesting targets. Review every selected event and every covering order."
        if pending else
        f"{next_text} Start with the **{mapping_total} mapping-limited records**, first **{mapping_head}**, then the **{unresolved_total} unresolved structures**, first **{unresolved_head}**, in the stable master-table order recorded in `followup_queues`. Prepare a bounded investigation of failed covering orders and missing cutouts before drawing further origin conclusions. For unresolved structures, reuse existing epoch profiles, raw cutouts and calibration-fiber metadata with explicit instrumental/natural controls. Freeze each follow-up method before new calculations. Do not create an empty raw batch or repeat completed epoch work merely to resume.")
    put(REPO/'CONTINUE_SETI.md', f'''# Continue SETI from this checkpoint

Read the [current continuation state]({BATCH_PATH}/CONTINUATION_STATE.json), fetch current GitHub, and compare source hashes before starting. Another session may have advanced the project.

## Completed work and current status

The survey remains **{n_main} unique exposures of {n_targets} targets, {hours:.9f} hours**. V1 searched {n_v1} exposures and found {hits_v1} preliminary hits. V2 searched {n_v2} exposures and produced {combined_size} records. No observing time was added by this follow-up. There is no qualified laser candidate or calibrated null result.

The [epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md) is complete for all {cohort_size} new V2 records against same-target observations among the new 100 spectra: 2,185 event/exposure pairs and 4,370 profiles, with discovery observations excluded from other-epoch summaries. Earlier 200 exposures were excluded. Its audit passed; do not repeat it merely to resume.

[This raw batch]({BATCH_PATH}/README.md) selected {expected_events} pending records in {expected_exposures} exposures. Adopted outcomes: **{adopted_text}**. All {len(prior_selected)} predecessor raw-reviewed selected V1/V2 decisions remain unchanged. This batch adds {len(reviewed_ids)} completed raw reviews to the cumulative selected master; its {adopted_counts['N']} unavailable records remain explicit N cases in the current336 table and pending queue. The current new cohort is:

| New V2 status | Count |
|---|---:|
{table}

Older cohort: {older_text}. Combined {combined_size}: {combined_text}. All origin descriptions are provisional.

Unresolved new IDs: {unresolved}.
Mapping-limited new IDs: {limited}.
Older mapping limitations: {', '.join(older_limited)}.

## Next action

{next_action_text}

The continuation state preserves exact follow-up queues: {mapping_total} mapping-limited records and {unresolved_total} unresolved structures across both V2 cohorts. Mapping investigations have first priority, followed by interpretation of unresolved structures. Epoch metrics provide context and do not veto an origin. Rubin remains the approved second week (8–14 November) and has not been analyzed.

## Restore, verify and preserve continuity

Input package names, sizes, hashes and Library identities are in the current state. The initial science/raw inputs and every later raw batch have separate checkpoints; preserve them all. Extract into staging first: `v2/extension02/` member paths are relative to `work_harps_20261101`. Copy verified payloads without overwriting newer status files with historical archive reports. Residual `.part` files are never science inputs.

All 4,370 epoch profiles are recoverable from [18 ordered parts](work_harps_20261101/v2/extension02/epoch_followup/PROFILE_ARRAYS_PARTS.json) with `restore_profile_archive.py`. Each raw batch README documents its evidence archive and audit. See [restoration instructions](work_harps_20261101/v2/RESTORE.md). Run audits in a separate copy because reports are rewritten; do not rely on old absolute runtime paths.

After each verified batch, retain source IDs/hashes, decisions, limitations, commands, evidence and the exact next queue. Original catalogs and historical results remain immutable. The user authorized public GitHub updates on 1 November 2026; earlier approval-wait notes are historical.

This checkpoint awaits final publication readback. Root must record verified remote heads and file hashes in `{BATCH_PATH}/PUBLICATION_RECEIPT.json` before claiming delivery. No unattended background science search is configured.
''')
    put(CURRENT/'CURRENT_RESULTS.md', f'''# Aktuel råopfølgning på den nye HARPS-prøve

**{cohort_size-counts['N']} af {cohort_size} nye V2-poster er rågennemgået; {counts['N']} mangler.** Vurderingerne er foreløbige. Ingen kvalificeret laser- eller SETI-kandidat er identificeret.

| Aktuel status | Antal |
|---|---:|
{table}
| Hele det nye katalog | {cohort_size} |

[Seneste gruppe](../{BATCH_NAME}/README.md) omfatter {expected_events} hidtil ikke rågennemgåede poster i {expected_exposures} eksponeringer. Dens vedtagne udfald er {adopted_text}. Alle {len(prior_selected)} tidligere udvalgte V1/V2-afgørelser, inklusive senere billedkoblingskontroller, er bevaret. Numerisk kontrol og visuelle vurderinger er dokumenteret særskilt; agentkontrol er ikke menneskelig fagfællebedømmelse eller nye observationer.

Uafklarede nye poster: {unresolved}.
Nye begrænsninger i billedkobling: {limited}.
Den ældre kohorte er uændret: {older_text}. Alle {combined_size} poster samlet: {combined_text}.

[Alle aktuelle nye poster](CURRENT_V2_ALL336_DISPOSITIONS.csv) · [alle {len(all_selected)} rågennemgåede udvalgte V1/V2-poster](CURRENT_SELECTED_EVENT_DISPOSITIONS.csv) · [opsummering](CURRENT_SUMMARY.json) · [statuskombinationskode](../{BATCH_NAME}/update_current.py) · [præcise arbejds-køer](../{BATCH_NAME}/CONTINUATION_STATE.json) · [historisk baseline](RESULTS.md) · [tidligere bredere billedkobling](mapping_followup/README.md).

Baseline-kolonner angiver historiske trin; `current_code` og `current_evidence_table` angiver gældende opfølgning. Historiske billedkoblingsregler er heterogene. Der foreligger ingen global følsomheds- eller falsk-alarm-kalibrering og intet kvalificeret nulresultat for lasere.
''')
    put(V2/'RESTORE.md', f'''# Gendannelse og fortsættelse af HARPS-arbejdet

Start i [CONTINUE_SETI.md](../../CONTINUE_SETI.md) og [den aktuelle maskinlæsbare tilstand](extension02/{BATCH_NAME}/CONTINUATION_STATE.json). Hent seneste GitHub-version før arbejde; tidligere sessioner og arkivrapporter kan være historiske.

Hovedprøven er uændret: {n_main} unikke eksponeringer af {n_targets} stjerner, {hours:.9f} timer. V1 har {hits_v1} foreløbige træf i {n_v1} eksponeringer. V2 har {combined_size} poster i {n_v2} eksponeringer. Originale detektorer, indstillinger og kataloger er bevaret.

## Aktuel status

Ældre kohorte: {older_text}, bevaret i `followup_synthesis/CUMULATIVE_333.csv`. Ny kohorte: {current_text}, i `extension02/raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv`. Alle {combined_size} poster er samlet i `CURRENT_V2_DISPOSITIONS.csv` med kohorte og evidenskilde.

Seneste rågruppe omfatter {expected_events} poster i {expected_exposures} eksponeringer og bevarer alle {len(prior_selected)} tidligere udvalgte V1/V2-afgørelser. Den resterende råkø rummer {len(pending)} poster i {len(queue)} eksponeringer. {next_text}

Den maskinlæsbare tilstand bevarer to konkrete opfølgningskøer i stabil katalogrækkefølge: først {mapping_total} billedkoblingsbegrænsninger (første {mapping_head}), derefter {unresolved_total} uafklarede strukturer (første {unresolved_head}). Fastlås en særskilt afgrænset metode før nye beregninger. En tom råkø er ikke et kalibreret nulresultat.

Den nye epokekontrol er afsluttet: alle {cohort_size} poster blandt de nye 100 spektre, 2.185 par og 4.370 profiler. Tidligere 200 eksponeringer indgår ikke i denne kontrol. Genkør ikke afsluttede rå- eller epokebatcher blot for at fortsætte. Uafklarede strukturer og billedkoblinger står som særskilt opfølgning efter restkøen; Rubin-ugen 8.–14. november er endnu ikke analyseret.

## Input og evidens

Klon/hent `andersenmartin-blip/setisearch`, branch `optical-harps-week-20261101`, og gå til `work_harps_20261101`. Ældre input er linket i [V2-rapporten](README.md), [første rågruppe](triage_batch01/README.md), [anden rågruppe](triage_batch02/README.md) og `triage_followup/`.

De første extension02-inputpakker er i [gemte input](extension02/checkpoints/SAVED_INPUTS.md); senere rågrupper har separate checkpoints i den aktuelle tilstandsfil. Kontroller både arkiv- og medlemshashes. Udpak til staging; medlemstier under `v2/extension02/` er relative til `work_harps_20261101`. Kopier kun verificerede payloads og kvitteringer; erstat ikke nyere status med historiske arkivrapporter. Ufuldstændige `.part`-filer er ikke analyseinput.

[Seneste gruppes README](extension02/{BATCH_NAME}/README.md) beskriver evidensarkiv, billedudsnit og kontrollen. Ældre evidensarkiver bevares i deres egne mapper. Epokeprofiler gendannes fra 18 dele med `python3 restore_profile_archive.py` inde i `extension02/epoch_followup`; scriptet verificerer dele og samlet SHA-256.

## Reproduktion

Brug Python 3 med NumPy, SciPy, Astropy og Matplotlib i de registrerede versioner fra gruppens `SUMMARY.json`. Undgå gamle absolutte runtime-stier. Kør audits i en separat kopi med gendannede, hashverificerede input, da rapporterne skrives igen. Fra `work_harps_20261101`:

```bash
python3 v2/extension02/epoch_followup/independent_audit/check_epochs.py
python3 v2/extension02/{BATCH_NAME}/independent_audit/check_batch04.py
```

Følg hver gruppes README ved fuld reproduktion; bevar originale resultater og tidsstempler som historisk evidens. Ny reproduktion kan have andre tidsstempler uden ændret videnskab.

Alle oprindelsesvurderinger er foreløbige. Agentkontrol er ikke menneskelig fagfællebedømmelse; historiske billedkoblingsregler er heterogene. Der foreligger ingen global følsomhed, falsk-alarm-rate eller kvalificeret laser-eksklusion. Ingen automatisk baggrundssøgning er konfigureret.
''')
    # Refresh hashes only after every mutable output exists in memory. Inherited
    # state includes CONTINUE_SETI.md, so hashing it before rendering would be stale.
    for path in outputs:
        state['source_hashes'][str(path.relative_to(REPO))] = digest(path)
    for path in [OUT/'SUMMARY.json', OUT/'ADOPTED_DISPOSITIONS.csv', OUT/'FOLLOWUP_FREEZE.json',
                 INPUT/'CONTINUATION_STATE.json', INPUT/'CURRENT_V2_DISPOSITIONS.csv']:
        state['source_hashes'][str(path.relative_to(REPO))] = sha(path)
    if archive_manifest.exists(): state['source_hashes'][str(archive_manifest.relative_to(REPO))] = sha(archive_manifest)
    # Root may prepend its current summary before adoption; use the current entry point.
    if (REPO/'README.md').exists(): state['source_hashes']['README.md'] = sha(REPO/'README.md')
    if (OUT/'README.md').exists(): state['source_hashes'][BATCH_PATH+'/README.md'] = sha(OUT/'README.md')
    put(OUT/'CONTINUATION_STATE.json', jsontext(state))
    # Protect every mutable predecessor table, not just the new336 cohort.
    predecessors = [(CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv', INPUT/'CURRENT_V2_ALL336_DISPOSITIONS.csv'),
                    (CURRENT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv', INPUT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv'),
                    (CURRENT/'CURRENT_SUMMARY.json', INPUT/'CURRENT_SUMMARY.json'),
                    (V2/'CURRENT_STATUS.json', INPUT/'CURRENT_SUMMARY.json'),
                    (V2/'CURRENT_V2_DISPOSITIONS.csv', INPUT/'CURRENT_V2_DISPOSITIONS.csv')]
    for live, previous in predecessors:
        require(sha(live) in {sha(previous), digest(live)},
                'Current file differs from both frozen predecessor and exact new overlay: ' + str(live.relative_to(REPO)))
    if args.apply:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)
    print(jsontext(dict(mode='APPLIED' if args.apply else 'DRY_RUN', new_counts=counts,
        all_counts=total_counts, prior_selected_preserved=len(prior_selected), selected_rows=len(all_selected),
        pending_events=len(pending), pending_exposures=len(queue), next_event=pending[0]['candidate_id'] if pending else None,
        output_files=[str(p.relative_to(REPO)) for p in outputs])))

if __name__ == '__main__': main()
