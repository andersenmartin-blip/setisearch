#!/usr/bin/env python3
"""LS8A metadata-only preflight for the fixed held-out CHEOPS DEFAULT L2 visit."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from astropy.io import fits

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls8a_l2_metadata'
BASE='https://cheops-webapp-pg.obsuksprd2.unige.ch/'
KEY='CH_PR100006_TG000301_V0300'
BUDGET=64*1024
SAFE={'content-length','content-type','content-range','accept-ranges',
      'content-disposition','etag','last-modified'}

def sha(b): return hashlib.sha256(b).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def get_url():
    payload={'fileType':'lightcurves','filters':{'file_key':{'equal':[KEY]}},'aperture':'default'}
    with urlopen(Request(BASE+'download',data=json.dumps(payload).encode(),
        headers={'Accept':'application/json','User-Agent':'dace-query/3.0.1'}),timeout=45) as r:
        info=json.load(r)
    if not isinstance(info.get('key'),str) or not info['key']:
        raise RuntimeError('exact held-out DEFAULT lightcurve unavailable')
    return BASE+'download/photometry/'+info['key']+'?compressed=false'

def rr(url,start,count,identity,records):
    assert count==2880 and (len(records)+1)*count<=BUDGET
    with urlopen(Request(url,headers={'Range':f'bytes={start}-{start+count-1}',
        'Accept':'application/octet-stream','Accept-Encoding':'identity'}),timeout=45) as r:
        assert r.status==206
        prefix,total=r.headers['Content-Range'].split('/'); total=int(total)
        assert prefix==f'bytes {start}-{start+count-1}'
        now={'total':total,'etag':r.headers.get('ETag'),
             'content_disposition':r.headers.get('Content-Disposition')}
        if identity: assert now==identity,(now,identity)
        b=r.read(count+1); assert len(b)==count
        records.append({'start':start,'count':count,'sha256':sha(b),
          'retrieved_utc':datetime.now(timezone.utc).isoformat(),
          'headers':{k:v for k,v in r.headers.items() if k.lower() in SAFE}})
        return b,now

def header(url,start,identity,records):
    raw=b''; off=start
    for _ in range(16):
        b,identity=rr(url,off,2880,identity,records); raw+=b; off+=2880
        if any(b[i:i+8]==b'END     ' for i in range(0,2880,80)): return raw,off,identity
    raise RuntimeError('header exceeds bound')

def main():
    assert not OUT.exists(),'refuse completed overwrite'
    OUT.mkdir()
    url=get_url(); records=[]
    p,off,ident=header(url,0,None,records)
    h0=fits.Header.fromstring(p.decode('ascii'),sep='')
    t,tstart,ident=header(url,off,ident,records)
    h1=fits.Header.fromstring(t.decode('ascii'),sep='')
    assert h0['SIMPLE'] is True and h1['XTENSION']=='BINTABLE'
    assert h1.get('EXTNAME')=='SCI_COR_Lightcurve'
    declared=h1['NAXIS1']*h1['NAXIS2']+h1.get('PCOUNT',0)
    assert tstart==sum(x['count'] for x in records) and tstart<ident['total']
    assert tstart+declared<=ident['total']
    (OUT/'primary_header.bin').write_bytes(p); (OUT/'lightcurve_header.bin').write_bytes(t)
    cols=[{'index':i,'name':h1[f'TTYPE{i}'],'format':h1[f'TFORM{i}'],'unit':h1.get(f'TUNIT{i}')}
          for i in range(1,h1['TFIELDS']+1)]
    names={c['name'] for c in cols}
    required={'BJD_TIME','FLUX','FLUXERR','STATUS','EVENT'}
    assert required<=names
    keys=['EXTNAME','EXT_VER','DATA_LVL','PROC_CHN','PIPE_VER','TIMESYS','T_STRT_U','T_STOP_U',
          'NEXP','EXPTIME','TEXPTIME','EXPT_TYP','AP_RADI','STACKING','ROUNDING','NLIN_COR',
          'CHECKSUM','DATASUM']
    summary={'stage':'LS8A_HELDOUT_METADATA_PREFLIGHT','status':'METADATA_ONLY',
      'selection_rule':'chronologically earliest public 55 Cnc visit after retained March 2020 pilot',
      'archive_visit_id':'100006000301','obsid':1300462,'file_key':KEY,
      'selection':{'file_type':'lightcurves','aperture':'default','selected_before_table_data':True},
      'total_file_bytes':ident['total'],'etag':ident['etag'],'content_disposition':ident['content_disposition'],
      'header_bytes_acquired':tstart,'table_data_bytes_acquired':0,'table_data_start':tstart,
      'table_bytes_declared':declared,'rows':h1['NAXIS2'],'row_bytes':h1['NAXIS1'],
      'fields':h1['TFIELDS'],'keywords':{k:h1.get(k,h0.get(k)) for k in keys},'columns':cols,
      'science_values_inspected':0,'native_transient_trials':0,'candidate_decisions':0}
    save(OUT/'summary.json',summary)
    save(OUT/'ranges.json',{'budget_bytes':BUDGET,'total_bytes_read':sum(x['count'] for x in records),'ranges':records})
    files=sorted(p for p in OUT.iterdir() if p.is_file())
    (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.name}\n' for p in files if p.name!='SHA256SUMS'))
    print(json.dumps({k:summary[k] for k in ['stage','file_key','content_disposition','total_file_bytes',
      'header_bytes_acquired','table_data_bytes_acquired','rows','row_bytes','fields','keywords']},indent=2))

if __name__=='__main__': main()
