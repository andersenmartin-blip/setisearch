"""Fixed complete displays of the two-event normalization diagnostics; no classifier."""
from pathlib import Path
import csv,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT=Path(__file__).resolve().parent

def rows(name):return list(csv.DictReader((OUT/name).open()))
def main():
 (OUT/'figures').mkdir(exist_ok=True);prof=rows('PROFILE_DIAGNOSTICS.csv');merged=rows('MERGED_WINDOW_DIAGNOSTICS.csv');native=rows('NATIVE_ORDER_DIAGNOSTICS.csv');ids=['V2E2-0092','V2E2-0104'];display=[];dates={r['dp_id']:r['date_obs'][:10]for r in prof}
 plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
 fig,axes=plt.subplots(2,2,figsize=(13.5,7.5),constrained_layout=True)
 for i,rid in enumerate(ids):
  rs=[r for r in prof if r['candidate_id']==rid and r['frame']=='barycentric'];xx=np.arange(len(rs));labels=[r['date_obs'][:10]for r in rs];norm=np.array([float(r['normalization_adu'])for r in rs]);noise=np.array([float(r['first_difference_noise_proxy_adu'])for r in rs])
  axes[i,0].plot(xx,norm,'o-',color='#176b8f',label='Merged local median (ADU)');axes[i,0].plot(xx,noise,'s--',color='#d28a19',label='Difference noise proxy (ADU)');axes[i,0].set_title(rid+' — unnormalized local scale');axes[i,0].set_ylabel('ADU');axes[i,0].legend(fontsize=8)
  axes[i,1].plot(xx,norm/noise,'o-',color='#476b2a');axes[i,1].axhline(3,color='#b13b3b',ls='--',label='Existing flag: median / noise ≤3');axes[i,1].set_title(rid+' — existing low-continuum diagnostic');axes[i,1].set_ylabel('Median / noise proxy');axes[i,1].legend(fontsize=8)
  for j,r in enumerate(rs):
   if r['is_discovery_exposure']=='True':
    axes[i,0].scatter(j,norm[j],marker='*',s=160,color='black',zorder=6);axes[i,1].scatter(j,norm[j]/noise[j],marker='*',s=160,color='black',zorder=6)
  for ax in axes[i]:ax.set_xticks(xx,labels,rotation=35,ha='right');ax.grid(alpha=.2)
 fig.suptitle('HD114386: the same final epoch is weak in both spectral windows\nBarycentric windows shown; both frames retained in tables. Stars mark discovery epochs. Noise proxy is not a calibrated error.',fontsize=12)
 fig.savefig(OUT/'figures/EPOCH_NORMALIZATION.png',dpi=150);plt.close(fig)
 for rid in ids:
  rr=[r for r in merged if r['candidate_id']==rid];fig,axes=plt.subplots(4,3,figsize=(15,12),constrained_layout=True)
  for i,r in enumerate(rr):
   with np.load(OUT/r['derived_path'])as z:a={k:z[k].copy()for k in z.files}
   cb=float(r['center_sampled_bary_air_angstrom']);ct=float(r['center_native_topocentric_air_angstrom']);norm=float(r['normalization_adu']);ax=axes[i,0];ax.plot(a['wavelength_bary_air_angstrom']-cb,a['raw_flux'],lw=.8,color='#176b8f');ax.plot(a['profile_offset'],a['raw_linear_background'],color='#d28a19',lw=1.6,label='Side-fit background');ax.axhline(norm,color='black',ls=':',lw=.8,label='±2 Å median');ax.axhline(0,color='gray',lw=.5);ax.set_title(dates[r['dp_id']]+' '+r['frame']+'\nMerged flux; median '+f'{norm:.1f}'+' ADU');ax.legend(fontsize=7);ax.set_xlabel('Barycentric window offset (Å)');ax.set_ylabel('Merged uncalibrated ADU');ax.set_xlim(-2,2)
   for n in [n for n in native if(n['candidate_id'],n['dp_id'],n['frame'])==(r['candidate_id'],r['dp_id'],r['frame'])]:
    with np.load(OUT/n['derived_path'])as z:axes[i,1].plot(z['native_wave']-ct,z['native_flux'],lw=.8,label='Order '+n['order']+'; median '+f"{float(n['native_median_adu']):.1f}")
   axes[i,1].axhline(0,color='gray',lw=.5);axes[i,1].set_xlim(-2,2);axes[i,1].set_xlabel('Topocentric native window offset (Å)');axes[i,1].set_ylabel('Native extracted ADU');axes[i,1].legend(fontsize=7);axes[i,1].set_title('All covering orders, unnormalized')
   axes[i,2].plot(a['profile_offset'],a['raw_residual']/norm,color='#583b80',lw=.9);axes[i,2].axhline(0,color='gray',lw=.5);axes[i,2].axvspan(-.25,.25,color='#176b8f',alpha=.08);axes[i,2].set_xlabel('Profile-frame offset (Å)');axes[i,2].set_ylabel('Residual / local median');axes[i,2].set_title('Saved normalized residual; low flag '+r['local_continuum_low']);axes[i,2].set_xlim(-1,1)
  fig.suptitle(rid+' — discovery and every flagged profile, all frames\nPer-panel vertical scales. Native and merged ADU have different extraction/scaling; do not equate amplitudes.',fontsize=12)
  fig.savefig(OUT/f'figures/{rid}_FOCUSED_PROFILES.png',dpi=135);plt.close(fig)
 for start in range(0,len(native),4):
  rr=native[start:start+4];fig,axes=plt.subplots(4,2,figsize=(12,12),constrained_layout=True)
  for i,r in enumerate(rr):
   with np.load(OUT/r['derived_path'])as z:raw=z['raw_cutout'][:,8:25];excess=z['raw_excess'][:,8:25]
   frac=float(r['raw_column'])-round(float(r['raw_column']));lo,hi=float(raw.min()),float(raw.max());lim=max(float(abs(excess).max()),1.)
   im=axes[i,0].imshow(raw,origin='lower',aspect='auto',extent=(-8.5,8.5,-15.5,15.5),cmap='viridis',vmin=lo,vmax=hi);fig.colorbar(im,ax=axes[i,0],label='Raw ADU');im=axes[i,1].imshow(excess,origin='lower',aspect='auto',extent=(-8.5,8.5,-15.5,15.5),cmap='RdBu_r',vmin=-lim,vmax=lim);fig.colorbar(im,ax=axes[i,1],label='ADU minus fixed side background')
   for ax in axes[i]:ax.axhline(0,color='black',lw=.5);ax.axvline(frac,color='black',lw=.5);ax.set_xlabel('Detector column offset');ax.set_ylabel('Dispersion-row offset')
   title=f"{r['candidate_id']} {dates[r['dp_id']]} {r['frame']} order {r['order']}";axes[i,0].set_title(title+'\nOriginal counts');axes[i,1].set_title('Signed excess; independent symmetric scale')
   display.append({'candidate_id':r['candidate_id'],'dp_id':r['dp_id'],'frame':r['frame'],'order':int(r['order']),'path':r['derived_path'],'sha256':r['derived_sha256'],'figure':f'figures/RAW_CONTEXT_{start//4+1:02d}.png','row':i+1,'column_range':[-8,8],'dispersion_row_range':[-15,15],'raw_scale':[lo,hi],'signed_excess_scale':[-lim,lim]})
  fig.suptitle('Fixed central raw context: no coordinate changes or new origin assignments\nBackground = per-column median of first10 and last10 rows of original31×33 cutout.',fontsize=12);fig.savefig(OUT/f'figures/RAW_CONTEXT_{start//4+1:02d}.png',dpi=135);plt.close(fig)
 (OUT/'FIGURE_INDEX.json').write_text(json.dumps({'raw_panels':display,'profile_figures':[f'figures/{rid}_FOCUSED_PROFILES.png'for rid in ids],'epoch_summary':'figures/EPOCH_NORMALIZATION.png','frames_are_alternative_views_not_independent_exposures':True},indent=2)+'\n')
 print('Created6figures: oneepoch,2profilepages,3rawpages/12allorderpanels')
if __name__=='__main__':main()
