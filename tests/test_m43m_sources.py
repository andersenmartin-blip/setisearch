import unittest
from urllib.error import HTTPError, URLError
from m43m_epoch_sources import transient, restart_gate


class SourceExpansionTests(unittest.TestCase):
    def test_transient_boundary(self):
        for error in (TimeoutError(), ConnectionResetError(), URLError(TimeoutError()),
                      HTTPError('https://example.invalid', 503, 'unavailable', {}, None)):
            self.assertTrue(transient(error))
        for error in (ValueError('changed ETag'), OSError('disk full'), URLError('unknown failure'),
                      HTTPError('https://example.invalid', 403, 'forbidden', {}, None)):
            self.assertFalse(transient(error))

    def test_restart_rejects_downloads_partial_rows_and_changed_identity(self):
        first = {'receipt_sha256': 'retained'}
        zero = dict(range_attempts=0, range_completed=0, accepted_range_bytes=0)
        restart_gate(first, first, {'resumed_rows': 16}, zero)
        with self.assertRaises(ValueError):
            restart_gate(first, {'receipt_sha256': 'changed'}, {'resumed_rows': 16}, zero)
        with self.assertRaises(ValueError):
            restart_gate(first, first, {'resumed_rows': 15}, zero)
        for key in zero:
            with self.assertRaises(ValueError):
                restart_gate(first, first, {'resumed_rows': 16}, {**zero, key: 1})
