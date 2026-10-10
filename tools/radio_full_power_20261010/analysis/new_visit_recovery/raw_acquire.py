"""Durable raw ranges first, then one serial write/close/read-only decode pass.

Twenty-seven authenticated old ranges are copied locally. Only the sixty-nine
unattempted source ranges may be requested; no HTTP retry is implemented.
"""
import concurrent.futures
import hashlib
import http.client
import os
from pathlib import Path
import threading
import time
import urllib.request


def write_compact(d, reader, h5py, plugin, item, path, raw_by_row, raw_root):
    """Serial raw-only write pass; close the writer before returning."""
    with h5py.File(path,'x',rdcc_nbytes=0) as handle:
        data,pipeline=reader.create_compact_dataset(handle,item,h5py,plugin)
        for row in item['chunks']:
            record=raw_by_row[(item['label'],row['time_row'])]
            raw=(raw_root/record['path']).read_bytes()
            d.require(len(raw) == row['stored_size'] and hashlib.sha256(raw).hexdigest() == record['raw_sha256'],
                      'Standalone exact source bytes changed before serial assembly')
            data.id.write_direct_chunk((row['time_row'],0,0),raw,filter_mask=0)
        handle.flush()
    return pipeline


def acquire(d, root, scope, source, out, started, receipt):
    reader = d.load_module('s2017_recovery_standard_reader', root/scope['code_paths']['reader'])
    reader.PHYSICAL_INTERVAL = (d.C0, d.C0+d.COUNT)
    h5py, plugin, np = reader.current_codecs()
    d.require(h5py.version.hdf5_version == scope['hdf5_version'], 'HDF5 version differs')
    receipt['runtime_versions'] = {**d.VERSIONS, 'HDF5': h5py.version.hdf5_version}
    import json
    original = json.loads((root/scope['original_acquisition_receipt']).read_bytes())
    inventory = json.loads((root/scope['retained_raw_inventory']).read_bytes())
    d.require(original['status'] == 'INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY'
              and inventory['total_retained_received_chunks'] == 27 and inventory['received_chunks_lost'] == 0,
              'Original failure and exact retained27 inventory must remain unchanged')
    oldrequests = {(record['scan_id'], record['time_row']): record for record in original['value_read_requests']}
    d.require(len(oldrequests) == 27 and all(record['status'] == 'PASS_EXACT_SOURCE_RANGE'
              for record in oldrequests.values()), 'Exactly27 received original ranges required')
    rawdir = out/'raw_ranges'
    rawdir.mkdir()
    ledger = {'new_requests_attempted': 0, 'new_BODY_bytes_received': 0,
        'new_BODY_reserved_upper_bound_bytes': 0, 'original_requests_attempted': 27,
        'original_BODY_bytes_received': 83845205, 'original_BODY_reserved_upper_bound_bytes': 83845232,
        'cumulative_requests_attempted': 27, 'cumulative_BODY_bytes_received': 83845205,
        'cumulative_BODY_reserved_upper_bound_bytes': 83845232,
        'BODY_cap_bytes': d.BODY_CAP, 'complete': False}
    receipt.update(value_read_requests=[], raw_range_records=[], decoded_files=[],
                   decoded_row_progress={}, local_pipeline_records=[])
    mutex, stop = threading.RLock(), threading.Event()
    opener = urllib.request.build_opener(reader.NoRedirect())

    def persist():
        d.save(out/'SOURCE_BODY_LEDGER.json', ledger)
        d.save(out/'ACQUISITION_RESULT.json', receipt)

    def durable_raw(label, row, raw, expected_sha, origin):
        d.require(hashlib.sha256(raw).hexdigest() == expected_sha, 'Raw source SHA differs before durable copy')
        path = rawdir/(label+'_row%02d.raw.bin' % row['time_row'])
        temporary = path.with_suffix(path.suffix+'.tmp')
        with temporary.open('xb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        fd = os.open(rawdir, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        d.require(path.stat().st_size == row['stored_size'] and d.digest(path) == expected_sha,
                  'Durable standalone raw range differs')
        record = {'scan_id':label, 'time_row':row['time_row'], 'path':path.relative_to(out).as_posix(),
            'stored_size':len(raw), 'raw_sha256':expected_sha, 'filter_mask':0,
            'original_source_chunk_origin':row['chunk_origin'], 'source_range':row['byte_range'],
            'origin':origin, 'fsync_before_HDF5':True}
        with mutex:
            receipt['raw_range_records'].append(record)
            persist()

    persist()
    oldstage = root/scope['original_acquisition_directory']
    reused = set()
    for entry in inventory['records']:
        label = entry['scan_id']
        identity = next(item for item in source['sources'] if item['label'] == label)
        path = oldstage/(label+'.compact.h5')
        d.require(path.stat().st_size == entry['file_bytes'] and d.digest(path) == entry['file_sha256'],
                  'Original retained partial file pin differs')
        with h5py.File(path,'r',rdcc_nbytes=0) as handle:
            data = handle['data']
            d.require(data.attrs['original_source_url'] == identity['url']
                      and data.attrs['original_source_etag'] == identity['etag']
                      and int(data.attrs['original_source_frequency_chunk_origin']) == d.C0,
                      'Original partial source identity differs')
            for oldrow in entry['allocated_rows']:
                index = oldrow['row']
                row = identity['chunks'][index]
                mask, raw = data.id.read_direct_chunk((index,0,0))
                request = oldrequests[(label,index)]
                d.require(mask == 0 and len(raw) == row['stored_size']
                          and hashlib.sha256(raw).hexdigest() == oldrow['raw_sha256'] == request['raw_sha256'],
                          'Original indexed raw source row differs')
                durable_raw(label,row,raw,request['raw_sha256'],'REUSED_ORIGINAL_INDEXED_COMPACT_SOURCE_BYTES_NO_HTTP')
                reused.add((label,index))
    for suffix in inventory['unindexed_matching_source_bytes']:
        label, index = suffix['scan_id'], suffix['row']
        row = next(item for item in source['sources'] if item['label'] == label)['chunks'][index]
        path = oldstage/(label+'.compact.h5')
        with path.open('rb') as handle:
            handle.seek(suffix['local_raw_byte_offset'])
            raw = handle.read(suffix['stored_size'])
        request = oldrequests[(label,index)]
        d.require(len(raw) == row['stored_size'] and hashlib.sha256(raw).hexdigest()
                  == suffix['raw_sha256'] == request['raw_sha256'], 'Original unindexed received source bytes differ')
        durable_raw(label,row,raw,request['raw_sha256'],'REUSED_ORIGINAL_UNINDEXED_EXACT_SOURCE_SUFFIX_NO_HTTP')
        reused.add((label,index))
    d.require(reused == set(oldrequests) and len(reused) == 27, 'Exactly all27 old ranges must be reused')

    def fetch(item, row):
        label, index = item['label'], row['time_row']
        size, offset = row['stored_size'], row['byte_offset']
        d.require((label,index) not in oldrequests, 'Any original attempted GET is forbidden')
        record = {'scan_id':label,'time_row':index,'attempt':1,'request_range':row['byte_range'],
            'expected_etag':item['etag'],'body_bytes_received':0,'status':'ADMITTED_PREVIOUSLY_UNATTEMPTED_RANGE',
            'request_headers':{'Range':row['byte_range'],'If-Match':item['etag'],
                'Accept-Encoding':'identity','User-Agent':'SETI-S2017-retained27-unattempted69-once/1'}}
        with mutex:
            d.require(not stop.is_set() and ledger['new_requests_attempted'] < 69
                and ledger['cumulative_BODY_reserved_upper_bound_bytes']+size+1 <= d.BODY_CAP,
                'New request stopped or cumulative frozen budget exhausted')
            ledger['new_requests_attempted'] += 1
            ledger['cumulative_requests_attempted'] += 1
            ledger['new_BODY_reserved_upper_bound_bytes'] += size+1
            ledger['cumulative_BODY_reserved_upper_bound_bytes'] += size+1
            receipt['value_read_requests'].append(record)
            persist()
        parts, wall = [], time.monotonic()
        try:
            remaining = d.WALL_CAP-(time.monotonic()-started)
            d.require(remaining > 0, 'Recovery wall cap reached before request')
            request = urllib.request.Request(item['url'],headers=record['request_headers'])
            with opener.open(request,timeout=min(60,remaining)) as response:
                with mutex:
                    record.update(http_status=response.status,response_url=response.geturl(),
                        response_headers={key:response.headers.get(key) for key in
                            ('ETag','Content-Range','Content-Length','Content-Encoding','Last-Modified')})
                d.require(response.status == 206 and response.geturl() == item['url']
                    and response.headers.get('ETag') == item['etag']
                    and response.headers.get('Content-Range') == f'bytes {offset}-{offset+size-1}/{item["source_file_bytes"]}'
                    and response.headers.get('Content-Length') == str(size)
                    and response.headers.get('Content-Encoding','identity').lower() == 'identity',
                    'Exact frozen source URL/206/ETag/range/length/encoding required')
                while record['body_bytes_received'] <= size:
                    d.require(time.monotonic()-started < d.WALL_CAP, 'Recovery wall cap reached while receiving')
                    try:
                        part = response.read(min(65536,size+1-record['body_bytes_received']))
                    except http.client.IncompleteRead as error:
                        with mutex:
                            record['body_bytes_received'] += len(error.partial)
                            ledger['new_BODY_bytes_received'] += len(error.partial)
                            ledger['cumulative_BODY_bytes_received'] += len(error.partial)
                        raise
                    if not part:
                        break
                    parts.append(part)
                    with mutex:
                        record['body_bytes_received'] += len(part)
                        ledger['new_BODY_bytes_received'] += len(part)
                        ledger['cumulative_BODY_bytes_received'] += len(part)
                d.require(record['body_bytes_received'] == size, 'Incomplete or overlong range; no retry')
            raw = b''.join(parts)
            sha = hashlib.sha256(raw).hexdigest()
            with mutex:
                record.update(status='PASS_EXACT_SOURCE_RANGE',raw_sha256=sha)
            durable_raw(label,row,raw,sha,'NEW_PREVIOUSLY_UNATTEMPTED_EXACT_SOURCE_RANGE')
            with mutex:
                record['standalone_raw_path'] = 'raw_ranges/'+label+'_row%02d.raw.bin' % index
                record['standalone_raw_fsynced'] = True
            print('RECOVERY_RAW_RANGE_DURABLE',label,index,flush=True)
        except BaseException as error:
            stop.set()
            with mutex:
                record.update(status='FAILED_CLOSED_NO_RETRY',error_type=type(error).__name__,error=str(error))
            raise
        finally:
            with mutex:
                record['wall_s'] = time.monotonic()-wall
                persist()

    def network_worker(item):
        for row in item['chunks']:
            if (item['label'],row['time_row']) not in reused:
                fetch(item,row)

    errors=[]
    executor=concurrent.futures.ThreadPoolExecutor(max_workers=6)
    futures=[executor.submit(network_worker,item) for item in source['sources']]
    try:
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except BaseException as error:
                errors.append(error)
                stop.set()
    finally:
        stop.set()
        executor.shutdown(wait=True,cancel_futures=True)
        with mutex:
            receipt['source_worker_errors']=[{'error_type':type(error).__name__,'error':str(error)} for error in errors]
            persist()
    if errors:
        raise errors[0]
    d.require(len(receipt['raw_range_records']) == 96 and ledger['new_requests_attempted'] == 69
        and ledger['new_BODY_bytes_received'] == scope['exact_remaining_payload_BODY_bytes']
        and ledger['new_BODY_reserved_upper_bound_bytes'] == scope['remaining_reserved_BODY_upper_bound_bytes']
        and ledger['cumulative_BODY_bytes_received'] == scope['exact_expected_payload_BODY_bytes']
        and ledger['cumulative_BODY_reserved_upper_bound_bytes'] == scope['reserved_payload_BODY_upper_bound_bytes'],
        'All96 durable source ranges and exact cumulative accounting required before HDF5 assembly')
    receipt['raw_range_records'].sort(key=lambda record:(d.SCANS.index(record['scan_id']),record['time_row']))
    receipt['value_read_requests'].sort(key=lambda record:(d.SCANS.index(record['scan_id']),record['time_row']))
    persist()
    raw_by_row={(record['scan_id'],record['time_row']):record for record in receipt['raw_range_records']}
    previous_decoded={(label,row['time_row']):row['decoded_sha256']
        for label,rows in original['decoded_row_progress'].items() for row in rows}
    # All six serial writers are closed before any raw-roundtrip or decoded
    # dataset read. HTTP workers have already exited, and all96 rawbins exist.
    for item in source['sources']:
        label,path=item['label'],out/(item['label']+'.compact.h5')
        pipeline=write_compact(d,reader,h5py,plugin,item,path,raw_by_row,out)
        receipt['local_pipeline_records'].append({'scan_id':label,**pipeline})
        persist()
        print('RECOVERY_SERIAL_WRITER_CLOSED',label,flush=True)
    for item in source['sources']:
        label,path=item['label'],out/(item['label']+'.compact.h5')
        decoded=[]
        receipt['decoded_row_progress'][label]=decoded
        with h5py.File(path,'r',rdcc_nbytes=0) as handle:
            data=handle['data']
            for row in item['chunks']:
                index=row['time_row'];record=raw_by_row[(label,index)]
                mask,raw=data.id.read_direct_chunk((index,0,0))
                d.require(mask == 0 and len(raw) == row['stored_size']
                    and hashlib.sha256(raw).hexdigest() == record['raw_sha256'], 'Serial compact raw roundtrip differs')
                record['compact_raw_roundtrip_sha256']=record['raw_sha256']
                values=data[index,0,:]
                d.require(values.shape == (d.COUNT,) and values.dtype.str == '<f4'
                    and np.isfinite(values).all() and (values >= 0).all(),'Invalid complete serial decoded power row')
                sha=hashlib.sha256(values.tobytes(order='C')).hexdigest()
                if (label,index) in previous_decoded:
                    d.require(sha == previous_decoded[(label,index)],'Previously authenticated decoded row differs')
                decoded.append({'time_row':index,'decoded_bytes':values.nbytes,'decoded_sha256':sha})
                persist()
        receipt['decoded_files'].append({'scan_id':label,'array_file':path.name,'bytes':path.stat().st_size,
            'file_sha256':d.digest(path),'shape':[16,1,d.COUNT],'source_channel0':d.C0,'decoded_rows':decoded})
        persist()
        print('RECOVERY_SERIAL_COMPACT_COMPLETE',label,flush=True)
    d.require(len(receipt['decoded_files']) == 6 and sum(len(rows) for rows in receipt['decoded_row_progress'].values()) == 96,
              'Six complete corrected compact files and96 decoded rows required')
    return {'new_telescope_HTTP_requests':69,'new_telescope_BODY_bytes':ledger['new_BODY_bytes_received'],
        'total_cumulative_telescope_HTTP_requests':96,'cumulative_telescope_BODY_bytes':ledger['cumulative_BODY_bytes_received'],
        'cumulative_reserved_BODY_upper_bound_bytes':ledger['cumulative_BODY_reserved_upper_bound_bytes'],
        'source_range_count_authenticated':96,'reused_original_source_ranges':27,'repeated_source_GETs':0,
        'complete_compact_files':6,'decoded_row_SHA256s':96,'standalone_durable_raw_range_files':96,
        'whole_original_telescope_MD5_verified':False,'source_workers_max':6,
        'HDF5_assembly_threads':1,'write_decode_interleaving':False,
        'previous26_decoded_row_SHA256s_match':True}
