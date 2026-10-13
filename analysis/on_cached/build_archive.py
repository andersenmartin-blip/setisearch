#!/usr/bin/env python3
"""Package the new ON analysis with exact cached maps and portable raw crops."""
from pathlib import Path
import hashlib,json,zipfile,time

ROOT=Path(__file__).resolve().parent.parent;B=ROOT/'on_cached';O=B/'delivery'
started,cpu=time.monotonic(),time.process_time();chosen=set()
exclude={'__pycache__','deps','restored','raw_archives','results_archives','previous','original_results','on_results','qa_scratch'}
for p in B.rglob('*'):
    if not p.is_file() or any(v in exclude for v in p.relative_to(B).parts):continue
    if p.suffix in {'.h5','.zip','.whl','.tmp'} or p.name.startswith(('preview-','final-')):continue
    if p.name in {'PACKAGE_RECEIPT.json','UPLOAD_REQUEST.json','UPLOAD_RECEIPT.json'} or p.name.endswith('_entries.json'):continue
    if 'LIBRARY_SEARCH' in p.name or p.name.endswith('_download_request.json'):continue
    chosen.add(p.relative_to(ROOT).as_posix())

def gather(value):
    if isinstance(value,dict):
        if isinstance(value.get('path'),str):
            p=ROOT/value['path']
            if p.is_file() and p.suffix not in {'.h5','.zip','.whl'}:chosen.add(value['path'])
        for v in value.values():gather(v)
    elif isinstance(value,list):
        for v in value:gather(v)

for rel in ['on_cached/ranking/scope.json','on_cached/context/SCOPE.json',
            'on_cached/context/results/CONTEXT_PROFILES.json',
            'on_cached/qa/selection/scope.json','on_cached/qa/context/scope.json',
            'on_cached/reproduction/SCOPE.json',
            'next_dc/crossscan/results/CONTEXT_PROFILES.json',
            'next_dc/qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json',
            'next_dc/qa/context/REPRODUCTION_SCOPE.json']:
    p=ROOT/rel;assert p.is_file(),rel;chosen.add(rel);gather(json.loads(p.read_text()))
for rel in ['next_dc/qa/context/reproduce_from_saved_crops.py',
            'next_dc/qa/context/REPRODUCTION_SCOPE.json',
            'next_dc/qa/context/REPRODUCTION_GO.json',
            'next_dc/qa/context/REPRODUCTION_RECEIPT.json']:
    chosen.add(rel)
for folder in ['new_phase_science','new_phase_review']:
    for p in (ROOT/folder).glob('*'):
        if p.is_file():chosen.add(p.relative_to(ROOT).as_posix())
pins=[]
for rel in sorted(chosen):
    p=ROOT/rel;assert p.is_file(),rel
    with p.open('rb') as f:s=hashlib.file_digest(f,'sha256').hexdigest()
    pins.append({'path':rel,'bytes':p.stat().st_size,'sha256':s})
manifest={'schema':'SETI_ON_CACHED_WINNERS_AND_FIXED_CROP_PACKAGE_V1','date_utc':'2026-10-13',
    'files':pins,'source_full_HDF5_compacts_included':False,'raw_normalization_crops_included':True,
    'original_AB':'FAIL_CLOSED','qualified_SETI_detection':False,'new_telescope_requests':0,'cost_DKK':0}
archive=O/'SETI_MAALSTJERNE_RESULTATER_2026-10-13.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for item in pins:
        raw=(ROOT/item['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
        info=zipfile.ZipInfo(item['path'],(2026,10,13,12,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,raw)
    z.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None and set(z.namelist())==chosen|{'MANIFEST.json'}
    for item in pins:
        raw=z.read(item['path']);assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
with archive.open('rb') as f:s=hashlib.file_digest(f,'sha256').hexdigest()
receipt={'status':'PASS_EXACT_MEMBERS_ALL_CRC_PAYLOAD_SHA256','filename':archive.name,'bytes':archive.stat().st_size,
    'sha256':s,'members':len(pins)+1,'uncompressed_payload_bytes':sum(p['bytes'] for p in pins),
    'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-started}
(O/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
