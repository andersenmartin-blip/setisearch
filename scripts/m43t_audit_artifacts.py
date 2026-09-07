"""Verify published-result denominators, seals and paired-input identities."""
import gzip
import hashlib
import json
from pathlib import Path
from m43b_active_support import seal
from m43e_economical_bank import read_sealed, write_sealed
from m43t_mask_comparison import frozen
from seti_repeater.mask_m43t import POLICIES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43t_mask_comparison'


def main():
    result = read_sealed(OUT / 'result.json')
    cfg = frozen(result['freeze_commit'])
    checked = []
    for path in sorted(OUT.glob('*.json')):
        if path.name == 'artifact_validation.json':
            continue
        read_sealed(path)
        checked.append(path.name)
    compressed = (OUT / 'paired_trial_audits.jsonl.gz').read_bytes()
    raw = gzip.decompress(compressed)
    assert hashlib.sha256(compressed).hexdigest() == result['trial_ledger_sha256']
    assert hashlib.sha256(raw).hexdigest() == result['trial_ledger_uncompressed_sha256']
    ledger = [json.loads(line) for line in raw.splitlines() if line.strip()]
    assert len(ledger) == 64
    outcomes = {}
    member_count = 0
    for record in ledger:
        assert record['result_sha256'] == seal({k: v for k, v in record.items() if k != 'result_sha256'})
        assert record['freeze_commit'] == result['freeze_commit']
        assert record['config_sha256'] == result['config_sha256']
        assert record['bindings'] == result['calibration_bindings']
        a, b = (record['audits'][policy] for policy in POLICIES)
        assert a['input_inventory_sha256'] == b['input_inventory_sha256']
        assert a['overlay'] == b['overlay']
        historical = read_sealed(ROOT / 'results_m43s_profile_sensitivity' /
            f'truth{record["truth"]["truth_index"]:02d}.strength{record["amplitude"]:03d}.json')['audit']
        assert a['input_inventory_sha256'] == historical['input_inventory_sha256']
        for audit in (a, b):
            member_count += len(audit['members'])
            assert audit['calibration_binding'] == result['calibration_bindings'][audit['mask_policy']]
        for e in record['endpoints']:
            key = e['mask_policy'], e['truth']['truth_index'], e['nominal_total_epoch_strength']
            assert key not in outcomes
            outcomes[key] = e
    assert len(result['endpoints']) == 160 and len(outcomes) == 128
    for e in result['endpoints']:
        key = e['mask_policy'], e['truth']['truth_index'], e['nominal_total_epoch_strength']
        if key[-1] != 0:
            assert outcomes[key] == e
        else:
            assert e['zero_level_reuses_one_m43t_arm_baseline'] is True
    for row in result['summary']:
        subset = [e for e in result['endpoints'] if e['mask_policy'] == row['mask_policy']
                  and e['truth']['profile'] == row['profile']
                  and e['nominal_total_epoch_strength'] == row['strength']]
        assert len(subset) == row['denominator'] == 8
        for key in ('retained', 'passes_physical_vetoes', 'recovered'):
            assert sum(e[key] for e in subset) == row[key]
    gains = [r for r in result['paired_changes'] if r['neighbor9_recovered'] and not r['legacy_recovered']]
    losses = [r for r in result['paired_changes'] if r['legacy_recovered'] and not r['neighbor9_recovered']]
    strongest = [outcomes['neighbor9', i, 32]['recovered'] for i in (1, 5, 9, 13)]
    reversals = []
    for policy in POLICIES:
        for truth in cfg['truths']:
            for lo, hi in zip(cfg['amplitudes'][1:-1], cfg['amplitudes'][2:]):
                if outcomes[policy, truth['truth_index'], lo]['recovered'] and not outcomes[policy, truth['truth_index'], hi]['recovered']:
                    reversals.append({'policy': policy, 'truth_index': truth['truth_index'], 'lower_strength': lo, 'higher_strength': hi})
    nulls = {}
    zero_mask_sha = hashlib.sha256(bytes(3 * 4097)).hexdigest()
    for policy in POLICIES:
        cal = read_sealed(OUT / f'{policy}.calibration.json')
        held = read_sealed(OUT / f'{policy}.heldout.json')
        assert len(cal['null_maxima']) == len(held['null_maxima']) == 128
        cut = result['heldout'][policy]['threshold']
        assert cut == max(10., max(cal['null_maxima']))
        assert sum(v >= cut for v in held['null_maxima']) == result['heldout'][policy]['at_or_above_threshold']
        baseline = read_sealed(OUT / f'{policy}.baseline.json')['audit']
        nulls[policy] = {'training_maximum': max(cal['null_maxima']),
                        'baseline_all_74_cropped_masks_zero': len(baseline['mask_sha256s']) == 74 and all(v == zero_mask_sha for v in baseline['mask_sha256s'].values())}
    restores = [read_sealed(OUT / f'restore.epoch{e}_{kind}.json') for e in (1, 2, 3) for kind in ('on', 'off')]
    assert all(r['complete'] and len(r['arrays']) == 16 and all(x['original_digest_exact'] for x in r['arrays']) for r in restores)
    gate = {'all_four_previous_strong_misses_recovered': all(strongest), 'no_paired_nonzero_recovery_losses': not losses,
            'no_additional_heldout_exceedances': result['heldout']['neighbor9']['at_or_above_threshold'] <= result['heldout']['legacy']['at_or_above_threshold']}
    audit = write_sealed(OUT / 'artifact_validation.json', {'complete': True,
        'result_sha256_verified': result['result_sha256'], 'frozen_dependencies_verified': len(cfg['pinned_sha256']),
        'sealed_json_files_verified': checked, 'sealed_trial_records_verified': 64,
        'paired_input_identities_exact': True, 'endpoint_count': 160, 'nonzero_member_decisions': member_count,
        'all_64_injected_score_inventories_match_m43s': True,
        'restored_source_receipts_exact': 6, 'restored_full_support_arrays_exact': 96,
        'paired_gains': gains, 'paired_losses': losses, 'adjacent_strength_reversals': reversals,
        'null_checks': nulls, 'development_gate_conditions': gate,
        'development_gate_passed': all(gate.values()), 'general_adoption_qualified': False})
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
