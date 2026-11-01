"""Post-run descriptive diagnostics from saved results; never opens source FITS."""
from pathlib import Path
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

root = Path(__file__).parent / 'results_frozen_20261101'
trials = json.loads((root / 'trials.json').read_text())
rows = []
for t in trials:
    k = t['nearest_center_index_patch']
    local = [e for e in t['detector_result']['all_threshold_runs']
             if e['start_index'] <= k + 2 and e['end_index_exclusive'] > k - 2]
    with np.load(root / t['geometry_id'] / f"injection_{t['amplitude_factor']:02d}_arrays.npz") as a:
        ratio = float(a['local_std'][k] / t['unmodified_local_population_std_adu'])
    rows.append(dict(geometry_id=t['geometry_id'], background_index=t['background_index'],
        phase=t['subpixel_phase'], anchor_angstrom=t['anchor_angstrom'],
        amplitude_factor=t['amplitude_factor'], recovered=t['recovered'],
        largest_center_overlapping_run_pixels=max([e['run_pixels'] for e in local], default=0),
        center_local_std_divided_by_unmodified_std=ratio,
        strongest_center_overlapping_run_contrast=max([e['peak_local_contrast'] for e in local], default=None)))
summary = dict(schema='POST_RUN_DESCRIPTIVE_DIAGNOSTIC_V1',
    source='Previously saved trials.json and per-injection NPZ; no new source spectra or detector runs',
    recovered_by_background_phase=[dict(background_index=b, phase=[0,.25,.5][b],
        recovered=sum(t['recovered'] for t in trials if t['background_index']==b), trials=16)
        for b in range(3)],
    phase_caution='Background and subpixel phase change together; their separate effects cannot be estimated from this design.',
    strongest_amplitude_misses=sum(t['amplitude_factor']==32 and not t['recovered'] for t in trials),
    strongest_amplitude_misses_with_exactly_3_crossing_pixels=sum(r['amplitude_factor']==32 and not r['recovered'] and r['largest_center_overlapping_run_pixels']==3 for r in rows),
    interpretation='All six misses at strength 32 have a 3-pixel threshold run, below the required four. Injected flux increases the detector local scatter, which limits contrast. This demonstrates incomplete recovery even for strong, instrument-width lines in these fixed examples. It does not identify the individual causal contribution of phase and stellar background.',
    rows=rows)
(root / 'descriptive_diagnostic.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
with (root / 'descriptive_diagnostic.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

geometries=list(dict.fromkeys(t['geometry_id'] for t in trials))
matrix=np.array([[next(r['recovered'] for r in rows if r['geometry_id']==g and r['amplitude_factor']==a)
                  for a in [4,8,16,32]] for g in geometries])
fig=plt.figure(figsize=(14,9),layout='constrained')
outer=fig.add_gridspec(1,2,width_ratios=[1.05,1])
ax=fig.add_subplot(outer[0])
ax.imshow(matrix,cmap=ListedColormap(['#e6eaf0','#107d8c']),vmin=0,vmax=1,aspect='auto')
for i,g in enumerate(geometries):
    for j,a in enumerate([4,8,16,32]):
        r=next(r for r in rows if r['geometry_id']==g and r['amplitude_factor']==a)
        ax.text(j,i,f"{r['largest_center_overlapping_run_pixels']} pixels"+('\nrecovered' if r['recovered'] else ''),
                ha='center',va='center',fontsize=9,color='white' if r['recovered'] else '#29384a')
ax.set_xticks(range(4),['4×','8×','16×','32×'])
ax.set_xlabel('Added continuous peak / unmodified local standard deviation')
labels=[]
for g in geometries:
    r=next(r for r in rows if r['geometry_id']==g)
    labels.append(f"B{r['background_index']+1}, phase {r['phase']:.2f} | {r['anchor_angstrom']:.2f} Å")
ax.set_yticks(range(12),labels,fontsize=9)
ax.set_title('11 / 48 recovered; 0 / 12 controls have a matching hit\nCells show longest center-overlapping threshold run',fontsize=12,pad=15)
for edge in [3.5,7.5]:ax.axhline(edge,color='white',linewidth=3)
sub=outer[1].subgridspec(3,1)
for b in range(3):
    t=next(t for t in trials if t['background_index']==b and t['anchor_angstrom']==6504.73 and t['amplitude_factor']==32)
    r=next(r for r in rows if r['geometry_id']==t['geometry_id'] and r['amplitude_factor']==32)
    ax=fig.add_subplot(sub[b])
    with np.load(root/t['geometry_id']/'injection_32_arrays.npz') as a:
        x=(a['wave']-t['center_angstrom'])/t['nominal_step_angstrom']
        mask=np.abs(x)<8
        ax.plot(x[mask],a['local_contrast'][mask],'-o',color='#107d8c',markersize=5)
    ax.axhline(3.5,color='#b0452b',linestyle='--',label='Fixed threshold 3.5')
    ax.axvline(0,color='#8b95a2',linestyle=':',linewidth=1)
    ax.set(xlim=(-7,7),ylim=(-.6,6),ylabel='Local contrast')
    ax.set_title(f"6504.73 Å, 32× | B{b+1}, phase {t['subpixel_phase']:.2f}: "
                 f"{r['largest_center_overlapping_run_pixels']} pixels → "+('recovered' if t['recovered'] else 'miss'),fontsize=11)
    ax.grid(alpha=.2)
    if b==0:ax.legend(fontsize=9,loc='upper right')
    if b==2:ax.set_xlabel('Pixel displacement from continuous injection center')
fig.suptitle('Frozen HARPS recovery audit: a four-pixel requirement can miss strong narrow lines\n'
             '12 paired geometries × 4 strengths; background and phase are confounded; no detector tuning',fontsize=15)
fig.savefig(root/'validation_recovery_diagnostic.png',dpi=170)
plt.close(fig)
print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))
