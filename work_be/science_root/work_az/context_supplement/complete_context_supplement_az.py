"""Exhaustive posthoc context for dynamically discovered pending AZ groups.

Main AZ grouping, representatives, selection, flags and prior controls are immutable.
"""
from pathlib import Path
import argparse,copy,datetime,hashlib,json,os,sys
sys.dont_write_bytecode=True
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
B=Path(__file__).resolve().parent;P=B.parent;W=P.parent
sys.path.insert(0,str(P/'runtime'));sys.path.insert(0,str(P/'followup'))
sys.path.insert(0,str(B))
import publication
import numpy as np
assert np.__version__=='2.3.5'
import followup_az as inherited
from continuous_normalization_ac import normalize
PLAN=B/'PLAN_FROZEN_CONTEXT_SUPPLEMENT_AZ.json'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def new(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def arrays(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def identity(x):return x['namespace'],x['class'],int(x['group_id'])
def groupmap(grouping):
    out={}
    for namespace,field in [('all3ON','all3ON_groups'),('intermittent1or2ON','intermittent_groups')]:
        for g in grouping[field]:
            k=(namespace,g['class'],int(g['group_id']));assert k not in out;out[k]=g
    return out
def token(k):return f'{k[0]}_{k[1]}_{k[2]:04d}'
def inputs():
    paths=[Path(__file__),B/'plot_context_supplement_az.py',B/'publication.py',B/'review/audit_context_supplement_az.py',P/'PROTOCOL_BOUND_AZ.json',P/'RUNTIME_AZ.json',P/'followup/results/FOLLOWUP_RESULT_AZ.json',P/'followup/results/GROUPING_AZ.json',P/'followup/INDEPENDENT_FOLLOWUP_REVIEW_AZ.json',P/'followup/FOLLOWUP_ACTUAL_EXIT_AZ.json',P/'followup/FOLLOWUP_REVIEW_ACTUAL_EXIT_AZ.json',P/'review/NUMERIC_ACTUAL_EXIT_AZ.json',P/'review/INDEPENDENT_DETECTOR_AZ.json',P/'followup/followup_az.py',P/'followup/continuous_normalization_ac.py',P/'followup/inherited_grouping_ab.py',P/'followup/review_source/oracles_independent_ad.py',P/'results/all_ON_forced_triage.npz']
    paths += [P/f'results/scan{j}_grid.npz' for j in range(6)]
    return {str(p):sha(p) for p in paths}
def main_closure():
    result=P/'followup/results/FOLLOWUP_RESULT_AZ.json';numeric=P/'review/INDEPENDENT_DETECTOR_AZ.json';review=P/'followup/INDEPENDENT_FOLLOWUP_REVIEW_AZ.json'
    assert read(result)['status']=='COMPLETE' and read(review)['result_sha256']==sha(result)
    for path in (numeric,review):assert read(path)['status']=='PASS'
    for receipt,bound in [(P/'followup/FOLLOWUP_ACTUAL_EXIT_AZ.json',result),(P/'followup/FOLLOWUP_REVIEW_ACTUAL_EXIT_AZ.json',review),(P/'review/NUMERIC_ACTUAL_EXIT_AZ.json',numeric)]:
        r=read(receipt);assert r['actual_exit_code']==0 and r.get('background_jobs_running',False) is False and r['result_sha256']==sha(bound),receipt
    return True
def publish(path,values):
    receipt=publication.publish_npz(values,path);rp=Path(path).with_suffix('.publication.json');new(rp,receipt)
    return {'path':str(path),'sha256':sha(path),'bytes':Path(path).stat().st_size,'publication_receipt_path':str(rp),'publication_receipt_sha256':sha(rp)}
def freeze():
    main_closure()
    main=read(P/'followup/results/FOLLOWUP_RESULT_AZ.json');g=groupmap(read(P/'followup/results/GROUPING_AZ.json'));queue=main['local_context_backlog'];assert len({identity(x) for x in queue})==len(queue)
    assert set(g)=={identity(x) for x in queue}
    for item in queue:assert g[identity(item)]['representative_global_seed_row']==item['representative_global_seed_row']
    pending=sorted([copy.deepcopy(x) for x in queue if not x['bounded_local_context_completed']],key=identity)
    choices=[]
    for source in (0,2,4):
        candidates=[x for x in pending if g[identity(x)]['representative']['source_scan']==source]
        if candidates:choices.append(identity(max(candidates,key=lambda x:(g[identity(x)]['representative']['source_ESS'],-x['representative_global_seed_row']))))
    for operator in (min,max):
        if pending:choices.append(identity(operator(pending,key=lambda x:g[identity(x)]['representative']['frequency_at_midpoint_mhz'])))
    plots=list(dict.fromkeys(choices))[:4];pins=inputs();runtime=read(P/'RUNTIME_AZ.json')
    assert runtime['modules']['numpy']['version']=='2.3.5'
    plan={'schema':'SETI_AZ_POSTHOC_PENDING_CONTEXT_PLAN_V1','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':main['target'],'primary_id':main['primary_id'],'timing':'Explicitly posthoc to AZ powers, AZ outcomes and reviewed main followup. Every remaining main-queue identity is frozen before this supplementary measurement. No prospective-before-power claim.','source_and_input_sha256':pins,'parent_local_context_backlog':copy.deepcopy(queue),'pending_identities':pending,'parent_total_groups':len(queue),'parent_completed_before':sum(x['bounded_local_context_completed'] for x in queue),'pending_group_count':len(pending),'plot_identities':[list(x) for x in plots],'selection':'Every remaining inherited current AZ group; unchanged namespace/class/groupid/member set and unchanged representative. Dynamic counts including zero. No new ranking, threshold, origin veto or backfill.','window':'Union of six projected midpoint centers and six metadata-mapped fixed-frequency centers, pad1024channels each side, nativeclip; all16rows/sixscans.','normalization':'Exact current AZ runtime NumPy2.3.5 and unchanged AC full-native normalization4096 before crop.','measurements':'Inherited scalar per-row math.fsum original integer tracks and width/rate calibration; same-width zero-drift fixed control explicitly posthoc/descriptive; no automatic veto or origin assignment.','figure_selection':'At most4identities: max-sourceESS pending representative per source scan0/2/4, then lowest/highest sourcefrequency across allpending, deduplicated in order then capped at4; all numeric contexts retained. FULL and±32nativechannel ZOOM,display−2..15.','zero_pending_contract':'Freeze and produce reviewed no-op overlay retaining original queue exactly; no native/triage NPZ loads or arrays/figures manufactured. Explicit zero-track and zero-pixel review.','publication':'Exact pinned AQ detector publication.py: create and close each NPZ/PNG in private /tmp, fsync, verify typed arrays or full decoded pixels and stable inode/size/hash, then exclusive distinct-inode copy to canonical destination and revalidate. Each success receipt retained. Failure preserves evidence; no automatic repair, overwrite or retry.','preserve':'All main grouping/memberships/representatives/flags/counts/topselection and original prospectively defined controls unchanged. Parent files remain read-only.','new_examined_MHz_visits':0,'new_independent_epochs':0,'accepted_SETI_candidates':0,'physical_origin':'UNRESOLVED'}
    new(PLAN,plan);print(json.dumps({'status':'FROZEN','pending':len(pending),'total_groups':len(queue),'plot_count':len(plots),'plan_sha256':sha(PLAN)}),flush=True)
def run():
    main_closure();plan=read(PLAN)
    for path,digest in plan['source_and_input_sha256'].items():assert sha(path)==digest,path
    protocol=P/'PROTOCOL_BOUND_AZ.json';p=read(protocol);scopes=p['scans'];main=read(P/'followup/results/FOLLOWUP_RESULT_AZ.json');groups=groupmap(read(P/'followup/results/GROUPING_AZ.json'));out=B/'results'
    assert main['target']==plan['target']==p['target'] and main['primary_id']==plan['primary_id']==p['primary_id']
    assert main['local_context_backlog']==plan['parent_local_context_backlog']
    assert read(P/'review/INDEPENDENT_DETECTOR_AZ.json')['status']=='PASS' and read(P/'followup/INDEPENDENT_FOLLOWUP_REVIEW_AZ.json')['status']=='PASS'
    out.mkdir(exist_ok=False);records=[];local=[];nativepins={};maxerr=0.;t=None
    if plan['pending_identities']:t=arrays(P/'results/all_ON_forced_triage.npz')
    for number,pending in enumerate(plan['pending_identities'],1):
        k=identity(pending);group=copy.deepcopy(groups[k]);assert group['representative_global_seed_row']==pending['representative_global_seed_row'];rep=group['representative'];centers=rep['projected_centers_six_scans'];fixed=[inherited.fixed_geometry(rep,scopes,j)[1] for j in range(6)]
        lo=max(0,min(centers+fixed)-1024);hi=min(scopes[0]['nchannels'],max(centers+fixed)+1025)
        records.append({'selection_number':number,'identity':list(k),'origin':k[0],'group':group,'window_lo':lo,'window_hi_exclusive':hi,'fixed_frequency_MHz':inherited.fixed_geometry(rep,scopes,rep['source_scan'])[0],'fixed_centers_six_scans':fixed,'array_filename':f'CONTEXT_{token(k)}_SIX_SCAN_ARRAYS_AZ.npz','scans':[]});local.append({})
    for s in scopes if records else []:
        j=s['scan'];native=Path(p['root'])/s['native_path'];assert sha(native)==s['input_sha256'];nativepins[str(native)]=s['input_sha256'];raw=np.load(native,mmap_mode='r',allow_pickle=False);y,_=normalize(raw,4096);grid=arrays(P/f'results/scan{j}_grid.npz')
        for idx,rec in enumerate(records):
            rep=rec['group']['representative'];row=rec['group']['representative_global_seed_row'];width=rep['width_channels'];ri=rep['drift_index'];center=int(t['predicted_center'][row,j]);lo=rec['window_lo'];hi=rec['window_hi_exclusive']
            offsets=np.rint(rep['drift_hz_s']*(np.arange(16)-7.5)*s['dt_seconds']/s['df_hz']).astype(np.int32);assert np.array_equal(offsets,grid['offsets'][ri]) and grid['drift_hz_s'][ri]==rep['drift_hz_s'];ch=center+offsets;assert int(ch.min())-width//2>=lo and int(ch.max())+width//2<hi
            vals=np.asarray(raw[:,lo:hi]).copy();norm=np.asarray(y[:,lo:hi]).copy();nr=inherited.row_metrics(norm,ch,width,lo);rr=inherited.row_metrics(vals,ch,width,lo);cal=grid[f'calibration_width_{width}'][ri];score=(nr['total']-float(cal[0]))/float(cal[1]);ref=float(t['forced_center_ess'][row,j]);err=abs(score-ref);assert err<=1e-4+5e-6*abs(ref);maxerr=max(maxerr,err)
            local[idx].update({f'raw_scan{j}':vals,f'normalized_scan{j}':norm,f'original_integer_channels_scan{j}':ch,f'normalized_row_contributions_scan{j}':np.asarray(nr['row_contributions']),f'raw_row_contributions_scan{j}':np.asarray(rr['row_contributions'])})
            companion,fixedchannels=inherited.fixed_companion(raw,y,grid,rep,scopes,j);companion.update(inherited_fixed_companion_rule_frozen_before_current_target_powers=False,prospective_before_AZ_powers=False,supplementary_plan_frozen_before_this_run=True,timing_disclosure='Posthoc supplementary control after AZ powers/outcomes; exhaustive remaining queue fixed before this run.')
            # No inherited prospective flag may describe this new supplementary control.
            for flag in list(companion):
                if flag.startswith('prospective_before_') and flag.endswith('_powers'):companion[flag]=False
            local[idx][f'fixed_integer_channels_scan{j}']=fixedchannels
            if companion['status']=='MEASURED':local[idx][f'fixed_normalized_row_contributions_scan{j}']=np.asarray(companion['normalized_track']['row_contributions']);local[idx][f'fixed_raw_row_contributions_scan{j}']=np.asarray(companion['raw_track']['row_contributions'])
            rec['scans'].append({'scan':j,'role':s['role'],'fch1_mhz':s['fch1_mhz'],'df_hz':s['df_hz'],'dt_seconds':s['dt_seconds'],'fixed_frequency_companion':companion,'normalized_original_track':nr,'raw_original_track':rr,'calibration_median':float(cal[0]),'calibration_scale':float(cal[1]),'recovered_ESS':score,'forced_center_ESS':ref,'absolute_ESS_error':err})
        del raw,y,grid;print(json.dumps({'scan':j,'groups_measured':len(records)}),flush=True)
    publications=[]
    for idx,rec in enumerate(records):local[idx]['native_channels']=np.arange(rec['window_lo'],rec['window_hi_exclusive'],dtype=np.int32);publications.append(publish(out/rec['array_filename'],local[idx]));local[idx]=None
    overlay=copy.deepcopy(main['local_context_backlog']);completed={tuple(rec['identity']) for rec in records}
    for item in overlay:
        if identity(item) in completed:item['bounded_local_context_completed']=True
    assert len(overlay)==plan['parent_total_groups'] and all(x['bounded_local_context_completed'] for x in overlay)
    for path,digest in {**plan['source_and_input_sha256'],**nativepins}.items():assert sha(path)==digest,path
    result={'schema':'SETI_AZ_POSTHOC_CONTEXT_SUPPLEMENT_RESULT_V1','status':'COMPLETE','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':plan['target'],'primary_id':plan['primary_id'],'plan_sha256':sha(PLAN),'protocol_sha256':sha(protocol),'publication_source_sha256':sha(B/'publication.py'),'parent_followup_result_sha256':sha(P/'followup/results/FOLLOWUP_RESULT_AZ.json'),'parent_grouping_sha256':sha(P/'followup/results/GROUPING_AZ.json'),'selected_representatives':records,'supplementary_group_count':len(records),'parent_total_groups':len(overlay),'parent_pending_groups_before':plan['pending_group_count'],'parent_previously_completed_identities':[list(identity(x)) for x in main['local_context_backlog'] if x['bounded_local_context_completed']],'current_parent_groups_completed_after_overlay':len(overlay),'current_parent_groups_pending_after_overlay':0,'pending_groups_after_overlay':0,'all_groups_completed_after_overlay':len(overlay),'local_context_backlog_overlay':overlay,'local_track_checks':6*len(records),'fixed_frequency_companion_checks':sum(s['fixed_frequency_companion']['status']=='MEASURED' for rec in records for s in rec['scans']),'maximum_selected_track_ESS_error':maxerr,'publications':publications,'input_sha256_verified_before_after':{**plan['source_and_input_sha256'],**nativepins},'zero_pending_noop':not records,'target_NPZ_and_native_arrays_loaded':bool(records),'parent_scientific_flags_counts_grouping_representatives_and_selection_changed':False,'parent_scientific_flags_counts_grouping_and_selection_changed':False,'new_examined_MHz_visits':0,'new_independent_epochs':0,'accepted_SETI_candidates':0,'physical_origin':'UNRESOLVED','limits':['Posthoc supplementary bounded context only. Main AZ flags/counts/grouping/selection and original prospectivecontrols unchanged.','Only current AZ pending context closed; no claim all earlier project queues complete.','Empirical scores are not Gaussian significance or calibrated search-wide FAP.','Fixed-frequency controls are descriptive, without origin assignment or automatic veto.','No added coverage/IDs, observingtime, independentepoch, sensitivityqualification or candidatecredit.']}
    new(out/'FOLLOWUP_RESULT_CONTEXT_SUPPLEMENT_AZ.json',result);print(json.dumps({'status':'COMPLETE','groups':len(records),'total_groups':len(overlay),'tracks':6*len(records),'maximum_ESS_error':maxerr,'result_sha256':sha(out/'FOLLOWUP_RESULT_CONTEXT_SUPPLEMENT_AZ.json')}),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','run']);args=parser.parse_args();freeze() if args.action=='freeze' else run()
