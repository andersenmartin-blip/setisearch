#!/usr/bin/env python3
"""Header-only verification of the Kepler-732 dedicated six-scan sequence."""
import hashlib,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ls2c_header_preflight import hdf5_header_record,atomic_write
from seti_repeater.search_v0p6 import canonical_json_bytes

def main():
    out=Path('results_ls6_header');out.mkdir(exist_ok=True)
    rows=json.loads(Path('results_ls6_inventory/kepler732_--527320.json').read_text())['payload']['data']
    products=[r for r in rows if r['url'].endswith(('.gpuspec.0002.h5','.gpuspec.8.0001.h5'))]
    def read(r):
        path=out/(hashlib.sha256(r['url'].encode()).hexdigest()+'.json')
        if path.exists():return json.loads(path.read_text())
        h=hdf5_header_record(r['url'],'setisearch-LS6-header/1.0');h['listing_record']=r
        atomic_write(path,canonical_json_bytes(h));return h
    with ThreadPoolExecutor(max_workers=3) as pool:headers=list(pool.map(read,products))
    result={'artifact_type':'seti_repeater.ls6_header_inventory','spectral_values_read':False,'headers':headers}
    atomic_write(out/'headers.json',canonical_json_bytes(result))
    print([(h.get('source_name'),h.get('tstart_mjd'),h.get('error')) for h in headers],flush=True)
if __name__=='__main__':main()
