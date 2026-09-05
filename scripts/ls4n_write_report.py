#!/usr/bin/env python3
"""Render verified LS4N evidence without rerunning synthetic or spectral data."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from ls4n_reference_policy import ROOT,OUT,load
from ls4n_result_summary import main as write_summary,verified

LABELS={
 'train_clean':'ON train · quiet OFF',
 'train_off_inside':'ON train · inside OFF pulse',
 'train_off_reference_early':'ON train · early OFF reference',
 'train_off_reference_late':'ON train · late OFF reference',
 'train_on_reference':'ON train · ON reference pulse',
 'null_off_reference':'Plateau only · OFF reference',
 'single_off_reference':'Single ON pulse · OFF reference',
 'rfi_clone_reference_early':'RFI clone · early OFF reference',
 'rfi_clone_reference_late':'RFI clone · late OFF reference'}


def main():
    write_summary();summary,mr,synthetic=verified()
    families={r['family']:r for r in summary['synthetic_families']}
    plt.rcParams.update({'font.size':10,'svg.hashsalt':'ls4n-reference-policy-v1'})
    fig,axes=plt.subplots(1,2,figsize=(15,7),gridspec_kw={'width_ratios':[1,1.5]})
    fig.subplots_adjust(left=.09,right=.97,bottom=.23,top=.78,wspace=1.05)
    fig.suptitle('LS4N · recovery gained by separating reference-only OFF activity',fontsize=17,x=.05,ha='left',y=.96)
    fig.text(.05,.88,'Retrospective diagnostic comparison; original Stage-1 vetoes and sky decisions are preserved.',fontsize=11)
    ax=axes[0];y=np.arange(2)
    old=[b['original_truth_pass_configurations'] for b in summary['measured_bands']]
    new=[b['counterfactual_truth_pass_configurations'] for b in summary['measured_bands']]
    ax.barh(y-.18,old,height=.32,color='#64748b',label='Original HTR diagnostic')
    ax.barh(y+.18,new,height=.32,color='#0e7490',label='Reference-only counterfactual')
    for values,offset in ((old,-.18),(new,.18)):
        for i,value in enumerate(values):ax.text(value+1,i+offset,str(value),va='center')
    ax.set_yticks(y,['8.5 GHz','10.5 GHz']);ax.invert_yaxis();ax.set_xlim(0,72)
    ax.set_title('Measured backgrounds\nTruth-recovery configurations / 72 per band',fontsize=11,pad=15)
    ax.set_xlabel('Passing configurations, complete grid')
    ax.legend(loc='upper left',bbox_to_anchor=(-.15,-.13),frameon=False,fontsize=9)
    ax=axes[1];order=list(LABELS);y=np.arange(len(order))
    old=[families[f]['original_htr_pass'] for f in order];new=[families[f]['counterfactual_htr_pass'] for f in order]
    ax.barh(y-.18,old,height=.32,color='#64748b')
    ax.barh(y+.18,new,height=.32,color=['#b45309' if f.startswith('rfi_') else '#0e7490' for f in order])
    for values,offset in ((old,-.18),(new,.18)):
        for i,value in enumerate(values):ax.text(value+2,i+offset,str(value),va='center',fontsize=9)
    ax.set_yticks(y,[LABELS[f] for f in order]);ax.invert_yaxis();ax.set_xlim(0,150)
    ax.set_title('Constructed controls\nHTR diagnostic admissions / 144 labels per family',fontsize=11,pad=15)
    ax.set_xlabel('Admitted labelled cases')
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
        ax.xaxis.grid(True,alpha=.15);ax.set_axisbelow(True)
    fig.text(.05,.07,'Orange rows are exact causal-label copies, not independent observations or an empirical RFI rate.',fontsize=11,color='#92400e')
    fig.savefig(OUT/'policy_comparison.svg',metadata={'Date':None})
    fig.savefig(OUT/'policy_comparison.png',dpi=150);plt.close(fig)
    svg=OUT/'policy_comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    grid=load('results_ls4n_reference_policy/recovery_grid.json')['measured']
    lines=['# LS4N: reference-only OFF diagnostics recover injections and admit origin clones','',
        '**Completed: all 144 LS4L configurations and 256 selected-fragment evaluations reclassified diagnostically; 1,296 labelled synthetic scenarios completed, representing 880 distinct waveform pairs and 880 residual evaluations. All 66 relevant tests passed. No new radio spectra were read.**','',
        'Separating reference-only OFF activity increases measured truth-associated HTR diagnostic recovery from **15/144 to 47/144** configurations. The additional **32** configurations are all at 8.5 GHz. Original Stage-1 vetoes remain attached, so original joint passes and promoted sky candidates remain **zero**.','',
        '![Measured recovery and constructed interference counterexamples](results_ls4n_reference_policy/policy_comparison.svg)','',
        '## Exact diagnostic comparison','',
        'The original HTR diagnostic requires cross-scale ON pulse support, no ON-reference pulse and no OFF pulse anywhere in the inside/reference regions. The counterfactual keeps the support requirement, ON-reference veto and inside-OFF veto, while recording reference-only OFF activity separately. Truth recovery requires at least three of the same injected pulses at two supporting scales. This is a separately frozen retrospective diagnostic study; the operational rule was not edited.','',
        'LS4M OFF morphology was joined to the original LS4L event records. All 256 selected-fragment and 48 fixed-window OFF count/veto comparisons reproduce their original values before the policy comparison. No pulse is newly detected, associated, widened or merged.','',
        'Inside and reference regions are defined in time relative to each scan. A1 and B1 are separate pointings observed at different times; reference-only OFF activity is not evidence that interference was absent during the ON observation.','',
        '## Measured-background outcomes','',
        '| Group | Original HTR truth passes / full grid | Counterfactual / full grid | Counterfactual / selected positive configurations | Zero-level fragment truth passes |',
        '|---|---:|---:|---:|---:|']
    for b in summary['measured_bands']:
        lines.append(f"| {b['band_ghz']} GHz | {b['original_truth_pass_configurations']}/{b['full_grid_configurations']} | {b['counterfactual_truth_pass_configurations']}/{b['full_grid_configurations']} | {b['counterfactual_positive_selected_passes']}/{b['selected_positive_configurations']} | {b['zero_counterfactual_truth_passes']}/{b['zero_fragment_evaluations']} |")
    lines += ['', 'All 47 counterfactual truth-passing configurations contain a passing fragment absent at its own zero-HTR comparison. The 64 zero-level fragment evaluations have zero counterfactual pulse admissions and zero truth recoveries. These comparisons condition on previously injected medium selection and reused A1/B1 backgrounds; they are not complete-pipeline false-alarm trials. Medium and HTR amplitudes remain separate digital units, not a calibrated physical signal strength.','',
        'Each cell below contains six configurations: two time placements and three pulse widths. Entries are counterfactual truth recoveries, with empty selections retained in the denominator.','',
        '| Group | Medium amplitude | HTR 0 | HTR 4 | HTR 8 | HTR 16 |',
        '|---|---:|---:|---:|---:|---:|']
    for band in (8.5,10.5):
        for medium in (1.,4.,16.):
            rows=[r for r in grid if r['band_ghz']==band and r['medium_amplitude']==medium]
            lines.append(f'| {band} GHz | {medium:g} | '+' | '.join(f"{r['counterfactual_truth_passes']}/6" for r in rows)+' |')
    lines += ['', '## Complete synthetic controls','',
        'Each family has 144 labelled rows: eight seeds, white and AR(1) rho 0.8 noise, three ON widths (3/12/100 ms) and amplitudes (4/8/16 sigma). Vectors last 120 s at 1 ms sampling; the ON envelope is 30–70 s. A 12 ms, height-16 control pulse is placed at 50.25 s inside, 15.25 s in the early reference or 105.25 s in the late reference. The original LS4E residual processor and thresholds are unchanged. Unlike LS4K, these cases do not add a smooth OFF bump.','',
        '| Family | Labelled rows | Original HTR admission | Counterfactual HTR admission | Counterfactual truth recovery |',
        '|---|---:|---:|---:|---:|']
    for family,label in LABELS.items():
        f=families[family]
        lines.append(f"| {label} | {f['labelled_rows']} | {f['original_htr_pass']} | {f['counterfactual_htr_pass']} | {f['counterfactual_truth_pass']} |")
    lines += ['', 'The alternative admits **111/144** trains for both early and late OFF-reference pulses, matching quiet-OFF recovery. It still rejects every tested inside-OFF-pulse, ON-reference-pulse, plateau-only and single-ON-pulse case. All admitted train cases meet the same truth-association requirement. The complete width/amplitude/background grid is retained in `recovery_grid.json`; unsuccessful cells are not omitted.','',
        'Both explicit ON-only interference clone families also receive **111/144** admissions. Their waveforms, truth annotations and decisions are exactly identical to their signal-labelled counterparts; every pair was verified. These are constructed causal counterexamples, not observed interference or independent trials. They show that the diagnostic inputs cannot resolve origin, not that 111/144 real interference signals would be accepted.','',
        '## Decision and next boundary','',
        'Reference-only OFF activity is a useful separate diagnostic category: it explains a substantial conditional injection-recovery loss in the existing lower-band backgrounds. The current evidence does **not** justify promoting those diagnostics into scientific candidates. The interference clones retain the same ambiguity as the recovered injections, and the original Stage-1 rejection remains unresolved.','',
        'The next useful investigation should seek independent discriminating evidence, such as a preregistered repeatability or beam/pointing consistency test, before considering a change in acceptance. Its feasibility and development/validation split should be established before opening reserved observations. Repeating threshold relaxations on these same backgrounds would not supply independent confirmation.','',
        'No operational veto, LS4F disposition or LS4I/LS4J/LS4L endpoint changed. A3/C1/D1 remain unopened. There is no new sky candidate, calibrated physical sensitivity, survey completeness, false-alarm probability or technosignature claim.','',
        '## Freeze, checkpoints and reproduction','',
        'Plan, configuration, implementation, tests and dependency/input identities were frozen locally at `dc95afd` and published at `598a99c62323db1b694cd02e0cda9cfc47099eb0` before the full numerical study. The measured ledger was saved first; synthetic progress was flushed and checkpointed after every seed. Final ledgers are losslessly compressed. Repeated backgrounds, null labels and causal clones make the labelled rows dependent.','',
        f"Result identity: `{summary['result_sha256']}`. Runtime: Python {summary['python_version']}, NumPy {summary['numpy_version']}.",'',
        '```bash','sha256sum -c LS4N_FREEZE.sha256','sha256sum -c RESULTS_MANIFEST_LS4N.sha256',
        'PYTHONPATH=src:scripts python scripts/ls4n_result_summary.py',
        'PYTHONPATH=src:scripts python scripts/ls4n_write_report.py','```','',
        'The verifier rechecks input hashes, all measured joins and original decisions, complete synthetic keys, every policy decision, all clone equivalences, waveform counts, ledger checkpoints and aggregate results. These commands need only retained derived evidence. The numerical runner refuses an existing output directory.','']
    (ROOT/'LS4N_REFERENCE_POLICY_RESULT.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
