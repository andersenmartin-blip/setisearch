"""Independent final continuity audit; reads current science, never rewrites it."""
from pathlib import Path
import collections, csv, datetime, hashlib, json, re, subprocess, urllib.parse
OUT = Path(__file__).resolve().parents[1]
EXT = OUT.parent
BASE = EXT.parents[1]
V2 = BASE/'v2'
REPO = BASE.parent
CURRENT = EXT/'raw_followup'
INPUT = OUT/'inputs'
AUDIT = Path(__file__).resolve().parent
CODES = 'AOUMN'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda:handle.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def read(path): return json.loads(Path(path).read_text())
def rows(path):
    with Path(path).open(newline='') as handle: return list(csv.DictReader(handle))
def counts(records,key):
    c=collections.Counter(r[key] for r in records)
    return {k:c[k] for k in CODES}
def main():
    checks=[]; failures=[]
    def check(name,ok,detail=None):
        result=dict(name=name,passed=bool(ok))
        if detail is not None: result['detail']=detail
        checks.append(result)
        if not ok: failures.append(name)
    current=rows(CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
    before=rows(INPUT/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
    master=rows(V2/'CURRENT_V2_DISPOSITIONS.csv')
    prior_master=rows(INPUT/'CURRENT_V2_DISPOSITIONS.csv')
    selected_master=rows(CURRENT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
    prior_selected=rows(INPUT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
    selected=rows(OUT/'SELECTED_EVENTS.csv');exposures=rows(OUT/'SELECTED_EXPOSURES.csv')
    decisions=rows(OUT/'ADOPTED_DISPOSITIONS.csv');summary=read(OUT/'SUMMARY.json')
    state=read(OUT/'CONTINUATION_STATE.json');old_state=read(INPUT/'CONTINUATION_STATE.json')
    current_summary=read(CURRENT/'CURRENT_SUMMARY.json');status=read(V2/'CURRENT_STATUS.json')
    old={r['candidate_id']:r for r in before};new={r['candidate_id']:r for r in current}
    by_decision={r['candidate_id']:r for r in decisions};selected_ids={r['review_id']for r in selected}
    check('unique_new_cohort_336',len(new)==len(current)==len(old)==len(before)==336)
    check('unique_combined_master_669',len(master)==len({r['review_id']for r in master})==669)
    check('selected_scope_115_records_32_exposures',len(selected)==len(selected_ids)==len(decisions)==len(by_decision)==115 and len(exposures)==32 and set(by_decision)==selected_ids)
    check('new_counts',counts(current,'current_code')=={'A':142,'O':20,'U':61,'M':19,'N':94},counts(current,'current_code'))
    check('all_counts',counts(master,'current_code')=={'A':351,'O':45,'U':156,'M':23,'N':94},counts(master,'current_code'))
    check('adopted_counts',counts(decisions,'code')=={'A':62,'O':7,'U':34,'M':12,'N':0}==summary['adopted_counts'],counts(decisions,'code'))
    changed=[k for k in old if old[k]['current_code']!=new[k]['current_code']]
    check('exactly_selected_115_N_rows_changed',set(changed)==selected_ids and all(old[k]['current_code']=='N'for k in changed))
    check('all_127_prior_reviewed_V2_rows_original_fields_preserved',sum(r['current_code']!='N'for r in before)==127 and all(all(new[k][field]==value for field,value in r.items())for k,r in old.items()if r['current_code']!='N'))
    check('all_94_remaining_pending_original_fields_preserved',all(all(new[k][field]==value for field,value in r.items())for k,r in old.items()if k not in selected_ids))
    mutable={'current_code','current_disposition','current_evidence','current_evidence_table','final_physical_origin_confirmed'}
    check('all_selected_historical_fields_preserved',all(all(new[k][field]==value for field,value in old[k].items()if field not in mutable)for k in selected_ids))
    older=[r for r in master if r['cohort']=='V2_first100'];older_before=[r for r in prior_master if r['cohort']=='V2_first100']
    check('older_333_master_rows_byte_values_preserved',older==older_before and len(older)==333)
    old_master_by={r['review_id']:r for r in prior_master};master_by={r['review_id']:r for r in master}
    check('all_unselected_master_rows_preserved',all(master_by[k]==r for k,r in old_master_by.items()if k not in selected_ids))
    check('all_133_prior_selected_fields_preserved',len(prior_selected)==133 and all(all(selected_master[i][k]==v for k,v in r.items())for i,r in enumerate(prior_selected)))
    check('selected_master_exact248_unique',len(selected_master)==len({r['review_id']for r in selected_master})==248 and {r['review_id']for r in selected_master[133:]}==selected_ids)
    figure_paths=[r['figure']for r in selected_master[133:]]
    check('all_115_new_figure_links_point_to_batch03',all(p.startswith('../raw_followup_batch03/')and(CURRENT/p).is_file()for p in figure_paths))
    evidence_tables=[r['current_evidence_table']for r in current if r['candidate_id']in selected_ids]
    check('new_evidence_tables_resolve',all(p=='../raw_followup_batch03/ADOPTED_DISPOSITIONS.csv'and(CURRENT/p).is_file()for p in evidence_tables))
    check('current_summary_equals_status',current_summary==status)
    check('current_summaries_counts_and_latest_batch',status['current_new_V2_counts']==counts(current,'current_code') and status['current_all_V2_counts']==counts(master,'current_code') and status['V2_raw_reviewed']==575 and status['V2_raw_unreviewed']==94 and status['latest_raw_batch']['selected_events']==115 and status['latest_raw_batch']['selected_exposures']==32)
    pending=[r for r in current if r['current_code']=='N'];queue=[]
    for r in rows(EXT/'MAIN100.csv'):
        ids=[p['candidate_id']for p in pending if p['dp_id']==r['dp_id']]
        if ids:queue.append(dict(dp_id=r['dp_id'],target=r['canonical_target'],selection_index=int(r['selection_index']),pending_ids=ids,raw_progenitor_id=r['raw_progenitor_id'],ancillary_archive_id=r['ancillary_archive_id'],raw_source_url=r['raw_source_url'],ancillary_source_url=r['ancillary_source_url']))
    q=state['pending_raw_queue']
    check('exact_pending_event_queue',q['events']==[{k:r[k]for k in['candidate_id','dp_id','target','source_input_sha256']}for r in pending])
    check('exact_MAIN100_pending_exposure_queue',q['exposure_queue']==queue and len(queue)==37 and len(pending)==94)
    check('next_queue_head_0243_HD124553',q['first_event']=='V2E2-0243'and q['first_exposure']==queue[0]and queue[0]['target']=='HD124553'and q['pending_events']==94 and q['pending_exposures']==37)
    check('queue_source_hash',q['source_sha256']==sha(CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv'))
    check('next_directory_batch04',state['next_action']['directory_to_create'].endswith('/raw_followup_batch04')and state['next_action']['queue_head']=='V2E2-0243')
    check('state_unresolved_and_limited_IDs_exact',state['science']['new_V2_unresolved_ids']==[r['candidate_id']for r in current if r['current_code']=='U']and state['science']['new_V2_mapping_limited_ids']==[r['candidate_id']for r in current if r['current_code']=='M'])
    check('survey_scope_and_completed_epoch_state_preserved',all(state['science'][k]==old_state['science'][k]for k in['main_exposures','main_targets','main_exposure_seconds','main_exposure_hours','V1_exposures','V1_hits','V2_exposures','V2_events','new_V2_events'])and state['completed_epoch_comparison']==old_state['completed_epoch_comparison']and state['independent_epoch_audit']==old_state['independent_epoch_audit'])
    frozen=read(OUT/'FOLLOWUP_FREEZE.json')
    check('all_frozen_source_hashes',all(sha(BASE/p)==h for p,h in frozen['source_hashes'].items()),len(frozen['source_hashes']))
    check('all_current_state_source_hashes',all(sha(REPO/p)==h for p,h in state['source_hashes'].items()),len(state['source_hashes']))
    check('all_current_summary_source_hashes',all(sha(V2/p)==h for p,h in current_summary['source_hashes'].items()),len(current_summary['source_hashes']))
    check('all_adoption_summary_source_hashes',all(sha(OUT/p)==h for p,h in summary['source_hashes'].items()),len(summary['source_hashes']))
    primary=read(OUT/'PRIMARY_VISUAL_REVIEW.json');secondary=read(OUT/'SECONDARY_VISUAL_REVIEW.json')
    pa={r['review_id']:r for r in primary['events']};sa={r['review_id']:r for r in secondary['events']}
    disagreements=[k for k in selected_ids if pa[k]['code']!=sa[k]['code']]
    check('exact_one_review_disagreement_0235',set(disagreements)=={'V2E2-0235'} and pa['V2E2-0235']['code']=='U'and sa['V2E2-0235']['code']=='A'and by_decision['V2E2-0235']['code']=='U')
    check('other_114_adoptions_match_both_reviews',all(by_decision[k]['code']==pa[k]['code']==sa[k]['code']for k in selected_ids if k!='V2E2-0235'))
    review_hash_count=0;review_hash_pass=True
    for r in [primary,secondary]:
        for name in ['source_sha256','source_hashes']:
            for p,h in r.get(name,{}).items():review_hash_count+=1;review_hash_pass=review_hash_pass and sha(OUT/p)==h
    root_adjudication=read(OUT/'ROOT_ADJUDICATION.json')
    for name in ['figure_sha256','review_sha256']:
        for p,h in root_adjudication.get(name,{}).items():review_hash_count+=1;review_hash_pass=review_hash_pass and sha(OUT/p)==h
    check('review_and_root_evidence_hashes',review_hash_pass,review_hash_count)
    mapping={r['review_id']:r for r in read(OUT/'NATIVE_MAPPING.json')['events']}
    check('all_12_mapping_limitations_preserved',{k for k,r in mapping.items()if not r['mapping_supported']}=={k for k,r in by_decision.items()if r['code']=='M'} and sum(not r['mapping_supported']for r in mapping.values())==12)
    check('no_final_physical_origin_claims',all(r['final_physical_origin_confirmed'].lower()=='false'for r in decisions) and summary['all_origins_provisional']is True and summary['qualified_laser_candidates']==0)
    checkpoint=read(OUT/'checkpoints/LIBRARY_INPUTS.json');archives=checkpoint['archives'];input_manifest=read(OUT/'checkpoints/INPUT_ARCHIVES.json')
    check('all16_archive_identities_unique_and_prior8_preserved',len(state['input_archives'])==16 and len({r['library_file_id']for r in state['input_archives']})==16 and state['input_archives'][:len(old_state['input_archives'])]==old_state['input_archives']and len(old_state['input_archives'])==8)
    check('new8_archive_metadata_saved_and_in_state',len(archives)==8 and state['input_archives'][8:]==archives and all(r['status']=='succeeded'and r['local_metadata_applied']is True and r['library_url']=='https://chatgpt.com/library?file_id='+r['library_file_id']+'&account_id=personal'for r in archives))
    check('input_manifest_hash_matches',checkpoint['input_archives_manifest_sha256']==sha(OUT/'checkpoints/INPUT_ARCHIVES.json'))
    check('new8_archive_metadata_matches_packaging',all(all(a[k]==b[k]for k in['filename','bytes','sha256','products','complete_exposures'])for a,b in zip(archives,input_manifest['archives']))and len(input_manifest['archives'])==8)
    local_zip_checks=[]
    for r in input_manifest['archives']:
        p=Path(r['local_path']);local_zip_checks.append(dict(filename=r['filename'],bytes=p.stat().st_size,sha256=sha(p),passed=p.stat().st_size==r['bytes']and sha(p)==r['sha256']))
    check('all8_local_saved_archive_hashes_and_sizes',all(r['passed']for r in local_zip_checks),len(local_zip_checks))
    archive_products=[p for a in archives for p in a['products']];manifest=read(OUT/'products/MANIFEST.json');product_by={r['relative_path']:r for r in manifest['products']}
    check('new_archives_cover_exact64_canonical_products',len(archive_products)==len({r['relative_path']for r in archive_products})==len(product_by)==64 and set(r['relative_path']for r in archive_products)==set(product_by)and all(all(r[k]==product_by[r['relative_path']][k]for k in['sha256','bytes','dp_id','archive_id','kind'])for r in archive_products))
    check('no_residual_part_archive_members',not any(r['relative_path'].endswith('.part')for r in archive_products)and input_manifest['residual_part_files_included']==0)
    # Current root header is audited; unchanged historical archive links are out of scope.
    root_text=(REPO/'README.md').read_text();old_root=subprocess.check_output(['git','show','e4dd888cd711e7da9bd2e058d874fd55f525f37e:README.md'],cwd=REPO).decode()
    root_prefix=root_text[:-len(old_root)]if root_text.endswith(old_root)else root_text
    check('root_historical_README_unchanged',root_text.endswith(old_root))
    docs=[(REPO/'README.md',root_prefix),(REPO/'CONTINUE_SETI.md',(REPO/'CONTINUE_SETI.md').read_text()),(V2/'RESTORE.md',(V2/'RESTORE.md').read_text()),(CURRENT/'CURRENT_RESULTS.md',(CURRENT/'CURRENT_RESULTS.md').read_text()),(OUT/'README.md',(OUT/'README.md').read_text()),(OUT/'checkpoints/SAVED_INPUTS.md',(OUT/'checkpoints/SAVED_INPUTS.md').read_text())]
    links=[];broken=[]
    for file,content in docs:
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',content):
            target=target.strip().split(' "')[0].strip('<>')
            if not target or target.startswith(('#','http:','https:','mailto:')):continue
            relative=urllib.parse.unquote(target.split('#',1)[0]);p=(file.parent/relative).resolve()
            links.append(dict(source=str(file.relative_to(REPO)),target=target))
            if not p.exists():broken.append(links[-1])
    check('all_current_documentation_relative_links_resolve',not broken,dict(checked=len(links),broken=broken))
    check('root_current_header_counts_and_next_record',all(t in root_prefix for t in['115','32','575','669','94','37','V2E2-0243','142 A / 20 O / 61 U / 19 M / 94 N']))
    publication=state['publication']; publication_state=publication['state']
    if publication_state=='AWAITING_FINAL_PUBLICATION_READBACK':
        publication_ok=publication['publication_success_must_be_verified_separately']is True
    elif publication_state=='PUBLISHED_AND_REMOTE_READBACK_VERIFIED':
        receipt_path=REPO/publication['receipt']
        publication_ok=publication['publication_success_must_be_verified_separately']is False and receipt_path.is_file()
        if publication_ok:
            receipt=read(receipt_path)
            publication_ok=receipt.get('status')=='PUBLISHED_AND_REMOTE_READBACK_VERIFIED'
            if publication.get('receipt_sha256'):publication_ok=publication_ok and sha(receipt_path)==publication['receipt_sha256']
    else: publication_ok=False
    check('publication_state_is_explicit_and_locally_consistent',publication_ok,publication_state)
    check('no_unattended_worker_claim',state['execution']['active_science_workers']==0 and state['execution']['automatic_background_search']is False)
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS'if not failures else'FAIL',scope='Independent continuity, provenance, metadata and documentation audit; not a new raw-array or morphology review.',checks_passed=sum(r['passed']for r in checks),checks_total=len(checks),blocking_findings=failures,checks=checks,script_sha256=sha(Path(__file__)),audited_file_hashes={str(p.relative_to(REPO)):sha(p)for p in[OUT/'CONTINUATION_STATE.json',OUT/'SUMMARY.json',OUT/'ADOPTED_DISPOSITIONS.csv',CURRENT/'CURRENT_V2_ALL336_DISPOSITIONS.csv',CURRENT/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',V2/'CURRENT_V2_DISPOSITIONS.csv',CURRENT/'CURRENT_SUMMARY.json',V2/'CURRENT_STATUS.json',REPO/'README.md',REPO/'CONTINUE_SETI.md',V2/'RESTORE.md',OUT/'README.md',OUT/'checkpoints/LIBRARY_INPUTS.json']},local_zip_checks=local_zip_checks,limits='GitHub publication remains a separate root readback gate. Only the newly prepended current root README header is link-audited; unchanged historical archive links are not revalidated. Library persistence status comes from saved successful receipts; this audit independently verifies local archive hashes and published metadata, not remote Library bytes.')
    (AUDIT/'CONTINUITY_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],checks_passed=result['checks_passed'],checks_total=result['checks_total'],blocking_findings=failures,relative_links_checked=len(links),report=str((AUDIT/'CONTINUITY_AUDIT.json').relative_to(REPO))),indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
