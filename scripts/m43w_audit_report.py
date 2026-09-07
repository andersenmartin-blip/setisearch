"""Audit complete M43W decisions, associations and declared development gates."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
from m43b_active_support import seal
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from m43s_profile_sensitivity import endpoint
from seti_repeater import detector_m43u as detector,search_v0p6 as core

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43w_confirmation'
POLICIES=('neighbor9','off_window','epoch_confirmation','combined')

def main():
    r=read_sealed(OUT/'result.json');cfg=json.loads((ROOT/'config/m43w_confirmation.json').read_text())
    config_sha=hashlib.sha256((ROOT/'config/m43w_confirmation.json').read_bytes()).hexdigest()
    for p,h in cfg['pinned_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    prior=set()
    for path in ('config/m43r_joint_calibration.json','config/m43t_mask_comparison.json','config/m43u_prior_neighbor2_shifts.json','config/m43u_signal_interference.json'):
        c=json.loads((ROOT/path).read_text());prior.update(tuple(x) for x in c['calibration_shifts']+c['heldout_shifts'])
    fresh=[tuple(x) for x in cfg['training_shifts']+cfg['heldout_shifts']]
    assert len(prior)==1024 and len(set(fresh))==256 and not set(fresh)&prior
    for zero,a,b in fresh:assert zero==0 and min(a,4097-a,b,4097-b,abs(a-b),4097-abs(a-b))>=128
    train=read_sealed(OUT/'calibration.json');held=read_sealed(OUT/'heldout.json');anchors=read_sealed(OUT/'anchors.json')
    assert len(train['null_maxima'])==len(held['null_maxima'])==128
    cut=max(10.,max(train['null_maxima']))
    assert cut==r['heldout']['threshold'] and r['heldout']==held['diagnostic']
    assert sum(v>=cut for v in held['null_maxima'])==r['heldout']['at_or_above_threshold']
    assert anchors['all_96_arrays_exact'] and anchors['all_48_native_gathers_exact']
    assert len(anchors['queries'])*3==anchors['OFF_window_scalar_comparisons']==4440
    packed=(OUT/'case_audits.jsonl.gz').read_bytes();raw=gzip.decompress(packed)
    assert hashlib.sha256(packed).hexdigest()==r['ledger_sha256'] and hashlib.sha256(raw).hexdigest()==r['ledger_uncompressed_sha256']
    ledger=[json.loads(x) for x in raw.splitlines() if x.strip()];assert len(ledger)==192
    _,_,_,metadata,basis,parent,_,_=build_context();bank,table,_=detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis)
    _,grid,_=grid_context();factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    endpoints=[];members=0;policy_member_decisions=0;loss_evidence=[]
    for rec,case in zip(ledger,cfg['cases']):
        assert rec['result_sha256']==seal({k:v for k,v in rec.items() if k!='result_sha256'})
        assert rec['case']==case and rec['freeze_commit']==r['freeze_commit'] and rec['config_sha256']==config_sha
        assert rec['binding']==train['binding'] and rec['reference_audit']['overlay']['components']==case['components']
        base=rec['reference_audit'];evidence=rec['confirmation_evidence'];members+=len(base['members'])
        assert len(evidence)==len(base['members']) and set(rec['policy_decisions'])==set(POLICIES)
        matched=endpoint(base,case['reference_truth'],grid,factors,basis,case['strength'],'audit')
        associated=set(matched['associated_record_ids'])
        reference_final={m['record_id'] for m in base['members'] if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}
        for p,e in zip(POLICIES,rec['endpoints']):
            assert (e['policy'],e['case_index'],e['case_type'],e['strength'],e['signal_present'])==(p,case['case_index'],case['case_type'],case['strength'],case['signal_present'])
            final=set();physical=set()
            assert len(rec['policy_decisions'][p])==len(base['members'])
            for m,proof,d in zip(base['members'],evidence,rec['policy_decisions'][p]):
                assert d['record_id']==m['record_id']==proof['record_id']
                values=[m['epoch_values_at_proxy_carrier'][i] for i in m['active_epochs_zero_based']]
                assert proof['minimum_active_ON_score']==min(values)
                assert proof['active_confirmation_passed']==all(v>=5.5 for v in values)
                off=proof['off_window'];assert off['active_epochs']==m['active_epochs_zero_based']
                radius=m['spectral_width_channels']//2;center=grid.score_slice.start+m['proxy_carrier_index']
                assert [off['radius_proxy_bins'],off['first_support_index'],off['stop_support_index']]==[radius,center-radius,center+radius+1]
                assert off['vetoed']==any(v>=5.5 for v in off['maxima'])
                reasons=[]
                if p in ('off_window','combined') and off['vetoed']:reasons.append('width_aware_OFF')
                if p in ('epoch_confirmation','combined') and not all(v>=5.5 for v in values):reasons.append('active_epoch_below_5p5')
                passing=m['passes_evaluated_physical_vetoes'] and not reasons
                assert d['m43w_rejections']==reasons and d['passes_evaluated_physical_vetoes']==passing
                if passing:
                    physical.add(m['record_id'])
                    if m['meets_diagnostic_rank_cut']:final.add(m['record_id'])
                policy_member_decisions+=1
            assert final<=reference_final and e['final_members']==len(final)
            a=e['truth_association'];assert set(a['associated_record_ids'])==associated
            assert a['associated_final_survivors']==len(final&associated) and a['recovered']==bool(final&associated)
            assert a['associated_physical_survivors']==len(physical&associated)
        if case['signal_present'] and rec['endpoints'][0]['truth_association']['recovered']:
            relevant=associated&reference_final
            for e in rec['endpoints'][1:]:
                if e['truth_association']['recovered']:continue
                by_id={d['record_id']:d for d in rec['policy_decisions'][e['policy']]}
                proof_by_id={d['record_id']:d for d in evidence}
                loss_evidence.append({'case_index':case['case_index'],'case_type':case['case_type'],
                    'strength':case['strength'],'score_index':case['score_index'],'local_template':case['local_template'],
                    'active_epochs':case['active_epochs'],'policy':e['policy'],
                    'lost_associated_members':[{'member':m,'new_decision':by_id[m['record_id']],
                        'confirmation_evidence':proof_by_id[m['record_id']]} for m in base['members'] if m['record_id'] in relevant]})
        endpoints.extend(rec['endpoints'])
    assert endpoints==r['endpoints'] and len(endpoints)==768
    assert sum(c['signal_present'] for c in cfg['cases'])==96
    assert len({(c['score_index'],tuple(c['active_epochs']),c['local_template']) for c in cfg['cases']})==16
    summary=[]
    for p in POLICIES:
        for strength in (12.,32.):
            for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                rows=[e for e in endpoints if (e['policy'],e['strength'],e['case_type'])==(p,strength,kind)]
                assert len(rows)==16
                summary.append({'policy':p,'strength':strength,'case_type':kind,'inputs':16,
                    'truth_associations':sum(e['truth_association']['recovered'] for e in rows),
                    'cases_with_final_members':sum(e['final_members']>0 for e in rows),'final_members':sum(e['final_members'] for e in rows)})
    assert summary==r['summary']
    write_sealed(OUT/'signal_loss_evidence.json',{'source_result':r['result_sha256'],'losses':loss_evidence})
    lookup={(e['case_index'],e['policy']):e for e in endpoints}
    for p,c in r['comparisons'].items():
        rows=[e for e in endpoints if e['policy']==p];loss=[];gain=[];added=[];removed=[]
        for e in rows:
            old=lookup[e['case_index'],'neighbor9']
            a,b=(old['truth_association']['recovered'],e['truth_association']['recovered']) if e['signal_present'] else (old['final_members']>0,e['final_members']>0)
            if b and not a:(gain if e['signal_present'] else added).append(e['case_index'])
            if a and not b:(loss if e['signal_present'] else removed).append(e['case_index'])
        assert [gain,loss,added,removed]==[c['signal_gains'],c['signal_losses'],c['added_leaking_controls'],c['removed_leaking_controls']]
        cond={'no_signal_case_loss':not loss,'no_increased_leaking_control_count':len(added)<=len(removed),
            'zero_ON_OFF_final_members':all(e['final_members']==0 for e in rows if e['case_type']=='ON-OFF'),
            'zero_interferer_only_false_associations':all(not e['truth_association']['recovered'] for e in rows if e['case_type']=='interferer-only'),
            'zero_shared_heldout_pre_veto_exceedances':r['heldout']['at_or_above_threshold']==0}
        assert cond==c['conditions'] and c['development_gate_passed']==all(cond.values())
        assert not gain and not added
    audit=write_sealed(OUT/'artifact_validation.json',{'complete':True,'pinned_files':len(cfg['pinned_sha256']),
        'sealed_inputs':192,'policy_endpoints':768,'reference_member_records':members,'policy_member_decisions':policy_member_decisions,
        'fresh_shift_rows':256,'excluded_prior_rows':1024,'new_scalar_OFF_anchors':4440,
        'all_policy_subsets_exact':True,'truth_associations_recomputed':True,'gates_recomputed':True,'result_seal':r['result_sha256']})
    aggregate=[];table_lines=['| Endpoint | Signal cases associated /96 | Leaking controls /96 | ON-OFF leaks /32 | Interferer-only false associations /32 | Development gate |','|---|---:|---:|---:|---:|---|']
    for p in POLICIES:
        rows=[e for e in endpoints if e['policy']==p]
        a={'policy':p,'signal_associations':sum(e['truth_association']['recovered'] for e in rows if e['signal_present']),
            'leaking_controls':sum(e['final_members']>0 for e in rows if not e['signal_present']),
            'ON_OFF_leaks':sum(e['final_members']>0 for e in rows if e['case_type']=='ON-OFF'),
            'false_associations':sum(e['truth_association']['recovered'] for e in rows if e['case_type']=='interferer-only'),
            'final_members':sum(e['final_members'] for e in rows)}
        aggregate.append(a);gate='reference' if p=='neighbor9' else str(r['comparisons'][p]['development_gate_passed'])
        table_lines.append(f"| {p} | {a['signal_associations']} | {a['leaking_controls']} | {a['ON_OFF_leaks']} | {a['false_associations']} | {gate} |")
    detail=['| Strength / input | Neighbor9 | OFF window | Epoch confirmation | Combined |','|---|---:|---:|---:|---:|']
    for strength in (12.,32.):
        for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
            rows=[next(s for s in summary if (s['policy'],s['strength'],s['case_type'])==(p,strength,kind)) for p in POLICIES]
            field='truth_associations' if kind in ('nearest','combined','mixed','interferer-only') else 'cases_with_final_members'
            detail.append(f'| {strength:g} / {kind} | '+' | '.join(f'{s[field]}/16' for s in rows)+' |')
    gates=[]
    for p,c in r['comparisons'].items():
        gates.append(f"### {p}\n\nSignal loss cases: {c['signal_losses']}. Removed leaking-control cases: {c['removed_leaking_controls']}.\n")
        gates.extend(f'- {k}: **{v}**.' for k,v in c['conditions'].items())
    report=f'''# M43W: prospective OFF-window and active-epoch confirmation

Completed **192 native inputs, 192 shared base detector executions and 768
paired policy endpoints**. One uninjected execution/four endpoints is separate.
The protocol, code, complete panel and gates were public before scoring.
No candidate or general adoption is claimed.

**All three alternatives fail the predeclared development gate.** Active-epoch
confirmation removes all18 leaking-control cases and all3 absent-truth
associations, but loses two of the reference's80 signal-associated cases.
The same-width OFF-window addition changes no final member set in this panel.
It also leaves the three false associations, so it fails its own gate.

## Complete prospective comparison

{chr(10).join(table_lines)}

Signal associations use the unchanged exact activity subset and <=20 Hz
maximum center-track residual. They are not proof of causal signal recovery;
the interferer-only controls explicitly measure absent-truth confusion.
Controls count cases with any final member; member multiplicity is reported
separately in the complete result. Nonincrease of control leakage is automatic
for these additive predicates, so that condition cannot establish success alone.

## Strength and morphology

Rows nearest/combined/mixed count signal associations. Interferer-only rows
count false associations with the absent combined truth. Supported-spike and
ON-OFF rows count cases with any final diagnostic survivor. Every entry has
16 inputs at the listed strength.

{chr(10).join(detail)}

Each of the 16 strata crosses two new carrier centers 768/3328, all four activity
subsets and two anchor templates. Strengths 12/32 are nominal native injection
strengths, not measured output SNRs. Mixed inputs add a single-epoch component
with four times the signal strength, 12 proxy bins away. Signal-only and that
exact interferer-only input are both present. Supported spikes add strength S/8
six bins away in other active epochs; ON/OFF components have equal strength S.

## What changes and what is shared

All endpoints start from the unchanged neighbor9 mask and complete detector
path. OFF-window adds a >=5.5 veto over the same-width paired-OFF proxy-bin
neighborhood of radius `width//2`, using full support without clipping/wrapping.
Epoch confirmation requires >=5.5 in every declared active ON epoch. Combined
applies both. Predicates run after the existing retention and physical/alias
stages; upstream alias witness sets are shared, not recomputed after rejection.

No alternative lowers the score threshold or introduces new retained members.
The four endpoints are computed from one base execution per input and are
paired, not independent runs or noise realizations. Alternative final sets
are exact subsets of the reference. The stronger active requirement can reject
faint or uneven signals; its measured cost must remain visible.

## Frozen development conditions

{chr(10).join(gates)}

A failed condition is not relaxed after evaluation. A passing development
panel would still require broader and independent validation. Earlier M43U/V
counts and failures remain unchanged; exposed V cases 35/44/61/69 are not part
of this panel.

Every lost signal case has a [member-level rejection record](results_m43w_confirmation/signal_loss_evidence.json),
including its per-epoch scores, OFF-window measurements and exact new reasons.
This preserves the distinction between total signal strength and the weakest
declared active epoch. No threshold is adjusted to remove these failures.

Cases73 and74 represent the SAME strength12 combined-profile truth, with and
without its stronger neighboring component: carrier768, anchor0, all three
epochs active. They are two paired input cases, not two independent signal
realizations. Both have two associated width3 members at carriers768/769,
with combined scores10.694390/11.062478. Their minimum active-epoch scores are
5.393839/5.422268, below5.5. The loss is therefore caused by the new absolute
per-epoch floor despite adequate total score; the OFF addition is not its cause.

The final member sets of OFF-window and reference are identical, as are those
of combined and epoch-confirmation. All32 ON-OFF cases already have zero final
members under the reference, so this panel provides no comparative repair
evidence for the old ON-OFF failure. Its absence at the new locations does not
erase the exposed M43V failure or establish that OFF rejection is generally sound.

## Next step

The next useful candidate is confirmation from the aggregate of the remaining
active epochs after removing the strongest epoch, rather than an absolute
floor on each one. That targets domination by one observation while potentially
retaining distributed weak evidence. This is a proposed endpoint, not a tested
repair. It must be explicitly defined and publicly frozen before evaluation,
including its threshold, fresh null rows and complete decision conditions.

Use new carrier/activity combinations and unequal active-epoch strengths,
with matched signal-only, interferer-only and mixed inputs. Retain false truth
associations and signal-case losses as separate gates. Keep cases73/74 and the
earlier V failures as exposed development examples. Any further OFF proposal
must address width/response information explicitly and preserve its false-veto
cost; merely reducing the5.5 floor to fit these exposed values is not qualified.

## Calibration, validation and scope

The 128 new training shifts have maximum {max(train['null_maxima']):.6f}; the
shared operational threshold is {cut:.6f}. The separate 128 held-out shifts have
maximum {max(held['null_maxima']):.6f}, with {r['heldout']['at_or_above_threshold']}/128
at or above threshold. All 256 new rows exclude 1,024 prior R/T/U rows.

This certificate uses the conservative >=3 pre-veto global maxima for all
four endpoints. Because the added cuts only reject, no lower threshold is
claimed. Masks are estimated on baseline full support, cropped and co-rolled;
they are not regenerated after scrambling. Shared pre-veto held-out evidence
does not measure OFF false-rejection rates or an independent physical FAP.

All 96 original arrays and 48 native ON/OFF gathers reproduce. Before calibration,
4,440 new OFF-window maxima at fixed real-data positions across all 37 templates,
eight widths and three epochs match scalar references, including score edges.
Four focused tests pass. Unchanged detector numerical evidence is reused.
Artifact validation verifies {len(cfg['pinned_sha256'])} pinned files, 192 sealed
inputs, 768 endpoints, {members:,} reference members and {policy_member_decisions:,}
policy decisions, recomputed associations and every development condition.
Runtime: {r['wall_seconds']:.1f} seconds; new telescope requests: 0.

This is the same 37-template, 4,097-carrier pilot in one observing sequence.
It adds injection combinations, not observing coverage, full-bank completeness,
arbitrary variability sensitivity or population constraints. The two signal
profiles and two strengths do not qualify all astrophysical signal classes.

- Public freeze: `{r['freeze_commit']}`.
- Result seal: `{r['result_sha256']}`.
- Ledger SHA-256: `{r['ledger_sha256']}`.
- [Plan](MILESTONE_43W_CONFIRMATION_PLAN.md), [complete result](results_m43w_confirmation/result.json),
  [ledger](results_m43w_confirmation/case_audits.jsonl.gz),
  [validation](results_m43w_confirmation/artifact_validation.json),
  [run log](results_m43w_confirmation/live_run.log), and
  [manifest](RESULTS_MANIFEST_M43W_CONFIRMATION.sha256).
'''
    for a,b in {'all18':'all 18','all3':'all 3','reference\'s80':'reference\'s 80',
        'Cases73':'Cases 73','and74':'and 74','strength12':'strength 12','carrier768':'carrier 768',
        'anchor0':'anchor 0','width3':'width 3','carriers768':'carriers 768','scores10.':'scores 10.',
        'below5.5':'below 5.5','All32':'All 32','cases73':'cases 73','the5.5':'the 5.5'}.items():report=report.replace(a,b)
    (ROOT/'MILESTONE_43W_CONFIRMATION_RESULT.md').write_text(report)
    print(json.dumps({'audit':audit,'aggregate':aggregate,'comparisons':r['comparisons']},indent=2))

if __name__=='__main__':main()
