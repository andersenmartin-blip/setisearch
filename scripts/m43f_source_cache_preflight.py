#!/usr/bin/env python3
"""M43F metadata-only native coverage and channel-mapping compatibility gate."""
import hashlib
import json
from pathlib import Path
import numpy as np
from m43b_active_support import ROOT, seal
from m43d_bank_coverage import nested_banks
from m43e_economical_bank import checkerboard_bank, read_sealed, write_sealed
from seti_repeater import search_v0p6 as core
from seti_repeater import source_v0p6 as source

OUT = ROOT/'results_m43f_source_cache_preflight'
ROUNDING_RESERVE_CHANNELS = 2


def endpoint_coverage(geometry, factors, grid, width):
    factors=np.asarray(factors,dtype='<f8')
    if factors.ndim!=2 or not factors.size or not np.isfinite(factors).all() or np.any(factors<=0):
        raise ValueError('finite positive factor table required')
    if type(width) is not int or width<1 or width%2!=1:
        raise ValueError('positive odd width required')
    endpoints=np.stack((grid.support_hz[0]*factors,grid.support_hz[-1]*factors),axis=-1)
    indices=core.nearest_native_indices(geometry,endpoints)
    half=width//2
    lo=indices[:,:,0];hi=indices[:,:,1]
    failed=(lo<half)|(hi>=geometry.channel_count-half)
    per_template=np.any(failed,axis=1)
    minimum=int(lo.min());maximum=int(hi.max())
    return {'raw_center_start':minimum,'raw_center_stop':maximum+1,
            'lower_headroom_channels':minimum-half,
            'upper_headroom_channels':geometry.channel_count-1-maximum-half,
            'uncovered_templates':int(per_template.sum()),
            'uncovered_template_integration_rows':int(failed.sum()),
            'uncovered_template_indices_sha256':hashlib.sha256(np.flatnonzero(per_template).astype('<i8').tobytes()).hexdigest(),
            'endpoint_indices_sha256':hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest(),
            'all_covered':not bool(failed.any()),
            'filter_radius_channels':half}


def enlarged_interval(old_interval, coverage, remote_channel_count):
    """Descending archive-axis proposal; keep old extraction and guard both ends."""
    start,stop=map(int,old_interval)
    if start<0 or stop<=start or stop>remote_channel_count:
        raise ValueError('invalid old extraction')
    half=coverage['filter_radius_channels']
    low=coverage['raw_center_start']-half-ROUNDING_RESERVE_CHANNELS
    high=coverage['raw_center_stop']-1+half+ROUNDING_RESERVE_CHANNELS
    needed_start=stop-1-high
    needed_stop=stop-low
    proposal=(min(start,needed_start),max(stop,needed_stop))
    if proposal[0]<0 or proposal[1]>remote_channel_count:
        raise ValueError('proposed extraction exceeds telescope band')
    return proposal


def duplicate_witness(geometry, factors, grid):
    """Exhaust one predeclared minimum-factor row; never infer exact duplicates."""
    location=np.unravel_index(np.argmin(factors),factors.shape)
    value=float(factors[location])
    indices=core.nearest_native_indices(geometry,grid.support_hz*value)
    steps=np.diff(indices)
    counts={str(int(step)):int(np.count_nonzero(steps==step)) for step in np.unique(steps)}
    duplicate=np.flatnonzero(steps==0)
    witness=None
    if duplicate.size:
        i=int(duplicate[0])
        witness={'support_indices':[i,i+1],'proxy_carriers_hz':[float(grid.support_hz[i]),float(grid.support_hz[i+1])],
                 'mapped_native_indices':[int(indices[i]),int(indices[i+1])]}
    return {'template_index':int(location[0]),'integration_index':int(location[1]),'factor':value,
            'step_counts':counts,'duplicate_pairs':int(duplicate.size),'first_duplicate':witness,
            'mapping_sha256':hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest(),
            'mapping_injective':bool(np.all(steps>0))}


def resource_estimate(channel_count,integration_count):
    raw=channel_count*integration_count*4
    frequency=channel_count*8
    product=2*raw+frequency
    return {'native_channels':int(channel_count),'raw_bytes':int(raw),'normalized_bytes':int(raw),
            'frequency_bytes':int(frequency),'raw_normalized_frequency_bytes':int(product),
            'legacy_source_channel_cap_passed':channel_count<=source.M37_MAXIMUM_SOURCE_NATIVE_CHANNELS,
            'legacy_raw_byte_cap_passed':raw<=source.M37_MAXIMUM_SOURCE_RAW_NBYTES,
            'legacy_frequency_byte_cap_passed':frequency<=source.M37_MAXIMUM_SOURCE_FREQUENCY_NBYTES,
            'legacy_product_array_cap_passed':product<=source.M37_MAXIMUM_NORMALIZED_PRODUCT_ARRAY_NBYTES}


def build_context():
    cfgpath=ROOT/'config/m43f_source_cache_preflight.json'
    cfg=json.loads(cfgpath.read_text())
    for path,digest in cfg['pinned_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('changed frozen file: '+path)
    confirmed=read_sealed(ROOT/'results_m43e_economical_bank/confirmation.json.gz')
    if confirmed['selected_bank']!='checker32' or confirmed['selected_bank_gate_passed'] is not True:
        raise RuntimeError('M43E qualification differs')
    metadata=json.loads((ROOT/'config/hd156668b_m37_preflight.json').read_text())
    source.validate_m37_source_scan_definitions(metadata['scans'])
    basis=core.make_factor_basis_from_metadata(metadata)
    bank_result=json.loads((ROOT/'results_m37_v0p6_bank_preflight/bank_preflight.json').read_text())
    original=bank_result['template_bank']['records']
    bank,_=checkerboard_bank(nested_banks(original)['disk32'])
    bank_digest=core.template_bank_sha256(bank)
    if len(bank)!=1701 or bank_digest!=confirmed['bank_inventory']['checker32']['bank_sha256']:
        raise RuntimeError('fixed M43E bank differs')
    table=core.make_template_factor_table(basis,bank,expected_template_bank_sha256=bank_digest)
    if basis.basis_sha256!=confirmed['factor_basis_sha256']:
        raise RuntimeError('basis changed')
    return cfgpath,cfg,confirmed,metadata,basis,bank,table,bank_result


def run():
    cfgpath,cfg,confirmed,metadata,basis,bank,table,legacy=build_context()
    cfg_hash=hashlib.sha256(cfgpath.read_bytes()).hexdigest()
    matrices={s['label']:core.factor_table_for_scan(table,basis,s['label']) for s in metadata['scans']}
    legacy_records={(r['window_id'],r['scan_label']):r for r in legacy['extraction_coverage']['records']}
    OUT.mkdir(exist_ok=True)
    rows=[];windows=[]
    for window_id in core.M37_WINDOW_IDS:
        grid=core.make_m37_proxy_carrier_grid(window_id)
        old_interval=source.m37_extraction_interval(window_id)
        proposed=[];window_rows=[]
        for scan in metadata['scans']:
            label=scan['label'];header=scan['expected_header']
            if float(header['foff_mhz'])>=0:raise RuntimeError('descending archive convention changed')
            geometry=core.native_geometry_from_extraction(fch1_mhz=header['fch1_mhz'],foff_mhz=header['foff_mhz'],
                                                        channel_start=old_interval[0],channel_stop=old_interval[1])
            matrix=matrices[label]
            old=endpoint_coverage(geometry,matrix[:93],grid,129)
            expected=legacy_records[(window_id,label)]
            if (old['lower_headroom_channels']!=expected['proxy_lower_headroom_channels']-64
                    or old['upper_headroom_channels']!=expected['proxy_upper_headroom_channels']-64
                    or not old['all_covered']):
                raise RuntimeError('M37 baseline coverage differs')
            coverage={str(width):endpoint_coverage(geometry,matrix,grid,width) for width in core.M37_SPECTRAL_WIDTHS}
            interval=enlarged_interval(old_interval,coverage['129'],int(header['dataset_shape'][2]))
            proposed.append(interval)
            bad=(matrix<1.)|(matrix>=2.)
            witness=duplicate_witness(geometry,matrix,grid)
            row={'window_id':window_id,'scan_label':label,'scan_kind':scan['kind'],
                 'old_extraction_interval':list(old_interval),'old_native_channels':geometry.channel_count,
                 'factor_min':float(matrix.min()),'factor_max':float(matrix.max()),
                 'legacy_factor_range_violating_rows':int(bad.sum()),
                 'legacy_factor_range_violating_templates':int(np.any(bad,axis=1).sum()),
                 'legacy_cache_factor_precondition_passed':not bool(bad.any()),
                 'm37_baseline_coverage_exact':True,'baseline_width129_coverage':old,
                 'width_coverage':coverage,'minimum_factor_mapping':witness,
                 'needed_interval_with_two_channel_reserve':list(interval)}
            window_rows.append(row)
        # One common interval per window across all six scans, including OFF.
        interval=(min(p[0] for p in proposed),max(p[1] for p in proposed))
        count=interval[1]-interval[0]
        for row,scan in zip(window_rows,metadata['scans'],strict=True):
            header=scan['expected_header']
            geometry=core.native_geometry_from_extraction(fch1_mhz=header['fch1_mhz'],foff_mhz=header['foff_mhz'],
                                                        channel_start=interval[0],channel_stop=interval[1])
            proposal_check=endpoint_coverage(geometry,matrices[row['scan_label']],grid,129)
            if not proposal_check['all_covered']:
                raise RuntimeError('proposed source coverage failed direct recheck')
            row['proposed_width129_coverage']=proposal_check
            row['proposed_raw_center_span_channels']=proposal_check['raw_center_stop']-proposal_check['raw_center_start']
            payload=row['proposed_raw_center_span_channels']*int(header['dataset_shape'][0])*4
            row['estimated_cache_payload_bytes_per_width']=int(payload)
            row['estimated_cache_payload_bytes_all_eight_widths']=int(payload)*8
            row['row_sha256']=seal(row)
            rows.append(row)
        resources=resource_estimate(count,16)
        windows.append({'window_id':window_id,'old_interval':list(old_interval),'proposed_interval':list(interval),
                        'channels_added':count-(old_interval[1]-old_interval[0]),
                        'relative_source_channel_count':count/(old_interval[1]-old_interval[0]),
                        'normalization_origin_shift_channels':interval[1]-old_interval[1],
                        'normalization_block_offset_mod4096':(interval[1]-old_interval[1])%4096,
                        'resource_estimate_per_scan':resources,
                        'estimated_all_six_scans_cache_payload_bytes':sum(r['estimated_cache_payload_bytes_all_eight_widths'] for r in window_rows)})
        print('window preflight complete',window_id,flush=True)
    unique_factors=table.factors
    compatible=all(r['width_coverage']['129']['all_covered'] and r['legacy_cache_factor_precondition_passed'] for r in rows)
    result={'artifact_type':'m43f-native-coverage-and-mapping-preflight-v1',
            'status':'legacy-source-mapping-compatible' if compatible else 'legacy-source-mapping-incompatible',
            'config_sha256':cfg_hash,'m43e_confirmation_sha256':confirmed['result_sha256'],
            'bank_sha256':core.template_bank_sha256(bank),'template_count':1701,
            'factor_basis_sha256':basis.basis_sha256,'factor_table_sha256':table.factor_table_sha256,
            'factor_table_shape':list(table.factors.shape),
            'distinct_factor_rows_below_one':int(np.count_nonzero(unique_factors<1)),
            'distinct_factor_rows_ge_two':int(np.count_nonzero(unique_factors>=2)),
            'all_30_baseline_geometries_exact':len(rows)==30 and all(r['m37_baseline_coverage_exact'] for r in rows),
            'old_extraction_covered_scan_windows_width129':sum(r['width_coverage']['129']['all_covered'] for r in rows),
            'legacy_mapping_precondition_passed_scan_windows':sum(r['legacy_cache_factor_precondition_passed'] for r in rows),
            'minimum_factor_duplicate_witnesses':sum(r['minimum_factor_mapping']['first_duplicate'] is not None for r in rows),
            'all_proposed_intervals_rechecked':all(r['proposed_width129_coverage']['all_covered'] for r in rows),
            'rows':rows,'windows':windows,'legacy_compatible':compatible,
            'proposed_intervals_are_validated_source_products':False,
            'remote_telescope_requests':0,'new_spectral_reads':0,'cache_payloads_built':0,'new_injections':0,'new_scores':0,
            'production_detector_changed':False,'sensitivity_claimed':False}
    result=write_sealed(OUT/'preflight.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','windows')},indent=2),flush=True)


if __name__=='__main__':run()
