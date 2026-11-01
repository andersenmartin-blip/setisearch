from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
mapping=json.loads((P/'NATIVE_MAPPING.json').read_text())['orders']
for ident in [165,205]:
 m=next(x for x in mapping if x['review_id']==f'V2-{ident:04d}')
 d=np.load(P/m['cutout']);fig,ax=plt.subplots(1,3,figsize=(12,4),layout='constrained')
 for a,key in zip(ax[:2],['raw_cutout','raw_excess']):
  a.imshow(d[key][:,6:19],origin='lower',aspect='auto',cmap='magma',extent=[-6.5,6.5,-10.5,10.5]);a.axhline(0,c='cyan',lw=.7);a.axvline(m['raw_column']-round(m['raw_column']),c='cyan',lw=.7);a.set_title(key)
 x=np.arange(-6,7);bg=d['raw_background'][6:19];bg=bg-np.median(bg[[0,1,11,12]]);ex=d['raw_excess'][8:13,6:19].sum(axis=0)
 ax[2].plot(x,bg/bg.max(),'.-',label='continuum');ax[2].plot(x,ex/ex.max(),'.-',label='central5rows excess');ax[2].legend(loc='lower center');fig.suptitle(f'V2-{ident:04d} order{m["order"]}: additional central-trace detail (descriptive)');fig.savefig(P/'agent_local_097_220'/f'FOCUS_{ident:04d}.png',dpi=130);plt.close(fig)
