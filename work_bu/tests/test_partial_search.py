"""Artificial-only checks for partial-cadence semantics and pinned numerics."""
from pathlib import Path
import ast
import importlib.util
import unittest
import numpy as np

SOURCE = Path(__file__).resolve().parents[1]/'partial_search.py'
spec = importlib.util.spec_from_file_location('bu_partial_test_subject',SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class PartialSearchTests(unittest.TestCase):
    def test_actual_header_time_overrides_catalogue_mjd(self):
        header = {'scan':0,'shape':[16,1,359661568],
                  'archive':{'id':65133,'target':'HIP44295','mjd':57660.61373842593},
                  'attrs':{'source_name':'HIP44295','tstart':57660.61375,'tsamp':18.253611008,
                           'fch1':2802.83203125,'foff':-2.7939677238464355e-06,
                           'nchans':359661568,'nbits':32,'nifs':1},
                  'chunks':[{'scan':0,'time_index':row,'chunk_offset':[row,0,179306496],
                             'filter_mask':0,'size':100} for row in range(16)]}
        scope = {'header_tstart_mjd':57660.61375,'dt_seconds':18.253611008,
                 'df_hz':-2.7939677238464355,'source_header_first_frequency_mhz':2802.83203125,
                 'source_nchannels':359661568}
        subject.verify_header_content(scope,0,header)
        scope['header_tstart_mjd'] = header['archive']['mjd']
        with self.assertRaisesRegex(ValueError,'not bound to original'):
            subject.verify_header_content(scope,0,header)

    def test_frozen_source_ast_and_grid(self):
        kernel, normalizer, numeric = subject.load_numerics()
        self.assertEqual(subject.sha(subject.BN),subject.BN_SHA)
        self.assertEqual(len(numeric['drift_rates']({'scans':[{'dt_seconds':18.253611008,'df_hz':-2.7939677238464355}]})),839)
        tree = ast.parse(subject.BN.read_text())
        expected = [node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in subject.NUMERIC_FUNCTIONS]
        self.assertEqual(tuple(node.name for node in expected),subject.NUMERIC_FUNCTIONS)
        for name in subject.NUMERIC_FUNCTIONS:
            self.assertEqual(numeric[name].__code__.co_filename,str(subject.BN))

    def test_partial_status_truth_table(self):
        center = np.full((4,6),12.0); maximum = center.copy()
        center[:,[1,3]]=0; maximum[:,[1,3]]=0
        center[:,5]=np.nan; maximum[:,5]=np.nan
        valid = np.ones((4,6),dtype=bool); valid[:,5]=False
        maximum[1,1]=5
        center[2,2]=9.99
        valid[3,3]=False
        result = subject.classify_partial(center,maximum,valid)
        self.assertEqual(result['candidate_status'].tolist(),[
            'INCOMPLETE_OFF_COVERAGE','REJECTED_AVAILABLE_OFF','THREE_ON_FAIL','UNSUPPORTED'])
        self.assertFalse(result['complete_OFF_support'].any())
        self.assertEqual(result['three_ON_pass'].tolist(),[True,True,False,True])
        self.assertEqual(result['available_OFF_veto'].tolist(),[False,True,False,False])

    def test_missing_off_cannot_be_zero_filled(self):
        center = np.zeros((1,6)); valid = np.ones((1,6),dtype=bool); valid[:,5]=False
        with self.assertRaisesRegex(ValueError,'OFF5'):
            subject.classify_partial(center,center.copy(),valid)

    def test_actual_kernel_partial_association_and_off_neighborhood(self):
        kernel, _, _ = subject.load_numerics()
        df = -2.7939677238464355; fch1 = 2301.85546875
        scopes = [{'scan':j,'role':'ON' if j%2==0 else 'OFF',
                   'tref_midpoint_mjd':57660.0,'fch1_mhz':fch1,'df_hz':df} for j in range(5)]
        records = [{'support_start':0} for _ in scopes]
        supports = [np.zeros((16,128),dtype=np.float32) for _ in scopes]
        for j in (0,2,4): supports[j][:,64]=1
        grids = [{'drift_hz_s':np.linspace(-4,4,839), 'offsets':np.zeros((839,16),dtype=np.int32),
                  **{f'calibration_width_{w}':np.tile([0.,1.],(839,1)) for w in subject.WIDTHS}} for _ in scopes]
        catalogs = []
        for j in range(5):
            count = int(j%2==0)
            catalogs.append({'channel_at_midpoint':np.full(count,64,dtype=np.int32),
                             'drift_index':np.full(count,419,dtype=np.int32),
                             'width_channels':np.full(count,1,dtype=np.int16),
                             'ess':np.full(count,16.),'drift_hz_s':np.zeros(count),
                             'frequency_at_midpoint_mhz':np.full(count,fch1+64*df/1e6)})
        arrays, summary = subject.associate_partial({'scans':scopes},records,grids,catalogs,kernel,supports)
        self.assertEqual(arrays['candidate_status'].tolist(),['INCOMPLETE_OFF_COVERAGE']*3)
        self.assertTrue(np.isnan(arrays['forced_center_local_ess'][:,5]).all())
        self.assertFalse(arrays['forced_valid'][:,5].any())
        self.assertEqual(summary['full_cadence_candidate_assessment'],'NOT_EVALUABLE_MISSING_OFF5')
        supports[1][:,65] = .4
        arrays, summary = subject.associate_partial({'scans':scopes},records,grids,catalogs,kernel,supports)
        self.assertEqual(arrays['candidate_status'].tolist(),['REJECTED_AVAILABLE_OFF']*3)
        self.assertTrue((arrays['forced_center_local_ess'][:,1] == 0).all())
        self.assertTrue((arrays['forced_neighborhood_max_local_ess'][:,1] > 5).all())

    def test_empty_catalog_is_explicitly_partial(self):
        kernel,_,_ = subject.load_numerics()
        scopes = [{'scan':j,'tref_midpoint_mjd':0.,'fch1_mhz':2300.,'df_hz':-2.7939677238464355} for j in range(5)]
        empty = {key:np.array([],dtype=dtype) for key,dtype in [
            ('channel_at_midpoint',np.int32),('drift_index',np.int32),('width_channels',np.int16),
            ('ess',np.float64),('drift_hz_s',np.float64),('frequency_at_midpoint_mhz',np.float64)]}
        grid = {'drift_hz_s':np.linspace(-4,4,839),'offsets':np.zeros((839,16),dtype=np.int32)}
        arrays,summary = subject.associate_partial({'scans':scopes},[{'support_start':0}]*5,[grid]*5,[empty]*5,kernel,
                                                   [np.zeros((16,128),dtype=np.float32)]*5)
        self.assertEqual(arrays['forced_center_local_ess'].shape,(0,6))
        self.assertEqual(summary['ON_local_catalog_rows'],0)
        self.assertFalse(summary['complete_OFF_support'])


if __name__ == '__main__':
    unittest.main()
