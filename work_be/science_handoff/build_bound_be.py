"""Bind BB87+BC1+BE8 inputs without releasing detector execution.

Default invocation validates arguments only through argparse. --check verifies all
binding prerequisites without writing. A separate binding-only GO is mandatory.
"""
from datetime import datetime, timezone
import argparse
import copy
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from common_be import Context, LINEAGE, sha, read, new, require

BASE = Path(__file__).resolve().parents[2]
WORK = BASE / 'work_be'
ENGINE = WORK / 'science_root'
B = ENGINE / 'work_az'
NATIVE_SCHEMA = 'SETI_BE_RECOVERY_NATIVE_INPUT_PROOF_V1'
PRODUCTION_SCOPE = 'COMPLETE_PRODUCTION_ACQUISITION_NATIVE_RECONSTRUCTION'


def validate_production_native(native):
    require(native.get('execution_mode') == 'PRODUCTION',
            'Binding requires a production native proof; simulation/unknown/missing mode rejected')
    require(native.get('proof_scope') == PRODUCTION_SCOPE,
            'Binding requires complete production acquisition/native reconstruction proof')
    return True


def verify_inputs(a):
    ctx = Context(a.evidence_root, a.relocations)
    paths = {name: ctx.resolve(getattr(a, name)) for name in ['manifest', 'prepower', 'recovery', 'native_actual', 'go']}
    mp, pp, rp, ap, gp = [paths[k] for k in ['manifest', 'prepower', 'recovery', 'native_actual', 'go']]
    pins = {}
    for path in paths.values():
        ctx.pin(path, pins)
    nativepath = ctx.resolve(B / 'review/INDEPENDENT_NATIVE_AZ.json')
    prep_path = ctx.resolve(WORK / 'SCIENCE_SOURCE_PREPARATION_BE.json')
    native, prep, go = read(nativepath), read(prep_path), read(gp)
    ctx.pin(nativepath, pins)
    ctx.pin(prep_path, pins)
    require(go.get('schema') == 'SETI_BE_BINDING_GO_V1', 'Wrong binding GO schema')
    require(go.get('authorized') is True and go.get('binding_only') is True, 'Explicit binding-only GO required')
    require(go.get('numerical_execution_authorized') is False, 'Binding cannot release numerical execution')
    ctx.pin_relocations(go, pins)
    expected = {'manifest_sha256': sha(mp), 'prepower_protocol_sha256': sha(pp),
                'recovery_protocol_sha256': sha(rp), 'native_review_sha256': sha(nativepath),
                'native_actual_sha256': sha(ap), 'binder_source_sha256': sha(__file__),
                'source_preparation_sha256': sha(prep_path), 'relocations_sha256': sha(a.relocations)}
    for key, digest in expected.items():
        require(go.get(key) == digest, 'Binding GO pin differs: ' + key)
    review_path = ctx.resolve(go['independent_review_path'])
    ctx.pin(review_path, pins, go['independent_review_sha256'])
    review = read(review_path)
    require(review.get('status') == 'PASS' and review.get('approved_for_binding_after_native_actual0') is True,
            'Independent binding review required')
    require(review.get('binder_source_sha256') == sha(__file__), 'Binding review source differs')
    validate_production_native(native)
    require(native.get('status') == 'PASS' and native.get('schema') == NATIVE_SCHEMA, 'BE native proof required')
    require(native.get('recovery_input_lineage') == LINEAGE, 'Native BB/BC/BE lineage differs')
    require(native.get('reconstructed_chunk_count') == 96 and native.get('reconstructed_scan_count') == 6,
            'Full native reconstruction missing')
    require(native.get('new_native_rows_verified') == 8 and native.get('inherited_rows') == 88,
            'Wrong prior/new native counts')
    require(native.get('new_repeat_receipts_checked') == 1 and native.get('inherited_repeat_receipts_checked') == 5
            and native.get('repeat_receipts_checked') == 6, 'Repeat lineage differs')
    require(native.get('all_exact_array_and_power_hashes_match') is True, 'Native byte equality missing')
    for key, path in [('manifest_sha256', mp), ('prepower_protocol_sha256', pp), ('recovery_protocol_sha256', rp)]:
        require(native.get(key) == sha(path), 'Native proof binding differs: ' + key)
    actual = ctx.actual(ap, 0, pins)
    require(actual.get('result_sha256') == sha(nativepath), 'Native actual does not bind exact result')
    ctx.pin('work_bb/review/PARTIAL_INPUT_PROOF_BB.json', pins, native['inherited_BB_partial_proof_sha256'])
    ctx.pin('work_bc/review/PARTIAL_INPUT_PROOF_BC.json', pins, native['inherited_BC_partial_proof_sha256'])
    for path, digest in native['input_and_source_sha256_before_after'].items():
        ctx.pin(path, pins, digest)
    require(prep.get('status') == 'PASS' and prep.get('numerical_sources_changed') is False,
            'Unchanged numerical source preparation required')
    pairs = prep.get('source_pairs', [])
    require(len(pairs) == len({x['original_path'] for x in pairs}) == len({x['copied_path'] for x in pairs}) == 33,
            'Expected 33 unique source/copy pairs')
    require(sum(Path(x['copied_path']).suffix == '.py' for x in pairs) == 25
            and sum(Path(x['copied_path']).suffix == '.json' for x in pairs) == 8,
            'Expected 25 Python and 8 JSON numerical sources')
    parent_prep_path = ctx.pin(prep['parent_preparation_path'], pins, prep['parent_preparation_sha256'])
    parent_pairs = {ctx.resolve(x['copied_path']): x['sha256'] for x in read(parent_prep_path)['source_pairs']}
    require(len(parent_pairs) == 33, 'Parent engine preparation inventory differs')
    for pair in prep['source_pairs']:
        require(pair.get('byte_identical') is True, 'Preparation has nonidentical source')
        old = ctx.resolve(pair['original_path'])
        copied = ctx.resolve(pair['copied_path'])
        require(old in parent_pairs and parent_pairs[old] == pair['sha256'], 'Source missing from original engine preparation')
        require(copied.relative_to(B) == old.relative_to(ctx.evidence / 'work_bc/science_root/work_az'),
                'Engine relative source topology differs')
        require(copied.is_relative_to(B), 'Copied engine path outside fresh BE root')
        ctx.pin(old, pins, pair['sha256'])
        ctx.pin(copied, pins, pair['sha256'])
    p, recovery, manifest = read(pp), read(rp), read(mp)
    require(p['target'] == recovery['target'] == manifest['target'] == 'HIP44295', 'Wrong target')
    require(p['primary_id'] == recovery['primary_id'] == manifest['primary_id'] == 65133, 'Wrong primary ID')
    require(recovery['original_BB_prepower_sha256'] == sha(pp), 'Original prepower binding differs')
    require(manifest['schema'] == 'HDF5_EXACT_RANGE_RECOVERY_SIX_SCAN_BE_V1', 'Wrong BE acquisition schema')
    require(manifest.get('execution_mode') == 'PRODUCTION',
            'Binding requires a production acquisition manifest; simulation/unknown/missing mode rejected')
    require(manifest['protocol_sha256'] == sha(rp), 'Recovery protocol differs')
    require(manifest['inherited_BB_native_rows'] == 87 and manifest['inherited_BC_native_rows'] == 1
            and manifest['inherited_native_rows'] == 88 and manifest['new_native_rows'] == 8
            and manifest['total_native_rows'] == 96, 'Acquisition lineage differs')
    require(manifest['scan5_prior_rows_reconstructed'] == 8 and manifest['scan5_new_rows_decoded'] == 8,
            'Scan5 lineage differs')
    require(p['configuration'].get('threshold_ess') == 10. and p['configuration'].get('off_flag_threshold_ess') == 5.,
            'Frozen numerical thresholds differ')
    for protocol in [p, recovery]:
        for path, digest in protocol['source_and_state_sha256'].items():
            ctx.pin(path, pins, digest)
    require(len(p['scans']) == len(manifest['scans']) == 6, 'Six scans required')
    for original, acquired in zip(p['scans'], manifest['scans']):
        require(original['scan'] == acquired['scan'] and original['archive_id'] == acquired['archive']['id']
                and original['role'] == acquired['role'], 'Acquired scan identity differs')
        ctx.pin(acquired['array_relative_path'], pins, acquired['array_sha256'])
    return ctx, paths, pins, nativepath, prep_path, actual, p, manifest


def main():
    parser = argparse.ArgumentParser()
    for name in ['manifest', 'prepower', 'recovery', 'native-actual', 'go', 'evidence-root', 'relocations']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check', action='store_true', help='Validate only; do not write binding outputs')
    a = parser.parse_args()
    ctx, paths, pins, nativepath, prep_path, actual, p, manifest = verify_inputs(a)
    if a.check:
        print('PASS_BE_BINDING_PREREQUISITES_NO_WRITES')
        return
    binding_path = B / 'review/NATIVE_ACTUAL_EXIT_AZ.json'
    bound_path = B / 'PROTOCOL_BOUND_AZ.json'
    require(not binding_path.exists() and not bound_path.exists(), 'No automatic binding restart')
    require(not (B / 'ROOT_DETECTOR_RELEASE_AZ.json').exists(), 'Detector release must be created separately after binding')
    for path, digest in pins.items():
        require(sha(path) == digest, 'Evidence changed before binding: ' + path)
    binding = dict(actual, schema='SETI_BE_NATIVE_PHASE_RESULT_BINDING_V1', result_sha256=sha(nativepath),
                   result_path=str(nativepath), original_actual_receipt_path=str(paths['native_actual']),
                   original_actual_receipt_sha256=sha(paths['native_actual']),
                   binding_go_path=str(paths['go']), binding_go_sha256=sha(paths['go']))
    original_config = copy.deepcopy(p['configuration'])
    require('scans' not in original_config, 'Unexpected prebound scan configuration')
    bound = copy.deepcopy(p)
    for scope, acquired in zip(bound['scans'], manifest['scans']):
        scope['native_path'] = str(ctx.resolve(acquired['array_relative_path']))
        scope['input_sha256'] = acquired['array_sha256']
    bound['configuration']['scans'] = copy.deepcopy(bound['scans'])
    source_map = dict(pins)
    # Engine consumers require their own relative identities as well as absolute pins.
    prep = read(prep_path)
    for pair in prep['source_pairs']:
        path = ctx.resolve(pair['copied_path'])
        source_map[str(path.relative_to(ENGINE))] = pair['sha256']
    source_map[str(Path(__file__).resolve())] = sha(__file__)
    source_map[str(Path(a.relocations).resolve())] = sha(a.relocations)
    bound.update(schema='SETI_BE_BOUND_UNCHANGED_FULLGRID_V1', root=str(ENGINE),
                 execution_mode='PRODUCTION', native_proof_scope=PRODUCTION_SCOPE,
                 bound_utc=datetime.now(timezone.utc).isoformat(),
                 prepower_protocol_sha256=sha(paths['prepower']), recovery_protocol_sha256=sha(paths['recovery']),
                 acquisition_manifest_sha256=sha(paths['manifest']), independent_native_review_sha256=sha(nativepath),
                 recovery_input_lineage=copy.deepcopy(LINEAGE), source_sha256=source_map,
                 scientific_execution_authorized_by_binding=False, binding_go_sha256=sha(paths['go']),
                 execution_disclosure='BB87+BC1 already decoded rows and8 BE rows. The original BB/BC failed actual1 records remain preserved. Six unchanged numerical scans need separate explicit execution authorization.')
    require({k: v for k, v in bound['configuration'].items() if k != 'scans'} == original_config,
            'Numerical configuration changed during binding')
    new(binding_path, binding)
    bound['source_sha256'][str(binding_path)] = sha(binding_path)
    new(bound_path, bound)
    print('BOUND_BE_INPUTS_UNCHANGED_NUMERICS_NO_DETECTOR_RELEASE ' + sha(bound_path))


if __name__ == '__main__':
    main()
