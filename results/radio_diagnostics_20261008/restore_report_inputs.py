"""Restore three already published method report products as exact bytes."""
import base64,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=Path(__file__).resolve().parent
expected=[{"path":"results/radio_pilot_method_report_20261008/method_cells.csv","sha":"ee77abf87b5bd83d69124fc1c5246161cd1a009e"},{"path":"results/radio_pilot_method_report_20261008/report_data.json","sha":"c94dd0612988e7ccc3bf45cb6116a058e6bc9773"},{"path":"results/radio_pilot_method_report_20261008/report_artifact_manifest.json","sha":"513a3e1523610962dc6507870a1eeb2084277b1d"}]
records=[]
for item in expected:
    p=ROOT/item['path']; p.parent.mkdir(parents=True,exist_ok=True)
    b=base64.b64decode((ROOT/'recovery/diagnostics'/(p.name+'.b64')).read_bytes())
    h=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest(); assert h==item['sha']
    p.write_bytes(b); records.append({'path':item['path'],'git_blob_sha1':h,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
manifest=json.loads((ROOT/'results/radio_pilot_method_report_20261008/report_artifact_manifest.json').read_bytes())
(OUT/'RESTORED_METHOD_REPORT_INPUTS.json').write_text(json.dumps({'source_commit':'13131757641c06d7bfcb10790a79811c750b1178','records':records,'all_Git_blob_SHA1_verified':True,'new_scores':False},indent=2)+'\n')
data=json.loads((ROOT/'results/radio_pilot_method_report_20261008/report_data.json').read_bytes())
print(json.dumps({'data_keys':list(data),'manifest_keys':list(manifest),'first_cell':data.get('cells',[None])[0]}))
