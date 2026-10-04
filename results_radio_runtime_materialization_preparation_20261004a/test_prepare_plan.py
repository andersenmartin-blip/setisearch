"""Only bounded retained metadata and tiny filesystem negatives; no live work."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('inert_runtime_plan', ROOT / 'prepare_plan.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
PINS_RAW = (ROOT / 'authoritative-input-pins.json').read_bytes()
PINS = json.loads(PINS_RAW)
RAW = {name: (ROOT / 'inputs' / row['snapshot_path']).read_bytes() for name, row in PINS['inputs'].items()}


class PreparationTests(unittest.TestCase):
    def plan(self, inputs=None, pins=PINS_RAW, expected=builder.TRUSTED_PINMAP_SHA256):
        return builder.build_plan(RAW if inputs is None else inputs, pins, expected)

    def test_exact_plan_is_inert_and_deterministic(self):
        first = self.plan()
        self.assertEqual(builder.canonical(first), builder.canonical(self.plan()))
        self.assertEqual(first['status'], 'PENDING')
        self.assertEqual(first['source']['primary'], 'neighbor9')
        self.assertEqual(first['source']['cadence_id'], 85030)
        self.assertTrue(all(value is False for value in first['authority'].values()))
        self.assertTrue(all(value == 0 for value in first['operations_here'].values()))
        self.assertEqual(first['materialization']['wheel_file_bytes'], 68409067)
        self.assertEqual(len(first['remaining_authentic_receipt_requirements']['normalization_receiver_handoffs']), 12)
        self.assertEqual(len(first['remaining_authentic_receipt_requirements']['all_eleven_fields_still_pending']), 11)

    def test_build_uses_no_files_network_process_or_native_import(self):
        before = {name for name in sys.modules if name.startswith(('h5py', 'hdf5plugin', 'seti_repeater'))}
        with (mock.patch('builtins.open', side_effect=AssertionError('pure builder opened a file')),
             mock.patch('os.open', side_effect=AssertionError('pure builder opened a descriptor')),
             mock.patch('builtins.__import__', side_effect=AssertionError('pure builder imported a module'))):
            self.assertEqual(self.plan()['status'], 'PENDING')
        after = {name for name in sys.modules if name.startswith(('h5py', 'hdf5plugin', 'seti_repeater'))}
        self.assertEqual(before, after)

    def test_every_mutated_input_is_refused(self):
        for name in RAW:
            with self.subTest(name=name):
                changed = dict(RAW, **{name: RAW[name] + b' '})
                with self.assertRaises(ValueError):
                    self.plan(changed)

    def test_every_missing_input_and_unknown_extra_is_refused(self):
        for name in RAW:
            with self.subTest(name=name):
                changed = dict(RAW)
                changed.pop(name)
                with self.assertRaises(ValueError):
                    self.plan(changed)
        with self.assertRaises(ValueError):
            self.plan(dict(RAW, extra=b'{}'))

    def test_wrong_independent_outer_pin_is_refused(self):
        with self.assertRaises(ValueError):
            self.plan(expected='0' * 64)

    def test_repinning_a_changed_authoritative_map_cannot_promote_it(self):
        changed = copy.deepcopy(PINS)
        changed['remote_origin_authenticated_here'] = True
        raw = builder.canonical(changed)
        with self.assertRaises(ValueError):
            self.plan(pins=raw, expected=hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            self.plan(pins=raw)

    def test_repinning_changed_source_input_is_refused(self):
        source = json.loads(RAW['source_metadata'])
        source['cadence_id'] = 73005
        raw = builder.canonical(source)
        inputs = dict(RAW, source_metadata=raw)
        pins = copy.deepcopy(PINS)
        pins['inputs']['source_metadata'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        pins_raw = builder.canonical(pins)
        with self.assertRaises(ValueError):
            self.plan(inputs, pins=pins_raw, expected=hashlib.sha256(pins_raw).hexdigest())

    def test_wheel_provenance_identity_mutations_refused_semantically(self):
        provenance = json.loads(RAW['wheel_provenance'])
        mutations = {'url': 'https://example.invalid/other.whl', 'bytes': 1, 'sha256': '0' * 64,
            'filename': 'other.whl', 'version': '9.0.0', 'matching_tags': ['cp313-cp313-linux_aarch64'], 'yanked': True}
        for ordinal in range(3):
            for field, value in mutations.items():
                with self.subTest(wheel=ordinal, field=field):
                    changed = copy.deepcopy(provenance)
                    changed['official_package_wheels'][ordinal][field] = value
                    with self.assertRaises(ValueError):
                        builder.wheel_plan(changed, RAW)

    def test_official_metadata_repin_does_not_hide_wrong_wheel(self):
        provenance = json.loads(RAW['wheel_provenance'])
        metadata = json.loads(RAW['numpy_metadata'])
        entry = next(item for item in metadata['urls'] if item['filename'] == builder.WHEELS[0]['filename'])
        entry['digests']['sha256'] = '0' * 64
        raw = builder.canonical(metadata)
        provenance['official_package_wheels'][0]['metadata_pin'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        with self.assertRaises(ValueError):
            builder.wheel_plan(provenance, dict(RAW, numpy_metadata=raw))

    def test_official_selected_metadata_duplicate_and_missing_refused(self):
        provenance = json.loads(RAW['wheel_provenance'])
        for mode in ('missing', 'duplicate'):
            with self.subTest(mode=mode):
                metadata = json.loads(RAW['numpy_metadata'])
                selected = next(item for item in metadata['urls'] if item['filename'] == builder.WHEELS[0]['filename'])
                metadata['urls'] = ([entry for entry in metadata['urls'] if entry != selected] if mode == 'missing'
                                    else metadata['urls'] + [copy.deepcopy(selected)])
                raw = builder.canonical(metadata)
                changed = copy.deepcopy(provenance)
                changed['official_package_wheels'][0]['metadata_pin'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                with self.assertRaises(ValueError):
                    builder.wheel_plan(changed, dict(RAW, numpy_metadata=raw))

    def test_wrong_hash_lock_and_package_order_refused(self):
        provenance = json.loads(RAW['wheel_provenance'])
        with self.assertRaises(ValueError):
            builder.wheel_plan(provenance, dict(RAW, wheel_lock=b'numpy==2.3.5\n'))
        provenance['official_package_wheels'].reverse()
        with self.assertRaises(ValueError):
            builder.wheel_plan(provenance, RAW)

    def test_historical_runtime_never_claimed_fresh(self):
        plan = self.plan()
        self.assertFalse(plan['availability']['current_live_runtime_verified'])
        self.assertTrue(plan['availability']['observation_is_ephemeral_not_a_runtime_certificate'])
        self.assertEqual(plan['availability']['status'], 'ABSENT_AT_RECORDED_EXACT_PATH_OBSERVATION')
        self.assertIsNone(plan['materialization']['fresh_host_python_executable_sha256'])
        self.assertIsNone(plan['materialization']['fresh_host_image_identity'])
        self.assertTrue(plan['materialization']['historical_python_pin_cannot_authenticate_new_host'])

    def test_bootstrap_resources_unallocated_not_scientific_budget(self):
        resources = self.plan()['materialization']['bootstrap_resources']
        self.assertEqual(resources['status'], 'UNALLOCATED_UNMEASURED')
        self.assertTrue(resources['separate_finite_prospective_allocation_required_before_execution'])
        self.assertTrue(resources['does_not_fit_or_borrow_scientific_40s_4MiB_or_80s_18MiB_budgets'])
        self.assertIsNone(resources['installed_bytes'])

    def test_editing_returned_plan_does_not_mutate_later_fixed_scope(self):
        baseline = builder.canonical(self.plan())
        changed = self.plan()
        changed['materialization']['required_historical_versions']['python'] = '9.0.0'
        changed['materialization']['official_wheels'][0]['tags'].append('unsupported-tag')
        changed['authority']['scientific_execution_authorized'] = True
        self.assertEqual(builder.canonical(self.plan()), baseline)

    def test_existing_interface_symbols_required_without_execution(self):
        self.assertFalse(self.plan()['future_metadata_capture']['capture_to_existing_freeze_interface']['replaces_existing_verifier'])
        with self.assertRaises(ValueError):
            builder.interface_binding(b'VALUE=True\n', ('ScientificFreeze',), 'synthetic')
        with self.assertRaises(ValueError):
            builder.interface_binding(b'def broken(\n', ('ScientificFreeze',), 'synthetic')

    def test_duplicate_nonfinite_and_oversized_metadata_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b' ' * (builder.MAX_INPUT + 1)):
            with self.subTest(raw_prefix=raw[:16]):
                with self.assertRaises(ValueError):
                    builder.parse(raw)

    def test_local_snapshot_reader_refuses_symlink_hardlink_directory_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / 'input'
            file.write_bytes(b'{}')
            self.assertEqual(builder.safe_read(file), b'{}')
            link = root / 'link'
            link.symlink_to(file)
            with self.assertRaises(ValueError):
                builder.safe_read(link)
            with self.assertRaises(ValueError):
                builder.safe_read(root)
            hard = root / 'hard'
            os.link(file, hard)
            with self.assertRaises(ValueError):
                builder.safe_read(file)
            hard.unlink()
            file.write_bytes(b'x' * (builder.MAX_INPUT + 1))
            with self.assertRaises(ValueError):
                builder.safe_read(file)

    def test_exclusive_output_refuses_reuse_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            raw = builder.canonical(self.plan())
            builder.write_exclusive(path, raw)
            self.assertEqual(path.read_bytes(), raw)
            with self.assertRaises(FileExistsError):
                builder.write_exclusive(path, raw)
            with self.assertRaises(ValueError):
                builder.write_exclusive(Path(directory) / '..' / 'escape.json', raw)
            with self.assertRaises(ValueError):
                builder.safe_read('relative.json')

    def test_replaced_named_snapshot_refused_and_descriptor_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input'
            path.write_bytes(b'{}')
            original = os.fstat
            observed = []
            def replaced(descriptor):
                value = original(descriptor)
                observed.append(descriptor)
                if len(observed) == 2:
                    path.unlink()
                    path.write_bytes(b'{}')
                return value
            with mock.patch.object(builder.os, 'fstat', side_effect=replaced):
                with self.assertRaisesRegex(ValueError, 'Named snapshot identity changed'):
                    builder.safe_read(path)
            with self.assertRaises(OSError):
                original(observed[0])


if __name__ == '__main__':
    unittest.main()
