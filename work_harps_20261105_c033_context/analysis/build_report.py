"""Build a descriptive report from the completed frozen C033 outputs."""
from pathlib import Path
import json

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
def read(p):return json.loads(p.read_bytes())

def main():
    p=read(HERE/'PLAN.json');q=read(HERE/'RESULTS_QA.json')['summary'];audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json');n=read(PHASE/'scientific_review/NEXT_GROUP_METADATA.json');rows=read(HERE/'results/PROFILE_METRICS.json');dates={r['dp_id']:r['date_obs'][:10]for r in rows if r['kind']=='merged'}
    lines=['# C033 / HD126093: completed fixed joint context','',
        '**All four original records remain U. No qualified laser candidate or physical origin is established.**','',
        'Four original C033/R035 records, four own discovery references and six existing April–July 2025 observations produced 28 profiles and 128 comparisons. The fixed common midpoint is 3880.35 air Å. No observing time or new telescope observations were added.','',
        '## Frame comparisons','',
        'The table describes 20 directed nonself comparisons per region. They represent 14 distinct unordered relationships with six reciprocal discovery pairs among only six observations. Sixteen identical-product self rows remain labeled separately across frames and regions. Native-to-merged comparisons use the same exposure.','',
        '| Region | Higher barycentric raw Pearson r | Lower barycentric normalized RMS |','|---|---:|---:|']
    for region,w in q['frame_wins'].items():lines.append(f"| {region} | {w['raw_r'].get('barycentric',0)}/20 | {w['normalized_rms'].get('barycentric',0)}/20 |")
    lines += ['', 'Raw correlation and normalized RMS answer different questions. Preserve every metric disagreement. The surrounding May 29–May 30 RMS exception appears in both directions and is one unordered relationship. The June 25-to-June 27 exception occurs in both regions. No new selection, recentering, lag, width, continuum, mask or background fit was introduced.','',
        '| Region | Quantity | Observation → own reference | Barycentric | Topocentric |','|---|---|---|---:|---:|']
    for e in q['exceptions']:
        lines.append(f"| {e['region']} | {e['quantity']} | {dates[e['dp_id']]} → {dates[e['reference_dp_id']]} | {e['barycentric_value']:.9f} | {e['topocentric_value']:.9f} |")
    lines += ['', '## Coverage, references and signed samples','',
        f"All {q['profile_slots']} profiles have 601 finite raw and normalized grid samples. All {q['comparison_slots']} raw-correlation and normalized-RMS rows are evaluable. There are no raw-only or blocked slots. These are current C033 outcomes, independently checked rather than inherited from C031.",
        '', f"Eight frame profiles have a positive but low flank reference: the June 25 merged product in both frames, and native order 4 for the May 29, May 30 and June 27 discoveries in both frames. All remain explicit. Fourteen profiles retain nonpositive original source samples; no sign clipping or replacement was performed. ERR has no positive finite support.",
        '', '| Kind | Observation | Order | Frame | Flank reference | Difference-noise proxy |','|---|---|---:|---|---:|---:|']
    for r in q['low_reference_profiles']:
        lines.append(f"| {r['kind']} | {dates[r['dp_id']]} | {r['order']if r['order']is not None else'—'} | {r['frame']} | {r['flank_reference']:.6f} | {r['first_difference_noise_proxy']:.6f} |")
    lines += ['', 'Structured signed flanks are not calibrated continua. Merged flux is uncalibrated ADU; native units are unspecified. Each uses its own positive divisor. Low-reference flags and first-difference proxies do not establish false-alarm probabilities, calibrated significance, sensitivity, physical flux ratios or linewidth.','',
        '## Original cores, mapping and raw evidence','',
        'Original centers are 3880.35, 3880.35, 3880.3525 and 3880.3475 air Å for 0265, 0270, 0274 and 0279 respectively. Two original cores coincide with the common core and two differ. The original-core union [3880.0975, 3880.6025] is slightly wider than the common core [3880.10, 3880.60]. Each original marker and own discovery BERV remains explicit.',
        '', f"All 112 profile/member support records have full finite raw and normalized support on their nominal fixed-grid centers. Nominal counts are {q['original_member_nominal_grid_centers']} after the exact original bounds and discovery-frame transformation are applied. These counts reflect fixed-grid geometry; no new per-member correlations, fitted locations or member-specific statistic was added.",
        '', 'All eight original global/local/baseline/later mapping chains are true and remain separately recorded. Four original U/U/U review chains remain. The 0274 secondary review retains a possible compact off-trace deposit/blend in order 4, distinct from its broader trace-centered component. The full stored raw panel shows that bright deposit setting the color scale; all pixels and the original full scale are preserved. This caution is not transferred to other events and does not dispose of the broad component.',
        '', 'Nine physical source IDs are also present in C031, but none of the nine current windows shares original indices with its C031 window. Five native/order source IDs are additional reused products/orders. The dependency audit reads prior index metadata only. The observations are still the same six, and earlier C033 epoch/raw values were exposed. Disjoint C031 windows do not establish blind or independent validation.',
        '', '## Validation and publication','',
        f"Input custody and header audit: 2,845 checks over 288 native header-order records. Compact synthetic preflight: 119 checks. Separate scalar preflight: 1,449 checks over 73,014 values. Observed reconstruction: {audit['checks_passed']} checks over {audit['scalar_values_compared']:,} values. All 50 NPZ containers and six fixed scientific PNGs decode, and all figures were inspected by the same assistant. No separate-agent or human review is claimed.",
        '', 'All 25 public method files were retrieved and compared byte for byte before ROOT_RELEASE and the single production execution. The established numerical helpers match C031/C015 structurally. The public method freeze does not make previously exposed observations blind. Original scientific outputs and completed earlier diagnostics remain unchanged.',
        '', 'C031 PR #28 is merged and both main and the optical work branch were synchronized before this method freeze. Current C033 results are published and integrated only after exact result-tree verification and successful final-head CI.',
        '', '## Next original queue route','',
        f"{n['core_overlap_group']} begins at original queue row {n['queue_rows'][0]['queue_index']}: {', '.join(n['events'])}, exact original center {n['original_centers_bary_air_angstrom'][0]!r} air Å. Its own discovery is {n['proposed_anchor_dp_id']} with BERV {n['proposed_anchor_berv_km_s']!r} km/s. It was selected before C033 values by original queue order. Restore its own sources, freshly scan all 72 orders, and freeze its own geometry/reference handling; do not inherit current orders, mapping stages, quality or caution flags. C032 remains pending later in original queue order. Rubin remains limited feasibility with minimum 50 unmet. No background science job is running.",
        '', '## Fixed scientific figures','']
    for f in read(HERE/'RESULTS_QA.json')['figures']:lines += [f"![{Path(f['path']).stem}](results/figures/{Path(f['path']).name})",'']
    (HERE/'RESULTS_REPORT.md').write_text('\n'.join(lines).rstrip()+'\n')
    print('C033 report built from fixed completed outputs; no new numerical fit or classification.')

if __name__=='__main__':main()
