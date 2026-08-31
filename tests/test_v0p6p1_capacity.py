"""Tests for the sole post-contact M37 v0.6.1 capacity amendment."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from seti_repeater import capacity_v0p6p1 as capacity
from seti_repeater import search_v0p6 as core


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "config/hd156668b_m37_v0p6p1_capacity_amendment.json"


class M37V0P6P1CapacityTests(unittest.TestCase):
    def test_frozen_amendment_opens_with_complete_census_ancestry(self):
        profile = capacity.open_m37_v0p6p1_capacity_amendment(AMENDMENT)
        self.assertEqual(profile.maximum_records_per_window, 50_000)
        self.assertEqual(
            profile.maximum_retention_evidence_canonical_bytes_per_window,
            480_000_000,
        )
        record = profile.as_record()
        self.assertEqual(
            record["capacity_census_manifest_sha256"],
            capacity.M37_V0P6P1_CAPACITY_CENSUS_MANIFEST_SHA256,
        )
        self.assertEqual(
            capacity.validate_m37_v0p6p1_capacity_profile_record(record),
            profile,
        )

    def test_file_and_resealed_receipt_mutations_fail_closed(self):
        value = json.loads(AMENDMENT.read_text())
        value["capacities"]["maximum_records_per_window"] += 1
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "amendment.json"
            changed.write_text(json.dumps(value))
            with self.assertRaises(core.V0P6ContractError):
                capacity.open_m37_v0p6p1_capacity_amendment(changed)

        profile = capacity.open_m37_v0p6p1_capacity_amendment(AMENDMENT)
        changed_record = copy.deepcopy(profile.as_record())
        changed_record["capacities"]["maximum_records_per_window"] += 1
        with self.assertRaises(core.V0P6ContractError):
            capacity.validate_m37_v0p6p1_capacity_profile_record(
                changed_record
            )

    def test_retention_factory_changes_only_resource_arguments(self):
        profile = capacity.open_m37_v0p6p1_capacity_amendment(AMENDMENT)
        sentinel = object()
        inputs = [object() for _ in range(6)]
        with mock.patch.object(
            core,
            "_make_m37_retention_ledger_with_capacities",
            return_value=sentinel,
        ) as factory:
            result = capacity.make_m37_v0p6p1_retention_ledger(
                profile, *inputs
            )
        self.assertIs(result, sentinel)
        factory.assert_called_once_with(
            *inputs,
            maximum_records=50_000,
            maximum_evidence_canonical_bytes=480_000_000,
        )

    def test_derived_evidence_bound_fits_declared_envelope(self):
        hypotheses = (
            core.M37_TEMPLATE_COUNT
            * len(core.M37_SPECTRAL_WIDTHS)
            * len(core.M37_ACTIVITY_SUBSETS)
        )
        derived = (
            capacity.M37_V0P6P1_MAXIMUM_RECORDS_PER_WINDOW
            * core.M37_MAXIMUM_RECORD_CANONICAL_BYTES
            + capacity.M37_V0P6P1_MAXIMUM_CLUSTERS_PER_WINDOW * 2_048
            + hypotheses * 1_024
            + 5_000_000
        )
        self.assertEqual(
            derived, capacity.M37_V0P6P1_DERIVED_RETENTION_EVIDENCE_BYTES
        )
        self.assertLess(
            derived, capacity.M37_V0P6P1_MAXIMUM_EVIDENCE_CANONICAL_BYTES
        )


if __name__ == "__main__":
    unittest.main()
