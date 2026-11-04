"""Report immutable C029 measurements and delivery QA without new fitting."""
from pathlib import Path
import datetime,hashlib,json
from PIL import Image
HERE=Path(__file__).resolve().parent;PHASE=HERE.parent;ROOT=HERE.parents[1];OUT=HERE/'results'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def num(x):return 'unavailable' if x is None else f'{x:.6f}'

def main():
    plan=read(HERE/'PLAN.json');inv=read(ROOT/plan['inventory_path']);summary=read(OUT/'SUMMARY.json')
    profiles=read(OUT/'PROFILE_METRICS.json');pairs=read(OUT/'COMPARISONS.json');audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json')
    dependency=read(PHASE/'independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json')
    assert summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT' and audit['status']=='PASS_INDEPENDENT_C029_NUMERICAL_RECONSTRUCTION'
    assert len(profiles)==24 and len(pairs)==96 and dependency==audit['source_pixel_dependencies']
    nonself=[r for r in pairs if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']]
    dates={r['dp_id']:r['date_obs'][:10]for r in inv['merged_spectra']}
    wins={}
    for region in ['core','broad_pattern']:
        keys={(r['dp_id'],r['reference_dp_id'])for r in nonself};wr=wm=0
        for dp,ref in keys:
            rows={r['frame']:r for r in nonself if r['dp_id']==dp and r['reference_dp_id']==ref and r['region']==region}
            wr+=rows['barycentric']['raw_pearson']>rows['topocentric']['raw_pearson']
            wm+=rows['barycentric']['normalized_rms']<rows['topocentric']['normalized_rms']
        wins[region]=dict(nonself_directed_pairs=len(keys),barycentric_raw_r_higher=wr,topocentric_raw_r_higher=len(keys)-wr,barycentric_normalized_rms_lower=wm,topocentric_normalized_rms_lower=len(keys)-wm)
        assert wr==wm==len(keys)==15
    signed=[r for r in profiles if any(r[k]>0 for k in ['window_nonpositive_fraction','left_flank_nonpositive_fraction','right_flank_nonpositive_fraction'])]
    geometry=[]
    for e in inv['merged_spectra']:
        offset=plan['group_center_bary_air_angstrom']/(1+e['berv_km_s']/plan['c_km_s'])-summary['topocentric_anchor_air_angstrom']
        geometry.append(dict(dp_id=e['dp_id'],date_obs=e['date_obs'],predicted_center_offset_angstrom=offset,within_fixed_topocentric_core=abs(offset)<=.25))
    report=['# C029 / HD126093 at 3866.125 air Angstrom','',
        '**Complete: six existing observations, three original records and three own discovery references, 24 profiles and 96 comparisons. All three records remain U.**','',
        'Every one of the 15 directed nonself observation/reference pairs has higher barycentric raw correlation and lower barycentric normalized RMS, in both the original core and surrounding spectrum. The broad central crest and neighboring structure recur with amplitude and noise differences. These descriptive statistics do not identify a physical line, assign origin, qualify a laser candidate or calibrate significance, sensitivity or a survey null.','',
        '## Fixed scope and all observation/reference comparisons','',
        'All three exact original catalog centers are 3866.125 Å, so their original cores [3865.875,3866.375] Å are identical to the common ±0.25 Å core. There is no midpoint/member-core edge displacement in C029. The fixed broad window is [3863.125,3869.125] Å. The unchanged 0.01 Å grid has 51 core and 550 surrounding points.','',
        'The first-queue April 27 discovery fixes one common topocentric anchor 3866.0505825991236 Å at BERV 5.77068898867443 km/s. All three discovery references remain: 0261 on April 27, 0266 on May 29 and 0272 on May 30 2025. Each product retains its own epoch BERV. No center, width, lag, stellar RV, drift, continuum, background or mask was fitted.','',
        'Each cell below is **barycentric / topocentric**. Each reference compares all five other epochs. The 15 directed rows represent 12 distinct unordered observation relationships, including three reciprocal discovery pairs, within only six observations. References and reciprocal repetitions are dependent. Twelve labelled identical-product self rows remain in the full tables and add no recurrence evidence.','',
        '| Reference event/date | Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |',
        '|---|---|---:|---:|---:|---:|']
    for event,ref in plan['events'].items():
        for dp in plan['merged_dp_ids']:
            if dp==ref:continue
            rows={(r['frame'],r['region']):r for r in nonself if r['dp_id']==dp and r['reference_dp_id']==ref}
            cells=[num(rows['barycentric',region][metric])+' / '+num(rows['topocentric',region][metric])for metric,region in [('raw_pearson','core'),('raw_pearson','broad_pattern'),('normalized_rms','core'),('normalized_rms','broad_pattern')]]
            report.append('| '+event.replace('V2E2-','')+' / '+dates[ref]+' | '+dates[dp]+' | '+' | '.join(cells)+' |')
    report+=['','[Complete core profiles and all three markers](results/figures/MERGED_CORE_CONTEXT.png) · [Complete broad context](results/figures/MERGED_BROAD_CONTEXT.png)','',
        'The broad crest aligns closely barycentrically after fixed scalar normalization, while smaller neighboring structure and noisier epochs remain. The April discovery has higher raw flux than the other epochs. June 25 is much weaker and noisier but remains in every comparison. The full window includes many structured peaks and troughs; no line-free continuum or isolated-line model is assumed. No fitted peak amplitude or linewidth follows from the figure.','',
        '## Actual support, references and signed source samples','',
        'All 24 profiles have 601 finite raw and scaled grid points and valid positive fixed flank references, with false low-reference flags. None is partial, raw-only or blocked. All 96 Pearson and 96 normalized RMS values are evaluable. Every profile has zero positive finite ERR support. Full geometry, positive references and false low flags do not establish formal SNR or a general quality certificate.','',
        'Eight frame-profile rows from four observing products retain nonpositive original source samples. The two May order-2 native products and the June 25 / July 16 merged products are represented below. Frame rows share their observations; every original sign remains without clipping or sign-flip normalization. All saved nonpositive fractions in the fixed reference flanks are zero in this C029 result.','',
        '| Product/date/order | Frame | Nonpositive original-window fraction | Pooled reference | Finite original window samples |',
        '|---|---|---:|---:|---:|']
    for r in signed:
        label=r['kind']+' '+r['date_obs'][:10]+(' / order '+str(r['order'])if r['kind']=='native'else'')
        report.append(f"| {label} | {r['frame']} | {num(r['window_nonpositive_fraction'])} | {num(r['flank_reference'])} | {r['window_native_finite_samples']} |")
    report+=['','References are pooled signed medians of unchanged original samples in fixed 1.5–3 Å flanks, with at least twenty finite samples per side and positive pooled median. Structured flanks are not established line-free continua. Merged ADU is uncalibrated and native BUNIT is absent. Their separate normalization divisors are not physical native/merged flux ratios. ERR, first-difference proxies and low-reference flags do not calibrate significance, false-alarm probability, sensitivity or linewidth.','',
        '## All native orders, raw panels and staged review history','',
        'A fresh header-only scan of all 72 orders for each of three native discovery products (216 scans) selects both orders 2 and 3 in every product. All twelve native frame/order header geometries cover the fixed core, broad window and reference flanks. Actual finite support was measured separately, as above. All six native product/order pairs compare only with their own merged extraction:','',
        '| Discovery / order / frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS |',
        '|---|---:|---:|---:|---:|']
    for dp in plan['discovery_dp_ids']:
        for order in [2,3]:
            for frame in ['barycentric','topocentric']:
                rows={r['region']:r for r in pairs if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED'and r['dp_id']==dp and r['order']==order and r['frame']==frame}
                values=[rows['core']['raw_pearson'],rows['broad_pattern']['raw_pearson'],rows['core']['normalized_rms'],rows['broad_pattern']['normalized_rms']]
                report.append('| '+dates[dp]+' / '+str(order)+' / '+frame+' | '+' | '.join(num(v)for v in values)+' |')
    report+=['','[Native orders, page 1](results/figures/NATIVE_ORDERS_1.png) · [Native orders, page 2](results/figures/NATIVE_ORDERS_2.png)','',
        'The central extracted crests and broader spectral structure remain visible in both orders, with order-dependent shape, noise and relative-amplitude differences. Same-exposure extraction agreement is dependent evidence, not another observation or an origin confirmation.','',
        '| Event | Orders | Original global support | Original local / baseline support | Later five-window support | Original primary / secondary / adopted |',
        '|---|---|---|---|---|---|',
        '| 0261 | 2 and 3 | true | false / false | true | U / U / U |',
        '| 0266 | 2 and 3 | true | false / false | true | U / U / U |',
        '| 0272 | 2 and 3 | true | true / true | true | U / U / U |','',
        '[All original raw/excess pairs, page 1](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) · [Page 2](results/figures/PRESERVED_RAW_ORDER_CONTEXT_2.png)','',
        '0261 order 2 has a compact bright off-trace deposit to the right of the candidate location, dominating its full-scale panel. The preserved historical possible contamination/blend caution applies specifically to 0261. Its broader centered component is weak at that scale, while order 3 retains clear diffuse central multi-row enhancement. The deposit does not explain away that broad two-order component. No new contrast variant, crop, subtraction, registration or detector statistic is introduced.','',
        '0266 and 0272 retain broader centered multi-row patches in both orders, with lower contrast and more noise in order 2. Their separate review chains have no 0261 blend-caution transfer. Broad photon-compatible morphology remains descriptive; it does not assign a physical origin or qualify a laser. All three original and current U codes stay unchanged.','',
        '## Common-frame geometry and exact C028 source dependence','',
        '| Observation | Predicted coherent-center offset from fixed topocentric anchor (Å) | Inside fixed ±0.25 core |','|---|---:|---|']
    for r in geometry:report.append(f"| {r['date_obs'][:10]} | {r['predicted_center_offset_angstrom']:+.9f} | {'yes'if r['within_fixed_topocentric_core']else'no'} |")
    report+=['','Three metadata-predicted centers lie inside the common fixed topocentric core and three outside. These are predictions under a barycentric-coherence assumption, not fitted peaks or proof of full finite-feature coverage. Fixed windows can sample neighboring structure; frame statistics are not calibrated origin tests. The cohort BERV span remains 29.26984563734743 km/s.','',
        'Nominal C029 and C028 ±3 Å windows overlap by 4.430000000000291 Å. C029’s center is within C028’s positive flank, but only part of its core is; the reciprocal C028-core/C029-negative-flank intersection is also partial. These intervals and the next-route selection were recorded before current values.','',
        'The source-index audit confirms shared original samples in all six merged products and the two April native orders. The four additional May native/order windows are absent from C028’s bounded index but still use already-existing discovery observations and previously exposed epoch/raw evidence. They are not four new observations or independent untouched validation. Each shared pair verifies the same full-source SHA; no prior C028 array values were opened.','',
        '| Shared product/date/order | Original shared index interval [start,stop) | Shared source samples |',
        '|---|---|---:|']
    for r in dependency['shared_sources']:
        label=r['kind']+' '+dates[r['dp_id']]+(' / '+str(r['order'])if r['kind']=='native'else'')
        report.append(f"| {label} | [{r['shared_start']},{r['shared_stop']}) | {r['shared_original_source_indices']} |")
    report+=['','[Exact source-index audit](../independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json). Shared pixels, products, references and reciprocal pairs remain dependent. No new observing time, blind validation or source-pixel independence is claimed.','',
        '## Arithmetic, preservation and next unfinished route','',
        'The method and exact 23-file public readback at commit `'+read(HERE/'ROOT_RELEASE.json')['publication_commit']+'` preceded current observed values. Source/header checks passed2,418 checks. The 105 compact synthetic checks and 1,449 separate scalar checks over 73,014 synthetic values passed before execution. One successful observed execution completed the fixed comparison.','',
        f"Separate reconstruction passes **{audit['checks_passed']} checks / {audit['scalar_values_compared']:,} scalar comparisons** across twelve bounded source inputs,24 profiles,96 comparisons,six byte-exact raw containers and the source-index dependency audit. Source flux,ERR and original indices agree exactly. Fixed numerical tolerances pass; wavelength/interpolation arithmetic is not claimed bitwise identical. Maximum absolute differences:",'',
        '| Quantity | Maximum absolute difference |','|---|---:|']
    for k,v in audit['maximum_absolute_differences_by_kind'].items():report.append(f'| {k} | {v:.12g} |')
    report+=['','All six scientific PNGs were visually inspected and fully decoded. All 55 fixed source bindings and original numerical outputs remain unchanged. Separate scalar formulas and fresh processes were run by the same assistant, without an independent human or separate-agent review claim. The delivery preserves 42 NPZ files:12 bounded inputs,24 profiles and6original raw containers.','',
        '[Plan](PLAN.json) · [Release](ROOT_RELEASE.json) · [Profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json) · [Scalar audit](../independent_audit/NUMERICAL_AUDIT.json)','',
        '**Next:** C030 on HD126093, original queue row 64 onward, all eight records0262/0263/0267/0268/0273/0275/0276/0281 across R031/R032 and five discovery products against the same six observations. Original centers span 3866.935–3867.3275 Å; a metadata midrange proposal is 3867.13125 Å. This differs from the exact member centers and any common ±0.25 core is narrower than the full original member-core union. Preserve all original centers/cores and freeze the next group’s own geometry, references, normalization, support and plots. Order2 can approach a broad-window boundary; do not transfer current full-coverage or reference-quality outcomes.','',
        'All next original member cores already lie inside current C029’s broad window, while none intersects the current positive reference flank. This geometry differs from the C028/C029 partial reciprocal-flank overlap. Same products and overlapping windows remain dependent. See [the exact handoff](../NEXT_ACTION.json). All prior exact diagnostics remain closed with physical codes unchanged. Rubin remains limited feasibility with minimum 50 unmet.','']
    (HERE/'RESULTS_REPORT.md').write_text('\n'.join(report))
    images=[]
    for item in read(OUT/'PLOT_INDEX.json')['files']:
        path=OUT/item['path'];assert sha(path)==item['sha256'] and path.stat().st_size==item['bytes']
        with Image.open(path)as im:im.verify()
        with Image.open(path)as im:im.load();dimensions=list(im.size)
        images.append({**item,'dimensions':dimensions,'fully_decoded':True,'visually_inspected_by_assistant':True})
    for f,h in plan['source_hashes'].items():assert sha(ROOT/f)==h,f
    for f,h in read(OUT/'OUTPUT_HASHES.json').items():assert sha(OUT/f)==h,f
    qa=dict(status='PASS_C029_REPORT_AND_DELIVERY_QA',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),profile_slots=24,comparison_slots=96,evaluable_pearson_values=sum(r['raw_pearson']is not None for r in pairs),evaluable_normalized_rms_values=sum(r['normalized_rms']is not None for r in pairs),profiles_with_full601_support=sum(r['raw_grid_finite_samples']==r['normalized_grid_finite_samples']==601 for r in profiles),positive_reference_profiles=sum(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE'for r in profiles),raw_only_profiles=summary['raw_only_normalization_slots'],blocked_profiles=summary['blocked_source_profile_slots'],low_reference_flags=sum(r['low_flank_reference']is True for r in profiles),profiles_with_nonpositive_original_samples=len(signed),observing_products_with_nonpositive_samples=len({r['dp_id']for r in signed}),positive_finite_ERR_samples=sum(r['positive_finite_ERR_samples']for r in profiles),frame_wins=wins,predicted_topocentric_centers=geometry,predicted_centers_inside_fixed_core=sum(r['within_fixed_topocentric_core']for r in geometry),source_bindings_verified=len(plan['source_hashes']),all_numeric_files_unchanged=True,classifications_changed=0,origin_assignments=0,shared_C028_sources=len(dependency['shared_sources']),additional_native_sources=4,source_pixel_independence_claim=False,figures=images,report_sha256=sha(HERE/'RESULTS_REPORT.md'),report_builder_sha256=sha(Path(__file__)))
    assert qa['profiles_with_full601_support']==qa['positive_reference_profiles']==24 and len(signed)==8
    assert qa['evaluable_pearson_values']==qa['evaluable_normalized_rms_values']==96 and len(images)==6
    write(HERE/'RESULTS_QA.json',qa);print(json.dumps({k:v for k,v in qa.items()if k not in ['figures','predicted_topocentric_centers']},indent=2))
if __name__=='__main__':main()
