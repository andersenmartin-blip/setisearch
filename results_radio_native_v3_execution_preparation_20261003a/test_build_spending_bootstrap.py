"""Synthetic metadata-only operator regression; never invokes preclaim/dispatch."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

REPO=Path(__file__).resolve().parents[1]
HELPER=REPO/'results_radio_native_v3_execution_preparation_20261003a/build_spending_bootstrap.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


h=load(HELPER,'synthetic_operator')
modules={p:load(REPO/p,'synthetic_'+Path(p).stem) for p in h.SOURCE_PATHS}


def tree(entries):
    raw=b''.join((('40000' if x['mode']=='040000' else x['mode'])+' '+x['path']).encode()+b'\0'+bytes.fromhex(x['sha']) for x in entries)
    return {'sha':hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'tree':entries,'truncated':False}


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.modules=dict(modules);observer=self.modules[h.OBSERVER];claims=self.modules[h.CLAIMS]
        self.env={'PATH':'/usr/bin:/bin',**observer.ENVIRONMENT_FIXED}
        self.modules[h.ENVIRONMENT]=types.SimpleNamespace(expected_environment=lambda *args:self.env)
        python=str(Path(sys.executable).resolve());psha=hashlib.sha256(b'synthetic-python').hexdigest()
        plan={'kind':'synthetic-plan','runtime_executables':{'python':{'path':python,'bytes':123,'sha256':psha}}}
        freeze={'kind':'synthetic-freeze','executables':{'python':{'resolved':python,'sha256':psha}}}
        documents={'plan':plan,'complete_freeze':freeze,'preread':{'kind':'synthetic-preread'},'activation_readback':{'kind':'synthetic-readback'}}
        sourcepins={p:h.raw_pin((REPO/p).read_bytes()) for p in h.SOURCE_PATHS}
        docdesc={n:{'path':'results_synthetic_operator_only/'+n+'.json',**h.raw_pin(h.canonical(v)+b'\n')} for n,v in documents.items()}
        scope=str(REPO/observer.SCOPE_NAME)
        identity=h.digest({'namespace':claims.NAMESPACE,'repository':claims.REPOSITORY,'branch':claims.BRANCH,'marker_path':claims.MARKER})
        witness={'schema':claims.WITNESS_SCHEMA,'activation_identity_sha256':identity,
            'activation_receipt_sha256':'b'*64,'activation_commit':'1'*40,'control_scope':scope,
            'ledger_root':str(REPO/claims.LEDGER_DIRECTORY),
            'ledger_identity':{'device':1,'inode':2,'mode':0o700,'uid':3,'gid':4},
            'record_name':'spent-'+identity+'.json','record_sha256':'c'*64,
            'record_identity':{'device':1,'inode':5,'mode':0o600,'nlink':1,'uid':3,'gid':4,'bytes':123,'mtime_ns':6,'ctime_ns':7},
            'durable_before_workload':True,'one_invocation_spent':True}
        receipt={'activation_commit':'1'*40,'activation_tree':'2'*40,'activation_parent':'3'*40,
            'marker_blob':'4'*40,'marker_sha256':'5'*64}
        self.context={'manifest':{'documents':docdesc,'source_pins':sourcepins},'modules':self.modules,
            'documents':documents,'scope':scope,'activation_receipt':receipt,'local_witness':witness}
        self.record,self.raw=h.build_record(self.context)
        config_tree=tree([{'path':Path(claims.REGISTRY_PATH).name,'mode':'100644','sha':h.blob_sha(self.raw)}])
        root_tree=tree([{'path':'config','mode':'040000','sha':config_tree['sha']}])
        csha='6'*40
        origin={'claim_commit':{'sha':csha,'tree':{'sha':root_tree['sha']},'parents':[{'sha':'1'*40}]},
            'claim_root_tree':root_tree,'claim_config_tree':config_tree,'public_record':self.record,
            'claim_ref_readback':{'ref':claims.CLAIM_REF,'object':{'type':'commit','sha':csha}},
            'create_only_attestation':{'schema':h.ORIGIN_SCHEMA,'repository':claims.REPOSITORY,'branch':claims.BRANCH,
                'ref':claims.CLAIM_REF,'commit':csha,'operation':'mcp__codex_apps__github_create_branch',
                'creation_succeeded':True,'create_only_verified':True,'immutable_record_readback':True,'ref_readback_verified':True}}
        self.origin=origin;self.save_origin()

    def save_origin(self):
        descriptors={}
        for name,value in self.origin.items():
            p=self.root/(name+'.json');raw=h.canonical(value)+b'\n';p.write_bytes(raw)
            descriptors[name]={'path':str(p),**h.raw_pin(raw)}
        self.context['manifest']['public_origin']=descriptors

    def build(self):return h.bootstrap(self.context,self.record,self.raw)

    def test_public_record_exact_schema_raw_and_canonical_hashes(self):
        self.assertEqual(set(self.record),self.modules[h.CLAIMS].RECORD_FIELDS)
        self.assertEqual(self.raw,h.canonical(self.record)+b'\n')
        self.assertEqual(self.record['local_invocation_spending_sha256'],h.digest(self.context['local_witness']))

    def test_three_bootstrap_paths_and_all_raw_object_blob_pins(self):
        result=self.build();custody=self.modules[h.CUSTODY]
        self.assertEqual({x['path'] for x in result['files']},set(custody.CURRENT_PREDISPATCH_PATHS))
        for x in result['files']:
            raw=x['content'].encode();obj=json.loads(raw)
            self.assertEqual(h.raw_pin(raw),{k:x[k] for k in ('bytes','sha256')})
            self.assertEqual(h.digest(obj),x['canonical_object_sha256']);self.assertEqual(h.blob_sha(raw),x['git_blob_sha'])
        self.assertEqual(result['protected_files_created'],0);self.assertEqual(result['network_operations_performed'],0)
        self.assertTrue(result['origin_checked_structurally_only'])

    def test_launch_input_five_names_and_distinct_raw_vs_object_spend_pin(self):
        result=self.build();files={x['path']:x for x in result['files']}
        config=json.loads(files[self.modules[h.LAUNCHER].CONFIG_PATH]['content'])
        self.assertEqual(set(config['inputs']),self.modules[h.LAUNCHER].INPUT_NAMES)
        spend=config['inputs']['invocation_spending'];envelope=files[self.modules[h.CUSTODY].CURRENT_PUBLIC_CLAIM_PATH]
        self.assertEqual(spend['sha256'],envelope['sha256']);self.assertEqual(spend['object_sha256'],envelope['canonical_object_sha256'])
        self.assertNotEqual(spend['sha256'],spend['object_sha256'])

    def test_capsule_exact_sources_env_python_size_and_independent_digest_argv(self):
        result=self.build();observer=self.modules[h.OBSERVER]
        out=next(x for x in result['files'] if x['path']==observer.CAPSULE_PATH);capsule=json.loads(out['content'])
        self.assertEqual(set(capsule['source_pins']),observer.SOURCE_PATHS)
        self.assertEqual(capsule['environment'],self.env);self.assertEqual(capsule['python']['bytes'],123)
        self.assertEqual(result['observer_argv'][-2:],['--capsule-sha256',out['sha256']])
        self.assertFalse(capsule['authority']['scientific_execution_authorized'])

    def test_non_direct_C_parent_is_refused(self):
        self.origin['claim_commit']['parents']=[{'sha':'9'*40}];self.save_origin()
        with self.assertRaisesRegex(ValueError,'direct single-parent'):self.build()

    def test_wrong_ref_target_is_refused(self):
        self.origin['claim_ref_readback']['object']['sha']='9'*40;self.save_origin()
        with self.assertRaisesRegex(ValueError,'ref actual readback'):self.build()

    def test_changed_public_record_bytes_are_refused(self):
        self.origin['public_record']['permanent_spent']=False;self.save_origin()
        with self.assertRaisesRegex(ValueError,'registry bytes differ'):self.build()

    def test_absent_actual_create_only_attestation_cannot_be_invented(self):
        self.origin['create_only_attestation']['creation_succeeded']=False;self.save_origin()
        with self.assertRaisesRegex(ValueError,'connector origin attestation'):self.build()

    def test_raw_tree_digest_mismatch_is_refused(self):
        self.origin['claim_config_tree']['tree'][0]['sha']='9'*40;self.save_origin()
        with self.assertRaisesRegex(ValueError,'raw object digest'):self.build()

    def test_manifest_extra_authority_and_duplicate_JSON_are_refused_before_state_read(self):
        with self.assertRaises(ValueError):h.load_common({'execution_authorized':True},'preclaim')
        for raw in [b'{"x":1,"x":2}',b'{"x":NaN}']:
            with self.assertRaises(ValueError):h.parse(raw)

    def test_read_raw_refuses_symlink_or_changed_held_pin(self):
        p=self.root/'raw';p.write_bytes(b'abc');link=self.root/'link';link.symlink_to(p)
        with self.assertRaises(OSError):h.read_raw(link)
        with self.assertRaises(ValueError):h.read_raw(p,h.raw_pin(b'other'))

    def test_guarded_preclaim_is_fixed_and_does_not_execute_in_this_probe(self):
        frozen=self.context['documents']['complete_freeze'];python=frozen['executables']['python']['resolved']
        sha=h.raw_pin(HELPER.read_bytes())['sha256'];args=types.SimpleNamespace(manifest=str(self.root/'input.json'),manifest_sha256='a'*64,helper_sha256=sha)
        expected=[python,'-I','-S','-B',str(HELPER),'--guarded-preclaim','--manifest',args.manifest,
            '--manifest-sha256',args.manifest_sha256,'--helper-sha256',sha]
        seen=[]
        child_result={'schema':h.OUTPUT_SCHEMA,'stage':'preclaim','protected_original_local_preclaim_created':True,'public_claim_created':False}
        def mocked_observer(argv,env,**kwargs):
            seen.append(argv);self.assertEqual(env,self.env)
            return {'reason':None,'exit_code':0,'subreaper_scope_reaped_to_echild':True},h.canonical(child_result)+b'\n',b''
        self.modules[h.OBSERVER]=types.SimpleNamespace(observe_child=mocked_observer,RUN_SECONDS=4800)
        with mock.patch.object(sys,'orig_argv',expected),mock.patch.dict(os.environ,self.env,clear=True):
            result=h.guarded_preclaim(self.context,args)
        self.assertEqual(seen,[[python,'-I','-S','-B',str(HELPER),'--preclaim','--manifest',args.manifest,'--manifest-sha256',args.manifest_sha256]])
        self.assertEqual(result['guarded_parent_protected_files_created'],0)
        self.assertEqual(result['preclaim_result'],child_result)

    def test_guarded_preclaim_wrong_helper_pin_refuses_before_child(self):
        frozen=self.context['documents']['complete_freeze'];python=frozen['executables']['python']['resolved']
        args=types.SimpleNamespace(manifest=str(self.root/'input.json'),manifest_sha256='a'*64,helper_sha256='b'*64)
        expected=[python,'-I','-S','-B',str(HELPER),'--guarded-preclaim','--manifest',args.manifest,
            '--manifest-sha256',args.manifest_sha256,'--helper-sha256',args.helper_sha256]
        with mock.patch.object(sys,'orig_argv',expected),self.assertRaisesRegex(ValueError,'published caller pin'):
            h.guarded_preclaim(self.context,args)


if __name__=='__main__':
    watched=['config/radio_native_v3_control_activation_20261003e.activate.json',
        'config/radio_native_v3_control_spent_20261003e.claim.json',
        '.radio-native-v3-invocation-ledger-20261003e',
        'results_radio_native_v3_predispatch_20261003e',
        'results_radio_native_v3_compact_eight_input_control_20261003e']
    presence_before={p:os.path.lexists(REPO/p) for p in watched}
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BootstrapTests))
    presence_after={p:os.path.lexists(REPO/p) for p in watched}
    report={'synthetic_metadata_model_only':True,'tests_run':result.testsRun,'failures':len(result.failures),
        'errors':len(result.errors),'skips':len(result.skipped),'protected_preclaim_invocations':0,
        'live_subprocesses_from_guarded_preclaim_probe':0,'network_operations':0,
        'protected_paths_presence_before':presence_before,'protected_paths_presence_after':presence_after,
        'protected_states_absent_before_and_after':not any(presence_before.values()) and not any(presence_after.values()),
        'helper_pin':h.raw_pin(HELPER.read_bytes()),'test_pin':h.raw_pin(Path(__file__).read_bytes())}
    print(json.dumps(report,sort_keys=True))
    print(stream.getvalue(),file=sys.stderr)
    if not result.wasSuccessful():raise SystemExit(1)
