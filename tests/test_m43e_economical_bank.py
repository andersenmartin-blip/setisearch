import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from m43e_economical_bank import checkerboard_bank, fresh_truths, subset_summary, choose_bank, write_sealed, read_sealed
from m43d_bank_coverage import nested_banks, heldout_truths
from seti_repeater import search_v0p6 as core


class EconomicalBankTests(unittest.TestCase):
    def test_checkerboard_keeps_disk16_and_only_even_parity_additions(self):
        full=nested_banks(core.make_line_template_bank())['disk32']
        bank,indices=checkerboard_bank(full)
        self.assertEqual(bank[:889],full[:889])
        self.assertTrue(889<len(bank)<3301)
        self.assertEqual(list(indices),sorted(set(indices)))
        self.assertEqual([r['template_index'] for r in bank],list(range(len(bank))))
        for new,old in zip(bank,indices,strict=True):
            self.assertEqual((new['coefficient_x'],new['coefficient_y']),
                             (full[old]['coefficient_x'],full[old]['coefficient_y']))
        selected=set(map(int,indices))
        for i,r in enumerate(full[889:],889):
            self.assertEqual(i in selected,(round(r['coefficient_x']*32)+round(r['coefficient_y']*32))%2==0)

    def test_subset_remaps_template_identity_and_preserves_carrier_cells(self):
        grid=core.make_proxy_carrier_grid(.0005,1.,20,4)
        pairs=np.array([[0,1],[1,2],[1,3],[3,4]],dtype='<i8')
        distances=np.array([1.,2.,3.,4.])
        summary=subset_summary(pairs,distances,np.array([1,3]),4,grid)
        self.assertEqual(summary['candidate_cells'],3)
        self.assertEqual(summary['witness']['template_index'],0)
        self.assertEqual(summary['witness']['carrier_index'],2)
        self.assertEqual(summary['witness']['max_distance_hz'],2.)
        empty=subset_summary(pairs,distances,np.array([2]),4,grid)
        self.assertFalse(empty['supported']);self.assertIsNone(empty['witness'])

    def test_selection_requires_every_group_and_inclusive_95_percent(self):
        groups=[{'truth_count':100,'supported':{'checker32':95,'disk32':100}} for _ in range(5)]
        self.assertEqual(choose_bank(groups),'checker32')
        groups[3]['supported']['checker32']=94
        self.assertEqual(choose_bank(groups),'disk32')
        groups[1]['supported']['disk32']=94
        self.assertIsNone(choose_bank(groups))
        with self.assertRaises(ValueError):choose_bank([])

    def test_fresh_generator_new_label_unique_and_area_stratified(self):
        grid=core.make_proxy_carrier_grid(.001,1.,1000,64)
        fresh=fresh_truths(grid)
        self.assertEqual(fresh,fresh_truths(grid))
        self.assertEqual(len(fresh),1024)
        points={(r['coefficient_x'],r['coefficient_y']) for r in fresh}
        self.assertEqual(len(points),1024)
        self.assertFalse(points & {(r['coefficient_x'],r['coefficient_y']) for r in heldout_truths(grid)})
        for r in fresh:
            radius2=r['coefficient_x']**2+r['coefficient_y']**2
            self.assertGreaterEqual(radius2,r['radial_stratum']/32-1e-15)
            self.assertLess(radius2,(r['radial_stratum']+1)/32+1e-15)
            self.assertGreaterEqual(r['proxy_carrier_hz'],grid.score_hz[256])
            self.assertLessEqual(r['proxy_carrier_hz'],grid.score_hz[-257])

    def test_restart_identity_and_lossless_compression_reject_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            plain=Path(temp)/'test.json';packed=Path(temp)/'test.json.gz'
            expected=write_sealed(plain,{'count':3,'selection':'frozen'})
            self.assertEqual(write_sealed(packed,{'count':3,'selection':'frozen'}),expected)
            self.assertEqual(read_sealed(plain),read_sealed(packed))
            tampered=json.loads(plain.read_text());tampered['count']=4
            plain.write_text(json.dumps(tampered))
            with self.assertRaises(RuntimeError):read_sealed(plain)


if __name__=='__main__':unittest.main()
