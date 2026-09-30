"""Deterministic fixture framing and admission tests; no numeric RNG or data."""
import hashlib
import json
import unittest
from unittest.mock import patch

from seti_repeater import native_v2_broker_radio as broker
from radio_native_v2_local_transport_fixture import (
    DISABLED, PREFIX, deterministic_bundle, publisher_worker,
)


class LocalTransportFixtureTests(unittest.TestCase):
    def test_real_bundle_restores_exact_deterministic_source_and_constructs_publisher(self):
        bundle = deterministic_bundle(0, 32769, 'a'*40, 'b'*40)
        freeze = json.loads(bundle.freeze_bytes)
        restored = broker.restore(bundle.files, expected_manifest_sha256=freeze['manifest_sha256'],
                                  expected_prefix=bundle.prefix)
        expected = (bytes(range(256))*129)[:32769]
        self.assertEqual(restored, {'fixture/deterministic_payload.bin': expected})
        self.assertEqual(json.loads(bundle.manifest_bytes)['source_sha256'], hashlib.sha256(expected).hexdigest())
        with patch.object(broker, 'ROOT_PREFIX', PREFIX):
            publisher = broker.Publisher(bundle, lambda *args: self.fail('No dispatch authorized'),
                                         expected_bundle_sha256=bundle.sha256)
        self.assertFalse(publisher.attempted)
        self.assertEqual(len(bundle.files), 3)

    def test_fresh_sibling_framing_is_distinct_and_source_limits_are_checked_before_allocation(self):
        first = deterministic_bundle(0, 1024, 'a'*40, 'b'*40)
        sibling = deterministic_bundle(1, 1024, 'c'*40, 'd'*40)
        self.assertNotEqual(first.prefix, sibling.prefix)
        self.assertNotEqual(first.sha256, sibling.sha256)
        self.assertEqual(json.loads(sibling.freeze_bytes)['parent'], 'c'*40)
        for ordinal, size in ((True, 1), (8, 1), (0, 0), (0, broker.MAX_SOURCE_BYTES+1)):
            with self.assertRaisesRegex(ValueError, 'Bounded deterministic'):
                deterministic_bundle(ordinal, size, 'a'*40, 'b'*40)

    def test_fixture_permission_flags_cannot_authorize_a_native_worker(self):
        config = {'prefix': PREFIX, **{key: False for key in DISABLED}}
        for key in DISABLED:
            with self.assertRaisesRegex(ValueError, 'grants no authority'):
                publisher_worker({**config, key: True})


if __name__ == '__main__':
    unittest.main()
