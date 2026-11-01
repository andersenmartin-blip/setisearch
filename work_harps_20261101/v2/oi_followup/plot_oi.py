"""Three-line comparison in the fixed topocentric frame; retain non-detections."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;FIG=OUT/'figures';FIG.mkdir(exist_ok=True)
native=json.loads((OUT/'NATIVE_MEASUREMENTS.json').read_text());epoch=json.loads((OUT/'ALL_EPOCH_MEASUREMENTS.json').read_text())
lines=['OI5577','OI6300','OI6363']
def draw(ax,r,legend=True):
    d=np.load(OUT/r['array']);x=d['offset_angstrom'];scale=r['continuum_intercept_adu'];res=(d['flux_adu']-d['baseline_adu'])/scale
    ax.plot(x,res,'.-',ms=2,lw=.7,label='data minus linear baseline')
    width=r['reference_air_angstrom']/115000/np.sqrt(8*np.log(2));g=np.exp(-.5*(x/width)**2)*r['fixed_amplitude_adu']/scale
    ax.plot(x,g,color='darkorange',lw=.9,label='fixed-center profile')
    ax.axvline(0,color='grey',ls=':',lw=.7);ax.axhline(0,color='grey',lw=.5);ax.set_xlim(-.35,.35)
    ax.set_xlabel('Topocentric air offset (Å)',fontsize=8);ax.set_ylabel('Excess / side continuum',fontsize=8)
    ax.tick_params(labelsize=8)
    if legend:ax.legend(fontsize=6)

ids=list(dict.fromkeys(r['dp_id'] for r in native))
for start in range(0,len(ids),3):
    fig,axs=plt.subplots(3,3,figsize=(12,9));fig.subplots_adjust(left=.07,right=.98,bottom=.075,top=.90,wspace=.3,hspace=.50)
    for j,dp in enumerate(ids[start:start+3]):
        for i,label in enumerate(lines):
            r=next(r for r in native if r['dp_id']==dp and r['fiber']=='A' and r['line']==label)
            draw(axs[j,i],r);axs[j,i].set_title(r['target']+' '+r['date_obs'][:10]+' · '+label+'\nNative A order '+str(r['order']),fontsize=9)
    fig.suptitle('O I follow-up · native fiber A · all selected exposures\nSigned fits and fixed windows; no calibrated significance or automatic origin decisions.',fontsize=12)
    fig.savefig(FIG/f'NATIVE_{start//3+1:02d}.png',dpi=110);plt.close(fig)

for target in ['HD120411','HD119130']:
    group=[r for r in epoch if r['target']==target];ids=sorted(set(r['dp_id'] for r in group),key=lambda dp:next(r['date_obs'] for r in group if r['dp_id']==dp))
    fig,axs=plt.subplots(len(ids),3,figsize=(12,max(7,len(ids)*2.2)));fig.subplots_adjust(left=.07,right=.98,bottom=.035,top=1-.85/max(7,len(ids)*2.2),wspace=.3,hspace=.72)
    for j,dp in enumerate(ids):
        for i,label in enumerate(lines):
            r=next(r for r in group if r['dp_id']==dp and r['line']==label);draw(axs[j,i],r,False)
            axs[j,i].set_title(r['date_obs'][:10]+' · '+label+f' · BERV {r["berv_km_s"]:+.2f}',fontsize=8)
    fig.suptitle(target+' · every available main-sample epoch, including no saved hit\nMerged A spectrum transformed approximately to topocentric air; independent panel y scales.',fontsize=12)
    fig.savefig(FIG/(target+'_ALL_EPOCHS.png'),dpi=110);plt.close(fig)

highlights=[('V2-0165','ADP.2023-05-15T01:01:10.510'),('V2-0205','ADP.2022-05-25T01:02:16.015')]
fig,axs=plt.subplots(2,3,figsize=(12,7));fig.subplots_adjust(left=.07,right=.98,bottom=.09,top=.87,wspace=.3,hspace=.55)
for j,(hid,dp) in enumerate(highlights):
    for i,label in enumerate(lines):
        r=next(r for r in native if r['dp_id']==dp and r['fiber']=='A' and r['line']==label)
        draw(axs[j,i],r);axs[j,i].set_title(hid+' '+r['target']+' · '+label+f'\nBest offset {r["best_offset_angstrom"]:+.4f} Å',fontsize=9)
fig.suptitle('Same-exposure three-line check · native A\nV2-0165 retains particle-contamination concern; V2-0205 retains unresolved origin.',fontsize=12)
fig.savefig(FIG/'HIGHLIGHT_THREE_LINES.png',dpi=130);plt.close(fig)
print('Figures completed')
