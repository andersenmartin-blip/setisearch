#!/usr/bin/env python3
"""Verify retained LS4I evidence and produce the report and figure."""
import gzip
import hashlib
import json
import lzma
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from ls4i_measured_digital_injections import encoded, verify_freeze, bilateral_overlap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls4i_measured_digital_injections'


def read_json(name):
    path = OUT/name
    raw = (path.read_bytes() if path.exists() else
           lzma.decompress((OUT/(name+'.xz')).read_bytes()) if (OUT/(name+'.xz')).exists() else
           gzip.decompress((OUT/(name+'.gz')).read_bytes()))
    return json.loads(raw), raw


def verify():
    verify_freeze()
    config = json.loads((ROOT/'config/ls4i_measured_digital_injections.json').read_text())
    result, raw = read_json('injections.json')
    identity = result.pop('result_sha256')
    if hashlib.sha256(encoded(result)).hexdigest() != identity:
        raise ValueError('result identity mismatch')
    result['result_sha256'] = identity
    if result['status'] != 'measured-digital-study-complete':
        raise ValueError('incomplete study')
    if result['freeze_sha256'] != hashlib.sha256((ROOT/'LS4I_FREEZE.sha256').read_bytes()).hexdigest():
        raise ValueError('freeze identity mismatch')
    receipts, _ = read_json('source_receipts.json')
    if len(receipts['sources']) != 4:
        raise ValueError('incomplete source inventory')
    for receipt, expected in zip(receipts['sources'], config['sources']):
        if receipt['label'] != expected['label'] or receipt['product'] != expected['product'] or receipt['source_sha256'] != expected['source_sha256'] or receipt['bytes'] != expected['source_size_bytes'] or not receipt['raw_file_deleted']:
            raise ValueError('source receipt mismatch')
    medium, _ = read_json('A1_medium.json')
    off, _ = read_json('B1_medium.json')
    if not medium['historical_replay_agrees'] or not off['historical_replay_agrees'] or len(medium['trials']) != 36:
        raise ValueError('medium replay/grid failed')
    rows = result['paired_configurations']
    keys = [(r['frequency_index'],r['window_index'],r['pulse_width_s'],r['medium_amplitude'],r['htr_amplitude']) for r in rows]
    if len(keys) != 144 or len(set(keys)) != 144 or len(result['fixed_window_diagnostics']) != 48 or len(result['uninjected_baselines']) != 12:
        raise ValueError('incomplete or duplicate grid')
    for row in rows:
        trial = next(t for t in medium['trials'] if all(t[k] == row[k] for k in ('frequency_index','window_index','pulse_width_s','medium_amplitude')))
        if len(row['events']) != len(trial['matched_events']):
            raise ValueError('Stage-1 handoff count mismatch')
        for event, original in zip(row['events'], trial['matched_events']):
            if event['event_window_s'] != [original['event']['time_start_s'], original['event']['time_stop_s']] or event['stage1_off_survives'] != original['survives_adjacent_off_veto']:
                raise ValueError('detected Stage-1 window/veto was not preserved')
        if row['joint_digital_pass'] != any(e['stage1_off_survives'] and e['truth_associated_pass'] for e in row['events']):
            raise ValueError('paired decision mismatch')
        if row['stage1_matched_count'] != len(row['events']) or row['stage1_survivor_count'] != sum(e['stage1_off_survives'] for e in row['events']):
            raise ValueError('event count mismatch')
        for event in row['events']:
            if event['passed'] != (event['cross_scale_supported'] and not event['off_veto'] and not event['reference_veto']):
                raise ValueError('residual decision mismatch')
            if event['truth_associated_pass'] != (event['passed'] and event['matched_truth_pulses'] >= 3):
                raise ValueError('truth association mismatch')
    archive = OUT/'injections.json.gz'
    if archive.exists():
        if gzip.decompress(archive.read_bytes()) != raw:
            raise ValueError('compressed ledger mismatch')
    else:
        archive.write_bytes(gzip.compress(raw, mtime=0))
    return config, result, medium, receipts


def present(config, result, medium, receipts):
    overlap_audit = []
    for trial in medium['trials']:
        candidates = []
        fragment_intervals = []
        truth = trial['truth']
        for event in trial['search']['events']:
            if event['score'] < 8:
                continue
            tf = bilateral_overlap(event['time_start_s'],event['time_stop_s'],truth['time_start_s'],truth['time_stop_s'])
            ff = bilateral_overlap(event['frequency_start_mhz'],event['frequency_stop_mhz'],truth['frequency_start_mhz'],truth['frequency_stop_mhz'])
            candidates.append({'minimum_overlap_fraction':min(tf,ff),'time_overlap_fraction':tf,'frequency_overlap_fraction':ff,'event':event})
            if tf >= .5 and ff > 0:
                fragment_intervals.append((max(event['frequency_start_mhz'],truth['frequency_start_mhz']), min(event['frequency_stop_mhz'],truth['frequency_stop_mhz'])))
        best = max(candidates,key=lambda e:(e['minimum_overlap_fraction'],e['event']['score']),default=None)
        covered = 0.; endpoint = truth['frequency_start_mhz']
        for lo,hi in sorted(fragment_intervals):
            covered += max(0.,hi-max(lo,endpoint)); endpoint=max(endpoint,hi)
        overlap_audit.append({**{k:trial[k] for k in ('frequency_index','window_index','pulse_width_s','medium_amplitude')},
                              'best_retained_event_overlap':best,'time_aligned_fragment_count':len(fragment_intervals),
                              'descriptive_frequency_union_fraction':covered/(truth['frequency_stop_mhz']-truth['frequency_start_mhz'])})
    (OUT/'stage1_overlap_audit.json').write_bytes(encoded({'role':'post-result descriptive audit; no decision changes','trials':overlap_audit}))
    # An illustrative cell makes narrow-fragment retention visible.
    example = next(t for t in medium['trials'] if t['frequency_index']==0 and t['window_index']==0 and t['pulse_width_s']==.012 and t['medium_amplitude']==16.)
    truth = example['truth']
    fragments = [e for e in example['search']['events'] if e['score']>=8 and
                 bilateral_overlap(e['time_start_s'],e['time_stop_s'],truth['time_start_s'],truth['time_stop_s'])>=.5 and
                 min(e['frequency_stop_mhz'],truth['frequency_stop_mhz'])>max(e['frequency_start_mhz'],truth['frequency_start_mhz'])]
    fragments.sort(key=lambda e:e['frequency_start_mhz'])
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'ls4i-fragments'})
    fig,ax = plt.subplots(figsize=(11,5))
    fig.subplots_adjust(left=.19,right=.95,bottom=.28,top=.73)
    fig.suptitle('A strong injection retained as narrow frequency fragments',x=.05,y=.96,ha='left',fontsize=17,weight='bold')
    fig.text(.05,.86,'8.5 GHz band · 48–80 s envelope · 12 ms pulses · medium digital amplitude 16',fontsize=11)
    ax.barh(0,truth['frequency_stop_mhz']-truth['frequency_start_mhz'],left=truth['frequency_start_mhz'],height=.55,color='#2563eb')
    for i,e in enumerate(fragments,1):
        ax.barh(i,e['frequency_stop_mhz']-e['frequency_start_mhz'],left=e['frequency_start_mhz'],height=.55,color='#0f766e')
    ax.set_yticks(range(len(fragments)+1),['Injected band']+[f"Retained · score {e['score']:.1f}" for e in fragments])
    ax.invert_yaxis();ax.set_xlabel('Frequency (MHz)');ax.ticklabel_format(useOffset=False,axis='x')
    for side in ['top','right','left']:ax.spines[side].set_visible(False)
    fig.text(.05,.11,'Each fragment overlaps at most one quarter of the injected band; the frozen single-event rule requires at least half.',fontsize=11)
    fig.text(.05,.045,'Descriptive audit before OFF veto. Fragments are not merged into a promoted candidate.',fontsize=10,color='#4b5563')
    fig.savefig(OUT/'stage1_fragments.svg',metadata={'Date':None});fig.savefig(OUT/'stage1_fragments.png',dpi=150);plt.close(fig)
    stage = []
    for amplitude in config['medium_amplitudes']:
        trials = [t for t in medium['trials'] if t['medium_amplitude']==amplitude]
        stage.append([sum(bool(t['matched_events']) for t in trials),
                      sum(any(e['survives_adjacent_off_veto'] for e in t['matched_events']) for t in trials)])
    paired = [[sum(r['joint_digital_pass'] for r in result['paired_configurations'] if r['medium_amplitude']==m and r['htr_amplitude']==h)
               for h in config['htr_amplitudes']] for m in config['medium_amplitudes']]
    fixed = [[sum(r['truth_associated_pass'] for r in result['fixed_window_diagnostics'] if r['pulse_width_s']==w and r['htr_amplitude']==a)
              for a in config['htr_amplitudes']] for w in config['pulse_widths_s']]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.hashsalt':'ls4i-v1'})
    fig, axes = plt.subplots(1,3,figsize=(13,5.5))
    fig.subplots_adjust(left=.08,right=.97,top=.69,bottom=.27,wspace=.46)
    fig.suptitle('LS4I · digital injections in measured backgrounds',x=.08,y=.95,ha='left',fontsize=20,weight='bold')
    fig.text(.08,.86,'Same archived A1/B1 scans · separate medium and HTR amplitude axes',fontsize=12)
    descriptions = [
        (stage,12,['Associated','After OFF'],[f'{x:g}' for x in config['medium_amplitudes']], 'Stage 1 · count / 12 cells', 'Medium amplitude'),
        (paired,12,[f'{x:g}' for x in config['htr_amplitudes']],[f'{x:g}' for x in config['medium_amplitudes']], 'Paired digital pass · count / 12', 'Medium amplitude'),
        (fixed,4,[f'{x:g}' for x in config['htr_amplitudes']],[f'{w*1000:g}' for w in config['pulse_widths_s']], 'Fixed-window diagnostic · count / 4', 'Pulse width (ms)')]
    for index,(ax,(values,maximum,xticks,yticks,title,ylabel)) in enumerate(zip(axes,descriptions)):
        ax.imshow(values,cmap='Blues',vmin=0,vmax=maximum,aspect='auto')
        ax.set_xticks(range(len(xticks)),xticks)
        ax.set_yticks(range(len(yticks)),yticks)
        ax.set_title(title,loc='left',pad=12,fontsize=11)
        ax.set_ylabel(ylabel)
        if index: ax.set_xlabel('HTR amplitude')
        for (i,j),v in np.ndenumerate(values):
            ax.text(j,i,str(v),ha='center',va='center',fontsize=14,color='white' if v>maximum/2 else '#172554')
        for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.08,.14,'Medium units: native-channel pre-injection MAD scale. HTR units: collapsed injection-band reference MAD scale.',fontsize=10)
    fig.text(.08,.08,'Reused backgrounds; fixed-window tests bypass Stage 1. These counts are not physical signal completeness or independent trials.',fontsize=10,color='#4b5563')
    fig.savefig(OUT/'digital_recovery.svg',metadata={'Date':None})
    fig.savefig(OUT/'digital_recovery.png',dpi=150)
    plt.close(fig)
    for name in ('digital_recovery.svg', 'stage1_fragments.svg'):
        path = OUT/name
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    joint = sum(r['joint_digital_pass'] for r in result['paired_configurations'])
    baseline = sum(r['joint_pass'] for r in result['uninjected_baselines'])
    fixed_pass = sum(r['truth_associated_pass'] for r in result['fixed_window_diagnostics'])
    diagnostic_support = sum(r['cross_scale_supported'] for r in result['fixed_window_diagnostics'])
    fixed_off = sum(r['off_veto'] for r in result['fixed_window_diagnostics'])
    fixed_ref = sum(r['reference_veto'] for r in result['fixed_window_diagnostics'])
    by_band = []
    for frequency_index, center_mhz in enumerate((8500, 10500)):
        cases = [r for r in result['fixed_window_diagnostics']
                 if r['frequency_index'] == frequency_index and r['htr_amplitude'] > 0]
        by_band.append({'frequency_center_mhz': center_mhz, 'positive_amplitude_cases': len(cases),
                        'truth_associated_passes': sum(r['truth_associated_pass'] for r in cases),
                        'cross_scale_supported': sum(r['cross_scale_supported'] for r in cases),
                        'off_vetoes': sum(r['off_veto'] for r in cases),
                        'reference_vetoes': sum(r['reference_veto'] for r in cases)})
    summary = {'paired_passes':joint,'paired_configurations':144,'uninjected_baseline_passes':baseline,
               'fixed_window_passes':fixed_pass,'fixed_window_cases':48,'fixed_window_supported':diagnostic_support,
               'fixed_window_off_vetoes':fixed_off,'fixed_window_reference_vetoes':fixed_ref,
               'stage1_by_medium_amplitude':dict(zip(map(str,config['medium_amplitudes']),stage)),
               'paired_pass_grid':paired,'fixed_window_pass_grid':fixed,
               'source_bytes_verified':result['source_bytes_verified'],'result_sha256':result['result_sha256']}
    summary['candidate_conditioned_htr_event_evaluations'] = sum(len(r['events']) for r in result['paired_configurations'])
    summary['fixed_window_positive_amplitude_by_band'] = by_band
    (OUT/'summary.json').write_bytes(encoded(summary))
    text=f'''# LS4I: digital injections in measured observations

**Completed measured-background study: 36 Stage-1 interventions and 48 fixed-window HTR diagnostics.**

The four original A1/B1 medium/HTR files were downloaded, verified against
their frozen SHA256 identities and deleted after processing. Total verified
source data: {result['source_bytes_verified']:,} bytes. Both medium baselines
reproduced their historical complete searches within the frozen tolerances.
This experiment uses real archived backgrounds. Its two independently
defined digital amplitude coordinates are not a common physical injection.

![All stage and paired response counts](results_ls4i_measured_digital_injections/digital_recovery.svg)

## Stage-1 selection

Each row includes two frequency bands, two time placements and three pulse
widths. An association must cover half of both the injected and detected
intervals in time and frequency. Full global search competition, clipping,
normalization, retention and the original adjacent-OFF veto were preserved.

| Medium amplitude | Associated Stage-1 event | Survives Stage-1 OFF |
|---:|---:|---:|
'''
    for amplitude,counts in zip(config['medium_amplitudes'],stage):
        text+=f'| {amplitude:g} | {counts[0]}/12 | {counts[1]}/12 |\n'
    text+='''
The following **post-result descriptive audit** counts time-aligned retained
frequency fragments before the OFF veto. Their union is clipped to the
injected band. It is not a replacement association rule or a promoted
candidate, and does not enter the primary totals.

| Medium amplitude | Cells with time-aligned fragments | Median union coverage of injected band |
|---:|---:|---:|
'''
    for amplitude in config['medium_amplitudes']:
        a=[r for r in overlap_audit if r['medium_amplitude']==amplitude]
        text+=f"| {amplitude:g} | {sum(r['time_aligned_fragment_count']>0 for r in a)}/12 | {100*np.median([r['descriptive_frequency_union_fraction'] for r in a]):.1f}% |\n"
    if not any(x[0] for x in stage):
        text+='''
No retained Stage-1 event met the frozen bilateral association rule in any
of the 36 injected searches. Consequently, no candidate-conditioned HTR
event was evaluated: the 144 paired zeros follow from the Stage-1 association
gate and are **not 144 observed HTR rejections**. This does not establish that
the spectra contained no detectable excess. The descriptive overlap audit
retains the closest overlap attainable among retained ON-threshold events;
it neither relaxes the decision threshold nor promotes a missed association.

![A strong injection retained in narrow fragments](results_ls4i_measured_digital_injections/stage1_fragments.svg)

At medium amplitude 16, all 12 cells contain time-aligned retained fragments.
Their union spans approximately 91–100% of the injected band, while each
individual fragment falls short of the required 50% frequency coverage.
The zero primary association count therefore cannot be read as zero ability
to detect these strong digital perturbations. Spectral fragmentation and the
association definition must be qualified together before estimating recovery.
The uninjected Stage-1 baseline has no such time-aligned frequency fragments
in any of the four unique frequency/window placements under this descriptive
audit. This supports attributing the added fragments to the intervention,
without turning them into accepted sky candidates.
'''
    text+=f'''
## Follow-up and controls

The paired endpoint follows every associated Stage-1 event using its detected
time interval and frequency band, with 0.5 MHz padding and corrected HTR
channel-center selection. It requires the same event to survive both Stage-1
OFF and the LS4E truth-associated residual rule. No truth window replaces a
missed Stage-1 event. The result is **{joint}/144** paired digital passes.
The uninjected backgrounds yield {baseline}/12 baseline passes under the
corresponding width-dependent truth associations.

The separately labelled fixed-window HTR diagnostics give {fixed_pass}/48
truth-associated passes and {diagnostic_support}/48 cross-scale-supported
cases before vetoes. OFF vetoes occur in {fixed_off}/48 cases and ON-reference
vetoes in {fixed_ref}/48. Veto counts can overlap. These fixed-window cases
bypass Stage 1 and do not enter the paired-pass total.

Excluding the 12 zero-amplitude cases gives {fixed_pass}/36 passes. The
positive-amplitude cases separate sharply by the two fixed frequency bands:

| Band center | Truth-associated pass | Cross-scale support before vetoes | OFF veto | ON-reference veto |
|---:|---:|---:|---:|---:|
'''
    for band in by_band:
        n = band['positive_amplitude_cases']
        text += f"| {band['frequency_center_mhz']/1000:g} GHz | {band['truth_associated_passes']}/{n} | {band['cross_scale_supported']}/{n} | {band['off_vetoes']}/{n} | {band['reference_vetoes']}/{n} |\n"
    text+=f'''
At 8.5 GHz, every positive-amplitude case is vetoed by the reused OFF
background even though 17 of 18 have pulse support. At 10.5 GHz, 17 of 18
pass. These are conditional diagnostic counts on the same two scans, not
independent detections or evidence that either whole frequency band is clean.

The complete derived ledger retains both control flags, pulse counts,
truth associations, selected event windows, extraction indices, amplitude
normalizations and channel-dilution fractions. The compressed medium records
retain every searched event for each injection, including unrelated events.

## What the amplitudes mean

The common analytic shape has a 32 s envelope of height 0.1 and six separated
pulses of added height 1, with widths 3, 12 or 100 ms. Bin averages account
for fractional integration boundaries. In medium data the scale is each
native channel's unmodified full-scan robust MAD scale; injection precedes
normalization and clipping. The medium levels are 1, 4 and 16.

HTR levels 0, 4, 8 and 16 use the collapsed injection band's unmodified
outside-envelope reference MAD scale. Adding that digital level uniformly
to selected native channels is evaluated through linear band averaging,
including dilution into wider extraction bands. Archived byte values are
promoted to floating point; the perturbation is not re-quantized or clipped.
This specifies a software intervention after the original conversion.
Equal numerical amplitudes in the two products do not mean equal physical
power, and marginal recovery fractions must not be multiplied.

## Scope and next decision

These are deterministic cells on reused A1/B1 backgrounds. Zero-amplitude
cases repeat backgrounds under different truth-association widths; neither
they nor the other cells are independent observation trials. The data were
not chosen by scanning for clean noise. No physical flux limit, astronomical
completeness, calibrated false-alarm probability, independent confirmation
or general light-sail exclusion follows. Prior LS4F dispositions are unchanged.

The reserved A3/C1/D1 data remain unopened by this study. Any revised detector
must be qualified separately before those files are used for validation.
The LS4H physical amplitude-transfer limitation remains unresolved; this
separately labelled digital study does not remove it.

The next methodological step is a separately specified and qualified
fragment-association or event-retention rule, followed by HTR evaluation
using the resulting selected events. This report does not merge fragments
or revise any frozen LS4I decision.

## Reproduction and validation

All **52 relevant unit tests passed** before the source/configuration freeze
in local commit `030aa62` and before LS4I spectral access. The optimized
native-preprocessing cache was checked against full native recomputation,
including injected cases; the detector module itself was not modified.
Both real medium scans also passed historical full-search replay. Source
receipts, result identity, grid cardinalities and decision logic were verified.
The plan was frozen locally before execution, not publicly preregistered.

```bash
sha256sum -c LS4I_FREEZE.sha256
sha256sum -c RESULTS_MANIFEST_LS4I.sha256
PYTHONPATH=src:scripts python scripts/ls4i_result_summary.py
```

The summary script can verify the lossless compressed injection ledger
directly, without telescope access. The original runtime refuses to overwrite
an existing result directory; preserve it before any new raw-data repeat.
No scan arrays or raw spectra are published.

Runtime: Python {result['python_version']}, NumPy {result['numpy_version']}.
Result identity: `{result['result_sha256']}`.
'''
    (ROOT/'LS4I_MEASURED_DIGITAL_INJECTION_RESULT.md').write_text(text)
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    present(*verify())
