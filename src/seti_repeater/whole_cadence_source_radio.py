"""Retained deterministic codec fixture to receiver-native receipts.

No network, RNG, Gaussian renderer or telescope constructor. Reusing the one
texture across scan slots is explicit and cannot certify independent draws.
"""
import hashlib
import json
from dataclasses import asdict

from . import transfer_m43g as native
from .empty_null_radio import canonical
from .pipeline_receiver_radio import NativeRun
from .whole_cadence_reference_radio import _sha, digest

ARCHIVE_SHA256 = '3b3bb2a475a01cd12e328349bcd05433efe8b549f1df66b2cc8cf51b951f41dd'
MEMBER_SHA256 = '614804452ed5be266072c9b9ca9564ee2af14f8992ca13cfec0a331dcad08fa4'


def texture_law():
    return {'schema': 'radio-retained-codec-texture-law-v1',
        'kind': 'deterministic-retained-codec-fixture',
        'archive_sha256': ARCHIVE_SHA256, 'member_sha256': MEMBER_SHA256,
        'random_draws': 0, 'independent_cadences': False,
        'scan_slots_reuse_identical_native_rows': True,
        'gaussian_noise_law': False, 'telescope_source': False}


def bind_codec_cadence(context, reader, *, case_identity, law,
                       input_receipt, expected_normalized_row_hashes):
    """Normalize one verified row set, bind six explicit engineering slots.

    The caller authenticates the file and decoded-row hashes before returning
    each row. These are reproducibility receipts, not authentication signatures.
    """
    context.validate(); _sha(case_identity, 'case')
    if law != texture_law():
        raise ValueError('Exact deterministic texture law required; no Gaussian claim')
    law_sha = digest(law)
    w = context.native_window
    expected_keys = {'archive_sha256', 'member_sha256', 'role', 'window_identity',
                     'archive_interval', 'decoded_row_sha256s', 'runtime_receipt_sha256'}
    if (set(input_receipt) != expected_keys or input_receipt['archive_sha256'] != ARCHIVE_SHA256
            or input_receipt['member_sha256'] != MEMBER_SHA256
            or input_receipt['role'] != 'validation' or w['role'] != 'validation'
            or input_receipt['window_identity'] != w['identity']
            or input_receipt['archive_interval'] != w['archive_interval']):
        raise ValueError('Codec receipt/window ancestry mismatch')
    for key in ('decoded_row_sha256s',):
        if len(input_receipt[key]) != 16:
            raise ValueError('Complete ordered 16-row receipt required')
        for value in input_receipt[key]: _sha(value, key)
    _sha(input_receipt['runtime_receipt_sha256'], 'runtime receipt')
    if len(expected_normalized_row_hashes) != 16:
        raise ValueError('Complete normalized-row receipt required')
    for value in expected_normalized_row_hashes: _sha(value, 'normalized row')

    def checked_reader(row):
        value = reader(row)
        if native.array_hash(value) != input_receipt['decoded_row_sha256s'][row]:
            raise ValueError('Decoded codec row differs from retained receipt')
        return value

    common = {'kind': 'synthetic', 'input_domain': 'retained-codec-engineering',
        'case_identity': case_identity, 'noise_law_sha256': law_sha,
        'noise_law': law, 'context_sha256': context.identity,
        'receiver_factor_bank_sha256': context.factor_contract.factors.identity,
        'input_receipt': input_receipt, 'input_receipt_sha256': digest(input_receipt),
        'independent_draws': False, 'telescope_provenance': False}
    first = native.normalize_synthetic_rows(checked_reader, context.geometry, 16,
        input_orientation='descending', scope={**common, 'scan': context.scans[0]['label']})
    if [native.array_hash(row) for row in first.values] != list(expected_normalized_row_hashes):
        raise ValueError('Normalized payload differs from retained codec evidence')
    sources = {}
    for scan in context.scans:
        scope = {**common, 'scan': scan['label']}
        identity = native.digest({'contract': native.CONTRACT_SHA256,
            'geometry': asdict(first.geometry), 'rows': 16, 'scope': scope,
            'raw_sha256': first.raw_sha256, 'normalized_sha256': first.normalized_sha256})
        source = native.SyntheticSource(first.geometry, 16, canonical(scope).decode(),
            first.raw_sha256, first.normalized_sha256, identity, first.values)
        native.validate_source(source); sources[scan['label']] = source
    run = NativeRun(context, sources)
    receipt = {'schema': 'radio-codec-receiver-handoff-v1',
        'case_identity': case_identity, 'noise_law': law, 'noise_law_sha256': law_sha,
        'input_receipt': input_receipt, 'input_receipt_sha256': digest(input_receipt),
        'context_sha256': context.identity, 'source_ids': run.source_ids,
        'unique_raw_payloads': 1, 'unique_normalized_payloads': 1,
        'explicit_scan_slots': 6, 'source_ids_distinct': len(set(run.source_ids.values())) == 6,
        'normalized_row_sha256s': list(expected_normalized_row_hashes),
        'independent_draws_established': False, 'gaussian_renderer_qualified': False,
        'telescope_provenance_established': False, 'scientific_allocation_charged': False}
    receipt['receipt_sha256'] = digest(receipt)
    return run, receipt


def validate_codec_binding(run, *, case_identity, noise_law_sha256):
    """Recheck source identities plus semantic law/ancestry, before reduction."""
    if not isinstance(run, NativeRun): raise ValueError('NativeRun required')
    run.context.validate()
    if noise_law_sha256 != digest(texture_law()): raise ValueError('Wrong codec law')
    _sha(case_identity, 'case')
    expected_labels = {s['label'] for s in run.context.scans}
    if set(run.sources) != expected_labels: raise ValueError('Missing codec scan')
    receipts = set(); raw = set(); normalized = set()
    for label, source in run.sources.items():
        native.validate_source(source); scope = json.loads(source.scope_json)
        if (scope.get('noise_law') != texture_law()
                or scope.get('noise_law_sha256') != noise_law_sha256
                or scope.get('case_identity') != case_identity
                or scope.get('scan') != label
                or scope.get('context_sha256') != run.context.identity
                or scope.get('receiver_factor_bank_sha256') != run.context.factor_contract.factors.identity
                or scope.get('input_domain') != 'retained-codec-engineering'
                or scope.get('input_receipt_sha256') != digest(scope.get('input_receipt'))
                or scope.get('independent_draws') is not False
                or scope.get('telescope_provenance') is not False
                or run.source_ids.get(label) != source.identity):
            raise ValueError('Codec case/law/source binding changed')
        receipts.add(scope['input_receipt_sha256']);raw.add(source.raw_sha256);normalized.add(source.normalized_sha256)
    if len(receipts) != 1 or len(raw) != 1 or len(normalized) != 1:
        raise ValueError('Expected explicitly shared deterministic codec payload')
