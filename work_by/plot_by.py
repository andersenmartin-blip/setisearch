"""Scientific figures from closed BY outputs; no new selection or scoring."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parent
TMP=Path('/dev/shm/seti_by_20261031')
s=json.loads((ROOT/'SUMMARY_BY.json').read_text())
bins=json.loads((TMP/'rfi/outputs/PER_BIN_RFI_BY.json').read_text())['bins']
out=ROOT/'figures';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
fig=plt.figure(figsize=(12,8.4),layout='constrained')
gs=fig.add_gridspec(2,2,height_ratios=[1,1])
ax=fig.add_subplot(gs[0,:])
colors={'turboSETI':'#1665a4','energy_detection':'#df8424'}
for method,label in [('turboSETI','turboSETI · 171 rækker'),('energy_detection','Energy detection · 169 rækker')]:
    ax.plot([b['lower_edge_mhz']+.5 for b in bins],[100*b[method]['nonzero_fraction'] for b in bins],color=colors[method],lw=1,label=label)
ax.axvspan(2300,2361,color='#ccd0d5',alpha=.5,label='Kildens notch-markerede bins')
ax.set(xlabel='Frekvens (MHz; bins på 1 MHz)',ylabel='Rækker med ≥1 hit (%)',xlim=(1800,2801),ylim=(0,105),title='Nye hit-tabeller: alle publicerede observationsrækker fra 2019–2020')
ax.grid(axis='y',alpha=.2);ax.legend(loc='upper right',fontsize=8,ncols=3)
ax=fig.add_subplot(gs[1,0]);x=np.arange(4)
for offset,(method,label) in zip([-.19,.19],[('turboSETI','turboSETI /171'),('energy_detection','Energy detection /169')]):
    values=[b[method]['nonzero_rows'] for b in s['rfi']['fixed_neighborhood']]
    bars=ax.bar(x+offset,values,.36,color=colors[method],label=label)
    ax.bar_label(bars,padding=3,fontsize=9)
ax.set_xticks(x,['2298–99','2299–2300','2300–01*','2301–02*'])
ax.set(xlabel='Frekvensinterval (MHz)',ylabel='Rækker med ≥1 hit',ylim=(0,30),title='På forhånd valgt område omkring tidligere søgning')
ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
ax.text(.01,-.22,'* Notch-markeret. Her vises alle rækker i hver tabel.\nForskellige tærskler; lave hitantal er ikke et følsomhedsmål.',transform=ax.transAxes,fontsize=8,va='top')
ax=fig.add_subplot(gs[1,1]);groups=s['injection']['groups']
on=[g for g in groups if g['presence']=='ON_ONLY'];all5=[g for g in groups if g['presence']=='ALL_FIVE']
amp=[g['amplitude'] for g in on]
ax.plot(amp,[g['source_recovered'] for g in on],'o--',color='#6b8da8',label='Fundet i første ON')
ax.plot(amp,[g['three_ON_recovered'] for g in on],'o-',color='#12517b',label='Fundet i alle tre ON')
ax.plot(amp,[g['available_OFF_rejected'] for g in all5],'x:',color='#348156',ms=9,label='Alle fem: afvist via OFF')
ax.set_xscale('log',base=2);ax.set_xticks(amp,[str(int(a)) for a in amp])
ax.set(xlabel='Tilført normaliseret effekt pr. integration (ikke Jy)',ylabel='Testgeometrier ud af 24',ylim=(-1,26),title='Betinget genfinding: 3 lokale driftrater, q254')
ax.set_yticks([0,6,12,18,24]);ax.grid(alpha=.2);ax.legend(fontsize=8,loc='upper left')
ax.text(.01,-.22,'24 kontroller uden indsprøjtning gav ingen genfinding.\nTidligere brugt baggrund; ingen fuld ON/OFF-kvalifikation.',transform=ax.transAxes,fontsize=8,va='top')
fig.suptitle('BY — RFI-kontekst og genfinding af testsignaler',fontsize=16)
fig.savefig(out/'BY_RESULTS_2026-10-31.png',dpi=150)
fig.savefig(out/'BY_RESULTS_2026-10-31.svg')
plt.close(fig)
print(out/'BY_RESULTS_2026-10-31.png')
