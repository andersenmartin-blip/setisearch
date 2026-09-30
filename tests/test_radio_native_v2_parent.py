"""No-RNG capacity and manifest checks for the fresh native v2 parent."""
import copy
import hashlib
import unittest

from seti_repeater import native_v2_parent_radio as n
from seti_repeater import native_chain_engineering_radio as old
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_reference_radio import digest
from radio_receiver_adapter_common import context,ROOT
import radio_native_v2_prepare as prepare
import json


def binding(i):
    h=lambda label:digest({'native-v2-parent-test':label})
    return {'case_identity':h('case-'+str(i)),'plan_sha256':h('plan-'+str(i)),
        'context_sha256':h('context'),'source_contract_sha256':h('source'),
        'noise_law_sha256':h('law'),'role':'engineering'}


class NativeV2ParentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context=context('validation')
        cls.plans=[n.make_plan(cls.context,i) for i in range(8)]
        cls.reserved=json.loads((ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes())['cases']

    def test_exact_eight_case_caps_and_per_case_config_pins(self):
        cases=[binding(i) for i in range(8)]
        manifest,configs=n.manifest(digest('freeze'),digest('allocation'),cases)
        self.assertEqual(j.validate_manifest(manifest),manifest)
        self.assertEqual(manifest['caps']['ledger_reserve_bytes'],8*1024**2)
        self.assertEqual(manifest['caps']['evidence_bytes'],152*1024**2)
        self.assertEqual([c['checkpoint_limit'] for c in configs],[8]*8)
        self.assertTrue(all(c['existing_artifacts']=={} for c in configs))
        pins=manifest['artifact_groups']['physical']['binding_sha256']
        self.assertEqual(set(pins),{c['case_identity'] for c in cases})
        self.assertEqual(set(pins.values()),{hashlib.sha256(j.canonical(c)).hexdigest() for c in configs})

    def test_arithmetic_bounds_fit_without_silent_cap_increase(self):
        b=n.bounds()
        self.assertEqual((b.checkpoint_limit,b.physical_files_per_case),(8,48))
        self.assertEqual((b.artifact_batch_events_per_case,b.journal_events,b.journal_files),(8,168,340))
        self.assertLessEqual(b.journal_events,1536);self.assertLessEqual(b.journal_files,4096)
        self.assertEqual(b.cumulative_evidence_bytes,152*1024**2)
        self.assertFalse(n.record()['reservation_authorized'])

    def test_exact_worst_case_journal_receipts_fit_snapshot_and_cumulative_budget(self):
        model=n.worst_case_journal_model()
        self.assertEqual((model['events'],model['files']),(168,340))
        self.assertLessEqual(model['peak_revision_bytes'],128*1024)
        self.assertLessEqual(model['peak_stored_bytes_with_head_and_closure_reserve'],8*1024**2)

    def test_wrong_case_count_or_role_is_refused(self):
        cases=[binding(i) for i in range(8)]
        with self.assertRaisesRegex(ValueError,'eight-case'):
            n.manifest(digest('freeze'),digest('allocation'),cases[:-1])
        wrong=copy.deepcopy(cases);wrong[0]['role']='calibration'
        with self.assertRaises(ValueError):n.manifest(digest('freeze'),digest('allocation'),wrong)

    def test_fresh_plans_are_exact_unique_and_disjoint_from_closed_native_scope(self):
        old_plans=[old.make_plan(self.context,i) for i in range(8)]
        forbidden=self.reserved+[p['case'] for p in old_plans]
        self.assertEqual(len({p['case']['identity'] for p in self.plans}),8)
        self.assertEqual(len({p['case']['seed'] for p in self.plans}),8)
        for plan in self.plans:n.validate_plan(self.context,plan,forbidden)
        self.assertFalse({p['case']['identity'] for p in self.plans}&{p['case']['identity'] for p in old_plans})
        self.assertFalse({p['case']['seed'] for p in self.plans}&{p['case']['seed'] for p in old_plans})
        self.assertEqual([p['case']['spec'] for p in self.plans],list(old.SPECS))

    def test_plan_mutation_collision_and_other_window_are_refused_without_rng(self):
        changed=copy.deepcopy(self.plans[4]);changed['case']['spec']['total_digital_power']=501
        changed['plan_sha256']=digest({k:v for k,v in changed.items() if k!='plan_sha256'})
        with self.assertRaises(ValueError):n.validate_plan(self.context,changed,[])
        with self.assertRaisesRegex(ValueError,'collision'):
            n.validate_plan(self.context,self.plans[0],[self.plans[0]['case']])
        with self.assertRaisesRegex(ValueError,'validation'):n.make_plan(context('calibration'),0)

    def test_prepare_only_entrypoint_refuses_execution(self):
        with self.assertRaisesRegex(ValueError,'PREPARED_NOT_EXECUTABLE'):prepare.run()


if __name__=='__main__':unittest.main()
