"""Package reproducible context evidence; exclude only figures and archive outputs.

MANIFEST.json is the pre-archive source manifest; EVIDENCE_ARCHIVE.json is the
archive/member audit. Neither the archive nor its audit refers recursively to
itself. Original FITS/TAR inputs are external dependencies identified by their
existing hashes in the archived input tables and plans.
"""
from pathlib import Path
import zipfile,json,hashlib,datetime,zlib
P=Path(__file__).resolve().parent;archive=P/'LINE_CONTEXT_EVIDENCE.zip';audit=P/'EVIDENCE_ARCHIVE.json'
def sha(data):return hashlib.sha256(data).hexdigest()
source_files=[f for f in sorted(P.rglob('*')) if f.is_file() and f not in [archive,audit,P/'MANIFEST.json']]
(P/'MANIFEST.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Complete pre-archive line-context files, including all21 figures and all95 profiles; archive outputs audited separately.',files=[dict(path=str(f.relative_to(P)),bytes=f.stat().st_size,sha256=sha(f.read_bytes())) for f in source_files]),indent=2)+'\n')
files=[f for f in sorted(P.rglob('*')) if f.is_file() and f not in [archive,audit] and 'figures' not in f.relative_to(P).parts]
assert sum(f.suffix=='.npz' for f in files)==95
members=[]
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for f in files:
  data=f.read_bytes();name=str(f.relative_to(P));info=zipfile.ZipInfo(name,date_time=(2026,11,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
  z.writestr(info,data);members.append(dict(path=name,bytes=len(data),sha256=sha(data),crc32=f'{zlib.crc32(data)&0xffffffff:08x}'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(set(z.namelist()))==len(files)
 for m in members:
  data=z.read(m['path']);info=z.getinfo(m['path']);assert sha(data)==m['sha256'];assert f'{info.CRC:08x}'==m['crc32'];assert len(data)==m['bytes'];assert data==(P/m['path']).read_bytes()
report=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),archive=archive.name,archive_bytes=archive.stat().st_size,archive_sha256=sha(archive.read_bytes()),member_count=len(members),profile_npz_count=95,all_source_text_code_and_profiles_included=True,figures_excluded_and_published_separately=21,crc_test_passed=True,all_member_sha256_and_bytewise_source_checks_passed=True,source_manifest='MANIFEST.json',source_manifest_sha256=sha((P/'MANIFEST.json').read_bytes()),exclusions=['figures/ (all21 listed in source manifest; published separately)','LINE_CONTEXT_EVIDENCE.zip (self)','EVIDENCE_ARCHIVE.json (self-referential archive audit)'],members=members)
audit.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='members'},indent=2))
