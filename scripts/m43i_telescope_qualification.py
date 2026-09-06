#!/usr/bin/env python3
"""Frozen M43I real-source score anchors. Offline; no candidate selection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from m43f_source_cache_preflight import build_context
from m43e_economical_bank import read_sealed, write_sealed
from m43g_reference import sorted_reference, direct_reference
from seti_repeater import transfer_m43i as transfer
from seti_repeater import search_v0p6 as core

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43i_telescope_transfer'


def compare(a,b,label):
    if a.dtype!=b.dtype or a.shape!=b.shape or not np.array_equal(a,b):
        raise RuntimeError('M43I mismatch: '+label)


def run(work_root,freeze_commit):
    path=ROOT/'config/m43i_telescope_transfer.json'
    cfg=json.loads(path.read_text())
    for name,h in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:
            raise RuntimeError('frozen input changed: '+name)
    frozen=subprocess.check_output(['git','show',freeze_commit+':config/m43i_telescope_transfer.json'],cwd=ROOT)
    if frozen!=path.read_bytes():raise RuntimeError('configuration differs from freeze commit')
    if cfg['numpy_version']!=np.__version__ or cfg['contract_sha256']!=transfer.CONTRACT_SHA256:
        raise RuntimeError('frozen numerical runtime/contract changed')
    _,_,_,metadata,basis,bank,table,_=build_context()
    if table.factor_table_sha256!=cfg['factor_table_sha256'] or table.template_bank_sha256!=cfg['bank_sha256']:
        raise RuntimeError('fixed bank or factors changed')
    ancestor=read_sealed(ROOT/'results_m43h_widened_source/live_result.json')
    if ancestor['result_sha256']!=cfg['m43h_result_sha256']:raise RuntimeError('source qualification changed')
    grid=core.make_m37_proxy_carrier_grid(cfg['window'])
    if core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256']:raise RuntimeError('grid changed')
    OUT.mkdir(exist_ok=True)
    records=[];source_records=[]
    started=time.monotonic()
    for anchor in cfg['anchors']:
        label=anchor['scan'];directory=Path(work_root)/label/cfg['window']
        matrix=core.factor_table_for_scan(table,basis,label)
        if core.factor_table_sha256(matrix)!=anchor['scan_factor_sha256']:raise RuntimeError('scan factors changed')
        src=transfer.load_telescope_source(directory,trusted_receipt_sha256=anchor['source_receipt_sha256'])
        scope=json.loads(src.receipt_json)['scope']
        if scope['definition']['label']!=label or scope['window']!=cfg['window']:
            raise RuntimeError('source scan/window differs')
        for row in range(src.integration_count):
            raw=np.load(directory/f'row{row:02d}.native.npy',allow_pickle=False)
            reference=sorted_reference(np.ascontiguousarray(raw[::-1]).reshape(1,-1))
            compare(src.values[row:row+1],reference,'sorted native normalization')
        del raw,reference
        source_records.append({'scan':label,'source_identity':src.identity,
            'receipt_sha256':src.trusted_receipt_sha256,'normalized_sha256':src.normalized_sha256,
            'rows_sort_checked':src.integration_count,'native_channels':src.geometry.channel_count,
            'adapter_ndarray_bound_bytes':transfer.memory_bound(src.integration_count,src.geometry.channel_count)})
        chosen=anchor['full_grid_template_indices'];ranges=anchor['local_ranges']
        for width in cfg['widths']:
            cache=transfer.build_telescope_cache(src,matrix,grid,width,bank_sha256=table.template_bank_sha256)
            outputs=[]
            for start,stop in ranges:
                actual=transfer.gather_bank_slice(cache,start,stop,chunk_bins=cfg['local_chunk_bins'])
                reference=direct_reference(src.values,src.geometry,matrix,grid,width,start,stop)
                compare(actual,reference,'all-bank fixed local cells')
                outputs.append(actual)
            local_sha=transfer.array_hash(np.concatenate(outputs,axis=1))
            actual=transfer.gather_bank_slice(cache,0,grid.support_bin_count,template_indices=chosen,
                                             chunk_bins=cfg['full_chunk_bins'][0])
            alternate=transfer.gather_bank_slice(cache,0,grid.support_bin_count,template_indices=chosen,
                                                chunk_bins=cfg['full_chunk_bins'][1])
            compare(actual,alternate,'full-grid chunk invariance');del alternate
            for start in range(0,grid.support_bin_count,cfg['reference_chunk_bins']):
                stop=min(start+cfg['reference_chunk_bins'],grid.support_bin_count)
                reference=direct_reference(src.values,src.geometry,matrix[chosen],grid,width,start,stop)
                compare(actual[:,start:stop],reference,'full-grid direct native windows')
            for j,(start,stop) in enumerate(ranges):
                compare(actual[:,start:stop],outputs[j][chosen],'full/local agreement')
            duplicate=anchor['duplicate_witness']
            indices=core.nearest_native_indices(src.geometry,
                matrix[duplicate['template_index'],duplicate['integration_index']]*grid.support_hz[duplicate['support_indices']])
            if indices[0]!=indices[1]:raise RuntimeError('frozen repeat witness changed')
            row={'scan':label,'width':width,'source_identity':src.identity,'cache_identity':cache.identity,
                'cache_payload_sha256':cache.payload_sha256,'bank_templates':len(matrix),
                'local_cells_per_template':sum(b-a for a,b in ranges),'local_score_sha256':local_sha,
                'full_grid_template_indices':chosen,'support_cells_per_template':grid.support_bin_count,
                'full_score_sha256':transfer.array_hash(actual),
                'local_native_window_reference_exact':True,'full_native_window_reference_exact':True,
                'chunk_invariance_exact':True,'local_full_agreement_exact':True,
                'repeat_witness_retained':True}
            records.append(row)
            write_sealed(OUT/f'{label}.width{width:03d}.json',{'milestone':'M43I','freeze_commit':freeze_commit,
                'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'check':row})
            print(f'{label} width {width}: exact, {time.monotonic()-started:.1f}s elapsed',flush=True)
            del cache,actual,reference,outputs
        del src
    result={'milestone':'M43I','status':'bounded-telescope-score-anchors-qualified',
        'freeze_commit':freeze_commit,'config_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'contract_sha256':transfer.CONTRACT_SHA256,'bank_sha256':table.template_bank_sha256,
        'factor_table_sha256':table.factor_table_sha256,'m43h_result_sha256':ancestor['result_sha256'],
        'numpy_version':np.__version__,'sources':source_records,'checks':records,
        'summary':{'telescope_sources':len(source_records),'normalization_rows_sort_checked':sum(s['rows_sort_checked'] for s in source_records),
            'bank_scan_width_local_checks':len(records),
            'local_score_cells_compared':sum(r['bank_templates']*r['local_cells_per_template'] for r in records),
            'full_grid_template_vectors':sum(len(r['full_grid_template_indices']) for r in records),
            'full_grid_score_cells_compared':sum(len(r['full_grid_template_indices'])*r['support_cells_per_template'] for r in records)},
        'new_remote_requests':0,'full_bank_full_grid_search':False,'epoch_stack_qualified_on_real_data':False,
        'candidate_selection_performed':False,'detection_threshold_calibrated':False,'recovery_measured':False,
        'elapsed_seconds':round(time.monotonic()-started,3)}
    final=write_sealed(OUT/'qualification.json',result)
    print(json.dumps({'result_sha256':final['result_sha256'],'summary':final['summary']},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--work-root',type=Path,required=True)
    parser.add_argument('--freeze-commit',required=True)
    args=parser.parse_args();run(args.work_root,args.freeze_commit)
