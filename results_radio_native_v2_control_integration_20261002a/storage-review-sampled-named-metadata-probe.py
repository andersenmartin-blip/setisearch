#!/usr/bin/env python3
"""One tiny generated growth probe at the sampler's final named-stat boundary."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


source = Path(sys.argv[1]).resolve(); raw = source.read_bytes()
assert raw == source.read_bytes()
module = types.ModuleType('held_storage_sampler_review'); module.__file__ = str(source)
exec(compile(raw, str(source), 'exec'), module.__dict__)
original_stat = module.os.stat
with tempfile.TemporaryDirectory(prefix='seti-storage-sample-review-') as temporary:
    root = Path(temporary); target = root/'growth.dat'
    before = b'initial\n'; after = b'extended generated review bytes\n'
    target.write_bytes(before)
    calls = [0]; fired = [False]
    def grow_at_final_named_stat(name, *args, **kwargs):
        if name == 'growth.dat':
            calls[0] += 1
            if calls[0] == 2:
                target.write_bytes(after); fired[0] = True
        return original_stat(name, *args, **kwargs)
    module.os.stat = grow_at_final_named_stat
    try:
        inventory = module.sampled_storage_inventory(root)
    finally:
        module.os.stat = original_stat
    info = target.stat(); row = next(item for item in inventory['rows'] if item['path'] == 'growth.dat')
    outcome = {'mutation_fired': fired[0], 'initial_file_bytes': len(before),
        'final_named_stat_bytes': info.st_size, 'charged_file_bytes': row['bytes'],
        'latest_observed_size_charged': row['bytes'] >= info.st_size,
        'latest_observed_ctime_retained': row['ctime_ns'] == info.st_ctime_ns,
        'latest_observed_mtime_retained': row['mtime_ns'] == info.st_mtime_ns}
print(json.dumps({'schema': 'radio-native-v2-independent-sampler-named-stat-review-v1',
                  'reviewer_kind': 'independent_machine_agent', 'human_review': False,
                  'source_path': str(source), 'source_pin': pin(raw),
                  'runner_pin': pin(Path(__file__).read_bytes()), 'synthetic_only': True,
                  'generated_source_bytes': [len(before), len(after)],
                  'real_historical_b_files_read_or_mutated': False,
                  'real_c_journal_created': False, 'real_control_dispatched': False,
                  'telescope_reads': 0, 'result': outcome,
                  'all_expectations_met': all(outcome[key] is True for key in
                    ('mutation_fired', 'latest_observed_size_charged',
                     'latest_observed_ctime_retained', 'latest_observed_mtime_retained'))},
                 sort_keys=True, indent=2))
