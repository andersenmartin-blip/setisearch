"""Frozen-subset dynamic supplementary context diagnostics; no data-dependent display choices."""
from pathlib import Path
import csv,datetime,hashlib,json,sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'runtime'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
B=Path(__file__).resolve().parent
sys.path.insert(0,str(B))
import publication
import argparse
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    result=B/'results/FOLLOWUP_RESULT_CONTEXT_SUPPLEMENT_AZ.json';r=read(result);plan=read(B/'PLAN_FROZEN_CONTEXT_SUPPLEMENT_AZ.json');pins={str(result):sha(result)};figures=[]
    assert r['status']=='COMPLETE' and r['plan_sha256']==sha(B/'PLAN_FROZEN_CONTEXT_SUPPLEMENT_AZ.json')
    for path,d in plan['source_and_input_sha256'].items():assert sha(path)==d
    pubs={str(Path(x['path']).resolve()):x for x in r['publications']}
    (B/'figures').mkdir(exist_ok=False)
    for item in r['selected_representatives']:
        gid=item['group']['group_id'];identity=item['identity'];tag='_'.join(str(x) for x in identity)
        if identity not in plan['plot_identities']:continue
        local=result.parent/item['array_filename'];pins[str(local)]=sha(local);assert pins[str(local)]==pubs[str(local.resolve())]['sha256'];rep=item['group']['representative'];nu0=item['fixed_frequency_MHz'];width=rep['width_channels']
        with np.load(local,allow_pickle=False) as z:
            channels=z['native_channels']
            for mode in ('FULL','ZOOM'):
                fig,axes=plt.subplots(3,2,figsize=(13,10),squeeze=False,layout='constrained');im=ScalarMappable(norm=Normalize(-2,15),cmap='magma')
                for j,meta in enumerate(item['scans']):
                    ax=axes[j//2,j%2];df=meta['df_hz'];dt=meta['dt_seconds'];fixed=meta['fixed_frequency_companion'];center=fixed['mapped_center_channel'];keep=np.ones(len(channels),dtype=bool) if mode=='FULL' else (channels>=center-32)&(channels<=center+32)
                    if np.any(keep):
                        ch=channels[keep];x=(meta['fch1_mhz']-nu0)*1e6+ch*df;values=z[f'normalized_scan{j}'][:,keep];track=(meta['fch1_mhz']-nu0)*1e6+z[f'original_integer_channels_scan{j}']*df;fixedx=(meta['fch1_mhz']-nu0)*1e6+center*df
                        im=ax.imshow(values,origin='lower',aspect='auto',interpolation='nearest',extent=[x[0]-.5*df,x[-1]+.5*df,-.5,15.5],vmin=-2,vmax=15,cmap='magma');ax.plot(track,np.arange(16),color='cyan',lw=1.,zorder=3);ax.axvline(fixedx,color='#ffad33',lw=1.1,ls=(0,(3,4)),zorder=4);ax.set_xlim(x[0]-.5*df,x[-1]+.5*df)
                    else:ax.text(.5,.5,'Fixed frequency outside saved/native support',ha='center',transform=ax.transAxes)
                    companion=f"{fixed['empirical_score']:.3g}" if fixed['status']=='MEASURED' else 'unsupported'
                    ax.set_title(f"{meta['role']} scan {j} · original score {meta['forced_center_ESS']:.3g}; fixed score {companion}",fontsize=10);ax.set_ylabel('Time row');ax.set_xlabel('Frequency offset (Hz)');ax.set_yticks([0,5,10,15]);sec=ax.secondary_yaxis('right',functions=(lambda y,d=dt:y*d,lambda t,d=dt:t/d));sec.set_ylabel('Elapsed time (s)');sec.set_yticks([0,100,200])
                label='full saved local windows' if mode=='FULL' else '±32 native channels around mapped fixed frequency'
                fig.suptitle(f"{r['target']}: {label}\nSupplementary {identity[0]} / {identity[1]} group {gid} · template width {width} channel(s) · original drift {rep['drift_hz_s']:.5g} Hz/s\nZero frequency offset = {nu0:.12g} MHz. Posthoc descriptive fixed-frequency control.\nEmpirical scores are not Gaussian significance; no automatic veto or physical origin assigned.",fontsize=10)
                fig.legend(handles=[Line2D([0],[0],color='cyan',lw=1.,label='Inherited representative integer track'),Line2D([0],[0],color='#ffad33',lw=1.1,ls=(0,(3,4)),label='Supplementary fixed-frequency control')],loc='outside lower center',ncol=2,fontsize=9);fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.7,label='Normalized power (display clipped −2 to 15)')
                dest=B/f'figures/CONTEXT_{tag}_{mode}_AZ.png';receipt=publication.publish_png(fig,dest,dpi=150,bbox_inches='tight');plt.close(fig);rp=dest.with_suffix('.publication.json')
                with rp.open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
                figures.append({'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size,'mode':mode,'identity':identity,'publication_receipt_path':str(rp),'publication_receipt_sha256':sha(rp)})
    table=B/'results/GROUP_METRICS_CONTEXT_SUPPLEMENT_AZ.tsv'
    with table.open('x') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['namespace','class','group_id','seed_row','source_scan','source_ESS','frequency_MHz','width_channels','drift_Hz_s']+[f'original_ESS_scan{j}' for j in range(6)]+[f'fixed_ESS_scan{j}' for j in range(6)]+[f'max_positive_row_fraction_scan{j}' for j in range(6)])
        for item in r['selected_representatives']:
            g=item['group'];rep=g['representative'];sc=item['scans'];w.writerow([item['origin'],g['class'],g['group_id'],g['representative_global_seed_row'],rep['source_scan'],rep['source_ESS'],rep['frequency_at_midpoint_mhz'],rep['width_channels'],rep['drift_hz_s']]+[s['recovered_ESS'] for s in sc]+[s['fixed_frequency_companion'].get('empirical_score') for s in sc]+[s['normalized_original_track']['maximum_positive_row_fraction'] for s in sc])
    for path,d in pins.items():assert sha(path)==d
    for path,d in plan['source_and_input_sha256'].items():assert sha(path)==d
    manifest={'schema':'SETI_AZ_CONTEXT_SUPPLEMENT_FIGURES_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(__file__),'publication_source_sha256':sha(B/'publication.py'),'plan_sha256':sha(B/'PLAN_FROZEN_CONTEXT_SUPPLEMENT_AZ.json'),'input_sha256_unchanged':pins,'figures':figures,'plot_identities':plan['plot_identities'],'display_limits':[-2,15],'all_supplementary_numeric_contexts_retained':True,'supplementary_group_count':r['supplementary_group_count'],'zero_pending_noop':r['zero_pending_noop'],'fixed_frequency_timing':'posthoc supplementary','scientific_values_changed':False,'visual_QA_pending':True,'table':{'path':str(table),'sha256':sha(table),'bytes':table.stat().st_size}}
    with (B/'figures/FIGURE_MANIFEST_CONTEXT_SUPPLEMENT_AZ.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({'status':'COMPLETE_VISUAL_QA_PENDING','figures':len(figures),'plot_identities':plan['plot_identities']}),flush=True)
if __name__=='__main__':
    main()
