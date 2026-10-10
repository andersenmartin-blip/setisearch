#!/usr/bin/env python3
"""Package saved outputs byte-exactly; never read scientific array values."""
import gzip
import hashlib
import json
from pathlib import Path
import resource
import signal
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/radio_signal_followup_20261010'
CPU_CAP = 10
start_cpu, start_wall = time.process_time(), time.monotonic()
resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP+1))
resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
signal.alarm(120)

def h(b):
    return hashlib.sha256(b).hexdigest()

def save(p, d):
    p.write_text(json.dumps(d, indent=2, allow_nan=False)+'\n')

def require(ok, why):
    if not ok:
        raise ValueError(why)

def files_in(rel):
    return [p for p in (ROOT/rel).rglob('*') if p.is_file() and '__pycache__' not in p.parts]

for rel in ['results/radio_drift_anchor_20261010/measurement/QA_RECEIPT.json',
            'results/radio_gap_drift_20261010/measurement/QA_RECEIPT.json',
            'results/radio_signal_followup_20261010/CLAIMS_AUDIT_RECEIPT.json']:
    d=json.loads((ROOT/rel).read_text())
    require(d['status'].startswith('PASS'), 'QA missing or non-PASS: '+rel)

checkpoint=ROOT/'results/radio_gap_drift_20261010/measurement/DRIFT_CHECKPOINT.json'
raw=checkpoint.read_bytes()
gz=checkpoint.with_suffix('.json.gz')
gz.write_bytes(gzip.compress(raw, compresslevel=1, mtime=0))
require(gzip.decompress(gz.read_bytes())==raw, 'Checkpoint gzip losslessness')

prefixes=['tools/radio_drift_anchor_20261010','tools/radio_gap_drift_20261010',
          'tools/radio_signal_followup_20261010','results/radio_drift_anchor_20261010',
          'results/radio_gap_drift_20261010','results/radio_signal_followup_20261010']
reports=[ROOT/x for x in ['RADIO_SIGNAL_FOLLOWUP_REPORT_2026-10-10.md',
                         'RADIO_DRIFT_ANCHOR_REPORT_2026-10-10.md',
                         'RADIO_GAP_DRIFT_REPORT_2026-10-10.md',
                         'RADIO_SIGNAL_FOLLOWUP_REPRODUCIBILITY_2026-10-10.md']]
require(all(p.is_file() for p in reports), 'Missing reports')
all_new=set(reports)
for rel in prefixes:
    all_new.update(files_in(rel))
all_new={p for p in all_new if p.name not in ['BUNDLE_MANIFEST.json','BUNDLE_RECEIPT.json','PUBLICATION_LAYOUT.json']}
public=[]
for p in sorted(all_new):
    rel=str(p.relative_to(ROOT))
    if p.suffix=='.npz' or p==checkpoint or '/environment_evidence/' in rel:
        continue
    b=p.read_bytes()
    public.append({'path':rel,'bytes':len(b),'sha256':h(b),
                   'git_blob_sha1':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest(),
                   'encoding':'base64' if p.suffix in ['.png','.gz','.csv'] else 'utf-8'})
layout={'schema':'SETI_SIGNAL_FOLLOWUP_PUBLICATION_LAYOUT_V1','public_files':public,
        'checkpoint_original_path':str(checkpoint.relative_to(ROOT)),
        'checkpoint_original_bytes':len(raw),'checkpoint_original_sha256':h(raw),
        'checkpoint_gzip_is_byte_lossless':True,
        'NPZ_products':'Complete originals in SETI_SIGNAL_FOLLOWUP_2026-10-10.zip',
        'self_excluded_from_public_files_to_avoid_recursive_hash':True}
save(OUT/'PUBLICATION_LAYOUT.json',layout)
all_new.add(OUT/'PUBLICATION_LAYOUT.json')

anchor_scope=json.loads((ROOT/'tools/radio_drift_anchor_20261010/analysis_scope.json').read_text())
gap_scope=json.loads((ROOT/'tools/radio_gap_drift_20261010/scope.json').read_text())
inputs={ROOT/x['path'] for x in anchor_scope['input_files']}
inputs.update(ROOT/x for x in gap_scope['pinned_dependency_files'])
inputs.add(ROOT/gap_scope['acquisition_summary_path'])
members=sorted(all_new|inputs)
require(all(p.is_file() for p in members), 'Missing bundle member')
records=[]
for p in members:
    b=p.read_bytes()
    records.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':h(b)})
save(OUT/'BUNDLE_MANIFEST.json',{'schema':'SETI_SIGNAL_FOLLOWUP_BUNDLE_MANIFEST_V1',
    'members':records,'manifest_excludes_own_hash':True,
    'six_compact_HDF5_inputs_external_archive':'SETI_FRESH_BAND151_RAW_2026-10-09.zip',
    'external_RAW_archive_sha256':'6696fe54086e019ce966816dc818969ca5f1682e3ff9211326f1a68d2323ef1d',
    'dependency_wheels_not_bundled':True,'scientific_arrays_decoded_by_packaging':False})
members.append(OUT/'BUNDLE_MANIFEST.json')
archive=ROOT.parent/'SETI_SIGNAL_FOLLOWUP_2026-10-10.zip'
require(not archive.exists(), 'No overwrite of prior delivered bundle')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
    for p in members:
        z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive) as z:
    require(z.testzip() is None, 'ZIP CRC error')
    for r in records:
        b=z.read(r['path'])
        require(len(b)==r['bytes'] and h(b)==r['sha256'], 'Bundle member byte mismatch')
    require(z.read('results/radio_signal_followup_20261010/BUNDLE_MANIFEST.json') ==
            (OUT/'BUNDLE_MANIFEST.json').read_bytes(), 'Manifest byte mismatch')
cpu,wall=time.process_time()-start_cpu,time.monotonic()-start_wall
require(cpu<=CPU_CAP and wall<=120, 'Packaging cap exceeded')
receipt={'schema':'SETI_SIGNAL_FOLLOWUP_BUNDLE_RECEIPT_V1','status':'PASS_BYTE_EXACT_ARCHIVE',
    'file_name':archive.name,'local_path':str(archive),'bytes':archive.stat().st_size,
    'sha256':h(archive.read_bytes()),'member_count':len(members),
    'all_manifest_member_SHA256_and_ZIP_CRC_verified':True,
    'checkpoint_gzip_byte_lossless':True,'CSV_original_CRLF_preserved':True,
    'no_scientific_array_values_decoded':True,'process_CPU_s':cpu,'wall_s':wall,
    'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    'CPU_cap_s':CPU_CAP,'activity_charged':'anchor preparation/QA/packaging/publication reservation',
    'whole_activity_CPU_measured':False,
    'bundle_receipt_is_external_to_avoid_archive_self_reference':True}
save(OUT/'BUNDLE_RECEIPT.json',receipt)
signal.alarm(0)
print(json.dumps(receipt))
