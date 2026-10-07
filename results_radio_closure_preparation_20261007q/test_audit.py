"""New period-summary risks only. No historical workload is run."""
import copy
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('period_audit',HERE/'audit.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.manifest,cls.sources=a.inventory(HERE.parent)
    def modified(self,path,alter):
        inputs=dict(self.sources);manifest=copy.deepcopy(self.manifest)
        value=a.strict_json(inputs[path]);alter(value);inputs[path]=a.canonical(value)
        manifest['files'][path]=a.pin(inputs[path]);return manifest,inputs
    def test_complete_blocked_summary_and_reservation_arithmetic(self):
        s,r=a.review(self.manifest,self.sources)
        self.assertFalse(s['final_period_consolidation']);self.assertFalse(s['scientific_pilot_completed'])
        self.assertEqual(len(s['admission_obligations']),11)
        self.assertEqual((r['selected_subtotal']['reserved_wall_seconds'],r['selected_subtotal']['reserved_artifact_mib']),(2920,5512))
        self.assertIsNone(s['all_project_resource_total']);self.assertFalse(r['whole_period_total_qualified'])
    def test_missing_evidence_refused(self):
        inputs=dict(self.sources);inputs.pop(a.M+'FAILURE.json')
        with self.assertRaises(a.Refusal):a.review(self.manifest,inputs)
    def test_byte_drift_refused(self):
        inputs=dict(self.sources);inputs[a.K+'UNRECOVERED.json']+=b' '
        with self.assertRaises(a.Refusal):a.review(self.manifest,inputs)
    def test_duplicate_reservation_refused(self):
        _,r=a.review(self.manifest,self.sources);r['rows'][-1]=dict(r['rows'][0])
        with self.assertRaises(a.Refusal):a.reconcile(r['rows'])
    def test_process_as_cannot_replace_artifact_unit(self):
        _,r=a.review(self.manifest,self.sources);r['rows'][0]['reserved_artifact_mib']=512
        with self.assertRaises(a.Refusal):a.reconcile(r['rows'])
    def test_rehashed_fake_authority_refused(self):
        m,s=self.modified(a.META+'admission_matrix.json',lambda x:x['authority'].update(spectral_access_authorized=True))
        with self.assertRaises(a.Refusal):a.review(m,s)
    def test_rehashed_preparation_gate_ready_refused(self):
        def alter(x):x['gates']['prospective_protocol']['status']='passed'
        m,s=self.modified('config/radio_hd189733_source_preparation_20260927.json',alter)
        with self.assertRaises(a.Refusal):a.review(m,s)
    def test_rehashed_proposal_execution_refused(self):
        def alter(x):x['cases'][0]['executed']=True
        m,s=self.modified('config/radio_whole_cadence_null_proposal_20260928.json',alter)
        with self.assertRaises(a.Refusal):a.review(m,s)
    def test_reported_access_failure_cannot_be_cleared(self):
        m,s=self.modified(a.M+'FAILURE.json',lambda x:x.update(status='PASSED'))
        with self.assertRaises(a.Refusal):a.review(m,s)
    def test_duplicate_json_cannot_hide_authority(self):
        with self.assertRaises(a.Refusal):a.strict_json(b'{"ready":true,"ready":false}')
    def test_nonfinite_summary_input_refused(self):
        with self.assertRaises(a.Refusal):a.strict_json(b'{"seconds":NaN}')


if __name__=='__main__':unittest.main(verbosity=2)
