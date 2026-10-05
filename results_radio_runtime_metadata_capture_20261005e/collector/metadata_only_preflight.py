"""Bounded current-base-Python metadata preflight; never launch installed Python.

Native files are only statted here. This injected reader deliberately supplies
no native bytes, hashes, ELF interpretation, imports or filter observations.
The real collector's default reader and capture path are unchanged.
"""
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import resource
import signal
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    signal.alarm(60)
    started = time.monotonic()
    expected_python = Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12')
    if (not sys.flags.isolated or not sys.flags.dont_write_bytecode or not sys.flags.no_site or
            Path(sys.executable).resolve(strict=True) != expected_python or
            Path(sys.prefix).resolve(strict=True) != Path(sys.base_prefix).resolve(strict=True) or
            sys.version_info[:2] != (3, 12)):
        raise RuntimeError('pinned current base Python with -I -B -S required')
    spec = importlib.util.spec_from_file_location('collector_metadata_only_inert', ROOT / 'collect_runtime_identity.py')
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    class MetadataOnlyReader(collector.BoundedReader):
        def native(self, path, *, require_elf=True):
            return {'path': str(path), 'identity': collector.identity(Path(path).stat()),
                    'metadata_only_preflight_native_bytes_not_read': True}

    reader = MetadataOnlyReader(limit=64 * 1024 * 1024)
    python_raw, python_identity = reader.file(expected_python, cap=64 * 1024 * 1024)
    python_sha = hashlib.sha256(python_raw).hexdigest()
    if python_sha != 'fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7':
        raise collector.Refusal('current base interpreter differs from expected whole bytes')
    python_bytes = len(python_raw)
    del python_raw
    source_raw, source_identity = reader.file(ROOT / 'collect_runtime_identity.py', cap=1024 * 1024)
    source_sha, source_bytes = hashlib.sha256(source_raw).hexdigest(), len(source_raw)
    del source_raw
    control_read_bytes = reader.charged_bytes
    input_raw, _ = reader.file(ROOT / 'record-inputs.json', cap=65536)
    venv = Path(json.loads(input_raw)['venv_root'])
    site = venv / 'lib/python3.12/site-packages'
    inputs, input_pin = collector._read_record_inputs(ROOT / 'record-inputs.json', reader, venv)
    relocations, relocation_pin = collector._read_record_relocations(ROOT / 'record-relocations.json', reader, venv)
    results = {}
    for name, version in collector.COHORT.items():
        distribution = importlib.metadata.PathDistribution(site / (name + '-' + version + '.dist-info'))
        # Stdlib-only corroboration of the failure mechanism, never authoritative.
        actual_stdlib_projection = list(map(str, distribution.files))
        inventory = collector.distribution_inventory(name, distribution, venv, reader, relocations, inputs)
        reconstructed = inventory['stdlib_distribution_files_projection']['presence_filtered_paths']
        if actual_stdlib_projection != reconstructed:
            raise collector.Refusal('actual stdlib filtered projection differs from raw-derived projection')
        if inventory['file_count'] != {'numpy': 904, 'h5py': 106, 'hdf5plugin': 26}[name]:
            raise collector.Refusal('actual complete raw RECORD row count differs from exact cohort expectation')
        results[name] = inventory
    if results['numpy']['verified_generated_script_relocations'] != 2:
        raise collector.Refusal('exact two actual generated script relocations not verified')
    if any(name in sys.modules for name in collector.COHORT):
        raise collector.Refusal('scientific module was unexpectedly imported')
    report = {'schema': 'seti-raw-record-metadata-only-preflight-v1',
              'status': 'METADATA_LAYOUT_PREFLIGHT_PASSED_ONLY',
              'authority': dict(collector.NO_AUTHORITY),
              'interpreter': {'executable': sys.executable, 'resolved_path': str(expected_python),
                              'bytes': python_bytes, 'sha256': python_sha, 'identity': python_identity,
                              'isolated': bool(sys.flags.isolated),
                              'dont_write_bytecode': bool(sys.flags.dont_write_bytecode),
                              'no_site': bool(sys.flags.no_site),
                              'prefix': sys.prefix, 'base_prefix': sys.base_prefix},
              'installed_python_launched': False, 'scientific_modules_imported': False,
              'scientific_package_native_bytes_read': 0, 'native_filters_observed': False,
              'distributions': results, 'record_inputs_pin': input_pin,
              'record_relocations_pin': relocation_pin,
              'collector_sha256': source_sha, 'collector_bytes': source_bytes,
              'collector_identity': source_identity,
              'explicit_input_read_charged_bytes': reader.charged_bytes - control_read_bytes,
              'explicit_interpreter_and_collector_read_charged_bytes': control_read_bytes,
              'explicit_total_read_charged_bytes': reader.charged_bytes,
              'explicit_total_read_limit_bytes': reader.limit,
              'stdlib_projection_version_metadata_reads_are_implicit': True,
              'wall_limit_seconds': 60, 'address_space_limit_bytes': 512 * 1024 * 1024,
              'elapsed_seconds': time.monotonic() - started}
    path = ROOT / 'metadata-only-preflight.json'
    with path.open('xb') as output:
        output.write(collector.canonical(report))
    print(json.dumps({'status': report['status'], 'file': str(path),
                      'raw_row_counts': {n: d['file_count'] for n, d in results.items()},
                      'stdlib_filtered_counts': {n: len(d['stdlib_distribution_files_projection']['presence_filtered_paths'])
                                                  for n, d in results.items()},
                      'explicit_input_read_charged_bytes': report['explicit_input_read_charged_bytes'],
                      'explicit_total_read_charged_bytes': reader.charged_bytes,
                      'elapsed_seconds': report['elapsed_seconds']}, sort_keys=True))


if __name__ == '__main__':
    main()
