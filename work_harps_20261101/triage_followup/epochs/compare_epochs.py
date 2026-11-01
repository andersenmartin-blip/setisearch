"""Descriptive, fixed-location comparison of the ten original HARPS hits.

No new V2 inputs are opened. Local metrics are not calibrated significances.
Both supplied barycentric air and provisional topocentric air frames are kept.
"""
from pathlib import Path
import csv, json, hashlib, sys
from datetime import datetime, timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from harps_detector import read_spectrum, analyze_arrays
C=299792.458
OI={'H03':5577.339,'H06':5577.339,'H07':6300.304}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(x):
    if isinstance(x,dict): return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list): return [clean(v) for v in x]
    if isinstance(x,(float,np.floating)) and not np.isfinite(x): return None
    if isinstance(x,np.generic):return x.item()
    return x

hits=list(csv.DictReader((ROOT/'production/HIT_DISPOSITIONS.csv').open()))
manifest=json.loads((ROOT/'acquisition/DOWNLOAD_MANIFEST.json').read_text())
main=[x for x in manifest if x['role']=='main_unopened']
cfg=json.loads((ROOT/'code/DETECTOR_CONFIG.json').read_text())
sources=[];cache={}
for item in main:
    if item['canonical_target'] not in {x['canonical_target'] for x in hits}:continue
    p=ROOT/'data/main'/Path(item['path']).name
    assert digest(p)==item['sha256']
    wave,flux,meta=read_spectrum(p)
    assert meta['SPECSYS']=='BARYCENT' and meta['wavelength_ucd']=='em.wl;obs.atmos'
    cache[item['dp_id']]=(wave,flux,meta)
    sources.append({'dp_id':item['dp_id'],'path':str(p.relative_to(ROOT)),'sha256':item['sha256']})

rows=[];plotdata={};details=[]
for hit in hits:
    target=hit['canonical_target'];hid=hit['hit_id']
    epochs=sorted([x for x in main if x['canonical_target']==target],key=lambda x:x['primary_header']['MJD-OBS'])
    assert len(epochs)==5
    bary_center=float(hit['wave_peak_angstrom'])
    observed_top_center=bary_center/(1+float(hit['berv_km_s'])/C)
    centers={'BARYCENT_AIR':bary_center,'TOPOCENTRIC_AIR_APPROX':OI.get(hid,observed_top_center)}
    for frame,center in centers.items():
        for item in epochs:
            wave,flux,meta=cache[item['dp_id']]
            correction=1+meta['berv_km_s']/C
            w=wave if frame=='BARYCENT_AIR' else wave/correction
            take=np.flatnonzero((w>=center-.65)&(w<=center+.65))
            assert len(take)>110
            wp,fp=w[take],flux[take]
            valid=np.isfinite(fp)&(fp!=0)
            # Exclude the signal core; fit a line between median left/right sidebands.
            left=valid&(wp>=center-.4)&(wp<=center-.1)
            right=valid&(wp>=center+.1)&(wp<=center+.4)
            assert left.sum()>=20 and right.sum()>=20
            xl,xr=np.median(wp[left]),np.median(wp[right])
            yl,yr=np.median(fp[left]),np.median(fp[right])
            base=yl+(wp-xl)*(yr-yl)/(xr-xl)
            res=fp-base
            side=left|right
            side_median=np.median(res[side])
            scale=1.4826*np.median(np.abs(res[side]-side_median))
            assert scale>0
            core=valid&(np.abs(wp-center)<=.03)
            idx=np.flatnonzero(core)[np.argmax(res[core])]
            full_index=int(take[idx])
            v1win=flux[full_index-50:full_index+51]
            v1med=float(np.median(v1win));v1std=float(np.std(v1win,ddof=0))
            # Frozen run list is read, not re-selected; transform its peak coordinates.
            pr=json.loads((ROOT/'production/spectra'/(item['dp_id'].replace(':','_')+'.json')).read_text())
            matching=[]
            for event in pr['all_threshold_runs']:
                ew=event['wave_peak_angstrom']/(correction if frame!='BARYCENT_AIR' else 1)
                if abs(ew-center)<=.03:
                    matching.append({'status':event['status'],'run_pixels':event['run_pixels'],
                                     'peak_wave_in_frame_angstrom':ew,'peak_local_contrast':event['peak_local_contrast']})
            record=dict(hit_id=hid,canonical_target=target,frame=frame,
                comparison_center_angstrom=center,center_basis='known_OI_air_reference' if frame!='BARYCENT_AIR' and hid in OI else 'original_hit_peak',
                dp_id=item['dp_id'],date_obs_utc=meta['DATE-OBS'],berv_km_s=meta['berv_km_s'],
                is_original_hit=item['dp_id']==hit['dp_id'],exptime_seconds=meta['EXPTIME'],
                peak_within_0p03_angstrom=float(wp[idx]),peak_offset_angstrom=float(wp[idx]-center),
                local_peak_flux_adu=float(fp[idx]),sideband_baseline_at_peak_adu=float(base[idx]),
                peak_residual_adu=float(res[idx]),sideband_mad_scale_adu=float(scale),
                peak_over_sideband_scale=float(res[idx]/scale),
                original_detector_local_contrast=(float(fp[idx])-v1med)/v1std,
                v1_matching_preliminary_hits=sum(x['status']=='PRELIMINARY_EMISSION_HIT' for x in matching),
                v1_matching_short_runs=sum(x['status']=='SHORT_RUN' for x in matching),
                v1_matching_wide_runs=sum(x['status']=='WIDE_RUN' for x in matching),
                v1_matching_max_run_pixels=max([x['run_pixels'] for x in matching],default=0))
            rows.append(record)
            details.append({**record,'matching_original_runs':matching})
            plotdata.setdefault((hid,frame),[]).append((wp-center,res/scale,record))

with (OUT/'EPOCH_COMPARISON.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

summary=[]
for hit in hits:
    hid=hit['hit_id'];r=[x for x in rows if x['hit_id']==hid]
    summary.append({'hit_id':hid,'target':hit['canonical_target'],
        'barycentric_epochs_with_v1_hit':sum(x['v1_matching_preliminary_hits']>0 for x in r if x['frame']=='BARYCENT_AIR'),
        'topocentric_epochs_with_v1_hit':sum(x['v1_matching_preliminary_hits']>0 for x in r if x['frame']=='TOPOCENTRIC_AIR_APPROX'),
        'topocentric_reference_angstrom':OI.get(hid),
        'other_epoch_topocentric_peak_over_scale':[{'date':x['date_obs_utc'],'ratio':x['peak_over_sideband_scale'],'offset_angstrom':x['peak_offset_angstrom'],'v1_run_pixels':x['v1_matching_max_run_pixels']} for x in r if x['frame']=='TOPOCENTRIC_AIR_APPROX' and not x['is_original_hit']],
        'interpretation':'No absence-alone veto. Near-center peak metrics are descriptive and include a maximum over the fixed +/-0.03 Angstrom core.'})

protocol={
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Original ten hit locations, all five already analyzed main exposures per associated target; no V2, development or new validation inputs.',
 'counts':{'hits':len(hits),'unique_existing_spectra':len(cache),'rows':len(rows),'epochs_per_hit_per_frame':5},
 'script_sha256':digest(Path(__file__)),
 'input_table_sha256':digest(ROOT/'production/HIT_DISPOSITIONS.csv'),
 'source_files':sources,
 'method':{'frames':['BARYCENT_AIR','TOPOCENTRIC_AIR_APPROX'],
  'topocentric_formula':'lambda_bary/(1+BERV/299792.458); exact HARPS_3.8 implementation still to be checked.',
  'center_choice':'Original hit barycentric peak in barycentric frame; its provisional transformed peak in topocentric frame, except H03/H06=5577.339 and H07=6300.304 Angstrom O I air references.',
  'core_halfwidth_angstrom':.03,'sideband_offsets_angstrom':[[-.4,-.1],[.1,.4]],
  'baseline':'Linear interpolation of the median flux in left and right sidebands at their median wavelengths.',
  'noise_scale':'1.4826 times median absolute deviation of sideband residuals from their median; descriptive only; resampling covariance and line structure are not modeled.',
  'v1_runs':'Original saved detector run peak falls within +/-0.03 Angstrom of comparison center after frame conversion; no detector retuning.'},
 'limitations':['A local maximum is chosen inside the fixed core, so ratios are not a significance test.',
  'Instrumental, stellar and atmospheric profiles can mix; sideband structure can change the scale.',
  'Barycentric comparison is not a complete stellar-rest-frame correction; no stellar velocity model is imposed.',
  'Non-repetition is not grounds to reject a transient.',
  'The three O I matches are descriptive evidence, not final raw-detector classification.'],
 'summary':summary,'all_comparisons':details}
(OUT/'EPOCH_COMPARISON.json').write_text(json.dumps(clean(protocol),indent=2,allow_nan=False)+'\n')

for frame,label in [('BARYCENT_AIR','Barycentric air'),('TOPOCENTRIC_AIR_APPROX','Approximate topocentric air')]:
    fig,axes=plt.subplots(5,2,figsize=(14,18),layout='constrained')
    colors=plt.colormaps['tab10'](np.linspace(0,.8,5))
    for ax,hit in zip(axes.flat,hits):
        hid=hit['hit_id']
        for color,(x,y,r) in zip(colors,plotdata[(hid,frame)]):
            show=np.abs(x)<=.12
            ax.plot(x[show],y[show],color=color,lw=1.6 if r['is_original_hit'] else 1,
                    marker='.' if r['is_original_hit'] else None,ms=3,
                    label=r['date_obs_utc'][:10]+(' original' if r['is_original_hit'] else ''))
        ax.axvspan(-.03,.03,color='grey',alpha=.10)
        ax.axvline(0,color='black',ls=':',lw=.7);ax.axhline(0,color='black',lw=.5)
        ax.set_title(hid+' '+hit['canonical_target']+' | '+('O I reference' if frame!='BARYCENT_AIR' and hid in OI else 'original peak'))
        ax.set_xlabel('Wavelength offset (Angstrom)');ax.set_ylabel('Residual / sideband MAD scale')
        ax.legend(fontsize=7,loc='upper right');ax.grid(alpha=.15)
    fig.suptitle(label+' comparison of all five existing epochs per hit\nFixed +/-0.03 A search window; ratios are descriptive, not calibrated significance',fontsize=15)
    fig.savefig(OUT/('EPOCHS_'+frame+'.png'),dpi=130);plt.close(fig)
print(json.dumps({'counts':protocol['counts'],'summary':summary},indent=2))
