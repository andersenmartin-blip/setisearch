"""Derive exact frozen-order selection and verify remote metadata only; never read payload."""
import csv,io,json,math,urllib.request,urllib.parse,concurrent.futures,time
from common import *
P=verify_plan();require(not(OUT/'FOLLOWUP_FREEZE.json').exists(),'Already prepared; immutable selection must not be replaced')
summary=json.loads((EXT/'production/SUMMARY.json').read_text());require(summary['status']=='COMPLETED'and summary['selected_exposures']==summary['analyzed_exposures']==100 and summary['not_analyzed_exposures']==0,'Production is not complete100')
main=csvrows(EXT/'MAIN100.csv');require(len(main)==100 and [int(r['selection_index'])for r in main]==list(range(1,101)),'MAIN100 order mismatch')
manifest=json.loads((EXT/'acquisition/DOWNLOAD_MANIFEST.json').read_text());require(len(manifest)==100 and len({r['dp_id']for r in manifest})==100,'Acquisition incomplete')
meta={r['dp_id']:r for r in manifest};scope={r['dp_id']:r for r in main}
v1=csvrows(EXT/'production/V1_HITS.csv');v2=csvrows(EXT/'production/V2_HITS.csv')
require(len(v1)==summary['v1_hits']and len(v2)==summary['v2_hits'],'Hit count mismatch')
for label,rows,status in [('V1',v1,'PRELIMINARY_EMISSION_HIT'),('V2',v2,'PRELIMINARY_PROFILE_HIT')]:
 require(len(rows)==len({r['candidate_id']for r in rows}),'Repeated candidate ID '+label)
 for r in rows:
  m=meta[r['dp_id']];s=scope[r['dp_id']]
  require(r['status']==status,'Unexpected accepted status')
  require(r['input_sha256']==m['sha256']and r['raw_progenitor_id']==s['raw_progenitor_id']and int(r['selection_index'])==int(s['selection_index']),'Event provenance mismatch '+r['candidate_id'])
selected=[r for r in main if r['dp_id']in{h['dp_id']for h in v1}][:8];used={r['dp_id']for r in selected}
selected+= [r for r in main if r['dp_id']not in used and r['dp_id']in{h['dp_id']for h in v2}][:8-len(selected)]
require(len(selected)<=8 and len({r['dp_id']for r in selected})==len(selected),'Selection overflow')
products=csvrows(BASE/'v2/next_sample/PRODUCT_METADATA.csv');provenance=csvrows(BASE/'v2/next_sample/RAW_PROVENANCE.csv');checks=[];jobs=[]
for rank,r in enumerate(selected,1):
 dp=r['dp_id'];m=meta[dp]
 require(m['download_status']=='DOWNLOADED'and m['header_status']=='PASS_METADATA_ONLY'and all(m['checks'].values()),'Failed source validation '+dp)
 require(sha(BASE/m['relative_path'])==m['sha256'],'Selected merged input hash mismatch '+dp)
 pp=[p for p in provenance if p['product_id']==dp];require(len(pp)==1 and pp[0]['source_file']==r['raw_progenitor_id'],'Ambiguous raw parent '+dp)
 aa=[p for p in products if p['product_id']==dp and p['extension']=='TAR'];require(len(aa)==1 and aa[0]['archive_id']==r['ancillary_archive_id']and aa[0]['access_url']==r['ancillary_source_url'],'Ambiguous ancillary '+dp)
 require(r['metadata_verification_status']=='PASS_ADP_RAW_ID_AND_CURRENT_METADATA','Original metadata not verified')
 for kind,aid,url,suffix in [('RAW',r['raw_progenitor_id'],r['raw_source_url'],'.fits.Z'),('ANCILLARY',r['ancillary_archive_id'],r['ancillary_source_url'],'.tar')]:
  require(url=='https://dataportal.eso.org/dataPortal/file/'+aid,'Unexpected product URL')
  jobs.append(dict(selected_rank=rank,selection_index=int(r['selection_index']),dp_id=dp,target=r['canonical_target'],kind=kind,raw_id=r['raw_progenitor_id'],archive_id=aid,url=url,filename=aid.replace(':','_')+suffix,source_science_sha256=m['sha256'],source_date_obs=m['primary_header']['DATE-OBS']))
 checks.append(dict(dp_id=dp,selected_rank=rank,selection_index=int(r['selection_index']),target=r['canonical_target'],priority='V1E2'if any(h['dp_id']==dp for h in v1)else'V2_FILL',V1_ids=[h['candidate_id']for h in v1 if h['dp_id']==dp],V2_ids=[h['candidate_id']for h in v2 if h['dp_id']==dp],source_sha256=m['sha256'],raw_provenance_unambiguous=True,ancillary_unambiguous=True,merged_source_sha256_verified=True))
# Only HEAD requests, at most2 per fixed product. No response-body read call exists here.
def head(job):
 result=dict(**job,attempts=[],metadata_status='FAILED')
 for timeout in [20,45]:
  t=time.monotonic()
  try:
   request=urllib.request.Request(job['url'],method='HEAD')
   with urllib.request.urlopen(request,timeout=timeout)as response:
    headers={k:response.headers.get(k)for k in ['Content-Length','Content-Type','Content-Disposition','Last-Modified','Content-Encoding']};size=int(headers['Content-Length']);require(size>0,'No positive Content-Length');require(response.geturl()==job['url'],'Unexpected HEAD redirect');require(response.status==200,'Unexpected HEAD status');require(job['archive_id']in(headers['Content-Disposition']or''),'Content-Disposition archive ID mismatch')
   result.update(metadata_status='VERIFIED',advertised_bytes=size,response_headers=headers,head_final_url=job['url']);result['attempts'].append(dict(outcome='SUCCESS',timeout_seconds=timeout,elapsed_seconds=time.monotonic()-t,returned_payload_bytes=0));break
  except Exception as e:result['attempts'].append(dict(outcome='FAILED',timeout_seconds=timeout,elapsed_seconds=time.monotonic()-t,returned_payload_bytes=0,error=repr(e)))
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:metadata=list(pool.map(head,jobs))
# Keep exposure selection fixed. Accept only complete metadata-verified pairs fitting in selected order.
cap=P['acquisition_bounds']['payload_cap_bytes'];planned=0;accepted=[];omitted=[]
for r in checks:
 pair=[j for j in metadata if j['dp_id']==r['dp_id']]
 if len(pair)!=2 or not all(j['metadata_status']=='VERIFIED'for j in pair):reason='UNVERIFIED_REMOTE_METADATA'
 elif planned+sum(j['advertised_bytes']for j in pair)>cap:reason='PAIR_EXCEEDS_REMAINING_PLANNED_CAP'
 else:accepted+=pair;planned+=sum(j['advertised_bytes']for j in pair);reason=None
 if reason:omitted.append(dict(dp_id=r['dp_id'],reason=reason,replaced=False))
selectedids={r['dp_id']for r in selected};events=[]
for label,rows in [('V1',v1),('V2',v2)]:
 for r in rows:
  if r['dp_id']in selectedids:
   events.append(dict(detector=label,review_id=r['candidate_id'],candidate_id=r['candidate_id'],dp_id=r['dp_id'],target=r['canonical_target'],selection_index=r['selection_index'],fitted_center_bary_air_angstrom=r['wave_peak_angstrom']if label=='V1'else r['fitted_center_angstrom'],source_sha256=r['input_sha256'],source_status=r['status'],raw_review_status='PENDING_PUBLICATION_AND_ACQUISITION'))
csvout('SELECTED_EXPOSURES.csv',selected);csvout('SELECTED_EVENTS.csv',events);dump('SELECTION.json',dict(created_utc=now(),selected_exposures=checks,selected_V1_events=sum(r['detector']=='V1'for r in events),selected_V2_events=sum(r['detector']=='V2'for r in events),all_extension_V1_events=len(v1),all_extension_V2_events=len(v2),V1_outside_selected_exposures=[r for r in v1 if r['dp_id']not in selectedids],selection_replacements=0,planned_payload_bytes=planned,payload_cap_bytes=cap,omitted_pairs=omitted,downloads_started=False))
dump('REMOTE_PRODUCT_METADATA.json',metadata);dump('JOBS.json',accepted)
sourcepaths=[OUT/f for f in ['PLAN.json','common.py','prepare_selection.py','acquire.py','extract_native.py','registration.py','local_registration.py','SELECTION.json','SELECTED_EXPOSURES.csv','SELECTED_EVENTS.csv','REMOTE_PRODUCT_METADATA.json','JOBS.json']]+[EXT/f for f in ['MAIN100.csv','FREEZE.json','PROTOCOL.json','acquisition/DOWNLOAD_MANIFEST.json','production/SUMMARY.json','production/V1_HITS.csv','production/V2_HITS.csv','production/V2_DISPOSITIONS.csv']]+[BASE/'v2/next_sample/PRODUCT_METADATA.csv',BASE/'v2/next_sample/RAW_PROVENANCE.csv']
dump('FOLLOWUP_FREEZE.json',dict(created_utc=now(),status='READY_FOR_ROOT_PUBLICATION_VERIFICATION',source_hashes={str(f.relative_to(BASE)):sha(f)for f in sourcepaths},selected_exposures=len(selected),selected_events=len(events),planned_products=len(accepted),planned_payload_bytes=planned,download_gate='Root must publish and independently verify this exact plan/code/selection before invoking acquire with commit and freeze hash.'))
print(json.dumps(read('SELECTION.json'),indent=2));print('FOLLOWUP_FREEZE_SHA256',sha(OUT/'FOLLOWUP_FREEZE.json'))
