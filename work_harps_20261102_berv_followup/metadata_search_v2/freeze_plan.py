"""Freeze the syntax amendment and explicitly selected completed audits, offline."""
import datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
assert not (HERE/'RUN_STARTED.json').exists()
files={}
for p in sorted(HERE.iterdir()):
    if p.is_file() and p.name not in {'PREFLIGHT_FREEZE.json','ROOT_RELEASE.json'}:
        b=p.read_bytes();files[p.name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
for name in json.loads((HERE/'AUDIT_FILES.json').read_text()):
    assert '/' not in name and 'header' not in name.lower()
    p=HERE.parent/'independent_audit'/name;b=p.read_bytes()
    files['../independent_audit/'+name]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
out={'schema':'HARPS_METADATA_PREFLIGHT_FREEZE_V2_SYNTAX_AMENDMENT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FROZEN_BEFORE_AMENDED_TARGET_REQUESTS','previous_failed_requests':1,'new_target_requests_executed':0,'additional_target_requests_max':2,'continuation_target_requests_max':3,'science_payload_bytes':0,'files':files}
p=HERE/'PREFLIGHT_FREEZE.json';p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'files':len(files),'freeze_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
