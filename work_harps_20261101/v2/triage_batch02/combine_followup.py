"""Cumulative descriptive dispositions; preserve every frozen/source table."""
from pathlib import Path
import csv,json,collections,hashlib,datetime
OUT=Path(__file__).resolve().parent;V2=OUT.parent
def rows(p):return list(csv.DictReader(p.open()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
first=rows(V2/'triage_batch01/FOLLOWUP_DISPOSITIONS.csv')
new=rows(OUT/'FOLLOWUP_DISPOSITIONS.csv')
corrections={r['review_id']:r for r in rows(V2/'mapping_followup_review/FOLLOWUP_DISPOSITIONS.csv')}
combined=[]
for batch,source in [('triage_batch01',first),('triage_batch02',new)]:
    for r in source:
        corrected=corrections.get(r['review_id'])
        combined.append(dict(review_id=r['review_id'],dp_id=r['dp_id'],canonical_target=r['canonical_target'],
            date_obs=r['date_obs'],fitted_center_bary_air_angstrom=r['fitted_center_bary_air_angstrom'],
            original_status='UNREVIEWED',initial_followup_status=r['followup_status'],
            current_followup_status=corrected['followup_status'] if corrected else r['followup_status'],
            evidence=corrected['evidence'] if corrected else r['evidence'],
            source_batch=batch,corrected_mapping_followup=bool(corrected),final_origin_confirmed=False,
            review_table='mapping_followup_review/FOLLOWUP_DISPOSITIONS.csv' if corrected else batch+'/FOLLOWUP_DISPOSITIONS.csv'))
assert len(combined)==333 and [r['review_id'] for r in combined]==[f'V2-{i:04d}' for i in range(1,334)]
with (OUT/'CUMULATIVE_DISPOSITIONS.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(combined[0]));w.writeheader();w.writerows(combined)
counts=dict(collections.Counter(r['current_followup_status'] for r in combined))
targets={t:dict(collections.Counter(r['current_followup_status'] for r in combined if r['canonical_target']==t)) for t in dict.fromkeys(r['canonical_target'] for r in combined)}
unresolved=[]
for h in combined:
    if h['current_followup_status'] not in ['UNRESOLVED_SPECTRAL_FEATURE','INSUFFICIENT_RAW_MAPPING']:continue
    center=float(h['fitted_center_bary_air_angstrom'])
    peers=[dict(review_id=r['review_id'],dp_id=r['dp_id'],barycentric_offset_angstrom=float(r['fitted_center_bary_air_angstrom'])-center)
           for r in combined if r['canonical_target']==h['canonical_target'] and r['dp_id']!=h['dp_id'] and abs(float(r['fitted_center_bary_air_angstrom'])-center)<=.03]
    unresolved.append(dict(review_id=h['review_id'],status=h['current_followup_status'],target=h['canonical_target'],
        center_bary_air_angstrom=center,other_exposures=len({r['dp_id'] for r in peers}),matches=peers))
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='FIRST_PASS_ALL333_COMPLETED_WITH_UNRESOLVED_CASES',
    reviewed_events=333,not_yet_reviewed=0,disposition_counts=counts,by_target=targets,
    total_main_exposures=200,total_main_targets=20,total_main_exposure_seconds=168299.165,
    v2_exposures=100,v2_targets=19,exposures_with_hits_and_raw_followup=92,
    total_raw_and_ancillary_products=184,raw_and_ancillary_bytes=2408361164,
    correction_of_prior_mapping_cases=6,additional_corrected_mapping_checks_with_disposition_retained=2,
    all_final_origins_confirmed=False,original_catalog_unchanged=True,
    unresolved_spectral_events_with_other_saved_hit_within_0p03_angstrom=sum(r['status']=='UNRESOLVED_SPECTRAL_FEATURE' and r['other_exposures']>0 for r in unresolved),
    mapping_insufficient_events_with_other_saved_hit_within_0p03_angstrom=sum(r['status']=='INSUFFICIENT_RAW_MAPPING' and r['other_exposures']>0 for r in unresolved),
    interpretation='All333 have a documented first-pass outcome. A completed first pass is not complete origin validation, a qualified null result, or evidence for technology. Extra raw products do not increase unique main exposure coverage.',
    method_caveat='Batch01 used one-region orientation plus local visual checks; six flagged cases and two related positions received fixed multi-region followup. Batch02 uses a fixed24-region registration and conservative two-sided local support flags. Counts reflect these different followup checks, not calibrated class frequencies.',
    repeat_caveat='Post-hoc proximity only among accepted hits in barycentric air coordinates; not all-epoch fitting, independent recurrence evidence, or stellar-rest-frame identification.',
    source_hashes={str(p.relative_to(V2)):sha(p) for p in [V2/'triage_batch01/FOLLOWUP_DISPOSITIONS.csv',OUT/'FOLLOWUP_DISPOSITIONS.csv',V2/'mapping_followup_review/FOLLOWUP_DISPOSITIONS.csv',Path(__file__)]})
(OUT/'CUMULATIVE_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'CUMULATIVE_REPEAT_PROXIMITY.json').write_text(json.dumps(dict(tolerance_angstrom=.03,events=unresolved),indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['by_target','source_hashes']},indent=2))
