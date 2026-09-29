// Prospective engineering broker. Mutations remain sequential in the worker.
const repo='andersenmartin-blip/setisearch';
const prefix='results_radio_whole_cadence_batch_2026-09-29/live01/';
const maxFiles=8,maxAggregateBytes=8*1024*1024;

function validateBatch(params){
  if(params.repository_full_name!==repo||!Array.isArray(params.requests)||
     params.requests.length<1||params.requests.length>maxFiles||
     !Number.isInteger(params.aggregate_response_bytes)||
     params.aggregate_response_bytes<1||params.aggregate_response_bytes>maxAggregateBytes)
    throw new Error('Bounded aggregate readback request required');
  const ordinals=new Set(),paths=new Set();
  for(const row of params.requests){
    if(Object.keys(row).sort().join(',')!=='encoding,ordinal,path,ref'||
       !Number.isInteger(row.ordinal)||row.encoding!=='base64'||
       typeof row.path!=='string'||!row.path.startsWith(prefix)||
       row.path.split('/').some(x=>['','.','..'].includes(x))||
       !/^[0-9a-f]{40}$/.test(row.ref)||ordinals.has(row.ordinal)||paths.has(row.path))
      throw new Error('Unsafe or duplicate immutable readback');
    ordinals.add(row.ordinal);paths.add(row.path);
  }
  for(let i=0;i<params.requests.length;i++)if(!ordinals.has(i))throw new Error('Incomplete readback ordinals');
}

async function fetchFiles(params){
  validateBatch(params);
  const settled=await Promise.allSettled(params.requests.map(async row=>{
    const t=Date.now();
    try{
      const response=await tools.mcp__codex_apps__github_fetch_file({
        repository_full_name:repo,path:row.path,ref:row.ref,encoding:'base64'});
      if(response.isError)throw new Error('GitHub tool returned isError');
      const result=response.structuredContent;
      if(!result||typeof result!=='object')throw new Error('Structured response absent');
      return {ordinal:row.ordinal,ok:true,result,tool_milliseconds:Date.now()-t};
    }catch(error){
      return {ordinal:row.ordinal,ok:false,error:String(error),automatic_retry:false,
              tool_milliseconds:Date.now()-t};
    }
  }));
  const items=settled.map(x=>x.value).map(x=>{
    const y={...x};delete y.tool_milliseconds;return y;
  });
  const result={items,underlying_request_count:params.requests.length};
  if(JSON.stringify(result).length>params.aggregate_response_bytes)
    throw new Error('Aggregate response exceeded pre-dispatch reservation');
  return result;
}

// The live wrapper must route only `fetch_files` here and preserve its exact
// result/error frame in the existing durable FileRPC. It must never retry a
// partial batch. Exported solely for syntax/unit harnesses before live freeze.
if(typeof module!=='undefined')module.exports={validateBatch,fetchFiles};
