#!/usr/bin/env python3
"""Frozen LS8Z range acquisition and paired-image analysis, with offline reuse."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen
import numpy as np
from astropy.io import fits
from ls8k_l2_screen import dtype
from seti_repeater.cheops_image_pair import analyze
from seti_repeater.cheops_url_timeout import resolve_url

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls8z_images'
BASE='https://cheops-webapp-pg.obsuksprd2.unige.ch/'


def atomic(path, payload):
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('wb') as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno())
    temp.replace(path)


def save(path,value):atomic(path,(json.dumps(value,indent=2,allow_nan=False)+'\n').encode())
def sha(raw):return hashlib.sha256(raw).hexdigest()


def get_url_once(key,kind):
    body={'fileType':kind,'filters':{'file_key':{'equal':[key]}},'aperture':None}
    with urlopen(Request(BASE+'download',data=json.dumps(body).encode(),headers={'Accept':'application/json','User-Agent':'dace-query/3.0.1'}),timeout=45) as response:
        result=json.load(response)
    return BASE+'download/photometry/'+result['key']+'?compressed=false'


TRANSPORT=[]
def get_url(key,kind):
    def record(entry):
        TRANSPORT.append(entry);save(OUT/'transport_attempts.json',TRANSPORT)
    return resolve_url(key+':'+kind,lambda _:get_url_once(key,kind),record)


def fetch(url,spec,scope,path,offline=False):
    receipt_path=path.with_suffix(path.suffix+'.json')
    if path.exists() and receipt_path.exists():
        record=json.loads(receipt_path.read_text());compressed=path.read_bytes();raw=gzip.decompress(compressed)
        assert sha(compressed)==record['gzip_sha256'] and sha(raw)==record['raw_sha256']
        assert record['start']==scope['start'] and record['count']==scope['count'] and record['etag']==spec['etag']
        assert len(raw)==scope['count']
        return raw
    assert not offline,'missing verified offline range'
    failures=[]
    for attempt in range(3):
        start,count=scope['start'],scope['count']
        try:
            with urlopen(Request(url,headers={'Range':f'bytes={start}-{start+count-1}','If-Match':spec['etag'],
                'Accept-Encoding':'identity','Accept':'application/octet-stream'}),timeout=90) as response:
                assert response.status==206
                assert response.headers['Content-Range']==f'bytes {start}-{start+count-1}/{spec["total"]}'
                assert int(response.headers['Content-Length'])==count
                assert response.headers.get('ETag')==spec['etag']
                assert response.headers.get('Content-Disposition')==spec['content_disposition']
                raw=response.read(count+1);assert len(raw)==count
            compressed=gzip.compress(raw,compresslevel=6,mtime=0)
            atomic(path,compressed)
            save(receipt_path,{'start':start,'count':count,'etag':spec['etag'],'content_disposition':spec['content_disposition'],
                'total':spec['total'],'raw_sha256':sha(raw),'gzip_sha256':sha(compressed),
                'status':206,'attempts':attempt+1,'prior_transport_failures':failures,'retrieved_utc':datetime.now(timezone.utc).isoformat()})
            return raw
        except AssertionError:
            raise # Identity/contract failures must never be retried away.
        except (OSError,TimeoutError) as error:
            failures.append({'attempt':attempt+1,'error':repr(error)})
            save(path.with_suffix('.failed.json'),failures)
    raise RuntimeError(f'exhausted identical-range retries: {path.name}')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--freeze',required=True);args=parser.parse_args()
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==args.freeze
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip()
    scope=json.loads((ROOT/'config/ls8z_payload_scope.json').read_text())
    for name,digest in scope['input_pins'].items():
        assert sha((ROOT/name).read_bytes())==digest,name
    cfg=json.loads((ROOT/'config/ls8z_images.json').read_text())
    assert cfg['status']=='METADATA_JOINED_IMAGES_CLOSED' and cfg['image_pixels_read']==0
    assert cfg['join_rows']==58 and cfg['image_science_bytes']==18560000 and cfg['smearing_bytes']==46400
    assert [(c['id'],c['start'],c['duration'],c['lo'],c['hi']) for c in cfg['contexts']]==[
        ('TG008601_N0',31,1,17,46)]
    assert json.loads((ROOT/'results_ls8z_metadata/audit.json').read_text())['status']=='PASS'
    for line in (ROOT/'results_ls8z_metadata/SHA256SUMS').read_text().splitlines():
        digest,relative=line.split('  ',1)
        assert sha((ROOT/'results_ls8z_metadata'/relative).read_bytes())==digest,relative
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'diagnostics.json').exists(),'refuse completed analysis overwrite'
    tables,urls={},{}
    results=[]
    for c in cfg['contexts']:
        key=c['file_key']; folder=OUT/c['id'];folder.mkdir(exist_ok=True)
        if key not in tables:
            header=fits.Header.fromstring((ROOT/'results_ls8y_l2_metadata'/key/'lightcurve_header.bin').read_bytes().decode(),sep='')
            tables[key]=np.frombuffer((ROOT/'results_ls8y_l2_screen'/key/'lightcurve_table.bin').read_bytes(),dtype=dtype(header))
        local=tables[key][c['lo']:c['hi']];n=len(local);d=c['duration']
        times=(local['BJD_TIME'].astype(float)-float(local['BJD_TIME'][14]))*86400.
        side=np.r_[np.arange(12),np.arange(16+d,28+d)];event=np.arange(14,14+d)
        arrays={}
        for kind in ('SCI_CAL_SubArray','SCI_COR_SubArray','SMEAR'):
            product='SCI_COR_SubArray' if kind=='SMEAR' else kind
            if not args.offline and (key,product) not in urls:urls[key,product]=get_url(key,product)
            raw=fetch(urls.get((key,product)),cfg['sources'][key][product],c['ranges'][kind],folder/(kind+'.bin.gz'),args.offline)
            arrays[kind]=np.frombuffer(raw,dtype='>f8').astype(float).reshape((n,200) if kind=='SMEAR' else (n,200,200))
            print(c['id'],kind,'verified bytes',len(raw),flush=True)
        spec=cfg['sources'][key]['SCI_COR_SubArray']
        center=[np.mean(local['CENTROID_X'][side].astype(float))-spec['xoff'],np.mean(local['CENTROID_Y'][side].astype(float))-spec['yoff']]
        result,maps=analyze(times,arrays['SCI_CAL_SubArray'],arrays['SCI_COR_SubArray'],arrays['SMEAR'],side,event,center,c['sign'])
        result={'id':c['id'],'file_key':key,'sign':c['sign'],'start':c['start'],'duration':d,**result}
        buffer=io.BytesIO();np.savez_compressed(buffer,**maps);atomic(folder/'event_maps.npz',buffer.getvalue())
        save(folder/'diagnostics.json',result);results.append(result)
        print(c['id'],result['classification'],flush=True)
    save(OUT/'diagnostics.json',results)
    save(OUT/'summary.json',{'status':'COMPLETE_UNAUDITED','contexts':len(results),
        'image_bytes':cfg['image_science_bytes'],'smearing_bytes':cfg['smearing_bytes'],
        'outcomes':{k:sum(r['classification']==k for r in results) for k in sorted(set(r['classification'] for r in results))},
        'input_l2_audit':'PASS','new_detector_qualification':False,'raw_imagettes_opened':False})


if __name__=='__main__':main()
