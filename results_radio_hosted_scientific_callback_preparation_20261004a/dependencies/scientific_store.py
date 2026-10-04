"""Detached scientific phase accounting and injected immutable Git CAS adapter.

No connector, filesystem, randomness, source rows or repository import is used.
Simulation reports are explicitly non-authoritative. A production caller must
independently authenticate a service qualification for *atomic expected-revision
CAS*. An ordinary GitHub force=false fast-forward operation cannot substitute
for that primitive, even with head checks immediately before and after it.
"""
from dataclasses import dataclass
import hashlib
import json
import re
from scientific_runtime import (canonical, digest, load_raw, sha256, git_sha,
                                safe_path, LIMITS, MIB, VerifiedFreeze)

REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
STORE_SCHEMA = 'radio-scientific-git-store-v1'
LEDGER_SCHEMA = 'radio-scientific-phase-ledger-v1'
PROOF_SCHEMA = 'radio-scientific-current-admission-v1'
# 2026-10-10T00:00:00Z: no current-session permission after 9 October UTC.
STOP_EPOCH_MILLISECONDS = 1791590400000
DOMAINS = ('synthetic-test-fixture', 'public-scientific-evidence')
BINDINGS = {'case_identity', 'role', 'context_sha256', 'source_contract_sha256',
            'noise_law_sha256', 'plan_sha256'}
_ADMISSION_TOKEN = object()


class Stopped(RuntimeError):
    pass


@dataclass(frozen=True, init=False)
class VerifiedAdmission:
    _raw: bytes

    def __init__(self, raw, *, _token=None):
        if _token is not _ADMISSION_TOKEN:
            raise ValueError('Admission result must come from a maintained verifier or store')
        object.__setattr__(self, '_raw', bytes(raw))

    @property
    def payload(self):
        return self._raw

    def record(self):
        return json.loads(self._raw)


def validate_cases(cases, expected_cases):
    if (not isinstance(cases, list) or cases != expected_cases or len(cases) != 151 or
            [c.get('role') for c in cases] != ['calibration']*127+['evaluation']*24):
        raise ValueError('Complete independently pinned ordered 127/24 bindings required')
    seen = set()
    for row in cases:
        if not isinstance(row, dict) or set(row) != BINDINGS:
            raise ValueError('Exact scientific case binding required')
        for key in BINDINGS-{'role'}:
            sha256(row[key], key)
        if row['case_identity'] in seen:
            raise ValueError('Repeated case identity would permit a retry')
        seen.add(row['case_identity'])
    return cases


def phase_genesis(cases, expected_cases, *, domain='synthetic-test-fixture'):
    validate_cases(cases, expected_cases)
    if domain not in DOMAINS:
        raise ValueError('Explicit evidence domain required')
    return {'schema': LEDGER_SCHEMA, 'domain': domain, 'status': 'PENDING',
            'cases': json.loads(canonical(cases)), 'limits': json.loads(canonical(LIMITS)),
            'events': [], 'scientific_allocation_charged': False,
            'scientific_execution_authorized': False}


def validate_phase_ledger(document, expected_cases):
    fields = {'schema', 'domain', 'status', 'cases', 'limits', 'events',
              'scientific_allocation_charged', 'scientific_execution_authorized'}
    if (not isinstance(document, dict) or set(document) != fields or
            document['schema'] != LEDGER_SCHEMA or document['domain'] not in DOMAINS or
            document['status'] not in ('PENDING', 'ACTIVE') or document['limits'] != LIMITS or
            document['scientific_allocation_charged'] is not (document['status'] == 'ACTIVE') or
            (document['status'] == 'ACTIVE' and document['domain'] != 'public-scientific-evidence') or
            document['scientific_execution_authorized'] is not False):
        raise ValueError('Prospective ledger schema, protected limits or authority differs')
    validate_cases(document['cases'], expected_cases)
    if len(canonical(document)) > LIMITS['ledger_bytes']:
        raise ValueError('Protected 8 MiB ledger capacity exhausted')
    if not isinstance(document['events'], list):
        raise ValueError('Ordered phase events required')
    consumed = []
    active = None
    stopped = False
    overhead_time = overhead_bytes = 0
    overhead_ids = set()
    for ordinal, event in enumerate(document['events']):
        if not isinstance(event, dict) or event.get('ordinal') != ordinal or type(event.get('ordinal')) is not int:
            raise ValueError('Phase event order changed')
        kind = event.get('kind')
        if kind == 'overhead':
            if set(event) != {'ordinal', 'kind', 'identity', 'category', 'milliseconds', 'bytes', 'sha256'}:
                raise ValueError('Exact overhead event required')
            sha256(event['identity']); sha256(event['sha256'])
            if event['identity'] in overhead_ids or event['category'] not in ('setup', 'failure', 'summary', 'finalization'):
                raise ValueError('Repeated or unsupported overhead event; no retry')
            if any(type(event[k]) is not int or event[k] < 0 for k in ('milliseconds', 'bytes')):
                raise ValueError('Nonnegative measured overhead required')
            overhead_ids.add(event['identity'])
            overhead_time += event['milliseconds']; overhead_bytes += event['bytes']
            if overhead_time > 200000 or overhead_bytes > 76*MIB:
                raise ValueError('Protected overhead reservation exhausted')
            continue
        if stopped:
            raise ValueError('Failed phase is permanently closed; no refund, retry or continuation')
        if kind == 'consume':
            if set(event) != {'ordinal', 'kind', 'binding', 'milliseconds', 'artifact_bytes', 'attempt_identity'}:
                raise ValueError('Exact irreversible consumption required')
            if active is not None or len(consumed) >= 151 or event['binding'] != expected_cases[len(consumed)]:
                raise ValueError('Ordered fresh case required; prior case remains consumed')
            sha256(event['attempt_identity'])
            if any(c['attempt_identity'] == event['attempt_identity'] for c in consumed):
                raise ValueError('Attempt identity reuse prohibited')
            quota = LIMITS[event['binding']['role']]
            if (type(event['milliseconds']) is not int or event['milliseconds'] != quota['milliseconds'] or
                    type(event['artifact_bytes']) is not int or event['artifact_bytes'] != quota['artifact_bytes']):
                raise ValueError('Exact per-case phase reservation required; overhead cannot be borrowed')
            active = {'binding': event['binding'], 'attempt_identity': event['attempt_identity'],
                      'milliseconds': event['milliseconds'], 'artifact_bytes': event['artifact_bytes'],
                      'status': 'consumed', 'used_bytes': 0, 'artifacts': {}}
            consumed.append(active)
        elif kind == 'artifact':
            if (set(event) != {'ordinal', 'kind', 'attempt_identity', 'name', 'bytes', 'sha256', 'publication'} or
                    active is None or event['attempt_identity'] != active['attempt_identity']):
                raise ValueError('Artifact requires current irrevocably consumed attempt')
            name = event['name']
            if not isinstance(name, str) or not re.fullmatch('[A-Za-z0-9_.-]{1,160}', name) or name in ('.', '..'):
                raise ValueError('Plain artifact filename required')
            sha256(event['sha256'])
            if name in active['artifacts'] or type(event['bytes']) is not int or event['bytes'] < 0:
                raise ValueError('Repeated artifact or invalid byte charge')
            validate_publication(event['publication'], expected_sha256=event['sha256'])
            active['artifacts'][name] = event['bytes']; active['used_bytes'] += event['bytes']
            if active['used_bytes'] > active['artifact_bytes']:
                raise ValueError('Per-case artifact capacity exhausted')
        elif kind == 'finish':
            if (set(event) != {'ordinal', 'kind', 'attempt_identity', 'outcome', 'elapsed_milliseconds'} or
                    active is None or event['attempt_identity'] != active['attempt_identity'] or
                    event['outcome'] not in ('completed', 'failed') or
                    type(event['elapsed_milliseconds']) is not int or event['elapsed_milliseconds'] < 0):
                raise ValueError('Exact measured disposition for current attempt required')
            if event['outcome'] == 'completed' and event['elapsed_milliseconds'] > active['milliseconds']:
                raise ValueError('Over-time attempt cannot complete')
            active['status'] = event['outcome']
            active['elapsed_milliseconds'] = event['elapsed_milliseconds']
            stopped = event['outcome'] == 'failed'
            active = None
        else:
            raise ValueError('Unsupported event; no refund/reset/retry operation')
    milliseconds = sum(c['milliseconds'] for c in consumed)
    artifact_bytes = sum(c['artifact_bytes'] for c in consumed)
    if milliseconds > 7000000 or artifact_bytes > 940*MIB:
        raise ValueError('Case reservations invade protected overhead')
    return {'consumed_cases': len(consumed), 'cases': json.loads(canonical(consumed)),
            'reserved_case_milliseconds': milliseconds, 'reserved_case_artifact_bytes': artifact_bytes,
            'protected_overhead_milliseconds': 200000, 'protected_ledger_bytes': 8*MIB,
            'protected_summary_failure_bytes': 76*MIB, 'used_overhead_milliseconds': overhead_time,
            'used_summary_failure_bytes': overhead_bytes, 'attempt_failed': stopped,
            'active_attempt': None if active is None else active['attempt_identity'],
            'full_reservations_remain_charged': True,
            'scientific_allocation_charged': document['scientific_allocation_charged'],
            'scientific_execution_authorized': False}


def append_phase_event(raw, expected_raw_pin, event, *, expected_cases):
    before = load_raw(raw, expected_raw_pin)
    validate_phase_ledger(before, expected_cases)
    candidate = json.loads(canonical(before))
    candidate['events'].append(json.loads(canonical(event)))
    validate_phase_ledger(candidate, expected_cases)
    return canonical(candidate)


def validate_publication(value, *, expected_sha256):
    if (not isinstance(value, dict) or set(value) != {'repository', 'commit', 'tree', 'path', 'blob', 'sha256'} or
            value['repository'] != REPOSITORY or value['sha256'] != sha256(expected_sha256)):
        raise ValueError('Immutable publication provenance differs')
    for key in ('commit', 'tree', 'blob'):
        git_sha(value[key])
    safe_path(value['path'])
    return value


class ScientificGitStore:
    """Callback adapter with mandatory separately authenticated atomic CAS law.

    invoke receives fixed operation names and argument dictionaries. Reads and
    writes are not retried. Any partial/ambiguous failure stops this instance.
    The callback must provide *atomic_ref_compare_and_swap*; no update_ref API is
    present. The real service qualification remains an external prerequisite.
    """
    def __init__(self, invoke, raw_spec, expected_spec_pin, *, expected_location,
                 raw_cas_qualification, expected_cas_qualification_pin,
                 expected_manifest_sha256, execution_verifier):
        spec = load_raw(raw_spec, expected_spec_pin)
        fields = {'schema', 'domain', 'repository', 'branch', 'prefix', 'manifest_sha256',
                  'cas_qualification_sha256', 'max_calls', 'max_response_bytes'}
        if (set(spec) != fields or spec['schema'] != STORE_SCHEMA or spec['domain'] not in DOMAINS or
                spec['repository'] != REPOSITORY or spec['branch'] != BRANCH or
                {'repository': spec['repository'], 'branch': spec['branch'], 'prefix': spec['prefix']} != expected_location):
            raise ValueError('Independent scientific store mode or location differs')
        safe_path(spec['prefix'])
        if not spec['prefix'].startswith('results_radio_scientific_'):
            raise ValueError('Distinct scientific namespace required')
        if spec['manifest_sha256'] != sha256(expected_manifest_sha256):
            raise ValueError('Independently supplied execution manifest differs')
        if (type(spec['max_calls']) is not int or not 1 <= spec['max_calls'] <= 1500 or
                type(spec['max_response_bytes']) is not int or not 1 <= spec['max_response_bytes'] <= 1536*MIB):
            raise ValueError('Finite transport ceilings required')
        law = load_raw(raw_cas_qualification, expected_cas_qualification_pin)
        if (set(law) != {'schema', 'domain', 'repository', 'branch', 'atomic_expected_revision_cas',
                        'immutable_readback_required', 'no_retries', 'qualified'} or
                law['schema'] != 'radio-scientific-atomic-cas-qualification-v1' or
                law['domain'] != spec['domain'] or law['repository'] != REPOSITORY or law['branch'] != BRANCH or
                law['atomic_expected_revision_cas'] is not True or law['immutable_readback_required'] is not True or
                law['no_retries'] is not True or law['qualified'] is not True or
                spec['cas_qualification_sha256'] != expected_cas_qualification_pin['sha256']):
            raise ValueError('Independently qualified atomic CAS primitive required; fast-forward is insufficient')
        self._invoke = invoke; self._spec = spec; self._execution_verifier = execution_verifier
        self.calls = 0; self.response_bytes = 0; self.stopped = False; self.receipts = []

    def _call(self, method, **params):
        if self.stopped:
            raise Stopped('Store instance stopped; no retry or resume')
        if self.calls >= self._spec['max_calls']:
            self.stopped = True
            raise Stopped('Transport call capacity exhausted')
        self.calls += 1
        try:
            result = self._invoke(method, params)
            if not isinstance(result, dict):
                raise ValueError('Object callback result required')
            # Blob bodies use bytes; account the actual body plus metadata JSON.
            meta = {k: v for k, v in result.items() if k != 'data'}
            self.response_bytes += len(canonical(meta))
            if 'data' in result:
                if not isinstance(result['data'], bytes):
                    raise ValueError('Raw immutable blob bytes required')
                self.response_bytes += len(result['data'])
            if self.response_bytes > self._spec['max_response_bytes']:
                raise ValueError('Transport response capacity exhausted after callback; operation may have landed')
            return result
        except BaseException as error:
            self.stopped = True
            raise Stopped('Callback failed without retry; original charge retained: '+str(error)) from error

    def _head(self):
        got = self._call('read_ref', repository=REPOSITORY, branch=BRANCH)
        if set(got) != {'repository', 'branch', 'commit'} or got['repository'] != REPOSITORY or got['branch'] != BRANCH:
            raise ValueError('Current branch readback location changed')
        return git_sha(got['commit'])

    def _commit(self, sha):
        got = self._call('read_commit', repository=REPOSITORY, commit=git_sha(sha))
        if (set(got) != {'sha', 'data'} or got['sha'] != sha or not isinstance(got['data'], bytes) or
                len(got['data']) > 65536):
            raise ValueError('Bounded original Git commit bytes required')
        raw = got['data']
        actual = hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if actual != sha:
            raise ValueError('Git commit raw content hash differs')
        headers = raw.split(b'\n\n', 1)[0].split(b'\n')
        trees = [line[5:].decode('ascii') for line in headers if line.startswith(b'tree ')]
        parents = [line[7:].decode('ascii') for line in headers if line.startswith(b'parent ')]
        if len(trees) != 1 or not any(line.startswith(b'author ') for line in headers) or not any(line.startswith(b'committer ') for line in headers):
            raise ValueError('Git commit structure differs')
        return {'tree': git_sha(trees[0]), 'parents': [git_sha(p) for p in parents]}

    def _tree(self, sha):
        got = self._call('read_tree', repository=REPOSITORY, tree=git_sha(sha))
        if set(got) != {'sha', 'truncated', 'tree'} or got['sha'] != sha or got['truncated'] is not False or not isinstance(got['tree'], list):
            raise ValueError('Complete nonrecursive Git tree required')
        entries = {}
        modes = {'040000': 'tree', '100644': 'blob', '100755': 'blob', '120000': 'blob', '160000': 'commit'}
        for row in got['tree']:
            if (not isinstance(row, dict) or set(row) != {'path', 'mode', 'type', 'sha'} or
                    row['mode'] not in modes or modes[row['mode']] != row['type']):
                raise ValueError('Git tree entry mode/type differs')
            name = safe_path(row['path'])
            if '/' in name or name in entries:
                raise ValueError('Duplicate or nonlocal Git tree name')
            entries[name] = {'mode': row['mode'], 'type': row['type'], 'sha': git_sha(row['sha'])}
        order = sorted(entries, key=lambda name: (name+('/' if entries[name]['type'] == 'tree' else '')).encode('utf-8'))
        raw = b''.join(entries[name]['mode'].lstrip('0').encode()+b' '+name.encode('utf-8')+b'\0'+bytes.fromhex(entries[name]['sha']) for name in order)
        if hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != sha:
            raise ValueError('Git tree raw content hash differs')
        return entries

    def _delta(self, oldsha, newsha, path, blob, *, add_only=False):
        old = {} if oldsha is None else self._tree(oldsha)
        new = self._tree(newsha)
        first, separator, tail = path.partition('/')
        if {k: v for k, v in old.items() if k != first} != {k: v for k, v in new.items() if k != first}:
            raise ValueError('Candidate changed an undeclared path')
        if not separator:
            if add_only and first in old:
                raise ValueError('Fresh admission/genesis path already exists; no overwrite or rearm')
            if new.get(first) != {'mode': '100644', 'type': 'blob', 'sha': blob}:
                raise ValueError('Candidate declared file mode/blob differs')
        else:
            current = new.get(first); prior = old.get(first)
            if current is None or (current['mode'], current['type']) != ('040000', 'tree') or (prior and (prior['mode'], prior['type']) != ('040000', 'tree')):
                raise ValueError('Candidate ancestor mode differs')
            self._delta(None if prior is None else prior['sha'], current['sha'], tail, blob, add_only=add_only)

    def _read(self, commit, path, expected):
        got = self._call('read_immutable_file', repository=REPOSITORY, commit=git_sha(commit), path=safe_path(path))
        fields = {'repository', 'commit', 'tree', 'path', 'mode', 'blob', 'bytes', 'data'}
        if (set(got) != fields or got['repository'] != REPOSITORY or got['commit'] != commit or
                got['path'] != path or got['mode'] != '100644' or type(got['bytes']) is not int or
                got['bytes'] != len(expected) or got['data'] != expected):
            raise ValueError('Immutable publication bytes, location or mode changed')
        git_sha(got['tree'])
        blob = hashlib.sha1(b'blob '+str(len(expected)).encode()+b'\0'+expected).hexdigest()
        if got['blob'] != blob:
            raise ValueError('Immutable publication Git blob changed')
        return got

    def publish(self, *, expected_revision, relative_path, raw_document, expected_document_pin,
                execution_manifest, expected_execution_manifest_pin, attempt_identity):
        """Readback-only metadata publication; phase state requires its strict API."""
        doc = load_raw(raw_document, expected_document_pin)
        if doc.get('schema') == LEDGER_SCHEMA:
            raise ValueError('Phase state requires the append-only checkpoint API')
        return self._publish(expected_revision=expected_revision, relative_path=relative_path,
                             raw_document=raw_document, expected_document_pin=expected_document_pin,
                             execution_manifest=execution_manifest,
                             expected_execution_manifest_pin=expected_execution_manifest_pin,
                             attempt_identity=attempt_identity)

    def publish_phase_genesis(self, *, expected_cases, **publication):
        doc = load_raw(publication['raw_document'], publication['expected_document_pin'])
        validate_phase_ledger(doc, expected_cases)
        if doc['domain'] != self._spec['domain']:
            raise ValueError('Phase ledger domain differs from independently qualified store')
        if doc['events']:
            raise ValueError('Fresh phase genesis must contain no prior events')
        return self._publish(**publication, add_only=True)

    def publish_phase_checkpoint(self, *, previous_raw, previous_pin, expected_cases, **publication):
        """Authenticate original immutable bytes and exactly one new phase event.

        New cases become irrevocably reserved only after accepted CAS and exact
        readback. A partial/ambiguous write closes the adapter; it cannot refund,
        rebase or reconstruct an execution lease from either checkpoint.
        """
        before = load_raw(previous_raw, previous_pin)
        after = load_raw(publication['raw_document'], publication['expected_document_pin'])
        validate_phase_ledger(before, expected_cases); validate_phase_ledger(after, expected_cases)
        if after['domain'] != self._spec['domain']:
            raise ValueError('Phase ledger domain differs from independently qualified store')
        if ({**after, 'events': before['events']} != before or
                len(after['events']) != len(before['events'])+1 or after['events'][:-1] != before['events']):
            raise ValueError('Scientific phase store is strictly append-only; no reset/refund/retry')
        path = self._spec['prefix']+'/'+safe_path(publication['relative_path'])
        try:
            self._read(publication['expected_revision'], path, previous_raw)
            return self._publish(**publication)
        except BaseException:
            self.stopped = True
            raise

    def _publish(self, *, expected_revision, relative_path, raw_document, expected_document_pin,
                 execution_manifest, expected_execution_manifest_pin, attempt_identity, add_only=False):
        """One exact-parent admission/checkpoint publication, never a retry.

        Callback create_candidate must return an independently readable exact
        parent commit and a delta containing only this declared ordinary file.
        CAS conflict stops without attempting to use a different branch parent.
        """
        if self.stopped:
            raise Stopped('Store instance stopped; no retry or resume')
        candidate = None
        try:
            git_sha(expected_revision); sha256(attempt_identity)
            doc = load_raw(raw_document, expected_document_pin)
            manifest = load_raw(execution_manifest, expected_execution_manifest_pin)
            if expected_execution_manifest_pin['sha256'] != self._spec['manifest_sha256']:
                raise ValueError('Execution manifest raw pin differs from store binding')
            verified = self._execution_verifier(manifest)
            if type(verified) is not VerifiedFreeze:
                raise ValueError('Immutable externally verified execution result required')
            verification = verified.record()
            if (verification.get('schema') != 'radio-scientific-freeze-verification-v1' or
                    verification.get('status') != 'QUALIFIED' or
                    verification.get('freeze_sha256') != expected_execution_manifest_pin['sha256'] or
                    verification.get('domain') != self._spec['domain'] or
                    verification.get('pins_authenticated') is not True or
                    verification.get('independent_pins_authenticated') is not True):
                raise ValueError('Execution verification provenance differs')
            git_sha(verification.get('published_commit')); git_sha(verification.get('published_tree'))
            if (type(verification.get('published_files')) is not int or verification['published_files'] < 2 or
                    type(verification.get('closure_files')) is not int or verification['closure_files'] < 5):
                raise ValueError('Complete runtime closure and immutable source publication required')
            if self._spec['domain'] == 'public-scientific-evidence' and verification.get('scientific_execution_authorized') is not True:
                raise ValueError('Actual scientific runtime qualification required')
            path = self._spec['prefix']+'/'+safe_path(relative_path)
            if self._head() != expected_revision:
                raise ValueError('Fresh expected branch revision differs')
            made = self._call('create_candidate', repository=REPOSITORY, parent=expected_revision,
                              files=[{'path': path, 'mode': '100644', 'data': raw_document}],
                              attempt_identity=attempt_identity)
            if set(made) != {'commit', 'tree'}:
                raise ValueError('Exact candidate identities required')
            candidate = git_sha(made['commit']); tree = git_sha(made['tree'])
            blob = hashlib.sha1(b'blob '+str(len(raw_document)).encode()+b'\0'+raw_document).hexdigest()
            before = self._commit(expected_revision)
            if self._commit(candidate) != {'tree': tree, 'parents': [expected_revision]}:
                raise ValueError('Candidate exact parent/tree differs')
            self._delta(before['tree'], tree, path, blob, add_only=add_only)
            cas = self._call('atomic_ref_compare_and_swap', repository=REPOSITORY, branch=BRANCH,
                             expected_revision=expected_revision, candidate=candidate,
                             qualification_sha256=self._spec['cas_qualification_sha256'])
            if cas != {'repository': REPOSITORY, 'branch': BRANCH, 'expected_revision': expected_revision,
                       'commit': candidate, 'atomic': True, 'accepted': True}:
                raise ValueError('Atomic CAS rejected or acknowledgement differs; no retry')
            immutable = self._read(candidate, path, raw_document)
            if immutable['tree'] != tree or self._head() != candidate:
                raise ValueError('Immutable tree or post-CAS head differs; publication may have landed')
            receipt = {'schema': 'radio-scientific-store-publication-v1', 'domain': self._spec['domain'],
                       'status': 'SIMULATION_ONLY' if self._spec['domain'] == 'synthetic-test-fixture' else 'READBACK_VERIFIED',
                       'repository': REPOSITORY, 'branch': BRANCH, 'parent': expected_revision,
                       'commit': candidate, 'tree': tree, 'path': path, 'blob': blob,
                       'sha256': expected_document_pin['sha256'], 'attempt_identity': attempt_identity,
                       'atomic_expected_revision_cas': True, 'immutable_bytes_read_back': True,
                       'automatic_retry': False, 'scientific_execution_authorized': False,
                       'scientific_allocation_charged': False}
            self.receipts.append(receipt)
            return VerifiedAdmission(canonical(receipt), _token=_ADMISSION_TOKEN)
        except BaseException as error:
            self.stopped = True
            self.receipts.append({'candidate': candidate, 'failure': str(error),
                                  'publication_may_have_landed': candidate is not None,
                                  'original_charges_retained': True, 'automatic_retry': False,
                                  'scientific_execution_authorized': False})
            raise


def validate_current_admission(raw_proof_bytes, expected_raw_pin, *, verified_closure,
                               expected_basis, raw_store_acknowledgement,
                               expected_store_acknowledgement_pin, raw_session_proof,
                               expected_session_proof_pin, expected_row_receipt_pins,
                               expected_current_session, raw_cas_qualification,
                               expected_cas_qualification_pin):
    """Authenticate a genuine current proof or an explicitly synthetic fixture.

    ACTIVE is derived from separately pinned closure, irrevocable store CAS ack,
    bounded live session metadata and exact independent row receipt pins. A
    candidate codec certificate or a caller's boolean cannot replace the closure.
    This verifier never performs an acquisition, reads a row, or creates a lease.
    """
    proof = load_raw(raw_proof_bytes, expected_raw_pin)
    ack = load_raw(raw_store_acknowledgement, expected_store_acknowledgement_pin)
    session = load_raw(raw_session_proof, expected_session_proof_pin)
    cas_law = load_raw(raw_cas_qualification, expected_cas_qualification_pin)
    from scientific_admission import VerifiedClosure, digest as closure_digest
    if not isinstance(verified_closure, VerifiedClosure):
        raise ValueError('Authenticated immutable scientific closure required')
    closure = verified_closure.record()
    fields = {'schema', 'domain', 'status', 'closure_sha256', 'basis_sha256', 'role',
              'context_sha256', 'receiver_bank_sha256', 'window_identity',
              'source_inventory_sha256', 'source_contract_sha256', 'runtime_identity_sha256',
              'trial_protocol_sha256', 'scientific_allocation_sha256', 'trial_allocation_sha256',
              'trial_case_identity',
              'acquisition_ledger_revision', 'acquisition_ledger_sha256',
              'store_acknowledgement_sha256', 'session_proof_sha256', 'session_identity',
              'row_receipt_pins', 'irrevocable', 'refund_or_retry_allowed'}
    if (set(proof) != fields or proof['schema'] != PROOF_SCHEMA or proof['domain'] not in DOMAINS or
            proof['status'] != ('ACTIVE' if proof['domain'] == 'public-scientific-evidence' else 'PENDING') or
            proof['irrevocable'] is not True or proof['refund_or_retry_allowed'] is not False):
        raise ValueError('Fresh admission domain, state or irreversible law differs')
    domain = proof['domain']
    if (set(cas_law) != {'schema', 'domain', 'repository', 'branch', 'atomic_expected_revision_cas',
                        'immutable_readback_required', 'no_retries', 'qualified'} or
            cas_law['schema'] != 'radio-scientific-atomic-cas-qualification-v1' or
            cas_law['domain'] != domain or cas_law['repository'] != REPOSITORY or cas_law['branch'] != BRANCH or
            cas_law['atomic_expected_revision_cas'] is not True or cas_law['immutable_readback_required'] is not True or
            cas_law['no_retries'] is not True or cas_law['qualified'] is not True):
        raise ValueError('Independent actual atomic CAS service law required')
    # A final closure authenticates actual evidence without granting a lease.
    if (closure.get('evidence_domain') != domain or closure.get('basis') != expected_basis or
            closure.get('evidence_closure_verified') is not True or
            closure.get('scientific_readiness') is not (domain == 'public-scientific-evidence')):
        raise ValueError('Complete independently authenticated scientific closure required')
    if (proof['closure_sha256'] != hashlib.sha256(verified_closure.payload).hexdigest() or
            proof['basis_sha256'] != closure['basis_sha256'] or
            closure['basis_sha256'] != closure_digest(expected_basis)):
        raise ValueError('Admission closure or basis binding differs')
    role = proof['role']
    if role not in ('calibration', 'validation', 'pilot'):
        raise ValueError('Admitted source role differs')
    if domain == 'public-scientific-evidence' and role != 'pilot':
        raise ValueError('This completed scientific closure admits the fixed pilot only')
    if proof['trial_case_identity'] != sha256(closure.get('trial_case_identity')):
        raise ValueError('Irrevocable fresh pilot trial identity differs')
    sessions = closure.get('acquisition_session_bindings')
    if not isinstance(sessions, list):
        raise ValueError('Authenticated acquisition session reservation required')
    reserved = [row for row in sessions if row.get('role') == role]
    if len(reserved) != 1 or reserved[0]['session_id'] != proof['session_identity']:
        raise ValueError('Current session absent from irrevocable acquisition ledger')
    reservation = reserved[0]
    if role == 'pilot' and proof['session_identity'] != closure.get('trial_session_identity'):
        raise ValueError('Current pilot session differs from fresh trial allocation')
    for field, values in (('context_sha256', 'receiver_context_sha256s'),
                          ('receiver_bank_sha256', 'receiver_bank_sha256s'),
                          ('window_identity', 'window_identities')):
        expected = (closure.get('pilot_receiver_context_sha256')
                    if field == 'context_sha256' and role == 'pilot'
                    else expected_basis.get(values, {}).get(role))
        if proof[field] != sha256(expected, 'independent source role binding'):
            raise ValueError('Source role/context/window/receiver bank differs')
    if proof['source_inventory_sha256'] != expected_basis['source_inventory_sha256']:
        raise ValueError('Original source inventory provenance differs')
    binding = {'source_contract_sha256': 'new_executable_source_contract_sha256',
               'trial_protocol_sha256': 'trial_protocol_sha256',
               'trial_allocation_sha256': 'trial_allocation_sha256',
               'acquisition_ledger_sha256': 'acquisition_ledger_sha256'}
    for field, closure_field in binding.items():
        if proof[field] != sha256(closure.get(closure_field), closure_field):
            raise ValueError('Scientific runtime/protocol/allocation/ledger binding differs')
    if (proof['runtime_identity_sha256'] != digest(closure.get('runtime_identity')) or
            proof['scientific_allocation_sha256'] != sha256(closure.get('document_sha256s', {}).get('scientific_allocation'))):
        raise ValueError('Runtime identity or scientific allocation binding differs')
    git_sha(proof['acquisition_ledger_revision'])
    if proof['acquisition_ledger_revision'] != closure.get('acquisition_ledger_revision'):
        raise ValueError('Acquisition ledger immutable revision differs')
    if (proof['store_acknowledgement_sha256'] != expected_store_acknowledgement_pin['sha256'] or
            proof['session_proof_sha256'] != expected_session_proof_pin['sha256']):
        raise ValueError('Separate store/session raw anchors differ')
    if (not isinstance(expected_row_receipt_pins, dict) or len(expected_row_receipt_pins) != 6 or
            proof['row_receipt_pins'] != expected_row_receipt_pins):
        raise ValueError('Exactly six independently supplied row receipt pins required')
    for label, pin in expected_row_receipt_pins.items():
        if (not isinstance(label, str) or not isinstance(pin, dict) or set(pin) != {'bytes', 'sha256'} or
                type(pin['bytes']) is not int or not 0 < pin['bytes'] <= 512*MIB):
            raise ValueError('Bounded original row receipt pin required')
        sha256(pin['sha256'])
    ack_fields = {'schema', 'domain', 'repository', 'branch', 'ledger_revision', 'ledger_sha256',
                  'allocation_sha256', 'trial_allocation_sha256', 'trial_protocol_sha256', 'session_identity',
                  'trial_case_identity',
                  'source_contract_sha256', 'row_receipt_pins', 'atomic_expected_revision_cas',
                  'cas_qualification_sha256', 'irrevocable', 'accepted', 'refund_or_retry_allowed'}
    if (set(ack) != ack_fields or ack['schema'] != 'radio-scientific-irrevocable-store-ack-v1' or
            ack['domain'] != domain or ack['repository'] != REPOSITORY or ack['branch'] != BRANCH or
            ack['atomic_expected_revision_cas'] is not True or ack['irrevocable'] is not True or
            ack['accepted'] is not True or ack['refund_or_retry_allowed'] is not False):
        raise ValueError('Actual irreversible atomic store acknowledgement required')
    if ack['cas_qualification_sha256'] != expected_cas_qualification_pin['sha256']:
        raise ValueError('Irrevocable store atomic CAS law binding differs')
    for ack_key, proof_key in (('ledger_revision', 'acquisition_ledger_revision'),
                               ('ledger_sha256', 'acquisition_ledger_sha256'),
                               ('allocation_sha256', 'scientific_allocation_sha256'),
                               ('trial_allocation_sha256', 'trial_allocation_sha256'),
                               ('trial_case_identity', 'trial_case_identity'),
                               ('trial_protocol_sha256', 'trial_protocol_sha256'),
                               ('session_identity', 'session_identity'),
                               ('source_contract_sha256', 'source_contract_sha256'),
                               ('row_receipt_pins', 'row_receipt_pins')):
        if ack[ack_key] != proof[proof_key]:
            raise ValueError('Irrevocable store acknowledgement binding differs')
    session_fields = {'schema', 'domain', 'session_identity', 'source_contract_sha256',
                      'context_sha256', 'window_identity', 'role', 'row_receipt_pins',
                      'session_ordinal', 'requests_used', 'bytes_used', 'started_epoch_milliseconds',
                      'deadline_epoch_milliseconds', 'no_retries', 'active'}
    if (set(session) != session_fields or session['schema'] != 'radio-scientific-source-session-proof-v1' or
            session['domain'] != domain or session['no_retries'] is not True or session['active'] is not True):
        raise ValueError('Fresh bounded source session required')
    for key in ('session_identity', 'source_contract_sha256', 'context_sha256', 'window_identity', 'role', 'row_receipt_pins'):
        if session[key] != proof[key]:
            raise ValueError('Session source/role/window/receipt provenance differs')
    for key, ceiling in (('session_ordinal', 2), ('requests_used', 500), ('bytes_used', 512*MIB)):
        if type(session[key]) is not int or not 0 <= session[key] <= ceiling:
            raise ValueError('Exact prospective source session capacity exhausted')
    if (session['session_ordinal'] != reservation['ordinal'] or
            session['requests_used'] > reservation['requests'] or session['bytes_used'] > reservation['bytes']):
        raise ValueError('Source session exceeds its independently reserved quota')
    if (not isinstance(expected_current_session, dict) or
            set(expected_current_session) != {'session_identity', 'now_epoch_milliseconds'} or
            expected_current_session['session_identity'] != sha256(proof['session_identity']) or
            any(type(session[k]) is not int for k in ('started_epoch_milliseconds', 'deadline_epoch_milliseconds')) or
            type(expected_current_session['now_epoch_milliseconds']) is not int or
            not session['started_epoch_milliseconds'] <= expected_current_session['now_epoch_milliseconds'] < session['deadline_epoch_milliseconds'] or
            not 0 < session['deadline_epoch_milliseconds']-session['started_epoch_milliseconds'] <= 1200000):
        raise ValueError('Expired, reused or unbounded current session')
    if (expected_current_session['now_epoch_milliseconds'] >= STOP_EPOCH_MILLISECONDS or
            session['deadline_epoch_milliseconds'] > STOP_EPOCH_MILLISECONDS):
        raise ValueError('Fixed 2026-10-09 stop date reached; no automatic extension')
    if session['deadline_epoch_milliseconds']-session['started_epoch_milliseconds'] > reservation['seconds']*1000:
        raise ValueError('Session deadline exceeds irrevocable time reservation')
    active = domain == 'public-scientific-evidence'
    result = {**proof, 'pins_authenticated': True,
              'complete_scientific_evidence_authenticated': True,
              'scientific_execution_authorized': active,
              'scientific_allocation_charged': active,
              'spectral_access_authorized': active, 'simulation_only': not active,
              'validated_current_epoch_milliseconds': expected_current_session['now_epoch_milliseconds'],
              'session_deadline_epoch_milliseconds': session['deadline_epoch_milliseconds'],
              'stop_epoch_milliseconds': STOP_EPOCH_MILLISECONDS,
              'source_rows_read_here': False, 'store_mutation_performed_here': False}
    return VerifiedAdmission(canonical(result), _token=_ADMISSION_TOKEN)
