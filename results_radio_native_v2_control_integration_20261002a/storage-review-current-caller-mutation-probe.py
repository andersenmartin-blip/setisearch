#!/usr/bin/env python3
"""Pure tiny mutation probe at the current-inventory validation boundary.

The hook only schedules mutation of the caller-owned dictionary after the
reviewed validator has returned. It does not change any authenticated external
record or production source. The allocated snapshot should retain 512 bytes.
"""
import hashlib
import json
from pathlib import Path
import sys
import types


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


source = Path(sys.argv[1]).resolve(); raw = source.read_bytes()
assert raw == source.read_bytes()
module = types.ModuleType('held_current_inventory_review')
module.__file__ = str(source)
exec(compile(raw, str(source), 'exec'), module.__dict__)
rows = [{'path': '.', 'kind': 'directory', 'device': 11, 'inode': 1,
         'bytes': 0, 'allocated_bytes': 0}]
for index in range(8):
    rows.append({'path': f'cases/case{index:02d}', 'kind': 'directory',
                 'device': 11, 'inode': 2+index, 'bytes': 0, 'allocated_bytes': 0})
rows.append({'path': 'cases/case00/tiny-source', 'kind': 'file',
             'device': 11, 'inode': 10, 'bytes': 512, 'allocated_bytes': 512})
caller = {'scope': '/synthetic/current-control', 'rows': rows,
          'entry_count': len(rows), 'logical_bytes': 512, 'allocated_bytes': 512}
original_validator = module._validate_inventory_totals
fired = [False]


def schedule_caller_mutation(inventory):
    original_validator(inventory)
    if not fired[0]:
        fired[0] = True
        caller['rows'].pop()
        caller.update(logical_bytes=0, allocated_bytes=0,
                      entry_count=len(caller['rows']))


module._validate_inventory_totals = schedule_caller_mutation
try:
    allocated = module.allocate_storage(caller,
        reserved_bytes=0, directory_reserved_bytes=0)
except Exception as error:
    result = {'accepted': False, 'error': type(error).__name__+': '+str(error),
              'snapshot_preserved': False}
else:
    observed = allocated['whole_logical_bytes_with_remaining_reservation']
    result = {'accepted': True, 'observed_whole_logical_bytes': observed,
              'observed_whole_allocated_bytes': allocated['whole_allocated_bytes_with_remaining_reservation'],
              'snapshot_preserved': observed == 512
                  and allocated['whole_allocated_bytes_with_remaining_reservation'] == 512}
print(json.dumps({'schema': 'radio-native-v2-independent-current-mutation-review-v1',
                  'reviewer_kind': 'independent_machine_agent', 'human_review': False,
                  'source_path': str(source), 'source_pin': pin(raw),
                  'runner_pin': pin(Path(__file__).read_bytes()),
                  'synthetic_only': True, 'expected_snapshot_bytes': 512,
                  'mutation_fired': fired[0], 'caller_bytes_after_mutation': caller['logical_bytes'],
                  'real_control_dispatched': False, 'telescope_reads': 0,
                  'result': result}, sort_keys=True, indent=2))
