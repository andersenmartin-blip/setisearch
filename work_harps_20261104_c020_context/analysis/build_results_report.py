"""Describe immutable C020 outputs; no production rerun, fit or new selection."""
from pathlib import Path
import datetime
import hashlib
import json
from PIL import Image

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
ROOT = HERE.parents[1]
OUT = HERE / 'results'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def num(value):
    return 'unavailable' if value is None else f'{value:.6f}'


def main():
    plan = read(HERE / 'PLAN.json')
    inventory = read(ROOT / plan['inventory_path'])
    summary = read(OUT / 'SUMMARY.json')
    profiles = read(OUT / 'PROFILE_METRICS.json')
    pairs = read(OUT / 'COMPARISONS.json')
    audit = read(PHASE / 'independent_audit/NUMERICAL_AUDIT.json')
    dependency = read(PHASE / 'independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json')
    plots = read(OUT / 'PLOT_INDEX.json')
    assert summary['status'] == 'COMPLETE_FIXED_GROUP_CONTEXT'
    assert len(profiles) == 16 and len(pairs) == 32
    assert audit['status'] == 'PASS_INDEPENDENT_C020_NUMERICAL_RECONSTRUCTION'
    assert dependency == audit['source_pixel_dependencies']
    nonself = [r for r in pairs if r['relationship'] == 'MERGED_EPOCH_TO_DISCOVERY'
               and not r['identical_product_self_pair']]
    wins = {}
    for region in ['core', 'broad_pattern']:
        wr = wm = count = 0
        for dp in plan['merged_dp_ids']:
            rows = {r['frame']: r for r in nonself if r['dp_id'] == dp and r['region'] == region}
            if not rows:
                continue
            count += 1
            wr += rows['barycentric']['raw_pearson'] > rows['topocentric']['raw_pearson']
            wm += rows['barycentric']['normalized_rms'] < rows['topocentric']['normalized_rms']
        wins[region] = dict(nonself_observation_pairs=count, barycentric_raw_r_higher=wr,
                            topocentric_raw_r_higher=count-wr,
                            barycentric_normalized_rms_lower=wm,
                            topocentric_normalized_rms_lower=count-wm)
        assert count == wr == wm == 6
    geometry = []
    for item in inventory['merged_spectra']:
        offset = (plan['group_center_bary_air_angstrom'] / (1+item['berv_km_s']/plan['c_km_s'])
                  - summary['topocentric_anchor_air_angstrom'])
        geometry.append(dict(dp_id=item['dp_id'], date_obs=item['date_obs'],
                             predicted_center_offset_angstrom=offset,
                             within_fixed_topocentric_core=abs(offset) <= .25))
    report = ['# C020 / HD114783 at 4303.13 air Angstrom', '',
        '**Complete: seven existing observations, one own May 15 discovery reference, sixteen profiles and thirty-two comparisons. V2E2-0136 remains U.**', '',
        'All six other epochs have higher raw correlation and lower normalized RMS in the barycentric frame, in both the original core and surrounding spectrum. A broad central crest, nearby rise and broader multi-peak pattern recur with amplitude differences. This descriptive agreement does not assign physical origin, identify a line, qualify a laser candidate or calibrate significance, sensitivity or a survey null.', '',
        '## Fixed scope and every nonself comparison', '',
        'The exact original center is 4303.13 Å, core [4302.88,4303.38] Å and broad context [4300.13,4306.13] Å. The unchanged 0.01 Å grid has 51 core and 550 surrounding points. Own discovery ADP.2023-05-16T01:01:18.574 was observed on 2023-05-15 at BERV −17.1985506565257 km/s and fixes topocentric anchor 4303.376876941822 Å. No center, width, lag, stellar velocity, drift, continuum, background or mask was fitted.', '',
        'Each cell is **barycentric / topocentric**. Six rows are six other observations against one fixed reference, within a seven-observation cohort. Four identical-product self-comparison records remain explicitly labelled and add no recurrence evidence.', '',
        '| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |',
        '|---|---:|---:|---:|---:|']
    for item in inventory['merged_spectra']:
        if item['dp_id'] == plan['anchor_dp_id']:
            continue
        rows = {(r['frame'], r['region']): r for r in nonself if r['dp_id'] == item['dp_id']}
        cells = []
        for metric, region in [('raw_pearson','core'), ('raw_pearson','broad_pattern'),
                               ('normalized_rms','core'), ('normalized_rms','broad_pattern')]:
            cells.append(num(rows['barycentric',region][metric]) + ' / ' + num(rows['topocentric',region][metric]))
        report.append('| ' + item['date_obs'][:10] + ' | ' + ' | '.join(cells) + ' |')
    report += ['', '[All seven original-core profiles](results/figures/MERGED_CORE_CONTEXT.png) · [Full surrounding spectrum](results/figures/MERGED_BROAD_CONTEXT.png)', '',
        'The central rounded crest and neighboring rise align closely in the barycentric frame after the fixed scalar normalization. The complete broad window retains many structured peaks and troughs; it is not a flat, isolated-line continuum. Signed raw amplitude differences remain visible. No peak width or amplitude was fitted, and high correlation does not separately identify the central event.', '',
        '## Actual finite support and reference quality', '',
        'All sixteen profiles have 601 finite raw and scaled grid points, valid positive pooled flank medians and false low-reference flags. None is partial, raw-only or blocked. All thirty-two raw Pearson and thirty-two normalized RMS values are evaluable. Every retained original source sample in the fixed windows and flanks is positive; this is a measured outcome, separate from header geometry. Every profile has zero positive finite ERR samples. Low-reference and first-difference proxies do not calibrate formal SNR or significance.', '',
        'The discovery merged reference is 2212.0908203125 ADU in both frames. Its barycentric negative/positive flanks contain 151/151 finite original samples; its topocentric flanks contain 150/150. Original window counts are 601 and 599 respectively. The fixed 601-point interpolated profiles remain fully supported; floating boundary-count differences are retained without changing the windows. Native order 19 has reference 2353.91015625 in unspecified units, 120/123 finite original flank samples and 486 finite original window samples in each frame. Structured flank samples remain without line-free assumptions. These native/merged divisors are not a physical flux ratio.', '',
        '## Own native order and original raw context', '',
        'A fresh header-only scan of all 72 native orders selected only order 19. Both frames geometrically cover the full core, context and reference flanks. Finite sample quality was subsequently measured, as reported above. The native product compares only with its own discovery merged extraction:', '',
        '| Frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS |',
        '|---|---:|---:|---:|---:|']
    for frame in ['barycentric', 'topocentric']:
        rows = {r['region']: r for r in pairs if r['relationship'] == 'SAME_EPOCH_NATIVE_TO_MERGED' and r['frame'] == frame}
        cells = [num(rows['core']['raw_pearson']), num(rows['broad_pattern']['raw_pearson']),
                 num(rows['core']['normalized_rms']), num(rows['broad_pattern']['normalized_rms'])]
        report.append('| ' + frame + ' | ' + ' | '.join(cells) + ' |')
    report += ['', '[Native order 19 against its own merged extraction](results/figures/NATIVE_ORDERS_1.png)', '',
        'Same-exposure extracted shapes agree closely, with larger surrounding differences. This is dependent extraction evidence, not another observation or an origin confirmation. The original global, local, baseline and later mapping-support stages are all true; their support does not classify the broad native feature.', '',
        '[Complete original stored raw/excess pair](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retains every saved pixel and separate full scales. A faint, diffuse central enhancement sits beside much brighter right-edge structure. The historical primary description retains a broad native peak, nearby secondary rise and weak diffuse raw enhancement. The secondary description retains a broad rounded native feature, neighboring emission-like structure and a smooth raw trace enhancement. Original primary, secondary and adopted codes remain U/U/U. No new crop, contrast variant, subtraction, registration or detector statistic was introduced. Right-edge structure does not classify the central feature.', '',
        '## Fixed-frame geometry and source-pixel dependence', '',
        '| Observation | Predicted coherent center offset from fixed topocentric anchor (Å) | Inside fixed ±0.25 core |',
        '|---|---:|---|']
    for row in geometry:
        report.append(f"| {row['date_obs'][:10]} | {row['predicted_center_offset_angstrom']:+.9f} | {'yes' if row['within_fixed_topocentric_core'] else 'no'} |")
    inside = sum(r['within_fixed_topocentric_core'] for r in geometry)
    report += ['', f'{inside} metadata-predicted coherent centers lie inside the fixed topocentric core and {7-inside} outside. These are predictions under a barycentric-coherence assumption, not fitted peaks or proof of full finite-feature coverage. A fixed topocentric core can sample neighboring structure when that predicted center leaves it; frame statistics remain descriptive.', '',
        'The nominal C020 and C021 barycentric ±3 Å windows have a 0.69625 Å gap. Their unions of source samples needed for both frames differ because their own reference anchors differ. The frozen source-index audit confirms **17 shared original merged-spectrum samples for the July 1 2023 product**, indices [52377,52394), and zero sharing for the other six products. It verifies the identical full-source SHA for each pair against the preserved C021 index metadata, without reading C021 array values. The overlap was anticipated before current values; no mask or window change follows. No source-pixel independence is claimed.', '',
        '[Exact source-index dependency audit](../independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json). The same seven January 2022–July 2023 observations and original 0136 epoch/raw evidence were already exposed. No blind or untouched-data validation, independent new observation or added observing time is claimed.', '',
        '## Arithmetic, delivery and next unfinished route', '']
    prospective = read(PHASE / 'independent_audit/PROSPECTIVE_AUDIT.json')
    preflight = read(HERE / 'SYNTHETIC_PREFLIGHT.json')
    receipt = read(PHASE / 'PROSPECTIVE_PUBLICATION_RECEIPT.json')
    report += [f"The method, source-only review and synthetic checks were public before observed C020 values. Exact readback covered 24 files at commit `{read(HERE/'ROOT_RELEASE.json')['publication_commit']}`. The {len(preflight['checks'])} compact preflight checks and {prospective['checks_passed']:,} separate scalar checks over {prospective['synthetic_scalars_compared']:,} synthetic values passed before execution.", '',
        f"The separate observed reconstruction passes **{audit['checks_passed']} checks / {audit['scalar_values_compared']:,} scalar comparisons** across all eight bounded input windows, sixteen profiles, thirty-two comparisons, the byte-exact original raw container and the seven source-index dependency pairs. Source flux, ERR and original indices agree exactly. Fixed numerical tolerances pass; wavelength/interpolation arithmetic is not claimed bitwise identical. Maximum absolute differences:", '',
        '| Quantity | Maximum absolute difference |', '|---|---:|']
    for kind, value in audit['maximum_absolute_differences_by_kind'].items():
        report.append(f'| {kind} | {value:.12g} |')
    report += ['', 'All four scientific PNGs were visually inspected and fully decoded. All 61 frozen source bindings and the original numerical outputs stayed unchanged. Separate scalar formulas and fresh processes were run by the same assistant; no independent human or separate-agent review is claimed.', '',
        '[Fixed plan](PLAN.json) · [Released method](ROOT_RELEASE.json) · [Profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json) · [Scalar audit](../independent_audit/NUMERICAL_AUDIT.json)', '',
        '**Next unfinished route:** original queue row 62, C028/R029/V2E2-0260 on **HD126093**, exact center **3864.5550000000003 Å**. Use its six April–July 2025 observations and its own April 27 discovery at BERV 5.77068898867443 km/s; the cohort span is 29.26984563734743 km/s. Own raw batch04 history retains orders 2 and 3, original local/baseline failures and later mapping support. Freshly scan all 72 own native headers and freeze a separate fixed diagnostic before new observed arithmetic. No HD114783 seven-epoch count, May reference, order-19 scope, BERV span or quality outcome is transferred.', '',
        'All exact C001–C023 routes are now complete, including C013/C014 normalization. The ten exact FRAME_BASELINE_CONTEXT records were already completed in the earlier bounded BERV and May-quality work and are skipped with [source-bound proof](../scientific_review/COMPLETED_ROUTE_SKIP_PROOF.json). Their physical U status remains. The four HD135204 records had no new selected epoch under those bounded filters; this is not archive-wide absence. The separate 0235 spatial/background route stays closed. See [the exact next handoff](../NEXT_ACTION.json). No completed diagnostic is replayed solely because U remains. Rubin stays limited feasibility with minimum 50 unmet.', '']
    (HERE / 'RESULTS_REPORT.md').write_text('\n'.join(report))
    images = []
    for item in plots['files']:
        path = OUT / item['path']
        assert sha(path) == item['sha256'] and path.stat().st_size == item['bytes']
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            im.load()
            dimensions = list(im.size)
        images.append({**item, 'fully_decoded': True, 'dimensions': dimensions,
                       'visually_inspected_by_assistant': True})
    for name, expected in plan['source_hashes'].items():
        assert sha(ROOT / name) == expected, name
    for name, expected in read(OUT / 'OUTPUT_HASHES.json').items():
        assert sha(OUT / name) == expected, name
    qa = dict(status='PASS_C020_REPORT_AND_DELIVERY_QA',
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        profile_slots=len(profiles), comparison_slots=len(pairs),
        evaluable_pearson_values=sum(r['raw_pearson'] is not None for r in pairs),
        evaluable_normalized_rms_values=sum(r['normalized_rms'] is not None for r in pairs),
        profiles_with_full601_support=sum(r['raw_grid_finite_samples'] == r['normalized_grid_finite_samples'] == 601 for r in profiles),
        positive_reference_profiles=sum(r['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE' for r in profiles),
        raw_only_profiles=summary['raw_only_normalization_slots'],
        blocked_profiles=summary['blocked_source_profile_slots'],
        low_reference_flags=sum(r['low_flank_reference'] is True for r in profiles),
        profiles_with_nonpositive_original_samples=sum(any(r[key] > 0 for key in ['window_nonpositive_fraction','left_flank_nonpositive_fraction','right_flank_nonpositive_fraction']) for r in profiles),
        positive_finite_ERR_samples=sum(r['positive_finite_ERR_samples'] for r in profiles),
        frame_wins=wins, predicted_topocentric_centers=geometry,
        predicted_centers_inside_fixed_core=inside,
        source_bindings_verified=len(plan['source_hashes']),
        source_pixel_dependencies=dependency,
        all_numeric_files_unchanged=True, classifications_changed=0, origin_assignments=0,
        figures=images, report_sha256=sha(HERE / 'RESULTS_REPORT.md'),
        report_builder_sha256=sha(Path(__file__)))
    assert len(plots['files']) == 4 and len(plan['source_hashes']) == 61
    assert qa['profiles_with_full601_support'] == qa['positive_reference_profiles'] == 16
    assert qa['evaluable_pearson_values'] == qa['evaluable_normalized_rms_values'] == 32
    assert sum(r['shared_original_source_indices'] for r in dependency['source_pairs']) == 17
    write(HERE / 'RESULTS_QA.json', qa)
    print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','source_pixel_dependencies','predicted_topocentric_centers']}, indent=2))


if __name__ == '__main__':
    main()
