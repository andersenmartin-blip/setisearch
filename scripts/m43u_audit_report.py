"""Audit the complete M43U ledger and render its declared comparisons."""
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from m43b_active_support import seal
from m43e_economical_bank import read_sealed, write_sealed
from m43u_signal_interference import frozen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43u_signal_interference'
POLICIES=('legacy','neighbor2','neighbor9')


def main():
    r=read_sealed(OUT/'result.json');cfg=frozen(r['freeze_commit'])
    before=json.loads(subprocess.check_output(['git','show','6091ff8907e4e882e7227ee6e9ec97c98dfe5331:config/m43u_signal_interference.json'],cwd=ROOT))
    assert {k:v for k,v in cfg.items() if k!='pinned_sha256'}=={k:v for k,v in before.items() if k!='pinned_sha256'}
    for p in OUT.glob('*.json'):
        if p.name!='artifact_validation.json':read_sealed(p)
    packed=(OUT/'case_audits.jsonl.gz').read_bytes();raw=gzip.decompress(packed)
    assert hashlib.sha256(packed).hexdigest()==r['ledger_sha256']
    assert hashlib.sha256(raw).hexdigest()==r['ledger_uncompressed_sha256']
    ledger=[json.loads(line) for line in raw.splitlines() if line.strip()]
    assert len(ledger)==r['cases']==72
    endpoints=[];members=0;max_masked={p:0 for p in POLICIES}
    for case,rec in zip(cfg['cases'],ledger):
        assert rec['result_sha256']==seal({k:v for k,v in rec.items() if k!='result_sha256'})
        assert rec['case']==case and rec['freeze_commit']==r['freeze_commit'] and rec['config_sha256']==r['config_sha256']
        assert rec['bindings']==r['bindings']
        assert len({a['input_inventory_sha256'] for a in rec['audits'].values()})==1
        assert len(rec['endpoints'])==3
        for p,e in zip(POLICIES,rec['endpoints']):
            a=rec['audits'][p]
            assert e['mask_policy']==p and e['case_index']==case['case_index']
            assert a['overlay']==rec['audits']['legacy']['overlay'] and a['overlay']['components']==case['components']
            assert a['calibration_binding']==r['bindings'][p]
            final=sum(m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut'] for m in a['members'])
            assert final==e['final_diagnostic_survivors']==a['final_diagnostic_survivors']
            assert e['control_leakage']==(not e['signal_present'] and final>0)
            for k in ('on','off'):
                assert e[f'masked_{k}_cells']==sum(n for name,n in a['masked_cell_counts'].items() if name.startswith(k+':'))
            assert all(0<=n<=3*4097 for n in a['masked_cell_counts'].values())
            members+=len(a['members']);max_masked[p]=max(max_masked[p],e['masked_on_cells'])
        for k in ('on','off'):
            counts=[e[f'masked_{k}_cells'] for e in rec['endpoints']]
            assert counts[0]>=counts[1]>=counts[2]
        endpoints.extend(rec['endpoints'])
    assert endpoints==r['endpoints'] and len(endpoints)==216
    assert sum(e['signal_present'] for e in endpoints)==144
    summary=[]
    for p in POLICIES:
        for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
            rows=[e for e in endpoints if e['mask_policy']==p and e['case_type']==kind]
            assert len(rows)==8
            summary.append({'policy':p,'case_type':kind,'denominator':8,'signal_present':rows[0]['signal_present'],
                'recovered':sum(e.get('association',{}).get('recovered',False) for e in rows),
                'control_leakage_cases':sum(e['control_leakage'] for e in rows),
                'final_diagnostic_survivors':sum(e['final_diagnostic_survivors'] for e in rows),
                'retained_truths':sum(e.get('association',{}).get('retained',False) for e in rows),
                'physical_truths':sum(e.get('association',{}).get('passes_physical_vetoes',False) for e in rows)})
    assert summary==r['summary']
    lookup={(e['case_index'],e['mask_policy']):e for e in endpoints}
    for p in POLICIES[1:]:
        c=r['comparisons'][p];g=[];l=[];lg=[];ll=[]
        for i in range(72):
            a,b=lookup[i,'legacy'],lookup[i,p]
            field='recovered' if a['signal_present'] else 'control_leakage'
            av=a['association'][field] if a['signal_present'] else a[field]
            bv=b['association'][field] if b['signal_present'] else b[field]
            if bv and not av:(g if a['signal_present'] else lg).append(i)
            if av and not bv:(l if a['signal_present'] else ll).append(i)
        assert [g,l,lg,ll]==[c['signal_gain_cases'],c['signal_loss_cases'],c['additional_control_leakage_cases'],c['removed_control_leakage_cases']]
        cond={'no_signal_recovery_loss':not l,'no_increase_in_control_leakage_cases':len(lg)<=len(ll),
            'no_ON_OFF_survivors':all(e['final_diagnostic_survivors']==0 for e in endpoints if e['mask_policy']==p and e['case_type']=='ON-OFF'),
            'no_additional_heldout_exceedances':r['heldout'][p]['at_or_above_threshold']<=r['heldout']['legacy']['at_or_above_threshold']}
        assert cond==c['development_conditions'] and all(cond.values())==c['development_gate_passed']
    direct={'signal_gain_cases':[],'signal_loss_cases':[],'additional_control_leakage_cases':[],'removed_control_leakage_cases':[]}
    for i in range(72):
        a,b=lookup[i,'neighbor2'],lookup[i,'neighbor9']
        av=a['association']['recovered'] if a['signal_present'] else a['control_leakage']
        bv=b['association']['recovered'] if b['signal_present'] else b['control_leakage']
        if bv and not av:direct['signal_gain_cases' if a['signal_present'] else 'additional_control_leakage_cases'].append(i)
        if av and not bv:direct['signal_loss_cases' if a['signal_present'] else 'removed_control_leakage_cases'].append(i)
    null_rows=[];baseline_rows=[]
    for p in POLICIES:
        cal=read_sealed(OUT/f'{p}.calibration.json');h=read_sealed(OUT/f'{p}.heldout.json')
        assert len(cal['null_maxima'])==len(h['null_maxima'])==128
        cut=r['heldout'][p]['threshold']
        assert cut==max(10.,max(cal['null_maxima']))
        assert sum(x>=cut for x in h['null_maxima'])==r['heldout'][p]['at_or_above_threshold']
        null_rows.append(f"| {p} | {max(cal['null_maxima']):.6f} | {cut:.6f} | {max(h['null_maxima']):.6f} | {r['heldout'][p]['at_or_above_threshold']}/128 |")
        a=read_sealed(OUT/f'{p}.baseline.json')['audit']
        baseline_rows.append(f"| {p} | {a['on_retained']} | {a['off_retained']} | {a['final_diagnostic_survivors']} | {sum(a['masked_cell_counts'].values())} |")
    anchors=read_sealed(OUT/'input_anchors.json')
    assert len(anchors['cache_inventory'])==48 and all(x['anchor_exact'] for x in anchors['cache_inventory'])
    audit=write_sealed(OUT/'artifact_validation.json',{'complete':True,'result_sha256_verified':r['result_sha256'],
        'frozen_dependencies_verified':len(cfg['pinned_sha256']),'scientific_config_unchanged_by_startup_amendment':True,
        'sealed_case_records':72,'endpoints':216,'signal_present_endpoints':144,'control_endpoints':72,
        'three_policy_input_identities_exact':True,'all_96_original_arrays_exact':True,'native_ON_OFF_cache_gathers_exact':48,
        'compact_member_decisions':members,'maximum_masked_ON_cells_by_policy':max_masked,
        'summary_and_development_gates_recomputed':True,'neighbor9_vs_neighbor2_descriptive':direct,'general_adoption_qualified':False})
    st=['| Signal case | Legacy retained / physical / recovered | Neighbor2 retained / physical / recovered | Neighbor9 retained / physical / recovered |','|---|---:|---:|---:|']
    ct=['| Constructed control | Legacy leaking cases / final members | Neighbor2 leaking cases / final members | Neighbor9 leaking cases / final members |','|---|---:|---:|---:|']
    for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
        rows=[next(x for x in summary if x['policy']==p and x['case_type']==kind) for p in POLICIES]
        fields=('retained_truths','physical_truths','recovered') if rows[0]['signal_present'] else ('control_leakage_cases','final_diagnostic_survivors')
        line='| '+kind+' | '+' | '.join(' / '.join(str(x[k]) for k in fields) for x in rows)+' |'
        (st if rows[0]['signal_present'] else ct).append(line)
    multiplicity=['| Policy | Mixed truths recovered | Final members | Associated final members | Other final members |','|---|---:|---:|---:|---:|']
    for policy in POLICIES:
        mixed=[e for e in endpoints if e['mask_policy']==policy and e['case_type']=='mixed']
        count=sum(e['final_diagnostic_survivors'] for e in mixed)
        associated=sum(e['association']['associated_final_survivors'] for e in mixed)
        recovered=sum(e['association']['recovered'] for e in mixed)
        multiplicity.append(f'| {policy} | {recovered}/8 | {count} | {associated} | {count-associated} |')
    comparisons=[];details=[]
    for p,c in r['comparisons'].items():
        comparisons.append(f"- **{p}**: {len(c['signal_gain_cases'])} signal gains, {len(c['signal_loss_cases'])} signal losses; {len(c['additional_control_leakage_cases'])} added and {len(c['removed_control_leakage_cases'])} removed leaking control cases. Development gate: **{'passed' if c['development_gate_passed'] else 'failed'}**.")
        details.append(f"### {p}\n\n"+'\n'.join(f'- {k.replace("_"," ")}: {v}.' for k,v in c.items() if k!='development_conditions')+'\n\n'+'\n'.join(f'- {k.replace("_"," ")}: **{v}**.' for k,v in c['development_conditions'].items()))
    totals={p:sum(e.get('association',{}).get('recovered',False) for e in endpoints if e['mask_policy']==p) for p in POLICIES}
    all_pass=all(c['development_gate_passed'] for c in r['comparisons'].values())
    next_text=('Both alternatives pass this finite development panel. Mixed-output multiplicity still needs explanation. The next useful step is a prospectively frozen comparison of matched signal-only, strong-component-only and combined inputs at the same strength and location, followed by independent carrier/activity combinations and additional observing sequences.' if all_pass else 'At least one alternative fails the predeclared development gate. Preserve the complete failures and identify whether masking, ON/OFF rejection or receiver-alias logic controls them before proposing a new rule. Freeze any subsequent change and evaluate it on additional combinations or observations; do not tune this completed panel.')
    report=f'''# M43U: native signals and interference at additional carriers

The completed three-policy experiment has **72 shared native inputs and 216 detector executions**. It recovers {totals['legacy']}/48 signal-present cases with legacy, {totals['neighbor2']}/48 with neighbor2, and {totals['neighbor9']}/48 with neighbor9. Signal recovery and interference leakage are reported separately. No astronomical candidate is claimed.

{chr(10).join(comparisons)}

## Signal recovery

Every row has eight cases per policy. Counts show retained truth, truth passing physical vetoes, and final rank-qualified recovery. All true signals have nominal strength 32; these are not measured output SNRs. The mixed cases also include a stronger nearby component.

{chr(10).join(st)}

## Constructed interference controls

Every row has eight cases per policy. The first count is the number of cases with at least one final diagnostic survivor; the second counts all such members, which can be many correlated representations of the same input. These fractions are not physical false-alarm probabilities.

{chr(10).join(ct)}

Single-epoch controls add strength 32 in one active epoch only. Supported-spike controls also add strength 4 six proxy bins away in the other active epochs. ON-OFF controls add strength 32 along the same anchor hypothesis in active ON and corresponding OFF scans. These are constructed negative controls with known origin, not measurements of the terrestrial interference population. Mixed cases add a strength-128 component twelve bins from a combined true signal, in the first active epoch.

The shared ON-OFF failure is case 61: injection center 3584, anchor template 0, all three epochs active. Its three surviving members are identical across policies, at carriers 3610–3612 with width 65 and SNR 10.115–10.334. The extra neighbor9 failure is supported-spike case 69: one width-9 member at carrier 3588, template 36, activity subset [0, 2], SNR 10.208. All these records retain `pending_receiver_alias_evaluation` and `scientific_candidate=false`. Here “final” means passing the evaluated physical vetoes and diagnostic rank cut; it does not mean complete receiver-alias clearance. These ledger facts localize the failures but do not establish their causal mechanism. A subsequent diagnostic must trace the paired-OFF and receiver decisions before modifying any veto.

Maximum cropped ON mask occupancy across cases is {json.dumps(max_masked)} cells. All per-case ON/OFF counts and physical dispositions are in the ledger. Mask counts obey neighbor9 <= neighbor2 <= legacy throughout. Equal final recovery alone does not prove that masks or earlier rejection stages behave identically.

## Mixed-input member multiplicity

{chr(10).join(multiplicity)}

Association here requires the defined truth's exact activity subset and <=20 Hz center-track agreement at every active integration. Other members can include correlated template/width copies, different activity subsets, displaced responses or interference-induced outputs. This accounting does not identify their physical origin. The predeclared development gate constrains true-signal losses and the 24 pure-control case outcomes; it does not constrain total member multiplicity in mixed cases. Extra members must therefore remain visible even if that gate passes. Matched signal-only/interference-only component ablations at the same strength and location would be needed for causal assignment.

## Complete paired changes and declared decision conditions

The direct descriptive neighbor9-versus-neighbor2 comparison has signal-gain cases {direct['signal_gain_cases']}, signal-loss cases {direct['signal_loss_cases']}, additional leaking controls {direct['additional_control_leakage_cases']}, and removed leaking controls {direct['removed_control_leakage_cases']}. This does not add a new decision gate.

Case indices below refer to the frozen `cases` inventory in the configuration, which gives the carrier, activity subset, anchor and all native components.

{chr(10).join(details)}

{next_text} General adoption remains unqualified even when a development gate passes.

## Conditional calibration and baseline

| Policy | Training maximum | Threshold | Held-out maximum | Held-out >= threshold |
|---|---:|---:|---:|---:|
{chr(10).join(null_rows)}

There are 128 training and 128 held-out shifts shared by all policies: 256 unique new rows and 768 policy-specific maxima. All 768 prior M43R/M43T rows were excluded. Masks are estimated on the original full-support baseline, cropped, then co-rolled with scores; masks are not re-estimated after scrambling. All thresholds were sealed before held-out and injection evaluation. These correlated within-sequence pre-veto maxima do not calibrate the constructed interference population and do not establish an independent physical FAP.

| Baseline policy | ON retained | OFF retained | Final diagnostic survivors | Cropped masked cells, ON+OFF |
|---|---:|---:|---:|---:|
{chr(10).join(baseline_rows)}

The three baseline executions are reported separately and are not included in the 216 injection endpoints or counted as independent noise realizations.

## Scope and reproducibility

Four new injection centers, score indices 512, 1536, 2560 and 3584, are crossed with two anchor templates. Each center uses one predeclared activity subset, so carrier and activity remain confounded. This is 37 templates and 4,097 central score carriers in the same three ON/OFF pairs as M43T; it adds injection locations, not observing coverage. It is not a full-bank survey or a blind completeness estimate. Native rounding, fractional placement, template offset and one-channel smearing have separate cases plus a combined profile, but only one true-signal strength is tested.

All additions occur after fixed normalization and before complete native filtering/gathering. Overlapping components are summed in declared float32 order before filtering. ON additions enter receiver signatures; OFF additions enter OFF retention and paired-OFF measurements. All 96 original arrays and 48 native ON/OFF cache/gather identities match. The finite sinc-squared/smearing prescription is a defined model, not a measured channelizer response.

The initial startup stopped on a misspelled NumPy version attribute, before any data preparation or score evaluation. [The published startup amendment](MILESTONE_43U_STARTUP_AMENDMENT.md) fixes only this guard and retains the [original failure log](results_m43u_signal_interference/startup_failure_initial.log). All scientific configuration values are unchanged. Six focused numerical tests and the additional startup guard test pass; unchanged older evidence is reused.

Artifact validation verifies all {len(cfg['pinned_sha256'])} pinned files, 72 full sealed case records, 216 endpoints, identical three-policy inputs/overlays, recomputed summaries and decision gates, and {members:,} compact member decisions. No cap was exhausted in the completed result. The numerical run took **{r['wall_seconds']:.1f} seconds**. It used retained inputs and made no telescope requests.

- Original prospective freeze: `6091ff8907e4e882e7227ee6e9ec97c98dfe5331`.
- Corrected public execution freeze: `{r['freeze_commit']}`.
- Configuration SHA-256: `{r['config_sha256']}`.
- Result seal: `{r['result_sha256']}`.
- Compressed ledger SHA-256: `{r['ledger_sha256']}`.
- Uncompressed ledger SHA-256: `{r['ledger_uncompressed_sha256']}`.
- [Plan](MILESTONE_43U_SIGNAL_INTERFERENCE_PLAN.md), [complete result](results_m43u_signal_interference/result.json), [case ledger](results_m43u_signal_interference/case_audits.jsonl.gz), [artifact validation](results_m43u_signal_interference/artifact_validation.json), [run log](results_m43u_signal_interference/live_run.log), and [checksum manifest](RESULTS_MANIFEST_M43U_SIGNAL_INTERFERENCE.sha256).

With retained verified inputs and no completed result already present:

```bash
PYTHONPATH=src:scripts OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/m43u_signal_interference.py \\
  --freeze-commit {r['freeze_commit']} \\
  --anchor-root /path/to/anchors --source-root /path/to/sources \\
  --checkpoint-root /path/to/m43u-case-checkpoints
```

Restart checkpoints must match the freeze, configuration, complete case and all three calibration bindings. Previous M43S/M43T results remain intact.
'''
    (ROOT/'MILESTONE_43U_SIGNAL_INTERFERENCE_RESULT.md').write_text(report)
    print(json.dumps({'validation':audit,'signal_recovery':totals,'comparisons':r['comparisons']},indent=2))


if __name__=='__main__':
    main()
