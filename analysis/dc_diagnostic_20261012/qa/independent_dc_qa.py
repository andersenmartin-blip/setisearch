#!/usr/bin/env python3
"""Independent frozen DC cell attribution, patches and stored-ranking QA.

No detector import/search, no telescope requests. Rebuilds local501 medians via
NumPy independently, conditional on authenticated saved fullcore normalization.
No execution of scientific arrays without explicit separately pinned root GO.
"""
from __future__ import annotations
import argparse,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
BASE=Path(__file__).resolve().parent
WORKSPACE=BASE.parent.parent
SOURCE=WORKSPACE/'seti_previous'
CHUNK=1048576
DC=[n*CHUNK+CHUNK//2 for n in (170,171,172)]
FCH1=2802832031.25; DF=-2.7939677238464355; TSAMP=18.253611008
SCANS=['epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off']
CONTEXTS={'central':'analysis/s2017_control_targets_20261011_v2/results/context/CONTEXT_PROFILES.json',
          'adjacent':'analysis/off_adjacent_20261011_context/results/CONTEXT_PROFILES.json'}
ATOL=1e-7; RTOL=1e-10
CAP_CPU=600;CAP_WALL=900;CAP_RAM=2*1024**3

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def pin(p):
    p=p.resolve()
    return {'path':p.relative_to(WORKSPACE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}
def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('Duplicate JSON key '+k)
        d[k]=v
    return d
def read(p):
    return json.loads(p.read_bytes(),object_pairs_hook=unique,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
def require(v,message):
    if not v:raise ValueError(message)
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def bounded_path(p,root):
    p=(root/p).resolve();require(p.is_relative_to(root.resolve()),'Unconfined input path');return p

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--scope',type=Path,default=BASE/'scope.json')
    parser.add_argument('--go',type=Path)
    args=parser.parse_args()
    if args.check_only:
        print(json.dumps({'status':'PREPARED_METADATA_ONLY_NO_ARRAYS_READ','qa_sha256':sha(Path(__file__)),
                          'derived_DC_channels':DC,'no_detector_import':True}));return
    require(args.go is not None,'Separate root GO required')
    scope=read(args.scope);go=read(args.go)
    require(go['authorized'] is True and go['scope_sha256']==sha(args.scope)
            and go['producer_sha256']==sha(Path(__file__)),'Exact root GO/source/scope pin required')
    require(scope['CPU_seconds']==CAP_CPU and scope['wall_seconds']==CAP_WALL
            and scope['RAM_bytes']==CAP_RAM,'Frozen QA resource limits differ')
    require(not (BASE/'QA_RECEIPT.json').exists(),'QA not overwriteable')
    def deadline(a,b):raise TimeoutError('QA resource cap')
    signal.signal(signal.SIGALRM,deadline);signal.signal(signal.SIGXCPU,deadline)
    resource.setrlimit(resource.RLIMIT_CPU,(CAP_CPU,CAP_CPU+1))
    resource.setrlimit(resource.RLIMIT_AS,(CAP_RAM,CAP_RAM));signal.alarm(CAP_WALL)
    started=time.monotonic();cpu=time.process_time();pins={};counts={};comparisons=[];mismatches=[]
    global np
    import numpy as np
    def checked(p,declared=None):
        actual=pin(p)
        if declared is not None:
            require(actual['bytes']==declared['bytes'] and actual['sha256']==declared['sha256'],
                    'Input pin differs: '+str(p))
        require(str(p) not in pins or pins[str(p)]==actual,'Repeated input changed')
        pins[str(p)]=actual;return p
    for d in scope['input_pins']:checked(bounded_path(d['path'],WORKSPACE),d)
    checked(Path(__file__));checked(args.scope);checked(args.go)
    def equal(a,b,label):
        aa=np.asarray(a);bb=np.asarray(b)
        ok=aa.shape==bb.shape and np.array_equal(aa,bb)
        if 'duplicate_rawcell' not in label or not ok:comparisons.append({'check':label,'ok':bool(ok)})
        if not ok:mismatches.append(label)
        return ok
    def near(a,b,label):
        aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float)
        ok=aa.shape==bb.shape and np.isfinite(aa).all() and np.isfinite(bb).all() and np.allclose(aa,bb,atol=ATOL,rtol=RTOL)
        delta=float(np.max(np.abs(aa-bb))) if aa.shape==bb.shape and aa.size else None
        comparisons.append({'check':label,'ok':bool(ok),'max_absolute_difference':delta})
        if not ok:mismatches.append(label)
        return ok
    headers_path=checked(SOURCE/'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json')
    headers={i['label']:i['current_header']['data_attributes'] for i in read(headers_path)['sources']}
    profiles=[];capsules=[];physical_bits={};raw_instances=0;duplicate_instances=0
    for phase,relative in CONTEXTS.items():
        matrix_path=checked(SOURCE/relative);matrix=read(matrix_path)
        require(len(matrix['profiles'])==54 and len(matrix['selected_tracks'])==9,'Frozen54x9 contexts required')
        for p in matrix['profiles']:
            prefix=phase+'/'+p['profile_id'];track=p['selected_track'];scan=p['context_scan_id'];width=track['width_channels']
            require(width in (1,3),'Invalid box width')
            cap_decl=p['raw_capsule'];norm_decl=p['normalization']
            root=matrix_path.parent if phase=='central' else SOURCE
            cap_path=checked(bounded_path(cap_decl['path'],root),cap_decl)
            norm_path=checked(bounded_path(norm_decl['path'],root),norm_decl)
            normal=read(norm_path)
            for k in ('row_power_median','row_winsorized_residual_location','row_residual_MAD_scale'):
                a=np.asarray(normal[k]);require(a.shape==(16,) and np.isfinite(a).all(),'Invalid saved full16 normalization')
            require(np.all(np.asarray(normal['row_power_median'])>0) and np.all(np.asarray(normal['row_residual_MAD_scale'])>0),
                    'Saved normalization denominator not positive')
            with np.load(cap_path,allow_pickle=False) as v:cap={k:v[k].copy() for k in v.files}
            raw=cap['raw_power'];require(raw.shape==(16,503) and raw.dtype==np.dtype('<f4'),'Raw503 schema differs')
            require(np.isfinite(raw).all() and (raw>=0).all(),'Raw503 has invalid power')
            elapsed=(headers[scan]['tstart']-headers[track['scan_id']]['tstart'])*86400+np.arange(16)*TSAMP
            centers=np.rint((track['frequency_hz_at_own_first_midpoint']-FCH1)/DF+track['drift_hz_s']*elapsed/DF).astype(np.int64)
            equal(centers,p['rounded_absolute_centers'],prefix+'/saved_matrix_centers')
            equal(centers,cap['rounded_absolute_centers'],prefix+'/saved_capsule_centers')
            equal(elapsed,p['times_from_primary_reference_s'],prefix+'/matrix_elapsed')
            if 'times_from_primary_reference_s' in cap:equal(elapsed,cap['times_from_primary_reference_s'],prefix+'/capsule_elapsed')
            offsets=np.array([-1,0,1]) if width==3 else np.array([0])
            cols=251+offsets
            ratio=raw.astype(np.float64)/np.asarray(normal['row_power_median'])[:,None]
            med=np.empty((16,width),dtype=np.float64)
            for r in range(16):
                for j,c in enumerate(cols):med[r,j]=np.median(ratio[r,c-250:c+251])
            cells=(ratio[:,cols]-med-np.asarray(normal['row_winsorized_residual_location'])[:,None])/np.asarray(normal['row_residual_MAD_scale'])[:,None]
            denom=float(np.sqrt(16*width));cell_score=cells/denom;row=cells.sum(axis=1);full=float(cell_score.sum())
            near(row,p['row_standardized_box_sum'],prefix+'/saved_matrix_row_standardized')
            near(row,cap['row_standardized_box_sum'],prefix+'/saved_capsule_row_standardized')
            old=p.get('fixed_robust_box_track_score',p.get('direct_fixed_robust_box_track_score'))
            near(full,old,prefix+'/saved_original_score')
            if 'row_score_contribution' in cap:near(row/denom,cap['row_score_contribution'],prefix+'/saved_capsule_row_score')
            source_cell_channels=centers[:,None]+offsets[None,:]
            exact=np.isin(source_cell_channels,DC)
            contribution=np.where(exact,cell_score,0.).sum(axis=1)
            remainder=np.where(~exact,cell_score,0.).sum(axis=1)
            dc_total=float(contribution.sum());rest_total=float(remainder.sum());pos=np.maximum(cell_score,0)
            pos_total=float(pos.sum());pos_dc=float(pos[exact].sum());positive_fraction=pos_dc/pos_total if pos_total else None
            rows=np.flatnonzero(exact.any(axis=1)).tolist()
            native=track.get('native_chunk_index',171)
            profile_key=relative+'#'+p['profile_id']
            for raw_row in range(16):
                for j,bits in enumerate(raw[raw_row].view(np.uint32)):
                    physical=(native,scan,raw_row,int(centers[raw_row])-251+j)
                    if physical in physical_bits:
                        equal(int(bits),physical_bits[physical],prefix+'/duplicate_rawcell/'+str((raw_row,j)))
                        duplicate_instances+=1
                    else:physical_bits[physical]=int(bits)
                    raw_instances+=1
            reconstructed={'phase':phase,'profile_id':p['profile_id'],'profile_key':profile_key,'native':native,'context_scan_id':scan,
                'width_channels':width,'fixed_full_score':full,'exactDC_score_contribution':dc_total,
                'remaining_score_contribution':rest_total,'signed_DC_score_fraction':dc_total/full if full else None,
                'positive_cell_DC_fraction':positive_fraction,'exactDC_overlap_rows':rows,
                'row_original_score_contribution':(row/denom).tolist(),
                'row_exactDC_score_contribution':contribution.tolist(),'row_remaining_score_contribution':remainder.tolist(),
                'cell_standardized_values':cells.tolist(),'cell_absolute_channels':source_cell_channels.tolist(),
                'cell_normalized_medians':med.tolist(),'cell_residual_values':(ratio[:,cols]-med).tolist(),
                'positive_dc_standardized_cell_mass':float(np.maximum(cells,0)[exact].sum()),
                'total_positive_standardized_cell_mass':float(np.maximum(cells,0).sum()),
                'cell_raw_power':raw[:,cols].astype(float).tolist(),
                'source_capsule':pin(cap_path),'normalization':pin(norm_path)}
            near(dc_total+rest_total,full,prefix+'/algebraic_sum')
            profiles.append(reconstructed);capsules.append({'phase':phase,'profile_id':p['profile_id'],'profile_key':profile_key,'native':native,'scan':scan,'centers':centers,'raw':raw,'source_capsule':pin(cap_path)})
    require(len(profiles)==108,'Frozen profile total differs')
    counts.update({'independent_profiles':108,'local501_medians':sum(16*p['width_channels'] for p in profiles),
                   'reconstructed_box_cells':sum(16*p['width_channels'] for p in profiles),'source_capsules_hashed':108,
                   'normalizations_hashed':108,'raw503_cells_read':108*16*503,
                   'raw_cell_instances':raw_instances,'unique_raw_cells':len(physical_bits),
                   'duplicate_raw_cells_bit_equal':duplicate_instances})
    patch_records=[];patch_cube=np.empty((3,6,16,129),dtype='<f4');row_index=np.arange(16)[:,None]
    flank_columns=np.r_[np.arange(0,49),np.arange(80,129)]
    for di,dc in enumerate(DC):
        for si,scan in enumerate(SCANS):
            covering=[];patch=np.empty((16,129),dtype='<f4');row_provenance=[];row_comparisons=0
            candidates=sorted([c for c in capsules if c['scan']==scan and c['native']==170+di],key=lambda c:c['profile_key'])
            for row in range(16):
                selected=None
                for cap in candidates:
                    indices=dc+np.arange(-64,65)-cap['centers'][row]+251
                    if not ((indices>=0)&(indices<503)).all():continue
                    candidate=cap['raw'][row,indices]
                    if selected is None:
                        patch[row]=candidate;selected=cap
                        row_provenance.append({'source_row':row,'profile_key':cap['profile_key'],
                            'raw_capsule':cap['source_capsule']['path'],'capsule_center':int(cap['centers'][row]),
                            'capsule_half_open_slice':[int(indices[0]),int(indices[-1])+1]})
                    else:
                        equal(candidate.view(np.uint32),patch[row].view(np.uint32),f'patch/{dc}/{scan}/row{row}/covering/{cap["phase"]}/{cap["profile_id"]}')
                        row_comparisons+=1
                    if cap['source_capsule'] not in covering:covering.append(cap['source_capsule'])
                require(selected is not None,'No frozen capsule row fully covers DC±64 '+str((dc,scan,row)))
            patch_cube[di,si]=patch
            flank=np.median(patch[:,flank_columns].astype(np.float64),axis=1)
            require((flank>0).all(),'Invalid flank denominator')
            ratio=patch[:,64].astype(np.float64)/flank
            argmax=np.argmax(patch,axis=1);peak=argmax==64
            ties=np.count_nonzero(patch==np.max(patch,axis=1,keepdims=True),axis=1)
            patch_records.append({'DC_channel':dc,'scan_id':scan,'covering_capsules':covering,'canonical_row_provenance':row_provenance,
                'covering_capsule_row_bit_comparisons':row_comparisons,
                'row_center_over_flank_ratio':ratio.tolist(),'row_flank_median_power':flank.tolist(),
                'row_center_raw_power':patch[:,64].astype(float).tolist(),'row_raw_argmax_offset':(argmax-64).tolist(),
                'raw_center_argmax_rows':np.flatnonzero(peak).tolist(),'raw_center_argmax_count':int(peak.sum()),
                'row_maximum_tie_count':ties.tolist(),'raw_center_is_unique_peak_count':int((peak&(ties==1)).sum())})
    counts['independent_patches']=len(patch_records);counts['physical_raw_rows']=18*16
    counts['raw_peak_count']=sum(p['raw_center_argmax_count'] for p in patch_records)
    counts['covering_capsule_row_bit_comparisons']=sum(p['covering_capsule_row_bit_comparisons'] for p in patch_records)
    save(BASE/'INDEPENDENT_RECONSTRUCTION.json',{'DC_channels':DC,'profiles':profiles,'raw_patches':patch_records})
    with (BASE/'INDEPENDENT_PATCHES.npz').open('xb') as f:np.savez(f,raw_power=patch_cube,DC_channels=np.asarray(DC),scan_ids=np.asarray(SCANS),offsets=np.arange(-64,65))
    compare_primary(scope,profiles,patch_records,patch_cube,near,equal,checked,read,counts)
    compare_ranking(scope,near,equal,checked,read,counts)
    geometry=read(checked(WORKSPACE/'dc_study/geometry/GEOMETRY_RESULT.json'))
    for rel,d in geometry['input_pins'].items():checked(WORKSPACE/rel,d)
    for i,g in enumerate(geometry['fixed_line_center_geometry']):
        equal(g['fixed_line_source_channel'],DC[i],'geometry/DC_channel/'+str(i))
        equal(g['DC_offset_channels'],0,'geometry/exact_offset/'+str(i))
        near(g['header_frequency_Hz'],FCH1+DF*DC[i],'geometry/header_frequency/'+str(i))
    for file,g in zip(('blimpy_waterfall.py','blimpy_base_reader.py'),geometry['software_sources']):
        raw=(WORKSPACE/'dc_study/geometry'/file).read_bytes()
        equal(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),g['git_blob_sha'],'geometry/official_git_blob/'+file)
    counts['geometry_input_hashes_verified']=len(geometry['input_pins'])
    changed=[]
    for path,old in pins.items():
        if pin(Path(path))!=old:changed.append(path)
    mismatches.extend('input_changed/'+p for p in changed)
    elapsed=time.monotonic()-started;cpu_used=time.process_time()-cpu;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    require(elapsed<=CAP_WALL and cpu_used<=CAP_CPU and rss<=CAP_RAM,'Measured QA resource limit exceeded')
    result={'status':'PASS_INDEPENDENT_DC_DIAGNOSTIC_QA' if not mismatches else 'FAIL_QA_MISMATCHES_PRESERVED',
            'counts':counts,'comparisons':comparisons,'mismatches':mismatches,
            'CPU_seconds':cpu_used,'wall_seconds':elapsed,'peak_RSS_bytes':rss,
            'limits':{'CPU_seconds':CAP_CPU,'wall_seconds':CAP_WALL,'RAM_bytes':CAP_RAM},
            'numeric_tolerance':{'absolute':ATOL,'relative':RTOL},'input_pins_before_and_after':list(pins.values()),
            'limitations':['Local501 arithmetic is independent of producer but conditional on saved fullcore power median, MAD and winsorized residual location; fullcore residual filtering and normalization were not rerun.',
                           'Original source compact HDF5 arrays are not decoded here: raw patch provenance follows pinned pre-existing raw503 capsule bytes and consistency across every covering capsule.',
                           'Algebraic score decomposition is not a masked-detector score or reoptimized search and does not supply sensitivity, SNR or false-alarm calibration.',
                           'TOP20 geometric contact annotation preserves exposed original ranks. Geometric contact alone does not prove physical origin, and an untouched record is not independently qualified.',
                           'These historical original OFF targets differ and their contexts do not constitute independent repeats of one target. Nonstationary burst4 family is outside this study.'],
            'detector_imported':False,'detector_rerun':False,'telescope_requests':0,'new_mask_veto':False,'reranked_records':0,
            'qualified_SETI_detection':False}
    save(BASE/'QA_RECEIPT.json',result);signal.alarm(0)
    print(json.dumps({'status':result['status'],'counts':counts,'mismatches':mismatches,
                     'CPU_seconds':cpu_used,'wall_seconds':elapsed,'peak_RSS_bytes':rss}))

def compare_primary(scope,profiles,patches,patch_cube,near,equal,checked,read,counts):
    resultroot=WORKSPACE/'dc_study/primary/results'
    primary_scope=read(checked(WORKSPACE/'dc_study/primary/SCOPE.json'))
    receipt=read(checked(resultroot/'EXECUTION_RECEIPT.json'))
    equal(receipt['scope_sha256'],sha(WORKSPACE/'dc_study/primary/SCOPE.json'),'primary/receipt_scope')
    equal(receipt['driver_sha256'],sha(WORKSPACE/'dc_study/primary/driver.py'),'primary/receipt_driver')
    for d in receipt['input_byte_pins'].values():checked(WORKSPACE/d['path'],d)
    for d in receipt['output_byte_pins'].values():checked(WORKSPACE/d['path'],d)
    outputs=read(resultroot/'PROFILE_ATTRIBUTION.json')['profiles']
    rows=read(resultroot/'ROW_CELL_ATTRIBUTION.json')['rows']
    require(len(outputs)==108 and len(rows)==1728,'Primary profile/row result count differs')
    bykey={p['profile_key']:p for p in outputs};rowkey={(r['profile_key'],r['source_row']):r for r in rows}
    require(len(bykey)==108 and len(rowkey)==1728,'Duplicate primary output identity')
    own_fractions=[];standardized_dc={};including_profiles={};row_instances=0
    for p in profiles:
        key=p['profile_key'];actual=bykey[key]
        mapping={'fixed_full_score':'reconstructed_fixed_score','exactDC_score_contribution':'signed_dc_score',
            'remaining_score_contribution':'signed_remainder_score','positive_cell_DC_fraction':'positive_dc_cell_mass_fraction',
            'positive_dc_standardized_cell_mass':'positive_dc_standardized_cell_mass',
            'total_positive_standardized_cell_mass':'total_positive_standardized_cell_mass'}
        for own,field in mapping.items():
            if p[own] is None:equal(actual[field],None,'primary/'+key+'/'+field)
            else:near(actual[field],p[own],'primary/'+key+'/'+field)
        equal(actual['dc_box_overlap_rows'],p['exactDC_overlap_rows'],'primary/'+key+'/overlap_rows')
        equal(actual['dc_box_overlap_row_count'],len(p['exactDC_overlap_rows']),'primary/'+key+'/overlap_count')
        for r in range(16):
            row=rowkey[key,r];cells=row['cells'];require(len(cells)==p['width_channels'],'Producer cellwidth differs')
            equal([c['absolute_source_channel'] for c in cells],p['cell_absolute_channels'][r],'cells/'+key+'/'+str(r)+'/channels')
            near([c['raw_power'] for c in cells],p['cell_raw_power'][r],'cells/'+key+'/'+str(r)+'/rawpower')
            near([c['local501_normalized_median'] for c in cells],p['cell_normalized_medians'][r],'cells/'+key+'/'+str(r)+'/local501_median')
            near([c['residual'] for c in cells],p['cell_residual_values'][r],'cells/'+key+'/'+str(r)+'/residual')
            near([c['standardized_cell'] for c in cells],p['cell_standardized_values'][r],'cells/'+key+'/'+str(r)+'/standardized')
            equal([c['is_exact_dc'] for c in cells],[ch in DC for ch in p['cell_absolute_channels'][r]],'cells/'+key+'/'+str(r)+'/exactDC')
            near(row['dc_score_contribution'],p['row_exactDC_score_contribution'][r],'rows/'+key+'/'+str(r)+'/dcscore')
            near(row['remainder_score_contribution'],p['row_remaining_score_contribution'][r],'rows/'+key+'/'+str(r)+'/remainder')
            near(row['standardized_row_box_sum'],p['row_original_score_contribution'][r]*np.sqrt(16*p['width_channels']),'rows/'+key+'/'+str(r)+'/box')
            for ch,z in zip(p['cell_absolute_channels'][r],p['cell_standardized_values'][r]):
                if ch in DC:
                    physical=(p['native'],p['context_scan_id'],r)
                    standardized_dc.setdefault(physical,[]).append(z)
                    including_profiles.setdefault(physical,[]).append(key);row_instances+=1
        # Parent's18 own primary fractions independently traced to unchanged selected track.
        if p['context_scan_id']==actual['selected_track']['scan_id']:
            own_fractions.append(p['positive_cell_DC_fraction'])
            near(actual['selected_track']['score'],p['fixed_full_score'],'primary/'+key+'/origin_winner')
    require(len(own_fractions)==18,'Expected18 origin primary comparisons')
    counts['own_primary_profiles_verified']=18
    counts['own_primary_positive_DC_fraction_min']=min(own_fractions)
    counts['physical_DC_scan_rows_with_original_box_contact']=len(including_profiles)
    counts['all_profile_DC_overlap_row_instances']=row_instances
    # Raw cube ordering is independently constructed native ascending then scan chronology.
    with np.load(checked(resultroot/'DC_RAW_PATCHES.npz'),allow_pickle=False) as saved:
        equal(saved['raw_power'].view(np.uint32),patch_cube.reshape(18,16,129).view(np.uint32),'primary/raw_patch_bits')
        equal(saved['offsets_from_dc'],np.arange(-64,65),'primary/raw_patch_offsets')
        equal(saved['source_rows'],np.arange(16),'primary/raw_patch_rows')
        equal(saved['dc_source_channels'],np.repeat(DC,6),'primary/raw_patch_dc_order')
        equal(saved['native_dc_indices'],np.repeat([170,171,172],6),'primary/raw_patch_native_order')
        equal(saved['context_scan_ids'],SCANS*3,'primary/raw_patch_scan_order')
    metrics=read(resultroot/'DC_PATCH_METRICS.json');physical=read(resultroot/'DEDUPLICATED_DC_SCAN_ROWS.json')['physical_rows']
    physicalkey={(r['dc_source_channel'],r['context_scan_id'],r['source_row']):r for r in physical}
    require(len(metrics['patches'])==18 and len(physical)==len(physicalkey)==288,'Distinct physical patch/row output count differs')
    allratios=[];strict_count=0;max_count=0
    for p in patches:
        dc,scan=p['DC_channel'],p['scan_id'];index=DC.index(dc);scanindex=SCANS.index(scan)
        actual=next(q for q in metrics['patches'] if q['dc_source_channel']==dc and q['context_scan_id']==scan)
        bits=patch_cube[index,scanindex].tobytes()
        equal(actual['raw_patch_float32_sha256'],hashlib.sha256(bits).hexdigest(),f'patch/{dc}/{scan}/decoded_hash')
        equal(actual['canonical_row_provenance'],p['canonical_row_provenance'],f'patch/{dc}/{scan}/provenance')
        equal(actual['strict_center_peak_rows'],p['raw_center_is_unique_peak_count'],f'patch/{dc}/{scan}/strict_peak_rows')
        values=patch_cube[index,scanindex].astype(np.float64)
        for r in range(16):
            center=float(values[r,64]);othermax=float(np.max(np.r_[values[r,:64],values[r,65:]]));fullmax=float(values[r].max())
            expected={'raw_dc_power':center,'symmetric98_flank_median':p['row_flank_median_power'][r],
                'center_over_symmetric98_flank_median':p['row_center_over_flank_ratio'][r],
                'center_over_left_adjacent':center/values[r,63],'center_over_right_adjacent':center/values[r,65],
                'center_over_strongest_other_patch_bin':center/othermax,
                'strict_center_peak_over129':center>othermax,'center_is_maximum_including_ties':center==fullmax,
                'raw_patch_peak_offset_from_dc':p['row_raw_argmax_offset'][r]}
            row=next(a for a in actual['row_metrics'] if a['source_row']==r);phys=physicalkey[dc,scan,r]
            for k,v in expected.items():
                for output,a in [('row_metrics',row),('physical_rows',phys)]:
                    if isinstance(v,(bool,np.bool_,int)):equal(a[k],v,f'patch/{dc}/{scan}/{r}/{output}/{k}')
                    else:near(a[k],v,f'patch/{dc}/{scan}/{r}/{output}/{k}')
            physicalcoord=(index+170,scan,r);included=including_profiles.get(physicalcoord,[]);z=standardized_dc.get(physicalcoord,[])
            equal(phys['number_of_original_boxes_including_same_dc_cell'],len(included),f'patch/{dc}/{scan}/{r}/included_count')
            equal(sorted(phys['including_profile_keys']),sorted(included),f'patch/{dc}/{scan}/{r}/included_profiles')
            equal(phys['canonical_profile_key'],p['canonical_row_provenance'][r]['profile_key'],f'patch/{dc}/{scan}/{r}/canonical_profile')
            for k,v in [('conditional_dc_standardized_cell_min',min(z) if z else None),('conditional_dc_standardized_cell_max',max(z) if z else None)]:
                if v is None:equal(phys[k],v,f'patch/{dc}/{scan}/{r}/'+k)
                else:near(phys[k],v,f'patch/{dc}/{scan}/{r}/'+k)
            allratios.append(expected['center_over_symmetric98_flank_median']);strict_count+=expected['strict_center_peak_over129'];max_count+=expected['center_is_maximum_including_ties']
    summary=metrics['deduplicated_summary']
    equal(summary['strict_center_peak_count_over288'],strict_count,'rawsummary/strict_peak_count')
    equal(summary['center_is_maximum_including_ties_count_over288'],max_count,'rawsummary/inclusive_peak_count')
    equal(summary['all108_original_box_dc_overlap_row_instances'],row_instances,'rawsummary/overlap_instances')
    equal(summary['physical_rows_with_at_least_one_original_box_including_dc'],len(including_profiles),'rawsummary/physical_box_contact')
    for k,v in [('count',len(allratios)),('min',min(allratios)),('median',float(np.median(allratios))),('max',max(allratios))]:
        near(summary['center_over_symmetric98_flank_median_over288'][k],v,'rawsummary/ratio/'+k)
    rawrecon=read(resultroot/'RAW_RECONCILIATION.json')
    for field,own in [('cell_instances','raw_cell_instances'),('unique_cells','unique_raw_cells'),('duplicate_instances_bit_equal','duplicate_raw_cells_bit_equal')]:
        equal(rawrecon[field],counts[own],'rawreconciliation/'+field)
    counts['raw_center_strict_peak_count']=int(strict_count)
    counts['raw_center_flank_ratio_min']=min(allratios);counts['raw_center_flank_ratio_median']=float(np.median(allratios));counts['raw_center_flank_ratio_max']=max(allratios)

def compare_ranking(scope,near,equal,checked,read,counts):
    annotated=read(checked(WORKSPACE/'dc_study/ranking/ANNOTATED_TOP120.json'))
    groups=read(checked(WORKSPACE/'dc_study/ranking/scope.json'))['groups']
    reconstructed=[];touch_total=0
    for group in groups:
        top20=read(checked(WORKSPACE/group['top20']['path'],group['top20']))
        require(len(top20['records'])==20,'Original TOP20 record count differs')
        originals=top20['records']
        for rank,original in enumerate(originals,1):
            matched=[r for r in annotated['records'] if r['phase']==group['phase'] and r['source_TOP20_path']==group['top20']['path'] and r['original_rank']==rank]
            require(len(matched)==1,'Annotated original ranking identity missing/duplicate')
            r=matched[0]
            for k,v in original.items():equal(r[k],v,f'ranking/{group["phase"]}/{group["primary_target"]}/{rank}/original/{k}')
            native=original.get('native_chunk_index',171)
            reference=native*CHUNK+original['core_q']*4096+original['carrier_index_in_core']
            require(reference==original['reference_source_channel'],'Original source carrier map differs')
            times=np.array([i*TSAMP for i in range(16)],dtype=np.float64)
            centers=np.rint((original['frequency_hz_at_own_first_midpoint']-FCH1)/DF+original['drift_hz_s']*times/DF).astype(np.int64)
            half=original['width_channels']//2
            mask=np.array([[abs(int(c)-dc)<=half for dc in DC] for c in centers]);rows=np.flatnonzero(mask.any(axis=1)).tolist()
            nearest=min(DC,key=lambda dc:(abs(reference-dc),dc))
            prefix=f'ranking/{group["phase"]}/{group["primary_target"]}/{rank}'
            equal(r['rounded_absolute_centers'],centers,prefix+'/centers')
            equal(r['center_offsets_from_nearest_DC'],centers-nearest,prefix+'/center_offsets')
            equal(r['nearest_frozen_DC_channel'],nearest,prefix+'/nearestDC')
            equal(r['reference_offset_from_nearest_DC_channels'],reference-nearest,prefix+'/reference_offset')
            equal(r['rows_intersecting_any_frozen_DC'],len(rows),prefix+'/row_count')
            equal(r['row_indices_intersecting_any_frozen_DC'],rows,prefix+'/rows')
            equal(r['geometrically_DC_untouched'],not bool(rows),prefix+'/untouched')
            for i,dc in enumerate(DC):equal(r['touch_counts_by_frozen_DC'][str(dc)],int(mask[:,i].sum()),prefix+'/DC_contacts/'+str(dc))
            touch_total+=bool(rows);reconstructed.append(r)
    require(len(reconstructed)==120 and len(annotated['records'])==120,'Ranking total differs')
    equal(annotated['counts']['DC_touched_records'],touch_total,'ranking/aggregate_touched')
    equal(annotated['counts']['DC_untouched_records'],120-touch_total,'ranking/aggregate_untouched')
    untouched=read(checked(WORKSPACE/'dc_study/ranking/DC_UNTOUCHED_EXPOSED_SUBSET.json'))
    equal(untouched['records'],[r for r in reconstructed if r['geometrically_DC_untouched']],'ranking/subset_preserves_original_order')
    counts.update({'original_ranking_records_verified':120,'ranking_center_rows_verified':1920,
                   'ranking_DC_contact_checks':5760,'ranking_DC_touched_records':int(touch_total),
                   'ranking_DC_untouched_records':120-int(touch_total)})
if __name__=='__main__':main()
