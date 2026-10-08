#!/usr/bin/env python3
"""HDF5 metadata-only source preflight, using the working local Python runtime.

Uses attrs/shape/chunks/filter description and get_chunk_info_by_coord only.
No dataset slicing, read_direct, read_direct_chunk, decompression or values.
Each exact file is attempted once; no retries or substitution.
"""
from pathlib import Path
import concurrent.futures, datetime, hashlib, io, json, multiprocessing, os, resource, time, urllib.request
import h5py
import numpy as np

P=Path(__file__).resolve().parent
MAX_REQUEST_BYTES=65536
MAX_SOURCE_METADATA_BYTES=1048576
MAX_SOURCE_REQUESTS=64
MAX_SOURCE_WALL_S=600

def native(x):
    if isinstance(x,bytes): return x.decode('utf-8')
    if isinstance(x,np.ndarray): return [native(v) for v in x.tolist()]
    if isinstance(x,np.generic): return native(x.item())
    if isinstance(x,(list,tuple)): return [native(v) for v in x]
    return x

class MetadataRangeReader(io.RawIOBase):
    def __init__(self,scan):
        super().__init__()
        self.scan=scan; self.position=0; self.receipts=[]; self.received=0; self.started=time.monotonic()
        self.cache=[(0,(P/(scan['label']+'_superblock.bin')).read_bytes())]
        self.directory=P/'metadata_ranges'/scan['label']; self.directory.mkdir(parents=True,exist_ok=False)
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self,offset,whence=0):
        if whence==0: position=offset
        elif whence==1: position=self.position+offset
        elif whence==2: position=self.scan['expected_remote_size_bytes']+offset
        else: raise ValueError('Invalid seek mode')
        if not 0<=position<=self.scan['expected_remote_size_bytes']: raise ValueError('Seek outside exact source')
        self.position=position
        return position
    def readinto(self,b):
        data=self.read(len(b)); b[:len(data)]=data; return len(data)
    def read(self,n=-1):
        if n==0: return b''
        if not 0<n<=MAX_REQUEST_BYTES: raise ValueError('Unbounded or oversized metadata read refused')
        start=self.position; stop=start+n
        if stop>self.scan['expected_remote_size_bytes']: raise ValueError('Metadata read exceeds exact source')
        for lo,data in self.cache:
            if lo<=start and stop<=lo+len(data):
                self.position=stop
                return data[start-lo:stop-lo]
        if len(self.receipts)>=MAX_SOURCE_REQUESTS or self.received+n>MAX_SOURCE_METADATA_BYTES or time.monotonic()-self.started>MAX_SOURCE_WALL_S:
            raise ValueError('Metadata-only request/byte/wall budget exhausted')
        receipt={'offset':start,'requested_bytes':n,'range':f'bytes={start}-{stop-1}','state':'RESERVED',
                 'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'body_bytes_observed':0}
        self.receipts.append(receipt)
        (self.directory/'receipts.json').write_text(json.dumps(self.receipts,indent=2)+'\n')
        ts=time.monotonic()
        try:
            req=urllib.request.Request(self.scan['url'],headers={'Range':receipt['range'],'If-Match':self.scan['expected_etag'],'Accept-Encoding':'identity','User-Agent':'setisearch-primary-hdf5-metadata-20261008'})
            with urllib.request.urlopen(req,timeout=15) as response:
                receipt.update(status=response.status,response_headers=dict(response.headers),final_url=response.geturl())
                expected=f"bytes {start}-{stop-1}/{self.scan['expected_remote_size_bytes']}"
                if response.status!=206 or response.geturl()!=self.scan['url'] or response.headers.get('Content-Range')!=expected or response.headers.get('ETag')!=self.scan['expected_etag'] or int(response.headers['Content-Length'])!=n:
                    raise ValueError('Exact range/ETag/size not honored; body refused without draining')
                data=response.read(n+1)
                receipt['body_bytes_observed']=len(data); self.received+=len(data)
                if len(data)!=n: raise ValueError('Short or excessive metadata body')
                receipt['body_sha256']=hashlib.sha256(data).hexdigest()
                filename=f'{start:012d}_{n:06d}.bin'; (self.directory/filename).write_bytes(data)
                receipt['retained_file']=filename; receipt['state']='PASS'
                self.cache.append((start,data)); self.position=stop
                return data
        except Exception as e:
            receipt.update(state='FAILED_CLOSED',error_type=type(e).__name__,error=str(e))
            raise
        finally:
            receipt.update(wall_s=time.monotonic()-ts,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            (self.directory/'receipts.json').write_text(json.dumps(self.receipts,indent=2)+'\n')

def inspect(scan):
    begin=time.monotonic(); cpu=time.process_time(); reader=None
    result={'label':scan['label'],'role':scan['role'],'url':scan['url'],'spectral_values_read':False,
            'metadata_operations':['attrs','shape','dtype','chunks','get_create_plist filters','get_chunk_info_by_coord'],
            'status':'FAILED_CLOSED','h5py_version':h5py.__version__,'hdf5_version':h5py.version.hdf5_version}
    try:
        reader=MetadataRangeReader(scan)
        with reader:
            with h5py.File(reader,'r',driver='fileobj',rdcc_nbytes=0) as f:
                d=f['data']
                result['current_header']={'root_attributes':{k:native(v) for k,v in f.attrs.items()},'data_attributes':{k:native(v) for k,v in d.attrs.items()},'dataset_shape':list(d.shape),'dataset_dtype':str(d.dtype),'dataset_chunks':list(d.chunks)}
                pl=d.id.get_create_plist()
                result['current_header']['hdf5_filters']=[native(pl.get_filter(i)) for i in range(pl.get_nfilters())]
                h=scan['expected_header']; a=result['current_header']['data_attributes']
                exact=(list(d.shape)==h['dataset_shape'] and str(d.dtype)==h['dataset_dtype'] and list(d.chunks)==scan['expected_chunks'] and all(a[k]==h[j] for k,j in [('fch1','fch1_mhz'),('foff','foff_mhz'),('tsamp','tsamp_s'),('tstart','tstart_mjd'),('source_name','source_name'),('src_raj','src_raj_hours'),('src_dej','src_dej_deg')]))
                if not exact: raise ValueError('Current header no longer matches pinned historical source identity')
                if result['current_header']['hdf5_filters']!=scan['observed_hdf5_filters']: raise ValueError('Current HDF5 filter declaration changed')
                chunks=[]
                for t in range(h['dataset_shape'][0]):
                    coord=(t,0,152*1048576)
                    info=d.id.get_chunk_info_by_coord(coord)
                    entry={'time_row':t,'chunk_origin':list(coord),'chunk_offset':native(info.chunk_offset),'filter_mask':int(info.filter_mask),'byte_offset':info.byte_offset,'stored_size':int(info.size),'decoded_size':4194304}
                    if info.byte_offset is None or info.size<=0: raise ValueError('Missing required complete time-row chunk')
                    if info.byte_offset+info.size>scan['expected_remote_size_bytes']: raise ValueError('Chunk interval outside file')
                    chunks.append(entry)
                result.update(status='METADATA_AND_ALL_REQUIRED_CHUNK_LOCATIONS_VERIFIED',chunks=chunks,
                              compressed_payload_bytes_for_all_rows=sum(x['stored_size'] for x in chunks),
                              decoded_chunk_bytes_all_rows=16*4194304)
    except Exception as e:
        result.update(error_type=type(e).__name__,error=str(e))
    finally:
        result.update(metadata_source_body_bytes=reader.received if reader else 0,metadata_requests=len(reader.receipts) if reader else 0,
                      wall_s=time.monotonic()-begin,cpu_s=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        (P/(scan['label']+'_chunk_metadata.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    c=json.loads((P/'historical_source_preparation.json').read_text()); access=json.loads((P/'current_access_receipts.json').read_text())
    if any(x['status']!='PUBLIC_HEAD_AND_METADATA_RANGE_VERIFIED' for x in access['sources']): raise ValueError('Current access failed; metadata route refused')
    freeze={'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metadata_only':True,'pilot_values_read':False,
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'h5py':h5py.__version__,'hdf5':h5py.version.hdf5_version,
            'max_source_metadata_body_bytes':MAX_SOURCE_METADATA_BYTES,'max_source_requests':MAX_SOURCE_REQUESTS,
            'max_single_metadata_request_bytes':MAX_REQUEST_BYTES,'max_source_wall_s':MAX_SOURCE_WALL_S,'no_retries':True,'chunk_index':152}
    (P/'chunk_metadata_preflight_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
    start=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=6,mp_context=multiprocessing.get_context('spawn')) as pool:
        results=list(pool.map(inspect,c['scans']))
    out={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'metadata_only':True,'spectral_values_read':False,
         'wall_s':time.monotonic()-start,'metadata_source_body_bytes':sum(x['metadata_source_body_bytes'] for x in results),
         'metadata_requests':sum(x['metadata_requests'] for x in results),'sources':results}
    if all(x['status']=='METADATA_AND_ALL_REQUIRED_CHUNK_LOCATIONS_VERIFIED' for x in results):
        out['compressed_payload_bytes_required']=sum(x['compressed_payload_bytes_for_all_rows'] for x in results)
        out['decoded_chunk_bytes_required']=sum(x['decoded_chunk_bytes_all_rows'] for x in results)
    (P/'current_chunk_metadata.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='sources'}))
    for x in results: print(x['label'],x['status'],x.get('error',''),x.get('compressed_payload_bytes_for_all_rows'))

if __name__=='__main__': main()
