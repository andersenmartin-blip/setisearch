"""Adopt verified batch02 decisions without changing original catalogs or frozen inputs.

Default is dry-run. --apply writes current tables, reports and a NEW continuation
state. Published epoch state and all earlier raw/production evidence stay intact.
SUMMARY.json and ADOPTED_DISPOSITIONS.csv are explicit root-adoption inputs.
"""
from pathlib import Path
import argparse, collections, copy, csv, hashlib, io, json

OUT = Path(__file__).resolve().parent
EXT = OUT.parent
V2 = EXT.parent
BASE = V2.parent
REPO = BASE.parent
PREVIOUS = EXT / 'raw_followup'
INPUT = OUT / 'inputs'
CODES = {'A': 'PROVISIONAL_DETECTOR_ARTIFACT', 'O': 'PROVISIONAL_ATMOSPHERIC_OI',
         'U': 'UNRESOLVED_SPECTRAL_FEATURE', 'M': 'INSUFFICIENT_RAW_MAPPING',
         'N': 'UNREVIEWED_RAW_FOLLOWUP'}
BATCH_PATH = str(OUT.relative_to(REPO))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rows(path):
    with Path(path).open(newline='') as handle:
        return list(csv.DictReader(handle))

def read(path):
    return json.loads(Path(path).read_text())

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def flag(value):
    return str(value).lower() == 'true'

def csvtext(records):
    columns = list(dict.fromkeys(k for r in records for k in r))
    handle = io.StringIO(newline='')
    writer = csv.DictWriter(handle, fieldnames=columns)
    writer.writeheader()
    writer.writerows(records)
    return handle.getvalue()

def jsontext(value):
    return json.dumps(value, indent=2, allow_nan=False) + '\n'

def count(records, key='current_code'):
    c = collections.Counter(r[key] for r in records)
    return {k: c[k] for k in CODES}

def normalized_decisions(selected, new_before):
    decisions = rows(OUT / 'ADOPTED_DISPOSITIONS.csv')
    selected_ids = {r['review_id'] for r in selected}
    by_id = {r['candidate_id']: r for r in new_before}
    result = []
    for original in decisions:
        r = dict(original)
        k = r.get('candidate_id') or r.get('review_id')
        code = r.get('code') or r.get('current_code')
        evidence = r.get('evidence') or r.get('current_evidence') or r.get('note')
        require(k in selected_ids, 'Unselected decision: ' + str(k))
        require(code in CODES, 'Unknown decision code: ' + str(code))
        require(r['dp_id'] == by_id[k]['dp_id'], 'Decision exposure mismatch: ' + k)
        require(by_id[k]['current_code'] == 'N', 'Attempt to replace already reviewed event: ' + k)
        require(bool(evidence and evidence.strip()), 'Missing adopted evidence: ' + k)
        mapped = flag(r.get('all_covering_orders_mapping_verified'))
        if code in 'AOU':
            require(mapped, 'Physical/morphological decision without all-order mapping: ' + k)
        if code == 'M':
            require(not mapped, 'Mapping-limited decision incorrectly marked verified: ' + k)
        require(not flag(r.get('final_physical_origin_confirmed')), 'Physical origins must remain provisional')
        result.append(dict(r, candidate_id=k, code=code, evidence=evidence,
                           all_covering_orders_mapping_verified=mapped))
    require(len(result) == len({r['candidate_id'] for r in result}) == len(selected), 'Duplicate/missing decision')
    require({r['candidate_id'] for r in result} == selected_ids, 'Selected/decision coverage mismatch')
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write after all adoption gates pass')
    args = parser.parse_args()
    freeze = read(OUT / 'FOLLOWUP_FREEZE.json')
    for rel, digest in freeze['source_hashes'].items():
        require(sha(BASE / rel) == digest, 'Changed frozen input/code: ' + rel)
    before = rows(INPUT / 'CURRENT_V2_ALL336_DISPOSITIONS.csv')
    prior_selected = rows(INPUT / 'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
    prior_summary = read(INPUT / 'CURRENT_SUMMARY.json')
    state = read(INPUT / 'CONTINUATION_STATE.json')
    selected = rows(OUT / 'SELECTED_EVENTS.csv')
    exposures = rows(OUT / 'SELECTED_EXPOSURES.csv')
    summary = read(OUT / 'SUMMARY.json')
    require(len(before) == len({r['candidate_id'] for r in before}) == 336, 'Original new cohort incomplete')
    require(count(before) == {'A': 44, 'O': 8, 'U': 6, 'M': 1, 'N': 277}, 'Prior science counts changed')
    require(len(prior_selected) == 65, 'Prior selected scope changed')
    for rel, expected in prior_summary['source_hashes'].items():
        require(sha(V2 / rel) == expected, 'Changed historical source: ' + rel)
    require(len(selected) == 68 and len(exposures) == 16, 'Batch02 selection changed')
    require(all(r['detector'] == 'V2' for r in selected), 'Unexpected detector in batch02')
    require(summary['status'] == 'ROOT_ADOPTED_CONSERVATIVE_REVIEW', 'Root adoption missing')
    require(summary['independent_numeric_audit'] == 'PASS', 'Independent audit not passed')
    require(summary['root_visual_review_complete'] is True, 'Root visual review not recorded')
    require(summary['original_production_unchanged'] is True, 'Original catalogs not verified')
    require(summary['selected_events'] == 68 and summary['selected_exposures'] == 16, 'Summary selection mismatch')
    decisions = normalized_decisions(selected, before)
    adopted_counts = count(decisions, 'code')
    require({k: summary['adopted_counts'].get(k, 0) for k in CODES} == adopted_counts, 'Adopted counts mismatch')
    timestamp = summary['created_utc']  # deterministic output from the adopted evidence checkpoint
    decision_by = {r['candidate_id']: r for r in decisions}
    selected_by = {r['review_id']: r for r in selected}
    new = copy.deepcopy(before)
    for r in new:
        k = r['candidate_id']
        r['selected_for_raw_followup_batch02'] = str(k in decision_by)
        if k in decision_by:
            d = decision_by[k]
            r.update(current_code=d['code'], current_disposition=CODES[d['code']],
                     current_evidence=d['evidence'],
                     current_evidence_table='../raw_followup_batch02/ADOPTED_DISPOSITIONS.csv',
                     final_physical_origin_confirmed='False')
    # Only current fields change. Original baseline fields remain exact historical values.
    mutable = {'current_code', 'current_disposition', 'current_evidence', 'current_evidence_table',
               'final_physical_origin_confirmed', 'selected_for_raw_followup_batch02'}
    for old, current in zip(before, new):
        require(all(old[k] == current[k] for k in old if k not in mutable), 'Baseline field changed')
        if old['candidate_id'] not in decision_by:
            require(all(old[k] == current[k] for k in old), 'Earlier/unselected event changed')
    all_selected = copy.deepcopy(prior_selected)
    for d in decisions:
        k = d['candidate_id']; s = selected_by[k]
        agreement = d.get('primary_review_agrees', d.get('second_review_agrees', ''))
        all_selected.append(dict(review_id=k, detector='V2', dp_id=d['dp_id'], target=s['target'],
            note=d['evidence'], figure=('../raw_followup_batch02/' + d['figure']) if d.get('figure') else '', figure_row=d.get('figure_row', ''),
            all_covering_orders_mapping_verified=str(d['all_covering_orders_mapping_verified']),
            topocentric_air_angstrom=d.get('topocentric_air_angstrom', ''),
            nearest_OI_air_angstrom=d.get('nearest_OI_air_angstrom', ''),
            nearest_OI_offset_angstrom=d.get('nearest_OI_offset_angstrom', ''),
            original_production_unchanged='True', final_physical_origin_confirmed='False',
            baseline_code='N', baseline_disposition='UNREVIEWED_RAW_FOLLOWUP',
            second_review_agrees=agreement, review_scope='Batch02 prospective all-order raw mapping; provisional morphology',
            current_code=d['code'], current_disposition=CODES[d['code']], wider_followup_applied='False',
            current_evidence=d['evidence'], current_evidence_table='../raw_followup_batch02/ADOPTED_DISPOSITIONS.csv',
            current_raw_batch='extension02/raw_followup_batch02'))
    require(len(all_selected) == len({r['review_id'] for r in all_selected}) == 133, 'Selected master duplicates')
    master = []
    old_records = rows(V2 / 'followup_synthesis/CUMULATIVE_333.csv')
    old_hits = rows(V2 / 'production/V2_HITS.csv')
    status_codes = {v: k for k, v in CODES.items()}
    for r in old_records:
        matches = [h for h in old_hits if h['dp_id'] == r['dp_id'] and
                   abs(float(h['fitted_center_angstrom']) - float(r['fitted_center_bary_air_angstrom'])) < 1e-8]
        require(len(matches) == 1, 'Ambiguous old event match')
        master.append(dict(cohort='V2_first100', review_id=r['review_id'], dp_id=r['dp_id'],
            target=r['canonical_target'], fitted_center_bary_air_angstrom=r['fitted_center_bary_air_angstrom'],
            input_sha256=matches[0]['input_sha256'], current_code=status_codes[r['current_followup_status']],
            current_disposition=r['current_followup_status'], evidence_table='followup_synthesis/CUMULATIVE_333.csv',
            final_physical_origin_confirmed='False'))
    require(len(master) == 333 and count(master) == {'A': 209, 'O': 25, 'U': 95, 'M': 4, 'N': 0}, 'Old cohort changed')
    hits = {r['candidate_id']: r for r in rows(EXT / 'production/V2_HITS.csv')}
    for r in new:
        h = hits[r['candidate_id']]
        require(h['dp_id'] == r['dp_id'] and h['input_sha256'] == r['source_input_sha256'], 'New hit provenance changed')
        master.append(dict(cohort='V2_extension02', review_id=r['candidate_id'], dp_id=r['dp_id'], target=r['target'],
            fitted_center_bary_air_angstrom=h['fitted_center_angstrom'], input_sha256=h['input_sha256'],
            current_code=r['current_code'], current_disposition=r['current_disposition'],
            evidence_table='extension02/raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv', final_physical_origin_confirmed='False'))
    require(len(master) == len({r['review_id'] for r in master}) == 669, 'Combined cohort coverage mismatch')
    counts = count(new); total_counts = count(master)
    outputs = {}
    def put(path, content): outputs[path] = content
    def digest(path):
        return hashlib.sha256(outputs[path].encode()).hexdigest() if path in outputs else sha(path)
    put(PREVIOUS / 'CURRENT_V2_ALL336_DISPOSITIONS.csv', csvtext(new))
    put(PREVIOUS / 'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv', csvtext(all_selected))
    put(V2 / 'CURRENT_V2_DISPOSITIONS.csv', csvtext(master))
    current_summary = copy.deepcopy(prior_summary)
    current_summary.update(created_utc=timestamp, status='ROOT_ADOPTED_BATCH02_OVERLAY',
        basis='Original selected65 preserved; new68 decisions explicitly adopted after independent numerical audit and visual review. All physical origins remain provisional.',
        current_new_V2_counts=counts, current_all_V2_counts=total_counts,
        V2_raw_reviewed=669-counts['N'], V2_raw_unreviewed=counts['N'],
        latest_raw_batch=dict(directory='extension02/raw_followup_batch02', selected_events=68,
            selected_exposures=16, adopted_counts=adopted_counts,
            summary_sha256=sha(OUT/'SUMMARY.json'), adopted_dispositions_sha256=sha(OUT/'ADOPTED_DISPOSITIONS.csv')),
        all_original_and_baseline_files_unchanged=True)
    current_summary['source_hashes'].update({str(p.relative_to(V2)): sha(p) for p in
        [INPUT/'CURRENT_V2_ALL336_DISPOSITIONS.csv', INPUT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',
         INPUT/'CURRENT_SUMMARY.json', OUT/'SUMMARY.json', OUT/'ADOPTED_DISPOSITIONS.csv']})
    put(PREVIOUS/'CURRENT_SUMMARY.json', jsontext(current_summary))
    put(V2/'CURRENT_STATUS.json', jsontext(current_summary))
    pending = [r for r in new if r['current_code'] == 'N']
    main = rows(EXT/'MAIN100.csv'); queue = []
    for r in main:
        ids = [x['candidate_id'] for x in pending if x['dp_id'] == r['dp_id']]
        if ids:
            queue.append(dict(dp_id=r['dp_id'], target=r['canonical_target'], selection_index=int(r['selection_index']),
                pending_ids=ids, raw_progenitor_id=r['raw_progenitor_id'], ancillary_archive_id=r['ancillary_archive_id'],
                raw_source_url=r['raw_source_url'], ancillary_source_url=r['ancillary_source_url']))
    require(sum(len(r['pending_ids']) for r in queue) == len(pending), 'Pending queue omission')
    state['schema'] = 'SETI_CONTINUATION_STATE_V2'
    state['created_utc'] = timestamp
    state['science'].update(new_V2_current_codes=counts,
        new_V2_unresolved_ids=[r['candidate_id'] for r in new if r['current_code'] == 'U'],
        new_V2_mapping_limited_ids=[r['candidate_id'] for r in new if r['current_code'] == 'M'])
    state['latest_raw_batch'] = current_summary['latest_raw_batch']
    state['pending_raw_queue'] = dict(source=str((PREVIOUS/'CURRENT_V2_ALL336_DISPOSITIONS.csv').relative_to(REPO)),
        source_sha256=digest(PREVIOUS/'CURRENT_V2_ALL336_DISPOSITIONS.csv'),
        selection='Rows where current_code == N, retaining exact candidate IDs. Exposure queue follows MAIN100 selection order.',
        pending_events=len(pending), pending_exposures=len(queue), first_event=pending[0]['candidate_id'] if pending else None,
        first_exposure=queue[0] if queue else None,
        events=[{k:r[k] for k in ['candidate_id','dp_id','target','source_input_sha256']} for r in pending], exposure_queue=queue)
    state['next_action'] = dict(kind='PREPARE_NEXT_BOUNDED_RAW_BATCH' if pending else 'FOLLOW_UP_UNRESOLVED_CASES',
        directory_to_create='work_harps_20261101/v2/extension02/raw_followup_batch03',
        action='Prepare a separate bounded batch from this exact pending queue in MAIN100 order. Freeze selected IDs, raw/ancillary identities and limits before new arrays. Reuse hash-verified products; retain failed/omitted pairs without replacements. Do not rerun completed epoch or raw batches merely to resume.',
        queue_head=pending[0]['candidate_id'] if pending else None,
        reproduction_is_not_new_science=True, no_fixed_batch_selection_has_been_made_in_this_handoff=True)
    state['after_pending_raw_review'] = [
        'Follow up all current unresolved spectral structures, using continuous epoch metrics as context, not an origin veto.',
        'Investigate all current mapping limitations including the four older events V2-0149,V2-0231,V2-0232,V2-0333 in separately recorded follow-up.',
        'Continue the approved Rubin week (8–14 November); no Rubin analysis has been completed at this checkpoint.']
    state['previous_continuation_state'] = dict(path=str((INPUT/'CONTINUATION_STATE.json').relative_to(REPO)),
        sha256=sha(INPUT/'CONTINUATION_STATE.json'), historical_epoch_state='work_harps_20261101/v2/extension02/epoch_followup/CONTINUATION_STATE.json')
    archive_manifest = OUT/'checkpoints/LIBRARY_INPUTS.json'
    if archive_manifest.exists():
        archives = read(archive_manifest)
        if isinstance(archives, dict): archives = archives.get('archives', archives.get('files', []))
        require(isinstance(archives, list) and archives, 'Unrecognized batch02 archive manifest')
        require(all(r.get('status') == 'succeeded' and r.get('library_file_id') for r in archives), 'Incomplete batch02 archive checkpoint')
        state['input_archives'].extend(copy.deepcopy(archives))
    else:
        state['batch02_raw_input_checkpoint'] = 'NOT_YET_SAVED; original archive URLs and hashes remain in products/MANIFEST.json. Root must update before claiming saved raw inputs.'
    state['publication'] = dict(authorization=state['publication']['authorization'],
        authorization_quote=state['publication']['authorization_quote'], state='AWAITING_FINAL_PUBLICATION_READBACK',
        previous_verified_content_commit=state['publication'].get('verified_content_commit'),
        publication_success_must_be_verified_separately=True,
        receipt=BATCH_PATH+'/PUBLICATION_RECEIPT.json')
    state['execution'] = dict(active_science_workers=0, automatic_background_search=False,
        meaning_of_continuity='Durable source, results, explicit pending queue and reproducible next action; not an unattended scheduled job.')
    state['source_hashes'].update({str(p.relative_to(REPO)): digest(p) for p in
        [V2/'CURRENT_STATUS.json', PREVIOUS/'CURRENT_V2_ALL336_DISPOSITIONS.csv', V2/'CURRENT_V2_DISPOSITIONS.csv',
         OUT/'SUMMARY.json', OUT/'ADOPTED_DISPOSITIONS.csv', OUT/'FOLLOWUP_FREEZE.json']})
    if archive_manifest.exists(): state['source_hashes'][str(archive_manifest.relative_to(REPO))] = sha(archive_manifest)
    put(OUT/'CONTINUATION_STATE.json', jsontext(state))
    unresolved = ', '.join(state['science']['new_V2_unresolved_ids'])
    limited = ', '.join(state['science']['new_V2_mapping_limited_ids'])
    table = '\n'.join(f'| {label} | {counts[k]} |' for k,label in [('A','Provisional detector artefact'),('O','O I-compatible'),('U','Unresolved spectral structure'),('M','Insufficient raw mapping'),('N','No raw review yet')])
    first = queue[0] if queue else None
    next_text = (f"The next queue head is **{pending[0]['candidate_id']}**, exposure **{first['dp_id']}**, target **{first['target']}**." if pending else 'The raw-review queue is empty; proceed to explicitly unresolved cases.')
    put(REPO/'CONTINUE_SETI.md', f'''# Continue SETI from this checkpoint

Start with the [current continuation state]({BATCH_PATH}/CONTINUATION_STATE.json). Fetch current GitHub first and compare checkpoint hashes before starting; another session may have advanced the project. The state preserves every pending event ID, exposure/product identity and exact source hashes.

## Completed work

The survey contains **300 unique exposures of 20 targets, 70.874650833 hours**. V1 searched all300; V2 searched the latter200 and produced669 records. There is no qualified laser candidate and no calibrated null result.

The [epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md) is complete: all336 new V2 records against same-target exposures among the new100, 2,185 event/exposure pairs and4,370 profiles. Discovery observations are excluded from other-epoch summaries. Its independent numerical audit passed. Earlier200 exposures were excluded; follow-up adds no observing time. Do not repeat this calculation merely to resume.

[Raw batch02]({BATCH_PATH}/README.md) selected16 exposures and68 previously unreviewed V2 records in frozen MAIN100 order. It preserves the earlier65 selected V1/V2 decisions and the later mapping overlay. The current table covers all336 new V2 records:

| New V2 status | Count |
|---|---:|
{table}

New unresolved IDs: {unresolved or 'none'}.
New mapping-limited IDs: {limited or 'none'}.
The older333 remain209 A,25 O,95 U,4 M. Their mapping limitations are V2-0149,0231,0232,0333. All codes are provisional follow-up descriptions, not confirmed physical origins.

## Next action

{next_text} There are **{len(pending)} pending records in {len(queue)} exposures**. Follow the exact `current_code == N` queue in the current state; prepare a separate `raw_followup_batch03/` with selected IDs, raw/ancillary identities, fixed limits and analysis rules before new raw-array reads. Reuse verified cached pairs when available. Preserve failures/omissions and do not replace selected targets based on morphology.

Review every selected record and every covering order. Preserve original and later mapping decisions. After pending raw review, follow up all unresolved spectral structures and mapping limitations; epoch metrics provide context, not an origin veto. Rubin remains the approved second week (8–14 November) and has not been analyzed.

## Restore and verify

Restore input archives from the exact names, lengths, SHA-256 values and Library links in the current continuation state. Extract into a separate staging directory first. Member paths beginning `v2/extension02/` are relative to `work_harps_20261101/`. Copy verified science inputs without replacing newer status documents with historical report copies. The original four input packages cover the100 science spectra and first8 raw/ancillary pairs; batch02 raw inputs require the separate checkpoint recorded for this batch.

GitHub preserves all4,370 epoch profiles in [18 ordered parts](work_harps_20261101/v2/extension02/epoch_followup/PROFILE_ARRAYS_PARTS.json). Run `python3 restore_profile_archive.py` inside `epoch_followup`; it validates and reconstructs the exact ZIP. Extract there to restore `profiles/`. See [restoration instructions](work_harps_20261101/v2/RESTORE.md) and each batch's README for audit commands. Run audits in a separate working copy because reports get rewritten. Use installed packages and recorded versions; do not rely on an earlier session's absolute runtime path.

## Maintain continuity

After each verified batch, save source IDs/hashes, commands and outcomes, decisions, unresolved cases, evidence and exact next queue. Keep frozen catalogs and historical results unchanged. Publish the new result, then verify remote branch heads and key file hashes before claiming GitHub is current. The user explicitly authorized public GitHub updates on1 November2026. Earlier archive notes requesting approval are historical.

This locally generated checkpoint awaits final publication readback; root records the verified delivery in `{BATCH_PATH}/PUBLICATION_RECEIPT.json`. No automatic background science search is configured. Durable evidence and a precise queue support later continuation; they do not imply execution between turns.
''')
    put(PREVIOUS/'CURRENT_RESULTS.md', f'''# Aktuel råopfølgning på den nye HARPS-prøve

**{336-counts['N']} af336 nye V2-poster er rågennemgået; {counts['N']} mangler.** Alle vurderinger er foreløbige. Ingen kvalificeret laser- eller SETI-kandidat er identificeret.

| Aktuel status | Antal |
|---|---:|
{table}
| Hele det nye katalog | 336 |

Den første faste gruppe omfattede59 V2-poster og6 V1-poster fra8 eksponeringer. De6 V1 matcher V2-poster og er ikke6 ekstra uafhængige fænomener. Baseline og den senere bredere billedkobling er bevaret uændret. [Batch02](../raw_followup_batch02/README.md) udvalgte derefter68 hidtil ikke rågennemgåede V2-poster i16 eksponeringer fra den nøjagtige restkø; alle dækkende ordener indgår i billedkoblingskravet. Numerisk kontrol og visuelle vurderinger er dokumenteret særskilt. Agentkontrol er ikke menneskelig fagfællebedømmelse eller nye observationer.

Aktuelle uafklarede nye poster: {unresolved or 'ingen'}.
Aktuelle nye begrænsninger i billedkobling: {limited or 'ingen'}.

[Alle336 aktuelle poster](CURRENT_V2_ALL336_DISPOSITIONS.csv) · [alle133 udvalgte V1/V2-poster](CURRENT_SELECTED_EVENT_DISPOSITIONS.csv) · [aktuel opsummering](CURRENT_SUMMARY.json) · [ny statuskombinationskode](../raw_followup_batch02/update_current.py) · [præcis restkø](../raw_followup_batch02/CONTINUATION_STATE.json) · [tidligere baseline](RESULTS.md) · [tidligere bredere billedkobling](mapping_followup/README.md).

Oprindelige produktionskataloger, baselinetabeller og alle tidligere afgørelser bevares. Kolonner med baseline-status beskriver det historiske trin; `current_code` og `current_evidence_table` angiver gældende opfølgning. Reglerne for billedkobling varierer mellem historiske trin. Der er ingen global følsomheds- eller falsk-alarm-kalibrering og intet kvalificeret nulresultat for lasere.
''')
    put(V2/'RESTORE.md', f'''# Gendannelse og fortsættelse efter300 HARPS-eksponeringer

Start i [CONTINUE_SETI.md](../../CONTINUE_SETI.md) og [den aktuelle maskinlæsbare tilstand](extension02/raw_followup_batch02/CONTINUATION_STATE.json). Hent seneste GitHub-version før arbejde; tidligere sessioner og arkivrapporter kan være historiske.

Hovedprøven er300 unikke eksponeringer af20 stjerner,255.148,743 sekunder (70,874651 timer). V1 har22 træf på300 eksponeringer. V2 har333 oprindelige og336 nye poster på200 eksponeringer; de første100 er ikke genkørt med V2. Originale detektorkoder, indstillinger og kataloger er uændrede.

## Aktuel videnskabelig status

Oprindelige333:209 A,25 O,95 U,4 M i `followup_synthesis/CUMULATIVE_333.csv`. Deres epokekontrol omfattede117 relevante eksponeringer blandt de tidligere200:91 barycentrisk vedvarende,3 med kalibreringsrefleks-hypotese,1 svag O I-hypotese. Det er beskrivende kontekst, ikke automatiske oprindelsesvetoer.

Nye336: {counts['A']} A, {counts['O']} O, {counts['U']} U, {counts['M']} M, {counts['N']} N i `extension02/raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv`. Alle669 er samlet i `CURRENT_V2_DISPOSITIONS.csv` med eksplicit kohorte og evidenskilde. Første rågruppe omfattede59 V2+6 V1-poster i8 eksponeringer; den senere billedkobling er bevaret separat. Batch02 udvalgte68 V2-poster i16 yderligere eksponeringer. Historiske baseline-felter skal ikke fortolkes som gældende status.

Den nye epokekontrol af alle336 poster mod samme mål i de nye100 spektre er afsluttet:2.185 par,4.370 profiler, uafhængig numerisk kontrol bestået. Genkør den ikke blot for at fortsætte. Næste opgave er restkøen på{len(pending)} poster/{len(queue)} eksponeringer, efterfulgt af uafklarede strukturer og billedkoblinger. Rubin-ugen8.–14. november er endnu ikke analyseret.

## Input og evidens

Klon/hent `andersenmartin-blip/setisearch`, branch `optical-harps-week-20261101`, og gå til `work_harps_20261101`. De oprindelige input er linket i [V2-rapporten](README.md) og råinput i [batch01](triage_batch01/README.md), [batch02](triage_batch02/README.md) samt `triage_followup/`.

De fire første extension02-inputpakker indeholder100 1D-FITS og16 oprindelige RAW/TAR-produkter; se [gemte input](extension02/checkpoints/SAVED_INPUTS.md). Batch02's nye råinput skal gendannes fra det særskilte checkpoint i dens tilstandsfil. Kontroller arkiv- og medlemshashes. Udpak til separat stagingmappe; `v2/extension02/`-medlemmer er relative til `work_harps_20261101`. Kopier ikke historiske statusrapporter oven på nyere filer. Ufuldstændige diagnostiske overførselsfiler er aldrig analyseinput.

Evidensarkiver for ældre opfølgninger ligger i deres respektive mapper. Alle336 nye1D-udsnit er i `extension02/review1d/EXTENSION02_REVIEW1D_EVIDENCE.zip`; første rågruppe i `extension02/raw_followup/RAW_BASELINE_EVIDENCE.zip`. Batch02's README beskriver den nye evidens. Alle4.370 epokeprofiler rekonstrueres fra18 GitHub-dele med `python3 restore_profile_archive.py` inde i `extension02/epoch_followup`; scriptet kontrollerer dele og samlet SHA-256 før udpakning.

## Reproduktion

Brug Python3 med NumPy, SciPy, Astropy og Matplotlib; de seneste registrerede kørsler bruger Python3.12.14, NumPy2.3.5, SciPy1.17.0 og Astropy8.0.2. Brug aktuelle installerede pakker, ikke tidligere sessioners absolutte runtime-stier. Følg hver analyses registrerede versioner ved eksakt numerisk reproduktion.

Kør audits i en separat kopi med hashverificerede input, da de skriver nye rapporter. Fra `work_harps_20261101`:

```bash
python3 v2/extension02/audit/run_audit.py
python3 v2/extension02/raw_followup/audit/run_numeric_audit.py
python3 v2/extension02/epoch_followup/independent_audit/check_epochs.py
```

Se batch02's README for dens kontrolkommando. Fuld produktionsreproduktion er valgfri og kræver separate outputmapper. Bevar publicerede metadata og timestamps ved kildehashkontrol; en reproduktions nye tidsstempler er ikke ændret videnskab.

Visuelle vurderinger er foreløbige agentvurderinger, ikke en fysisk classifier eller menneskelig fagfællebedømmelse. Historiske billedkoblingsregler er heterogene. Opfølgningen giver ikke global følsomhed, falsk-alarm-rate eller et kvalificeret fravær af lasersignaler. Ingen automatisk baggrundssøgning er konfigureret.
''')
    # A second identical apply is harmless. A different current cohort is a concurrency conflict.
    live = PREVIOUS/'CURRENT_V2_ALL336_DISPOSITIONS.csv'
    require(sha(live) in [sha(INPUT/'CURRENT_V2_ALL336_DISPOSITIONS.csv'), digest(live)],
            'Current336 differs from both frozen predecessor and this exact overlay; inspect concurrent work')
    if args.apply:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print(json.dumps(dict(mode='APPLIED' if args.apply else 'DRY_RUN', new_counts=counts,
        all_counts=total_counts, selected_rows=len(all_selected), pending_events=len(pending),
        pending_exposures=len(queue), next_event=pending[0]['candidate_id'] if pending else None,
        output_files=[str(p.relative_to(REPO)) for p in outputs]), indent=2))

if __name__ == '__main__':
    main()
