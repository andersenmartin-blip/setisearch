#!/usr/bin/env python3
"""Build the remaining eight fixed band selections from authenticated JSON only.

No NumPy import, raw NPZ read/decode, detector import or scientific execution.
The source ZIP is hashed completely; only its context JSON is decompressed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ARCHIVE_BYTES = 48468705
ARCHIVE_SHA256 = '52b948958c89069a7afb563cf377ee33e4f1324e014428d597b4b3e3a20f6eb3'
MEMBER = 'SETI_NATIVE_SPOR_2026-10-14/seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
METADATA_BYTES = 629588
METADATA_SHA256 = '31efe1e5eeba63d10fbc04ea60bd29eb3086f142b6111a185f821a40a0558522'
PREFIX = 'SETI_NATIVE_SPOR_2026-10-14/'
SCANS = ('epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off')


def require(condition,message):
    if not condition:
        raise ValueError(message)


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1<<20):
            digest.update(block)
    return digest.hexdigest()


def build(archive_path,output):
    archive_path=Path(archive_path).resolve();output=Path(output)
    require(archive_path.is_file() and not archive_path.is_symlink()
            and archive_path.stat().st_size==ARCHIVE_BYTES and sha(archive_path)==ARCHIVE_SHA256,
            'Exact restored original source ZIP required')
    require(zipfile.is_zipfile(archive_path),'Valid source ZIP central directory required')
    with zipfile.ZipFile(archive_path) as archive:
        require(archive.namelist().count(MEMBER)==1,'Unique original metadata member required')
        raw=archive.read(MEMBER)
        require(len(raw)==METADATA_BYTES and hashlib.sha256(raw).hexdigest()==METADATA_SHA256,
                'Exact original source context JSON required')
        matrix=json.loads(raw)
        groups=sorted({(c['native_chunk_index'],c['core_q']) for c in matrix['normalization_crops']})
        require(len(groups)==9 and groups[0]==(170,131),'Original canonical nine-band order required')
        cases=[];source_headers_checked=0
        for index in range(1,9):
            native,q=groups[index]
            crops=[c for c in matrix['normalization_crops']
                   if (c['native_chunk_index'],c['core_q'])==(native,q)]
            by_scan={c['scan_id']:c for c in crops}
            require(len(crops)==6 and set(by_scan)==set(SCANS),'Six original raw crops required per band')
            first=by_scan[SCANS[0]]
            core=first['normalization_source_channel_interval_half_open']
            loaded=first['source_channel_interval_half_open']
            require(core==[native*1048576+q*4096,native*1048576+(q+1)*4096]
                    and loaded==[core[0]-4000,core[1]+4000],'Original fixed native source geometry required')
            scans=[]
            for scan_id in SCANS:
                crop=by_scan[scan_id]
                require(crop['normalization_source_channel_interval_half_open']==core
                        and crop['source_channel_interval_half_open']==loaded,
                        'Same original band geometry required across scans')
                declaration={'scan_id':scan_id}
                for field,source_field in [('raw_crop','raw_crop'),('normalization','normalization')]:
                    d={**crop[source_field],'path':'seti_work/'+crop[source_field]['path']}
                    member=PREFIX+d['path']
                    require(archive.namelist().count(member)==1 and
                            archive.getinfo(member).file_size==d['bytes'],
                            'Original member header size/census differs')
                    source_headers_checked+=1
                    declaration[field]=d
                scans.append(declaration)
            band={'native_chunk_index':native,'core_q':q,'diagnostic_only':True,
                'family':'real_sham','fresh_background':False,'synthetic_injection':False,
                'source_rows_per_scan':16,'reference_source_channel_interval':core,
                'loaded_source_channel_interval':loaded,'scans':scans,
                'interpretation':'Exposed 2017 background diagnostic; neither independent null nor new observation; no synthetic Gamma16 FAP transfer.'}
            cases.append({'canonical_index':index,
                'identity':f'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B{index:02d}',
                'band':band})
    result={'schema':'SETI_REMAINING_REAL_DESCRIPTIVE_COHORT_SOURCE_SELECTION_V1',
        'mode':'DESCRIPTIVE_POSTSELECTED_2017','status':'METADATA_ONLY_REQUIRES_NEW_PUBLIC_EXECUTABLE_FREEZE',
        'source_archive':{'path':str(archive_path),'bytes':ARCHIVE_BYTES,'sha256':ARCHIVE_SHA256},
        'source_metadata':{'member':MEMBER,'bytes':METADATA_BYTES,'sha256':METADATA_SHA256},
        'canonical_nine_band_order':[{'canonical_index':i,'native_chunk_index':n,'core_q':q}
                                   for i,(n,q) in enumerate(groups)],
        'excluded_completed_case':{'canonical_index':0,'identity':'SETI_REAL_FULLSCAN_DESCRIPTIVE_20261016_B00',
            'endpoint_unchanged':True},'cases':cases,'case_count':8,
        'member_headers_checked_without_reading_raw_members':source_headers_checked,
        'raw_NPZ_members_read':0,'raw_arrays_decoded':0,'numerical_jobs_run':0,
        'old_case_ids_reused':False,'original_A_B':'FAIL_CLOSED',
        'protected_2016_closed':True,'unavailable_2019_closed':True,
        'new_telescope_requests':0,'new_telescope_bytes':0,'cost_DKK':0,
        'builder_source':{'path':str(Path(__file__).resolve()),'sha256':sha(__file__)}}
    require([c['canonical_index'] for c in cases]==list(range(1,9))
            and len({c['identity'] for c in cases})==8 and source_headers_checked==96,
            'Complete exact remaining-case census required')
    data=(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    with output.open('xb') as stream:stream.write(data)
    return {'status':result['status'],'cases':8,'source_headers':96,
            'output_bytes':len(data),'output_sha256':hashlib.sha256(data).hexdigest(),
            'raw_arrays_decoded':0,'numerical_jobs_run':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.archive,args.output),sort_keys=True))
