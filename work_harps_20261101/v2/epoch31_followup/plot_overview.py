"""Compact visual audit of every group's complete two-frame epoch profiles."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
groups=json.loads((OUT/'GROUP_RESULTS.json').read_text());rows=list(csv.DictReader((OUT/'ALL_EPOCH_MEASUREMENTS.csv').open()))
for start in range(0,len(groups),4):
    fig,axs=plt.subplots(4,2,figsize=(12,12));fig.subplots_adjust(left=.07,right=.985,bottom=.05,top=.90,wspace=.23,hspace=.55)
    for j,g in enumerate(groups[start:start+4]):
        for fi,frame in enumerate(['barycentric','topocentric']):
            selected=[r for r in rows if r['group_id']==g['group_id'] and r['frame']==frame]
            for r,color in zip(selected,plt.cm.viridis(np.linspace(.05,.95,len(selected)))):
                d=np.load(OUT/r['profile_path']);axs[j,fi].plot(d['offset_air_angstrom'],d['normalized_flux'],lw=.7,c=color,alpha=.85)
            med=g['frames'][frame]['pairwise_correlation_summary']['median']
            axs[j,fi].set_title(f"{g['group_id']} {g['target']} {g['center_bary_air_angstrom']:.4f}Å · {frame}\n{g['epoch_count']} epochs; median pairwise core r={med:.3f}",fontsize=9)
            axs[j,fi].axvline(0,c='red',ls=':',lw=.6);axs[j,fi].set_xlim(-.45,.45);axs[j,fi].set_xlabel('Air wavelength offset (Å)',fontsize=8);axs[j,fi].set_ylabel('Relative flux',fontsize=8);axs[j,fi].tick_params(labelsize=8)
    for unused in range(len(groups[start:start+4]),4):
        for ax in axs[unused]: ax.set_visible(False)
    fig.suptitle(f'All-epoch profile overview {start//4+1}/{(len(groups)+3)//4} · all available selected epochs, including nonhits\nNormalization uses local ±2Å median; no formal ERR arrays or significance claims.',fontsize=11)
    fig.savefig(OUT/'figures'/f'OVERVIEW_{start//4+1:02d}.png',dpi=110);plt.close(fig)
print(str((len(groups)+3)//4)+' complete overview pages')
