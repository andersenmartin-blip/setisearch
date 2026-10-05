"""Repair unpublished caller receipt using retained lossless Python JSON integers."""
from pathlib import Path
import hashlib,json,os,stat
BASE=Path('/workspace/scratch/d804553c0e89')
NS=BASE/'setisearch-status-20261004/results_radio_runtime_bootstrap_preparation_20261005a'
def main():
    receipt=NS/'administrative/invocation-receipt.json'
    old=receipt.read_bytes()
    backup=NS/'administrative/invocation-receipt-before-integer-repair.json'
    with backup.open('xb') as f: f.write(old)
    r=json.loads(old); copies=json.loads((BASE/'bootstrap-A-caller-copies.json').read_bytes())
    changes=[]
    for stream in copies['streams']:
        s=Path(stream['source_path']).stat(follow_symlinks=False)
        ident=stream['source_identity']
        assert ident['mtime_ns']==s.st_mtime_ns and ident['ctime_ns']==s.st_ctime_ns
        assert ident['device']==s.st_dev and ident['inode']==s.st_ino and ident['bytes']==s.st_size
        assert stat.S_ISREG(s.st_mode) and ident['mode']=='%04o'%stat.S_IMODE(s.st_mode)
        previous=next(x for x in r['caller_copies']['streams'] if x['source_path']==stream['source_path'])
        for field in ('mtime_ns','ctime_ns'):
            changes.append(dict(source=stream['source_path'],field=field,previous_decimal=str(previous['source_identity'][field]),exact_decimal=str(ident[field])))
    r['caller_copies']=copies
    r['administrative_integer_representation_repair']={
      'reason':'JavaScript numeric roundtrip rounded source nanosecond integers in unpublished administrative receipt',
      'authority':'retained successful Python caller-copy JSON; exact integers rechecked against unchanged source stat',
      'previous_receipt':'administrative/invocation-receipt-before-integer-repair.json',
      'previous_sha256':hashlib.sha256(old).hexdigest(),
      'changed_fields':changes,'original_files_modified':False,'bootstrap_replayed':False}
    raw=(json.dumps(r,indent=2)+'\n').encode()
    receipt.write_bytes(raw)
    print(json.dumps(dict(status='CORRECTED_EXACT_INTEGER_RECEIPT',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),original_files_modified=False,bootstrap_replayed=False),sort_keys=True))
if __name__=='__main__': main()
