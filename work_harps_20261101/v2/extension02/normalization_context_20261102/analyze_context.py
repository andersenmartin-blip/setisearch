"""Bounded unnormalized context from frozen archived profiles and exact original inputs."""
from pathlib import Path
import csv,datetime,hashlib,io,json,subprocess,tarfile
import numpy as np
from astropy.io import fits
OUT=Path(__file__).resolve().parent;EXT=OUT.parent;C=299792.458

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(p.open()))
def dump(name,obj):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def csvout(name,data):
 with(OUT/name).open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in data for k in r)));w.writeheader();w.writerows(data)
def finite(x):return float(x)if np.isfinite(x)else None
def mad(a):return 1.4826*np.median(np.abs(a-np.median(a)))
def corr(a,b,mask):
 a=np.asarray(a)[mask];b=np.asarray(b)[mask];a=a-a.mean();b=b-b.mean();den=np.sqrt(np.dot(a,a)*np.dot(b,b));return float(np.dot(a,b)/den)if den else None
def poly(header,prefix,degree,order,x):return np.polynomial.polynomial.polyval(x,[header[f'{prefix}{order*(degree+1)+j}']for j in range(degree+1)])
def summary(a):
 a=np.asarray(a);a=a[np.isfinite(a)];return {'samples':int(len(a)),'minimum':float(a.min()),'p10':float(np.quantile(a,.1)),'median':float(np.median(a)),'p90':float(np.quantile(a,.9)),'maximum':float(a.max()),'nonpositive_samples':int(np.sum(a<=0))}
def main():
 assert not(OUT/'SUMMARY.json').exists(),'No replacement of completed output'
 plan=json.loads((OUT/'PLAN.json').read_text());freeze=json.loads((OUT/'FREEZE.json').read_text())
 for name,h in freeze['local_source_hashes'].items():assert sha(OUT/name)==h,name
 for name,h in plan['source_hashes'].items():assert sha(EXT/name)==h,name
 selected=rows(OUT/'inputs/SELECTED_EPOCH_PROFILES.csv');focused=rows(OUT/'inputs/FOCUSED_EPOCH_PROFILES.csv');products=json.loads((OUT/'SOURCE_PRODUCTS.json').read_text())['products']
 for r in products:assert(OUT/r['local_path']).stat().st_size==r['bytes']and sha(OUT/r['local_path'])==r['sha256']
 arrays={};profilemetrics=[]
 for r in selected:
  p=OUT/'inputs'/r['profile_path'];assert sha(p)==r['profile_sha256']
  with np.load(p,allow_pickle=False)as z:arr={k:z[k].copy()for k in z.files}
  assert all(len(a)==201 for a in arr.values());key=(r['candidate_id'],r['dp_id'],r['frame']);arrays[key]=arr
 for r in selected:
  key=(r['candidate_id'],r['dp_id'],r['frame']);a=arrays[key];ref=arrays[(r['candidate_id'],r['source_dp_id'],r['frame'])];reference=next(z for z in selected if(z['candidate_id'],z['dp_id'],z['frame'])==(r['candidate_id'],r['source_dp_id'],r['frame']))
  n=float(r['normalization_adu']);nr=float(reference['normalization_adu']);x=a['offset_air_angstrom'];core=np.abs(x)<=.250000001
  rawbg=a['linear_background']*n;rawres=a['raw_flux']-rawbg;refr=ref['raw_flux']-ref['linear_background']*nr
  normalized=corr(a['residual'],ref['residual'],core);unnormalized=corr(rawres,refr,core)
  row={k:r[k]for k in ['candidate_id','dp_id','source_dp_id','date_obs','frame','is_discovery_exposure','local_continuum_low','normalization_adu','first_difference_noise_proxy_adu','correlation_to_discovery']}
  row.update(normalization_to_noise_proxy=n/float(r['first_difference_noise_proxy_adu']),raw_flux_nonpositive=int(np.sum(a['raw_flux']<=0)),raw_flux_min=float(a['raw_flux'].min()),raw_flux_median=float(np.median(a['raw_flux'])),raw_flux_max=float(a['raw_flux'].max()),normalized_flux_identity_max_abs=float(np.max(abs(a['normalized_flux']-a['raw_flux']/n))),residual_identity_max_abs=float(np.max(abs(a['residual']-(a['raw_flux']/n-a['linear_background'])))),raw_scaled_residual_identity_max_abs=float(np.max(abs(rawres-a['residual']*n))),recomputed_normalized_correlation=normalized,recomputed_unnormalized_correlation=unnormalized,pearson_invariance_abs_error=abs(normalized-unnormalized),saved_correlation_abs_error=abs(normalized-float(r['correlation_to_discovery'])),half_normalizer_correlation=corr(rawres/(.5*n),refr/nr,core),double_normalizer_correlation=corr(rawres/(2*n),refr/nr,core),normalized_core_residual_rms=float(np.sqrt(np.mean(a['residual'][core]**2))),raw_core_residual_rms=float(np.sqrt(np.mean(rawres[core]**2))),narrow_template_amplitude_adu=float(r['narrow_amplitude'])*n,narrow_template_residual_rms_adu=float(r['narrow_residual_rms'])*n)
  profilemetrics.append(row)
 csvout('PROFILE_DIAGNOSTICS.csv',profilemetrics)
 (OUT/'derived').mkdir();merged=[];native=[];inputaudit=[]
 for dp in sorted({r['dp_id']for r in focused}):
  prods={r['kind']:r for r in products if r['dp_id']==dp};science=prods['SCIENCE'];sciencepath=OUT/science['local_path']
  with fits.open(sciencepath,memmap=False)as hd:
   ph=hd[0].header;eh=hd[1].header;w=np.asarray(hd[1].data['WAVE'][0],float);f=np.asarray(hd[1].data['FLUX'][0],float);err=np.asarray(hd[1].data['ERR'][0],float)
   assert ph['SPECSYS']=='BARYCENT' and eh['TUNIT1']=='angstrom' and ph['DATE-OBS']==science['primary_header']['DATE-OBS'];berv=float(ph['ESO DRS BERV'])
  rawprod=prods['RAW'];anc=prods['ANCILLARY'];rawbytes=subprocess.run(['gzip','-cd',str(OUT/rawprod['local_path'])],capture_output=True,check=True).stdout
  with fits.open(io.BytesIO(rawbytes),memmap=False)as hd:
   rh=hd[0].header;assert rh['ARCFILE'].removesuffix('.fits')==rawprod['raw_id']and rh['DATE-OBS']==ph['DATE-OBS'];raw=np.hstack([hd[1].data[:,50:2098],hd[2].data[:,50:2098]]).astype(float)
  with tarfile.open(OUT/anc['local_path'])as archive:
   members=[m for m in archive if m.name.endswith('_e2ds_A.fits')];assert len(members)==1 and Path(members[0].name).name==anc['raw_id']+'_e2ds_A.fits'
   with fits.open(io.BytesIO(archive.extractfile(members[0]).read()),memmap=False)as hd:nh=hd[0].header;nf=hd[0].data.astype(float)
  assert nh['DATE-OBS']==ph['DATE-OBS'] and abs(float(nh['ESO DRS BERV'])-berv)<1e-8 and nf.shape==(72,4096) and raw.shape==(4096,4096)
  oldmap=json.loads((EXT/rawprod['historical_batch']/'NATIVE_MAPPING.json').read_text());prior=next(s for s in oldmap['spectra']if s['dp_id']==dp);orient=prior['grid_best'];assert prior['raw_sha256']==rawprod['sha256'] and prior['ancillary_sha256']==anc['sha256']
  degree=int(nh['ESO DRS CAL TH DEG LL']);trace_degree=int(nh['ESO DRS CAL LOC DEG CTR']);pixels=np.arange(4096);waves=np.array([poly(nh,'ESO DRS CAL TH COEFF LL',degree,o,pixels)for o in range(72)])
  inputaudit.append({'dp_id':dp,'science_sha256':science['sha256'],'raw_sha256':rawprod['sha256'],'ancillary_sha256':anc['sha256'],'native_member':members[0].name,'berv_km_s':berv,'grid_orientation':orient,'new_global_fit':False,'independent_origin_assignment':False})
  spacing=np.median(np.diff(w))
  for r in [r for r in focused if r['dp_id']==dp]:
   cb=float(r['center_sampled_bary_air_angstrom']);ct=cb/(1+berv/C);mask=(abs(w-cb)<=2)&np.isfinite(f);pairs=(abs(w[:-1]-cb)<=2)&np.isfinite(f[:-1])&np.isfinite(f[1:])&(np.diff(w)<1.51*spacing);norm=float(np.median(f[mask]));noise=float(mad(np.diff(f)[pairs])/np.sqrt(2));label=r['candidate_id']+'_'+dp.replace(':','_')+'_'+r['frame'];arr=arrays[(r['candidate_id'],dp,r['frame'])]
   outpath=OUT/'derived'/(label+'_merged.npz');np.savez_compressed(outpath,wavelength_bary_air_angstrom=w[mask],raw_flux=f[mask],ERR=err[mask],profile_offset=arr['offset_air_angstrom'],profile_raw_flux=arr['raw_flux'],raw_linear_background=arr['linear_background']*norm,raw_residual=arr['residual']*norm)
   s=summary(f[mask]);record={k:r[k]for k in ['candidate_id','dp_id','frame','is_discovery_exposure','local_continuum_low']};record.update(center_sampled_bary_air_angstrom=cb,center_native_topocentric_air_angstrom=ct,normalization_adu=norm,first_difference_noise_proxy_adu=noise,normalization_to_noise_proxy=norm/noise,normalization_difference_from_saved=norm-float(r['normalization_adu']),noise_difference_from_saved=noise-float(r['first_difference_noise_proxy_adu']),finite_positive_ERR=int(np.sum(np.isfinite(err[mask])&(err[mask]>0))),left_side_median_adu=float(np.median(f[(w>=cb-2)&(w<cb-1)])),right_side_median_adu=float(np.median(f[(w>cb+1)&(w<=cb+2)])),**{f'window_{k}':v for k,v in s.items()},derived_path=str(outpath.relative_to(OUT)),derived_sha256=sha(outpath));merged.append(record)
   covering=np.flatnonzero((waves[:,0]<ct)&(waves[:,-1]>ct))
   for order in covering:
    o=int(order);k=int(np.argmin(abs(waves[o]-ct)));rr=4095-k if orient['row_flip']else k;arg=4095-k if orient['argument_flip']else k;col=float(poly(nh,'ESO DRS CAL LOC CTR',trace_degree,o,arg));col=4095-col if orient['column_flip']else col;cc=round(col);nm=(abs(waves[o]-ct)<=2)&np.isfinite(nf[o]);nd=np.diff(nf[o]);pairsm=(abs(waves[o,:-1]-ct)<=2)&np.isfinite(nd);native_med=float(np.median(nf[o,nm]));native_noise=float(mad(nd[pairsm])/np.sqrt(2));cut=raw[rr-15:rr+16,cc-16:cc+17].copy();assert cut.shape==(31,33);bg=np.median(cut[np.r_[0:10,21:31]],axis=0);excess=cut-bg[None,:]
    dest=OUT/'derived'/(label+f'_o{o:02d}.npz');np.savez_compressed(dest,native_wave=waves[o,nm],native_flux=nf[o,nm],raw_cutout=cut,raw_background=bg,raw_excess=excess,center_topocentric=np.array(ct),raw_trace_column=np.array(col),raw_row=np.array(rr))
    center_columns=abs(np.arange(-16,17)-(col-cc))<=2;core=np.arange(31)>=13;core&=np.arange(31)<=17
    nrec={k:record[k]for k in ['candidate_id','dp_id','frame','is_discovery_exposure','local_continuum_low']};nrec.update(order=o,covering_orders_count=int(len(covering)),center_topocentric_air_angstrom=ct,native_pixel=k,raw_row=rr,raw_column=col,native_median_adu=native_med,native_noise_proxy_adu=native_noise,native_median_to_noise_proxy=native_med/native_noise,**{f'native_{name}':v for name,v in summary(nf[o,nm]).items()},raw_center_median_adu=float(np.median(cut[np.ix_(core,center_columns)])),raw_side_background_median_adu=float(np.median(bg[center_columns])),raw_center_excess_median_adu=float(np.median(excess[np.ix_(core,center_columns)])),raw_center_excess_max_adu=float(excess[np.ix_(core,center_columns)].max()),prior_global_correlation=orient['median_correlation'],diagnostic_only_no_new_mapping_gate=True,derived_path=str(dest.relative_to(OUT)),derived_sha256=sha(dest));native.append(nrec)
 csvout('MERGED_WINDOW_DIAGNOSTICS.csv',merged);csvout('NATIVE_ORDER_DIAGNOSTICS.csv',native);dump('INPUT_IDENTITY_CHECKS.json',inputaudit)
 checks={'profile_normalized_identity_max_abs':max(r['normalized_flux_identity_max_abs']for r in profilemetrics),'profile_residual_identity_max_abs':max(r['residual_identity_max_abs']for r in profilemetrics),'raw_scaled_residual_identity_max_abs':max(r['raw_scaled_residual_identity_max_abs']for r in profilemetrics),'pearson_invariance_max_abs':max(r['pearson_invariance_abs_error']for r in profilemetrics),'original_correlation_reproduction_max_abs':max(r['saved_correlation_abs_error']for r in profilemetrics),'normalization_difference_max_abs':max(abs(r['normalization_difference_from_saved'])for r in merged),'noise_difference_max_abs':max(abs(r['noise_difference_from_saved'])for r in merged)}
 assert checks['pearson_invariance_max_abs']<1e-12 and checks['original_correlation_reproduction_max_abs']<1e-12 and checks['normalization_difference_max_abs']<1e-12 and checks['noise_difference_max_abs']<1e-12
 for name,h in plan['source_hashes'].items():assert sha(EXT/name)==h,name
 dump('SUMMARY.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'COMPLETE_DESCRIPTIVE_NORMALIZATION_CONTEXT','events':2,'archived_profiles':len(profilemetrics),'focused_profiles':len(merged),'focused_exposures':len(inputaudit),'native_order_contexts':len(native),'low_profiles':[{'candidate_id':r['candidate_id'],'dp_id':r['dp_id'],'frame':r['frame'],'norm_to_noise':r['normalization_to_noise_proxy']}for r in profilemetrics if r['local_continuum_low']=='True'],'discovery_low_flags':sum(r['local_continuum_low']=='True'and r['is_discovery_exposure']=='True'for r in profilemetrics),'checks':checks,'original_U_labels_changed':0,'new_origin_assignments':0,'new_observations':0,'rerun_original_4370_pipeline':False,'input_source_hashes_unchanged':True,'plan_sha256':sha(OUT/'PLAN.json'),'script_sha256':sha(Path(__file__)),'limits':plan['limitations']})
 print(json.dumps({'profiles':len(profilemetrics),'focused':len(merged),'native_order_contexts':len(native),'checks':checks},indent=2))
if __name__=='__main__':main()
