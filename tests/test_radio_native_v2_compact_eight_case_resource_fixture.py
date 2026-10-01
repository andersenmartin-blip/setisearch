"""Small preparation tests only: never generate a maximum source or run eight cases."""
from collections import Counter
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import selectors
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

    def test_derived_source_worker_refuses_missing_admission_and_false_isolation_before_writes(self):
        derived = fixture.templates((ROOT/fixture.CODE_FILES[0]).read_text())
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); root = parent/'case00'; root.mkdir()
            recipe = parent/'prepare.py'; recipe.write_bytes(derived['prepare.py'])
            arguments = [str(recipe),str(root),PYTHON,fixture.NAMESPACE,'0',fixture.PREFIX+'/case00-fixed']
            result = subprocess.run([PYTHON,'-I','-S','-B',*arguments],
                capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'retained admission digest required',result.stderr)
            self.assertEqual(list(root.iterdir()),[])
            # A caller cannot manufacture the claimed isolation merely by
            # supplying a vector which contains the expected flag strings.
            result = subprocess.run([PYTHON,'-S','-B',*arguments,str(root/'worker-admission.json'),'a'*64],
                capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'Actual isolated no-site no-bytecode interpreter required',result.stderr)
            self.assertEqual(list(root.iterdir()),[])

    def test_locally_valid_supplied_claim_cannot_generate_or_execute_cached_admission_code(self):
        import marshal
        import struct
        from tests.test_radio_native_v2_worker_admission import synthetic_worker_materials
        derived = fixture.templates((ROOT/fixture.CODE_FILES[0]).read_text())
        with tempfile.TemporaryDirectory() as directory:
            material = synthetic_worker_materials(directory,ordinal=0,
                plan=fixture.build_plan(),derived_sources=derived)
            root = material['case_root']
            before = sorted(str(path.relative_to(root)) for path in root.rglob('*'))
            result = subprocess.run(material['argv'],capture_output=True,
                env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'BLOCKED_PREPARATION_REVIEW',result.stderr)
            self.assertEqual(before,sorted(str(path.relative_to(root)) for path in root.rglob('*')))
            self.assertFalse((root/'deterministic-source.bin').exists())
            self.assertFalse((root/'preparation-identity.json').exists())
            result = subprocess.run([material['argv'][0],'-X','utf8',*material['argv'][1:]],
                capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'exact preparation worker argv',result.stderr)
            self.assertEqual(before,sorted(str(path.relative_to(root)) for path in root.rglob('*')))
            module = material['code_root']/'scripts/radio_native_v2_worker_admission.py'
            cached = Path(importlib.util.cache_from_source(str(module)))
            cached.parent.mkdir()
            marker = Path(directory)/'unchecked-bytecode-executed'
            payload = compile('from pathlib import Path; Path('+repr(str(marker))+').write_text("bad")',str(module),'exec')
            info = module.stat()
            cached.write_bytes(importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(info.st_mtime),info.st_size)+marshal.dumps(payload))
            result = subprocess.run(material['argv'],capture_output=True,
                env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(marker.exists())
            self.assertFalse((root/'deterministic-source.bin').exists())
            self.assertFalse((root/'preparation-identity.json').exists())

    def test_component_bootstrap_refuses_fifo_alias_and_oversize_before_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'component.py'; raw=b'value=7\n'
            wanted={'component.py':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}
            source.write_bytes(raw)
            self.assertEqual(fixture.pinned_component(root,'component.py',wanted)['value'],7)
            source.unlink(); os.mkfifo(source)
            start=time.monotonic()
            with self.assertRaisesRegex(ValueError,'regular material source'):
                fixture.pinned_component(root,'component.py',wanted)
            self.assertLess(time.monotonic()-start,1)
            source.unlink(); target=root/'target.py'; target.write_bytes(raw); source.symlink_to(target)
            with self.assertRaises(OSError): fixture.pinned_component(root,'component.py',wanted)
            source.unlink(); source.write_bytes(raw*100)
            with self.assertRaisesRegex(ValueError,'regular material source'):
                fixture.pinned_component(root,'component.py',wanted)

    def test_plan_selected_admission_source_cannot_replace_independent_entry_implementation(self):
        from tests.test_radio_native_v2_worker_admission import synthetic_worker_materials
        import radio_native_v2_worker_admission as admission
        with tempfile.TemporaryDirectory() as directory:
            material=synthetic_worker_materials(directory)
            marker=Path(directory)/'plan-selected-implementation-executed'
            source=material['code_root']/admission.SELF
            malicious=('from pathlib import Path\nPath('+repr(str(marker))+').write_text("executed")\n').encode()
            source.write_bytes(malicious)
            # Refresh every self-asserted plan/freeze/proof source pin. The
            # entrypoint's reviewed implementation pin stays independent.
            plan=copy.deepcopy(material['plan']); freeze=copy.deepcopy(material['freeze']); proof=copy.deepcopy(material['proof'])
            plan['code_files'][admission.SELF]=tiny_pin(malicious)
            freeze['code_sha256s'][admission.SELF]=tiny_pin(malicious)['sha256']
            proof['code_files_verified']=plan['code_files']
            proof['plan_sha256']=tiny_pin(admission.canonical(plan))['sha256']
            proof['complete_freeze_sha256']=tiny_pin(admission.canonical(freeze))['sha256']
            bundle=admission.build_admission_bundle(plan,freeze,proof,execution_scope=str(material['scope']),ordinal=0)
            material['bundle_path'].write_bytes(admission.bundle_bytes(bundle)); digest=fixture.pin(material['bundle_path'])['sha256']
            original=fixture.pin(ROOT/admission.SELF)
            program='\n'.join(['import json,sys','from pathlib import Path',
                'p=Path(sys.argv[1]); m={"__name__":"independent_entry_test","__file__":str(p)}',
                'exec(compile(p.read_bytes(),str(p),"exec"),m)',
                'm["REPO"]=Path(sys.argv[2])',
                'm["WORKER_ADMISSION_IMPLEMENTATION_PIN"]=json.loads(sys.argv[5])',
                'm["checked_worker_bundle"](sys.argv[3],sys.argv[4],"prepare")'])
            before=sorted(str(path) for path in material['case_root'].rglob('*'))
            result=subprocess.run([PYTHON,'-I','-S','-B','-c',program,str(SCRIPT),str(material['code_root']),
                str(material['bundle_path']),digest,json.dumps(original)],capture_output=True,
                env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'regular material source',result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(before,sorted(str(path) for path in material['case_root'].rglob('*')))

    def test_derived_node_workers_refuse_at_closed_gate_before_identity_or_outputs(self):
        from tests.test_radio_native_v2_worker_admission import synthetic_worker_materials, tiny_prepared, phase_descriptor, retain_role
        import radio_native_v2_worker_admission as admission
        derived=fixture.templates((ROOT/fixture.CODE_FILES[0]).read_text())
        for role in ('caller','lossless-project','lossless-verify-retained'):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as directory:
                material=synthetic_worker_materials(directory,plan=fixture.build_plan(),derived_sources=derived)
                root=material['case_root']; prepared=tiny_prepared(material)
                inputs={'prepared_json':phase_descriptor(root/'prepared.json')}
                if role!='caller':
                    (root/'public-evidence').mkdir()
                    recipe=[str(root),PYTHON,fixture.NAMESPACE,'0',fixture.PREFIX+'/case00-fixed',
                        str(material['bundle_path']),material['bundle_sha256']]
                    options={'fullPath':str(root/'caller-result.json'),'preparedPath':str(root/'prepared.json'),
                        'recipePath':str(root/'derived/prepare.py'),
                        'projectionPath':str(root/'public-evidence/caller-transcript-compact-lossless.json'),
                        'recipeArguments':recipe,'identityPath':str(root/'lossless-project-identity.json')}
                    if role=='lossless-project':
                        transcript={'schema':fixture.SCHEMA,'control_case_identity':prepared['control_case_identity'],
                            'qualified':{},'seen':[],'deliveries':[],'read_receipts':[]}
                        write_tiny_json(root/'caller-result.json',transcript)
                        write_tiny_json(root/'project-arguments.json',options)
                        inputs.update(arguments_json=phase_descriptor(root/'project-arguments.json'),
                            caller_transcript=phase_descriptor(root/'caller-result.json'),
                            preparation_bundle=phase_descriptor(material['bundle_path']))
                    else:
                        # The retained payload is deliberately tiny and cannot
                        # qualify fixed26MiB reconstruction. The closed gate
                        # must run before even inspecting helper arguments.
                        projection=root/'public-evidence/caller-transcript-compact-lossless.json'; write_tiny_json(projection,{'schema':'synthetic-unqualified'})
                        (root/'deterministic-source.bin').write_bytes(b'tiny unqualified retained payload')
                        options={'projectionPath':str(projection),'recipePath':str(root/'derived/prepare.py'),
                            'retainedSourcePath':prepared['request_view']['path'],'retainedPayloadPath':str(root/'deterministic-source.bin'),
                            'auditPath':str(root/'public-evidence/reconstruction-audit.json'),'python':PYTHON,
                            'identityPath':str(root/'lossless-verify-identity.json')}
                        write_tiny_json(root/'projection-verify-arguments.json',options)
                        inputs.update(arguments_json=phase_descriptor(root/'projection-verify-arguments.json'),
                            projection=phase_descriptor(projection),source_wire=phase_descriptor(prepared['request_view']['path']),
                            deterministic_source=phase_descriptor(root/'deterministic-source.bin'),
                            preparation_bundle=phase_descriptor(material['bundle_path']))
                admitted=retain_role(material,role,inputs)
                if role!='lossless-verify-retained':
                    checked=admission.validate_worker_admission(str(admitted['bundle_path']),role=role,ordinal=0,
                        argv=admitted['argv'],environment=dict(fixture.CHILD_ENVIRONMENT),expected_bundle_sha256=admitted['bundle_sha256'])
                    self.assertFalse(checked['publication_claim_independently_verified'])
                    self.assertFalse(checked['full_source_domain_content_verified'])
                before=sorted(str(path) for path in root.rglob('*'))
                result=subprocess.run(admitted['argv'],capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(b'BLOCKED_PREPARATION_REVIEW',result.stderr)
                self.assertEqual(result.stdout,b'')
                self.assertEqual(before,sorted(str(path) for path in root.rglob('*')))
                for name in ('caller-start.json','caller-summary.json','lossless-project-identity.json',
                             'lossless-verify-identity.json','public-evidence/reconstruction-audit.json'):
                    self.assertFalse((root/name).exists(),name)

    def test_admitted_derived_helper_legacy_modes_cannot_write_without_guard(self):
        derived=fixture.templates((ROOT/fixture.CODE_FILES[0]).read_text())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); inputs=tiny_lossless_inputs(root)
            helper=root/'admitted-helper.js'; helper.write_bytes(derived['lossless-helper.js'])
            recipe_args=root/'five-arguments.json'; write_tiny_json(recipe_args,[str(root),PYTHON,'tiny','0','tiny-prefix'])
            output=root/'must-not-be-written.json'; audit=root/'must-not-be-audited.json'
            vectors=[['--project',str(inputs['full_path']),str(inputs['prepared_path']),str(inputs['recipe_path']),str(output),str(recipe_args)],
                ['--verify-projection',str(output),str(inputs['recipe_path']),str(root/'fresh-root'),str(audit),PYTHON],
                ['--verify-retained-source',str(output),str(inputs['recipe_path']),str(inputs['source_path']),str(audit),PYTHON,str(inputs['payload_path'])]]
            before=sorted(str(path) for path in root.rglob('*'))
            for args in vectors:
                with self.subTest(mode=args[0]):
                    result=subprocess.run([NODE,str(helper),*args],capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
                    self.assertNotEqual(result.returncode,0); self.assertIn(b'Exact admitted resource helper mode',result.stderr)
                    self.assertEqual(before,sorted(str(path) for path in root.rglob('*')))
                    self.assertFalse(output.exists()); self.assertFalse(audit.exists()); self.assertFalse((root/'fresh-root').exists())

    def test_admitted_recipe_contract_requires_seven_args_for_tiny_library_reconstruction(self):
        # Tiny library-only lossless data transformation; no admitted worker,
        # preparation recipe, source generation, or transport case is run.
        derived=fixture.templates((ROOT/fixture.CODE_FILES[0]).read_text())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); inputs=tiny_lossless_inputs(root)
            helper=root/'admitted-helper.js'; helper.write_bytes(derived['lossless-helper.js'])
            projection=root/'tiny-seven-arg-projection.json'; audit=root/'tiny-seven-arg-audit.json'
            base=[str(root),PYTHON,'tiny-no-network-fixture','0','tiny-archive-prefix']
            options={'fullPath':str(inputs['full_path']),'preparedPath':str(inputs['prepared_path']),
                'recipePath':str(inputs['recipe_path']),'projectionPath':str(projection),'recipeArguments':base}
            invoke='const helper=require(process.argv[1]); const options=JSON.parse(process.argv[2]); process.stdout.write(JSON.stringify(helper.project(options)));'
            result=subprocess.run([NODE,'-e',invoke,str(helper),tiny_json(options)],capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0); self.assertIn(b'recipe arguments required',result.stderr)
            self.assertFalse(projection.exists())
            options['recipeArguments']=[*base,str(root/'worker-admission.json'),'1'*64]
            result=subprocess.run([NODE,'-e',invoke,str(helper),tiny_json(options)],capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode()); self.assertEqual(json.loads(result.stdout)['status'],'PASSED')
            self.assertEqual(json.loads(projection.read_bytes())['regeneration']['recipe_arguments'],options['recipeArguments'])
            verify={'projectionPath':str(projection),'recipePath':str(inputs['recipe_path']),
                'retainedSourcePath':str(inputs['source_path']),'retainedPayloadPath':str(inputs['payload_path']),
                'auditPath':str(audit),'python':PYTHON}
            verify_invoke='const helper=require(process.argv[1]); process.stdout.write(JSON.stringify(helper.verifyProjection(JSON.parse(process.argv[2]))));'
            result=subprocess.run([NODE,'-e',verify_invoke,str(helper),tiny_json(verify)],capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            self.assertEqual(json.loads(result.stdout)['reconstructed_full_transcript']['sha256'],inputs['original_pin']['sha256'])
            bad=json.loads(projection.read_bytes()); bad['regeneration']['recipe_arguments']=base; write_tiny_json(projection,bad); audit.unlink()
            result=subprocess.run([NODE,'-e',verify_invoke,str(helper),tiny_json(verify)],capture_output=True,env=fixture.CHILD_ENVIRONMENT,timeout=10)
            self.assertNotEqual(result.returncode,0); self.assertIn(b'recipe identity arguments required',result.stderr)
            self.assertFalse(audit.exists())
            self.assertIn('recipeArguments.length === 5',fixture.LOSSLESS_HELPER)
            self.assertIn('regeneration.recipe_arguments.length === 5',fixture.LOSSLESS_HELPER)

    def test_tiny_source_domain_reader_rejects_other_ordinals_corruption_and_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for ordinal in range(8):
                domain=fixture.source_domain(ordinal)
                raw=b''.join(hashlib.sha256(domain+counter.to_bytes(8,'big')).digest() for counter in range(3))[:65]
                path=root/f'source{ordinal}'; path.write_bytes(raw)
                proof=fixture.verify_fresh_source_domain(path,ordinal,len(raw))
                self.assertEqual(proof['sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual(proof['source_domain_hex'],domain.hex())
                self.assertFalse(proof['native_case_binding_verified'])
                with self.assertRaisesRegex(ValueError,'counter domain'):
                    fixture.verify_fresh_source_domain(path,(ordinal+1)%8,len(raw))
                with self.assertRaisesRegex(ValueError,'source length'):
                    fixture.verify_fresh_source_domain(path,ordinal,len(raw)-1)
                path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
                with self.assertRaisesRegex(ValueError,'counter domain'):
                    fixture.verify_fresh_source_domain(path,ordinal,len(raw))
            linked=root/'linked'; linked.symlink_to(root/'source0')
            fifo=root/'fifo';os.mkfifo(fifo)
            for path in (linked,fifo):
                with self.assertRaises((OSError,ValueError)):
                    fixture.verify_fresh_source_domain(path,0,65)

    def test_prepared_and_terminal_identity_cannot_relabel_a_frozen_outer_case(self):
        # Shape-only metadata exercises identity semantics; no source file or
        # maximum payload is created by this test.
        ordinal=0; domain=fixture.source_domain(ordinal).hex(); source_hash='1'*64
        fixed={'ordinal':ordinal,'source_case_id':fixture.NAMESPACE+'/case00',
            'source_domain_hex':domain,'archive_prefix':fixture.PREFIX+'/case00-fixed','source_bytes':26*fixture.MIB}
        proof={'bytes':26*fixture.MIB,'sha256':source_hash,'source_domain_hex':domain,
            'case_ordinal':0,'native_case_binding_verified':False}
        identity={'namespace':fixture.NAMESPACE,'case_ordinal':0,'source_case_id':fixed['source_case_id'],
            'source_sha256':source_hash,'native_case_binding_verified':False}
        identity['engineering_case_binding_sha256']=hashlib.sha256(fixture.canonical(identity)).hexdigest()
        prepared={'control_case_identity':identity,'source_domain_hex':domain,'source_bytes':26*fixture.MIB,'source_sha256':source_hash}
        terminal={'kind':'terminal','status':'SINGLE_CASE_COMPONENT_ONLY','fixture_only':True,'control_case_identity':identity}
        self.assertEqual(fixture.audit_fresh_identity(prepared,fixed,proof,terminal),identity)
        changes=[('prepared',('source_sha256',),'2'*64),('prepared',('source_domain_hex',),fixture.source_domain(1).hex()),
            ('prepared',('control_case_identity','case_ordinal'),False),
            ('fixed',('archive_prefix',),fixture.PREFIX+'/case01-fixed'),
            ('fixed',('ordinal',),False),('proof',('case_ordinal',),False),
            ('proof',('source_domain_hex',),fixture.source_domain(1).hex()),
            ('terminal',('control_case_identity','source_case_id'),fixture.NAMESPACE+'/case01'),
            ('terminal',('control_case_identity','engineering_case_binding_sha256'),'3'*64),
            ('terminal',('fixture_only',),1)]
        for name,keys,value in changes:
            copies=json.loads(json.dumps({'prepared':prepared,'fixed':fixed,'proof':proof,'terminal':terminal}))
            target=copies[name]
            for key in keys[:-1]: target=target[key]
            target[keys[-1]]=value
            with self.subTest(change=(name,keys)),self.assertRaises(ValueError):
                fixture.audit_fresh_identity(copies['prepared'],copies['fixed'],copies['proof'],copies['terminal'])

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
            self.assertFalse(observation['wait4_maximum_includes_completely_reaped_descendants'])
            self.assertEqual(observation['tree_termination_coverage'],'NOT_INDEPENDENTLY_VERIFIED')
            self.assertTrue(observation['reported_identity_verified'])
            self.assertTrue(observation['direct_child_reaped'])
            self.assertFalse(observation['aggregate_concurrent_rss_measured'])
            self.assertGreaterEqual(data['grandchild_peak_bytes'],24*1024**2)
            self.assertGreaterEqual(observation['wait4_ru_maxrss_bytes'],data['grandchild_peak_bytes'])
            self.assertLess(observation['peak_rss_bytes'],data['own_peak_bytes']+data['grandchild_peak_bytes'])
            self.assertFalse(observation['raw_stdout_duplicate_written'])
            self.assertEqual((root/'small-nested-stdout.log').read_bytes(),b'')

    def test_missing_child_identity_closes_with_direct_reap_without_tree_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaisesRegex(RuntimeError,'identity was never verified'):
                fixture.observe_process([PYTHON,'-I','-S','-B','-c','pass'],root,'missing',root/'absent.json',
                    deadline=time.monotonic()+3,pipe_output=True)
            receipt=fixture.small_json(root/'missing-observation.json')
            self.assertEqual(receipt['exit_code'],0)
            self.assertTrue(receipt['direct_child_reaped'])
            self.assertFalse(receipt['reported_identity_verified'])
            self.assertFalse(receipt['complete_descendant_wait_chain_verified'])
            self.assertEqual(receipt['tree_termination_coverage'],'NOT_INDEPENDENTLY_VERIFIED')

    def test_sibling_procfs_pid_cannot_substitute_for_launched_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); sibling_identity=root/'sibling.json'
            sibling_source=('import os,json,sys,time; '
                'open(sys.argv[1],"x").write(json.dumps({"procfs_pid":int(os.readlink("/proc/self")),"namespace_pid":os.getpid()})); '
                'time.sleep(5)')
            sibling=subprocess.Popen([PYTHON,'-I','-S','-B','-c',sibling_source,str(sibling_identity)],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=fixture.CHILD_ENVIRONMENT)
            try:
                end=time.monotonic()+2
                while not sibling_identity.exists() and time.monotonic()<end: time.sleep(0.005)
                sibling_pin=fixture.small_json(sibling_identity)
                child_source=('import os,json,sys,time; '
                    'open(sys.argv[1],"x").write(json.dumps({"procfs_pid":int(sys.argv[2]),"namespace_pid":os.getpid()})); '
                    'time.sleep(0.1)')
                with self.assertRaisesRegex(RuntimeError,'differs from independently launched direct child'):
                    fixture.observe_process([PYTHON,'-I','-S','-B','-c',child_source,str(root/'forged.json'),str(sibling_pin['procfs_pid'])],
                        root,'forged',root/'forged.json',deadline=time.monotonic()+3,pipe_output=True)
                receipt=fixture.small_json(root/'forged-observation.json')
                self.assertNotEqual(receipt['bound_child_identity']['procfs_pid'],sibling_pin['procfs_pid'])
                self.assertFalse(receipt['reported_identity_verified'])
                self.assertIsNone(sibling.poll(),'A forged report must not target a sibling for termination')
            finally:
                sibling.terminate(); sibling.wait(timeout=3)

    def test_inherited_pipe_after_root_exit_is_bounded_by_original_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); child_identity=root/'pipe-identity.json'
            source=('import os,json,sys,time,subprocess; '
                'open(sys.argv[1],"x").write(json.dumps({"procfs_pid":int(os.readlink("/proc/self")),"namespace_pid":os.getpid()})); '
                'time.sleep(0.03); '
                'subprocess.Popen([sys.executable,"-I","-S","-B","-c","import time; time.sleep(5)"])')
            started=time.monotonic()
            with self.assertRaisesRegex(RuntimeError,'deadline exceeded'):
                fixture.observe_process([PYTHON,'-I','-S','-B','-c',source,str(child_identity)],root,'pipe-holder',child_identity,
                    deadline=started+0.35,pipe_output=True,new_session=True)
            self.assertLess(time.monotonic()-started,1.5)
            receipt=fixture.small_json(root/'pipe-holder-observation.json')
            self.assertEqual(receipt['exit_code'],0)
            self.assertTrue(receipt['reported_identity_verified'])
            self.assertFalse(receipt['complete_pipe_output'])
            self.assertFalse(receipt['complete_descendant_wait_chain_verified'])

    def test_oversized_output_is_not_retained_beyond_fixed_buffer_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); child_identity=root/'output-identity.json'
            source=('import os,json,sys,time; '
                'open(sys.argv[1],"x").write(json.dumps({"procfs_pid":int(os.readlink("/proc/self")),"namespace_pid":os.getpid()})); '
                'time.sleep(0.03); sys.stdout.write("x"*200000); sys.stdout.flush(); time.sleep(1)')
            with self.assertRaisesRegex(RuntimeError,'output cap exceeded'):
                fixture.observe_process([PYTHON,'-I','-S','-B','-c',source,str(child_identity)],root,'large-output',child_identity,
                    deadline=time.monotonic()+3,pipe_output=True,output_cap=16384)
            receipt=fixture.small_json(root/'large-output-observation.json')
            self.assertGreater(receipt['observed_output_bytes']['stdout'],16384)
            self.assertFalse(receipt['complete_pipe_output'])
            self.assertEqual((root/'large-output-stdout.log').stat().st_size,0)

    def test_sample_retention_stays_bounded_without_discarding_kernel_peak(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); child_identity=root/'sample-identity.json'
            source=('import os,json,sys,time; '
                'open(sys.argv[1],"x").write(json.dumps({"procfs_pid":int(os.readlink("/proc/self")),"namespace_pid":os.getpid()})); '
                'time.sleep(0.1)')
            with mock.patch.object(fixture,'OBSERVATION_SAMPLE_LIMIT',3):
                receipt,_,_=fixture.observe_process([PYTHON,'-I','-S','-B','-c',source,str(child_identity)],root,'samples',child_identity,
                    deadline=time.monotonic()+3,pipe_output=True)
            self.assertGreater(receipt['sample_count'],3)
            self.assertEqual(receipt['retained_sample_count'],3)
            self.assertEqual(len(receipt['samples']),3)
            self.assertGreaterEqual(receipt['peak_rss_bytes'],receipt['wait4_ru_maxrss_bytes'])

    def test_observer_registration_and_setup_failures_reap_child_and_close_every_pipe(self):
        real_popen=subprocess.Popen
        for failure in ('first-blocking-setup','second-selector-register','direct-child-map'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); captured=[]; selector=selectors.DefaultSelector()
                register=selector.register; calls=[]
                def capture(*args,**kwargs):
                    child=real_popen(*args,**kwargs); captured.append(child); return child
                def register_or_fail(*args,**kwargs):
                    calls.append(args[0])
                    if failure=='second-selector-register' and len(calls)==2:
                        raise RuntimeError('injected second registration failure')
                    return register(*args,**kwargs)
                with mock.patch.object(fixture.subprocess,'Popen',side_effect=capture), \
                        mock.patch.object(fixture.selectors,'DefaultSelector',return_value=selector), \
                        mock.patch.object(selector,'register',side_effect=register_or_fail):
                    stack=contextlib.ExitStack()
                    with stack:
                        if failure=='first-blocking-setup':
                            stack.enter_context(mock.patch.object(fixture.os,'set_blocking',side_effect=RuntimeError('injected blocking setup failure')))
                        elif failure=='direct-child-map':
                            stack.enter_context(mock.patch.object(fixture,'launched_child_identity',side_effect=RuntimeError('injected mapping setup failure')))
                        started=time.monotonic()
                        with self.assertRaisesRegex(RuntimeError,'Observer/child phase failed'):
                            fixture.observe_process([PYTHON,'-I','-S','-B','-c','import time; time.sleep(20)'],
                                root,failure,root/'unwritten-identity.json',deadline=started+5,pipe_output=True)
                        self.assertLess(time.monotonic()-started,2)
                self.assertEqual(len(captured),1)
                child=captured[0]
                self.assertIsNotNone(child.returncode)
                self.assertTrue(child.stdout.closed); self.assertTrue(child.stderr.closed)
                with self.assertRaises(ChildProcessError): os.waitpid(child.pid,os.WNOHANG)
                receipt=fixture.small_json(root/(failure+'-observation.json'))
                self.assertTrue(receipt['direct_child_reaped'])
                self.assertFalse(receipt['reported_identity_verified'])
                self.assertFalse(receipt['complete_pipe_output'])
                self.assertFalse(receipt['complete_descendant_wait_chain_verified'])
                self.assertIn('injected',receipt['reason'])
                if failure=='first-blocking-setup': self.assertEqual(calls,[])
                if failure=='second-selector-register': self.assertEqual(len(calls),2)

    def test_exact39_command_observation_count_cannot_hide_wrong_name(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); observations=root/'command-observations'; observations.mkdir()
            for number in range(38): write_tiny_json(observations/f'command-{number}-observation.json',{})
            write_tiny_json(observations/'command-38-observation.json',{})
            self.assertEqual(len(list(observations.glob('command-*-observation.json'))),39)
            with mock.patch.object(fixture,'pinned_component') as bootstrap:
                with self.assertRaisesRegex(ValueError,'Exact38 reader and one tail observation names'):
                    fixture.verified_command_observations(root,{},0)
                bootstrap.assert_not_called()


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
