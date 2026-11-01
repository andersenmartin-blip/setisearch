"""Checkpoint verified raw batch02 payloads without mutating analysis artifacts."""
from pathlib import Path
import argparse,hashlib,json,zipfile,datetime
OUT=Path(__file__).resolve().parent;BASE=OUT.parent.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--destination',required=True);args=a.parse_args()
 dest=Path(args.destination);dest.mkdir(parents=True,exist_ok=True)
 manifest=json.loads((OUT/'products/MANIFEST.json').read_text());products=manifest['products']
 assert len(products)==32 and all(r['status']=='DOWNLOADED'for r in products),'Checkpoint requires complete32products'
 groups=[products[i:i+8]for i in range(0,len(products),8)];archives=[]
 for i,group in enumerate(groups,1):
  path=dest/f'SETI_HARPS_RAW_BATCH02_INPUTS_PART{i}_2026-11-01.zip';assert not path.exists(),'No overwrite'
  members=[]
  with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3)as z:
   for r in group:
    p=BASE/r['relative_path'];assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
    z.write(p,r['relative_path']);members.append(dict(relative_path=r['relative_path'],sha256=r['sha256'],bytes=r['bytes'],dp_id=r['dp_id'],archive_id=r['archive_id'],kind=r['kind']))
    receipt=p.with_name(p.name+'.json');z.write(receipt,str(receipt.relative_to(BASE)))
   for name in ['products/MANIFEST.json','FOLLOWUP_FREEZE.json','SELECTED_EXPOSURES.csv','SELECTED_EVENTS.csv','PREREGISTRATION_RECEIPT.json']:
    p=OUT/name;z.write(p,str(p.relative_to(BASE)))
   z.writestr('RESTORE_BATCH02_INPUTS.txt','Members are relative to work_harps_20261101. Extract into separate staging; verify SHA256 against products/MANIFEST.json, then copy only payloads/receipts into the current worktree. Do not overwrite current status, plans or newer evidence with archive copies. Four parts contain32 original ESO payload products,16 complete exposurepairs. No added observing time.\n')
  with zipfile.ZipFile(path)as z:assert z.testzip()is None
  archives.append(dict(filename=path.name,local_path=str(path.resolve()),bytes=path.stat().st_size,sha256=sha(path),products=members))
  print(path.name,path.stat().st_size,flush=True)
 checkpoint=OUT/'checkpoints';checkpoint.mkdir(exist_ok=True)
 (checkpoint/'INPUT_ARCHIVES.json').write_text(json.dumps(dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_products=16,ancillary_products=16,archives=archives),indent=2)+'\n')
 (dest/'upload_request.json').write_text(json.dumps({'uploads':[dict(local_path=r['local_path'],purpose='create_library_file',library_artifact_type='other')for r in archives]},indent=2))
if __name__=='__main__':main()
