import unittest
from urllib.error import URLError
from seti_repeater.cheops_url_timeout import resolve_url


class BoundedTransport(unittest.TestCase):
    def call(self, outcomes):
        calls, records, delays = [], [], []
        iterator = iter(outcomes)
        def request(key):
            calls.append(key)
            value = next(iterator)
            if isinstance(value, Exception):
                raise value
            return value
        return lambda: resolve_url('EXACT_KEY', request, records.append, delays.append), calls, records, delays

    def test_success_uses_one_exact_request_and_does_not_log_url(self):
        run, calls, records, delays = self.call(['private-temporary-url'])
        self.assertEqual(run(), 'private-temporary-url')
        self.assertEqual(calls, ['EXACT_KEY'])
        self.assertEqual([x['outcome'] for x in records], ['RESOLVED'])
        self.assertNotIn('private-temporary-url', str(records))
        self.assertEqual(delays, [])

    def test_wrapped_timeout_then_success_is_retained(self):
        run, calls, records, delays = self.call([URLError(TimeoutError()), 'url'])
        self.assertEqual(run(), 'url')
        self.assertEqual(calls, ['EXACT_KEY'] * 2)
        self.assertEqual([x['outcome'] for x in records], ['TIMEOUT', 'RESOLVED'])
        self.assertEqual(delays, [5])

    def test_stops_at_three_timeouts(self):
        run, calls, records, delays = self.call([TimeoutError()] * 4)
        with self.assertRaises(TimeoutError):
            run()
        self.assertEqual(calls, ['EXACT_KEY'] * 3)
        self.assertEqual([x['attempt'] for x in records], [1, 2, 3])
        self.assertEqual(delays, [5, 5])

    def test_non_timeout_url_error_is_not_retried(self):
        run, calls, records, delays = self.call([URLError('certificate failure'), 'url'])
        with self.assertRaises(URLError):
            run()
        self.assertEqual(len(calls), 1)
        self.assertEqual(records[0]['outcome'], 'STOP_NON_TIMEOUT')
        self.assertEqual(delays, [])

    def test_identity_or_schema_assertion_is_not_retried(self):
        run, calls, records, delays = self.call([AssertionError('identity'), 'url'])
        with self.assertRaises(AssertionError):
            run()
        self.assertEqual(len(calls), 1)
        self.assertEqual(records[0]['outcome'], 'STOP_NON_TIMEOUT')
        self.assertEqual(delays, [])


if __name__ == '__main__':
    unittest.main()
