"""Plot already sealed aggregate counts; no new scoring."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
s=json.loads((HERE/'FINAL_SUMMARY_BZ.json').read_text())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'SETI_BZ_20261031'})
fig,(ax,control)=plt.subplots(1,2,figsize=(11.5,4.7),gridspec_kw={'width_ratios':[1.45,1]})
colors={4:'#7594b2',8:'#006f87',16:'#d58f2e'}
for amp in [4,8,16]:
    vals=[next(g['three_ON_recovered'] for g in arm['groups'] if g['presence']=='ON_ONLY' and g['amplitude']==amp) for arm in s['arms']]
    ax.plot(range(4),vals,'o-',label=f'A = {amp}',color=colors[amp],linewidth=2.5)
    for x,y in enumerate(vals):ax.annotate(str(y),(x,y),xytext=(0,9),textcoords='offset points',ha='center',color=colors[amp])
ax.set(xticks=range(4),xticklabels=['1×\n3 rater','2×\n5 rater','4×\n9 rater','8×\n17 rater'],ylim=(-.5,27),yticks=range(0,25,4),ylabel='Genfundet i tre ON-scanninger / 24',xlabel='Gitterfinhed og antal lokale driftrater',title='Flere rater genfinder nogle tabte signaler')
ax.grid(axis='y',alpha=.2);ax.legend(loc='upper left',bbox_to_anchor=(0,.85),ncol=3,frameon=False)
control.axis('off')
control.text(0,1,'Kontroller ved 8×',fontweight='bold',fontsize=14,va='top')
control.text(0,.83,'Nul-kontroller: 0/24 genfundet\n\nAlle fem scanninger med signal:\nA = 4:   4/4 genfundne afvist\nA = 8:   15/15 genfundne afvist\nA = 16: 24/24 genfundne afvist\n\nKildescanningens genfinding ændres ikke.\nA = 1 og 2: fortsat 0/24.',va='top',linespacing=1.5)
fig.suptitle('BZ · Betinget genfinding på bevaret observationsbaggrund',fontsize=15,fontweight='bold',x=.05,ha='left')
fig.text(.05,.025,'Samme 24 geometrier og fem eksponerede scanninger · faste tærskler · manglende OFF5 · ingen ny observationsdækning',fontsize=9,color='#555555')
fig.subplots_adjust(left=.07,right=.98,top=.80,bottom=.20,wspace=.30)
out=HERE/'figures';out.mkdir(exist_ok=True)
for ext in ['svg','png']:fig.savefig(out/f'BZ_RECOVERY_2026-10-31.{ext}',dpi=170,metadata={'Date':None} if ext=='svg' else {})
print('Saved BZ SVG and PNG from sealed aggregate counts.')
