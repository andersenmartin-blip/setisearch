"""Restore redundant source sidecars from authenticated compact HDF5 raw chunks.

Run from the extracted RAW archive root. No decoding, HTTP or scientific search.
Original partial and complete HDF5 files stay unchanged.
"""
from pathlib import Path
import hashlib, json, os
import h5py

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

stage=Path('analysis/new_visit_recovery/results/acquire')
receipt=json.loads((stage/'ACQUISITION_RESULT.json').read_bytes())
if not receipt['status'].startswith('COMPLETE_'): raise ValueError('Complete source acquisition required')
records=receipt['raw_range_records']
if len(records)!=96: raise ValueError('Exactly96 source ranges required')
for source in receipt['decoded_files']:
    path=stage/source['array_file']
    if sha(path)!=source['file_sha256']: raise ValueError('Sourcefile SHA differs')
    with h5py.File(path,'r',rdcc_nbytes=0) as h:
        for item in records:
            if item['scan_id']!=source['scan_id']: continue
            mask,raw=h['data'].id.read_direct_chunk((item['time_row'],0,0))
            if mask!=0 or len(raw)!=item['stored_size'] or hashlib.sha256(raw).hexdigest()!=item['raw_sha256']:
                raise ValueError('Exact compressed source bytes differ')
            target=stage/item['path']; target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:
                f.write(raw);f.flush();os.fsync(f.fileno())
print('Restored96 byte-identical compressed sidecars; no sourcevalues decoded')
