"""Proposed lossless ASCII artifact envelope, with physical byte accounting.

Offline codec only; this does not publish, allocate, create a lease, authorize
science or make the current raw-binary remote store ready.
"""
import base64
import hashlib
import json
from .empty_null_radio import canonical
from .whole_cadence_journal_radio import artifact_name
from .whole_cadence_reference_radio import _sha

CHUNK=256*1024
MAX_RAW=18*1024**2
SCHEMA='radio-lossless-ascii-envelope-v1'


def sha(data):return hashlib.sha256(data).hexdigest()


def _cap(value):
    if type(value) is not int or not 0<value<=32*1024**2:raise ValueError('Bounded physical storage cap required')


def encode(payload,*,case_identity,name,physical_byte_cap):
    _cap(physical_byte_cap);_sha(case_identity,'case identity');artifact_name(name)
    if not isinstance(payload,bytes) or len(payload)>MAX_RAW:raise ValueError('Bounded immutable raw bytes required')
    # Reject the unavoidable encoded payload cost before allocating the envelope.
    minimum=sum(4*((min(CHUNK,len(payload)-o)+2)//3) for o in range(0,len(payload),CHUNK))
    if minimum>=physical_byte_cap:raise ValueError('Encoded bytes leave no manifest space within physical cap')
    chunks={};records=[]
    for i,o in enumerate(range(0,len(payload),CHUNK)):
        raw=payload[o:o+CHUNK];encoded=base64.b64encode(raw);path=f'chunk{i:04d}.b64';chunks[path]=encoded
        records.append({'name':path,'raw_bytes':len(raw),'encoded_bytes':len(encoded),'raw_sha256':sha(raw),'encoded_sha256':sha(encoded)})
    manifest={'schema':SCHEMA,'mode':'ENGINEERING_PROPOSAL_ONLY','encoding':'base64-rfc4648-canonical-ascii',
        'case_identity':case_identity,'artifact_name':name,'raw_bytes':len(payload),'raw_sha256':sha(payload),'chunks':records}
    parts={**chunks,'manifest.json':canonical(manifest)}
    used=sum(map(len,parts.values()))
    if used>physical_byte_cap:raise ValueError('Manifest plus encoded chunks exceed physical storage cap')
    receipt={'manifest_sha256':sha(parts['manifest.json']),'logical_bytes':len(payload),'physical_stored_bytes':used,
        'physical_byte_cap':physical_byte_cap,'scientific_execution_authorized':False,'live_transport_qualified':False}
    return parts,receipt


def decode(parts,*,expected_manifest_sha256,case_identity,name,physical_byte_cap):
    _cap(physical_byte_cap);_sha(expected_manifest_sha256,'manifest pin');_sha(case_identity,'case identity');artifact_name(name)
    if (not isinstance(parts,dict) or not all(isinstance(k,str) and isinstance(v,bytes) for k,v in parts.items())
            or 'manifest.json' not in parts):raise ValueError('Immutable complete envelope required')
    if sum(map(len,parts.values()))>physical_byte_cap:raise ValueError('Physical storage cap exceeded')
    raw_manifest=parts['manifest.json']
    if len(raw_manifest)>65536 or sha(raw_manifest)!=expected_manifest_sha256:raise ValueError('Independent manifest pin differs')
    m=json.loads(raw_manifest)
    if (canonical(m)!=raw_manifest or set(m)!={'schema','mode','encoding','case_identity','artifact_name','raw_bytes','raw_sha256','chunks'}
            or m['schema']!=SCHEMA or m['mode']!='ENGINEERING_PROPOSAL_ONLY' or m['encoding']!='base64-rfc4648-canonical-ascii'
            or m['case_identity']!=case_identity or m['artifact_name']!=name):raise ValueError('Envelope identity/schema differs')
    if type(m['raw_bytes']) is not int or not 0<=m['raw_bytes']<=MAX_RAW:raise ValueError('Raw envelope capacity exceeded')
    _sha(m['raw_sha256'],'raw aggregate')
    count=(m['raw_bytes']+CHUNK-1)//CHUNK
    if len(m['chunks'])!=count or set(parts)!={'manifest.json',*(f'chunk{i:04d}.b64' for i in range(count))}:
        raise ValueError('Envelope chunk inventory differs')
    decoded=[]
    for i,c in enumerate(m['chunks']):
        size=min(CHUNK,m['raw_bytes']-i*CHUNK);path=f'chunk{i:04d}.b64'
        if (set(c)!={'name','raw_bytes','encoded_bytes','raw_sha256','encoded_sha256'} or c['name']!=path
                or type(c['raw_bytes']) is not int or c['raw_bytes']!=size or type(c['encoded_bytes']) is not int
                or c['encoded_bytes']!=4*((size+2)//3)):raise ValueError('Chunk order/length metadata differs')
        encoded=parts[path]
        if len(encoded)!=c['encoded_bytes'] or sha(encoded)!=c['encoded_sha256']:raise ValueError('Encoded chunk bytes differ')
        data=base64.b64decode(encoded,validate=True)
        if base64.b64encode(data)!=encoded:raise ValueError('Noncanonical base64 envelope')
        if len(data)!=size or sha(data)!=c['raw_sha256']:raise ValueError('Decoded chunk bytes differ')
        decoded.append(data)
    payload=b''.join(decoded)
    if len(payload)!=m['raw_bytes'] or sha(payload)!=m['raw_sha256']:raise ValueError('Raw aggregate bytes differ')
    return payload
