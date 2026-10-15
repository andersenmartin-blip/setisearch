"""Complete numerical footprint fixture, no detector/normalizer/RNG execution."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import time

from array_adapter import load_case_field, verify_arrays, write_arrays
from layout import specs, storage_bounds, values
from runtime import guard, store


def main():
    phase, request_path = sys.argv[1:]
    request = json.loads(Path(request_path).read_text())
    if request['mode'] != 'COMPLETE_CASE_ENGINEERING_ONLY':
        raise ValueError('No science admission')
    code_root = Path(__file__).resolve().parent
    for name, pin in request['source_pins'].items():
        if store.digest_file(code_root / name) != pin: raise ValueError('Source pin differs')
    folder = Path(request['folder']); bundle = folder / 'payload'
    expected_specs = specs(); bounds = storage_bounds(expected_specs)
    layout = json.loads((code_root / 'ARRAY_LAYOUT.json').read_text())
    if layout['specs'] != expected_specs or layout['bounds'] != bounds:
        raise ValueError('Frozen layout differs from source definitions')
    if phase == 'produce':
        dependency = json.loads((code_root / 'SOURCE_DEPENDENCY.json').read_text())
        cache = Path(dependency['cache'])
        if store.digest_file(cache / 'MANIFEST.json') != dependency['manifest_sha256']:
            raise ValueError('Previous engineering metadata manifest differs')
        bundle.mkdir()
        budget = store.Budget(bounds['per_case_conditional_bundle_cap_bytes'])
        start = time.process_time()
        for name, pin in dependency['members'].items():
            source = cache / name
            if source.stat().st_size != pin['bytes'] or store.digest_file(source) != pin['sha256']:
                raise ValueError('Previous engineering asset changed: ' + name)
            if name == 'output.msgpack.gz' and pin['bytes'] > 128 * 1024**2:
                raise ValueError('Physical compressed metadata cap exceeded')
            with source.open('rb') as inp, budget.writer(bundle / name) as out:
                while block := inp.read(1 << 20): out.write(block)
        descriptors = write_arrays(bundle / 'case_arrays.npz', expected_specs, values, budget,
                                    physical_cap=bounds['NPZ_physical_writer_cap_bytes'])
        document = {'schema': 'SETI_COMPLETE_ENGINEERING_NUMERIC_ARRAYS_V1',
                    'arrays': descriptors, 'bounds': bounds,
                    'scientific_data_or_QA': False, 'source_array_paths_explicit': True}
        raw = (json.dumps(document, indent=2, sort_keys=True) + '\n').encode()
        if len(raw) > 1024**2: raise ValueError('Array descriptor asset cap exhausted')
        with budget.writer(bundle / 'CASE_ARRAYS.json') as out: out.write(raw)
        manifest = json.loads((cache / 'MANIFEST.json').read_text())
        manifest['members'] = {p.name: {'bytes': p.stat().st_size, 'sha256': store.digest_file(p)}
                               for p in sorted(bundle.iterdir()) if p.is_file()}
        raw = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
        if len(raw) > 65536: raise ValueError('Manifest physical cap exhausted')
        with budget.writer(bundle / 'MANIFEST.json') as out: out.write(raw)
        guard.durable_json(folder / 'PRODUCER_METRICS.json', {
            'arrays_written': len(descriptors), 'all_array_raw_bytes': bounds['all_array_raw_bytes'],
            'NPZ_bytes': (bundle / 'case_arrays.npz').stat().st_size,
            'bundle_bytes': budget.used, 'writer_self_CPU_s': time.process_time() - start,
            'source_metadata_sha256_unchanged': dependency['members']['output.msgpack.gz']['sha256'],
            'complete_source_geometry_plus_two_edge_arrays': True,
            'new_scientific_cases_or_draws': 0})
    elif phase == 'verify':
        metadata, receipt = store.verify_bundle(bundle, cap=bounds['per_case_conditional_bundle_cap_bytes'])
        if (len(metadata['all_ON_threshold_hypotheses']) != 61440 or
                sum(len(h['OFF_comparisons']) for h in metadata['all_ON_threshold_hypotheses']) != 184320):
            raise ValueError('Retained dense record census changed')
        del metadata
        document = json.loads((bundle / 'CASE_ARRAYS.json').read_text())
        if document['bounds'] != bounds: raise ValueError('Array bound document differs')
        if (bundle / 'case_arrays.npz').stat().st_size > bounds['NPZ_physical_writer_cap_bytes']:
            raise ValueError('NPZ physical cap exceeded')
        numeric = verify_arrays(bundle / 'case_arrays.npz', document['arrays'], expected_specs)
        typed = []
        for spec in expected_specs[-2:]:
            array = load_case_field(bundle, spec['path'])
            expected = values(spec)
            if (array.dtype.str != expected.dtype.str or array.shape != expected.shape or
                    array.tobytes() != expected.tobytes()):
                raise ValueError('Typed consumer edge bits differ')
            typed.append({'path': spec['path'], 'dtype': array.dtype.str,
                          'shape': list(array.shape), 'bits_equal': True})
        receipt.update(status='COMPLETE_CASE_TRANSPORT_INTEGRITY_ONLY', numeric=numeric,
                       typed_edge_checks=typed,
                       dense_records_retained=61440, OFF_receipts_retained=184320,
                       file_inventory={p.name: {'bytes': p.stat().st_size, 'sha256': store.digest_file(p)}
                                       for p in sorted(bundle.iterdir())})
        guard.durable_json(folder / 'VERIFICATION.json', receipt)
    else:
        raise ValueError('Unknown engineering phase')


if __name__ == '__main__': main()
