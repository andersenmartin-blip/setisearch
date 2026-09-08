"""Run the prospectively frozen M43AB development comparison."""
import argparse
import gzip
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore, NativeReceiver
from m43r_joint_calibration import grid_context, compact
from m43s_profile_sensitivity import endpoint
from m43aa_native_response import native_parts, raw_window_score
from m43z_joint_controls import WINDOW
from seti_repeater import search_v0p6 as core, detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43s import restore_calibration
from seti_repeater.injection_m43u import JointOverlay
from seti_repeater.mask_m43u import bind_calibration
from seti_repeater.confirmation_m43z import apply_controls as old_controls
from seti_repeater.attribution_m43ab import centered_signatures, reclassify, apply_controls, POLICIES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_m43ab_attribution'
CONFIG = ROOT/'config/m43ab_attribution.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policy_decisions(audits):
    return {p:[dict(record_id=m['record_id'],
                   passes_evaluated_physical_vetoes=m['passes_evaluated_physical_vetoes'],
                   physical_disposition=m['physical_disposition'],
                   rejections=m.get('m43ab_rejections', m.get('m43z_rejections', [])))
               for m in a['members']] for p, a in audits.items()}


def costs(endpoints, baseline_counts):
    out = {}
    for panel in ('historical', 'fresh'):
        refs = {r['name']:r for r in endpoints if r['panel'] == panel and r['policy'] == 'neighbor9'}
        for policy in POLICIES:
            rows = [r for r in endpoints if r['panel'] == panel and r['policy'] == policy]
            gains = []; losses = []; added = []; removed = []
            for r in rows:
                old = refs[r['name']]
                if r['signal_present']:
                    if r['recovered'] and not old['recovered']: gains.append(r['name'])
                    if old['recovered'] and not r['recovered']: losses.append(r['name'])
                else:
                    if r['final_members'] and not old['final_members']: added.append(r['name'])
                    if old['final_members'] and not r['final_members']: removed.append(r['name'])
            controls = [r for r in rows if not r['signal_present']]
            cond = dict(no_signal_loss=not losses, zero_control_members=all(r['final_members'] == 0 for r in controls),
                zero_false_control_associations=all(not r['recovered'] for r in controls),
                strict_control_leak_reduction=len(removed)>len(added), zero_baseline_members=baseline_counts[policy] == 0)
            out[f'{panel}:{policy}'] = dict(signal_gains=gains, signal_losses=losses,
                added_leaking_controls=added, removed_leaking_controls=removed,
                conditions=cond, development_gate_passed=all(cond.values()))
    return out


def run(runtime, freeze):
    start_time = time.monotonic(); cfg = json.loads(CONFIG.read_text())
    assert subprocess.check_output(['git', 'show', freeze+':config/m43ab_attribution.json'], cwd=ROOT) == CONFIG.read_bytes()
    assert platform.python_version() == cfg['python_version'] and np.__version__ == cfg['numpy_version']
    for p, h in cfg['pinned_sha256'].items(): assert sha(ROOT/p) == h, p
    publication = read_sealed(OUT/'public_freeze.json')
    assert publication['commit'] == freeze and publication['remote_verified'] is True
    assert not (OUT/'result.json').exists(), 'preserve completed run'
    (OUT/'inputs').mkdir(exist_ok=True)
    _, _, _, metadata, basis, parent, parent_table, _ = build_context()
    bank, table, bridge = detector.catalogue_bridge(parent, cfg['parent_template_indices'], basis)
    assert bridge == cfg['bridge']
    original, grid, start = grid_context(); assert core.proxy_carrier_grid_sha256(grid) == cfg['grid_sha256']
    old = AnchorStore(runtime/'anchors', dict(parent_template_indices=cfg['parent_template_indices'], support_carriers=original.support_bin_count))
    arrays = {k:old.get(*k)[0][:, start:start+grid.support_bin_count] for k in old.expected_ids}
    provenance = dict(family='M43P-exact-central-slice', parent_inventory_sha256=detector.digest(old.inventory),
        parent_score_ids_sha256=detector.digest([[*k, v] for k, v in sorted(old.expected_ids.items())]),
        support_start=start, support_count=grid.support_bin_count, grid_sha256=cfg['grid_sha256'])
    assert provenance == read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline = ScoreStore(arrays, provenance)
    receiver = NativeReceiver(runtime/'sources', metadata, basis, parent, parent_table, original)
    overlay = JointOverlay(baseline, receiver, bank, table, basis, grid, progress=lambda m:print(m, flush=True))
    assert overlay.cache_inventory == read_sealed(ROOT/'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    prior = read_sealed(ROOT/'results_m43z_joint_controls/calibration.json')
    cal, threshold = restore_calibration(prior, prior['result_sha256'], prior['threshold']['certificate_sha256'])
    binding = bind_calibration(cal, threshold, 'neighbor9'); assert binding == prior['binding']
    write_sealed(OUT/'anchors.json', dict(all_96_arrays_exact=True, all_48_native_gathers_exact=True,
        calibration_restored_exactly=True, calibration_sha256=prior['result_sha256'], new_null_rows=0))
    history = {}
    with gzip.open(ROOT/'results_m43z_joint_controls/case_audits.jsonl.gz', 'rt') as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r['case']['case_index'] in cfg['historical_cases']:
                    assert r['result_sha256'] == detector.digest({k:v for k,v in r.items() if k != 'result_sha256'})
                    history[r['case']['case_index']] = r
    assert set(history) == set(cfg['historical_cases'])
    common = dict(window=WINDOW, grid=grid, bank=bank, table=table, basis=basis, scans=metadata['scans'])
    factors = np.stack([core.factor_table_for_scan(table, basis, f'epoch{e+1}_on') for e in range(3)], axis=1)
    endpoints = []; inventory = []; direct_total = 0; baseline_counts = None
    specs = [dict(name='baseline', panel='baseline', components=[], original_case_index=None)]+cfg['cases']
    for index, case in enumerate(specs):
        path = OUT/'inputs'/(case['name']+'.json.gz')
        if path.exists():
            rec = json.loads(gzip.decompress(path.read_bytes()))
            assert rec['result_sha256'] == detector.digest({k:v for k,v in rec.items() if k != 'result_sha256'})
            assert rec['freeze_commit'] == freeze and rec['case'] == case and rec['config_sha256'] == sha(CONFIG)
        else:
            store = overlay.trial(case['components'])
            if case['panel'] == 'baseline': store = baseline
            result = detector.execute(**common, store=store, mask_policy='neighbor9', calibration=cal,
                threshold=threshold, calibration_binding=binding, receiver_factory=overlay, maximum_records=cfg['maximum_records'])
            audit = compact(result, overlay.overlay_receipt); audit['masked_cell_counts'] = result['masked_cell_counts']
            audits, old_evidence = old_controls(audit, store, grid)
            if case['panel'] == 'historical':
                h = history[case['original_case_index']]
                assert audits['neighbor9'] == h['reference_audit'], case['name']
                assert old_evidence == h['confirmation_evidence'], case['name']
                for p, a in audits.items():
                    assert [{k:m[k] for k in ('record_id', 'passes_evaluated_physical_vetoes', 'physical_disposition', 'm43z_rejections')} for m in a['members']] == h['policy_decisions'][p]
            elif case['panel'] == 'baseline':
                h = read_sealed(ROOT/'results_m43z_joint_controls/baseline.json')
                assert audits == h['audits'] and old_evidence == h['evidence']
            parts = native_parts(overlay, case['components']); checks = []
            def check(e, w, raw, score):
                src = receiver.cache(f'epoch{e+1}_on', 1).source
                direct = raw_window_score(src, np.full(src.integration_count, raw), parts.get(('on', e), []), w)
                assert np.float32(direct['score']).view('<u4') == np.float32(score).view('<u4'), (case['name'], e, w)
                checks.append(dict(epoch=e, width=w, native_center=raw, score=score, exact=True))
            sigs, receipt = centered_signatures(overlay, result['retained']['on'], check)
            new_result = reclassify(result, sigs, receipt, grid, bank, table, basis, metadata['scans'], WINDOW, cfg['maximum_records'])
            new_audit = compact(new_result, overlay.overlay_receipt)
            new_audits, evidence = apply_controls(new_audit, store, grid); audits.update(new_audits)
            rows = []
            if case['panel'] != 'baseline':
                for p, a in audits.items():
                    association = endpoint(a, case['reference_truth'], grid, factors, basis, case['strength'], path.name)
                    rows.append(dict(name=case['name'], panel=case['panel'], case_index=case['case_index'],
                        original_case_index=case['original_case_index'], policy=p, case_type=case['case_type'],
                        signal_present=case['signal_present'], recovered=association['recovered'],
                        final_members=a['final_diagnostic_survivors'], truth_association=association))
            old_veto = {m['record_id'] for m in audit['members'] if m['physical_disposition'] == 'rfi_veto_receiver_frame_alias' and m['meets_diagnostic_rank_cut']}
            released = {m['record_id'] for m in new_audit['members'] if m['record_id'] in old_veto and m['passes_evaluated_physical_vetoes']}
            payload = {k:v for k,v in overlay.overlay_receipt.items() if k in ('patch_payloads', 'background_provenance')}
            rec = dict(case=case, config_sha256=sha(CONFIG), freeze_commit=freeze,
                reference_audit=audits['neighbor9'], policy_decisions=policy_decisions(audits),
                old_confirmation_evidence=old_evidence, new_confirmation_evidence=evidence,
                original_signatures=result['receiver_signatures'], centered_signatures=sigs,
                centered_receipt=receipt, centered_alias=new_result['receiver_alias'],
                original_alias=result['receiver_alias'], direct_checks=checks,
                historical_reference_exact=case['panel'] in ('historical', 'baseline'),
                native_payload_identity=detector.digest(payload), endpoints=rows,
                alias_veto_members=len(old_veto), released_alias_member_ids=sorted(released),
                final_counts={p:a['final_diagnostic_survivors'] for p,a in audits.items()})
            rec['result_sha256'] = detector.digest(rec)
            temp = path.with_suffix('.tmp'); temp.write_bytes(gzip.compress(core.canonical_json_bytes(rec), compresslevel=6, mtime=0)); temp.replace(path)
        direct_total += len(rec['direct_checks']); endpoints.extend(rec['endpoints'])
        if case['panel'] == 'baseline': baseline_counts = rec['final_counts']
        inventory.append(dict(name=case['name'], file=path.relative_to(ROOT).as_posix(), file_sha256=sha(path),
            record_sha256=rec['result_sha256'], native_payload_identity=rec['native_payload_identity'],
            released_alias_members=len(rec['released_alias_member_ids']), alias_veto_members=rec['alias_veto_members']))
        print(f"{index+1}/{len(specs)} {case['name']} {rec['final_counts']}", flush=True)
        write_sealed(OUT/'progress.json', dict(complete=False, completed_inputs=index+1, planned_inputs=len(specs)))
    summary = []
    for panel in ('historical', 'fresh'):
        for p in cfg['policies']:
            rows = [r for r in endpoints if r['panel'] == panel and r['policy'] == p]
            signal = [r for r in rows if r['signal_present']]; control = [r for r in rows if not r['signal_present']]
            summary.append(dict(panel=panel, policy=p, signal_inputs=len(signal), control_inputs=len(control),
                recovered_signals=sum(r['recovered'] for r in signal), leaking_controls=sum(r['final_members']>0 for r in control),
                false_control_associations=sum(r['recovered'] for r in control)))
    write_sealed(OUT/'result.json', dict(milestone='M43AB', complete=True, freeze_commit=freeze,
        base_executions_including_baseline=len(specs), paired_endpoints_including_baseline=len(specs)*len(cfg['policies']),
        historical_inputs=36, fresh_inputs=112, separate_baseline=1, endpoints=endpoints, inventory=inventory,
        direct_native_checks=direct_total, baseline_counts=baseline_counts, summary=summary,
        comparisons=costs(endpoints, baseline_counts), distinct_native_payloads=len({r['native_payload_identity'] for r in inventory}),
        new_null_rows=0, new_observing_sequences=0, general_adoption_qualified=False,
        astronomical_candidate_claimed=False, physical_false_alarm_probability_measured=False,
        prior_M43X_Z_failed_gates_remain=True, wall_seconds=round(time.monotonic()-start_time, 3)))
    write_sealed(OUT/'progress.json', dict(complete=True, completed_inputs=len(specs), planned_inputs=len(specs)))
    print('M43AB COMPLETE', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--runtime-root', type=Path, required=True)
    parser.add_argument('--freeze', required=True); args = parser.parse_args()
    run(args.runtime_root, args.freeze)
