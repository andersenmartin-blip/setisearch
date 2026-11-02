"""Download only prospectively selected public products; never interpret arrays."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value, exclusive=False):
    with path.open('x' if exclusive else 'w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def repository_path(relative):
    path = (REPO / relative).resolve()
    if not path.is_relative_to(REPO):
        raise ValueError('Path outside repository')
    return path


def preflight():
    freeze = read(HERE / 'PREFLIGHT_FREEZE.json')
    for required in [HERE / 'PLAN.json', Path(__file__)]:
        if str(required.relative_to(REPO)) not in freeze['files']:
            raise ValueError('Freeze must bind the plan and executor')
    for name, expected in freeze['files'].items():
        path = repository_path(name)
        if digest(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise ValueError('Frozen input changed: ' + name)
    plan = read(HERE / 'PLAN.json')
    release = read(HERE / 'ROOT_RELEASE.json')
    if release.get('freeze_sha256') != digest(HERE / 'PREFLIGHT_FREEZE.json'):
        raise ValueError('Release freeze mismatch')
    if release.get('remote_bytes_verified') is not True:
        raise ValueError('Exact public readback required')
    if not re.fullmatch('[0-9a-f]{40}', release.get('prospective_commit', '')):
        raise ValueError('Prospective commit required')
    selection_path = repository_path(plan['selection_path'])
    if digest(selection_path) != plan['selection_sha256']:
        raise ValueError('Selection changed')
    selected = read(selection_path)['selected']
    identities = [(row['target'], row['dp_id']) for row in plan['inputs']]
    if identities != [(row['target'], row['dp_id']) for row in selected]:
        raise ValueError('Exact selected-slot accounting required')
    if not 1 <= len(identities) <= 4 or len(set(identities)) != len(identities):
        raise ValueError('Require one to four distinct products')
    destinations = [repository_path(row['local_path']) for row in plan['inputs']]
    if len(set(destinations)) != len(destinations) or any(path.exists() for path in destinations):
        raise ValueError('Require distinct, unused product destinations')
    for target in ['HD122640', 'HD135204']:
        if sum(row[0] == target for row in identities) > 2:
            raise ValueError('At most two products per target')
    for row, original in zip(plan['inputs'], selected):
        if row['target'] not in ['HD122640', 'HD135204']:
            raise ValueError('Unexpected target')
        if row['metadata_access_url'] != original['metadata']['access_url']:
            raise ValueError('DataLink identity differs from frozen metadata')
        expected = 'https://dataportal.eso.org/dataPortal/file/' + row['dp_id']
        if row['source_url'] != expected:
            raise ValueError('URL differs from the frozen direct-file contract')
        parsed = urllib.parse.urlsplit(row['source_url'])
        if parsed.scheme != 'https' or parsed.hostname != 'dataportal.eso.org' or parsed.username or parsed.password:
            raise ValueError('Expected public HTTPS ESO data-portal URL')
        if not repository_path(row['local_path']).is_relative_to(HERE / 'products'):
            raise ValueError('Unexpected product destination')
    version = subprocess.run(['curl', '--disable', '--version'], capture_output=True, text=True, check=True).stdout
    match = re.search(r'curl (\d+)\.(\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (8, 4, 0):
        raise ValueError('Streaming byte cap requires curl >=8.4')
    return plan, release, version


def acquire(row, index):
    product = repository_path(row['local_path'])
    stem = row['dp_id'].replace(':', '_')
    receipt_path = HERE / 'receipts' / (stem + '.json')
    headers_path = HERE / 'receipts' / (stem + '.headers')
    stats_path = HERE / 'receipts' / (stem + '.curl.json')
    stderr_path = HERE / 'receipts' / (stem + '.stderr')
    save(HERE / 'receipts' / (stem + '.STARTED.json'), {'started_utc': now(), 'index': index, 'attempt': 1, 'dp_id': row['dp_id']}, exclusive=True)
    args = ['curl', '--disable', '--silent', '--show-error', '--globoff', '--request', 'GET',
            '--proto', '=https', '--proto-redir', '=https', '--max-redirs', '0', '--retry', '0',
            '--max-time', '60', '--connect-timeout', '15', '--max-filesize', '16777216',
            '--header', 'Accept-Encoding: identity', '--user-agent', 'SETI-HARPS-fixed-followup/1.0',
            '--output', str(product), '--dump-header', str(headers_path), '--write-out', '%{json}', row['source_url']]
    receipt = {'started_utc': now(), 'index': index, 'dp_id': row['dp_id'], 'target': row['target'],
               'source_url': row['source_url'], 'attempt': 1, 'command': args, 'new_arrays_interpreted': 0}
    preexisting = product.exists()
    try:
        if preexisting:
            raise FileExistsError('Preserve existing payload: ' + str(product))
        response = subprocess.run(args, capture_output=True, timeout=65, check=False)
        stats_path.write_bytes(response.stdout)
        stderr_path.write_bytes(response.stderr)
        stats = json.loads(response.stdout) if response.stdout else {}
        receipt.update(curl_returncode=response.returncode, transport=stats)
        if response.returncode or stats.get('http_code') != 200 or stats.get('num_redirects') != 0 or stats.get('url_effective') != row['source_url']:
            raise ValueError('Transport/status/redirect contract failed')
        if not product.is_file() or not 0 < product.stat().st_size < 16777216:
            raise ValueError('Empty or byte-capped payload')
        with product.open('rb') as stream:
            if stream.read(9) != b'SIMPLE  =':
                raise ValueError('Not an uncompressed FITS primary header')
        receipt['status'] = 'COMPLETE'
    except Exception as error:
        receipt.update(status='FAILED', reason=type(error).__name__ + ': ' + str(error))
    receipt['finished_utc'] = now()
    receipt['preexisting_payload_preserved'] = preexisting
    if product.is_file() and not preexisting:
        receipt.update(bytes=product.stat().st_size, sha256=digest(product))
    save(receipt_path, receipt, exclusive=True)
    return {'target': row['target'], 'dp_id': row['dp_id'], 'status': receipt['status'],
            'reason': receipt.get('reason'), 'local_path': row['local_path'], 'bytes': receipt.get('bytes', 0),
            'sha256': receipt.get('sha256'), 'source_url': row['source_url'],
            'acquisition_receipt_path': str(receipt_path.relative_to(REPO)),
            'acquisition_receipt_sha256': digest(receipt_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit('No network by default; --execute and a verified prospective release are required.')
    plan, release, version = preflight()
    save(HERE / 'RUN_STARTED.json', {'started_utc': now(), 'release': release, 'curl_version': version}, exclusive=True)
    (HERE / 'products').mkdir(exist_ok=False)
    (HERE / 'receipts').mkdir(exist_ok=False)
    inputs, stopped = [], False
    for index, row in enumerate(plan['inputs'], 1):
        if stopped:
            result = {'target': row['target'], 'dp_id': row['dp_id'], 'status': 'NOT_ATTEMPTED', 'reason': 'Stopped after earlier failed acquisition', 'local_path': row['local_path'], 'bytes': 0, 'sha256': None}
        else:
            result = acquire(row, index)
            stopped = result['status'] != 'COMPLETE'
        inputs.append(result)
        save(HERE / 'ACQUISITION_MANIFEST.json', {'schema': 'HARPS_BERV_SCIENCE_ACQUISITION_V1', 'updated_utc': now(),
             'status': 'STOPPED_AFTER_FAILURE' if stopped else ('COMPLETE' if len(inputs) == len(plan['inputs']) else 'IN_PROGRESS'),
             'plan_sha256': digest(HERE / 'PLAN.json'), 'inputs': inputs, 'bytes_saved': sum(item['bytes'] for item in inputs),
             'new_arrays_interpreted': 0, 'original_survey_exposures': 300, 'original_labels_changed': 0}, exclusive=False)
    print(json.dumps({'slots': len(inputs), 'complete': sum(row['status'] == 'COMPLETE' for row in inputs), 'bytes': sum(row['bytes'] for row in inputs)}))


if __name__ == '__main__':
    main()
