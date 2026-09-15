#!/usr/bin/env python3
"""Retrieve the exact small official PIPE wheel; extract data only, no code.

This HTTPS PyPI distribution is distinct from the blocked mission-archive
download. It supplies only the gain reference, nonlin provenance and licence.
"""
import hashlib
import io
import json
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = ('https://files.pythonhosted.org/packages/f9/c1/'
       'bcb472a01aac35f754dcea942314b2d89d91159ac377e495a2b1e0afd80f/'
       'pipe_cheops-1.1-py3-none-any.whl')
SHA = '2719c0742a3cd4c4fb641685ef6503dc5d783deca2164bcd987a6f42e923b6fe'
SIZE = 1522572
GAIN = 'CH_TU2020-02-18T06-15-13_REF_APP_GainCorrection_V0109.fits'
GAIN_BLOB = '3bde861175310b797e53a9be506d9f2eab816a73'
MEMBERS = ['pipe/data/'+GAIN, 'pipe/data/nonlin.txt',
           'pipe_cheops-1.1.dist-info/LICENSE.rst']


def main():
    with urlopen(URL, timeout=45) as response:
        assert response.status == 200
        if response.headers.get('Content-Length'):
            assert int(response.headers['Content-Length']) == SIZE
        body = response.read(2_000_001)
    assert len(body) == SIZE and hashlib.sha256(body).hexdigest() == SHA
    out = ROOT/'results_ls7s_calibration'
    target = out/'calibration'
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(body)) as wheel:
        for name in MEMBERS:
            data = wheel.read(name)
            if name.endswith(GAIN):
                blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                assert blob == GAIN_BLOB
            dest = target/Path(name).name
            if dest.exists():
                assert dest.read_bytes() == data, 'Existing reference differs; do not overwrite'
            else:
                dest.write_bytes(data)
    print(json.dumps({'wheel_bytes':SIZE,'wheel_sha256':SHA,
                      'extracted_members':MEMBERS,'package_code_executed':False},indent=2))


if __name__ == '__main__':
    main()
