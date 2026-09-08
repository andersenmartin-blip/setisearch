"""Summarize complete, audited Z evidence without selecting or modifying outcomes."""
import json
from pathlib import Path
from m43z_joint_controls import ROOT,OUT,CONFIG,sha
from m43e_economical_bank import read_sealed,write_sealed
from seti_repeater.confirmation_m43z import POLICIES

def main():
    r=read_sealed(OUT/'result.json');a=read_sealed(OUT/'artifact_validation.json');cfg=json.loads(CONFIG.read_text())
    assert r['complete'] and a['passed']
    identities=read_sealed(OUT/'input_identity_groups.json')['groups']
    input_group={i:h for h,indices in identities.items() for i in indices}
    aggregate=[]
    for policy in POLICIES:
        es=[e for e in r['endpoints'] if e['policy']==policy];signals=[e for e in es if e['signal_present']];controls=[e for e in es if not e['signal_present']]
        assert len(signals)==224 and len(controls)==128
        aggregate.append(dict(policy=policy,signal_associations=sum(e['truth_association']['recovered'] for e in signals),
            leaking_controls=sum(e['final_members']>0 for e in controls),
            distinct_leaking_control_patch_inventories=len({input_group[e['case_index']] for e in controls if e['final_members']>0}),
            control_types={t:sum(e['final_members']>0 for e in controls if e['case_type']==t) for t in ('interferer-only','supported-spike','ON-OFF','OFF-only')},
            final_members=sum(e['final_members'] for e in es)))
    pairs=[]
    for kind in ('distributed17-near-OFF','distributed17-far-OFF','combined-near-OFF','distributed17-moderate-OFF','mixed-unequal'):
        for policy in POLICIES:
            es=[p for p in r['matched_component_comparison'] if p['case_type']==kind and p['policy']==policy];assert len(es)==32
            eligible=[e for e in r['endpoints'] if e['case_type']==kind and e['policy']=='neighbor9' and e['truth_association']['recovered']]
            pairs.append(dict(case_type=kind,policy=policy,pairs=32,signal_only_associations=sum(e['signal_only_recovered'] for e in es),
                with_interference_associations=sum(e['with_interference_recovered'] for e in es),paired_losses=sum(e['paired_loss'] for e in es),
                paired_gains=sum(e['paired_gain'] for e in es),reference_recoverable_with_interference=len(eligible),
                added_policy_losses=sum(e['added_policy_loss_on_interference_input'] for e in es)))
    activity=[];matched_strata=[]
    for policy in POLICIES:
        for strength in (24.,48.):
            for active in ([0,1],[0,2],[1,2],[0,1,2]):
                for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                    es=[e for e in r['endpoints'] if e['policy']==policy and e['strength']==strength and e['case_type']==kind and cfg['cases'][e['case_index']]['active_epochs']==active]
                    assert len(es)==4
                    activity.append(dict(policy=policy,strength=strength,active_epochs=active,case_type=kind,inputs=4,
                        signal_present=es[0]['signal_present'],truth_associations=sum(e['truth_association']['recovered'] for e in es),
                        cases_with_final_members=sum(e['final_members']>0 for e in es)))
                    ps=[e for e in r['matched_component_comparison'] if e['policy']==policy and e['case_type']==kind and cfg['cases'][e['case_index']]['strength']==strength and cfg['cases'][e['case_index']]['active_epochs']==active]
                    if ps:
                        assert len(ps)==4
                        matched_strata.append(dict(policy=policy,strength=strength,active_epochs=active,case_type=kind,pairs=4,
                            signal_only_associations=sum(e['signal_only_recovered'] for e in ps),with_interference_associations=sum(e['with_interference_recovered'] for e in ps),
                            paired_losses=sum(e['paired_loss'] for e in ps),paired_gains=sum(e['paired_gain'] for e in ps),
                            added_policy_losses=sum(e['added_policy_loss_on_interference_input'] for e in ps)))
    write_sealed(OUT/'activity_breakdown.json',dict(source_result_sha256=r['result_sha256'],endpoints=activity,matched_costs=matched_strata))
    leaking=[dict(case=cfg['cases'][e['case_index']],endpoint=e) for e in r['endpoints'] if not e['signal_present'] and e['final_members']>0]
    write_sealed(OUT/'interpretation.json',dict(source_result_sha256=r['result_sha256'],aggregate=aggregate,matched_costs=pairs,leaking_controls=leaking,
        retrospective_choice_used_for_reporting=False,prior_X_failures_preserved=True))
    table='\n'.join(f"| {s['policy']} | {s['signal_associations']}/224 | {s['leaking_controls']}/128 | {s['control_types']['interferer-only']}/32 | {s['control_types']['supported-spike']}/32 | {s['control_types']['ON-OFF']}/32 | {s['control_types']['OFF-only']}/32 |" for s in aggregate)
    pairtable='\n'.join(f"| {s['case_type']} | {s['policy']} | {s['signal_only_associations']}/32 | {s['with_interference_associations']}/32 | {s['paired_losses']} | {s['paired_gains']} | {s['added_policy_losses']}/{s['reference_recoverable_with_interference']} |" for s in pairs)
    conditions='\n'.join('- '+p+': '+(', '.join(k for k,v in c['conditions'].items() if not v) or 'all new-panel conditions pass')+'.' for p,c in r['comparisons'].items())
    identityline='; '.join(p['policy']+': '+str(p['leaking_controls'])+' leaking labels from '+str(p['distinct_leaking_control_patch_inventories'])+' distinct native patch inventories' for p in aggregate)
    lossline='; '.join(p+': '+str(len(c['signal_losses']))+' signal-case losses, '+str(len(c['removed_leaking_controls']))+' leaking controls removed' for p,c in r['comparisons'].items())
    train=read_sealed(OUT/'calibration.json');held=read_sealed(OUT/'heldout.json')
    notes=(ROOT/'M43Z_FAILURE_INTERPRETATION.md').read_text()
    text=f'''# M43Z result: joint OFF-window rejection and signal-retention cost

The frozen experiment completed all352 inputs and1,408 paired policy endpoints.
{lossline}. All policies are additive cuts of the same reference executions.
All three alternatives fail the frozen acceptance gates.
No astronomical candidate or general adoption is claimed. The earlier M43X
signal losses remain unresolved; new combinations cannot erase exposed failures.

## Complete signal and control results

| Policy | Signal associations | Leaking controls | Interferer-only | Supported spike | ON-OFF | OFF-only |
|---|---:|---:|---:|---:|---:|---:|
{table}

Signal association uses the exact injected activity subset and <=20 Hz maximum
center-track residual over every active ON integration. Counts are not independent
physical detections. Pure controls and signal-present inputs retain separate
denominators. Counts in the four control-type columns are leaking cases.

The following predeclared new-panel conditions fail:

{conditions}

The zero interferer-only-member condition explicitly tests background-supported
single-epoch interference, even when it does not associate with the absent truth.
No condition was weakened after evaluation. Complete gains/losses and Boolean
gates are retained in result.json.

Duplicate-aware control accounting: {identityline}. These groups share the
same fixed background; even different patch inventories are not independent
observing sequences.

## Matched signal costs

Every row contains32 paired input labels, not32 independent observations.
The last column counts additional policy losses among with-interference cases
that reference still associates. A denominator of zero is undefined, not a zero
false-veto rate. Paired losses/gains compare signal-only to with-interference
under the same policy and can include effects already present in reference.
Mixed-unequal adds ON interference; the other four families add OFF interference.

| Input family | Policy | Signal only | With interference | Paired losses | Paired gains | Added policy losses / reference recoverable |
|---|---|---:|---:|---:|---:|---:|
{pairtable}

All128 signal/OFF pairs have exactly identical ON native patch payloads. The
near and far OFF offsets are16 and96 proxy bins with alternating sign and
strength4S in the declared active epochs; the added moderate near-OFF family uses strengthS. Distributed17 is a specified sum of
17 equal snapped carrier components q-8 through q+8, with total nominal strengthS
per epoch. It reuses the existing ordered float32 overlay and filtering. It is
not a measured channelizer model or general broadband completeness statement.

[Breakdowns by strength and each activity subset](results_m43z_joint_controls/activity_breakdown.json) retain all conditional denominators.

[Exact signal-loss members and OFF maxima](results_m43z_joint_controls/signal_loss_evidence.json)
provide ON scores, OFF-window maxima and locations, base decisions and added-cut
reasons. [Interpretation data](results_m43z_joint_controls/interpretation.json)
include every surviving pure-control case. The full ledger preserves all retained
members and all four policy decisions, including rejected and unassociated ones.

## Failure interpretation and next work

{notes.split(chr(10),2)[2]}

## Frozen scope and checks

New carriers896/3200, all four active-epoch subsets, existing anchors0/36,
strengths24/48, eleven input families:352 cases with224 signal-present and128 pure
controls. There are {a['distinct_native_patch_inventories']} distinct native patch
inventories. These are correlated interventions on the same observing sequence.
One separate uninjected baseline adds four endpoints to the1,408 panel endpoints.
No source scope or observing coverage was added.

The original320 cases are unchanged; a public pre-evaluation amendment appended32 moderate near-OFF counterparts before any Z scoring. Two composition tests pass. The audit verifies {a['pinned_files']} frozen files,
all352 seals, {a['reference_members']:,} retained reference members and
{a['policy_member_decisions']:,} policy member decisions, all associations/gates,
128 matched ON payload invariants and exact set intersections. All96 original
arrays and48 native gathers match. The unchanged W4,440 OFF scalar anchors and
X5,920 aggregate anchors are reused rather than rerun.

Training and heldout each use128 new shift rows, excluding1,536 earlier rows.
Training maximum {max(train['null_maxima']):.6f}, heldout maximum
{max(held['null_maxima']):.6f}, fixed calibrated threshold {r['heldout']['threshold']:.6f},
heldout exceedances {r['heldout']['at_or_above_threshold']}/128. Future fresh rows
must exclude1,792 total prior rows. These within-sequence pre-veto nulls do not
measure an independent physical FAP or OFF false-veto probability.
Numerical experiment runtime: {r['wall_seconds']:.3f} seconds.

The ephemeral workspace had been cleared. Existing archive byte ranges were
redownloaded against original ETags, sizes and segment hashes, then all source
receipts and96 arrays were reproduced. Recovery is not new telescope coverage.
The initial missing hdf5plugin dependency failure is preserved; installing the
required package restored the already qualified HDF5 runtime. Redundant HTTP
mirror caches were released only after source/anchor verification to stay within
local disk capacity. Source files and anchor arrays were retained. No experiment
rule was changed by operational restoration. Recovery logs are under restoration/.

Public scientific freeze:
[{r['freeze_commit']}](https://github.com/andersenmartin-blip/setisearch/commit/{r['freeze_commit']}).
The full gzip is published as three byte segments under ledger_parts/ because
the publishing connection has a 16 MiB request limit. Reconstruct the exact original
with `python scripts/m43z_restore_ledger.py` before audit or checksum verification.
No original record or seal changed.
Result seal: `{r['result_sha256']}`.
[Plan](MILESTONE_43Z_JOINT_CONTROLS_PLAN.md),
[result](results_m43z_joint_controls/result.json),
[complete ledger and reconstruction instructions](results_m43z_joint_controls/ledger_parts/README.md),
[audit](results_m43z_joint_controls/artifact_validation.json),
[run log](results_m43z_joint_controls/live_run.log),
[checksum manifest](RESULTS_MANIFEST_M43Z_JOINT_CONTROLS.sha256).
'''
    # Space prose numerals without altering identifiers/paths or recorded values.
    for old,new in [('all352','all 352'),('strengthS','strength S'),('families:352','families: 352'),('All128','All 128'),('original320','original 320'),('appended32','appended 32'),('type4','type 4'),('type3','type 3'),('and1,408','and 1,408'),('contains32','contains 32'),('not32','not 32'),('All96','All 96'),('are16','are 16'),('and96','and 96'),('strength4S','strength 4S'),('carriers896','carriers 896'),('anchors0','anchors 0'),('strengths24','strengths 24'),('with224','with 224'),('and128','and 128'),('the1,408','the 1,408'),('all96','all 96'),('and48','and 48'),('W4,440','W 4,440'),('X5,920','X 5,920'),('use128','use 128'),('excluding1,536','excluding 1,536'),('exclude1,792','exclude 1,792')]:text=text.replace(old,new)
    (ROOT/'MILESTONE_43Z_JOINT_CONTROLS_RESULT.md').write_text(text)
    print(json.dumps(dict(aggregate=aggregate,matched_costs=pairs,failed_conditions={p:[k for k,v in c['conditions'].items() if not v] for p,c in r['comparisons'].items()}),indent=2))
if __name__=='__main__':main()
