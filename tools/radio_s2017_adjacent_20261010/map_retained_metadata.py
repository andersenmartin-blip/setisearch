#!/usr/bin/env python3
"""Offline-only adjacent170/172 v1 TREE traversal from authenticated saved bytes.

No HTTP client, HDF5, numerical package, codec, payload file or value API exists
in this mapper. A missing metadata node is reported, never requested.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
SCANS=('epoch1_on','epoch1_off','epoch2_on','epoch2_off','epoch3_on','epoch3_off')
COUNT=1048576
NATIVES=(170,172)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw=path.read_bytes()
    return {'bytes':len(raw),'sha256':sha(raw)}


def save_new(path,value):
    with path.open('x') as handle:
        json.dump(value,handle,indent=2,allow_nan=False)
        handle.write('\n')


def require(ok,message):
    if not ok:
        raise ValueError(message)


def main():
    manifest_path=ROOT/'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
    scope_path=ROOT/'analysis/next_visit/DIRECT_MIDPOINT_METADATA_SCOPE.json'
    require(sha(manifest_path.read_bytes())=='1fd17cbf60251b77c06a2bbeb00f405b068f3d60b32b9f4cfcf39eccc4076107','Original171 manifest changed')
    require(sha(scope_path.read_bytes())=='68c4e425194c03a568642a8011e5a9ae1ba513e71e811a645e28a050ba629bca','Original direct scope changed')
    midpoint=json.loads(manifest_path.read_bytes())
    scope=json.loads(scope_path.read_bytes())
    parser_path=Path(scope['pinned_original_parser_path'])
    require(sha(parser_path.read_bytes())=='e868886941a807c5d95d14c1e7aad5597edfac389dcef98b5a522bb17f812d21','Original pure parser changed')
    for path,expected in scope['pinned_files'].items():
        require(sha(Path(path).read_bytes())==expected,'Pinned original metadata evidence changed: '+path)
    code=parser_path.read_text()
    func=next(v for v in ast.parse(code).body if isinstance(v,ast.FunctionDef) and v.name=='parse_node')
    env={'struct':struct}
    exec(compile(ast.get_source_segment(code,func),'<pinned-pure-parse_node>','exec'),env)
    parse=env['parse_node']
    pins={p.relative_to(ROOT).as_posix():pin(p) for p in (Path(__file__),manifest_path,scope_path,parser_path,
         ROOT/'analysis/next_visit/DIRECT_MAPPING_INDEPENDENT_AUDIT.json')}
    caches={}; request_count=0; cache_bytes=0
    for source in scope['sources']:
        label=source['label']
        receipt_path=ROOT/'analysis/next_visit/direct_midpoint_metadata'/label/'METADATA_MAP_RECEIPT.json'
        receipt=json.loads(receipt_path.read_bytes())
        expected=midpoint['direct_map_receipt_pins'][str(receipt_path)]
        require(sha(receipt_path.read_bytes())==expected,'Original direct receipt changed')
        require(receipt['status']=='PASS_EXACT16_MIDPOINT_CHUNK_DESCRIPTORS_METADATA_ONLY','Original direct mapping not complete')
        require(all(receipt[k]==source[k] for k in ('url','etag','source_file_bytes')),'Original direct receipt identity differs')
        pins[receipt_path.relative_to(ROOT).as_posix()]=pin(receipt_path)
        records=source['cached_header_ranges']+receipt['requests']
        cache=[]
        for record in records:
            offset,n=record['offset'],record['requested_bytes']
            headers=record['response_headers']
            require(record['state']=='PASS_EXACT_RANGE_METADATA' and record['status']==206
                and record['url']==source['url'] and record['final_url']==source['url']
                and headers.get('ETag')==source['etag']
                and headers.get('Content-Range')==f'bytes {offset}-{offset+n-1}/{source["source_file_bytes"]}'
                and headers.get('Content-Length')==str(n)
                and record['attempt']==1,'Retained metadata HTTP identity/range differs')
            path=Path(record['retained_path'])
            raw=path.read_bytes()
            require(len(raw)==n and sha(raw)==record['body_sha256'],'Retained metadata bytes changed')
            relative=path.relative_to(ROOT).as_posix()
            pins[relative]={'bytes':n,'sha256':record['body_sha256']}
            cache.append((offset,raw,relative))
        caches[label]=cache
        request_count+=len(records);cache_bytes+=sum(len(raw) for _,raw,_ in cache)
    require([s['label'] for s in midpoint['sources']]==list(SCANS),'Original chronological source order changed')
    by_native={}; missing=[]; all_ranges={label:[] for label in SCANS}; visited=set()
    for native in NATIVES:
        c0=native*COUNT
        items=[]
        for olditem in midpoint['sources']:
            item=copy.deepcopy(olditem)
            item['chunks']=[]
            source=next(s for s in scope['sources'] if s['label']==item['label'])
            for row in range(16):
                target=(row,0,c0,0)
                address,previous=source['chunk_index_root_address'],None
                traversal=[]
                for depth in range(3):
                    matches=[(base,raw,path) for base,raw,path in caches[item['label']] if base<=address and address+3136<=base+len(raw)]
                    if not matches:
                        missing.append({'scan_id':item['label'],'native_chunk_index':native,'time_row':row,'metadata_byte_offset':address,'metadata_stored_size':3136,'byte_range':f'bytes={address}-{address+3135}'})
                        break
                    base,whole,path=matches[0]
                    raw=whole[address-base:address-base+3136]
                    level,keys,coords,children=parse(raw,address,item['source_file_bytes'])
                    require(previous is None or level==previous-1,'TREE level does not descend exactly')
                    require(not any(t['address']==address for t in traversal),'Cyclic TREE metadata')
                    require(all(whole2[address-base2:address-base2+3136]==raw for base2,whole2,_ in matches),'Overlapping retained nodes differ')
                    visited.add((item['label'],address))
                    traversal.append({'address':address,'level':level,'sha256':sha(raw),'retained_metadata_path':path,'offset_in_retained_metadata':address-base})
                    choices=[i for i in range(len(children)) if coords[i]<=target<coords[i+1]]
                    require(len(choices)==1,'Ambiguous or absent target TREE interval')
                    i=choices[0]
                    if level==0:
                        require(coords[i]==target,'Exact adjacent native coordinate absent')
                        size,mask=keys[i][:2];offset=children[i]
                        require(mask==0 and 0<size<=COUNT*4 and 0<=offset<=item['source_file_bytes']-size,'Source chunk bounds or filter differs')
                        item['chunks'].append({'time_row':row,'chunk_origin':list(target[:3]),'byte_offset':offset,'stored_size':size,
                             'byte_range':f'bytes={offset}-{offset+size-1}','filter_mask':mask,'decoded_size':COUNT*4,
                             'traversal':traversal,'spectral_payload_fetched':False})
                        all_ranges[item['label']].append((offset,offset+size,native,row))
                        break
                    previous,address=level,children[i]
                else:
                    raise ValueError('Pinned TREE depth exhausted')
            items.append(item)
        by_native[str(native)]={'native_chunk_index':native,'physical_channel_interval_half_open':[c0,c0+COUNT],
            'frequency_center_limits_MHz':sorted([(midpoint['fch1_hz']+midpoint['df_hz']*c0)/1e6,(midpoint['fch1_hz']+midpoint['df_hz']*(c0+COUNT-1))/1e6]),
            'total_future_spectral_payload_bytes':sum(c['stored_size'] for item in items for c in item['chunks']),'sources':items}
    for label,ranges in all_ranges.items():
        sorted_ranges=sorted(ranges)
        require(all(a[1]<=b[0] for a,b in zip(sorted_ranges,sorted_ranges[1:])),'Adjacent native payload intervals overlap')
        olditem=next(s for s in midpoint['sources'] if s['label']==label)
        require(all(not (a<old['byte_offset']+old['stored_size'] and old['byte_offset']<b) for a,b,_,_ in ranges for old in olditem['chunks']),'New range overlaps previously opened171')
    count=sum(len(item['chunks']) for band in by_native.values() for item in band['sources'])
    receipt={'schema':'SETI_S2017_ADJACENT170_172_OFFLINE_METADATA_RECEIPT_V1',
         'status':'PASS_EXACT192_ADJACENT_DESCRIPTORS_RETAINED_METADATA_ONLY' if not missing and count==192 else 'INCOMPLETE_METADATA_NODES_ABSENT_NO_HTTP',
         'native_chunk_indices':list(NATIVES),'descriptor_count':count,'missing_metadata_ranges':missing,
         'new_metadata_HTTP_requests':0,'new_metadata_BODY_bytes':0,'new_power_HTTP_requests':0,'new_power_BODY_bytes':0,
         'spectral_values_read':False,'spectral_payload_fetched':False,'retained_metadata_requests_authenticated':request_count,
         'retained_metadata_bytes_authenticated':cache_bytes,'unique_TREE_nodes_traversed':len(visited),
         'exact_future_payload_bytes':sum(b['total_future_spectral_payload_bytes'] for b in by_native.values()),
         'code_and_metadata_pins':pins}
    save_new(HERE/'METADATA_EXTRACTION_RECEIPT.json',receipt)
    require(not missing and count==192,'Offline cache missing nodes; exact missing ranges retained in receipt')
    manifest={'schema':'SETI_S2017_ADJACENT170_172_RETAINED_METADATA_SOURCE_V1','status':'PASS_EXACT192_FROZEN_SOURCE_DESCRIPTORS_METADATA_ONLY',
         'target':midpoint['target'],'visit_id':midpoint['visit_id'],'scan_order':list(SCANS),'rows_per_scan':16,'native_chunk_channels':COUNT,
         'native_chunk_indices':list(NATIVES),'by_native_chunk':by_native,'fch1_hz':midpoint['fch1_hz'],'df_hz':midpoint['df_hz'],'tsamp_s':midpoint['tsamp_s'],
         'selection_rule':'Fixed adjacent native170 and172, one below and one above previously selected midpoint171; parent selected both before any fresh170/172 values. Prior171 results were known; this is a coverage extension, not independent blind validation.',
         'spectral_values_read':False,'spectral_payload_fetched':False,'total_future_spectral_payload_bytes':receipt['exact_future_payload_bytes'],
         'decoded_complete_chunk_bytes':192*COUNT*4,'metadata_extraction_receipt_path':'analysis/s2017_next_native/METADATA_EXTRACTION_RECEIPT.json',
         'metadata_extraction_receipt_sha256':sha((HERE/'METADATA_EXTRACTION_RECEIPT.json').read_bytes()),'code_and_metadata_pins':pins,
         'original171_source_manifest_sha256':sha(manifest_path.read_bytes()),'new_metadata_HTTP_requests':0,'new_power_HTTP_requests':0,
         'original_A_B_status':'FAIL_CLOSED_UNCHANGED','cost_DKK':0}
    save_new(HERE/'source_manifest.json',manifest)
    print(json.dumps({'status':receipt['status'],'descriptor_count':count,'new_HTTP_requests':0,
        'by_native_payload_bytes':{k:v['total_future_spectral_payload_bytes'] for k,v in by_native.items()},
        'exact_future_payload_bytes':receipt['exact_future_payload_bytes'],
        'source_manifest_sha256':sha((HERE/'source_manifest.json').read_bytes()),'receipt_sha256':sha((HERE/'METADATA_EXTRACTION_RECEIPT.json').read_bytes())}))

if __name__=='__main__':
    main()
