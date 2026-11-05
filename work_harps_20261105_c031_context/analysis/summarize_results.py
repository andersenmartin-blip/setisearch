"""Describe the frozen C031 outputs without refitting or changing classifications."""
from pathlib import Path
import collections, datetime, hashlib, json
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
PHASE=HERE.parent
OUT=HERE/'results'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')

def main():
    plan=read(HERE/'PLAN.json');summary=read(OUT/'SUMMARY.json');profiles=read(OUT/'PROFILE_METRICS.json');pairs=read(OUT/'COMPARISONS.json')
    audit=read(PHASE/'independent_audit/NUMERICAL_AUDIT.json')
    hashes=read(OUT/'OUTPUT_HASHES.json')
    assert all(sha(OUT/p)==h for p,h in hashes.items())
    frame_wins={};exceptions=[]
    for region in ['core','broad_pattern']:
        rows=[r for r in pairs if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY'and r['region']==region and not r['identical_product_self_pair']]
        idx={(r['dp_id'],r['reference_dp_id'],r['frame']):r for r in rows}
        directed={(dp,ref)for dp,ref,frame in idx}
        w=dict(nonself_directed_pairs=len(directed),distinct_unordered_relationships=len({tuple(sorted(p))for p in directed}),reciprocal_discovery_pairs=len({tuple(sorted(p))for p in directed if p[::-1]in directed}))
        for quantity,prefer_low,label in [('raw_pearson',False,'raw_r'),('normalized_rms',True,'normalized_rms')]:
            counts=collections.Counter()
            for dp,ref in sorted(directed):
                b=idx[dp,ref,'barycentric'][quantity];t=idx[dp,ref,'topocentric'][quantity]
                if b is None or t is None:key='unmeasurable'
                elif b==t:key='tie'
                else:key='barycentric'if ((b<t)if prefer_low else(b>t))else'topocentric'
                counts[key]+=1
                if key!='barycentric':exceptions.append(dict(region=region,quantity=quantity,dp_id=dp,reference_dp_id=ref,barycentric_value=b,topocentric_value=t,result=key))
            w[label]=dict(counts)
        frame_wins[region]=w
    containers=[]
    for p in sorted(OUT.rglob('*.npz')):
        with np.load(p,allow_pickle=False)as z:
            arrays={k:dict(shape=list(z[k].shape),dtype=str(z[k].dtype))for k in z.files}
        containers.append(dict(path=str(p.relative_to(PHASE)),bytes=p.stat().st_size,sha256=sha(p),arrays=arrays))
    assert len(containers)==50
    figures=[]
    for p in sorted((OUT/'figures').glob('*.png')):
        with Image.open(p)as im:im.load();size=list(im.size)
        figures.append(dict(path=str(p.relative_to(PHASE)),sha256=sha(p),pixels=size))
    assert len(figures)==6
    support=read(PHASE/'independent_audit/MEMBER_CORE_SUPPORT.json')['records']
    q=dict(profile_slots=len(profiles),comparison_slots=len(pairs),evaluable_pearson_values=sum(r['raw_pearson']is not None for r in pairs),evaluable_normalized_rms_values=sum(r['normalized_rms']is not None for r in pairs),profiles_with_full601_raw_support=sum(r['raw_grid_finite_samples']==601 for r in profiles),partial_raw_profile_slots=sum(0<r['raw_grid_finite_samples']<601 for r in profiles),partial_raw_sample_counts=sorted({r['raw_grid_finite_samples']for r in profiles if r['raw_grid_finite_samples']<601}),positive_reference_profiles=sum(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE'for r in profiles),raw_only_slots=audit['raw_only_slots'],low_reference_profiles=[{k:r[k]for k in ['kind','dp_id','order','frame','flank_reference','first_difference_noise_proxy']}for r in profiles if r['low_flank_reference']is True],profiles_with_nonpositive_original_samples=sum(r['window_nonpositive_fraction']is not None and r['window_nonpositive_fraction']>0 for r in profiles),positive_finite_ERR_samples=sum(r['positive_finite_ERR_samples']for r in profiles),frame_wins=frame_wins,exceptions=exceptions,original_member_support_records=len(support),original_member_nominal_grid_centers=sorted({r['nominal_grid_centers']for r in support}),all_original_member_core_raw_support_complete=all(r['finite_raw_grid_centers']==r['nominal_grid_centers']for r in support),original_member_raw_only_support_records=sum(r['finite_normalized_grid_centers']==0 for r in support),native_broad_unevaluable_raw_rows=[{k:r[k]for k in ['dp_id','order','frame','region','raw_pearson_block_reason','common_finite_raw_samples']}for r in pairs if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED'and r['raw_pearson']is None])
    result=dict(schema='HARPS_C031_RESULTS_QA_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS_FIXED_OUTPUT_DESCRIPTION_AND_CONTAINER_DECODE',summary=q,npz_containers=containers,figures=figures,original_numeric_hashes_unchanged=True,labels_changed=0,new_fits_or_variants=0,public_method_publication_verified=False,public_preregistration_claim=False)
    write(HERE/'RESULTS_QA.json',result)
    lines=['# C031 / HD126093: fixed joint context','', '**All four original records remain U. No qualified laser candidate or physical origin is established.**','',
        'Four discovery references and six existing April–July 2025 observations produced 28 profiles and 128 comparisons. The common midpoint is 3868.1499999999996 air Å. No observations or observing time were added.','',
        '## Frame comparisons','',
        'Each row below describes 20 directed nonself comparisons. They represent 14 distinct unordered observation relationships with six reciprocal discovery pairs among only six observations. Sixteen identical-product self comparisons remain labeled separately across frames and regions.','',
        '| Region | Higher barycentric raw correlation | Lower barycentric normalized RMS |','|---|---:|---:|']
    for region,w in frame_wins.items():lines.append(f"| {region} | {w['raw_r'].get('barycentric',0)}/20 | {w['normalized_rms'].get('barycentric',0)}/20 |")
    lines+=['','In the common core, the May 30 observation compared with the May 29 discovery has better topocentric raw correlation and normalized RMS. In the surrounding pattern, the June 25 observation compared with the June 27 discovery has better topocentric values. Both exceptions are retained; they are different directed relationships.','',
        '| Exception | Barycentric raw r | Topocentric raw r | Barycentric RMS | Topocentric RMS |','|---|---:|---:|---:|---:|']
    for region in ['core','broad_pattern']:
        er=[r for r in exceptions if r['region']==region];corr=next(r for r in er if r['quantity']=='raw_pearson');rms=next(r for r in er if r['quantity']=='normalized_rms')
        lines.append(f"| {region} | {corr['barycentric_value']:.9f} | {corr['topocentric_value']:.9f} | {rms['barycentric_value']:.9f} | {rms['topocentric_value']:.9f} |")
    lines+=['','The fixed pattern generally aligns better barycentrically, but this dependent descriptive result does not identify its physical cause. No stellar radial velocity, center, lag, width, continuum, background or mask was fitted.','',
        '## Coverage and signed references','',
        f"{q['partial_raw_profile_slots']} order-2 frame profiles retain partial broad support, with {q['partial_raw_sample_counts']} finite samples out of 601. The other {q['profiles_with_full601_raw_support']} profiles have all 601 finite raw samples.",
        '', 'The June 27 and July 16 barycentric order-2 profiles have insufficient finite right-flank support and remain RAW_ONLY. Their raw cores remain available. The July 16 topocentric order-2 reference is positive but explicitly flagged LOW FLANK REFERENCE. No reference outcome is transferred between frames.','',
        f"Raw Pearson is evaluable in {q['evaluable_pearson_values']}/128 rows; normalized RMS in {q['evaluable_normalized_rms_values']}/128. The three unevaluable raw correlations are barycentric order-2 surrounding comparisons with 424,410 and404 common samples,below the fixed440 gate. The two raw-only barycentric cores also lack normalized RMS. All missing results and reasons remain in the complete tables.",
        '',f"{q['profiles_with_nonpositive_original_samples']} profiles retain nonpositive original samples. ERR has no positive finite support. Structured flanks and first-difference noise proxies do not establish calibrated significance, false-alarm probability, linewidth or sensitivity.",
        '', '## Original member cores and raw evidence','',
        'The common ±0.25 Å core is not the union of the four original member cores. Exact original centers are 3868.1549999999997,3868.1525,3868.145 and3868.145 air Å. Every marker,boundary and own discovery BERV remains. The surrounding region can contain original-core edges.',
        '',f"All {len(support)} profile/member support records are retained,with nominal counts {q['original_member_nominal_grid_centers']}. All original cores have full finite raw support; {q['original_member_raw_only_support_records']} support records have no normalized samples because their parent profiles are raw-only. No extra member-specific correlation or fit was added.",
        '', 'All eight original event/order raw containers remain byte-exact. Original local/baseline mapping is true only for0277/order3 and0282/order3; global/later support is true for all eight. Four original U/U/U chains and event-specific noisy morphology/additional uncertainty remain. No0261-specific contamination caution transfers.',
        '', 'All14 current bounded source windows share original indices with C030. The dependency audit reads prior index metadata,not prior arrays. No blind or source-pixel-independent validation is claimed.',
        '', '## Validation and publication status','',
        f"Input custody/header checks:2,845 across288 native header-order records. Compact synthetic checks:118. Separate scalar preflight:1,449 checks over73,014 values. Observed reconstruction:{audit['checks_passed']} checks over{audit['scalar_values_compared']:,} values. All50 NPZ containers and6 fixed scientific PNGs decode. Separate scalar implementation and visual inspection are by the same assistant;no independent human or separate-agent review.",
        '', 'The analysis was frozen and byte-verified in a **local Git commit before current arithmetic**. Automatic approval review blocked public GitHub disclosure. This is **not public preregistration**. The complete C031 package remains unpublished pending direct user approval. C030 PR27 was already merged and its previous work branch synchronized.',
        '', '## Next original route','',
        'C033/R035 begins at original queue row67: four records0265/0270/0274/0279 and four own discovery references,metadata midpoint3880.35 air Å. It was selected before C031 values by original queue order. C032 remains pending later in that order; it is not silently skipped. Restore own native/raw inputs,scan all72 orders per product and freeze its separate method. Completed exact diagnoses remain closed despite physical U. Rubin remains limited feasibility with minimum50 unmet.',
        '', '## Fixed figures','']
    for f in figures:lines += [f"![{Path(f['path']).stem}](results/figures/{Path(f['path']).name})",'']
    (HERE/'RESULTS_REPORT.md').write_text('\n'.join(lines).rstrip()+'\n')
    print(json.dumps(q,indent=2))

if __name__=='__main__':main()
