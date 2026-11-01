"""Fixed multi-order reference-grid check; only writes in mapping_followup."""
from pathlib import Path
import json, io, tarfile, subprocess, hashlib, itertools, gc
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter

OUT = Path(__file__).resolve().parent
BASE = OUT.parents[1]
OLD = BASE / 'v2/triage_batch01'
PLAN = json.loads((OUT/'PLAN.json').read_text())
MAPPING = json.loads((OLD/'NATIVE_MAPPING.json').read_text())
PRODUCTS = json.loads((OLD/'products/MANIFEST.json').read_text())['products']

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def poly(h, prefix, degree, order, x):
    return np.polynomial.polynomial.polyval(x, [h[prefix+str(order*(degree+1)+i)] for i in range(degree+1)])
def number(x): return float(x) if np.isfinite(x) else None
def highpass(x): return x-median_filter(x,size=31,mode='nearest')
def corr(a,b,mask):
    return number(np.corrcoef(a[mask],b[mask])[0,1]) if np.sum(mask)>=100 else None
def load(dp):
    rr=next(r for r in PRODUCTS if r['dp_id']==dp and r['kind']=='RAW')
    tr=next(r for r in PRODUCTS if r['dp_id']==dp and r['kind']=='ANCILLARY')
    for r in [rr,tr]: assert sha(BASE/r['relative_path'])==r['sha256']
    with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(BASE/rr['relative_path'])],check=True,capture_output=True).stdout)) as h:
        rh=h[0].header.copy()
        assert rh['ARCFILE'].removesuffix('.fits')==rr['raw_id']
        raw=np.hstack([h[1].data[:,50:2098],h[2].data[:,50:2098]]).astype(float)
    with tarfile.open(BASE/tr['relative_path']) as t:
        member=next(m for m in t if m.name.endswith('_e2ds_A.fits'))
        with fits.open(io.BytesIO(t.extractfile(member).read())) as h:
            native=h[0].data.astype(float);hdr=h[0].header.copy()
    assert hdr['DATE-OBS']==rh['DATE-OBS']
    assert raw.shape==(4096,4096) and native.shape==(72,4096)
    old=next(r for r in MAPPING['spectra'] if r['dp_id']==dp)
    assert abs(hdr['ESO DRS BERV']-old['berv_km_s'])<1e-8
    return raw,native,hdr,dict(raw_sha256=rr['sha256'],ancillary_sha256=tr['sha256'],date_obs=rh['DATE-OBS'],native_member=member.name)

def trace(h,o,x,argflip):
    return poly(h,'ESO DRS CAL LOC CTR',int(h['ESO DRS CAL LOC DEG CTR']),o,4095-x if argflip else x)

def inspect(dp):
    raw,native,h,provenance=load(dp)
    old=next(r for r in MAPPING['spectra'] if r['dp_id']==dp)
    candidates=[r for r in MAPPING['orders'] if r['dp_id']==dp]
    regions=[]
    for o in PLAN['reference_orders']:
        for lo,hi in PLAN['reference_windows_half_open']:
            x=np.arange(lo,hi)
            mask=np.ones(len(x),bool)
            excluded=[]
            for r in candidates:
                if r['order']==o:
                    near=abs(x-r['native_pixel'])<=PLAN['candidate_exclusion_half_width_pixels']
                    if near.any(): excluded.append(r['review_id'])
                    mask &= ~near
            reg=dict(order=o,pixel_interval_half_open=[lo,hi],samples=int(mask.sum()),excluded_candidate_ids=excluded,options=[])
            ref=highpass(native[o,x])
            for rowflip,colflip,argflip in itertools.product([False,True],repeat=3):
                yy=4095-x if rowflip else x
                tc=trace(h,o,x,argflip)
                if colflip: tc=4095-tc
                cx=np.rint(tc).astype(int)
                aperture=np.array([raw[yy,cx+j] for j in range(-3,4)]).sum(axis=0)
                hp=highpass(aperture)
                profile=np.median(np.stack([raw[yy,cx+j][mask] for j in range(-8,9)]),axis=1)
                peak=int(np.argmax(profile))-8
                reg['options'].append(dict(row_flip=rowflip,column_flip=colflip,argument_flip=argflip,
                    correlation=corr(ref,hp,mask),continuum_peak_integer_offset=peak,
                    continuum_profile=profile.tolist()))
            regions.append(reg)
    summaries=[]
    for flips in itertools.product([False,True],repeat=3):
        idx=list(itertools.product([False,True],repeat=3)).index(flips)
        cs=[r['options'][idx]['correlation'] for r in regions if r['options'][idx]['correlation'] is not None]
        offsets=[r['options'][idx]['continuum_peak_integer_offset'] for r in regions]
        summaries.append(dict(row_flip=flips[0],column_flip=flips[1],argument_flip=flips[2],
            median_correlation=float(np.median(cs)),min_correlation=float(min(cs)),max_correlation=float(max(cs)),
            regions_above_original_0p8_threshold=sum(v>.8 for v in cs),valid_regions=len(cs),
            median_abs_continuum_peak_offset=float(np.median(np.abs(offsets))),
            max_abs_continuum_peak_offset=int(max(abs(z) for z in offsets))))
    summaries.sort(key=lambda r:r['median_correlation'],reverse=True)
    candidate_info=[]
    for r in candidates:
        if r['review_id'] not in PLAN['review_ids']:continue
        o=r['order']; k=r['native_pixel']
        candidate_info.append(dict(review_id=r['review_id'],order=o,native_pixel=k,
            original_raw_column=r['raw_column'],argument_false_column=float(trace(h,o,k,False)),
            argument_true_column=float(trace(h,o,k,True)),original_raw_row=r['raw_row']))
    record=dict(dp_id=dp,provenance=provenance,original_status=old['status'],original_best_orientation=old['orientations'][0],
        fixed_grid_orientation_summaries=summaries,reference_regions=regions,candidate_positions=candidate_info)
    del raw,native;gc.collect()
    return record

if __name__=='__main__':
    records=[]
    for dp in PLAN['dp_ids']:
        r=inspect(dp);records.append(r)
        print(json.dumps(dict(dp_id=dp,summaries=r['fixed_grid_orientation_summaries'],candidate_positions=r['candidate_positions'])),flush=True)
    result=dict(plan_sha256=sha(OUT/'PLAN.json'),script_sha256=sha(Path(__file__)),original_mapping_sha256=sha(OLD/'NATIVE_MAPPING.json'),records=records)
    (OUT/'REFERENCE_GRID.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
