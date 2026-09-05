import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ls6_pointing_audit import hdf5_position,distance
class PointingTests(unittest.TestCase):
    def test_hdf5_decimal_units(self):
        ra,dec=hdf5_position({'src_raj':18.9,'src_dej':45.95})
        self.assertAlmostEqual(ra,283.5);self.assertAlmostEqual(dec,45.95)
    def test_sigproc_packed_units_are_not_silently_accepted(self):
        with self.assertRaises(RuntimeError):hdf5_position({'src_raj':185400,'src_dej':455700})
    def test_measured_listing_offset(self):
        self.assertAlmostEqual(distance((283.49994,45.94999),(283.7317274,45.9585288))*60,9.6823274846,places=6)
