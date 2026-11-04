"""Describe saved C028 outcomes without refitting or rerunning numerical work."""
from pathlib import Path
import datetime
import hashlib
import json
from PIL import Image

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
OUT=HERE/'results'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def num(value):
    return 'unavailable' if value is None else f'{value:.6f}'


def main():
    plan=read(HERE/'PLAN.json');inv=read(ROOT/plan['inventory_path'])
    summary=read(OUT/'SUMMARY.json');profiles=read(OUT/'PROFILE_METRICS.json')
    pairs=read(OUT/'COMPARISONS.json');audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json')
    correction=read(HERE/'caption_correction/CORRECTION.json')
    assert summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT'
    assert audit['status']=='PASS_INDEPENDENT_C028_NUMERICAL_RECONSTRUCTION'
    assert len(profiles)==16 and len(pairs)==32
    nonself=[r for r in pairs if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']]
    wins={}
    for region in ['core','broad_pattern']:
        raw=rms=count=0
        for dp in plan['merged_dp_ids']:
            rows={r['frame']:r for r in nonself if r['dp_id']==dp and r['region']==region}
            if not rows:continue
            count+=1
            raw+=rows['barycentric']['raw_pearson']>rows['topocentric']['raw_pearson']
            rms+=rows['barycentric']['normalized_rms']<rows['topocentric']['normalized_rms']
        wins[region]=dict(nonself_observation_pairs=count,barycentric_raw_r_higher=raw,
            topocentric_raw_r_higher=count-raw,barycentric_normalized_rms_lower=rms,
            topocentric_normalized_rms_lower=count-rms)
        assert count==raw==rms==5
    geometry=[]
    for item in inv['merged_spectra']:
        offset=plan['group_center_bary_air_angstrom']/(1+item['berv_km_s']/plan['c_km_s'])-summary['topocentric_anchor_air_angstrom']
        geometry.append(dict(dp_id=item['dp_id'],date_obs=item['date_obs'],
            predicted_center_offset_angstrom=offset,within_fixed_topocentric_core=abs(offset)<=.25))
    signed=[r for r in profiles if any(r[k]>0 for k in ['window_nonpositive_fraction','left_flank_nonpositive_fraction','right_flank_nonpositive_fraction'])]
    report=['# C028 / HD126093 at 3864.5550000000003 air Angstrom','',
        '**Complete: six existing observations, one own April 27 discovery reference, sixteen profiles and thirty-two comparisons. V2E2-0260 remains U.**','',
        'All five other epochs have higher raw correlation and lower normalized RMS in the barycentric frame, in both the original core and surrounding spectrum. The central broad crest and broader structured pattern recur with amplitude and noise differences. This descriptive agreement does not identify a physical line, assign origin, qualify a laser candidate or calibrate significance, sensitivity or a survey null.','',
        '## Fixed scope and every nonself comparison','',
        'Preserve the exact original catalog center 3864.5550000000003 Å, core [3864.3050000000003,3864.8050000000003] Å and context [3861.5550000000003,3867.5550000000003] Å. The 0.01 Å grid has 51 core and 550 surrounding points. Own discovery ADP.2025-04-28T01:01:15.579 was observed on 2025-04-27 at BERV 5.77068898867443 km/s and fixes topocentric anchor 3864.480612819388 Å. No center, width, lag, stellar RV, drift, continuum, background or mask was fitted.','',
        'Each cell is **barycentric / topocentric**. Five rows represent five other observations against one fixed reference within the six-observation cohort. Four identical-product self rows remain labelled and add no recurrence evidence.','',
        '| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |',
        '|---|---:|---:|---:|---:|']
    for item in inv['merged_spectra']:
        if item['dp_id']==plan['anchor_dp_id']:continue
        rows={(r['frame'],r['region']):r for r in nonself if r['dp_id']==item['dp_id']}
        cells=[]
        for metric,region in [('raw_pearson','core'),('raw_pearson','broad_pattern'),('normalized_rms','core'),('normalized_rms','broad_pattern')]:
            cells.append(num(rows['barycentric',region][metric])+' / '+num(rows['topocentric',region][metric]))
        report.append('| '+item['date_obs'][:10]+' | '+' | '.join(cells)+' |')
    report+=['','[All six original-core profiles](caption_correction/figures/MERGED_CORE_CONTEXT.png) · [Complete surrounding spectrum](caption_correction/figures/MERGED_BROAD_CONTEXT.png)','',
        'The discovery has higher signed raw amplitude than the other observations. The central crest aligns barycentrically after the fixed scalar normalization, while neighboring peaks and troughs remain inside the unchanged windows. June 25 has much lower raw flux and visibly noisier scaled structure; it also has the lowest barycentric shape agreement of these five nonself comparisons. It remains included. These observations are descriptive, without a fitted amplitude or linewidth, a line identification or a calibrated recurrence test.','',
        '## Finite support, signed samples and references','',
        'All sixteen profiles have 601 finite raw and normalized grid points, valid positive pooled flank references and false low-reference flags. None is partial, raw-only or blocked. All thirty-two Pearson and thirty-two normalized RMS values are evaluable. Every profile has zero positive finite ERR samples. Full coverage and false low-reference flags do not establish formal SNR or general measurement quality.','',
        'Four frame-profile rows from two reused observations contain nonpositive original source samples. Every original sign remains, without clipping or a sign-flip normalization. Fractions below are the saved fractions of finite original samples in each fixed region; frame rows share their observing products.','',
        '| Observation | Frame | Nonpositive window fraction | Negative flank fraction | Positive flank fraction |',
        '|---|---|---:|---:|---:|']
    for row in signed:
        report.append('| '+row['date_obs'][:10]+' | '+row['frame']+' | '+' | '.join(num(row[k]) for k in ['window_nonpositive_fraction','left_flank_nonpositive_fraction','right_flank_nonpositive_fraction'])+' |')
    report+=['','June 25 retains reference levels 64.815281 / 57.656324 ADU and first-difference noise proxies 16.438986 / 16.818882 ADU (B/T). Both fixed low-reference flags are false despite the negative samples and noisier appearance. The proxy and flag are descriptive, without calibrated significance or a formal noise model.','',
        'Discovery reference details, separately from interpolated 601-point support:','',
        '| Product / frame | Pooled reference | Finite original flanks L/R | Finite original window samples |',
        '|---|---:|---:|---:|']
    for row in profiles:
        if row['dp_id']!=plan['anchor_dp_id']:continue
        product='merged ADU' if row['kind']=='merged' else f"native order {row['order']} (unit unspecified)"
        report.append(f"| {product} / {row['frame']} | {row['flank_reference']:.12g} | {row['left_flank_finite_samples']} / {row['right_flank_finite_samples']} | {row['window_native_finite_samples']} |")
    report+=['','The flanks contain structured source samples, including part of the next C029 feature. They are not established line-free continua. Native BUNIT is absent and merged ADU is uncalibrated; the separate native/merged divisors do not define physical flux ratios.','',
        '## Own native orders and preserved raw morphology','',
        'A fresh scan of all 72 native headers selects orders 2 and 3. Both frames geometrically cover the core, ±3 context and both flanks in each order. Actual finite support was subsequently measured, as above. The native products compare only with their own discovery merged extraction:','',
        '| Order / frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS |',
        '|---|---:|---:|---:|---:|']
    for order in [2,3]:
        for frame in ['barycentric','topocentric']:
            rows={r['region']:r for r in pairs if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED' and r['order']==order and r['frame']==frame}
            cells=[num(rows['core']['raw_pearson']),num(rows['broad_pattern']['raw_pearson']),num(rows['core']['normalized_rms']),num(rows['broad_pattern']['normalized_rms'])]
            report.append('| '+str(order)+' / '+frame+' | '+' | '.join(cells)+' |')
    report+=['','[Both native orders against their own merged extraction](results/figures/NATIVE_ORDERS_1.png)','',
        'The central extracted crests agree in shape; surrounding agreement is weaker and normalized amplitudes differ. Both orders share one exposure and extraction lineage, so these are dependent comparisons. Original global support, local/baseline failures and later five-window support remain distinct for each order. Geometric or later mapping support does not erase the original failures or determine origin.','',
        '[Both complete original raw/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain every saved pixel and separate full scales. Both show a diffuse central multi-row enhancement; order 2 is weaker and noisier. The historical broad, trace-centered, photon-compatible description remains provisional U/U/U. Photon-compatible morphology is not proof of an astrophysical origin or a laser. No new raw crop, contrast variant, registration, background subtraction or detector statistic was introduced. C029/0261 compact off-trace contamination is a separate historical record and is not transferred to 0260.','',
        '## Frame geometry and next-window dependence','',
        '| Observation | Predicted coherent-center offset from fixed topocentric anchor (Å) | Inside fixed ±0.25 core |',
        '|---|---:|---|']
    for row in geometry:
        report.append(f"| {row['date_obs'][:10]} | {row['predicted_center_offset_angstrom']:+.9f} | {'yes' if row['within_fixed_topocentric_core'] else 'no'} |")
    inside=sum(row['within_fixed_topocentric_core'] for row in geometry)
    report+=['',f'{inside} of six metadata-predicted coherent centers fall inside the fixed topocentric core; {6-inside} fall outside. These are predictions under a barycentric-coherence assumption, not fitted peaks or proof of full finite-feature coverage. A fixed core may sample neighboring structure. The cohort BERV span is 29.26984563734743 km/s; neither geometry nor frame agreement is a calibrated origin test.','',
        'Next C029 at 3866.125 Å reuses the same six observations. The nominal ±3 Å windows overlap by 4.430000000000291 Å. Its catalog center lies in the current positive reference flank; only part of its ±0.25 core lies in that flank. The current core also intersects only part of the next negative flank. The next route was selected and this overlap recorded before current values. Shared windows, flanks, pixels and products are dependent. No source-pixel independence, blind validation, new observation or extra observing time is claimed. The preceding C020 analysis used a different star and different observing products.','',
        '## Arithmetic and delivery corrections','',
        'The public fixed method and exact 23-file readback at commit `'+read(HERE/'ROOT_RELEASE.json')['publication_commit']+'` preceded current observed values. Source-only restoration and header checking passed 1,563 checks. The 97 compact synthetic checks and 1,449 separate scalar checks over 73,014 synthetic values passed before execution.','',
        f"The separate observed reconstruction passes **{audit['checks_passed']} checks / {audit['scalar_values_compared']:,} scalar comparisons** across all eight bounded source inputs, sixteen profiles, thirty-two comparisons and two byte-exact original raw containers. Original flux, ERR and source indices agree exactly. Fixed numerical tolerances pass; wavelength/interpolation arithmetic is not claimed bitwise identical. Maximum absolute differences:",'',
        '| Quantity | Maximum absolute difference |','|---|---:|']
    for kind,value in audit['maximum_absolute_differences_by_kind'].items():
        report.append(f'| {kind} | {value:.12g} |')
    report+=['','An initial release JSON-format error stopped validation before any observed array access or result-directory creation. A newline-only release-metadata repair is recorded in [the repair receipt](RELEASE_FORMAT_REPAIR.json); the public method and plan were unchanged. The successful observed calculation ran once.','',
        'The original frozen renderer inherited **R021** in the two merged-image titles. All plan/event identities and numerical values correctly use **C028/R029**. Separate [caption-corrected copies](caption_correction/CORRECTION.json) change only that label to R029. The changed-pixel boxes are [869,34,881,50] in both 1820×1120 images; every pixel below the title band is identical. The original four PNGs, original renderer and numerical outputs remain unchanged. There are four scientific display views and six preserved PNG files including the two corrected copies. All six were visually inspected and fully decoded.','',
        'All 47 fixed source bindings and all original numerical hashes remain unchanged. Separate scalar formulas and fresh processes were run by the same assistant, without an independent human or separate-agent review claim.','',
        '[Plan](PLAN.json) · [Release](ROOT_RELEASE.json) · [All profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json) · [Scalar audit](../independent_audit/NUMERICAL_AUDIT.json)','',
        '**Next:** C029/R030 on HD126093, original queue row 63 onward, records V2E2-0261/0266/0272 at exact 3866.125 Å. Preserve all three discovery references and six observing products, every per-record/order mapping stage and 0261 compact off-trace deposit/possible blend separately from its centered broad component. Restore its own products/raw containers, freshly scan all 72 headers per discovery and freeze a distinct fixed comparison before new arithmetic. See [the handoff](../NEXT_ACTION.json). C028 and all earlier exact diagnostics remain closed with physical U unchanged. Rubin remains limited feasibility with minimum 50 unmet.','']
    (HERE/'RESULTS_REPORT.md').write_text('\n'.join(report))
    figures=[]
    for item in read(OUT/'PLOT_INDEX.json')['files']:
        path=OUT/item['path'];assert sha(path)==item['sha256']
        figures.append(path)
    for item in correction['comparisons']:
        original=HERE/item['original_path'];path=HERE/item['corrected_path']
        assert sha(original)==item['original_sha256'] and sha(path)==item['corrected_sha256']
        assert item['all_pixels_below_title_band_identical'] is True
        figures.append(path)
    decoded=[]
    for path in figures:
        with Image.open(path) as im:im.verify()
        with Image.open(path) as im:im.load();dimensions=list(im.size)
        decoded.append(dict(path=str(path.relative_to(HERE)),sha256=sha(path),bytes=path.stat().st_size,dimensions=dimensions,fully_decoded=True,visually_inspected_by_assistant=True))
    for name,expected in plan['source_hashes'].items():assert sha(ROOT/name)==expected,name
    for name,expected in read(OUT/'OUTPUT_HASHES.json').items():assert sha(OUT/name)==expected,name
    qa=dict(status='PASS_C028_REPORT_AND_DELIVERY_QA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        profile_slots=len(profiles),comparison_slots=len(pairs),
        evaluable_pearson_values=sum(r['raw_pearson'] is not None for r in pairs),
        evaluable_normalized_rms_values=sum(r['normalized_rms'] is not None for r in pairs),
        profiles_with_full601_support=sum(r['raw_grid_finite_samples']==r['normalized_grid_finite_samples']==601 for r in profiles),
        positive_reference_profiles=sum(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' for r in profiles),
        raw_only_profiles=summary['raw_only_normalization_slots'],blocked_profiles=summary['blocked_source_profile_slots'],
        low_reference_flags=sum(r['low_flank_reference'] is True for r in profiles),
        profiles_with_nonpositive_original_samples=len(signed),observing_products_with_nonpositive_samples=len({r['dp_id'] for r in signed}),
        positive_finite_ERR_samples=sum(r['positive_finite_ERR_samples'] for r in profiles),
        frame_wins=wins,predicted_topocentric_centers=geometry,predicted_centers_inside_fixed_core=inside,
        source_bindings_verified=len(plan['source_hashes']),all_numeric_files_unchanged=True,
        classifications_changed=0,origin_assignments=0,scientific_display_views=4,delivered_PNG_files=len(decoded),
        label_correction_path='caption_correction/CORRECTION.json',label_correction_sha256=sha(HERE/'caption_correction/CORRECTION.json'),
        figures=decoded,report_sha256=sha(HERE/'RESULTS_REPORT.md'),report_builder_sha256=sha(Path(__file__)))
    assert len(signed)==4 and qa['observing_products_with_nonpositive_samples']==2
    assert qa['profiles_with_full601_support']==qa['positive_reference_profiles']==16
    assert qa['evaluable_pearson_values']==qa['evaluable_normalized_rms_values']==32 and len(decoded)==6
    write(HERE/'RESULTS_QA.json',qa)
    print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','predicted_topocentric_centers']},indent=2))


if __name__=='__main__':
    main()
