"""Capacity estimates checked against actual small durable store histories."""
import copy
from pathlib import Path
import tempfile
import unittest
from seti_repeater import whole_cadence_capacity_radio as c
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_reference_radio import digest


def fixture(count=3):
    m={'schema':j.SCHEMA,'mode':'engineering','namespace':'capacity-arithmetic-fixture-only',
       'execution_binding_sha256':digest('capacity-runtime-fixture'),
       'allocation_sha256':digest('not-an-allocation'),
       'cases':[{'case_identity':digest(['fixture',i]),'plan_sha256':digest(['plan',i]),
                 'context_sha256':digest('context'),'source_contract_sha256':digest('source'),
                 'noise_law_sha256':digest('no-values'),'role':'engineering'} for i in range(count)],
       'caps':{**j.CAPS,'active_milliseconds':10000,'evidence_bytes':1024**2,'ledger_reserve_bytes':65536},
       'required_artifacts':['a.json','b.bin']}
    rs=[{'case_identity':r['case_identity'],'milliseconds':1000,'artifact_bytes':1000} for r in m['cases']]
    return m,rs


class CapacityTests(unittest.TestCase):
    def test_matches_actual_retained_revision_file_sizes_with_zero_bytes_and_clock(self):
        for count in (1,3):
            m,rs=fixture(count);expected=c.project(m,rs)
            with tempfile.TemporaryDirectory() as directory:
                root=Path(directory);store=j.DirectoryStore.create(root/'store',m)
                for i,r in enumerate(rs):
                    cp=store.read();lease=j.consume(store,expected_revision=cp.revision,
                        expected_manifest_sha256=digest(m),binding=m['cases'][i],milliseconds=r['milliseconds'],
                        artifact_bytes=r['artifact_bytes'],directory=root/f'case{i}',clock=lambda:0.)
                    lease.write_artifact('a.json',b'');lease.write_artifact('b.bin',b'');lease.finish()
                sizes=[p.stat().st_size for p in (root/'store/revisions').iterdir()]
                self.assertEqual(sum(sizes),expected['all_revisions_lower_bound_bytes'])
                self.assertEqual(len(sizes),expected['revision_count'])
                self.assertEqual(max(sizes),expected['latest_snapshot_lower_bound_bytes'])

    def test_larger_real_payload_receipts_exceed_lower_bound(self):
        m,rs=fixture(1);expected=c.project(m,rs)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);s=j.DirectoryStore.create(root/'store',m);cp=s.read()
            lease=j.consume(s,expected_revision=cp.revision,expected_manifest_sha256=digest(m),
                binding=m['cases'][0],milliseconds=1000,artifact_bytes=1000,directory=root/'case',clock=lambda:0.)
            lease.write_artifact('a.json',b'x'*100);lease.write_artifact('b.bin',b'x'*100);lease.finish()
            self.assertGreater(sum(p.stat().st_size for p in (root/'store/revisions').iterdir()),expected['all_revisions_lower_bound_bytes'])

    def test_small_latest_snapshot_does_not_hide_all_revision_overflow(self):
        m,rs=fixture(20)
        m['caps']['active_milliseconds']=20000;r=c.project(m,rs)
        self.assertLess(r['latest_snapshot_lower_bound_bytes'],m['caps']['ledger_reserve_bytes'])
        self.assertGreater(r['all_revisions_lower_bound_bytes'],m['caps']['ledger_reserve_bytes'])
        self.assertEqual(r['status'],'BLOCKED_LOWER_BOUND_EXCEEDS_LEDGER_RESERVE')
        self.assertFalse(r['execution_authorized'])

    def test_under_bound_never_authorizes_execution(self):
        m,rs=fixture(1);r=c.project(m,rs)
        self.assertEqual(r['status'],'NOT_QUALIFIED_LOWER_BOUND_ONLY');self.assertFalse(r['allocation_charged'])

    def test_scientific_projection_counts_rng_and_external_receipts_without_store(self):
        m,rs=fixture(151);m['mode']='scientific';m['caps']=dict(j.CAPS)
        for i,row in enumerate(m['cases']):row['role']='calibration' if i<127 else 'evaluation'
        r=c.project(m,rs)
        self.assertEqual(r['event_count'],151*5)
        self.assertEqual(r['revision_count'],151*5+1)
        events=list(c.minimal_events(m,m['cases'][0],1000,1000))
        self.assertEqual(events[1]['kind'],'rng_start')
        self.assertEqual(events[2]['publication']['location'],'x')
        self.assertFalse(r['store_created'])

    def test_missing_or_reordered_reservations_rejected(self):
        m,rs=fixture()
        for bad in (rs[:-1],list(reversed(rs))):
            with self.assertRaises(ValueError):c.project(m,bad)

    def test_bool_and_zero_budget_rejected(self):
        m,rs=fixture()
        for bad in (True,0):
            rows=copy.deepcopy(rs);rows[0]['artifact_bytes']=bad
            with self.assertRaises(ValueError):c.project(m,rows)

    def test_cumulative_reservation_cap_is_not_reset(self):
        m,rs=fixture();m['caps']['active_milliseconds']=1000
        with self.assertRaisesRegex(ValueError,'ceiling'):c.project(m,rs)

    def test_inputs_are_not_changed(self):
        m,rs=fixture();before=copy.deepcopy((m,rs));c.project(m,rs)
        self.assertEqual((m,rs),before)


if __name__=='__main__':unittest.main()
