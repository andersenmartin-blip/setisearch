"""Restore only hash-bound text and selected saved-case members; no scoring."""
import base64,hashlib,io,json,tarfile
from pathlib import Path,PurePosixPath

BASE=Path.cwd().resolve();OUT=Path(__file__).resolve().parent

def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def place(path,b,size,expected):
    target=(BASE/path).resolve()
    if not target.is_relative_to(BASE):raise ValueError('Output escapes project root')
    if len(b)!=size or sha(b)!=expected:raise ValueError('Original bytes differ: '+path)
    existed=target.exists()
    if existed:
        if target.read_bytes()!=b:raise ValueError('Refuse overwrite of different existing input: '+path)
    else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
    return {'path':path,'bytes':len(b),'sha256':sha(b),'existed_identical':existed,'restored_original_bytes':True}

def main():
    receipt=OUT/'RESTORATION_RECEIPT.json'
    if receipt.exists():raise ValueError('Restoration receipt exists: preserve previous attempt')
    t=json.loads((OUT/'TRANSFER_BINDINGS.json').read_text());m=json.loads((OUT/'INPUT_MANIFEST.json').read_text())
    records=[];archives=[]
    for e in t['texts']:
        b=(BASE/e['transfer_path']).read_bytes()
        if blob(b)!=e['git_blob_sha1']:raise ValueError('Git text blob differs: '+e['path'])
        records.append(place(e['path'],b,e['bytes'],e['observed_sha256']))
    for i,e in enumerate(t['archives']):
        raw=base64.b64decode((BASE/e['transfer_path']).read_text(),validate=True)
        if len(raw)!=e['bytes'] or sha(raw)!=e['declared_sha256'] or blob(raw)!=e['git_blob_sha1']:raise ValueError('Original archive bytes differ: '+e['path'])
        selected=m['case_members'] if i==0 else m['coordinator_selected_members']
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
            members=tar.getmembers()
            if sum(x.size for x in members)>33554432:raise ValueError('Archive exceeds bounded declared restore allowance')
            for x in members:
                p=PurePosixPath(x.name)
                if p.is_absolute() or '..' in p.parts or not (x.isfile() or x.isdir()):raise ValueError('Unsafe archive member: '+x.name)
            chosen=[]
            for wanted in selected:
                direct=[x for x in members if x.isfile() and x.name==wanted['path']]
                matches=direct or [x for x in members if x.isfile() and PurePosixPath(x.name).name==Path(wanted['path']).name]
                if len(matches)!=1:raise ValueError('Ambiguous/missing original member: '+wanted['path'])
                x=matches[0]
                if x.size!=wanted['bytes']:raise ValueError('Member metadata size differs')
                b=tar.extractfile(x).read()
                rec=place(wanted['path'],b,wanted['bytes'],wanted['sha256']);rec['original_tar_member']=x.name;records.append(rec);chosen.append(x.name)
        archives.append({'path':e['path'],'bytes':len(raw),'git_blob_sha1':blob(raw),'sha256':sha(raw),'original_compressed_bytes_authenticated':True,'selected_members':chosen,'unselected_members_not_restored':True})
    if len(records)!=54 or sum(x['bytes'] for x in records)!=1896541:raise ValueError('Restored layout differs from manifest')
    output=BASE/'pilot_protocol_20261008/review/METHOD_SAVED_CASE_000_REPRODUCTION.json'
    if output.exists():raise ValueError('Verification output already exists: no invocation')
    result={'status':'PASS_EXACT_SAVED_CASE_INPUT_RESTORATION','actual_date':'2026-10-08','source_commit':t['source_commit'],'files':records,'file_count':len(records),'restored_bytes':sum(x['bytes'] for x in records),'archives':archives,'compressed_bytes':sum(x['bytes'] for x in archives),'all_original_admission_claim_input_bytes_preserved':True,'numeric_maps_deserialized':0,'generator_detector_import_or_execution':False,'fresh_verifier_output_absent':True,'verifier_run_here':False}
    with receipt.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'file_count':len(records),'restored_bytes':result['restored_bytes'],'compressed_bytes':result['compressed_bytes'],'verification_output_absent':True}))

if __name__=='__main__':main()
