"""Post-execution inventory audit and descriptive M43V report."""
import gzip
import hashlib
import json
from pathlib import Path
from m43b_active_support import seal
from m43e_economical_bank import read_sealed,write_sealed
from m43v_component_diagnostic import coordinate,final_keys,set_comparison

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43v_component_diagnostic'
POLICIES=('legacy','neighbor2','neighbor9');VARIANTS=('both','first','second')

def main():
    r=read_sealed(OUT/'result.json');cfg=json.loads((ROOT/'config/m43v_component_diagnostic.json').read_text())
    import subprocess
    first=json.loads(subprocess.check_output(['git','show','277e3315d2c5250cbbb58852b334b5896636c353:config/m43v_component_diagnostic.json'],cwd=ROOT))
    assert {k:v for k,v in first.items() if k!='pinned_sha256'}=={k:v for k,v in cfg.items() if k!='pinned_sha256'}
    for p,h in cfg['pinned_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    packed=(OUT/'case_audits.jsonl.gz').read_bytes();raw=gzip.decompress(packed)
    assert hashlib.sha256(packed).hexdigest()==r['ledger_sha256']
    assert hashlib.sha256(raw).hexdigest()==r['ledger_uncompressed_sha256']
    records=[json.loads(line) for line in raw.splitlines() if line.strip()]
    assert len(records)==30
    original={}
    with gzip.open(ROOT/'results_m43u_signal_interference/case_audits.jsonl.gz','rt') as f:
        for line in f:
            if line.strip():
                x=json.loads(line);original[x['case']['case_index']]=x
    members=0;replays=0;trace=[];lookup={}
    for rec,spec in zip(records,cfg['inputs']):
        assert rec['result_sha256']==seal({k:v for k,v in rec.items() if k!='result_sha256'})
        assert rec['spec']==spec and rec['freeze_commit']==r['freeze_commit']
        assert rec['config_sha256']==hashlib.sha256((ROOT/'config/m43v_component_diagnostic.json').read_bytes()).hexdigest()
        assert rec['components']==[original[spec['case_index']]['case']['components'][i] for i in spec['component_indices']]
        assert len({a['input_inventory_sha256'] for a in rec['audits'].values()})==1
        for p,a in rec['audits'].items():
            assert p in POLICIES
            assert a['final_diagnostic_survivors']==len(final_keys(a))
            assert len({coordinate(m) for m in a['members']})==len(a['members'])
            members+=len(a['members'])
            if spec['variant']=='both':
                assert a==original[spec['case_index']]['audits'][p];replays+=1
            for probe in rec['probes'][p]:
                for ar in probe['annotated_records']:
                    adj=ar['single_adjacent_off_evidence'];alias=ar['receiver_alias_evidence'];off=ar['off_track_evidence']
                    assert adj['vetoed']==any(x['snr']>=5.5 for x in adj['paired_adjacent_off_measurements'])
                    assert alias['matched']==(alias['matched_cross_component_record_count']>0)
                    trace.append({'case_index':spec['case_index'],'variant':spec['variant'],'policy':p,
                        'coordinate':probe['coordinate'],'on_scores':probe['on_scores'],'off_scores':probe['off_scores'],
                        'same_OFF_match':off['same_hypothesis']['matched'],'local_OFF_match':off['local_track']['matched'],
                        'paired_OFF_max':adj['maximum_active_epoch_snr'],'paired_OFF_veto':adj['vetoed'],
                        'qualified_receiver_epochs':alias['qualified_signature_epoch_count'],'receiver_alias_match':alias['matched'],
                        'disposition':ar['member_disposition']})
        lookup[spec['case_index'],spec['variant']]=rec
    assert replays==30
    summary=[]
    for i in cfg['selected_cases']:
        for p in POLICIES:
            row={'case_index':i,'case_type':original[i]['case']['case_type'],'policy':p}
            row.update(set_comparison(*(final_keys(lookup[i,v]['audits'][p]) for v in VARIANTS)))
            row['truth_association']={v:lookup[i,v]['truth_association'].get(p,{}).get('recovered') for v in VARIANTS}
            summary.append(row)
    assert json.loads(json.dumps(summary))==r['summary']
    false_associations=[]
    for (i,v),rec in lookup.items():
        if v!='second':continue
        for p,a in rec['truth_association'].items():
            if a['recovered']:
                ids=set(a['associated_record_ids'])
                false_associations.append({'case_index':i,'policy':p,'association':a,
                    'final_members':[m for m in rec['audits'][p]['members'] if m['record_id'] in ids and m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']]})
    write_sealed(OUT/'false_truth_associations.json',{'source_result':r['result_sha256'],'cases':false_associations})
    write_sealed(OUT/'failure_stage_trace.json',{'source_result':r['result_sha256'],'retained_probe_records':trace})
    audit=write_sealed(OUT/'artifact_validation.json',{'complete':True,'pinned_files':len(cfg['pinned_sha256']),
        'sealed_inputs':30,'endpoints':90,'historical_endpoint_replays_exact':replays,
        'member_decisions':members,'summary_recomputed':True,'retained_probe_records':len(trace),
        'result_seal':r['result_sha256']})
    mt=['| Policy | Both: truth associations / members | Signal only: associations / members | Interferer only: false associations / members | Both-only coordinates |','|---|---:|---:|---:|---:|']
    totals={}
    for p in POLICIES:
        rows=[s for s in summary if s['case_type']=='mixed' and s['policy']==p]
        totals[p]={v:{'associated_cases':sum(s['truth_association'][v] for s in rows),'members':sum(s[v] for s in rows)} for v in VARIANTS}
        total_new=sum(s['both_only'] for s in rows)
        mt.append('| '+p+' | '+' | '.join(f"{totals[p][v]['associated_cases']}/8 / {totals[p][v]['members']}" for v in VARIANTS)+f' | {total_new} |')
    ct=['| Case / policy | Both | First only | Second only | Both-only coordinates |','|---|---:|---:|---:|---:|']
    for s in summary:
        if s['case_type']!='mixed':ct.append(f"| {s['case_index']} / {s['policy']} | {s['both']} | {s['first']} | {s['second']} | {s['both_only']} |")
    pt=['| Case / policy / carrier / width | Paired OFF maximum | Retained OFF match | Qualified receiver epochs | Alias match |','|---|---:|---|---:|---|']
    for x in trace:
        if x['variant']=='both':
            _,q,w,_=x['coordinate']
            pt.append(f"| {x['case_index']} / {x['policy']} / {q} / {w} | {x['paired_OFF_max']:.6f} | {x['same_OFF_match'] or x['local_OFF_match']} | {x['qualified_receiver_epochs']} | {x['receiver_alias_match']} |")
    report=f'''# M43V: component interventions and actual failure-stage evidence

Completed **30 native inputs and 90 detector executions**: 30 exact historical
M43U endpoint replays and 60 new component endpoints. Three baseline replays are
separate. All original calibration summaries, maxima, thresholds and bindings
reproduce exactly. No detector or threshold changes; no new observations.

This is retrospective diagnosis of all eight M43U mixed cases and the two
leaking controls, not independent validation or a new pass/fail gate. Both
M43U development gates remain failed. No astronomical candidate is claimed.

The diagnostic identifies three limitations: the paired-OFF floor leaves three
wide-filter responses just below its rejection boundary; weak displaced power
can both suppress neighbor9's isolation mask and satisfy its active-epoch cut;
and one interferer-only input falsely matches the absent intended truth.

## Matched mixed-input interventions

The first component is the intended strength-32 combined-profile signal; the
second is the strength-128 nearby single-epoch component. Positions, profiles,
strengths and epoch membership are identical in both and component-only inputs.
Association uses the original exact activity subset and <=20 Hz center-track
rule. An association when only the interferer is injected is a false truth
association in this controlled test, never true-signal recovery.

{chr(10).join(mt)}

Counts of members are correlated template/carrier/width/activity representations,
not independent physical events. Both-only coordinates are present in the joint
input but absent from the union of the two component-only final sets. Their
presence establishes a conditional interaction in the implemented pipeline,
not which astronomical or instrumental process exists in real observations.
The complete per-case set differences and truth-association outcomes are in
[result.json](results_m43v_component_diagnostic/result.json).

In case 44, the signal alone is recovered by every policy. Adding the stronger
component removes its association under legacy and neighbor2, while neighbor9
retains it. Thus that paired difference is conditional on adding interference.

In case 35, neighbor9 associates one interferer-only member with the absent
intended truth: template 36, carrier 1574, width 129, activity [0,2], score
11.909003 and maximum center-track residual 19.491880 Hz. Its active-epoch
values are 13.691339 and 3.150533. No true signal was injected in this endpoint.
The broad response and marginal second-epoch support pass the declared
association and diagnostic cuts. This demonstrates that those cuts can be
confused; it does not justify retrospectively subtracting one from M43U's
8/8 association count or assigning every jointly associated member to the
interferer. See [the complete false-association record](results_m43v_component_diagnostic/false_truth_associations.json).

## Leaking-control interventions

Case 61: first is ON injection, second is the matching OFF injection; both use
strength 32 at carrier 3584, template 0, all epochs. Case 69: first is the
strength-32 epoch-0 spike at 3584, second is strength-4 power at 3590 in epochs
1 and 2, template 36. Counts below are final diagnostic member coordinates.

{chr(10).join(ct)}

The fixed historical probe coordinates were declared before M43V execution:
case 61 carriers 3610–3612, width 65, template 0, epochs [0,1,2]; case 69
carrier 3588, width 9, template 36, epochs [0,2]. Full probe traces include
scores, masks and contributing isolation seeds even when a probe is not retained.

{chr(10).join(pt)}

Paired-OFF rejection uses an inclusive 5.5 single-epoch floor at the exact
same template/carrier/width. Retained OFF-track matching uses 20 Hz tolerance.
Receiver-alias rejection requires qualifying signatures and a matching distinct
identity component in at least two active epochs. All actual measurements and
decisions, including component-only probes, are in
[failure_stage_trace.json](results_m43v_component_diagnostic/failure_stage_trace.json)
and the [complete ledger](results_m43v_component_diagnostic/case_audits.jsonl.gz).

Case 61 has no masking at the three probes. Adding the OFF component removes
152 of the 155 ON-only final coordinates, leaving three unchanged coordinates.
Their paired-OFF maxima are 5.436803, 5.362956 and 5.488204, all below 5.5.
No retained OFF track matches, and the executed receiver-alias search finds
no cross-component match despite three qualifying signature epochs. This is
a remaining boundary failure of the combined rules, not missing OFF input.

For case 69, the first component alone gives epoch scores 10.577853, 1.565340,
2.525096 at the fixed width-9 probe. Adding the weak second component changes
the latter two values to 2.898673 and 3.858429. Epochs [0,2] then satisfy the
minimum of 3 and yield stack score 10.207994. Of the 16 original isolation
seeds able to mask the probe, legacy retains 16, neighbor2 retains 11, and
neighbor9 retains none. The first component alone still leaves six neighbor9
seeds. This intervention therefore both removes exclusion and supplies the
second active epoch. Neither component alone has a final member. Receiver
peak scores 3.196169 and 1.854530 are below the 5.5 qualification floor, so
zero epochs qualify for alias matching. The ledger's seed traces reproduce
the actual mask bit for every probe and policy.

## Next experiment

The next useful milestone is a prospectively frozen comparison of rejection
evidence that accounts for filter width and the separate contributions from
active epochs. It must include ON/OFF paired signals, dominant single-epoch
power with displaced weak support, and interferer-only truth-confusion controls.
Keep true signals, both mixed components and their matched single-component
inputs in the same panel. Evaluate additional carrier/activity combinations
and a predeclared strength range with new calibration and held-out evidence.

Any proposed width-aware OFF or cross-epoch consistency rule must be defined
before evaluation. Preserve cases 35, 44, 61 and 69 as exposed development
examples, rather than treating successful repairs on them as independent
validation. Include false truth associations in the decision conditions;
recovery counts alone cannot establish that the intended component was found.
M43V supplies the diagnosis; it does not adopt a corrected detector.

## Clarification of the inherited disposition label

`pending_receiver_alias_evaluation` is a legacy output label that remains after
the alias routine has executed if no rejecting alias match is found. It does
not by itself mean that this routine was skipped. The alias certificate,
qualifying epoch count and actual match evidence establish what ran. Earlier
M43U prose cautiously associated the label with incomplete clearance; M43V
clarifies execution without changing any historical member or decision.
No-match under this limited rule is not proof of celestial origin.

## Validation and limits

Two focused coordinate/set-accounting tests pass. The unchanged detector's
earlier numerical tests are reused. This audit verifies {len(cfg['pinned_sha256'])}
pinned files, 30 sealed input records, all 90 endpoints, 30 exact historical
pipeline audits, {members:,} member decisions and all reported set comparisons.
The run revalidates 96 original arrays and 48 native ON/OFF gather anchors.
Completed numerical runtime: {r['wall_seconds']:.1f} seconds. Source requests: 0.

The original freeze stopped on a baseline provenance mismatch before any
component input. The [public amendment](MILESTONE_43V_BASELINE_AMENDMENT.md)
restores the exact original baseline call; all scientific configuration values
remain unchanged. The original failure log is retained. Successful baseline and
historical audits still have to match M43U in full, not only in event counts.

No additional nulls, independent background realizations, carrier/activity
coverage, end-to-end completeness or physical false-alarm probabilities are
measured. Component interventions are conditional on this one observing sequence.
Any corrected rule requires a prospective freeze and additional evaluation
combinations; these already exposed cases remain development diagnostics.

- Public execution freeze: `{r['freeze_commit']}`.
- Result seal: `{r['result_sha256']}`.
- Compressed ledger SHA-256: `{r['ledger_sha256']}`.
- [Frozen plan](MILESTONE_43V_COMPONENT_DIAGNOSTIC_PLAN.md).
- [Audit](results_m43v_component_diagnostic/artifact_validation.json),
  [run log](results_m43v_component_diagnostic/live_run.log), and
  [checksum manifest](RESULTS_MANIFEST_M43V_COMPONENT_DIAGNOSTIC.sha256).
'''
    (ROOT/'MILESTONE_43V_COMPONENT_DIAGNOSTIC_RESULT.md').write_text(report)
    print(json.dumps({'audit':audit,'mixed_totals':totals,'control_rows':[{k:v for k,v in s.items() if not k.endswith('_coordinates')} for s in summary if s['case_type']!='mixed']},indent=2))

if __name__=='__main__':main()
