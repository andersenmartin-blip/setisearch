from pathlib import Path
import json,collections,datetime
P=Path(__file__).resolve().parent
notes=json.loads((P/'agent_review_097_220_manual.json').read_text())
m=json.loads((P/'NATIVE_MAPPING.json').read_text());local=json.loads((P/'agent_local_097_220/INDEX.json').read_text());focus=json.loads((P/'FOCUS_INDEX.json').read_text())
assert set(notes)=={str(i) for i in range(97,221)}
suffix={
'A':'Provisional qualitative detector-artifact interpretation; no calibrated particle classification or final origin confirmation.',
'O':'Provisional atmospheric compatibility only; no independent sky measurement or calibration-contamination test confirms the origin.',
'U':'Origin remains unresolved; neither isolated occurrence nor repetition is used as an origin veto.',
'M':'No raw-based origin is assigned; apparent morphology does not override incomplete registration.'}
out={}
for k,(code,reason) in notes.items():
 hid=f'V2-{int(k):04d}';orders=[r for r in m['orders'] if r['review_id']==hid]
 if any(r.get('mapping_verified') is False for r in orders):assert code=='M',hid
 if code=='O':assert any(r.get('OI_flag') for r in orders),hid
 loc=[r for r in local if r['review_id']==hid]
 assert len(loc)==sum(r['status']=='EXTRACTED' for r in orders)
 refs=f'REVIEW_{(int(k)-97)//6+1:02d}.png event panel{(int(k)-97)%6+1}'
 refs+='; local raw '+', '.join(f"LOCAL_{r['page']:02d}.png panel{r['position']} (order{r['order']})" for r in loc)
 ff=[r for r in focus if r['review_id']==hid]
 if ff:refs+=f"; FOCUS_{ff[0]['page']:02d}.png row{ff[0]['row']}"
 if int(k)==205:refs+='; agent_local_097_220/FOCUS_0205.png'
 out[k]=[code,reason+' '+suffix[code]+' Viewed: '+refs+'.']
(P/'agent_review_097_220.json').write_text(json.dumps(out,indent=2)+'\n')
summary=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),range=[97,220],events=len(out),counts=dict(collections.Counter(v[0] for v in out.values())),extracted_orders_viewed=len(local),edge_orders=[dict(review_id=r['review_id'],order=r['order'],status=r['status']) for r in m['orders'] if 97<=int(r['review_id'][3:])<=220 and r['status']!='EXTRACTED'],review_pages=list(range(1,22)),focus_pages=list(range(1,9)),local_pages=list(range(1,15)),explicit_limit='Same review agent; no independent expert validation. All 164 available extracted-order raw panels and 124 native profiles inspected; two edge-truncated orders have no full cutout and are not claimed observed. Fixed mapping flags retained.')
(P/'agent_review_097_220_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
