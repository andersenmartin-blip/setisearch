"""Independent bounded SIGPROC header reader; no payload values interpreted."""
from pathlib import Path
import struct
import hashlib
import json

EXPECTED_SHA='d0b41cf5d38b4128cf569f8c3d7d053ca923c7f5a1537a534b4a475e348dc688'
EXPECTED_BLOB='6fd2b196909eb35099eb07b7ba6d551bbf445725'
INTS={'machine_id','telescope_id','data_type','nchans','nbeams','ibeam','nbits','nifs'}
FLOATS={'src_raj','src_dej','az_start','za_start','fch1','foff','tstart','tsamp'}
STRINGS={'rawdatafile','source_name'}

def read_header(path):
    with Path(path).open('rb') as f:
        def text():
            n=struct.unpack('<i',f.read(4))[0]
            assert 0<n<256
            return f.read(n).decode('ascii')
        assert text()=='HEADER_START'
        header={}
        while True:
            key=text()
            if key=='HEADER_END': break
            assert key not in header
            if key in INTS: value=struct.unpack('<i',f.read(4))[0]
            elif key in FLOATS: value=struct.unpack('<d',f.read(8))[0]
            elif key in STRINGS: value=text()
            else: raise ValueError('Unsupported header field: '+key)
            header[key]=value
        header['header_bytes']=f.tell()
    return header

def main():
    root=Path(__file__).resolve().parents[2]
    data=root/'work_cb/new_data_discovery'
    path=data/'HIP35136_57563_0011_mid.fil'
    h=read_header(path)
    sh=hashlib.sha256();git=hashlib.sha1(b'blob '+str(path.stat().st_size).encode()+b'\0')
    with path.open('rb') as f:
        while part:=f.read(1024*1024):sh.update(part);git.update(part)
    assert sh.hexdigest()==EXPECTED_SHA and git.hexdigest()==EXPECTED_BLOB
    claimed=json.loads((data/'HIP35136_HEADER.json').read_text())
    assert all(claimed[k]==v for k,v in h.items())
    size=path.stat().st_size;payload=size-h['header_bytes']
    assert h['nbits']==32 and h['nifs']==1
    assert payload%(h['nchans']*4)==0
    rows=payload//(h['nchans']*4)
    assert rows==273 and h['nchans']==65536
    result={'schema':'SETI_CB_INDEPENDENT_HEADER_REVIEW_V1','status':'PASS_HEADER_AND_IDENTITY',
        'header':h,'bytes':size,'sha256':sh.hexdigest(),'git_blob_sha':git.hexdigest(),
        'rows':rows,'channels':h['nchans'],'samples':rows*h['nchans'],
        'payload_remainder_bytes':payload%(h['nchans']*4),
        'duration_seconds':rows*h['tsamp'],'channel_width_hz':abs(h['foff'])*1e6,
        'no_power_values_interpreted':True}
    out=Path(__file__).parent/'HEADER_REVIEW_CB.json'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','rows','channels','samples','no_power_values_interpreted']}))

if __name__=='__main__': main()
