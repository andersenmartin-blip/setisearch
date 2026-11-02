"""Scientific protocol review with metadata and synthetic guards; no requests."""
from pathlib import Path
import ast,copy,csv,datetime,hashlib,importlib.util,json,math,re,sys,textwrap
import numpy as np
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;EXT=OUT.parent;BASE=EXT.parent;ROOT=BASE.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return list(csv.DictReader(Path(p).open()))
def load(p):return json.loads(Path(p).read_text())
def segment(text,begin,end):return text[text.index(begin):text.index(end)]
def module(path):
 spec=importlib.util.spec_from_file_location('gaia_match_scientific_review',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
 plan=load(EXT/'PLAN.json');oldplan=load(BASE/'gaia_selection/PLAN.json');old=(BASE/'gaia_selection/match_gaia.py').read_text();new=(EXT/'match_gaia.py').read_text();m=module(EXT/'match_gaia.py');tests=[]
 reviewed={'PLAN.json':sha(EXT/'PLAN.json'),'match_gaia.py':sha(EXT/'match_gaia.py'),'CANDIDATE_METADATA.csv':sha(EXT/'CANDIDATE_METADATA.csv'),'original_match_gaia.py':sha(BASE/'gaia_selection/match_gaia.py')}
 def check(name,ok,detail=None):tests.append({'name':name,'pass':bool(ok),**({'detail':detail} if detail else {})})
 check('matcher_hash_matches_plan',reviewed['match_gaia.py']==plan['match_script_sha256'])
 check('all_planned_input_hashes',all(sha(ROOT/r['path'])==r['sha256'] for r in plan['input_files']))
 check('association_guards_unchanged',all(plan['association'][key]==oldplan['association'][key] for key in ['target_epoch','propagation','match_radius_arcsec','neighbor_ambiguity_radius_arcsec','neighbor_evidence_radius_arcsec','unique_rule']))
 check('stellar_rules_unchanged',plan['stellar_evidence']==oldplan['stellar_evidence'])
 check('field_radius_and_margin',plan['gaia_query']['center_deg']==oldplan['gaia_query']['center_deg'] and plan['gaia_query']['radius_deg']==1.1 and 'assert csep.max()<=3960.001' in new)
 check('proper_motion_and_covariance_block_unchanged',segment(old,' n=len(catalog);data=', ' csep=jdsep(')==segment(new,' n=len(catalog);data=', ' csep=jdsep('))
 check('neighbor_and_stellar_block_byte_identical',segment(old,' allneighbors=[];objects=[];warnings_seen=Counter()', ' # A development neighbor')==segment(new,' allneighbors=[];objects=[];warnings_seen=Counter()', ' # Exclude every Gaia neighbor'))
 check('distance_ordering_byte_identical',segment(old,' selected=sorted(', ' assert len(selected)')==segment(new,' selected=sorted(', ' assert len(selected)'))
 candidate=rows(EXT/'CANDIDATE_METADATA.csv');feasibility=rows(BASE/'extension_feasibility/OBJECT_FEASIBILITY.csv');passed=sorted([r['object_id'] for r in feasibility if r['status']=='MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION'],key=int)
 check('exact104_metadata_pass_set_order',[r['r:diaObjectId'] for r in candidate]==passed and len(candidate)==len(set(passed))==104)
 history={r['r:diaObjectId']:r for r in rows(BASE/'extension_feasibility/HISTORY_SELECTION.csv')}
 check('candidate_metadata_preserved',all(history[r['r:diaObjectId']]==r for r in candidate))
 dev=rows(BASE/'access_pilot/DEVELOPMENT_SELECTION.csv');oldmain=rows(BASE/'access_pilot/MAIN_METADATA_CANDIDATES_UNMATCHED.csv');prior=dev+oldmain;prior_ids={r['r:diaObjectId'] for r in prior};selected=rows(BASE/'gaia_selection/MAIN_SELECTION.csv');neighbors=rows(BASE/'gaia_selection/ALL_NEIGHBORS.csv')
 check('all_prior433_preserved',len(dev)==20 and len(oldmain)==413 and len(prior_ids)==433 and len(selected)==188 and {r['diaObjectId'] for r in neighbors}==prior_ids)
 check('no_exact_prior_identity_overlap',not (set(passed)&prior_ids))
 required=['work_rubin_20261102/gaia_selection/ALL_NEIGHBORS.csv','work_rubin_20261102/gaia_selection/MAIN_SELECTION.csv','work_rubin_20261102/access_pilot/DEVELOPMENT_SELECTION.csv','work_rubin_20261102/access_pilot/MAIN_METADATA_CANDIDATES_UNMATCHED.csv','work_rubin_20261102/access_pilot/DEVELOPMENT_OBJECT_INVENTORY.csv']
 check('all_exclusion_sources_frozen',set(required)<=set(r['path'] for r in plan['input_files']))
 # Execute only metadata pool initialization; no catalog, network or flux reads.
 init=segment(new," main=rows(OUT/'CANDIDATE_METADATA.csv')", " catalog=rows(OUT/'GAIA_DR3_FIELD.csv')")
 env={'rows':rows,'OUT':EXT,'ACCESS':BASE/'access_pilot'}
 try:
  exec(textwrap.dedent(init),env)
  check('metadata_pool_initialization_executes',len(env['objs'])==537 and sum(x['cohort']=='prior433_comparison_only' for x in env['objs'])==433 and sum(x['cohort']=='extension_metadata_pool' for x in env['objs'])==104)
 except Exception as exc:check('metadata_pool_initialization_executes',False,type(exc).__name__+': '+str(exc))
 # Real prior identities are metadata only. Verify source union construction executes.
 original_gaia={r['gaia_source_id'] for r in neighbors if r['within2arcsec']=='True'}
 old_selected_gaia={r['matched_gaia_source_id'] for r in selected}
 annotations={match for r in rows(BASE/'access_pilot/DEVELOPMENT_OBJECT_INVENTORY.csv') for value in r.values() for match in re.findall(r'Gaia DR3 (\d+)',value or '')}
 synthetic_recomputed='999999999999999991';synthetic_outside='999999999999999992'
 en={'rows':rows,'OUT':EXT,'ACCESS':BASE/'access_pilot','prior':prior,'allneighbors':[{'cohort':'prior433_comparison_only','gaia_source_id':synthetic_recomputed,'within2arcsec':True},{'cohort':'prior433_comparison_only','gaia_source_id':synthetic_outside,'within2arcsec':False},{'cohort':'extension_metadata_pool','gaia_source_id':'999999999999999993','within2arcsec':True}]}
 union=segment(new," prior_neighbors=rows(OUT.parent/'gaia_selection/ALL_NEIGHBORS.csv')",' eligible=[];used={}')
 exec(textwrap.dedent(union),en)
 check('union_all_original433_188_annotations_recomputed',en['prior_gaia']==original_gaia|old_selected_gaia|annotations|{synthetic_recomputed} and len(en['prior_coords'])==433)
 # Scientific boundary tests execute the actual unchanged guard statements.
 guard=textwrap.dedent(segment(new,"  plx=data['parallax'][j]",'  objects.append('))
 def qualification(label,n1=1,n2=1,pm=True,plx=3.,perr=1.,mur=0.,mud=0.,er=1.,ed=1.,rho=0.,expected=True):
  data={k:np.array([v]) for k,v in [('parallax',plx),('parallax_error',perr),('pmra',mur),('pmdec',mud),('pmra_error',er),('pmdec_error',ed),('pmra_pmdec_corr',rho)]}
  env={'data':data,'j':0,'pmok':np.array([pm]),'n1':n1,'n2':n2,'math':math}
  exec(guard,env);check('stellar_guard_'+label,env['qualified']==expected)
 qualification('parallax_exact3')
 qualification('parallax_below3',plx=math.nextafter(3.,0.),expected=False)
 qualification('pm_exact5',plx=0.,mur=5.)
 qualification('pm_below5',plx=0.,mur=math.nextafter(5.,0.),expected=False)
 qualification('pm_covariance_correlation',plx=0.,mur=3.,mud=-3.,rho=.5)
 qualification('invalid_singular_covariance',plx=0.,mur=100.,rho=1.,expected=False)
 qualification('negative_pm_uncertainty',plx=0.,mur=100.,er=-1.,expected=False)
 qualification('missing_motion',pm=False,expected=False)
 qualification('no_neighbor',n1=0,n2=0,expected=False)
 qualification('two_one_arcsec_neighbors',n1=2,n2=2,expected=False)
 qualification('second_two_arcsec_neighbor',n2=2,expected=False)
 qualification('parallax_unavailable_PM_qualifies',plx=math.nan,mur=5.)
 # Exclusion/dedup/ranking synthetic cases using the actual selection statements.
 def synthetic_obj(id_,gaia,ra=5.,dist=10.,eligible=True,cohort='extension_metadata_pool'):
  return {'diaObjectId':str(id_),'cohort':cohort,'ra_deg':ra,'dec_deg':0.,'nearest_gaia_source_id':str(gaia),'matched_gaia_source_id':str(gaia),'association_eligible_before_development_exclusion':eligible,'distance_rank_pc':dist}
 objects=[synthetic_obj(10,110,dist=20.),synthetic_obj(11,110,dist=1.),synthetic_obj(12,120),synthetic_obj(13,130,ra=1/3600),synthetic_obj(14,140,eligible=False),synthetic_obj(15,150,dist=''),synthetic_obj(16,160),synthetic_obj(17,170),synthetic_obj(18,180),synthetic_obj(19,190,cohort='prior433_comparison_only')]
 env={'objects':objects,'prior_gaia':{'120','160','170','180'},'prior_coords':[(0.,0.,'prior')],'prior_selected':[{}]*188,'jdsep':m.jdsep,'math':math}
 selection=textwrap.dedent(segment(new,' eligible=[];used={}'," write('ALL104_ASSOCIATIONS.csv'"))
 exec(selection,env);byid={r['diaObjectId']:r for r in env['objects']}
 check('synthetic_leak_exclusion_lowestID_dedup_and_rank',[r['diaObjectId'] for r in env['selected']]==['10','15'] and byid['11']['retained_counterpart_diaObjectId']=='10' and all(not byid[str(i)]['main_selected'] for i in [12,13,14,16,17,18,19]))
 check('prior_comparison_cannot_enter_extension',byid['19']['main_exclusion_reason']=='INITIAL433_COMPARISON_ONLY')
 check('caps_consistent',plan['max_additional_selected']==312 and plan['max_total_main']==500 and plan['original_main_count']==188 and 'assert len(selected)<=312 and len(selected)+len(prior_selected)<=500' in new)
 check('no_field_or_stellar_threshold_relaxation',plan['association']['match_radius_arcsec']==1 and plan['association']['neighbor_ambiguity_radius_arcsec']==2 and plan['stellar_evidence']['parallax_snr_min']==3 and plan['stellar_evidence']['pm_joint_sigma_min']==5)
 check('reviewed_files_unchanged',sha(EXT/'PLAN.json')==reviewed['PLAN.json'] and sha(EXT/'match_gaia.py')==reviewed['match_gaia.py'] and sha(EXT/'CANDIDATE_METADATA.csv')==reviewed['CANDIDATE_METADATA.csv'])
 result={'schema':'RUBIN_EXTENSION_GAIA_SCIENTIFIC_PROTOCOL_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if all(t['pass'] for t in tests) else 'FAIL','checks_passed':sum(t['pass'] for t in tests),'checks_total':len(tests),'failures':[t for t in tests if not t['pass']],'checks':tests,'reviewed_hashes':reviewed,'prior_exclusion_metadata_counts':{'initial433_objects':len(prior),'original_all_neighbor_within2_gaia_ids':len(original_gaia),'original188_selected_gaia_ids':len(old_selected_gaia),'historical_development_annotation_ids':len(annotations)},'auditor_script_sha256':sha(Path(__file__)),'network_requests':0,'new_Gaia_catalog_read':False,'Rubin_science_flux_files_read':0,'limitations':['Scientific code/protocol review with metadata and synthetic guard executions only; does not replace transport preflight or independent matching reconstruction after retrieval.','Prior433 rematching is exclusion-only; original cohort association/results remain immutable.','Same original coordinate proxy and incomplete field/motion assumptions remain. No photometric evaluability conclusion.']}
 (OUT/'PROTOCOL_AUDIT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['checks','reviewed_hashes','limitations']},indent=2))
if __name__=='__main__':main()
