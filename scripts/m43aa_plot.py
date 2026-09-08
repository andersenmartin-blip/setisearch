"""Illustrative full-neighborhood plots; all numeric probes are in the ledger."""
import gzip
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'results_m43aa_native_response'
COLORS=['#2468a2','#c26026','#27816b']

def record(i):
    return json.loads(gzip.decompress((OUT/'inputs'/f'case{i:03d}.json.gz').read_bytes()))

def style(ax):
    ax.grid(alpha=.18); ax.spines[['top','right']].set_visible(False)
    ax.axhline(5.5,color='#79838d',ls=':',lw=1,label='Existing 5.5 floor')
    ax.set_xlabel('Proxy channel offset from nominal test signal')
    ax.set_ylabel('Native filtered score')

def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'figure.dpi':130})
    fig,axes=plt.subplots(1,3,figsize=(15,5.6))
    for ax,i in zip(axes,[324,336,346]):
        r=record(i); case=r['associations']['neighbor9']['truth']; q=case['score_index']; t=case['local_template']; e=case['active_epochs'][0]
        a=next(a for a in r['responses'] if (a['template_index'],a['proxy_carrier_index'])==(t,q))
        w=next(w for w in a['widths'] if w['width']==17)
        x=np.arange(a['first_proxy_index'],a['last_proxy_index']+1)-q
        ax.plot(x,w['on']['values'][e],color=COLORS[0],label=f'ON, epoch {e+1}')
        ax.plot(x,w['off']['values'][e],color=COLORS[1],label=f'OFF, epoch {e+1}')
        ax.axvline(0,color='#40494f',alpha=.5,lw=.8)
        style(ax); ax.set_title(f'Case {i} | width 17'); ax.legend(fontsize=8,loc='upper left')
    fig.suptitle('Lost test signals: nearby OFF response can exceed the floor',fontsize=16,y=.97)
    fig.subplots_adjust(left=.055,right=.99,bottom=.20,top=.78,wspace=.24)
    fig.text(.5,.015,'One illustrated active epoch per case. All 321 response samples are shown. Selected retrospective tests on one observing sequence.',ha='center',fontsize=10,color='#48545f')
    fig.savefig(OUT/'off_loss_responses.png',dpi=160); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(15,5.6))
    for ax,i in zip(axes,[6,16,96]):
        r=record(i); byid={m['record_id']:m for m in r['reference_audit']['members']}
        kept=[byid[d['record_id']] for d in r['policy_decisions']['combined'] if d['passes_evaluated_physical_vetoes'] and byid[d['record_id']]['meets_diagnostic_rank_cut']]
        # Stable lexicographic representative, not the most visually separated one.
        m=min(kept,key=lambda m:(m['template_index'],m['proxy_carrier_index'],m['spectral_width_channels'],m['active_epochs_zero_based']))
        t,q,w=m['template_index'],m['proxy_carrier_index'],m['spectral_width_channels']
        a=next(a for a in r['responses'] if (a['template_index'],a['proxy_carrier_index'])==(t,q))
        aw=next(x for x in a['widths'] if x['width']==w)
        x=np.arange(a['first_proxy_index'],a['last_proxy_index']+1)-q
        injected={e for c in r['spec']['components'] for e in c['epochs']}
        for e in range(3):
            label=f'Epoch {e+1}: '+('injected' if e in injected else 'unchanged background')
            ax.plot(x,aw['on']['values'][e],color=COLORS[e],label=label,alpha=1 if e in m['active_epochs_zero_based'] else .35)
        ax.axvline(0,color='#40494f',alpha=.5,lw=.8)
        style(ax); ax.set_xlabel('Proxy channel offset from retained member')
        ax.set_title(f'Case {i} | width {w}\nActive epochs: '+', '.join(str(e+1) for e in m['active_epochs_zero_based']))
        ax.legend(fontsize=8,loc='upper left')
    fig.suptitle('Residual controls: uninjected background supplies apparent confirmation',fontsize=16,y=.97)
    fig.subplots_adjust(left=.055,right=.99,bottom=.20,top=.78,wspace=.24)
    fig.text(.5,.015,'First retained coordinate in each configuration. Faded curve = inactive epoch. Profiles are descriptive; no shape rule is validated.',ha='center',fontsize=10,color='#48545f')
    fig.savefig(OUT/'residual_background_responses.png',dpi=160); plt.close(fig)

if __name__=='__main__':main()
