"""Review-only handoff and zero-level comparison contracts."""
import copy
import unittest
from ls4l_vetoed_fragment_diagnostics import load,stage_input,review_annotations,KEYS
from ls4i_measured_digital_injections import event_band

C=load('config/ls4l_vetoed_fragment_diagnostics.json')
S=stage_input(C)
H=load('config/ls4c_lhs1140_x_htr_followup.json')['expected_filterbank_header']


def fixture(zero_pass=False):
    rows=[]
    for t in S['trials']:
        for amplitude in C['htr_amplitudes']:
            passed=amplitude>0 or zero_pass
            events=[]
            for m in t['matched_events']:
                e=m['event']
                events.append({'event_window_s':[e['time_start_s'],e['time_stop_s']],
                    'band_indices':event_band(e,H,C),'stage1_off_survives':False,
                    'passed':passed,'cross_scale_supported':passed,'off_veto':False,'reference_veto':False,
                    'truth_associated_pass':passed,'matched_truth_pulses':3 if passed else 0})
            rows.append({**{k:t[k] for k in KEYS},'htr_amplitude':amplitude,'events':events,
                         'stage1_matched_count':len(events),'stage1_survivor_count':0,'joint_digital_pass':False})
    return {'paired_configurations':rows,'fixed_window_diagnostics':[{} for _ in range(48)],'uninjected_baselines':[{} for _ in range(12)]}


class ReviewTests(unittest.TestCase):
    def test_complete_handoff_and_same_fragment_zero_comparison(self):
        for zero_pass in (False,True):
            result=fixture(zero_pass);before=copy.deepcopy(result)
            rows=review_annotations(result,S,C,H)
            self.assertEqual(len(rows),144)
            self.assertEqual(sum(len(r['events']) for r in rows),256)
            self.assertEqual(sum(r['review_pass_absent_at_zero_any'] for r in rows),0 if zero_pass else 54)
            self.assertTrue(all(not r['original_joint_pass'] and not r['sky_candidate_promoted'] for r in rows))
            self.assertEqual(result,before)

    def test_changed_geometry_and_original_veto_fail(self):
        for field,value in (('event_window_s',[0,32]),('band_indices',[0,3]),('stage1_off_survives',True)):
            result=fixture();row=next(r for r in result['paired_configurations'] if r['events'])
            row['events'][0][field]=value
            with self.assertRaises(ValueError):review_annotations(result,S,C,H)

    def test_missing_duplicated_or_promoted_configuration_fails(self):
        result=fixture();result['paired_configurations'].pop()
        with self.assertRaises(ValueError):review_annotations(result,S,C,H)
        result=fixture();result['paired_configurations'][0]=copy.deepcopy(result['paired_configurations'][1])
        with self.assertRaises(ValueError):review_annotations(result,S,C,H)
        result=fixture();result['paired_configurations'][0]['joint_digital_pass']=True
        with self.assertRaises(ValueError):review_annotations(result,S,C,H)

    def test_only_existing_development_htr_sources_with_bounded_budget(self):
        self.assertEqual({s['label'] for s in C['sources']},{'A1','B1'})
        self.assertEqual({s['product'] for s in C['sources']},{'high_time_resolution'})
        self.assertEqual(sum(s['source_size_bytes'] for s in C['sources']),18870174378)
        self.assertEqual(C['resource']['max_total_download_bytes'],2*18870174378)
        self.assertEqual(len(S['htr_band_indices']),10)
        self.assertFalse(C['reserved_sources_opened'])

if __name__=='__main__':unittest.main()
