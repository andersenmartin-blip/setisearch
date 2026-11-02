"""Independent raw-pixel reconstruction of the frozen reference diagnostic.

Does not import project analysis modules. Rebuilds polynomial coordinates,
interpolated aperture sums, correlations, ranks, clipping and summary medians.
Only RAW_NUMERICAL_AUDIT.json is written by this script.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import io
import json
import subprocess
import tarfile
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def median(xs):return float(np.median(xs)) if xs else None

def pearson(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    if len(a)<3 or not np.isfinite(a).all() or not np.isfinite(b).all():return None
    ac=a-a.mean();bc=b-b.mean();den=np.sqrt(np.dot(ac,ac)*np.dot(bc,bc))
    return float(np.dot(ac,bc)/den) if den else None

def average_ranks(values):
    order=np.argsort(values,kind='stable');sorted_values=values[order]
    boundaries=np.r_[0,np.flatnonzero(sorted_values[1:]!=sorted_values[:-1])+1,len(values)]
    result=np.empty(len(values),dtype=float)
    for left,right in zip(boundaries[:-1],boundaries[1:]):result[order[left:right]]=(left+right+1)/2
    return result

def clip_mad(values):
    center=np.median(values);spread=1.4826*np.median(np.abs(values-center))
    if not np.isfinite(spread) or spread<=0:return None
    return np.minimum(np.maximum(values,center-5*spread),center+5*spread)

def highpass(values):return values-median_filter(values,size=31,mode='nearest')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--products-dir',type=Path,required=True);parser.add_argument('--exposure-dir',type=Path,required=True);args=parser.parse_args()
    exposure=args.exposure_dir.resolve()
    assert exposure.parent==OUT and exposure.name.startswith('exposure_')
    plan=read(exposure/'RAW_DIAGNOSTIC_PLAN.json');data=read(exposure/'RAW_REFERENCE_DIAGNOSTICS.json');summary=read(exposure/'RAW_REFERENCE_SUMMARY.json')
    checked={str(p.relative_to(ROOT)):digest(p) for p in [exposure/'RAW_DIAGNOSTIC_PLAN.json',OUT/'diagnose_exposure.py',exposure/'RAW_REFERENCE_DIAGNOSTICS.json',exposure/'RAW_REFERENCE_SUMMARY.json']}
    assert digest(OUT/'diagnose_exposure.py')==plan['script_sha256']==data['script_sha256']
    assert digest(exposure/'RAW_DIAGNOSTIC_PLAN.json')==data['plan_sha256']
    for name,sha in plan['source_hashes'].items():assert digest(ROOT/name)==sha
    products={p['kind']:p for p in plan['products']}
    paths={kind:args.products_dir/Path(p['relative_path']).name for kind,p in products.items()}
    for kind,p in products.items():assert paths[kind].stat().st_size==p['bytes'] and digest(paths[kind])==p['sha256']
    with fits.open(io.BytesIO(subprocess.check_output(['gzip','-cd',str(paths['RAW'])])),memmap=False) as hd:
        raw=np.concatenate((hd[1].data[:,50:2098],hd[2].data[:,50:2098]),axis=1).astype(float);rh=hd[0].header.copy()
    with tarfile.open(paths['ANCILLARY']) as archive:
        members=[m for m in archive.getmembers() if m.name.endswith('_e2ds_A.fits')];assert len(members)==1
        assert Path(members[0].name).name==plan['raw_id']+'_e2ds_A.fits'
        with fits.open(io.BytesIO(archive.extractfile(members[0]).read()),memmap=False) as hd:
            native=np.array(hd[0].data,dtype=float);header=hd[0].header.copy()
    original=read(ROOT/plan['original_mapping']);prior=read(ROOT/plan['previous_reference_audit'])
    spec=next(s for s in original['spectra'] if s['dp_id']==plan['dp_id']);orientation=spec['grid_best']
    assert data['orientation']==orientation and spec['status']=='REGISTERED'
    assert raw.shape==(4096,4096) and native.shape==(72,4096)
    assert rh['ARCFILE'].removesuffix('.fits')==plan['raw_id'] and rh['DATE-OBS']==header['DATE-OBS']==spec['date_obs']
    assert rh['INSTRUME']==header['INSTRUME']=='HARPS' and abs(header['ESO DRS BERV']-spec['berv_km_s'])<1e-8
    candidates=[r for r in original['orders'] if r['dp_id']==plan['dp_id']]
    prior_refs={r['order']:r for r in prior['reference_audit'] if r['dp_id']==plan['dp_id']}
    metric_errors={};mismatches=[];counts={'measured_windows':0,'unavailable_windows':0,'offset_correlations':0,'valid_subwindows':0,'prior_reference_windows':0,'metrics_compared':0};max_poly_error=0.
    def equal(actual,expected,label,atol=1e-10):
        counts['metrics_compared']+=1
        if actual is None or expected is None:
            if actual is not None or expected is not None:mismatches.append({'label':label,'actual':actual,'expected':expected})
            return
        err=abs(actual-expected);metric_errors[label.split(':')[0]]=max(metric_errors.get(label.split(':')[0],0.),err)
        if not np.isfinite(err) or err>atol:mismatches.append({'label':label,'actual':actual,'expected':expected,'absolute_error':err,'tolerance':atol})
    degree=int(header['ESO DRS CAL LOC DEG CTR']);reconstructed=[]
    assert len(data['orders'])==72
    for order_record in data['orders']:
        o=order_record['order'];assert o==len(reconstructed)
        coefficients=[header['ESO DRS CAL LOC CTR'+str(o*(degree+1)+j)] for j in range(degree+1)]
        new_windows=[]
        for wi,((lo,hi),published) in enumerate(zip(plan['reference_windows_half_open'],order_record['windows'])):
            x=np.arange(lo,hi);argument=4095-x if orientation['argument_flip'] else x
            row=4095-x if orientation['row_flip'] else x
            column=np.full(len(x),coefficients[-1],dtype=float)
            for coefficient in coefficients[-2::-1]:column=coefficient+column*argument
            direct=sum(coefficient*argument.astype(float)**j for j,coefficient in enumerate(coefficients))
            max_poly_error=max(max_poly_error,float(np.max(np.abs(column-direct))))
            if orientation['column_flip']:column=4095-column
            bounds=(column>=9)&(column<4086);keep=bounds.copy();exclusions=[]
            for candidate in candidates:
                if candidate['order']==o:
                    near=np.abs(x-candidate['native_pixel'])<=80
                    if np.any(near):exclusions.append(candidate['review_id'])
                    keep=np.logical_and(keep,np.logical_not(near))
            assert published['pixel_interval_half_open']==[lo,hi] and published['samples']==int(keep.sum()) and published['excluded_ids']==exclusions and published['full_reference_geometry']==bool(bounds.all())
            record={'original_pearson':None,'spearman':None,'winsorized_pearson':None,'spatial_offset_correlations':[],'subwindows':[]}
            usable=keep.sum()>=200 and bounds.all()
            if usable:
                counts['measured_windows']+=1;assert published['status']=='MEASURED'
                low=np.floor(column).astype(int);fraction=column-low
                a=highpass(native[o,x]);aa=a[keep]
                def aperture(center):
                    total=np.zeros(len(x))
                    for delta in range(center-3,center+4):
                        total+=raw[row,low+delta]*(1-fraction)+raw[row,low+delta+1]*fraction
                    return highpass(total)
                b=aperture(0);bb=b[keep]
                record['original_pearson']=pearson(aa,bb);record['spearman']=pearson(average_ranks(aa),average_ranks(bb))
                ca,cb=clip_mad(aa),clip_mad(bb);record['winsorized_pearson']=pearson(ca,cb) if ca is not None and cb is not None else None
                for key in ['original_pearson','spearman','winsorized_pearson']:equal(record[key],published[key],f'{key}:{o}:{wi}')
                for oi,offset in enumerate(range(-4,5)):
                    value=pearson(aa,aperture(offset)[keep]);record['spatial_offset_correlations'].append(value)
                    assert published['spatial_offset_correlations'][oi]['offset_pixels']==offset
                    equal(value,published['spatial_offset_correlations'][oi]['pearson'],f'offset:{o}:{wi}:{offset}');counts['offset_correlations']+=1
                for si,start in enumerate(range(lo,hi,64)):
                    stop=min(start+64,hi);sub=keep&(x>=start)&(x<stop);expected=published['subwindows'][si]
                    assert expected['pixel_interval_half_open']==[start,stop] and expected['samples']==int(sub.sum())
                    value=pearson(a[sub],b[sub]) if sub.sum()>=40 else None
                    record['subwindows'].append(value);equal(value,expected['pearson'],f'subwindow:{o}:{wi}:{si}')
                    if value is not None:counts['valid_subwindows']+=1
            else:
                counts['unavailable_windows']+=1;assert published['status']=='INSUFFICIENT_REFERENCE'
                assert all(published[k] is None for k in ['original_pearson','spearman','winsorized_pearson'])
                assert published['spatial_offset_correlations']==[] and published['subwindows']==[]
            if o in prior_refs:
                p=prior_refs[o]['windows'][wi];assert p['samples']==int(keep.sum()) and p['excluded_ids']==exclusions
                equal(record['original_pearson'],p['correlation'],f'original_reference:{o}:{wi}');counts['prior_reference_windows']+=1
            new_windows.append(record)
        reconstructed.append(new_windows)
        ss=summary['order_summaries'][o];assert ss['order']==o
        valid=[r for r in new_windows if r['spatial_offset_correlations']]
        assert ss['measured_windows']==len(valid)
        for field,metric in [('original_pearson_median','original_pearson'),('spearman_median','spearman'),('winsorized_pearson_median','winsorized_pearson')]:
            equal(median([r[metric] for r in valid if r[metric] is not None]),ss[field],f'summary_{metric}:{o}')
        sub=[v for r in valid for v in r['subwindows'] if v is not None];assert ss['valid_64pixel_subwindows']==len(sub)
        equal(median(sub),ss['subwindow_pearson_median'],f'summary_subwindow:{o}')
        for oi,offset in enumerate(range(-4,5)):
            val=median([r['spatial_offset_correlations'][oi] for r in valid if r['spatial_offset_correlations'][oi] is not None])
            assert ss['spatial_offset_medians'][oi]['offset_pixels']==offset
            equal(val,ss['spatial_offset_medians'][oi]['pearson'],f'summary_offset:{o}:{offset}')
    assert counts['measured_windows']==summary['measured_windows'] and counts['unavailable_windows']==summary['unavailable_reference_windows']
    assert counts['measured_windows']+counts['unavailable_windows']==360
    assert counts['prior_reference_windows']==data['original_pearson_windows_verified']==summary['original_pearson_windows_verified']==5*len(prior_refs)
    assert max_poly_error<1e-9
    assert all(digest(ROOT/name)==sha for name,sha in checked.items())
    assert all(digest(ROOT/name)==sha for name,sha in plan['source_hashes'].items())
    assert all(digest(paths[kind])==p['sha256'] for kind,p in products.items())
    result={'schema':'SETI_REMAINING_REFERENCE_NUMERICAL_AUDIT_V1','dp_id':plan['dp_id'],'review_ids':plan['review_ids'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not mismatches else 'FAIL','independence':'No project analysis modules imported. Independent centered-dot Pearson, average-rank implementation, direct 7-term aperture summation, Horner coordinates checked against direct-power sums, clipping and summary reconstruction. NumPy/SciPy median filtering and Astropy FITS decoding are shared primitives.','coverage':dict(raw_pairs=1,orders=72,reference_windows=360,**counts),'max_absolute_metric_errors':metric_errors,'max_horner_vs_direct_power_column_error_pixels':max_poly_error,'metric_absolute_tolerance':1e-10,'mismatches':mismatches,'checked_outputs_sha256':checked,'auditor_script_sha256':digest(__file__),'input_product_sha256':{k:v['sha256'] for k,v in products.items()},'input_and_source_hashes_unchanged':True,'no_current_dispositions_changed':True,'limitations':['One selected exposure; no independent population or calibrated significance.','Numerical reproduction does not identify the cause of low reference correlation or any physical signal origin.','Any missing pixels remain unavailable and all existing M labels must be retained.']}
    (exposure/'RAW_NUMERICAL_AUDIT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['checked_outputs_sha256','input_product_sha256','independence','limitations']},indent=2))

if __name__=='__main__':main()
