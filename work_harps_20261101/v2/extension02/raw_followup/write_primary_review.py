"""Record the primary AI-agent visual judgments made on all17 neutral pages."""
from pathlib import Path
import csv,json,datetime,hashlib,collections
O=Path(__file__).resolve().parent
E=list(csv.DictReader((O/'SELECTED_EVENTS.csv').open()));M=json.loads((O/'NATIVE_MAPPING.json').read_text());I={r['review_id']:r for r in json.loads((O/'FIGURE_INDEX.json').read_text())}
notes={}
def add(prefix,ids,code,note):
 for n in ids:
  key=prefix+'-'+str(n).zfill(4);assert key not in notes;notes[key]=(code,note)
add('V1E2',[1],'O','Narrow native peak; raw excess spans the science trace rather than a single cross-dispersion pixel. Position consistent with O I5577; adjacent bright calibration-fiber structure is distinct. No independent sky control.')
add('V1E2',[2],'A','Compact charge-like core concentrated into a single cross-dispersion pixel near the trace, narrower spatially than the continuum. Same raw event as V2E2-0106.')
add('V1E2',[3],'I','Prescribed local mapping incomplete in at least one overlapping order. A diagonal off-trace streak crosses the other order and only that order has the sharp peak; artifact concern retained without declaring full raw mapping verified.')
add('V1E2',[4],'A','Large compact/double-peaked charge in one overlapping order; corresponding peak absent in other order. Same raw feature as V2E2-0171.')
add('V1E2',[5],'O','Trace-compatible distributed raw excess and narrow native structure near O I6300; same event as V2E2-0212. B is calibration, so atmospheric origin remains provisional.')
add('V1E2',[6],'O','Raw excess spans the science-fiber profile and multiple dispersion rows near O I5577; same event as V2E2-0226. No independent sky control.')
add('V2E2',[1],'I','Useful order2 shows a blue spectral hump; overlapping low-flux order3 is noisy and prescribed mapping incomplete. Do not transfer a ghost origin from another exposure or wavelength coincidence.')
add('V2E2',[2,4,6,7,9,10],'A','Compact one-row or few-pixel charge-like excess, spatially narrower than the continuum or offset from its center; some cases have a transverse tail. Raw morphology supports a provisional detector artifact.')
add('V2E2',[3,8],'O','Native structure near O I6300 with raw excess distributed over the science trace. Nearby calibration-fiber peak is spatially distinct. No independent sky control; atmospheric interpretation provisional.')
add('V2E2',[5,59,62],'A','Sharp excess appears in only one overlapping order; its raw image contains compact charge or a short off-trace tail while the companion order lacks the corresponding feature.')
add('V2E2',[60],'O','Trace-compatible narrow structure near O I5577, same raw event as V1E2-0001. Position and morphology support provisional atmosphere, not independent confirmation.')
add('V2E2',[61,64],'A','A slanted off-trace charge track reaches/crosses the science trace at the extracted peak.')
add('V2E2',[63],'A','One-dispersion-row transverse charge structure crosses the broader continuum trace; provisional detector artifact.')
add('V2E2',[104],'U','Broad structured peak appears consistently in both overlapping orders; raw illumination follows both science traces. No clear compact-charge signature; physical spectral origin unresolved.')
add('V2E2',[105],'A','Diagonal charge track crosses the science trace at the narrow peak. A broader native spectral hump may coexist; this judgment does not assign every surrounding count to the artifact.')
add('V2E2',[106],'A','Same compact raw charge-like feature as V1E2-0002; concentrated cross-dispersion core relative to continuum.')
add('V2E2',[107],'A','Clear long slanted charge trail crosses the science trace at the candidate position.')
add('V2E2',[108],'A','Compact bright core displaced to one side of the science continuum; spatially concentrated charge-like morphology.')
add('V2E2',[128,130,131],'I','Broad photon-compatible spectral/raw structure is visible, but prescribed local mapping support fails for at least one required order/window. Keep insufficient mapping separately from any physical-origin interpretation.')
add('V2E2',[129],'U','Smooth broad structure repeats in both overlapping orders and follows science-fiber illumination. Spectral origin unresolved; no compact detector-hit morphology apparent.')
add('V2E2',[132],'I','Same feature as V1E2-0003: diagonal off-trace streak and one-order-only sharp peak, with incomplete prescribed local mapping. Artifact concern retained but incomplete status preserved.')
add('V2E2',[171],'A','Same one-order compact/double charge feature as V1E2-0004; no corresponding peak in other covering order.')
add('V2E2',[172,178,180],'A','Strong peak in one overlapping order only; raw compact or transverse charge structure crosses that trace. The companion order does not corroborate the peak.')
add('V2E2',[173],'A','Diagonal charge trail in one overlapping order; the other order lacks the sharp spectral peak.')
add('V2E2',[174,175,176,177,182,183],'A','Compact charge-like core or thin transverse bar, narrower than continuum and/or displaced in cross-dispersion; provisional detector artifact.')
add('V2E2',[179],'O','O I5577-position structure with raw excess distributed across the science trace rather than an isolated charge pixel; atmosphere provisional without sky fiber.')
add('V2E2',[181],'A','Long diagonal track crosses the science trace and extends well off it; clear detector-artifact concern.')
add('V2E2',[200],'A','Narrow compact excess in only one covering order, confined spatially relative to the continuum; companion order lacks peak.')
add('V2E2',[201,202,203,205,207,209,210,211,213,214],'A','Compact charge core or short diagonal/transverse track at or beside the science trace. Morphology differs from the broader continuum illumination; provisional detector artifact.')
add('V2E2',[204],'O','Weak native excess near O I5577 is distributed along the science-fiber spatial profile; no isolated dominating charge core. Atmosphere provisional without independent sky.')
add('V2E2',[206],'A','Long diagonal off-trace charge track intersects one order, with a sharp peak absent from the overlapping order.')
add('V2E2',[208,225,228],'I','One-order-only compact charge concern is visible, but at least one overlapping order fails the prescribed local mapping criterion. Insufficient mapping remains the event status.')
add('V2E2',[212],'O','Same O I6300-position, trace-compatible raw feature as V1E2-0005; no independent sky control.')
add('V2E2',[224],'A','Short compact/diagonal charge feature in one overlap order only; corresponding peak absent from the other order.')
add('V2E2',[226],'O','Same O I5577-position, distributed raw feature as V1E2-0006; no independent sky control.')
add('V2E2',[227],'O','Weak O I6300-position native feature with trace-compatible raw distribution, not an isolated bright charge pixel. Stellar/continuum blend and calibration limitations remain.')
assert set(notes)=={e['review_id']for e in E},(set(notes)-{e['review_id']for e in E},{e['review_id']for e in E}-set(notes))
labels={'A':'PROVISIONAL_DETECTOR_ARTIFACT','O':'PROVISIONAL_ATMOSPHERIC_OI','U':'UNRESOLVED_SPECTRAL_FEATURE','I':'INSUFFICIENT_LOCAL_RAW_MAPPING'}
rows=[]
for e in E:
 code,note=notes[e['review_id']];orders=[m for m in M['orders']if m['review_id']==e['review_id']and m['status']=='EXTRACTED'];center=orders[0]['topocentric_air_angstrom']if orders else None
 refs=[5577.339,6300.304,6363.776];nearest=min(refs,key=lambda w:abs(w-center))if center is not None else None
 rows.append(dict(review_id=e['review_id'],detector=e['detector'],dp_id=e['dp_id'],target=e['target'],primary_code=code,primary_disposition=labels[code],note=note,figure=I[e['review_id']]['figure'],figure_row=I[e['review_id']]['row'],all_covering_orders_mapping_verified=all(m['mapping_verified']for m in orders),topocentric_air_angstrom=center,nearest_OI_air_angstrom=nearest,nearest_OI_offset_angstrom=center-nearest if center is not None else None,original_production_unchanged=True,final_physical_origin_confirmed=False))
result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='Primary AI agent oi_doublet',review_method='Viewed all17 neutral pages/all65 records/all86 extracted covering orders. Separate AI-agent review; primary judgments withheld from second reviewer until its judgments are fixed. Both know selection/detector context; not blinded scientific validation or human review.',counts=dict(collections.Counter(r['primary_code']for r in rows)),rows=rows,figures_sha256={str(f.relative_to(O)):hashlib.sha256(f.read_bytes()).hexdigest()for f in sorted((O/'figures').glob('REVIEW_*.png'))})
path=O/'PRIMARY_VISUAL_REVIEW.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n');print(result['counts']);print('PRIMARY_SHA256',hashlib.sha256(path.read_bytes()).hexdigest());print('OI offsets',[(r['review_id'],r['nearest_OI_offset_angstrom'])for r in rows if r['primary_code']=='O'])
