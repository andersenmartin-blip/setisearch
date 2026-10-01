#!/usr/bin/env python3
"""Independently reconstruct public Actions body evidence with bounded decoding.

Read-only audit; performs no HTTP request, native execution or case reservation.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re

NAMESPACE = 'radio-native-v2-actions-control-20261001a'
MAX_FILE = 40 * 1024**2
MAX_TOTAL = 192 * 1024**2
FLAGS = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
         'scientific_execution_authorized', 'restart_authorized',
         'transport_integration_qualified')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode(item):
    if (type(item.get('bytes')) is not int or not 0 <= item['bytes'] <= MAX_FILE
            or not re.fullmatch('[0-9a-f]{64}', item.get('sha256', ''))
            or item.get('encoding') != 'gzip_base64'):
        raise ValueError('Bounded exact public evidence pin required')
    packed = base64.b64decode(item['content'], validate=True)
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as source:
        data = source.read(item['bytes'] + 1)
        if len(data) != item['bytes'] or source.read(1) or sha(data) != item['sha256']:
            raise ValueError('Lossless evidence byte/hash bound differs')
    return data


def audit(path):
    raw = Path(path).read_bytes()
    if len(raw) > 8 * 1024**2:
        raise ValueError('Bounded compact public evidence only')
    envelope = json.loads(raw)
    if any(envelope.get(key) is not False for key in FLAGS):
        raise ValueError('Publication engineering cannot grant scientific authority')
    verified = {}
    total = 0
    # Only compact selected metadata is retained across reads.
    selected = {}
    wanted = {'publisher/caller-summary.json', 'publisher/compact-control-evidence.json',
              'supervisor-report.json', 'supervisor-terminal.json',
              'runtime-inventory-before-control.json', 'activation-proof.json'}
    for name, item in envelope['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('Canonical evidence path required')
        data = decode(item)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError('Original case evidence allocation exceeded')
        verified[name] = {'bytes': len(data), 'sha256': sha(data)}
        if name in wanted:
            selected[name] = json.loads(data)
        del data
    summary = selected['publisher/caller-summary.json']
    compact = selected['publisher/compact-control-evidence.json']
    observer = selected['supervisor-report.json']
    terminal = selected['supervisor-terminal.json']
    if (summary['status'] != 'PUBLISHED_SOURCE_CONTROL_COMPONENT_ONLY'
            or terminal['status'] != 'PASS_COMPONENT_CONTROL'
            or observer['status'] != 'PASS_COMPONENT_RESOURCE_OBSERVATION'
            or observer['failures'] or observer['coverage_errors']
            or not observer['direct_child_termination_coverage_complete']
            or observer['direct_child_exit_code'] != 0):
        raise ValueError('Exact successful publisher and lifetime observation required')
    bodies = {item['path']: item for item in compact['bodies']}
    if len(bodies) != len(compact['bodies']):
        raise ValueError('Duplicate body custody')
    records = compact['records']
    requests = replies = 0
    mutations = []
    for ordinal, record in enumerate(records):
        if (record['ordinal'] != ordinal or record['response_unknown']
                or record['request_body_transmission_verified'] is not True
                or record['automatic_retry'] is not False):
            raise ValueError('Complete exact non-retried body record required')
        requests += record['request_body_bytes']
        replies += record['response_body_bytes']
        request = b''
        for kind in ('request', 'response'):
            name = record.get(kind + '_body_file')
            data = decode(bodies[name]) if name else b''
            if (len(data) != record[kind + '_body_bytes']
                    or sha(data) != record[kind + '_body_sha256']):
                raise ValueError('Reconstructed body differs from exact operation pin')
            if kind == 'request':
                request = data
            elif record['path'] == '/graphql':
                response = json.loads(data)
        if (record['sent_request_body_bytes'] != len(request)
                or record['sent_request_body_sha256'] != sha(request)):
            raise ValueError('Actual sent body differs from retained application request')
        if record['path'] == '/graphql':
            payload = json.loads(request)
            ref = payload['variables']['input']['refUpdates']
            if (record['method'] != 'POST' or len(ref) != 1
                    or ref[0] != {'name': 'refs/heads/m43-support-qualification',
                                  'beforeOid': summary['activation_commit'],
                                  'afterOid': summary['publication_commit'], 'force': False}
                    or 'errors' in response
                    or response['data']['updateRefs']['clientMutationId'] != NAMESPACE):
                raise ValueError('Atomic fixed expected-parent publication acknowledgement differs')
            mutations.append(ordinal)
        del request, data
    usage = summary['usage']
    if (len(records) != usage['operation_count'] or requests != usage['request_bytes']
            or replies != usage['response_bytes'] or usage['unknown_response_count'] != 0
            or mutations != [len(records) - 2]
            or json.loads(decode(bodies[records[-1]['response_body_file']]))['object']['sha'] != summary['publication_commit']):
        raise ValueError('Exact complete ledger/final head accounting differs')
    source = compact['source_recipe']
    generated = source['pattern'].encode() * source['repetitions']
    if len(generated) != source['bytes'] or sha(generated) != source['sha256']:
        raise ValueError('Fresh engineering source recipe differs')
    source_posts = [r for r in records if r.get('request_body_file') == 'source-blob-request.json']
    if len(source_posts) != 1:
        raise ValueError('Exactly one maximum-source submission required')
    posted = json.loads(decode(bodies[source_posts[0]['request_body_file']]))
    if base64.b64decode(posted['content'], validate=True) != generated:
        raise ValueError('Real maximum-source POST differs from frozen recipe')
    got = [r for r in records if r['method'] == 'GET' and r['path'].endswith('/git/blobs/' + source['git_blob_sha1'])]
    if len(got) != 1:
        raise ValueError('Exactly one immutable source readback required')
    value = json.loads(decode(bodies[got[0]['response_body_file']]))
    if base64.b64decode(value['content'].replace('\n', '').replace('\r', ''), validate=True) != generated:
        raise ValueError('Real maximum-source GET differs from posted exact bytes')
    caps = summary['caps']
    if (requests > caps['request_bytes'] or replies > caps['reply_bytes']
            or len(records) > caps['prospective_http_operations']
            or observer['direct_child_peak_rss_bytes'] > caps['rss_per_process_bytes']
            or observer['elapsed_seconds'] > caps['seconds']
            or terminal['storage_allocated_bytes_before_terminal'] + terminal['terminal_storage_reservation_bytes'] > caps['host_receipt_bytes']):
        raise ValueError('Original shared resource allocation exceeded')
    runtime = selected['runtime-inventory-before-control.json']
    return {'schema': 'radio-native-v2-actions-independent-public-evidence-audit-v1',
            'status': 'PASSED_COMPONENT_ONLY', 'evidence_sha256': sha(raw),
            'verified_outer_files': verified, 'verified_body_count': len(bodies),
            'operations': len(records), 'request_bytes': requests, 'response_bytes': replies,
            'source_bytes': source['bytes'], 'source_sha256': source['sha256'],
            'source_publication_commit': summary['publication_commit'],
            'source_publication_tree': summary['publication_tree'],
            'activation_commit': summary['activation_commit'],
            'publisher_peak_rss_bytes': observer['direct_child_peak_rss_bytes'],
            'publisher_lifetime_seconds': observer['elapsed_seconds'],
            'runtime_inventory_files': len(runtime['runtime_files']),
            'runtime_inventory_sha256': verified['runtime-inventory-before-control.json']['sha256'],
            'full_job_resource_qualification': False, 'native_eight_case_qualification': False,
            'original_full_archive_transport_qualification': False,
            'scientific_execution_count': 0, 'telescope_reads': 0,
            **{key: False for key in FLAGS}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit(args.evidence)
    with Path(args.output).open('x') as target:
        target.write(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('status', 'operations', 'request_bytes',
          'response_bytes', 'publisher_peak_rss_bytes', 'publisher_lifetime_seconds',
          'runtime_inventory_files')}, sort_keys=True))


if __name__ == '__main__':
    main()
