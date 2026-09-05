#!/usr/bin/env python3
"""Verify LS4J accounting and retain the exact OFF events behind every veto."""
import hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from ls4j_fragment_association import ROOT, OUT, load, verify, fragment_associated
from ls4i_measured_digital_injections import encoded, associated
from seti_repeater.light_sail import frequency_overlap_fraction


def main():
    config=verify()
    result=load('results_ls4j_fragment_association/stage1.json.gz')
    identity=result.pop('result_sha256')
    assert hashlib.sha256(encoded(result)).hexdigest()==identity
    assert result['freeze_sha256']==hashlib.sha256((ROOT/'LS4J_FREEZE.sha256').read_bytes()).hexdigest()
    summary=load('results_ls4j_fragment_association/summary.json')
    assert identity==summary['stage1_result_sha256']
    assert len(result['trials'])==36 and len(result['baselines'])==12
    a=load('results_ls4i_measured_digital_injections/A1_medium.json.xz')
    b=load('results_ls4i_measured_digital_injections/B1_medium.json.xz')['baseline_search']['events']
    old=load('config/ls4b_lhs1140_x_light_sail.json')['medium_resolution_screen']
    trace,off_catalog=[],{}
    for ti,t in enumerate(result['trials']):
        original=a['trials'][ti]
        assert all(t[k]==original[k] for k in ('frequency_index','window_index','pulse_width_s','medium_amplitude','truth'))
        assert t['legacy_match_count']==len(original['matched_events'])==0
        assert len(t['decoy_controls'])==5
        for mi,m in enumerate(t['matched_events']):
            event=m['event']
            assert event in original['search']['events'] and event['score']>=old['on_score_threshold']
            assert fragment_associated(event,t['truth'],config['base_bin_width_mhz'],config['association_threshold'])
            assert not associated(event,t['truth'],.5)
            vetoes=[]; indices=[]
            for oi,off in enumerate(b):
                fraction=frequency_overlap_fraction(event,off)
                if off['score']>=old['off_veto_score_threshold'] and fraction>=old['off_veto_frequency_overlap']:
                    vetoes.append({'off_label':'B1','off_score':off['score'],'frequency_overlap_fraction':fraction})
                    indices.append(oi)
                    row=off_catalog.setdefault(oi,{'source_event_index':oi,'event':off,'matched_fragment_uses':0,'frequency_index':t['frequency_index']})
                    row['matched_fragment_uses']+=1
            assert vetoes==m['adjacent_off_vetoes']
            assert m['survives_adjacent_off_veto']==(not vetoes)
            trace.append({'trial_index':ti,'matched_event_index':mi,'B1_source_event_indices':indices})
    assert sum(bool(t['matched_events']) for t in result['trials'])==summary['matched_cells']
    assert len(trace)==summary['matched_events']==64
    assert len(off_catalog)==11 and sum(len(t['B1_source_event_indices']) for t in trace)==136
    assert sum(m['survives_adjacent_off_veto'] for t in result['trials'] for m in t['matched_events'])==summary['surviving_events']==0
    assert summary['followup_status']=='not-run-no-stage1-survivors'
    assert summary['paired_passes']==summary['candidate_conditioned_htr_evaluations']==summary['new_spectral_bytes_read']==0
    assert all(not t['matched_events'] for t in result['baselines'])
    assert all(not c['matched_event_indices'] and c['survivor_count']==0 for t in result['trials']+result['baselines'] for c in t['decoy_controls'])
    audit={'role':'post-result descriptive trace; unchanged frequency-only OFF veto',
           'source':'results_ls4i_measured_digital_injections/B1_medium.json.xz',
           'source_event_index_is_zero_based':True,'links':trace,'off_events':list(off_catalog.values())}
    (OUT/'off_veto_trace.json').write_bytes(encoded(audit))
    rows=[]
    for fi,center in enumerate(config['frequency_centers_mhz']):
        for amplitude in config['medium_amplitudes']:
            trials=[t for t in result['trials'] if t['frequency_index']==fi and t['medium_amplitude']==amplitude]
            matches=[m for t in trials for m in t['matched_events']]
            rows.append({'frequency_center_mhz':center,'medium_amplitude':amplitude,'cells':len(trials),
                         'associated_cells':sum(bool(t['matched_events']) for t in trials),'associated_events':len(matches),
                         'surviving_cells':sum(any(m['survives_adjacent_off_veto'] for m in t['matched_events']) for t in trials)})
    (OUT/'accounting.json').write_bytes(encoded({'rows':rows,'injected_decoy_regions':180,'injected_decoy_matches':0,
         'baseline_truth_labels':12,'unique_baseline_truths':4,'baseline_control_labels':60,'unique_baseline_controls':20,
         'baseline_matches':0,'unique_off_events':len(off_catalog),'total_off_event_links':sum(len(t['B1_source_event_indices']) for t in trace)}))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'ls4j-v1'})
    fig,axes=plt.subplots(1,2,figsize=(10.5,5.4))
    fig.subplots_adjust(left=.10,right=.94,top=.70,bottom=.29,wspace=.38)
    fig.suptitle('LS4J · fragments recovered, then vetoed by OFF',x=.08,y=.94,ha='left',weight='bold',fontsize=18)
    fig.text(.08,.84,'Same 36 LS4I interventions · new fragment-local association · unchanged search and veto',fontsize=11)
    for ax,key,title in zip(axes,('associated_cells','surviving_cells'),('Fragment-associated · count / 6','After Stage-1 OFF · count / 6')):
        values=np.array([r[key] for r in rows]).reshape(2,3)
        ax.imshow(values,cmap='Blues',vmin=0,vmax=6,aspect='auto')
        ax.set_xticks([0,1,2],['1','4','16']);ax.set_yticks([0,1],['8.5 GHz','10.5 GHz'])
        ax.set_xlabel('Medium digital amplitude');ax.set_title(title,loc='left',pad=12,fontsize=12)
        for (i,j),v in np.ndenumerate(values):ax.text(j,i,str(v),ha='center',va='center',color='white' if v>3 else '#172554',fontsize=18)
        for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.08,.15,'18/36 cells associated · all 64 associated fragments vetoed · 0/180 displaced-control matches',fontsize=11)
    fig.text(.08,.08,'No HTR evaluation was needed. Reused development data; no physical completeness or sky detection.',fontsize=10,color='#4b5563')
    fig.savefig(OUT/'fragment_recovery.svg',metadata={'Date':None});fig.savefig(OUT/'fragment_recovery.png',dpi=150);plt.close(fig)
    p=OUT/'fragment_recovery.svg';p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n')
    text='''# LS4J: fragment-local recovery and the Stage-1 OFF boundary

**Completed: 18/36 injected cases associate under the qualified fragment-local
rule; all 64 associated fragments are vetoed by the unchanged Stage-1 OFF
control. No selected-event HTR evaluation or new spectral download was needed.**

The rule and all 60 relevant tests were frozen locally in `2875715` and
published in `a02ad75dc3af5cbb6dc026b2c0627e6578a8a8c4` before reclassification.
This is a development amendment informed by LS4I's known fragmentation,
not an independent validation or retroactive change to LS4I's result.

![Fragment association before and after the unchanged OFF veto](results_ls4j_fragment_association/fragment_recovery.svg)

## What changed

An event may now associate with a resolved portion of the injected band.
Time overlap still covers at least 50% of both intervals. Frequency overlap
must cover at least half of the detected event and at least half the smaller
of the injected bandwidth and the detector's 2.9296875 MHz nominal base bin.
This rejects tiny slivers and very broad unrelated events. It does not claim
recovery of the complete injected bandwidth. No events are merged or widened.

The original score thresholds, global search, event retention, OFF veto and
HTR diagnostic remain unchanged. All previous LS4I associations were replayed
exactly, and the complete retained inputs checked against frozen hashes.
The archived medium searches already contain the original native-preprocessing
injections, so reclassification needs no new medium spectral access.

## All injected cases

Each row contains two time placements and three pulse widths. Digital
amplitude is measured in the LS4I native-channel unmodified MAD scale;
it is neither a physical flux unit nor a calibrated Gaussian significance.

| Band center | Medium amplitude | Associated cases | Associated fragments | Cases surviving OFF |
|---:|---:|---:|---:|---:|
'''
    for r in rows:
        text+=f"| {r['frequency_center_mhz']/1000:g} GHz | {r['medium_amplitude']:g} | {r['associated_cells']}/6 | {r['associated_events']} | {r['surviving_cells']}/6 |\n"
    text+='''
At amplitude 16, all 12 cases now associate. Amplitude 4 associates in all
six 8.5 GHz cases and none of the six 10.5 GHz cases. Amplitude 1 has no
associations. These are repeated interventions on the same background;
the fractions are descriptive, not independent Bernoulli trials.

The 180 deliberately displaced control regions have **zero associations**.
The uninjected baseline also has zero associations in its four unique truth
placements and twenty unique control placements (12 and 60 width-labelled
records). Controls are reused and were specified after LS4I, so their zeros
do not establish a calibrated false-alarm probability.

## What actually triggers the veto

The unchanged Stage-1 rule looks for frequency overlap with any retained
B1 OFF event at score 6 or higher; it does not require an OFF pulse train or matching
relative scan time. Every one of the 64 recovered fragments meets that veto.
The exact trace links them to 11 distinct retained OFF events, with 136
fragment-to-OFF links in total. Several links reuse the same OFF feature.

| OFF band | Distinct OFF events | Endpoint bandwidth | Score range | Relative interval in B1 |
|---|---:|---:|---:|---|
'''
    for fi in (0,1):
        events=[v['event'] for v in off_catalog.values() if v['frequency_index']==fi]
        widths=[e['frequency_stop_mhz']-e['frequency_start_mhz'] for e in events]
        text+=f"| {config['frequency_centers_mhz'][fi]/1000:g} GHz | {len(events)} | {min(widths):.3f} MHz | {min(e['score'] for e in events):.2f}–{max(e['score'] for e in events):.2f} | {min(e['time_start_s'] for e in events):.2f}–{max(e['time_stop_s'] for e in events):.2f} s |\n"
    text+='''
These are roughly 64.4 s OFF boxes. B1 times are measured from B1's own scan
start, not simultaneous with A1. No physical cause for these background
features is established by this accounting. The complete source events and
all links are retained in the [OFF trace](results_ls4j_fragment_association/off_veto_trace.json).

LS4I's 17/18 positive-amplitude fixed-window HTR passes at 10.5 GHz cannot
rescue these events: that diagnostic bypassed Stage 1. Stage-1 frequency
screening and the later HTR pulse-control veto ask different questions.
Here the Stage-1 gate already rejects every associated event, so **0/144
paired configurations can pass**, with **zero actual HTR event evaluations**.
This is a logical consequence of the unchanged gate, not 144 measured HTR
rejections. The predeclared conditional-download rule avoided rereading
18.87 GB of HTR products whose evaluation could not change the conjunction.

## Next methodological decision

The new association rule resolves the accounting failure for strong test
injections, but it has only development qualification. The remaining loss
is now attributable to the deliberately conservative Stage-1 OFF veto on
these frequency regions. A subsequent study should qualify the specificity
and injected-signal losses of that veto against explicit RFI/continuum and
pulse-train counterexamples before changing it. The present report neither
weakens the veto nor promotes a rejected event to a sky candidate.

A3/C1/D1 remain unopened. LS4F's sky-candidate dispositions and LS4I's original
endpoint remain unchanged. No physical amplitude transfer, survey completeness,
independent confirmation, or technosignature is established.

## Reproduce from retained evidence

```bash
sha256sum -c LS4I_FREEZE.sha256
sha256sum -c LS4J_FREEZE.sha256
sha256sum -c RESULTS_MANIFEST_LS4J.sha256
PYTHONPATH=src:scripts python scripts/ls4j_result_summary.py
```

The summary verifies the canonical Stage-1 identity, original event handoff
and every OFF veto against the complete retained B1 search. The frozen runner
refuses to overwrite its result directory. Full reclassification can be
repeated in a separate checkout after preserving that derived directory;
no telescope access is required for the Stage-1 phase.
'''
    text+=f'\nStage-1 result identity: `{identity}`.\n'
    (ROOT/'LS4J_FRAGMENT_ASSOCIATION_RESULT.md').write_text(text)
    print('Verified: 36 cases, 64 exact event handoffs and all 136 OFF links; no HTR download required.')

if __name__=='__main__':main()
