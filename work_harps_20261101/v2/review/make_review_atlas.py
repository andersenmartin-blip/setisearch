"""Descriptive review plots and O I flags for EVERY accepted V2 event.

This post-analysis aid neither changes the frozen detector nor rejects hits.
IDs follow the saved V2_HITS.csv order; no ranking or selection is performed.
"""
from pathlib import Path
import csv,json,sys,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'code'))
from harps_detector import read_spectrum
OUT=BASE/'v2/review/atlas';OUT.mkdir(exist_ok=True)
hits=list(csv.DictReader((BASE/'v2/production/V2_HITS.csv').open()))
manifest={r['dp_id']:r for r in json.loads((BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json').read_text())}
cache={};index=[]
for start in range(0,len(hits),12):
    fig,axes=plt.subplots(4,3,figsize=(13,12),layout='constrained')
    page=start//12+1
    for j,ax in enumerate(axes.flat):
        n=start+j
        if n>=len(hits): ax.set_visible(False);continue
        h=hits[n];m=manifest[h['dp_id']]
        if h['dp_id'] not in cache:
            w,f,meta=read_spectrum(BASE/m['relative_path'])
            assert meta['sha256']==h['input_sha256']
            cache[h['dp_id']]=(w,f)
        w,f=cache[h['dp_id']];k=int(h['seed_index']);off=np.arange(-50,51)
        baseline=float(h['sideband_intercept_adu'])+float(h['sideband_slope_adu_per_pixel'])*off
        scale=float(h['sideband_mad_adu']);center=float(h['fitted_center_angstrom'])
        x=w[k+off]-center;y=(f[k+off]-baseline)/scale
        g=float(h['amplitude_over_sideband_mad'])*np.exp(-.5*(x/(float(h['fwhm_model_angstrom'])/2.354820045))**2)
        ax.plot(x,y,'.-',lw=.8,ms=2,label='data - baseline');ax.plot(x,g,color='tab:orange',lw=1,label='frozen profile')
        ax.axvspan(w[k-12]-center,w[k+12]-center,color='grey',alpha=.08)
        ax.axhline(0,color='black',lw=.4);ax.set_xlim(-.5,.5)
        hid=f'V2-{n+1:04d}';berv=m['primary_header']['HIERARCH ESO DRS BERV']
        top=center/(1+berv/299792.458)
        nearest=min([5577.339,6300.304],key=lambda r:abs(top-r));delta=top-nearest
        flag=abs(delta)<=.03
        ax.set_title(f'{hid} {h["canonical_target"]}  {h["date_obs"][:10]}\n{center:.4f} Å bary · A/MAD {float(h["amplitude_over_sideband_mad"]):.1f} · cos {float(h["profile_cosine"]):.2f}',fontsize=8)
        ax.set_xlabel('Barycentric air offset (Å)',fontsize=8);ax.set_ylabel('Residual / sideband MAD',fontsize=8);ax.tick_params(labelsize=7)
        index.append(dict(review_id=hid,dp_id=h['dp_id'],target=h['canonical_target'],seed_index=k,
            fitted_center_bary_air_angstrom=center,berv_km_s=berv,approx_topocentric_air_angstrom=top,
            nearest_of_two_OI_air_references_angstrom=nearest,offset_angstrom=delta,
            OI_0p03_angstrom_flag=flag,origin_status='UNREVIEWED',atlas_file=f'atlas/ATLAS_{page:02d}.png',panel=j+1))
    fig.suptitle(f'All accepted V2 events · page {page}/28 · UNREVIEWED\nScores are not calibrated significance; orange curve is the saved model',fontsize=13)
    fig.savefig(OUT/f'ATLAS_{page:02d}.png',dpi=100);plt.close(fig)
with (OUT.parent/'REVIEW_INDEX.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(index[0]));w.writeheader();w.writerows(index)
summary=dict(total_events=len(index),panels=len(index),pages=28,unique_input_spectra=len(cache),
    OI_two_line_flagged=sum(r['OI_0p03_angstrom_flag'] for r in index),all_origin_status='UNREVIEWED',
    interpretation='Post-hoc +/-0.03 A flags around only O I 5577.339 and 6300.304 air wavelengths. Descriptive priority flags, not an airglow classifier or rejection. Approximate classical BERV inverse; many other atmospheric/stellar/instrument lines not checked.',
    input_hits_sha256=hashlib.sha256((BASE/'v2/production/V2_HITS.csv').read_bytes()).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT.parent/'ATLAS_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')

v=json.loads((BASE/'v2/validation/results/SUMMARY.json').read_text())
fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained');xx=np.arange(4)
for offset,key,label,color in [(-.18,'v1','V1 original rule','#8c9aa9'),(.18,'v2','V2 fixed profile','#197f94')]:
    vals=[r[key] for r in v['by_amplitude']]
    bars=ax.bar(xx+offset,vals,width=.34,label=label,color=color)
    ax.bar_label(bars,labels=[str(n)+'/48' for n in vals],padding=3)
ax.set_xticks(xx,['4×','8×','16×','32×']);ax.set_ylim(0,56);ax.set_yticks([0,12,24,36,48])
ax.set_xlabel('Injected peak / original local standard deviation');ax.set_ylabel('Recovered injections')
ax.set_title('Fresh paired validation: V2 recovers more inserted lines');ax.legend(loc='upper left')
fig.text(.5,-.015,'Four spectra of one star; 16 reused background patches and 48 geometries. Not a global sensitivity estimate.',ha='center',fontsize=8)
fig.savefig(OUT.parent/'VALIDATION_COMPARISON.png',dpi=140,bbox_inches='tight');plt.close(fig)
print(json.dumps(summary,indent=2))
