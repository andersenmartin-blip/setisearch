#!/usr/bin/env python3
"""Build a complete cached-map and fixed-crop numerical reproduction package."""
from pathlib import Path
import hashlib,json,zipfile,time

ROOT=Path(__file__).resolve().parent.parent
B=ROOT/'carrier_followup'
O=B/'delivery'
started,cpu=time.monotonic(),time.process_time()
selected=set()
exclude={'__pycache__','library_helpers_current','qa_scratch'}
for p in B.rglob('*'):
    if not p.is_file() or any(x in exclude for x in p.relative_to(B).parts):continue
    if p.suffix in {'.zip','.tmp'} or p.name.startswith(('preview-','final-')):continue
    if p.name in {'PACKAGE_RECEIPT.json','UPLOAD_REQUEST.json','UPLOAD_RECEIPT.json'} or p.name.endswith('_entries.json'):continue
    selected.add(p.relative_to(ROOT).as_posix())

def gather(value):
    if isinstance(value,dict):
        if 'path' in value and isinstance(value['path'],str):
            p=ROOT/value['path']
            if p.is_file() and p.suffix!='.h5':selected.add(value['path'])
        for v in value.values():gather(v)
    elif isinstance(value,list):
        for v in value:gather(v)

for rel in ['carrier_followup/ranking/scope.json','carrier_followup/context/SCOPE.json',
            'carrier_followup/context/results/CONTEXT_PROFILES.json',
            'carrier_followup/reproduction/SCOPE.json',
            'next_dc/qa/context/REPRODUCTION_SCOPE.json',
            'next_dc/crossscan/results/CONTEXT_PROFILES.json',
            'next_dc/qa/context/RAW_NORMALIZATION_CROP_MANIFEST.json']:
    p=ROOT/rel
    assert p.is_file(),rel
    selected.add(rel);gather(json.loads(p.read_text()))
for rel in ['next_dc/ranking/scope.json','next_dc/ranking/ALL2289_GEOMETRY.json',
            'next_dc/ranking/SELECTED_TOP9.json','next_dc/crossscan/SCOPE.json',
            'next_dc/crossscan/driver.py','next_dc/qa/context/QA_RECEIPT.json',
            'next_dc/qa/selection/QA_RECEIPT.json',
            'next_dc/qa/context/reproduce_from_saved_crops.py',
            'next_dc/qa/context/REPRODUCTION_SCOPE.json',
            'next_dc/qa/context/REPRODUCTION_RECEIPT.json',
            'next_dc/qa/context/REPRODUCTION_GO.json',
            'seti_previous/analysis/new_visit_search/dependencies/detector.py',
            'seti_previous/analysis/s2017_next_native/source_manifest_v2.json']:
    selected.add(rel)

pins=[]
for rel in sorted(selected):
    p=ROOT/rel;assert p.is_file(),rel
    with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    pins.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha})
maps=json.loads((B/'ranking/scope.json').read_text())['groups']
map_paths={m['pin']['path'] for g in maps for m in g['maps']}
assert len(map_paths)==2289 and map_paths<=selected
manifest={'schema':'SETI_ALL_CARRIER_AND_FIXED_CROP_PACKAGE_V1','date_utc':'2026-10-12',
    'files':pins,'cached_map_files_included':2289,'cached_carrier_winners_included':9375744,
    'source_HDF5_compacts_included':False,'normalization_crops_included':True,
    'original_AB':'FAIL_CLOSED','qualified_SETI_detection':False,
    'new_observation':False,'new_telescope_requests':0,'cost_DKK':0}
archive=O/'SETI_KANALMAKSIMA_RESULTATER_2026-10-12.zip'
assert not archive.exists()
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for item in pins:
        raw=(ROOT/item['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        info=zipfile.ZipInfo(item['path'],(2026,10,12,12,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,raw)
    z.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert set(z.namelist())==selected|{'MANIFEST.json'}
    for item in pins:
        raw=z.read(item['path'])
        assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
with archive.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
receipt={'status':'PASS_EXACT_MEMBERS_ALL_CRC_PAYLOAD_SHA256','filename':archive.name,
    'bytes':archive.stat().st_size,'sha256':sha,'members':len(pins)+1,
    'uncompressed_payload_bytes':sum(p['bytes'] for p in pins),
    'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-started}
(O/'PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
