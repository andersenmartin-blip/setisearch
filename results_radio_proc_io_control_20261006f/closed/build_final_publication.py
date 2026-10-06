"""Build closed evidence/draft UTF8 publication; no control/scientific execution."""
from pathlib import Path
import hashlib,json,stat
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
PREFIX='results_radio_proc_io_control_20261006f/closed'
DRAFT=BASE/'codec16-preparation-20261006-draft'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def main():
    bodies=json.loads((HERE/'result-publication-payload.json').read_bytes())
    metas=json.loads((HERE/'result-publication-meta.json').read_bytes())
    def add(path,repo):
        st=path.lstat();assert stat.S_ISREG(st.st_mode) and path.resolve()==path
        raw=path.read_bytes();body=raw.decode('utf-8');assert '\0' not in body and len(raw)<950*1024
        assert repo not in bodies
        bodies[repo]=body;metas[repo]=dict(local_path=str(path),bytes=len(raw),sha256=sha(raw),raw_bytes=len(raw),
            raw_sha256=sha(raw),encoding='utf-8',git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest())
    for name in ('RADIO_PROC_IO_CONTROL_2026-10-06F_RESULT.md','RADIO_CODEC16_2026-10-06_PREPARATION.md'):
        path=HERE/name
        if path.exists():add(path,name)
    add(Path(__file__),PREFIX+'/build_final_publication.py')
    reviewer=HERE/'review_closed_F.py'
    if reviewer.exists():add(reviewer,PREFIX+'/review_closed_F.py')
    for path in sorted(HERE.glob('*REVIEW*.json')):
        add(path,PREFIX+'/'+path.name)
    for path in sorted(HERE.glob('*review.log')):
        add(path,PREFIX+'/'+path.name)
    for path in sorted(DRAFT.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            add(path,'results_radio_codec16_preparation_20261006/'+path.relative_to(DRAFT).as_posix())
    summary=dict(schema='radio-proc-io-control-final-publication-build-v1',files=len(bodies),
        complete_utf8_bytes=sum(len(x.encode()) for x in bodies.values()),closed_result_files_present=True,
        draft_status='NO_DISPATCHED',scientific_authority=False,automatic_successor=False)
    path=HERE/'FINAL_PUBLICATION_BUILD.json';path.write_bytes(canonical(summary));add(path,PREFIX+'/'+path.name)
    (HERE/'final-publication-payload.json').write_bytes(canonical(bodies))
    (HERE/'final-publication-metadata.json').write_bytes(canonical(metas))
    print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
