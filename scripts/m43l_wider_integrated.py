#!/usr/bin/env python3
"""M43L exhaustive wider integrated scores, seven bounded numerical processes."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import subprocess
import time
import numpy as np
from m43f_source_cache_preflight import build_context
from m43e_economical_bank import read_sealed,write_sealed
from m43j_exhaustive_anchors import batches
from m43l_reference import build_reference,integrate_reference
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43l_wider_integrated'


def validate_batches(records,count,size,support):
    intervals=batches(count,size)
    if len(records)!=len(intervals):raise ValueError('incomplete batch inventory')
    for r,(a,b) in zip(records,intervals):
        if (r['template_start']!=a or r['template_stop']!=b or r['cells_compared']!=(b-a)*support
                or r['factorized_reference_exact'] is not True):raise ValueError('batch inventory or exactness differs')
        core._frozen_sha256(r['score_sha256'],'batch score')
    return sum(r['cells_compared'] for r in records)


def qualify_batch(cache,reference,a,b,*,gather_chunk,reference_chunk,retain_indices):
    actual=transfer.gather_bank_slice(cache,0,cache.grid.support_bin_count,
        template_indices=np.arange(a,b),chunk_bins=gather_chunk)
    for left in range(0,cache.grid.support_bin_count,reference_chunk):
        right=min(left+reference_chunk,cache.grid.support_bin_count)
        expected=integrate_reference(reference,cache.factors[a:b],cache.grid,left,right)
        if actual[:,left:right].dtype!=expected.dtype or not np.array_equal(actual[:,left:right],expected):
            raise RuntimeError(f'factorized reference mismatch: templates {a}:{b}, carriers {left}:{right}')
    vectors={i:actual[i-a].copy() for i in retain_indices if a<=i<b}
    return {'template_start':a,'template_stop':b,'cells_compared':(b-a)*cache.grid.support_bin_count,
        'factorized_reference_exact':True,'score_sha256':transfer.array_hash(actual)},vectors


def frozen_inputs(freeze):
    path=ROOT/'config/m43l_wider_integrated.json';cfg=json.loads(path.read_text())
    for name,h in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise RuntimeError('frozen input changed: '+name)
    if subprocess.check_output(['git','show',freeze+':config/m43l_wider_integrated.json'],cwd=ROOT)!=path.read_bytes():
        raise RuntimeError('configuration differs from public freeze')
    if cfg['numpy_version']!=np.__version__:raise RuntimeError('NumPy differs')
    return cfg,hashlib.sha256(path.read_bytes()).hexdigest()


def width_job(width,work_root,freeze,abort):
    try:
        cfg,config_sha=frozen_inputs(freeze)
        if width not in cfg['widths']:raise RuntimeError('unfrozen width')
        prior=read_sealed(ROOT/'results_m43i_telescope_transfer/qualification.json')
        native=read_sealed(ROOT/'results_m43k_native_filters/qualification.json')
        if prior['result_sha256']!=cfg['m43i_result_sha256'] or native['result_sha256']!=cfg['m43k_result_sha256']:
            raise RuntimeError('ancestor identity differs')
        _,_,_,_,basis,bank,table,_=build_context()
        if table.template_bank_sha256!=cfg['bank_sha256'] or table.factor_table_sha256!=cfg['factor_table_sha256']:
            raise RuntimeError('bank/factors differ')
        grid=core.make_m37_proxy_carrier_grid(cfg['window'])
        if core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256']:raise RuntimeError('grid differs')
        results=[];started=time.monotonic()
        for anchor in cfg['anchors']:
            if abort.is_set():raise RuntimeError('peer failure; stopped')
            label=anchor['scan'];matrix=core.factor_table_for_scan(table,basis,label)
            if len(matrix)!=cfg['template_count'] or core.factor_table_sha256(matrix)!=anchor['scan_factor_sha256']:
                raise RuntimeError('scan factor table differs')
            src=transfer.load_telescope_source(Path(work_root)/label/cfg['window'],trusted_receipt_sha256=anchor['source_receipt_sha256'])
            old_src=next(s for s in prior['sources'] if s['scan']==label)
            old=next(c for c in prior['checks'] if c['scan']==label and c['width']==width)
            k=next(c for c in native['checks'] if c['scan']==label and c['width']==width)
            if src.identity!=old_src['source_identity']:raise RuntimeError('source identity differs')
            cache=transfer.build_telescope_cache(src,matrix,grid,width,bank_sha256=table.template_bank_sha256)
            if cache.identity!=old['cache_identity'] or cache.payload_sha256!=k['cache_payload_sha256']:
                raise RuntimeError('cache identity differs')
            reference=build_reference(src.values,src.geometry,width,chunk_centers=cfg['native_reference_chunk'])
            if (reference.filtered_payload_sha256!=k['cache_payload_sha256']
                    or list(reference.row_sha256)!=[r['reference_sha256'] for r in k['native_rows']]):
                raise RuntimeError('independent native reference differs from M43K')
            checkpoint={'milestone':'M43L','freeze_commit':freeze,'config_sha256':config_sha,'scan':label,'width':width,
                'source_identity':src.identity,'receipt_sha256':src.trusted_receipt_sha256,
                'cache_identity':cache.identity,'cache_payload_sha256':cache.payload_sha256,
                'native_reference_sha256':reference.filtered_payload_sha256,'m43k_native_reference_exact':True,
                'batches':[],'complete':False}
            records=[];retained={};target=OUT/f'{label}.width{width:03d}.json'
            for index,(a,b) in enumerate(batches(len(matrix),cfg['template_batch'])):
                if abort.is_set():raise RuntimeError('peer failure; stopped')
                record,vectors=qualify_batch(cache,reference,a,b,gather_chunk=cfg['gather_chunk'],
                    reference_chunk=cfg['reference_chunk'],retain_indices=anchor['m43i_template_indices'])
                records.append(record);retained.update(vectors);checkpoint['batches']=records
                write_sealed(target,checkpoint)
                if (index+1)%4==0 or b==len(matrix):
                    print(f'{label} width {width}: {b}/{len(matrix)} templates exact; {time.monotonic()-started:.1f}s',flush=True)
            cells=validate_batches(records,cfg['template_count'],cfg['template_batch'],grid.support_bin_count)
            overlap=transfer.array_hash(np.stack([retained[i] for i in anchor['m43i_template_indices']]))
            if overlap!=old['full_score_sha256']:raise RuntimeError('M43I full vectors differ')
            checkpoint.update(complete=True,cells_compared=cells,m43i_full_vectors_exact=True,m43i_overlap_sha256=overlap)
            done=write_sealed(target,checkpoint)
            results.append({'scan':label,'width':width,'checkpoint':str(target.relative_to(ROOT)),
                'checkpoint_sha256':done['result_sha256'],'source_identity':src.identity,'cache_identity':cache.identity,
                'cells_compared':cells,'batch_count':len(records),'m43k_native_reference_exact':True,'m43i_full_vectors_exact':True})
            del cache,reference,src,retained,vectors
        return results
    except BaseException:
        abort.set()
        raise


def run(work_root,freeze):
    cfg,config_sha=frozen_inputs(freeze);OUT.mkdir(exist_ok=True);started=time.monotonic();results=[]
    context=mp.get_context('spawn')
    with context.Manager() as manager:
        abort=manager.Event()
        with ProcessPoolExecutor(max_workers=cfg['workers'],mp_context=context) as pool:
            jobs=[pool.submit(width_job,w,str(work_root),freeze,abort) for w in cfg['widths']]
            try:
                for job in as_completed(jobs):results.extend(job.result())
            except BaseException:
                abort.set()
                for job in jobs:job.cancel()
                raise
    order={a['scan']:i for i,a in enumerate(cfg['anchors'])}
    results.sort(key=lambda r:(order[r['scan']],r['width']))
    expected=[(a['scan'],w) for a in cfg['anchors'] for w in cfg['widths']]
    if [(r['scan'],r['width']) for r in results]!=expected:raise RuntimeError('source/width inventory differs')
    result=write_sealed(OUT/'qualification.json',{'milestone':'M43L','status':'all-wider-integrated-real-anchors-qualified',
        'freeze_commit':freeze,'config_sha256':config_sha,'m43i_result_sha256':cfg['m43i_result_sha256'],
        'm43j_result_sha256':cfg['m43j_result_sha256'],'m43k_result_sha256':cfg['m43k_result_sha256'],
        'bank_sha256':cfg['bank_sha256'],'factor_table_sha256':cfg['factor_table_sha256'],'grid_sha256':cfg['grid_sha256'],
        'numpy_version':np.__version__,'checks':results,'summary':{'sources':len(cfg['anchors']),'widths':cfg['widths'],
            'source_width_checks':len(results),'complete_template_vectors':len(results)*cfg['template_count'],
            'batches_completed':sum(r['batch_count'] for r in results),'integrated_score_cells_compared':sum(r['cells_compared'] for r in results)},
        'new_remote_requests':0,'candidate_selection_performed':False,'detection_threshold_calibrated':False,
        'multi_epoch_real_stack_qualified':False,'recovery_measured':False,'workers':cfg['workers'],
        'elapsed_seconds':round(time.monotonic()-started,3)})
    print(json.dumps({'result_sha256':result['result_sha256'],'summary':result['summary']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',type=Path,required=True);p.add_argument('--freeze-commit',required=True)
    args=p.parse_args();run(args.work_root,args.freeze_commit)
