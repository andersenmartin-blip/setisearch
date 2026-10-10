"""Pure bounded legacy HDF5 TREE/type-1 metadata planning; no I/O or imports
of native libraries. Caller supplies already authenticated metadata cache bytes.
Leaf raw-chunk addresses are records only and are never read by this module.
"""
import hashlib

MAX_TIME_ROWS = 512
MAX_LEVEL = 15
MAX_NODE_ENTRIES = 64
MAX_NODE_BYTES = 64 + 48 * MAX_NODE_ENTRIES
MAX_NODES = 1024
MAX_FRAGMENTS = 256
MAX_MISSING_BYTES = 1024 ** 2
UNDEFINED = (1 << 64) - 1
MIDPOINT_RULE = 'floor(n_native_frequency_chunks/2); zero-based; fixed before amplitudes'


class InvalidMetadata(ValueError):
    pass


class Unsupported(ValueError):
    pass


class MissingMetadata(Exception):
    pass


def require(ok, message):
    if not ok:
        raise InvalidMetadata(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def uint(raw, offset, width):
    require(width in (1, 2, 4, 8) and 0 <= offset <= len(raw) - width,
            'Integer field exceeds typed metadata extent')
    return int.from_bytes(raw[offset:offset + width], 'little')


class ChunkIndexPlanner:
    def __init__(self, source, cache):
        self.source, self.cache = source, cache
        self.nodes, self.incoming, self.fragment_keys = {}, {}, set()
        self.node_intervals = []
        self.result = {
            'schema': 'SETI_CACHE_ONLY_LEGACY_TREE1_MIDPOINT_PLAN_V1',
            'source_id': source.get('source_id'), 'status': 'UNSET',
            'fixed_midpoint_rule': MIDPOINT_RULE,
            'selected_native': None, 'nodes': [], 'descriptors': [],
            'missing_metadata_fragments': [], 'invalid': [], 'unsupported': [],
            'HTTP_requests': 0, 'HTTP_authorized': False,
            'spectral_values_read': False, 'payload_pointer_followed': False,
            'source_values_admission': 'BLOCKED',
            'independent_validation_admission': 'BLOCKED'}

    def address(self, relative, length=1):
        require(relative != UNDEFINED and type(relative) is int,
                'Undefined metadata or raw-chunk address')
        absolute = self.base + relative
        require(0 <= absolute <= self.file_size - length,
                'Typed address exceeds authenticated source file')
        return absolute

    def pointer_evidence(self, offset, interpretation, **fields):
        evidence = self.cache.evidence(offset, 8, interpretation)
        evidence.update(encoded_field_hex=self.cache.read(offset, 8).hex(), **fields)
        return evidence

    def read_metadata(self, offset, length, kind, evidence):
        require(0 < length <= MAX_NODE_BYTES and 0 <= offset <= self.file_size - length,
                'Typed TREE metadata extent exceeds source or node bound')
        gaps = self.cache.missing(offset, length)
        if gaps:
            for start, size in gaps:
                key = (start, size, kind)
                if key not in self.fragment_keys:
                    self.fragment_keys.add(key)
                    self.result['missing_metadata_fragments'].append({
                        'source_id': self.source['source_id'],
                        'offset': start, 'length': size,
                        'range': f'bytes={start}-{start + size - 1}',
                        'object_kind': kind,
                        'typed_object_interval_half_open': [offset, offset + length],
                        'typed_parent_evidence': evidence,
                        'payload_pointer': False, 'HTTP_authorized': False})
            require(len(self.fragment_keys) <= MAX_FRAGMENTS and
                    sum(x['length'] for x in self.result['missing_metadata_fragments']) <= MAX_MISSING_BYTES,
                    'Finite TREE metadata proposal bound exceeded')
            raise MissingMetadata()
        return self.cache.read(offset, length)

    def admit_source(self):
        s = self.source
        require(s['status'] == 'COMPLETE_HEADER_METADATA_ONLY',
                'Complete qualified header metadata record required')
        self.file_size = s['source_file_bytes']
        require(type(self.file_size) is int and self.file_size == self.cache.file_size,
                'Authenticated cache/source size differs')
        shape, chunks = s['shape'], s['chunks']
        if not (len(shape) == len(chunks) == 3 and shape[1] == chunks[0] == chunks[1] == 1
                and s['dtype_string'] == '<f4' and s['dtype_itemsize_bytes'] == 4):
            raise Unsupported('Only little-endian float32 [time,1,frequency], [1,1,N] chunks supported')
        require(all(type(x) is int and x > 0 for x in shape + chunks)
                and 1 <= shape[0] <= MAX_TIME_ROWS and chunks[2] <= shape[2],
                'Invalid or unsupported finite dataset geometry')
        sb = s['superblock']
        if not (sb['version'] == 0 and sb['offset_width'] == sb['length_width'] == 8):
            raise Unsupported('Only qualified v0 superblock offset/length widths8/8 supported')
        require(sb['absolute_EOF'] == self.file_size and type(sb['base_address']) is int,
                'Qualified superblock source EOF differs')
        self.base = sb['base_address']
        require(0 <= self.base < self.file_size, 'Superblock base exceeds source')
        self.shape, self.chunks = shape, chunks
        filters = s['creation_filters']
        require(isinstance(filters, list) and len(filters) <= 8,
                'Finite admitted creation-filter pipeline required')
        self.filter_count = len(filters)
        native_count = (shape[2] + chunks[2] - 1) // chunks[2]
        ordinal = native_count // 2
        self.start = ordinal * chunks[2]
        count = min(chunks[2], shape[2] - self.start)
        expected = {'native_ordinal_zero_based': ordinal,
                    'absolute_channel_start': self.start, 'channel_count': count}
        require(s['fixed_midpoint_rule'] == MIDPOINT_RULE
                and s['metadata_derived_midpoint'] == expected
                and s['native_chunks_along_frequency'] == native_count,
                'Header-derived midpoint differs from fixed pre-amplitude rule')
        self.result['selected_native'] = dict(expected,
            native_chunk_channel_count=chunks[2], native_chunks_along_frequency=native_count,
            actual_time_rows=shape[0], decoded_full_chunk_bytes=chunks[2] * 4,
            logical_channel_interval_half_open=[self.start, self.start + count])
        layout = s['chunk_layout']
        if not (layout['layout_version'] == 3 and layout['layout_class'] == 2
                and layout['dimensionality_including_element_size'] == 4):
            raise Unsupported('Only qualified version3/class2/rank4 legacy chunk-index layout supported')
        offset = layout['layout_message_offset']
        require(not self.cache.missing(offset, 8),
                'Previously qualified layout envelope absent from authenticated cache')
        envelope = self.cache.read(offset, 8)
        length = uint(envelope, 2, 2)
        require(uint(envelope, 0, 2) == 8 and 27 <= length <= 65536,
                'Verified layout-message envelope differs')
        require(not self.cache.missing(offset + 8, length),
                'Previously qualified layout body absent from authenticated cache')
        body = self.cache.read(offset + 8, length)
        require(sha(body) == layout['layout_message_body_sha256'] and body[:3] == b'\x03\x02\x04',
                'Verified data layout-message body differs')
        dimensions = [uint(body, 11 + i * 4, 4) for i in range(4)]
        require(dimensions == chunks + [4] == layout['encoded_dimensions'],
                'Verified layout dimensions differ from qualified chunk shape')
        root_relative = uint(body, 3, 8)
        self.root = self.address(root_relative, 24)
        require(layout['pointer_field_offset'] == offset + 11
                and layout['pointer_field_hex'] == body[3:11].hex()
                and root_relative == layout['chunk_index_root_relative_address']
                and self.root == layout['chunk_index_root_absolute_address'],
                'Verified root pointer fields differ')
        require(layout['metadata_evidence']['offset'] == offset
                and layout['metadata_evidence']['bytes'] == 8 + length
                and layout['metadata_evidence']['sha256'] == sha(envelope + body),
                'Verified layout metadata evidence differs')
        self.root_evidence = self.pointer_evidence(offset + 11,
            'Qualified v3/class2 layout legacy TREE root address',
            layout_message_evidence=self.cache.evidence(offset, 8 + length,
                'Actual cached qualified data-object chunk-layout message'))

    def node(self, address, parent_evidence, expected_level, lower, upper):
        if address not in self.nodes:
            header = self.read_metadata(address, 24, 'legacy_TREE1_node_header', parent_evidence)
            if header[:4] != b'TREE' or header[4] != 1:
                raise Unsupported('Typed chunk-index pointer does not address a legacy TREE/type1 node')
            level, used = header[5], uint(header, 6, 2)
            require(level <= MAX_LEVEL and 1 <= used <= MAX_NODE_ENTRIES,
                    'TREE node level or used-entry count exceeds supported finite bounds')
            extent = 64 + 48 * used
            for a, b in self.node_intervals:
                require(address + extent <= a or b <= address,
                        'Distinct typed TREE node extents overlap')
            require(len(self.nodes) < MAX_NODES, 'Finite TREE node count exceeded')
            evidence = self.cache.evidence(address, 24,
                'TREE/type1 header: level and used-entry count establish64+48*n extent')
            evidence.update(node_entries_used=used, node_used_extent_bytes=extent,
                            incoming_pointer_evidence=parent_evidence)
            raw = self.read_metadata(address, extent, 'legacy_TREE1_used_keys_and_children', evidence)
            siblings = [uint(raw, 8, 8), uint(raw, 16, 8)]
            require(all(x == UNDEFINED or self.address(x, 24) != address for x in siblings),
                    'Invalid self-referencing TREE sibling')
            keys, pointers = [], []
            for i in range(used + 1):
                key_offset = 24 + 48 * i
                coordinates = tuple(uint(raw, key_offset + 8 + j * 8, 8) for j in range(4))
                require(coordinates[3] == 0, 'TREE key element placeholder must be zero')
                keys.append({'coordinates': coordinates,
                             'stored_bytes': uint(raw, key_offset, 4),
                             'filter_mask': uint(raw, key_offset + 4, 4),
                             'field_offset': address + key_offset})
                if i < used:
                    pointer_offset = address + key_offset + 40
                    relative = uint(raw, key_offset + 40, 8)
                    self.address(relative, 24 if level else 1)
                    pointers.append({'relative': relative, 'field_offset': pointer_offset})
                    c = coordinates
                    require(all(c[j] < self.shape[j] and c[j] % self.chunks[j] == 0
                                for j in range(3)),
                            'Real TREE lower key is outside dataset or chunk alignment')
            require(all(keys[i]['coordinates'] < keys[i + 1]['coordinates'] for i in range(used)),
                    'TREE coordinate keys are not strictly sorted')
            node = {'address': address, 'level': level, 'entries_used': used,
                    'used_extent_bytes': extent, 'sha256': sha(raw),
                    'metadata_evidence': self.cache.evidence(address, extent,
                        'Complete used TREE/type1 header, keys and child pointers'),
                    'keys': keys, 'children': pointers,
                    'siblings_relative': siblings, 'siblings_followed': False}
            self.nodes[address] = node
            self.node_intervals.append((address, address + extent))
            self.result['nodes'].append(node)
        node = self.nodes[address]
        require(expected_level is None or node['level'] == expected_level,
                'TREE child level does not descend by exactly one')
        coordinates = [k['coordinates'] for k in node['keys']]
        require((lower is None or coordinates[0] >= lower)
                and (upper is None or coordinates[-1] <= upper),
                'TREE child key extent escapes parent interval')
        return node

    def select_row(self, row):
        target = (row, 0, self.start, 0)
        address, evidence = self.root, self.root_evidence
        expected_level, lower, upper = None, None, None
        visited, traversal = set(), []
        for _ in range(MAX_LEVEL + 1):
            require(address not in visited, 'Cyclic TREE traversal')
            visited.add(address)
            node = self.node(address, evidence, expected_level, lower, upper)
            keys = node['keys']
            matches = [i for i in range(node['entries_used'])
                       if keys[i]['coordinates'] <= target < keys[i + 1]['coordinates']]
            require(len(matches) == 1, 'Target has no unique TREE key interval')
            index = matches[0]
            key, pointer = keys[index], node['children'][index]
            traversal.append({'node_address': address, 'level': node['level'],
                              'node_sha256': node['sha256'], 'selected_child_index': index,
                              'key_interval': [list(key['coordinates']), list(keys[index + 1]['coordinates'])]})
            evidence = self.pointer_evidence(pointer['field_offset'],
                'Internal TREE child metadata address' if node['level'] else 'Leaf raw-chunk address; never followed',
                node_header_evidence=self.cache.evidence(address, 24, 'Verified TREE/type1 node header'),
                selected_key_evidence=self.cache.evidence(key['field_offset'], 40,
                    'Verified selected rank4 chunk coordinate key'),
                node_level=node['level'], selected_child_index=index)
            if node['level'] == 0:
                require(key['coordinates'] == target, 'Leaf chunk origin differs from exact midpoint target')
                require(key['stored_bytes'] > 0
                        and key['filter_mask'] >> self.filter_count == 0,
                        'Leaf stored length or filter mask differs from admitted pipeline')
                payload = self.address(pointer['relative'], key['stored_bytes'])
                return {'time_row': row, 'coordinates': list(target),
                        'source_channel_start': self.start,
                        'logical_channel_count': self.result['selected_native']['channel_count'],
                        'decoded_full_chunk_bytes': self.chunks[2] * 4,
                        'file_offset': payload, 'size': key['stored_bytes'],
                        'filter_mask': key['filter_mask'],
                        'payload_interval_half_open': [payload, payload + key['stored_bytes']],
                        'typed_leaf_pointer_evidence': evidence, 'metadata_traversal': traversal,
                        'payload_pointer_followed': False, 'HTTP_authorized': False}
            next_address = self.address(pointer['relative'], 24)
            require(next_address not in visited, 'Cyclic TREE child metadata pointer')
            incoming = (address, index, key['coordinates'], keys[index + 1]['coordinates'])
            require(next_address not in self.incoming or self.incoming[next_address] == incoming,
                    'TREE metadata child has conflicting parent intervals')
            self.incoming[next_address] = incoming
            address, expected_level = next_address, node['level'] - 1
            lower, upper = key['coordinates'], keys[index + 1]['coordinates']
        raise InvalidMetadata('Finite TREE traversal depth exceeded')

    def run(self):
        try:
            self.admit_source()
            for row in range(self.shape[0]):
                try:
                    self.result['descriptors'].append(self.select_row(row))
                except MissingMetadata:
                    pass
            spans = sorted((d['file_offset'], d['file_offset'] + d['size'])
                           for d in self.result['descriptors'])
            require(all(spans[i][1] <= spans[i + 1][0] for i in range(len(spans) - 1)),
                    'Selected distinct time-row raw chunk intervals overlap')
            require(all(b <= x or y <= a for a, b in spans for x, y in self.node_intervals),
                    'Selected raw chunk interval overlaps admitted TREE metadata')
        except Unsupported as error:
            self.result['unsupported'].append(str(error))
        except (InvalidMetadata, KeyError, TypeError, ValueError, IndexError) as error:
            self.result['invalid'].append(str(error))
        self.result['status'] = ('INVALID_METADATA' if self.result['invalid'] else
            'UNSUPPORTED_FORMAT' if self.result['unsupported'] else
            'INCOMPLETE_TYPED_CHUNK_INDEX_METADATA' if self.result['missing_metadata_fragments'] else
            'COMPLETE_SELECTED_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION')
        if self.result['status'].startswith('COMPLETE_'):
            require(len(self.result['descriptors']) == self.shape[0],
                    'Complete plan lacks exact actual time-row descriptors')
        self.result['expected_descriptor_count'] = getattr(self, 'shape', [None])[0]
        self.result['completed_descriptor_count'] = len(self.result['descriptors'])
        self.result['metadata_nodes_read'] = len(self.nodes)
        self.result['requested_metadata_bytes'] = sum(x['length'] for x in self.result['missing_metadata_fragments'])
        self.result['selected_payload_bytes_recorded_not_requested'] = sum(d['size'] for d in self.result['descriptors'])
        return self.result


def plan_source(source, cache):
    """Pure metadata plan for one future qualified actual source; no cache fetch."""
    return ChunkIndexPlanner(source, cache).run()
