'use strict';
// Integrated, offline Publisher/Worker/source-only-helper fixture. The fake
// connector writes only the newly created local Git repository.
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process');
const assert=(ok,message)=>{if(!ok)throw Error(message);};
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function diskInventory(root) {
  const rows=[];function walk(directory){for(const entry of fs.readdirSync(directory,{withFileTypes:true})){
    const filename=path.join(directory,entry.name);if(entry.isDirectory())walk(filename);
    else if(entry.isFile()){const stat=fs.statSync(filename);rows.push({path:path.relative(root,filename),bytes:stat.size,allocated_bytes:stat.blocks*512});}
    else throw Error('Nonordinary fixture filesystem entry');}}
  walk(root);return{files:rows.length,logical_bytes:rows.reduce((sum,r)=>sum+r.bytes,0),
    allocated_bytes:rows.reduce((sum,r)=>sum+r.allocated_bytes,0),rows};
}

async function runFixture(prepared) {
  const code=prepared.code_root,transport=require(path.join(code,'scripts/radio_native_v2_local_transport.js')),
    {LocalGit}=require(path.join(code,'scripts/radio_native_v2_local_git.js')),
    {createLocalWorker}=require(path.join(code,'scripts/radio_native_v2_local_worker.js'));
  const ledger=new transport.SharedLedger(),started=Date.now(),gitEnv={PATH:'/usr/bin:/bin',LANG:'C',LC_ALL:'C',
    GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_SYSTEM:'/dev/null',GIT_CONFIG_GLOBAL:'/dev/null',
    GIT_AUTHOR_NAME:'Closed transport fixture',GIT_AUTHOR_EMAIL:'fixture@example.invalid',
    GIT_COMMITTER_NAME:'Closed transport fixture',GIT_COMMITTER_EMAIL:'fixture@example.invalid',
    GIT_AUTHOR_DATE:'2000-01-01T00:00:00Z',GIT_COMMITTER_DATE:'2000-01-01T00:00:00Z'};
  const git=(args,input=null)=>cp.execFileSync(prepared.git_path,['--no-replace-objects','-c','core.hooksPath=/dev/null',
    '-c','gc.auto=0',...args],{cwd:prepared.repository_path,env:gitEnv,input,encoding:'utf8',maxBuffer:8*1024*1024,timeout:30000}).trim();
  let head=prepared.parent,host,connectorCount=0,readCount=0,deliveryCount=0,gitProcessCount=0;
  const raw=value=>({content:[{type:'text',text:JSON.stringify(value)}],structuredContent:value,
    _meta:{offline_fixture:true},isError:false});
  const adapter=createLocalWorker({root:prepared.store_root,python:prepared.python,
    sourceRoot:path.join(code,'src'),helper:path.join(code,'scripts/radio_native_v2_local_worker_helper.py'),
    helperLaunch:prepared.helper_launch});
  const courier=async(tool,args,context)=>{
    connectorCount++;
    if(context.request_view) {
      const plan=host.prepareCourierReads(context.request_view,{python:prepared.python}),descriptors=[];
      for(const item of plan) {
        const output=transport.readRange(item.path,item.offset,item.bytes).toString('ascii');
        const envelope={chunk_id:'offline-'+item.ordinal,wall_time_seconds:0,exit_code:0,original_token_count:Math.ceil(output.length/4),output};
        descriptors.push(transport.makeReadDescriptor(envelope,{path:item.path,source_sha256:item.source_sha256,
          offset:item.offset,bytes:item.bytes}));readCount++;
      }
      await host.completeCourierReads(plan,descriptors);
    }
    let result;
    if(tool.endsWith('_fetch'))result=raw({content:JSON.stringify({ref:'refs/heads/m43-support-qualification',object:{type:'commit',sha:head}})});
    else if(tool.endsWith('_create_tree')) {
      git(['read-tree',args.base_tree_sha]);
      for(const row of args.tree_elements) {
        const blob=git(['hash-object','-w','--stdin'],row.content);
        git(['update-index','--add','--cacheinfo',row.mode+','+blob+','+row.path]);
      }
      result=raw({sha:git(['write-tree'])});
    }else if(tool.endsWith('_create_commit'))result=raw({sha:git(['commit-tree',args.tree_sha,'-p',args.parent_sha],args.message+'\n')});
    else if(tool.endsWith('_update_ref')) {
      git(['update-ref','refs/heads/'+args.branch_name,args.sha,head]);head=args.sha;result=raw({success:true});
    }else throw Error('Unknown offline connector fixture operation');
    const request=JSON.stringify({tool:'write_stdin',arguments:{session_id:1,fixture_delivery:deliveryCount}}),
      token=ledger.reserve({tool:'write_stdin',request_bytes:Buffer.byteLength(request),request_sha256:transport.sha(request),
        response_reservation:65536,label:'offline_courier_delivery'});
    ledger.complete(token,{output:'offline connector reply delivered',exit_code:0});deliveryCount++;
    return result;
  };
  const runGit=async(kind,plan,left)=>{
    gitProcessCount++;const at=Date.now();
    if(kind==='git_fetch') {
      // The candidate's objects are created in this same isolated repository.
      // A local existence check exercises this fixture stage; no network fetch.
      git(['cat-file','-e',plan.args.at(-1)]);return{exit_code:0,output:'offline candidate objects already local',wall_time_seconds:(Date.now()-at)/1000};
    }
    assert(kind==='git_cat_file_batch','Known offline Git process stage');
    const fd=fs.openSync(plan.stdout_path,'wx',0o600);
    try {
      const child=cp.spawnSync(plan.executable,plan.args,{cwd:plan.cwd,env:gitEnv,input:plan.stdin_text,
        stdio:['pipe',fd,'pipe'],encoding:'utf8',timeout:Math.max(1,Math.floor(left)),maxBuffer:1024*1024});
      assert(child.status===0&&!child.error,'Exact local Git batch failed');fs.fsyncSync(fd);
    }finally{fs.closeSync(fd);}
    const dir=fs.openSync(path.dirname(plan.stdout_path),'r');try{fs.fsyncSync(dir);}finally{fs.closeSync(dir);}
    return{exit_code:0,output:'offline raw Git batch durably spooled',wall_time_seconds:(Date.now()-at)/1000};
  };
  host=transport.createLocalBrokerHost({repoPath:prepared.repository_path,spoolRoot:prepared.spool_root,
    gitPath:prepared.git_path,fixture_namespace:transport.FIXTURE_PREFIX,ledger,
    localGit:new LocalGit({repoPath:prepared.repository_path,gitPath:prepared.git_path}),courier,
    persistRaw:adapter.persistRaw,persistRawBatch:adapter.persistRawBatch,
    persistRawBatchLazy:adapter.persistRawBatchLazy,persistRequestViewRaw:adapter.persistRequestViewRaw,
    groupedGitReadback:adapter.groupedGitReadback,runGit});
  const launch=prepared.worker_launch,worker=cp.spawn(launch.executable,launch.args,{cwd:code,env:launch.env,stdio:['ignore','pipe','pipe']});
  let stdout='',stderr='',done=false,exitCode=null,serviceError=null,serviced=0;
  worker.stdout.on('data',data=>{stdout+=data;assert(Buffer.byteLength(stdout)<=1024*1024,'Bounded fixture Worker output');});
  worker.stderr.on('data',data=>{stderr+=data;assert(Buffer.byteLength(stderr)<=65536,'Bounded fixture Worker error');});
  worker.on('close',value=>{exitCode=value;done=true;});
  const end=Date.now()+120000;
  while(!done&&Date.now()<end) {
    try {const receipt=await adapter.serviceOne(host);if(receipt.serviced)serviced++;}
    catch(error){serviceError=String(error);break;}
    await delay(5);
  }
  if(!done) {
    const grace=Date.now()+32000;while(!done&&Date.now()<grace)await delay(20);
    if(!done){worker.kill('SIGKILL');while(!done)await delay(10);}
  }
  let pythonResult=null;
  if(fs.existsSync(path.join(prepared.fixture_root,'python-result.json')))
    pythonResult=JSON.parse(fs.readFileSync(path.join(prepared.fixture_root,'python-result.json'),'utf8'));
  const result={schema:'radio-native-v2-integrated-local-transport-capacity-v1',mode:'OFFLINE_ONLY',
    status:pythonResult?.status==='PASSED'&&!serviceError&&exitCode===0?'PASSED':'STOPPED',
    source_bytes_per_case:prepared.source_bytes,payload_mode:prepared.payload_mode,requested_cases:prepared.cases,completed_cases:pythonResult?.completed_cases||0,
    python_result:pythonResult,service_error:serviceError,worker_exit_code:exitCode,worker_stderr:stderr,
    serviced_worker_requests:serviced,connector_fixture_operations:connectorCount,
    courier_read_fixture_operations:readCount,courier_delivery_fixture_operations:deliveryCount,
    explicit_git_fixture_operations:gitProcessCount,host_usage:host.usage(),host_state:host.state(),
    local_worker_usage:adapter.usage(),local_worker_state:adapter.state(),
    node_peak_rss_bytes:process.resourceUsage().maxRSS*1024,elapsed_seconds:(Date.now()-started)/1000,
    storage:diskInventory(prepared.fixture_root),
    simulated_tool_envelopes:true,actual_functions_tool_calls:0,network_fetches:0,
    automatic_retry:false,execution_authorized:false,scientific_execution_authorized:false,
    rng_draws:0,telescope_reads:0,native_case_reservations:0,public_mutations:0,
    limitations:['Source-only Python policy; complete native runtime/public freeze authority unqualified',
      'Local simulated connector/courier envelopes; actual tool timing is separately required',
      'Local candidate existence check stands in for both network Git fetch stages']};
  const destination=path.join(prepared.fixture_root,'node-result.json');
  fs.writeFileSync(destination,JSON.stringify(result,null,2)+'\n',{flag:'wx'});return result;
}
module.exports={runFixture,diskInventory};
if(require.main===module) {
  assert(process.argv.length===3,'Usage: node radio_native_v2_local_transport_fixture.js prepared.json');
  process.stdout.write(JSON.stringify({schema:'radio-native-v2-fixture-process-identity-v1',
    proc_pid:Number(fs.readlinkSync('/proc/self'))})+'\n');
  runFixture(JSON.parse(fs.readFileSync(process.argv[2],'utf8'))).then(result=>process.stdout.write(JSON.stringify({
    status:result.status,completed_cases:result.completed_cases,elapsed_seconds:result.elapsed_seconds,
    result_path:path.join(JSON.parse(fs.readFileSync(process.argv[2],'utf8')).fixture_root,'node-result.json')})+'\n'))
    .catch(error=>{process.stderr.write(String(error)+'\n');process.exitCode=1;});
}
