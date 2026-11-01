"""Lossless evidence archive; large inputs are in the separate input checkpoint."""
from pathlib import Path
import hashlib,json,zipfile
BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'v2/V2_ANALYSIS_EVIDENCE.zip'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
for sub in ['v2','triage_followup']:
    for p in sorted((BASE/sub).rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(BASE)
        if '__pycache__' in rel.parts or rel.parts[:2]==('v2','data'):continue
        if p.suffix.lower() in {'.png','.fits','.z','.tar','.zip','.pyc'}:continue
        if p.name=='EVIDENCE_ARCHIVE.json':continue
        files.append(p)
manifest=[dict(path=str(p.relative_to(BASE)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,p.relative_to(BASE))
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    for m in manifest:assert hashlib.sha256(z.read(m['path'])).hexdigest()==m['sha256']
record=dict(archive=OUT.name,bytes=OUT.stat().st_size,sha256=sha(OUT),members=len(manifest),
    excluded='Raw FITS/TAR inputs, PNG figures (published separately), pycache and this manifest. All numeric tables, per-spectrum/per-trial JSON, analysis arrays, source code and receipts included.',files=manifest)
(BASE/'v2/EVIDENCE_ARCHIVE.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='files'},indent=2))
