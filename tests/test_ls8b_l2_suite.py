import unittest
from unittest.mock import patch

from scripts import ls8b_l2_suite as suite


class Response:
    status = 206

    def __init__(self, headers):
        self.headers = headers
        self.read_called = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, count):
        self.read_called = True
        return b'x' * min(count, int(self.headers['Content-Length']))


class SuiteChecks(unittest.TestCase):
    def test_historical_method_and_selection_pins(self):
        suite.verify_inputs()

    def test_negative_transitive_cluster_and_tie(self):
        rows = [{'start': 10, 'duration': 1, 'score': -9.},
                {'start': 11, 'duration': 2, 'score': -10.},
                {'start': 12, 'duration': 1, 'score': -10.},
                {'start': 20, 'duration': 1, 'score': -8.5},
                {'start': 30, 'duration': 1, 'score': 11.}]
        groups = suite.signed_clusters(rows, -1)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]['representative']['start'], 12)
        self.assertEqual(groups[0]['representative']['score'], -10.)
        self.assertEqual(len(groups[0]['members']), 3)
        self.assertEqual(groups[1]['representative']['score'], -8.5)
        self.assertEqual(len(suite.signed_clusters(rows, 1)), 1)

    def test_transport_rejects_before_body_read(self):
        identity = {'total': 6000, 'etag': 'original', 'content_disposition': 'fixed.fits'}
        good = {'Content-Range': 'bytes 0-2879/6000', 'Content-Length': '2880',
                'ETag': 'original', 'Content-Disposition': 'fixed.fits'}
        for field, value in [('Content-Length', '3000'), ('ETag', 'changed'),
                             ('Content-Range', 'bytes 2880-5759/6000'),
                             ('Content-Disposition', 'other.fits')]:
            response = Response({**good, field: value})
            with self.subTest(field=field), patch.object(suite, 'urlopen', return_value=response):
                with self.assertRaises(AssertionError):
                    suite.read_range('https://example.invalid', 0, 2880, identity)
                self.assertFalse(response.read_called)

    def test_header_budget_stops_before_next_request(self):
        receipts = [{} for _ in range(22)]
        with patch.object(suite, 'read_range') as read:
            with self.assertRaises(AssertionError):
                suite.header('https://example.invalid', 0, None, receipts)
            read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
