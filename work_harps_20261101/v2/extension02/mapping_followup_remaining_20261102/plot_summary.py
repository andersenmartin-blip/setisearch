from pathlib import Path
import csv,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent
rows=list(csv.DictReader((OUT/'ALL_1512_ORDER_DIAGNOSTICS.csv').open()));failed=list(csv.DictReader((OUT/'FAILED_28_ORDER_DIAGNOSTICS.csv').open()))
fig,axes=plt.subplots(2,1,figsize=(10,8),layout='constrained')
for key,color,label in [('original_pearson_median','#1d4b8c','Original Pearson'),('winsorized_pearson_median','#bc601e','Fixed winsorized diagnostic')]:
 values=np.array([[float(r[key]) for r in rows if int(r['order'])==o] for o in range(72)])
 axes[0].plot(range(72),np.median(values,axis=1),color=color,lw=2,label=label)
 if key=='original_pearson_median':axes[0].fill_between(range(72),np.percentile(values,10,axis=1),np.percentile(values,90,axis=1),color=color,alpha=.12,label='Original Pearson: 10–90% range')
axes[0].set(title='All 72 orders in each of 21 M-selected exposures',xlabel='Native order index (0-based)',ylabel='Median correlation across exposures',ylim=(0,1.02),xlim=(-.5,71.5))
axes[0].legend(loc='lower left',fontsize=9)
for band,color,label in [(False,'#1d4b8c','Failed references: orders 1–52'),(True,'#bc601e','Failed references: orders 66–70')]:
 subset=[r for r in failed if (int(r['order'])>=66)==band]
 axes[1].scatter([float(r['original_pearson_median']) for r in subset],[float(r['winsorized_pearson_median']) for r in subset],color=color,label=label,s=45,alpha=.85,edgecolor='white',lw=.4)
axes[1].plot([.25,1],[.25,1],color='.5',ls='--',lw=1,label='Unchanged correlation')
axes[1].set(title='The 28 previously failed exposure/order references',xlabel='Original Pearson median',ylabel='Winsorized Pearson median (diagnostic)',xlim=(.25,.85),ylim=(.2,1.02))
axes[1].legend(loc='lower right',fontsize=9)
for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.15)
fig.suptitle('HARPS mapping controls: improvement depends on spectral order',fontsize=14,fontweight='bold')
fig.text(.5,-.025,'Descriptive posthoc sample · Fixed coordinates and original gates · All 35 mapping-limited records remain M',ha='center',fontsize=9)
fig.savefig(OUT/'MAPPING_DIAGNOSTIC_SUMMARY.png',dpi=170,bbox_inches='tight');fig.savefig(OUT/'MAPPING_DIAGNOSTIC_SUMMARY.pdf',bbox_inches='tight')
