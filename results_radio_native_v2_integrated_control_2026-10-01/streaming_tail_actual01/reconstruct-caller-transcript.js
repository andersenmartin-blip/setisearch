'use strict';
// Evidence reconstruction only. No SDK, network, Git, native case or RNG.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const sha=data=>crypto.createHash('sha256').update(data).digest('hex');
assert(process.argv.length===4,'Usage: node reconstruct-caller-transcript.js REPOSITORY_ROOT NEW_OUTPUT_PATH');
const root=path.resolve(process.argv[2]),output=path.resolve(process.argv[3]);
const artifact=JSON.parse(fs.readFileSync(path.join(__dirname,'caller-transcript-compact-lossless.json'),'utf8'));
const control=JSON.parse(fs.readFileSync(path.join(__dirname,'prospective_control.json'),'utf8'));
for(const [name,pin]of Object.entries(control.code_pins)){
  const data=fs.readFileSync(path.join(root,name));
  assert(data.length===pin.bytes&&sha(data)===pin.sha256,'Frozen reconstruction source differs: '+name);
}
const h=require(path.join(root,'scripts/radio_native_v2_broker_host'));
const streaming=require(path.join(root,'scripts/radio_native_v2_streaming_tool_courier'));
const factory=require(path.join(root,'scripts/radio_native_v2_streaming_tail_control'));
const client=factory.makeClient(h,streaming.CAPS,{padding:control.padding});
const planned=streaming.planStreamingTail({python:control.python,
  tail_helper_path:control.scope+'/frozen-code/scripts/radio_native_v2_streaming_caller_tail.py',
  tail_helper_sha256:control.code_pins['scripts/radio_native_v2_streaming_caller_tail.py'].sha256,
  caller_tail_path:control.caller_tail_path},client,h);
assert(planned.pins.wire_sha256===artifact.plan.wire_sha256&&
  planned.pins.payload_sha256===artifact.plan.payload_sha256&&
  planned.pins.client_sha256===artifact.plan.synthetic_client_sha256,'Exact deterministic control pins differ');
const argumentsObject=Object.fromEntries(artifact.reconstruction.argument_entries.map(([key,value])=>
  [key,key==='chars'?planned.encoded+'\n':value]));
const request=JSON.stringify({tool:artifact.reconstruction.request_tool,arguments:argumentsObject});
assert(Buffer.byteLength(request)===artifact.reconstruction.expected_request_bytes&&
  sha(request)===artifact.reconstruction.expected_request_sha256,'Reconstructed full request differs');
for(const records of [artifact.result.records,artifact.result.persistence.records]){
  assert(records[1].request_json===null,'Only the two pinned omitted request fields may be restored');
  records[1].request_json=request;
}
const json=JSON.stringify(artifact.result),data=Buffer.from(json);
assert(data.length===artifact.full_result_pin.bytes&&sha(data)===artifact.full_result_pin.sha256,
  'Full original actual caller transcript differs after reconstruction');
const fd=fs.openSync(output,fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_WRONLY|fs.constants.O_NOFOLLOW,0o600);
try{fs.writeFileSync(fd,data);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
const reopened=fs.readFileSync(output);
assert(reopened.length===data.length&&sha(reopened)===artifact.full_result_pin.sha256,'Independent file reopen differs');
process.stdout.write(JSON.stringify({schema:'radio-native-v2-streaming-actual-lossless-reconstruction-v1',
  status:'PASSED',bytes:reopened.length,sha256:sha(reopened),restored_request_bytes:Buffer.byteLength(request),
  restored_request_sha256:sha(request),raw_actual_reply_envelopes_retained:true,
  all_original_result_fields_and_property_order_restored:true,new_case_executions:0,
  actual_sdk_calls:0,network_fetches:0,rng_draws:0,telescope_reads:0,automatic_retry:false})+'\n');
