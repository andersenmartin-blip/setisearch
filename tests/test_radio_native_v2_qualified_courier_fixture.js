'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {streamJson}=require('../scripts/radio_native_v2_qualified_courier_fixture');
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
test('bounded scalar streaming preserves exact JSON bytes across control, Unicode and surrogate boundaries',()=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'seti-courier-json-')),destination=path.join(directory,'receipt.json');
  try{
    const boundary='a'.repeat(32767)+'\ud83d\ude80'+'b'.repeat(32767)+'\ud800'+'c'.repeat(32767)+'\udc00',
      controls='\u0000\b\t\n\f\r"\\\u001f',unicode='æøå λ 漢字 🛰️ \u2028\u2029',
      value={source:'Q0FERVQ='.repeat(524288),boundary,controls,unicode,nested:[{['x'.repeat(32767)+'🚀']:boundary},null,true,42]};
    const expected=Buffer.from(JSON.stringify(value)+'\n');
    streamJson(destination,value);const observed=fs.readFileSync(destination);
    assert.equal(observed.length,expected.length);assert.equal(hash(observed),hash(expected));
    assert.deepEqual(JSON.parse(observed),value);
    assert.throws(()=>streamJson(destination,value),/EEXIST/);
  }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
