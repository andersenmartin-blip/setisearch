#!/usr/bin/env python3
"""Pin geometry-only inputs and producer before contact metrics are computed."""
import hashlib
import json
from pathlib import Path
import zipfile

BASE = Path(__file__).resolve().parent
WORKSPACE = BASE.parent.parent
PHASES = (
    ('central171', 'seti_previous/analysis/s2017_control_targets_20261011_v2', [171]),
    ('adjacent170_172', 'seti_previous/analysis/off_adjacent_20261011', [170, 172]),
)
TARGETS = (('HIP97319', 'epoch1_off'), ('HIP97461', 'epoch2_off'), ('HIP97663', 'epoch3_off'))


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(WORKSPACE)), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


groups = []
for phase, directory, natives in PHASES:
    for target, scan in TARGETS:
        primary = 'primary20170428_' + target
        root = WORKSPACE / directory / 'results' / primary
        geometry = []
        for rank in (1, 2, 3):
            capsule = root / ('global_top%02d_raw503.npz' % rank)
            with zipfile.ZipFile(capsule) as archive:
                member = archive.read('rounded_absolute_centers.npy')
            geometry.append({'path': str(capsule.relative_to(WORKSPACE)),
                             'member': 'rounded_absolute_centers.npy', 'member_bytes': len(member),
                             'member_sha256': hashlib.sha256(member).hexdigest()})
        groups.append({'phase': phase, 'primary_target': target, 'scan_id': scan,
                       'primary_id': primary, 'natives': natives,
                       'top20': pin(root / 'TOP20.json'), 'top3': pin(root / 'TOP3.json'),
                       'top3_centers': geometry})
scope = {
    'schema': 'SETI_FROZEN_TOP120_GEOMETRY_CONTACT_SCOPE_V1',
    'created_utc_date': '2026-10-12', 'authorized_purpose': 'annotate 120 stored OFF winners without reranking',
    'constants': {'fch1_hz': 2802832031.25, 'df_hz': -2.7939677238464355,
                  'tsamp_s': 18.253611008, 'rows': 16, 'fine_channels_per_native': 1048576,
                  'native_indices': [170, 171, 172],
                  'DC_channels': [178782208, 179830784, 180879360]},
    'groups': groups,
    'source_geometry_convention': 'Every own scan first integration midpoint is dt=0; dt[r]=r*18.253611008 s; complete absolute source channel rounded with np.rint to nearest-even.',
    'rounded_center_formula': 'np.rint((f_at_own_first_midpoint-FCH1)/DF + drift*dt/DF).astype(int64)',
    'box_formula': 'inclusive center +/- width//2; widths are 1 or 3',
    'contact_rule': 'Count row once if its selected inclusive box contains at least one of the three frozen DC channels.',
    'untouched_rule': 'No row box intersects any of the three frozen DC channels.',
    'offset_rule': 'Nearest DC is selected by absolute reference-channel distance, then smaller DC channel; retain all 16 integer center offsets and per-DC contact counts.',
    'output_order': 'central171 then adjacent170_172; targets HIP97319,HIP97461,HIP97663; each original rank1..20 unchanged',
    'expected_counts': {'groups': 6, 'stored_TOP20_records': 120, 'geometry_rows': 1920,
                        'frozen_DC_row_box_checks': 5760, 'saved_TOP3_center_arrays': 18},
    'limits': {'CPU_seconds': 600, 'wall_seconds': 900, 'memory_bytes': 1073741824,
               'source_power_array_values': 0, 'new_detector_scores': 0, 'new_telescope_requests': 0,
               'output_bytes_cap': 1048576, 'rerun_or_overwrite': False},
    'source_driver_pins': [pin(WORKSPACE / directory / 'driver.py') for _, directory, _ in PHASES],
    'source_scope_pins': [pin(WORKSPACE / directory / 'scope.json') for _, directory, _ in PHASES],
    'producer_pin': pin(BASE / 'annotate_existing_top20.py'),
    'interpretation': [
        'Existing exposed winner lists; contact labels are exact geometry, not a new detector, veto, physical-source classification or calibrated significance.',
        'Original scores and ranks are copied without modification; no new detector scores or reranking.',
        'Untouched subset is incomplete: contaminated maxima and TOP20 truncation can conceal clean runners-up.',
        'Contact counts describe whole selected boxes and do not attribute their scores to any individual raw cell.',
        'All scans belong to one historical visit; no protected panels or prior FAIL_CLOSED statuses are opened or changed.',
        'Preparation inadvertently loaded one preexisting raw_power array while printing only its shape and dtype; no power values or measurements were printed or used. Scope preparation subsequently reads only NPZ geometry members.',
    ],
}
path = BASE / 'scope.json'
assert not path.exists(), 'Preserve the original frozen scope'
path.write_text(json.dumps(scope, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
print(json.dumps({'scope_path': str(path), 'scope_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'producer_sha256': scope['producer_pin']['sha256'], 'groups_pinned': len(groups),
                  'new_DC_contact_metrics_computed': 0}))
