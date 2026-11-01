"""Independent bounded little-endian Cap'n Proto decoder for this sealed fixture.

Uses struct only for wire decoding, not pycapnp or the producer decoder.
Supports exactly the observed single-segment, unpacked Hit messages; fail closed
on other wire types. Field offsets follow the author's generated hit.capnp.h.
"""
from pathlib import Path
import hashlib
import json
import struct
import numpy as np

RAW_SHA = 'a272009ac00ebc4b3775e2253a1f762963e984d6c83349a3c3104e1fbdd17a08'
GIT_SHA = 'd1eb0703218be2287ec7a61a83e27e700b72271c'

def decode(raw):
    assert hashlib.sha256(raw).hexdigest() == RAW_SHA
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == GIT_SHA
    cursor = 0
    answer = []
    while cursor < len(raw):
        seg_minus_one, words = struct.unpack_from('<II', raw, cursor)
        assert seg_minus_one == 0, 'Only one-segment messages accepted'
        end = cursor + 8 + words*8
        assert end <= len(raw)
        seg = raw[cursor+8:end]
        def pointer(pos, typ):
            lo,hi=struct.unpack_from('<II',seg,pos)
            assert lo&3 == typ
            signed = struct.unpack('<i',struct.pack('<I',lo))[0] >> 2
            target = pos+8+8*signed
            assert 0 <= target <= len(seg)
            return target, hi
        def structure(pos):
            target,hi=pointer(pos,0)
            data_words, pointer_words=hi&65535,hi>>16
            assert target+8*(data_words+pointer_words) <= len(seg)
            return target,data_words,pointer_words
        def value(st,offset,fmt):
            target,data_words,_=st
            size=struct.calcsize(fmt)
            return struct.unpack_from(fmt,seg,target+offset)[0] if offset+size<=data_words*8 else 0
        def plist(st,number,code,bits):
            base,dw,pw=st
            assert number < pw
            target,hi=pointer(base+dw*8+8*number,1)
            assert hi&7==code
            count=hi>>3
            nbytes=(count*bits+7)//8
            assert target+nbytes<=len(seg)
            return seg[target:target+nbytes], count
        root=structure(0)
        assert root[1:]==(0,2)
        signal=structure(root[0]); fb=structure(root[0]+8)
        meta={name:value(fb,off,fmt) for name,off,fmt in [
            ('fch1',0,'<d'),('foff',8,'<d'),('tstart',16,'<d'),('tsamp',24,'<d'),
            ('ra',32,'<d'),('dec',40,'<d'),('telescopeId',48,'<i'),
            ('numTimesteps',52,'<i'),('numChannels',56,'<i'),
            ('coarseChannel',60,'<i'),('startChannel',64,'<i'),('beam',68,'<i')]}
        name,name_len=plist(fb,0,2,8)
        assert name[-1:]==b'\0'
        meta['sourceName']=name[:-1].decode('utf-8')
        payload,count=plist(fb,1,4,32)
        assert count==meta['numTimesteps']*meta['numChannels']
        # struct unpack decodes every sample independently; numpy only stores it.
        vals=struct.unpack('<'+str(count)+'f',payload)
        array=np.asarray(vals,dtype='<f4').reshape(meta['numTimesteps'],meta['numChannels'])
        assert array.tobytes()==payload
        ref={name:value(signal,off,fmt) for name,off,fmt in [
            ('frequency',0,'<d'),('index',8,'<i'),('driftSteps',12,'<i'),
            ('driftRate',16,'<d'),('snr',24,'<f'),('coarseChannel',28,'<i'),
            ('beam',32,'<i'),('numTimesteps',36,'<i'),('power',40,'<f'),('incoherentPower',44,'<f')]}
        answer.append({'metadata':meta,'reference':ref,'array':array,'raw_data_sha256':hashlib.sha256(payload).hexdigest(),
                       'message_start':cursor,'message_end':end,'segment_words':words})
        cursor=end
    assert cursor==len(raw)
    return answer

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('raw',type=Path);ap.add_argument('out',type=Path)
    args=ap.parse_args();rows=decode(args.raw.read_bytes())
    args.out.mkdir(parents=True,exist_ok=True)
    for i,row in enumerate(rows):
        np.save(args.out/f'independent_hit_{i}.npy',row.pop('array'),allow_pickle=False)
    (args.out/'independent_metadata.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps({'status':'PASS_INDEPENDENT_WIRE_DECODE','hits':len(rows),'samples':sum(r['metadata']['numTimesteps']*r['metadata']['numChannels'] for r in rows)}))
