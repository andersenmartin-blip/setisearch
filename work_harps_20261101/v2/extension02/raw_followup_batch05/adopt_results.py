"""Root-authorized batch05 bookkeeping; no science-array or mapping changes."""
from collections import Counter
from common import *

def main():
 verify_plan();verify_freeze()
 primary=read('PRIMARY_VISUAL_REVIEW.json');secondary=read('SECONDARY_VISUAL_REVIEW.json');mapping=read('NATIVE_MAPPING.json');audit=read('independent_audit/SUMMARY.json');root=read('ROOT_ADJUDICATION.json')
 require(audit['status']=='PASS' and root['root_visual_review_complete'],'Audit/root adoption required')
 for name,h in audit['source_hashes'].items():require(sha(OUT/name)==h,'Changed audit input '+name)
 for name,h in primary['source_sha256'].items():require(sha(OUT/name)==h,'Changed primary input '+name)
 for r in secondary['inspected_evidence']:require(sha(OUT/r['path'])==r['sha256'],'Changed secondary input '+r['path'])
 for name,h in root['source_sha256'].items():require(sha(OUT/name)==h,'Changed root input '+name)
 selected=csvrows(OUT/'SELECTED_EVENTS.csv');a={r['review_id']:r for r in primary['events']};b={r['review_id']:r for r in secondary['records']};m={r['review_id']:r for r in mapping['events']};f={r['review_id']:r for r in read('FIGURE_INDEX.json')}
 ids=[r['review_id']for r in selected];require(set(ids)==set(a)==set(b)==set(m) and len(ids)==len(a)==len(b)==2,'Record coverage')
 require(primary['extracted_order_cutouts_inspected']==secondary['scope']['covering_order_panels']==mapping['extracted_orders']==2,'All covering orders must be reviewed')
 decisions=[];comparisons=[]
 for s in selected:
  rid=s['review_id'];x=a[rid];y=b[rid];q=m[rid];order=next(r for r in mapping['orders']if r['review_id']==rid)
  require(x['dp_id']==s['dp_id'] and x['candidate_id']==y['candidate_id']==rid,'Review identity')
  require(x['covering_orders']==y['covering_orders']==q['covering_orders'] and x['orders_seen']==y['viewed_orders']==q['covering_orders'],'Order coverage')
  require(x['code']==y['code']=='A' and q['mapping_supported'] and x['all_covering_orders_mapping_verified'] and y['all_covering_orders_mapping_verified'],'Root-adopted result contract')
  wave=order['topocentric_air_angstrom'];nearest=min([5577.338,6300.304,6363.776],key=lambda w:abs(w-wave));evidence=x['evidence']+' Provisional charge morphology only; weaker photon/background components or blends are not excluded.'
  decisions.append(dict(candidate_id=rid,review_id=rid,dp_id=s['dp_id'],code='A',evidence=evidence,all_covering_orders_mapping_verified=True,primary_code='A',secondary_code='A',reviewers_agree=True,primary_review_agrees=True,second_review_agrees=True,root_adoption_note='Separate visual reviews agree; root inspected all2 atlas/central order panels and adopts provisional A without overrides.',figure=f[rid]['figure'],figure_row=f[rid]['row'],topocentric_air_angstrom=wave,nearest_OI_air_angstrom=nearest,nearest_OI_offset_angstrom=wave-nearest,final_physical_origin_confirmed=False))
  comparisons.append(dict(review_id=rid,primary='A',secondary='A',adopted='A',root_override=False))
 csvout('ADOPTED_DISPOSITIONS.csv',decisions);stamp=now()
 dump('ROOT_VISUAL_CHECK.json',{**root,'created_utc':stamp,'status':'ROOT_CONSERVATIVE_ADOPTION_COMPLETE'})
 dump('REVIEW_COMPARISON.json',dict(created_utc=stamp,reviewers_agree=2,root_matches_both=2,events=comparisons))
 manifest=read('products/MANIFEST.json');products=manifest['products'];sources=['PRIMARY_VISUAL_REVIEW.json','SECONDARY_VISUAL_REVIEW.json','ROOT_ADJUDICATION.json','ROOT_VISUAL_CHECK.json','ADOPTED_DISPOSITIONS.csv','independent_audit/SUMMARY.json','independent_audit/ACQUISITION_INVENTORY.json','FOLLOWUP_FREEZE.json','products/MANIFEST.json','EVIDENCE_ARCHIVE.json','EVIDENCE_PARTS.json','checkpoints/LIBRARY_INPUTS.json']
 dump('SUMMARY.json',dict(created_utc=stamp,status='ROOT_ADOPTED_CONSERVATIVE_REVIEW',selected_events=2,selected_exposures=1,acquired_products=2,planned_products=2,charged_payload_bytes=manifest['charged_payload_bytes'],payload_attempts=sum(len(r['attempts'])for r in products),payload_retries=0,independent_numeric_audit='PASS',root_visual_review_complete=True,original_production_unchanged=True,adopted_counts={'A':2,'O':0,'U':0,'M':0,'N':0},mapping_supported_events=2,mapping_limited_events=0,unavailable_events=0,extracted_order_cutouts=2,expected_covering_order_records=2,reviewers_agreed_records=2,root_adjudications=0,raw_pending_before=2,raw_pending_after=0,main_unique_exposures_unchanged=300,main_targets_unchanged=20,main_hours_unchanged=70.87465083333333,qualified_laser_candidates=0,all_origins_provisional=True,source_hashes={name:sha(OUT/name)for name in sources},limits='Post-detection descriptive AI review with heterogeneous historical controls; no calibrated false-alarm rate,sensitivity,null or confirmed origin.',runtime=dict(python='3.12.14',numpy='2.3.5',scipy='1.17.0',astropy='8.0.2',matplotlib='3.10.8')))
 print('Adopted2A; pending0; unchanged science methods.')
if __name__=='__main__':main()
