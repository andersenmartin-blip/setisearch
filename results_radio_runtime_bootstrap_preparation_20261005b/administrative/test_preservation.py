"""Pure local preservation tests; never reads the actual B root or opens a socket."""
import argparse
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

WORK = Path(__file__).resolve().parent
BASIS = Path('/workspace/scratch/a5b2addacbd5/setisearch-20261005')
PREREAD = 'results_radio_runtime_bootstrap_preparation_20261005a/installer-preread.json'
spec = importlib.util.spec_from_file_location('preserver', WORK / 'preserve_bootstrap_b.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreservationTests(unittest.TestCase):
    def test_roundtrip_all_representation_types_and_final_objects(self):
        preread_raw = (BASIS / PREREAD).read_bytes()
        preread = json.loads(preread_raw)
        selected = [next(r for r in preread['installer_source_files'] if r['stored_encoding'] == encoding)
                    for encoding in ('utf8', 'base64')]
        selected.append(next(r for r in preread['installer_source_files'] if r['stored_mode'] == '100755'))
        with tempfile.TemporaryDirectory(prefix='synthetic-preservation-') as temporary:
            outer = Path(temporary)
            repo = outer / 'repo'
            actual = outer / 'synthetic-finished-root'
            repo.mkdir()
            actual.mkdir(mode=0o700)
            original = {}
            def create(path, raw, mode=0o644):
                target = actual / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                target.chmod(mode)
                original[path] = (raw, mode)
            identity = 'b' * 64
            for path in ('spent.json', 'supervisor-result.json'):
                create(path, json.dumps({'bootstrap_identity': identity, 'status': 'SYNTHETIC'}).encode())
            create('artifact-manifest.json', b'{"synthetic":"terminal self exclusion retained"}\n')
            create('transport.raw', b'CONNECT denied\r\n\r\n')
            create('binary-unmatched.bin', bytes(range(256)) * 4000, 0o755)
            create('empty.raw', b'')
            for row in selected:
                encoded = (BASIS / row['repository_artifact_path']).read_bytes()
                raw = base64.b64decode(encoded) if row['stored_encoding'] == 'base64' else encoded
                create('installer/' + row['seed_relative_path'], raw, int(row['filesystem_mode'], 8))
            archive_buffer = io.BytesIO()
            member_raw = bytes(range(256)) * 17
            with zipfile.ZipFile(archive_buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('pkg/payload.bin', member_raw)
            complete = archive_buffer.getvalue()
            wheels = []
            for filename, raw in (('one.whl', complete), ('two.whl', b''), ('three.whl', b'\xffpartial')):
                create('wheelhouse/' + filename, raw)
                expected = complete if filename == 'one.whl' else b'expected-wheel-bytes'
                wheels.append({'filename': filename, 'bytes': len(expected),
                               'sha256': hashlib.sha256(expected).hexdigest()})
            create('site/pkg/payload.bin', member_raw)
            plan = json.dumps({'materialization': {'official_wheels': wheels}}).encode()
            (repo / 'plan.json').write_bytes(plan)
            catalog = (WORK / 'immutable-original-preparation-tree.json').read_bytes()
            (repo / 'catalog.json').write_bytes(catalog)
            args = argparse.Namespace(repository_root=str(repo), root=str(actual), output='preserved',
                plan='plan.json', plan_sha256=hashlib.sha256(plan).hexdigest(),
                basis_repository_root=str(BASIS), installer_preread=PREREAD,
                installer_preread_sha256=hashlib.sha256(preread_raw).hexdigest(),
                basis_tree_catalog='catalog.json', basis_tree_catalog_sha256=hashlib.sha256(catalog).hexdigest(),
                bootstrap_identity=identity)
            self.assertEqual(module.preserve(args), 0)
            manifest = json.loads((repo / 'preserved/preservation-manifest.json').read_bytes())
            self.assertEqual(manifest['schema'], 'radio-runtime-package-bootstrap-lossless-preservation-v2')
            self.assertFalse(manifest['scientific_authority'])
            self.assertFalse(manifest['all_three_original_archives_present_and_exact'])
            self.assertEqual(len(manifest['complete_original_archive_paths']), 1)
            self.assertTrue(manifest['full_before_after_identity_equal'])
            payloads = {p['root_relative_path']: p for p in manifest['payloads']}
            def parts(payload):
                chunks = []
                for part in payload['parts']:
                    encoded = (repo / part['encoded']['repository_path']).read_bytes()
                    self.assertEqual(hashlib.sha256(encoded).hexdigest(), part['encoded']['sha256'])
                    raw = base64.b64decode(encoded[:-1], validate=True)
                    self.assertEqual(len(raw), part['raw_bytes'])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), part['raw_sha256'])
                    chunks.append(raw)
                raw = b''.join(chunks)
                self.assertEqual(len(raw), payload['raw_bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), payload['raw_sha256'])
                return raw
            reconstructed = {}
            kinds = set()
            for row in manifest['before']['entries']:
                if row['kind'] != 'file':
                    continue
                preservation = row['preservation']
                kind = preservation['kind']
                kinds.add(kind)
                if kind == 'parts':
                    raw = parts(payloads[row['path']])
                elif kind == 'exact-utf8-file':
                    raw = (repo / preservation['stored']['repository_path']).read_bytes()
                elif kind == 'installer-basis-reference':
                    self.assertEqual(preservation['immutable_publication']['commit'], module.BASIS_COMMIT)
                    self.assertEqual(preservation['immutable_publication']['git_blob'], preservation['encoded_git_blob'])
                    encoded = (BASIS / preservation['repository_path']).read_bytes()
                    raw = base64.b64decode(encoded[:-1], validate=True) if preservation['stored_encoding'] == 'base64' else encoded
                elif kind == 'wheel-member-byte-equivalence':
                    member = preservation['member']
                    archive_raw = parts(payloads[member['archive_root_relative_path']])
                    with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
                        raw = archive.read(member['member_path'])
                else:
                    self.fail('unrecognized preservation form')
                self.assertEqual(len(raw), row['bytes'])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
                reconstructed[row['path']] = (raw, row['identity']['mode'])
            self.assertEqual(reconstructed, original)
            self.assertEqual(kinds, {'parts', 'exact-utf8-file', 'installer-basis-reference', 'wheel-member-byte-equivalence'})
            with self.assertRaises(FileExistsError):
                module.preserve(args)  # Output is exclusive; no reset, overwrite, or retry.

    def test_rejects_symlink_and_hardlink(self):
        for link_kind in ('symlink', 'hardlink'):
            with self.subTest(link_kind=link_kind), tempfile.TemporaryDirectory(prefix='synthetic-preservation-') as temporary:
                root = Path(temporary)
                original = root / 'file'
                original.write_bytes(b'raw')
                if link_kind == 'symlink':
                    (root / 'link').symlink_to('file')
                else:
                    import os
                    os.link(original, root / 'link')
                tree = module.HeldTree(str(root))
                try:
                    with self.assertRaises(module.PreservationError):
                        module.inventory(tree, hashes=True)
                finally:
                    tree.close()


if __name__ == '__main__':
    unittest.main()
