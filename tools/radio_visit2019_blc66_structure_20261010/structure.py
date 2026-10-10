"""Pure, bounded HDF5 metadata structure planning. No I/O or native imports.

Format references and supported subset are documented in METHOD.md. Cached
bytes are supplied by the separately admitted CLI. Missing ranges are evidence
records only: this module has no fetch callback and never follows raw storage.
"""
import hashlib
import math

MAX_OBJECT_BYTES = 65536
MAX_CACHE_BYTES = 4 * 1024 ** 2
MAX_OBJECTS = 128
MAX_MESSAGES = 2048
MAX_FRAGMENTS = 128
MAX_MISSING_BYTES = 1024 ** 2
MAX_DEPTH = 8
SIGNATURE = b"\x89HDF\r\n\x1a\n"


class Unsupported(ValueError):
    pass


class InvalidMetadata(ValueError):
    pass


class CacheMissing(Exception):
    pass


def require(ok, message):
    if not ok:
        raise InvalidMetadata(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def uint(raw, offset, width):
    require(width in (1, 2, 4, 8) and 0 <= offset <= len(raw) - width,
            "Integer field exceeds typed metadata span")
    return int.from_bytes(raw[offset:offset + width], "little")


def align8(n):
    return (n + 7) // 8 * 8


class MetadataCache:
    """Authenticated spans supplied by caller; overlaps must agree exactly."""
    def __init__(self, ranges, file_size):
        require(isinstance(file_size, int) and file_size >= 96, "Invalid logical file size")
        self.file_size = file_size
        self.ranges = sorted(ranges, key=lambda r: r[0])
        require(0 < len(ranges) <= 128 and sum(len(r[1]) for r in ranges) <= MAX_CACHE_BYTES,
                "Finite cache bound exceeded")
        for i, (start, raw, pin) in enumerate(self.ranges):
            require(isinstance(raw, bytes) and raw and 0 <= start <= file_size - len(raw),
                    "Cached span outside logical source")
            require(pin["bytes"] == len(raw) and pin["sha256"] == sha(raw), "Cache pin differs")
            for other, body, _ in self.ranges[:i]:
                a, b = max(start, other), min(start + len(raw), other + len(body))
                require(a >= b or raw[a - start:b - start] == body[a - other:b - other],
                        "Overlapping cached metadata differs")

    def missing(self, offset, length):
        require(0 < length <= MAX_OBJECT_BYTES and 0 <= offset <= self.file_size - length,
                "Typed metadata extent outside source or object bound")
        cursor, end, gaps = offset, offset + length, []
        for start, raw, _ in self.ranges:
            stop = start + len(raw)
            if stop <= cursor or start >= end:
                continue
            if start > cursor:
                gaps.append((cursor, min(start, end) - cursor))
            cursor = max(cursor, min(stop, end))
        if cursor < end:
            gaps.append((cursor, end - cursor))
        return gaps

    def read(self, offset, length):
        if self.missing(offset, length):
            raise CacheMissing()
        cursor, end, parts = offset, offset + length, []
        while cursor < end:
            start, raw, _ = next(r for r in self.ranges if r[0] <= cursor < r[0] + len(r[1]))
            stop = min(end, start + len(raw))
            parts.append(raw[cursor - start:stop - start])
            cursor = stop
        return b"".join(parts)

    def evidence(self, offset, length, interpretation):
        raw = self.read(offset, length)
        pins = [pin for start, body, pin in self.ranges
                if start < offset + length and offset < start + len(body)]
        return {"offset": offset, "bytes": length, "sha256": sha(raw),
                "interpretation": interpretation, "cache_pins": pins}


class Planner:
    def __init__(self, source_id, cache, file_size):
        require(cache.file_size == file_size, "Cache/source size differs")
        self.source_id, self.cache, self.file_size = source_id, cache, file_size
        self.result = {"source_id": source_id, "status": "UNSET", "superblock": None,
                       "objects": [], "messages": [], "missing_metadata_fragments": [],
                       "unsupported": [], "invalid": [], "HTTP_requests": 0,
                       "spectral_values_read": False, "payload_ranges_proposed": 0}
        self.objects, self.fragment_keys = set(), set()
        self.sb = None

    def read(self, offset, length, object_kind, evidence):
        missing = self.cache.missing(offset, length)
        if missing:
            for start, count in missing:
                key = (start, count, object_kind)
                if key not in self.fragment_keys:
                    self.fragment_keys.add(key)
                    self.result["missing_metadata_fragments"].append({
                        "source_id": self.source_id, "offset": start, "length": count,
                        "range": f"bytes={start}-{start + count - 1}", "object_kind": object_kind,
                        "typed_object_interval_half_open": [offset, offset + length],
                        "typed_parent_evidence": evidence, "payload_pointer": False,
                        "HTTP_authorized": False})
            require(len(self.fragment_keys) <= MAX_FRAGMENTS
                    and sum(x["length"] for x in self.result["missing_metadata_fragments"]) <= MAX_MISSING_BYTES,
                    "Finite missing-fragment bound exceeded")
            raise CacheMissing()
        return self.cache.read(offset, length)

    def pointer(self, offset, width, interpretation, **fields):
        evidence = self.cache.evidence(offset, width, interpretation)
        evidence["encoded_field_hex"] = self.cache.read(offset, width).hex()
        evidence.update(fields)
        return evidence

    def address(self, value):
        require(value != (1 << 64) - 1, "Undefined metadata address")
        result = self.sb["base_address"] + value
        require(0 <= result < self.file_size, "Metadata pointer outside source")
        return result

    def superblock(self):
        # No scanning outside retained signature locations; no requests to find one.
        candidates = []
        for offset in (0, 512, 1024, 2048):
            try:
                if self.cache.read(offset, 8) == SIGNATURE:
                    candidates.append(offset)
            except (CacheMissing, InvalidMetadata):
                pass
        require(len(candidates) == 1, "Expected one cached HDF5 signature at a permitted location")
        offset = candidates[0]
        initial = self.read(offset, 16, "superblock_version_and_width_fields",
                            self.cache.evidence(offset, 8, "HDF5 signature at permitted offset"))
        if initial[8] != 0:
            raise Unsupported("Only version-0 superblocks are supported")
        if initial[13:15] != b"\x08\x08":
            raise Unsupported("First scope supports offset/length widths 8/8 only")
        raw = self.read(offset, 96, "v0_superblock_and_root_symbol_entry",
                        self.cache.evidence(offset, 16, "verified v0 superblock version/width fields"))
        require(raw[9:13] == b"\0\0\0\0" and raw[15] == 0,
                "Unsupported auxiliary superblock versions or reserved fields")
        base, eof = uint(raw, 24, 8), uint(raw, 40, 8)
        if base != offset:
            raise Unsupported("Relocated superblock/base mismatch is not supported")
        require(eof == self.file_size and uint(raw, 16, 2) > 0 and uint(raw, 18, 2) > 0,
                "Superblock EOF or group K differs from authenticated source")
        if uint(raw, 48, 8) != (1 << 64) - 1:
            raise Unsupported("External file-driver metadata is not supported")
        require(uint(raw, 76, 4) == 0 and uint(raw, 72, 4) in (0, 1),
                "Invalid root symbol-table entry")
        root = uint(raw, 64, 8)
        self.sb = {"version": 0, "signature_offset": offset, "offset_width": 8,
                   "length_width": 8, "base_address": base, "absolute_EOF": eof,
                   "group_leaf_K": uint(raw, 16, 2), "group_internal_K": uint(raw, 18, 2),
                   "root_object_header_relative_address": root}
        self.result["superblock"] = self.sb
        return self.address(root), self.pointer(offset + 64, 8, "v0 root symbol-table OH address",
            superblock_evidence=self.cache.evidence(offset, 96, "verified v0 superblock/root entry"))

    def object_header(self, address, evidence, label, depth=0):
        require(depth <= MAX_DEPTH, "Object traversal depth cap exceeded")
        require(address not in self.objects, "Repeated/cyclic object-header address")
        self.objects.add(address)
        require(len(self.objects) <= MAX_OBJECTS, "Object count cap exceeded")
        header = self.read(address, 16, "v1_object_header_prefix", evidence)
        if header[0] != 1:
            raise Unsupported("Only version-1 object headers are supported")
        require(header[1] == 0 and header[12:16] == b"\0" * 4, "Object prefix reserved bytes differ")
        count, size = uint(header, 2, 2), uint(header, 8, 4)
        require(0 < count <= MAX_MESSAGES and 8 <= size <= MAX_OBJECT_BYTES and size % 8 == 0,
                "Invalid bounded object-header message count or size")
        item = {"label": label, "address": address, "version": 1,
                "declared_total_messages": count, "initial_message_bytes": size,
                "parsed_messages": 0, "complete_message_coverage": False}
        self.result["objects"].append(item)
        size_evidence = self.pointer(address + 8, 4, "v1 initial message-block size",
            object_header_address=address,
            header_evidence=self.cache.evidence(address, 16, "verified v1 object-header prefix"))
        state = {"count": 0, "missing": False, "blocks": set(), "links": [], "symbol_tables": []}
        self.message_block(address + 16, size, size_evidence, state, label, depth)
        item["parsed_messages"] = state["count"]
        item["complete_message_coverage"] = not state["missing"]
        if not state["missing"]:
            require(state["count"] == count, "Total message count differs across continuation blocks")
        if label == "root":
            targets = [link for link in state["links"] if link[0] == "data"]
            for tree, heap, parent in state["symbol_tables"]:
                try:
                    targets.extend(self.group_links(tree, heap, parent, depth + 1))
                except CacheMissing:
                    state["missing"] = True
            require(len(targets) <= 1, "Ambiguous duplicate root data links")
            if targets:
                _, target, pointer = targets[0]
                try:
                    self.object_header(target, pointer, "data", depth + 1)
                except CacheMissing:
                    pass
            elif not state["missing"]:
                raise Unsupported("Named root hard link 'data' was not found")

    def message_block(self, address, size, evidence, state, label, depth):
        require(depth <= MAX_DEPTH and address not in state["blocks"], "Continuation depth/cycle invalid")
        state["blocks"].add(address)
        try:
            raw = self.read(address, size, "v1_object_header_messages", evidence)
        except CacheMissing:
            state["missing"] = True
            return
        offset = 0
        while offset < size:
            require(size - offset >= 8, "Incomplete version-1 message envelope")
            kind, length, flags = uint(raw, offset, 2), uint(raw, offset + 2, 2), raw[offset + 4]
            require(raw[offset + 5:offset + 8] == b"\0" * 3 and length % 8 == 0,
                    "Message reserved/alignment fields invalid")
            require(offset + 8 + length <= size, "Message crosses declared block boundary")
            if flags & 2:
                raise Unsupported("Shared object-header messages are not supported")
            require(flags & ~0x7f == 0, "Reserved object-message flag set")
            payload_address = address + offset + 8
            body = raw[offset + 8:offset + 8 + length]
            state["count"] += 1
            require(len(self.result["messages"]) < MAX_MESSAGES, "Aggregate message cap exceeded")
            self.result["messages"].append({"object": label, "offset": address + offset,
                "type": kind, "data_bytes_including_padding": length, "flags": flags,
                "data_sha256": sha(body)})
            try:
                if kind == 0x10:
                    require(length >= 16 and body[16:] == b"\0" * (length - 16), "Invalid continuation payload")
                    target, extent = self.address(uint(body, 0, 8)), uint(body, 8, 8)
                    parent = self.pointer(payload_address, 16, "v1 continuation offset and length",
                        message_type=kind, object_header=label,
                        message_header_evidence=self.cache.evidence(address + offset, 8, "v1 continuation message envelope"))
                    self.message_block(target, extent, parent, state, label, depth + 1)
                elif kind == 0x06:
                    state["links"].append(self.compact_link(body, payload_address))
                elif kind == 0x11:
                    require(length >= 16 and body[16:] == b"\0" * (length - 16), "Invalid symbol-table message")
                    parent = self.pointer(payload_address, 16, "group symbol-table TREE and local HEAP addresses",
                        message_header_evidence=self.cache.evidence(address + offset, 8, "v1 symbol-table message envelope"))
                    state["symbol_tables"].append((self.address(uint(body, 0, 8)), self.address(uint(body, 8, 8)), parent))
                elif kind == 0x0c:
                    self.attribute(body, payload_address)
                elif kind == 8:
                    # Admit the old-library chunked layout envelope only; its
                    # TREE/storage address is deliberately not decoded or followed.
                    require(length >= 3, "Short data-layout message")
                    if body[:2] != b"\x03\x02":
                        raise Unsupported("Only version-3 chunked layout is admitted; no raw storage traversal")
                    dimensions = body[2]
                    require(2 <= dimensions <= 9 and length >= 11 + 4 * dimensions,
                            "Version-3 chunked layout extent invalid")
                elif kind in (0, 1, 3, 4, 5, 0x0a, 0x0b, 0x0d, 0x0e, 0x12):
                    pass  # Recognized, untraversed metadata; no dataset storage pointer is queued.
                else:
                    raise Unsupported(f"Object-header message type 0x{kind:04x} is outside this scope")
            except CacheMissing:
                state["missing"] = True
            offset += 8 + length

    def compact_link(self, raw, absolute):
        require(len(raw) >= 2, "Short link message")
        if raw[0] != 1 or raw[1] & 0xe0:
            raise Unsupported("Unsupported compact link version/flags")
        flags, cursor = raw[1], 2
        if flags & 8:
            raise Unsupported("Soft/external/user-defined links are not followed")
        if flags & 4:
            cursor += 8
        encoding = "ascii"
        if flags & 16:
            require(uint(raw, cursor, 1) == 1, "Unsupported link charset")
            encoding, cursor = "utf-8", cursor + 1
        width = 1 << (flags & 3)
        length = uint(raw, cursor, width)
        cursor += width
        require(0 < length <= 1024 and cursor + length + 8 <= len(raw), "Link extent invalid")
        name = raw[cursor:cursor + length].decode(encoding)
        cursor += length
        target = self.address(uint(raw, cursor, 8))
        require(raw[cursor + 8:] == b"\0" * (len(raw) - cursor - 8), "Compact-link padding differs")
        return name, target, self.pointer(absolute + cursor, 8, "compact hard-link object-header address", link_name=name,
            link_message_evidence=self.cache.evidence(absolute, len(raw), "verified compact hard-link payload"))

    def group_links(self, tree_address, heap_address, evidence, depth):
        """Traverse only legacy group metadata; never raw-chunk TREE type 1."""
        header = self.read(heap_address, 32, "local_heap_header", evidence)
        if header[:4] != b"HEAP" or header[4] != 0:
            raise Unsupported("Only version-0 local heaps are supported")
        require(header[5:8] == b"\0" * 3, "Local heap reserved bytes differ")
        size, data_address = uint(header, 8, 8), self.address(uint(header, 24, 8))
        parent = self.pointer(heap_address + 8, 24, "local-heap segment size/free offset/data address")
        names = self.read(data_address, size, "local_heap_link_names", parent)
        targets, visited = [], set()

        def visit(address, previous, level_depth, pointer):
            require(level_depth <= MAX_DEPTH and address not in visited, "Group TREE cycle/depth invalid")
            visited.add(address)
            require(len(visited) <= MAX_OBJECTS, "Group metadata node cap exceeded")
            raw = self.read(address, 24, "group_tree_header", pointer)
            if raw[:4] != b"TREE" or raw[4] != 0:
                raise Unsupported("Only group TREE type 0 is traversed")
            level, n = raw[5], uint(raw, 6, 2)
            require(0 < n <= min(2 * self.sb["group_internal_K"], 128)
                    and (previous is None or level == previous - 1), "Group TREE count/level invalid")
            extent = 24 + (n + 1) * 8 + n * 8
            node = self.read(address, extent, "group_tree_used_entries",
                             self.pointer(address + 4, 4, "group TREE type/level/entry count"))
            offsets = [uint(node, 24 + 16 * i, 8) for i in range(n + 1)]
            require(all(v < len(names) for v in offsets), "Group TREE name offsets exceed local heap")
            for i in range(n):
                field = address + 32 + 16 * i
                target = self.address(uint(node, 32 + 16 * i, 8))
                parent = self.pointer(field, 8, "group TREE metadata child", level=level)
                if level:
                    visit(target, level, level_depth + 1, parent)
                else:
                    symbols = self.read(target, 8, "symbol_table_node_header", parent)
                    if symbols[:4] != b"SNOD" or symbols[4] != 1:
                        raise Unsupported("Only version-1 symbol-table nodes are supported")
                    require(symbols[5] == 0, "SNOD reserved byte differs")
                    count = uint(symbols, 6, 2)
                    require(count <= min(2 * self.sb["group_leaf_K"], 128), "SNOD count cap exceeded")
                    if not count:
                        continue
                    data = self.read(target + 8, count * 40, "symbol_table_entries",
                                     self.pointer(target + 6, 2, "SNOD symbol count"))
                    for j in range(count):
                        cursor = 40 * j
                        name_offset = uint(data, cursor, 8)
                        require(name_offset < len(names), "Symbol name offset outside heap")
                        end = names.find(b"\0", name_offset)
                        require(end >= name_offset and end - name_offset <= 1024, "Invalid symbol name extent")
                        name = names[name_offset:end].decode("utf-8")
                        kind = uint(data, cursor + 16, 4)
                        require(uint(data, cursor + 20, 4) == 0, "Symbol entry reserved bytes differ")
                        if name == "data":
                            if kind not in (0, 1):
                                raise Unsupported("Named data symbol is not a hard link")
                            ref = self.address(uint(data, cursor + 8, 8))
                            targets.append((name, ref, self.pointer(target + 8 + cursor + 8, 8,
                                "symbol-table hard-link address", link_name=name,
                                symbol_entry_evidence=self.cache.evidence(target + 8 + cursor, 40, "hard-link symbol entry"),
                                symbol_name_evidence=self.cache.evidence(data_address + name_offset, end - name_offset + 1,
                                                                          "data name in verified local heap"))))
        visit(tree_address, None, depth, evidence)
        return targets

    def attribute(self, raw, absolute):
        require(len(raw) >= 8, "Short attribute message")
        version = raw[0]
        if version not in (1, 2):
            raise Unsupported("Only attribute versions 1 and 2 are supported")
        require(raw[1] == 0, "Shared/flagged attributes are not supported")
        name_size, type_size, space_size = (uint(raw, i, 2) for i in (2, 4, 6))
        cursor = 8
        for count in (name_size, type_size, space_size):
            require(count > 0, "Empty attribute component")
        type_start = cursor + (align8(name_size) if version == 1 else name_size)
        space_start = type_start + (align8(type_size) if version == 1 else type_size)
        data_start = space_start + (align8(space_size) if version == 1 else space_size)
        require(data_start <= len(raw), "Attribute components exceed message")
        require(raw[8 + name_size - 1] == 0, "Attribute name lacks its declared NUL terminator")
        datatype, dataspace = raw[type_start:type_start + type_size], raw[space_start:space_start + space_size]
        require(len(datatype) >= 8, "Short attribute datatype")
        type_class, type_version = datatype[0] & 15, datatype[0] >> 4
        if type_version not in (1, 2, 3):
            raise Unsupported("Unsupported attribute datatype version")
        if type_class in (0, 1, 2, 3, 4, 5):
            return  # Fixed types cannot generate heap proposals, regardless of bit patterns.
        if type_class != 9:
            raise Unsupported("Compound/reference/enum/array attribute schemas are not traversed")
        bits = uint(datatype, 1, 2) | datatype[3] << 16
        if bits & 15 != 1 or bits & 0xfff000:
            raise Unsupported("Only variable-length strings are metadata-heap supported")
        require((bits >> 4) & 15 in (0, 1, 2) and (bits >> 8) & 15 in (0, 1),
                "Unsupported VL string padding/character set")
        # Parent unsigned byte: integer class, size1, offset0, precision8, unsigned.
        parent = datatype[8:]
        require(len(parent) >= 12, "Short VL string parent datatype")
        if parent[0] >> 4 not in (1, 2, 3):
            raise Unsupported("Unsupported VL string parent datatype version")
        require(len(parent) >= 12 and parent[0] & 15 == 0 and uint(parent, 4, 4) == 1
                and uint(parent, 8, 2) == 0 and uint(parent, 10, 2) == 8
                and not (parent[1] & 8), "VL string parent is not unsigned byte")
        require(uint(datatype, 4, 4) == 16, "VL descriptor size must match supported 8-byte address format")
        require(len(dataspace) >= 8, "Short attribute dataspace")
        if dataspace[0] != 1:
            raise Unsupported("Unsupported attribute dataspace version")
        rank, flags = dataspace[1], dataspace[2]
        require(rank <= 8 and flags in (0, 1) and dataspace[3:8] == b"\0" * 5,
                "Unsupported attribute dataspace rank/flags")
        require(len(dataspace) >= 8 + rank * 8 * (2 if flags & 1 else 1), "Short attribute dataspace")
        elements = math.prod(uint(dataspace, 8 + 8 * i, 8) for i in range(rank))
        require(0 < elements <= 64 and data_start + elements * 16 <= len(raw), "VL attribute count/extent invalid")
        for i in range(elements):
            cursor = data_start + i * 16
            length, address, index = uint(raw, cursor, 4), uint(raw, cursor + 4, 8), uint(raw, cursor + 12, 4)
            if length == 0 and address == 0 and index == 0:
                continue
            require(length <= MAX_OBJECT_BYTES and index > 0, "Invalid bounded VL metadata identifier")
            evidence = self.pointer(absolute + cursor, 16, "VL string attribute sequence-length/global-heap ID",
                attribute_message_offset=absolute, element=i, heap_object_index=index,
                attribute_header_evidence=self.cache.evidence(absolute, 8, "verified attribute message header"),
                datatype_evidence=self.cache.evidence(absolute + type_start, type_size, "verified VL string datatype"),
                dataspace_evidence=self.cache.evidence(absolute + space_start, space_size, "verified VL attribute dataspace"))
            self.global_heap(self.address(address), index, length, evidence)

    def global_heap(self, address, wanted_index, sequence_length, evidence):
        header = self.read(address, 16, "global_heap_collection_header", evidence)
        if header[:4] != b"GCOL" or header[4] != 1:
            raise Unsupported("Only version-1 global heap collections are supported")
        require(header[5:8] == b"\0" * 3, "Global heap reserved bytes differ")
        size = uint(header, 8, 8)
        require(4096 <= size <= MAX_OBJECT_BYTES and size % 8 == 0
                and address <= self.file_size - size, "Global heap collection extent invalid")
        # Read headers only for other objects; do not fetch unrelated heap data.
        cursor, indices = 16, set()
        next_evidence = {"collection_header": self.cache.evidence(address, 16, "verified GCOL v1 header"),
                         "first_object_relative_offset": 16, "originating_attribute_reference": evidence}
        while cursor + 16 <= size:
            require(len(indices) < MAX_OBJECTS, "Heap object count cap exceeded")
            item = self.read(address + cursor, 16, "global_heap_object_header", next_evidence)
            index, refs, length = uint(item, 0, 2), uint(item, 2, 2), uint(item, 8, 8)
            require(item[4:8] == b"\0" * 4 and index not in indices, "Invalid/duplicate heap object header")
            indices.add(index)
            if index == 0:
                require(refs == 0 and length == size - cursor, "GCOL free object size must include its header")
                break
            extent = 16 + align8(length)
            require(cursor + extent <= size, "Live heap object crosses collection extent")
            if index == wanted_index:
                require(length == sequence_length and refs > 0, "VL attribute length/refcount differs from heap object")
                if length:
                    self.read(address + cursor + 16, length, "referenced_string_attribute_heap_bytes",
                              self.pointer(address + cursor, 16, "referenced GCOL live-object index/refcount/data size",
                                           originating_attribute_reference=evidence))
                return
            next_evidence = {"previous_live_object_header": self.pointer(address + cursor, 16,
                "GCOL live-object index/refcount/data size"),
                "previous_object_relative_offset": cursor, "aligned_data_bytes": align8(length),
                "next_object_relative_offset": cursor + extent,
                "collection_header": self.cache.evidence(address, 16, "verified GCOL v1 header"),
                "originating_attribute_reference": evidence}
            cursor += extent
        raise InvalidMetadata("Referenced VL attribute heap index absent")

    def run(self):
        try:
            address, parent = self.superblock()
            self.object_header(address, parent, "root")
        except CacheMissing:
            pass
        except Unsupported as error:
            self.result["unsupported"].append(str(error))
        except (InvalidMetadata, UnicodeError) as error:
            self.result["invalid"].append(str(error))
        if self.result["invalid"]:
            status = "INVALID_METADATA"
        elif self.result["unsupported"]:
            status = "UNSUPPORTED_FORMAT"
        elif self.result["missing_metadata_fragments"]:
            status = "INCOMPLETE_TYPED_METADATA_FRAGMENTS"
        else:
            status = "COMPLETE_SUPPORTED_HEADER_STRUCTURE"
        self.result["status"] = status
        self.result["counts"] = {"object_headers": len(self.result["objects"]),
            "messages": len(self.result["messages"]),
            "missing_fragments": len(self.result["missing_metadata_fragments"]),
            "missing_bytes": sum(r["length"] for r in self.result["missing_metadata_fragments"])}
        return self.result


def plan_source(source_id, cache, file_size):
    return Planner(source_id, cache, file_size).run()
