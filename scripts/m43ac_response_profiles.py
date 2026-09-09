"""Reconstruct three selected response neighborhoods, without detector scoring."""
import argparse
import json
from pathlib import Path
import numpy as np
from m43ac_dual_evidence import ROOT, OUT, SOURCE, NEW, context, source_records, final_ids, sha
from m43aa_native_response import native_parts, response_profiles, similarity
from m43e_economical_bank import read_sealed, write_sealed
from m43q_integrated_detector import AnchorStore, NativeReceiver
from seti_repeater import detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43u import JointOverlay
from seti_repeater.attribution_m43ab import centered_signatures, centered_agreement


def run(runtime):
    assert not (OUT / 'response_summary.json').exists(), 'preserve completed responses'
    (OUT / 'responses').mkdir(exist_ok=True)
    cfg, metadata, basis, parent, pt, bank, table, original, grid, start = context()
    old = AnchorStore(runtime / 'anchors', dict(parent_template_indices=cfg['parent_template_indices'],
                                              support_carriers=original.support_bin_count))
    arrays = {k: old.get(*k)[0][:, start:start + grid.support_bin_count] for k in old.expected_ids}
    provenance = dict(family='M43P-exact-central-slice', parent_inventory_sha256=detector.digest(old.inventory),
        parent_score_ids_sha256=detector.digest([[*k, v] for k, v in sorted(old.expected_ids.items())]),
        support_start=start, support_count=grid.support_bin_count, grid_sha256=cfg['grid_sha256'])
    assert provenance == read_sealed(ROOT / 'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline = ScoreStore(arrays, provenance)
    receiver = NativeReceiver(runtime / 'sources', metadata, basis, parent, pt, original)
    overlay = JointOverlay(baseline, receiver, bank, table, basis, grid,
                           progress=lambda m: print(m, flush=True))
    assert overlay.cache_inventory == read_sealed(ROOT / 'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    results = []; direct_checks = 0; sources = []; signature_epochs = 0
    for item, rec in source_records():
        name = rec['case']['name']
        if name not in ('z138', 'fresh032'):
            continue
        sources.append(item)
        survivors = final_ids(rec, NEW); assert len(survivors) == 1
        rid = next(iter(survivors)); ids = {rid}
        original_records = {m['record_id']: m for m in rec['original_alias']['records']}
        if name == 'fresh032':
            ids.add(original_records[rid]['receiver_alias_evidence']['best_receiver_alias_witness']['record_id'])
        selected = [original_records[i] for i in sorted(ids)]
        store = overlay.trial(rec['case']['components'])
        assert overlay.overlay_receipt == rec['reference_audit']['overlay']
        signatures, receipt = overlay(selected, bank, table)
        centered, cr = centered_signatures(overlay, selected)
        for i in ids:
            assert signatures[i] == rec['original_signatures'][i]
            assert centered[i] == rec['centered_signatures'][i]
            signature_epochs += len(signatures[i])
        parts = native_parts(overlay, rec['case']['components'])
        profiles, checks = response_profiles(store, baseline, overlay, parts, grid, selected, 160)
        direct_checks += checks
        for m in selected:
            t, q, w = m['template_index'], m['proxy_carrier_index'], m['spectral_width_channels']
            on = store.get('on', t, w)[0]; off = store.get('off', t, w)[0]
            assert np.array_equal(on[:, grid.score_slice.start+q], np.array(m['epoch_values_at_proxy_carrier'], dtype='<f4'))
            agreement = centered_agreement(on, off, grid, q, w, m['active_epochs_zero_based'])
            expected = next(e['agreement'] for e in rec['new_confirmation_evidence'] if e['record_id'] == m['record_id'])
            assert agreement == expected
        for profile in profiles:
            t, q = profile['template_index'], profile['proxy_carrier_index']
            m = next(m for m in selected if (m['template_index'], m['proxy_carrier_index']) == (t, q))
            width_files = []
            for w in profile['widths']:
                path = OUT / 'responses' / f'{name}.t{t}.q{q}.w{w["width"]:03d}.json'
                write_sealed(path, dict(name=name, template_index=t, proxy_carrier_index=q,
                    first_proxy_index=profile['first_proxy_index'], last_proxy_index=profile['last_proxy_index'], **w))
                width_files.append(dict(file=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
            focal = next(w for w in profile['widths'] if w['width'] == m['spectral_width_channels'])
            radius = max(1, m['spectral_width_channels']//2); sl = slice(160-radius, 161+radius)
            epochs = []
            for e in range(3):
                on = np.array(focal['on']['values'][e]); off = np.array(focal['off']['values'][e])
                bon = np.array(focal['on']['baseline_values'][e]); boff = np.array(focal['off']['baseline_values'][e])
                epochs.append(dict(epoch=e, active=e in m['active_epochs_zero_based'],
                    on_center=float(on[160]), baseline_on_center=float(bon[160]),
                    off_center=float(off[160]), baseline_off_center=float(boff[160]),
                    on_increment_center=float(on[160]-bon[160]),
                    off_increment_center=float(off[160]-boff[160]),
                    full_on_response_equals_baseline=bool(np.array_equal(on, bon)),
                    full_off_response_equals_baseline=bool(np.array_equal(off, boff)),
                    centered_raw_correlation=similarity(on[sl], off[sl]),
                    centered_baseline_correlation=similarity(bon[sl], boff[sl]),
                    centered_increment_correlation=similarity((on-bon)[sl], (off-boff)[sl]),
                    centered_on_increment_variation=float(np.ptp((on-bon)[sl])),
                    centered_off_increment_variation=float(np.ptp((off-boff)[sl])),
                    on_shape=focal['on']['shape'][e], off_shape=focal['off']['shape'][e],
                    on_increment_shape=focal['on']['increment_shape'][e],
                    off_increment_shape=focal['off']['increment_shape'][e]))
            results.append(dict(name=name, role='survivor' if m['record_id'] == rid else 'old_alias_witness',
                record_id=m['record_id'], template_index=t, proxy_carrier_index=q,
                width=m['spectral_width_channels'], response_files=width_files, epochs=epochs))
        print(f'{name}: {len(profiles)} neighborhoods, {checks} direct native comparisons exact', flush=True)
    assert len(results) == 3 and direct_checks == 144 and signature_epochs == 7
    write_sealed(OUT / 'response_summary.json', dict(retrospective=True, sources=sources,
        all_96_arrays_exact=True, all_48_native_gathers_exact=True,
        original_and_centered_signature_epochs_exact=signature_epochs,
        overlay_receipts_exact=True, focal_agreements_exact=True,
        direct_native_comparisons=direct_checks, response_neighborhoods=3,
        radius_proxy_bins=160, profiles=results, new_detector_executions=0,
        new_null_rows=0, new_injection_specifications=0, new_observing_sequences=0))
    print('M43AC RESPONSES COMPLETE', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--runtime-root', required=True, type=Path)
    run(parser.parse_args().runtime_root)
