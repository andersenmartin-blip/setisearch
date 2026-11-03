"""C009 identity/coverage audit: opaque hashes and FITS/NPY headers, no flux values."""
import ast,csv,datetime,hashlib,io,json,math,re,struct,subprocess,tarfile,zipfile
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent;I=PHASE/'inputs';OLD=REPO/'work_harps_20261101/v2/extension02'
INV=I/'INPUT_INVENTORY.json';C=299792.458;CB=6802.02;ANCHOR=3.26509772194068;CT=CB/(1+ANCHOR/C)
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
inv=read(INV);expected_inventory='961a3b767b16441bac13c260b5ff44254282788caea34f69ceb8f1ffd3ddd9e3';ck('inventory',sha(INV)==expected_inventory,'final inventory binding')
ck('inventory',sha(I/'restore_inputs.py')=='33b4074cad530f1e5fc0d3c22fe0f490926f27d3d48db3db386e5bc5a33d696c','final restore helper binding')
ck('anchor',inv['coordinate_anchor']=={'discovery_dp_id':'ADP.2023-03-23T01:02:04.831','discovery_berv_km_s':ANCHOR,'center_barycentric_air_angstrom':CB,'fixed_topocentric_air_angstrom':CT,'formula':'center_barycentric_air_angstrom/(1+discovery_berv_km_s/299792.458)'},'March 2023 discovery coordinate anchor')
group_path=OLD/'unresolved_context_20261102/CORE_OVERLAP_GROUPS.csv';group=next(r for r in csv.DictReader(group_path.open()) if r['group_id']=='C009')
event_path=OLD/'raw_followup_batch02/SELECTED_EVENTS.csv';source_events={r['review_id']:r for r in csv.DictReader(event_path.open())}
expected_events={'V2E2-0050'}
ck('scope',set(group['member_ids'].split('|'))==set(inv['events'])=={e for r in inv['native_products'] for e in r['discovery_for']}==expected_events and len(inv['native_products'])==1,'exact archived C009 membership')
ck('inventory',len(inv['files'])==10 and len({r['path'] for r in inv['files']})==10,'10 unique restored paths')
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
ck('scope',float(source_events['V2E2-0050']['fitted_center_bary_air_angstrom'])==CB,'original singleton center equals frozen metadata center')
ck('anchor',merged_headers['ADP.2023-03-23T01:02:04.831']['ESO DRS BERV']==ANCHOR,'first discovery anchor exact')
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
 for order in [70]:
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
   ck('mapping',record['dp_id']==r['dp_id'] and record['native_pixel']==k and record['raw_row']==row and record['raw_column']==oldrow['raw_column'],r['event']+str(order)+' exact prior raw coordinate identity')
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
   frame_endpoints=[q*(1+mh['ESO DRS BERV']/C) for q in [lo,hi]] if frame=='barycentric' else [lo,hi];center=CB if frame=='barycentric' else CT
   offsets=[q-center for q in frame_endpoints];geom=r['orders'][str(order)]['fixed_frame_header_geometry'][frame]
   ck('wavelength_geometry',all(abs(a-b)<1e-8 for a,b in zip(frame_endpoints,geom['header_endpoint_air_angstrom'])) and all(abs(a-b)<1e-8 for a,b in zip(offsets,geom['offset_endpoints_from_frame_center_angstrom'])) and geom['context_air_angstrom']==[center-3,center+3] and geom['core_air_angstrom']==[center-.25,center+.25],r['event']+str(order)+frame+' exact frame geometry')
   ck('wavelength_geometry',geom['full_context_geometrically_covered']==(offsets[0]<=-3 and offsets[1]>=3) and geom['full_core_geometrically_covered']==(offsets[0]<=-.25 and offsets[1]>=.25) and geom['negative_reference_flank_geometrically_covered']==(offsets[0]<=-3 and offsets[1]>=-1.5) and geom['positive_reference_flank_geometrically_covered']==(offsets[0]<=1.5 and offsets[1]>=3),r['event']+str(order)+frame+' coverage flags match independent endpoints')
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
  ck('all_order_geometry',covered==scan['original_events_covered'] and bool(covered)==scan['covers_any_original_event_center']==scan['selected_for_profile']==(order in [70]),product['dp_id']+str(order)+' only order 70 cover original event')
  all_order_geometry.append({'dp_id':product['dp_id'],'order':order,'events_covered':covered,'positive_derivative':mono})
ck('scope',len(inv['all_order_header_scan'])==72 and len(all_order_geometry)==72,'all unique order headers accounted')
ck('deduplication',inv['unique_native_order_pairs']==[{'dp_id':r['dp_id'],'order':order} for r in inv['native_products'] for order in [70]] and len({r['dp_id'] for r in inv['native_products']})==1,'exactly one unique order pair from one discovery product')
ck('mapping_history',all(r['old_global'] is True and r['final_reference_supported'] is True and r['old_local'] is True and r['old_baseline_verified'] is True and r['order']==70 and r['event']=='V2E2-0050' for r in mapping_history),'order 70 historical global/local/baseline/five-window support gates remain individually true')
for r in inv['native_order_coverage']:
 oldrow=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order'])
 ck('line_coverage',r['dp_id']==oldrow['dp_id'] and r['order']==70 and r['selected_for_profile'] and r['saved_raw_panel_exists'] and abs(r['original_topocentric_feature_center_air_angstrom']-oldrow['topocentric_air_angstrom'])<1e-10,r['event']+' inventory coverage links exact old record')
# Old evidence ZIPs and NPY shape headers only.
e2=OLD/'raw_followup_batch02';e2m=read(e2/'EVIDENCE_ARCHIVE.json');parts=read(e2/'EVIDENCE_PARTS.json');data2=b''
for part in parts['parts']:
 b=(e2/part['path']).read_bytes();ck('evidence_archive',len(b)==part['bytes'] and digest(b)==part['sha256'],part['path']);data2+=b
ck('evidence_archive',len(data2)==e2m['bytes'] and digest(data2)==e2m['sha256'],'batch02 assembled evidence')
for r in inv['saved_native_raw_cutouts']:
 oldpanel=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order']);ck('raw_source_identity',r['archive_member']==oldpanel['cutout'] and r['file']['sha256']==oldpanel['cutout_sha256'] and oldpanel['dp_id']=='ADP.2023-03-23T01:02:04.831','exact original mapped NPZ source')
 with zipfile.ZipFile(io.BytesIO(data2)) as z:ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256'],r['event']+str(r['order'])+' saved cutout')
 shape=[]
 with zipfile.ZipFile(REPO/r['file']['path']) as z:
  for name in z.namelist():
   with z.open(name) as f:
    assert f.read(6)==b'\x93NUMPY';v=tuple(f.read(2));n=struct.unpack('<H' if v==(1,0) else '<I',f.read(2 if v==(1,0) else 4))[0];assert n<65536;h=ast.literal_eval(f.read(n).decode('latin1'));shape.append({'key':name[:-4],'shape':list(h['shape']),'dtype':h['descr'],'fortran_order':h['fortran_order']})
 ck('NPY_headers',shape==r['npy_headers'],r['event']+str(r['order']))
ck('scope',len(coverage)==2 and len(mapping_history)==1 and not exclusions and not inv['excluded_native_orders'] and len(inv['saved_native_raw_cutouts'])==1,'one event covering-order panel and no original-line structural exclusions')
ck('scope',len(inv['archives'])==2 and len(inv['source_hashes'])==14 and len(inv['mapping_records'])==len(inv['native_order_coverage'])==1 and {(r['event'],r['order']) for r in inv['saved_native_raw_cutouts']}=={('V2E2-0050',70)},'exact archive, source, mapping and saved-panel scope')
historical_reviews={'adopted':[r for r in csv.DictReader((OLD/'raw_followup_batch02/ADOPTED_DISPOSITIONS.csv').open()) if r['review_id'] in expected_events]}
for label,name in [('primary','PRIMARY_VISUAL_REVIEW.json'),('secondary','SECONDARY_VISUAL_REVIEW.json'),('comparison','REVIEW_COMPARISON.json')]:
 historical_reviews[label]=[r for r in read(OLD/'raw_followup_batch02'/name)['events'] if r['review_id'] in expected_events]
for label,rows in historical_reviews.items():ck('review_custody',len(rows)==1 and rows==inv['historical_raw_review_records'][label],label+' exact prior records')
ck('review_custody',all(r['code']=='U' for r in historical_reviews['adopted']),'singleton prior U decision preserved')
ck('review_disagreement',historical_reviews['primary'][0]['code']=='A' and historical_reviews['secondary'][0]['code']=='A' and historical_reviews['comparison'][0]['primary']=='A' and historical_reviews['comparison'][0]['secondary']=='A' and historical_reviews['comparison'][0]['adopted']=='U','exact primary A / secondary A / root-adopted U distinction')
ck('review_disagreement',historical_reviews['adopted'][0]['primary_code']=='A' and historical_reviews['adopted'][0]['secondary_code']=='A' and historical_reviews['adopted'][0]['code']=='U' and 'artifact/spectral blend' in historical_reviews['adopted'][0]['evidence'] and 'underlying spectral contribution cannot be excluded' in historical_reviews['secondary'][0]['evidence'],'adopted uncertainty and secondary qualification preserved')
ck('review_disagreement','conservative override A to U' in historical_reviews['comparison'][0]['root_note'] and historical_reviews['adopted'][0]['final_physical_origin_confirmed']=='False','root override and unconfirmed origin preserved')
current_path=REPO/'work_harps_20261101/v2/CURRENT_V2_DISPOSITIONS.csv';queue_path=OLD/'unresolved_context_20261102/ACTION_QUEUE.csv'
current_rows=[r for r in csv.DictReader(current_path.open()) if r['review_id']=='V2E2-0050'];queue_rows=[r for r in csv.DictReader(queue_path.open()) if r['candidate_id']=='V2E2-0050']
ck('current_disposition',len(current_rows)==1 and current_rows[0]['current_code']=='U' and current_rows[0]['final_physical_origin_confirmed']=='False' and float(current_rows[0]['fitted_center_bary_air_angstrom'])==CB and current_rows[0]['dp_id']=='ADP.2023-03-23T01:02:04.831','current singleton U and unconfirmed origin at original center')
ck('original_queue',len(queue_rows)==1 and queue_rows[0]['queue_index']=='18' and queue_rows[0]['current_code_unchanged']=='U' and queue_rows[0]['core_overlap_group']=='C009' and queue_rows[0]['resolution_group']=='R010' and queue_rows[0]['primary_evidence_route']=='INDIVIDUAL_PROFILE_CONTEXT','original queue row18 route and adopted U preserved')
baseline=read(PHASE/'BASELINE_VERIFICATION.json');ck('immutability',baseline['baseline_commit']=='e3b4a2be111e60c48012159354f63de355a61e3b' and baseline['all_source_hashes_unchanged'] is True,'exact frozen baseline');diff=subprocess.run(['git','diff','--name-only',baseline['baseline_commit'],'--',str(OLD.relative_to(REPO))],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines();ck('immutability',not diff,'old extension02 tracked bytes unchanged')
prior_plan_paths=[REPO/('work_harps_20261102_'+g+'_context/analysis/PLAN.json') for g in ['c001','c003','c005','c006','c007','c004','c002','c008']]
prior_windows=[{'group':p.parents[1].name.split('_')[3].upper(),'center_bary_air_A':read(p)['group_center_bary_air_angstrom'],'window_bary_air_A':[read(p)['group_center_bary_air_angstrom']-3,read(p)['group_center_bary_air_angstrom']+3]} for p in prior_plan_paths]
ck('prior_dependency',all(read(p)['grid']['window_angstrom']==[-3,3] for p in prior_plan_paths) and all(CB-3>r['window_bary_air_A'][1] or CB+3<r['window_bary_air_A'][0] for r in prior_windows),'disjoint from exact eight prior frozen windows')
prior_diff=subprocess.run(['git','diff','--name-only',baseline['baseline_commit'],'--',*[str(p.relative_to(REPO)) for p in prior_plan_paths]],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines()
ck('immutability',not prior_diff,'prior eight method plans unchanged')
handoff_path=REPO/'work_harps_20261102_c008_context/NEXT_ACTION.json'
handoff=read(handoff_path)
ck('prior_dependency',handoff['events']==['V2E2-0050'] and handoff['catalog_center_bary_air_angstrom']==CB and handoff['discovery_anchor_dp_id']=='ADP.2023-03-23T01:02:04.831' and handoff['discovery_anchor_berv_km_s']==ANCHOR and handoff['wavelength_dependency']['overlaps_completed_or_current_C001_through_C008_bounded_windows'] is False,'exact C008 metadata handoff')
summary={'schema':'HARPS_C009_INPUT_AUDIT_V1','status':'PASS' if not failures else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_sha256':sha(INV),'restore_script_sha256':sha(I/'restore_inputs.py'),'audit_script_sha256':sha(Path(__file__)),'baseline_commit':baseline['baseline_commit'],'check_count':sum(counts.values()),'checks_by_scope':counts,'failures':failures,'input_counts':{'merged':7,'native_A':1,'ancillary':1,'saved_cutouts':1,'archives':2},'anchor':{'dp_id':'ADP.2023-03-23T01:02:04.831','berv_km_s':ANCHOR,'barycentric_center_A':CB,'topocentric_center_A':CT},'merged_headers':merged_summary,'raw_identifier_timestamp_offsets':timestamp_offsets,'native_coverage':coverage,'mapping_gate_history':mapping_history,'excluded_native_orders':exclusions,'limits':['Coverage counts derive only from monotone header wavelength polynomials; finite flux, actual gaps and normalization remain unassessed.','Header-derived support is checked afresh for order 70, both fixed frames and both flanks. Finite flux or usable normalization cannot be inferred from geometric coverage.','Native BUNIT is absent; use native/instrumental flux labels, no asserted calibrated ADU equivalence to merged flux.','Inherited native topocentric air convention is traced to the old extractor; no new wavelength solution.','All historical local/global/baseline/five-window gates remain separate and true for 0050 order 70; no new registration or mapping is performed.','ERR columns are declared unavailable; no positive uncertainty support is established.'],'source_hashes':inv['source_hashes'],'network_requests':0,'new_flux_or_pixel_values_interpreted':0,'raw_images_restored_or_read':False}
summary['prior_wavelength_dependency']={'C009_window_bary_air_A':[CB-3,CB+3],'completed_windows':prior_windows,'disjoint_from_C001_through_C008_contexts':True,'interpretation':'Wavelength windows differ, but the same seven observations and previously interpreted original epoch/native/raw evidence are reused. No untouched-data, blind-analysis or independent-observation claim follows.'}
summary['additional_source_hashes']={str(p.relative_to(REPO)):sha(p) for p in [group_path,event_path,handoff_path,current_path,queue_path,*prior_plan_paths]}
summary['historical_review_disagreement']={'primary_code':historical_reviews['primary'][0]['code'],'secondary_code':historical_reviews['secondary'][0]['code'],'root_adopted_code':historical_reviews['adopted'][0]['code'],'root_note':historical_reviews['comparison'][0]['root_note'],'qualification':historical_reviews['adopted'][0]['evidence'],'no_classification_performed_by_input_audit':True}
summary['all_order_header_geometry_count']=len(all_order_geometry)
summary['unique_native_coverage']=[dict({k:v for k,v in row.items() if k!='event'},discovery_for=next(p['discovery_for'] for p in inv['native_products'] if p['dp_id']==row['dp_id'])) for i,row in enumerate(coverage) if not any((prior['dp_id'],prior['order'],prior['frame'])==(row['dp_id'],row['order'],row['frame']) for prior in coverage[:i])]
summary['deduplication']='One event and one unique discovery product supply one native covering order and one preserved raw panel, giving two product/order/frame contexts. Both frames reuse the same exposure; all seven target epochs and original epoch/native/raw evidence remain shared observations.'
(HERE/'INPUT_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':summary['status'],'check_count':summary['check_count'],'failures':failures}));assert not failures
