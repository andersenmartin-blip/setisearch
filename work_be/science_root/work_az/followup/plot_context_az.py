"""Prospective metadata-driven full and fixed-frequency zoom context figures."""
from pathlib import Path
import argparse,datetime,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
import publication
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 q=argparse.ArgumentParser();q.add_argument('result');q.add_argument('output_directory');a=q.parse_args();result=Path(a.result).resolve();r=json.loads(result.read_text());out=Path(a.output_directory).resolve();out.mkdir(exist_ok=True,parents=True);bound={str(result):sha(result)};figures=[]
 for idx,item in enumerate(r['selected_representatives']):
  local=result.parent/f'SELECTED_{idx+1}_SIX_SCAN_LOCAL_ARRAYS_AZ.npz';bound[str(local)]=sha(local);rep=item['group']['representative'];nu0=item['fixed_frequency_MHz'];width=rep['width_channels']
  with np.load(local,allow_pickle=False) as z:
   channels=z['native_channels']
   for mode in ('FULL','ZOOM'):
    fig,axes=plt.subplots(3,2,figsize=(13,10),squeeze=False,layout='constrained');im=ScalarMappable(norm=Normalize(-2,15),cmap='magma')
    for j,meta in enumerate(item['scans']):
     ax=axes[j//2,j%2];df=meta['df_hz'];dt=meta['dt_seconds'];fixed=meta['fixed_frequency_companion'];center=fixed['mapped_center_channel'];keep=np.ones(len(channels),dtype=bool) if mode=='FULL' else (channels>=center-32)&(channels<=center+32)
     if np.any(keep):
      ch=channels[keep];x=(meta['fch1_mhz']-nu0)*1e6+ch*df;values=z[f'normalized_scan{j}'][:,keep];track=(meta['fch1_mhz']-nu0)*1e6+z[f'original_integer_channels_scan{j}']*df;fixedx=(meta['fch1_mhz']-nu0)*1e6+center*df
      im=ax.imshow(values,origin='lower',aspect='auto',interpolation='nearest',extent=[x[0]-.5*df,x[-1]+.5*df,-.5,15.5],vmin=-2,vmax=15,cmap='magma')
      ax.plot(track,np.arange(16),color='cyan',lw=1.,zorder=3);ax.axvline(fixedx,color='#ffad33',lw=1.1,ls=(0,(3,4)),zorder=4);ax.set_xlim(x[0]-.5*df,x[-1]+.5*df)
     else:ax.text(.5,.5,'Fixed frequency outside saved/native support',ha='center',transform=ax.transAxes)
     companion=f"{fixed['empirical_score']:.3g}" if fixed['status']=='MEASURED' else 'unsupported'
     ax.set_title(f"{meta['role']} scan {j} · original score {meta['forced_center_ESS']:.3g}; fixed score {companion}",fontsize=10);ax.set_ylabel('Time row');ax.set_xlabel('Frequency offset (Hz)');ax.set_yticks([0,5,10,15])
     sec=ax.secondary_yaxis('right',functions=(lambda y,d=dt:y*d,lambda t,d=dt:t/d));sec.set_ylabel('Elapsed time (s)');sec.set_yticks([0,100,200])
    label='full saved local windows' if mode=='FULL' else '±32 native channels around each mapped fixed-frequency center'
    fig.suptitle(f"{r['target']}: {label}\n{item['origin']} group {item['group']['group_id']} · template width {width} channel(s) · original drift {rep['drift_hz_s']:.5g} Hz/s\nZero frequency offset = {nu0:.12g} MHz. Inherited fixed-frequency companion rule frozen before BB visit65133 powers.\nEmpirical scores are not Gaussian significance; no automatic veto or physical origin is assigned.",fontsize=10)
    fig.legend(handles=[Line2D([0],[0],color='cyan',lw=1.,label='Original selected integer track'),Line2D([0],[0],color='#ffad33',lw=1.1,ls=(0,(3,4)),label='Prospective fixed-frequency companion')],loc='outside lower center',ncol=2,fontsize=9)
    fig.colorbar(im,ax=axes.ravel().tolist(),shrink=.7,label='Normalized power (display clipped −2 to 15)')
    dest=out/f"SELECTED_{idx+1}_{mode}_CONTEXT_AZ.png";publication_receipt=publication.publish_png(fig,dest,dpi=150,bbox_inches='tight');plt.close(fig);receiptpath=dest.with_suffix('.publication.json')
    with receiptpath.open('x') as f:json.dump(publication_receipt,f,indent=2,sort_keys=True);f.write('\n')
    figures.append({'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size,'mode':mode,'publication_receipt_path':str(receiptpath),'publication_receipt_sha256':sha(receiptpath)})
 for p,h in bound.items():assert sha(p)==h
 manifest={'schema':'SETI_AZ_PROSPECTIVE_CONTEXT_FIGURES_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':sha(__file__),'input_sha256_unchanged':bound,'figures':figures,'display_limits':[-2,15],'fixed_frequency_companion_prospectively_specified':True,'scientific_values_changed':False,'visual_QA_pending':True}
 with (out/'FIGURE_MANIFEST_AZ.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({'status':'FIGURES_COMPLETE_VISUAL_QA_PENDING','count':len(figures)}),flush=True)
if __name__=='__main__':main()
