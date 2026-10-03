"""Detached prospective scientific executable authentication, never activation.

This module reads nothing on import. Every trust anchor is a mandatory,
independently supplied raw pin, inventory, dependency graph or runtime identity.
The optional readers are injected; this module does not discover files, invoke
Git, inspect an ELF, import a plugin, acquire source rows or start an execution.
Structural closure verification is relative to the supplied complete inventory;
the independent producer of that inventory must qualify actual ELF/plugin law.
"""
from dataclasses import dataclass
import hashlib
import json
import re

SCHEMA = 'radio-scientific-prospective-executable-freeze-v1'
MODE = 'PROSPECTIVE_SCIENTIFIC_ONLY'
ROLES = ('code', 'input', 'runtime', 'elf', 'plugin')
_VERIFICATION_TOKEN = object()
MIB = 1024 ** 2
LIMITS = {'calibration': {'count': 127, 'milliseconds': 40000, 'artifact_bytes': 4*MIB},
          'evaluation': {'count': 24, 'milliseconds': 80000, 'artifact_bytes': 18*MIB},
          'overhead_milliseconds': 200000, 'ledger_bytes': 8*MIB,
          'failure_and_summary_bytes': 76*MIB, 'total_milliseconds': 7200000,
          'total_evidence_bytes': 1024**3, 'rss_bytes': 512*MIB,
          'modelled_array_bytes': 256*MIB}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii') + b'\n'


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256(value, label='SHA256'):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Invalid '+label)
    return value


def git_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('Invalid immutable Git identity')
    return value


def safe_path(value, *, absolute=False):
    if (not isinstance(value, str) or not value or len(value) > 4096 or '\\' in value or
            any(ord(c) < 32 for c in value) or value.startswith('/') != absolute or
            any(p in ('', '.', '..') for p in value.split('/')[1 if absolute else 0:])):
        raise ValueError('Unsafe pinned file location')
    return value


def load_raw(raw, expected_pin, *, cap=8*MIB):
    if (not isinstance(raw, bytes) or not isinstance(expected_pin, dict) or
            set(expected_pin) != {'bytes', 'sha256'} or type(expected_pin['bytes']) is not int or
            not 0 < expected_pin['bytes'] <= cap or len(raw) != expected_pin['bytes'] or
            hashlib.sha256(raw).hexdigest() != sha256(expected_pin['sha256'])):
        raise ValueError('Raw document differs from independent bounded pin')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError('Invalid pinned JSON') from error
    if not isinstance(value, dict) or canonical(value) != raw:
        raise ValueError('Canonical JSON object with one terminal LF required')
    return value


def validate_inventory(inventory):
    if not isinstance(inventory, dict) or not 0 < len(inventory) <= 100000:
        raise ValueError('Complete independent file inventory required')
    found = {role: [] for role in ROLES}
    locations = set()
    for identity, row in inventory.items():
        if not isinstance(identity, str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,200}', identity):
            raise ValueError('Plain distinct file identity required')
        if (not isinstance(row, dict) or set(row) != {'role', 'location', 'path', 'mode', 'bytes', 'sha256'} or
                row['role'] not in ROLES or row['location'] not in ('repository', 'runtime') or
                row['mode'] not in ('100644', '100755') or type(row['bytes']) is not int or not 0 <= row['bytes'] <= 2**40):
            raise ValueError('Exact ordinary file role, mode and location required')
        if row['role'] in ('code', 'input') and row['location'] != 'repository':
            raise ValueError('Code/input must have immutable repository provenance')
        if row['role'] in ('runtime', 'elf', 'plugin') and row['location'] != 'runtime':
            raise ValueError('Runtime/native/plugin location differs')
        safe_path(row['path'], absolute=row['location'] == 'runtime')
        sha256(row['sha256'])
        location = (row['location'], row['path'])
        if location in locations:
            raise ValueError('Aliased file location cannot claim two closure identities')
        locations.add(location)
        found[row['role']].append(identity)
    if any(not ids for ids in found.values()):
        raise ValueError('Code, input, runtime, ELF and plugin inventories all required')
    return {role: sorted(ids) for role, ids in found.items()}


def validate_edges(edges, inventory):
    native = {key for key, row in inventory.items() if row['role'] in ('elf', 'plugin')}
    if not isinstance(edges, dict) or set(edges) != native:
        raise ValueError('Complete ELF/plugin dependency graph required')
    for identity, dependencies in edges.items():
        if (not isinstance(dependencies, list) or dependencies != sorted(set(dependencies)) or
                any(key not in native or key == identity for key in dependencies)):
            raise ValueError('Unresolved, duplicate or unordered native dependency')
        if inventory[identity]['role'] == 'plugin' and not dependencies:
            raise ValueError('Plugin must bind its independently identified ELF dependencies')
    # Every dependency is present, including terminal nodes with an empty list.
    return edges


@dataclass(frozen=True, init=False)
class VerifiedFreeze:
    _raw: bytes

    def __init__(self, raw, *, _token=None):
        if _token is not _VERIFICATION_TOKEN:
            raise ValueError('Runtime verification result must come from the maintained verifier')
        object.__setattr__(self, '_raw', bytes(raw))

    @property
    def payload(self):
        return self._raw

    def record(self):
        return json.loads(self._raw)


class ProspectiveFreeze:
    """Authenticate a complete prospective freeze against external trust anchors."""
    _schema = SCHEMA
    _mode = MODE
    _actual = False

    def __init__(self, raw, expected_raw_pin, *, expected_inventory,
                 expected_dependency_edges, expected_runtime_identity):
        doc = load_raw(raw, expected_raw_pin)
        fields = {'schema', 'mode', 'status', 'inventory', 'role_inventories',
                  'dependency_edges', 'runtime_identity', 'limits',
                  'source_contract_sha256', 'trial_protocol_sha256',
                  'codec_certificate_sha256', 'scientific_execution_authorized',
                  'scientific_allocation_charged'}
        if self._actual:
            fields.add('domain')
        if (set(doc) != fields or doc['schema'] != self._schema or doc['mode'] != self._mode or
                doc['status'] != ('QUALIFIED' if self._actual else 'PENDING') or
                doc['scientific_execution_authorized'] is not False or
                doc['scientific_allocation_charged'] is not False or doc['limits'] != LIMITS or
                (self._actual and doc['domain'] not in ('public-scientific-evidence', 'synthetic-test-fixture'))):
            raise ValueError('Freeze mode, status, limits or authority differs')
        roles = validate_inventory(expected_inventory)
        validate_edges(expected_dependency_edges, expected_inventory)
        if (doc['inventory'] != expected_inventory or doc['role_inventories'] != roles or
                doc['dependency_edges'] != expected_dependency_edges or
                not isinstance(expected_runtime_identity, dict) or not expected_runtime_identity or
                doc['runtime_identity'] != expected_runtime_identity):
            raise ValueError('Freeze differs from complete independent closure or runtime')
        if self._actual:
            names = {'python', 'numpy', 'h5py', 'hdf5', 'hdf5plugin', 'python_executable_sha256'}
            if (set(expected_runtime_identity) != names or
                    any(not isinstance(expected_runtime_identity[name], str) or
                        not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}', expected_runtime_identity[name])
                        for name in names-{'python_executable_sha256'})):
                raise ValueError('Actual scientific Python/NumPy/HDF5/plugin runtime identity required')
            executable = sha256(expected_runtime_identity['python_executable_sha256'])
            if not any(row['role'] == 'runtime' and row['mode'] == '100755' and row['sha256'] == executable
                       for row in expected_inventory.values()):
                raise ValueError('Independently pinned executable must occur in complete runtime closure')
        for key in ('source_contract_sha256', 'trial_protocol_sha256', 'codec_certificate_sha256'):
            sha256(doc[key], key)
        self._raw = bytes(raw)
        self._pin = dict(expected_raw_pin)
        self._doc = doc

    @property
    def expected_sha256(self):
        return self._pin['sha256']

    def verify(self, *, read_file, published_commit, published_tree, read_published_file,
               expected_source_contract_sha256, expected_trial_protocol_sha256,
               expected_codec_certificate_sha256, runtime_identity):
        """Readbacks are untrusted callback results, never self-derived expected pins.

        read_file(location,path) returns {mode,bytes,data}; repository readback
        (commit,path) returns {commit,tree,path,mode,bytes,data,blob,commit_raw,
        tree_chain}. Original commit and complete nonrecursive tree-chain bytes
        authenticate membership in the independently expected Git root. Native
        ELF closure has already been independently
        supplied; this pure verifier neither executes nor rediscovers it.
        """
        git_sha(published_commit); git_sha(published_tree)
        doc = self._doc
        if doc['runtime_identity'] != runtime_identity:
            raise ValueError('Current runtime identity changed')
        for name, expected in (('source_contract_sha256', expected_source_contract_sha256),
                               ('trial_protocol_sha256', expected_trial_protocol_sha256),
                               ('codec_certificate_sha256', expected_codec_certificate_sha256)):
            if doc[name] != sha256(expected, name):
                raise ValueError('Independent source/protocol/codec provenance differs')
        published = 0
        for identity, row in sorted(doc['inventory'].items()):
            got = read_file(row['location'], row['path'])
            self._bytes(got, row)
            if row['location'] == 'repository':
                got = read_published_file(published_commit, row['path'])
                if (not isinstance(got, dict) or set(got) != {'commit', 'tree', 'path', 'mode', 'bytes', 'data', 'blob', 'commit_raw', 'tree_chain'} or
                        got['commit'] != published_commit or got['tree'] != published_tree or got['path'] != row['path']):
                    raise ValueError('Immutable source publication location differs')
                self._bytes({k: got[k] for k in ('mode', 'bytes', 'data')}, row)
                data = got['data']
                expected_blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                if got['blob'] != expected_blob:
                    raise ValueError('Immutable source Git blob differs')
                self._publication_membership(got, row, published_commit, published_tree)
                published += 1
        domain = doc.get('domain', 'prospective-component')
        record = {'schema': 'radio-scientific-freeze-verification-v1',
                  'status': 'QUALIFIED' if self._actual else 'PENDING',
                  'domain': domain, 'freeze_sha256': self.expected_sha256,
                  'published_commit': published_commit, 'published_tree': published_tree,
                  'published_files': published, 'closure_files': len(doc['inventory']),
                  'independent_pins_authenticated': True, 'pins_authenticated': True,
                  'actual_elf_inspection_performed': False,
                  'scientific_execution_authorized': self._actual and domain == 'public-scientific-evidence',
                  'scientific_allocation_charged': False}
        return VerifiedFreeze(canonical(record), _token=_VERIFICATION_TOKEN)

    @staticmethod
    def _bytes(got, row):
        if (not isinstance(got, dict) or set(got) != {'mode', 'bytes', 'data'} or
                got['mode'] != row['mode'] or type(got['bytes']) is not int or got['bytes'] != row['bytes'] or
                not isinstance(got['data'], bytes) or len(got['data']) != row['bytes'] or
                hashlib.sha256(got['data']).hexdigest() != row['sha256']):
            raise ValueError('File bytes, ordinary mode or independent pin differs')

    @staticmethod
    def _publication_membership(got, row, commit, tree):
        raw = got['commit_raw']
        if (not isinstance(raw, bytes) or len(raw) > 65536 or
                hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != commit):
            raise ValueError('Immutable source raw commit differs')
        headers = raw.split(b'\n\n', 1)[0].split(b'\n')
        if [line for line in headers if line.startswith(b'tree ')] != [b'tree '+tree.encode()]:
            raise ValueError('Immutable source commit root tree differs')
        parts = row['path'].split('/')
        chain = got['tree_chain']
        if not isinstance(chain, list) or len(chain) != len(parts):
            raise ValueError('Complete immutable source path ancestry required')
        modes = {'040000': 'tree', '100644': 'blob', '100755': 'blob', '120000': 'blob', '160000': 'commit'}
        for ordinal, (name, doc) in enumerate(zip(parts, chain, strict=True)):
            if (not isinstance(doc, dict) or set(doc) != {'sha', 'truncated', 'tree'} or
                    doc['sha'] != tree or doc['truncated'] is not False or
                    not isinstance(doc['tree'], list) or len(doc['tree']) > 100000):
                raise ValueError('Complete immutable source tree required')
            entries = {}
            for entry in doc['tree']:
                if (not isinstance(entry, dict) or set(entry) != {'path', 'mode', 'type', 'sha'} or
                        entry['mode'] not in modes or modes[entry['mode']] != entry['type']):
                    raise ValueError('Immutable source tree mode/type differs')
                path = safe_path(entry['path'])
                if '/' in path or path in entries:
                    raise ValueError('Duplicate immutable source tree name')
                entries[path] = {'mode': entry['mode'], 'type': entry['type'], 'sha': git_sha(entry['sha'])}
            order = sorted(entries, key=lambda path: (path+('/' if entries[path]['type'] == 'tree' else '')).encode('utf-8'))
            body = b''.join(entries[path]['mode'].lstrip('0').encode()+b' '+path.encode('utf-8')+b'\0'+bytes.fromhex(entries[path]['sha']) for path in order)
            if hashlib.sha1(b'tree '+str(len(body)).encode()+b'\0'+body).hexdigest() != tree:
                raise ValueError('Immutable source tree raw content hash differs')
            entry = entries.get(name)
            expected = (row['mode'], 'blob') if ordinal == len(parts)-1 else ('040000', 'tree')
            if entry is None or (entry['mode'], entry['type']) != expected:
                raise ValueError('Immutable source path mode or location differs')
            tree = entry['sha']
        if tree != got['blob']:
            raise ValueError('Immutable source root membership differs from blob')


class ScientificFreeze(ProspectiveFreeze):
    """Production verifier for a *new* actual certificate, never a candidate.

    A successful actual record authenticates this executable/runtime component;
    it does not grant a source session or consumption lease. Full detached
    closure, irrevocable allocation and current session proofs are still needed.
    No actual certificate is manufactured by this class or its test fixtures.
    """
    _schema = 'radio-scientific-executable-freeze-v1'
    _mode = 'SCIENTIFIC_EXECUTABLE_ONLY'
    _actual = True
