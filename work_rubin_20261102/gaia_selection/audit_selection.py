"""Separate vector propagation and exhaustive selection/integrity checks.
No imports of matcher; no network and no Rubin flux reads.
"""
from pathlib import Path
import csv,json,math,hashlib,datetime
from collections import Counter
import numpy as np
from astropy.time import Time
P=Path(__file__).resolve().parent
A=P.parent/'access_pilot'
def rows(p):return list(csv.DictReader(p.open()))
def num(x):
 try:y=float(x);return y if math.isfinite(y)else math.nan
 except:return math.nan
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def angular(v,u):return np.rad2deg(np.arctan2(np.linalg.norm(np.cross(v,u),axis=-1),np.sum(v*u,axis=-1)))*3600

def run():
 g=rows(P/'GAIA_DR3_FIELD.csv');o=rows(P/'ALL433_ASSOCIATIONS.csv');s=rows(P/'MAIN_SELECTION.csv');n=rows(P/'ALL_NEIGHBORS.csv')
 orig=rows(A/'DEVELOPMENT_SELECTION.csv')+rows(A/'MAIN_METADATA_CANDIDATES_UNMATCHED.csv')
 assert len(o)==433 and set(x['diaObjectId']for x in o)==set(x['r:diaObjectId']for x in orig)
 assert len({x['source_id']for x in g})==len(g)==3933
 for x in o:assert str(int(x['diaObjectId']))==x['diaObjectId']
 for x in g:assert str(int(x['source_id']))==x['source_id']
 src={x['source_id']:i for i,x in enumerate(g)}
 gv={k:np.array([num(x[k])for x in g])for k in ['ra','dec','pmra','pmdec','ref_epoch','parallax','radial_velocity']}
 a,d=np.deg2rad(gv['ra']),np.deg2rad(gv['dec'])
 xyz=np.array([np.cos(d)*np.cos(a),np.cos(d)*np.sin(a),np.sin(d)]).T
 ea=np.array([-np.sin(a),np.cos(a),np.zeros(len(a))]).T
 ed=np.array([-np.sin(d)*np.cos(a),-np.sin(d)*np.sin(a),np.cos(d)]).T
 finite=np.isfinite(gv['pmra'])&np.isfinite(gv['pmdec'])&np.isfinite(gv['ref_epoch'])
 rate=(np.nan_to_num(gv['pmra'])[:,None]*ea+np.nan_to_num(gv['pmdec'])[:,None]*ed)/206264806.24709636
 distok=(gv['parallax']>0)&np.isfinite(gv['radial_velocity'])&finite
 radial=np.zeros(len(g));radial[distok]=gv['radial_velocity'][distok]*(31557600/3.085677581491367e13)/(1000/gv['parallax'][distok])
 rate+=radial[:,None]*xyz;rate[~finite]=0
 stored_by={}
 for x in n:stored_by.setdefault(x['diaObjectId'],[]).append(x)
 maxerr=0;threshold_disagreements=[];records=0
 for r in o:
  epoch=float(Time(float(r['coordinate_reference_mjd_tai_proxy']),format='mjd',scale='tai').tcb.jyear)
  dt=np.where(finite,epoch-gv['ref_epoch'],0)
  moved=xyz+dt[:,None]*rate;moved/=np.linalg.norm(moved,axis=1)[:,None]
  ar,dr=math.radians(float(r['ra_deg'])),math.radians(float(r['dec_deg']))
  target=np.array([math.cos(dr)*math.cos(ar),math.cos(dr)*math.sin(ar),math.sin(dr)])
  sep=angular(moved,target);j=int(np.argmin(sep))
  assert g[j]['source_id']==r['nearest_gaia_source_id']
  for limit,key in [(1,'gaia_neighbors_within1arcsec'),(2,'gaia_neighbors_within2arcsec'),(10,'gaia_neighbors_within10arcsec')]:
   if int(np.sum(sep<=limit))!=int(r[key]):threshold_disagreements.append([r['diaObjectId'],limit,int(np.sum(sep<=limit)),r[key]])
  expected={g[i]['source_id']for i in np.where(sep<=10)[0]}|{g[i]['source_id']for i in np.argsort(sep)[:2]}
  assert expected=={x['gaia_source_id']for x in stored_by[r['diaObjectId']]}
  for x in stored_by[r['diaObjectId']]:
   i=src[x['gaia_source_id']];e=abs(float(sep[i])-float(x['separation_arcsec']));maxerr=max(e,maxerr);records+=1
  p=num(r['parallax_mas']);ep=num(r['parallax_error_mas']);snr=p/ep if ep>0 and math.isfinite(p)else math.nan
  isstar=snr>=3 or num(r['pm_joint_sigma'])>=5
  unique=int(r['gaia_neighbors_within1arcsec'])==1 and int(r['gaia_neighbors_within2arcsec'])==1 and r['motion_propagated']=='True'
  assert str(unique)==r['unique_under_frozen_catalog_rule']
  assert str(bool(isstar and unique))==r['association_eligible_before_development_exclusion']
 assert not threshold_disagreements,threshold_disagreements
 assert maxerr<0.01,maxerr # Prospective tolerance before this audit:10mas for first-order approximation vsERFA light-time propagation.
 assert len(s)==188
 assert len({x['matched_gaia_source_id']for x in s})==len(s)
 assert all(x['cohort']=='main_metadata_pool'and x['main_selected']=='True'and x['development_near_ids']==''and x['development_same_gaia']=='False' for x in s)
 key=lambda r:(r['distance_rank_pc']=='',float(r['distance_rank_pc'])if r['distance_rank_pc']else math.inf,int(r['diaObjectId']))
 assert s==sorted(s,key=key)
 assert [int(x['selection_index'])for x in s]==list(range(1,len(s)+1))
 assert {x['diaObjectId']for x in s}=={x['diaObjectId']for x in o if x['main_selected']=='True'}
 freeze=json.loads((P/'SELECTION_FREEZE.json').read_text());assert freeze['selection_sha256']==sha(P/'MAIN_SELECTION.csv')
 assert freeze['selected_exact_diaObjectIds']==[x['diaObjectId']for x in s]
 assert freeze['selected_exact_GaiaDR3sourceIds']==[x['matched_gaia_source_id']for x in s]
 report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_SEPARATE_NUMERICAL_AND_SELECTION_CHECK','all433_coverage':True,'catalog_rows':len(g),'catalog_pairs_recomputed':len(g)*len(o),'neighbor_records_checked':records,'max_approximation_vs_erfa_separation_error_arcsec':maxerr,'tolerance_arcsec':0.01,'threshold_disagreements':threshold_disagreements,'selected_unique_objects':len(s),'exact64bit_IDs_preserved':True,'selection_hash_and_order_match':True,'scope':'Separate script with Cartesian linear propagation+radial perspective and atan2 angular separation, no matcher imports; same agent, not external independent reviewer. First-order propagation check does not validate astrophysical association or all systematics.','no_Rubin_flux_read':True,'script_sha256':sha(P/'audit_selection.py')}
 (P/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':run()
