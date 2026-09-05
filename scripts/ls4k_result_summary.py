#!/usr/bin/env python3
"""Verify synthetic policy evidence and render all eight scenario families."""
import gzip
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from ls4k_off_policy_counterexamples import ROOT,OUT,CLONES,configuration,decisions
from ls4g_synthetic_recovery import encoded,verify_manifest

LABELS={'signal_clean':'Injected train · quiet OFF','signal_smooth_off':'Injected train · smooth OFF',
'signal_pulsed_off':'Injected train · OFF pulse','signal_reference_pulse':'Injected train · reference pulse',
'null_smooth_off':'Plateau only · smooth OFF','isolated_on_smooth_off':'Single ON pulse · smooth OFF',
'rfi_clone_clean':'RFI clone · quiet OFF','rfi_clone_smooth_off':'RFI clone · smooth OFF'}


def main():
    verify_manifest(ROOT/'LS4K_FREEZE.sha256');config=configuration()
    summary=json.loads((OUT/'summary.json').read_text());identity=summary.pop('result_sha256')
    assert hashlib.sha256(encoded(summary)).hexdigest()==identity
    assert summary['freeze_sha256']==hashlib.sha256((ROOT/'LS4K_FREEZE.sha256').read_bytes()).hexdigest()
    raw=gzip.decompress((OUT/'scenarios.jsonl.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==summary['ledger_sha256']
    rows=[json.loads(line) for line in raw.splitlines()]
    keys=('family','background','width_s','amplitude_sigma','seed')
    index={tuple(r[k] for k in keys):r for r in rows}
    assert len(index)==len(rows)==summary['scenario_rows']==1152
    assert len({r['waveform_sha256'] for r in rows})==summary['distinct_waveform_pairs']==736
    for r in rows:
        for k,v in decisions(r['stage1_off_survives'],r).items():assert r[k]==v
        assert r['passed']==(r['supported'] and not r['off_veto'] and not r['reference_veto'])
        assert r['recovered']==(r['passed'] and r['matched_truth_pulses']>=3)
        if r['family'] in CLONES:
            counterpart=index[(CLONES[r['family']],r['background'],r['width_s'],r['amplitude_sigma'],r['seed'])]
            assert {k:v for k,v in r.items() if k not in ('cell','family')}=={k:v for k,v in counterpart.items() if k not in ('cell','family')}
    for total in summary['families']:
        subset=[r for r in rows if r['family']==total['family']]
        assert len(subset)==total['scenario_rows']==144
        for k,v in total.items():
            if k not in ('family','scenario_rows'):assert sum(r[k] for r in subset)==v
    table=[]
    for background in config['backgrounds']:
        for width in config['widths_s']:
            for amplitude in config['amplitudes_sigma']:
                subset=[r for r in rows if r['family']=='signal_smooth_off' and r['background']==background and r['width_s']==width and r['amplitude_sigma']==amplitude]
                table.append({'background':background,'width_s':width,'amplitude_sigma':amplitude,'rows':len(subset),'diagnostic_recoveries':sum(r['diagnostic_truth_recovery'] for r in subset)})
    (OUT/'recovery_grid.json').write_bytes(encoded({'role':'conditional smooth-OFF synthetic waveform recovery, not physical completeness','cells':table}))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'ls4k-v1'})
    fig,ax=plt.subplots(figsize=(11.8,7.6))
    fig.subplots_adjust(left=.36,right=.93,top=.77,bottom=.21)
    fig.suptitle('LS4K · diagnostic access is not origin identification',x=.055,y=.95,ha='left',weight='bold',fontsize=18)
    fig.text(.055,.875,'Counts per 144 labelled scenarios · same LS4E pulse diagnostic in both columns',fontsize=12)
    values=np.array([[r['current_gate_pass'],r['diagnostic_admission']] for r in summary['families']])
    ax.imshow(values,cmap='Blues',vmin=0,vmax=144,aspect='auto')
    ax.set_xticks([0,1],['Current gate + pulse rule','Diagnostic path; veto retained'])
    ax.xaxis.tick_top();ax.tick_params(axis='x',labelsize=10,pad=9)
    ax.set_yticks(range(8),[LABELS[r['family']] for r in summary['families']])
    for (i,j),v in np.ndenumerate(values):ax.text(j,i,str(v),ha='center',va='center',fontsize=15,color='white' if v>72 else '#172554')
    for spine in ax.spines.values():spine.set_visible(False)
    ax.axhline(5.5,color='#9a3412',lw=2)
    for label in ax.get_yticklabels()[-2:]:label.set_color('#9a3412')
    fig.text(.055,.125,'RFI rows deliberately copy the signal inputs exactly. Identical observed data receive identical decisions.',fontsize=11)
    fig.text(.055,.065,'Stipulated Stage-1 events + synthetic collapsed vectors; no medium search, physical transfer or new sky candidate.',fontsize=10,color='#4b5563')
    fig.savefig(OUT/'policy_comparison.svg',metadata={'Date':None});fig.savefig(OUT/'policy_comparison.png',dpi=150);plt.close(fig)
    p=OUT/'policy_comparison.svg';p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
    text='''# LS4K: OFF-gate deferral exposes both recovery and an origin ambiguity

**Completed: 1,152 labelled synthetic scenarios, representing 736 distinct
waveform pairs and 736 residual evaluations. All 66 relevant tests passed.**

An additional diagnostic path recovers 109/144 injected trains behind a
smooth OFF feature, while the existing Stage-1 gate admits none of them.
It rejects every tested OFF-pulse, ON-reference-pulse, plateau-only and
single-pulse case. However, an exactly identical ON-only interference
counterexample gets the same 109/144 admissions. This supports investigating
a **veto-preserving diagnostic queue**, not automatic scientific acceptance
or an origin classifier. The operational OFF veto remains unchanged.

![All scenario families under the two policies](results_ls4k_off_policy/policy_comparison.svg)

## What was actually evaluated

The actual original Stage-1 veto receives **stipulated retained-event inputs**:
a score-12 ON event, with either no OFF event or a frequency-overlapping
score-10 OFF event. These records are not generated by a medium-resolution
search. Independently specified synthetic collapsed vectors are evaluated
with unchanged LS4E detrending, pulse-bank, truth matching and control vetoes.
No radio spectra or reserved observations were accessed.

Each vector is 120 s long at 1 ms sampling. The grid includes white and
AR(1), rho 0.8 noise, eight seeds, three pulse widths (3/12/100 ms) and three
pulse heights (4/8/16 noise-standard-deviation units). A smooth OFF case uses
a Gaussian bump of height 8, center 60 s and sigma 20 s. A pulsed control
adds one 12 ms, height-16 pulse to OFF or the ON-reference region.

The paired inputs are a conditional policy experiment, **not a physically
consistent joint instrument simulation**. There is no common calibrated
medium/HTR amplitude transfer or end-to-end search completeness measurement.

## Complete outcomes

“Current pass” requires the original Stage-1 OFF gate and the LS4E pulse rule.
“Diagnostic admission” evaluates the same pulse rule while keeping the
Stage-1 rejection attached. Neither column establishes a source's origin;
no diagnostic admission was promoted to a sky candidate.

| Scenario | Labelled rows | Current pass | Diagnostic admission |
|---|---:|---:|---:|
'''
    for r in summary['families']:
        text+=f"| {LABELS[r['family']]} | {r['scenario_rows']} | {r['current_gate_pass']} | {r['diagnostic_admission']} |\n"
    text+='''
Every admitted six-pulse case also matches at least three of its injected
pulses at two supporting scales. The two pulsed-control families still have
109/144 supported ON trains before vetoes, but all 144 OFF-pulse cases trigger
the OFF pulse veto and all 144 reference-pulse cases trigger the reference
veto. Thus the extra diagnostic route does not bypass those pulse controls.
The [complete recovery grid](results_ls4k_off_policy/recovery_grid.json) retains
all width, amplitude and noise combinations; no low-recovery cells are omitted.

## What the counterexamples establish

The two RFI families reuse the signal families' exact waveforms, noise,
truth annotations and Stage-1 evidence. Their hypothetical causal label is
ON-only local pulsed interference. Byte-level input hashes and all decision
fields were verified identical for every paired case. These are constructed
counterexamples, not observed RFI populations or independent trials.

With quiet OFF, both policies already admit 109/144 signal-labelled cases
and their 109/144 interference clones. With smooth OFF, diagnostic access
restores the same count for both causal labels. A rule supplied identical
observables cannot distinguish those labels. The existing veto removes both
in the smooth-OFF condition; it does not solve the quiet-OFF ambiguity either.

This does not measure the prevalence of real ON-only interference. It also
does not identify the 11 real OFF features seen in LS4J as smooth Gaussian
bumps: their morphology remains an empirical question. Zero admissions in
the other synthetic negative families cannot establish a false-alarm rate.

## Concrete next step

A separately frozen measured-data diagnostic can follow the 64 LS4J-associated,
Stage-1-vetoed fragments through HTR using their actual event windows and
frequency selections. Keep every original OFF veto and sky disposition;
record pulse support, OFF/reference vetoes and truth-associated recovery in
a review-only ledger. This would test whether the synthetic smooth-OFF
opportunity exists in the archived A1/B1 backgrounds without treating a
relaxed gate as an accepted candidate. It is not executed in LS4K.

The reserved A3/C1/D1 data remain unopened. LS4F candidate dispositions and
LS4I/LS4J endpoints are unchanged. No physical transfer, survey completeness,
independent confirmation, or technosignature is claimed.

## Freeze and reproduction

Plan, configuration, code, tests and dependencies were frozen locally at
`d09fc55` and published at `916835b08fc3330427689f179928b08ceda7746b` before
numerical scenario execution. All 1,152 rows are preserved in a lossless
compressed ledger. Matched backgrounds, identical RFI copies and repeated
null labels make the rows dependent; they are not 1,152 independent trials.

```bash
sha256sum -c LS4K_FREEZE.sha256
sha256sum -c RESULTS_MANIFEST_LS4K.sha256
PYTHONPATH=src:scripts python scripts/ls4k_result_summary.py
```

The summary verifies the canonical result and ledger hashes, all grid keys,
all clone comparisons, all family totals and both policy decisions. The
frozen runner refuses to overwrite an existing results directory; preserve
it or use a separate checkout before a complete synthetic repeat.
'''
    text+=f"\nRuntime: Python {summary['python_version']}, NumPy {summary['numpy_version']}.\nResult identity: `{identity}`.\n"
    (ROOT/'LS4K_OFF_POLICY_RESULT.md').write_text(text)
    print(f'Verified {len(rows)} rows, {summary["distinct_waveform_pairs"]} waveform pairs and all clone identities.')

if __name__=='__main__':main()
