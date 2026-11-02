"""Deterministically package only the20 bulky full-reference diagnostic JSON files."""
from pathlib import Path
import zipfile,json,hashlib,io
OUT=Path(__file__).resolve().parent
NAME='MAPPING_REFERENCE_EVIDENCE.zip'
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 execution=json.loads((OUT/'EXECUTION_SUMMARY.json').read_text());assert execution['exposures']==20
 members=[];buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
  for i in range(1,21):
   name=f'exposure_{i:02d}/RAW_REFERENCE_DIAGNOSTICS.json';p=OUT/name;data=p.read_bytes()
   info=zipfile.ZipInfo(name,date_time=(2026,11,2,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100600<<16
   archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
   members.append(dict(path=name,bytes=len(data),sha256=digest(data)))
 data=buffer.getvalue();(OUT/NAME).write_bytes(data);parts=[];(OUT/'evidence_parts').mkdir(exist_ok=True)
 for i,start in enumerate(range(0,len(data),900000),1):
  name=f'evidence_parts/MAPPING_REFERENCE_EVIDENCE.zip.part{i:03d}';piece=data[start:start+900000];(OUT/name).write_bytes(piece)
  parts.append(dict(path=name,bytes=len(piece),sha256=digest(piece)))
 metadata=dict(archive=NAME,bytes=len(data),sha256=digest(data),members=members,member_count=len(members),uncompressed_bytes=sum(m['bytes'] for m in members),compression='zip deflate level9',fixed_zip_timestamp='2026-11-02T00:00:00',source='Exactly20 new full-reference diagnostic JSON outputs; per-exposure summaries and all scripts/tables remain direct files.')
 (OUT/'EVIDENCE_ARCHIVE.json').write_text(json.dumps(metadata,indent=2)+'\n')
 (OUT/'EVIDENCE_PARTS.json').write_text(json.dumps(dict(archive=NAME,bytes=len(data),sha256=digest(data),parts=parts),indent=2)+'\n')
 print(json.dumps({k:v for k,v in metadata.items() if k!='members'},indent=2))
if __name__=='__main__':main()
