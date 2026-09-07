"""Frozen paired isolation-mask experiment using retained M43S native inputs."""
import argparse
import gzip
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import time
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore, NativeReceiver
from m43r_joint_calibration import grid_context, compact
from m43s_profile_sensitivity import endpoint, geometry_summary
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43t as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43s import ProfileOverlay
from seti_repeater.mask_m43t import POLICIES, bind_calibration

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43t_mask_comparison'
CONFIG = ROOT / 'config/m43t_mask_comparison.json'
WINDOW = 'm43t-central-mask-comparison'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen(commit):
    cfg = json.loads(CONFIG.read_text())
    if subprocess.check_output(['git', 'show', commit + ':config/m43t_mask_comparison.json'], cwd=ROOT) != CONFIG.read_bytes():
        raise ValueError('configuration differs from public freeze')
    for path, expected in cfg['pinned_sha256'].items():
        if sha(ROOT / path) != expected:
            raise ValueError('frozen dependency changed: ' + path)
    if platform.python_version() != cfg['python_version'] or np.__version__ != cfg['numpy_version']:
        raise ValueError('numerical runtime changed')
    return cfg


def run(work, source_root, checkpoint_root, freeze):
    cfg = frozen(freeze); started = time.monotonic()
    OUT.mkdir(exist_ok=True); checkpoint_root.mkdir(parents=True, exist_ok=True)
    if (OUT / 'result.json').exists():
        raise ValueError('completed M43T result exists; preserve it')
    try:
        _, _, _, metadata, basis, parent, parent_table, _ = build_context()
        bank, table, bridge = detector.catalogue_bridge(parent, cfg['parent_template_indices'], basis)
        if bridge != cfg['bridge']:
            raise ValueError('catalogue bridge changed')
        original, grid, start = grid_context()
        if core.proxy_carrier_grid_sha256(grid) != cfg['grid_sha256']:
            raise ValueError('grid changed')
        old = AnchorStore(work, {'parent_template_indices': cfg['parent_template_indices'],
                                 'support_carriers': original.support_bin_count})
        arrays = {key: old.get(*key)[0][:, start:start+grid.support_bin_count] for key in old.expected_ids}
        provenance = {'family': 'M43P-exact-central-slice', 'parent_inventory_sha256': detector.digest(old.inventory),
                      'parent_score_ids_sha256': detector.digest([[*k, v] for k, v in sorted(old.expected_ids.items())]),
                      'support_start': start, 'support_count': grid.support_bin_count,
                      'grid_sha256': core.proxy_carrier_grid_sha256(grid)}
        baseline = ScoreStore(arrays, provenance)
        previous = read_sealed(ROOT / 'results_m43r_joint_calibration/calibration.json')
        if provenance != previous['baseline_provenance']:
            raise ValueError('baseline provenance changed')
        print('All 96 M43P arrays and central baseline identity verified', flush=True)
        common = dict(window=WINDOW, grid=grid, bank=bank, table=table, basis=basis, scans=metadata['scans'])
        calibrations = {}; thresholds = {}; bindings = {}; null_summary = {}
        # Complete and seal both calibration certificates before held-out or injected scoring.
        for policy in POLICIES:
            cal, summary = detector.calibrate(**common, store=baseline, mask_policy=policy,
                shifts=np.asarray(cfg['calibration_shifts'], dtype=np.int64), minimum_shift_bins=128,
                progress=lambda m: print(policy + ' training ' + m, flush=True))
            threshold = core.calibrated_threshold((cal,), expected_window_ids=(WINDOW,),
                                                  reference_floor=10., quantile=1., scientific_p_ceiling=.01)
            binding = bind_calibration(cal, threshold, policy)
            calibrations[policy] = cal; thresholds[policy] = threshold; bindings[policy] = binding
            write_sealed(OUT / (policy + '.calibration.json'), {'freeze_commit': freeze,
                'config_sha256': sha(CONFIG), 'baseline_provenance': provenance, 'summary': summary,
                'mask_policy': policy, 'null_maxima': cal.null_maxima.tolist(),
                'threshold': threshold.as_record(), 'binding': binding})
            print(policy + ' frozen threshold ' + str(threshold.operational_threshold_snr), flush=True)
        for policy in POLICIES:
            heldout, summary = detector.calibrate(**common, store=baseline, mask_policy=policy,
                shifts=np.asarray(cfg['heldout_shifts'], dtype=np.int64), minimum_shift_bins=128,
                progress=lambda m: print(policy + ' heldout ' + m, flush=True))
            values = heldout.null_maxima; threshold = thresholds[policy]
            null_summary[policy] = {'count': len(values), 'at_or_above_threshold': int(np.count_nonzero(values >= threshold.operational_threshold_snr)),
                'maximum': float(np.max(values)), 'threshold': threshold.operational_threshold_snr,
                'scope': 'paired correlated within-sequence pre-veto maxima; baseline masks co-rolled, not re-estimated; not physical FAP'}
            write_sealed(OUT / (policy + '.heldout.json'), {'freeze_commit': freeze, 'mask_policy': policy,
                'summary': summary, 'null_maxima': values.tolist(), 'diagnostic': null_summary[policy],
                'calibration_binding': bindings[policy]})
            print(policy + ' heldout ' + json.dumps(null_summary[policy]), flush=True)
        receiver = NativeReceiver(source_root, metadata, basis, parent, parent_table, original)
        overlay = ProfileOverlay(baseline, receiver, bank, table, basis, grid,
                                 progress=lambda m: print(m, flush=True))
        anchors = read_sealed(ROOT / 'results_m43r_joint_calibration/native_anchors.json')
        if overlay.cache_inventory != anchors['cache_inventory']:
            raise ValueError('native gather anchor identities changed')
        write_sealed(OUT / 'input_reuse.json', {'freeze_commit': freeze, 'config_sha256': sha(CONFIG),
            'baseline_provenance': provenance, 'cache_inventory': overlay.cache_inventory,
            'all_reused_identities_exact': True, 'telescope_requests': 0})
        fixed = dict(**common, receiver_factory=overlay, maximum_records=cfg['maximum_records'])
        background = {}; audit_paths = []
        def execute(policy, store):
            result = detector.execute(**fixed, store=store, calibration=calibrations[policy],
                threshold=thresholds[policy], mask_policy=policy, calibration_binding=bindings[policy])
            audit = compact(result, overlay.overlay_receipt)
            audit.update(mask_policy=policy, calibration_binding=bindings[policy])
            return audit
        for policy in POLICIES:
            overlay.trial(cfg['truths'][0], 0)
            background[policy] = execute(policy, baseline)
            path = OUT / (policy + '.baseline.json')
            write_sealed(path, {'freeze_commit': freeze, 'audit': background[policy]})
        on_factors = np.stack([core.factor_table_for_scan(table, basis, f'epoch{e+1}_on') for e in range(3)], axis=1)
        endpoints = []; old_endpoints = read_sealed(ROOT / 'results_m43s_profile_sensitivity/result.json')['endpoints']
        for truth in cfg['truths']:
            if geometry_summary(truth, grid, on_factors, basis) != cfg['geometry'][str(truth['truth_index'])]:
                raise ValueError('truth geometry changed')
            for policy in POLICIES:
                e = endpoint(background[policy], truth, grid, on_factors, basis, 0, policy + '.baseline.json')
                e.pop('zero_level_reuses_m43r_baseline'); e.update(mask_policy=policy, zero_level_reuses_one_m43t_arm_baseline=True)
                endpoints.append(e)
            for amplitude in cfg['amplitudes'][1:]:
                t0 = time.monotonic(); name = f'truth{truth["truth_index"]:02d}.strength{amplitude:03d}.json'
                path = checkpoint_root / name
                if path.exists():
                    record = read_sealed(path)
                    if record['freeze_commit'] != freeze or record['config_sha256'] != sha(CONFIG):
                        raise ValueError('checkpoint belongs to another freeze')
                    if record['truth'] != truth or record['amplitude'] != amplitude or record['bindings'] != bindings:
                        raise ValueError('checkpoint scope or calibration changed')
                else:
                    store = overlay.trial(truth, amplitude); audits = {}; outcomes = []
                    for policy in POLICIES:
                        audits[policy] = execute(policy, store)
                        e = endpoint(audits[policy], truth, grid, on_factors, basis, amplitude, name)
                        e.pop('zero_level_reuses_m43r_baseline'); e.update(mask_policy=policy, zero_level_reuses_one_m43t_arm_baseline=False)
                        outcomes.append(e)
                    if audits['legacy']['input_inventory_sha256'] != audits['neighbor9']['input_inventory_sha256']:
                        raise ValueError('paired injected score inventories differ')
                    if audits['legacy']['overlay'] != audits['neighbor9']['overlay']:
                        raise ValueError('paired native injection receipts differ')
                    record = write_sealed(path, {'freeze_commit': freeze, 'config_sha256': sha(CONFIG),
                        'truth': truth, 'amplitude': amplitude, 'bindings': bindings, 'audits': audits,
                        'endpoints': outcomes, 'wall_seconds': round(time.monotonic()-t0, 3)})
                endpoints.extend(record['endpoints']); audit_paths.append(path)
                print(f'Paired truth {truth["truth_index"]} strength {amplitude}: ' +
                      str({e['mask_policy']: e['recovered'] for e in record['endpoints']}), flush=True)
                write_sealed(OUT / 'progress.json', {'complete': False, 'completed_pairs': len(audit_paths),
                    'planned_pairs': 64, 'completed_endpoints': len(endpoints), 'planned_endpoints': 160})
        if len(endpoints) != 160 or len(audit_paths) != 64:
            raise ValueError('incomplete comparison denominator')
        summary = [{'mask_policy': policy, 'profile': profile, 'strength': amplitude,
            'denominator': 8, **{k: sum(e[k] for e in endpoints if e['mask_policy'] == policy and
                e['truth']['profile'] == profile and e['nominal_total_epoch_strength'] == amplitude)
                for k in ('retained', 'passes_physical_vetoes', 'recovered')}}
            for policy in POLICIES for profile in cfg['profiles'] for amplitude in cfg['amplitudes']]
        lookup = {(e['mask_policy'], e['truth']['truth_index'], e['nominal_total_epoch_strength']): e for e in endpoints}
        paired_changes = [{'truth_index': t['truth_index'], 'profile': t['profile'], 'strength': a,
            'legacy_recovered': lookup['legacy', t['truth_index'], a]['recovered'],
            'neighbor9_recovered': lookup['neighbor9', t['truth_index'], a]['recovered']}
            for t in cfg['truths'] for a in cfg['amplitudes'][1:]]
        # A new baseline calibration is distinct from M43S; report any changed reference outcomes.
        legacy_differences = [{'truth_index': e['truth']['truth_index'], 'strength': e['nominal_total_epoch_strength'],
            'm43s_recovered': e['recovered'], 'm43t_legacy_recovered': lookup['legacy', e['truth']['truth_index'], e['nominal_total_epoch_strength']]['recovered']}
            for e in old_endpoints if e['nominal_total_epoch_strength'] in cfg['amplitudes'] and
            e['recovered'] != lookup['legacy', e['truth']['truth_index'], e['nominal_total_epoch_strength']]['recovered']]
        ledger = b''.join(p.read_bytes()+b'\n' for p in audit_paths)
        (OUT / 'paired_trial_audits.jsonl.gz').write_bytes(gzip.compress(ledger, compresslevel=9, mtime=0))
        if gzip.decompress((OUT / 'paired_trial_audits.jsonl.gz').read_bytes()) != ledger:
            raise ValueError('lossless ledger round trip failed')
        write_sealed(OUT / 'result.json', {'milestone': 'M43T', 'status': 'paired-mask-comparison-complete',
            'freeze_commit': freeze, 'config_sha256': sha(CONFIG), 'summary': summary, 'endpoints': endpoints,
            'paired_changes': paired_changes, 'legacy_differences_from_m43s': legacy_differences,
            'heldout': null_summary, 'calibration_bindings': bindings, 'distinct_injection_inputs': 64,
            'new_injected_detector_executions': 128, 'new_background_executions': 2, 'zero_level_endpoint_reuses': 32,
            'unique_new_shift_rows': 256, 'arm_specific_null_maxima': 512,
            'trial_ledger_sha256': sha(OUT / 'paired_trial_audits.jsonl.gz'),
            'trial_ledger_uncompressed_sha256': hashlib.sha256(ledger).hexdigest(),
            'wall_seconds': round(time.monotonic()-started, 3), 'telescope_requests': 0,
            'full_bank_search': False, 'physical_false_alarm_probability_measured': False,
            'scientific_candidate_selection_authorized': False})
        write_sealed(OUT / 'progress.json', {'complete': True, 'completed_pairs': 64, 'completed_endpoints': 160})
        print(json.dumps(summary, indent=2), flush=True)
    except BaseException as error:
        write_sealed(OUT / 'failure.json', {'freeze_commit': freeze, 'error': repr(error), 'complete': False})
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze-commit', required=True)
    p.add_argument('--anchor-root', type=Path, required=True); p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--checkpoint-root', type=Path, required=True)
    a = p.parse_args(); run(a.anchor_root, a.source_root, a.checkpoint_root, a.freeze_commit)
