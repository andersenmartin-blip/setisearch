"""Hand-calculated morphology and exact retrospective replay contracts."""
import copy
import unittest

import numpy as np

from ls4m_control_morphology import (load, selections, replay_checks, concentration,
    reference_mask, peak_sample_bounds, cross_band_matches)
from seti_repeater.light_sail_residual import residual_metrics


class MorphologyTests(unittest.TestCase):
    def test_uniform_and_single_channel_excess(self):
        baseline = np.full(4, 10.)
        broad = concentration(np.full((3,4),14.),baseline)
        self.assertEqual(broad['largest_channel_fraction'],.25)
        self.assertEqual(broad['effective_positive_channels'],4.)
        narrow = concentration(np.array([[14.,10.,9.,8.]]),baseline)
        self.assertEqual(narrow['largest_channel_fraction'],1.)
        self.assertEqual(narrow['effective_positive_channels'],1.)
        self.assertEqual(narrow['positive_channel_count'],1)
        empty = concentration(np.full((3,4),9.),baseline)
        self.assertIsNone(empty['largest_channel_fraction'])
        with self.assertRaises(ValueError): concentration(np.empty((0,4)),baseline)

    def test_peak_interval_matches_native_blocks_at_all_real_scales(self):
        dt = load('config/ls4c_lhs1140_x_htr_followup.json')['expected_filterbank_header']['tsamp_s']
        for offset in (0,130000,592123):
            for seconds in (.001,.003,.01,.03,.1,.3):
                width = round(seconds/dt)
                for block in (0,1,17):
                    peak = (offset+(block+.5)*width)*dt
                    self.assertEqual(peak_sample_bounds(peak,width*dt,dt,837632),
                                     (offset+block*width,offset+(block+1)*width))

    def test_reference_mask_excludes_guard_and_inside(self):
        np.testing.assert_array_equal(np.flatnonzero(reference_mask(10,1.,[3.,6.],1.)),[0,1,7,8,9])

    def fixture(self):
        previous = load('results_ls4l_v2_vetoed_fragment_diagnostics/diagnostics.json.gz')
        records = []
        for s in selections(previous):
            old = (previous['paired_configurations'][s['uses'][0]['row_index']]['events'][s['uses'][0]['event_index']]
                   if s['uses'] else previous['fixed_window_diagnostics'][s['fixed_uses'][0]])
            records.append({**s, 'residual_metrics':{'envelope_s':s['event_window_s'],
                'scales':[{'inside_pulses':[{}]*n,'reference_pulses':[]} for n in old['off_counts']]}})
        return previous,records

    def test_exact_inventory_and_all_replay_uses(self):
        previous,records = self.fixture()
        self.assertEqual(len(records),21)
        self.assertEqual(sum(bool(r['uses']) for r in records),17)
        self.assertEqual(sum(len(r['uses']) for r in records),256)
        self.assertEqual(sum(len(r['fixed_uses']) for r in records),48)
        self.assertTrue(replay_checks(records,previous)['all_off_counts_and_vetoes_agree'])

    def test_replay_rejects_missing_duplicate_changed_counts_and_veto(self):
        previous,original = self.fixture()
        cases = [original[:-1], [original[0]]+original[:-1]]
        altered = copy.deepcopy(original)
        altered[0]['residual_metrics']['scales'][0]['inside_pulses'].append({})
        cases.append(altered)
        altered = copy.deepcopy(original); altered[0]['event_window_s'] = [0.,32.]
        cases.append(altered)
        for records in cases:
            with self.assertRaises(ValueError): replay_checks(records,previous)
        row = next(r for r in previous['paired_configurations'] if r['events'])
        row['events'][0]['stage1_off_survives'] = True
        with self.assertRaises(ValueError): replay_checks(original,previous)

    def test_reference_and_inside_impulses_are_kept_separate(self):
        settings = copy.deepcopy(load('config/ls4e_residual_qualification.json')['settings'])
        values = np.random.default_rng(114013).normal(0,1,120000)
        values[10000:10010] += 100
        values[50000:50010] += 100
        metrics = residual_metrics(values,.001,30.,70.,settings)
        first = metrics['scales'][0]
        self.assertTrue(any(abs(p['peak_time_s']-10.) < .02 for p in first['reference_pulses']))
        self.assertTrue(any(abs(p['peak_time_s']-50.) < .02 for p in first['inside_pulses']))
        self.assertFalse(any(abs(p['peak_time_s']-10.) < .02 for p in first['inside_pulses']))

    def test_cross_band_coincidences_label_shared_channels(self):
        records=[]
        for i,band in enumerate(([0,11],[10,21],[21,32])):
            records.append({'selection_id':i,'band_indices':band,'event_window_s':[10.,20.],'uses':[{}],
                'residual_metrics':{'scales':[{'requested_width_s':.1,'effective_width_s':.1,
                    'inside_pulses':[{'peak_time_s':12.}], 'reference_pulses':[]}]}})
        pairs=cross_band_matches(records)
        self.assertEqual([p['shared_native_channels'] for p in pairs],[1,0,0])
        self.assertTrue(all(p['matched_pulses']==1 for p in pairs))


if __name__ == '__main__': unittest.main()
