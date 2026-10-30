"""Verify restored historical native170/172 bytes and decoded rows, without search."""
from pathlib import Path
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work_be/runtime'))
import numpy as np
import h5py
import bitshuffle

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    metadata=ROOT/'next_native_bk_metadata'
    receipt=json.loads((metadata/'ACQUISITION_RESULT.json').read_text())
    manifest=json.loads((metadata/'source_manifest_v2.json').read_text())
    archive=ROOT/'next_native_bk_parts/SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip'
    assert archive.stat().st_size==604399781 and sha(archive)=='b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f'
    parts=[]
    for number,library_id,digest in [(1,'libfile_8815fd74d7b48191a566a9823f82eb5b','ad4be599d3e7da809df1d473c8fa677e0c2581d251fb65d9cc01d90849dd8dbb'),(2,'libfile_9c85de4fba3c8191822fbfdfd87b655a','2ad6609f4984c536fc4dbee2223975f756459d681b8c9e1f5c6b8731f149a97f'),(3,'libfile_cb891970f2dc81919c8cf09b9b8b7b71','d585965102de3ac3cbc9864a92249e0fb660ed6968540249c34e650b880b15ca')]:
        path=Path(str(archive)+f'.part{number:02d}');assert sha(path)==digest
        parts.append({'part':number,'file_name':path.name,'library_file_id':library_id,'bytes':path.stat().st_size,'sha256':digest})
    records=[];row_count=0
    for item in receipt['decoded_files']:
        path=ROOT/'next_native_bk_restored/analysis/s2017_next_native/results/acquire'/item['array_file']
        assert path.stat().st_size==item['bytes'] and sha(path)==item['file_sha256']
        rows=[]
        with h5py.File(path,'r') as h:
            d=h['data'];assert d.shape==(16,1,1048576) and d.chunks==(1,1,1048576) and d.dtype==np.dtype('<f4')
            assert int(d.attrs['original_source_frequency_chunk_origin'])==item['source_channel0']==item['native_chunk_index']*1048576
            for row in item['decoded_rows']:
                t=row['time_row'];mask,payload=d.id.read_direct_chunk((t,0,0));assert mask==0
                nbytes,blockbytes=struct.unpack('>QI',payload[:12]);assert nbytes==4194304 and blockbytes>0 and blockbytes%4==0
                values=bitshuffle.decompress_lz4(np.frombuffer(payload[12:],dtype=np.uint8),(1048576,),np.dtype('<f4'),block_size=blockbytes//4)
                digest=hashlib.sha256(values.tobytes()).hexdigest();assert digest==row['decoded_sha256']
                assert np.isfinite(values).all() and (values>=0).all()
                rows.append({'row':t,'sha256':digest});row_count+=1
        records.append({'native':item['native_chunk_index'],'scan_id':item['scan_id'],'path':str(path),'bytes':path.stat().st_size,'sha256':item['file_sha256'],'shape':[16,1,1048576],'dtype':'<f4','source_channel0':item['source_channel0'],'decoded_rows':rows})
    assert len(records)==12 and row_count==192
    result={'schema':'SETI_BK_ADJACENT_NATIVE_CACHE_PREPARATION_V1','status':'PASS_EXACT12_COMPACTS_192_DECODED_ROWS_NO_SEARCH',
      'completed_utc':datetime.now(timezone.utc).isoformat(),'archive_file_name':archive.name,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),
      'parts':parts,'native_chunk_indices':[170,172],'files':records,'verified_decoded_rows':row_count,
      'metadata_source_commit':'849c4079e81d9c502510681ed454be8f745c02bc',
      'acquisition_receipt_repo_path':'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json','acquisition_receipt_sha256':sha(metadata/'ACQUISITION_RESULT.json'),
      'source_manifest_repo_path':'analysis/s2017_next_native/source_manifest_v2.json','source_manifest_sha256':sha(metadata/'source_manifest_v2.json'),
      'coordinates':{n:{k:manifest['by_native_chunk'][n][k] for k in ['physical_channel_interval_half_open','frequency_center_limits_MHz']} for n in ('170','172')},
      'target':manifest['target'],'visit_id':manifest['visit_id'],'scan_order':manifest['scan_order'],'df_hz':manifest['df_hz'],'tsamp_s':manifest['tsamp_s'],
      'runtime_versions':{'numpy':np.__version__,'h5py':h5py.__version__,'bitshuffle':bitshuffle.__version__},
      'source_data_previously_exposed':True,'new_archive_requests':0,'new_independent_observations':0,'new_unique_archive_ID_credit':0,
      'new_signal_search_executed':False,'new_scores_computed':False,'global_original_search_credit_changed':False,
      'historical_outcomes_preserved':'Original A/B and B06/native172/q81 failure and no-retry statuses are unchanged; this is byte restoration, not replay or requalification.',
      'next_action':'Freeze a distinct expanded descriptive six-scan native170 family before scores, with correct physical channel/frequency coordinates and safe carrier exclusions. Native172 follows only under a separate fixed scope preserving all historical B06 outcomes. Same historical visit; no blind/fresh or new-observation claims.',
      'verification_limit':'Retained package/compact identities and decoded row hashes, not independent original HDF5 TREE/codec/model or whole-source-file MD5 qualification.'}
    destination=ROOT/'work_bk/next_data/PREPARED_ADJACENT_DATA_BK.json'
    with destination.open('x') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'status':result['status'],'verified_compacts':len(records),'verified_decoded_rows':row_count,'new_signal_search_executed':False,'receipt_path':str(destination)}))
if __name__=='__main__':main()
