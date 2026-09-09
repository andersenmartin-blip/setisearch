"""Retrospective descriptors of frozen M43AB results; no new detector rule."""
import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43r_joint_calibration import grid_context
from seti_repeater import detector_m43u as detector, search_v0p6 as core

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43ac_dual_evidence'
SOURCE = ROOT / 'results_m43ab_attribution'
NEW = 'centered_receiver_off_match_aggregate'
FOCAL = ('z170', 'z171', 'z280', 'z281', 'z096', 'z138', 'fresh032',
         'z324', 'z336', 'z346', 'z260', 'z261', 'z265')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_records():
    result = read_sealed(SOURCE / 'result.json')
    for item in result['inventory']:
        path = ROOT / item['file']
        assert sha(path) == item['file_sha256'], path
        rec = json.loads(gzip.decompress(path.read_bytes()))
        assert rec['result_sha256'] == item['record_sha256']
        assert detector.digest({k: v for k, v in rec.items() if k != 'result_sha256'}) == rec['result_sha256']
        yield item, rec


def context():
    cfg = json.loads((ROOT / 'config/m43ab_attribution.json').read_text())
    for p, h in cfg['pinned_sha256'].items():
        assert sha(ROOT / p) == h, p
    _, _, _, metadata, basis, parent, parent_table, _ = build_context()
    bank, table, bridge = detector.catalogue_bridge(parent, cfg['parent_template_indices'], basis)
    assert bridge == cfg['bridge']
    original, grid, start = grid_context()
    assert core.proxy_carrier_grid_sha256(grid) == cfg['grid_sha256']
    return cfg, metadata, basis, parent, parent_table, bank, table, original, grid, start


def final_ids(rec, policy):
    eligible = {m['record_id'] for m in rec['reference_audit']['members'] if m['meets_diagnostic_rank_cut']}
    return {d['record_id'] for d in rec['policy_decisions'][policy]
            if d['passes_evaluated_physical_vetoes'] and d['record_id'] in eligible}


def witness_trace(rec, rid):
    old = next(m for m in rec['original_alias']['records'] if m['record_id'] == rid)
    witness = old['receiver_alias_evidence']['best_receiver_alias_witness']
    if witness is None:
        return None
    wid = witness['record_id']
    assert wid != rid
    rows = []
    for old_match in witness['matched_active_epochs']:
        e = old_match['epoch_zero_based']
        a = next(s for s in rec['centered_signatures'][rid] if s['epoch_zero_based'] == e)
        b = next(s for s in rec['centered_signatures'][wid] if s['epoch_zero_based'] == e)
        qualified = a['peak_snr'] >= 5.5 and b['peak_snr'] >= 5.5
        delta = abs(a['peak_frequency_mhz'] - b['peak_frequency_mhz']) * 1e6
        rows.append(dict(epoch=e, old_match=old_match, centered_left=a, centered_right=b,
                         both_centered_above_floor=qualified, centered_separation_hz=delta,
                         centered_pair_matches=qualified and delta <= 20.))
    # Include shared epochs which did not qualify for the old witness too.
    old_epochs = {r['epoch'] for r in rows}
    left = {s['epoch_zero_based']: s for s in rec['centered_signatures'][rid]}
    right = {s['epoch_zero_based']: s for s in rec['centered_signatures'][wid]}
    for e in sorted(left.keys() & right.keys() - old_epochs):
        a, b = left[e], right[e]
        qualified = a['peak_snr'] >= 5.5 and b['peak_snr'] >= 5.5
        delta = abs(a['peak_frequency_mhz'] - b['peak_frequency_mhz']) * 1e6
        rows.append(dict(epoch=e, old_match=None, centered_left=a, centered_right=b,
                         both_centered_above_floor=qualified, centered_separation_hz=delta,
                         centered_pair_matches=qualified and delta <= 20.))
    qualified = sum(r['both_centered_above_floor'] for r in rows)
    matched = sum(r['centered_pair_matches'] for r in rows)
    cause = ('fewer_than_two_shared_centered_epochs_above_floor' if qualified < 2 else
             'centered_peak_separation' if matched < 2 else 'old_witness_still_matches')
    return dict(witness_record_id=wid, cause=cause, epochs=sorted(rows, key=lambda r: r['epoch']))


def geometry(rec, member, factors, grid):
    rid = member['record_id']; t = member['template_index']; q = member['proxy_carrier_index']
    width = member['spectral_width_channels']; spacing = abs(grid.channel_width_hz)
    out = []
    for old, centered in zip(rec['original_signatures'][rid], rec['centered_signatures'][rid]):
        e = old['epoch_zero_based']; assert e == centered['epoch_zero_based']
        track = grid.score_hz[q] * factors[e][t]
        midpoint = old['predicted_mid_mhz'] * 1e6
        half = width // 2 * spacing
        # Half-channel allowance describes nearest-channel quantization, not a
        # fitted source extent. The envelope does not prove common origin.
        lo = float(track.min() - midpoint - half - spacing / 2)
        hi = float(track.max() - midpoint + half + spacing / 2)
        offset = old['offset_from_prediction_hz']
        out.append(dict(epoch=e, original=old, centered=centered,
                        filter_half_span_hz=half, native_channel_spacing_hz=spacing,
                        predicted_track_span_hz=float(np.ptp(track)),
                        track_filter_envelope_offsets_hz=[lo, hi],
                        peak_inside_midpoint_filter=abs(offset) <= half + spacing / 2,
                        peak_inside_track_filter_envelope=lo <= offset <= hi,
                        peak_minus_center_snr=old['peak_snr'] - centered['peak_snr']))
    return out


def ledger():
    assert not (OUT / 'ledger_summary.json').exists(), 'preserve completed ledger'
    OUT.mkdir(exist_ok=True); (OUT / 'focal').mkdir(exist_ok=True)
    cfg, metadata, basis, parent, pt, bank, table, original, grid, start = context()
    factors = [core.factor_table_for_scan(table, basis, f'epoch{e+1}_on') for e in range(3)]
    inventory = []; summaries = []; all_causes = Counter(); totals = Counter()
    for item, rec in source_records():
        inventory.append(item); name = rec['case']['name']
        members = {m['record_id']: m for m in rec['reference_audit']['members']}
        old_alias = {rid for rid, m in members.items() if m['meets_diagnostic_rank_cut']
                     and m['physical_disposition'] == 'rfi_veto_receiver_frame_alias'}
        released = old_alias & final_ids(rec, 'centered_receiver')
        assert released == set(rec['released_alias_member_ids'])
        surviving = released & final_ids(rec, NEW)
        traces = {rid: witness_trace(rec, rid) for rid in released}
        causes = Counter(v['cause'] for v in traces.values())
        assert not causes['old_witness_still_matches']
        all_causes.update(causes)
        totals.update(inputs=1, members=len(members), old_alias=len(old_alias),
                      released=len(released), released_final=len(surviving))
        summaries.append(dict(name=name, panel=rec['case']['panel'],
            signal_present=rec['case'].get('signal_present'), old_alias=len(old_alias),
            released=len(released), released_final=len(surviving), witness_causes=dict(causes),
            final_counts=rec['final_counts']))
        if name in FOCAL:
            associations = {e['policy']: e['truth_association']['associated_record_ids'] for e in rec['endpoints']}
            selected = set(associations[NEW]) | surviving
            if not rec['case']['signal_present']:
                selected |= final_ids(rec, NEW)
            rows = []
            for rid in sorted(selected):
                m = members[rid]
                rows.append(dict(member=m, geometry=geometry(rec, m, factors, grid),
                    old_best_witness=witness_trace(rec, rid),
                    original_alias_evidence=next(r['receiver_alias_evidence'] for r in rec['original_alias']['records'] if r['record_id'] == rid),
                    centered_alias_evidence=next(r['receiver_alias_evidence'] for r in rec['centered_alias']['records'] if r['record_id'] == rid),
                    decisions={p: next(d for d in ds if d['record_id'] == rid) for p, ds in rec['policy_decisions'].items()},
                    old_confirmation=next(r for r in rec['old_confirmation_evidence'] if r['record_id'] == rid),
                    new_confirmation=next(r for r in rec['new_confirmation_evidence'] if r['record_id'] == rid)))
            # Shard text so each GitHub tree entry stays small and reviewable.
            files = []
            for i in range(0, len(rows), 8):
                p = OUT / 'focal' / f'{name}.{i//8:03d}.json'
                write_sealed(p, dict(name=name, members=rows[i:i+8])); files.append(p.relative_to(ROOT).as_posix())
            write_sealed(OUT / 'focal' / f'{name}.json', dict(source=item, case=rec['case'],
                summary=summaries[-1], associations=associations, member_files=files,
                selection='all truth-associated members, plus released final members; controls include all new final members'))
        print(f'{name}: old alias {len(old_alias)}, released {len(released)}, final {len(surviving)}', flush=True)
    write_sealed(OUT / 'ledger_summary.json', dict(milestone='M43AC', retrospective=True,
        source_commit='2612645426a348bcbf02917c110751e24671be57',
        source_result_sha256=sha(SOURCE / 'result.json'), sources=inventory,
        totals=dict(totals), old_best_witness_causes=dict(all_causes), inputs=summaries,
        new_detector_executions=0, new_endpoint=False, new_null_rows=0))
    print(json.dumps(dict(totals=totals, causes=all_causes)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.parse_args(); ledger()
