#!/usr/bin/env python3
"""Predeclare residual-domain engineering injection identities using JSON geometry only."""
import hashlib
import json
import resource
import signal
import time
from collections import Counter
from fractions import Fraction
from pathlib import Path

BASE = Path('/workspace/scratch/b83cfe20d6e1/checkpoints/SETI_NATIVE_SPOR_2026-10-14/SETI_NATIVE_SPOR_2026-10-14')
OUT = Path('/workspace/scratch/b83cfe20d6e1/retention_validation_20261014')
DRIFTS = (Fraction(-83, 100), Fraction(47, 100))
PHASES = (Fraction(-41, 100), Fraction(13, 100))
HOSTS = (-768, 768)
DF = Fraction.from_float(-2.7939677238464355)
H = Fraction.from_float(4 / 158)
DC = {178782208, 179830784, 180879360}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(path):
    return dict(path=path.relative_to(BASE).as_posix(), bytes=path.stat().st_size, sha256=sha(path))


def encode(q):
    return [str(q.numerator), str(q.denominator)]


def even(q):
    n, rem = divmod(q.numerator, q.denominator)
    twice = rem * 2
    return n + int(twice > q.denominator or twice == q.denominator and n % 2 != 0)


def create(path, obj):
    with path.open('x', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')


def main():
    start = time.perf_counter()
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    signal.alarm(300)
    gf = BASE / 'rounding_followup/exact_geometry_results/GEOMETRY.json'
    mf = BASE / 'seti_work/seti_burst_full/context_results/CONTEXT_PROFILES.json'
    tf = BASE / 'rounding_followup/results/INJECTIONS.json'
    g = json.loads(gf.read_bytes())
    m = json.loads(mf.read_bytes())
    old = json.loads(tf.read_bytes())
    assert g['counts']['profiles'] == 54
    assert g['counts']['total_unique_paths_zero_offset'] == 22235
    assert g['path_order'] == 'window_start_row_slow_native_four_channel_tuple_lexicographic_fast'
    profiles = {p['profile_id']: p for p in m['profiles']}
    crops = {c['crop_id']: c for c in m['normalization_crops']}
    old_place = set()
    old_relative = set()
    for t in old['trials']:
        rows = tuple(t['true_active_source_rows'])
        host = t['host_offset_channels']
        for field in ('canonical_float_truth_absolute_centers', 'canonical_rational_truth_absolute_centers'):
            bins = tuple(t[field][r] for r in rows)
            old_place.add((t['profile_id'], rows, bins))
            old_relative.add((t['profile_id'], rows, tuple(b - host for b in bins)))
    assert {t['host_offset_channels'] for t in old['trials']} == {512}
    dedup = {}
    support_intervals = []
    all_path_checks = 0
    all_path_dc = 0
    draw_sequence = 0
    unavailable = []
    for family in g['profiles']:
        pid = family['profile_id']
        p = profiles[pid]
        crop = crops[p['normalization_crop_id']]
        lo, hi = crop['source_channel_interval_half_open']
        assert hi - lo == 12096
        assert crop['normalization_source_channel_interval_half_open'] == [lo + 4000, lo + 8096]
        assert p['times_from_primary_reference_s'] == family['times_from_primary_reference_s']
        assert p['selected_track']['source_reference_channel'] == family['source_reference_channel']
        assert p['selected_track']['drift_hz_s'] == family['original_drift_hz_s']
        times = [Fraction.from_float(t) for t in family['times_from_primary_reference_s']]
        base = family['source_reference_channel']
        d0 = Fraction.from_float(family['original_drift_hz_s'])
        for w in family['windows']:
            wi = w['window_index']
            rows = tuple(w['window_source_rows'])
            assert rows == tuple(range(2 * wi, 2 * wi + 4))
            lookup = {tuple(p['channels']) for p in w['paths']}
            assert len(lookup) == w['unique_paths']
            for host in HOSTS:
                all_bins = [b + host for path in lookup for b in path]
                assert min(all_bins) - 250 >= lo and max(all_bins) + 250 < hi
                support_intervals.append((min(all_bins) - 250 - lo, max(all_bins) + 250 - lo))
                all_path_checks += len(lookup)
                all_path_dc += sum(any(b + host in DC for b in path) for path in lookup)
                for di, fraction in enumerate(DRIFTS):
                    for pi, phase in enumerate(PHASES):
                        draw_sequence += 1
                        delta = fraction * H
                        truth = [even(Fraction(base + host) + phase + (d0 + delta) * t / DF) for t in times]
                        bins = tuple(truth[r] for r in rows)
                        native = tuple(b - host for b in bins)
                        draw = dict(draw_id=f'D{draw_sequence:05d}', drift_fraction_index=di,
                                    phase_index=pi, drift_fraction=encode(fraction), phase_fraction=encode(phase),
                                    delta_drift_fraction=encode(delta), canonical_truth16=truth)
                        reasons = []
                        if native not in lookup:
                            reasons.append('UNATTAINABLE_IN_FROZEN_EXACT_FAMILY')
                        if any(b in DC for b in bins):
                            reasons.append('SELECTED_ACTIVE4_DC_CONTACT')
                        if not (min(bins) - 250 >= lo and max(bins) + 250 < hi):
                            reasons.append('RAW501_CROP_INCOMPLETE')
                        key = (pid, host, rows, bins)
                        if reasons:
                            unavailable.append(dict(profile_id=pid, host_offset_channels=host, window_index=wi,
                                                    draw=draw, reasons=reasons))
                            continue
                        if key not in dedup:
                            dedup[key] = dict(profile_id=pid, origin_scan_id=family['origin_scan_id'],
                                context_scan_id=family['context_scan_id'], origin_rank=family['origin_rank'],
                                host_offset_channels=host, true_window_index=wi, true_window_start_row=2 * wi,
                                true_active_source_rows=list(rows), native4=list(native), truth_active4=list(bins),
                                truth16=truth, drift_fraction=encode(fraction), phase_fraction=encode(phase),
                                alias_draw_count=0, draws=[], canonical_placement_seen_in_prior=key[:1] + (rows, bins) in old_place,
                                native4_seen_in_prior_same_profile_window=(pid, rows, native) in old_relative,
                                raw501_crop_complete=True, exact_search_lookup_complete=True,
                                selected_active4_dc_contact=False)
                        item = dedup[key]
                        item['alias_draw_count'] += 1
                        item['draws'].append(draw)
    records = list(dedup.values())
    for i, item in enumerate(records, 1):
        item['geometry_id'] = f'G{i:05d}'
    assert draw_sequence == 3024
    assert not unavailable
    assert not any(t['canonical_placement_seen_in_prior'] for t in records)
    assert all_path_checks == 22235 * 2
    old_native_count = sum(t['native4_seen_in_prior_same_profile_window'] for t in records)
    cpu = resource.getrusage(resource.RUSAGE_SELF)
    manifest = dict(schema='SETI_PREDECLARED_RETENTION_GEOMETRY_V1', date='2026-10-14',
        frozen_policy_commit='f1108023a7bf7e2700d97a0b31c6eb30d9fa1f14',
        status='PASS_METADATA_ONLY_GEOMETRY_AVAILABILITY',
        geometry_arithmetic='Separate exact Fraction.from_float for saved binary64 d0/time/DF/half_step; exact new rational fractions and phases; exact nearest-ties-even rounding; all-even offsets preserve parity.',
        design=dict(drift_fractions=[encode(q) for q in DRIFTS], phases=[encode(q) for q in PHASES],
                    host_offset_channels=list(HOSTS), window_start_rows=list(range(0, 13, 2)), amplitudes=[0, 2, 8],
                    nominal_geometry_draws=3024, retention_k=[1, 5],
                    canonical_truth='exact rational affine rounding, no canonical float truth reuse',
                    dedup_key=['profile_id','host_offset_channels','true_active_source_rows','truth_active4'],
                    aliases='All four parameter draws preserved; score once per unique placement/amplitude; representative truth16 from first draw, other truth16 in alias mappings.',
                    A0_interpretation='Sham-target rank on exposed residual background; no injected signal, recovery or calibrated false-alarm claim.'),
        counts=dict(profiles=54, nominal_geometry_draws=3024, available_geometry_draws=3024,
                    unique_geometry_placements=len(records), duplicate_alias_draws=3024-len(records),
                    amplitude_levels=3, scored_trial_rows=3*len(records), unavailable_geometry_draws=0,
                    prior_absolute_placement_collisions=0, prior_same_window_native4_collisions=old_native_count,
                    unique_geometry_native4_unseen_in_prior=len(records)-old_native_count,
                    all_search_path_host_availability_checks=all_path_checks,
                    all_search_path_host_selected4_DC_contacts=all_path_dc,
                    alias_draw_count_histogram={str(k): v for k,v in sorted(Counter(r['alias_draw_count'] for r in records).items())}),
        raw501_support_crop_indices_inclusive=[min(a for a,b in support_intervals),max(b for a,b in support_intervals)],
        offsets_availability='-768 and +768 both pre-existing frozen score-array offsets; every frozen search native4 bin has unchanged raw501 support within preserved12096 crop.',
        input_pins=[pin(gf),pin(mf),pin(tf)],
        geometries=records, unavailable_draws=unavailable,
        interpretation=['New parameter identities and absolute injection placements on already exposed2017 residual scores.',
            'Some new parameter choices alias old relative native4 trajectories; report separately without freshness claim.',
            'This is prospective conditional retention engineering after k5 freeze, not fresh observed data, physical sensitivity or qualification validation.',
            'Overlapping windows, geometric aliases, origins and shared source crops are dependent; unique trial count is computational only.',
            'A0/2/8 are paired amplitude perturbations, not independent replicates.'],
        spectral_arrays_opened=False, new_observed_outcomes_scored=False,
        resource_usage=dict(CPU_s=cpu.ru_utime+cpu.ru_stime, wall_s=time.perf_counter()-start, peak_RSS_bytes=cpu.ru_maxrss*1024),
        budget=dict(metadata_CPU_s_cap=60, wall_s_cap=300, memory_bytes_cap=1024**3,
                    incremental_reserved_CPU_s=180, producer_CPU_s_cap=60, QA_CPU_s_cap=60,
                    prior_ledger_retained=True,new_telescope_requests=0,new_telescope_bytes=0,DKK=0),
        preserved=dict(original_A_B='FAIL_CLOSED', protected_2016=True, closed_2019=True,
                       qualified_SETI_detection=False, calibrated_FAP=False, new_observation=False,
                       checkpoint='2026-10-20'))
    OUT.mkdir(parents=True, exist_ok=True)
    create(OUT/'GEOMETRY_MANIFEST.json', manifest)
    print(json.dumps({k: manifest[k] for k in ('status','counts','raw501_support_crop_indices_inclusive','resource_usage')}))


if __name__ == '__main__':
    main()
