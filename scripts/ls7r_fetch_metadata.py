#!/usr/bin/env python3
"""Re-fetch the selected visit's public DACE metadata and calibration log.

The mission-browser 31-row selection and 49-row inventory are separately
saved DOM exports. They are not recreated by a differently scoped DACE query.
Requires dace-query==3.0.1; no authentication credentials are used.
"""
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

from dace_query import DaceClass
from dace_query.cheops import CheopsClass
from ls7r_acquire import OUT, KEY, SAFE_HEADERS, get_url, sha, save_json


def log_extract(body, headers):
    text = body.decode('utf8')
    refs = sorted(set(re.findall(r'CH_[A-Za-z0-9_.:-]*(?:REF|MCO)_[A-Za-z0-9_.:-]*\.fits', text)))
    lines = [{'line': i+1, 'text': line} for i,line in enumerate(text.splitlines())
             if any(x in line for x in ['REF_APP_', 'MCO_REP_', 'gain correction',
                                        'non-linearity', 'flat field', 'BadPixel'])]
    return {'product_name': headers.get('Content-Disposition'), 'log_sha256': sha(body),
            'log_bytes': len(body), 'headers': headers,
            'reference_filenames': refs, 'selected_lines': lines}


def main():
    OUT.mkdir(exist_ok=True)
    client = CheopsClass(DaceClass(dace_rc_config_path=Path('/dev/null')))
    visit = client.query_database(limit=10, filters={'file_key': {'contains': [KEY[:-6]]}},
                                  output_format='dict')
    products = client.browse_products(filters={'file_key': {'equal': [KEY]}},
                                      file_type='all', output_format='dict')
    save_json(OUT/'dace_visit.json',visit)
    save_json(OUT/'dace_products.json',products)
    assert sum(x=='log' for x in products['file_ext']) == 1
    url = get_url('log')
    with urlopen(Request(url,headers={'Range':'bytes=0-0'}),timeout=45) as r:
        assert r.status==206
        total=int(r.headers['Content-Range'].split('/')[-1])
        assert 0<total<10_000_000
    with urlopen(Request(url,headers={'Range':f'bytes=0-{total-1}'}),timeout=45) as r:
        assert r.status==206
        body=r.read(total+1); assert len(body)==total
        headers={k:v for k,v in r.headers.items() if k.lower() in SAFE_HEADERS}
    (OUT/'pipeline.log').write_bytes(body)
    save_json(OUT/'calibration_log_extract.json',log_extract(body,headers))


if __name__=='__main__':
    main()
