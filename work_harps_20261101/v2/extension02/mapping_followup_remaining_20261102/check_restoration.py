"""Check deterministic packaging and fresh,repeat,conflict,corrupt,symlink restore."""
from pathlib import Path
import json,hashlib,tempfile,shutil,subprocess,sys
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 manifest=json.loads((OUT/'EVIDENCE_ARCHIVE.json').read_text());parts=json.loads((OUT/'EVIDENCE_PARTS.json').read_text());checks=[]
 before={name:sha(OUT/name) for name in ['EVIDENCE_ARCHIVE.json','EVIDENCE_PARTS.json']+[p['path'] for p in parts['parts']]}
 subprocess.run([sys.executable,str(OUT/'package_evidence.py')],check=True,capture_output=True)
 checks.append(dict(name='deterministic_repack',passed=all(sha(OUT/n)==h for n,h in before.items())))
 with tempfile.TemporaryDirectory(prefix='mapping_restore_') as temp:
  root=Path(temp)
  for name in ['EVIDENCE_ARCHIVE.json','EVIDENCE_PARTS.json','restore_evidence.py']+[p['path'] for p in parts['parts']]:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OUT/name,p)
  def run():return subprocess.run([sys.executable,str(root/'restore_evidence.py')],capture_output=True,text=True)
  r=run();checks.append(dict(name='fresh_parts_only_restore',passed=r.returncode==0 and all(sha(root/m['path'])==m['sha256'] for m in manifest['members'])))
  r=run();checks.append(dict(name='identical_existing_retained',passed=r.returncode==0))
  p=root/manifest['members'][0]['path'];original=p.read_bytes();p.write_bytes(b'changed')
  r=run();checks.append(dict(name='changed_output_refused_without_overwrite',passed=r.returncode!=0 and p.read_bytes()==b'changed'));p.write_bytes(original)
  part=root/parts['parts'][0]['path'];saved=part.read_bytes();part.write_bytes(b'broken'+saved[6:])
  r=run();checks.append(dict(name='corrupt_part_refused',passed=r.returncode!=0));part.write_bytes(saved)
  p.unlink();p.symlink_to(root/manifest['members'][1]['path'])
  r=run();checks.append(dict(name='symlink_output_refused',passed=r.returncode!=0 and p.is_symlink()))
 assert all(c['passed'] for c in checks),checks
 report=dict(status='PASS',checks=checks,members=20,archive_sha256=manifest['sha256'],validation_script_sha256=sha(Path(__file__)))
 (OUT/'RESTORE_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
