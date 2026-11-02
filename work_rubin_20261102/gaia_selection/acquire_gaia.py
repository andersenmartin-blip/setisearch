"""Public metadata-only Gaia DR3 query; no Rubin photometry."""
from pathlib import Path
import hashlib,json,datetime,urllib.request,urllib.parse,urllib.error,time
OUT=Path(__file__).resolve().parent
URL='https://gea.esac.esa.int/tap-server/tap/sync'
COLUMNS='source_id,ra,dec,ref_epoch,ra_error,dec_error,pmra,pmdec,pmra_error,pmdec_error,pmra_pmdec_corr,parallax,parallax_error,parallax_over_error,radial_velocity,radial_velocity_error,ruwe,duplicated_source,astrometric_params_solved,phot_g_mean_mag,ra_pmra_corr,dec_pmdec_corr,ra_dec_corr'
QUERY=f"SELECT TOP 50001 {COLUMNS} FROM gaiadr3.gaia_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',8.986275,-42.709834,0.6)) ORDER BY source_id"
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def main():
 plan=json.loads((OUT/'PLAN.json').read_text())
 assert not (OUT/'GAIA_DR3_FIELD.csv').exists()
 receipts=[]
 payload=urllib.parse.urlencode({'REQUEST':'doQuery','LANG':'ADQL','FORMAT':'csv','MAXREC':'50001','QUERY':QUERY}).encode()
 (OUT/'QUERY.adql').write_text(QUERY+'\n')
 for attempt,timeout in enumerate([45,90],1):
  rec={'attempt':attempt,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'url':URL,'method':'POST','query_sha256':hashlib.sha256(QUERY.encode()).hexdigest(),'timeout_seconds':timeout,'response_bytes':0}
  try:
   req=urllib.request.Request(URL,data=payload,headers={'Content-Type':'application/x-www-form-urlencoded','User-Agent':'SETI-archival-metadata-study/1.0'})
   with urllib.request.build_opener(NoRedirect()).open(req,timeout=timeout) as response:
    rec.update(http_status=response.status,headers=dict(response.headers),final_url=response.geturl())
    body=response.read(8000001);rec['response_bytes']=len(body)
    if len(body)>8000000:raise ValueError('metadata cap exceeded')
    if response.status!=200:raise ValueError('unexpected status')
    if not body.startswith(b'source_id,'):raise ValueError('unexpected CSV header')
    (OUT/'GAIA_DR3_FIELD.csv').write_bytes(body)
    rec.update(status='SUCCESS',sha256=hashlib.sha256(body).hexdigest())
  except Exception as exc:
   rec.update(status='FAILED',error=repr(exc))
   if isinstance(exc,urllib.error.HTTPError):
    rec['http_status']=exc.code
    rec['error_body']=exc.read(5000).decode('utf-8','replace');exc.close()
  receipts.append(rec);(OUT/'ACQUISITION_RECEIPTS.json').write_text(json.dumps(receipts,indent=2)+'\n')
  print(rec['status'],rec.get('http_status'),rec['response_bytes'],flush=True)
  if rec['status']=='SUCCESS':return
  if rec.get('http_status') and rec['http_status']<500:break
 raise RuntimeError('Gaia acquisition failed; receipts retained')
if __name__=='__main__':main()
