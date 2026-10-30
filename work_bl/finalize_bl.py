"""Summarize only the closed BL campaign; do not run any search or decode."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work_bl'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def write(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')

def main():
    closed = WORK / 'results/CAMPAIGN_COMPLETE_BL.json'
    result = read(closed)
    assert result['status'] == 'ALL_FOUR_BATCHES_SEARCHED_AND_AUDITED'
    assert not (WORK / 'results/CAMPAIGN_STOP_BL.json').exists()
    assert result['q_list'] == list(range(1,33)) and result['completed_batches'] == 4
    assert result['total_track_trials'] == 1732018176
    batches = result['batch_results']
    assert [b['batch'] for b in batches] == [1,2,3,4]
    assert [q for b in batches for q in b['q_list']] == result['q_list']
    retained_pins = dict(result['input_source_plan_sha256'])
    for batch in batches:
        for path, digest in read(batch['audit_result_path'])['input_and_artifact_sha256'].items():
            assert path not in retained_pins or retained_pins[path] == digest
            retained_pins[path] = digest
    for path, digest in retained_pins.items():
        assert sha(path) == digest, 'Closed audit/source artifact changed: ' + path
    prepared_path = ROOT / 'work_bk/next_data/PREPARED_ADJACENT_DATA_BK.json'
    prepared = read(prepared_path)
    expected = {f['scan_id']:[r['sha256'] for r in f['decoded_rows']]
                for f in prepared['files'] if f['native'] == 170}
    row_checks = []
    for batch in batches:
        assert batch['actual_search_exit_code'] == batch['actual_audit_exit_code'] == 0
        for key in ['search_actual','audit_actual','audit_result','complete_result','plan']:
            assert sha(batch[key+'_path']) == batch[key+'_sha256']
        for actual in [read(batch['search_actual_path']),read(batch['audit_actual_path'])]:
            assert actual['stdout_eof'] and actual['child_wait_completed']
            assert actual['stdout_fully_preserved'] and actual['capture_error'] is None
            assert sha(actual['log_path']) == actual['observed_stdout_sha256'] == actual['log_sha256']
        plan = read(batch['plan_path'])
        marker = Path(batch['complete_result_path']).parent / 'NORMALIZED_INPUTS_COMPLETE.json'
        norm = read(marker)
        for scope, scan in zip(plan['scans'], norm['scans'], strict=True):
            assert scan['full_native_row_sha256'] == expected[scope['label']]
        row_checks.append(dict(batch=batch['batch'], matched_decoded_row_hashes=96,
                               marker_sha256=sha(marker)))
    totals = {key:sum(b[key] for b in batches) for key in [
        'ON_catalog_rows','OFF_catalog_rows','passing_flags','total_track_trials',
        'forced_measurement_slots','supported_forced_measurements','unsupported_forced_slots',
        'fixed_scalar_sum_comparisons','shared_kernel_calibration_vector_replays',
        'search_wall_seconds','audit_wall_seconds','search_user_cpu_seconds',
        'search_system_cpu_seconds','audit_user_cpu_seconds','audit_system_cpu_seconds']}
    assert totals['passing_flags'] == 0
    assert totals['total_track_trials'] == result['total_track_trials']
    maxima = {str(width):{role:max(b['maximum_local_ESS_by_width'][str(width)][role]
               for b in batches) for role in ['ON','OFF']} for width in [1,3,9,33]}
    summary = dict(schema='SETI_BL_NATIVE170_CLOSED_RESULTS_V1', status='PASS_CLOSED_SEARCH_AND_BOUNDED_AUDIT',
        completed_utc=datetime.now(timezone.utc).isoformat(), prereg_github_commit=result['prereg_github_commit'],
        target='HIP98505 / HD189733', observation_date='2017-04-28', native_chunk_index=170,
        q_list=result['q_list'], carrier_channels=32*4096, scan_core_searches=192,
        technical_width_hz=32*4096*2.7939677238464355,
        frequency_center_limits_mhz=[2304.78515625+(33*4096-1)*(-2.7939677238464355)/1e6,
                                     2304.78515625+4096*(-2.7939677238464355)/1e6],
        campaign_wall_seconds=result['wall_seconds'], totals=totals, maximum_local_ESS_by_width=maxima,
        maximum_scalar_sum_error=max(b['maximum_scalar_sum_error'] for b in batches),
        maximum_replayed_calibration_error=max(b['maximum_replayed_calibration_error'] for b in batches),
        repeated_row_hash_checks=row_checks, unique_decoded_rows=96,
        all_four_searches_and_audits_actual_exit_zero=True,
        campaign_complete_sha256=sha(closed), prepared_adjacent_receipt_sha256=sha(prepared_path),
        new_archive_requests=0, new_observations=0, new_unique_archive_ID_credit=0, cost_DKK=0,
        BA_authoritative_archive_IDs_unchanged=486,
        BA_authoritative_technical_MHz_visits_unchanged=268.50128173828125,
        candidate_assessment='No qualified SETI candidate; local ESS and flags are descriptive, not calibrated sigma/SNR/FAP or astronomical sensitivity.',
        historical_outcomes_preserved=prepared['historical_outcomes_preserved'],
        next_action='Freeze a distinct native170 q33..40 continuation before scores; use same method if adopted. Native172 requires separate scope; preserve B06/native172/q81 failures.',
        background_science_jobs_running=False)
    write(WORK / 'results/REAL_SEARCH_SUMMARY_BL.json', summary)
    binary_paths = sorted(p for p in (WORK/'results').rglob('*') if p.suffix in ['.npy','.npz'])
    members = [dict(path=str(p.relative_to(WORK)), bytes=p.stat().st_size, sha256=sha(p)) for p in binary_paths]
    resume = dict(schema='SETI_BL_BINARY_RESULTS_RESUME_V1', prereg_github_commit=result['prereg_github_commit'],
        repository='andersenmartin-blip/setisearch', branch='m43-support-qualification',
        summary=summary, binary_members=members, original_raw_parts=prepared['parts'],
        raw_archive_sha256=prepared['archive_sha256'],
        note='Original absolute paths in pinned text evidence are historical. Restore new work in a distinct namespace; never rerun/overwrite closed BL. Detailed JSON/logs are published on GitHub.')
    delivery_dir = ROOT.parent / 'deliveries';delivery_dir.mkdir(exist_ok=True)
    archive = delivery_dir / 'SETI_BL_SEARCH_RESULTS_2026-10-30.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p, record in zip(binary_paths, members, strict=True):z.write(p, record['path'])
        z.writestr('RESUME_BL.json', json.dumps(resume, indent=2, sort_keys=True)+'\n')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for record in members:
            b=z.read(record['path']);assert len(b)==record['bytes'] and hashlib.sha256(b).hexdigest()==record['sha256']
        assert json.loads(z.read('RESUME_BL.json'))==resume
    for path, digest in retained_pins.items():
        assert sha(path) == digest, 'Closed artifact changed during packaging: ' + path
    delivery = dict(schema='SETI_BL_DELIVERY_V1', stage='BL', status=summary['status'],
        prereg_github_commit=result['prereg_github_commit'],
        archive_path=str(archive.resolve()), archive_bytes=archive.stat().st_size, archive_sha256=sha(archive),
        archive_members=len(members)+1, all_member_CRC_and_SHA256_verified=True,
        summary_path=str((WORK/'results/REAL_SEARCH_SUMMARY_BL.json').resolve()),
        summary_sha256=sha(WORK/'results/REAL_SEARCH_SUMMARY_BL.json'),
        next_action=summary['next_action'])
    write(WORK / 'DELIVERY_BL.json', delivery)
    print(json.dumps(delivery, indent=2))

if __name__ == '__main__':
    main()
