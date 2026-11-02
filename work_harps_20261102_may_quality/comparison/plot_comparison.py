#!/usr/bin/env python3
"""Plot all fixed event profiles after completed comparison; no new statistics.

This presentation script never runs the science comparison or accesses FITS data.
It reads only hash-verified reference and already computed profile NPZ files.
"""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
RESULTS=HERE/'results'
REPO=HERE.parents[1]
CONTEXT=REPO/'work_harps_20261102_berv_followup/prospective_comparison/results'
COLORS=['#263238','#1976b9','#dc7420','#3b8b4b']
STYLES=['-','-','--','-.']
FRAMES=['barycentric','topocentric']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def profile(path,expected_hash):
    if sha(path)!=expected_hash:raise ValueError('Profile hash mismatch: '+str(path))
    with np.load(path,allow_pickle=False)as archive:
        return {key:np.array(archive[key],copy=True)for key in ['offset_air_angstrom','normalized_flux','residual']}


def bounds(series,field,core):
    samples=[]
    for entry in series:
        x=entry['arrays']['offset_air_angstrom'];y=entry['arrays'][field]
        keep=np.isfinite(y)&((np.abs(x)<=.250000001)if core else np.ones(x.shape,dtype=bool))
        samples.extend(y[keep].tolist())
    if not samples:return (-1.,1.)
    lo,hi=min(samples),max(samples)
    margin=.06*(hi-lo)if hi>lo else max(abs(lo)*.06,.05)
    return lo-margin,hi+margin


def main():
    if not(RESULTS/'SUMMARY.json').is_file():raise RuntimeError('Completed science summary required; this script does not run the comparison.')
    plan=load(HERE/'PLOT_PLAN.json')
    if sha(Path(__file__))!=plan['script_sha256']:raise ValueError('Prospective plot code changed')
    if sha(HERE/'EVENTS.json')!=plan['events_sha256']:raise ValueError('Event list changed')
    if sha(CONTEXT/'OUTPUT_HASHES.json')!=plan['closed_prior_output_manifest_sha256']:raise ValueError('Closed prior phase manifest changed')
    context_hashes=load(CONTEXT/'OUTPUT_HASHES.json')
    for name,expected in context_hashes.items():
        if sha(CONTEXT/name)!=expected:raise ValueError('Closed prior science output changed: '+name)
    original_hashes=load(RESULTS/'OUTPUT_HASHES.json')
    for name,expected in original_hashes.items():
        if sha(RESULTS/name)!=expected:raise ValueError('Computed science output changed: '+name)
    events=load(HERE/'EVENTS.json')
    rows=load(RESULTS/'ALL_COMPARISON_MEASUREMENTS.json')
    if len(rows)!=12:raise ValueError('All twelve May-quality slots required')
    context_rows=load(CONTEXT/'ALL_COMPARISON_MEASUREMENTS.json')
    if len(context_rows)!=24:raise ValueError('Closed prior24 context slots changed')
    plot_rows=[(r,CONTEXT,'Prior archive')for r in context_rows]+[(r,RESULTS,'May-quality archive')for r in rows]
    output=RESULTS/'figures'
    output.mkdir(exist_ok=False)
    byevent={e['candidate_id']:e for e in events}
    selected=[byevent[identity]for identity in plan['events_to_plot']]
    details=[];all_series={}
    for event in selected:
        grouped={}
        for frame in FRAMES:
            reference=event['discovery_profiles'][frame]
            discovery=profile(HERE/'inputs'/reference['profile_path'],reference['profile_sha256'])
            entries=[{'label':f"Discovery {event['discovery_date_obs'][:10]} · BERV {event['discovery_berv_km_s']:+.3f} km/s",
                      'dp_id':event['discovery_dp_id'],'arrays':discovery,'profile_sha256':reference['profile_sha256'],
                      'discovery':True,'status':'EXISTING_REFERENCE','color_index':0}]
            slot_index=0
            for row,row_root,phase_label in plot_rows:
                if row['candidate_id']!=event['candidate_id']or row['frame']!=frame:continue
                slot_index+=1
                if row['status']!='MEASURED_DESCRIPTIVE_CONTEXT':
                    details.append({'candidate_id':event['candidate_id'],'frame':frame,'dp_id':row['dp_id'],
                                    'status':row['status'],'plotted':False})
                    continue
                arrays=profile(row_root/row['profile_path'],row['profile_sha256'])
                entries.append({'label':f"{phase_label} {row['date_obs'][:10]} · BERV {row['berv_km_s']:+.3f} km/s",
                                'dp_id':row['dp_id'],'arrays':arrays,'profile_sha256':row['profile_sha256'],
                                'discovery':False,'status':row['status'],'color_index':slot_index})
                details.append({'candidate_id':event['candidate_id'],'frame':frame,'dp_id':row['dp_id'],
                                'status':row['status'],'plotted':True,'profile_sha256':row['profile_sha256']})
            grouped[frame]=entries
        all_series[event['candidate_id']]=grouped
        combined=[entry for entries in grouped.values()for entry in entries]
        ylimits=[bounds(combined,'normalized_flux',False),bounds(combined,'residual',True)]
        fig,axes=plt.subplots(2,2,figsize=(12.5,7.8),layout='constrained')
        for i,frame in enumerate(FRAMES):
            for j,(field,limits)in enumerate([('normalized_flux',(-1,1)),('residual',(-.25,.25))]):
                ax=axes[i,j]
                for k,entry in enumerate(grouped[frame]):
                    color_index=entry['color_index']
                    a=entry['arrays'];ax.plot(a['offset_air_angstrom'],a[field],color=COLORS[color_index],ls=STYLES[color_index],lw=1.25,
                                            alpha=.85,label=entry['label'])
                ax.set_xlim(*limits);ax.set_ylim(*ylimits[j]);ax.axvline(0,color='#707070',lw=.7,alpha=.65)
                if j==0:
                    ax.axvspan(-1,-.6,color='#999999',alpha=.08);ax.axvspan(.6,1,color='#999999',alpha=.08)
                else:ax.axhline(0,color='#707070',lw=.7,alpha=.55)
                ax.grid(alpha=.18);ax.set_title(frame.capitalize()+(' · full fixed window'if j==0 else' · correlation core'))
                ax.set_ylabel('Flux / local median'if j==0 else'Residual / local median')
                ax.set_xlabel(f'Offset in {frame} air wavelength [Å]')
        handles,labels=axes[0,0].get_legend_handles_labels()
        axes[0,0].legend(handles,labels,fontsize=7.5,loc='best',framealpha=.92)
        fig.suptitle(f"{event['candidate_id']} · {event['target']} · fixed barycentric center {event['fitted_center_bary_air_angstrom']:.4f} Å\n"
                     'Separate post-hoc May-quality phase plus closed prior context. No origin assignment.',fontsize=12)
        path=output/(event['candidate_id']+'_PROFILE_COMPARISON.png');fig.savefig(path,dpi=150);plt.close(fig)
    fig,axes=plt.subplots(len(selected),2,figsize=(13,2.3*len(selected)),squeeze=False,layout='constrained')
    for i,event in enumerate(selected):
        grouped=all_series[event['candidate_id']]
        limits=bounds([entry for entries in grouped.values()for entry in entries],'residual',True)
        for j,frame in enumerate(FRAMES):
            ax=axes[i,j]
            for k,entry in enumerate(grouped[frame]):
                color_index=entry['color_index']
                a=entry['arrays'];ax.plot(a['offset_air_angstrom'],a['residual'],color=COLORS[color_index],ls=STYLES[color_index],lw=1.05,alpha=.9)
            ax.set_xlim(-.25,.25);ax.set_ylim(*limits);ax.axhline(0,color='#777777',lw=.6);ax.axvline(0,color='#777777',lw=.6)
            ax.grid(alpha=.16);ax.set_title(f"{event['candidate_id']} · {frame}",fontsize=10)
            ax.set_ylabel('Normalized residual')
            if i==len(selected)-1:ax.set_xlabel('Fixed-frame air-wavelength offset [Å]')
    fig.suptitle('All six HD122640 records · discovery (dark), May 22 (blue), Jan 20 (orange), May 20 quality phase (green)\n'
                 'Fixed zero-shift comparison; rows are correlated records, not six independent signals.',fontsize=12)
    fig.savefig(output/'ALL_SIX_HD122640_RESIDUALS.png',dpi=150);plt.close(fig)
    for name,expected in original_hashes.items():
        if sha(RESULTS/name)!=expected:raise ValueError('Science output changed during plotting: '+name)
    for name,expected in context_hashes.items():
        if sha(CONTEXT/name)!=expected:raise ValueError('Closed prior output changed during plotting: '+name)
    index={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'ALL_DECLARED_HD122640_PROFILES_PLOTTED',
           'prospective_plot_plan_sha256':sha(HERE/'PLOT_PLAN.json'),'script_sha256':sha(Path(__file__)),
           'events_plotted':[e['candidate_id']for e in selected],
           'events_without_new_selected_epochs':[e['candidate_id']for e in events if e['target']=='HD135204'],
           'profiles':details,'figures':[{'path':str(p.relative_to(RESULTS)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(output.glob('*.png'))],
           'y_axis_rule':'All finite plotted values plus6percent padding, shared between frames for each event and quantity; no clipping or per-frame rescaling.',
           'new_statistics_or_thresholds':False,'original_science_outputs_unchanged':True,'closed_prior_24_profiles_unchanged':True,'prior_profile_recomputation':False,'origin_assignments':0}
    (RESULTS/'PLOT_INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps({k:v for k,v in index.items()if k!='profiles'},indent=2))


if __name__=='__main__':
    main()
