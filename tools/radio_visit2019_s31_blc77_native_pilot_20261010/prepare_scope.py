"""Prepare one prospective native pilot scope from completed metadata only.

Never imports scientific dependencies, decodes amplitudes or invokes search.
Opaque file hashes authenticate existing acquired bytes. The resulting scope
requires a subsequent public freeze, late root admission and separate root GO.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import resource
import signal
import sys
import time

sys.dont_write_bytecode = True


def main():
    start = time.monotonic()
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'qualified-metadata', 'acquisition-scope', 'acquisition-result', 'acquisition-execution',
                 'acquisition-outer', 'extra-input-pins'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--shared-root', action='append', required=True)
    p.add_argument('--CPU-seconds', type=int, default=6000)
    p.add_argument('--wall-seconds', type=int, default=7200)
    p.add_argument('--memory-bytes', type=int, default=1610612736)
    args = p.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (20, 22))
    resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
    signal.alarm(120)
    root = Path(args.root)
    if not root.is_absolute() or root.resolve() != root:
        raise ValueError('Canonical root required')
    worker = Path(__file__).parent / 'search_saved.py'
    spec = importlib.util.spec_from_file_location('inert_native_pilot_metadata', worker)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require = module.require
    require('numpy' not in sys.modules and 'h5py' not in sys.modules and 'scipy' not in sys.modules,
            'Scope preparation must remain stdlib metadata-only')
    def pin(path):
        path = Path(path)
        require(path.is_absolute() and path.resolve() == path and root in path.parents and path.is_file(),
                'Canonical existing root-contained input required')
        return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
                'sha256': module.digest(path)}
    prerequisites = {key: pin(getattr(args, cli)) for key, cli in
        (('qualified_metadata_pin', 'qualified_metadata'), ('acquisition_scope_pin', 'acquisition_scope'), ('acquisition_result_pin', 'acquisition_result'),
         ('acquisition_execution_pin', 'acquisition_execution'), ('acquisition_outer_pin', 'acquisition_outer'))}
    metadata = module.read_pin(root, prerequisites['qualified_metadata_pin'])
    geometry = module.derive_geometry(metadata)
    acquisition = module.read_pin(root, prerequisites['acquisition_result_pin'])
    acquisition_scope = module.read_pin(root, prerequisites['acquisition_scope_pin'])
    execution = module.read_pin(root, prerequisites['acquisition_execution_pin'])
    outer = module.read_pin(root, prerequisites['acquisition_outer_pin'])
    require(acquisition['schema'] == module.ACQ_SCHEMA and acquisition['status'] == module.ACQ_PASS
            and acquisition['qualified_metadata_pin'] == prerequisites['qualified_metadata_pin']
            and execution['schema'] == 'SETI_VISIT2019_ONE_NATIVE_RAW_EXECUTION_RECEIPT_V1'
            and execution['status'] == module.ACQ_PASS and execution['resource_caps_satisfied'] is True
            and execution['ACQUISITION_RESULT_pin'] == prerequisites['acquisition_result_pin']
            and outer['schema'] == 'SETI_VISIT2019_ONE_NATIVE_RAW_FULL_CHILD_RESOURCE_RECEIPT_V1'
            and outer['status'] == 'PASS_WHOLE_CHILD_RESOURCES_AND_COMPLETE_ACQUISITION'
            and outer['actual_child_return_code'] == 0 and outer['resource_caps_satisfied'] is True
            and outer['ACQUISITION_RESULT_pin'] == prerequisites['acquisition_result_pin']
            and outer['EXECUTION_RECEIPT_pin'] == prerequisites['acquisition_execution_pin'],
            'Actual complete closed raw acquisition required before scope preparation')
    extra_manifest_pin = pin(args.extra_input_pins)
    extra = module.read_pin(root, extra_manifest_pin)
    require(extra['schema'] == 'SETI_VISIT2019_NATIVE_PILOT_EXTRA_INPUT_PINS_V1'
            and isinstance(extra['input_pins'], list), 'Explicit extra provenance pin manifest required')
    pins = {}
    def add(value):
        require(value['path'] not in pins or pins[value['path']] == value, 'Conflicting duplicate source pin')
        module.read_pin(root, value, False)
        pins[value['path']] = value
    for value in list(prerequisites.values()) + [extra_manifest_pin] + extra['input_pins']:
        add(value)
    for name in ('search_saved.py', 'prepare_scope.py', 'launch_once.py', 'METHOD.md', 'dependencies/detector.py'):
        add(pin(Path(__file__).parent / name))
    require(acquisition_scope['schema'] == 'SETI_VISIT2019_ONE_NATIVE_RAW_ACQUISITION_SCOPE_V1'
            and acquisition_scope['qualified_metadata_pin'] == prerequisites['qualified_metadata_pin']
            and acquisition['scope_sha256'] == prerequisites['acquisition_scope_pin']['sha256'],
            'Exact acquisition scope provenance required')
    for key, value in acquisition_scope.items():
        if key.endswith('_pin') and isinstance(value, dict) and set(value) == {'path', 'bytes', 'sha256'}:
            add(value)
    add(execution['SOURCE_BODY_LEDGER_pin'])
    for value in acquisition['verified_input_end_pins']:
        add(value)
    for key in ('scope_pin', 'root_admission_pin', 'common_pin', 'worker_pin'):
        add(outer[key])
    descriptors = module.read_pin(root, acquisition_scope['descriptor_manifest_pin'])
    for evidence in descriptors['typed_index_evidence_pins']:
        add(evidence)
    require(len(acquisition['compact_files']) == 6, 'All six closed compact records required')
    acquisition_directory = module.confined(root, prerequisites['acquisition_result_pin']['path']).parent
    # Source writer holds the stable directory flock until its terminal receipt.
    import fcntl
    fd = os.open(acquisition_directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for record in acquisition['compact_files']:
            add(record['pin'])
            for raw in record['raw_rows']:
                raw_pin = pin(module.confined(acquisition_directory, raw['path']))
                add(raw_pin)
                require(raw_pin['bytes'] == raw['bytes'] and raw_pin['sha256'] == raw['sha256'],
                        'Durable original compressed source row pin differs')
    finally:
        os.close(fd)
    limits = {**module.MAX_LIMITS, 'CPU_seconds': args.CPU_seconds,
              'wall_seconds': args.wall_seconds, 'memory_bytes': args.memory_bytes}
    require(all(type(limits[k]) is int and 0 < limits[k] <= v for k, v in module.MAX_LIMITS.items()),
            'Prospective limits exceed root authorized maximum')
    roots = [Path(x) for x in args.shared_root]
    require(roots and len(set(roots)) == len(roots) and all(x.is_absolute() and x.resolve() == x for x in roots)
            and all(not p.is_relative_to(q) for p in roots for q in roots if p != q), 'Disjoint canonical shared roots required')
    scope = {'schema': 'SETI_VISIT2019_FIXED_ONE_NATIVE_PILOT_SEARCH_SCOPE_V1',
        'family_id': module.FAMILY, 'search_script_sha256': module.digest(worker),
        'unchanged_detector_sha256': module.DETECTOR_SHA,
        'detector_path': (Path(__file__).parent / 'dependencies/detector.py').relative_to(root).as_posix(),
        'root_GO_required': True, 'retry_resume_rerun_authorized': False,
        'geometry': geometry, **prerequisites, 'input_pins': sorted(pins.values(), key=lambda x: x['path']),
        'limits': limits, 'shared_workspace_roots': [str(x) for x in roots], 'hdf5_version': '1.14.6',
        'output_directory': 'results/' + module.FAMILY + '/measurement',
        'selection_rule': 'zero-based floor(actual native-frequency-chunk count/2), before amplitudes; all full safe interior cores',
        'scored_scans': list(module.SCANS), 'profile_scans': list(module.SCANS),
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'independent_validation_status': 'BLOCKED_UNCHANGED',
        'qualified_sky_detection': False, 'calibrated_SNR_FAP': False, 'OFF_veto_applied': False}
    require(module.output_reservation_bytes(geometry) <= limits['output_bytes'],
            'Actual decoded/maps/profiles geometry exceeds pre-amplitude output reservation')
    stage = root / 'results' / module.FAMILY
    stage.mkdir(parents=True, exist_ok=True)
    target = Path(__file__).parent / 'scope.json'
    marker = stage / 'SCOPE_PREPARATION_STARTED_ONCE.json'
    receipt_path = stage / 'SCOPE_PREPARATION_RECEIPT.json'
    require(not target.exists() and not marker.exists() and not receipt_path.exists(), 'Scope preparation is once-only; no retry/replace')
    module.save_json(marker, {'status': 'STARTED_METADATA_ONLY_SCOPE_PREPARATION', 'amplitudes_opened': False})
    for value in pins.values():
        module.read_pin(root, value, False)
    require(time.process_time() <= 20 and time.monotonic() - start <= 120, 'Scope metadata cap exceeded')
    module.save_json(target, scope)
    receipt = {'status': 'COMPLETE_METADATA_ONLY_NATIVE_PILOT_SCOPE_PREPARED_NO_SCIENCE_GO',
        'scope_pin': pin(target), 'geometry': geometry, 'input_pin_count': len(pins),
        'generator_pin': pin(Path(__file__)), 'amplitudes_opened': False, 'NumPy_h5py_imported': False,
        'source_GETs': 0, 'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - start,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    module.save_json(receipt_path, receipt)
    signal.alarm(0)
    print(json.dumps(receipt, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
