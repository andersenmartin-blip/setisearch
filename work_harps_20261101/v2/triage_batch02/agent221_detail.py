"""Central trace and original-count context for all OI flags and mapping warnings."""
from pathlib import Path
import csv,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'NATIVE_MAPPING.json').read_text())
hits=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()))
selected=[h for h in hits if int(h['review_id'][-4:]) in [241,247,253,267,285,286,287,304,310]]
for start in range(0,len(selected),4):
    fig,axs=plt.subplots(4,3,figsize=(12,10),layout='constrained')
    for j,h in enumerate(selected[start:start+4]):
        ms=[m for m in data['orders'] if m['review_id']==h['review_id'] and m['status']=='EXTRACTED']
        for t,key in enumerate(['raw_cutout','raw_excess']):
            images=[];centers=[];offset=0
            for m in ms:
                d=np.load(OUT/m['cutout']);v=np.maximum(d[key][:,6:19],0);v/=max(v.max(),1)
                centers.append(offset+6+m['raw_column']-round(m['raw_column']));offset+=16
                images.extend([v,np.full((21,3),np.nan)])
            if images:
                axs[j,t].imshow(np.hstack(images[:-1]),origin='lower',aspect='auto',cmap='magma',vmin=0,vmax=1)
                for c in centers:axs[j,t].axvline(c,color='cyan',lw=.6)
                axs[j,t].axhline(10,color='cyan',lw=.6)
            axs[j,t].set_title(h['review_id']+' '+('raw counts' if t==0 else 'positive excess'),fontsize=10)
            axs[j,t].set_yticks([0,10,20],[-10,0,10]);axs[j,t].set_xticks([])
        for m in ms:
            d=np.load(OUT/m['cutout']);v=d['raw_background'][6:19];v=v/max(v.max(),1)
            x=np.arange(-6,7)-(m['raw_column']-round(m['raw_column']))
            axs[j,2].plot(x,v,'.-',label='order '+str(m['order']))
        axs[j,2].axvline(0,color='cyan',lw=.6);axs[j,2].legend(fontsize=8)
        axs[j,2].set_title('Outer-row median · normalized',fontsize=10)
        axs[j,2].set_xlabel('Raw column minus predicted center')
    for j in range(len(selected[start:start+4]),4):
        for ax in axs[j]:ax.set_visible(False)
    fig.suptitle('Additional central trace detail · selected ambiguous or obscured panels\nEvery covering extracted order shown; panels independently scaled; origin remains provisional.',fontsize=12)
    fig.savefig(OUT/'figures'/f'AGENT221_DETAIL_{start//4+1:02d}.png',dpi=110);plt.close(fig)
(OUT/'AGENT221_DETAIL_INDEX.json').write_text(json.dumps([dict(review_id=h['review_id'],page=i//4+1,row=i%4+1) for i,h in enumerate(selected)],indent=2)+'\n')
print('focused events',len(selected))
