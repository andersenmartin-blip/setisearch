"""Restore archived earlier references and copy the20 exact discovery cache files."""
from pathlib import Path
import hashlib,json,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REPO=ROOT.parent
OLD=REPO/'work_harps_20261102_berv_followup/prospective_comparison'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 script=OLD/'restore_profile_evidence.py'
 state=json.loads((REPO/'work_harps_20261102_berv_followup/CONTINUATION_STATE.json').read_bytes())
 for p in [script,OLD/'PROFILE_EVIDENCE.json',OLD/'PROFILE_EVIDENCE.zip']:
  assert sha(p)==state['source_hashes'][str(p.relative_to(REPO))]
 subprocess.run([sys.executable,str(script)],check=True)
 events=json.loads((ROOT/'comparison/EVENTS.json').read_bytes());n=0
 for e in events:
  for x in e['discovery_profiles'].values():
   relative=Path('inputs')/x['profile_path'];src=OLD/relative;dest=ROOT/'comparison'/relative
   assert sha(src)==x['profile_sha256'] and dest.resolve().is_relative_to(ROOT/'comparison/inputs')
   if dest.exists() and sha(dest)!=x['profile_sha256']:raise FileExistsError('Preserve differing cache:'+str(dest))
   dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists():
    with dest.open('xb') as f:f.write(src.read_bytes())
   n+=1
 assert n==20
 print(json.dumps({'status':'PASS_EXACT_REFERENCE_CACHE','discovery_files':n,'old_context_profiles':24,'science_arrays_read':0}))
if __name__=='__main__':main()
