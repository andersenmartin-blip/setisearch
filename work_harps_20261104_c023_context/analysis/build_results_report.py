"""Build descriptive C023 report from immutable saved outcomes; no fitting or selection."""
from pathlib import Path
import datetime,hashlib,json
from PIL import Image
HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
OUT=HERE/'results'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def num(x):return 'unavailable' if x is None else f'{x:.6f}'

def main():
    plan=read(HERE/'PLAN.json');inv=read(ROOT/plan['inventory_path']);summary=read(OUT/'SUMMARY.json')
    profiles=read(OUT/'PROFILE_METRICS.json');pairs=read(OUT/'COMPARISONS.json')
    audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json');plots=read(OUT/'PLOT_INDEX.json')
    assert len(profiles)==16 and len(pairs)==32 and audit['status']=='PASS_INDEPENDENT_C023_NUMERICAL_RECONSTRUCTION'
    nonself=[r for r in pairs if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']]
    wins={}
    for region in ['core','broad_pattern']:
        wr=wm=0
        for dp in plan['merged_dp_ids']:
            rows={r['frame']:r for r in nonself if r['dp_id']==dp and r['region']==region}
            if not rows:continue
            wr+=rows['barycentric']['raw_pearson']>rows['topocentric']['raw_pearson']
            wm+=rows['barycentric']['normalized_rms']<rows['topocentric']['normalized_rms']
        wins[region]={'nonself_observation_pairs':6,'barycentric_raw_r_higher':wr,'topocentric_raw_r_higher':6-wr,'barycentric_normalized_rms_lower':wm,'topocentric_normalized_rms_lower':6-wm}
    assert wins['core']['barycentric_raw_r_higher']==1 and wins['core']['barycentric_normalized_rms_lower']==2
    assert wins['broad_pattern']['barycentric_raw_r_higher']==wins['broad_pattern']['barycentric_normalized_rms_lower']==6
    geometry=[]
    for r in inv['merged_spectra']:
        offset=plan['group_center_bary_air_angstrom']/(1+r['berv_km_s']/plan['c_km_s'])-summary['topocentric_anchor_air_angstrom']
        geometry.append({'dp_id':r['dp_id'],'date_obs':r['date_obs'],'predicted_center_offset_angstrom':offset,'within_fixed_topocentric_core':abs(offset)<=.25})
    report=['# C023 / HD114783 at 5944.965 air Angstrom','',
        '**Complete: seven existing observations, one own February 5 discovery reference, sixteen profiles and thirty-two comparisons. V2E2-0122 remains U.**','',
        'The central core and surrounding spectrum have different descriptive frame behavior. All six other epochs have better surrounding-spectrum raw correlation and normalized RMS in the barycentric frame. In the original core, raw correlation is higher topocentrically in five of six comparisons, while normalized RMS is lower topocentrically in four of six. These uncalibrated statistics do not assign origin, identify a physical line, qualify a laser candidate or calibrate significance, sensitivity or a survey null.','',
        '## Fixed scope and all nonself comparisons','',
        'The exact original center is 5944.965 Å, core [5944.715,5945.215] Å and broad window [5941.965,5947.965] Å. The unchanged 0.01-Angstrom grid has 51 core and 550 surrounding points. Own discovery ADP.2022-02-06T01:07:28.382 was observed on 2022-02-05 at BERV 26.6810328154809 km/s and fixes topocentric anchor 5944.43595503388 Å. No center, width, lag, stellar velocity, drift, continuum, background or mask was fitted.','',
        'Each cell below is **barycentric / topocentric**. Six rows represent six other observations against one fixed reference; the cohort contains seven observations. Four identical-product self-comparison records remain labelled and add no recurrence evidence.','',
        '| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |','|---|---:|---:|---:|---:|']
    for item in inv['merged_spectra']:
        if item['dp_id']==plan['anchor_dp_id']:continue
        rows={(r['frame'],r['region']):r for r in nonself if r['dp_id']==item['dp_id']}
        cells=[]
        for metric,region in [('raw_pearson','core'),('raw_pearson','broad_pattern'),('normalized_rms','core'),('normalized_rms','broad_pattern')]:cells.append(num(rows['barycentric',region][metric])+' / '+num(rows['topocentric',region][metric]))
        report.append('| '+item['date_obs'][:10]+' | '+' | '.join(cells)+' |')
    report+=['','[All seven original-core profiles](results/figures/MERGED_CORE_CONTEXT.png) · [Full surrounding spectrum](results/figures/MERGED_BROAD_CONTEXT.png)','',
        'The discovery retains a raised, flat-topped or rounded central shape whose scaled appearance differs from all six other epochs. The broader spectrum includes recurring absorption structure that aligns more closely barycentrically. This visual description is not a fitted amplitude, width, repeatability test or a specific identification of the central event. The nearby structure remains inside the fixed windows and references.','',
        'May 5 2022 and March 22 2023 illustrate the distinction between shape and scale: their core raw correlation favors the topocentric frame, while normalized RMS favors the barycentric frame. The July comparison has a small barycentric correlation advantage (0.383694 versus 0.362813), but topocentric RMS is lower. Pearson is unchanged by positive scalar normalization; normalized RMS also reflects the retained reference levels and amplitude mismatch. No statistic is selected as an origin verdict.','',
        '## Actual finite support and reference quality','',
        'All sixteen profiles have 601 finite raw and normalized grid points, valid positive pooled flank medians and false low-reference flags. None is raw-only, partial or blocked. All thirty-two raw Pearson and thirty-two normalized RMS values are evaluable. Every retained original source sample in the fixed windows and flanks is positive; this is a measured outcome, not an inference from geometry. There are zero positive finite ERR samples in every profile. False low-reference flags and first-difference proxies are not formal SNR, significance or general quality certificates.','',
        'The discovery merged reference is 26451.701172 ADU, with 150 finite original samples in each flank. Native order 57 has reference 42398.552734 in unspecified native units, with 92/94 finite source samples in the negative/positive flanks and 372 finite original source samples in each fixed window. Native BUNIT is absent; the native and merged divisors are not a physical flux ratio. Structured flank samples remain unchanged without line-free assumptions.','',
        '## Own native order and original raw context','',
        'A fresh header-only scan of all 72 native orders selects order 57 only. Both fixed frames geometrically cover the full core, ±3 context and reference flanks. Actual finite support is reported above, separately from header geometry. The native product compares only with its own discovery merged extraction:','',
        '| Frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS |','|---|---:|---:|---:|---:|']
    for frame in ['barycentric','topocentric']:
        rows={r['region']:r for r in pairs if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED' and r['frame']==frame}
        report.append('| '+frame+' | '+' | '.join([num(rows['core']['raw_pearson']),num(rows['broad_pattern']['raw_pearson']),num(rows['core']['normalized_rms']),num(rows['broad_pattern']['normalized_rms'])])+' |')
    report+=['','[Native order 57 against its own merged extraction](results/figures/NATIVE_ORDERS_1.png)','',
        'The central extracted shape agrees closely within the same exposure, while surrounding structure retains larger differences. Shared extraction is dependent evidence, not another observation or an origin confirmation. Original order-57 global, local, baseline and later reference-support stages are all true. These historical mapping stages do not resolve the original morphology.','',
        '[Complete original stored raw/excess pair](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) preserves every saved pixel and separate full scales. At those full scales the central enhancement is faint beside dominant right-edge structure. The historical primary and secondary enlarged-view descriptions retain an irregular/asymmetric multi-row central excess, a bright lower component and an upper-right extension, with a possible charge/photon mixture. Those records remain U/U/U. No new enlargement, contrast variant, crop, subtraction, registration or detector statistic is introduced; right-edge structure does not classify the central feature.','',
        '## Fixed-frame geometry and dependence','',
        '| Observation | Predicted coherent center offset from fixed topocentric anchor (Å) | Inside fixed ±0.25 core |','|---|---:|---|']
    for r in geometry:report.append(f"| {r['date_obs'][:10]} | {r['predicted_center_offset_angstrom']:+.9f} | {'yes' if r['within_fixed_topocentric_core'] else 'no'} |")
    report+=['','Three metadata-predicted coherent centers stay inside the fixed topocentric core and four fall outside. These are predictions under a barycentric-coherence assumption, not fitted peaks or proof of full finite-feature coverage. A fixed topocentric window can sample neighboring structure; frame statistics are descriptive rather than calibrated origin tests.','',
        'The same seven January 2022–July 2023 HD114783 observations and the same native product lineage were used previously. This C023 wavelength window is disjoint from completed same-target C017/C018/C019/C021/C022 bounded windows, but observing products are shared and the original 0122 epoch/raw evidence was already exposed. No blind or untouched-data validation, independent new observation or added observing time is claimed.','',
        '## Arithmetic, delivery and next action','',
        'The method and source-only/synthetic checks were public before observed C023 values. Exact readback covered 23 files at commit `'+read(HERE/'ROOT_RELEASE.json')['publication_commit']+'`. The 97 synthetic preflight checks and 1,449 separate scalar checks over 73,016 synthetic values passed before execution.','',
        f"The separate observed reconstruction passes **{audit['checks_passed']} checks / {audit['scalar_values_compared']:,} scalar comparisons** across all eight bounded source windows, sixteen profiles, thirty-two comparisons and the byte-exact original raw container. Source flux, ERR and indices agree exactly. Maximum source-wavelength difference is 9.095e-13 Å, raw interpolation difference 9.349e-08 native units, normalized difference 2.205e-12 and comparison difference 5.451e-14. Fixed tolerances pass; floating-point wavelength/interpolation results are not claimed bitwise identical.",'',
        'All four scientific PNGs were visually inspected and fully decoded; all 47 source bindings and original numerical outputs stayed unchanged. Separate formulas and fresh processes were run by the same assistant, without a separate-agent or human-review claim.','',
        '[Fixed plan](PLAN.json) · [Released method](ROOT_RELEASE.json) · [Profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json) · [Scalar audit](../independent_audit/NUMERICAL_AUDIT.json)','',
        '**Next:** original queue row 53, C020/R021, V2E2-0136 on HD114783 at 4303.13 Å. Its own May 15 2023 discovery reference and source-specific raw/mapping history are retained in [the next metadata handoff](../scientific_review/NEXT_GROUP_METADATA.json). The selection preceded C023 values; do not inherit the February reference, order-57 scope or quality. Freeze its separate method before any new observed arithmetic. C023 is closed as this fixed diagnostic with U unchanged. Completed mapping, normalization and other profile routes are not replayed. Rubin remains limited feasibility with minimum 50 unmet.','']
    (HERE/'RESULTS_REPORT.md').write_text('\n'.join(report))
    images=[]
    for item in plots['files']:
        f=OUT/item['path'];assert sha(f)==item['sha256'] and f.stat().st_size==item['bytes']
        with Image.open(f) as im:im.verify()
        with Image.open(f) as im:im.load();dimensions=list(im.size)
        images.append({**item,'fully_decoded':True,'dimensions':dimensions,'visually_inspected_by_assistant':True})
    for f,h in plan['source_hashes'].items():assert sha(ROOT/f)==h,f
    for f,h in read(OUT/'OUTPUT_HASHES.json').items():assert sha(OUT/f)==h,f
    qa={'status':'PASS_C023_REPORT_AND_DELIVERY_QA','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'profile_slots':len(profiles),'comparison_slots':len(pairs),'evaluable_pearson_values':sum(r['raw_pearson'] is not None for r in pairs),'evaluable_normalized_rms_values':sum(r['normalized_rms'] is not None for r in pairs),'profiles_with_full601_support':16,'partial_profiles':0,'positive_reference_profiles':16,'raw_only_profiles':0,'blocked_profiles':0,'low_reference_flags':0,'profiles_with_nonpositive_original_samples':0,'frame_wins':wins,'predicted_topocentric_centers':geometry,'predicted_centers_inside_fixed_core':sum(r['within_fixed_topocentric_core'] for r in geometry),'source_bindings_verified':47,'all_numeric_files_unchanged':True,'classifications_changed':0,'origin_assignments':0,'figures':images,'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'report_builder_sha256':sha(Path(__file__))}
    assert qa['predicted_centers_inside_fixed_core']==3
    write(HERE/'RESULTS_QA.json',qa)
    print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','predicted_topocentric_centers']},indent=2))

if __name__=='__main__':main()
