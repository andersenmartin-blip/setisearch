"""Create the final RESULTS admission from completed metadata only.

No imports of science code, arrays, archives, part payloads, HTTP or Library.
The immutable RESULTS builder separately authenticates empirical source/output
bytes and builds the archive only after its own root GO.
"""
import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import time

BASE = Path('analysis/s2017_next_native')
DELIVERY = BASE / 'delivery'
CONTROL = Path('analysis/s2017_next_native_execution')
SCOPE = DELIVERY / 'RESULTS_ADMISSION_PREPARATION_SCOPE_V2.json'
OUTPUT = DELIVERY / 'ACTUAL_RESULTS_COMPLETION_ADMISSION.json'
STAGE = DELIVERY / 'admission_prepare_v2'
SCRIPT = DELIVERY / 'prepare_results_admission_v2.py'
BUILDER = DELIVERY / 'build_results_package.py'
BUILDER_SHA = 'b371d6df3b1b692f456045d89a2076cdfdbf9ae5553bbdd1fea5c08a7b247dee'
ACQ = BASE / 'results/acquire/ACQUISITION_RESULT.json'
ACQ_SHA = '2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e'
SOURCE_QA = BASE / 'results/source_review/QA_RECEIPT.json'
SOURCE_QA_SHA = '21a8edaf91e9a60d3209d33e4620a5f93038aabfafd3910094bd25e0fd66318a'
SOURCE_SHA = '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
INTERIOR_QA = BASE / 'results/search/review/QA_RECEIPT.json'
BOUNDARY_QA = BASE / 'boundaries/results/review/QA_RECEIPT.json'
BOUNDARY_QA_SHA = '48153e180358319feb3906fc719eabc9f224200933aa69eccbe0e20cdb8f1b36'
JOBS = tuple('native%d_batch%02d' % (native, batch) for native in (170, 172) for batch in (1, 2, 3))
PAIRS = ('pair170_171', 'pair171_172')
TEXT = {'.py', '.json', '.md', '.txt', '.csv', '.log'}
CPU, WALL, RAM = 60, 300, 512 * 1024**2
MAX_FILE = 64 * 1024**2
OLD_PACKAGES = 'analysis/delivery/DATA_PACKAGES.json'
OLD_PACKAGES_PIN = {'bytes': 1570,
    'sha256': 'b93b5a67555109be86c9642dfefb5c55f3011862d4e5d8e355188e86b551c17f'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result


def confined(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts and '\\' not in str(name),
            'Root-relative POSIX metadata path required')
    result = root / p
    require(result.resolve().is_relative_to(root) and not result.is_symlink(),
            'Metadata path leaves root or is a symlink')
    return result


def metadata(root, name, pins, expected=None):
    path = confined(root, name)
    require(path.suffix in TEXT and 'raw_ranges' not in path.parts and path.name != 'DATA_PACKAGES.json',
            'Only bounded text/code metadata may be opened')
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_FILE, 'Bounded regular metadata file required')
    with path.open('rb') as handle:
        raw = handle.read(MAX_FILE + 1)
    require(len(raw) <= MAX_FILE, 'Metadata read exceeded declared maximum')
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'Metadata changed while read')
    raw.decode('utf8')
    require(b'\x00' not in raw, 'Plain UTF8 text required')
    observed = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    relative = Path(name).as_posix()
    require(relative not in pins or pins[relative] == observed, 'Metadata changed during admission')
    if expected is not None:
        require(observed == expected if isinstance(expected, dict) else observed['sha256'] == expected,
                'Pinned metadata identity differs: ' + relative)
    pins[relative] = observed
    return raw


def read_json(root, name, pins, expected=None):
    return json.loads(metadata(root, name, pins, expected), object_pairs_hook=unique_fields)


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                     allow_nan=False).encode('utf8')
    return hashlib.sha256(raw).hexdigest()


def validate_inventory(inventory):
    require(isinstance(inventory, dict) and bool(inventory), 'Nonempty declared byte inventory required')
    for name, expected in inventory.items():
        path = Path(name)
        require(isinstance(name, str) and bool(name) and name == path.as_posix()
                and not path.is_absolute() and '..' not in path.parts and '\\' not in name,
                'Canonical root-relative POSIX byte pin required')
        require(isinstance(expected, dict) and set(expected) == {'bytes', 'sha256'}
                and type(expected['bytes']) is int and expected['bytes'] >= 0
                and isinstance(expected['sha256'], str)
                and re.fullmatch('[0-9a-f]{64}', expected['sha256']), 'Declared byte-pin schema differs')


def declared_presence(root, name, expected, observed):
    """Validate known producer PNG/PDF metadata; never open its binary body."""
    validate_inventory({name: expected})
    path = confined(root, name)
    require(path.suffix in {'.png', '.pdf'}, 'Only known producer PNG/PDF may use stat-only presence admission')
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_size == expected['bytes'],
            'Declared regular producer image/reference presence/length differs')
    record = {'bytes': info.st_size, 'device': info.st_dev, 'inode': info.st_ino,
              'mtime_ns': info.st_mtime_ns, 'producer_declared_sha256': expected['sha256'],
              'body_opened_by_metadata_preparation': False}
    require(name not in observed or observed[name] == record, 'Declared producer binary metadata changed during admission')
    observed[name] = record


def reference_metadata(root, name, expected, reference_observed):
    """Authenticate only the old ledger, without admitting it to builder payload."""
    require(name == OLD_PACKAGES and expected == OLD_PACKAGES_PIN,
            'Only the exact prior1570-byte DATA_PACKAGES ledger may be reference-only text')
    path = confined(root, name)
    before = path.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_size == expected['bytes'],
            'Exact bounded prior-ledger length required before opening')
    with path.open('rb') as handle:
        opened = os.fstat(handle.fileno())
        require((opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) ==
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns),
                'Prior ledger identity changed before bounded opening')
        raw = handle.read(expected['bytes'] + 1)
        closed = os.fstat(handle.fileno())
    after = path.stat()
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
    require(len(raw) == expected['bytes'] and identity(before) == identity(closed) == identity(after),
            'Prior ledger length/EOF/identity changed during reference-only read')
    raw.decode('utf8')
    require(b'\x00' not in raw and hashlib.sha256(raw).hexdigest() == expected['sha256'],
            'Prior ledger is not exact pinned plain UTF8 text')
    require(name not in reference_observed or reference_observed[name] == expected,
            'Reference-only prior ledger changed during admission')
    reference_observed[name] = dict(expected)


def linked_review(root, contract, required_pins, pins, producer_binary_pins, presence,
                  reference_text_pins, reference_observed):
    review = read_json(root, contract['path'], pins)
    require(review['schema'] == contract['schema'] and review['status'] == contract['status'],
            'Required actual scientific/evidence review differs')
    declared = review['input_byte_pins']
    validate_inventory(declared)
    require(all(declared.get(name) == expected for name, expected in required_pins.items()),
            'Actual review does not bind all exact completed outputs/evidence')
    for name, expected in declared.items():
        if name in reference_text_pins:
            require(expected == reference_text_pins[name], 'Review prior-ledger reference differs')
            reference_metadata(root, name, expected, reference_observed)
        elif name in producer_binary_pins:
            require(expected == producer_binary_pins[name], 'Review known producer image/reference pin differs')
            declared_presence(root, name, expected, presence)
        elif Path(name).suffix in TEXT:
            metadata(root, name, pins, expected)
        else:
            require(False, 'Unknown binary review reference is forbidden: ' + name)
    return {'path': contract['path'], 'sha256': pins[contract['path']]['sha256'],
            'status': contract['status']}


def save_new(path, value):
    raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf8')
    with path.open('xb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def measured(started):
    return {'process_CPU_seconds_including_imports': time.process_time(),
            'wall_seconds_including_imports': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}


def main():
    started = time.monotonic()
    def deadline(signum, frame):
        raise TimeoutError('Metadata admission CPU/wall cap reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    resource.setrlimit(resource.RLIMIT_CPU, (CPU, CPU + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM, RAM))
    signal.alarm(WALL)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'expected-scope-sha256', 'expected-interior-qa-sha256', 'expected-static-review-sha256', 'freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-all8-and-both-actual-qa', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    require(args.root_go_after_all8_and_both_actual_qa, 'Explicit root GO after all8 COMPLETE and both actual QA required')
    require(re.fullmatch('[0-9a-f]{64}', args.expected_scope_sha256) and
            re.fullmatch('[0-9a-f]{64}', args.expected_interior_qa_sha256) and
            re.fullmatch('[0-9a-f]{64}', args.expected_static_review_sha256) and
            re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Actual scope/QA SHA and public freeze arguments required')
    pins, presence, reference_observed, handles, created = {}, {}, {}, [], False
    try:
        require(Path(__file__).resolve() == root / SCRIPT, 'Exact admission script path required')
        scope = read_json(root, SCOPE, pins, args.expected_scope_sha256)
        require(scope['schema'] == 'SETI_ADJACENT_RESULTS_METADATA_ADMISSION_PREPARATION_V2'
                and scope['output_path'] == OUTPUT.as_posix()
                and scope['script_path'] == SCRIPT.as_posix()
                and scope['CPU_cap_s'] == CPU and scope['wall_cap_s'] == WALL
                and scope['memory_cap_bytes'] == RAM and scope['engineering_output_stage'] == STAGE.as_posix()
                and scope['reference_only_metadata_pins'] == {OLD_PACKAGES: OLD_PACKAGES_PIN},
                'Frozen V2 metadata admission scope differs')
        metadata(root, SCRIPT, pins, scope['script_sha256'])
        review = read_json(root, scope['static_review_path'], pins, args.expected_static_review_sha256)
        require(review['status'] == 'PASS_INDEPENDENT_STATIC_METADATA_ONLY_RESULTS_ADMISSION'
                and review['script_sha256'] == scope['script_sha256']
                and review['scope_sha256'] == args.expected_scope_sha256,
                'Independent static review must bind exact assembler and scope')
        for name, expected in scope['fixed_text_input_pins'].items():
            metadata(root, name, pins, expected)
        builder_raw = metadata(root, BUILDER, pins, BUILDER_SHA)
        literals = {}
        for node in ast.parse(builder_raw).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ('QA_COUNTS', 'QA_CONTRACTS', 'SOURCE_QA_COUNTS'):
                        literals[target.id] = ast.literal_eval(node.value)
        require(set(literals) == {'QA_COUNTS', 'QA_CONTRACTS', 'SOURCE_QA_COUNTS'}, 'Immutable builder QA literals missing')
        for path in (BASE / 'ACTIVE_FAMILY_FLOCK.lock', DELIVERY / 'ARCHIVE_ACTIVE_FLOCK.lock'):
            handle = (root / path).open('a+b')
            handles.append(handle)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (root / OUTPUT).exists(), 'Final admission already exists; no overwrite')
        (root / STAGE).mkdir(parents=True, exist_ok=False)
        created = True
        acq = read_json(root, ACQ, pins, ACQ_SHA)
        sq = read_json(root, SOURCE_QA, pins, SOURCE_QA_SHA)
        require(acq['status'] == 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
                and acq['source_manifest_sha256'] == SOURCE_SHA and acq['new_telescope_HTTP_requests'] == 192
                and acq['new_telescope_BODY_bytes'] == 597792529
                and sq['acquisition_receipt_sha256'] == ACQ_SHA and sq['source_manifest_sha256'] == SOURCE_SHA,
                'Actual acquisition/source QA identity differs')
        require(sq['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
                and sq['status'] == 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
                and sq['counts'] == literals['SOURCE_QA_COUNTS']
                and sq['scope_sha256'] == acq['scope_sha256']
                and sq['driver_sha256'] == acq['driver_sha256']
                and sq['public_freeze_commit'] == acq['public_freeze_commit']
                and sq['new_telescope_HTTP_requests'] == sq['new_telescope_BODY_bytes'] == 0
                and sq['detector_or_score_rerun'] is False and sq['medians_recomputed'] is False,
                'Actual source QA full metadata provenance differs')
        metadata(root, BASE / 'qa_sources.py', pins, sq['qa_script_sha256'])
        for qa_field, acq_field in (('source_range_raw_record_sha256', 'raw_range_records'),
                ('decoded_file_row_record_sha256', 'decoded_files'),
                ('source_range_request_record_sha256', 'value_read_requests')):
            require(sq[qa_field] == canonical_sha(acq[acq_field]), 'Source QA canonical record pin differs')
        compact_pins = {(BASE / 'results/acquire' / item['array_file']).as_posix():
                        {'bytes': item['bytes'], 'sha256': item['file_sha256']} for item in acq['decoded_files']}
        validate_inventory(compact_pins)
        require(len(compact_pins) == 12 and sq['compact_input_byte_pins'] == compact_pins,
                'Source QA exact12 compact inventory differs')
        raw_path = DELIVERY / 'RAW_PACKAGE_RECEIPT.json'
        retention_path = DELIVERY / 'ROOT_RAW_RETENTION_RECEIPT.json'
        raw = read_json(root, raw_path, pins)
        retention = read_json(root, retention_path, pins)
        durability = read_json(root, DELIVERY / 'RAW_PARTS_DURABILITY_RECEIPT.json', pins)
        plan = read_json(root, DELIVERY / 'RAW_ARCHIVE_PARTS_PLAN.json', pins)
        assembly = read_json(root, DELIVERY / 'RAW_PARTS_LOCAL_RESTORATION_AND_ASSEMBLY_RECEIPT.json', pins)
        require(raw['status'] == 'PASS_ARCHIVE_CRC_AND_ALL_MEMBER_SHA256' and raw['kind'] == 'RAW'
                and raw['archive_bytes'] == 604399781 and raw['archive_sha256'] == plan['original_archive_sha256']
                and retention['status'] == 'COMPLETE_ROOT_ONLY192_REDUNDANT_SIDECARS_REMOVED_AFTER_DURABLE_RAW_SAVE'
                and retention['sidecars_removed'] == retention['compressed_H5_chunks_verified'] == 192
                and retention['durable_RAW_save_confirmed'] is True and retention['raw_archive_sha256'] == raw['archive_sha256']
                and retention['durable_RAW_parts_receipt_sha256'] == pins[(DELIVERY / 'RAW_PARTS_DURABILITY_RECEIPT.json').as_posix()]['sha256'],
                'Actual RAW durability/retention receipt required')
        require(durability['status'] == 'COMPLETE_ALL_ORIGINAL_RAW_ARCHIVE_BYTES_DURABLY_SAVED_IN_THREE_ORDERED_PARTS'
                and durability['all_per_item_save_statuses_succeeded'] is True
                and durability['whole_archive_byte_exact_recoverability_confirmed'] is True
                and durability['single_file_save_claimed'] is False
                and durability['plan_sha256'] == pins[(DELIVERY / 'RAW_ARCHIVE_PARTS_PLAN.json').as_posix()]['sha256']
                and assembly['archive_sha256'] == raw['archive_sha256'] and assembly['archive_bytes'] == raw['archive_bytes'],
                'Three actual durable parts and local ordered byte proof required')
        require(len(durability['parts']) == len(plan['parts']) == 3 and all(
            {key: got[key] for key in want} == want and got['confirmed_save_status'] == 'succeeded'
            for want, got in zip(plan['parts'], durability['parts'])), 'Actual saved parts differ from immutable plan')
        safe, boundaries, values = [], [], {}
        total_maps = total_profiles = total_combinations = 0
        for kind, names in (('interior', JOBS), ('boundary', PAIRS)):
            for name in names:
                prefix = BASE / ('results/search' if kind == 'interior' else 'boundaries/results') / name
                receipt_path = prefix / ('EXECUTION_RECEIPT.json' if kind == 'interior' else 'measurement/EXECUTION_RECEIPT.json')
                receipt = read_json(root, receipt_path, pins)
                status = ('COMPLETE_S2017_ADJACENT_NATIVE_SAFE_INTERIOR_JOB_EXPLORATORY_ONLY' if kind == 'interior'
                          else 'COMPLETE_S2017_TWO_NEW_JOINED_CORES_SIX_ON_MAPS_NINE_FIXED_PROFILES_EXPLORATORY_ONLY')
                maps = (252 if name.endswith('batch03') else 255) if kind == 'interior' else 6
                require(receipt['status'] == status and receipt['job_id' if kind == 'interior' else 'pair_id'] == name
                        and receipt['search_summary']['completed_ON_maps'] == maps
                        and receipt['fixed_profile_summary']['profile_count'] == 9
                        and receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == 0,
                        'Every final actual job must be COMPLETE with exact count and zero new HTTP')
                require(receipt['acquisition_receipt_sha256' if kind == 'interior' else 'new_acquisition_receipt_sha256'] == ACQ_SHA
                        and receipt['source_QA_receipt_sha256' if kind == 'interior' else 'new_source_QA_receipt_sha256'] == SOURCE_QA_SHA,
                        'Actual job source prerequisite pins differ')
                scope_path = BASE / ('search' if kind == 'interior' else 'boundaries') / 'scopes' / (name + '.json')
                job_scope = read_json(root, scope_path, pins, receipt['scope_sha256'])
                metadata(root, BASE / ('search' if kind == 'interior' else 'boundaries') / 'driver.py', pins, receipt['driver_sha256'])
                require(job_scope['driver_sha256'] == receipt['driver_sha256'], 'Job scope/scientific driver identity differs')
                values[name] = receipt
                record = {'path': receipt_path.as_posix(), 'sha256': pins[receipt_path.as_posix()]['sha256']}
                (safe if kind == 'interior' else boundaries).append(record)
                total_maps += maps
                total_profiles += 9
                total_combinations += receipt['search_summary']['correlated_drift_width_combinations']
        require((total_maps, total_profiles, total_combinations) == (1536, 72, 9877585920), 'Actual eight-family aggregate differs')
        execution_review = read_json(root, scope['actual_search_admission_review_path'], pins)
        require(execution_review['schema'] == 'SETI_S2017_ADJACENT_EIGHT_ACTUAL_SEARCH_ADMISSION_REVIEW_V1'
                and execution_review['status'] == 'PASS_EIGHT_ACTUAL_COMPLETE_JOBS_METADATA_AND_ALL_OUTPUT_BYTE_IDENTITIES'
                and execution_review['acquisition_receipt_sha256'] == ACQ_SHA
                and execution_review['source_QA_receipt_sha256'] == SOURCE_QA_SHA
                and execution_review['counts']['search_jobs'] == 8
                and execution_review['counts']['maps'] == total_maps
                and execution_review['counts']['fixed_profiles'] == total_profiles
                and set(execution_review['jobs']) == set(JOBS + PAIRS), 'Actual eight-job output identity admission differs')
        for name, record in zip(JOBS + PAIRS, safe + boundaries):
            require(execution_review['jobs'][name]['execution_receipt_sha256'] == record['sha256']
                    and execution_review['jobs'][name]['scope_sha256'] == values[name]['scope_sha256'],
                    'Actual eight-job admission does not bind current receipt/scope')
        qa_records, qa_values, external = [], {}, {}
        for kind, path, expected_sha in (('interior', INTERIOR_QA, args.expected_interior_qa_sha256),
                                        ('boundary', BOUNDARY_QA, BOUNDARY_QA_SHA)):
            qa = read_json(root, path, pins, expected_sha)
            expected_path, schema, status = literals['QA_CONTRACTS'][kind]
            require(path.as_posix() == expected_path and qa['schema'] == schema and qa['status'] == status
                    and qa['counts'] == literals['QA_COUNTS'][kind]
                    and qa['detector_or_score_rerun'] is False and qa['fixed_track_optimization_applied'] is False
                    and qa['new_telescope_HTTP_requests'] == qa['new_telescope_BODY_bytes'] == 0,
                    'Exact actual saved-output/source QA PASS required')
            names, receipts = (JOBS, safe) if kind == 'interior' else (PAIRS, boundaries)
            receipt_key = 'search_receipt_SHA256s' if kind == 'interior' else 'pair_execution_receipt_SHA256s'
            require(qa[receipt_key] == {name: rec['sha256'] for name, rec in zip(names, receipts)}
                    and qa['scope_SHA256s'] == {name: values[name]['scope_sha256'] for name in names},
                    'Actual QA receipt/scope dictionaries do not cover current completed jobs')
            freeze_key = 'public_freeze_commit' if kind == 'interior' else 'search_public_freeze_commit'
            require(all(values[name]['driver_sha256'] == qa['driver_sha256']
                        and values[name]['public_freeze_commit'] == qa[freeze_key] for name in names),
                    'Actual QA searched driver/public freeze differs')
            require(isinstance(qa['qa_public_freeze_commit'], str)
                    and re.fullmatch('[0-9a-f]{40}', qa['qa_public_freeze_commit']),
                    'Actual QA public40-hex freeze identity missing')
            code_path = BASE / ('search' if kind == 'interior' else 'boundaries') / 'qa_saved_outputs.py'
            metadata(root, code_path, pins, qa['qa_script_sha256'])
            if kind == 'interior':
                require(qa['prerequisites']['acquisition']['path'] == ACQ.as_posix()
                        and qa['prerequisites']['acquisition']['sha256'] == ACQ_SHA
                        and qa['prerequisites']['source_QA']['path'] == SOURCE_QA.as_posix()
                        and qa['prerequisites']['source_QA']['sha256'] == SOURCE_QA_SHA, 'Interior actual QA source gate differs')
            else:
                require(qa['new_acquisition_receipt_sha256'] == ACQ_SHA
                        and qa['new_source_QA_receipt_sha256'] == SOURCE_QA_SHA
                        and all(values[name]['prior171_source_QA_receipt_sha256'] == qa['prior171_source_QA_receipt_sha256']
                                for name in names), 'Boundary actual QA source gate differs')
            validate_inventory(qa['all_input_byte_pins'])
            for name, rec in zip(names, receipts):
                declared_scope = (BASE / ('search' if kind == 'interior' else 'boundaries') / 'scopes' / (name + '.json')).as_posix()
                require(qa['all_input_byte_pins'][rec['path']]['sha256'] == rec['sha256']
                        and qa['all_input_byte_pins'][declared_scope]['sha256'] == values[name]['scope_sha256'],
                        'Actual QA byte inventory omits execution/scope identity')
            declared_driver = (BASE / ('search' if kind == 'interior' else 'boundaries') / 'driver.py').as_posix()
            require(qa['all_input_byte_pins'][declared_driver]['sha256'] == qa['driver_sha256']
                    and qa['all_input_byte_pins'][ACQ.as_posix()]['sha256'] == ACQ_SHA
                    and qa['all_input_byte_pins'][SOURCE_QA.as_posix()]['sha256'] == SOURCE_QA_SHA,
                    'Actual QA byte inventory omits driver/acquisition/source-QA identity')
            for name, expected in qa['all_input_byte_pins'].items():
                # Never open binary source/array inputs during metadata assembly.
                # The unchanged builder will authenticate all of these later.
                if Path(name).suffix not in TEXT:
                    continue
                metadata(root, name, pins, expected)
                if not Path(name).is_relative_to(BASE):
                    external[name] = expected
            qa_records.append({'kind': kind, 'path': path.as_posix(), 'sha256': expected_sha, 'expected_status': status})
            qa_values[kind] = qa
        interpretations, producer_png_pins, producer_binary_pins, excluded_pdf_pins, science_reviews = [], {}, {}, {}, []
        require([x['kind'] for x in scope['interpretation_families']] == ['interior', 'boundary'],
                'Exactly both completed interpretation families required')
        for contract in scope['interpretation_families']:
            kind = contract['kind']
            path = Path(contract['receipt_path'])
            receipt = read_json(root, path, pins)
            require(receipt['status'] == 'COMPLETE_DESCRIPTIVE_ONLY_QUALIFIED_CLAIM_FALSE'
                    and receipt['qualified_claim'] is False and receipt['detector_or_score_rerun'] is False
                    and all(receipt[field] is False for field in contract['false_fields'])
                    and receipt['counts'] == contract['counts']
                    and receipt[contract['actual_QA_sha256_field']] == qa_records[0 if kind == 'interior' else 1]['sha256'],
                    'Required actual saved-only interpretation differs')
            if contract['receipt_schema'] is not None:
                require(receipt['schema'] == contract['receipt_schema'], 'Interpretation receipt schema differs')
            if kind == 'interior':
                require(receipt['source_QA_sha256'] == SOURCE_QA_SHA
                        and receipt['acquisition_receipt_sha256'] == ACQ_SHA
                        and receipt['search_public_freeze_commit'] == qa_values[kind]['public_freeze_commit']
                        and receipt['QA_public_freeze_commit'] == qa_values[kind]['qa_public_freeze_commit'],
                        'Interior interpretation acquisition/source/search/QA freeze differs')
            else:
                require(receipt['source_QA_sha256'] == SOURCE_QA_SHA, 'Boundary interpretation source-QA differs')
            validate_inventory(receipt['input_pins'])
            validate_inventory(receipt['output_pins'])
            qa_path = (INTERIOR_QA if kind == 'interior' else BOUNDARY_QA).as_posix()
            require(receipt['input_pins'].get(qa_path) == pins[qa_path]
                    and receipt['input_pins'].get(SOURCE_QA.as_posix()) == pins[SOURCE_QA.as_posix()],
                    'Interpretation must bind actual source and saved-output QA')
            metadata(root, contract['script_path'], pins, receipt['interpretation_script_sha256'])
            outputs = set(contract['required_text_outputs']) | set(contract['required_png_outputs'])
            require(outputs.issubset(receipt['output_pins']), 'Declared interpretation outputs missing')
            linked = {path.as_posix(): pins[path.as_posix()], qa_path: pins[qa_path]}
            for name in contract['required_text_outputs']:
                require(Path(name).name == name and Path(name).suffix in TEXT, 'Only declared local text outputs required')
                full = (path.parent / name).as_posix()
                metadata(root, full, pins, receipt['output_pins'][name])
                linked[full] = pins[full]
                external[full] = pins[full]
            report = read_json(root, path.parent / contract['summary_json_name'], pins)
            require(report['schema'] == contract['summary_schema']
                    and report['status'] == receipt['status'] and report['qualified_claim'] is False,
                    'Actual interpretation summary contract differs')
            for name in contract['required_png_outputs']:
                require(Path(name).name == name and Path(name).suffix == '.png', 'Only declared local PNG outputs required')
                full = (path.parent / name).as_posix()
                declared_presence(root, full, receipt['output_pins'][name], presence)
                producer_png_pins[full] = receipt['output_pins'][name]
                producer_binary_pins[full] = receipt['output_pins'][name]
                linked[full] = receipt['output_pins'][name]
            for name in contract['reference_only_excluded_binary_outputs']:
                require(Path(name).name == name and Path(name).suffix == '.pdf',
                        'Only the two known boundary producer PDF references may be excluded')
                full = (path.parent / name).as_posix()
                require(full in scope['reference_only_excluded_producer_binary_paths'],
                        'Unknown excluded producer binary reference')
                declared_presence(root, full, receipt['output_pins'][name], presence)
                producer_binary_pins[full] = receipt['output_pins'][name]
                excluded_pdf_pins[full] = receipt['output_pins'][name]
            for name, expected in receipt['input_pins'].items():
                if Path(name).suffix in TEXT:
                    metadata(root, name, pins, expected)
            external[path.as_posix()] = pins[path.as_posix()]
            interpretations.append({'kind': kind, 'path': path.as_posix(), 'sha256': pins[path.as_posix()]['sha256']})
            science_reviews.append(linked_review(root, contract['independent_review'], linked, pins,
                producer_binary_pins, presence, scope['reference_only_metadata_pins'], reference_observed))
        require(set(scope['required_final_presence_paths']) == set(producer_png_pins),
                'Frozen final PNG presence inventory must equal both producer outputs')
        require(set(scope['reference_only_excluded_producer_binary_paths']) == set(excluded_pdf_pins),
                'Frozen excluded PDF-reference inventory must equal the two known producer outputs')
        final_text = {}
        for name in scope['final_report_paths']:
            metadata(root, name, pins)
            final_text[name] = pins[name]
            external[name] = pins[name]
        evidence_contract = scope['final_evidence_review']
        evidence = linked_review(root, evidence_contract, {**final_text,
            **{x['path']: pins[x['path']] for x in interpretations + qa_records + science_reviews}}, pins,
            producer_binary_pins, presence, scope['reference_only_metadata_pins'], reference_observed)
        final_synthesis = linked_review(root, scope['final_synthesis_review'], {**final_text,
            evidence['path']: pins[evidence['path']],
            **{x['path']: pins[x['path']] for x in interpretations + qa_records + science_reviews}}, pins,
            producer_binary_pins, presence, scope['reference_only_metadata_pins'], reference_observed)
        # Explicitly preserve original171/runtime, engineering/restore records,
        # own scope/code and every sibling execution control text/log.
        for name in scope['required_external_text_paths']:
            metadata(root, name, pins)
            external[name] = pins[name]
        require((root / CONTROL).is_dir(), 'Sibling execution-control namespace required')
        for path in (root / CONTROL).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.lock':
                continue
            require(path.suffix in TEXT, 'Unexpected sibling execution-control payload type')
            name = path.relative_to(root).as_posix()
            metadata(root, name, pins)
            external[name] = pins[name]
        for number, wave in enumerate(('actual_wave1', 'actual_wave2', 'actual_wave3'), 1):
            control = read_json(root, CONTROL / wave / 'ORCHESTRATION_RECEIPT.json', pins)
            require(control['schema'] == 'SETI_S2017_ADJACENT_TWO_JOB_ONE_SHOT_WAVE_CONTROL_V1'
                    and control['status'] == 'COMPLETE_TWO_ROOT_AUTHORIZED_JOBS_ONCE_NO_RETRY'
                    and control['wave'] == number and control['HTTP_requests'] == 0
                    and control['retry_resume_rerun_authorized'] is False
                    and [x['job_id'] for x in control['jobs']] == ['native170_batch%02d' % number, 'native172_batch%02d' % number],
                    'Every exact owned wave must be actually complete without retries')
            for record in control['jobs']:
                expected_path = BASE / 'results/search' / record['job_id'] / 'EXECUTION_RECEIPT.json'
                require(record['exit_code'] == 0 and record['status'] == values[record['job_id']]['status']
                        and record['actual_receipt_path'] == expected_path.as_posix()
                        and record['actual_receipt_sha256'] == pins[expected_path.as_posix()]['sha256']
                        and record['scope_sha256'] == values[record['job_id']]['scope_sha256'],
                        'Wave control must bind current exact completed receipt/scope')
                metadata(root, record['log_path'], pins, record['log_sha256'])
        code_pins = {name: pins[name] for name in scope['exact_builder_code_paths']}
        require(set(code_pins) == {(DELIVERY / name).as_posix() for name in (
            'build_results_package.py', 'archive_common.py', 'reconstruct_raw_sidecars.py')}, 'Exactly three immutable RESULTS builder code pins required')
        admission = {'schema': 'SETI_ADJACENT170_172_RESULTS_ACTUAL_COMPLETION_ADMISSION_V1',
            'acquisition_receipt_sha256': ACQ_SHA, 'source_QA_receipt_sha256': SOURCE_QA_SHA,
            'source_manifest_sha256': SOURCE_SHA, 'code_pins': code_pins, 'safe_receipts': safe,
            'boundary_receipts': boundaries, 'actual_QA_receipts': qa_records,
            'raw_package_receipt': {'path': raw_path.as_posix(), 'sha256': pins[raw_path.as_posix()]['sha256']},
            'root_retention_receipt': {'path': retention_path.as_posix(), 'sha256': pins[retention_path.as_posix()]['sha256']},
            'external_reference_file_pins': external,
            'archive_filename': 'SETI_S2017_ADJACENT170_172_RESULTS_2026-10-10.zip',
            'metadata_preparation_script_sha256': pins[SCRIPT.as_posix()]['sha256'],
            'metadata_preparation_scope_sha256': args.expected_scope_sha256,
            'metadata_preparation_static_review_sha256': args.expected_static_review_sha256,
            'metadata_preparation_public_freeze_commit': args.freeze_commit,
            'engineering_repair_history': {'path': scope['engineering_repair_history_path'],
                'sha256': pins[scope['engineering_repair_history_path']]['sha256']},
            'metadata_preparation_attempt': 'V2 separate one-shot engineering stage after preserved V1 reference-only guard failure',
            'scientific_search_or_QA_rerun_in_this_repair': False,
            'actual_new_counts': {'maps': total_maps, 'fixed_profiles': total_profiles,
                'raw_patch_cell_occurrences': 891648, 'correlated_drift_width_combinations': total_combinations},
            'actual_saved_interpretation_receipts': interpretations,
            'actual_independent_scientific_reviews': science_reviews,
            'final_report_evidence_review': evidence, 'final_scientific_synthesis_review': final_synthesis,
            'producer_declared_interpretation_PNG_pins': producer_png_pins,
            'reference_only_excluded_producer_PDF_pins': excluded_pdf_pins,
            'reference_only_authenticated_prior_metadata_pins': reference_observed,
            'reference_only_inputs_admitted_to_builder_external_or_payload_pins': False,
            'interpretation_PNG_admission': 'regular-file presence, size and stable metadata only; archive verification must compare member SHA against producer pins',
            'RAW_durable_representation': 'three ordered exact byte parts, not a single saved ZIP',
            'source_arrays_archives_part_bodies_or_sidecars_opened_by_preparation': False}
        for name, expected in list(pins.items()):
            metadata(root, name, pins, expected)
        for name, expected in producer_binary_pins.items():
            declared_presence(root, name, expected, presence)
        for name, expected in list(reference_observed.items()):
            reference_metadata(root, name, expected, reference_observed)
        use = measured(started)
        require(use['process_CPU_seconds_including_imports'] <= CPU and use['wall_seconds_including_imports'] <= WALL
                and use['peak_RSS_bytes'] <= RAM, 'Final metadata admission resource cap exceeded')
        save_new(root / OUTPUT, admission)
        admission_raw = (root / OUTPUT).read_bytes()
        save_new(root / STAGE / 'ADMISSION_PREPARATION_RECEIPT.json', {
            'status': 'COMPLETE_METADATA_ONLY_ACTUAL_RESULTS_ADMISSION_NO_ARCHIVE_BUILD',
            'admission_path': OUTPUT.as_posix(), 'admission_bytes': len(admission_raw),
            'admission_sha256': hashlib.sha256(admission_raw).hexdigest(), 'public_freeze_commit': args.freeze_commit,
            'engineering_repair_history': {'path': scope['engineering_repair_history_path'],
                'sha256': pins[scope['engineering_repair_history_path']]['sha256']},
            'metadata_preparation_attempt': 'V2 separate one-shot engineering stage',
            'original_V1_attempt_preserved': scope['original_failed_preparation'],
            'scientific_search_or_QA_rerun_in_this_repair': False,
            'all_text_input_byte_pins': pins, 'metadata_only': True,
            'reference_only_prior_metadata_pins': reference_observed,
            'producer_binary_stat_presence_records': presence,
            'producer_binary_bodies_opened': False,
            'new_HTTP_requests': 0, 'source_value_reads': 0, 'archive_or_part_payload_reads': 0,
            'detector_or_profile_runs': 0, **use})
        print(json.dumps({'status': 'COMPLETE_METADATA_ONLY_ACTUAL_RESULTS_ADMISSION_NO_ARCHIVE_BUILD',
            'admission_path': OUTPUT.as_posix(), 'admission_sha256': hashlib.sha256(admission_raw).hexdigest(), **use}))
    except BaseException as error:
        if created and not (root / STAGE / 'FAILURE_RECEIPT.json').exists():
            save_new(root / STAGE / 'FAILURE_RECEIPT.json', {'status': 'INCOMPLETE_METADATA_ADMISSION_PRESERVE_NO_RETRY_NO_OVERWRITE',
                'error_type': type(error).__name__, 'error': str(error), 'public_freeze_commit': args.freeze_commit,
                'text_inputs_observed': pins, 'new_HTTP_requests': 0, 'source_value_reads': 0,
                'archive_or_part_payload_reads': 0, 'detector_or_profile_runs': 0, **measured(started)})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(handles):
            handle.close()


if __name__ == '__main__':
    main()
