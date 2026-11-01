"""Record the primary agent's visual review; this is NOT an automatic classifier."""
from pathlib import Path
import csv,json,hashlib,datetime
BASE=Path(__file__).resolve().parent.parent
OUT=BASE/'triage_followup'
hits=list(csv.DictReader((BASE/'production/HIT_DISPOSITIONS.csv').open()))
notes={
 'H01':'Compact excess at the expected dispersion row, displaced toward the right side of the ordinary fibre trace; narrower cross-dispersion shape than the continuum.',
 'H02':'Excess concentrated in a single raw dispersion row with a cross-dispersion shape unlike a scaled continuum trace.',
 'H03':'Native emission profile at the O I 5577.339 air reference; raw excess lies on the fibre trace. The other four epochs also have near-reference excess, with descriptive peak/MAD ratios 5.0–9.0.',
 'H04':'Order34 shows a long sloping raw charge track crossing the fibre at the hit, extending well outside the trace. The corresponding native line is absent in overlapping order33. The initial edge-distance choice selected order33; both orders are now retained.',
 'H05':'Sloping compact charge feature crosses the right side of the fibre trace at the native line; morphology differs from a simple scaled fibre profile.',
 'H06':'Native emission profile at the O I 5577.339 air reference; excess lies on the fibre trace. Other epochs have near-reference excess, with descriptive peak/MAD ratios 3.8–13.8.',
 'H07':'Native emission profile at the O I 6300.304 air reference and excess on the fibre trace; other epochs give weaker descriptive near-reference excess.',
 'H08':'A sloping raw charge track extends outside and crosses the fibre trace near the native line; the brightest charge lies several cross-dispersion pixels away from the trace.',
 'H09':'A sloping raw charge feature extends across and beyond the fibre trace at the native line, inconsistent with simply scaling its continuum cross-section.',
 'H10':'A sloping track crosses the fibre in order53, which has the native emission peak. Overlapping order52 does not show that peak. The two native orders and raw cutouts are retained.'}
rows=[]
for h in hits:
    hid=h['hit_id'];oi=hid in {'H03','H06','H07'}
    rows.append(dict(hit_id=hid,canonical_target=h['canonical_target'],dp_id=h['dp_id'],
        original_status='UNREVIEWED',followup_status='PROVISIONAL_ATMOSPHERIC_OI' if oi else 'PROVISIONAL_DETECTOR_ARTIFACT',
        confidence_scope='Qualitative primary-agent review, not independent adjudication',
        evidence=notes[hid],remaining_work='Check independent sky/calibration evidence and exact wavelength transformation' if oi else 'Confirm with independent reviewer and calibration/cosmic-ray masks where available',
        raw_plot='native/RAW_REVIEW_01_05.png' if int(hid[1:])<=5 else 'native/RAW_REVIEW_06_10.png',
        overlap_plot=f'native/{hid}_OVERLAPPING_ORDERS.png' if hid in {'H04','H10'} else '',
        final_origin_confirmed=False,kept_in_original_hit_list=True))
with (OUT/'FOLLOWUP_DISPOSITIONS.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
record=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='Primary agent visual inspection',
    reviewed_hits=10,provisional_detector_artifacts=7,provisional_atmospheric_OI=3,final_confirmed_origins=0,
    basis='Native extracted orders, registered raw CCD cutouts, five existing epochs per target and two O I wavelength references. Non-repetition alone was never a veto.',
    original_table_unchanged_sha256=hashlib.sha256((BASE/'production/HIT_DISPOSITIONS.csv').read_bytes()).hexdigest(),
    mapping_sha256=hashlib.sha256((OUT/'native/MAPPING.json').read_bytes()).hexdigest(),
    independent_review='Not completed; parallel reviewer stopped at account usage limit. No claim of independent review.',rows=rows)
(OUT/'VISUAL_REVIEW.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='rows'},indent=2))
