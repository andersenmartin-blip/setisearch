#!/usr/bin/env python3
"""Independent stdlib audit; imports no production/project analysis module."""
import csv,hashlib,itertools,json,math,statistics,datetime
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
REPO=BASE.parents[3]
checks=[]
failures=[]
def check(name,condition,detail=None):
    checks.append({'name':name,'passed':bool(condition),**({'detail':detail} if detail is not None else {})})
    if not condition:failures.append(name)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def readcsv(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def f(x):
    try:v=float(x)
    except (ValueError,TypeError):return None
    return v if math.isfinite(v) else None
def eq(a,b):
    aa,bb=f(a),f(b)
    return aa is None and bb is None or aa is not None and bb is not None and math.isclose(aa,bb,rel_tol=2e-12,abs_tol=2e-12)
def b(x):
    if x not in ('True','False'):raise ValueError(x)
    return x=='True'
def numcheck(name,a,z):check(name,eq(a,z),None if eq(a,z) else [a,z])
def quantile(values,q):
    s=sorted(values);t=(len(s)-1)*q;lo=int(t);hi=min(lo+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(t-lo)
plan=json.loads((BASE/'PLAN.json').read_text())
freeze=json.loads((BASE/'FREEZE.json').read_text())
summary=json.loads((BASE/'SUMMARY.json').read_text())
check('plan freeze SHA256',digest(BASE/'PLAN.json')==freeze['plan_sha256'])
check('script freeze SHA256',digest(BASE/'build_context.py')==freeze['script_sha256'])
sources={}
source_status=[]
for source in plan['source_files']:
    p=BASE/source['snapshot_path']
    check('snapshot '+p.name,digest(p)==source['sha256'] and p.stat().st_size==source['bytes'])
    original=REPO/source['source_path']
    source_status.append({'path':source['source_path'],'present':original.exists(),'unchanged_at_audit':original.exists() and digest(original)==source['sha256']})
    sources[source['source_path'].split('extension02/',1)[1]]=p
for name,info in json.loads((BASE/'OUTPUT_HASHES.json').read_text()).items():
    check('output digest '+name,digest(BASE/name)==info['sha256'] and (BASE/name).stat().st_size==info['bytes'])
current=readcsv(sources['raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv'])
chosen=[r for r in current if r['current_code']=='U']
ids=[r['candidate_id'] for r in chosen]
check('exhaustive frozen90',len(ids)==90 and ids==plan['scope']['selected_ids'] and len(set(ids))==90)
cat={r['candidate_id']:r for r in readcsv(sources['production/V2_HITS.csv'])}
epoch={r['candidate_id']:r for r in readcsv(sources['epoch_followup/EVENT_SUMMARY.csv'])}
all_measure=readcsv(sources['epoch_followup/ALL_EPOCH_MEASUREMENTS.csv'])
measure={cid:[r for r in all_measure if r['candidate_id']==cid] for cid in ids}
events=readcsv(BASE/'EVENT_CONTEXT.csv');byid={r['candidate_id']:r for r in events}
check('event coverage order',len(events)==90 and [r['candidate_id'] for r in events]==ids)
expected_selected=sum((measure[cid] for cid in ids),[])
check('existing measurement rows exact',readcsv(BASE/'SELECTED_EXISTING_EPOCH_MEASUREMENTS.csv')==expected_selected)
expected_low={};expected_small={};source_byid={r['candidate_id']:r for r in chosen}
for cid in ids:
    d,c,e,o=source_byid[cid],cat[cid],epoch[cid],byid[cid]
    check(cid+' identity',d['dp_id']==c['dp_id']==e['source_dp_id']==o['dp_id'] and d['target']==c['canonical_target']==e['target']==o['target'] and d['source_input_sha256']==c['input_sha256']==o['source_input_sha256'])
    check(cid+' unchanged U and no width inference',o['current_code_unchanged']=='U' and o['width_is_measured']=='False')
    check(cid+' evidence exact',o['raw_evidence']==d['current_evidence'] and o['raw_evidence_table']==d['current_evidence_table'])
    numcheck(cid+' center',o['center_bary_air_angstrom'],c['fitted_center_angstrom'])
    numcheck(cid+' epoch center',o['center_bary_air_angstrom'],e['fitted_center_bary_air_angstrom'])
    numcheck(cid+' nominal width',o['nominal_resolution_angstrom'],float(c['fitted_center_angstrom'])/115000)
    numcheck(cid+' historical template width',o['production_fixed_template_fwhm_angstrom'],c['fwhm_model_angstrom'])
    numcheck(cid+' selection index',o['selection_index'],d['selection_index'])
    numcheck(cid+' other epoch count',o['other_epochs'],e['other_epochs'])
    numcheck(cid+' stored BERV span',o['berv_span_km_s'],e['berv_span_km_s'])
    numcheck(cid+' stored BERV span nominal units',o['berv_span_resolution_elements'],e['berv_span_resolution_elements'])
    numcheck(cid+' stored correlation delta',o['median_correlation_bary_minus_topo'],e['median_correlation_bary_minus_topo'])
    values=[float(r['berv_km_s']) for r in measure[cid]]
    span=max(values)-min(values)
    numcheck(cid+' independently computed BERV span',o['berv_span_km_s'],span)
    numcheck(cid+' independently computed nominal BERV span',o['berv_span_resolution_elements'],span/(299792.458/115000))
    expected_small[cid]=span<(299792.458/115000)
    check(cid+' low frame span flag',b(o['frame_span_below_one_resolution_element'])==expected_small[cid]==b(e['frame_separation_below_one_resolution_element']))
    low=False
    for frame in ('barycentric','topocentric'):
        part=[r for r in measure[cid] if r['frame']==frame]
        disc=[r for r in part if b(r['is_discovery_exposure'])]
        others=[r for r in part if not b(r['is_discovery_exposure'])]
        check(cid+frame+' discovery and other coverage',len(disc)==1 and disc[0]['dp_id']==d['dp_id'] and len(others)==int(e['other_epochs']) and len(set(r['dp_id'] for r in part))==len(part))
        dr=disc[0]
        lows=sum(b(r['local_continuum_low']) for r in others)
        low|=bool(lows) or b(dr['local_continuum_low'])
        check(cid+frame+' low continuum flags',b(o[frame+'_discovery_low_continuum'])==b(dr['local_continuum_low']) and int(o[frame+'_other_low_continuum_count'])==lows==int(e[frame+'_other_low_continuum_count']))
        for col in ('normalization_adu','first_difference_noise_proxy_adu','narrow_amplitude','narrow_residual_rms','broad3_amplitude','broad3_residual_rms'):
            numcheck(cid+frame+' discovery '+col,o[frame+'_discovery_'+col],dr[col])
        corr=[f(r['correlation_to_discovery']) for r in others if f(r['correlation_to_discovery']) is not None]
        for suffix,q in [('median',0.5),('q25',0.25),('q75',0.75)]:
            numcheck(cid+frame+' copied correlation '+suffix,o[frame+'_other_correlation_'+suffix],e[frame+'_other_correlation_to_discovery_'+suffix])
            numcheck(cid+frame+' recomputed correlation '+suffix,o[frame+'_other_correlation_'+suffix],quantile(corr,q) if corr else None)
        amplitudes=[f(r['narrow_amplitude']) for r in others if f(r['narrow_amplitude']) is not None]
        numcheck(cid+frame+' copied narrow amplitude median',o[frame+'_other_narrow_amplitude_median'],e[frame+'_other_narrow_amplitude_median'])
        numcheck(cid+frame+' recomputed narrow amplitude median',o[frame+'_other_narrow_amplitude_median'],statistics.median(amplitudes) if amplitudes else None)
        dn,db=f(dr['narrow_residual_rms']),f(dr['broad3_residual_rms'])
        ratio=db/dn if db is not None and dn is not None and dn>0 else None
        numcheck(cid+frame+' discovery RMS ratio',o[frame+'_discovery_broad3_to_narrow_rms'],ratio)
        ratios=[float(r['broad3_residual_rms'])/float(r['narrow_residual_rms']) for r in others if f(r['broad3_residual_rms']) is not None and f(r['narrow_residual_rms']) is not None and float(r['narrow_residual_rms'])>0]
        numcheck(cid+frame+' other RMS median',o[frame+'_other_broad3_to_narrow_rms_median'],statistics.median(ratios) if ratios else None)
        check(cid+frame+' other RMS count',int(o[frame+'_other_broad3_to_narrow_rms_n'])==len(ratios))
    expected_low[cid]=low
    check(cid+' any low continuum',b(o['any_low_continuum_context'])==low)
# Independently build graph partitions using disjoint-set unions.
expected_groups={}
for kind,prefix,stem in [('resolution','R','RESOLUTION'),('core','C','CORE_OVERLAP')]:
    roots={cid:cid for cid in ids}
    def root(cid):
        while roots[cid]!=cid:cid=roots[cid]
        return cid
    edges={}
    for a,z in itertools.combinations(ids,2):
        if cat[a]['canonical_target']!=cat[z]['canonical_target']:continue
        wa,wz=float(cat[a]['fitted_center_angstrom']),float(cat[z]['fitted_center_angstrom'])
        delta=abs(wa-wz);scale=(wa+wz)/230000;limit=scale if kind=='resolution' else .5
        if delta<=limit:
            edges[(a,z)]=(delta,scale,limit)
            roots[root(z)]=root(a)
    groups={}
    for cid in ids:groups.setdefault(root(cid),[]).append(cid)
    ordered=sorted(groups.values(),key=lambda members:(cat[members[0]]['canonical_target'],min(float(cat[c]['fitted_center_angstrom']) for c in members),min(members)))
    stored_edges=readcsv(BASE/(stem+'_PAIR_EDGES.csv'))
    check(kind+' all pair edges unique complete',len(stored_edges)==len(edges) and {(r['candidate_a'],r['candidate_b']) for r in stored_edges}==set(edges))
    for row in stored_edges:
        a,z=row['candidate_a'],row['candidate_b'];delta,scale,limit=edges[(a,z)]
        numcheck(kind+a+z+' delta',row['separation_angstrom'],delta)
        numcheck(kind+a+z+' normalized delta',row['separation_nominal_resolution_elements'],delta/scale)
        numcheck(kind+a+z+' edge threshold',row['edge_limit_angstrom'],limit)
        check(kind+a+z+' edge target/exposure',row['target']==cat[a]['canonical_target'] and b(row['same_source_exposure'])==(cat[a]['dp_id']==cat[z]['dp_id']))
    stored_groups=readcsv(BASE/(stem+'_GROUPS.csv'))
    check(kind+' all groups coverage',len(stored_groups)==len(ordered))
    expected_groups[kind]={}
    for n,(members,row) in enumerate(zip(ordered,stored_groups),1):
        gid=f'{prefix}{n:03d}';members=sorted(members)
        for cid in members:expected_groups[kind][cid]=(gid,len(members))
        check(gid+' exact ordered members',row['group_id']==gid and row['member_ids'].split('|')==members and int(row['events'])==len(members))
        check(gid+' target and exposures',row['target']==cat[members[0]]['canonical_target'] and int(row['distinct_source_exposures'])==len({cat[c]['dp_id'] for c in members}))
        waves=[float(cat[c]['fitted_center_angstrom']) for c in members];lo,hi=min(waves),max(waves);span=hi-lo;scale=(lo+hi)/230000
        for key,val in [('minimum_center_bary_air_angstrom',lo),('maximum_center_bary_air_angstrom',hi),('center_span_angstrom',span),('center_span_nominal_resolution_elements',span/scale)]:numcheck(gid+key,row[key],val)
        check(gid+' chain flag',b(row['endpoint_span_exceeds_one_edge'])==(span>(scale if kind=='resolution' else .5)))
        check(gid+' any low flag',b(row['any_low_continuum_context'])==any(expected_low[c] for c in members))
        check(gid+' homogeneous frame baseline',len({expected_small[c] for c in members})==1 and b(row['frame_span_below_one_resolution_element'])==expected_small[members[0]])
        spans={float(epoch[c]['berv_span_km_s']) for c in members};check(gid+' homogeneous BERV span',len(spans)==1);numcheck(gid+' BERV span',row['berv_span_km_s'],next(iter(spans)))
        for frame in ('barycentric','topocentric'):
            vals=[f(epoch[c][frame+'_other_correlation_to_discovery_median']) for c in members];vals=[v for v in vals if v is not None]
            numcheck(gid+frame+' correlation min',row[frame+'_event_median_correlation_min'],min(vals) if vals else None)
            numcheck(gid+frame+' correlation max',row[frame+'_event_median_correlation_max'],max(vals) if vals else None)
    for cid in ids:
        gid,count=expected_groups[kind][cid];field='resolution' if kind=='resolution' else 'core_overlap'
        check(cid+kind+' assigned group',byid[cid][field+'_group']==gid and int(byid[cid][field+'_group_events'])==count)
actions=readcsv(BASE/'ACTION_QUEUE.csv')
check('action coverage and order',[r['candidate_id'] for r in actions]==ids)
expected_routes=[]
for n,row in enumerate(actions,1):
    cid=row['candidate_id'];o=byid[cid]
    if expected_low[cid]:route,index='NORMALIZATION_CONTEXT',0
    elif expected_small[cid]:route,index='FRAME_BASELINE_CONTEXT',1
    elif expected_groups['core'][cid][1]>1:route,index='JOINT_PROFILE_CONTEXT',2
    else:route,index='INDIVIDUAL_PROFILE_CONTEXT',3
    expected_routes.append(route)
    check(cid+' action',int(row['queue_index'])==n and row['current_code_unchanged']=='U' and row['target']==cat[cid]['canonical_target'] and row['dp_id']==cat[cid]['dp_id'] and row['primary_evidence_route']==route==o['primary_evidence_route'] and row['next_evidence_needed']==plan['work_queues']['next_evidence'][index])
    check(cid+' action flags/groups',b(row['any_low_continuum_context'])==expected_low[cid] and b(row['frame_span_below_one_resolution_element'])==expected_small[cid] and row['resolution_group']==expected_groups['resolution'][cid][0] and row['core_overlap_group']==expected_groups['core'][cid][0])
for key,val in [('selected_events',90),('selected_targets',len({cat[c]['canonical_target'] for c in ids})),('selected_discovery_exposures',len({cat[c]['dp_id'] for c in ids})),('existing_epoch_measurement_rows_reused',len(expected_selected)),('existing_other_epoch_measurement_rows_reused',sum(not b(r['is_discovery_exposure']) for r in expected_selected)),('existing_distinct_comparison_exposures',len({r['dp_id'] for r in expected_selected})),('resolution_groups',len(set(v[0] for v in expected_groups['resolution'].values()))),('core_overlap_groups',len(set(v[0] for v in expected_groups['core'].values())))]:check('summary '+key,summary[key]==val)
for kind,stem in [('resolution','RESOLUTION'),('core_overlap','CORE_OVERLAP')]:
    groups=readcsv(BASE/(stem+'_GROUPS.csv'));edges=readcsv(BASE/(stem+'_PAIR_EDGES.csv'))
    for key,value in [(kind+'_multi_event_groups',sum(int(r['events'])>1 for r in groups)),(kind+'_group_singletons',sum(int(r['events'])==1 for r in groups)),(kind+'_groups_with_chain_span',sum(b(r['endpoint_span_exceeds_one_edge']) for r in groups)),(kind+'_edges',len(edges))]:check('summary '+key,summary[key]==value)
check('summary routes',summary['primary_evidence_routes']==dict(Counter(expected_routes)))
check('summary target counts',summary['per_target_events']==dict(Counter(cat[c]['canonical_target'] for c in ids)))
check('summary low IDs',summary['events_with_any_low_continuum_context']==[c for c in ids if expected_low[c]])
check('summary small-span IDs',summary['events_with_frame_span_below_one_resolution_element']==[c for c in ids if expected_small[c]])
check('no changes/new measurements',all(summary[k]==0 for k in ('changed_classifications','new_observations','new_flux_measurements')))
check('plan interpretation constraints','not an estimated or fitted line width' in plan['resolution']['width_angstrom'] and 'never counts of independent physical sources' in plan['grouping']['construction'] and 'not likelihood or a scientific classifier' in plan['work_queues']['limitations'])
report={'schema':'HARPS_UNRESOLVED_INDEPENDENT_CONTEXT_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not failures else 'FAIL','checks':len(checks),'failed_checks':failures,'scope':{'events':len(ids),'targets':len({cat[c]['canonical_target'] for c in ids}),'source_snapshots':len(sources),'existing_measurement_rows_checked':len(expected_selected),'pixel_array_reads':0,'project_modules_imported':0},'independence':'Separate stdlib implementation; uses disjoint-set graph reconstruction, scalar joins and quantile/RMS reaggregation from preserved tables. Not independent data, external peer review or physical-origin validation.','scientific_cautions':['Fixed catalog FWHM and nominal lambda/R are templates/scales, never measured intrinsic widths.','Graph components describe positional proximity/window dependence and cannot count independent physical sources.','Multiple events share discovery/comparison spectra; event-row correlations and residual RMS are not significance or origin probabilities.','Low-continuum flags and short BERV spans remain explicit. Nonflagged cases are not validated.','All current U labels are preserved in these outputs; this audit is of the frozen batch04 source snapshot.'],'source_file_status_at_audit':source_status,'input_hashes':{p.name:digest(p) for p in BASE.glob('*.csv')},'plan_sha256':digest(BASE/'PLAN.json'),'summary_sha256':digest(BASE/'SUMMARY.json'),'audit_script_sha256':digest(Path(__file__)),'check_details':checks}
(HERE/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('check_details','input_hashes')},indent=2))
raise SystemExit(bool(failures))
