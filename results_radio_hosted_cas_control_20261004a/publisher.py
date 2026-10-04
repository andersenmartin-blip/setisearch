"""One-shot administrative evidence publication; inert on import.

The child must be reaped before this separate 120-second/20-call budget starts.
All original regular files are archived losslessly. This publisher's own receipts
are excluded from that archive and remain local/runner evidence: no recursion and
no scientific authority are inferred from an administrative publication.
"""
import argparse
import base64
import gzip
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

# The isolated CLI does not search ambient module paths for project code.
_control_path = Path(__file__).resolve().with_name('control.py')
_control_spec = importlib.util.spec_from_file_location('radio_hosted_control_frozen', _control_path)
c = importlib.util.module_from_spec(_control_spec)
_control_spec.loader.exec_module(c)

NAMESPACE = 'radio-hosted-cas-control-20261004a'
EVIDENCE_PATH = c.PREFIX + '/evidence.json'
PUBLICATION_DIRECTORY = 'publication'
MAX_CALLS, MAX_SECONDS = 20, 120
MAX_TOTAL, MAX_RETAINED = 12 << 20, 12 << 20
ORIGINAL_CAP, ARCHIVE_CAP = 8 << 20, 1 << 20
SECRET = re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|Bearer [A-Za-z0-9_.-]{20,})')


def safe_body(raw, transport=None):
    c.require(type(raw) is bytes and not SECRET.search(raw))
    c.require(transport is None or not transport.contains_secret(raw))


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def read_stable(path, *, limit=ORIGINAL_CAP, transport=None, after_read=None):
    """Read a sole-link regular file and compare opened and named identities."""
    path = Path(path)
    before = path.lstat()
    c.require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        c.require(identity(before) == identity(opened))
        raw = stream.read(limit + 1)
        if after_read is not None:
            after_read(path)
        final = os.fstat(stream.fileno())
        named = path.lstat()
    c.require(identity(before) == identity(final) == identity(named) and len(raw) == before.st_size)
    safe_body(raw, transport)
    return raw, before


def inventory(root, excluded=None):
    root = Path(root)
    c.require(root.is_absolute() and root == root.resolve() and root.is_dir() and not root.is_symlink())
    rows = {}
    stack = [root]
    while stack:
        directory = stack.pop()
        for path in sorted(directory.iterdir()):
            if excluded is not None and path == excluded:
                continue
            info = path.lstat()
            relative = path.relative_to(root).as_posix()
            c.require(not path.is_symlink() and path.resolve().is_relative_to(root))
            if stat.S_ISDIR(info.st_mode):
                rows[relative + '/'] = identity(info)
                stack.append(path)
            else:
                c.require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1)
                rows[relative] = identity(info)
    return rows


def archive(root, proof, report, status, *, excluded=None, transport=None, after_read=None):
    """No source/raw body is discarded or truncated to make a successful archive."""
    before = inventory(root, excluded)
    files = {}
    root_info = Path(root).lstat()
    logical, allocated = root_info.st_size, max(root_info.st_size, root_info.st_blocks * 512)
    for relative in sorted(before):
        if relative.endswith('/'):
            info = (Path(root) / relative[:-1]).lstat()
            c.require(identity(info) == before[relative])
            logical += info.st_size
            allocated += max(info.st_size, info.st_blocks * 512)
            c.require(logical <= ORIGINAL_CAP and allocated <= ORIGINAL_CAP)
            continue
        raw, info = read_stable(Path(root) / relative, transport=transport, after_read=after_read)
        c.require(identity(info) == before[relative])
        logical += len(raw)
        allocated += max(info.st_size, info.st_blocks * 512)
        c.require(logical <= ORIGINAL_CAP and allocated <= ORIGINAL_CAP)
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        files[relative] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                           'encoding': 'gzip_base64', 'content': base64.b64encode(compressed).decode()}
    c.require(before == inventory(root, excluded) and identity(root_info) == identity(Path(root).lstat()))
    result = {'schema': 'radio-hosted-cas-control-evidence-v1',
              'namespace': NAMESPACE, 'repository': c.REPOSITORY, 'branch': c.BRANCH,
              'activation': proof['activation'], 'run_id': proof['run_id'],
              'manifest_sha256': proof['manifest_sha256'], 'status': status,
              'scientific_authority': False, 'component_only': True,
              'original_scope_logical_bytes': logical, 'original_scope_allocated_bytes': allocated,
              'original_scope_cap_bytes': ORIGINAL_CAP, 'files': files,
              'publisher_receipts': 'EXCLUDED_NONRECURSIVE_LOCAL_AND_RUNNER_ONLY',
              'complete_child_streams_retained': report.get('full_retained') is True,
              'supervisor_child_reaped': report.get('direct_child_reaped') is True,
              'supervisor_child_launched': report.get('child_launched') is True}
    body = c.canonical(result)
    c.require(len(body) <= ARCHIVE_CAP)
    safe_body(body, transport)
    return body


class AdministrativeArtifacts:
    def __init__(self, output):
        self.path = Path(output)
        c.require(self.path.is_absolute() and self.path == self.path.resolve() and not self.path.exists())
        self.path.mkdir(mode=0o700)
        info = self.path.lstat()
        self.logical, self.allocated = info.st_size, max(info.st_size, info.st_blocks * 512)
        self.write('exclusive-claim.json', c.canonical({'exclusive': True, 'pid': os.getpid()}))

    def write(self, name, raw):
        c.require(type(raw) is bytes and '/' not in name and name not in ('', '.', '..'))
        charge = max(len(raw), ((len(raw) + 4095) // 4096) * 4096)
        c.require(self.logical + len(raw) + 4096 <= MAX_RETAINED
                  and self.allocated + charge + 4096 <= MAX_RETAINED)
        fd = os.open(self.path / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        infos = [self.path.lstat(), *(path.lstat() for path in self.path.iterdir())]
        self.logical = sum(info.st_size for info in infos)
        self.allocated = sum(max(info.st_size, info.st_blocks * 512) for info in infos)
        c.require(self.logical <= MAX_RETAINED and self.allocated <= MAX_RETAINED)
        fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def supervisor_terminal(report):
    c.require(type(report) is dict and report.get('schema') == 'radio-hosted-cas-supervisor-observation-v1')
    c.require(report.get('component_only') is True and report.get('scientific_authority') is False
              and report.get('no_retry') is True)
    c.require(type(report.get('full_retained')) is bool)
    c.require(type(report.get('launch_attempted')) is bool and type(report.get('launched')) is bool
              and type(report.get('no_child_launch_proven')) is bool)
    child = report.get('direct_child')
    if child is None:
        c.require(report.get('status') == 'CLOSED_BEFORE_CHILD'
                  and report.get('no_child_launch_proven') is True
                  and report['launch_attempted'] is False and report['launched'] is False)
    else:
        c.require(report.get('direct_child_reaped') is True
                  and report['launch_attempted'] is True and report['launched'] is True
                  and report['no_child_launch_proven'] is False
                  and type(child) is dict and type(child.get('pid')) is int and child['pid'] > 0
                  and type(child.get('wait_status')) is int
                  and type(child.get('exit_code')) is int
                  and type(child.get('reaped_epoch_ns')) is int and child['reaped_epoch_ns'] > 0
                  and type(child.get('wait4_max_rss_bytes')) is int
                  and child['wait4_max_rss_bytes'] >= 0
                  and report.get('status') in ('COMPONENT_OBSERVED', 'CLOSED_FAILED'))
    return {**report, 'child_launched': child is not None}


def accepted_candidate(witness, activation, proof, baseline):
    """Rebuild A from independently pinned local activation objects, not witness roots."""
    c.require(type(witness) is dict)
    for field in ('oid', 'tree', 'parent', 'blob'):
        c.sha(witness.get(field))
    c.require(witness['parent'] == activation and witness.get('path') == c.STATE_PATH)
    try:
        raw = bytes.fromhex(witness['raw_commit_hex'])
        body = bytes.fromhex(witness['body_hex'])
    except Exception:
        raise c.ClosedError() from None
    expected = c.canonical({'schema': 'radio-hosted-cas-control-state-v1', 'engineering_only': True,
        'purpose': 'accepted-cas', 'activation': activation, 'parent': activation,
        'manifest_sha256': proof['manifest_sha256'], 'run_id': proof['run_id'], **c.FALSE_AUTHORITY})
    c.require(body == expected and c.git_oid('blob', body) == witness['blob'])
    root, owned = dict(baseline['root']), dict(baseline['owned'])
    c.require('service-state.json' not in owned and 'evidence.json' not in owned)
    owned['service-state.json'] = ('100644', 'blob', witness['blob'])
    root[c.PREFIX] = ('040000', 'tree', c.git_oid('tree', c.tree_bytes(owned)))
    tree = c.git_oid('tree', c.tree_bytes(root))
    c.require(tree == witness['tree'] and raw == c.commit_bytes(tree, activation,
        'Engineering CAS control: accepted-cas') and c.git_oid('commit', raw) == witness['oid'])
    return {'oid': witness['oid'], 'tree': tree, 'root': root, 'owned': owned,
            'blob': witness['blob'], 'body': body, 'raw': raw, 'parent': activation, 'path': c.STATE_PATH}


def allowed_head(head, activation, candidate, child_status):
    c.sha(head)
    c.require(head in {activation, candidate['oid'] if candidate else activation})
    if child_status == 'SERVICE_COMPONENT_CONTROL_PASSED':
        c.require(candidate is not None and head == candidate['oid'])
    c.require(child_status in ('SERVICE_COMPONENT_CONTROL_PASSED', 'CLOSED_FAILED', 'CLOSED_BEFORE_CHILD'))
    return head


class Publisher(c.Control):
    def __init__(self, transport, output, proof, root, expected_manifest, baseline, *, clock=time.monotonic,
                 started=None):
        self.transport, self.clock, self.started = transport, clock, clock() if started is None else started
        self.calls = self.total = self.attempted = self.mutations = 0
        self.proof, self.root, self.expected_manifest = proof, Path(root), expected_manifest
        self.activation, self.run_id = c.sha(proof['activation']), proof['run_id']
        self.output, self.baseline = Path(output), baseline
        self.artifacts = AdministrativeArtifacts(self.output / PUBLICATION_DIRECTORY)
        self.tree_cache = {}
        self.recovery = None

    def remaining(self):
        remaining = MAX_SECONDS - (self.clock() - self.started)
        c.require(remaining > 0)
        return remaining

    def api(self, method, suffix, payload=None, *, graphql=False, allow_error=False):
        c.require(self.calls < MAX_CALLS)
        c.verify_proof(self.proof, self.activation, self.run_id, self.root, self.expected_manifest)
        self.remaining()
        path = '/graphql' if graphql else '/repos/' + c.REPOSITORY + '/' + suffix
        raw = b'' if payload is None else c.canonical(payload)
        request = c.canonical({'method': method, 'path': path, 'body': payload})
        safe_body(request, self.transport)
        reply_allowance = c.MAX_RESPONSE
        c.require(self.total + len(request) + reply_allowance <= MAX_TOTAL
                  and self.artifacts.logical + len(request) + reply_allowance + 16384 <= MAX_RETAINED
                  and self.artifacts.allocated + len(request) + reply_allowance + 16384 <= MAX_RETAINED)
        self.calls += 1
        number = '%02d' % self.calls
        self.artifacts.write(number + '-request.json', request)
        self.total += len(request)
        dispatched = received = False
        try:
            dispatched = True
            status, response = self.transport(method, path, raw, min(30, self.remaining()))
            c.require(type(status) is int and type(response) is bytes)
            c.require(len(response) <= reply_allowance)
            received = True
            self.total += len(response)
            try:
                safe_body(response, self.transport)
            except c.ClosedError:
                self.artifacts.write(number + '-response-redacted.json', c.canonical({'redacted': True}))
                raise
            capped = len(response) == c.MAX_RESPONSE
            self.artifacts.write(number + ('-response-partial.raw' if capped else '-response.raw'), response)
            self.artifacts.write(number + '-journal.json', c.canonical({'call': self.calls,
                'status': status, 'request_sha256': hashlib.sha256(request).hexdigest(),
                'response_sha256': hashlib.sha256(response).hexdigest(), 'total_bytes': self.total,
                'response_capped_unknown_eof': capped}))
            # At the cap the transport cannot prove EOF. Preserve the exact
            # retained prefix and stop, even if it happens to be valid JSON.
            c.require(len(response) < c.MAX_RESPONSE and self.total <= MAX_TOTAL)
            self.remaining()
            answer = c.strict_json(response)
            c.require(type(answer) is dict and status in (200, 201))
            if not allow_error:
                c.require(not answer.get('errors'))
            return status, answer
        except BaseException:
            if dispatched and not received:
                self.total += reply_allowance
            self.artifacts.write(number + '-error.json', c.canonical({'closed': True,
                'unknown_response_allowance_spent': dispatched and not received,
                'wire_charge_scope': 'CONSERVATIVE_REQUEST_ENVELOPES_AND_REPLY_BYTES'}))
            raise c.ClosedError() from None

    def publication_candidate(self, parent, root, owned, body):
        c.require('evidence.json' not in owned)
        blob = c.git_oid('blob', body)
        self.recovery = {'blob': blob, 'archive_bytes': len(body),
                         'archive_sha256': hashlib.sha256(body).hexdigest(),
                         'blob_create_acknowledged': False, 'scientific_authority': False}
        self.artifacts.write('archive-object-prospect.json', c.canonical(self.recovery))
        _, result = self.api('POST', 'git/blobs', {'content': base64.b64encode(body).decode(), 'encoding': 'base64'})
        c.require(result.get('sha') == blob)
        self.recovery['blob_create_acknowledged'] = True
        self.artifacts.write('archive-blob-ack.json', c.canonical(self.recovery))
        new_owned = dict(owned); new_owned['evidence.json'] = ('100644', 'blob', blob)
        new_root = dict(root)
        new_root[c.PREFIX] = ('040000', 'tree', c.git_oid('tree', c.tree_bytes(new_owned)))
        tree = c.git_oid('tree', c.tree_bytes(new_root))
        parent_tree = c.git_oid('tree', c.tree_bytes(root))
        _, result = self.api('POST', 'git/trees', {'base_tree': parent_tree,
            'tree': [{'path': EVIDENCE_PATH, 'mode': '100644', 'type': 'blob', 'sha': blob}]})
        c.require(result.get('sha') == tree)
        message = 'Preserve engineering hosted CAS control evidence'
        raw = c.commit_bytes(tree, parent, message)
        oid = c.git_oid('commit', raw)
        self.recovery.update(precomputed_commit=oid, tree=tree, parent=parent)
        self.artifacts.write('publication-commit-prospect.json', c.canonical(self.recovery))
        _, result = self.api('POST', 'git/commits', {'tree': tree, 'parents': [parent],
            'message': message + '\n', 'author': c.IDENTITY, 'committer': c.IDENTITY})
        returned = result.get('sha')
        if type(returned) is str and re.fullmatch('[0-9a-f]{40}', returned):
            self.recovery['unqualified_returned_commit_oid'] = returned
            self.artifacts.write('unqualified-commit-return.json', c.canonical({
                'unqualified_returned_commit_oid': returned, 'scientific_authority': False,
                'intrinsic_commit_bytes_qualified': False}))
        c.require(result.get('sha') == oid)
        return {'oid': oid, 'raw': raw, 'tree': tree, 'root': new_root, 'owned': new_owned,
                'blob': blob, 'body': body, 'parent': parent, 'path': EVIDENCE_PATH}

    def run(self):
        c.require(not self.attempted)
        self.attempted = True
        new = body = None
        pre_cas_readback_complete = False
        try:
            c.verify_proof(self.proof, self.activation, self.run_id, self.root, self.expected_manifest)
            report = supervisor_terminal(c.strict_json(read_stable(self.output / 'terminal.json',
                                                                   transport=self.transport)[0]))
            outcome = c.strict_json(read_stable(self.output / 'supervisor-outcome.json',
                                               transport=self.transport)[0])
            c.require(type(outcome) is dict and outcome.get('component_only') is True
                      and outcome.get('scientific_authority') is False)
            child_file = self.output / 'child' / 'result.json'
            child_status = ('CLOSED_BEFORE_CHILD' if not report['child_launched'] else 'CLOSED_FAILED')
            if report['child_launched'] and child_file.exists():
                child_status = c.strict_json(read_stable(child_file, transport=self.transport)[0]).get('status')
            if child_status == 'SERVICE_COMPONENT_CONTROL_PASSED':
                if not (report.get('status') == 'COMPONENT_OBSERVED'
                        and report['direct_child']['exit_code'] == 0
                        and report['full_retained'] is True
                        and outcome.get('status') == 'COMPONENT_OBSERVED'):
                    child_status = 'CLOSED_FAILED'
            if outcome.get('status') == 'CLOSED_FAILED':
                child_status = 'CLOSED_FAILED'
            witness_file = self.output / 'child' / 'accepted-candidate.json'
            candidate = (accepted_candidate(c.strict_json(read_stable(witness_file,
                transport=self.transport)[0]), self.activation, self.proof, self.baseline)
                         if witness_file.exists() else None)
            body = archive(self.output, self.proof, report, child_status,
                           excluded=self.artifacts.path, transport=self.transport)
            self.artifacts.write('archive.json', body)
            parent = allowed_head(self.head(), self.activation, candidate, child_status)
            root, owned = self.baseline['root'], self.baseline['owned']
            if parent != self.activation:
                self.immutable(candidate)
                root, owned = candidate['root'], candidate['owned']
            new = self.publication_candidate(parent, root, owned, body)
            self.artifacts.write('publication-candidate.json', c.canonical({
                'oid': new['oid'], 'parent': parent, 'tree': new['tree'], 'blob': new['blob'],
                'raw_commit_hex': new['raw'].hex(), 'path': EVIDENCE_PATH}))
            self.immutable(new)
            pre_cas_readback_complete = True
            c.require(self.head() == parent)
            self.cas(parent, new['oid'], 'administrative-evidence')
            c.require(self.head() == new['oid'])
            self.immutable(new)
            c.verify_proof(self.proof, self.activation, self.run_id, self.root, self.expected_manifest)
            self.remaining()
            result = {'schema': 'radio-hosted-cas-control-evidence-publication-v1',
                'status': 'ADMINISTRATIVE_EVIDENCE_PUBLISHED' if type(self.transport) is c.HTTPSTransport
                          else 'SYNTHETIC_PUBLICATION_ONLY',
                'commit': new['oid'], 'parent': parent, 'tree': new['tree'], 'blob': new['blob'],
                'archive_bytes': len(body), 'archive_sha256': hashlib.sha256(body).hexdigest(),
                'calls': self.calls, 'request_reply_bytes': self.total, 'automatic_retry': False,
                'scientific_authority': False, 'component_only': True,
                'publication_receipts_in_archive': False}
        except BaseException:
            result = {'schema': 'radio-hosted-cas-control-evidence-publication-v1',
                'status': 'CLOSED_FAILED', 'attempt_spent': True, 'automatic_retry': False,
                'mutations_attempted': self.mutations, 'mutation_may_have_landed': self.mutations > 0,
                'calls': self.calls, 'request_reply_bytes': self.total, 'scientific_authority': False,
                'component_only': True, 'publication_receipts_in_archive': False}
            if self.recovery is not None:
                result['recoverable_archive_object'] = dict(self.recovery)
            if new is not None:
                result['recoverable_precreated_objects'] = {
                    'commit': new['oid'], 'parent': new['parent'], 'tree': new['tree'],
                    'blob': new['blob'], 'archive_bytes': len(body),
                    'archive_sha256': hashlib.sha256(body).hexdigest(),
                    'pre_cas_immutable_readback_complete': pre_cas_readback_complete}
        self.artifacts.write('result.json', c.canonical(result))
        return result


def local_baseline(root, activation):
    """Intrinsic checkout object witnesses; no network or credential access."""
    root = Path(root)
    def git(*args):
        environment = {'PATH': os.environ.get('PATH', ''), 'LC_ALL': 'C',
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
            'GIT_CONFIG_SYSTEM': '/dev/null', 'GIT_NO_LAZY_FETCH': '1',
            'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}
        result = subprocess.run(['git', '--no-replace-objects', '--literal-pathspecs',
            '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=',
            '-C', str(root), *args], env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=10, check=True)
        c.require(len(result.stdout) <= c.MAX_RESPONSE)
        return result.stdout
    raw = git('cat-file', 'commit', c.sha(activation))
    c.require(c.git_oid('commit', raw) == activation)
    first_line = raw.split(b'\n', 1)[0]
    c.require(first_line.startswith(b'tree '))
    tree = c.sha(first_line[5:].decode('ascii'))
    def entries(oid):
        raw_tree = git('cat-file', 'tree', oid)
        c.require(c.git_oid('tree', raw_tree) == oid)
        result = {}
        for row in git('ls-tree', '-z', oid).split(b'\0'):
            if not row:
                continue
            header, name = row.split(b'\t', 1)
            mode, kind, obj = header.decode('ascii').split(' ')
            result[name.decode('utf-8')] = (mode, kind, c.sha(obj))
        c.require(c.tree_bytes(result) == raw_tree)
        return result
    top = entries(tree)
    c.require(c.PREFIX in top and top[c.PREFIX][:2] == ('040000', 'tree'))
    owned = entries(top[c.PREFIX][2])
    c.require('service-state.json' not in owned and 'evidence.json' not in owned)
    return {'root': top, 'owned': owned, 'tree': tree}


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--proof', required=True)
    args = parser.parse_args()
    c.require(Path(args.proof).is_absolute())
    env = os.environ
    c.require(env.get('GITHUB_REPOSITORY') == c.REPOSITORY and env.get('GITHUB_REF') == c.REF
              and env.get('GITHUB_EVENT_NAME') == 'push' and env.get('GITHUB_RUN_ATTEMPT') == '1'
              and env.get('GITHUB_WORKFLOW_REF') == c.REPOSITORY + '/' + c.WORKFLOW_PATH + '@' + c.REF)
    proof = c.strict_json(read_stable(Path(args.proof))[0])
    c.require(proof['run_id'] == env.get('GITHUB_RUN_ID') and proof['activation'] == env.get('GITHUB_SHA'))
    root = Path(__file__).resolve().parents[1]
    c.require(root == Path(env.get('GITHUB_WORKSPACE', '')).resolve())
    freeze_raw = (root / c.FREEZE_PATH).read_bytes()
    expected_manifest = hashlib.sha256(freeze_raw).hexdigest()
    c.verify_proof(proof, proof['activation'], proof['run_id'], root, expected_manifest)
    baseline = local_baseline(root, proof['activation'])
    publisher = Publisher(c.HTTPSTransport(env.get('GITHUB_TOKEN')), args.output, proof, root,
                          expected_manifest, baseline, started=started)
    result = publisher.run()
    print(c.canonical(result).decode(), end='')
    return 0 if result['status'] == 'ADMINISTRATIVE_EVIDENCE_PUBLISHED' else 1


if __name__ == '__main__':
    try:
        status = main()
    except Exception:
        print('ADMINISTRATIVE_PUBLICATION_CLOSED_FAILED', file=sys.stderr)
        status = 1
    sys.exit(status)
