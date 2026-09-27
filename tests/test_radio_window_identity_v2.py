"""Actual new metadata identities and focused rehashed-tamper checks; no spectra."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from seti_repeater import window_identity_radio_v2 as m

ROOT=Path(__file__).resolve().parents[1]


class WindowV2Tests(unittest.TestCase):
    def setUp(self):
        self.raw=(ROOT/'config/radio_hd189733_source_preparation_20260927.json').read_bytes()
        self.pin=hashlib.sha256(self.raw).hexdigest()
        self.design=json.loads((ROOT/'results_radio_hd189733_geometry_2026-09-27/window_geometry.json').read_text())

    def build(self,design=None):
        d=self.design if design is None else design
        raw=json.dumps(d,sort_keys=True).encode()
        return m.build(self.raw,self.pin,raw,hashlib.sha256(raw).hexdigest())

    def altered(self,change):
        d=copy.deepcopy(self.design);w=d['windows'][0];change(w)
        w['payload_keys_sha256']=m.digest(w['payload_keys'])
        w['identity']=m.digest({k:v for k,v in w.items() if k!='identity'})
        with self.assertRaises(ValueError):self.build(d)

    def test_widened_actual_geometry_binds_but_never_authorizes(self):
        r=self.build()
        self.assertEqual(r['distinct_native_chunk_identities'],288)
        self.assertEqual(r['normalization_blocks'],48)
        self.assertTrue(all(w['native_channel_count']==65536 for w in r['windows']))
        self.assertFalse(r['spectral_access_authorized'])
        self.assertFalse(r['threshold_transfer_authorized'])

    def test_external_pin_required(self):
        raw=json.dumps(self.design).encode()
        with self.assertRaises(ValueError):m.build(self.raw,'0'*64,raw,hashlib.sha256(raw).hexdigest())

    def test_rehashed_changed_source_rejected(self):
        self.altered(lambda w:w['payload_keys'][0].update(source_url='https://bldata.berkeley.edu/old_source.h5'))

    def test_rehashed_changed_etag_rejected(self):
        self.altered(lambda w:w['payload_keys'][0].update(etag='"changed"'))

    def test_rehashed_shifted_interval_rejected(self):
        self.altered(lambda w:w.update(archive_interval=[v+1 for v in w['archive_interval']]))

    def test_rehashed_duplicate_time_row_rejected(self):
        self.altered(lambda w:w['payload_keys'][0]['chunk_coordinates_time_feed_frequency'].__setitem__(1,w['payload_keys'][0]['chunk_coordinates_time_feed_frequency'][0]))

    def test_rehashed_normalization_gap_rejected(self):
        self.altered(lambda w:w['normalization_blocks_native_channels'][0].__setitem__(1,4095))

    def test_rehashed_cross_role_payload_reuse_rejected(self):
        d=copy.deepcopy(self.design);w=copy.deepcopy(d['windows'][0])
        w['role']='validation';w['name']='hd189733_validation_geometry'
        w['identity']=m.digest({k:v for k,v in w.items() if k!='identity'})
        d['windows'][1]=w
        with self.assertRaisesRegex(ValueError,'share a decoded native chunk'):self.build(d)


if __name__=='__main__':unittest.main()
