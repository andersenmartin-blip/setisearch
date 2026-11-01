from pathlib import Path
import json,csv,hashlib
P=Path(__file__).resolve().parent;p=json.load((P/'ATOMIC_CONTEXT_PLAN.json').open());out=[]
for r in csv.DictReader((P/'CANDIDATE_CONTEXT_95.csv').open()):
 w=float(r['approx_stellar_air_angstrom']);line=min(p['lines_air_angstrom'],key=lambda x:abs(w-x[1]));d=w-line[1]
 out.append(dict(review_id=r['review_id'],target=r['target'],approx_stellar_air_angstrom=w,nearest_in_bounded_list=line[0],reference_air_angstrom=line[1],difference_angstrom=d,within_0p10_angstrom=abs(d)<=.1,source_url=p['source_urls'][line[2]],specific_identification='UNASSIGNED',limitation='Incomplete selected H/He/Ca reference list; positional overlap alone is not chemical identity.'))
with (P/'ATOMIC_CONTEXT_95.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
(P/'ATOMIC_CONTEXT_SUMMARY.json').write_text(json.dumps(dict(events=len(out),within_0p10=[r for r in out if r['within_0p10_angstrom']],origin_dispositions_changed=False,plan_sha256=hashlib.sha256((P/'ATOMIC_CONTEXT_PLAN.json').read_bytes()).hexdigest()),indent=2)+'\n')
print(json.dumps([r for r in out if r['within_0p10_angstrom']],indent=2))
