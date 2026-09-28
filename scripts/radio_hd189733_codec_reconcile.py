#!/usr/bin/env python3
"""Reconcile the existing failed-oracle fixture without generating a new one."""
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback

import h5py
import hdf5plugin
import numpy as np

import radio_hd189733_codec_profile as original
from seti_repeater import hdf5_filter_contract_radio as filters
from seti_repeater import search_v0p6 as core
from seti_repeater import source_v0p6 as normalization
from seti_repeater import transfer_m43g as native

BASE=original.ROOT/'results_radio_hd189733_codec_2026-09-28'
OUT=BASE/'reconcile01'


def reference_normalization(selection):
    selection=np.asarray(selection)
    if selection.dtype!=np.dtype('<f4') or selection.ndim!=1 or not len(selection) or not np.isfinite(selection).all():
        raise ValueError('Finite one-dimensional float32 oracle selection required')
    ascending=selection[::-1]
    expected=np.empty_like(ascending)
    for start in range(0,len(ascending),4096):
        block=np.ascontiguousarray(ascending[start:start+4096].reshape(1,-1))
        expected[start:start+4096]=normalization.normalize_float32_blocks_v0p6(block)[0]
    return expected


def main():
    started=time.monotonic();OUT.mkdir(exist_ok=False)
    error=json.loads((original.OUT/'error.json').read_text())
    if 'C-order <f4 matrix' not in error['error']:raise ValueError('Unexpected original failure')
    pins=json.loads((original.OUT/'input_pins.json').read_text())
    for path,checksum in pins.items():
        if original.file_hash(original.ROOT/path)!=checksum:raise ValueError('Original fixture input changed: '+path)
    paths=[original.OUT/'current_encoder_fixture.h5',original.OUT/'legacy_declaration_fixture.h5']
    retained_pins={p.name:{'bytes':p.stat().st_size,'sha256':original.file_hash(p)} for p in paths}
    original.write(OUT/'retained_input_pins.json',retained_pins)
    raw=json.loads((original.OUT/'compressed_chunk_receipts.json').read_text())
    profile=json.loads((original.OUT/'source_profile.json').read_text())
    geometry=json.loads((original.ROOT/original.GEOMETRY).read_text())
    windows=geometry['windows'];full_cells=extracted_cells=normalized_cells=0
    decoded=[];normalized=[]
    def budget():
        if time.monotonic()-started+error['active_seconds']>600:raise RuntimeError('Combined active-time cap')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:raise RuntimeError('Reconciliation RSS cap')
        if sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())>128*1024**2:raise RuntimeError('Combined retained-byte cap')
    try:
        with h5py.File(paths[0],'r',rdcc_nbytes=8*1024**2) as modern, h5py.File(paths[1],'r',rdcc_nbytes=8*1024**2) as legacy:
            ds=legacy['data'];filters.check_dataset(ds,profile['filter_pipeline'])
            encoder_profile=filters.signature([modern['data'].id.get_create_plist().get_filter(0)])
            if ds.id.get_num_chunks()!=48 or modern['data'].id.get_num_chunks()!=48:raise ValueError('Retained chunk inventory changed')
            for item in raw:
                for dataset in (modern['data'],ds):
                    mask,payload=dataset.id.read_direct_chunk(tuple(item['offset']))
                    if mask!=0 or hashlib.sha256(payload).hexdigest()!=item['compressed_sha256'] or len(payload)!=item['compressed_bytes']:
                        raise ValueError('Retained compressed bytes differ')
            for w in windows:
                ci=w['archive_chunk_index'];lo,hi=w['archive_interval'];expected_rows=[];measured_rows=[]
                for row in range(16):
                    expected=original.pattern(ci,row);measured=ds[row,0,ci*original.CHUNK:(ci+1)*original.CHUNK]
                    if not np.array_equal(expected.view('<u4'),measured.view('<u4')):raise ValueError('Complete decoded chunk differs')
                    full_cells+=original.CHUNK
                    selection=ds[row,0,lo:hi];wanted=expected[lo-ci*original.CHUNK:hi-ci*original.CHUNK]
                    if not np.array_equal(selection.view('<u4'),wanted.view('<u4')):raise ValueError('Archive selection differs')
                    expected_rows.append(wanted.copy());measured_rows.append(selection)
                    extracted_cells+=len(selection)
                    receipt={'row':row,'role':w['role'],'decoded_sha256':native.array_hash(measured),
                        'selected_native_sha256':native.array_hash(selection),'decoded_cells':original.CHUNK,
                        'selected_cells':len(selection),'all_bits_equal':True}
                    original.write(OUT/f'{w["role"]}_row{row:02d}_decode.json',receipt);decoded.append(receipt);budget()
                source=json.loads((original.ROOT/original.SOURCE).read_text())
                geom=core.NativeFrequencyGeometry(w['native_frequency_low_hz'],
                    abs(source['scans'][0]['expected_header']['foff_mhz'])*1e6,65536)
                adapted=native.normalize_synthetic_rows(lambda row:measured_rows[row],geom,16,
                    input_orientation='descending',scope={'kind':'synthetic',
                        'input_domain':'retained-source-shaped-codec-fixture','role':w['role'],
                        'source_preparation_sha256':original.INPUTS[original.SOURCE],
                        'telescope_provenance':False})
                for row,selection in enumerate(expected_rows):
                    wanted=reference_normalization(selection)
                    if not np.array_equal(wanted.view('<u4'),adapted.values[row].view('<u4')):raise ValueError('Normalized row differs')
                    receipt={'row':row,'role':w['role'],'normalized_sha256':native.array_hash(adapted.values[row]),
                        'cells':len(wanted),'all_bits_equal':True}
                    original.write(OUT/f'{w["role"]}_row{row:02d}_normalization.json',receipt);normalized.append(receipt)
                    normalized_cells+=len(wanted);budget()
                print('reconciled retained role',w['role'],flush=True)
        for p in paths:
            if original.file_hash(p)!=retained_pins[p.name]['sha256']:raise ValueError('Retained HDF5 file changed')
        result={'schema':'radio-hd189733-retained-codec-reconciliation-v1',
            'status':'ORIGINAL_ORACLE_FAILURE_RETAINED_CORRECTED_RECONCILIATION_PASS',
            'original_fixture_execution_status':'FAILED_ORACLE_C_ORDER',
            'new_hdf5_fixtures_generated':0,'new_random_or_scientific_controls':0,
            'codec_filter_pipeline':profile['filter_pipeline'],'local_encoder_filter_pipeline':encoder_profile,
            'compressed_chunk_payload_checks':96,'unique_populated_chunks':48,
            'decoded_cells_bit_exact':full_cells,'extracted_native_cells_bit_exact':extracted_cells,
            'normalized_cells_bit_exact':normalized_cells,'decode_row_receipts':len(decoded),
            'normalization_row_receipts':len(normalized),'input_hdf5_pins':retained_pins,
            'reconciliation_seconds':time.monotonic()-started,
            'combined_execution_seconds':time.monotonic()-started+error['active_seconds'],
            'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'same_existing_normalizer_used_on_independently_selected_expected_rows':True,
            'arithmetic_texture_is_not_a_telescope_noise_model':True,
            'archive_encoder_or_archive_payload_verified':False,
            'source_native_receiver_handoff_qualified':False,'new_source_requests':0,
            'scientific_attempt_budget_charged':False,'telescope_spectra_opened':False,
            'telescope_admission_authorized':False,
            'reconcile_script_sha256':original.file_hash(Path(__file__)),
            'reconcile_scope_sha256':original.file_hash(original.ROOT/'RADIO_HD189733_CODEC_RECONCILE_2026-09-28_SCOPE.md')}
        budget();original.write(OUT/'result.json',result);print(json.dumps(result,indent=2),flush=True)
    except BaseException as failure:
        original.write(OUT/'error.json',{'error':repr(failure),'traceback':traceback.format_exc(),
            'decoded_cells_checked':full_cells,'normalized_cells_checked':normalized_cells,
            'new_fixture_generated':False})
        raise


if __name__=='__main__':main()
