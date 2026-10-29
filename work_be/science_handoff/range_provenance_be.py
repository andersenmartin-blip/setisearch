"""Verify BB87, BC1 and BE8 derived chunks and genuine HTTP range evidence.

This module reads retained files only and has no transport or codec dependency.
"""
import hashlib
from common_be import read, sha, require

REFERENCES = {'receipt_relative_path', 'payload_relative_path', 'stored_receipt_sha256',
              'receipt_schema', 'lineage'}
SCHEMAS = {'SETI_BB_DERIVED_COMPRESSED_CHUNK_V1': 'BB',
           'SETI_BC_DERIVED_COMPRESSED_CHUNK_V1': 'BC',
           'SETI_BE_DERIVED_COMPRESSED_CHUNK_V1': 'BE'}


def coordinate_stage(scan, row):
    require(type(scan) is int and type(row) is int and 0 <= scan < 6 and 0 <= row < 16,
            'Invalid selected coordinate')
    if scan < 5 or row < 7:
        return 'BB'
    return 'BC' if row == 7 else 'BE'


def paths(ctx):
    return {'BB': ctx.evidence / 'work_bb/acquire/hip44295_65133',
            'BC': ctx.evidence / 'work_bc/acquire', 'BE': ctx.evidence / 'work_be/acquire'}


def verify(ctx, record, kind, scans, heads, pins):
    j = record['scan']
    require(type(j) is int and 0 <= j < 6, 'Invalid range scan')
    archive = scans[j]['archive']
    lo, hi = record['start'], record['stop_inclusive']
    require(type(lo) is int and type(hi) is int and 0 <= lo <= hi < archive['size'],
            'Range outside archive')
    require(record['bytes'] == hi - lo + 1 <= 8388608, 'Range size differs or exceeds cap')
    require(record['archive_id'] == archive['id'] and record['url'] == archive['url'],
            'Range archive identity differs')
    require(record['etag'] == heads[j]['etag'] and bool(record['etag']), 'Range ETag differs')
    bp = ctx.pin(record['payload_relative_path'], pins, record['sha256'])
    rp = ctx.pin(record['receipt_relative_path'], pins, record['stored_receipt_sha256'])
    require(bp.stat().st_size == record['bytes'], 'Payload length differs')
    stored = read(rp)
    roots = paths(ctx)
    schema = record.get('receipt_schema')
    if schema in SCHEMAS:
        stage = SCHEMAS[schema]
        require(kind == 'payload' and stored.get('receipt_schema') == schema,
                'Derived schema/kind differs')
        require(coordinate_stage(j, record['time_index']) == stage, 'Derived coordinate lineage differs')
        require(stored['status'] == record['status'] == 'DERIVED_FROM_VERIFIED_RANGES',
                'Derived status differs')
        require(stored['new_HTTP_whole_chunk_receipt_claimed'] is False,
                'Derived union is not a whole-chunk HTTP response')
        require(bp.parent == roots[stage] / 'derived' and rp.parent == bp.parent
                and rp.with_suffix('.bin') == bp and bp.name == f'scan{j}_row{record["time_index"]}.bin',
                'Derived storage identity differs')
        assembled, offset = bytearray(), 0
        for segment in record['coverage_segments']:
            length = segment['length']
            require(type(length) is int and length > 0 and segment['output_offset'] == offset,
                    'Noncontiguous derived union')
            a, b = segment['source_start'], segment['source_stop']
            require(a == lo + offset and b - a + 1 == length, 'Derived source coordinates differ')
            source = segment['source_receipt']
            require(source.get('receipt_schema') not in SCHEMAS and source['scan'] == j,
                    'Derived source cannot recursively claim another derived chunk')
            require(source['start'] <= a <= b <= source['stop_inclusive'], 'Source span does not contain slice')
            sourcepath = verify(ctx, source, 'retained_http_range', scans, heads, pins)
            part = sourcepath.read_bytes()[a-source['start']:b-source['start']+1]
            require(len(part) == length, 'Short source slice')
            assembled.extend(part)
            offset += length
        require(offset == record['bytes'] and bytes(assembled) == bp.read_bytes()
                and hashlib.sha256(assembled).hexdigest() == record['sha256'], 'Derived union bytes differ')
    else:
        require(record['status'] == 206 and record['attempts'] == 1 and record['failed_attempts'] == [],
                'Genuine single-attempt HTTP206 evidence required')
        require(record['content_range'] == f'bytes {lo}-{hi}/{archive["size"]}', 'Content-Range differs')
        suffix = '.repeat' if kind == 'repeat' or record.get('kind') == 'repeat' else ''
        stem = f'scan{j}_{lo}_{hi}{suffix}'
        allowed = [roots['BB'] / 'transport', roots['BB'] / 'raw_transport',
                   roots['BC'] / 'transport', roots['BE'] / 'transport']
        require(bp.parent in allowed and rp.parent == bp.parent and bp.name == stem+'.bin'
                and rp.name == stem+'.json', 'HTTP receipt storage identity differs')
        require(bp.parent not in [roots['BC'] / 'transport', roots['BE'] / 'transport'] or j == 5,
                'BC/BE transports may concern scan5 only')
    for key in set(stored) | set(record):
        if key not in REFERENCES:
            require(key in stored and key in record and stored[key] == record[key],
                    'Stored receipt and manifest differ: ' + key)
    return bp
