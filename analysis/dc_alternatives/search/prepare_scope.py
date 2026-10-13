#!/usr/bin/env python3
"""Bind the exposed carrier inventory and exact original raw frames."""
import gzip
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
import numpy as np
import scipy

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': sha(raw)}


inventory_path = BASE / 'EXCLUDED_CARRIERS.json'
inventory = json.loads(inventory_path.read_text())
frame_path = ROOT / 'dc_alternatives/feasibility/ORIGINAL_ON_FRAME_INVENTORY.json'
frames = json.loads(frame_path.read_text())
raw_receipt_path = ROOT / 'on_cached/feasibility/RAW_RESTORATION_RECEIPT.json'
raw_receipt = json.loads(raw_receipt_path.read_text())
original_scope_path = ROOT / 'on_cached/ranking/scope.json'
original_scope = json.loads(original_scope_path.read_text())
frame_index = {(g['scan_id'], g['native_chunk_index'], g['core_q']): g for g in frames['groups']}
source_index = {(r['scan_id'], r['native_chunk_index']): r for r in raw_receipt['sources']}
groups = []
for original in inventory['groups']:
    key = (original['primary_scan_id'], original['native_chunk_index'], original['core_q'])
    frame = frame_index[key]
    source = source_index[key[:2]]
    assert frame['original_s_power_shape'] == [16, 12096]
    assert frame['original_s_power_source_channel0'] == key[1] * 1048576 + key[2] * 4096 - 4000
    assert original['source_map_metadata']['map_pin'] == frame['original_map_pin_declared_by_checkpoint_only_not_map_payload_read']
    assert original['source_map_metadata']['normalization_pin'] == frame['original_normalization_pin']
    source_pin = pin(ROOT / source['restored_path'])
    assert source_pin['bytes'] == source['bytes'] and source_pin['sha256'] == source['sha256']
    groups.append(dict(original, exact_original_frame=frame, raw_source_metadata=source,
                       raw_source_pin=source_pin,
                       excluded_inventory_indices=[i for i, r in enumerate(inventory['records']) if r['group_id'] == original['group_id']]))
assert len(groups) == 18 and sum(len(g['excluded_inventory_indices']) for g in groups) == 7083
old_results = []
for scan in original_scope['primary_scan_ids']:
    path = ROOT / 'on_cached/ranking' / scan / 'RESULT.json'
    receipt = json.loads(path.with_name('EXECUTION_RECEIPT.json').read_text())
    actual = pin(path)
    assert actual in receipt['outputs']
    old_results.append({'primary_scan_id': scan, 'result_pin': actual})
scope = {'schema': 'SETI_DC_CONTACT_ALTERNATIVE_ORIGINAL_GRID_SCOPE_V1', 'date': '2026-10-13',
    'goal': 'Recover the maximum DC-untouched original-grid hypothesis at the 7,083 ON carriers whose cached winning hypothesis contacted DC; all other cached clean maxima remain unchanged.',
    'groups': groups, 'primary_scan_ids': original_scope['primary_scan_ids'], 'constants': inventory['constants'],
    'excluded_inventory_pin': pin(inventory_path), 'excluded_inventory_gzip_pin': pin(BASE / 'EXCLUDED_CARRIERS.json.gz'),
    'original_frame_inventory_pin': pin(frame_path), 'raw_restoration_receipt_pin': pin(raw_receipt_path),
    'prefix_arithmetic_contract_pin': pin(ROOT / 'dc_alternatives/feasibility/PREFIX_ARITHMETIC_CONTRACT.json'),
    'original_ON_selection_scope_pin': pin(original_scope_path), 'cached_clean_prefixes': old_results,
    'producer_pin': pin(BASE / 'recover_alternatives.py'),
    'runtime': {'numpy': np.__version__, 'scipy': scipy.__version__,
                'h5py': '3.15.1', 'HDF5': '1.14.6', 'hdf5plugin': '7.1.0'},
    'counts': {'original_DC_contact_carriers': 7083, 'carriers_per_ON': 2361, 'core_groups': 18,
                'ON_native_sources': 9, 'original_hypotheses_per_carrier': 1570,
                'hypothesis_score_occurrences_upper_bound': 11120310,
                'complete_original_raw_frame_cells': 3483648, 'complete_raw_frame_bytes': 13934592},
    'source_query_rule': 'Decode/authenticate each of the nine ON native sources once, using original whole-file and sixteen decoded-row hashes; preserve both exact scoring crops from each source.',
    'normalization_rule': 'Use immutable original saved row_power_median, row_winsorized_residual_location and row_residual_MAD_scale. No mask, new fit, normalization domain or kernel change.',
    'prefix_rule': 'Normalize the full original16x12096 frame; scipy median_filter size(1,501),mode nearest; z from original terms; prefix[:,1:]=np.cumsum(z,axis1,dtypefloat64),zero initial column; original width-box differences.',
    'score_rule': 'Complete absolute-channel np.rint at original own-row times; sequential row0..15 box additions to float64 zero scores; one division by sqrt(16*width). Original grid values remain unchanged, including near-zero floating value.',
    'exact_hypothesis_tie_rule': 'Original width1 then3; ascending original785drifts in16-value tiles; np.argmax first tie within tile; update only on strict greater. This differs from global frequency-rank tie keys.',
    'unrestricted_reconciliation': 'Before writing recovered maxima, replay unrestricted original family at every inventory carrier and require exact original score,drift andwidth. Any discrepancy stops the job and is preserved, never silently tolerated.',
    'DC_rule': 'Admissible iff none of the sixteen width1/3 inclusive boxes touches any fixed DC source channel178782208,179830784,180879360. This is hypothesis eligibility, not a spectral power mask.',
    'EMPTY_rule': 'Retain each carrier with no admissible hypothesis as explicit EMPTY: score/drift/width null, admissible_count0; original tuple remains preserved.',
    'merge_rule': 'Merge all recovered nonempty maxima with each original exact cached-clean rawTOP700 prefix, sort once by scoredesc/frequencyasc/driftasc/widthasc/native/q/carrier, retain rawTOP700/rawTOP100 and separatedTOP100 with greater-than3 channel spacing; finalTOP3 is first3 of separated list.',
    'merge_completeness_proof': 'An original clean winner is already the maximum over the unchanged full original hypothesis family; DC conditioning cannot lower it. Every cached clean carrier outside the oldTOP700 has700 clean predecessors that remain in the merged domain, so cannot enter the mergedTOP700. New alternative carriers are disjoint from those clean carriers. Therefore the merge yields exact complete clean-family TOP700 without sorting all9,412,608 carriers again.',
    'separated_prefix_proof': 'Unique reference channels per ON;99 prior selections block at most693 carriers including themselves. The100th separated pick occurs by raw rank694 when enough carriers exist; exactTOP700 suffices.',
    'output': ['all7,083 original tuples/DC diagnostics plus recovered clean maxima or EMPTY and admissible counts',
                'eighteen complete float32 scoring-frame NPZ files with pins',
                'eighteen authoritative recovered-winner NPZ arrays and normalized z frame hashes',
                'per-ON merged rawTOP700/rawTOP100/separatedTOP100/TOP3 and overlap with formerON TOP3',
                'global selectedTOP9, execution and aggregation receipts'],
    'selected_score_authority': 'Each selected record has source_kind and authoritative_score_source(kind,pin,record_index,score_field,drift_field,width_field,channel_field). Cached clean records bind original map arrays; recovered records bind the newly frozen recovered-winner NPZ arrays. Original map_pin is retained as parent provenance, not substituted for a recovered score.',
    'limits': {'CPU_seconds_per_job': 600, 'wall_seconds_per_job': 900, 'RAM_bytes_per_job': 2147483648,
                'output_bytes_per_job': 33554432, 'maximum_parallel_jobs': 2, 'DKK': 0,
                'new_telescope_HTTP': 0, 'rerun_or_overwrite': False},
    'metadata_preparation': {'new_source_float_queries': 0, 'new_hypothesis_scores': 0},
    'interpretation_limits': ['Prospective counterfactual DC-untouched conditioning of the original785-drift,width1/3 ordinary16 family; no new observing visit, frequency coverage or hypothesis extension.',
        'The recovered maxima and ranks are exposed exploratory scores, not calibrated SNR, FAP or source origin.',
        'Reference-channel separation does not establish independent physical sources; ON recurrence is not required.',
        'Original A/B FAIL_CLOSED,protected2016 andclosed2019 remain unchanged.']}
path = BASE / 'scope.json'
assert not path.exists()
raw = (json.dumps(scope, indent=2, allow_nan=False) + '\n').encode()
path.write_bytes(raw)
compressed = gzip.compress(raw, compresslevel=9, mtime=0)
(BASE / 'scope.json.gz').write_bytes(compressed)
assert gzip.decompress(compressed) == raw
print(json.dumps({'status': 'PREPARED_BEFORE_NEW_RAW_OR_HYPOTHESIS_SCORES', 'scope_sha256': sha(raw),
                   'compressed_scope_sha256': sha(compressed), 'producer_sha256': scope['producer_pin']['sha256'],
                   'scope_bytes': len(raw), 'compressed_bytes': len(compressed)}))
