"""Resource admission and immutable-attempt regression tests; no science data."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from phase_budget import (MODE, MIN_METADATA_RESERVE_BYTES, MIN_SLOT_OVERHEAD_BYTES,
                          NotAdmitted, PhaseLedger, plan_budget)


def plan(**overrides):
    args = dict(primary_count=2, primary_bound_bytes=1000, primary_cpu_s=4,
                qa_count=2, qa_bound_bytes=2000, qa_cpu_s=5,
                exposed_count=1, exposed_bound_bytes=3000, exposed_cpu_s=6,
                exposed_qa_count=1, exposed_qa_bound_bytes=4000, exposed_qa_cpu_s=7,
                metadata_reserve_bytes=MIN_METADATA_RESERVE_BYTES, metadata_cpu_s=3,
                log_receipt_overhead_bytes=MIN_SLOT_OVERHEAD_BYTES + 1000,
                output_limit_bytes=10**7, disk_headroom_bytes=10**7, cpu_limit_s=100)
    args.update(overrides)
    return plan_budget(**args)


def receipt(**overrides):
    result = dict(wait4_reaped=True, exit_code=0, watchdog_fired=False,
                  launcher_verified=True, resource_acceptance=True,
                  whole_child_CPU_s=1.5, wall_s=2, peak_RSS_bytes=100,
                  status='RESOURCE_COMPLIANT_ONLY', errors=[], interruption=None,
                  limits={'cpu_s': 4, 'wall_s': 20, 'address_space_bytes': 1000})
    result.update(overrides)
    return result


class PhaseBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / 'fresh'

    def tearDown(self):
        self.temp.cleanup()

    def fresh(self, **overrides):
        return PhaseLedger.create(self.folder, plan(**overrides))

    def finish(self, ledger, claim, **overrides):
        args = dict(receipt=receipt(), payload_bytes=100, log_receipt_bytes=100)
        args.update(overrides)
        return ledger.complete(claim['claim_id'], **args)

    def test_exact_reservation_includes_every_phase_metadata_and_slot_overhead(self):
        p = plan()
        expected = MIN_METADATA_RESERVE_BYTES + 6*(MIN_SLOT_OVERHEAD_BYTES+1000) + 13000
        self.assertEqual(p['total_reserved_output_bytes'], expected)
        self.assertEqual(p['total_reserved_cpu_s'], 34)
        self.assertFalse(p['scientific_admission'])
        exact = plan(output_limit_bytes=expected, disk_headroom_bytes=expected, cpu_limit_s=34)
        self.assertTrue(exact['admitted'])

    def test_failure_of_each_whole_plan_capacity_precedes_directory_claim(self):
        for field, error in [('output_limit_bytes', 'OUTPUT_LIMIT'),
                             ('disk_headroom_bytes', 'DISK_HEADROOM'), ('cpu_limit_s', 'CPU_LIMIT')]:
            with self.subTest(field=field):
                p = plan(**{field: 1})
                self.assertIn(error, p['errors'])
                with self.assertRaises(NotAdmitted): PhaseLedger.create(self.folder, p)
                self.assertFalse(self.folder.exists())

    def test_small_primary_cannot_hide_later_qa_or_exposed_slots(self):
        p = plan(output_limit_bytes=100000)
        self.assertIn('OUTPUT_LIMIT', p['errors'])
        self.assertGreater(p['phases']['qa']['reserved_output_bytes'], 30000)
        with self.assertRaises(NotAdmitted): PhaseLedger.create(self.folder, p)

    def test_science_mode_rejected_before_any_mutation(self):
        with self.assertRaises(NotAdmitted): plan(mode='SCIENCE')
        with self.assertRaises(NotAdmitted): PhaseLedger.create(self.folder, plan(), mode='SCIENCE')
        self.assertFalse(self.folder.exists())

    def test_types_nonfinite_and_unreserved_events_are_rejected(self):
        for args in ({'primary_count': True}, {'qa_bound_bytes': 0}, {'exposed_cpu_s': float('nan')},
                     {'cpu_limit_s': float('inf')}, {'metadata_cpu_s': -1},
                     {'metadata_reserve_bytes': MIN_METADATA_RESERVE_BYTES-1},
                     {'log_receipt_overhead_bytes': MIN_SLOT_OVERHEAD_BYTES-1}):
            with self.subTest(args=args), self.assertRaises(ValueError): plan(**args)

    def test_tampered_admitted_flag_or_bound_is_not_trusted(self):
        for mutate in (lambda x: x.update(total_reserved_output_bytes=1),
                       lambda x: x['phases']['qa'].update(payload_bound_bytes=1),
                       lambda x: x.update(scientific_admission=True)):
            p = plan(); mutate(p)
            with self.assertRaises(ValueError): PhaseLedger.create(self.folder, p)
        self.assertFalse(self.folder.exists())

    def test_live_disk_check_before_create_and_before_next_claim(self):
        with mock.patch('phase_budget.shutil.disk_usage') as disk:
            disk.return_value.free = 1
            with self.assertRaises(NotAdmitted): self.fresh()
        self.assertFalse(self.folder.exists())
        ledger = self.fresh()
        before = ledger.snapshot()['events']
        with mock.patch('phase_budget.shutil.disk_usage') as disk:
            disk.return_value.free = 1
            with self.assertRaises(NotAdmitted): ledger.claim('primary', 'a')
        self.assertEqual(before, ledger.snapshot()['events'])

    def test_append_retains_original_claim_and_never_refunds(self):
        ledger = self.fresh()
        claim = ledger.claim('primary', 'one')
        prior = {p.name: p.read_bytes() for p in self.folder.iterdir()}
        self.finish(ledger, claim)
        for name, raw in prior.items(): self.assertEqual((self.folder/name).read_bytes(), raw)
        state = ledger.snapshot()
        self.assertEqual(state['reserved_cpu_s_retained'], 34)
        self.assertEqual(state['reserved_output_bytes_retained'], plan()['total_reserved_output_bytes'])
        with self.assertRaises(NotAdmitted): ledger.claim('primary', 'one')
        self.assertEqual(ledger.claim('primary', 'two')['slot'], 1)

    def test_pending_receipt_blocks_every_other_phase(self):
        ledger = self.fresh()
        claim = ledger.claim('primary', 'one')
        with self.assertRaises(NotAdmitted): ledger.claim('qa', 'other')
        with self.assertRaises(NotAdmitted): ledger.close()
        self.finish(ledger, claim)
        ledger.claim('qa', 'one')  # Independent QA may use its primary case id.

    def test_each_phase_has_an_independent_nonrefundable_count(self):
        ledger = self.fresh(primary_count=1, qa_count=0)
        self.finish(ledger, ledger.claim('primary', 'a'))
        with self.assertRaises(NotAdmitted): ledger.claim('primary', 'b')
        with self.assertRaises(NotAdmitted): ledger.claim('qa', 'a')
        self.assertEqual(ledger.claim('exposed', 'a')['phase'], 'exposed')

    def test_every_guard_failure_stops_the_next_attempt(self):
        faults = [dict(wait4_reaped=False), dict(exit_code=9), dict(exit_code=False),
                  dict(watchdog_fired=True), dict(launcher_verified=False),
                  dict(resource_acceptance=False), dict(whole_child_CPU_s=4.00001),
                  dict(whole_child_CPU_s=float('nan')), dict(peak_RSS_bytes=1001),
                  dict(wall_s=21), dict(interruption='KeyboardInterrupt'),
                  dict(status='PASS'), dict(errors=['FAIL']), dict(limits=None),
                  dict(limits={'cpu_s':5, 'wall_s':20, 'address_space_bytes':1000})]
        for index, fault in enumerate(faults):
            with self.subTest(fault=fault):
                path = Path(self.temp.name)/str(index)
                ledger = PhaseLedger.create(path, plan())
                c = ledger.claim('primary', 'a')
                event = self.finish(ledger, c, receipt=receipt(**fault))
                self.assertFalse(event['data']['accepted'])
                self.assertEqual(ledger.snapshot()['status'], 'STOPPED_RETAINED_NO_RETRY')
                with self.assertRaises(NotAdmitted): ledger.claim('qa', 'a')
                with self.assertRaises(NotAdmitted): self.finish(ledger, c)

    def test_payload_or_external_logs_overquota_are_durable_and_stop(self):
        for index, args in enumerate(({'payload_bytes':1001}, {'log_receipt_bytes':1001})):
            ledger = PhaseLedger.create(Path(self.temp.name)/str(index), plan())
            c = ledger.claim('primary', 'a')
            result = self.finish(ledger, c, **args)
            self.assertFalse(result['data']['accepted'])
            self.assertEqual(len(ledger.snapshot()['terminals']), 1)
            with self.assertRaises(NotAdmitted): ledger.claim('primary', 'b')

    def test_partial_error_preserves_evidence_closes_and_cannot_retry(self):
        ledger = self.fresh()
        c = ledger.claim('primary', 'a')
        result = ledger.partial_error(c['claim_id'], error='worker failed after write',
                                      payload_bytes=73, log_receipt_bytes=5)
        self.assertEqual(result['kind'], 'PARTIAL_ERROR')
        self.assertEqual(result['data']['payload_bytes'], 73)
        self.assertFalse(result['data']['reservations_refunded'])
        with self.assertRaises(NotAdmitted): ledger.claim('primary', 'b')
        closed = ledger.close()
        self.assertFalse(closed['data']['all_reserved_slots_completed_engineering_only'])
        with self.assertRaises(NotAdmitted): PhaseLedger.create(self.folder, plan())

    def test_close_is_once_only_even_when_slots_unsubmitted(self):
        ledger = self.fresh()
        self.assertFalse(ledger.close()['data']['all_reserved_slots_completed_engineering_only'])
        with self.assertRaises(NotAdmitted): ledger.claim('primary', 'a')
        with self.assertRaises(NotAdmitted): ledger.close()
        self.assertEqual(ledger.snapshot()['reserved_cpu_s_retained'], 34)

    def test_all_four_phases_can_complete_only_as_engineering(self):
        ledger = self.fresh(primary_count=1, qa_count=1)
        for phase in ('primary', 'qa', 'exposed', 'exposed_qa'):
            self.finish(ledger, ledger.claim(phase, 'fixture'))
        close = ledger.close()['data']
        self.assertTrue(close['all_reserved_slots_completed_engineering_only'])
        self.assertFalse(close['scientific_admission'])
        self.assertFalse(close['closed_banks_reusable'])

    def test_hash_chain_and_inventory_changes_fail_closed(self):
        ledger = self.fresh()
        c = ledger.claim('primary', 'a')
        target = self.folder/'000001.json'
        raw = target.read_bytes()
        value = json.loads(raw); value['data']['case_id']='tampered'
        target.write_text(json.dumps(value))
        with self.assertRaises(NotAdmitted): ledger.snapshot()
        target.write_bytes(raw)
        (self.folder/'unreserved.txt').write_text('unknown')
        with self.assertRaises(NotAdmitted): ledger.complete(c['claim_id'], receipt=receipt(), payload_bytes=0)

    def test_tail_deletion_cannot_reissue_an_attempt(self):
        ledger = self.fresh()
        ledger.claim('primary', 'a')
        (self.folder/'000001.json').unlink()
        with self.assertRaises(NotAdmitted): ledger.claim('primary', 'a')
        with self.assertRaises(NotAdmitted): ledger.snapshot()

    def test_concurrent_claims_are_serialized_before_launch(self):
        ledger = self.fresh()
        def attempt(case_id):
            try:
                return ledger.claim('primary', case_id)
            except NotAdmitted:
                return None
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, ('a', 'b')))
        self.assertEqual(sum(x is not None for x in results), 1)
        self.assertEqual(len(ledger.snapshot()['claims']), 1)


if __name__ == '__main__':
    unittest.main()
