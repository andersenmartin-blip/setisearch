"""Summarize the completed frozen study; never fit or evaluate a new policy."""
from collections import Counter
import json
from pathlib import Path

from m43e_economical_bank import read_sealed, write_sealed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43af_response'
PANELS = ('training', 'historical_original', 'historical_additional')
LABELS = {
    'training': 'Training',
    'historical_original': 'Original historical panel',
    'historical_additional': 'Former additional panel (now historical)',
}
REFERENCES = {
    'neighbor9': 'Neighbor9',
    'centered_receiver_off_match_aggregate': 'Centered receiver + ON/OFF agreement + aggregation',
    'geometry_receiver_off_aggregate': 'Geometry + original OFF + aggregation',
    'geometry_receiver_aligned_off_aggregate': 'Geometry + aligned OFF + aggregation',
}
KNOWN_WEAK_CASES = ('ad_ab_z260', 'ad_ab_z261', 'ad_ab_z265')


def span(values):
    return [min(values), max(values)] if values else None


def format_span(values):
    if values is None:
        return 'None'
    if values[0] == values[1]:
        return f'{values[0]:.6f}'
    return f'{values[0]:.6f} to {values[1]:.6f}'


def main():
    result = read_sealed(OUT / 'result.json')
    audit = read_sealed(OUT / 'audit.json')
    decision = read_sealed(OUT / 'model_decision.json')
    publication = read_sealed(OUT / 'model_publication.json')
    reconciliation = read_sealed(OUT / 'historical_execution_reconciliation.json')
    archive = json.loads((OUT / 'complete_archive/manifest.json').read_text())
    assert result['complete'] and audit['passed']
    assert not result['model_feasible'] and result['boundary'] is None
    assert not result['native_validation_opened'] and not result['general_adoption_qualified']
    assert result['model_decision_sha256'] == decision['result_sha256']
    assert publication['remote_verified'] and publication['model_decision_sha256'] == decision['result_sha256']
    assert archive['source_result_sha256'] == result['result_sha256']
    assert archive['original_files'] == 508 and audit['files'] == len(result['inventory']) == 502
    groups = {}
    records = []
    for entry in result['inventory']:
        r = read_sealed(ROOT / entry['file'])
        assert r['result_sha256'] == entry['record_sha256']
        records.append(r)
        groups.setdefault(r['phase'], []).append(r)
    assert {p:len(rows) for p, rows in groups.items()} == result['phase_counts']
    assert set(groups) == {'baseline', 'null_training', *PANELS}
    phase_summary = {}
    totals = Counter()
    for phase, rows in groups.items():
        counts = Counter()
        for r in rows:
            counts.update(r['acquisition']['counts'])
            assert r['summary']['complete']
        assert counts['incomplete_profiles'] == counts['undefined_member_measurements'] == 0
        assert counts['requested_unique_profiles'] == sum(len(r['acquisition']['profiles']) for r in rows)
        assert counts['requested_unique_profiles'] == counts['newly_acquired_complete_profiles'] + counts['reused_complete_profiles']
        totals.update(counts)
        totals['direct_profile_native_checks'] += sum(len(r['direct_checks']) for r in rows)
        phase_summary[phase] = dict(inputs=len(rows), acquisition_counts=dict(counts),
            distinct_native_payloads=len({r['native_payload_identity'] for r in rows}),
            direct_profile_native_checks=sum(len(r['direct_checks']) for r in rows),
            upstream_reused_inputs=sum(bool(r['upstream_reused']) for r in rows))
        if phase in PANELS:
            signals = [r for r in rows if r['case']['signal_present']]
            controls = [r for r in rows if not r['case']['signal_present']]
            refs = {}
            for policy in REFERENCES:
                get = lambda r: next(e for e in r['original_endpoints'] if e['policy'] == policy)
                refs[policy] = dict(signal_cases=len(signals),
                    recovered_signals=sum(bool(get(r)['recovered']) for r in signals),
                    control_cases=len(controls),
                    leaking_controls=sum(get(r)['final_members'] > 0 for r in controls))
            phase_summary[phase]['original_reference_outcomes'] = refs
    weak_rows = []
    for name in KNOWN_WEAK_CASES:
        r = next(r for r in records if r['phase'].startswith('historical') and r['case']['name'] == name)
        associated = set(r['summary']['associated_record_ids'])
        weak = [m for m in r['acquisition']['measurements']
                if m['record_id'] in associated and not m['old_remaining']['remaining_passed']]
        coordinates = {m['record_id']:m['coordinate'] for m in r['summary']['members']}
        assert weak and all(coordinates[m['record_id']] is not None for m in weak)
        weak_rows.append(dict(name=name, associated_weak_members=len(weak),
            spectral_widths=sorted({m['spectral_width'] for m in weak}),
            old_remaining_score_range=span([m['old_remaining']['remaining_score'] for m in weak]),
            on_coordinate_range=span([coordinates[m['record_id']]['on'] for m in weak]),
            off_coordinate_range=span([coordinates[m['record_id']]['off'] for m in weak]),
            members=[dict(record_id=m['record_id'], width=m['spectral_width'],
                old_remaining_score=m['old_remaining']['remaining_score'],
                coordinate=coordinates[m['record_id']]) for m in weak]))
    weak_ids = {m['record_id'] for row in weak_rows for m in row['members']}
    summary = dict(source_result_sha256=result['result_sha256'], source_audit_sha256=audit['result_sha256'],
        model_decision_sha256=decision['result_sha256'], model_publication_commit=publication['commit'],
        phase_summary=phase_summary, acquisition_totals=dict(totals),
        original_source_native_null_probes=result['null_original_source_checks'],
        known_historical_weak_cases=weak_rows,
        distinct_known_weak_member_ids=len(weak_ids), model_selected=False,
        historical_endpoints_reused_without_detector_rerun=True,
        native_validation_opened=False, physical_false_alarm_probability_measured=False,
        astronomical_candidate_claimed=False,
        historical_log_completion_lines=reconciliation['unique_completion_lines_in_saved_log'],
        historical_records_not_in_saved_log=reconciliation['sealed_records_without_completion_lines'],
        complete_archive=dict(original_files=archive['original_files'], parts=len(archive['parts']),
            bytes=archive['archive_bytes'], sha256=archive['archive_sha256']))
    write_sealed(OUT / 'report_summary.json', summary)

    text = [
        '# M43AF complete: the frozen joint response rule does not qualify', '',
        '**All 502 prescribed evaluations and the independent whole-study audit are complete.**',
        'The 1,156-point training grid has no feasible boundary. No model is selected,',
        'no new detector is adopted, and both validation panels remain unopened.',
        'The remaining 261 historical response acquisitions were completed only after',
        'the immutable failed model decision was publicly verified. They preserve the',
        'original detector endpoints and are diagnostic measurements, not new detections.', '',
        '## Study accounting', '',
        '| Input group | Recorded inputs | Role |', '|---|---:|---|',
        '| Original historical panel | 149 (83 signals /66 controls) | Reused detector endpoints; response acquisition |',
        '| Former additional panel | 112 (64 signals /48 controls) | Historical diagnostic, not validation |',
        '| Baseline | 1 | Reused original input |',
        '| Training injection/control panel | 112 (64 signals /48 controls) | Frozen joint fitting panel |',
        '| Native training nulls | 128 | Native translations within the original observing sequence |',
        '| Total | 502 | 262 reused upstream inputs and 240 new upstream training/null executions |', '',
        'The validation injection panel (112 inputs) and held-out native nulls (128)',
        'were not opened. All data share one observing sequence; different injections',
        'and translations do not create independent astronomical observations.', '',
        '## Training failure remains unchanged', '',
        'The frozen rule accepts when x >= a and y < b. Here x is the',
        'remaining-epoch ON projection mean divided by sqrt(2w+1); y is the',
        'larger of the two OFF projection means, using the same scale. Signed',
        'values are retained. These coordinates are not calibrated SNR values.', '',
        'The required recovery set contains 57 specific signal cases. The independent',
        'auditor verifies all 1,156 frozen grid points against the same 241 training,',
        'baseline and native-null records. There are zero feasible points.', '',
        '| Requirement within the frozen grid | Best competing cost |', '|---|---|',
        '| No control, baseline or null members survive | At least 4 required signal cases are lost |',
        '| All 57 required signal cases are recovered | At least 8 of 48 control inputs retain members |', '',
        '![All frozen grid evaluations and the unachieved qualification target](results_m43af_response/figures/training_grid_tradeoff.svg)', '',
        'These are descriptive properties of this fixed grid, not a new optimized',
        'boundary or a proof against every continuous boundary or classifier.',
        'An absent model is not credited with rejecting every control, recovering a',
        'signal, or measuring zero-valued detector performance.', '',
        '## Unchanged reference outcomes', '',
        'The following counts are read from the sealed original endpoints. No M43AF',
        'learned endpoint exists, and the historical detector executions were not repeated.', '',
    ]
    for phase in PANELS:
        text.extend([f'### {LABELS[phase]}', '', '| Original reference | Signals recovered | Leaking control inputs |', '|---|---:|---:|'])
        for policy, label in REFERENCES.items():
            row = phase_summary[phase]['original_reference_outcomes'][policy]
            text.append(f"| {label} | {row['recovered_signals']}/{row['signal_cases']} | {row['leaking_controls']}/{row['control_cases']} |")
        text.append('')
    text.extend(['## The three inherited weak-epoch cases', '',
        '[M43AE](MILESTONE_43AE_JOINT_RESPONSE_RESULT.md) identified the following three losses against neighbor9. M43AF now',
        'records their associated weak-member response coordinates before the old',
        'remaining-epoch cut. The original 5.5 failures and original endpoint outcomes',
        'remain unchanged. Measured projections are not credited as restored detections.', '',
        '| Historical case | Associated weak members | Widths | Old remaining score | ON coordinate | OFF coordinate |',
        '|---|---:|---|---|---|---|'])
    for row in weak_rows:
        widths=', '.join(map(str,row['spectral_widths']))
        text.append(f"| `{row['name']}` | {row['associated_weak_members']} | {widths} | {format_span(row['old_remaining_score_range'])} | {format_span(row['on_coordinate_range'])} | {format_span(row['off_coordinate_range'])} |")
    text.extend(['', 'Ranges include every associated weak member of each named case.',
        f'The three cases repeat {len(weak_ids)} distinct member identifiers; their repeated coordinates do not constitute nine independent weak-signal examples.',
        'Exact per-member coordinates and all 261 historical diagnostic records are',
        'retained in the sealed result and lossless archive.', '', '## Evidence and reproducibility', '',
        f"- {totals['retained_members']:,} retained member records and {totals['eligible_before_remaining']:,} eligible member measurements.",
        f"- {totals['requested_unique_profiles']:,} complete profiles: {totals['newly_acquired_complete_profiles']:,} newly acquired and {totals['reused_complete_profiles']:,} reused exact profiles.",
        f"- {totals['member_profile_links']:,} member/profile links; zero incomplete profiles and zero undefined member measurements.",
        f"- {totals['direct_profile_native_checks']:,} direct native profile comparisons, plus {result['null_original_source_checks']:,} independent original-source native-null probes.",
        '- The full scalar/coordinate oracle and independent grid audit pass; all 940 pinned scientific files remain unchanged.',
        '- The reconstructed runtime reproduces all six sources, 96 arrays, 48 inherited gathers, 7,503,600 score values and the 432 zero-translation probes exactly.',
        '- All 61 focused tests pass in the reconstructed environment. The original closed training records were restored without rerunning training.', '',
        f"The saved historical run log has {reconciliation['unique_completion_lines_in_saved_log']} completion lines; all 261 historical records are present and audited.",
        'The frozen collector does not emit a new completion line when it returns an',
        'existing matching sealed record. The execution reconciliation names the 63',
        'records absent from this log. Scientific denominators come from the complete',
        'sealed inventory and independent audit, not console-line counts.', '',
        'The native nulls and baseline have no eligible members and therefore supply',
        'no conditional profile-tail observations. No physical false-alarm probability,',
        'additional sky coverage, production qualification or astronomical candidate is claimed.', '',
        f"Scientific freeze: `{result['freeze_commit']}`.", '',
        f"Verified model publication: `{publication['commit']}`.", '',
        f"Complete result seal: `{result['result_sha256']}`.", '',
        f"Complete audit seal: `{audit['result_sha256']}`.", '',
        f"The complete archive reconstructs **508 original files** in **{len(archive['parts'])} parts** ({archive['archive_bytes']:,} compressed bytes).",
        f"Archive SHA256: `{archive['archive_sha256']}`.", '',
        '```bash', 'PYTHONPATH=src:scripts python scripts/m43af_archive.py restore --stage complete',
        'PYTHONPATH=src:scripts python scripts/m43af_archive.py verify --stage complete', '```', '',
        'The earlier 244-file training archive and its publication remain intact.', '',
        '## Consequence for the next study', '',
        'M43AF is closed with an explicit failed qualification. Any change to the',
        'grid, response representation or acceptance rule belongs to a newly named',
        'and prospectively frozen study with fresh evaluation inputs. Historical',
        'coordinates may motivate that design but cannot serve as independent validation.',
        'General adoption also requires evidence from an independent observing sequence.', '',
        'See `M43AF_CURRENT_CONTINUATION.md` for the current restart point.', ''])
    (ROOT / 'MILESTONE_43AF_RESPONSE_STUDY_RESULT.md').write_text('\n'.join(text))
    continuation = f'''# M43AF completed continuation

The frozen no-model branch is complete: all 502 prescribed records and the
independent whole-study audit pass. No boundary qualifies and no new detector
is adopted. The 112 validation inputs and 128 held-out native nulls remain unopened.

Read [the complete report](MILESTONE_43AF_RESPONSE_STUDY_RESULT.md).

## Public scientific anchors

- Scientific freeze: `{result['freeze_commit']}`.
- Verified training/model publication: `{publication['commit']}`.
- Model-decision seal: `{decision['result_sha256']}`.
- Complete result seal: `{result['result_sha256']}`.
- Complete audit seal: `{audit['result_sha256']}`.
- Complete archive SHA256: `{archive['archive_sha256']}`.

The original 940 pinned files, earlier endpoints, failed gates and closed
training records remain unchanged. The earlier training-release manifest
describes its exact payload at the training-publication commit above; compare
that historical manifest at that commit rather than against later status documents.

## Restore completed evidence

Use Python {archive['python_version']} and zlib {archive['zlib_version']} with the
frozen dependencies. Restore the earlier dependency archives and then the
complete M43AF archive; do not rerun closed scientific evaluations.

```bash
PYTHONPATH=src:scripts python scripts/m43z_restore_ledger.py
PYTHONPATH=src:scripts python scripts/m43ab_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ad_archive.py restore
PYTHONPATH=src:scripts python scripts/m43ae_archive.py restore
PYTHONPATH=src:scripts python scripts/m43af_archive.py restore --stage complete
PYTHONPATH=src:scripts python scripts/m43af_archive.py verify --stage complete
```

The complete archive restores 508 original files, including all 502 records,
the full training grid, immutable decision, publication receipt and audits.
The earlier 244-file training archive remains available independently.

Native source data are needed only for a new native computation or an explicit
reproduction of the independent native checks. All six original sources and
96 arrays were reconstructed and verified during completion. Exact source
archives can restore the raw/normalized rows; the bounded recovery helper can
regenerate anchors or recover missing original sources against their pinned
receipts. Inspect availability before relying on a previous runtime.

## Next scientific scope

M43AF remains a failed qualification on one observing sequence. Any revised
grid, feature representation or acceptance rule requires a newly named,
prospectively frozen study and fresh evaluation inputs. The now-measured
historical coordinates may inform that design; they are not independent validation.
General adoption also requires evidence from an independent observing sequence.
No unattended computation between sessions is assumed.
'''
    (ROOT / 'M43AF_CURRENT_CONTINUATION.md').write_text(continuation)
    print(json.dumps(dict(complete=True, inputs=502, acquisition_totals=dict(totals),
                         known_weak_cases=[r['name'] for r in weak_rows])), flush=True)


if __name__ == '__main__':
    main()
