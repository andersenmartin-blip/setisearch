"""Fresh full source acquisition candidate, local synthetic HTTP only.

The existing source modules are imported unchanged. Only open_response is
replaced by a .invalid-only in-memory responder. Socket operations are denied.
No executable telescope contract, source allocation or scientific claim.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import socket
import struct
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path('/workspace/scratch/fb4056c33767/frozen-project')
RUNTIME = Path('/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a/venv')
OUT = Path('/workspace/scratch/fb4056c33767/acquisition-candidate/attempt01')
START = time.monotonic()
LIMITS = {'seconds':60,'peak_rss_bytes':512*1024**2,'generated_file_bytes':640*1024**2}
SHAPE = (16,1,264503296)
CHUNKS = (1,1,1048576)
PROFILE = [[32008,1,[0,3,4,0,2]]]
PINS = {
 'src/seti_repeater/source_radio.py':'d189028cacf05482a8b9a74a9544d30a1c45cd60f95784be5f06b2ce093e677f',
 'src/seti_repeater/source_m43h.py':'85ce563e78b2d16f65b6a15313c4ae0c22a58f1455ce8db77acbc9a62d33429d',
 'src/seti_repeater/source_v0p6.py':'70a33bb5688b9dcdca7933ef4707fe9e989fc5cb9d7402c4d0f88b6c28f2988f',
 'src/seti_repeater/search_v0p6.py':'6bac0d68d76d818d49d57e3b6a19b30b1e6c2ef25c9d06b9c25a1ab2321ac7e4',
 'src/seti_repeater/http_range_v0p6.py':'0e831ef08c2b6109c67a44e8ead0f21cd20892e24c3112fe3adbde00fd990991',
 'src/seti_repeater/transport_radio.py':'80a936cf23b40dacfbef74d9558de7ce6ce41700c5c916d9b2268eabd966085a',
 'src/seti_repeater/transport_m43h.py':'eedcad40b3a4e2f772df1564388066beefe098217d2edb2cd67c24a9805063a5',
 'src/seti_repeater/hdf5_filter_contract_radio.py':'65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6',
 'src/seti_repeater/prospective_source_metadata_radio.py':'2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360',
 'config/radio_hd189733_source_preparation_20260927.json':'98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1',
 'results_radio_hd189733_geometry_2026-09-27/window_geometry.json':'92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6',
}
CASES=[]
SOCKET_ATTEMPTS=[]
ORACLES=[]

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'

def write(path,value):
    with Path(path).open('xb') as handle:
        handle.write(canonical(value));handle.flush();os.fsync(handle.fileno())

def file_pin(path):
    path=Path(path);h=hashlib.sha256()
    with path.open('rb') as handle:
        for part in iter(lambda:handle.read(1024*1024),b''):h.update(part)
    st=path.stat()
    return {'path':str(path),'bytes':st.st_size,'allocated_bytes':st.st_blocks*512,'sha256':h.hexdigest()}

def audit(event,args):
    if event.startswith('socket.') and event not in ('socket.__new__',):
        SOCKET_ATTEMPTS.append({'event':event,'argument_types':[type(x).__name__ for x in args]})
        raise RuntimeError('socket operation denied by acquisition candidate')

sys.addaudithook(audit)
if not sys.flags.isolated or not sys.dont_write_bytecode or Path(sys.prefix).resolve()!=RUNTIME.resolve():
    raise RuntimeError('isolated pinned interpreter -I -B required')
sys.path.insert(0,str(ROOT/'src'))
import h5py
import hdf5plugin
import numpy as np
from seti_repeater import source_radio as source
from seti_repeater import source_m43h as rows
from seti_repeater import transport_radio as net
from seti_repeater import http_range_v0p6 as old
from seti_repeater import hdf5_filter_contract_radio as guard

def budget():
    if time.monotonic()-START>LIMITS['seconds']:raise RuntimeError('candidate time ceiling')
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>LIMITS['peak_rss_bytes']:raise RuntimeError('candidate RSS ceiling')
    if OUT.exists() and sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>LIMITS['generated_file_bytes']:
        raise RuntimeError('candidate file ceiling')

def runtime_snapshot():
    paths=set();links=[]
    for p in RUNTIME.rglob('*'):
        if p.is_symlink():
            target=p.resolve(strict=True)
            if not target.is_relative_to(RUNTIME):raise ValueError('runtime alias leaves held root')
            links.append({'path':str(p),'link_text':os.readlink(p),'resolved_target':str(target),'target_is_directory':target.is_dir()})
        elif p.is_file():paths.add(p.resolve())
    stdlib=Path(sys.base_prefix)/'lib/python3.12'
    for d,subdirs,names in os.walk(stdlib):
        subdirs[:]=[n for n in subdirs if n!='site-packages']
        for name in names:
            p=Path(d)/name
            if p.is_file():paths.add(p.resolve())
    modules={}
    for name,module in tuple(sys.modules.items()):
        p=getattr(module,'__file__',None)
        if p and Path(p).is_file():
            p=Path(p).resolve();paths.add(p);modules[name]=str(p)
    mapped=[]
    for line in Path('/proc/self/maps').read_text().splitlines():
        parts=line.split(maxsplit=5)
        if len(parts)==6 and parts[-1].startswith('/'):
            p=Path(parts[-1]).resolve(strict=True);paths.add(p);mapped.append(str(p))
    paths.add(Path(sys.executable).resolve())
    files=[file_pin(p) for p in sorted(paths)]
    return {'schema':'radio-acquisition-candidate-observed-runtime-files-v1','files':files,'links':links,
        'loaded_module_paths':modules,'mapped_paths':sorted(set(mapped)),'file_count':len(files),
        'raw_bytes':sum(p['bytes'] for p in files),'complete_execution_runtime_freeze':False,
        'externally_observed_complete_lifetime':False}

def texture(scan,ci,row,start=0,stop=CHUNKS[2]):
    i=np.arange(start,stop,dtype='<u4')
    return (np.float32(100)+((i*17+ci*31+row*13+scan*19)%4093).astype('<f4')*np.float32(1/4096)
        +((i//4096)%17).astype('<f4')*np.float32(1/32)+np.float32(scan/8)).astype('<f4')

def independent_raw(scan,ci,row,start,stop):
    return b''.join(struct.pack('<f',100+((i*17+ci*31+row*13+scan*19)%4093)/4096
        +((i//4096)%17)/32+scan/8) for i in range(start,stop))

def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]

def independent_normalized(native_bytes):
    values=list(struct.unpack('<'+str(len(native_bytes)//4)+'f',native_bytes));values.reverse();out=[]
    for start in range(0,len(values),4096):
        part=values[start:start+4096];ordered=sorted(part);n=len(part)
        center=ordered[n//2] if n%2 else f32(f32(ordered[n//2-1]+ordered[n//2])/2)
        dev=sorted(abs(f32(x-center)) for x in part)
        mad=dev[n//2] if n%2 else f32(f32(dev[n//2-1]+dev[n//2])/2)
        scale=max(f32(f32(1.4826)*mad),struct.unpack('<f',bytes.fromhex('00008000'))[0])
        out.extend(f32(f32(x-center)/scale) for x in part)
    return struct.pack('<'+str(len(out))+'f',*out)

def fresh_h5(scan_index,definition,windows):
    encoded=[]
    # The encoder is ephemeral in-memory scratch, with no persistent duplicate.
    with h5py.File(str(OUT/('encoder-'+str(scan_index)+'.h5')),'w',driver='core',backing_store=False) as h:
        d=h.create_dataset('data',shape=CHUNKS,chunks=CHUNKS,dtype='<f4',**hdf5plugin.Bitshuffle(nelems=0,cname='lz4'))
        encoder_profile=guard.signature([d.id.get_create_plist().get_filter(0)])
        for w in windows:
            ci=w['archive_chunk_index']
            for row in range(16):
                d[0,0,:]=texture(scan_index,ci,row);h.flush()
                mask,payload=d.id.read_direct_chunk((0,0,0))
                if mask:raise ValueError('current local encoder skipped codec')
                encoded.append((row,ci,payload))
            budget()
    path=OUT/'fixtures'/(definition['label']+'.h5')
    plugin_paths=[h5py.h5pl.get(i) for i in range(h5py.h5pl.size())]
    try:
        for i in range(h5py.h5pl.size()-1,-1,-1):h5py.h5pl.remove(i)
        if not h5py.h5z.unregister_filter(32008) or h5py.h5z.filter_avail(32008):raise RuntimeError('legacy declaration isolation failed')
        with h5py.File(path,'x',rdcc_nbytes=8*1024**2) as h:
            p=h5py.h5p.create(h5py.h5p.DATASET_CREATE);p.set_chunk(CHUNKS)
            p.set_filter(32008,h5py.h5z.FLAG_OPTIONAL,(0,3,4,0,2));p.set_fill_time(h5py.h5d.FILL_TIME_NEVER)
            d=h5py.Dataset(h5py.h5d.create(h.id,b'data',h5py.h5t.IEEE_F32LE,h5py.h5s.create_simple(SHAPE),dcpl=p))
            guard.check_dataset(d,PROFILE)
            for row,ci,payload in encoded:d.id.write_direct_chunk((row,0,ci*CHUNKS[2]),payload,filter_mask=0)
            hd=definition['expected_header']
            h.attrs.update({'source_name':hd['source_name'],'src_raj':hd['src_raj_hours'],'src_dej':hd['src_dej_deg'],
                'tstart':hd['tstart_mjd'],'tsamp':hd['tsamp_s'],'fch1':hd['fch1_mhz'],'foff':hd['foff_mhz']})
            if d.id.get_num_chunks()!=48:raise ValueError('fixture chunk inventory differs')
            h.flush()
    finally:
        for i in range(h5py.h5pl.size()-1,-1,-1):h5py.h5pl.remove(i)
        for p in plugin_paths:h5py.h5pl.append(p)
        if not hdf5plugin.register(filters=32008,force=True):raise RuntimeError('codec registration restoration failed')
    return path,encoder_profile,[{'row':row,'chunk_index':ci,'compressed_bytes':len(b),
        'compressed_sha256':hashlib.sha256(b).hexdigest()} for row,ci,b in encoded]

class Response:
    def __init__(self,url,status,headers,payload):self.url=url;self.status=status;self.headers=headers;self.payload=payload;self.reads=0
    def geturl(self):return self.url
    def read(self,n):self.reads+=1;return self.payload[:n]
    def __enter__(self):return self
    def __exit__(self,*args):pass

class SyntheticServer:
    def __init__(self,definitions,paths,fault=None):
        self.definitions={d['url']:d for d in definitions};self.paths=dict(zip([d['url'] for d in definitions],paths))
        self.calls=[];self.responses=[];self.fault=fault
    def __call__(self,request,timeout):
        if request.full_url not in self.definitions or '.invalid/' not in request.full_url:raise RuntimeError('only independently pinned synthetic URLs allowed')
        definition=self.definitions[request.full_url];method=request.get_method();headers={'ETag':definition['expected_etag'],'Accept-Ranges':'bytes',
            'Content-Length':str(definition['expected_remote_size_bytes'])};payload=b'';status=200
        record={'url':request.full_url,'method':method,'range':request.headers.get('Range'),'timeout':timeout}
        if method=='GET':
            a,b=map(int,request.headers['Range'].removeprefix('bytes=').split('-'))
            if request.headers.get('If-match')!=definition['expected_etag'] or request.headers.get('Accept-encoding')!='identity':
                raise AssertionError('source transport identity binding absent')
            with self.paths[request.full_url].open('rb') as h:h.seek(a);payload=h.read(b-a+1)
            headers.update({'Content-Range':f'bytes {a}-{b}/{definition["expected_remote_size_bytes"]}','Content-Length':str(b-a+1)});status=206
            if self.fault=='etag':headers['ETag']='"wrong"'
            if self.fault=='range':headers['Content-Range']=f'bytes {a+1}-{b+1}/{definition["expected_remote_size_bytes"]}'
            if self.fault=='length':headers['Content-Length']=str(b-a+2)
            if self.fault=='encoding':headers['Content-Encoding']='gzip'
            if self.fault=='url':record['returned_url']='https://other.invalid/wrong'
            if self.fault=='status':status=200
            if self.fault=='short':payload=payload[:-1]
            if self.fault=='overlong':payload+=b'!'
            if self.fault=='interrupt' and sum(c['method']=='GET' for c in self.calls)>=2:
                self.calls.append(record);raise OSError('fresh intentional simulated transport interruption')
        self.calls.append(record)
        response=Response(record.get('returned_url',request.full_url),status,headers,payload);self.responses.append(response)
        return response
    def receipt(self):return {'calls':self.calls,'body_read_calls':sum(r.reads for r in self.responses),'response_count':len(self.responses)}

def expect(name,operation,reject=False):
    try:value=operation()
    except (ValueError,RuntimeError,OSError) as e:
        if not reject:raise
        CASES.append({'name':name,'expected':'reject','pass':True,'exception':type(e).__name__,'reason':str(e)});return None
    if reject:raise AssertionError('expected refusal accepted: '+name)
    CASES.append({'name':name,'expected':'accept','pass':True});return value

def main():
    OUT.mkdir(exist_ok=False);(OUT/'fixtures').mkdir()
    inputs={name:file_pin(ROOT/name) for name in PINS}
    if any(inputs[n]['sha256']!=v for n,v in PINS.items()):raise ValueError('held source/input bytes differ')
    before=runtime_snapshot();write(OUT/'runtime-before.json',before)
    original=json.loads((ROOT/'config/radio_hd189733_source_preparation_20260927.json').read_bytes())
    geometry=json.loads((ROOT/'results_radio_hd189733_geometry_2026-09-27/window_geometry.json').read_bytes())
    if original['hdf5_runtime'] is not None or original['windows']:raise ValueError('original preparation activated')
    windows=copy.deepcopy(geometry['windows'])
    for w in windows:w['name']='hd189733_'+w['role']+'_receiver_v1'
    definitions=copy.deepcopy(original['scans']);fixtures=[];raw_chunks=[]
    for i,d in enumerate(definitions):
        if guard.declared(d,required=True)!=PROFILE or tuple(d['expected_header']['dataset_shape'])!=SHAPE or tuple(d['expected_chunks'])!=CHUNKS:
            raise ValueError('held six-source metadata differs')
        d['url']='https://'+d['label']+'.invalid/source.h5';d['expected_etag']='"fresh-acquisition-candidate-'+str(i)+'"'
        path,encoder_profile,chunks=fresh_h5(i,d,windows);d['expected_remote_size_bytes']=path.stat().st_size
        fixtures.append(path);raw_chunks.append({'label':d['label'],'chunks':chunks});budget()
    descriptor={'schema':'radio-fresh-synthetic-acquisition-descriptor-v1','source_metadata_origin_sha256':inputs['config/radio_hd189733_source_preparation_20260927.json']['sha256'],
        'geometry_origin_sha256':inputs['results_radio_hd189733_geometry_2026-09-27/window_geometry.json']['sha256'],
        'scans':definitions,'windows':windows,'fixture_files':[file_pin(p) for p in fixtures],
        'original_header_label_role_chunks_filters_preserved':True,'only_definition_changes':['url','expected_etag','expected_remote_size_bytes'],
        'source_filter_pipeline':PROFILE,'current_encoder_filter_pipeline':encoder_profile,'current_encoder_is_original_archive_encoder':False,
        'synthetic_texture':'100+((i*17+chunk*31+row*13+scan*19)%4093)/4096+((i//4096)%17)/32+scan/8',
        'raw_chunk_receipts':raw_chunks,'random_draws':0,'telescope_provenance':False,'scientific_allocation':False}
    write(OUT/'fixture-descriptor.json',descriptor);descriptor_pin=file_pin(OUT/'fixture-descriptor.json');contract=descriptor_pin['sha256']
    products=[];transports=[]
    server=SyntheticServer(definitions,fixtures);session=net.Budget(1000,512*1024**2,60)
    with patch.object(net,'open_response',side_effect=server):
        for si,d in enumerate(definitions):
            mirror=OUT/'mirrors'/d['label']
            for w in windows:
                destination=OUT/'products'/w['role']/d['label']
                receipt,detail=expect('full_acquisition_'+d['label']+'_'+w['role'],lambda d=d,w=w,destination=destination,mirror=mirror:
                    source._extract_bound_source(d,w,contract,destination,mirror,session,kind='local-fixture'))
                if detail['resumed_rows']!=0:raise AssertionError('fresh rows unexpectedly resumed')
                before_get=sum(c['method']=='GET' for c in server.calls)
                repeated,repeated_detail=expect('restart_same_window_'+d['label']+'_'+w['role'],lambda d=d,w=w,destination=destination,mirror=mirror:
                    source._extract_bound_source(d,w,contract,destination,mirror,session,kind='local-fixture'))
                if repeated_detail['resumed_rows']!=16 or repeated!=receipt or before_get!=sum(c['method']=='GET' for c in server.calls):
                    raise AssertionError('same-window resume lost original receipt or redownloaded')
                row_oracles=[]
                for row in range(16):
                    lo,hi=w['archive_interval'];ci=w['archive_chunk_index'];a=lo-ci*CHUNKS[2];b=hi-ci*CHUNKS[2]
                    expected=independent_raw(si,ci,row,a,b)
                    native=np.load(destination/f'row{row:02d}.native.npy',allow_pickle=False)
                    normalized=np.load(destination/f'row{row:02d}.normalized.npy',allow_pickle=False)
                    if native.tobytes()!=expected:raise AssertionError('independent synthetic native row oracle differs')
                    # Independent scalar normalization on the first row of every
                    # source/window; all rows reproduce via actual rehydrate.
                    normalized_oracle=None
                    if row==0:
                        wanted=independent_normalized(expected)
                        if normalized.tobytes()!=wanted:raise AssertionError('independent normalized row oracle differs')
                        normalized_oracle=hashlib.sha256(wanted).hexdigest()
                    row_oracles.append({'row':row,'native_sha256':hashlib.sha256(expected).hexdigest(),
                        'normalized_sha256':rows.array_hash(normalized),'independent_normalized_sha256':normalized_oracle})
                hydrated=expect('rehydrate_'+d['label']+'_'+w['role'],lambda destination=destination,receipt=receipt:
                    rows.rehydrate(destination,receipt['receipt_sha256'],required_kind='local-fixture'))
                if hydrated!=receipt:raise AssertionError('complete receipt restoration differs')
                products.append({'label':d['label'],'role':w['role'],'window':w['name'],'directory':str(destination),
                    'receipt_sha256':receipt['receipt_sha256'],'scope_sha256':rows.digest(receipt['scope']),
                    'fixture_source_contract_sha256':contract,'source_metadata_origin_sha256':descriptor['source_metadata_origin_sha256'],
                    'source_file':file_pin(destination/'source.json'),'row_oracles':row_oracles})
                transports.append({'label':d['label'],'role':w['role'],'range_plan':detail['range_plan'],'budget':detail['budget']});budget()
        # Exact current helper rejects LOCAL-FIXTURE checkpoint ancestry growth
        # after other windows; the live-only extension branch is not exercised.
        # Preserve and record this limitation rather than silently relabeling it.
        for d in definitions:
            w=windows[0];destination=OUT/'products'/w['role']/d['label'];prior=next(p for p in products if p['label']==d['label'] and p['role']==w['role'])
            before_get=sum(c['method']=='GET' for c in server.calls)
            expect('local_fixture_multiwindow_resume_refused_'+d['label'],lambda d=d,w=w,destination=destination:
                source._extract_bound_source(d,w,contract,destination,OUT/'mirrors'/d['label'],session,kind='local-fixture'),True)
            if file_pin(destination/'source.json')!=prior['source_file'] or before_get!=sum(c['method']=='GET' for c in server.calls):
                raise AssertionError('expected resume refusal changed original receipt or redownloaded')
    write(OUT/'positive-http-transcript.json',server.receipt())
    # Each failure uses a new directory. Positive receipts are never rewritten.
    def run_bad(name,definition=None,fault=None,limits=None,setup=None):
        d=definition or definitions[0];w=windows[0];target=OUT/'negative'/name/'products';mirror=OUT/'negative'/name/'mirror'
        mirror.mkdir(parents=True)
        if setup:setup(mirror)
        badserver=SyntheticServer(definitions,fixtures,fault=fault);b=net.Budget(*(limits or (1000,64*1024**2,60)))
        with patch.object(net,'open_response',side_effect=badserver):
            expect(name,lambda:source._extract_bound_source(d,w,contract,target,mirror,b,kind='local-fixture'),True)
        if (target/'source.json').exists():raise AssertionError('failed acquisition completed a receipt')
        write(mirror.parent/'failure-case.json',{'name':name,'server':badserver.receipt(),'budget':b.record(),'completed_receipt':False})
        return badserver,b
    for field in ('expected_etag','expected_remote_size_bytes'):
        d=copy.deepcopy(definitions[0]);d[field]=('"wrong"' if field=='expected_etag' else d[field]+1)
        s,b=run_bad('reject_'+field,d)
        if len(s.calls)!=1 or s.responses[0].reads:raise AssertionError('identity fault reached body')
    for name,mutator in [('header_source_name',lambda d:d['expected_header'].__setitem__('source_name','wrong')),
        ('header_time',lambda d:d['expected_header'].__setitem__('tstart_mjd',d['expected_header']['tstart_mjd']+1)),
        ('chunks',lambda d:d['expected_chunks'].__setitem__(2,524288)),
        ('filter_id',lambda d:d['observed_hdf5_filters'][0].__setitem__(0,32009)),
        ('filter_clients',lambda d:d['observed_hdf5_filters'][0][2].__setitem__(1,4))]:
        d=copy.deepcopy(definitions[0]);mutator(d);run_bad('reject_'+name,d)
    for fault in ('etag','range','length','encoding','url','status','short','overlong','interrupt'):
        s,b=run_bad('reject_response_'+fault,fault=fault)
        if fault in ('etag','range','length','encoding','url','status') and s.receipt()['body_read_calls']!=0:
            raise AssertionError('prebody response guard read body')
    run_bad('reject_request_budget',limits=(1,64*1024**2,60))
    run_bad('reject_byte_budget',limits=(1000,1,60))
    base=OUT/'mirrors'/definitions[0]['label'];label=definitions[0]['label'];cp_name=label+'.h5.sparse.ranges.json';sparse_name=label+'.h5.sparse'
    def copy_mirror(target):
        shutil.copyfile(base/cp_name,target/cp_name);shutil.copyfile(base/sparse_name,target/sparse_name)
    def corrupted_checkpoint(target):
        copy_mirror(target);cp=json.loads((target/cp_name).read_bytes());cp['checkpoint_sha256']='0'*64
        (target/cp_name).write_bytes(old._canonical_json_bytes(cp))
    run_bad('reject_checkpoint_digest',setup=corrupted_checkpoint)
    def corrupt_payload(target):
        copy_mirror(target);cp=json.loads((target/cp_name).read_bytes());first=cp['segments'][0]
        with (target/sparse_name).open('r+b') as h:h.seek(first['start']);v=h.read(1);h.seek(first['start']);h.write(bytes([v[0]^1]))
    run_bad('reject_checkpoint_payload',setup=corrupt_payload)
    # Payload origins remain distinct; no independence or noise-law claim.
    for w in windows:
        pp=[p for p in products if p['role']==w['role']]
        if len({p['row_oracles'][0]['native_sha256'] for p in pp})!=6:raise AssertionError('synthetic sources not raw-distinct')
    final=runtime_snapshot();write(OUT/'runtime-after.json',final)
    before_payload={p['path']:(p['bytes'],p['sha256']) for p in before['files']}
    final_payload={p['path']:(p['bytes'],p['sha256']) for p in final['files']}
    if any(final_payload.get(p)!=v for p,v in before_payload.items()):raise AssertionError('observed held runtime bytes changed')
    if any(file_pin(ROOT/n)['sha256']!=v for n,v in PINS.items()):raise AssertionError('held source/input changed')
    if SOCKET_ATTEMPTS:raise AssertionError('socket capability attempted')
    missing=next(ast.literal_eval(n.value) for n in ast.parse((ROOT/'src/seti_repeater/prospective_source_metadata_radio.py').read_bytes()).body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MISSING_FIELDS' for t in n.targets))
    generated=[file_pin(p) for p in sorted(OUT.rglob('*')) if p.is_file()];budget()
    index={'schema':'radio-full-source-acquisition-candidate-index-v1','status':'PASS','authority':'local synthetic candidate engineering only',
        'products':products,'fixture_descriptor_pin':descriptor_pin,'fixture_source_contract_sha256':contract,
        'retained_source_inventory_sha256':original['source_inventory_sha256'],'input_pins':inputs,'script_pin':file_pin(__file__),
        'actual_imported_project_modules':{n:p for n,p in final['loaded_module_paths'].items() if n=='seti_repeater' or n.startswith('seti_repeater.')},
        'runtime':source.runtime(),'runtime_before_pin':file_pin(OUT/'runtime-before.json'),'runtime_after_pin':file_pin(OUT/'runtime-after.json'),
        'observed_before_runtime_file_payloads_unchanged':True,'observed_after_additional_paths':sorted(set(final_payload)-set(before_payload)),
        'cases':CASES,'case_count':len(CASES),'full_scan_window_pairs':18,'row_products':288,
        'independent_struct_raw_cells_checked':288*65536,'independent_scalar_normalized_cells_checked':18*65536,
        'positive_session_budget':session.record(),'transport_details':transports,'socket_attempts':SOCKET_ATTEMPTS,
        'network_requests':0,'telescope_or_holdout_files_opened':0,'rng_draws':0,'native_scoring_or_scientific_cases':0,
        'resource_limits':LIMITS,'observed_seconds':time.monotonic()-START,'observed_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'generated_files':generated,'generated_logical_bytes':sum(p['bytes'] for p in generated),'generated_allocated_bytes':sum(p['allocated_bytes'] for p in generated),
        'scientific_missing_fields_unchanged':missing,'complete_execution_runtime_freeze':False,'externally_observed_complete_lifetime':False,
        'public_authentication_established':False,'source_specific_executable_contract_created':False,'source_or_scientific_admission':False,
        'receiver_handoff_qualified':False,'hosted_transport_qualified':False,
        'coverage_limitations':['local simulated HTTP adapter; no hosted or network transaction','independent normalized scalar oracle covers row zero of each scan/window; all 288 rows rehydrate',
            'local-fixture multiwindow restart is currently refused after checkpoint extension; original products remain valid and unchanged',
            'runtime snapshots describe observed paths and bytes; no complete lifetime or public certificate','synthetic source bytes and .invalid identity; no telescope provenance or scientific qualification']}
    write(OUT/'index.json',index)
    print(json.dumps({'status':'PASS','cases':len(CASES),'scan_window_pairs':18,'rows':288,'seconds':index['observed_seconds'],
        'generated_bytes':index['generated_logical_bytes'],'report':file_pin(OUT/'index.json')},sort_keys=True))

if __name__=='__main__':
    try:main()
    except BaseException as error:
        if OUT.exists() and not (OUT/'failure.json').exists():
            write(OUT/'failure.json',{'schema':'radio-full-acquisition-candidate-failure-v1','error':repr(error),
                'traceback':traceback.format_exc(),'seconds':time.monotonic()-START,'completed_cases':CASES,
                'automatic_retry':False,'source_or_scientific_admission':False})
        raise
