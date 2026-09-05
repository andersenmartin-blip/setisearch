"""Geometry, negative controls, legacy inclusion and exact veto preservation."""
import copy
import itertools
import json
import math
from pathlib import Path
import unittest
from ls4i_measured_digital_injections import associated
from ls4j_fragment_association import fragment_associated, candidates, select, decoys

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'config/ls4j_fragment_association.json').read_text())
DETECTOR=json.loads((ROOT/'config/ls4b_lhs1140_x_light_sail.json').read_text())['medium_resolution_screen']


def box(f0=0.,f1=12.,t0=48.,t1=80.,score=10.):
    return dict(frequency_start_mhz=f0,frequency_stop_mhz=f1,time_start_s=t0,time_stop_s=t1,score=score)


class FragmentAssociationTests(unittest.TestCase):
    def test_narrow_fragment_recovery_does_not_claim_full_band(self):
        truth=box();fragment=box(3,6)
        self.assertFalse(associated(fragment,truth,.5))
        self.assertTrue(fragment_associated(fragment,truth,3))
        self.assertTrue(fragment_associated(box(0,24),truth,3))
        self.assertFalse(fragment_associated(box(0,24.01),truth,3))

    def test_resolved_overlap_and_boundary_not_sliver_or_tiny_fragment(self):
        truth=box()
        for fragment in (box(0,.1),box(11.9,14.9),box(12,15),box(-4,-1)):
            self.assertFalse(fragment_associated(fragment,truth,3))
        self.assertTrue(fragment_associated(box(10.5,13.5),truth,3))
        self.assertFalse(fragment_associated(box(10.5001,13.5001),truth,3))
        # Narrow injected truth still requires half of that truth and event.
        self.assertTrue(fragment_associated(box(0,3),box(0,2),3))

    def test_temporal_overlap_remains_bilateral(self):
        truth=box()
        self.assertTrue(fragment_associated(box(3,6,64,96),truth,3))
        for fragment in (box(3,6,64.001,96.001),box(3,6,48,49),box(3,6,0,200),box(3,6,176,208)):
            self.assertFalse(fragment_associated(fragment,truth,3))

    def test_discrete_set_oracle_and_legacy_inclusion(self):
        # Independent half-unit occupancy oracle, including bands smaller than a bin.
        for e0,e1,t0,t1 in itertools.product(range(-2,4),range(4,15),range(0,3),range(3,11)):
            event,truth=box(e0,e1),box(t0,t1)
            e=set(range(2*e0,2*e1));t=set(range(2*t0,2*t1))
            expected=(2*len(e&t)>=len(e) and 2*len(e&t)>=min(6,len(t)))
            actual=fragment_associated(event,truth,3)
            self.assertEqual(actual,expected)
            if associated(event,truth,.5): self.assertTrue(actual)

    def test_nonfinite_or_invalid_geometry_fails(self):
        for e in (box(4,3),box(0,0),box(t0=80,t1=48),box(f0=math.nan),box(t1=math.inf)):
            with self.assertRaises(ValueError): fragment_associated(e,box(),3)
        for width in (0,-1,math.inf):
            with self.assertRaises(ValueError): fragment_associated(box(),box(),width)

    def test_unchanged_score_off_and_actual_event_handoff(self):
        a={'events':[box(3,6,score=8),box(7,10,score=7.99),box(8,11,score=9)],'retention_truncated':False}
        b={'events':[box(3,6,t0=200,t1=220,score=6)],'retention_truncated':False}
        before=copy.deepcopy((a,b));items=candidates(a,b,DETECTOR)
        chosen=select(items,box(),{**CONFIG,'base_bin_width_mhz':3})
        self.assertEqual(len(chosen),2)
        self.assertEqual([c['survives_adjacent_off_veto'] for c in chosen],[True,False])
        self.assertEqual(chosen[1]['event'],a['events'][0])
        self.assertEqual(chosen[1]['adjacent_off_vetoes'],[{'off_label':'B1','off_score':6.,'frequency_overlap_fraction':1.}])
        self.assertEqual((a,b),before)

    def test_caps_fail_instead_of_truncation(self):
        with self.assertRaises(ValueError):
            candidates({'retention_truncated':True},{'retention_truncated':False},DETECTOR)
        with self.assertRaises(ValueError):
            select([{'event':box()}]*65,box(),CONFIG)

    def test_control_regions_disjoint_and_resource_inventory(self):
        for start,stop in CONFIG['envelopes_s']:
            truth=box(8494,8506,start,stop)
            controls=list(decoys(truth,CONFIG))
            self.assertEqual(len(controls),5)
            for control in controls:
                self.assertFalse(fragment_associated(truth,control,CONFIG['base_bin_width_mhz']))
                self.assertGreaterEqual(control['time_start_s'],0)
                self.assertLessEqual(control['time_stop_s'],292)
        self.assertEqual({s['label'] for s in CONFIG['sources']},{'A1','B1'})
        self.assertEqual({s['product'] for s in CONFIG['sources']},{'high_time_resolution'})
        self.assertEqual(sum(s['source_size_bytes'] for s in CONFIG['sources'])*2,CONFIG['resource']['max_total_download_bytes'])

if __name__=='__main__': unittest.main()
