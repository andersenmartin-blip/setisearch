"""Read-only ESO metadata verification for the proposed100; no science download."""
from pathlib import Path
import csv,json,urllib.request,urllib.parse,datetime,hashlib,concurrent.futures,time
OUT=Path(__file__).resolve().parent
def query(name,adql):
    url='https://archive.eso.org/tap_obs/sync?'+urllib.parse.urlencode(dict(REQUEST='doQuery',LANG='ADQL',FORMAT='csv',QUERY=adql,MAXREC=5000))
    start=time.monotonic()
    with urllib.request.urlopen(url,timeout=45) as response:
        data=response.read(3_000_001);status=response.status;ctype=response.headers.get('Content-Type')
    assert len(data)<=3_000_000
    assert data[:6]!=b'<?xml ',data[:200]
    (OUT/(name+'.csv')).write_bytes(data)
    receipt=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),adql=adql,url=url,status=status,
        content_type=ctype,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),seconds=time.monotonic()-start,
        rows=len(list(csv.DictReader(data.decode().splitlines()))),science_arrays_opened=0)
    (OUT/(name+'_QUERY.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(name=name,rows=receipt['rows'],bytes=len(data),seconds=receipt['seconds'])),flush=True)
    return receipt
def main():
    rows=list(csv.DictReader((OUT/'PROPOSED100_METADATA.csv').open()))
    ids=','.join("'"+r['dp_id']+"'" for r in rows)
    tasks=[('RAW_PROVENANCE',"SELECT f.product_id,f.archive_id,f.internal_file_id,p.source_file FROM phase3v2.product_files AS f JOIN phase3v2.provenance AS p ON f.internal_file_id=p.product_file WHERE f.product_id IN ("+ids+") AND f.archive_id=f.product_id"),
        ('PRODUCT_METADATA',"SELECT product_id,archive_id,extension,eso_category,original_filename,access_url,access_estsize FROM phase3v2.product_files WHERE product_id IN ("+ids+")"),
        ('CURRENT_OBSCORE',"SELECT dp_id,target_name,s_ra,s_dec,instrument_name,t_min,t_max,t_exptime,em_min,em_max,em_res_power,snr,n_obs,multi_ob,obs_release_date,access_url,access_estsize FROM ivoa.ObsCore WHERE dp_id IN ("+ids+")")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:receipts=list(pool.map(lambda t:query(*t),tasks))
    (OUT/'METADATA_QUERY_SUMMARY.json').write_text(json.dumps(dict(queries=receipts,total_bytes=sum(r['bytes'] for r in receipts),new_science_arrays_opened=0),indent=2)+'\n')
if __name__=='__main__':main()
