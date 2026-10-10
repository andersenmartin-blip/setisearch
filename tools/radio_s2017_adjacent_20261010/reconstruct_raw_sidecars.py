#!/usr/bin/env python3
"""Reconstruct exact compressed sidecars from authenticated compact H5; no decode.

Optional native restriction lets a consumer reconstruct one bounded subset.
No HTTP, numerical arrays, detector or dataset value read is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda:handle.read(1024**2),b''):h.update(block)
    return h.hexdigest()


def require(ok,message):
    if not ok:raise ValueError(message)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acquisition-receipt',required=True,type=Path)
    p.add_argument('--expected-acquisition-sha256',required=True)
    p.add_argument('--compact-directory',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--native',type=int,choices=(170,172))
    args=p.parse_args()
    require(digest(args.acquisition_receipt)==args.expected_acquisition_sha256,'Acquisition receipt SHA differs')
    receipt=json.loads(args.acquisition_receipt.read_bytes())
    require(receipt['status']=='COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
        and receipt['complete_compact_files']==12 and receipt['source_range_count_authenticated']==192,
        'Complete192range/12compact receipt required')
    import h5py
    require(h5py.__version__=='3.15.1' and h5py.version.hdf5_version=='1.14.6','Pinned H5 runtime differs')
    args.output.mkdir(parents=True,exist_ok=False)
    records={(r['native_chunk_index'],r['scan_id'],r['time_row']):r for r in receipt['raw_range_records']}
    results=[]
    for file in receipt['decoded_files']:
        native=file['native_chunk_index'];label=file['scan_id']
        if args.native is not None and native!=args.native:continue
        path=args.compact_directory/file['array_file']
        require(Path(file['array_file']).name==file['array_file'] and path.stat().st_size==file['bytes']
            and digest(path)==file['file_sha256'],'Compact whole-file pin differs')
        with h5py.File(path,'r',rdcc_nbytes=0) as handle:
            data=handle['data']
            require(data.shape==(16,1,1048576) and data.dtype.str=='<f4'
                and int(data.attrs['original_source_frequency_chunk_origin'])==native*1048576,'Compact frame differs')
            for row in range(16):
                record=records[(native,label,row)];mask,raw=data.id.read_direct_chunk((row,0,0))
                sha=hashlib.sha256(raw).hexdigest()
                require(mask==0 and len(raw)==record['stored_size'] and sha==record['raw_sha256']
                    ==record['compact_raw_roundtrip_sha256'],'Stored compressed chunk SHA differs')
                relative=Path(record['path'])
                require(not relative.is_absolute() and '..' not in relative.parts and relative.parts[0]=='raw_ranges','Unsafe raw sidecar name')
                target=args.output/relative;target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                results.append({'path':relative.as_posix(),'bytes':len(raw),'sha256':sha})
    expected=96 if args.native is not None else 192
    require(len(results)==expected,'Complete bounded subset required')
    with (args.output/'RECONSTRUCTION_RECEIPT.json').open('x') as handle:
        json.dump({'status':'PASS_EXACT_COMPRESSED_SIDECARS_RECONSTRUCTED_NO_HTTP_NO_DECODE',
            'acquisition_receipt_sha256':args.expected_acquisition_sha256,'new_HTTP_requests':0,
            'spectral_values_decoded':False,'raw_files':results},handle,indent=2);handle.write('\n')

if __name__=='__main__':main()
