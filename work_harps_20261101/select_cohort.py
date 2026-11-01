"""Metadata-only selection; never opens scientific arrays."""
import csv, json, re, math, hashlib
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

P=Path(__file__).resolve().parent
norm=lambda s: re.sub(r'\s+','',s).upper()
source=P/'access_probe/harps_post2019_metadata.csv'
refs_path=P/'literature/upstream_referenced_exposure_ids.json'
refs=json.loads(refs_path.read_text())
rows=list(csv.DictReader(source.open()))
groups=defaultdict(dict)
reasons=defaultdict(int)
for r in rows:
    name=norm(r['target_name'])
    if not re.fullmatch(r'HD\d+[AB]?',name): reasons['non_HD_name']+=1; continue
    if not r['obs_release_date'] or r['obs_release_date']>'2026-11-01T00:00:00Z': reasons['not_public_at_cutoff']+=1; continue
    if int(r['n_obs'])!=1 or r['multi_ob']!='S': reasons['not_single_exposure']+=1; continue
    if float(r['snr'] or 0)<50: reasons['catalogue_snr_below_50']+=1; continue
    if float(r['t_exptime'])<300 or float(r['t_min'])<58849: reasons['time_or_exposure_cut']+=1; continue
    if r['dp_id'] in refs['records']: reasons['upstream_referenced_ADP']+=1; continue
    r['canonical_target']=name
    # Prefer latest ADP reprocessing when the same target/start time is repeated.
    key=r['t_min']
    if key not in groups[name] or r['dp_id']>groups[name][key]['dp_id']: groups[name][key]=r
eligible={}
for name,bytime in groups.items():
    rr=sorted(bytime.values(),key=lambda r:(float(r['t_min']),r['dp_id']))
    nights={math.floor(float(r['t_min'])-.5) for r in rr}
    if len(rr)>=5 and len(nights)>=3: eligible[name]=rr
names=sorted(eligible)
assert len(names)>=21
dev_name=names[0]
main_names=names[1:21]

def choose(rr,n=5):
    bynight={}
    for r in rr: bynight.setdefault(math.floor(float(r['t_min'])-.5),r)
    first=list(bynight.values())
    if len(first)>=n:
        return [first[round(i*(len(first)-1)/(n-1))] for i in range(n)]
    out=first[:]
    for r in rr:
        if r not in out: out.append(r)
        if len(out)==n: break
    return sorted(out,key=lambda r:float(r['t_min']))

selected=[]
for name in main_names:
    for r in choose(eligible[name]): selected.append(dict(r,role='main_unopened'))
dev=choose(eligible[dev_name],5)
for i,r in enumerate(dev): r['role']='development' if i<2 else 'validation_background_unopened'
out=P/'selection';out.mkdir(exist_ok=True)
for fname,rr in [('MAIN100.csv',selected),('DEVELOPMENT_AND_VALIDATION.csv',dev)]:
    with (out/fname).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
summary={
 'selected_at_utc':datetime.now(timezone.utc).isoformat(),
 'metadata_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'upstream_ids_sha256':hashlib.sha256(refs_path.read_bytes()).hexdigest(),
 'upstream_commit':refs['upstream_commit'],
 'input_rows':len(rows),'eligible_target_groups':len(names),'excluded_row_counts':dict(reasons),
 'main_targets':main_names,'main_exposures':len(selected),
 'main_exposure_seconds':sum(float(r['t_exptime']) for r in selected),
 'development_targets':['HD203608',dev_name],
 'validation_backgrounds':[r['dp_id'] for r in dev if r['role'].startswith('validation')],
 'selection_rule':'Public at2026-11-01T00Z; single HARPS exposure>=300s, MJD>=58849,catalogueSNR>=50; HD names normalized by whitespace; remove upstream-referenced ADP IDs; latest ADP per target/start; >=5exposures and>=3noon-UTC nights. Bounded alphabetical5000-row metadata snapshot; first eligible target development, next20 main;5epochs spread evenly over available nights, chronological fill if<5nights.',
 'limitations':['Not representative of allHARPSstars; original5000metadata cap and alphabeticalordering are retained.','Absence from referencedIDs does not prove no prior search. Rawprogenitor crosscheck pendingFITSheaders.','Coordinates and physicalidentity consistency will be checked before production; no fluxbased reselection.'],
 'flux_arrays_opened_for_selection':False,
 'status':'METADATA_SELECTION_FIXED_BEFORE_MAIN_DOWNLOAD'
}
(out/'SELECTION.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
