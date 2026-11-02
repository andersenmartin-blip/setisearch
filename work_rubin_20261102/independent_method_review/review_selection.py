"""Independent metadata-only Gaia association/exclusion reconstruction."""
from pathlib import Path
import csv,json,math,hashlib,re,datetime
import numpy as np
from astropy.time import Time
P=Path(__file__).resolve().parent;B=P.parent;G=B/'gaia_selection';A=B/'access_pilot'
def read(p):return json.loads(p.read_text())
def rows(p):return list(csv.DictReader(p.open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def num(x):
 try:v=float(x);return v if math.isfinite(v) else math.nan
 except (ValueError,TypeError):return math.nan
def sep(ra,dec,ra2,dec2):
 da=np.radians(ra)-np.radians(ra2);d=np.radians(dec);d2=np.radians(dec2)
 z=np.sin((d-d2)/2)**2+np.cos(d)*np.cos(d2)*np.sin(da/2)**2
 return np.degrees(2*np.arctan2(np.sqrt(np.clip(z,0,1)),np.sqrt(np.clip(1-z,0,1))))*3600

def main():
 dev=rows(A/'DEVELOPMENT_SELECTION.csv');pool=rows(A/'MAIN_METADATA_CANDIDATES_UNMATCHED.csv');cat=rows(G/'GAIA_DR3_FIELD.csv');allr=rows(G/'ALL433_ASSOCIATIONS.csv');selected=rows(G/'MAIN_SELECTION.csv');neighbors=rows(G/'ALL_NEIGHBORS.csv');freeze=read(G/'SELECTION_FREEZE.json')
 assert len(dev)==20 and len(pool)==413 and len(cat)==3933 and len(allr)==433 and len(selected)==188
 dev_ids={r['r:diaObjectId'] for r in dev};pool_ids={r['r:diaObjectId'] for r in pool};assert not dev_ids&pool_ids
 for r in cat:assert str(int(r['source_id']))==r['source_id']
 for r in allr:assert str(int(r['diaObjectId']))==r['diaObjectId']
 sources={r['source_id']:r for r in cat};lookup={r['diaObjectId']:r for r in allr};assert set(lookup)==dev_ids|pool_ids
 # Independent constant Cartesian velocity propagation, including radial perspective.
 d={k:np.array([num(r[k]) for r in cat]) for k in ['ra','dec','ref_epoch','pmra','pmdec','parallax','radial_velocity']}
 rad=np.radians(d['ra']);dec=np.radians(d['dec']);v=np.column_stack([np.cos(dec)*np.cos(rad),np.cos(dec)*np.sin(rad),np.sin(dec)])
 ea=np.column_stack([-np.sin(rad),np.cos(rad),np.zeros(len(cat))]);ed=np.column_stack([-np.sin(dec)*np.cos(rad),-np.sin(dec)*np.sin(rad),np.cos(dec)])
 pm=np.isfinite(d['pmra'])&np.isfinite(d['pmdec'])&np.isfinite(d['ref_epoch']);velocity=(np.nan_to_num(d['pmra'])[:,None]*ea+np.nan_to_num(d['pmdec'])[:,None]*ed)/206264806.24709636
 rvok=pm&(d['parallax']>0)&np.isfinite(d['radial_velocity']);radial=np.zeros(len(cat));radial[rvok]=d['radial_velocity'][rvok]*31557600/(3.085677581491367e13*1000/d['parallax'][rvok]);velocity+=radial[:,None]*v;velocity[~pm]=0
 expected_dev_gaia=set();eligible=[];max_nearest_error=0.;recomputed_neighbors={}
 for raw in dev+pool:
  id_=raw['r:diaObjectId'];r=lookup[id_];epoch=Time(float(raw['r:midpointMjdTai']),format='mjd',scale='tai').tcb.jyear
  moved=v+np.where(pm,epoch-d['ref_epoch'],0)[:,None]*velocity;moved/=np.linalg.norm(moved,axis=1)[:,None]
  ar,dr=math.radians(float(raw['r:ra'])),math.radians(float(raw['r:dec']));target=np.array([math.cos(dr)*math.cos(ar),math.cos(dr)*math.sin(ar),math.sin(dr)])
  angles=np.degrees(np.arctan2(np.linalg.norm(np.cross(moved,target),axis=1),moved@target))*3600;indices=np.argsort(angles,kind='stable');j=int(indices[0]);near1=np.flatnonzero(angles<=1);near2=np.flatnonzero(angles<=2);near10=np.flatnonzero(angles<=10)
  assert r['nearest_gaia_source_id']==cat[j]['source_id'];max_nearest_error=max(max_nearest_error,abs(float(r['nearest_separation_arcsec'])-angles[j]))
  assert [len(near1),len(near2),len(near10)]==[int(r[f'gaia_neighbors_within{x}arcsec']) for x in [1,2,10]]
  expected_ids={cat[i]['source_id'] for i in set(near10)|set(indices[:2])};assert expected_ids=={n['gaia_source_id'] for n in neighbors if n['diaObjectId']==id_}
  if id_ in dev_ids:expected_dev_gaia|={cat[i]['source_id'] for i in near2}
  g=cat[j];plx,pe=num(g['parallax']),num(g['parallax_error']);ps=plx/pe if pe>0 else math.nan
  er,ed_,rho=num(g['pmra_error']),num(g['pmdec_error']),num(g['pmra_pmdec_corr']);mu1,mu2=num(g['pmra']),num(g['pmdec']);joint=math.nan
  if pm[j] and er>0 and ed_>0 and math.isfinite(rho) and abs(rho)<1:
   a,b=mu1/er,mu2/ed_;joint=math.sqrt(max(0,(a*a-2*rho*a*b+b*b)/(1-rho*rho)))
  if math.isfinite(joint):assert abs(joint-float(r['pm_joint_sigma']))<1e-10
  good=len(near1)==len(near2)==1 and pm[j] and (ps>=3 or joint>=5)
  assert bool(good)==(r['association_eligible_before_development_exclusion']=='True')
  if good and id_ in pool_ids:eligible.append(r)
 assert max_nearest_error<.01
 extra=read(G/'ADDITIONAL_INPUTS.json')
 for f in extra['files']:assert sha(B.parent/f['path'])==f['sha256']
 for r in rows(A/'DEVELOPMENT_OBJECT_INVENTORY.csv'):
  for value in r.values():expected_dev_gaia.update(re.findall(r'Gaia DR3 (\d+)',value or ''))
 assert expected_dev_gaia==set(read(G/'SUMMARY.json')['development_gaia_exclusion_ids'])
 kept=[]
 for r in eligible:
  near=[d['r:diaObjectId'] for d in dev if float(sep(float(r['ra_deg']),float(r['dec_deg']),float(d['r:ra']),float(d['r:dec'])))<=2]
  same=r['nearest_gaia_source_id'] in expected_dev_gaia
  assert ';'.join(near)==r['development_near_ids'] and str(same)==r['development_same_gaia']
  if not near and not same:kept.append(r)
 dedup={}
 for r in sorted(kept,key=lambda r:int(r['diaObjectId'])):dedup.setdefault(r['matched_gaia_source_id'],r)
 exact=sorted(dedup.values(),key=lambda r:(not bool(r['distance_rank_pc']),float(r['distance_rank_pc']) if r['distance_rank_pc'] else math.inf,int(r['diaObjectId'])))
 assert [r['diaObjectId'] for r in exact]==[r['diaObjectId'] for r in selected]==freeze['selected_exact_diaObjectIds']
 assert [r['matched_gaia_source_id'] for r in exact]==freeze['selected_exact_GaiaDR3sourceIds'];assert sha(G/'MAIN_SELECTION.csv')==freeze['selection_sha256']
 report=dict(status='PASS_INDEPENDENT_GAIA_SELECTION',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),catalog_rows=3933,metadata_objects=433,catalog_object_pairs=3933*433,development_objects=20,main_selected=188,exact_large_integer_identifiers_preserved=True,selected_unique_GaiaIDs=188,exclusion_rule_recomputed=True,stellar_PM_covariance_guard_recomputed=True,max_cartesian_vs_astropy_nearest_separation_difference_arcsec=max_nearest_error,separation_crosscheck_tolerance_arcsec=.01,source_hashes={str(p.relative_to(B)):sha(p) for p in [G/'MAIN_SELECTION.csv',G/'SELECTION_FREEZE.json',G/'GAIA_DR3_FIELD.csv',G/'PLAN.json',G/'match_gaia.py',G/'ADDITIONAL_INPUTS.json',A/'DEVELOPMENT_OBJECT_INVENTORY.csv']},no_main_photometry_read=True,limitations=['Independent Cartesian first-order propagation validates neighbor counts/nearest IDs for this exact catalog, not unresolved companions or full association probability.','Rubin coordinate-reference epoch proxy, missing observer parallax/RV and finite Gaia field remain documented selection limitations.','No claim that188 metadata-selected objects are photometrically evaluable.'],script_sha256=sha(Path(__file__)))
 (P/'GAIA_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_hashes'},indent=2))
if __name__=='__main__':main()
