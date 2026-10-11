"""Restore exactly pinned prior 2017 files, without a telescope request."""
import hashlib, json, time, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
RECOVERED = ROOT.parent / 'recovered'
OUT = Path(__file__).parent / 'INPUT_RESTORATION_RECEIPT.json'
def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def main():
    start=time.process_time(); wall=time.perf_counter()
    assert not OUT.exists()
    bundle=RECOVERED/'SETI_BURST4_RESULTS_2026-10-11.zip'
    assert digest(bundle)=='8e5e37405026187302260d6a82c490aaa475edea37d2506a851d2ba1dcbf57e3'
    m=json.loads((ROOT/'RESULT_PACKAGE_MANIFEST.json').read_text())
    for r in m['files']:
        p=ROOT/r['path']; assert p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],r['path']
    join=RECOVERED/'SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip'
    if not join.exists():
        with join.open('xb') as f:
            for i in (1,2,3):
                p=RECOVERED/('SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip.part%02d'%i)
                with p.open('rb') as inp:
                    for b in iter(lambda:inp.read(1048576),b''):f.write(b)
    archives=[(RECOVERED/'SETI_S2017_NATIVE171_RAW_2026-10-10.zip','6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786','analysis/new_visit_recovery/results/acquire'),(join,'b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f','analysis/s2017_next_native/results/acquire')]
    restored=[]
    for archive,sha,directory in archives:
        assert digest(archive)==sha
        with zipfile.ZipFile(archive) as z:
            names=[n for n in z.namelist() if n.startswith(directory+'/') and (n.endswith('.compact.h5') or n.endswith('/ACQUISITION_RESULT.json'))]
            for name in names:
                assert '..' not in Path(name).parts and not name.startswith('/')
                data=z.read(name); p=ROOT/name; p.parent.mkdir(parents=True,exist_ok=True)
                if p.exists():assert p.read_bytes()==data
                else:
                    with p.open('xb') as f:f.write(data)
                restored.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    for _,_,directory in archives:
        a=json.loads((ROOT/directory/'ACQUISITION_RESULT.json').read_text())
        for r in a['decoded_files']:
            p=ROOT/directory/r['array_file'];assert p.stat().st_size==r['bytes'] and digest(p)==r['file_sha256']
    receipt={'status':'PASS_PRIOR1938_PAYLOAD_HASHES_AND18_SOURCE_COMPACT_FILE_HASHES','restored_files':restored,'previous_payload_files_verified':len(m['files']),'original_source_arrays_decoded':False,'new_telescope_HTTP_requests':0,'cost_DKK':0,'process_CPU_s':time.process_time()-start,'wall_s':time.perf_counter()-wall}
    with OUT.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='restored_files'}))
if __name__=='__main__':main()
