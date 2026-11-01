"""Read-only independent sufficient-statistics audit of saved arrays and immutable inputs."""
from pathlib import Path
import json,hashlib,datetime
import numpy as np
O=Path(__file__).resolve().parent; B=O.parents[1]
plan=json.loads((O/'PLAN.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
for filename in ['NATIVE_MEASUREMENTS.json','ALL_EPOCH_MEASUREMENTS.json']:
 for r in json.loads((O/filename).read_text()):
  d=np.load(O/r['array']);x=d['offset_angstrom'];y=d['flux_adu'];s=d['side_mask'];c=d['core_mask']
  # Closed-form straight-line regression independent of lstsq implementation.
  slope=np.mean((x[s]-x[s].mean())*(y[s]-y[s].mean()))/np.var(x[s]);intercept=y[s].mean()-slope*x[s].mean()
  residual=y-intercept-slope*x;sigma=r['reference_air_angstrom']/(115000*np.sqrt(8*np.log(2)))
  model=np.exp(-(x[c]/sigma)**2/2);amp=np.sum(model*residual[c])/np.sum(model**2)
  assert np.isclose(intercept,r['continuum_intercept_adu'],rtol=1e-10,atol=1e-8)
  assert np.isclose(amp,r['fixed_amplitude_adu'],rtol=1e-10,atol=1e-8)
  assert np.allclose(intercept+slope*x,d['baseline_adu'],rtol=1e-10,atol=1e-8)
  assert np.isclose(amp*np.sqrt(2*np.pi)*sigma,r['fixed_model_area_adu_angstrom'],rtol=1e-10,atol=1e-8)
  assert len(r['trials'])==33
  checks.append(r['array'])
immutable={r:sha(B/r)==h for r,h in plan['original_hashes'].items()};assert all(immutable.values())
a=json.loads((O/'OI25_FOLLOWUP.json').read_text());assert len(a)==25 and len({r['review_id'] for r in a})==25
result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),array_fits_independently_recomputed=len(checks),all_original_hashes_unchanged=immutable,oi25_rows=25,oi25_native_offsets_min_max_angstrom=[min(r['native_fit_offset_angstrom']for r in a),max(r['native_fit_offset_angstrom']for r in a)],oi25_sky_control_rows=sum(r['simultaneous_sky_fiber_available']for r in a),passed=True,limits='This verifies numerical implementation, completeness and immutable source catalogs; not physical origin or calibrated significance.')
(O/'VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
