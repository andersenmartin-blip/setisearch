#!/usr/bin/env python3
"""Read only the closed byte fixtures; never recreate a storage qualification."""
import json
from pathlib import Path
import resource
import time
from unittest.mock import patch

from seti_repeater import physical_evidence_radio as e
from seti_repeater.empty_null_radio import canonical
from seti_repeater.pipeline_receiver_radio import NativeRun

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_radio_physical_evidence_2026-09-29'
Q = OUT / 'qualification01'


def inventory():
    return {p.relative_to(Q).as_posix(): {'bytes': p.stat().st_size,
            'sha256': e.sha(p.read_bytes())} for p in Q.rglob('*') if p.is_file()}


def main():
    fixed = json.loads((Q / 'fixed_before_storage.json').read_bytes())
    before = inventory()
    pins = {p: e.sha((ROOT / p).read_bytes()) for p in (
        'src/seti_repeater/physical_evidence_radio.py',
        'scripts/radio_physical_evidence_reader_audit.py',
        'results_radio_physical_evidence_2026-09-29/reader_tests.log')}
    with (OUT / 'reader_audit_fixed.json').open('xb') as f:
        f.write(canonical({'source_inventory': before, 'code_and_test_sha256s': pins,
                           'write_or_replay_authority': False}))
    started = time.monotonic()
    rows = []
    with patch.object(e.Writer, 'create', side_effect=AssertionError('Writer forbidden')), \
         patch.object(e.Writer, 'checkpoint', side_effect=AssertionError('Writer forbidden')), \
         patch('numpy.random.Generator', side_effect=AssertionError('RNG forbidden')), \
         patch('numpy.random.SeedSequence', side_effect=AssertionError('RNG forbidden')), \
         patch.object(NativeRun, '__init__', side_effect=AssertionError('Native run forbidden')):
        for name, result_name, schedule in (
                ('representation01', 'representation_result.json', fixed['schedule']),
                ('capacity01', 'capacity_result.json', fixed['schedule'][:1])):
            prior = json.loads((Q / result_name).read_bytes())
            t = time.monotonic()
            view = e.inspect(Q / name,
                expected_config_sha256=prior['reservation_sha256'],
                expected_last_checkpoint_sha256=prior['latest_checkpoint_sha256'])
            inspected = time.monotonic() - t
            restored = []
            for expected in schedule:
                raw = view.snapshot(expected['index'])
                assert len(raw) == expected['bytes'] and e.sha(raw) == expected['sha256']
                restored.append({'index': expected['index'], 'bytes': len(raw), 'sha256': e.sha(raw)})
            assert len(view.checkpoint_bytes) == len(schedule)
            for mapping in (view.files, view.verified_values):
                try:
                    mapping['mutation'] = b'forbidden'
                except TypeError:
                    pass
                else:
                    raise AssertionError('Read-only cache or inventory is mutable')
            rows.append({'name': name, 'inspect_seconds': inspected,
                'inspect_and_restore_seconds': time.monotonic() - t,
                'restored': restored, **view.summary()})
        assert inventory() == before
    result = {'schema': 'radio-physical-evidence-reader-audit-v1', 'status': 'PASS',
        'elapsed_seconds': time.monotonic() - started,
        'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        'fixtures': rows, 'closed_qualification_files_unchanged': True,
        'new_random_values': 0, 'new_native_scores': 0, 'new_physical_decisions': 0,
        'new_storage_fixture_executions': 0,
        'timing_is_descriptive_not_a_controlled_benchmark': True}
    with (OUT / 'reader_audit_result.json').open('xb') as f:
        f.write(canonical(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
