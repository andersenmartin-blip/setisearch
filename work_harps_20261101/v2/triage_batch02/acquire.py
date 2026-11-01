"""Remaining 237 saved V2 events, all fourteen remaining targets; public raw/native follow-up.

Selection is the pre-existing CSV order, not profile strength or morphology.
No search settings or initial dispositions are changed.
"""
from pathlib import Path
import csv,json,hashlib,urllib.request,urllib.parse,time,datetime,threading,concurrent.futures
BASE=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
PROD=OUT/'products';PROD.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
index=list(csv.DictReader((BASE/'v2/review/REVIEW_INDEX.csv').open()))
selected=index[96:];ids=list(dict.fromkeys(r['dp_id'] for r in selected))
assert len(selected)==237 and len(ids)==68 and len(set(r['target'] for r in selected))==14
assert selected[0]['review_id']=='V2-0097' and selected[-1]['review_id']=='V2-0333'
manifest={r['dp_id']:r for r in json.loads((BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json').read_text())}
plan=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),selection='Rows97-333 of frozen review index; all remaining hits of fourteen targets',
    hits=237,spectra=68,raw_products=68,ancillary_products=68,max_transferred_bytes=2200000000,max_file_bytes=30000000,
    metadata_query_timeout_seconds=45,download_timeout_seconds=[20,60],workers=3,
    input_index_sha256=sha(BASE/'v2/review/REVIEW_INDEX.csv'),hits_sha256=sha(BASE/'v2/production/V2_HITS.csv'),
    original_dispositions_sha256=sha(BASE/'v2/production/V2_DISPOSITIONS.csv'),
    interpretation='Post-detection descriptive investigation; no claim of independent blind validation or final origin. All237 remain tracked, including failures.',selected=selected)
planfile=OUT/'PLAN.json'
if planfile.exists():raise RuntimeError('Scope already exists; inspect previous outcome before resuming')
planfile.write_text(json.dumps(plan,indent=2)+'\n')
with (OUT/'SELECTED_HITS.csv').open('w',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=list(selected[0]));wr.writeheader();wr.writerows(selected)
query="SELECT product_id,archive_id,extension,eso_category,original_filename,access_url,access_estsize FROM phase3v2.product_files WHERE product_id IN ("+','.join("'"+i+"'" for i in ids)+')'
url='https://archive.eso.org/tap_obs/sync?'+urllib.parse.urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=query))
(OUT/'ANCILLARY_QUERY.json').write_text(json.dumps(dict(adql=query,url=url),indent=2)+'\n')
with urllib.request.urlopen(url,timeout=45) as f: data=f.read()
(OUT/'ANCILLARY_METADATA.csv').write_bytes(data)
metadata=list(csv.DictReader(data.decode().splitlines()))
jobs=[]
for dp in ids:
    m=manifest[dp];assert len(m['raw_progenitor_ids'])==1
    raw=m['raw_progenitor_ids'][0]
    a=[r for r in metadata if r['product_id']==dp and r['extension']=='TAR'];assert len(a)==1,dp
    jobs.extend([dict(dp_id=dp,kind='RAW',raw_id=raw,url='https://dataportal.eso.org/dataPortal/file/'+raw,filename=raw.replace(':','_')+'.fits.Z'),
                 dict(dp_id=dp,kind='ANCILLARY',raw_id=raw,url=a[0]['access_url'],filename=a[0]['archive_id'].replace(':','_')+'.tar')])
(OUT/'JOBS.json').write_text(json.dumps(jobs,indent=2)+'\n')
total=0;lock=threading.Lock();start=time.monotonic()
def get(job):
    global total
    receipt=dict(**job,attempts=[]);p=PROD/job['filename']
    for timeout in plan['download_timeout_seconds']:
        t=time.monotonic()
        try:
            with urllib.request.urlopen(job['url'],timeout=timeout) as h:
                blocks=[];size=0
                while True:
                    b=h.read(1048576)
                    if not b:break
                    size+=len(b)
                    with lock:
                        total+=len(b)
                        if total>plan['max_transferred_bytes']:raise RuntimeError('Total byte limit')
                    if size>plan['max_file_bytes']:raise RuntimeError('File byte limit')
                    blocks.append(b)
            data=b''.join(blocks);p.write_bytes(data)
            receipt.update(status='DOWNLOADED',bytes=len(data),sha256=sha(p),relative_path=str(p.relative_to(BASE)),magic_hex=data[:8].hex())
            receipt['attempts'].append(dict(timeout=timeout,outcome='SUCCESS',seconds=time.monotonic()-t));break
        except Exception as e:
            receipt['status']='FAILED';receipt['attempts'].append(dict(timeout=timeout,outcome='FAILED',seconds=time.monotonic()-t,error=repr(e)))
    (PROD/(job['filename']+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(dp_id=job['dp_id'],kind=job['kind'],status=receipt['status'])),flush=True)
    return receipt
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(get,jobs))
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),wall_seconds=time.monotonic()-start,total_transferred_bytes=total,products=results)
(PROD/'MANIFEST.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(downloaded=sum(r['status']=='DOWNLOADED' for r in results),total=len(results),bytes=total,seconds=summary['wall_seconds'])),flush=True)
