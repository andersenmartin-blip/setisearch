#!/usr/bin/env python3
"""M43J exhaustive width-one real-data numerical anchors, without detection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from m43f_source_cache_preflight import build_context
from m43e_economical_bank import read_sealed, write_sealed
from m43g_reference import direct_reference
from seti_repeater import transfer_m43i as transfer
from seti_repeater import search_v0p6 as core

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43j_exhaustive_anchors'


def batches(count,size):
    transfer.integer(count,'template count');transfer.integer(size,'batch size')
    return [(a,min(a+size,count)) for a in range(0,count,size)]


def qualify_batch(cache,start,stop,*,gather_chunk,reference_chunk,retain_indices=()):
    """Bank-contiguous batch, each selected template spans the ENTIRE support."""
    transfer.integer(start,'template start',0);transfer.integer(stop,'template stop')
    transfer.integer(reference_chunk,'reference chunk')
    if stop<=start or stop>len(cache.factors):raise ValueError('invalid template batch')
    selection=np.arange(start,stop)
    actual=transfer.gather_bank_slice(cache,0,cache.grid.support_bin_count,
            template_indices=selection,chunk_bins=gather_chunk)
    for left in range(0,cache.grid.support_bin_count,reference_chunk):
        right=min(left+reference_chunk,cache.grid.support_bin_count)
        expected=direct_reference(cache.source.values,cache.source.geometry,
                cache.factors[selection],cache.grid,cache.width,left,right)
        if (actual[:,left:right].dtype!=expected.dtype
                or actual[:,left:right].shape!=expected.shape
                or not np.array_equal(actual[:,left:right],expected)):
            raise RuntimeError(f'M43J exactness failure: templates {start}:{stop}, support {left}:{right}')
    # Retain only the two preselected M43I vectors for an ancestor comparison.
    retained={i:np.array(actual[i-start]) for i in retain_indices if start<=i<stop}
    record={'template_start':start,'template_stop':stop,
        'support_cells_per_template':cache.grid.support_bin_count,
        'cells_compared':(stop-start)*cache.grid.support_bin_count,
        'score_sha256':transfer.array_hash(actual),'native_window_reference_exact':True}
    return record,retained


def validate_inventory(records,*,count,size,support):
    expected=batches(count,size)
    if len(records)!=len(expected):raise ValueError('incomplete batch inventory')
    for r,(a,b) in zip(records,expected):
        if (r['template_start']!=a or r['template_stop']!=b
                or r['support_cells_per_template']!=support
                or r['cells_compared']!=(b-a)*support
                or r['native_window_reference_exact'] is not True):
            raise ValueError('batch coverage, count or exactness differs')
        core._frozen_sha256(r['score_sha256'],'batch score')
    return sum(r['cells_compared'] for r in records)


def run(work_root,freeze_commit):
    path=ROOT/'config/m43j_exhaustive_anchors.json';cfg=json.loads(path.read_text())
    config_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    for name,h in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:
            raise RuntimeError('frozen input changed: '+name)
    if subprocess.check_output(['git','show',freeze_commit+':config/m43j_exhaustive_anchors.json'],cwd=ROOT)!=path.read_bytes():
        raise RuntimeError('configuration differs from freeze commit')
    if cfg['numpy_version']!=np.__version__ or cfg['width']!=1:
        raise RuntimeError('frozen runtime or width differs')
    _,_,_,_,basis,bank,table,_=build_context()
    if table.template_bank_sha256!=cfg['bank_sha256'] or table.factor_table_sha256!=cfg['factor_table_sha256']:
        raise RuntimeError('bank/factors differ')
    prior=read_sealed(ROOT/'results_m43i_telescope_transfer/qualification.json')
    if prior['result_sha256']!=cfg['m43i_result_sha256']:raise RuntimeError('M43I differs')
    grid=core.make_m37_proxy_carrier_grid(cfg['window'])
    if core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256'] or grid.support_bin_count!=cfg['support_cells']:
        raise RuntimeError('grid differs')
    OUT.mkdir(exist_ok=True);source_results=[];started=time.monotonic()
    for anchor in cfg['anchors']:
        label=anchor['scan'];matrix=core.factor_table_for_scan(table,basis,label)
        if core.factor_table_sha256(matrix)!=anchor['scan_factor_sha256'] or len(matrix)!=cfg['template_count']:
            raise RuntimeError('scan factors/count differ')
        src=transfer.load_telescope_source(Path(work_root)/label/cfg['window'],
                trusted_receipt_sha256=anchor['source_receipt_sha256'])
        scope=json.loads(src.receipt_json)['scope']
        if scope['definition']['label']!=label or scope['window']!=cfg['window']:
            raise RuntimeError('source scan/window differs')
        old_source=next(s for s in prior['sources'] if s['scan']==label)
        if src.identity!=old_source['source_identity']:raise RuntimeError('M43I source identity differs')
        cache=transfer.build_telescope_cache(src,matrix,grid,1,bank_sha256=table.template_bank_sha256)
        old=next(c for c in prior['checks'] if c['scan']==label and c['width']==1)
        if cache.identity!=old['cache_identity'] or cache.payload_sha256!=old['cache_payload_sha256']:
            raise RuntimeError('M43I cache identity differs')
        records=[];retained={}
        for a,b in batches(len(matrix),cfg['template_batch']):
            record,vectors=qualify_batch(cache,a,b,gather_chunk=cfg['gather_chunk'],
                reference_chunk=cfg['reference_chunk'],retain_indices=anchor['m43i_template_indices'])
            retained.update(vectors);records.append(record)
            write_sealed(OUT/f'{label}.batch{a:04d}.json',{'milestone':'M43J',
                'freeze_commit':freeze_commit,'config_sha256':config_sha,'scan':label,
                'source_identity':src.identity,'cache_identity':cache.identity,'check':record})
            print(f'{label} {b}/{len(matrix)} templates exact; {time.monotonic()-started:.1f}s',flush=True)
        cells=validate_inventory(records,count=len(matrix),size=cfg['template_batch'],support=grid.support_bin_count)
        overlap_sha=transfer.array_hash(np.stack([retained[i] for i in anchor['m43i_template_indices']]))
        if overlap_sha!=old['full_score_sha256']:raise RuntimeError('M43I full-vector overlap differs')
        source_results.append({'scan':label,'source_identity':src.identity,'receipt_sha256':src.trusted_receipt_sha256,
            'cache_identity':cache.identity,'cache_payload_sha256':cache.payload_sha256,
            'cells_compared':cells,'batches':records,'m43i_full_vectors_exact':True,
            'm43i_overlap_sha256':overlap_sha})
        del cache,src,retained,vectors
    summary={'telescope_sources':len(source_results),'native_width':1,'templates_per_source':cfg['template_count'],
        'support_cells_per_template':grid.support_bin_count,'complete_template_vectors':len(source_results)*cfg['template_count'],
        'batches_completed':sum(len(s['batches']) for s in source_results),
        'score_cells_compared':sum(s['cells_compared'] for s in source_results)}
    result=write_sealed(OUT/'qualification.json',{'milestone':'M43J','status':'exhaustive-width-one-real-anchors-qualified',
        'freeze_commit':freeze_commit,'config_sha256':config_sha,'m43i_result_sha256':prior['result_sha256'],
        'bank_sha256':table.template_bank_sha256,'factor_table_sha256':table.factor_table_sha256,
        'grid_sha256':cfg['grid_sha256'],'numpy_version':np.__version__,'sources':source_results,'summary':summary,
        'new_remote_requests':0,'candidate_selection_performed':False,'detection_threshold_calibrated':False,
        'multi_epoch_real_stack_qualified':False,'all_widths_exhaustive':False,'recovery_measured':False,
        'elapsed_seconds':round(time.monotonic()-started,3)})
    print(json.dumps({'result_sha256':result['result_sha256'],'summary':summary},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--work-root',type=Path,required=True)
    parser.add_argument('--freeze-commit',required=True);args=parser.parse_args()
    run(args.work_root,args.freeze_commit)
