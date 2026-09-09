"""Summarize the closed, audited M43AD experiment; no decision changes."""
import gzip
import json
from pathlib import Path
from m43e_economical_bank import read_sealed, write_sealed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43ad_geometry'


def main():
    result = read_sealed(OUT/'result.json'); audit = read_sealed(OUT/'audit.json')
    assert result['complete'] and audit['passed']
    cfg = json.loads((ROOT/'config/m43ad_geometry.json').read_text())
    original = read_sealed(ROOT/'results_m43ab_attribution/result.json')
    prior_payloads = {i['native_payload_identity'] for i in original['inventory']}
    panels = {c['name']: c['panel'] for c in cfg['cases']}
    fresh = [i for i in result['inventory'] if panels.get(i['name']) == 'fresh']
    fresh_payloads = {i['native_payload_identity'] for i in fresh}
    detail = []; records = {}
    for item in result['inventory']:
        if item['name'] == 'baseline': continue
        rec = json.loads(gzip.decompress((ROOT/item['file']).read_bytes()))
        records[item['name']] = rec
        m = {r['record_id']: r for r in rec['reference_audit']['members']}
        final = {}
        for p, ds in rec['policy_decisions'].items():
            final[p] = [d['record_id'] for d in ds if d['passes_evaluated_physical_vetoes'] and m[d['record_id']]['meets_diagnostic_rank_cut']]
        rows = {e['policy']:e for e in rec['endpoints']}
        detail.append(dict(name=item['name'],panel=rec['case']['panel'],case_type=rec['case']['case_type'],
            signal_present=rec['case']['signal_present'],
            recovered={p:r['recovered'] for p,r in rows.items()},
            final_counts={p:len(ids) for p,ids in final.items()},
            associated_final_widths={p:sorted({m[rid]['spectral_width_channels'] for rid in ids
                if rid in rows[p]['truth_association']['associated_record_ids']}) for p,ids in final.items()},
            final_member_widths={p:sorted({m[rid]['spectral_width_channels'] for rid in ids}) for p,ids in final.items()},
            incomplete_profiles=sum(not r['complete'] for e in rec['geometry_confirmation_evidence'] for r in e['aligned'])))
    write_sealed(OUT/'case_summary.json',dict(cases=detail,
        fresh_input_labels=len(fresh),fresh_distinct_payloads=len(fresh_payloads),
        fresh_payload_overlap_with_M43AB=len(fresh_payloads & prior_payloads)))
    examples = []
    for name,rid in [
        ('ab_z138','7c28beae7230358376f59a7b856b74c2a766c0694b85da322dd8fcef9f706f9a'),
        ('ab_z158','2fa0bc2996c06336506167fb8516ab87b62d2191acf483cec8e9a31369af8107'),
        ('new038','5cb19beedab4d8911b48cdf7ce85ff30854238b49561dd96066fc0c1d75a37be')]:
        rec = records[name]
        member = next(m for m in rec['reference_audit']['members'] if m['record_id'] == rid)
        ev = next(e for e in rec['geometry_confirmation_evidence'] if e['record_id'] == rid)
        rows = []
        for row in ev['aligned']:
            short = {k:v for k,v in row.items() if k != 'profile'}
            if row.get('profile',{}).get('complete'):
                p = row['profile']; w = p['radius_proxy_bins']
                short.update({k:p[k] for k in ('center_shift_bins','correlation','on_track_span_hz','off_track_span_hz')})
                short['aligned_OFF_center'] = p['aligned_off_values'][w]
            rows.append(short)
        examples.append(dict(name=name,record_id=rid,
            member={k:member[k] for k in ('template_index','proxy_carrier_index','spectral_width_channels','active_epochs_zero_based')},
            remaining=ev['remaining'],aligned=rows,
            decisions={p:next(d for d in ds if d['record_id']==rid) for p,ds in rec['policy_decisions'].items()}))
    write_sealed(OUT/'mechanism_examples.json',dict(
        interpretation='Post-run excerpts of unchanged sealed evidence; no new endpoint or threshold.',examples=examples))
    totals = audit['totals']
    lines = ['# M43AD: width/track attribution and receiver-aligned ON/OFF comparison', '',
        'Completed 9 September 2026. The predeclared development experiment is closed.',
        f"Public scientific freeze: `{result['freeze_commit']}`.",
        'The source, plan and tests were publicly verified before the first evaluation.', '',
        '**All three new policies fail their predeclared gates on both panels.**',
        'Geometry with the original OFF rule recovers two additional historical',
        'signals without adding leaking controls, but does not improve the additional',
        'panel. Receiver-aligned ON/OFF comparison recovers more signals while also',
        'admitting more controls and rejecting one signal retained by the centered',
        'combination. No policy is adopted.', '',
        '## Complete comparison', '',
        '**150 base executions and 1,500 paired policy endpoints**: 37 historical inputs',
        '(19 signal-present, 18 controls), 112 prospectively specified combinations',
        '(64 signal-present, 48 controls), and one separate unchanged baseline.',
        f"There are **{result['distinct_native_payloads']} distinct native payload inventories** overall.",
        f"The additional panel has {len(fresh_payloads)} distinct payloads, with {len(fresh_payloads & prior_payloads)} payload identities shared with M43AB.",
        'These are correlated interventions on one existing observing sequence, not',
        'independent astronomical observations or a physical false-alarm calibration.', '',
        '| Policy | Historical signals /19 | Historical leaking controls /18 | Additional signals /64 | Additional leaking controls /48 |',
        '|---|---:|---:|---:|---:|']
    for p in cfg['policies']:
        h = next(s for s in result['summary'] if s['panel'] == 'historical' and s['policy'] == p)
        f = next(s for s in result['summary'] if s['panel'] == 'fresh' and s['policy'] == p)
        lines.append(f"| `{p}` | {h['recovered_signals']} | {h['leaking_controls']} | {f['recovered_signals']} | {f['leaking_controls']} |")
    lines += ['', 'A recovered signal means at least one final member passes the unchanged',
        'activity/track association criterion. It is not proof of the physical origin',
        'of every retained member. A leaking control has any final rank-eligible member.',
        'The added historical control is M43AB fresh032; earlier M43AB /17 control',
        'denominators remain unchanged in their original report.', '',
        '## What the comparison establishes', '',
        'Against the original combined rule, geometry plus the original OFF rule',
        'raises historical recovery from 8/19 to 10/19, with the same three leaking',
        'controls. It restores `ab_z171` at widths 9/17 and `ab_z281` at widths',
        '1/3/5/9. On the additional panel, both rules recover 55/64 signals and',
        'leak the same three control inputs: `new004`, `new018`, `new046`.',
        'Those three labels share one native payload; label counts are not three',
        'independent interference realizations.', '',
        'The aligned combination recovers 13/19 historical signals but leaks 8/18',
        'controls, compared with 13/19 and 5/18 for the centered combination.',
        'It removes `ab_z138` and `ab_fresh032`, but newly leaks `ab_z148`,',
        '`ab_z158`, `ab_z198`, `ab_z278`, and `ab_z318` relative to that combination.',
        'It still loses the weak unequal-epoch `ab_z260/261/265` family.', '',
        'On the additional panel, the aligned combination recovers 56/64 signals',
        'and leaks 6/48 controls. The centered combination recovers 57/64 and leaks',
        '5/48. Alignment removes the `new032` control but adds `new076` and',
        '`new104`, and loses the previously recovered width-17 signal in `new038`.',
        'It preserves `new003`, which the original combined rule loses.',
        'Among the 32 predeclared signal-only/mixed pairs, mixed-case recovery is',
        'lost in seven pairs for the original and geometry/original-OFF combinations,',
        'five for the centered combination, and six for the aligned combination.', '',
        '## Mechanisms and limits', '',
        'The post-run excerpts in `mechanism_examples.json` identify exact members',
        'inside the original sealed inputs; they do not add an evaluated policy.',
        'For the width-129 survivor in `ab_z138`, fixed receiver-coordinate shifts',
        'of about 29–30 bins give correlations 0.739701, 0.810251 and 0.940601.',
        'The latter two epochs trigger the predeclared ON/OFF veto.', '',
        'That successful stationary-receiver example does not generalize to all',
        'moving ON/OFF controls. The recorded `ab_z158` survivor has only one',
        'qualifying OFF maximum (6.307977); its fixed shift is about -464.956 bins',
        'and its correlation is 0.774079. It remains below the unchanged 0.8 floor,',
        'whereas the original OFF-window rule rejects this control.', '',
        'The additional `new038` signal exposes a second attribution problem.',
        'Its surviving width-17 member passes geometry and remaining-epoch support.',
        'In zero-based epoch 2 the original OFF maximum is 8.078562 and the aligned',
        'correlation is 0.955689, so the frozen rule rejects the signal. However,',
        'the compared OFF profile is displaced by -474.528 bins and its center is',
        'only 3.255846. The rule combines a qualifying maximum in the original',
        'window with shape agreement at a different coordinate; it does not require',
        'them to identify the same response. This is evidence against treating',
        'that conjunction as sufficient physical attribution. The stored evidence',
        'does not by itself identify the physical cause of the aligned background.', '',
        'These examples motivate the next integrated study: make the OFF amplitude,',
        'shape and hypothesized track refer to one explicitly attributed response,',
        'while retaining both stationary-receiver and moving-track alternatives.',
        'Simply adding another veto would leave the signal-loss counterexample',
        'unresolved. Specify the joint rule and its signal/control costs before new',
        'evaluation; all M43AD cases are historical after this result. Continue to',
        'treat weak-epoch/background support as a separate requirement. No new',
        'threshold, combined hypothesis or calibration is validated here.', '',
        '## Predeclared gates', '',
        '`no_signal_loss` and strict control-leak reduction compare with the',
        'original `neighbor9` reference, not with `combined`. Preservation of the',
        'centered combination is a separate additional requirement. All ten policies',
        'have zero baseline survivors. On the additional panel, geometry alone',
        'retains one false control truth association; the two new combinations',
        'have none but still leave control members.', '',
        '| Panel and policy | Passed | Failed requirements |', '|---|---|---|']
    for name, comparison in result['comparisons'].items():
        failed = ', '.join(k for k,v in comparison['conditions'].items() if not v) or 'none'
        lines.append(f"| `{name}` | {comparison['development_gate_passed']} | {failed} |")
    lines += ['', 'Full gain/loss names, control additions/removals and preservation costs against',
        'the M43AB centered combination are in `result.json` (lossless archive).',
        '`case_summary.json` lists all cases and final associated widths.',
        '`paired_signal_costs.json` preserves every additional signal-only/mixed pair.', '',
        '## Reproducibility and audit', '',
        f"The audit verifies {audit['pinned_files']} frozen dependencies, {totals['inputs']} sealed inputs,",
        f"{totals['policy_decisions']:,} policy-member decisions and {totals['direct_native_checks']:,} direct native comparisons.",
        f"All {totals['exact_historical_inputs_including_baseline']} historical/baseline inputs replay all seven old policies exactly.",
        f"An exhaustive oracle checks {totals['exhaustive_cross_identity_pairs']:,} cross-identity alias pairs without bucket pruning.",
        f"All {totals.get('reconstructed_profiles',0):,} queried complete aligned profiles reproduce from their stored coordinates,",
        f"interpolation brackets and values. Incomplete profile requests: {totals.get('incomplete_profiles',0)}.",
        'Repeated member/epoch queries and arithmetic checks are not independent events.', '',
        'All six original source receipts, 96 original arrays and 48 native gathers',
        'match. Eight focused tests pass. Python 3.12.14 / NumPy 2.3.5 preserves exact',
        'historical replay despite the Python patch change. No new null rows were',
        'generated; the original M43Z calibration and thresholds were restored.',
        f"Recorded evaluation wall time: {result['wall_seconds']:.3f} seconds.", '',
        '```bash', 'python scripts/m43z_restore_ledger.py', 'python scripts/m43ab_archive.py restore',
        'python scripts/m43ad_archive.py restore', 'PYTHONPATH=src:scripts python scripts/m43ad_audit.py', '```', '',
        'The archive restores original gzip bytes and verifies their SHA256 values.',
        'Full native re-execution also needs the original source/anchor runtime.', '',
        '## Claim boundary', '', 'No production rule is adopted. No additional observing coverage, independent',
        'physical false-alarm probability or astronomical candidate is claimed.',
        'Original M43X/Z/AB failed gates and denominators remain public. Weak',
        'unequal-epoch support and background-supported confirmation remain distinct',
        'questions; the 5.5 floor was not tuned to remove a particular control.', '']
    (ROOT/'MILESTONE_43AD_GEOMETRY_RESULT.md').write_text('\n'.join(lines))
    print(json.dumps(dict(report_written=True,fresh_distinct_payloads=len(fresh_payloads),
        fresh_overlap_with_M43AB=len(fresh_payloads & prior_payloads))))


if __name__ == '__main__': main()
