"""C019 identity/coverage audit: opaque hashes and FITS/NPY headers, no flux values."""
import argparse,ast,csv,datetime,hashlib,io,json,math,re,struct,subprocess,tarfile,zipfile
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent;I=PHASE/'inputs';OLD=REPO/'work_harps_20261101/v2/extension02'
INV=I/'INPUT_INVENTORY.json';C=299792.458;CB=3881.6137500000004;ANCHOR=29.658729150824;CT=CB/(1+ANCHOR/C)
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
inv=read(INV);expected_inventory='ceff0bd21ef4dac8a27003450ed3c64b912190c040981c2c03c665a6c160b9ab';ck('inventory',sha(INV)==expected_inventory,'final inventory binding')
ck('inventory',sha(I/'restore_inputs.py')=='269611623f40193eebf7d3406c59ad5c0bddb014d6ae9faed56a1a0f582ae831','final restore helper binding')
ck('anchor',inv['coordinate_anchor']=={'discovery_dp_id':'ADP.2022-01-22T01:09:14.958','anchor_selection_rule':'First member in original ACTION_QUEUE fixes one common group topocentric anchor; all five discovery products remain separate references.','original_member_centers_barycentric_air_angstrom':{'V2E2-0115':3881.6125,'V2E2-0120':3881.615,'V2E2-0125':3881.6150000000002,'V2E2-0129':3881.615,'V2E2-0135':3881.6125},'group_center_rule':'Midpoint of exact minimum/maximum member catalog centers; exact individual cores remain distinct, without post-value expansion.','discovery_berv_km_s':ANCHOR,'center_barycentric_air_angstrom':CB,'fixed_topocentric_air_angstrom':CT,'formula':'center_barycentric_air_angstrom/(1+discovery_berv_km_s/299792.458)'},'first-queue January common anchor and separate exact five member centers')
group_path=OLD/'unresolved_context_20261102/CORE_OVERLAP_GROUPS.csv';group=next(r for r in csv.DictReader(group_path.open()) if r['group_id']=='C019')
event_path=OLD/'raw_followup_batch03/SELECTED_EVENTS.csv';original_event_path=OLD/'raw_followup/SELECTED_EVENTS.csv';source_events={r['review_id']:r for p in [original_event_path,event_path] for r in csv.DictReader(p.open())}
event_centers={'V2E2-0115':3881.6125,'V2E2-0120':3881.615,'V2E2-0125':3881.6150000000002,'V2E2-0129':3881.615,'V2E2-0135':3881.6125};expected_events=set(event_centers);expected_products={'V2E2-0115':'ADP.2022-01-22T01:09:14.958','V2E2-0120':'ADP.2022-02-06T01:07:28.382','V2E2-0125':'ADP.2022-05-06T01:04:00.123','V2E2-0129':'ADP.2023-01-17T01:07:48.581','V2E2-0135':'ADP.2023-05-16T01:01:18.574'}
ck('scope',set(group['member_ids'].split('|'))==set(inv['events'])=={e for r in inv['native_products'] for e in r['discovery_for']}==expected_events and len(inv['native_products'])==5,'exact archived C019 membership')
ck('inventory',len(inv['files'])==27 and len({r['path'] for r in inv['files']})==27,'27 unique restored paths')
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
ck('scope',{e:float(source_events[e]['fitted_center_bary_air_angstrom']) for e in expected_events}==event_centers and {e:source_events[e]['dp_id'] for e in expected_events}==expected_products and (min(event_centers.values())+max(event_centers.values()))/2==CB,'exact individual centers, five discovery identities and fixed metadata midpoint')
ck('anchor',merged_headers['ADP.2022-01-22T01:09:14.958']['ESO DRS BERV']==ANCHOR,'first-queue January discovery anchor exact')
old_maps={'batch03':read(OLD/'raw_followup_batch03/NATIVE_MAPPING.json'),'original':read(OLD/'raw_followup/NATIVE_MAPPING.json')};later_mapping=read(OLD/'raw_followup/mapping_followup/MAPPING_AUDIT.json');coverage=[];mapping_history=[];exclusions=[]
archive_names={};native_headers={}
for name,ap in archivepaths.items():
 with zipfile.ZipFile(ap) as z:archive_names[name]=set(z.namelist())
for r in [dict(p,event=e,original_topocentric_feature_center_air_angstrom=p['original_event_centers_topocentric_air_angstrom'][e]) for p in inv['native_products'] for e in p['discovery_for']]:
 old=old_maps['original' if r['event']=='V2E2-0129' else 'batch03']
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
   baseline_verified=oldrow.get('baseline_mapping_verified',oldrow.get('mapping_verified'));final=oldrow.get('five_window_mapping_supported');record=next(x for x in inv['mapping_records'] if x['event']==r['event'] and x['order']==order)
   ck('mapping',record['original_local_mapping_usable']==oldrow['local_mapping_usable'] and record['original_grid_mapping_usable']==oldrow['grid_mapping_usable'] and record['original_baseline_mapping_verified']==baseline_verified and record['final_reference_mapping_supported']==final and record['registration_changed'] is False,r['event']+str(order)+' gate history')
   ck('mapping',record['dp_id']==r['dp_id'] and record['native_pixel']==k and record['raw_row']==row and record['raw_column']==oldrow['raw_column'],r['event']+str(order)+' exact prior raw coordinate identity')
   mapping_history.append({'event':r['event'],'order':order,'old_global':oldrow['grid_mapping_usable'],'old_local':oldrow['local_mapping_usable'],'old_baseline_verified':baseline_verified,'final_reference_supported':final,'native_pixel':k,'raw_row':row,'raw_column':oldrow['raw_column'],'original_mapping_source':'raw_followup/NATIVE_MAPPING.json' if r['event']=='V2E2-0129' else 'raw_followup_batch03/NATIVE_MAPPING.json'})
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
  ck('all_order_geometry',covered==scan['original_events_covered'] and bool(covered)==scan['covers_any_original_event_center']==scan['selected_for_profile']==(order in [3,4]),product['dp_id']+str(order)+' only orders 3/4 cover each original event')
  ck('all_order_common_geometry',scan['covers_common_fixed_barycentric_center']==(lo<=CB/(1+mh['ESO DRS BERV']/C)<=hi) and scan['covers_common_fixed_topocentric_anchor']==(lo<=CT<=hi),product['dp_id']+str(order)+' separate common B/T center coverage')
  all_order_geometry.append({'dp_id':product['dp_id'],'order':order,'events_covered':covered,'positive_derivative':mono})
ck('scope',len(inv['all_order_header_scan'])==360 and len(all_order_geometry)==360,'all unique order headers accounted')
ck('deduplication',inv['unique_native_order_pairs']==[{'dp_id':r['dp_id'],'order':order} for r in inv['native_products'] for order in [3,4]] and len({r['dp_id'] for r in inv['native_products']})==5,'ten distinct product/order pairs from five discovery references')
for event in sorted(expected_events):
 for order in [3,4]:
  records=[r for r in mapping_history if r['event']==event and r['order']==order];expected=(True,True,True,None if event=='V2E2-0129' else True)
  ck('mapping_history',len(records)==1 and tuple(records[0][k] for k in ['old_global','old_local','old_baseline_verified','final_reference_supported'])==expected,event+' order '+str(order)+' original true gates and distinct later assessment')
for r in inv['mapping_records']:
 is_original=r['event']=='V2E2-0129';source=OLD/('raw_followup/NATIVE_MAPPING.json' if is_original else 'raw_followup_batch03/NATIVE_MAPPING.json');basis='mapping_verified in original raw_followup mapping' if is_original else 'explicit baseline_mapping_verified in batch03 mapping'
 before=next(x for x in old_maps['original' if is_original else 'batch03']['orders'] if x['review_id']==r['event'] and x['order']==r['order']);present='five_window_mapping_supported' in before;assessment='UNASSESSED_FIELD_ABSENT_NOT_SELECTED_FOR_FOLLOWUP' if is_original else 'EXPLICITLY_SUPPORTED'
 ck('mapping_source_identity',r['original_mapping_source']==str(source.relative_to(REPO)) and r['baseline_field_basis']==basis and r['later_five_window_field_present'] is present and r['later_five_window_assessment']==assessment and (not is_original or r['later_mapping_selection_checked_at']==str((OLD/'raw_followup/mapping_followup/MAPPING_AUDIT.json').relative_to(REPO))),r['event']+' order '+str(r['order'])+' exact original source, baseline field and later assessment')
for r in inv['native_order_coverage']:
 old=old_maps['original' if r['event']=='V2E2-0129' else 'batch03'];oldrow=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order'])
 ck('line_coverage',r['dp_id']==oldrow['dp_id']==expected_products[r['event']] and r['order'] in [3,4] and r['selected_for_profile'] and r['saved_raw_panel_exists'] and abs(r['original_topocentric_feature_center_air_angstrom']-oldrow['topocentric_air_angstrom'])<1e-10,r['event']+' inventory coverage links exact original record')
# Opaque original evidence archive/member hashes; only NPY shape/dtype headers are decoded.
batch=OLD/'raw_followup_batch03';batch_meta=read(batch/'EVIDENCE_ARCHIVE.json');batch_parts=read(batch/'EVIDENCE_PARTS.json');batch_bytes=b''
for part in batch_parts['parts']:
 b=(batch/part['path']).read_bytes();ck('evidence_archive',len(b)==part['bytes'] and digest(b)==part['sha256'],part['path']);batch_bytes+=b
ck('evidence_archive',len(batch_bytes)==batch_meta['bytes'] and digest(batch_bytes)==batch_meta['sha256'],'batch03 complete original evidence archive')
original=OLD/'raw_followup';original_manifest=read(original/'RAW_BASELINE_EVIDENCE_MANIFEST.json');original_archive=original/original_manifest['archive'];original_bytes=original_archive.read_bytes()
ck('evidence_archive',len(original_bytes)==original_manifest['archive_bytes'] and digest(original_bytes)==original_manifest['archive_sha256'],'0128 exact original baseline evidence archive')
original_members={r['path']:r for r in original_manifest['members']}
for r in inv['saved_native_raw_cutouts']:
 is_original=r['event']=='V2E2-0129';old=old_maps['original' if is_original else 'batch03'];oldpanel=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order']);expected_sha=original_members[oldpanel['cutout']]['sha256'] if is_original else oldpanel['cutout_sha256'];expected_bytes=original_members[oldpanel['cutout']]['bytes'] if is_original else r['file']['bytes']
 ck('raw_source_identity',r['archive_member']==oldpanel['cutout'] and r['file']['sha256']==expected_sha and r['file']['bytes']==expected_bytes and oldpanel['dp_id']==expected_products[r['event']],r['event']+' exact original order '+str(r['order'])+' panel custody')
 with zipfile.ZipFile(io.BytesIO(original_bytes if is_original else batch_bytes)) as z:ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256'],r['event']+str(r['order'])+' original panel member')
 shape=[]
 with zipfile.ZipFile(REPO/r['file']['path']) as z:
  for name in z.namelist():
   with z.open(name) as f:
    assert f.read(6)==b'\x93NUMPY';v=tuple(f.read(2));n=struct.unpack('<H' if v==(1,0) else '<I',f.read(2 if v==(1,0) else 4))[0];assert n<65536;h=ast.literal_eval(f.read(n).decode('latin1'));shape.append({'key':name[:-4],'shape':list(h['shape']),'dtype':h['descr'],'fortran_order':h['fortran_order']})
 ck('NPY_headers',shape==r['npy_headers'],r['event']+str(r['order'])+' metadata only')
ck('scope',len(coverage)==20 and len(mapping_history)==10 and not exclusions and not inv['excluded_native_orders'] and len(inv['saved_native_raw_cutouts'])==10,'ten original panels and twenty fixed-frame contexts')
ck('scope',len(inv['archives'])==4 and len(inv['source_hashes'])==27 and len(inv['mapping_records'])==len(inv['native_order_coverage'])==10 and {(r['event'],r['order']) for r in inv['saved_native_raw_cutouts']}=={(e,o) for e in expected_events for o in [3,4]},'exact archive/source/mapping/panel scope')
batch_events=expected_events-{'V2E2-0129'};batch_reviews={'adopted':[r for r in csv.DictReader((batch/'ADOPTED_DISPOSITIONS.csv').open()) if r['review_id'] in batch_events]}
for label,name in [('primary','PRIMARY_VISUAL_REVIEW.json'),('secondary','SECONDARY_VISUAL_REVIEW.json'),('comparison','REVIEW_COMPARISON.json')]:
 batch_reviews[label]=[r for r in read(batch/name)['events'] if r['review_id'] in batch_events]
for label,rows in batch_reviews.items():ck('review_custody',len(rows)==4 and {r['review_id'] for r in rows}==batch_events,label+' four original batch03 records')
for event in sorted(batch_events):
 primary=next(r for r in batch_reviews['primary'] if r['review_id']==event);secondary=next(r for r in batch_reviews['secondary'] if r['review_id']==event);adopted=next(r for r in batch_reviews['adopted'] if r['review_id']==event);comparison=next(r for r in batch_reviews['comparison'] if r['review_id']==event)
 ck('review_chain',primary['code']==secondary['code']==adopted['code']==adopted['primary_code']==adopted['secondary_code']==comparison['primary']==comparison['secondary']==comparison['adopted']=='U',event+' original primary/secondary/adopted U/U/U')
 ck('review_chain',primary['covering_orders']==secondary['covering_orders']==[3,4] and secondary['baseline_all_orders_mapping_verified'] is True and adopted['final_physical_origin_confirmed']=='False',event+' original true mapping and unconfirmed origin retained')
original_primary=next(r for r in read(original/'PRIMARY_VISUAL_REVIEW.json')['rows'] if r['review_id']=='V2E2-0129');original_secondary=read(original/'audit/INDEPENDENT_VISUAL_NOTES.json')['notes']['V2E2-0129'];agreement=next(r for r in read(original/'REVIEW_AGREEMENT.json')['rows'] if r['review_id']=='V2E2-0129');baseline_row=next(r for r in csv.DictReader((original/'BASELINE_SELECTED_EVENT_DISPOSITIONS.csv').open()) if r['review_id']=='V2E2-0129');original_current=next(r for r in csv.DictReader((original/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv').open()) if r['review_id']=='V2E2-0129')
ck('review_0129_original',original_primary['primary_code']==original_secondary[0]==agreement['primary_code']==agreement['second_code_original']==agreement['second_code_normalized']==baseline_row['baseline_code']=='U' and original_primary['all_covering_orders_mapping_verified'] is True and original_primary['final_physical_origin_confirmed'] is False and baseline_row['final_physical_origin_confirmed']=='False','0129 original U/U/U, true mapping and unresolved origin, without 0128 history transfer')
later_selection_path=original/'mapping_followup/SELECTED_EVENTS.csv';later_selection=list(csv.DictReader(later_selection_path.open()))
ck('mapping_0129_unassessed',not any(r['review_id']=='V2E2-0129' for r in later_selection+later_mapping['orders']+later_mapping['events']),'0129 is absent from the separate completed mapping followup selection/orders/events')
for order in [3,4]:
 before=next(r for r in old_maps['original']['orders'] if r['review_id']=='V2E2-0129' and r['order']==order);record=next(r for r in inv['mapping_records'] if r['event']=='V2E2-0129' and r['order']==order)
 ck('mapping_0129_unassessed','five_window_mapping_supported' not in before and before['mapping_verified'] is True and record['final_reference_mapping_supported'] is None,'0129 order '+str(order)+' absent later field stays null/unassessed, distinct from original true baseline')
history=inv['historical_raw_review_records']
for label,rows in batch_reviews.items():ck('review_custody',rows==history['batch03_original'][label],label+' exact original batch03 inventory records')
later_dispositions_path=original/'mapping_followup/FOLLOWUP_DISPOSITIONS.csv';later_dispositions=[r for r in csv.DictReader(later_dispositions_path.open()) if r['review_id']=='V2E2-0129']
expected_0129={'original_primary':original_primary,'original_secondary_source_record':original_secondary,'original_review_agreement':agreement,'original_adopted_baseline':baseline_row,'current_adopted_record':original_current,'later_mapping_records':[r for r in later_mapping['orders'] if r['review_id']=='V2E2-0129'],'later_disposition_records':later_dispositions,'later_mapping_followup_selected':False,'later_five_window_field_present':False,'later_five_window_supported':None,'later_five_window_assessment':'UNASSESSED_FIELD_ABSENT_NOT_SELECTED_FOR_FOLLOWUP','original_baseline_containers_restored':True,'later_wider_container_substituted':False}
ck('review_custody',history['separate_raw_followup_0129']==expected_0129 and not later_dispositions,'exact 0129 original U history/current record with absent unassessed later stage')

current_path=REPO/'work_harps_20261101/v2/CURRENT_V2_DISPOSITIONS.csv';queue_path=OLD/'unresolved_context_20261102/ACTION_QUEUE.csv'
current_rows=[r for r in csv.DictReader(current_path.open()) if r['review_id'] in expected_events];queue_rows=[r for r in csv.DictReader(queue_path.open()) if r['candidate_id'] in expected_events];expected_queue={'V2E2-0115':'34','V2E2-0120':'39','V2E2-0125':'43','V2E2-0129':'47','V2E2-0135':'52'}
ck('current_disposition',len(current_rows)==5 and {r['review_id'] for r in current_rows}==expected_events and all(r['current_code']=='U' and r['final_physical_origin_confirmed']=='False' and float(r['fitted_center_bary_air_angstrom'])==event_centers[r['review_id']] and r['dp_id']==expected_products[r['review_id']] for r in current_rows),'five exact current U labels/individual centers/discovery identities')
ck('review_custody',history['current_adopted']==current_rows,'exact five root-current records retained')
ck('original_queue',len(queue_rows)==5 and {r['candidate_id']:r['queue_index'] for r in queue_rows}==expected_queue and all(r['current_code_unchanged']=='U' and r['core_overlap_group']=='C019' and r['resolution_group']=='R020' and r['primary_evidence_route']=='JOINT_PROFILE_CONTEXT' for r in queue_rows),'full original C019 joint queue group/R020 preserved')
baseline=read(PHASE/'BASELINE_VERIFICATION.json')
ck('immutability',baseline['baseline_commit']=='103b6c4f471d1e473315b7d86579047516e26f91' and baseline['previous_state_sha256']=='47db3c1322addab03740e98d6fb21babefe31504ab9efe2d50af07a35d98fdf2' and baseline['previous_source_hashes_verified_exact_local_and_public']==2487 and baseline['tracked_and_index_diffs_empty'] is True and baseline['new_observed_arrays_read'] is False,'exact GREEN C018 baseline and prior-state custody')
prior_plan_paths=[REPO/('work_harps_20261102_'+g+'_context/analysis/PLAN.json') for g in ['c001','c003','c005','c006','c007','c004','c002','c008']]+[REPO/('work_harps_20261103_'+g+'_context/analysis/PLAN.json') for g in ['c009','c010','c012','c011','c016','c015','c018']]
prior_windows=[];group_rows={r['group_id']:r for r in csv.DictReader(group_path.open())};current_dp_ids={r['dp_id'] for r in inv['merged_spectra']}
for path in prior_plan_paths:
 plan=read(path);group_id=path.parents[1].name.split('_')[3].upper();target=group_rows[group_id]['target'];center=plan['group_center_bary_air_angstrom'];overlap=[max(CB-3,center-3),min(CB+3,center+3)];has_overlap=overlap[0]<overlap[1];shared=sorted(current_dp_ids & set(plan['merged_dp_ids']))
 ck('prior_dependency',plan['grid']['window_angstrom']==[-3,3] and set(plan['events'])==set(group_rows[group_id]['member_ids'].split('|')) and plan.get('target',target)==target,group_id+' exact original target/membership/window')
 ck('prior_dependency',(group_id=='C018' and target=='HD114783' and set(shared)==current_dp_ids and not has_overlap) or (target!='HD114783' and not shared),group_id+' same-cohort/disjoint C018 window or separate other-target products')
 prior_windows.append({'group':group_id,'target':target,'center_bary_air_A':center,'window_bary_air_A':[center-3,center+3],'numeric_overlap_bary_air_A':overlap if has_overlap else None,'shared_merged_dp_ids':shared})
ck('prior_dependency',[r['group'] for r in prior_windows if r['numeric_overlap_bary_air_A']]==['C005'],'only C005 has other-target numerical overlap')
prior_inventory_path=REPO/'work_harps_20261103_c018_context/inputs/INPUT_INVENTORY.json';prior_inventory=read(prior_inventory_path)
ck('target_cohort',{(r['dp_id'],r['file']['sha256']) for r in prior_inventory['merged_spectra']}=={(r['dp_id'],r['file']['sha256']) for r in inv['merged_spectra']} and all(next(x for x in prior_inventory['native_products'] if x['dp_id']==r['dp_id'])['file']['sha256']==r['file']['sha256'] for r in inv['native_products']),'exact seven merged products and five reused native products match C018 custody')
diff=subprocess.run(['git','diff','--name-only',baseline['baseline_commit'],'--',str(OLD.relative_to(REPO)),*[str(p.relative_to(REPO)) for p in prior_plan_paths],'work_harps_20261103_c018_context'],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines()
ck('immutability',not diff,'old extension02, fifteen plans and entire tracked C018 phase unchanged')
handoff_path=REPO/'work_harps_20261103_c018_context/NEXT_ACTION.json';handoff=read(handoff_path);metadata_path=REPO/'work_harps_20261103_c018_context/scientific_review/NEXT_GROUP_METADATA.json';metadata=read(metadata_path)
ck('prior_dependency',handoff['events']==list(event_centers) and handoff['catalog_center_bary_air_angstrom']==list(event_centers.values()) and handoff['proposed_group_center_bary_air_angstrom']==CB and handoff['discovery_anchor_dp_id']=='ADP.2022-01-22T01:09:14.958' and handoff['discovery_anchor_berv_km_s']==ANCHOR and handoff['proposed_topocentric_anchor_air_angstrom']==CT and handoff['target']=='HD114783' and handoff['existing_cohort_epoch_count']==7 and abs(handoff['berv_span_km_s']-59.073251754930496)<1e-12,'C018 handoff exact five member centers/common anchor/seven epochs')
ck('prior_dependency',handoff['core_overlap_group']=='C019' and handoff['resolution_groups']==['R020'] and handoff['queue_rows']==queue_rows and handoff['distinct_discovery_product_count']==5 and set(handoff['distinct_discovery_products'])==set(expected_products.values())<current_dp_ids,'five exact references are a proper subset of the seven-epoch cohort')
nonreference_epochs=current_dp_ids-set(expected_products.values())
ck('target_cohort',nonreference_epochs=={'ADP.2023-03-23T01:02:04.833','ADP.2023-07-02T01:01:43.311'},'March22 and July1 epochs remain in cohort without becoming discovery references')
ck('review_custody',history['per_event_history']==handoff['historical_review_disagreement']['per_event_history'],'exact five per-event U/U/U histories with no 0128 transfer')
dependency=handoff['wavelength_dependency']
ck('prior_dependency',dependency['proposed_group_core_bary_air_angstrom']==[CB-.25,CB+.25] and dependency['proposed_group_window_bary_air_angstrom']==[CB-3,CB+3] and dependency['overlaps_current_C018_bounded_window'] is False and dependency['same_observing_products_as_C018'] is True and dependency['shared_bounded_spectral_source_pixels_with_C018'] is False,'same observations with disjoint fixed spectral windows; complete historical raw crops not declared independent')
for r in dependency['numeric_wavelength_overlaps_on_other_target']:
 row=next(x for x in prior_windows if x['group']==r['prior_group'])
 ck('prior_dependency',row['target']==r['prior_target'] and row['window_bary_air_A']==r['prior_window_bary_air_angstrom'] and row['numeric_overlap_bary_air_A']==r['numeric_wavelength_overlap_bary_air_angstrom'] and not row['shared_merged_dp_ids'] and r['same_observing_products'] is r['shared_source_pixels'] is False,'handoff exact C005 other-target numerical overlap')
ck('target_cohort',{(r['dp_id'],r['date_obs'],r['mjd_obs'],r['berv_km_s']) for r in handoff['existing_cohort_epochs']}=={(r['dp_id'],r['date_obs'],r['mjd_obs'],r['berv_km_s']) for r in inv['merged_spectra']},'all seven exact epoch identities/dates/BERVs match handoff')
for r in handoff['historical_mapping_stages']:
 record=next(x for x in inv['mapping_records'] if x['event']==r['candidate_id'] and x['order']==r['order']);legacy=r['candidate_id']=='V2E2-0129';expected=(True,True,True,None if legacy else True)
 ck('prior_dependency',r['candidate_id'] in expected_events and r['dp_id']==expected_products[r['candidate_id']] and tuple(r[k] for k in ['global_grid_usable','original_local_usable','original_baseline_verified','later_five_window_supported'])==expected and record['original_grid_mapping_usable']==r['global_grid_usable'] and record['original_local_mapping_usable']==r['original_local_usable'] and record['original_baseline_mapping_verified']==r['original_baseline_verified'] and record['final_reference_mapping_supported']==r['later_five_window_supported'] and r['later_five_window_field_present'] is (not legacy) and record['registration_changed'] is r['registration_changed'] is False,r['candidate_id']+' order '+str(r['order'])+' exact separate original/later handoff stages')
epoch_path=OLD/'epoch_followup/ALL_EPOCH_MEASUREMENTS.csv';epoch_records=list(csv.DictReader(epoch_path.open()))
for event in sorted(expected_events):
 rows=[r for r in epoch_records if r['candidate_id']==event]
 ck('existing_evidence_dependency',len(rows)==14 and {r['dp_id'] for r in rows}==current_dp_ids and all(r['target']=='HD114783' for r in rows) and {(r['dp_id'],r['frame']) for r in rows}=={(dp,frame) for dp in current_dp_ids for frame in ['barycentric','topocentric']},event+' original seven-epoch/two-frame evidence already exists')
summary={'schema':'HARPS_C019_INPUT_AUDIT_V1','status':'PASS' if not failures else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_sha256':sha(INV),'restore_script_sha256':sha(I/'restore_inputs.py'),'audit_script_sha256':sha(Path(__file__)),'baseline_commit':baseline['baseline_commit'],'check_count':sum(counts.values()),'checks_by_scope':counts,'failures':failures,'target':'HD114783','input_counts':{'merged':7,'native_A':5,'ancillary':5,'saved_original_cutouts':10,'archives':4},'anchor':{'dp_id':'ADP.2022-01-22T01:09:14.958','berv_km_s':ANCHOR,'barycentric_common_midpoint_center_A':CB,'topocentric_common_center_A':CT,'policy':'First original-queue discovery fixes common coordinates; five discoveries remain separate references across seven observations.'},'exact_individual_event_centers_bary_air_A':event_centers,'exact_individual_original_cores_bary_air_A':{e:[center-.25,center+.25] for e,center in event_centers.items()},'distinct_discovery_products':expected_products,'nonreference_observing_epochs':sorted(nonreference_epochs),'common_context_geometry':{'barycentric_window_air_A':[CB-3,CB+3],'barycentric_core_air_A':[CB-.25,CB+.25],'topocentric_window_air_A':[CT-3,CT+3],'topocentric_core_air_A':[CT-.25,CT+.25],'coverage_count_core_policy':'Fixed common metric core; exact original member cores/markers remain distinct.'},'merged_headers':merged_summary,'raw_identifier_timestamp_offsets':timestamp_offsets,'native_coverage':coverage,'mapping_gate_history':mapping_history,'excluded_native_orders':exclusions,'limits':['All coordinate support is derived only from fresh header polynomials. Finite samples, actual gaps, reference quality and usable normalization remain unassessed.','The exact catalog-extrema midpoint/common core and first-queue January anchor remain separate from five exact original member centers/cores and discovery markers. No post-value expansion or fitted linewidth is introduced.','All ten original order3/4 global/local/baseline stages are true. Eight batch03 later-five-window fields explicitly support their contexts. Older 0129 has no such field and is absent from the later followup; its two later entries stay null/unassessed, distinct from original true support.','All five original primary/secondary/adopted and current labels remain U. No C018/0128 I/M/I history, order2 mapping failure or missing-flank result is transferred.','Original 0129 baseline NPZ containers are restored exactly; no later wider container or replayed mapping diagnosis is substituted.','Native BUNIT is absent; flux remains instrumental/native without asserted calibrated ADU equivalence to merged flux. Air-wavelength convention remains inherited from the archived extractor, without a new solution.','ERR is declared unavailable; no positive uncertainty support is inferred.','C019 reuses seven C018 observations and five native products. Newly bounded spectral windows are disjoint, without asserting independence of complete historical raw crops or observations. Original C019 epoch/raw evidence already existed; no new, blind or untouched observing evidence is claimed.'],'source_hashes':inv['source_hashes'],'network_requests':0,'new_flux_or_pixel_values_interpreted':0,'raw_images_restored_or_read':False}
summary['historical_review_custody']={'all_original_primary_secondary_adopted_codes':'U/U/U','current_adopted_codes':'U','0129_original_baseline_code':'U','0129_later_five_window_supported':None,'0129_later_five_window_assessment':'UNASSESSED_FIELD_ABSENT_NOT_SELECTED_FOR_FOLLOWUP','0129_original_baseline_panels':[r for r in original_manifest['members'] if 'V2E2-0129_o' in r['path']],'no_0128_review_stage_history_transferred':True,'no_classification_performed_by_input_audit':True}
summary['prior_wavelength_dependency']={'C019_window_bary_air_A':[CB-3,CB+3],'completed_windows':prior_windows,'same_target_prior_group':'C018','same_observations_as_C018':True,'disjoint_newly_bounded_spectral_windows':True,'independence_of_full_historical_raw_crops_asserted':False,'other_target_numeric_overlap_groups':['C005'],'interpretation':'All seven observations and five native products are reused from C018. Bounded spectral windows differ, but original epoch/raw evidence already existed and observation/full-crop independence is not implied. C005 numeric overlap is another target with disjoint products/pixels.'}
summary['reference_pair_dependence']={'observations':7,'references':5,'other_epochs_per_reference':6,'directed_nonself_pairs_per_frame_region':30,'unordered_observation_pairs':20,'reciprocal_duplicate_directed_records':10,'interpretation':'Metadata combinatorics of seven reused observations, not independent samples or new numerical comparisons.'}
additional_paths=[group_path,event_path,original_event_path,handoff_path,metadata_path,current_path,queue_path,epoch_path,prior_inventory_path,original/'NATIVE_MAPPING.json',original/'RAW_BASELINE_EVIDENCE_MANIFEST.json',original_archive,original/'PRIMARY_VISUAL_REVIEW.json',original/'audit/INDEPENDENT_VISUAL_NOTES.json',original/'REVIEW_AGREEMENT.json',original/'BASELINE_SELECTED_EVENT_DISPOSITIONS.csv',original/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',original/'mapping_followup/MAPPING_AUDIT.json',later_selection_path,later_dispositions_path,*prior_plan_paths]
summary['additional_source_hashes']={str(p.relative_to(REPO)):sha(p) for p in additional_paths}
summary['all_order_header_geometry_count']=len(all_order_geometry)
summary['support_assessment_scope']={'coordinate_support':'Header-polynomial geometry only','finite_sample_support_assessed':False,'reference_quality_assessed':False,'no_usable_normalization_or_finite_flux_inferred':True}
summary['unique_native_coverage']=[dict({k:v for k,v in row.items() if k!='event'},discovery_for=next(p['discovery_for'] for p in inv['native_products'] if p['dp_id']==row['dp_id'])) for row in coverage]
summary['deduplication']='Five discoveries supply ten product/order contexts and ten original raw panels, or twenty frame contexts. Five references compare with six other epochs each; only seven observations exist, including two non-reference epochs.'
(HERE/'INPUT_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':summary['status'],'check_count':summary['check_count'],'failures':failures}));assert not failures
