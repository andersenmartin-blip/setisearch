"""Synthetic byte fixtures only; this suite does not inspect the host runtime."""

import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest


_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("prepared_elf_metadata", _HERE / "elf_metadata.py")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
parse_elf = _MODULE.parse_elf
ElfMetadataError = _MODULE.ElfMetadataError


def elf_fixture(*, dynamic=True, interpreter=True, extras=(), string_table=None):
    """Construct a tiny disjoint conceptual ELF; never an executable capture."""
    raw = bytearray(2048)
    ident = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    headers = [(1, 5, 0, 0x400000, 0x400000, len(raw), len(raw) + 64, 4096)]
    if dynamic:
        entries = [(5, 0x400500), (10, 128), (1, 1), (1, 13),
                   (14, 25), (15, 37), (29, 47)] + list(extras) + [(0, 0)]
        table = b"\0libfirst.so\0libother.so\0libowned.so\0/old/path\0$ORIGIN/lib\0"
        if string_table is not None:
            table = string_table
        raw[0x500:0x500 + len(table)] = table
        dyn = b"".join(struct.pack("<qQ", *entry) for entry in entries)
        raw[0x300:0x300 + len(dyn)] = dyn
        headers.append((2, 6, 0x300, 0x400300, 0x400300, len(dyn), len(dyn), 8))
    if interpreter:
        interp = b"/synthetic/ld.so\0"
        raw[0x700:0x700 + len(interp)] = interp
        headers.append((3, 4, 0x700, 0x400700, 0x400700, len(interp), len(interp), 1))
    struct.pack_into("<16sHHIQQQIHHHHHH", raw, 0,
                     ident, 3, 62, 1, 0, 64, 0, 0, 64, 56, len(headers), 0, 0, 0)
    for index, header in enumerate(headers):
        struct.pack_into("<IIQQQQQQ", raw, 64 + index * 56, *header)
    return bytes(raw)


def split_load_fixture(*, seam=0x530, second_offset=None, second_vaddr=None):
    """Adjacent disjoint PT_LOADs with one unchanged virtual/file translation."""
    raw = bytearray(elf_fixture())
    original = [struct.unpack_from("<IIQQQQQQ", raw, 64 + index * 56)
                for index in range(3)]
    second_offset = seam if second_offset is None else second_offset
    second_vaddr = 0x400000 + seam if second_vaddr is None else second_vaddr
    headers = [(1, 5, 0, 0x400000, 0x400000, seam, seam, 1),
               (1, 4, second_offset, second_vaddr, second_vaddr,
                len(raw) - second_offset, len(raw) - second_offset, 1),
               original[1], original[2]]
    struct.pack_into("<H", raw, 56, len(headers))
    for index, header in enumerate(headers):
        struct.pack_into("<IIQQQQQQ", raw, 64 + index * 56, *header)
    return bytes(raw)


def changed(raw, offset, fmt, value):
    result = bytearray(raw)
    struct.pack_into(fmt, result, offset, value)
    return bytes(result)


class ElfMetadataTests(unittest.TestCase):
    def assert_rejected(self, raw, text=None, **caps):
        with self.assertRaisesRegex(ElfMetadataError, text or "."):
            parse_elf(raw, **caps)

    def test_selected_metadata_and_intrinsic_hash(self):
        raw = elf_fixture()
        result = parse_elf(raw)
        self.assertEqual(result["needed"], ["libfirst.so", "libother.so"])
        self.assertEqual(result["soname"], "libowned.so")
        self.assertEqual(result["rpath"], "/old/path")
        self.assertEqual(result["runpath"], "$ORIGIN/lib")
        self.assertEqual(result["interpreter"], "/synthetic/ld.so")
        self.assertEqual(result["dynamic_entry_count"], 8)
        self.assertEqual(result["file_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(result["loader_emulation"])

    def test_contiguous_file_backed_string_table_across_adjacent_loads(self):
        raw = split_load_fixture()
        result = parse_elf(raw)
        self.assertEqual(result["needed"], ["libfirst.so", "libother.so"])
        self.assertEqual(result["runpath"], "$ORIGIN/lib")
        self.assertEqual(result["dynamic_string_table_mapping"]["segment_count"], 2)
        self.assertFalse(result["loader_emulation"])

    def test_synthetic_table_geometry_from_separate_pinned_python_preread(self):
        # Numbers are from root's separate current preread, not bytes from the
        # runtime ELF or a claim about the original unnamed failure input.
        raw = bytearray(45056)
        base, strtab, strsz = 4190208, 4191704, 42266
        string_offset = strtab - base
        raw[string_offset:string_offset + 19] = b"\0synthetic-only.so\0"
        raw[string_offset + strsz - 1] = 0
        entries = [(5, strtab), (10, strsz), (1, 1), (0, 0)]
        dynamic = b"".join(struct.pack("<qQ", *entry) for entry in entries)
        raw[512:512 + len(dynamic)] = dynamic
        headers = [(1, 6, 0, base, base, 4096, 4096, 4096),
                   (1, 4, 4096, 4194304, 4194304, len(raw) - 4096, len(raw) - 4096, 4096),
                   (2, 6, 512, base + 512, base + 512, len(dynamic), len(dynamic), 8)]
        ident = b"\x7fELF\x02\x01\x01" + b"\0" * 9
        struct.pack_into("<16sHHIQQQIHHHHHH", raw, 0,
                         ident, 3, 62, 1, 0, 64, 0, 0, 64, 56, 3, 0, 0, 0)
        for index, header in enumerate(headers):
            struct.pack_into("<IIQQQQQQ", raw, 64 + index * 56, *header)
        result = parse_elf(bytes(raw))
        self.assertEqual(result["needed"], ["synthetic-only.so"])
        self.assertEqual(result["dynamic_string_table_mapping"]["virtual_address"], strtab)
        self.assertEqual(result["dynamic_string_table_mapping"]["range_size"], strsz)
        self.assertEqual(result["dynamic_string_table_mapping"]["segment_count"], 2)
        self.assertFalse(result["loader_emulation"])

    def test_adjacent_virtual_but_noncontiguous_file_translation_rejects(self):
        self.assert_rejected(split_load_fixture(second_offset=0x540), "file-backed")

    def test_adjacent_file_but_virtual_gap_rejects(self):
        self.assert_rejected(split_load_fixture(second_vaddr=0x400540), "file-backed")

    def test_adjacent_load_bss_gap_cannot_back_string_table(self):
        raw = split_load_fixture(second_vaddr=0x400540)
        raw = changed(raw, 64 + 40, "<Q", 0x540)
        self.assert_rejected(raw, "file-backed")

    def test_file_backing_rejection_retains_bounded_request_geometry(self):
        raw = changed(elf_fixture(), 0x300 + 8, "<Q", 0x400800)
        with self.assertRaises(ElfMetadataError) as raised:
            parse_elf(raw)
        context = raised.exception.context
        self.assertEqual(context["schema"], "radio-elf-metadata-error-context-v1")
        self.assertEqual(context["table_address"], 0x400800)
        self.assertEqual(context["range_size"], 128)
        self.assertEqual(context["range_end"], 0x400880)
        self.assertEqual(context["stage"], "dynamic string table")
        self.assertEqual(context["candidate_count"], 1)
        self.assertEqual(context["candidates"][0]["reason"], "BSS_ONLY_OR_GAP")
        self.assertEqual(context["file_sha256"], hashlib.sha256(raw).hexdigest())

    def test_error_candidate_samples_are_bounded_without_losing_counts(self):
        raw = bytearray(elf_fixture())
        # Replace program-header table with 40 valid disjoint memory loads and
        # one PT_DYNAMIC. Their file bytes may alias; virtual bytes do not.
        headers = [(1, 4, 0, 0x400000 + index * 0x1000,
                    0x400000 + index * 0x1000, 2048, 2048, 1)
                   for index in range(40)]
        headers.append((2, 6, 0xB00, 0x400B00, 0x400B00, 128, 128, 8))
        raw.extend(b"\0" * (4096 - len(raw)))
        # Increase first load backing so dynamic array exists there; no overlap.
        headers[0] = (1, 4, 0, 0x400000, 0x400000, 4096, 4096, 1)
        table = b"".join(struct.pack("<qQ", *e) for e in
                         [(5, 0x800000), (10, 128), (1, 1), (0, 0)] + [(0, 0)] * 4)
        raw[0xB00:0xB80] = table
        struct.pack_into("<H", raw, 56, len(headers))
        for index, header in enumerate(headers):
            struct.pack_into("<IIQQQQQQ", raw, 64 + index * 56, *header)
        with self.assertRaises(ElfMetadataError) as raised:
            parse_elf(bytes(raw))
        context = raised.exception.context
        self.assertEqual(context["candidate_count"], 40)
        self.assertEqual(len(context["candidates"]), 16)
        self.assertTrue(context["candidates_truncated"])
        self.assertEqual(sum(context["reason_counts"].values()), 40)

    def test_range_overflow_error_has_request_and_no_wrapped_end(self):
        raw = changed(elf_fixture(), 0x300 + 8, "<Q", (1 << 64) - 64)
        with self.assertRaises(ElfMetadataError) as raised:
            parse_elf(raw)
        self.assertEqual(raised.exception.context["table_address"], (1 << 64) - 64)
        self.assertEqual(raised.exception.context["range_size"], 128)
        self.assertIsNone(raised.exception.context["range_end"])

    def test_truncated_header_rejection_still_has_bounded_input_context(self):
        raw = elf_fixture()[:63]
        with self.assertRaises(ElfMetadataError) as raised:
            parse_elf(raw)
        self.assertEqual(raised.exception.context["file_bytes"], 63)
        self.assertIsNone(raised.exception.context["table_address"])
        self.assertEqual(raised.exception.context["candidates"], [])

    def test_static_subset_has_no_dynamic_names(self):
        result = parse_elf(elf_fixture(dynamic=False, interpreter=False))
        self.assertFalse(result["dynamic_present"])
        self.assertEqual(result["needed"], [])
        self.assertIsNone(result["interpreter"])

    def test_unsupported_header_families(self):
        raw = elf_fixture()
        for offset, fmt, value in [(4, "B", 1), (5, "B", 2), (6, "B", 2),
                                   (7, "B", 9), (8, "B", 1), (9, "B", 1),
                                   (16, "<H", 4), (18, "<H", 183), (20, "<I", 2),
                                   (48, "<I", 1), (52, "<H", 65), (54, "<H", 55),
                                   (56, "<H", 0), (56, "<H", 65535)]:
            with self.subTest(offset=offset, value=value):
                self.assert_rejected(changed(raw, offset, fmt, value))

    def test_input_and_header_bounds(self):
        raw = elf_fixture()
        self.assert_rejected(raw[:63])
        self.assert_rejected(bytearray(raw), "exact bytes")
        self.assert_rejected(raw, "input byte bound", max_bytes=2047)
        self.assert_rejected(changed(raw, 32, "<Q", 0), "overlaps")
        self.assert_rejected(changed(raw, 32, "<Q", 2000), "outside")
        self.assert_rejected(changed(raw, 32, "<Q", (1 << 64) - 32), "overflow")

    def test_explicit_caps_only_lower_fixed_ceilings(self):
        raw = elf_fixture()
        for name, value in [("max_bytes", True), ("max_strings", 0),
                            ("max_dynamic_entries", 4097), ("max_string_bytes", -1)]:
            with self.subTest(name=name):
                self.assert_rejected(raw, "invalid", **{name: value})
        self.assert_rejected(raw, "program-header count", max_program_headers=2)
        self.assert_rejected(raw, "dynamic entry bound", max_dynamic_entries=7)
        self.assert_rejected(raw, "string count bound", max_strings=5)
        self.assert_rejected(raw, "string byte bound", max_string_bytes=20)

    def test_load_range_and_alignment_rejections(self):
        raw = elf_fixture()
        # PT_LOAD starts at byte 64. Field offsets: offset=8, vaddr=16,
        # filesz=32, memsz=40, align=48 within the program header.
        for offset, value, text in [(64 + 8, 2040, "outside"),
                                    (64 + 16, (1 << 64) - 1, "overflow"),
                                    (64 + 40, 1000, "exceeds memory"),
                                    (64 + 48, 3, "power of two"),
                                    (64 + 8, 1, "outside")]:
            with self.subTest(offset=offset):
                self.assert_rejected(changed(raw, offset, "<Q", value), text)
        raw = changed(raw, 64 + 32, "<Q", 1800)
        self.assert_rejected(changed(raw, 64 + 8, "<Q", 1), "incongruent")

    def test_duplicate_program_header_and_overlapping_load_reject(self):
        raw = elf_fixture()
        # Change PT_INTERP into a second PT_DYNAMIC.
        self.assert_rejected(changed(raw, 64 + 2 * 56, "<I", 2), "ambiguous")
        # Change PT_INTERP into a second overlapping load.
        self.assert_rejected(changed(raw, 64 + 2 * 56, "<I", 1), "overlapping")

    def test_dynamic_mapping_and_entry_rejections(self):
        raw = elf_fixture()
        dynamic_header = 64 + 56
        self.assert_rejected(changed(raw, dynamic_header + 16, "<Q", 0x400301), "mismatch")
        self.assert_rejected(changed(raw, dynamic_header + 16, "<Q", 0x500300), "file-backed")
        self.assert_rejected(changed(raw, dynamic_header + 32, "<Q", 127), "layout")
        self.assert_rejected(changed(raw, 0x300 + 7 * 16, "<q", 21), "lacks DT_NULL")
        self.assert_rejected(changed(raw, 0x300 + 7 * 16 + 8, "<Q", 1), "DT_NULL")
        self.assert_rejected(changed(raw, 0x300, "<q", -1), "negative")

    def test_nonzero_tail_after_first_null_rejects(self):
        raw = elf_fixture(extras=((0, 0), (21, 0)))
        self.assert_rejected(raw, "after DT_NULL")

    def test_singleton_duplicates_and_missing_tables_reject(self):
        raw = elf_fixture()
        for tag, value in [(5, 0x400500), (10, 128), (14, 25), (15, 37), (29, 47)]:
            with self.subTest(tag=tag):
                self.assert_rejected(elf_fixture(extras=((tag, value),)), "duplicate")
        self.assert_rejected(changed(raw, 0x300, "<q", 21), "requires DT_STRTAB")
        self.assert_rejected(changed(raw, 0x300 + 16 + 8, "<Q", 0), "nonempty")

    def test_loader_dependency_extensions_reject(self):
        for tag in (0x7FFFFFFF, 0x7FFFFFFD, 0x6FFFFEFC, 0x6FFFFEFB):
            with self.subTest(tag=tag):
                self.assert_rejected(elf_fixture(extras=((tag, 1),)), "loader extension")

    def test_other_numeric_dynamic_tags_are_explicitly_uninterpreted(self):
        result = parse_elf(elf_fixture(extras=((0x6FFFFEF5, 0x400600), (30, 8))))
        self.assertEqual(result["uninterpreted_dynamic_tags"], [30, 0x6FFFFEF5])

    def test_virtual_string_table_file_mapping_required(self):
        raw = elf_fixture()
        self.assert_rejected(changed(raw, 0x300 + 8, "<Q", 0x400800), "file-backed")
        self.assert_rejected(changed(raw, 0x300 + 16 + 8, "<Q", (1 << 64) - 1), "overflow")
        # Filesz excludes final 128 bytes while memsz still covers them: BSS
        # cannot supply dynamic strings in the captured file.
        raw = changed(raw, 64 + 32, "<Q", 0x580)
        self.assert_rejected(changed(raw, 0x300 + 8, "<Q", 0x400550), "file-backed")

    def test_string_offsets_termination_encoding_and_boundaries(self):
        raw = elf_fixture()
        self.assert_rejected(changed(raw, 0x300 + 2 * 16 + 8, "<Q", 128), "offset outside")
        self.assert_rejected(changed(raw, 0x300 + 2 * 16 + 8, "<Q", 0), "needed is empty")
        self.assert_rejected(changed(raw, 0x500, "B", 1), "boundary NUL")
        self.assert_rejected(changed(raw, 0x500 + 127, "B", 1), "boundary NUL")
        self.assert_rejected(changed(raw, 0x501, "B", 255), "UTF-8")
        self.assert_rejected(changed(raw, 0x501, "B", 10), "control")
        self.assert_rejected(raw, "string byte bound", max_string_bytes=15)

    def test_needed_duplicates_preserve_order_and_count_toward_caps(self):
        result = parse_elf(elf_fixture(extras=((1, 1),)))
        self.assertEqual(result["needed"], ["libfirst.so", "libother.so", "libfirst.so"])
        self.assert_rejected(elf_fixture(extras=((1, 1),)), "string count", max_strings=6)

    def test_empty_search_path_is_preserved_without_resolution(self):
        raw = elf_fixture()
        result = parse_elf(changed(raw, 0x300 + 6 * 16 + 8, "<Q", 0))
        self.assertEqual(result["runpath"], "")
        self.assertFalse(result["loader_emulation"])

    def test_interpreter_exact_termination_and_aggregate_bound(self):
        raw = elf_fixture()
        self.assert_rejected(changed(raw, 0x700, "B", 0), "empty")
        self.assert_rejected(changed(raw, 0x700 + 2, "B", 0), "after its terminator")
        self.assert_rejected(changed(raw, 0x700 + 16, "B", 1), "missing terminator")
        self.assert_rejected(raw, "string byte bound", max_string_bytes=68)


if __name__ == "__main__":
    unittest.main(verbosity=2)
