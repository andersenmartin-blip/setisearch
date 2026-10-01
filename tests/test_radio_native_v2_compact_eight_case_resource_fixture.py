"""Small preparation tests only: never generate a maximum source or run eight cases."""
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
SPEC = importlib.util.spec_from_file_location('compact_eight_preparation', SCRIPT)
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)
PYTHON = str(Path(sys.executable).resolve())
NODE = shutil.which('node')


class CompactEightPreparationTests(unittest.TestCase):
    def test_eight_domains_are_distinct_fixed_and_reject_nonordinals(self):
        domains = [fixture.source_domain(ordinal) for ordinal in range(8)]
        self.assertEqual(len(set(domains)), 8)
        self.assertEqual(len({hashlib.sha256(domain+b'\0'*8).hexdigest() for domain in domains}), 8)
        for ordinal, domain in enumerate(domains):
            self.assertIn(fixture.NAMESPACE.encode(), domain)
            self.assertTrue(domain.endswith(ordinal.to_bytes(8, 'big')))
            self.assertEqual(domain, fixture.source_domain(ordinal))
        for value in (-1, 8, 0.0, True, '0', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                fixture.source_domain(value)

    def test_plan_only_cli_pins_fresh_derivations_and_creates_no_source_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory)/'never-created'
            process = subprocess.run([PYTHON,'-I','-S','-B',str(SCRIPT),'--prepare-plan'],
                cwd=directory, capture_output=True, timeout=30, env={**fixture.CHILD_ENVIRONMENT,
                    'PATH':str(Path(NODE).parent)+':/usr/bin:/bin'})
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertEqual(process.stderr, b'')
            plan = json.loads(process.stdout)
            self.assertEqual(process.stdout, fixture.canonical(plan)+b'\n')
            self.assertEqual(plan['schema'], fixture.PLAN_SCHEMA)
            self.assertEqual(plan['namespace'], fixture.NAMESPACE)
            self.assertEqual(len(plan['cases']), 8)
            self.assertEqual(len({row['source_case_id'] for row in plan['cases']}), 8)
            self.assertEqual(plan['child_environment'], fixture.CHILD_ENVIRONMENT)
            for key, value in fixture.AUTHORITY.items():
                self.assertEqual(plan[key], value, key)
            self.assertEqual(plan['original_limits'], fixture.LIMITS)
            self.assertFalse(plan['scope_reuse_or_retry_permitted'])
            self.assertTrue(plan['complete_runtime_freeze_required'])
            self.assertTrue(plan['public_immutable_preread_required'])
            self.assertEqual(set(plan['code_files']), set(fixture.CODE_FILES))
            self.assertFalse(scope.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])
            self.assertEqual(plan['execution_status'], 'BLOCKED_PREPARATION_REVIEW')
            self.assertEqual(plan['execution_blockers'], list(fixture.EXECUTION_BLOCKERS))
            self.assertTrue(plan['execution_blockers'])
            self.assertFalse(plan['large_source_generation_admitted'])
            self.assertFalse(plan['activation_guard_complete'])
            self.assertFalse(plan['complete_resource_measurement_join_qualified'])
            derived = fixture.templates((ROOT/fixture.CODE_FILES[0]).read_text())
            for name, raw in derived.items():
                self.assertEqual(plan['derived_code'][name], {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})

    def test_fresh_code_derivations_are_syntax_valid_without_executing_preparation(self):
        derived = fixture.templates((ROOT/fixture.CODE_FILES[0]).read_text())
        compile(derived['prepare.py'], 'fresh-prepare.py', 'exec')
        for name in ('prepare.py','fresh-caller.js'):
            self.assertNotIn(b'offline_full03', derived[name])
            self.assertNotIn(b'/bin/bash', derived[name])
        self.assertIn(fixture.NAMESPACE.encode(), derived['prepare.py'])
        self.assertIn(fixture.PREFIX.encode(), derived['prepare.py'])
        self.assertIn(b'--command-worker', derived['fresh-caller.js'])
        with tempfile.TemporaryDirectory() as directory:
            for name, raw in derived.items():
                if name.endswith('.js'):
                    path = Path(directory)/name; path.write_bytes(raw)
                    result = subprocess.run([NODE,'--check',str(path)],capture_output=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertEqual(set(Path(directory).iterdir()), {Path(directory)/name for name in derived if name.endswith('.js')})

    def test_big_entrypoints_refuse_before_touching_any_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory)/'not-created'
            calls = [lambda:fixture.run_control(scope,{}, {}, {}, None),
                lambda:fixture.validate_activation({}, {}, {}, repo=scope),
                lambda:fixture.control_worker(scope), lambda:fixture.verifier_worker(scope),
                lambda:fixture.command_worker(scope,'command-tail','never executed'),
                lambda:fixture.exec_command_child(scope,'command-tail','never executed')]
            for call in calls:
                with self.subTest(call=call), mock.patch.object(fixture.subprocess,'Popen') as launch:
                    with self.assertRaisesRegex(RuntimeError, 'BLOCKED_PREPARATION_REVIEW'):
                        call()
                    launch.assert_not_called()
                    self.assertFalse(scope.exists())
            modes = [['--control-worker',str(scope)],['--verifier-worker',str(scope)],
                ['--command-worker',str(scope),'command-tail','never executed'],
                ['--exec-command-child',str(scope),'command-tail','never executed'],
                ['--run','--scope',str(scope),'--plan',str(scope/'plan.json'),
                    '--preread',str(scope/'preread.json'),'--complete-freeze',str(scope/'freeze.json')]]
            for arguments in modes:
                result = subprocess.run([PYTHON,'-I','-S','-B',str(SCRIPT),*arguments],
                    cwd=directory,capture_output=True,timeout=10,env=fixture.CHILD_ENVIRONMENT)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'BLOCKED_PREPARATION_REVIEW',result.stderr)
                self.assertFalse(scope.exists())
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_storage_inventory_includes_directories_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'subdirectory').mkdir(); (root/'subdirectory/data').write_bytes(b'tiny')
            result = fixture.inventory(root)
            rows = {row['path']:row for row in result['files']}
            self.assertEqual(set(rows), {'.','subdirectory','subdirectory/data'})
            self.assertEqual(rows['.']['kind'],'directory')
            self.assertEqual(rows['subdirectory']['kind'],'directory')
            self.assertEqual(rows['subdirectory/data']['bytes'],4)
            self.assertEqual(result['logical_bytes'],sum(path.lstat().st_size for path in [root,root/'subdirectory',root/'subdirectory/data']))
            self.assertEqual(result['allocated_bytes'],sum(path.lstat().st_blocks*512 for path in [root,root/'subdirectory',root/'subdirectory/data']))
            (root/'unaccounted-symlink').symlink_to(root/'subdirectory/data')
            with self.assertRaises(ValueError): fixture.inventory(root)

    def test_no_follow_json_and_pin_refuse_fifo_and_symlink_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fifo = root/'fifo'; os.mkfifo(fifo)
            data = root/'data.json'; data.write_bytes(b'{}'); link=root/'symlink';link.symlink_to(data)
            started=time.monotonic()
            for path in (fifo,link):
                for read in (fixture.small_json, fixture.pin):
                    with self.subTest(path=path,read=read), self.assertRaises((ValueError,OSError)):
                        read(path)
            self.assertLess(time.monotonic()-started,1)

    def test_wait4_nested_small_child_peak_is_maximum_process_not_concurrent_sum(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); identity=root/'child-identity.json'
            grandchild = "import time; payload=bytearray(24*1024*1024); payload[::4096]=b'x'*(len(payload)//4096); time.sleep(0.08)"
            source = '\n'.join([
                'import json,os,resource,subprocess,sys,time',
                'with open(sys.argv[1],"x") as stream:',
                ' json.dump({"procfs_pid":int(os.readlink("/proc/self")),"namespace_pid":os.getpid()},stream); stream.flush(); os.fsync(stream.fileno())',
                'time.sleep(0.03)',
                'own=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024',
                'child=subprocess.Popen([sys.executable,"-I","-S","-B","-c",sys.argv[2]])',
                '_,status,usage=os.wait4(child.pid,0); child.returncode=os.waitstatus_to_exitcode(status)',
                'assert child.returncode==0',
                'print(json.dumps({"own_peak_bytes":own,"grandchild_peak_bytes":usage.ru_maxrss*1024}))'])
            observation,stdout,stderr=fixture.observe_process([PYTHON,'-I','-S','-B','-c',source,str(identity),grandchild],
                root,'small-nested',identity,deadline=time.monotonic()+10,pipe_output=True)
            data=json.loads(stdout)
            self.assertEqual(stderr,b'')
            self.assertEqual(observation['exit_code'],0)
            self.assertIsNone(observation['reason'])
            self.assertTrue(observation['includes_entire_child_lifetime'])
            self.assertTrue(observation['wait4_maximum_includes_completely_reaped_descendants'])
            self.assertFalse(observation['aggregate_concurrent_rss_measured'])
            self.assertGreaterEqual(data['grandchild_peak_bytes'],24*1024**2)
            self.assertGreaterEqual(observation['wait4_ru_maxrss_bytes'],data['grandchild_peak_bytes'])
            self.assertLess(observation['peak_rss_bytes'],data['own_peak_bytes']+data['grandchild_peak_bytes'])
            self.assertFalse(observation['raw_stdout_duplicate_written'])
            self.assertEqual((root/'small-nested-stdout.log').read_bytes(),b'')


def tiny_json(value):
    # This order-preserving wire agrees with JSON.stringify for these tiny values.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def tiny_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def write_tiny_json(path, value):
    path.write_bytes((tiny_json(value) + '\n').encode())


def tiny_lossless_inputs(root):
    python = str(Path(sys.executable).resolve())
    source_path = root / 'source-æ-漢-🛰.wire'
    payload_path = root / 'deterministic-source.bin'
    payload = b'tiny deterministic engineering fixture only\n'
    payload_path.write_bytes(payload)
    # The immutable source contract is ASCII. UTF-8 is exercised in retained
    # envelope metadata, original commands/paths and the create_tree request.
    outputs = [tiny_json('range %02d: "quoted" \\ path\tend\n' % ordinal)[1:-1].encode()
        for ordinal in range(38)]
    source = b''.join(outputs)
    source_path.write_bytes(source)
    source_pin = tiny_pin(source)
    identity = {'namespace': 'tiny-lossless-offline-fixture', 'case_ordinal': 0,
        'source_case_id': 'small-roundtrip-case', 'engineering_case_binding_sha256': '1' * 64,
        'source_sha256': tiny_pin(payload)['sha256'], 'native_case_binding_verified': False}
    plans, receipts, records = [], [], []
    offset = 0
    for ordinal, raw in enumerate(outputs):
        output = raw.decode('ascii')
        arguments = {'cmd': 'tiny-source-reader %02d %s' % (ordinal, source_path),
            'max_output_tokens': 64, 'yield_time_ms': 1}
        request = tiny_json({'tool': 'exec_command', 'arguments': arguments})
        envelope = {'output': output, 'exit_code': 0, 'wall_time_seconds': 0.001,
            'chunk_id': '%08d' % ordinal, 'unicode_metadata': 'æ漢🛰️',
            'escaped_metadata': '"quoted" \\ path\tend\n'}
        response = tiny_json(envelope)
        request_pin, response_pin, output_pin = tiny_pin(request.encode()), tiny_pin(response.encode()), tiny_pin(raw)
        plans.append({'ordinal': ordinal, 'tool': 'exec_command', 'path': str(source_path),
            'offset': offset, 'bytes': len(raw), 'source_sha256': source_pin['sha256'],
            'output_sha256': output_pin['sha256'], 'response_reserved_bytes': 4096, 'arguments': arguments})
        receipts.append({'ordinal': ordinal, 'path': str(source_path), 'offset': offset,
            'bytes': len(raw), 'source_sha256': source_pin['sha256'], 'output_sha256': output_pin['sha256'],
            'envelope_entries': [[key, None if key == 'output' else value] for key, value in envelope.items()],
            'envelope_bytes': response_pin['bytes'], 'envelope_sha256': response_pin['sha256']})
        records.append({'ordinal': ordinal, 'kind': 'actual_source_read', 'tool': 'exec_command',
            'request_json': request, 'request_bytes': request_pin['bytes'], 'request_sha256': request_pin['sha256'],
            'raw_result': envelope, 'response_json': response,
            'response_bytes': response_pin['bytes'], 'response_sha256': response_pin['sha256']})
        offset += len(raw)
    prefix = '{"tool":"mcp__tiny_create_tree","arguments":{"note":"æ漢🛰️","tree":[{"path":"tiny.txt","content":"'
    suffix = '"}]}}'
    create_request = prefix + source.decode('ascii') + suffix
    # The request is valid JSON despite repeated quotes, slashes and line escapes.
    json.loads(create_request)
    request_pin = tiny_pin(create_request.encode())
    records.append({'ordinal': 38, 'kind': 'actual_connector', 'tool': 'mcp__tiny_create_tree',
        'request_json': create_request, 'request_bytes': request_pin['bytes'],
        'request_sha256': request_pin['sha256'], 'response_json': '{"offline_fixture":true}',
        'retained_metadata': 'æ漢🛰️ "quoted" \\ path\tend\n'})
    prepared = {'scope': str(root), 'python': python, 'control_case_identity': identity,
        'source_bytes': len(payload), 'source_sha256': tiny_pin(payload)['sha256'],
        'archive_bytes': len(source) + len(payload), 'archive_files': 2,
        'files': [{'path': source_path.name, **source_pin}, {'path': payload_path.name, **tiny_pin(payload)}],
        'reads': plans, 'request_view': {'path': str(source_path), 'source_bytes': len(source),
            'source_sha256': source_pin['sha256'], 'offset': 0, 'bytes': len(source),
            'sha256': source_pin['sha256'], 'request_prefix': prefix, 'request_suffix': suffix,
            'request_bytes': request_pin['bytes'], 'request_sha256': request_pin['sha256']}}
    transcript = {'schema': 'tiny-lossless-original-transcript-v1', 'control_case_identity': identity,
        'qualified': {'client': {'records': records}},
        'seen': {'unicode': 'æ漢🛰️', 'escaped': '\\ "quote"\t\n'},
        'deliveries': [{'ordinal': 0, 'fixture_only': True}], 'read_receipts': receipts}
    full_path, prepared_path, recipe_path = root / 'tiny-full.json', root / 'prepared.json', root / 'recipe.py'
    write_tiny_json(full_path, transcript)
    write_tiny_json(prepared_path, prepared)
    # If retained verification accidentally executes the recipe, it must fail.
    recipe_path.write_text("raise RuntimeError('Tiny retained-source recipe must never execute')\n")
    return {'full_path': full_path, 'prepared_path': prepared_path, 'recipe_path': recipe_path,
        'source_path': source_path, 'payload_path': payload_path, 'python': python,
        'original_pin': tiny_pin(full_path.read_bytes()), 'source_pin': source_pin, 'payload_pin': tiny_pin(payload)}


class SmallLosslessProjectorRoundtrip(unittest.TestCase):
    def test_tiny_resource_helper_roundtrip(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'The embedded helper requires the existing local Node runtime')
        with tempfile.TemporaryDirectory(prefix='tiny-lossless-projector-') as directory:
            root = Path(directory).resolve()
            inputs = tiny_lossless_inputs(root)
            self.assertLess(inputs['source_pin']['bytes'], 4096)
            self.assertLess(inputs['original_pin']['bytes'], 100 * 1024)
            helper = root / 'lossless-helper.js'
            helper.write_text(fixture.LOSSLESS_HELPER)
            projection_path, audit_path = root / 'projection.json', root / 'audit.json'
            project_identity, verify_identity = root / 'project-identity.json', root / 'verify-identity.json'
            project_options, verify_options = root / 'project-options.json', root / 'verify-options.json'
            write_tiny_json(project_options, {'fullPath': str(inputs['full_path']),
                'preparedPath': str(inputs['prepared_path']), 'recipePath': str(inputs['recipe_path']),
                'projectionPath': str(projection_path), 'recipeArguments': [str(root), inputs['python'],
                    'tiny-no-network-fixture', '0', 'tiny-archive-prefix'], 'identityPath': str(project_identity)})
            result = subprocess.run([node, str(helper), '--resource-project', str(project_options)],
                capture_output=True, text=True, timeout=10,
                env=fixture.CHILD_ENVIRONMENT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            projected = json.loads(result.stdout)
            self.assertEqual((projected['bytes'], projected['sha256']),
                (inputs['original_pin']['bytes'], inputs['original_pin']['sha256']))
            projection = json.loads(projection_path.read_bytes())
            self.assertEqual(len(projection['large_field_replacements']), 77)
            self.assertEqual(Counter(row['field'] for row in projection['large_field_replacements']),
                Counter({'raw_result.output': 38, 'response_json': 38, 'request_json': 1}))
            self.assertEqual(len(projection['transcript']['qualified']['client']['records']), 39)
            write_tiny_json(verify_options, {'projectionPath': str(projection_path),
                'recipePath': str(inputs['recipe_path']), 'retainedSourcePath': str(inputs['source_path']),
                'retainedPayloadPath': str(inputs['payload_path']), 'auditPath': str(audit_path),
                'python': inputs['python'], 'identityPath': str(verify_identity)})
            before_verify = {path.name for path in root.iterdir()}
            result = subprocess.run([node, str(helper), '--resource-verify-retained', str(verify_options)],
                capture_output=True, text=True, timeout=10,
                env=fixture.CHILD_ENVIRONMENT)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertEqual(json.loads(result.stdout)['status'], 'PASSED')
            audit = json.loads(audit_path.read_bytes())
            rebuilt = audit['reconstructed_full_transcript']
            self.assertEqual((rebuilt['bytes'], rebuilt['sha256']),
                (inputs['original_pin']['bytes'], inputs['original_pin']['sha256']))
            self.assertTrue(rebuilt['hash_only_sink'])
            self.assertFalse(rebuilt['full_duplicate_file_written'])
            self.assertEqual((audit['restored_source_output_fields'], audit['restored_complete_raw_response_json_fields'],
                audit['restored_complete_create_tree_request_fields']), (38, 38, 1))
            self.assertTrue(audit['exact_original_metadata_and_property_order_preserved'])
            self.assertTrue(audit['no_accumulated_reconstructed_large_strings'])
            self.assertTrue(audit['no_reconstructed_full_buffer'])
            self.assertFalse(audit['deterministic_recipe_reexecuted_for_this_proof'])
            self.assertFalse(audit['additional_full_source_copy_written'])
            self.assertFalse(audit['additional_full_transcript_copy_written'])
            self.assertEqual({path.name for path in root.iterdir()} - before_verify,
                {'audit.json', 'verify-identity.json'})
            self.assertEqual(tiny_pin(inputs['source_path'].read_bytes()), inputs['source_pin'])
            self.assertEqual(tiny_pin(inputs['payload_path'].read_bytes()), inputs['payload_pin'])
            for identity_path in (project_identity, verify_identity):
                observed = json.loads(identity_path.read_bytes())
                self.assertGreater(observed['procfs_pid'], 0)
                self.assertGreater(observed['namespace_pid'], 0)
            for field in ('network_fetches', 'actual_connector_calls', 'actual_functions_sdk_calls',
                    'native_case_reservations', 'native_case_executions', 'scientific_cases_run', 'rng_draws', 'telescope_reads'):
                self.assertEqual(audit[field], 0)
            self.assertFalse(audit['execution_authorized'])
            self.assertFalse(audit['scientific_execution_authorized'])
            # A changed retained byte must close before any completed audit.
            changed = bytearray(inputs['source_path'].read_bytes()); changed[0] ^= 1
            inputs['source_path'].write_bytes(changed)
            changed_audit, changed_identity = root/'changed-audit.json', root/'changed-identity.json'
            options = json.loads(verify_options.read_bytes())
            options.update(auditPath=str(changed_audit), identityPath=str(changed_identity))
            changed_options=root/'changed-options.json';write_tiny_json(changed_options,options)
            failed = subprocess.run([node,str(helper),'--resource-verify-retained',str(changed_options)],
                capture_output=True,text=True,timeout=10,env=fixture.CHILD_ENVIRONMENT)
            self.assertNotEqual(failed.returncode,0)
            self.assertIn('Exact regenerated source',failed.stderr)
            self.assertFalse(changed_audit.exists())


if __name__=='__main__':
    unittest.main()
