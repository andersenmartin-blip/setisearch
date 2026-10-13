"""Combine two checked numerical modules without omitting their manifests."""
import argparse, hashlib, json, zipfile
from pathlib import Path

def main():
    a=argparse.ArgumentParser();a.add_argument('--on',type=Path,required=True);a.add_argument('--dc',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--portable-receipt',type=Path,required=True);a.add_argument('--portable-log',type=Path,required=True)
    args=a.parse_args();assert not args.out.exists()
    proof=json.loads(args.portable_receipt.read_text());assert proof['status'].startswith('PASS_PORTABLE54')
    items=[]
    with zipfile.ZipFile(args.out,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        def add(name,b):
            z.writestr(name,b);items.append({'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
        for p,prefix in [(args.on,''),(args.dc,'DC_PORTABLE/')]:
            with zipfile.ZipFile(p) as src:
                assert src.testzip() is None
                for n in src.namelist():add(prefix+n,src.read(n))
        add('ON_PORTABLE_VALIDATION/QA_RECEIPT.json',args.portable_receipt.read_bytes())
        add('ON_PORTABLE_VALIDATION/RUN.log',args.portable_log.read_bytes())
        add('README.txt',('SETI - samlet resultatpakke, 13. oktober 2026\n\nON-burst: 288 nye kort, 1170 scoreaudits og 54 faste kontekster.\nDC-alternativer: 7083 tidligere DC-ramte carriers, 7074 tilladte alternativer, ni EMPTY. TOP9 er uændret.\nAlle kilde-QA og gemte-crop-reproduktioner består. Ingen kvalificeret SETI-detektion.\n\nLæs seti_burst_on/delivery/RESULTS.md og seti_burst_on/REPLAY_README.md.\nDC-reproduktion: DC_PORTABLE/analysis/dc_alternatives/reproduction/README.md.\nKør scripts fra de angivne modulrødder; ingen fulde HDF5-filer medfølger.\nON-replay kræver de dokumenterede runtimebiblioteker; DC-replay kræver NumPy 2.3.5.\nRESULT_PACKAGE_MANIFEST.json indeholder SHA256 for alle andre medlemmer.\n').encode())
        z.writestr('RESULT_PACKAGE_MANIFEST.json',json.dumps({'schema':'SETI_COMBINED_RESULT_PACKAGE_V1','date':'2026-10-13','files':items,'new_telescope_requests':0,'new_observation':False,'qualified_SETI_detection':False,'original_AB':'FAIL_CLOSED'},indent=2)+'\n')
    with zipfile.ZipFile(args.out) as z:
        assert z.testzip() is None and len(z.namelist())==len(items)+1
        for r in items:
            b=z.read(r['path']);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
    receipt={'status':'PASS_COMBINED_ARCHIVE_CRC_ALL_MEMBER_SHA256_AND_ACTUAL_PORTABLE_REPLAYS','file':str(args.out),'bytes':args.out.stat().st_size,'sha256':hashlib.sha256(args.out.read_bytes()).hexdigest(),'members':len(items)+1,'payloads':len(items),'source_HDF5_files':0,'ON_maps':288,'ON_context_profiles':54,'DC_recovered_alternatives':7074,'portable_ON_QA_receipt_sha256':hashlib.sha256(args.portable_receipt.read_bytes()).hexdigest()}
    (args.out.parent/'RESULT_PACKAGE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
