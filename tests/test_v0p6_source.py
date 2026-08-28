"""Known-answer and adversarial tests for the M37 source boundary."""

from __future__ import annotations

from dataclasses import replace
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from seti_repeater.dedoppler import robust_block_normalize
from seti_repeater.search_v0p6 import (
    V0P6CapacityError,
    V0P6ContractError,
    V0P6IncompleteError,
)
import seti_repeater.source_v0p6 as source


ROOT = Path(__file__).resolve().parents[1]


def immutable_copy(values: np.ndarray, dtype: str) -> np.ndarray:
    array = np.ascontiguousarray(values, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=dtype).reshape(array.shape)


class V0P6NormalizationKnownAnswerTests(unittest.TestCase):
    def test_native_order_extractor_adapter_hash_and_pre_network_gate(self):
        adapter_path = ROOT / "scripts" / "m37_v0p6_hdf5_extract.py"
        self.assertEqual(
            hashlib.sha256(adapter_path.read_bytes()).hexdigest(),
            source.M37_HDF5_EXTRACTOR_SOURCE_SHA256,
        )
        spec = importlib.util.spec_from_file_location(
            "m37_v0p6_hdf5_extract_test", adapter_path
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(
            module,
            "_remote_identity",
            side_effect=AssertionError("unauthorized path made a remote request"),
        ):
            iterator = module.iter_m37_normalized_scan_products(
                source._M37_SCAN_SOURCES,
                scan_label="epoch1_on",
                spectral_access_authorized=False,
            )
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                next(iterator)
        with (
            patch.object(
                module.source,
                "M37_HDF5_EXTRACTOR_SOURCE_SHA256",
                "0" * 64,
            ),
            patch.object(
                module,
                "_remote_identity",
                side_effect=AssertionError(
                    "source-hash mismatch made a remote request"
                ),
            ),
        ):
            iterator = module.iter_m37_normalized_scan_products(
                source._M37_SCAN_SOURCES,
                scan_label="epoch1_on",
                spectral_access_authorized=True,
            )
            with self.assertRaisesRegex(V0P6ContractError, "extractor source"):
                next(iterator)

    def test_float32_even_median_mad_known_answer_and_v05_equivalence(self):
        values = np.array(
            [
                [9, 1, 7, 3, 5, 11, 13, 15],
                [2, 2, 2, 6, 10, 14, 18, 22],
            ],
            dtype=np.float32,
        )
        normalized = source.normalize_float32_blocks_v0p6(values)
        self.assertEqual(
            hashlib.sha256(normalized.astype("<f4").tobytes()).hexdigest(),
            "27fecbfb7be90e9a79f096622a8b11b66bb9a8d9400a89550e76de99ef52fdfc",
        )
        np.testing.assert_array_equal(
            normalized, robust_block_normalize(values, block=4096)
        )
        self.assertEqual(normalized.dtype, np.dtype("<f4"))
        self.assertTrue(normalized.flags.c_contiguous)

    def test_global_block_origin_terminal_block_and_input_chunklessness(self):
        values = (
            np.arange(2 * 4101, dtype=np.float32).reshape(2, 4101) % 37
        ) - np.float32(18.0)
        joined_from_irregular_chunks = np.ascontiguousarray(
            np.concatenate(
                (
                    values[:, :17],
                    values[:, 17:2049],
                    values[:, 2049:4096],
                    values[:, 4096:],
                ),
                axis=1,
            ),
            dtype="<f4",
        )
        first = source.normalize_float32_blocks_v0p6(values)
        second = source.normalize_float32_blocks_v0p6(
            joined_from_irregular_chunks
        )
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(
            first, robust_block_normalize(values, block=4096)
        )
        self.assertEqual(
            hashlib.sha256(first.astype("<f4").tobytes()).hexdigest(),
            "bdc4dd47fcc142644b7c1a3ff23e4d4ba38ae08e4323db6ce13e33c8658a3542",
        )
        # A single-channel terminal block has center=value, MAD=0, and a
        # float32-tiny scale, so its normalized value is exactly zero.
        one = source.normalize_float32_blocks_v0p6(
            np.array([[7.0]], dtype=np.float32)
        )
        self.assertEqual(one[0, 0].view(np.uint32), 0)

    def test_descending_raw_is_reversed_before_4096_block_partition(self):
        ascending = (
            np.arange(4101, dtype=np.float32)[None, :] % 41
        ) - np.float32(20.0)
        descending = np.ascontiguousarray(ascending[:, ::-1], dtype="<f4")
        canonical_from_descending = np.ascontiguousarray(
            descending[:, ::-1], dtype="<f4"
        )
        expected = source.normalize_float32_blocks_v0p6(ascending)
        actual = source.normalize_float32_blocks_v0p6(
            canonical_from_descending
        )
        np.testing.assert_array_equal(actual, expected)
        forbidden = source.normalize_float32_blocks_v0p6(descending)[:, ::-1]
        self.assertFalse(np.array_equal(forbidden, expected))

    def test_engine_identity_binds_contract_source_and_runtime(self):
        self.assertEqual(
            len(source.M37_NORMALIZATION_IMPLEMENTATION_SHA256), 64
        )
        payload = {
            **source._runtime_identity_payload(
                source.M37_NORMALIZATION_CONTRACT_SHA256
            ),
            "normalization_implementation_sha256": (
                source.M37_NORMALIZATION_IMPLEMENTATION_SHA256
            ),
        }
        self.assertEqual(
            hashlib.sha256(
                source.core.canonical_json_bytes(payload)
            ).hexdigest(),
            source.M37_NORMALIZATION_ENGINE_IDENTITY_SHA256,
        )
        extraction_payload = {
            **source._runtime_identity_payload(
                source.M37_EXTRACTION_CONTRACT_SHA256
            ),
            "frozen_extractor_source_sha256": (
                source.M37_HDF5_EXTRACTOR_SOURCE_SHA256
            ),
            "extraction_factory_implementation_sha256": (
                source.M37_EXTRACTION_FACTORY_IMPLEMENTATION_SHA256
            ),
        }
        self.assertEqual(
            hashlib.sha256(
                source.core.canonical_json_bytes(extraction_payload)
            ).hexdigest(),
            source.M37_EXTRACTION_ENGINE_IDENTITY_SHA256,
        )


class V0P6M37SourceProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = json.loads(
            (ROOT / "config" / "hd156668b_m37_preflight.json").read_text()
        )
        cls.scans = cls.config["scans"]
        cls.scan = cls.scans[0]
        cls.window_id = "m37_1400p5"
        cls.start, cls.stop = source._M37_EXTRACTION_INTERVALS[cls.window_id]
        header = cls.scan["expected_header"]
        cls.original_frequency = np.ascontiguousarray(
            float(header["fch1_mhz"])
            + np.arange(cls.start, cls.stop, dtype=np.float64)
            * float(header["foff_mhz"]),
            dtype="<f8",
        )
        count = cls.stop - cls.start
        pattern = (np.arange(count, dtype=np.uint32) % 251).astype(np.float32)
        raw = np.empty((16, count), dtype=np.float32)
        for row in range(16):
            raw[row] = pattern + np.float32(row * 0.125)
        del pattern
        cls.extracted = source.attest_m37_extracted_scan(
            raw,
            cls.original_frequency,
            cls.scans,
            window_id=cls.window_id,
            scan_label=cls.scan["label"],
            observed_url=cls.scan["url"],
            observed_remote_size_bytes=cls.scan[
                "expected_remote_size_bytes"
            ],
            observed_etag=cls.scan["expected_etag"],
            observed_header=header,
            channel_start=cls.start,
            channel_stop=cls.stop,
        )
        del raw
        cls.product = source.normalize_m37_extracted_scan(cls.extracted)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.extracted = None
        cls.product = None
        cls.original_frequency = None
        gc.collect()

    def extraction_kwargs(self) -> dict[str, object]:
        return {
            "window_id": self.window_id,
            "scan_label": self.scan["label"],
            "observed_url": self.scan["url"],
            "observed_remote_size_bytes": self.scan[
                "expected_remote_size_bytes"
            ],
            "observed_etag": self.scan["expected_etag"],
            "observed_header": self.scan["expected_header"],
            "channel_start": self.start,
            "channel_stop": self.stop,
        }

    def test_exact_source_inventory_and_normative_geometry_are_bound(self):
        source.validate_m37_source_scan_definitions(self.scans)
        source._validate_internal_geometry_inventory()
        self.assertEqual(
            self.product.source_scan_definitions_sha256,
            source.M37_SOURCE_SCAN_DEFINITIONS_SHA256,
        )
        self.assertEqual(
            self.product.extraction_geometry_inventory_sha256,
            source.M37_EXTRACTION_GEOMETRY_INVENTORY_SHA256,
        )
        self.assertEqual(
            self.product.bank_preflight_result_sha256,
            source.M37_BANK_PREFLIGHT_RESULT_SHA256,
        )
        self.assertEqual(self.product.scan_inventory_sha256, source.core.M37_SCAN_INVENTORY_SHA256)
        self.assertEqual(self.product.geometry.channel_count, self.stop - self.start)

    def test_factory_derives_canonical_ascending_axis_and_normalizes_inside(self):
        product = source.validate_m37_normalized_scan_product(self.product)
        self.assertLess(product.frequency_mhz[0], product.frequency_mhz[-1])
        np.testing.assert_array_equal(
            product.frequency_mhz, self.original_frequency[::-1]
        )
        self.assertEqual(
            product.original_frequency_mhz_sha256,
            hashlib.sha256(self.original_frequency.tobytes()).hexdigest(),
        )
        self.assertEqual(
            product.original_raw_values_sha256,
            source._reversed_raw_sha256(product.raw_values),
        )
        self.assertFalse(product.raw_values.flags.writeable)
        self.assertFalse(product.frequency_mhz.flags.writeable)
        self.assertFalse(product.normalized_values.flags.writeable)
        self.assertLess(
            product.raw_values_nbytes
            + product.frequency_mhz_nbytes
            + product.normalized_values_nbytes,
            source.M37_MAXIMUM_NORMALIZED_PRODUCT_ARRAY_NBYTES,
        )

    def test_wrong_source_identity_header_roles_and_geometry_fail_before_seal(self):
        raw = self.product.raw_values
        frequency = self.original_frequency
        cases: list[tuple[str, dict[str, object], object]] = []
        for label, changed in (
            ("url", {"observed_url": self.scan["url"] + ".changed"}),
            (
                "size",
                {
                    "observed_remote_size_bytes": self.scan[
                        "expected_remote_size_bytes"
                    ]
                    + 1
                },
            ),
            ("etag", {"observed_etag": '"changed"'}),
            ("start", {"channel_start": self.start + 1}),
            ("stop", {"channel_stop": self.stop - 1}),
            ("window", {"window_id": "m37_1406p5"}),
            ("label", {"scan_label": "epoch1_off"}),
        ):
            kwargs = self.extraction_kwargs()
            kwargs.update(changed)
            cases.append((label, kwargs, self.scans))
        changed_header = json.loads(json.dumps(self.scan["expected_header"]))
        changed_header["tstart_mjd"] += 1e-6
        header_kwargs = self.extraction_kwargs()
        header_kwargs["observed_header"] = changed_header
        cases.append(("header", header_kwargs, self.scans))
        changed_scans = json.loads(json.dumps(self.scans))
        changed_scans[0]["kind"] = "off"
        cases.append(("kind", self.extraction_kwargs(), changed_scans))
        for label, kwargs, scans in cases:
            with self.subTest(label=label):
                with self.assertRaises(V0P6ContractError):
                    source.attest_m37_extracted_scan(
                        raw, frequency, scans, **kwargs
                    )

    def test_frequency_is_only_an_exact_header_derived_witness(self):
        wrong_value = self.original_frequency.copy()
        wrong_value[0] = np.nextafter(wrong_value[0], np.inf)
        with self.assertRaisesRegex(V0P6ContractError, "frequency witness"):
            source.attest_m37_extracted_scan(
                self.product.raw_values,
                wrong_value,
                self.scans,
                **self.extraction_kwargs(),
            )
        # The canonical ascending axis is also rejected as an extraction-axis
        # witness: raw HDF5 bytes must be presented in native descending order.
        with self.assertRaisesRegex(V0P6ContractError, "frequency witness"):
            source.attest_m37_extracted_scan(
                self.product.raw_values,
                self.product.frequency_mhz,
                self.scans,
                **self.extraction_kwargs(),
            )

    def test_raw_frequency_and_normalized_substitution_fail_closed(self):
        changed_raw = self.product.raw_values.copy()
        changed_raw[0, 0] = np.nextafter(changed_raw[0, 0], np.inf)
        changed_raw = immutable_copy(changed_raw, "<f4")
        with self.assertRaises(V0P6IncompleteError):
            source.validate_m37_normalized_scan_product(
                replace(self.product, raw_values=changed_raw)
            )
        del changed_raw

        changed_frequency = self.product.frequency_mhz.copy()
        changed_frequency[0] = np.nextafter(changed_frequency[0], np.inf)
        changed_frequency = immutable_copy(changed_frequency, "<f8")
        with self.assertRaises(V0P6IncompleteError):
            source.validate_m37_normalized_scan_product(
                replace(self.product, frequency_mhz=changed_frequency)
            )
        del changed_frequency

        arbitrary_normalized = immutable_copy(
            np.zeros(self.product.normalized_values.shape, dtype=np.float32),
            "<f4",
        )
        forged = replace(
            self.product,
            normalized_values=arbitrary_normalized,
            normalized_values_sha256=hashlib.sha256(
                arbitrary_normalized.tobytes()
            ).hexdigest(),
            product_sha256="",
        )
        forged = replace(
            forged,
            product_sha256=hashlib.sha256(
                source.core.canonical_json_bytes(
                    source._normalized_payload(forged)
                )
            ).hexdigest(),
        )
        with self.assertRaisesRegex(V0P6IncompleteError, "do not reproduce"):
            source.validate_m37_normalized_scan_product(forged)

    def test_mutable_arrays_read_only_outputs_and_engine_mutation_fail(self):
        with self.assertRaises(ValueError):
            self.product.raw_values.setflags(write=True)
        with self.assertRaises(ValueError):
            self.product.normalized_values[0, 0] = np.float32(0.0)
        mutable = self.product.normalized_values.copy()
        with self.assertRaisesRegex(V0P6IncompleteError, "mutability"):
            source.validate_m37_normalized_scan_product(
                replace(self.product, normalized_values=mutable)
            )
        with self.assertRaisesRegex(V0P6ContractError, "engine"):
            source.validate_m37_normalized_scan_product(
                replace(
                    self.product,
                    normalization_engine_identity_sha256="f" * 64,
                )
            )

    def test_receipt_mutation_reseal_and_self_hash_lack_live_trust(self):
        with self.assertRaisesRegex(V0P6IncompleteError, "extraction receipt"):
            source.validate_m37_normalized_scan_product(
                replace(self.product, extraction_receipt_sha256="e" * 64)
            )
        resealed = replace(self.product, _receipt=object())
        # Every content hash is still internally correct.  Without either the
        # original live receipt or an independently supplied digest it fails.
        with self.assertRaisesRegex(V0P6ContractError, "live or independently"):
            source.validate_m37_normalized_scan_product(resealed)
        source.validate_m37_normalized_scan_product(
            resealed,
            expected_product_sha256=self.product.product_sha256,
            expected_extraction_receipt_sha256=(
                self.product.extraction_receipt_sha256
            ),
        )

    def test_strict_cache_api_binds_product_sha_and_refuses_generic_arrays(self):
        planned = SimpleNamespace(
            width_channels=1,
            source_sha256=self.product.product_sha256,
        )
        with patch.object(
            source.core,
            "plan_m37_native_filter_cache",
            return_value=planned,
        ) as planner:
            observed = source.plan_m37_production_native_filter_cache(
                self.product,
                None,
                None,
                self.scans,
                None,
                1,
            )
        self.assertIs(observed, planned)
        self.assertEqual(
            planner.call_args.kwargs["source_sha256"],
            self.product.product_sha256,
        )
        cache_sentinel = object()
        with (
            patch.object(
                source.core,
                "plan_m37_native_filter_cache",
                return_value=planned,
            ),
            patch.object(
                source.core,
                "build_native_filter_cache",
                return_value=cache_sentinel,
            ) as builder,
        ):
            cache = source.build_m37_production_native_filter_cache(
                self.product,
                planned,
                None,
                None,
                self.scans,
                None,
            )
        self.assertIs(cache, cache_sentinel)
        np.testing.assert_array_equal(
            builder.call_args.args[0], self.product.normalized_values
        )
        with self.assertRaisesRegex(V0P6ContractError, "sealed normalized"):
            source.build_m37_production_native_filter_cache(
                self.product.normalized_values,
                planned,
                None,
                None,
                self.scans,
                None,
            )

    def test_working_set_gate_rejects_three_products_plus_three_rolls(self):
        one_roll = self.product.normalized_values_nbytes
        scan_at_a_time = source.m37_source_working_set_accounting(
            (self.product,),
            additional_live_ndarray_nbytes=one_roll,
            simultaneous_normalization_reproductions=1,
        )
        self.assertTrue(scan_at_a_time["within_live_ndarray_cap"])
        self.assertEqual(
            scan_at_a_time["peak_live_ndarray_nbytes"],
            self.product.raw_values_nbytes
            + self.product.frequency_mhz_nbytes
            + self.product.normalized_values_nbytes
            + one_roll
            + self.product.raw_values_nbytes,
        )
        with self.assertRaisesRegex(V0P6CapacityError, "512-MiB"):
            source.m37_source_working_set_accounting(
                (self.product, self.product, self.product),
                additional_live_ndarray_nbytes=3 * one_roll,
                simultaneous_normalization_reproductions=0,
            )
        largest = 916_947
        raw = 16 * largest * np.dtype("<f4").itemsize
        frequency = largest * np.dtype("<f8").itemsize
        theoretical_peak = 3 * (2 * raw + frequency) + 3 * raw
        self.assertEqual(theoretical_peak, 550_168_200)
        self.assertGreater(
            theoretical_peak,
            source.M37_MAXIMUM_SOURCE_FACTORY_LIVE_NDARRAY_NBYTES,
        )

    def test_z_cross_process_rehydration_and_wrong_raw_orientation(self):
        extraction_record = source.extracted_scan_product_record(
            self.extracted
        )
        product_record = source.normalized_scan_product_record(self.product)
        extraction_digest = self.extracted.extraction_receipt_sha256
        product_digest = self.product.product_sha256
        raw_original = np.ascontiguousarray(
            self.product.raw_values[:, ::-1], dtype="<f4"
        )
        frequency_original = np.ascontiguousarray(
            self.product.frequency_mhz[::-1], dtype="<f8"
        )
        normalized_witness = self.product.normalized_values.copy()

        # A canonical/ascending raw payload masquerading as header-native raw
        # bytes produces a different extraction receipt and cannot rehydrate
        # against the independently trusted original receipt.
        wrong_orientation = np.ascontiguousarray(
            raw_original[:, ::-1], dtype="<f4"
        )
        with self.assertRaises(V0P6IncompleteError):
            source.rehydrate_m37_extracted_scan_product(
                wrong_orientation,
                frequency_original,
                self.scans,
                extraction_record,
                expected_extraction_receipt_sha256=extraction_digest,
            )
        del wrong_orientation

        # Drop the live factory products before rehydration to model a new
        # process.  Only detached records, arrays, and independent digests stay.
        self.__class__.extracted = None
        self.__class__.product = None
        gc.collect()
        restored = source.rehydrate_m37_normalized_scan_product(
            raw_original,
            frequency_original,
            normalized_witness,
            self.scans,
            extraction_record,
            product_record,
            expected_extraction_receipt_sha256=extraction_digest,
            expected_product_sha256=product_digest,
        )
        self.assertEqual(restored.product_sha256, product_digest)
        self.assertEqual(
            restored.extraction_receipt_sha256, extraction_digest
        )
        source.validate_m37_normalized_scan_product(restored)
        self.__class__.product = restored


if __name__ == "__main__":
    unittest.main()
