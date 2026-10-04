"""Inert, injected GraphQL CAS mapping; no credentials or network implementation.

All observations in this module are supplied by callers. A successful mapping
is preparation evidence only. Extra false-authority fields deliberately prevent
its receipt from satisfying ScientificGitStore's exact production CAS schema.
The declared commit tree is bound, but complete tree membership/delta, authentic
service conflict behavior, runtime and resource qualification remain external.
"""
import copy
import hashlib
import json
import re

REPOSITORY = 'andersenmartin-blip/setisearch'
REPOSITORY_ID = 'R_kgDOT558WQ'
BRANCH = 'm43-support-qualification'
NAMESPACE = 'radio-hosted-cas-preparation-20261004a'
PATH = 'results_radio_hosted_cas_preparation_20261004a/candidate.json'
QUERY = 'mutation($input:UpdateRefsInput!){updateRefs(input:$input){clientMutationId}}'
OPERATION = 'atomic_ref_compare_and_swap'
WITNESS_FIELDS = {'repository', 'commit', 'tree', 'parents', 'path', 'mode',
                  'blob', 'data', 'raw_commit'}
PARAM_FIELDS = {'repository', 'branch', 'expected_revision', 'candidate',
                'qualification_sha256'}
FALSE_AUTHORITY = {
    'actual_service_qualified': False, 'scientific_execution_authorized': False,
    'scientific_allocation_authorized': False, 'reservation_authorized': False,
    'restart_authorized': False, 'transport_integration_qualified': False,
    'tree_delta_qualified': False,
}


def _sha(value, length):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % length, value):
        raise ValueError('Canonical lowercase hexadecimal identity required')
    return value


def _canonical(value):
    def encode(item):
        if isinstance(item, bytes):
            return {'raw_bytes_hex': item.hex()}
        raise TypeError('Only JSON fields and raw bytes permitted')
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False, default=encode).encode()


def witness_sha256(witness):
    """Pin complete declared witness fields, including original raw bytes."""
    return hashlib.sha256(_canonical(witness)).hexdigest()


def _git_object(kind, raw):
    return hashlib.sha1(kind.encode() + b' ' + str(len(raw)).encode()
                        + b'\0' + raw).hexdigest()


def _validate_witness(witness, expected, candidate):
    if not isinstance(witness, dict) or set(witness) != WITNESS_FIELDS:
        raise ValueError('Exact pre-created immutable witness fields required')
    if (witness['repository'] != REPOSITORY or witness['commit'] != candidate
            or witness['parents'] != [expected] or witness['path'] != PATH
            or witness['mode'] != '100644'):
        raise ValueError('Candidate location, sole expected parent or mode differs')
    _sha(witness['tree'], 40); _sha(witness['blob'], 40)
    raw = witness['raw_commit']; data = witness['data']
    if (not isinstance(raw, bytes) or not isinstance(data, bytes)
            or not 1 <= len(raw) <= 65536 or len(data) > 65536):
        raise ValueError('Bounded complete raw commit/blob bytes required')
    if _git_object('commit', raw) != candidate or _git_object('blob', data) != witness['blob']:
        raise ValueError('Intrinsic immutable commit or blob identity differs')
    headers = raw.split(b'\n\n', 1)[0].split(b'\n')
    trees = [line[5:].decode('ascii') for line in headers if line.startswith(b'tree ')]
    parents = [line[7:].decode('ascii') for line in headers if line.startswith(b'parent ')]
    if (b'\n\n' not in raw or trees != [witness['tree']] or parents != [expected]
            or sum(line.startswith(b'author ') for line in headers) != 1
            or sum(line.startswith(b'committer ') for line in headers) != 1):
        raise ValueError('Original commit sole parent, tree or headers differ')


class HostedCASPreparation:
    """One disposable adapter attempt; injected callbacks only, never retry.

    transport(request) returns GraphQL-shaped JSON. read_ref(request) returns
    repository/branch/commit. read_candidate(request) returns the complete raw
    witness. Their supplied responses are not authentic-service certificates.
    qualification_sha256 pins only caller input syntax/value, not qualification.
    """
    def __init__(self, transport, read_ref, read_candidate, *, candidate_witness,
                 witness_pin, qualification_sha256):
        self._transport = transport
        self._read_ref = read_ref
        self._read_candidate = read_candidate
        self._source = candidate_witness
        self._witness = copy.deepcopy(candidate_witness)
        self._pin = _sha(witness_pin, 64)
        self._qualification = _sha(qualification_sha256, 64)
        if witness_sha256(self._witness) != self._pin:
            raise ValueError('Independent witness pin differs')
        self.attempted = False
        self.mutation_attempted = False
        self.calls = 0
        self.result = None

    def __call__(self, method, params):
        return self.invoke(method, params)

    def invoke(self, method, params):
        if self.attempted:
            raise RuntimeError('Adapter identity already spent; no retry or resume')
        self.attempted = True  # Precheck failures also spend this instance.
        try:
            if method != OPERATION or not isinstance(params, dict) or set(params) != PARAM_FIELDS:
                raise ValueError('Only the exact scientific callback-shape operation permitted')
            frozen = copy.deepcopy(params)
            binding = witness_sha256(frozen)
            if frozen['repository'] != REPOSITORY or frozen['branch'] != BRANCH:
                raise ValueError('Fixed repository and branch required')
            expected = _sha(frozen['expected_revision'], 40)
            candidate = _sha(frozen['candidate'], 40)
            if expected == candidate or _sha(frozen['qualification_sha256'], 64) != self._qualification:
                raise ValueError('Distinct candidate and pinned qualification input required')
            _validate_witness(self._witness, expected, candidate)

            def unchanged():
                if (witness_sha256(self._source) != self._pin
                        or witness_sha256(params) != binding):
                    raise ValueError('Pinned caller source fields changed during attempt')

            def call(callback, request):
                unchanged()
                sent = copy.deepcopy(request)
                self.calls += 1
                answer = callback(sent)
                unchanged()
                if sent != request:
                    raise ValueError('Injected callback changed its fixed request')
                return copy.deepcopy(answer)

            def head():
                got = call(self._read_ref, {'repository': REPOSITORY, 'branch': BRANCH})
                if (not isinstance(got, dict) or set(got) != {'repository', 'branch', 'commit'}
                        or got['repository'] != REPOSITORY or got['branch'] != BRANCH):
                    raise ValueError('Exact branch readback location required')
                return _sha(got['commit'], 40)

            def immutable():
                got = call(self._read_candidate, {'repository': REPOSITORY,
                           'commit': candidate, 'path': PATH})
                _validate_witness(got, expected, candidate)
                if witness_sha256(got) != self._pin or got != self._witness:
                    raise ValueError('Complete immutable candidate readback differs')

            if head() != expected:
                raise ValueError('Current branch differs from exact expected revision')
            immutable()  # Independently readable candidate precedes mutation.
            request = {'query': QUERY, 'variables': {'input': {
                'repositoryId': REPOSITORY_ID,
                'refUpdates': [{'name': 'refs/heads/' + BRANCH, 'beforeOid': expected,
                                'afterOid': candidate, 'force': False}],
                'clientMutationId': NAMESPACE}}}
            self.mutation_attempted = True  # Ambiguous exceptions never retry.
            answer = call(self._transport, request)
            required_ack = {'data': {'updateRefs': {'clientMutationId': NAMESPACE}}}
            if answer != required_ack:
                raise ValueError('Missing, erroneous or ambiguous exact GraphQL acknowledgement')
            immutable()
            if head() != candidate:
                raise ValueError('Post-CAS branch differs; mutation may have landed')
            unchanged()
            self.result = {
                'schema': 'radio-hosted-cas-preparation-v1',
                'domain': 'synthetic-test-fixture', 'status': 'PREPARATION_MAPPING_ONLY',
                'namespace': NAMESPACE, 'repository': REPOSITORY, 'branch': BRANCH,
                'expected_revision': expected, 'commit': candidate,
                'atomic': True, 'accepted': True,
                'qualification_sha256': self._qualification,
                'immutable_bytes_read_back': True, 'engineering_only': True,
                'preparation_only': True, 'automatic_retry': False, **FALSE_AUTHORITY,
            }
            return copy.deepcopy(self.result)
        except BaseException as error:
            self.result = {
                'schema': 'radio-hosted-cas-preparation-v1',
                'domain': 'synthetic-test-fixture', 'status': 'CLOSED_FAILED',
                'namespace': NAMESPACE, 'engineering_only': True, 'preparation_only': True,
                'error_type': type(error).__name__, 'attempt_spent': True,
                'mutation_may_have_landed': self.mutation_attempted,
                'automatic_retry': False, **FALSE_AUTHORITY,
            }
            raise
