"""Regression for the observed boundary-coordinate serialization failure."""
import json
import unittest
import numpy as np
from ls8p_audit import boundary
from ls8p_reaudit import json_boundary


class BoundarySerialization(unittest.TestCase):
    def test_recovery_changes_only_integer_representation(self):
        c0 = np.array([[True, True, False], [False, False, False]])
        c1 = np.array([[False, True, True], [False, False, False]])
        cal = np.array([[10., -20., 5.], [0., 0., 0.]])
        cor = np.array([[5., -20., -7.], [0., 0., 0.]])
        maps = {'CAL': cal, 'COR': cor, 'DELTA': cor - cal}
        original = boundary(maps, [c0, c1])
        with self.assertRaisesRegex(TypeError, 'int64'):
            json.dumps(original, allow_nan=False)
        repaired = json_boundary(maps, [c0, c1])
        self.assertEqual(repaired, original)
        self.assertEqual(json.loads(json.dumps(repaired, allow_nan=False)), repaired)
        for name in ('C0_only_pixels', 'C1_only_pixels'):
            self.assertTrue(all(type(v) is int for xy in repaired[name]['xy'] for v in xy))


if __name__ == '__main__':
    unittest.main()
