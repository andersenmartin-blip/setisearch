"""Extract native-order and raw CCD cutouts; empirical orientation check away from hits.

Not an origin classifier. Raw calibration is not rerun. Mapping confidence and
unresolved one-pixel conventions remain recorded instead of hidden rejection.
"""
from pathlib import Path
import csv,json,io,tarfile,subprocess,hashlib
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
BASE=Path(__file__).resolve().parent.parent;OUT=BASE/'triage_followup/native';OUT.mkdir(exist_ok=True)
manifest=json.loads((BASE/'triage_followup/products/MANIFEST.json').read_text())['products']
hits=list(csv.DictReader((BASE/'production/HIT_DISPOSITIONS.csv').open()))
def poly(header,prefix,degree,order,x):
 return np.polynomial.polynomial.polyval(x,[header[prefix+str(order*(degree+1)+j)] for j in range(degree+1)])
all_records=[]
fig,axes=plt.subplots(10,2,figsize=(14,24),layout='constrained')
for row,hit in enumerate(hits):
 rawrec=next(x for x in manifest if x['hit_id']==hit['hit_id'] and x['kind']=='RAW')
 tarrec=next(x for x in manifest if x['hit_id']==hit['hit_id'] and x['kind']=='ANCILLARY')
 assert rawrec['status']==tarrec['status']=='DOWNLOADED'
 with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(BASE/rawrec['relative_path'])],capture_output=True,check=True).stdout)) as h:
  assert h[0].header['ARCFILE'].removesuffix('.fits') in json.loads(hit['raw_progenitor_ids'])
  raw=np.hstack([h[1].data[:,50:2098],h[2].data[:,50:2098]]).astype(float)
  raw_date=h[0].header['DATE-OBS']
 with tarfile.open(BASE/tarrec['relative_path']) as t:
  m=next(m for m in t if m.name.endswith('_e2ds_A.fits'))
  with fits.open(io.BytesIO(t.extractfile(m).read())) as h:
   native=h[0].data.astype(float);hdr=h[0].header.copy()
 x=np.arange(4096);degree=int(hdr['ESO DRS CAL TH DEG LL']);ldeg=int(hdr['ESO DRS CAL LOC DEG CTR'])
 waves=np.array([poly(hdr,'ESO DRS CAL TH COEFF LL',degree,o,x) for o in range(len(native))])
 center=float(hit['wave_peak_angstrom'])/(1+float(hit['berv_km_s'])/299792.458)
 orders=np.flatnonzero((waves[:,0]<center)&(waves[:,-1]>center)).tolist();assert orders
 # Choose order with more pixel distance to an edge; record all possible orders.
 order=max(orders,key=lambda o:min(np.argmin(abs(waves[o]-center)),4095-np.argmin(abs(waves[o]-center))))
 k=int(np.argmin(abs(waves[order]-center)))
 # Reference pixels are fixed before looking at raw candidate morphology.
 refx=np.arange(1000,1400);reforder=50
 ref=native[reforder,refx];ref=ref-median_filter(ref,size=31,mode='nearest')
 options=[]
 for rowflip in [False,True]:
  for colflip in [False,True]:
   for locflip in [False,True]:
    yy=4095-refx if rowflip else refx
    lx=4095-refx if locflip else refx
    xx=np.rint(poly(hdr,'ESO DRS CAL LOC CTR',ldeg,reforder,lx)).astype(int)
    if colflip:xx=4095-xx
    measured=np.array([raw[y,max(0,c-3):min(4096,c+4)].sum() for y,c in zip(yy,xx)])
    residual=measured-median_filter(measured,size=31,mode='nearest')
    corr=float(np.corrcoef(ref,residual)[0,1])
    options.append(dict(row_flip=rowflip,column_flip=colflip,localization_argument_flip=locflip,reference_correlation=corr))
 best=max(options,key=lambda t:t['reference_correlation'])
 cy=4095-k if best['row_flip'] else k
 locx=4095-k if best['localization_argument_flip'] else k
 cx=float(poly(hdr,'ESO DRS CAL LOC CTR',ldeg,order,locx));cx=4095-cx if best['column_flip'] else cx
 icx=int(round(cx));cut=raw[cy-10:cy+11,icx-9:icx+10]
 assert cut.shape==(21,19)
 lo=max(0,k-15);hi=min(4096,k+16)
 rec=dict(hit_id=hit['hit_id'],target=hit['canonical_target'],dp_id=hit['dp_id'],raw_date=raw_date,
  raw_sha256=rawrec['sha256'],ancillary_sha256=tarrec['sha256'],native_member=m.name,
  topocentric_air_estimate_angstrom=center,possible_orders=orders,chosen_zero_based_order=order,native_pixel=k,
  nearest_native_wave_angstrom=float(waves[order,k]),pixel_wave_difference=float(waves[order,k]-center),
  trimmed_raw_row=cy,trimmed_raw_column_float=cx,mapping=best,all_mapping_options=options,
  mapping_status='EMPIRICALLY_REGISTERED_REFERENCE_INTERVAL' if best['reference_correlation']>.8 else 'MAPPING_UNCERTAIN',
  origin_status='UNRESOLVED_REQUIRES_MORPHOLOGY_REVIEW',
  limitation='Header polynomials and archived primary geometry, with orientation checked against native spectral structure in fixed order50/pixels1000:1399. Pixel zero/one conventions and drift are not a new full calibration. No cosmic-ray or laser label inferred automatically.')
 np.savez_compressed(OUT/(hit['hit_id']+'_cutout.npz'),raw_cutout=cut,native_wave=waves[order,lo:hi],native_flux=native[order,lo:hi])
 all_records.append(rec)
 ax=axes[row,0];ax.plot(waves[order,lo:hi],native[order,lo:hi],'.-',ms=3);ax.axvline(center,color='red',ls='--');ax.set_title(hit['hit_id']+' '+hit['canonical_target']+' · native order '+str(order));ax.set_ylabel('Extracted electrons')
 ax=axes[row,1];ax.imshow(cut,origin='lower',aspect='auto',cmap='magma',extent=[-9.5,9.5,-10.5,10.5]);ax.axvline(cx-icx,color='cyan',lw=.8);ax.axhline(0,color='cyan',lw=.8);ax.set_title('Raw CCD · reference correlation %.3f'%best['reference_correlation']);ax.set_ylabel('Raw row offset')
axes[-1,0].set_xlabel('Approximate topocentric air wavelength (Å)');axes[-1,1].set_xlabel('Trimmed raw column offset')
fig.suptitle('Original ten hits: native spectral orders and raw CCD cutouts\nData inspection only; no automatic origin classification',fontsize=17)
fig.savefig(OUT/'ORIGINAL_TEN_NATIVE_AND_RAW.png',dpi=130)
(OUT/'MAPPING.json').write_text(json.dumps(all_records,indent=2)+'\n')
print(json.dumps([dict(hit=x['hit_id'],order=x['chosen_zero_based_order'],pixel=x['native_pixel'],mapping=x['mapping']) for x in all_records],indent=2))
