"""Non-executing lower bound on retained full-snapshot journal capacity.

No journal store, lease, allocation mutation, RNG or native data is constructed.
The lower bound can disqualify a storage design; it can never qualify one.
"""
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest
from . import whole_cadence_journal_radio as journal

ZERO = '0'*64
NONCE = '00000000-0000-0000-0000-000000000000'


def minimal_events(manifest, binding, milliseconds, artifact_bytes):
    """Byte-length shapes only. These are never execution or consumption records."""
    yield {'kind': 'consume', 'binding': binding, 'milliseconds': milliseconds,
           'artifact_bytes': artifact_bytes, 'nonce': NONCE}
    if manifest['mode'] == 'scientific':
        yield {'kind': 'rng_start', 'nonce': NONCE, 'plan_sha256': binding['plan_sha256']}
    for name in manifest['required_artifacts']:
        row = {'kind': 'artifact', 'nonce': NONCE, 'name': name, 'size': 0, 'sha256': ZERO}
        if manifest['mode'] == 'scientific':
            # Shortest nonempty location/revision accepted by journal.replay.
            # Actual remote receipts and payload lengths are necessarily longer.
            row['publication'] = {'location': 'x', 'revision': 'x', 'sha256': ZERO}
        yield row
    yield {'kind': 'finish', 'nonce': NONCE, 'outcome': 'completed',
           'elapsed_milliseconds': 0, 'reason': ''}


def project(manifest, reservations):
    """Return a canonical-byte lower bound for every full immutable revision.

Hash contents have fixed lengths. All real artifact sizes, finish times,
publication locations and additional artifacts can only enlarge this bound.
No compression, Git delta encoding or filesystem metadata saving is assumed.
"""
    manifest = journal.clone(journal.validate_manifest(manifest))
    if len(reservations) != len(manifest['cases']):
        raise ValueError('Complete ordered prospective reservations required')
    milliseconds = artifacts = 0
    for case, reservation in zip(manifest['cases'], reservations, strict=True):
        if set(reservation) != {'case_identity','milliseconds','artifact_bytes'}:
            raise ValueError('Exact reservation fields required')
        if reservation['case_identity'] != case['case_identity']:
            raise ValueError('Prospective case order or identity differs')
        if any(type(reservation[k]) is not int or reservation[k] <= 0 for k in ('milliseconds','artifact_bytes')):
            raise ValueError('Positive integer reservations required')
        milliseconds += reservation['milliseconds']; artifacts += reservation['artifact_bytes']
    caps = manifest['caps']
    if milliseconds > caps['active_milliseconds'] or artifacts+caps['ledger_reserve_bytes'] > caps['evidence_bytes']:
        raise ValueError('Existing cumulative reservation ceiling exceeded')
    genesis_bytes = len(canonical(journal.genesis(manifest)))
    current = total = genesis_bytes; event_count = 0; cases = []
    for ordinal, (case, r) in enumerate(zip(manifest['cases'], reservations, strict=True)):
        first = event_count; before = total
        for event in minimal_events(manifest, case, r['milliseconds'], r['artifact_bytes']):
            record = {'index': event_count, 'previous': ZERO, 'event': event, 'sha256': ZERO}
            current += len(canonical(record)) + (1 if event_count else 0)
            total += current; event_count += 1
        cases.append({'ordinal': ordinal, 'case_identity': case['case_identity'],
                      'event_count': event_count-first, 'latest_snapshot_lower_bound_bytes': current,
                      'new_revisions_lower_bound_bytes': total-before,
                      'cumulative_revisions_lower_bound_bytes': total})
    reserve = caps['ledger_reserve_bytes']
    result = {'schema': 'radio-full-snapshot-capacity-lower-bound-v1',
              'status': 'BLOCKED_LOWER_BOUND_EXCEEDS_LEDGER_RESERVE' if total>reserve else 'NOT_QUALIFIED_LOWER_BOUND_ONLY',
              'manifest_sha256': digest(manifest), 'reservation_sha256': digest(reservations),
              'case_count': len(cases), 'event_count': event_count, 'revision_count': event_count+1,
              'genesis_bytes': genesis_bytes, 'latest_snapshot_lower_bound_bytes': current,
              'all_revisions_lower_bound_bytes': total,
              'genesis_repetition_alone_bytes': genesis_bytes*(event_count+1),
              'ledger_reserve_bytes': reserve, 'excess_lower_bound_bytes': max(0,total-reserve),
              'first_case_exceeding_reserve': next((c['ordinal'] for c in cases if c['cumulative_revisions_lower_bound_bytes']>reserve),None),
              'artifact_reservations_bytes': artifacts, 'case_reserved_milliseconds': milliseconds,
              'cases': cases, 'raw_canonical_bytes_not_git_pack_disk_measurement': True,
              'actual_artifact_lengths_or_remote_receipts_measured': False,
              'compression_or_delta_savings_assumed': False, 'store_created': False,
              'allocation_charged': False, 'values_generated': 0, 'execution_authorized': False}
    result['report_sha256'] = digest(result)
    return result
