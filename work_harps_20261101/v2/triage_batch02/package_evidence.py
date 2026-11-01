"""Package small scientific evidence; inputs are in six separate checkpoints."""
from pathlib import Path
import json,hashlib,zipfile
BASE=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
archive=OUT/'TRIAGE02_EVIDENCE.zip'
files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
       and p.suffix.lower() not in {'.fits','.z','.tar','.zip','.pyc'} and not (p.suffix.lower()=='.png' and p.parent.name=='figures') and p.name!='EVIDENCE_ARCHIVE.json']
members=[dict(path=str(p.relative_to(BASE)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files]
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(BASE))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for m in members:assert hashlib.sha256(z.read(m['path'])).hexdigest()==m['sha256']
record=dict(filename=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),members=len(members),
    excluded='Raw FITS.Z/TAR inputs are in Library checkpoints; Primary figures are published separately; extra agent detail PNGs are included here.',files=members)
(OUT/'EVIDENCE_ARCHIVE.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='files'}))
