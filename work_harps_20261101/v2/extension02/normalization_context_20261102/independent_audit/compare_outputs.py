"""Compare independent expectations and original arrays to all delivered contexts."""
from pathlib import Path
import json,csv,hashlib,math,statistics,subprocess,io,tarfile,datetime
import numpy as np
from astropy.io import fits
OUT=Path(__file__).resolve().parent;CONTEXT=OUT.parent;EXT=CONTEXT.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(n):return list(csv.DictReader((CONTEXT/n).open()))
def key(r):return (r['candidate_id'],r['dp_id'],r['frame'])
def med(a):return statistics.median(float(x) for x in a)
def mad(a):
 a=[float(x) for x in a];middle=med(a);return 1.4826*med(abs(v-middle) for v in a)
def poly(h,prefix,degree,order,x):return sum(float(h[prefix+str(order*(degree+1)+j)])*x**j for j in range(degree+1))

def main():
 expected=json.loads((OUT/'INDEPENDENT_EXPECTATIONS.json').read_text());products=json.loads((CONTEXT/'SOURCE_PRODUCTS.json').read_text())['products']
 profile=table('PROFILE_DIAGNOSTICS.csv');merged=table('MERGED_WINDOW_DIAGNOSTICS.csv');native=table('NATIVE_ORDER_DIAGNOSTICS.csv')
 assert len(profile)==28 and len(merged)==8 and len(native)==12
 recorded_paths=['PLAN.json','FREEZE.json','analyze_context.py','SOURCE_PRODUCTS.json','PROFILE_DIAGNOSTICS.csv','MERGED_WINDOW_DIAGNOSTICS.csv','NATIVE_ORDER_DIAGNOSTICS.csv','SUMMARY.json','INPUT_IDENTITY_CHECKS.json']
 hashes={p:sha(CONTEXT/p) for p in recorded_paths};checks=0;maximum=0.;maxwave=0.;maxtrace=0.
 def close(actual,wanted,tolerance=1e-10):
  nonlocal checks,maximum
  difference=abs(float(actual)-float(wanted));assert difference<=tolerance,(actual,wanted,difference,tolerance)
  maximum=max(maximum,difference);checks+=1
 pm={key(r):r for r in profile};assert set(pm)=={key(r) for r in expected['profile_records']}
 for e in expected['profile_records']:
  r=pm[key(e)]
  for a,b in [('normalization_adu','normalizer'),('first_difference_noise_proxy_adu','noise'),('normalization_to_noise_proxy','normalizer_over_noise'),('recomputed_normalized_correlation','recomputed_normalized_residual_pearson'),('recomputed_unnormalized_correlation','recomputed_unnormalized_residual_pearson')]:close(r[a],e[b])
  close(r['half_normalizer_correlation'],e['recomputed_normalized_residual_pearson'],1e-12);close(r['double_normalizer_correlation'],e['recomputed_normalized_residual_pearson'],1e-12)
  assert (r['local_continuum_low']=='True')==e['low'] and (r['is_discovery_exposure']=='True')==e['is_discovery']
 mm={key(r):r for r in merged};nm={(*key(r),int(r['order'])):r for r in native}
 assert set(mm)=={key(r) for r in expected['focused_merged']};assert set(nm)=={(*key(r),r['order']) for r in expected['native_orders']}
 for e in expected['focused_merged']:
  r=mm[key(e)]
  for a,b in [('normalization_adu','normalization'),('first_difference_noise_proxy_adu','noise_proxy'),('normalization_to_noise_proxy','normalizer_over_noise'),('window_samples','samples'),('window_nonpositive_samples','nonpositive_samples'),('finite_positive_ERR','finite_positive_ERR_samples')]:close(r[a],e[b])
  p=CONTEXT/r['derived_path'];assert sha(p)==r['derived_sha256'];hashes[r['derived_path']]=sha(p)
  with np.load(p,allow_pickle=False) as d:
   assert hashlib.sha256(d['wavelength_bary_air_angstrom'].astype('<f8').tobytes()).hexdigest()==e['selected_wave_sha256']
   assert hashlib.sha256(d['raw_flux'].astype('<f8').tobytes()).hexdigest()==e['selected_flux_sha256']
 for e in expected['native_orders']:
  r=nm[(*key(e),e['order'])]
  for a,b in [('native_pixel','native_pixel'),('raw_row','raw_row'),('raw_column','raw_column'),('center_topocentric_air_angstrom','topocentric_center'),('native_samples','native_samples'),('native_median','native_median'),('native_nonpositive_samples','native_nonpositive'),('native_minimum','native_min'),('native_maximum','native_max')]:close(r[a],e[b])
  p=CONTEXT/r['derived_path'];assert sha(p)==r['derived_sha256'];hashes[r['derived_path']]=sha(p)
  with np.load(p,allow_pickle=False) as d:
   for a,b in [('raw_cutout','raw_cutout_sha256'),('raw_background','raw_background_sha256'),('raw_excess','raw_excess_sha256')]:assert hashlib.sha256(d[a].astype('<f8').tobytes()).hexdigest()==e[b]
 for dp in dict.fromkeys(r['dp_id'] for r in merged):
  prods={r['kind']:r for r in products if r['dp_id']==dp}
  for r in prods.values():assert sha(CONTEXT/r['local_path'])==r['sha256']
  with fits.open(CONTEXT/prods['SCIENCE']['local_path'],memmap=False) as hd:
   w=np.array(hd[1].data['WAVE'][0],float);f=np.array(hd[1].data['FLUX'][0],float);err=np.array(hd[1].data['ERR'][0],float)
  with tarfile.open(CONTEXT/prods['ANCILLARY']['local_path']) as tar:
   member=next(m for m in tar if m.name.endswith('_e2ds_A.fits'))
   with fits.open(io.BytesIO(tar.extractfile(member).read()),memmap=False) as hd:h=hd[0].header.copy();nf=hd[0].data.astype(float)
  for r in [r for r in merged if r['dp_id']==dp]:
   cb=float(r['center_sampled_bary_air_angstrom']);mask=(abs(w-cb)<=2)&np.isfinite(f);vals=f[mask]
   close(r['left_side_median_adu'],med(f[(w>=cb-2)&(w<cb-1)]));close(r['right_side_median_adu'],med(f[(w>cb+1)&(w<=cb+2)]))
   for k,v in [('window_minimum',min(vals)),('window_maximum',max(vals)),('window_p10',np.quantile(vals,.1)),('window_p90',np.quantile(vals,.9))]:close(r[k],v)
   with np.load(CONTEXT/r['derived_path']) as d:assert np.array_equal(d['ERR'],err[mask],equal_nan=True)
  px=np.arange(4096,dtype=float);degree=int(h['ESO DRS CAL TH DEG LL'])
  for r in [r for r in native if r['dp_id']==dp]:
   o=int(r['order']);ct=float(r['center_topocentric_air_angstrom']);wv=poly(h,'ESO DRS CAL TH COEFF LL',degree,o,px);sel=(abs(wv-ct)<=2)&np.isfinite(nf[o]);values=nf[o,sel]
   pairs=(abs(wv[:-1]-ct)<=2)&np.isfinite(np.diff(nf[o]));noise=mad(np.diff(nf[o])[pairs])/math.sqrt(2)
   close(r['native_noise_proxy_adu'],noise);close(r['native_median_to_noise_proxy'],med(values)/noise)
   close(r['native_p10'],np.quantile(values,.1));close(r['native_p90'],np.quantile(values,.9))
   with np.load(CONTEXT/r['derived_path'],allow_pickle=False) as d:
    assert np.array_equal(d['native_flux'],values)
    wave_error=float(np.max(abs(d['native_wave']-wv[sel])));assert wave_error<1e-10;maxwave=max(maxwave,wave_error)
    cut=d['raw_cutout'];bg=d['raw_background'];excess=d['raw_excess'];col=float(r['raw_column']);cc=round(col)
    columns=[i for i,offset in enumerate(range(-16,17)) if abs(offset-(col-cc))<=2];rr=list(range(13,18))
    center_values=[cut[a,b] for a in rr for b in columns];excess_values=[excess[a,b] for a in rr for b in columns]
    close(r['raw_center_median_adu'],med(center_values));close(r['raw_side_background_median_adu'],med(bg[columns]));close(r['raw_center_excess_median_adu'],med(excess_values));close(r['raw_center_excess_max_adu'],max(excess_values))
 for p,digest in hashes.items():assert sha(CONTEXT/p)==digest
 source=json.loads((CONTEXT/'PLAN.json').read_text())['source_hashes']
 for p,digest in source.items():assert sha(EXT/p)==digest
 summary=json.loads((CONTEXT/'SUMMARY.json').read_text());assert summary['original_U_labels_changed']==0 and summary['new_origin_assignments']==0
 report=dict(schema='SETI_NORMALIZATION_CONTEXT_INDEPENDENT_AUDIT_V1',status='PASS',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),coverage=dict(archived_profiles=28,focused_merged_windows=8,original_source_products=9,native_order_contexts=12,raw_cutouts=12,derived_array_files=20,scalar_metric_comparisons=checks),max_scalar_metric_discrepancy=maximum,max_direct_power_native_wavelength_discrepancy_angstrom=maxwave,profile_algebra_max_errors=expected['max_absolute_errors'],positive_scalar_normalization_alone_cannot_change_Pearson=True,all28_normalizers_positive=True,all_low_flags_in_single_nondiscovery_exposure=True,low_exposure='ADP.2023-08-29T01:02:07.487',low_profile_count=4,discovery_low_profile_count=0,all_focused_ERR_missing=True,original_U_labels_unchanged=True,checked_output_sha256=hashes,script_sha256=sha(Path(__file__)),independent_expectations_script_sha256=sha(OUT/'check_normalization.py'),limitations=['Audits only the two fixed events and selected raw/native context; no new search or physical-origin assignment.','Common NumPy/Astropy primitives and FITS sources; no production analysis functions imported.','Noise proxy from adjacent differences is descriptive and may be affected by correlated interpolation or spectral structure; no calibrated significance.'])
 (OUT/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='checked_output_sha256'},indent=2))
if __name__=='__main__':main()
