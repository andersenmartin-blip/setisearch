"""Restore exact existing C033 inputs; inspect FITS/NPY headers, never array values."""
import argparse, ast, csv, hashlib, io, json, re, struct, tarfile, zipfile
from pathlib import Path
from astropy.io import fits

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OLD=REPO/'work_harps_20261101/v2/extension02'
EVENTS={'V2E2-0265': 'ADP.2025-04-28T01:01:15.579', 'V2E2-0270': 'ADP.2025-05-30T01:00:44.357', 'V2E2-0274': 'ADP.2025-05-31T01:00:40.760', 'V2E2-0279': 'ADP.2025-06-28T01:01:54.505'}
CENTER_BARY_AIR=3880.35
EVENT_CENTERS={'V2E2-0265': 3880.35, 'V2E2-0270': 3880.35, 'V2E2-0274': 3880.3525, 'V2E2-0279': 3880.3475}
DISCOVERY_BERV_KM_S=5.77068898867443
SPEED_OF_LIGHT_KM_S=299792.458
ANCHOR_TOPO_AIR=CENTER_BARY_AIR/(1+DISCOVERY_BERV_KM_S/SPEED_OF_LIGHT_KM_S)
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(p.read_bytes())
def read(p):return json.loads(p.read_bytes())
def write(n,x):(HERE/n).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def record(p):return {'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)}
def retain(p,b,expected=None):
    if expected:assert len(b)==int(expected['bytes']) and digest(b)==expected['sha256'],str(p)
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==b,'Differing existing file: '+str(p)
    else:
        with p.open('xb') as f:f.write(b)
    return record(p)
def npy_headers(p):
    out=[]
    with zipfile.ZipFile(p) as z:
        for name in z.namelist():
            assert name.endswith('.npy')
            with z.open(name) as f:
                assert f.read(6)==b'\x93NUMPY'
                version=tuple(f.read(2));assert version in [(1,0),(2,0),(3,0)]
                n=struct.unpack('<H' if version==(1,0) else '<I',f.read(2 if version==(1,0) else 4))[0];assert n<=65536
                h=ast.literal_eval(f.read(n).decode('utf-8' if version==(3,0) else 'latin1').strip())
                out.append({'key':name[:-4],'shape':list(h['shape']),'dtype':h['descr'],'fortran_order':h['fortran_order']})
    return out
def header(p):
    with fits.open(p,memmap=True,lazy_load_hdus=False,do_not_scale_image_data=True) as h:
        return [x.header.copy() for x in h]
def compact(h,keys):return {k:h.get(k) for k in keys}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive-dir',type=Path,action='append',required=True);a=ap.parse_args()
    source_names=['acquisition/DOWNLOAD_MANIFEST.csv','checkpoints/INPUT_CHECKPOINTS.json','epoch_followup/INPUT_CHECKS.json','epoch_followup/EVENT_RESULTS.json','raw_followup_batch04/checkpoints/INPUT_ARCHIVES.json','raw_followup_batch04/NATIVE_MAPPING.json','raw_followup_batch04/extract_native.py','raw_followup_batch04/EVIDENCE_ARCHIVE.json','raw_followup_batch04/EVIDENCE_PARTS.json','raw_followup_batch04/ADOPTED_DISPOSITIONS.csv','raw_followup_batch04/PRIMARY_VISUAL_REVIEW.json','raw_followup_batch04/SECONDARY_VISUAL_REVIEW.json','raw_followup_batch04/REVIEW_COMPARISON.json']
    source_hashes={str((OLD/n).relative_to(REPO)):sha(OLD/n) for n in source_names}
    handoff=REPO/'work_harps_20261105_c031_context/NEXT_ACTION.json'
    source_hashes[str(handoff.relative_to(REPO))]=sha(handoff)
    assert {r['candidate_id']:r['dp_id'] for r in read(handoff)['queue_rows']}==EVENTS
    epochs=[r for r in read(OLD/'epoch_followup/INPUT_CHECKS.json') if r['target']=='HD126093'];assert len(epochs)==6
    downloads={r['dp_id']:r for r in csv.DictReader((OLD/'acquisition/DOWNLOAD_MANIFEST.csv').open()) if r['canonical_target']=='HD126093'}
    assert set(downloads)=={r['dp_id'] for r in epochs}
    science_part=next(p for p in read(OLD/'checkpoints/INPUT_CHECKPOINTS.json')['parts'] if all(r['dp_id'] in p['exposure_ids'] for r in epochs))
    raw_parts=read(OLD/'raw_followup_batch04/checkpoints/INPUT_ARCHIVES.json')['archives']
    selected_parts={};members={};ancillary_names={}
    for event,dp in EVENTS.items():
        part=next(p for p in raw_parts if any(m['dp_id']==dp and m['kind']=='ANCILLARY' for m in p['products']))
        selected_parts[event]=part
        members[event]=next(m for m in part['products'] if m['dp_id']==dp and m['kind']=='ANCILLARY')
        ancillary_names[event]=Path(members[event]['relative_path']).name
    archives=[];archive_paths={}
    for p in {p['filename']:p for p in [science_part,*selected_parts.values()]}.values():
        found=[d/p['filename'] for d in a.archive_dir if (d/p['filename']).is_file()];assert found,'Missing '+p['filename']
        cache=found[0];assert cache.stat().st_size==p['bytes'] and sha(cache)==p['sha256']
        archive_paths[p['filename']]=cache;archives.append({k:p[k] for k in ['filename','bytes','sha256']})
    files=[];merged=[]
    with zipfile.ZipFile(archive_paths[science_part['filename']]) as z:
        for e in epochs:
            d=downloads[e['dp_id']];m=next(m for m in science_part['members'] if m['path']==d['relative_path']);assert m['sha256']==d['sha256']==e['sha256']
            p=HERE/'merged'/Path(m['path']).name;files.append(retain(p,z.read(m['path']),m));h=header(p);ph,th=h
            assert ph['ARCFILE'].removesuffix('.fits')==e['dp_id'] and ph['INSTRUME']=='HARPS' and ph['OBJECT'].replace(' ','')=='HD126093'
            assert ph['SPECSYS']=='BARYCENT' and ph['NCOMBINE']==1 and th['NAXIS2']==1
            assert [th['TTYPE'+str(i)] for i in [1,2,3]]==['WAVE','FLUX','ERR']
            assert th['TUNIT1']=='angstrom' and th['TUNIT2']==th['TUNIT3']=='adu'
            assert abs(ph['ESO DRS BERV']-e['berv_km_s'])<1e-10
            assert ph['PROV1'].removesuffix('.fits')==d['expected_raw_progenitor_id']
            merged.append({'dp_id':e['dp_id'],'raw_id':d['expected_raw_progenitor_id'],'file':record(p),'discovery_for':[k for k,v in EVENTS.items() if v==e['dp_id']],'date_obs':e['date_obs'],'mjd_obs':e['mjd_obs'],'berv_km_s':e['berv_km_s'],'primary_header':compact(ph,['ARCFILE','PROV1','INSTRUME','OBJECT','DATE-OBS','EXPTIME','MJD-OBS','SPECSYS','FLUXCAL','NCOMBINE','WAVELMIN','WAVELMAX','SPEC_BIN','SPEC_RES','SNR','ESO DRS BERV']),'table_header':compact(th,['NAXIS1','NAXIS2','TTYPE1','TTYPE2','TTYPE3','TFORM1','TFORM2','TFORM3','TUNIT1','TUNIT2','TUNIT3','TUCD1','TCOMM3']),'archive_member':m['path']})
    old=read(OLD/'raw_followup_batch04/NATIVE_MAPPING.json')
    native=[];mapping=[];excluded=[];coverage=[];all_order_scan=[]
    representatives={}
    for event,dp in EVENTS.items():representatives.setdefault(dp,event)
    for dp,event in representatives.items():
        related=[e for e,d in EVENTS.items() if d==dp]
        pinfo=selected_parts[event];m=members[event];member=m.get('path',m.get('relative_path'))
        with zipfile.ZipFile(archive_paths[pinfo['filename']]) as z:
            anc=HERE/'source_products'/ancillary_names[event];files.append(retain(anc,z.read(member),m))
        spec=next(s for s in old['spectra'] if s['dp_id']==dp)
        assert sha(anc)==spec['ancillary_sha256']
        with tarfile.open(anc) as t:
            tm=t.getmember(spec['native_member']);assert tm.isfile()
            p=HERE/'native'/Path(tm.name.replace(':','_')).name;files.append(retain(p,t.extractfile(tm).read()))
        nh=header(p)[0];assert nh['NAXIS1']==4096 and nh['NAXIS2']==72 and nh['INSTRUME']=='HARPS' and nh['OBJECT'].replace(' ','')=='HD126093'
        assert nh['DATE-OBS']==spec['date_obs'] and abs(nh['ESO DRS BERV']-spec['berv_km_s'])<1e-10
        degree=int(nh['ESO DRS CAL TH DEG LL']);ldeg=int(nh['ESO DRS CAL LOC DEG CTR']);assert degree==3 and ldeg==4
        event_centers={e:next(r['topocentric_air_angstrom'] for r in old['orders'] if r['review_id']==e) for e in related}
        covering=sorted({r['order'] for r in old['orders'] if r['review_id'] in related});assert covering==[3,4]
        assert abs(nh['ESO DRS BERV']-next(e['berv_km_s'] for e in epochs if e['dp_id']==dp))<1e-12
        assert all(abs(c-EVENT_CENTERS[e]/(1+nh['ESO DRS BERV']/SPEED_OF_LIGHT_KM_S))<1e-10 for e,c in event_centers.items())
        orders={}
        for o in range(72):
            coeff=[nh['ESO DRS CAL TH COEFF LL'+str(o*(degree+1)+j)] for j in range(degree+1)]
            endpoint=[coeff[0],sum(c*4095**j for j,c in enumerate(coeff))]
            derivatives=[coeff[1],sum(j*c*4095**(j-1) for j,c in enumerate(coeff) if j)]
            vertex=-coeff[2]/(3*coeff[3]) if coeff[3] else -1
            if 0<vertex<4095:derivatives.append(coeff[1]+2*coeff[2]*vertex+3*coeff[3]*vertex**2)
            assert min(derivatives)>0
            covered=[e for e,c in event_centers.items() if endpoint[0]<c<endpoint[1]]
            all_order_scan.append({'dp_id':dp,'order':o,'header_endpoint_topocentric_air_angstrom':endpoint,'positive_wavelength_derivative_on_full_order':True,'original_events_covered':covered,'covers_any_original_event_center':bool(covered),'selected_for_profile':bool(covered)})
            assert bool(covered)==(o in covering)
            if not covered:continue
            factor=1+nh['ESO DRS BERV']/SPEED_OF_LIGHT_KM_S
            geometry={}
            for frame,frame_center,frame_scale in [('barycentric',CENTER_BARY_AIR,factor),('topocentric',ANCHOR_TOPO_AIR,1.0)]:
                frame_endpoints=[x*frame_scale for x in endpoint]
                geometry[frame]={'header_endpoint_air_angstrom':frame_endpoints,'offset_endpoints_from_frame_center_angstrom':[x-frame_center for x in frame_endpoints],'context_air_angstrom':[frame_center-3,frame_center+3],'core_air_angstrom':[frame_center-.25,frame_center+.25],'full_context_geometrically_covered':frame_endpoints[0]<=frame_center-3 and frame_endpoints[1]>=frame_center+3,'full_core_geometrically_covered':frame_endpoints[0]<=frame_center-.25 and frame_endpoints[1]>=frame_center+.25,'negative_reference_flank_geometrically_covered':frame_endpoints[0]<=frame_center-3 and frame_endpoints[1]>=frame_center-1.5,'positive_reference_flank_geometrically_covered':frame_endpoints[0]<=frame_center+1.5 and frame_endpoints[1]>=frame_center+3}
            orders[str(o)]={'wavelength_coefficients_ascending':coeff,'trace_coefficients_ascending':[nh['ESO DRS CAL LOC CTR'+str(o*(ldeg+1)+j)] for j in range(ldeg+1)],'header_endpoint_topocentric_air_angstrom':endpoint,'covers_original_center':True,'coverage_status':'COVERING_LINE','fixed_frame_header_geometry':geometry,'original_event_centers_topocentric_air_angstrom':event_centers}
            for e in related:
                assert e in covered
                coverage.append({'event':e,'dp_id':dp,'order':o,'status':'COVERING_LINE','header_endpoint_topocentric_air_angstrom':endpoint,'original_topocentric_feature_center_air_angstrom':event_centers[e],'source_file':record(p),'selected_for_profile':True,'saved_raw_panel_exists':True})
        native.append({'covering_orders':covering,'header_orders_available':covering,'original_topocentric_feature_center_air_angstrom':event_centers[event],'original_event_centers_topocentric_air_angstrom':event_centers,'event':event,'discovery_for':related,'dp_id':dp,'file':record(p),'ancillary_file':record(anc),'ancillary_archive_member':member,'native_tar_member':tm.name,'numpy_shape_from_header':[nh['NAXIS2'],nh['NAXIS1']],'wavelength_polynomial_degree':degree,'trace_polynomial_degree':ldeg,'orders':orders,'wavelength_polynomial_argument':'zero-based native pixel,0..4095','inherited_wavelength_representation':'topocentric air angstrom, as in the unchanged historical extractor; merged spectra are barycentric air angstrom','flux_unit_header':nh.get('BUNIT'),'primary_header':compact(nh,['INSTRUME','OBJECT','DATE-OBS','MJD-OBS','EXPTIME','ESO DRS BERV','BUNIT','ESO DRS CAL TH FILE','ESO DRS CAL LOC FILE']),'orientation':{k:spec['grid_best'][k] for k in ['row_flip','argument_flip','column_flip']}})
    for r in old['orders']:
        if r['review_id'] in EVENTS:
            event=r['review_id'];dp=EVENTS[event]
            entry={'event':event,'dp_id':dp,'order':r['order'],'native_pixel':r['native_pixel'],'raw_row':r['raw_row'],'raw_column':r['raw_column'],'original_grid_mapping_usable':r['grid_mapping_usable'],'original_local_mapping_usable':r['local_mapping_usable'],'original_baseline_mapping_verified':r.get('baseline_mapping_verified',r['mapping_verified']),'final_reference_mapping_supported':r['five_window_mapping_supported'],'registration_changed':False}
            assert [entry[k] for k in ['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']]==([True,True,True,True])
            mapping.append(entry)
    e2=OLD/'raw_followup_batch04';e2m=read(e2/'EVIDENCE_ARCHIVE.json');parts=read(e2/'EVIDENCE_PARTS.json');chunks=[]
    for part in parts['parts']:
        b=(e2/part['path']).read_bytes();assert len(b)==part['bytes'] and digest(b)==part['sha256'];chunks.append(b)
    e2bytes=b''.join(chunks);assert len(e2bytes)==e2m['bytes'] and digest(e2bytes)==e2m['sha256']
    cutouts=[]
    for event in EVENTS:
        with zipfile.ZipFile(io.BytesIO(e2bytes)) as z:
            manifest=e2m['members']
            for order in next(n['covering_orders'] for n in native if event in n['discovery_for']):
                m=next(m for m in manifest if Path(m['path']).name==event+'_o'+str(order).zfill(2)+'.npz');p=HERE/'evidence'/Path(m['path']).name
                files.append(retain(p,z.read(m['path']),m));assert sha(p)==next(r['cutout_sha256'] for r in old['orders'] if r['review_id']==event and r['order']==order);cutouts.append({'event':event,'order':order,'file':record(p),'npy_headers':npy_headers(p),'archive_member':m['path']})
    assert len(files)==22 and len({f['path'] for f in files})==22 and len(mapping)==8 and len(cutouts)==8 and len(excluded)==0
    historical_reviews={'adopted':[r for r in csv.DictReader((OLD/'raw_followup_batch04/ADOPTED_DISPOSITIONS.csv').open()) if r['review_id'] in EVENTS]}
    for label,name in [('primary','PRIMARY_VISUAL_REVIEW.json'),('secondary','SECONDARY_VISUAL_REVIEW.json'),('comparison','REVIEW_COMPARISON.json')]:
        historical_reviews[label]=[r for r in read(OLD/'raw_followup_batch04'/name)['records' if label=='secondary' else 'events'] if r['review_id'] in EVENTS]
    assert all(len(rows)==4 for rows in historical_reviews.values())
    assert all(r['code']=='U' for r in historical_reviews['adopted'])
    assert historical_reviews['primary'][0]['code']=='U' and historical_reviews['secondary'][0]['code']=='U'
    assert all(sha(REPO/n)==h for n,h in source_hashes.items())
    inventory={'schema':'HARPS_C033_EXACT_INPUT_INVENTORY_V1','status':'PASS_HEADER_ONLY_RESTORATION','target':'HD126093','events':EVENTS,'merged_spectra':merged,'native_products':native,'native_order_coverage':coverage,'all_order_header_scan':all_order_scan,'unique_native_order_pairs':[{'dp_id':n['dp_id'],'order':o} for n in native for o in n['covering_orders']],'excluded_native_orders':excluded,'saved_native_raw_cutouts':cutouts,'mapping_records':mapping,'historical_raw_review_records':historical_reviews,'coordinate_anchor':{'discovery_dp_id':EVENTS['V2E2-0265'],'discovery_berv_km_s':DISCOVERY_BERV_KM_S,'center_barycentric_air_angstrom':CENTER_BARY_AIR,'fixed_topocentric_air_angstrom':ANCHOR_TOPO_AIR,'formula':'center_barycentric_air_angstrom/(1+discovery_berv_km_s/299792.458)'},'historical_review_note':'Four original U/U/U chains remain. All eight original global/local/baseline/later mapping stages are true. The0274 secondary review retains a possible compact off-trace deposit/blend caution distinct from the broad trace-centered component; other events do not inherit it. Four own discoveries and six reused observations; restoration decodes headers only.','archives':archives,'files':files,'source_hashes':source_hashes,'science_array_values_interpreted':0,'network_requests':0,'historical_files_modified':False,'full_raw_products_restored':False,'full_raw_note':'Original raw products remain available in the same verified discovery archives; this broader-profile phase restores native A and existing raw cutouts only.'}
    write('INPUT_INVENTORY.json',inventory);write('RESTORE_RECEIPT.json',{'status':'PASS','files':len(files),'merged_spectra':6,'native_A_products':4,'unique_covering_order_pairs':8,'event_covering_order_contexts':8,'excluded_native_orders':0,'saved_cutouts':8,'source_hashes_unchanged':True,'all_files_verified':True,'science_array_values_interpreted':0,'network_requests':0})
    print(json.dumps({'status':'PASS','files':len(files),'merged':6,'native_A':4,'unique_native_order_pairs':8,'event_order_contexts':8,'excluded_orders':0,'cutouts':len(cutouts),'inventory_sha256':sha(HERE/'INPUT_INVENTORY.json')},indent=2))

if __name__=='__main__':main()
