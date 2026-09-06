#!/usr/bin/env python3
"""One frozen M43P run: sparse transfer, masks, stacks and scramble wiring.

Full-support real anchors use the first and final retained M43O batches.
Scrambles test numerical wiring; this script does not calibrate a threshold.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43o_real_stacks import ancestor
from m43p_reference import mask_reference, sparse_reference, masked_stack_reference, scramble_reference
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer
from seti_repeater.adjacent_m43p import gather_score_indices, paired_off_decision

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43p_combined_controls'
CONFIG=ROOT/'config/m43p_combined_controls.json'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen(commit):
    cfg=json.loads(CONFIG.read_text())
    if subprocess.check_output(['git','show',commit+':config/m43p_combined_controls.json'],cwd=ROOT)!=CONFIG.read_bytes():
        raise ValueError('configuration differs from pre-evaluation freeze')
    for name,digest in cfg['pinned_sha256'].items():
        if sha(ROOT/name)!=digest: raise ValueError('frozen input changed: '+name)
    if np.__version__!=cfg['numpy_version']: raise ValueError('NumPy runtime differs')
    return cfg


def equal(a,b,label):
    if a.shape!=b.shape or a.dtype!=b.dtype or not np.array_equal(a,b):
        raise RuntimeError('M43P comparison failed: '+label)


def source_job(kind,width,work,source_root,freeze):
    cfg=frozen(freeze); parent=json.loads((ROOT/'config/m43o_real_stacks.json').read_text())
    if kind not in ('on','off') or width not in cfg['widths']:raise ValueError('unfrozen source job')
    _,_,_,metadata,basis,bank,table,_=build_context()
    grid=core.make_m37_proxy_carrier_grid(cfg['window'])
    if (table.template_bank_sha256!=cfg['bank_sha256'] or table.factor_table_sha256!=cfg['factor_table_sha256']
            or core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256']):
        raise ValueError('bank/factors/grid changed')
    records=[]; sparse=[]
    for epoch in (1,2,3):
        if (work/'abort').exists(): raise RuntimeError('peer failed')
        label=f'epoch{epoch}_{kind}'
        anchor=next(x for x in parent['sources'] if x['scan']==label)
        factors=core.factor_table_for_scan(table,basis,label)
        if core.factor_table_sha256(factors)!=anchor['scan_factor_sha256']: raise ValueError('scan factors changed')
        src=transfer.load_telescope_source(source_root/label/cfg['window'],trusted_receipt_sha256=anchor['receipt_sha256'])
        cache=transfer.build_telescope_cache(src,factors,grid,width,bank_sha256=cfg['bank_sha256'])
        old,spec=ancestor(parent,label,width)
        if src.identity!=old['source_identity'] or cache.identity!=old['cache_identity']:
            raise ValueError('source/cache differs from completed M43J/L/N')
        queries=np.asarray(cfg['query_score_indices'][label],dtype=np.int64)
        actual=gather_score_indices(cache,queries,chunk_bins=4)
        expected=sparse_reference(src,factors,grid,width,queries)
        equal(actual,expected,'all-bank sparse/native windows')
        arrays=[]
        for batch_index in cfg['ancestor_batch_indices']:
            b=old['batches'][batch_index]; a,z=b['template_start'],b['template_stop']
            scores=transfer.gather_bank_slice(cache,0,grid.support_bin_count,template_indices=np.arange(a,z),chunk_bins=4096)
            if transfer.array_hash(scores)!=b['score_sha256']: raise ValueError('anchor replay changed')
            equal(actual[a:z],scores[:,queries+grid.support_guard_bins],'sparse/full anchors')
            name=f'{label}.width{width:03d}.batch{batch_index:02d}.npy'
            np.save(work/name,scores,allow_pickle=False)
            arrays.append({'path':name,'template_start':a,'template_stop':z,'score_sha256':b['score_sha256']})
            del scores
        records.append({'scan':label,'source_identity':src.identity,'receipt_sha256':anchor['receipt_sha256'],
            'cache_identity':cache.identity,'ancestor_result_sha256':spec['result_sha256'],
            'queries':queries.tolist(),'sparse_cells':actual.size,'sparse_score_sha256':transfer.array_hash(actual),
            'native_window_exact':True,'full_anchor_exact':True,'arrays':arrays})
        sparse.append(actual)
        del src,cache,actual,expected
    # Each scan has its own duplicate-channel witness positions. Only the first
    # seven common queries can be compared as exact paired OFF coordinates.
    veto=[]
    if kind=='off':
        cube=np.stack([x[:,:7] for x in sparse])
        for subset in core.M37_ACTIVITY_SUBSETS:
            values=cube.reshape(3,-1)
            actual=paired_off_decision(values,subset)
            expected=np.array([any(float(values[e,q])>=5.5 for e in subset) for q in range(values.shape[1])])
            equal(actual,expected,'paired OFF rule')
            veto.append({'subset':list(subset),'cells_compared':actual.size,'vetoed_cells':int(actual.sum()),
                         'mask_applied':False,'numerical_diagnostic_only':True})
    cp={'milestone':'M43P','freeze_commit':freeze,'config_sha256':sha(CONFIG),'kind':kind,'width':width,
        'complete':True,'sources':records,'paired_off_checks':veto}
    write_sealed(OUT/f'{kind}.width{width:03d}.json',cp)
    print(f'{kind} width {width}: all-bank sparse oracle and 37 full-support anchors exact',flush=True)


def make_accumulator(cfg,kind,template,shifts):
    # Explicitly a one-template diagnostic inventory, never a full-bank null.
    scope=hashlib.sha256(core.canonical_json_bytes({'bank':cfg['bank_sha256'],'template':template})).hexdigest()
    return core.CalibrationAccumulator.create(window_id='m43p-component-'+kind,score_bin_count=cfg['score_carriers'],
        template_count=1,template_bank_sha256_value=scope,factor_basis_sha256_value=core.M37_FACTOR_BASIS_SHA256,
        factor_basis_labels_sha256_value=core.M37_FACTOR_BASIS_LABELS_SHA256,
        scan_inventory_sha256_value=core.M37_SCAN_INVENTORY_SHA256,
        factor_row_selection_sha256_value=core.M37_FACTOR_ROW_SELECTION_SHA256S[kind],
        factor_table_sha256_value=cfg['factor_table_sha256'],spectral_widths=cfg['widths'],
        activity_subsets=core.M37_ACTIVITY_SUBSETS,minimum_active_epoch_snr=3.,stack_statistic='sum',
        scramble_shifts=shifts,minimum_shift_bins=cfg['minimum_shift_bins'],
        expected_scramble_sha256=cfg['scramble_table_sha256'])


def logic_job(kind,work,freeze):
    cfg=frozen(freeze); grid=core.make_m37_proxy_carrier_grid(cfg['window'])
    shifts=np.asarray(cfg['scramble_shifts'],dtype=np.int64)
    loaded={}; fingerprints={}
    for width in cfg['widths']:
        cp=read_sealed(OUT/f'{kind}.width{width:03d}.json')
        if (not cp['complete'] or cp['freeze_commit']!=freeze or cp['config_sha256']!=sha(CONFIG)
                or cp['kind']!=kind or cp['width']!=width
                or [s['scan'] for s in cp['sources']]!=[f'epoch{e}_{kind}' for e in (1,2,3)]):
            raise ValueError('source checkpoint differs')
        for source in cp['sources']:
            for item in source['arrays']:
                a=np.load(work/item['path'],mmap_mode='r',allow_pickle=False)
                if transfer.array_hash(a)!=item['score_sha256']:raise ValueError('stored anchor array changed')
                loaded[(width,source['scan'],item['template_start'])]=a
                fingerprints[item['path']]=item['score_sha256']
    checks=[]
    for start,stop in cfg['template_intervals']:
        for template in range(start,stop):
            if (work/'abort').exists():raise RuntimeError('peer failed')
            support={width:np.stack([loaded[(width,f'epoch{epoch}_{kind}',start)][template-start]
                                    for epoch in (1,2,3)]) for width in cfg['widths']}
            mask=core.build_m37_two_pass_template_mask(support.__getitem__)
            expected=mask_reference(support);equal(mask,expected,'width-OR and full-support dilation')
            cropped=slice(grid.support_guard_bins,grid.support_guard_bins+grid.score_bin_count)
            score_mask=np.ascontiguousarray(mask[:,cropped]); arrays={w:np.ascontiguousarray(v[:,cropped]) for w,v in support.items()}
            accumulator=make_accumulator(cfg,kind,template,shifts)
            finite=0; maximum=-np.inf
            for wi,width in enumerate(cfg['widths']):
                vectors=arrays[width]
                for subset in core.M37_ACTIVITY_SUBSETS:
                    score=core.stack_hypothesis(vectors,subset,minimum_active_epoch_snr=3.,stack_statistic='sum',exclusion_mask=score_mask)
                    expected=masked_stack_reference(vectors,subset,score_mask)
                    equal(score,expected,'masked real stack')
                    maximum=max(maximum,float(expected.max()));finite+=int(np.isfinite(score).sum())
                core.update_calibration(accumulator,vectors,template_index=0,width_index=wi,exclusion_mask=score_mask)
            null=scramble_reference(arrays,score_mask,shifts)
            equal(accumulator.null_maxima,null,'scramble sign, domain, masks and all subset/width maxima')
            if accumulator.observed_maximum!=maximum:raise RuntimeError('observed maximum mismatch')
            # No threshold or p-value is generated; nulls can legitimately be empty.
            expected_cells=len(cfg['widths'])*len(core.M37_ACTIVITY_SUBSETS)*grid.score_bin_count
            if accumulator.observed_score_cells!=expected_cells or accumulator.null_score_cells!=expected_cells*len(shifts):
                raise RuntimeError('scramble or observed inventory incomplete')
            if len(accumulator._visited_hypothesis_keys)!=32:raise RuntimeError('hypothesis inventory incomplete')
            checks.append({'template_index':template,'mask_sha256':transfer.array_hash(mask),
                'mask_bits_compared':int(mask.size),'masked_score_cells':expected_cells,'finite_masked_scores':finite,
                'scrambled_score_cells':expected_cells*len(shifts),'null_maxima':[None if not np.isfinite(x) else float(x) for x in null],
                'observed_maximum':None if not np.isfinite(maximum) else maximum,'reference_exact':True})
            write_sealed(OUT/f'{kind}.logic.json',{'milestone':'M43P','kind':kind,'freeze_commit':freeze,
                'config_sha256':sha(CONFIG),'input_array_hashes':fingerprints,'checks':checks,'complete':len(checks)==cfg['anchor_templates']})
            print(f'{kind} template {template}: masks, masked stacks and four scrambles exact ({len(checks)}/{cfg["anchor_templates"]})',flush=True)
            del support,arrays,mask,score_mask,accumulator


def run(work,source_root,freeze):
    cfg=frozen(freeze);started=time.monotonic();OUT.mkdir(exist_ok=True);work.mkdir(exist_ok=False)
    def phase(jobs,workers):
        def child(args):
            if (work/'abort').exists():raise RuntimeError('peer failure')
            command=[sys.executable,__file__,'--freeze-commit',freeze,'--work-root',str(work),'--source-root',str(source_root),*args]
            result=subprocess.run(command)
            if result.returncode:
                (work/'abort').touch();raise RuntimeError('child failed: '+' '.join(args))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending=[pool.submit(child,args) for args in jobs]
            for task in as_completed(pending):task.result()
    try:
        phase([['--kind',kind,'--width',str(w)] for w in reversed(cfg['widths']) for kind in ('on','off')],cfg['source_workers'])
        phase([['--kind',kind,'--logic'] for kind in ('on','off')],cfg['logic_workers'])
        products=[read_sealed(OUT/f'{kind}.width{w:03d}.json') for kind in ('on','off') for w in cfg['widths']]
        logic=[read_sealed(OUT/f'{kind}.logic.json') for kind in ('on','off')]
        if not all(x['complete'] for x in products+logic):raise RuntimeError('incomplete qualification')
        checks=[x for p in logic for x in p['checks']]
        result={'milestone':'M43P','status':'combined-component-controls-qualified','freeze_commit':freeze,
            'config_sha256':sha(CONFIG),'wall_seconds':round(time.monotonic()-started,3),
            'source_product_sha256s':[p['result_sha256'] for p in products],
            'logic_product_sha256s':[p['result_sha256'] for p in logic],
            'summary':{'source_width_products':len(products)*3,'anchor_templates_per_kind':cfg['anchor_templates'],
                'full_support_epoch_cells_replayed':cfg['anchor_templates']*6*len(cfg['widths'])*cfg['support_carriers'],
                'all_bank_sparse_cells':sum(s['sparse_cells'] for p in products for s in p['sources']),
                'mask_bits_compared':sum(x['mask_bits_compared'] for x in checks),
                'masked_stack_cells_compared':sum(x['masked_score_cells'] for x in checks),
                'scrambled_stack_cells_compared_through_maxima':sum(x['scrambled_score_cells'] for x in checks),
                'paired_off_decisions_compared':sum(v['cells_compared'] for p in products for v in p['paired_off_checks'])},
            'telescope_requests':0,'new_threshold_calibrated':False,'measured_native_injection_recovery':False,
            'full_bank_masks_qualified':False,'complete_candidate_pipeline_qualified':False,
            'scope':'One window; 37 full-support template anchors and all-bank sparse diagnostics; inherited synthetic event/OFF tests are separate.'}
        write_sealed(OUT/'qualification.json',result);print(json.dumps(result['summary'],indent=2),flush=True)
    except BaseException as error:
        (work/'abort').touch()
        write_sealed(OUT/'failure.json',{'milestone':'M43P','freeze_commit':freeze,'error':repr(error),'complete':False})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True)
    p.add_argument('--work-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--kind',choices=['on','off']);p.add_argument('--width',type=int);p.add_argument('--logic',action='store_true')
    a=p.parse_args()
    if a.logic:logic_job(a.kind,a.work_root,a.freeze_commit)
    elif a.kind:source_job(a.kind,a.width,a.work_root,a.source_root,a.freeze_commit)
    else:run(a.work_root,a.source_root,a.freeze_commit)
