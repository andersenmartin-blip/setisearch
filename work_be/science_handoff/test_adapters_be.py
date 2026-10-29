"""Synthetic structural and provenance rejection checks; no telescope powers."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from common_be import Context, ROOT, new, sha
import range_provenance_be as provenance
from verify_native_be import COUNTS, PROOF_SCOPE, validate_manifest, validate_marker
from build_bound_be import validate_production_native
from run_science_phases_be import validate_production_bound


def manifest():
    chunks=[]
    for j in range(6):
        for t in range(16):
            stage=provenance.coordinate_stage(j,t)
            chunks.append({'scan':j,'time_index':t,'receipt_schema':f'SETI_{stage}_DERIVED_COMPRESSED_CHUNK_V1'})
    return dict(schema='HDF5_EXACT_RANGE_RECOVERY_SIX_SCAN_BE_V1',execution_mode='PRODUCTION',target='HIP44295',primary_id=65133,
                scans=[{'scan':j,'role':('ON','OFF')[j%2]} for j in range(6)],chunk_receipts=chunks,
                repeated_chunk_receipts=[{'scan':j} for j in range(6)],full_original_md5_verified=False,**COUNTS)


class LineageTests(unittest.TestCase):
    def test_three_stage_partition(self):
        self.assertEqual(validate_manifest(manifest()),{'BB':87,'BC':1,'BE':8})

    def test_reject_old_87_plus_9(self):
        m=manifest();m['inherited_native_rows']=87;m['new_native_rows']=9
        with self.assertRaises(ValueError):validate_manifest(m)

    def test_reject_row7_freshness_relabel(self):
        m=manifest();m['chunk_receipts'][87]['receipt_schema']='SETI_BE_DERIVED_COMPRESSED_CHUNK_V1'
        with self.assertRaises(ValueError):validate_manifest(m)

    def test_reject_duplicate_coordinate(self):
        m=manifest();m['chunk_receipts'][-1]=copy.deepcopy(m['chunk_receipts'][-2])
        with self.assertRaises(ValueError):validate_manifest(m)

    def test_reject_missing_genuine_sixth_repeat(self):
        m=manifest();m['repeated_chunk_receipts'][-1]={'scan':4}
        with self.assertRaises(ValueError):validate_manifest(m)

    def test_reject_simulation_and_unknown_manifest_modes(self):
        for mode in ('SIMULATION','UNKNOWN',None):
            m=manifest();m['execution_mode']=mode
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_manifest(m)

    def test_production_marker_and_simulation_marker_rejection(self):
        marker=dict(COUNTS,schema='SETI_BE_RECOVERY_ACQUISITION_COMPLETE_V1',status='PASS',
                    execution_mode='PRODUCTION',manifest_sha256='manifest',protocol_sha256='protocol',
                    scientific_coverage_credit=0,mandatory_native_and_science_checks_pending=True)
        validate_marker(marker,'manifest','protocol')
        for mode in ('SIMULATION','UNKNOWN',None):
            bad=dict(marker,execution_mode=mode)
            with self.subTest(mode=mode),self.assertRaises(ValueError):validate_marker(bad,'manifest','protocol')

    def test_binder_rejects_simulation_or_missing_proof_scope(self):
        valid={'execution_mode':'PRODUCTION','proof_scope':PROOF_SCOPE}
        validate_production_native(valid)
        for mode in ('SIMULATION','UNKNOWN',None):
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                validate_production_native(dict(valid,execution_mode=mode))
        with self.assertRaises(ValueError):validate_production_native({'execution_mode':'PRODUCTION'})

    def test_phase_sequencer_rejects_simulation_or_missing_native_scope(self):
        valid={'execution_mode':'PRODUCTION','native_proof_scope':PROOF_SCOPE}
        validate_production_bound(valid)
        for mode in ('SIMULATION','UNKNOWN',None):
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                validate_production_bound(dict(valid,execution_mode=mode))
        with self.assertRaises(ValueError):validate_production_bound({'execution_mode':'PRODUCTION'})


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='be_synthetic_',dir=ROOT)
        self.base=Path(self.tmp.name)
        self.evidence=self.base/'evidence';self.evidence.mkdir()
        self.map=self.base/'relocations.json'
        new(self.map,{'schema':'SETI_BE_EXPLICIT_RELOCATIONS_V1','network_requests_authorized':0,
                     'mappings':[{'from':'/historical/run','to':str(self.evidence)}]})
        self.ctx=Context(self.evidence,self.map)
        self.scans=[{'archive':{'id':j,'url':'https://synthetic.invalid/file'+str(j),'size':1000}} for j in range(6)]
        self.heads=[{'etag':'synthetic-etag'} for _ in range(6)]

    def tearDown(self):self.tmp.cleanup()

    def http(self,lo,payload):
        folder=self.evidence/'work_bc/acquire/transport';folder.mkdir(parents=True,exist_ok=True)
        hi=lo+len(payload)-1;bp=folder/f'scan5_{lo}_{hi}.bin';rp=bp.with_suffix('.json')
        bp.write_bytes(payload)
        r={'scan':5,'archive_id':5,'url':self.scans[5]['archive']['url'],'etag':'synthetic-etag',
           'start':lo,'stop_inclusive':hi,'bytes':len(payload),'sha256':sha(bp),
           'status':206,'attempts':1,'failed_attempts':[],'content_range':f'bytes {lo}-{hi}/1000'}
        new(rp,r)
        return dict(r,payload_relative_path=str(bp),receipt_relative_path=str(rp),stored_receipt_sha256=sha(rp))

    def test_explicit_relocation_and_unmapped_root_rejected(self):
        r=self.http(100,b'fixture')
        wanted=self.ctx.resolve(r['receipt_relative_path'])
        relative=wanted.relative_to(self.evidence)
        self.assertEqual(self.ctx.resolve('/historical/run/'+str(relative)),wanted)
        with self.assertRaises(ValueError):self.ctx.resolve('/unmapped/run/'+str(relative))

    def test_genuine_http_hash_and_receipt_checks(self):
        r=self.http(100,b'fixture');pins={}
        provenance.verify(self.ctx,r,'retained_http_range',self.scans,self.heads,pins)
        Path(r['payload_relative_path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):provenance.verify(self.ctx,r,'retained_http_range',self.scans,self.heads,{})

    def test_derived_union_rejects_incomplete_source_slices(self):
        source=self.http(100,b'abcd')
        folder=self.evidence/'work_bc/acquire/derived';folder.mkdir(parents=True)
        bp=folder/'scan5_row7.bin';bp.write_bytes(b'abcd');rp=bp.with_suffix('.json')
        segment={'output_offset':0,'source_start':100,'source_stop':103,'length':4,'source_receipt':source}
        r={'receipt_schema':'SETI_BC_DERIVED_COMPRESSED_CHUNK_V1','status':'DERIVED_FROM_VERIFIED_RANGES',
           'scan':5,'time_index':7,'archive_id':5,'url':self.scans[5]['archive']['url'],'etag':'synthetic-etag',
           'start':100,'stop_inclusive':103,'bytes':4,'sha256':sha(bp),'coverage_segments':[segment],
           'new_HTTP_whole_chunk_receipt_claimed':False}
        new(rp,r)
        augmented=dict(r,payload_relative_path=str(bp),receipt_relative_path=str(rp),stored_receipt_sha256=sha(rp))
        provenance.verify(self.ctx,augmented,'payload',self.scans,self.heads,{})
        # Re-save a self-consistent receipt that omits a source byte: byte-union
        # validation must reject it even though both file hashes are genuine.
        bad=copy.deepcopy(r);bad['coverage_segments'][0].update(source_stop=102,length=3)
        rp.write_text(json.dumps(bad))
        augmented=dict(bad,payload_relative_path=str(bp),receipt_relative_path=str(rp),stored_receipt_sha256=sha(rp))
        with self.assertRaises(ValueError):provenance.verify(self.ctx,augmented,'payload',self.scans,self.heads,{})


if __name__ == '__main__':unittest.main()
