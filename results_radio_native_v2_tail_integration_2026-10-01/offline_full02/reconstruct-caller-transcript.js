'use strict';
// Standalone lossless OFFLINE data reconstruction. No connector, SDK, Git,
// source-reader dispatch, tail saver, scientific case or retry is invoked.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const ensure=(ok,message)=>{if(!ok)throw Error(message);},sha=data=>crypto.createHash('sha256').update(data).digest('hex');
function shaFile(filename){const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW),h=crypto.createHash('sha256'),buffer=Buffer.alloc(65536);let bytes=0;
  try{while(true){const n=fs.readSync(fd,buffer,0,buffer.length,null);if(!n)break;h.update(buffer.subarray(0,n));bytes+=n;}}finally{fs.closeSync(fd);}return {bytes,sha256:h.digest('hex')};}
function streamJson(filename,value){const fd=fs.openSync(filename,'wx',0o600);try{const put=s=>fs.writeSync(fd,s),
  string=text=>{put('"');for(let offset=0;offset<text.length;){let end=Math.min(text.length,offset+32768);
    const last=text.charCodeAt(end-1),next=text.charCodeAt(end);
    if(end<text.length&&last>=0xd800&&last<=0xdbff&&next>=0xdc00&&next<=0xdfff)end--;
    put(JSON.stringify(text.slice(offset,end)).slice(1,-1));offset=end;}put('"');},walk=v=>{
  if(typeof v==='string')string(v);
  else if(Array.isArray(v)){put('[');v.forEach((x,i)=>{if(i)put(',');walk(x);});put(']');}
  else if(v&&typeof v==='object'){put('{');Object.keys(v).forEach((k,i)=>{if(i)put(',');string(k);put(':');walk(v[k]);});put('}');}
  else put(JSON.stringify(v));};walk(value);put('\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function main(){
  ensure(process.argv.length===3||process.argv.length===4,'Usage: node reconstruct-caller-transcript.js fresh-absolute-scratch-directory [python-executable]');
  const root=path.resolve(process.argv[2]),python=process.argv[3]||process.env.CODEX_PRIMARY_RUNTIME_PYTHON||'/usr/bin/python3',started=Date.now(),
    projectionPath=path.join(__dirname,'caller-transcript-compact-lossless.json'),projection=JSON.parse(fs.readFileSync(projectionPath,'utf8')),
    recipe=path.join(__dirname,projection.regeneration.recipe_file),recipeRaw=fs.readFileSync(recipe),regeneration=projection.regeneration;
  ensure(projection.schema==='radio-native-v2-offline-lossless-caller-transcript-projection-v1'&&projection.fixture_only===true,'Pinned offline lossless projection required');
  ensure(path.isAbsolute(process.argv[2])&&!fs.existsSync(root),'Exclusive fresh absolute reconstruction scope required; no overwrite or retry');
  ensure(sha(recipeRaw)===regeneration.recipe_sha256&&recipeRaw.length===regeneration.recipe_bytes,'Exact frozen deterministic preparation recipe required');
  fs.mkdirSync(root,{mode:0o700});const data=path.join(root,'regenerated-archive');fs.mkdirSync(data,{mode:0o700});
  const prepare=cp.spawnSync(python,['-I','-S','-B',recipe,data,python],{encoding:'utf8',maxBuffer:1048576,timeout:120000,
    env:{PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C'}});
  ensure(!prepare.error&&prepare.status===0&&prepare.stdout===''&&prepare.stderr==='','Exact offline archive data recipe failed: '+String(prepare.error||prepare.stderr));
  const sourceFile=path.join(data,regeneration.regenerated_relative_source_path),sourcePin=shaFile(sourceFile),payloadPin=shaFile(path.join(data,'deterministic-source.bin')),
    prepared=JSON.parse(fs.readFileSync(path.join(data,'prepared.json'),'utf8'));
  ensure(sourcePin.bytes===regeneration.immutable_source_bytes&&sourcePin.sha256===regeneration.immutable_source_sha256,'Regenerated immutable request source bytes differ');
  ensure(payloadPin.bytes===regeneration.source_bytes&&payloadPin.sha256===regeneration.source_sha256,'Regenerated deterministic source bytes differ');
  ensure(prepared.archive_bytes===regeneration.archive_bytes&&prepared.archive_files===regeneration.archive_files,'Regenerated maximum archive layout differs');
  const transcript=projection.transcript,records=transcript.qualified.client.records,plans=new Map(regeneration.reads.map(p=>[p.ordinal,p])),
    receipts=new Map(transcript.read_receipts.map(r=>[r.ordinal,r])),fd=fs.openSync(sourceFile,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
  let sourceFields=0,envelopeFields=0,requestFields=0;
  const read=(offset,bytes)=>{const output=Buffer.alloc(bytes);let used=0;while(used<bytes){const n=fs.readSync(fd,output,used,bytes-used,offset+used);ensure(n>0,'Regenerated source range truncated');used+=n;}
    ensure(output.every(x=>x<128),'Exact immutable ASCII source range required');return output.toString('ascii');};
  try{
    for(const item of projection.large_field_replacements){const record=records[item.record_ordinal];ensure(record&&record.ordinal===item.record_ordinal,'Exact original record ordinal required');
      if(item.field==='raw_result.output'){
        const marker=record.raw_result.output,plan=plans.get(item.source_plan_ordinal);
        ensure(marker.$offline_lossless_reconstruction==='immutable_source_range'&&marker.source_plan_ordinal===plan.ordinal,'Exact removed raw source field descriptor required');
        const output=read(plan.offset,plan.bytes);ensure(sha(output)===plan.output_sha256,'Regenerated exact raw source read bytes differ');record.raw_result.output=output;sourceFields++;
      }else if(item.field==='response_json'){
        const marker=record.response_json,plan=plans.get(item.source_plan_ordinal),receipt=receipts.get(plan.ordinal);
        ensure(marker.$offline_lossless_reconstruction==='ordered_source_read_envelope'&&typeof record.raw_result.output==='string','Exact ordered removed envelope descriptor required');
        const restored={};for(const [key,value] of receipt.envelope_entries)Object.defineProperty(restored,key,{value:key==='output'?record.raw_result.output:value,enumerable:true});
        const response=JSON.stringify(restored);ensure(response===JSON.stringify(record.raw_result),'Original raw source envelope property order or metadata differs');
        ensure(Buffer.byteLength(response)===record.response_bytes&&sha(response)===record.response_sha256&&
          receipt.envelope_bytes===record.response_bytes&&receipt.envelope_sha256===record.response_sha256,'Reconstructed complete raw source envelope pin differs');
        record.response_json=response;envelopeFields++;
      }else if(item.field==='request_json'){
        const marker=record.request_json,view=regeneration.request_view;ensure(marker.$offline_lossless_reconstruction==='immutable_create_tree_request_view','Exact removed connector request descriptor required');
        const request=view.request_prefix+read(view.offset,view.bytes)+view.request_suffix;
        ensure(Buffer.byteLength(request)===record.request_bytes&&sha(request)===record.request_sha256&&record.request_sha256===view.request_sha256,'Reconstructed complete create_tree request pin differs');
        record.request_json=request;requestFields++;
      }else throw Error('Unknown lossless field reconstruction refused');
    }
  }finally{fs.closeSync(fd);}
  ensure(sourceFields===regeneration.reads.length&&envelopeFields===sourceFields&&requestFields===1,'Exact complete large field reconstruction required');
  const destination=path.join(root,'caller-result-reconstructed.json');streamJson(destination,transcript);const restoredPin=shaFile(destination),expected=projection.original_full_transcript;
  ensure(restoredPin.bytes===expected.bytes&&restoredPin.sha256===expected.sha256,'Entire original caller transcript file bytes/hash differ after reconstruction');
  const audit={schema:'radio-native-v2-offline-lossless-transcript-reconstruction-audit-v1',status:'PASSED',
    projection_sha256:sha(fs.readFileSync(projectionPath)),projection_bytes:fs.statSync(projectionPath).size,recipe_sha256:sha(recipeRaw),
    reconstruction_helper_sha256:sha(fs.readFileSync(__filename)),original_full_transcript:expected,
    reconstructed_full_transcript:{...restoredPin,path:destination},regenerated_request_source:sourcePin,regenerated_deterministic_source:payloadPin,
    restored_source_output_fields:sourceFields,restored_complete_raw_response_json_fields:envelopeFields,restored_complete_create_tree_request_fields:requestFields,
    exact_original_metadata_and_property_order_preserved:true,complete_full_file_bytecount_and_sha256_match:true,
    data_reconstruction_only:true,new_case_executions:0,actual_functions_sdk_calls:0,actual_connector_calls:0,network_fetches:0,real_public_github_mutations:0,
    native_case_reservations:0,scientific_cases_run:0,rng_draws:0,telescope_reads:0,automatic_retry:false,execution_authorized:false,
    scientific_execution_authorized:false,live_transport_qualified:false,elapsed_seconds:(Date.now()-started)/1000};
  fs.writeFileSync(path.join(root,'reconstruction-audit.json'),JSON.stringify(audit,null,2)+'\n',{flag:'wx',mode:0o600});
  process.stdout.write(JSON.stringify({status:audit.status,bytes:restoredPin.bytes,sha256:restoredPin.sha256,projection_bytes:audit.projection_bytes,audit_path:path.join(root,'reconstruction-audit.json')})+'\n');
}
try{main();}catch(error){process.stderr.write(String(error)+'\n');process.exitCode=1;}
