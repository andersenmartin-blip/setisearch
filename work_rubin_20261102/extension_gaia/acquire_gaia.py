"""One bounded public Gaia DR3 metadata cone, with one transient retry."""
from pathlib import Path
import csv, datetime, hashlib, io, json, math, socket
import urllib.request, urllib.parse, urllib.error
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dump(name,value):(OUT/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def main():
    plan=json.loads((OUT/'PLAN.json').read_text())
    assert sha(__file__)==plan['acquire_script_sha256']
    assert sha(OUT/'match_gaia.py')==plan['match_script_sha256']
    for entry in plan['input_files']:assert sha(ROOT/entry['path'])==entry['sha256'],entry['path']
    review=json.loads((OUT/'independent_review/PREFLIGHT.json').read_text())
    assert review['status'].startswith('PASS')
    assert review['plan_sha256']==sha(OUT/'PLAN.json')
    assert review['acquire_script_sha256']==sha(__file__)
    assert review['match_script_sha256']==sha(OUT/'match_gaia.py')
    assert not (OUT/'ACQUISITION_STARTED.json').exists()
    dump('ACQUISITION_STARTED.json',{'utc':now(),'plan_sha256':sha(OUT/'PLAN.json')})
    query=(OUT/'QUERY.adql').read_text().strip()
    assert hashlib.sha256(query.encode()).hexdigest()==plan['gaia_query']['query_sha256']
    payload=urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','MAXREC':'50000','QUERY':query}).encode()
    receipts=[]
    for attempt in range(1,3):
        rec={'attempt':attempt,'started_utc':now(),'url':plan['gaia_query']['url'],'method':'POST',
             'query_sha256':hashlib.sha256(query.encode()).hexdigest(),'timeout_seconds':45,
             'payload':payload.decode(),'response_byte_cap':8000000}
        body=b'';chunks=[];unknown=False;retry=False;error=None;status=None;count=None
        try:
            req=urllib.request.Request(rec['url'],data=payload,headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'SETI-bounded-Gaia-metadata-extension'})
            try:response=urllib.request.build_opener(NoRedirect()).open(req,timeout=45)
            except urllib.error.HTTPError as exc:response=exc
            with response:
                status=response.status;rec['headers']=dict(response.headers)
                if int(response.headers.get('Content-Length','0'))>=8000000:raise ValueError('Declared bytecap reached; terminal truncation stop')
                n=0
                while n<8000000:
                    block=response.read(min(65536,8000000-n))
                    if not block:break
                    chunks.append(block);n+=len(block)
                body=b''.join(chunks)
                if len(body)>=8000000:raise ValueError('Body bytecap reached; terminal truncation stop')
            if status!=200:
                error='HTTP'+str(status);retry=status in[500,502,503,504]
            else:
                reader=csv.DictReader(io.StringIO(body.decode('utf-8')))
                if reader.fieldnames!=plan['gaia_query']['columns']:raise ValueError('Unexpected CSV columns')
                rows=list(reader);count=len(rows)
                if not 1<count<50000:raise ValueError('Empty/insufficient or rowcap response; terminal stop')
                if len({row['source_id']for row in rows})!=count:raise ValueError('Duplicate Gaia IDs')
                for row in rows:
                    if not row['source_id'].isdigit()or not 0<int(row['source_id'])<2**63:raise ValueError('Invalid exact source ID')
                    ra=float(row['ra']);dec=float(row['dec'])
                    if not math.isfinite(ra)or not math.isfinite(dec)or not 0<=ra<360 or not -90<=dec<=90:raise ValueError('Invalid Gaia coordinate')
                    ar,dr=map(math.radians,plan['gaia_query']['center_deg']);a=math.radians(ra);d=math.radians(dec)
                    h=math.sin((d-dr)/2)**2+math.cos(d)*math.cos(dr)*math.sin((a-ar)/2)**2
                    sep=math.degrees(2*math.asin(math.sqrt(min(1,max(0,h)))))*3600
                    if sep>3960.001:raise ValueError('Gaia outside frozen1.1degree field')
        except urllib.error.URLError as exc:
            error=repr(exc);unknown=True;retry=isinstance(exc.reason,(TimeoutError,socket.timeout,ConnectionResetError,ConnectionAbortedError,BrokenPipeError))
        except(TimeoutError,socket.timeout,ConnectionResetError,ConnectionAbortedError,BrokenPipeError)as exc:
            error=repr(exc);unknown=True;retry=True
        except Exception as exc:
            error=repr(exc);unknown=True;retry=False
        if chunks:body=b''.join(chunks)
        rec.update(http_status=status,error=error,status='SUCCESS'if error is None and status==200 else'FAILED',
                   response_bytes_saved=len(body),sha256=hashlib.sha256(body).hexdigest(),
                   unknown_remaining_bytes=unknown,charged_bytes=8000000 if unknown else len(body),catalog_rows=count)
        path=OUT/f'ATTEMPT_{attempt:02}.body';path.write_bytes(body);rec['path']=path.name
        receipts.append(rec);dump('ACQUISITION_RECEIPTS.json',receipts)
        print(rec['status'],status,len(body),count,error,flush=True)
        if rec['status']=='SUCCESS':
            with(OUT/'GAIA_DR3_FIELD.csv').open('xb')as file:file.write(body)
            return
        if not retry:break
    raise RuntimeError('Single Gaia cone acquisition failed; exact receipts retained, no alternate request')

if __name__=='__main__':main()
