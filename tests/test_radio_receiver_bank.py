import dataclasses
from fractions import Fraction
import json
from pathlib import Path
import unittest

import numpy as np

from seti_repeater import receiver_bank_radio as r
from seti_repeater import factors_radio as orbital

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "config/radio_hd189733_source_preparation_20260927.json"
DESIGN = ROOT / "results_radio_hd189733_geometry_2026-09-27/window_geometry.json"
SOURCE_SHA = "98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1"
DESIGN_SHA = "92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6"


class ReceiverBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.args = (SOURCE.read_bytes(), SOURCE_SHA, DESIGN.read_bytes(), DESIGN_SHA)
        cls.banks = [r.build(*cls.args, role) for role in ("calibration", "validation", "pilot")]

    def test_three_roles_have_distinct_bound_banks(self):
        self.assertEqual(len({b.identity for b in self.banks}), 3)
        self.assertTrue(all(b.factors.shape == (81,96,3) for b in self.banks))

    def test_external_source_pin_required(self):
        with self.assertRaises(ValueError):
            r.build(self.args[0]+b" ", *self.args[1:], "pilot")

    def test_external_design_pin_required(self):
        with self.assertRaises(ValueError):
            r.build(self.args[0], self.args[1], self.args[2]+b" ", self.args[3], "pilot")

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError): r.build(*self.args, "development")

    def test_zero_rate_and_anchor_exact(self):
        for b in self.banks:
            np.testing.assert_array_equal(b.factors[40], np.ones((96,3)))
            np.testing.assert_array_equal(b.factors[:,0,1], np.ones(81))

    def test_received_drift_sign_matches_chronological_frequency(self):
        self.assertLess(self.banks[0].factors[0,-1,1], 1)
        self.assertGreater(self.banks[0].factors[-1,-1,1], 1)

    def test_mutable_or_modified_payload_rejected(self):
        b = self.banks[0]
        with self.assertRaises(ValueError): dataclasses.replace(b, factors=b.factors.copy()).validate()
        with self.assertRaises(ValueError): b.factors[0,0,0] = 2

    def test_mutated_identity_rejected(self):
        with self.assertRaises(ValueError): dataclasses.replace(self.banks[0], identity="0"*64).validate()

    def test_receiver_type_cannot_impersonate_orbital_provider(self):
        with self.assertRaises(ValueError): orbital.validate(self.banks[0])

    def test_exact_clock_overlap_rejected(self):
        source = json.loads(self.args[0])
        source["scans"][1]["expected_header"]["tstart_mjd"] = source["scans"][0]["expected_header"]["tstart_mjd"]
        with self.assertRaises(ValueError): r.clock(source)

    def test_nonpositive_duration_rejected(self):
        source = json.loads(self.args[0]); source["scans"][0]["expected_header"]["tsamp_s"] = 0
        with self.assertRaises(ValueError): r.clock(source)

    def test_exact_clock_midpoints_not_mjd_roundtrip(self):
        rows = r.clock(json.loads(self.args[0]))
        self.assertEqual(rows[0][1], Fraction(0))
        self.assertTrue(all(2*x[1] == x[0]+x[2] for x in rows))

    def test_coverage_is_geometric_not_spectral_permission(self):
        for role in ("calibration", "validation", "pilot"):
            c = r.coverage(*self.args, role)
            self.assertTrue(c["continuous_linear_family_contained_at_width_129"])
            self.assertTrue(c["full_support_and_receiver_neighborhood_inside_extraction"])
            self.assertFalse(c["spectral_power_recovery_qualified"])
            self.assertFalse(c["spectral_access_authorized"])

    def test_unchanged_primary_widths(self):
        self.assertEqual(r.WIDTHS, (1,3,5,9,17,33,65,129))
        for b in self.banks:
            self.assertEqual(json.loads(b.provenance_json)["primary"], "neighbor9")


if __name__ == "__main__": unittest.main()
