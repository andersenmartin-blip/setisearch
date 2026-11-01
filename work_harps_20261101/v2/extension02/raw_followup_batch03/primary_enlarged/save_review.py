"""Serialize independently recorded visual observations; no morphology classifier."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS = """
0085|O|Central enlargement shows a trace-centred, spatially spread, few-row photon-like enhancement, rather than a thin charge streak; native profile is compatible with a narrow line. Topocentric wavelength is consistent with O I 5577.338 A.
0086|U|Broad native bump and diffuse trace-confined raw enhancement; no unambiguous compact charge deposit is visible. The broad spectral structure remains unresolved.
0087|U|Broad enhancement is present in both orders 2 and 3; order 2 is noisier and order 3 is smoother. Raw enhancement follows the trace rather than a narrow off-trace streak.
0088|A|Sharp native spike accompanies a bright compact raw deposit several columns left of the order 64 trace; spatial offset and compactness support provisional charge contamination.
0089|U|Both orders 2 and 3 show broad native structure and diffuse central enhancement; neither establishes a clear charge morphology or a qualified narrow emission source.
0090|A|Enlargement resolves a very thin, bright deposit at row zero just left of the trace, superposed on a strongly curved background trace. The isolated native spike is consistent with this compact charge feature.
0091|A|A narrow raw streak extends from the trace to the right over several columns, with bright discrete segments; the native peak is sharply asymmetric.
0092|U|Weak, noisy native peak with diffuse central excess in the enlargement. The central feature does not establish a distinct charge trail or an O I identification.
0093|A|Enlargement shows a bright one-row horizontal deposit centred several columns left of the trace, with a much sharper spatial concentration than the trace itself.
0094|U|Broad native bump with a second nearby shoulder; raw enhancement remains trace-confined and diffuse. Spectral structure remains unresolved.
0095|U|Native peak extends over many dispersion samples and the raw enhancement is diffuse around the trace, with no distinct charge track.
0096|U|Broad native peak and nearby secondary structure accompany a weak, trace-confined raw excess; origin cannot be assigned from this morphology.
0097|A|Order 16 has an isolated narrow native spike and compact raw deposit; order 17 lacks a corresponding narrow peak, supporting charge contamination in one covering order.
0098|U|Broad structured native feature with a weak diffuse central raw enhancement; no clear compact charge morphology is established.
0099|A|A bright compact deposit lies right of the trace and connects to it through a thin row. Broader positive trace-confined structure is also present, so the charge interpretation does not exclude an underlying spectral blend.
0100|O|Central enlargement shows a spatially spread central enhancement over several dispersion rows, despite trace curvature in the background residual. Native profile and topocentric wavelength are compatible with O I 6300.304 A.
0101|A|Order 3 shows a sharp native spike and compact raw deposit; order 4 is noisier and does not reproduce the narrow spike.
0102|A|Order 4 contains a strong narrow spike and compact raw charge-like deposit, while order 3 lacks the matching narrow feature.
0103|A|Enlargement reveals a bright, thin horizontal deposit at the predicted row, concentrated left of the trace; the native profile is sharply peaked.
0109|A|A long diagonal raw charge trail crosses the order 2 trace and accompanies the narrow spike; covering order 1 does not reproduce the spike.
0110|U|Broad native bump and secondary spectral structure accompany only a weak diffuse central raw enhancement.
0111|O|A smooth trace-centred central enhancement spans several rows and columns, compatible with a photon line at O I 6300.304 A. A separate bright pixel at the upper-right edge is remote from the candidate centre.
0112|A|Central enlargement isolates a one-row bright deposit left of the trace, with an abrupt concentration inconsistent with the broader spatial trace profile.
0113|A|A short diagonal raw charge track crosses the order 2 trace; order 1 does not show a matching narrow native peak.
0114|U|Broad native enhancement is present in both orders 2 and 3, with diffuse trace-centred raw structure; the noisy overlap does not establish an origin.
0115|U|Both orders 3 and 4 show broad matching native peaks and spatially diffuse central enhancements, without a distinct charge track.
0116|U|Broad native peak with diffuse trace-confined raw enhancement; unresolved spectral structure remains.
0117|U|Broad smooth native peak and diffuse central raw enhancement; no isolated compact charge morphology is established.
0118|U|Both covering orders show a broad peak with nearby additional structure. Raw enhancement is trace-confined and does not isolate a charge deposit.
0119|U|Broad enhancement appears in both orders; order 2 is noisier and higher, but no clearly separate compact charge feature is established.
0120|U|Broad smooth peak agrees across orders 3 and 4, with diffuse raw enhancement near the trace.
0121|U|Broad native bump and diffuse trace-centred raw structure remain unresolved.
0122|U|Enlargement reveals an irregular, slightly displaced multi-row central excess, with a bright lower component and a weaker extension to the upper right. The weak flat-topped native enhancement and possible charge/photon mixture are insufficient for a clear A or O assignment.
0123|A|A thin horizontal deposit sits several columns left of the trace at the candidate row; the native feature is sharply peaked.
0124|U|Broad feature is present in both orders 2 and 3 with noisy overlap and diffuse central raw structure.
0125|U|Broad smooth native enhancement appears in both orders 3 and 4, without a clear compact deposit.
0126|U|Broad native peak spans many samples and the raw excess is diffuse and trace-confined.
0127|U|Broad native maximum and smooth central raw enhancement do not establish a distinct charge track or a narrow source identity.
0133|U|Both orders 2 and 3 show a broad peak; the noisier order 2 and smoother order 3 are consistent with unresolved broad spectral structure.
0134|U|Order 3 contains a broad smooth trace-centred enhancement. Order 2 has a remote bright pixel high and left of the candidate, but its central mean excess remains broad and weak; that remote deposit does not classify the central feature.
0135|U|Broad native profiles agree across orders 3 and 4. A remote off-trace pixel in order 3 is not the central feature, which remains diffuse.
0136|U|Broad native peak with a secondary nearby rise and weak diffuse raw enhancement remains unresolved.
0137|A|Enlargement resolves a compact bright deposit to the right of the trace at row approximately +1, with a short horizontal extension and a sharp native peak.
0138|U|Both orders contain a broad central enhancement; order 2 is very noisy while order 3 shows the smoother broad profile.
0139|U|Broad native peak and diffuse trace-centred raw enhancement remain unresolved.
0140|A|A bright deposit is confined predominantly to one dispersion row across a few central columns, with a very sharp native spike.
0141|A|The enlargement shows a long segmented diagonal charge trail crossing the trace from upper left to lower right.
0142|A|A compact, asymmetric multi-pixel deposit is concentrated in a narrow column left of the trace, with separate bright row components; it is substantially narrower spatially than the surrounding trace.
0143|A|A bright nearly single-pixel deposit sits just left of the trace and above row zero, accompanying the sharp isolated native spike.
0144|A|A short horizontal compact deposit lies just right of the trace below row zero, with abrupt native-profile edges.
0145|A|Enlargement resolves a short stepped charge pattern from a bright lower-left pixel to a thin central row, rather than a smooth spatial line image.
0146|A|Short diagonal charge structure crosses the candidate trace, with an additional separated compact deposit farther left; the native feature is narrow.
0147|A|A short diagonal staircase of bright pixels runs from the trace down to the right, accounting for the irregular few-sample native peak.
0148|A|Order 68 contains a thin compact horizontal deposit and a sharp native spike; order 67 lacks a matching spike.
0149|A|Central enlargement resolves a predominantly one-row bright deposit immediately left of the trace, with an isolated narrow native feature.
0150|A|Order 16 contains a bright compact cross-like deposit at the predicted centre and narrow native spike; order 15 does not reproduce that feature.
0151|A|Compact raw charge structure crosses the trace near row zero, with a sharply peaked native profile.
0152|A|A long, very thin horizontal raw streak crosses order 43 and produces its narrow spike; covering order 42 has no corresponding spike.
0153|A|A short compact horizontal deposit lies left of the trace just above row zero, coincident with the sharp native feature.
0154|A|Enlargement resolves a very thin central horizontal deposit with a sharp row concentration and narrow native spike.
0155|A|Order 54 shows a bright essentially single-row central deposit and sharp spike; order 53 lacks a corresponding native enhancement and shows only weaker residual structure.
0156|A|A short thin horizontal raw deposit is visible left of the trace above row zero, accompanying an asymmetric sharp native peak.
0157|A|A clear short diagonal sequence of bright pixels crosses the trace from upper left to lower right; the native spike has an asymmetric tail.
0158|M|Order 68 fails the all-covering-order mapping gate. Its displayed raw context contains diagonal and separated compact features, but morphology cannot override unsupported mapping.
0159|M|Full raw cutout for covering order 0 is unavailable at the edge; order 1 shows a compact bright deposit. Incomplete covering-order support requires M.
0160|M|Full raw cutout for covering order 0 is unavailable at the edge; order 1 contains compact deposits near the candidate. Incomplete covering-order support requires M.
0161|A|Order 2 contains a bright compact slanted deposit at the trace and sharp spike; the noisy order 3 does not reproduce a comparable narrow feature.
0162|A|A compact bright deposit crosses the trace with a short lower-right extension and a sharp native peak.
0163|A|A short asymmetric charge-like deposit crosses the trace near row zero and accompanies an isolated narrow spike.
0164|A|A short diagonal compact feature crosses order 25; order 26 does not reproduce its sharp native spike.
0165|A|A long nearly horizontal thin raw streak crosses order 43; order 42 lacks the associated narrow spike.
0166|O|Enlargement shows a spatially spread trace-centred enhancement spanning several rows, with a smooth few-sample native peak. Its topocentric wavelength is compatible with O I 5577.338 A.
0167|A|The central excess follows a thin stepped horizontal pattern across the trace, including a bright pixel to the lower right, rather than a smooth line image.
0168|O|A weak trace-centred enhancement spans several rows and columns amid curved-trace background residuals. Native profile and topocentric wavelength are compatible with O I 6300.304 A; origin remains provisional.
0169|M|Order 68 is unsupported by the required mapping gate; a short slanted raw feature is visible, but no origin assignment is made.
0170|M|Order 70 is unsupported by the mapping gate. A diagonal charge-like trail is visible in the displayed context but cannot replace the missing mapping support.
0184|M|Order 1 fails the required mapping gate. A compact bright deposit appears in that order while order 0 does not reproduce the spike; unsupported covering-order mapping requires M.
0185|M|Order 7 fails the mapping gate despite a visible compact central deposit; morphology is not adopted as origin evidence.
0186|A|Order 9 contains a bright thin horizontal deposit and a sharp native spike; order 8 lacks the matching narrow feature.
0187|A|Order 18 shows a compact central deposit and a separate diagonal trail farther upper-left; order 19 does not reproduce the narrow spike.
0188|A|A compact raw deposit lies just to the right of the trace near row zero, with a sharp native spike.
0189|A|Order 20 has a compact vertically short deposit just left and below the trace centre; the noisy order 21 does not reproduce the same narrow feature.
0190|A|A compact rectangular bright deposit lies just left of the trace above row zero, producing a narrow flat-topped native peak.
0191|A|Order 33 contains a thin horizontal deposit immediately left of the trace below row zero; order 32 lacks its sharp native spike.
0192|A|An extended shallow diagonal charge-like track runs across the trace toward the upper right, with a sharp asymmetric native peak.
0193|A|Enlargement resolves a compact bright deposit centred near the trace and confined to very few rows, with abrupt spatial and dispersion concentration.
0194|M|Order 50 fails the mapping gate. The native peak is near an O I region, but unsupported mapping prevents an O assignment; central morphology alone is not used to override this limit.
0195|M|Order 52 fails the mapping gate; a weak compact central feature accompanies the native spike, but origin remains unassigned.
0196|A|Enlargement resolves a bright one-row pixel left of the trace with a short horizontal extension through the trace, accompanying a sharp spike.
0197|A|A short stepped diagonal sequence of compact bright pixels crosses the trace; the native feature contains several narrow peaks.
0198|A|A thin horizontal deposit lies left of the trace at the candidate row, coincident with a sharp native spike.
0199|M|Order 67 fails the required mapping gate. A weak central raw feature is displayed, but the event remains mapping-limited.
0215|A|Order 20 contains a short thin slanted track through the trace and a sharp spike; order 19 lacks the corresponding spike.
0216|A|A compact vertically short raw deposit at the trace accompanies a sharp isolated native peak.
0217|A|Enlargement shows a very bright thin two-column deposit at the candidate row. A broader sloping native background is also present, but the narrow excess has clear charge-like morphology.
0218|A|A bright narrow deposit lies just right of the trace, concentrated primarily in a single dispersion row, with an abrupt native-profile edge.
0219|O|A weak diffuse central enhancement occupies several rows and columns amid substantial background fluctuations. The few-sample native peak and topocentric wavelength are compatible with O I 5577.338 A; this is a provisional compatibility label.
0220|A|A short diagonal stepped charge track runs from lower left into the trace and accompanies the sharp native spike.
0221|O|A spatially spread central enhancement occupies several dispersion rows, with an asymmetric but resolved native peak. Its topocentric wavelength is compatible with O I 6300.304 A; weak background/trace residuals limit origin certainty.
0222|A|A long shallow diagonal raw charge track crosses the trace from upper left toward row zero, explaining the sharp native excess.
0223|M|Order 68 fails the mapping gate. A compact horizontal central deposit is visible but cannot establish an origin under the covering-order rule.
0229|U|Both orders show a broad enhancement; order 2 is substantially noisier, while order 3 has smooth diffuse trace-centred structure.
0230|A|Order 3 has a very bright compact stepped deposit and sharp spike atop broader structure. Order 4 has a much weaker diffuse broad enhancement, so an underlying spectral blend is possible even though the sharp spike is charge-contaminated.
0231|U|Broad profiles occur in both orders 3 and 4; the noisier order 4 has a split peak, but the raw images do not establish an isolated compact charge deposit at the candidate.
0232|A|A long bright diagonal charge trail crosses order 7; the noisy order 6 does not reproduce the sharp spike.
0233|A|Central enlargement resolves a bright predominantly one-row deposit immediately left of the trace below row zero, with a sharply asymmetric native peak.
0234|U|Order 2 has highly unstable low-background native normalization and large noise excursions; order 3 shows a broad diffuse enhancement. The raw images do not establish a distinct compact charge source for the candidate.
0235|U|Enlargement shows a compact asymmetric multi-row patch just below and left of the trace. Its sharp spatial edge is charge-like, but the patch also spans several dispersion rows; retain U because a clear isolated charge track versus a photon/charge mixture is not resolved.
0236|U|Broad native enhancement is present in both orders 2 and 3 with diffuse trace-centred raw structure and stronger noise in order 2.
0237|U|Order 2 has large noisy native excursions and unstable normalization, while order 3 has a smooth broad peak. Central raw structure is diffuse rather than a clear charge track.
0238|M|Order 4 fails the mapping gate. Both displayed orders show broad central enhancement, but the all-covering-order rule requires M.
0239|A|Order 5 contains a compact stepped bright deposit at the trace and sharp spike; noisy order 6 does not reproduce that narrow peak.
0240|A|Enlargement shows a long shallow diagonal charge streak crossing the trace, with bright segments on both sides and a sharp native spike.
0241|A|A long thin horizontal charge streak extends from the left edge through the candidate row and trace; its off-trace segments are distinct from the bright stellar continuum.
0242|A|A bright thin horizontal deposit lies several columns left of the trace, connected by a weaker row toward the trace; the weak native peak remains sharply asymmetric.
"""

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manual={}
    for line in OBSERVATIONS.strip().splitlines():
        suffix,code,evidence=line.split('|',2)
        rid='V2E2-'+suffix
        assert rid not in manual
        manual[rid]=(code,evidence)
    mapping=json.loads((ROOT/'NATIVE_MAPPING.json').read_text())
    figures=json.loads((ROOT/'FIGURE_INDEX.json').read_text())
    scales=json.loads((ROOT/'primary_enlarged/DISPLAY_SCALES.json').read_text())
    selected=list(csv.DictReader((ROOT/'SELECTED_EVENTS.csv').open()))
    assert set(manual)=={r['review_id']for r in selected}
    bymap={r['review_id']:r for r in mapping['events']}
    byfig={r['review_id']:r for r in figures}
    events=[]
    for s in selected:
        rid=s['review_id'];m=bymap[rid];f=byfig[rid];code,evidence=manual[rid]
        orders=[r for r in mapping['orders']if r['review_id']==rid]
        seen=[r['order']for r in orders if r['status']=='EXTRACTED']
        assert seen==f['displayed_orders']
        assert (code=='M')==(not m['mapping_supported'])
        e=dict(review_id=rid,candidate_id=s['candidate_id'],dp_id=s['dp_id'],code=code,evidence=evidence,
               all_covering_orders_mapping_verified=m['mapping_supported'],covering_orders=m['covering_orders'],
               orders_seen=seen,missing_full_cutout_orders=f['missing_full_cutout_orders'],unsupported_orders=m['unsupported_orders'],
               figure=f['figure'],enlarged_figures=sorted({r['figure']for r in scales['index']if r['review_id']==rid}),provisional=True)
        if rid in {'V2E2-0099','V2E2-0122','V2E2-0230','V2E2-0235'}:
            e['possible_blend']=True
        if code=='O':
            wave=orders[0]['topocentric_air_angstrom'];ref=min([5577.338,6300.304,6363.776],key=lambda x:abs(x-wave))
            e.update(topocentric_air_angstrom=wave,oi_reference_air_angstrom=ref,oi_offset_angstrom=wave-ref)
        events.append(e)
    assert len(events)==115 and len({r['dp_id']for r in events})==32
    assert sum(len(e['orders_seen'])for e in events)==155
    assert sum(len(e['covering_orders'])for e in events)==157
    out=dict(created_utc=datetime.now(timezone.utc).isoformat(),status='COMPLETED_PRIMARY_INDEPENDENT_AI_VISUAL_REVIEW',
             reviewer='batch03_visual_a',selected_events=115,selected_exposures=32,covering_order_records=157,
             extracted_order_cutouts_inspected=155,missing_full_cutouts=2,atlas_pages_inspected=list(range(1,30)),
             central_pages_inspected=sorted({r['figure']for r in scales['index']}),
             counts={c:sum(e['code']==c for e in events)for c in ['A','O','U','M','N']},
             method='Actual image inspection of all 29 frozen atlas pages, covering every one of the 155 available raw cutouts and native profiles. Fixed central +/-8-column displays inspected on all eight enlargement pages (43 covering-order panels for 40 events); original arrays and coordinates retained. Per-order display scales are recorded in primary_enlarged/DISPLAY_SCALES.json and reproduced by render.py. Enlargements are post-hoc display aids only, with no numerical extraction or classifier/selection threshold tuning.',
             independence='Judgments recorded and saved without reading batch03 secondary reviewer output or any batch03 adopted morphology labels. Parent provided availability and mapping-gate status only. This AI review is independent of the second AI pass but is not blinded external or human validation.',
             code_legend={'A':'Clear provisional charge-like contamination in the reviewed candidate context; no particle/instrument-origin proof.',
                          'O':'Topocentric O I-compatible wavelength and photon-like trace morphology; provisional compatibility, not proven sky origin.',
                          'U':'Broad, ambiguous, noisy, blended, or unresolved morphology requiring further interpretation.',
                          'M':'At least one covering order lacks required mapping support or a full cutout; morphology cannot override this gate.',
                          'N':'Raw/companion pair unavailable.'},
             limitations=['AI visual inspection is not calibrated classifier performance, human validation, or proof of physical origin.',
                          'Bright calibration-fibre features dominate many full-width displays; central enlargement reduces that scale problem but does not remove background, trace-curvature, or faint-feature uncertainty.',
                          'Positive excess uses the frozen background convention; original raw counts were also inspected, and subtraction residuals alone are not origin evidence.',
                          'A can coexist with an underlying broad spectral component; possible blends are explicitly retained for 0099, 0122, 0230 and 0235.',
                          'All 12 mapping-limited events remain M, including two events missing the full edge cutout for order 0.',
                          'O labels establish compatibility only; neither sky origin nor an artificial/laser source is proven. No qualified laser candidate is declared.'],
             source_sha256={str(p.relative_to(ROOT)):sha(p)for p in [ROOT/'PLAN.json',ROOT/'VISUAL_REVIEW_PLAN.json',ROOT/'FOLLOWUP_FREEZE.json',ROOT/'SELECTED_EVENTS.csv',ROOT/'NATIVE_MAPPING.json',ROOT/'FIGURE_INDEX.json',ROOT/'primary_enlarged/render.py',ROOT/'primary_enlarged/DISPLAY_SCALES.json']},events=events)
    (ROOT/'PRIMARY_VISUAL_REVIEW.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'counts':out['counts'],'events':len(events),'inspected_cutouts':155,'enlargement_panels':scales['order_panels']},indent=2))

if __name__=='__main__':
    main()
