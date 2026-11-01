"""Post-hoc display and local-trace audit; no search thresholds or vetoes."""
from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
mapping=json.loads((OUT/'NATIVE_MAPPING.json').read_text())
notes=json.loads((OUT/'VISUAL_NOTES_DRAFT.json').read_text())
selected=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()))
quality=[]
for r in mapping['orders']:
    if r['status']!='EXTRACTED':continue
    d=np.load(OUT/r['cutout']);bg=d['raw_background'];mid=12+r['raw_column']-round(r['raw_column'])
    maximum=6+int(np.argmax(bg[6:19]))
    quality.append(dict(review_id=r['review_id'],order=r['order'],continuum_peak_minus_predicted_column=float(maximum-mid),
        visual_local_mapping_warning=r['review_id'] in ['V2-0046','V2-0047'],global_reference_mapping_verified=r['mapping_verified']))
(OUT/'LOCAL_TRACE_AUDIT.json').write_text(json.dumps(dict(method='Descriptive maximum of outer-row median continuum in columns6:18; no universal mapping threshold inferred. Events46/47 flagged by visual and numerical review.',orders=quality),indent=2)+'\n')
oi=[r for r in selected if notes[str(int(r['review_id'][-4:]))][0]=='O_PENDING']
for start in range(0,len(oi),5):
    fig,axes=plt.subplots(5,2,figsize=(9,10),layout='constrained')
    for j,h in enumerate(oi[start:start+5]):
        m=next(r for r in mapping['orders'] if r['review_id']==h['review_id'] and r['status']=='EXTRACTED')
        d=np.load(OUT/m['cutout']);cut=d['raw_cutout'][:,6:19];excess=d['raw_excess'][:,6:19]
        mid=m['raw_column']-round(m['raw_column'])
        for ax,values,label in [(axes[j,0],cut,'raw counts'),(axes[j,1],excess,'positive excess')]:
            ax.imshow(np.maximum(values,0),origin='lower',aspect='auto',cmap='magma',extent=[-6.5,6.5,-10.5,10.5])
            ax.axvline(mid,color='cyan',lw=.6);ax.axhline(0,color='cyan',lw=.6)
            ax.set_title(h['review_id']+' · '+label+' · O I offset '+f'{float(h["offset_angstrom"]):+.4f} Å',fontsize=9)
        axes[j,0].set_ylabel('Dispersion pixel offset')
    fig.suptitle('O I-flagged events with usable mapping · central trace only\nNo off-fibre sky measurement or atmospheric confirmation',fontsize=12)
    fig.savefig(OUT/'figures'/f'OI_FOCUSED_{start//5+1:02d}.png',dpi=110);plt.close(fig)
print('local audit rows',len(quality),'focused O I displays',len(oi))
