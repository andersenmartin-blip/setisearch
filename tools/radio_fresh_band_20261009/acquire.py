"""Separate exploratory newband acquisition. Never calls the qualified pilot CLI."""
import hashlib, importlib.metadata, importlib.util, json, resource, signal, time, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)

def main():
    started,cpu=time.monotonic(),time.process_time()
    scope_path=ROOT/'tools/radio_fresh_band_20261009/acquisition_scope.json'
    scope=json.loads(scope_path.read_text())
    for name,pin in scope['pinned_files'].items():
        assert digest(ROOT/name)==pin, ('frozen file mismatch',name)
    manifest=json.loads((ROOT/scope['source_manifest']).read_text())
    assert manifest['status']=='OFFLINE_METADATA_PINNED_FOR_SEPARATE_EXPLORATORY_ACQUISITION'
    assert manifest['new_band_values_opened'] is False
    interval=tuple(manifest['physical_channel_interval_half_open'])
    assert interval==(158334976,159383552)
    items=manifest['sources']
    assert [x['label'] for x in items]==scope['scans'] and [x['role'] for x in items]==['on','off']*3
    assert sum(x['future_spectral_payload_bytes'] for x in items)==305137622
    spec=importlib.util.spec_from_file_location('unchanged_pure_reader',ROOT/'pilot_reader_20261008/value_reader.py')
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    # Explicit origin configuration for the reused compact-dataset helper only.
    # The old gated run() and validate_source() remain untouched and are never called.
    reader.PHYSICAL_INTERVAL=interval
    for item in items:
        assert item['dtype_exact']=='<f4'
        assert item['current_header']['dataset_shape']==[16,1,264503296]
        assert item['current_header']['dataset_chunks']==[1,1,1048576]
        assert len(item['chunks'])==16
        for row,ch in enumerate(item['chunks']):
            assert ch['time_row']==row and ch['chunk_origin']==[row,0,interval[0]]
            assert ch['filter_mask']==0 and ch['decoded_size']==4194304
            assert 0<ch['stored_size']<=5*1024**2
            assert ch['byte_range']==f"bytes={ch['byte_offset']}-{ch['byte_offset']+ch['stored_size']-1}"
            assert ch['byte_offset']+ch['stored_size']<=item['source_file_bytes']
    out=ROOT/'results/radio_fresh_band_20261009/arrays';out.mkdir(parents=True,exist_ok=False)
    initial=scope['prior_same_cadence_source_plus_metadata_BODY_bytes']
    ledger={'source_body_bytes_received':initial,'source_body_bytes_charged_upper_bound':initial,
            'new_value_requests_attempted':0,'source_body_byte_ceiling':2147483648,
            'new_activity_body_ceiling':scope['new_spectral_BODY_byte_ceiling'],'prior_body_bytes':initial,'complete':False}
    receipts=[]
    result={'status':'ACQUISITION_IN_PROGRESS','qualification':'FAIL_CLOSED_UNCHANGED',
            'source_manifest_sha256':digest(ROOT/scope['source_manifest']),'scope_sha256':digest(scope_path),
            'script_sha256':digest(__file__),'source_channel0':interval[0],
            'physical_channel_interval_half_open':list(interval),'new_observation_visit':False,
            'value_read_requests':receipts,'decoded_files':[],'decoded_row_progress':{},'local_pipeline_records':[]}
    def deadline(s,f):raise TimeoutError('Bounded acquisition wall limit')
    signal.signal(signal.SIGALRM,deadline);signal.alarm(scope['wall_limit_s'])
    resource.setrlimit(resource.RLIMIT_CPU,(scope['CPU_limit_s'],scope['CPU_limit_s']))
    resource.setrlimit(resource.RLIMIT_AS,(scope['memory_limit_bytes'],scope['memory_limit_bytes']))
    try:
        h5py,plugin,np=reader.current_codecs()
        result['versions']={n:importlib.metadata.version(n) for n in ['h5py','hdf5plugin','numpy']}
        assert result['versions']==scope['versions']
        result['versions']['hdf5']=h5py.version.hdf5_version
        opener=urllib.request.build_opener(reader.NoRedirect())
        for item in items:
            path=out/(item['label']+'.compact.h5');decoded_rows=[]
            result['decoded_row_progress'][item['label']]=decoded_rows
            with h5py.File(path,'x',rdcc_nbytes=8*1024**2) as handle:
                ds,pipeline=reader.create_compact_dataset(handle,item,h5py,plugin)
                assert int(ds.attrs['original_source_frequency_chunk_origin'])==interval[0]
                result['local_pipeline_records'].append({'scan_id':item['label'],**pipeline})
                for ch in item['chunks']:
                    assert ledger['new_value_requests_attempted']<96
                    assert ledger['source_body_bytes_charged_upper_bound']-initial+ch['stored_size']+1<=scope['new_spectral_BODY_byte_ceiling']
                    body=reader.acquire_chunk(item,ch,ledger,out/'SOURCE_BODY_LEDGER.json',receipts,opener)
                    origin=(ch['time_row'],0,0);ds.id.write_direct_chunk(origin,body,filter_mask=0)
                    mask,retained=ds.id.read_direct_chunk(origin);assert mask==0 and retained==body
                    row=ds[ch['time_row'],0,:]
                    assert row.shape==(1048576,) and row.dtype==np.dtype('<f4') and np.isfinite(row).all() and (row>=0).all()
                    decoded_rows.append({'time_row':ch['time_row'],'decoded_bytes':row.nbytes,
                                         'decoded_sha256':hashlib.sha256(row.tobytes(order='C')).hexdigest()})
                    save(out/'ACQUISITION_RESULT.json',result)
                    print(json.dumps({'event':'FRESH_ROW_RECEIVED','scan':item['label'],'row':ch['time_row'],
                                      'new_bodybytes':ledger['source_body_bytes_received']-initial}),flush=True)
            result['decoded_files'].append({'scan_id':item['label'],'array_file':path.name,
                                            'file_sha256':digest(path),'bytes':path.stat().st_size,
                                            'source_channel0':interval[0],'shape':[16,1,1048576],
                                            'decoded_rows':decoded_rows})
        assert len(receipts)==96 and len(result['decoded_files'])==6
        assert ledger['source_body_bytes_received']-initial==305137622
        ledger['complete']=True;result['status']='COMPLETE_SIX_SCAN_FRESH_FREQUENCY_CHUNK_EXPLORATORY_ONLY'
    except BaseException as e:
        result.update(status='FAILED_CLOSED_NO_RETRY',error_type=type(e).__name__,error=str(e));raise
    finally:
        result.update(cpu_s=time.process_time()-cpu,wall_s=time.monotonic()-started,
                      peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      new_spectral_BODY_bytes=ledger['source_body_bytes_received']-initial)
        save(out/'SOURCE_BODY_LEDGER.json',ledger);save(out/'ACQUISITION_RESULT.json',result)
        signal.alarm(0)

if __name__=='__main__':main()
