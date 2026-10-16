#!/usr/bin/env python3
"""Render fixed own-ON descriptive comparisons; controls are points, no errorbars."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).resolve().parent
results=json.loads((root/'results/RESULTS.json').read_text())
rows=results['own_ON_summary']
fig, ax=plt.subplots(figsize=(10.5,6.5),layout='constrained')
fig.patch.set_facecolor('#fbfcff');ax.set_facecolor('#fbfcff')
y=np.arange(9)
for i,r in enumerate(rows):
    controls=r['neighboring_control_values']
    ax.scatter(controls,[i]*8,s=30,color='#aeb6c1',alpha=.8,zorder=2,
               label='Same neighboring-support statistic at 8 fixed frequency offsets' if i==0 else None)
ax.scatter([r['original_delta_score'] for r in rows],y+.11,s=66,color='#2264a6',marker='o',zorder=3,
           label='Originally selected central bins: original width1 sum / 2')
ax.scatter([r['masked_neighbor_unit_L2_score'] for r in rows],y-.11,s=72,color='#cf632f',marker='D',zorder=4,
           label='Predicted sweep support with selected central bins masked')
ax.axvline(0,color='#697586',lw=.8)
ax.set_yticks(y,[r['track'].replace('epoch','Scan ').replace('_on_rank',' · track ') +
                f"   |   sweep {r['sweep_native_channels']:.1f} channels" for r in rows])
ax.invert_yaxis();ax.spines[['top','right','left']].set_visible(False)
ax.grid(axis='x',alpha=.15)
ax.set_xlabel('Standardized weighted sum (descriptive; not a calibrated SNR or probability)')
ax.set_title('Do the selected peaks have neighboring power expected from an 18 s frequency sweep?',
             loc='left',fontsize=13,fontweight='bold',pad=18)
ax.legend(loc='upper left',bbox_to_anchor=(0,-.18),frameon=False,fontsize=9)
fig.suptitle('HIP98505 / HD189733 · 28 April 2017 · 9 previously selected ON tracks',
             x=.015,ha='left',fontsize=10,color='#566274')
fig.text(.02,-.09,'One exposed historical visit. Fixed original tracks and four rows; no refit. Gray points are dependent controls.\n'
         'Template: a continuous one-channel uniform line convolved with the exposure sweep. Shorter bursts or a different channel response can be narrower.',
         fontsize=9,color='#566274')
fig.savefig(root/'results/DRIFT_SMEARING.png',dpi=160,bbox_inches='tight')
fig.savefig(root/'results/DRIFT_SMEARING.svg',bbox_inches='tight')
