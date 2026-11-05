"""Describe the frozen C033 outputs without refitting or changing classifications."""
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
    result=dict(schema='HARPS_C033_RESULTS_QA_V1',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS_FIXED_OUTPUT_DESCRIPTION_AND_CONTAINER_DECODE',summary=q,npz_containers=containers,figures=figures,original_numeric_hashes_unchanged=True,labels_changed=0,new_fits_or_variants=0,public_method_publication_verified=True,public_preregistration_claim=False)
    write(HERE/'RESULTS_QA.json',result)
    print(json.dumps(q,indent=2))

if __name__=='__main__':main()
