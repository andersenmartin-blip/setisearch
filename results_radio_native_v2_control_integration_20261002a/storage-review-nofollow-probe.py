#!/usr/bin/env python3
"""Tiny generated path/ancestor race probes of held historical helper bytes.

All file mutations target newly generated temporary fixture bytes. No archived
b row, real c journal, activation marker or telescope file is read or modified.
"""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


source = Path(sys.argv[1]).resolve()
raw = source.read_bytes()
assert raw == source.read_bytes()
module = types.ModuleType('held_historical_read_review')
module.__file__ = str(source)
exec(compile(raw, str(source), 'exec'), module.__dict__)
fixture = b'tiny-review-only\n'
expected = pin(fixture)
cases = [('baseline', None, True),
         ('file_symlink_before_read', 'file_symlink', False),
         ('ancestor_symlink_before_read', 'ancestor_symlink', False),
         ('file_replace_during_read', 'file_replace', False),
         ('file_content_mutation_during_read', 'file_content', False),
         ('ancestor_replace_during_read', 'ancestor_replace', False),
         ('ancestor_chmod_during_read', 'ancestor_chmod', False),
         ('ancestor_symlink_during_read', 'ancestor_switch', False),
         ('hardlink_before_read', 'hardlink', False),
         ('pin_content_mismatch', 'pin_mismatch', False),
         ('dotdot_path_before_read', 'dotdot', False)]
results = []
original_read = module.os.read
for name, action, expected_accept in cases:
    module.os.read = original_read
    with tempfile.TemporaryDirectory(prefix='seti-storage-read-review-') as temporary:
        root = Path(temporary); parent = root/'plain'; parent.mkdir()
        target = parent/'input.json'; target.write_bytes(fixture)
        path = str(target); wanted = expected.copy(); fired = [False]
        if action == 'file_symlink':
            real = parent/'real.json'; target.rename(real); target.symlink_to(real)
        elif action == 'ancestor_symlink':
            real_parent = root/'real'; parent.rename(real_parent); parent.symlink_to(real_parent, target_is_directory=True)
        elif action == 'hardlink':
            module.os.link(target, parent/'second-link')
        elif action == 'pin_mismatch':
            wanted = pin(b'other-review-only\n')
        elif action == 'dotdot':
            path = str(parent/'..'/'plain'/'input.json')
        elif action:
            def racing_read(fd, size):
                output = original_read(fd, size)
                if not fired[0]:
                    fired[0] = True
                    if action == 'file_replace':
                        target.rename(parent/'old-input'); target.write_bytes(fixture)
                    elif action == 'file_content':
                        target.write_bytes(b'X' + fixture[1:])
                    elif action == 'ancestor_replace':
                        parent.rename(root/'old-parent'); parent.mkdir(); target.write_bytes(fixture)
                    elif action == 'ancestor_chmod':
                        parent.chmod(0o711)
                    elif action == 'ancestor_switch':
                        parent.rename(root/'old-parent'); other = root/'new-parent'; other.mkdir()
                        (other/'input.json').write_bytes(fixture)
                        parent.symlink_to(other, target_is_directory=True)
                return output
            module.os.read = racing_read
        try:
            observed = module.read_raw(path, wanted)
        except Exception as error:
            result = {'name': name, 'accepted': False,
                      'error': type(error).__name__ + ': ' + str(error)}
        else:
            result = {'name': name, 'accepted': True, 'read_pin': pin(observed)}
        result.update(expected_accept=expected_accept,
                      expectation_met=result['accepted'] is expected_accept,
                      mutation_fired=fired[0])
        results.append(result)
    module.os.read = original_read
print(json.dumps({'schema': 'radio-native-v2-independent-storage-read-review-v1',
                  'reviewer_kind': 'independent_machine_agent', 'human_review': False,
                  'source_path': str(source), 'source_pin': pin(raw),
                  'generated_fixture_bytes': len(fixture), 'synthetic_only': True,
                  'historical_b_files_read_or_mutated': False,
                  'real_c_journal_created': False, 'real_control_dispatched': False,
                  'telescope_reads': 0, 'cases': results,
                  'all_expectations_met': all(item['expectation_met'] for item in results)},
                 sort_keys=True, indent=2))
