from dataclasses import replace
import hashlib
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import unittest
from unittest import mock

import numpy as np

import seti_repeater.calibration_kernel_v0p6 as kernel
from seti_repeater.calibration_kernel_v0p6 import (
    CalibrationKernelContractError,
    CalibrationKernelUnavailableError,
    calibration_kernel_identity,
    m37_null_scramble_maxima,
)
from seti_repeater.search_v0p6 import (
    M37_ACTIVITY_SUBSETS,
    M37_LIVE_NDARRAY_CAP_BYTES,
    M37_SCORE_HALF_BINS,
    load_m37_scramble_tables,
    stack_hypothesis,
)


def independent_roll_stack_reference(vectors, mask, shifts):
    """Literal np.roll plus the public core scorer, independent of the C loop."""
    result = np.empty(shifts.shape[0], dtype=np.float64)
    rolled_vectors = np.empty_like(vectors)
    rolled_mask = np.empty_like(mask)
    with np.errstate(over="ignore", invalid="ignore"):
        for scramble_index, row in enumerate(shifts):
            for epoch, shift in enumerate(row):
                rolled_vectors[epoch] = np.roll(vectors[epoch], int(shift))
                rolled_mask[epoch] = np.roll(mask[epoch], int(shift))
            maximum = -np.inf
            for subset in M37_ACTIVITY_SUBSETS:
                score = stack_hypothesis(
                    rolled_vectors,
                    subset,
                    minimum_active_epoch_snr=3.0,
                    stack_statistic="minimum_epoch",
                    exclusion_mask=rolled_mask,
                )
                maximum = max(maximum, float(np.max(score)))
            result[scramble_index] = maximum
    return result


def assert_float64_bits_equal(test_case, left, right):
    test_case.assertEqual(left.dtype, np.dtype(np.float64))
    test_case.assertEqual(right.dtype, np.dtype(np.float64))
    np.testing.assert_array_equal(left.view(np.uint64), right.view(np.uint64))


class V0P6CalibrationKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = calibration_kernel_identity()

    def test_source_abi_algorithm_and_runtime_are_attested(self):
        identity = self.identity
        self.assertEqual(identity.source_sha256, kernel._EXPECTED_C_SOURCE_SHA256)
        self.assertEqual(
            identity.algorithm_sha256,
            kernel._EXPECTED_ALGORITHM_SHA256,
        )
        self.assertEqual(identity.abi_tag, kernel._ABI_TAG)
        self.assertEqual(
            hashlib.sha256(identity.abi_tag.encode("ascii")).hexdigest(),
            identity.abi_sha256,
        )
        self.assertGreaterEqual(identity.openmp_version, 201_107)
        self.assertGreaterEqual(identity.openmp_max_threads, 1)
        self.assertNotIn("-ffast-math", identity.compiler_flags)
        self.assertIn("-fno-fast-math", identity.compiler_flags)
        self.assertEqual(len(identity.library_sha256), 64)
        self.assertEqual(len(identity.identity_sha256), 64)
        self.assertEqual(calibration_kernel_identity(), identity)

    def test_runtime_identity_is_stable_across_fresh_processes(self):
        script = (
            "from seti_repeater.calibration_kernel_v0p6 import "
            "calibration_kernel_identity; "
            "i=calibration_kernel_identity(); "
            "print(i.library_sha256 + ':' + i.identity_sha256)"
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(
            Path(kernel.__file__).resolve().parents[1]
        )
        identities = [
            subprocess.check_output(
                [sys.executable, "-c", script],
                env=environment,
                text=True,
                timeout=30,
            ).strip()
            for _ in range(2)
        ]
        self.assertEqual(identities[0], identities[1])
        self.assertEqual(
            identities[0],
            f"{self.identity.library_sha256}:{self.identity.identity_sha256}",
        )

    def test_randomized_small_and_odd_grids_are_bitwise_identical(self):
        rng = np.random.default_rng(3_721_260_827)
        for q in (1, 3, 5, 17, 31, 63, 101):
            for _ in range(8):
                vectors = rng.uniform(-4.0, 14.0, size=(3, q)).astype(
                    np.float32
                )
                mask = np.ascontiguousarray(rng.random((3, q)) < 0.19)
                shifts = rng.integers(0, q, size=(13, 3), dtype=np.int64)
                expected = independent_roll_stack_reference(
                    vectors, mask, shifts
                )
                actual = m37_null_scramble_maxima(
                    vectors, mask, shifts, thread_count=3
                )
                assert_float64_bits_equal(self, actual, expected)

    def test_floor_mask_ties_wrap_and_overflow_match_core(self):
        largest = np.finfo(np.float32).max
        vectors = np.array(
            [
                [3.0, 2.9999998, 4.0, 8.0, 8.0, largest, 6.0, 7.0, 5.0],
                [3.0, 9.0, 4.0, 8.0, 7.0, largest, 6.0, 5.0, 7.0],
                [3.0, 9.0, 5.0, 8.0, 7.0, largest, 6.0, 7.0, 5.0],
            ],
            dtype=np.float32,
        )
        mask = np.zeros_like(vectors, dtype=np.bool_)
        mask[0, 3] = True
        mask[1, 6] = True
        shifts = np.array(
            [[0, 0, 0], [8, 1, 4], [1, 8, 0], [4, 4, 4]],
            dtype=np.int64,
        )
        expected = independent_roll_stack_reference(vectors, mask, shifts)
        for threads in (1, 2, 4):
            actual = m37_null_scramble_maxima(
                vectors, mask, shifts, thread_count=threads
            )
            assert_float64_bits_equal(self, actual, expected)

        all_masked = np.ones_like(mask)
        rejected = m37_null_scramble_maxima(
            vectors, all_masked, shifts, thread_count=2
        )
        self.assertTrue(np.all(np.isneginf(rejected)))

    def test_explicit_thread_counts_are_bitwise_deterministic(self):
        rng = np.random.default_rng(3_722_260_827)
        vectors = rng.uniform(2.0, 11.0, size=(3, 10_003)).astype(np.float32)
        mask = np.ascontiguousarray(rng.random(vectors.shape) < 0.03)
        shifts = rng.integers(
            0, vectors.shape[1], size=(37, 3), dtype=np.int64
        )
        single = m37_null_scramble_maxima(
            vectors, mask, shifts, thread_count=1
        )
        for threads in (2, 3, min(8, self.identity.openmp_max_threads)):
            parallel = m37_null_scramble_maxima(
                vectors, mask, shifts, thread_count=threads
            )
            assert_float64_bits_equal(self, parallel, single)

    def test_caller_output_is_validated_and_reused(self):
        vectors = np.full((3, 11), 4.0, dtype=np.float32)
        mask = np.zeros((3, 11), dtype=np.bool_)
        shifts = np.array([[0, 1, 10], [7, 2, 0]], dtype=np.int64)
        out = np.empty(2, dtype=np.float64)
        returned = m37_null_scramble_maxima(
            vectors, mask, shifts, thread_count=1, out=out
        )
        self.assertIs(returned, out)
        self.assertTrue(np.all(np.isfinite(out)))

        read_only = np.empty(2, dtype=np.float64)
        read_only.setflags(write=False)
        with self.assertRaisesRegex(CalibrationKernelContractError, "writable"):
            m37_null_scramble_maxima(
                vectors, mask, shifts, thread_count=1, out=read_only
            )
        with self.assertRaisesRegex(CalibrationKernelContractError, "one cell"):
            m37_null_scramble_maxima(
                vectors,
                mask,
                shifts,
                thread_count=1,
                out=np.empty(3, dtype=np.float64),
            )

    def test_bad_dtype_layout_finiteness_shapes_shifts_and_threads_fail_closed(self):
        vectors = np.full((3, 11), 4.0, dtype=np.float32)
        mask = np.zeros((3, 11), dtype=np.bool_)
        shifts = np.array([[0, 1, 10], [7, 2, 0]], dtype=np.int64)
        cases = (
            (
                "dtype",
                lambda: m37_null_scramble_maxima(
                    vectors.astype(np.float64), mask, shifts
                ),
            ),
            (
                "C-contiguous",
                lambda: m37_null_scramble_maxima(
                    np.asfortranarray(vectors), mask, shifts
                ),
            ),
            (
                "dtype",
                lambda: m37_null_scramble_maxima(
                    vectors, mask.astype(np.uint8), shifts
                ),
            ),
            (
                "shape",
                lambda: m37_null_scramble_maxima(
                    vectors, mask[:, :-1].copy(), shifts
                ),
            ),
            (
                "dtype",
                lambda: m37_null_scramble_maxima(
                    vectors, mask, shifts.astype(np.int32)
                ),
            ),
            (
                "shape",
                lambda: m37_null_scramble_maxima(
                    vectors, mask, shifts[:, :2].copy()
                ),
            ),
            (
                r"\[0, q\)",
                lambda: m37_null_scramble_maxima(
                    vectors,
                    mask,
                    np.array([[0, -1, 1]], dtype=np.int64),
                ),
            ),
            (
                r"\[0, q\)",
                lambda: m37_null_scramble_maxima(
                    vectors,
                    mask,
                    np.array([[0, 11, 1]], dtype=np.int64),
                ),
            ),
            (
                "exact integer",
                lambda: m37_null_scramble_maxima(
                    vectors, mask, shifts, thread_count=True
                ),
            ),
            (
                r"\[1, 1024\]",
                lambda: m37_null_scramble_maxima(
                    vectors, mask, shifts, thread_count=0
                ),
            ),
        )
        for pattern, operation in cases:
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(
                    CalibrationKernelContractError, pattern
                ):
                    operation()

        nonfinite = vectors.copy()
        nonfinite[0, 0] = np.nan
        with self.assertRaisesRegex(CalibrationKernelContractError, "finite"):
            m37_null_scramble_maxima(nonfinite, mask, shifts)
        nonfinite[0, 0] = np.inf
        with self.assertRaisesRegex(CalibrationKernelContractError, "finite"):
            m37_null_scramble_maxima(nonfinite, mask, shifts)

    def test_array_cap_and_output_validation_fail_closed(self):
        vectors = np.full((3, 7), 4.0, dtype=np.float32)
        mask = np.zeros_like(vectors, dtype=np.bool_)
        shifts = np.zeros((1, 3), dtype=np.int64)
        with mock.patch.object(kernel, "M37_LIVE_NDARRAY_CAP_BYTES", 1):
            with self.assertRaisesRegex(
                CalibrationKernelContractError, "live-array budget"
            ):
                m37_null_scramble_maxima(vectors, mask, shifts)
        minimum = float.fromhex("0x1.0f876c0000000p+2")
        kernel._validate_output(np.array([-np.inf, minimum], dtype=np.float64))
        for invalid in (np.nan, np.inf, 3.0, 4.2426406):
            with self.subTest(invalid=invalid):
                with self.assertRaises(CalibrationKernelUnavailableError):
                    kernel._validate_output(
                        np.array([invalid], dtype=np.float64)
                    )

    def test_mutated_source_and_native_identity_tags_fail_closed(self):
        with mock.patch.object(
            kernel, "_EXPECTED_C_SOURCE_SHA256", "0" * 64
        ):
            with self.assertRaisesRegex(
                CalibrationKernelUnavailableError, "source SHA-256 changed"
            ):
                kernel._validated_source_bytes()
        for tags, pattern in (
            (
                ("wrong-abi", kernel._EXPECTED_C_SOURCE_SHA256,
                 kernel._EXPECTED_ALGORITHM_SHA256),
                "ABI changed",
            ),
            (
                (kernel._ABI_TAG, "0" * 64,
                 kernel._EXPECTED_ALGORITHM_SHA256),
                "source identity",
            ),
            (
                (kernel._ABI_TAG, kernel._EXPECTED_C_SOURCE_SHA256,
                 "0" * 64),
                "algorithm identity",
            ),
        ):
            with self.subTest(pattern=pattern):
                with self.assertRaisesRegex(
                    CalibrationKernelUnavailableError, pattern
                ):
                    kernel._require_identity_tags(*tags)

        forged = replace(
            self.identity,
            openmp_max_threads=self.identity.openmp_max_threads + 1,
        )
        with mock.patch.object(kernel, "_LOADED_IDENTITY", forged):
            with self.assertRaisesRegex(
                CalibrationKernelUnavailableError, "in-memory"
            ):
                calibration_kernel_identity()

    @unittest.skipUnless(
        os.environ.get("SETI_RUN_M37_KERNEL_BENCHMARK") == "1",
        "set SETI_RUN_M37_KERNEL_BENCHMARK=1 for the exact-grid benchmark",
    )
    def test_exact_m37_grid_256_scramble_benchmark_and_peak_rss(self):
        q = 2 * M37_SCORE_HALF_BINS + 1
        rng = np.random.default_rng(3_723_260_827)
        vectors = rng.uniform(2.5, 12.0, size=(3, q)).astype(np.float32)
        mask = np.ascontiguousarray(rng.random((3, q)) < 0.025)
        shifts = np.ascontiguousarray(
            load_m37_scramble_tables()[0],
            dtype=np.int64,
        )
        self.assertEqual(vectors.shape, (3, 747_665))
        self.assertEqual(shifts.shape, (256, 3))
        self.assertLessEqual(
            vectors.nbytes + mask.nbytes + shifts.nbytes + 256 * 8,
            M37_LIVE_NDARRAY_CAP_BYTES,
        )

        # Warm the already-attested function before measuring only kernel work.
        m37_null_scramble_maxima(
            vectors[:, :101].copy(),
            mask[:, :101].copy(),
            np.mod(shifts[:2], 101),
            thread_count=min(2, self.identity.openmp_max_threads),
        )
        start = time.perf_counter()
        output = m37_null_scramble_maxima(vectors, mask, shifts)
        wall_seconds = time.perf_counter() - start

        # Full-q bit identity for three witnesses without paying the old 256x
        # Python-loop cost on every test run.
        expected_witnesses = independent_roll_stack_reference(
            vectors, mask, shifts[:3]
        )
        assert_float64_bits_equal(self, output[:3], expected_witnesses)
        self.assertTrue(np.all(np.isfinite(output)))
        output_sha256 = hashlib.sha256(
            np.asarray(output, dtype="<f8").tobytes()
        ).hexdigest()

        peak_raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_bytes = int(peak_raw if sys.platform == "darwin" else peak_raw * 1024)
        self.assertLess(peak_bytes, M37_LIVE_NDARRAY_CAP_BYTES)
        # This is opt-in precisely because performance assertions are machine
        # dependent; on the target host it must beat the measured 9.696 s loop.
        self.assertLess(wall_seconds, 9.696)
        print(
            "M37_KERNEL_BENCHMARK "
            f"wall_seconds={wall_seconds:.6f} "
            f"baseline_seconds=9.696000 "
            f"speedup={9.696 / wall_seconds:.2f}x "
            f"peak_rss_bytes={peak_bytes} "
            f"output_sha256={output_sha256}",
            flush=True,
        )


if __name__ == "__main__":
    unittest.main()
