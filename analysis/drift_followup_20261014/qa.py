"""Independent QA for the frozen conditional local drift diagnostic.

Check-only imports no numerical modules and opens no spectral arrays. Numerical
execution requires exact scope, this code, completed producer receipt and root QA
GO hashes. No producer import or producer-source inspection is used. Every saved
normalization core is recomputed using direct 501-bin medians; changed channels
are independently sampled from authenticated raw12096 crops.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import signal
import time

for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'

CPU_CAP, WALL_CAP, MEMORY_CAP = 600, 900, 2 * 1024**3
DF, TSAMP = -2.7939677238464355, 18.253611008
OFFSETS = [0,-1024,-768,-512,-256,256,512,768,1024]
PHASES = [-.5,-.25,0.,.25,.5]
STARTS = [0,2,4,6,8,10,12]
DC = [178782208,179830784,180879360]
ATOL, RTOL = 1e-7, 1e-10


def require(ok, why):
    if not ok:
        raise ValueError(why)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):
            h.update(chunk)
    return h.hexdigest()


def pairs(items):
    d={}
    for key,value in items:
        require(key not in d, 'Duplicate JSON key')
        d[key]=value
    return d


def decode(data):
    return json.loads(data,object_pairs_hook=pairs,
                      parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root,name):
    path=root/name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root) and not path.is_symlink(), 'Input path escapes root')
    return path


def json_out(path,data):
    with path.open('xb') as f:
        f.write((json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        f.flush();os.fsync(f.fileno())


def exact(a,b,why):
    a,b=np.asarray(a),np.asarray(b)
    require(a.shape==b.shape and np.array_equal(a,b),why)


def close(a,b,why):
    a,b=np.asarray(a),np.asarray(b)
    require(a.shape==b.shape,why+' (shape)')
    finite=np.isfinite(a)&np.isfinite(b)
    require(np.array_equal(np.isfinite(a),np.isfinite(b)) and np.array_equal(a[~finite],b[~finite]),why+' (nonfinite)')
    require(np.allclose(a[finite],b[finite],atol=ATOL,rtol=RTOL),why+' (numerical)')
    return float(np.max(np.abs(a[finite]-b[finite]))) if finite.any() else 0.


def direct_normalization(raw,core0,crop0):
    """Independent row-major direct501 medians on every original core cell."""
    require(raw.shape==(16,12096) and raw.dtype==np.dtype('<f4'), 'Raw crop dtype/shape differs')
    local=core0-crop0
    require(local==4000,'Expected authenticated halo origin')
    core=raw[:,local:local+4096].astype(np.float64)
    levels=np.median(core,axis=1)
    residual=np.empty((16,4096),dtype=np.float64)
    for row in range(16):
        ratio=raw[row].astype(np.float64)/levels[row]
        for first in range(0,4096,256):
            positions=np.arange(local+first,local+min(4096,first+256))
            samples=ratio[positions[:,None]+np.arange(-250,251)]
            residual[row,first:first+len(positions)]=ratio[positions]-np.median(samples,axis=1)
    centers=np.median(residual,axis=1)
    scales=1.4826*np.median(np.abs(residual-centers[:,None]),axis=1)
    clipped=np.clip(residual-centers[:,None],-5*scales[:,None],5*scales[:,None])
    locations=centers+clipped.mean(axis=1)
    require(np.all(levels>0) and np.all(scales>0), 'Normalization scales invalid')
    return {'row_power_median':levels,'row_residual_median':centers,
            'row_residual_MAD_scale':scales,'row_winsorized_residual_location':locations}


def family_centers(profile):
    """Absolute-channel rounding, with frozen primary reference in every window."""
    track=profile['selected_track']
    times=np.asarray(profile['times_from_primary_reference_s'],dtype=np.float64)
    require(times.shape==(16,) and np.all(np.isfinite(times)), 'Frozen times invalid')
    require(np.allclose(np.diff(times),TSAMP,atol=1e-9,rtol=0),'Times do not preserve exact integration spacing')
    require(profile['reference_time_mjd']==track['reference_time_mjd'],'Reference changed from original selection')
    d0=float(track['drift_hz_s'])
    drifts=d0+np.linspace(-4/158,4/158,81)
    tuples=[(d,p) for d in drifts for p in PHASES]
    require(len(tuples)==405, 'Family count differs')
    centers=np.empty((9,405,16),dtype=np.int64)
    for oi,offset in enumerate(OFFSETS):
        for ti,(drift,phase) in enumerate(tuples):
            centers[oi,ti]=np.rint(int(track['source_reference_channel'])+phase+offset+drift*times/DF).astype(np.int64)
    if profile['context_scan_id']==track['scan_id']:
        require(times[track['window_start_row']]==0.,'Origin anchor is not original selected first midpoint')
        exact(centers[0,202],profile['rounded_absolute_centers'],'Coarse r0 geometry differs from prior frozen profile')
    return centers,drifts,times


def direct_family_residuals(raw,crop0,normal,centers):
    """Only identical row/channel samples share work; direct501 medians otherwise."""
    terms=np.empty(centers.shape,dtype=np.float64)
    halo=np.arange(-250,251)
    for row in range(16):
        channels,inverse=np.unique(centers[:,:,row],return_inverse=True)
        positions=channels-crop0
        require(positions.min()>=250 and positions.max()+250<12096, 'Family lacks full501 halo')
        ratio=raw[row].astype(np.float64)/normal['row_power_median'][row]
        z=np.empty(len(channels),dtype=np.float64)
        for start in range(0,len(channels),256):
            sl=positions[start:start+256]
            medians=np.median(ratio[sl[:,None]+halo],axis=1)
            z[start:start+len(sl)]=(ratio[sl]-medians-normal['row_winsorized_residual_location'][row])/normal['row_residual_MAD_scale'][row]
        terms[:,:,row]=z[inverse].reshape(9,405)
    return terms


def window_values(terms,centers):
    row_dc=np.isin(centers,DC)
    scores=np.stack([terms[:,:,s:s+4].sum(axis=2)/2. for s in STARTS],axis=2)
    window_dc=np.stack([row_dc[:,:,s:s+4].any(axis=2) for s in STARTS],axis=2)
    clean=np.where(window_dc,-np.inf,scores)
    return scores,clean,row_dc,window_dc


def winner(scores):
    require(np.isfinite(scores).any(), 'No DC-clean family hypothesis')
    flat=int(np.argmax(scores))
    index=np.unravel_index(flat,scores.shape)
    return float(scores[index]),tuple(int(i) for i in index)


def injection_cases(profile,centers,times,clean):
    """Conditional z-domain single-bin deltas; no observed arrays are mutated."""
    track=profile['selected_track']
    host=OFFSETS.index(512)
    background=clean[host]
    background_max,background_winner=winner(background)
    for active_start in STARTS:
        for drift_fraction in (-.73,.61):
            for phase in (-.37,.29):
                drift=float(track['drift_hz_s'])+drift_fraction*(4/158)
                true=np.rint(int(track['source_reference_channel'])+512+phase+drift*times/DF).astype(np.int64)
                hit=centers[host]==true[None,:]
                active=np.zeros(16,dtype=np.bool_);active[active_start:active_start+4]=True
                captures=np.stack([(hit[:,s:s+4]&active[None,s:s+4]).sum(axis=1) for s in STARTS],axis=1)
                eligible=np.isfinite(background)
                response=np.where(eligible,captures/4.,-np.inf)
                geometry,geometry_win=winner(response)
                coarse_window=STARTS.index(active_start)
                for amplitude in (2.,8.):
                    injected=np.where(eligible,background+amplitude*captures/2.,-np.inf)
                    fine,fine_win=winner(injected)
                    coarse_active=float(injected[202,coarse_window])
                    coarse_all,coarse_win=winner(injected[202])
                    yield {'profile_id':profile['profile_id'],'active_start_row':active_start,
                           'drift_fraction':drift_fraction,'true_drift_hz_s':drift,'true_phase_channels':phase,
                           'amplitude':amplitude,'true_centers':true.tolist(),'background_max':background_max,
                           'background_winner':background_winner,'injected_fine_max':fine,
                           'injected_fine_winner':fine_win,'fine_uplift':fine-background_max,
                           'coarse_active_score':coarse_active,'coarse_all7_max':coarse_all,
                           'coarse_all7_winner':coarse_win,'signal_only_response':geometry,
                           'signal_only_winner':geometry_win,
                           'coarse_active_response':float(response[202,coarse_window]),
                           'coarse_all7_response':float(response[202].max()),
                           '_injected':injected,'_captures':captures,'_response':response,
                           '_background':background}


def audit_winner(saved,values,centers,drifts,offset_index,fixed_window=None,fixed_hypothesis=None):
    eligible=np.asarray(values)
    score,index=winner(eligible)
    if fixed_window is not None:
        hi=index[0];wi=fixed_window
    elif fixed_hypothesis is not None:
        hi=fixed_hypothesis;wi=index[0]
    else:
        hi,wi=index
    di,pi=divmod(hi,5)
    start=STARTS[wi];selected=centers[offset_index,hi,start:start+4]
    expect={'hypothesis_index':hi,'drift_index':di,'phase_index':pi,'window_index':wi,
            'window_start_row':start,'offset_channels':OFFSETS[offset_index],
            'selected4_dc_contact':bool(np.isin(selected,DC).any()),
            'full16_dc_contact':bool(np.isin(centers[offset_index,hi],DC).any()),
            'selected4_absolute_centers':selected.tolist()}
    for key,value in expect.items():
        require(saved[key]==value,'Saved winner '+key+' differs')
    error=max(close(saved['score'],score,'Winner score differs'),
              close(saved['drift_hz_s'],drifts[di],'Winner drift differs'),
              close(saved['phase_channels'],PHASES[pi],'Winner phase differs'))
    return hi,wi,error


def audit_profile(saved,profile,arrays,normal,crop0,raw):
    centers,drifts,times=family_centers(profile)
    terms=direct_family_residuals(raw,crop0,normal,centers)
    scores,clean,row_dc,window_dc=window_values(terms,centers)
    schema={'residual_row_terms':('<f8',(9,405,16)),
            'rounded_absolute_centers':('<i8',(9,405,16)),
            'scores':('<f8',(9,405,7)),'row_dc_mask':('|b1',(9,405,16)),
            'window_dc_mask':('|b1',(9,405,7)),
            'family_drift_hz_s':('<f8',(405,)),'family_phase_channels':('<f8',(405,)),
            'offset_channels':('<i8',(9,)),'window_start_rows':('<i8',(7,)),
            'window_source_rows':('<i8',(7,4)),
            'times_from_primary_reference_s':('<f8',(16,)),
            'row501_unique_center_counts':('<i8',(16,))}
    require(set(arrays)==set(schema),'Saved family NPZ fields differ')
    for key,(dtype,shape) in schema.items():
        require(arrays[key].dtype==np.dtype(dtype) and arrays[key].shape==shape,'Saved '+key+' dtype/shape differs')
    for key,expect in [('rounded_absolute_centers',centers),('row_dc_mask',row_dc),('window_dc_mask',window_dc),
                       ('offset_channels',OFFSETS),('window_start_rows',STARTS),
                       ('window_source_rows',[list(range(s,s+4)) for s in STARTS]),
                       ('row501_unique_center_counts',[len(np.unique(centers[:,:,r])) for r in range(16)])]:
        exact(arrays[key],expect,'Saved family '+key+' differs')
    row_error=close(arrays['residual_row_terms'],terms,'All family row residuals differ')
    score_error=close(arrays['scores'],scores,'All raw family scores differ')
    close(arrays['family_drift_hz_s'],np.repeat(drifts,5),'Saved drift axis differs')
    close(arrays['family_phase_channels'],np.tile(PHASES,81),'Saved phase axis differs')
    exact(arrays['times_from_primary_reference_s'],times,'Saved original-reference time axis differs')
    close(terms[0,202],profile['row_standardized_box_sum'],'Original fixed16 terms changed')
    wi=STARTS.index(profile['selected_track']['window_start_row'])
    fixed=float(scores[0,202,wi])
    close(fixed,profile['fixed_four_row_score'],'Prior original4 score does not reproduce')
    expected_meta={'profile_id':profile['profile_id'],'origin_scan_id':profile['selected_track']['scan_id'],
                   'context_scan_id':profile['context_scan_id'],'origin_rank':profile['selected_track']['rank'],
                   'original_window_start_row':STARTS[wi],'original_width_channels':1,
                   'times_from_primary_reference_s':times.tolist(),
                   'coarse_zero_offset_full16_absolute_centers':centers[0,202].tolist()}
    for key,value in expected_meta.items():
        require(saved[key]==value,'Profile summary '+key+' differs')
    close(saved['original_fixed_four_row_score'],profile['fixed_four_row_score'],'Original metadata score differs')
    close(saved['recomputed_fixed_four_row_score'],fixed,'Recomputed fixed score differs')
    close(saved['baseline_difference'],fixed-profile['fixed_four_row_score'],'Baseline difference differs')
    require(len(saved['offset_results'])==9,'Offset summary count differs')
    fixed_best=[];all7_best=[]
    for oi,record in enumerate(saved['offset_results']):
        require(record['offset_channels']==OFFSETS[oi],'Summary offset order changed')
        close(record['fixed_d0_phase0_original4_score'],scores[oi,202,wi],'Coarse fixed4 score differs')
        require(record['fixed_d0_phase0_original4_dc_eligible']==bool(not window_dc[oi,202,wi]),'Coarse DC eligibility differs')
        _,_,e=audit_winner(record['fixed_d0_phase0_max7'],clean[oi,202],centers,drifts,oi,fixed_hypothesis=202)
        hi,_,e1=audit_winner(record['fine_fixed_original4'],clean[oi,:,wi],centers,drifts,oi,fixed_window=wi)
        hi7,_,e2=audit_winner(record['fine_max7'],clean[oi],centers,drifts,oi)
        score_error=max(score_error,e,e1,e2)
        require(record['excluded_original4_hypotheses']==int(window_dc[oi,:,wi].sum())
                and record['excluded_all7_hypothesis_windows']==int(window_dc[oi].sum())
                and record['full16_contact_hypotheses']==int(row_dc[oi].any(axis=1).sum()),'DC exclusion summaries differ')
        fixed_best.append(float(clean[oi,:,wi].max()));all7_best.append(float(clean[oi].max()))
        if oi==0:
            require(saved['fine_fixed4_zero_offset_full16_absolute_centers']==centers[0,hi].tolist()
                    and saved['fine_max7_zero_offset_full16_absolute_centers']==centers[0,hi7].tolist(),
                    'Fine zero-offset full16 centers differ')
    counts=[]
    for vector in (fixed_best,all7_best):
        counts.extend([sum(v>vector[0] for v in vector[1:]),sum(v==vector[0] for v in vector[1:])])
    expected_rank=dict(zip(('fixed_original4_control_strictly_greater_count','fixed_original4_control_equal_count',
                            'max7_control_strictly_greater_count','max7_control_equal_count'),counts))
    expected_rank['fixed_original4_rank_among_target_plus8']=1+counts[0]
    expected_rank['max7_rank_among_target_plus8']=1+counts[2]
    require(saved['control_ranks']==expected_rank,'Conditional control ranks differ')
    return centers,times,clean,{'profile_id':profile['profile_id'],'max_row_error':row_error,
                              'max_score_error':score_error,'control_ranks':expected_rank,
                              'DC_contact_hypothesis_rows':int(row_dc.sum())}


def trial_key(trial):
    return (trial['profile_id'],trial['true_window_start_row'],
            trial['true_drift_fraction_of_half_original_step'],trial['true_phase_channels'],
            trial['amplitude_per_active_standardized_single_bin'])


def audit_injection(saved,case,profile,centers,drifts):
    host=OFFSETS.index(512);wi=STARTS.index(case['active_start_row'])
    injected=case['_injected'];captures=case['_captures'];response=case['_response'];background=case['_background']
    hi,fwi,error=audit_winner(saved['fine_winner'],injected,centers,drifts,host)
    _,coarse_index=winner(injected[202]);cwi=coarse_index[0]
    _,signal_index=winner(response);shi,swi=signal_index
    expect={'profile_id':profile['profile_id'],'origin_scan_id':profile['selected_track']['scan_id'],
            'context_scan_id':profile['context_scan_id'],'origin_rank':profile['selected_track']['rank'],
            'host_offset_channels':512,'true_window_index':wi,'true_window_start_row':STARTS[wi],
            'true_active_source_rows':list(range(STARTS[wi],STARTS[wi]+4)),
            'true_absolute_centers':case['true_centers'],
            'fine_winner_matches_true_activity_window':fwi==wi,
            'fine_winner_matching_active4_count':int(captures[hi,fwi]),
            'coarse_winner_window_index':cwi,'coarse_winner_window_start_row':STARTS[cwi],
            'coarse_winner_matches_true_activity_window':cwi==wi,
            'coarse_winner_matching_active4_count':int(captures[202,cwi]),
            'coarse_truewindow_matching_active4_count':int(captures[202,wi]),
            'signal_only_fine_best_matching_active4_count':int(captures[shi,swi]),
            'signal_only_fine_best_hypothesis_index':shi,'signal_only_fine_best_window_index':swi,
            'signal_only_fine_best_matches_true_activity_window':swi==wi,
            'raw_sensitivity_or_FAP_established':False}
    for key,value in expect.items():
        require(saved[key]==value,'Injection '+key+' differs')
    expected_float={'true_drift_fraction_of_half_original_step':case['drift_fraction'],
                    'true_drift_hz_s':case['true_drift_hz_s'],'true_phase_channels':case['true_phase_channels'],
                    'amplitude_per_active_standardized_single_bin':case['amplitude'],
                    'fine_score':case['injected_fine_max'],
                    'fine_zero_injection_max7_score':case['background_max'],
                    'fine_max7_uplift':case['fine_uplift'],
                    'fine_winner_matching_active4_fraction':float(captures[hi,fwi]/4.),
                    'coarse_max7_score':float(injected[202,cwi]),
                    'coarse_zero_injection_max7_score':float(background[202].max()),
                    'coarse_max7_uplift':float(injected[202,cwi]-background[202].max()),
                    'coarse_truewindow_score':float(injected[202,wi]),
                    'coarse_zero_injection_truewindow_score':float(background[202,wi]),
                    'coarse_truewindow_uplift':float(injected[202,wi]-background[202,wi]),
                    'coarse_truewindow_signal_only_matched_row_fraction':float(captures[202,wi]/4.),
                    'signal_only_fine_best_matched_row_fraction':float(captures[shi,swi]/4.)}
    for key,value in expected_float.items():
        error=max(error,close(saved[key],value,'Injection '+key+' differs'))
    require(saved['model']=='additive_standardized_residual_native_delta_bin_frozen_normalization','Saved injection model differs from frozen delta transport')
    return {'fine_score_error':error,'signal_only_capture_fraction':float(captures[shi,swi]/4.),
            'fine_winner_capture_fraction':float(captures[hi,fwi]/4.),
            'fine_winner_matches_true_activity_window':fwi==wi}


def audit_csv(data,records,why):
    rows=list(csv.DictReader(io.StringIO(data.decode())))
    require(len(rows)==len(records),why+' row count differs')
    for row,record in zip(rows,records):
        require(set(row)==set(record),why+' columns differ')
        for key,value in record.items():
            if isinstance(value,(list,dict)):
                require(decode(row[key])==value,why+' nested field differs')
            elif isinstance(value,bool):
                require(row[key] in (str(value),str(value).lower()),why+' bool field differs')
            else:
                require(row[key]==str(value),why+' scalar field differs')


def validate_scope(scope):
    require(scope['schema']=='SETI_LOCAL_DRIFT_DIAGNOSTIC_V1', 'Wrong diagnostic scope')
    g=scope['geometry'];n=scope['normalization'];i=scope['injections'];b=scope['budget']
    require(g['df_hz']==DF and g['tsamp_s']==TSAMP and g['offset_channels']==OFFSETS
            and g['phase_channels']==PHASES and g['window_start_rows']==STARTS
            and g['width_channels']==1 and g['window_length_rows']==4
            and g['drift_count']==81 and g['drift_half_step_hz_s']==4/158
            and g['dc_channels']==DC,'Frozen geometry differs')
    require(n['median_width']==501 and n['reuse_fixed_original_core'] is True
            and n['tolerance_abs']==ATOL and n['tolerance_rel']==RTOL,'Frozen preprocessing differs')
    require(i['active_start_rows']==STARTS and i['amplitudes_per_active_standardized_single_bin']==[2,8]
            and i['drift_fractions_of_half_step']==[-.73,.61] and i['phase_channels']==[-.37,.29]
            and i['host_offset_channels']==512 and i['cases']==3024
            and i['signal_model'].startswith('Additive normalized-domain delta in one native bin'),
            'Frozen diagnostic injection model differs')
    require(b['CPU_seconds']==CPU_CAP and b['wall_seconds']==WALL_CAP and b['memory_bytes']==MEMORY_CAP
            and b['DKK']==0,'Frozen resource reservation differs')
    require(len(scope['profile_ids'])==54 and len(set(scope['profile_ids']))==54,'Profile family differs')
    require(all(value is False for key,value in scope['interpretation'].items() if key in
                ('calibrated_FAP','independent_replication','physical_sensitivity','qualified_OFF_veto','qualified_SETI_detection')),
            'Prohibited scientific interpretation')


def arguments():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True)
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--inputs-root',help='Frozen input tree; defaults to SCOPE source_root')
    p.add_argument('--portable-inputs',action='store_true',help='Substitute extracted input root, preserving every byte pin')
    p.add_argument('--output-dir',default='qa_results')
    for key in ('scope-sha256','qa-sha256','receipt-sha256','root-go-sha256'):
        p.add_argument('--'+key)
    return p.parse_args()


def main():
    args=arguments();root=Path(args.root).resolve()
    if args.check_only:
        print(json.dumps({'status':'PASS_TEXT_ONLY_INDEPENDENT_LOCAL_DRIFT_QA_INTERFACE',
                          'source_values_read':False,'numerical_modules_imported':False,
                          'profiles':54,'normalization_cores':54,'observed_row_samples':3149280,
                          'injections':3024,'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,
                          'memory_cap_bytes':MEMORY_CAP,'producer_imported':False}))
        return
    for pin in (args.scope_sha256,args.qa_sha256,args.receipt_sha256,args.root_go_sha256):
        require(pin is not None and re.fullmatch('[0-9a-f]{64}',pin),'Exact frozen SHA256 required')
    require(sha(Path(__file__).resolve())==args.qa_sha256,'Independent QA code changed')
    run(root,args)


def run(root,args):
    global np
    started=time.monotonic()
    scope_path=root/'SCOPE.json';go_path=root/'QA_GO.json'
    receipt_path=root/'results'/'EXECUTION_RECEIPT.json'
    require(sha(scope_path)==args.scope_sha256 and sha(go_path)==args.root_go_sha256
            and sha(receipt_path)==args.receipt_sha256,'Frozen gate/receipt digest differs')
    scope=decode(scope_path.read_bytes());validate_scope(scope)
    go=decode(go_path.read_bytes())
    require(go['status']=='GO_INDEPENDENT_LOCAL_DRIFT_QA'
            and go['scope_sha256']==args.scope_sha256 and go['qa_code_sha256']==args.qa_sha256
            and go['producer_receipt_sha256']==args.receipt_sha256,'Root QA GO does not authorize this exact run')
    receipt=decode(receipt_path.read_bytes())
    require(receipt['status']=='COMPLETE_BOUNDED_LOCAL_DRIFT_PHASE_PRODUCTION','Producer did not complete')
    require(receipt['scope']['sha256']==args.scope_sha256,'Producer used different scope')
    source_root=Path(args.inputs_root or scope['source_root']).resolve()
    require(args.portable_inputs or source_root==Path(scope['source_root']).resolve(),'Exact input root required unless portable')
    out=confined(root,args.output_dir)
    require(not out.exists() and out!=root and out!=root/'results','Fresh separate QA output required')
    pin_map={p['path']:p for p in scope['input_pins']}
    require(len(pin_map)==114 and len(pin_map)==len(scope['input_pins']),'Frozen input pin count differs')
    read_pins={}

    def authenticated(base,pin):
        path=confined(base,pin['path']);data=path.read_bytes()
        require(len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256'],
                'Pinned bytes differ: '+pin['path'])
        read_pins[str(path)]={'bytes':len(data),'sha256':pin['sha256']}
        return data

    for pin in scope['input_pins']:
        authenticated(source_root,pin)
    product_root=root/'results'
    product_pins={p['path']:p for p in receipt['outputs']}
    require(len(product_pins)==58 and len(product_pins)==len(receipt['outputs']),'Saved output pin count differs')
    require({'PROFILES.json','PROFILES.csv','INJECTIONS.json','INJECTIONS.csv'}<=set(product_pins),
            'Saved summaries missing')
    summaries={name:authenticated(product_root,product_pins[name]) for name in
               ('PROFILES.json','PROFILES.csv','INJECTIONS.json','INJECTIONS.csv')}
    profiles_doc=decode(summaries['PROFILES.json']);injections_doc=decode(summaries['INJECTIONS.json'])
    require(profiles_doc['schema']=='SETI_LOCAL_DRIFT81_PHASE5_FOLLOWUP_V1'
            and profiles_doc['status']=='COMPLETE_54_AUTHENTICATED_PROFILES','Saved profile result schema/status differs')
    require(injections_doc['schema']=='SETI_RESIDUAL_DOMAIN_DELTA_BIN_INJECTION_TRANSPORT_V1'
            and injections_doc['count']==3024,'Saved injection schema/count differs')
    saved_profiles=profiles_doc['profiles'];saved_trials=injections_doc['trials']
    require(len(saved_profiles)==54 and [p['profile_id'] for p in saved_profiles]==scope['profile_ids'],
            'Saved profile order/count differs')
    require(len(saved_trials)==3024,'Saved injection case count differs')
    audit_csv(summaries['PROFILES.csv'],saved_profiles,'Profile CSV')
    audit_csv(summaries['INJECTIONS.csv'],saved_trials,'Injection CSV')
    trials={trial_key(t):t for t in saved_trials}
    require(len(trials)==3024,'Duplicate saved injection trial')
    matrix=decode(authenticated(source_root,pin_map[scope['matrix_path']]))
    require(matrix['status']=='COMPLETE_FULL_ON_BURST4_CLEAN_TOP9_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
            and [p['profile_id'] for p in matrix['profiles']]==scope['profile_ids'],
            'Authoritative frozen context profile matrix differs')
    crop_records={c['crop_id']:c for c in matrix['normalization_crops']}
    require(len(crop_records)==54,'Frozen normalization crop count differs')

    def alarm(signum,frame):
        raise TimeoutError('Independent local drift QA exceeded frozen wall bound')

    resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP))
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP))
    signal.signal(signal.SIGALRM,alarm);signal.alarm(WALL_CAP)
    import numpy as numpy
    np=numpy
    out.mkdir()
    reports=[];normal_reports=[];injection_reports=[]
    norms_done=set();seen_trials=set()
    try:
        for index,(profile,saved) in enumerate(zip(matrix['profiles'],saved_profiles)):
            record=crop_records[profile['normalization_crop_id']]
            require(record['raw_crop']==profile['raw_normalization_crop']
                    and record['normalization']==profile['normalization'],'Context input pins inconsistent')
            for pin in (record['raw_crop'],record['normalization']):
                require(pin_map[pin['path']]==pin,'Profile input was not scope-frozen')
            raw_bytes=authenticated(source_root,record['raw_crop'])
            with np.load(io.BytesIO(raw_bytes),allow_pickle=False) as archive:
                require(len(archive.files)==len(set(archive.files)),'Duplicate raw NPZ members')
                raw={key:archive[key] for key in archive.files}
            require(set(raw)=={'raw_power','source_channel0','normalization_source_channels','absolute_time_rows'},
                    'Raw crop schema differs')
            require(raw['source_channel0'].dtype==np.dtype('<i8') and raw['source_channel0'].shape==(),
                    'Crop origin dtype/shape differs')
            crop0=int(raw['source_channel0']);core0=record['normalization_source_channel_interval_half_open'][0]
            require(record['source_channel_interval_half_open']==[crop0,crop0+12096]
                    and record['normalization_source_channel_interval_half_open']==[core0,core0+4096],
                    'Raw/core metadata coordinate intervals differ')
            require(raw['normalization_source_channels'].dtype==np.dtype('<i8')
                    and raw['absolute_time_rows'].dtype==np.dtype('<i8'), 'Raw coordinate dtypes differ')
            exact(raw['normalization_source_channels'],np.arange(core0,core0+4096),'Raw core coordinates differ')
            exact(raw['absolute_time_rows'],np.arange(16),'Raw time-row coordinates differ')
            require(np.isfinite(raw['raw_power']).all() and np.all(raw['raw_power']>=0),'Raw crop nonfinite/negative')
            saved_normal=decode(authenticated(source_root,record['normalization']))
            normal=direct_normalization(raw['raw_power'],core0,crop0)
            nerr=0.
            for key,value in normal.items():
                nerr=max(nerr,close(saved_normal[key],value,'Independent normalization '+key+' differs'))
            exact(saved_normal['normalization_unmasked_counts'],np.full(16,4096),'Normalization counts differ')
            exact(saved_normal['normalization_source_channels'],np.arange(core0,core0+4096),'Normalization core channels differ')
            require(profile['normalization_crop_id'] not in norms_done,'Normalization reused where unique core expected')
            norms_done.add(profile['normalization_crop_id'])
            normal_reports.append({'crop_id':profile['normalization_crop_id'],'max_absolute_error':nerr,
                                   'direct501_core_channels':65536})
            require(saved['input_raw_crop']==record['raw_crop'] and saved['input_normalization']==record['normalization'],
                    'Saved result input provenance differs')
            family_pin=saved['family_arrays'];require(product_pins[family_pin['path']]==family_pin,
                                                     'Family artifact receipt pin differs')
            with np.load(io.BytesIO(authenticated(product_root,family_pin)),allow_pickle=False) as archive:
                require(len(archive.files)==len(set(archive.files)),'Duplicate result NPZ members')
                arrays={key:archive[key] for key in archive.files}
            centers,times,clean,report=audit_profile(saved,profile,arrays,normal,crop0,raw['raw_power'])
            reports.append(report);drifts=float(profile['selected_track']['drift_hz_s'])+np.linspace(-4/158,4/158,81)
            for case in injection_cases(profile,centers,times,clean):
                key=(case['profile_id'],case['active_start_row'],case['drift_fraction'],case['true_phase_channels'],case['amplitude'])
                require(key in trials and key not in seen_trials,'Missing/repeated injected conditional case')
                seen_trials.add(key)
                injection_reports.append(audit_injection(trials[key],case,profile,centers,drifts))
            if (index+1)%9==0:
                print(json.dumps({'QA_profiles_complete':index+1,'wall_seconds':round(time.monotonic()-started,3)}),flush=True)
        require(len(norms_done)==54 and len(seen_trials)==3024,'Independent audit incomplete')
        for path,pin in read_pins.items():
            actual=Path(path)
            require(actual.stat().st_size==pin['bytes'] and sha(actual)==pin['sha256'],'Authenticated input changed during QA')
        require(sha(scope_path)==args.scope_sha256 and sha(go_path)==args.root_go_sha256
                and sha(receipt_path)==args.receipt_sha256 and sha(Path(__file__).resolve())==args.qa_sha256,
                'Frozen authorization/code changed during QA')
        elapsed=time.monotonic()-started;usage=resource.getrusage(resource.RUSAGE_SELF)
        require(elapsed<=WALL_CAP and usage.ru_utime+usage.ru_stime<=CPU_CAP and usage.ru_maxrss*1024<=MEMORY_CAP,
                'Independent audit exceeded frozen resource reservation')
        result={'schema':'SETI_INDEPENDENT_LOCAL_DRIFT_QA_V1',
                'status':'PASS_INDEPENDENT_54_CORES_3149280_ROW_TERMS_1377810_SCORES_486_WINNERS_3024_INJECTIONS',
                'scope_sha256':args.scope_sha256,'qa_code_sha256':args.qa_sha256,
                'producer_receipt_sha256':args.receipt_sha256,'root_go_sha256':args.root_go_sha256,
                'portable_inputs':args.portable_inputs,'actual_input_root':str(source_root),
                'original_scope_input_root':scope['source_root'],'producer_imported':False,
                'authenticated_scope_inputs':114,'normalization_cores':54,'normalization_rows':864,
                'direct501_normalization_core_cells':54*16*4096,'family_row_terms':54*9*405*16,
                'family_window_scores':54*9*405*7,'offset_summaries':486,
                'conditional_injections':3024,'max_normalization_error':max(r['max_absolute_error'] for r in normal_reports),
                'max_family_row_error':max(r['max_row_error'] for r in reports),
                'max_family_score_error':max(r['max_score_error'] for r in reports),
                'max_injection_score_error':max(r['fine_score_error'] for r in injection_reports),
                'all_injection_signal_only_full_capture':sum(r['signal_only_capture_fraction']==1. for r in injection_reports),
                'injected_winner_full_capture':sum(r['fine_winner_capture_fraction']==1. for r in injection_reports),
                'injected_winner_matches_activity_window':sum(r['fine_winner_matches_true_activity_window'] for r in injection_reports),
                'CPU_seconds':usage.ru_utime+usage.ru_stime,'wall_seconds':elapsed,'peak_memory_bytes':usage.ru_maxrss*1024,
                'tolerance_abs':ATOL,'tolerance_rel':RTOL,'qualified_SETI_detection':False,'calibrated_FAP':False,
                'physical_sensitivity':False,'independent_replication':False,
                'normalization_reports':normal_reports,'profile_reports':reports}
        json_out(out/'QA_RECEIPT.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('normalization_reports','profile_reports')},sort_keys=True),flush=True)
    except BaseException as exc:
        json_out(out/'QA_FAILURE.json',{'status':'FAIL_CLOSED_INDEPENDENT_LOCAL_DRIFT_QA',
                                      'error_type':type(exc).__name__,'error':str(exc),
                                      'profiles_complete':len(reports),'injections_complete':len(injection_reports)})
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    main()
