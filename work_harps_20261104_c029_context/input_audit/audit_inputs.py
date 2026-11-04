"""Independent byte/header custody audit. No spectral or detector values decoded."""
from pathlib import Path
import ast, datetime, hashlib, json, math, struct, tarfile, zipfile
from astropy.io.fits import Header

HERE = Path(__file__).resolve().parent
PHASE = HERE.parent
ROOT = HERE.parents[1]
OLD = ROOT / 'work_harps_20261101/v2/extension02'
CB = 3866.125
C = 299792.458
DP = 'ADP.2025-04-28T01:01:15.579'
BERV = 5.77068898867443
CT = CB / (1 + BERV / C)
checks = []

def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(v, label):
    if not v: raise AssertionError(label)
    checks.append(label)

def headers(path):
    result = []
    with path.open('rb') as f:
        while f.tell() < path.stat().st_size:
            chunks = []
            while True:
                b = f.read(2880)
                ck(len(b) == 2880, 'Complete FITS header block')
                chunks.append(b)
                if any(b[i:i+8] == b'END     ' for i in range(0,2880,80)): break
                ck(len(chunks) < 183, 'Bounded FITS header')
            h = Header.fromstring(b''.join(chunks).decode('ascii'), sep='')
            result.append(h)
            n = math.prod(h['NAXIS'+str(i)] for i in range(1,h['NAXIS']+1)) if h['NAXIS'] else 0
            n = (n+h.get('PCOUNT',0))*h.get('GCOUNT',1)*abs(h['BITPIX'])//8
            f.seek(((n+2879)//2880)*2880, 1)
        ck(f.tell() == path.stat().st_size, 'Exact FITS end position')
    return result

def poly(coeff, x):
    return math.fsum(v*x**i for i,v in enumerate(coeff))

def main():
    inv = read(PHASE/'inputs/INPUT_INVENTORY.json')
    handoff = read(ROOT/'work_harps_20261104_c028_context/NEXT_ACTION.json')
    ck(inv['target']=='HD126093' and inv['events']=={'V2E2-0261': 'ADP.2025-04-28T01:01:15.579', 'V2E2-0266': 'ADP.2025-05-30T01:00:44.357', 'V2E2-0272': 'ADP.2025-05-31T01:00:40.760'}, 'Own target and three complete events')
    ck([r['dp_id'] for r in inv['merged_spectra']]==[r['dp_id'] for r in handoff['existing_cohort_epochs']], 'Exact six existing epochs')
    ck(len(inv['files'])==18 and len({x['path'] for x in inv['files']})==18, 'Eighteen distinct restored files')
    for item in inv['files']:
        p=ROOT/item['path']
        ck(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'], 'Exact restored bytes '+p.name)
    for group in [inv['source_hashes'], handoff['source_hashes']]:
        for p,h in group.items(): ck(sha(ROOT/p)==h, 'Historical source '+p)
    cache=ROOT.parent/'seti_input_cache'
    archives={r['filename']:cache/r['filename'] for r in inv['archives']}
    for item in inv['archives']:
        p=archives[item['filename']]
        ck(p.stat().st_size==item['bytes'] and sha(p)==item['sha256'], 'Whole archive '+p.name)
    science=next(p for n,p in archives.items() if 'EXTENSION02_INPUTS' in n)
    merged_headers={}
    with zipfile.ZipFile(science) as z:
        for item in inv['merged_spectra']:
            p=ROOT/item['file']['path']; hs=headers(p); h,t=hs
            ck(hashlib.sha256(z.read(item['archive_member'])).hexdigest()==sha(p), 'Merged archive member '+item['dp_id'])
            ck(len(hs)==2 and h['NAXIS']==0 and t['NAXIS2']==1, 'Single-exposure table '+item['dp_id'])
            ck(h['INSTRUME']=='HARPS' and h['OBJECT'].replace(' ','')=='HD126093' and h['ARCFILE']==item['dp_id']+'.fits' and h['PROV1']==item['raw_id']+'.fits', 'Merged identity/progenitor '+item['dp_id'])
            ck(h['SPECSYS']=='BARYCENT' and h['NCOMBINE']==1 and h['FLUXCAL']=='UNCALIBRATED', 'Frame/calibration '+item['dp_id'])
            ck([t['TTYPE'+str(i)] for i in [1,2,3]]==['WAVE','FLUX','ERR'] and t['TUNIT1']=='angstrom' and t['TUNIT2']==t['TUNIT3']=='adu' and 'obs.atmos' in t['TUCD1'], 'Merged air wavelength and ADU '+item['dp_id'])
            ck('not available' in t.get('TCOMM3','').lower(), 'ERR explicitly unavailable '+item['dp_id'])
            ck(h['ESO DRS BERV']==item['berv_km_s'] and h['DATE-OBS']==item['date_obs'] and h['MJD-OBS']==item['mjd_obs'], 'Own dates and BERV '+item['dp_id'])
            ck(all(h.get(k)==v for k,v in item['primary_header'].items()), 'Recorded merged header '+item['dp_id'])
            merged_headers[item['dp_id']]=h
    ck(merged_headers[DP]['ESO DRS BERV']==BERV, 'Own April discovery anchor')
    ck(max(h['ESO DRS BERV'] for h in merged_headers.values())-min(h['ESO DRS BERV'] for h in merged_headers.values())==29.26984563734743, 'Own target BERV span')
    old=read(OLD/'raw_followup_batch04/NATIVE_MAPPING.json')
    ck(len(inv['native_products'])==3, 'Three native discovery products')
    geometry=[]
    for native in inv['native_products']:
        dp=native['dp_id']; p=ROOT/native['file']['path']; h=headers(p)[0]
        ck([h['NAXIS2'],h['NAXIS1']]==[72,4096] and h['INSTRUME']=='HARPS' and h['OBJECT'].replace(' ','')=='HD126093', 'Native shape/target')
        ck(h['DATE-OBS']==merged_headers[dp]['DATE-OBS'] and h['ESO DRS BERV']==merged_headers[dp]['ESO DRS BERV'] and h.get('BUNIT') is None, 'Native own exposure and unspecified units')
        anc=ROOT/native['ancillary_file']['path']
        part=next(r for r in read(OLD/'raw_followup_batch04/checkpoints/INPUT_ARCHIVES.json')['archives'] if any(m['dp_id']==dp and m['kind']=='ANCILLARY' for m in r['products']));archive=archives[part['filename']]
        with zipfile.ZipFile(archive) as z: ck(hashlib.sha256(z.read(native['ancillary_archive_member'])).hexdigest()==sha(anc), 'Ancillary member identity')
        with tarfile.open(anc) as z:
            member=z.getmember(native['native_tar_member'])
            ck(member.isfile() and hashlib.sha256(z.extractfile(member).read()).hexdigest()==sha(p), 'Native TAR member identity')
        selected=[]
        for order in range(72):
            co=[h['ESO DRS CAL TH COEFF LL'+str(4*order+i)] for i in range(4)]
            lo,hi=poly(co,0),poly(co,4095)
            vertices=[0.,4095.]; vertex=-co[2]/(3*co[3]) if co[3] else -1
            if 0<vertex<4095: vertices.append(vertex)
            ck(min(co[1]+2*co[2]*x+3*co[3]*x*x for x in vertices)>0, 'Monotonic header wavelength '+str(order))
            cover=lo<(CB/(1+h['ESO DRS BERV']/C))<hi
            scan=next(r for r in inv['all_order_header_scan'] if r['order']==order and r['dp_id']==dp)
            ck(cover==scan['selected_for_profile']==scan['covers_any_original_event_center'], 'Independent all-order selection '+str(order))
            ck(all(abs(a-b)<1e-9 for a,b in zip([lo,hi],scan['header_endpoint_topocentric_air_angstrom'])), 'Independent endpoint '+str(order))
            if not cover: continue
            selected.append(order)
            for frame in ['barycentric','topocentric']:
                factor=1+h['ESO DRS BERV']/C if frame=='barycentric' else 1.
                center=CB if frame=='barycentric' else CT
                ends=[lo*factor,hi*factor]; offsets=[x-center for x in ends]
                g=native['orders'][str(order)]['fixed_frame_header_geometry'][frame]
                ck(all(abs(a-b)<1e-9 for a,b in zip(ends,g['header_endpoint_air_angstrom'])), 'Fresh frame geometry '+str(order)+'/'+frame)
                expected=[offsets[0]<=-3 and offsets[1]>=3, offsets[0]<=-.25 and offsets[1]>=.25,offsets[0]<=-3 and offsets[1]>=-1.5,offsets[0]<=1.5 and offsets[1]>=3]
                keys=['full_context_geometrically_covered','full_core_geometrically_covered','negative_reference_flank_geometrically_covered','positive_reference_flank_geometrically_covered']
                ck([g[k] for k in keys]==expected, 'Header support flags '+str(order)+'/'+frame)
                geometry.append({'dp_id':dp,'order':order,'frame':frame,'offset_endpoints_angstrom':offsets,'geometric_grid_centers':sum(offsets[0]<=i/100<=offsets[1] for i in range(-300,301)),**{k:g[k] for k in keys}})
        ck(selected==native['covering_orders']==[2,3] and len(inv['all_order_header_scan'])==216, 'Own two covering orders retained from all 72 headers')
        for r in [r for r in inv['mapping_records'] if r['dp_id']==dp]:
            original=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order'])
            names=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
            ck([r[k] for k in names]==([True,True,True,True] if r['event']=='V2E2-0272' else [True,False,False,True]), 'Separate mapping history '+str(r['order']))
            ck(all(r[k]==original[k] for k in ['native_pixel','raw_row','raw_column']) and r['registration_changed'] is False, 'Original coordinates '+str(r['order']))
    for r in inv['saved_native_raw_cutouts']:
        with zipfile.ZipFile(ROOT/r['file']['path']) as z:
            shape_headers=[]
            for name in z.namelist():
                with z.open(name) as f:
                    ck(f.read(6)==b'\x93NUMPY', 'NPY magic '+name)
                    version=f.read(2); n=struct.unpack('<H' if version==b'\x01\x00' else '<I',f.read(2 if version==b'\x01\x00' else 4))[0]
                    meta=ast.literal_eval(f.read(n).decode('latin1').strip());shape_headers.append({'key':name[:-4],'shape':list(meta['shape']),'dtype':meta['descr'],'fortran_order':meta['fortran_order']})
            ck(shape_headers==r['npy_headers'], 'Original raw container header '+str(r['order']))
    history=inv['historical_raw_review_records']
    ck(all(r['code']=='U' for stage in ['primary','secondary','adopted'] for r in history[stage]), 'Original U/U/U remains')
    report={'status':'PASS_INDEPENDENT_C029_HEADER_AND_CUSTODY_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'checks':checks,'native_header_orders_scanned':216,'native_geometry':geometry,'restored_files':18,'merged_epochs':6,'native_products':3,'saved_raw_panels':6,'observational_array_values_decoded':0,'network_requests':0,'inventory_sha256':sha(PHASE/'inputs/INPUT_INVENTORY.json'),'restorer_sha256':sha(PHASE/'inputs/restore_inputs.py'),'audit_script_sha256':sha(Path(__file__)),'limitation':'Separate implementation executed by the same assistant; no independent human or separate-agent review is claimed.'}
    (HERE/'INPUT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks']},indent=2))

if __name__=='__main__': main()
