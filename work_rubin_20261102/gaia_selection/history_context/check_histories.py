"""Metadata-only positional context; never changes frozen main selection."""
from pathlib import Path
import csv,json,hashlib,datetime,math,warnings
from collections import defaultdict,Counter
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astropy import units as u
OUT=Path(__file__).resolve().parent;GAIA=OUT.parent;ACCESS=GAIA.parent/'access_pilot'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):return list(csv.DictReader(p.open()))
def number(x):
 try:v=float(x);return v if math.isfinite(v)else math.nan
 except:return math.nan
def save(name,rs,keys=None):
 keys=keys or list(dict.fromkeys(k for r in rs for k in r))
 with(OUT/name).open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rs)
def main():
 plan=json.loads((OUT/'PLAN.json').read_text());selection_hash=sha(GAIA/'MAIN_SELECTION.csv');assert selection_hash==plan['selection_sha256']
 for f in plan['metadata_inputs']:assert sha(ACCESS/'metadata'/f['filename'])==f['sha256']
 selection=csvrows(GAIA/'MAIN_SELECTION.csv');selected={r['diaObjectId']:r for r in selection};catalog={r['source_id']:r for r in csvrows(GAIA/'GAIA_DR3_FIELD.csv')}
 assert len(selected)==188
 metadata=[]
 for entry in plan['metadata_inputs']:
  p=ACCESS/'metadata'/entry['filename'];rs=json.loads(p.read_text(),parse_int=str)
  for r in rs:
   assert not any('flux'in k.lower()for k in r),'Unexpected flux field in fixed metadata-only input'
   if str(r['r:diaObjectId'])in selected:metadata.append(dict(r,metadata_input=entry['filename']))
 valid=[];results=[]
 for r in metadata:
  rid=str(r['r:diaObjectId']);s=selected[rid];g=catalog[s['matched_gaia_source_id']]
  row={'diaObjectId':rid,'diaSourceId':str(r['r:diaSourceId']),'matched_gaia_source_id':s['matched_gaia_source_id'],'band':r.get('r:band',''),'visit':str(r.get('r:visit','')),'detector':str(r.get('r:detector','')),'midpointMjdTai':r.get('r:midpointMjdTai',''),'source_ra_deg':r.get('r:ra',''),'source_dec_deg':r.get('r:dec',''),'metadata_input':r['metadata_input']}
  vals=[number(r.get(k))for k in ['r:ra','r:dec','r:midpointMjdTai']]
  if not all(math.isfinite(x)for x in vals):row['status']='MISSING_FINITE_SOURCE_COORDINATE_OR_TIME';results.append(row);continue
  valid.append((row,g,vals))
 def arr(key):return np.array([number(g[key])for row,g,vals in valid])
 ra,dec,pmra,pmdec,epoch,plx,rv=[arr(k)for k in ['ra','dec','pmra','pmdec','ref_epoch','parallax','radial_velocity']]
 times=Time(np.array([vals[2]for row,g,vals in valid]),format='mjd',scale='tai').tcb
 predicted_ra=np.empty(len(valid));predicted_dec=np.empty(len(valid));warns=[]
 for mask in [plx>0,~(plx>0)]:
  kw=dict(ra=ra[mask]*u.deg,dec=dec[mask]*u.deg,pm_ra_cosdec=pmra[mask]*u.mas/u.yr,pm_dec=pmdec[mask]*u.mas/u.yr,obstime=Time(epoch[mask],format='jyear',scale='tcb'),frame='icrs')
  if np.all(plx[mask]>0):kw.update(distance=1000/plx[mask]*u.pc,radial_velocity=np.where(np.isfinite(rv[mask]),rv[mask],0)*u.km/u.s)
  with warnings.catch_warnings(record=True)as caught:
   warnings.simplefilter('always');c=SkyCoord(**kw).apply_space_motion(new_obstime=times[mask]);warns.extend(str(w.message)for w in caught)
  predicted_ra[mask]=c.ra.deg;predicted_dec[mask]=c.dec.deg
 targets=SkyCoord(ra=np.array([vals[0]for row,g,vals in valid])*u.deg,dec=np.array([vals[1]for row,g,vals in valid])*u.deg)
 sep=targets.separation(SkyCoord(ra=predicted_ra*u.deg,dec=predicted_dec*u.deg)).arcsec
 for i,(row,g,vals)in enumerate(valid):
  row.update(status='MEASURED_METADATA_CONTEXT',gaia_ra_at_source_time_deg=float(predicted_ra[i]),gaia_dec_at_source_time_deg=float(predicted_dec[i]),separation_arcsec=float(sep[i]),within1arcsec=bool(sep[i]<=1),within2arcsec=bool(sep[i]<=2),utc_night=str(Time(vals[2],format='mjd',scale='tai').utc.isot)[:10]);results.append(row)
 results.sort(key=lambda r:(int(r['diaObjectId']),number(r['midpointMjdTai']),int(r['diaSourceId'])))
 grouped=defaultdict(list)
 for r in results:grouped[r['diaObjectId']].append(r)
 summaries=[]
 for s in selection:
  rs=grouped[s['diaObjectId']];good=[r for r in rs if r['status']=='MEASURED_METADATA_CONTEXT'];v=[r['separation_arcsec']for r in good]
  summaries.append({'selection_index':s['selection_index'],'diaObjectId':s['diaObjectId'],'matched_gaia_source_id':s['matched_gaia_source_id'],'metadata_rows':len(rs),'unique_diaSourceIds':len({r['diaSourceId']for r in rs}),'finite_position_rows':len(good),'missing_position_rows':len(rs)-len(good),'distinct_utc_nights':len({r['utc_night']for r in good}),'bands':';'.join(sorted({r['band']for r in rs})),'median_separation_arcsec':float(np.median(v))if v else'','max_separation_arcsec':max(v)if v else'','source_rows_outside1arcsec':sum(not r['within1arcsec']for r in good),'source_rows_outside2arcsec':sum(not r['within2arcsec']for r in good),'frozen_selection_unchanged':True})
 save('SOURCE_POSITION_CONTEXT.csv',results);save('OBJECT_POSITION_CONTEXT.csv',summaries)
 assert sha(GAIA/'MAIN_SELECTION.csv')==selection_hash
 report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'COMPLETE_METADATA_ONLY_HISTORY_CONTEXT_SELECTION_UNCHANGED','selected_objects':len(selection),'objects_with_metadata_history':sum(r['metadata_rows']>0 for r in summaries),'source_metadata_rows':len(results),'unique_object_source_pairs':len({(r['diaObjectId'],r['diaSourceId'])for r in results}),'finite_position_rows':len(valid),'missing_position_rows':len(results)-len(valid),'rows_outside1arcsec':sum(r['source_rows_outside1arcsec']for r in summaries),'rows_outside2arcsec':sum(r['source_rows_outside2arcsec']for r in summaries),'objects_any_row_outside1arcsec':sum(r['source_rows_outside1arcsec']>0 for r in summaries),'objects_any_row_outside2arcsec':sum(r['source_rows_outside2arcsec']>0 for r in summaries),'max_source_separation_arcsec':float(np.max(sep)),'median_source_separation_arcsec':float(np.median(sep)),'source_mjd_tai_min':min(vals[2]for row,g,vals in valid),'source_mjd_tai_max':max(vals[2]for row,g,vals in valid),'propagation_warnings':dict(Counter(warns)),'selection_sha256':selection_hash,'script_sha256':sha(OUT/'check_histories.py'),'main_flux_values_read':False,'limitations':['This is supplementary descriptive QA of the already retrieved metadata histories, not a replacement selection or a new photometric quality gate.','No source centroid uncertainty/flags or flux values used; offsets can reflect centroid noise, blends, misassociation or other processing. No origin is assigned.','One fixed Gaia counterpart per selected object is propagated; this supplemental check does not repeat the all-neighbor association decision for every source epoch.','Available history metadata need not be exhaustive and may span beyond the eventual main photometry window.','The original188-object selection, ordering and classifications remain unchanged.']}
 (OUT/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
