"""Materialize the second agent's recorded inspection of all 43 review panels.

This file encodes visual judgments, not an automatic classification algorithm.
It reads the existing frozen figure index and mapping audit, and only creates
the two explicitly named second-agent review files beside this script.
"""
from pathlib import Path
import collections
import hashlib
import json

ROOT = Path(__file__).resolve().parent

NOTES = {
    99: ('U', 'A several-sample peak is visible in orders 2 and 3. Order 2 is much noisier, including large excursions, while order 3 shows a smoother central fibre-associated excess. No distinct isolated charge track is apparent; the weak blue continuum limits interpretation of the normalized height.'),
    106: ('A', 'The narrow peak is prominent in order 7, without a convincing matching profile in noisy order 6. The order-7 candidate core is a compact, nearly single-row pixel group rather than a smooth fibre profile. This supports a probable detector artifact; neighboring bright spots are not used as evidence.'),
    110: ('U', 'Both covering orders show a broader peak, with larger and noisier normalized excursions in order 2. Order 3 has an extended central fibre-associated excess; order 2 is weaker. The panels do not establish a distinct particle track or an atomic identification.'),
    115: ('U', 'The native peak is broad and rounded in both orders 2 and 3, with order 2 noisier. The order-3 raw excess occupies several spatial and dispersion pixels near the fibre. This remains an unresolved spectral structure.'),
    117: ('U', 'The order-19 native feature is a broad asymmetric hump with a left shoulder. Raw excess is spread over the central fibre rather than a distinct compact charge trail. Bright off-fibre spots alone do not establish an artifact.'),
    118: ('U', 'Order 19 contains a smooth broad peak with adjacent depression and additional structure. Its central raw excess is compatible with the fibre profile, and no isolated track is established. A physical line identification is not supplied by these panels.'),
    120: ('U', 'A broader peak occurs in both orders 2 and 3, with more noise in order 2. The central order-3 excess is spatially extended and fibre-associated. There is no clear candidate-centered particle morphology.'),
    125: ('U', 'The broad feature is clearest in order 2; the noisier near-edge order-3 spectrum is compatible with a broader rise. Order 2 has a central excess spanning several dispersion samples. The weaker overlap does not provide an independent artifact diagnosis.'),
    126: ('U', 'Both orders show a broad feature. Order 2 has noisy subsidiary maxima, whereas order 3 is smoother and has a central fibre-associated raw excess. The shape is not sufficient for a specific spectral or detector-origin identification.'),
    129: ('U', 'A broad hump is present in both orders 2 and 3. Order 2 is noisier; the order-3 excess is smoothly centered on the fibre. No unambiguous compact charge structure is apparent.'),
    131: ('U', 'The order-19 feature is broad, asymmetric and shouldered. Its raw excess extends across several pixels along the central fibre, without a separable particle trail. It remains a spectral structure of unresolved origin.'),
    132: ('U', 'Order 19 shows a smooth broad peak with a neighboring trough and secondary bump. The central raw excess is fibre-compatible; the surrounding structure does not establish a distinct isolated detector hit.'),
    135: ('U', 'Both orders 2 and 3 contain a broad peak, with a higher and noisier normalized feature in order 2. The order-3 raw excess extends over multiple rows near the fibre. No separate charge streak is apparent.'),
    139: ('U', 'Order 2 shows a modest smooth bump and weak on-fibre excess. Noisier order 3 has a compatible central rise but does not yield a decisive morphology. Mapping is supported, while the low signal-to-noise ratio leaves the feature unresolved.'),
    149: ('M', 'The extracted order-1 panel contains a sharp native feature on a broader slope and a compact offset pixel group. However, order 1 fails the fixed broader-reference mapping gate, and covering order 0 is edge-truncated. These appearances cannot support an origin disposition under the required mapping rule.'),
    155: ('A', 'The narrow native peak appears in order 53 and lacks a matching feature in order 52. Order 53 shows a compact, almost single-row transverse or offset pixel group at the candidate. The joint morphology and overlap support a probable detector artifact, independent of neighboring calibration-fibre light.'),
    186: ('A', 'A sharp peak appears in order 2 without a corresponding peak in order 1. The order-2 raw panel shows a diagonal multi-pixel track crossing the candidate trace, supporting a probable detector artifact. The old local displacement remains historical evidence; the fixed broader reference audit now supports mapping.'),
    217: ('A', 'Order 26 contains a sharp native spike and a compact candidate-centered raw pixel group. Noisy order 27 lacks a compelling matching feature. The compact morphology supports a probable detector artifact, with the weak overlap treated as supplementary evidence.'),
    221: ('U', 'Order 2 has a very large noisy normalized peak and negative nearby excursions, while order 3 shows a smaller broader feature and central fibre-associated excess. The near-zero side continuum makes the order-2 ratio unstable. Broader references now support mapping, but do not identify the origin.'),
    228: ('A', 'The sharp native feature occurs in order 57 and is absent from order 58. The order-57 raw candidate is a compact transverse pixel group, with no corresponding excess in order 58. This supports a probable detector artifact.'),
    231: ('M', 'Broader native features and central raw excess are visible in orders 2 and 3, but order 3 fails the fixed broader-reference gate. The visually spectral appearance cannot override that failure; mapping remains insufficient for an origin disposition.'),
    232: ('M', 'Order 2 has a noisy large normalized feature, and order 3 has a smoother broader peak with central raw excess. Order 3 nevertheless fails the required broader-reference mapping criterion, so no spectral-origin or artifact classification is assigned.'),
    233: ('U', 'The feature is a broad shoulder or peak in both orders 18 and 19, with order 18 noisier. The raw excess is extended near the central fibre, particularly in order 19. These panels do not identify a distinct compact detector track.'),
    235: ('A', 'A narrow native spike in order 52 is superposed on broader continuum or absorption structure and lacks a matching peak in order 53. The raw order-52 panel shows an oblique multi-pixel charge streak crossing the trace, supporting a probable detector artifact.'),
    243: ('U', 'Both orders 2 and 3 show a coincident broader peak, with noisier order-2 samples. Their central raw excess is extended and fibre-associated rather than a distinct isolated track. The origin remains unresolved.'),
    244: ('U', 'Order 2 reaches an extreme normalized ratio alongside large negative excursions, indicating an unstable weak-continuum normalization. Order 3 shows a much smaller broad peak. Both panels have central fibre-associated raw excess; the ratio is not treated as a physical emission amplitude.'),
    260: ('U', 'Orders 2 and 3 show smoothly agreeing broader peaks and extended central fibre-associated excess. No obvious compact particle pattern is established. Agreement across the overlap supports a spectral structure but does not identify it.'),
    263: ('U', 'Both orders show a broad asymmetric peak with a left shoulder and nearby dip. The raw signal is distributed over several pixels near the fibre in both panels, without a distinct isolated charge trail. It remains unresolved.'),
    266: ('U', 'A broad matching peak is present in orders 2 and 3, with a modest amplitude difference. Their central raw excess is fibre-associated. The morphology does not provide an atomic identification or decisive detector-artifact evidence.'),
    268: ('U', 'Both orders contain a broad structured feature with a secondary bump and nearby depression. The raw excess lies around the central fibre and does not isolate a compact charge event. The structure remains unresolved.'),
    272: ('U', 'A broad hump appears in both orders, with more noise in order 2. Order 3 shows a spatially extended central excess compatible with the fibre. No clear candidate-centered particle trail is visible.'),
    273: ('U', 'The native feature is broad and coincident in orders 2 and 3, although the blue order 2 is noisy. Raw excess is associated with the central fibre in both panels; an isolated diagonal or compact charge track is not established.'),
    274: ('U', 'Order 2 contains several noisy maxima within a broader central structure, while order 3 gives a rounded peak. Both raw panels show fibre-associated excess rather than a distinct sharply isolated charge event. The feature remains unresolved.'),
    277: ('U', 'A broad, somewhat structured peak agrees between orders 2 and 3. The raw signal extends around the central fibre in both panels. The overlap and spatial appearance support a spectral structure without establishing its cause.'),
    278: ('U', 'Both native spectra show a broader humped or multi-peaked feature, with order 2 noisier. Their central raw excess is coherent with the fibre, and no conclusive separate particle track is apparent.'),
    279: ('U', 'The broader peak is coincident in orders 2 and 3 despite the noisy blue-order continuum. Raw excess is central and fibre-associated in both. The panels do not support a specific atomic identification or a decisive detector diagnosis.'),
    280: ('U', 'Both orders have a broader structured peak. Order 2 adds a narrower noisy fluctuation, but the raw signal in both panels remains compatible with central fibre-associated excess and lacks a distinct charge track. The narrow fluctuation alone is insufficient for an artifact class.'),
    281: ('U', 'Order 3 shows a broad peak with a central fibre-associated raw excess. Order 2 is noisier, has a larger normalized height, and a weaker raw counterpart. These differences do not establish an isolated detector event.'),
    284: ('U', 'Both orders show a broad coincident peak, with order 2 noisier, and central fibre-associated raw signal. The previous local offset is retained in the history, while the broader fixed references now pass. That mapping result does not establish a physical origin.'),
    306: ('A', 'A narrow native peak occurs in order 63 and is absent from order 64. Order 63 shows a small compact or transverse raw pixel group at the candidate; order 64 lacks a corresponding excess. This supports a probable detector artifact.'),
    322: ('U', 'Both orders show broader coincident structure, with larger and noisier normalized excursions in order 2. The weak raw excess is associated with the central fibre. The panels do not establish a distinct compact detector event or physical line identity.'),
    326: ('A', 'The narrow native feature appears in order 64 and is absent from order 63. Its raw candidate is a compact, nearly single-row pixel group in order 64, while order 63 has no corresponding peak. This supports a probable detector artifact.'),
    333: ('M', 'The order-70 native spike and a short oblique or offset raw group are suggestive of a detector event. Nevertheless the broader-reference median correlation is approximately 0.768, below the fixed 0.8 criterion. The reference profile being centered does not override that failure; origin disposition remains mapping-limited.'),
}

index = json.loads((ROOT / 'FIGURE_INDEX.json').read_text())
plan = json.loads((ROOT / 'PLAN.json').read_text())
audit = json.loads((ROOT / 'MAPPING_AUDIT.json').read_text())
by_id = {int(row['review_id'].split('-')[1]): row for row in index}
events = {int(row['review_id'].split('-')[1]): row for row in audit['events']}
expected = {int(x.split('-')[1]) for x in plan['review_ids']}
assert set(NOTES) == expected == set(by_id) == set(events)
assert len(NOTES) == 43
assert {i for i, row in events.items() if not row['mapping_supported']} == {149, 231, 232, 333}
assert all(NOTES[i][0] == 'M' for i, row in events.items() if not row['mapping_supported'])
result = {}
for event_id, (code, reason) in sorted(NOTES.items()):
    location = by_id[event_id]
    covering = ', '.join(str(o) for o in events[event_id]['covering_orders'])
    provenance = f"REVIEW_{location['page']:02d}.png row {location['row']}; covering orders {covering}. "
    result[str(event_id)] = [code, provenance + reason + ' Provisional visual assessment; no final origin claim.']

notes_path = ROOT / 'VISUAL_NOTES_SECOND_AGENT.json'
notes_path.write_text(json.dumps(result, indent=2) + '\n')
counts = dict(sorted(collections.Counter(value[0] for value in result.values()).items()))
assert counts == {'A': 8, 'M': 4, 'U': 31}
summary = {
    'reviewer': '/root/mapping_43/visual_review (second AI agent)',
    'review_type': 'Independent provisional visual reading of shared diagnostic figures; not an independent observation or human review.',
    'reviewed_event_count': len(result),
    'reviewed_figure_pages': [f'figures/REVIEW_{n:02d}.png' for n in range(1, 12)],
    'panel_coverage': 'All native, raw-count and wide-excess panels available for every event in the figure index. Event 149 has a retained edge-truncated covering order 0 without a full usable review panel; that limitation is preserved.',
    'reference_figures_claimed_reviewed': False,
    'mapping_evidence': 'The parent supplied fixed-plan numeric mapping gates. The four failed events are M regardless of suggestive visual morphology. No geometry fitting or detector tuning was performed by this reviewer.',
    'classification_counts': {key: counts.get(key, 0) for key in ('A', 'O', 'U', 'M')},
    'artifact_ids': [f'V2-{i:04d}' for i, value in sorted(NOTES.items()) if value[0] == 'A'],
    'mapping_limited_ids': [f'V2-{i:04d}' for i, value in sorted(NOTES.items()) if value[0] == 'M'],
    'code_meanings': {'A': 'probable detector artifact', 'O': 'compatible with atmospheric O I', 'U': 'unresolved spectral structure', 'M': 'insufficient raw mapping'},
    'independence': 'The provisional tally and event judgments were formed before seeing any parent visual dispositions. The reviewer was aware of fixed mapping flags and previous mapping cautions.',
    'interpretation_limits': [
        'All dispositions are provisional. No laser or extraterrestrial-origin conclusion follows from this review.',
        'Overlap consistency and fibre-associated morphology do not identify an atomic transition or astronomical source.',
        'Large normalized blue-order ratios can reflect a weak or near-zero side continuum; they are not interpreted directly as physical emission amplitudes.',
        'Neighboring calibration-fibre light is not itself detector-artifact evidence.',
        'The wide positive-excess display is scaled to the central eleven-column maximum, so brighter outside charge may saturate.',
        'This reviewer did not alter original data, previous dispositions, mapping thresholds, geometry, or the original detector.'
    ],
    'notes_sha256': hashlib.sha256(notes_path.read_bytes()).hexdigest(),
    'input_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ('PLAN.json', 'FIGURE_INDEX.json', 'MAPPING_AUDIT.json')},
}
(ROOT / 'VISUAL_NOTES_SECOND_AGENT_SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'events': len(result), 'counts': summary['classification_counts'], 'notes_sha256': summary['notes_sha256']}))
