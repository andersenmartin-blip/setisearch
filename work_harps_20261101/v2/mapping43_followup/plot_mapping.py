"""Every43 event and all covering orders in saved order, no ranking."""
from pathlib import Path
import json,csv,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent;(OUT/'figures').mkdir(exist_ok=True)
data=json.loads((OUT/'MAPPING_AUDIT.json').read_text());hits=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()));index=[]
for start in range(0,len(hits),4):
    fig,axs=plt.subplots(4,3,figsize=(14,12));fig.subplots_adjust(left=.055,right=.985,bottom=.055,top=.91,wspace=.25,hspace=.48)
    for j,h in enumerate(hits[start:start+4]):
        ev=next(r for r in data['events'] if r['review_id']==h['review_id']);ms=[r for r in data['orders'] if r['review_id']==h['review_id'] and r['status']=='EXTRACTED']
        images=[[],[]];centers=[[],[]];offset=[0,0]
        for m in ms:
            d=np.load(OUT/m['cutout']);scale=m['native_side_median'];axs[j,0].plot(d['native_wave']-m['topocentric_air_angstrom'],d['native_flux']/scale,'.-',lw=.8,ms=3,label='o'+str(m['order']))
            arrays=[np.maximum(d['raw_cutout'][:,10:23],0),np.maximum(d['raw_excess'],0)]
            for q,v in enumerate(arrays):
                norm=max(v.max(),1) if q==0 else max(v[:,11:22].max(),1)
                images[q].extend([v/norm,np.full((31,3),np.nan)])
                centers[q].append(offset[q]+(6 if q==0 else 16)+m['raw_column']-round(m['raw_column']));offset[q]+=v.shape[1]+3
        axs[j,0].axvline(0,color='red',ls=':',lw=.7);axs[j,0].axhline(1,color='grey',lw=.5);axs[j,0].set_xlim(-.38,.38);axs[j,0].legend(fontsize=8)
        axs[j,0].set_title(h['review_id']+' '+h['canonical_target']+'\n'+('REFERENCE SUPPORTED' if ev['mapping_supported'] else 'MAPPING STILL LIMITED'),fontsize=10)
        axs[j,0].set_xlabel('Topocentric air offset (Å)',fontsize=9);axs[j,0].set_ylabel('Native flux / side median',fontsize=9)
        for q in range(2):
            ax=axs[j,q+1]
            if images[q]:ax.imshow(np.hstack(images[q][:-1]),origin='lower',aspect='auto',cmap='magma',vmin=0,vmax=1)
            for c in centers[q]:ax.axvline(c,color='cyan',lw=.6)
            ax.axhline(15,color='cyan',lw=.6);ax.set_yticks([0,15,30],[-15,0,15]);ax.set_xticks([]);ax.set_ylabel('Raw dispersion offset',fontsize=8)
            ax.set_title(('Central raw counts' if q==0 else 'Wide positive excess · central scale')+' · '+','.join('o'+str(m['order']) for m in ms),fontsize=9)
        if ev['edge_truncated_orders']:axs[j,0].text(.02,.03,'Truncated: '+str(ev['edge_truncated_orders']),transform=axs[j,0].transAxes,fontsize=7)
        index.append(dict(review_id=h['review_id'],page=start//4+1,row=j+1,orders=[m['order'] for m in ms],mapping_supported=ev['mapping_supported']))
    for j in range(len(hits[start:start+4]),4):
        for ax in axs[j]:ax.set_visible(False)
    fig.suptitle('43 mapping follow-ups · native and raw evidence · page '+str(start//4+1)+'/'+str(math.ceil(len(hits)/4))+'\nCoordinates unchanged. Reference support is geometry evidence only; origin judgments remain provisional.',fontsize=13)
    fig.savefig(OUT/'figures'/f'REVIEW_{start//4+1:02d}.png',dpi=110);plt.close(fig)
(OUT/'FIGURE_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
for start in range(0,len(data['reference_audit']),12):
    subset=data['reference_audit'][start:start+12];fig,axs=plt.subplots(4,3,figsize=(13,12));fig.subplots_adjust(left=.06,right=.98,bottom=.05,top=.93,wspace=.3,hspace=.5)
    for j,r in enumerate(subset):
        ax=axs.flat[j]
        for w in r['windows']:
            if w['profile'] is not None:
                p=np.array(w['profile']);ax.plot(np.arange(-8,9),p/max(p.max(),1),'.-',ms=2,lw=.8,label=str(w['pixel_interval_half_open'][0]))
        ax.axvline(0,color='black',ls=':',lw=.8);ax.set_xlim(-8,8);ax.set_title(r['dp_id'][4:14]+' o'+str(r['order'])+' · '+('supported' if r['mapping_supported'] else 'limited')+'\nmedian r '+str(round(r['median_correlation'],3) if r['median_correlation'] is not None else 'none'),fontsize=9);ax.legend(fontsize=6)
    for j in range(len(subset),12):axs.flat[j].set_visible(False)
    fig.suptitle('Fixed candidate-excluded reference profiles · page '+str(start//12+1),fontsize=13)
    fig.savefig(OUT/'figures'/f'REFERENCES_{start//12+1:02d}.png',dpi=100);plt.close(fig)
print('wrote',len(index),'event displays and',len(data['reference_audit']),'order reference profiles')
