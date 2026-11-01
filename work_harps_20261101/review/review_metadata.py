"""Independent metadata audit; no scientific flux arrays are accessed."""
import csv, json, hashlib, re, math
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u

P=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:list(csv.DictReader(p.open()))
main=read(P/'selection/MAIN100.csv')
dv=read(P/'selection/DEVELOPMENT_AND_VALIDATION.csv')
original=read(P/'access_probe/harps_post2019_metadata.csv')
sel=json.loads((P/'selection/SELECTION.json').read_text())
refs=json.loads((P/'literature/UPSTREAM_REFERENCED_IDS.json').read_text())
byid={r['dp_id']:r for r in original}
checks={}
checks['source_metadata_hash_matches']=sha(P/'access_probe/harps_post2019_metadata.csv')==sel['metadata_sha256']
checks['source_reference_hash_matches']=sha(P/'literature/upstream_referenced_exposure_ids.json')==sel['upstream_ids_sha256']
checks['100_main_rows_and_unique_ids']=len(main)==len({r['dp_id'] for r in main})==100
checks['20_targets']=len({r['canonical_target'] for r in main})==20
checks['original_rows_preserved']=all(all(r[k]==byid[r['dp_id']][k] for k in byid[r['dp_id']]) for r in main+dv)
checks['normalized_names']=all(re.sub(r'\s+','',r['target_name']).upper()==r['canonical_target'] for r in main+dv)
checks['public_at_cutoff']=all(bool(r['obs_release_date']) and r['obs_release_date']<='2026-11-01T00:00:00Z' for r in main+dv)
checks['single_exposure_HARPS']=all(r['instrument_name']=='HARPS' and r['n_obs']=='1' and r['multi_ob']=='S' for r in main+dv)
checks['snr_exposure_and_date_cuts']=all(float(r['snr'])>=50 and float(r['t_exptime'])>=300 and float(r['t_min'])>=58849 for r in main+dv)
checks['no_referenced_ADP_overlap']=not(set(refs['ADP']) & {r['dp_id'] for r in main+dv})
checks['main_development_validation_disjoint']=not({r['dp_id'] for r in main}&{r['dp_id'] for r in dv}) and len(dv)==len({r['dp_id'] for r in dv})
checks['development_and_validation_roles']=sum(r['role']=='development' for r in dv)==2 and sum(r['role']=='validation_background_unopened' for r in dv)==3
checks['development_targets_excluded']=not(set(sel['development_targets'])&{r['canonical_target'] for r in main})
checks['exposure_seconds_sum_matches']=abs(sum(float(r['t_exptime']) for r in main)-sel['main_exposure_seconds'])<1e-8
groups=defaultdict(list)
for r in main:groups[r['canonical_target']].append(r)
checks['five_epochs_minimum_three_noon_UTC_nights']=all(len(rr)==5 and len({math.floor(float(r['t_min'])-.5) for r in rr})>=3 for rr in groups.values())
catalog=list(csv.DictReader((P/'literature/upstream/OSETI_targets.txt').open(),delimiter='\t'))
namekey=list(catalog[0])[0]
catcoords=SkyCoord([x['RA'] for x in catalog],[x['DEC'] for x in catalog],unit=(u.hourangle,u.deg))
targets=[]
for name,rr in groups.items():
    coords=SkyCoord([float(r['s_ra']) for r in rr]*u.deg,[float(r['s_dec']) for r in rr]*u.deg)
    sepmax=max(float(coords[i].separation(coords).arcsec.max()) for i in range(len(rr)))
    ii,dd,_=coords[0].match_to_catalog_sky(catcoords);idx=int(np.asarray(ii).item());distance=float(np.asarray(dd.arcsec).item())
    targets.append(dict(target=name,epochs=len(rr),nights=len({math.floor(float(r['t_min'])-.5) for r in rr}),
        pointing_pairwise_max_arcsec=sepmax,nearest_parent_catalog_name=catalog[idx][namekey],
        nearest_parent_catalog_first_pointing_arcsec=distance,
        parent_catalog_match_within_60_arcsec=distance<60))
result=dict(schema='HARPS_METADATA_INDEPENDENT_REVIEW_V1',reviewed_utc=datetime.now(timezone.utc).isoformat(),
    input_sha256={str(p.relative_to(P)):sha(p) for p in [P/'selection/MAIN100.csv',P/'selection/DEVELOPMENT_AND_VALIDATION.csv',P/'selection/SELECTION.json',P/'literature/UPSTREAM_REFERENCED_IDS.json']},
    checks=checks,all_selection_checks_pass=all(checks.values()),targets=targets,
    flux_arrays_opened=False,
    limitations=['ObsCore s_ra/s_dec are pointing coordinates, not necessarily intended-target coordinates. Pairwise differences up to about73arcsec require separate FITS TEL TARG coordinate review; they are not silently treated as proof of wrong source.',
    'Parent optical SETI catalog is not all HARPS targets; nearest objects beyond60arcsec are recorded as no positional match, not assigned as source identity.',
    'No overlap with listed ADP references does not prove never searched. Raw-progenitor overlap is reviewed separately after download.'])
(P/'review/METADATA_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'all_selection_checks_pass':all(checks.values()),'checks':checks,'max_pairwise_pointing_arcsec':max(x['pointing_pairwise_max_arcsec'] for x in targets)},indent=2))
