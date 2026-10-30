"""Validate and package terminal BN evidence without running search or decoding.

A COMPLETE terminal permits a complete descriptive summary. A STOP terminal
retains partial outputs and failure receipts while crediting only closed,
audited batches. Existing scientific and packaging artifacts are never
overwritten. ZIP parts are consecutive byte ranges, not separate ZIP files.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_bn'
EXPECTED_BATCHES = ([list(range(start, start + 8)) for start in range(1, 121, 8)]
                    + [list(range(121, 128))]
                    + [list(range(start, start + 8)) for start in range(129, 249, 8)]
                    + [list(range(249, 255))])
EXPECTED_Q = list(range(1, 128)) + list(range(129, 255))
PART_BYTES = 200 * 1024 * 1024
WIDTHS = (1, 3, 9, 33)
TOTAL_KEYS = ('ON_catalog_rows', 'OFF_catalog_rows', 'passing_flags', 'total_track_trials',
              'forced_measurement_slots', 'supported_forced_measurements', 'unsupported_forced_slots',
              'fixed_scalar_sum_comparisons', 'shared_kernel_calibration_vector_replays',
              'search_wall_seconds', 'audit_wall_seconds', 'search_user_cpu_seconds',
              'search_system_cpu_seconds', 'audit_user_cpu_seconds', 'audit_system_cpu_seconds')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def verify_pins(pins):
    for path, digest in pins.items():
        require(sha(path) == digest, 'Retained audit/source artifact changed: ' + path)


def add_pin(pins, path, digest):
    path = str(Path(path).resolve())
    require(path not in pins or pins[path] == digest, 'Conflicting retained artifact pin: ' + path)
    pins[path] = digest


def frequency_intervals(qs):
    if not qs:
        return []
    groups = [[qs[0]]]
    for q in qs[1:]:
        if q == groups[-1][-1] + 1:
            groups[-1].append(q)
        else:
            groups.append([q])
    return [dict(q_first=g[0], q_last=g[-1],
                 frequency_center_limits_mhz=[2298.92578125 + ((g[-1]+1)*4096-1)*(-2.7939677238464355)/1e6,
                                              2298.92578125 + g[0]*4096*(-2.7939677238464355)/1e6])
            for g in groups]


def actual_receipt(path, success_required):
    value = read(path)
    log = Path(value['log_path'])
    require(log.is_file() and log.stat().st_size == value['log_bytes']
            and sha(log) == value['log_sha256'], 'Saved actual-process log changed: ' + str(path))
    observed_exact = (value['log_sha256'] == value['observed_stdout_sha256']
                      and value['log_bytes'] == value['observed_stdout_bytes'])
    if success_required:
        require(value['actual_exit_code'] == 0 and value['capture_error'] is None
                and value['stdout_eof'] is True and value['child_wait_completed'] is True
                and value['stdout_fully_preserved'] is True and observed_exact,
                'Closed batch actual-process capture did not pass: ' + str(path))
    return dict(path=str(Path(path).resolve()), sha256=sha(path),
                saved_log_identity_verified=True, observed_stdout_equals_saved_log=observed_exact,
                closed_audited_success_required=success_required, receipt=value)


def split_archive(archive):
    parts = []
    with archive.open('rb') as stream:
        offset = 0
        number = 1
        while True:
            chunk = stream.read(PART_BYTES)
            if not chunk:
                break
            path = Path(str(archive) + f'.part{number:02d}')
            with path.open('xb') as destination:
                destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            digest = hashlib.sha256(chunk).hexdigest()
            require(path.stat().st_size == len(chunk) and sha(path) == digest, 'Saved archive part differs')
            parts.append(dict(part=number, file_name=path.name, local_path=str(path.resolve()),
                              offset=offset, bytes=len(chunk), sha256=digest))
            offset += len(chunk)
            number += 1
    joined = hashlib.sha256()
    total = 0
    for part in parts:
        require(part['bytes'] <= PART_BYTES and part['offset'] == total, 'Nonconsecutive archive part')
        with Path(part['local_path']).open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                joined.update(chunk)
                total += len(chunk)
    require(total == archive.stat().st_size and joined.hexdigest() == sha(archive),
            'Reassembled archive identity differs')
    return parts


def main():
    require(len(EXPECTED_BATCHES) == 32 and [q for g in EXPECTED_BATCHES for q in g] == EXPECTED_Q
            and len(EXPECTED_Q) == 253, 'Finalizer fixed geometry differs')
    complete_path = WORK / 'results/CAMPAIGN_COMPLETE_BN.json'
    stop_path = WORK / 'results/CAMPAIGN_STOP_BN.json'
    require(complete_path.is_file() != stop_path.is_file(), 'Exactly one terminal campaign marker required')
    is_complete = complete_path.is_file()
    terminal_path = complete_path if is_complete else stop_path
    terminal = read(terminal_path)
    start_path = WORK / 'execution/CAMPAIGN_START_BN.json'
    start = read(start_path)
    require(start['frozen_q_list'] == EXPECTED_Q and start['frozen_batch_count'] == 32,
            'Campaign start scope differs')
    require(start['prereg_github_commit'] == terminal['prereg_github_commit'], 'Terminal preregistration differs')
    require(terminal['background_science_jobs_running'] is False, 'Terminal campaign must be quiescent')
    batches = terminal['batch_results']
    require(terminal['completed_batches'] == len(batches) <= 32, 'Closed batch count differs')
    require([b['batch'] for b in batches] == list(range(1, len(batches)+1)), 'Closed batches are not a prefix')
    completed_q = []
    pins = dict(start['input_source_plan_sha256'])
    add_pin(pins, start_path, sha(start_path))
    add_pin(pins, terminal_path, sha(terminal_path))
    for batch in batches:
        number = batch['batch']
        require(batch['q_list'] == EXPECTED_BATCHES[number-1], 'Closed batch carrier list differs')
        completed_q.extend(batch['q_list'])
        require(batch['actual_search_exit_code'] == batch['actual_audit_exit_code'] == 0,
                'Only successful searched/audited batches may be credited')
        for key in ['search_actual', 'audit_actual', 'audit_result', 'complete_result', 'plan']:
            add_pin(pins, batch[key+'_path'], batch[key+'_sha256'])
        audit = read(batch['audit_result_path'])
        require(audit['status'] == 'PASS_CLOSED_BOUNDED_REAL_RESULTS', 'Closed audit status differs')
        require(audit['fixed_scalar_sum_comparisons'] == len(batch['q_list'])*216
                and audit['shared_kernel_calibration_vector_replays'] == len(batch['q_list'])*72,
                'Closed variable-batch audit counts differ')
        for path, digest in audit['input_and_artifact_sha256'].items():
            add_pin(pins, path, digest)
        search_actual = actual_receipt(batch['search_actual_path'], True)['receipt']
        audit_actual = actual_receipt(batch['audit_actual_path'], True)['receipt']
        complete = read(batch['complete_result_path'])
        require(complete['q_list'] == batch['q_list']
                and complete['plan_sha256'] == batch['plan_sha256'] == audit['plan_sha256']
                and complete['status'] == 'ALL_FROZEN_BATCH_SEARCHES_AND_TRIAGE_COMPLETE'
                and audit['complete_result_sha256'] == batch['complete_result_sha256']
                == search_actual['result_sha256'], 'Closed batch result bindings differ')
        scans = []
        for q in batch['q_list']:
            scans.extend(read(Path(batch['complete_result_path']).parent / f'q{q:03d}' / 'SIX_SCAN_SEARCH_COMPLETE.json')['scans'])
        derived = dict(
            ON_catalog_rows=sum(r['ON_local_catalog_rows'] for r in complete['q_results']),
            OFF_catalog_rows=sum(s['local_hits'] for s in scans if s['role'] == 'OFF'),
            passing_flags=sum(r['all3ON_ge10_noOFF_rows'] for r in complete['q_results']),
            total_track_trials=complete['total_track_trials'],
            forced_measurement_slots=sum(r['forced_measurement_slots'] for r in complete['q_results']),
            supported_forced_measurements=sum(r['supported_slots'] for r in complete['q_results']),
            unsupported_forced_slots=sum(r['unsupported_slots'] for r in complete['q_results']),
            fixed_scalar_sum_comparisons=audit['fixed_scalar_sum_comparisons'],
            shared_kernel_calibration_vector_replays=audit['shared_kernel_calibration_vector_replays'],
            maximum_scalar_sum_error=audit['maximum_scalar_sum_error'],
            maximum_replayed_calibration_error=audit['maximum_replayed_calibration_error'],
            search_wall_seconds=search_actual['wall_seconds'], audit_wall_seconds=audit_actual['wall_seconds'],
            search_user_cpu_seconds=search_actual['child_user_cpu_seconds'],
            search_system_cpu_seconds=search_actual['child_system_cpu_seconds'],
            audit_user_cpu_seconds=audit_actual['child_user_cpu_seconds'],
            audit_system_cpu_seconds=audit_actual['child_system_cpu_seconds'],
            maximum_local_ESS_by_width={str(w):{role:max(ws['maximum_local_ess'] for s in scans
                if s['role'] == role for ws in s['width_searches'] if ws['width_channels'] == w)
                for role in ['ON','OFF']} for w in WIDTHS})
        require(all(batch[k] == v for k, v in derived.items()), 'Closed batch metrics differ from saved evidence')
        require(derived['total_track_trials'] == len(batch['q_list'])*54125568 == audit['track_trials']
                and audit_actual['result_sha256'] == batch['audit_result_sha256'],
                'Closed batch detector/audit computational bindings differ')
    if is_complete:
        require(terminal['status'] == 'ALL_THIRTY_TWO_BATCHES_SEARCHED_AND_AUDITED'
                and terminal['q_list'] == EXPECTED_Q and completed_q == EXPECTED_Q,
                'Complete terminal scope differs')
        require(terminal['total_track_trials'] == 13693768704 and len(batches) == 32,
                'Complete terminal computational count differs')
        for path, digest in terminal['input_source_plan_sha256'].items():
            add_pin(pins, path, digest)
    else:
        require(terminal['status'] == 'STOPPED_NO_NEXT_BATCH', 'Unknown stopped terminal status')
    prepared_path = ROOT / 'work_bk/next_data/PREPARED_ADJACENT_DATA_BK.json'
    prepared = read(prepared_path)
    reference_plan = read(WORK / 'plans/batch01.json')
    require(Path(reference_plan['prepared_adjacent_receipt_path']).resolve() == prepared_path.resolve(),
            'Prepared raw-data receipt path differs')
    add_pin(pins, prepared_path, reference_plan['prepared_adjacent_receipt_sha256'])
    expected_rows = {f['scan_id']:[r['sha256'] for r in f['decoded_rows']]
                     for f in prepared['files'] if f['native'] == 172}
    require(len(expected_rows) == 6 and all(len(v) == 16 for v in expected_rows.values()), 'Raw row receipt differs')
    row_checks = []
    for marker in sorted((WORK/'results').glob('batch*/run/NORMALIZED_INPUTS_COMPLETE.json')):
        number = int(marker.parents[1].name.removeprefix('batch'))
        plan_path = WORK / 'plans' / f'batch{number:02d}.json'
        plan, normalized = read(plan_path), read(marker)
        require(normalized['status'] == 'PASS' and normalized['plan_sha256'] == sha(plan_path),
                'Normalization plan binding differs')
        require(len(normalized['scans']) == 6 and normalized['full_native_channel_count'] == 1048576,
                'Normalization scan geometry differs')
        for scope, scan in zip(plan['scans'], normalized['scans'], strict=True):
            require(scan['scan'] == scope['scan'] and scan['input_sha256'] == scope['input_sha256']
                    and scan['full_native_row_sha256'] == expected_rows[scope['label']],
                    'Decoded native172 row identity differs')
        add_pin(pins, marker, sha(marker))
        row_checks.append(dict(batch=number, matched_decoded_row_hashes=96, marker_sha256=sha(marker),
                               closed_audited_batch=number <= len(batches)))
    verify_pins(pins)
    captures = []
    for actual in sorted((WORK/'execution').glob('batch*/*_ACTUAL_EXIT_BN.json')):
        number = int(actual.parent.name.removeprefix('batch'))
        require(1 <= number <= min(32, len(batches)+1), 'Unexpected process capture batch')
        captured = actual_receipt(actual, number <= len(batches))
        value = captured['receipt']
        require(actual.name in ['SEARCH_ACTUAL_EXIT_BN.json','REAL_RESULT_AUDIT_ACTUAL_EXIT_BN.json'],
                'Unknown process capture role')
        source = (WORK / 'bounded_search_bn.py' if actual.name.startswith('SEARCH_')
                  else WORK / 'review/audit_real_results_bn.py')
        plan = WORK / 'plans' / f'batch{number:02d}.json'
        require(value['batch'] == number and value['prereg_github_commit'] == terminal['prereg_github_commit']
                and value['source_sha256'] == pins[str(source.resolve())]
                and value['plan_sha256'] == pins[str(plan.resolve())],
                'Process capture source/plan/preregistration identity differs')
        if value['result_sha256'] is not None:
            add_pin(pins, value['result_path'], value['result_sha256'])
        add_pin(pins, actual, captured['sha256'])
        add_pin(pins, captured['receipt']['log_path'], captured['receipt']['log_sha256'])
        captures.append(captured)
    require(len(captures) >= 2*len(batches), 'Missing closed-batch process capture')
    if is_complete:
        require(len(captures) == 64, 'Complete campaign must have exactly 64 closed process captures')
    verify_pins(pins)
    totals = {key:sum(b[key] for b in batches) for key in TOTAL_KEYS}
    require(totals['total_track_trials'] == len(completed_q)*54125568,
            'Closed computational count differs')
    if is_complete:
        require(totals['passing_flags'] == 0 and totals['total_track_trials'] == terminal['total_track_trials'],
                'Complete campaign cannot contain a passing descriptive flag')
    maxima = {str(w):{role:max((b['maximum_local_ESS_by_width'][str(w)][role] for b in batches), default=None)
                       for role in ['ON', 'OFF']} for w in WIDTHS}
    status = 'PASS_CLOSED_SEARCH_AND_BOUNDED_AUDIT' if is_complete else 'PARTIAL_STOPPED_NO_NEXT_BATCH'
    assessment = ('No qualified SETI candidate; no descriptive ON/OFF flags passed.'
                  if is_complete else 'Stopped campaign; only the listed closed batches are credited. '
                  'Inspect terminal reason, any descriptive flags, and retained failed/partial outputs before further work.')
    assessment += ' Local ESS is not calibrated sigma/SNR/FAP or astronomical sensitivity.'
    next_action = ('Reassess access to additional telescope data and qualification/calibration of the search under a separate frozen plan; preserve all historical A/B and B06 failure and no-retry states.'
                   if is_complete else 'Manual inspection of the stopped campaign; no automatic retry or next search.')
    summary = dict(schema='SETI_BN_NATIVE172_TERMINAL_RESULTS_V1', status=status,
        finalized_utc=datetime.now(timezone.utc).isoformat(), finite_campaign_completed=is_complete,
        full_scope_coverage_claim=is_complete, prereg_github_commit=terminal['prereg_github_commit'],
        target='HIP98505 / HD189733', observation_date='2017-04-28', native_chunk_index=172,
        frozen_q_list=EXPECTED_Q, q_list=completed_q, completed_batches=len(batches),
        carrier_channels=len(completed_q)*4096, scan_core_searches=len(completed_q)*6,
        technical_width_hz=len(completed_q)*4096*2.7939677238464355,
        carrier_frequency_center_intervals=frequency_intervals(completed_q), excluded_carrier_q=[0,128,255],
        campaign_wall_seconds=terminal['wall_seconds'], totals=totals, maximum_local_ESS_by_width=maxima,
        maximum_scalar_sum_error=max((b['maximum_scalar_sum_error'] for b in batches), default=None),
        maximum_replayed_calibration_error=max((b['maximum_replayed_calibration_error'] for b in batches), default=None),
        repeated_row_hash_checks=row_checks, unique_expected_native172_rows=96,
        unique_recovered_decoded_rows=96 if row_checks else 0,
        all_counted_searches_and_audits_actual_exit_zero=True, retained_verified_pin_count=len(pins),
        terminal_marker_path=str(terminal_path.resolve()), terminal_marker_sha256=sha(terminal_path),
        terminal_reason=terminal.get('reason'),
        capture_attempts=len(captures), nonzero_or_missing_exit_capture_attempts=sum(
            c['receipt']['actual_exit_code'] != 0 for c in captures),
        all_capture_attempt_wall_seconds=sum(c['receipt']['wall_seconds'] for c in captures),
        prepared_adjacent_receipt_sha256=sha(prepared_path),
        new_archive_requests=0, new_observations=0, new_unique_archive_ID_credit=0, cost_DKK=0,
        BA_authoritative_archive_IDs_unchanged=486,
        BA_authoritative_technical_MHz_visits_unchanged=268.50128173828125,
        candidate_assessment=assessment, historical_outcomes_preserved=prepared['historical_outcomes_preserved'],
        next_action=next_action, background_science_jobs_running=False)
    summary_path = WORK / 'results/REAL_SEARCH_SUMMARY_BN.json'
    write(summary_path, summary)
    add_pin(pins, summary_path, sha(summary_path))
    add_pin(pins, Path(__file__).resolve(), sha(__file__))
    binary_paths = sorted(p for p in (WORK/'results').rglob('*') if p.is_file() and p.suffix in ['.npy','.npz'])
    members = []
    for path in binary_paths:
        relative = path.relative_to(WORK)
        number = int(relative.parts[1].removeprefix('batch'))
        closed = number <= len(batches)
        require(not closed or str(path.resolve()) in pins, 'Closed binary missing from audit pins: '+str(path))
        digest = sha(path)
        if closed:
            require(digest == pins[str(path.resolve())], 'Closed binary changed before archive')
        members.append(dict(path=str(relative), bytes=path.stat().st_size, sha256=digest,
                            batch=number, closed_audited_batch=closed,
                            forensic_partial_output=not closed))
    resume = dict(schema='SETI_BN_BINARY_RESULTS_RESUME_V1', prereg_github_commit=terminal['prereg_github_commit'],
        repository='andersenmartin-blip/setisearch', branch='m43-support-qualification',
        summary=summary, binary_members=members, original_raw_parts=prepared['parts'],
        raw_archive_sha256=prepared['archive_sha256'], terminal_marker=terminal,
        actual_capture_receipts=captures, retained_verified_artifact_pins=pins,
        note='Restore in a distinct namespace; do not overwrite or rerun closed BN. '
             'Uncounted partial binaries are forensic evidence, not complete scan/search results. '
             'Source, plans, detailed result JSON and logs are published on GitHub.')
    delivery_dir = ROOT.parent / 'deliveries'
    delivery_dir.mkdir(exist_ok=True)
    archive = delivery_dir / 'SETI_BN_SEARCH_RESULTS_2026-10-30.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for path, record in zip(binary_paths, members, strict=True):
            z.write(path, record['path'])
        z.writestr('RESUME_BN.json', json.dumps(resume, indent=2, sort_keys=True)+'\n')
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, 'ZIP CRC check failed')
        require(len(z.infolist()) == len(members)+1, 'ZIP member count differs')
        for record in members:
            content = z.read(record['path'])
            require(len(content) == record['bytes'] and hashlib.sha256(content).hexdigest() == record['sha256'],
                    'ZIP member bytes differ: '+record['path'])
        require(json.loads(z.read('RESUME_BN.json')) == resume, 'ZIP resume metadata differs')
    for path, record in zip(binary_paths, members, strict=True):
        require(path.stat().st_size == record['bytes'] and sha(path) == record['sha256'],
                'Binary changed during packaging: '+str(path))
    verify_pins(pins)
    add_pin(pins, archive, sha(archive))
    parts = split_archive(archive)
    for part in parts:
        add_pin(pins, part['local_path'], part['sha256'])
    manifest_path = delivery_dir / 'SETI_BN_SEARCH_RESULTS_2026-10-30_MANIFEST.json'
    manifest = dict(schema='SETI_BN_ORDERED_ZIP_PART_MANIFEST_V1', status=status,
        archive_file_name=archive.name, archive_bytes=archive.stat().st_size, archive_sha256=sha(archive),
        archive_members=len(members)+1, binary_members=len(members),
        all_member_CRC_and_SHA256_verified=True, reassembled_part_bytes_and_SHA256_verified=True,
        part_maximum_bytes=PART_BYTES, parts=parts, summary=summary,
        reconstruction='Concatenate the complete parts in ascending integer part order into archive_file_name. '
                       'Verify archive_bytes and archive_sha256 before opening the ZIP; parts are not separate ZIP archives.')
    write(manifest_path, manifest)
    add_pin(pins, manifest_path, sha(manifest_path))
    verify_pins(pins)
    delivery = dict(schema='SETI_BN_DELIVERY_V1', stage='BN', status=status,
        finite_campaign_completed=is_complete, prereg_github_commit=terminal['prereg_github_commit'],
        archive_path=str(archive.resolve()), archive_bytes=archive.stat().st_size, archive_sha256=sha(archive),
        archive_members=len(members)+1, all_member_CRC_and_SHA256_verified=True,
        parts=parts, manifest_path=str(manifest_path.resolve()), manifest_sha256=sha(manifest_path),
        summary_path=str(summary_path.resolve()), summary_sha256=sha(summary_path),
        next_action=summary['next_action'])
    write(WORK / 'DELIVERY_BN.json', delivery)
    print(json.dumps(delivery, indent=2))


if __name__ == '__main__':
    main()

