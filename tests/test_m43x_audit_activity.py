import copy
import unittest
from m43x_audit_report_v2 import verify_member_activity_identity

class AuditActivityTests(unittest.TestCase):
    def test_two_epoch_truth_with_additional_three_epoch_hypothesis(self):
        rec={'case':{'active_epochs':[0,2]},'reference_audit':{'members':[
            {'record_id':'truth','active_epochs_zero_based':[0,2]},
            {'record_id':'other','active_epochs_zero_based':[0,1,2]}]},
            'policy_decisions':{'epoch_confirmation':[
                {'record_id':'truth','passes_evaluated_physical_vetoes':True},
                {'record_id':'other','passes_evaluated_physical_vetoes':False}],
                'remaining_aggregate':[
                {'record_id':'truth','passes_evaluated_physical_vetoes':True},
                {'record_id':'other','passes_evaluated_physical_vetoes':True}]}}
        verify_member_activity_identity(rec)
        bad=copy.deepcopy(rec);bad['policy_decisions']['remaining_aggregate'][0]['passes_evaluated_physical_vetoes']=False
        with self.assertRaises(AssertionError):verify_member_activity_identity(bad)
        bad=copy.deepcopy(rec);bad['policy_decisions']['remaining_aggregate'].pop()
        with self.assertRaises(AssertionError):verify_member_activity_identity(bad)

if __name__=='__main__':unittest.main()
