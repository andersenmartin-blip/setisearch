import unittest

from scripts.ls8e_select_target import (
    basic_visit_eligibility, choose_target, product_flags
)


def visit(key, mjd, eligible=True):
    return {
        "file_key": key,
        "date_mjd_start": mjd,
        "eligible": eligible,
    }


class LS8ESelectionAnswers(unittest.TestCase):
    def test_first_host_needs_two_visits(self):
        ledgers = [
            {"rank": 1, "target": "GJ 876", "visits": [visit("A_V0300", 1)]},
            {"rank": 2, "target": "HD 219134",
             "visits": [visit("B2_V0300", 3), visit("B1_V0300", 2)]},
        ]
        result = choose_target(ledgers)
        self.assertEqual(result["target"], "HD 219134")
        self.assertEqual([x["file_key"] for x in result["selected_visits"]],
                         ["B1_V0300", "B2_V0300"])

    def test_55_cnc_is_excluded_even_if_eligible(self):
        ledgers = [
            {"rank": 7, "target": "55 Cnc",
             "visits": [visit("A_V0300", 1), visit("B_V0300", 2)]},
            {"rank": 8, "target": "47 UMa",
             "visits": [visit("C_V0300", 3), visit("D_V0300", 4)]},
        ]
        self.assertEqual(choose_target(ledgers)["target"], "47 UMa")

    def test_ineligible_visits_do_not_count(self):
        ledgers = [
            {"rank": 1, "target": "GJ 876",
             "visits": [visit("A_V0300", 1), visit("B_V0300", 2, False)]},
        ]
        self.assertIsNone(choose_target(ledgers))

    def test_basic_visit_gate(self):
        row = {
            "file_key": "CH_PR123456_TG000001_V0300",
            "data_pipe_version": "14.1.2",
            "status_published": True,
            "db_lc_available": True,
            "obs_exptime": "2.2",
            "obs_nexp": 10,
            "obs_total_exptime": 22.0,
        }
        self.assertEqual(basic_visit_eligibility(row), (True, []))
        row["obs_total_exptime"] = 61.0
        ok, reasons = basic_visit_eligibility(row)
        self.assertFalse(ok)
        self.assertIn("STACKED_EXPOSURE_OUTSIDE_BOUND", reasons)

    def test_product_gate_requires_default_cal_and_cor(self):
        products = {
            "file": [
                "x_SCI_COR_Lightcurve-DEFAULT_V0300.fits",
                "x_SCI_CAL_SubArray_V0300.fits",
                "x_SCI_COR_SubArray_V0300.fits",
            ],
            "file_ext": [
                "SCI_COR_Lightcurve",
                "SCI_CAL_SubArray",
                "SCI_COR_SubArray",
            ],
        }
        self.assertTrue(product_flags(products)["eligible"])
        products["file_ext"] = products["file_ext"][:-1]
        products["file"] = products["file"][:-1]
        self.assertFalse(product_flags(products)["eligible"])


if __name__ == "__main__":
    unittest.main()
