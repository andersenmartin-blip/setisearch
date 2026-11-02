"""Adopt independent reviews using an explicit root visual/adjudication record.

This is post-review bookkeeping; it never reads raw arrays or changes mapping.
"""
import collections
from common import *

def main():
 plan=verify_plan();verify_freeze();expected_events=plan['selection_rule']['expected_V2_events'];expected_exposures=plan['selection_rule']['max_unique_exposures']
 p=read('PRIMARY_VISUAL_REVIEW.json');s=read('SECONDARY_VISUAL_REVIEW.json');audit=read('independent_audit/SUMMARY.json');mapping=read('NATIVE_MAPPING.json');root=read('ROOT_ADJUDICATION.json')
 require(audit['status']=='PASS','Audit not passed');require(root['root_visual_review_complete']is True,'Root review incomplete')
 for f,h in audit['source_hashes'].items():require(sha(OUT/f)==h,'Changed audited output '+f)
 selected=csvrows(OUT/'SELECTED_EVENTS.csv');primary=p['events'];secondary=s['records'];a={r['review_id']:r for r in primary};b={r['review_id']:r for r in secondary};m={r['review_id']:r for r in mapping['events']};fig={r['review_id']:r for r in read('FIGURE_INDEX.json')}
 require(len(primary)==len(a)==len(secondary)==len(b)==expected_events,'Duplicate or missing review record')
 ids=[r['review_id']for r in selected];require(len(ids)==expected_events and set(ids)==set(a)==set(b)==set(m),'Review coverage mismatch')
 pages=sorted({r['page']for r in fig.values()});require(p['atlas_pages_inspected']==s['atlas_pages_inspected']==pages,'Incomplete atlas review')
 require(p['extracted_order_cutouts_inspected']==s['extracted_orders_reviewed_count']==len(s['extracted_orders_reviewed'])==mapping['extracted_orders'],'Incomplete available-cutout review')
 actual_cutouts={(r['review_id'],r['order']):r for r in mapping['orders'] if r.get('cutout')}
 reviewed_cutouts={(r['review_id'],r['order']):r for r in s['extracted_orders_reviewed']}
 require(set(actual_cutouts)==set(reviewed_cutouts),'Secondary cutout identities differ from extracted evidence')
 for key,r in reviewed_cutouts.items():
  require(r['cutout']==actual_cutouts[key]['cutout'] and sha(OUT/r['cutout'])==r['cutout_sha256']==actual_cutouts[key]['cutout_sha256'],'Secondary cutout provenance mismatch')
 overrides={r['review_id']:r for r in root['adjudications']};require(set(overrides)<=set(ids),'Unselected override')
 decisions=[];comparison=[]
 for event in selected:
  k=event['review_id'];x=a[k];y=b[k];q=m[k]
  require(x['dp_id']==y['dp_id']==event['dp_id'],'Review exposure mismatch')
  require(x['covering_orders']==y['covering_orders']==q['covering_orders'],'Review covering-order mismatch')
  require(x['all_covering_orders_mapping_verified']==y['all_covering_orders_mapping_verified']==q['mapping_supported'],'Review mapping mismatch')
  if k in overrides:code=overrides[k]['code'];evidence=overrides[k]['evidence'];note=overrides[k]['reason']
  else:
   require(x['code']==y['code'],'Disagreement requires root adjudication '+k)
   code=x['code'];evidence=x['evidence'];note='Separate reviews agree; provisionally adopted after root evidence checks.'
  if q['status']=='NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE':require(code=='N','Unavailable pair requires N')
  elif not q['mapping_supported']:require(code=='M','Any unsupported order requires M')
  else:require(code in ('A','O','U'),'Supported event invalid code')
  orderrows=[r for r in mapping['orders']if r['review_id']==k];wave=orderrows[0]['topocentric_air_angstrom']if orderrows else None;nearest=min([5577.338,6300.304,6363.776],key=lambda w:abs(w-wave))if wave is not None else None
  decisions.append(dict(candidate_id=k,review_id=k,dp_id=event['dp_id'],code=code,evidence=evidence,all_covering_orders_mapping_verified=q['mapping_supported'],primary_code=x['code'],secondary_code=y['code'],reviewers_agree=x['code']==y['code'],primary_review_agrees=code==x['code'],second_review_agrees=code==y['code'],root_adoption_note=note,figure=fig[k]['figure'],figure_row=fig[k]['row'],topocentric_air_angstrom=wave,nearest_OI_air_angstrom=nearest,nearest_OI_offset_angstrom=wave-nearest if wave is not None else None,final_physical_origin_confirmed=False))
  comparison.append(dict(review_id=k,primary=x['code'],secondary=y['code'],adopted=code,root_note=note))
 csvout('ADOPTED_DISPOSITIONS.csv',decisions)
 stamp=now();counts={k:collections.Counter(r['code']for r in decisions)[k]for k in'AOUMN'};manifest=read('products/MANIFEST.json');products=manifest['products'];pending_before=plan['selection_rule']['expected_pending_events_before'];after=pending_before-len(selected)+counts['N']
 dump('ROOT_VISUAL_CHECK.json',{**root,'created_utc':stamp,'status':'ROOT_CONSERVATIVE_ADOPTION_COMPLETE'})
 dump('REVIEW_COMPARISON.json',dict(created_utc=stamp,reviewers_agree=sum(r['primary']==r['secondary']for r in comparison),root_matches_both=sum(r['adopted']==r['primary']==r['secondary']for r in comparison),events=comparison))
 sources=['PRIMARY_VISUAL_REVIEW.json','SECONDARY_VISUAL_REVIEW.json','ROOT_ADJUDICATION.json','ROOT_VISUAL_CHECK.json','ADOPTED_DISPOSITIONS.csv','independent_audit/SUMMARY.json','independent_audit/SUPPLEMENTAL_INVENTORY.json','FOLLOWUP_FREEZE.json','products/MANIFEST.json','EVIDENCE_ARCHIVE.json','EVIDENCE_PARTS.json','checkpoints/LIBRARY_INPUTS.json']
 dump('SUMMARY.json',dict(created_utc=stamp,status='ROOT_ADOPTED_CONSERVATIVE_REVIEW',selected_events=expected_events,selected_exposures=expected_exposures,acquired_products=sum(r['status']=='DOWNLOADED'for r in products),planned_products=len(products),charged_payload_bytes=manifest['charged_payload_bytes'],payload_attempts=sum(len(r['attempts'])for r in products),payload_retries=sum(max(0,len(r['attempts'])-1)for r in products),independent_numeric_audit='PASS',root_visual_review_complete=True,original_production_unchanged=True,adopted_counts=counts,mapping_supported_events=sum(r['mapping_supported']for r in m.values()),mapping_limited_events=counts['M'],unavailable_events=counts['N'],extracted_order_cutouts=mapping['extracted_orders'],expected_covering_order_records=len(mapping['orders']),reviewers_agreed_records=sum(r['primary']==r['secondary']for r in comparison),root_adjudications=len(overrides),raw_pending_before=pending_before,raw_pending_after=after,main_unique_exposures_unchanged=300,main_targets_unchanged=20,main_hours_unchanged=70.87465083333333,qualified_laser_candidates=0,all_origins_provisional=True,source_hashes={f:sha(OUT/f)for f in sources},limits='Post-detection descriptive AI review, heterogeneous historical controls. No calibrated false-alarm rate, sensitivity, null or confirmed origin.',runtime=dict(python='3.12.14',numpy='2.3.5',scipy='1.17.0',astropy='8.0.2',matplotlib='3.10.8')))
 print('Adopted',counts,'pending',after)
if __name__=='__main__':main()
