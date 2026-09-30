// Real local Node -> Python CLI -> fsync/store -> worker callbacks.
// Connector/network calls, RNG and native cases are absent from these fixtures.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),
  os=require('node:os'),child=require('node:child_process'),crypto=require('node:crypto');
const h=require('../scripts/radio_native_v2_broker_host'),b=require('../scripts/radio_native_v2_host_bridge');
const repo=path.resolve(__dirname,'..'),python=process.env.CODEX_PRIMARY_RUNTIME_PYTHON || '/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python';
const hash=value=>crypto.createHash('sha256').update(value).digest('hex');
function fixture(t) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'seti-host-bridge-')),root=path.join(directory,'store'),calls=[];
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const tools={exec_command:async args=>{
    calls.push(args);const started=Date.now();
    const result=child.spawnSync('/bin/bash',['-c',args.cmd],{encoding:'utf8',maxBuffer:65536,timeout:10000});
    return {exit_code:result.status,output:result.stdout+(result.stderr||''),wall_time_seconds:(Date.now()-started)/1000};
  }};
  const adapter=b.createHostWorkerBridge({hostLibrary:h,tools,root,python,
    helper:path.join(repo,'scripts/radio_native_v2_bridge.py'),sourceRoot:path.join(repo,'src')});
  return{adapter,root,directory,calls};
}

test('real Python durable sink receives untouched Unicode connector envelope',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const request=JSON.stringify({url:'https://example.invalid/fixture'}),response=JSON.stringify({content:[{type:'text',text:'raw framing 🎯 λ'}],isError:false});
  const raw=JSON.stringify({request_json:request,response_json:response});
  const saved=await f.adapter.persistRaw({request_json:request,response_json:response,storage_json:raw});
  assert.equal(saved.stored_sha256,hash(raw));
  const status=await f.adapter.action({action:'status'}),item=JSON.parse(fs.readFileSync(path.join(f.root,'items','host_receipt-00000000','sealed.json'),'utf8'));
  assert.equal(item.bytes,Buffer.byteLength(raw));assert.equal(item.sha256,hash(raw));assert.equal(status.buckets.host_receipt.items,1);
  assert.ok(f.adapter.usage().supporting_receipt_durable_bytes>0);
});

test('real untouched Git spool is hashed before bounded base64 projection',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const archive='fixture/archive.json',data=Buffer.from('{"fixture":true}\n'),blob=crypto.createHash('sha1').update('blob '+data.length+'\0').update(data).digest('hex');
  const spool=path.join(f.directory,'case00.git-batch'),batch=Buffer.concat([Buffer.from(blob+' blob '+data.length+'\n'),data,Buffer.from('\n')]);
  fs.writeFileSync(spool,batch,{flag:'wx'});const sequence=[];
  const result=await f.adapter.groupedGitReadback({commit:'a'.repeat(40),spool_path:spool,paths:[archive],
    files:{[archive]:{bytes:data.length,sha256:hash(data),blob}},callGit:async kind=>sequence.push(kind)});
  assert.deepEqual(sequence,['git_fetch','git_cat_file_batch']);assert.equal(result.raw_git_receipt.sha256,hash(batch));
  assert.deepEqual(result.result,{[archive]:{sha:blob,content:data.toString('base64')}});
});

test('real Python worker mailbox dispatches callbacks once and persists original reply',async t=>{
  const f=fixture(t);await f.adapter.action({action:'create'});
  const program=`import json,sys\nfrom seti_repeater.native_v2_bridge_radio import Store,Worker\nfrom seti_repeater.empty_null_radio import canonical\nw=Worker(Store(sys.argv[1]),seconds=10)\nu=w.transport_usage()\np={'url':'https://example.invalid/fixture'}\nr=w.invoke('fetch',p)\ns=w.persist(0,'fetch',canonical(p),r)\nprint(json.dumps({'usage':u,'result':r,'saved':s}))\n`;
  const worker=child.spawn(python,['-B','-c',program,f.root],{env:{...process.env,PYTHONPATH:path.join(repo,'src')},stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='',done=false,exitCode;
  worker.stdout.on('data',data=>stdout+=data);worker.stderr.on('data',data=>stderr+=data);
  const completion=new Promise(resolve=>worker.on('exit',code=>{done=true;exitCode=code;resolve();}));
  t.after(()=>{if(!done)worker.kill('SIGKILL');});
  const invocations=[],fakeHost={usage:()=>({fixture:true,calls:0}),invoke:async(operation,params)=>{
    invocations.push({operation,params});return {fixture:true,sha:'b'.repeat(40)};
  }};
  const deadline=Date.now()+12000;let serviced=0;
  while(!done && Date.now()<deadline) {
    const receipt=await f.adapter.serviceOne(fakeHost);if(receipt.serviced)serviced++;
    await new Promise(resolve=>setTimeout(resolve,10));
  }
  assert.equal(done,true,'Bounded worker completion');await completion;
  assert.equal(exitCode,0,stderr);assert.equal(serviced,2);assert.equal(invocations.length,1);
  const result=JSON.parse(stdout);assert.deepEqual(result.usage,{calls:0,fixture:true});
  assert.equal(result.saved.sha256,hash(h.canonical(result.result)));
  const status=await f.adapter.action({action:'status'});assert.equal(status.buckets.python_receipt.items,1);
  assert.equal(status.buckets.python_receipt.unknown_bytes,0);
  assert.equal(f.adapter.capabilityManifest().execution_authorized,false);
});
