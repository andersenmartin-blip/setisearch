"""Original Gaia rule applied to separate frozen104-object extension; no flux."""
from pathlib import Path
import csv,json,hashlib,datetime,math,warnings
from collections import Counter,defaultdict
import numpy as np
from astropy.time import Time
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.utils import iers
iers.conf.auto_download=False

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
ACCESS=OUT.parent/'access_pilot'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(Path(p).open()))
def num(x):
 try:v=float(x);return v if math.isfinite(v) else math.nan
 except (TypeError,ValueError):return math.nan
def write(name,records,keys=None):
 keys=keys or list(dict.fromkeys(k for r in records for k in r))
 with (OUT/name).open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(records)
def jdsep(ra,dec,rra,rdec):
 # Stable angular separation via haversine, radians -> arcsec.
 a=np.deg2rad(ra);d=np.deg2rad(dec);ar=np.deg2rad(rra);dr=np.deg2rad(rdec)
 h=np.sin((d-dr)/2)**2+np.cos(d)*np.cos(dr)*np.sin((a-ar)/2)**2
 return np.rad2deg(2*np.arcsin(np.sqrt(np.clip(h,0,1))))*3600

def run():
 plan=json.loads((OUT/'PLAN.json').read_text())
 for entry in plan['input_files']:assert sha(ROOT/entry['path'])==entry['sha256']
 assert sha(Path(__file__))==plan['match_script_sha256']
 acquisition=json.loads((OUT/'ACQUISITION_RECEIPTS.json').read_text())[-1]
 assert acquisition['status']=='SUCCESS'and acquisition['sha256']==sha(OUT/'GAIA_DR3_FIELD.csv')
 main=rows(OUT/'CANDIDATE_METADATA.csv')
 assert len(main)==104 and len({x['r:diaObjectId']for x in main})==104
 prior=rows(ACCESS/'DEVELOPMENT_SELECTION.csv')+rows(ACCESS/'MAIN_METADATA_CANDIDATES_UNMATCHED.csv')
 assert len(prior)==433
 objs=[dict(x,cohort='prior433_comparison_only')for x in prior]+[dict(x,cohort='extension_metadata_pool')for x in main]
 assert not ({x['r:diaObjectId']for x in main}&{x['r:diaObjectId']for x in prior})
 catalog=rows(OUT/'GAIA_DR3_FIELD.csv');assert 1<len(catalog)<50000
 assert len({x['source_id']for x in catalog})==len(catalog)
 n=len(catalog);data={k:np.array([num(x[k])for x in catalog])for k in ['ra','dec','ref_epoch','ra_error','dec_error','pmra','pmdec','pmra_error','pmdec_error','pmra_pmdec_corr','parallax','parallax_error','radial_velocity','ra_pmra_corr','dec_pmdec_corr']}
 assert np.all(np.isfinite(data['ra']))and np.all(np.isfinite(data['dec']))
 pmok=np.isfinite(data['pmra'])&np.isfinite(data['pmdec'])&np.isfinite(data['ref_epoch'])
 withdist=pmok&(data['parallax']>0);nodist=pmok&~withdist
 coords={}
 for label,mask in [('distance',withdist),('angular',nodist)]:
  kw=dict(ra=data['ra'][mask]*u.deg,dec=data['dec'][mask]*u.deg,pm_ra_cosdec=data['pmra'][mask]*u.mas/u.yr,pm_dec=data['pmdec'][mask]*u.mas/u.yr,obstime=Time(data['ref_epoch'][mask],format='jyear',scale='tcb'),frame='icrs')
  if label=='distance':
   kw['distance']=1000/data['parallax'][mask]*u.pc
   kw['radial_velocity']=np.where(np.isfinite(data['radial_velocity'][mask]),data['radial_velocity'][mask],0)*u.km/u.s
  coords[label]=SkyCoord(**kw)
 csep=jdsep(data['ra'],data['dec'],8.986275,-42.709834)
 assert csep.max()<=3960.001
 allneighbors=[];objects=[];warnings_seen=Counter()
 for index,obj in enumerate(objs):
  target_time=Time(float(obj['r:midpointMjdTai']),format='mjd',scale='tai').tcb
  epoch=float(target_time.jyear);ra=data['ra'].copy();dec=data['dec'].copy()
  with warnings.catch_warnings(record=True)as warns:
   warnings.simplefilter('always')
   for label,mask in [('distance',withdist),('angular',nodist)]:
    moved=coords[label].apply_space_motion(new_obstime=target_time)
    ra[mask]=moved.ra.deg;dec[mask]=moved.dec.deg
   warnings_seen.update(str(x.message)for x in warns)
  sep=jdsep(ra,dec,float(obj['r:ra']),float(obj['r:dec']));order=np.argsort(sep,kind='stable');j=int(order[0]);g=catalog[j]
  n1=int(np.sum(sep<=1));n2=int(np.sum(sep<=2));n10=int(np.sum(sep<=10))
  evidence_indices=sorted(set(np.where(sep<=10)[0].tolist()+order[:2].tolist()),key=lambda i:(sep[i],int(catalog[i]['source_id'])))
  for rank,i in enumerate(evidence_indices,1):
   dt=epoch-data['ref_epoch'][i]
   va=data['ra_error'][i]**2+(dt*data['pmra_error'][i])**2+2*dt*data['ra_pmra_corr'][i]*data['ra_error'][i]*data['pmra_error'][i]
   vd=data['dec_error'][i]**2+(dt*data['pmdec_error'][i])**2+2*dt*data['dec_pmdec_corr'][i]*data['dec_error'][i]*data['pmdec_error'][i]
   allneighbors.append({'diaObjectId':obj['r:diaObjectId'],'cohort':obj['cohort'],'rank_in_stored_neighbors':rank,'gaia_source_id':catalog[i]['source_id'],'separation_arcsec':float(sep[i]),'within1arcsec':bool(sep[i]<=1),'within2arcsec':bool(sep[i]<=2),'within10arcsec':bool(sep[i]<=10),'motion_propagated':bool(pmok[i]),'propagated_ra_deg':float(ra[i]),'propagated_dec_deg':float(dec[i]),'target_jyear_tcb':epoch,'gaia_ref_epoch_jyear_tcb':float(data['ref_epoch'][i]),'gaia_coordinate_shift_arcsec':float(jdsep(ra[i],dec[i],data['ra'][i],data['dec'][i])),'gaia_propagated_ra_sigma_mas_linear':math.sqrt(va)if math.isfinite(va)and va>=0 else '', 'gaia_propagated_dec_sigma_mas_linear':math.sqrt(vd)if math.isfinite(vd)and vd>=0 else '', 'parallax_mas':g.get('parallax','')if i==j else catalog[i].get('parallax',''),'pmra_masyr':catalog[i]['pmra'],'pmdec_masyr':catalog[i]['pmdec'],'perspective_distance_used':bool(withdist[i]),'radial_velocity_measured':bool(withdist[i]and math.isfinite(data['radial_velocity'][i]))})
  plx=data['parallax'][j];err=data['parallax_error'][j];psnr=plx/err if math.isfinite(plx)and math.isfinite(err)and err>0 else math.nan
  pmsig=math.nan;rho=data['pmra_pmdec_corr'][j];er=data['pmra_error'][j];ed=data['pmdec_error'][j]
  if pmok[j] and math.isfinite(rho)and abs(rho)<1 and er>0 and ed>0:
   a=data['pmra'][j]/er;b=data['pmdec'][j]/ed
   pmsig=math.sqrt(max(0,(a*a-2*rho*a*b+b*b)/(1-rho*rho)))
  reasons=[]
  if n1==0:reasons.append('NO_GAIA_WITHIN_1_ARCSEC')
  elif n1>1:reasons.append('MULTIPLE_GAIA_WITHIN_1_ARCSEC')
  if n2>1:reasons.append('SECOND_GAIA_WITHIN_2_ARCSEC')
  if not pmok[j]:reasons.append('NEAREST_GAIA_MOTION_UNAVAILABLE')
  if not ((math.isfinite(psnr)and psnr>=3)or(math.isfinite(pmsig)and pmsig>=5)):reasons.append('STELLAR_ASTROMETRIC_EVIDENCE_BELOW_FROZEN_GUARD')
  unique=n1==1 and n2==1 and bool(pmok[j]);qualified=unique and not reasons
  objects.append({'diaObjectId':obj['r:diaObjectId'],'cohort':obj['cohort'],'ra_deg':obj['r:ra'],'dec_deg':obj['r:dec'],'coordinate_reference_mjd_tai_proxy':obj['r:midpointMjdTai'],'coordinate_reference_jyear_tcb_proxy':epoch,'nearest_gaia_source_id':g['source_id'],'matched_gaia_source_id':g['source_id']if unique else '', 'nearest_separation_arcsec':float(sep[j]),'second_separation_arcsec':float(sep[order[1]]),'gaia_neighbors_within1arcsec':n1,'gaia_neighbors_within2arcsec':n2,'gaia_neighbors_within10arcsec':n10,'unique_under_frozen_catalog_rule':unique,'motion_propagated':bool(pmok[j]),'stellar_astrometric_evidence':bool((math.isfinite(psnr)and psnr>=3)or(math.isfinite(pmsig)and pmsig>=5)),'association_eligible_before_development_exclusion':qualified,'parallax_mas':plx if math.isfinite(plx)else'','parallax_error_mas':err if math.isfinite(err)else'','parallax_snr':psnr if math.isfinite(psnr)else'','pm_joint_sigma':pmsig if math.isfinite(pmsig)else'','distance_rank_pc':1000/plx if plx>0 and math.isfinite(psnr)and psnr>=3 else'','ruwe':g['ruwe'],'duplicated_source':g['duplicated_source'],'astrometric_params_solved':g['astrometric_params_solved'],'reason_codes':';'.join(reasons)})
  if(index+1)%100==0:print('Matched',index+1,flush=True)
 # Exclude every Gaia neighbor within2arcsec of any original433 identity.
 prior_neighbors=rows(OUT.parent/'gaia_selection/ALL_NEIGHBORS.csv')
 prior_gaia={x['gaia_source_id']for x in prior_neighbors if x['within2arcsec']=='True'}
 prior_selected=rows(OUT.parent/'gaia_selection/MAIN_SELECTION.csv')
 prior_gaia|={x['matched_gaia_source_id']for x in prior_selected}
 recomputed_prior_gaia={x['gaia_source_id']for x in allneighbors if x['cohort']=='prior433_comparison_only'and x['within2arcsec']}
 prior_gaia|=recomputed_prior_gaia
 prior_coords=[(float(x['r:ra']),float(x['r:dec']),x['r:diaObjectId'])for x in prior]
 # Historical development Gaia annotations remain exclusion-only evidence.
 annpath=ACCESS/'DEVELOPMENT_OBJECT_INVENTORY.csv';annotation_ids=set()
 import re
 for r in rows(annpath):
  for value in r.values():
   for match in re.findall(r'Gaia DR3 (\d+)',value or''):annotation_ids.add(match)
 prior_gaia|=annotation_ids
 eligible=[];used={}
 for r in objects:
  if r['cohort']=='prior433_comparison_only':r.update(main_selected=False,main_exclusion_reason='INITIAL433_COMPARISON_ONLY');continue
  near=[i for a,d,i in prior_coords if float(jdsep(float(r['ra_deg']),float(r['dec_deg']),a,d))<=2]
  same=r['nearest_gaia_source_id']in prior_gaia
  reasons=[]
  if not r['association_eligible_before_development_exclusion']:reasons.append('ASSOCIATION_OR_STELLAR_GUARD_FAILED')
  if near:reasons.append('WITHIN_2_ARCSEC_OF_INITIAL433')
  if same:reasons.append('SAME_GAIA_AS_INITIAL433_OR_DEVELOPMENT_ANNOTATION')
  r.update(prior_near_ids=';'.join(near),prior_same_gaia=same,main_exclusion_reason=';'.join(reasons),main_selected=not reasons)
  if not reasons:eligible.append(r)
 for r in sorted(eligible,key=lambda x:int(x['diaObjectId'])):
  g=r['matched_gaia_source_id']
  if g in used:r.update(main_selected=False,main_exclusion_reason='DUPLICATE_EXTENSION_GAIA_KEEP_LOWEST_DIAOBJECTID',retained_counterpart_diaObjectId=used[g])
  else:used[g]=r['diaObjectId']
 selected=sorted([r for r in objects if r.get('main_selected')],key=lambda r:(r['distance_rank_pc']=='' ,float(r['distance_rank_pc'])if r['distance_rank_pc']!=''else math.inf,int(r['diaObjectId'])))
 for index,r in enumerate(selected,1):r['selection_index']=index
 assert len(selected)<=312 and len(selected)+len(prior_selected)<=500
 write('ALL104_ASSOCIATIONS.csv',[r for r in objects if r['cohort']=='extension_metadata_pool']);write('PRIOR433_RECOMPUTED_CONTEXT.csv',[r for r in objects if r['cohort']=='prior433_comparison_only']);write('ALL_NEIGHBORS.csv',allneighbors)
 write('MAIN_SELECTION.csv',selected,keys=list(dict.fromkeys(k for r in objects for k in r)))
 write('REJECTED_MAIN.csv',[r for r in objects if r['cohort']=='extension_metadata_pool'and not r['main_selected']])
 write('PRIOR_GAIA_EXCLUSION_IDS.csv',[{'gaia_source_id':x,'original433_within2arcsec':any(v['gaia_source_id']==x and v['within2arcsec']=='True'for v in prior_neighbors),'original188_selected':any(v['matched_gaia_source_id']==x for v in prior_selected),'development_historical_annotation':x in annotation_ids,'prior433_recomputed_within2arcsec':x in recomputed_prior_gaia}for x in sorted(prior_gaia,key=int)])
 summary={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'EXTENSION_METADATA_SELECTION_COMPLETE_NO_MAIN_FLUX_READ','gaia_rows':n,'rubin_metadata_objects':len(main),'prior433_comparison_context_only':len(prior),'original_development_objects':20,'original_main188_unchanged':True,'initial433_prior_objects':len(prior),'main_pool_objects':len(main),'main_selected_unique_stellar_associations':len(selected),'selected_valid_parallax_distance_ranks':sum(r['distance_rank_pc']!=''for r in selected),'selected_PM_only_or_uncertain_distance':sum(r['distance_rank_pc']==''for r in selected),'all104_unique_positional_associations':sum(r['unique_under_frozen_catalog_rule']for r in objects if r['cohort']=='extension_metadata_pool'),'all104_stellar_eligible_before_development_exclusion':sum(r['association_eligible_before_development_exclusion']for r in objects if r['cohort']=='extension_metadata_pool'),'all104_association_reason_counts':dict(Counter(x for r in objects if r['cohort']=='extension_metadata_pool'for x in r['reason_codes'].split(';')if x)),'main_exclusion_reason_counts':dict(Counter(x for r in objects if r['cohort']=='extension_metadata_pool'for x in r['main_exclusion_reason'].split(';')if x)),'prior_gaia_exclusion_ids':sorted(prior_gaia,key=int),'development_annotation_exclusion_ids':sorted(annotation_ids,key=int),'all_neighbors_rows':len(allneighbors),'coordinate_epoch_proxy':'Each cone metadata midpointMjdTai, not documented DiaObject astrometric reference epoch','warnings_from_space_motion':dict(warnings_seen),'catalog_motion_margin_arcsec':360,'largest_catalog_pm_masyr':float(np.nanmax(np.hypot(data['pmra'],data['pmdec']))),'no_claim_of_50_evaluable_objects':True,'source_hashes':{'PLAN.json':sha(OUT/'PLAN.json'),'match_gaia.py':sha(OUT/'match_gaia.py'),'GAIA_DR3_FIELD.csv':sha(OUT/'GAIA_DR3_FIELD.csv')},'limitations':plan['limitations']+['Gaia catalog association rule cannot rule out unresolved companions or uncatalogued objects.','Rubin reference epoch and its astrometric covariance are absent from input; fixed1arcsec/2arcsec guards are descriptive, not calibrated association probability.','Annual observer parallax is not applied; Gaia positions are barycentric and Rubin coordinate convention/reference epoch is not fully established.','UnknownRV uses0 and missingdistance uses angular-only propagation; noPM neighbors retain2016 coordinates as uncertainty-neighbor evidence.','Gaia catalog field completeness conditional on motion within360arcsec margin and finite catalog completeness; no exhaustive sky claim.']}
 (OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False,default=lambda value:value.item())+'\n')
 (OUT/'SELECTION_FREEZE.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FROZEN_SEPARATE_EXTENSION_METADATA_SELECTION_BEFORE_FLUX','plan_sha256':sha(OUT/'PLAN.json'),'selection_sha256':sha(OUT/'MAIN_SELECTION.csv'),'script_sha256':sha(OUT/'match_gaia.py'),'catalog_sha256':sha(OUT/'GAIA_DR3_FIELD.csv'),'selected_exact_diaObjectIds':[r['diaObjectId']for r in selected],'selected_exact_GaiaDR3sourceIds':[r['matched_gaia_source_id']for r in selected]},indent=2)+'\n')
 print(json.dumps(summary,indent=2,default=lambda value:value.item()))
if __name__=='__main__':run()
