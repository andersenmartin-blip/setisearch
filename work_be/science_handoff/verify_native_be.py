"""Prepared offline native proof for BB87 + BC1 + BE8 retained inputs.

Import and --help use only the standard library. Execution requires independently
reviewed external GO plus complete acquisition actual0; no network fallback.
The unchanged historical codec/TREE helper is shared, not independently qualified.
"""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
from common_be import Context, LINEAGE, ROOT, WORK, new, read, require, sha, utc
import common_be
import range_provenance_be as provenance

MANIFEST_SCHEMA = 'HDF5_EXACT_RANGE_RECOVERY_SIX_SCAN_BE_V1'
PROOF_SCHEMA = 'SETI_BE_RECOVERY_NATIVE_INPUT_PROOF_V1'
PROOF_SCOPE = 'COMPLETE_PRODUCTION_ACQUISITION_NATIVE_RECONSTRUCTION'
REPEAT_KEYS = ('archive_id', 'scan', 'start', 'stop_inclusive', 'bytes', 'sha256', 'etag', 'url')
COUNTS = {'inherited_BB_native_rows': 87, 'inherited_BC_native_rows': 1,
          'inherited_native_rows': 88, 'new_native_rows': 8, 'total_native_rows': 96,
          'inherited_repeat_checks': 5, 'new_repeat_checks': 1,
          'scan5_prior_rows_reconstructed': 8, 'scan5_new_rows_decoded': 8}


def validate_manifest(m):
    """Structural lineage checks are also usable without a numeric runtime."""
    require(m['schema'] == MANIFEST_SCHEMA and m['target'] == 'HIP44295'
            and m['primary_id'] == 65133, 'BE manifest identity differs')
    require(m.get('execution_mode') == 'PRODUCTION', 'Simulation or unspecified acquisition cannot enter native proof')
    for key, value in COUNTS.items():
        require(type(m[key]) is int and m[key] == value, 'BE manifest lineage differs: ' + key)
    chunks = m['chunk_receipts']
    require(len(chunks) == 96, 'Exactly96 selected chunks required')
    coords = [(r['scan'], r['time_index']) for r in chunks]
    require(len(set(coords)) == 96 and set(coords) == {(j,t) for j in range(6) for t in range(16)},
            'Selected coordinate inventory is incomplete/duplicated')
    stagecounts = {'BB': 0, 'BC': 0, 'BE': 0}
    for r in chunks:
        stage = provenance.coordinate_stage(r['scan'], r['time_index'])
        require(r['receipt_schema'] == f'SETI_{stage}_DERIVED_COMPRESSED_CHUNK_V1',
                'Selected chunk mislabeled across BB/BC/BE')
        stagecounts[stage] += 1
    require(stagecounts == {'BB':87, 'BC':1, 'BE':8}, 'Three-stage coordinate lineage differs')
    scans, repeats = m['scans'], m['repeated_chunk_receipts']
    require(len(scans) == 6 and [s['scan'] for s in scans] == list(range(6))
            and [s['role'] for s in scans] == ['ON','OFF']*3, 'Ordered six-scan ON/OFF inventory differs')
    require(len(repeats) == 6 and sorted(r['scan'] for r in repeats) == list(range(6)),
            'Exactly one genuine repeat per scan required')
    require(m['full_original_md5_verified'] is False, 'Original full-file MD5 is unqualified')
    return stagecounts


def validate_marker(marker, manifest_sha256, protocol_sha256):
    require(marker.get('schema') == 'SETI_BE_RECOVERY_ACQUISITION_COMPLETE_V1'
            and marker.get('status') == 'PASS' and marker.get('execution_mode') == 'PRODUCTION',
            'Only a completed production acquisition marker can enter native proof')
    require(marker['manifest_sha256'] == manifest_sha256 and marker['protocol_sha256'] == protocol_sha256,
            'Acquisition marker binding differs')
    for key,value in COUNTS.items():
        require(type(marker[key]) is int and marker[key] == value, 'Acquisition marker lineage differs: '+key)
    require(marker['scientific_coverage_credit'] == 0 and marker['mandatory_native_and_science_checks_pending'] is True,
            'Acquisition cannot grant science credit')


def referenced(ctx, obj, key, pins):
    return ctx.pin(obj[key + '_path'], pins, obj[key + '_sha256'])


def verify_prior(ctx, m, pins):
    bbpath = referenced(ctx, m, 'prior_BB_partial_proof', pins)
    bcpath = referenced(ctx, m, 'prior_BC_partial_proof', pins)
    bb, bc = read(bbpath), read(bcpath)
    require(bb['status'] == 'PASS_PARTIAL_INPUTS' and bb['derived_compressed_chunks_verified'] == 87
            and bb['retained_TREE_descriptors_checked'] == 87 and bb['all_declared_valid_row_bytes_match'],
            'Inherited BB partial proof differs')
    require(bc['status'] == 'PASS_PARTIAL_INPUTS' and bc['total_derived_compressed_chunks_retained'] == 88
            and bc['inherited_rows_verified_by_prior_hash_bound_proof'] == 87
            and bc['BC_new_row_redecoded_by_this_audit'] == 1
            and bc['scan5_valid_rows_compared'] == 8 and bc['all_declared_valid_row_bytes_match'],
            'Inherited BC delta proof differs')
    require(bc['inherited_BB_partial_proof_sha256'] == sha(bbpath), 'BC proof does not bind original BB proof')
    for proof in (bb, bc):
        for name, digest in proof['input_and_evidence_sha256'].items():
            ctx.pin(name, pins, digest)
    # Original failed acquisitions remain failed, never translated to success.
    ctx.actual('work_bb/execution/PAYLOAD_ACTUAL_EXIT_BB.json', 1, pins)
    ctx.actual('work_bb/execution/PARTIAL_INPUT_AUDIT_ACTUAL_EXIT_BB.json', 0, pins)
    ctx.actual('work_bc/execution/RECOVERY_ACTUAL_EXIT_BC.json', 1, pins)
    ctx.actual('work_bc/execution/PARTIAL_INPUT_AUDIT_ACTUAL_EXIT_BC.json', 0, pins)
    for key, canonical in [('original_BB_failed_actual','work_bb/execution/PAYLOAD_ACTUAL_EXIT_BB.json'),
                           ('prior_BC_failed_actual','work_bc/execution/RECOVERY_ACTUAL_EXIT_BC.json')]:
        require(referenced(ctx,m,key,pins) == ctx.resolve(canonical),
                'Manifest historical failure identity differs: '+key)
    return bbpath, bcpath, bb, bc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','prepower','recovery','go','output','evidence-root','relocations'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    ctx = Context(args.evidence_root, args.relocations)
    pins = {}
    mp, pp, rp, gp = [ctx.pin(p, pins) for p in (args.manifest,args.prepower,args.recovery,args.go)]
    out = Path(args.output).resolve()
    require(out.is_relative_to(WORK) and not out.exists(), 'New BE-only proof output required')
    go = read(gp)
    require(go['schema'] == 'SETI_BE_NATIVE_GO_V1' and go['authorized'] is True
            and go['native_reconstruction_only'] is True
            and go['numerical_execution_authorized'] is False, 'External native-only GO required')
    ctx.pin_relocations(go, pins)
    for path, key in [(mp,'manifest'),(pp,'prepower_protocol'),(rp,'recovery_protocol'),
                      (Path(__file__),'native_review_source'),
                      (Path(provenance.__file__),'provenance_source'),
                      (Path(common_be.__file__),'common_source')]:
        ctx.pin(path, pins, go[key+'_sha256'])
    ap = referenced(ctx, go, 'acquisition_actual', pins)
    acquisition_actual = ctx.actual(ap, 0, pins)
    markerpath = referenced(ctx, go, 'acquisition_marker', pins)
    require(acquisition_actual['result_sha256'] == sha(markerpath)
            and ctx.resolve(acquisition_actual['result_path']) == markerpath,
            'Acquisition actual0 is not bound to the completion marker')
    reviewpath = referenced(ctx, go, 'scientific_method_review', pins)
    review = read(reviewpath)
    require(review['status'] == 'PASS' and review['approved_for_native_after_acquisition_actual0'] is True
            and review['native_review_source_sha256'] == sha(__file__), 'Independent native source review required')
    p, recovery, m, marker = read(pp), read(rp), read(mp), read(markerpath)
    validate_manifest(m)
    require(p['target'] == recovery['target'] == m['target'] == 'HIP44295'
            and p['primary_id'] == recovery['primary_id'] == m['primary_id'] == 65133,
            'Protocol identity differs')
    require(recovery['original_BB_prepower_sha256'] == sha(pp)
            and m['protocol_sha256'] == sha(rp), 'Prepower/recovery binding differs')
    require(recovery['configuration'] == p['configuration'] and recovery['selection'] == p['selection']
            and recovery['hdf_chunk_index_model'] == p['hdf_chunk_index_model'], 'Original science or TREE model changed')
    validate_marker(marker,sha(mp),sha(rp))
    for protocol in (p,recovery):
        for name,digest in protocol['source_and_state_sha256'].items():
            ctx.pin(name,pins,digest)
    local_acquisition_sources = recovery['local_source_sha256']
    require(len(local_acquisition_sources) == 1, 'Exactly one protocol-pinned acquisition runner required')
    for name,digest in local_acquisition_sources.items():
        source = ctx.pin(name,pins,digest)
        require(source == WORK/'recover_missing_rows_be.py' and marker['source_sha256'] == digest,
                'Production marker acquisition source differs from frozen protocol')
    bbpath, bcpath, bb, bc = verify_prior(ctx,m,pins)
    addendumpath = referenced(ctx,m,'power_contact_scope_addendum',pins)
    addendum = read(addendumpath)
    require(m['power_contact_scope_addendum'] == addendum == bc['power_contact_scope_addendum'],
            'Historical prefix scope correction changed')
    require(addendum['status'] == 'PASS_SCOPE_CORRECTION_BEFORE_DECODING'
            and addendum['power_decodes_by_this_review'] == 0 and addendum['network_requests_by_this_review'] == 0,
            'Historical addendum identity differs')
    ctx.pin(addendum['exact_request_actual_path'],pins,addendum['exact_request_actual_sha256'])
    ctx.actual(addendum['exact_request_actual_path'],0,pins)
    ctx.pin(addendum['exact_request_result_path'],pins,addendum['exact_request_result_sha256'])
    hp = referenced(ctx,m,'actual_headers',pins)
    heads = read(hp)['headers']
    require(sha(hp) == p['actual_headers_sha256'] and len(heads) == 6, 'Original actual headers differ')
    selection = referenced(ctx,m,'selection',pins)
    sel = read(selection)
    require(sel['powers_inspected_before_selection'] is False
            and sel['actual_headers_sha256'] == sha(hp)
            and sel['target'] == 'HIP44295' and sel['primary_id'] == 65133,
            'Original selection was not fixed before BB powers')
    channel = p['selection']['channel_start']
    require(channel == 179306496 and p['selection']['channel_count'] == 1048576
            and p['selection']['native_chunk_index'] == 171, 'Original selection geometry differs')
    scans,chunks,repeats = m['scans'],m['chunk_receipts'],m['repeated_chunk_receipts']
    require([s['archive']['id'] for s in scans] == [s['archive_id'] for s in p['scans']]
            and [s['archive'] for s in scans] == [h['row'] for h in heads], 'Archive identities differ')
    require(sel['rows'] == [s['archive'] for s in scans]
            and sel['roles'] == [s['role'] for s in scans]
            and all(sel[k] == p['selection'][k] for k in ('native_chunk_index','channel_start','channel_count','halo_channels'))
            and sel['ntime'] == 16, 'Original selected cadence/geometry differs')
    for h in heads:
        require(h['shape'] == [16,1,h['attrs']['nchans']] and h['chunks'] == [1,1,1048576]
                and h['dtype'] == 'float32' and channel+1048576 <= h['shape'][2], 'Native geometry/type differs')
    codecpath = ctx.pin(WORK/'science_root/work_az/review/review_native_az.py',pins)
    preparation = read(ctx.pin(WORK/'SCIENCE_SOURCE_PREPARATION_BE.json',pins))
    require(preparation['status'] == 'PASS' and preparation['numerical_sources_changed'] is False
            and len(preparation['source_pairs']) == 33, 'Unchanged engine preparation required')
    copied = set()
    original_engine = ctx.evidence/'work_bc/science_root/work_az'
    copied_engine = WORK/'science_root/work_az'
    parentpath = ctx.pin(preparation['parent_preparation_path'],pins,preparation['parent_preparation_sha256'])
    require(parentpath == ctx.resolve('work_bc/SCIENCE_SOURCE_PREPARATION_BC.json'), 'Wrong parent engine preparation')
    parentpairs = {ctx.resolve(pair['copied_path']):pair['sha256'] for pair in read(parentpath)['source_pairs']}
    require(len(parentpairs) == 33, 'Parent engine inventory differs')
    for pair in preparation['source_pairs']:
        original = ctx.pin(pair['original_path'],pins,pair['sha256'])
        copy = ctx.pin(pair['copied_path'],pins,pair['sha256'])
        require(pair['byte_identical'] is True and copy.is_relative_to(copied_engine)
                and original.is_relative_to(original_engine)
                and parentpairs.get(original) == pair['sha256']
                and copy.relative_to(copied_engine) == original.relative_to(original_engine)
                and original != copy and copy not in copied, 'Engine source pair invalid/duplicated')
        copied.add(copy)
    matches = [x for x in preparation['source_pairs'] if ctx.resolve(x['copied_path']) == codecpath]
    require(len(matches) == 1 and matches[0]['sha256'] == sha(codecpath) and matches[0]['byte_identical'],
            'Codec not bound to unchanged original engine')
    ctx.pin(matches[0]['original_path'],pins,matches[0]['sha256'])
    # No external numeric import occurs until all preceding actual0, review,
    # unchanged33-source and inherited evidence gates succeed.
    require(sys.flags.optimize == 0 and os.environ.get('PYTHONOPTIMIZE','') in ('','0'),
            'Unchanged native helpers require Python optimization disabled')
    sys.dont_write_bytecode = True
    sys.path.insert(0,str(WORK/'runtime'))
    import numpy as np
    import h5py
    import bitshuffle
    require((np.__version__,h5py.__version__,bitshuffle.__version__) == ('2.3.5','3.16.0','0.5.2'),
            'Pinned codec runtime differs')
    spec = importlib.util.spec_from_file_location('unchanged_native_helpers_be',codecpath)
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    codec.verify_range = lambda folder,r,allscans,actualheads,inputs,kind: provenance.verify(ctx,r,kind,scans,heads,pins)
    metadata = m['all_metadata_receipts']
    for r in metadata:
        provenance.verify(ctx,r,'retained_http_range',scans,heads,pins)
    roots = provenance.paths(ctx)
    for r in repeats:
        path = provenance.verify(ctx,r,'repeat',scans,heads,pins)
        require(path.parent == (roots['BB']/'raw_transport' if r['scan'] < 5 else roots['BE']/'transport'),
                'Five inherited repeats plus one BE repeat required')
        matches = [c for c in chunks if c['scan'] == r['scan'] and c['start'] == r['start']]
        require(len(matches) == 1 and all(matches[0][k] == r[k] for k in REPEAT_KEYS)
                and matches[0]['time_index'] == p['repeat_time_index'] == 7, 'Genuine row7 repeat differs')
    row7 = next(r for r in chunks if (r['scan'],r['time_index']) == (5,7))
    first = ctx.resolve('work_bc/acquire/transport/scan5_8154457534_8157560831.json')
    firstrecord = read(first)
    require((row7['start'],row7['stop_inclusive'],row7['bytes']) == (8154457534,8157574411,3116878)
            and row7['sha256'] == addendum['assembled_compressed_chunk_sha256_without_decode'], 'BC row7 derived union differs')
    prefix,*tail = row7['coverage_segments']
    require(ctx.resolve(prefix['source_receipt']['receipt_relative_path']) == first
            and prefix['output_offset'] == 0 and prefix['source_start'] == 8154457534
            and prefix['source_stop'] == 8157560831 and prefix['length'] == 3103298
            and prefix['source_receipt']['sha256'] == firstrecord['sha256'], 'BC prefix is not its original genuine range')
    require(sum(s['length'] for s in tail) == 13580 and all(
            ctx.resolve(s['source_receipt']['receipt_relative_path']).is_relative_to(roots['BB']) for s in tail),
            'BC row7 tail is not exact inherited BB contact')
    oldpartial = ctx.pin(bb['partial_summary']['scan5_partial_array_path'],pins,
                         bb['partial_summary']['scan5_partial_array_sha256'])
    bcpartial = ctx.pin(bc['partial_summary']['scan5_partial_array_path'],pins,
                        bc['partial_summary']['scan5_partial_array_sha256'])
    require(referenced(ctx,m,'prior_BB_partial_array',pins) == oldpartial
            and referenced(ctx,m,'prior_BC_partial_array',pins) == bcpartial,
            'Manifest retained partial-array lineage differs from original proofs')
    oldraw = np.load(oldpartial,mmap_mode='r',allow_pickle=False)
    bcraw = np.load(bcpartial,mmap_mode='r',allow_pickle=False)
    require(oldraw.shape == bcraw.shape == (16,1048576) and oldraw.dtype == bcraw.dtype == np.dtype('<f4'),
            'Partial allocation shape/type differs')
    prior_bc = {r['time_index']:r for r in bc['scan5_valid_row_reports']}
    require(set(prior_bc) == set(range(8)), 'Eight prior valid scan5 rows required')
    reports,nodes = [],[]
    for s in scans:
        j=s['scan']
        descriptorpath = ctx.pin(m['descriptor_header_paths'][j],pins)
        descriptor = read(descriptorpath)
        require(descriptor['scan'] == j and descriptor['archive'] == s['archive']
                and descriptor['shape'] == heads[j]['shape'] and descriptor['attrs'] == s['sigproc'] == heads[j]['attrs']
                and descriptor['etag'] == heads[j]['etag'], 'Descriptor header identity differs')
        require(len(descriptor['chunks']) == 16 and sorted(c['time_index'] for c in descriptor['chunks']) == list(range(16)),
                '16 selected descriptors required')
        checked,used = codec.audit_chunk_index(None,{**s,'_scans':scans},descriptor,heads,metadata,pins,channel,p['hdf_chunk_index_model'])
        require(checked == 16,'TREE proof does not cover all16 rows')
        nodes.append({'scan':j,'nodes':used})
        array = ctx.pin(s['array_relative_path'],pins,s['array_sha256'])
        expected = roots['BB']/f'data/scan{j}.npy' if j < 5 else roots['BE']/'data/scan5.npy'
        require(array == expected, 'Canonical array path differs')
        oldreport = bb['scan_reports'][j]
        require(oldreport['scan'] == j,'BB report scan differs')
        if j < 5:
            require(sha(array) == oldreport['array_file_sha256'] and oldreport['canonical_complete'],
                    'Inherited canonical array changed')
        raw = np.load(array,mmap_mode='r',allow_pickle=False)
        require(raw.shape == (16,1048576) and raw.dtype == np.dtype('<f4'), 'Canonical array shape/type differs')
        power,rows = hashlib.sha256(),[]
        for c in sorted(descriptor['chunks'],key=lambda x:x['time_index']):
            t=c['time_index']
            require(c['scan'] == j and c['filter_mask'] == 0 and c['chunk_offset'] == [t,0,channel]
                    and c['etag'] == heads[j]['etag'], 'Selected descriptor coordinate/filter/ETag differs')
            matches=[r for r in chunks if (r['scan'],r['time_index'],r['start']) == (j,t,c['byte_offset'])]
            require(len(matches) == 1, 'Selected descriptor has no unique derived chunk')
            r=matches[0]
            require(r['bytes'] == c['size'] and r['stop_inclusive'] == c['byte_offset']+c['size']-1,
                    'Descriptor byte extent differs')
            payload=provenance.verify(ctx,r,'payload',scans,heads,pins).read_bytes()
            decoded,_=codec.decode_payload(payload,1048576)
            data=decoded.tobytes(order='C');digest=hashlib.sha256(data).hexdigest()
            require(data == raw[t].tobytes(order='C'),'Reconstructed canonical row differs')
            stage=provenance.coordinate_stage(j,t)
            if stage == 'BB':
                pr=oldreport['rows'][t]
                require(pr['time_index'] == t and pr['compressed_sha256'] == r['sha256']
                        and pr['decoded_row_sha256'] == digest and pr['exact_match'],'Original BB row proof differs')
                if j == 5:
                    require(data == oldraw[t].tobytes(order='C'),'Original seven-row partial differs')
            if j == 5 and t < 8:
                pr=prior_bc[t]
                require(pr['compressed_sha256'] == r['sha256'] and pr['decoded_row_sha256'] == digest
                        and data == bcraw[t].tobytes(order='C'), 'Prior BC eight-row partial differs')
            power.update(data)
            rows.append({'time_index':t,'compressed_sha256':r['sha256'],'decoded_sha256':digest,
                         'exact_row_match':True,'lineage':stage+'_prior' if stage != 'BE' else 'BE_recovery'})
        require(power.hexdigest() == s['array_powers_sha256'],'Canonical power hash differs')
        reports.append({'scan':j,'array_sha256':sha(array),'array_powers_sha256':power.hexdigest(),
                        'rows_reconstructed':16,'exact_array_and_power_hashes_match':True,'rows':rows})
        del raw
        print('BE_NATIVE_SCAN_VERIFIED',j,flush=True)
    del oldraw,bcraw
    ctx.verify_pins(pins)
    result={'schema':PROOF_SCHEMA,'status':'PASS','execution_mode':'PRODUCTION','proof_scope':PROOF_SCOPE,
            'completed_utc':utc(),'target':'HIP44295','primary_id':65133,
            'manifest_sha256':sha(mp),'prepower_protocol_sha256':sha(pp),'recovery_protocol_sha256':sha(rp),
            'inherited_BB_partial_proof_sha256':sha(bbpath),'inherited_BC_partial_proof_sha256':sha(bcpath),
            'original_BB_payload_actual_exit':1,'original_BC_recovery_actual_exit':1,
            'recovery_input_lineage':LINEAGE,'reconstructed_scan_count':6,'reconstructed_chunk_count':96,
            'inherited_BB_rows':87,'inherited_BC_rows':1,'inherited_rows':88,'new_native_rows_verified':8,
            'derived_chunks_verified':96,'new_repeat_receipts_checked':1,'inherited_repeat_receipts_checked':5,
            'repeat_receipts_checked':6,'scan5_prior_valid_rows_compared':8,
            'retained_HTTP_receipts_checked':len(metadata),'retained_HDF_chunk_descriptor_checks':96,
            'retained_TREE_nodes':nodes,'scans':reports,'all_exact_array_and_power_hashes_match':True,
            'input_and_source_sha256_before_after':pins,'network_requests':0,'science_recalculated':False,
            'coverage_credit_added':0,'candidate_assessment':None,'queue_advanced':False,
            'limits':'BB87+BC1 are prior contact; BE8 and one genuine row7 repeat complete acquisition only. Shared unchanged bitshuffle codec and TREE-v1 model/traversal; no independent codec/model qualification, full original-file MD5, astronomical sensitivity, global FAP, new epoch or signal-origin qualification.'}
    new(out,result)
    print('PASS_BE_NATIVE_PROOF',sha(out),flush=True)


if __name__ == '__main__':
    main()
