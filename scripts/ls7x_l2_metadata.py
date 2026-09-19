#!/usr/bin/env python3
"""LS7X metadata-only preflight for fixed DEFAULT CHEOPS L2 light curve."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_ls7x_l2_metadata'
BASE = 'https://cheops-webapp-pg.obsuksprd2.unige.ch/'
KEY = 'CH_PR300024_TG000301_V0300'
BUDGET = 64 * 1024
SAFE_HEADERS = {'content-length','content-type','content-range','accept-ranges',
                'content-disposition','etag','last-modified'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def get_url():
    payload = {'fileType': 'lightcurves',
               'filters': {'file_key': {'equal': [KEY]}},
               'aperture': 'default'}
    with urlopen(Request(BASE+'download', data=json.dumps(payload).encode(),
                         headers={'Accept':'application/json',
                                  'User-Agent':'dace-query/3.0.1'}), timeout=45) as r:
        info=json.load(r)
    assert isinstance(info.get('key'), str) and info['key']
    return BASE+'download/photometry/'+info['key']+'?compressed=false'


def read_range(url, start, count, identity, records):
    assert count == 2880
    assert (len(records)+1)*2880 <= BUDGET
    with urlopen(Request(url, headers={'Range':f'bytes={start}-{start+count-1}',
                                      'Accept':'application/octet-stream',
                                      'Accept-Encoding':'identity'}), timeout=45) as r:
        assert r.status == 206
        cr=r.headers['Content-Range']
        prefix,total=cr.split('/')
        total=int(total)
        assert prefix == f'bytes {start}-{start+count-1}'
        assert int(r.headers['Content-Length']) == count
        etag=r.headers.get('ETag')
        disposition=r.headers.get('Content-Disposition')
        now={'total':total,'etag':etag,'content_disposition':disposition}
        if identity:
            assert now == identity, (now,identity)
        body=r.read(count+1)
        assert len(body)==count
        records.append({'start':start,'count':count,'sha256':sha(body),
                        'retrieved_utc':datetime.now(timezone.utc).isoformat(),
                        'headers':{k:v for k,v in r.headers.items()
                                   if k.lower() in SAFE_HEADERS}})
    return body, now


def read_header(url, start, identity, records):
    raw=b''
    offset=start
    for _ in range(16):
        block,identity=read_range(url,offset,2880,identity,records)
        raw+=block
        offset+=2880
        if any(block[i:i+8] == b'END     ' for i in range(0,2880,80)):
            return raw, offset, identity
    raise ValueError('header exceeds declared bound')


def main():
    assert not OUT.exists(), 'refuse completed preflight overwrite'
    OUT.mkdir()
    url=get_url()
    records=[]
    primary,offset,identity=read_header(url,0,None,records)
    h0=fits.Header.fromstring(primary.decode('ascii'), sep='')
    assert h0['SIMPLE'] is True

    table_header,table_start,identity=read_header(url,offset,identity,records)
    h1=fits.Header.fromstring(table_header.decode('ascii'), sep='')
    assert h1['XTENSION'] == 'BINTABLE'
    assert h1.get('EXTNAME') == 'SCI_COR_Lightcurve'
    data_bytes=h1['NAXIS1']*h1['NAXIS2'] + h1.get('PCOUNT',0)
    assert data_bytes > 0
    # Critical boundary: acquired bytes end exactly at table-data start.
    assert table_start == sum(x['count'] for x in records)
    assert table_start < identity['total']
    assert table_start + data_bytes <= identity['total']

    (OUT/'primary_header.bin').write_bytes(primary)
    (OUT/'lightcurve_header.bin').write_bytes(table_header)
    columns=[{'index':i,'name':h1[f'TTYPE{i}'],'format':h1[f'TFORM{i}'],
              'unit':h1.get(f'TUNIT{i}')}
             for i in range(1,h1['TFIELDS']+1)]
    names={x['name'] for x in columns}
    required={'UTC_TIME','MJD_TIME','BJD_TIME','FLUX','FLUXERR','STATUS','EVENT'}
    assert required <= names, sorted(required-names)

    keys=['EXTNAME','EXT_VER','DATA_LVL','PROC_CHN','PIPE_VER','TIMESYS',
          'T_STRT_U','T_STOP_U','T_STRT_M','T_STOP_M','NEXP','EXPTIME',
          'TEXPTIME','EXPT_TYP','AP_RADI','STACKING','ROUNDING','NLIN_COR',
          'BIAS_RON','DARK','FFIELD','JITTER','WCS','SMEARING','BKGSL_C',
          'APERTURE','CONTAMIN','PSF_FIT','LC_QUAL','LC_CFG','CHECKSUM','DATASUM']
    summary={
        'stage':'LS7X_METADATA_PREFLIGHT',
        'file_key':KEY,
        'selection':{'file_type':'lightcurves','aperture':'default',
                     'selected_before_table_data':True},
        'total_file_bytes':identity['total'],
        'etag':identity['etag'],
        'content_disposition':identity['content_disposition'],
        'header_bytes_acquired':table_start,
        'table_data_bytes_acquired':0,
        'table_data_start':table_start,
        'table_bytes_declared':data_bytes,
        'rows':h1['NAXIS2'],
        'row_bytes':h1['NAXIS1'],
        'fields':h1['TFIELDS'],
        'keywords':{k:h1.get(k,h0.get(k)) for k in keys},
        'columns':columns,
        'required_columns_present':sorted(required),
        'science_values_inspected':0,
        'native_transient_trials':0,
        'candidate_decisions':0,
        'new_qualified_observing_seconds':0
    }
    save(OUT/'summary.json',summary)
    save(OUT/'ranges.json',{'download_api':BASE+'download','budget_bytes':BUDGET,
                            'total_bytes_read':sum(x['count'] for x in records),
                            'ranges':records})
    files=sorted(p for p in OUT.iterdir() if p.is_file())
    (OUT/'SHA256SUMS').write_text(''.join(
        f'{sha(p.read_bytes())}  {p.name}\n' for p in files if p.name!='SHA256SUMS'))
    print(json.dumps({k:summary[k] for k in ['stage','content_disposition',
          'total_file_bytes','header_bytes_acquired','table_data_bytes_acquired',
          'rows','row_bytes','fields']}, indent=2))


if __name__ == '__main__':
    main()
