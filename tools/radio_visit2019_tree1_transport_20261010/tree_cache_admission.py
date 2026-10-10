"""Inert authentication of TREE/type1 metadata and its separate transport history.

No HTTP, native library, payload-following or source-value API. Initial/header
completion cache is admitted by unchanged c677 loader before this extension.
"""
import hashlib
import json
import re

PLAN_SCHEMA='SETI_VISIT2019_PURE_TREE1_METADATA_PLAN_RESULT_V1'
PLAN_STATUS='INCOMPLETE_TYPED_CHUNK_INDEX_METADATA'
PLAN_EXEC_STATUS='COMPLETE_PURE_TREE1_METADATA_PLAN_CAPTURE_NO_VALUES_ADMISSION'
TREE_SCOPE_SCHEMA='SETI_VISIT2019_FIXED_TREE1_METADATA_FETCH_SCOPE_V1'
TREE_RESULT_SCHEMA='SETI_VISIT2019_FIXED_TREE1_METADATA_FETCH_RESULT_V1'
TREE_COMPLETE='COMPLETE_FIXED_TREE1_METADATA_FETCH_NO_VALUES_ADMISSION'
KINDS=('legacy_TREE1_node_header','legacy_TREE1_used_keys_and_children')
MAX_NODE_BYTES=64+48*64  # Supported entry-count bound; every actual extent derives from its cached header.


def require(test,message):
    if not test:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical_sha(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def field(cache,offset,length):
    require(type(offset) is int and type(length) is int and 0<length<=65536
            and 0<=offset<=cache['file_size']-length,'Cached metadata field bounds differ')
    cursor,end,parts=offset,offset+length,[]
    while cursor<end:
        found=next((r for r in cache['cache_ranges'] if r[0]<=cursor<r[0]+len(r[1])),None)
        require(found is not None,'Cached metadata proof has an uncovered field')
        a,raw,pin=found;stop=min(end,a+len(raw));parts.append(raw[cursor-a:stop-a]);cursor=stop
    return b''.join(parts)


def verify_evidence(value,cache):
    count=0
    if isinstance(value,dict):
        if all(k in value for k in ('offset','bytes','sha256','cache_pins')):
            raw=field(cache,value['offset'],value['bytes'])
            require(sha(raw)==value['sha256'],'Typed parent byte digest differs')
            pins=[pin for a,body,pin in cache['cache_ranges'] if a<value['offset']+value['bytes'] and value['offset']<a+len(body)]
            require(value['cache_pins']==pins,'Typed parent cache pins differ')
            if 'encoded_field_hex' in value:require(raw.hex()==value['encoded_field_hex'],'Encoded typed pointer differs')
            count+=1
        for v in value.values():count+=verify_evidence(v,cache)
    elif isinstance(value,list):
        for v in value:count+=verify_evidence(v,cache)
    return count


def input_pins(execution,loader,admitted):
    if 'input_pins' in execution:pins=execution['input_pins']
    else:
        manifest=loader.read_json(execution['input_pins_manifest_pin'],admitted)
        require(manifest['schema']=='SETI_VISIT2019_TYPED_STRUCTURE_INPUT_PINS_V1','Exact TREE input-pin manifest schema required')
        pins=manifest['input_pins']
    require(isinstance(pins,list) and 0<len(pins)<=4096,'Bounded nonempty TREE input-pin list required')
    for pin in pins:loader.read_pin(pin,admitted)


def admit_metadata_qualification(scope,admitted,loader,caches):
    entry=scope['metadata_qualification']
    qs=loader.read_json(entry['scope_pin'],admitted);q=loader.read_json(entry['result_pin'],admitted)
    qe=loader.read_json(entry['execution_pin'],admitted);loader.read_pin(entry['worker_pin'],admitted)
    require(qs['schema']=='SETI_VISIT2019_SIX_HDF_HEADER_CACHE_QUALIFICATION_SCOPE_V3'
            and qs['cache_admission']==scope['cache_admission']
            and qs['source_manifest_pin']==scope['cache_admission']['source_manifest_pin']
            and qe['cache_admission_worker_sha256']==qs['cache_admission_worker_pin']['sha256']
            and qe['typed_parser_sha256']==qs['typed_parser_pin']['sha256']
            and qe['metadata_core_sha256']==qs['metadata_core_pin']['sha256']
            and q['schema']=='SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_RESULT_V1'
            and q['status']=='PASS_SIX_HEADER_METADATA_ELIGIBILITY_ONLY'
            and qe['schema']=='SETI_VISIT2019_SIX_HEADER_METADATA_QUALIFICATION_EXECUTION_V1'
            and qe['status']=='COMPLETE_CACHE_ONLY_METADATA_QUALIFICATION_NO_VALUES_ADMISSION'
            and qe['metadata_eligibility_status']==q['status']
            and q['scope_sha256']==qe['scope_sha256']==entry['scope_pin']['sha256']
            and qe['METADATA_QUALIFICATION_RESULT_sha256']==entry['result_pin']['sha256']
            and qe['script_sha256']==q['script_sha256']==qs['script_sha256']==entry['worker_pin']['sha256']
            and q['public_freeze_commit']==qe['public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}',q['public_freeze_commit'])
            and qe['all_input_end_readbacks_exact'] is qe['resource_caps_satisfied'] is True,
            'Complete actually qualified six-header provenance required')
    require(q['HTTP_requests']==qe['HTTP_requests']==0 and q['spectral_values_read'] is qe['spectral_values_read'] is False
            and q['dataset_value_API_used'] is qe['dataset_value_API_used'] is False
            and q['chunk_index_nodes_read']==qe['chunk_index_nodes_read']==0
            and q['codec_invoked'] is qe['codec_invoked'] is False
            and len(q['sources'])==len(caches)==6,'Qualification must be cache-only before TREE traversal')
    input_pins(qe,loader,admitted)
    for record,cache in zip(q['sources'],caches):
        require(record['source_id']==cache['source_id'] and record['url']==cache['url']
                and record['ordered_index']==cache['ordered_index'] and record['etag']==cache['etag']
                and record['source_file_bytes']==cache['file_size'] and record['status']=='COMPLETE_HEADER_METADATA_ONLY'
                and record['superblock']['absolute_EOF']==cache['file_size'],'Qualified source frame/order differs')
    return q['sources']


def validate_fragment(proposal,cache,qualified):
    a,n=proposal['offset'],proposal['length'];typed=proposal['typed_object_interval_half_open'];kind=proposal['object_kind']
    require(type(a) is int and type(n) is int and 0<n<=MAX_NODE_BYTES and 0<=a<=cache['file_size']-n
            and proposal['source_id']==cache['source_id'] and proposal['range']==f'bytes={a}-{a+n-1}'
            and kind in KINDS and proposal['payload_pointer'] is False and proposal['HTTP_authorized'] is False
            and len(typed)==2 and all(type(x) is int for x in typed)
            and 0<=typed[0]<=a<a+n<=typed[1]<=cache['file_size'],'Exact bounded TREE-only fragment required')
    evidence=proposal['typed_parent_evidence'];require(verify_evidence(evidence,cache)>0,'TREE parent has no cached-byte proof')
    if kind=='legacy_TREE1_node_header':
        require(typed[1]-typed[0]==24,'TREE header object span must be24 bytes')
        require(evidence['bytes']==8 and evidence['encoded_field_hex']==field(cache,evidence['offset'],8).hex(),
                'TREE header must derive from an actual cached8-byte pointer')
        target=qualified['superblock']['base_address']+int.from_bytes(field(cache,evidence['offset'],8),'little')
        require(target==typed[0],'Cached TREE pointer does not address proposed header')
        if 'node_level' in evidence:
            h=evidence['node_header_evidence'];raw=field(cache,h['offset'],24)
            require(raw[:5]==b'TREE\x01' and 0<raw[5]<=15 and raw[5]==evidence['node_level'],
                    'Only an internal TREE node may authorize a child metadata GET')
            used=int.from_bytes(raw[6:8],'little');index=evidence['selected_child_index']
            key=evidence['selected_key_evidence']
            require(type(index) is int and 0<=index<used<=64
                    and key['offset']==h['offset']+24+48*index and key['bytes']==40
                    and evidence['offset']==key['offset']+40, 'Internal child must be its actual verified TREE pointer field')
        else:
            layout=qualified['chunk_layout']
            require(evidence['offset']==layout['pointer_field_offset']
                    and target==layout['chunk_index_root_absolute_address'],'Only qualified layout root pointer may authorize firstTREEheader')
    else:
        require(evidence['offset']==typed[0] and evidence['bytes']==24,'Used-node extent requires its own cached24-byte header')
        raw=field(cache,typed[0],24);used=int.from_bytes(raw[6:8],'little')
        require(raw[:5]==b'TREE\x01' and raw[5]<=15 and 1<=used<=64
                and evidence['node_entries_used']==used and evidence['node_used_extent_bytes']==64+48*used
                and typed[1]-typed[0]==64+48*used,'TREE used extent is not64+48*n from actual verifiedheader')
    require(all(a+n<=start or start+len(raw)<=a for start,raw,pin in cache['cache_ranges']),
            'TREE fragment overlaps already retained initial/header/index metadata')


def admit_tree_plan(scope,admitted,loader,caches):
    ps=loader.read_json(scope['planner_scope_pin'],admitted);plan=loader.read_json(scope['planner_result_pin'],admitted)
    execution=loader.read_json(scope['planner_execution_pin'],admitted)
    loader.read_pin(scope['planner_worker_pin'],admitted);loader.read_pin(scope['planner_parser_pin'],admitted)
    require(ps['schema']=='SETI_VISIT2019_TYPED_TREE1_PLAN_SCOPE_V1'
            and ps['cache_admission']==scope['cache_admission']
            and ps['tree_metadata_rounds']==scope['tree_metadata_rounds']
            and ps['metadata_qualification']==scope['metadata_qualification'], 'TREE parent cache/qualification/history lineage differs')
    require(plan['schema']==PLAN_SCHEMA and plan['status']==PLAN_STATUS
            and execution['status']==PLAN_EXEC_STATUS
            and execution['scope_sha256']==plan['scope_sha256']==scope['planner_scope_pin']['sha256']
            and execution['PLAN_RESULT_sha256']==scope['planner_result_pin']['sha256']
            and execution['script_sha256']==ps['script_sha256']==scope['planner_worker_pin']['sha256']
            and execution['parser_sha256']==ps['parser_sha256']==scope['planner_parser_pin']['sha256']
            and execution['all_input_end_readbacks_exact'] is execution['resource_caps_satisfied'] is True
            and execution['public_freeze_commit']==plan['public_freeze_commit']
            and re.fullmatch(r'[0-9a-f]{40}',plan['public_freeze_commit'])
            and plan['qualification_result_pin']==scope['metadata_qualification']['result_pin'], 'Closedclean actualTREE plan pins differ')
    require(plan['HTTP_requests']==execution['HTTP_requests']==0
            and plan['spectral_values_read'] is execution['spectral_values_read'] is False
            and plan['payload_pointer_followed'] is execution['payload_pointer_followed'] is False,
            'TREE parent may record raw descriptors but must never follow payload')
    input_pins(execution,loader,admitted)
    qualified=admit_metadata_qualification(scope,admitted,loader,caches)
    require(len(plan['sources'])==len(scope['sources'])==len(caches)==6,'Exact sixTREE sources required')
    requests=[];prior=[]
    for pin in scope['prior_attempted_request_pins']:
        record=loader.read_json(pin,admitted);interval=record['requested_interval_half_open']
        c=next((x for x in caches if x['source_id']==record['source_id']),None)
        require(c is not None and record['url']==c['url'] and record['etag']==c['etag']
                and record['source_file_bytes']==c['file_size'] and record['method']=='GET' and record['attempt']==1
                and len(interval)==2 and all(type(x) is int for x in interval)
                and 0<=interval[0]<interval[1]<=c['file_size'],'Prior attempted TREE interval identity differs')
        prior.append((c['source_id'],*interval))
    for saved,source,c,q in zip(plan['sources'],scope['sources'],caches,qualified):
        require(saved['source_id']==c['source_id'] and all(source[k]==c[k] for k in ('source_id','url','ordered_index'))
                and saved['schema']=='SETI_CACHE_ONLY_LEGACY_TREE1_MIDPOINT_PLAN_V1'
                and saved['status'] in (PLAN_STATUS,'COMPLETE_SELECTED_NATIVE_CHUNK_DESCRIPTORS_NO_VALUES_ADMISSION')
                and not saved['invalid'] and not saved['unsupported'] and saved['HTTP_requests']==0
                and saved['spectral_values_read'] is saved['payload_pointer_followed'] is False,
                'Any invalid/unsupported/nonmetadata TREE source blocks whole transport')
        require([x['proposal'] for x in source['requests']]==saved['missing_metadata_fragments'], 'Exact entire cleanTREE missing-fragment list required')
        added=0
        for request in source['requests']:
            p=request['proposal'];validate_fragment(p,c,q);a,n=p['offset'],p['length']
            require(re.fullmatch(r'R[0-9]{3}_[A-Z0-9_]+',request['request_id']),'Safe fixed TREE requestID required')
            require(all(sid!=c['source_id'] or a+n<=start or end<=a for sid,start,end in prior),'TREE GET repeats a prior attempted interval')
            require(all(old_c['source_id']!=c['source_id'] or a+n<=old_p['offset'] or old_p['offset']+old_p['length']<=a
                        for old_c,old_r,old_p in requests),'TREE requestlist fragments overlap')
            requests.append((c,request,p));added+=n
        require(len(c['cache_ranges'])+len(source['requests'])<=128
                and sum(len(raw) for a,raw,pin in c['cache_ranges'])+added<=4194304,'Finite cumulativeTREE cache bounds fail')
    require(0<len(requests)<=192 and len({r['request_id'] for c,r,p in requests})==len(requests)
            and sum(p['length'] for c,r,p in requests)==scope['limits']['application_BODY_cap_bytes']<=1048576,
            'Finite complete frozenTREE request/BODY inventory differs')
    return requests


def admit_tree_cache_history(scope,admitted,loader,caches):
    rounds=scope['tree_metadata_rounds'];require(isinstance(rounds,list) and len(rounds)<=16,'Finite separateTREE history required')
    for i,entry in enumerate(rounds):
        old_scope=loader.read_json(entry['scope_pin'],admitted);result=loader.read_json(entry['result_pin'],admitted)
        execution=loader.read_json(entry['execution_pin'],admitted)
        require(entry['expected_scope_schema']==TREE_SCOPE_SCHEMA and entry['expected_result_schema']==TREE_RESULT_SCHEMA
                and entry['expected_complete_status']==TREE_COMPLETE,'Only separateclosed TREE metadata transports admitted')
        loader.bind_closed_transport(entry,old_scope,result,execution,'FETCH_RESULT_sha256',admitted)
        require(old_scope['cache_admission']==scope['cache_admission'] and old_scope['tree_metadata_rounds']==rounds[:i]
                and old_scope['metadata_qualification']==scope['metadata_qualification'],'PriorTREE cache/history qualification differs')
        requests=admit_tree_plan(old_scope,admitted,loader,caches)
        require(len(entry['requests'])==len(result['requests'])==len(requests),'Complete priorTREE request inventory differs')
        require(result['GET_requests_attempted']==len(requests) and result['HEAD_requests_attempted']==0, 'PriorTREE request counts differ')
        for (c,requested,p),pins,saved in zip(requests,entry['requests'],result['requests']):
            require(pins['request_id']==requested['request_id'] and pins['source_id']==c['source_id'],'PriorTREE requestorder differs')
            get=loader.read_json(pins['GET_receipt_pin'],admitted)
            require(saved['request_receipt_pin']==pins['GET_receipt_pin']
                    and {k:v for k,v in saved.items() if k!='request_receipt_pin'}==get,'PriorTREE standalone/global receipt differs')
            a,n=p['offset'],p['length'];etag,size=c['etag'],c['file_size']
            require(get['request_id']==requested['request_id'] and get['source_id']==c['source_id'] and get['url']==get['final_url']==c['url']
                    and get['method']=='GET' and get['attempt']==1 and get['status']==206
                    and get['state']=='PASS_EXACT_TYPED_METADATA_FRAGMENT_RETAINED'
                    and get['offset']==a and get['original_expected_length']==n and get['requested_interval_half_open']==[a,a+n]
                    and get['etag']==etag and get['source_file_bytes']==size
                    and get['proposal_sha256']==canonical_sha(p) and get['retained_fragment']==pins['fragment_pin']
                    and get['body_bytes_returned_to_application']==get['BODY_reserved_upper_bound_bytes']==pins['fragment_pin']['bytes']==n
                    and get['request_headers']=={'Accept-Encoding':'identity','Range':f'bytes={a}-{a+n-1}','If-Match':etag}
                    and get['response_headers']['Content-Range']==f'bytes {a}-{a+n-1}/{size}'
                    and get['response_headers']['Content-Length']==str(n) and get['response_headers']['ETag']==etag,
                    'PriorTREE exact206/ETag/range/body evidence differs')
            loader.identity_encoding(get)
            raw=loader.read_pin(pins['fragment_pin'],admitted);c['cache_ranges'].append((a,raw,pins['fragment_pin']))
            c['cache_ranges'].sort(key=lambda x:x[0])
        require(result['application_BODY_bytes_received']==result['application_BODY_charged_upper_bound_bytes']
                ==sum(p['length'] for c,r,p in requests),'PriorTREE completeBODY accounting differs')
    return caches
