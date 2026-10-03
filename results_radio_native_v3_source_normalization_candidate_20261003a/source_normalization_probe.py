"""Fresh source-adapter known-answer laws; no project module is imported."""
import __future__
import ast
import copy
from dataclasses import dataclass, asdict
import hashlib
import json
import math
import operator
import os
from pathlib import Path
import resource
import shutil
import struct
import sys
import threading
import time
import traceback
from types import ModuleType, SimpleNamespace

import numpy as np

ROOT = Path('/workspace/scratch/8fcd6bf45392/setisearch-20261003-archive')
OUT = Path('/workspace/scratch/fa2e54995e11/source-normalization-candidate/attempt01')
RUNTIME = Path('/workspace/scratch/8fcd6bf45392/seti-hdf5-runtime-candidate-20261003a/venv')
CODEC_REPORT = Path('/workspace/scratch/fa2e54995e11/source-candidate/all-rows-probe-20261003c/all-rows-probe.json')
PINS = {
    'src/seti_repeater/source_m43h.py': '85ce563e78b2d16f65b6a15313c4ae0c22a58f1455ce8db77acbc9a62d33429d',
    'src/seti_repeater/source_radio.py': 'd189028cacf05482a8b9a74a9544d30a1c45cd60f95784be5f06b2ce093e677f',
    'src/seti_repeater/source_v0p6.py': '70a33bb5688b9dcdca7933ef4707fe9e989fc5cb9d7402c4d0f88b6c28f2988f',
    'src/seti_repeater/search_v0p6.py': '6bac0d68d76d818d49d57e3b6a19b30b1e6c2ef25c9d06b9c25a1ab2321ac7e4',
    'src/seti_repeater/http_range_v0p6.py': '0e831ef08c2b6109c67a44e8ead0f21cd20892e24c3112fe3adbde00fd990991',
    'src/seti_repeater/hdf5_filter_contract_radio.py': '65533ad8ead2bd7283beee9645a18b3a652a3ede50425573b64aaca69120e6a6',
    'src/seti_repeater/prospective_source_metadata_radio.py': '2852d23d30619e2406c36f46ffee2452fd64cd3834e31f18a7bb1f0ac8081360',
    'config/radio_hd189733_source_preparation_20260927.json': '98f6ced7e10cabaac139e027e8449e34ddf49024254761217a288ca6dc439cf1',
    'results_radio_hd189733_geometry_2026-09-27/window_geometry.json': '92fb0472203124f0f0a3f05a6a136c410ceaa72a31b66c12fcbbfb1c8c0eebc6',
}
START = time.monotonic()
LIMITS = {'seconds': 60, 'peak_rss_bytes': 256*1024**2, 'generated_file_bytes': 96*1024**2}
CASES = []
FUNCTION_PINS = []


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()+b'\n'


def pin(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    st=Path(path).stat()
    return {'path':str(path),'sha256':h.hexdigest(),'bytes':st.st_size,'allocated_bytes':st.st_blocks*512}


def write(path,value):
    with Path(path).open('xb') as f:
        f.write(canonical(value));f.flush();os.fsync(f.fileno())


def budget():
    if time.monotonic()-START>LIMITS['seconds']:raise RuntimeError('time ceiling')
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>LIMITS['peak_rss_bytes']:raise RuntimeError('RSS ceiling')
    if sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())>LIMITS['generated_file_bytes']:raise RuntimeError('file ceiling')


def extract(relative,names,globals_value,namespace_name):
    raw=(ROOT/relative).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINS[relative]:raise ValueError('module pin differs')
    text=raw.decode();tree=ast.parse(text)
    selected=[];seen=set()
    for node in tree.body:
        name=node.name if isinstance(node,(ast.FunctionDef,ast.ClassDef)) else None
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
        if name in names:
            selected.append(node);seen.add(name)
            segment=ast.get_source_segment(text,node).encode()
            FUNCTION_PINS.append({'module':relative,'name':name,'line_start':node.lineno,
                'line_end':node.end_lineno,'source_bytes':len(segment),
                'source_sha256':hashlib.sha256(segment).hexdigest(),
                'ast_sha256':hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()})
    if seen!=set(names):raise ValueError('function allowlist incomplete')
    module=ModuleType(namespace_name);module.__dict__.update(globals_value)
    sys.modules[namespace_name]=module
    compiled=compile(ast.Module(body=selected,type_ignores=[]),str(ROOT/relative),'exec',
        flags=__future__.annotations.compiler_flag,dont_inherit=True)
    exec(compiled,module.__dict__)
    return module


def expect(name,operation,error=None):
    try:result=operation()
    except Exception as caught:
        if error is None or not isinstance(caught,error):raise
        CASES.append({'name':name,'expected':'reject','pass':True,'exception':type(caught).__name__,'reason':str(caught)})
        return None
    if error is not None:raise AssertionError('unexpected acceptance: '+name)
    CASES.append({'name':name,'expected':'accept','pass':True})
    return result


def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]


def reference_normalize(native):
    ascending=list(reversed(native))
    result=[]
    for start in range(0,len(ascending),4096):
        section=ascending[start:start+4096]
        def median(values):
            ordered=sorted(values);n=len(values)
            if n%2:return ordered[n//2]
            return f32(f32(ordered[n//2-1]+ordered[n//2])/2)
        center=median(section)
        deviations=[abs(f32(x-center)) for x in section]
        mad=median(deviations)
        scale=max(f32(f32(1.4826)*mad),struct.unpack('<f',bytes.fromhex('00008000'))[0])
        result.extend(f32(f32(x-center)/scale) for x in section)
    return b''.join(struct.pack('<f',x) for x in ascending),b''.join(struct.pack('<f',x) for x in result)


def selected_pattern(ci,row,lo,hi):
    i=np.arange(lo-ci*1048576,hi-ci*1048576,dtype='<u4')
    return (np.float32(100)+((i*17+ci*31+row*13)%4093).astype('<f4')*np.float32(1/4096)
            +((i//4096)%17).astype('<f4')*np.float32(1/32)).astype('<f4')


class SyntheticDataset:
    def __init__(self,definition,window):
        header=definition['expected_header'];self.shape=tuple(header['dataset_shape'])
        self.dtype=np.dtype('<f4');self.chunks=tuple(definition['expected_chunks'])
        self.attrs={'source_name':header['source_name'].encode(),'src_raj':np.float64(header['src_raj_hours']),
            'src_dej':header['src_dej_deg'],'tstart':header['tstart_mjd'],'tsamp':header['tsamp_s'],
            'fch1':header['fch1_mhz'],'foff':header['foff_mhz']}
        self.filters=copy.deepcopy(definition['observed_hdf5_filters'])
        self.window=window;self.payload_reads=0;self.forbid_reads=False;self.payload_mode='valid'
    @property
    def id(self):return self
    def get_create_plist(self):return self
    def get_nfilters(self):return len(self.filters)
    def get_filter(self,index):return self.filters[index]
    def __getitem__(self,key):
        self.payload_reads+=1
        if self.forbid_reads:raise AssertionError('resumption attempted a synthetic payload read')
        row,feed,interval=key
        if feed!=0 or interval.start!=self.window['archive_interval'][0] or interval.stop!=self.window['archive_interval'][1]:
            raise AssertionError('hyperslab coordinates differ')
        raw=selected_pattern(self.window['archive_chunk_index'],row,interval.start,interval.stop)
        if self.payload_mode=='float64':return raw.astype('<f8')
        if self.payload_mode=='short':return raw[:-1]
        if self.payload_mode=='not-array':return raw.tolist()
        if self.payload_mode=='nan':raw[0]=np.nan
        return raw


class SyntheticHandle:
    def __init__(self,dataset):self.dataset=dataset;self.attrs={}
    def __getitem__(self,key):
        if key!='data':raise KeyError(key)
        return self.dataset


def main():
    if not sys.flags.isolated or not sys.dont_write_bytecode or Path(sys.prefix).resolve()!=RUNTIME:
        raise RuntimeError('isolated candidate interpreter -I -B required')
    OUT.mkdir(exist_ok=False)
    inputs={name:pin(ROOT/name) for name in PINS}
    if any(inputs[name]['sha256']!=expected for name,expected in PINS.items()):raise ValueError('input pin differs')
    codec_pin=pin(CODEC_REPORT)
    if codec_pin['sha256']!='e98bb2735128980c2f95efe3747e8a0794d2829d45fb0efac94347b435340dca':raise ValueError('codec48 report pin differs')
    codec=json.loads(CODEC_REPORT.read_bytes())
    core=extract('src/seti_repeater/search_v0p6.py',
        ['V0P6ContractError','V0P6CapacityError','_strict_int','canonical_json_bytes','_frozen_sha256',
         'NativeFrequencyGeometry','native_geometry_from_extraction'],
        {'np':np,'json':json,'math':math,'operator':operator,'dataclass':dataclass},'candidate_pure_geometry')
    legacy=extract('src/seti_repeater/source_v0p6.py',
        ['_F4','M37_MAXIMUM_SOURCE_RAW_NBYTES','M37_NORMALIZATION_BLOCK_CHANNELS',
         'M37_NORMALIZATION_MAD_MULTIPLIER','M37_NORMALIZATION_SCALE_FLOOR','_float32_median_rows',
         'normalize_float32_blocks_v0p6'],{'np':np,'core':core},'candidate_pure_normalization')
    transport=extract('src/seti_repeater/http_range_v0p6.py',
        ['CHECKPOINT_ARTIFACT','_canonical_json_bytes','_sha256_bytes','_write_atomic'],
        {'json':json,'hashlib':hashlib,'os':os,'threading':threading,'Path':Path},'candidate_pure_persistence')
    rows=extract('src/seti_repeater/source_m43h.py',
        ['VERSION','BLOCK','MAX_CHANNELS','MAX_ROWS','MAX_MODELLED_BYTES','MAX_HDF5_CHUNK_BYTES','HDF5_CACHE_BYTES',
         'digest','array_hash','file_hash','seal','verify','verify_transport_checkpoint','atomic_json','atomic_npy',
         'resource_bound','normalize_native_row','make_scope','observed_header','validate_dataset','_check_row',
         '_extract_rows','_complete','rehydrate'],
        {'np':np,'core':core,'legacy':legacy,'old_transport':transport,'hashlib':hashlib,'json':json,
         'Path':Path,'os':os,'asdict':asdict},'candidate_pure_source_rows')
    guard=extract('src/seti_repeater/hdf5_filter_contract_radio.py',
        ['_integer','signature','declared','check_dataset'],{},'candidate_pure_filter_guard')
    radio_raw=(ROOT/'src/seti_repeater/source_radio.py').read_bytes()
    radio_tree=ast.parse(radio_raw)
    outer=next(n for n in radio_tree.body if isinstance(n,ast.FunctionDef) and n.name=='_extract_bound_source')
    nested=next(n for n in outer.body if isinstance(n,ast.FunctionDef) and n.name=='dataset_checked')
    segment=ast.get_source_segment(radio_raw.decode(),nested).encode()
    FUNCTION_PINS.append({'module':'src/seti_repeater/source_radio.py','name':'_extract_bound_source.dataset_checked',
        'line_start':nested.lineno,'line_end':nested.end_lineno,'source_bytes':len(segment),
        'source_sha256':hashlib.sha256(segment).hexdigest(),
        'ast_sha256':hashlib.sha256(ast.dump(nested,include_attributes=False).encode()).hexdigest()})
    nested_code=compile(ast.Module(body=[nested],type_ignores=[]),'pinned-source-radio-dataset-guard','exec')
    source=json.loads((ROOT/'config/radio_hd189733_source_preparation_20260927.json').read_bytes())
    windows=json.loads((ROOT/'results_radio_hd189733_geometry_2026-09-27/window_geometry.json').read_bytes())['windows']
    contract=inputs['config/radio_hd189733_source_preparation_20260927.json']['sha256']
    source_scopes=[]
    def checked(definition,window,dataset=None):
        scope=rows.make_scope(definition,window['name'],window['archive_interval'],contract,'local-fixture')
        namespace={'rows':rows,'filter_contract':guard,'definition':definition,'scope':scope,
                   'expected_filters':guard.declared(definition,required=True)}
        exec(nested_code,namespace)
        handle=SyntheticHandle(dataset or SyntheticDataset(definition,window))
        return scope,handle,namespace['dataset_checked']
    # Exact retained header-affine maps and metadata guards for all six scans.
    for definition in source['scans']:
        for window in windows:
            scope,handle,check=checked(definition,window)
            expect('metadata_'+definition['label']+'_'+window['role'],lambda:check(handle))
            if handle.dataset.payload_reads:raise AssertionError('metadata guard indexed payload')
            g=scope['geometry']
            if g['channel_count']!=65536 or g['raw_zero_hz']!=window['native_frequency_low_hz']:
                raise AssertionError('retained window geometry differs')
            if abs(g['raw_zero_hz']+(65535*g['channel_width_hz'])-window['native_frequency_high_hz'])>4*math.ulp(window['native_frequency_high_hz']):
                raise AssertionError('reversed source endpoint mapping differs')
            source_scopes.append({'scan':definition['label'],'window':window['role'],'scope_sha256':rows.digest(scope),'geometry':g})
    # Independent scalar float32 rounding checks cover even/odd/terminal blocks.
    kats=[]
    for count in (1,2,3,4095,4096,4097,8193):
        values=np.array([f32((i*17%97)/8+(i//4096)*100) for i in range(count)],dtype='<f4')
        ascending,normalized=expect('normalization_KAT_'+str(count),lambda:rows.normalize_native_row(values))
        expected_ascending,expected_normalized=reference_normalize(values.tolist())
        if ascending.tobytes()!=expected_ascending or normalized.tobytes()!=expected_normalized:
            raise AssertionError('independent scalar float32 normalization differs')
        kats.append({'channels':count,'native_sha256':rows.array_hash(values),'ascending_sha256':rows.array_hash(ascending),
                     'normalized_sha256':rows.array_hash(normalized),'independent_stdlib_exact':True})
    const=np.full(4097,128,dtype='<f4')
    a,n=expect('constant_row_scale_floor',lambda:rows.normalize_native_row(const))
    if not np.array_equal(n,np.zeros_like(n)):raise AssertionError('constant row does not normalize to zero')
    invalid=[('float64',np.arange(4,dtype='<f8')),('big_endian',np.arange(4,dtype='>f4')),
        ('matrix',np.ones((1,4),dtype='<f4')),('empty',np.empty(0,dtype='<f4')),
        ('strided',np.arange(8,dtype='<f4')[::2]),('oversized',np.zeros(rows.MAX_CHANNELS+1,dtype='<f4')),
        ('nan',np.array([1,np.nan],dtype='<f4')),('infinity',np.array([1,np.inf],dtype='<f4'))]
    for name,raw in invalid:expect('normalization_reject_'+name,lambda raw=raw:rows.normalize_native_row(raw),ValueError)
    expect('normalization_reject_overflow',lambda:rows.normalize_native_row(np.array([np.finfo(np.float32).max]*2,dtype='<f4')),ValueError)
    definition=source['scans'][0];window=windows[0]
    # Metadata rejection must precede any payload indexing.
    for name,mutation in [
        ('source_name',lambda d:d.attrs.__setitem__('source_name',b'wrong')),
        ('time',lambda d:d.attrs.__setitem__('tstart',d.attrs['tstart']+1)),
        ('frequency',lambda d:d.attrs.__setitem__('fch1',d.attrs['fch1']+1)),
        ('shape',lambda d:setattr(d,'shape',(15,1,264503296))),
        ('dtype',lambda d:setattr(d,'dtype',np.dtype('<f8'))),
        ('chunks',lambda d:setattr(d,'chunks',(1,1,524288))),
        ('filter_id',lambda d:d.filters[0].__setitem__(0,32009)),
        ('filter_client_data',lambda d:d.filters[0][2].__setitem__(1,4)),
        ('missing_filter',lambda d:setattr(d,'filters',[])),
    ]:
        d=SyntheticDataset(definition,window);mutation(d);scope,h,check=checked(definition,window,d)
        expect('metadata_reject_'+name,lambda:check(h),ValueError)
        if d.payload_reads:raise AssertionError('bad metadata read payload')
    # Scope guards and exact digest/type admission.
    for name,interval in [('negative',[-1,8]),('empty',[8,8]),('boolean',[True,8]),
                          ('float',[1.0,8]),('outside',[264503290,264503300]),('oversized',[0,rows.MAX_CHANNELS+1]),('singleton',[0,1])]:
        expect('scope_reject_'+name,lambda interval=interval:rows.make_scope(definition,'candidate',interval,contract,'local-fixture'),ValueError)
    expect('scope_reject_kind',lambda:rows.make_scope(definition,'candidate',[0,8],contract,'other'),ValueError)
    expect('scope_reject_digest',lambda:rows.make_scope(definition,'candidate',[0,8],'A'*64,'local-fixture'),ValueError)
    for name,mutator in [('ascending',lambda d:d['expected_header'].__setitem__('foff_mhz',1.0)),
                          ('rows',lambda d:d['expected_header']['dataset_shape'].__setitem__(0,17)),
                          ('feeds',lambda d:d['expected_header']['dataset_shape'].__setitem__(1,2))]:
        bad=copy.deepcopy(definition);mutator(bad)
        expect('scope_reject_'+name,lambda bad=bad:rows.make_scope(bad,'candidate',[0,8],contract,'local-fixture'),ValueError)
    # Persist 16 source rows at each of the three actual windows, using only new
    # in-memory synthetic arrays whose hashes match the already pinned codec48.
    products=[];baselines=[]
    codec_hashes={(item['row'],item['role']):item['selected_sha256'] for item in codec['decode_receipts']}
    for window in windows:
        scope,h,check=checked(definition,window);check(h)
        directory=OUT/('product_'+window['role'])
        inventory,resumed=expect('extract_'+window['role'],lambda:rows._extract_rows(h,scope,directory))
        if resumed or h.dataset.payload_reads!=16:raise AssertionError('fresh source extraction count differs')
        for receipt in inventory:
            if receipt['native_sha256']!=codec_hashes[(receipt['row'],window['role'])]:raise AssertionError('codec/normalization synthetic input differs')
        proof={'kind':'candidate-synthetic-array-owned','telescope_provenance':False,'network_requests':0}
        complete=expect('complete_'+window['role'],lambda:rows._complete(directory,scope,inventory,proof))
        restored=expect('rehydrate_'+window['role'],lambda:rows.rehydrate(directory,complete['receipt_sha256'],required_kind='local-fixture'))
        if restored!=complete:raise AssertionError('receipt reconstruction differs')
        h.dataset.forbid_reads=True
        again,again_resumed=expect('resume_'+window['role'],lambda:rows._extract_rows(h,scope,directory))
        if again!=inventory or again_resumed!=16 or h.dataset.payload_reads!=16:raise AssertionError('synthetic persistence resume differs')
        repeated=expect('complete_idempotent_'+window['role'],lambda:rows._complete(directory,scope,inventory,proof))
        if repeated!=complete:raise AssertionError('idempotent source completion differs')
        baselines.append((directory,scope,inventory,complete))
        products.append({'role':window['role'],'rows':16,'fresh_payload_reads':16,'resumed_rows':16,
            'receipt_sha256':complete['receipt_sha256'],'source_file':pin(directory/'source.json'),
            'scope_sha256':rows.digest(scope),'codec48_selected_inputs_match':True,
            'row_receipts':inventory})
        budget()
    base,scope,inventory,complete=baselines[0]
    baseline_files={str(p):pin(p) for directory,_,_,_ in baselines for p in directory.iterdir() if p.is_file()}
    expect('rehydrate_reject_default_telescope_kind',lambda:rows.rehydrate(base,complete['receipt_sha256']),ValueError)
    expect('rehydrate_reject_wrong_trust',lambda:rows.rehydrate(base,'0'*64,required_kind='local-fixture'),ValueError)
    expect('complete_reject_missing_rows',lambda:rows._complete(base,scope,inventory[:-1],{}),ValueError)
    expect('complete_reject_reordered_rows',lambda:rows._complete(base,scope,list(reversed(inventory)),{}),ValueError)
    altered=copy.deepcopy(inventory);altered[0]['row']=1
    expect('complete_reject_unsealed_row',lambda:rows._complete(base,scope,altered,{}),ValueError)
    # Every mutation has its own directory; original products are immutable.
    def mutation_dir(name):
        directory=OUT/('negative_'+name);directory.mkdir()
        for filename in ('scope.json','source.json','row00.json','row00.native.npy','row00.normalized.npy'):
            shutil.copyfile(base/filename,directory/filename)
        return directory
    def replace_json(path,value):path.write_bytes(canonical(value))
    for name,mutator in [('scope_mapping',lambda r:r['scope']['geometry'].__setitem__('raw_zero_hz',r['scope']['geometry']['raw_zero_hz']+1)),
                          ('missing_rows',lambda r:r.__setitem__('rows',r['rows'][:-1])),
                          ('wrong_kind',lambda r:r['scope'].__setitem__('kind','telescope-remote')),
                          ('incomplete',lambda r:r.__setitem__('complete',False))]:
        d=mutation_dir(name);r=copy.deepcopy(complete);mutator(r);r=rows.seal({k:v for k,v in r.items() if k!='receipt_sha256'})
        replace_json(d/'source.json',r)
        expect('rehydrate_reject_'+name,lambda d=d,r=r:rows.rehydrate(d,r['receipt_sha256'],required_kind='local-fixture'),ValueError)
    d=mutation_dir('unsealed_source');r=copy.deepcopy(complete);r['complete']=False;replace_json(d/'source.json',r)
    expect('rehydrate_reject_unsealed_source',lambda:rows.rehydrate(d,complete['receipt_sha256'],required_kind='local-fixture'),ValueError)
    for name,mode in [('native_dtype','dtype'),('native_shape','shape'),('native_nonfinite','nan'),
                      ('wrong_normalized','normalized'),('wrong_ascending_hash','ascending'),('wrong_file_hash','file'),('wrong_row_order','order')]:
        d=mutation_dir(name);r=json.loads((d/'row00.json').read_bytes())
        if mode=='order':r['row']=1
        elif mode=='ascending':r['ascending_raw_sha256']='0'*64
        elif mode=='file':r['native_file_sha256']='0'*64
        else:
            key='normalized' if mode=='normalized' else 'native';path=d/('row00.'+key+'.npy')
            values=np.load(path,allow_pickle=False)
            if mode=='dtype':values=values.astype('<f8')
            elif mode=='shape':values=values[:-1]
            elif mode=='nan':values[0]=np.nan
            elif mode=='normalized':values=np.roll(values,1)
            rows.atomic_npy(path,values);r[key+'_file_sha256']=rows.file_hash(path);r[key+'_sha256']=rows.array_hash(values)
        r=rows.seal({k:v for k,v in r.items() if k!='receipt_sha256'});replace_json(d/'row00.json',r)
        expect('row_reject_'+name,lambda d=d:rows._check_row(d,scope,0),ValueError)
    # Wrong hyperslab type/shape is rejected before persistence of row data.
    for mode in ('float64','short','not-array','nan'):
        d=SyntheticDataset(definition,windows[0]);d.payload_mode=mode;s,h,check=checked(definition,windows[0],d)
        expect('extract_reject_'+mode,lambda mode=mode:rows._extract_rows(h,s,OUT/('bad_hyperslab_'+mode)),ValueError)
    # The pure inherited checkpoint law authenticates no transport transaction.
    identity={'url':'https://candidate.invalid/synthetic','size':64,'etag':'"candidate"'}
    checkpoint={'artifact_type':transport.CHECKPOINT_ARTIFACT,'schema_version':1,'remote':identity,'segments':[]}
    def reseal_checkpoint(record):
        record={k:v for k,v in record.items() if k!='checkpoint_sha256'}
        return {**record,'checkpoint_sha256':transport._sha256_bytes(transport._canonical_json_bytes(record))}
    cp=reseal_checkpoint(checkpoint)
    expect('checkpoint_exact_metadata',lambda:rows.verify_transport_checkpoint(cp,identity))
    for name,mutator in [('remote',lambda x:x['remote'].__setitem__('size',65)),
                          ('artifact',lambda x:x.__setitem__('artifact_type','wrong')),('schema',lambda x:x.__setitem__('schema_version',2))]:
        bad=copy.deepcopy(checkpoint);mutator(bad);bad=reseal_checkpoint(bad)
        expect('checkpoint_reject_'+name,lambda bad=bad:rows.verify_transport_checkpoint(bad,identity),ValueError)
    bad=copy.deepcopy(cp);bad['checkpoint_sha256']='0'*64
    expect('checkpoint_reject_digest',lambda:rows.verify_transport_checkpoint(bad,identity),ValueError)
    for name,expected in PINS.items():
        if pin(ROOT/name)['sha256']!=expected:raise AssertionError('held source/input changed')
    if pin(CODEC_REPORT)!=codec_pin:raise AssertionError('codec48 report changed')
    if any(pin(Path(path))!=before for path,before in baseline_files.items()):raise AssertionError('positive product changed')
    if any(name=='seti_repeater' or name.startswith('seti_repeater.') for name in sys.modules):raise AssertionError('project module imported')
    if 'h5py' in sys.modules or 'hdf5plugin' in sys.modules:raise AssertionError('unnecessary HDF5 capability loaded')
    prospective=ast.parse((ROOT/'src/seti_repeater/prospective_source_metadata_radio.py').read_bytes())
    missing=next(ast.literal_eval(n.value) for n in prospective.body if isinstance(n,ast.Assign) and
        any(isinstance(t,ast.Name) and t.id=='MISSING_FIELDS' for t in n.targets))
    budget()
    generated=[pin(p) for p in sorted(OUT.rglob('*')) if p.is_file()]
    result={'schema':'radio-source-normalization-receipt-candidate-laws-v1','status':'PASS','authority':'candidate-only synthetic preparation',
        'script_pin':pin(Path(__file__)),'input_pins':inputs,'actual_function_and_constant_pins':FUNCTION_PINS,
        'codec48_report_pin':codec_pin,'case_count':len(CASES),'cases':CASES,'source_scan_window_scopes':source_scopes,
        'independent_normalization_kats':kats,'synthetic_products':products,'positive_product_files_unchanged':True,
        'generated_files':generated,'generated_file_logical_bytes':sum(x['bytes'] for x in generated),
        'generated_file_allocated_bytes':sum(x['allocated_bytes'] for x in generated),
        'runtime':{'python':sys.version,'numpy':np.__version__,'interpreter':pin(Path(sys.executable)),
                   'isolated':bool(sys.flags.isolated),'dont_write_bytecode':sys.dont_write_bytecode},
        'resource_limits':LIMITS,'observed_seconds':time.monotonic()-START,
        'observed_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'source_modules_imported':0,'synthetic_hyperslabs_read':48,'metadata_guard_payload_reads':0,
        'network_requests':0,'archived_HDF5_or_telescope_or_holdout_files_opened':0,'rng_draws':0,
        'scientific_functions_invoked':0,'native_reservations_or_executions':0,
        'scientific_missing_fields_unchanged':list(missing),'complete_execution_runtime_freeze':False,
        'externally_observed_complete_lifetime':False,'authenticated_public_source_certificate':False,
        'source_or_scientific_admission':False,'receiver_handoff_qualified':False,'hosted_transport_qualified':False,
        'source_specific_executable_contract_created':False,
        'coverage_limitations':['one scan synthetic row persistence at three retained windows; all six scan/window metadata scopes',
            'pure allowlisted function execution; no complete acquisition/source module import route',
            'local-fixture receipts only; no telescope provenance','no receiver handoff, hosted transport or scientific 127/24 execution',
            'no independent public evidence authentication or external whole-source lifetime/resource certificate']}
    write(OUT/'result.json',result)
    print(json.dumps({'status':'PASS','case_count':len(CASES),'products':3,'synthetic_rows':48,'report':pin(OUT/'result.json')},sort_keys=True))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        if OUT.exists() and not (OUT/'failure.json').exists():
            write(OUT/'failure.json',{'schema':'radio-source-normalization-candidate-failure-v1','error':repr(error),
                'traceback':traceback.format_exc(),'authority':'candidate-only','scientific_admission':False,'automatic_retry':False})
        raise
