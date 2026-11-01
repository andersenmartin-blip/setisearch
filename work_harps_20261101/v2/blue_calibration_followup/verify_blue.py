"""Independent moment-form correlation and ridge-support audit, without changing source files."""
from pathlib import Path
import json,hashlib,numpy as np,datetime
O=Path(__file__).resolve().parent;B=O.parents[1];P=json.loads((O/'PLAN.json').read_text())
rows=json.loads((O/'NATIVE_MEASUREMENTS.json').read_text());cm=json.loads((O/'NATIVE_AB_COMPARISONS.json').read_text());pm=json.loads((O/'RAW_PATCH_METADATA.json').read_text());ridge=json.loads((O/'RIDGE_RESULTS.json').read_text())['results']
for c in cm:
 a=next(r for r in rows if r['dp_id']==c['dp_id']and r['group_id']==c['group_id']and r['fiber']=='A'and r['order']==c['A_order']);b=next(r for r in rows if r['dp_id']==c['dp_id']and r['group_id']==c['group_id']and r['fiber']=='B'and r['order']==c['B_order']);da=np.load(O/a['array']);db=np.load(O/b['array']);w=da['wave_angstrom'];wb=db['wave_angstrom'];mask=(abs(w-a['center_air_angstrom'])<=1.5)&(w>=wb[0])&(w<=wb[-1]);x=da['highpass_adu'][mask];y=np.interp(w[mask],wb,db['highpass_adu']);mx=x.mean();my=y.mean();corr=((x-mx)*(y-my)).sum()/np.sqrt(((x-mx)**2).sum()*((y-my)**2).sum());assert abs(corr-c['same_wavelength_highpass_Pearson_r'])<1e-12
for r in ridge:
 m=next(p for p in pm if p['group_id']==r['group_id']and p['A_order']==r['A_order']);d=np.load(O/m['array']);y=d['raw_rows'];x=d['raw_columns'];im=d['highpass_adu'];best=r['best'];cy=r['candidate_row'];line=r['predicted_science_column']+best['intercept_offset']+best['slope']*(y-cy);mask=abs(x[None,:]-line[:,None])<=2;mask&=abs(y[:,None]-cy)>80
 for path in m['trace_paths']:mask&=abs(x[None,:]-np.array(path['raw_columns'])[:,None])>6
 assert mask.sum()==best['training_pixels'];assert mask.sum()>=200
 low=int(np.sum(mask.any(axis=1)&(y<cy-80)));up=int(np.sum(mask.any(axis=1)&(y>cy+80)));assert low==best['lower_training_rows']and up==best['upper_training_rows']and min(low,up)>=25
 assert abs(im[mask].mean()-best['score_adu'])<1e-12
 eligible=[t for t in r['full_grid']if t['eligible']];assert max(t['score_adu']for t in eligible)==best['score_adu'];assert len(r['full_grid'])==91*81
immutable={s:hashlib.sha256((B/s).read_bytes()).hexdigest()==h for s,h in P['original_hashes'].items()};assert all(immutable.values())
out=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_cutout_count=len(rows),independent_correlations_verified=len(cm),ridge_off_trace_and_withheld_support_verified=len(ridge),native_arrays_present=all((O/r['array']).exists()for r in rows),original_hashes_unchanged=immutable,passed=True,limits='Numeric audit is not validation of physical parent order, calibrated significance, or origin classification. Ridge selection remains explicitly post hoc.')
(O/'VERIFICATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
