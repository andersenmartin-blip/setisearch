"""Serialize manually recorded secondary image judgments; not a classifier."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv, hashlib, json

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Notes recorded after actual viewing of all 24 atlas pages and all nine
# fixed-central enlargement pages. No primary/adopted judgments were read.
notes = {
243: ('A', 'o68 has a narrow native spike and a thin, stepped excess extending many columns across the trace; the enlarged view resolves a charge-like track.'),
244: ('O', 'o50 has a weak, few-sample native enhancement at topocentric air 5577.347244804177 A. The central enlargement shows a small multi-row, trace-centered excess with a spatial profile compatible with the fiber. This supports provisional OI/photon compatibility only; the weak signal and adjacent residual structure do not prove sky origin.'),
245: ('A', 'o69 has a two-sample native feature and a narrow horizontal deposit concentrated in about one dispersion row, slightly right of the trace, resolved in the central view.'),
246: ('A', 'o58 has a sharp native spike and a thin stepped diagonal deposit crossing the trace and extending rightward; the central view separates it from broader background residuals.'),
247: ('A', 'o69 has a small native feature and a compact staircase of bright pixels just right of the trace, with a short thin extension leftward. The central view supports a localized charge deposit rather than a smooth fiber-shaped patch.'),
248: ('A', 'o61 shows a narrow native spike with a long thin inclined deposit, becoming brightest well right of the fiber and continuing toward the trace.'),
249: ('M', 'o70 was displayed, but its frozen five-window/global mapping gate is unsupported. Visible context cannot establish the selected event origin.'),
250: ('A', 'o63 has a short native double feature; the central view resolves a very narrow column of bright pixels on the left flank of the fiber, spatially unlike the ordinary trace profile.'),
251: ('A', 'The native spike appears in o65, whose central view shows a thin diagonal deposit from the left flank through the trace. o66 has no matching narrow native spike or matching deposit; both orders were inspected.'),
252: ('A', 'o50 has a sharp native spike and detached compact pixels several columns to the right of the trace, including a bright small patch near the event row and separated lower pixels.'),
253: ('A', 'o54 has a sharp native spike and an approximately single-row horizontal deposit across the central/right trace pixels, distinct from the wider curved trace-background residual.'),
254: ('A', 'o58 has a sharp native spike and a long nearly horizontal stepped excess extending across the central crop well beyond the fiber width.'),
255: ('A', 'o49 contains the native spike and a narrow sequence of separated bright pixels along one column on the right trace flank. o48 has no matching spike or localized event deposit; both orders were inspected.'),
256: ('A', 'o51 shows a sharp native spike and a thin off-trace deposit left of the fiber that extends toward its flank; the central spatial curve has an off-trace bump.'),
257: ('A', 'o69 has an extremely concentrated bright central deposit with a single-row/dominant-pixel core and sharply peaked spatial excess, accompanying a sharp native spike. This is provisional charge-like morphology.'),
258: ('A', 'o48 has a sharp native spike and a thin compact horizontal deposit on the right fiber flank. The central view resolves its limited dispersion extent and offset spatial peak.'),
259: ('M', 'o70 was displayed, but its frozen mapping gate is unsupported. No morphology assignment is made for the selected event.'),
260: ('U', 'Both o2 and o3 show a broad rounded native feature with smooth trace-centered multi-row excess. This is broader spectral/photon-like structure of unresolved origin.'),
261: ('U', 'Both native orders o2/o3 contain broad structure. o2 also has a bright compact off-trace charge-like deposit to the right, while o3 retains a clear broad trace-centered patch. The off-trace deposit does not explain away the broad two-order feature; possible contamination/blend remains explicit.'),
262: ('U', 'o2 and o3 both show a broad native enhancement and a smooth trace-confined excess patch; no isolated charge morphology explains the shared broad structure.'),
263: ('U', 'o2/o3 show rounded broad native peaks and trace-centered, multi-row raw patches in both orders. Physical origin remains unresolved.'),
264: ('U', 'o2/o3 contain a broad spectral enhancement amid neighboring structure, with diffuse trace-confined raw excess in both orders.'),
265: ('U', 'o3/o4 show a broad rounded or flat-topped native feature with diffuse trace-centered raw patches. Its broad spectral origin remains unresolved.'),
266: ('U', 'o2/o3 have broad rounded native peaks and centered raw patches spanning several dispersion rows; both orders support unresolved broad structure.'),
267: ('U', 'o2/o3 have broad somewhat asymmetric multi-sample native enhancements with centered raw patches. Neither order supplies a clear isolated charge explanation.'),
268: ('U', 'o2/o3 show broad rounded native features and smooth trace-centered raw excess; the broad structure remains unresolved.'),
269: ('U', 'o2/o3 show a noisier, weaker but shared broad enhancement and trace-confined raw context. Low contrast limits a more specific interpretation.'),
270: ('U', 'o3/o4 show a broad rounded asymmetric native peak and coherent diffuse trace-centered patches in both orders.'),
271: ('U', 'o19 contains a smooth broad native feature between neighboring troughs and a broad trace-confined raw enhancement. This remains unresolved spectral structure.'),
272: ('U', 'o2/o3 contain broad structure. o2 has noisier sharper substructure, but both raw panels show broad centered patches; isolated charge morphology is not established.'),
273: ('U', 'o2/o3 show a broad centered native enhancement and diffuse trace-following raw patches in both orders.'),
274: ('U', 'o3/o4 contain broad native structure. The central views show a bright broad trace patch in o3 and a weaker centered patch in o4; o4 also has a separated off-trace bright pixel near the upper left. That contamination does not explain the shared broad feature.'),
275: ('U', 'o2/o3 display a coherent broad native enhancement and trace-centered raw patches, preserving unresolved broad spectral structure.'),
276: ('U', 'o2/o3 display a broad rounded enhancement and diffuse centered excess in both covering orders; origin is unresolved.'),
277: ('U', 'o2/o3 share broad spectral structure with trace-confined raw patches. There is no clear isolated deposit accounting for the broad feature.'),
278: ('U', 'o2/o3 have noisy low blue continuum and unequal amplitudes, with weaker broader trace-centered structure most apparent in o3. The evidence remains ambiguous, not a secure charge assignment.'),
279: ('U', 'o3/o4 show a broad rounded coherent native peak and corresponding centered raw patches; the broad component remains unresolved.'),
280: ('M', 'Covering order o0 has no full cutout because of an edge truncation. Available o1 shows a diagonal charge-like track, but absence of the required o0 context retains the record as mapping-limited.'),
281: ('U', 'o2/o3 show broad weak structure with noisier narrow substructure in o2. Enlargements show noisy multi-row trace-centered excess in o2 and a clearer broad centered patch in o3, without a clear detached charge deposit.'),
282: ('U', 'o2 has a noisy narrow component on a weak broader feature; o3 has a broad trace-centered patch. Both central views remain consistent with weak/noisy trace structure, and do not establish a charge-only explanation.'),
283: ('U', 'o2/o3 have very noisy low blue continuum, with broader structure in o3 and weak trace-centered raw patches. The low-contrast feature remains unresolved.'),
284: ('A', 'o53 has a narrow native feature and a thin ascending diagonal trail from well left of the fiber toward its central pixels, clearly resolved in the enlargement.'),
285: ('A', 'o33 contains the narrow native spike and an inclined track extending rightward beyond the trace. o34 has no comparable narrow native spike or track; both central views were inspected.'),
286: ('A', 'o40 has a sharp spike over a sloping native continuum and an approximately single-row two-pixel bright central deposit, resolved in the enlargement.'),
287: ('A', 'o1 has a very sharp native spike with a thin single-row deposit extending rightward from the trace, including a concentrated off-trace bright component.'),
288: ('A', 'o55 shows a narrow native feature and an obvious thin ascending diagonal trail to the right of the trace, rather than a trace-confined photon patch.'),
289: ('U', 'o54 has a small flat-topped two-sample native feature. The fixed central enlargement is dominated by curved trace/background residuals; the weak near-center excess is not resolved as an unambiguous isolated charge deposit or a secure photon-shaped line. Retain unresolved.'),
290: ('M', 'o69 context was displayed, but the frozen mapping gate is unsupported; no event-origin assignment is supported.'),
291: ('A', 'o60 has a narrow native spike and a compact two-step deposit on the right trace flank, with its strongest pixels shifted from the fiber center.'),
292: ('A', 'o38 contains the native spike and a conspicuous curved/stepped deposit to the left of the trace. o37 lacks the corresponding narrow spectral event; both raw orders were inspected.'),
293: ('A', 'o59 has a short native double feature and a very bright compact block left of the fiber; the central spatial excess is strongly displaced and sharply peaked.'),
294: ('A', 'o61 has a sharp native spike and a thin horizontal one-row excess across several central/right pixels, separated in the enlargement from broader background residuals.'),
295: ('M', 'o66 is displayed but the frozen mapping support gate fails; visible localized morphology cannot establish the selected event origin.'),
296: ('M', 'o68 is displayed but the frozen mapping support gate fails. No event-origin assignment is made.'),
297: ('M', 'o68 is displayed but the frozen mapping support gate fails. Localized visible context does not override that limitation.'),
298: ('M', 'o69 is displayed but the frozen mapping support gate fails. No event-origin assignment is made.'),
299: ('M', 'o70 shows track-like raw structure, but the frozen mapping support gate fails. The selected event remains mapping-limited.'),
300: ('M', 'o70 shows track-like raw structure, but the frozen mapping support gate fails. The selected event remains mapping-limited.'),
301: ('A', 'o57 contains the native spike and a thin horizontal deposit spanning the center and right trace flank. o56 has no matching narrow spike or deposit; both enlarged orders were inspected.'),
302: ('A', 'o63 has a weak native feature; the central view resolves a thin stepped diagonal excess from the left off-trace region toward the trace, distinct from its broad background curvature.'),
303: ('U', 'o3 contains a broad rounded native feature with neighboring structure and a diffuse trace-centered raw patch. The broad component remains unresolved.'),
304: ('A', 'o62 has a very sharp native spike and a short approximately single-row central deposit, with a small step between its brightest pixels.'),
305: ('U', 'o3 contains a broad rounded native feature amid neighboring structure and a smooth trace-centered raw patch. It remains unresolved.'),
306: ('A', 'o62 has a short flat-topped native feature and a compact detached bright spot several columns right of the trace, resolved in the central view.'),
307: ('A', 'o70 shows a two-sample native feature and a compact stepped pair of bright pixels right of the fiber center; its spatial excess is displaced.'),
308: ('U', 'o3 shows a smooth broad native enhancement with neighboring spectral structure and a diffuse centered raw patch; origin is unresolved.'),
309: ('U', 'o3 shows a broad native enhancement and a diffuse trace-centered raw patch, without a distinct charge deposit accounting for it.'),
310: ('A', 'o56 has a narrow native peak and a thin short deposit well left of the fiber, stepping toward its flank. The enlargement resolves the offset structure.'),
311: ('A', 'o70 has a sharp native spike and a very concentrated near-single-row central pixel deposit, with a narrow spatial excess peak.'),
312: ('M', 'Covering order o0 lacks a full cutout because of edge truncation. Available o1 shows a compact charge-like event, but the missing required order retains mapping-limited status.'),
313: ('A', 'o35 has a sharp native event and a conspicuous stepped/diagonal deposit crossing the trace and extending beyond the fiber width.'),
314: ('A', 'o63 has a sharp native peak and a thin stepped nearly horizontal charge-like track crossing the trace and extending on both sides.'),
315: ('A', 'o64 has a sharp native spike and a long thin descending diagonal track extending from the left off-trace region through the predicted event position.'),
316: ('A', 'o69 has a sharp native spike and a nearly single-row horizontal deposit extending to both sides of the trace, unlike the broader fiber profile.'),
317: ('A', 'o14 contains the large narrow native spike and a thin horizontal off-center deposit. o13 shows only ordinary broad trace structure without the corresponding spike; both orders were inspected.'),
318: ('A', 'o66 shows a sharp native spike and a bright stepped horizontal deposit at and to the right of the trace, with very limited dispersion extent.'),
319: ('U', 'o3 has noisy broad multi-sample native structure and a centered multi-row raw patch. It remains unresolved broad blue structure.'),
320: ('A', 'o16 has the large native spike and an obvious thin diagonal track through the trace. o15 lacks the corresponding narrow spike and shows normal trace/background structure.'),
321: ('A', 'o24 contains the sharp native spike and a long nearly horizontal single-row track extending right of the trace. o25 has no corresponding narrow spike; both covering orders were inspected.'),
322: ('A', 'o56 has a sharp native feature over adjacent absorption structure and a prominent long diagonal track crossing the trace.'),
323: ('A', 'o70 has a sharp native feature and a bright short descending stepped track to the right of the trace, clearly unlike a smooth centered photon patch.'),
324: ('A', 'o54 has a sharp native spike and a dominant central pixel with very limited row extent; the enlarged spatial excess is much narrower than the ordinary fiber profile.'),
325: ('A', 'o61 has a sharp native spike. Removing the outer calibration-fiber region from the display reveals a thin one-row deposit from the left trace flank across its center.'),
326: ('A', 'o69 has a short native double feature and a compact bright central pixel/short row deposit, resolved independently of the bright outer calibration-fiber pixels.'),
327: ('A', 'o65 has a sharp native spike; the central view reveals a long thin shallow descending track across the fiber, otherwise obscured by the outer bright calibration-fiber scale.'),
328: ('A', 'o65 has a narrow native feature and an approximately single-row central deposit with a narrow, slightly offset spatial excess peak.'),
329: ('A', 'o64 has a sharp native spike and a thin horizontal stepped deposit extending far right of the trace; the enlargement resolves its off-trace continuation.'),
330: ('A', 'o64 has a small two-sample native feature and a compact bright pixel left of the fiber near the selected row, accompanied by a thin low-level extension toward the trace.'),
331: ('A', 'o65 has narrow peaks over a sloping/absorbed native background. The central view shows a thin stepped diagonal deposit on the left fiber flank, with discrete bright pixels; broad background structure is not assigned an origin.'),
332: ('N', 'The selected record is retained, but the frozen product pair is unavailable after two HTTP 503 HEAD attempts. The atlas explicitly shows unavailable context; no native/raw morphology was available to assess.'),
333: ('N', 'The selected record is retained, but the frozen product pair is unavailable after two HTTP 503 HEAD attempts. The atlas explicitly shows unavailable context; no native/raw morphology was available to assess.'),
334: ('A', 'o61 has a sharp native spike and a short thin stepped deposit across the trace center, revealed by the fixed central enlargement.'),
335: ('A', 'o63 has a small native peak adjacent to a deep broad absorption feature. The central view resolves a compact one-column/two-row bright deposit on the right trace flank with a sharply displaced spatial excess. This supports a charge-like contribution to the selected peak; it does not assign the neighboring broad structure an origin.'),
336: ('M', 'o70 was displayed and contains thin off-trace structure, but its frozen mapping gate is unsupported. The selected record remains mapping-limited.'),
}

mapping = json.loads((OUT/'NATIVE_MAPPING.json').read_text())
atlas = json.loads((OUT/'FIGURE_INDEX.json').read_text())
central = json.loads((HERE/'INDEX.json').read_text())
atlas_by_id = {r['review_id']:r for r in atlas}
central_by_id = {}
for r in central['records']:
    central_by_id.setdefault(r['review_id'], []).append(r)
selected = list(csv.DictReader((OUT/'SELECTED_EVENTS.csv').open()))
assert len(notes) == 94 and set(notes) == set(range(243,337))
assert len(mapping['events']) == len(atlas) == len(selected) == 94
assert {r['review_id'] for r in selected} == {r['review_id'] for r in mapping['events']}
reviewed_orders=[]
for r in mapping['orders']:
    if r['status'] == 'EXTRACTED':
        assert sha(OUT/r['cutout']) == r['cutout_sha256']
        a=atlas_by_id[r['review_id']]
        assert r['order'] in a['displayed_orders']
        reviewed_orders.append(dict(review_id=r['review_id'],order=r['order'],cutout=r['cutout'],cutout_sha256=r['cutout_sha256'],atlas_figure=a['figure'],atlas_row=a['row']))
assert len(reviewed_orders)==122
records=[]
for event in mapping['events']:
    rid=event['review_id']; code,evidence=notes[int(rid.split('-')[1])]
    a=atlas_by_id[rid]
    unavailable=event['status']=='NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE'
    assert (code=='N') == unavailable
    assert (code=='M') == (not event['mapping_supported'] and not unavailable)
    assert code in ['M','N'] or event['mapping_supported']
    assert event['covering_orders']==a['covering_orders']
    records.append(dict(review_id=rid,dp_id=event['dp_id'],code=code,evidence=evidence,covering_orders=event['covering_orders'],all_covering_orders_mapping_verified=event['mapping_supported'],native_mapping_status=event['status'],unsupported_orders=event.get('unsupported_orders',[]),edge_truncated_orders=event.get('edge_truncated_orders',[]),atlas_pages_inspected=[a['page']],atlas_figure=a['figure'],atlas_row=a['row'],extracted_orders_reviewed=a['displayed_orders'],missing_full_cutout_orders=a['missing_full_cutout_orders'],central_enlargements=[dict(figure=x['figure'],row=x['row'],order=x['order'])for x in central_by_id.get(rid,[])],contamination_or_blend_caution=int(rid.split('-')[1])in[261,274],additional_uncertainty=int(rid.split('-')[1])in[244,269,278,281,282,283,289,331,335]))
source_paths=['PLAN.json','VISUAL_REVIEW_PLAN.json','FOLLOWUP_FREEZE.json','SELECTED_EVENTS.csv','NATIVE_MAPPING.json','FIGURE_INDEX.json','secondary_enlarged/render.py','secondary_enlarged/INDEX.json','secondary_enlarged/save_review.py']
figures=[f'figures/REVIEW_{i:02d}.png'for i in range(1,25)]
enlargements=[f'secondary_enlarged/CENTRAL_{i:02d}.png'for i in range(1,10)]
result=dict(created_utc=datetime.now(timezone.utc).isoformat(),reviewer='secondary independent AI visual reviewer /root/batch04_visual_b',status='ACTUAL_VISUAL_REVIEW_COMPLETED',independence='All judgments were recorded from the saved atlas and independently rendered fixed central enlargements before reading any primary review or adopted labels. Selected sample and prior scientific context were known; this is not blinded scientific validation or human review.',scope=dict(selected_events=94,selected_exposures=37,available_exposures=36,atlas_pages=24,covering_order_records=124,extracted_order_cutouts=122,edge_truncated_orders=2,unavailable_records=2),method='Actual inspection of every record on all 24 frozen atlas pages, including original raw counts, positive excess and native spectra in every available covering order. Additionally inspected all 51 panels on nine central enlargement pages. The enlargement uses all 31 rows and fixed central columns 8:25 of each unchanged 31x33 cutout; all scales and cutout hashes are logged in secondary_enlarged/INDEX.json. No sample, mapping, classifier threshold or extraction was changed. Labels below are manually recorded descriptive judgments.',codebook=dict(A='Provisional detector charge-like morphology',O='Provisional OI wavelength plus photon-compatible morphology; not proven sky origin',U='Unresolved broad, ambiguous or potentially blended structure',M='At least one covering order lacks required verified mapping/full cutout',N='Native/raw product pair unavailable; no morphology assessment'),counts=dict(sorted(Counter(r['code']for r in records).items())),atlas_pages_inspected=list(range(1,25)),atlas_figures_inspected=figures,central_enlargement_pages_inspected=enlargements,central_enlargement_order_panels_inspected=51,extracted_orders_reviewed=reviewed_orders,extracted_orders_reviewed_count=122,unavailable_review_ids=['V2E2-0332','V2E2-0333'],contamination_or_blend_review_ids=['V2E2-0261','V2E2-0274'],explicit_weak_red_unresolved_review_ids=['V2E2-0289'],source_sha256={p:sha(OUT/p)for p in source_paths},figure_sha256={p:sha(OUT/p)for p in figures+enlargements},limits=['A and O are provisional morphology compatibility judgments, not physical-origin proofs.','Broad two-order features remain unresolved even if one raw panel also contains a separate off-trace charge-like deposit.','No qualified laser candidate, calibrated null result, global false-alarm rate or sensitivity follows from this descriptive post-detection review.','The two AI-agent reviews are not independent human validation or blinded scientific validation.','Bright outer calibration-fiber pixels affect whole-cutout display contrast; fixed central enlargements are display aids only.'],records=records)
(OUT/'SECONDARY_VISUAL_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(counts=result['counts'],records=len(records),cutouts_verified=len(reviewed_orders),central_panels=51,review_sha256=sha(OUT/'SECONDARY_VISUAL_REVIEW.json')),indent=2))
