"""C004 identity/coverage audit: opaque hashes and FITS/NPY headers, no flux values."""
import ast,csv,datetime,hashlib,io,json,math,re,struct,subprocess,tarfile,zipfile
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent;I=PHASE/'inputs';OLD=REPO/'work_harps_20261101/v2/extension02'
INV=I/'INPUT_INVENTORY.json';C=299792.458;CB=3872.245;ANCHOR=10.77158288517;CT=CB/(1+ANCHOR/C)
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def head(f):
 blocks=[]
 while True:
  b=f.read(2880)
  if len(b)!=2880:raise ValueError('Truncated FITS header')
  blocks.append(b)
  if any(b[i:i+8]==b'END     ' for i in range(0,2880,80)):return Header.fromstring(b''.join(blocks).decode('ascii'),sep='')
  if len(blocks)*2880>524288:raise ValueError('Header cap')
def headers(p):
 result=[]
 with p.open('rb') as f:
  while f.tell()<p.stat().st_size:
   h=head(f);result.append(h);n=math.prod(h['NAXIS'+str(i)] for i in range(1,h['NAXIS']+1)) if h['NAXIS'] else 0
   n=(n+h.get('PCOUNT',0))*h.get('GCOUNT',1)*abs(h['BITPIX'])//8;f.seek(((n+2879)//2880)*2880,1)
  assert f.tell()==p.stat().st_size
 return result
counts={};failures=[]
def ck(group,condition,detail):
 counts[group]=counts.get(group,0)+1
 if not condition:failures.append(group+': '+detail)
def poly(co,x):
 v=0.
 for c in reversed(co):v=v*x+c
 return v
download={r['dp_id']:r for r in csv.DictReader((OLD/'acquisition/DOWNLOAD_MANIFEST.csv').open())};timestamp_offsets=[]
inv=read(INV);expected_inventory='1be83dc6e3be2ca639de5a90f16bcff28081e591243c5d2f46160ecc2222607e';ck('inventory',sha(INV)==expected_inventory,'final inventory binding')
group_path=OLD/'unresolved_context_20261102/CORE_OVERLAP_GROUPS.csv';group=next(r for r in csv.DictReader(group_path.open()) if r['group_id']=='C004')
event_path=OLD/'raw_followup_batch02/SELECTED_EVENTS.csv';source_events={r['review_id']:r for r in csv.DictReader(event_path.open())}
expected_events={'V2E2-0028','V2E2-0045','V2E2-0052'}
ck('scope',set(group['member_ids'].split('|'))==set(inv['events'])=={e for r in inv['native_products'] for e in r['discovery_for']}==expected_events and len(inv['native_products'])==3,'exact archived C004 membership')
ck('inventory',len(inv['files'])==16 and len({r['path'] for r in inv['files']})==16,'16 unique restored paths')
for r in inv['files']:
 p=(REPO/r['path']).resolve();p.relative_to(I);ck('restored_bytes',p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],p.name)
for path,h in inv['source_hashes'].items():ck('historical_sources',sha(REPO/path)==h,path)
archive_dirs=[REPO.parent/'restored_normalization',REPO.parent/'restored_mapping_remaining'];archivepaths={}
historical_archives=read(OLD/'checkpoints/INPUT_CHECKPOINTS.json')['parts']+read(OLD/'raw_followup/checkpoints/RAW_INPUT_CHECKPOINTS.json')['parts']+read(OLD/'raw_followup_batch02/checkpoints/INPUT_ARCHIVES.json')['archives']
for r in inv['archives']:
 matches=[x for x in historical_archives if x['filename']==r['filename']];ck('archive',len(matches)==1 and all(matches[0][k]==r[k] for k in ['bytes','sha256']),r['filename']+' historical archive identity')
 p=next(d/r['filename'] for d in archive_dirs if (d/r['filename']).exists());ck('archive',p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],r['filename']);archivepaths[r['filename']]=p
science_archive=next(p for n,p in archivepaths.items() if 'EXTENSION02_INPUTS' in n)
checks=read(OLD/'epoch_followup/INPUT_CHECKS.json');previous={r['dp_id']:r for r in checks if r['target']=='HD106515A'};ck('merged_identity',set(previous)=={r['dp_id'] for r in inv['merged_spectra']},'exact prior seven epochs')
ck('merged_identity',len({r['raw_id'] for r in inv['merged_spectra']})==7,'seven unique progenitors')
merged_headers={};merged_summary=[]
with zipfile.ZipFile(science_archive) as z:
 for r in inv['merged_spectra']:
  p=REPO/r['file']['path'];ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256']==previous[r['dp_id']]['sha256'],r['dp_id'])
  hs=headers(p);ck('merged_headers',len(hs)==2 and hs[0]['NAXIS']==0 and hs[1]['XTENSION']=='BINTABLE' and hs[1]['NAXIS2']==1,r['dp_id']+' structure');ph,th=hs
  ck('merged_headers',all(ph.get(k)==v for k,v in r['primary_header'].items()) and all(th.get(k)==v for k,v in r['table_header'].items()),r['dp_id']+' inventory headers')
  prov=[c.value.removesuffix('.fits') for c in ph.cards if re.fullmatch(r'PROV\d+',c.keyword)];ck('merged_identity',prov==[r['raw_id']] and ph['ARCFILE']==r['dp_id']+'.fits' and ph['OBJECT'].replace(' ','')=='HD106515A' and ph['INSTRUME']=='HARPS',r['dp_id']+' identity')
  original=download[r['dp_id']];ck('merged_identity',r['raw_id']==original['expected_raw_progenitor_id'] and r['file']['sha256']==original['sha256'],r['dp_id']+' original PROV1 custody')
  delta=(datetime.datetime.fromisoformat(r['raw_id'].removeprefix('HARPS.'))-datetime.datetime.fromisoformat(ph['DATE-OBS'])).total_seconds()*1000
  ck('dates',abs(delta)<=10 and ph['DATE-OBS']==previous[r['dp_id']]['date_obs'] and abs(ph['MJD-OBS']-previous[r['dp_id']]['mjd_obs'])<1e-8,r['dp_id']+' raw identifier vs DATE-OBS')
  timestamp_offsets.append({'dp_id':r['dp_id'],'raw_id':r['raw_id'],'header_DATE_OBS':ph['DATE-OBS'],'raw_identifier_minus_header_milliseconds':delta,'policy':'Exact identifiers preserved; existing millisecond offset recorded, not string-normalized.'})
  ck('merged_units',ph['SPECSYS']=='BARYCENT' and ph['NCOMBINE']==1 and ph['FLUXCAL']=='UNCALIBRATED' and ph['SPEC_RES']==115000 and th['TUNIT1']=='angstrom' and th['TUNIT2']==th['TUNIT3']=='adu' and 'obs.atmos' in th['TUCD1'],r['dp_id'])
  formats=[re.fullmatch(r'([1-9][0-9]*)([DE])',th['TFORM'+str(i)]) for i in [1,2,3]];ck('merged_headers',all(formats) and len({int(m[1]) for m in formats if m})==1 and [th['TTYPE'+str(i)] for i in [1,2,3]]==['WAVE','FLUX','ERR'],r['dp_id']+' vectors')
  ck('merged_headers',math.isfinite(ph['ESO DRS BERV']) and abs(ph['ESO DRS BERV'])<100 and ph['ESO DRS BERV']==r['berv_km_s']==previous[r['dp_id']]['berv_km_s'],r['dp_id']+' BERV')
  ck('merged_headers','not available' in th.get('TCOMM3','').lower(),r['dp_id']+' unavailable ERR explicitly retained')
  merged_headers[r['dp_id']]=ph;merged_summary.append({'dp_id':r['dp_id'],'berv_km_s':ph['ESO DRS BERV'],'date_obs':ph['DATE-OBS'],'wavelength_unit':'air Angstrom','frame':'BARYCENT','flux_unit':'ADU, uncalibrated','ERR':'Declared unavailable/NaN; no sample values read'})
ck('scope',all(float(source_events[e]['fitted_center_bary_air_angstrom'])==CB for e in expected_events),'all original group centers equal frozen metadata center')
ck('anchor',merged_headers['ADP.2022-03-08T01:01:37.342']['ESO DRS BERV']==ANCHOR,'first discovery anchor exact')
old=read(OLD/'raw_followup_batch02/NATIVE_MAPPING.json');coverage=[];mapping_history=[];exclusions=[]
archive_names={};native_headers={}
for name,ap in archivepaths.items():
 with zipfile.ZipFile(ap) as z:archive_names[name]=set(z.namelist())
for r in [dict(p,event=e,original_topocentric_feature_center_air_angstrom=p['original_event_centers_topocentric_air_angstrom'][e]) for p in inv['native_products'] for e in p['discovery_for']]:
 anc=REPO/r['ancillary_file']['path'];native=REPO/r['file']['path'];ap=next(p for n,p in archivepaths.items() if r['ancillary_archive_member'] in archive_names[n])
 with zipfile.ZipFile(ap) as z:ck('archive_members',digest(z.read(r['ancillary_archive_member']))==r['ancillary_file']['sha256'],r['event']+' ancillary')
 with tarfile.open(anc) as z:
  members=[m for m in z if m.name.endswith('_e2ds_A.fits')];ck('native_identity',len(members)==1 and members[0].name==r['native_tar_member'] and members[0].isfile(),r['event']+' unique nativeA');ck('archive_members',digest(z.extractfile(members[0]).read())==r['file']['sha256'],r['event']+' native bytes')
 hs=headers(native);h=hs[0];native_headers[r['dp_id']]=h;mh=merged_headers[r['dp_id']];ck('native_headers',len(hs)==1 and [h['NAXIS2'],h['NAXIS1']]==[72,4096] and h['INSTRUME']=='HARPS' and h['OBJECT'].replace(' ','')=='HD106515A' and h['DATE-OBS']==mh['DATE-OBS'] and h['ESO DRS BERV']==mh['ESO DRS BERV'],r['event'])
 ck('native_identity',Path(r['native_tar_member']).name==mh['PROV1'].removesuffix('.fits')+'_e2ds_A.fits',r['event']+' exact raw identifier in TAR member')
 ck('native_headers',all(h.get(k)==v for k,v in r['primary_header'].items()) and h['EXPTIME']==mh['EXPTIME'] and h['MJD-OBS']==mh['MJD-OBS'],r['event']+' native header/exposure metadata')
 ck('native_headers',h.get('BUNIT') is None and r['flux_unit_header'] is None,r['event']+' native flux unit unspecified')
 spec=next(s for s in old['spectra'] if s['dp_id']==r['dp_id'])
 ck('native_identity',spec['ancillary_sha256']==r['ancillary_file']['sha256'] and spec['native_member']==r['native_tar_member'],r['event']+' historical native source binding')
 ck('mapping',r['orientation']=={k:spec['grid_best'][k] for k in r['orientation']}=={'row_flip':True,'argument_flip':True,'column_flip':False},r['event']+' unchanged orientation')
 for order in [3]:
  co=[h['ESO DRS CAL TH COEFF LL'+str(4*order+j)] for j in range(4)];tc=[h['ESO DRS CAL LOC CTR'+str(5*order+j)] for j in range(5)];ck('native_headers',h['ESO DRS CAL TH DEG LL']==3 and co==r['orders'][str(order)]['wavelength_coefficients_ascending'] and tc==r['orders'][str(order)]['trace_coefficients_ascending'],r['event']+str(order)+' coefficients')
  oldevent=next(x for x in old['events'] if x['review_id']==r['event']);known_feature=next(x['topocentric_air_angstrom'] for x in old['orders'] if x['review_id']==r['event'])
  original_event=source_events[r['event']];recomputed_feature=float(original_event['fitted_center_bary_air_angstrom'])/(1+mh['ESO DRS BERV']/C)
  ck('line_coverage',original_event['dp_id']==r['dp_id'] and abs(recomputed_feature-known_feature)<1e-10,r['event']+str(order)+' original center divided by own BERV')
  lo,hi=poly(co,0),poly(co,4095);covers=lo<known_feature<hi
  ck('line_coverage',r['covering_orders']==oldevent['covering_orders'] and (order in r['covering_orders'])==covers and abs(r['original_topocentric_feature_center_air_angstrom']-known_feature)<1e-10,r['event']+str(order)+' original feature coverage')
  ck('line_coverage',r['orders'][str(order)]['covers_original_center']==covers and all(abs(a-b)<1e-8 for a,b in zip(r['orders'][str(order)]['header_endpoint_topocentric_air_angstrom'],[lo,hi])),r['event']+str(order)+' endpoint metadata')
  if covers:
   oldrow=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==order);k=oldrow['native_pixel'];row=4095-k
   ck('mapping',oldrow['raw_row']==row and abs(poly(tc,row)-oldrow['raw_column'])<1e-8 and abs(poly(co,k)-oldrow['native_nearest_wave_angstrom'])<1e-8,r['event']+str(order)+' prior pixel mapping')
   final=oldrow['five_window_mapping_supported'];record=next(x for x in inv['mapping_records'] if x['event']==r['event'] and x['order']==order)
   ck('mapping',record['original_local_mapping_usable']==oldrow['local_mapping_usable'] and record['original_grid_mapping_usable']==oldrow['grid_mapping_usable'] and record['original_baseline_mapping_verified']==oldrow['baseline_mapping_verified'] and record['final_reference_mapping_supported']==final and record['registration_changed'] is False,r['event']+str(order)+' gate history')
   mapping_history.append({'event':r['event'],'order':order,'old_global':oldrow['grid_mapping_usable'],'old_local':oldrow['local_mapping_usable'],'old_baseline_verified':oldrow['baseline_mapping_verified'],'final_reference_supported':final,'native_pixel':k,'raw_row':row})
  else:
   exclusions.append({'event':r['event'],'order':order,'status':'NOT_COVERING_LINE','original_feature_center_topocentric_air_A':known_feature,'order_endpoint_topocentric_air_A':[lo,hi],'feature_exceeds_upper_endpoint_A':known_feature-hi,'common_first_anchor_center_topocentric_air_A':CT,'common_anchor_within_domain':lo<CT<hi,'reason':'The original event-specific feature is outside this order. Common-anchor context coverage cannot create a historical line-covering order or raw panel.'})
  derivative=lambda x:co[1]+2*co[2]*x+3*co[3]*x*x;vertices=[0.,4095.];v=-co[2]/(3*co[3]) if co[3] else -1
  if 0<v<4095:vertices.append(v)
  ck('wavelength_geometry',min(derivative(x) for x in vertices)>0,r['event']+str(order)+' monotone degree3 wavelength')
  if not covers:continue
  lo,hi=poly(co,0),poly(co,4095);grid=[j/100 for j in range(-300,301)]
  for frame in ['barycentric','topocentric']:
   requested=[(CB+x)/(1+mh['ESO DRS BERV']/C) if frame=='barycentric' else CT+x for x in grid];support=[lo<=q<=hi for q in requested]
   coverage.append({'event':r['event'],'dp_id':r['dp_id'],'order':order,'frame':frame,'native_wavelength_domain_air_A':[lo,hi],'grid_samples_geometrically_covered':sum(support),'core_covered':sum(ok and abs(x)<=.25+1e-12 for x,ok in zip(grid,support)),'negative_flank_covered':sum(ok and -3<=x<=-1.5 for x,ok in zip(grid,support)),'positive_flank_covered':sum(ok and 1.5<=x<=3 for x,ok in zip(grid,support))})
# Check all 72 header-only order geometries, once per unique product.
# None of these operations decodes spectral flux or detector pixels.
all_order_geometry=[]
for product in inv['native_products']:
 h=native_headers[product['dp_id']];mh=merged_headers[product['dp_id']]
 for order in range(72):
  co=[h['ESO DRS CAL TH COEFF LL'+str(4*order+j)] for j in range(4)]
  lo,hi=poly(co,0),poly(co,4095)
  derivative=lambda x:co[1]+2*co[2]*x+3*co[3]*x*x
  vertices=[0.,4095.];v=-co[2]/(3*co[3]) if co[3] else -1
  if 0<v<4095:vertices.append(v)
  mono=min(derivative(x) for x in vertices)>0
  covered=[e for e in product['discovery_for'] if lo<float(source_events[e]['fitted_center_bary_air_angstrom'])/(1+mh['ESO DRS BERV']/C)<hi]
  scan=next(x for x in inv['all_order_header_scan'] if x['dp_id']==product['dp_id'] and x['order']==order)
  ck('all_order_geometry',mono and scan['positive_wavelength_derivative_on_full_order'] is True and all(abs(a-b)<1e-8 for a,b in zip(scan['header_endpoint_topocentric_air_angstrom'],[lo,hi])),product['dp_id']+str(order)+' endpoints and monotonicity')
  ck('all_order_geometry',covered==scan['original_events_covered'] and bool(covered)==scan['covers_any_original_event_center']==scan['selected_for_profile']==(order==3),product['dp_id']+str(order)+' only order 3 covers original events')
  all_order_geometry.append({'dp_id':product['dp_id'],'order':order,'events_covered':covered,'positive_derivative':mono})
ck('scope',len(inv['all_order_header_scan'])==216 and len(all_order_geometry)==216,'all unique order headers accounted')
ck('deduplication',inv['unique_native_order_pairs']==[{'dp_id':r['dp_id'],'order':3} for r in inv['native_products']] and len({r['dp_id'] for r in inv['native_products']})==3,'exactly three unique product-order pairs')
ck('mapping_history',all(r['old_global'] is True and r['final_reference_supported'] is True and r['old_local'] is True and r['old_baseline_verified'] is True for r in mapping_history),'all three historical global/local/baseline/five-window gates preserved as true')
for r in inv['native_order_coverage']:
 oldrow=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order'])
 ck('line_coverage',r['dp_id']==oldrow['dp_id'] and r['order']==3 and r['selected_for_profile'] and r['saved_raw_panel_exists'] and abs(r['original_topocentric_feature_center_air_angstrom']-oldrow['topocentric_air_angstrom'])<1e-10,r['event']+' inventory coverage links exact old record')
# Old evidence ZIPs and NPY shape headers only.
e2=OLD/'raw_followup_batch02';e2m=read(e2/'EVIDENCE_ARCHIVE.json');parts=read(e2/'EVIDENCE_PARTS.json');data2=b''
for part in parts['parts']:
 b=(e2/part['path']).read_bytes();ck('evidence_archive',len(b)==part['bytes'] and digest(b)==part['sha256'],part['path']);data2+=b
ck('evidence_archive',len(data2)==e2m['bytes'] and digest(data2)==e2m['sha256'],'batch02 assembled evidence')
for r in inv['saved_native_raw_cutouts']:
 with zipfile.ZipFile(io.BytesIO(data2)) as z:ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256'],r['event']+str(r['order'])+' saved cutout')
 shape=[]
 with zipfile.ZipFile(REPO/r['file']['path']) as z:
  for name in z.namelist():
   with z.open(name) as f:
    assert f.read(6)==b'\x93NUMPY';v=tuple(f.read(2));n=struct.unpack('<H' if v==(1,0) else '<I',f.read(2 if v==(1,0) else 4))[0];assert n<65536;h=ast.literal_eval(f.read(n).decode('latin1'));shape.append({'key':name[:-4],'shape':list(h['shape']),'dtype':h['descr'],'fortran_order':h['fortran_order']})
 ck('NPY_headers',shape==r['npy_headers'],r['event']+str(r['order']))
ck('scope',len(coverage)==6 and len(mapping_history)==3 and not exclusions and not inv['excluded_native_orders'] and len(inv['saved_native_raw_cutouts'])==3,'three event covering-order panels and no structural exclusions')
historical_reviews={'adopted':[r for r in csv.DictReader((OLD/'raw_followup_batch02/ADOPTED_DISPOSITIONS.csv').open()) if r['review_id'] in expected_events]}
for label,name in [('primary','PRIMARY_VISUAL_REVIEW.json'),('secondary','SECONDARY_VISUAL_REVIEW.json'),('comparison','REVIEW_COMPARISON.json')]:
 historical_reviews[label]=[r for r in read(OLD/'raw_followup_batch02'/name)['events'] if r['review_id'] in expected_events]
for label,rows in historical_reviews.items():ck('review_custody',len(rows)==3 and rows==inv['historical_raw_review_records'][label],label+' exact prior records')
ck('review_custody',all(r['code']=='U' for r in historical_reviews['adopted']),'all three prior U decisions preserved')
baseline=read(PHASE/'BASELINE_VERIFICATION.json');diff=subprocess.run(['git','diff','--name-only',baseline['baseline_commit'],'--',str(OLD.relative_to(REPO))],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines();ck('immutability',not diff,'old extension02 tracked bytes unchanged')
summary={'schema':'HARPS_C004_INPUT_AUDIT_V1','status':'PASS' if not failures else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_sha256':sha(INV),'restore_script_sha256':sha(I/'restore_inputs.py'),'audit_script_sha256':sha(Path(__file__)),'baseline_commit':baseline['baseline_commit'],'check_count':sum(counts.values()),'checks_by_scope':counts,'failures':failures,'input_counts':{'merged':7,'native_A':3,'ancillary':3,'saved_cutouts':3,'archives':3},'anchor':{'dp_id':'ADP.2022-03-08T01:01:37.342','berv_km_s':ANCHOR,'barycentric_center_A':CB,'topocentric_center_A':CT},'merged_headers':merged_summary,'raw_identifier_timestamp_offsets':timestamp_offsets,'native_coverage':coverage,'mapping_gate_history':mapping_history,'excluded_native_orders':exclusions,'limits':['Coverage counts derive only from monotone header wavelength polynomials; finite flux, actual gaps and normalization remain unassessed.','Header-derived support is checked afresh for order 3, both fixed frames and both flanks. Finite flux or usable normalization cannot be inferred from geometric coverage.','Native BUNIT is absent; use native/instrumental flux labels, no asserted calibrated ADU equivalence to merged flux.','Inherited native topocentric air convention is traced to the old extractor; no new wavelength solution.','All historical local/global/baseline/five-window gates remain separate. All three events retain true historical global, local, baseline and later five-window gates; no new registration or mapping is performed.','ERR columns are declared unavailable; no positive uncertainty support is established.'],'source_hashes':inv['source_hashes'],'network_requests':0,'new_flux_or_pixel_values_interpreted':0,'raw_images_restored_or_read':False}
summary['prior_wavelength_overlap']={'completed_group':'C003','completed_center_bary_air_A':3869.75125,'C004_center_offset_A':CB-3869.75125,'C004_core_bary_air_A':[CB-.25,CB+.25],'C003_positive_reference_flank_bary_air_A':[3869.75125+1.5,3869.75125+3],'core_inside_prior_positive_flank':3869.75125+1.5<=CB-.25 and CB+.25<=3869.75125+3,'interpretation':'Geometry only; central flux already seen in C003 and seven observations reused. No blind or independent interpretation.'}
summary['additional_source_hashes']={str(p.relative_to(REPO)):sha(p) for p in [group_path,event_path]}
summary['all_order_header_geometry_count']=len(all_order_geometry)
summary['unique_native_coverage']=[dict({k:v for k,v in row.items() if k!='event'},discovery_for=next(p['discovery_for'] for p in inv['native_products'] if p['dp_id']==row['dp_id'])) for i,row in enumerate(coverage) if not any((prior['dp_id'],prior['order'],prior['frame'])==(row['dp_id'],row['order'],row['frame']) for prior in coverage[:i])]
summary['deduplication']='Three distinct event/product/raw-panel identities are retained, giving six product/order/frame contexts. All seven target observations are shared with earlier phases; the original C004 core lies within the completed C003 positive reference flank, so this is not untouched or independent validation.'
(HERE/'INPUT_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':summary['status'],'check_count':summary['check_count'],'failures':failures}));assert not failures
