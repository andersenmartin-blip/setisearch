"""Preserve separate reviews and produce explicit baseline ledgers; original files immutable."""
from pathlib import Path
import csv,json,hashlib,collections,datetime
O=Path(__file__).resolve().parent;E=O.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,x):(O/name).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def csvout(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with (O/name).open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
primary=json.loads((O/'PRIMARY_VISUAL_REVIEW.json').read_text());second=json.loads((O/'audit/INDEPENDENT_VISUAL_NOTES.json').read_text());rows=primary['rows'];assert len(rows)==len(second['notes'])==65
agreement=[]
for r in rows:
 code,note=second['notes'][r['review_id']];normalized='I'if code=='M'else code
 agreement.append(dict(review_id=r['review_id'],primary_code=r['primary_code'],second_code_original=code,second_code_normalized=normalized,agree=r['primary_code']==normalized))
assert all(r['agree']for r in agreement)
dump('REVIEW_AGREEMENT.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),primary_sha256=sha(O/'PRIMARY_VISUAL_REVIEW.json'),second_sha256=sha(O/'audit/INDEPENDENT_VISUAL_NOTES.json'),compared_records=65,category_agreements=65,category_disagreements=0,normalization='Primary I and second M both mean insufficient local raw mapping; no other relabeling.',review_scope='Separate AI-agent visual reviews with primary judgments withheld until second was fixed. Both agents knew selection and detector context. Agreement is not blinded scientific validation or human review.',rows=agreement))
byid={r['review_id']:r for r in rows};baseline=[]
for r in rows:baseline.append({k:v for k,v in r.items()if k not in ['primary_code','primary_disposition']}|dict(baseline_code=r['primary_code'],baseline_disposition=r['primary_disposition'],second_review_agrees=True,review_scope='Selected subset; post-detection provisional raw morphology'))
csvout('BASELINE_SELECTED_EVENT_DISPOSITIONS.csv',baseline)
with (E/'production/V2_HITS.csv').open()as f:allv2=list(csv.DictReader(f))
v2ledger=[]
for h in allv2:
 r=byid.get(h['candidate_id']);v2ledger.append(dict(candidate_id=h['candidate_id'],dp_id=h['dp_id'],target=h['canonical_target'],selection_index=h['selection_index'],source_input_sha256=h['input_sha256'],original_production_status=h['status'],selected_for_raw_followup=r is not None,baseline_raw_review_code=r['primary_code']if r else'NOT_SELECTED',baseline_raw_disposition=r['primary_disposition']if r else'UNREVIEWED_NOT_SELECTED_FOR_RAW',note=r['note']if r else'Outside fixed eight-exposure raw follow-up; no raw-origin assessment.',original_production_unchanged=True))
assert len(v2ledger)==336 and sum(r['selected_for_raw_followup']for r in v2ledger)==59
csvout('BASELINE_V2_ALL336_DISPOSITIONS.csv',v2ledger)
with (E/'production/V1_HITS.csv').open()as f:v1=list(csv.DictReader(f))
mapping=json.loads((O/'NATIVE_MAPPING.json').read_text())['orders'];links=[]
for h in v1:
 candidates=[r for r in allv2 if r['dp_id']==h['dp_id']];match=min(candidates,key=lambda r:abs(float(r['fitted_center_angstrom'])-float(h['wave_peak_angstrom'])));delta=float(match['fitted_center_angstrom'])-float(h['wave_peak_angstrom']);assert abs(delta)<.03
 pix1={r['order']:r['native_pixel']for r in mapping if r['review_id']==h['candidate_id']};pix2={r['order']:r['native_pixel']for r in mapping if r['review_id']==match['candidate_id']}
 links.append(dict(V1_id=h['candidate_id'],V2_id=match['candidate_id'],dp_id=h['dp_id'],V2_minus_V1_barycentric_angstrom=delta,native_pixel_difference_by_order={str(o):pix2[o]-pix1[o]for o in pix1 if o in pix2},interpretation='Nearest same-exposure V2 event; raw pages corroborate shared feature. Cross-detector record, not independent exposure or discovery.'))
dump('V1_V2_CROSS_LINKS.json',links)
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selected_exposures=8,selected_targets=5,raw_products=8,ancillary_products=8,all_products_identity_and_hash_verified=True,recorded_known_returned_payload_bytes=210108924,recorded_charged_payload_bytes=210108924,surviving_partial_prefix_bytes_preserved_separately=4194304,partial_prefix_network_provenance='UNKNOWN; see PARTIAL_FILE_ANOMALY.json; excluded from science.',event_records=65,V1_event_records=6,V2_event_records=59,covering_native_order_cutouts=86,mapping_usable_order_cutouts=77,baseline_counts=dict(collections.Counter(r['primary_code']for r in rows)),V1_baseline_counts=dict(collections.Counter(r['primary_code']for r in rows if r['detector']=='V1')),V2_baseline_counts=dict(collections.Counter(r['primary_code']for r in rows if r['detector']=='V2')),V2_all336_counts=dict(collections.Counter(r['baseline_raw_review_code']for r in v2ledger)),V2_raw_unreviewed_not_selected=277,cross_detector_same_exposure_links=6,independent_sky_control_exposures=0,FP_calibration_B_exposures=8,separate_agent_category_agreement=[65,65],original_catalogs_modified=False,complete_new100_raw_triage=False,confirmed_technosignatures=0,physical_origin_assignments_final=False,baseline_preserved_before_any_widened_mapping_followup=True)
dump('BASELINE_SUMMARY.json',summary);print(json.dumps(summary,indent=2))
