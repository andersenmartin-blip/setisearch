"""Display continuous metrics; no thresholds or categorical repeat assignments."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
events=json.loads((OUT/'EVENT_RESULTS.json').read_text())
rows=list(csv.DictReader((OUT/'ALL_EPOCH_MEASUREMENTS.csv').open()))
(OUT/'figures').mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(8.5,7),layout='constrained')
x=[e['frames']['barycentric']['other_correlation_to_discovery']['median'] for e in events]
y=[e['frames']['topocentric']['other_correlation_to_discovery']['median'] for e in events]
c=[e['berv_span_resolution_elements'] for e in events]
s=ax.scatter(x,y,c=c,cmap='viridis',s=25,alpha=.75,edgecolor='none')
ax.plot([-1,1],[-1,1],color='.6',ls='--',lw=1)
ax.set(xlim=(-1.03,1.03),ylim=(-1.03,1.03),xlabel='Barycentric: median correlation with other exposures',ylabel='Topocentric: median correlation with other exposures',title='336 event records: continuous cross-epoch profile comparison')
ax.grid(alpha=.15)
fig.colorbar(s,ax=ax,label='Full target BERV span / (c / 115000)')
fig.text(.5,-.015,'Source exposure excluded. Core ±0.25 Å, no shift optimization. Similarity is not an origin identification.',ha='center',fontsize=9)
fig.savefig(OUT/'figures/CONTINUOUS_FRAME_COMPARISON.png',dpi=170,bbox_inches='tight');plt.close(fig)

chosen=[events[0],events[(len(events)-1)//2],events[-1]]
fig,axes=plt.subplots(3,2,figsize=(13,11),layout='constrained')
for i,event in enumerate(chosen):
    for j,frame in enumerate(['barycentric','topocentric']):
        ax=axes[i,j];selected=[r for r in rows if r['candidate_id']==event['candidate_id'] and r['frame']==frame]
        for r in selected:
            a=np.load(OUT/r['profile_path']);source=r['is_discovery_exposure']=='True'
            ax.plot(a['offset_air_angstrom'],a['residual'],color='black' if source else None,lw=1.8 if source else 1,alpha=1 if source else .6,label=r['date_obs'][:10]+(' source' if source else ''))
        ax.axvline(0,color='.5',lw=.7);ax.axhline(0,color='.5',lw=.7)
        ax.set(xlim=(-.25,.25),xlabel='Offset from fixed frame center (air Å)',ylabel='Locally normalized flux minus background',title=event['candidate_id']+' · '+event['target']+' · '+frame)
        ax.grid(alpha=.15);ax.legend(fontsize=7,ncol=2,loc='best')
fig.suptitle('First, middle and last catalogue records (fixed index selection, no ranking)',fontsize=15)
fig.savefig(OUT/'figures/FIXED_INDEX_PROFILE_EXAMPLES.png',dpi=170,bbox_inches='tight');plt.close(fig)
print('Saved two figures')
