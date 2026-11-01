"""Fresh-process direct FITS/scalar audit of deterministic first/middle/last atlas rows."""
from pathlib import Path
import csv,json,math,hashlib
import numpy as np
from astropy.io import fits
O=Path(__file__).resolve().parent;BASE=O.parents[2];E=O.parent
read=lambda p:list(csv.DictReader(p.open()))
rows=read(O/'REVIEW_INDEX.csv');hits=read(E/'production/V2_HITS.csv');by={r['candidate_id']:r for r in hits};old=read(BASE/'v2/production/V2_HITS.csv')
manifest={r['dp_id']:r for r in json.loads((E/'acquisition/DOWNLOAD_MANIFEST.json').read_text())};checks=[]
selection=sorted({0,len(rows)//2,len(rows)-1}) if rows else []
for i in selection:
 r=rows[i];h=by[r['candidate_id']];p=BASE/manifest[r['dp_id']]['relative_path'];npz=np.load(O/r['profile_file']);k=int(h['seed_index']);center=float(h['fitted_center_angstrom']);errs=[];modelerrs=[];maxraw=0;maxoffset=0
 with fits.open(p,memmap=False) as hd:
  berv=float(hd[0].header['HIERARCH ESO DRS BERV']);wave=hd[1].data['WAVE'][0];flux=hd[1].data['FLUX'][0]
  for j,off in enumerate(range(-50,51)):
   if k+off<0 or k+off>=len(wave):assert not npz['in_bounds'][j];continue
   x=float(wave[k+off])-center;raw=float(flux[k+off]);base=float(h['sideband_intercept_adu'])+float(h['sideband_slope_adu_per_pixel'])*off;mad=float(h['sideband_mad_adu'])
   value=(raw-base)/mad;model=float(h['amplitude_over_sideband_mad'])*math.exp(-.5*(x/(float(h['fwhm_model_angstrom'])/2.354820045))**2)
   if math.isfinite(value):errs.append(abs(value-float(npz['residual_over_sideband_mad'][j])))
   if math.isfinite(model):modelerrs.append(abs(model-float(npz['saved_gaussian_model'][j])))
   if math.isfinite(raw):maxraw=max(maxraw,abs(raw-float(npz['raw_flux_adu'][j])))
   maxoffset=max(maxoffset,abs(x-float(npz['wavelength_offset_air_angstrom'][j])))
 top=center/(1+berv/299792.458);nearest=min([5577.339,6300.304],key=lambda z:abs(top-z));flag=abs(top-nearest)<=.03;flag6363=abs(top-6363.776)<=.03
 assert abs(top-float(r['approx_topocentric_air_angstrom']))<1e-10
 assert str(flag)==r['original_two_OI_0p03_flag'] and str(flag6363)==r['posthoc_OI6363_0p03_flag']
 peers=[f'V2-{n+1:04d}' for n,past in enumerate(old) if past['canonical_target']==h['canonical_target'] and abs(float(past['fitted_center_angstrom'])-center)<=.03]
 assert set(peers)==set(json.loads(r['old333_matched_review_ids'])) and len(peers)==int(r['old333_match_count'])
 assert max(errs,default=0)<1e-10 and max(modelerrs,default=0)<1e-10 and maxraw<1e-10 and maxoffset<1e-10
 checks.append({'candidate_id':r['candidate_id'],'max_residual_difference':max(errs,default=0),'max_saved_model_difference':max(modelerrs,default=0),'max_raw_difference':maxraw,'max_offset_difference':maxoffset,'old333_match_ids_verified':peers,'both_original_and_posthoc_OI_flags_verified':True})
expected={h['candidate_id'] for h in hits};assert len(rows)==len(expected) and {r['candidate_id'] for r in rows}==expected
assert all((O/r['atlas_file']).exists() and (O/r['profile_file']).exists() for r in rows)
record=json.loads((O/'INPUT_CHECKS.json').read_text());plan=json.loads((O/'PLAN.json').read_text())
for key,hval in record['input_hashes'].items():
 path=BASE/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv' if key=='old333_triage_context' else BASE/plan['inputs'][key]
 assert hashlib.sha256(path.read_bytes()).hexdigest()==hval
assert all(r['origin_status']=='UNREVIEWED' for r in read(E/'production/V2_DISPOSITIONS.csv'))
result={'status':'PASSED','audit_kind':'Same-agent fresh-process direct FITS reads and scalar arithmetic; not independent human validation.','selection':'First/middle/last accepted candidate in saved order, or empty if no hits.','checked_candidates':len(checks),'checks':checks,'all_accepted_candidates_covered_once':True,'all_indexed_figures_and_profiles_exist':True,'input_and_production_disposition_hashes_unchanged':True}
(O/'NUMERICAL_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
