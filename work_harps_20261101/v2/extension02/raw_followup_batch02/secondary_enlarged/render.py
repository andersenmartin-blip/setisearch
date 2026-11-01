import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
p=Path(__file__).resolve().parent.parent
ids={f'V2E2-{i:04d}' for i in [12,13,14,15,17,31,36,37,38,40,47,48,49,50,55,57,58,65,66,67,68,69,71,72,73,78,79,80,82,84]}
orders=[r for r in json.loads((p/'NATIVE_MAPPING.json').read_text())['orders'] if r['review_id'] in ids and r['status']=='EXTRACTED']
records=[]
for start in range(0,len(orders),6):
 group=orders[start:start+6]; fig,axes=plt.subplots(len(group),3,figsize=(14,3*len(group)),squeeze=False)
 for i,r in enumerate(group):
  z=np.load(p/r['cutout']);raw=z['raw_cutout'][:,8:25];exc=z['raw_excess'][:,8:25];bg=z['raw_background'][8:25];x=np.arange(-8,9)
  lo=float(np.min(raw));hi=float(np.max(raw));em=float(np.max(np.maximum(exc,0)))
  axes[i,0].imshow(raw,origin='lower',extent=[-8.5,8.5,-15.5,15.5],aspect='auto',vmin=lo,vmax=hi,cmap='inferno')
  axes[i,1].imshow(np.maximum(exc,0),origin='lower',extent=[-8.5,8.5,-15.5,15.5],aspect='auto',vmin=0,vmax=max(em,1),cmap='inferno')
  for a in axes[i,:2]:a.axvline(r['raw_column']-round(r['raw_column']),color='cyan',lw=.5);a.axhline(0,color='cyan',lw=.5);a.set_xlabel('Column offset');a.set_ylabel('Dispersion row offset')
  axes[i,0].set_title(r['review_id']+' o'+str(r['order'])+f' raw [{lo:.0f},{hi:.0f}]')
  axes[i,1].set_title(f'Positive excess; scale 0–{em:.1f}')
  central=np.mean(z['raw_cutout'][13:18,8:25],axis=0)
  axes[i,2].plot(x,central,label='mean rows -2..+2');axes[i,2].plot(x,bg,label='side median');axes[i,2].plot(x,central-bg,label='difference');axes[i,2].axvline(r['raw_column']-round(r['raw_column']),color='k',lw=.5);axes[i,2].legend(fontsize=7);axes[i,2].set_xlabel('Column offset');axes[i,2].set_ylabel('Raw counts');axes[i,2].set_title('Spatial context; descriptive only')
  records.append(dict(review_id=r['review_id'],order=r['order'],figure=f'secondary_enlarged/CENTRAL_{start//6+1:02d}.png',raw_range=[lo,hi],positive_excess_max=em))
 fig.suptitle('Secondary reviewer enlarged center ±8 columns; fixed data/coordinates; per-order scales',y=.999);fig.tight_layout(rect=[0,0,1,.98]);fig.savefig(p/f'secondary_enlarged/CENTRAL_{start//6+1:02d}.png',dpi=110);plt.close(fig)
(p/'secondary_enlarged/INDEX.json').write_text(json.dumps(records,indent=2)+'\n')
print(len(orders),'orders',len(range(0,len(orders),6)),'pages')
