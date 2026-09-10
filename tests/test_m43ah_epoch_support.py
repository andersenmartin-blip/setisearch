import copy
import itertools
import math
import random
import unittest

import m43ah_epoch_support as study
import m43ag_boundary_obstruction as ag


def fixture(active=(0, 1), on=(20.0, 4.0, -2.0),
            receiver=(1.0, 0.5, 0.0), track=(0.0, 1.0, 0.0)):
    member = dict(record_id='member', active_epochs_zero_based=list(active),
        epoch_values_at_proxy_carrier=list(on), template_index=2,
        proxy_carrier_index=10, spectral_width_channels=1)
    measurement = dict(record_id='member', active_epochs=list(active), spectral_width=1, off={})
    profiles = {}
    for h, values in [('receiver_mean', receiver), ('candidate_track', track)]:
        rows = []
        for e in active:
            pid = f'2:10:1:{e}:{h}'
            rows.append(dict(epoch=e, available=True, complete=True, profile_id=pid,
                on_center=on[e], off_center=values[e]))
            profiles[pid] = dict(template=2, score_index=10, width=1, epoch=e,
                hypothesis=h, complete=True, on_values=[on[e]-2, on[e], on[e]-1],
                aligned_off_values=[values[e]]*3,
                off_left_values=[values[e]-1]*3, off_right_values=[values[e]+3]*3,
                interpolation_weights=[0.25]*3)
        measurement['off'][h] = dict(complete=True, defined=True, epochs=rows)
    return member, measurement, profiles


class EpochSupportTests(unittest.TestCase):
    def check(self, *args, **kwargs):
        member, measurement, profiles = fixture(*args, **kwargs)
        result = study.member_features(member, measurement)
        count = study.raw_profile_audit(member, profiles, result)
        self.assertEqual(count, 2*len(member['active_epochs_zero_based']))
        return result

    def test_two_epoch_support_is_the_weaker_epoch(self):
        result = self.check()
        self.assertEqual(result['second_epoch_on'], 4)
        self.assertEqual(result['second_epoch_excess'], 3)

    def test_three_epochs_require_second_largest_not_third(self):
        result = self.check(active=(0, 1, 2), on=(20, 4, -2))
        self.assertEqual(result['second_epoch_on'], 4)

    def test_single_epoch_outlier_does_not_supply_second_support(self):
        result = self.check(on=(1e6, 0.25, 1000), receiver=(0,0,0), track=(0,0,0))
        self.assertEqual(result['second_epoch_on'], 0.25)

    def test_inactive_epoch_never_enters_the_statistic(self):
        a = self.check(on=(20,4,-1e6))
        b = self.check(on=(20,4,1e6))
        self.assertEqual(a, b)

    def test_negative_off_does_not_reward_a_noise_dip(self):
        result = self.check(receiver=(-100,-50,0), track=(-1,-2,0))
        self.assertEqual(result['off_penalty'], [0,0])
        self.assertEqual(result['second_epoch_excess'], result['second_epoch_on'])

    def test_both_off_mappings_are_used(self):
        result = self.check(receiver=(8,0,0), track=(0,3,0))
        self.assertEqual(result['off_penalty'], [8,3])
        self.assertEqual(result['second_epoch_excess'], 1)

    def test_signed_values_and_ties_are_preserved(self):
        result = self.check(active=(0,1,2), on=(-2,-2,-5), receiver=(0,0,0), track=(0,0,0))
        self.assertEqual(result['second_epoch_on'], -2)
        self.assertEqual(result['second_epoch_excess'], -2)

    def test_subtraction_precedes_the_order_statistic(self):
        result = self.check(active=(0,1,2), on=(20,10,9), receiver=(19,0,0), track=(0,0,0))
        self.assertEqual(result['second_epoch_on'], 10)
        self.assertEqual(result['second_epoch_excess'], 9)

    def test_truth_fields_cannot_change_features(self):
        member, measurement, _ = fixture()
        expected = study.member_features(member, measurement)
        member.update(signal_present=False, associated_record_ids=[], reference_recovered=False,
                      injected_truth={'strength':1e99}, case_name='adversarial')
        measurement['signal_present'] = True
        self.assertEqual(study.member_features(member, measurement), expected)

    def test_malformed_measurements_fail_closed(self):
        for mutation in ['nan', 'inactive', 'duplicate', 'order', 'profile', 'missing', 'on', 'record', 'width']:
            m, report, _ = fixture()
            if mutation == 'nan':m['epoch_values_at_proxy_carrier'][0] = math.nan
            if mutation == 'inactive':m['active_epochs_zero_based'] = [0,3]
            if mutation == 'duplicate':m['active_epochs_zero_based'] = [0,0]
            if mutation == 'order':m['active_epochs_zero_based'] = [1,0]
            if mutation == 'profile':report['off']['receiver_mean']['epochs'][0]['profile_id'] = 'wrong'
            if mutation == 'missing':report['off']['receiver_mean']['complete'] = False
            if mutation == 'on':report['off']['candidate_track']['epochs'][0]['on_center'] += 1
            if mutation == 'record':report['record_id'] = 'wrong'
            if mutation == 'width':report['spectral_width'] = 2
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                study.member_features(m, report)

    def test_raw_profile_tampering_is_rejected(self):
        for mutation in ['missing', 'identity', 'span', 'on', 'off', 'weight', 'interpolation']:
            m, report, profiles = fixture()
            feature = study.member_features(m, report)
            p = profiles['2:10:1:0:receiver_mean']
            if mutation == 'missing':p['complete'] = False
            if mutation == 'identity':p['epoch'] = 1
            if mutation == 'span':p['on_values'].pop()
            if mutation == 'on':p['on_values'][1] += 1
            if mutation == 'off':p['aligned_off_values'][1] += 1
            if mutation == 'weight':p['interpolation_weights'][1] = -0.1
            if mutation == 'interpolation':p['off_left_values'][1] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                study.raw_profile_audit(m, profiles, feature)

    def test_feature_audit_rejects_changed_headlines_and_vectors(self):
        for mutation in ['second_epoch_on','second_epoch_excess','off_penalty','epoch_excess','active_epochs']:
            m, report, profiles = fixture()
            feature = study.member_features(m, report)
            if mutation in ['second_epoch_on','second_epoch_excess']:feature[mutation] += 1
            elif mutation == 'active_epochs':feature[mutation] = [0,2]
            else:feature[mutation][0] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                study.raw_profile_audit(m, profiles, feature)

    def test_seeded_scalar_oracle_on_all_activity_subsets(self):
        rng = random.Random(43008)
        for i in range(100):
            active = rng.choice([(0,1),(0,2),(1,2),(0,1,2)])
            on = tuple(rng.randint(-10,20)/4 for _ in range(3))
            off1 = tuple(rng.randint(-10,20)/4 for _ in range(3))
            off2 = tuple(rng.randint(-10,20)/4 for _ in range(3))
            with self.subTest(case=i):self.check(active, on, off1, off2)

    def test_changed_original_coordinate_binding_is_rejected(self):
        cases = [dict(name='s', members=[dict(record_id='r', coordinate=dict(on=1, off=2))])]
        ledger = [dict(name='s', members=[dict(record_id='r', original_m43af_coordinate=dict(on=1,off=9),
                                             second_epoch_on=3)])]
        with self.assertRaises(ValueError):study.transformed_cases(cases, ledger, 'second_epoch_on')

    def test_record_provenance_changes_are_rejected(self):
        decision = dict(freeze_commit='frozen', config_sha256='config')
        item = dict(record_sha256='seal', phase='training', name='s', native_payload_identity='native')
        record = dict(result_sha256='seal', phase='training', freeze_commit='frozen',
            config_sha256='config', summary=dict(name='s', panel='training'), native_payload_identity='native')
        study.check_record(record, item, decision)
        for key in ['result_sha256','phase','freeze_commit','config_sha256','native_payload_identity']:
            changed = copy.deepcopy(record);changed[key] = 'changed'
            with self.subTest(key=key), self.assertRaises(ValueError):study.check_record(changed,item,decision)
        changed = copy.deepcopy(record);changed['summary']['name'] = 'other'
        with self.assertRaises(ValueError):study.check_record(changed,item,decision)

    def test_recovery_accounting_tracks_all_signals_and_each_reference(self):
        def case(name, xy, signal=True, refs=(True,True)):
            return dict(name=name, panel='training', complete=True, signal_present=signal,
                reference_recovered=dict(zip(ag.REFERENCES,refs)), associated_record_ids=['m'] if signal else [],
                members=[dict(record_id='m',coordinate=dict(on=xy[0],off=xy[1]))])
        cases = [case('s1',(2,0)),case('s2',(3,-1),refs=(False,False)),case('c',(0,1),False)]
        result = ag.exact_sweep(cases,['s1'])
        result_accounting = study.recovery_accounting(cases,result)
        self.assertEqual(result_accounting['total_signal_cases'],2)
        self.assertEqual(result_accounting['all_signal_recovery_range'],[2,2])
        for row in result_accounting['zero_leak_optimal_states']:
            self.assertEqual(row['recovered_signal_cases'],['s1','s2'])
            self.assertTrue(all(v==['s2'] for v in row['reference_signal_gains'].values()))


if __name__ == '__main__':
    unittest.main()
