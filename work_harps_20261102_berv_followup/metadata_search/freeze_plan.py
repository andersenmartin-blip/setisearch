"""Freeze committed metadata-query inputs after independent preflight; no network."""
import datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
assert not (HERE/'RUN_STARTED.json').exists()
excluded={'PREFLIGHT_FREEZE.json','ROOT_RELEASE.json','ESO_PROGRAMMATIC.html','ESO_DEMO.html'}
files={}
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or path.name in excluded or '__pycache__' in path.parts: continue
    data=path.read_bytes();files[str(path.relative_to(HERE))]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
audit=HERE.parent/'independent_audit'
for path in sorted(audit.glob('*')):
    if path.is_file() and path.suffix in {'.py','.json','.md'}:
        data=path.read_bytes();files['../independent_audit/'+path.name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
out={'schema':'HARPS_METADATA_PREFLIGHT_FREEZE_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FROZEN_BEFORE_TARGET_REQUESTS','target_requests_executed':0,'science_payload_bytes':0,'files':files,'raw_HTML_excluded':'Source URLs/retrieval hashes and concise contract notes retained; full HTML pages remain local only.'}
p=HERE/'PREFLIGHT_FREEZE.json';p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'files':len(files),'freeze_sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
