"""Tests for the capacity-only M37 v0.6.1 physical continuation."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import unittest
from unittest import mock

from seti_repeater import adjacent_v0p6 as adjacent
from seti_repeater import capacity_v0p6p1 as capacity
from seti_repeater import physical_resource_v0p6 as resource
from seti_repeater import physical_v0p6p1 as physical
from seti_repeater import receiver_v0p6 as receiver
from seti_repeater import search_v0p6 as core


ROOT = Path(__file__).resolve().parents[1]
AMENDMENT = ROOT / "config/hd156668b_m37_v0p6p1_capacity_amendment.json"
RETENTION = ROOT / "results_m37_v0p6p1_primary_006" / "retention"


class M37V0P6P1PhysicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = capacity.open_m37_v0p6p1_capacity_amendment(AMENDMENT)

    @staticmethod
    def _certificate(window_id: str, kind: str):
        path = RETENTION / f"{window_id}-{kind}.json.gz"
        artifact = json.loads(gzip.decompress(path.read_bytes()))
        return artifact["certificate"]

    def test_all_published_amended_retention_certificates_validate(self):
        counts = {}
        for window_id in core.M37_WINDOW_IDS:
            for kind in ("on", "off"):
                certificate = self._certificate(window_id, kind)
                validated = (
                    physical.validate_m37_v0p6p1_retention_certificate(
                        certificate,
                        self.profile,
                        expected_kind=kind,
                        expected_certificate_sha256=certificate[
                            "retention_certificate_sha256"
                        ],
                    )
                )
                counts[(window_id, kind)] = validated[
                    "retained_record_count"
                ]
        self.assertEqual(counts[("m37_1418p5", "on")], 41_640)
        self.assertEqual(counts[("m37_1418p5", "off")], 0)
        self.assertEqual(sum(counts.values()), 46_043)

    def test_old_and_amended_resource_limits_remain_separate(self):
        self.assertEqual(core.M37_MAXIMUM_RECORDS_PER_WINDOW, 10_000)
        self.assertEqual(self.profile.maximum_records_per_window, 50_000)
        self.assertEqual(
            receiver.M37_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS,
            5_000_000,
        )
        self.assertEqual(
            physical.M37_V0P6P1_MAXIMUM_RECEIVER_SIGNATURE_LOCAL_CHANNEL_VISITS,
            25_000_000,
        )

    def test_execution_wrapper_changes_only_declared_resource_arguments(self):
        sentinel = {"validated": True}
        execution = {"execution_result_sha256": "a" * 64}
        with (
            mock.patch.object(
                physical,
                "_validate_scientific_inputs",
                return_value=({}, ["bank"]),
            ),
            mock.patch.object(
                resource,
                "execute_physical_evidence_streams",
                return_value=execution,
            ) as execute,
            mock.patch.object(
                physical,
                "validate_m37_v0p6p1_physical_evidence_execution_result",
                return_value=sentinel,
            ),
        ):
            result = physical.execute_m37_v0p6p1_physical_evidence_streams(
                self.profile,
                [],
                {},
                object(),
                object(),
                [],
                object(),
                object(),
                object(),
                expected_on_retention_certificate_sha256="b" * 64,
            )
        self.assertIs(result, sentinel)
        kwargs = execute.call_args.kwargs
        self.assertEqual(kwargs["maximum_records"], 50_000)
        self.assertEqual(kwargs["maximum_receiver_queries"], 150_000)
        self.assertEqual(kwargs["maximum_adjacent_queries"], 150_000)
        self.assertEqual(
            kwargs["maximum_receiver_local_channel_visits"], 25_000_000
        )
        self.assertEqual(kwargs["maximum_evidence_canonical_bytes"], 480_000_000)
        self.assertEqual(
            kwargs["local_receiver_half_width_hz"],
            receiver.M37_RECEIVER_SIGNATURE_LOCAL_HALF_WIDTH_HZ,
        )
        self.assertEqual(
            kwargs["single_adjacent_off_snr_floor"],
            adjacent.M37_SINGLE_ADJACENT_OFF_SNR_FLOOR,
        )

    def test_physical_artifact_cap_scales_with_amended_evidence(self):
        self.assertEqual(
            physical.M37_V0P6P1_PHYSICAL_DISPOSITION_ARTIFACT_MAXIMUM_BYTES,
            1_953_554_432,
        )


if __name__ == "__main__":
    unittest.main()
