"""Plot original selected Voyager power stamps and independently checked paths."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent
d = json.loads((ROOT/'new_data/RESULT_CA_VOYAGER.json').read_text())
plt.rcParams.update({'font.size':11, 'svg.fonttype':'none'})
fig, axes = plt.subplots(1,5,figsize=(16,5.5),sharey=True)
for ax, r in zip(axes,d['records']):
    i=r['hit']; a=np.load(ROOT/f'new_data/stamp_{i}.npy',allow_pickle=False).astype(float)
    m=r['filterbank']; df=m['foff']*1e6; dt=m['tsamp']
    relative=a/np.median(a,axis=1)[:,None]
    extent=[-df/2,(a.shape[1]-.5)*df,-dt/2,(a.shape[0]-.5)*dt]
    # Each panel has its own color scale so the selected weaker structures remain visible.
    ax.imshow(np.log10(relative),origin='lower',aspect='auto',extent=extent,
              cmap='magma',vmin=0,vmax=float(np.percentile(np.log10(relative),99)))
    t=np.arange(a.shape[0])*dt
    best=r['best']; ref=r['reference_signal']
    ax.plot(np.array(best['selected_channels'])*df,t,c='#5DF4F0',lw=1.6,alpha=.9)
    ref_start=(ref['frequency']-m['fch1'])/m['foff']
    ax.plot((ref_start+ref['driftRate']*t/df)*df,t,c='white',ls='--',lw=1.2)
    flag='Inden for tolerance' if r['within_predeclared_reference_tolerances'] else 'AFVIGELSE BEVARET'
    ax.set_title(f"Udsnit {i+1}\n{best['drift_rate_Hz_s']:.6f} Hz/s",fontsize=12)
    ax.text(.5,-.2,flag,ha='center',transform=ax.transAxes,fontsize=9,
            color='#005e67' if r['within_predeclared_reference_tolerances'] else '#a33318')
    ax.set_xlabel('Frekvensoffset (Hz)')
    ax.set_xlim(-50,-260)
    ax.text(.5,-.28,f"Reference: {ref['frequency']:.6f} MHz",ha='center',transform=ax.transAxes,fontsize=8)
axes[0].set_ylabel('Tid fra første sample (sekunder)')
fig.suptitle('Voyager: fem målte signaludsnit fra samme historiske observation',fontsize=17,x=.07,ha='left')
fig.legend(handles=[Line2D([0],[0],color='#168e99',lw=2,label='Ny lineær sporsøgning'),
                    Line2D([0],[0],color='#555555',lw=1.5,ls='--',label='Publiceret reference')],
           loc='upper left',bbox_to_anchor=(.065,.92),ncol=2,frameon=False)
fig.text(.07,.018,'9.344 effektmålinger · 16 integrationer · relative farveskalaer pr. panel · udvalgte signaler, ingen blind ON/OFF-test',fontsize=10)
fig.subplots_adjust(left=.07,right=.99,top=.78,bottom=.29,wspace=.20)
out=ROOT/'figures';out.mkdir(exist_ok=True)
fig.savefig(out/'CA_VOYAGER_2026-11-01.png',dpi=160)
fig.savefig(out/'CA_VOYAGER_2026-11-01.svg')
plt.close(fig)
