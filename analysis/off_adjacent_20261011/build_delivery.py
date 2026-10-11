"""Archive the completed result and reproduction inputs; raw sources stay external."""
import hashlib,json,zipfile,time,resource
from pathlib import Path

root=Path(__file__).resolve().parents[2]
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_text())
qa=read(root/'analysis/off_adjacent_20261011_qa/results/QA_RECEIPT.json')
assert qa['status'].startswith('PASS'),qa['status']
context=read(root/'analysis/off_adjacent_20261011_context/results/EXECUTION_RECEIPT.json')
assert context['status'].startswith('COMPLETE')
review=read(root/'analysis/off_adjacent_20261011_context/CONTEXT_QA_RECEIPT.json')
assert review['status'].startswith('PASS')
files=set()
for folder in ['analysis/off_adjacent_20261011','analysis/off_adjacent_20261011_qa','analysis/off_adjacent_20261011_context']:
 for p in (root/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.lock':files.add(p)
scope=read(root/'analysis/off_adjacent_20261011/scope.json')
ctxscope=read(root/'analysis/off_adjacent_20261011_context/context_scope.json')
for pin in scope['text_code_pins']+ctxscope['input_pins']:
 p=root/pin['path'];assert p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256'];files.add(p)
for p in (root/'analysis/runtime/wheels').glob('*.whl'):files.add(p)
for name in ['analysis/RESTORE_20261011.py','analysis/RESTORATION_RECEIPT_20261011.json','analysis/REMOVED_DUPLICATE_TEMP_CACHE_20261011.json']:
 files.add(root/name)
out=root.parent/'deliverables';out.mkdir(exist_ok=True)
archive=out/'SETI_ADJACENT_CONTROL_RESULTS_2026-10-11.zip'
manifest={'schema':'SETI_ADJACENT_COMPLETED_RESULT_PACKAGE_V1','files':[{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)],'raw_sources_external':[
 {'name':'SETI_S2017_NATIVE171_RAW_2026-10-10.zip','sha256':'6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786'},
 {'name':'SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip.part01 + part02 + part03','reassembled_sha256':'b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f'}],
 'raw_sources_copied':False,'new_observation':False,'qualified_SETI_detection':False,'scope_sha256':sha(root/'analysis/off_adjacent_20261011/scope.json'),
 'primary_QA_sha256':sha(root/'analysis/off_adjacent_20261011_qa/results/QA_RECEIPT.json'),'context_QA_sha256':sha(root/'analysis/off_adjacent_20261011_context/CONTEXT_QA_RECEIPT.json')}
t=time.perf_counter();cpu=time.process_time()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(files):z.write(p,p.relative_to(root).as_posix())
 z.writestr('RESULT_PACKAGE_MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for record in manifest['files']:
  assert hashlib.sha256(z.read(record['path'])).hexdigest()==record['sha256']
receipt={'status':'PASS_COMPLETE_ARCHIVE_CRC_AND_MEMBER_SHA256','archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'payload_files':len(files),'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-t,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
(out/'ARCHIVE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
