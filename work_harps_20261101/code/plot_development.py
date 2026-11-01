"""Render a preserved first-stage result without changing the detector."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser()
parser.add_argument('directory',type=Path)
args=parser.parse_args()
p=args.directory
a=np.load(p/'search_arrays.npz')
r=json.loads((p/'result.json').read_text())
events=sorted(r['all_threshold_runs'],key=lambda e:e['peak_local_contrast'],reverse=True)[:6]
fig=plt.figure(figsize=(12,8.5),layout='constrained')
gs=fig.add_gridspec(3,3,height_ratios=[1.4,1,1])
ax=fig.add_subplot(gs[0,:])
sel=(a['wave']>=3800)&(a['wave']<=6900)
ax.plot(a['wave'][sel][::10]/10,a['flux'][sel][::10],color='#225f84',lw=.4)
ax.set(xlabel='Barycentrisk luftbølgelængde (nm)',ylabel='Flux (ukalibreret ADU)',
       title='HARPS udviklingsspektrum · '+str(r['input']['OBJECT'])+' · '+str(r['input']['DATE-OBS']))
ax.text(.01,.03,f"{r['searched_samples']:,} søgte punkter · {r['preliminary_hit_count']} foreløbige hits · {r['short_run_count']} kortere udsving",transform=ax.transAxes,fontsize=10)
for slot,event in enumerate(events):
    ax=fig.add_subplot(gs[1+slot//3,slot%3])
    k=event['peak_index']; s=slice(max(0,k-30),min(len(a['wave']),k+31)); w=a['wave'][s]/10
    ax.plot(w,a['flux'][s],'-o',ms=2,lw=.7,label='Målt flux')
    ax.plot(w,a['continuum'][s],lw=1,label='Lokal median')
    ax.plot(w,a['continuum'][s]+3.5*a['local_std'][s],lw=.8,ls='--',label='Median + 3,5 × lokal std')
    ax.set(title=f"{event['wave_peak_angstrom']/10:.3f} nm · {event['run_pixels']} punkt",xlabel='nm',ylabel='ADU')
    ax.ticklabel_format(useOffset=False,axis='x'); ax.tick_params(labelsize=8)
    if slot==0: ax.legend(fontsize=6)
fig.suptitle('Udviklingsdata alene — lokale udsving er ikke påviste lasersignaler',fontsize=13)
fig.savefig(p/'development_spectrum.png',dpi=160)
