"""Post-hoc line-region context, recorded before detailed flux measurements.

No detection settings or original dispositions are modified.
"""
from pathlib import Path
import csv,json,hashlib,io,tarfile,datetime,collections
import numpy as np
from astropy.io import fits
from scipy.ndimage import median_filter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];V2=BASE/'v2'
PLAN=json.loads((OUT/'PLAN.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save_csv(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def finite(x):return float(x) if np.isfinite(x) else None
source=V2/'triage_batch02/CUMULATIVE_DISPOSITIONS.csv'
assert sha(source)==PLAN['input_table_sha256']
events=[r for r in csv.DictReader(source.open()) if r['current_followup_status']=='UNRESOLVED_SPECTRAL_FEATURE']
assert len(events)==64
products=[]
for b in ['triage_batch01','triage_batch02']:
    products.extend(json.loads((V2/b/'products/MANIFEST.json').read_text())['products'])
products=[r for r in products if r['kind']=='ANCILLARY'];assert len(products)==92
rv=[]
for r in products:
    p=BASE/r['relative_path'];assert sha(p)==r['sha256']
    with tarfile.open(p) as t:
        ms=[m for m in t if '_ccf_' in m.name and m.name.endswith('_A.fits')]
        rec=dict(dp_id=r['dp_id'],ancillary_path=r['relative_path'],ancillary_sha256=r['sha256'],ccf_members=len(ms),status='MISSING_OR_AMBIGUOUS',ccf_member='',date_obs='',rvc_km_s=None,rv_uncorrected_km_s=None,ccf_noise_km_s=None,ccf_fwhm_km_s=None,ccf_mask='',target_planning_rv_km_s=None,berv_km_s=None)
        if len(ms)==1:
            with fits.open(io.BytesIO(t.extractfile(ms[0]).read())) as hd:
                h=hd[0].header
                rec.update(status='AVAILABLE',ccf_member=ms[0].name,date_obs=h['DATE-OBS'],rvc_km_s=finite(h.get('ESO DRS CCF RVC',np.nan)),rv_uncorrected_km_s=finite(h.get('ESO DRS CCF RV',np.nan)),ccf_noise_km_s=finite(h.get('ESO DRS CCF NOISE',np.nan)),ccf_fwhm_km_s=finite(h.get('ESO DRS CCF FWHM',np.nan)),ccf_mask=h.get('ESO DRS CCF MASK',''),target_planning_rv_km_s=finite(h.get('ESO TEL TARG RADVEL',np.nan)),berv_km_s=finite(h.get('ESO DRS BERV',np.nan)))
        rv.append(rec)
save_csv(OUT/'RV_HEADERS_92.csv',rv)
(OUT/'RV_HEADERS_92.json').write_text(json.dumps(dict(method='Read original CCF_A headers only; not a new RV fit.',exposures=rv),indent=2)+'\n')
by_dp={r['dp_id']:r for r in rv}
input_manifest={r['dp_id']:r for r in json.loads((V2/'acquisition/DOWNLOAD_MANIFEST.json').read_text())}
records=[];(OUT/'profiles').mkdir(exist_ok=True);(OUT/'figures').mkdir(exist_ok=True)
for h in events:
    m=input_manifest[h['dp_id']];p=BASE/m['relative_path'];assert sha(p)==m['sha256']
    with fits.open(p) as hd:
        assert hd[0].header['SPECSYS']=='BARYCENT'
        assert hd[1].header['TUNIT1'].lower()=='angstrom'
        assert hd[1].header['TUCD1']=='em.wl;obs.atmos'
        wave=np.asarray(hd[1].data['WAVE'][0],dtype=float);flux=np.asarray(hd[1].data['FLUX'][0],dtype=float);err=np.asarray(hd[1].data['ERR'][0],dtype=float)
        berv=float(hd[0].header['ESO DRS BERV'])
        assert hd[0].header['DATE-OBS']==by_dp[h['dp_id']]['date_obs']
    center=float(h['fitted_center_bary_air_angstrom']);r=by_dp[h['dp_id']];velocity=r['rvc_km_s']
    rest=center/(1+velocity/299792.458) if velocity is not None else None
    off=wave-center;sel=abs(off)<=10
    ww=wave[sel];ff=flux[sel];ee=err[sel];xx=off[sel]
    valid=np.isfinite(ww)&np.isfinite(ff)&np.isfinite(ee)&(ee>0)
    core=valid&(abs(xx)<=.025);peak=valid&(abs(xx)<=.06)
    med3=median_filter(ff,size=3,mode='nearest')
    rec=dict(review_id=h['review_id'],target=h['canonical_target'],dp_id=h['dp_id'],center_bary_air_angstrom=center,
        berv_km_s=berv,approx_topocentric_air_angstrom=center/(1+berv/299792.458),rvc_km_s=velocity,
        ccf_noise_km_s=r['ccf_noise_km_s'],ccf_mask=r['ccf_mask'],approx_stellar_air_angstrom=rest,
        broad_region='OTHER_OR_UNIDENTIFIED',core_samples=int(core.sum()),core_median_adu=finite(np.median(ff[core])),
        central_median3_peak_adu=finite(np.max(med3[peak])),original_status=h['current_followup_status'],disposition_changed=False,
        adp_sha256=m['sha256'],rv_source_member=r['ccf_member'])
    for band in PLAN['bands']:
        if rest is not None and band['low_air_angstrom']<=rest<=band['high_air_angstrom']:rec['broad_region']=band['label']
    for lo,hi in [(1,5),(3,10)]:
        mask=valid&(abs(xx)>=lo)&(abs(xx)<=hi)
        prefix=f'context_{lo}_{hi}'
        rec[prefix+'_samples']=int(mask.sum())
        for quantile in [50,90,95]:
            level=float(np.percentile(ff[mask],quantile))
            rec[f'{prefix}_p{quantile}_adu']=level
            rec[f'core_over_{prefix}_p{quantile}']=rec['core_median_adu']/level if level>0 else None
            rec[f'peak_over_{prefix}_p{quantile}']=rec['central_median3_peak_adu']/level if level>0 else None
    rec['left_local_min_adu']=finite(np.min(med3[valid&(xx>=-.5)&(xx<=-.05)]))
    rec['right_local_min_adu']=finite(np.min(med3[valid&(xx>=.05)&(xx<=.5)]))
    rec['profile_file']='profiles/'+h['review_id']+'.npz'
    np.savez_compressed(OUT/rec['profile_file'],wave_bary_air=ww,flux_adu=ff,err_adu=ee,valid=valid)
    records.append(rec)
save_csv(OUT/'CONTEXT_64.csv',records)

# Deterministic maximum-span grouping, with every original event retained.
groups=[]
for target in dict.fromkeys(r['target'] for r in records):
    chosen=sorted([r for r in records if r['target']==target],key=lambda r:r['approx_stellar_air_angstrom'])
    batch=[]
    for r in chosen:
        if batch and r['approx_stellar_air_angstrom']-batch[0]['approx_stellar_air_angstrom']>.06:
            groups.append(batch);batch=[]
        batch.append(r)
    if batch:groups.append(batch)
group_rows=[]
for i,group in enumerate(groups):
    group_rows.append(dict(group_id=f'L{i+1:02d}',target=group[0]['target'],events=[r['review_id'] for r in group],
        approximate_stellar_air_median_angstrom=float(np.median([r['approx_stellar_air_angstrom'] for r in group])),
        span_angstrom=float(np.ptp([r['approx_stellar_air_angstrom'] for r in group])),
        rvc_span_km_s=float(np.ptp([r['rvc_km_s'] for r in group])),representative=min(group,key=lambda r:r['review_id'])['review_id'],
        broad_region=group[0]['broad_region']))
clusters=[];batch=[]
for g in sorted(group_rows,key=lambda x:x['approximate_stellar_air_median_angstrom']):
    if batch and g['approximate_stellar_air_median_angstrom']-batch[0]['approximate_stellar_air_median_angstrom']>.10:
        clusters.append(batch);batch=[]
    batch.append(g)
if batch:clusters.append(batch)
cross=[]
for i,cl in enumerate(clusters):
    cross.append(dict(cluster_id=f'C{i+1:02d}',groups=[g['group_id'] for g in cl],targets=list(dict.fromkeys(g['target'] for g in cl)),events=[e for g in cl for e in g['events']],
        min_stellar_air_angstrom=min(g['approximate_stellar_air_median_angstrom'] for g in cl),max_stellar_air_angstrom=max(g['approximate_stellar_air_median_angstrom'] for g in cl),
        interpretation='Descriptive rest-frame proximity, not a transition identification or independence test.'))
(OUT/'GROUPS.json').write_text(json.dumps(dict(method=PLAN['groups'],groups=group_rows,cross_target_clusters=cross),indent=2)+'\n')
by_id={r['review_id']:r for r in records}
for start in range(0,len(group_rows),4):
    fig,axs=plt.subplots(4,2,figsize=(13,11));fig.subplots_adjust(left=.07,right=.98,bottom=.06,top=.91,wspace=.25,hspace=.5)
    for j,g in enumerate(group_rows[start:start+4]):
        r=by_id[g['representative']];d=np.load(OUT/r['profile_file']);off=d['wave_bary_air']-r['center_bary_air_angstrom'];flux=d['flux_adu'];scale=r['context_3_10_p95_adu']
        for ax,lim in [(axs[j,0],.6),(axs[j,1],10)]:
            keep=abs(off)<=lim;ax.plot(off[keep],flux[keep]/scale,lw=.8);ax.axvline(0,c='red',ls=':',lw=.8);ax.axhline(1,c='grey',lw=.7)
            ax.axhline(r['context_1_5_p95_adu']/scale,c='orange',ls='--',lw=.7);ax.set_xlim(-lim,lim);ax.set_ylabel('Flux / wider local P95',fontsize=8);ax.set_xlabel('Barycentric-air offset from saved peak (Å)',fontsize=8);ax.tick_params(labelsize=8)
        axs[j,0].set_title(g['group_id']+' '+r['target']+' '+r['review_id']+f' | approximate stellar {r["approx_stellar_air_angstrom"]:.3f} Å',fontsize=9)
        axs[j,1].set_title(r['broad_region']+f' | CCF RV {r["rvc_km_s"]:+.3f} km/s',fontsize=9)
    for j in range(len(group_rows[start:start+4]),4):
        for ax in axs[j]:ax.set_visible(False)
    fig.suptitle('Wider spectral context: all target/feature groups, earliest saved event per group\nGrey=P95 at 3–10 Å; orange=P95 at 1–5 Å. Percentiles are not a calibrated stellar continuum.',fontsize=12)
    fig.savefig(OUT/'figures'/f'CONTEXT_{start//4+1:02d}.png',dpi=110);plt.close(fig)
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),events=len(records),targets=len(set(r['target'] for r in records)),
    groups=len(group_rows),ccf_header_exposures=len(rv),ccf_headers_available=sum(r['status']=='AVAILABLE' for r in rv),
    events_with_ccf_rvc=sum(r['rvc_km_s'] is not None for r in records),broad_region_counts=dict(collections.Counter(r['broad_region'] for r in records)),
    core_below_context1_5_p95=sum(r['core_over_context_1_5_p95']<1 for r in records),core_below_context3_10_p95=sum(r['core_over_context_3_10_p95']<1 for r in records),
    median3_peak_below_context1_5_p95=sum(r['peak_over_context_1_5_p95']<1 for r in records),median3_peak_below_context3_10_p95=sum(r['peak_over_context_3_10_p95']<1 for r in records),
    cross_target_clusters_with_multiple_targets=[x for x in cross if len(x['targets'])>1],all_dispositions_unchanged=True,
    limits='Post-hoc spectral-context annotations. Percentile upper envelopes are not true continua; broad bandpass membership does not identify a line, and CCF rest-frame approximation is not precision wavelength calibration. No new detector veto or statistical significance is assigned.',
    plan_sha256=sha(OUT/'PLAN.json'),code_sha256=sha(Path(__file__)),input_table_sha256=sha(source))
(OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
