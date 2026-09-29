"""Lossless read-only archive of a complete immutable journal history.

Each event is stored once with all original revision hashes and lengths.
Restoration yields original canonical documents, never an execution lease or
an authoritative writable store. No historical revision may be discarded.
"""
from dataclasses import dataclass
import hashlib
import json
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import _sha, digest
from . import whole_cadence_journal_radio as journal

SCHEMA = 'radio-readonly-journal-history-v1'
MAX_ENCODED = 8*1024**2
MAX_DECODED = 1024**3
MAX_REVISIONS = 2048


def limits(encoded_cap, decoded_cap):
    if (type(encoded_cap) is not int or not 0<encoded_cap<=MAX_ENCODED
            or type(decoded_cap) is not int or not 0<decoded_cap<=MAX_DECODED):
        raise ValueError('Finite bounded integer archive limits required')


def encode(revisions, *, expected_revision_sha256s, encoded_cap=MAX_ENCODED, decoded_cap=MAX_DECODED):
    limits(encoded_cap, decoded_cap)
    pins=tuple(expected_revision_sha256s)
    if not 1<=len(pins)<=MAX_REVISIONS or len(set(pins))!=len(pins):
        raise ValueError('Distinct bounded complete revision inventory required')
    for pin in pins:_sha(pin,'independent revision')
    previous=None;checkpoints=[];total=0
    for i,raw in enumerate(revisions):
        if i>=len(pins) or not isinstance(raw,bytes) or hashlib.sha256(raw).hexdigest()!=pins[i]:
            raise ValueError('Original immutable revision pin differs')
        total+=len(raw)
        if total>decoded_cap:raise ValueError('Decoded history capacity exceeded')
        doc=json.loads(raw)
        if canonical(doc)!=raw:raise ValueError('Noncanonical original revision')
        journal.replay(doc)
        if len(doc['events'])!=i:raise ValueError('Missing, duplicate or reordered revision')
        if previous is not None and (doc['manifest']!=previous['manifest'] or doc['events'][:-1]!=previous['events']):
            raise ValueError('History is not a single immutable append-only chain')
        checkpoints.append({'event_count':i,'sha256':pins[i],'size':len(raw)})
        previous=doc
    if len(checkpoints)!=len(pins):raise ValueError('Incomplete original revision inventory')
    payload=canonical({'schema':SCHEMA,'latest':previous,'checkpoints':checkpoints,
                       'restoration_only':True,'execution_restart_authorized':False})
    if len(payload)>encoded_cap:raise ValueError('Encoded history capacity exceeded')
    # Independent original pins, not just the newly generated envelope hash.
    verify(payload,expected_sha256=hashlib.sha256(payload).hexdigest(),
           expected_revision_sha256s=pins,encoded_cap=encoded_cap,decoded_cap=decoded_cap)
    return payload


@dataclass(frozen=True)
class VerifiedHistory:
    payload: bytes
    payload_sha256: str

    def revision(self, index):
        if hashlib.sha256(self.payload).hexdigest()!=self.payload_sha256:raise ValueError('History changed')
        packed=json.loads(self.payload);rows=packed['checkpoints']
        if type(index) is not int or not 0<=index<len(rows):raise ValueError('Revision index outside inventory')
        doc=packed['latest'];doc['events']=doc['events'][:index];raw=canonical(doc)
        if len(raw)!=rows[index]['size'] or hashlib.sha256(raw).hexdigest()!=rows[index]['sha256']:
            raise ValueError('Restored revision differs')
        return raw

    def summary(self):
        packed=json.loads(self.payload)
        return {'schema':SCHEMA,'archive_sha256':self.payload_sha256,
                'encoded_bytes':len(self.payload),'revision_count':len(packed['checkpoints']),
                'restored_canonical_bytes':sum(r['size'] for r in packed['checkpoints']),
                'latest_revision_sha256':packed['checkpoints'][-1]['sha256'],
                'execution_restart_authorized':False,'writable_store_qualified':False,
                'source_artifact_payloads_included':False}


def verify(payload, *, expected_sha256, expected_revision_sha256s,
           encoded_cap=MAX_ENCODED, decoded_cap=MAX_DECODED):
    limits(encoded_cap,decoded_cap);_sha(expected_sha256,'independent archive')
    if not isinstance(payload,bytes) or len(payload)>encoded_cap:raise ValueError('Encoded history capacity exceeded')
    if hashlib.sha256(payload).hexdigest()!=expected_sha256:raise ValueError('Archive bytes differ from independent pin')
    packed=json.loads(payload)
    if (canonical(packed)!=payload or set(packed)!={'schema','latest','checkpoints','restoration_only','execution_restart_authorized'}
            or packed['schema']!=SCHEMA or packed['restoration_only'] is not True
            or packed['execution_restart_authorized'] is not False):
        raise ValueError('Read-only history schema or authority differs')
    rows=packed['checkpoints'];pins=tuple(expected_revision_sha256s)
    if (not 1<=len(rows)<=MAX_REVISIONS or len(rows)!=len(pins)
            or len(set(pins))!=len(pins) or len(packed['latest']['events'])+1!=len(rows)):
        raise ValueError('Complete distinct revision inventory required')
    for i,(r,pin) in enumerate(zip(rows,pins,strict=True)):
        _sha(pin,'independent revision')
        if (set(r)!={'event_count','size','sha256'} or type(r['event_count']) is not int or r['event_count']!=i
                or r['sha256']!=pin or type(r['size']) is not int or r['size']<=0):
            raise ValueError('Revision order, pin or length differs')
    if sum(r['size'] for r in rows)>decoded_cap:raise ValueError('Decoded history capacity exceeded')
    journal.replay(packed['latest'])
    restored=VerifiedHistory(payload,expected_sha256)
    total=0
    for i in range(len(rows)):
        total+=len(restored.revision(i))
        if total>decoded_cap:raise ValueError('Decoded history capacity exceeded')
    return restored
