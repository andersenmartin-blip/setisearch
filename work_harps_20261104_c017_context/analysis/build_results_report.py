"""Render descriptive tables from already frozen C017 outputs; no fitting or selection."""
from pathlib import Path
import collections,datetime,hashlib,json,platform
from PIL import Image
HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
ROOT=HERE.parents[1]
OUT=HERE/'results'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def num(v): return 'unavailable' if v is None else f'{v:.6f}'

def main():
    plan=read(HERE/'PLAN.json');inv=read(ROOT/plan['inventory_path']);summary=read(OUT/'SUMMARY.json')
    profiles=read(OUT/'PROFILE_METRICS.json');pairs=read(OUT/'COMPARISONS.json')
    audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json');plots=read(OUT/'PLOT_INDEX.json')
    assert len(profiles)==18 and len(pairs)==36 and audit['status']=='PASS_INDEPENDENT_C017_NUMERICAL_RECONSTRUCTION'
    nonself=[r for r in pairs if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']]
    wins={}
    for region in ['core','broad_pattern']:
        count_r=count_rms=0
        for epoch in plan['merged_dp_ids']:
            rows={r['frame']:r for r in nonself if r['dp_id']==epoch and r['region']==region}
            if not rows: continue
            count_r+=rows['barycentric']['raw_pearson']>rows['topocentric']['raw_pearson']
            count_rms+=rows['barycentric']['normalized_rms']<rows['topocentric']['normalized_rms']
        wins[region]={'nonself_observation_pairs':6,'barycentric_r_higher':count_r,'barycentric_normalized_rms_lower':count_rms}
    geometry=[]
    for item in inv['merged_spectra']:
        offset=plan['group_center_bary_air_angstrom']/(1+item['berv_km_s']/plan['c_km_s'])-summary['topocentric_anchor_air_angstrom']
        geometry.append({'dp_id':item['dp_id'],'date_obs':item['date_obs'],'predicted_center_offset_angstrom':offset,'within_fixed_topocentric_core':abs(offset)<=.25})
    report=['# C017 / HD114783 at 3868.175 air Angstrom','',
        '**Complete fixed context: seven existing observations, one February5 discovery, eighteen profiles and thirty-six comparisons. V2E2-0118 remains U.**','',
        'All six other epochs have higher raw Pearson correlation and lower normalized RMS in the barycentric frame, in both the original core and surrounding spectrum. The central rounded, multi-sample peak and neighboring structure recur with retained amplitude differences. These descriptive comparisons do not identify a physical line or origin, establish a laser candidate or calibrate significance, sensitivity or a survey null.','',
        'The original center is3868.175 Å, original core[3867.925,3868.425] Å and broad window[3865.175,3871.175] Å. The fixed601-point grid has51core and550surrounding centers. Own discovery ADP.2022-02-06T01:07:28.382 was observed2022-02-05T07:45:49.762; BERV26.6810328154809km/s fixes topocentric anchor3867.830769460069 Å. No epoch was recentered, and no center, width, lag, stellar velocity, drift, continuum, background or mask was fitted.','',
        '## All six nonself epoch comparisons','',
        'Each cell is **barycentric / topocentric**. The six rows use one fixed reference and six other observations; the total cohort is seven observations. Four identical-product self-comparison records are separately labelled and supply no recurrence evidence.','',
        '| Other observation | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |','|---|---:|---:|---:|---:|']
    for item in inv['merged_spectra']:
        if item['dp_id']==plan['anchor_dp_id']:continue
        rows={(r['frame'],r['region']):r for r in nonself if r['dp_id']==item['dp_id']}
        values=[]
        for metric,region in [('raw_pearson','core'),('raw_pearson','broad_pattern'),('normalized_rms','core'),('normalized_rms','broad_pattern')]:values.append(num(rows['barycentric',region][metric])+' / '+num(rows['topocentric',region][metric]))
        report.append('| '+item['date_obs'][:10]+' | '+' | '.join(values)+' |')
    report+=['','[All seven epochs, original core](results/figures/MERGED_CORE_CONTEXT.png) · [Full surrounding spectrum](results/figures/MERGED_BROAD_CONTEXT.png)','',
        'The broad view retains many recurring peaks and troughs, rather than reducing the spectrum to an isolated central emission line. Native raw and flank-scaled curves retain their original signs. Same-quantity merged y limits match across frames.','',
        '## Both native covering orders and partial support','',
        'The new header-only scan considered all72 native orders and selected orders2 and3 at the exact own discovery center. Order2 ends about+2.1765 Å from the fixed center: it covers518 of601 grid points, including all51core points and467surrounding points. It has163 finite negative-flank and77finite positive-flank source points. Although the full positive-flank wavelength interval is absent, both finite counts exceed the unchanged20-per-side requirement, and467 common surrounding points exceed the unchanged440 gate. Its valid positive normalization does **not** mean full wavelength coverage.','',
        'Order3 and all fourteen merged frame profiles have601finite raw/scaled grid values. All eighteen profiles have usable positive references; none is raw-only, blocked or marked low-reference. All36 Pearson and36 normalized RMS values are evaluable. Order2 contains five preserved nonpositive original window samples in each frame (the same source values reused); no sign clipping occurs. Native ERR is unavailable and no profile has positive finite ERR support. False low-reference flags and first-difference proxies are not formal SNR or general quality certificates.','',
        '| Native order | Frame | Core raw r | Surrounding raw r | Core normalized RMS | Surrounding normalized RMS | Surrounding common points |','|---:|---|---:|---:|---:|---:|---:|']
    for order in [2,3]:
        for frame in ['barycentric','topocentric']:
            rows={r['region']:r for r in pairs if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED' and r['order']==order and r['frame']==frame}
            report.append(f'| {order} | {frame} | '+ ' | '.join([num(rows['core']['raw_pearson']),num(rows['broad_pattern']['raw_pearson']),num(rows['core']['normalized_rms']),num(rows['broad_pattern']['normalized_rms']),str(rows['broad_pattern']['common_finite_raw_samples'])])+' |')
    report+=['','[Both native orders](results/figures/NATIVE_ORDERS_1.png)','',
        'Order2 has visibly weaker extraction agreement and a different scaled shape; order3 tracks the same-exposure merged structure more closely. Native divisors are63.717245 for order2 and227.462486 for order3, versus244.846443ADU in the discovery merged spectrum. Native BUNIT is absent, so native units remain unspecified; these are not physical flux ratios. Same-exposure extraction agreement supplies no independent observation or origin confirmation.','',
        '## Original raw containers and mapping history','',
        '| Order | Original global | Original local | Original baseline | Later reference support |','|---:|---|---|---|---|','| 2 | true | false | false | true |','| 3 | true | true | true | true |','',
        '[Both complete original raw/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain every stored pixel at separate full scales. Both show central vertical/trace-associated enhancements with surrounding variations; order3 also retains a bright right-edge structure. These original stored excess arrays were not newly subtracted. No new crop, contrast variant, registration, detector statistic or model was introduced. Later support leaves original order2 local/baseline failures unchanged. Original primary/secondary/adopted U/U/U remains separate from numerical profile quality and physical origin.','',
        '## Fixed topocentric geometry and reused evidence','',
        '| Observation | Predicted coherent center offset (Å) | Within fixed±0.25core |','|---|---:|---|']
    for row in geometry:report.append(f"| {row['date_obs'][:10]} | {row['predicted_center_offset_angstrom']:+.9f} | {'yes' if row['within_fixed_topocentric_core'] else 'no'} |")
    report+=['','Four predicted centers remain within the fixed February-reference core and three lie outside. These are metadata predictions under a coherence assumption, not fitted centers or proof of full finite-feature coverage. Fixed topocentric comparisons may sample neighboring structure; they are descriptive rather than calibrated origin tests.','',
        'C017 directly reuses the same seven January2022–July2023 HD114783 observing products as completed C018/C019/C021/C022. It overlaps C018 source spectral pixels over[3866.33375,3871.175] Å, width4.8412500000004 Å. The disjoint central cores lie in each other surrounding context; neither intersects the other fixed reference flanks. This core was already exposed in C018. No blind, untouched or independent-data validation and no new observing time is claimed. C019/C021/C022 bounded windows are disjoint but share observing lineage. Other-target numerical wavelength overlaps share no observations or source pixels.','',
        '## Exact method freeze, arithmetic and delivery','',
        'The method, input custody, source-only review,94synthetic checks and1,449 separate scalar checks over73,016synthetic values were public before current observed array access. Exact public readback covered23files at commit`'+read(HERE/'ROOT_RELEASE.json')['publication_commit']+'`.','',
        f"The separate scalar reconstruction passes **{audit['checks_passed']} checks / {audit['scalar_values_compared']:,} scalar comparisons**, reconstructing all9bounded source windows,18profiles,36comparisons and both byte-exact historical raw containers. Source signed flux,ERR and indices agree exactly. Maximum native wavelength difference is4.547e-13 Å, raw interpolation difference2.027e-09native units, normalized difference3.181e-11 and comparison difference5.847e-13. Arithmetic agrees within fixed tolerances; floating-point wavelength/interpolation values are not asserted bitwise identical.",'',
        'All four PNGs were visually inspected and fully decoded. The numerical files and44source bindings remained unchanged. Separate formulas and fresh processes were executed by the same assistant; no separate-agent or human review is claimed.','',
        '[Fixed plan](PLAN.json) · [Released method](ROOT_RELEASE.json) · [Numerical audit](../independent_audit/NUMERICAL_AUDIT.json) · [All profile metrics](results/PROFILE_METRICS.csv) · [All comparisons](results/COMPARISONS.csv) · [Output hashes](results/OUTPUT_HASHES.json)','',
        '## Next original-queue route','',
        '**C023/R024, V2E2-0122 on HD114783 at5944.965 Å**, original queue row41, was selected before C017 values. It precedes C020row53. The own February5 discovery and same seven existing epochs are explicit in [the next metadata handoff](../scientific_review/NEXT_GROUP_METADATA.json). Freshly scan its own72native headers and preserve its own raw/mapping/review history; do not transfer C017 order scope or quality. Freeze that separate analysis before its observed values. Completed mapping, normalization and profile routes are not repeated merely because physical U remains. Rubin remains limited feasibility with minimum50unmet.','']
    (HERE/'RESULTS_REPORT.md').write_text('\n'.join(report))
    visual=[]
    for item in plots['files']:
        p=OUT/item['path'];assert sha(p)==item['sha256'] and p.stat().st_size==item['bytes']
        with Image.open(p) as im:im.verify()
        with Image.open(p) as im:im.load();size=list(im.size)
        visual.append({**item,'fully_decoded':True,'dimensions':size,'visually_inspected_by_assistant':True})
    for p,h in plan['source_hashes'].items():assert sha(ROOT/p)==h,p
    for p,h in read(OUT/'OUTPUT_HASHES.json').items():assert sha(OUT/p)==h,p
    nonpositive=[r for r in profiles if (r.get('window_nonpositive_fraction') or 0)>0]
    qa={'status':'PASS_C017_REPORT_AND_DELIVERY_QA','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'profile_slots':len(profiles),'comparison_slots':len(pairs),'evaluable_pearson_values':sum(r['raw_pearson'] is not None for r in pairs),'evaluable_normalized_rms_values':sum(r['normalized_rms'] is not None for r in pairs),'profiles_with_full601_support':sum(r['raw_grid_finite_samples']==601 for r in profiles),'partial_profiles':2,'partial_profile_finite_grid_points':518,'positive_reference_profiles':sum(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' for r in profiles),'profiles_with_nonpositive_original_samples':len(nonpositive),'barycentric_descriptive_wins':wins,'predicted_topocentric_centers':geometry,'predicted_centers_inside_fixed_core':sum(r['within_fixed_topocentric_core'] for r in geometry),'source_bindings_verified':len(plan['source_hashes']),'all_numeric_files_unchanged':True,'classifications_changed':0,'new_origin_assignments':0,'figures':visual,'report_sha256':sha(HERE/'RESULTS_REPORT.md'),'report_builder_sha256':sha(Path(__file__))}
    write(HERE/'RESULTS_QA.json',qa)
    print(json.dumps({k:v for k,v in qa.items() if k not in ['figures','predicted_topocentric_centers']},indent=2))

if __name__=='__main__':main()
