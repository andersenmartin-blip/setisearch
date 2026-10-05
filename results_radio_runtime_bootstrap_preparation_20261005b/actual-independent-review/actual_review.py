"""Read-only review of a closed B scope; no gate execution/import or live IO."""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat

BASE=Path('/workspace/scratch/66170938f826')
ROOT=BASE/'radio-runtime-bootstrap-20261005b'
PUB=BASE/'bootstrap-b-publication'
OUT=BASE/'bootstrap-b-review'
REPO=BASE/'setisearch'
checks=[]

def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(path.read_bytes())
def check(name,condition,detail=None):
    checks.append({'check':name,'passed':bool(condition),'detail':detail})
    if not condition: raise AssertionError(name+': '+str(detail))
def read_regular(path):
    """Hold all ancestors and the sole-link regular final object while hashing."""
    path=Path(path)
    if not path.is_absolute(): raise AssertionError('absolute path required')
    fds=[os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)]
    bindings=[]; fd=None
    try:
        for component in path.parts[1:-1]:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fds[-1])
            st=os.fstat(child); bindings.append((fds[-1],component,st.st_dev,st.st_ino)); fds.append(child)
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fds[-1]); before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1: raise AssertionError('non-sole regular input')
        chunks=[]
        while True:
            raw=os.read(fd,65536)
            if not raw: break
            chunks.append(raw)
        raw=b''.join(chunks); after=os.fstat(fd); named=os.stat(path.name,dir_fd=fds[-1],follow_symlinks=False)
        attrs=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)
        if attrs(before)!=attrs(after) or attrs(after)!=attrs(named): raise AssertionError('held/named input drift')
        for parent,name,device,inode in bindings:
            observed=os.stat(name,dir_fd=parent,follow_symlinks=False)
            if not stat.S_ISDIR(observed.st_mode) or (observed.st_dev,observed.st_ino)!=(device,inode): raise AssertionError('ancestor drift')
        return raw,before
    finally:
        if fd is not None: os.close(fd)
        for opened in reversed(fds): os.close(opened)

inv=load(PUB/'invocation-pins.json')
contract_path=REPO/'config/radio_runtime_bootstrap_20261005b.freeze.json'
cr,cst=read_regular(contract_path); c=json.loads(cr)
proof_raw,pst=read_regular(PUB/'publication-proof.json'); proof=json.loads(proof_raw)
activation_raw,ast=read_regular(Path(c['activation_path']))
marker=json.loads(activation_raw)
check('contract proof and activation raw external hashes',sha(cr)==inv['contract_sha256'] and sha(proof_raw)==inv['publication_proof_sha256'] and sha(activation_raw)==inv['activation_sha256'])
check('distinct B identity and fixed activation provenance',c['bootstrap_identity']==inv['bootstrap_identity']!= '7e4a63f99adcb7a9725211960b368db972e92b16c60bdf1a3d5220e49df2d52b' and proof['activation_parent']==proof['prepared_commit']==inv['prepared_commit'] and proof['activation_commit']==inv['activation_commit'] and proof['activation_changed_path']=='config/radio_runtime_bootstrap_20261005b.activate.json')
check('activation exact engineering and single-use binding',marker['engineering_only'] is True and marker['single_use'] is True and marker['contract_sha256']==sha(cr) and marker['bootstrap_identity']==c['bootstrap_identity'])
source=c['source_pins']; runtime=c['runtime_pins']; pins=source+runtime
check('full selected before-after receipts match contract',load(ROOT/'selected-runtime-before.json')==load(ROOT/'selected-runtime-after.json')==pins,{'source':len(source),'runtime':len(runtime),'total':len(pins)})
read_source_bytes=0
for pin in pins:
    raw,st=read_regular(Path(pin['path'])); read_source_bytes+=len(raw)
    if {'path':pin['path'],'bytes':len(raw),'sha256':sha(raw),'mode':format(st.st_mode&0o7777,'04o')}!=pin: raise AssertionError('selected pin changed:'+pin['path'])
check('all selected pins independently remain exact',True,{'files':len(pins),'bytes':read_source_bytes})
check('accepted gate source retained unchanged',next(p['sha256'] for p in source if Path(p['path']).name=='bootstrap_gate.py')=='057471012f946ce9fc5427a9c6f41a7fbb506fa2f6e0a7a6940cf85460f74f00')
for row,pin in zip(proof['publication_files'],source):
    raw=base64.b64decode(row['content_base64'],validate=True)
    expected={k:row[k] for k in ('path','bytes','sha256','mode')}
    if expected!=pin or len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['git_blob']: raise AssertionError('raw proof body pin/blob failed')
check('all detached source proof bodies match pins and intrinsic Git blobs',len(proof['publication_files'])==len(source) and len({r['repository_path'] for r in proof['publication_files']})==len(source))
readback=load(PUB/'preparation-readback.json')
for row in readback['files']:
    raw,st=read_regular(REPO/row['path'])
    if len(raw)!=row['bytes'] or sha(raw)!=row['sha256'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['git_blob']: raise AssertionError('recorded prepared local body/blob failed:'+row['path'])
check('prepared local bodies corroborate recorded full readback',len(readback['files'])==121 and sum(r['bytes'] for r in readback['files'])==3029584 and readback['complete_full_body_readback'] is True and readback['complete_intrinsic_git_blob_match'] is True and all(row['full_utf8_body_equal'] is True for row in readback['readbacks']))

# Independent anchored recursive walk, with final object hashes included.
fd=os.open(ROOT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
rows={}; files=directories=logical=allocated=0
try:
    def walk(parent,prefix=''):
        global files,directories,logical,allocated
        st=os.fstat(parent); directories+=1; logical+=st.st_size; allocated+=st.st_blocks*512
        rows[prefix or '.']={'kind':'directory','bytes':st.st_size,'allocated_bytes':st.st_blocks*512,'device':st.st_dev,'inode':st.st_ino,'mode':format(st.st_mode&0o7777,'04o')}
        for name in sorted(os.listdir(parent)):
            rel=name if not prefix else prefix+'/'+name
            observed=os.stat(name,dir_fd=parent,follow_symlinks=False)
            if stat.S_ISDIR(observed.st_mode):
                child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent)
                try:
                    if (os.fstat(child).st_dev,os.fstat(child).st_ino)!=(observed.st_dev,observed.st_ino): raise AssertionError('dir replaced')
                    walk(child,rel)
                    named=os.stat(name,dir_fd=parent,follow_symlinks=False)
                    if (named.st_dev,named.st_ino)!=(observed.st_dev,observed.st_ino): raise AssertionError('dir drift')
                finally: os.close(child)
            elif stat.S_ISREG(observed.st_mode) and observed.st_nlink==1:
                raw,st=read_regular(ROOT/rel); files+=1; logical+=len(raw); allocated+=st.st_blocks*512
                rows[rel]={'kind':'file','bytes':len(raw),'allocated_bytes':st.st_blocks*512,'device':st.st_dev,'inode':st.st_ino,'mode':format(st.st_mode&0o7777,'04o'),'sha256':sha(raw)}
            else: raise AssertionError('unsafe artifact object')
    walk(fd)
finally: os.close(fd)

manifest_raw,mst=read_regular(ROOT/'artifact-manifest.json'); manifest=json.loads(manifest_raw)
report_raw,rst=read_regular(ROOT/'supervisor-result.json'); report=json.loads(report_raw)
stdout_raw,sst=read_regular(PUB/'cli.stdout.raw'); stdout=json.loads(stdout_raw)
check('CLI report matches retained full report',stdout['report']==report and (PUB/'cli.stderr.raw').stat().st_size==0)
check('full report authenticates operational manifest',sha(manifest_raw)==report['artifact_manifest_sha256'])
manifest_rows={r['path']:r for r in manifest['manifest']['entries']}
for rel,row in manifest_rows.items():
    if row.get('hash_exclusion'): continue
    local=rows[rel]
    if any(local[k]!=row[k] for k in ('kind','bytes','allocated_bytes','device','inode','mode')) or (row['kind']=='file' and local['sha256']!=row['sha256']): raise AssertionError('manifest object mismatch:'+rel)
check('complete operational manifest matches every held current object',manifest['manifest']['complete'] is True and set(rows)-set(manifest_rows)=={'artifact-manifest.json','supervisor-result.json'},len(manifest_rows))
final=stdout['final_scope']
check('final independent recursive file directory and storage totals match CLI',final['files']==files==491 and final['directories']==directories==80 and final['logical_bytes']==logical==7679548 and final['allocated_bytes']==allocated==8814592,{'files':files,'directories':directories,'logical_bytes':logical,'allocated_bytes':allocated})

spent=load(ROOT/'spent.json'); acquisition=load(ROOT/'acquisition-numpy.json'); transport=load(ROOT/'transport-numpy.json'); selection=load(ROOT/'selected-proxy.json'); descriptor=load(ROOT/'transport-descriptor.json')
check('spent allocation irreversibly closed with no retry',report['status']=='CLOSED_FAILED' and spent['irreversible'] is True and spent['retry_allowed'] is False and report['retry_allowed'] is False and report['spent_forever'] is True and spent['bootstrap_identity']==report['bootstrap_identity']==c['bootstrap_identity'])
for key in ('contract_sha256','publication_proof_sha256','activation_sha256','prepared_commit','activation_commit'):
    check('spent report invocation binding '+key,spent[key]==report[key]==inv[key])
check('one selected PIP_PROXY endpoint preserved without fallback',selection==report['selected_proxy'] and selection['selection_reads']==1 and selection['environment_name']=='PIP_PROXY' and selection['selected_proxy_url']=='http://127.0.0.1:46149' and selection['direct_fallback'] is False and selection['retry'] is False)
check('selected trust descriptor and observed bytes match',sha((ROOT/'transport-descriptor.json').read_bytes())==c['transport_descriptor_sha256']==transport['transport_descriptor_sha256'] and transport['trust_observed_bytes']==descriptor['trust_binding']['bytes']==1310 and transport['trust_observed_sha256']==descriptor['trust_binding']['sha256'])
wheel=c['wheels'][0]; wheelpath=ROOT/'wheelhouse'/wheel['filename']
raw,wst=read_regular(wheelpath)
check('single original NumPy output remains empty and failed',wheel['name']=='numpy' and acquisition['filename']==wheel['filename'] and acquisition['url']==wheel['url'] and acquisition['expected_bytes']==wheel['bytes'] and acquisition['expected_sha256']==wheel['sha256'] and len(raw)==acquisition['written_bytes']==acquisition['received_body_bytes']==0 and sha(raw)==acquisition['sha256'] and acquisition['status']=='CLOSED_FAILED')
check('archive output exact recorded sole file identity',{'bytes':wst.st_size,'dev':wst.st_dev,'ino':wst.st_ino,'mode':wst.st_mode&0o7777,'nlink':wst.st_nlink}==acquisition['file_identity'])
check('CONNECT timeout raw receipts cleanup and zero HTTP body agree',acquisition==report['acquisition_receipts'][0] and report['transport_receipt_count']==1 and report['transport_receipt_paths']==['transport-numpy.json'] and transport['status']=='CLOSED_FAILED' and 'TimeoutError' in transport['failure'] and transport['received_connect_prefix_bytes']==0 and base64.b64decode(transport['received_connect_prefix_base64'])==b'' and transport['registered_resource_count']==transport['cleanup_attempt_count']==1 and not transport.get('cleanup_failures') and acquisition['http_status'] is None and acquisition['charged_body_reads']==0)
check('remaining wheels installer and science absent',not (ROOT/'acquisition-h5py.json').exists() and not (ROOT/'acquisition-hdf5plugin.json').exists() and len(list((ROOT/'wheelhouse').iterdir()))==1 and not list((ROOT/'site').iterdir()) and report['pip_child'] is None and report['installation_preflight'] is None and report['installed_package_checks'] is None and report['wheel_inspection_summaries']==[] and report['native_package_imports']==report['telescope_reads']==report['scientific_cases_run']==0 and not any(rel.startswith('child.') for rel in rows))
check('sixteen scientific authority fields remain false',len(report['authority'])==16 and all(v is False for v in report['authority'].values()) and spent['authority']==report['authority'])
charge=report['parent_explicit_read_charged_bytes']; received=report['parent_explicit_received_bytes']
check('selected read category sums and conservative joined reserve agree',charge==sum(report['parent_precharged_categories'].values()) and received==sum(report['parent_explicit_received_categories'].values()) and charge>=received and report['joined_read_conservative_charged_bytes']==charge+report['child_read_reserved_bytes'] and report['parent_precharged_categories']['network']==4178 and report['parent_explicit_received_categories']['network']==0)
check('selected finite budgets hold',charge<=c['limits']['parent_read_bytes'] and report['joined_read_conservative_charged_bytes']<=c['limits']['joined_read_bytes'] and max(logical,allocated)<=c['limits']['artifact_bytes'] and files<=c['limits']['file_count'] and directories<=c['limits']['directory_count'] and stdout['selected_whole_scope_elapsed_seconds']<=c['limits']['wall_seconds'])
check('selected observations have not been promoted to full certificates',report['joined_full_scope_io_qualified'] is False and report['interpreter_implicit_loader_closure_qualified'] is False and report['publication_provenance_network_reauthenticated_here'] is False and report['child_read_observed_bytes'] is None and report['joined_read_observed_bytes'] is None and report['runtime_qualification']=='PENDING_RUNTIME_QUALIFICATION' and transport['peer_verification_native_qualified'] is False and transport['tls_resource_custody_qualified'] is False and transport['runtime_qualified'] is False)

result={'schema':'radio-bootstrap-b-independent-actual-review-v1','status':'REVIEWED_CLOSED_FAILED','bootstrap_identity':c['bootstrap_identity'],'prepared_commit':inv['prepared_commit'],'activation_commit':inv['activation_commit'],'assertions_passed':len(checks),'checks':checks,'final_report_sha256':sha(report_raw),'final_manifest_sha256':sha(manifest_raw),'cli_stdout_sha256':sha(stdout_raw),'operational_files_hashed':files,'directories_observed':directories,'logical_bytes':logical,'allocated_bytes':allocated,'selected_explicit_read_charged_bytes':charge,'selected_explicit_received_bytes':received,'joined_read_conservative_charged_bytes':report['joined_read_conservative_charged_bytes'],'selected_elapsed_whole_seconds':stdout['selected_whole_scope_elapsed_seconds'],'review_operations':{'new_connection':0,'SSLContext':0,'gate_reexecution':0,'installation':0,'scientific_import':0,'telescope_read':0,'readonly_selected_source_files':len(pins),'readonly_selected_source_bytes':read_source_bytes,'readonly_artifact_files':files},'limitations':['This independent read-only review corroborates retained local bytes and recorded intrinsic Git blob IDs; it does not make a new network provenance claim.','Raw adapter acquisition receipts retain their emitted SIMULATION_ONLY wording; the separately scope-bound transport receipt correctly records ACTUAL_PACKAGE_BOOTSTRAP_ONLY without native TLS qualification.','Network charge includes conservative CONNECT send and bounded receive allowance. A zero received prefix does not establish actual wire bytes, proxy service state or end-to-end reachability.','Recorded zero scientific dispatch/import/access and empty site/absent child support engineering-only failure; artifacts do not provide a full native process/kernel/provider certificate.','The conservative full child read reserve remains charged although no child was dispatched.','This later review reads files outside the closed original attempt; its reads do not revise the original scope counters.']}
(OUT/'actual-review.json').write_text(json.dumps(result,indent=2)+'\n')
(OUT/'actual-REVIEW.md').write_text(f'''# Independent closed bootstrap B review

Result: **REVIEWED_CLOSED_FAILED**. All {len(checks)} independent assertions passed. No gate was rerun, and no new connection, SSL context, package installation/import or scientific access occurred.

The one original NumPy acquisition failed while receiving the proxy CONNECT response: `TimeoutError`. Both separate receipts are retained. The CONNECT prefix and HTTP body contain zero received bytes; the sole NumPy archive remains zero bytes. One raw resource was registered and one cleanup was attempted, with no recorded cleanup failure. h5py and hdf5plugin were unattempted, pip was never dispatched, and the site directory is empty. The recorded scientific imports, telescope reads and scientific cases remain zero, with all sixteen authority flags false.

The spent identity `{c['bootstrap_identity']}` remains irreversible and retry is false. The selected proxy is `http://127.0.0.1:46149`, read once from PIP_PROXY; no fallback or substitution is recorded. The explicit 1,310-byte trust pin agrees with observed bytes.

All 1,258 selected source/runtime pins match the before/after receipts and independent held-file hashes. The 13 detached source bodies match their intrinsic Git blobs. All 121 local prepared bodies (3,029,584 bytes) corroborate the recorded immutable full readback. This review made no new network provenance claim. Prepared commit: `{inv['prepared_commit']}`. Activation commit: `{inv['activation_commit']}`.

Every operational manifest entry matches the current held object. Independently hashing the two excluded final objects completes local review: report SHA-256 `{sha(report_raw)}`; manifest SHA-256 `{sha(manifest_raw)}`. Final scope: {files} files, {directories} directories, {logical:,} logical bytes and {allocated:,} allocated bytes. Whole selected elapsed time: {stdout['selected_whole_scope_elapsed_seconds']:.6f} seconds.

Selected explicit read charges sum to {charge:,} bytes; explicit received bytes sum to {received:,}. Network allowance is 4,178 charged bytes and zero received bytes. Conservative joined charge is {report['joined_read_conservative_charged_bytes']:,} bytes, including the full 1 GiB child reserve despite no child dispatch. These are selected counters, not a full wire, native loader, kernel/provider or peak-resource certificate. The report and transport receipt preserve those qualification limits. No scientific result or runtime qualification follows.

See `actual-review.json` for exact assertions. This later read-only review does not revise original attempt counters.
''')
print(json.dumps({k:result[k] for k in ('status','assertions_passed','final_report_sha256','final_manifest_sha256','operational_files_hashed','directories_observed','logical_bytes','allocated_bytes','selected_elapsed_whole_seconds')},indent=2))
