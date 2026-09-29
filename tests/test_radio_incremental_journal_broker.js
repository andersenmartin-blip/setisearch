'use strict';
const fs=require('fs'), assert=require('assert');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
const body=fs.readFileSync('scripts/radio_incremental_journal_broker.js','utf8');
const run=new AsyncFunction('tools','notify','repoPath','rpcPath',body);
async function scenario(request,response){
  const raw=JSON.stringify({id:1,...request});let handoffs=0,calls=0,patch='';
  const tools={
    exec_command:async()=>({exit_code:0,output:JSON.stringify(++handoffs===1?
      {kind:'request',bytes:raw.length,first:raw}:{kind:'done',result:{status:'fixture'}})}),
    apply_patch:async value=>{patch=value;},
    mcp__codex_apps__github_fetch_file:async()=>{calls++;return response;},
    mcp__codex_apps__github_update_ref:async()=>{calls++;return response;}
  };
  const result=await run(tools,()=>{},'/repo','/rpc');return {result,calls,patch};
}
(async()=>{
  const good={method:'fetch_file',params:{repository_full_name:'andersenmartin-blip/setisearch',
    path:'results_radio_incremental_journal_2026-09-29/complete01/head.json',
    ref:'a'.repeat(40),encoding:'base64'}};
  const result=await scenario(good,{isError:false,structuredContent:{sha:'b'.repeat(40),
    encoding:'base64',content:'eA==\n',display_url:'discard'}});
  assert.strictEqual(result.calls,1);assert.strictEqual(result.result.requests,1);
  const delivered=JSON.parse(result.patch.split('\n').find(x=>x.startsWith('+{')).slice(1));
  assert.deepStrictEqual(delivered.result,{sha:'b'.repeat(40),encoding:'base64',content:'eA=='});
  await assert.rejects(()=>scenario({...good,params:{...good.params,path:'outside/head.json'}},{}),/Unsafe immutable/);
  await assert.rejects(()=>scenario({method:'update_ref',params:{repository_full_name:'andersenmartin-blip/setisearch',
    branch_name:'main',sha:'a'.repeat(40),force:false}},{}),/Unsafe branch/);
  const failure=await scenario(good,{isError:true});
  const error=JSON.parse(failure.patch.split('\n').find(x=>x.startsWith('+{')).slice(1));
  assert.strictEqual(failure.calls,1);assert.strictEqual(error.ok,false);assert.strictEqual(error.automatic_retry,false);
  process.stdout.write('4 new broker checks passed; async-function source syntax valid\n');
})().catch(e=>{process.stderr.write(String(e)+'\n');process.exit(1);});
