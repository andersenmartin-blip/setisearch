"""Independent metadata-only reconstruction of the HARPS continuation baseline."""
from pathlib import Path
import collections,csv,datetime,hashlib,json
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
OLD=ROOT/'work_harps_20261101';EXT=OLD/'v2/extension02';H=EXT/'next_followup_20261102'
def read(path):return json.loads(path.read_text())
def rows(path):return list(csv.DictReader(path.open()))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
checks=[]
def check(label,condition):
    assert condition,label
    checks.append(label)

handoff=read(H/'HANDOFF.json');sourcehashes=read(H/'SOURCE_HASHES.json')
for name,record in sourcehashes.items():
    check('Handoff source hash '+name,sha(ROOT/name)==record['sha256'])
    check('Handoff source bytes '+name,(ROOT/name).stat().st_size==record['bytes'])
preservation=read(H/'PRESERVATION_CHECK.json');current=rows(OLD/'v2/CURRENT_V2_DISPOSITIONS.csv')
codes={r['review_id']:r['current_code'] for r in current};counts=dict(collections.Counter(codes.values()))
check('669 distinct current labels',len(current)==len(codes)==669)
check('Current global counts preserved',counts=={'U':185,'A':403,'O':46,'M':35}==handoff['preserved_current_counts']==preservation['all669_counts'])
expected={'HD122640':['V2E2-0229','V2E2-0231','V2E2-0234','V2E2-0235','V2E2-0236','V2E2-0237'],
          'HD135204':['V2E2-0303','V2E2-0305','V2E2-0308','V2E2-0309']}
queue=[r for r in rows(EXT/'unresolved_context_20261102/ACTION_QUEUE.csv') if r['primary_evidence_route']=='FRAME_BASELINE_CONTEXT']
check('Exact10 frame queue IDs',{t:[r['candidate_id'] for r in queue if r['target']==t] for t in expected}==expected==handoff['queue_ids_by_target'])
check('All10 current U labels',len(queue)==10 and all(codes[r['candidate_id']]=='U' and r['current_code_unchanged']=='U' for r in queue))
check('Event namespace preserved','V2-0231' not in {r['candidate_id'] for r in queue} and codes['V2E2-0231']=='U')
manifests=[('initial100',OLD/'acquisition/DOWNLOAD_MANIFEST.json','main_unopened'),
           ('v2_first100',OLD/'v2/acquisition/DOWNLOAD_MANIFEST.json','v2_main_unopened'),
           ('extension02',EXT/'acquisition/DOWNLOAD_MANIFEST.json','extension02_unopened')]
allmain=[]
for cohort,path,role in manifests:
    selected=[r for r in read(path) if r['role']==role]
    check('Exactly100 main epochs '+cohort,len(selected)==100)
    for r in selected:
        check('One exact raw progenitor '+r['dp_id'],len(r['raw_progenitor_ids'])==1)
        allmain.append({**r,'cohort':cohort})
dpids=sorted(r['dp_id'] for r in allmain);rawids=sorted(x for r in allmain for x in r['raw_progenitor_ids'])
check('Distinct300 exact DP IDs',len(dpids)==len(set(dpids))==300)
check('Distinct300 exact raw IDs',len(rawids)==len(set(rawids))==300)
inventory=rows(H/'EXISTING_TARGET_EXPOSURES.csv');coverage=rows(H/'BERV_COVERAGE.csv');targets={}
check('Exactly29 recorded target epochs',len(inventory)==29)
nominal=299792.458/115000
for target in expected:
    selected=[r for r in allmain if r['canonical_target']==target]
    check('Exact target epoch identities '+target,{r['dp_id'] for r in selected}=={r['dp_id'] for r in inventory if r['target']==target})
    berv=[r['primary_header']['HIERARCH ESO DRS BERV'] for r in selected]
    targets[target]={'epochs':len(selected),'cohort_counts':dict(collections.Counter(r['cohort'] for r in selected)),
                     'berv_min_km_s':min(berv),'berv_max_km_s':max(berv),'berv_span_km_s':max(berv)-min(berv),
                     'span_resolution_elements':(max(berv)-min(berv))/nominal,
                     'dates_utc':sorted({r['primary_header']['DATE-OBS'] for r in selected})}
    check('Target epoch count '+target,len(selected)=={'HD122640':14,'HD135204':15}[target])
    check('Sub-resolution BERV span '+target,max(berv)-min(berv)<nominal)
    for scope in ['extension02_only','earlier200_only','all_existing300']:
        subset=[r for r in selected if scope=='all_existing300' or (r['cohort']=='extension02')==(scope=='extension02_only')]
        bs=[r['primary_header']['HIERARCH ESO DRS BERV'] for r in subset]
        data=next(r for r in handoff['coverage'] if r['target']==target and r['scope']==scope)
        table=next(r for r in coverage if r['target']==target and r['scope']==scope)
        for key,value in [('exposures',len(subset)),('berv_min_km_s',min(bs)),('berv_max_km_s',max(bs)),('berv_span_km_s',max(bs)-min(bs)),('nominal_resolution_km_s',nominal),('span_resolution_elements',(max(bs)-min(bs))/nominal)]:
            check('Handoff coverage '+target+' '+scope+' '+key,abs(float(data[key])-value)<1e-12 and abs(float(table[key])-value)<1e-12)
extras=[r for r in rows(OLD/'expansion/EXTRA_ELIGIBLE_METADATA.csv') if r['canonical_target'] in expected]
check('19 existing extra rows already used',len(extras)==19 and all(r['dp_id'] in set(dpids) for r in extras))
for path,digest in read(H/'PROVENANCE_REFRESH.json')['stable_file_hashes_before_and_after'].items():check('Stable handoff provenance '+path,sha(H/path)==digest)
report={'status':'PASS_INDEPENDENT_HANDOFF_STATE_BASELINE','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'baseline_git_head':'cfc0aa5146237ab82db183008ce8b162ad37c71a','checks_passed':len(checks),'checks':checks,
        'global_current_counts':counts,'exact_frame_queue_ids_by_target':expected,'targets':targets,'nominal_c_over_R_km_s':nominal,
        'existing_main_dp_ids_to_exclude':dpids,'existing_main_raw_ids_to_exclude':rawids,
        'science_arrays_read':0,'network_requests':0,'labels_changed':0,
        'scope':'Review and reproduction of saved metadata and current labels only. No new target search or spectrum read.',
        'source_hashes':{str(path.relative_to(ROOT)):sha(path) for path in [H/'HANDOFF.json',H/'SOURCE_HASHES.json',H/'PROVENANCE_REFRESH.json',H/'EXISTING_TARGET_EXPOSURES.csv',H/'FRAME_BASELINE_QUEUE.csv',OLD/'v2/CURRENT_V2_DISPOSITIONS.csv']},
        'auditor_script_sha256':sha(Path(__file__)),
        'limitations':['Existing inventory exhaustion refers only to the saved19extra rows, not the ESO archive.',
                      'Current BERV spans below c/R are descriptive planning context; no new photon-origin classification or statistical-power conclusion.',
                      'Product hashes in acquisition manifests are saved metadata claims, not fresh checks of binary arrays.']}
(OUT/'STATE_BASELINE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'checks_passed':len(checks),'targets':{t:r['epochs'] for t,r in targets.items()},'distinct_DP':len(set(dpids)),'distinct_raw':len(set(rawids))}))
