"""192 first-attempt exact ranges, durable raw sidecars, serial closed H5 writers.

Only source worker threads perform HTTP/file-byte persistence. HDF5 starts after
all 192 standalone bodies are durable and all source threads have exited.
"""
import concurrent.futures
import hashlib
import http.client
import os
from pathlib import Path
import threading
import time
import urllib.request


def acquire(d,root,scope,source,out,started,receipt):
    reader=d.load_module('s2017_adjacent_standard_reader',root/scope['code_paths']['reader'])
    h5py,plugin,np=reader.current_codecs()
    d.require(h5py.version.hdf5_version==scope['hdf5_version'],'HDF5 runtime differs')
    receipt['runtime_versions']={**d.VERSIONS,'HDF5':h5py.version.hdf5_version}
    oldstore=d.load_module('unchanged_corrected_serial_store',root/scope['code_paths']['corrected_serial_store'])
    rawdir=out/'raw_ranges';rawdir.mkdir()
    ledger={'schema':'SETI_S2017_ADJACENT170_172_SOURCE_BODY_LEDGER_V1','requests_attempted':0,'BODY_bytes_received':0,
        'BODY_reserved_upper_bound_bytes':0,'BODY_cap_bytes':d.BODY_CAP,'HTTP_request_cap':192,'complete':False}
    receipt.update(value_read_requests=[],raw_range_records=[],decoded_files=[],decoded_row_progress={},local_pipeline_records=[])
    mutex,stop=threading.RLock(),threading.Event()
    opener=urllib.request.build_opener(reader.NoRedirect())

    def persist():
        d.save(out/'SOURCE_BODY_LEDGER.json',ledger)
        d.save(out/'ACQUISITION_RESULT.json',receipt)

    def durable_raw(native,item,row,raw,sha):
        name='native%d_%s_row%02d.raw.bin'%(native,item['label'],row['time_row'])
        path=rawdir/name;tmp=path.with_suffix(path.suffix+'.tmp')
        with tmp.open('xb') as handle:
            handle.write(raw);handle.flush();os.fsync(handle.fileno())
        tmp.replace(path)
        fd=os.open(rawdir,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        d.require(path.stat().st_size==row['stored_size'] and d.digest(path)==sha,'Durable standalone raw differs')
        record={'native_chunk_index':native,'scan_id':item['label'],'time_row':row['time_row'],
            'path':path.relative_to(out).as_posix(),'stored_size':len(raw),'raw_sha256':sha,'filter_mask':0,
            'original_source_chunk_origin':row['chunk_origin'],'source_range':row['byte_range'],
            'origin':'NEW_PREVIOUSLY_UNATTEMPTED_EXACT_SOURCE_RANGE','fsync_before_HDF5':True}
        with mutex:
            receipt['raw_range_records'].append(record);persist()
        return path.relative_to(out).as_posix()

    persist()

    def fetch(native,item,row):
        size,offset=row['stored_size'],row['byte_offset']
        record={'native_chunk_index':native,'scan_id':item['label'],'time_row':row['time_row'],'attempt':1,
            'request_url':item['url'],'request_range':row['byte_range'],'expected_etag':item['etag'],
            'source_file_bytes':item['source_file_bytes'],'body_bytes_received':0,'status':'ADMITTED_PREVIOUSLY_UNATTEMPTED_RANGE',
            'request_headers':{'Range':row['byte_range'],'If-Match':item['etag'],'Accept-Encoding':'identity',
                'User-Agent':'SETI-S2017-fixed-adjacent170-172-once/1'}}
        with mutex:
            d.require(not stop.is_set() and ledger['requests_attempted']<192
                and ledger['BODY_reserved_upper_bound_bytes']+size+1<=d.BODY_CAP,'Stopped or frozen admission exhausted')
            ledger['requests_attempted']+=1;ledger['BODY_reserved_upper_bound_bytes']+=size+1
            receipt['value_read_requests'].append(record);persist()
        parts=[];wall=time.monotonic()
        try:
            remaining=d.WALL_CAP-(time.monotonic()-started)
            d.require(remaining>0,'Acquisition wall limit before request')
            request=urllib.request.Request(item['url'],headers=record['request_headers'])
            with opener.open(request,timeout=min(60,remaining)) as response:
                with mutex:
                    record.update(http_status=response.status,response_url=response.geturl(),
                        response_headers={key:response.headers.get(key) for key in
                            ('ETag','Content-Range','Content-Length','Content-Encoding','Last-Modified')})
                d.require(response.status==206 and response.geturl()==item['url']
                    and response.headers.get('ETag')==item['etag']
                    and response.headers.get('Content-Range')==f'bytes {offset}-{offset+size-1}/{item["source_file_bytes"]}'
                    and response.headers.get('Content-Length')==str(size)
                    and response.headers.get('Content-Encoding','identity').lower()=='identity',
                    'Exact frozen source URL/206/ETag/range/length/encoding required before body')
                while record['body_bytes_received']<=size:
                    d.require(time.monotonic()-started<d.WALL_CAP,'Acquisition wall cap while receiving')
                    try:part=response.read(min(65536,size+1-record['body_bytes_received']))
                    except http.client.IncompleteRead as error:
                        with mutex:
                            record['body_bytes_received']+=len(error.partial);ledger['BODY_bytes_received']+=len(error.partial)
                        raise
                    if not part:break
                    parts.append(part)
                    with mutex:
                        record['body_bytes_received']+=len(part);ledger['BODY_bytes_received']+=len(part)
                d.require(record['body_bytes_received']==size,'Incomplete or overlong exact range; no retry')
            raw=b''.join(parts);sha=hashlib.sha256(raw).hexdigest()
            with mutex:record.update(status='PASS_EXACT_SOURCE_RANGE',raw_sha256=sha)
            rawpath=durable_raw(native,item,row,raw,sha)
            with mutex:record.update(standalone_raw_path=rawpath,standalone_raw_fsynced=True)
            print('ADJACENT_RAW_DURABLE',native,item['label'],row['time_row'],flush=True)
        except BaseException as error:
            stop.set()
            with mutex:record.update(status='FAILED_CLOSED_NO_RETRY',error_type=type(error).__name__,error=str(error))
            raise
        finally:
            with mutex:record['wall_s']=time.monotonic()-wall;persist()

    def source_worker(label):
        for native in d.NATIVES:
            item=next(item for item in source['by_native_chunk'][str(native)]['sources'] if item['label']==label)
            for row in item['chunks']:fetch(native,item,row)

    errors=[]
    executor=concurrent.futures.ThreadPoolExecutor(max_workers=d.SOURCE_WORKERS)
    futures=[executor.submit(source_worker,label) for label in d.SCANS]
    try:
        for future in concurrent.futures.as_completed(futures):
            try:future.result()
            except BaseException as error:errors.append(error);stop.set()
    finally:
        stop.set();executor.shutdown(wait=True,cancel_futures=True)
        with mutex:
            receipt['source_worker_errors']=[{'error_type':type(error).__name__,'error':str(error)} for error in errors];persist()
    if errors:raise errors[0]
    d.require(len(receipt['raw_range_records'])==192 and ledger['requests_attempted']==192
        and ledger['BODY_bytes_received']==scope['exact_expected_payload_BODY_bytes']
        and ledger['BODY_reserved_upper_bound_bytes']==scope['reserved_payload_BODY_upper_bound_bytes'],
        'Exactly192 durable source bodies and exact accounting required before assembly')
    ordering=lambda r:(d.NATIVES.index(r['native_chunk_index']),d.SCANS.index(r['scan_id']),r['time_row'])
    receipt['raw_range_records'].sort(key=ordering);receipt['value_read_requests'].sort(key=ordering);persist()
    rawmap={(r['native_chunk_index'],r['scan_id'],r['time_row']):r for r in receipt['raw_range_records']}
    # The exact corrected storage helper is unchanged. One independent reader
    # module and immutable frame binding per native prevents cross-frame state.
    for native in d.NATIVES:
        frame=d.load_module('s2017_native%d_compact_reader'%native,root/scope['code_paths']['reader'])
        frame.PHYSICAL_INTERVAL=(native*d.COUNT,(native+1)*d.COUNT)
        raw_by_row={(label,row):r for (n,label,row),r in rawmap.items() if n==native}
        for item in source['by_native_chunk'][str(native)]['sources']:
            path=out/('native%d_%s.compact.h5'%(native,item['label']))
            pipeline=oldstore.write_compact(d,frame,h5py,plugin,item,path,raw_by_row,out)
            receipt['local_pipeline_records'].append({'native_chunk_index':native,'scan_id':item['label'],**pipeline});persist()
            print('ADJACENT_SERIAL_WRITER_CLOSED',native,item['label'],flush=True)
    # All12 writer handles are closed before any raw roundtrip or value decode.
    for native in d.NATIVES:
        for item in source['by_native_chunk'][str(native)]['sources']:
            label=item['label'];path=out/('native%d_%s.compact.h5'%(native,label));decoded=[]
            receipt['decoded_row_progress']['native%d_%s'%(native,label)]=decoded
            with h5py.File(path,'r',rdcc_nbytes=0) as handle:
                data=handle['data']
                d.require(data.shape==(16,1,d.COUNT) and data.dtype.str=='<f4'
                    and int(data.attrs['original_source_frequency_chunk_origin'])==native*d.COUNT
                    and data.attrs['original_source_url']==item['url'] and data.attrs['original_source_etag']==item['etag'],
                    'Serial compact geometry and source identity differs')
                for row in item['chunks']:
                    index=row['time_row'];record=rawmap[(native,label,index)]
                    mask,raw=data.id.read_direct_chunk((index,0,0))
                    d.require(mask==0 and len(raw)==row['stored_size'] and hashlib.sha256(raw).hexdigest()==record['raw_sha256'],
                        'Compact raw roundtrip differs')
                    record['compact_raw_roundtrip_sha256']=record['raw_sha256']
                    values=data[index,0,:]
                    d.require(values.shape==(d.COUNT,) and values.dtype.str=='<f4'
                        and np.isfinite(values).all() and (values>=0).all(),'Invalid full-native decoded power row')
                    decoded.append({'time_row':index,'decoded_bytes':values.nbytes,
                        'decoded_sha256':hashlib.sha256(values.tobytes(order='C')).hexdigest()});persist()
            receipt['decoded_files'].append({'native_chunk_index':native,'scan_id':label,'array_file':path.name,
                'bytes':path.stat().st_size,'file_sha256':d.digest(path),'shape':[16,1,d.COUNT],
                'source_channel0':native*d.COUNT,'decoded_rows':decoded});persist()
            print('ADJACENT_SERIAL_COMPACT_COMPLETE',native,label,flush=True)
    d.require(len(receipt['decoded_files'])==12 and sum(len(x) for x in receipt['decoded_row_progress'].values())==192,
        'All12 complete compact files and192 decoded rows required')
    return {'new_telescope_HTTP_requests':192,'new_telescope_BODY_bytes':ledger['BODY_bytes_received'],
        'reserved_BODY_upper_bound_bytes':ledger['BODY_reserved_upper_bound_bytes'],'source_range_count_authenticated':192,
        'complete_compact_files':12,'decoded_row_SHA256s':192,'standalone_durable_raw_range_files':192,'repeated_source_GETs':0,
        'source_workers_max':d.SOURCE_WORKERS,'HDF5_assembly_threads':1,'write_decode_interleaving':False,
        'all12_writers_closed_before_any_value_decode':True,'whole_original_telescope_MD5_verified':False}
