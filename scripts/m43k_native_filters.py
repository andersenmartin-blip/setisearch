#!/usr/bin/env python3
"""M43K exhaustive native-filter oracle; retained M43I telescope arithmetic."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from m43f_source_cache_preflight import build_context
from m43e_economical_bank import read_sealed, write_sealed
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43k_native_filters'


def audit_native_values(normalized,filtered,width,*,chunk_centers):
    """Compare every valid center, using materialized indexed windows, row-wise.

    No sliding-window view, production filtering, cumulative sum or convolution
    is used by this oracle. It shares the frozen float32 reduction and sqrt rule.
    This pure numerical helper makes no source provenance claim.
    """
    transfer.integer(width,'width');transfer.integer(chunk_centers,'reference chunk')
    if width not in core.M37_SPECTRAL_WIDTHS:raise ValueError('unsupported width')
    if (normalized.dtype!=np.dtype('<f4') or normalized.ndim!=2
            or filtered.dtype!=np.dtype('<f4') or not normalized.flags.c_contiguous
            or not filtered.flags.c_contiguous):raise ValueError('native array dtype/layout differs')
    rows,n=normalized.shape;half=width//2;valid=n-2*half
    if rows<1 or valid<1 or filtered.shape!=(rows,valid):raise ValueError('native filter shape differs')
    offsets=np.arange(-half,half+1,dtype=np.int64);records=[]
    for row in range(rows):
        h=hashlib.sha256();checked=0
        for start in range(0,valid,chunk_centers):
            stop=min(start+chunk_centers,valid)
            centers=np.arange(start+half,stop+half,dtype=np.int64)
            windows=normalized[row,centers[:,None]+offsets[None,:]]
            reference=(np.sum(windows,axis=1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
            if not np.isfinite(reference).all() or not np.array_equal(filtered[row,start:stop],reference):
                raise RuntimeError(f'native filter mismatch: width {width}, row {row}, centers {start+half}:{stop+half}')
            h.update(memoryview(reference).cast('B'));checked+=len(reference)
        actual_hash=transfer.array_hash(filtered[row])
        if checked!=valid or h.hexdigest()!=actual_hash:raise RuntimeError('native row inventory/hash differs')
        records.append({'row':row,'native_center_start':half,'native_center_stop':n-half,
            'values_compared':checked,'reference_sha256':h.hexdigest(),
            'cache_row_sha256':actual_hash,'exact':True})
    return records


def bank_coverage(geometry,factors,grid,width):
    """Endpoint bound for positive factors on a strictly increasing q lattice.

    Binary64 multiplication, subtraction, positive division and nearest-even
    rounding are nondecreasing here. Thus endpoint bounds cover every interior
    mapping as well, including repeats. This is a bound, not a score evaluation.
    """
    transfer.integer(width,'width')
    if width not in core.M37_SPECTRAL_WIDTHS:raise ValueError('unsupported width')
    f=np.asarray(factors)
    if f.dtype!=np.dtype('<f8') or f.ndim!=2 or not f.size or not np.isfinite(f).all() or np.any(f<=0) or np.any(f>=2):
        raise ValueError('positive finite binary64 factor matrix required')
    q=grid.support_hz
    if not np.isfinite(q).all() or not np.all(np.diff(q)>0) or geometry.channel_width_hz<=0:
        raise ValueError('monotonic finite frequency grid required')
    endpoints=np.rint((f[...,None]*q[[0,-1]]-geometry.raw_zero_hz)/geometry.channel_width_hz).astype(np.int64)
    low=int(endpoints.min());high=int(endpoints.max());half=width//2
    if low<half or high>=geometry.channel_count-half:raise core.V0P6CoverageError('bank extends beyond audited native centers')
    return {'template_integration_pairs':int(f.size),'minimum_mapped_center':low,
        'maximum_mapped_center':high,'audited_native_start':half,'audited_native_stop':geometry.channel_count-half,
        'all_bank_mappings_inside_audited_domain':True,'argument':'positive-factor monotonic endpoint bound'}


def run(work_root,freeze_commit):
    path=ROOT/'config/m43k_native_filters.json';cfg=json.loads(path.read_text())
    config_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    for name,h in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=h:raise RuntimeError('frozen input changed: '+name)
    if subprocess.check_output(['git','show',freeze_commit+':config/m43k_native_filters.json'],cwd=ROOT)!=path.read_bytes():
        raise RuntimeError('configuration differs from public freeze')
    if cfg['numpy_version']!=np.__version__:raise RuntimeError('NumPy differs')
    prior=read_sealed(ROOT/'results_m43i_telescope_transfer/qualification.json')
    exhaustive=read_sealed(ROOT/'results_m43j_exhaustive_anchors/qualification.json')
    if prior['result_sha256']!=cfg['m43i_result_sha256'] or exhaustive['result_sha256']!=cfg['m43j_result_sha256']:
        raise RuntimeError('ancestor result differs')
    _,_,_,_,basis,bank,table,_=build_context()
    if table.template_bank_sha256!=cfg['bank_sha256'] or table.factor_table_sha256!=cfg['factor_table_sha256']:
        raise RuntimeError('bank or factors differ')
    grid=core.make_m37_proxy_carrier_grid(cfg['window'])
    if core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256']:raise RuntimeError('grid differs')
    OUT.mkdir(exist_ok=True);checks=[];sources=[];started=time.monotonic()
    for anchor in cfg['anchors']:
        label=anchor['scan'];matrix=core.factor_table_for_scan(table,basis,label)
        if core.factor_table_sha256(matrix)!=anchor['scan_factor_sha256']:raise RuntimeError('scan factors differ')
        src=transfer.load_telescope_source(Path(work_root)/label/cfg['window'],trusted_receipt_sha256=anchor['source_receipt_sha256'])
        old_src=next(s for s in prior['sources'] if s['scan']==label)
        if src.identity!=old_src['source_identity']:raise RuntimeError('M43I source identity differs')
        sources.append({'scan':label,'source_identity':src.identity,'receipt_sha256':src.trusted_receipt_sha256,
            'native_channels':src.geometry.channel_count,'integration_rows':src.integration_count})
        for width in cfg['widths']:
            cache=transfer.build_telescope_cache(src,matrix,grid,width,bank_sha256=table.template_bank_sha256)
            old=next(c for c in prior['checks'] if c['scan']==label and c['width']==width)
            if cache.identity!=old['cache_identity'] or cache.payload_sha256!=old['cache_payload_sha256']:
                raise RuntimeError('M43I native cache differs')
            rows=audit_native_values(src.values,cache.values,width,chunk_centers=cfg['reference_chunk_centers'])
            coverage=bank_coverage(src.geometry,matrix,grid,width)
            local=[]
            for a,b in anchor['local_ranges']:
                local.append(transfer.gather_bank_slice(cache,a,b,chunk_bins=7))
            local_hash=transfer.array_hash(np.concatenate(local,axis=1))
            if local_hash!=old['local_score_sha256']:raise RuntimeError('M43I local integrated scores differ')
            record={'scan':label,'width':width,'source_identity':src.identity,'cache_identity':cache.identity,
                'cache_payload_sha256':cache.payload_sha256,'native_rows':rows,
                'native_values_compared':sum(r['values_compared'] for r in rows),'bank_coverage':coverage,
                'm43i_cache_identity_exact':True,'m43i_local_scores_exact':True,'local_score_sha256':local_hash,
                'local_integrated_cells':len(matrix)*sum(b-a for a,b in anchor['local_ranges'])}
            checks.append(record)
            write_sealed(OUT/f'{label}.width{width:03d}.json',{'milestone':'M43K','freeze_commit':freeze_commit,
                'config_sha256':config_sha,'check':record})
            print(f'{label} width {width}: all {record["native_values_compared"]} native values exact; {time.monotonic()-started:.1f}s',flush=True)
            del cache,local
        del src
    result=write_sealed(OUT/'qualification.json',{'milestone':'M43K','status':'all-wider-native-filter-values-qualified',
        'freeze_commit':freeze_commit,'config_sha256':config_sha,'bank_sha256':table.template_bank_sha256,
        'factor_table_sha256':table.factor_table_sha256,'grid_sha256':cfg['grid_sha256'],'numpy_version':np.__version__,
        'm43i_result_sha256':prior['result_sha256'],'m43j_result_sha256':exhaustive['result_sha256'],
        'sources':sources,'checks':checks,'summary':{'sources':len(sources),'widths':cfg['widths'],
            'source_width_checks':len(checks),'native_row_width_checks':sum(len(c['native_rows']) for c in checks),
            'native_values_compared':sum(c['native_values_compared'] for c in checks),
            'local_integrated_cells_reproduced':sum(c['local_integrated_cells'] for c in checks)},
        'new_remote_requests':0,'all_widths_full_bank_integrated_scores_evaluated':False,
        'candidate_selection_performed':False,'detection_threshold_calibrated':False,
        'multi_epoch_real_stack_qualified':False,'recovery_measured':False,
        'elapsed_seconds':round(time.monotonic()-started,3)})
    print(json.dumps({'result_sha256':result['result_sha256'],'summary':result['summary']},indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',type=Path,required=True);p.add_argument('--freeze-commit',required=True)
    args=p.parse_args();run(args.work_root,args.freeze_commit)
