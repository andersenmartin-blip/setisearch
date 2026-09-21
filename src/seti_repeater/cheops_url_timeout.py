"""Fixed, bounded retries for download URL resolution only; no science retries."""
from datetime import datetime, timezone
import time
from urllib.error import URLError


def resolve_url(key, request_once, record, wait=time.sleep):
    """Keep the exact request; record every outcome without logging temporary URLs."""
    for attempt in range(1, 4):
        entry = {'file_key': key, 'attempt': attempt,
                 'started_utc': datetime.now(timezone.utc).isoformat()}
        try:
            url = request_once(key)
        except Exception as exc:
            reason = exc.reason if isinstance(exc, URLError) else exc
            timeout = isinstance(reason, TimeoutError)
            entry.update(outcome='TIMEOUT' if timeout else 'STOP_NON_TIMEOUT',
                         error_type=type(reason).__name__)
            record(entry)
            if not timeout or attempt == 3:
                raise
            wait(5)
        else:
            entry['outcome'] = 'RESOLVED'
            record(entry)
            return url
    raise AssertionError('unreachable')
