"""Build lossless public evidence for the completed closed scope and inert repair."""
from pathlib import Path
import base64,hashlib,json
BASE=Path('/workspace/scratch/da6462abff17')
HERE=Path(__file__).resolve().parent
ROOT=BASE/'radio-offline-runtime-materialization-20261005c'
REPAIR=BASE/'runtime-elf-parser-repair'
PREFIX='results_radio_offline_runtime_materialization_20261005c/actual'
payload={};metadata={}
def add_raw(name,raw):
    try:
        body=raw.decode('utf-8')
        if '\0' in body:raise UnicodeError()
        encoding='utf-8'
    except UnicodeError:
        body=base64.b64encode(raw).decode('ascii')+'\n';name+='.base64';encoding='base64'
    encoded=body.encode('utf-8')
    if len(encoded)>950000:raise ValueError('oversized immutable body: '+name)
    payload[name]=body
    metadata[name]=dict(raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),encoding=encoding,
        utf8_bytes=len(encoded),git_blob=hashlib.sha1(b'blob '+str(len(encoded)).encode()+b'\0'+encoded).hexdigest())
def add(name,path):add_raw(name,Path(path).read_bytes())
for path in [ROOT/'result.json',ROOT/'caller-receipt.json',ROOT/'spent.json',ROOT/'installed-byte-evidence.json',
             ROOT/'installer/preparation-receipt.json',ROOT/'installer/spent.json',ROOT/'installer/wheel-lock.txt']:
    add(PREFIX+'/'+path.relative_to(ROOT).as_posix(),path)
for path in sorted((ROOT/'processes').iterdir()):
    if path.is_file():add(PREFIX+'/processes/'+path.name,path)
for path in sorted((ROOT/'admission').iterdir()):
    if path.is_file():add(PREFIX+'/admission/'+path.name,path)
for suffix in ['.caller-stdout','.caller-stderr']:
    add(PREFIX+'/outer'+suffix,BASE/(ROOT.name+suffix))
for name in ['preservation-summary.json','ACTUAL_REVIEW.md','preserve_closed_scope.py','build_publication.py']:
    add(PREFIX+'/'+name,HERE/name)
add(PREFIX+'/administrative-first-archive-outcome.txt',HERE/'initial-administrative-attempt/OUTCOME.txt')
add(PREFIX+'/administrative-first-archive-source.py',HERE/'initial-administrative-attempt/preserve_closed_scope.py')
manifest=(HERE/'preservation-manifest.json').read_bytes();parts=[]
for n,start in enumerate(range(0,len(manifest),350000)):
    raw=manifest[start:start+350000];name=PREFIX+'/preservation-manifest.json.part'+str(n).zfill(4)+'.base64'
    body=base64.b64encode(raw).decode('ascii')+'\n';add_raw(name,body.encode())
    parts.append(dict(path=name,decoded_bytes=len(raw),decoded_sha256=hashlib.sha256(raw).hexdigest()))
index=dict(schema='radio-preservation-manifest-base64-parts-v1',parts=parts,total_decoded_bytes=len(manifest),
    decoded_sha256=hashlib.sha256(manifest).hexdigest(),reconstruction='Decode each part separately as base64, concatenate in listed order; then verify total length and SHA-256.')
add_raw(PREFIX+'/preservation-manifest-parts.json',(json.dumps(index,sort_keys=True,indent=2)+'\n').encode())
for path in sorted(REPAIR.rglob('*')):
    if path.is_file() and '__pycache__' not in path.parts:
        add('results_radio_elf_parser_repair_20261005/'+path.relative_to(REPAIR).as_posix(),path)
add('RADIO_OFFLINE_RUNTIME_MATERIALIZATION_2026-10-05C_RESULT.md',HERE/'RADIO_OFFLINE_RUNTIME_MATERIALIZATION_2026-10-05C_RESULT.md')
add('PROJECT_STATUS.md',HERE/'PROJECT_STATUS.md')
(HERE/'result-publication-payload.json').write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n')
(HERE/'result-publication-metadata.json').write_text(json.dumps(metadata,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(files=len(payload),utf8_bytes=sum(len(x.encode()) for x in payload.values()),largest=max(len(x.encode()) for x in payload.values()))))
