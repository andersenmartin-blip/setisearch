"""Select exact nine frozen source members from already-restored input packages."""
from pathlib import Path
import argparse,hashlib,json,zipfile
OUT=Path(__file__).resolve().parent
ARCHIVES=None
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archives',required=True,type=Path);args=parser.parse_args();archives=args.archives.resolve()
 plan=json.loads((OUT/'PLAN.json').read_text());needed={r['relative_path']:r for r in plan['original_product_inputs']};found={}
 for archivepath in sorted(archives.glob('*.zip')):
  with zipfile.ZipFile(archivepath)as archive:
   names=set(archive.namelist())
   for rel,r in needed.items():
    if rel not in names:continue
    assert rel not in found,'Repeated source member'
    data=archive.read(rel);assert len(data)==r['bytes']and hashlib.sha256(data).hexdigest()==r['sha256'],rel
    target=OUT/'inputs/source_products'/Path(rel).name;target.parent.mkdir(exist_ok=True)
    if target.exists():assert target.read_bytes()==data
    else:target.write_bytes(data)
    found[rel]={**r,'local_path':str(target.relative_to(OUT)),'archive_filename':archivepath.name}
 assert set(found)==set(needed),'Missing original source'
 (OUT/'SOURCE_PRODUCTS.json').write_text(json.dumps({'status':'PASS','products':[found[r['relative_path']]for r in plan['original_product_inputs']],'source_array_values_inspected':False},indent=2)+'\n');print('PASS9sourceproducts restored and hashesverified')
if __name__=='__main__':main()
