"""C016 identity/coverage audit: opaque hashes and FITS/NPY headers, no flux values."""
import argparse,ast,csv,datetime,hashlib,io,json,math,re,struct,subprocess,tarfile,zipfile
from pathlib import Path
from astropy.io.fits import Header
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];PHASE=HERE.parent;I=PHASE/'inputs';OLD=REPO/'work_harps_20261101/v2/extension02'
INV=I/'INPUT_INVENTORY.json';C=299792.458;CB=4303.7875;ANCHOR=19.1606928163471;CT=CB/(1+ANCHOR/C)
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
inv=read(INV);expected_inventory='ef8b5ebe21e6ab03f037691c6582a3b70187a77908274c46e08e89e430f99cce';ck('inventory',sha(INV)==expected_inventory,'final inventory binding')
ck('inventory',sha(I/'restore_inputs.py')=='36451bef2b6557dfd81f765f36eeca7878dd525607b9d656ccca2b5fff5fd018','final restore helper binding')
ck('anchor',inv['coordinate_anchor']=={'discovery_dp_id':'ADP.2022-03-08T01:01:37.348','anchor_selection_rule':'First member in the original ACTION_QUEUE fixes one common group topocentric anchor; all four discovery products remain separate references.','original_member_centers_barycentric_air_angstrom':{'V2E2-0094':4303.785,'V2E2-0096':4303.785,'V2E2-0098':4303.785,'V2E2-0110':4303.79},'group_center_rule':'Midpoint of minimum/maximum original member catalog centers; not a fitted peak.','discovery_berv_km_s':ANCHOR,'center_barycentric_air_angstrom':CB,'fixed_topocentric_air_angstrom':CT,'formula':'center_barycentric_air_angstrom/(1+discovery_berv_km_s/299792.458)'},'March 2022 first-queue anchor, common midpoint and separate individual centers')
group_path=OLD/'unresolved_context_20261102/CORE_OVERLAP_GROUPS.csv';group=next(r for r in csv.DictReader(group_path.open()) if r['group_id']=='C016')
event_path=OLD/'raw_followup_batch03/SELECTED_EVENTS.csv';source_events={r['review_id']:r for r in csv.DictReader(event_path.open())}
expected_events={'V2E2-0094','V2E2-0096','V2E2-0098','V2E2-0110'};event_centers={'V2E2-0094':4303.785,'V2E2-0096':4303.785,'V2E2-0098':4303.785,'V2E2-0110':4303.79};expected_products={'V2E2-0094':'ADP.2022-03-08T01:01:37.348','V2E2-0096':'ADP.2022-05-17T01:02:16.724','V2E2-0098':'ADP.2023-01-03T01:08:17.803','V2E2-0110':'ADP.2023-08-29T01:02:07.487'}
ck('scope',set(group['member_ids'].split('|'))==set(inv['events'])=={e for r in inv['native_products'] for e in r['discovery_for']}==expected_events and len(inv['native_products'])==4,'exact archived C016 membership')
ck('inventory',len(inv['files'])==19 and len({r['path'] for r in inv['files']})==19,'19 unique restored paths')
for r in inv['files']:
 p=(REPO/r['path']).resolve();p.relative_to(I);ck('restored_bytes',p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],p.name)
for path,h in inv['source_hashes'].items():ck('historical_sources',sha(REPO/path)==h,path)
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive-dir',type=Path,action='append',default=[]);args=parser.parse_args();archive_dirs=args.archive_dir or [REPO.parent/'c010_archive_cache',REPO.parent/'c016_archive_cache'];archivepaths={}
historical_archives=read(OLD/'checkpoints/INPUT_CHECKPOINTS.json')['parts']+read(OLD/'raw_followup/checkpoints/RAW_INPUT_CHECKPOINTS.json')['parts']+read(OLD/'raw_followup_batch03/checkpoints/INPUT_ARCHIVES.json')['archives']
for r in inv['archives']:
 matches=[x for x in historical_archives if x['filename']==r['filename']];ck('archive',len(matches)==1 and all(matches[0][k]==r[k] for k in ['bytes','sha256']),r['filename']+' historical archive identity')
 candidates=[p for d in archive_dirs for p in d.rglob(r['filename']) if p.is_file()];ck('archive',len(candidates)==1,r['filename']+' one exact local archive');p=candidates[0];ck('archive',p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],r['filename']);archivepaths[r['filename']]=p
science_archive=next(p for n,p in archivepaths.items() if 'EXTENSION02_INPUTS' in n)
checks=read(OLD/'epoch_followup/INPUT_CHECKS.json');previous={r['dp_id']:r for r in checks if r['target']=='HD114386'};ck('merged_identity',set(previous)=={r['dp_id'] for r in inv['merged_spectra']},'exact prior seven epochs')
ck('merged_identity',len({r['raw_id'] for r in inv['merged_spectra']})==7,'seven unique progenitors')
ck('target_cohort',inv['target']=='HD114386' and all(r['target']=='HD114386' for r in previous.values()),'existing target-specific cohort only')
ck('target_cohort',abs(max(r['berv_km_s'] for r in inv['merged_spectra'])-min(r['berv_km_s'] for r in inv['merged_spectra'])-51.572001697156)<1e-12,'own HD114386 BERV span, no old target span transfer')
merged_headers={};merged_summary=[]
with zipfile.ZipFile(science_archive) as z:
 for r in inv['merged_spectra']:
  p=REPO/r['file']['path'];ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256']==previous[r['dp_id']]['sha256'],r['dp_id'])
  hs=headers(p);ck('merged_headers',len(hs)==2 and hs[0]['NAXIS']==0 and hs[1]['XTENSION']=='BINTABLE' and hs[1]['NAXIS2']==1,r['dp_id']+' structure');ph,th=hs
  ck('merged_headers',all(ph.get(k)==v for k,v in r['primary_header'].items()) and all(th.get(k)==v for k,v in r['table_header'].items()),r['dp_id']+' inventory headers')
  prov=[c.value.removesuffix('.fits') for c in ph.cards if re.fullmatch(r'PROV\d+',c.keyword)];ck('merged_identity',prov==[r['raw_id']] and ph['ARCFILE']==r['dp_id']+'.fits' and ph['OBJECT'].replace(' ','')=='HD114386' and ph['INSTRUME']=='HARPS',r['dp_id']+' identity')
  original=download[r['dp_id']];ck('merged_identity',r['raw_id']==original['expected_raw_progenitor_id'] and r['file']['sha256']==original['sha256'],r['dp_id']+' original PROV1 custody')
  delta=(datetime.datetime.fromisoformat(r['raw_id'].removeprefix('HARPS.'))-datetime.datetime.fromisoformat(ph['DATE-OBS'])).total_seconds()*1000
  ck('dates',abs(delta)<=10 and ph['DATE-OBS']==previous[r['dp_id']]['date_obs'] and abs(ph['MJD-OBS']-previous[r['dp_id']]['mjd_obs'])<1e-8,r['dp_id']+' raw identifier vs DATE-OBS')
  timestamp_offsets.append({'dp_id':r['dp_id'],'raw_id':r['raw_id'],'header_DATE_OBS':ph['DATE-OBS'],'raw_identifier_minus_header_milliseconds':delta,'policy':'Exact identifiers preserved; existing millisecond offset recorded, not string-normalized.'})
  ck('merged_units',ph['SPECSYS']=='BARYCENT' and ph['NCOMBINE']==1 and ph['FLUXCAL']=='UNCALIBRATED' and ph['SPEC_RES']==115000 and th['TUNIT1']=='angstrom' and th['TUNIT2']==th['TUNIT3']=='adu' and 'obs.atmos' in th['TUCD1'],r['dp_id'])
  formats=[re.fullmatch(r'([1-9][0-9]*)([DE])',th['TFORM'+str(i)]) for i in [1,2,3]];ck('merged_headers',all(formats) and len({int(m[1]) for m in formats if m})==1 and [th['TTYPE'+str(i)] for i in [1,2,3]]==['WAVE','FLUX','ERR'],r['dp_id']+' vectors')
  ck('merged_headers',math.isfinite(ph['ESO DRS BERV']) and abs(ph['ESO DRS BERV'])<100 and ph['ESO DRS BERV']==r['berv_km_s']==previous[r['dp_id']]['berv_km_s'],r['dp_id']+' BERV')
  ck('merged_headers','not available' in th.get('TCOMM3','').lower(),r['dp_id']+' unavailable ERR explicitly retained')
  merged_headers[r['dp_id']]=ph;merged_summary.append({'dp_id':r['dp_id'],'berv_km_s':ph['ESO DRS BERV'],'date_obs':ph['DATE-OBS'],'wavelength_unit':'air Angstrom','frame':'BARYCENT','flux_unit':'ADU, uncalibrated','ERR':'Declared unavailable/NaN; no sample values read'})
ck('scope',{e:float(source_events[e]['fitted_center_bary_air_angstrom']) for e in expected_events}==event_centers and {e:source_events[e]['dp_id'] for e in expected_events}==expected_products and (min(event_centers.values())+max(event_centers.values()))/2==CB,'exact individual centers, four discovery identities and fixed metadata midpoint')
ck('anchor',merged_headers['ADP.2022-03-08T01:01:37.348']['ESO DRS BERV']==ANCHOR,'first-queue March discovery anchor exact')
old=read(OLD/'raw_followup_batch03/NATIVE_MAPPING.json');coverage=[];mapping_history=[];exclusions=[]
archive_names={};native_headers={}
for name,ap in archivepaths.items():
 with zipfile.ZipFile(ap) as z:archive_names[name]=set(z.namelist())
for r in [dict(p,event=e,original_topocentric_feature_center_air_angstrom=p['original_event_centers_topocentric_air_angstrom'][e]) for p in inv['native_products'] for e in p['discovery_for']]:
 anc=REPO/r['ancillary_file']['path'];native=REPO/r['file']['path'];ap=next(p for n,p in archivepaths.items() if r['ancillary_archive_member'] in archive_names[n])
 with zipfile.ZipFile(ap) as z:ck('archive_members',digest(z.read(r['ancillary_archive_member']))==r['ancillary_file']['sha256'],r['event']+' ancillary')
 with tarfile.open(anc) as z:
  members=[m for m in z if m.name.endswith('_e2ds_A.fits')];ck('native_identity',len(members)==1 and members[0].name==r['native_tar_member'] and members[0].isfile(),r['event']+' unique nativeA');ck('archive_members',digest(z.extractfile(members[0]).read())==r['file']['sha256'],r['event']+' native bytes')
 hs=headers(native);h=hs[0];native_headers[r['dp_id']]=h;mh=merged_headers[r['dp_id']];ck('native_headers',len(hs)==1 and [h['NAXIS2'],h['NAXIS1']]==[72,4096] and h['INSTRUME']=='HARPS' and h['OBJECT'].replace(' ','')=='HD114386' and h['DATE-OBS']==mh['DATE-OBS'] and h['ESO DRS BERV']==mh['ESO DRS BERV'],r['event'])
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
  ck('all_order_geometry',covered==scan['original_events_covered'] and bool(covered)==scan['covers_any_original_event_center']==scan['selected_for_profile']==(order==19),product['dp_id']+str(order)+' only order 19 covers each original event')
  ck('all_order_common_geometry',scan['covers_common_fixed_barycentric_center']==(lo<=CB/(1+mh['ESO DRS BERV']/C)<=hi) and scan['covers_common_fixed_topocentric_anchor']==(lo<=CT<=hi),product['dp_id']+str(order)+' separate common B/T center coverage')
  all_order_geometry.append({'dp_id':product['dp_id'],'order':order,'events_covered':covered,'positive_derivative':mono})
ck('scope',len(inv['all_order_header_scan'])==288 and len(all_order_geometry)==288,'all unique order headers accounted')
ck('deduplication',inv['unique_native_order_pairs']==[{'dp_id':r['dp_id'],'order':19} for r in inv['native_products']] and len({r['dp_id'] for r in inv['native_products']})==4,'exactly four unique product/order pairs from four distinct discoveries')
for event in sorted(expected_events):
 records=[r for r in mapping_history if r['event']==event]
 ck('mapping_history',len(records)==1 and records[0]['order']==19 and all(records[0][k] is True for k in ['old_global','old_local','old_baseline_verified','final_reference_supported']),event+' all four original/later mapping gates true')
for r in inv['native_order_coverage']:
 oldrow=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order'])
 ck('line_coverage',r['dp_id']==oldrow['dp_id']==expected_products[r['event']] and r['order']==19 and r['selected_for_profile'] and r['saved_raw_panel_exists'] and abs(r['original_topocentric_feature_center_air_angstrom']-oldrow['topocentric_air_angstrom'])<1e-10,r['event']+' inventory coverage links exact original record')
# Read old evidence bytes for custody; decode NPY shape headers only.
e2=OLD/'raw_followup_batch03';e2m=read(e2/'EVIDENCE_ARCHIVE.json');parts=read(e2/'EVIDENCE_PARTS.json');data2=b''
for part in parts['parts']:
 b=(e2/part['path']).read_bytes();ck('evidence_archive',len(b)==part['bytes'] and digest(b)==part['sha256'],part['path']);data2+=b
ck('evidence_archive',len(data2)==e2m['bytes'] and digest(data2)==e2m['sha256'],'batch03 assembled evidence')
for r in inv['saved_native_raw_cutouts']:
 oldpanel=next(x for x in old['orders'] if x['review_id']==r['event'] and x['order']==r['order']);ck('raw_source_identity',r['archive_member']==oldpanel['cutout'] and r['file']['sha256']==oldpanel['cutout_sha256'] and oldpanel['dp_id']==expected_products[r['event']],'exact original mapped NPZ source')
 with zipfile.ZipFile(io.BytesIO(data2)) as z:ck('archive_members',digest(z.read(r['archive_member']))==r['file']['sha256'],r['event']+str(r['order'])+' saved cutout')
 shape=[]
 with zipfile.ZipFile(REPO/r['file']['path']) as z:
  for name in z.namelist():
   with z.open(name) as f:
    assert f.read(6)==b'\x93NUMPY';v=tuple(f.read(2));n=struct.unpack('<H' if v==(1,0) else '<I',f.read(2 if v==(1,0) else 4))[0];assert n<65536;h=ast.literal_eval(f.read(n).decode('latin1'));shape.append({'key':name[:-4],'shape':list(h['shape']),'dtype':h['descr'],'fortran_order':h['fortran_order']})
 ck('NPY_headers',shape==r['npy_headers'],r['event']+str(r['order']))
ck('scope',len(coverage)==8 and len(mapping_history)==4 and not exclusions and not inv['excluded_native_orders'] and len(inv['saved_native_raw_cutouts'])==4,'four original covering-order panels, eight fixed-frame contexts and no original-line exclusions')
ck('scope',len(inv['archives'])==3 and len(inv['source_hashes'])==14 and len(inv['mapping_records'])==len(inv['native_order_coverage'])==4 and {(r['event'],r['order']) for r in inv['saved_native_raw_cutouts']}=={(e,19) for e in expected_events},'exact archive/source/mapping/panel scope')
historical_reviews={'adopted':[r for r in csv.DictReader((OLD/'raw_followup_batch03/ADOPTED_DISPOSITIONS.csv').open()) if r['review_id'] in expected_events]}
for label,name in [('primary','PRIMARY_VISUAL_REVIEW.json'),('secondary','SECONDARY_VISUAL_REVIEW.json'),('comparison','REVIEW_COMPARISON.json')]:
 historical_reviews[label]=[r for r in read(OLD/'raw_followup_batch03'/name)['events'] if r['review_id'] in expected_events]
for label,rows in historical_reviews.items():
 ck('review_custody',len(rows)==4 and {r['review_id'] for r in rows}==expected_events and rows==inv['historical_raw_review_records'][label],label+' exact four historical records')
for event in sorted(expected_events):
 primary=next(r for r in historical_reviews['primary'] if r['review_id']==event);secondary=next(r for r in historical_reviews['secondary'] if r['review_id']==event);adopted=next(r for r in historical_reviews['adopted'] if r['review_id']==event);comparison=next(r for r in historical_reviews['comparison'] if r['review_id']==event)
 ck('review_chain',primary['code']==secondary['code']==adopted['code']==adopted['primary_code']==adopted['secondary_code']==comparison['primary']==comparison['secondary']==comparison['adopted']=='U',event+' exact U/U/U historical review chain')
 ck('review_chain',primary['covering_orders']==secondary['covering_orders']==primary['orders_seen']==secondary['orders_seen']==[19] and secondary['baseline_all_orders_mapping_verified'] is True and adopted['final_physical_origin_confirmed']=='False' and 'Separate reviews agree' in comparison['root_note'],event+' original supported coverage remains provisional and origin unconfirmed')
current_path=REPO/'work_harps_20261101/v2/CURRENT_V2_DISPOSITIONS.csv';queue_path=OLD/'unresolved_context_20261102/ACTION_QUEUE.csv'
current_rows=[r for r in csv.DictReader(current_path.open()) if r['review_id'] in expected_events];queue_rows=[r for r in csv.DictReader(queue_path.open()) if r['candidate_id'] in expected_events];expected_queue={'V2E2-0094':'27','V2E2-0096':'29','V2E2-0098':'30','V2E2-0110':'32'}
ck('current_disposition',len(current_rows)==4 and {r['review_id'] for r in current_rows}==expected_events and all(r['current_code']=='U' and r['final_physical_origin_confirmed']=='False' and float(r['fitted_center_bary_air_angstrom'])==event_centers[r['review_id']] and r['dp_id']==expected_products[r['review_id']] for r in current_rows),'all four current U/unconfirmed decisions at exact individual centers')
ck('original_queue',len(queue_rows)==4 and {r['candidate_id']:r['queue_index'] for r in queue_rows}==expected_queue and all(r['current_code_unchanged']=='U' and r['core_overlap_group']=='C016' and r['resolution_group']=='R017' and r['primary_evidence_route']=='JOINT_PROFILE_CONTEXT' for r in queue_rows),'exact original joint queue rows27/29/30/32 and R017 preserved')
baseline=read(PHASE/'BASELINE_VERIFICATION.json')
ck('immutability',baseline['baseline_commit']=='48bf48e93e7eb772993ba3b166f8035f309debff' and baseline['previous_state_sha256']=='2039a86cf1a62151757a656a17f05b767fce0ea510eae1b9c4245a4666a284e8' and baseline['all_source_hashes_unchanged'] is True,'exact frozen C011 baseline and prior state')
prior_plan_paths=[REPO/('work_harps_20261102_'+g+'_context/analysis/PLAN.json') for g in ['c001','c003','c005','c006','c007','c004','c002','c008']]+[REPO/('work_harps_20261103_'+g+'_context/analysis/PLAN.json') for g in ['c009','c010','c012','c011']]
prior_windows=[];group_rows={r['group_id']:r for r in csv.DictReader(group_path.open())};current_dp_ids={r['dp_id'] for r in inv['merged_spectra']}
for path in prior_plan_paths:
 plan=read(path);group_id=path.parents[1].name.split('_')[3].upper();target=group_rows[group_id]['target'];center=plan['group_center_bary_air_angstrom'];overlap=[max(CB-3,center-3),min(CB+3,center+3)];shared=sorted(current_dp_ids & set(plan['merged_dp_ids']))
 ck('prior_dependency',plan['grid']['window_angstrom']==[-3,3] and set(plan['events'])==set(group_rows[group_id]['member_ids'].split('|')) and plan.get('target',target)==target,group_id+' frozen window and original target membership')
 ck('prior_dependency',overlap[0]>overlap[1] and target!='HD114386' and not shared,group_id+' disjoint window and separate observing products from new target')
 prior_windows.append({'group':group_id,'target':target,'center_bary_air_A':center,'window_bary_air_A':[center-3,center+3],'numeric_overlap_bary_air_A':None,'shared_merged_dp_ids':shared})
diff=subprocess.run(['git','diff','--name-only',baseline['baseline_commit'],'--',str(OLD.relative_to(REPO)),*[str(p.relative_to(REPO)) for p in prior_plan_paths],'work_harps_20261103_c011_context'],cwd=REPO,capture_output=True,text=True,check=True).stdout.splitlines()
ck('immutability',not diff,'old extension02, twelve bounded plans and entire prior C011 tracked phase unchanged')
handoff_path=REPO/'work_harps_20261103_c011_context/NEXT_ACTION.json';handoff=read(handoff_path);metadata_path=REPO/'work_harps_20261103_c011_context/scientific_review/NEXT_GROUP_METADATA.json';metadata=read(metadata_path)
ck('prior_dependency',handoff['events']==['V2E2-0094','V2E2-0096','V2E2-0098','V2E2-0110'] and handoff['catalog_center_bary_air_angstrom']==[event_centers[e] for e in handoff['events']] and handoff['proposed_group_center_bary_air_angstrom']==CB and handoff['discovery_anchor_dp_id']=='ADP.2022-03-08T01:01:37.348' and handoff['discovery_anchor_berv_km_s']==ANCHOR and handoff['proposed_topocentric_anchor_air_angstrom']==CT and handoff['target']=='HD114386' and handoff['existing_cohort_epoch_count']==7 and abs(handoff['berv_span_km_s']-51.572001697156)<1e-12,'C011 handoff exact joint centers, own cohort and first-queue March reference')
ck('prior_dependency',handoff['core_overlap_group']=='C016' and handoff['resolution_groups']==['R017'] and handoff['queue_rows']==queue_rows and handoff['distinct_discovery_product_count']==4 and set(handoff['distinct_discovery_products'])==set(expected_products.values()),'handoff all four joint queue members and distinct references')
ck('prior_dependency',handoff['wavelength_dependency']['overlaps_any_completed_bounded_group_window'] is False and handoff['wavelength_dependency']['proposed_group_window_bary_air_angstrom']==[CB-3,CB+3] and handoff['wavelength_dependency']['proposed_group_core_bary_air_angstrom']==[CB-.25,CB+.25],'handoff fixed common core/window is disjoint from prior bounded groups')
ck('target_cohort',{(r['dp_id'],r['date_obs'],r['mjd_obs'],r['berv_km_s']) for r in handoff['existing_cohort_epochs']}=={(r['dp_id'],r['date_obs'],r['mjd_obs'],r['berv_km_s']) for r in inv['merged_spectra']},'all seven exact target-specific epoch identities/dates/BERVs match handoff')
for r in handoff['historical_mapping_stages']:
 record=next(x for x in inv['mapping_records'] if x['event']==r['candidate_id'] and x['order']==r['order'])
 ck('prior_dependency',r['candidate_id'] in expected_events and r['dp_id']==expected_products[r['candidate_id']] and r['order']==19 and all(r[k] is True for k in ['global_grid_usable','original_local_usable','original_baseline_verified','later_five_window_supported']) and record['native_pixel']==r['native_pixel'] and record['raw_row']==r['raw_row'] and record['raw_column']==r['raw_column'] and record['registration_changed'] is r['registration_changed'] is False,r['candidate_id']+' handoff exact all-true mapping stages/raw coordinates')
# Original event-epoch identities establish prior use without opening any profile arrays.
epoch_path=OLD/'epoch_followup/ALL_EPOCH_MEASUREMENTS.csv';epoch_records=list(csv.DictReader(epoch_path.open()))
for event in sorted(expected_events|{'V2E2-0092','V2E2-0104'}):
 rows=[r for r in epoch_records if r['candidate_id']==event]
 ck('existing_evidence_dependency',len(rows)==14 and {r['dp_id'] for r in rows}==current_dp_ids and all(r['target']=='HD114386' for r in rows) and {(r['dp_id'],r['frame']) for r in rows}=={(dp,frame) for dp in current_dp_ids for frame in ['barycentric','topocentric']},event+' original seven-epoch two-frame evidence already exists')
norm=OLD/'normalization_context_20261102';norm_plan_path=norm/'PLAN.json';norm_summary_path=norm/'SUMMARY.json';norm_plan=read(norm_plan_path);norm_summary=read(norm_summary_path)
ck('existing_evidence_dependency',norm_summary['status']=='COMPLETE_DESCRIPTIVE_NORMALIZATION_CONTEXT' and norm_summary['archived_profiles']==28 and norm_summary['focused_profiles']==8 and norm_summary['native_order_contexts']==12 and norm_summary['new_observations']==norm_summary['original_U_labels_changed']==0 and set(norm_plan['event_ids'])=={'V2E2-0092','V2E2-0104'},'completed normalization route custody and zero new observations/label changes')
for r in [r for r in norm_plan['original_product_inputs'] if r['kind']=='SCIENCE']:
 original=next(x for x in inv['merged_spectra'] if x['dp_id']==r['dp_id'])
 ck('existing_evidence_dependency',r['sha256']==original['file']['sha256'] and r['bytes']==original['file']['bytes'],'focused normalization product is identical existing input '+r['dp_id'])
for r in metadata['skipped_completed_routes']:
 ck('existing_evidence_dependency',r['candidate_id'] in ['V2E2-0092','V2E2-0104'] and r['route']=='NORMALIZATION_CONTEXT' and sha(norm_plan_path)==r['plan_sha256'] and sha(norm_summary_path)==r['summary_sha256'] and sha(norm/'README.md')==r['readme_sha256'],'exact completed normalization evidence for skipped route '+r['candidate_id'])
summary={'schema':'HARPS_C016_INPUT_AUDIT_V1','status':'PASS' if not failures else 'FAIL','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_sha256':sha(INV),'restore_script_sha256':sha(I/'restore_inputs.py'),'audit_script_sha256':sha(Path(__file__)),'baseline_commit':baseline['baseline_commit'],'check_count':sum(counts.values()),'checks_by_scope':counts,'failures':failures,'target':'HD114386','input_counts':{'merged':7,'native_A':4,'ancillary':4,'saved_cutouts':4,'archives':3},'anchor':{'dp_id':'ADP.2022-03-08T01:01:37.348','berv_km_s':ANCHOR,'barycentric_common_midpoint_center_A':CB,'topocentric_common_center_A':CT,'policy':'First original-queue discovery; exact event-specific catalog/discovery markers are retained separately.'},'exact_individual_event_centers_bary_air_A':event_centers,'distinct_discovery_products':expected_products,'merged_headers':merged_summary,'raw_identifier_timestamp_offsets':timestamp_offsets,'native_coverage':coverage,'mapping_gate_history':mapping_history,'excluded_native_orders':exclusions,'limits':['All coordinate-support counts derive from fresh monotone header polynomials for each distinct product; finite flux, actual gaps and reference quality remain unassessed.','The fixed common midpoint/first-queue March anchor does not replace exact individual catalog/discovery markers or imply a measured linewidth.','Native BUNIT is absent; retain instrumental/native flux labels without asserted calibrated ADU equivalence to merged flux.','Topocentric air convention is inherited from the archived extractor, without a new wavelength solution.','Every original order-19 global/local/baseline/later-five-window stage is true; no other-wavelength discrepancy or old-target quality is transferred. No new registration/mapping is performed.','ERR is declared unavailable; no positive uncertainty support is inferred.'],'source_hashes':inv['source_hashes'],'network_requests':0,'new_flux_or_pixel_values_interpreted':0,'raw_images_restored_or_read':False}
summary['prior_wavelength_dependency']={'C016_window_bary_air_A':[CB-3,CB+3],'completed_windows':prior_windows,'disjoint_from_all_twelve_completed_bounded_contexts':True,'interpretation':'New target-specific HD114386 products are separate from prior bounded-group products. Its seven observations and original C016 epoch/native/raw evidence already existed, and also supplied completed blue normalization contexts. This dependent post-detection context adds no observation, blind/untouched data or independent observing evidence. Earlier 0092 raw-window discrepancies remain local and do not alter the four historically supported order-19 panels.'}
summary['additional_source_hashes']={str(p.relative_to(REPO)):sha(p) for p in [group_path,event_path,handoff_path,metadata_path,current_path,queue_path,epoch_path,norm_plan_path,norm_summary_path,norm/'README.md',*prior_plan_paths]}
summary['historical_review_chains']=[{'event':event,'primary_code':next(r['code'] for r in historical_reviews['primary'] if r['review_id']==event),'secondary_code':next(r['code'] for r in historical_reviews['secondary'] if r['review_id']==event),'root_adopted_code':next(r['code'] for r in historical_reviews['adopted'] if r['review_id']==event),'qualification':next(r['evidence'] for r in historical_reviews['adopted'] if r['review_id']==event),'no_classification_performed_by_input_audit':True} for event in sorted(expected_events)]
summary['all_order_header_geometry_count']=len(all_order_geometry)
summary['common_context_geometry']={'barycentric_window_air_A':[CB-3,CB+3],'barycentric_core_air_A':[CB-.25,CB+.25],'topocentric_window_air_A':[CT-3,CT+3],'topocentric_core_air_A':[CT-.25,CT+.25],'coverage_count_core_policy':'Fixed common group core, distinct from each original member-centered core.'}
summary['exact_individual_original_cores_bary_air_A']={event:[center-.25,center+.25] for event,center in event_centers.items()}
summary['support_assessment_scope']={'coordinate_support':'Header-polynomial geometry only','finite_sample_support_assessed':False,'reference_quality_assessed':False,'no_usable_normalization_or_finite_flux_inferred':True}
summary['unique_native_coverage']=[dict({k:v for k,v in row.items() if k!='event'},discovery_for=next(p['discovery_for'] for p in inv['native_products'] if p['dp_id']==row['dp_id'])) for i,row in enumerate(coverage) if not any((prior['dp_id'],prior['order'],prior['frame'])==(row['dp_id'],row['order'],row['frame']) for prior in coverage[:i])]
summary['deduplication']='Four events in four distinct discovery products supply four native order-19 contexts and four preserved raw panels, or eight product/order/frame contexts. Both frames of each product reuse one exposure. All seven HD114386 epochs and original epoch/native/raw evidence already existed.'
(HERE/'INPUT_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':summary['status'],'check_count':summary['check_count'],'failures':failures}));assert not failures
