"""Distinct V2 stdlib-only hand-built TREE1 fixtures; original20 preserved. Root alone runs after review.

This file never opens real caches, invokes h5py/NumPy, fetches anything or reads
raw payloads. --source requires the reviewed pure planner SHA.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(value, width):
    return value.to_bytes(width, 'little')


def key(coords, size=8, mask=0):
    return enc(size, 4) + enc(mask, 4) + b''.join(enc(c, 8) for c in coords)


def node(level, origins, children, size=8, mask=0):
    assert len(origins) == len(children) + 1
    header = b'TREE' + bytes([1, level]) + enc(len(children), 2) + b'\xff' * 16
    body = b''.join(key(c, size, mask) + enc(child, 8)
                    for c, child in zip(origins[:-1], children))
    return header + body + key(origins[-1], 0, 0)


class ToyCache:
    """Independent span cache logs reads and forbids every toy payload interval."""
    def __init__(self, ranges, file_size=65536, payloads=()):
        self.ranges = sorted(ranges)
        self.file_size, self.payloads, self.reads = file_size, payloads, []

    def missing(self, offset, length):
        assert 0 < length <= 65536 and 0 <= offset <= self.file_size - length
        cursor, end, gaps = offset, offset + length, []
        for start, raw in self.ranges:
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
        assert not any(offset < end and start < offset + length for start, end in self.payloads), \
            'Planner attempted to read toy raw payload'
        assert not self.missing(offset, length), 'Planner read a missing metadata span'
        self.reads.append((offset, length))
        result, cursor, end = [], offset, offset + length
        while cursor < end:
            start, raw = next(r for r in self.ranges if r[0] <= cursor < r[0] + len(r[1]))
            stop = min(end, start + len(raw))
            result.append(raw[cursor - start:stop - start])
            cursor = stop
        return b''.join(result)

    def evidence(self, offset, length, interpretation):
        raw = self.read(offset, length)
        return {'offset': offset, 'bytes': length, 'sha256': sha(raw),
                'interpretation': interpretation,
                'cache_pins': [{'path': 'TOY_ONLY', 'bytes': len(raw), 'sha256': sha(raw)}]}


def source_layout(base=0, ntime=2, nfreq=160, channels=16):
    shape, chunks = [ntime, 1, nfreq], [1, 1, channels]
    native = (nfreq + channels - 1) // channels
    ordinal, start = native // 2, (native // 2) * channels
    body = b'\x03\x02\x04' + enc(1024, 8) + b''.join(enc(c, 4) for c in chunks + [4])
    envelope = enc(8, 2) + enc(len(body), 2) + b'\0' * 4
    offset = base + 64
    raw = envelope + body
    source = {'source_id': 'TOY', 'status': 'COMPLETE_HEADER_METADATA_ONLY',
        'source_file_bytes': 65536, 'shape': shape, 'chunks': chunks,
        'dtype_string': '<f4', 'dtype_itemsize_bytes': 4, 'creation_filters': [['TOY_FILTER']],
        'superblock': {'version': 0, 'offset_width': 8, 'length_width': 8,
            'absolute_EOF': 65536, 'base_address': base},
        'native_chunks_along_frequency': native,
        'fixed_midpoint_rule': 'floor(n_native_frequency_chunks/2); zero-based; fixed before amplitudes',
        'metadata_derived_midpoint': {'native_ordinal_zero_based': ordinal,
            'absolute_channel_start': start, 'channel_count': min(channels, nfreq - start)},
        'chunk_layout': {'layout_version': 3, 'layout_class': 2,
            'dimensionality_including_element_size': 4,
            'encoded_dimensions': chunks + [4],
            'chunk_index_root_relative_address': 1024,
            'chunk_index_root_absolute_address': base + 1024,
            'pointer_field_offset': offset + 11, 'pointer_field_hex': body[3:11].hex(),
            'layout_message_offset': offset, 'layout_message_body_sha256': sha(body),
            'metadata_evidence': {'offset': offset, 'bytes': len(raw), 'sha256': sha(raw)}}}
    return source, [(offset, raw)], start


def leaf_scene(base=0, ntime=2, nfreq=160, channels=16, mask=0):
    s, ranges, start = source_layout(base, ntime, nfreq, channels)
    origins = [(r, 0, start, 0) for r in range(ntime)] + [(ntime, 0, 0, 0)]
    raw = node(0, origins, [50000 + 100 * r for r in range(ntime)], mask=mask)
    ranges.append((base + 1024, raw))
    payloads = [(base + 50000 + 100 * r, base + 50008 + 100 * r) for r in range(ntime)]
    return s, ToyCache(ranges, payloads=payloads)


def internal_scene():
    s, ranges, start = source_layout()
    a, b, sentinel = (0, 0, start, 0), (1, 0, start, 0), (2, 0, 0, 0)
    ranges += [(1024, node(1, [a, b, sentinel], [4096, 8192])),
               (4096, node(0, [a, b], [50000])),
               (8192, node(0, [b, sentinel], [50100]))]
    return s, ToyCache(ranges, payloads=[(50000, 50008), (50100, 50108)])


def mutate_range(cache, address, transform):
    cache.ranges = [(start, transform(raw) if start == address else raw)
                    for start, raw in cache.ranges]


def cases(module):
    complete = 'COMPLETE_SELECTED_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION'
    records = []
    def check(name, source, cache, status, inspect=None):
        result = module.plan_source(source, cache)
        assert result['status'] == status, (name, result['status'], result)
        assert result['HTTP_requests'] == 0 and result['spectral_values_read'] is False
        assert result['payload_pointer_followed'] is False
        if inspect:
            inspect(result)
        records.append({'case': name, 'status': 'PASS', 'planner_status': status,
                        'metadata_read_calls': len(cache.reads)})

    s, c = leaf_scene()
    def exact_rows(r):
        assert [d['coordinates'] for d in r['descriptors']] == [[0, 0, 80, 0], [1, 0, 80, 0]]
        assert [d['file_offset'] for d in r['descriptors']] == [50000, 50100]
        assert r['nodes'][0]['used_extent_bytes'] == 160
    check('dynamic_two_rows_complete_leaf_and_outside_final_sentinel', s, c, complete, exact_rows)

    s, c = internal_scene()
    check('dynamic_descending_internal_tree_three_nodes', s, c, complete,
          lambda r: (_ for _ in ()).throw(AssertionError()) if r['metadata_nodes_read'] != 3 else None)

    s, c = leaf_scene(base=512)
    check('actual_base_relative_addresses', s, c, complete,
          lambda r: (_ for _ in ()).throw(AssertionError()) if r['descriptors'][0]['file_offset'] != 50512 else None)

    s, c = leaf_scene(ntime=3, nfreq=17)
    check('actual_three_rows_partial_last_native_midpoint', s, c, complete,
          lambda r: (_ for _ in ()).throw(AssertionError()) if r['selected_native']['channel_count'] != 1 else None)

    s, c = leaf_scene(mask=1)
    check('filter_mask_preserved_without_codec', s, c, complete,
          lambda r: (_ for _ in ()).throw(AssertionError()) if r['descriptors'][0]['filter_mask'] != 1 else None)

    s, c = leaf_scene()
    c.ranges = [(a, b) for a, b in c.ranges if a != 1024]
    def missing_header(r):
        assert [(x['offset'], x['length']) for x in r['missing_metadata_fragments']] == [(1024, 24)]
    check('missing_root_exact_typed_24byte_header', s, c,
          'INCOMPLETE_TYPED_CHUNK_INDEX_METADATA', missing_header)

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:24])
    def missing_body(r):
        assert [(x['offset'], x['length']) for x in r['missing_metadata_fragments']] == [(1048, 136)]
        assert r['missing_metadata_fragments'][0]['typed_parent_evidence']['node_entries_used'] == 2
    check('cache_subtracted_dynamic_used_extent', s, c,
          'INCOMPLETE_TYPED_CHUNK_INDEX_METADATA', missing_body)

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: b'BTHD' + raw[4:])
    check('unknown_index_format_never_guessed', s, c, 'UNSUPPORTED_FORMAT')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:6] + enc(0, 2) + raw[8:])
    check('zero_used_entries_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:6] + enc(65, 2) + raw[8:])
    check('unsupported_finite_used_entries_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:72] + key((0, 0, 80, 0)) + raw[112:])
    check('unsorted_duplicate_key_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:32] + enc(0, 8) + enc(0, 8) + enc(81, 8) + enc(0, 8) + raw[64:])
    check('unaligned_origin_invalid', s, c, 'INVALID_METADATA')

    s, c = internal_scene()
    mutate_range(c, 1024, lambda raw: raw[:64] + enc(1024, 8) + raw[72:])
    check('cycle_before_following_child', s, c, 'INVALID_METADATA')

    s, c = internal_scene()
    mutate_range(c, 4096, lambda raw: raw[:5] + b'\x01' + raw[6:])
    check('child_level_must_descend_exactly', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:64] + enc(65534, 8) + raw[72:])
    check('payload_length_outside_file_record_rejected_without_read', s, c, 'INVALID_METADATA')

    s, c = leaf_scene(mask=2)
    check('mask_outside_actual_filter_pipeline_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    s['metadata_derived_midpoint']['absolute_channel_start'] = 64
    check('frozen_midpoint_mismatch_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    s['chunk_layout']['pointer_field_hex'] = '00' * 8
    check('qualified_layout_parent_pointer_mismatch_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:112] + enc(50000, 8) + raw[120:])
    check('duplicate_selected_raw_intervals_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    s['superblock']['offset_width'] = 4
    check('unsupported_offset_width_no_metadata_guess', s, c, 'UNSUPPORTED_FORMAT')

    # Distinct V2 cases: final fence is not a real chunk coordinate.
    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:-40] + key((2, 1, 96, 4), 0, 0))
    check('generated_final_upper_fence_byte_extent4_zero_size_mask', s, c, complete, exact_rows)

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:56] + enc(4, 8) + raw[64:])
    check('nonfinal_real_key_byte_coordinate4_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:-40] + key((2, 1, 96, 8), 0, 0))
    check('unknown_final_fence_byte_coordinate8_invalid', s, c, 'INVALID_METADATA')

    s, c = leaf_scene()
    mutate_range(c, 1024, lambda raw: raw[:-40] + key((2, 1, 96, 4), 8, 0))
    check('nonzero_storage_size_on_generated_byte_extent_fence_invalid', s, c, 'INVALID_METADATA')
    assert len(records) == 24
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--expected-source-sha256', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    source = Path(args.source)
    raw = source.read_bytes()
    assert sha(raw) == args.expected_source_sha256
    spec = importlib.util.spec_from_file_location('pure_toy_tree1_target', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = cases(module)
    assert sha(source.read_bytes()) == args.expected_source_sha256
    result = {'schema': 'SETI_TREE1_SYNTHETIC_SOURCE_FIXTURE_RESULT_V1',
        'status': 'PASS_SYNTHETIC_ONLY_TREE1_METADATA_FIXTURES',
        'parser_sha256': args.expected_source_sha256,
        'fixture_source_sha256': sha(Path(__file__).read_bytes()),
        'cases_passed': len(records), 'cases': records,
        'real_source_cache_opened': False, 'HTTP_requests': 0,
        'spectral_values_read': False, 'native_imports': False}
    with Path(args.receipt).open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'cases_passed': len(records)}))


if __name__ == '__main__':
    main()
