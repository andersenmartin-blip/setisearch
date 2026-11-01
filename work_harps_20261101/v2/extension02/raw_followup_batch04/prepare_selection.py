"""Freeze all remaining 37 pending exposures and verify HEAD metadata, never payload."""
import concurrent.futures
import time
import urllib.request
import urllib.error
from common import *
from transfer_guards import no_redirect_opener,close_http_error


def head(job):
    """At most two HEAD attempts; denied products are terminal, no redirects."""
    result={**job,'attempts':[],'metadata_status':'FAILED'}
    for timeout in [20,45]:
        began=time.monotonic()
        try:
            request=urllib.request.Request(job['url'],method='HEAD')
            with no_redirect_opener().open(request,timeout=timeout)as response:
                headers={k:response.headers.get(k)for k in ['Content-Length','Content-Type','Content-Disposition','Last-Modified','Content-Encoding']}
                size=int(headers['Content-Length'])
                require(size>0,'No positive Content-Length')
                require(response.geturl()==job['url']and response.status==200,'Unexpected HEAD redirect/status')
                require(job['archive_id']in(headers['Content-Disposition']or''),'Content-Disposition archive ID mismatch')
            result.update(metadata_status='VERIFIED',advertised_bytes=size,response_headers=headers,head_final_url=job['url'])
            result['attempts'].append(dict(outcome='SUCCESS',timeout_seconds=timeout,elapsed_seconds=time.monotonic()-began,returned_payload_bytes=0))
            break
        except Exception as error:
            close_http_error(error)
            result['attempts'].append(dict(outcome='FAILED',timeout_seconds=timeout,elapsed_seconds=time.monotonic()-began,returned_payload_bytes=0,error=repr(error)))
            if isinstance(error,urllib.error.HTTPError)and error.code in(401,403):break
    return result


def selection_inputs(plan):
    # Copies are immutable evidence; live status will advance after this batch.
    for item in plan['queue_snapshot']['sources']:
        require(sha(OUT/item['snapshot_path'])==item['sha256'],'Changed queue snapshot')
        require(sha(BASE.parent/item['source_path'])==item['sha256'],'Live queue changed before preparation')
    summary=json.loads((EXT/'production/SUMMARY.json').read_text())
    require(summary['status']=='COMPLETED'and summary['selected_exposures']==summary['analyzed_exposures']==100 and summary['not_analyzed_exposures']==0,'Production is not complete100')
    main=csvrows(EXT/'MAIN100.csv')
    require(len(main)==100 and[int(r['selection_index'])for r in main]==list(range(1,101)),'MAIN100 order mismatch')
    manifest=json.loads((EXT/'acquisition/DOWNLOAD_MANIFEST.json').read_text())
    require(len(manifest)==100 and len({r['dp_id']for r in manifest})==100,'Acquisition incomplete')
    meta={r['dp_id']:r for r in manifest};scope={r['dp_id']:r for r in main}
    v1=csvrows(EXT/'production/V1_HITS.csv');v2=csvrows(EXT/'production/V2_HITS.csv')
    require(len(v1)==summary['v1_hits']and len(v2)==summary['v2_hits']==336,'Hit count mismatch')
    for label,rows,status in [('V1',v1,'PRELIMINARY_EMISSION_HIT'),('V2',v2,'PRELIMINARY_PROFILE_HIT')]:
        require(len(rows)==len({r['candidate_id']for r in rows}),'Repeated candidate ID '+label)
        for row in rows:
            m=meta[row['dp_id']];s=scope[row['dp_id']]
            require(row['status']==status,'Unexpected accepted status')
            require(row['input_sha256']==m['sha256']and row['raw_progenitor_id']==s['raw_progenitor_id']and int(row['selection_index'])==int(s['selection_index']),'Event provenance mismatch '+row['candidate_id'])
    dispositions=csvrows(OUT/'inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv')
    require(len(dispositions)==336 and {r['candidate_id']for r in dispositions}=={r['candidate_id']for r in v2},'Current disposition coverage mismatch')
    require({code:sum(r['current_code']==code for r in dispositions) for code in plan['selection_rule']['expected_current_V2_codes']}==plan['selection_rule']['expected_current_V2_codes'],'Predecessor disposition counts changed')
    require(len(csvrows(OUT/'inputs/CURRENT_SELECTED_EVENT_DISPOSITIONS.csv'))==plan['selection_rule']['expected_previously_selected_records'],'Predecessor selected review count changed')
    pending=[r for r in dispositions if r['current_code']=='N']
    pending_ids={r['candidate_id']for r in pending}
    state=read('inputs/CONTINUATION_STATE.json');queue=state['pending_raw_queue']
    require(queue['source_sha256']==sha(OUT/'inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv'),'Continuation queue disposition hash mismatch')
    require(len(pending)==queue['pending_events']==plan['selection_rule']['expected_pending_events_before'] and {r['candidate_id']for r in queue['events']}==pending_ids,'Pending event queue mismatch')
    v2byid={r['candidate_id']:r for r in v2}
    for row in pending:
        hit=v2byid[row['candidate_id']]
        require(row['dp_id']==hit['dp_id']and row['source_input_sha256']==hit['input_sha256'],'Pending record provenance mismatch')
    for row in queue['events']:
        hit=v2byid[row['candidate_id']]
        require(row['dp_id']==hit['dp_id']and row['source_input_sha256']==hit['input_sha256'],'Continuation event provenance mismatch')
    pending_exposures={r['dp_id']for r in pending}
    all_pending=[r for r in main if r['dp_id']in pending_exposures]
    require(len(all_pending)==queue['pending_exposures']==plan['selection_rule']['expected_pending_exposures_before'],'Pending exposure count mismatch')
    require([r['dp_id']for r in all_pending]==[r['dp_id']for r in queue['exposure_queue']],'Pending exposure order mismatch')
    for queued,source in zip(queue['exposure_queue'],all_pending):
        expected=[r['candidate_id']for r in pending if r['dp_id']==source['dp_id']]
        require(queued['pending_ids']==expected and int(queued['selection_index'])==int(source['selection_index'])and queued['raw_progenitor_id']==source['raw_progenitor_id']and queued['ancillary_archive_id']==source['ancillary_archive_id'],'Continuation exposure identity mismatch')
    selected=all_pending[:plan['selection_rule']['max_unique_exposures']]
    require([int(r['selection_index'])for r in selected]==plan['selection_rule']['expected_selection_indices'],'Unexpected selected MAIN100 indices')
    ids={r['dp_id']for r in selected}
    events=[r for r in v2 if r['dp_id']in ids]
    require(len(selected)==plan['selection_rule']['max_unique_exposures']==37 and len(events)==plan['selection_rule']['expected_V2_events']==94,'Batch size mismatch')
    require(all(r['candidate_id']in pending_ids for r in events),'Already reviewed event in selected exposure')
    require(not any(r['dp_id']in ids for r in v1),'Unexpected V1 event in selected pending exposure')
    return selected,events,meta,v1,v2


def main():
    plan=verify_plan()
    require(not(OUT/'FOLLOWUP_FREEZE.json').exists(),'Already prepared; immutable selection must not be replaced')
    selected,events,meta,v1,v2=selection_inputs(plan)
    products=csvrows(BASE/'v2/next_sample/PRODUCT_METADATA.csv')
    provenance=csvrows(BASE/'v2/next_sample/RAW_PROVENANCE.csv')
    checks=[];jobs=[]
    for rank,row in enumerate(selected,1):
        dp=row['dp_id'];m=meta[dp]
        require(m['download_status']=='DOWNLOADED'and m['header_status']=='PASS_METADATA_ONLY'and all(m['checks'].values()),'Failed source validation '+dp)
        require(sha(BASE/m['relative_path'])==m['sha256'],'Selected merged input hash mismatch '+dp)
        parents=[p for p in provenance if p['product_id']==dp]
        require(len(parents)==1 and parents[0]['source_file']==row['raw_progenitor_id'],'Ambiguous raw parent '+dp)
        ancillary=[p for p in products if p['product_id']==dp and p['extension']=='TAR']
        require(len(ancillary)==1 and ancillary[0]['archive_id']==row['ancillary_archive_id']and ancillary[0]['access_url']==row['ancillary_source_url'],'Ambiguous ancillary '+dp)
        require(row['metadata_verification_status']=='PASS_ADP_RAW_ID_AND_CURRENT_METADATA','Original metadata not verified')
        for kind,archive_id,url,suffix in [('RAW',row['raw_progenitor_id'],row['raw_source_url'],'.fits.Z'),('ANCILLARY',row['ancillary_archive_id'],row['ancillary_source_url'],'.tar')]:
            require(url=='https://dataportal.eso.org/dataPortal/file/'+archive_id,'Unexpected product URL')
            jobs.append(dict(selected_rank=rank,selection_index=int(row['selection_index']),dp_id=dp,target=row['canonical_target'],kind=kind,raw_id=row['raw_progenitor_id'],archive_id=archive_id,url=url,filename=archive_id.replace(':','_')+suffix,source_science_sha256=m['sha256'],source_date_obs=m['primary_header']['DATE-OBS']))
        checks.append(dict(dp_id=dp,selected_rank=rank,selection_index=int(row['selection_index']),target=row['canonical_target'],priority='PENDING_N_MAIN100_ORDER',V1_ids=[],V2_ids=[r['candidate_id']for r in events if r['dp_id']==dp],source_sha256=m['sha256'],raw_provenance_unambiguous=True,ancillary_unambiguous=True,merged_source_sha256_verified=True))
    # No body reads; each immutable original URL receives HEAD only.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:metadata=list(pool.map(head,jobs))
    cap=plan['acquisition_bounds']['payload_cap_bytes'];planned=0;accepted=[];omitted=[]
    for row in checks:
        pair=[j for j in metadata if j['dp_id']==row['dp_id']]
        if len(pair)!=2 or not all(j['metadata_status']=='VERIFIED'for j in pair):reason='UNVERIFIED_REMOTE_METADATA'
        elif planned+sum(j['advertised_bytes']for j in pair)>cap:reason='PAIR_EXCEEDS_REMAINING_PLANNED_CAP'
        else:accepted+=pair;planned+=sum(j['advertised_bytes']for j in pair);reason=None
        if reason:omitted.append(dict(dp_id=row['dp_id'],reason=reason,replaced=False))
    selected_events=[dict(detector='V2',review_id=r['candidate_id'],candidate_id=r['candidate_id'],dp_id=r['dp_id'],target=r['canonical_target'],selection_index=r['selection_index'],fitted_center_bary_air_angstrom=r['fitted_center_angstrom'],source_sha256=r['input_sha256'],source_status=r['status'],raw_review_status='PENDING_PUBLICATION_AND_ACQUISITION')for r in events]
    csvout('SELECTED_EXPOSURES.csv',selected);csvout('SELECTED_EVENTS.csv',selected_events)
    dump('SELECTION.json',dict(created_utc=now(),selected_exposures=checks,selected_V1_events=0,selected_V2_events=len(events),all_extension_V1_events=len(v1),all_extension_V2_events=len(v2),V1_outside_selected_exposures=v1,selection_replacements=0,planned_payload_bytes=planned,payload_cap_bytes=cap,omitted_pairs=omitted,downloads_started=False,pending_before=plan['selection_rule']['expected_pending_events_before'],pending_outside_selected=plan['selection_rule']['expected_pending_events_before']-len(events)))
    dump('REMOTE_PRODUCT_METADATA.json',metadata);dump('JOBS.json',accepted)
    local_names=['PLAN.json','common.py','prepare_selection.py','acquire.py','extract_native.py','mapping_quality.py','plot_review.py','registration.py','local_registration.py','transfer_guards.py','test_transfer_guards.py','inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv','inputs/CONTINUATION_STATE.json','inputs/CURRENT_SELECTED_EVENT_DISPOSITIONS.csv','inputs/CURRENT_SUMMARY.json','inputs/CURRENT_V2_DISPOSITIONS.csv','CACHE_CHECK.json','VISUAL_REVIEW_PLAN.json','SELECTION.json','SELECTED_EXPOSURES.csv','SELECTED_EVENTS.csv','REMOTE_PRODUCT_METADATA.json','JOBS.json']
    sourcepaths=[OUT/f for f in local_names]+[EXT/f for f in ['MAIN100.csv','FREEZE.json','PROTOCOL.json','acquisition/DOWNLOAD_MANIFEST.json','production/SUMMARY.json','production/V1_HITS.csv','production/V2_HITS.csv','production/V2_DISPOSITIONS.csv']]+[BASE/'v2/next_sample/PRODUCT_METADATA.csv',BASE/'v2/next_sample/RAW_PROVENANCE.csv']
    dump('FOLLOWUP_FREEZE.json',dict(created_utc=now(),status='READY_FOR_ROOT_PUBLICATION_VERIFICATION',source_hashes={str(f.relative_to(BASE)):sha(f)for f in sourcepaths},selected_exposures=len(selected),selected_events=len(events),planned_products=len(accepted),planned_payload_bytes=planned,download_gate='Root must publish and independently verify this exact plan/code/selection before invoking acquire with commit and freeze hash.'))
    print(json.dumps(dict(selected_exposures=len(selected),selected_V2_events=len(events),verified_products=len(accepted),planned_payload_bytes=planned,omitted_pairs=omitted),indent=2))
    print('FOLLOWUP_FREEZE_SHA256',sha(OUT/'FOLLOWUP_FREEZE.json'))


if __name__=='__main__':main()
