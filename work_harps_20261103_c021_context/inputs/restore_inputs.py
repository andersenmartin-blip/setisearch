"""Restore exact existing C021 inputs; inspect FITS/NPY headers, never array values."""
import argparse, ast, csv, hashlib, io, json, re, struct, tarfile, zipfile
from pathlib import Path
from astropy.io import fits

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
OLD=REPO/'work_harps_20261101/v2/extension02'
EVENTS={'V2E2-0116':'ADP.2022-01-22T01:09:14.958','V2E2-0121':'ADP.2022-02-06T01:07:28.382','V2E2-0126':'ADP.2022-05-06T01:04:00.123','V2E2-0130':'ADP.2023-01-17T01:07:48.581','V2E2-0139':'ADP.2023-07-02T01:01:43.311'}
ORIGINAL_CENTERS_BARY_AIR={'V2E2-0116':4309.827499999999,'V2E2-0121':4309.827499999999,'V2E2-0126':4309.825,'V2E2-0130':4309.825,'V2E2-0139':4309.827499999999}
ANCHOR_DP_ID=EVENTS['V2E2-0116']
CENTER_BARY_AIR=(min(ORIGINAL_CENTERS_BARY_AIR.values())+max(ORIGINAL_CENTERS_BARY_AIR.values()))/2
DISCOVERY_BERV_KM_S=29.658729150824
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
    source_names=['acquisition/DOWNLOAD_MANIFEST.csv','checkpoints/INPUT_CHECKPOINTS.json','epoch_followup/INPUT_CHECKS.json','epoch_followup/EVENT_RESULTS.json','raw_followup_batch03/checkpoints/INPUT_ARCHIVES.json','raw_followup_batch03/NATIVE_MAPPING.json','raw_followup_batch03/extract_native.py','raw_followup_batch03/EVIDENCE_ARCHIVE.json','raw_followup_batch03/EVIDENCE_PARTS.json','raw_followup_batch03/ADOPTED_DISPOSITIONS.csv','raw_followup_batch03/PRIMARY_VISUAL_REVIEW.json','raw_followup_batch03/SECONDARY_VISUAL_REVIEW.json','raw_followup_batch03/REVIEW_COMPARISON.json','raw_followup/checkpoints/RAW_INPUT_CHECKPOINTS.json','raw_followup/NATIVE_MAPPING.json','raw_followup/extract_native.py','raw_followup/RAW_BASELINE_EVIDENCE_MANIFEST.json','raw_followup/RAW_BASELINE_EVIDENCE.zip','raw_followup/PRIMARY_VISUAL_REVIEW.json','raw_followup/audit/INDEPENDENT_VISUAL_NOTES.json','raw_followup/REVIEW_AGREEMENT.json','raw_followup/BASELINE_SELECTED_EVENT_DISPOSITIONS.csv','raw_followup/CURRENT_SELECTED_EVENT_DISPOSITIONS.csv','raw_followup/mapping_followup/MAPPING_AUDIT.json','raw_followup/mapping_followup/FIRST_VISUAL_NOTES.json','raw_followup/mapping_followup/SECOND_VISUAL_NOTES.json','raw_followup/mapping_followup/FOLLOWUP_DISPOSITIONS.csv','raw_followup/mapping_followup/PRESERVED_INPUT_HASHES.json','raw_followup/mapping_followup/VERIFICATION.json','raw_followup/mapping_followup/FINAL_REVIEW_SUMMARY.json','raw_followup/mapping_followup/EVIDENCE_ARCHIVE.json','raw_followup/mapping_followup/MAPPING_FOLLOWUP_EVIDENCE.zip']
    source_hashes={str((OLD/n).relative_to(REPO)):sha(OLD/n) for n in source_names}
    handoff=REPO/'work_harps_20261103_c019_context/NEXT_ACTION.json';handoff_data=read(handoff)
    source_hashes[str(handoff.relative_to(REPO))]=sha(handoff)
    current_path=OLD.parent/'CURRENT_V2_DISPOSITIONS.csv';source_hashes[str(current_path.relative_to(REPO))]=sha(current_path)
    assert {r['candidate_id']:r['dp_id'] for r in handoff_data['queue_rows']}==EVENTS
    epochs=[r for r in read(OLD/'epoch_followup/INPUT_CHECKS.json') if r['target']=='HD114783'];assert len(epochs)==7
    downloads={r['dp_id']:r for r in csv.DictReader((OLD/'acquisition/DOWNLOAD_MANIFEST.csv').open()) if r['canonical_target']=='HD114783'}
    assert set(downloads)=={r['dp_id'] for r in epochs} and set(EVENTS.values()).issubset(downloads)
    science_part=next(p for p in read(OLD/'checkpoints/INPUT_CHECKPOINTS.json')['parts'] if all(r['dp_id'] in p['exposure_ids'] for r in epochs))
    batch_root=OLD/'raw_followup_batch03';legacy_root=OLD/'raw_followup';follow_root=legacy_root/'mapping_followup'
    batch_model=read(batch_root/'NATIVE_MAPPING.json');legacy_model=read(legacy_root/'NATIVE_MAPPING.json');later_mapping=read(follow_root/'MAPPING_AUDIT.json')
    def model(event):return legacy_model if event=='V2E2-0130' else batch_model
    def original_source(event):return legacy_root if event=='V2E2-0130' else batch_root
    raw_parts=read(batch_root/'checkpoints/INPUT_ARCHIVES.json')['archives'];legacy_parts=read(legacy_root/'checkpoints/RAW_INPUT_CHECKPOINTS.json')['parts']
    selected_parts={};members={}
    for event,dp in EVENTS.items():
        if event=='V2E2-0130':
            part=next(p for p in legacy_parts if dp in p['exposure_ids']);spec=next(s for s in legacy_model['spectra'] if s['dp_id']==dp)
            member=next(m for m in part['members'] if m['sha256']==spec['ancillary_sha256']);assert member['path'].endswith('.tar')
        else:
            part=next(p for p in raw_parts if any(m['dp_id']==dp and m['kind']=='ANCILLARY' for m in p['products']))
            member=next(m for m in part['products'] if m['dp_id']==dp and m['kind']=='ANCILLARY')
        selected_parts[event]=part;members[event]=member
    archives=[];archive_paths={}
    for part in {p['filename']:p for p in [science_part,*selected_parts.values()]}.values():
        found=[d/part['filename'] for d in a.archive_dir if (d/part['filename']).is_file()];assert found,'Missing '+part['filename']
        cache=found[0];assert cache.stat().st_size==part['bytes'] and sha(cache)==part['sha256']
        archive_paths[part['filename']]=cache;archives.append({k:part[k] for k in ['filename','bytes','sha256']})
    assert len(archives)==5
    files=[];merged=[]
    with zipfile.ZipFile(archive_paths[science_part['filename']]) as z:
        for e in epochs:
            d=downloads[e['dp_id']];m=next(m for m in science_part['members'] if m['path']==d['relative_path']);assert m['sha256']==d['sha256']==e['sha256']
            p=HERE/'merged'/Path(m['path']).name;files.append(retain(p,z.read(m['path']),m));ph,th=header(p)
            assert ph['ARCFILE'].removesuffix('.fits')==e['dp_id'] and ph['INSTRUME']=='HARPS' and ph['OBJECT'].replace(' ','')=='HD114783'
            assert ph['SPECSYS']=='BARYCENT' and ph['NCOMBINE']==1 and th['NAXIS2']==1
            assert [th['TTYPE'+str(i)] for i in [1,2,3]]==['WAVE','FLUX','ERR']
            assert th['TUNIT1']=='angstrom' and th['TUNIT2']==th['TUNIT3']=='adu'
            assert abs(ph['ESO DRS BERV']-e['berv_km_s'])<1e-10 and ph['PROV1'].removesuffix('.fits')==d['expected_raw_progenitor_id']
            merged.append({'dp_id':e['dp_id'],'raw_id':d['expected_raw_progenitor_id'],'file':record(p),'discovery_for':[k for k,v in EVENTS.items() if v==e['dp_id']],'date_obs':e['date_obs'],'mjd_obs':e['mjd_obs'],'berv_km_s':e['berv_km_s'],'primary_header':compact(ph,['ARCFILE','PROV1','INSTRUME','OBJECT','DATE-OBS','EXPTIME','MJD-OBS','SPECSYS','FLUXCAL','NCOMBINE','WAVELMIN','WAVELMAX','SPEC_BIN','SPEC_RES','SNR','ESO DRS BERV']),'table_header':compact(th,['NAXIS1','NAXIS2','TTYPE1','TTYPE2','TTYPE3','TFORM1','TFORM2','TFORM3','TUNIT1','TUNIT2','TUNIT3','TUCD1','TCOMM3']),'archive_member':m['path']})
    native=[];mapping=[];coverage=[];all_order_scan=[];excluded=[]
    for event,dp in EVENTS.items():
        old=model(event);pinfo=selected_parts[event];m=members[event];member=m.get('path',m.get('relative_path'))
        with zipfile.ZipFile(archive_paths[pinfo['filename']]) as z:
            anc=HERE/'source_products'/Path(member).name;files.append(retain(anc,z.read(member),m))
        spec=next(s for s in old['spectra'] if s['dp_id']==dp);assert sha(anc)==spec['ancillary_sha256']
        with tarfile.open(anc) as t:
            tm=t.getmember(spec['native_member']);assert tm.isfile();p=HERE/'native'/Path(tm.name.replace(':','_')).name;files.append(retain(p,t.extractfile(tm).read()))
        nh=header(p)[0];assert nh['NAXIS1']==4096 and nh['NAXIS2']==72 and nh['INSTRUME']=='HARPS' and nh['OBJECT'].replace(' ','')=='HD114783'
        assert nh['DATE-OBS']==spec['date_obs'] and abs(nh['ESO DRS BERV']-spec['berv_km_s'])<1e-10
        degree=int(nh['ESO DRS CAL TH DEG LL']);ldeg=int(nh['ESO DRS CAL LOC DEG CTR']);assert degree==3 and ldeg==4
        original_center=next(r['topocentric_air_angstrom'] for r in old['orders'] if r['review_id']==event)
        assert abs(original_center-ORIGINAL_CENTERS_BARY_AIR[event]/(1+nh['ESO DRS BERV']/SPEED_OF_LIGHT_KM_S))<1e-10
        if dp==ANCHOR_DP_ID:assert abs(nh['ESO DRS BERV']-DISCOVERY_BERV_KM_S)<1e-12
        historical_covering=sorted({r['order'] for r in old['orders'] if r['review_id']==event});assert historical_covering==[19]
        factor=1+nh['ESO DRS BERV']/SPEED_OF_LIGHT_KM_S;orders={};covering=[]
        for o in range(72):
            coeff=[nh['ESO DRS CAL TH COEFF LL'+str(o*(degree+1)+j)] for j in range(degree+1)]
            endpoint=[coeff[0],sum(c*4095**j for j,c in enumerate(coeff))]
            derivatives=[coeff[1],sum(j*c*4095**(j-1) for j,c in enumerate(coeff) if j)]
            vertex=-coeff[2]/(3*coeff[3]) if coeff[3] else -1
            if 0<vertex<4095:derivatives.append(coeff[1]+2*coeff[2]*vertex+3*coeff[3]*vertex**2)
            assert min(derivatives)>0
            covered=endpoint[0]<original_center<endpoint[1]
            all_order_scan.append({'dp_id':dp,'order':o,'header_endpoint_topocentric_air_angstrom':endpoint,'positive_wavelength_derivative_on_full_order':True,'original_events_covered':[event] if covered else [],'covers_any_original_event_center':covered,'selected_for_profile':covered,'covers_common_fixed_barycentric_center':endpoint[0]*factor<CENTER_BARY_AIR<endpoint[1]*factor,'covers_common_fixed_topocentric_anchor':endpoint[0]<ANCHOR_TOPO_AIR<endpoint[1]})
            if not covered:continue
            covering.append(o);geometry={}
            for frame,frame_center,frame_scale in [('barycentric',CENTER_BARY_AIR,factor),('topocentric',ANCHOR_TOPO_AIR,1.0)]:
                frame_endpoints=[x*frame_scale for x in endpoint]
                geometry[frame]={'header_endpoint_air_angstrom':frame_endpoints,'offset_endpoints_from_frame_center_angstrom':[x-frame_center for x in frame_endpoints],'context_air_angstrom':[frame_center-3,frame_center+3],'core_air_angstrom':[frame_center-.25,frame_center+.25],'full_context_geometrically_covered':frame_endpoints[0]<=frame_center-3 and frame_endpoints[1]>=frame_center+3,'full_core_geometrically_covered':frame_endpoints[0]<=frame_center-.25 and frame_endpoints[1]>=frame_center+.25,'negative_reference_flank_geometrically_covered':frame_endpoints[0]<=frame_center-3 and frame_endpoints[1]>=frame_center-1.5,'positive_reference_flank_geometrically_covered':frame_endpoints[0]<=frame_center+1.5 and frame_endpoints[1]>=frame_center+3}
            orders[str(o)]={'wavelength_coefficients_ascending':coeff,'trace_coefficients_ascending':[nh['ESO DRS CAL LOC CTR'+str(o*(ldeg+1)+j)] for j in range(ldeg+1)],'header_endpoint_topocentric_air_angstrom':endpoint,'covers_original_center':True,'coverage_status':'COVERING_LINE','fixed_frame_header_geometry':geometry,'original_event_centers_topocentric_air_angstrom':{event:original_center}}
            coverage.append({'event':event,'dp_id':dp,'order':o,'status':'COVERING_LINE','header_endpoint_topocentric_air_angstrom':endpoint,'original_topocentric_feature_center_air_angstrom':original_center,'source_file':record(p),'selected_for_profile':True,'saved_raw_panel_exists':True})
        assert covering==historical_covering
        native.append({'covering_orders':covering,'header_orders_available':covering,'original_topocentric_feature_center_air_angstrom':original_center,'original_event_centers_topocentric_air_angstrom':{event:original_center},'event':event,'discovery_for':[event],'dp_id':dp,'file':record(p),'ancillary_file':record(anc),'ancillary_archive_member':member,'native_tar_member':tm.name,'numpy_shape_from_header':[nh['NAXIS2'],nh['NAXIS1']],'wavelength_polynomial_degree':degree,'trace_polynomial_degree':ldeg,'orders':orders,'wavelength_polynomial_argument':'zero-based native pixel,0..4095','inherited_wavelength_representation':'topocentric air angstrom, as in the unchanged historical extractor; merged spectra are barycentric air angstrom','flux_unit_header':nh.get('BUNIT'),'primary_header':compact(nh,['INSTRUME','OBJECT','DATE-OBS','MJD-OBS','EXPTIME','ESO DRS BERV','BUNIT','ESO DRS CAL TH FILE','ESO DRS CAL LOC FILE']),'orientation':{k:spec['grid_best'][k] for k in ['row_flip','argument_flip','column_flip']},'original_mapping_source':str((original_source(event)/'NATIVE_MAPPING.json').relative_to(REPO))})
        for row in [r for r in old['orders'] if r['review_id']==event]:
            later=next((r for r in later_mapping['orders'] if r['review_id']==event and r['order']==row['order']),None)
            entry={'event':event,'dp_id':dp,'order':row['order'],'native_pixel':row['native_pixel'],'raw_row':row['raw_row'],'raw_column':row['raw_column'],'original_grid_mapping_usable':row['grid_mapping_usable'],'original_local_mapping_usable':row['local_mapping_usable'],'original_baseline_mapping_verified':row.get('baseline_mapping_verified',row['mapping_verified']),'final_reference_mapping_supported':later['reference_mapping_supported'] if event=='V2E2-0130' else row['five_window_mapping_supported'],'registration_changed':False,'original_mapping_source':str((original_source(event)/'NATIVE_MAPPING.json').relative_to(REPO)),'baseline_field_basis':'mapping_verified in original raw_followup mapping' if event=='V2E2-0130' else 'explicit baseline_mapping_verified in batch03 mapping'}
            assert entry['original_grid_mapping_usable'] is True and entry['final_reference_mapping_supported'] is True
            assert entry['original_local_mapping_usable']==entry['original_baseline_mapping_verified']==(event in ['V2E2-0121','V2E2-0139'])
            if event=='V2E2-0130':
                assert later_mapping['coordinates_changed'] is False and later_mapping['original_hashes_unchanged'] is True
                assert all(later[k]==row[k] for k in ['native_pixel','raw_row','raw_column','topocentric_air_angstrom'])
                entry['later_mapping_source']=str((follow_root/'MAPPING_AUDIT.json').relative_to(REPO))
            mapping.append(entry)
    bm=read(batch_root/'EVIDENCE_ARCHIVE.json');parts=read(batch_root/'EVIDENCE_PARTS.json');chunks=[]
    for part in parts['parts']:
        b=(batch_root/part['path']).read_bytes();assert len(b)==part['bytes'] and digest(b)==part['sha256'];chunks.append(b)
    batch_bytes=b''.join(chunks);assert len(batch_bytes)==bm['bytes'] and digest(batch_bytes)==bm['sha256']
    lm=read(legacy_root/'RAW_BASELINE_EVIDENCE_MANIFEST.json');legacy_bytes=(legacy_root/'RAW_BASELINE_EVIDENCE.zip').read_bytes();assert len(legacy_bytes)==lm['archive_bytes'] and digest(legacy_bytes)==lm['archive_sha256']
    preserved=read(follow_root/'PRESERVED_INPUT_HASHES.json');cutouts=[]
    for event in EVENTS:
        legacy=event=='V2E2-0130';manifest=lm['members'] if legacy else bm['members'];data=legacy_bytes if legacy else batch_bytes
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for order in [19]:
                member=next(m for m in manifest if Path(m['path']).name==event+'_o'+str(order).zfill(2)+'.npz');p=HERE/'evidence'/Path(member['path']).name
                files.append(retain(p,z.read(member['path']),member))
                if legacy:assert sha(p)==preserved['v2/extension02/raw_followup/'+member['path']]
                else:assert sha(p)==next(r['cutout_sha256'] for r in batch_model['orders'] if r['review_id']==event and r['order']==order)
                cutouts.append({'event':event,'order':order,'file':record(p),'npy_headers':npy_headers(p),'archive_member':member['path'],'original_source_directory':str(original_source(event).relative_to(REPO)),'container_stage':'original baseline panel' if legacy else 'original batch03 panel','later_wider_container_substituted':False})
    assert len(files)==22 and len({f['path'] for f in files})==22 and len(native)==5 and len(mapping)==5 and len(cutouts)==5 and len(all_order_scan)==360 and len(excluded)==0
    batch_events=set(EVENTS)-{'V2E2-0130'}
    original={'adopted':[r for r in csv.DictReader((batch_root/'ADOPTED_DISPOSITIONS.csv').open()) if r['review_id'] in batch_events]}
    for label,name in [('primary','PRIMARY_VISUAL_REVIEW.json'),('secondary','SECONDARY_VISUAL_REVIEW.json'),('comparison','REVIEW_COMPARISON.json')]:original[label]=[r for r in read(batch_root/name)['events'] if r['review_id'] in batch_events]
    assert all(len(rows)==4 for rows in original.values())
    assert all(r['code']=='U' for label in ['adopted','primary','secondary'] for r in original[label])
    primary=next(r for r in read(legacy_root/'PRIMARY_VISUAL_REVIEW.json')['rows'] if r['review_id']=='V2E2-0130')
    secondary=read(legacy_root/'audit/INDEPENDENT_VISUAL_NOTES.json')['notes']['V2E2-0130'];agreement=next(r for r in read(legacy_root/'REVIEW_AGREEMENT.json')['rows'] if r['review_id']=='V2E2-0130')
    def csv_event(path):return next(r for r in csv.DictReader(path.open()) if r['review_id']=='V2E2-0130')
    baseline=csv_event(legacy_root/'BASELINE_SELECTED_EVENT_DISPOSITIONS.csv');current=csv_event(legacy_root/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv');later_disposition=csv_event(follow_root/'FOLLOWUP_DISPOSITIONS.csv')
    first=read(follow_root/'FIRST_VISUAL_NOTES.json')['notes']['V2E2-0130'];second=read(follow_root/'SECOND_VISUAL_NOTES.json')['notes']['V2E2-0130']
    assert primary['primary_code']=='I' and secondary[0]=='M' and agreement['second_code_normalized']=='I' and baseline['baseline_code']=='I'
    assert current['current_code']==later_disposition['proposed_code']==first[0]==second[0]=='U'
    assert later_disposition['coordinates_changed']=='False' and later_disposition['original_native_and_raw_pixels_preserved']=='True'
    final=read(follow_root/'FINAL_REVIEW_SUMMARY.json');assert final['coordinates_changed'] is False and final['original_raw_pixels_and_native_samples_preserved'] is True
    wm=read(follow_root/'EVIDENCE_ARCHIVE.json');assert (follow_root/'MAPPING_FOLLOWUP_EVIDENCE.zip').stat().st_size==wm['bytes'] and sha(follow_root/'MAPPING_FOLLOWUP_EVIDENCE.zip')==wm['sha256']
    current_rows=[r for r in csv.DictReader(current_path.open()) if r['review_id'] in EVENTS];assert len(current_rows)==5 and all(r['current_code']=='U' for r in current_rows)
    history={'batch03_original':original,'separate_raw_followup_0130':{'original_primary':primary,'original_secondary_source_record':secondary,'original_review_agreement':agreement,'original_adopted_baseline':baseline,'current_adopted_record':current,'later_primary_source_record':first,'later_secondary_source_record':second,'later_disposition_record':later_disposition,'later_mapping_records':[r for r in later_mapping['orders'] if r['review_id']=='V2E2-0130'],'later_verification_record':read(follow_root/'VERIFICATION.json'),'later_evidence_archive':{k:wm[k] for k in ['filename','bytes','sha256']},'later_preservation_declarations':{k:final[k] for k in ['coordinates_changed','original_raw_pixels_and_native_samples_preserved','baseline_files_unchanged','original_catalogs_unchanged']},'later_wider_containers_are_distinct_from_original_baseline_panels':True,'new_pixel_equality_test_performed':False},'current_adopted':current_rows,'per_event_history':handoff_data['historical_review_disagreement']['per_event_history']}
    assert all(sha(REPO/n)==h for n,h in source_hashes.items())
    inventory={'schema':'HARPS_C021_EXACT_INPUT_INVENTORY_V1','status':'PASS_HEADER_ONLY_RESTORATION','target':'HD114783','events':EVENTS,'merged_spectra':merged,'native_products':native,'native_order_coverage':coverage,'all_order_header_scan':all_order_scan,'unique_native_order_pairs':[{'dp_id':n['dp_id'],'order':o} for n in native for o in n['covering_orders']],'excluded_native_orders':excluded,'saved_native_raw_cutouts':cutouts,'mapping_records':mapping,'historical_raw_review_records':history,'coordinate_anchor':{'discovery_dp_id':ANCHOR_DP_ID,'anchor_selection_rule':'First member in original ACTION_QUEUE fixes one common group topocentric anchor; all five discovery products remain separate references.','original_member_centers_barycentric_air_angstrom':ORIGINAL_CENTERS_BARY_AIR,'group_center_rule':'Midpoint of exact minimum/maximum member catalog centers; exact individual cores remain distinct, without post-value expansion.','discovery_berv_km_s':DISCOVERY_BERV_KM_S,'center_barycentric_air_angstrom':CENTER_BARY_AIR,'fixed_topocentric_air_angstrom':ANCHOR_TOPO_AIR,'formula':'center_barycentric_air_angstrom/(1+discovery_berv_km_s/299792.458)'},'historical_review_note':'Four batch03 members0116/0121/0126/0139 retain original U/U/U. Separate raw_followup0130 retains original primary I, secondary M normalized I and baseline I; completed later five-window mapping and separate visual reviews at unchanged coordinates retain U/U/current U. All five original global and later support fields are true; original local/baseline stages remain false for0116/0126/0130 and true for0121/0139. Original baseline panels are restored without substitution by distinct later wider containers. Historical preservation declarations remain records without a new pixel-equality test or diagnostic replay. No C019/0129 null-stage or quality outcome is transferred. Every current label remains U.','archives':archives,'files':files,'source_hashes':source_hashes,'science_array_values_interpreted':0,'network_requests':0,'historical_files_modified':False,'full_raw_products_restored':False,'full_raw_note':'Full raw detector products remain in the verified discovery archives; restore native A and five original raw panels only.'}
    write('INPUT_INVENTORY.json',inventory);write('RESTORE_RECEIPT.json',{'status':'PASS','files':len(files),'merged_spectra':7,'native_A_products':5,'unique_covering_order_pairs':5,'event_covering_order_contexts':5,'excluded_native_orders':0,'saved_cutouts':5,'all_order_header_rows':360,'source_hashes_unchanged':True,'all_files_verified':True,'science_array_values_interpreted':0,'network_requests':0,'original_0130_baseline_containers_preserved':True,'completed_mapping_diagnostic_replayed':False})
    print(json.dumps({'status':'PASS','files':len(files),'merged':7,'native_A':5,'unique_native_order_pairs':5,'event_order_contexts':5,'all_order_header_rows':360,'excluded_orders':0,'cutouts':len(cutouts),'inventory_sha256':sha(HERE/'INPUT_INVENTORY.json')},indent=2))

if __name__=='__main__':main()
