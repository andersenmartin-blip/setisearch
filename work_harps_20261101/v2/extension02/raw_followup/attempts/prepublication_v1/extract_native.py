"""Fixed baseline native/raw extraction of every accepted event in selected exposures."""
import io,tarfile,subprocess,gc
import numpy as np
from astropy.io import fits
from common import *
from registration import evaluate_reference_grid
from local_registration import evaluate_local_trace
P=verify_plan();freeze=verify_freeze();require(not(OUT/'NATIVE_MAPPING.json').exists(),'Existing extraction must not be silently replaced')
events=csvrows(OUT/'SELECTED_EVENTS.csv');selected=csvrows(OUT/'SELECTED_EXPOSURES.csv');prod=read('products/MANIFEST.json')['products'];source={r['dp_id']:r for r in json.loads((EXT/'acquisition/DOWNLOAD_MANIFEST.json').read_text())}
NATIVE=OUT/'native';NATIVE.mkdir(exist_ok=True);(OUT/'reference').mkdir(exist_ok=True)
def poly(h,prefix,degree,order,x):return np.polynomial.polynomial.polyval(x,[h[prefix+str(order*(degree+1)+i)]for i in range(degree+1)])
def context(h):return{k:v for k,v in h.items()if any(t in k for t in ['DPR','INS OPTI','LAMP','DRIFT','CAL TH FILE','CAL LOC FILE'])and isinstance(v,(str,int,float,bool))}
spectra=[];orders=[];local_audit=[];fiber_inventory=[];event_summary=[]
for s in selected:
 dp=s['dp_id'];hits=[r for r in events if r['dp_id']==dp];pair=[r for r in prod if r['dp_id']==dp and r['status']=='DOWNLOADED']
 if len(pair)!=2 or {r['kind']for r in pair}!={'RAW','ANCILLARY'}:
  spectra.append(dict(dp_id=dp,status='PRODUCT_PAIR_UNAVAILABLE'))
  event_summary.extend(dict(review_id=r['review_id'],detector=r['detector'],dp_id=dp,status='NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE')for r in hits);continue
 rr=next(r for r in pair if r['kind']=='RAW');tr=next(r for r in pair if r['kind']=='ANCILLARY')
 for r in pair:require(sha(BASE/r['relative_path'])==r['sha256'],'Product hash mismatch')
 with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(BASE/rr['relative_path'])],check=True,capture_output=True).stdout))as h:
  rh=h[0].header.copy();require(rh['ARCFILE'].removesuffix('.fits')==s['raw_progenitor_id'],'Raw archive identity mismatch');require(rh['DATE-OBS']==source[dp]['primary_header']['DATE-OBS'],'Raw date mismatch');raw=np.hstack([h[1].data[:,50:2098],h[2].data[:,50:2098]]).astype(float)
 with tarfile.open(BASE/tr['relative_path'])as t:
  member=next(m for m in t if m.name.endswith('_e2ds_A.fits'))
  with fits.open(io.BytesIO(t.extractfile(member).read()))as h:native=h[0].data.astype(float);hdr=h[0].header.copy()
  inv=dict(dp_id=dp,raw_context=context(rh),members=t.getnames(),fiber_headers={})
  for fiber in ['A','B']:
   ms=[m for m in t if m.name.endswith('_e2ds_'+fiber+'.fits')]
   if not ms:inv['fiber_headers'][fiber]=dict(status='MISSING');continue
   with fits.open(io.BytesIO(t.extractfile(ms[0]).read()))as h:inv['fiber_headers'][fiber]=dict(status='PRESENT',context=context(h[0].header),member=ms[0].name)
  inv['independent_sky_fiber_available']=rh.get('ESO DPR TYPE','').split(',')[1:2]==['SKY']and inv['fiber_headers']['B']['status']=='PRESENT';fiber_inventory.append(inv)
 require(hdr['DATE-OBS']==rh['DATE-OBS'],'Native date mismatch');berv=float(hdr['ESO DRS BERV']);require(abs(berv-source[dp]['primary_header']['HIERARCH ESO DRS BERV'])<1e-8,'Native/science BERV mismatch');require(raw.shape==(4096,4096)and native.shape==(72,4096),'Unexpected raw/native shape')
 degree=int(hdr['ESO DRS CAL TH DEG LL']);ldeg=int(hdr['ESO DRS CAL LOC DEG CTR']);x=np.arange(4096);waves=np.array([poly(hdr,'ESO DRS CAL TH COEFF LL',degree,o,x)for o in range(72)])
 candidates=[]
 for hit in hits:
  center=float(hit['fitted_center_bary_air_angstrom'])/(1+berv/299792.458)
  for order in np.flatnonzero((waves[:,0]<center)&(waves[:,-1]>center)):candidates.append(dict(review_id=hit['review_id'],order=int(order),native_pixel=int(np.argmin(abs(waves[order]-center)))))
 grid=evaluate_reference_grid(raw,native,hdr,candidates);best=grid['orientation_summaries'][0];ok=best['median_correlation']is not None and best['median_correlation']>.8 and best['valid_regions']>=18 and best['valid_orders']>=5 and best['median_abs_continuum_peak_offset']<=1
 name=dp.replace(':','_')+'.json';dump('reference/'+name,grid);spectra.append(dict(dp_id=dp,status='REGISTERED'if ok else'MAPPING_UNCERTAIN',raw_sha256=rr['sha256'],ancillary_sha256=tr['sha256'],date_obs=rh['DATE-OBS'],berv_km_s=berv,native_member=member.name,reference_grid='reference/'+name,grid_best=best))
 for hit in hits:
  center=float(hit['fitted_center_bary_air_angstrom'])/(1+berv/299792.458);cover=np.flatnonzero((waves[:,0]<center)&(waves[:,-1]>center)).tolist();statuses=[]
  for order in cover:
   k=int(np.argmin(abs(waves[order]-center)));cy=4095-k if best['row_flip']else k;arg=4095-k if best['argument_flip']else k;cx=float(poly(hdr,'ESO DRS CAL LOC CTR',ldeg,order,arg));cx=4095-cx if best['column_flip']else cx;icx=round(cx)
   if not(20<=k<4076 and 12<=icx<4084 and 10<=cy<4086):orders.append(dict(review_id=hit['review_id'],detector=hit['detector'],dp_id=dp,order=order,status='EDGE_TRUNCATED',native_pixel=k));statuses.append('EDGE_TRUNCATED');continue
   local=evaluate_local_trace(raw,native,hdr,order,k,best,candidates);local.update(review_id=hit['review_id'],order=order,dp_id=dp,global_reference_mapping_verified=bool(ok));local_audit.append(local)
   cut=raw[cy-10:cy+11,icx-12:icx+13];background=np.median(cut[np.r_[0:5,16:21]],axis=0);excess=cut-background[None,:];sl=slice(k-20,k+21);wave=waves[order,sl];flux=native[order,sl];filename=hit['review_id']+'_o'+str(order).zfill(2)+'.npz';np.savez_compressed(NATIVE/filename,raw_cutout=cut,raw_background=background,raw_excess=excess,native_wave=wave,native_flux=flux)
   orders.append(dict(review_id=hit['review_id'],detector=hit['detector'],dp_id=dp,target=hit['target'],order=order,status='EXTRACTED',native_pixel=k,topocentric_air_angstrom=center,native_nearest_wave_angstrom=float(waves[order,k]),raw_row=cy,raw_column=cx,cutout='native/'+filename,mapping_verified=bool(ok and local['local_mapping_usable']),grid_mapping_usable=bool(ok),local_mapping_usable=bool(local['local_mapping_usable']),reference_correlation=best['median_correlation'],origin_status='UNREVIEWED'));statuses.append('EXTRACTED')
  event_summary.append(dict(review_id=hit['review_id'],detector=hit['detector'],dp_id=dp,covering_orders=cover,status='NATIVE_CONTEXT_EXTRACTED'if'EXTRACTED'in statuses else'NO_USABLE_FULL_CUTOUT',origin_status='UNREVIEWED'))
 print(dp,len(hits),'events',flush=True);del raw,native;gc.collect()
require(len(event_summary)==len(events),'Event accounting incomplete');verify_freeze()
dump('NATIVE_MAPPING.json',dict(created_utc=now(),spectra=spectra,orders=orders,events=event_summary,hits=len(events),extracted_orders=sum(r['status']=='EXTRACTED'for r in orders),method='Unchanged triage_batch02 reference/local checks; fixed raw/native snippets. V1 centers use accepted peak; V2 centers use accepted fitted center. No classification performed.'))
dump('LOCAL_TRACE_AUDIT.json',dict(method='Unchanged candidate-excluded two-sided local continuum check',orders=local_audit));dump('FIBER_INVENTORY.json',fiber_inventory)
