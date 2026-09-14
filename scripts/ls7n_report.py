#!/usr/bin/env python3
"""Descriptive report from completed LS7N records; no new response evaluation."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_ls7n_response'


def main():
    summary=json.loads((OUT/'summary.json').read_text());audit=json.loads((OUT/'audit.json').read_text())
    native=[json.loads(r) for r in gzip.decompress((OUT/'native.jsonl.gz').read_bytes()).splitlines()]
    assert audit['status']=='PASS' and not summary['joint_feasibility_pass']
    report=['# LS7N cadence-level calibrated response — joint requirement FAIL','',
            'Completed and independently audited 14 September 2026. Source freeze:',
            '`'+summary['source_commit']+'`.','',
            '**The new calibrated response does not improve native prediction.**',
            'All 420 original windows are available under both coordinate conventions',
            '(840 paired model/window rows), and all 12,600 downstream pulse responses',
            'pass their fixed protection limits. Both sectors fail the native requirement.',
            'No detector is adopted, new candidate selected or observing coverage added.','',
            '## Native result on the unchanged metric','',
            'All rows below use the same original static baseline, aperture and covariance.',
            'Changes are percentages of static residual energy; positive means worse.',
            'Coordinate alternatives are separate sensitivity outputs, not two observing samples.','',
            '| Sector | Field-column offset | Motion only | Protected plane only | Combined | Combined backgrounds improved |',
            '|---|---:|---:|---:|---:|---:|']
    diagnostics=[]
    for cell in summary['cells']:
        methods=cell['methods'];sector,offset=cell['sector'],cell['column_offset']
        changes=[100*(methods[m]['ratio']-1) for m in ['motion','plane','combined']]
        improved=sum(b['ratio']<1 for b in methods['combined']['backgrounds'])
        report.append(f'| {sector} | {offset} | {changes[0]:+.4f}% | {changes[1]:+.4f}% | {changes[2]:+.4f}% | {improved}/10 |')
        rows=[r for r in native if r['sector']==sector and r['column_offset']==offset]
        total=math.fsum(r['energies']['static'] for r in rows)
        methods_diag={}
        for method in ['motion','plane','combined']:
            size=math.fsum(r['accounting'][method]['correction_energy'] for r in rows)
            alignment=math.fsum(r['accounting'][method]['alignment'] for r in rows)
            change=-2*alignment+size
            assert math.isclose(change,math.fsum(r['energies'][method]-r['energies']['static'] for r in rows),rel_tol=1e-10,abs_tol=1e-8)
            methods_diag[method]={'minus_twice_alignment_percent':-200*alignment/total,'correction_size_percent':100*size/total}
        ratios=[math.sqrt(math.fsum(v*v for v in r['uncertainty_entry_envelope_aperture'])/
                          math.fsum(v*v for v in r['correction_aperture']['motion'])) for r in rows]
        diagnostics.append({'sector':sector,'column_offset':offset,'methods':methods_diag,
                            'entry_envelope_norm_over_motion_norm':{'minimum':min(ratios),'median':statistics.median(ratios),'maximum':max(ratios)}})
    report += ['', 'Combined response improves zero of ten sector-29 backgrounds and two of ten',
               'sector-32 backgrounds, against six required. No background is doubled, but',
               'the aggregate and improvement-count gates fail in all four cells. Plane',
               'alone passes in sector 32 and fails in sector 29; it is not selected as a',
               'replacement. The separately closed LS7J combined increases were 45.74% and',
               '34.51%. The new increases are smaller, but the fixed static baseline remains',
               'better. That historical comparison is descriptive and adds no validation sample.','',
               '## Why the correction loses on this metric','',
               'For static residual r and correction c under the fixed projected covariance',
               'metric Q, the energy change is -2 r^T Q c + c^T Q c. The two terms below',
               'sum to the reported combined change. No gain or alternative correction was fitted.','',
               '| Sector | Offset | Alignment term / static energy | Correction size / static energy |',
               '|---|---:|---:|---:|']
    for d in diagnostics:
        m=d['methods']['combined']
        report.append(f"| {d['sector']} | {d['column_offset']} | {m['minus_twice_alignment_percent']:+.4f}% | {m['correction_size_percent']:+.4f}% |")
    report += ['', 'The correction has useful aggregate alignment, but its squared size exceeds',
               'that benefit. This establishes a mismatch for this fixed cadence response.',
               'It does not distinguish motion-estimator noise, response derivative error,',
               'reference astrometry, crowding or other scene changes. Availability and',
               'downstream pulse self-subtraction do not explain the observed failure.','',
               '## Pulse protection and calibration-entry stress','',
               '| Sector | Offset | Maximum nominal distortion | Maximum entry-stress distortion | Failed pulse cases |',
               '|---|---:|---:|---:|---:|']
    for c in summary['cells']:
        p=c['protection'];stress=max(p[k]['maximum_distortion'] for k in ['minus_entries','plus_entries'])
        report.append(f"| {c['sector']} | {c['column_offset']} | {100*p['nominal']['maximum_distortion']:.6f}% | {100*stress:.6f}% | 0/3150 |")
    report += ['', 'Limits are 1% for nominal PRFs and 5% for the two entry-stress profiles.',
               'The 12,600 rows cover five source offsets, three profile variants and all',
               '840 model/window combinations. Pulses are constant over the fixed windows',
               'of 2, 3 or 5 cadences (40, 60 or 100 seconds); these are not millisecond',
               'pulse timing tests. Positional metadata and outside-event samples stay fixed.',
               'This demonstrates downstream protection only; unknown upstream target',
               'participation remains unbounded. Entry stresses are not statistical draws.','',
               '## Physical scope and uncertainty','',
               'The model translates an effective commissioning PRF using supplied 20-second',
               'POS_CORR displacements. It adds no quaternion jitter or second exposure blur.',
               'Its source amplitude and reference are estimated only from protected sidebands.',
               'The background plane protects the 18 declared calibrated source profiles.',
               'All fits and operators are available; every protected span has rank 18.',
               'The fixed 110-pixel support retains both original science apertures.','',
               'The exact fast motion kernel, reference astrometry, focus/color response and',
               'upstream target exclusion remain unestablished. The two column conventions',
               'produce the same failure; that sensitivity does not solve the absolute origin.',
               'There is no tested quaternion-to-detector or subcadence response in LS7N.','',
               'Calibration entries are transported into a conservative image envelope,',
               'without interpreting their covariance or including amplitude-fit error.',
               'Its median aperture norm divided by the motion-prediction norm is:','',
               '| Sector | Offset | Median envelope norm / motion norm |',
               '|---|---:|---:|']
    for d in diagnostics:report.append(f"| {d['sector']} | {d['column_offset']} | {d['entry_envelope_norm_over_motion_norm']['median']:.4f} |")
    report += ['', 'These deliberately broad entry envelopes do not calibrate small-motion',
               'derivative uncertainty. Their size is not a measured probability of an error',
               'or proof that the actual derivative is inaccurate by that factor.','',
               '## Independent audit and decision','',
               f"The audit rebuilt all native and pulse rows with **{audit['numeric_comparisons']:,} numerical comparisons**.",
               'It uses raw FITS image bytes, SciPy interpolation, normal equations for',
               'source flux, a different SVD driver/QR solve for the plane, and explicit',
               'quadratic forms. It imports none of the new producer or response operators.',
               'Maximum aperture-correction difference is 1.98e-12 electrons/second;',
               'maximum individual energy difference is 3.19e-12 and pulse-distortion',
               'difference is 7.27e-14. All 146 inherited manifest entries remain unchanged.',
               'Five analytic/known-answer tests also pass, including exclusion of event',
               'photons from source amplitude and noise estimation.','',
               '**Close this exact cadence-level calibrated correction as a negative result.**',
               'No empirical gain/sign/lag/profile retry or unused-data opening follows.',
               'The next useful information is an independent astrometric/reference-star',
               'measurement and response uncertainty on the same pointing, with explicit',
               'target exclusion and time sampling. An availability/geometry assessment must',
               'precede any bounded acquisition; no such new input is claimed to exist here.',
               'If it cannot be established, reassess the optical data/product choice rather',
               'than append another locally adjusted correction.','',
               '[Current continuation](../LS7N_CONTINUATION.md), [frozen specification](../LS7N_SPEC.md).','',
               '## Reproduction','',
               '[Native records](native.jsonl.gz), [pulse responses](pulses.jsonl.gz),',
               '[summary](summary.json), [independent audit](audit.json),',
               '[descriptive accounting](diagnostics.json), [evaluation log](evaluation.log),',
               '[audit log](audit.log), [provenance](provenance.json), [checksums](SHA256SUMS).','',
               'Execution was local Python 3.12.14 with requirements_ls7g.txt. No GitHub',
               'Actions run is claimed. Source and audit scripts refuse to overwrite results.',
               'Reproduce in an isolated checkout of the source freeze before the result',
               'directory existed. No additional raw engineering download is needed.','']
    (OUT/'diagnostics.json').write_text(json.dumps({'scope':'descriptive arithmetic on completed records; no fit or new evaluation','cells':diagnostics},indent=2)+'\n')
    (OUT/'REPORT.md').write_text('\n'.join(report))


if __name__=='__main__':main()
