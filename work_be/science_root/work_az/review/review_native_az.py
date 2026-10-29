#!/usr/bin/env python3
"""Offline AZ native-row proof, adapted from AV exact reconstruction.

Re-decodes all96 retained bitshuffle chunks, checks every row against canonical
arrays and their full file/power hashes, independently rereads retained HDF
chunk-index metadata, and validates every metadata/payload/repeat receipt.
No network. Shared bitshuffle codec does not constitute an independent decoder.
"""
from pathlib import Path
import argparse, datetime, hashlib, io, json, os, platform, struct, sys, traceback
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(W/'work_az/runtime'))
import numpy as np
import h5py, bitshuffle

VERSION='1.2.0-az-dynamic-geometry-targeted-tree-native-row-proof'
ROWS=16; CHANNELS=1048576
TARGET='HIP92283'; PRIMARY_ID=65097
RECEIPT_KEYS=('archive_id','scan','start','stop_inclusive','bytes','content_range','sha256','etag','url','status')

def read(path):return json.loads(Path(path).read_text())
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def publish(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
def pin(path,inputs):
    path=Path(path).resolve();digest=sha(path);inputs[str(path)]=digest;return digest
def relative_file(folder,relative):
    path=(folder/relative).resolve();path.relative_to(folder)
    require(path.is_file(),'Missing retained file: '+str(relative));return path
def norm(value):
    if isinstance(value,bytes):return value.decode()
    if isinstance(value,(list,tuple)):return [norm(v) for v in value]
    return norm(value.tolist()) if hasattr(value,'tolist') else value

def decode_payload(payload,nchannels):
    # Inherited AV byte-header and codec arithmetic retained exactly.
    require(len(payload)>12,'Compressed payload has no body')
    nbytes,blockbytes=struct.unpack('>QI',payload[:12])
    require(nbytes==4*nchannels and blockbytes>0 and blockbytes%4==0,'Compressed header size/block differs')
    decoded=bitshuffle.decompress_lz4(np.frombuffer(payload[12:],dtype=np.uint8),(nchannels,),np.dtype('<f4'),block_size=blockbytes//4)
    require(decoded.shape==(nchannels,) and decoded.dtype==np.dtype('<f4'),'Decoded row shape/dtype differs')
    require(np.isfinite(decoded).all() and (decoded>=0).all(),'Decoded powers are nonfinite or negative')
    return decoded,blockbytes

def verify_range(folder,receipt,scans,headers,inputs,kind):
    j=receipt['scan'];require(isinstance(j,int) and 0<=j<6,'Invalid range scan')
    archive=scans[j]['archive'];begin,end=receipt['start'],receipt['stop_inclusive']
    require(0<=begin<=end<archive['size'],'Range outside archive')
    require(receipt['archive_id']==archive['id'] and receipt['url']==archive['url'],'Range archive identity differs')
    require(receipt['status']==206 and receipt['bytes']==end-begin+1,'Range status/length differs')
    require(receipt['content_range']==f"bytes {begin}-{end}/{archive['size']}",'Content-Range differs')
    require(receipt['etag']==headers[j]['etag'] and bool(receipt['etag']),'Range ETag differs')
    require(receipt['attempts']==1 and receipt.get('failed_attempts')==[],'Request attempts differ')
    cap=1048576 if kind=='metadata' else 8388608
    require(receipt['bytes']<=cap,'Range exceeds frozen request cap')
    suffix='.repeat' if kind=='repeat' else ''
    canonical=f'transport/scan{j}_{begin}_{end}{suffix}.bin'
    require(receipt.get('payload_relative_path',canonical)==canonical,'Retained payload path differs')
    bp=relative_file(folder,canonical)
    rp=relative_file(folder,f'transport/scan{j}_{begin}_{end}{suffix}.json')
    cached=read(rp);require(cached==receipt,'Retained receipt differs from manifest/header')
    require('kind' not in receipt or receipt['kind']==kind or kind in ('metadata','payload') and receipt['kind']=='hdf_io','Range kind differs')
    digest=pin(bp,inputs);pin(rp,inputs)
    require(bp.stat().st_size==receipt['bytes'] and digest==receipt['sha256'],'Retained range bytes/hash differ')
    return bp

class RetainedMetadata(io.RawIOBase):
    """Independent sparse, read-only HDF view, with no network fallback."""
    def __init__(self,size,spans):self.size=size;self.spans=spans;self.pos=0
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        require(0<=self.pos<=self.size,'Invalid retained metadata seek');return self.pos
    def readinto(self,buffer):
        count=min(len(buffer),max(0,self.size-self.pos))
        if not count:return 0
        start=self.pos;stop=start+count;out=bytearray(count);seen=bytearray(count)
        for begin,payload in self.spans:
            lo=max(start,begin);hi=min(stop,begin+len(payload))
            if hi<=lo:continue
            for position in range(lo,hi):
                k=position-start;value=payload[position-begin]
                require(not seen[k] or out[k]==value,'Conflicting retained metadata overlap')
                out[k]=value;seen[k]=1
        require(all(seen),f'Unretained metadata range {start}:{stop}; network forbidden')
        buffer[:count]=out;self.pos=stop;return count

def audit_chunk_index(folder,scan,header,actual,metadata_receipts,inputs,channel_start,index_model):
    """Independent HDF v1 TREE traversal; no whole-index HDF enumeration."""
    j=scan['scan'];spans=[];total=scan['archive']['size'];nodes={};used={}
    root=index_model['root_address'];levels=index_model['levels']
    for receipt in metadata_receipts:
        if receipt['scan']==j:
            bp=verify_range(folder,receipt,scan['_scans'],actual,inputs,'metadata')
            spans.append((receipt['start'],bp.read_bytes()))
    require(spans,'No retained metadata for chunk index')
    cache=RetainedMetadata(total,spans)
    def get(address,length):
        require(0<=address and 0<length<=3136 and address+length<=total,'Invalid TREE metadata extent')
        cache.seek(address);payload=cache.read(length)
        require(len(payload)==length,'Short retained TREE metadata read');return payload
    def node(address,expected_level):
        if address in nodes:
            require(nodes[address]['level']==expected_level,'TREE node level reused inconsistently')
            return nodes[address]
        h=get(address,24)
        require(h[:4]==b'TREE' and h[4]==1 and h[5]==expected_level,'TREE signature/type/level differs')
        n=struct.unpack_from('<H',h,6)[0];require(1<=n<=64,'TREE entry count outside inherited model')
        length=40+n*48;body=get(address+24,length);keys=[];pointers=[]
        for i in range(n+1):
            size,mask,*coord=struct.unpack_from('<II4Q',body,i*48)
            keys.append(dict(size=size,mask=mask,coord=tuple(coord)))
            if i<n:pointers.append(struct.unpack_from('<Q',body,i*48+40)[0])
        require(all(keys[i]['coord']<keys[i+1]['coord'] for i in range(n)),'TREE coordinate keys not strictly increasing')
        used[address]=dict(address=address,level=expected_level,nentries=n,used_bytes=24+length,sha256=hashlib.sha256(h+body).hexdigest())
        result=dict(address=address,level=expected_level,nentries=n,keys=keys,pointers=pointers);nodes[address]=result;return result
    for chunk in sorted(header['chunks'],key=lambda item:item['time_index']):
        row=chunk['time_index'];target=(row,0,channel_start,0);address=root;visited=set()
        for level in levels:
            require(address not in visited and 0<=address and address+24<=total,'TREE cycle or out-of-file node');visited.add(address)
            branch=node(address,level)
            choices=[i for i in range(branch['nentries']) if branch['keys'][i]['coord']<=target<branch['keys'][i+1]['coord']]
            require(len(choices)==1,'TREE target lacks unique containing key interval')
            i=choices[0];pointer=branch['pointers'][i]
            if level:
                require(pointer not in visited and 0<=pointer and pointer+24<=total,'TREE child pointer invalid');address=pointer;continue
            key=branch['keys'][i]
            require(key['coord']==target and key['mask']==0 and 0<key['size']<=8388608 and 0<=pointer and pointer+key['size']<=total,'TREE leaf chunk descriptor invalid')
            require(pointer==chunk['byte_offset'] and key['size']==chunk['size'],'Independent TREE chunk pointer/size differs')
            require(key['mask']==chunk['filter_mask'] and list(key['coord'][:3])==chunk['chunk_offset']==[row,0,channel_start],'Independent TREE chunk coordinates/filter differs')
    return len(header['chunks']),list(used.values())

def audit(folder,protocol):
    folder=Path(folder).resolve();protocol=Path(protocol).resolve();p=read(protocol);inputs={}
    pin(protocol,inputs);pin(__file__,inputs)
    require(p['target']==TARGET and p['primary_id']==PRIMARY_ID,'Prospective target differs')
    config=p['selection'];channel_start=config['channel_start'];chunk_index=config['native_chunk_index']
    require(isinstance(chunk_index,int) and chunk_index>=0 and channel_start==chunk_index*CHANNELS,'Prospective chunk index/start differs')
    require('hdf_chunk_index_model' in p,'Explicit prepower HDF chunk-index model required')
    index_model=p['hdf_chunk_index_model']
    require(isinstance(index_model['root_address'],int) and index_model['root_address']>=0 and index_model['levels']==[2,1,0] and index_model.get('node_type',1)==1 and index_model.get('max_node_entries',64)==64,'Unsupported prospective TREE-v1 model')
    catalog_path=W/'work_az/catalog/entry.json'
    require(p['source_sha256'].get('work_az/catalog/entry.json')==pin(catalog_path,inputs),'Catalog entry not pinned before powers')
    catalog=read(catalog_path);catalog_rows=catalog['rows'];ids=[r['id'] for r in catalog_rows]
    require(catalog['target']==TARGET and catalog['id']==PRIMARY_ID and len(catalog_rows)==6 and len(set(ids))==6 and ids[0]==PRIMARY_ID,'Catalog target/identities differ')
    require(catalog.get('sequence')==['ON','OFF']*3 and catalog.get('metadata_pass') is True,'Catalog geometry/order not qualified')
    require(np.__version__=='2.3.5' and bitshuffle.__version__=='0.5.2' and h5py.__version__=='3.16.0','Pinned codec runtime differs')
    for relative,digest in p['source_sha256'].items():
        source=Path(relative);require(not source.is_absolute() and '..' not in source.parts,'Unsafe source pin')
        require(pin(W/source,inputs)==digest,'Prospective source pin differs: '+relative)
    require(config==dict(native_chunk_index=chunk_index,channel_start=channel_start,channel_count=CHANNELS,halo_channels=4096),'Prospective native geometry differs')
    paths={name:relative_file(folder,relative) for name,relative in [('manifest','data/pilot_manifest.json'),('marker','ACQUISITION_COMPLETE.json'),('selection','selection_frozen.json'),('actual','actual_headers_result.json')]}
    for path in paths.values():pin(path,inputs)
    manifest,marker,selection,actual=(read(paths[name]) for name in ('manifest','marker','selection','actual'))
    manifest_hash=sha(paths['manifest']);protocol_hash=sha(protocol)
    require(manifest['schema']=='HDF5_EXACT_RANGE_SIX_SCAN_V1' and manifest['target']==TARGET,'Manifest schema/target differs')
    require(marker['status']=='PASS' and (marker['scans'],marker['chunks'],marker['fresh_repeats'])==(6,96,6),'Acquisition marker incomplete')
    require(marker['manifest_sha256']==manifest_hash and marker['protocol_sha256']==manifest['protocol_sha256']==protocol_hash,'Acquisition protocol/manifest binding differs')
    require(manifest['selection_sha256']==sha(paths['selection']) and selection['protocol_sha256']==protocol_hash,'Selection binding differs')
    require(selection['actual_headers_sha256']==manifest['actual_headers_sha256']==p['actual_headers_sha256']==sha(paths['actual']),'Actual header binding differs')
    require(selection['target']==TARGET and selection['primary_id']==PRIMARY_ID and selection['ntime']==ROWS and selection['channel_start']==channel_start and selection['channel_count']==CHANNELS and selection['halo_channels']==4096 and selection['native_chunk_index']==chunk_index,'Selection geometry/target differs')
    require(selection['powers_inspected_before_selection'] is False,'Selection must precede powers')
    scans=manifest['scans'];receipts=manifest['chunk_receipts'];repeats=manifest['repeated_chunk_receipts'];actual_headers=actual['headers']
    require(len(scans)==6 and [s['scan'] for s in scans]==list(range(6)) and [s['role'] for s in scans]==['ON','OFF']*3,'Six ordered ON/OFF scans required')
    require([s['archive']['id'] for s in scans]==ids and selection['rows']==[s['archive'] for s in scans] and selection['roles']==[s['role'] for s in scans],'Archive IDs/roles differ')
    require(actual['header_qualified_for_acquisition'] and not actual['powers_inspected'] and actual['target']==TARGET and actual['primary_id']==PRIMARY_ID,'Actual header qualification differs')
    require(len(actual_headers)==6 and [h['row'] for h in actual_headers]==selection['rows']==catalog_rows,'Actual header/catalog sources differ')
    require(actual['selected']['native_chunk_index']==chunk_index and actual['selected']['channel_start']==channel_start and actual['selected_count']==CHANNELS and actual['core_channels']==[4096,CHANNELS-4096],'Actual header selection differs')
    require(len(receipts)==96 and len({(r['scan'],r['start']) for r in receipts})==96,'96 unique chunk receipts required')
    require(len(repeats)==6 and sorted(r['scan'] for r in repeats)==list(range(6)),'Six fresh repeat receipts required')
    require(manifest['new_native_rows']==96 and manifest['previous_power_payloads_reused']==0 and manifest['full_original_md5_verified'] is False,'Fresh acquisition provenance differs')
    inherited=[r for h in actual_headers for r in h['metadata_requests']]
    require(manifest['inherited_header_metadata_receipts']==inherited,'Inherited header receipts differ')
    prior_phase=manifest.get('inherited_prior_phase_metadata_receipts',[])
    metadata=list(manifest['metadata_receipts'])+inherited+prior_phase
    for receipt in metadata:verify_range(folder,receipt,scans,actual_headers,inputs,'metadata')
    for receipt in repeats:
        verify_range(folder,receipt,scans,actual_headers,inputs,'repeat')
        original=[r for r in receipts if r['scan']==receipt['scan'] and r['start']==receipt['start']]
        require(len(original)==1 and all(original[0][key]==receipt[key] for key in RECEIPT_KEYS),'Fresh repeat bytes/source differs')
    reports=[];chunk_index_checks=0;tree_nodes=[]
    for scan in scans:
        j=scan['scan'];require(scan['array_file']==f'scan{j}.npy' and scan['slice_shape']==[ROWS,CHANNELS] and scan['ntime']==ROWS and scan['channel_start']==channel_start and scan['channel_stop_exclusive']==channel_start+CHANNELS,'Canonical scan geometry differs')
        hp=relative_file(folder,f'data/scan{j}_header.json');mp=relative_file(folder,f'metadata_scan{j}.json');pin(hp,inputs);pin(mp,inputs)
        header=read(hp);mh=read(mp)
        require(mh==actual_headers[j] and all(mh['checks'].values()),'Metadata header checks differ')
        require(header['scan']==j and header['archive']==mh['row']==scan['archive'] and header['attrs']==mh['attrs']==scan['sigproc'] and header['etag']==mh['etag'],'Descriptor header identity differs')
        require(header['shape']==mh['shape']==[ROWS,1,mh['attrs']['nchans']] and mh['shape'][2]>=channel_start+CHANNELS and mh['chunks']==[1,1,CHANNELS] and mh['dtype']=='float32','Header geometry/type differs')
        require(header['inherited_header_metadata_receipts']==mh['metadata_requests'],'Descriptor inherited metadata differs')
        require(header['metadata_requests']==[r for r in manifest['metadata_receipts'] if r['scan']==j],'Descriptor new metadata differs')
        require(header.get('inherited_prior_phase_metadata_receipts',[])==[r for r in prior_phase if r['scan']==j],'Descriptor inherited prior-phase metadata differs')
        chunks=header['chunks'];require(len(chunks)==ROWS and sorted(c['time_index'] for c in chunks)==list(range(ROWS)),'16 unique ordered chunk rows required')
        checked,used_nodes=audit_chunk_index(folder,{**scan,'_scans':scans},header,actual_headers,metadata,inputs,channel_start,index_model);chunk_index_checks+=checked;tree_nodes.append(dict(scan=j,nodes=used_nodes))
        array_path=relative_file(folder,f'data/{scan["array_file"]}');require(pin(array_path,inputs)==scan['array_sha256'],'Canonical array file SHA differs')
        raw=np.load(array_path,mmap_mode='r',allow_pickle=False);require(raw.shape==(ROWS,CHANNELS) and raw.dtype==np.dtype('<f4'),'Canonical array shape/dtype differs')
        powers=hashlib.sha256();rows=[]
        for chunk in sorted(chunks,key=lambda item:item['time_index']):
            row=chunk['time_index'];begin=chunk['byte_offset'];end=begin+chunk['size']-1
            require(chunk['scan']==j and chunk['filter_mask']==0 and chunk['chunk_offset']==[row,0,channel_start] and chunk['etag']==header['etag'],'Chunk coordinate/filter/ETag differs')
            matches=[r for r in receipts if r['scan']==j and r['start']==begin];require(len(matches)==1,'Chunk receipt missing/duplicate')
            receipt=matches[0];require(receipt['stop_inclusive']==end and receipt['bytes']==chunk['size'],'Chunk descriptor range differs')
            payload_path=verify_range(folder,receipt,scans,actual_headers,inputs,'payload');payload=payload_path.read_bytes()
            decoded,blockbytes=decode_payload(payload,CHANNELS);rowbytes=decoded.tobytes(order='C')
            require(rowbytes==raw[row].tobytes(order='C'),'Reconstructed row differs from canonical native array')
            powers.update(rowbytes);rows.append(dict(time_index=row,payload_sha256=receipt['sha256'],decoded_row_sha256=hashlib.sha256(rowbytes).hexdigest(),codec_block_bytes=blockbytes,exact_row_bytes_match=True))
        require(powers.hexdigest()==scan['array_powers_sha256'],'Reconstructed power-byte SHA differs')
        reports.append(dict(scan=j,array_file=scan['array_file'],array_sha256=scan['array_sha256'],array_powers_sha256=powers.hexdigest(),rows_reconstructed=ROWS,rows=rows,exact_array_and_power_hashes_match=True));del raw
        print(json.dumps(dict(scan_reconstructed=j,rows=ROWS,exact_sha256_match=True)),flush=True)
    for path,digest in inputs.items():require(sha(path)==digest,'Input/source mutated during audit: '+path)
    return dict(schema='SETI_AZ_OFFLINE_NATIVE_INPUT_PROOF_V1',version=VERSION,status='PASS',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),target=TARGET,primary_id=PRIMARY_ID,native_chunk_index=chunk_index,channel_start=channel_start,archive_ids=ids,hdf_chunk_index_model=index_model,protocol_sha256=protocol_hash,manifest_sha256=manifest_hash,reconstructed_scan_count=6,reconstructed_chunk_count=96,independent_retained_HDF_chunk_descriptor_checks=chunk_index_checks,independent_TREE_v1_used_nodes=tree_nodes,metadata_receipts_checked=len(metadata),repeat_receipts_checked=6,fresh_repeat_bytes_and_receipts_checked=6,all_exact_array_and_power_hashes_match=True,scans=reports,input_and_source_sha256_before_after=inputs,runtime=dict(python=sys.version,numpy=np.__version__,h5py=h5py.__version__,bitshuffle=bitshuffle.__version__,platform=platform.platform()),network_requests=0,science_recalculated=False,limitations='All96 rows are re-decoded and compared byte-for-byte with canonical arrays. HDF v1 TREE path metadata are parsed independently from retained bytes with the disclosed inherited TREE-v1 root/levels model recorded in this proof; no whole-index HDF enumeration. Uses acquisition h5py/bitshuffle codec, so not an independent decoder or full original HDF archive MD5 verification. No detector results or astronomical sensitivity are qualified.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--target',required=True);parser.add_argument('--protocol',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=audit(args.target,args.protocol);publish(args.output,result)
    print(json.dumps(dict(status='PASS',output=args.output,sha256=sha(args.output),scans=6,chunks=96)),flush=True)
