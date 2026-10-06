"""Pure invented ELF/maps/auxv fixtures; none are scientific/native cases."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import unittest

spec=importlib.util.spec_from_file_location('mapping',Path(__file__).with_name('mapping.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
EVIDENCE=[]


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.inputs=[]
        self.identity={'device':os.makedev(8,1),'inode':12,'bytes':8192}
        self.base=0x4000

    def tearDown(self):
        EVIDENCE.append({'test':self.id(),'invented_inputs':self.inputs,'native_observation':False,'science_identity':None})

    def elf(self,kind=3,flags=5,vaddr=0,offset=0,size=4096,memory=None,align=4096,phnum=1,**changes):
        ident=b'\x7fELF\x02\x01\x01'+b'\0'*9
        h=dict(ident=ident,kind=kind,machine=62,version=1,entry=vaddr+0x200,phoff=64,shoff=0,
               flags=0,ehsize=64,phsize=56,phnum=phnum,shsize=0,shnum=0,shstr=0)
        h.update(changes);raw=bytearray(8192)
        raw[:64]=m.EHDR.pack(*h.values())
        raw[64:120]=m.PHDR.pack(1,flags,offset,vaddr,0,size,memory if memory is not None else size,align)
        self.inputs.append({'kind':'elf-prefix','header_hex':bytes(raw[:120]).hex(),'declared_bytes':8192})
        return bytes(raw)

    def maps(self,line=None):
        raw=line or b'00004000-00005000 r-xp 00000000 08:01 12 /fixture/main\n'
        self.inputs.append({'kind':'maps','raw_hex':raw.hex()});return m.parse_maps(raw,4096)

    def aux(self,**changes):
        values={3:self.base+64,4:56,5:1,6:4096,9:self.base+0x200,33:0x9000}
        for key,value in changes.items(): values[int(key)]=value
        return values

    def bind(self,raw=None,rows=None,base=None):
        elf=m.parse_elf(raw or self.elf(),8192)
        return m.executable_binding(rows if rows is not None else self.maps(),elf,self.base if base is None else base,self.identity,4096)

    def test_exact_snapshot_binding_is_never_runtime_authority(self):
        r=self.bind();self.assertEqual(r['segments'][0]['start'],0x4000)
        self.assertFalse(r['native_runtime_or_science_authority']);self.assertFalse(r['mapped_content_verified'])
        self.assertFalse(r['continuous_mapping_custody'])

    def test_split_executable_maps_cover_same_original_offsets(self):
        rows=self.maps(b'00004000-00005000 r-xp 00000000 08:01 12 /fixture/main\n00005000-00006000 r-xp 00001000 08:01 12 /fixture/main\n')
        self.assertEqual(len(self.bind(self.elf(size=8192),rows)['segments'][0]['pieces']),2)

    def test_same_path_wrong_inode_refused(self):
        with self.assertRaises(m.Refusal): self.bind(rows=self.maps(b'00004000-00005000 r-xp 00000000 08:01 13 /fixture/main\n'))

    def test_different_path_same_inode_is_metadata_only(self):
        r=self.bind(rows=self.maps(b'00004000-00005000 r-xp 00000000 08:01 12 /fixture/alias\n'))
        self.assertFalse(r['callback_origin_authenticated'])

    def test_wrong_device_refused(self):
        with self.assertRaises(m.Refusal): self.bind(rows=self.maps(b'00004000-00005000 r-xp 00000000 08:02 12 /fixture/main\n'))

    def test_wrong_offset_refused(self):
        with self.assertRaises(m.Refusal): self.bind(rows=self.maps(b'00004000-00005000 r-xp 00001000 08:01 12 /fixture/main\n'))

    def test_writable_executable_mapping_refused(self):
        with self.assertRaises(m.Refusal): self.bind(rows=self.maps(b'00004000-00005000 rwxp 00000000 08:01 12 /fixture/main\n'))

    def test_anonymous_executable_mapping_refused(self):
        with self.assertRaises(m.Refusal): self.bind(rows=self.maps(b'00004000-00005000 r-xp 00000000 00:00 0\n'))

    def test_shared_executable_mapping_refused(self):
        with self.assertRaises(m.Refusal): self.bind(rows=self.maps(b'00004000-00005000 r-xs 00000000 08:01 12 /fixture/main\n'))

    def test_deleted_mapping_refused(self):
        with self.assertRaises(m.Refusal): self.bind(rows=self.maps(b'00004000-00005000 r-xp 00000000 08:01 12 /fixture/main (deleted)\n'))

    def test_incomplete_executable_pages_refused(self):
        with self.assertRaises(m.Refusal): self.bind(self.elf(size=8192))

    def test_gap_refused(self):
        rows=self.maps(b'00005000-00006000 r-xp 00001000 08:01 12 /fixture/main\n')
        with self.assertRaises(m.Refusal): self.bind(self.elf(size=8192),rows)

    def test_maps_overlap_refused(self):
        with self.assertRaises(m.Refusal): self.maps(b'00004000-00006000 r-xp 00000000 08:01 12 /f\n00005000-00006000 r-xp 00001000 08:01 12 /f\n')

    def test_maps_unordered_refused(self):
        with self.assertRaises(m.Refusal): self.maps(b'00005000-00006000 r-xp 00001000 08:01 12 /f\n00004000-00005000 r-xp 00000000 08:01 12 /f\n')

    def test_maps_unaligned_refused(self):
        with self.assertRaises(m.Refusal): self.maps(b'00004001-00005000 r-xp 00000000 08:01 12 /f\n')

    def test_maps_missing_newline_refused(self):
        with self.assertRaises(m.Refusal): self.maps(b'00004000-00005000 r-xp 00000000 08:01 12 /f')

    def test_maps_large_body_refused(self):
        with self.assertRaises(m.Refusal): m.parse_maps(b'x'*(m.MAX_MAP_BYTES+1),4096)

    def test_maps_raw_nonutf8_names_preserved(self):
        rows=self.maps(b'00004000-00005000 r-xp 00000000 08:01 12 /fixture/\xff\n')
        self.assertTrue(bytes.fromhex(rows[0]['raw_name_hex']).endswith(b'\xff'))

    def test_boolean_loader_base_refused(self):
        with self.assertRaises(m.Refusal): self.bind(base=False)

    def test_boolean_descriptor_inode_refused(self):
        self.identity['inode']=True
        with self.assertRaises(m.Refusal): self.bind()

    def test_relocated_extent_overflow_refused(self):
        with self.assertRaises(m.Refusal): self.bind(base=2**64-4096)

    def test_et_exec_relocation_refused(self):
        with self.assertRaises(m.Refusal): self.bind(self.elf(kind=2))

    def test_et_exec_fixed_main_base(self):
        elf=m.parse_elf(self.elf(kind=2,vaddr=0x400000),8192)
        aux={3:0x400040,4:56,5:1,6:4096,9:0x400200}
        self.assertEqual(m.administrative_main_base(elf,aux),0)

    def test_wrong_auxv_entry_refused(self):
        elf=m.parse_elf(self.elf(),8192);aux=self.aux();aux[9]+=1
        with self.assertRaises(m.Refusal): m.administrative_main_base(elf,aux)

    def test_wrong_auxv_program_header_count_refused(self):
        elf=m.parse_elf(self.elf(),8192);aux=self.aux();aux[5]=2
        with self.assertRaises(m.Refusal): m.administrative_main_base(elf,aux)

    def test_elf_other_endian_refused(self):
        raw=bytearray(self.elf());raw[5]=2
        with self.assertRaises(m.Refusal): m.parse_elf(bytes(raw),8192)

    def test_elf_other_machine_refused(self):
        with self.assertRaises(m.Refusal): m.parse_elf(self.elf(machine=183),8192)

    def test_elf_extended_phnum_refused(self):
        with self.assertRaises(m.Refusal): m.parse_elf(self.elf(phnum=65535),8192)

    def test_elf_incomplete_program_table_refused(self):
        with self.assertRaises(m.Refusal): m.parse_elf(self.elf()[:100],8192)

    def test_elf_file_extent_refused(self):
        with self.assertRaises(m.Refusal): m.parse_elf(self.elf(size=9000),8192)

    def test_elf_file_memory_size_refused(self):
        with self.assertRaises(m.Refusal): m.parse_elf(self.elf(memory=1),8192)

    def test_elf_alignment_refused(self):
        with self.assertRaises(m.Refusal): m.parse_elf(self.elf(align=4095),8192)

    def test_writable_executable_segment_refused(self):
        with self.assertRaises(m.Refusal): self.bind(self.elf(flags=7))

    def test_executable_anonymous_bss_refused(self):
        with self.assertRaises(m.Refusal): self.bind(self.elf(memory=8192))

    def test_program_table_ambiguous_load_refused(self):
        raw=bytearray(self.elf(phnum=2));raw[120:176]=raw[64:120]
        elf=m.parse_elf(bytes(raw),8192)
        with self.assertRaises(m.Refusal): m.administrative_main_base(elf,self.aux())

    def test_auxv_duplicate_tag_refused(self):
        raw=m.AUX.pack(6,4096)*2+m.AUX.pack(33,0x9000)+m.AUX.pack(0,0)
        with self.assertRaises(m.Refusal): m.parse_auxv(raw)

    def test_auxv_unterminated_refused(self):
        with self.assertRaises(m.Refusal): m.parse_auxv(m.AUX.pack(6,4096)+m.AUX.pack(33,0x9000))

    def test_auxv_trailing_record_refused(self):
        with self.assertRaises(m.Refusal): m.parse_auxv(m.AUX.pack(6,4096)+m.AUX.pack(33,0x9000)+m.AUX.pack(0,0)+m.AUX.pack(3,1))

    def test_auxv_unknown_tags_retained(self):
        raw=m.AUX.pack(6,4096)+m.AUX.pack(33,0x9000)+m.AUX.pack(123456,789)+m.AUX.pack(0,0)
        self.assertEqual(m.parse_auxv(raw)[123456],789)

    def test_vdso_exact_snapshots_never_admit_target(self):
        rows=self.maps(b'00009000-0000b000 r-xp 00000000 00:00 0 [vdso]\n')
        raw=self.elf();w=m.vdso_witness(rows,self.aux(),raw,raw)
        self.assertFalse(w['target_kernel_objects_supported']);self.assertFalse(w['native_runtime_or_science_authority'])

    def test_vdso_auxv_spoof_refused(self):
        rows=self.maps(b'00009000-0000b000 r-xp 00000000 00:00 0 [vdso]\n');aux=self.aux();aux[33]+=4096
        with self.assertRaises(m.Refusal): m.vdso_region(rows,aux)

    def test_vdso_file_inode_refused(self):
        rows=self.maps(b'00009000-0000b000 r-xp 00000000 00:00 12 [vdso]\n')
        with self.assertRaises(m.Refusal): m.vdso_region(rows,self.aux())

    def test_vdso_duplicate_region_refused(self):
        rows=self.maps(b'00009000-0000b000 r-xp 00000000 00:00 0 [vdso]\n0000c000-0000e000 r-xp 00000000 00:00 0 [vdso]\n')
        with self.assertRaises(m.Refusal): m.vdso_region(rows,self.aux())

    def test_vdso_bytes_changed_refused(self):
        rows=self.maps(b'00009000-0000b000 r-xp 00000000 00:00 0 [vdso]\n');raw=self.elf();changed=raw[:-1]+b'\x01'
        with self.assertRaises(m.Refusal): m.vdso_witness(rows,self.aux(),raw,changed)

    def test_vdso_short_read_refused(self):
        rows=self.maps(b'00009000-0000b000 r-xp 00000000 00:00 0 [vdso]\n');raw=self.elf()
        with self.assertRaises(m.Refusal): m.vdso_witness(rows,self.aux(),raw[:-1],raw[:-1])

    def test_vdso_writable_elf_refused(self):
        rows=self.maps(b'00009000-0000b000 r-xp 00000000 00:00 0 [vdso]\n');raw=self.elf(flags=7)
        with self.assertRaises(m.Refusal): m.vdso_witness(rows,self.aux(),raw,raw)

    def test_no_dispatch(self):
        with self.assertRaises(m.Refusal): m.dispatch('even if geometry matches')


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MappingTests))
    folder=Path(__file__).parent;number=1
    while (folder/('PURE_FIXTURES-%d.json'%number)).exists(): number+=1
    with (folder/('PURE_FIXTURES-%d.json'%number)).open('x') as stream:
        json.dump({'schema':'radio-M-invented-source-fixtures-v1','cases':EVIDENCE,'native_or_science_authority':False},stream,sort_keys=True)
        stream.write('\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
