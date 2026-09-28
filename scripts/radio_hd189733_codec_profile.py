#!/usr/bin/env python3
"""One source-shaped local codec fixture; never opens a telescope product."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import resource
import sys
import time
import traceback

import h5py
import hdf5plugin
import numpy as np

from seti_repeater import hdf5_filter_contract_radio as filters
from seti_repeater import search_v0p6 as core
from seti_repeater import source_radio
from seti_repeater import transfer_m43g as native
from seti_repeater import source_v0p6 as normalization

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_hd189733_codec_2026-09-28/fixture01'
SOURCE='config/radio_hd189733_source_preparation_20260927.json'
GEOMETRY='results_radio_hd189733_geometry_2026-09-27/window_geometry.json'
INPUTS={SOURCE:'98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1',
        GEOMETRY:'92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6'}
CHUNK=1048576


def file_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for part in iter(lambda:handle.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def write(path,value):
    with path.open('x') as handle:
        json.dump(value,handle,indent=2,sort_keys=True,allow_nan=False);handle.write('\n')


def pattern(chunk_index,row):
    """Fixed binary-exact arithmetic texture; no PRNG or signal recipe."""
    i=np.arange(CHUNK,dtype='<u4')
    return (np.float32(100.) + ((i*17+chunk_index*31+row*13)%4093).astype('<f4')*np.float32(1/4096)
            + ((i//4096)%17).astype('<f4')*np.float32(1/32)).astype('<f4')


def main():
    started=time.monotonic();OUT.mkdir(parents=True,exist_ok=False)
    def budget():
        if time.monotonic()-started>600:raise RuntimeError('Fixture active time cap')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:raise RuntimeError('Fixture RSS cap')
        if sum(p.stat().st_size for p in OUT.iterdir() if p.is_file())>128*1024**2:raise RuntimeError('Fixture retained cap')
    pins=dict(INPUTS)
    for path in ['scripts/radio_hd189733_codec_profile.py','RADIO_HD189733_CODEC_2026-09-28_SCOPE.md',
                 'src/seti_repeater/hdf5_filter_contract_radio.py','src/seti_repeater/source_radio.py',
                 'src/seti_repeater/transfer_m43g.py','src/seti_repeater/source_v0p6.py']:
        pins[path]=file_hash(ROOT/path)
    write(OUT/'input_pins.json',pins)
    completed=[]
    try:
        for path,checksum in pins.items():
            if file_hash(ROOT/path)!=checksum:raise ValueError('Input pin mismatch: '+path)
        source=json.loads((ROOT/SOURCE).read_text());geometry=json.loads((ROOT/GEOMETRY).read_text())
        profile=[[32008,1,[0,3,4,0,2]]]
        if any(filters.declared(s,required=True)!=profile for s in source['scans']):
            raise ValueError('Selected source codec declarations differ')
        shape=(16,1,264503296);chunks=(1,1,CHUNK)
        if any(tuple(s['expected_chunks'])!=chunks or tuple(s['expected_header']['dataset_shape'])!=shape
               or s['expected_header']['dataset_dtype']!='float32' for s in source['scans']):
            raise ValueError('Source chunk/type geometry differs')
        windows=geometry['windows']
        if [w['role'] for w in windows]!=['calibration','validation','pilot']:raise ValueError('Window order changed')
        for w in windows:
            lo,hi=w['archive_interval'];ci=w['archive_chunk_index']
            if hi-lo!=65536 or not ci*CHUNK<=lo<hi<=(ci+1)*CHUNK:raise ValueError('Window/chunk mismatch')
        runtime={**source_radio.runtime(),'python':platform.python_version(),'machine':platform.machine(),
                 'byteorder':sys.byteorder,'python_binary_sha256':file_hash(Path(sys.executable))}
        if {k:runtime[k] for k in ('numpy','h5py','hdf5','hdf5plugin')}!={
                'numpy':'2.3.5','h5py':'3.16.0','hdf5':'2.0.0','hdf5plugin':'7.1.0'}:
            raise ValueError('Local codec runtime differs from published baseline')
        h5root=Path(h5py.__file__).resolve().parent
        binaries=list(h5root.glob('*.so'))+list((h5root.parent/'h5py.libs').glob('*.so*'))
        binaries+=list(Path(hdf5plugin.PLUGINS_PATH).glob('*bshuf*'))
        if not binaries:raise ValueError('No codec runtime binary inventory')
        runtime['binary_sha256s']={str(p.relative_to(h5root.parent)):file_hash(p) for p in sorted(set(binaries))}
        write(OUT/'runtime.json',runtime)
        write(OUT/'source_profile.json',{
            'schema':'radio-hd189733-codec-profile-v1','source_preparation_sha256':INPUTS[SOURCE],
            'source_inventory_sha256':source['source_inventory_sha256'],
            'source_scan_labels':[s['label'] for s in source['scans']],
            'filter_pipeline':profile,'dataset_shape':list(shape),'chunks':list(chunks),'dtype':'<f4',
            'decoded_chunk_bytes':CHUNK*4,
            'windows':[{k:w[k] for k in ('role','archive_interval','archive_chunk_index','identity')} for w in windows],
            'domain':'retained metadata plus local fixture','telescope_admission_authorized':False})
        encoder=OUT/'current_encoder_fixture.h5';legacy=OUT/'legacy_declaration_fixture.h5'
        # Every populated chunk is complete. The very large logical dataset
        # stays sparse; no other chunk or source value is generated or read.
        with h5py.File(encoder,'x',rdcc_nbytes=8*1024**2) as handle:
            ds=handle.create_dataset('data',shape=shape,chunks=chunks,dtype='<f4',
                                     **hdf5plugin.Bitshuffle(nelems=0,cname='lz4'))
            encoder_profile=filters.signature([ds.id.get_create_plist().get_filter(0)])
            for row in range(16):
                for w in windows:
                    ci=w['archive_chunk_index'];ds[row,0,ci*CHUNK:(ci+1)*CHUNK]=pattern(ci,row)
                    budget()
            handle.flush()
            if ds.id.get_num_chunks()!=48:raise ValueError('Unexpected encoder chunk inventory')
        print('encoded 48 full local chunks',flush=True)

        # Isolated process only. Remove automatic search paths, unregister
        # the filter while declaring the legacy CD tuple, write already
        # compressed bytes directly, then restore the real decoder.
        plugin_paths=[h5py.h5pl.get(i) for i in range(h5py.h5pl.size())]
        raw_receipts=[]
        try:
            for i in range(h5py.h5pl.size()-1,-1,-1):h5py.h5pl.remove(i)
            if not h5py.h5z.unregister_filter(32008) or h5py.h5z.filter_avail(32008):
                raise RuntimeError('Cannot isolate optional-filter fixture creation')
            with h5py.File(legacy,'x',rdcc_nbytes=8*1024**2) as handle:
                dcpl=h5py.h5p.create(h5py.h5p.DATASET_CREATE);dcpl.set_chunk(chunks)
                dcpl.set_filter(32008,h5py.h5z.FLAG_OPTIONAL,(0,3,4,0,2))
                dcpl.set_fill_time(h5py.h5d.FILL_TIME_NEVER)
                did=h5py.h5d.create(handle.id,b'data',h5py.h5t.IEEE_F32LE,
                                   h5py.h5s.create_simple(shape),dcpl=dcpl)
                ds=h5py.Dataset(did)
                filters.check_dataset(ds,profile)
                with h5py.File(encoder,'r',rdcc_nbytes=8*1024**2) as encoded:
                    for row in range(16):
                        for w in windows:
                            offset=(row,0,w['archive_chunk_index']*CHUNK)
                            mask,payload=encoded['data'].id.read_direct_chunk(offset)
                            if mask!=0:raise ValueError('Encoder skipped the declared filter')
                            ds.id.write_direct_chunk(offset,payload,filter_mask=0)
                            raw_receipts.append({'row':row,'role':w['role'],'offset':list(offset),
                                'filter_mask':int(mask),'compressed_bytes':len(payload),
                                'compressed_sha256':hashlib.sha256(payload).hexdigest()})
                            budget()
                handle.flush()
                if ds.id.get_num_chunks()!=48:raise ValueError('Unexpected legacy fixture chunk inventory')
        finally:
            for i in range(h5py.h5pl.size()-1,-1,-1):h5py.h5pl.remove(i)
            for path in plugin_paths:h5py.h5pl.append(path)
            if not hdf5plugin.register(filters=32008,force=True):raise RuntimeError('Codec registration restore failed')
        print('legacy source declaration preserved; decoder restored',flush=True)
        write(OUT/'compressed_chunk_receipts.json',raw_receipts)
        full_cells=extracted_cells=normalized_cells=0;decoded_receipts=[];normalization_receipts=[]
        with h5py.File(legacy,'r',rdcc_nbytes=8*1024**2) as handle:
            ds=handle['data'];filters.check_dataset(ds,profile)
            for w in windows:
                expected_rows=[];decoded_rows=[];ci=w['archive_chunk_index'];lo,hi=w['archive_interval']
                for row in range(16):
                    expected=pattern(ci,row);decoded=ds[row,0,ci*CHUNK:(ci+1)*CHUNK]
                    if decoded.dtype!=np.dtype('<f4') or not np.array_equal(decoded.view('<u4'),expected.view('<u4')):
                        raise ValueError('Full-chunk decoded bytes differ')
                    full_cells+=CHUNK
                    # Selection oracle is direct arithmetic from the fixed
                    # pattern; the measured selection is a separate HDF5 read.
                    expected_selection=expected[lo-ci*CHUNK:hi-ci*CHUNK]
                    selected=ds[row,0,lo:hi]
                    if not np.array_equal(selected.view('<u4'),expected_selection.view('<u4')):
                        raise ValueError('Archive extraction mapping differs')
                    expected_rows.append(expected_selection.copy());decoded_rows.append(selected)
                    extracted_cells+=len(selected)
                    decoded_receipts.append({'role':w['role'],'row':row,'decoded_sha256':native.array_hash(decoded),
                        'selected_native_sha256':native.array_hash(selected),'all_bits_equal':True})
                    budget()
                geom=core.NativeFrequencyGeometry(channel_count=65536,
                    channel_width_hz=abs(source['scans'][0]['expected_header']['foff_mhz'])*1e6,
                    raw_zero_hz=w['native_frequency_low_hz'])
                adapted=native.normalize_synthetic_rows(lambda row:decoded_rows[row],geom,16,
                    input_orientation='descending',scope={'kind':'synthetic',
                        'input_domain':'hd189733-source-shaped-codec-fixture','role':w['role'],
                        'source_preparation_sha256':INPUTS[SOURCE],'telescope_provenance':False})
                for row,expected_selection in enumerate(expected_rows):
                    expected_norm=np.empty(65536,dtype='<f4')
                    ascending=expected_selection[::-1]
                    for start in range(0,65536,4096):
                        expected_norm[start:start+4096]=normalization.normalize_float32_blocks_v0p6(
                            ascending[start:start+4096].reshape(1,-1))[0]
                    if not np.array_equal(adapted.values[row].view('<u4'),expected_norm.view('<u4')):
                        raise ValueError('Independent selection/orientation normalization differs')
                    normalization_receipts.append({'role':w['role'],'row':row,
                        'normalized_sha256':native.array_hash(adapted.values[row]),'all_bits_equal':True})
                    normalized_cells+=65536
                completed.append(w['role']);budget()
        write(OUT/'decoded_row_receipts.json',decoded_receipts)
        write(OUT/'normalization_receipts.json',normalization_receipts)
        for path,checksum in pins.items():
            if file_hash(ROOT/path)!=checksum:raise ValueError('Input changed during fixture: '+path)
        result={'schema':'radio-hd189733-codec-profile-result-v1',
            'status':'EXACT_DECLARATION_AND_FULL_CHUNK_LOCAL_FIXTURE_PASS',
            'encoder_filter_pipeline':encoder_profile,'source_declaration_pipeline':profile,
            'populated_chunks':48,'complete_chunks_decoded':48,'decoded_cells_bit_exact':full_cells,
            'extracted_native_cells_bit_exact':extracted_cells,'normalized_cells_bit_exact':normalized_cells,
            'active_seconds':time.monotonic()-started,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'hdf5_fixtures':{p.name:{'bytes':p.stat().st_size,'sha256':file_hash(p)} for p in (encoder,legacy)},
            'fixture_data':'one deterministic arithmetic texture on three positions; not independent observations',
            'original_archive_encoder_or_payload_verified':False,
            'runtime_binary_identities_pinned':len(binaries),'current_runtime_source_shaped_codec_fixture_qualified':True,
            'real_source_receipt_handoff_qualified':False,'receiver_detector_handoff_qualified':False,
            'new_source_requests':0,'telescope_spectra_opened':False,'new_scientific_attempt_allocations':0,
            'old_source_preparation_unchanged':True,'telescope_admission_authorized':False}
        budget();write(OUT/'result.json',result);print(json.dumps(result,indent=2),flush=True)
    except BaseException as error:
        write(OUT/'error.json',{'error':repr(error),'traceback':traceback.format_exc(),
            'completed_roles':completed,'active_seconds':time.monotonic()-started,
            'new_source_requests':0,'telescope_spectra_opened':False,'fixture_retry_authorized':False})
        raise


if __name__=='__main__':main()
