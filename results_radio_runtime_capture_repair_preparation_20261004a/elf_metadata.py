"""Bounded, pure ELF64 metadata extraction for prospective runtime capture.

This supports a conservative subset: little-endian x86-64 ET_EXEC/ET_DYN,
ordinary program headers, uniquely file-backed dynamic/string tables that may
span adjacent loads with one continuous virtual-to-file translation,
and UTF-8 metadata strings without control characters. Rejection is not a
claim that the input could not run on Linux. No file is opened and no ELF
code, loader, subprocess, plugin, or credential is invoked here. Parsed
DT_NEEDED names are not a runtime dependency-resolution attestation.

Layout references (read 2026-10-04):
https://gabi.xinuos.com/elf/02-eheader.html
https://gabi.xinuos.com/elf/07-pheader.html
https://gabi.xinuos.com/elf/08-dynamic.html
"""

import hashlib
import struct


class ElfMetadataError(ValueError):
    """Input rejection with bounded geometry; never a partial metadata result."""
    def __init__(self, message, context=None):
        super().__init__(message)
        self.context = {} if context is None else context


_U64_MAX = (1 << 64) - 1
_EHEADER = struct.Struct("<16sHHIQQQIHHHHHH")
_PHEADER = struct.Struct("<IIQQQQQQ")
_DYNAMIC = struct.Struct("<qQ")
_STRING_TAGS = {1: "needed", 14: "soname", 15: "rpath", 29: "runpath"}
_SINGLETON_TAGS = {5, 10, 14, 15, 29}
# These extensions can add loader dependencies beyond DT_NEEDED. Unsupported
# means explicit rejection, never a silently incomplete dependency list.
_LOADER_EXTENSION_TAGS = {0x7FFFFFFF, 0x7FFFFFFD, 0x6FFFFEFC, 0x6FFFFEFB}
_CAP_CEILINGS = {
    "max_bytes": 64 * 1024 * 1024,
    "max_program_headers": 1024,
    "max_dynamic_entries": 4096,
    "max_strings": 512,
    "max_string_bytes": 65536,
}


def _require(condition, message, context=None):
    if not condition:
        raise ElfMetadataError(message, context)


def _end(start, size, label):
    _require(start <= _U64_MAX - size, label + " unsigned range overflow")
    return start + size


def _file_range(start, size, file_bytes, label):
    end = _end(start, size, label)
    _require(end <= file_bytes, label + " lies outside input bytes")
    return end


def parse_elf(raw, *, max_bytes=64 * 1024 * 1024,
              max_program_headers=1024, max_dynamic_entries=4096,
              max_strings=512, max_string_bytes=65536):
    """Pure bounded metadata or a contextual rejection, never loader proof.

    Complete requested virtual ranges must have disjoint PT_LOAD backing and
    one continuous virtual-to-file translation. Adjacent load segments may
    jointly provide that backing; BSS, gaps and changed translations cannot.
    Rejection context samples at most16 load candidates while retaining total
    counts. Input hashes are emitted only for bytes within the fixed input cap.
    Section headers, runtime relocation and loader behavior are not certified.
    """
    try:
        return _parse_elf(raw, max_bytes=max_bytes,
                          max_program_headers=max_program_headers,
                          max_dynamic_entries=max_dynamic_entries,
                          max_strings=max_strings, max_string_bytes=max_string_bytes)
    except ElfMetadataError as exc:
        context = {"schema": "radio-elf-metadata-error-context-v1",
                   "file_bytes": len(raw) if type(raw) is bytes else None,
                   "file_sha256": hashlib.sha256(raw).hexdigest()
                       if type(raw) is bytes and len(raw) <= _CAP_CEILINGS["max_bytes"] else None,
                   "stage": "ELF metadata subset",
                   "table_address": None, "range_size": None, "range_end": None,
                   "candidate_count": 0, "candidates": [],
                   "candidates_truncated": False, "reason_counts": {},
                   "loader_emulation": False,
                   "parser_subset": "ELF64_LE_X86_64_ET_EXEC_ET_DYN_UNIQUE_CONTIGUOUS_FILE_BACKING"}
        context.update(exc.context)
        exc.context = context
        raise


def _parse_elf(raw, *, max_bytes, max_program_headers, max_dynamic_entries,
               max_strings, max_string_bytes):
    limits = dict(max_bytes=max_bytes, max_program_headers=max_program_headers,
                  max_dynamic_entries=max_dynamic_entries,
                  max_strings=max_strings, max_string_bytes=max_string_bytes)
    for name, value in limits.items():
        _require(type(value) is int and 0 < value <= _CAP_CEILINGS[name],
                 "invalid " + name)
    _require(type(raw) is bytes, "input must be exact bytes")
    _require(_EHEADER.size <= len(raw) <= max_bytes, "input byte bound")
    (ident, elf_type, machine, version, _entry, phoff, _shoff, flags,
     ehsize, phentsize, phnum, _shentsize, _shnum, _shstrndx) = _EHEADER.unpack_from(raw)
    _require(ident[:4] == b"\x7fELF", "ELF magic")
    _require(ident[4] == 2 and ident[5] == 1, "ELF64 little-endian required")
    _require(ident[6] == 1 and version == 1, "ELF version")
    _require(ident[7] in (0, 3) and ident[8] == 0 and ident[9:] == b"\0" * 7,
             "unsupported ABI or identification padding")
    _require(elf_type in (2, 3) and machine == 62 and flags == 0,
             "x86-64 ET_EXEC/ET_DYN required")
    _require(ehsize == _EHEADER.size and phentsize == _PHEADER.size,
             "unsupported ELF/program-header layout")
    _require(0 < phnum <= max_program_headers and phnum != 0xFFFF,
             "program-header count bound or extended numbering")
    _require(phoff >= ehsize, "program-header table overlaps ELF header")
    _file_range(phoff, phnum * phentsize, len(raw), "program-header table")
    loads, dynamics, interps = [], [], []
    for index in range(phnum):
        (kind, pflags, offset, vaddr, _paddr, filesz, memsz,
         align) = _PHEADER.unpack_from(raw, phoff + index * phentsize)
        if kind == 0:  # PT_NULL contents are unspecified.
            continue
        _end(vaddr, memsz, "segment virtual address")
        _file_range(offset, filesz, len(raw), "segment file range")
        if kind in (1, 2, 3):
            _require(filesz <= memsz, "segment file size exceeds memory size")
        if kind == 1:
            _require(align in (0, 1) or (align & (align - 1)) == 0,
                     "PT_LOAD alignment is not a power of two")
            if align > 1:
                _require(offset % align == vaddr % align, "PT_LOAD incongruent alignment")
            loads.append(dict(offset=offset, vaddr=vaddr, filesz=filesz,
                              memsz=memsz, flags=pflags, align=align))
        elif kind == 2:
            dynamics.append(dict(offset=offset, vaddr=vaddr, filesz=filesz))
        elif kind == 3:
            interps.append(dict(offset=offset, filesz=filesz))
    _require(loads, "at least one PT_LOAD required")
    _require(len(dynamics) <= 1 and len(interps) <= 1,
             "ambiguous PT_DYNAMIC or PT_INTERP segments")
    # Program-header PT_LOAD elements must be in ascending virtual-address
    # order. Reject actual byte-range overlap, without emulating page mapping.
    previous_end = None
    for segment in loads:
        if previous_end is not None:
            _require(segment["vaddr"] >= previous_end, "overlapping or unordered PT_LOAD")
        previous_end = _end(segment["vaddr"], segment["memsz"], "PT_LOAD memory range")

    def file_offset(vaddr, size, label):
        context = {"stage": label, "table_address": vaddr, "range_size": size,
                   "range_end": None, "candidate_count": len(loads),
                   "candidates": [], "candidates_truncated": len(loads) > 16,
                   "reason_counts": {}}
        _require(vaddr <= _U64_MAX - size,
                 label + " unsigned range overflow", context)
        requested_end = vaddr + size
        context["range_end"] = requested_end
        covered = []
        for index, segment in enumerate(loads):
            backed_end = _end(segment["vaddr"], segment["filesz"], "PT_LOAD backed range")
            memory_end = _end(segment["vaddr"], segment["memsz"], "PT_LOAD memory range")
            lo, hi = max(vaddr, segment["vaddr"]), min(requested_end, backed_end)
            if lo < hi:
                reason = "FULL_FILE_BACKED" if lo == vaddr and hi == requested_end else "PARTIAL_FILE_BACKED"
                covered.append((lo, hi, segment["offset"] - segment["vaddr"], index))
            elif requested_end <= segment["vaddr"]:
                reason = "BEFORE_SEGMENT"
            elif vaddr >= backed_end and vaddr < memory_end:
                reason = "BSS_ONLY_OR_GAP"
            else:
                reason = "AFTER_FILE_BACKED_RANGE"
            context["reason_counts"][reason] = context["reason_counts"].get(reason, 0) + 1
            if index < 16:
                context["candidates"].append({
                    "load_index": index, "vaddr": segment["vaddr"],
                    "file_backed_end": backed_end, "memory_end": memory_end,
                    "file_offset": segment["offset"], "file_bytes": segment["filesz"],
                    "reason": reason})
        cursor = vaddr
        translation = None
        contributing = []
        for lo, hi, delta, index in covered:
            _require(lo == cursor, label + " has no unique file-backed PT_LOAD coverage", context)
            if translation is None:
                translation = delta
            _require(delta == translation,
                     label + " has no continuous file-backed PT_LOAD translation", context)
            cursor = hi
            contributing.append(index)
        _require(cursor == requested_end and translation is not None,
                 label + " has no unique file-backed PT_LOAD coverage", context)
        offset = vaddr + translation
        _file_range(offset, size, len(raw), label)
        return offset, {"virtual_address": vaddr, "range_size": size,
                        "file_offset": offset, "segment_count": len(contributing),
                        "load_indices": contributing,
                        "continuous_file_translation": True,
                        "loader_emulation": False}

    string_count = 0
    string_bytes = 0

    def decode_string(start, end, label, allow_empty=False):
        nonlocal string_count, string_bytes
        _require(string_count < max_strings, "string count bound")
        remaining = max_string_bytes - string_bytes
        terminator = raw.find(b"\0", start, min(end, start + remaining + 1))
        _require(terminator >= start, label + " missing terminator or string byte bound")
        encoded = raw[start:terminator]
        _require(allow_empty or encoded, label + " is empty")
        try:
            value = encoded.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ElfMetadataError(label + " is not supported UTF-8") from exc
        _require(not any(ord(char) < 32 or ord(char) == 127 for char in value),
                 label + " contains control characters")
        string_count += 1
        string_bytes += len(encoded)
        return value, terminator

    interpreter = None
    if interps:
        segment = interps[0]
        _require(segment["filesz"] > 1, "empty PT_INTERP")
        end = segment["offset"] + segment["filesz"]
        interpreter, terminator = decode_string(segment["offset"], end, "PT_INTERP")
        _require(terminator == end - 1, "PT_INTERP has bytes after its terminator")

    entries = []
    dynamic_entry_count = 0
    if dynamics:
        segment = dynamics[0]
        _require(segment["filesz"] >= _DYNAMIC.size and
                 segment["filesz"] % _DYNAMIC.size == 0, "PT_DYNAMIC entry layout")
        slots = segment["filesz"] // _DYNAMIC.size
        _require(slots <= max_dynamic_entries, "dynamic entry bound")
        mapped, _dynamic_mapping = file_offset(segment["vaddr"], segment["filesz"], "PT_DYNAMIC")
        _require(mapped == segment["offset"], "PT_DYNAMIC address/offset mismatch")
        terminated = False
        for index in range(slots):
            tag, value = _DYNAMIC.unpack_from(raw, segment["offset"] + index * _DYNAMIC.size)
            if terminated:
                _require(tag == 0 and value == 0, "nonzero dynamic data after DT_NULL")
                continue
            dynamic_entry_count += 1
            _require(tag >= 0, "unsupported negative dynamic tag")
            if tag == 0:
                _require(value == 0, "unsupported nonzero DT_NULL value")
                terminated = True
            else:
                _require(tag not in _LOADER_EXTENSION_TAGS, "unsupported loader extension tag")
                entries.append((tag, value))
        _require(terminated, "PT_DYNAMIC lacks DT_NULL")

    singleton = {}
    for tag, value in entries:
        if tag in _SINGLETON_TAGS:
            _require(tag not in singleton, "duplicate singleton dynamic tag")
            singleton[tag] = value
    needed, soname, rpath, runpath = [], None, None, None
    string_mapping = None
    if dynamics:
        _require(5 in singleton and 10 in singleton and singleton[10] > 0,
                 "PT_DYNAMIC requires DT_STRTAB and nonempty DT_STRSZ")
        strsz = singleton[10]
        string_start, string_mapping = file_offset(singleton[5], strsz, "dynamic string table")
        string_end = string_start + strsz
        _require(raw[string_start] == 0 and raw[string_end - 1] == 0,
                 "dynamic string table boundary NULs")
        for tag, offset in entries:
            if tag not in _STRING_TAGS:
                continue
            _require(offset < strsz, "dynamic string offset outside DT_STRSZ")
            value, _terminator = decode_string(string_start + offset, string_end,
                                              _STRING_TAGS[tag], tag in (15, 29))
            if tag == 1:
                needed.append(value)
            elif tag == 14:
                soname = value
            elif tag == 15:
                rpath = value
            else:
                runpath = value
    return {
        "schema": "radio-elf64-metadata-preparation-v1",
        "file_bytes": len(raw), "file_sha256": hashlib.sha256(raw).hexdigest(),
        "elf_class": 64, "endianness": "little", "machine": machine,
        "elf_type": elf_type, "interpreter": interpreter, "needed": needed,
        "rpath": rpath, "runpath": runpath, "soname": soname,
        "program_header_count": phnum, "load_segments": loads,
        "dynamic_present": bool(dynamics), "dynamic_entry_count": dynamic_entry_count,
        "dynamic_string_table_mapping": string_mapping,
        "uninterpreted_dynamic_tags": sorted({tag for tag, _ in entries
                                                if tag not in _STRING_TAGS and tag not in (5, 10)}),
        "loader_emulation": False,
    }
