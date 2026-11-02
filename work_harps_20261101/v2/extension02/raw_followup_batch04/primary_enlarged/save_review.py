"""Serialize primary judgments made after actual atlas and central-image inspection.

The notes below are independent visual judgments, not a numerical classifier.
No secondary review or root-adopted label was consulted before this was saved.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]

# Explicit observations recorded during the primary visual pass.
NOTES = {
243: ('A', 'Thin, slightly sloping one-row deposit crosses the trace in order 68, accompanying the narrow native spike; central enlargement exposes the charge-like geometry hidden by the full-frame scale.'),
244: ('O', 'Weak rounded native feature in order 50 and a noisy but trace-centered, several-pixel spatial excess are photon-compatible; no clear thin off-trace track or isolated charge pixel is resolved. Topocentric 5577.347245 A is +0.009245 A from OI 5577.338 A. OI-compatible only, with uncertain physical origin and no sky-fiber validation.'),
245: ('A', 'Order 69 has a short, very thin horizontal central deposit just below the predicted row, accompanying a narrow/double native peak.'),
246: ('A', 'Central enlargement of order 58 reveals a thin horizontal-to-sloping deposit extending rightward across the trace, accompanying the narrow native spike.'),
247: ('A', 'Order 69 shows a compact bright pixel about two columns right of the trace, with short thin connecting structure; the weak native bump has charge-like spatial context.'),
248: ('A', 'Order 61 shows a compact off-trace deposit about five columns right of the trace with a thin angled connection toward the extraction trace.'),
249: ('M', 'Order 70 contains a compact central pixel-like excess, but its frozen mapping gate is unsupported; visible morphology cannot override the mapping limitation.'),
250: ('A', 'Order 63 contains a compact one-column, few-row deposit to the left of the trace near the candidate row; native sharp structure and the asymmetric compact deposit support provisional charge morphology.'),
251: ('A', 'Order 65 has a thin stepped track crossing the trace and the sharp native feature; overlapping order 66 lacks that sharp feature and lacks the central track. Both orders were inspected.'),
252: ('A', 'Order 50 has separated compact bright deposits several columns right of the trace near and below the candidate row, unlike a trace-centered photon profile; the candidate is at 5581.432406 A, not the 5577 OI line.'),
253: ('A', 'Order 54 has a thin short horizontal deposit crossing the central trace, visible after removal of full-cutout calibration-dominated scaling.'),
254: ('A', 'Order 58 has a long, almost horizontal one-row track spanning the trace and reaching both sides of the fixed central display.'),
255: ('A', 'Sharp native feature and compact vertically stepped one-column deposits occur in order 49; overlapping order 48 has no matching sharp feature or central deposit. Both orders were inspected.'),
256: ('A', 'Order 51 shows a short sloping thin track left of the trace, with a bright compact segment and faint continuation toward the trace; broader native background structure remains contextual.'),
257: ('A', 'Order 69 has a very bright saturated compact central deposit with a much narrower cross-dispersion profile than the continuum trace.'),
258: ('A', 'Order 48 contains a thin short central-row deposit with its brightest pixel offset about two columns right of the trace.'),
259: ('M', 'Order 70 shows weak thin central-row structure, but the frozen mapping gate is unsupported; retain M irrespective of that morphology.'),
260: ('U', 'Orders 2 and 3 both show a broad native feature and diffuse trace-centered excess across several dispersion rows. The feature is photon-compatible but its origin remains unresolved.'),
261: ('U', 'Broad trace-centered emission remains in order 3 and weakly in order 2. Order 2 additionally contains a bright compact off-trace deposit near column +7 at the candidate row; possible contamination/blending is explicit and does not dispose of the broader centered component.'),
262: ('U', 'Both orders 2 and 3 show broad native structure and diffuse trace-centered excess; order 2 is noisier and weaker. No unique charge morphology explains the shared broad component.'),
263: ('U', 'Order 2 is noisy, while order 3 has a clear diffuse trace-centered patch and broad native profile; both covering orders were inspected and the shared broad feature remains unresolved.'),
264: ('U', 'Weak broad native structure is present in orders 2 and 3, with diffuse central excess and nearby spectral structure; origin cannot be assigned from the photon-like morphology.'),
265: ('U', 'Orders 3 and 4 contain a broad native feature and several-row trace-centered patch; the weaker order 4 remains photon-compatible and unresolved.'),
266: ('U', 'Orders 2 and 3 show a broad centered feature with diffuse raw excess, weaker and noisier in order 2; no clear track accounts for the shared component.'),
267: ('U', 'Order 2 has noisy diffuse central excess and order 3 has a broader smooth trace-centered patch. The native feature remains unresolved after both orders were inspected.'),
268: ('U', 'Broad native feature and diffuse central patch occur in both orders 2 and 3; noisy order 2 pixels do not establish a compact charge explanation.'),
269: ('U', 'Order 2 is very weak and noisy, and order 3 has a diffuse centered patch with a broader native bump. The available morphology is insufficient for a physical-origin assignment.'),
270: ('U', 'Both orders 3 and 4 show a broad native profile with a several-row photon-compatible trace-centered patch; no decisive charge morphology is present.'),
271: ('U', 'Single covering order 19 shows a strong broad rounded native feature and diffuse trace-centered excess extending over several dispersion rows; origin remains unresolved.'),
272: ('U', 'Orders 2 and 3 both show broad trace-centered morphology, with lower contrast and more noise in order 2; no clear isolated charge component explains the feature.'),
273: ('U', 'Both overlapping orders 2 and 3 contain a broad native feature and diffuse central excess; the noisy blue order does not warrant an artifact assignment.'),
274: ('U', 'Orders 3 and 4 retain a broad centered feature. A separate compact bright pixel near column -8 and row +12 in order 4 dominates its display scale, but does not explain the centered component also seen in order 3; nearby charge contamination is noted without collapsing the unresolved feature.'),
275: ('U', 'Weak diffuse centered excess in order 2 accompanies a clearer broad photon-compatible patch in order 3; both native profiles remain broader than a single-pixel event.'),
276: ('U', 'Orders 2 and 3 show broad centered structure with differing signal levels; the noisy order 2 image and smoother order 3 patch leave the origin unresolved.'),
277: ('U', 'Order 2 is extremely weak and noisy; order 3 shows a weak diffuse central patch and broader native feature. The overlap does not establish an artifact or physical origin.'),
278: ('U', 'Order 2 is near the noise/background level and order 3 retains a weak broad trace-centered feature. Morphology and order-to-order amplitude differences remain uncertain.'),
279: ('U', 'Orders 3 and 4 both show a broad native feature with diffuse trace-centered excess; the weaker order 4 does not supply a unique charge morphology.'),
280: ('M', 'Available order 1 shows a long diagonal charge-like trail crossing the trace, but covering order 0 lacks a complete edge cutout and has unsupported mapping. All-covering-order validation fails, so retain M.'),
281: ('U', 'Order 2 is very noisy and order 3 has a broad, diffuse trace-centered patch. The differing native shapes do not establish a unique charge explanation for the broader feature.'),
282: ('U', 'Order 2 has only very weak, noisy central excess with a sharper-looking native fluctuation; order 3 retains diffuse broader centered excess. The possible mixture/noisy morphology remains unresolved.'),
283: ('U', 'Order 2 is weak and noisy, while order 3 has a faint several-row centered patch. Native structure and raw context are insufficient to identify the origin.'),
284: ('A', 'Order 53 has a thin diagonal track rising from the left toward the predicted trace, with discrete bright segments and a sharp native feature.'),
285: ('A', 'Order 33 has a sloping thin track extending rightward from the trace and the sharp native feature; overlapping order 34 lacks the matching sharp feature and central track.'),
286: ('A', 'Order 40 contains a very thin bright central-row deposit over about two columns, accompanying the sharp native spike on a broader continuum gradient.'),
287: ('A', 'Order 1 contains a bright nearly single-pixel deposit just right of the predicted trace at the candidate row, together with a very narrow native spike.'),
288: ('A', 'Order 55 has an extended thin sloping track to the right of the trace with a bright compact segment, accompanying the narrow native feature.'),
289: ('U', 'The weak flat-topped native bump in order 54 has only a faint, poorly separated central excess against strong continuum/background-gradient residuals. The fixed central enlargement does not reveal a sufficiently clear isolated charge pixel, track, or secure photon profile; retain ambiguous morphology.'),
290: ('M', 'Order 69 has compact thin pixels right of the trace near the candidate row, but its frozen five-window mapping support fails. Retain M.'),
291: ('A', 'Order 60 has a small stepped two-pixel deposit just right of the predicted trace and at the candidate row, narrower than the continuum spatial profile.'),
292: ('A', 'Order 38 shows a curved thin track approaching the trace from the left with a sharp native feature; overlapping order 37 lacks that sharp feature and track.'),
293: ('A', 'Order 59 contains a saturated compact block offset left of the trace, only a few pixels across, dominating the native sharp/double peak; the deposit is much narrower than a photon spatial profile.'),
294: ('A', 'Order 61 has a short thin central-row deposit with a compact bright right-hand pixel, accompanying a sharp native feature.'),
295: ('M', 'Order 66 contains a bright compact pixel left of the trace, but its frozen mapping gate is unsupported; no origin class is adopted.'),
296: ('M', 'Order 68 contains a bright compact central-row deposit, but its frozen mapping gate is unsupported; retain M.'),
297: ('M', 'Order 68 shows a long thin sloping track spanning the trace, but the frozen mapping support fails; visible charge-like morphology does not override M.'),
298: ('M', 'Order 69 shows separated compact central-row deposits, but the frozen mapping support fails; retain M.'),
299: ('M', 'Order 70 has a long diagonal thin track crossing the trace; frozen mapping support is nevertheless unsupported, so retain M.'),
300: ('M', 'Order 70 has a long diagonal thin track rising from the left toward the trace; the unsupported frozen mapping gate requires M.'),
301: ('A', 'Order 57 has a thin horizontal central-row deposit and the sharp native feature; overlapping order 56 lacks the matching sharp feature and charge track. Both were inspected.'),
302: ('A', 'Order 63 central enlargement reveals a short oblique stepped track crossing from left of the trace toward the center, despite the weak native bump and calibration-dominated full image.'),
303: ('U', 'Order 3 has a broad native feature, a diffuse trace-centered central patch and nearby spectral structure. The photon-compatible morphology leaves its physical origin unresolved.'),
304: ('A', 'Order 62 contains a thin two-column central-row deposit just left of the trace, accompanying the sharp native spike.'),
305: ('U', 'Order 3 shows a broad native profile and a diffuse several-row centered patch with neighboring structure; morphology alone cannot assign the origin.'),
306: ('A', 'Order 62 has a compact one-column/few-row deposit about four columns right of the trace near the candidate row; it is distinctly offset and narrower than the continuum profile.'),
307: ('A', 'Order 70 has a short stepped compact deposit about two columns right of the trace, corresponding to the narrow/double native feature.'),
308: ('U', 'Order 3 contains a broad centered photon-compatible patch and neighboring native/raw spectral structure; no decisive charge track identifies the feature.'),
309: ('U', 'Order 3 contains a broad native feature and a diffuse centered patch over several rows, with adjacent spectral structure; origin remains unresolved.'),
310: ('A', 'Order 56 shows a short thin stepped track left of the trace at the candidate row, exposed by the central enlargement.'),
311: ('A', 'Order 70 contains a compact bright central-row pixel with short thin wings, accompanying the sharp native feature.'),
312: ('M', 'Order 1 shows a compact central charge-like deposit, but the other covering order 0 lacks a complete edge cutout and has unsupported mapping; retain M.'),
313: ('A', 'Order 35 contains a thin diagonal deposit extending from the left into the trace, with bright central pixels and a sharp native feature.'),
314: ('A', 'Order 63 shows a thin gently curved/sloping track across the trace with an offset bright pixel, supporting provisional charge morphology.'),
315: ('A', 'Order 64 has an extended diagonal thin track crossing the trace from upper left to lower right; the sharp native feature is coincident with that track.'),
316: ('A', 'Order 69 has a nearly horizontal one-row track across the trace, with multiple compact bright segments.'),
317: ('A', 'Sharp native component occurs in order 14 with a thin horizontal/stepped deposit extending left of the trace. Overlapping order 13 has broader background spectral structure but no matching sharp spike or thin track. The A judgment concerns the sharp component, not all underlying photon flux.'),
318: ('A', 'Order 66 contains a thin row-like deposit extending from the trace toward the right, spatially asymmetric and narrower than the continuum profile.'),
319: ('U', 'Order 3 shows a weak broad native bump and a noisy diffuse trace-centered patch; neighboring spectral structure and low contrast leave the origin unresolved.'),
320: ('A', 'Order 16 has a long diagonal track crossing the trace and the sharp native spike; overlapping order 15 lacks that sharp component and instead has broader unrelated spectral structure.'),
321: ('A', 'Order 24 contains an extended nearly horizontal track crossing the trace with a sharp native spike; overlapping order 25 lacks the sharp spike and track, showing only broader background structure.'),
322: ('A', 'Order 56 has a long diagonal thin track traversing the trace, superposed on a continuum/absorption gradient; provisional charge morphology applies to the narrow selected feature.'),
323: ('A', 'Order 70 contains a short sloping thin deposit extending from the trace toward the right below the central row, coincident with the narrow native spike.'),
324: ('A', 'Order 54 has a bright nearly single-pixel central-row deposit, much narrower than the continuum spatial profile.'),
325: ('A', 'Order 61 central enlargement reveals a thin short horizontal central-row deposit despite the calibration-dominated full atlas scale.'),
326: ('A', 'Order 69 has a compact bright central-row pixel with short thin wings and an additional offset faint pixel; the narrow native feature has clear charge-like context.'),
327: ('A', 'Order 65 has a long thin gently sloping track across the trace, exposed by the fixed central display despite strong off-trace calibration pixels in the full cutout.'),
328: ('A', 'Order 65 has a thin short central-row deposit with a bright center and rightward extension, accompanying a sharp native spike.'),
329: ('A', 'Order 64 contains a thin track extending along the candidate row from the trace to a compact bright deposit on the far right of the central display.'),
330: ('A', 'Order 64 contains a compact bright pixel about three columns left of the trace, with faint thin row-like continuation toward the center; this charge-like morphology accompanies the weak narrow/flat-topped native feature.'),
331: ('A', 'Order 65 central enlargement reveals a short sloping stepped track left of and entering the trace, accompanying asymmetric narrow native structure on a broader gradient.'),
332: ('N', 'No raw/product pair is available after the frozen metadata omission following two HTTP503 HEAD attempts. The unavailable notice was inspected on atlas page 23; no raw morphology or origin assessment is possible.'),
333: ('N', 'No raw/product pair is available after the frozen metadata omission following two HTTP503 HEAD attempts. The unavailable notice was inspected on atlas page 23; no raw morphology or origin assessment is possible.'),
334: ('A', 'Order 61 contains a thin short stepped central-row deposit accompanying the sharp native spike; the feature is visible in the central display despite bright off-trace calibration pixels.'),
335: ('A', 'Order 63 contains a compact bright one-column/few-row deposit just right of the trace, much narrower in the spatial direction than the continuum profile. Native absorption structure remains contextual; the topocentric center 6299.060462 A is not coincident with OI 6300.304 A.'),
336: ('M', 'Order 70 shows a long thin sloping track crossing the trace, but the frozen mapping gate is unsupported; retain M irrespective of the visible charge-like morphology.'),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    mapping = json.loads((ROOT/'NATIVE_MAPPING.json').read_text())
    figures = json.loads((ROOT/'FIGURE_INDEX.json').read_text())
    scales = json.loads((ROOT/'primary_enlarged/DISPLAY_SCALES.json').read_text())
    selected = list(csv.DictReader((ROOT/'SELECTED_EVENTS.csv').open()))
    by_event = {r['review_id']: r for r in mapping['events']}
    by_figure = {r['review_id']: r for r in figures}
    assert len(selected) == len(NOTES) == 94
    assert set(NOTES) == set(range(243,337))
    extracted = [r for r in mapping['orders'] if r['status'] == 'EXTRACTED']
    assert len(extracted) == 122
    for order in extracted:
        assert sha(ROOT/order['cutout']) == order['cutout_sha256']
    assert {(x['review_id'],x['order']) for x in extracted} == {(x['review_id'],x['order']) for x in scales['index']}
    events = []
    for s in selected:
        rid = s['review_id']; q = by_event[rid]; f = by_figure[rid]
        code, evidence = NOTES[int(rid.split('-')[-1])]
        assert (code == 'N') == (q['status'] == 'NOT_RAW_REVIEWED_PRODUCT_PAIR_UNAVAILABLE')
        assert (code == 'M') == (not q['mapping_supported'] and code != 'N')
        orders = [x for x in mapping['orders'] if x['review_id'] == rid]
        shown = [x for x in scales['index'] if x['review_id'] == rid]
        assert sorted(x['order'] for x in shown) == sorted(f['displayed_orders'])
        rec = dict(review_id=rid,candidate_id=s['candidate_id'],dp_id=s['dp_id'],code=code,
                   evidence=evidence,provisional=True,
                   all_covering_orders_mapping_verified=q['mapping_supported'],
                   covering_orders=q['covering_orders'],orders_seen=f['displayed_orders'],
                   extracted_order_cutouts_inspected=len(shown),
                   missing_full_cutout_orders=f['missing_full_cutout_orders'],
                   unsupported_orders=q.get('unsupported_orders',[]),
                   atlas_pages_inspected=[f['page']],figure=f['figure'],
                   enlarged_figures=sorted({x['figure'] for x in shown}),
                   topocentric_air_angstrom=orders[0]['topocentric_air_angstrom'] if orders else None)
        if code == 'O':
            rec['oi_reference_air_angstrom'] = 5577.338
            rec['oi_offset_angstrom'] = rec['topocentric_air_angstrom'] - 5577.338
        events.append(rec)
    counts = {x:Counter(r['code'] for r in events)[x] for x in 'AOUMN'}
    source_files = ['PLAN.json','VISUAL_REVIEW_PLAN.json','FOLLOWUP_FREEZE.json','SELECTED_EVENTS.csv',
                    'NATIVE_MAPPING.json','FIGURE_INDEX.json','FIBER_INVENTORY.json',
                    'primary_enlarged/render.py','primary_enlarged/DISPLAY_SCALES.json',
                    'primary_enlarged/save_review.py']
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  status='COMPLETED_PRIMARY_INDEPENDENT_AI_VISUAL_REVIEW',reviewer='batch04_visual_a',
                  selected_events=94,selected_exposures=len({r['dp_id'] for r in selected}),
                  covering_order_records=len(mapping['orders']),extracted_order_cutouts_inspected=122,
                  missing_full_cutouts=2,unavailable_events=2,
                  atlas_pages_inspected=list(range(1,25)),
                  central_pages_inspected=[f'primary_enlarged/CENTRAL_{i:02d}.png' for i in range(1,22)],
                  counts=counts,
                  method='Actual independent inspection of all 24 atlas pages, all 94 selected records and every one of the 122 extracted covering-order cutouts. All 21 fixed central +/-8-column, full-31-row enlargement pages were additionally inspected. Both original counts and positive excess were considered alongside the native profiles and descriptive spatial context. Missing edge orders and unavailable pairs remain explicit. No coordinate, numerical method, selection or classifier threshold was changed.',
                  display_scales='primary_enlarged/DISPLAY_SCALES.json',
                  independence='No secondary review or root-adopted labels were read before this primary review was saved.',
                  limitations=[
                      'These are post-detection AI visual judgments, not blinded scientific validation, human review or physical-origin proof.',
                      'Full-cutout scales can be dominated by calibration-fiber pixels; fixed central enlargements were inspected systematically for every available order.',
                      'Positive excess depends on the frozen side-background subtraction; spatial gradients and noisy low-contrast features remain interpretive limitations.',
                      'A is provisional charge morphology for the selected narrow component, not proof that all nearby photon flux is instrumental.',
                      'O requires both OI-compatible topocentric wavelength and photon-compatible morphology; no independent sky-fiber validation is implied.',
                      'U preserves broad, noisy, ambiguous or potentially blended features. In particular, 0261 retains a broad centered component despite off-trace charge contamination; 0274 retains a centered component despite a separate distant compact pixel.',
                      'M retains every event with any unsupported or missing covering order. N retains both omitted product-pair events without any origin assessment.',
                      'No qualified laser candidate, calibrated null, global false-alarm rate or sensitivity claim follows from this review.'
                  ],
                  source_sha256={x:sha(ROOT/x) for x in source_files},events=events)
    assert result['selected_exposures'] == 37
    assert result['covering_order_records'] == 124
    assert sum(counts.values()) == 94
    (ROOT/'PRIMARY_VISUAL_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'counts':counts,'sha256':sha(ROOT/'PRIMARY_VISUAL_REVIEW.json'),
                      'unresolved_ids':[r['review_id'] for r in events if r['code']=='U'],
                      'oi_ids':[r['review_id'] for r in events if r['code']=='O']},indent=2))

if __name__ == '__main__':
    main()
