#!/usr/bin/env python3
"""Descriptive reporting of completed LS7O outputs; no fitting or selection."""
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls7o_response'


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]
def stats(values):
    v=np.asarray(values,dtype=float)
    return {'minimum':float(v.min()),'median':float(np.median(v)),'maximum':float(v.max())} if v.size else None


def main():
    summary=read(OUT/'summary.json');audit=read(OUT/'audit.json')
    assert audit['status']=='PASS'
    native=rows(OUT/'native.jsonl.gz');motion=rows(OUT/'reference_motion.jsonl.gz')
    meta=read(ROOT/'results_ls7o_metadata/inventory.json');inputs=read(ROOT/'results_ls7o_inputs/sources.json')
    quality=read(OUT/'quality_diagnosis.json')
    available_model_rows=sum(r['energies']['combined'] is not None for r in native)
    pulse_rows=rows(OUT/'pulses.jsonl.gz')
    available_pulses=sum(r['metrics'] is not None for r in pulse_rows)
    actual={'reference_windows_available':summary['reference_windows_available'],
            'planned_native_windows':420,'planned_paired_model_rows':840,'evaluated_combined_model_rows':available_model_rows,
            'planned_pulse_response_slots':12600,'evaluated_pulse_responses':available_pulses,
            'input_availability_pass':summary['reference_windows_available']==420,
            'native_correction_measured':available_model_rows>0,'downstream_pulse_transfer_measured':available_pulses>0,
            'source_summary_native_pixel_response_evaluated_flag':summary['native_pixel_response_evaluated'],
            'flag_clarification':'The frozen producer sets native_pixel_response_evaluated=True when its stage runs, even when every new-reference fit is blocked. Use the explicit evaluated counts here; no blocked slot is a measured response.'}
    (OUT/'scope_accounting.json').write_text(json.dumps(actual,indent=2)+'\n')
    diagnostics={'sectors':[],'energy_cells':[]}
    for sector in [29,32]:
        mm=[r for r in motion if r['sector']==sector and r['valid']]
        diagnostic={'sector':sector,'available_windows':len(mm),'unavailable_windows':210-len(mm)}
        for axis,name in [(0,'column'),(1,'row')]:
            diagnostic[name]={'conditional_formal_error_pixels':stats([p[axis] for r in mm for p in r['formal_sigma_xy']]),
                              'absolute_displacement_pixels':stats([abs(p[axis]) for r in mm for p in r['positions_xy']]),
                              'weighted_design_condition':stats([r['conditions_xy'][axis] for r in mm]),
                              'window_reference_residual_mean_per_3_dof':stats([r['reference_residual_mean_chi2_per_3_dof_xy'][axis] for r in mm])}
        diagnostics['sectors'].append(diagnostic)
    for cell in summary['cells']:
        selected=[r for r in native if r['sector']==cell['sector'] and r['column_offset']==cell['column_offset'] and r.get('reference_valid') and r['energies']['combined'] is not None]
        static=sum(r['energies']['static'] for r in selected)
        accounting={}
        if static:
            for method in ['motion','plane','combined']:
                alignment=sum(r['accounting'][method]['alignment'] for r in selected)
                size=sum(r['accounting'][method]['correction_energy'] for r in selected)
                accounting[method]={'minus_twice_alignment_fraction':-2*alignment/static,'correction_size_fraction':size/static,
                                    'net_energy_change_fraction':(size-2*alignment)/static}
        diagnostics['energy_cells'].append({'sector':cell['sector'],'column_offset':cell['column_offset'],'accounting':accounting})
    (OUT/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2,allow_nan=False)+'\n')
    passed=summary['joint_feasibility_pass'];result='PASS' if passed else 'FAIL'
    headline=f'**Joint development requirement: {result}. Independent numerical audit: PASS.**' if available_model_rows else '**Input availability: FAIL. Native correction and pulse transfer: NOT EVALUATED. Independent audit: PASS.**'
    text=['# LS7O six-reference centroid availability and response','',headline,'',
          'Twelve archived 20-second reference products from seven distinct stars were selected by metadata before reading their time series. The six-reference affine centroid estimator replaces the prior target POS_CORR input. The calibrated target PRF and protected plane retain their previous fixed rules. These are the same twenty closed contexts, with no added observing coverage or adopted detector.','',
          '## Fixed native comparison','',
          '| Sector | Field-column offset | Available / 210 | Motion / static energy | Plane / static | Combined / static | Improved backgrounds | Joint cell |',
          '|---|---:|---:|---:|---:|---:|---:|---|']
    for c in summary['cells']:
        methods=c['methods'];combined=methods['combined']
        ratios=[f"{methods[k]['ratio']:.9f}" if methods[k]['ratio'] is not None else 'unavailable' for k in ['motion','plane','combined']]
        improved=sum(b['ratio'] is not None and b['ratio']<1 for b in combined['backgrounds'])
        improvement=f'{improved}/10' if combined['windows'] else 'not evaluated'
        status=('PASS' if c['pass'] else 'FAIL') if combined['windows'] else 'BLOCKED'
        text.append(f"| {c['sector']} | {c['column_offset']} | {combined['windows']} | {' | '.join(ratios)} | {improvement} | {status} |")
    text+=['','All four cells must meet the predeclared native requirements and pulse limits. The ledger reserves 840 paired slots sharing 420 windows and twenty backgrounds; unavailable slots are not measured model responses. The static denominator and every historical window are unchanged. No ablation replaces the primary model.','',
           '## Reference acquisition and geometry','',
           f"The complete products would occupy {sum(r['product']['bytes'] for r in meta['references']):,} bytes for light curves and {sum(r['available_tpf']['bytes'] for r in meta['references']):,} bytes for matching target-pixel files. The frozen acquisition instead transfers exactly {inputs['download_bytes']:,} raw table bytes: 48,120 reference rows in 120 ranges. No reference pixel time series is acquired.", '',
           '| Sector | TIC | Tmag | Separation (degrees) | Centroid pixels | Valid rows / 4,010 |','|---|---:|---:|---:|---:|---:|']
    for r,p in zip(meta['references'],inputs['records'],strict=True):
        assert (r['sector'],r['tic'])==(p['sector'],p['tic'])
        text.append(f"| {r['sector']} | {r['tic']} | {r['tmag']:.2f} | {r['separation_deg']:.5f} | {r['moment_centroid_pixels']} | {p['valid_centroid_rows']} |")
    text+=['',f"The target lies inside the reference convex hull in both sectors. The nearest centroid-contributing pixel is {min(r['minimum_target_to_centroid_pixel_distance'] for r in meta['references']):.3f} pixels from its nominal position. All reference masks are pairwise disjoint. Exact CADENCENO joins pass; the maximum TIME-TIMECORR discrepancy is {audit['input_audit']['maximum_time_join_error_seconds']:.9g} seconds, below the frozen 0.001-second tolerance.",'',
           'The published ranges retain raw bytes, SHA-256, product ETags and metadata. Whole-product FITS checksums are not verified by these partial reads. The independent struct parser exactly checks every preserved centroid, quoted error, quality, cadence and time field.','',
           '## Availability obstruction','',
           '| Sector | Windows with finite centroids and positive errors | All-six quality-zero event windows | All-six quality-zero sideband windows | Fully available windows |','|---|---:|---:|---:|---:|']
    for s in quality['sectors']:
        c=s['window_counts']
        text.append(f"| {s['sector']} | {c['all_six_finite_positive_errors']}/210 | {c['all_six_quality_zero_event']}/210 | {c['all_six_quality_zero_sideband']}/210 | {c['actual_reference_prediction_available']}/210 |")
    text+=['','Every complete window fails the fixed requirement that all six stars have QUALITY=0 throughout all 110 sideband rows. All selected centroids and quoted positive errors are numerically present. There are at least three individually usable references at every saved cadence, but that does not satisfy the frozen all-six, all-sideband rule. These descriptive counts do not evaluate a relaxed rule.','',
           'Observed bits are 64 (an optimal-aperture cosmic ray), 512 (an outlier removed before cotrending), 1024 (a collateral-pixel cosmic ray), and 4096 (scattered-light exclusion), as defined in [SDPDD Rev F, table 32](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf). Flags describe different processing conditions; their presence alone does not identify the astrometric error of a retained centroid. No flag is waived here.','',
           '## Conditional error accounting','',
           '| Sector | Axis | Median formal error (pixels) | Largest displacement (pixels) | Median reference residual / 3 | Largest reference residual / 3 |','|---|---|---:|---:|---:|---:|']
    for d in diagnostics['sectors']:
        for axis in ['column','row']:
            v=d[axis]
            if v['conditional_formal_error_pixels']:
                text.append(f"| {d['sector']} | {axis} | {v['conditional_formal_error_pixels']['median']:.8g} | {v['absolute_displacement_pixels']['maximum']:.8g} | {v['window_reference_residual_mean_per_3_dof']['median']:.6g} | {v['window_reference_residual_mean_per_3_dof']['maximum']:.6g} |")
    if not available_model_rows:
        text+=['','No reference field was fitted, so this table has no measured conditional-error or affine-residual values.','']
    text+=['','Where available, these summaries repeat selected cadences across windows. The specified formal errors assume independent quoted reference errors and condition on fitted sideband centers and weights. Center uncertainty, shared calibration, centroid response, focus, crowding and target PRF errors remain outside that conditional model.','',
           '## Pulse protection and audit','',
           '| Sector | Offset | Nominal maximum distortion | Entry-stress maximum distortion | Failed or blocked slots |','|---|---:|---:|---:|---:|']
    for c in summary['cells']:
        p=c['protection'];nom=p['nominal']['maximum_distortion'];stress=[p[k]['maximum_distortion'] for k in ['minus_entries','plus_entries'] if p[k]['maximum_distortion'] is not None]
        n='unavailable' if nom is None else f'{100*nom:.8f}%';s='unavailable' if not stress else f'{100*max(stress):.8f}%'
        text.append(f"| {c['sector']} | {c['column_offset']} | {n} | {s} | {sum(v['failed_cases'] for v in p.values())} |")
    text+=['',f"Limits are 1% for nominal calibration and 5% for entry stresses. **{available_pulses:,} of 12,600 planned pulse-response slots were evaluated.** Unavailable slots count against the joint requirement but are not measured pulse distortions. Target photons are excluded from the final reference combination; shared upstream calibration and optical cross-talk remain unbounded.",'',
           f"The audit passes {audit['numeric_comparisons']:,} numerical comparisons and {audit['input_audit']['exact_scalar_values_checked']:,} exact raw-field comparisons. It independently reconstructs metadata coordinates, mask exclusion, raw rows, eligibility and every available numerical branch. Here the native numerical comparisons concern the unchanged static baseline; no new affine/PRF/pulse branch was reached. {sum(audit['preserved_manifest_entries'].values()):,} manifest entries, including the new input packages, agree. Execution used Python {summary['python']} locally; no GitHub Actions run is claimed.",'',
           'The frozen producer has a coarse stage flag named native_pixel_response_evaluated which is true when its evaluator runs, including a fully blocked run. [Explicit scope accounting](scope_accounting.json) records zero evaluated corrections and zero evaluated pulse transfers. The original output is preserved; the blocked ledger must not be read as a measured correction failure.','',
           '## Reproduction and decision','',
           f"Source freeze: `{summary['source_commit']}`. The response result directory and reference time-series extracts are absent from that checkpoint. Run acquisition, evaluation and audit in order using requirements_ls7g.txt. Frozen membership, product/range limits, model equations and claim boundaries are in [LS7O_SPEC.md](../LS7O_SPEC.md).",'',
           '[Native availability ledger](native.jsonl.gz), [reference availability](reference_motion.jsonl.gz), [pulse slots](pulses.jsonl.gz), [gates](summary.json), [audit](audit.json), [quality attribution](quality_diagnosis.json), [per-window attribution](quality_windows.jsonl.gz), [raw input provenance](../results_ls7o_inputs/sources.json), [metadata inventory](../results_ls7o_metadata/inventory.json), [continuation](../LS7O_CONTINUATION.md).','']
    if passed:
        text+=['The fixed descriptive requirement passes. This justifies further response/error qualification; it does not establish a detector, calibrated uncertainty, astrophysical completeness or a candidate. Keep unused sectors and M43 panels closed pending a separately justified qualification plan.','']
    else:
        text+=['Close the exact all-six/all-sideband eligibility formulation. The archive contains simultaneous reference measurements, but the frozen input contract is unusable on these windows. No empirical success or failure of the reference-driven physical correction was measured. The next work is a pixel/product quality and centroid-response contract using these fixed reference identities, or a different optical product if that contract cannot be established. Do not drop stars, waive flags or reweight this completed experiment to manufacture an available result. LS7J and LS7N remain separate measured failures; unused sectors and M43 panels remain closed.','']
    (OUT/'REPORT.md').write_text('\n'.join(text))
    provenance={'source_commit':summary['source_commit'],'source_tree':'12f13e10f0c11001c40595dab332d37b181221b3',
                'config_sha256':hashlib.sha256((ROOT/'config/ls7o_reference.json').read_bytes()).hexdigest(),
                'report_generator_is_post_evaluation_descriptive_only':True,'preserved_science_predecessor':'3354f09bf34af32a3fbf6ed68af77076f9f3d604'}
    (OUT/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')


if __name__=='__main__':main()
