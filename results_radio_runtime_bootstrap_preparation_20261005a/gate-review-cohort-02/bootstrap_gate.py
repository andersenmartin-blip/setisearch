"""Single-use, independently pinned engineering wheel acquisition/offline installer.

Importing this module grants no execution authority. No native scientific package
is imported here. The only child is an isolated, pinned pure-Python pip seed.
"""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import selectors
import stat
import subprocess
import sys
import time

SCHEMA = 'radio-runtime-package-bootstrap-supervisor-v1'
PROOF_SCHEMA = 'radio-runtime-package-bootstrap-publication-readback-v1'
MARKER_SCHEMA = 'radio-runtime-package-bootstrap-activation-v1'
ACTIVATION_REPOSITORY_PATH = 'config/radio_runtime_bootstrap_20261005a.activate.json'
BASIS_SHA256 = 'c0736896f9a1aee3598c11e11149057553e30fc4f436a5600086dad51352251c'
PIN_KEYS = {'path', 'bytes', 'sha256', 'mode'}
CONTRACT_KEYS = {'schema','bootstrap_identity','evidence_domain','source_pins','runtime_pins',
    'seed_pins','python_executable','python_sha256','attribution_basis_path','wheel_io_path',
    'plan_path','plan_sha256','wheel_lock_utf8','output_root','output_root_identity',
    'spent_path','activation_path','wheels','limits','expected_versions'}
LIMIT_KEYS = {'wall_seconds','child_seconds','reap_seconds','artifact_bytes','address_space_bytes',
    'parent_read_bytes','child_read_reserve_bytes','joined_read_bytes','stream_bytes',
    'sample_count','file_bytes','file_count','directory_count','terminal_reserve_bytes'}
CEILINGS = {'wall_seconds':300,'child_seconds':260,'reap_seconds':10,
    'artifact_bytes':1536*1024**2,'address_space_bytes':1024**3,
    'parent_read_bytes':3*1024**3,'child_read_reserve_bytes':1024**3,
    'joined_read_bytes':4*1024**3,'stream_bytes':1024**2,'sample_count':1200,
    'file_bytes':128*1024**2,'file_count':20000,'directory_count':4096,
    'terminal_reserve_bytes':8*1024**2}
PROOF_KEYS = {'schema','repository','branch','prepared_commit','prepared_tree',
    'activation_commit','activation_tree','activation_parent','activation_changed_path',
    'contract_sha256','publication_files','activation_sha256','bootstrap_identity',
    'plan_sha256','provenance'}
MARKER_KEYS = {'schema','bootstrap_identity','prepared_commit','prepared_tree',
    'contract_sha256','engineering_only','single_use'}
EXPECTED_VERSIONS = {'numpy':'2.3.5','h5py':'3.16.0','hdf5plugin':'7.1.0'}
AUTHORITY = dict.fromkeys(('acquisition_authorized','allocation_created','cas_qualified',
    'certificate_issued','download_authorized','execution_authorized','hosted_transport_qualified',
    'installation_authorized','metadata_capture_dispatch_authorized','reservation_authorized',
    'rng_authorized','runtime_import_authorized','runtime_qualified','scientific_execution_authorized',
    'source_contract_admitted','spectral_access_authorized'),False)
SAMPLE_BYTES = 512*1024
MAX_PAYLOAD = 512*1024**2
FINAL_EXCLUSIONS = ['artifact-manifest.json','supervisor-result.json']


class Refusal(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def hex_value(value, length=64):
    return type(value) is str and len(value)==length and all(c in '0123456789abcdef' for c in value)


def absolute(value):
    if type(value) is not str or not value.startswith('/') or str(Path(value))!=value or '..' in Path(value).parts or '\x00' in value:
        raise Refusal('noncanonical absolute path')
    return value


def safe_relative(value):
    if type(value) is not str or not value or value.startswith('/') or '\\' in value or any(ord(c)<32 or ord(c)==127 for c in value):
        raise Refusal('unsafe relative path')
    if any(p in ('','.','..') for p in value.split('/')) or len(value.split('/'))>64:
        raise Refusal('unsafe relative components')
    return value


def pinned_json(raw, expected):
    if type(raw) is not bytes or not hex_value(expected) or digest(raw)!=expected:
        raise Refusal('external raw pin mismatch')
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:
                raise Refusal('duplicate JSON field')
            result[k]=v
        return result
    try:
        return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(Refusal('nonfinite JSON')))
    except (ValueError,UnicodeError) as exc:
        raise Refusal('invalid pinned JSON') from exc


def validate_pin(pin):
    if type(pin) is not dict or set(pin)!=PIN_KEYS or type(pin['bytes']) is not int or pin['bytes']<0 or not hex_value(pin['sha256']) or type(pin['mode']) is not str or len(pin['mode'])!=4 or any(c not in '01234567' for c in pin['mode']):
        raise Refusal('selected pin schema')
    absolute(pin['path'])


def validate_contract(raw, expected):
    obj=pinned_json(raw,expected)
    if type(obj) is not dict or set(obj)!=CONTRACT_KEYS or obj['schema']!=SCHEMA:
        raise Refusal('bootstrap exact contract schema')
    if obj['evidence_domain'] not in ('package-bootstrap-only','synthetic-test-fixture') or not hex_value(obj['bootstrap_identity']):
        raise Refusal('fresh engineering identity/domain')
    for key in ('python_sha256','plan_sha256'):
        if not hex_value(obj[key]): raise Refusal('detached source hash law')
    for key in ('python_executable','attribution_basis_path','wheel_io_path','plan_path','output_root','spent_path','activation_path'):
        absolute(obj[key])
    if not obj['activation_path'].endswith('/'+ACTIVATION_REPOSITORY_PATH):
        raise Refusal('fixed fresh activation path')
    if Path(obj['spent_path']).parent!=Path(obj['output_root']) or Path(obj['spent_path']).name!='spent.json':
        raise Refusal('fixed root spent path')
    identity=obj['output_root_identity']
    if type(identity) is not dict or set(identity)!={'device','inode','mode'} or type(identity['device']) is not int or identity['device']<0 or type(identity['inode']) is not int or identity['inode']<=0 or identity['mode']!='0700':
        raise Refusal('externally pinned fresh root identity')
    limits=obj['limits']
    if type(limits) is not dict or set(limits)!=LIMIT_KEYS or any(type(v) is not int or v<=0 for v in limits.values()) or any(limits[k]>CEILINGS[k] for k in limits):
        raise Refusal('finite bootstrap limits')
    if limits['parent_read_bytes']+limits['child_read_reserve_bytes']>limits['joined_read_bytes'] or limits['child_seconds']+limits['reap_seconds']+2>limits['wall_seconds'] or limits['terminal_reserve_bytes']<1024**2 or limits['terminal_reserve_bytes']+2*limits['stream_bytes']>=limits['artifact_bytes']:
        raise Refusal('joined/terminal resource envelope')
    if type(obj['source_pins']) is not list or type(obj['runtime_pins']) is not list:
        raise Refusal('explicit source/runtime inventory')
    pins=obj['source_pins']+obj['runtime_pins']
    if not pins or len(pins)>4096: raise Refusal('finite selected inventory')
    for pin in pins: validate_pin(pin)
    if len({p['path'] for p in pins})!=len(pins) or any(rows!=sorted(rows,key=lambda p:p['path']) for rows in (obj['source_pins'],obj['runtime_pins'])):
        raise Refusal('selected inventory order/duplicates')
    selected={p['path']:p for p in pins}
    source={p['path']:p for p in obj['source_pins']}
    required=(str(Path(__file__).resolve()),obj['attribution_basis_path'],obj['wheel_io_path'],obj['plan_path'])
    if any(p not in source for p in required) or obj['python_executable'] not in selected or selected[obj['python_executable']]['sha256']!=obj['python_sha256'] or source[obj['plan_path']]['sha256']!=obj['plan_sha256']:
        raise Refusal('complete supervisor/helper/plan/interpreter pins')
    if obj['evidence_domain']=='package-bootstrap-only' and source[obj['attribution_basis_path']]['sha256']!=BASIS_SHA256:
        raise Refusal('exact published B attribution basis required')
    seeds=obj['seed_pins']
    if type(seeds) is not list or not seeds or len(seeds)>4096: raise Refusal('finite pinned pip seed inventory')
    relative=[]
    for seed in seeds:
        if type(seed) is not dict or set(seed)!=PIN_KEYS|{'relative_path'}: raise Refusal('seed pin schema')
        pin={k:seed[k] for k in PIN_KEYS}; validate_pin(pin)
        safe_relative(seed['relative_path'])
        if seed['relative_path'].endswith(('.pyc','.pyo')) or not seed['relative_path'].startswith(('pip/','pip-26.2.1.dist-info/')) or selected.get(seed['path'])!=pin or pin not in obj['runtime_pins']:
            raise Refusal('frozen pure pip source/data inventory')
        relative.append(seed['relative_path'])
    if len(set(relative))!=len(relative) or relative!=sorted(relative) or 'pip/__main__.py' not in relative or sum(p['bytes'] for p in seeds)>64*1024**2:
        raise Refusal('seed order/entry point/finite seed bytes')
    if obj['expected_versions']!=EXPECTED_VERSIONS or type(obj['wheels']) is not list or len(obj['wheels'])!=3 or {w.get('name'):w.get('version') for w in obj['wheels'] if type(w) is dict}!=EXPECTED_VERSIONS:
        raise Refusal('exact three package identities')
    if type(obj['wheel_lock_utf8']) is not str or len(obj['wheel_lock_utf8'].encode())>65536 or '\x00' in obj['wheel_lock_utf8']:
        raise Refusal('finite original offline wheel lock')
    for wheel in obj['wheels']:
        if type(wheel) is not dict or set(wheel)!={'bytes','filename','url','sha256','name','version','tags'} or type(wheel['bytes']) is not int or wheel['bytes']<=0 or wheel['bytes']>limits['file_bytes'] or not hex_value(wheel['sha256']):
            raise Refusal('exact wheel acquisition rows')
        safe_relative(wheel['filename'])
        if '/' in wheel['filename'] or not wheel['filename'].endswith('.whl'): raise Refusal('wheel archive basename')
        if wheel['name']+'=='+wheel['version'] not in obj['wheel_lock_utf8'] or '--hash=sha256:'+wheel['sha256'] not in obj['wheel_lock_utf8']:
            raise Refusal('wheel lock lacks exact version/hash')
    if obj['evidence_domain']=='package-bootstrap-only' and sum(w['bytes'] for w in obj['wheels'])!=68409067:
        raise Refusal('original three archive total changed')
    return obj


def verify_publication(contract,contract_hash,proof_raw,proof_hash,marker_raw,marker_hash):
    proof=pinned_json(proof_raw,proof_hash); marker=pinned_json(marker_raw,marker_hash)
    if type(proof) is not dict or set(proof)!=PROOF_KEYS or proof['schema']!=PROOF_SCHEMA or proof['repository']!='andersenmartin-blip/setisearch' or proof['branch']!='m43-support-qualification':
        raise Refusal('detached preparation/activation provenance schema')
    for k in ('prepared_commit','prepared_tree','activation_commit','activation_tree','activation_parent'):
        if not hex_value(proof[k],40): raise Refusal('immutable Git identity')
    if proof['activation_parent']!=proof['prepared_commit'] or proof['activation_commit']==proof['prepared_commit'] or proof['activation_tree']==proof['prepared_tree'] or proof['activation_changed_path']!=ACTIVATION_REPOSITORY_PATH:
        raise Refusal('distinct marker-only activation provenance')
    if proof['bootstrap_identity']!=contract['bootstrap_identity'] or proof['contract_sha256']!=contract_hash or proof['activation_sha256']!=marker_hash or proof['plan_sha256']!=contract['plan_sha256'] or type(proof['provenance']) is not str or not proof['provenance'] or len(proof['provenance'])>2048:
        raise Refusal('externally bound publication identities')
    expected_marker={'schema':MARKER_SCHEMA,'bootstrap_identity':contract['bootstrap_identity'],
        'prepared_commit':proof['prepared_commit'],'prepared_tree':proof['prepared_tree'],
        'contract_sha256':contract_hash,'engineering_only':True,'single_use':True}
    if type(marker) is not dict or set(marker)!=MARKER_KEYS or marker!=expected_marker:
        raise Refusal('fresh irreversible activation exact bindings')
    rows=proof['publication_files']
    if type(rows) is not list or len(rows)!=len(contract['source_pins']): raise Refusal('full source immutable readback')
    for row,pin in zip(rows,contract['source_pins']):
        if type(row) is not dict or set(row)!=PIN_KEYS|{'content_base64','git_blob','repository_path'} or {k:row[k] for k in PIN_KEYS}!=pin or not hex_value(row['git_blob'],40):
            raise Refusal('publication fullcontent pin row')
        safe_relative(row['repository_path'])
        try: raw=base64.b64decode(row['content_base64'],validate=True)
        except (ValueError,TypeError) as exc: raise Refusal('publication base64 raw body') from exc
        if len(raw)!=pin['bytes'] or digest(raw)!=pin['sha256'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['git_blob']:
            raise Refusal('publication exact raw body/hash/blob')
    return proof


def held_file(path,cap,charge=None,received=None):
    """Nofollow every ancestor; authenticate held/named identities after read."""
    parts=Path(absolute(path)).parts[1:]
    if not parts or len(parts)>64: raise Refusal('finite file path')
    dirs=[os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)]
    links=[]; fd=None
    try:
        for component in parts[:-1]:
            child=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=dirs[-1])
            item=os.fstat(child); links.append((dirs[-1],component,item.st_dev,item.st_ino)); dirs.append(child)
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=dirs[-1]); before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>cap: raise Refusal('sole-link finite regular file required')
        raw=bytearray()
        while len(raw)<before.st_size:
            size=min(65536,before.st_size-len(raw))
            if charge: charge(size)
            chunk=os.read(fd,size)
            if received: received(len(chunk),'regular')
            if not chunk: raise Refusal('selected file truncated')
            raw.extend(chunk)
        if charge: charge(1)
        probe=os.read(fd,1)
        if received: received(len(probe),'regular')
        if probe: raise Refusal('selected file grew beyond pinned size')
        after=os.fstat(fd); named=os.stat(parts[-1],dir_fd=dirs[-1],follow_symlinks=False)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns,before.st_mode)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns,after.st_mode) or (named.st_dev,named.st_ino,named.st_mode,named.st_nlink)!=(after.st_dev,after.st_ino,after.st_mode,1):
            raise Refusal('selected held/named file drift')
        for directory,name,device,inode in links:
            item=os.stat(name,dir_fd=directory,follow_symlinks=False)
            if not stat.S_ISDIR(item.st_mode) or (item.st_dev,item.st_ino)!=(device,inode): raise Refusal('selected ancestor namespace drift')
        return bytes(raw),before
    finally:
        if fd is not None: os.close(fd)
        for fd in reversed(dirs): os.close(fd)


def pin_read(pin,budget=None):
    validate_pin(pin)
    raw,item=held_file(pin['path'],pin['bytes'],budget.debit_read if budget else None,budget.record_received if budget else None)
    observed={'path':pin['path'],'bytes':len(raw),'sha256':digest(raw),'mode':format(item.st_mode&0o7777,'04o')}
    if observed!=pin: raise Refusal('frozen selected source/runtime pin mismatch')
    return raw,{'device':item.st_dev,'inode':item.st_ino},observed


def compile_verified(raw,path,name):
    namespace={'__name__':name,'__file__':path,'__builtins__':__builtins__}
    exec(compile(raw,path,'exec'),namespace)
    return namespace


def hold_root(path):
    parts=Path(absolute(path)).parts[1:]
    fds=[os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)]; bindings=[]
    try:
        for name in parts:
            child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fds[-1])
            item=os.fstat(child); bindings.append((fds[-1],name,item.st_dev,item.st_ino)); fds.append(child)
        return fds[-1],fds,bindings
    except BaseException:
        for fd in reversed(fds): os.close(fd)
        raise


def root_matches(path,fd,identity,bindings=()):
    held=os.fstat(fd); named=os.stat(path,follow_symlinks=False)
    actual={'device':held.st_dev,'inode':held.st_ino,'mode':format(held.st_mode&0o7777,'04o')}
    if actual!=identity or not stat.S_ISDIR(named.st_mode) or (named.st_dev,named.st_ino)!=(held.st_dev,held.st_ino):
        raise Refusal('owned held/named root drift')
    for parent,name,device,inode in bindings:
        item=os.stat(name,dir_fd=parent,follow_symlinks=False)
        if not stat.S_ISDIR(item.st_mode) or (item.st_dev,item.st_ino)!=(device,inode):
            raise Refusal('owned root ancestor namespace drift')


def inventory(root_fd,limits,deadline,*,hashes=False,budget=None,exclude=()):
    rows=[]; logical=allocated=files=directories=0
    def walk(fd,prefix):
        nonlocal logical,allocated,files,directories
        item=os.fstat(fd); directories+=1
        if directories>limits['directory_count']: raise Refusal('artifact directory cap')
        logical+=item.st_size; allocated+=item.st_blocks*512
        rows.append({'path':prefix or '.','kind':'directory','bytes':item.st_size,
            'allocated_bytes':item.st_blocks*512,'device':item.st_dev,'inode':item.st_ino,'mode':format(item.st_mode&0o7777,'04o')})
        names=os.listdir(fd)
        if len(names)>limits['file_count']+limits['directory_count']: raise Refusal('finite directory entry inventory')
        for name in sorted(names):
            if time.monotonic_ns()>=deadline: raise Refusal('recursive selected storage deadline')
            safe_relative(name); rel=name if not prefix else prefix+'/'+name
            value=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if stat.S_ISDIR(value.st_mode):
                child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
                try:
                    if (os.fstat(child).st_dev,os.fstat(child).st_ino)!=(value.st_dev,value.st_ino): raise Refusal('artifact directory replacement')
                    walk(child,rel)
                    named=os.stat(name,dir_fd=fd,follow_symlinks=False)
                    if (named.st_dev,named.st_ino)!=(value.st_dev,value.st_ino): raise Refusal('artifact directory namespace drift')
                finally: os.close(child)
            elif stat.S_ISREG(value.st_mode) and value.st_nlink==1:
                files+=1
                if files>limits['file_count'] or value.st_size>limits['file_bytes']: raise Refusal('artifact file count/size cap')
                logical+=value.st_size; allocated+=value.st_blocks*512
                row={'path':rel,'kind':'file','bytes':value.st_size,'allocated_bytes':value.st_blocks*512,
                    'device':value.st_dev,'inode':value.st_ino,'mode':format(value.st_mode&0o7777,'04o')}
                if hashes and rel not in exclude:
                    source=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
                    try:
                        held=os.fstat(source)
                        if (held.st_dev,held.st_ino,held.st_nlink)!=(value.st_dev,value.st_ino,1): raise Refusal('manifest file substituted')
                        sha=hashlib.sha256(); remaining=value.st_size
                        while remaining:
                            if time.monotonic_ns()>=deadline: raise Refusal('manifest selected custody deadline')
                            n=min(65536,remaining)
                            if budget: budget.debit_read(n)
                            chunk=os.read(source,n)
                            if not chunk: raise Refusal('manifest file truncated')
                            if budget: budget.record_received(len(chunk),'regular')
                            sha.update(chunk); remaining-=len(chunk)
                        if budget: budget.debit_read(1)
                        if os.read(source,1): raise Refusal('manifest file grew')
                        after=os.fstat(source); named=os.stat(name,dir_fd=fd,follow_symlinks=False)
                        if (held.st_dev,held.st_ino,held.st_size,held.st_mtime_ns,held.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or (named.st_dev,named.st_ino,named.st_nlink)!=(after.st_dev,after.st_ino,1): raise Refusal('manifest custody drift')
                        row['sha256']=sha.hexdigest()
                    finally: os.close(source)
                elif rel in exclude: row['hash_exclusion']='self/final-report cycle explicitly excluded'
                rows.append(row)
            else: raise Refusal('artifact symlink/hardlink/special object refused')
            if max(logical,allocated)>limits['artifact_bytes']: raise Refusal('artifact logical/allocated cap')
    try: walk(root_fd,'')
    except BaseException as exc:
        exc.partial_inventory={'entries':rows,'logical_bytes':logical,'allocated_bytes':allocated,
            'files':files,'directories':directories,'complete':False}
        raise
    return {'entries':rows,'logical_bytes':logical,'allocated_bytes':allocated,
        'files':files,'directories':directories,'complete':True}


class Budget:
    """Conservative pre-syscall charge, with explicit received categories separate."""
    def __init__(self,limits,root,root_fd,identity,deadline,initial=0,bindings=(),initial_received=0):
        self.limits=limits; self.root=root; self.root_fd=root_fd; self.identity=identity; self.deadline=deadline
        self.bytes=initial; self.categories={'regular':initial,'network':0,'proc':0,'zip':0,'pipe':0}
        self.received={'regular':initial_received,'network':0,'zip':0,'pipe':0,'proc':0}
        self.terminal_regular_reserved_bytes=0; self.terminal_pidfd_reserved_bytes=0
        self.terminal_mode=False; self.terminal_reservation=None; self.basis_reads=None
        self.bindings=bindings
        self.directory_guards={root_fd:('',{'device':identity['device'],'inode':identity['inode']})}
    def check(self):
        if time.monotonic_ns()>=self.deadline: raise Refusal('whole bootstrap selected deadline')
        root_matches(self.root,self.root_fd,self.identity,self.bindings)
    def debit_read(self,n): self._debit(n,'regular')
    def debit_network(self,n): self._debit(n,'network')
    def _debit(self,n,kind):
        self.check()
        if type(n) is not int or n<0: raise Refusal('read precharge schema')
        if self.bytes+n+self.terminal_regular_reserved_bytes+self.terminal_pidfd_reserved_bytes>self.limits['parent_read_bytes']:
            raise Refusal('parent explicit read reserve exhausted before syscall')
        self.bytes+=n; self.categories[kind]+=n
    def record_received(self,n,kind='regular'):
        if type(n) is not int or n<0 or kind not in self.received: raise Refusal('received read observation schema')
        if self.received[kind] is not None: self.received[kind]+=n
    def before_write(self,n):
        self.check()
        if type(n) is not int or n<0: raise Refusal('prospective write schema')
        scope=inventory(self.root_fd,self.limits,self.deadline)
        reserve=0 if self.terminal_mode else self.limits['terminal_reserve_bytes']
        if max(scope['logical_bytes'],scope['allocated_bytes'])+n+4096+reserve>self.limits['artifact_bytes']:
            raise Refusal('artifact prospective protected terminal envelope')
    def after_write(self):
        self.check(); scope=inventory(self.root_fd,self.limits,self.deadline)
        reserve=0 if self.terminal_mode else self.limits['terminal_reserve_bytes']
        if max(scope['logical_bytes'],scope['allocated_bytes'])+reserve>self.limits['artifact_bytes']:
            raise Refusal('artifact measured protected terminal envelope')
    def check_directory(self,fd):
        self.check()
        guard=self.directory_guards.get(fd)
        if guard is None: raise Refusal('unregistered held artifact directory')
        relative,expected=guard; held=os.fstat(fd)
        if not stat.S_ISDIR(held.st_mode) or {'device':held.st_dev,'inode':held.st_ino}!=expected:
            raise Refusal('held artifact directory substituted')
        named=os.fstat(self.root_fd) if not relative else os.stat(relative,dir_fd=self.root_fd,follow_symlinks=False)
        if not stat.S_ISDIR(named.st_mode) or (named.st_dev,named.st_ino)!=(held.st_dev,held.st_ino):
            raise Refusal('held/named wheelhouse namespace drift')
    def reserve_terminal(self,n):
        eof=self.limits['file_count']+4096
        pidfd=2*16385
        reserve=n+self.limits['artifact_bytes']+eof+pidfd
        if self.bytes+reserve>self.limits['parent_read_bytes']: raise Refusal('terminal custody read reservation cannot fit')
        self.terminal_regular_reserved_bytes=reserve-pidfd; self.terminal_pidfd_reserved_bytes=pidfd
        self.terminal_reservation={'source_pass_bytes':n,'entire_artifact_manifest_read_ceiling':self.limits['artifact_bytes'],
            'eof_allowance':eof,'pidfd_terminal_bytes':pidfd,'reserved_bytes':reserve}
    def begin_terminal_files(self):
        self.terminal_regular_reserved_bytes=0; self.terminal_pidfd_reserved_bytes=0; self.terminal_mode=True
    def begin_terminal_pidfd(self): self.terminal_pidfd_reserved_bytes=0
    def proc_at(self,directory,leaf,cap):
        self.check()
        if leaf not in ('status','stat') and not(type(leaf) is str and leaf.isdecimal()):
            raise Refusal('held procfs leaf scope')
        if type(cap) is not int or not 0<cap<=16384: raise Refusal('finite held procfs cap')
        fd=None; chunks=[]; began=self.bytes; received_before=self.received['proc']
        try:
            fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
            if not stat.S_ISREG(os.fstat(fd).st_mode): raise Refusal('held procfs regular observation required')
            remaining=cap+1
            while remaining:
                requested=min(65536,remaining)
                self._debit(requested,'proc')
                raw=os.read(fd,requested); self.record_received(len(raw),'proc')
                if not raw: break
                chunks.append(raw); remaining-=len(raw)
            raw=b''.join(chunks)
            if len(raw)>cap: raise Refusal('procfs finite observation cap')
            return raw
        except (Refusal,OSError) as exc:
            held=os.fstat(directory)
            exc.proc_read_evidence={'held_directory':{'device':held.st_dev,'inode':held.st_ino},
                'leaf':leaf,'cap':cap,'raw_received_base64':base64.b64encode(b''.join(chunks)).decode(),
                'charged_bytes':self.bytes-began,'received_bytes':self.received['proc']-received_before,
                'error':type(exc).__name__+':'+str(exc)[:300]}
            raise
        finally:
            if fd is not None: os.close(fd)


def directory(root_fd,relative,budget):
    safe_relative(relative); current=os.dup(root_fd)
    try:
        for name in relative.split('/'):
            try:
                budget.before_write(4096); os.mkdir(name,0o700,dir_fd=current); os.fsync(current); budget.after_write()
            except FileExistsError: pass
            next_fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=current)
            os.fchmod(next_fd,0o700)
            os.close(current); current=next_fd
        return current
    except BaseException:
        os.close(current); raise


def write_new(root_fd,relative,raw,budget,mode=0o600):
    safe_relative(relative)
    parent=directory(root_fd,str(Path(relative).parent),budget) if '/' in relative else os.dup(root_fd)
    fd=None
    try:
        budget.before_write(len(raw)); fd=os.open(Path(relative).name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,mode,dir_fd=parent)
        offset=0
        while offset<len(raw):
            budget.check(); n=os.write(fd,raw[offset:offset+65536])
            if n<=0: raise Refusal('artifact write no progress')
            offset+=n
        os.fchmod(fd,mode); os.fsync(fd); os.fsync(parent); budget.after_write()
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def prospective_install(contract,inspections,budget,seed_bytes,proof_bytes):
    payload=sum(row['payload_bytes'] for row in inspections)
    if payload>MAX_PAYLOAD: raise Refusal('static uncompressed payload exceeds 512 MiB')
    destinations={}; metadata=[]
    for spec,inspection in zip(contract['wheels'],inspections):
        if inspection.get('status') != 'STATIC_WHEEL_PREFLIGHT_VERIFIED':
            # Concrete inspector may use its own status; structural receipts must
            # still have verified=True when that spelling is different.
            if inspection.get('verified') is not True: raise Refusal('wheel inspector verified status absent')
        for member in inspection['members']:
            path=safe_relative(member['path'])
            if any(component.endswith('.data') for component in path.split('/')):
                raise Refusal('wheel .data installation mapping requires separate reviewed law')
            if member['kind']=='file':
                if path in destinations: raise Refusal('cross-wheel regular destination collision')
                destinations[path]=member
        metadata.append({'name':spec['name'],'version':spec['version'],'payload_bytes':inspection['payload_bytes']})
    blocks=max(4096,os.fstatvfs(budget.root_fd).f_frsize)
    if blocks>65536: raise Refusal('filesystem accounting unit outside finite prospective law')
    archive=sum(w['bytes'] for w in contract['wheels'])
    samples=contract['limits']['file_bytes']
    evidence=proof_bytes+2*1024**2+samples+contract['limits']['terminal_reserve_bytes']
    directory_and_rounding=(contract['limits']['file_count']+contract['limits']['directory_count'])*blocks
    planned=3*payload+archive+seed_bytes+evidence+directory_and_rounding+4*1024**2
    if planned>contract['limits']['artifact_bytes']:
        raise Refusal('static payload/temp/evidence/filesystem envelope cannot fit before pip')
    return {'payload_bytes':payload,'payload_ceiling_bytes':MAX_PAYLOAD,'payload_and_temporary_factor':3,
        'archive_bytes':archive,'seed_bytes':seed_bytes,'sample_artifact_ceiling_bytes':samples,
        'filesystem_unit_bytes':blocks,'file_directory_rounding_upper_bytes':directory_and_rounding,
        'conservative_artifact_upper_bytes':planned,'artifact_headroom_bytes':contract['limits']['artifact_bytes']-planned,
        'packages':metadata,'destination_members':len(destinations),'full_peak_certified':False}


def pip_command(contract):
    root=contract['output_root']; installer=root+'/installer'
    # -I -B -S admits only this owned pip seed ahead of the verified stdlib.
    bootstrap="import sys,runpy;sys.path.insert(0,"+repr(installer)+");sys.argv="+repr(['pip','--isolated','--disable-pip-version-check','install','--no-index','--no-deps','--no-cache-dir','--require-hashes','--only-binary=:all:','--no-compile','--progress-bar','off','--target',root+'/site','--find-links',root+'/wheelhouse','-r',root+'/wheel-lock.txt'])+";runpy.run_module('pip',run_name='__main__')"
    return [contract['python_executable'],'-I','-B','-S','-c',bootstrap]


def supervise(command,contract,budget,basis):
    limits=contract['limits']; root=contract['output_root']; samples=[]; receipt=None
    child=status=usage=kernel=None; failure=None; raw_counts={'stdout':0,'stderr':0}; dispatches=0
    selected=selectors.DefaultSelector(); stream_fds={}; sample_fd=None; sample_bytes=0
    def append(fd,raw):
        budget.before_write(len(raw)); offset=0
        while offset<len(raw):
            n=os.write(fd,raw[offset:]);
            if n<=0: raise Refusal('stream retention write no progress')
            offset+=n
        budget.after_write()
    def sample(now):
        nonlocal sample_bytes
        if len(samples)>=limits['sample_count']: raise Refusal('process sample count cap')
        if sample_bytes+SAMPLE_BYTES>limits['file_bytes']: raise Refusal('prospective sample file byte cap')
        budget.before_write(SAMPLE_BYTES)
        item=kernel.observe(budget); item['monotonic_ns']=now
        raw=canonical(item)
        if len(raw)>SAMPLE_BYTES: raise Refusal('finite raw sample record cap')
        append(sample_fd,raw); sample_bytes+=len(raw)
        samples.append({'monotonic_ns':now,'attribution_authenticated':item.get('attribution_authenticated') is True,
            'VmRSS_bytes':item.get('VmRSS_bytes'),'sample_bytes':len(raw)})
        if not item.get('membership_scan_complete') or item.get('observed_process_group_members')!=[item['procfs_pid']] or item['VmRSS_bytes']>limits['address_space_bytes']:
            raise Refusal('observed process group/RSS guard')
    def reap_until(deadline):
        nonlocal status,usage
        while time.monotonic_ns()<deadline:
            waited,current,current_usage=os.wait4(child.pid,os.WNOHANG)
            if waited:
                status,usage=current,current_usage; child.returncode=os.waitstatus_to_exitcode(status)
                if kernel is not None: kernel.mark_reaped(waited,budget)
                return
            time.sleep(0.01)
    def receive_ready(timeout):
        nonlocal failure
        for key,_ in selected.select(timeout):
            name=key.data; requested=min(65536,limits['stream_bytes']+1-raw_counts[name])
            if requested<=0: raise Refusal('raw stream retention probe envelope exhausted')
            budget._debit(requested,'pipe'); raw=os.read(key.fileobj.fileno(),requested); budget.record_received(len(raw),'pipe')
            if not raw:
                selected.unregister(key.fileobj); key.fileobj.close()
            else:
                append(stream_fds[name],raw); raw_counts[name]+=len(raw)
                if raw_counts[name]>limits['stream_bytes']:
                    failure=failure or 'RAW_STREAM_CAP'; selected.unregister(key.fileobj); key.fileobj.close()
                    if status is None: basis['_kill_child_group'](child,kernel)
    try:
        for name in ('stdout','stderr'):
            stream_fds[name]=os.open('child.'+name+'.raw',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=budget.root_fd)
        sample_fd=os.open('procfs-samples.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=budget.root_fd)
        budget.after_write()
        def setup():
            resource.setrlimit(resource.RLIMIT_AS,(limits['address_space_bytes'],limits['address_space_bytes']))
            resource.setrlimit(resource.RLIMIT_FSIZE,(limits['file_bytes'],limits['file_bytes']))
            resource.setrlimit(resource.RLIMIT_CORE,(0,0))
            resource.setrlimit(resource.RLIMIT_CPU,(limits['child_seconds'],limits['child_seconds']+1))
        if budget.deadline-time.monotonic_ns()<13*10**9: raise Refusal('insufficient child/terminal wall room')
        child=subprocess.Popen(command,cwd=root,env={'LANG':'C','LC_ALL':'C','PYTHONHASHSEED':'0',
            'PYTHONDONTWRITEBYTECODE':'1','PIP_CONFIG_FILE':'/dev/null','TMPDIR':root+'/tmp',
            'PIP_NO_INDEX':'1','PIP_DISABLE_PIP_VERSION_CHECK':'1'},stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,start_new_session=True,preexec_fn=setup)
        dispatches=1; launched=time.monotonic_ns()
        for name,stream in (('stdout',child.stdout),('stderr',child.stderr)):
            os.set_blocking(stream.fileno(),False); selected.register(stream,selectors.EVENT_READ,name)
        child_deadline=min(budget.deadline-(limits['reap_seconds']+2)*10**9,launched+limits['child_seconds']*10**9)
        kernel=basis['KernelChild'](child.pid,contract['_verified_python_object'],budget,child_deadline); receipt=kernel.receipt
        sample(time.monotonic_ns())
        next_sample=launched+250_000_000; killed=False
        while status is None or selected.get_map():
            now=time.monotonic_ns(); budget.check(); budget.after_write()
            if now>child_deadline and not killed:
                failure=failure or 'CHILD_DEADLINE'; basis['_kill_child_group'](child,kernel); killed=True
            if now>budget.deadline-2*10**9: failure=failure or 'WHOLE_SCOPE_DEADLINE'; break
            if status is None:
                waited,current,current_usage=os.wait4(child.pid,os.WNOHANG)
                if waited:
                    status,usage=current,current_usage; child.returncode=os.waitstatus_to_exitcode(status); kernel.mark_reaped(waited,budget)
            receive_ready(0.02)
            if status is None and now>=next_sample:
                sample(now); next_sample=now+250_000_000
        if status is None:
            basis['_kill_child_group'](child,kernel)
            reap_until(min(budget.deadline-10**9,time.monotonic_ns()+limits['reap_seconds']*10**9))
            if status is None: failure=failure or 'REAP_DEADLINE'
    except BaseException as exc:
        receipt=getattr(exc,'process_receipt',receipt)
        if receipt is not None and hasattr(exc,'proc_read_evidence'): receipt['proc_read_failure']=exc.proc_read_evidence
        failure=failure or 'SUPERVISOR_EXCEPTION:'+type(exc).__name__+':'+str(exc)[:500]
        if child is not None and status is None:
            try:
                basis['_kill_child_group'](child,kernel)
                reap_until(min(budget.deadline-10**9,time.monotonic_ns()+limits['reap_seconds']*10**9))
                if status is None: failure+=';REAP_DEADLINE'
            except BaseException as cleanup:
                if receipt is not None: receipt['terminal_cleanup_error']=type(cleanup).__name__+':'+str(cleanup)[:300]
        # Even a pre-sample startup failure may have emitted useful pip stderr.
        # Preserve bounded available suffixes after kill/reap; never reopen a PID.
        drain_deadline=min(budget.deadline-10**9,time.monotonic_ns()+10**9)
        try:
            while selected.get_map() and time.monotonic_ns()<drain_deadline:
                receive_ready(0.02)
        except BaseException as drain:
            if receipt is not None: receipt['failure_pipe_drain_error']=type(drain).__name__+':'+str(drain)[:300]
    finally:
        if kernel is not None: kernel.close()
        selected.close()
        for stream in (getattr(child,'stdout',None),getattr(child,'stderr',None)):
            if stream is not None and not stream.closed: stream.close()
        for fd in list(stream_fds.values())+([sample_fd] if sample_fd is not None else []):
            os.fsync(fd); os.close(fd)
    if status is not None and os.waitstatus_to_exitcode(status)!=0: failure=failure or 'PIP_NONZERO'
    return {'failure':failure,'child_pid':child.pid if child else None,'child_exit_code':os.waitstatus_to_exitcode(status) if status is not None else None,
        'wait_status':status,'child_reaped':status is not None,'process_attribution':receipt,
        'authenticated_procfs_samples':sum(p['attribution_authenticated'] for p in samples),'procfs_samples':len(samples),
        'raw_stdout_bytes':raw_counts['stdout'],'raw_stderr_bytes':raw_counts['stderr'],
        'wait4_direct_child_ru_maxrss_bytes':int(usage.ru_maxrss*1024) if usage else None,
        'engineering_child_dispatches':dispatches,'aggregate_descendant_absence_certified':False}


def verify_installed(contract,inspections,manifest):
    rows={r['path']:r for r in manifest['entries'] if r['kind']=='file'}
    verified=0; native=0; versions=[]
    for seed in contract['seed_pins']:
        row=rows.get('installer/'+seed['relative_path'])
        if row is None or row['bytes']!=seed['bytes'] or row.get('sha256')!=seed['sha256'] or row['mode']!=seed['mode']:
            raise Refusal('owned installer seed changed across child')
    for spec,inspection in zip(contract['wheels'],inspections):
        metadata_paths=[]
        for member in inspection['members']:
            if member['kind']!='file': continue
            path=member['path']
            if path.endswith('.dist-info/RECORD'): continue
            installed=rows.get('site/'+path)
            if installed is None or installed['bytes']!=member['bytes'] or installed.get('sha256')!=member['sha256']:
                raise Refusal('installed wheel member fullbyte mismatch:'+path[:160])
            verified+=1
            if '.so' in Path(path).name: native+=1
            if path.endswith('.dist-info/METADATA'): metadata_paths.append(path)
        if len(metadata_paths)!=1: raise Refusal('one installed exact wheel METADATA required')
        versions.append({'name':spec['name'],'version':spec['version'],'metadata_path':'site/'+metadata_paths[0],
            'verified_from_wheel_exact_metadata':True})
    if len(versions)!=3: raise Refusal('three installed package metadata rows required')
    return {'package_versions':versions,'verified_installed_wheel_members':verified,
        'native_members_byte_verified_without_import':native,'native_imports':0,
        'hdf5_runtime_version_observed':None,'runtime_qualification':'PENDING_RUNTIME_QUALIFICATION'}


def run(contract_raw,contract_hash,proof_raw,proof_hash,marker_raw,marker_hash,*,initial_read_bytes=0,initial_read_received_bytes=0,started_monotonic_ns=None):
    began=time.monotonic_ns() if started_monotonic_ns is None else started_monotonic_ns
    if type(initial_read_bytes) is not int or initial_read_bytes<0 or type(initial_read_received_bytes) is not int or not 0<=initial_read_received_bytes<=initial_read_bytes or type(began) is not int or began>time.monotonic_ns(): raise Refusal('selected startup accounting')
    contract=validate_contract(contract_raw,contract_hash); proof=verify_publication(contract,contract_hash,proof_raw,proof_hash,marker_raw,marker_hash)
    if str(Path(sys.executable).resolve())!=contract['python_executable'] or not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
        raise Refusal('pinned parent interpreter and -I -B -S required')
    root=contract['output_root']; limits=contract['limits']; deadline=began+limits['wall_seconds']*10**9
    if Path(root).resolve()!=Path(root): raise Refusal('artifact root ancestor symlink')
    root_fd,root_fds,root_bindings=hold_root(root)
    try:
        root_matches(root,root_fd,contract['output_root_identity'],root_bindings)
        if os.listdir(root_fd): raise Refusal('fresh empty root required; no retry/resume')
        budget=Budget(limits,root,root_fd,contract['output_root_identity'],deadline,initial_read_bytes,root_bindings,initial_read_received_bytes)
        verified={}; objects={}; before=[]
        keep={contract['attribution_basis_path'],contract['wheel_io_path'],contract['plan_path']}|{s['path'] for s in contract['seed_pins']}
        pins=contract['source_pins']+contract['runtime_pins']
        if initial_read_bytes+2*sum(p['bytes']+1 for p in pins)+MAX_PAYLOAD+2*1024**2>limits['parent_read_bytes']:
            raise Refusal('known before/after/final-custody parent read envelope cannot fit')
        for pin in pins:
            raw,obj,observed=pin_read(pin,budget); before.append(observed); objects[pin['path']]=obj
            if pin['path'] in keep: verified[pin['path']]=raw
        if contract['evidence_domain']=='package-bootstrap-only':
            plan=pinned_json(verified[contract['plan_path']],contract['plan_sha256'])
            materialization=plan.get('materialization',{})
            required_wheels=[{k:row[k] for k in ('bytes','filename','url','sha256','name','version','tags')} for row in materialization.get('official_wheels',[])]
            if required_wheels!=contract['wheels'] or materialization.get('offline_hash_lock_utf8')!=contract['wheel_lock_utf8']:
                raise Refusal('complete original plan wheel identities/offline lock changed')
            glibc=os.confstr('CS_GNU_LIBC_VERSION') or ''
            try: glibc_version=tuple(int(v) for v in glibc.split()[1].split('.'))
            except (ValueError,IndexError): raise Refusal('selected glibc version unavailable')
            if sys.version_info[:3]!=(3,12,14) or sys.byteorder!='little' or os.uname().machine!='x86_64' or not glibc.startswith('glibc ') or glibc_version<(2,28):
                raise Refusal('fixed wheel interpreter/platform compatibility')
        marker_local,_=held_file(contract['activation_path'],len(marker_raw),budget.debit_read,budget.record_received)
        if marker_local!=marker_raw: raise Refusal('local activation differs from detached fullbyte witness')
        basis=compile_verified(verified[contract['attribution_basis_path']],contract['attribution_basis_path'],'_verified_bootstrap_attribution')
        wheel_io=compile_verified(verified[contract['wheel_io_path']],contract['wheel_io_path'],'_verified_bootstrap_wheel_io')
        budget.basis_reads=basis['Reads'](limits['parent_read_bytes'])
        budget.reserve_terminal(sum(p['bytes']+1 for p in pins))
        spent={'schema':'radio-runtime-package-bootstrap-spent-v1','bootstrap_identity':contract['bootstrap_identity'],
            'contract_sha256':contract_hash,'publication_proof_sha256':proof_hash,'activation_sha256':marker_hash,
            'prepared_commit':proof['prepared_commit'],'activation_commit':proof['activation_commit'],
            'started_monotonic_ns':began,'spent_monotonic_ns':time.monotonic_ns(),'limits':limits,
            'irreversible':True,'retry_allowed':False,'engineering_bootstrap_authorized':True,
            'engineering_reservation_spent':True,'authority':AUTHORITY}
        # No scope mutation precedes this exclusive, fsynced single-use record.
        write_new(root_fd,'spent.json',canonical(spent),budget)
        failure=None; acquisitions=[]; inspections=[]; child_report=None; preflight=None; installed=None; after=None; manifest=None
        try:
            write_new(root_fd,'admission-witness.json',proof_raw,budget,0o644)
            write_new(root_fd,'selected-runtime-before.json',canonical(before),budget)
            for dirname in ('installer','wheelhouse','site','tmp'):
                fd=directory(root_fd,dirname,budget); os.close(fd)
            for seed in contract['seed_pins']:
                write_new(root_fd,'installer/'+seed['relative_path'],verified[seed['path']],budget,int(seed['mode'],8))
            for seed in contract['seed_pins']:
                copied={k:seed[k] for k in PIN_KEYS}
                copied['path']=root+'/installer/'+seed['relative_path']
                pin_read(copied,budget)
            write_new(root_fd,'wheel-lock.txt',contract['wheel_lock_utf8'].encode(),budget,0o644)
            wheelhouse=os.open('wheelhouse',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
            wheelhouse_stat=os.fstat(wheelhouse)
            budget.directory_guards[wheelhouse]=('wheelhouse',{'device':wheelhouse_stat.st_dev,'inode':wheelhouse_stat.st_ino})
            try:
                for wheel in contract['wheels']:
                    def check_deadline():
                        budget.check(); return max(0.001,(deadline-time.monotonic_ns())/1e9)
                    try: acquisition=wheel_io['acquire_wheel'](wheel,wheelhouse,budget,check_deadline)
                    except BaseException as exc:
                        if hasattr(exc,'receipt'): acquisitions.append(exc.receipt)
                        raise
                    acquisitions.append(acquisition)
                    held=os.open(wheel['filename'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=wheelhouse)
                    try:
                        try: inspection=wheel_io['inspect_wheel'](held,wheel,budget,check_deadline)
                        except BaseException as exc:
                            if hasattr(exc,'receipt'): inspections.append(exc.receipt)
                            raise
                        inspections.append(inspection)
                    finally: os.close(held)
            finally:
                budget.directory_guards.pop(wheelhouse,None); os.close(wheelhouse)
            preflight=prospective_install(contract,inspections,budget,sum(p['bytes'] for p in contract['seed_pins']),len(proof_raw))
            write_new(root_fd,'installation-preflight.json',canonical(preflight),budget)
            contract['_verified_python_object']=objects[contract['python_executable']]
            child_report=supervise(pip_command(contract),contract,budget,basis)
            if child_report['failure']: raise Refusal(child_report['failure'])
        except BaseException as exc:
            failure=type(exc).__name__+':'+str(exc)[:500]
            if hasattr(exc,'partial_inventory'): scope_partial=exc.partial_inventory
            else: scope_partial=None
        budget.begin_terminal_files(); terminal_payload=[]
        try:
            after=[]
            for pin in pins:
                _,_,observed=pin_read(pin,budget); after.append(observed)
        except BaseException as exc:
            failure=failure or 'TERMINAL_PIN_DRIFT:'+type(exc).__name__+':'+str(exc)[:300]
        try:
            manifest=inventory(root_fd,limits,deadline,hashes=True,budget=budget,exclude=FINAL_EXCLUSIONS)
            if not failure: installed=verify_installed(contract,inspections,manifest)
        except BaseException as exc:
            failure=failure or 'TERMINAL_MANIFEST:'+type(exc).__name__+':'+str(exc)[:300]
            manifest=getattr(exc,'partial_inventory',manifest)
        manifest_document={'schema':'radio-runtime-package-bootstrap-artifact-manifest-v1',
            'bootstrap_identity':contract['bootstrap_identity'],'manifest':manifest,
            'hash_scope':'all operational objects before this manifest and final report',
            'self_and_final_report_exclusions':FINAL_EXCLUSIONS,'selected_read_charge_qualified_as_full_scope':False}
        manifest_raw=canonical(manifest_document)
        report={'schema':'radio-runtime-package-bootstrap-supervisor-result-v1','bootstrap_identity':contract['bootstrap_identity'],
            'status':'CLOSED_FAILED' if failure else 'MATERIALIZED_PACKAGES_ONLY','runtime_qualification':'PENDING_RUNTIME_QUALIFICATION',
            'failure':failure,'contract_sha256':contract_hash,'publication_proof_sha256':proof_hash,'activation_sha256':marker_hash,
            'prepared_commit':proof['prepared_commit'],'activation_commit':proof['activation_commit'],
            'started_monotonic_ns':began,'before_final_report_monotonic_ns':time.monotonic_ns(),
            'selected_elapsed_before_final_report_seconds':(time.monotonic_ns()-began)/1e9,
            'acquisition_receipts':acquisitions,'wheel_inspection_summaries':[{k:v for k,v in row.items() if k!='members'} for row in inspections],
            'installation_preflight':preflight,'installed_package_checks':installed,'pip_child':child_report,
            'selected_before_after_equal':before==after,'source_runtime_files':len(pins),
            'parent_explicit_read_charged_bytes':budget.bytes,'parent_precharged_categories':budget.categories,
            'parent_explicit_received_categories':budget.received,
            'parent_explicit_received_bytes':sum(budget.received.values()),
            'parent_charge_category_description':'regular includes physical ZIP archive read precharges; zip received category separately records archive bytes returned',
            'child_read_reserved_bytes':limits['child_read_reserve_bytes'],'child_read_observed_bytes':None,
            'joined_read_conservative_charged_bytes':budget.bytes+limits['child_read_reserve_bytes'],
            'joined_read_observed_bytes':None,'joined_full_scope_io_qualified':False,
            'terminal_read_reservation':budget.terminal_reservation,'artifact_manifest_sha256':digest(manifest_raw),
            'parent_lifetime_ru_maxrss_bytes_at_selected_call':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),
            'limits':limits,'spent_forever':True,'retry_allowed':False,'authority':AUTHORITY,
            'engineering_bootstrap_authorized':True,'engineering_reservation_spent':True,
            'native_package_imports':0,'telescope_reads':0,'scientific_cases_run':0,'eleven_scientific_fields':'PENDING',
            'publication_provenance_network_reauthenticated_here':False,
            'attribution_basis_dispatch':'held hash-verified exact B bytes compiled without invoking old run',
            'interpreter_implicit_loader_closure_qualified':False,
            'observation_limits':['pip regular/ZIP/implicit loader reads are not measured; full child reserve remains charged',
                'sampling cannot certify between-sample or provider peaks, aggregate descendant absence, or a full scope RSS cap',
                'recursive storage guards detect snapshots; transient child growth between checks is not a full peak certificate',
                'wait4 peak covers direct child only; parent ru_maxrss covers parent process lifetime',
                'raw stream cap retains received bytes including one probe; unread suffix is unobserved',
                'manifest explicitly excludes its own and final-report hashes; caller must retain/hash final objects']}
        after_raw=canonical(after); report_raw=canonical(report)
        if len(manifest_raw)+len(after_raw)+len(report_raw)>limits['terminal_reserve_bytes']:
            raise Refusal('spent terminal manifest/report bound exceeded; partial evidence retained')
        write_new(root_fd,'selected-runtime-after.json',after_raw,budget)
        write_new(root_fd,'artifact-manifest.json',manifest_raw,budget)
        write_new(root_fd,'supervisor-result.json',report_raw,budget)
        budget.check(); final_scope=inventory(root_fd,limits,deadline)
        if max(final_scope['logical_bytes'],final_scope['allocated_bytes'])>limits['artifact_bytes']: raise Refusal('final selected storage cap')
        completed=time.monotonic_ns()
        return {'report':report,'final_scope':final_scope,'completed_monotonic_ns':completed,
            'selected_whole_scope_elapsed_seconds':(completed-began)/1e9}
    finally:
        for fd in reversed(root_fds): os.close(fd)


def main():
    began=time.monotonic_ns(); parser=argparse.ArgumentParser()
    for name in ('contract','contract-sha256','publication-proof','publication-proof-sha256','activation','activation-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args(); raw_inputs=[]; count=0; received=0
    def charge(n):
        nonlocal count
        if type(n) is not int or n<0 or count+n>34*1024**2: raise Refusal('finite CLI pre-admission read request envelope')
        count+=n
    def observe(n,kind='regular'):
        nonlocal received
        received+=n
    for path,cap in ((args.contract,16*1024**2),(args.publication_proof,16*1024**2),(args.activation,65536)):
        raw,_=held_file(path,cap,charge,observe); raw_inputs.append(raw)
    result=run(raw_inputs[0],args.contract_sha256,raw_inputs[1],args.publication_proof_sha256,raw_inputs[2],args.activation_sha256,
        initial_read_bytes=count,initial_read_received_bytes=received,started_monotonic_ns=began)
    sys.stdout.buffer.write(canonical(result))


if __name__=='__main__':
    try: main()
    except (Refusal,OSError) as exc:
        sys.stderr.write('CLOSED_FAILED: '+str(exc)+'\n'); raise SystemExit(1)
