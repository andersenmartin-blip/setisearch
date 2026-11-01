"""Reassemble byte-identical archived profiles; verify every part and final ZIP."""
from pathlib import Path
import hashlib,json,os,zipfile

ROOT=Path(__file__).resolve().parent

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def main():
    manifest=json.loads((ROOT/'PROFILE_ARRAYS_PARTS.json').read_text())
    target=ROOT/manifest['output_filename']
    for part in manifest['parts']:
        path=ROOT/part['path']
        assert path.resolve().is_relative_to(ROOT),'Invalid part path'
        assert path.stat().st_size==part['bytes'] and digest(path)==part['sha256'],part['path']
    if target.exists():
        assert target.stat().st_size==manifest['bytes'] and digest(target)==manifest['sha256'],'Existing ZIP differs; move it aside explicitly'
    else:
        temp=target.with_suffix('.zip.assembling')
        with temp.open('xb') as output:
            for part in manifest['parts']:
                with (ROOT/part['path']).open('rb') as stream:
                    for block in iter(lambda:stream.read(1024*1024),b''):
                        output.write(block)
        assert temp.stat().st_size==manifest['bytes'] and digest(temp)==manifest['sha256'],'Reassembled ZIP differs'
        os.replace(temp,target)
    with zipfile.ZipFile(target) as archive:
        assert len(archive.namelist())==4370 and archive.testzip() is None,'Archive inventory/CRC mismatch'
    print(f'PASS: {len(manifest["parts"])} parts; byte-identical ZIP; 4370 profiles. Extract this ZIP inside {ROOT}.')

if __name__=='__main__':
    main()
