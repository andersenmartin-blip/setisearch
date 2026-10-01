'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),
  path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const h=require('../scripts/radio_native_v2_broker_host'),client=require('../scripts/radio_native_v2_tool_courier_client'),
  wrapper=require('../scripts/radio_native_v2_streaming_tool_courier');
const ROOT=path.resolve(__dirname,'..'),HELPER=path.join(ROOT,'scripts/radio_native_v2_streaming_caller_tail.py'),
  PYTHON='/usr/bin/python3',HELPER_SHA=crypto.createHash('sha256').update(fs.readFileSync(HELPER)).digest('hex'),
  REPO='andersenmartin-blip/setisearch',BRANCH='m43-support-qualification',SHA='a'.repeat(40),
  startup={cmd:'offline two-call controller fixture',max_output_tokens:400000,yield_time_ms:30000};
const DRIVER=`import json,os,pty,signal,subprocess,sys
master,slave=pty.openpty()
p=subprocess.Popen(['/bin/bash','-c',sys.argv[1]],stdin=slave,stdout=slave,stderr=slave)
os.close(slave)
def cleanup(*args):
 if p.poll() is None: p.kill(); p.wait()
 sys.exit(1)
signal.signal(signal.SIGTERM,cleanup)
def frame():
 data=b''
 while b'\\n' not in data:
  data+=os.read(master,65536)
  if len(data)>8192: raise ValueError('unexpected PTY input echo or oversized reply')
 return data.decode()
print(json.dumps({'output':frame(),'pid':p.pid}),flush=True)
for line in sys.stdin:
 chars=json.loads(line)['chars'].encode(); offset=0
 while offset<len(chars): offset+=os.write(master,chars[offset:])
 output=frame(); code=p.wait(timeout=30)
 print(json.dumps({'output':output,'exit_code':code}),flush=True)
 break
os.close(master)
`;
function actualPtyBridge(cmd){
  const process=cp.spawn(PYTHON,['-u','-c',DRIVER,cmd],{stdio:['pipe','pipe','pipe']});
  let buffer='',stderr='';const queue=[],waiters=[];
  process.stdout.on('data',data=>{buffer+=data.toString();let index;
    while((index=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,index);buffer=buffer.slice(index+1);
      const value=JSON.parse(line);if(waiters.length)waiters.shift().resolve(value);else queue.push(value);}});
  process.stderr.on('data',data=>{stderr+=data.toString();});
  process.on('exit',code=>{if(code!==0)for(const waiter of waiters.splice(0))waiter.reject(Error('PTY bridge failed: '+stderr));});
  return {process,next:()=>queue.length?Promise.resolve(queue.shift()):new Promise((resolve,reject)=>waiters.push({resolve,reject})),
    transfer:chars=>new Promise((resolve,reject)=>process.stdin.write(JSON.stringify({chars})+'\n',error=>error?reject(error):resolve()))};
}
function argsFor(operation){
  if(operation==='fetch')return {url:'https://api.github.com/repos/'+REPO+'/git/ref/heads/'+BRANCH};
  if(operation==='create_tree')return {repository_full_name:REPO,base_tree_sha:SHA,tree_elements:[{content:'fixture',mode:'100644',path:'f',type:'blob'}]};
  if(operation==='create_commit')return {repository_full_name:REPO,parent_sha:SHA,tree_sha:SHA,message:'offline'};
  return {repository_full_name:REPO,branch_name:BRANCH,sha:SHA,force:false};
}
function fixture({idle=true,padding='\\"'.repeat(30000)}={}){
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'streaming-tail-')),seen=[],bridges=[];let pending=null;
  const packets=client.CLIENT_SEQUENCE.map((op,ordinal)=>({schema:client.CONTROLLER_SCHEMA,kind:'request',ordinal,
    tool:'mcp__codex_apps__github_'+op,arguments:argsFor(op),request_view:null,reads:[],
    delivery_request_reserved_bytes:1024*1024,deadline_ms:30000,automatic_retry:false}));
  const raw=output=>({session_id:7,output,padding,wall_time_seconds:0.1,chunk_id:'component'});
  const tools={exec_command:async args=>{
    seen.push(['exec_command',args]);
    if(args.cmd===startup.cmd){if(idle){pending=packets[0];return {session_id:7,output:''};}
      return {session_id:7,output:JSON.stringify(packets[0])+'\n'};}
    assert.equal(args.tty,true);assert.equal(args.yield_time_ms,1000);
    const bridge=actualPtyBridge(args.cmd);bridges.push(bridge);const ready=await bridge.next();
    return {session_id:88,output:ready.output,wall_time_seconds:0.01,chunk_id:'actual-pty-ready'};
  },write_stdin:async args=>{
    seen.push(['write_stdin',args]);
    if(args.session_id===88){assert.equal(args.yield_time_ms,30000);const bridge=bridges.at(-1);
      await bridge.transfer(args.chars);const final=await bridge.next();
      return {exit_code:final.exit_code,output:final.output,wall_time_seconds:0.01,chunk_id:'actual-pty-readback'};}
    assert.equal(args.session_id,7);assert.equal(args.yield_time_ms,30000);
    if(args.chars===''){const packet=pending;pending=null;return raw(JSON.stringify(packet)+'\n');}
    const body=JSON.parse(args.chars);
    if(body.ordinal===5)return {exit_code:0,output:JSON.stringify({schema:client.CONTROLLER_SCHEMA,kind:'terminal',
      status:'SINGLE_CASE_COMPONENT_ONLY'})+'\n',padding:'\x7f'.repeat(30000)};
    if(idle){pending=packets[body.ordinal+1];return {session_id:7,output:''};}
    return {session_id:7,output:JSON.stringify(packets[body.ordinal+1])+'\n'};
  }};
  for(const name of Object.keys(client.CLIENT_CORE))tools[name]=async args=>{seen.push([name,args]);
    return {structuredContent:{sha:SHA},content:[{type:'text',text:'offline transport fixture'}]};};
  const options={hostLibrary:h,clientLibrary:client,startup_arguments:startup,python:PYTHON,
    tail_helper_path:HELPER,tail_helper_sha256:HELPER_SHA,caller_tail_path:path.join(directory,'tail.json')};
  return {tools,options,seen,directory,cleanup:()=>{for(const bridge of bridges)if(bridge.process.exitCode===null)bridge.process.kill();
    fs.rmSync(directory,{recursive:true,force:true});}};
}
const run=(f,extra={})=>wrapper.runStreamingToolCourier(f.tools,{...f.options,...extra});

test('real client reserves two calls before startup and transfers a large legal tail through an actual raw PTY',async()=>{
  const f=fixture();try{
    const result=await run(f);assert.equal(result.status,'CLOSED_UNQUALIFIED',result.reason);
    assert.deepEqual(result.client.prospective_caps,wrapper.CAPS);
    assert.equal(result.client.records.filter(r=>r.kind==='actual_idle_poll').length,6);
    assert.equal(result.tail_records.length,2);
    assert.deepEqual(result.tail_records.map(r=>[r.tool,r.kind]),[['exec_command','actual_caller_tail_start'],['write_stdin','actual_caller_tail_transfer']]);
    const ready=JSON.parse(result.tail_records[0].raw_result.output);
    assert.equal(ready.stdin_is_tty,true);assert.equal(ready.stdin_mode,'tty_raw_noecho');
    const stored=fs.readFileSync(f.options.caller_tail_path);
    assert.ok(stored.length>47616);assert.equal(stored.length,result.persistence.payload_bytes);
    assert.equal(result.persistence.stored_bytes,stored.length);
    assert.equal(result.persistence.stored_bytes_reserved,wrapper.LIMITS.canonical_bytes);
    assert.equal(result.tail_reservation.storage_kind,'host_receipt');
    assert.equal(crypto.createHash('sha256').update(stored).digest('hex'),result.persistence.payload_sha256);
    assert.equal(result.persistence.calls,2);
    assert.equal(result.persistence.request_bytes,result.tail_records.reduce((n,r)=>n+Buffer.byteLength(r.request_json),0));
    assert.equal(result.persistence.response_bytes,result.tail_records.reduce((n,r)=>n+Buffer.byteLength(r.response_json),0));
    assert.ok(result.persistence.request_bytes<=8*1024**2);
    assert.ok(result.persistence.response_bytes<=256*1024);
    assert.ok(result.combined_usage.calls<=64);
    assert.equal(result.actual_client_runtime_rss_known,false);
    assert.equal(result.receipt_storage_joined_into_host_ledger,false);
    assert.equal(result.host_custody_qualified,false);assert.equal(result.execution_authorized,false);
    const validation=cp.spawnSync(PYTHON,['-c','import json,sys; from seti_repeater import native_v2_transport_contract_radio as c; '+
      'v=json.load(sys.stdin); c.validate_client(v["client"],qualified=True); c.validate_persistence(v["persistence"],v["client"]); print("accepted")'],{
      input:JSON.stringify({client:result.client,persistence:result.persistence}),encoding:'utf8',
      env:{...process.env,PYTHONPATH:path.join(ROOT,'src')},maxBuffer:1024*1024});
    assert.equal(validation.status,0,validation.stderr);assert.equal(validation.stdout.trim(),'accepted');
  }finally{f.cleanup();}
});

test('prospective planner bounds wire separately from sixfold DEL canonical storage and never puts tail in shell argv',async()=>{
  const f=fixture({idle:true,padding:'\x7f'.repeat(120000)});try{
    const result=await run(f);assert.ok(result.persistence,result.reason);
    const plan=wrapper.planStreamingTail(f.options,result.client,h);
    assert.ok(plan.pins.payload_bytes>plan.pins.wire_bytes*4);
    assert.ok(plan.startup_arguments.cmd.length<4000);
    assert.ok(!plan.startup_arguments.cmd.includes(plan.encoded.slice(0,100)));
    assert.ok(plan.prospective_request_bytes<=8*1024**2);
    assert.equal(plan.pins.payload_bytes,fs.statSync(f.options.caller_tail_path).size);
    assert.equal(Buffer.from(wrapper.utf8Base64('Thy ☃ 🚀 \x7f'),'base64').toString(),'Thy ☃ 🚀 \x7f');
  }finally{f.cleanup();}
});

test('seventh caller poll is refused before actual SDK dispatch and no streaming helper is started',async()=>{
  const f=fixture();try{
    f.tools.exec_command=async args=>{f.seen.push(['exec_command',args]);return {session_id:7,output:''};};
    f.tools.write_stdin=async args=>{f.seen.push(['write_stdin',args]);return {session_id:7,output:''};};
    const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');
    assert.match(result.client.reason,/Seventh caller poll/);
    assert.equal(f.seen.filter(r=>r[0]==='write_stdin').length,6);
    assert.equal(f.seen.filter(r=>r[0]==='exec_command').length,1);assert.equal(result.persistence,null);
  }finally{f.cleanup();}
});

test('nonterminal transfer acknowledgement closes without a third call or retry',async()=>{
  const f=fixture({idle:false});try{
    const real=f.tools.write_stdin;let transferred=0;
    f.tools.write_stdin=async args=>{if(args.session_id===88){f.seen.push(['write_stdin',args]);transferred++;
      return {session_id:88,output:''};}return real(args);};
    const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');assert.match(result.reason,/no third call/);
    assert.equal(transferred,1);assert.equal(result.tail_records.length,2);assert.equal(result.persistence,null);
    assert.equal(result.combined_usage.unknown_response_count,0);
  }finally{f.cleanup();}
});

test('lost transfer reply stays conservatively charged and is never retried',async()=>{
  const f=fixture({idle:false});try{
    const real=f.tools.write_stdin;let transferred=0;
    f.tools.write_stdin=async args=>{if(args.session_id===88){transferred++;throw Error('streaming reply lost');}return real(args);};
    const result=await run(f);assert.equal(result.status,'CLOSED_FAILED');assert.equal(transferred,1);
    assert.equal(result.persistence,null);assert.equal(result.combined_usage.unknown_response_count,1);
    assert.equal(result.combined_usage.unknown_response_bytes,wrapper.LIMITS.transfer_response_bytes);
    assert.equal(result.automatic_retry,false);
  }finally{f.cleanup();}
});

test('oversized raw tail fails exact plan before either additional call',async()=>{
  const f=fixture({idle:false});try{
    const result=await run(f);assert.ok(result.persistence,result.reason);
    const mutated=structuredClone(result.client),last=mutated.records.filter(r=>r.kind==='actual_delivery').at(-1);
    last.response_json=JSON.stringify({output:'x'.repeat(256*1024)});last.response_bytes=Buffer.byteLength(last.response_json);
    let called=0;const failed=await wrapper.executeStreamingTail({exec_command:async()=>{called++;},write_stdin:async()=>{called++;}},f.options,mutated);
    assert.equal(failed.status,'CLOSED_FAILED');assert.match(failed.reason,/raw-envelope bounds/);assert.equal(called,0);
  }finally{f.cleanup();}
});

test('missing independent RSS in production closes before caller startup',async()=>{
  const f=fixture();try{
    const result=await run(f,{production:true});assert.equal(result.status,'CLOSED_FAILED');
    assert.match(result.reason,/RSS before startup/);assert.equal(f.seen.length,0);
  }finally{f.cleanup();}
});
