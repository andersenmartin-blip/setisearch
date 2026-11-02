"""Fixed descriptive raw/native diagnostic for the first frozen M exposure.

Retains original mapping, candidate exclusions and Pearson gate. Additional
rank, winsorized, subwindow and offset metrics are diagnostics only; they do
not substitute for the original gate or support physical-origin labels.
"""
from pathlib import Path
import datetime
import hashlib
import io
import json
import subprocess
import argparse
import tarfile
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
from scipy.stats import rankdata

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
BASE = ROOT / 'work_harps_20261101'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def save(name, value):
    p=OUT/name
    if p.exists(): raise RuntimeError('Refusing existing diagnostic output: '+name)
    p.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def corr(a,b):
    if len(a)<3 or not np.isfinite(a).all() or not np.isfinite(b).all(): return None
    if np.std(a)==0 or np.std(b)==0: return None
    v=float(np.corrcoef(a,b)[0,1])
    return v if np.isfinite(v) else None


def winsor(a):
    median=np.median(a);mad=1.4826*np.median(np.abs(a-median))
    if not np.isfinite(mad) or mad<=0: return None
    return np.clip(a,median-5*mad,median+5*mad)


def hp(a):return a-median_filter(a,size=31,mode='nearest')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--products-dir',type=Path,required=True,help='Directory containing the two restored canonical basenames')
    args=parser.parse_args()
    plan=json.loads((OUT/'RAW_DIAGNOSTIC_PLAN.json').read_text())
    product_path=lambda item: args.products_dir/Path(item['relative_path']).name
    assert digest(Path(__file__))==plan['script_sha256']
    for path,sha in plan['source_hashes'].items():assert digest(ROOT/path)==sha,path
    for item in plan['products']:
        path=product_path(item);assert path.stat().st_size==item['bytes'] and digest(path)==item['sha256']
    assert plan['orders']==list(range(72)) and plan['spatial_offsets']==list(range(-4,5))
    assert plan['reference_windows_half_open']==[[128,768],[896,1536],[1664,2304],[2432,3072],[3200,3968]]
    original=json.loads((ROOT/plan['original_mapping']).read_text())
    previous=json.loads((ROOT/plan['previous_reference_audit']).read_text())
    dp=plan['dp_id'];spec=next(s for s in original['spectra'] if s['dp_id']==dp)
    flips=spec['grid_best'];assert spec['status']=='REGISTERED'
    prior_refs={r['order']:r for r in previous['reference_audit'] if r['dp_id']==dp}
    candidates=[r for r in original['orders'] if r['dp_id']==dp]
    assert sorted(set(r['review_id'] for r in candidates))==plan['candidate_exclusion_ids']
    product={r['kind']:r for r in plan['products']}
    with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(product_path(product['RAW']))],check=True,capture_output=True).stdout),memmap=False) as hdus:
        raw=np.hstack([hdus[1].data[:,50:2098],hdus[2].data[:,50:2098]]).astype(float);rh=hdus[0].header.copy()
    with tarfile.open(product_path(product['ANCILLARY'])) as archive:
        members=[m for m in archive if m.name.endswith('_e2ds_A.fits')]
        assert len(members)==1 and Path(members[0].name).name==plan['raw_id']+'_e2ds_A.fits'
        with fits.open(io.BytesIO(archive.extractfile(members[0]).read()),memmap=False) as hdus:
            native=hdus[0].data.astype(float);header=hdus[0].header.copy()
    assert raw.shape==(4096,4096) and native.shape==(72,4096)
    assert rh['ARCFILE'].removesuffix('.fits')==plan['raw_id']
    assert rh['DATE-OBS']==header['DATE-OBS']==spec['date_obs']
    assert rh['INSTRUME']==header['INSTRUME']=='HARPS'
    assert abs(header['ESO DRS BERV']-spec['berv_km_s'])<1e-8
    degree=int(header['ESO DRS CAL LOC DEG CTR'])
    output=[];baseline_matches=0;invalid_windows=0
    for order in plan['orders']:
        windows=[]
        for window_index,(lo,hi) in enumerate(plan['reference_windows_half_open']):
            x=np.arange(lo,hi);yy=4095-x if flips['row_flip'] else x
            argument=4095-x if flips['argument_flip'] else x
            coeff=[header['ESO DRS CAL LOC CTR'+str(order*(degree+1)+j)] for j in range(degree+1)]
            columns=np.polynomial.polynomial.polyval(argument,coeff)
            if flips['column_flip']:columns=4095-columns
            bounds=(columns>=9)&(columns<4086);mask=bounds.copy();excluded=[]
            for candidate in candidates:
                if candidate['order']==order:
                    near=np.abs(x-candidate['native_pixel'])<=80
                    if near.any():excluded.append(candidate['review_id'])
                    mask &= ~near
            rec=dict(pixel_interval_half_open=[lo,hi],samples=int(mask.sum()),excluded_ids=excluded,
                full_reference_geometry=bool(bounds.all()),status='INSUFFICIENT_REFERENCE',
                original_pearson=None,spearman=None,winsorized_pearson=None,spatial_offset_correlations=[],subwindows=[])
            if mask.sum()>=200 and bounds.all():
                low=np.floor(columns).astype(int);fraction=columns-low
                values=np.stack([raw[yy,low+offset]*(1-fraction)+raw[yy,low+offset+1]*fraction for offset in range(-8,9)])
                a=hp(native[order,x]);b=hp(values[5:12].sum(axis=0))
                aa,bb=a[mask],b[mask];wa,wb=winsor(aa),winsor(bb)
                rec.update(status='MEASURED',original_pearson=corr(aa,bb),spearman=corr(rankdata(aa),rankdata(bb)),
                    winsorized_pearson=corr(wa,wb) if wa is not None and wb is not None else None)
                for offset in plan['spatial_offsets']:
                    shifted=hp(values[5+offset:12+offset].sum(axis=0))
                    rec['spatial_offset_correlations'].append(dict(offset_pixels=offset,pearson=corr(aa,shifted[mask])))
                for start in range(lo,hi,64):
                    stop=min(start+64,hi);submask=mask & (x>=start)&(x<stop)
                    rec['subwindows'].append(dict(pixel_interval_half_open=[start,stop],samples=int(submask.sum()),
                        pearson=corr(a[submask],b[submask]) if submask.sum()>=40 else None))
            else:invalid_windows+=1
            if order in prior_refs:
                prior=prior_refs[order]['windows'][window_index]
                assert prior['samples']==rec['samples'] and prior['excluded_ids']==excluded
                assert (prior['correlation'] is None)==(rec['original_pearson'] is None)
                if prior['correlation'] is not None:
                    assert np.isclose(prior['correlation'],rec['original_pearson'],rtol=0,atol=1e-12)
                baseline_matches+=1
            windows.append(rec)
        output.append(dict(order=order,was_previously_selected_reference=order in prior_refs,windows=windows))
    # Preserve every original reference and all control orders, no result-based selection.
    save('RAW_REFERENCE_DIAGNOSTICS.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        plan_sha256=digest(OUT/'RAW_DIAGNOSTIC_PLAN.json'),script_sha256=digest(Path(__file__)),
        dp_id=dp,orientation=flips,orders=output,original_pearson_windows_verified=baseline_matches))
    measured=[w for order in output for w in order['windows'] if w['status']=='MEASURED']
    def summarize(order):
        rs=[w for w in order['windows'] if w['status']=='MEASURED']
        def med(key):
            values=[w[key] for w in rs if w[key] is not None]
            return float(np.median(values)) if values else None
        sub=[w['pearson'] for r in rs for w in r['subwindows'] if w['pearson'] is not None]
        return dict(order=order['order'],measured_windows=len(rs),original_pearson_median=med('original_pearson'),
            spearman_median=med('spearman'),winsorized_pearson_median=med('winsorized_pearson'),
            valid_64pixel_subwindows=len(sub),subwindow_pearson_median=float(np.median(sub)) if sub else None,
            spatial_offset_medians=[dict(offset_pixels=o,pearson=float(np.median(v)) if v else None)
              for o in plan['spatial_offsets']
              for v in [[r['spatial_offset_correlations'][o+4]['pearson'] for r in rs if r['spatial_offset_correlations'][o+4]['pearson'] is not None]]])
    summary=dict(status='COMPLETE_DIAGNOSTIC_ONLY_NO_RECLASSIFICATION',dp_id=dp,records_followed=['V2-0149'],
        raw_pairs=1,orders=72,reference_windows=360,measured_windows=len(measured),
        unavailable_reference_windows=invalid_windows,original_pearson_windows_verified=baseline_matches,
        original_gate_unchanged=True,current_code='M',origin_assignments=0,coordinates_adjusted=False,
        parent_dispositions_changed=False,comparison_population='All72 orders in same single selected exposure; descriptive controls, not independent validation.',
        products=plan['products'],order_summaries=[summarize(o) for o in output],
        limitations=['Only one exposure, selected as the first stable M queue entry.',
        'Rank, winsorized and subwindow metrics are not acceptance gates and do not justify relaxing the original Pearson gate.',
        'Spatial-offset curves probe fixed apertures; their maxima do not refit mapping or select new coordinates.',
        'Order0 candidate trace is outside active detector. No statistic reconstructs missing pixels.',
        'No cosmic-ray mask, raw background model or pipeline-equivalent extraction is inferred from correlation changes.'])
    for path,sha in plan['source_hashes'].items():assert digest(ROOT/path)==sha,path
    for item in plan['products']:assert digest(product_path(item))==item['sha256']
    save('RAW_REFERENCE_SUMMARY.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['products','order_summaries']},indent=2))

if __name__=='__main__':main()
