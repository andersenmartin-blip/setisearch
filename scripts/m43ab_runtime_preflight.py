"""Operational checks only: restore no calibration and score no M43AB cases."""
import argparse
import json
import time
from pathlib import Path
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore, NativeReceiver
from m43r_joint_calibration import grid_context
from seti_repeater import detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43u import JointOverlay

ROOT = Path(__file__).resolve().parents[1]


def run(runtime):
    started = time.monotonic()
    cfg = json.loads((ROOT/'config/m43ab_attribution.json').read_text())
    _, _, _, metadata, basis, parent, parent_table, _ = build_context()
    bank, table, bridge = detector.catalogue_bridge(parent, cfg['parent_template_indices'], basis)
    assert bridge == cfg['bridge']
    original, grid, start = grid_context()
    old = AnchorStore(runtime/'anchors', dict(parent_template_indices=cfg['parent_template_indices'],
                                            support_carriers=original.support_bin_count))
    arrays = {k:old.get(*k)[0][:, start:start+grid.support_bin_count] for k in old.expected_ids}
    provenance = dict(family='M43P-exact-central-slice', parent_inventory_sha256=detector.digest(old.inventory),
        parent_score_ids_sha256=detector.digest([[*k, v] for k,v in sorted(old.expected_ids.items())]),
        support_start=start, support_count=grid.support_bin_count, grid_sha256=cfg['grid_sha256'])
    assert provenance == read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline = ScoreStore(arrays, provenance)
    receiver = NativeReceiver(runtime/'sources', metadata, basis, parent, parent_table, original)
    overlay = JointOverlay(baseline, receiver, bank, table, basis, grid, progress=lambda m:print(m, flush=True))
    assert overlay.cache_inventory == read_sealed(ROOT/'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    record = dict(passed=True, all_96_arrays_exact=True, all_48_native_gathers_exact=True,
        calibration_not_executed=True, new_cases_scored=0, new_rule_evaluated=False,
        purpose='operational restoration and unchanged arithmetic preflight',
        wall_seconds=round(time.monotonic()-started, 3))
    write_sealed(ROOT/'results_m43ab_attribution/runtime_preflight.json', record)
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--runtime-root', type=Path, required=True)
    run(p.parse_args().runtime_root)
