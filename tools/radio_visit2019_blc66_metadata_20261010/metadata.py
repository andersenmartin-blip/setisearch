"""Bounded HDF5 header extraction and six-scan metadata qualification.

Inert on import. The caller supplies an already authenticated metadata cache,
the frozen completed typed plan, and h5py after installing resource limits.
No HTTP, dataset values, chunk-index traversal, or codec entry point exists.
"""
import hashlib
import io
import math

MAX_ATTRIBUTES = 64
MAX_ATTRIBUTE_ELEMENTS = 64
MAX_ATTRIBUTE_BYTES = 65536
MAX_READER_CALLS = 4096
ON_POINTING_TOLERANCE_DEGREES = 1 / 60
DISTINCT_POINTING_MIN_DEGREES = 1 / 60


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def plain(value):
    if isinstance(value, bytes):
        return value.decode('utf-8')
    if hasattr(value, 'tolist'):
        return plain(value.tolist())
    if isinstance(value, (list, tuple)):
        return [plain(x) for x in value]
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite metadata value')
    require(value is None or type(value) in (str, int, float, bool, list),
            'Unsupported metadata serialization type')
    return value


def number(attributes, key):
    value = attributes[key]
    require(type(value) in (int, float) and math.isfinite(value),
            'Finite scalar metadata number required: ' + key)
    return float(value)


def integer(attributes, key):
    value = number(attributes, key)
    require(value == int(value), 'Integral scalar metadata required: ' + key)
    return int(value)


def packed_coordinate(value, declination=False):
    """SIGPROC HHMMSS/±DDMMSS scalar to degrees; reject malformed fields."""
    require(type(value) in (int, float) and math.isfinite(value),
            'Finite packed scalar coordinate required')
    require(declination or value >= 0, 'Negative right ascension')
    sign = math.copysign(1, value) if declination else 1
    absolute = abs(value)
    major = int(absolute // 10000)
    remainder = absolute - major * 10000
    minute = int(remainder // 100)
    second = remainder - minute * 100
    require(0 <= minute < 60 and 0 <= second < 60,
            'Malformed SIGPROC coordinate minute/second')
    maximum = 90 if declination else 23
    require(major <= maximum and (not declination or major < 90 or minute == second == 0),
            'SIGPROC coordinate exceeds sky bounds')
    result = sign * (major + minute / 60 + second / 3600)
    return result if declination else result * 15


def separation(first, second):
    ra1, dec1, ra2, dec2 = map(math.radians, [*first, *second])
    a = (math.sin((dec2 - dec1) / 2) ** 2
         + math.cos(dec1) * math.cos(dec2) * math.sin((ra2 - ra1) / 2) ** 2)
    return math.degrees(2 * math.asin(math.sqrt(min(1, max(0, a)))))


class CacheOnly(io.RawIOBase):
    """Logical file reader with finite exact cache spans and no fetch callback."""
    def __init__(self, cache, size):
        self.cache, self.size, self.position = cache, size, 0
        self.reads, self.misses = [], []

    def seek(self, offset, whence=0):
        require(type(offset) is int and whence in (0, 1, 2), 'Invalid metadata seek')
        position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        require(0 <= position <= self.size, 'Metadata seek outside logical file')
        self.position = position
        return position

    def tell(self):
        return self.position

    def readinto(self, buffer):
        n = len(buffer)
        require(len(self.reads) + len(self.misses) < MAX_READER_CALLS,
                'Metadata-reader call bound exceeded')
        if n == 0:
            return 0
        record = {'offset': self.position, 'bytes': n}
        try:
            body = self.cache.read(self.position, n)
        except Exception as error:
            record.update(origin='h5py_metadata_read_request',
                          typed_pointer_metadata_evidence_verified=False,
                          HTTP_authorized=False, error_type=type(error).__name__)
            self.misses.append(record)
            raise ValueError('Missing bounded cached metadata; no acquisition callback') from error
        require(len(body) == n, 'Short authenticated cache read')
        self.reads.append(record)
        buffer[:] = body
        self.position += n
        return n


def attributes(manager):
    names = list(manager.keys())
    require(len(names) <= MAX_ATTRIBUTES and all(isinstance(k, str) and len(k) <= 128 for k in names),
            'Metadata attribute-name bound exceeded')
    result = {}
    for key in names:
        identifier = manager.get_id(key)
        try:
            shape = identifier.shape
            require(isinstance(shape, tuple) and len(shape) <= 3,
                    'Unsupported attribute rank')
            count = math.prod(shape)
            require(0 < count <= MAX_ATTRIBUTE_ELEMENTS
                    and 0 < identifier.dtype.itemsize <= 128
                    and count * identifier.dtype.itemsize <= MAX_ATTRIBUTE_BYTES,
                    'Metadata attribute shape/size bound exceeded')
        finally:
            identifier.close()
        value = plain(manager[key])
        require(not isinstance(value, str) or len(value.encode('utf-8')) <= MAX_ATTRIBUTE_BYTES,
                'Metadata string attribute exceeds bound')
        result[key] = value
    return result


def chunk_layout_pointer(plan, cache, chunks, itemsize, file_size):
    """Decode only the verified data-object layout message, without TREE reads."""
    messages = [m for m in plan['messages'] if m['object'] == 'data' and m['type'] == 8]
    require(len(messages) == 1, 'Exactly one verified data chunk-layout message required')
    message = messages[0]
    offset, length = message['offset'], message['data_bytes_including_padding']
    envelope = cache.read(offset, 8)
    require(int.from_bytes(envelope[:2], 'little') == 8
            and int.from_bytes(envelope[2:4], 'little') == length,
            'Typed data-layout envelope differs')
    body = cache.read(offset + 8, length)
    require(sha(body) == message['data_sha256'] and body[:2] == b'\x03\x02',
            'Only the verified version-3 chunked layout is supported')
    rank = body[2]
    require(rank == len(chunks) + 1 and length >= 11 + 4 * rank,
            'Chunk-layout rank/extent differs')
    encoded_dimensions = [int.from_bytes(body[11 + i * 4:15 + i * 4], 'little') for i in range(rank)]
    require(encoded_dimensions == chunks + [itemsize], 'Chunk-layout dimensions differ from h5py metadata')
    pointer = int.from_bytes(body[3:11], 'little')
    base = plan['superblock']['base_address']
    require(pointer != (1 << 64) - 1 and 0 <= base + pointer < file_size,
            'Undefined or out-of-file chunk-index root pointer')
    return {'layout_version': 3, 'layout_class': 2,
            'dimensionality_including_element_size': rank,
            'encoded_dimensions': encoded_dimensions,
            'chunk_index_root_relative_address': pointer,
            'chunk_index_root_absolute_address': base + pointer,
            'pointer_field_offset': offset + 11,
            'pointer_field_hex': body[3:11].hex(),
            'layout_message_offset': offset,
            'layout_message_body_sha256': sha(body),
            'metadata_evidence': cache.evidence(offset, 8 + length, 'verified data-object version-3 chunk-layout message'),
            'chunk_index_nodes_read': 0, 'payload_pointer_followed': False,
            'HTTP_authorized': False}


def extract(identity, cache, plan, file_size, h5py):
    require(plan['source_id'] == identity['source_id']
            and plan['status'] == 'COMPLETE_SUPPORTED_HEADER_STRUCTURE'
            and not plan['missing_metadata_fragments']
            and plan['HTTP_requests'] == plan['payload_ranges_proposed'] == 0
            and plan['spectral_values_read'] is False,
            'Exact complete metadata-only typed plan required')
    virtual = CacheOnly(cache, file_size)
    record = {'source_id': identity['source_id'], 'url': identity['url'],
              'ordered_index': identity['ordered_index'],
              'candidate_role': identity['candidate_role'],
              'source_file_bytes': file_size, 'status': 'NOT_PARSED',
              'HTTP_requests': 0, 'spectral_values_read': False,
              'dataset_value_API_used': False, 'chunk_index_nodes_read': 0,
              'codec_invoked': False, 'source_values_admission': 'BLOCKED',
              'independent_validation_admission': 'BLOCKED'}
    try:
        with h5py.File(virtual, 'r') as handle:
            require(isinstance(handle.get('data', getlink=True), h5py.HardLink),
                    'Named data object must be an internal hard link')
            dataset = handle['data']
            require(isinstance(dataset, h5py.Dataset), 'Named data object must be a dataset')
            shape = list(dataset.shape)
            chunks = list(dataset.chunks) if dataset.chunks else None
            dtype = dataset.dtype
            require(dtype.kind == 'f' and dtype.itemsize == 4 and dtype.str == '<f4',
                    'Only native/little-endian float32 metadata datatype supported')
            require(len(shape) == 3 and all(type(x) is int and x > 0 for x in shape)
                    and shape[1] == 1 and chunks is not None and len(chunks) == 3
                    and chunks[0] == chunks[1] == 1 and 0 < chunks[2] <= shape[2],
                    'Only positive [ntime,1,nchannels] with [1,1,native_channels] chunks supported')
            creation = dataset.id.get_create_plist()
            try:
                require(creation.get_nfilters() <= 8, 'Metadata filter count exceeds bound')
                filters = [plain(creation.get_filter(i)) for i in range(creation.get_nfilters())]
            finally:
                creation.close()
            record.update(shape=shape, dtype=str(dtype), dtype_string=dtype.str,
                          dtype_itemsize_bytes=dtype.itemsize, chunks=chunks,
                          creation_filters=filters,
                          root_attributes=attributes(handle.attrs),
                          data_attributes=attributes(dataset.attrs))
        a = record['data_attributes']
        require(record['root_attributes'].get('CLASS') == 'FILTERBANK', 'Expected FILTERBANK product')
        require(a.get('source_name') == identity['expected_source_name'],
                'Actual source_name differs from frozen identity')
        require(integer(a, 'nchans') == shape[2] and integer(a, 'nifs') == 1
                and integer(a, 'nbits') == 32, 'Declared header/dataset geometry differs')
        for key in ('fch1', 'foff', 'tstart', 'tsamp', 'src_raj', 'src_dej'):
            number(a, key)
        require(a['tsamp'] > 0 and a['foff'] != 0, 'Nonpositive tsamp or zero foff')
        first, last = a['fch1'], a['fch1'] + (shape[2] - 1) * a['foff']
        require(min(first, last) > 0 and math.isfinite(last), 'Invalid positive channel-center range')
        filename_start = identity['filename_MJD_integer'] + identity['filename_second_of_day'] / 86400
        delta = (a['tstart'] - filename_start) * 86400
        require(abs(delta) <= 2, 'Actual header/file timestamp identity differs')
        ra = packed_coordinate(a['src_raj'])
        dec = packed_coordinate(a['src_dej'], declination=True)
        native_count = (shape[2] + chunks[2] - 1) // chunks[2]
        native_ordinal = native_count // 2
        native_start = native_ordinal * chunks[2]
        record.update(header_minus_filename_start_seconds=delta,
                      channel_center_interval_MHz=[min(first, last), max(first, last)],
                      pointing_degrees={'RA': ra, 'DEC': dec},
                      scan_time_interval_MJD_half_open=[a['tstart'], a['tstart'] + shape[0] * a['tsamp'] / 86400],
                      native_chunks_along_frequency=native_count,
                      fixed_midpoint_rule='floor(n_native_frequency_chunks/2); zero-based; fixed before amplitudes',
                      metadata_derived_midpoint={'native_ordinal_zero_based': native_ordinal,
                         'absolute_channel_start': native_start,
                         'channel_count': min(chunks[2], shape[2] - native_start)},
                      chunk_layout=chunk_layout_pointer(plan, cache, chunks, dtype.itemsize, file_size),
                      status='COMPLETE_HEADER_METADATA_ONLY')
    except (MemoryError, TimeoutError, KeyboardInterrupt, SystemExit):
        raise
    except Exception as error:
        record.update(status='HEADER_EXTRACTION_INCOMPLETE_OR_UNSUPPORTED',
                      error_type=type(error).__name__, error=str(error))
    finally:
        record['metadata_reader_ranges'] = virtual.reads
        record['missing_metadata_read_ranges'] = virtual.misses
    return record


def qualify(records):
    """Fixed descriptive header gates, with no amplitude or statistical test."""
    result = {'status': 'METADATA_NOT_ELIGIBLE', 'checks': [],
              'source_values_admission': 'BLOCKED', 'independent_validation_admission': 'BLOCKED',
              'HTTP_requests': 0, 'spectral_values_read': False,
              'pointing_tolerance_degrees': ON_POINTING_TOLERANCE_DEGREES,
              'distinct_pointing_minimum_degrees': DISTINCT_POINTING_MIN_DEGREES,
              'beam_separation_model_used': False,
              'controls_certified_blank_sky_or_independent_noise': False}
    def check(name, ok, **evidence):
        result['checks'].append({'name': name, 'PASS': bool(ok), **evidence})
        return bool(ok)
    if not check('six_complete_actual_headers', len(records) == 6
                 and all(r['status'] == 'COMPLETE_HEADER_METADATA_ONLY' for r in records)):
        return result
    grids = [{k: r[k] for k in ('shape', 'dtype_string', 'chunks', 'creation_filters')}
             | {k: r['data_attributes'][k] for k in ('nchans', 'nifs', 'nbits', 'fch1', 'foff', 'tsamp')}
             for r in records]
    check('exact_six_common_geometry_frequency_time_grid_and_filters', all(g == grids[0] for g in grids),
          common_grid=grids[0], differing_source_ids=[r['source_id'] for r, g in zip(records, grids) if g != grids[0]])
    expected_roles = ['ON_CANDIDATE', 'CONTROL_CANDIDATE'] * 3
    check('actual_six_alternating_roles', [r['candidate_role'] for r in records] == expected_roles
          and [r['ordered_index'] for r in records] == list(range(1, 7)))
    ons, offs = records[::2], records[1::2]
    on_names = [r['data_attributes']['source_name'] for r in ons]
    off_names = [r['data_attributes']['source_name'] for r in offs]
    check('actual_three_target_names', on_names == ['HIP98505'] * 3, names=on_names)
    check('actual_three_distinct_control_names', len(set(off_names)) == 3 and 'HIP98505' not in off_names,
          names=off_names)
    coords = [(r['pointing_degrees']['RA'], r['pointing_degrees']['DEC']) for r in records]
    angles = [{'first_source_id': records[i]['source_id'], 'second_source_id': records[j]['source_id'],
               'separation_degrees': separation(coords[i], coords[j])}
              for i in range(6) for j in range(i + 1, 6)]
    on_angles = [x for x in angles if any(x['first_source_id'] == r['source_id'] for r in ons)
                 and any(x['second_source_id'] == r['source_id'] for r in ons)]
    distinct_angles = [x for x in angles if x not in on_angles]
    check('three_actual_ON_pointings_agree', all(x['separation_degrees'] <= ON_POINTING_TOLERANCE_DEGREES for x in on_angles),
          pair_separations=on_angles)
    check('actual_controls_distinct_from_ON_and_each_other',
          all(x['separation_degrees'] >= DISTINCT_POINTING_MIN_DEGREES for x in distinct_angles),
          pair_separations=distinct_angles)
    intervals = [r['scan_time_interval_MJD_half_open'] for r in records]
    gaps = [(intervals[i + 1][0] - intervals[i][1]) * 86400 for i in range(5)]
    starts = [r['data_attributes']['tstart'] for r in records]
    deltas = [(starts[i + 1] - starts[i]) * 86400 for i in range(5)]
    check('ordered_nonoverlapping_six_scan_cadence', all(g >= 0 for g in gaps)
          and all(0 < d <= 600 for d in deltas), adjacent_start_deltas_seconds=deltas,
          adjacent_end_to_start_gaps_seconds=gaps)
    check('actual_target_persists_across_visit', starts[4] > starts[0]
          and (starts[4] - starts[0]) * 86400 <= 1800,
          first_to_third_ON_seconds=(starts[4] - starts[0]) * 86400)
    mids = [r['metadata_derived_midpoint'] for r in records]
    check('fixed_metadata_derived_midpoint_common_to_six', all(m == mids[0] for m in mids), midpoint=mids[0])
    if all(c['PASS'] for c in result['checks']):
        result['status'] = 'PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
        result['common_grid'] = grids[0]
        result['fixed_metadata_derived_midpoint'] = mids[0]
        result['qualified_roles'] = ['ON_TARGET', 'CONTROL_DISTINCT_POINTING'] * 3
    return result
