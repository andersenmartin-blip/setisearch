"""Join explicit primary-agent visual notes to immutable V2 results; audit counts."""
from pathlib import Path
import csv,json,hashlib,datetime,collections
BASE=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'PLAN.json').read_text())
assert sha(BASE/'v2/review/REVIEW_INDEX.csv')==plan['input_index_sha256']
assert sha(BASE/'v2/production/V2_HITS.csv')==plan['hits_sha256']
assert sha(BASE/'v2/production/V2_DISPOSITIONS.csv')==plan['original_dispositions_sha256']
notes=json.loads((OUT/'MANUAL_REVIEW_NOTES.json').read_text());assert set(notes)=={str(i) for i in range(1,97)}
selected=list(csv.DictReader((OUT/'SELECTED_HITS.csv').open()))
hits=list(csv.DictReader((BASE/'v2/production/V2_HITS.csv').open()))
mapping=json.loads((OUT/'NATIVE_MAPPING.json').read_text())
types={'A':'PROVISIONAL_DETECTOR_ARTIFACT','O':'PROVISIONAL_ATMOSPHERIC_OI','U':'UNRESOLVED_SPECTRAL_FEATURE','M':'INSUFFICIENT_RAW_MAPPING'}
rows=[];repeat=[]
for i,s in enumerate(selected):
    h=hits[i];hid=s['review_id'];code,reason=notes[str(i+1)]
    assert h['dp_id']==s['dp_id'] and h['seed_index']==s['seed_index']
    orders=[r for r in mapping['orders'] if r['review_id']==hid]
    assert orders and any(r['status']=='EXTRACTED' for r in orders)
    if any(r.get('mapping_verified')==False for r in orders):assert code=='M'
    if hid in ['V2-0046','V2-0047']:assert code=='M'
    if code=='O':assert s['OI_0p03_angstrom_flag']=='True'
    center=float(h['fitted_center_angstrom'])
    peers=[dict(review_id=f'V2-{j+1:04d}',dp_id=x['dp_id'],barycentric_offset_angstrom=float(x['fitted_center_angstrom'])-center)
           for j,x in enumerate(hits) if x['canonical_target']==h['canonical_target'] and x['dp_id']!=h['dp_id'] and abs(float(x['fitted_center_angstrom'])-center)<=.03]
    if code=='U':repeat.append(dict(review_id=hid,target=h['canonical_target'],fitted_center_bary_air_angstrom=center,other_exposures=len({x['dp_id'] for x in peers}),matches=peers))
    rows.append(dict(review_id=hid,dp_id=s['dp_id'],canonical_target=s['target'],date_obs=h['date_obs'],
        fitted_center_bary_air_angstrom=center,original_status='UNREVIEWED',followup_status=types[code],
        evidence=reason,covering_orders=json.dumps([r['order'] for r in orders]),
        edge_truncated_orders=json.dumps([r['order'] for r in orders if r['status']=='EDGE_TRUNCATED']),
        raw_mapping_status='INSUFFICIENT' if code=='M' else 'REFERENCE_AND_LOCAL_VISUAL_CHECK',
        atlas_page=(i//6)+1,atlas_panel=(i%6)+1,final_origin_confirmed=False,
        reviewer='Primary agent visual review; no independent reviewer',kept_in_original_catalog=True))
with (OUT/'FOLLOWUP_DISPOSITIONS.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
counts=dict(collections.Counter(r['followup_status'] for r in rows))
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='FIRST_PASS_COMPLETED_WITH_UNRESOLVED_CASES',
    reviewed_events=len(rows),total_v2_events=len(hits),not_yet_reviewed=len(hits)-len(rows),targets=5,input_exposures=24,
    disposition_counts=counts,all_final_origins_confirmed=False,original_catalog_unchanged=True,
    native_orders_extracted=mapping['extracted_orders'],edge_truncated_orders=mapping['edge_truncated_orders'],
    global_mapping_uncertain_exposures=sum(r['status']!='REGISTERED' for r in mapping['spectra']),
    global_mapping_uncertain_hits=4,additional_local_mapping_uncertain_hits=2,
    unresolved_spectral_features_with_another_saved_V2_hit_within_0p03_bary_air=sum(r['other_exposures']>0 for r in repeat),
    repeat_limit='Post-hoc proximity among already accepted V2 hits, not all-epoch photometry, a stellar-rest-frame identification or an origin veto.',
    controls='All48 products hashed and raw/native DATE-OBS and BERV checked. Visual dispositions are provisional same-agent judgments, not independent validation.',
    source_hashes={str(p.relative_to(BASE)):sha(p) for p in [OUT/'PLAN.json',OUT/'MANUAL_REVIEW_NOTES.json',OUT/'NATIVE_MAPPING.json',OUT/'LOCAL_TRACE_AUDIT.json',Path(__file__)]})
(OUT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
(OUT/'REPEAT_PROXIMITY.json').write_text(json.dumps(dict(tolerance_angstrom=.03,frame='Barycentric air',selection='Only24 unresolved spectral features; matches in immutable333-hit list',events=repeat),indent=2)+'\n')
print(json.dumps(summary,indent=2))
