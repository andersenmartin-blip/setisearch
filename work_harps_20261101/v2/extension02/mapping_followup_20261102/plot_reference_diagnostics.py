from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
OUT=Path(__file__).resolve().parent
summary=json.loads((OUT/'RAW_REFERENCE_SUMMARY.json').read_text())
rows=summary['order_summaries']
fig,axes=plt.subplots(2,1,figsize=(10,7.5),layout='constrained',gridspec_kw={'height_ratios':[1.2,1]})
colors={'original_pearson_median':'#1e4b8a','spearman_median':'#b86017','winsorized_pearson_median':'#2d7d60','subwindow_pearson_median':'#9153a0'}
labels={'original_pearson_median':'Original Pearson','spearman_median':'Spearman (diagnostic)','winsorized_pearson_median':'Winsorized Pearson (diagnostic)','subwindow_pearson_median':'64-pixel subwindows (diagnostic)'}
for key in colors:
 axes[0].plot([r['order'] for r in rows],[r[key] if r[key] is not None else np.nan for r in rows],label=labels[key],lw=1.6,color=colors[key])
axes[0].axhline(.8,color='.45',linestyle='--',lw=1,label='Original Pearson gate (>0.8)')
axes[0].set(xlabel='Native order index (0-based)',ylabel='Median correlation',xlim=(-.5,71.5),ylim=(0,1.02),title='All 72 orders in the same exposure; additional metrics do not replace the original gate')
axes[0].legend(fontsize=8,loc='lower left',ncol=2)
for order,color in [(0,'#858585'),(1,'#1e4b8a'),(3,'#2d7d60'),(70,'#b86017')]:
 r=rows[order];v=r['spatial_offset_medians'];axes[1].plot([x['offset_pixels'] for x in v],[x['pearson'] for x in v],label=f'Order {order}',marker='o',markersize=4,color=color)
axes[1].axvline(0,color='.45',ls='--',lw=1)
axes[1].set(xlabel='Fixed aperture displacement from original trace (pixels)',ylabel='Median Pearson correlation',ylim=(0,1.02),xticks=range(-4,5),title='Descriptive aperture probe: original coordinates remain unchanged')
axes[1].legend(fontsize=9,ncol=4,loc='lower left')
for ax in axes:ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.15)
fig.suptitle('HD118006: why mapping remains limited',fontsize=14,fontweight='bold')
fig.text(.5,-.025,'ADP.2023-02-24T01:01:17.491  |  One selected exposure  |  V2-0149 remains M; no origin assignment',ha='center',fontsize=9)
fig.savefig(OUT/'REFERENCE_DIAGNOSTICS.png',dpi=170,bbox_inches='tight')
fig.savefig(OUT/'REFERENCE_DIAGNOSTICS.pdf',bbox_inches='tight')
