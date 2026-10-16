#!/usr/bin/env python3
"""Once-only descriptive full search on a fixed, previously exposed 2017 band.

This is a new documented execution, not new observing data or admission of a
closed scientific study. Both complete processes are prospectively reserved.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
WORKSPACE = SOURCE.parent
IDENTITY = 'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00'
MODE = 'DESCRIPTIVE_POSTSELECTED_2017'
SCHEMA = 'SETI_FIXED_RETAINED_BAND_COMPLETE_DESCRIPTIVE_SCOPE_V1'
MIB = 1024**2
PAYLOAD_CAP = 768*MIB
PRIMARY_CAP = 800*MIB
QA_CAP = 64*MIB
LOG_CAP = MIB
METADATA_CAP = MIB
OUTPUT_CAP = 2*1024**3
TOTAL_CPU = 1300
GUARD_SHA = 'd02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492'
ARCHIVE_SHA = '52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'
PIN_PATHS = (
    'analysis/real_fullscan_20261016/run.py',
    'analysis/real_fullscan_20261016/reader.py',
    'analysis/real_fullscan_20261016/producer.py',
    'analysis/real_fullscan_20261016/verifier.py',
    'analysis/real_fullscan_20261016/SOURCE_SELECTION.json',
    'tools/science_payload_20261016/payload.py',
    'tools/bounded_payload_20261015/payload_store.py',
    'tools/fullcase_payload_20261015/array_adapter.py',
    'tools/whole_child_guard_20261015/guard.py',
    'analysis/sixscan_burst_20261015/worker.py',
    'analysis/sixscan_burst_20261015/detector.py',
    'analysis/sixscan_burst_20261015/qa.py',
    'analysis/sixscan_burst_20261015/contract.json',
)


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(MIB),b''):h.update(block)
    return h.hexdigest()


def save(path, value):
    data=(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    require(len(data)<=METADATA_CAP//2,'Parent metadata file cap exceeded')
    with Path(path).open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    sync_directory(Path(path).parent)


def sync_directory(path):
    fd=os.open(Path(path),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def size(path):
    path=Path(path)
    if not path.exists():return 0
    require(not path.is_symlink(),'Symlink output rejected')
    if path.is_file():return path.stat().st_size
    total=0
    for p in path.rglob('*'):
        require(not p.is_symlink(),'Symlink output rejected')
        if p.is_file():total+=p.stat().st_size
    return total


def source_pins():
    return [dict(path=p,bytes=(SOURCE/p).stat().st_size,sha256=sha(SOURCE/p)) for p in PIN_PATHS]


def check_acceptance(pin):
    path=Path(pin['path'])
    require(path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],
            'Pinned complete-search engineering acceptance differs')
    require(json.loads(path.read_text())['status']=='PASS_COMPLETE_SEARCH_ENGINEERING_ONLY',
            'Complete-search engineering and independent QA must pass first')


def once_path():
    return WORKSPACE/'work'/'REAL_DESCRIPTIVE_CLAIMS_20261016'/(IDENTITY+'.json')


def freeze(scope_path, output_root, source_archive, engineering_result):
    scope_path=Path(scope_path).resolve();output_root=Path(output_root).resolve()
    archive=Path(source_archive).resolve();acceptance=Path(engineering_result).resolve()
    require(scope_path.parent.is_dir() and output_root.parent.is_dir() and not output_root.exists(),
            'Existing parent and fresh descriptive output directory required')
    require(not once_path().exists(),'Descriptive identity already attempted; no retry')
    require(archive.stat().st_size==48468705 and sha(archive)==ARCHIVE_SHA,
            'Original retained source archive size/hash required; no substitution')
    pin=dict(path=str(acceptance),bytes=acceptance.stat().st_size,sha256=sha(acceptance))
    check_acceptance(pin)
    require(sha(SOURCE/'tools/whole_child_guard_20261015/guard.py')==GUARD_SHA,'Guard bytes differ')
    selection=json.loads((HERE/'SOURCE_SELECTION.json').read_text())
    band=selection['selected_band']
    scope=dict(schema=SCHEMA,identity=IDENTITY,mode=MODE,output_root=str(output_root),
        source_pins=source_pins(),source_archive=dict(path=str(archive),bytes=48468705,sha256=ARCHIVE_SHA),
        source_metadata=dict(member='SETI_NATIVE_SPOR_2026-10-14/seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json',
            bytes=629588,sha256='31efe1e5eeba63d10fbc04ea60bd29eb3086f142b6111a185f821a40a0558522'),
        band=band,integration_acceptance=pin,
        scientific_bank_admission=False,rank_status='NOT_APPLIED_NO_CALIBRATION',
        qualified_SETI_detection=False,original_A_B='FAIL_CLOSED',
        selection='First canonical retained band sorted by native_chunk_index then core_q from original metadata; chosen before this new execution, independent of new outputs.',
        data_status='Previously exposed and postselected historical visit 2017-04-28; old unknown executions may have searched the same hypotheses.',
        search=dict(core_carriers=4096,OFF_reference_halo='unchanged metadata-derived original rule',
            widths=[1,3,9,33],window_starts=[0,2,4,6,8,10,12],window_rows=4,
            maximum_drift_Hz_s=4,normalization_channels=4096,running_median_channels=501,
            retained_k_per_ON_carrier=5,ON_descriptive_score_cut=10,OFF_descriptive_score_cut=8,
            ON_output='All retained per-carrier top5 hypotheses at or above10; not every scored ON hypothesis above10.',
            OFF_output='Every scored OFF native4 identity at or above8, under unchanged complete inventory cap2,000,000.',
            rank_status='NOT_APPLIED_NO_CALIBRATION',new_fitting_or_retuning=False),
        resources=dict(primary_CPU_s=600,qa_CPU_s=600,metadata_CPU_s=100,
            reserved_total_CPU_s=TOTAL_CPU,child_wall_s=1800,child_address_space_bytes=1024**3,
            payload_cap_bytes=PAYLOAD_CAP,primary_phase_bytes=PRIMARY_CAP,qa_phase_bytes=QA_CAP,
            per_phase_log_receipt_bytes=LOG_CAP,metadata_bytes=METADATA_CAP,total_output_cap_bytes=OUTPUT_CAP),
        interpretation=dict(scientific_bank_admission=False,qualified_SETI_detection=False,
            calibrated_SNR_or_FAP=False,independent_reobservation=False,
            OFF_dispositions_are_algorithmic_diagnostics_only=True,physical_origin_inferred=False,
            unknown_and_failed_banks_unchanged=True,old_case_ids_reused=False,
            original_A_B='FAIL_CLOSED',protected_2016_closed=True,unavailable_2019_closed=True),
        new_telescope_requests=0,new_telescope_bytes=0,cost_DKK=0,checkpoint='2026-10-20',
        reservations_refunded=False,
        logs='Python log writers are bounded; native stdout/stderr excess is checked after reap, not a universal hard physical writer cap.')
    save(scope_path,scope)
    return dict(status='FROZEN_DESCRIPTIVE_ONLY',scope_sha256=sha(scope_path),identity=IDENTITY)


def run(scope_path):
    scope_path=Path(scope_path).resolve();scope=json.loads(scope_path.read_text())
    require(scope['schema']==SCHEMA and scope['identity']==IDENTITY and scope['mode']==MODE,
            'Fresh fixed descriptive scope required')
    require(scope['source_pins']==source_pins(),'Frozen source pins changed')
    check_acceptance(scope['integration_acceptance'])
    require(scope['source_archive']['sha256']==ARCHIVE_SHA and
            sha(scope['source_archive']['path'])==ARCHIVE_SHA,'Original archive changed')
    root=Path(scope['output_root']);require(not root.exists() and root.parent.is_dir(),'Fresh output root required')
    reserve=PRIMARY_CAP+QA_CAP+2*LOG_CAP+METADATA_CAP
    require(reserve<=OUTPUT_CAP and reserve<=shutil.disk_usage(root.parent).free,
            'All future phase output reservations must fit before launch')
    require(600+600+100==TOTAL_CPU,'Complete CPU reservation must fit')
    claim=once_path();claim.parent.mkdir(parents=True,exist_ok=True)
    sync_directory(claim.parent.parent)
    save(claim,dict(identity=IDENTITY,mode=MODE,status='CLAIMED_BEFORE_NUMERICAL_CHILD_IMPORTS_OR_RAW_ARRAY_READ',
        scope_sha256=sha(scope_path),output_root=str(root),no_retry=True,reserved_CPU_s=TOTAL_CPU,
        reserved_output_bytes=reserve,reservations_refunded=False,scientific_bank_admission=False))
    root.mkdir();sync_directory(root.parent);save(root/'FROZEN_SCOPE.json',scope)
    guard_path=SOURCE/'tools/whole_child_guard_20261015/guard.py'
    require(sha(guard_path)==GUARD_SHA,'Pinned guard changed')
    spec=importlib.util.spec_from_file_location('descriptive_real_guard',guard_path)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    folder=root/'observation';qa_report=root/'QA_REPORT.json'
    state=dict(identity=IDENTITY,status='RUNNING_DESCRIPTIVE_ONLY',scope_sha256=sha(scope_path),phases=[],
        resource_reservation=dict(CPU_s=TOTAL_CPU,output_bytes=reserve),reservations_refunded=False,
        rank_status='NOT_APPLIED_NO_CALIBRATION',scientific_bank_admission=False,qualified_SETI_detection=False,
        original_A_B='FAIL_CLOSED',new_observation=False)
    phases=(('primary',[sys.executable,str(HERE/'producer.py'),'--folder',str(folder),'--scope',str(scope_path),
             '--scope-sha256',sha(scope_path),'--payload-cap',str(PAYLOAD_CAP)],folder,PRIMARY_CAP,
             folder/'PRODUCER.json','PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY'),
            ('qa',[sys.executable,str(HERE/'verifier.py'),'--folder',str(folder),'--report',str(qa_report)],
             qa_report,QA_CAP,qa_report,'PASS_DESCRIPTIVE_REAL_FULLSCAN_QA_ONLY'))
    for phase,command,output,bound,report,expected_status in phases:
        attempt=root/('process_'+phase);receipt=None
        try:
            require(scope['source_pins']==source_pins(),'Frozen sources changed before phase')
            require(size(root)+bound+LOG_CAP+METADATA_CAP<=OUTPUT_CAP,'Reserved output headroom unavailable')
            require(shutil.disk_usage(root).free>=bound+LOG_CAP+METADATA_CAP,
                    'Live filesystem headroom no longer covers the next reserved phase')
            save(root/('CLAIM_'+phase+'.json'),dict(phase=phase,identity=IDENTITY,
                scope_sha256=sha(scope_path),CPU_reserved_s=600,output_reserved_bytes=bound+LOG_CAP,no_retry=True))
            receipt=guard.run_once(command,attempt,guard.policy(600,1800,1024**3))
            require(receipt.get('resource_acceptance') is True,'Whole-child resource/process closure failed')
            report_data=json.loads(report.read_text())
            require(report_data['status']==expected_status and report_data.get('scientific_bank_admission') is False,
                    'Complete descriptive phase report required')
            output_bytes,log_bytes=size(output),size(attempt)
            require(output_bytes<=bound and log_bytes<=LOG_CAP,'Reserved phase output or log cap exceeded')
            event=dict(phase=phase,status='ACCEPTED_DESCRIPTIVE_PHASE_ONLY',receipt=receipt,
                output_bytes=output_bytes,log_receipt_bytes=log_bytes,report_sha256=sha(report),reservations_refunded=False)
            save(root/('PHASE_'+phase+'.json'),event);state['phases'].append(event)
        except BaseException as error:
            event=dict(phase=phase,status='FAILED_RETAINED_NO_RETRY',receipt=receipt,
                output_bytes=size(output),log_receipt_bytes=size(attempt),
                error=dict(type=type(error).__name__,message=str(error)[:1024]),reservations_refunded=False)
            save(root/('FAILURE_'+phase+'.json'),event);state['phases'].append(event)
            state['status']='STOPPED_RETAINED_NO_RETRY';break
    if state['status']=='RUNNING_DESCRIPTIVE_ONLY':
        try:
            require(scope['source_pins']==source_pins(),'Sources changed during run')
            require(len(state['phases'])==2 and all(p['status']=='ACCEPTED_DESCRIPTIVE_PHASE_ONLY' for p in state['phases']),
                    'Both complete phases must pass')
            state['status']='COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED'
        except BaseException as error:
            state['status']='STOPPED_RETAINED_NO_RETRY';state['finalization_error']=str(error)[:1024]
    measurements=[p['receipt'].get('whole_child_CPU_s') if p['receipt'] else None for p in state['phases']]
    known=[v for v in measurements if type(v) in (int,float) and math.isfinite(v) and v>=0]
    state['known_whole_children_CPU_s']=math.fsum(known)
    state['unknown_CPU_measurement_count']=len(measurements)-len(known)
    state['whole_children_CPU_s']=math.fsum(known) if len(known)==len(measurements) else None
    state['actual_output_bytes_before_final_receipt']=size(root)
    if size(root)+METADATA_CAP>OUTPUT_CAP:state['status']='STOPPED_RETAINED_NO_RETRY'
    save(root/'RESULT.json',state)
    return dict(status=state['status'],identity=IDENTITY,whole_children_CPU_s=state['whole_children_CPU_s'],
        qualified_SETI_detection=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('freeze');p.add_argument('--scope',required=True,type=Path);p.add_argument('--output-root',required=True,type=Path)
    p.add_argument('--source-archive',required=True,type=Path);p.add_argument('--engineering-result',required=True,type=Path)
    p=sub.add_parser('run');p.add_argument('--scope',required=True,type=Path)
    a=ap.parse_args()
    r=freeze(a.scope,a.output_root,a.source_archive,a.engineering_result) if a.command=='freeze' else run(a.scope)
    print(json.dumps(r,sort_keys=True),flush=True)
    return 0 if r['status'] in ('FROZEN_DESCRIPTIVE_ONLY','COMPLETE_DESCRIPTIVE_REAL_FULLSCAN_QA_VERIFIED') else 1


if __name__=='__main__':raise SystemExit(main())
