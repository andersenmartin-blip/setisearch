from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
D=P/'agent_local_097_220';D.mkdir(exist_ok=True)
m=json.loads((P/'NATIVE_MAPPING.json').read_text());la=json.loads((P/'LOCAL_TRACE_AUDIT.json').read_text())
lookup={(r['review_id'],r['order']):r for r in la['orders']}
rows=[r for r in m['orders'] if 97<=int(r['review_id'][3:])<=220 and r['status']=='EXTRACTED']
index=[]
for start in range(0,len(rows),12):
 fig,axs=plt.subplots(3,4,figsize=(14,10),layout='constrained')
 for ax,r in zip(axs.flat,rows[start:start+12]):
  d=np.load(P/r['cutout']);a=lookup[(r['review_id'],r['order'])]
  cut=d['raw_cutout'][:,6:19];bg=d['raw_background'][6:19]
  # Clip colour display to continuum scale so an energetic event cannot hide local trace.
  low=np.percentile(cut,5);high=max(np.max(bg),low+1)
  ax.imshow(cut,origin='lower',aspect='auto',cmap='magma',extent=[-6.5,6.5,-10.5,10.5],vmin=low,vmax=high)
  pred=r['raw_column']-round(r['raw_column']);ax.axvline(pred,c='cyan',lw=.6);ax.axhline(0,c='cyan',lw=.6)
  offsets=[w.get('peak_offset') for w in a['windows']]
  ax.set_title(r['review_id']+f" order {r['order']} · map {r['mapping_verified']}\nlocal offsets "+', '.join('NA' if x is None else f'{x:+.2f}' for x in offsets),fontsize=9)
  ax.set_xticks([-6,-3,0,3,6]);ax.set_yticks([-10,0,10]);ax.tick_params(labelsize=7)
  index.append(dict(review_id=r['review_id'],order=r['order'],page=start//12+1,position=(len(index)%12)+1))
 for ax in list(axs.flat)[len(rows[start:start+12]):]:ax.set_visible(False)
 fig.suptitle('Assigned97–220: local raw continuum check · central13columns\nColour clipped at outer-row continuum maximum; quantitative mapping flags remain fixed.',fontsize=12)
 fig.savefig(D/f'LOCAL_{start//12+1:02d}.png',dpi=110);plt.close(fig)
(D/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
print('rendered',len(rows),'orders',len(list(D.glob('LOCAL_*.png'))),'pages')
