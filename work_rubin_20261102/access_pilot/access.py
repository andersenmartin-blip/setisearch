#!/usr/bin/env python3
"""Small logged public Rubin/Fink API requests; JSON identifiers never use float."""
import datetime,hashlib,json,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE='https://api.lsst.fink-portal.org'

def fetch(endpoint,payload,label,*,method='POST',max_bytes=8000000):
    path=ROOT/label
    if path.exists():
        raise FileExistsError(path)
    url=BASE+endpoint
    body=None
    if method=='GET' and payload:url+='?'+urllib.parse.urlencode(payload)
    if method=='POST':body=json.dumps(payload).encode()
    request=urllib.request.Request(url,data=body,method=method,headers={'Content-Type':'application/json','User-Agent':'SETI archival science pilot; bounded public API queries'})
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();data=b'';status=None;error=None;headers={}
    try:
        with urllib.request.urlopen(request,timeout=40) as response:
            status=response.status;headers=dict(response.headers)
            data=response.read(max_bytes+1)
            if len(data)>max_bytes:raise ValueError('response exceeded frozen maximum')
    except urllib.error.HTTPError as exc:
        status=exc.code;headers=dict(exc.headers);data=exc.read(min(max_bytes,100000));error=str(exc)
    except Exception as exc:error=repr(exc)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    receipt={'started_utc':started,'elapsed_seconds':time.monotonic()-t,'method':method,'url':url,'payload':payload,'http_status':status,'error':error,'bytes_saved':len(data),'sha256':hashlib.sha256(data).hexdigest(),'headers':headers,'max_response_bytes':max_bytes,'path':str(path.relative_to(ROOT)),'complete':error is None}
    path.with_suffix(path.suffix+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['path','http_status','error','bytes_saved','elapsed_seconds']}),flush=True)
    return receipt,data

def parsed(data):
    return json.loads(data,parse_int=str)
