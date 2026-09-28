#!/usr/bin/env python3
"""One bounded handoff of the retained codec archive; not a control experiment."""
import hashlib
import json
from pathlib import Path
import resource
import sys
import tarfile
import time
import traceback

import h5py
import hdf5plugin
import numpy as np

from radio_receiver_adapter_common import ROOT, PINS, context
from seti_repeater import hdf5_filter_contract_radio as filters
from seti_repeater import source_radio
from seti_repeater import transfer_m43g as native
from seti_repeater.whole_cadence_source_radio import (
    ARCHIVE_SHA256, MEMBER_SHA256, texture_law, bind_codec_cadence, validate_codec_binding,
)
from seti_repeater.whole_cadence_reference_radio import digest, reduce_native_run

BASE = ROOT/'results_radio_whole_cadence_handoff_2026-09-28'
OUT = BASE/'native01'
OLD = ROOT/'results_radio_hd189733_codec_2026-09-28'
NS = 'radio-whole-cadence-handoff-engineering-20260928'


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')


def file_hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024*1024), b''): h.update(part)
    return h.hexdigest()


def main():
    started = time.monotonic(); OUT.mkdir(parents=True, exist_ok=False)
    pins = dict(PINS)
    paths = ['RADIO_WHOLE_CADENCE_HANDOFF_2026-09-28_SCOPE.md',
        'scripts/radio_whole_cadence_handoff.py', 'src/seti_repeater/whole_cadence_source_radio.py',
        'src/seti_repeater/whole_cadence_reference_radio.py',
        'src/seti_repeater/pipeline_receiver_radio.py', 'src/seti_repeater/transfer_m43g.py',
        'src/seti_repeater/hdf5_filter_contract_radio.py', 'src/seti_repeater/source_radio.py',
        'src/seti_repeater/source_v0p6.py', 'src/seti_repeater/search_v0p6.py']
    for path in paths: pins[path] = file_hash(ROOT/path)
    write(OUT/'input_pins.json', pins)
    def budget():
        if time.monotonic()-started > 600: raise RuntimeError('Native handoff time cap')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > 512*1024**2: raise RuntimeError('Native handoff RSS cap')
        if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) > 128*1024**2:
            raise RuntimeError('Native handoff evidence cap')
    try:
        for path, checksum in pins.items():
            if file_hash(ROOT/path) != checksum: raise ValueError('Input changed: '+path)
        archive = OLD/'retained_hdf5_fixtures.tar.xz'
        if file_hash(archive) != ARCHIVE_SHA256: raise ValueError('Archive changed')
        member = 'legacy_declaration_fixture.h5'; restored = OUT/member
        with tarfile.open(archive, 'r:xz') as handle:
            if set(handle.getnames()) != {'current_encoder_fixture.h5', member}:
                raise ValueError('Unexpected archive members')
            info = handle.getmember(member)
            if not info.isfile() or info.size != 27894547: raise ValueError('Unexpected retained member')
            with restored.open('xb') as out, handle.extractfile(info) as src:
                for part in iter(lambda: src.read(1024*1024), b''): out.write(part)
        if file_hash(restored) != MEMBER_SHA256: raise ValueError('Restored member changed')
        old_runtime = json.loads((OLD/'fixture01/runtime.json').read_text())
        runtime = source_radio.runtime()
        for key in ('numpy', 'h5py', 'hdf5', 'hdf5plugin'):
            if runtime[key] != old_runtime[key]: raise ValueError('Codec version changed')
        binary_root = Path(h5py.__file__).resolve().parent.parent
        for name, checksum in old_runtime['binary_sha256s'].items():
            if file_hash(binary_root/name) != checksum: raise ValueError('Codec binary changed: '+name)
        runtime_receipt = {'versions': runtime, 'verified_binary_sha256s': old_runtime['binary_sha256s'],
            'python_executable_sha256': file_hash(Path(sys.executable))}
        write(OUT/'runtime.json', runtime_receipt)
        c = context('validation'); w = c.native_window; lo, hi = w['archive_interval']
        decoded = [json.loads((OLD/f'reconcile01/validation_row{i:02d}_decode.json').read_text())
                   for i in range(16)]
        normalized = [json.loads((OLD/f'reconcile01/validation_row{i:02d}_normalization.json').read_text())
                      for i in range(16)]
        for i, (a,b) in enumerate(zip(decoded, normalized, strict=True)):
            if a['row'] != i or b['row'] != i or a['role'] != 'validation' or b['role'] != 'validation':
                raise ValueError('Retained row order changed')
        receipt = {'archive_sha256': ARCHIVE_SHA256, 'member_sha256': MEMBER_SHA256,
            'role': 'validation', 'window_identity': w['identity'], 'archive_interval': [lo,hi],
            'decoded_row_sha256s': [r['selected_native_sha256'] for r in decoded],
            'runtime_receipt_sha256': digest(runtime_receipt)}
        case = hashlib.sha256((NS+'/retained-codec-native').encode()).hexdigest()
        law = texture_law(); law_sha = digest(law)
        with h5py.File(restored, 'r', rdcc_nbytes=8*1024**2) as handle:
            ds = handle['data']; filters.check_dataset(ds, [[32008,1,[0,3,4,0,2]]])
            if ds.shape != (16,1,264503296) or ds.chunks != (1,1,1048576) or ds.dtype != np.dtype('<f4'):
                raise ValueError('Retained HDF5 geometry changed')
            run, handoff = bind_codec_cadence(c, lambda i: ds[i,0,lo:hi], case_identity=case,
                law=law, input_receipt=receipt,
                expected_normalized_row_hashes=[r['normalized_sha256'] for r in normalized])
        validate_codec_binding(run, case_identity=case, noise_law_sha256=law_sha)
        write(OUT/'source_handoff.json', handoff)
        write(OUT/'source_scopes.json', {k: json.loads(s.scope_json) for k,s in run.sources.items()})
        if run.modelled_bytes > 256*1024**2: raise RuntimeError('Native modelled-array cap')
        print('Retained codec bytes bound to six explicitly shared-payload source slots', flush=True)
        budget(); store = run.build_store(); run.validate_store(store)
        np.savez_compressed(OUT/'scores.npz', **{f'{k}_{t:03d}_{w:03d}':v for (k,t,w),v in sorted(store.arrays.items())})
        write(OUT/'score_provenance.json', store.provenance)
        write(OUT/'score_vector_ids.json', [[*k,v] for k,v in sorted(store.expected_ids.items())])
        validate_codec_binding(run, case_identity=case, noise_law_sha256=law_sha)
        unit = reduce_native_run(run, store, case_identity=case, noise_law_sha256=law_sha)
        write(OUT/'maximum.json', unit.record()); budget()
        rejects = {}
        for label, case_arg, law_arg in [('wrong_case', 'f'*64, law_sha), ('wrong_law', case, 'e'*64)]:
            try: validate_codec_binding(run, case_identity=case_arg, noise_law_sha256=law_arg)
            except ValueError as error: rejects[label] = str(error)
            else: raise ValueError('Source boundary accepted '+label)
        # Exercise corruption on a copied score inventory; never edit the retained archive.
        saved = store.expected_ids['off',80,129]; store.expected_ids['off',80,129] = 'd'*64
        try:
            reduce_native_run(run, store, case_identity=case, noise_law_sha256=law_sha)
        except ValueError as error: rejects['changed_last_off_vector_id'] = str(error)
        else: raise ValueError('Native boundary accepted a changed OFF identity')
        finally: store.expected_ids['off',80,129] = saved
        write(OUT/'negative_handoff_checks.json', rejects)
        for path, checksum in pins.items():
            if file_hash(ROOT/path) != checksum: raise ValueError('Input changed during handoff: '+path)
        result = {'schema': 'radio-whole-cadence-native-handoff-result-v1',
            'status': 'RETAINED_CODEC_TO_NATIVE_MAXIMUM_ENGINEERING_PASS',
            'source_slots': 6, 'unique_native_textures': 1, 'new_codec_fixtures_generated': 0,
            'native_source_identities': len(run.source_ids), 'native_cache_receipts': len(store.provenance['native_caches']),
            'score_vectors': len(store.arrays), 'score_cells_preserved': sum(x.size for x in store.arrays.values()),
            'complete_on_hypotheses': unit.record()['visited_hypotheses'],
            'maximum': unit.record()['maximum'], 'eligible_on_cells': unit.record()['eligible_cells'],
            'modelled_array_bound_bytes': run.modelled_bytes,
            'active_seconds': time.monotonic()-started,
            'peak_process_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'source_preparation_sha256': PINS['config/radio_hd189733_source_preparation_20260927.json'],
            'negative_handoff_checks': len(rejects),
            'gaussian_renderer_qualified': False, 'independent_null_cadences_generated': 0,
            'scientific_allocations_charged': 0, 'new_source_requests': 0,
            'telescope_values_opened': False, 'original_codec_failure_preserved': True,
            'telescope_admission_authorized': False}
        write(OUT/'result.json', result); print(json.dumps(result, indent=2), flush=True)
    except BaseException as error:
        write(OUT/'error.json', {'error': repr(error), 'traceback': traceback.format_exc(),
            'active_seconds': time.monotonic()-started, 'automatic_retry_authorized': False})
        raise


if __name__ == '__main__': main()
