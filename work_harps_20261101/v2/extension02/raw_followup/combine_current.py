"""Root-adopted follow-up overlay; preserve all original and baseline catalogs."""
from pathlib import Path
import csv,json,hashlib,collections,datetime
O=Path(__file__).resolve().parent;E=O.parent;V=E.parent
paths=[O/'BASELINE_SELECTED_EVENT_DISPOSITIONS.csv',O/'BASELINE_V2_ALL336_DISPOSITIONS.csv',O/'mapping_followup/FOLLOWUP_DISPOSITIONS.csv',V/'followup_synthesis/CUMULATIVE_333.csv',E/'production/V2_HITS.csv',V/'production/V2_HITS.csv']
def rows(p):return list(csv.DictReader(p.open()))
def write(p,rs):
 with p.open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(V)):sha(p)for p in paths}
a=rows(paths[0]);m={r['review_id']:r for r in rows(paths[2])};assert len(a)==65 and len(m)==9
assert all(r['visual_review_agreement']=='True'and r['coordinates_changed']=='False'and r['final_physical_origin_confirmed']=='False'for r in m.values())
for r in a:
 k=r['review_id'];r['current_code']='M'if r['baseline_code']=='I'else r['baseline_code'];r['current_disposition']=r['baseline_disposition'];r['wider_followup_applied']=k in m;r['current_evidence']=r['note'];r['current_evidence_table']='BASELINE_SELECTED_EVENT_DISPOSITIONS.csv'
 if k in m:
  q=m[k];assert r['baseline_code']==q['baseline_code']and r['dp_id']==q['dp_id'];r['current_code']=q['proposed_code'];r['current_disposition']=q['proposed_status'];r['current_evidence']=q['evidence_first'];r['current_evidence_table']='mapping_followup/FOLLOWUP_DISPOSITIONS.csv'
write(O/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',a);by={r['review_id']:r for r in a}
new=rows(paths[1]);assert len(new)==336
for r in new:
 k=r['candidate_id'];r['current_code']=by[k]['current_code']if k in by else'N';r['current_disposition']=by[k]['current_disposition']if k in by else'UNREVIEWED_RAW_FOLLOWUP';r['wider_followup_applied']=k in m;r['current_evidence']=by[k]['current_evidence']if k in by else'Not selected for this8-exposure raw follow-up; retained for subsequent review.';r['current_evidence_table']=by[k]['current_evidence_table']if k in by else'audit/UNREVIEWED_V2_EVENTS.csv';r['final_physical_origin_confirmed']=False
assert sum(r['current_code']=='N'for r in new)==277
write(O/'CURRENT_V2_ALL336_DISPOSITIONS.csv',new)
old=rows(paths[3]);oldhits=rows(paths[5]);newhits={r['candidate_id']:r for r in rows(paths[4])};status_codes={'PROVISIONAL_DETECTOR_ARTIFACT':'A','PROVISIONAL_ATMOSPHERIC_OI':'O','UNRESOLVED_SPECTRAL_FEATURE':'U','INSUFFICIENT_RAW_MAPPING':'M'};master=[]
for r in old:
 match=[h for h in oldhits if h['dp_id']==r['dp_id']and abs(float(h['fitted_center_angstrom'])-float(r['fitted_center_bary_air_angstrom']))<1e-8];assert len(match)==1
 master.append(dict(cohort='V2_first100',review_id=r['review_id'],dp_id=r['dp_id'],target=r['canonical_target'],fitted_center_bary_air_angstrom=r['fitted_center_bary_air_angstrom'],input_sha256=match[0]['input_sha256'],current_code=status_codes[r['current_followup_status']],current_disposition=r['current_followup_status'],evidence_table='followup_synthesis/CUMULATIVE_333.csv',final_physical_origin_confirmed=False))
for r in new:
 h=newhits[r['candidate_id']];assert h['dp_id']==r['dp_id']and h['input_sha256']==r['source_input_sha256']
 master.append(dict(cohort='V2_extension02',review_id=r['candidate_id'],dp_id=r['dp_id'],target=r['target'],fitted_center_bary_air_angstrom=h['fitted_center_angstrom'],input_sha256=h['input_sha256'],current_code=r['current_code'],current_disposition=r['current_disposition'],evidence_table='extension02/raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv',final_physical_origin_confirmed=False))
assert len(master)==len({r['review_id']for r in master})==669
write(V/'CURRENT_V2_DISPOSITIONS.csv',master)
vc=dict(collections.Counter(r['current_code']for r in new));v1c=dict(collections.Counter(r['current_code']for r in a if r['detector']=='V1'));allc=dict(collections.Counter(r['current_code']for r in master))
assert vc=={'U':6,'A':44,'O':8,'N':277,'M':1}and v1c=={'O':3,'A':3}
assert all(sha(V/p)==h for p,h in before.items())
s=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='ROOT_ADOPTED_CONSERVATIVE_OVERLAY',basis='Both nine-record reviews agree; exact fresh-process reconstruction passed; root inspected all3 neutral review pages and retains every covering-order limitation.',main_exposures=300,main_targets=20,main_exposure_seconds=255148.743,main_exposure_hours=255148.743/3600,V1_exposures=300,V1_hits=22,V2_exposures=200,V2_events=669,older_V2_events=333,new_V2_events=336,current_new_V2_counts=vc,current_new_V1_counts=v1c,current_all_V2_counts=allc,V2_raw_reviewed=392,V2_raw_unreviewed=277,old95_epoch_context={'input_pool_main_exposures':200,'relevant_unique_exposures':117,'barycentric_persistent':91,'observer_frame':3,'weak_line':1,'new100_not_included':True},source_hashes=before,all_original_and_baseline_files_unchanged=True,all_origins_provisional=True,homogeneous_raw_mapping_method=False,code_legend={'A':'provisional detector artifact','O':'provisional atmospheric OI','U':'unresolved spectral feature','M':'insufficient raw mapping','N':'no raw review yet'},limits='Post-detection follow-up with heterogeneous historical controls; not a global false-alarm rate, sensitivity estimate, or laser exclusion. Six newV1 records match same-exposureV2 records and are not additional independent features.')
(O/'CURRENT_SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n');(V/'CURRENT_STATUS.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({k:s[k]for k in ['current_new_V2_counts','current_new_V1_counts','current_all_V2_counts','V2_raw_reviewed','V2_raw_unreviewed']},indent=2))
