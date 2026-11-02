"""Independent Gaia extension associations from exact catalog/metadata inputs.

Cartesian constant-velocity propagation and vector cross/dot distances provide an
independent check of the production spherical Astropy propagation. No flux read.
"""
from pathlib import Path
import collections,csv,datetime,hashlib,json,math,re
import numpy as np
from astropy.time import Time
from astropy.utils import iers
iers.conf.auto_download=False
OUT=Path(__file__).resolve().parent;G=OUT.parent;B=G.parent;A=B/'access_pilot'
def rows(p):return list(csv.DictReader(Path(p).open()))
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def num(x):
    try:v=float(x);return v if math.isfinite(v) else math.nan
    except (ValueError,TypeError):return math.nan
def vec(ra,dec):
    a,d=math.radians(float(ra)),math.radians(float(dec))
    return np.array([math.cos(d)*math.cos(a),math.cos(d)*math.sin(a),math.sin(d)])
def separation(target,others):return np.degrees(np.arctan2(np.linalg.norm(np.cross(others,target),axis=1),others@target))*3600
checks=0;failures=[]
def check(label,left,right):
    global checks
    checks+=1
    if left!=right:failures.append({'check':label,'expected':left,'observed':right})
def close(label,left,right,tolerance):check(label,True,math.isfinite(right) and abs(left-right)<=tolerance)

plan=read(G/'PLAN.json');pre=read(OUT/'PREFLIGHT.json')
check('Pre-reviewed plan immutable',pre['plan_sha256'],sha(G/'PLAN.json'))
check('Pre-reviewed matcher immutable',pre['match_script_sha256'],sha(G/'match_gaia.py'))
for item in plan['input_files']:check('Frozen input '+item['path'],item['sha256'],sha(B.parent/item['path']))
candidates=rows(G/'CANDIDATE_METADATA.csv');prior=rows(A/'DEVELOPMENT_SELECTION.csv')+rows(A/'MAIN_METADATA_CANDIDATES_UNMATCHED.csv')
metadata={r['r:diaObjectId']:r for r in rows(B/'extension_feasibility/HISTORY_SELECTION.csv')}
expected_ids={r['object_id'] for r in rows(B/'extension_feasibility/OBJECT_FEASIBILITY.csv') if int(r['necessary_condition_october_sources'])>0}
check('Exact104 candidate set',expected_ids,{r['r:diaObjectId'] for r in candidates});check('Candidate count',104,len(candidates))
check('Original cohort count',433,len(prior));check('No original exact IDs',set(),expected_ids&{r['r:diaObjectId'] for r in prior})
for r in candidates:
    for key in ['r:ra','r:dec','r:midpointMjdTai']:check('Candidate coordinate/epoch '+r['r:diaObjectId']+' '+key,metadata[r['r:diaObjectId']][key],r[key])
cat=rows(G/'GAIA_DR3_FIELD.csv');observed={r['diaObjectId']:r for r in rows(G/'ALL104_ASSOCIATIONS.csv')};neighbors=rows(G/'ALL_NEIGHBORS.csv');selected=rows(G/'MAIN_SELECTION.csv');summary=read(G/'SUMMARY.json');freeze=read(G/'SELECTION_FREEZE.json')
receipts=read(G/'ACQUISITION_RECEIPTS.json')
check('Gaia request attempt cap',True,1<=len(receipts)<=2)
for receipt in receipts:
    body=(G/receipt['path']).read_bytes()
    check('Attempt saved-byte hash',hashlib.sha256(body).hexdigest(),receipt['sha256'])
    check('Attempt saved-byte count',len(body),receipt['response_bytes_saved'])
    check('Attempt byte cap',True,len(body)<=8000000)
    check('Attempt charge rule',8000000 if receipt['unknown_remaining_bytes'] else len(body),receipt['charged_bytes'])
    check('Attempt frozen query',plan['gaia_query']['query_sha256'],receipt['query_sha256'])
    check('Review preceded request',True,datetime.datetime.fromisoformat(pre['reviewed_utc'])<=datetime.datetime.fromisoformat(receipt['started_utc']))
check('Total attempt byte charge cap',True,sum(r['charged_bytes'] for r in receipts)<=16000000)
check('Successful last acquisition','SUCCESS',receipts[-1]['status'])
check('Canonical catalog acquisition hash',sha(G/'GAIA_DR3_FIELD.csv'),receipts[-1]['sha256'])
check('Safe Gaia row count',True,1<len(cat)<50000)
check('Unique exact Gaia identifiers',len(cat),len({r['source_id'] for r in cat}))
check('Candidate association accounting',expected_ids,set(observed))
for r in cat:check('Exact Gaia ID '+r['source_id'],r['source_id'],str(int(r['source_id'])))
data={k:np.array([num(r[k]) for r in cat]) for k in ['ra','dec','ref_epoch','pmra','pmdec','parallax','radial_velocity']}
rad=np.radians(data['ra']);dec=np.radians(data['dec']);v=np.column_stack([np.cos(dec)*np.cos(rad),np.cos(dec)*np.sin(rad),np.sin(dec)])
check('Gaia frozen field bound',True,float(separation(vec(8.986275,-42.709834),v).max())<=3960.001)
ea=np.column_stack([-np.sin(rad),np.cos(rad),np.zeros(len(cat))]);ed=np.column_stack([-np.sin(dec)*np.cos(rad),-np.sin(dec)*np.sin(rad),np.cos(dec)])
pm=np.isfinite(data['pmra'])&np.isfinite(data['pmdec'])&np.isfinite(data['ref_epoch'])
velocity=(np.nan_to_num(data['pmra'])[:,None]*ea+np.nan_to_num(data['pmdec'])[:,None]*ed)/206264806.24709636
rvok=pm&(data['parallax']>0)&np.isfinite(data['radial_velocity']);radial=np.zeros(len(cat))
radial[rvok]=data['radial_velocity'][rvok]*31557600/(3.085677581491367e13*1000/data['parallax'][rvok])
velocity+=radial[:,None]*v;velocity[~pm]=0
def propagate(raw):
    epoch=Time(float(raw['r:midpointMjdTai']),format='mjd',scale='tai').tcb.jyear
    moved=v+np.where(pm,epoch-data['ref_epoch'],0)[:,None]*velocity
    moved/=np.linalg.norm(moved,axis=1)[:,None]
    angles=separation(vec(raw['r:ra'],raw['r:dec']),moved)
    return epoch,moved,angles,np.argsort(angles,kind='stable')
prior_old={r['gaia_source_id'] for r in rows(B/'gaia_selection/ALL_NEIGHBORS.csv') if r['within2arcsec']=='True'}
original_selected=rows(B/'gaia_selection/MAIN_SELECTION.csv')
prior_main={r['matched_gaia_source_id'] for r in original_selected}
annotations=set()
for row in rows(A/'DEVELOPMENT_OBJECT_INVENTORY.csv'):
    for value in row.values():annotations.update(re.findall(r'Gaia DR3 (\d+)',value or ''))
prior_recomputed=set();prior_by_object={}
prior_context={r['diaObjectId']:r for r in rows(G/'PRIOR433_RECOMPUTED_CONTEXT.csv')}
check('Exact prior comparison identities',{r['r:diaObjectId'] for r in prior},set(prior_context))
for raw in prior:
    epoch,moved,angles,order=propagate(raw)
    ids={cat[i]['source_id'] for i in np.flatnonzero(angles<=2)}
    prior_recomputed|=ids;prior_by_object[raw['r:diaObjectId']]=ids
    oid=raw['r:diaObjectId'];context=prior_context[oid]
    check('Prior nearest Gaia '+oid,cat[order[0]]['source_id'],context['nearest_gaia_source_id'])
    close('Prior nearest separation '+oid,float(angles[order[0]]),float(context['nearest_separation_arcsec']),.01)
    for radius in [1,2,10]:check('Prior neighbor count '+oid+' '+str(radius),int(np.sum(angles<=radius)),int(context[f'gaia_neighbors_within{radius}arcsec']))
    check('Every prior two-arcsec identity '+oid,ids,{r['gaia_source_id'] for r in neighbors if r['diaObjectId']==oid and r['within2arcsec']=='True'})
    check('Prior context excluded from new main '+oid,'False',context['main_selected'])
prior_gaia=prior_old|prior_main|annotations|prior_recomputed
check('Entire conservative prior Gaia exclusion union',prior_gaia,set(summary['prior_gaia_exclusion_ids']))
check('Historical annotation IDs',annotations,set(summary['development_annotation_exclusion_ids']))
check('Prior Gaia exclusion table',prior_gaia,{r['gaia_source_id'] for r in rows(G/'PRIOR_GAIA_EXCLUSION_IDS.csv')})
prior_vectors=np.array([vec(r['r:ra'],r['r:dec']) for r in prior])
eligible=[];max_nearest_delta=0.;max_stored_delta=0.;expected_reasons=collections.Counter()
for raw in candidates:
    oid=raw['r:diaObjectId'];r=observed[oid];epoch,moved,angles,order=propagate(raw);j=int(order[0]);g=cat[j]
    near={radius:np.flatnonzero(angles<=radius) for radius in [1,2,10]}
    check('Nearest exact Gaia ID '+oid,g['source_id'],r['nearest_gaia_source_id'])
    max_nearest_delta=max(max_nearest_delta,abs(float(r['nearest_separation_arcsec'])-angles[j]))
    close('Nearest separation '+oid,float(angles[j]),float(r['nearest_separation_arcsec']),.01)
    close('Second separation '+oid,float(angles[order[1]]),float(r['second_separation_arcsec']),.01)
    for radius in [1,2,10]:check('Neighbor count '+oid+' '+str(radius),len(near[radius]),int(r[f'gaia_neighbors_within{radius}arcsec']))
    inds=sorted(set(near[10])|set(order[:2]),key=lambda i:(angles[i],int(cat[i]['source_id'])))
    stored=[n for n in neighbors if n['diaObjectId']==oid]
    check('Stored all-neighbor identities '+oid,[cat[i]['source_id'] for i in inds],[n['gaia_source_id'] for n in stored])
    for n,i in zip(stored,inds,strict=True):
        max_stored_delta=max(max_stored_delta,abs(float(n['separation_arcsec'])-angles[i]))
        close('Neighbor separation '+oid+' '+n['gaia_source_id'],float(angles[i]),float(n['separation_arcsec']),.01)
        for radius in [1,2,10]:check('Neighbor membership '+oid+' '+n['gaia_source_id']+' '+str(radius),bool(angles[i]<=radius),n[f'within{radius}arcsec']=='True')
    plx,pe=num(g['parallax']),num(g['parallax_error']);ps=plx/pe if pe>0 else math.nan
    er,de,rho=num(g['pmra_error']),num(g['pmdec_error']),num(g['pmra_pmdec_corr']);mu=np.array([num(g['pmra']),num(g['pmdec'])]);joint=math.nan
    if pm[j] and er>0 and de>0 and math.isfinite(rho) and abs(rho)<1:
        covariance=np.array([[er*er,rho*er*de],[rho*er*de,de*de]])
        joint=math.sqrt(max(0,float(mu@np.linalg.solve(covariance,mu))))
    if math.isfinite(ps):close('Parallax SNR '+oid,ps,float(r['parallax_snr']),1e-10)
    else:check('Unavailable parallax SNR '+oid,'',r['parallax_snr'])
    if math.isfinite(joint):close('PM full covariance guard '+oid,joint,float(r['pm_joint_sigma']),1e-8)
    else:check('Unavailable PM guard '+oid,'',r['pm_joint_sigma'])
    reasons=[]
    if len(near[1])==0:reasons.append('NO_GAIA_WITHIN_1_ARCSEC')
    elif len(near[1])>1:reasons.append('MULTIPLE_GAIA_WITHIN_1_ARCSEC')
    if len(near[2])>1:reasons.append('SECOND_GAIA_WITHIN_2_ARCSEC')
    if not pm[j]:reasons.append('NEAREST_GAIA_MOTION_UNAVAILABLE')
    if not (ps>=3 or joint>=5):reasons.append('STELLAR_ASTROMETRIC_EVIDENCE_BELOW_FROZEN_GUARD')
    unique=len(near[1])==len(near[2])==1 and bool(pm[j]);good=unique and not reasons
    check('Association reasons '+oid,';'.join(reasons),r['reason_codes'])
    check('Unique positional association '+oid,unique,r['unique_under_frozen_catalog_rule']=='True')
    check('Stellar evidence '+oid,bool(ps>=3 or joint>=5),r['stellar_astrometric_evidence']=='True')
    check('Eligible before prior exclusion '+oid,good,r['association_eligible_before_development_exclusion']=='True')
    check('Exact matched Gaia '+oid,g['source_id'] if unique else '',r['matched_gaia_source_id'])
    rank=1000/plx if plx>0 and ps>=3 else None
    if rank is None:check('Uncertain-distance rank '+oid,'',r['distance_rank_pc'])
    else:close('Distance ordering proxy '+oid,rank,float(r['distance_rank_pc']),1e-8)
    near_prior=[prior[i]['r:diaObjectId'] for i,d in enumerate(separation(vec(raw['r:ra'],raw['r:dec']),prior_vectors)) if d<=2]
    same=g['source_id'] in prior_gaia
    check('Prior coordinate exclusions '+oid,';'.join(near_prior),r['prior_near_ids'])
    check('Prior Gaia exclusion '+oid,same,r['prior_same_gaia']=='True')
    expected_reasons.update(reasons)
    if good and not near_prior and not same:eligible.append((oid,g['source_id'],rank))
dedup={}
for record in sorted(eligible,key=lambda r:int(r[0])):dedup.setdefault(record[1],record)
expected=sorted(dedup.values(),key=lambda r:(r[2] is None,r[2] if r[2] is not None else math.inf,int(r[0])))
check('Extension ceiling',True,len(expected)<=312 and len(expected)+len(original_selected)<=500)
check('Exact final ranked Rubin selection',[r[0] for r in expected],[r['diaObjectId'] for r in selected])
check('Exact final ranked Gaia selection',[r[1] for r in expected],[r['matched_gaia_source_id'] for r in selected])
for oid,row in observed.items():check('Per-candidate final selected flag '+oid,oid in {r[0] for r in expected},row['main_selected']=='True')
check('Sequential ranking indices',list(range(1,len(selected)+1)),[int(r['selection_index']) for r in selected])
check('Unique selected Gaia IDs',len(selected),len({r['matched_gaia_source_id'] for r in selected}))
check('Selection has no prior Gaia identities',set(),{r['matched_gaia_source_id'] for r in selected}&prior_gaia)
check('Frozen exact Rubin IDs',[r[0] for r in expected],freeze['selected_exact_diaObjectIds'])
check('Frozen exact Gaia IDs',[r[1] for r in expected],freeze['selected_exact_GaiaDR3sourceIds'])
check('Frozen selection hash',sha(G/'MAIN_SELECTION.csv'),freeze['selection_sha256'])
check('Frozen catalog hash',sha(G/'GAIA_DR3_FIELD.csv'),freeze['catalog_sha256'])
check('Summary selected',len(expected),summary['main_selected_unique_stellar_associations'])
check('Summary association reasons',dict(expected_reasons),summary['all104_association_reason_counts'])
report={'status':'PASS_INDEPENDENT_EXTENSION_GAIA_SELECTION' if not failures else 'FAIL',
        'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'check_count':checks,'failures':failures,
        'catalog_rows':len(cat),'candidate_objects':len(candidates),'prior_objects':len(prior),
        'catalog_object_pairs':len(cat)*(len(candidates)+len(prior)),'selected_extension_objects':len(expected),
        'prior_original_neighbor_Gaia_ids':len(prior_old),'prior_recomputed_neighbor_Gaia_ids':len(prior_recomputed),
        'prior_union_Gaia_ids':len(prior_gaia),
        'maximum_independent_nearest_separation_delta_arcsec':max_nearest_delta,
        'maximum_independent_stored_neighbor_separation_delta_arcsec':max_stored_delta,
        'network_requests_made':0,'science_flux_files_read':False,
        'source_hashes':{str(p.relative_to(B)):sha(p) for p in [G/'PLAN.json',G/'match_gaia.py',G/'GAIA_DR3_FIELD.csv',G/'CANDIDATE_METADATA.csv',G/'MAIN_SELECTION.csv',G/'SELECTION_FREEZE.json',B/'gaia_selection/MAIN_SELECTION.csv']},
        'script_sha256':sha(__file__),
        'limitations':['Metadata association does not establish photometric evaluability or the minimum50 scientifically evaluable stars.',
                      'Independent Cartesian motion approximation checks this exact catalog and frozen neighbor decisions; it does not establish association probabilities or exclude unresolved/uncatalogued companions.',
                      'Rubin coordinate epoch proxy, missing observer parallax/RV, and finite catalog margin remain original limitations.']}
(OUT/'MATCHING_AUDIT.json').write_text(json.dumps(report,indent=2,default=list,allow_nan=False)+'\n')
print(json.dumps({key:report[key] for key in ['status','check_count','catalog_rows','selected_extension_objects']}))
assert not failures,failures[:5]
