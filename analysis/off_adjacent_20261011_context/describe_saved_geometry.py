"""Reproduce post-selection geometry from saved, QA-checked context JSON.

This descriptive helper was saved after the original arithmetic calculation.
It is not a prospectively specified significance or origin test.
"""
from pathlib import Path
import json, hashlib, math
base = Path(__file__).resolve().parent
mp = base / 'results/CONTEXT_PROFILES.json'
m = json.loads(mp.read_text())
stationary = [t for t in m['selected_tracks'] if t['rank'] == 1]
assert len(stationary) == 3 and len({t['reference_source_channel'] for t in stationary}) == 1
channel = stationary[0]['reference_source_channel']
records = []
for p in m['profiles']:
    t = p['selected_track']
    if t['rank'] != 3:
        continue
    hit = [i for i, c in enumerate(p['rounded_absolute_centers']) if abs(c - channel) <= t['width_channels'] // 2]
    pos = [max(x, 0.) for x in p['row_score_contribution']]
    total = math.fsum(pos)
    records.append({'primary_target': t['primary_target'], 'context_scan_id': p['context_scan_id'],
      'own_primary_scan': t['scan_id'] == p['context_scan_id'], 'stationary2297_box_overlap_rows': hit,
      'positive_contribution_fraction_on_hit_rows': math.fsum(pos[i] for i in hit) / total if total else None,
      'fixed_score': p['fixed_robust_box_track_score']})
r = {'schema': 'SETI_POST_SELECTION_SAVED_CENTER_GEOMETRY_DESCRIPTION_V1',
     'status': 'COMPLETE_DESCRIPTIVE_GEOMETRY_NO_GRID_OR_FIT',
     'source_context_matrix_sha256': hashlib.sha256(mp.read_bytes()).hexdigest(),
     'reference_selection': 'The already saved rank1 channel shared by all three primaries; post-selection descriptive geometry only',
     'reference_source_channel': channel, 'reference_frequency_hz': stationary[0]['frequency_hz_at_own_first_midpoint'],
     'records': records, 'no_new_fit': True, 'no_detector_reexecution': True,
     'physical_origin_established': False, 'false_alarm_calibration': False}
with (base / 'delivery/NEARBY_STATIONARY_GEOMETRY.json').open('x') as stream:
    json.dump(r, stream, indent=2); stream.write('\n')
