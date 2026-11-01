"""Fixed broader reference audit of all43 mapping-limited hits; no search."""
from pathlib import Path
import json,csv,io,tarfile,subprocess,hashlib,gc,datetime
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
OUT=Path(__file__).resolve().parent;V2=OUT.parent;BASE=V2.parent;OLD=V2/'triage_batch02'
PLAN=json.loads((OUT/'PLAN.json').read_text())
HITS=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()))
MAPPING=json.loads((OLD/'NATIVE_MAPPING.json').read_text())
PRODUCTS=json.loads((OLD/'products/MANIFEST.json').read_text())['products']
(OUT/'native').mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(h,prefix,deg,o,x):return np.polynomial.polynomial.polyval(x,[h[prefix+str(o*(deg+1)+j)] for j in range(deg+1)])
def trace(h,o,x,flips):
    arg=4095-x if flips['argument_flip'] else x
    col=poly(h,'ESO DRS CAL LOC CTR',int(h['ESO DRS CAL LOC DEG CTR']),o,arg)
    return 4095-col if flips['column_flip'] else col
def interp(raw,yy,col):
    lo=np.floor(col).astype(int);f=col-lo
    return raw[yy,lo]*(1-f)+raw[yy,lo+1]*f
def hp(a):return a-median_filter(a,size=31,mode='nearest')
def peak(profile):
    k=int(np.argmax(profile));p=float(k-8)
    if 0<k<16:
        a,b,c=profile[k-1:k+2];den=a-2*b+c
        if den:p+=float(.5*(a-c)/den)
    return p
for rel,digest in PLAN['input_hashes'].items():assert sha(V2/rel)==digest,rel
spectra=[];orders=[];refs=[]
for dp in dict.fromkeys(r['dp_id'] for r in HITS):
    print('BEGIN '+dp,flush=True)
    rr=next(r for r in PRODUCTS if r['dp_id']==dp and r['kind']=='RAW');tr=next(r for r in PRODUCTS if r['dp_id']==dp and r['kind']=='ANCILLARY')
    for r in [rr,tr]:assert r['status']=='DOWNLOADED' and sha(BASE/r['relative_path'])==r['sha256']
    with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(BASE/rr['relative_path'])],check=True,capture_output=True).stdout)) as hd:
        raw=np.hstack([hd[1].data[:,50:2098],hd[2].data[:,50:2098]]).astype(float);rh=hd[0].header.copy()
    with tarfile.open(BASE/tr['relative_path']) as tar:
        mem=next(m for m in tar if m.name.endswith('_e2ds_A.fits'))
        with fits.open(io.BytesIO(tar.extractfile(mem).read())) as hd:native=hd[0].data.astype(float);h=hd[0].header.copy()
    assert raw.shape==(4096,4096) and native.shape==(72,4096)
    assert rh['ARCFILE'].removesuffix('.fits')==rr['raw_id'] and rh['DATE-OBS']==h['DATE-OBS']
    oldspec=next(r for r in MAPPING['spectra'] if r['dp_id']==dp);flips=oldspec['grid_best'];assert oldspec['status']=='REGISTERED'
    assert abs(h['ESO DRS BERV']-oldspec['berv_km_s'])<1e-8
    dp_hits=[r for r in HITS if r['dp_id']==dp];dp_ids={r['review_id'] for r in dp_hits}
    candidates=[r for r in MAPPING['orders'] if r['dp_id']==dp]
    needed=sorted({r['order'] for r in candidates if r['review_id'] in dp_ids})
    audit={}
    for o in needed:
        windows=[]
        for lo,hi in PLAN['reference_windows_half_open']:
            x=np.arange(lo,hi);yy=4095-x if flips['row_flip'] else x;cols=trace(h,o,x,flips)
            bounds=(cols>=9)&(cols<4086);mask=bounds.copy();excluded=[]
            for cand in candidates:
                if cand['order']==o:
                    near=abs(x-cand['native_pixel'])<=80
                    if near.any():excluded.append(cand['review_id'])
                    mask&=~near
            rec=dict(pixel_interval_half_open=[lo,hi],samples=int(mask.sum()),excluded_ids=excluded,correlation=None,peak_offset=None,profile=None)
            if mask.sum()>=200 and bounds.all():
                values=np.stack([interp(raw,yy,cols+j) for j in range(-8,9)])
                profile=np.median(values[:,mask],axis=1)
                profile-=np.median(profile[np.r_[0:2,15:17]])
                cc=float(np.corrcoef(hp(native[o,x])[mask],hp(values[5:12].sum(axis=0))[mask])[0,1])
                rec.update(correlation=cc if np.isfinite(cc) else None,peak_offset=peak(profile),profile=profile.tolist(),peak_above_outer_baseline=float(profile.max()))
            windows.append(rec)
        good=[r for r in windows if r['correlation'] is not None]
        cc=float(np.median([r['correlation'] for r in good])) if good else None
        po=float(np.median([abs(r['peak_offset']) for r in good])) if good else None
        supported=sum(abs(r['peak_offset'])<=1 for r in good)
        usable=bool(len(good)>=3 and cc>.8 and po<=.75 and supported>=3)
        audit[o]=dict(dp_id=dp,order=o,valid_reference_windows=len(good),median_correlation=cc,median_abs_peak_offset=po,windows_within_one_pixel=supported,mapping_supported=usable,windows=windows)
        refs.append(audit[o])
    for hit in dp_hits:
        oldorders=[r for r in candidates if r['review_id']==hit['review_id']]
        for old in oldorders:
            o=old['order'];k=old['native_pixel'];cx=float(trace(h,o,np.array(k),flips));cy=int(4095-k if flips['row_flip'] else k);icx=round(cx)
            r=dict(review_id=hit['review_id'],dp_id=dp,target=hit['canonical_target'],order=o,native_pixel=k,raw_row=cy,raw_column=cx,previous_status=old['status'],previous_mapping_verified=old.get('mapping_verified'),reference_mapping_supported=audit[o]['mapping_supported'])
            if not(20<=k<4076 and 16<=icx<4080 and 15<=cy<4081):
                r['status']='EDGE_TRUNCATED';orders.append(r);continue
            cut=raw[cy-15:cy+16,icx-16:icx+17].copy();bg=np.median(cut[np.r_[0:10,21:31]],axis=0);excess=cut-bg[None,:]
            xs=np.arange(k-20,k+21);wave=poly(h,'ESO DRS CAL TH COEFF LL',int(h['ESO DRS CAL TH DEG LL']),o,xs)
            center=float(hit['fitted_center_bary_air_angstrom'])/(1+float(h['ESO DRS BERV'])/299792.458)
            path=OUT/'native'/f'{hit["review_id"]}_o{o:02d}.npz'
            np.savez_compressed(path,raw_cutout=cut,raw_background=bg,raw_excess=excess,native_wave=wave,native_flux=native[o,xs])
            if old['status']=='EXTRACTED':
                d=np.load(OLD/old['cutout']);assert np.array_equal(d['raw_cutout'],cut[5:26,4:29]);assert np.array_equal(d['native_flux'],native[o,xs]);assert np.array_equal(d['native_wave'],wave)
                assert cx==old['raw_column'] and cy==old['raw_row']
            r.update(status='EXTRACTED',cutout=str(path.relative_to(OUT)),topocentric_air_angstrom=center,native_side_median=float(np.median(native[o,xs][np.r_[0:8,33:41]])))
            orders.append(r)
    spectra.append(dict(dp_id=dp,date_obs=rh['DATE-OBS'],berv_km_s=float(h['ESO DRS BERV']),orientation=flips,input_raw_sha256=rr['sha256'],input_ancillary_sha256=tr['sha256'],orders=needed))
    print(json.dumps(dict(dp_id=dp,orders=len(needed),supported=sum(r['mapping_supported'] for r in audit.values()))),flush=True)
    del raw,native,cut,excess;gc.collect()
for rel,digest in PLAN['input_hashes'].items():assert sha(V2/rel)==digest,rel
events=[]
for hit in HITS:
    rs=[r for r in orders if r['review_id']==hit['review_id']];full=[r for r in rs if r['status']=='EXTRACTED'];usable=bool(full and all(r['reference_mapping_supported'] for r in full))
    events.append(dict(review_id=hit['review_id'],mapping_supported=usable,covering_orders=[r['order'] for r in rs],edge_truncated_orders=[r['order'] for r in rs if r['status']=='EDGE_TRUNCATED'],unsupported_extracted_orders=[r['order'] for r in full if not r['reference_mapping_supported']],origin_status='UNREVIEWED'))
record=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha256=sha(OUT/'PLAN.json'),script_sha256=sha(Path(__file__)),spectra=spectra,reference_audit=refs,orders=orders,events=events,original_hashes_unchanged=True,coordinates_changed=False)
(OUT/'MAPPING_AUDIT.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(events=len(events),supported=sum(r['mapping_supported'] for r in events),remaining=[r['review_id'] for r in events if not r['mapping_supported']]),indent=2))
