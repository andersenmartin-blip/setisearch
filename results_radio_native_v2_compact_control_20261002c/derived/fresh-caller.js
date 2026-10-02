'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');
const MIB=1024*1024,LIMITS={"calls": 64, "request_bytes": 50331648, "response_bytes": 67108864, "seconds": 600, "rss_bytes": 536870912},SCHEMA="radio-native-v2-compact-eight-input-resource-control-v1";
'use strict';
function requireNodeWorkerAdmission(role,scope,bundlePath,bundleDigest){
 const actual=[process.argv0,...process.execArgv,...process.argv.slice(1)];
 require('node:child_process').execFileSync("/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12",['-I','-S','-B','-c',"import hashlib,json,os,stat,sys\nfrom pathlib import Path\np=sys.argv[1]; wanted={'bytes': 128291, 'sha256': 'c1acc2e3f7148fecedec507d1fd8fabba8a85e1be3907945653ffd0aeaa7c5b4'}\nfd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)\ntry:\n before=os.fstat(fd)\n if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size!=wanted['bytes']:\n  raise ValueError('Exact pinned Node admission fixture required')\n raw=bytearray()\n while True:\n  block=os.read(fd,65536)\n  if not block:break\n  raw.extend(block)\n  if len(raw)>wanted['bytes']:raise ValueError('Node admission fixture exceeded pin')\n after=os.fstat(fd); named=os.stat(p,follow_symlinks=False)\n stable=lambda i:(i.st_dev,i.st_ino,i.st_size,i.st_mtime_ns,i.st_ctime_ns)\n if stable(before)!=stable(after) or stable(after)!=stable(named):raise ValueError('Node admission fixture changed')\nfinally:os.close(fd)\nif hashlib.sha256(raw).hexdigest()!=wanted['sha256']:raise ValueError('Node admission fixture source differs')\nm={'__name__':'frozen_node_admission','__file__':p}\nexec(compile(bytes(raw),p,'exec'),m)\nm['node_worker_entry'](sys.argv[2],sys.argv[3],sys.argv[4],json.loads(sys.argv[5]),json.loads(sys.argv[6]))\n",require('node:path').join(scope,'frozen-code',"scripts/radio_native_v2_compact_eight_case_resource_fixture.py"),role,bundlePath,bundleDigest,JSON.stringify(actual),JSON.stringify(process.env)],{env:{"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},maxBuffer:65536,stdio:['ignore','pipe','pipe']});
}
const ensure=(ok,message)=>{if(!ok)throw Error(message);},sha=data=>crypto.createHash('sha256').update(data).digest('hex'),
  quote=s=>"'"+s.replace(/'/g,"'\\''")+"'",delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function writeExclusive(filename,value){const fd=fs.openSync(filename,'wx',0o600);try{fs.writeFileSync(fd,typeof value==='string'?value:JSON.stringify(value,null,2)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function inventory(root){const rows=[];const visit=d=>{for(const entry of fs.readdirSync(d,{withFileTypes:true})){const filename=path.join(d,entry.name);
  if(entry.isDirectory())visit(filename);else {ensure(entry.isFile(),'Ordinary fixture entries required');const s=fs.statSync(filename);rows.push({path:path.relative(root,filename),bytes:s.size,allocated_bytes:s.blocks*512});}}};visit(root);
  return {files:rows.length,logical_bytes:rows.reduce((n,r)=>n+r.bytes,0),allocated_bytes:rows.reduce((n,r)=>n+r.allocated_bytes,0),rows};}
function procMemory(pid){const raw=fs.readFileSync('/proc/'+pid+'/status','utf8'),fields={};for(const line of raw.split('\n')){const a=line.split(':');fields[a[0]]=a.slice(1).join(':').trim();}
  return {at_epoch_ms:Date.now(),rss_bytes:Number((fields.VmRSS||'0').split(' ')[0])*1024,kernel_high_water_bytes:Number((fields.VmHWM||'0').split(' ')[0])*1024};}
function streamJson(filename,value){const fd=fs.openSync(filename,'wx',0o600);try{const put=s=>fs.writeSync(fd,s),
  string=text=>{put('"');for(let offset=0;offset<text.length;){let end=Math.min(text.length,offset+32768);
    // JSON.stringify retains paired surrogates as one Unicode code point and
    // escapes unpaired surrogates. Never split an existing pair at a boundary.
    const last=text.charCodeAt(end-1),next=text.charCodeAt(end);
    if(end<text.length&&last>=0xd800&&last<=0xdbff&&next>=0xdc00&&next<=0xdfff)end--;
    put(JSON.stringify(text.slice(offset,end)).slice(1,-1));offset=end;}put('"');},walk=v=>{
  if(typeof v==='string')string(v);
  else if(Array.isArray(v)){put('[');v.forEach((x,i)=>{if(i)put(',');walk(x);});put(']');}
  else if(v&&typeof v==='object'){put('{');Object.keys(v).forEach((k,i)=>{if(i)put(',');string(k);put(':');walk(v[k]);});put('}');}
  else put(JSON.stringify(v));};walk(value);put('\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
async function caller(scope,bundlePath,bundleDigest){
 requireNodeWorkerAdmission('caller',scope,bundlePath,bundleDigest);
  const code=path.join(scope,'frozen-code'),h=require(path.join(code,'scripts/radio_native_v2_broker_host.js')),
    c=require(path.join(code,'scripts/radio_native_v2_tool_courier_client.js')),
    q=require(path.join(code,'scripts/radio_native_v2_qualified_tool_courier.js')),
    prepared=JSON.parse(fs.readFileSync(path.join(scope,'prepared.json'),'utf8')),
    startup={cmd:'fresh offline maximum component '+prepared.control_case_identity.source_case_id,max_output_tokens:400000,yield_time_ms:30000},
    started=Date.now(),checkpoints=[],seen=[],deliveries=[],readReceipts=[],identity='node-proc:'+fs.readlinkSync('/proc/self'),session=742000+prepared.control_case_identity.case_ordinal;
  const sample=label=>{const r=process.memoryUsage();checkpoints.push({label,at_epoch_ms:Date.now(),rss_bytes:r.rss,heap_used_bytes:r.heapUsed,external_bytes:r.external});};sample('caller_entry');
  writeExclusive(path.join(scope,'caller-start.json'),{identity,pid:process.pid,proc_pid:Number(fs.readlinkSync('/proc/self')),started_at_epoch_ms:started});
  const argsFor=operation=>operation==='fetch'?{url:'https://api.github.com/repos/andersenmartin-blip/setisearch/git/ref/heads/m43-support-qualification'}:
    operation==='create_commit'?{repository_full_name:'andersenmartin-blip/setisearch',parent_sha:'a'.repeat(40),tree_sha:'b'.repeat(40),message:'Fresh offline maximum component '+prepared.control_case_identity.source_case_id}:
    {repository_full_name:'andersenmartin-blip/setisearch',branch_name:'m43-support-qualification',sha:'c'.repeat(40),force:false};
  const frame=ordinal=>({schema:c.CONTROLLER_SCHEMA,kind:'request',ordinal,tool:'mcp__codex_apps__github_'+c.CLIENT_SEQUENCE[ordinal],
    arguments:ordinal===1?null:argsFor(c.CLIENT_SEQUENCE[ordinal]),request_view:ordinal===1?prepared.request_view:null,
    reads:ordinal===1?prepared.reads:[],delivery_request_reserved_bytes:2*c.CLIENT_CORE['mcp__codex_apps__github_'+c.CLIENT_SEQUENCE[ordinal]]+
      (ordinal===1?prepared.reads.length*(2*8192+1024):0)+2*128*1024+8192,
    worker_deadline_epoch_ms:started+LIMITS.seconds*1000,deadline_ms:LIMITS.seconds*1000,automatic_retry:false});
  const output=ordinal=>({chunk_id:'offline-controller-'+ordinal,wall_time_seconds:0,session_id:session,
    original_token_count:100,output:JSON.stringify(frame(ordinal))+'\n',offline_fixture:true});
  const readByCommand=new Map(prepared.reads.map(row=>[row.arguments.cmd,row]));
  let tailCount=0,connectorOrdinal=0,deliveryOrdinal=0,sourceReads=0;
  const execLocal=args=>new Promise((resolve,reject)=>{const at=Date.now();cp.execFile(prepared.python,['-I','-S','-B',path.join(code,'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'),'--command-worker',scope,'command-'+String(readByCommand.get(args.cmd)?.ordinal??'tail'),args.cmd,bundlePath,bundleDigest],
    {encoding:'utf8',maxBuffer:2*MIB,timeout:Math.max(1,Math.min(120000,started+600000-Date.now())),env:{PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C'}},
    (error,stdout,stderr)=>{if(error)return reject(Error('Real local Python execution failed without retry: '+String(error)));ensure(stderr==='','Real local Python helper stderr must be empty');
      resolve({chunk_id:'offline-local-python-'+(readByCommand.get(args.cmd)?.ordinal??'tail'),wall_time_seconds:(Date.now()-at)/1000,
        exit_code:0,original_token_count:Math.ceil(Buffer.byteLength(stdout)/4),output:stdout,offline_fixture:true});});});
  const tools={exec_command:async args=>{
    if(args.cmd===startup.cmd){seen.push({kind:'mock_controller_start'});sample('controller_start');return output(0);}
    const plan=readByCommand.get(args.cmd);
    if(plan){ensure(JSON.stringify(args)===JSON.stringify(plan.arguments),'Frozen source reader exact arguments changed');const raw=await execLocal(args);
      sourceReads++;const json=JSON.stringify(raw);readReceipts.push({ordinal:plan.ordinal,path:plan.path,offset:plan.offset,bytes:plan.bytes,
        source_sha256:plan.source_sha256,envelope_entries:Object.entries(raw).map(([k,v])=>[k,k==='output'?null:v]),
        envelope_bytes:Buffer.byteLength(json),envelope_sha256:sha(json),output_sha256:sha(raw.output)});sample('source_read_'+plan.ordinal);return raw;}
    ensure(args.cmd.includes(quote(path.join(code,'scripts/radio_native_v2_caller_tail.py'))),'Only the pinned real tail saver may follow the fixture source readers');
    ensure(tailCount++===0,'Exactly one real local caller-tail saver; no retry');const raw=await execLocal(args);sample('tail_saved_and_reopened');return raw;
  },write_stdin:async args=>{
    ensure(args.session_id===session&&args.yield_time_ms===30000&&args.chars!=='' ,'Exact offline six-delivery shape required');
    const body=JSON.parse(args.chars);ensure(body.ordinal===deliveryOrdinal&&body.automatic_retry===false,'Exact ordered mock controller ingress required');
    ensure(body.read_descriptors.length===(deliveryOrdinal===1?prepared.reads.length:0),'Exact source extraction descriptors required');
    deliveries.push({ordinal:body.ordinal,request_bytes:Buffer.byteLength(JSON.stringify({tool:'write_stdin',arguments:args})),
      read_descriptors:body.read_descriptors,start_raw_present:body.start_raw!==null,previous_delivery_raw_present:body.previous_delivery_raw!==null});
    deliveryOrdinal++;sample('delivery_'+body.ordinal);if(deliveryOrdinal<6)return output(deliveryOrdinal);
    return {chunk_id:'offline-terminal',wall_time_seconds:0,exit_code:0,original_token_count:32,offline_fixture:true,
      output:JSON.stringify({schema:c.CONTROLLER_SCHEMA,kind:'terminal',status:'SINGLE_CASE_COMPONENT_ONLY',fixture_only:true,control_case_identity:prepared.control_case_identity})+'\n'};
  }};
  for(const tool of Object.keys(c.CLIENT_CORE))tools[tool]=async args=>{
    ensure(tool==='mcp__codex_apps__github_'+c.CLIENT_SEQUENCE[connectorOrdinal],'Exact six ordered mock connectors required');
    if(tool.endsWith('_create_tree')){ensure(args.tree_elements.length===28,'Maximum archive must contain 28 files');let bytes=0;
      for(const row of args.tree_elements){const pin=prepared.files[row.path];ensure(pin&&Buffer.byteLength(row.content)===pin.bytes&&sha(row.content)===pin.sha256,'Actual reassembled archive differs from frozen byte pins');bytes+=pin.bytes;}
      ensure(bytes===36875057,'Exact maximum 36,875,057-byte ASCII archive required');}
    const payload=tool.endsWith('_fetch')?{ref:'refs/heads/m43-support-qualification',object:{type:'commit',sha:connectorOrdinal<4?'a'.repeat(40):'c'.repeat(40)}}:
      tool.endsWith('_create_tree')?{sha:'b'.repeat(40)}:tool.endsWith('_create_commit')?{sha:'c'.repeat(40)}:{success:true};
    const raw={content:[{type:'text',text:JSON.stringify(payload)}],structuredContent:payload,_meta:{offline_fixture:true,control_case_identity:prepared.control_case_identity},isError:false};
    seen.push({kind:'mock_connector',ordinal:connectorOrdinal,tool,request_sha256:sha(JSON.stringify({tool,arguments:args})),response_sha256:sha(JSON.stringify(raw))});
    connectorOrdinal++;sample('connector_'+(connectorOrdinal-1));return raw;
  };
  const independentRss=async interval=>{
    sample('wrapper_interval_complete');writeExclusive(path.join(scope,'rss-observation-request.json'),interval);
    const deadline=Date.now()+30000;while(!fs.existsSync(path.join(scope,'rss-observation.json'))&&Date.now()<deadline)await delay(10);
    ensure(fs.existsSync(path.join(scope,'rss-observation.json')),'Independent parent procfs observation timed out');return JSON.parse(fs.readFileSync(path.join(scope,'rss-observation.json'),'utf8'));
  };
  const qualified=await q.runQualifiedToolCourier(tools,{hostLibrary:h,clientLibrary:c,python:prepared.python,startup_arguments:startup,
    tail_helper_path:path.join(code,'scripts/radio_native_v2_caller_tail.py'),tail_helper_sha256:sha(fs.readFileSync(path.join(code,'scripts/radio_native_v2_caller_tail.py'))),
    caller_tail_path:path.join(scope,'caller-tail.json'),production:false,read_actual_client_rss:independentRss,
    onProgress:event=>sample('progress_'+event.kind+'_'+(event.ordinal??''))});sample('qualified_wrapper_returned');
  // Stream each retained scalar separately so evidence writing does not add a
  // second enormous serialization of the complete client transcript.
  streamJson(path.join(scope,'caller-result.json'),{schema:SCHEMA,control_case_identity:prepared.control_case_identity,qualified,seen,deliveries,read_receipts:readReceipts});sample('full_scratch_transcript_written');
  const result={schema:SCHEMA,control_case_identity:prepared.control_case_identity,controller_terminal:qualified.client.controller_terminal,status:qualified.status,source_reads:sourceReads,mock_connector_operations:connectorOrdinal,mock_delivery_operations:deliveryOrdinal,
    real_local_tail_saver_calls:tailCount,process_memory_usage_checkpoints:checkpoints,
    process_memory_usage_peak_sampled_rss_bytes:Math.max(...checkpoints.map(r=>r.rss_bytes)),process_resource_usage_max_rss_bytes:process.resourceUsage().maxRSS*1024,
    caller_identity:identity,caller_started_at_epoch_ms:started,caller_finished_at_epoch_ms:Date.now(),elapsed_seconds:(Date.now()-started)/1000,
    combined_usage:qualified.combined_usage,tail_record:qualified.tail_record,persistence:qualified.persistence,client_rss_observation:qualified.client_rss_observation,
    client_status:qualified.client?.status,client_reason:qualified.client?.reason,read_receipts:readReceipts,deliveries,seen,
    execution_authorized:false,scientific_execution_authorized:false,automatic_retry:false};
  writeExclusive(path.join(scope,'caller-summary.json'),result);process.stdout.write(JSON.stringify({status:result.status,source_reads:sourceReads,mock_connectors:connectorOrdinal,mock_deliveries:deliveryOrdinal})+'\n');
}

if(process.argv.length!==6||process.argv[2]!=='--caller')throw Error('Exact admitted fresh caller mode required');caller(path.resolve(process.argv[3]),path.resolve(process.argv[4]),process.argv[5]).catch(error=>{process.stderr.write(String(error)+'\n');process.exitCode=1;});
