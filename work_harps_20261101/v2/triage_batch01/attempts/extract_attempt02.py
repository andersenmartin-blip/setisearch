"""All overlapping native orders and raw cutouts for the fixed first96 hits.

This is post-detection inspection, not a new search or automatic origin veto.
Raw excess images subtract the per-column median of outer dispersion rows.
Both original and subtracted cutouts are retained for inspection.
"""
from pathlib import Path
import csv,json,io,tarfile,subprocess,hashlib,sys,gc
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
BASE=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
NATIVE=OUT/'native';NATIVE.mkdir(exist_ok=True)
selected=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()))
products=json.loads((OUT/'products/MANIFEST.json').read_text())['products']
old={r['dp_id']:r for r in json.loads((BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json').read_text())}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(h,prefix,deg,o,x):return np.polynomial.polynomial.polyval(x,[h[prefix+str(o*(deg+1)+i)] for i in range(deg+1)])
def number(x):return float(x) if np.isfinite(x) else None
mapping=[];spectra=[]
for dp in dict.fromkeys(r['dp_id'] for r in selected):
    print('BEGIN '+dp,flush=True)
    rr=next(r for r in products if r['dp_id']==dp and r['kind']=='RAW')
    tr=next(r for r in products if r['dp_id']==dp and r['kind']=='ANCILLARY')
    if rr['status']!='DOWNLOADED' or tr['status']!='DOWNLOADED':
        spectra.append(dict(dp_id=dp,status='PRODUCT_MISSING'));continue
    for r in [rr,tr]:assert sha(BASE/r['relative_path'])==r['sha256']
    with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(BASE/rr['relative_path'])],check=True,capture_output=True).stdout)) as h:
        rh=h[0].header.copy()
        assert rh['ARCFILE'].removesuffix('.fits')==rr['raw_id']
        assert rh['DATE-OBS']==old[dp]['primary_header']['DATE-OBS']
        raw=np.hstack([h[1].data[:,50:2098],h[2].data[:,50:2098]]).astype(float)
    with tarfile.open(BASE/tr['relative_path']) as t:
        member=next(m for m in t if m.name.endswith('_e2ds_A.fits'))
        with fits.open(io.BytesIO(t.extractfile(member).read())) as h:
            native=h[0].data.astype(float);hdr=h[0].header.copy()
    assert hdr['DATE-OBS']==rh['DATE-OBS']
    berv=float(hdr['ESO DRS BERV']);assert abs(berv-old[dp]['primary_header']['HIERARCH ESO DRS BERV'])<1e-8
    assert raw.shape==(4096,4096) and native.shape==(72,4096)
    degree=int(hdr['ESO DRS CAL TH DEG LL']);ldeg=int(hdr['ESO DRS CAL LOC DEG CTR'])
    x=np.arange(4096);waves=np.array([poly(hdr,'ESO DRS CAL TH COEFF LL',degree,o,x) for o in range(72)])
    refx=np.arange(1000,1400);ref=native[50,refx];ref=ref-median_filter(ref,size=31,mode='nearest')
    orientations=[]
    for rowflip in [False,True]:
        for colflip in [False,True]:
            for argflip in [False,True]:
                y=4095-refx if rowflip else refx;lx=4095-refx if argflip else refx
                cx=np.rint(poly(hdr,'ESO DRS CAL LOC CTR',ldeg,50,lx)).astype(int)
                if colflip:cx=4095-cx
                val=np.array([raw[yy,max(0,c-3):min(4096,c+4)].sum() for yy,c in zip(y,cx)])
                val=val-median_filter(val,size=31,mode='nearest')
                orientations.append(dict(row_flip=rowflip,column_flip=colflip,argument_flip=argflip,correlation=number(np.corrcoef(ref,val)[0,1])))
    options=sorted(orientations,key=lambda r:r['correlation'] if r['correlation'] is not None else -2,reverse=True)
    best=options[0]
    assert best['row_flip'] and not best['column_flip'] and best['argument_flip'] and best['correlation']>.8,(dp,best)
    spectra.append(dict(dp_id=dp,status='REGISTERED',raw_sha256=rr['sha256'],ancillary_sha256=tr['sha256'],date_obs=rh['DATE-OBS'],berv_km_s=berv,
                        native_member=member.name,reference_order=50,reference_pixel_range=[1000,1399],orientations=options))
    for hit in [r for r in selected if r['dp_id']==dp]:
        center=float(hit['fitted_center_bary_air_angstrom'])/(1+berv/299792.458)
        orders=np.flatnonzero((waves[:,0]<center)&(waves[:,-1]>center)).tolist();assert orders
        for o in orders:
            k=int(np.argmin(abs(waves[o]-center)));cy=4095-k
            cx=float(poly(hdr,'ESO DRS CAL LOC CTR',ldeg,o,cy));icx=round(cx)
            # Full support is required for the 21x25 raw display and 41-point spectrum.
            if not (20<=k<4076 and 12<=icx<4084 and 10<=cy<4086):
                mapping.append(dict(review_id=hit['review_id'],dp_id=dp,order=o,status='EDGE_TRUNCATED',native_pixel=k));continue
            cut=raw[cy-10:cy+11,icx-12:icx+13]
            background=np.median(cut[np.r_[0:5,16:21]],axis=0)
            excess=cut-background[None,:]
            sl=slice(k-20,k+21);wave=waves[o,sl];flux=native[o,sl]
            scale=float(np.median(flux[np.r_[0:8,33:41]]))
            filename=f'{hit["review_id"]}_o{o:02d}.npz'
            np.savez_compressed(NATIVE/filename,raw_cutout=cut,raw_background=background,raw_excess=excess,native_wave=wave,native_flux=flux)
            core=excess[8:13].sum(axis=0)
            # Descriptive morphology only; no threshold or disposition is derived.
            bg=background-np.median(background[np.r_[0:4,21:25]])
            raw_cos=float(core@bg/np.sqrt((core@core)*(bg@bg))) if (core@core)*(bg@bg)>0 else None
            outer=np.r_[0:7,18:25]
            mapping.append(dict(review_id=hit['review_id'],dp_id=dp,target=hit['target'],order=o,status='EXTRACTED',native_pixel=k,
                topocentric_air_angstrom=center,native_nearest_wave_angstrom=float(waves[o,k]),raw_row=cy,raw_column=cx,
                native_side_median=scale,native_core_max_over_side_median=float(flux[18:23].max()/scale),
                descriptive_cross_profile_cosine=raw_cos,outer_excess_positive_max=float(np.maximum(excess[:,outer],0).max()),
                raw_excess_positive_max=float(np.maximum(excess,0).max()),cutout='native/'+filename,
                OI_flag=hit['OI_0p03_angstrom_flag']=='True',origin_status='UNREVIEWED'))
    print(json.dumps(dict(dp_id=dp,correlation=best['correlation'],hits=sum(r['dp_id']==dp for r in selected))),flush=True)
    # Release large CCD arrays and the final view before loading the next exposure.
    del raw,cut,excess,native,h
    gc.collect()
record=dict(hits=len(selected),products_spectra=len(spectra),extracted_orders=sum(r['status']=='EXTRACTED' for r in mapping),
    edge_truncated_orders=sum(r['status']=='EDGE_TRUNCATED' for r in mapping),spectra=spectra,orders=mapping,
    method='All covering native orders; classical inverse BERV. Raw excess subtracts per-column median of rows -10:-6 and +6:+10. No raw re-reduction, no automatic rejection.',
    limitation='Approximate wavelength transformation and pixel/drift conventions; cross-profile values are descriptive, not a statistical cosmic-ray test.',
    script_sha256=sha(Path(__file__)))
(OUT/'NATIVE_MAPPING.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:record[k] for k in ['hits','products_spectra','extracted_orders','edge_truncated_orders']}),flush=True)
