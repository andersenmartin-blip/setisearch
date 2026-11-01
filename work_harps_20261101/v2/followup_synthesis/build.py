"""Append-only synthesis of published333 events and explicit follow-up overlays."""
from pathlib import Path
import csv,json,hashlib,collections,datetime
O=Path(__file__).resolve().parent;V=O.parent
paths=['triage_batch02/CUMULATIVE_DISPOSITIONS.csv','mapping43_followup/FOLLOWUP_DISPOSITIONS.csv','epoch31_followup/COMBINED_95_EVENT_FOLLOWUP.csv','profile_widths/EVENT_WIDTHS.json','profile_widths31/EVENT_WIDTHS.json']
def read(p):return list(csv.DictReader((V/p).open()))
a=read(paths[0]);m={r['review_id']:r for r in read(paths[1])};e={r['review_id']:r for r in read(paths[2])};widths={r['review_id']:r for p in paths[3:] for r in json.loads((V/p).read_text())}
assert len(a)==333 and len(m)==43 and len(e)==len(widths)==95 and set(e)==set(widths)
for r in a:
 k=r['review_id'];r['status_before_mapping43']=r['current_followup_status'];r['mapping43_followup_applied']=k in m
 if k in m:
  assert r['current_followup_status']==m[k]['prior_followup_status'];r['current_followup_status']=m[k]['followup_status'];r['evidence']=m[k]['evidence'];r['review_table']='mapping43_followup/FOLLOWUP_DISPOSITIONS.csv'
 r['epoch_finding']=e[k]['followup_finding'] if k in e else '';r['epoch_selected_exposures']=e[k]['selected_epochs'] if k in e else ''
 r['barycentric_pairwise_median_r']=e[k]['barycentric_pairwise_median_r'] if k in e else '';r['topocentric_pairwise_median_r']=e[k]['topocentric_pairwise_median_r'] if k in e else ''
 r['minimum_width_reference_ratio']=widths[k]['minimum_width_ratio'] if k in widths else '';r['maximum_width_reference_ratio']=widths[k]['maximum_width_ratio'] if k in widths else ''
 r['all_width_methods_orders_above_two']=widths[k]['all_complete_orders_both_methods_above_two'] if k in widths else ''
 r['final_origin_confirmed']=False
assert {r['review_id'] for r in a if r['current_followup_status']=='UNRESOLVED_SPECTRAL_FEATURE'}==set(e)
with (O/'CUMULATIVE_333.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(a[0]));w.writeheader();w.writerows(a)
s=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),events=333,status_counts=dict(collections.Counter(r['current_followup_status'] for r in a)),unresolved_events=95,epoch_finding_counts=dict(collections.Counter(r['followup_finding'] for r in e.values())),native_complete_orders=sum(r['complete_orders'] for r in widths.values()),events_all_native_orders_both_methods_above_two_reference_widths=sum(r['all_complete_orders_both_methods_above_two'] for r in widths.values()),all_original_catalogs_unchanged=True,all_origins_provisional=True,source_sha256={p:hashlib.sha256((V/p).read_bytes()).hexdigest() for p in paths},interpretation='Descriptive post-hoc evidence; original accepted catalog retained. New100 extension02 is a separate prospective catalog. Repeated profiles, broad molecular-band locations and fitted widths do not identify a transition or exclude a narrow added component. Historical mapping criteria differ by stage.')
(O/'SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
