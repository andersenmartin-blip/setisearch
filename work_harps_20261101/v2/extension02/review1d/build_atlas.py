"""Descriptive 1D follow-up of every accepted extension02 event; never assigns origin."""
from pathlib import Path
import sys,csv,json,hashlib,math,collections,datetime
sys.dont_write_bytecode=True
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;EXT=OUT.parent;BASE=EXT.parents[1]
sys.path.insert(0,str(BASE/'code'))
from harps_detector import read_spectrum
PLAN=json.loads((OUT/'PLAN.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def readcsv(p):return list(csv.DictReader(p.open()))
def csvout(p,rows,emptyfields):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else emptyfields);w.writeheader();w.writerows(rows)
def scalar(x):return float(x) if np.isfinite(x) else None
production=EXT/'production';summary=json.loads((production/'SUMMARY.json').read_text())
assert summary['status'].startswith('COMPLETED')
paths={k:BASE/v for k,v in PLAN['inputs'].items() if not k.endswith('sha256') and k not in ['new_spectra']}
for key in ['old_accepted_hits','old_review_index']:assert sha(paths[key])==PLAN['inputs'][key+'_sha256']
start_hashes={k:sha(p) for k,p in paths.items()}
hits=readcsv(paths['new_hits']);dispositions=readcsv(paths['new_dispositions']);oldhits=readcsv(paths['old_accepted_hits']);oldindex=readcsv(paths['old_review_index'])
assert len(oldhits)==333 and len(oldindex)==333
assert len(hits)==summary['v2_hits']==len(dispositions)
assert all(h['status']=='PRELIMINARY_PROFILE_HIT' for h in hits)
assert all(h['origin_status']=='UNREVIEWED' for h in dispositions)
assert [h['candidate_id'] for h in hits]==[h['candidate_id'] for h in dispositions]
assert len({h['candidate_id'] for h in hits})==len(hits)
oldstatuspath=BASE/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv';oldstatus={r['review_id']:r for r in readcsv(oldstatuspath)}
start_hashes['old333_triage_context']=sha(oldstatuspath)
manifest={r['dp_id']:r for r in json.loads(paths['new_manifest'].read_text())};exposures=readcsv(production/'EXPOSURES.csv')
oldbytarget=collections.defaultdict(list)
for n,h in enumerate(oldhits):
    rid=f'V2-{n+1:04d}';idx=oldindex[n]
    assert idx['review_id']==rid and idx['dp_id']==h['dp_id'] and abs(float(idx['fitted_center_bary_air_angstrom'])-float(h['fitted_center_angstrom']))<1e-8
    oldbytarget[h['canonical_target']].append((rid,h,oldstatus[rid]['current_followup_status']))
(OUT/'atlas').mkdir(exist_ok=True);(OUT/'profiles').mkdir(exist_ok=True)
index=[];matches=[];checks={};lastdp=None;profile_data=[]
for n,h in enumerate(hits):
    cid=h['candidate_id'];dp=h['dp_id'];center=float(h['fitted_center_angstrom']);k=int(h['seed_index']);target=h['canonical_target']
    if dp!=lastdp:
        receipt=manifest[dp];path=BASE/receipt['relative_path'];wave,flux,meta=read_spectrum(path)
        assert meta['sha256']==h['input_sha256']==receipt['sha256']
        assert meta['SPECSYS']=='BARYCENT' and 'em.wl' in meta['wavelength_ucd']
        checks[dp]={'input_sha256':meta['sha256'],'relative_path':receipt['relative_path'],'target':target,'date_obs':meta['DATE-OBS'],'berv_km_s':meta['berv_km_s'],'SPECSYS':meta['SPECSYS'],'wavelength_unit':meta['wavelength_unit'],'wavelength_ucd':meta['wavelength_ucd'],'finite_error_samples':meta['finite_error_samples'],'source_samples':len(wave)}
        pitch=float(np.median(np.diff(wave)));lastdp=dp
    off=np.arange(-50,51);ix=k+off;inbounds=(ix>=0)&(ix<len(wave));x=np.full(101,np.nan);raw=np.full(101,np.nan)
    x[inbounds]=wave[ix[inbounds]]-center;raw[inbounds]=flux[ix[inbounds]]
    baseline=float(h['sideband_intercept_adu'])+float(h['sideband_slope_adu_per_pixel'])*off
    scale=float(h['sideband_mad_adu']);usable_scale=math.isfinite(scale) and scale>0
    y=(raw-baseline)/scale if usable_scale else np.full(101,np.nan)
    model=float(h['amplitude_over_sideband_mad'])*np.exp(-.5*(x/(float(h['fwhm_model_angstrom'])/2.354820045))**2)
    gaps=np.flatnonzero(np.diff(x)>1.51*pitch);ploty=y.copy();ploty[gaps+1]=np.nan
    berv=float(meta['berv_km_s']);top=center/(1+berv/299792.458)
    nearest=min([5577.339,6300.304],key=lambda r:abs(top-r));delta=top-nearest;flag=abs(delta)<=.03
    delta6363=top-6363.776;flag6363=abs(delta6363)<=.03
    peers=[]
    for rid,old,prior in oldbytarget[target]:
        difference=center-float(old['fitted_center_angstrom'])
        if abs(difference)<=.03:
            peers.append((rid,old,difference,prior));matches.append({'candidate_id':cid,'old_review_id':rid,'target':target,'new_dp_id':dp,'old_dp_id':old['dp_id'],'new_bary_air_angstrom':center,'old_bary_air_angstrom':float(old['fitted_center_angstrom']),'new_minus_old_angstrom':difference,'old333_triage_status_context_only':prior,'independent_validation':False})
    peers.sort(key=lambda q:(abs(q[2]),q[0]));priority='SIMULTANEOUS_SKY_AND_MULTILINE_CONTEXT' if flag or flag6363 else ('COMPARE_EXISTING_PEERS_AND_NEW_RAW' if peers else 'NEW_RAW_AND_ALL_EPOCH_CONTEXT')
    profile=f'profiles/{cid}.npz';np.savez_compressed(OUT/profile,offset_pixels=off,wavelength_offset_air_angstrom=x,raw_flux_adu=raw,saved_baseline_adu=baseline,residual_over_sideband_mad=y,saved_gaussian_model=model,in_bounds=inbounds,plot_residual_with_gap_breaks=ploty)
    page=n//8+1;panel=n%8+1
    index.append({'candidate_id':cid,'dp_id':dp,'target':target,'date_obs':h['date_obs'],'selection_index':int(h['selection_index']),'seed_index':k,'fitted_center_bary_air_angstrom':center,'berv_km_s':berv,'approx_topocentric_air_angstrom':top,'nearest_original_two_OI_air_angstrom':nearest,'offset_original_two_OI_angstrom':delta,'original_two_OI_0p03_flag':flag,'posthoc_OI6363_offset_angstrom':delta6363,'posthoc_OI6363_0p03_flag':flag6363,'old333_match_count':len(peers),'old333_matched_review_ids':json.dumps([q[0] for q in peers]),'old333_nearest_absolute_offset_angstrom':min((abs(q[2]) for q in peers),default=None),'descriptive_followup_route':priority,'origin_status':'UNREVIEWED','amplitude_over_sideband_mad':float(h['amplitude_over_sideband_mad']),'profile_cosine':float(h['profile_cosine']),'full_101_sample_range_available':bool(inbounds.all()),'valid_flux_samples':int(np.isfinite(raw).sum()),'large_wavelength_gaps':len(gaps),'sideband_mad_positive_finite':usable_scale,'source_finite_error_samples':meta['finite_error_samples'],'atlas_file':f'atlas/ATLAS_{page:03d}.png','panel':panel,'profile_file':profile})
    profile_data.append((x,ploty,model))
    if panel==8 or n==len(hits)-1:
        start=n-panel+1;fig,axes=plt.subplots(4,2,figsize=(13,13));fig.subplots_adjust(left=.07,right=.985,bottom=.045,top=.92,wspace=.22,hspace=.54)
        for j,ax in enumerate(axes.flat):
            if j>=panel:ax.set_visible(False);continue
            rr=index[start+j];xx,yy,gg=profile_data[j]
            ax.plot(xx,yy,'.-',lw=.8,ms=2,color='#315a79');ax.plot(xx,gg,lw=1.1,color='#ce7832')
            ax.axvspan(xx[38],xx[62],color='grey',alpha=.08);ax.axhline(0,color='black',lw=.4);ax.set_xlim(-.5,.5)
            ax.set_title(f"{rr['candidate_id']} · {rr['target']} · {rr['date_obs'][:10]}\n{rr['fitted_center_bary_air_angstrom']:.4f} Å bary · A/MAD {rr['amplitude_over_sideband_mad']:.1f} · cosine {rr['profile_cosine']:.2f}",fontsize=9)
            ax.set_xlabel('Barycentric air wavelength offset (Å)',fontsize=8);ax.set_ylabel('Residual / sideband MAD',fontsize=8);ax.tick_params(labelsize=8)
        fig.suptitle(f'Extension02 · every accepted V2 event · page {page}/{(len(hits)+7)//8} · all UNREVIEWED\nSaved residual and fixed model; scores are not calibrated significance.',fontsize=12)
        fig.savefig(OUT/f'atlas/ATLAS_{page:03d}.png',dpi=110);plt.close(fig);profile_data=[]
        print(f'page {page}: candidates {start+1}–{n+1}',flush=True)
csvout(OUT/'REVIEW_INDEX.csv',index,['candidate_id','origin_status']);csvout(OUT/'OLD_MATCHES.csv',matches,['candidate_id','old_review_id','new_minus_old_angstrom'])
targetcounts=[]
for target in sorted({r['canonical_target'] for r in exposures}):
    rr=[r for r in index if r['target']==target];ee=[r for r in exposures if r['canonical_target']==target]
    targetcounts.append({'target':target,'analyzed_exposures':len(ee),'exposures_with_V2_hits':len({r['dp_id'] for r in rr}),'accepted_V2_events':len(rr),'events_with_old333_match':sum(r['old333_match_count']>0 for r in rr),'original_two_OI_flags':sum(r['original_two_OI_0p03_flag'] for r in rr),'posthoc_OI6363_flags':sum(r['posthoc_OI6363_0p03_flag'] for r in rr)})
csvout(OUT/'TARGET_COUNTS.csv',targetcounts,['target','accepted_V2_events'])
exposurecounts=[]
for e in exposures:
    rr=[r for r in index if r['dp_id']==e['dp_id']];assert len(rr)==int(e['v2_hits'])
    exposurecounts.append({'dp_id':e['dp_id'],'target':e['canonical_target'],'date_obs':e['date_obs'],'accepted_V2_events':len(rr),'original_two_OI_flags':sum(r['original_two_OI_0p03_flag'] for r in rr),'posthoc_OI6363_flags':sum(r['posthoc_OI6363_0p03_flag'] for r in rr),'events_with_old333_match':sum(r['old333_match_count']>0 for r in rr)})
csvout(OUT/'EXPOSURE_COUNTS.csv',exposurecounts,['dp_id','accepted_V2_events'])
bins=collections.Counter(math.floor(r['fitted_center_bary_air_angstrom']/100)*100 for r in index)
csvout(OUT/'WAVELENGTH_COUNTS.csv',[{'bin_lower_inclusive_air_angstrom':k,'bin_upper_exclusive_air_angstrom':k+100,'accepted_V2_events':v} for k,v in sorted(bins.items())],['bin_lower_inclusive_air_angstrom','bin_upper_exclusive_air_angstrom','accepted_V2_events'])
assert len(index)==len(hits) and {r['candidate_id'] for r in index}=={r['candidate_id'] for r in hits}
assert all(sha(p)==start_hashes[k] for k,p in paths.items()) and sha(oldstatuspath)==start_hashes['old333_triage_context']
dump(OUT/'INPUT_CHECKS.json',{'input_hashes':start_hashes,'unique_spectra':checks,'all_inputs_unchanged':True,'all_production_statuses_preserved':True,'plan_sha256':sha(OUT/'PLAN.json'),'script_sha256':sha(Path(__file__))})
dump(OUT/'ATLAS_SUMMARY.json',{'status':'COMPLETE_DESCRIPTIVE_ATLAS_VISUAL_REVIEW_PENDING','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'accepted_events':len(index),'panels':len(index),'pages':(len(index)+7)//8,'analyzed_exposures':len(exposures),'exposures_with_hits':len(checks),'targets_analyzed':len(targetcounts),'targets_with_hits':sum(r['accepted_V2_events']>0 for r in targetcounts),'events_with_old333_match':sum(r['old333_match_count']>0 for r in index),'old333_match_pairs':len(matches),'original_two_OI_flag_count':sum(r['original_two_OI_0p03_flag'] for r in index),'posthoc_OI6363_flag_count':sum(r['posthoc_OI6363_0p03_flag'] for r in index),'followup_route_counts':dict(collections.Counter(r['descriptive_followup_route'] for r in index)),'missing_ranges':sum(not r['full_101_sample_range_available'] for r in index),'invalid_scale_count':sum(not r['sideband_mad_positive_finite'] for r in index),'all_origin_statuses':'UNREVIEWED','interpretation':'Complete descriptive first pass, not raw-pixel validation. Old accepted-hit proximity and OI proximity cannot identify origin or establish independent repetition. No all-epoch or calibrated-significance claim.'})
