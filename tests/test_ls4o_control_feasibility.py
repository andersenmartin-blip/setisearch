import copy
import unittest
from ls4o_control_feasibility import packed_angle,separation_deg,interval_metrics,inventory,queries,load

C=load('config/ls4o_control_feasibility.json')


class FeasibilityTests(unittest.TestCase):
    def test_packed_coordinates_and_rejections(self):
        self.assertAlmostEqual(packed_angle(123000.,True),187.5)
        self.assertAlmostEqual(packed_angle(-153000.),-15.5)
        self.assertAlmostEqual(packed_angle(-3000.),-.5)
        for value,ra in [(126000.,True),(-10000.,True),(240000.,True),(900001.,False),(float('nan'),False)]:
            with self.assertRaises(ValueError):packed_angle(value,ra)

    def test_spherical_wrap_poles_and_right_angle(self):
        self.assertAlmostEqual(separation_deg(359,0,1,0),2)
        self.assertAlmostEqual(separation_deg(0,0,90,0),90)
        self.assertAlmostEqual(separation_deg(0,90,180,90),0)

    def test_interval_disjoint_touching_overlap_and_containment(self):
        for args,expected in [((0,10,20,5),{'overlap_s':0.,'gap_s':10.}),((0,10,10,10),{'overlap_s':0.,'gap_s':0.}),
                ((0,10,5,10),{'overlap_s':5.,'gap_s':0.}),((0,10,2,3),{'overlap_s':3.,'gap_s':0.})]:
            self.assertEqual(interval_metrics(*args),expected)

    def receipts(self):
        def record(url,mjd,target='LHS1140',freq=10013.):
            return {'url':url,'mjd':mjd,'target':target,'center_freq':freq,'size':100,'telescope':'GBT'}
        old=record('old.gpuspec.0002.fil',C['original_x_start_mjd'])
        later=record('later.gpuspec.0002.fil',C['original_x_start_mjd']+1.)
        htr=record('later.gpuspec.8.0001.fil',C['original_x_start_mjd']+1.)
        wrong=record('wrong',C['original_x_start_mjd']+2.,'OTHER')
        return [{'kind':'target_only','successful':True,'record_limit_reached':False,'response':{'data':[old,later,htr,wrong]}},
                {'kind':'historical_restricted_control','successful':True,'record_limit_reached':False,'response':{'data':[old]}}]

    def test_dedup_exact_alias_filter_epoch_boundary_and_products(self):
        result=inventory(self.receipts(),C)
        self.assertEqual(result['unique_accepted_products'],3)
        self.assertEqual(result['excluded_nonmatching_records'],1)
        self.assertEqual(result['unique_scan_frequency_groups'],2)
        self.assertEqual(len(result['candidate_later_or_earlier_x_scan_groups']),1)
        candidate=result['candidate_later_or_earlier_x_scan_groups'][0]
        self.assertTrue(candidate['has_medium_product'] and candidate['has_htr_product'])
        self.assertEqual(result['restricted_products_missing_from_target_queries'],[])

    def test_nonmatching_band_same_day_and_conflict_are_not_hidden(self):
        receipts=self.receipts()
        for r in receipts[0]['response']['data'][1:3]:r['center_freq']=6500.
        self.assertFalse(inventory(receipts,C)['candidate_later_or_earlier_x_scan_groups'])
        receipts=self.receipts();receipts[1]['response']['data'][0]=copy.deepcopy(receipts[1]['response']['data'][0])
        receipts[1]['response']['data'][0]['size']=101
        self.assertTrue(inventory(receipts,C)['metadata_conflicts'])
        receipts=self.receipts();receipts[0]['successful']=False
        self.assertTrue(inventory(receipts,C)['restricted_products_missing_from_target_queries'])

    def test_query_scope_and_resource_bounds(self):
        q=queries(C);self.assertEqual(len(q),11)
        self.assertTrue(all(set(x['params'])=={'target','limit'} for x in q[:-1]))
        self.assertEqual(q[-1]['params']['cadence'],'True')
        self.assertEqual(C['network']['max_response_bytes'],2000000)


if __name__=='__main__':unittest.main()
