#!/usr/bin/env python3
"""Prepare metadata for a new experiment; never generate or activate controls."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

from seti_repeater.empty_null_radio import ProposedReferenceDesign, canonical

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = 'e5841013b40b069eceb5fb7d5d64fd31a01b8764'
DESIGN = 'radio-hd189733-whole-cadence-null-20260928-v1'
OUT = ROOT / 'results_radio_empty_null_method_2026-09-28/proposal01'
CONFIG = ROOT / 'config/radio_whole_cadence_null_proposal_20260928.json'
OLD_RESERVATION = 'results_radio_hd189733_receiver_2026-09-28/control_identity_reservation.json'
MAP = 'results_radio_hd189733_score_map_2026-09-28/result.json'
GEOMETRY = 'results_radio_hd189733_geometry_2026-09-27/window_geometry.json'
OLD_PANEL = 'config/radio_hd189733_panel_20260928.json'


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def published(path):
    return subprocess.check_output(['git', 'show', CHECKPOINT + ':' + path], cwd=ROOT)


def scalars(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from scalars(child)
    elif isinstance(value, list):
        for child in value:
            yield from scalars(child)
    elif isinstance(value, (str, int)) and not isinstance(value, bool):
        yield value


def main():
    if OUT.exists() or CONFIG.exists():
        raise ValueError('Proposal already materialized; inspect it instead of replacing it')
    old = json.loads(published(OLD_RESERVATION))
    panel = json.loads(published(OLD_PANEL))
    score_map = json.loads(published(MAP))
    geometry = json.loads(published(GEOMETRY))
    tables = {row['role']: row for row in score_map['tables']}
    source_context = tables['calibration']['context_sha256']
    destination_context = tables['validation']['context_sha256']
    law = {
        'schema': 'radio-whole-cadence-proposed-noise-law-v1',
        'domain': 'synthetic digital power; not telescope noise',
        'ideal_model': 'independent Gaussian entries, mean 100, standard deviation 1, then float32',
        'implementation_model': 'NumPy Generator(PCG64(SeedSequence([case seed, scan index])))',
        'scan_indices': list(range(6)), 'rows_per_scan': 16, 'channels_per_row': 65536,
        'order': 'scan index, integration row, ascending native channel',
        'generator_calls': 'one normal(100., 1., 65536).astype(<f4) per row',
        'calibration_injection': None, 'calibration_comb': False,
        'normalization': 'existing pinned normalize_synthetic_rows; 4096-channel blocks',
        'seed_derivation': 'first 8 big-endian bytes SHA256(namespace + /seed-v1)',
        'independence_from_unique_seed_hashes_proved': False,
        'rank_theorem_assumption': 'ideal independent whole-cadence draws with identical score law',
        'pseudo_random_implementation_is_exact_random_sampling': False,
    }
    null_names = tuple(f'{DESIGN}/null/{i:03d}' for i in range(127))
    evaluation_names = tuple(f'{DESIGN}/evaluation/{i:03d}' for i in range(24))
    names = null_names + evaluation_names
    seeds = tuple(int.from_bytes(hashlib.sha256((name+'/seed-v1').encode()).digest()[:8], 'big')
                  for name in names)
    design = ProposedReferenceDesign(DESIGN, null_names, evaluation_names, seeds,
                                    digest(law), source_context, destination_context).record()
    evaluation_recipes = [copy.deepcopy(x['recipe']) for x in old['identities']
                          if x['role'] == 'evaluation']
    assert len(evaluation_recipes) == 24
    cases = []
    for index, (name, seed) in enumerate(zip(names, seeds, strict=True)):
        is_null = index < 127
        recipe = {'kind': 'noise_only'} if is_null else evaluation_recipes[index-127]
        # This changes only proposal-status metadata, not an injection parameter.
        recipe.pop('renderer_frozen', None)
        item = {
            'namespace': name, 'seed': seed,
            'role': 'calibration' if is_null else 'evaluation',
            'index': index if is_null else index-127,
            'context_sha256': source_context if is_null else destination_context,
            'source_contract_sha256': old['source_contract_sha256'],
            'noise_law_sha256': digest(law), 'recipe': recipe,
            'proposed_only': True, 'budget_charged': False, 'executed': False,
            'outcomes_may_select_settings': False,
        }
        item['identity'] = digest(item)
        cases.append(item)

    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', CHECKPOINT, 'config'],
                                    cwd=ROOT, text=True).splitlines()
    paths = sorted(p for p in paths if p.endswith('.json'))
    extras = [OLD_RESERVATION,
              'results_radio_hd189733_receiver_2026-09-28/prior_config_identifier_inventory.json']
    prior_scalars = set(); file_hashes = {}
    for path in paths + extras:
        payload = published(path)
        file_hashes[path] = hashlib.sha256(payload).hexdigest()
        prior_scalars.update(scalars(json.loads(payload)))
    compared = set(names) | set(seeds) | {x['identity'] for x in cases}
    collisions = sorted((repr(x) for x in compared & prior_scalars))
    if collisions:
        raise ValueError('Fresh proposal collides with published metadata: '+str(collisions))

    windows = []
    for row in geometry['windows']:
        if row['role'] == 'pilot':
            continue
        df = tables[row['role']]['geometry']['channel_width_hz']
        center = (row['proposed_first_on_midpoint_carrier_center_hz']/1e6)*1e6
        windows.append({
            'role': row['role'], 'archive_channel_interval_half_open': row['archive_interval'],
            'native_channel_center_endpoints_hz_inclusive':
                [row['native_frequency_low_hz'], row['native_frequency_high_hz']],
            'scored_carrier_endpoints_hz_inclusive': [center-40*df, center+40*df],
            'scored_carrier_count': 81, 'support_carrier_count': 99,
            'carrier_spacing_hz': df, 'carrier_center_hz': center,
            'context_sha256': tables[row['role']]['context_sha256'],
            'receiver_bank_sha256': tables[row['role']]['bank_sha256'],
            'native_window_identity': row['identity'],
            'telescope_values_opened': False,
        })

    limits = {
        'new_calibration_cadences': 127, 'new_evaluation_cases': 24,
        'new_evaluation_attempt_allocations': 1, 'new_development_cases': 0,
        'new_remedies': 0, 'pilots': 0, 'source_requests': 0,
        'active_seconds': 7200, 'process_rss_bytes': 512*1024**2,
        'modelled_array_bytes': 256*1024**2, 'retained_evidence_bytes': 1024**3,
        'maximum_records_per_scan_kind_case': 10000,
        'maximum_stage_canonical_bytes': 128000000,
        'identity_track_comparisons': 5000000, 'off_candidate_visits': 5000000,
    }
    prior = {
        'development_cases_spent_closed': 6, 'calibration_cadences_spent_closed': 3,
        'evaluation_values_generated': 0, 'evaluation_runs_executed': 0,
        'evaluation_attempt_allocations_charged_closed': 1,
        'old_unopened_evaluation_identities_not_reusable': 24,
        'retained_score_diagnoses_spent_closed': 1, 'remedies': 0, 'pilots': 0,
        'target_source_metadata': panel['prior_target_metadata'],
        'all_other_historical_ledgers_remain_separately_preserved': True,
    }
    cumulative = {
        'development_cases': 6, 'calibration_cadences': 130,
        'evaluation_values_generated_at_most': 24, 'evaluation_runs_executed_at_most': 1,
        'evaluation_attempt_allocations_charged_including_old_failure': 2,
        'archived_old_plus_new_evaluation_identity_count': 48,
        'remedies': 0, 'pilots': 0,
        'target_source_metadata_requests': panel['prior_target_metadata']['requests'],
        'old_conditional_scrambles_are_not_independent_cadences': True,
        'status': 'COUNTERFACTUAL_CEILING_ONLY_IF_SEPARATELY_ACTIVATED',
    }
    pins = {path: checksum for path, checksum in panel['pins'].items()
            if path.startswith('src/') or path in (GEOMETRY, MAP, OLD_RESERVATION)}
    pins[OLD_PANEL] = hashlib.sha256(published(OLD_PANEL)).hexdigest()
    for path in ('src/seti_repeater/empty_null_radio.py',
                 'scripts/radio_whole_cadence_proposal.py',
                 'RADIO_EMPTY_NULL_METHOD_2026-09-28_SCOPE.md'):
        pins[path] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    cfg = {
        'schema': 'radio-whole-cadence-null-proposal-config-v1',
        'status': 'PROPOSED_NOT_ACTIVATED', 'checkpoint': CHECKPOINT,
        'primary': 'neighbor9', 'design': design, 'noise_law': law,
        'windows': windows, 'cases': cases, 'gates': old['gates'],
        'association_rule': old['association_rule'],
        'score_bank': {'rate_labels_hz_s': [i/10 for i in range(-40,41)],
                       'widths_channels': [1,3,5,9,17,33,65,129],
                       'minimum_active_epoch_snr': 3, 'stack_statistic': 'sum',
                       'activity_subsets': [[0,1],[0,2],[1,2],[0,1,2]],
                       'hypotheses_per_cadence': 2592,
                       'on_scored_cells_per_cadence': 209952},
        'null_statistic': 'maximum over complete unchanged eligible ON family, else typed EMPTY',
        'score_shift_resampling': False,
        'rank_rule': {'reference_count': 127, 'keep_every_empty': True,
                      'inclusive_numerator': '1 + count(reference >= observed member)',
                      'denominator': 128, 'ceiling_numerator': 1, 'ceiling_denominator': 100,
                      'floor_snr': 10, 'higher_quantile_numerator': 1,
                      'higher_quantile_denominator': 1, 'ties_randomized': False},
        'runtime_intended': panel['runtime'], 'pins': pins,
        'proposed_limits_not_activated': limits, 'prior_actual_counters': prior,
        'cumulative_if_activated_and_fully_executed': cumulative,
        'new_budget_charged': False, 'new_values_generated': False,
        'old_attempt_or_identity_reuse_authorized': False,
        'integrated_runner_implemented': False, 'detector_certificate_issued': False,
        'source_codec_runtime_qualified': False, 'telescope_access_authorized': False,
        'activation_requirements': [
            'explicit new allocation replacing neither the old failure nor its counters',
            'distinct whole-cadence statistic/reference and downstream certificate adapter',
            'targeted interface, provenance, capacity and crash/consumption tests',
            'publish and independently read back an executable code/config/budget freeze',
        ],
    }
    OUT.mkdir(parents=True, exist_ok=False)
    write(OUT/'identity_collision_audit.json', {
        'schema': 'radio-proposed-control-identity-collision-audit-v1',
        'checkpoint': CHECKPOINT, 'config_files_inspected': len(paths),
        'additional_metadata_files_inspected': len(extras),
        'metadata_sha256s': file_hashes, 'all_string_and_integer_scalars_compared': True,
        'distinct_prior_metadata_scalars': len(prior_scalars), 'new_namespaces': len(names),
        'new_seeds': len(seeds), 'new_case_identities': len(cases),
        'collisions': collisions, 'old_score_or_holdout_payloads_read': False,
        'distinct_identity_does_not_prove_statistical_independence': True,
    })
    write(OUT/'proposed_reference_design.json', design)
    write(CONFIG, cfg)
    write(OUT/'result.json', {
        'schema': 'radio-whole-cadence-null-proposal-result-v1',
        'status': 'PROPOSAL_MATERIALIZED_NO_ALLOCATION',
        'config_path': str(CONFIG.relative_to(ROOT)),
        'config_sha256': hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        'proposed_independent_null_units': 127, 'proposed_fresh_evaluation_units': 24,
        'config_metadata_files_inspected': len(paths), 'identity_collisions': len(collisions),
        'new_values_generated': 0, 'new_attempt_allocations_charged': 0,
        'telescope_requests': 0, 'seed_uniqueness_is_not_independence_proof': True,
    })
    print(json.dumps(json.loads((OUT/'result.json').read_text()), indent=2))


if __name__ == '__main__':
    main()
