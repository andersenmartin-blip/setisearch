import unittest
from m43v_component_diagnostic import coordinate,final_keys,set_comparison

class ComponentAccountingTests(unittest.TestCase):
    def test_coordinates_ignore_scores_but_preserve_activity_and_width(self):
        m=dict(template_index=2,proxy_carrier_index=12,spectral_width_channels=9,active_epochs_zero_based=[0,2],
            snr=10,record_id='a',passes_evaluated_physical_vetoes=True,meets_diagnostic_rank_cut=True)
        n=m|dict(snr=32,record_id='b')
        self.assertEqual(coordinate(m),coordinate(n))
        self.assertNotEqual(coordinate(m),coordinate(m|dict(active_epochs_zero_based=[0,1])))
        self.assertNotEqual(coordinate(m),coordinate(m|dict(spectral_width_channels=5)))
        self.assertEqual(len(final_keys({'members':[m,n,m|dict(passes_evaluated_physical_vetoes=False)]})),1)

    def test_component_union_does_not_double_count_and_retains_nonlinearity(self):
        k=lambda x:(0,x,1,(0,1))
        r=set_comparison({k(1),k(4)},{k(1),k(2)},{k(2),k(3)})
        self.assertEqual([r[x] for x in ('both','component_union','both_only','shared_with_component_union','component_union_only')],[2,3,1,1,2])
        self.assertEqual(r['both_only_coordinates'],[k(4)])

if __name__=='__main__':unittest.main()
