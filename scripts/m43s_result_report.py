"""Validate completed M43S audits and generate a readable result + manifest."""
from collections import Counter
import json
from m43s_profile_sensitivity import ROOT,OUT,CONFIG,frozen,sha
from m43e_economical_bank import read_sealed,write_sealed


def main():
    r=read_sealed(OUT/'result.json');cfg=frozen(r['freeze_commit'])
    assert len(r['endpoints'])==112
    assert len({(e['truth']['truth_index'],e['nominal_total_epoch_strength']) for e in r['endpoints']})==112
    outcomes={};dispositions=Counter();members=0
    for p in sorted(OUT.glob('truth*.json')):
        item=read_sealed(p);audit=item['audit'];outcome=item['endpoint']
        assert item['freeze_commit']==r['freeze_commit'] and item['config_sha256']==r['config_sha256']
        assert audit['threshold']['certificate_sha256']==r['threshold_certificate_sha256']
        assert len(audit['members'])==audit['retention_certificates']['on']['retained_record_count']
        key=(outcome['truth']['truth_index'],outcome['nominal_total_epoch_strength']);assert key not in outcomes
        outcomes[key]=outcome;members+=len(audit['members']);dispositions.update(m['physical_disposition'] for m in audit['members'])
    assert len(outcomes)==96
    for e in r['endpoints']:
        if e['nominal_total_epoch_strength']:assert e==outcomes[e['truth']['truth_index'],e['nominal_total_epoch_strength']]
        else:assert e['zero_level_reuses_m43r_baseline']
    for s in r['summary']:
        es=[e for e in r['endpoints'] if e['truth']['profile']==s['profile'] and e['nominal_total_epoch_strength']==s['nominal_total_epoch_strength']]
        assert len(es)==s['denominator']==8
        for key in ('retained','passes_physical_vetoes','recovered'):assert s[key]==sum(e[key] for e in es)
    reversals=[]
    for truth in cfg['truths']:
        es=sorted((e for e in r['endpoints'] if e['truth']==truth),key=lambda e:e['nominal_total_epoch_strength'])
        for lower,higher in zip(es,es[1:]):
            if lower['recovered'] and not higher['recovered']:
                reversals.append({'truth_index':truth['truth_index'],'recovered_strength':lower['nominal_total_epoch_strength'],
                    'missed_higher_strength':higher['nominal_total_epoch_strength']})
    write_sealed(OUT/'artifact_validation.json',{'complete':True,'unique_endpoints':112,'nonzero_trial_audits':96,
        'same_threshold_certificate':r['threshold_certificate_sha256'],'all_compact_member_decisions':members,
        'member_dispositions':dict(dispositions),'all_frozen_dependencies_exact':True,'nonmonotonic_recovery_pairs':reversals})
    profiles=cfg['profiles'];by={(s['profile'],s['nominal_total_epoch_strength']):s for s in r['summary']}
    rows=['| Nominal total strength | Ideal retained | Ideal recovered | Combined retained | Combined recovered |',
        '|---:|---:|---:|---:|---:|']
    for a in cfg['amplitudes']:
        x,y=[by[p,a] for p in profiles]
        rows.append(f'| {a} | {x["retained"]}/8 | {x["recovered"]}/8 | {y["retained"]}/8 | {y["recovered"]}/8 |')
    details=['| Anchor / carrier index | Active epochs (1-based) | Profile | Recovered strengths | First recovered tested strength |',
        '|---|---|---|---|---:|']
    for truth in cfg['truths']:
        strengths=[e['nominal_total_epoch_strength'] for e in r['endpoints'] if e['truth']==truth and e['recovered']]
        details.append(f'| {truth["parent_anchor"]} / {truth["score_index"]} | {", ".join(str(e+1) for e in truth["active_epochs"])} | '
            +('ideal' if truth['profile']==profiles[0] else 'combined')+' | '+(', '.join(map(str,strengths)) or 'none')+' | '+str(min(strengths) if strengths else 'none')+' |')
    zero=sum(e['recovered'] for e in r['endpoints'] if e['nominal_total_epoch_strength']==0)
    primary=sum(e['recovered'] for e in r['endpoints'] if e['truth']['profile']==profiles[0] and e['nominal_total_epoch_strength']>0)
    exact=sum(e['ideal_exact_grid_recovered'] is True for e in r['endpoints'] if e['nominal_total_epoch_strength']>0)
    midpoint=[g['maximum_active_row_residual_hz'] for g in cfg['geometric_midpoint_controls'].values()]
    selected=[g['maximum_active_row_residual_hz'] for g in cfg['geometry'].values()]
    fractions=[t['coefficient_fraction_toward_partner'] for t in cfg['truths'] if t['profile']==profiles[1]]
    lost_physical=sum(e['retained'] and not e['passes_physical_vetoes'] for e in r['endpoints'])
    lost_rank=sum(e['passes_physical_vetoes'] and not e['recovered'] for e in r['endpoints'])
    diagnostic=read_sealed(OUT/'retrospective_loss_diagnostic.json')
    assert diagnostic['original_result_sha256']==r['result_sha256']
    cases=diagnostic['cases'];mask_losses=sum(c['all_above_threshold_associated_cells_removed_by_mask'] for c in cases)
    diagnostic_rows=['| Strongest-level missed truth | Associated cells >=10 without mask | With original mask | Best active-cut score before mask |',
        '|---:|---:|---:|---:|']
    for c in cases:
        best=c['best_unmasked_associated_member']
        diagnostic_rows.append(f'| {c["truth_index"]} | {c["associated_active_cut_cells_at_threshold_without_mask"]} | '
            +f'{c["associated_cells_at_threshold_with_mask"]} | '+(f'{best["unmasked_active_cut_score"]:.6f}' if best else 'none')+' |')
    text=f'''# M43S weaker and fractional native-profile sensitivity results

The prospectively frozen pilot is complete: **96 new signal-injection runs**,
16 reused zero-level endpoints, and 112 total endpoints. It measures the effect
of weaker ideal signals and a defined harder profile on the unchanged M43R
detector. All tests use one observing sequence, 37 templates and the same small
11.6 kHz search interval. No astronomical candidate is authorized.

## Recovery versus injected strength

Each profile has eight truths per strength: two anchor/carrier groups crossed
with the four activity subsets. The table gives retained and fully recovered
truths separately. The 16 zero-level endpoints reuse one M43R background
execution; {zero} were recovered. They are not independent noise trials.

'''+ '\n'.join(rows)+f'''

The total-strength scale equals M43R's nominal active-epoch width-1 SNR for ideal
bin-centered signals. For the combined profile it is the **total added power**
on that same scale, not the actual peak SNR. Power is spread across channels,
with fractional carrier placement, a supported off-template perturbation and a
one-channel linear sweep during each integration. The effects are combined and
cannot be assigned individually from this experiment.

There were {lost_physical} truth/strength endpoints retained but lost at the
physical-veto stage, and {lost_rank} that passed physical vetoes but failed rank.
These are truth-level losses, not counts of the correlated member records.

'''+ '\n'.join(details)+f'''

The first recovered tested strength is a bracket point on this finite grid,
not a continuous detection limit or a population completeness percentile.
There are {len(reversals)} adjacent-strength reversals where a recovered signal
becomes a miss at higher injected strength. Those outcomes remain in the table
and need a rejection-stage explanation; recovery must not be assumed monotonic.

## Association and geometric scope

The new M43S primary endpoint requires the exact activity subset and a retained
member within 20 Hz of the true center track at **every active integration**,
passing physical vetoes and inclusive rank p <=0.01. Any searched template and
width may supply it. This differs from M43R's exact-template/exact-carrier
endpoint, which is preserved. In ideal-profile trials here, the secondary exact
criterion recovered {exact}/48 nonzero endpoints, versus {primary}/48 under the
new association criterion. The two must not be silently conflated.

Before publication or new signal evaluation, metadata showed that all eight
literal midpoint controls lacked a member within 20 Hz in this **37-template
sample**: their nearest residuals range from {min(midpoint):.3f} to
{max(midpoint):.3f} Hz. Those geometry-only controls remain in config, outside
the 112 injected endpoints. This finding says nothing by itself about coverage
of the full 1,701-template bank.

To measure numerical sensitivity rather than known geometric absence, the frozen
rule selects the largest dyadic fraction toward the partner whose nearest
active-row residual is <= one native channel. Selected coefficient fractions
range from {min(fractions):.9g} to {max(fractions):.9g}; all selected truths have
residual <={max(selected):.6f} Hz. Every attempted metadata fraction is retained.
These are near-template perturbations, not a sample of the entire gaps between
templates. Carrier 1024 is paired with anchor 0 and carrier 3072 with anchor
1700, so carrier and anchor effects also cannot be separated.

## Retrospective diagnosis of strong-signal losses

After the frozen experiment completed, a separately labelled diagnostic replayed
only the {len(cases)} strongest-level misses. Every reproduced injected input
identity and ON mask hash matches the original trial, and masked above-threshold
associated-cell counts reproduce the retained-member audits exactly.

'''+ '\n'.join(diagnostic_rows)+f'''

In {mask_losses}/{len(cases)} of these misses, the inherited isolation mask removes
all associated above-threshold cells before the later physical-veto stages.
The diagnostic retains the exact seed witnesses: filter width, epoch, neighboring
carrier, injected and background epoch scores. The rule flags a >=10 peak when
all other epochs at that carrier are below 3, combines flags across widths and
expands them by nine carriers. A displaced multi-epoch signal can therefore
trigger an isolated-epoch flag at a nearby carrier and lose its usable members.
This is a sensitivity limitation of the existing rule; arithmetic still matches
the frozen implementation.

Removing a mask in this explanation is **not a calibrated alternate detector**
and does not establish final recovery after other vetoes. No rule, threshold,
original endpoint or published result was changed. An actual mask revision needs
its own prospective null and injection calibration.

## Native model, calibration reuse and evidence

The combined profile uses a finite sinc-squared response, 17 midpoint time
samples across a one-native-channel sweep, and 16 tail channels beyond each
sweep endpoint. Each finite native packet is normalized to unit total mass;
unnormalized masses and packet hashes are retained. It is a defined sensitivity
model, not an instrument-channelizer measurement or inferred astrophysical drift.
Normalization remains fixed before addition. Complete affected native windows
and integrated columns are recomputed in float32; the same patches feed receiver
signatures. Original telescope receipts remain untouched.

- Public freeze: `{r['freeze_commit']}`.
- Result seal: `{r['result_sha256']}`.
- Config SHA-256: `{r['config_sha256']}`; {len(cfg['pinned_sha256'])} pinned dependencies.
- The M43R threshold certificate `{r['threshold_certificate_sha256']}` is reused
  unchanged at threshold 10. Its 128 calibration maxima and held-out diagnostics
  are reused; **zero new null calculations** are counted.
- Ten focused tests pass, including five new profile/association/rehydration
  tests and the five M43R injection tests. Earlier unchanged integration evidence
  remains applicable and is not relabelled as new testing.
- All 24 native cache/gather identities reproduce the M43R anchors exactly.
  Original 96 M43P arrays and the complete baseline identity are verified on load.
- All 112 endpoints and {members:,} compact member decisions validate; every
  trial uses the same threshold. There is no truncation.
- Runtime: {r['wall_seconds']:.3f} seconds; zero new telescope data requests.

The [audit directory](results_m43s_profile_sensitivity/) contains all 96 sealed
nonzero trial files, source/profile provenance, compact members, stage
certificates, complete endpoints, input-reuse evidence and logs. Compact audits
bind the full in-memory pipeline hash but are not full pipeline serializations.
The manifest covers these artifacts, report, plan, model and executable scripts.

## Interpretation and next step

This is a bounded sensitivity experiment on previously inspected background.
It locates recovery changes on the tested strength grid and exposes the limits
of interpreting sparse-template tests. It is not an independent search,
instrument-completeness measurement or statement that no artificial emission
exists. The immediate next step is a prospectively frozen isolation-mask
comparison, with fresh null calibration and paired injection trials, to test
a repair for the demonstrated losses. Broader template coverage and independently
varied profile effects and carriers remain necessary afterward. The fixed
detector and existing results remain reference points.

Reproduce in the pinned Python/NumPy environment with the retained M43H/M43P
inputs:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \\
  .venv/bin/python scripts/m43s_profile_sensitivity.py \\
  --freeze-commit {r['freeze_commit']} \\
  --anchor-root /path/to/m43p_work --source-root /path/to/m43h_work/live
```
'''
    (ROOT/'MILESTONE_43S_PROFILE_SENSITIVITY_RESULT.md').write_text(text)
    paths=[p for p in OUT.rglob('*') if p.is_file()]
    paths += [CONFIG,ROOT/'MILESTONE_43S_PROFILE_SENSITIVITY_PLAN.md',ROOT/'MILESTONE_43S_PROFILE_SENSITIVITY_RESULT.md']
    paths += [ROOT/p for p in ('src/seti_repeater/injection_m43s.py','scripts/m43s_profile_sensitivity.py',
        'scripts/m43s_freeze_config.py','scripts/m43s_result_report.py','scripts/m43s_loss_diagnostic.py','tests/test_m43s_profiles.py')]
    (ROOT/'RESULTS_MANIFEST_M43S_PROFILE_SENSITIVITY.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in sorted(paths)))
    print(json.dumps({'manifest_entries':len(paths),'result_sha256':r['result_sha256'],'member_decisions':members,'summary':r['summary']},indent=2))


if __name__=='__main__':main()
