"""Check closed CB artifact bindings without rerunning numerical analysis."""
from pathlib import Path
import hashlib,json,zipfile

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    root=Path(__file__).resolve().parents[2];w=root/'work_cb'
    scope=json.loads((w/'SCOPE_CB.json').read_text());freeze=json.loads((w/'PUBLIC_FREEZE_CB.json').read_text())
    execution=json.loads((w/'EXECUTION_CB.json').read_text());result=json.loads((w/'results/RESULT_CB.json').read_text())
    review=json.loads((w/'review/NUMERICAL_REVIEW_CB.json').read_text())
    assert review['status']=='PASS_COMPLETE_NUMERICAL_REVIEW'
    assert all(sha(root/p)==h for p,h in review['bound_input_output_hashes'].items())
    assert sha(w/'SCOPE_CB.json')==freeze['scope_sha256']==result['scope_sha256']
    assert sha(w/'analyze_stellar.py')==freeze['program_sha256']==result['program_sha256']
    assert sha(root/scope['input']['header'])==scope['input']['header_sha256']
    assert sha(root/scope['input']['path'])==scope['input']['sha256']==result['input_sha256']
    assert result['public_scope_commit']==freeze['public_commit']
    for row in freeze['files']:
        b=(root/row['path']).read_bytes()
        git=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        assert git==row['blob_sha'],row['path']
    for name,digest in result['files_sha256'].items():assert sha(w/'results'/name)==digest
    archive=w/'CLOSED_PRODUCTION_CB.zip'
    assert sha(archive)==execution['archive_sha256']
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for member in execution['members']:
            b=z.read(member['path']);local=w/'results'/member['path']
            assert len(b)==member['bytes']
            assert hashlib.sha256(b).hexdigest()==member['sha256']==sha(local)
            assert b==local.read_bytes()
    assert execution['actual_process_exit_code']==0 and execution['production_attempts']==1
    assert execution['new_stellar_power_values_read']==review['power_samples_checked']==result['samples']
    report={'schema':'SETI_CB_FINAL_BINDING_REVIEW_V1','status':'PASS_CLOSED_ARTIFACT_BINDING_REVIEW',
      'numerical_review_sha256':sha(w/'review/NUMERICAL_REVIEW_CB.json'),
      'execution_receipt_sha256':sha(w/'EXECUTION_CB.json'),
      'closed_archive_sha256':sha(archive),'closed_archive_crc_pass':True,
      'closed_member_bytes_exact':len(execution['members']),
      'public_freeze_local_git_blobs_verified':len(freeze['files']),
      'scope_program_header_raw_and_result_pins_verified':True,
      'all_numerically_audited_bytes_still_unchanged':True,
      'limits':['This checks local bytes against recorded public Git blob IDs; root performed remote readback.',
                'Natural production exit is the root executor receipt; this reviewer observed its own numerical audit exit0.'],
      'reviewer_sha256':sha(__file__)}
    (w/'review/BINDING_REVIEW_CB.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','closed_member_bytes_exact','public_freeze_local_git_blobs_verified']}))

if __name__=='__main__':main()
