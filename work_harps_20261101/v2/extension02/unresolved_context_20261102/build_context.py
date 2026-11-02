#!/usr/bin/env python3
"""Descriptive joins/grouping of existing HARPS measurements; no pixel reads."""
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = 115000.0


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def truth(value):
    assert value in ('True', 'False'), value
    return value == 'True'


def csv_out(name, data):
    assert data, name
    fields = list(data[0])
    with (HERE / name).open('w', newline='') as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(data)


def components(events, relation, prefix):
    neighbors = {r['candidate_id']: set() for r in events}
    links = []
    for i, a in enumerate(events):
        for b in events[i+1:]:
            if a['target'] != b['target']:
                continue
            delta = abs(a['center_bary_air_angstrom'] - b['center_bary_air_angstrom'])
            nominal = (a['center_bary_air_angstrom'] + b['center_bary_air_angstrom']) / (2 * R)
            threshold = nominal if relation == 'resolution' else 0.5
            if delta <= threshold:
                neighbors[a['candidate_id']].add(b['candidate_id'])
                neighbors[b['candidate_id']].add(a['candidate_id'])
                links.append({'candidate_a': a['candidate_id'], 'candidate_b': b['candidate_id'],
                              'target': a['target'], 'separation_angstrom': delta,
                              'separation_nominal_resolution_elements': delta / nominal,
                              'edge_limit_angstrom': threshold,
                              'same_source_exposure': a['dp_id'] == b['dp_id']})
    byid = {r['candidate_id']: r for r in events}
    unseen = set(byid)
    groups = []
    while unseen:
        seed = min(unseen)
        todo = [seed]
        found = set()
        while todo:
            item = todo.pop()
            if item in found:
                continue
            found.add(item)
            todo.extend(neighbors[item] - found)
        unseen -= found
        groups.append(sorted(found))
    groups.sort(key=lambda g: (byid[g[0]]['target'], min(byid[i]['center_bary_air_angstrom'] for i in g), g[0]))
    assignment = {}
    table = []
    for n, members in enumerate(groups, 1):
        gid = f'{prefix}{n:03d}'
        selected = [byid[i] for i in members]
        waves = [e['center_bary_air_angstrom'] for e in selected]
        span = max(waves) - min(waves)
        span_nominal = span / ((min(waves) + max(waves)) / (2 * R))
        pair_limit = (min(waves) + max(waves)) / (2 * R) if relation == 'resolution' else 0.5
        result = {'group_id': gid, 'target': selected[0]['target'], 'events': len(members),
                  'distinct_source_exposures': len({e['dp_id'] for e in selected}),
                  'minimum_center_bary_air_angstrom': min(waves), 'maximum_center_bary_air_angstrom': max(waves),
                  'center_span_angstrom': span, 'center_span_nominal_resolution_elements': span_nominal,
                  'endpoint_span_exceeds_one_edge': span > pair_limit,
                  'any_low_continuum_context': any(e['any_low_continuum_context'] for e in selected),
                  'frame_span_below_one_resolution_element': selected[0]['frame_span_below_one_resolution_element'],
                  'berv_span_km_s': selected[0]['berv_span_km_s'],
                  'member_ids': '|'.join(members)}
        for frame in ('barycentric', 'topocentric'):
            values = [e[f'{frame}_other_correlation_median'] for e in selected]
            finite = [v for v in values if v is not None]
            result[f'{frame}_event_median_correlation_min'] = min(finite) if finite else None
            result[f'{frame}_event_median_correlation_max'] = max(finite) if finite else None
        table.append(result)
        for item in members:
            assignment[item] = result
    return assignment, table, links


def main():
    plan = json.loads((HERE / 'PLAN.json').read_text())
    freeze = json.loads((HERE / 'FREEZE.json').read_text())
    assert freeze['plan_sha256'] == sha(HERE / 'PLAN.json')
    assert freeze['script_sha256'] == sha(Path(__file__))
    sources = {}
    for entry in plan['source_files']:
        path = HERE / entry['snapshot_path']
        assert sha(path) == entry['sha256']
        sources[entry['source_path'].split('extension02/', 1)[1]] = path
    current = rows(sources['raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv'])
    selected = [r for r in current if r['current_code'] == 'U']
    assert [r['candidate_id'] for r in selected] == plan['scope']['selected_ids']
    catalog = {r['candidate_id']: r for r in rows(sources['production/V2_HITS.csv'])}
    epochs = {r['candidate_id']: r for r in rows(sources['epoch_followup/EVENT_SUMMARY.csv'])}
    measurements = defaultdict(list)
    for row in rows(sources['epoch_followup/ALL_EPOCH_MEASUREMENTS.csv']):
        measurements[row['candidate_id']].append(row)
    output = []
    selected_measurements = []
    for disposition in selected:
        cid = disposition['candidate_id']
        cat, epoch = catalog[cid], epochs[cid]
        assert disposition['dp_id'] == cat['dp_id'] == epoch['source_dp_id']
        assert disposition['target'] == cat['canonical_target'] == epoch['target']
        assert disposition['source_input_sha256'] == cat['input_sha256']
        wave = float(cat['fitted_center_angstrom'])
        assert wave == float(epoch['fitted_center_bary_air_angstrom'])
        event = {'candidate_id': cid, 'target': disposition['target'], 'dp_id': disposition['dp_id'],
                 'selection_index': int(disposition['selection_index']), 'source_input_sha256': cat['input_sha256'],
                 'current_code_unchanged': 'U', 'center_bary_air_angstrom': wave,
                 'nominal_resolution_angstrom': wave / R,
                 'production_fixed_template_fwhm_angstrom': float(cat['fwhm_model_angstrom']),
                 'width_is_measured': False,
                 'other_epochs': int(epoch['other_epochs']),
                 'berv_span_km_s': float(epoch['berv_span_km_s']),
                 'berv_span_resolution_elements': float(epoch['berv_span_resolution_elements']),
                 'frame_span_below_one_resolution_element': truth(epoch['frame_separation_below_one_resolution_element']),
                 'median_correlation_bary_minus_topo': number(epoch['median_correlation_bary_minus_topo']),
                 'raw_evidence_table': disposition['current_evidence_table'],
                 'raw_evidence': disposition['current_evidence']}
        all_low = False
        for frame in ('barycentric', 'topocentric'):
            sub = [m for m in measurements[cid] if m['frame'] == frame]
            discovery = [m for m in sub if truth(m['is_discovery_exposure'])]
            other = [m for m in sub if not truth(m['is_discovery_exposure'])]
            assert len(discovery) == 1
            assert len(other) == int(epoch['other_epochs'])
            assert len({m['dp_id'] for m in sub}) == len(sub)
            assert discovery[0]['dp_id'] == cat['dp_id']
            assert all(m['target'] == disposition['target'] for m in sub)
            disc = discovery[0]
            low_count = sum(truth(m['local_continuum_low']) for m in other)
            assert low_count == int(epoch[f'{frame}_other_low_continuum_count'])
            all_low |= low_count > 0 or truth(disc['local_continuum_low'])
            event[f'{frame}_discovery_low_continuum'] = truth(disc['local_continuum_low'])
            event[f'{frame}_other_low_continuum_count'] = low_count
            event[f'{frame}_other_correlation_median'] = number(epoch[f'{frame}_other_correlation_to_discovery_median'])
            event[f'{frame}_other_correlation_q25'] = number(epoch[f'{frame}_other_correlation_to_discovery_q25'])
            event[f'{frame}_other_correlation_q75'] = number(epoch[f'{frame}_other_correlation_to_discovery_q75'])
            event[f'{frame}_other_narrow_amplitude_median'] = number(epoch[f'{frame}_other_narrow_amplitude_median'])
            for column in ('normalization_adu', 'first_difference_noise_proxy_adu', 'narrow_amplitude', 'narrow_residual_rms', 'broad3_amplitude', 'broad3_residual_rms'):
                event[f'{frame}_discovery_{column}'] = number(disc[column])
            nrms = number(disc['narrow_residual_rms'])
            brms = number(disc['broad3_residual_rms'])
            event[f'{frame}_discovery_broad3_to_narrow_rms'] = brms / nrms if nrms is not None and nrms > 0 and brms is not None else None
            ratios = [float(m['broad3_residual_rms']) / float(m['narrow_residual_rms']) for m in other
                      if number(m['broad3_residual_rms']) is not None and number(m['narrow_residual_rms']) is not None and float(m['narrow_residual_rms']) > 0]
            event[f'{frame}_other_broad3_to_narrow_rms_median'] = statistics.median(ratios) if ratios else None
            event[f'{frame}_other_broad3_to_narrow_rms_n'] = len(ratios)
        event['any_low_continuum_context'] = all_low
        output.append(event)
        selected_measurements.extend(measurements[cid])
    resmap, restable, resedges = components(output, 'resolution', 'R')
    coremap, coretable, coreedges = components(output, 'core', 'C')
    actions = []
    for event in output:
        cid = event['candidate_id']
        res, core = resmap[cid], coremap[cid]
        event['resolution_group'] = res['group_id']
        event['resolution_group_events'] = res['events']
        event['core_overlap_group'] = core['group_id']
        event['core_overlap_group_events'] = core['events']
        if event['any_low_continuum_context']:
            route, next_evidence = 'NORMALIZATION_CONTEXT', plan['work_queues']['next_evidence'][0]
        elif event['frame_span_below_one_resolution_element']:
            route, next_evidence = 'FRAME_BASELINE_CONTEXT', plan['work_queues']['next_evidence'][1]
        elif core['events'] > 1:
            route, next_evidence = 'JOINT_PROFILE_CONTEXT', plan['work_queues']['next_evidence'][2]
        else:
            route, next_evidence = 'INDIVIDUAL_PROFILE_CONTEXT', plan['work_queues']['next_evidence'][3]
        event['primary_evidence_route'] = route
        actions.append({'queue_index': len(actions)+1, 'candidate_id': cid, 'target': event['target'],
                        'dp_id': event['dp_id'], 'current_code_unchanged': 'U', 'primary_evidence_route': route,
                        'any_low_continuum_context': event['any_low_continuum_context'],
                        'frame_span_below_one_resolution_element': event['frame_span_below_one_resolution_element'],
                        'resolution_group': res['group_id'], 'core_overlap_group': core['group_id'],
                        'next_evidence_needed': next_evidence,
                        'priority_context': 'After pending raw review and project mapping-limited queue; route is not a likelihood ranking.'})
    csv_out('EVENT_CONTEXT.csv', output)
    csv_out('RESOLUTION_GROUPS.csv', restable)
    csv_out('CORE_OVERLAP_GROUPS.csv', coretable)
    csv_out('RESOLUTION_PAIR_EDGES.csv', resedges)
    csv_out('CORE_OVERLAP_PAIR_EDGES.csv', coreedges)
    csv_out('ACTION_QUEUE.csv', actions)
    csv_out('SELECTED_EXISTING_EPOCH_MEASUREMENTS.csv', selected_measurements)
    summary = {'schema': 'HARPS_UNRESOLVED_CONTEXT_SUMMARY_V1', 'status': 'COMPLETE_DESCRIPTIVE_AGGREGATION_NO_NEW_CLASSIFICATIONS',
               'selected_events': len(output), 'selected_targets': len({e['target'] for e in output}),
               'selected_discovery_exposures': len({e['dp_id'] for e in output}),
               'existing_epoch_measurement_rows_reused': len(selected_measurements),
               'existing_other_epoch_measurement_rows_reused': sum(not truth(m['is_discovery_exposure']) for m in selected_measurements),
               'existing_distinct_comparison_exposures': len({m['dp_id'] for m in selected_measurements}),
               'new_flux_measurements': 0, 'new_observations': 0, 'changed_classifications': 0,
               'resolution_groups': len(restable), 'resolution_multi_event_groups': sum(g['events'] > 1 for g in restable),
               'resolution_group_singletons': sum(g['events'] == 1 for g in restable),
               'resolution_groups_with_chain_span': sum(g['endpoint_span_exceeds_one_edge'] for g in restable),
               'core_overlap_groups': len(coretable), 'core_overlap_multi_event_groups': sum(g['events'] > 1 for g in coretable),
               'core_overlap_group_singletons': sum(g['events'] == 1 for g in coretable),
               'core_overlap_groups_with_chain_span': sum(g['endpoint_span_exceeds_one_edge'] for g in coretable),
               'resolution_edges': len(resedges), 'core_overlap_edges': len(coreedges),
               'events_with_any_low_continuum_context': [e['candidate_id'] for e in output if e['any_low_continuum_context']],
               'events_with_frame_span_below_one_resolution_element': [e['candidate_id'] for e in output if e['frame_span_below_one_resolution_element']],
               'primary_evidence_routes': dict(Counter(e['primary_evidence_route'] for e in output)),
               'per_target_events': dict(Counter(e['target'] for e in output)),
               'plan_sha256': sha(HERE / 'PLAN.json'), 'script_sha256': sha(Path(__file__)),
               'source_snapshots_unchanged': True, 'limitations': plan['limits']}
    (HERE / 'SUMMARY.json').write_text(json.dumps(summary, indent=2)+'\n')
    results = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in HERE.glob('*.csv')}
    results['SUMMARY.json'] = {'sha256': sha(HERE / 'SUMMARY.json'), 'bytes': (HERE / 'SUMMARY.json').stat().st_size}
    (HERE / 'OUTPUT_HASHES.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('limitations', 'events_with_frame_span_below_one_resolution_element', 'events_with_any_low_continuum_context')}, indent=2))


if __name__ == '__main__':
    main()
