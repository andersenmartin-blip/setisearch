"""Fresh-process numerical audit by a separate agent; never writes source products.

Independent reconstruction of wavelength/trace Horner polynomials, raw trimming,
cutouts and descriptive scalar outputs. Reference-grid rerun explicitly reuses
registration.py and is reproducibility evidence, not independent algorithm validation.
"""
from pathlib import Path
import csv, datetime, gc, hashlib, io, json, subprocess, sys, tarfile
import numpy as np
from astropy.io import fits

OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
sys.path.insert(0,str(OUT))
from registration import evaluate_reference_grid

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def horner(header,prefix,degree,order,x):
    # Implemented here rather than importing the extractor's polynomial helper.
    result=np.zeros_like(np.asarray(x,dtype=float))
    for power in range(degree,-1,-1):
        result=result*x+float(header[prefix+str(order*(degree+1)+power)])
    return result

def close(a,b,atol=1e-9):
    assert abs(float(a)-float(b))<=atol,(a,b,atol)
    return abs(float(a)-float(b))

def recursive_compare(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys(),(a.keys(),b.keys())
        return max([recursive_compare(a[k],b[k]) for k in a]+[0.0])
    if isinstance(a,list):
        assert len(a)==len(b)
        return max([recursive_compare(x,y) for x,y in zip(a,b)]+[0.0])
    if isinstance(a,float):return close(a,b,1e-12)
    assert a==b,(a,b)
    return 0.0

def main():
    selected=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()))
    index=list(csv.DictReader((BASE/'v2/review/REVIEW_INDEX.csv').open()))
    assert selected==index[96:]
    assert len(selected)==237
    assert [r['review_id'] for r in selected]==[f'V2-{i:04d}' for i in range(97,334)]
    ids=list(dict.fromkeys(r['dp_id'] for r in selected));assert len(ids)==68
    plan=json.loads((OUT/'PLAN.json').read_text())
    checks={}
    for filename,key in [('v2/review/REVIEW_INDEX.csv','input_index_sha256'),('v2/production/V2_HITS.csv','hits_sha256'),('v2/production/V2_DISPOSITIONS.csv','original_dispositions_sha256')]:
        value=digest(BASE/filename);assert value==plan[key]
        checks[filename]=value
    mapping=json.loads((OUT/'NATIVE_MAPPING.json').read_text())
    assert mapping['script_sha256']==digest(OUT/'extract_native.py')
    records=mapping['orders'];assert len(records)==326
    assert len({(r['review_id'],r['order']) for r in records})==326
    assert {r['review_id'] for r in records}=={r['review_id'] for r in selected}
    assert sum(r['status']=='EXTRACTED' for r in records)==324
    edges=[r for r in records if r['status']=='EDGE_TRUNCATED'];assert len(edges)==2
    assert {r['dp_id'] for r in mapping['spectra']}==set(ids)
    array_inventory=[]
    for r in records:
        if r['status']!='EXTRACTED':continue
        file=OUT/r['cutout']
        with np.load(file) as d:
            assert set(d.files)=={'native_wave','native_flux','raw_cutout','raw_background','raw_excess'}
            assert d['native_wave'].shape==d['native_flux'].shape==(41,)
            assert d['raw_cutout'].shape==d['raw_excess'].shape==(21,25)
            assert d['raw_background'].shape==(25,)
            assert np.array_equal(d['raw_excess'],d['raw_cutout']-d['raw_background'][None,:])
        array_inventory.append(dict(review_id=r['review_id'],order=r['order'],path=r['cutout'],sha256=digest(file)))
    products=json.loads((OUT/'products/MANIFEST.json').read_text())['products'];assert len(products)==136
    jobs=json.loads((OUT/'JOBS.json').read_text());assert len(jobs)==136
    assert {(r['dp_id'],r['kind']) for r in products}=={(r['dp_id'],r['kind']) for r in jobs}
    products_verified=[]
    for r in products:
        path=BASE/r['relative_path'];assert r['status']=='DOWNLOADED'
        assert path.stat().st_size==r['bytes'] and digest(path)==r['sha256']
        assert json.loads((OUT/'products'/(r['filename']+'.json')).read_text())==r
        products_verified.append(dict(dp_id=r['dp_id'],kind=r['kind'],sha256=r['sha256'],bytes=r['bytes']))
    old={r['dp_id']:r for r in json.loads((BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json').read_text())}
    tested=[]
    for pos in [0,len(ids)//2,len(ids)-1]:
        dp=ids[pos];rr=next(r for r in products if r['dp_id']==dp and r['kind']=='RAW');tr=next(r for r in products if r['dp_id']==dp and r['kind']=='ANCILLARY')
        packed=subprocess.run(['gzip','-cd',str(BASE/rr['relative_path'])],capture_output=True,check=True).stdout
        with fits.open(io.BytesIO(packed)) as f:
            raw_head=f[0].header.copy()
            raw=np.concatenate((f[1].data[:,50:2098],f[2].data[:,50:2098]),axis=1).astype(np.float64)
        del packed
        assert raw_head['ARCFILE'].removesuffix('.fits')==rr['raw_id']
        assert raw_head['DATE-OBS']==old[dp]['primary_header']['DATE-OBS']
        with tarfile.open(BASE/tr['relative_path']) as archive:
            choices=[x for x in archive.getmembers() if x.name.endswith('_e2ds_A.fits')];assert len(choices)==1
            with fits.open(io.BytesIO(archive.extractfile(choices[0]).read())) as f:
                native=f[0].data.astype(np.float64);header=f[0].header.copy()
        assert raw.shape==(4096,4096) and native.shape==(72,4096)
        assert header['DATE-OBS']==raw_head['DATE-OBS']
        berv=float(header['ESO DRS BERV']);close(berv,old[dp]['primary_header']['HIERARCH ESO DRS BERV'],1e-8)
        degree=int(header['ESO DRS CAL TH DEG LL']);trace_degree=int(header['ESO DRS CAL LOC DEG CTR'])
        wave=np.asarray([horner(header,'ESO DRS CAL TH COEFF LL',degree,order,np.arange(4096)) for order in range(72)])
        candidates=[]
        for hit in [r for r in selected if r['dp_id']==dp]:
            center=float(hit['fitted_center_bary_air_angstrom'])/(1+berv/299792.458)
            covering=[o for o in range(72) if wave[o,0]<center<wave[o,-1]]
            actual=[r['order'] for r in records if r['review_id']==hit['review_id']]
            assert covering==actual
            for o in covering:candidates.append(dict(review_id=hit['review_id'],order=o,native_pixel=int(np.argmin(np.abs(wave[o]-center)))))
        grid=evaluate_reference_grid(raw,native,header,candidates)
        spectrum=next(r for r in mapping['spectra'] if r['dp_id']==dp)
        saved_grid=json.loads((OUT/spectrum['reference_grid']).read_text())
        # Extractor adds its display alias to the first summary; retain this when comparing.
        grid['orientation_summaries'][0]['correlation']=grid['orientation_summaries'][0]['median_correlation']
        grid_diff=recursive_compare(grid,saved_grid)
        best=grid['orientation_summaries'][0]
        event_checks=[]
        for r in [z for z in records if z['dp_id']==dp]:
            hit=next(z for z in selected if z['review_id']==r['review_id'])
            center=float(hit['fitted_center_bary_air_angstrom'])/(1+berv/299792.458)
            o=r['order'];pixel=int(np.argmin(abs(wave[o]-center)));assert pixel==r['native_pixel']
            raw_row=4095-pixel if best['row_flip'] else pixel
            argument=4095-pixel if best['argument_flip'] else pixel
            raw_col=float(horner(header,'ESO DRS CAL LOC CTR',trace_degree,o,argument))
            if best['column_flip']:raw_col=4095-raw_col
            col=int(round(raw_col))
            supported=20<=pixel<4076 and 12<=col<4084 and 10<=raw_row<4086
            assert supported==(r['status']=='EXTRACTED')
            if not supported:
                event_checks.append(dict(review_id=r['review_id'],order=o,status='EDGE_SUPPORT_CONFIRMED'));continue
            assert raw_row==r['raw_row'];coord_diff=close(raw_col,r['raw_column'])
            close(center,r['topocentric_air_angstrom'],1e-10)
            close(wave[o,pixel],r['native_nearest_wave_angstrom'])
            cut=raw[raw_row-10:raw_row+11,col-12:col+13]
            background=np.median(np.concatenate((cut[:5],cut[16:])),axis=0)
            excess=cut-background
            native_slice=native[o,pixel-20:pixel+21]
            wavelength_slice=wave[o,pixel-20:pixel+21]
            scale=float(np.median(np.concatenate((native_slice[:8],native_slice[33:]))))
            scalar_diffs=[close(scale,r['native_side_median']),close(float(native_slice[18:23].max()/scale),r['native_core_max_over_side_median'])]
            core=excess[8:13].sum(axis=0);bg=background-np.median(np.concatenate((background[:4],background[21:])))
            den=np.sqrt(np.dot(core,core)*np.dot(bg,bg))
            cosine=float(np.dot(core,bg)/den) if den>0 else None
            if cosine is None:assert r['descriptive_cross_profile_cosine'] is None
            else:scalar_diffs.append(close(cosine,r['descriptive_cross_profile_cosine']))
            scalar_diffs.append(close(np.maximum(excess,0).max(),r['raw_excess_positive_max']))
            scalar_diffs.append(close(np.maximum(np.concatenate((excess[:,:7],excess[:,18:]),axis=1),0).max(),r['outer_excess_positive_max']))
            with np.load(OUT/r['cutout']) as saved:
                exact={key:bool(np.array_equal(value,saved[key])) for key,value in [('raw_cutout',cut),('raw_background',background),('raw_excess',excess),('native_flux',native_slice)]}
                assert all(exact.values())
                wd=float(np.max(np.abs(wavelength_slice-saved['native_wave'])));assert wd<=1e-9
            event_checks.append(dict(review_id=r['review_id'],order=o,status='MATCH',exact_array_checks=exact,native_wave_max_absolute_difference_angstrom=wd,raw_column_absolute_difference_pixels=coord_diff,max_scalar_absolute_difference=max(scalar_diffs)))
        tested.append(dict(selection_index_zero_based=pos,dp_id=dp,date_obs=raw_head['DATE-OBS'],events=len({x['review_id'] for x in event_checks}),covering_orders=len(event_checks),grid_reproduction_max_absolute_difference=grid_diff,checks=event_checks))
        print(json.dumps(dict(dp_id=dp,orders=len(event_checks),status='MATCH')),flush=True)
        del raw,native,wave,cut,excess;gc.collect()
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASSED',reviewer='Separate analysis agent; fresh Python process',scope='All input hashes and event/order coverage; independent sample extraction for first/middle/last unique exposure by original metadata order.',selection_rule=dict(unique_exposures=68,indices_zero_based=[0,34,67]),counts=dict(events=237,unique_exposures=68,source_products_verified=136,all_order_records=326,extracted_arrays_checked=324,edge_truncated_order_records=2,sampled_exposures=3,sampled_orders=sum(x['covering_orders'] for x in tested)),unchanged_original_hashes=checks,source_products=products_verified,array_inventory=array_inventory,edges=edges,sampled_exposures=tested,code_sha256=digest(Path(__file__)),limitations=['The reference grid rerun reuses registration.py; it checks reproducibility, not an independent algorithm implementation.','The inverse-BERV approximation and coordinate conventions are reproduced, not externally calibrated.','This audit does not assign or confirm astrophysical origins, validate all raw cutouts independently, or substitute for independent human review.'])
    (OUT/'INDEPENDENT_NUMERICAL_AUDIT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=result['status'],counts=result['counts'])),flush=True)

if __name__=='__main__':main()
