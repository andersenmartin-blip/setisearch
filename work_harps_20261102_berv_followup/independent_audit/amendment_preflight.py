"""Focused review of the explicitly authorized ADQL ordering amendment."""
from pathlib import Path
import copy,datetime,hashlib,json,re
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=OUT.parents[1]
OLD=BASE/'metadata_search';NEW=BASE/'metadata_search_v2'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=read(OLD/'PLAN.json');new=read(NEW/'PLAN.json');amendment=read(NEW/'AMENDMENT.json');checks=[]
def check(label,value):
    assert value,label
    checks.append(label)
check('Original failed route independently audited',read(OUT/'RESULT_AUDIT.json')['status']=='PASS_SAFE_STOP_WITH_QUERY_CONTRACT_FAILURE')
check('Original consumed exactly one failed request',read(OLD/'SUMMARY.json')['target_requests']==1 and read(OLD/'SUMMARY.json')['status']=='STOPPED_BOUNDED_METADATA')
check('No original astronomical result',read(OLD/'SUMMARY.json')['returned_products']==0 and read(OLD/'CANDIDATES.json')==[])
check('Original second target not attempted',not(OLD/'HD135204.ATTEMPT_STARTED.json').exists())
check('New route has no execution markers',not(NEW/'RUN_STARTED.json').exists() and not list(NEW.glob('*.ATTEMPT_STARTED.json')) and not(NEW/'responses').exists())
for filename in ['search_metadata.py','EXISTING_300.json','TARGETS.json','SCHEMA_CONTRACT.json']:
    check('Unchanged reviewed implementation/input '+filename,(OLD/filename).read_bytes()==(NEW/filename).read_bytes())
check('Exact reviewed runtime inherited',sha(NEW/'search_metadata.py')==read(OUT/'RUNTIME_PREFLIGHT_AUDIT.json')['script_sha256'])
check('Same directory-depth runtime roots',NEW.parents[1]==OLD.parents[1]==ROOT)
for key,value in old.items():
    if key not in {'schema','status','predecessor_commit','requests','limits','source_hashes'}:check('Preserved scientific contract '+key,new[key]==value)
for key,value in old['limits'].items():check('Preserved per-run limit '+key,new['limits'][key]==value)
check('Explicit continuation budget',new['limits']['previous_failed_target_requests']==1 and new['limits']['additional_target_requests_max']==2 and new['limits']['continuation_target_requests_max']==3)
check('Amendment request accounting',amendment['original_requests_consumed']==1 and amendment['additional_requests_max']==2 and amendment['continuation_requests_max']==3)
check('No retrospective new astronomical data used',new['technical_amendment']['original_query_valid_rows']==0 and new['technical_amendment']['selection_criteria_and_science_unchanged'] is True)
for original,changed in zip(old['requests'],new['requests'],strict=True):
    filename=original['query_file'];a=(OLD/filename).read_text();b=(NEW/filename).read_text()
    old_clause='ORDER BY o.t_min ASC, o.dp_id ASC, p.source_file ASC'
    new_clause='ORDER BY t_min ASC, dp_id ASC, source_file ASC'
    check('Exactly one original ordering clause '+filename,a.count(old_clause)==1)
    check('Only permitted ADQL replacement '+filename,a.replace(old_clause,new_clause)==b)
    check('Amended query hash '+filename,sha(NEW/filename)==changed['query_sha256'])
    original_without_hash={k:v for k,v in original.items() if k!='query_sha256'}
    changed_without_hash={k:v for k,v in changed.items() if k!='query_sha256'}
    check('Request form/columns/endpoint unchanged '+filename,original_without_hash==changed_without_hash)
    keys=[x.strip().split()[0] for x in b.rsplit('ORDER BY ',1)[1].strip().split(',')]
    check('Unqualified identifiers allowed by official sort-key grammar '+filename,keys==['t_min','dp_id','source_file'] and all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',x) for x in keys))
    check('Unambiguous returned output names '+filename,all(changed['expected_columns'].count(x)==1 for x in keys))
for path,digest in new['source_hashes'].items():check('New frozen historical/failure source '+path,sha(ROOT/path)==digest)
for path,digest in old['source_hashes'].items():check('Original historical source binding retained '+path,new['source_hashes'][path]==digest)
original_freeze=read(OLD/'PREFLIGHT_FREEZE.json')
for path,record in original_freeze['files'].items():check('Original frozen artifact still immutable '+path,sha(OLD/path)==record['sha256'])
syntax=read(NEW/'OFFICIAL_SYNTAX_EVIDENCE.json')
check('Official primary grammar source',syntax['source_url']=='https://wiki.ivoa.net/internal/IVOA/IvoaVOQL/adql-bnf-v2.0.html')
check('Relevant official grammar preserved',syntax['short_exact_grammar_excerpts']==['<sort_key> ::= <column_name> | <unsigned_integer>','<column_name> ::= <identifier>','<column_reference> ::= [ <qualifier> <period> ] <column_name>'])
report={'status':'PASS_FOCUSED_SYNTAX_AMENDMENT_PREFLIGHT','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'checks_passed':len(checks),'checks':checks,'plan_sha256':sha(NEW/'PLAN.json'),'executor_sha256':sha(NEW/'search_metadata.py'),
        'query_hashes':{r['query_file']:sha(NEW/r['query_file']) for r in new['requests']},'auditor_script_sha256':sha(Path(__file__)),
        'independent_primary_source_verification':{'url':syntax['source_url'],'method':'Official IVOA BNF independently opened through web retrieval; column_name/column_reference and sort_key productions inspected at lines218/222/576. No archive query test.','conclusion':'The corrected unqualified returned-column identifiers satisfy the ADQL2.0 sort-key production. This addresses the observed period rejection; full service execution remains a prospective test.'},
        'scope':'Only qualified-to-unqualified ORDER BY syntax changed. All selection criteria, scientific inputs, transport implementation and per-request limits are identical to reviewed originals.',
        'root_authorized_additional_requests_max':2,'continuation_requests_max_including_original_failure':3,
        'archive_target_queries_by_review':0,'science_arrays_read':0,'original_labels_changed':0,
        'release_state':'No remaining amendment preflight blocker. A new prospective freeze, exact-byte publication verification and root release are still required; the original failed route is not reopened.',
        'limitations':['The original static preflight missed the ordering grammar restriction; its HTTP400 and stop remain preserved.',
                      'No valid astronomical rows have yet been received, so no epoch availability, BERV or origin conclusion follows.']}
(OUT/'AMENDMENT_PREFLIGHT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks),'plan_sha256':report['plan_sha256']}))
