"""C021 identity/coverage audit: opaque hashes and FITS/NPY headers, no flux values."""
import argparse,ast,csv,datetime,hashlib,io,json,math,re,struct,subprocess,tarfile,zipfile
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent;I=PHASE/'inputs';OLD=REPO/'work_harps_20261101/v2/extension02'
INV=I/'INPUT_INVENTORY.json';C=299792.458;CB=4309.82625;ANCHOR=29.658729150824;CT=CB/(1+ANCHOR/C)
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
inv=read(INV);expected_inventory='61c26f45548618c783ad71bd2f6eb79d82528740918d2de67e58a924ccc09fd0';ck('inventory',sha(INV)==expected_inventory,'final inventory binding')
ck('inventory',sha(I/'restore_inputs.py')=='00c96f8584c58506d7da4c9e67604a648eefb55b1e0a65272cbd6cf396f64470','final restore helper binding')
ck('anchor',inv['coordinate_anchor']=={'discovery_dp_id':'ADP.2022-01-22T01:09:14.958','anchor_selection_rule':'First member in original ACTION_QUEUE fixes one common group topocentric anchor; all five discovery products remain separate references.','original_member_centers_barycentric_air_angstrom':{'V2E2-0116':4309.827499999999,'V2E2-0121':4309.827499999999,'V2E2-0126':4309.825,'V2E2-0130':4309.825,'V2E2-0139':4309.827499999999},'group_center_rule':'Midpoint of exact minimum/maximum member catalog centers; exact individual cores remain distinct, without post-value expansion.','discovery_berv_km_s':ANCHOR,'center_barycentric_air_angstrom':CB,'fixed_topocentric_air_angstrom':CT,'formula':'center_barycentric_air_angstrom/(1+discovery_berv_km_s/299792.458)'},'first-queue January anchor and separate five exact member centers')
group_path=OLD/'unresolved_context_20261102/CORE_OVERLAP_GROUPS.csv';group=next(r for r in csv.DictReader(group_path.open()) if r['group_id']=='C021')
event_path=OLD/'raw_followup_batch03/SELECTED_EVENTS.csv';original_event_path=OLD/'raw_followup/SELECTED_EVENTS.csv';source_events={r['review_id']:r for p in [original_event_path,event_path] for r in csv.DictReader(p.open())}
event_centers={'V2E2-0116':4309.827499999999,'V2E2-0121':4309.827499999999,'V2E2-0126':4309.825,'V2E2-0130':4309.825,'V2E2-0139':4309.827499999999};expected_events=set(event_centers);expected_products={'V2E2-0116':'ADP.2022-01-22T01:09:14.958','V2E2-0121':'ADP.2022-02-06T01:07:28.382','V2E2-0126':'ADP.2022-05-06T01:04:00.123','V2E2-0130':'ADP.2023-01-17T01:07:48.581','V2E2-0139':'ADP.2023-07-02T01:01:43.311'}
ck('scope',set(group['member_ids'].split('|'))==set(inv['events'])=={e for r in inv['native_products'] for e in r['discovery_for']}==expected_events and len(inv['native_products'])==5,'exact archived C021 membership')
ck('inventory',len(inv['files'])==22 and len({r['path'] for r in inv['files']})==22,'22 unique restored paths')
for r in inv['files']:
 p=(REPO/r['path']).resolve();p.relative_to(I);ck('restored_bytes',p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],p.name)
for path,h in inv['source_hashes'].items():ck('historical_sources',sha(REPO/path)==h,path)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-dir',type=Path,action='append',default=[]);args=parser.parse_args();archive_dirs=args.archive_dir or [REPO.parent/'c010_archive_cache',REPO.parent/'c016_archive_cache',REPO.parent/'c018_archive_cache'];archivepaths={}
historical_archives=read(OLD/'checkpoints/INPUT_CHECKPOINTS.json')['parts']+read(OLD/'raw_followup/checkpoints/RAW_INPUT_CHECKPOINTS.json')['parts']+read(OLD/'raw_followup_batch03/checkpoints/INPUT_ARCHIVES.json')['archives']
for r in inv['archives']:
 matches=[x for x in historical_archives if x['filename']==r['filename']];ck('archive',len(matches)==1 and all(matches[0][k]==r[k] for k in ['bytes','sha256']),r['filename']+' historical archive identity')
 candidates=[p for d in archive_dirs for p in d.rglob(r['filename']) if p.is_file()];ck('archive',len(candidates)==1,r['filename']+' one exact local archive');p=candidates[0];ck('archive',p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],r['filename']);archivepaths[r['filename']]=p
science_archive=next(p for n,p in archivepaths.items() if 'EXTENSION02_INPUTS' in n)
checks=read(OLD/'epoch_followup/INPUT_CHECKS.json');previous={r['dp_id']:r for r in checks if r['target']=='HD114783'};ck('merged_identity',set(previous)=={r['dp_id'] for r in inv['merged_spectra']},'exact prior seven epochs')
ck('merged_identity',len({r['raw_id'] for r in inv['merged_spectra']})==7,'seven unique progenitors')
ck('target_cohort',inv['target']=='HD114783' and all(r['target']=='HD114783' for r in previous.values()),'existing target-specific cohort only')
ck('target_cohort',abs(max(r['berv_km_s'] for r in inv['merged_spectra'])-min(r['berv_km_s'] for r in inv['merged_spectra'])-59.073251754930496)<1e-12,'own HD114783 BERV span, no old target span transfer')
merged_headers={};merged_summary=[]
with zipfile.ZipFile(science_archive) as z:
 for r in inv['merged_spectra']:
  p=REPO/r['file']['path'];ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256']==previous[r['dp_id']]['sha256'],r['dp_id'])
  hs=headers(p);ck('merged_headers',len(hs)==2 and hs[0]['NAXIS']==0 and hs[1]['XTENSION']=='BINTABLE' and hs[1]['NAXIS2']==1,r['dp_id']+' structure');ph,th=hs
  ck('merged_headers',all(ph.get(k)==v for k,v in r['primary_header'].items()) and all(th.get(k)==v for k,v in r['table_header'].items()),r['dp_id']+' inventory headers')
  prov=[c.value.removesuffix('.fits') for c in ph.cards if re.fullmatch(r'PROV\d+',c.keyword)];ck('merged_identity',prov==[r['raw_id']] and ph['ARCFILE']==r['dp_id']+'.fits' and ph['OBJECT'].replace(' ','')=='HD114783' and ph['INSTRUME']=='HARPS',r['dp_id']+' identity')
  original=download[r['dp_id']];ck('merged_identity',r['raw_id']==original['expected_raw_progenitor_id'] and r['file']['sha256']==original['sha256'],r['dp_id']+' original PROV1 custody')
  delta=(datetime.datetime.fromisoformat(r['raw_id'].removeprefix('HARPS.'))-datetime.datetime.fromisoformat(ph['DATE-OBS'])).total_seconds()*1000
  ck('dates',abs(delta)<=10 and ph['DATE-OBS']==previous[r['dp_id']]['date_obs'] and abs(ph['MJD-OBS']-previous[r['dp_id']]['mjd_obs'])<1e-8,r['dp_id']+' raw identifier vs DATE-OBS')
  timestamp_offsets.append({'dp_id':r['dp_id'],'raw_id':r['raw_id'],'header_DATE_OBS':ph['DATE-OBS'],'raw_identifier_minus_header_milliseconds':delta,'policy':'Exact identifiers preserved; existing millisecond offset recorded, not string-normalized.'})
  ck('merged_units',ph['SPECSYS']=='BARYCENT' and ph['NCOMBINE']==1 and ph['FLUXCAL']=='UNCALIBRATED' and ph['SPEC_RES']==115000 and th['TUNIT1']=='angstrom' and th['TUNIT2']==th['TUNIT3']=='adu' and 'obs.atmos' in th['TUCD1'],r['dp_id'])
  formats=[re.fullmatch(r'([1-9][0-9]*)([DE])',th['TFORM'+str(i)]) for i in [1,2,3]];ck('merged_headers',all(formats) and len({int(m[1]) for m in formats if m})==1 and [th['TTYPE'+str(i)] for i in [1,2,3]]==['WAVE','FLUX','ERR'],r['dp_id']+' vectors')
  ck('merged_headers',math.isfinite(ph['ESO DRS BERV']) and abs(ph['ESO DRS BERV'])<100 and ph['ESO DRS BERV']==r['berv_km_s']==previous[r['dp_id']]['berv_km_s'],r['dp_id']+' BERV')
  ck('merged_headers','not available' in th.get('TCOMM3','').lower(),r['dp_id']+' unavailable ERR explicitly retained')
  merged_headers[r['dp_id']]=ph;merged_summary.append({'dp_id':r['dp_id'],'berv_km_s':ph['ESO DRS BERV'],'date_obs':ph['DATE-OBS'],'wavelength_unit':'air Angstrom','frame':'BARYCENT','flux_unit':'ADU, uncalibrated','ERR':'Declared unavailable/NaN; no sample values read'})
ck('scope',{e:float(source_events[e]['fitted_center_bary_air_angstrom']) for e in expected_events}==event_centers and {e:source_events[e]['dp_id'] for e in expected_events}==expected_products and (min(event_centers.values())+max(event_centers.values()))/2==CB,'exact individual centers, five exact discovery identities and fixed metadata midpoint')
ck('anchor',merged_headers['ADP.2022-01-22T01:09:14.958']['ESO DRS BERV']==ANCHOR,'first-queue January discovery anchor exact')
old_maps={'batch03':read(OLD/'raw_followup_batch03/NATIVE_MAPPING.json'),'original':read(OLD/'raw_followup/NATIVE_MAPPING.json')};later_mapping=read(OLD/'raw_followup/mapping_followup/MAPPING_AUDIT.json');coverage=[];mapping_history=[];exclusions=[]
archive_names={};native_headers={}
for name,ap in archivepaths.items():
 with zipfile.ZipFile(ap) as z:archive_names[name]=set(z.namelist())
for r in [dict(p,event=e,original_topocentric_feature_center_air_angstrom=p['original_event_centers_topocentric_air_angstrom'][e]) for p in inv['native_products'] for e in p['discovery_for']]:
 old=old_maps['original' if r['event']=='V2E2-0130' else 'batch03']
 anc=REPO/r['ancillary_file']['path'];native=REPO/r['file']['path'];ap=next(p for n,p in archivepaths.items() if r['ancillary_archive_member'] in archive_names[n])
 with zipfile.ZipFile(ap) as z:ck('archive_members',digest(z.read(r['ancillary_archive_member']))==r['ancillary_file']['sha256'],r['event']+' ancillary')
 with tarfile.open(anc) as z:
  members=[m for m in z if m.name.endswith('_e2ds_A.fits')];ck('native_identity',len(members)==1 and members[0].name==r['native_tar_member'] and members[0].isfile(),r['event']+' unique nativeA');ck('archive_members',digest(z.extractfile(members[0]).read())==r['file']['sha256'],r['event']+' native bytes')
 hs=headers(native);h=hs[0];native_headers[r['dp_id']]=h;mh=merged_headers[r['dp_id']];ck('native_headers',len(hs)==1 and [h['NAXIS2'],h['NAXIS1']]==[72,4096] and h['INSTRUME']=='HARPS' and h['OBJECT'].replace(' ','')=='HD114783' and h['DATE-OBS']==mh['DATE-OBS'] and h['ESO DRS BERV']==mh['ESO DRS BERV'],r['event'])
 ck('native_identity',Path(r['native_tar_member']).name==mh['PROV1'].removesuffix('.fits')+'_e2ds_A.fits',r['event']+' exact raw identifier in TAR member')
 ck('native_headers',all(h.get(k)==v for k,v in r['primary_header'].items()) and h['EXPTIME']==mh['EXPTIME'] and h['MJD-OBS']==mh['MJD-OBS'],r['event']+' native header/exposure metadata')
 ck('native_headers',h.get('BUNIT') is None and r['flux_unit_header'] is None,r['event']+' native flux unit unspecified')
 spec=next(s for s in old['spectra'] if s['dp_id']==r['dp_id'])
 ck('native_identity',spec['ancillary_sha256']==r['ancillary_file']['sha256'] and spec['native_member']==r['native_tar_member'],r['event']+' historical native source binding')
 ck('mapping',r['orientation']=={k:spec['grid_best'][k] for k in r['orientation']}=={'row_flip':True,'argument_flip':True,'column_flip':False},r['event']+' unchanged orientation')
 # Discover coverage from all header polynomials before consulting stored covering-order lists.
 for order in [o for o in range(72) if poly([h['ESO DRS CAL TH COEFF LL'+str(4*o+j)] for j in range(4)],0)<r['original_topocentric_feature_center_air_angstrom']<poly([h['ESO DRS CAL TH COEFF LL'+str(4*o+j)] for j in range(4)],4095)]:
  co=[h['ESO DRS CAL TH COEFF LL'+str(4*order+j)] for j in range(4)];tc=[h['ESO DRS CAL LOC CTR'+str(5*order+j)] for j in range(5)];ck('native_headers',h['ESO DRS CAL TH DEG LL']==3 and co==r['orders'][str(order)]['wavelength_coefficients_ascending'] and tc==r['orders'][str(order)]['trace_coefficients_ascending'],r['event']+str(order)+' coefficients')
  oldevent=next(x for x in old['events'] if x['review_id']==r['event']);known_feature=next(x['topocentric_air_angstrom'] for x in old['orders'] if x['review_id']==r['event'] and x['order']==order)
  original_event=source_events[r['event']];recomputed_feature=float(original_event['fitted_center_bary_air_angstrom'])/(1+mh['ESO DRS BERV']/C)
  ck('line_coverage',original_event['dp_id']==r['dp_id'] and abs(recomputed_feature-known_feature)<1e-10,r['event']+str(order)+' original center divided by own BERV')
  lo,hi=poly(co,0),poly(co,4095);covers=lo<known_feature<hi
  ck('line_coverage',r['covering_orders']==oldevent['covering_orders'] and (order in r['covering_orders'])==covers and abs(r['original_topocentric_feature_center_air_angstrom']-known_feature)<1e-10,r['event']+str(order)+' original feature coverage')
  ck('line_coverage',r['orders'][str(order)]['covers_original_center']==covers and all(abs(a-b)<1e-8 for a,b in zip(r['orders'][str(order)]['header_endpoint_topocentric_air_angstrom'],[lo,hi])),r['event']+str(order)+' endpoint metadata')
  if covers:
   oldrow=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==order);k=oldrow['native_pixel'];row=4095-k
   ck('mapping',oldrow['raw_row']==row and abs(poly(tc,row)-oldrow['raw_column'])<1e-8 and abs(poly(co,k)-oldrow['native_nearest_wave_angstrom'])<1e-8,r['event']+str(order)+' prior pixel mapping')
   baseline_verified=oldrow.get('baseline_mapping_verified',oldrow.get('mapping_verified'));final=(next(x for x in later_mapping['orders'] if x['review_id']==r['event'] and x['order']==order)['reference_mapping_supported'] if r['event']=='V2E2-0130' else oldrow['five_window_mapping_supported']);record=next(x for x in inv['mapping_records'] if x['event']==r['event'] and x['order']==order)
   ck('mapping',record['original_local_mapping_usable']==oldrow['local_mapping_usable'] and record['original_grid_mapping_usable']==oldrow['grid_mapping_usable'] and record['original_baseline_mapping_verified']==baseline_verified and record['final_reference_mapping_supported']==final and record['registration_changed'] is False,r['event']+str(order)+' gate history')
   ck('mapping',record['dp_id']==r['dp_id'] and record['native_pixel']==k and record['raw_row']==row and record['raw_column']==oldrow['raw_column'],r['event']+str(order)+' exact prior raw coordinate identity')
   mapping_history.append({'event':r['event'],'order':order,'old_global':oldrow['grid_mapping_usable'],'old_local':oldrow['local_mapping_usable'],'old_baseline_verified':baseline_verified,'final_reference_supported':final,'native_pixel':k,'raw_row':row,'raw_column':oldrow['raw_column'],'original_mapping_source':'raw_followup/NATIVE_MAPPING.json' if r['event']=='V2E2-0130' else 'raw_followup_batch03/NATIVE_MAPPING.json'})
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
   coverage.append({'event':r['event'],'dp_id':r['dp_id'],'order':order,'frame':frame,'native_wavelength_domain_air_A':[lo,hi],'fixed_frame_header_endpoint_air_A':frame_endpoints,'fixed_frame_offset_endpoint_air_A':offsets,'grid_samples_geometrically_covered':sum(support),'core_covered':sum(ok and abs(x)<=.25+1e-12 for x,ok in zip(grid,support)),'negative_flank_covered':sum(ok and -3<=x<=-1.5 for x,ok in zip(grid,support)),'positive_flank_covered':sum(ok and 1.5<=x<=3 for x,ok in zip(grid,support))})
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
  ck('all_order_geometry',covered==scan['original_events_covered'] and bool(covered)==scan['covers_any_original_event_center']==scan['selected_for_profile']==(order==19),product['dp_id']+str(order)+' only order19 covers each original event')
  ck('all_order_common_geometry',scan['covers_common_fixed_barycentric_center']==(lo<=CB/(1+mh['ESO DRS BERV']/C)<=hi) and scan['covers_common_fixed_topocentric_anchor']==(lo<=CT<=hi),product['dp_id']+str(order)+' separate common B/T center coverage')
  all_order_geometry.append({'dp_id':product['dp_id'],'order':order,'events_covered':covered,'positive_derivative':mono})
ck('scope',len(inv['all_order_header_scan'])==360 and len(all_order_geometry)==360,'all unique order headers accounted')
failed_original_events={'V2E2-0116','V2E2-0126','V2E2-0130'}
ck('deduplication',inv['unique_native_order_pairs']==[{'dp_id':r['dp_id'],'order':19} for r in inv['native_products']] and len({r['dp_id'] for r in inv['native_products']})==5,'five distinct product/order19 pairs from five discovery references')
for event in sorted(expected_events):
 records=[r for r in mapping_history if r['event']==event];original_ok=event not in failed_original_events
 ck('mapping_history',len(records)==1 and records[0]['order']==19 and tuple(records[0][k] for k in ['old_global','old_local','old_baseline_verified','final_reference_supported'])==(True,original_ok,original_ok,True),event+' separate original global/local/baseline and later true gates')
for r in inv['mapping_records']:
 is_original=r['event']=='V2E2-0130';source_path=OLD/('raw_followup/NATIVE_MAPPING.json' if is_original else 'raw_followup_batch03/NATIVE_MAPPING.json');later_path=OLD/('raw_followup/mapping_followup/MAPPING_AUDIT.json' if is_original else 'raw_followup_batch03/NATIVE_MAPPING.json');basis='mapping_verified in original raw_followup mapping' if is_original else 'explicit baseline_mapping_verified in batch03 mapping'
 ck('mapping_source_identity',r['original_mapping_source']==str(source_path.relative_to(REPO)) and r['baseline_field_basis']==basis and r.get('later_mapping_source',r['original_mapping_source'])==str(later_path.relative_to(REPO)),r['event']+' exact original/later source and baseline-field basis')
for r in inv['native_order_coverage']:
 old=old_maps['original' if r['event']=='V2E2-0130' else 'batch03'];oldrow=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order'])
 ck('line_coverage',r['dp_id']==oldrow['dp_id']==expected_products[r['event']] and r['order']==19 and r['selected_for_profile'] and r['saved_raw_panel_exists'] and abs(r['original_topocentric_feature_center_air_angstrom']-oldrow['topocentric_air_angstrom'])<1e-10,r['event']+' exact original order19 coverage/raw record')
# Opaque original evidence archive/member hashes; only NPY shape/dtype headers are decoded.
batch=OLD/'raw_followup_batch03';batch_meta=read(batch/'EVIDENCE_ARCHIVE.json');batch_parts=read(batch/'EVIDENCE_PARTS.json');batch_bytes=b''
for part in batch_parts['parts']:
 b=(batch/part['path']).read_bytes();ck('evidence_archive',len(b)==part['bytes'] and digest(b)==part['sha256'],part['path']);batch_bytes+=b
ck('evidence_archive',len(batch_bytes)==batch_meta['bytes'] and digest(batch_bytes)==batch_meta['sha256'],'batch03 complete original evidence archive')
original=OLD/'raw_followup';original_manifest=read(original/'RAW_BASELINE_EVIDENCE_MANIFEST.json');original_archive=original/original_manifest['archive'];original_bytes=original_archive.read_bytes()
ck('evidence_archive',len(original_bytes)==original_manifest['archive_bytes'] and digest(original_bytes)==original_manifest['archive_sha256'],'0128 exact original baseline evidence archive')
original_members={r['path']:r for r in original_manifest['members']}
for r in inv['saved_native_raw_cutouts']:
 is_original=r['event']=='V2E2-0130';old=old_maps['original' if is_original else 'batch03'];oldpanel=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order']);expected_sha=original_members[oldpanel['cutout']]['sha256'] if is_original else oldpanel['cutout_sha256'];expected_bytes=original_members[oldpanel['cutout']]['bytes'] if is_original else r['file']['bytes']
 ck('raw_source_identity',r['archive_member']==oldpanel['cutout'] and r['file']['sha256']==expected_sha and r['file']['bytes']==expected_bytes and oldpanel['dp_id']==expected_products[r['event']],r['event']+' exact original order '+str(r['order'])+' panel custody')
 with zipfile.ZipFile(io.BytesIO(original_bytes if is_original else batch_bytes)) as z:ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256'],r['event']+str(r['order'])+' original panel member')
 shape=[]
 with zipfile.ZipFile(REPO/r['file']['path']) as z:
  for name in z.namelist():
   with z.open(name) as f:
    assert f.read(6)==b'\x93NUMPY';v=tuple(f.read(2));n=struct.unpack('<H' if v==(1,0) else '<I',f.read(2 if v==(1,0) else 4))[0];assert n<65536;h=ast.literal_eval(f.read(n).decode('latin1'));shape.append({'key':name[:-4],'shape':list(h['shape']),'dtype':h['descr'],'fortran_order':h['fortran_order']})
 ck('NPY_headers',shape==r['npy_headers'],r['event']+str(r['order'])+' metadata only')
ck('scope',len(coverage)==10 and len(mapping_history)==5 and not exclusions and not inv['excluded_native_orders'] and len(inv['saved_native_raw_cutouts'])==5,'five original panels and ten fixed-frame order19 contexts')
ck('scope',len(inv['archives'])==5 and len(inv['source_hashes'])==34 and len(inv['mapping_records'])==len(inv['native_order_coverage'])==5 and {(r['event'],r['order']) for r in inv['saved_native_raw_cutouts']}=={(e,19) for e in expected_events},'exact archive/source/mapping/panel scope')
# Six batch03 histories retain original U/U/U. 0130 retains its distinct earlier I/M/I stages.
batch_events=expected_events-{'V2E2-0130'};batch_reviews={'adopted':[r for r in csv.DictReader((batch/'ADOPTED_DISPOSITIONS.csv').open()) if r['review_id'] in batch_events]}
for label,name in [('primary','PRIMARY_VISUAL_REVIEW.json'),('secondary','SECONDARY_VISUAL_REVIEW.json'),('comparison','REVIEW_COMPARISON.json')]:
 batch_reviews[label]=[r for r in read(batch/name)['events'] if r['review_id'] in batch_events]
for label,rows in batch_reviews.items():ck('review_custody',len(rows)==4 and {r['review_id'] for r in rows}==batch_events,label+' all four exact batch03 records')
for event in sorted(batch_events):
 primary=next(r for r in batch_reviews['primary'] if r['review_id']==event);secondary=next(r for r in batch_reviews['secondary'] if r['review_id']==event);adopted=next(r for r in batch_reviews['adopted'] if r['review_id']==event);comparison=next(r for r in batch_reviews['comparison'] if r['review_id']==event)
 ck('review_chain',primary['code']==secondary['code']==adopted['code']==adopted['primary_code']==adopted['secondary_code']==comparison['primary']==comparison['secondary']==comparison['adopted']=='U',event+' original primary/secondary/adopted U/U/U')
 ck('review_chain',primary['covering_orders']==secondary['covering_orders']==[19] and secondary['baseline_all_orders_mapping_verified'] is (event not in failed_original_events) and adopted['final_physical_origin_confirmed']=='False',event+' event-specific original baseline stage and unconfirmed origin retained')
original_primary=next(r for r in read(original/'PRIMARY_VISUAL_REVIEW.json')['rows'] if r['review_id']=='V2E2-0130');original_secondary=read(original/'audit/INDEPENDENT_VISUAL_NOTES.json')['notes']['V2E2-0130'];agreement=next(r for r in read(original/'REVIEW_AGREEMENT.json')['rows'] if r['review_id']=='V2E2-0130');baseline_row=next(r for r in csv.DictReader((original/'BASELINE_SELECTED_EVENT_DISPOSITIONS.csv').open()) if r['review_id']=='V2E2-0130')
ck('review_0130_original',original_primary['primary_code']=='I' and original_primary['primary_disposition']=='INSUFFICIENT_LOCAL_RAW_MAPPING' and original_primary['all_covering_orders_mapping_verified'] is False and original_primary['final_physical_origin_confirmed'] is False,'0130 original primary insufficient-mapping I retained')
ck('review_0130_original',original_secondary[0]=='M' and agreement['primary_code']=='I' and agreement['second_code_original']=='M' and agreement['second_code_normalized']=='I' and agreement['agree'] is True and baseline_row['baseline_code']=='I' and baseline_row['baseline_disposition']=='INSUFFICIENT_LOCAL_RAW_MAPPING','0130 original secondary M normalized I and adopted baseline I retained')
later=original/'mapping_followup';later_first=read(later/'FIRST_VISUAL_NOTES.json')['notes']['V2E2-0130'];later_second=read(later/'SECOND_VISUAL_NOTES.json')['notes']['V2E2-0130'];later_row=next(r for r in csv.DictReader((later/'FOLLOWUP_DISPOSITIONS.csv').open()) if r['review_id']=='V2E2-0130');later_summary=read(later/'FINAL_REVIEW_SUMMARY.json');later_meta=read(later/'EVIDENCE_ARCHIVE.json');later_archive=later/later_meta['filename']
ck('evidence_archive',later_archive.stat().st_size==later_meta['bytes'] and sha(later_archive)==later_meta['sha256'],'0130 completed mapping-followup archive identity')
ck('review_0130_later',later_first[0]==later_second[0]==later_row['proposed_code']=='U' and later_row['baseline_code']=='I' and later_row['baseline_status']=='INSUFFICIENT_LOCAL_RAW_MAPPING' and later_row['final_physical_origin_confirmed']=='False','0130 later U/U followup keeps original I baseline and origin unconfirmed')
ck('review_0130_later',later_mapping['coordinates_changed'] is False and later_summary['coordinates_changed'] is False and later_summary['original_raw_pixels_and_native_samples_preserved'] is True and later_row['coordinates_changed']=='False' and later_row['original_native_and_raw_pixels_preserved']=='True','0130 unchanged-coordinate and original-pixel-preservation declarations retained as recorded metadata')
later_container_records=[]
with zipfile.ZipFile(later_archive) as z:
 for r in [r for r in later_meta['files'] if 'V2E2-0130_o' in r['path']]:
  members=[n for n in z.namelist() if n==r['path'] or r['path'].endswith(n)]
  ck('evidence_archive',len(members)==1 and len(z.read(members[0]))==r['bytes'] and digest(z.read(members[0]))==r['sha256'],'0130 later container exact bytes; not substituted for original panel')
  later_container_records.append(r)
for order in [19]:
 before=next(r for r in old_maps['original']['orders'] if r['review_id']=='V2E2-0130' and r['order']==order);after=next(r for r in later_mapping['orders'] if r['review_id']=='V2E2-0130' and r['order']==order)
 ck('review_0130_later',all(before[k]==after[k] for k in ['review_id','dp_id','order','native_pixel','raw_row','raw_column','cutout','topocentric_air_angstrom']) and after['previous_mapping_verified']==before['mapping_verified'] and after['reference_mapping_supported'] is True,'0130 order '+str(order)+' exact original coordinates/stage retained in later followup')
history=inv['historical_raw_review_records']
for label,rows in batch_reviews.items():ck('review_custody',rows==history['batch03_original'][label],label+' exact original records copied into inventory without 0130 flattening')
later_verification=read(later/'VERIFICATION.json');original_current=next(r for r in csv.DictReader((original/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv').open()) if r['review_id']=='V2E2-0130')
expected_0130={'original_primary':original_primary,'original_secondary_source_record':original_secondary,'original_review_agreement':agreement,'original_adopted_baseline':baseline_row,'current_adopted_record':original_current,'later_primary_source_record':later_first,'later_secondary_source_record':later_second,'later_disposition_record':later_row,'later_mapping_records':[r for r in later_mapping['orders'] if r['review_id']=='V2E2-0130'],'later_verification_record':later_verification,'later_evidence_archive':{k:later_meta[k] for k in ['filename','bytes','sha256']},'later_preservation_declarations':{k:later_summary[k] for k in ['coordinates_changed','original_raw_pixels_and_native_samples_preserved','baseline_files_unchanged','original_catalogs_unchanged']},'later_wider_containers_are_distinct_from_original_baseline_panels':True,'new_pixel_equality_test_performed':False}
ck('review_custody',history['separate_raw_followup_0130']==expected_0130,'all exact 0130 original/later records and explicit no-new-pixel-test limit')
ck('review_0130_later',later_verification['status']=='PASS_EXACT_FRESH_PROCESS_RECONSTRUCTION_ALL_FOUR_EXPOSURES' and next(r for r in later_verification['exposures'] if r['dp_id']==expected_products['V2E2-0130'])['all_original_raw_native_samples_and_coordinates_exact'] is True,'completed original wider reconstruction is preserved as prior evidence, not rerun')

current_path=REPO/'work_harps_20261101/v2/CURRENT_V2_DISPOSITIONS.csv';queue_path=OLD/'unresolved_context_20261102/ACTION_QUEUE.csv'
current_rows=[r for r in csv.DictReader(current_path.open()) if r['review_id'] in expected_events];queue_rows=[r for r in csv.DictReader(queue_path.open()) if r['candidate_id'] in expected_events];expected_queue={'V2E2-0116':'35','V2E2-0121':'40','V2E2-0126':'44','V2E2-0130':'48','V2E2-0139':'55'}
ck('current_disposition',len(current_rows)==5 and {r['review_id'] for r in current_rows}==expected_events and all(r['current_code']=='U' and r['final_physical_origin_confirmed']=='False' and float(r['fitted_center_bary_air_angstrom'])==event_centers[r['review_id']] and r['dp_id']==expected_products[r['review_id']] for r in current_rows),'all five exact current U labels/individual centers/discovery products, distinct from original 0130 baseline I')
ck('review_custody',history['current_adopted']==current_rows,'exact five root-current records retained separately from original review stages')
ck('original_queue',len(queue_rows)==5 and {r['candidate_id']:r['queue_index'] for r in queue_rows}==expected_queue and all(r['current_code_unchanged']=='U' and r['core_overlap_group']=='C021' and r['resolution_group']=='R022' and r['primary_evidence_route']=='JOINT_PROFILE_CONTEXT' for r in queue_rows),'exact full original joint queue group and route retained')
baseline=read(PHASE/'BASELINE_VERIFICATION.json')
ck('immutability',baseline['baseline_commit']=='b4728c70f901ae2b7e9eb4f344981a5db900e691' and baseline['previous_state_sha256']=='73e2470696e3d55524d3d0ef0199f2b9c56801ebc3a6d344952f6038ce7518f3' and baseline['previous_source_hashes_verified_exact_local_and_public']==2610 and baseline['tracked_and_index_diffs_empty'] is True and baseline['new_observed_arrays_read'] is False,'exact GREEN C019 baseline and prior-state custody')
prior_plan_paths=[REPO/('work_harps_20261102_'+g+'_context/analysis/PLAN.json') for g in ['c001','c003','c005','c006','c007','c004','c002','c008']]+[REPO/('work_harps_20261103_'+g+'_context/analysis/PLAN.json') for g in ['c009','c010','c012','c011','c016','c015','c018','c019']]
prior_windows=[];group_rows={r['group_id']:r for r in csv.DictReader(group_path.open())};current_dp_ids={r['dp_id'] for r in inv['merged_spectra']}
for path in prior_plan_paths:
 plan=read(path);group_id=path.parents[1].name.split('_')[3].upper();target=group_rows[group_id]['target'];center=plan['group_center_bary_air_angstrom'];overlap=[max(CB-3,center-3),min(CB+3,center+3)];has_overlap=overlap[0]<overlap[1];shared=sorted(current_dp_ids & set(plan['merged_dp_ids']))
 ck('prior_dependency',plan['grid']['window_angstrom']==[-3,3] and set(plan['events'])==set(group_rows[group_id]['member_ids'].split('|')) and plan.get('target',target)==target,group_id+' exact original target/membership/window')
 ck('prior_dependency',(group_id in ['C018','C019'] and target=='HD114783' and set(shared)==current_dp_ids and not has_overlap) or (target!='HD114783' and not shared),group_id+' same-cohort/disjoint blue context or separate other-target products')
 prior_windows.append({'group':group_id,'target':target,'center_bary_air_A':center,'window_bary_air_A':[center-3,center+3],'numeric_overlap_bary_air_A':overlap if has_overlap else None,'shared_merged_dp_ids':shared})
ck('prior_dependency',{r['group'] for r in prior_windows if r['numeric_overlap_bary_air_A']}=={'C006','C007'},'only C006/C007 have other-target numerical overlaps')
c016_window=next(r['window_bary_air_A'] for r in prior_windows if r['group']=='C016');c016_gap=(CB-3)-c016_window[1]
ck('prior_dependency',c016_gap>0 and abs(c016_gap-0.03874999999970896)<1e-12,'nearby HD114386 C016 window remains disjoint by the exact metadata gap')
prior_inventory_path=REPO/'work_harps_20261103_c018_context/inputs/INPUT_INVENTORY.json';prior_inventory=read(prior_inventory_path);prior_c019_plan=read(prior_plan_paths[-1])
ck('target_cohort',{(r['dp_id'],r['file']['sha256']) for r in prior_inventory['merged_spectra']}=={(r['dp_id'],r['file']['sha256']) for r in inv['merged_spectra']} and all(next(x for x in prior_inventory['native_products'] if x['dp_id']==r['dp_id'])['file']['sha256']==r['file']['sha256'] for r in inv['native_products']),'exact seven merged and five native products match C018 source custody')
references=set(expected_products.values());old_references=set(prior_c019_plan['discovery_dp_ids'])
ck('target_cohort',references-old_references=={'ADP.2023-07-02T01:01:43.311'} and old_references-references=={'ADP.2023-05-16T01:01:18.574'},'C021 July1 reference replaces C019 May15 reference while exact counts stay equal')
diff=subprocess.run(['git','diff','--name-only',baseline['baseline_commit'],'--',str(OLD.relative_to(REPO)),*[str(p.relative_to(REPO)) for p in prior_plan_paths],'work_harps_20261103_c019_context'],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines()
ck('immutability',not diff,'old extension02, sixteen plans and entire tracked C019 phase unchanged')
handoff_path=REPO/'work_harps_20261103_c019_context/NEXT_ACTION.json';handoff=read(handoff_path);metadata_path=REPO/'work_harps_20261103_c019_context/scientific_review/NEXT_GROUP_METADATA.json';metadata=read(metadata_path)
ck('prior_dependency',handoff['events']==list(event_centers) and handoff['catalog_center_bary_air_angstrom']==list(event_centers.values()) and handoff['proposed_group_center_bary_air_angstrom']==CB and handoff['discovery_anchor_dp_id']=='ADP.2022-01-22T01:09:14.958' and handoff['discovery_anchor_berv_km_s']==ANCHOR and handoff['proposed_topocentric_anchor_air_angstrom']==CT and handoff['target']=='HD114783' and handoff['existing_cohort_epoch_count']==7 and abs(handoff['berv_span_km_s']-59.073251754930496)<1e-12,'C019 handoff exact five centers/common anchor/seven epochs')
ck('prior_dependency',handoff['core_overlap_group']=='C021' and handoff['resolution_groups']==['R022'] and handoff['queue_rows']==queue_rows and handoff['distinct_discovery_product_count']==5 and set(handoff['distinct_discovery_products'])==references<current_dp_ids,'five exact C021 references are a proper subset of seven epochs')
nonreference_epochs=current_dp_ids-references
ck('target_cohort',nonreference_epochs=={'ADP.2023-03-23T01:02:04.833','ADP.2023-05-16T01:01:18.574'},'March22 and May15 remain non-reference observing epochs')
ck('review_custody',history['per_event_history']==handoff['historical_review_disagreement']['per_event_history'],'exact five per-event original/later histories including distinct 0130 stages')
dependency=handoff['wavelength_dependency']
ck('prior_dependency',dependency['proposed_group_core_bary_air_angstrom']==[CB-.25,CB+.25] and dependency['proposed_group_window_bary_air_angstrom']==[CB-3,CB+3] and dependency['overlaps_current_C019_bounded_window'] is False and dependency['overlaps_completed_C018_bounded_window'] is False and dependency['same_observing_products_as_C019'] is True and dependency['shared_bounded_spectral_source_pixels_with_C019'] is False and abs(dependency['nearby_other_target_C016_gap_angstrom']-c016_gap)<1e-12,'same observations/disjoint bounded windows and exact C016 gap, without full-crop independence claim')
for r in dependency['numeric_wavelength_overlaps_on_other_target']:
 row=next(x for x in prior_windows if x['group']==r['prior_group'])
 ck('prior_dependency',row['target']==r['prior_target'] and row['window_bary_air_A']==r['prior_window_bary_air_angstrom'] and row['numeric_overlap_bary_air_A']==r['numeric_wavelength_overlap_bary_air_angstrom'] and not row['shared_merged_dp_ids'] and r['same_observing_products'] is r['shared_source_pixels'] is False,'handoff exact other-target numerical overlap '+r['prior_group'])
ck('target_cohort',{(r['dp_id'],r['date_obs'],r['mjd_obs'],r['berv_km_s']) for r in handoff['existing_cohort_epochs']}=={(r['dp_id'],r['date_obs'],r['mjd_obs'],r['berv_km_s']) for r in inv['merged_spectra']},'seven exact epoch identities/dates/BERVs match handoff')
for r in handoff['historical_mapping_stages']:
 record=next(x for x in inv['mapping_records'] if x['event']==r['candidate_id'] and x['order']==r['order']);original_ok=r['candidate_id'] not in failed_original_events
 ck('prior_dependency',r['candidate_id'] in expected_events and r['dp_id']==expected_products[r['candidate_id']] and r['order']==19 and tuple(r[k] for k in ['global_grid_usable','original_local_usable','original_baseline_verified','later_five_window_supported'])==(True,original_ok,original_ok,True) and all(record[k]==r[k2] for k,k2 in [('original_grid_mapping_usable','global_grid_usable'),('original_local_mapping_usable','original_local_usable'),('original_baseline_mapping_verified','original_baseline_verified'),('final_reference_mapping_supported','later_five_window_supported'),('original_mapping_source','original_mapping_source'),('native_pixel','native_pixel'),('raw_row','raw_row'),('raw_column','raw_column')]) and record.get('later_mapping_source',record['original_mapping_source'])==r['later_mapping_source'] and record['registration_changed'] is r['registration_changed'] is False,r['candidate_id']+' exact original/later mapping stages/sources/coordinates')
epoch_path=OLD/'epoch_followup/ALL_EPOCH_MEASUREMENTS.csv';epoch_records=list(csv.DictReader(epoch_path.open()))
for event in sorted(expected_events):
 rows=[r for r in epoch_records if r['candidate_id']==event]
 ck('existing_evidence_dependency',len(rows)==14 and {r['dp_id'] for r in rows}==current_dp_ids and all(r['target']=='HD114783' for r in rows) and {(r['dp_id'],r['frame']) for r in rows}=={(dp,frame) for dp in current_dp_ids for frame in ['barycentric','topocentric']},event+' original seven-epoch/two-frame evidence already exists')
summary={'schema':'HARPS_C021_INPUT_AUDIT_V1','status':'PASS' if not failures else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_sha256':sha(INV),'restore_script_sha256':sha(I/'restore_inputs.py'),'audit_script_sha256':sha(Path(__file__)),'baseline_commit':baseline['baseline_commit'],'check_count':sum(counts.values()),'checks_by_scope':counts,'failures':failures,'target':'HD114783','input_counts':{'merged':7,'native_A':5,'ancillary':5,'saved_original_cutouts':5,'archives':5},'anchor':{'dp_id':'ADP.2022-01-22T01:09:14.958','berv_km_s':ANCHOR,'barycentric_common_midpoint_center_A':CB,'topocentric_common_center_A':CT,'policy':'First original-queue discovery fixes common coordinates; all five discoveries remain separate references across seven observations.'},'exact_individual_event_centers_bary_air_A':event_centers,'exact_individual_original_cores_bary_air_A':{e:[center-.25,center+.25] for e,center in event_centers.items()},'distinct_discovery_products':expected_products,'nonreference_observing_epochs':sorted(nonreference_epochs),'common_context_geometry':{'barycentric_window_air_A':[CB-3,CB+3],'barycentric_core_air_A':[CB-.25,CB+.25],'topocentric_window_air_A':[CT-3,CT+3],'topocentric_core_air_A':[CT-.25,CT+.25],'coverage_count_core_policy':'Fixed common metric core; exact original member cores/markers remain distinct.'},'merged_headers':merged_summary,'raw_identifier_timestamp_offsets':timestamp_offsets,'native_coverage':coverage,'mapping_gate_history':mapping_history,'excluded_native_orders':exclusions,'limits':['Fresh coordinate support comes only from header polynomials. Finite samples, actual gaps, reference quality and usable normalization remain unassessed.','Exact catalog-extrema midpoint/common core and January anchor remain separate from five original centers/cores/markers. No post-value expansion or fitted linewidth is introduced.','All original global and later-five-window stages are true. Original local/baseline are false for 0116/0126/0130 and true for 0121/0139; later support does not rewrite failed original stages.','Four batch03 originals retain U/U/U. Older 0130 retains original primary I, secondary M normalized I and baseline I, followed by later U/U/current U; no C019/0129 null-stage or original-U history is transferred.','Original 0130 baseline panel is restored exactly and separately from the later wider container. This audit checks byte custody, unchanged coordinate metadata and recorded prior preservation declarations without decoding pixel values or rerunning reconstruction.','Native BUNIT is absent; native flux remains instrumental without asserted calibrated ADU equivalence to merged flux. Air convention remains inherited from the extractor without a new solution.','ERR is declared unavailable; no positive uncertainty support is inferred.','Seven observations and five native products are reused; bounded windows disjoint from C018/C019 do not supply independent observations or prove independence of full historical crops. Original C021 epoch/raw and completed 0130 mapping evidence already existed.'],'source_hashes':inv['source_hashes'],'network_requests':0,'new_flux_or_pixel_values_interpreted':0,'raw_images_restored_or_read':False}
summary['historical_review_custody']={'batch03_original_U_U_U_members':sorted(batch_events),'0130_original_primary':'I','0130_original_secondary':'M','0130_original_secondary_normalized':'I','0130_original_adopted_baseline':'I','0130_later_primary':'U','0130_later_secondary':'U','0130_current_adopted':'U','0130_original_baseline_panel':[r for r in original_manifest['members'] if 'V2E2-0130_o' in r['path']],'0130_later_distinct_container':later_container_records,'prior_pixel_preservation_declarations_are_not_a_new_pixel_test':True,'no_classification_performed_by_input_audit':True}
summary['prior_wavelength_dependency']={'C021_window_bary_air_A':[CB-3,CB+3],'completed_windows':prior_windows,'same_target_prior_groups':['C018','C019'],'same_seven_observations':True,'disjoint_newly_bounded_spectral_windows':True,'independence_of_full_historical_raw_crops_asserted':False,'other_target_numeric_overlap_groups':['C006','C007'],'nearby_other_target_C016_gap_A':c016_gap,'interpretation':'Same observations/native products at a different bounded spectral window. C006/C007 numerical overlap is another target with separate products/pixels; C016 is disjoint. Original C021 epoch/raw and 0130 wider mapping evidence already existed, without blind, untouched or added-observing-time claims.'}
summary['reference_pair_dependence']={'observations':7,'references':5,'other_epochs_per_reference':6,'directed_nonself_pairs_per_frame_region':30,'unordered_observation_pairs':20,'reciprocal_duplicate_directed_records':10,'interpretation':'Metadata combinatorics of seven reused observations, not independent samples or new numerical comparisons. July1 replaces May15 as a reference relative to C019.'}
additional_paths=[group_path,event_path,original_event_path,handoff_path,metadata_path,current_path,queue_path,epoch_path,prior_inventory_path,original/'NATIVE_MAPPING.json',original/'RAW_BASELINE_EVIDENCE_MANIFEST.json',original_archive,original/'PRIMARY_VISUAL_REVIEW.json',original/'audit/INDEPENDENT_VISUAL_NOTES.json',original/'REVIEW_AGREEMENT.json',original/'BASELINE_SELECTED_EVENT_DISPOSITIONS.csv',original/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',later/'MAPPING_AUDIT.json',later/'FIRST_VISUAL_NOTES.json',later/'SECOND_VISUAL_NOTES.json',later/'FOLLOWUP_DISPOSITIONS.csv',later/'FINAL_REVIEW_SUMMARY.json',later/'VERIFICATION.json',later/'EVIDENCE_ARCHIVE.json',later_archive,*prior_plan_paths]
summary['additional_source_hashes']={str(p.relative_to(REPO)):sha(p) for p in additional_paths}
summary['all_order_header_geometry_count']=len(all_order_geometry)
summary['support_assessment_scope']={'coordinate_support':'Header-polynomial geometry only','finite_sample_support_assessed':False,'reference_quality_assessed':False,'no_usable_normalization_or_finite_flux_inferred':True}
summary['unique_native_coverage']=[dict({k:v for k,v in row.items() if k!='event'},discovery_for=next(p['discovery_for'] for p in inv['native_products'] if p['dp_id']==row['dp_id'])) for row in coverage]
summary['deduplication']='Five discoveries supply five product/order19 contexts and five original raw panels, or ten frame contexts. Five references compare with six other epochs each; only seven observations exist, including two non-reference epochs.'
(HERE/'INPUT_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':summary['status'],'check_count':summary['check_count'],'failures':failures}));assert not failures
