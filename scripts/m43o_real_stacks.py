#!/usr/bin/env python3
"""Frozen real-stack qualification through retained per-epoch batch digests."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import numpy as np
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43j_exhaustive_anchors import batches
from m43l_wider_integrated import FileAbort
from m43o_stack_reference import qualify_stacks,SUBSETS,MODES
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43o_real_stacks'
CONFIG=ROOT/'config/m43o_real_stacks.json'


def frozen(freeze):
    cfg=json.loads(CONFIG.read_text())
    for path,digest in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('frozen input changed: '+path)
    if subprocess.check_output(['git','show',freeze+':config/m43o_real_stacks.json'],cwd=ROOT)!=CONFIG.read_bytes():
        raise ValueError('configuration differs from public freeze')
    if np.__version__!=cfg['numpy_version'] or cfg['subsets']!=[list(x) for x in SUBSETS] or cfg['modes']!=list(MODES):
        raise ValueError('runtime or stack rule differs')
    return cfg,hashlib.sha256(CONFIG.read_bytes()).hexdigest()


def ancestor(cfg,label,width):
    spec=next(x for x in cfg['ancestors'] if x['scan']==label and x['width']==width)
    result=read_sealed(ROOT/spec['path'])
    if result['result_sha256']!=spec['result_sha256']:raise ValueError('ancestor checkpoint identity differs')
    if spec['milestone']=='M43J':
        item=next(x for x in result['sources'] if x['scan']==label)
    else:
        item=result
        if item['complete'] is not True or item['scan']!=label or item['width']!=width:
            raise ValueError('ancestor source/width differs')
    if len(item['batches'])!=54:raise ValueError('ancestor incomplete')
    return item,spec


def validate_checkpoint(cp,cfg,kind,width,freeze,contract):
    if (cp['kind']!=kind or cp['width']!=width or cp['freeze_commit']!=freeze or cp['config_sha256']!=contract
            or cp['complete'] is not True):raise ValueError('incomplete or changed stack checkpoint')
    expected_labels=[f'epoch{i}_{kind}' for i in (1,2,3)]
    if [x['scan'] for x in cp['sources']]!=expected_labels:raise ValueError('stack source order differs')
    resolved=[ancestor(cfg,label,width) for label in expected_labels]
    ancestors=[x[0] for x in resolved]
    for source,(old,spec) in zip(cp['sources'],resolved):
        anchor=next(x for x in cfg['sources'] if x['scan']==source['scan'])
        if (source['receipt_sha256']!=anchor['receipt_sha256'] or source['ancestor_path']!=spec['path']
                or source['ancestor_result_sha256']!=spec['result_sha256']):raise ValueError('source trust anchor differs')
        if source['source_identity']!=old['source_identity'] or source['cache_identity']!=old['cache_identity']:
            raise ValueError('stack source/cache identity differs')
    intervals=batches(cfg['template_count'],cfg['template_batch'])
    if len(cp['batches'])!=len(intervals):raise ValueError('stack batch inventory differs')
    replay=0;stack=0;finite={mode:0 for mode in MODES}
    for index,(record,(a,b)) in enumerate(zip(cp['batches'],intervals)):
        if record['template_start']!=a or record['template_stop']!=b:raise ValueError('stack batch bounds differ')
        expected_hashes=[]
        for old in ancestors:
            batch=old['batches'][index]
            if batch['template_start']!=a or batch['template_stop']!=b:raise ValueError('ancestor bounds differ')
            expected_hashes.append(batch['score_sha256'])
        if record['epoch_score_sha256']!=expected_hashes:raise ValueError('epoch replay lineage differs')
        expected=[(mode,list(subset)) for mode in MODES for subset in SUBSETS]
        if [(x['mode'],x['subset']) for x in record['stacks']]!=expected:raise ValueError('stack rule inventory differs')
        cells=(b-a)*cfg['support_carriers'];replay+=3*cells
        for item in record['stacks']:
            if item['cells_compared']!=cells or item['reference_exact'] is not True:raise ValueError('stack comparison incomplete')
            if not 0<=item['finite_cells']<=cells:raise ValueError('finite count invalid')
            if item['mode']=='raw' and item['finite_cells']!=cells:raise ValueError('raw arithmetic not fully checked')
            core._frozen_sha256(item['score_sha256'],'stack digest')
            finite[item['mode']]+=item['finite_cells'];stack+=cells
    return {'kind':kind,'width':width,'checkpoint':f'results_m43o_real_stacks/{kind}.width{width:03d}.json',
        'checkpoint_sha256':cp['result_sha256'],'batches':len(intervals),'epoch_cells_replayed':replay,
        'stack_cells_compared':stack,'finite_cells_by_mode':finite}


def one(kind,width,work_root,freeze,abort):
    try:
        cfg,contract=frozen(freeze)
        if kind not in cfg['kinds'] or width not in cfg['widths']:raise ValueError('unfrozen job')
        if abort.is_set():raise RuntimeError('peer failure; queued job stopped')
        _,_,_,metadata,basis,bank,table,_=build_context()
        grid=core.make_m37_proxy_carrier_grid(cfg['window'])
        if (core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256'] or table.template_bank_sha256!=cfg['bank_sha256']
                or table.factor_table_sha256!=cfg['factor_table_sha256']):raise ValueError('bank/factors/grid differ')
        labels=[f'epoch{i}_{kind}' for i in (1,2,3)];sources=[];caches=[];priors=[];times=[]
        for label in labels:
            definition=next(x for x in metadata['scans'] if x['label']==label)
            if definition['kind'].lower()!=kind:raise ValueError('ON/OFF source mixture')
            times.append(definition['expected_header']['tstart_mjd'])
            anchor=next(x for x in cfg['sources'] if x['scan']==label)
            matrix=core.factor_table_for_scan(table,basis,label)
            if core.factor_table_sha256(matrix)!=anchor['scan_factor_sha256']:raise ValueError('scan factors changed')
            source=transfer.load_telescope_source(work_root/label/cfg['window'],trusted_receipt_sha256=anchor['receipt_sha256'])
            cache=transfer.build_telescope_cache(source,matrix,grid,width,bank_sha256=cfg['bank_sha256'])
            old,spec=ancestor(cfg,label,width)
            if source.identity!=old['source_identity'] or cache.identity!=old['cache_identity']:raise ValueError('ancestor source/cache differs')
            sources.append({'scan':label,'receipt_sha256':anchor['receipt_sha256'],'source_identity':source.identity,
                'cache_identity':cache.identity,'ancestor_path':spec['path'],'ancestor_result_sha256':spec['result_sha256']})
            caches.append(cache);priors.append(old)
        if not times[0]<times[1]<times[2]:raise ValueError('epoch times not ordered')
        cp={'milestone':'M43O','freeze_commit':freeze,'config_sha256':contract,'kind':kind,'width':width,
            'sources':sources,'batches':[],'complete':False}
        path=OUT/f'{kind}.width{width:03d}.json'
        for index,(a,b) in enumerate(batches(cfg['template_count'],cfg['template_batch'])):
            if abort.is_set():raise RuntimeError('peer failure; stopped before batch')
            vectors=[];expected=[]
            for cache,old in zip(caches,priors):
                prior=old['batches'][index]
                if prior['template_start']!=a or prior['template_stop']!=b:raise ValueError('ancestor batch bounds differ')
                value=transfer.gather_bank_slice(cache,0,grid.support_bin_count,template_indices=np.arange(a,b),chunk_bins=cfg['gather_chunk'])
                vectors.append(value);expected.append(prior['score_sha256'])
            stacks=qualify_stacks(vectors,labels,kind,expected,chunk_bins=cfg['stack_chunk'])
            cp['batches'].append({'template_start':a,'template_stop':b,'epoch_score_sha256':expected,'stacks':stacks})
            write_sealed(path,cp)
            del vectors,value,stacks
            if (index+1)%8==0 or b==cfg['template_count']:
                print(f'{kind} width {width}: {b}/{cfg["template_count"]} templates, all stack rules exact',flush=True)
        cp['complete']=True;done=write_sealed(path,cp)
        validate_checkpoint(done,cfg,kind,width,freeze,contract)
    except BaseException:
        abort.set();raise


def run(work_root,freeze):
    cfg,contract=frozen(freeze);OUT.mkdir(exist_ok=True);started=time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='m43o-control-') as d:
            abort_path=Path(d)/'abort';abort=FileAbort(abort_path)
            def child(kind,width):
                if abort.is_set():raise RuntimeError('peer failure; queued job stopped')
                r=subprocess.run([sys.executable,__file__,'--work-root',str(work_root),'--freeze-commit',freeze,
                    '--kind',kind,'--width',str(width),'--abort-file',str(abort_path)])
                if r.returncode:abort.set();raise RuntimeError(f'{kind} width {width} exited {r.returncode}')
            with ThreadPoolExecutor(max_workers=cfg['workers']) as pool:
                jobs=[pool.submit(child,kind,width) for width in reversed(cfg['widths']) for kind in cfg['kinds']]
                try:
                    for job in as_completed(jobs):job.result()
                except BaseException:
                    abort.set()
                    for job in jobs:job.cancel()
                    raise
        checks=[validate_checkpoint(read_sealed(OUT/f'{kind}.width{width:03d}.json'),cfg,kind,width,freeze,contract)
            for kind in cfg['kinds'] for width in cfg['widths']]
        summary={'source_width_inputs':48,'kind_width_checks':len(checks),'batches':sum(x['batches'] for x in checks),
            'epoch_cells_replayed':sum(x['epoch_cells_replayed'] for x in checks),
            'stack_cells_compared':sum(x['stack_cells_compared'] for x in checks),
            'raw_stack_cells':sum(x['finite_cells_by_mode']['raw'] for x in checks),
            'active3_finite_cells':sum(x['finite_cells_by_mode']['active3'] for x in checks)}
        for key,value in cfg['expected_counts'].items():
            if summary[key]!=value:raise ValueError('frozen denominator differs: '+key)
        result=write_sealed(OUT/'qualification.json',{'milestone':'M43O','status':'real-stack-arithmetic-and-active-cut-qualified',
            'freeze_commit':freeze,'config_sha256':contract,'bank_sha256':cfg['bank_sha256'],
            'factor_table_sha256':cfg['factor_table_sha256'],'grid_sha256':cfg['grid_sha256'],
            'numpy_version':np.__version__,'workers':cfg['workers'],'checks':checks,'summary':summary,
            'new_remote_requests':0,'exclusion_masks_qualified':False,'candidate_selection_performed':False,
            'detection_threshold_calibrated':False,'recovery_measured':False,'elapsed_seconds':round(time.monotonic()-started,3)})
        print(json.dumps({'result_sha256':result['result_sha256'],'summary':summary}),flush=True)
    except BaseException as error:
        write_sealed(OUT/'run_failure.json',{'milestone':'M43O','freeze_commit':freeze,'config_sha256':contract,
            'status':'incomplete','error_type':type(error).__name__,'reason':str(error),
            'checkpoint_paths':sorted(str(p.relative_to(ROOT)) for p in OUT.glob('*.width*.json'))})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',required=True,type=Path);p.add_argument('--freeze-commit',required=True)
    p.add_argument('--kind');p.add_argument('--width',type=int);p.add_argument('--abort-file',type=Path);a=p.parse_args()
    if a.kind:
        if a.width is None or a.abort_file is None:p.error('kind requires width and abort-file')
        one(a.kind,a.width,a.work_root,a.freeze_commit,FileAbort(a.abort_file))
    else:run(a.work_root,a.freeze_commit)
