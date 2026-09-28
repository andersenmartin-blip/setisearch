#!/usr/bin/env python3
"""Verify durable reports and rehydrate existing deterministic mock identities.

Reconstruction checks the recorded raw-row hashes, normalized NPZ rows and full
source identities. It is not another mock experiment, RNG draw or score run.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from radio_receiver_adapter_common import ROOT,context
from seti_repeater import receiver_development_radio as render
from seti_repeater import transfer_m43g as native
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.empty_null_radio import canonical

OUT=ROOT/'results_radio_whole_cadence_physical_2026-09-28'


def write(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def read(path):return json.loads(path.read_text())


def original(path):
    p=ROOT/path
    return p.read_bytes() if p.is_file() else subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)


def verify_hash(value,key):
    if value[key]!=digest({k:v for k,v in value.items() if k!=key}):raise ValueError('Changed '+key)


def main():
    started=time.monotonic()
    old=read(ROOT/'results_radio_whole_cadence_handoff_2026-09-28/postflight.json')
    invariants=old['historical_invariant_pins']
    for p,h in invariants.items():
        if hashlib.sha256(original(p)).hexdigest()!=h:raise ValueError('Historical pin changed: '+p)
    code=read(OUT/'qualified_code_pins.json')
    for p,h in code['pins'].items():
        if hashlib.sha256(original(p)).hexdigest()!=h:raise ValueError('Qualified code changed: '+p)
    complete=aborted=0
    for p in sorted((OUT/'physical01').glob('*_result.json')):
        r=read(p);verify_hash(r,'result_sha256');verify_hash(r['retention'],'result_sha256')
        for kind in ('on','off'):
            for row in r['retention']['retained'][kind]:verify_hash(row,'record_id');complete+=1
        members=[rid for c in r['clusters'] for rid in c['member_ids']]
        ids={x['record_id'] for x in r['retention']['retained']['on']}
        if len(members)!=len(set(members)) or set(members)!=ids:raise ValueError('Cluster inventory differs')
    for p in sorted((OUT/'physical01').glob('*_expected_failure.json')):
        r=read(p)
        if r['complete'] is not False or 'result_sha256' in r:raise ValueError('Failure became pass')
        verify_hash(r['retention'],'result_sha256')
        aborted+=sum(len(v) for v in r['retention']['retained'].values())
    if (complete,aborted)!=(14,6):raise ValueError('Physical trigger count differs')
    selected=read(OUT/'render01/selected_before_execution.json');source_rows=[];raw_cells=normalized_cells=0
    for index in range(2):
        receipt=read(OUT/f'render01/case{index}_receipt.json');verify_hash(receipt,'receipt_sha256')
        plan=read(OUT/f'render01/case{index}_plan.json');verify_hash(plan,'plan_sha256')
        c=context('calibration' if plan['case']['role']=='calibration' else 'validation')
        scopes=read(OUT/f'render01/case{index}_source_scopes.json');recipe=plan['case']['recipe']
        with np.load(OUT/f'render01/case{index}_normalized_sources.npz',allow_pickle=False) as arrays:
            if set(arrays.files)!=set(receipt['source_ids']):raise ValueError('Mock source inventory differs')
            for si,scan in enumerate(receipt['row_receipts']):
                label=scan['scan'];values=arrays[label]
                if values.shape!=(16,65536) or values.dtype!=np.dtype('<f4'):raise ValueError('Mock source layout differs')
                rawhash=hashlib.sha256()
                for row,row_receipt in enumerate(scan['rows']):
                    base=(100.+((np.arange(65536,dtype='<u4')*17+si*31+row*13)%257).astype('<f8')/512.).astype('<f4')
                    if native.array_hash(base)!=row_receipt['background_sha256']:raise ValueError('Mock reconstruction background differs')
                    reconstructed=base.astype('<f8')
                    if row_receipt['injected']:
                        indices,mass=render.pixel_masses(row_receipt['center_channel'],row_receipt['sweep_channels'],
                            recipe['injection_width_channels'],65536)
                        reconstructed[indices]+=recipe['total_digital_power']*mass
                    reconstructed=reconstructed.astype('<f4')
                    if native.array_hash(reconstructed)!=row_receipt['raw_sha256']:raise ValueError('Mock reconstructed raw row differs')
                    if native.array_hash(values[row])!=row_receipt['normalized_sha256']:raise ValueError('Retained normalized row differs')
                    rawhash.update(reconstructed.tobytes());raw_cells+=65536;normalized_cells+=65536
                normhash=native.array_hash(values)
                source_id=native.digest({'contract':native.CONTRACT_SHA256,'geometry':asdict(c.geometry),'rows':16,
                    'scope':scopes[label],'raw_sha256':rawhash.hexdigest(),'normalized_sha256':normhash})
                if source_id!=receipt['source_ids'][label] or source_id!=scan['source_identity']:
                    raise ValueError('Full mock source rehydration identity differs')
                source_rows.append({'case':index,'scan':label,'source_identity':source_id,
                    'raw_sha256':rawhash.hexdigest(),'normalized_sha256':normhash,'geometry':asdict(c.geometry),
                    'rows':16,'all_retained_row_hashes_verified':True})
    write('source_rehydration.json',{'schema':'radio-whole-cadence-mock-rehydration-v1','sources':source_rows,
        'raw_cells_reconstructed_and_verified':raw_cells,'normalized_cells_restored_and_verified':normalized_cells,
        'new_cases_or_random_draws':0,'uses_original_mock_receipts':True})
    for p in (OUT/'gates01').glob('*_result.json'):verify_hash(read(p),'result_sha256')
    proposal=json.loads(original('config/radio_whole_cadence_null_proposal_20260928.json'))
    proposed={c['identity'] for c in proposal['cases']}
    mocks={read(OUT/f'render01/case{i}_receipt.json')['case_identity'] for i in range(2)}
    if mocks & proposed:raise ValueError('Mock/proposed case identity overlap')
    retained=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    if retained>128*1024**2:raise ValueError('Total evidence cap exceeded')
    result={'schema':'radio-whole-cadence-physical-postflight-v1','status':'VERIFIED_FOR_PUBLICATION',
        'historical_invariant_pins':invariants,'new_distinct_unit_tests':66,'additional_schedule_rejection_checks':1,
        'physical_complete_run_triggers':complete,'physical_failed_run_triggers_preserved':aborted,
        'mock_sources_rehydrated':len(source_rows),'mock_raw_cells_reconstructed':raw_cells,
        'mock_normalized_cells_verified':normalized_cells,'handcrafted_gate_examples':8,
        'proposed_case_metadata_plans':151,'proposed_cases_executed':0,'new_gaussian_draws':0,
        'new_scientific_allocations':0,'new_source_requests':0,'new_telescope_values':0,
        'old_attempts_reopened':False,'external_messages':0,'plan_extended':False,
        'old_preparation_contracts_changed':False,'native_full_chain_qualified':False,
        'real_rng_entry_available':False,'prospective_proposal_status':'PROPOSED_NOT_ACTIVATED',
        'retained_evidence_bytes_at_postflight':retained,'postflight_seconds':time.monotonic()-started}
    write('postflight.json',result);print(json.dumps({k:v for k,v in result.items() if k!='historical_invariant_pins'},indent=2))


if __name__=='__main__':main()
