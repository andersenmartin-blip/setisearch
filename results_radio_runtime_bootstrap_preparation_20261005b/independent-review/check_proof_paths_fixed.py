from pathlib import Path
import tempfile
import os
import json
HERE=Path(__file__).resolve().parent/'snapshot-03'
T={'__name__':'review_fixture','__file__':str(HERE/'test_bootstrap_gate.py')}
exec(compile((HERE/'test_bootstrap_gate.py').read_bytes(),T['__file__'],'exec'),T)
G=T['G']
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp); os.chmod(root,0o700)
    c=T['fixture'](root); ch,p,m=T['proof_fixture'](c)
    for row in p['publication_files']: row['repository_path']='one-path-for-all-source-files.py'
    pr=G['canonical'](p); mr=G['canonical'](m)
    try:
        G['verify_publication'](c,ch,pr,G['digest'](pr),mr,G['digest'](mr))
        accepted=True
    except G['Refusal']: accepted=False
    print(json.dumps({'case':'all publication source rows use one identical repository_path','accepted':accepted,'note':'Duplicate paths refused; actual immutable tree identity still requires external caller readback.'},indent=2))
