"""Tests for persisted threshold-bound global-null vectors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from seti_repeater import null_artifact_v0p6 as null_io
from seti_repeater import search_v0p6 as core


def _fixture():
    grid = core.make_proxy_carrier_grid(0.0001, 1.0, 5, 1)
    bank = [core.make_line_template_bank()[0]]
    bank_sha256 = core.template_bank_sha256(bank)
    values = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    shifts = core.make_scramble_shift_table(
        values.size,
        3,
        grid.score_bin_count,
        seed=37_062_121,
        minimum_shift_bins=1,
    )
    calibration = core.CalibrationAccumulator.create(
        window_id="synthetic",
        score_bin_count=grid.score_bin_count,
        template_count=1,
        template_bank_sha256_value=bank_sha256,
        factor_basis_sha256_value="1" * 64,
        factor_basis_labels_sha256_value="2" * 64,
        scan_inventory_sha256_value="3" * 64,
        factor_row_selection_sha256_value="4" * 64,
        factor_table_sha256_value="5" * 64,
        spectral_widths=(1,),
        activity_subsets=((0, 1),),
        minimum_active_epoch_snr=None,
        stack_statistic="sum",
        scramble_shifts=shifts,
        minimum_shift_bins=1,
        expected_scramble_sha256=core.scramble_table_sha256(shifts),
    )
    core.update_calibration(
        calibration,
        np.zeros((3, grid.score_bin_count), dtype=np.float32),
        template_index=0,
        width_index=0,
        exclusion_mask=None,
    )
    calibration.null_maxima[:] = values
    calibration._checkpoint_state()
    calibration.finalize()
    threshold = core.calibrated_threshold(
        (calibration,),
        expected_window_ids=("synthetic",),
        reference_floor=1.0,
        quantile=0.0,
    )
    return threshold, values


class GlobalNullArtifactTests(unittest.TestCase):
    def test_round_trip_rehydrates_threshold_and_read_only_vector(self) -> None:
        threshold, values = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global-null.json"
            receipt = null_io.publish_global_null_artifact(
                path,
                threshold,
                values,
                metadata={"window_scope": "synthetic"},
                spectral_dataset_values_read=True,
            )
            opened = null_io.open_global_null_artifact(
                path,
                expected_file_sha256=receipt.file_sha256,
                expected_threshold_certificate_sha256=(
                    receipt.threshold_certificate_sha256
                ),
                require_spectral_dataset_values_read=True,
            )
            self.assertEqual(opened.receipt, receipt)
            np.testing.assert_array_equal(opened.values, values)
            self.assertFalse(opened.values.flags.writeable)
            core.validate_threshold_certificate(opened.threshold)
            self.assertEqual(opened.metadata, {"window_scope": "synthetic"})

    def test_existing_file_and_independent_identities_fail_closed(self) -> None:
        threshold, values = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global-null.json"
            receipt = null_io.publish_global_null_artifact(
                path,
                threshold,
                values,
                metadata={},
                spectral_dataset_values_read=False,
            )
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                null_io.publish_global_null_artifact(
                    path,
                    threshold,
                    values,
                    metadata={},
                    spectral_dataset_values_read=False,
                )
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaisesRegex(core.V0P6IncompleteError, "file identity"):
                null_io.open_global_null_artifact(
                    path,
                    expected_file_sha256="0" * 64,
                    expected_threshold_certificate_sha256=(
                        receipt.threshold_certificate_sha256
                    ),
                )
            with self.assertRaisesRegex(core.V0P6IncompleteError, "threshold identity"):
                null_io.open_global_null_artifact(
                    path,
                    expected_file_sha256=receipt.file_sha256,
                    expected_threshold_certificate_sha256="1" * 64,
                )

    def test_resealed_vector_mutation_cannot_escape_threshold_binding(self) -> None:
        threshold, values = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global-null.json"
            receipt = null_io.publish_global_null_artifact(
                path,
                threshold,
                values,
                metadata={},
                spectral_dataset_values_read=True,
            )
            record = json.loads(path.read_text())
            record["global_null_maxima"][0] = 99.0
            changed = core.canonical_json_bytes(record)
            path.chmod(0o644)
            path.write_bytes(changed)
            path.chmod(0o444)
            with self.assertRaisesRegex(core.V0P6IncompleteError, "accounting"):
                null_io.open_global_null_artifact(
                    path,
                    expected_file_sha256=hashlib.sha256(changed).hexdigest(),
                    expected_threshold_certificate_sha256=(
                        receipt.threshold_certificate_sha256
                    ),
                )

    def test_spectral_read_provenance_and_m37_wrapper_are_strict(self) -> None:
        threshold, values = _fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "global-null.json"
            receipt = null_io.publish_global_null_artifact(
                path,
                threshold,
                values,
                metadata={},
                spectral_dataset_values_read=False,
            )
            with self.assertRaisesRegex(
                core.V0P6IncompleteError, "spectral-read provenance"
            ):
                null_io.open_global_null_artifact(
                    path,
                    expected_file_sha256=receipt.file_sha256,
                    expected_threshold_certificate_sha256=(
                        receipt.threshold_certificate_sha256
                    ),
                    require_spectral_dataset_values_read=True,
                )
            with self.assertRaisesRegex(core.V0P6IncompleteError, "M37 contract"):
                null_io.publish_m37_global_null_artifact(
                    Path(directory) / "m37.json",
                    threshold,
                    values,
                    metadata={},
                )


if __name__ == "__main__":
    unittest.main()
