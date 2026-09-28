"""Replay one retained connector corruption; never retry the consumed live case."""
import json
from pathlib import Path
import unittest
from seti_repeater import whole_cadence_remote_radio as r
from test_radio_whole_cadence_remote import manifest,specification
import hashlib

class RetainedResponseTests(unittest.TestCase):
    def setUp(self):
        self.response=json.loads(Path('results_radio_whole_cadence_remote_2026-09-28/short_binary_response.json').read_bytes())
        spec=specification(manifest());self.client=r.Client(lambda method,params:self.response)
        self.store=r.GitStore(self.client,spec,hashlib.sha256(spec).hexdigest(),execution_verifier=lambda m:None)
        self.sha=self.response['sha'];self.store.blob_paths[self.sha]=('b49a315e6312839d423a3be65b08a7935c759b74',r.PREFIX+'/retained-response-only.bin')

    def test_actual_short_response_exceeds_exact_size_cap(self):
        with self.assertRaisesRegex(ValueError,'Encoded Git blob exceeds cap'):self.store._blob(self.sha,17,fresh=True)

    def test_relaxed_size_still_cannot_hide_wrong_blob_hash(self):
        with self.assertRaisesRegex(ValueError,'content hash differs'):self.store._blob(self.sha,64,fresh=True)

if __name__=='__main__':unittest.main()
