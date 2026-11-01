"""Fresh-process integrity and three-exposure wider-cutout reconstruction."""
from pathlib import Path
import json,csv,hashlib,io,subprocess,datetime
import numpy as np
from astropy.io import fits
OUT=Path(__file__).resolve().parent;V2=OUT.parent;BASE=V2.parent;OLD=V2/'triage_batch02'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'PLAN.json').read_text());a=json.loads((OUT/'MAPPING_AUDIT.json').read_text());old=json.loads((OLD/'NATIVE_MAPPING.json').read_text());products=json.loads((OLD/'products/MANIFEST.json').read_text())['products']
checks=[]
for rel,digest in plan['input_hashes'].items():assert sha(V2/rel)==digest;checks.append(dict(path=rel,sha256=digest))
ids=[r['review_id'] for r in csv.DictReader((OUT/'SELECTED_HITS.csv').open())]
assert len(ids)==43 and [r['review_id'] for r in a['events']]==ids
assert len(a['orders'])==81 and len({(r['review_id'],r['order']) for r in a['orders']})==81
assert sum(r['status']=='EXTRACTED' for r in a['orders'])==80
for r in a['orders']:
    if r['status']!='EXTRACTED':continue
    d=np.load(OUT/r['cutout']);q=next(x for x in old['orders'] if x['review_id']==r['review_id'] and x['order']==r['order']);e=np.load(OLD/q['cutout'])
    assert d['raw_cutout'].shape==(31,33)
    assert np.array_equal(d['raw_cutout'][5:26,4:29],e['raw_cutout'])
    assert np.array_equal(d['native_wave'],e['native_wave']) and np.array_equal(d['native_flux'],e['native_flux'])
    assert np.array_equal(d['raw_background'],np.median(d['raw_cutout'][np.r_[0:10,21:31]],axis=0))
    assert np.array_equal(d['raw_excess'],d['raw_cutout']-d['raw_background'][None,:])
    assert r['raw_column']==q['raw_column'] and r['raw_row']==q['raw_row']
dp_ids=[r['dp_id'] for r in a['spectra']];chosen=[dp_ids[i] for i in [0,len(dp_ids)//2,len(dp_ids)-1]];sample=[]
for dp in chosen:
    rec=next(r for r in products if r['dp_id']==dp and r['kind']=='RAW');assert sha(BASE/rec['relative_path'])==rec['sha256']
    rawbytes=subprocess.run(['gzip','-cd',str(BASE/rec['relative_path'])],capture_output=True,check=True).stdout
    with fits.open(io.BytesIO(rawbytes)) as hd:raw=np.concatenate([hd[1].data[:,50:2098],hd[2].data[:,50:2098]],axis=1).astype(float)
    tested=[]
    for r in a['orders']:
        if r['dp_id']!=dp or r['status']!='EXTRACTED':continue
        x=round(r['raw_column']);y=r['raw_row'];cut=raw[y-15:y+16,x-16:x+17];d=np.load(OUT/r['cutout']);assert np.array_equal(cut,d['raw_cutout']);tested.append(dict(review_id=r['review_id'],order=r['order'],max_abs_raw_difference=0.0))
    sample.append(dict(dp_id=dp,cutouts=tested))
record=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASSED',same_agent_fresh_process=True,independent_human_validation=False,original_hashes_unchanged=checks,events=43,covering_order_records=81,complete_wider_cutouts_checked=80,coordinates_changed=False,old_native_and_raw_centres_identical=True,sampling='First, middle and last exposure in saved metadata order',sampled_exposures=sample,script_sha256=sha(Path(__file__)))
(OUT/'OUTPUT_VERIFICATION.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(status='PASSED',all_cutouts=80,sampled_raw_cutouts=sum(len(r['cutouts']) for r in sample))))
