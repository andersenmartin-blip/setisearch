"""Fail-closed accounting tests for the post-contact capacity census."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

import numpy as np

from seti_repeater import search_v0p6 as core


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "scripts" / "m37_v0p6_capacity_census.py"
    spec = importlib.util.spec_from_file_location(
        "m37_v0p6_capacity_census_test", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class M37CapacityCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.census = _module()
        cls.window_id = core.M37_WINDOW_IDS[0]
        cls.line_indices = tuple(range(core.M37_TEMPLATE_COUNT))
        cls.expected = {
            "expected_run_id": "run-004",
            "expected_window_id": cls.window_id,
            "expected_kind": "on",
            "expected_script_sha256": "1" * 64,
            "expected_source_metadata_sha256": "2" * 64,
            "expected_failure_evidence_sha256": "3" * 64,
            "expected_threshold_certificate_sha256": "4" * 64,
            "expected_operational_threshold_snr": 100.0,
            "expected_cache_manifest_file_sha256": "5" * 64,
            "expected_factor_bundle_manifest_sha256": "6" * 64,
            "expected_journal_head_sha256": "7" * 64,
            "expected_line_indices": cls.line_indices,
        }

    def _seal_child(self, value):
        sealed = copy.deepcopy(value)
        sealed.pop("artifact_sha256", None)
        sealed["artifact_sha256"] = self.census._sha256_bytes(
            core.canonical_json_bytes(sealed)
        )
        return sealed

    def _empty_child(self):
        hypotheses = (
            core.M37_TEMPLATE_COUNT
            * len(core.M37_SPECTRAL_WIDTHS)
            * len(core.M37_ACTIVITY_SUBSETS)
        )
        grid = core.make_m37_proxy_carrier_grid(self.window_id)
        value = {
            "artifact_type": self.census.CHILD_ARTIFACT_TYPE,
            "diagnostic_id": self.census.DIAGNOSTIC_ID,
            "run_id": "run-004",
            "window_id": self.window_id,
            "scan_kind": "on",
            "claim_boundary": self.census.CHILD_CLAIM_BOUNDARY,
            "diagnostic_orchestrator_sha256": "1" * 64,
            "source_metadata_sha256": "2" * 64,
            "capacity_failure_evidence_sha256": "3" * 64,
            "threshold_certificate_sha256": "4" * 64,
            "operational_threshold_snr": 100.0,
            "cache_run_manifest_file_sha256": "5" * 64,
            "factor_bundle_manifest_sha256": "6" * 64,
            "invalid_run_journal_head_sha256": "7" * 64,
            "proxy_grid_sha256": core.proxy_carrier_grid_sha256(grid),
            "frequency_bucket_hz": self.census.FREQUENCY_BUCKET_HZ,
            "hypotheses_evaluated": hypotheses,
            "score_cells_evaluated": hypotheses * grid.score_bin_count,
            "above_threshold_record_count": 0,
            "nonzero_hypothesis_count": 0,
            "maximum_snr": None,
            "retention_capacity": core.M37_MAXIMUM_RECORDS_PER_WINDOW,
            "capacity_exceeded": False,
            "counts_by_template": [
                {
                    "template_index": index,
                    "line_index": self.line_indices[index],
                    "count": 0,
                }
                for index in range(core.M37_TEMPLATE_COUNT)
            ],
            "counts_by_width": [
                {
                    "width_index": index,
                    "width_channels": width,
                    "count": 0,
                }
                for index, width in enumerate(core.M37_SPECTRAL_WIDTHS)
            ],
            "counts_by_activity_subset": [
                {"active_epochs_zero_based": list(subset), "count": 0}
                for subset in core.M37_ACTIVITY_SUBSETS
            ],
            "frequency_buckets": [],
            "snr_ratio_histogram": [
                {**item, "count": 0}
                for item in self.census._ratio_histogram(
                    np.asarray([], dtype=np.float64), 100.0
                )
            ],
            "nonzero_hypotheses": [],
        }
        return self._seal_child(value)

    def test_ratio_histogram_uses_inclusive_lower_boundaries(self):
        threshold = 100.0
        values = threshold * np.asarray([1.0, 1.05, 1.1, 256.0, 300.0])
        counts = [
            item["count"]
            for item in self.census._ratio_histogram(values, threshold)
        ]
        self.assertEqual(counts[:3], [1, 1, 1])
        self.assertEqual(counts[-1], 2)
        self.assertEqual(sum(counts), len(values))
        with self.assertRaises(core.V0P6IncompleteError):
            self.census._ratio_histogram(
                np.asarray([np.nextafter(threshold, 0.0)]), threshold
            )

    def test_empty_child_passes_full_cross_total_validation(self):
        child = self._empty_child()
        self.assertEqual(
            self.census._validate_child(child, **self.expected), child
        )

    def test_child_rejects_resealed_provenance_and_order_changes(self):
        changed = self._empty_child()
        changed["source_metadata_sha256"] = "8" * 64
        changed = self._seal_child(changed)
        with self.assertRaises(core.V0P6IncompleteError):
            self.census._validate_child(changed, **self.expected)

        changed = self._empty_child()
        changed["counts_by_width"].reverse()
        changed = self._seal_child(changed)
        with self.assertRaises(core.V0P6IncompleteError):
            self.census._validate_child(changed, **self.expected)

    def _seal_manifest(self, value):
        sealed = copy.deepcopy(value)
        sealed.pop("manifest_sha256", None)
        sealed["manifest_sha256"] = self.census._sha256_bytes(
            core.canonical_json_bytes(sealed)
        )
        return sealed

    def _manifest(self):
        entries = [
            {
                "window_id": window_id,
                "scan_kind": kind,
                "above_threshold_record_count": index,
            }
            for index, (window_id, kind) in enumerate(
                (pair for window_id in core.M37_WINDOW_IDS
                 for pair in ((window_id, "on"), (window_id, "off")))
            )
        ]
        return self._seal_manifest(
            {
                "artifact_type": self.census.MANIFEST_ARTIFACT_TYPE,
                "diagnostic_id": self.census.DIAGNOSTIC_ID,
                "claim_boundary": self.census.MANIFEST_CLAIM_BOUNDARY,
                "window_count": len(core.M37_WINDOW_IDS),
                "scan_kind_count": len(self.census.KINDS),
                "entry_count": len(entries),
                "total_score_cells_evaluated": (
                    self.census._total_score_cells()
                ),
                "total_above_threshold_records": sum(
                    item["above_threshold_record_count"] for item in entries
                ),
                "entries": entries,
            }
        )

    def test_manifest_requires_all_ten_ordered_cross_totals(self):
        manifest = self._manifest()
        self.assertEqual(self.census._validate_manifest(manifest), manifest)

        changed = copy.deepcopy(manifest)
        changed["entries"].reverse()
        changed = self._seal_manifest(changed)
        with self.assertRaises(core.V0P6IncompleteError):
            self.census._validate_manifest(changed)


if __name__ == "__main__":
    unittest.main()
