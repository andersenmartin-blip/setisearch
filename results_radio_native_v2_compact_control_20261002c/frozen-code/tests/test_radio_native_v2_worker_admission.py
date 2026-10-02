"""Synthetic supplied publication claims only; no generator or worker launch."""
import copy
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_worker_admission as admission
import radio_native_v2_runtime_custody as custody
import radio_native_v2_prospective_spending as spending
import radio_native_v2_historical_observation as history

ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(Path(sys.executable).resolve())
SCRIPT = ROOT / admission.SELF


def tiny_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def synthetic_activation_receipt(plan, freeze, proof, *, execution_scope):
    return {'schema':admission.ACTIVATION_RECEIPT_SCHEMA,
        'namespace':admission.ACTIVATION_NAMESPACE,
        'activation_commit':'2'*40,'activation_tree':'3'*40,
        'activation_parent':'1'*40,'activation_public_readback_verified':True,
        'marker_path':admission.ACTIVATION_MARKER,'marker_blob':'4'*40,
        'marker_sha256':'5'*64,
        'plan_sha256':hashlib.sha256(admission.canonical(plan)).hexdigest(),
        'complete_freeze_sha256':hashlib.sha256(admission.canonical(freeze)).hexdigest(),
        'execution_preread_sha256':hashlib.sha256(admission.canonical(proof)).hexdigest(),
        'one_control_invocation':True,
        'control_scope':str(execution_scope),
        'runtime_custody_manifest_sha256':freeze['runtime_custody_manifest_sha256'],
        'activation_only_runtime_complete':True,
        **{key:False for key in admission.ACTIVATION_DISABLED}}


def synthetic_worker_materials(root, *, ordinal=0, plan=None, derived_sources=None):
    """Reusable synthetic local proof fixture; no real public readback exists.

    Optional actual prospective plan/derived_sources support testing a pinned
    generated guard through its independent BLOCKED fixture refusal. By
    default only tiny inert derived strings are materialized. The returned
    complete freeze is structurally valid with synthetic measured versions;
    it is deliberately not an independently recomputed execution closure.
    """
    root = Path(root).absolute()
    scope = root / 'whole'; case = scope / 'cases' / f'case{ordinal:02d}'
    code = case / 'frozen-code'; derived = case / 'derived'
    code.mkdir(parents=True); derived.mkdir()
    plan = copy.deepcopy(fixture.build_plan(ROOT) if plan is None else plan)
    plan['invocation_repository_root'] = str(root)
    plan['invocation_ledger_root'] = spending.ledger_root_for_repository(root)
    # A test can construct materials before root adds the validator to its
    # shared CODE_FILES. The validator is always an explicit prospective pin.
    plan['code_files'][admission.SELF] = tiny_pin(SCRIPT.read_bytes())
    plan['code_files'][admission.CUSTODY_SOURCE] = tiny_pin((ROOT/admission.CUSTODY_SOURCE).read_bytes())
    plan['code_files'][admission.SPENDING_SOURCE] = tiny_pin((ROOT/admission.SPENDING_SOURCE).read_bytes())
    # Synthetic material roots can relocate; historical input bytes retain the
    # exact immutable published pins, without observing any original storage.
    plan['historical_storage_inputs'] = copy.deepcopy(history.HISTORICAL_INPUT_PINS)
    plan['code_files'].update(plan['historical_storage_inputs'])
    if derived_sources is None:
        derived_sources = {'prepare.py': b'# tiny synthetic inert preparation source\n',
            'fresh-caller.js': b'// tiny synthetic inert caller\n',
            'lossless-helper.js': b'// tiny synthetic inert helper\n'}
    plan['derived_code'] = {name: tiny_pin(raw) for name, raw in derived_sources.items()}
    for relative, wanted in plan['code_files'].items():
        path = code / relative; path.parent.mkdir(parents=True, exist_ok=True)
        raw = (ROOT / relative).read_bytes()
        if tiny_pin(raw) != wanted:
            raise ValueError('Synthetic materials must match supplied prospective source pins')
        path.write_bytes(raw)
    for name, raw in derived_sources.items():
        (derived / name).write_bytes(raw)
    hashes = {path: pin['sha256'] for path, pin in plan['code_files'].items()
              if not path.startswith('tests/') and path not in plan['historical_storage_inputs']}
    for relative in ('scripts/radio_native_v2_runner_freeze.py', 'scripts/radio_native_v2_broker_host.js'):
        hashes[relative] = tiny_pin((ROOT / relative).read_bytes())['sha256']
    inputs = {path: pin['sha256'] for path, pin in plan['code_files'].items()
              if path.startswith('tests/') or path in plan['historical_storage_inputs']}
    paths = {name: record['path'] for name, record in plan['runtime_executables'].items()}
    tiny_bin = root/'tiny-activation-bin'; tiny_bin.mkdir()
    tiny_git = tiny_bin/'tiny-activation-git'; tiny_git.write_bytes(b'tiny inert activation-only Git; never executed')
    tiny_core = root/'tiny-activation-core'; tiny_core.mkdir()
    tiny_material = root/'tiny-material-runtime'; tiny_material.write_bytes(b'tiny inert material runtime; never executed')
    paths['git'] = str(tiny_git)
    runtime = {path: tiny_pin(Path(path).read_bytes())['sha256'] for path in paths.values()}
    runtime[str(tiny_material)] = tiny_pin(tiny_material.read_bytes())['sha256']
    coverage = {key: False for key in ('external_tool_transport_runtime_frozen',
        'operating_system_kernel_frozen', 'git_credential_and_network_configuration_frozen',
        'git_script_interpreters_qualified', 'arbitrary_node_modules_qualified',
        'python_cached_bytecode_execution_qualified', 'python_import_source_policy_qualified')}
    coverage.update({'repository': 'synthetic structural metadata only',
        'python_numpy': 'synthetic structural metadata only',
        'git_node': 'synthetic structural metadata only',
        'qualification_scope': 'synthetic local assertions; no public readback or runtime closure'})
    freeze = {'schema': admission.FREEZE_SCHEMA, 'freeze_kind': 'COMPLETE_RUNNER_BROKER_RUNTIME',
        'mode': 'PROSPECTIVE_ENGINEERING_ONLY', 'namespace': admission.FREEZE_NAMESPACE,
        **{key: False for key in admission.FREEZE_DISABLED}, 'transport_qualification': None,
        'repository_code_inventory': sorted(hashes), 'code_sha256s': hashes,
        'input_file_inventory': sorted(inputs), 'input_sha256s': inputs,
        'runtime_file_inventory': sorted(runtime), 'runtime_sha256s': runtime,
        'executables': {name: {'invocation': path, 'resolved': path, 'sha256': runtime[path],
            'version': {'node': 'synthetic-unverified'} if name == 'node' else
                sys.version if name == 'python' else 'synthetic-unverified-git'} for name, path in paths.items()},
        'git_exec_path': str(tiny_core), 'git_runtime_file_inventory': [],
        'git_node_elf_inventory': [], 'unavailable_unused_python_extensions': {},
        'python': sys.version, 'numpy': 'synthetic-unverified',
        'environment_fingerprints': {key: None for key in admission.ENVIRONMENT_KEYS}, 'coverage': coverage}
    manifest = custody.build_manifest(runtime_paths=sorted(runtime),runtime_sha256s=runtime,
        activation_only_paths=[paths['git']],alias_roots=sorted([str(tiny_bin),str(tiny_core)]))
    freeze['runtime_custody_manifest'] = manifest
    freeze['runtime_custody_manifest_sha256'] = hashlib.sha256(custody.canonical(manifest)).hexdigest()
    proof = {'schema': admission.PREREAD_SCHEMA, 'namespace': admission.NAMESPACE,
        'plan_sha256': hashlib.sha256(admission.canonical(plan)).hexdigest(),
        'complete_freeze_sha256': hashlib.sha256(admission.canonical(freeze)).hexdigest(),
        'public_immutable_readback_verified': True, 'engineering_control_admitted': True,
        'code_files_verified': plan['code_files'], 'preparation_commit': '1' * 40,
        **admission.AUTHORITY}
    activation_receipt = synthetic_activation_receipt(plan,freeze,proof,execution_scope=scope)
    Path(plan['invocation_ledger_root']).mkdir(mode=0o700)
    witness = spending.consume_once(activation_receipt, execution_scope=str(scope),
        ledger_root=plan['invocation_ledger_root'], repository_root=str(root),
        receipt_validator=lambda receipt: (admission._validate_activation_receipt(
            receipt, plan, freeze, proof, execution_scope=str(scope)), True)[1])
    bundle = admission.build_admission_bundle(plan, freeze, proof, activation_receipt,
        repository_root=str(root), execution_scope=str(scope), ordinal=ordinal, invocation_spending=witness)
    path = case / 'worker-admission.json'
    raw = admission.bundle_bytes(bundle); path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    argv = admission.expected_worker_argv(bundle, str(path), ordinal=ordinal, expected_bundle_sha256=digest)
    return {'bundle': bundle, 'bundle_path': path, 'bundle_sha256': digest, 'argv': argv,
        'scope': scope, 'case_root': case, 'code_root': code, 'derived_root': derived,
        'plan': plan, 'freeze': freeze, 'proof': proof,
        'activation_receipt':activation_receipt, 'invocation_spending':witness}


def phase_descriptor(path):
    path = Path(path)
    return {'path': str(path), **tiny_pin(path.read_bytes())}


def tiny_prepared(materials, *, ordinal=None, case_root=None):
    """Fixed allocation metadata with a 38-byte synthetic wire, no large data.

    Archive file pins and source allocation are deliberately asserted metadata.
    These tests never establish actual source generation or transport validity.
    """
    ordinal = materials['bundle']['case_ordinal'] if ordinal is None else ordinal
    root = Path(materials['case_root'] if case_root is None else case_root)
    root.mkdir(parents=True, exist_ok=True)
    source = tiny_pin(b'tiny synthetic deterministic source ' + str(ordinal).encode())['sha256']
    identity = {'namespace': admission.NAMESPACE, 'case_ordinal': ordinal,
        'source_case_id': admission.NAMESPACE + f'/case{ordinal:02d}', 'source_sha256': source,
        'native_case_binding_verified': False}
    identity['engineering_case_binding_sha256'] = tiny_pin(admission.canonical(identity))['sha256']
    wire = bytes(range(65, 65+38)); wire_path = root/'store/items/request-000001/part'
    wire_path.parent.mkdir(parents=True); wire_path.write_bytes(wire)
    request_prefix = '{"tool":"mcp__codex_apps__github_create_tree","arguments":'
    view = {'schema': 'radio-native-v2-existing-request-view-v1', 'path': str(wire_path),
        'source_bytes':len(wire), 'source_sha256':tiny_pin(wire)['sha256'], 'offset':0,
        'bytes':len(wire), 'sha256':tiny_pin(wire)['sha256'], 'request_prefix':request_prefix,
        'request_suffix':'}', 'request_bytes':len(wire)+len(request_prefix)+1,
        'request_sha256':tiny_pin(request_prefix.encode()+wire+b'}')['sha256']}
    python = materials['plan']['runtime_executables']['python']['path']; reads = []
    for index, byte in enumerate(wire):
        argv = [python,'-I','-S','-B','-c',admission.SOURCE_READER,str(wire_path),str(index),'1']
        reads.append({'ordinal':index, 'tool':'exec_command',
            'arguments':{'cmd':shlex.join(argv),'max_output_tokens':400000,'yield_time_ms':1000},
            'path':str(wire_path),'offset':index,'bytes':1,'source_sha256':view['source_sha256'],
            'output_sha256':tiny_pin(bytes([byte]))['sha256'],'response_reserved_bytes':8205})
    prefix = materials['plan']['cases'][ordinal]['archive_prefix']; fake = tiny_pin(b'synthetic archive pin')['sha256']
    files = {prefix+f'/chunk{index:04d}.b64': {'bytes':1398104,'sha256':fake} for index in range(26)}
    files.update({prefix+'/manifest.json':{'bytes':524288,'sha256':fake},prefix+'/HEAD':{'bytes':65,'sha256':fake}})
    prepared = {'schema':'radio-native-v2-offline-maximum-prepared-v1','python':python,'scope':str(root),
        'control_case_identity':identity,'source_domain_hex':admission.source_domain(ordinal).hex(),
        'source_bytes':26*1024**2,'source_sha256':source,'archive_bytes':36875057,'archive_files':28,
        'actual_source_read_fragments':38,'conservative_source_read_fragment_ceiling':39,
        'manifest_bytes':524288,'request_view':view,'reads':reads,'files':files}
    (root/'prepared.json').write_bytes(admission.canonical(prepared)+b'\n')
    return prepared


def retain_role(materials, role, inputs, *, ordinal=0):
    bundle = admission.build_role_admission_bundle(materials['plan'],materials['freeze'],materials['proof'],
        materials['activation_receipt'],
        repository_root=materials['bundle']['invocation_repository_root'], role=role,execution_scope=str(materials['scope']),ordinal=ordinal,phase_inputs=inputs,
        invocation_spending=materials['invocation_spending'])
    layout = admission.worker_role_layout(bundle,role=role,ordinal=ordinal)
    path = Path(layout['bundle_path']); raw = admission.bundle_bytes(bundle); path.write_bytes(raw)
    digest = tiny_pin(raw)['sha256']
    argv = admission.expected_worker_argv(bundle,str(path),role=role,ordinal=ordinal,expected_bundle_sha256=digest)
    return {'bundle':bundle,'bundle_path':path,'bundle_sha256':digest,'argv':argv,'ordinal':ordinal,'role':role}


def synthetic_role_materials(root, role='caller', *, command_label='command-0'):
    """Reusable tiny V2 metadata fixture; no immutable publication is verified."""
    materials = synthetic_worker_materials(root); case = materials['case_root']
    prepared = tiny_prepared(materials)
    common = {'prepared_json':phase_descriptor(case/'prepared.json')}
    if role == 'caller': inputs = common
    elif role == 'command':
        command = prepared['reads'][int(command_label.removeprefix('command-'))]['arguments']['cmd']
        inputs = {**common,'label':command_label,'command':command,
            'source_wire':phase_descriptor(prepared['request_view']['path'])}
    elif role == 'lossless-project':
        (case/'public-evidence').mkdir()
        # Ordered original prefix is independently checked; full semantics stay false.
        transcript = {'schema':fixture.SCHEMA,'control_case_identity':prepared['control_case_identity'],
            'qualified':{},'seen':[],'deliveries':[],'read_receipts':[]}
        (case/'caller-result.json').write_text(json.dumps(transcript,separators=(',',':'))+'\n')
        recipe = [str(case),PYTHON,admission.NAMESPACE,'0',materials['plan']['cases'][0]['archive_prefix'],
            str(materials['bundle_path']),materials['bundle_sha256']]
        options = {'fullPath':str(case/'caller-result.json'),'preparedPath':str(case/'prepared.json'),
            'recipePath':str(case/'derived/prepare.py'),
            'projectionPath':str(case/'public-evidence/caller-transcript-compact-lossless.json'),
            'recipeArguments':recipe,'identityPath':str(case/'lossless-project-identity.json')}
        (case/'project-arguments.json').write_bytes(admission.canonical(options)+b'\n')
        inputs = {**common,'arguments_json':phase_descriptor(case/'project-arguments.json'),
            'caller_transcript':phase_descriptor(case/'caller-result.json'),
            'preparation_bundle':phase_descriptor(materials['bundle_path'])}
    elif role in admission.WHOLE_ROLES:
        scope = materials['scope']
        shutil.copytree(materials['code_root'],scope/'frozen-code')
        shutil.copytree(materials['derived_root'],scope/'derived')
        shutil.rmtree(scope/'cases')
        for name,key in (('plan.json','plan'),('complete-freeze.json','freeze'),('public-preread.json','proof')):
            (scope/name).write_bytes(admission.canonical(materials[key])+b'\n')
        inputs = {'plan_json':phase_descriptor(scope/'plan.json'),
            'freeze_json':phase_descriptor(scope/'complete-freeze.json'),
            'preread_json':phase_descriptor(scope/'public-preread.json')}
        if role == 'verifier':
            rows = []; prepared_cases = []
            for index in range(8):
                case_root = scope/f'cases/case{index:02d}'
                current = tiny_prepared(materials,ordinal=index,case_root=case_root)
                trace = {'schema':fixture.SCHEMA,'control_case_identity':current['control_case_identity'],
                    'qualified':{},'seen':[],'deliveries':[],'read_receipts':[]}
                path = case_root/'caller-result.json'; path.write_text(json.dumps(trace,separators=(',',':'))+'\n')
                rows.append({'ordinal':index,'source_case_id':current['control_case_identity']['source_case_id'],
                    'source_path':str(path),**tiny_pin(path.read_bytes()),'client_peak_rss_bytes':1,
                    'other_host_receipt_bytes':0,'other_host_receipt_allocated_bytes':0})
                prepared_cases.append(phase_descriptor(case_root/'prepared.json'))
            (scope/'compact-input-plan.json').write_bytes(admission.canonical(
                {'schema':'radio-native-v2-compact-retained-run-plan-v1','run_id':admission.NAMESPACE,'cases':rows})+b'\n')
            inputs.update(compact_input_plan=phase_descriptor(scope/'compact-input-plan.json'),prepared_cases=prepared_cases)
    else: raise ValueError('Tiny reusable fixture does not create large retained-source payloads')
    materials['prepared'] = prepared
    materials['role_materials'] = retain_role(materials,role,inputs,ordinal=None if role in admission.WHOLE_ROLES else 0)
    return materials


class WorkerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.materials = synthetic_worker_materials(self.root)

    def validate(self, **kwargs):
        materials = self.materials
        values = {'ordinal': materials['bundle']['case_ordinal'],
            'argv': materials['argv'], 'environment': dict(admission.CHILD_ENVIRONMENT),
            'expected_bundle_sha256': materials['bundle_sha256']}
        values.update(kwargs)
        return admission.validate_worker_admission(str(materials['bundle_path']), **values)

    def retain_changed_bundle(self, bundle=None, *, canonical=True):
        bundle = self.materials['bundle'] if bundle is None else bundle
        raw = admission.canonical(bundle) + b'\n' if canonical else json.dumps(bundle, indent=2).encode() + b'\n'
        self.materials['bundle_path'].write_bytes(raw)
        self.materials['bundle_sha256'] = hashlib.sha256(raw).hexdigest()
        self.materials['argv'][-1] = self.materials['bundle_sha256']

    def refresh_embedded_digests(self):
        bundle = self.materials['bundle']; plan = bundle['plan']; freeze = bundle['complete_freeze']; proof = bundle['public_preread']
        bundle['plan_sha256'] = proof['plan_sha256'] = hashlib.sha256(admission.canonical(plan)).hexdigest()
        bundle['complete_freeze_sha256'] = proof['complete_freeze_sha256'] = hashlib.sha256(admission.canonical(freeze)).hexdigest()
        bundle['public_preread_sha256'] = hashlib.sha256(admission.canonical(proof)).hexdigest()
        activation = bundle['activation_receipt']
        activation['plan_sha256'] = bundle['plan_sha256']
        activation['complete_freeze_sha256'] = bundle['complete_freeze_sha256']
        activation['execution_preread_sha256'] = bundle['public_preread_sha256']
        bundle['activation_receipt_sha256'] = hashlib.sha256(admission.canonical(activation)).hexdigest()
        self.retain_changed_bundle()

    def test_valid_local_supplied_claim_has_no_publication_or_execution_authority(self):
        before = sorted(str(path) for path in self.root.rglob('*'))
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('Admission never launches workers')):
            receipt = self.validate()
        self.assertEqual(receipt['status'], 'LOCAL_SUPPLIED_PREREAD_VALIDATED_EXECUTION_BLOCKED')
        self.assertTrue(receipt['exact_worker_argv_checked'])
        self.assertTrue(receipt['complete_child_environment_checked'])
        self.assertTrue(receipt['current_materialized_code_and_derived_pins_checked'])
        self.assertTrue(receipt['material_runtime_custody_rechecked'])
        self.assertEqual(receipt['runtime_custody_manifest_sha256'],self.materials['freeze']['runtime_custody_manifest_sha256'])
        self.assertFalse(receipt['activation_only_git_used_by_worker'])
        self.assertFalse(receipt['activation_only_git_aliases_enumerated_by_worker'])
        self.assertFalse(receipt['publication_claim_independently_verified'])
        self.assertFalse(receipt['complete_expected_runtime_closure_verified'])
        self.assertFalse(receipt['runtime_and_supplement_join_verified'])
        self.assertTrue(receipt['fixture_execution_guard_still_required'])
        for key, value in admission.AUTHORITY.items():
            self.assertEqual(receipt[key], value, key)
        self.assertFalse(receipt['large_source_generation_admitted'])
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob('*')))

    def test_postactivation_worker_does_not_reopen_git_or_scan_git_aliases(self):
        freeze=self.materials['freeze']; Path(freeze['executables']['git']['resolved']).unlink()
        shutil.rmtree(freeze['git_exec_path'])
        trusted=admission._custody_module()
        # Material-code enumeration remains required; only the custody checker
        # is forbidden from walking the activation-only alias roots.
        with (mock.patch.object(admission,'_custody_module',return_value=trusted),
                mock.patch.object(trusted,'build_manifest',side_effect=AssertionError('No Git alias scan')),
                mock.patch.object(trusted,'validate_activation_runtime',side_effect=AssertionError('No full activation scan')),
                mock.patch.object(subprocess,'Popen',side_effect=AssertionError('No Git or worker launch'))):
            self.assertTrue(self.validate()['material_runtime_custody_rechecked'])

    def test_material_runtime_same_bytes_replacement_or_hardlink_is_refused(self):
        material=self.root/'tiny-material-runtime'; raw=material.read_bytes()
        replacement=self.root/'replacement'; replacement.write_bytes(raw); os.replace(replacement,material)
        with mock.patch.object(subprocess,'Popen') as launch,self.assertRaises(ValueError): self.validate()
        launch.assert_not_called()
        # A separate tiny fixture retains a pristine observation until a new
        # hardlink is introduced. Installed Python/Node files are never changed.
        another=synthetic_worker_materials(self.root/'hardlink-case')
        os.link(self.root/'hardlink-case/tiny-material-runtime',self.root/'extra-material-alias')
        with self.assertRaises(ValueError):
            admission.validate_worker_admission(str(another['bundle_path']),ordinal=0,
                argv=another['argv'],environment=dict(admission.CHILD_ENVIRONMENT),
                expected_bundle_sha256=another['bundle_sha256'])

    def test_rehashed_receipt_custody_scope_ceased_bit_and_spent_identity_refuse(self):
        original=copy.deepcopy(self.materials['bundle'])
        changes=(('runtime_custody_manifest_sha256','0'*64),('activation_only_runtime_complete',False),
            ('activation_only_runtime_complete',1),('control_scope',str(self.root/'other-control')),
            ('schema',admission.ACTIVATION_RECEIPT_SCHEMA.replace('v2','v1')),
            *((key,value) for namespace,marker,commit in admission.SPENT_ACTIVATIONS
                for key,value in (('namespace',namespace),('marker_path',marker),('activation_commit',commit))))
        for key,value in changes:
            self.materials['bundle']=copy.deepcopy(original)
            self.materials['bundle']['activation_receipt'][key]=value
            self.refresh_embedded_digests()
            with self.subTest(key=key,value=value),self.assertRaises(ValueError): self.validate()

    def test_selfconsistent_manifest_cannot_replace_root_or_lifecycle_policy(self):
        original=copy.deepcopy(self.materials['bundle']); freeze=original['complete_freeze']
        alternate=self.root/'candidate-alias-root'; alternate.mkdir()
        material=str(self.root/'tiny-material-runtime')
        for mode in ('roots','classification'):
            self.materials['bundle']=copy.deepcopy(original); changed=self.materials['bundle']['complete_freeze']
            roots=[str(alternate)] if mode=='roots' else freeze['runtime_custody_manifest']['alias_roots']
            activation=[freeze['executables']['git']['resolved']]+([material] if mode=='classification' else [])
            changed['runtime_custody_manifest']=custody.build_manifest(runtime_paths=freeze['runtime_file_inventory'],
                runtime_sha256s=freeze['runtime_sha256s'],activation_only_paths=sorted(activation),alias_roots=roots)
            changed['runtime_custody_manifest_sha256']=hashlib.sha256(custody.canonical(changed['runtime_custody_manifest'])).hexdigest()
            self.materials['bundle']['activation_receipt']['runtime_custody_manifest_sha256']=changed['runtime_custody_manifest_sha256']
            self.refresh_embedded_digests()
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'policy differs'): self.validate()

    def test_candidate_custody_source_pin_cannot_replace_independent_bootstrap(self):
        bundle=self.materials['bundle']; raw=b'raise AssertionError("candidate custody code executed")\n'
        relative=admission.CUSTODY_SOURCE
        bundle['plan']['code_files'][relative]=tiny_pin(raw)
        bundle['complete_freeze']['code_sha256s'][relative]=tiny_pin(raw)['sha256']
        (self.materials['code_root']/relative).write_bytes(raw)
        self.refresh_embedded_digests()
        with mock.patch.object(subprocess,'Popen') as launch,self.assertRaisesRegex(ValueError,'independently reviewed|independent'):
            self.validate()
        launch.assert_not_called()

    def test_eight_case_ordinals_bind_exact_domains_and_case_layouts(self):
        receipt = self.validate()
        self.assertEqual(receipt['source_domain_hex'], fixture.source_domain(0).hex())
        another = synthetic_worker_materials(self.root / 'another', ordinal=7)
        result = admission.validate_worker_admission(str(another['bundle_path']), ordinal=7,
            argv=another['argv'], environment=dict(admission.CHILD_ENVIRONMENT),
            expected_bundle_sha256=another['bundle_sha256'])
        self.assertEqual(result['source_domain_hex'], fixture.source_domain(7).hex())
        self.assertTrue(result['source_case_id'].endswith('/case07'))

    def test_builder_creates_no_execution_scope_and_copies_input_metadata(self):
        fresh = self.root / 'must-remain-uncreated'
        plan = copy.deepcopy(self.materials['plan'])
        ledger_parent = self.root/'separate-synthetic-ledger'; ledger_parent.mkdir()
        plan['invocation_repository_root'] = str(ledger_parent)
        plan['invocation_ledger_root'] = spending.ledger_root_for_repository(ledger_parent)
        Path(plan['invocation_ledger_root']).mkdir(mode=0o700)
        proof = copy.deepcopy(self.materials['proof'])
        proof['plan_sha256'] = hashlib.sha256(admission.canonical(plan)).hexdigest()
        synthetic_receipt=synthetic_activation_receipt(plan,self.materials['freeze'],proof,execution_scope=fresh)
        witness = spending.consume_once(synthetic_receipt, execution_scope=str(fresh),
            ledger_root=plan['invocation_ledger_root'], repository_root=str(ledger_parent),
            receipt_validator=lambda receipt: (admission._validate_activation_receipt(
                receipt, plan, self.materials['freeze'], proof, execution_scope=str(fresh)), True)[1])
        bundle = admission.build_admission_bundle(plan, self.materials['freeze'], proof, synthetic_receipt,
            repository_root=str(ledger_parent), execution_scope=str(fresh), ordinal=2, invocation_spending=witness)
        self.assertFalse(fresh.exists())
        bundle['plan']['cases'][2]['source_bytes'] = 0
        self.assertEqual(self.materials['plan']['cases'][2]['source_bytes'], 26*1024**2)

    def test_cached_parent_bundle_digest_refuses_replacement_even_if_internal_pins_match(self):
        old = self.materials['bundle_sha256']
        self.materials['bundle']['public_preread']['preparation_commit'] = '2' * 40
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'bundle bytes changed'):
            self.validate(expected_bundle_sha256=old)

    def test_both_bundle_builders_require_independent_original_root(self):
        materials=self.materials
        args=(materials['plan'],materials['freeze'],materials['proof'],materials['activation_receipt'])
        common={'execution_scope':str(materials['scope']),'ordinal':0,
            'invocation_spending':materials['invocation_spending']}
        with self.assertRaisesRegex(TypeError,'repository_root'):
            admission.build_admission_bundle(*args,**common)
        with self.assertRaisesRegex(TypeError,'repository_root'):
            admission.build_role_admission_bundle(*args,role='caller',phase_inputs={},**common)

    def test_rehashed_plan_root_and_ledger_cannot_replace_authenticated_bundle_root(self):
        bundle=copy.deepcopy(self.materials['bundle'])
        alternate=str(self.root/'tempting-fake-original-repository')
        bundle['plan'].update(invocation_repository_root=alternate,
            invocation_ledger_root=spending.ledger_root_for_repository(alternate))
        bundle['plan_sha256']=hashlib.sha256(admission.canonical(bundle['plan'])).hexdigest()
        bundle['activation_receipt']['plan_sha256']=bundle['plan_sha256']
        bundle['activation_receipt_sha256']=hashlib.sha256(admission.canonical(bundle['activation_receipt'])).hexdigest()
        with (mock.patch.object(admission,'_custody_module') as custody_module,
                mock.patch.object(admission,'_spending_module') as spender):
            with self.assertRaisesRegex(ValueError,'independent original root'):
                admission._validate_bundle(bundle,ordinal=0)
            custody_module.assert_not_called(); spender.assert_not_called()
        self.assertFalse(Path(alternate).exists())

    def test_replacing_bundle_original_root_is_denied_by_independently_retained_argv_digest(self):
        old=self.materials['bundle_sha256']; bundle=self.materials['bundle']
        alternate=str(self.root/'tempting-fake-original-repository')
        bundle['invocation_repository_root']=alternate
        bundle['plan'].update(invocation_repository_root=alternate,
            invocation_ledger_root=spending.ledger_root_for_repository(alternate))
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError,'bundle bytes changed'):
            self.validate(expected_bundle_sha256=old)
        self.assertFalse(Path(alternate).exists())

    def test_explicit_builder_root_cannot_default_to_candidate_plan_root(self):
        materials=self.materials
        with (mock.patch.object(admission,'_custody_module') as custody_module,
                mock.patch.object(admission,'_spending_module') as spender):
            with self.assertRaisesRegex(ValueError,'independent original root'):
                admission.build_admission_bundle(materials['plan'],materials['freeze'],
                    materials['proof'],materials['activation_receipt'],
                    repository_root=str(self.root/'wrong-original'),execution_scope=str(materials['scope']),
                    ordinal=0,invocation_spending=materials['invocation_spending'])
            custody_module.assert_not_called(); spender.assert_not_called()

    def test_historical_receipts_refuse_before_custody_or_spender_io_even_with_malformed_other_evidence(self):
        for namespace,marker,commit in admission.SPENT_ACTIVATIONS:
            for key,value in (('namespace',namespace),('marker_path',marker),('activation_commit',commit)):
                bundle=copy.deepcopy(self.materials['bundle']); bundle['activation_receipt']={key:value}
                bundle['complete_freeze']={}; bundle['plan']={}
                with self.subTest(key=key,value=value):
                    with (mock.patch.object(admission,'_custody_module') as custody_module,
                            mock.patch.object(admission,'_spending_module') as spender,
                            mock.patch.object(admission,'read_pinned_file') as read):
                        with self.assertRaisesRegex(ValueError,'permanently spent'):
                            admission._validate_bundle(bundle,ordinal=0)
                        custody_module.assert_not_called(); spender.assert_not_called(); read.assert_not_called()

    def test_selfconsistent_historical_snapshot_change_cannot_replace_independent_map_pin(self):
        bundle=copy.deepcopy(self.materials['bundle']); plan=bundle['plan']
        relative=next(iter(plan['historical_storage_inputs']))
        plan['historical_storage_inputs'][relative]['sha256']='9'*64
        plan['code_files'][relative]=copy.deepcopy(plan['historical_storage_inputs'][relative])
        bundle['complete_freeze']['input_sha256s'][relative]='9'*64
        with (mock.patch.object(admission,'_custody_module') as custody_module,
                mock.patch.object(admission,'_spending_module') as spender):
            with self.assertRaisesRegex(ValueError,'independently pinned historical storage'):
                admission._validate_bundle(bundle,ordinal=0)
            custody_module.assert_not_called(); spender.assert_not_called()

    def test_historical_input_must_be_frozen_as_input_even_if_present_in_code_hashes(self):
        bundle=self.materials['bundle']; freeze=bundle['complete_freeze']
        relative=next(iter(bundle['plan']['historical_storage_inputs']))
        pin=freeze['input_sha256s'].pop(relative)
        freeze['input_file_inventory']=sorted(freeze['input_sha256s'])
        freeze['code_sha256s'][relative]=pin
        freeze['repository_code_inventory']=sorted(freeze['code_sha256s'])
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError,'independently pinned historical input'):
            self.validate()

    def test_retained_digest_is_mandatory_and_covers_the_terminal_newline(self):
        raw = self.materials['bundle_path'].read_bytes()
        for digest in (None, '1' * 64, hashlib.sha256(raw[:-1]).hexdigest()):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                self.validate(expected_bundle_sha256=digest)

    def test_canonical_json_duplicates_and_nonfinite_are_refused_even_with_matching_digest(self):
        self.retain_changed_bundle(canonical=False)
        with self.assertRaisesRegex(ValueError, 'canonical admission bundle'):
            self.validate()
        for raw in (b'{"schema":"x","schema":"y"}\n', b'{"claim":NaN}\n'):
            self.materials['bundle_path'].write_bytes(raw)
            self.materials['bundle_sha256'] = hashlib.sha256(raw).hexdigest()
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.validate()

    def test_exact_argv_refuses_extra_argument_flags_crosscase_or_wrong_domain(self):
        original = list(self.materials['argv'])
        for index, value in ((1, '-E'), (2, '-s'), (3, '-b'), (5, str(self.root / 'wrong-scope')),
                (7, 'different-namespace'), (8, '1'), (9, admission.PREFIX + '/case01-fixed'),
                (10, str(self.root / 'alternate-bundle.json')), (11, '0'*64)):
            changed = list(original); changed[index] = value
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'exact preparation worker argv'):
                self.validate(argv=changed)
        with self.assertRaises(ValueError): self.validate(argv=original + ['extra'])
        with self.assertRaises(ValueError): self.validate(role='control-worker')

    def test_minimal_complete_child_environment_refuses_injection_missing_or_numeric_values(self):
        for environment in ({**admission.CHILD_ENVIRONMENT, 'LD_PRELOAD': '/unfrozen.so'},
                {**admission.CHILD_ENVIRONMENT, 'PYTHONPATH': '/alternate'},
                {**admission.CHILD_ENVIRONMENT, 'LC_CTYPE': 'C.UTF-8'},
                {'PATH': '/usr/bin:/bin', 'LANG': 'C'},
                {**admission.CHILD_ENVIRONMENT, 'LANG': 0}):
            with self.subTest(environment=environment), self.assertRaises(ValueError):
                self.validate(environment=environment)

    def test_ordinals_refuse_boolean_float_string_or_crosscase(self):
        for ordinal in (True, 0.0, '0', -1, 8, 1):
            with self.subTest(ordinal=ordinal), self.assertRaises(ValueError):
                self.validate(ordinal=ordinal)

    def test_recomputed_metadata_hashes_do_not_hide_authority_claims(self):
        for location, key, value in (('plan', 'rng_draws', False),
                ('plan', 'execution_authorized', 0), ('plan', 'large_source_generation_admitted', True),
                ('complete_freeze', 'rng_authorized', True),
                ('public_preread', 'native_case_reservations', False),
                ('public_preread', 'public_immutable_readback_verified', 1)):
            old = copy.deepcopy(self.materials['bundle'])
            self.materials['bundle'][location][key] = value
            self.refresh_embedded_digests()
            with self.subTest(location=location, key=key), self.assertRaises(ValueError):
                self.validate()
            self.materials['bundle'] = old; self.retain_changed_bundle()

    def test_unknown_proof_fields_or_nonimmutable_commit_ids_are_refused(self):
        self.materials['bundle']['public_preread']['hidden_authority'] = True
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'proof structure'):
            self.validate()
        del self.materials['bundle']['public_preread']['hidden_authority']
        self.materials['bundle']['public_preread']['preparation_commit'] = 'main'
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'immutable public preparation commit'):
            self.validate()

    def test_activation_receipt_false_readback_authority_and_stale_pins_are_refused(self):
        for key,value in (('activation_public_readback_verified',False),
                ('automatic_retry',True),('plan_sha256','0'*64),
                ('activation_parent','not-a-commit')):
            old=copy.deepcopy(self.materials['bundle'])
            receipt=self.materials['bundle']['activation_receipt']; receipt[key]=value
            self.materials['bundle']['activation_receipt_sha256']=hashlib.sha256(
                admission.canonical(receipt)).hexdigest()
            self.retain_changed_bundle()
            with self.subTest(key=key),self.assertRaises(ValueError): self.validate()
            self.materials['bundle']=old; self.retain_changed_bundle()

    def test_crosscase_source_domain_is_refused_despite_consistent_digest_refresh(self):
        self.materials['bundle']['plan']['cases'][0]['source_domain_hex'] = fixture.source_domain(1).hex()
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'fixed case source_domain_hex'):
            self.validate()

    def test_case_shape_and_original_limits_require_exact_integer_types(self):
        self.materials['bundle']['plan']['cases'][0]['real_legacy_tail_operations'] = True
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'engineering case allocation'):
            self.validate()
        self.materials['bundle']['plan']['cases'][0]['real_legacy_tail_operations'] = 1
        self.materials['bundle']['plan']['original_limits']['case_calls'] = 128
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'original fixed resource limits'):
            self.validate()

    def test_materialized_generator_or_code_tampering_is_detected(self):
        generator = self.materials['derived_root'] / 'prepare.py'
        generator.write_bytes(b'# changed unadmitted source\n')
        with self.assertRaisesRegex(ValueError, 'materialized source prepare.py'):
            self.validate()
        generator.write_bytes(b'# tiny synthetic inert preparation source\n')
        module = self.materials['code_root'] / admission.SELF
        module.write_bytes(module.read_bytes() + b'\n# changed current bytes\n')
        with self.assertRaisesRegex(ValueError, 'materialized source scripts/radio_native_v2_worker_admission.py'):
            self.validate()

    def test_missing_extra_cache_or_fifo_material_entries_are_refused(self):
        generator = self.materials['derived_root'] / 'prepare.py'; raw = generator.read_bytes()
        generator.unlink()
        with self.assertRaisesRegex(ValueError, 'derived inventory'):
            self.validate()
        generator.write_bytes(raw)
        cache = self.materials['code_root'] / 'injected.pyc'; cache.write_bytes(b'unfrozen cached code')
        with self.assertRaisesRegex(ValueError, 'code inventory'):
            self.validate()
        cache.unlink(); os.mkfifo(cache)
        with self.assertRaisesRegex(ValueError, 'alias or special file'):
            self.validate()

    def test_unpinned_empty_material_directory_is_refused(self):
        empty = self.materials['code_root'] / 'unfrozen-empty-module-path'
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, 'code directory inventory'):
            self.validate()

    def test_existing_generator_outputs_refuse_scope_reuse_before_any_mutation(self):
        previous = self.materials['case_root'] / 'prepared.json'
        previous.write_bytes(b'{}')
        before = sorted(str(path) for path in self.root.rglob('*'))
        with self.assertRaisesRegex(ValueError, 'scope reuse refused'):
            self.validate()
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob('*')))

    def test_symlink_hardlink_and_ancestor_aliases_are_refused(self):
        generator = self.materials['derived_root'] / 'prepare.py'; alternate = self.root / 'alternate-source'
        alternate.write_bytes(generator.read_bytes()); generator.unlink(); generator.symlink_to(alternate)
        with self.assertRaises(ValueError): self.validate()
        generator.unlink(); os.link(alternate, generator)
        with self.assertRaises(ValueError): self.validate()
        alias = self.root / 'case-alias'; alias.symlink_to(self.materials['case_root'], target_is_directory=True)
        with self.assertRaises(OSError):
            admission.load_bundle(str(alias / 'worker-admission.json'),
                expected_bundle_sha256=self.materials['bundle_sha256'])

    def test_bundle_fifo_is_rejected_without_blocking(self):
        path = self.materials['bundle_path']; path.unlink(); os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'regular worker evidence'):
            self.validate()

    def test_original_freeze_omission_and_runtime_version_type_are_refused(self):
        del self.materials['bundle']['complete_freeze']['coverage']
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'complete original runner freeze structure'):
            self.validate()

    def test_canonical_path_aliases_are_refused_before_material_reads(self):
        for value in (str(self.materials['scope']) + '/.', str(self.root) + '//whole',
                      str(self.root) + '/other/../whole', 'relative/scope'):
            old = copy.deepcopy(self.materials['bundle'])
            self.materials['bundle']['execution_scope'] = value
            self.retain_changed_bundle()
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.validate()
            self.materials['bundle'] = old

    def test_check_only_cli_runs_under_isolated_python_and_creates_nothing(self):
        before = sorted(str(path) for path in self.root.rglob('*'))
        process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--check-only',
            '--bundle', str(self.materials['bundle_path']), '--bundle-sha256', self.materials['bundle_sha256'],
            '--ordinal', '0'], capture_output=True, timeout=10, env=admission.CHILD_ENVIRONMENT)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        result = json.loads(process.stdout)
        self.assertFalse(result['publication_claim_independently_verified'])
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob('*')))


class WorkerRoleAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def material(self, role='caller', **kwargs):
        self.materials = synthetic_role_materials(self.root,role,**kwargs)
        return self.materials

    def validate(self, **kwargs):
        role = self.materials['role_materials']
        arguments = {'role':role['role'],'ordinal':role['ordinal'],'argv':role['argv'],
            'environment':dict(admission.CHILD_ENVIRONMENT),'expected_bundle_sha256':role['bundle_sha256']}
        arguments.update(kwargs)
        return admission.validate_worker_admission(str(role['bundle_path']),**arguments)

    def refresh_role(self):
        old = self.materials['role_materials']
        self.materials['role_materials'] = retain_role(self.materials,old['role'],
            old['bundle']['phase_inputs'],ordinal=old['ordinal'])

    def rewrite_prepared(self, prepared):
        path = self.materials['case_root']/'prepared.json'
        path.write_bytes(admission.canonical(prepared)+b'\n')
        self.materials['role_materials']['bundle']['phase_inputs']['prepared_json'] = phase_descriptor(path)
        self.refresh_role()

    def test_caller_checks_tiny_current_prepared_snapshot_and_keeps_all_closure_false(self):
        self.material(); before = sorted(str(path) for path in self.root.rglob('*'))
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('No launch')):
            receipt = self.validate()
        self.assertTrue(receipt['role_identity_metadata_checked'])
        self.assertTrue(receipt['fresh_role_output_names_absent'])
        for key in ('full_source_domain_content_verified','complete_retained_transport_semantics_verified',
                    'publication_claim_independently_verified','complete_expected_runtime_closure_verified','execution_authorized'):
            self.assertIs(receipt[key],False)
        self.assertEqual(before,sorted(str(path) for path in self.root.rglob('*')))

    def test_role_layout_binds_node_bundle_and_receipt_paths(self):
        material = self.material(); role = material['role_materials']
        layout = admission.worker_role_layout(role['bundle'])
        self.assertEqual(layout['bundle_path'],str(material['case_root']/'caller-admission.json'))
        self.assertEqual(layout['receipt_scope'],str(material['case_root']/'caller-supervisor'))
        self.assertEqual(layout['runtime_name'],'node'); self.assertEqual(layout['seconds_limit'],600)
        self.assertEqual(role['argv'],[material['plan']['runtime_executables']['node']['path'],
            str(material['derived_root']/'fresh-caller.js'),'--caller',str(material['case_root']),
            str(role['bundle_path']),role['bundle_sha256']])

    def test_caller_preexisting_outputs_rejected_and_running_snapshot_is_explicit(self):
        material = self.material(); path = material['case_root']/'caller-start.json'; path.write_text('{}')
        with self.assertRaisesRegex(ValueError,'Existing role output'): self.validate()
        role = material['role_materials']
        receipt = admission.validate_running_caller_admission(str(role['bundle_path']),ordinal=0,
            argv=role['argv'],environment=dict(admission.CHILD_ENVIRONMENT),expected_bundle_sha256=role['bundle_sha256'])
        self.assertTrue(receipt['running_caller_snapshot_recheck'])
        self.assertFalse(receipt['fresh_role_output_names_absent'])
        self.assertFalse(receipt['live_caller_parent_identity_independently_verified'])

    def test_all_caller_terminal_and_rss_names_refuse_reuse(self):
        material = self.material()
        for name in ('caller-result.json','caller-summary.json','caller-tail.json','rss-observation-request.json','rss-observation.json'):
            path = material['case_root']/name; path.write_text('{}')
            with self.subTest(name=name), self.assertRaisesRegex(ValueError,'Existing role output'): self.validate()
            path.unlink()

    def test_exact_node_flags_role_and_bundle_digest_cannot_be_relabelled(self):
        self.material(); original = self.materials['role_materials']['argv']
        for argv in ([original[0],'--expose-gc',*original[1:]],original+['extra'],
                     [*original[:-1],'0'*64]):
            with self.subTest(argv=argv), self.assertRaisesRegex(ValueError,'exact caller worker argv'): self.validate(argv=argv)
        with self.assertRaisesRegex(ValueError,'declared worker role'): self.validate(role='lossless-project')

    def test_stale_prepared_file_pin_refused_before_material_scope_mutation(self):
        material = self.material(); path = material['case_root']/'prepared.json'; path.write_bytes(path.read_bytes()+b' ')
        before = sorted(str(path) for path in self.root.rglob('*'))
        with self.assertRaisesRegex(ValueError,'current role input'): self.validate()
        self.assertEqual(before,sorted(str(path) for path in self.root.rglob('*')))

    def test_rehashed_crosscase_domain_and_false_numeric_fields_refused(self):
        self.material(); original = copy.deepcopy(self.materials['prepared'])
        for key,value in (('source_domain_hex',admission.source_domain(1).hex()),('source_bytes',True),
                ('actual_source_read_fragments',38.0),('manifest_bytes',False)):
            changed = copy.deepcopy(original); changed[key]=value; self.rewrite_prepared(changed)
            with self.subTest(key=key), self.assertRaises(ValueError): self.validate()

    def test_rehashed_prepared_reader_arbitrary_script_or_boolean_reservation_refused(self):
        self.material(); original=copy.deepcopy(self.materials['prepared'])
        for field,value in (('arguments',{'cmd':shlex.join([PYTHON,'-I','-S','-B','-c','print("bypass")']),
                'max_output_tokens':400000,'yield_time_ms':1000}),('response_reserved_bytes',True),('ordinal',False)):
            changed=copy.deepcopy(original); changed['reads'][0][field]=value; self.rewrite_prepared(changed)
            with self.subTest(field=field), self.assertRaises(ValueError): self.validate()

    def test_archive_prefix_and_unexpected_authorization_prepared_fields_refused(self):
        self.material(); original=copy.deepcopy(self.materials['prepared'])
        changed=copy.deepcopy(original); key=next(iter(changed['files'])); changed['files']['wrong/'+key]=changed['files'].pop(key)
        self.rewrite_prepared(changed)
        with self.assertRaisesRegex(ValueError,'fixed archive paths'): self.validate()
        changed=copy.deepcopy(original); changed['execution_authorized']=True; self.rewrite_prepared(changed)
        with self.assertRaisesRegex(ValueError,'prepared metadata'): self.validate()

    def test_reader_exact_current_byte_range_and_wrapper_argv_binding(self):
        material=self.material('command'); receipt=self.validate(); role=material['role_materials']
        self.assertEqual(receipt['command_binding']['reader_ordinal'],0)
        self.assertEqual(role['argv'][5],'--exec-command-child')
        self.assertEqual(receipt['worker_role_layout']['seconds_limit'],120)
        changed=list(role['argv']); changed[5]='--command-worker'
        with self.assertRaisesRegex(ValueError,'exact command worker argv'): self.validate(argv=changed)

    def test_reader_rehashed_wire_tampering_still_refuses_prepared_pin_and_output_sha(self):
        material=self.material('command'); inputs=material['role_materials']['bundle']['phase_inputs']
        path=Path(inputs['source_wire']['path']); path.write_bytes(b'X'+path.read_bytes()[1:])
        inputs['source_wire']=phase_descriptor(path); self.refresh_role()
        with self.assertRaisesRegex(ValueError,'wire/prepared join'): self.validate()
        prepared=copy.deepcopy(material['prepared']); prepared['request_view']['source_sha256']=inputs['source_wire']['sha256']
        for row in prepared['reads']: row['source_sha256']=inputs['source_wire']['sha256']
        self.rewrite_prepared(prepared)
        with self.assertRaisesRegex(ValueError,'selected source-reader output'): self.validate()

    def test_command_label_and_literal_must_select_frozen_prepared_command(self):
        material=self.material('command'); inputs=material['role_materials']['bundle']['phase_inputs']
        inputs['command']=material['prepared']['reads'][1]['arguments']['cmd']; self.refresh_role()
        with self.assertRaisesRegex(ValueError,'selected exact prepared reader command'): self.validate()
        inputs=self.materials['role_materials']['bundle']['phase_inputs']; inputs['label']='command-00'
        with self.assertRaisesRegex(ValueError,'command label'): self.refresh_role()

    def test_command_identity_output_reuse_refused(self):
        material=self.material('command'); folder=material['case_root']/'command-observations'; folder.mkdir()
        (folder/'command-0-identity.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Existing role output'): self.validate()

    def test_tail_pinned_bootstrap_payload_and_explicit_terminal_identity_checked(self):
        material=self.material('command'); root=material['case_root']; prepared=material['prepared']
        identity=prepared['control_case_identity']
        response=json.dumps({'output':json.dumps({'control_case_identity':identity}),'isError':False},separators=(',',':'))
        value={'schema':'radio-native-v2-caller-only-tail-v2','client_sha256':'1'*64,
            'records':[{'ordinal':56,'response_json':response}]}; payload=admission.canonical(value)
        command=shlex.join([PYTHON,'-I','-S','-B','-c',admission.TAIL_BOOTSTRAP,
            str(root/'frozen-code/scripts/radio_native_v2_caller_tail.py'),
            material['plan']['code_files']['scripts/radio_native_v2_caller_tail.py']['sha256'],
            '--destination',str(root/'caller-tail.json'),'--payload-base64',base64.b64encode(payload).decode(),
            '--expected-bytes',str(len(payload)),'--expected-sha256',tiny_pin(payload)['sha256'],
            '--client-sha256','1'*64,'--terminal-ordinal','56'])
        inputs={'prepared_json':phase_descriptor(root/'prepared.json'),'label':'command-tail','command':command,'source_wire':None}
        material['role_materials']=retain_role(material,'command',inputs)
        receipt=self.validate(); self.assertFalse(receipt['command_binding']['complete_client_binding_independently_recovered'])
        changed=command.replace('"Pinned caller-tail helper source differs"','"unbound helper"')
        inputs=material['role_materials']['bundle']['phase_inputs']; inputs['command']=changed; self.refresh_role()
        with self.assertRaisesRegex(ValueError,'pinned tail bootstrap'): self.validate()

    def test_tail_matching_payload_hash_cannot_hide_wrong_terminal_case_identity(self):
        material=self.material('command'); prepared=material['prepared']; root=material['case_root']
        wrong=copy.deepcopy(prepared['control_case_identity']); wrong['case_ordinal']=7
        payload=admission.canonical({'schema':'radio-native-v2-caller-only-tail-v2','client_sha256':'1'*64,
            'records':[{'ordinal':56,'response_json':json.dumps({'output':json.dumps({'control_case_identity':wrong}),'isError':False})}]})
        command=shlex.join([PYTHON,'-I','-S','-B','-c',admission.TAIL_BOOTSTRAP,
            str(root/'frozen-code/scripts/radio_native_v2_caller_tail.py'),
            material['plan']['code_files']['scripts/radio_native_v2_caller_tail.py']['sha256'],
            '--destination',str(root/'caller-tail.json'),'--payload-base64',base64.b64encode(payload).decode(),
            '--expected-bytes',str(len(payload)),'--expected-sha256',tiny_pin(payload)['sha256'],
            '--client-sha256','1'*64,'--terminal-ordinal','56'])
        inputs={'prepared_json':phase_descriptor(root/'prepared.json'),'label':'command-tail','command':command,'source_wire':None}
        material['role_materials']=retain_role(material,'command',inputs)
        with self.assertRaisesRegex(ValueError,'retained terminal case identity'): self.validate()

    def test_project_exact_options_recipe_digest_and_trace_identity_checked(self):
        material=self.material('lossless-project'); receipt=self.validate()
        self.assertFalse(receipt['complete_retained_transport_semantics_verified'])
        path=material['case_root']/'project-arguments.json'; options=json.loads(path.read_bytes()); options['recipeArguments'][-1]='0'*64
        path.write_bytes(admission.canonical(options)+b'\n')
        material['role_materials']['bundle']['phase_inputs']['arguments_json']=phase_descriptor(path); self.refresh_role()
        with self.assertRaisesRegex(ValueError,'frozen lossless options'): self.validate()

    def test_project_noncanonical_preparation_recipe_cannot_be_admitted(self):
        material=self.material('lossless-project'); path=material['bundle_path']
        path.write_bytes(json.dumps(material['bundle'],indent=2).encode()+b'\n')
        material['role_materials']['bundle']['phase_inputs']['preparation_bundle']=phase_descriptor(path); self.refresh_role()
        with self.assertRaisesRegex(ValueError,'canonical admission bundle'): self.validate()

    def test_project_rehashed_trace_crosscase_identity_refused_without_full_parse(self):
        material=self.material('lossless-project'); path=material['case_root']/'caller-result.json'; trace=json.loads(path.read_bytes())
        trace['control_case_identity']['case_ordinal']=1; path.write_text(json.dumps(trace,separators=(',',':'))+'\n')
        material['role_materials']['bundle']['phase_inputs']['caller_transcript']=phase_descriptor(path); self.refresh_role()
        with self.assertRaisesRegex(ValueError,'leading retained caller identity'): self.validate()

    def test_retained_verifier_refuses_truncated_actual_payload_despite_matching_file_descriptor(self):
        material=self.material('lossless-project'); root=material['case_root']; prepared=material['prepared']
        projection=root/'public-evidence/caller-transcript-compact-lossless.json'
        projection.write_bytes(admission.canonical({'schema':'radio-native-v2-compact-eight-case-lossless-projection-v1',
            'fixture_only':True,'execution_authorized':False,'scientific_execution_authorized':False})+b'\n')
        payload=root/'deterministic-source.bin'; payload.write_bytes(b'tiny truncated retained source')
        options={'projectionPath':str(projection),'recipePath':str(root/'derived/prepare.py'),
            'retainedSourcePath':prepared['request_view']['path'],'retainedPayloadPath':str(payload),
            'auditPath':str(root/'public-evidence/reconstruction-audit.json'),'python':PYTHON,
            'identityPath':str(root/'lossless-verify-identity.json')}
        arguments=root/'projection-verify-arguments.json'; arguments.write_bytes(admission.canonical(options)+b'\n')
        inputs={'prepared_json':phase_descriptor(root/'prepared.json'),'arguments_json':phase_descriptor(arguments),
            'projection':phase_descriptor(projection),'source_wire':phase_descriptor(prepared['request_view']['path']),
            'deterministic_source':phase_descriptor(payload),'preparation_bundle':phase_descriptor(material['bundle_path'])}
        material['role_materials']=retain_role(material,'lossless-verify-retained',inputs)
        self.assertEqual(material['role_materials']['argv'][2],'--resource-verify-retained')
        before=sorted(str(path) for path in self.root.rglob('*'))
        with self.assertRaisesRegex(ValueError,'retained deterministic payload/prepared pin'): self.validate()
        self.assertEqual(before,sorted(str(path) for path in self.root.rglob('*')))

    def test_phase_descriptor_bounds_and_boolean_bytes_rejected_in_builder(self):
        material=self.material('caller'); inputs=copy.deepcopy(material['role_materials']['bundle']['phase_inputs'])
        for amount in (True,1.0,0,192*1024**2+1):
            inputs['prepared_json']['bytes']=amount
            with self.subTest(amount=amount), self.assertRaisesRegex(ValueError,'input byte count'):
                retain_role(material,'caller',inputs)

    def test_verifier_rehashed_current_prepared_identity_still_must_match_retained_trace(self):
        material=self.material('verifier'); path=material['scope']/'cases/case03/prepared.json'; prepared=json.loads(path.read_bytes())
        prepared['source_sha256']='0'*64; identity=prepared['control_case_identity']; identity['source_sha256']='0'*64
        del identity['engineering_case_binding_sha256']; identity['engineering_case_binding_sha256']=tiny_pin(admission.canonical(identity))['sha256']
        path.write_bytes(admission.canonical(prepared)+b'\n')
        material['role_materials']['bundle']['phase_inputs']['prepared_cases'][3]=phase_descriptor(path); self.refresh_role()
        with self.assertRaisesRegex(ValueError,'leading retained caller identity'): self.validate()

    def test_whole_control_exact_roots_none_ordinal_and_no_case_scope_reuse(self):
        material=self.material('control'); receipt=self.validate(); layout=receipt['worker_role_layout']
        self.assertIsNone(receipt['case_ordinal']); self.assertEqual(layout['receipt_scope'],str(material['scope']/'whole-control-supervisor'))
        self.assertEqual(layout['seconds_limit'],4800); self.assertEqual(layout['shared_storage_limit_bytes'],1536*1024**2)
        for ordinal in (False,0,0.0):
            with self.subTest(ordinal=ordinal), self.assertRaisesRegex(ValueError,'exactly None'): self.validate(ordinal=ordinal)
        (material['scope']/'cases').mkdir()
        with self.assertRaisesRegex(ValueError,'Existing role output'): self.validate()

    def test_whole_control_current_embedded_plan_snapshot_must_match(self):
        material=self.material('control'); path=material['scope']/'plan.json'; plan=json.loads(path.read_bytes()); plan['execution_authorized']=True
        path.write_bytes(admission.canonical(plan)+b'\n'); material['role_materials']['bundle']['phase_inputs']['plan_json']=phase_descriptor(path); self.refresh_role()
        with self.assertRaisesRegex(ValueError,'whole-scope plan_json'): self.validate()

    def test_whole_verifier_joins_eight_current_prepared_and_trace_identities(self):
        material=self.material('verifier'); receipt=self.validate()
        self.assertTrue(receipt['role_identity_metadata_checked']); self.assertFalse(receipt['complete_retained_transport_semantics_verified'])
        path=material['scope']/'cases/case03/prepared.json'; prepared=json.loads(path.read_bytes()); prepared['control_case_identity']['source_sha256']='0'*64
        path.write_bytes(admission.canonical(prepared)+b'\n')
        with self.assertRaisesRegex(ValueError,'current role input'): self.validate()

    def test_verifier_exact_integer_resource_fields_and_replay_are_refused(self):
        material=self.material('verifier'); path=material['scope']/'compact-input-plan.json'; plan=json.loads(path.read_bytes())
        plan['cases'][0]['client_peak_rss_bytes']=True; path.write_bytes(admission.canonical(plan)+b'\n')
        material['role_materials']['bundle']['phase_inputs']['compact_input_plan']=phase_descriptor(path); self.refresh_role()
        with self.assertRaisesRegex(ValueError,'resource integers'): self.validate()

    def test_role_input_symlink_hardlink_and_extra_phase_key_are_refused(self):
        material=self.material(); path=material['case_root']/'prepared.json'; alternate=self.root/'alias-prepared'; alternate.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(alternate)
        with self.assertRaises(OSError): self.validate()
        path.unlink(); os.link(alternate,path)
        with self.assertRaisesRegex(ValueError,'sole-link'): self.validate()
        material['role_materials']['bundle']['phase_inputs']['execution_authorized']=True
        with self.assertRaisesRegex(ValueError,'phase input inventory'): self.refresh_role()


if __name__ == '__main__':
    unittest.main()
