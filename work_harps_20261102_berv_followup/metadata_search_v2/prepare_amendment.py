"""Create the separately authorized syntax-only amendment; no network."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=HERE.parent/'metadata_search'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,d):(HERE/n).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
assert not (HERE/'RUN_STARTED.json').exists()
previous=json.loads((OLD/'SUMMARY.json').read_text())
assert previous['target_requests']==1 and previous['status']=='STOPPED_BOUNDED_METADATA'
assert previous['returned_products']==0 and previous['metadata_candidates']==0
assert len(list(OLD.glob('*.ATTEMPT_STARTED.json')))==1
for name in ['EXISTING_300.json','TARGETS.json','SCHEMA_CONTRACT.json','search_metadata.py']:
    shutil.copyfile(OLD/name,HERE/name)
plan=json.loads((OLD/'PLAN.json').read_text())
plan['schema']='HARPS_BERV_METADATA_PLAN_V2_SYNTAX_AMENDMENT'
plan['predecessor_commit']='234562d3619ea894bfd4c8a9b58e7dd002f6f2e8'
plan['status']='PROSPECTIVE_SYNTAX_AMENDMENT_NOT_EXECUTED'
plan['limits'].update(continuation_target_requests_max=3,previous_failed_target_requests=1,additional_target_requests_max=2)
plan['technical_amendment']={'only_ADQL_change':'ORDER BY o.t_min ASC, o.dp_id ASC, p.source_file ASC → ORDER BY t_min ASC, dp_id ASC, source_file ASC',
 'original_stop_preserved':True,'original_query_valid_rows':0,'selection_criteria_and_science_unchanged':True,
 'authorization':'Parent explicitly authorized a new separately frozen two-request correction after the failed run. No automatic retry or self-adjusting loop.',
 'new_failure_rule':'Any new failure closes this amended run; no further automatic correction or target retry.',
 'official_contract':'OFFICIAL_SYNTAX_EVIDENCE.json'}
before='ORDER BY o.t_min ASC, o.dp_id ASC, p.source_file ASC\n'
after='ORDER BY t_min ASC, dp_id ASC, source_file ASC\n'
query_changes=[]
for req in plan['requests']:
    old=OLD/req['query_file'];q=old.read_text();assert q.count(before)==1
    new=q.replace(before,after);(HERE/req['query_file']).write_text(new)
    req['query_sha256']=sha(HERE/req['query_file'])
    assert new.replace(after,before)==q
    query_changes.append({'file':req['query_file'],'original_sha256':sha(old),'amended_sha256':req['query_sha256'],'exact_only_replacement':True})
for name in ['PREFLIGHT_FREEZE.json','PLAN.json','SUMMARY.json','RESULTS.md','RESULT_HASHES.json','RUN_STARTED.json','HD122640.ATTEMPT_STARTED.json','responses/HD122640.REQUEST.json','responses/HD122640.vot','search_metadata.py','sources/ESO_TAP_TABLES.xml']:
    path=OLD/name;plan['source_hashes'][str(path.relative_to(ROOT))]=sha(path)
save('PLAN.json',plan)
save('AMENDMENT.json',{'status':'SYNTAX_ONLY_BEFORE_ANY_VALID_RETURNED_ROWS','original_freeze_sha256':sha(OLD/'PREFLIGHT_FREEZE.json'),'original_requests_consumed':1,'additional_requests_max':2,'continuation_requests_max':3,'queries':query_changes,'executor_identical_to_original':sha(HERE/'search_metadata.py')==sha(OLD/'search_metadata.py'),'selection_payloads_identical':[name for name in ['EXISTING_300.json','TARGETS.json','SCHEMA_CONTRACT.json'] if sha(HERE/name)==sha(OLD/name)],'science_arrays_read':0,'live_query_tests':0})
print('Syntax-only correction prepared; original failure preserved; zero new target requests.')
