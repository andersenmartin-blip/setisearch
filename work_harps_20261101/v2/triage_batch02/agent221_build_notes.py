"""Assemble explicit visual decisions; this is not an automatic classifier.

All REVIEW21-40 assigned panels, FOCUS09-15, and separate AGENT221_DETAIL
figures were visually inspected. The categorical choices below are manual.
Mapping audit text and panel references are appended mechanically.
"""
from pathlib import Path
import json, collections, hashlib, datetime

OUT = Path(__file__).resolve().parent
decisions = """
221|M|Broad blue-region feature in orders2/3, with very noisy order2 and stronger normalized order2 amplitude. No raw origin assignment because the local registration check fails.
222|A|Sharp spike occurs only in order54, with a compact one-row raw charge feature; overlapping order53 follows the smooth continuum without the spike.
223|A|Almost single-point native spike with a compact raw excess narrower than the continuum fiber profile.
224|A|Sharp asymmetric native spike with a compact raw charge feature just below and left of the predicted center.
225|A|Very narrow native spike coincides with a short slanted compact raw charge feature near the fiber.
226|A|Narrow asymmetric native peak has a sloping raw feature extending several dispersion rows and across the fiber, inconsistent with the smooth continuum trace.
227|U|Broad noisy peak occurs in both blue orders2/3; raw excess extends along the registered fiber in both. Spectral origin remains unassigned.
228|M|Very sharp native spike is present in order57 but absent in order58. The incomplete local check in order58 prevents a raw-based event origin assignment under the frozen conservative rule.
229|A|Long diagonal raw charge track crosses the fiber at an almost single-point native spike.
230|U|Broad peak and nearby minima/secondary structure agree in blue orders2/3, with excess on the registered fibers; origin unresolved.
231|M|Broad peak appears in orders2/3, with noisier order2; candidate-excluded continuum support is insufficient for the required local checks.
232|M|Order2 is extremely noisy while order3 shows a broader peak. Incomplete candidate-excluded registration support prevents an origin assignment.
233|M|Broad structured peak appears in both orders18/19; the order18 edge prevents the required two-sided local registration check.
234|A|Sharp single-point native spike coincides with a compact raw core and a short transverse one-row extension.
235|M|Sharp spike is present in order52 but absent in order53. The incomplete order53 local mapping check prevents a raw-based event origin assignment.
236|A|Narrow few-point native spike coincides with a nearly single-pixel raw charge feature at the fiber.
237|A|Sharp native spike with a compact raw charge feature offset slightly above the fiber crossing; adjacent-fiber light does not explain this central compact excess.
238|U|Broad peak occurs in both blue orders2/3, although order2 is noisy. Both raw panels show fiber-aligned excess; origin remains unresolved.
239|U|Broad asymmetric peak with neighboring maxima and troughs in order3; raw excess follows the fiber over several dispersion rows.
240|A|Sharp high spike is confined to order6, with a compact raw pixel event; overlapping order5 lacks the spike and is dominated by ordinary noisy structure.
241|U|Noisy order2 and clearer broad order3 peak. Focused raw display reveals weak noisy fiber-region structure in order2 and a wider on-fiber feature in order3; no clean particle morphology explains the common feature.
242|U|Broad order3 peak and very noisy larger order2 peak occur at the same center, with extended fiber-aligned excess; no origin assigned.
243|M|Broad peak appears in both blue orders2/3. The required candidate-excluded local continuum support is incomplete.
244|M|Order2 has extreme normalized fluctuations and a much smaller broad order3 peak. Incomplete local reference support prevents an origin decision; large normalized height is not evidence of intrinsic luminosity.
245|U|Broad peak appears in both orders3/4, with fiber-aligned raw excess and no clear transverse charge track at the common feature.
246|A|Narrow native spike coincides with a diagonal raw charge segment extending to the left of the registered fiber.
247|A|Narrow native spike coincides with a slanted raw charge feature displaced to the right of the registered continuum. Focused raw counts confirm the continuum remains centered while this feature lies off-center.
248|A|Narrow two-point native top with a long shallow diagonal raw charge track crossing the fiber.
249|A|Sharp native peak with an isolated compact raw charge feature slightly right and below the fiber center.
250|A|Sharp spike appears only in order51 and has a transverse one-row raw charge feature; overlapping order50 lacks the spike.
251|A|Two close sharp native maxima coincide with a short diagonal charge segment across the fiber.
252|A|Sharp native spike with a compact sloping raw charge event at the fiber crossing.
253|A|Sharp native spike with a nearly one-pixel raw charge feature several columns left of the fiber. Focused original counts verify the continuum trace is centered independently of the displaced event.
254|A|Sharp native spike with a compact approximately one-column, two-row raw charge feature near the fiber.
255|A|Single narrow native spike with compact raw excess to the left of the continuum trace; the bright adjacent fiber is spatially separate.
256|A|Narrow native spike coincides with an almost single-pixel raw event at the fiber.
257|A|Sharp asymmetric native spike coincides with a long sloping raw charge trail through the fiber.
258|A|Narrow spike on broader spectral structure, with a diagonal raw track through the fiber; the narrow excess is provisionally attributed to a detector artifact.
259|A|Sharp native spike with compact raw charge excess displaced several columns right of the fiber.
260|M|Broad similar peak in orders2/3. Required candidate-excluded continuum support is missing on one side, so no raw origin assignment is made.
261|U|Broad peak appears in both orders2/3 with neighboring trough and fiber-aligned raw excess; origin unresolved.
262|U|Broad asymmetric peak in both blue orders2/3, larger/noisier in order2, with extended on-fiber raw excess.
263|M|Broad structured peak agrees in orders2/3, but the required local mapping windows are incomplete after candidate exclusion.
264|U|Broad peak occurs in both orders3/4, with extended fiber-aligned raw excess and no clear particle trail at the common feature.
265|U|Smooth broad order19 peak lies between neighboring troughs, with extended on-fiber raw excess; origin not assigned.
266|M|Broad peak appears in both blue orders2/3; missing candidate-excluded reference support prevents the required local check.
267|U|Broad peak appears in both orders2/3. Order3 also contains a much brighter compact off-center raw event; a display saturated at the95th percentile reveals the underlying broader fiber-aligned feature in both orders. Mixed contamination is possible; the common spectral feature remains unresolved.
268|M|Broad peak with neighboring structure agrees in orders2/3, but local continuum support is incomplete under the frozen criteria.
269|U|Broad peak agrees in orders3/4, with extended fiber-aligned raw excess in both orders.
270|U|Smooth broad order19 peak between neighboring troughs, with extended raw excess centered on the registered fiber.
271|U|Broad blue peak appears in both orders2/3 with a neighboring absorption trough and on-fiber raw excess.
272|M|Broad asymmetric peak in both blue orders2/3; one required local continuum side lacks sufficient samples.
273|M|Broad noisy peak occurs in orders2/3; order2 lacks the required one-sided continuum support, so the event remains mapping-limited despite a usable order3 check.
274|M|Noisy broad order2 peak and lower smoother order3 peak. Both orders have incomplete candidate-excluded continuum support.
275|U|Broad somewhat asymmetric peak appears in both orders3/4, with noisy but extended fiber-aligned raw excess.
276|U|Smooth broad order19 peak and adjacent troughs, with an extended centered raw profile.
277|M|Broad asymmetric blue feature occurs in orders2/3; local continuum checks are incomplete after neighboring-candidate exclusion.
278|M|Broad blue peak occurs in orders2/3; the required local reference side is absent in both orders.
279|M|Broad blue peak occurs in both orders, with noisier order2; local reference samples are insufficient on one side in both orders.
280|M|Broad noisy peak with adjacent spectral structure appears in orders2/3; both local checks lack sufficient candidate-free samples.
281|M|Noisy broad order2 peak and lower smoother order3 peak; incomplete candidate-free reference windows prevent an origin assignment.
282|U|Broad peak occurs in both orders3/4 with noisy but fiber-aligned raw excess.
283|U|Smooth broad order19 feature lies between troughs; raw excess is extended and centered on the fiber.
284|M|Broad noisy peak appears in orders2/3, but the order2 local continuum maximum violates the fixed positional criterion. No raw origin assigned.
285|U|Broad peak in order3 and larger noisier order2 feature. Order2 contains a compact off-center raw event that dominates its initial scale; the saturated detail still shows weaker surrounding structure. Possible particle contamination superposed on a shared spectral feature; do not classify the whole event as a confirmed artifact.
286|U|Broad common order2/3 feature with an extra sharper point in noisy order2. Focused raw display shows extended on-fiber emission and no unambiguous separate track; possible contamination remains unresolved.
287|U|Broad peak in order3 and sharper, higher noisy top in order4. Both central raw panels show fiber-region excess but order4 is noisy; the origin of the common feature and sharper contribution remain unresolved.
288|A|Sharp native spike coincides with a compact near-single-pixel raw charge excess at the fiber.
289|U|Broad noisy peak in both orders3/4 with centered raw excess; no clear transverse particle trail explains the shared feature.
290|A|Sharp spike is confined to order34, with compact raw charge excess at the fiber; overlapping order33 lacks the spike.
291|A|Sharp narrow native spike coincides with a tilted raw charge track extending through the cutout and crossing the fiber, rather than following the continuum profile.
292|A|Narrow two-point native spike coincides with a compact slanted raw charge feature at the fiber.
293|A|Sharp native spike with a short diagonal raw charge segment crossing the fiber.
294|A|Sharp native spike coincides with a shallow sloping raw charge track extending far to the left of the fiber.
295|A|Sharp native spike with a compact slanted raw charge feature left of the fiber; nearby extended spectral light is spatially distinct from this compact event.
296|A|Narrow native peak with a transverse/sloping raw charge feature extending left of the continuum trace.
297|A|Sharp native spike with nearly single-pixel raw excess at the fiber center.
298|A|Sharp native spike with compact raw charge excess displaced just right of the fiber.
299|A|Two sharp adjacent native maxima coincide with a short diagonal raw charge segment crossing the fiber.
300|A|Very narrow native spike with a compact approximately one-column raw event at the fiber.
301|A|Sharp native spike with compact slanted raw excess just above and left of the fiber center.
302|A|Narrow asymmetric native peak with a compact raw charge feature at the fiber, spatially distinct from broader neighboring spectral structure.
303|A|Sharp narrow native peak with a compact approximately one-row raw charge feature just above the fiber crossing.
304|A|Narrow native peak with a compact off-center raw feature and faint transverse extension toward the fiber. Focused raw counts confirm the continuum is centered independently of the displaced charge feature.
305|U|Broad multipeak structure in order3 with a neighboring secondary peak and trough; raw excess is extended along the fiber.
306|M|Sharp spike appears in order63 but not order64. The order64 edge prevents the required local check, so no raw-based event origin is assigned.
307|A|Narrow two-point native top coincides with a transverse raw charge streak extending across and away from the fiber.
308|A|Narrow asymmetric native peak with a slanted raw charge segment offset left of the fiber and crossing its vicinity.
309|U|Broad multipeak structure in order3, similar in shape to V2-0305; extended raw excess follows the fiber. Shape similarity is descriptive, not an origin identification.
310|A|Sharp native spike with a compact off-center raw pixel feature and a faint horizontal extension toward the fiber. Focused counts confirm an independently centered continuum trace.
311|U|Broad order3 peak with neighboring secondary peak/trough and extended fiber-aligned raw excess; origin unresolved.
312|A|Sharp native spike coincides with a nearly single-pixel raw excess at the fiber.
313|U|Broad structured order3 peak with neighboring maxima/minima, with extended centered raw excess; origin unresolved.
314|A|Narrow native spike with a compact diagonal charge feature to the left of the registered trace.
315|A|Sharp native spike with a compact one-row raw event at the fiber.
316|A|Sharp native spike with compact slanted raw excess near the fiber, narrower than the continuum profile.
317|A|Sharp asymmetric native spike with an isolated compact raw charge feature just below and left of the fiber.
318|A|Sharp native peak with a nearly one-pixel raw excess at the fiber crossing.
319|A|Very narrow two-point native top coincides with a compact one-row raw charge feature at the fiber.
320|A|Sharp large spike occurs in order1 with a compact raw event; overlapping order2 is noisy and lacks a comparable sharp spike.
321|A|Sharp native spike with a short diagonal compact charge segment extending left of the fiber.
322|M|Broad noisy peak appears in orders2/3; the order2 edge leaves insufficient local continuum samples on one side.
323|A|Narrow native spike with a transverse slightly sloping raw charge segment crossing the fiber.
324|A|Sharp native spike coincides with a compact diagonal charge feature left of the fiber.
325|A|Sharp native spike with a compact approximately one-row raw charge feature at the fiber.
326|M|Narrow spike is present only in order64, while order63 lacks it. Too few order64 local reference samples prevent a raw-based event origin assignment.
327|A|Sharp native spike coincides with compact raw charge excess just left of the fiber.
328|A|Sharp narrow native peak with a long shallow raw charge trail across the fiber and a bright off-center end.
329|A|Sharp spike on top of a broader native feature, with a long diagonal raw track crossing the fiber; the narrow excess is provisionally a detector artifact.
330|A|Narrow two-point native top coincides with a diagonal raw charge segment through the fiber.
331|A|Sharp native spike with compact raw charge excess at the fiber and a small slanted extension.
332|A|Sharp narrow native top with a short transverse raw charge streak extending right of the fiber.
333|M|Sharp asymmetric native spike retained. The local reference window at the order edge has too few samples; no raw-based origin assignment despite a compact slanted feature in the displayed cutout.
""".strip()

notes = {}
mapping = json.loads((OUT / 'NATIVE_MAPPING.json').read_text())
audit = json.loads((OUT / 'LOCAL_TRACE_AUDIT.json').read_text())
focus = {x['review_id']: x for x in json.loads((OUT / 'FOCUS_INDEX.json').read_text())}
detail = {x['review_id']: x for x in json.loads((OUT / 'AGENT221_DETAIL_INDEX.json').read_text())}
for line in decisions.splitlines():
    num, code, reason = line.split('|', 2)
    i = int(num)
    hid = f'V2-{i:04d}'
    orders = [x for x in mapping['orders'] if x['review_id'] == hid]
    assert orders and all(x['status'] == 'EXTRACTED' for x in orders)
    failed = [x for x in audit['orders'] if x['review_id'] == hid and not x['local_mapping_usable']]
    assert (code == 'M') == any(not x['mapping_verified'] for x in orders)
    if code == 'M':
        pieces = []
        for a in failed:
            sides = []
            for name, w in zip(['left', 'right'], a['windows']):
                if w['samples'] < 60:
                    sides.append(f'{name} side {w["samples"]} samples (<60)')
                elif abs(w['peak_offset']) > 1:
                    sides.append(f'{name} continuum peak offset {w["peak_offset"]:+.3f} pixels (outside +/-1)')
            pieces.append(f'order{a["order"]}: ' + ', '.join(sides))
        reason += ' Mapping limitation: ' + '; '.join(pieces) + '.'
    reason += f' Viewed REVIEW_{(i-97)//6+1:02d}, panel{(i-97)%6+1}, all covering orders ' + '/'.join(str(x['order']) for x in orders) + '.'
    if hid in focus:
        f = focus[hid]
        reason += f' Also FOCUS_{f["page"]:02d}, row{f["row"]}.'
    if hid in detail:
        f = detail[hid]
        reason += f' Also AGENT221_DETAIL_{f["page"]:02d}, row{f["row"]}.'
    if i in [267, 285]:
        reason += ' Also AGENT221_DETAIL_SATURATED, positive excess clipped for display at its95th percentile; arrays unchanged.'
    notes[num] = [code, reason]

assert set(notes) == {str(i) for i in range(221,334)}
(OUT / 'agent_review_221_333.json').write_text(json.dumps(notes, indent=2) + '\n')
summary = dict(
    created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    reviewer='Separate subagent visual first-pass review; not independent human research validation',
    reviewed_range=[221,333], reviewed_events=len(notes),
    counts=dict(collections.Counter(x[0] for x in notes.values())),
    inspected_pages=dict(review=list(range(21,41)), focus=list(range(9,16)), additional_detail=[1,2,3], saturated_detail=True),
    scope='Only assigned events221-333, every covering extracted order; original detector, catalog and inputs unchanged.',
    interpretation='All categorical judgments provisional. M controls registration usability only, not astrophysical origin. A does not certify a specific particle mechanism. U may include natural structure and mixed contamination.',
    hashes={name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['agent_review_221_333.json','MAPPING_PLAN.json','NATIVE_MAPPING.json','LOCAL_TRACE_AUDIT.json']})
(OUT / 'agent_review_221_333_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
