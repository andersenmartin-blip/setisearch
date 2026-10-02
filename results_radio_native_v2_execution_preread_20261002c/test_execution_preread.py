#!/usr/bin/env python3
"""Focused metadata tests; temporary-root mocks do not prove public execution.

Real published preparation metadata are read only. Filesystem mutation tests
explicitly patch the builder's independent root/output anchors to private
TemporaryDirectory fixtures, so they never create a project c output, marker,
journal, launch configuration or scope. No production module is imported.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

BUILDER = Path(__file__).parent/'build_execution_preread.py'
spec = importlib.util.spec_from_file_location('isolated_c_preread_builder', BUILDER)
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)


class MetadataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = builder.ORIGINAL_ROOT
        cls.plan_raw = (Path(cls.root)/builder.PLAN_PATH).read_bytes()
        cls.freeze_raw = (Path(cls.root)/builder.FREEZE_PATH).read_bytes()
        cls.proof_raw = (Path(cls.root)/builder.PROOF_PATH).read_bytes()
        cls.plan = builder.strict_json(cls.plan_raw)
        cls.freeze = builder.strict_json(cls.freeze_raw)
        cls.proof = builder.strict_json(cls.proof_raw)

    def build(self, **changed):
        values = {'plan_raw': self.plan_raw, 'freeze_raw': self.freeze_raw,
            'proof_raw': self.proof_raw, 'root': self.root, 'expected_proof_pin': builder.PROOF_PIN}
        values.update(changed)
        return builder.build_preread(**values)

    def validate_plan(self, mutate):
        plan = copy.deepcopy(self.plan); mutate(plan)
        with self.assertRaises(ValueError): builder.validate_material(plan, self.freeze, root=self.root)

    def validate_freeze(self, mutate):
        freeze = copy.deepcopy(self.freeze); mutate(freeze)
        with self.assertRaises(ValueError): builder.validate_material(self.plan, freeze, root=self.root)

    def validate_proof(self, mutate):
        proof = copy.deepcopy(self.proof); mutate(proof)
        with self.assertRaises(ValueError): builder.validate_public_proof(proof)

    def test_positive_exact_25_fields_and_all_49_material_files(self):
        value = self.build()
        self.assertEqual(len(value), 25)
        self.assertEqual(value['code_files_verified'], builder.MATERIAL_FILES)
        self.assertEqual(len(value['code_files_verified']), 49)
        for key, wanted in builder.AUTHORITY.items():
            self.assertIs(type(value[key]), type(wanted)); self.assertEqual(value[key], wanted)

    def test_positive_canonical_digests_exclude_raw_newline(self):
        value = self.build()
        self.assertEqual(value['plan_sha256'], hashlib.sha256(builder.canonical(self.plan)).hexdigest())
        self.assertEqual(value['complete_freeze_sha256'], hashlib.sha256(builder.canonical(self.freeze)).hexdigest())
        self.assertNotEqual(value['plan_sha256'], builder.PLAN_PIN['sha256'])
        self.assertNotEqual(value['complete_freeze_sha256'], builder.FREEZE_PIN['sha256'])

    def test_output_material_mapping_is_detached(self):
        value = self.build(); value['code_files_verified'].clear()
        self.assertEqual(len(builder.MATERIAL_FILES), 49); self.assertEqual(len(self.build()['code_files_verified']), 49)

    def test_wrong_independent_root_refused_before_input_authentication(self):
        with self.assertRaisesRegex(ValueError, 'original repository root'):
            self.build(root='/tmp/candidate-root', expected_proof_pin=None)

    def test_changed_raw_plan_refused(self):
        with self.assertRaises(ValueError): self.build(plan_raw=self.plan_raw+b' ')

    def test_changed_raw_freeze_refused(self):
        with self.assertRaises(ValueError): self.build(freeze_raw=self.freeze_raw+b' ')

    def test_changed_raw_proof_refused(self):
        with self.assertRaises(ValueError): self.build(proof_raw=self.proof_raw+b' ')

    def test_independent_proof_digest_not_inferred_from_candidate(self):
        with self.assertRaises(ValueError): self.build(expected_proof_pin={**builder.PROOF_PIN, 'sha256': '0'*64})

    def test_independent_proof_bytes_not_inferred_from_candidate(self):
        with self.assertRaises(ValueError): self.build(expected_proof_pin={**builder.PROOF_PIN, 'bytes': builder.PROOF_PIN['bytes']+1})

    def test_boolean_proof_pin_size_refused(self):
        with self.assertRaises(ValueError): self.build(expected_proof_pin={**builder.PROOF_PIN, 'bytes': True})

    def test_plan_schema_namespace_and_mode_refused(self):
        for field in ('schema', 'namespace', 'mode', 'execution_status'):
            with self.subTest(field=field): self.validate_plan(lambda v, key=field: v.update({key:'altered'}))

    def test_plan_candidate_original_root_refused(self):
        self.validate_plan(lambda v: v.update(invocation_repository_root='/tmp/candidate'))

    def test_plan_original_b_journal_refused(self):
        self.validate_plan(lambda v: v.update(invocation_ledger_root=self.root+'/.radio-native-v2-invocation-ledger'))

    def test_material_mapping_missing_extra_and_changed_refused(self):
        first = next(iter(builder.MATERIAL_FILES))
        for mutate in (lambda v:v['code_files'].pop(first),
                lambda v:v['code_files'].update({'scripts/unreviewed.py':{'bytes':1,'sha256':'0'*64}}),
                lambda v:v['code_files'][first].update(sha256='0'*64)):
            with self.subTest(mutation=mutate): self.validate_plan(mutate)

    def test_missing_and_changed_historical_input_literals_refused(self):
        first = next(iter(builder.HISTORICAL_FILES))
        for mutate in (lambda v:v['historical_storage_inputs'].pop(first),
                lambda v:v['historical_storage_inputs'][first].update(sha256='0'*64)):
            with self.subTest(mutation=mutate): self.validate_plan(mutate)

    def test_historical_archive_wrong_freeze_route_refused(self):
        first = next(iter(builder.HISTORICAL_FILES))
        def wrong_route(freeze):
            freeze['code_sha256s'][first] = freeze['input_sha256s'].pop(first)
            freeze['repository_code_inventory'] = sorted(freeze['code_sha256s'])
            freeze['input_file_inventory'] = sorted(freeze['input_sha256s'])
        self.validate_freeze(wrong_route)

    def test_test_source_wrong_freeze_route_refused(self):
        first = next(path for path in builder.MATERIAL_FILES if path.startswith('tests/'))
        def wrong_route(freeze):
            freeze['code_sha256s'][first] = freeze['input_sha256s'].pop(first)
            freeze['repository_code_inventory'] = sorted(freeze['code_sha256s'])
            freeze['input_file_inventory'] = sorted(freeze['input_sha256s'])
        self.validate_freeze(wrong_route)

    def test_changed_freeze_mapping_and_inventory_refused(self):
        first = next(iter(builder.MATERIAL_FILES))
        self.validate_freeze(lambda v:v['code_sha256s'].update({first:'0'*64}))
        self.validate_freeze(lambda v:v['runtime_file_inventory'].append('/tmp/unreviewed'))

    def test_wrong_freeze_headers_refused(self):
        for field in ('schema', 'freeze_kind', 'namespace', 'mode'):
            with self.subTest(field=field): self.validate_freeze(lambda v,key=field:v.update({key:'altered'}))

    def test_plan_authority_boolean_integer_substitution_refused(self):
        for key, wanted in builder.AUTHORITY.items():
            with self.subTest(field=key): self.validate_plan(lambda v,k=key,w=wanted:v.update({k:0 if type(w) is bool else False}))

    def test_activation_lifetime_and_generation_flags_refused(self):
        for key in ('historical_storage_lifetime_qualified','one_invocation_spending_enforced',
                'complete_resource_measurement_join_qualified','activation_guard_complete',
                'large_source_generation_admitted','large_inputs_generated','spent_control_rearmed'):
            with self.subTest(field=key): self.validate_plan(lambda v,k=key:v.update({k:True}))

    def test_missing_required_preparation_flags_refused(self):
        for key in ('historical_storage_accounting_prepared','historical_storage_live_reobservation_required',
                'complete_runtime_freeze_required','public_immutable_preread_required'):
            with self.subTest(field=key): self.validate_plan(lambda v,k=key:v.pop(k))

    def test_freeze_authority_and_transport_refused(self):
        for key in ('execution_authorized','reservation_authorized','scientific_execution_authorized',
                'restart_authorized','rng_authorized','transport_integration_qualified'):
            with self.subTest(field=key): self.validate_freeze(lambda v,k=key:v.update({k:True}))
        self.validate_freeze(lambda v:v.update(transport_qualification={}))

    def test_original_blockers_and_limits_must_remain_exact(self):
        self.validate_plan(lambda v:v['execution_blockers'].pop())
        self.validate_plan(lambda v:v['execution_blockers'].reverse())
        self.validate_plan(lambda v:v['original_limits'].update(case_calls=65))
        self.validate_plan(lambda v:v['original_limits'].update(case_calls=64.0))

    def test_public_proof_wrong_commit_tree_parent_repository_refused(self):
        for key, value in (('commit','0'*40),('tree','0'*40),('parents',['0'*40]),
                ('repository','someone/else'),('branch','main'),('schema','unreviewed')):
            with self.subTest(field=key): self.validate_proof(lambda v,k=key,w=value:v.update({k:w}))

    def test_public_file_wrong_blob_digest_size_refused(self):
        for key, value in (('git_blob_sha','0'*40),('sha256','0'*64),('bytes',0),('bytes',False)):
            with self.subTest(field=key): self.validate_proof(lambda v,k=key,w=value:v['files'][0].update({k:w}))

    def test_public_file_missing_duplicate_unsorted_and_extra_refused(self):
        mutations = (lambda v:v['files'].pop(), lambda v:v['files'].__setitem__(1,v['files'][0]),
            lambda v:v['files'].reverse(), lambda v:v['files'][0].update(path='scripts/unreviewed.py'))
        for mutate in mutations:
            with self.subTest(mutation=mutate): self.validate_proof(mutate)

    def test_public_joins_boolean_claims_and_extra_fields_refused(self):
        for key, value in (('all_material_files_verified',False),('all_content_and_git_blob_readbacks_match',1),
                ('file_count',170),('raw_bytes',1),('material_file_count',48),
                ('execution_authorized',0),('whole_control_qualified',True),('telescope_reads',False)):
            with self.subTest(field=key): self.validate_proof(lambda v,k=key,w=value:v.update({k:w}))
        self.validate_proof(lambda v:v.update(extra_authority=True))
        self.validate_proof(lambda v:v['files'][0].update(content_matches=1))
        self.validate_proof(lambda v:v['files'][0].update(git_blob_matches=False))

    def test_strict_json_duplicate_keys_refused(self):
        with self.assertRaises(ValueError): builder.strict_json(b'{"schema":"first","schema":"second"}\n')

    def test_strict_json_nonfinite_constants_and_overflow_refused(self):
        for raw in (b'{"value":NaN}\n',b'{"value":Infinity}\n',b'{"value":-Infinity}\n',b'{"value":1e309}\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): builder.strict_json(raw)

    def test_strict_json_noncanonical_newline_utf8_and_top_level_refused(self):
        for raw in (b'{ "value":1}\n',b'{"value":1}',b'{"value":1}\n\n',
                b'{"z":1,"a":2}\n',b'[]\n',b'{"value":"\xff"}\n'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): builder.strict_json(raw)


class SecureFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='seti-c-preread-test-')
        self.root = Path(self.temp.name)
        self.root_patch = mock.patch.object(builder,'ORIGINAL_ROOT',str(self.root));self.root_patch.start()
        self.addCleanup(self.root_patch.stop);self.addCleanup(self.temp.cleanup)
        (self.root/'config').mkdir();(self.root/'evidence').mkdir()

    def put(self, relative, raw=b'{"value":1}\n'):
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        return path,builder.raw_pin(raw)

    def test_descriptor_reader_round_trip_and_wrong_pin(self):
        _,pin=self.put('evidence/input.json')
        self.assertEqual(builder.read_pinned(str(self.root),'evidence/input.json',pin),b'{"value":1}\n')
        with self.assertRaises(ValueError):builder.read_pinned(str(self.root),'evidence/input.json',{**pin,'sha256':'0'*64})

    def test_reader_refuses_symlink_leaf(self):
        target,pin=self.put('evidence/target.json');(self.root/'evidence/link.json').symlink_to(target)
        with self.assertRaises((OSError,ValueError)):builder.read_pinned(str(self.root),'evidence/link.json',pin)

    def test_reader_refuses_symlink_ancestor(self):
        _,pin=self.put('evidence/input.json');(self.root/'alias').symlink_to(self.root/'evidence',target_is_directory=True)
        with self.assertRaises((OSError,ValueError)):builder.read_pinned(str(self.root),'alias/input.json',pin)

    def test_reader_refuses_hardlink_and_path_traversal(self):
        target,pin=self.put('evidence/input.json');os.link(target,self.root/'evidence/linked.json')
        with self.assertRaises(ValueError):builder.read_pinned(str(self.root),'evidence/input.json',pin)
        with self.assertRaises(ValueError):builder.read_pinned(str(self.root),'evidence/../evidence/input.json',pin)

    def test_exclusive_output_preserves_existing_file(self):
        raw=b'{"value":1}\n';builder.write_exclusive(str(self.root),builder.OUTPUT_PATH,raw)
        with self.assertRaises(FileExistsError):builder.write_exclusive(str(self.root),builder.OUTPUT_PATH,b'{"value":2}\n')
        self.assertEqual((self.root/builder.OUTPUT_PATH).read_bytes(),raw)

    def test_writer_only_allows_fixed_output_and_receipt(self):
        with self.assertRaises(ValueError):builder.write_exclusive(str(self.root),'config/unreviewed.json',b'{"value":1}\n')
        self.assertFalse((self.root/'config/unreviewed.json').exists())

    def test_output_file_and_directory_are_fsynced(self):
        calls=[];actual=os.fsync
        with mock.patch.object(builder.os,'fsync',side_effect=lambda fd:(calls.append(os.fstat(fd).st_mode),actual(fd))[1]):
            builder.write_exclusive(str(self.root),builder.OUTPUT_PATH,b'{"value":1}\n')
        import stat
        self.assertTrue(any(stat.S_ISREG(mode) for mode in calls));self.assertTrue(any(stat.S_ISDIR(mode) for mode in calls))

    def test_fsync_failure_retains_output_without_rearming(self):
        with mock.patch.object(builder.os,'fsync',side_effect=OSError('injected fsync failure')):
            with self.assertRaises(OSError):builder.write_exclusive(str(self.root),builder.OUTPUT_PATH,b'{"value":1}\n')
        self.assertTrue((self.root/builder.OUTPUT_PATH).exists())
        with self.assertRaises(FileExistsError):builder.write_exclusive(str(self.root),builder.OUTPUT_PATH,b'{"value":1}\n')

    def test_writer_refuses_same_bytes_named_swap_during_file_fsync(self):
        raw=b'{"value":1}\n';actual=builder.os.fsync;changed=False
        def syncing(fd):
            nonlocal changed
            actual(fd)
            if not changed:
                changed=True;replacement=self.root/'config/replacement.json'
                replacement.write_bytes(raw);os.replace(replacement,self.root/builder.OUTPUT_PATH)
        with mock.patch.object(builder.os,'fsync',side_effect=syncing):
            with self.assertRaises(ValueError):builder.write_exclusive(str(self.root),builder.OUTPUT_PATH,raw)

    def test_writer_refuses_output_mutation_during_directory_fsync(self):
        raw=b'{"value":1}\n';actual=builder.os.fsync;calls=0
        def syncing(fd):
            nonlocal calls
            calls+=1;actual(fd)
            if calls==2:(self.root/builder.OUTPUT_PATH).write_bytes(b'{"value":2}\n')
        with mock.patch.object(builder.os,'fsync',side_effect=syncing):
            with self.assertRaises(ValueError):builder.write_exclusive(str(self.root),builder.OUTPUT_PATH,raw)

    def test_protected_c_marker_journal_scope_launch_absence_enforced(self):
        builder.require_protected_absent(str(self.root))
        for relative in builder.PROTECTED_ABSENT:
            with self.subTest(relative=relative):
                path=self.root/relative;path.write_bytes(b'fixture')
                with self.assertRaises(ValueError):builder.require_protected_absent(str(self.root))
                path.unlink()
        builder.require_protected_absent(str(self.root))

    def test_protected_marker_symlink_refused(self):
        path=self.root/builder.PROTECTED_ABSENT[1];path.symlink_to('/does/not/exist')
        with self.assertRaises(ValueError):builder.require_protected_absent(str(self.root))

    def test_secure_reader_detects_mid_read_file_change(self):
        path,pin=self.put('evidence/input.json');actual=builder.os.read;changed=False
        def reading(fd,count):
            nonlocal changed
            raw=actual(fd,count)
            if raw and not changed:
                changed=True;path.write_bytes(b'{"value":2}\n')
            return raw
        with mock.patch.object(builder.os,'read',side_effect=reading):
            with self.assertRaises(ValueError):builder.read_pinned(str(self.root),'evidence/input.json',pin)

    def test_postwrite_named_output_replacement_refused_before_receipt(self):
        # Patch only input/pure-build anchors to isolate the real output writer
        # and descriptor reader. This fixture grants no project/public authority.
        receipt_parent=self.root/Path(builder.RECEIPT_PATH).parent;receipt_parent.mkdir(parents=True)
        actual_read=builder.read_pinned;actual_write=builder.write_exclusive
        value={'schema':builder.PREREAD_SCHEMA,'value':'held fixture'}
        def reading(root,relative,expected):
            if relative==builder.OUTPUT_PATH:return actual_read(root,relative,expected)
            return b'{"fixture":true}\n'
        def writing(root,relative,raw):
            actual_write(root,relative,raw)
            if relative==builder.OUTPUT_PATH:
                target=self.root/relative;replacement=self.root/'config/replacement.json'
                replacement.write_bytes(b'{"replaced":true}\n');os.replace(replacement,target)
        with mock.patch.object(builder,'read_pinned',side_effect=reading), \
                mock.patch.object(builder,'build_preread',return_value=value), \
                mock.patch.object(builder,'write_exclusive',side_effect=writing):
            with self.assertRaises(ValueError):builder.run('build',root=str(self.root),expected_proof_pin=builder.PROOF_PIN)
        self.assertTrue((self.root/builder.OUTPUT_PATH).exists())
        self.assertFalse((self.root/builder.RECEIPT_PATH).exists())

    def test_late_named_output_change_refused_before_receipt(self):
        receipt_parent=self.root/Path(builder.RECEIPT_PATH).parent;receipt_parent.mkdir(parents=True)
        actual_read=builder.read_pinned;proof_reads=0
        value={'schema':builder.PREREAD_SCHEMA,'value':'held fixture'}
        def reading(root,relative,expected):
            nonlocal proof_reads
            if relative==builder.OUTPUT_PATH:return actual_read(root,relative,expected)
            if relative==builder.PROOF_PATH:
                proof_reads+=1
                if proof_reads==2:(self.root/builder.OUTPUT_PATH).write_bytes(b'{"replaced":true}\n')
            return b'{"fixture":true}\n'
        with mock.patch.object(builder,'read_pinned',side_effect=reading), \
                mock.patch.object(builder,'build_preread',return_value=value):
            with self.assertRaises(ValueError):builder.run('build',root=str(self.root),expected_proof_pin=builder.PROOF_PIN)
        self.assertFalse((self.root/builder.RECEIPT_PATH).exists())


if __name__ == '__main__':unittest.main(verbosity=2)
