'use strict';
const assert=require('assert');
const {fetchFiles}=require('../scripts/radio_whole_cadence_readbatch_broker.js');
const prefix='results_radio_whole_cadence_batch_2026-09-29/live01/';

function request(n=3){
  return {repository_full_name:'andersenmartin-blip/setisearch',aggregate_response_bytes:65536,
    requests:Array.from({length:n},(_,ordinal)=>({ordinal,path:prefix+'part'+ordinal+'.txt',
      ref:'a'.repeat(40),encoding:'base64'}))};
}

(async()=>{
  let calls=0;
  global.tools={mcp__codex_apps__github_fetch_file:async args=>{
    calls++;
    if(args.path.endsWith('part1.txt'))throw new Error('retained partial failure');
    return {isError:false,structuredContent:{sha:'b'.repeat(40),encoding:'base64',
      content:'eA==\n',display_url:'discard-me',display_title:'discard-me'}};
  }};
  const partial=await fetchFiles(request());
  assert.strictEqual(calls,3);
  assert.strictEqual(partial.underlying_request_count,3);
  assert.deepStrictEqual(partial.items.map(x=>x.ordinal),[0,1,2]);
  assert.strictEqual(partial.items[1].ok,false);
  assert.strictEqual(partial.items[1].automatic_retry,false);
  assert.deepStrictEqual(Object.keys(partial.items[0].result).sort(),['content','encoding','sha']);
  assert.strictEqual(partial.items[0].result.content,'eA==');

  const duplicate=request();duplicate.requests[1].path=duplicate.requests[0].path;
  await assert.rejects(()=>fetchFiles(duplicate),/duplicate/i);
  assert.strictEqual(calls,3);

  const tiny=request(1);tiny.aggregate_response_bytes=1;
  await assert.rejects(()=>fetchFiles(tiny),/exceeded pre-dispatch reservation/i);
  assert.strictEqual(calls,4);
  process.stdout.write('4 broker risk checks passed\n');
})().catch(error=>{console.error(error);process.exit(1);});
