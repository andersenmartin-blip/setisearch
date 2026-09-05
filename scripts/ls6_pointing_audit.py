#!/usr/bin/env python3
"""Read only Kepler-732 HDF5 pointing attributes, never spectrum values."""
import json,hashlib,math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import fsspec,h5py
from ls2c_header_preflight import json_value,atomic_write
from seti_repeater.search_v0p6 import canonical_json_bytes

def hdf5_position(attrs):
    # BL HDF5 stores RA in decimal hours and Dec in decimal degrees;
    # SIGPROC packed HHMMSS/DDMMSS decoding would be incorrect here.
    ra=float(attrs['src_raj']);dec=float(attrs['src_dej'])
    if not 0<=ra<24 or not -90<=dec<=90:raise RuntimeError('unexpected HDF5 coordinate units')
    return ra*15,dec
def distance(a,b):
    r1,d1=map(math.radians,a);r2,d2=map(math.radians,b)
    return math.degrees(math.acos(max(-1,min(1,math.sin(d1)*math.sin(d2)+math.cos(d1)*math.cos(d2)*math.cos(r1-r2)))))
def main():
    out=Path('results_ls6_header');out.mkdir(exist_ok=True)
    planets=json.loads(Path('results_ls6_inventory/kepler732_planets.json').read_text())['payload']
    reference=(planets[0]['ra'],planets[0]['dec'])
    rows=json.loads(Path('results_ls6_inventory/kepler732_--527320.json').read_text())['payload']['data']
    rows=[r for r in rows if r['target']=='KEPLER732C' and r['url'].endswith('.0002.h5')]
    def read(r):
        p=out/('pointing_'+hashlib.sha256(r['url'].encode()).hexdigest()+'.json')
        if p.exists():return json.loads(p.read_text())
        with fsspec.open(r['url'],mode='rb',block_size=1048576,cache_type='blockcache',client_kwargs={'trust_env':True}) as remote:
            with h5py.File(remote,'r') as f:
                attrs={**{k:json_value(v) for k,v in f.attrs.items()},**{k:json_value(v) for k,v in f['data'].attrs.items()}}
        header_position=hdf5_position(attrs)
        if distance(header_position,(r['ra'],r['decl']))*3600>1:raise RuntimeError('header/listing coordinate disagreement exceeds 1 arcsecond')
        result={'url':r['url'],'source_name':attrs['source_name'],'tstart':attrs['tstart'],'raw_src_raj':attrs['src_raj'],'raw_src_dej':attrs['src_dej'],'header_ra_dec_deg':header_position,'nasa_ra_dec_deg':reference,'header_to_nasa_arcmin':distance(header_position,reference)*60,'listing_to_nasa_arcmin':distance((r['ra'],r['decl']),reference)*60,'coordinate_units':'HDF5 decimal RA hours and Dec degrees','spectral_values_read':False}
        atomic_write(p,canonical_json_bytes(result));return result
    with ThreadPoolExecutor(max_workers=3) as pool:result={'spectral_values_read':False,'rows':list(pool.map(read,rows))}
    atomic_write(out/'pointing_audit.json',canonical_json_bytes(result));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
