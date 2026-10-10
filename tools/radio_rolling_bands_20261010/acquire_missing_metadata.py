"""Prospective exact six-node HDF5 index acquisition; no spectrum or decoder.

Inert until CLI invocation after public scope freeze/readback. Each missing
3136-byte TREE leaf receives one HTTP GET. HTTP redirects and retries are
disabled. The original pure parser is extracted from pinned historical code;
no original Source(), HTTP fallback, array or codec function is instantiated.
"""
import argparse
import ast
import hashlib
import http.client
import json
import os
from pathlib import Path
import resource
import signal
import struct
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as stream:
        json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def require(ok, message):
    if not ok:
        raise ValueError(message)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scope', required=True)
    parser.add_argument('--expected-scope-sha256', required=True)
    args = parser.parse_args()
    started = time.monotonic()
    scope_path = Path(args.scope).resolve()
    require(sha(scope_path.read_bytes()) == args.expected_scope_sha256, 'Exact metadata scope SHA required')
    scope = json.loads(scope_path.read_text())
    require(scope['schema'] == 'SETI_ROLLING_SIX_MISSING_METADATA_NODES_ONCE_V1', 'Unexpected scope schema')
    for path, expected in scope['pinned_files'].items():
        require(sha((ROOT / path).read_bytes()) == expected, 'Frozen file changed: ' + path)
    require(scope['max_HTTP_GETs'] == 6 and scope['expected_metadata_BODY_bytes'] == 18816
            and scope['metadata_BODY_cap_bytes'] == 18816 and scope['attempts_per_node'] == 1,
            'Exact six-node admission required')
    require(scope['CPU_limit_s'] == 15 and scope['wall_limit_s'] == 300
            and scope['memory_limit_bytes'] == 536870912, 'Unexpected resource limits')
    require(scope['spectral_payload_GETs_authorized'] is False and scope['protected_native_chunks'] == [156, 159],
            'No spectral or old-holdout opening allowed')
    requests = scope['requests']
    require(len(requests) == 6 and len({r['label'] for r in requests}) == 6, 'One metadata node per scan required')
    for r in requests:
        require(r['nbytes'] == 3136 and 0 <= r['address'] <= r['source_file_bytes'] - 3136
                and r['target_time_row'] == 12 and r['native_chunks_requiring_this_node'] == [157, 158],
                'Unexpected metadata node geometry')
        require(r['range'] == f"bytes={r['address']}-{r['address']+3135}", 'Exact metadata range required')
    original = (ROOT / scope['original_parser_path']).read_text()
    pure = next(x for x in ast.parse(original).body if isinstance(x, ast.FunctionDef) and x.name == 'parse_node')
    env = {'struct': struct}
    exec(compile(ast.get_source_segment(original, pure), '<pinned-original-pure-parse_node>', 'exec'), env)
    parse_node = env['parse_node']
    out = ROOT / scope['output_directory']
    out.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 'SETI_ROLLING_METADATA_NODE_BODY_RECEIPT_V1', 'status': 'IN_PROGRESS',
               'scope_sha256': sha(scope_path.read_bytes()), 'script_sha256': sha(Path(__file__).read_bytes()),
               'requests': [], 'metadata_BODY_bytes_received': 0, 'spectral_payload_BODY_bytes': 0,
               'metadata_BODY_charged_upper_bound_bytes': 0,
               'spectral_values_read': False, 'codec_imports': False, 'retry_performed': False,
               'qualified_pilot': False, 'A_B': 'FAIL_CLOSED_UNCHANGED', 'cost_DKK': 0}

    def deadline(signum, frame):
        raise TimeoutError('Metadata acquisition resource limit reached')

    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(scope['wall_limit_s'])
    resource.setrlimit(resource.RLIMIT_CPU, (14, 15))
    resource.setrlimit(resource.RLIMIT_AS, (scope['memory_limit_bytes'], scope['memory_limit_bytes']))
    save(out / 'RECEIPT.json', receipt)
    opener = urllib.request.build_opener(NoRedirect())
    try:
        for r in requests:
            record = {'label': r['label'], 'offset': r['address'], 'requested_bytes': 3136,
                      'range': r['range'], 'attempt': 1, 'state': 'RESERVED_BEFORE_GET',
                      'body_bytes_observed': 0,
                      'request_headers': {'Range': r['range'], 'If-Match': r['etag'], 'Accept-Encoding': 'identity'}}
            receipt['requests'].append(record)
            receipt['metadata_BODY_charged_upper_bound_bytes'] += 3136
            save(out / 'RECEIPT.json', receipt)
            require(len(receipt['requests']) <= 6 and receipt['metadata_BODY_charged_upper_bound_bytes'] <= 18816,
                    'Request or BODY bound exceeded')
            try:
                request = urllib.request.Request(r['url'], headers=record['request_headers'])
                with opener.open(request, timeout=scope['HTTP_timeout_s']) as response:
                    record.update(status=response.status, final_url=response.geturl(), response_headers=dict(response.headers))
                    require(response.status == 206 and response.geturl() == r['url'], 'Exact URL and HTTP206 required before BODY')
                    require(response.headers.get('ETag') == r['etag'], 'Frozen ETag changed')
                    require(response.headers.get('Content-Range') == f"bytes {r['address']}-{r['address']+3135}/{r['source_file_bytes']}",
                            'Exact metadata Content-Range required')
                    require(response.headers.get('Content-Length') == '3136'
                            and response.headers.get('Content-Encoding', 'identity').lower() == 'identity',
                            'Exact unencoded metadata Content-Length required')
                    # Read only the pinned metadata bytes; no spectrum or +1 probe.
                    chunks = []
                    while record['body_bytes_observed'] < 3136:
                        try:
                            piece = response.read(3136 - record['body_bytes_observed'])
                        except http.client.IncompleteRead as error:
                            record['body_bytes_observed'] += len(error.partial)
                            receipt['metadata_BODY_bytes_received'] += len(error.partial)
                            raise
                        if not piece:
                            break
                        chunks.append(piece)
                        record['body_bytes_observed'] += len(piece)
                        receipt['metadata_BODY_bytes_received'] += len(piece)
                    require(record['body_bytes_observed'] == 3136, 'Truncated metadata node; no retry')
                    body = b''.join(chunks)
                level, keys, coords, children = parse_node(body, r['address'], r['source_file_bytes'])
                require(level == 0, 'Only the frozen missing TREE leaf is accepted')
                for q in [157, 158]:
                    target = (12, 0, q * 1048576, 0)
                    selected = [i for i in range(len(children)) if coords[i] <= target < coords[i+1]]
                    require(len(selected) == 1 and coords[selected[0]] == target,
                            'Metadata leaf lacks exact157/158 origins')
                folder = out / r['label']
                folder.mkdir()
                filename = f"{r['address']:012d}_003136.bin"
                (folder / filename).write_bytes(body)
                record.update(state='PASS', body_sha256=sha(body), retained_file=filename)
            except BaseException as error:
                record.update(state='FAILED_CLOSED_NO_RETRY', error_type=type(error).__name__, error=str(error))
                raise
            finally:
                save(out / 'RECEIPT.json', receipt)
        require(receipt['metadata_BODY_bytes_received'] == receipt['metadata_BODY_charged_upper_bound_bytes'] == 18816,
                'Metadata actual/charged BODY total differs')
        require(sha(scope_path.read_bytes()) == args.expected_scope_sha256, 'Metadata scope changed during run')
        for path, expected in scope['pinned_files'].items():
            require(sha((ROOT / path).read_bytes()) == expected, 'Pinned input changed during run: ' + path)
        measured = {'cpu_s': time.process_time(), 'wall_s': time.monotonic() - started,
                    'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(measured['cpu_s'] <= 15 and measured['wall_s'] <= 300
                and measured['peak_rss_bytes'] <= scope['memory_limit_bytes'], 'Measured resource cap exceeded')
        receipt.update(status='PASS_EXACT_SIX_METADATA_NODES_NO_SPECTRUM', completion_resource_guard=measured,
                       end_of_run_all_pins_verified=True)
    except BaseException as error:
        receipt.update(status='FAILED_CLOSED_NO_RETRY', error_type=type(error).__name__, error=str(error))
        raise
    finally:
        receipt.update(cpu_s=time.process_time(), wall_s=time.monotonic() - started,
                       peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
        save(out / 'RECEIPT.json', receipt)
        signal.alarm(0)


if __name__ == '__main__':
    main()
