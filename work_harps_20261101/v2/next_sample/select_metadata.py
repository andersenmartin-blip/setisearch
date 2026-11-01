"""Propose 100 unused metadata-selected exposures; never reads science arrays.

The original alphabetical 5000-row snapshot and quality rules are retained.
This is a reproducible proposal, not authorization or a prospective freeze.
"""
from pathlib import Path
import csv,json,hashlib,datetime,math,re,collections

OUT=Path(__file__).resolve().parent
BASE=OUT.parents[1]
CUTOFF='2026-11-01T00:00:00Z'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(s):return re.sub(r'\s+','',s).upper()
def night(r):return math.floor(float(r['t_min'])-.5)
def read(p):return list(csv.DictReader(p.open()))
def write(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def evenly_spread(rows,n):
    rows=sorted(rows,key=lambda r:(float(r['t_min']),r['dp_id']))
    if not n:return []
    if n==1:return [rows[len(rows)//2]]
    assert n<=len(rows)
    return [rows[round(i*(len(rows)-1)/(n-1))] for i in range(n)]
def choose(rows,n,prior_nights):
    by_night={}
    for r in sorted(rows,key=lambda r:(float(r['t_min']),r['dp_id'])):by_night.setdefault(night(r),r)
    fresh=[r for k,r in by_night.items() if k not in prior_nights]
    old=[r for k,r in by_night.items() if k in prior_nights]
    selected=evenly_spread(fresh,min(n,len(fresh)))
    selected+=evenly_spread(old,min(n-len(selected),len(old)))
    used={r['dp_id'] for r in selected}
    selected+=evenly_spread([r for r in rows if r['dp_id'] not in used],n-len(selected))
    return sorted(selected,key=lambda r:(float(r['t_min']),r['dp_id']))

def main():
    paths=[BASE/'access_probe/harps_post2019_metadata.csv',BASE/'selection/SELECTION.json',
           BASE/'selection/MAIN100.csv',BASE/'selection/DEVELOPMENT_AND_VALIDATION.csv',
           BASE/'v2/selection/MAIN100.csv',BASE/'v2/selection/VALIDATION4.csv',
           BASE/'acquisition/DOWNLOAD_MANIFEST.json',BASE/'v2/acquisition/DOWNLOAD_MANIFEST.json',
           BASE/'literature/UPSTREAM_REFERENCED_IDS.json',BASE/'literature/upstream_referenced_exposure_ids.json',
           BASE/'v2/code/FREEZE.json',BASE/'v2/code/CONFIG.json',BASE/'v2/code/profile_detector.py']
    selection=json.loads(paths[1].read_text());source=read(paths[0])
    assert len(source)==5000 and sha(paths[0])==selection['metadata_sha256']
    prior=sum([read(p) for p in paths[2:6]],[])
    prior_ids={r['dp_id'] for r in prior};prior_starts={(canonical(r['target_name']),float(r['t_min'])) for r in prior}
    prior_manifests=sum([json.loads(p.read_text()) for p in paths[6:8]],[])
    prior_raw={x for r in prior_manifests for x in r['raw_progenitor_ids']}
    assert len(prior)==len(prior_ids)==len(prior_starts)==209
    assert {r['dp_id'] for r in prior_manifests}==prior_ids and len(prior_raw)==209
    prior_nights=collections.defaultdict(set)
    for r in prior:prior_nights[canonical(r['target_name'])].add(night(r))
    references=json.loads(paths[8].read_text());records=json.loads(paths[9].read_text())
    upstream_adp=set(references['ADP'])|{k for k in records['records'] if k.startswith('ADP.')}
    upstream_raw=set(references['HARPS'])|{k for k in records['records'] if k.startswith('HARPS.')}
    names=sorted(selection['main_targets']);by_key={};reasons=collections.Counter();ledger=[]
    for original in source:
        r=dict(original);name=canonical(r['target_name']);reason=None
        if not re.fullmatch(r'HD\d+[AB]?',name):reason='non_HD_name'
        elif r['instrument_name']!='HARPS':reason='not_HARPS'
        elif not r['obs_release_date'] or r['obs_release_date']>CUTOFF:reason='not_public_at_cutoff'
        elif int(r['n_obs'])!=1 or r['multi_ob']!='S':reason='not_single_exposure'
        elif float(r['snr'] or 0)<50:reason='catalogue_snr_below_50'
        elif float(r['t_exptime'])<300 or float(r['t_min'])<58849:reason='time_or_exposure_cut'
        elif r['dp_id'] in upstream_adp:reason='upstream_referenced_ADP'
        elif r['dp_id'] in prior_ids or (name,float(r['t_min'])) in prior_starts:reason='previously_used_ADP_or_same_target_start'
        elif name not in names:reason='outside_original_20_main_targets'
        if reason:reasons[reason]+=1;ledger.append(dict(dp_id=r['dp_id'],target=name,reason=reason));continue
        key=(name,float(r['t_min']));r['canonical_target']=name
        if key in by_key:
            loser=min([r,by_key[key]],key=lambda z:z['dp_id']);reasons['duplicate_target_start_reprocessing']+=1
            ledger.append(dict(dp_id=loser['dp_id'],target=name,reason='duplicate_target_start_reprocessing'))
        if key not in by_key or r['dp_id']>by_key[key]['dp_id']:by_key[key]=r
    groups=collections.defaultdict(list)
    for r in by_key.values():groups[r['canonical_target']].append(r)
    allocations=dict.fromkeys(names,0)
    while sum(allocations.values())<100:
        progressed=False
        for name in names:
            if allocations[name]<len(groups[name]):allocations[name]+=1;progressed=True
            if sum(allocations.values())==100:break
        if not progressed:break
    proposed=[]
    for name in names:
        for r in choose(groups[name],allocations[name],prior_nights[name]):
            proposed.append(dict(r,role='next_main_proposed_unopened',proposal_status='METADATA_ONLY_NOT_FROZEN_OR_DOWNLOADED',source_url='https://dataportal.eso.org/dataPortal/file/'+r['dp_id']))
    assert len(proposed)==100 and len({r['dp_id'] for r in proposed})==100
    assert not ({r['dp_id'] for r in proposed}&(prior_ids|upstream_adp))
    assert not ({(r['canonical_target'],float(r['t_min'])) for r in proposed}&prior_starts)
    eligible=[r for name in names for r in sorted(groups[name],key=lambda z:(float(z['t_min']),z['dp_id']))]
    write(OUT/'ELIGIBLE_METADATA.csv',eligible);write(OUT/'EXCLUSION_LEDGER.csv',ledger);write(OUT/'PROPOSED100_METADATA.csv',proposed)
    inventory=[dict(canonical_target=name,previous_used_exposures=sum(canonical(r['target_name'])==name for r in prior),
        eligible_unused=len(groups[name]),eligible_unused_nights=len({night(r) for r in groups[name]}),
        proposed=allocations[name],proposed_nights=len({night(r) for r in proposed if r['canonical_target']==name}),
        proposed_new_nights=sum(night(r) not in prior_nights[name] for r in proposed if r['canonical_target']==name)) for name in names]
    write(OUT/'TARGET_INVENTORY.csv',inventory)
    result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PROPOSED_METADATA_ONLY_NOT_FROZEN_OR_DOWNLOADED',
        scope='Same bounded alphabetical 5000-row metadata snapshot and original20 main-target roster; no new flux or FITS data accessed.',
        input_rows=len(source),previous_used_total=209,previous_main=200,previous_development_validation=9,
        eligible_unused_main_exposures=len(eligible),eligible_targets=sum(bool(groups[n]) for n in names),
        first_failing_cut_counts=dict(reasons),exclusion_ledger_rows=len(ledger),proposed_exposures=100,
        represented_targets=sum(n>0 for n in allocations.values()),allocations=allocations,
        proposed_exposure_seconds=sum(float(r['t_exptime']) for r in proposed),
        proposed_target_night_pairs=len({(r['canonical_target'],night(r)) for r in proposed}),
        proposed_new_target_night_pairs=len({(r['canonical_target'],night(r)) for r in proposed if night(r) not in prior_nights[r['canonical_target']]}),
        estimated_download_bytes=sum(math.ceil(float(r['access_estsize'])*1024) for r in proposed),
        estimate_method='Conservative binary1024 multiplier on archive access_estsize; estimate only, not measured transferred bytes.',
        selection_rule='Original target-balanced alphabetical round robin to100, capped by available count; maximize distinct nights, prefer nights absent from all209 prior inputs, spread ranks evenly, then fill using unused exposure ranks. Latest ADP per normalized target/start retained.',
        quality_cuts=dict(instrument='HARPS',single_exposure=True,snr_min=50,t_exptime_min_seconds=300,t_min_mjd=58849,public_before_utc=CUTOFF),
        previous_adp_ids=sorted(prior_ids),previous_raw_ids=sorted(prior_raw),
        upstream_adp_count=len(upstream_adp),upstream_raw_count=len(upstream_raw),upstream_reference_commit=references['upstream_commit'],
        known_ADP_overlap=0,known_raw_overlap_status='PENDING_METADATA_PROVENANCE_QUERY',
        original_detector_and_config_unchanged=True,new_science_arrays_accessed=0,
        input_hashes={str(p.relative_to(BASE)):sha(p) for p in paths},code_sha256=sha(Path(__file__)),
        output_hashes={p.name:sha(p) for p in sorted(OUT.glob('*.csv')) if p.name in ['ELIGIBLE_METADATA.csv','EXCLUSION_LEDGER.csv','PROPOSED100_METADATA.csv','TARGET_INVENTORY.csv']},
        limitations=['The bounded alphabetical snapshot is not representative of the whole HARPS archive.',
                    'No match to the pinned reference ADP/raw-ID inventory is not proof these exposures have never been searched.',
                    'Only16-20 of the existing20 targets may have unused data; no new targets substituted.',
                    'Internal header target/coordinate, BERV, unit, release and raw-identity checks remain mandatory after any approved acquisition.',
                    'This is a prepared proposal. Root must assess current followup workload and freeze selection/method before new flux access.'])
    assert sum(reasons.values())+len(eligible)==len(source)
    (OUT/'PROPOSAL.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['eligible_unused_main_exposures','eligible_targets','proposed_exposures','represented_targets','allocations','proposed_exposure_seconds','estimated_download_bytes','proposed_new_target_night_pairs']},indent=2))

if __name__=='__main__':main()
