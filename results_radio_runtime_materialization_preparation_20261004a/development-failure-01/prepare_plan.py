#!/usr/bin/env python3
"""Pure, inert HD189733 runtime preparation. No acquisition or activation API.

build_plan accepts raw retained bytes and an independently supplied outer pin.
The CLI only reads the fixed local snapshots and writes one exclusive plan.
It never imports the retained source interfaces or HDF5/native packages.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat

NAMESPACE = 'radio-runtime-materialization-preparation-20261004a'
SOURCE_COMMIT = '3abe758efbe2c5bf3220f6843d5d5711aac8596b'
TRUSTED_PINMAP_SHA256 = 'c44a001916445f88d04dfd01f776a20ebd47b607b011b5c8e6e3ea84d2db5506'
SOURCE_INVENTORY = '3a925af307f8083647c39aad6393b08a1c05a296d056eea251dd6487ccf6530f'
NAMES = frozenset(('wheel_provenance', 'wheel_lock', 'numpy_metadata', 'h5py_metadata',
    'hdf5plugin_metadata', 'source_metadata', 'preserved_basis', 'trial_protocol',
    'candidate_certificate', 'scientific_runtime_interface', 'scientific_admission_interface',
    'receiver_adapter_interface', 'source_runtime_interface', 'current_availability'))
LABELS = tuple('epoch%d_%s' % (epoch, role) for epoch in (1, 2, 3) for role in ('on', 'off'))
ROLES = ('calibration', 'validation', 'pilot')
RUNTIME = {'python': '3.12.14', 'numpy': '2.3.5', 'h5py': '3.16.0',
           'hdf5': '2.0.0', 'hdf5plugin': '7.1.0'}
WHEELS = (
 {'name': 'numpy', 'version': '2.3.5', 'bytes': 16606086,
  'filename': 'numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
  'sha256': '0d8163f43acde9a73c2a33605353a4f1bc4798745a8b1d73183b28e5b435ae28',
  'url': 'https://files.pythonhosted.org/packages/b6/23/2a1b231b8ff672b4c450dac27164a8b2ca7d9b7144f9c02d2396518352eb/numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
  'tags': ['cp312-cp312-manylinux_2_27_x86_64', 'cp312-cp312-manylinux_2_28_x86_64']},
 {'name': 'h5py', 'version': '3.16.0', 'bytes': 5405250,
  'filename': 'h5py-3.16.0-cp312-cp312-manylinux_2_28_x86_64.whl',
  'sha256': 'dfc21898ff025f1e8e67e194965a95a8d4754f452f83454538f98f8a3fcb207e',
  'url': 'https://files.pythonhosted.org/packages/9e/e9/1a19e42cd43cc1365e127db6aae85e1c671da1d9a5d746f4d34a50edb577/h5py-3.16.0-cp312-cp312-manylinux_2_28_x86_64.whl',
  'tags': ['cp312-cp312-manylinux_2_28_x86_64']},
 {'name': 'hdf5plugin', 'version': '7.1.0', 'bytes': 46397731,
  'filename': 'hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
  'sha256': '9d4cf36434819fae53e4da432f0287ebaeb02386ab97b73d261092efbab12247',
  'url': 'https://files.pythonhosted.org/packages/26/56/3f788afb8d7fc451d20a66a64ea58bbe189f6f11780b28ba09148974fb33/hdf5plugin-7.1.0-py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl',
  'tags': ['py3-none-manylinux_2_27_x86_64', 'py3-none-manylinux_2_28_x86_64']})
FLAGS = ('download_authorized', 'installation_authorized', 'runtime_import_authorized',
    'metadata_capture_dispatch_authorized', 'execution_authorized', 'reservation_authorized',
    'acquisition_authorized', 'rng_authorized', 'scientific_execution_authorized',
    'spectral_access_authorized', 'source_contract_admitted', 'certificate_issued',
    'runtime_qualified', 'hosted_transport_qualified', 'cas_qualified', 'allocation_created')
MAX_INPUT = 512 * 1024
MAX_TOTAL = 2 * 1024 * 1024


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON member')
        result[key] = value
    return result


def parse(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT:
        raise ValueError('Bounded raw bytes required')
    try:
        value = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError('Invalid bounded JSON') from error
    return value


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_pinmap(raw, expected_sha256):
    need(expected_sha256 == TRUSTED_PINMAP_SHA256 and digest(raw) == expected_sha256,
         'Authoritative input-pin map or independent outer pin differs')
    value = parse(raw)
    need(set(value) == {'schema', 'source_commit', 'origin_authenticated_by', 'remote_origin_authenticated_here', 'inputs'}
         and value['schema'] == 'radio-runtime-materialization-authoritative-input-pins-v1'
         and value['source_commit'] == SOURCE_COMMIT and value['remote_origin_authenticated_here'] is False
         and set(value['inputs']) == NAMES, 'Exact retained input origin/membership required')
    return value


def authenticate(raw_inputs, pinmap):
    need(type(raw_inputs) is dict and set(raw_inputs) == NAMES, 'Complete fixed raw-input set required')
    total = 0
    for name, raw in raw_inputs.items():
        pin = pinmap['inputs'][name]
        need(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT and len(raw) == pin['bytes']
             and digest(raw) == pin['sha256'], 'Retained input differs: ' + name)
        total += len(raw)
        need(total <= MAX_TOTAL, 'Total preparation-input bound exceeded')
        if name != 'current_availability':
            need(pin['source_commit'] == SOURCE_COMMIT and
                 hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == pin['git_blob'],
                 'Intrinsic retained Git blob differs')


def wheel_plan(provenance, raw_inputs):
    rows = provenance['official_package_wheels']
    need(len(rows) == 3 and provenance['wheel_bytes'] == 68409067 and
         provenance['python_version'] == RUNTIME['python'] and
         provenance['scientific_execution_authorized'] is False and
         provenance['source_execution_authorized'] is False, 'Historical package scope differs')
    result = []
    for row, expected in zip(rows, WHEELS, strict=True):
        need(all(row[key] == expected[key] for key in ('name', 'version', 'bytes', 'filename', 'sha256', 'url'))
             and row['matching_tags'] == expected['tags'] and row['yanked'] is False,
             'Selected historical wheel identity or tags differ')
        metadata_raw = raw_inputs[row['name'] + '_metadata']
        need(row['metadata_pin'] == {'bytes': len(metadata_raw), 'sha256': digest(metadata_raw)},
             'Retained official metadata raw pin differs')
        metadata = parse(metadata_raw)
        need(metadata['info']['name'].lower() == expected['name'] and
             metadata['info']['version'] == expected['version'], 'Official package version differs')
        candidates = [entry for entry in metadata['urls'] if entry['filename'] == expected['filename']]
        need(len(candidates) == 1, 'Exactly one official selected wheel required')
        selected = candidates[0]
        need(selected['size'] == expected['bytes'] and selected['url'] == expected['url'] and
             selected['digests']['sha256'] == expected['sha256'] and selected['yanked'] is False,
             'Official selected wheel metadata differs')
        result.append(dict(expected, requires_python=metadata['info']['requires_python'],
            requires_dist=metadata['info']['requires_dist'], official_metadata_raw_sha256=digest(metadata_raw)))
    expected_lock = ''.join(row['name'] + '==' + row['version'] + ' --hash=sha256:' + row['sha256'] + '\n' for row in WHEELS)
    need(raw_inputs['wheel_lock'] == expected_lock.encode(), 'Exact offline hash lock differs')
    return result


def interface_binding(raw, required_names, name):
    try:
        tree = ast.parse(raw.decode())
    except (SyntaxError, UnicodeError) as error:
        raise ValueError('Invalid pinned interface source') from error
    defined = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
    need(set(required_names) <= defined, 'Required maintained interface missing: ' + name)
    return {'input_name': name, 'source_sha256': digest(raw),
            'required_symbols': list(required_names), 'executed_or_imported_here': False}


def build_plan(raw_inputs, authoritative_pinmap_raw, expected_pinmap_sha256):
    """Return an inert PENDING plan; caller-supplied bytes never grant authority."""
    pins = validate_pinmap(authoritative_pinmap_raw, expected_pinmap_sha256)
    authenticate(raw_inputs, pins)
    source = parse(raw_inputs['source_metadata'])
    basis_doc = parse(raw_inputs['preserved_basis'])
    basis = basis_doc['basis']
    protocol = parse(raw_inputs['trial_protocol'])
    candidate = parse(raw_inputs['candidate_certificate'])
    provenance = parse(raw_inputs['wheel_provenance'])
    availability = parse(raw_inputs['current_availability'])
    need(source['archive_target'] == 'HIP98505' and source['cadence_id'] == 85030 and
         source['stage'] == 'preparation-only-no-spectral-access' and source['windows'] == [] and
         source['hdf5_runtime'] is None and source['source_inventory_sha256'] == SOURCE_INVENTORY,
         'Unchanged blocked HD189733 source preparation required')
    scans = source['scans']
    need([scan['label'] for scan in scans] == list(LABELS) and
         [scan['role'] for scan in scans] == ['on', 'off'] * 3 and
         digest(canonical(scans)) == SOURCE_INVENTORY and
         basis['source_inventory_sha256'] == SOURCE_INVENTORY and
         basis['source_metadata_sha256'] == digest(raw_inputs['source_metadata']),
         'Exact six-scan/basis ancestry differs')
    for scan in scans:
        need(scan['expected_header']['dataset_shape'] == [16, 1, 264503296] and
             scan['expected_chunks'] == [1, 1, 1048576] and
             scan['expected_header']['dataset_dtype'] == 'float32' and
             scan['observed_hdf5_filters'] == [[32008, 1, [0, 3, 4, 0, 2]]],
             'Source HDF5 profile differs')
    need(basis_doc['evidence_domain'] == 'preserved-metadata-only' and
         protocol['evidence_domain'] == 'prospective-preparation-only' and
         protocol['status'] == 'PENDING_EXTERNAL_QUALIFICATION' and
         protocol['source_inventory_sha256'] == SOURCE_INVENTORY and
         protocol['search']['primary'] == 'neighbor9' and
         protocol['pilot']['source'] == 'HIP98505' and protocol['pilot']['cadence_id'] == 85030,
         'Preparation protocol scope or authority differs')
    need(candidate['authority'] == 'prospective-candidate-codec-proof-only' and
         all(value is False for value in candidate['authority_boundaries'].values()) and
         candidate['source_profile']['source_inventory_sha256'] == SOURCE_INVENTORY and
         candidate['runtime']['python'] == RUNTIME['python'] and
         candidate['runtime']['versions'] == {key: value for key, value in RUNTIME.items() if key != 'python'} and
         candidate['runtime']['fresh_live_runtime_reobservation_performed'] is False and
         candidate['coverage']['rows_1_through_14_exercised'] is False,
         'Candidate evidence scope/runtime/authority differs')
    need(availability['schema'] == 'radio-runtime-recorded-path-availability-observation-v1' and
         availability['candidate_root'] == provenance['candidate_root'] and
         availability['runtime_loaded'] is False and availability['scientific_authority'] is False and
         availability['whole_filesystem_absence_claim'] is False,
         'Exact-path availability observation differs')
    need([row['filename'] for row in availability['wheels']] == [row['filename'] for row in WHEELS] and
         all(type(row['is_file']) is bool for row in availability['wheels']) and
         type(availability['candidate_root_exists']) is bool,
         'Availability observations must be typed and exact')
    wheels = wheel_plan(provenance, raw_inputs)
    interfaces = [
        interface_binding(raw_inputs['scientific_runtime_interface'], ('ScientificFreeze', 'ProspectiveFreeze', 'validate_inventory', 'validate_edges'), 'scientific_runtime_interface'),
        interface_binding(raw_inputs['scientific_admission_interface'], ('validate_scientific_closure', 'VerifiedClosure'), 'scientific_admission_interface'),
        interface_binding(raw_inputs['receiver_adapter_interface'], ('from_telescope', 'validate_receiver_metadata', 'LoadedRows'), 'receiver_adapter_interface'),
        interface_binding(raw_inputs['source_runtime_interface'], ('runtime', 'load_contract'), 'source_runtime_interface')]
    gap_rows = [{'role': role, 'scan': scan, 'row_indices_required': list(range(16)),
        'receiver_context_sha256': basis['receiver_context_sha256s'][role],
        'receiver_bank_sha256': basis['receiver_bank_sha256s'][role],
        'raw_row_sha256s': None, 'normalized_row_sha256s': None,
        'authentic_receipts_supplied': False} for role in ('calibration', 'validation') for scan in LABELS]
    all_absent = (availability['candidate_root_exists'] is False and
                  all(row['is_file'] is False for row in availability['wheels']))
    plan = {
        'schema': 'radio-source-bound-runtime-materialization-plan-v1',
        'namespace': NAMESPACE, 'status': 'PENDING', 'evidence_domain': 'inert-metadata-preparation-only',
        'authoritative_input_pinmap_sha256': expected_pinmap_sha256,
        'input_provenance': {'retained_source_commit': SOURCE_COMMIT, 'origin': pins['origin_authenticated_by'],
            'immutable_public_readback_performed_here': False,
            'source_raw_pins': {name: {key: value for key, value in row.items() if key != 'snapshot_path'}
                                for name, row in pins['inputs'].items()}},
        'source': {'target': 'HD189733/HIP98505', 'cadence_id': 85030, 'primary': 'neighbor9',
            'source_inventory_sha256': SOURCE_INVENTORY, 'scans': list(LABELS),
            'frame': 'recorded-topocentric', 'observer_ephemeris_used': False,
            'source_profile': {'shape': [16, 1, 264503296], 'chunks': [1, 1, 1048576],
                'dtype': '<f4', 'legacy_filter_pipeline': [[32008, 1, [0, 3, 4, 0, 2]]],
                'current_encoder_pipeline_is_distinct': [[32008, 1, [0, 4, 4, 0, 2]]]},
            'windows': candidate['coverage']['windows'], 'window_identities': basis['window_identities'],
            'receiver_bank_sha256s': basis['receiver_bank_sha256s'],
            'search': protocol['search'], 'original_preparation_contract_unchanged': True},
        'materialization': {'required_historical_versions': RUNTIME, 'official_wheels': wheels,
            'wheel_file_bytes': sum(row['bytes'] for row in WHEELS),
            'offline_hash_lock_utf8': raw_inputs['wheel_lock'].decode(),
            'future_offline_install_required_flags': ['--no-index', '--no-deps', '--no-cache-dir', '--require-hashes', '--only-binary=:all:'],
            'platform_requirements': {'python_abi': 'cp312', 'machine': 'x86_64', 'endianness': 'little',
                'minimum_glibc_for_all_selected_wheels': '2.28'},
            'fresh_host_python_executable_sha256': None, 'fresh_host_image_identity': None,
            'historical_primary_python_executable_sha256': provenance['primary_python_sha256'],
            'historical_python_pin_cannot_authenticate_new_host': True,
            'required_site_isolation': 'owned new environment, no system site packages, fixed import paths and no inherited PYTHONPATH',
            'astropy_required_by_active_recorded_receiver_scope': False,
            'bootstrap_resources': {'status': 'UNALLOCATED_UNMEASURED',
                'wheel_bytes_only': 68409067, 'download_time': None, 'installed_bytes': None,
                'install_peak_rss_bytes': None, 'complete_dependency_bytes': None,
                'separate_finite_prospective_allocation_required_before_execution': True,
                'does_not_fit_or_borrow_scientific_40s_4MiB_or_80s_18MiB_budgets': True,
                'does_not_borrow_previous_engineering_reservations': True}},
        'availability': {'status': 'ABSENT_AT_RECORDED_EXACT_PATH_OBSERVATION' if all_absent else 'RECORDED_PATH_FACTS_ONLY',
            'observation': availability, 'current_live_runtime_verified': False,
            'observation_is_ephemeral_not_a_runtime_certificate': True,
            'historical_candidate_root_or_wheel_paths_are_not_recovery_authority': True},
        'existing_interfaces': interfaces,
        'existing_candidate_evidence': {'certificate_raw_sha256': digest(raw_inputs['candidate_certificate']),
            'authority': candidate['authority'], 'historical_matching_codec_binaries': 30,
            'candidate_native_byte_cohort_count': candidate['runtime']['native_byte_cohort_count'],
            'observed_row_role_pairs': candidate['coverage']['row_role_pairs'],
            'metadata_case_laws': candidate['coverage']['metadata_case_laws'],
            'normalization_receiver_qualified': False, 'rows_1_through_14_qualified': False,
            'fresh_host_runtime_qualified': False},
        'future_metadata_capture': {'implemented_here': False, 'dispatch_authorized': False,
            'new_complete_prospective_scope_required': True,
            'forbidden_operations': ['archive HEAD or range requests', 'opening archive HDF5 datasets',
                'spectral or holdout values', 'scientific RNG or case execution', 'CAS service probes',
                'source-session allocation', 'workflow activation', 'credential discovery'],
            'checklist': [
                'Authenticate published collector, exact package/provenance/source code pins and a separate finite bootstrap/capture allocation before dispatch.',
                'Observe actual hosted image/release/kernel/architecture/libc and Python version, executable bytes/hash and import path isolation; do not reuse the old interpreter hash.',
                'Authenticate every wheel byte/hash/tag before offline installation in the fresh isolated environment; preserve failures and installation overhead.',
                'Under an externally bounded child, import only the explicitly frozen source-runtime dependencies, recording exact NumPy/h5py/HDF5/hdf5plugin identities and filter registration; open no HDF5 dataset.',
                'Record before/after complete code/input/runtime/ELF/plugin inventories, exact DT_NEEDED and loader/RPATH resolution, loaded mappings and independently expected dependency edges.',
                'Retain full secret-free request/result/native/host/caller evidence and parent/descendant timing/RSS/storage/wait-chain limits from initialization through termination; samples alone do not certify a full peak.',
                'Publish and independently read back raw captured evidence; a report producer must not promote its own observed hashes or Boolean flags into qualified trust anchors.'],
            'capture_to_existing_freeze_interface': {'constructor': 'ScientificFreeze(raw, expected_raw_pin, expected_inventory, expected_dependency_edges, expected_runtime_identity)',
                'runtime_identity_keys': ['python', 'numpy', 'h5py', 'hdf5', 'hdf5plugin', 'python_executable_sha256'],
                'inventory_roles': ['code', 'input', 'runtime', 'elf', 'plugin'],
                'verify_required_inputs': ['read_file', 'published_commit', 'published_tree', 'read_published_file',
                    'expected_source_contract_sha256', 'expected_trial_protocol_sha256', 'expected_codec_certificate_sha256', 'runtime_identity'],
                'full_codec_certificate_schema': 'radio-source-specific-codec-runtime-case-law-certificate-v1',
                'full_closure_validator': 'validate_scientific_closure', 'replaces_existing_verifier': False}},
        'remaining_authentic_receipt_requirements': {'normalization_receiver_handoffs': gap_rows,
            'rehydration_and_detector_handoff_still_required': True,
            'hosted_transport_schema': 'radio-actual-hosted-native-transport-certificate-v1',
            'hosted_phase_profiles': [{'role': 'calibration', 'maximum_milliseconds': 40000, 'maximum_artifact_bytes': 4194304},
                {'role': 'evaluation', 'maximum_milliseconds': 80000, 'maximum_artifact_bytes': 18874368}],
            'actual_host_native_caller_receipts_supplied': False,
            'atomic_exact_precreated_candidate_expected_revision_cas_supplied': False,
            'scientific_127_24_outcomes_supplied': False, 'current_source_session_supplied': False,
            'source_session_maximum_milliseconds': 1200000, 'source_session_maximum_requests': 500,
            'source_session_maximum_bytes': 536870912,
            'current_session_required_bindings': ['source_contract_sha256', 'context_sha256', 'window_identity', 'role', 'row_receipt_pins',
                'irreversible_allocation', 'public_ledger_revision', 'current_session_identity', 'monotone_before_after_loader_clock'],
            'all_eleven_fields_still_pending': candidate['pending_scientific_fields']},
        'preserved_dispositions': {'HD1461': 'HOLD', 'GJ724': 'untouched reserve', 'native8': 'unreserved',
            'scientific_127_24': 'NOT ACTIVATED', 'spectra_and_original_112_128_holdouts': 'unopened',
            'CAS_closed_failed_attempt': 'preserve, no automatic successor', 'LS': 'paused, BF untouched', 'CHEOPS': 'UNSENT',
            'consolidation_date': '2026-10-09', 'automatic_extension': False},
        'operations_here': {'downloads': 0, 'installs': 0, 'hdf5_or_native_imports': 0, 'live_calls': 0,
            'telescope_or_holdout_reads': 0, 'scientific_rng_draws': 0, 'allocations': 0, 'workflow_activations': 0},
        'authority': {flag: False for flag in FLAGS}}
    need(len(plan['remaining_authentic_receipt_requirements']['all_eleven_fields_still_pending']) == 11,
         'All original eleven pending fields required')
    return plan


def safe_read(path):
    path = Path(path)
    need(path.is_absolute() and '..' not in path.parts, 'Absolute regular snapshot path required')
    for ancestor in (path, *path.parents):
        need(not ancestor.is_symlink(), 'Symlink snapshot path refused')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as source:
        before = os.fstat(source.fileno())
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= MAX_INPUT,
             'Bounded sole-link snapshot required')
        raw = source.read(MAX_INPUT + 1)
        after = os.fstat(source.fileno())
        fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        need(all(getattr(before, key) == getattr(after, key) for key in fields) and len(raw) == before.st_size,
             'Snapshot changed during read')
        return raw


def write_exclusive(path, raw):
    path = Path(path)
    need(path.is_absolute() and '..' not in path.parts, 'Absolute exclusive output required')
    for ancestor in (path, *path.parents):
        need(not ancestor.is_symlink(), 'Symlink output path refused')
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    need(safe_read(path) == raw, 'Exact persisted plan readback differs')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--pins', required=True)
    parser.add_argument('--pins-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    pins_raw = safe_read(args.pins)
    pins = validate_pinmap(pins_raw, args.pins_sha256)
    root = Path(args.inputs)
    raw_inputs = {name: safe_read(root / record['snapshot_path']) for name, record in pins['inputs'].items()}
    result = canonical(build_plan(raw_inputs, pins_raw, args.pins_sha256))
    write_exclusive(args.output, result)
    print(json.dumps({'status': 'PENDING', 'bytes': len(result), 'sha256': digest(result),
                      'scientific_execution_authorized': False}, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Preparation refused: ' + type(error).__name__, file=__import__('sys').stderr)
        raise SystemExit(1)
