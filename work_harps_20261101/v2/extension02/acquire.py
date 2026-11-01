#!/usr/bin/env python3
"""Bounded, single-pass acquisition; headers only, no spectral array access."""
import argparse
import concurrent.futures
import datetime
import importlib.util
import json
import math
from pathlib import Path
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True
from common import BASE, HERE, ROLE, csvout, dump, now, require, sha, verified_scope, verify_publication


class PayloadBudget:
    """Reserve body reads across workers so concurrent reads cannot exceed cap.

    A failed read is conservatively charged its full reservation, since urllib
    may have consumed some bytes before raising. Headers/TLS are not payload.
    """
    def __init__(self, limit):
        self.limit = limit
        self.charged = 0
        self.returned = 0
        self.reserved = 0
        self.condition = threading.Condition()

    def read(self, response, requested):
        with self.condition:
            while self.limit - self.charged - self.reserved <= 0 and self.reserved:
                self.condition.wait(timeout=1)
            amount = min(requested, self.limit - self.charged - self.reserved)
            if amount <= 0:
                raise RuntimeError('Total payload budget exhausted')
            self.reserved += amount
        try:
            block = response.read(amount)
        except Exception:
            with self.condition:
                self.reserved -= amount
                self.charged += amount
                self.condition.notify_all()
            raise
        with self.condition:
            self.reserved -= amount
            self.charged += len(block)
            self.returned += len(block)
            self.condition.notify_all()
        return block


class ArchiveRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        parsed = urllib.parse.urlparse(newurl)
        require(parsed.scheme == 'https' and parsed.hostname in ('dataportal.eso.org', 'archive.eso.org'),
                'Redirect outside public ESO archive refused')
        return super().redirect_request(request, fp, code, message, headers, newurl)

    def http_error_302(self, request, fp, code, message, headers):
        # The stdlib handler drains redirect bodies outside PayloadBudget.
        # Close without reading instead; this task only issues GET requests.
        target = headers.get('Location') or headers.get('URI')
        try:
            require(bool(target), 'Redirect has no destination')
            count = getattr(request, 'extension02_redirect_count', 0)
            require(count < 3, 'Redirect bound exceeded')
            destination = urllib.parse.urljoin(request.full_url, target)
            redirected = self.redirect_request(request, fp, code, message, headers, destination)
            redirected.extension02_redirect_count = count + 1
        finally:
            fp.close()
        return self.parent.open(redirected, timeout=request.timeout)

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


def header_module():
    spec = importlib.util.spec_from_file_location('frozen_v2_header_checks', BASE / 'v2/acquisition/download_selected.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def context(previous):
    upstream = json.loads((BASE / 'literature/UPSTREAM_REFERENCED_IDS.json').read_text())
    full = json.loads((BASE / 'literature/upstream_referenced_exposure_ids.json').read_text())
    upstream['ADP'] = sorted(set(upstream['ADP']) | {x for x in full['records'] if x.startswith('ADP.')})
    upstream['HARPS'] = sorted(set(upstream['HARPS']) | {x for x in full['records'] if x.startswith('HARPS.')})
    targets = {}
    for row in json.loads((BASE / 'acquisition/TARGET_COORDINATE_HEADERS.json').read_text())['files']:
        targets.setdefault(row['canonical_target'], []).append(row)
    return dict(upstream=upstream, old_adp_ids=set(previous['adp_ids']), old_raw_ids=set(previous['raw_ids']),
                old_time_keys={(x[0], float(x[1])) for x in previous['target_start_keys']}, old_targets=targets)


def inspect(path, row, ctx, module):
    report = module.inspect(path, row, ctx)
    with path.open('rb') as stream:
        header = module.old.read_header(stream)
    observed = datetime.datetime.fromisoformat(header['DATE-OBS']).replace(tzinfo=datetime.timezone.utc)
    expected = datetime.datetime.fromisoformat(row['raw_start_utc'])
    berv = header.get('HIERARCH ESO DRS BERV')
    report['checks'].update({
        'adp_archive_id_matches': header.get('ARCFILE') == row['dp_id'] + '.fits',
        'raw_provenance_matches_prospective_query': report['raw_progenitor_ids'] == [row['raw_progenitor_id']],
        'raw_date_matches_within_0p01_seconds': abs((observed - expected).total_seconds()) <= .01,
        'berv_present_finite_and_within_100_km_s': isinstance(berv, (int, float)) and math.isfinite(berv) and abs(berv) <= 100,
        'science_spectrum_product': header.get('PRODCATG') == 'SCIENCE.SPECTRUM',
        'proposal_matches_metadata': str(header.get('PROG_ID')) == row['proposal_id'],
        'observing_block_matches_metadata': str(header.get('OBID1')) == row['obs_id'],
    })
    report.update(header_status='PASS_METADATA_ONLY' if all(report['checks'].values()) else 'EXCLUDED_PENDING_REVIEW',
                  expected_raw_progenitor_id=row['raw_progenitor_id'],
                  queried_provenance_sha256=sha(BASE / 'v2/next_sample/RAW_PROVENANCE.csv'))
    return report


def fetch(row, ctx, module, protocol, budget, started):
    filename = row['dp_id'].replace(':', '_')
    path = HERE / 'data/main' / (filename + '.fits')
    receipt_path = HERE / 'acquisition/receipts' / (filename + '.json')
    receipt = dict(dp_id=row['dp_id'], canonical_target=row['canonical_target'], role=ROLE,
                   selection_index=int(row['selection_index']), source_url=row['source_url'], path=str(path),
                   relative_path=str(path.relative_to(BASE)), expected_raw_progenitor_id=row['raw_progenitor_id'],
                   started_utc=now(), attempts=[], array_values_inspected=False)
    require(not path.exists() and not receipt_path.exists(), 'Refusing overwrite or implicit reacquisition: ' + row['dp_id'])
    opener = urllib.request.build_opener(ArchiveRedirects())
    for timeout in protocol['attempt_timeouts_seconds']:
        if time.monotonic() - started >= protocol['maximum_start_wall_seconds']:
            receipt['download_status'] = 'NOT_RUN_WALL_BOUND'
            break
        attempt = dict(started_utc=now(), timeout_seconds=timeout, returned_payload_bytes=0)
        tick = time.monotonic()
        try:
            request = urllib.request.Request(row['source_url'], headers={
                'User-Agent': 'SETI-HARPS-extension02/1.0 (public archive research)', 'Accept-Encoding': 'identity'})
            chunks = []
            size = 0
            with opener.open(request, timeout=timeout) as response:
                attempt.update(http_status=response.status, final_url=response.url,
                               response_headers={k: response.headers.get(k) for k in
                                                 ('Content-Type', 'Content-Length', 'Content-Disposition', 'Last-Modified', 'Content-Encoding')})
                require(response.status == 200, 'Expected HTTP 200')
                length = response.headers.get('Content-Length')
                length = int(length) if length is not None else None
                require(length is None or 0 < length <= protocol['per_file_byte_cap'], 'Invalid or oversized Content-Length')
                require(response.headers.get('Content-Encoding', 'identity') == 'identity', 'Encoded payload not allowed')
                while length is None or size < length:
                    room = protocol['per_file_byte_cap'] - size
                    require(room > 0, 'Unknown-length response reached file cap without EOF')
                    amount = min(1_048_576, room, length - size if length is not None else room)
                    block = budget.read(response, amount)
                    if not block:
                        break
                    size += len(block)
                    attempt['returned_payload_bytes'] += len(block)
                    chunks.append(block)
            payload = b''.join(chunks)
            require(length is None or len(payload) == length, 'Content-Length mismatch')
            require(payload.startswith(b'SIMPLE  ') and len(payload) % 2880 == 0, 'Not a complete padded FITS file')
            partial = path.with_suffix('.part')
            partial.write_bytes(payload)
            partial.replace(path)
            receipt.update(download_status='DOWNLOADED', bytes=len(payload), sha256=sha(path))
            receipt.update(inspect(path, row, ctx, module))
            attempt['outcome'] = 'SUCCESS' if receipt['header_status'] == 'PASS_METADATA_ONLY' else 'HEADER_EXCLUDED'
            attempt['elapsed_seconds'] = time.monotonic() - tick
            receipt['attempts'].append(attempt)
            break
        except Exception as exc:
            attempt.update(outcome='FAILED', error_type=type(exc).__name__, error=str(exc), elapsed_seconds=time.monotonic() - tick)
            receipt['attempts'].append(attempt)
            receipt['download_status'] = 'FAILED'
            if path.exists():
                receipt.update(download_status='DOWNLOADED_HEADER_REVIEW_FAILED', header_status='EXCLUDED_PENDING_REVIEW')
                break
            if budget.charged >= budget.limit or isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403, 404):
                break
    receipt['finished_utc'] = now()
    dump(receipt_path, receipt)
    print(json.dumps({k: receipt.get(k) for k in ['dp_id', 'download_status', 'header_status', 'bytes']}), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Start acquisition only after root verifies publication')
    parser.add_argument('--freeze-commit')
    parser.add_argument('--published-freeze-sha256')
    args = parser.parse_args()
    rows, previous, protocol, freeze = verified_scope()
    if not args.download:
        print(json.dumps(dict(status='PREFLIGHT_PASS_NO_DOWNLOAD', selected=len(rows), prior_excluded=len(previous['adp_ids']),
                              targets=len({r['canonical_target'] for r in rows}), freeze_sha256=sha(HERE / 'FREEZE.json'))))
        return
    publication = verify_publication(args.freeze_commit, args.published_freeze_sha256)
    out = HERE / 'acquisition'
    out.mkdir(exist_ok=False)
    (out / 'receipts').mkdir()
    (HERE / 'data/main').mkdir(parents=True, exist_ok=False)
    dump(out / 'PUBLICATION.json', publication)
    dump(out / 'ACQUISITION_SCOPE.json', dict(created_utc=now(), protocol=protocol,
                                            selection_sha256=sha(HERE / 'MAIN100.csv'), freeze_sha256=sha(HERE / 'FREEZE.json'),
                                            publication=publication, array_values_inspected=False))
    budget = PayloadBudget(protocol['total_payload_byte_cap'])
    started = time.monotonic()
    ctx = context(previous)
    module = header_module()
    with concurrent.futures.ThreadPoolExecutor(max_workers=protocol['workers']) as pool:
        receipts = list(pool.map(lambda row: fetch(row, ctx, module, protocol, budget, started), rows))
    actual_raw = {}
    for receipt in receipts:
        for raw in receipt.get('raw_progenitor_ids', []):
            actual_raw.setdefault(raw, []).append(receipt['dp_id'])
    for receipt in receipts:
        if receipt.get('checks'):
            receipt['checks']['unique_raw_within_extension02'] = all(len(actual_raw[x]) == 1 for x in receipt['raw_progenitor_ids'])
            if not all(receipt['checks'].values()):
                receipt['header_status'] = 'EXCLUDED_PENDING_REVIEW'
            dump(out / 'receipts' / (receipt['dp_id'].replace(':', '_') + '.json'), receipt)
    dump(out / 'DOWNLOAD_MANIFEST.json', receipts)
    csvout(out / 'DOWNLOAD_MANIFEST.csv', receipts)
    counts = {}
    for receipt in receipts:
        key = receipt.get('header_status', receipt['download_status'])
        counts[key] = counts.get(key, 0) + 1
    result = dict(finished_utc=now(), selected_files=len(rows), elapsed_seconds=time.monotonic() - started,
                  returned_payload_bytes=budget.returned, conservative_charged_payload_bytes=budget.charged,
                  payload_budget_bytes=budget.limit, result_counts=counts, array_values_inspected=False,
                  retry_payload_included=True, replacements_allowed=False,
                  accounting='Response-body bytes only. Failed reads charge the entire reservation; transport headers and TLS overhead are not measured.')
    dump(out / 'ACQUISITION_RESULT.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
