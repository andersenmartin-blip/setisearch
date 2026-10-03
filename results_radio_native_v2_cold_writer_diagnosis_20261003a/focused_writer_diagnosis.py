"""Retain the existing tiny writer unittest's original temporary evidence.

No source/test modifications, admission bypass, real control or science run.
Only the existing tiny final-report probe is launched by its original test.
"""
import hashlib
import io
import json
from pathlib import Path
import shutil
import traceback
import unittest
from unittest import mock

import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_resource_finalization as finalization
from test_radio_native_v2_resource_finalization import ResourceFinalizationTests


DESTINATION = Path(__file__).resolve().parent
OBSERVE = fixture.observe_process
TEST = 'test_actual_isolated_final_report_writer_fsyncs_and_exits'


def pin(path):
    raw = Path(path).read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


summaries = []
for ordinal in range(12):
    destination = DESTINATION / f'attempt-{ordinal:02d}'
    destination.mkdir()
    observation_call = {}

    def retain_observation(*args, **kwargs):
        argv, scope, label, identity_path = args[:4]
        observation_call.update(argv=argv, temporary_scope=str(scope), label=label,
            identity_path=str(identity_path), observer_options=kwargs)
        try:
            result = OBSERVE(*args, **kwargs)
            observation_call['returned_stdout_hex'] = result[1].hex()
            observation_call['returned_stderr_hex'] = result[2].hex()
            observation_call['returned_observation'] = result[0]
            return result
        except BaseException as error:
            observation_call['exception'] = repr(error)
            (destination / 'observer-exception.txt').write_text(traceback.format_exc())
            raise
        finally:
            shutil.copytree(scope, destination / 'retained-actual-writer')
            observation_call['retained_files'] = {
                path.relative_to(scope).as_posix(): pin(path)
                for path in sorted(Path(scope).rglob('*')) if path.is_file()}
            (destination / 'observation-call.json').write_text(json.dumps(observation_call,
                sort_keys=True, indent=2) + '\n')

    output = io.StringIO()
    with mock.patch.object(fixture, 'observe_process', side_effect=retain_observation):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(
            unittest.TestSuite([ResourceFinalizationTests(TEST)]))
    (destination / 'unittest-output.log').write_text(output.getvalue())
    observation = json.loads((destination / 'retained-actual-writer' /
        'final-report-writer-observation.json').read_text())
    identity = destination / 'retained-actual-writer' / finalization.FINAL_WRITER_IDENTITY_NAME
    summary = {'attempt': ordinal, 'testsRun': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors),
        'exit_code': observation['exit_code'], 'reason': observation['reason'],
        'reported_identity_verified': observation['reported_identity_verified'],
        'identity_exists_after_observer': identity.exists(),
        'identity': json.loads(identity.read_text()) if identity.exists() else None,
        'source_pins': {str(Path(module.__file__).resolve()): pin(module.__file__)
            for module in (fixture, finalization)}}
    summaries.append(summary)
    print(json.dumps(summary, sort_keys=True), flush=True)
    if not result.wasSuccessful():
        break

(DESTINATION / 'focused-writer-summary.json').write_text(json.dumps(summaries,
    sort_keys=True, indent=2) + '\n')
