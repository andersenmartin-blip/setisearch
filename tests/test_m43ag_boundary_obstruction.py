import itertools
import copy
import json
import math
from pathlib import Path
import random
import tempfile
import unittest

from m43ag_boundary_obstruction import (canonical, sha, sealed_read, exact_sweep,
    dominance_certificates, direct_audit, audit_old_grid)


def case(name, signal, coords, associated=None):
    members = [dict(record_id=str(i), coordinate=dict(on=x, off=y))
               for i, (x,y) in enumerate(coords)]
    return dict(name=name, signal_present=signal, panel='training', complete=True,
                members=members, associated_record_ids=([m['record_id'] for m in members]
                    if associated is None and signal else associated or []))


def exhaustive_rectangles(cases, required):
    """Independent complete Cartesian enumeration for small synthetic fixtures."""
    xs = {m['coordinate']['on'] for c in cases for m in c['members']}
    ys = {m['coordinate']['off'] for c in cases for m in c['members']}
    a_values = sorted(xs)+[max(xs, default=0)+1]
    b_values = sorted(ys)+[max(ys, default=0)+1]
    costs = []
    for a,b in itertools.product(a_values, b_values):
        recovered, leaked = set(), set()
        for c in cases:
            accepted = {m['record_id'] for m in c['members']
                        if m['coordinate']['on'] >= a and m['coordinate']['off'] < b}
            if c['signal_present'] and accepted.intersection(c['associated_record_ids']):
                recovered.add(c['name'])
            if not c['signal_present'] and accepted:
                leaked.add(c['name'])
        costs.append((len(set(required)-recovered), len(leaked)))
    return (min(loss for loss, leak in costs if leak == 0),
            min((leak for loss, leak in costs if loss == 0), default=None))


class BoundaryObstructionTests(unittest.TestCase):
    def check(self, cases, required):
        result = exact_sweep(cases, required)
        certs = dominance_certificates(cases, required)
        direct_audit(cases, result, certs, required)
        expected = exhaustive_rectangles(cases, required)
        self.assertEqual((result['minimum_required_losses_with_zero_leaks'],
                          result['minimum_leaking_cases_with_all_required']), expected)
        return result, certs

    def test_equal_coordinates_force_leak_including_strict_off_tie(self):
        result, certs = self.check([case('s', True, [(2,1)]), case('c', False, [(2,1)])], ['s'])
        self.assertEqual(result['minimum_required_losses_with_zero_leaks'], 1)
        self.assertEqual(result['minimum_leaking_cases_with_all_required'], 1)
        self.assertTrue(certs[0]['individually_impossible_without_leaks'])

    def test_negative_coordinates_and_lower_inclusivity(self):
        result, _ = self.check([case('s', True, [(-1,-2)]), case('c', False, [(-1,-1)])], ['s'])
        self.assertEqual(result['minimum_required_losses_with_zero_leaks'], 0)

    def test_one_undominated_member_suffices_for_case(self):
        _, certs = self.check([case('s', True, [(0,0),(2,-1)]), case('c', False, [(1,0)])], ['s'])
        self.assertFalse(certs[0]['individually_impossible_without_leaks'])
        self.assertEqual(certs[0]['undominated_member_ids'], ['1'])

    def test_unassociated_signal_member_does_not_recover_case(self):
        result, _ = self.check([case('s', True, [(0,0),(9,-9)], ['0']),
                               case('c', False, [(1,-1)])], ['s'])
        self.assertEqual(result['minimum_required_losses_with_zero_leaks'], 1)

    def test_no_eligible_association_is_explicit_impossibility(self):
        result, certs = self.check([case('s', True, [], []), case('c', False, [])], ['s'])
        self.assertIsNone(result['minimum_leaking_cases_with_all_required'])
        self.assertEqual(certs[0]['reason'], 'no_eligible_associated_members')

    def test_empty_controls_supply_no_tail_observations(self):
        result, _ = self.check([case('s', True, [(0,-1)]), case('c', False, [])], ['s'])
        self.assertEqual(result['minimum_required_losses_with_zero_leaks'], 0)
        self.assertEqual(result['minimum_leaking_cases_with_all_required'], 0)

    def test_multiple_members_count_one_leaking_case(self):
        result, _ = self.check([case('s', True, [(0,0)]),
                               case('c', False, [(1,0),(2,-1),(3,-2)])], ['s'])
        self.assertEqual(result['minimum_leaking_cases_with_all_required'], 1)

    def test_joint_rectangle_conflict_without_individual_dominance(self):
        # Each signal can separately avoid c; one rectangle recovering both cannot.
        result, certs = self.check([case('s1', True, [(0,-2)]), case('s2', True, [(2,0)]),
                                   case('c', False, [(1,-1)])], ['s1','s2'])
        self.assertTrue(all(not c['individually_impossible_without_leaks'] for c in certs))
        self.assertEqual(result['minimum_required_losses_with_zero_leaks'], 1)

    def test_seeded_fixtures_match_all_rectangles(self):
        rng = random.Random(43007)
        for i in range(100):
            cases = []
            for j in range(5):
                coords = [(rng.randint(-2,2), rng.randint(-2,2)) for _ in range(rng.randrange(5))]
                associated = [str(k) for k in range(len(coords)) if rng.random() < .7] if j < 3 else []
                cases.append(case(str(j), j < 3, coords, associated))
            with self.subTest(i=i):
                self.check(cases, ['0','1','2'])

    def test_malformed_evidence_fails_closed(self):
        for mutation in ('nan', 'undefined', 'duplicate', 'validation', 'incomplete'):
            cases = [case('s', True, [(1,0)]), case('c', False, [])]
            if mutation == 'nan':cases[0]['members'][0]['coordinate']['on'] = math.nan
            if mutation == 'undefined':cases[0]['members'][0]['coordinate'] = None
            if mutation == 'duplicate':cases[0]['members'] *= 2
            if mutation == 'validation':cases[0]['panel'] = 'validation'
            if mutation == 'incomplete':cases[0]['complete'] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                exact_sweep(cases, ['s'])

    def test_certificate_tampering_is_rejected(self):
        cases = [case('s', True, [(0,0)]), case('c', False, [(1,-1)])]
        result = exact_sweep(cases, ['s'])
        certs = dominance_certificates(cases, ['s'])
        certs[0]['blocked_members'][0]['control_coordinate']['off'] = 100
        with self.assertRaises(ValueError):direct_audit(cases, result, certs, ['s'])

    def test_missing_cut_is_rejected(self):
        cases = [case('s', True, [(0,0)]), case('c', False, [(1,-1)])]
        result = exact_sweep(cases, ['s'])
        certs = dominance_certificates(cases, ['s'])
        result['sweep'].pop()
        with self.assertRaises(ValueError):direct_audit(cases, result, certs, ['s'])

    def test_headline_and_inventory_tampering_is_rejected(self):
        cases = [case('s', True, [(0,0)]), case('c', False, [(1,-1)])]
        original = exact_sweep(cases, ['s'])
        certs = dominance_certificates(cases, ['s'])
        changes = {
            'minimum_required_losses_with_zero_leaks': 0,
            'minimum_leaking_cases_with_all_required': 0,
            'control_free_optimal_state_indices': [],
            'all_required_optimal_state_indices': [],
            'on_cut_equivalence_classes': 999,
            'non_signal_cases': [],
        }
        for key, value in changes.items():
            result = copy.deepcopy(original)
            result[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                direct_audit(cases, result, certs, ['s'])

    def test_certificate_reason_tampering_is_rejected(self):
        cases = [case('s', True, [(0,0)]), case('c', False, [(1,-1)])]
        result = exact_sweep(cases, ['s'])
        certs = dominance_certificates(cases, ['s'])
        certs[0]['reason'] = 'no_eligible_associated_members'
        with self.assertRaises(ValueError):direct_audit(cases, result, certs, ['s'])

    def test_audit_cannot_drop_a_required_case(self):
        cases = [case('s1', True, [(0,0)]), case('s2', True, [(2,-2)]),
                 case('c', False, [(1,-1)])]
        result = exact_sweep(cases, ['s2'])
        certs = dominance_certificates(cases, ['s2'])
        with self.assertRaises(ValueError):
            direct_audit(cases, result, certs, ['s1','s2'])

    def test_grid_audit_reports_impossible_recovery(self):
        cases = [case('s', True, []), case('c', False, [])]
        grid = dict(required_signal_cases=['s'], grid=[dict(
            boundary=dict(on_lower=None, off_upper=None), required_signal_losses=['s'],
            leaking_control_or_baseline_cases=[], recovered_signal_cases=0, feasible=False)])
        result = audit_old_grid(cases, grid, ['s'])
        self.assertEqual(result['minimum_required_losses_with_zero_leaks'], 1)
        self.assertIsNone(result['minimum_leaking_cases_with_all_required'])

    def test_nondeterministic_valid_witness_is_rejected(self):
        cases = [case('s', True, [(0,0)]), case('c', False, [(1,-1),(2,-2)])]
        result = exact_sweep(cases, ['s'])
        certs = dominance_certificates(cases, ['s'])
        witness = certs[0]['blocked_members'][0]
        witness['control_record_id'] = '1'
        witness['control_coordinate'] = dict(on=2, off=-2)
        with self.assertRaises(ValueError):direct_audit(cases, result, certs, ['s'])

    def test_source_seal_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'record.json'
            value = dict(measurement=3)
            value['result_sha256'] = sha(canonical(value))
            path.write_bytes(canonical(value))
            self.assertEqual(sealed_read(path), value)
            value['measurement'] = 4
            path.write_bytes(canonical(value))
            with self.assertRaises(ValueError):sealed_read(path)


if __name__ == '__main__':
    unittest.main()
