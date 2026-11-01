"""Reconcile separately saved reviews with explicit root conservative adjudication."""
import collections
from common import *

def main():
 verify_plan();verify_freeze()
 primary=read('PRIMARY_VISUAL_REVIEW.json');secondary=read('SECONDARY_VISUAL_REVIEW.json');audit=read('independent_audit/SUMMARY.json');mapping=read('NATIVE_MAPPING.json')
 require(audit['status']=='PASS','Audit not passed')
 for p,h in audit['source_hashes'].items():require(sha(OUT/p)==h,'Changed audited source '+p)
 selected=csvrows(OUT/'SELECTED_EVENTS.csv');a={r['review_id']:r for r in primary['events']};b={r['review_id']:r for r in secondary['events']};m={r['review_id']:r for r in mapping['events']};fig={r['review_id']:r for r in read('FIGURE_INDEX.json')}
 ids=[r['review_id']for r in selected];require(set(ids)==set(a)==set(b)==set(m)and len(ids)==68,'Review coverage mismatch')
 require(primary['atlas_pages_inspected']==secondary['atlas_pages_inspected']==list(range(1,18)),'Incomplete atlas coverage')
 require(primary['extracted_order_cutouts_inspected']==secondary['extracted_orders_reviewed']==audit['reconstructed_event_order_cutouts']==94,'Cutout coverage mismatch')
 decisions=[];comparison=[]
 for s in selected:
  k=s['review_id'];x=a[k];y=b[k];q=m[k]
  require(x['dp_id']==y['dp_id']==s['dp_id'],'Review provenance mismatch')
  require(x['covering_orders']==y['covering_orders']==q['covering_orders'],'Review order mismatch')
  require(x['all_covering_orders_mapping_verified']==y['all_covering_orders_mapping_verified']==q['mapping_supported'],'Review mapping mismatch')
  require(x['code']==y['code'],'Unexpected reviewer disagreement requires separate root decision')
  code=x['code'];evidence=x['evidence'];note='Separate reviewers agree; adopted provisionally after root checks.'
  if k=='V2E2-0050':
   code='U';evidence='Both reviewers describe a compact slanted charge cluster in order70. Root retains U: the weak asymmetric excess lies over broader residual structure, so visual morphology alone does not sufficiently exclude a photon/spectral contribution. All-order mapping passes. Possible artifact/spectral blend remains unresolved; this is not a qualified laser candidate.'
   note='Root conservative override A to U after inspecting REVIEW_10 and secondary_enlarged/CENTRAL_03. No mapping, extraction, threshold or original catalog changed.'
  if not q['mapping_supported']:require(code=='M','Unsupported covering order must remain M')
  else:require(code in ('A','O','U'),'Supported event unexpected code')
  orderrows=[r for r in mapping['orders']if r['review_id']==k];wave=orderrows[0]['topocentric_air_angstrom'];nearest=min([5577.338,6300.304,6363.776],key=lambda w:abs(w-wave))
  decisions.append(dict(candidate_id=k,review_id=k,dp_id=s['dp_id'],code=code,evidence=evidence,all_covering_orders_mapping_verified=q['mapping_supported'],primary_code=x['code'],secondary_code=y['code'],reviewers_agree=x['code']==y['code'],primary_review_agrees=code==x['code'],second_review_agrees=code==y['code'],root_adoption_note=note,figure=fig[k]['figure'],figure_row=fig[k]['row'],topocentric_air_angstrom=wave,nearest_OI_air_angstrom=nearest,nearest_OI_offset_angstrom=wave-nearest,final_physical_origin_confirmed=False))
  comparison.append(dict(review_id=k,primary=x['code'],secondary=y['code'],adopted=code,root_note=note))
 csvout('ADOPTED_DISPOSITIONS.csv',decisions)
 stamp=now();counts=dict(collections.Counter(r['code']for r in decisions));require(counts=={'A':36,'O':5,'U':21,'M':6},'Adoption counts unexpected')
 root=dict(created_utc=stamp,status='ROOT_CONSERVATIVE_ADOPTION_COMPLETE',atlas_pages_inspected=[1,2,3,4,5,6,7,8,9,10,11,14,15],central_pages_inspected=['secondary_enlarged/CENTRAL_'+str(i).zfill(2)+'.png'for i in range(1,7)],scope='Root visually inspected every adopted U and M record, all five O records using central enlargements, the0055 possible blend and artifact examples. Two separate agents inspected all17 atlaspages and all94 available cutouts. Root did not claim a third complete independent68-record review.',reviewers_agreed_records=68,root_overrides=[comparison[ids.index('V2E2-0050')]],possible_blends=['V2E2-0050','V2E2-0055'],limits='AI-agent descriptive inspection, not blinded scientific validation or human review; physical origins remain provisional.')
 dump('ROOT_VISUAL_CHECK.json',root);dump('REVIEW_COMPARISON.json',dict(created_utc=stamp,reviewers_agree=68,root_matches_reviewers=67,events=comparison))
 sources=['PRIMARY_VISUAL_REVIEW.json','SECONDARY_VISUAL_REVIEW.json','ROOT_VISUAL_CHECK.json','ADOPTED_DISPOSITIONS.csv','independent_audit/SUMMARY.json','independent_audit/SUPPLEMENTAL_INVENTORY.json','FOLLOWUP_FREEZE.json','products/MANIFEST.json','EVIDENCE_ARCHIVE.json','EVIDENCE_PARTS.json','checkpoints/LIBRARY_INPUTS.json']
 dump('SUMMARY.json',dict(created_utc=stamp,status='ROOT_ADOPTED_CONSERVATIVE_REVIEW',selected_events=68,selected_exposures=16,acquired_products=32,charged_payload_bytes=423684432,payload_attempts=33,payload_retries=1,retry_detail='One HTTP503 before body read; allowed retry succeeded.',independent_numeric_audit='PASS',root_visual_review_complete=True,original_production_unchanged=True,adopted_counts=counts,mapping_supported_events=62,mapping_limited_events=6,unavailable_events=0,extracted_order_cutouts=94,expected_covering_order_records=96,global_region_orientation_checks=3072,five_window_reference_checks=405,reviewers_agreed_records=68,root_overrides=1,raw_pending_before=277,raw_pending_after=209,pending_exposures_after=69,main_unique_exposures_unchanged=300,main_targets_unchanged=20,main_hours_unchanged=70.87465083333333,qualified_laser_candidates=0,all_origins_provisional=True,source_hashes={p:sha(OUT/p)for p in sources},limits='Post-detection review with heterogeneous historical mapping controls. No global false-alarm rate, sensitivity estimate, calibrated null or confirmed physical origins. Residual transfer files excluded and independently inventoried; canonical products and cutouts verify exactly.',runtime=dict(python='3.12.14',numpy='2.3.5',scipy='1.17.0',astropy='8.0.2',matplotlib='3.10.8')))
 print('Adopted',counts,'pending209; all original freeze hashes match')
if __name__=='__main__':main()
