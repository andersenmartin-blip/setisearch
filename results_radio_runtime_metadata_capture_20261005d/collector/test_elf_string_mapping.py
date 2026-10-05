"""Pure synthetic ELF bytes; no native loading or scientific package imports."""
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parent

def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/filename)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

original=module('original_inert','original-collector.py')
repaired=module('repaired_inert','collect_runtime_identity.py')
mapping=module('mapping_inert','elf_string_mapping.py')


def fixture(bits=64,endian='<',second_offset=410,second_va_offset=410,first_filesz=410,first_memsz=None):
    raw=bytearray(640)
    header_size,phsize,dynwidth=(64,56,16) if bits==64 else (52,32,8)
    raw[:16]=b'\x7fELF'+bytes([2 if bits==64 else 1,1 if endian=='<' else 2,1])+bytes(9)
    struct.pack_into(endian+('HHIQQQIHHHHHH' if bits==64 else 'HHIIIIIHHHHHH'),raw,16,
                     3,62 if bits==64 else 3,1,0,header_size,0,0,header_size,phsize,3,0,0,0)
    def ph(index,kind,off,va,filesz,memsz):
        if bits==64:
            struct.pack_into(endian+'IIQQQQQQ',raw,header_size+index*phsize,
                             kind,4,off,va,0,filesz,memsz,1)
        else:
            struct.pack_into(endian+'IIIIIIII',raw,header_size+index*phsize,
                             kind,off,va,0,filesz,memsz,4,1)
    ph(0,1,0,0x1000,first_filesz,first_filesz if first_memsz is None else first_memsz)
    ph(1,1,second_offset,0x1000+second_va_offset,len(raw)-second_offset,len(raw)-second_offset)
    ph(2,2,240,0x1000+240,6*dynwidth,6*dynwidth)
    table=b'\0libfoo.so\0$ORIGIN\0/locked/lib\0'
    first_count=min(len(table),max(0,first_filesz-400))
    raw[400:400+first_count]=table[:first_count]
    # File bytes following the virtual split may reside elsewhere in the file.
    continuation=max(0,second_va_offset-400)
    if continuation<len(table):
        raw[second_offset:second_offset+len(table)-continuation]=table[continuation:]
    for index,(tag,value) in enumerate(((5,0x1000+400),(10,len(table)),(1,1),(15,11),(29,19),(0,0))):
        struct.pack_into(endian+('qQ' if bits==64 else 'iI'),raw,240+index*dynwidth,tag,value)
    return bytes(raw)


class StringMappingTests(unittest.TestCase):
    def test_cross_segment_full_table_in_all_classes_and_byte_orders(self):
        for bits in (32,64):
            for endian in ('<','>'):
                raw=fixture(bits,endian)
                with self.assertRaisesRegex(original.Refusal,'outside unique PT_LOAD'):
                    original.elf_dynamic(raw)
                result=repaired.elf_dynamic(raw)
                self.assertEqual(result['needed'],['libfoo.so'])
                self.assertEqual(result['rpath'],['$ORIGIN'])
                self.assertEqual(result['runpath'],['/locked/lib'])

    def test_virtual_contiguity_can_join_noncontiguous_file_spans(self):
        result=repaired.elf_dynamic(fixture(second_offset=450))
        self.assertEqual(result['needed'],['libfoo.so'])
        self.assertEqual(result['runpath'],['/locked/lib'])

    def test_same_translation_overlapping_load_headers_are_unambiguous(self):
        self.assertEqual(mapping.file_backed_virtual_bytes(b'abcdefgh',[(100,8,0),(102,6,2)],101,6),b'bcdefg')

    def test_conflicting_offsets_refused_even_if_bytes_happen_to_match(self):
        with self.assertRaisesRegex(mapping.Refusal,'conflicting file-offset'):
            mapping.file_backed_virtual_bytes(b'aaaaaaaa',[(100,4,0),(100,4,4)],100,4)
        with self.assertRaisesRegex(repaired.Refusal,'conflicting file-offset'):
            repaired.elf_dynamic(fixture(first_filesz=420,second_offset=450))

    def test_virtual_gap_and_zero_fill_are_not_file_backing(self):
        with self.assertRaisesRegex(mapping.Refusal,'non-file-backed virtual gap'):
            mapping.file_backed_virtual_bytes(b'abcdefgh',[(100,3,0),(104,4,4)],100,8)
        with self.assertRaisesRegex(repaired.Refusal,'non-file-backed virtual gap'):
            repaired.elf_dynamic(fixture(first_filesz=409,first_memsz=500,second_va_offset=411))

    def test_outfile_extent_and_missing_dynamic_terminator_refused(self):
        with self.assertRaisesRegex(mapping.Refusal,'load bounds invalid'):
            mapping.file_backed_virtual_bytes(b'abc',[(100,4,0)],100,3)
        raw=bytearray(fixture())
        struct.pack_into('<qQ',raw,240+5*16,1,1)
        with self.assertRaisesRegex(repaired.Refusal,'unterminated ELF dynamic'):
            repaired.elf_dynamic(bytes(raw))

    def test_table_size_and_string_offset_must_be_complete_bounded_bytes(self):
        for length in (0,9):
            with self.assertRaises(mapping.Refusal):
                mapping.file_backed_virtual_bytes(b'abcdefgh',[(100,8,0)],100,length)
        raw=bytearray(fixture())
        struct.pack_into('<qQ',raw,240+2*16,1,1000)
        with self.assertRaisesRegex(repaired.Refusal,'string offset outside table'):
            repaired.elf_dynamic(bytes(raw))

    def test_file_size_exceeding_memory_size_is_invalid_load(self):
        with self.assertRaisesRegex(repaired.Refusal,'file/memory extent is invalid'):
            repaired.elf_dynamic(fixture(first_memsz=409))


if __name__=='__main__':
    unittest.main()
