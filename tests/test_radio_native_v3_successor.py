"""Versioned successor seams: read-only actual plan and tiny admission checks.

These tests do not activate e, create a project claim/journal/control, generate
large sources, invoke science/native cases, draw RNG or open telescope values.
"""
import copy
import hashlib
from pathlib import Path
import os
import tempfile
import types
import time
import unittest
from unittest import mock

import radio_native_v3_compact_eight_case_resource_fixture as fixture
import radio_native_v3_worker_admission as worker
import radio_native_v3_custody_observation as custody
import radio_native_v3_public_claim as claims
import radio_native_v3_prospective_spending as spending
import radio_native_v3_control_activation as activation
import radio_native_v3_compact_control_launch as launcher
import radio_native_v3_process_tree_supervisor as supervisor
import radio_native_v3_resource_finalization as finalizer
from test_radio_native_v3_public_claim import synthetic_claim,repin
from test_radio_native_v3_custody_observation import contract,populate,ledger_inventory,public_spending,retain_envelope

REPO=Path(__file__).resolve().parents[1]


def object_sha(value):
    return hashlib.sha256(fixture.canonical(value)).hexdigest()


class SuccessorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original=os.open
        def deny_old(path,*args,**kwargs):
            if isinstance(path,(str,os.PathLike)) and str(path).startswith(custody.ORIGINAL_REPOSITORY_ROOT):
                raise AssertionError('Original root must never be queried by successor')
            return original(path,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=deny_old):
            cls.plan=fixture.build_plan(REPO)
            worker._validate_plan(cls.plan,repository_root=str(REPO))
            cls.freeze={'input_sha256s':{p:v['sha256'] for p,v in custody.ARCHIVAL_INPUT_PINS.items()},
                'code_sha256s':{custody.SELF:cls.plan['code_files'][custody.SELF]['sha256']}}
            cls.archive_components=custody.observe_historical_storage(str(REPO),plan=cls.plan,
                freeze=cls.freeze,repository_root=str(REPO),execution_scope=str(REPO/'synthetic-scope-not-created'))[1]

    def test_actual_current_root_plan_and_metadata_admission(self):
        self.assertEqual(self.plan['invocation_repository_root'],str(REPO))
        self.assertEqual(self.plan['invocation_ledger_root'],str(REPO/spending.LEDGER_DIRECTORY))
        self.assertEqual(self.plan['budget_domain'],'new-current-engineering-lifetime-only')
        self.assertIs(self.plan['missing_original_storage_accounted'],False)
        self.assertIs(self.plan['original_identity_continuity_proved'],False)
        self.assertIs(self.plan['public_permanent_spend_before_dispatch_required'],True)
        self.assertEqual(set(self.archive_components),{'archive_b_metadata_copy','archive_c_metadata_copy'})
        for observed in self.archive_components.values():
            self.assertIs(observed['selected_metadata_only'],True)
            self.assertIs(observed['missing_original_storage_accounted'],False)
            self.assertIs(observed['original_identity_continuity_proved'],False)
        self.assertEqual(sum(row['kind']=='file' for v in self.archive_components.values() for row in v['rows']),19)

    def test_fixed_e_identities_and_existing_tombstones_agree(self):
        self.assertEqual(activation.NAMESPACE,claims.NAMESPACE)
        self.assertEqual(spending.NAMESPACE,claims.NAMESPACE)
        self.assertEqual(worker.ACTIVATION_NAMESPACE,claims.NAMESPACE)
        for actual in (activation.MARKER,spending.MARKER,worker.ACTIVATION_MARKER):
            self.assertEqual(actual,claims.MARKER)
        for actual in (activation.SPENT_ACTIVATIONS,spending.SPENT_ACTIVATIONS,worker.SPENT_ACTIVATIONS,custody.SPENT_ACTIVATIONS):
            self.assertEqual(actual,claims.SPENT_ACTIVATIONS)
        self.assertIn('20261003e',launcher.CONFIG_PATH)
        self.assertEqual(finalizer.EXTERNAL_STORAGE_SCHEMA,custody.JOIN_SCHEMA)
        self.assertEqual(finalizer.EXTERNAL_STORAGE_OBSERVATION_ROLES,worker.JOINT_HISTORY_COMPONENT_ROLES)

    def test_every_selected_material_and_bootstrap_pin_matches(self):
        self.assertEqual(len(fixture.CODE_FILES),len(set(fixture.CODE_FILES)))
        for path,pin in self.plan['code_files'].items():
            self.assertTrue((REPO/path).is_file(),path)
            self.assertEqual(pin,fixture.pin(REPO/path),path)
        for module in (launcher,supervisor,finalizer):
            for path,pin in module.BOOTSTRAP_SOURCE_PINS.items():
                self.assertEqual(pin,fixture.pin(REPO/path),path)
        for pin,path in ((fixture.WORKER_ADMISSION_IMPLEMENTATION_PIN,worker.SELF),
                (fixture.HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN,custody.SELF),
                (fixture.PUBLIC_CLAIM_IMPLEMENTATION_PIN,'scripts/radio_native_v3_public_claim.py'),
                (fixture.INVOCATION_SPENDING_IMPLEMENTATION_PIN,'scripts/radio_native_v3_prospective_spending.py')):
            self.assertEqual(pin,fixture.pin(REPO/path))

    def test_missing_public_claim_stops_before_scope_journal_or_dispatch(self):
        with tempfile.TemporaryDirectory(prefix='v3-missing-public-claim-') as root:
            scope=Path(root)/'scope-not-created'
            with mock.patch.object(Path,'mkdir',side_effect=AssertionError('no mutation')), \
                    mock.patch.object(fixture.subprocess,'Popen',side_effect=AssertionError('no process')):
                with self.assertRaisesRegex(ValueError,'BLOCKED_PUBLIC_PERMANENT_SPEND'):
                    fixture.run_control(scope,self.plan,{},self.freeze,{},None)
            self.assertFalse(scope.exists())
        self.assertFalse((REPO/spending.LEDGER_DIRECTORY).exists())
        self.assertFalse((REPO/claims.MARKER).exists())

    def test_actual_worker_public_claim_check_rejects_rehashed_invalid_reference(self):
        claim,args=synthetic_claim();plan={'code_files':{'scripts/radio_native_v3_public_claim.py':worker.PUBLIC_CLAIM_IMPLEMENTATION_PIN}}
        args['plan']=plan;claim['record']['plan_sha256']=object_sha(plan)
        claim_sha=repin(claim)
        dispatch={key:None for key in spending.DISPATCH_WITNESS_FIELDS}
        bundle={'schema':spending.SPENDING_BUNDLE_SCHEMA,'local_witness':args['invocation_spending'],
            'public_claim':claim,'public_claim_sha256':claim_sha,'dispatch_witness':dispatch}
        receipt={key:claim['record'][key] for key in ('activation_commit','activation_tree','activation_parent','marker_blob','marker_sha256')}
        self.assertTrue(worker._validate_public_spending(bundle,receipt,plan,args['complete_freeze'],args['execution_preread'],
            scope=args['execution_scope'],repository_root=args['repository_root']))
        claim['registry_pin']['create_only_ref']='refs/heads/rearm'
        bundle['public_claim_sha256']=repin(claim)
        with self.assertRaises(ValueError):
            worker._validate_public_spending(bundle,receipt,plan,args['complete_freeze'],args['execution_preread'],
                scope=args['execution_scope'],repository_root=args['repository_root'])

    def test_new_derived_source_domain_and_source_guards_compile_without_execution(self):
        derived=fixture.templates((REPO/fixture.CODE_FILES[0]).read_text(),REPO)
        self.assertEqual(set(derived),{'prepare.py','fresh-caller.js','lossless-helper.js'})
        compile(derived['prepare.py'],'synthetic-v3-prepare-not-executed','exec')
        for raw in derived.values():
            self.assertIn(b'radio_native_v3_',raw)
        self.assertNotEqual(fixture.source_domain(0),fixture.source_domain(1))
        self.assertIn(fixture.NAMESPACE.encode(),fixture.source_domain(0))
        self.assertEqual(worker.source_domain(0),fixture.source_domain(0))

    def test_launcher_keeps_cold_preflight_before_guard_module_loading(self):
        # Complete outer orchestration is not invoked: reads and the prospective
        # child observer are mocked, and the observer raises before any launch.
        events=[];envelope={'synthetic_spending_envelope':True}
        documents={'plan':self.plan,'complete_freeze':{},'preread':{},'activation_readback':{},'invocation_spending':envelope}
        descriptors={name:{'path':self.plan['current_public_claim_path'] if name=='invocation_spending' else 'synthetic-'+name+'.json',
            'bytes':len(fixture.canonical(value))+1,'sha256':hashlib.sha256(fixture.canonical(value)+b'\n').hexdigest()}
            for name,value in documents.items()}
        descriptors['invocation_spending']['object_sha256']=object_sha(envelope)
        config={'scope':str(REPO/'synthetic-never-launched'),'inputs':descriptors}
        by_path={str(REPO/descriptors[name]['path']):fixture.canonical(value)+b'\n' for name,value in documents.items()}
        def read(path,**kwargs):return {},by_path[str(path)]
        def preflight(plan,freeze):events.append('cold-preflight');return {'environment':{'LANG':'C'}}
        def module(*args):
            events.append('guard-module-import')
            return types.SimpleNamespace(validate_spending_bundle=lambda *args,**kwargs:events.append('public-private-envelope-check'))
        def observe(*args,**kwargs):events.append('observer-boundary');raise RuntimeError('synthetic stop before subprocess')
        with mock.patch.object(launcher,'read_pinned',side_effect=read), \
                mock.patch.object(launcher,'preflight',side_effect=preflight), \
                mock.patch.object(launcher,'_source_module',side_effect=module), \
                mock.patch.object(launcher,'observe_child',side_effect=observe), \
                mock.patch.object(launcher.subprocess,'Popen',side_effect=AssertionError('no real child')):
            with self.assertRaisesRegex(RuntimeError,'synthetic stop'):
                launcher._launch_control_once(config,time.monotonic_ns())
        self.assertEqual(events,['cold-preflight','guard-module-import','public-private-envelope-check','observer-boundary'])

    def test_current_custody_join_reaches_strict_versioned_finalizer(self):
        with tempfile.TemporaryDirectory(prefix='v3-actual-join-') as directory:
            root=Path(directory);populate(root);scope,plan,freeze=contract(root)
            envelope=public_spending(root,scope);retain_envelope(root,envelope)
            external=custody.observe_joined_storage(str(root),plan=plan,freeze=freeze,
                repository_root=str(root),execution_scope=scope,
                prospective_ledger=ledger_inventory(root,scope),public_spending=envelope)
            checked=finalizer._external_ledger_inventory({'scope':scope,'rows':[]},external)
            self.assertEqual(checked,external)
            self.assertEqual(len(checked['components']),4)
            roots=[item['root'] for item in checked['components']]
            for index,first in enumerate(roots):
                for second in roots[index+1:]:
                    self.assertFalse(first==second or first.startswith(second+'/') or second.startswith(first+'/'))
            broken=copy.deepcopy(external);broken['components'][0]['root']=scope
            with self.assertRaises(ValueError):
                finalizer._external_ledger_inventory({'scope':scope,'rows':[]},broken)
            broken=copy.deepcopy(external);broken['rows'][1]['inode']=broken['rows'][0]['inode']
            broken['rows'][1]['device']=broken['rows'][0]['device']
            with self.assertRaises(ValueError):
                finalizer._external_ledger_inventory({'scope':scope,'rows':[]},broken)

    def test_unchanged_numerical_limits_and_scientific_gates(self):
        self.assertEqual(self.plan['original_limits'],worker.ORIGINAL_LIMITS)
        self.assertEqual(self.plan['original_limits'],finalizer.LIMITS)
        for key in ('execution_authorized','scientific_execution_authorized','reservation_authorized',
                'native_case_binding_verified','host_ledger_join_complete'):
            self.assertIs(self.plan[key],False)
        for key in ('native_case_reservations','native_case_executions','scientific_cases_run','rng_draws','telescope_reads'):
            self.assertEqual(self.plan[key],0)
        changed=copy.deepcopy(self.plan);changed['retained_storage_component_roles']['historical_b_scope']='historical_scope'
        with self.assertRaises(ValueError):worker._validate_plan(changed,repository_root=str(REPO))


if __name__=='__main__':unittest.main()
