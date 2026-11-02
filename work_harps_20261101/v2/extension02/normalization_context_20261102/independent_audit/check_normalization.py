"""Independent scalar normalization and original-source integrity audit.

No production analysis functions imported. Closed-form sideband least-squares,
centered-dot Pearson and scalar medians/MAD reconstruct stored profile algebra.
Direct-power polynomials reconstruct focused native wavelengths and traces.
"""
from pathlib import Path
import json,csv,hashlib,math,statistics,subprocess,io,tarfile,datetime
import numpy as np
from astropy.io import fits
OUT=Path(__file__).resolve().parent;CONTEXT=OUT.parent;EXT=CONTEXT.parent
EXPECTED_PLAN='16e85105173f77fe3a41be5b45dccce4e80474b8655aad1894df9da2b59c92a6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def med(a):return statistics.median(float(x) for x in a)
def mad(a):
 a=[float(x) for x in a if math.isfinite(float(x))]
 m=med(a);return 1.4826*med([abs(x-m) for x in a])
def pearson(a,b):
 pairs=[(float(x),float(y)) for x,y in zip(a,b) if math.isfinite(float(x)) and math.isfinite(float(y))]
 if len(pairs)<20:return None
 mx=math.fsum(x for x,y in pairs)/len(pairs);my=math.fsum(y for x,y in pairs)/len(pairs)
 xx=math.fsum((x-mx)**2 for x,y in pairs);yy=math.fsum((y-my)**2 for x,y in pairs)
 return math.fsum((x-mx)*(y-my) for x,y in pairs)/math.sqrt(xx*yy) if xx>0 and yy>0 else None
def poly(h,prefix,degree,order,x):
 return sum(float(h[prefix+str(order*(degree+1)+j)])*x**j for j in range(degree+1))
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def main():
 assert sha(CONTEXT/'PLAN.json')==EXPECTED_PLAN
 plan=json.loads((CONTEXT/'PLAN.json').read_text())
 for rel,digest in plan['source_hashes'].items():assert sha(EXT/rel)==digest,rel
 rows=[r for r in csv.DictReader((EXT/'epoch_followup/ALL_EPOCH_MEASUREMENTS.csv').open()) if r['candidate_id'] in plan['event_ids']]
 focus=[r for r in rows if r['is_discovery_exposure']=='True' or r['local_continuum_low']=='True']
 assert len(rows)==28 and len(focus)==8 and len({r['dp_id'] for r in focus})==3
 profiles={};profile_records=[];max_errors={'normalized_identity':0.,'residual_identity':0.,'closed_form_raw_side_background':0.,'raw_residual_scale':0.,'discovery_pearson':0.,'positive_scalar_pearson_invariance':0.}
 for r in rows:
  p=CONTEXT/'inputs/profiles'/Path(r['profile_path']).name;assert sha(p)==r['profile_sha256']
  with np.load(p,allow_pickle=False) as d:arr={k:d[k].copy() for k in d.files}
  x=arr['offset_air_angstrom'];assert len(x)==201 and np.array_equal(x,np.linspace(-1,1,201))
  norm=float(r['normalization_adu']);assert norm>0
  f,y,bg,res=(arr[k] for k in ['raw_flux','normalized_flux','linear_background','residual']);side=(abs(x)>=.599999999)&np.isfinite(f)
  sx=x[side];sf=f[side];mx=math.fsum(sx)/len(sx);mf=math.fsum(sf)/len(sf)
  slope=math.fsum((float(u)-mx)*(float(v)-mf) for u,v in zip(sx,sf))/math.fsum((float(u)-mx)**2 for u in sx)
  fitted_raw_background=(mf-slope*mx)+slope*x;raw_residual=f-norm*bg
  errs=dict(normalized_identity=float(np.nanmax(abs(y-f/norm))),residual_identity=float(np.nanmax(abs(res-(y-bg)))),closed_form_raw_side_background=float(np.nanmax(abs(fitted_raw_background-norm*bg))),raw_residual_scale=float(np.nanmax(abs(raw_residual-norm*res))))
  assert errs['normalized_identity']<1e-12 and errs['residual_identity']<1e-12 and errs['closed_form_raw_side_background']<1e-10 and errs['raw_residual_scale']<1e-10
  for k,v in errs.items():max_errors[k]=max(max_errors[k],v)
  key=(r['candidate_id'],r['dp_id'],r['frame']);profiles[key]=dict(arr=arr,row=r,raw_residual=raw_residual)
  profile_records.append(dict(candidate_id=r['candidate_id'],dp_id=r['dp_id'],frame=r['frame'],normalizer=norm,noise=float(r['first_difference_noise_proxy_adu']),normalizer_over_noise=norm/float(r['first_difference_noise_proxy_adu']),low=r['local_continuum_low']=='True',is_discovery=r['is_discovery_exposure']=='True',errors=errs,profile_sha256=r['profile_sha256']))
 for key,p in profiles.items():
  r=p['row'];ref=profiles[(r['candidate_id'],r['source_dp_id'],r['frame'])];core=abs(p['arr']['offset_air_angstrom'])<=.250000001
  nr=pearson(p['arr']['residual'][core],ref['arr']['residual'][core]);rr=pearson(p['raw_residual'][core],ref['raw_residual'][core])
  assert nr is not None and rr is not None
  e1=abs(nr-float(r['correlation_to_discovery']));e2=abs(nr-rr);assert e1<1e-12 and e2<1e-12
  max_errors['discovery_pearson']=max(max_errors['discovery_pearson'],e1);max_errors['positive_scalar_pearson_invariance']=max(max_errors['positive_scalar_pearson_invariance'],e2)
  next(a for a in profile_records if (a['candidate_id'],a['dp_id'],a['frame'])==key).update(recomputed_normalized_residual_pearson=nr,recomputed_unnormalized_residual_pearson=rr)
 products=json.loads((CONTEXT/'SOURCE_PRODUCTS.json').read_text())['products'];assert len(products)==9
 for r in products:
  p=CONTEXT/r['local_path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
 merged=[];native_results=[];raw_checks=0
 for dp in dict.fromkeys(r['dp_id'] for r in focus):
  pair={r['kind']:r for r in products if r['dp_id']==dp};assert set(pair)=={'SCIENCE','RAW','ANCILLARY'}
  with fits.open(CONTEXT/pair['SCIENCE']['local_path'],memmap=False) as hd:
   ph=hd[0].header.copy();w=np.array(hd[1].data['WAVE'][0],float);flux=np.array(hd[1].data['FLUX'][0],float);err=np.array(hd[1].data['ERR'][0],float)
   assert hd[1].header['TUNIT1']=='angstrom' and ph['SPECSYS']=='BARYCENT'
  with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(CONTEXT/pair['RAW']['local_path'])],check=True,capture_output=True).stdout),memmap=False) as hd:
   raw=np.hstack([hd[1].data[:,50:2098],hd[2].data[:,50:2098]]).astype(float);rh=hd[0].header.copy()
  with tarfile.open(CONTEXT/pair['ANCILLARY']['local_path']) as tar:
   member=[m for m in tar if m.name.endswith('_e2ds_A.fits')];assert len(member)==1 and Path(member[0].name).name==pair['RAW']['raw_id']+'_e2ds_A.fits'
   with fits.open(io.BytesIO(tar.extractfile(member[0]).read()),memmap=False) as hd:native=hd[0].data.astype(float);h=hd[0].header.copy()
  assert raw.shape==(4096,4096) and native.shape==(72,4096)
  assert rh['ARCFILE'].removesuffix('.fits')==pair['RAW']['raw_id']
  assert rh['DATE-OBS']==h['DATE-OBS']==ph['DATE-OBS'] and rh['INSTRUME']==h['INSTRUME']=='HARPS'
  assert abs(h['ESO DRS BERV']-ph['ESO DRS BERV'])<1e-8
  mapping=json.loads((EXT/pair['RAW']['historical_batch']/'NATIVE_MAPPING.json').read_text());spec=next(s for s in mapping['spectra'] if s['dp_id']==dp);flips=spec['grid_best'];assert spec['status']=='REGISTERED'
  spacing=med(np.diff(w));pixels=np.arange(4096,dtype=float);wd=int(h['ESO DRS CAL TH DEG LL']);td=int(h['ESO DRS CAL LOC DEG CTR'])
  waves=[poly(h,'ESO DRS CAL TH COEFF LL',wd,o,pixels) for o in range(72)]
  for r in [a for a in focus if a['dp_id']==dp]:
   center=float(r['center_sampled_bary_air_angstrom']);mask=(abs(w-center)<=2)&np.isfinite(flux)
   vals=flux[mask];adj=(abs(w[:-1]-center)<=2)&np.isfinite(flux[:-1])&np.isfinite(flux[1:])&(np.diff(w)<1.51*spacing)
   norm=med(vals);noise=mad(np.diff(flux)[adj])/math.sqrt(2)
   assert abs(norm-float(r['normalization_adu']))<1e-12 and abs(noise-float(r['first_difference_noise_proxy_adu']))<1e-12
   assert int(mask.sum())==int(r['normalization_samples']);assert (norm<=3*noise)==(r['local_continuum_low']=='True')
   merged.append(dict(candidate_id=r['candidate_id'],dp_id=dp,frame=r['frame'],center_sampled_bary_air_angstrom=center,samples=int(mask.sum()),normalization=norm,noise_proxy=noise,normalizer_over_noise=norm/noise,nonpositive_samples=int((vals<=0).sum()),nonpositive_fraction=float((vals<=0).mean()),finite_positive_ERR_samples=int((np.isfinite(err[mask])&(err[mask]>0)).sum()),q05=float(np.quantile(vals,.05)),q50=norm,q95=float(np.quantile(vals,.95)),selected_wave_sha256=hashlib.sha256(w[mask].astype('<f8').tobytes()).hexdigest(),selected_flux_sha256=hashlib.sha256(vals.astype('<f8').tobytes()).hexdigest()))
   topo=center/(1+float(h['ESO DRS BERV'])/299792.458)
   covering=[o for o,wv in enumerate(waves) if min(wv)<=topo<=max(wv)]
   for o in covering:
    wave=waves[o];k=int(np.argmin(abs(wave-topo)));sel=(abs(wave-topo)<=2)&np.isfinite(native[o]);nv=native[o,sel]
    arg=4095-k if flips['argument_flip'] else k;col=float(poly(h,'ESO DRS CAL LOC CTR',td,o,arg));col=4095-col if flips['column_flip'] else col;row=4095-k if flips['row_flip'] else k;ic=round(col)
    full=20<=k<4076 and 16<=ic<4080 and 15<=row<4081
    rec=dict(candidate_id=r['candidate_id'],dp_id=dp,frame=r['frame'],order=o,native_pixel=k,topocentric_center=topo,raw_row=row,raw_column=col,full_cutout=bool(full),native_samples=int(sel.sum()),native_median=med(nv),native_nonpositive=int((nv<=0).sum()),native_min=float(nv.min()),native_max=float(nv.max()))
    if full:
     cut=raw[row-15:row+16,ic-16:ic+17];bg=np.median(np.concatenate([cut[:10],cut[-10:]],axis=0),axis=0);excess=cut-bg[None,:]
     rec.update(raw_cutout_sha256=hashlib.sha256(cut.astype('<f8').tobytes()).hexdigest(),raw_background_sha256=hashlib.sha256(bg.astype('<f8').tobytes()).hexdigest(),raw_excess_sha256=hashlib.sha256(excess.astype('<f8').tobytes()).hexdigest());raw_checks+=1
    native_results.append(rec)
 for rel,digest in plan['source_hashes'].items():assert sha(EXT/rel)==digest
 save('INDEPENDENT_EXPECTATIONS.json',dict(status='PASS_SOURCE_RECONSTRUCTION_AWAITING_OUTPUT_COMPARISON',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile_records=profile_records,focused_merged=merged,native_orders=native_results,coverage=dict(profiles=28,focused_profiles=8,source_products=9,native_order_records=len(native_results),raw_cutouts=raw_checks),max_absolute_errors=max_errors,script_sha256=sha(Path(__file__))))
 print(json.dumps(dict(profiles=28,focused_profiles=8,native_orders=len(native_results),raw_cutouts=raw_checks,max_errors=max_errors),indent=2))
if __name__=='__main__':main()
