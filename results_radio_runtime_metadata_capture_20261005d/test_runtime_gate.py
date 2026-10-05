"""Pure D admission/read/tree tests; TEMP synthetic metadata files only."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH=Path(__file__).with_name('runtime_gate.py')
spec=importlib.util.spec_from_file_location('synthetic_d_gate_test',PATH)
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

EXPECTED_LIMITS=dict(wall_seconds=180,operation_seconds=150,child_wall_seconds=90,child_cpu_seconds=80,
    parent_address_space_bytes=512*1024**2,child_address_space_bytes=512*1024**2,
    parent_read_bytes=1536*1024**2,root_explicit_read_bytes=1408*1024**2,
    supervisor_pin_read_bytes=32*1024**2,supervisor_proc_read_bytes=32*1024**2,
    misc_stream_read_bytes=64*1024**2,opaque_child_read_reserve_bytes=512*1024**2,
    joined_read_bytes=2*1024**3,artifact_bytes=64*1024**2,terminal_reserve_bytes=8*1024**2,
    output_file_bytes=8*1024**2,input_file_bytes=128*1024**2,stdout_bytes=2*1024**2,
    stderr_bytes=2*1024**2,file_count=2000,directory_count=128,child_dispatches=1,
    child_cleanup_seconds=10,child_sample_interval_seconds=0.02)


def inputs():
    keys=('gate_source_path','launcher_source_path','supervisor_source_path','collector_source_path',
          'filter_input_path','record_relocations_path','phase2_path')
    fields={key:'/SYNTHETIC_ONLY/'+key for key in keys}
    sources=[dict(path=path,bytes=1,sha256='1'*64) for path in fields.values()]
    manifest_pin=dict(path='/SYNTHETIC_ONLY/input-manifest',bytes=1,sha256='8'*64)
    sources.append(manifest_pin)
    published={'SYNTHETIC_REPOSITORY/'+key:dict(local_path=path,raw_bytes=1,raw_sha256='1'*64)
               for key,path in fields.items()}
    published['SYNTHETIC_REPOSITORY/input-manifest']=dict(local_path=manifest_pin['path'],
                                                        raw_bytes=1,raw_sha256='8'*64)
    runtime={key:'/SYNTHETIC_ONLY/'+key for key in ('python_executable','guard_path','exec_seal_path')}
    freeze=dict(schema=gate.SCHEMA,identity=gate.IDENTITY,limits=copy.deepcopy(EXPECTED_LIMITS),
        single_use=True,automatic_successor=False,engineering_only=True,network=False,install=False,
        hdf5_dataset_access=False,scientific_authority=False,marker_repository_path='SYNTHETIC_ONLY.activate.json',
        source_pins=sources,published_sources=published,input_manifest_pin=copy.deepcopy(manifest_pin),
        runtime_pins=[dict(path=p,bytes=1,sha256='2'*64) for p in runtime.values()],**fields,**runtime)
    freeze_hash,marker_hash='3'*64,'4'*64
    marker=dict(schema='radio-runtime-metadata-capture-activation-v1',identity=gate.IDENTITY,
        freeze_sha256=freeze_hash,single_use=True,automatic_successor=False,
        prepared_commit='5'*40,prepared_tree='6'*40)
    proof=dict(schema='radio-runtime-metadata-capture-publication-proof-v1',
        repository='andersenmartin-blip/setisearch',branch='m43-support-qualification',
        preparation_commit=marker['prepared_commit'],preparation_tree=marker['prepared_tree'],
        activation_commit='7'*40,sole_parent=marker['prepared_commit'],
        changed_paths=[freeze['marker_repository_path']],marker_sha256=marker_hash,
        full_preparation_readback_exact=True,marker_readback_exact=True,source_readbacks=copy.deepcopy(published))
    return freeze,proof,marker,freeze_hash,marker_hash


class AdmissionTests(unittest.TestCase):
    def test_positive_synthetic_binding_and_no_mutation(self):
        args=inputs();before=copy.deepcopy(args)
        self.assertIsNone(gate.admit(*args));self.assertEqual(args,before)
        self.assertEqual(gate.LIMITS,EXPECTED_LIMITS)

    def test_wrong_scope_or_marker_binding(self):
        cases=((0,'schema','old-C-schema'),(0,'identity','old-C-identity'),
            (2,'schema','wrong'),(2,'identity','wrong'),(2,'freeze_sha256','0'*64))
        for index,key,value in cases:
            args=inputs();args[index][key]=value
            with self.subTest(index=index,key=key),self.assertRaises(gate.Refusal):gate.admit(*args)

    def test_wrong_publication_proof(self):
        cases={'repository':'wrong','branch':'main','preparation_commit':'0'*40,
               'preparation_tree':'0'*40,'sole_parent':'0'*40,'marker_sha256':'0'*64,
               'changed_paths':['wrong'],'activation_commit':'short','full_preparation_readback_exact':False,
               'marker_readback_exact':False,'source_readbacks':{}}
        for key,value in cases.items():
            args=inputs();args[1][key]=value
            with self.subTest(key=key),self.assertRaises(gate.Refusal):gate.admit(*args)

    def test_all_flags_exact_no_authority(self):
        for index,keys in ((0,('single_use','automatic_successor','engineering_only','network','install',
                              'hdf5_dataset_access','scientific_authority')),
                           (2,('single_use','automatic_successor'))):
            for key in keys:
                for mutation in (not inputs()[index][key],int(inputs()[index][key]),None):
                    args=inputs();args[index][key]=mutation
                    with self.subTest(index=index,key=key,value=mutation),self.assertRaises(gate.Refusal):gate.admit(*args)

    def test_each_frozen_limit_mutation_refused(self):
        for key in EXPECTED_LIMITS:
            for delta in (-1,1):
                args=inputs();args[0]['limits'][key]+=delta
                with self.subTest(key=key,delta=delta),self.assertRaises(gate.Refusal):gate.admit(*args)

    def test_source_publication_and_executable_path_coverage(self):
        for change in ('unpublished-source','missing-driver','missing-binary','manifest-pin-mismatch',
                       'publication-raw-sha-mismatch','publication-raw-size-mismatch',
                       'duplicate-source-path','duplicate-publication-local-path'):
            args=inputs()
            if change=='unpublished-source':args[0]['source_pins'].append(dict(path='/SYNTHETIC_UNPUBLISHED'))
            elif change=='missing-driver':args[0]['collector_source_path']='/SYNTHETIC_UNPINNED'
            elif change=='missing-binary':args[0]['guard_path']='/SYNTHETIC_UNPINNED'
            elif change=='manifest-pin-mismatch':args[0]['input_manifest_pin']['sha256']='0'*64
            elif change.startswith('publication-raw'):
                descriptor=next(iter(args[0]['published_sources'].values()))
                if change.endswith('sha-mismatch'):descriptor['raw_sha256']='0'*64
                else:descriptor['raw_bytes']=2
                args[1]['source_readbacks']=copy.deepcopy(args[0]['published_sources'])
            elif change=='duplicate-source-path':
                args[0]['source_pins'].append(copy.deepcopy(args[0]['source_pins'][0]))
            else:
                args[0]['published_sources']['SYNTHETIC_DUPLICATE']=copy.deepcopy(
                    next(iter(args[0]['published_sources'].values())))
                args[1]['source_readbacks']=copy.deepcopy(args[0]['published_sources'])
            with self.subTest(change=change),self.assertRaises(gate.Refusal):gate.admit(*args)

    def test_duplicate_json_and_changed_raw_hash(self):
        raw=b'{"a":{"x":1,"x":2}}'
        with self.assertRaisesRegex(gate.Refusal,'duplicate'):gate.json_checked(raw,gate.sha(raw))
        raw=b'{"synthetic":true}'
        self.assertEqual(gate.json_checked(raw,gate.sha(raw)),{'synthetic':True})
        with self.assertRaisesRegex(gate.Refusal,'raw hash'):gate.json_checked(raw+b' ',gate.sha(raw))


def file_pin(path,root=None):
    st=path.lstat();raw=path.read_bytes()
    pin=dict(path=str(path),bytes=len(raw),sha256=gate.sha(raw),mode=st.st_mode&0o7777,
             identity=[st.st_dev,st.st_ino],links=st.st_nlink)
    if root is not None:pin['relative_path']=path.relative_to(root).as_posix()
    return pin


class ReadTests(unittest.TestCase):
    def test_current_pin_and_wrong_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input';p.write_bytes(b'synthetic')
            pin=file_pin(p);self.assertEqual(gate.Reads().pin(pin),b'synthetic')
            pin['sha256']='0'*64
            with self.assertRaises(gate.Refusal):gate.Reads().pin(pin)

    def test_symlink_and_change_during_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input';p.write_bytes(b'synthetic');link=Path(d)/'alias';link.symlink_to(p)
            with self.assertRaises(gate.Refusal):gate.Reads().raw(link)
            original=gate.os.read
            def mutate(fd,count):
                raw=original(fd,count);p.write_bytes(b'changed and expanded');return raw
            with patch.object(gate.os,'read',side_effect=mutate),self.assertRaisesRegex(gate.Refusal,'custody changed'):
                gate.Reads().raw(p)


class WholeTreeTests(unittest.TestCase):
    def test_exact_full_cardinality_then_extra_missing_symlink_and_pth_refusal(self):
        # 1038 one-byte stdlib metadata fixtures plus 110 directories; none is
        # Python source, native code, astronomical data or scientific fixture.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'SYNTHETIC_INSTALLED_TREE';root.mkdir()
            for n in range(109):(root/('dir%03d'%n)).mkdir()
            for n in range(1038):(root/('metadata%04d'%n)).write_bytes(b'x')
            directories=[]
            for p in [root]+sorted(x for x in root.iterdir() if x.is_dir()):
                st=p.stat();directories.append(dict(relative_path=p.relative_to(root).as_posix(),
                    identity=[st.st_dev,st.st_ino],mode=st.st_mode&0o7777))
            manifest=dict(schema='radio-installed-tree-input-v1',root=str(root),directories=directories,
                          files=[file_pin(p,root) for p in sorted(root.iterdir()) if p.is_file()])
            result=gate.check_installed_tree(manifest,gate.Reads())
            self.assertEqual((result['files'],result['directories']),(1038,110))
            duplicate_dir=copy.deepcopy(manifest)
            duplicate_dir['directories'].append(copy.deepcopy(duplicate_dir['directories'][0]))
            with self.subTest(change='duplicate-directory'),self.assertRaisesRegex(gate.Refusal,'cardinality'):
                gate.check_installed_tree(duplicate_dir,gate.Reads())
            redirected=copy.deepcopy(manifest)
            outside=Path(d)/'SYNTHETIC_OUTSIDE_PIN_SOURCE';outside.write_bytes(b'x')
            redirected['files'][0]['path']=str(outside)
            first=root/redirected['files'][0]['relative_path'];first.write_bytes(b'y')
            try:
                with self.subTest(change='redirected-file-pin'),self.assertRaises(gate.Refusal):
                    gate.check_installed_tree(redirected,gate.Reads())
            finally:first.write_bytes(b'x')
            for name in ('unexpected-metadata','added.pth'):
                p=root/name;p.write_bytes(b'x')
                with self.subTest(addition=name),self.assertRaisesRegex(gate.Refusal,'unexpected'):
                    gate.check_installed_tree(manifest,gate.Reads())
                p.unlink()
            missing=root/'metadata0000';missing.unlink()
            with self.assertRaisesRegex(gate.Refusal,'missing'):
                gate.check_installed_tree(manifest,gate.Reads())
            # Restore membership with a symlink, deliberately without changing
            # the original pin identity. It must fail kind/identity admission.
            missing.symlink_to(root/'metadata0001')
            with self.assertRaisesRegex(gate.Refusal,'identity/kind'):
                gate.check_installed_tree(manifest,gate.Reads())


if __name__=='__main__':unittest.main()
