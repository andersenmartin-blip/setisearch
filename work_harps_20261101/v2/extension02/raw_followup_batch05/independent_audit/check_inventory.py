"""Independent batch05 manifest/receipt/accounting audit; no network or array reads."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
BATCH = HERE.parent
BASE = BATCH.parent.parents[1]


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    output = HERE / 'ACQUISITION_INVENTORY.json'
    assert not output.exists(), 'Preserve prior audit output'
    manifest = read(BATCH / 'products/MANIFEST.json')
    jobs = read(BATCH / 'JOBS.json')
    plan = read(BATCH / 'PLAN.json')
    start = read(BATCH / 'DOWNLOAD_STARTED.json')
    products = manifest['products']
    assert len(products) == len(jobs) == 2
    assert [p['archive_id'] for p in products] == [j['archive_id'] for j in jobs]
    assert {p['kind'] for p in products} == {'RAW', 'ANCILLARY'}
    assert {p['dp_id'] for p in products} == {'ADP.2023-07-07T01:08:58.252'}
    assert manifest['publication'] == start['publication']
    assert start['publication']['commit'] == '5d41596a3c11bed6d169ed2c5dd2a4213345041b'
    assert start['publication']['freeze_sha256'] == sha(BATCH / 'FOLLOWUP_FREEZE.json')
    known = charged = attempts = 0
    records = []
    for p, job in zip(products, jobs):
        assert p['status'] == 'DOWNLOADED'
        assert p['url'] == job['url'] == 'https://dataportal.eso.org/dataPortal/file/' + p['archive_id']
        assert p['head_final_url'] == p['url']
        assert p['metadata_attempts'] == job['attempts']
        receipt = BATCH / 'products' / (p['filename'] + '.json')
        assert read(receipt) == p
        payload = BASE / p['relative_path']
        assert payload == BATCH / 'products' / p['filename']
        assert payload.stat().st_size == p['bytes'] == p['advertised_bytes'] == job['advertised_bytes']
        assert sha(payload) == p['sha256']
        assert 1 <= len(p['attempts']) <= plan['acquisition_bounds']['max_attempts_per_product']
        assert p['attempts'][-1]['outcome'] == 'SUCCESS'
        for a in p['attempts']:
            known += a['known_returned_payload_bytes']
            charged += a['charged_payload_bytes']
            attempts += 1
            assert a['charged_payload_bytes'] >= a['known_returned_payload_bytes'] >= 0
        records.append({'archive_id': p['archive_id'], 'bytes': p['bytes'], 'sha256': p['sha256'], 'receipt_sha256': sha(receipt), 'attempts': len(p['attempts'])})
    assert known == manifest['known_returned_payload_bytes']
    assert charged == manifest['charged_payload_bytes'] <= plan['acquisition_bounds']['payload_cap_bytes']
    assert manifest['unknown_bytes_conservatively_charged'] == charged - known
    assert manifest['reserved_bytes'] == manifest['replacements'] == 0
    allowed = {'MANIFEST.json'} | {p['filename'] for p in products} | {p['filename'] + '.json' for p in products}
    extras = sorted(p.name for p in (BATCH / 'products').iterdir() if p.name not in allowed)
    assert not extras, 'Noncanonical product files require explicit audit: ' + repr(extras)
    log_lines = (BATCH / 'acquisition.log').read_text().splitlines()
    statuses = [line for line in log_lines if line.startswith('ADP.')]
    assert len(statuses) == 2 and sum(line.startswith('COMPLETE ') for line in log_lines) == 1
    assert statuses == [p['dp_id'] + ' ' + p['kind'] + ' ' + p['status'] for p in products]
    out = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'PASS', 'canonical_products': len(products), 'complete_pairs': 1, 'payload_attempts': attempts, 'known_returned_payload_bytes': known, 'charged_payload_bytes': charged, 'unknown_byte_charge': charged-known, 'noncanonical_product_files': extras, 'acquisition_stdout_status_lines':len(statuses), 'completion_line_present':True, 'manifest_sha256': sha(BATCH / 'products/MANIFEST.json'), 'script_sha256': sha(Path(__file__)), 'products':records, 'scope':'Independent receipt equality, original frozen job identity, canonical length/hash and attempt-byte ledger accounting. Does not independently verify network traffic beyond retained receipts and stdout; source array reconstruction is in SUMMARY.json.'}
    output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
