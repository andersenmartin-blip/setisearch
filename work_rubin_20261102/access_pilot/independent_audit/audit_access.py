#!/usr/bin/env python3
"""Offline independent audit of Rubin access/development data and metadata only."""
import csv,hashlib,json,math,datetime
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.utils import iers
iers.conf.auto_download=False
P=Path(__file__).resolve().parent.parent
checks=Counter();failures=[]
def check(category,label,condition,detail=None):
 checks[category]+=1
 if not condition:failures.append({'category':category,'check':label,**({'detail':detail} if detail is not None else {})})
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def j(name,ids=False):return json.loads((P/name).read_text(),**({'parse_int':str} if ids else {}))
def csvrows(name):
 with (P/name).open(newline='') as f:return list(csv.DictReader(f))
def valid_id(value):return isinstance(value,str) and value.isdigit() and 0<int(value)<2**63
def finite(value):return isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value)
def valid_flux(row):return finite(row.get('r:scienceFlux')) and finite(row.get('r:scienceFluxErr')) and row['r:scienceFluxErr']>0
def utc(mjd):return Time(mjd,format='mjd',scale='tai').utc.isot
def check_row(category,label,observed,expected):
 for key,val in expected.items():
  good=observed.get(key)==('' if val is None else str(val))
  check(category,label+':'+key,good,{'actual':observed.get(key),'expected':val} if not good else None)
freeze=j('DEVELOPMENT_FREEZE.json');validation=j('DEVELOPMENT_VALIDATION.json');cutval=j('CUTOUT_VALIDATION.json')
cone=j('metadata/cone_october_n100.json',True);selection=csvrows('DEVELOPMENT_SELECTION.csv')
remaining=csvrows('MAIN_METADATA_CANDIDATES_UNMATCHED.csv');mainplan=j('METADATA_MAIN_ACQUISITION.json')
check('selection','433 metadata rows',len(cone)==433)
coneids=[r['r:diaObjectId'] for r in cone]
check('selection','unique positive exact64bit cone IDs',len(set(coneids))==433 and all(valid_id(x) for x in coneids))
ordered=sorted(coneids,key=int);selected=ordered[:20];selectedset=set(selected);remainingids=ordered[20:]
check('selection','frozen smallest20 numeric IDs',freeze['selected_ids']==selected)
check('selection','20 selection CSV IDs',len(selection)==20 and [r['r:diaObjectId'] for r in selection]==selected)
check('selection','cone metadata hash',sha(P/'metadata/cone_october_n100.json')==freeze['source_metadata_sha256'])
check('selection','selection CSV hash',sha(P/'DEVELOPMENT_SELECTION.csv')==freeze['selection_sha256'])
byid={r['r:diaObjectId']:r for r in cone}
for r in selection+remaining:check_row('selection','metadata CSV row '+r['r:diaObjectId'],r,byid[r['r:diaObjectId']])
check('selection','remaining413 complete',len(remaining)==413 and [r['r:diaObjectId'] for r in remaining]==remainingids==mainplan['ids'])
check('selection','development exact ID exclusion',set(remainingids).isdisjoint(selectedset) and mainplan['development_excluded']==selected)
check('selection','remaining inventory hash',sha(P/'MAIN_METADATA_CANDIDATES_UNMATCHED.csv')==mainplan['source_inventory_sha256'])
check('selection','no main flux flag',mainplan['main_flux_values_requested'] is False)
for name,digest in freeze['schema_sha256'].items():check('selection','schema hash '+name,sha(P/'metadata'/name)==digest)
for pair,oid in zip(freeze['cutout_selection'],selected[:2]):check('selection','first2 cutout identity '+oid,pair=={'diaObjectId':oid,'diaSourceId':byid[oid]['r:diaSourceId']})
receipts=[];science_bytes=0
for path in sorted(P.rglob('*.receipt.json')):
 receipt=json.loads(path.read_text());data_path=P/receipt['path'];receipts.append(receipt)
 check('receipts','path/hash/length '+str(path.relative_to(P)),data_path.exists() and data_path.stat().st_size==receipt['bytes_saved'] and sha(data_path)==receipt['sha256'])
 check('receipts','allowed provider '+receipt['path'],receipt['url'].startswith('https://api.lsst.fink-portal.org/api/v1/'))
 check('receipts','response limit '+receipt['path'],receipt['bytes_saved']<=receipt['max_response_bytes'])
 if receipt['http_status']==200:
  check('receipts','complete success '+receipt['path'],receipt['complete'] is True and receipt['error'] is None)
 else:check('receipts','preserved expected n1000 failure',receipt['path']=='metadata/cone_october.json' and receipt['http_status']==400 and receipt['complete'] is False)
 if receipt['path'].startswith('raw/'):
  science_bytes+=receipt['bytes_saved']
  check('receipts','flux/cutout after freeze '+receipt['path'],receipt['started_utc']>freeze['created_utc'])
check('receipts','raw total frozen budget',science_bytes<=freeze['limits']['max_total_science_bytes'])
# Every metadata-only cone and main-history response must lack photometry values.
def no_flux(rows):return all(not any('flux' in key.lower() or key.lower().endswith(('magnitude',':mag')) for key in row) for row in rows)
check('metadata','cone no photometry fields',no_flux(cone))
mainrows=[];requested=[]
for path in sorted((P/'metadata').glob('main_candidate_sources_[0-9][0-9].json')):
 rows=json.loads(path.read_text(),parse_int=str);receipt=json.loads(path.with_name(path.name+'.receipt.json').read_text());queryids=receipt['payload']['diaObjectId'].split(',');requested.extend(queryids)
 check('metadata','bounded requested IDs '+path.name,len(queryids)<=100 and set(queryids)<=set(remainingids) and set(queryids).isdisjoint(selectedset))
 check('metadata','exact metadata columns '+path.name,receipt['payload']['columns']==mainplan['columns'] and 'flux' not in receipt['payload']['columns'].lower())
 check('metadata','returned IDs subset '+path.name,all(valid_id(r['r:diaObjectId']) and valid_id(r['r:diaSourceId']) and r['r:diaObjectId'] in queryids for r in rows))
 check('metadata','no main photometry '+path.name,no_flux(rows))
 mainrows.extend(rows)
check('metadata','all413 requested once',requested==remainingids and len(set(requested))==413)
check('metadata','3596 saved metadata history rows',len(mainrows)==3596)
check('metadata','all413 represented',{r['r:diaObjectId'] for r in mainrows}==set(remainingids))
check('metadata','unique metadata source IDs',len({r['r:diaSourceId'] for r in mainrows})==len(mainrows))
sources=j('raw/development_sources.json',True);forced=j('raw/development_forced.json',True)
flags=list(validation['source_flag_inventory'])
check('streams','22 explicitly listed source flags',len(flags)==22)
streaminfo={r['stream']:r for r in validation['streams']}
for name,rows,idcol,n,nobj in [('sources',sources,'r:diaSourceId',259,20),('forced',forced,'r:diaForcedSourceId',326,14)]:
 check('streams',name+' exact row/object counts',len(rows)==n and len({r['r:diaObjectId'] for r in rows})==nobj)
 check('streams',name+' selected development only',{r['r:diaObjectId'] for r in rows}<=selectedset)
 check('streams',name+' request exact selection',j('raw/development_'+name+'.json.receipt.json')['payload']['diaObjectId'].split(',')==selected)
 for i,row in enumerate(rows):
  for field in ['r:diaObjectId',idcol,'r:visit']:check('identifiers',name+str(i)+field,valid_id(row[field]))
  check('streams',name+str(i)+' finite time/band',finite(row['r:midpointMjdTai']) and row['r:band'] in 'ugrizy' and len(row['r:band'])==1)
 measureids=[r[idcol] for r in rows];lo=min(r['r:midpointMjdTai'] for r in rows);hi=max(r['r:midpointMjdTai'] for r in rows)
 expected={'rows':n,'distinct_objects':nobj,'unique_measurement_ids':len(set(measureids)),'duplicate_id_rows':len(measureids)-len(set(measureids)),'valid_direct_science_flux_error_rows':sum(valid_flux(r) for r in rows),'mjd_tai_min':lo,'mjd_tai_max':hi,'utc_min':utc(lo),'utc_max':utc(hi),'input_sha256':sha(P/'raw'/('development_'+name+'.json'))}
 for key,value in expected.items():check('summary',name+key,streaminfo[name][key]==value)
check('summary','selected/retrieved object counts',validation['selected_objects']==20 and validation['retrieved_source_objects']==20 and validation['retrieved_forced_objects']==14)
for key,field in [('source_schema_versions','f:lsst_schema_version'),('source_observation_reasons','r:observation_reason')]:check('summary',key,validation[key]==dict(Counter(r.get(field,'ABSENT') for r in sources)))
for flag in flags:
 counts=dict(Counter('ABSENT' if 'r:'+flag not in r else 'null' if r['r:'+flag] is None else str(r['r:'+flag]) for r in sources));check('summary','flag '+flag,validation['source_flag_inventory'][flag]==counts)
for stream,rows in [('source',sources),('forced',forced)]:check('summary',stream+' withdrawal presence',validation[stream+'_timeWithdrawnMjdTai_presence']==dict(Counter('present' if 'r:timeWithdrawnMjdTai' in r else 'absent' for r in rows)))
# Recompute each inventory from actual rows, caching TAI->UTC conversions.
utc_by_time={t:utc(t) for t in {r['r:midpointMjdTai'] for r in sources+forced}}
def stamp(r):return utc_by_time[r['r:midpointMjdTai']]
def inwindow(r):return '2026-10-01'<=stamp(r)<'2026-11-01'
def goodflags(r):return all(r.get('r:'+k) is False for k in flags)
objects=csvrows('DEVELOPMENT_OBJECT_INVENTORY.csv');bands=csvrows('DEVELOPMENT_BAND_COVERAGE.csv')
check('inventory','20 object rows exact order',[r['diaObjectId'] for r in objects]==selected)
expectedbands=[]
for obs in objects:
 oid=obs['diaObjectId'];src=[r for r in sources if r['r:diaObjectId']==oid];fp=[r for r in forced if r['r:diaObjectId']==oid]
 expected={'diaObjectId':oid,'development_only':True,'source_rows':len(src),'forced_rows':len(fp),'source_distinct_visits':len({r['r:visit'] for r in src}),'source_utc_nights':len({stamp(r)[:10] for r in src}),'forced_utc_nights':len({stamp(r)[:10] for r in fp}),'source_bands':'|'.join(sorted({r['r:band'] for r in src})),'forced_bands':'|'.join(sorted({r['r:band'] for r in fp})),'first_source_utc':min(stamp(r) for r in src),'last_source_utc':max(stamp(r) for r in src),'main_window_source_rows':sum(inwindow(r) for r in src),'main_window_forced_rows':sum(inwindow(r) for r in fp),'sources_passing_all_listed_flags_explicit_false':sum(goodflags(r) for r in src),'valid_gaia_annotations':'|'.join(sorted({r.get('f:xm_gaiadr3_DR3Name','') for r in src if str(r.get('f:xm_gaiadr3_DR3Name','')).startswith('Gaia DR3 ')})),'Gaia_association_independently_verified':False}
 check_row('inventory',oid,obs,expected)
 for stream,data in [('source',src),('forced',fp)]:
  for band in sorted({r['r:band'] for r in data}):
   rows=[r for r in data if r['r:band']==band];usable=[r for r in rows if valid_flux(r)];positive=[r for r in usable if r['r:scienceFlux']>0]
   expectedbands.append({'diaObjectId':oid,'stream':stream,'band':band,'rows':len(rows),'unique_visits':len({r['r:visit'] for r in rows}),'unique_utc_nights':len({stamp(r)[:10] for r in rows}),'valid_direct_science_flux_error_rows':len(usable),'positive_direct_science_flux_error_rows':len(positive),'first_utc':min(stamp(r) for r in rows),'last_utc':max(stamp(r) for r in rows),'main_window_rows':sum(inwindow(r) for r in rows),'positive_science_rows_before_october':sum(stamp(r)<'2026-10-01' for r in positive),'quality_flags_available':stream=='source','passing_all_listed_flags_explicit_false':sum(goodflags(r) for r in rows) if stream=='source' else '', 'readiness_is_sampling_only':True})
check('inventory','band rows complete count/order',[(r['diaObjectId'],r['stream'],r['band']) for r in bands]==[(r['diaObjectId'],r['stream'],r['band']) for r in expectedbands])
for observed,expected in zip(bands,expectedbands):check_row('inventory',str((expected['diaObjectId'],expected['stream'],expected['band'])),observed,expected)
for stream,key in [('source','source_objects_with_at_least_one_band_three_positive_pre_october_rows'),('forced','forced_objects_with_at_least_one_band_three_positive_pre_october_rows')]:check('summary',key,validation[key]==len({r['diaObjectId'] for r in expectedbands if r['stream']==stream and r['positive_science_rows_before_october']>=3}))
# Supplement is separate and not silently folded into listed-22 flag inventories.
supplement=j('metadata/development_quality_supplement.json',True);suppby={r['r:diaSourceId']:r for r in supplement}
check('quality supplement','259 exact source identities',len(supplement)==259 and set(suppby)=={r['r:diaSourceId'] for r in sources})
for row in sources:
 s=suppby[row['r:diaSourceId']];check('quality supplement','identity '+row['r:diaSourceId'],all(s[k]==row[k] for k in ['r:diaObjectId','r:diaSourceId','r:midpointMjdTai','r:visit','r:detector','r:band']))
suppflags={key:dict(Counter('ABSENT' if key not in r else str(r[key]) for r in supplement)) for key in ['r:pixelFlags','r:pixelFlags_interpolatedCenter']}
# Check every expected FITS identity and all image plane inventory fields.
expected_fits={f"raw/cutouts/{pair['diaObjectId']}_{pair['diaSourceId']}_{kind}.fits" for pair in freeze['cutout_selection'] for kind in ['Science','Template','Difference']}
actual_fits={str(p.relative_to(P)) for p in (P/'raw/cutouts').glob('*.fits')}
check('cutouts','six exact products',actual_fits==expected_fits and len(actual_fits)==6)
check('cutouts','six inventory rows',{r['path'] for r in cutval['inventory']}==expected_fits and cutval['available_cutout_products']==6 and cutval['checked_development_objects']==2)
uncertainty_types={};cutout_details=[]
for item in cutval['inventory']:
 path=P/item['path'];parts=path.stem.split('_');oid,sid,kind=parts
 check('cutouts','length/hash '+kind+oid,path.stat().st_size==item['bytes'] and sha(path)==item['sha256'])
 receipt=j(item['path']+'.receipt.json');check('cutouts','request identity '+kind+oid,receipt['payload']=={'diaSourceId':sid,'kind':kind,'output-format':'FITS'} and sid==byid[oid]['r:diaSourceId'])
 with fits.open(path,checksum=True) as hdus:
  check('cutouts','four named HDUs '+kind+oid,[h.name for h in hdus]==['PRIMARY','UNCERT','MASKPLANE','PSFIMAGE'])
  check('cutouts','30x30 science/variance/mask '+kind+oid,all(h.data.shape==(30,30) for h in hdus[:3]))
  check('cutouts','nJy primary unit '+kind+oid,hdus[0].header.get('BUNIT')=='nJy')
  check('cutouts','explicit variance UTYPE '+kind+oid,hdus['UNCERT'].header.get('UTYPE')=='VarianceUncertainty')
  uncertainty_types[item['path']]=hdus['UNCERT'].header.get('UTYPE')
  for h,stored in zip(hdus,item['hdus']):
   check('cutouts','plane inventory '+kind+oid+h.name,stored['name']==h.name and stored['hdu_type']==type(h).__name__ and stored['shape']==list(h.data.shape) and stored['dtype']==str(h.data.dtype) and stored['finite_pixels']==int(np.isfinite(h.data).sum()) and all(h.header.get(k)==v for k,v in stored['header_provenance'].items()))
  cutout_details.append({'path':item['path'],'uncertainty_type':hdus['UNCERT'].header.get('UTYPE'),'primary_unit':hdus[0].header.get('BUNIT'),'variance_nonnegative_pixels':int(np.sum(hdus['UNCERT'].data>=0)),'variance_finite_pixels':int(np.isfinite(hdus['UNCERT'].data).sum())})
files=['DEVELOPMENT_FREEZE.json','DEVELOPMENT_SELECTION.csv','DEVELOPMENT_VALIDATION.json','DEVELOPMENT_OBJECT_INVENTORY.csv','DEVELOPMENT_BAND_COVERAGE.csv','CUTOUT_VALIDATION.json','METADATA_MAIN_ACQUISITION.json','MAIN_METADATA_CANDIDATES_UNMATCHED.csv','validate_development.py','access.py']
report={'schema':'RUBIN_ACCESS_INDEPENDENT_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not failures else 'FAIL','checks':sum(checks.values()),'checks_by_category':dict(checks),'failures':failures,'counts':{'cone_metadata_objects':len(cone),'development_objects':len(selected),'source_rows':len(sources),'source_objects':len({r['r:diaObjectId'] for r in sources}),'forced_rows':len(forced),'forced_objects':len({r['r:diaObjectId'] for r in forced}),'remaining_metadata_objects':len(remainingids),'remaining_metadata_history_rows':len(mainrows),'main_photometry_rows':0,'fits_products':len(actual_fits),'receipt_count':len(receipts),'raw_payload_bytes':science_bytes,'band_inventory_rows':len(bands)},'uncertainty_planes':cutout_details,'additional_quality_flags_not_in_listed22_inventory':suppflags,'limits':['Read-only offline audit; no network requests and no signal/origin classification.','Local request/response provenance, hashes and schema consistency verified; this is not independent archive authenticity validation.','The433-row cone response exceeded requested n100 and is not an exhaustive regional catalog.','Only exact20development Rubin IDs are currently excluded; coordinate-associated/Gaia-counterpart exclusion still requires independent crossmatch before main sample.','Listed-22 source quality inventory excludes separate pixelFlags and pixelFlags_interpolatedCenter supplement; future eligibility must explicitly apply all chosen flags.','UNCERT planes store VarianceUncertainty, not standard deviation.','No main science selection or main photometry search has been performed.','Astropy TAI-to-UTC conversion shares upstream library with original validator; scalar joins and inventories implemented independently.'],'file_sha256':{name:sha(P/name) for name in files},'audit_script_sha256':sha(Path(__file__))}
(P/'independent_audit/AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','checks','checks_by_category','failures','counts','additional_quality_flags_not_in_listed22_inventory']},indent=2))
raise SystemExit(bool(failures))
