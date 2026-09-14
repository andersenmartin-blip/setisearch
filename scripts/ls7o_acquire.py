#!/usr/bin/env python3
"""Frozen exact-range acquisition; inspect only 4010 predeclared rows per star."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from astropy.io import fits

from ls7o_reference_metadata import Ranges

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls7o_inputs'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def dtype_from_header(header):
    formats={'D':'>f8','E':'>f4','J':'>i4'}
    dtype=np.dtype([(header[f'TTYPE{i}'],formats[header[f'TFORM{i}']]) for i in range(1,header['TFIELDS']+1)])
    assert dtype.itemsize==header['NAXIS1']==100
    return dtype


def main():
    assert not OUT.exists(),'refuse to overwrite completed inputs'
    cfg=json.loads((ROOT/'config/ls7o_reference.json').read_text())
    for path,expected in cfg['input_sha256'].items():assert digest(ROOT/path)==expected,path
    inventory=json.loads((ROOT/'results_ls7o_metadata/inventory.json').read_text())
    OUT.mkdir();(OUT/'raw').mkdir()
    def one(record):
        sector,tic=record['sector'],record['tic']
        product=record['product']
        allocation=next(r for r in cfg['acquisition'] if (r['sector'],r['tic'])==(sector,tic))
        ranges=Ranges(product['uri'],product['bytes'],etag=product['etag'],budget=allocation['bytes'])
        blocks=[ranges.get(r['start'],r['length']) for r in allocation['ranges']]
        raw=b''.join(blocks)
        assert len(raw)==401_000==allocation['bytes']
        header=fits.Header.fromstring((ROOT/'results_ls7o_metadata'/(record['header_prefix']+'_lightcurve.hdr')).read_bytes().decode('ascii'))
        table=np.frombuffer(raw,dtype=dtype_from_header(header)).reshape(10,401)
        timing=np.load(ROOT/f'results_ls7k_inputs/timing_s{sector:03d}.npz',allow_pickle=False)
        np.testing.assert_array_equal(table['CADENCENO'],timing['cadence'])
        time=np.array(table['TIME'],float);corr=np.array(table['TIMECORR'],float)
        difference=(time-corr-timing['time_spacecraft_btjd'])*86400
        assert np.isfinite(difference).all() and np.max(abs(difference))<=cfg['spacecraft_alignment_tolerance_seconds']
        rawpath=OUT/'raw'/f's{sector:03d}_tic{tic}.bin.gz'
        rawpath.write_bytes(gzip.compress(raw,mtime=0))
        centroid=np.stack([table['MOM_CENTR1'],table['MOM_CENTR2']],axis=-1).astype(float)
        error=np.stack([table['MOM_CENTR1_ERR'],table['MOM_CENTR2_ERR']],axis=-1).astype(float)
        valid=np.isfinite(centroid).all(-1)&np.isfinite(error).all(-1)&(error>0).all(-1)&(table['QUALITY']==0)
        provenance={'sector':sector,'tic':tic,'uri':product['uri'],'product_bytes':product['bytes'],'etag':ranges.etag,
                    'download_bytes':ranges.total,'ranges':ranges.records,'raw_path':str(rawpath.relative_to(OUT)),
                    'raw_sha256':hashlib.sha256(raw).hexdigest(),'compressed_sha256':digest(rawpath),
                    'selected_rows':4010,'valid_centroid_rows':int(valid.sum()),
                    'maximum_spacecraft_alignment_error_seconds':float(np.max(abs(difference))),
                    'finite_formal_errors':int(np.isfinite(error).sum()),
                    'formal_error_min_max_pixels':[float(error[np.isfinite(error)].min()),float(error[np.isfinite(error)].max())]}
        data={'centroid_xy':centroid,'error_xy':error,'quality':table['QUALITY'].astype(np.int64),
              'cadence':table['CADENCENO'].astype(np.int64),'time_barycentric_btjd':time,'time_correction_days':corr}
        print(f'Sector {sector} TIC {tic}: exact cadence join, {valid.sum()}/4010 usable centroid rows',flush=True)
        return provenance,data
    with ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(one,inventory['references']))
    for sector in [29,32]:
        chosen=[(r,d) for r,d in results if r['sector']==sector]
        assert len(chosen)==6
        values={k:np.stack([d[k] for r,d in chosen]) for k in chosen[0][1]}
        np.savez_compressed(OUT/f'references_s{sector:03d}.npz',tic=np.array([r['tic'] for r,d in chosen]),**values)
    save(OUT/'sources.json',{'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                            'reference_products':12,'distinct_tics':len({r['tic'] for r,d in results}),
                            'selected_reference_rows':48_120,'download_bytes':sum(r['download_bytes'] for r,d in results),
                            'records':[r for r,d in results],
                            'whole_product_checksum_checked':False,
                            'scope':'exact HTTP ranges pinned to metadata ETags, raw byte SHA-256 and duplicate cadence/time checks'})
    paths=sorted(p for p in OUT.rglob('*') if p.is_file())
    (OUT/'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.relative_to(OUT)}\n' for p in paths))


if __name__=='__main__':main()
