"""Independent small-byte adversarial checks; no archive or telescope powers."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0,str(ROOT/'work_be/science_handoff'))
import common_be
import range_provenance_be as provenance
import verify_native_be as native

checks=[]


def check(name, fn, reject=False):
    try:
        fn()
    except (ValueError,KeyError,FileNotFoundError):
        if not reject:
            raise
    else:
        if reject:
            raise AssertionError('Accepted adversarial case: '+name)
    checks.append({'name':name,'expected_rejection':reject,'status':'PASS'})


def make_manifest():
    m={'schema':native.MANIFEST_SCHEMA,'target':'HIP44295','primary_id':65133,
       **native.COUNTS,'full_original_md5_verified':False,
       'scans':[{'scan':j,'role':'ON' if j%2==0 else 'OFF'} for j in range(6)],
       'repeated_chunk_receipts':[{'scan':j} for j in range(6)]}
    m['chunk_receipts']=[{'scan':j,'time_index':t,
                         'receipt_schema':'SETI_'+provenance.coordinate_stage(j,t)+'_DERIVED_COMPRESSED_CHUNK_V1'}
                        for j in range(6) for t in range(16)]
    return m


def changed_manifest(change):
    m=make_manifest();change(m);native.validate_manifest(m)


def main():
    check('correct87BB1BC8BE_partition',lambda:native.validate_manifest(make_manifest()))
    check('stale87plus9_count',lambda:changed_manifest(lambda m:m.update(inherited_native_rows=87,new_native_rows=9)),True)
    check('BCrow7_cannot_be_BE',lambda:changed_manifest(lambda m:m['chunk_receipts'][87].update(receipt_schema='SETI_BE_DERIVED_COMPRESSED_CHUNK_V1')),True)
    check('duplicate_coordinate_rejected',lambda:changed_manifest(lambda m:m['chunk_receipts'].__setitem__(88,copy.deepcopy(m['chunk_receipts'][87]))),True)
    check('missing_repeat_rejected',lambda:changed_manifest(lambda m:m['repeated_chunk_receipts'].pop()),True)
    check('bool_is_not_integer_count',lambda:changed_manifest(lambda m:m.update(inherited_BC_native_rows=True)),True)
    check('old_schema_rejected',lambda:changed_manifest(lambda m:m.update(schema='HDF5_EXACT_RANGE_RECOVERY_SIX_SCAN_BC_V1')),True)
    check('outside_coordinate_rejected',lambda:provenance.coordinate_stage(6,0),True)
    check('source_require_survives_pythonO',lambda:common_be.require(False,'forced'),True)
    with tempfile.TemporaryDirectory(prefix='adapter_review_',dir=ROOT/'work_be/review') as temporary:
        tmp=Path(temporary)
        class TinyContext:
            evidence=tmp/'evidence'
            work=tmp/'evidence/work_be'
            def resolve(self,path):
                p=Path(path).resolve()
                common_be.require(p.is_relative_to(tmp) and p.is_file(),'Tiny evidence escape')
                return p
            def pin(self,path,pins,expected=None):
                p=self.resolve(path);digest=common_be.sha(p)
                common_be.require(expected is None or digest==expected,'Tiny evidence hash differs')
                pins[str(p)]=digest
                return p
        ctx=TinyContext()
        scans=[{'archive':{'id':j,'size':100,'url':'https://example.invalid/synthetic'+str(j)}} for j in range(6)]
        heads=[{'etag':'synthetic-etag'} for _ in range(6)]
        def store_receipt(folder,stem,payload,record):
            folder.mkdir(parents=True,exist_ok=True)
            bp=folder/(stem+'.bin');rp=folder/(stem+'.json')
            bp.write_bytes(payload)
            rp.write_text(json.dumps(record,sort_keys=True)+'\n')
            return {**record,'payload_relative_path':str(bp),'receipt_relative_path':str(rp),
                    'stored_receipt_sha256':common_be.sha(rp)}
        def http(a,b,payload):
            return store_receipt(ctx.evidence/'work_bb/acquire/hip44295_65133/raw_transport',f'scan0_{a}_{b}',payload,
                {'scan':0,'archive_id':0,'url':scans[0]['archive']['url'],'etag':'synthetic-etag',
                 'start':a,'stop_inclusive':b,'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
                 'status':206,'attempts':1,'failed_attempts':[], 'content_range':f'bytes {a}-{b}/100'})
        a,b=http(20,22,b'abc'),http(23,24,b'de')
        segments=[{'output_offset':0,'length':3,'source_start':20,'source_stop':22,'source_receipt':a},
                  {'output_offset':3,'length':2,'source_start':23,'source_stop':24,'source_receipt':b}]
        record={'scan':0,'time_index':0,'archive_id':0,'url':scans[0]['archive']['url'],'etag':'synthetic-etag',
                'start':20,'stop_inclusive':24,'bytes':5,'sha256':hashlib.sha256(b'abcde').hexdigest(),
                'receipt_schema':'SETI_BB_DERIVED_COMPRESSED_CHUNK_V1','status':'DERIVED_FROM_VERIFIED_RANGES',
                'new_HTTP_whole_chunk_receipt_claimed':False,'coverage_segments':segments}
        derived=store_receipt(ctx.evidence/'work_bb/acquire/hip44295_65133/derived','scan0_row0',b'abcde',record)
        check('contiguous_genuine_source_union',lambda:provenance.verify(ctx,derived,'payload',scans,heads,{}))
        def reject_union(change):
            r=copy.deepcopy(derived);change(r);provenance.verify(ctx,r,'payload',scans,heads,{})
        check('gap_in_union_rejected',lambda:reject_union(lambda r:r['coverage_segments'][1].update(output_offset=4)),True)
        check('source_ETag_mutation_rejected',lambda:reject_union(lambda r:r['coverage_segments'][0]['source_receipt'].update(etag='wrong')),True)
        check('derived_as_repeat_rejected',lambda:provenance.verify(ctx,derived,'repeat',scans,heads,{}),True)
        check('fabricated_wholeHTTP_claim_rejected',lambda:reject_union(lambda r:r.update(new_HTTP_whole_chunk_receipt_claimed=True)),True)
        # Real Context relocation/mutation checks use only two tiny text files.
        evidence=tmp/'relocated';(evidence/'work_bb').mkdir(parents=True)
        tiny=evidence/'work_bb/tiny.txt';tiny.write_text('retained synthetic bytes\n')
        mapping=tmp/'relocations.json';mapping.write_text(json.dumps({'schema':'SETI_BE_EXPLICIT_RELOCATIONS_V1',
            'network_requests_authorized':0,'mappings':[{'from':'/historical/synthetic','to':str(evidence)}]}))
        context=common_be.Context(evidence,mapping)
        check('explicit_historical_relocation',lambda:common_be.require(context.resolve('/historical/synthetic/work_bb/tiny.txt')==tiny,'wrong relocation'))
        check('unknown_historical_root_rejected',lambda:context.resolve('/unmapped/tiny.txt'),True)
        check('traversal_rejected',lambda:context.resolve('work_bb/../tiny.txt'),True)
        check('incorrect_hash_rejected',lambda:context.pin(tiny,{},'0'*64),True)
        pins={};context.pin(tiny,pins);tiny.write_text('changed synthetic bytes\n')
        check('postpin_mutation_rejected',lambda:context.verify_pins(pins),True)
    forbidden={'numpy','h5py','bitshuffle','requests','urllib.request'}
    check('import_has_no_numeric_or_network_runtime',lambda:common_be.require(not forbidden.intersection(sys.modules),'unexpected runtime import'))
    output={'schema':'SETI_BE_INDEPENDENT_ADAPTER_SYNTHETIC_CHECKS_V1','status':'PASS',
            'checks':checks,'check_count':len(checks),'network_requests':0,'telescope_arrays_opened':0,
            'power_rows_decoded':0,'production_execution_authorized':False,
            'reviewed_source_sha256':{str(p.relative_to(ROOT)):common_be.sha(p) for p in
                sorted((ROOT/'work_be/science_handoff').glob('*.py'))}}
    common_be.new(ROOT/'work_be/review/INDEPENDENT_ADAPTER_SYNTHETIC_CHECKS_BE.json',output)
    print(json.dumps({'status':'PASS','checks':len(checks),'network_requests':0,'power_rows_decoded':0}))


if __name__=='__main__':
    main()
