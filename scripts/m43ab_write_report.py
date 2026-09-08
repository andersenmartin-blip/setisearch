"""Generate readable summaries only after the complete M43AB audit passes."""
import gzip
import json
from pathlib import Path
from m43e_economical_bank import read_sealed, write_sealed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43ab_attribution'
LABELS = {'neighbor9':'Unchanged neighbor9', 'off_window':'Original OFF window',
    'remaining_aggregate':'Original remaining-epoch aggregate', 'combined':'Original combination',
    'centered_receiver':'Centered receiver', 'centered_receiver_off_match':'Centered receiver + ON/OFF agreement',
    'centered_receiver_off_match_aggregate':'Centered receiver + agreement + aggregate'}


def load_case(name):
    return json.loads(gzip.decompress((OUT/'inputs'/(name+'.json.gz')).read_bytes()))


def run():
    result = read_sealed(OUT/'result.json'); audit = read_sealed(OUT/'artifact_validation.json')
    assert result['complete'] and audit['passed']
    lookup = {(s['panel'],s['policy']):s for s in result['summary']}
    critical = []
    for name in ('z171','z281','z324','z336','z346','z260','z261','z265'):
        r = load_case(name); members = {m['record_id']:m for m in r['reference_audit']['members']}
        row = dict(name=name)
        for policy in ('combined','centered_receiver_off_match_aggregate'):
            e = next(e for e in r['endpoints'] if e['policy'] == policy)
            associated = set(e['truth_association']['associated_record_ids'])
            kept = [members[d['record_id']] for d in r['policy_decisions'][policy]
                if d['record_id'] in associated and d['passes_evaluated_physical_vetoes']
                and members[d['record_id']]['meets_diagnostic_rank_cut']]
            row[policy] = dict(recovered=e['recovered'], associated_final_members=len(kept),
                              widths=sorted({m['spectral_width_channels'] for m in kept}))
        critical.append(row)
    write_sealed(OUT/'critical_signal_cases.json', dict(cases=critical))
    public = dict(milestone='M43AB', complete=True, public_freeze=result['freeze_commit'],
        inputs_including_baseline=149, endpoints_including_baseline=1043,
        distinct_native_payloads=result['distinct_native_payloads'], summary=result['summary'],
        comparisons=result['comparisons'], audit_passed=True, direct_native_checks=result['direct_native_checks'],
        prior_gates_remain_failed=True, general_adoption=False, astronomical_candidate=False)
    write_sealed(OUT/'summary.json', public)
    lines = ['# M43AB: five historical signal losses recovered, with interference costs', '',
        'Completed 8 September 2026. Candidate-centered receiver sampling and centered',
        'ON/OFF response agreement recover five signal-associated historical inputs',
        'lost by the original combined rule. This is a measured development gain,',
        'but the changed endpoints do not solve interference rejection.', '',
        '**No new rule is adopted, no astronomical candidate is claimed, and the',
        'original M43X/Z failed qualification gates remain.**', '',
        '## Scope and prospective freeze', '',
        f'The approved preparation tree was published as `{result["freeze_commit"]}`',
        '(byte-identical to approved local `1ee2069`, including `1a116c6`) and fetched',
        'and verified before any M43AB scoring. The README preparation update was',
        'published separately on main. Earlier upload rejections and the later owner',
        'approval remain documented; the M43AA retrospective status is unchanged.', '',
        '| Completed item | Count |', '|---|---:|',
        '| Historical M43Z inputs, selected after prior results | 36 |',
        '| Fresh native injection combinations fixed before scoring | 112 |',
        '| Separate uninjected baseline | 1 |',
        '| Base executions / paired policy endpoints, including baseline | 149 / 1,043 |',
        f'| Distinct native patch payloads, including baseline | {result["distinct_native_payloads"]} |',
        f'| Direct native centered-receiver arithmetic checks | {result["direct_native_checks"]:,} |', '',
        'All inputs use the same existing observing sequence. Fresh combinations are',
        'prospective within-sequence development inputs, not independent observations.',
        'M43Z calibration is restored exactly without new or recalculated null rows.',
        'The previous 0/128 held-out result is not a new M43AB false-alarm measurement.', '',
        '## Signal/control trade-off', '',
        '| Policy | Historical signals /19 | Historical leaking controls /17 | Fresh signals /64 | Fresh leaking controls /48 |',
        '|---|---:|---:|---:|---:|']
    for p,label in LABELS.items():
        h=lookup['historical',p]; f=lookup['fresh',p]
        lines.append(f'| {label} | {h["recovered_signals"]} | {h["leaking_controls"]} | {f["recovered_signals"]} | {f["leaking_controls"]} |')
    lines += ['',
        'On the fresh panel all seven policies recover 52/64 signal-present inputs.',
        'The original combination leaves 0/48 leaking controls; the new combination',
        'leaves 1/48 (interferer-only input fresh032, one final member). Thus the',
        'historical recovery gain does not demonstrate a sensitivity improvement on',
        'these fresh combinations, and the new combination regresses in control',
        'rejection. All three new endpoints fail their predeclared development gates.', '',
        'Signals here mean injected-truth associations under the unchanged exact',
        'activity-subset and 20 Hz maximum track-distance rule. An association alone',
        'does not establish which physical component produced the member. Counts of',
        'leaking controls count inputs with any final member, not independent events.',
        'The selected historical denominator must not replace M43Z’s original 224',
        'signal-present /128 pure-control denominator.', '',
        '## What was recovered, and what remains lost', '',
        '| Historical input | Original combination | New combination | New associated widths |',
        '|---|---|---|---|']
    for c in critical:
        old=c['combined']; new=c['centered_receiver_off_match_aggregate']
        lines.append(f'| {c["name"]} | {"Recovered" if old["recovered"] else "Lost"} | {"Recovered" if new["recovered"] else "Lost"} | '+(', '.join(map(str,new['widths'])) or 'None')+' |')
    lines += ['',
        'The mixed-input 170/171 and 280/281 families regain narrow members before',
        'the aggregation stage. In 171, the new combination retains 32 associated',
        'members with widths 1–65; in 281 it retains 13 with widths 1–9. At the',
        'paired template-0/carrier-3201/width-1 coordinate, the centered receiver',
        'signatures of 170 and 171 are identical despite the nearby interferer.',
        'This directly addresses the displaced-maximum effect exposed by M43AA.', '',
        'The three moderate-OFF losses 324/336/346 also regain their width-17',
        'associations. The weak unequal family 260/261/265 still fails aggregation;',
        'these are three labels sharing the same injected signal, not three',
        'independent physical signal realizations.', '',
        '## The controls expose the price of the changes', '',
        'Historical control 96 releases all 18 rank-eligible members previously',
        'rejected by receiver-alias matching. Its final combined count rises from',
        '19 to 30. A single centered sample therefore cannot replace the original',
        'receiver maximum without losing useful interference evidence.', '',
        'The response-agreement rule rejects seven of the eight original leaking',
        'ON-OFF inputs, but leaves input 138. Its surviving width-129 member has',
        'OFF maxima 5.774, 7.328 and 6.669, while the centered ON/OFF correlations',
        'are 0.658, −0.199 and 0.471. The fixed 0.8 agreement requirement prevents',
        'rejection despite the substantial OFF response. The original OFF-window',
        'rule rejects it. No threshold was adjusted after observing this result.', '',
        '## Predeclared development gates', '',
        '| Panel / new policy | Gate | Signal losses versus neighbor9 | Added leaking controls |',
        '|---|---|---|---|']
    for key, c in result['comparisons'].items():
        panel,p=key.split(':')
        lines.append(f'| {panel} / {LABELS[p]} | {"PASS" if c["development_gate_passed"] else "FAIL"} | '+(', '.join(c['signal_losses']) or 'None')+' | '+(', '.join(c['added_leaking_controls']) or 'None')+' |')
    lines += ['',
        'Full gain/loss lists, removed controls and false control associations are in',
        '`results_m43ab_attribution/summary.json`. Paired signal-only/mixed comparisons',
        'and every released alias-veto member are preserved in the record archive.', '',
        '## Validation and artifacts', '',
        f'The audit verifies {audit["pinned_files"]} frozen dependencies, 149 sealed inputs,',
        f'{audit["policy_member_decisions"]:,} per-member policy decisions, all 36 historical',
        'reference replays, the separate baseline, every truth association, all summary',
        'counts and all predeclared cost gates. The six original source receipts,',
        '96 original arrays and 48 native gathers match. Three synthetic tests pass.',
        f'Numerical runtime: {result["wall_seconds"]:.3f} seconds.', '',
        'Complete original input ledgers and the sealed full result are losslessly',
        'stored in `results_m43ab_attribution/archive/`. Run',
        '`python scripts/m43ab_archive.py restore` after cloning to reconstruct them.',
        'The archive checks all original file hashes; gzip reconstruction requires',
        'compatible Python/zlib output and stops on a mismatch. Archive metadata',
        'records the exact runtime. Closed run/audit logs and the result manifest',
        'are retained. No raw telescope files are republished.', '',
        '## Next useful task', '',
        'Retain both the candidate-centered measurement and the unrestricted receiver',
        'peak as separate evidence. Investigate a width- and track-aware attribution',
        'of the peak to the candidate, rather than replacing the entire alias witness',
        'with one sample. Include control 96, the fresh alias-release cases, the two',
        'recovered mixed families, historical ON-OFF input 138 and fresh032 explicitly.',
        'Inspect the surviving broad ON/OFF response before defining another fixed',
        'agreement endpoint. Do not lower the 0.8 or 5.5 floors on this completed',
        'panel. Any changed rule needs a new prospective freeze and additional',
        'evaluation inputs. The unresolved weak-epoch family remains a separate',
        'support-confirmation problem. Any future new null rows exclude all 1,792',
        'prior rows; preserve M43T history, original denominators and the LS branch.', '']
    (ROOT/'MILESTONE_43AB_ATTRIBUTION_RESULT.md').write_text('\n'.join(lines))
    print('Readable report and compact summary generated after passing audit')


if __name__ == '__main__': run()
