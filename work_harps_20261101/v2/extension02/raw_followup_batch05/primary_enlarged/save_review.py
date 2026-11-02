"""Record primary review after actual inspection of both fixed atlas/display pages."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
NOTES={
 'V2E2-0332':('A','Order64 has a thin, gently sloping charge-like trail spanning columns about -8 to 0 and crossing the predicted central row/trace. The sharp native spike coincides with this localized track. The full-cutout scale is dominated by a separate bright adjacent trace; fixed central enlargement reveals the selected morphology.'),
 'V2E2-0333':('A','Order66 shows a compact bright off-center deposit around column -2,row +1 with a thin diagonal tail extending through the central trace near row0. Its geometry is charge-like and accompanies the narrow native enhancement. The far-right bright adjacent trace dominates the full atlas scale and is distinct from this central contaminant.')}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 mapping=json.loads((ROOT/'NATIVE_MAPPING.json').read_text());figures=json.loads((ROOT/'FIGURE_INDEX.json').read_text());scales=json.loads((ROOT/'primary_enlarged/DISPLAY_SCALES.json').read_text());selected=list(csv.DictReader((ROOT/'SELECTED_EVENTS.csv').open()))
 by_event={r['review_id']:r for r in mapping['events']};by_fig={r['review_id']:r for r in figures}
 assert len(selected)==len(NOTES)==2 and set(NOTES)=={r['review_id']for r in selected}
 extracted=[r for r in mapping['orders']if r['status']=='EXTRACTED'];assert len(extracted)==2
 for r in extracted:assert sha(ROOT/r['cutout'])==r['cutout_sha256']
 assert {(r['review_id'],r['order'])for r in extracted}=={(r['review_id'],r['order'])for r in scales['index']}
 events=[]
 for s in selected:
  rid=s['review_id'];q=by_event[rid];f=by_fig[rid];code,note=NOTES[rid];orders=[r for r in mapping['orders']if r['review_id']==rid];shown=[r for r in scales['index']if r['review_id']==rid]
  assert q['mapping_supported'] and len(orders)==len(shown)==1 and not f['missing_full_cutout_orders']
  events.append(dict(review_id=rid,candidate_id=s['candidate_id'],dp_id=s['dp_id'],code=code,evidence=note,provisional=True,all_covering_orders_mapping_verified=q['mapping_supported'],covering_orders=q['covering_orders'],orders_seen=f['displayed_orders'],extracted_order_cutouts_inspected=len(shown),missing_full_cutout_orders=f['missing_full_cutout_orders'],unsupported_orders=q.get('unsupported_orders',[]),atlas_pages_inspected=[f['page']],figure=f['figure'],enlarged_figures=sorted({r['figure']for r in shown}),topocentric_air_angstrom=orders[0]['topocentric_air_angstrom']))
 source=['PLAN.json','VISUAL_REVIEW_PLAN.json','FOLLOWUP_FREEZE.json','SELECTED_EVENTS.csv','NATIVE_MAPPING.json','FIGURE_INDEX.json','FIBER_INVENTORY.json','primary_enlarged/render.py','primary_enlarged/DISPLAY_SCALES.json','primary_enlarged/save_review.py','figures/REVIEW_01.png','primary_enlarged/CENTRAL_01.png']
 r=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='COMPLETED_PRIMARY_AI_VISUAL_REVIEW',reviewer='batch05_primary',selected_events=2,selected_exposures=1,covering_order_records=2,extracted_order_cutouts_inspected=2,missing_full_cutouts=0,unavailable_events=0,atlas_pages_inspected=[1],central_pages_inspected=['primary_enlarged/CENTRAL_01.png'],counts={k:Counter(x['code']for x in events)[k]for k in 'AOUMN'},method='Actual inspection of the atlas for both selected events, both covering order cutouts, native profiles and one systematic fixed central +/-8-column, full31-row enlargement for both orders. Original counts and positive excess both inspected. No coordinate, method, selection or classifier threshold changed.',display_scales='primary_enlarged/DISPLAY_SCALES.json',independence='No secondary review or root-adopted labels read before saving this review. Primary reviewer also prepared and ran extraction; this is not an independent numerical audit.',limitations=['Post-detection AI visual judgments, not blinded scientific validation, human review or physical-origin proof.','A is provisional charge morphology for the selected component; additional underlying photon flux is not excluded.','Fixed side-background subtraction and nearby calibration-fiber signal limit interpretation of weak components.','No qualified laser candidate, calibrated null, global false-alarm rate or sensitivity claim follows.'],source_sha256={s:sha(ROOT/s)for s in source},events=events)
 (ROOT/'PRIMARY_VISUAL_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'counts':r['counts'],'sha256':sha(ROOT/'PRIMARY_VISUAL_REVIEW.json')},indent=2))
if __name__=='__main__':main()
