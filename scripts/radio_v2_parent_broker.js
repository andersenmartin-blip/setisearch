// Authorized tool-runtime broker for the fixed v2 terminal engineering archive.
const repo='andersenmartin-blip/setisearch';
const branch='m43-support-qualification';
const prefix='results_radio_v2_parent_2026-09-30/live01/';
const allowed=['fetch','fetch_file','create_blob','create_tree','create_commit','update_ref'];
const quoteShell=v=>"'"+v.replace(/'/g,"'\"'\"'")+"'";
const helper='PYTHONPATH=src:scripts python scripts/radio_v2_parent_handoff.py ';
let sequence=1, localCommands=0, rawResponseBytes=0, finished=false;
const brokerStarted=Date.now(),brokerEvents=[];
async function command(cmd,max_output_tokens=20000){
  if(++localCommands>3000)throw new Error('Frozen broker command cap exhausted');
  const r=await tools.exec_command({cmd,workdir:projectPath,max_output_tokens,yield_time_ms:1000});
  if(r.session_id)throw new Error('Unexpected asynchronous handoff command');
  if(r.exit_code!==0)throw new Error('Broker command failed: '+r.output);
  return r.output;
}
let next=JSON.parse(await command(helper+quoteShell(rpcPath)+' 1'));
while(!finished && sequence<=512){
  if(next.kind==='done'){finished=true;break;}
  if(next.kind!=='request' || next.bytes>600000)throw new Error('Bounded request required');
  let raw=next.first;
  const requestPath=rpcPath+'/request'+String(sequence).padStart(4,'0')+'.json';
  for(let offset=raw.length;offset<next.bytes;offset+=48000){
    const code='from pathlib import Path; import json; print(json.dumps(Path('+JSON.stringify(requestPath)+').read_text()['+offset+':'+(offset+48000)+']))';
    raw+=JSON.parse((await command('python -c '+quoteShell(code),50000)).trim());
  }
  if(raw.length!==next.bytes)throw new Error('Request byte frame differs');
  const {method,params,id}=JSON.parse(raw);
  if(id!==sequence || !allowed.includes(method))throw new Error('RPC method/sequence differs');
  if(method==='fetch'){
    if(!params.url.startsWith('https://api.github.com/repos/'+repo+'/git/'))throw new Error('Unsafe Git GET');
  }else if(params.repository_full_name!==repo)throw new Error('Repository differs');
  if(method==='fetch_file' && (!params.path.startsWith(prefix)||params.encoding!=='base64'||!/^[0-9a-f]{40}$/.test(params.ref)))throw new Error('Unsafe readback');
  if(method==='create_blob' && (params.encoding!=='base64'||params.content.length>349528))throw new Error('Unsafe blob bound');
  if(method==='create_tree' && (params.tree_elements.length>200||params.tree_elements.some(e=>!e.path.startsWith(prefix)||e.path.split('/').some(p=>p==='..'||p==='.'||p==='')||e.mode!=='100644'||e.type!=='blob'||'content' in e)))throw new Error('Unsafe archive tree');
  if(method==='update_ref' && (params.branch_name!==branch||params.force!==false))throw new Error('Unsafe ref update');
  let reply,toolResult;
  try{
    toolResult=await tools['mcp__codex_apps__github_'+method](params);
    const rawFrame=JSON.stringify(toolResult);rawResponseBytes+=rawFrame.length;
    if(rawResponseBytes>64*1024**2)throw new Error('Frozen complete tool-frame bound exhausted');
    await tools.apply_patch('*** Begin Patch\n*** Add File: '+rpcPath+'/tool'+String(sequence).padStart(4,'0')+'.json\n+'+rawFrame+'\n*** End Patch');
    if(toolResult.isError)throw new Error('GitHub returned isError');
    const result=method==='fetch'?JSON.parse(toolResult.structuredContent.content):toolResult.structuredContent;
    if(!result||typeof result!=='object')throw new Error('Structured response absent');
    reply={id,ok:true,result};
  }catch(error){reply={id,ok:false,error:String(error),automatic_retry:false};}
  await tools.apply_patch('*** Begin Patch\n*** Add File: '+rpcPath+'/response'+String(sequence).padStart(4,'0')+'.json.tmp\n+'+JSON.stringify(reply)+'\n*** End Patch');
  next=JSON.parse(await command(helper+quoteShell(rpcPath)+' '+sequence+' --deliver',50000));
  brokerEvents.push({sequence,method,ok:reply.ok,full_tool_frame_bytes:toolResult?JSON.stringify(toolResult).length:0});
  if(next.kind==='done'){finished=true;break;}
  if(!reply.ok)throw new Error('Worker failed to stop after failed transport');
  sequence++;
  if(sequence%20===0){notify({requests:sequence-1,raw_tool_frame_bytes:rawResponseBytes});await yield_control();}
}
if(!finished)throw new Error('Broker request cap exhausted before closure');
const summary={requests:sequence,local_handoff_commands:localCommands,complete_tool_frame_bytes:rawResponseBytes,
  broker_seconds:(Date.now()-brokerStarted)/1000,worker_result:next.result,events:brokerEvents,
  caps:{requests:512,local_commands:3000,tool_frame_bytes:64*1024**2,seconds:900},automatic_retry:false};
if(summary.broker_seconds>900)summary.broker_cap_exceeded=true;
await tools.apply_patch('*** Begin Patch\n*** Add File: '+rpcPath+'/../broker_result.json\n+'+JSON.stringify(summary)+'\n*** End Patch');
return summary;
