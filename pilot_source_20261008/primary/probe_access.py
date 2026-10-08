#!/usr/bin/env python3
"""One bounded HEAD + HDF5-superblock metadata range per exact primary source.

No spectral payload request, dataset read, retry or alternative source exists.
"""
from pathlib import Path
import concurrent.futures, datetime, hashlib, json, time, urllib.request

P=Path(__file__).resolve().parent
cfg=json.loads((P/'historical_source_preparation.json').read_text())

def request(scan,method,headers=None):
    start=time.monotonic()
    out={'url':scan['url'],'method':method,'request_headers':headers or {},'body_bytes_observed':0,
         'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'attempt':1}
    try:
        req=urllib.request.Request(scan['url'],method=method,headers={'Accept-Encoding':'identity','User-Agent':'setisearch-primary-metadata-20261008',**(headers or {})})
        with urllib.request.urlopen(req,timeout=15) as r:
            out.update(status=r.status,response_headers=dict(r.headers),final_url=r.geturl())
            if r.geturl()!=scan['url']:
                raise ValueError('Unexpected redirect; exact source identity required')
            if r.headers.get('ETag')!=scan['expected_etag']:
                raise ValueError('Changed ETag')
            if method=='HEAD':
                if r.status!=200 or int(r.headers['Content-Length'])!=scan['expected_remote_size_bytes']:
                    raise ValueError('HEAD status/size mismatch')
            else:
                expected=f"bytes 0-63/{scan['expected_remote_size_bytes']}"
                if r.status!=206 or r.headers.get('Content-Range')!=expected or int(r.headers['Content-Length'])!=64:
                    raise ValueError('Range not exactly honored; refused without reading body')
                b=r.read(65)
                out['body_bytes_observed']=len(b)
                if len(b)!=64 or b[:8]!=b'\x89HDF\r\n\x1a\n':
                    raise ValueError('Invalid bounded HDF5 superblock')
                out['body_sha256']=hashlib.sha256(b).hexdigest()
                (P/(scan['label']+'_superblock.bin')).write_bytes(b)
            out['state']='PASS'
    except Exception as e:
        out.update(state='FAILED_CLOSED',error_type=type(e).__name__,error=str(e))
    finally:
        out['wall_s']=time.monotonic()-start
        out['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    return out

def one(scan):
    receipts=[request(scan,'HEAD')]
    if receipts[0]['state']=='PASS':
        receipts.append(request(scan,'GET',{'Range':'bytes=0-63','If-Match':scan['expected_etag']}))
    return {'label':scan['label'],'role':scan['role'],'receipts':receipts,
            'status':'PUBLIC_HEAD_AND_METADATA_RANGE_VERIFIED' if len(receipts)==2 and receipts[-1]['state']=='PASS' else 'FAILED_CLOSED'}

start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results=list(pool.map(one,cfg['scans']))
out={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_commit':'b74e13df1c17baa4300657087ea06a5ee095e499',
     'metadata_only':True,'spectral_values_read':False,'source_body_bytes_received':sum(v['body_bytes_observed'] for x in results for v in x['receipts']),
     'requests':sum(len(x['receipts']) for x in results),'wall_s':time.monotonic()-start,'sources':results}
(P/'current_access_receipts.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='sources'}))
for x in results: print(x['label'],x['status'],[y.get('error','') for y in x['receipts'] if y['state']!='PASS'])
