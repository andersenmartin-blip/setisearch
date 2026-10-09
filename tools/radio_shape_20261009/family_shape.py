#!/usr/bin/env python3
"""Descriptive shapes of the existing complete 60ON/60OFF selection family."""
import argparse, csv, hashlib, io, json, resource, signal, time, zipfile
from pathlib import Path


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(a):
    sc=json.loads(Path(a.scope).read_text())
    assert sha(Path(__file__).read_bytes()) == sc['script_sha256']
    assert sha(Path(a.reference).read_bytes()) == sc['reference_sha256']
    assert sha(Path(a.seven_profiles).read_bytes()) == sc['seven_profiles_sha256']
    resource.setrlimit(resource.RLIMIT_CPU,(sc['limits']['CPU_s'],sc['limits']['CPU_s']))
    resource.setrlimit(resource.RLIMIT_AS,(sc['limits']['memory_bytes'],sc['limits']['memory_bytes']))
    signal.signal(signal.SIGALRM,lambda s,f: (_ for _ in ()).throw(TimeoutError('wall cap')))
    signal.alarm(sc['limits']['wall_s'])
    cpu0,wall0=time.process_time(),time.monotonic()
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    refs=json.loads(Path(a.reference).read_text())
    assert len(refs)==120 and len({x['id'] for x in refs})==120
    scans=sc['scans']; profiles={}; checks=[]
    with np.load(a.seven_profiles,allow_pickle=False) as d:
        assert d['scans'].tolist()==scans
        assert np.array_equal(d['source_channel_offsets'],np.arange(-64,65))
        for k,pid in enumerate(d['ids'].tolist()):
            profiles[pid]=d['mean_saved_row_normalized_minus_saved_flank'][k].copy()
    assert set(profiles)==set(sc['seven_ids'])
    archive=Path(a.archive)
    with archive.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    assert archive.stat().st_size==sc['archive']['bytes'] and digest==sc['archive']['sha256']
    metadata={x['id']:x for x in refs}

    def add(pid,norm,raw,medians,residual,width,channel):
        r=metadata[pid]
        assert pid not in profiles and r['width']==width and r['source_channel']==channel
        assert norm.shape==(6,16,129) and residual.shape==(6,16)
        np.testing.assert_array_equal(norm,raw.astype(np.float64)/medians[:,:,None])
        assert np.isfinite(norm).all() and np.isfinite(residual).all()
        # Algebraic recovery of the old saved baseline, not a new flank estimate.
        old_center=norm[:,:,64-width//2:65+width//2].mean(axis=-1)
        recovered_baseline=old_center-residual
        reconstructed=norm-recovered_baseline[:,:,None]
        error=float(np.max(np.abs(reconstructed[:,:,64-width//2:65+width//2].mean(axis=-1)-residual)))
        assert error<sc['arithmetic_tolerance']
        for i,s in enumerate(scans):
            assert abs(float(residual[i].mean())-r['by_scan'][s]['mean_residual'])<sc['arithmetic_tolerance']
        profiles[pid]=reconstructed.mean(axis=1)
        checks.append({'id':pid,'old_width':width,'old_selected_width_reconstruction_max_abs_error':error,
                       'saved_row_normalization_exact':True,'old_six_scan_means_verified':True})

    with zipfile.ZipFile(archive) as z:
        for pin in sc['patch_members']:
            b=z.read(pin['path'])
            assert len(b)==pin['bytes'] and sha(b)==pin['sha256']
            with np.load(io.BytesIO(b),allow_pickle=False) as d:
                assert d['scan_labels'].tolist()==scans
                if pin['kind']=='single':
                    add(pin['id'],d['row_normalized_power'],d['raw_power'],d['saved_full_chunk_row_medians'],
                        d['residual_each_row'],int(d['selected_width_channels']),int(d['source_channel']))
                else:
                    ids=d['profile_ids'].tolist();assert len(ids)==104 and len(set(ids))==104
                    for k,pid in enumerate(ids):
                        add(pid,d['row_normalized_power'][k],d['raw_power'][k],d['saved_row_medians'],
                            d['residual_each_row'][k],int(d['selected_widths'][k]),int(d['source_channels'][k]))
    assert set(profiles)==set(metadata) and len(checks)==113
    records=[]
    for r in refs:
        p=profiles[r['id']]
        assert p.shape==(6,129) and np.isfinite(p).all()
        # Old selected width provides provenance only; all new windows are fixed.
        for i,s in enumerate(scans):
            h=r['width']//2
            assert abs(float(p[i,64-h:65+h].mean())-r['by_scan'][s]['mean_residual'])<sc['arithmetic_tolerance']
        orig=scans.index(r['scan']);ctrl=sc['adjacency'][r['scan']]
        means={s:{str(w):float(p[i,64-w//2:65+w//2].mean()) for w in sc['widths_channels']} for i,s in enumerate(scans)}
        central=means[r['scan']]['1']; neighbor=float((p[orig,63]+p[orig,65])/2)
        records.append({'id':r['id'],'scan':r['scan'],'role':r['scan'].split('_')[1],'rank':r['rank'],
                        'source_channel':r['source_channel'],'frequency_hz':r['frequency_hz'],'original_selected_width':r['width'],
                        'adjacent_control_count':len(ctrl),'reused_seven_shape':r['id'] in sc['seven_ids'],
                        'fixed_window_mean_all_scans':means,'immediate_neighbor_mean':neighbor,
                        'central_minus_immediate_neighbors':central-neighbor,
                        'fixed_center_origin_minus_max_adjacent_control':{str(w):means[r['scan']][str(w)]-max(means[s][str(w)] for s in ctrl) for w in sc['widths_channels']}})
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(out/'ALL_120_FREQUENCY_PROFILES.npz',ids=np.array([r['id'] for r in refs]),
                        scans=np.array(scans),source_channel_offsets=np.arange(-64,65),
                        frequency_offsets_hz=np.arange(-64,65)*sc['df_hz'],
                        mean_saved_normalized_minus_recovered_or_direct_saved_flank=np.array([profiles[r['id']] for r in refs]))
    fields=['id','scan','role','rank','source_channel','frequency_hz','original_selected_width','adjacent_control_count',
            'central_mean','immediate_neighbor_mean','central_minus_immediate_neighbors']+[f'origin_window_{w}' for w in sc['widths_channels']]+[f'fixed_adjacent_difference_{w}' for w in sc['widths_channels']]
    with (out/'ALL_120_SHAPE_METRICS.csv').open('w',newline='') as fh:
        wr=csv.DictWriter(fh,fieldnames=fields);wr.writeheader()
        for r in records:
            row={k:r[k] for k in fields if k in r};row['central_mean']=r['fixed_window_mean_all_scans'][r['scan']]['1']
            for w in sc['widths_channels']:
                row[f'origin_window_{w}']=r['fixed_window_mean_all_scans'][r['scan']][str(w)]
                row[f'fixed_adjacent_difference_{w}']=r['fixed_center_origin_minus_max_adjacent_control'][str(w)]
            wr.writerow(row)
    groups={}
    for role in ['on','off']:
        for count in [None,1,2]:
            for width in [None,1,3]:
                xs=[r for r in records if r['role']==role and (count is None or r['adjacent_control_count']==count) and (width is None or r['original_selected_width']==width)]
                if not xs:continue
                key=f'{role}_controls_{count if count else "all"}_original_width_{width if width else "all"}'
                groups[key]={'n':len(xs),'ids':[r['id'] for r in xs]}
                for name,get in [('central_minus_immediate_neighbors',lambda r:r['central_minus_immediate_neighbors']),
                                 ('fixed_adjacent_difference_width1',lambda r:r['fixed_center_origin_minus_max_adjacent_control']['1']),
                                 ('origin_window_width1',lambda r:r['fixed_window_mean_all_scans'][r['scan']]['1']),
                                 ('origin_window_width3',lambda r:r['fixed_window_mean_all_scans'][r['scan']]['3'])]:
                    vals=np.array([get(r) for r in xs]);q=np.quantile(vals,[0,.25,.5,.75,1],method='linear')
                    groups[key][name]={'min':float(q[0]),'q25':float(q[1]),'median':float(q[2]),'q75':float(q[3]),'max':float(q[4])}
    fig,axs=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    for j,s in enumerate(scans):
        xs=[r for r in records if r['scan']==s]
        for ax,key in [(axs[0],'central_minus_immediate_neighbors'),(axs[1],'fixed_adjacent_difference_width1')]:
            yy=[r['central_minus_immediate_neighbors'] if key.startswith('central') else r['fixed_center_origin_minus_max_adjacent_control']['1'] for r in xs]
            xx=[j+(r['rank']-10.5)*.015 for r in xs]
            ax.scatter(xx,yy,color='#0072b2' if s.endswith('_on') else '#d55e00',marker='o' if s.endswith('_on') else 's',s=22,alpha=.8)
            for r,x,y in zip(xs,xx,yy):
                if r['id'] in sc['seven_ids']:ax.scatter([x],[y],s=85,facecolors='none',edgecolors='black',linewidths=1)
    for ax in axs:
        ax.set_yscale('symlog',linthresh=.1)
        ax.axhline(0,color='gray',linewidth=.7)
        ax.set_xticks(range(6),['ON1','OFF1','ON2','OFF2','ON3','OFF3'])
        ax.grid(axis='y',alpha=.15)
        ax.set_xlabel('Original scan; horizontal jitter preserves rank1..20')
    axs[0].set_title('Central minus immediate-neighbor mean')
    axs[1].set_title('Fixed center minus max adjacent control at same center')
    axs[0].set_ylabel('Saved normalized additive units (symlog above ±0.1)')
    fig.suptitle('Complete preselected family:60 ON /60 OFF; seven weak ON outlined\nOne visit; descriptive distributions, no significance calibration',fontsize=13)
    fig.savefig(out/'ALL_120_SHAPE_COMPARISON.png',dpi=130);plt.close(fig)
    result={'scope':'POST_DATA_DESCRIPTIVE_EXISTING_COMPLETE_SELECTION_FAMILY_SHAPE',
            'script_sha256':sc['script_sha256'],'scope_sha256':sha(Path(a.scope).read_bytes()),
            'profiles':120,'reused_seven_shapes_without_remeasurement':7,'new_shape_profiles':113,
            'new_source_dataset_or_detector_selection':False,'native_controls_are_certified_noise':False,
            'exchangeability_or_independence_assumed':False,'qualification':'FAIL_CLOSED_UNCHANGED',
            'seven_classification':'UNRESOLVED_UNCHANGED','checks':checks,'groups':groups,
            'records':records,'limitations':sc['limitations']}
    (out/'ALL_120_SHAPE_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    receipt={'success':True,'process_CPU_s':time.process_time()-cpu0,'wall_s':time.monotonic()-wall0,
             'maxrss_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'all113_patch_identities_verified':True,
             'all120_old_selected_width_means_verified':True,'new_telescope_HTTP_requests':0,
             'files':{p.name:{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(out.iterdir())}}
    (out/'EXECUTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    signal.alarm(0);print(json.dumps(receipt))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['scope','reference','seven-profiles','archive','output']:p.add_argument('--'+name,required=True)
    run(p.parse_args())
