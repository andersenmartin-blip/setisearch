"""Restore exact archived bytes; inspect only FITS/NPY headers, never array values."""
import argparse,ast,hashlib,io,json,re,struct,subprocess,tarfile,zipfile
from pathlib import Path
from astropy.io import fits

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OLD=REPO/'work_harps_20261101/v2/extension02/raw_followup_batch03'
DP='ADP.2023-02-23T01:01:36.791'
RAW='HARPS.2023-02-22T07:40:53.531'
ANC='ADP.2023-02-23T01:01:36.792'
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(path):return digest(path.read_bytes())
def read(p):return json.loads(p.read_bytes())
def save(name,obj):(HERE/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def retain(path,data,expected=None):
    if expected:
        assert len(data)==expected['bytes'] and digest(data)==expected['sha256'],str(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_bytes()==data,'Existing file differs: '+str(path)
    else:
        with path.open('xb') as f:f.write(data)
    return {'path':str(path.relative_to(REPO)),'bytes':len(data),'sha256':digest(data)}
def npy_headers(path):
    records=[]
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            assert info.filename.endswith('.npy')
            with z.open(info) as f:
                assert f.read(6)==b'\x93NUMPY'
                version=tuple(f.read(2));size=struct.unpack('<H' if version==(1,0) else '<I',f.read(2 if version==(1,0) else 4))[0]
                assert size<=65536
                header=ast.literal_eval(f.read(size).decode('latin1' if version[0]<3 else 'utf-8').strip())
                records.append({'key':info.filename.removesuffix('.npy'),'shape':list(header['shape']),'dtype':header['descr'],'fortran_order':header['fortran_order'],'header_bytes_read':f.tell(),'array_values_read':False})
    return records
def fits_headers(path):
    with fits.open(path,memmap=True,lazy_load_hdus=False,do_not_scale_image_data=True) as hd:
        rows=[{'hdu_index':i,'XTENSION':x.header.get('XTENSION'),'NAXIS':x.header.get('NAXIS'),'fits_axes':[x.header.get('NAXIS'+str(j)) for j in range(1,int(x.header.get('NAXIS',0))+1)],'numpy_shape_from_header':[x.header.get('NAXIS'+str(j)) for j in range(int(x.header.get('NAXIS',0)),0,-1)],'BITPIX':x.header.get('BITPIX')} for i,x in enumerate(hd)]
        h=hd[0].header.copy()
    return rows,h

def trace_header_metadata(path,member,expected_orders):
    shapes,header=fits_headers(path)
    assert shapes[0]['numpy_shape_from_header']==[expected_orders,4096]
    assert header['INSTRUME']=='HARPS' and header['DATE-OBS']=='2023-02-22T07:40:53.531'
    degree=int(header['ESO DRS CAL LOC DEG CTR'])
    keys=[k for k in header.keys() if re.fullmatch(r'ESO DRS CAL LOC CTR\d+',k)]
    keys.sort(key=lambda k:int(k.removeprefix('ESO DRS CAL LOC CTR')))
    assert keys==['ESO DRS CAL LOC CTR'+str(i) for i in range(expected_orders*(degree+1))]
    coefficients=[[float(header['ESO DRS CAL LOC CTR'+str(o*(degree+1)+j)]) for j in range(degree+1)] for o in range(expected_orders)]
    identity_keys=['DATE-OBS','INSTRUME','OBJECT','EXPTIME','ESO DRS BERV','ESO DRS CAL LOC FILE','ESO DRS CAL LOC DEG CTR']
    return {'native_fits_member':member,'file_path':str(path.relative_to(REPO)),'file_sha256':sha(path),'native_hdu_shapes':shapes,'primary_identity_headers':{k:header.get(k) for k in identity_keys},'trace_polynomial_degree':degree,'trace_order_count':expected_orders,'coefficients_ascending_by_zero_based_order':coefficients,'trace_header_key_pattern':'ESO DRS CAL LOC CTR{order*(degree+1)+power}','coefficients_from_primary_header_only':True,'array_values_read':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input-archive',type=Path,required=True);args=parser.parse_args()
    archive_manifest=read(OLD/'checkpoints/INPUT_ARCHIVES.json')
    original=next(a for a in archive_manifest['archives'] if any(p['dp_id']==DP for p in a['products']))
    assert args.input_archive.name==original['filename']
    assert args.input_archive.stat().st_size==original['bytes'] and sha(args.input_archive)==original['sha256']
    selected=[p for p in original['products'] if p['dp_id']==DP];assert len(selected)==2
    files=[];products={}
    with zipfile.ZipFile(args.input_archive) as z:
        for product in selected:
            data=z.read(product['relative_path']);path=HERE/'source_products'/Path(product['relative_path']).name
            files.append(retain(path,data,product));products[product['kind']]=path
    parts=read(OLD/'EVIDENCE_PARTS.json');evidence=read(OLD/'EVIDENCE_ARCHIVE.json')
    payloads=[]
    for part in parts['parts']:
        data=(OLD/part['path']).read_bytes();assert len(data)==part['bytes'] and digest(data)==part['sha256'];payloads.append(data)
    data=b''.join(payloads);assert len(data)==evidence['bytes'] and digest(data)==evidence['sha256']
    wanted=['native/V2E2-0235_o50.npz','reference/'+DP.replace(':','_')+'.json']
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in wanted:
            record=next(r for r in evidence['members'] if r['path']==name)
            files.append(retain(HERE/'evidence'/name,z.read(name),record))
    native_member='data/reduced/2023-02-21/'+RAW+'_e2ds_A.fits'
    native_paths={};native_members={}
    with tarfile.open(products['ANCILLARY']) as t:
        for fiber in ['A','B']:
            member='data/reduced/2023-02-21/'+RAW+'_e2ds_'+fiber+'.fits'
            matching=[m for m in t.getmembers() if m.name.endswith('_e2ds_'+fiber+'.fits')]
            assert len(matching)==1 and matching[0].name==member and matching[0].isfile()
            native_paths[fiber]=HERE/'derived'/(RAW.replace(':','_')+'_e2ds_'+fiber+'.fits');native_members[fiber]=member
            files.append(retain(native_paths[fiber],t.extractfile(matching[0]).read()))
    native_path=native_paths['A']
    raw_path=HERE/'derived'/(RAW.replace(':','_')+'.fits')
    raw_bytes=subprocess.run(['gzip','-cd',str(products['RAW'])],capture_output=True,check=True,timeout=60).stdout
    files.append(retain(raw_path,raw_bytes));del raw_bytes
    raw_shapes,rh=fits_headers(raw_path);native_shapes,nh=fits_headers(native_path)
    assert rh['ARCFILE'].removesuffix('.fits')==RAW and rh['DATE-OBS']=='2023-02-22T07:40:53.531' and rh['INSTRUME']=='HARPS'
    assert nh['DATE-OBS']==rh['DATE-OBS'] and nh['INSTRUME']=='HARPS'
    assert raw_shapes[1]['numpy_shape_from_header']==[4096,2148] and raw_shapes[2]['numpy_shape_from_header']==[4096,2148]
    assert native_shapes[0]['numpy_shape_from_header']==[72,4096]
    mapping=read(OLD/'NATIVE_MAPPING.json');order=next(r for r in mapping['orders'] if r['review_id']=='V2E2-0235');spectrum=next(r for r in mapping['spectra'] if r['dp_id']==DP)
    assert (order['order'],order['native_pixel'],order['raw_row'],order['raw_column'])==(50,956,3139,2323.7701943175816)
    orientation={k:spectrum['grid_best'][k] for k in ['row_flip','column_flip','argument_flip']}
    assert orientation=={'row_flip':True,'column_flip':False,'argument_flip':True}
    degree=int(nh['ESO DRS CAL LOC DEG CTR']);coeff=[float(nh['ESO DRS CAL LOC CTR'+str(50*(degree+1)+j)]) for j in range(degree+1)]
    mapped=sum(c*3139**j for j,c in enumerate(coeff));assert abs(mapped-order['raw_column'])<1e-8
    trace={'dp_id':DP,'raw_id':RAW,'ancillary_id':ANC,'event':'V2E2-0235','order_zero_based':50,'native_pixel_zero_based':956,'raw_row_zero_based':3139,'raw_column_zero_based':order['raw_column'],'orientation':orientation,'trace_polynomial_degree':degree,'trace_polynomial_coefficients_ascending':coeff,'trace_coefficient_header_keys':['ESO DRS CAL LOC CTR'+str(50*(degree+1)+j) for j in range(degree+1)],'polynomial_argument':'native x=4095-raw_row; argument_flip=true gives polynomial argument=raw_row; column_flip=false.','raw_mosaic':'hstack([HDU1[:,50:2098],HDU2[:,50:2098]]) in zero-based Python slices; no transpose or rotation. Both source HDUs are4096rows×2148columns; assembled4096×4096.','raw_hdu_shapes':raw_shapes,'native_hdu_shapes':native_shapes,'native_fits_member':native_member,'native_local_flanks_half_open':[[-280,-80],[81,281]],'raw_flanks_half_open_native_order':[[3220,3420],[2859,3059]],'raw_flanks_half_open_sorted':[[2859,3059],[3220,3420]],'required_raw_row_span_half_open':[2859,3420],'original_cutout_raw_rows_half_open':[3124,3155],'original_cutout_raw_columns_half_open':[2308,2341],'original_cutout_covers_control_rows':False,'array_values_read':False,'trace_registration_changed':False}
    trace['fiber_trace_metadata']={fiber:trace_header_metadata(native_paths[fiber],native_members[fiber],count) for fiber,count in [('A',72),('B',71)]}
    trace['fiber_order_index_caveat']='A has72 orders and B has71; matching physical orders cannot be assumed to share integer indices.'
    save('TRACE_METADATA.json',trace)
    npz=HERE/'evidence/native/V2E2-0235_o50.npz';shape_info=npy_headers(npz)
    assert next(r['shape'] for r in shape_info if r['key']=='raw_cutout')==[31,33]
    source_names=['NATIVE_MAPPING.json','LOCAL_TRACE_AUDIT.json','FIVE_WINDOW_MAPPING_AUDIT.json','EVIDENCE_ARCHIVE.json','EVIDENCE_PARTS.json','checkpoints/INPUT_ARCHIVES.json','checkpoints/LIBRARY_INPUTS.json','extract_native.py','local_registration.py','registration.py']
    source_hashes={str((OLD/n).relative_to(REPO)):sha(OLD/n) for n in source_names}
    source_hashes[str((REPO/'work_harps_20261102_may_quality/scientific_review/NEXT_STEP.md').relative_to(REPO))]=sha(REPO/'work_harps_20261102_may_quality/scientific_review/NEXT_STEP.md')
    inventory={'status':'RESTORED_VERIFIED_BYTES_HEADER_ONLY_INVENTORY','identities':{'dp_id':DP,'raw_id':RAW,'ancillary_id':ANC,'event':'V2E2-0235'},'files':files,'npy_headers_only':shape_info,'raw_header_summary':{k:rh.get(k) for k in ['ARCFILE','DATE-OBS','INSTRUME','OBJECT','EXPTIME']},'native_header_summary':{k:nh.get(k) for k in ['DATE-OBS','INSTRUME','OBJECT','EXPTIME','ESO DRS BERV']},'archive':{k:original[k] for k in ['filename','bytes','sha256']},'archive_local_path_used':str(args.input_archive),'archive_products_selected':selected,'evidence_zip':{k:evidence[k] for k in ['bytes','sha256','member_count']},'source_hashes':source_hashes,'full_raw_control_coverage_available':True,'existing_cutout_control_coverage_available':False,'science_array_values_interpreted':0,'new_network_requests':0,'trace_registration_changed':False}
    save('INPUT_INVENTORY.json',inventory)
    save('RESTORE_RECEIPT.json',{'status':'PASS','restored_exact_files':len(files),'raw_archive_products':2,'committed_evidence_members':2,'derived_exact_byte_members':3,'all_saved_files_rehashed':all(sha(REPO/r['path'])==r['sha256'] for r in files),'source_hashes_unchanged':all(sha(REPO/n)==h for n,h in source_hashes.items()),'array_values_read':False,'network_requests':0})
    print(json.dumps({'status':'PASS','files':files,'npy_headers':shape_info,'trace_degree':degree,'trace_coefficients_ascending':coeff},indent=2))

if __name__=='__main__':main()
