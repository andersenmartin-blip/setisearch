"""New proposed-envelope risks; fixed bytes, no runtime or scientific admission."""
import base64
import copy
import json
from pathlib import Path
import unittest
from seti_repeater import whole_cadence_ascii_radio as a
from seti_repeater.empty_null_radio import canonical

class AsciiTests(unittest.TestCase):
    def setUp(self):
        self.payload=Path('results_radio_whole_cadence_remote_2026-09-28/run02/case/payload.bin').read_bytes()
        self.identity='89317409d64880b9afbee488b60273b48697bbf19fd4fc78b311d16f552abd23'
        self.args={'case_identity':self.identity,'name':'payload.bin','physical_byte_cap':1048576}
        self.parts,self.receipt=a.encode(self.payload,**self.args)

    def decode(self,parts=None,**kw):
        return a.decode(parts or self.parts,expected_manifest_sha256=self.receipt['manifest_sha256'],**(self.args|kw))

    def alter(self,fn):
        m=json.loads(self.parts['manifest.json']);fn(m);self.parts['manifest.json']=canonical(m)
        self.receipt['manifest_sha256']=a.sha(self.parts['manifest.json'])

    def test_fixed_chunk_boundary_restores_every_original_byte(self):
        self.assertEqual(self.decode(),self.payload);self.assertEqual(len(json.loads(self.parts['manifest.json'])['chunks']),2)

    def test_actual_utf8_replacement_path_leaves_envelope_ascii_unchanged(self):
        observed={k:v.decode('utf-8',errors='replace').encode('utf-8') for k,v in self.parts.items()}
        self.assertEqual(observed,self.parts);self.assertEqual(self.decode(observed),self.payload)

    def test_storage_charge_includes_manifest_and_base64_expansion(self):
        charged=sum(map(len,self.parts.values()));self.assertEqual(charged,self.receipt['physical_stored_bytes'])
        self.assertGreater(charged,len(self.payload));self.assertFalse(self.receipt['live_transport_qualified'])
        with self.assertRaisesRegex(ValueError,'physical'):a.encode(self.payload,**(self.args|{'physical_byte_cap':charged-1}))

    def test_decoder_enforces_physical_not_decoded_byte_cap(self):
        with self.assertRaisesRegex(ValueError,'Physical'):self.decode(physical_byte_cap=len(self.payload))

    def test_manifest_substitution_rejected_before_decode(self):
        self.parts['manifest.json']+=b' '
        with self.assertRaisesRegex(ValueError,'manifest pin'):self.decode()

    def test_case_substitution_rejected(self):
        with self.assertRaisesRegex(ValueError,'identity'):self.decode(case_identity='a'*64)

    def test_artifact_name_substitution_rejected(self):
        with self.assertRaisesRegex(ValueError,'identity'):self.decode(name='other.bin')

    def test_missing_chunk_rejected(self):
        del self.parts['chunk0001.b64']
        with self.assertRaisesRegex(ValueError,'inventory'):self.decode()

    def test_reordered_chunks_rejected_even_with_repinned_manifest(self):
        self.alter(lambda m:m['chunks'].reverse())
        with self.assertRaisesRegex(ValueError,'order'):self.decode()

    def test_changed_ascii_bytes_rejected(self):
        self.parts['chunk0001.b64']=b'X'+self.parts['chunk0001.b64'][1:]
        with self.assertRaisesRegex(ValueError,'Encoded'):self.decode()

    def test_noncanonical_padding_bits_rejected(self):
        # The 17-byte tail ends with one '='. Change unused pad bits while
        # preserving decoded bytes, then independently re-pin metadata.
        p='chunk0001.b64';text=self.parts[p];alphabet=b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
        k=alphabet.index(text[-2]);altered=text[:-2]+bytes([alphabet[k+1]])+text[-1:]
        self.assertEqual(base64.b64decode(text),base64.b64decode(altered));self.parts[p]=altered
        self.alter(lambda m:m['chunks'][1].update(encoded_sha256=a.sha(altered)))
        with self.assertRaisesRegex(ValueError,'Noncanonical'):self.decode()

    def test_raw_aggregate_mismatch_rejected(self):
        self.alter(lambda m:m.update(raw_sha256='b'*64))
        with self.assertRaisesRegex(ValueError,'aggregate'):self.decode()

if __name__=='__main__':unittest.main()
