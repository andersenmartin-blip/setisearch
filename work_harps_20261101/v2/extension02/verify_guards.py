"""Offline guard tests: concurrency/retry accounting and exact frozen identity.

No network access, no FITS opened, no synthetic detections added to science.
"""
import concurrent.futures
import io
import json
import sys

sys.dont_write_bytecode = True
from common import HERE, dump, now, require, sha, verified_scope, verify_publication
from acquire import PayloadBudget


class BrokenRead:
    def read(self, count):
        raise OSError('synthetic partial transport failure')


def main():
    rows, previous, protocol, freeze = verified_scope()
    budget = PayloadBudget(10000)
    def consume(_):
        stream = io.BytesIO(b'x' * 20000)
        returned = 0
        while True:
            try:
                returned += len(budget.read(stream, 937))
            except RuntimeError:
                return returned
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        returned = sum(pool.map(consume, range(3)))
    require(returned == budget.returned == budget.charged == 10000 and budget.reserved == 0,
            'Concurrent payload cap violated')
    failed = PayloadBudget(100)
    try:
        failed.read(BrokenRead(), 60)
    except OSError:
        pass
    require(failed.charged == 60 and failed.returned == 0 and failed.reserved == 0, 'Failed read not charged conservatively')
    require(len(failed.read(io.BytesIO(b'z' * 100), 100)) == 40, 'Retry exceeded remaining payload budget')
    eof = PayloadBudget(100)
    require(eof.read(io.BytesIO(b''), 100) == b'' and eof.charged == eof.reserved == 0, 'EOF did not release reservation')
    invalid_gate_rejected = False
    try:
        verify_publication(None, sha(HERE / 'FREEZE.json'))
    except RuntimeError:
        invalid_gate_rejected = True
    require(invalid_gate_rejected, 'Missing publication commit accepted')
    result = dict(created_utc=now(), status='PASS_OFFLINE_NO_SCIENCE_ACCESS', selected_exposures=len(rows), prior_unique_inputs=len(previous['adp_ids']),
                  frozen_sources_checked=len(freeze['source_hashes']),
                  concurrent_cap_test='PASS', failed_read_charge_and_retry_test='PASS', eof_reservation_test='PASS', missing_commit_rejection='PASS',
                  science_arrays_opened=0, network_calls=0, freeze_sha256=sha(HERE / 'FREEZE.json'))
    dump(HERE / 'PREFLIGHT.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
