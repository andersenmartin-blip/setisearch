"""Bounded, one-shot Git archive of an already-terminal engineering v2 case.

This is a snapshot publisher, not a remote event store, lease, or execution
resume mechanism. The transport is injected; no credentials or RNG are used.
Every original physical/base file and every journal event/pointer version is
kept byte-for-byte. A single fast-forward commit exposes archive, manifest and
HEAD together. Any ambiguity poisons the attempt, including a lost update ack.
"""
import base64
from dataclasses import asdict, dataclass
import hashlib
import json
import re
import time
from types import MappingProxyType
from urllib.parse import quote

from .empty_null_radio import canonical
from . import physical_evidence_radio as naming
from . import physical_evidence_v2_radio as physical
from .physical_case_v2_radio import policy as parent_policy
from . import whole_cadence_event_store_radio as events
from . import whole_cadence_journal_radio as journal
from .whole_cadence_reference_radio import digest

REPO = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
PREFIX = 'results_radio_v2_parent_2026-09-30/live01'
SCHEMA = 'radio-engineering-v2-event-snapshot-archive-v1'
MAX_BLOB_BYTES = 262144
RESPONSE_RESERVATIONS = MappingProxyType({'fetch': 4 * 1024**2,
    'create_blob': 8192, 'create_tree': 262144, 'create_commit': 8192,
    'update_ref': 8192, 'fetch_file': 512 * 1024})


def git_object(kind, data):
    return hashlib.sha1(kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def git_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('Exact Git SHA required')
    return value


def safe_path(value):
    if (not isinstance(value, str) or any(p in ('', '.', '..') for p in value.split('/'))
            or '\\' in value or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Ordinary relative archive path required')
    return value


@dataclass(frozen=True)
class Limits:
    calls: int = 1024
    request_bytes: int = 64 * 1024**2
    response_bytes: int = 64 * 1024**2
    stored_bytes: int = 32 * 1024**2
    files: int = 256
    seconds: int = 1800

    def validate(self):
        hard = asdict(Limits())
        if any(type(v) is not int or not 0 < v <= hard[k] for k, v in asdict(self).items()):
            raise ValueError('Finite prospective archive bounds required')
        return self


@dataclass(frozen=True)
class Bundle:
    """Prepared immutable bytes. The separate SHA256 pin freezes the attempt."""
    files: object
    manifest_bytes: bytes
    freeze_bytes: bytes
    limits: Limits

    @property
    def sha256(self):
        return hashlib.sha256(self.freeze_bytes).hexdigest()


def _copy_map(values):
    if not isinstance(values, dict) and not isinstance(values, MappingProxyType):
        raise ValueError('Explicit raw file byte map required')
    result = {}
    for name, data in values.items():
        safe_path(name)
        if not isinstance(data, bytes):
            raise ValueError('Exact immutable bytes required')
        result[name] = data
    return result


def _validated_maps(physical_files, journal_files, base_files, pins):
    view = physical.inspect_files(physical_files,
        expected_config_sha256=pins['config_sha256'],
        expected_last_checkpoint_sha256=pins['last_checkpoint_sha256'])
    history = events.restore(journal_files,
        expected_genesis_sha256=pins['genesis_sha256'],
        expected_pointer_sha256=pins['pointer_sha256'])
    config = json.loads(view.config_bytes)
    doc = json.loads(history.revision_bytes[-1])
    state = journal.replay(doc)
    if not state['cases']:
        raise ValueError('Already-terminal parent case required')
    case = state['cases'][-1]
    if (case['status'] not in ('completed', 'failed')
            or case['binding']['case_identity'] != config['case_identity']
            or case['binding']['plan_sha256'] != config['plan_sha256']):
        raise ValueError('Physical/terminal parent case binding differs')
    if case['artifact_bytes'] > physical.MAX_BYTES:
        raise ValueError('Parent case exceeds fixed v2 18-MiB allocation')
    groups = doc['manifest']['artifact_groups']
    if set(groups) != {'physical'} or groups != parent_policy(config, max_files=groups['physical']['max_files']):
        raise ValueError('Exact v2 parent closure policy required')
    if config['budget_bytes'] != case['artifact_bytes'] - sum(groups['physical']['reserved_artifacts'].values()):
        raise ValueError('Parent/physical cumulative budget differs')
    for name, pin in config['existing_artifacts'].items():
        data = base_files.get(name)
        if data is None or len(data) != pin['bytes'] or physical.sha(data) != pin['sha256']:
            raise ValueError('Original charged base evidence differs')
    flat = {naming.flat_name(name): data for name, data in physical_files.items()}
    if set(flat) & set(base_files):
        raise ValueError('Parent base/physical filename collision')
    flat.update(base_files)
    if set(flat) != set(case['artifacts']):
        raise ValueError('Exact registered parent case inventory required')
    for name, record in case['artifacts'].items():
        if len(flat[name]) != record['size'] or physical.sha(flat[name]) != record['sha256']:
            raise ValueError('Registered parent artifact bytes differ')
    for policy in groups.values():
        if policy['prefix'] != 'physical-' or policy['binding_sha256'] != pins['config_sha256']:
            raise ValueError('Physical group reservation binding differs')
        raw = flat[policy['seal']]
        seal = json.loads(raw)
        members = {n: {'size': r['size'], 'sha256': r['sha256']}
                   for n, r in case['artifacts'].items() if n.startswith(policy['prefix'])}
        expected = {'schema': 'radio-engineering-artifact-group-v1',
            'case_identity': config['case_identity'], 'policy_sha256': digest(policy),
            'complete': seal.get('complete'), 'artifacts': members,
            'stored_bytes': sum(r['size'] for r in members.values()),
            'scientific_admission_authorized': False}
        if type(seal.get('complete')) is not bool or seal != expected or canonical(seal) != raw:
            raise ValueError('Exact parent physical group seal differs')
        if case['status'] == 'completed' and (not seal['complete'] or view.summary()['status'] != 'completed'):
            raise ValueError('Incomplete physical archive cannot label a completed case')
    return {'case_identity': config['case_identity'], 'plan_sha256': config['plan_sha256'],
        'case_status': case['status'], 'physical': view.summary(), 'journal': history.summary()}


def prepare_bundle(physical_files, journal_files, base_files, *, expected_config_sha256,
        expected_last_checkpoint_sha256, expected_genesis_sha256, expected_pointer_sha256,
        expected_parent_sha, expected_parent_tree_sha, limits=Limits()):
    """Validate and freeze all exact source bytes without opening any publisher."""
    limits.validate()
    physical_files, journal_files, base_files = map(_copy_map, (physical_files, journal_files, base_files))
    if (sum(map(len, physical_files.values())) + sum(map(len, journal_files.values()))
            + sum(map(len, base_files.values())) > limits.stored_bytes):
        raise ValueError('Stored archive byte cap exceeded')
    pins = {'config_sha256': expected_config_sha256,
        'last_checkpoint_sha256': expected_last_checkpoint_sha256,
        'genesis_sha256': expected_genesis_sha256, 'pointer_sha256': expected_pointer_sha256}
    for name, value in pins.items():
        journal._sha(value, name)
    summary = _validated_maps(physical_files, journal_files, base_files, pins)
    sources = {PREFIX + '/archive/' + group + '/' + name: (group, name, data)
               for group, values in [('physical', physical_files), ('journal', journal_files), ('base', base_files)]
               for name, data in values.items()}
    files = {}
    originals = {}
    for path, (group, name, data) in sorted(sources.items()):
        paths = [path] if len(data) <= MAX_BLOB_BYTES else [path + f'.part{i:04d}'
                for i in range((len(data) + MAX_BLOB_BYTES - 1) // MAX_BLOB_BYTES)]
        for i, stored in enumerate(paths):
            if stored in files or stored != path and stored in sources:
                raise ValueError('Transport part/original immutable path collision')
            files[stored] = data if len(paths) == 1 else data[i * MAX_BLOB_BYTES:(i + 1) * MAX_BLOB_BYTES]
        originals[path] = {'group': group, 'path': name, 'bytes': len(data),
            'sha256': physical.sha(data), 'blob': git_object('blob', data), 'stored_paths': paths}
    inventory = {path: {'bytes': len(data), 'sha256': physical.sha(data), 'blob': git_object('blob', data)}
                 for path, data in sorted(files.items())}
    manifest = canonical({'schema': SCHEMA, 'mode': 'engineering', 'repository': REPO,
        'branch': BRANCH, 'prefix': PREFIX, 'pins': pins, 'source_summary': summary,
        'files': inventory, 'original_files': originals, 'max_blob_bytes': MAX_BLOB_BYTES,
        'execution_restart_authorized': False,
        'scientific_admission_authorized': False, 'remote_event_store_qualified': False})
    files[PREFIX + '/manifest.json'] = manifest
    files[PREFIX + '/HEAD'] = physical.sha(manifest).encode() + b'\n'
    if (len(files) > limits.files or sum(map(len, files.values())) > limits.stored_bytes
            or any(len(v) > MAX_BLOB_BYTES for v in files.values())):
        raise ValueError('Complete archive/manifest/HEAD capacity exceeded')
    restored = restore_original_files(files, expected_manifest_sha256=physical.sha(manifest))
    if restored != {path: data for path, (_, _, data) in sources.items()}:
        raise ValueError('Prepared exact original byte reconstruction differs')
    freeze = canonical({'schema': SCHEMA, 'mode': 'engineering', 'repository': REPO,
        'branch': BRANCH, 'prefix': PREFIX, 'parent': git_sha(expected_parent_sha),
        'parent_tree': git_sha(expected_parent_tree_sha), 'limits': asdict(limits),
        'per_operation_response_reservations': dict(RESPONSE_RESERVATIONS),
        'files': {path: {'bytes': len(data), 'sha256': physical.sha(data), 'blob': git_object('blob', data)}
                  for path, data in sorted(files.items())}, 'manifest_sha256': physical.sha(manifest),
        'automatic_retry': False, 'single_atomic_commit': True,
        'execution_restart_authorized': False, 'scientific_admission_authorized': False})
    return Bundle(MappingProxyType(files), manifest, freeze, limits)


def restore_original_files(stored_files, *, expected_manifest_sha256):
    """Read-only reassembly of exact source bytes; no lease or execution state."""
    files = _copy_map(stored_files)
    hard = Limits()
    if (len(files) > hard.files or sum(map(len, files.values())) > hard.stored_bytes
            or any(len(v) > MAX_BLOB_BYTES for v in files.values())):
        raise ValueError('Bounded transport part inventory required')
    journal._sha(expected_manifest_sha256, 'manifest')
    raw = files[PREFIX + '/manifest.json']
    if physical.sha(raw) != expected_manifest_sha256 or files[PREFIX + '/HEAD'] != expected_manifest_sha256.encode() + b'\n':
        raise ValueError('Independent archive manifest/HEAD pin differs')
    manifest = json.loads(raw)
    if (canonical(manifest) != raw or manifest['schema'] != SCHEMA or manifest['mode'] != 'engineering'
            or manifest['repository'] != REPO or manifest['branch'] != BRANCH or manifest['prefix'] != PREFIX
            or manifest['max_blob_bytes'] != MAX_BLOB_BYTES
            or any(manifest[k] is not False for k in ('execution_restart_authorized',
                'scientific_admission_authorized', 'remote_event_store_qualified'))):
        raise ValueError('Exact engineering archive manifest required')
    if set(files) != set(manifest['files']) | {PREFIX + '/manifest.json', PREFIX + '/HEAD'}:
        raise ValueError('Exact transport part inventory differs')
    for path, record in manifest['files'].items():
        if record != {'bytes': len(files[path]), 'sha256': physical.sha(files[path]), 'blob': git_object('blob', files[path])}:
            raise ValueError('Stored transport part identity differs')
    restored = {}
    used = set()
    for path, record in manifest['original_files'].items():
        if (set(record) != {'group', 'path', 'bytes', 'sha256', 'blob', 'stored_paths'}
                or record['group'] not in ('physical', 'journal', 'base')
                or path != PREFIX + '/archive/' + record['group'] + '/' + safe_path(record['path'])
                or type(record['bytes']) is not int or not 0 <= record['bytes'] <= hard.stored_bytes):
            raise ValueError('Original source identity differs')
        expected_paths = [path] if record['bytes'] <= MAX_BLOB_BYTES else [path + f'.part{i:04d}'
            for i in range((record['bytes'] + MAX_BLOB_BYTES - 1) // MAX_BLOB_BYTES)]
        if record['stored_paths'] != expected_paths or used & set(expected_paths):
            raise ValueError('Original source transport order/collision differs')
        pieces = [files[p] for p in expected_paths]
        if len(expected_paths) > 1 and any(len(v) != MAX_BLOB_BYTES for v in pieces[:-1]):
            raise ValueError('Original source transport boundary differs')
        data = b''.join(pieces)
        if len(data) != record['bytes'] or physical.sha(data) != record['sha256'] or git_object('blob', data) != record['blob']:
            raise ValueError('Exact original source file bytes differ')
        restored[path] = data
        used.update(expected_paths)
    if used != set(manifest['files']):
        raise ValueError('Unreferenced transport part in archive')
    return MappingProxyType(restored)


class Stopped(RuntimeError):
    pass


class Publisher:
    """One process-local, bounded attempt; invoke(operation, parameters) -> dict."""
    def __init__(self, bundle, invoke, *, expected_bundle_sha256, clock=time.monotonic):
        if not isinstance(bundle, Bundle) or bundle.sha256 != expected_bundle_sha256:
            raise ValueError('Independent immutable bundle pin differs')
        bundle.limits.validate()
        freeze = json.loads(bundle.freeze_bytes)
        if (canonical(freeze) != bundle.freeze_bytes or freeze['limits'] != asdict(bundle.limits)
                or freeze['per_operation_response_reservations'] != dict(RESPONSE_RESERVATIONS)
                or set(bundle.files) != set(freeze['files'])
                or any(freeze['files'][p] != {'bytes': len(v), 'sha256': physical.sha(v), 'blob': git_object('blob', v)}
                       for p, v in bundle.files.items())
                or bundle.files[PREFIX + '/manifest.json'] != bundle.manifest_bytes
                or bundle.files[PREFIX + '/HEAD'] != physical.sha(bundle.manifest_bytes).encode() + b'\n'):
            raise ValueError('Prepared bundle contents changed')
        restore_original_files(bundle.files, expected_manifest_sha256=freeze['manifest_sha256'])
        self.bundle = bundle
        self.freeze = freeze
        self.invoke = invoke
        self.clock = clock
        self.started = clock()
        self.calls = self.request_bytes = self.response_bytes = 0
        self.response_charged_bytes = self.unknown_response_bytes = 0
        self.unknown_response_count = 0
        self.attempted = self.stopped = self.update_attempted = False
        self.events = []
        self.trees = {}
        self.receipt = None

    def _call(self, operation, **params):
        if self.stopped:
            raise Stopped('Archive attempt stopped; no retry')
        request = canonical(params)
        cap = self.bundle.limits
        reservation = RESPONSE_RESERVATIONS[operation]
        if (self.calls >= cap.calls or self.request_bytes + len(request) > cap.request_bytes
                or self.clock() - self.started > cap.seconds):
            raise ValueError('Frozen call/request/time bound exhausted')
        if self.response_charged_bytes + reservation > cap.response_bytes:
            raise ValueError('Frozen response/time capacity cannot reserve operation reply')
        self.calls += 1
        self.request_bytes += len(request)
        # Reserve a finite reply allowance before dispatch. A transport failure
        # retains the entire unknown charge. Exact replies settle to their true
        # JSON length, so successful calls do not accumulate unused allowances.
        self.response_charged_bytes += reservation
        event = {'call': self.calls, 'operation': operation, 'request_bytes': len(request),
                 'request_sha256': physical.sha(request), 'response_reserved_bytes': reservation,
                 'response_unknown': True}
        self.events.append(event)
        try:
            result = self.invoke(operation, params)
            response = canonical(result)
        except BaseException:
            self.unknown_response_bytes += reservation
            self.unknown_response_count += 1
            event['response_charged_bytes'] = reservation
            raise
        self.response_bytes += len(response)
        self.response_charged_bytes += len(response) - reservation
        event.update(response_bytes=len(response), response_sha256=physical.sha(response),
                     response_charged_bytes=len(response), response_unknown=False)
        if (len(response) > reservation or self.response_charged_bytes > cap.response_bytes
                or self.clock() - self.started > cap.seconds):
            raise ValueError('Frozen response/time bound exceeded')
        if not isinstance(result, dict):
            raise ValueError('Object transport response required')
        return result

    def _get(self, path):
        return self._call('fetch', url='https://api.github.com/repos/' + REPO + '/git/' + path)

    def _head(self):
        result = self._get('ref/heads/' + quote(BRANCH, safe=''))
        if result.get('ref') != 'refs/heads/' + BRANCH or result.get('object', {}).get('type') != 'commit':
            raise ValueError('Pinned branch identity/type differs')
        return git_sha(result['object']['sha'])

    def _commit(self, sha):
        result = self._get('commits/' + git_sha(sha))
        if result.get('sha') != sha:
            raise ValueError('Commit readback identity differs')
        return {'tree': git_sha(result['tree']['sha']), 'parents': [git_sha(p['sha']) for p in result['parents']]}

    def _tree(self, sha):
        git_sha(sha)
        if sha in self.trees:
            return self.trees[sha]
        result = self._get('trees/' + sha)
        if result.get('sha') != sha or result.get('truncated') is not False:
            raise ValueError('Missing/truncated tree readback')
        entries = {}
        allowed = {('040000', 'tree'), ('100644', 'blob'), ('100755', 'blob'), ('120000', 'blob'), ('160000', 'commit')}
        for row in result['tree']:
            name = safe_path(row['path'])
            if '/' in name or name in entries or (row['mode'], row['type']) not in allowed:
                raise ValueError('Git tree entry differs')
            entries[name] = {'mode': row['mode'], 'type': row['type'], 'sha': git_sha(row['sha'])}
        order = sorted(entries, key=lambda n: (n + ('/' if entries[n]['type'] == 'tree' else '')).encode())
        raw = b''.join(entries[n]['mode'].lstrip('0').encode() + b' ' + n.encode() + b'\0'
                       + bytes.fromhex(entries[n]['sha']) for n in order)
        if git_object('tree', raw) != sha:
            raise ValueError('Exact tree content hash differs')
        self.trees[sha] = entries
        return entries

    def _fresh_namespace(self, tree):
        for part in PREFIX.split('/'):
            row = self._tree(tree).get(part)
            if row is None:
                return
            if (row['mode'], row['type']) != ('040000', 'tree'):
                raise ValueError('Archive namespace ancestor is not ordinary')
            tree = row['sha']
        raise ValueError('Immutable archive namespace already exists; overwrite prohibited')

    def _delta(self, before_sha, after_sha, changes):
        before = {} if before_sha is None else self._tree(before_sha)
        after = self._tree(after_sha)
        groups = {}
        for path, value in changes.items():
            first, sep, tail = path.partition('/')
            groups.setdefault(first, {})[tail if sep else ''] = value
        if {n: v for n, v in before.items() if n not in groups} != {n: v for n, v in after.items() if n not in groups}:
            raise ValueError('Candidate tree changed an unrelated path')
        for first, remaining in groups.items():
            old, new = before.get(first), after.get(first)
            if '' in remaining:
                if len(remaining) != 1 or old is not None or new != {'mode': '100644', 'type': 'blob', 'sha': remaining['']}:
                    raise ValueError('Immutable archive leaf overwrite/content differs')
            else:
                if (new is None or (new['mode'], new['type']) != ('040000', 'tree')
                        or old is not None and (old['mode'], old['type']) != ('040000', 'tree')):
                    raise ValueError('Candidate archive directory differs')
                self._delta(None if old is None else old['sha'], new['sha'], remaining)

    def publish(self):
        if self.attempted or self.stopped:
            raise Stopped('One archive attempt only; no retry')
        self.attempted = True
        candidate = None
        try:
            if canonical(self.freeze) != self.bundle.freeze_bytes:
                raise ValueError('Prepared frozen publication state changed')
            parent, parent_tree = self.freeze['parent'], self.freeze['parent_tree']
            if self._head() != parent:
                raise ValueError('Frozen expected parent conflicts with fresh branch head')
            if self._commit(parent)['tree'] != parent_tree:
                raise ValueError('Frozen parent tree pin differs')
            self._fresh_namespace(parent_tree)
            changes = {}
            for path, data in sorted(self.bundle.files.items()):
                sha = git_object('blob', data)
                made = self._call('create_blob', repository_full_name=REPO,
                    content=base64.b64encode(data).decode(), encoding='base64')
                if made.get('sha') != sha:
                    raise ValueError('Created blob hash differs')
                changes[path] = sha
            made = self._call('create_tree', repository_full_name=REPO, base_tree_sha=parent_tree,
                tree_elements=[{'path': path, 'mode': '100644', 'type': 'blob', 'sha': sha}
                               for path, sha in sorted(changes.items())])
            tree = git_sha(made['sha'])
            self._delta(parent_tree, tree, changes)
            made = self._call('create_commit', repository_full_name=REPO, parent_sha=parent,
                tree_sha=tree, message='Engineering v2 event snapshot archive ' + self.bundle.sha256)
            candidate = git_sha(made['sha'])
            if self._commit(candidate) != {'tree': tree, 'parents': [parent]}:
                raise ValueError('Candidate exact parent/tree readback differs')
            if self._head() != parent:
                raise ValueError('Expected parent changed before fast-forward update')
            self.update_attempted = True
            updated = self._call('update_ref', repository_full_name=REPO,
                branch_name=BRANCH, sha=candidate, force=False)
            if updated.get('success') is not True:
                raise ValueError('Unconfirmed fast-forward update; inspect without retry')
            readback = {}
            for path, data in sorted(self.bundle.files.items()):
                result = self._call('fetch_file', repository_full_name=REPO, path=path,
                    ref=candidate, encoding='base64')
                if result.get('sha') != changes[path] or result.get('encoding') != 'base64':
                    raise ValueError('Immutable readback blob/encoding differs')
                encoded = result['content'].replace('\r', '').replace('\n', '')
                if len(encoded) != 4 * ((len(data) + 2) // 3):
                    raise ValueError('Immutable readback encoded byte length differs')
                raw = base64.b64decode(encoded, validate=True)
                if raw != data or git_object('blob', raw) != changes[path]:
                    raise ValueError('Immutable readback exact stored bytes differ')
                readback[path] = raw
            originals = restore_original_files(readback,
                expected_manifest_sha256=self.freeze['manifest_sha256'])
            if self._head() != candidate:
                raise ValueError('Post-publication head differs; inspect without retry')
            self.receipt = {'schema': SCHEMA, 'bundle_sha256': self.bundle.sha256,
                'parent': parent, 'parent_tree': parent_tree, 'commit': candidate, 'tree': tree,
                'file_count': len(changes), 'stored_bytes': sum(map(len, self.bundle.files.values())),
                'files': changes, 'immutable_bytes_read_back': True, 'exact_tree_delta_verified': True,
                'original_files_reconstructed': len(originals), 'transport_blob_limit_bytes': MAX_BLOB_BYTES,
                'force': False, 'single_atomic_commit': True, 'automatic_retry': False,
                'execution_restart_authorized': False, 'scientific_admission_authorized': False,
                'remote_event_store_qualified': False, 'usage': self.usage()}
            return self.receipt
        except BaseException as error:
            self.stopped = True
            self.receipt = {'candidate': candidate, 'error': repr(error),
                'update_may_have_landed': self.update_attempted, 'automatic_retry': False,
                'execution_restart_authorized': False, 'scientific_admission_authorized': False,
                'usage': self.usage()}
            raise Stopped('Archive publication stopped without retry: ' + str(error)) from error

    def usage(self):
        return {'calls': self.calls, 'request_bytes': self.request_bytes,
            'response_bytes': self.response_bytes, 'response_charged_bytes': self.response_charged_bytes,
            'unknown_response_bytes': self.unknown_response_bytes,
            'unknown_response_count': self.unknown_response_count,
            'elapsed_seconds': self.clock() - self.started}
