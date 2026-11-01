"""Shared integrity checks for the prospectively frozen extension02 scope."""
from pathlib import Path
import csv
import datetime
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROLE = 'extension02_unopened'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def csvrows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def csvout(path, rows):
    fields = sorted({k for row in rows for k in row}) or ['status']
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def verified_scope():
    """Check hashes and identities without opening any science file."""
    freeze = json.loads((HERE / 'FREEZE.json').read_text())
    require(freeze['status'] == 'FROZEN_BEFORE_EXTENSION02_ACQUISITION', 'Wrong freeze state')
    for name, digest in freeze['source_hashes'].items():
        require(sha(BASE / name) == digest, 'Frozen source changed: ' + name)
    protocol = json.loads((HERE / 'PROTOCOL.json').read_text())
    rows = csvrows(HERE / 'MAIN100.csv')
    previous = json.loads((HERE / 'PRIOR209.json').read_text())
    raw = {r['product_id']: r['source_file'] for r in csvrows(BASE / 'v2/next_sample/RAW_PROVENANCE.csv')}
    require(len(rows) == len({r['dp_id'] for r in rows}) == len({r['raw_progenitor_id'] for r in rows}) == 100,
            'Expected exactly 100 unique ADP and raw exposure IDs')
    require(len(previous['adp_ids']) == len(previous['raw_ids']) == len(previous['target_start_keys']) == 209,
            'Prior scope is not 209 unique inputs')
    previous_keys = {(r[0], float(r[1])) for r in previous['target_start_keys']}
    for index, row in enumerate(rows, 1):
        require(row['role'] == ROLE, 'Incorrect cohort role')
        require(int(row['selection_index']) == index, 'Selection order changed')
        require(row['dp_id'] not in previous['adp_ids'], 'Previously used ADP')
        require(row['raw_progenitor_id'] not in previous['raw_ids'], 'Previously used raw exposure')
        require((row['canonical_target'], float(row['t_min'])) not in previous_keys, 'Previously used target/start')
        require(raw[row['dp_id']] == row['raw_progenitor_id'], 'Raw metadata query mismatch')
        require(row['source_url'] == 'https://dataportal.eso.org/dataPortal/file/' + row['dp_id'], 'Unexpected source URL')
        require(row['metadata_verification_status'] == 'PASS_ADP_RAW_ID_AND_CURRENT_METADATA', 'Metadata not verified')
    validation = json.loads((BASE / 'v2/validation/results/SUMMARY.json').read_text())
    require(validation['evaluated_trials'] == 192, 'Original validation evidence changed')
    return rows, previous, protocol, freeze


def verify_publication(commit, published_hash):
    """Root supplies the commit it has independently published and verified."""
    require(bool(re.fullmatch(r'[0-9a-f]{40}', commit or '')), 'A full published Git commit is required')
    require(published_hash == sha(HERE / 'FREEZE.json'), 'Published FREEZE.json SHA256 does not match')
    return {
        'confirmed_utc': now(), 'repository': 'andersenmartin-blip/setisearch',
        'branch': 'optical-harps-week-20261101', 'freeze_commit': commit,
        'freeze_sha256': published_hash,
        'publication_url': 'https://github.com/andersenmartin-blip/setisearch/commit/' + commit,
        'verification_responsibility': 'Root must verify the remote commit contains this exact freeze before supplying these arguments.'
    }
