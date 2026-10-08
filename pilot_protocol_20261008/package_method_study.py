#!/usr/bin/env python3
"""Inert until explicit closed-coordinator admission; preserve METHODS64 original bytes.

No scientific modules, numeric array APIs, RNG, search, codec or network.
Source files are hashed/copied verbatim after closure. Missing attempts and
missing normal-completion artifacts are recorded without reconstruction.
"""
import argparse
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import resource
import signal
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/radio_pilot_method_study_20261008'
DEST = ROOT / 'pilot_protocol_20261008/method_study_archives'
CLAIMS = ROOT / 'pilot_protocol_20261008/method_study_claims'
PARENT = ROOT / 'pilot_method_study_20261008'
CASE_COUNT = 64


def write(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def receipt(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1': hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()}


def archive(path, sources):
    members = []
    with path.open('xb') as target:
        with gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0, compresslevel=9) as gz:
            with tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as tf:
                for source in sorted(set(sources)):
                    if source.is_symlink() or not source.is_file():
                        raise ValueError(f'Ordinary original files required: {source}')
                    before = source.stat()
                    raw = source.read_bytes()
                    after = source.stat()
                    if (before.st_size,before.st_mtime_ns) != (after.st_size,after.st_mtime_ns):
                        raise ValueError(f'Original changed during preservation: {source}')
                    name = source.relative_to(ROOT).as_posix()
                    info = tarfile.TarInfo(name)
                    info.size,info.mode,info.uid,info.gid = len(raw),0o644,0,0
                    info.uname = info.gname = ''
                    info.mtime = 0
                    tf.addfile(info,io.BytesIO(raw))
                    members.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    output = receipt(path)
    output.update(member_count=len(members), original_member_bytes=sum(x['bytes'] for x in members),members=members)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--coordinator-closed',action='store_true')
    parser.add_argument('--independent-review-closed',action='store_true')
    parser.add_argument('--coordinator-exit-code',type=int,required=True)
    args = parser.parse_args()
    if not args.coordinator_closed or not args.independent_review_closed:
        raise ValueError('Parent-confirmed coordinator/process and independent-review closure are required; preparation grants no invocation')
    start,cpu = time.monotonic(),time.process_time()
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # This check only reads closure metadata, and only after explicit parent
    # admission. It does not open arrays, source values or scientific modules.
    closure_names = ['outcomes.json','summary.json','resource_receipt.json',
                     'rolling_cpu_ledger.json','full_panel_plan.json']
    for name in closure_names:
        if not (BASE/name).is_file():
            raise ValueError(f'Closed-panel evidence missing: {name}')
    ledger = json.loads((BASE/'rolling_cpu_ledger.json').read_text())
    marker = BASE/'COMMITTED_PANEL.json'
    if args.coordinator_exit_code == 0:
        if not marker.is_file():
            raise ValueError('Exit0 requires original committed-panel close marker')
    elif ledger.get('status') != 'CLOSED_NO_RETRY':
        raise ValueError('Failure/incomplete closure requires original CLOSED_NO_RETRY ledger')
    extra = [PARENT/name for name in [
        'method_cases.json','METHOD_STUDY_SCOPE.md','METHOD_STUDY_PROTOCOL.json',
        'METHOD_ADMISSION_AND_OUTPUTS.md','run_method_study.py','run_method_study_panel.py',
        'close_b_and_admit_ledger.py','post_b_ledger.json','method_study_admission.json',
        'method_freeze_publication_receipt.json','method_freeze_files.json']]
    extra += [ROOT/'pilot_protocol_20261008/review/COMPLETE_METHOD_STUDY_OUTPUT_REVIEW.md',
              ROOT/'pilot_protocol_20261008/review/COMPLETE_METHOD_STUDY_OUTPUT_REVIEW.json',
              ROOT/'pilot_protocol_20261008/review/METHOD_AUDIT_RESOURCE_RECEIPT.json',
              ROOT/'pilot_protocol_20261008/review/METHOD_AUDIT_STDOUT.log']
    for path in extra:
        if not path.is_file():
            raise ValueError(f'Parent admission/freeze/scope evidence missing: {path}')
    if not (CLAIMS/'controller_claim.json').is_file():
        raise ValueError('Original controller claim required for closed panel')
    # Separate archival bounds, within the existing preparation reserve.
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    def deadline(signum,frame):
        raise TimeoutError('Archival-only180second wall bound reached')
    signal.signal(signal.SIGALRM,deadline)
    signal.alarm(180)
    DEST.mkdir()  # Refuse overwrite/replay; retain originals in place.
    archives = []
    expected = {'admission.json','truth.json','synthetic_array_hashes.json',
                'resource_receipt.json','outcome.json','outcomes.json',
                'artifact_manifest.json','scan_map_metadata.json',
                *[f'scan_{j:02d}_full_map.npz' for j in range(6)]}
    for i in range(CASE_COUNT):
        directory = BASE/f'case_{i:03d}'
        files = sorted(f for f in directory.rglob('*') if f.is_file()) if directory.is_dir() else []
        record = archive(DEST/f'case_{i:03d}.tar.gz',files)
        record.update(index=i,case_directory_present=directory.is_dir(),
                      original_case_file_count=len(files),
                      missing_normal_completion_members=sorted(expected-{f.name for f in files}),
                      empty_archive_is_missing_original_attempt_evidence=not files,
                      parent_attempt_receipts_present={name:(BASE/f'{name}_{i:03d}{suffix}').is_file()
                        for name,suffix in [('reservation','.json'),('closure','.json'),
                                             ('admission','.json'),('command','.json'),('case','.log')]})
        write(DEST/f'case_{i:03d}_manifest.json',record)
        archives.append(record)
        if (i+1)%20 == 0:
            print(f'Preserved originals for {i+1}/{CASE_COUNT} planned cases',flush=True)
    case_directories = {f'case_{i:03d}' for i in range(CASE_COUNT)}
    coordinator = [f for f in BASE.rglob('*') if f.is_file() and f.relative_to(BASE).parts[0] not in case_directories]
    coordinator += [f for f in CLAIMS.rglob('*') if f.is_file()] + extra
    coordinator_record = archive(DEST/'coordinator_evidence.tar.gz',coordinator)
    write(DEST/'coordinator_evidence_manifest.json',coordinator_record)
    manifest = {'schema':'setisearch-methods64-original-deterministic-archives-v1',
                'panel':'METHODS64','planned_case_count':CASE_COUNT,
                'case_directories_found':sum(x['case_directory_present'] for x in archives),
                'case_file_sets_found':sum(bool(x['original_case_file_count']) for x in archives),
                'indices_without_original_case_files':[x['index'] for x in archives if not x['original_case_file_count']],
                'canonical_claim_file_count':sum(f.is_file() for f in CLAIMS.rglob('*')),
                'parent_confirmed_coordinator_closed':True,'parent_confirmed_independent_review_closed':True,'coordinator_exit_code':args.coordinator_exit_code,
                'original_committed_panel_marker_present':marker.is_file(),
                'closed_rolling_ledger_status':ledger.get('status'),
                'closure_evidence':[receipt(BASE/name) for name in closure_names],
                'parent_admission_freeze_scope':[receipt(f) for f in extra],
                'synthetic_control_bytes_only':True,'archive_diagnostics_do_not_assert_scientific_completeness':True,'real_pilot_admission_granted':False,'generation_search_or_numeric_decode_performed':False,
                'originals_preserved':True,'failed_missing_originals_preserved_without_manufacturing':True,
                'empty_planned_case_archives_have_no_fabricated_members':True,
                'deterministic_tar_and_gzip':True,'gzip_mtime':0,'tar_mtime':0,'tar_uid_gid':[0,0],'tar_mode':'0644',
                'archives':archives,'coordinator_evidence':coordinator_record,
                'total_archive_bytes':sum(x['bytes'] for x in archives)+coordinator_record['bytes'],
                'total_archived_original_member_bytes':sum(x['original_member_bytes'] for x in archives)+coordinator_record['original_member_bytes']}
    write(ROOT/'pilot_protocol_20261008/method_study_archives_manifest.json',manifest)
    upload_index = [{k:x[k] for k in ['path','bytes','sha256','git_blob_sha1']}
                    for x in archives+[coordinator_record]]
    write(ROOT/'pilot_protocol_20261008/method_study_upload_index.json',upload_index)
    measurement = {'phase':'deterministic_METHODS64_archival_packaging',
                   'started_utc':started_utc,'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'wall_s':time.monotonic()-start,'cpu_s':time.process_time()-cpu,
                   'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                   'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'archive_count':CASE_COUNT+1,'total_archive_bytes':manifest['total_archive_bytes'],
                   'cpu_limit_s':120,'wall_limit_s':180,'scientific_work_performed':False,
                   'budget_binding':{'current_root_preparation_planning_reserve_cpu_s':1200,
                     'actual_archival_cpu_charged_within_reserve':True,
                     'reservation_is_not_measured_consumption':True},
                   'scope':'Internal interval before final receipt write. Parent wrapper must replace primary metrics with whole child-process wall/CPU/RSS including imports. MCP upload CPU remains unmeasured, not zero.'}
    write(ROOT/'pilot_protocol_20261008/method_study_packaging_resource_receipt.json',measurement)
    signal.alarm(0)
    print(json.dumps(measurement),flush=True)


if __name__ == '__main__':
    main()
