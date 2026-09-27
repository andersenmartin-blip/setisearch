"""Bounded selected-session HTML inventory, never a product/header downloader."""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_radio_directory_provenance_2026-09-27'
BASE = 'https://bldata.berkeley.edu/pipeline/AGBT16A_999_189/'
CHILDREN = ('collate/', 'holding/')
PAIRS = {'0015': '59769', '0017': '60443', '0019': '61117'}
CAP = 32768


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []

    def handle_starttag(self, tag, attributes):
        if tag.lower() == 'a':
            pairs = [(k, v) for k, v in attributes if k.lower() == 'href']
            if len(pairs) != 1 or pairs[0][1] is None:
                raise ValueError('ambiguous index anchor')
            self.links.append(pairs[0][1])


def main():
    OUT.mkdir(exist_ok=True)
    attempt = OUT / 'retrieval_01'
    attempt.mkdir(exist_ok=False)  # no silent retry or replacement
    write(attempt / 'source_snapshot.json', {p: (ROOT / p).read_text() for p in
        ('scripts/radio_directory_inventory_20260927.py', 'RADIO_DIRECTORY_PROVENANCE_2026-09-27_SCOPE.md')})
    opener = urllib.request.build_opener(NoRedirect)
    receipts, inventory = [], []
    for child in CHILDREN:
        url = BASE + child
        started = time.monotonic()
        receipt = {'url': url, 'method': 'GET', 'began_utc': datetime.now(timezone.utc).isoformat(),
            'bytes_received': 0, 'follow_redirects': False, 'retries': 0, 'product_requested': False}
        raw = b''
        try:
            with opener.open(urllib.request.Request(url, headers={'Accept': 'text/html'}), timeout=15) as response:
                receipt.update(status=response.status, response_url=response.geturl(), headers=dict(response.headers))
                if response.status != 200 or response.geturl() != url:
                    raise ValueError('unexpected status or final URL')
                if response.headers.get_content_type() != 'text/html':
                    raise ValueError('not an HTML index')
                raw = response.read(CAP + 1)
                receipt['bytes_received'] = len(raw)
                (attempt / (child.rstrip('/') + '.html')).write_bytes(raw)
                receipt['body_sha256'] = hashlib.sha256(raw).hexdigest()
                if len(raw) > CAP: raise ValueError('HTML cap exceeded')
                parser = Links(); parser.feed(raw.decode('utf-8')); parser.close()
                if not parser.links or parser.links[0] != '../' or '<html' not in raw.decode().lower():
                    raise ValueError('unexpected index layout')
                for href in parser.links:
                    target = urllib.parse.urljoin(url, href)
                    if href == '../': continue
                    parsed = urllib.parse.urlsplit(target)
                    name = urllib.parse.unquote(parsed.path.rsplit('/', 1)[-1])
                    safe = (target.startswith(url) and parsed.scheme == 'https'
                        and parsed.netloc == 'bldata.berkeley.edu' and not parsed.query and not parsed.fragment
                        and '/' not in urllib.parse.unquote(href))
                    match = re.search(r'guppi_57522_(59769|60443|61117)_HIP1499_(0015|0017|0019)(?:\.|$)', name)
                    same = bool(match and PAIRS[match.group(2)] == match.group(1))
                    extension = Path(name).suffix.lower()
                    inventory.append({'directory': child, 'href': href, 'url': target, 'name': name,
                        'safe_session_local_file_link': safe, 'matches_selected_scan_filename': same,
                        'scan': match.group(2) if same else None, 'extension': extension,
                        'listed_original_format': same and extension in ('.raw', '.fil'),
                        'possible_metadata_sidecar': extension in ('.log', '.txt', '.json', '.yaml', '.hdr', '.header'),
                        'product_opened': False})
                receipt['complete'] = True
        except Exception as error:
            receipt.update(complete=False, error_type=type(error).__name__, error=str(error))
        receipt['elapsed_seconds'] = time.monotonic() - started
        receipts.append(receipt)
        write(attempt / 'transport_receipts.json', receipts)
        if not receipt['complete']: break
    write(attempt / 'inventory.json', inventory)
    complete = len(receipts) == 2 and all(r['complete'] for r in receipts)
    originals = [i for i in inventory if i['listed_original_format']]
    sidecars = [i for i in inventory if i['possible_metadata_sidecar']]
    selected = [i for i in inventory if i['matches_selected_scan_filename']]
    source = json.loads((ROOT / 'config/radio_hd1461_source_preparation_20260926.json').read_text())
    pinned_on = [s['url'] for s in source['scans'] if s['role'] == 'on']
    result = {'schema': 'radio-selected-directory-discovery-v1',
        'status': 'INCOMPLETE' if not complete else ('NEW_LINK_REQUIRES_SEPARATE_HEADER_SCOPE' if originals or sidecars else 'NO_ORIGINAL_OR_SIDECAR_IN_LISTED_DIRECTORIES'),
        'index_parse_complete': complete, 'child_index_requests': len(receipts),
        'child_index_bytes_received': sum(r['bytes_received'] for r in receipts),
        'prior_parent_index_requests': 1, 'prior_parent_index_bytes_received': 387,
        'direct_index_requests_cumulative': 1 + len(receipts),
        'direct_index_bytes_received_cumulative': 387 + sum(r['bytes_received'] for r in receipts),
        'prior_rendered_resource_opens': 3, 'rendered_wire_requests': None, 'rendered_wire_bytes': None,
        'listed_child_file_links': len(inventory),
        'all_listed_links_safe_session_local_files': all(i['safe_session_local_file_link'] for i in inventory),
        'selected_same_scan_filename_links': selected, 'listed_original_links': originals,
        'possible_metadata_sidecar_links': sidecars,
        'all_three_pinned_on_product_urls_listed': set(pinned_on).issubset({i['url'] for i in inventory}),
        'unlisted_or_external_originals_absent': None, 'new_pointing_observable_obtained': False,
        'pointing_hold': 'HOLD_POINTING_PROVENANCE_UNRESOLVED', 'product_requests': 0,
        'spectral_values_opened': False, 'telescope_reservations': 0, 'scientific_trials': 0,
        'source_replaced': False, 'coordinates_corrected': False, 'primary': 'neighbor9'}
    write(OUT / 'result.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'listed_child_file_links', 'direct_index_requests_cumulative',
        'direct_index_bytes_received_cumulative', 'all_three_pinned_on_product_urls_listed', 'new_pointing_observable_obtained')}, indent=2))


if __name__ == '__main__': main()
