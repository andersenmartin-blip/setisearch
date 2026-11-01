"""Header-only descriptive check of the ten existing hits; no FITS arrays opened."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import json
import hashlib
import math

BASE=Path(__file__).resolve().parent.parent
OUT=Path(__file__).resolve().parent
C_KM_S=299792.458
REFERENCES=[5577.339,6300.304]
hits=list(csv.DictReader((BASE/'production/PRELIMINARY_HITS.csv').open()))
assert len(hits)==10
rows=[]
inputs={}
for number,hit in enumerate(hits,1):
    relative='production/spectra/'+hit['dp_id'].replace(':','_')+'.json'
    path=BASE/relative
    result=json.loads(path.read_text())
    meta=result['input']
    assert meta['sha256']==hit['input_sha256']
    assert meta['SPECSYS']=='BARYCENT' and meta['wavelength_ucd']=='em.wl;obs.atmos'
    inputs[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    bary=float(hit['wave_peak_angstrom']);berv=meta['berv_km_s'];beta=berv/C_KM_S
    # Exact algebraic inverse of the first-order wavelength-stretch convention.
    top=bary/(1+beta)
    reference=min(REFERENCES,key=lambda line:abs(top-line))
    offset=top-reference
    relativistic_alternative=bary/math.sqrt((1+beta)/(1-beta))
    rows.append(dict(hit_number=number,target=hit['canonical_target'],dp_id=hit['dp_id'],
        date_obs_utc=meta['DATE-OBS'],exposure_seconds=meta['EXPTIME'],berv_km_s=berv,
        pipeline=meta['PROCSOFT'],barycentric_air_peak_angstrom=bary,
        inferred_topocentric_air_peak_angstrom=top,
        nearest_of_two_OI_reference_air_angstrom=reference,offset_air_angstrom=offset,
        offset_velocity_equivalent_km_s=C_KM_S*offset/reference,
        offset_divided_by_nominal_resolution_element=offset/(reference/115000),
        nominal_half_grid_bin_angstrom=result['nominal_step_angstrom']/2/(1+beta),
        radial_relativistic_alternative_difference_angstrom=relativistic_alternative-top,
        delta_5577p339_air_angstrom=top-REFERENCES[0],
        delta_6300p304_air_angstrom=top-REFERENCES[1],
        disposition='UNREVIEWED'))
with (OUT/'TEN_HIT_HEADER_OFFSETS.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
report=dict(schema='INITIAL_HEADER_ONLY_TRIAGE_V1',created_utc=datetime.now(timezone.utc).isoformat(),
    scope='Ten previously detected first-stage hits, saved result/header metadata only. No FITS arrays opened, no new observations, no raw downloads, no changes to frozen code or existing dispositions.',
    formula='lambda_top_est = lambda_bary_air / (1 + BERV / 299792.458 km/s)',
    formula_status='Sign and first-order stretching convention supported by primary TAPAS paper and ESO barycentric S1D documentation. Exact HARPS_3.8 source implementation, full relativistic convention and air-dispersion treatment not verified in this bounded check; inferred topocentric values are preliminary.',
    reference_status='O I air wavelengths 5577.339 and 6300.304 Angstrom confirmed in National Bureau of Standards NSRDS-NBS 3 section 7, Charlotte E. Moore (1976), retrieved from the US government govinfo copy. Not a current complete airglow catalogue.',
    uncertainty=['Peak is the maximum-contrast sample, not a fitted centroid; approximately 0.01-Angstrom sampling gives a half-bin scale about 0.005 Angstrom, not a measured statistical uncertainty.',
        'No fitted centroid errors, error spectrum, wavelength-calibration covariance or BERV uncertainty has been propagated.',
        'A radial relativistic alternative is tabulated only as a scale comparison, not a verified HARPS correction or complete error bound.',
        'Airglow winds, blends, instrumental and reduction artifacts, sky/fibre-B data and two-dimensional detector morphology remain unchecked.',
        'Only two named O I lines are compared. A distant nearest reference does not rule out any other terrestrial, stellar or instrumental source.',
        'All ten disposition values remain UNREVIEWED. Wavelength coincidence does not establish origin, eliminate a hit or identify a laser.'],
    rows=rows,input_sha256=inputs,
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(OUT/'INITIAL_TRIAGE.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(hits=len(rows),all_dispositions='UNREVIEWED',max_radial_relativistic_alternative_difference_angstrom=max(abs(r['radial_relativistic_alternative_difference_angstrom']) for r in rows)),indent=2))
