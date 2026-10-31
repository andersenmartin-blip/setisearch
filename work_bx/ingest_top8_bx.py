"""Pinned, bounded ingestion of the authors' selected TOP8 archive.

`inspect` only parses pickle opcodes. `decode` uses a closed global allowlist
and a bounded ndarray BUILD proxy, then preserves powers without scoring.
No frequency-axis interpretation is inferred from a two-endpoint frequency list.
"""
from pathlib import Path
import argparse, collections, hashlib, io, json, math, os, pickle, pickletools
import resource, signal
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key] = '1'
import numpy as np

SOURCE = dict(repository='PetchMa/ML_GBT_SETI', commit='5f9c006a2960683969d9face28119af4d5b410b5',
              path='data_archive/top_8_data.pkl', bytes=12613542,
              git_blob_sha1='22b89220de8d38c07f6e3f2813ba0e39535b367f')
MAX_ARRAY_BYTES = 32*1024**2

def need(ok, message):
    if not ok: raise ValueError(message)

def digest(raw): return hashlib.sha256(raw).hexdigest()

def read_verified(path, expected=SOURCE):
    p = Path(path); need(p.is_file() and not p.is_symlink(), 'Regular nonsymlink input required')
    need(p.stat().st_size == expected['bytes'] <= 20*1024**2, 'Pinned input size differs')
    raw = p.read_bytes()
    actual = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    need(len(raw) == expected['bytes'] and actual == expected['git_blob_sha1'], 'Pinned Git blob differs')
    return raw, dict(**expected, sha256=digest(raw))

def inspect_opcodes(raw):
    counts=collections.Counter(); globals_seen=[]; recent=[]; protocols=[]; stop=None
    for op,arg,pos in pickletools.genops(raw):
        counts[op.name]+=1
        if op.name == 'PROTO': protocols.append(arg)
        need(sum(counts.values()) <= 200000, 'Opcode count exceeds finite bound')
        if op.name in ('EXT1','EXT2','EXT4','PERSID','BINPERSID','NEXT_BUFFER','READONLY_BUFFER'):
            raise ValueError('Unsupported external/extension pickle opcode: '+op.name)
        if op.name in ('GLOBAL','STACK_GLOBAL'):
            globals_seen.append(dict(opcode=op.name,position=pos,
                name=arg if op.name=='GLOBAL' else None,
                preceding_context=recent[-8:] if op.name=='STACK_GLOBAL' else []))
        if op.name == 'STOP': stop=pos
        small = arg if isinstance(arg,(int,float)) or arg is None else (arg[:160] if isinstance(arg,str) else '<bytes>')
        recent.append(dict(opcode=op.name, argument=small, position=pos));recent=recent[-8:]
    need(stop == len(raw)-1, 'Trailing data or missing final STOP')
    return dict(protocols=protocols,opcode_counts=dict(sorted(counts.items())),globals=globals_seen,
                stack_global_names_resolved=False,inspection='Opcode structure only; no unpickling or array decoding')

def safe_dtype(*args):
    value=np.dtype(*args)
    need(not value.hasobject and value.fields is None and value.subdtype is None
         and value.kind in 'biufcSU' and value.itemsize <= 1024, 'Unsafe dtype')
    return value

class ArrayProxy:
    def __setstate__(self,state):
        need(isinstance(state,tuple) and len(state)==5, 'Unexpected ndarray state')
        version,shape,dtype,fortran,raw=state
        need(version==1 and isinstance(shape,tuple) and len(shape)<=5
             and all(type(x) is int and 0<=x<=1048576 for x in shape), 'Unsafe ndarray shape/version')
        need(type(fortran) is bool and isinstance(raw,bytes), 'Only in-band byte arrays supported')
        dtype=safe_dtype(dtype); count=math.prod(shape)
        need(count*dtype.itemsize == len(raw) <= MAX_ARRAY_BYTES, 'Array byte count differs/exceeds cap')
        self.array=np.frombuffer(raw,dtype=dtype,count=count).reshape(shape,order='F' if fortran else 'C')

def reconstruct(subtype,shape,dtype):
    need(subtype is ArrayProxy and shape==(0,) and dtype==b'b', 'Unexpected ndarray reconstruction')
    return ArrayProxy()

def scalar(dtype,raw):
    dtype=safe_dtype(dtype)
    need(isinstance(raw,bytes) and len(raw)==dtype.itemsize, 'Invalid NumPy scalar bytes')
    return np.frombuffer(raw,dtype=dtype,count=1)[0]

class RestrictedUnpickler(pickle.Unpickler):
    def find_class(self,module,name):
        table={('numpy','ndarray'):ArrayProxy,('numpy','dtype'):safe_dtype}
        for prefix in ('numpy.core.multiarray','numpy._core.multiarray'):
            table[(prefix,'_reconstruct')]=reconstruct;table[(prefix,'scalar')]=scalar
        need((module,name) in table, 'Forbidden pickle global: '+module+'.'+name)
        return table[(module,name)]
    def persistent_load(self,pid): raise ValueError('Persistent pickle references forbidden')

def unpickle_restricted(raw):
    inspect_opcodes(raw)
    return RestrictedUnpickler(io.BytesIO(raw)).load()

def json_value(value,depth=0):
    need(depth<=20,'Metadata nesting exceeds cap')
    if value is None or type(value) in (str,bool,int): return value
    if type(value) is float:
        need(math.isfinite(value),'Nonfinite header value');return value
    if isinstance(value,np.generic): return json_value(value.item(),depth+1)
    if isinstance(value,bytes): return {'__bytes_hex__':value.hex()}
    if isinstance(value,ArrayProxy): return {'__ndarray__':value.array.tolist(),'dtype':value.array.dtype.str,'shape':list(value.array.shape)}
    if isinstance(value,(tuple,list)): return [json_value(x,depth+1) for x in value]
    if isinstance(value,dict):
        need(all(type(k) is str for k in value),'Header dictionary keys must be text')
        return {k:json_value(v,depth+1) for k,v in value.items()}
    raise ValueError('Unsupported metadata value type: '+type(value).__name__)

def validate(value):
    need(type(value) is dict and set(value)=={'mlc'+str(i) for i in range(1,9)},'Exactly eight named candidates required')
    result={};total=0
    for name,item in sorted(value.items()):
        need(type(item) is dict,'Candidate record must be a dictionary')
        header_keys=set(item)&{'all_headers','all_header'}
        need(len(header_keys)==1 and set(item)=={'data','frequency'}|header_keys,'Unexpected candidate fields')
        key=next(iter(header_keys)); data=item['data']
        need(isinstance(data,ArrayProxy),'Data must be a NumPy array');a=data.array
        need(a.shape in ((6,16,1,256),(6,16,1,4096)) and a.dtype.kind=='f' and a.dtype.itemsize in (4,8),'Unexpected candidate shape/dtype')
        need(np.isfinite(a).all() and (a>=0).all(),'Powers must be finite and nonnegative')
        frequency=item['frequency']; f=frequency.array if isinstance(frequency,ArrayProxy) else np.asarray(frequency)
        need(f.ndim==1 and f.size in (2,a.shape[-1]) and f.dtype.kind in 'iuf' and np.isfinite(f).all(),'Unexpected frequency metadata')
        headers=item[key];need(isinstance(headers,(list,tuple)) and len(headers)==6 and all(type(h) is dict for h in headers),'Six original header dictionaries required')
        total+=a.nbytes+f.nbytes;need(total<=MAX_ARRAY_BYTES,'Total decoded bytes exceed cap')
        result[name]=(a,f,dict(observed_keys=sorted(item),header_key=key,headers=json_value(headers),
            data_shape=list(a.shape),data_dtype=a.dtype.str,frequency_shape=list(f.shape),
            frequency_values=json_value(f.tolist()),frequency_units_and_endpoint_semantics='UNRESOLVED; use author extraction code before signal analysis'))
    return result

def save_json(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['inspect','decode']);parser.add_argument('input',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    need(np.__version__=='2.3.5','Pinned NumPy runtime differs')
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('Ingestion wall cap exceeded')));signal.alarm(45)
    raw,receipt=read_verified(args.input);opcodes=inspect_opcodes(raw);args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    save_json(args.output/'SOURCE_RECEIPT.json',receipt);save_json(args.output/'OPCODE_INSPECTION.json',opcodes)
    if args.mode=='decode':
        values=validate(unpickle_restricted(raw));inventory=[]
        for name,(data,frequency,metadata) in values.items():
            for label,array in [('data',data),('frequency',frequency)]:
                path=args.output/(name+'_'+label+'.npy')
                with path.open('xb') as f:np.save(f,array,allow_pickle=False)
                inventory.append(dict(path=path.name,bytes=path.stat().st_size,sha256=digest(path.read_bytes())))
            save_json(args.output/(name+'_metadata.json'),metadata)
        save_json(args.output/'DECODE_COMPLETE.json',dict(status='PASS_BOUNDED_SAFE_INGEST',source=receipt,arrays=inventory,signal_analysis_performed=False))
    need(read_verified(args.input)[1]==receipt,'Input changed during ingestion');signal.alarm(0)
    print(json.dumps(dict(mode=args.mode,status='PASS',output=str(args.output),source_sha256=receipt['sha256'],signal_analysis_performed=False)))

if __name__=='__main__':main()
