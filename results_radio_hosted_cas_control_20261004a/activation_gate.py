"""Read-only first-attempt Actions activation prerequisite, not qualification.

The marker binds a published source list and its canonical digest. This gate does
not authenticate a remote readback service, globally reserve an experiment,
qualify the hosted runtime/bootstrap, or issue any scientific authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

NAMESPACE = 'radio-hosted-cas-control-20261004a'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
PREFIX = 'results_radio_hosted_cas_control_20261004a'
MANIFEST = 'config/radio_hosted_cas_control_20261004a.freeze.json'
MARKER = 'config/radio_hosted_cas_control_20261004a.activate.json'
SOURCES = tuple(sorted((
    '.github/workflows/radio_hosted_cas_control_20261004a.yml',
    'RADIO_HOSTED_CAS_CONTROL_2026-10-04_PROTOCOL.md',
    *(PREFIX + '/' + name for name in (
        'activation_gate.py', 'control.py', 'publisher.py', 'supervisor.py',
        'test_activation_gate.py', 'test_control.py', 'test_publisher.py',
        'test_supervisor.py')),
)))
LIMITS = {
    'control_wall_seconds': 180, 'control_api_calls': 40,
    'response_bytes': 2097152, 'wire_bytes': 8388608,
    'retained_bytes': 8388608, 'publication_wall_seconds': 120,
    'publication_api_calls': 20, 'publication_wire_bytes': 12582912,
    'publication_retained_bytes': 12582912,
}
ALLOCATION = {'identity': NAMESPACE, 'wall_seconds': 300,
              'retained_bytes': 20971520, 'attempts': 1}
MUST_BE_ABSENT = {
    MARKER, PREFIX + '/service-state.json', PREFIX + '/conflict-test-state.json',
    PREFIX + '/evidence.json',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def sha(value, count):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % count, value):
        raise ValueError('Canonical lowercase hexadecimal identity required')
    return value


def object_id(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode()
                        + b'\0' + raw).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field refused')
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError('Nonfinite JSON number refused')))


def git_read(root, *arguments):
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                       GIT_CONFIG_SYSTEM='/dev/null', GIT_NO_LAZY_FETCH='1',
                       GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    result = subprocess.run(
        ['git', '--no-replace-objects', '--literal-pathspecs',
         '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
         '-c', 'credential.helper=', '-C', str(root), *arguments],
        env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=20, check=False)
    if result.returncode != 0 or len(result.stdout) > 4194304 or len(result.stderr) > 65536:
        raise ValueError('Bounded read-only Git operation failed')
    return result.stdout


def _tree(read, commit):
    entries = {}
    for row in read('ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if not row:
            continue
        header, path = row.split(b'\t', 1)
        mode, kind, blob = header.decode('ascii').split()
        name = path.decode('utf-8')
        if name in entries:
            raise ValueError('Duplicate Git tree member')
        entries[name] = (mode, kind, sha(blob, 40))
    return entries


def _parents(read, commit):
    raw = read('cat-file', 'commit', commit)
    if object_id('commit', raw) != commit or b'\n\n' not in raw:
        raise ValueError('Intrinsic original Git commit identity differs')
    headers = raw.split(b'\n\n', 1)[0].split(b'\n')
    parents = [line[7:].decode('ascii') for line in headers if line.startswith(b'parent ')]
    trees = [line[5:].decode('ascii') for line in headers if line.startswith(b'tree ')]
    if len(trees) != 1:
        raise ValueError('Exactly one original commit tree required')
    sha(trees[0], 40)
    return [sha(parent, 40) for parent in parents]


def _local(root, relative):
    path = root / relative
    for parent in (path, *path.parents):
        if parent == root.parent:
            break
        if parent.is_symlink():
            raise ValueError('Source symlink or symlink ancestor refused')
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 4194304:
        raise ValueError('Bounded independent ordinary source file required')
    raw = path.read_bytes()
    after = path.stat(follow_symlinks=False)
    identity = lambda value: (value.st_dev, value.st_ino, value.st_mode,
                              value.st_nlink, value.st_size, value.st_mtime_ns,
                              value.st_ctime_ns)
    if identity(before) != identity(after) or len(raw) != before.st_size:
        raise ValueError('Source identity changed while reading')
    return raw


def _runtime_state(path):
    if not path.startswith(PREFIX + '/') or path in SOURCES:
        return False
    parts = path[len(PREFIX) + 1:].split('/')
    # Selected source and retained development logs are not runtime claims.
    if path.endswith('.log') and 'development' in parts[-1]:
        return False
    return any(re.search(r'(^|[._-])(claim|claims|terminal|terminals)([._-]|$)',
                         part.lower()) for part in parts)


def verify(root, environment):
    root = Path(root).resolve()
    required = {'GITHUB_REPOSITORY': REPOSITORY,
                'GITHUB_REF': 'refs/heads/' + BRANCH,
                'GITHUB_EVENT_NAME': 'push', 'GITHUB_RUN_ATTEMPT': '1'}
    if any(environment.get(key) != value for key, value in required.items()):
        raise ValueError('Only the fixed repository/ref first push attempt permitted')
    activation = sha(environment.get('GITHUB_SHA'), 40)
    run_id = environment.get('GITHUB_RUN_ID')
    if not isinstance(run_id, str) or not re.fullmatch('[1-9][0-9]{0,19}', run_id):
        raise ValueError('Canonical positive Actions run ID required')
    read = lambda *args: git_read(root, *args)
    if read('rev-parse', '--verify', 'HEAD').decode('ascii').strip() != activation:
        raise ValueError('Checkout HEAD differs from exact activation')
    marker_raw = _local(root, MARKER)
    marker = _json(marker_raw)
    marker_keys = {'schema', 'namespace', 'repository', 'branch', 'preparation',
                   'manifest_sha256', 'source_readback_sha256', 'allocation'}
    if (not isinstance(marker, dict) or set(marker) != marker_keys
            or marker['schema'] != 'radio-hosted-cas-control-activation-v1'
            or marker['namespace'] != NAMESPACE or marker['repository'] != REPOSITORY
            or marker['branch'] != BRANCH):
        raise ValueError('Exact fixed activation marker required')
    preparation = sha(marker['preparation'], 40)
    sha(marker['manifest_sha256'], 64); sha(marker['source_readback_sha256'], 64)
    allocation = marker['allocation']
    if (not isinstance(allocation, dict) or set(allocation) != set(ALLOCATION)
            or allocation != ALLOCATION
            or any(type(allocation[key]) is not int
                   for key in ('wall_seconds', 'retained_bytes', 'attempts'))):
        raise ValueError('Exact independent one-attempt allocation required')
    if _parents(read, activation) != [preparation]:
        raise ValueError('Activation must have exactly the preparation as sole parent')
    _parents(read, preparation)
    prior = _tree(read, preparation); current = _tree(read, activation)
    if any(path in prior for path in MUST_BE_ABSENT) or any(_runtime_state(path) for path in prior):
        raise ValueError('Preparation already contains an activation or runtime state')
    marker_entry = ('100644', 'blob', object_id('blob', marker_raw))
    if current != {**prior, MARKER: marker_entry}:
        raise ValueError('Activation must add only its normal-blob marker')
    if read('cat-file', 'blob', marker_entry[2]) != marker_raw:
        raise ValueError('Marker local bytes differ from exact Git blob')
    manifest_raw = _local(root, MANIFEST)
    if hashlib.sha256(manifest_raw).hexdigest() != marker['manifest_sha256']:
        raise ValueError('Exact independently pinned manifest bytes differ')
    manifest = _json(manifest_raw)
    if (not isinstance(manifest, dict)
            or set(manifest) != {'schema', 'namespace', 'repository', 'branch', 'source_files', 'limits'}
            or manifest['schema'] != 'radio-hosted-cas-control-freeze-v1'
            or manifest['namespace'] != NAMESPACE or manifest['repository'] != REPOSITORY
            or manifest['branch'] != BRANCH):
        raise ValueError('Exact fixed source freeze manifest required')
    limits = manifest['limits']
    if (not isinstance(limits, dict) or set(limits) != set(LIMITS) or limits != LIMITS
            or any(type(value) is not int for value in limits.values())):
        raise ValueError('Original exact control and publication limits required')
    rows = manifest['source_files']
    if (not isinstance(rows, list) or len(rows) != len(SOURCES)
            or any(not isinstance(row, dict) or set(row) != {'path', 'bytes', 'sha256'} for row in rows)
            or [row['path'] for row in rows] != list(SOURCES)):
        raise ValueError('Exactly the ten sorted selected source rows required')
    if hashlib.sha256(canonical(rows)).hexdigest() != marker['source_readback_sha256']:
        raise ValueError('Independent canonical source-list readback digest differs')
    selected = [(MANIFEST, manifest_raw)]
    for row in rows:
        if type(row['bytes']) is not int or not 0 < row['bytes'] <= 4194304:
            raise ValueError('Bounded positive integer source size required')
        sha(row['sha256'], 64)
        raw = _local(root, row['path'])
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Selected local source bytes differ from frozen pins')
        selected.append((row['path'], raw))
    for relative, raw in selected:
        entry = ('100644', 'blob', object_id('blob', raw))
        if prior.get(relative) != entry or current.get(relative) != entry:
            raise ValueError('Selected preparation/activation source blob differs')
        if read('cat-file', 'blob', entry[2]) != raw:
            raise ValueError('Complete raw preparation blob readback differs')
    return {'schema': 'radio-hosted-cas-control-activation-proof-v1',
            'repository': REPOSITORY, 'branch': BRANCH, 'namespace': NAMESPACE,
            'activation': activation, 'preparation': preparation,
            'manifest_sha256': marker['manifest_sha256'], 'run_id': run_id,
            'source_files': rows}


def persist(proof, output, *, root, runner_temp):
    output = Path(output)
    root = Path(root).resolve(); temporary = Path(runner_temp).resolve()
    if (not output.is_absolute() or output.parent != output.parent.resolve()
            or not output.is_relative_to(temporary) or output.is_relative_to(root)):
        raise ValueError('Exclusive proof must be inside canonical RUNNER_TEMP outside checkout')
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(canonical(proof) + b'\n'); handle.flush(); os.fsync(handle.fileno())
    directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    proof = verify(Path.cwd(), os.environ)
    persist(proof, arguments.output, root=Path.cwd(), runner_temp=os.environ['RUNNER_TEMP'])


if __name__ == '__main__':
    main()
