'use strict';
// Deterministic support-envelope factory for one separately frozen actual
// tail-transfer boundary probe. Every controller/connector/source record is
// synthetic; only the two later tail tools may be real. No RNG or science.
const SCHEMA='radio-native-v2-streaming-tail-boundary-control-v1';
const AUTHORITY=Object.freeze({execution_authorized:false,reservation_authorized:false,
  scientific_execution_authorized:false,rng_draws:0,telescope_reads:0,automatic_retry:false});
function makeClient(h,caps,{padding='backslash'}={}){
  if(!['backslash','del'].includes(padding))throw Error('Fixed arithmetic padding required');
  const limit=256*1024,records=[],sequence=['fetch','create_tree','create_commit','fetch','update_ref','fetch'];
  const terminal={schema:'radio-native-v2-local-tool-courier-v1',kind:'terminal',status:'SINGLE_CASE_COMPONENT_ONLY'};
  function append(kind,tool,{large=false,terminalFrame=false}={}){
    const ordinal=records.length,request=JSON.stringify({tool,arguments:{synthetic_ordinal:ordinal}}),
      raw={output:terminalFrame?JSON.stringify(terminal)+'\n':'',synthetic_tail_boundary:true,padding:''};
    if(large){
      const left=limit-h.utf8Bytes(JSON.stringify(raw)),char=padding==='backslash'?'\\':'\x7f';
      raw.padding=char.repeat(padding==='backslash'?Math.floor(left/2):left);
      if(h.utf8Bytes(JSON.stringify(raw))===limit-1)raw.padding+='x';
    }
    const response=JSON.stringify(raw),bytes=h.utf8Bytes(response);
    if(large&&bytes!==limit)throw Error('Exact raw supporting envelope cap required');
    records.push({ordinal,kind,tool,request_json:request,request_bytes:h.utf8Bytes(request),
      request_sha256:h.sha256(request),response_json:response,response_bytes:bytes,
      response_sha256:h.sha256(response),raw_result:raw,response_reserved_bytes:large?limit:bytes+16,
      response_unknown:false,response_charged_bytes:bytes,automatic_retry:false});
  }
  append('actual_controller_start','exec_command');
  for(let phase=0;phase<6;phase++){
    if(phase===0)for(let poll=0;poll<6;poll++)append('actual_idle_poll','write_stdin',{large:true});
    if(phase===1)for(let read=0;read<39;read++)append('actual_source_read','exec_command');
    append('actual_connector','mcp__codex_apps__github_'+sequence[phase]);
    append('actual_delivery','write_stdin',{large:phase===5,terminalFrame:phase===5});
  }
  const usage={calls:records.length,request_bytes:records.reduce((n,r)=>n+r.request_bytes,0),
    response_bytes:records.reduce((n,r)=>n+r.response_bytes,0)};
  Object.assign(usage,{response_charged_bytes:usage.response_bytes,unknown_response_bytes:0,unknown_response_count:0,
    conservatively_charged_local_git_processes:4,calls_including_declared_git_processes:records.length+4,
    elapsed_seconds:0,hidden_http_bytes_known:false,all_actual_start_poll_read_connector_delivery_calls_counted:true});
  return {schema:'radio-native-v2-single-exec-tool-courier-v1',status:'SINGLE_CASE_COMPONENT_COMPLETE',reason:null,
    prospective_caps:{...caps},usage,records,events:[],controller_terminal:terminal,connector_requests:6,
    pending_delivery_reservation:null,last_supporting_acknowledgement_durable:false,
    controller_poll_receipts_joined_into_host_ledger:false,actual_client_runtime_rss_known:false,
    ...AUTHORITY};
}
function describe(h,client,plan){
  return {schema:SCHEMA,mode:'ACTUAL_TAIL_TOOLS_WITH_SYNTHETIC_CALLER',padding:'backslash',
    synthetic_client_sha256:plan.pins.client_sha256,synthetic_support_envelopes:7,
    synthetic_support_response_bytes:7*256*1024,synthetic_source_read_count:39,
    synthetic_caller_record_count:client.records.length,
    planned_actual_tool_calls:2,request_bytes_reserved:8*1024**2,response_bytes_reserved:256*1024,
    stored_bytes_reserved:6*7*256*1024+2048,stored_items_reserved:1,
    storage_kind:'host_receipt',wire_bytes:plan.pins.wire_bytes,wire_sha256:plan.pins.wire_sha256,
    payload_bytes:plan.pins.payload_bytes,payload_sha256:plan.pins.payload_sha256,
    base64_bytes:plan.encoded.length,planned_request_bytes_bound:plan.prospective_request_bytes,
    canonical_tail_sha256:plan.pins.payload_sha256,full_client_executed:false,
    actual_client_runtime_rss_known:false,full_host_transport_qualified:false,
    receipt_storage_joined_into_host_ledger:false,live_maximum_source_control_authorized:false,
    native_case_reservations:0,network_fetches:0,public_mutations_inside_probe:0,...AUTHORITY};
}
if(typeof module!=='undefined')module.exports={SCHEMA,makeClient,describe};
