#!/usr/bin/env python3
"""Bounded header-only preflight for the two frozen LS8G GJ 849 visits."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from astropy.io import fits

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls8g_l2_metadata'
BASE='https://cheops-webapp-pg.obsuksprd2.unige.ch/'
KEYS=['CH_PR100018_TG032401_V0300','CH_PR100018_TG032402_V0300']
BLOCK=2880; BUDGET=64*1024
REQ={'BJD_TIME','FLUX','FLUXERR','STATUS','EVENT'}
KEYWORDS=['EXTNAME','EXT_VER','DATA_LVL','PROC_CHN','PIPE_VER','TIMESYS','T_STRT_U','T_STOP_U',
 'NEXP','EXPTIME','TEXPTIME','EXPT_TYP','AP_RADI','STACKING','ROUNDING','NLIN_COR',
 'APERTURE','CHECKSUM','DATASUM']
SAFE={'content-length','content-type','content-range','accept-ranges','content-disposition','etag','last-modified'}

def sha(b): return hashlib.sha256(b).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def url_for(key):
 payload={'fileType':'lightcurves','filters':{'file_key':{'equal':[key]}},'aperture':'default'}
 with urlopen(Request(BASE+'download',data=json.dumps(payload).encode(),
   headers={'Accept':'application/json','User-Agent':'dace-query/3.0.1'}),timeout=45) as r: info=json.load(r)
 assert isinstance(info.get('key'),str) and info['key']
 return BASE+'download/photometry/'+info['key']+'?compressed=false'

def block(url,start,ident,records):
 assert (len(records)+1)*BLOCK<=BUDGET
 with urlopen(Request(url,headers={'Range':f'bytes={start}-{start+BLOCK-1}',
   'Accept':'application/octet-stream','Accept-Encoding':'identity'}),timeout=45) as r:
  assert r.status==206
  prefix,total=r.headers['Content-Range'].split('/'); total=int(total)
  assert prefix==f'bytes {start}-{start+BLOCK-1}' and int(r.headers['Content-Length'])==BLOCK
  now={'total':total,'etag':r.headers.get('ETag'),'content_disposition':r.headers.get('Content-Disposition')}
  assert now['etag'] and now['content_disposition']
  if ident: assert now==ident
  raw=r.read(BLOCK+1); assert len(raw)==BLOCK
  records.append({'start':start,'count':BLOCK,'sha256':sha(raw),'retrieved_utc':datetime.now(timezone.utc).isoformat(),
    'headers':{k:v for k,v in r.headers.items() if k.lower() in SAFE}})
  return raw,now

def header(url,start,ident,records):
 raw=b''; off=start
 for _ in range(16):
  b,ident=block(url,off,ident,records); raw+=b; off+=BLOCK
  if any(b[i:i+8]==b'END     ' for i in range(0,BLOCK,80)): return raw,off,ident
 raise RuntimeError('header exceeds bound')

def one(key):
 d=OUT/key; d.mkdir(parents=True); records=[]; url=url_for(key)
 p,off,ident=header(url,0,None,records); h0=fits.Header.fromstring(p.decode('ascii'),sep='')
 t,start,ident=header(url,off,ident,records); h1=fits.Header.fromstring(t.decode('ascii'),sep='')
 assert h0['SIMPLE'] is True and h1['XTENSION']=='BINTABLE' and h1['EXTNAME']=='SCI_COR_Lightcurve'
 assert key in ident['content_disposition']
 count=h1['NAXIS1']*h1['NAXIS2']+h1.get('PCOUNT',0)
 assert start==sum(x['count'] for x in records) and start+count<=ident['total']
 cols=[{'index':i,'name':h1[f'TTYPE{i}'],'format':h1[f'TFORM{i}'],'unit':h1.get(f'TUNIT{i}')} for i in range(1,h1['TFIELDS']+1)]
 assert REQ<={c['name'] for c in cols}
 kw={k:h1.get(k,h0.get(k)) for k in KEYWORDS}
 assert str(kw['PIPE_VER'])=='14.1.2' and int(kw['NEXP'])==14
 assert abs(float(kw['EXPTIME'])-3.0)<1e-9 and abs(float(kw['TEXPTIME'])-42.0)<1e-6
 (d/'primary_header.bin').write_bytes(p); (d/'lightcurve_header.bin').write_bytes(t)
 save(d/'ranges.json',{'budget_bytes':BUDGET,'total_bytes_read':sum(x['count'] for x in records),'ranges':records})
 x={'status':'METADATA_ONLY','file_key':key,'total_file_bytes':ident['total'],'etag':ident['etag'],
   'content_disposition':ident['content_disposition'],'header_bytes_acquired':start,'table_data_bytes_acquired':0,
   'table_data_start':start,'table_bytes_declared':count,'rows':h1['NAXIS2'],'row_bytes':h1['NAXIS1'],
   'fields':h1['TFIELDS'],'keywords':kw,'columns':cols,'lightcurve_values_read':0,'image_pixels_read':0}
 save(d/'summary.json',x); return x

def main():
 assert not OUT.exists(); OUT.mkdir(); rr=[one(k) for k in KEYS]
 schema=[[(c['name'],c['format'],c['unit']) for c in r['columns']] for r in rr]
 compatible=schema[0]==schema[1] and rr[0]['row_bytes']==rr[1]['row_bytes'] and rr[0]['fields']==rr[1]['fields']
 s={'stage':'LS8G_GJ849_L2_HEADER_PREFLIGHT','status':'PASS_COMPATIBLE' if compatible else 'INCOMPATIBLE',
   'selected_keys':KEYS,'products':rr,'compatible_schema':compatible,'table_data_bytes_acquired':0,
   'lightcurve_values_read':0,'image_pixels_read':0}
 save(OUT/'summary.json',s)
 files=sorted(p for p in OUT.rglob('*') if p.is_file())
 (OUT/'SHA256SUMS').write_text(''.join(f'{sha(p.read_bytes())}  {p.relative_to(OUT)}\n' for p in files if p.name!='SHA256SUMS'))
 print(json.dumps({'status':s['status'],'products':[{'key':r['file_key'],'rows':r['rows'],'row_bytes':r['row_bytes'],
  'table_start':r['table_data_start'],'table_bytes':r['table_bytes_declared'],'header_bytes':r['header_bytes_acquired']} for r in rr],
  'table_data_bytes_acquired':0},indent=2))
if __name__=='__main__': main()
