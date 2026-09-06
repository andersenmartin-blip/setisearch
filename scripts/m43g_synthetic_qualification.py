#!/usr/bin/env python3
"""Frozen M43G numerical transfer qualification. No telescope access."""
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
from m43f_source_cache_preflight import build_context
from m43e_economical_bank import read_sealed, write_sealed
from m43g_reference import sorted_reference, direct_reference
from seti_repeater import transfer_m43g as transfer
from seti_repeater import search_v0p6 as core

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43g_synthetic_transfer'


def synthetic_row(count, seed):
    rng = np.random.Generator(np.random.PCG64(seed))
    return np.ascontiguousarray(np.float32(10)+rng.standard_normal(count, dtype=np.float32))


def compare(a,b,label):
    if a.dtype!=b.dtype or a.shape!=b.shape or not np.array_equal(a,b):
        raise RuntimeError('qualification mismatch: '+label)


def reference_stack(vectors, subset):
    active = vectors[list(subset)]
    result = np.zeros(active.shape[1:], dtype=np.float32)
    for row in active:result += row
    result /= np.float32(np.sqrt(len(subset)))
    return np.where(np.all(active>=np.float32(3), axis=0), result, np.float32(-np.inf))


def run():
    config_path=ROOT/'config/m43g_synthetic_transfer.json'
    cfg=json.loads(config_path.read_text())
    for path,h in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:
            raise RuntimeError('frozen input changed: '+path)
    if np.__version__ != cfg['numpy_version']:
        raise RuntimeError('NumPy runtime differs from frozen qualification')
    _,_,confirmed,metadata,basis,bank,table,_=build_context()
    preflight=read_sealed(ROOT/'results_m43f_source_cache_preflight/preflight.json')
    if preflight['result_sha256']!=cfg['preflight_result_sha256']:
        raise RuntimeError('M43F identity differs')
    if table.factor_table_sha256!=cfg['factor_table_sha256']:
        raise RuntimeError('fixed factors differ')
    windows={w['window_id']:w for w in preflight['windows']}
    witnesses={(r['window_id'],r['scan_label']):r for r in preflight['rows']}
    normalization=[]; cache_rows=[]; full_rows=[]; stacks=[]
    for wi, window_id in enumerate(core.M37_WINDOW_IDS):
        grid=core.make_m37_proxy_carrier_grid(window_id)
        ranges=[(0,17),(grid.support_bin_count//2-8,grid.support_bin_count//2+9),
                (grid.support_bin_count-17,grid.support_bin_count)]
        local={width:{} for width in core.M37_SPECTRAL_WIDTHS}
        for si, scan in enumerate(metadata['scans']):
            label=scan['label']; header=scan['expected_header']
            interval=windows[window_id]['proposed_interval']
            geometry=core.native_geometry_from_extraction(fch1_mhz=header['fch1_mhz'],foff_mhz=header['foff_mhz'],channel_start=interval[0],channel_stop=interval[1])
            matrix=core.factor_table_for_scan(table,basis,label)
            seed=cfg['seed']+wi*10000+si*100
            def reader(row):return synthetic_row(geometry.channel_count,seed+row)[::-1]
            scope={'kind':'synthetic','window':window_id,'scan':label,'seed':seed,
                   'archive_interval':interval,'m43f_result':preflight['result_sha256']}
            src=transfer.normalize_synthetic_rows(reader,geometry,matrix.shape[1],input_orientation='descending',scope=scope)
            for row in range(matrix.shape[1]):
                raw=synthetic_row(geometry.channel_count,seed+row).reshape(1,-1)
                ref=sorted_reference(raw)
                compare(src.values[row:row+1],ref,'sort normalization')
            del raw,ref
            normalization.append({'window':window_id,'scan':label,'source_identity':src.identity,
                'raw_sha256':src.raw_sha256,'normalized_sha256':src.normalized_sha256,
                'row_count':matrix.shape[1],'native_channels':geometry.channel_count,
                'adapter_ndarray_bound_bytes':transfer.memory_bound(matrix.shape[1],geometry.channel_count)})
            first=witnesses[(window_id,label)]['minimum_factor_mapping']['first_duplicate']['support_indices'][0]
            witness_range=(first,first+2)
            minimum=int(np.unravel_index(matrix.argmin(),matrix.shape)[0])
            maximum=int(np.unravel_index(matrix.argmax(),matrix.shape)[0])
            chosen=sorted(set((minimum,maximum)))
            for width in core.M37_SPECTRAL_WIDTHS:
                cache=transfer.build_synthetic_cache(src,matrix,grid,width,bank_sha256=table.template_bank_sha256)
                outputs=[]
                for start,stop in ranges+[witness_range]:
                    actual=transfer.gather_bank_slice(cache,start,stop,chunk_bins=cfg['local_chunk_bins'])
                    reference=direct_reference(src.values,geometry,matrix,grid,width,start,stop)
                    compare(actual,reference,'whole-bank local native-window oracle')
                    outputs.append(actual)
                local[width][label]=np.concatenate(outputs[:3],axis=1)
                cache_rows.append({'window':window_id,'scan':label,'width':width,'cache_identity':cache.identity,
                    'cache_payload_sha256':cache.payload_sha256,'templates':matrix.shape[0],
                    'local_carrier_cells_per_template':sum(b-a for a,b in ranges+[witness_range]),
                    'local_scores_sha256':transfer.array_hash(np.concatenate(outputs,axis=1)),
                    'native_window_reference_exact':True})
                if window_id==cfg['full_grid_window'] and width in cfg['full_grid_widths']:
                    actual=transfer.gather_bank_slice(cache,0,grid.support_bin_count,template_indices=chosen,chunk_bins=cfg['full_chunk_bins'][0])
                    alternate=transfer.gather_bank_slice(cache,0,grid.support_bin_count,template_indices=chosen,chunk_bins=cfg['full_chunk_bins'][1])
                    compare(actual,alternate,'full-grid chunk invariance')
                    del alternate
                    for start in range(0,grid.support_bin_count,cfg['reference_chunk_bins']):
                        stop=min(start+cfg['reference_chunk_bins'],grid.support_bin_count)
                        reference=direct_reference(src.values,geometry,matrix[chosen],grid,width,start,stop)
                        compare(actual[:,start:stop],reference,'full-grid native-window oracle')
                    for j,(start,stop) in enumerate(ranges):
                        compare(actual[:,start:stop],outputs[j][chosen],'local/full agreement')
                    full_rows.append({'window':window_id,'scan':label,'width':width,'template_indices':chosen,
                        'carrier_cells_per_template':grid.support_bin_count,'score_sha256':transfer.array_hash(actual),
                        'chunk_invariance_exact':True,'native_window_reference_exact':True,'local_full_agreement_exact':True})
                    del actual,reference
                del cache,outputs
            print(window_id+' '+label+' complete',flush=True)
            del src
        for width in core.M37_SPECTRAL_WIDTHS:
            for kind in ('on','off'):
                labels=[s['label'] for s in metadata['scans'] if s['kind'].lower()==kind]
                vectors=np.stack([local[width][label] for label in labels],axis=0)
                for subset in core.M37_ACTIVITY_SUBSETS:
                    # Flatten bank and diagnostic carrier cells; never mix epochs.
                    v=vectors.reshape(3,-1)
                    actual=core.stack_hypothesis(v,subset,minimum_active_epoch_snr=3.,stack_statistic='sum')
                    expected=reference_stack(v,subset)
                    compare(actual,expected,'epoch stack arithmetic and active cut')
                    stacks.append({'window':window_id,'width':width,'kind':kind,'subset':list(subset),
                        'cells':actual.size,'finite_cells':int(np.isfinite(actual).sum()),
                        'score_sha256':transfer.array_hash(actual),'reference_exact':True})
        del local
    result={'milestone':'M43G','status':'synthetic-numerical-transfer-qualified',
            'contract_sha256':transfer.CONTRACT_SHA256,'config_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),
            'm43f_result_sha256':preflight['result_sha256'],'bank_sha256':table.template_bank_sha256,
            'factor_table_sha256':table.factor_table_sha256,'numpy_version':np.__version__,
            'normalization':normalization,'cache_checks':cache_rows,'full_grid_checks':full_rows,'stack_checks':stacks,
            'summary':{'synthetic_scan_window_sources':len(normalization),
                'normalization_rows_sort_checked':sum(r['row_count'] for r in normalization),
                'bank_scan_width_local_checks':len(cache_rows),
                'local_score_cells_compared':sum(r['templates']*r['local_carrier_cells_per_template'] for r in cache_rows),
                'full_grid_template_vectors':sum(len(r['template_indices']) for r in full_rows),
                'full_grid_score_cells_compared':sum(len(r['template_indices'])*r['carrier_cells_per_template'] for r in full_rows),
                'stack_vectors_checked':len(stacks),'stack_cells_compared':sum(r['cells'] for r in stacks)},
            'telescope_requests':0,'telescope_spectral_reads':0,'detection_threshold_calibrated':False,
            'production_source_attested':False,'measured_recovery':False}
    OUT.mkdir(exist_ok=True)
    write_sealed(OUT/'qualification.json',result)
    print(json.dumps(result['summary'],indent=2),flush=True)


if __name__=='__main__':run()
