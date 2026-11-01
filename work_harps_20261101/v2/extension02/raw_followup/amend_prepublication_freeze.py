"""One-shot explicit acquisition-guard amendment; selection and science scope stay fixed."""
from common import *
oldpath=OUT/'attempts/prepublication_v1/FOLLOWUP_FREEZE.json';old=json.loads(oldpath.read_text());prior=sha(oldpath)
require(sha(OUT/'FOLLOWUP_FREEZE.json')==prior,'Current freeze is not the preserved initial version')
require(not(OUT/'DOWNLOAD_STARTED.json').exists(),'Cannot amend after download starts')
changed={'v2/extension02/raw_followup/acquire.py','v2/extension02/raw_followup/common.py','v2/extension02/raw_followup/extract_native.py'}
for rel,digest in old['source_hashes'].items():
 if rel not in changed:require(sha(BASE/rel)==digest,'Unexpected selection/source/code change '+rel)
extra=['transfer_guards.py','test_transfer_guards.py','GUARD_TEST_RESULTS.json','PREPUBLICATION_AMENDMENT.json','amend_prepublication_freeze.py','README.md']
paths=[BASE/rel for rel in old['source_hashes']]+[OUT/rel for rel in extra]
new={**old,'created_utc':now(),'version':2,'amends_unpublished_freeze_sha256':prior,'amendment_record':'PREPUBLICATION_AMENDMENT.json','source_hashes':{str(p.relative_to(BASE)):sha(p)for p in paths},'selection_and_remote_metadata_unchanged':True,'science_payload_downloads_before_amendment':0}
dump('FOLLOWUP_FREEZE.json',new);verify_freeze()
for path in OUT.glob('*.py'):compile(path.read_text(),str(path),'exec')
dump('PREPARATION_AUDIT.json',dict(created_utc=now(),freeze_version=2,freeze_sha256=sha(OUT/'FOLLOWUP_FREEZE.json'),freeze_sources_rehashed=len(new['source_hashes']),freeze_hashes_match=True,selected_exposures=8,selected_events=65,V1_events=6,V2_events=59,mapping_helpers_byte_identical_to_baseline={name:sha(OUT/name)==sha(BASE/'v2/triage_batch02'/name)for name in ['registration.py','local_registration.py']},syntax_compilation_passed=len(list(OUT.glob('*.py'))),offline_guard_tests_passed=read('GUARD_TEST_RESULTS.json')['tests_passed'],downloads_started=False,scope='Preparation integrity only; no real raw/native payload requests.'))
print('AMENDED_FREEZE_SHA256',sha(OUT/'FOLLOWUP_FREEZE.json'));print('PINNED_SOURCES',len(new['source_hashes']))
