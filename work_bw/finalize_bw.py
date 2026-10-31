"""Aggregate BW's closed q254 evidence; do not run a detector or change rules."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, zipfile

ROOT = Path(__file__).resolve().parents[1]
BW = ROOT / 'work_bw'

def read(p):
    return json.loads(Path(p).read_text())

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    plan = read(BW / 'BW_PARTIAL_PLAN.json')
    serial = read(BW / 'execution/SERIAL_RUN_RESULT.json')
    base = BW / 'execution/batch1'
    child = read(base / 'payload/RESULT.json')
    cap = read(base / 'ACTUAL_RECEIPT.json')
    export = read(base / 'PARENT_EXPORT_VERIFICATION.json')
    acap = read(BW / 'audit_execution/batch1/ACTUAL_RECEIPT.json')
    auditpath = BW / 'review/BATCH1_INDEPENDENT_REVIEW.json'
    audit = read(auditpath)
    parentpath = ROOT / 'work_bv/SUMMARY_BV.json'
    parent = read(parentpath)
    assert serial['status'] == child['status'] == cap['status'] == export['status'] == acap['status'] == 'PASS'
    assert serial['all_planned_batches_completed'] and len(serial['completed_batches']) == 1
    assert cap['actual_exit_code'] == acap['actual_exit_code'] == 0 and cap['stdout_eof'] and acap['stdout_eof']
    assert all(c['child_wait_completed'] and c['natural_stdout_eof'] and not c['killed'] for c in (cap, acap))
    assert cap['result_sha256'] == sha(base / 'payload/RESULT.json')
    assert audit['status'] == 'PASS_BOUNDED_INDEPENDENT_REVIEW'
    archive = base / 'payload/EVIDENCE.zip'
    assert sha(archive) == child['archive']['sha256']
    with zipfile.ZipFile(archive) as z:
        raw = z.read('BATCH_COMPLETE.json')
        batch = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == audit['batch_complete_sha256']
    ph = sha(BW / 'BW_PARTIAL_PLAN.json')
    assert batch['q_list'] == plan['core_q_list'] == [254]
    assert batch['plan_sha256'] == audit['plan_sha256'] == serial['plan_sha256'] == ph
    assert batch['track_trials'] == 45104640 and len(batch['results']) == 1
    item = batch['results'][0]
    assert item['q'] == 254 and len(item['scans']) == 5
    scans = []
    for record, scope in zip(item['scans'], plan['scans']):
        assert record['scan'] == scope['scan'] and record['track_trials'] == 9020928
        scans.append(dict(scan=scope['scan'], role=scope['role'], target=scope['target'],
                          archive_id=scope['archive_id'], catalog_rows=record['local_hits'],
                          maximum_local_ess=max(w['maximum_local_ess'] for w in record['width_searches']),
                          correlated_track_combinations=record['track_trials']))
    assoc = item['association']
    counts = assoc['status_counts']
    onrows = sum(s['catalog_rows'] for s in scans if s['role'] == 'ON')
    assert onrows == sum(counts.values()) == assoc['ON_local_catalog_rows'] == audit['ON_seed_rows_all_semantically_reviewed']
    assert counts == audit['status_counts']
    previous = parent['combined_BU_BV']
    assert previous['q_list'] == list(range(1,254)) and parent['complete_OFF_support'] is False
    combined_counts = {k: parent['partial_status_counts'][k] + counts[k] for k in counts}
    summary = dict(
        schema='SETI_BW_Q254_RESULT_V1', status='COMPLETED_FIVE_SCAN_PARTIAL_BOUNDARY_EXTENSION',
        completed_utc=datetime.now(timezone.utc).isoformat(), target='HIP44295', primary_id=65133,
        public_freeze_commit=read(BW / 'PUBLIC_FREEZE_RECEIPT_BW.json')['public_commit_sha'],
        plan_sha256=ph, serial_result_sha256=sha(BW / 'execution/SERIAL_RUN_RESULT.json'),
        serial_wall_seconds=serial['wall_seconds'], q_list=[254], new_q_count=1, new_scan_q_count=5,
        new_correlated_track_combinations=45104640, new_ON_correlated_track_combinations=27062784,
        new_carrier_bin_width_mhz=4096 * abs(plan['scans'][0]['df_hz']) / 1e6,
        scans=scans, all_scan_catalog_rows=sum(s['catalog_rows'] for s in scans), ON_seed_rows=onrows,
        partial_status_counts=counts, three_ON_pass_rows=assoc['three_ON_pass_rows'],
        available_OFF_veto_rows=assoc['available_OFF_veto_rows'], maximum_local_ess=max(s['maximum_local_ess'] for s in scans),
        threshold_ess=10, available_OFF_flag_threshold_ess=5,
        combined_BU_BV_BW=dict(q_list=list(range(1,255)), q_count=254, scan_q_count=1270,
            correlated_track_combinations=previous['correlated_track_combinations'] + 45104640,
            carrier_bin_width_mhz=254 * 4096 * abs(plan['scans'][0]['df_hz']) / 1e6,
            frequency_max_mhz=plan['scans'][0]['fch1_mhz'] + 4096 * plan['scans'][0]['df_hz'] / 1e6,
            frequency_min_mhz=plan['scans'][0]['fch1_mhz'] + (255*4096-1) * plan['scans'][0]['df_hz'] / 1e6,
            maximum_local_ess=max(parent['maximum_local_ess'], max(s['maximum_local_ess'] for s in scans)),
            partial_status_counts=combined_counts, all_scan_catalog_rows=parent['all_scan_catalog_rows'] + sum(s['catalog_rows'] for s in scans),
            parent_BV_summary_sha256=sha(parentpath), parent_BV_commit='dc24c8636f8ca3511226007b846dc249e61608d1'),
        independent_review=dict(path=str(auditpath), sha256=sha(auditpath),
            scalar_checks=audit['independent_scalar_audit_sums'], calibration_vectors=audit['independent_calibration_vectors'],
            selected_forced_measurement_slots=audit['independent_selected_forced_measurement_slots'],
            maximum_scalar_error=audit['maximum_scalar_sum_error'], maximum_calibration_error=audit['maximum_calibration_error'],
            maximum_forced_ess_error=audit['maximum_selected_forced_ess_error'], normalization_review=audit['normalization_review']),
        closed_archive=dict(path=str(archive), bytes=archive.stat().st_size, sha256=sha(archive)),
        both_actual_exit_codes=0, both_natural_stdout_eof=True,
        complete_OFF_support=False, missing_scan=5, full_cadence_candidate_assessment='NOT_EVALUABLE_MISSING_OFF5',
        global_false_alarm_probability=None, calibrated_sensitivity=None, new_observation_epochs=0,
        new_archive_requests=0, new_original_unique_archive_ids=0, new_original_technical_coverage_mhz_visits=0,
        authoritative_unique_archive_ids=486, authoritative_technical_MHz_visits=268.50128173828125,
        qualified_astronomical_sensitivity_MHz_visits=0, queue_advanced=False, historical_failures_preserved=True,
        background_science_jobs_running=False, remaining_full_halo_cached_carrier_q=[], excluded_boundary_q=[0,255],
        scope_correction='BV froze q33..253; its claim that all full-halo safe cores were covered was overbroad. Original BN explicitly admitted q254. BW prospectively closes that remaining core; BV history is unchanged.',
        power_contact_scope='First detector scoring of q254 in previously decoded and fully normalized five-scan data. No new observations or held-out powers.',
        interpretation='Correlated tracks and threshold rows are not independent tests/candidates. This is a partial five-scan screen, not a full-cadence null result or calibrated sensitivity bound.',
        next_action='Resume original OFF5 rows8..15 and row7 repeat only with normal permitted archive access and complete retained BB/BC/BE proof gates; then qualify full cadence. Next queued fresh targets remain HIP58684/65193 and HIP59280/65205.')
    with (BW / 'SUMMARY_BW.json').open('x') as f:
        json.dump(summary, f, indent=2, sort_keys=True, allow_nan=False); f.write('\n')
    print(json.dumps(summary))

if __name__ == '__main__':
    main()
