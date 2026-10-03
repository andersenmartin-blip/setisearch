"""Tiny filesystem refusal/readback fixtures, no original E or data generation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name('public_lossless_reconstruct_v3.py')
SPEC = importlib.util.spec_from_file_location('offline_decoder_v3', SOURCE)
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)


class OutputSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='offline-v3-tests-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / 'repo'
        self.case = self.repo / decoder.SCOPE_NAME / 'cases' / 'case00'
        self.case.mkdir(parents=True)
        self.private = self.repo / '.private-journal'
        self.private.mkdir()
        (self.private / 'original').write_bytes(b'unchanged private fixture')
        self.recipe = self.case / 'original-recipe.py'
        self.recipe.write_bytes(b'# original recipe is never executed\n')
        self.prepared = self.case / 'prepared.json'
        metadata = {'schema': 'radio-native-v2-offline-maximum-prepared-v1',
            'control_case_identity': {'namespace': decoder.NAMESPACE, 'case_ordinal': 0,
                'source_case_id': decoder.NAMESPACE + '/case00',
                'native_case_binding_verified': False, 'source_sha256': '1' * 64},
            'scope': str(self.case), 'python': '/fixture/unused-python',
            'source_bytes': decoder.SOURCE_BYTES}
        recipe_raw = self.recipe.read_bytes()
        metadata = {'schema':decoder.PARTIAL_SCHEMA, 'fixture_only':True,
            'execution_authorized':False,'scientific_execution_authorized':False,
            'control_case_identity':metadata['control_case_identity'],
            'regeneration':{'prepared':metadata,
                'prepared_raw_sha256':hashlib.sha256(decoder.canonical(metadata)).hexdigest(),
                'recipe_sha256':hashlib.sha256(recipe_raw).hexdigest(),'recipe_bytes':len(recipe_raw)}}
        self.prepared.write_bytes(decoder.canonical(metadata))
        self.arguments = {'projection': str(self.prepared),
            'projection_sha256': hashlib.sha256(self.prepared.read_bytes()).hexdigest(),
            'original_recipe': str(self.recipe),
            'original_recipe_sha256': hashlib.sha256(self.recipe.read_bytes()).hexdigest(),
            'original_repository_root': str(self.repo),
            'original_prepared_sha256':metadata['regeneration']['prepared_raw_sha256']}

    def refused_before_counter(self, output, **changes):
        original_private = (self.private / 'original').read_bytes()
        with mock.patch.object(decoder, 'counter_bytes', side_effect=AssertionError('data reconstruction reached')) as counter:
            with self.assertRaises((ValueError, OSError)):
                decoder.reconstruct(**{**self.arguments, 'output_root': str(output), **changes})
            self.assertEqual(counter.call_count, 0)
        self.assertEqual((self.private / 'original').read_bytes(), original_private)

    def open_output(self, name='output'):
        output = decoder.OutputRoot(str(self.base / name), str(self.repo), {})
        self.addCleanup(output.close)
        return output

    def test_entire_repository_and_private_descendants_refused_before_counter(self):
        for destination in (self.repo, self.repo / 'new', self.case / 'new', self.private / 'new'):
            with self.subTest(destination=destination):
                self.refused_before_counter(destination)
                if destination.name == 'new':
                    self.assertFalse(destination.exists())

    def test_noncanonical_outputs_refused_before_counter(self):
        for destination in ('relative', str(self.base) + '/../alias', str(self.base) + '//alias', str(self.base) + '/a\\b'):
            with self.subTest(destination=destination):
                self.refused_before_counter(destination)

    def test_existing_and_symlink_roots_refused_without_content_change(self):
        destination = self.base / 'existing'
        destination.mkdir()
        (destination / 'keep').write_bytes(b'keep')
        self.refused_before_counter(destination)
        self.assertEqual((destination / 'keep').read_bytes(), b'keep')
        alias = self.base / 'alias'
        alias.symlink_to(self.private, target_is_directory=True)
        self.refused_before_counter(alias)
        self.assertEqual(sorted(path.name for path in self.private.iterdir()), ['original'])

    def test_symlink_ancestors_to_protected_or_outside_tree_refused(self):
        outside = self.base / 'outside'
        outside.mkdir()
        for target, label in ((self.repo, 'protected-alias'), (outside, 'outside-alias')):
            alias = self.base / label
            alias.symlink_to(target, target_is_directory=True)
            self.refused_before_counter(alias / 'new')
            self.assertFalse((target / 'new').exists())

    def test_physical_directory_alias_identity_refused_before_root_creation(self):
        parent = self.base / 'physical-alias-parent'
        parent.mkdir()
        info = parent.stat()
        with mock.patch.object(decoder, 'protected_directory_identities', return_value={(info.st_dev, info.st_ino)}):
            self.refused_before_counter(parent / 'new')
        self.assertFalse((parent / 'new').exists())

    def test_independent_repository_root_mismatch_refused_before_counter(self):
        wrong = self.base / 'wrong-repository'
        wrong.mkdir()
        self.refused_before_counter(self.base / 'fresh', original_repository_root=str(wrong))

    def test_metadata_symlink_and_hardlink_refused_before_counter(self):
        alias = self.case / 'symlink-prepared.json'
        alias.symlink_to(self.prepared)
        self.refused_before_counter(self.base / 'fresh', projection=str(alias))
        hardlink = self.case / 'hardlink-prepared.json'
        os.link(self.prepared, hardlink)
        self.refused_before_counter(self.base / 'fresh')

    def test_held_parent_replacement_refused_before_mkdir(self):
        parent = self.base / 'parent'
        parent.mkdir()
        output = decoder.OutputRoot(str(parent / 'fresh'), str(self.repo), {})
        self.addCleanup(output.close)
        parent.rename(self.base / 'old-parent')
        parent.mkdir()
        with self.assertRaisesRegex(ValueError, 'ancestry changed'):
            output.create()
        self.assertFalse((parent / 'fresh').exists())
        self.assertFalse((self.base / 'old-parent/fresh').exists())

    def test_owner_only_bounded_output_and_terminal_readback(self):
        output = self.open_output()
        output.create()
        output.write('deterministic-source.bin', b'tiny test bytes')
        output.finish()
        self.assertEqual((self.base / 'output').stat().st_mode & 0o777, 0o700)
        file = self.base / 'output/deterministic-source.bin'
        self.assertEqual(file.stat().st_mode & 0o777, 0o400)
        self.assertEqual(file.stat().st_uid, os.geteuid())
        self.assertEqual(file.stat().st_nlink, 1)

    def test_changed_output_root_mode_refused_before_file_write(self):
        output = self.open_output()
        output.create()
        os.chmod(self.base / 'output', 0o755)
        with self.assertRaisesRegex(ValueError, 'ownership changed'):
            output.write('deterministic-source.bin', b'tiny')
        self.assertFalse((self.base / 'output/deterministic-source.bin').exists())

    def test_fixed_names_existing_files_bounds_and_unknown_entries_refused(self):
        output = self.open_output()
        output.create()
        with self.assertRaisesRegex(ValueError, 'fixed offline output'):
            output.write('../escape', b'tiny')
        with self.assertRaisesRegex(ValueError, 'fixed offline output'):
            output.write('offline-reconstruction.json', b'x' * (decoder.MAX_RECEIPT_BYTES + 1))
        existing = self.base / 'output/deterministic-source.bin'
        existing.write_bytes(b'not overwritten')
        with self.assertRaises(FileExistsError):
            output.write('deterministic-source.bin', b'tiny')
        self.assertEqual(existing.read_bytes(), b'not overwritten')
        with self.assertRaisesRegex(ValueError, 'Unknown entry'):
            output.finish()

    def test_hardlinked_written_file_and_same_length_content_change_refused(self):
        output = self.open_output()
        output.create()
        output.write('deterministic-source.bin', b'tiny')
        file = self.base / 'output/deterministic-source.bin'
        alias = self.base / 'hardlink-output'
        os.link(file, alias)
        with self.assertRaisesRegex(ValueError, 'Sole-link regular'):
            output.finish()
        alias.unlink()
        os.chmod(file, 0o600)
        file.write_bytes(b'else')
        os.chmod(file, 0o400)
        with self.assertRaisesRegex(ValueError, 'identity/content changed'):
            output.finish()




class PartialRecipeTests(unittest.TestCase):
    def fixture(self):
        wire=b'a"\\b'
        identity={'namespace':decoder.NAMESPACE,'case_ordinal':0,'source_case_id':decoder.NAMESPACE+'/case00',
            'engineering_case_binding_sha256':'2'*64,'source_sha256':'1'*64,'native_case_binding_verified':False}
        arguments={'cmd':'literal fixture not executed','limit':1}
        prepared={'control_case_identity':identity,'source_bytes':decoder.SOURCE_BYTES,'source_sha256':'1'*64,
            'reads':[{'ordinal':i,'offset':0,'bytes':len(wire),'output_sha256':decoder.sha(wire),'arguments':arguments} for i in range(38)]}
        output=wire.decode('ascii');envelope={'chunk_id':'tiny','output':output,'exit_code':0}
        response=decoder.canonical(envelope).decode()
        record={'ordinal':3,'kind':'actual_source_read','request_json':decoder.canonical({'tool':'exec_command','arguments':arguments}).decode(),
            'raw_result':envelope,'response_json':response,'response_bytes':len(response.encode()),'response_sha256':decoder.sha(response.encode())}
        receipt={'ordinal':0,'envelope_bytes':len(response.encode()),'envelope_sha256':decoder.sha(response.encode())}
        records=[{'ordinal':i,'kind':'fixture'} for i in range(3)]+[record,{'ordinal':4,'kind':'actual_source_read','error':'preserved failure literal'}]
        transcript={'schema':'fixture','control_case_identity':identity,'qualified':{'client':{'records':records}},'read_receipts':[receipt]}
        raw=json.dumps(transcript,separators=(',',':'),ensure_ascii=False).encode()+b'\n'
        output_token=decoder.ascii_json_string(wire);response_token=decoder.ascii_json_string(response.encode())
        at=raw.index(output_token);next_at=raw.index(response_token,at+len(output_token))
        def literal(value):return {'kind':'literal','data_base64':__import__('base64').b64encode(value).decode(),'bytes':len(value),'sha256':decoder.sha(value)}
        def token(value,kind,**extras):return {'kind':kind,'source_plan_ordinal':0,'record_ordinal':3,'bytes':len(value),'sha256':decoder.sha(value),**extras}
        inner=response.index(output_token.decode());prefix=response[:inner].encode();suffix=response[inner+len(output_token):].encode()
        projection={'schema':decoder.PARTIAL_SCHEMA,'original_full_transcript':{'bytes':len(raw),'sha256':decoder.sha(raw)},'successful_source_reads':1,
            'parts':[literal(raw[:at]),token(output_token,'source_output_json'),literal(raw[at+len(output_token):next_at]),
                token(response_token,'response_json',envelope_prefix_base64=__import__('base64').b64encode(prefix).decode(),envelope_suffix_base64=__import__('base64').b64encode(suffix).decode()),literal(raw[next_at+len(response_token):])]}
        return projection,prepared,wire,raw

    def test_exact_partial_literal_and_double_quoted_source_reconstruction(self):
        projection,prepared,wire,raw=self.fixture()
        restored,tokens=decoder.restore_partial(projection,prepared,wire)
        self.assertEqual(restored,raw);self.assertEqual(len(tokens),2)

    def test_bad_literal_pin_and_noncanonical_base64_refused(self):
        projection,prepared,wire,raw=self.fixture()
        projection['parts'][0]['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'part bytes/SHA'):decoder.restore_partial(projection,prepared,wire)
        with self.assertRaises(ValueError):decoder.decode_b64('YQ=')

    def test_missing_out_of_order_or_duplicate_token_refused(self):
        projection,prepared,wire,raw=self.fixture()
        projection['parts'][1]['source_plan_ordinal']=1
        with self.assertRaisesRegex(ValueError,'identity/order'):decoder.restore_partial(projection,prepared,wire)
        projection['parts'].pop()
        with self.assertRaisesRegex(ValueError,'part inventory'):decoder.restore_partial(projection,prepared,wire)

    def test_wrong_range_or_envelope_or_whole_raw_pin_refused(self):
        projection,prepared,wire,raw=self.fixture()
        with self.assertRaisesRegex(ValueError,'source range'):decoder.restore_partial(projection,prepared,b'wrong')
        projection['parts'][3]['envelope_suffix_base64']='eA=='
        with self.assertRaisesRegex(ValueError,'part bytes/SHA'):decoder.restore_partial(projection,prepared,wire)
        projection,prepared,wire,raw=self.fixture();projection['original_full_transcript']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Entire original'):decoder.restore_partial(projection,prepared,wire)

    def test_complete_or_nonunique_plan_count_refused(self):
        projection,prepared,wire,raw=self.fixture();projection['successful_source_reads']=38
        with self.assertRaisesRegex(ValueError,'Strictly partial'):decoder.restore_partial(projection,prepared,wire)
        projection['successful_source_reads']=1;prepared['reads'][-1]['ordinal']=0
        with self.assertRaisesRegex(ValueError,'unique 38'):decoder.restore_partial(projection,prepared,wire)

    def test_bounded_directory_scan_names_and_pending_descriptors(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)/'repo';root.mkdir();(root/'one').mkdir();(root/'two').mkdir()
            with mock.patch.object(decoder,'MAX_PROTECTED_NAMES',0):
                with self.assertRaisesRegex(ValueError,'name scan'):decoder.protected_directory_identities(str(root),{})
            with mock.patch.object(decoder,'MAX_PENDING_DIRECTORIES',1):
                with self.assertRaisesRegex(ValueError,'pending directory'):decoder.protected_directory_identities(str(root),{})

    def test_independent_node_quoting_and_duplicate_token_scanner(self):
        import subprocess
        auditor=Path(__file__).with_name('public_lossless_partial_audit_v3.js')
        script="const a=require(process.argv[1]); const s='a\\\"\\\\b\\n'; const q=[...a.quoted([s])].join(''); if(q!==JSON.stringify(s))process.exit(2); let rejected=false; try{a.tokenSpans(Buffer.from('{\\\"x\\\":1,\\\"x\\\":2}'),new Map())}catch(e){rejected=true} if(!rejected)process.exit(3); process.stdout.write('PASS');"
        result=subprocess.run(['node','-e',script,str(auditor)],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,b'PASS')


    def test_node_growth_caps_oversize_and_metadata_duplicate_keys(self):
        import subprocess
        auditor=Path(__file__).with_name('public_lossless_partial_audit_v3.js')
        with tempfile.TemporaryDirectory() as temporary:
            file=Path(temporary)/'tiny';file.write_bytes(b'tiny')
            script="""const fs=require('node:fs'),c=require('node:crypto'),a=require(process.argv[1]),file=process.argv[2];
const real=fs.readSync, expected={bytes:4,sha256:c.createHash('sha256').update('tiny').digest('hex')};
for(const mode of ['read','hash']){fs.writeFileSync(file,'tiny');let calls=0,width=0;fs.readSync=function(fd,b,o,n,pos){calls++;width=Math.max(width,n);if(calls===1)fs.appendFileSync(file,'growth');return real(fd,b,o,n,pos);};let error='';try{if(mode==='read')a.read(file,expected.sha256,8);else a.filePin(file,expected,8);}catch(e){error=String(e)}finally{fs.readSync=real}if(!error.includes('grew beyond exact bounded')||width>5||calls!==1)throw Error('Unbounded growth regression '+mode);}
fs.writeFileSync(file,'oversized');let calls=0;fs.readSync=function(...args){calls++;return real(...args)};let refused=false;try{a.read(file,undefined,8)}catch(e){refused=true}finally{fs.readSync=real}if(!refused||calls)throw Error('Oversize must refuse before content read');
let duplicate=false;try{a.parseJSON(Buffer.from('{"a":1,"a":2}'))}catch(e){duplicate=true}if(!duplicate)throw Error('Duplicate metadata key accepted');process.stdout.write('PASS');"""
            result=subprocess.run(['node','-e',script,str(auditor),str(file)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,b'PASS')


if __name__ == '__main__':
    unittest.main()
