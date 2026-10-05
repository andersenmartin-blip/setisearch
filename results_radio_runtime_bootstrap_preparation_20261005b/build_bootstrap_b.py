"""Read-only preparation and pure freeze builder for the separate bootstrap B.

This program never allocates the bootstrap root, writes an activation/spent marker,
imports a scientific package, creates a TLS context, or performs network IO.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import time

FINAL_REPOSITORY = Path('/workspace/scratch/66170938f826/setisearch')
FINAL_COHORT = FINAL_REPOSITORY / 'results_radio_runtime_bootstrap_preparation_20261005b'
FINAL_ROOT = Path('/workspace/scratch/66170938f826/radio-runtime-bootstrap-20261005b')
FINAL_GATE = FINAL_COHORT / 'bootstrap_gate.py'
FINAL_FREEZE = FINAL_REPOSITORY / 'config/radio_runtime_bootstrap_20261005b.freeze.json'
OLD_FREEZE = Path('/workspace/scratch/a5b2addacbd5/setisearch-20261005/config/radio_runtime_bootstrap_20261005a.freeze.json')
OLD_FREEZE_SHA256 = '7bcdc460afd6cda314c32ece81419ceb2097e8e3caa4c67c99a0bf7b3754d9f6'
ORIGINAL_PLAN_SHA256 = 'fe0a2463d75002b2b675d998f7ac4f201b1b67664e21baa22b2e241ed8c46c25'
TRUST_PIN = {'path':'/usr/local/share/ca-certificates/nebula-dns.crt','bytes':1310,
    'sha256':'ab6933a81e6f0d142e6d5f58ed465589d899a523c2752055761af11d4ee38f2b','mode':'0644'}
READ_SECONDS = 60
READ_BYTES = 256 * 1024**2
READ_FILES = 4096
SOURCE_NAMES = ('bootstrap_gate.py','capture_basis.py','wheel_io.py','proxy_contract.py',
    'proxy_opener.py','native_bindings.py','original-plan.json','transport-descriptor.json',
    'selected-trust.pem','build_bootstrap_b.py','PROTOCOL.md','runtime-revalidation.json',
    'current-inputs/current-input-metadata.json')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode() + b'\n'


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


class PreparationRefusal(Exception):
    pass


class ReadGuard:
    def __init__(self):
        self.started = time.monotonic_ns()
        self.charged = 0
        self.received = 0
        self.files = 0

    def check(self):
        if time.monotonic_ns()-self.started >= READ_SECONDS*10**9:
            raise PreparationRefusal('preparation read wall exhausted')

    def charge(self,n):
        self.check()
        if type(n) is not int or n < 0 or self.charged+n > READ_BYTES:
            raise PreparationRefusal('preparation read byte cap exhausted')
        self.charged += n

    def record(self,n,kind):
        self.check()
        if kind != 'regular' or type(n) is not int or n < 0:
            raise PreparationRefusal('preparation received-byte schema')
        self.received += n

    def read(self,gate,path,cap):
        self.check()
        self.files += 1
        if self.files > READ_FILES:
            raise PreparationRefusal('preparation selected file cap exhausted')
        return gate['held_file'](str(path),cap,self.charge,self.record)


def load_gate(path,expected):
    """Bootstrap only the explicit reviewed gate; no implicit project imports."""
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise PreparationRefusal('canonical gate path with no ancestor symlink required')
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1024**2:
            raise PreparationRefusal('finite sole-link gate file required')
        raw = bytearray()
        while len(raw) < before.st_size:
            chunk = os.read(fd,min(65536,before.st_size-len(raw)))
            if not chunk:
                raise PreparationRefusal('gate truncated')
            raw.extend(chunk)
        if os.read(fd,1):
            raise PreparationRefusal('gate grew')
        after = os.fstat(fd)
        named = os.stat(path,follow_symlinks=False)
        fields = ('st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns')
        if any(getattr(before,k)!=getattr(after,k) for k in fields) or (named.st_dev,named.st_ino,named.st_nlink)!=(after.st_dev,after.st_ino,1):
            raise PreparationRefusal('gate held/named drift')
    finally:
        os.close(fd)
    raw = bytes(raw)
    if sha256(raw) != expected:
        raise PreparationRefusal('explicit gate hash mismatch')
    gate = {'__name__':'_read_only_bootstrap_b_preparation_gate','__file__':str(path)}
    exec(compile(raw,str(path),'exec'),gate)
    return gate, raw


def pinned_inputs(gate,guard,old_freeze,supplements):
    old_raw,_ = guard.read(gate,old_freeze,1024**2)
    if sha256(old_raw) != OLD_FREEZE_SHA256:
        raise PreparationRefusal('historical closed A freeze hash changed')
    old = json.loads(old_raw)
    supplementary_raw,_ = guard.read(gate,supplements,16384)
    supplementary = json.loads(supplementary_raw)
    if supplementary != [TRUST_PIN] or len(old['runtime_pins']) != 1244:
        raise PreparationRefusal('only the exact one trust supplement is permitted')
    runtime = sorted(copy.deepcopy(old['runtime_pins']) + supplementary,key=lambda row:row['path'])
    if len(runtime)!=1245 or len({row['path'] for row in runtime})!=1245:
        raise PreparationRefusal('distinct exact 1245 selected runtime pins required')
    for row in runtime:
        gate['validate_pin'](row)
    if old['plan_sha256']!=ORIGINAL_PLAN_SHA256 or old['evidence_domain']!='package-bootstrap-only':
        raise PreparationRefusal('original package plan/domain changed')
    return old, runtime, {'path':str(old_freeze),'bytes':len(old_raw),'sha256':sha256(old_raw)}, {
        'path':str(supplements),'bytes':len(supplementary_raw),'sha256':sha256(supplementary_raw)}


def descriptor(gate):
    return {'schema':gate['TRANSPORT_SCHEMA'],
        'proxy_selection':{'environment_name':'PIP_PROXY','policy':'canonical-credential-free-loopback-http-v1'},
        'trust_binding':{key:TRUST_PIN[key] for key in ('path','bytes','sha256')},
        'tunnel_destination':{'host':'files.pythonhosted.org','port':443}}


def revalidate_runtime(gate,gate_raw,old_freeze,supplements):
    guard = ReadGuard()
    old,runtime,old_pin,supplement_pin = pinned_inputs(gate,guard,old_freeze,supplements)
    observed = []
    for expected in runtime:
        raw,item = guard.read(gate,expected['path'],expected['bytes'])
        actual = {'path':expected['path'],'bytes':len(raw),'sha256':sha256(raw),'mode':format(item.st_mode&0o7777,'04o')}
        if actual != expected:
            raise PreparationRefusal('selected current runtime pin mismatch: '+expected['path'])
        observed.append({'pin':actual,'held_object':{'device':item.st_dev,'inode':item.st_ino},
            'held_named_and_ancestor_checks':'performed by selected gate held_file'})
    guard.check()
    return {'schema':'radio-runtime-package-bootstrap-b-current-input-revalidation-v1',
        'status':'CURRENT_SELECTED_BYTES_REVALIDATED','evidence_domain':'bounded-read-only-preparation',
        'selected_gate_sha256':sha256(gate_raw),'historical_closed_a_freeze':old_pin,
        'only_runtime_supplement_source':supplement_pin,'runtime_pin_count':len(runtime),
        'runtime_raw_bytes':sum(row['bytes'] for row in runtime),'observations':observed,
        'limits':{'wall_seconds':READ_SECONDS,'read_bytes':READ_BYTES,'selected_file_count':READ_FILES},
        'actual':{'elapsed_ns':time.monotonic_ns()-guard.started,'reserved_read_bytes':guard.charged,
            'received_regular_bytes':guard.received,'selected_files_read':guard.files},
        'network_operations':0,'tls_contexts_created':0,'scientific_packages_imported':0,
        'telescope_reads':0,'activation_written':False,'spent_marker_written':False,
        'implicit_native_loader_or_resource_closure_certified':False,'scientific_fields':'all 11 remain pending'}


def build_freeze(gate,old_freeze,supplements,identity,root_device,root_inode):
    """Return a B contract; consume externally supplied root identity, create nothing."""
    guard = ReadGuard()
    old,runtime,_,_ = pinned_inputs(gate,guard,old_freeze,supplements)
    if not gate['hex_value'](identity) or identity in gate['RETIRED_BOOTSTRAP_IDENTITIES'] or identity=='0'*64:
        raise PreparationRefusal('explicit fresh B identity required')
    if type(root_device)is not int or root_device < 0 or type(root_inode)is not int or root_inode <= 0:
        raise PreparationRefusal('external fresh mode0700 root identity required')
    source=[]
    raw_sources={}
    for name in SOURCE_NAMES:
        path=FINAL_COHORT/name
        raw,item=guard.read(gate,path,8*1024**2)
        pin={'path':str(path),'bytes':len(raw),'sha256':sha256(raw),'mode':format(item.st_mode&0o7777,'04o')}
        if pin['mode']!='0644':
            raise PreparationRefusal('prepared source mode0644 required')
        source.append(pin); raw_sources[name]=raw
    report=json.loads(raw_sources['runtime-revalidation.json'])
    if (report['status']!='CURRENT_SELECTED_BYTES_REVALIDATED' or report['selected_gate_sha256']!=sha256(raw_sources['bootstrap_gate.py'])
            or report['runtime_pin_count']!=1245 or [row['pin'] for row in report['observations']]!=runtime
            or report['network_operations']!=0 or report['tls_contexts_created']!=0 or report['scientific_packages_imported']!=0
            or report['activation_written'] is not False or report['spent_marker_written'] is not False):
        raise PreparationRefusal('full current selected runtime revalidation report required')
    obj=copy.deepcopy(old)
    obj.update({'schema':gate['SCHEMA'],'bootstrap_identity':identity,
        'source_pins':sorted(source,key=lambda row:row['path']),'runtime_pins':runtime,
        'attribution_basis_path':str(FINAL_COHORT/'capture_basis.py'),'wheel_io_path':str(FINAL_COHORT/'wheel_io.py'),
        'plan_path':str(FINAL_COHORT/'original-plan.json'),'proxy_contract_path':str(FINAL_COHORT/'proxy_contract.py'),
        'proxy_opener_path':str(FINAL_COHORT/'proxy_opener.py'),'native_bindings_path':str(FINAL_COHORT/'native_bindings.py'),
        'transport_descriptor_path':str(FINAL_COHORT/'transport-descriptor.json'),
        'transport_descriptor_sha256':sha256(raw_sources['transport-descriptor.json']),
        'output_root':str(FINAL_ROOT),'output_root_identity':{'device':root_device,'inode':root_inode,'mode':'0700'},
        'spent_path':str(FINAL_ROOT/'spent.json'),
        'activation_path':str(FINAL_REPOSITORY/gate['ACTIVATION_REPOSITORY_PATH'])})
    if sha256(raw_sources['original-plan.json'])!=ORIGINAL_PLAN_SHA256 or obj['limits']!=gate['CEILINGS']:
        raise PreparationRefusal('unchanged original package plan and exact original ceilings required')
    if len(raw_sources['selected-trust.pem'])!=TRUST_PIN['bytes'] or sha256(raw_sources['selected-trust.pem'])!=TRUST_PIN['sha256']:
        raise PreparationRefusal('lossless authentic selected trust representation required')
    raw=canonical(obj)
    gate['validate_contract'](raw,sha256(raw))
    gate['validate_transport_descriptor'](raw_sources['transport-descriptor.json'],obj['transport_descriptor_sha256'],obj)
    return obj


def write_exclusive(path,raw):
    """Write only a specified preparation artifact; never make parent directories."""
    path=Path(path)
    if path.name in ('spent.json','radio_runtime_bootstrap_20261005b.activate.json') or path==FINAL_ROOT or FINAL_ROOT in path.parents:
        raise PreparationRefusal('builder cannot mutate actual bootstrap root or activation')
    if not path.is_absolute() or path.parent.resolve()!=path.parent:
        raise PreparationRefusal('canonical existing preparation destination required')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o644)
    try:
        os.fchmod(fd,0o644)
        view=memoryview(raw)
        while view:
            count=os.write(fd,view)
            if count<=0: raise PreparationRefusal('preparation write made no progress')
            view=view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('descriptor','trust','revalidate','freeze'))
    parser.add_argument('--gate',default=str(FINAL_GATE))
    parser.add_argument('--gate-sha256',required=True)
    parser.add_argument('--old-freeze',default=str(OLD_FREEZE))
    parser.add_argument('--supplements',default='/workspace/scratch/66170938f826/bootstrap-b-inputs/runtime-supplements.json')
    parser.add_argument('--output',required=True)
    parser.add_argument('--identity')
    parser.add_argument('--root-device',type=int)
    parser.add_argument('--root-inode',type=int)
    args=parser.parse_args()
    gate,gate_raw=load_gate(args.gate,args.gate_sha256)
    if args.operation=='descriptor':
        obj=descriptor(gate)
    elif args.operation=='trust':
        guard=ReadGuard()
        raw,item=guard.read(gate,TRUST_PIN['path'],TRUST_PIN['bytes'])
        actual={'path':TRUST_PIN['path'],'bytes':len(raw),'sha256':sha256(raw),'mode':format(item.st_mode&0o7777,'04o')}
        if actual!=TRUST_PIN:
            raise PreparationRefusal('selected current trust pin mismatch')
        write_exclusive(args.output,raw)
        print(json.dumps({'operation':args.operation,'path':args.output,'bytes':len(raw),'sha256':sha256(raw)},sort_keys=True))
        return
    elif args.operation=='revalidate':
        obj=revalidate_runtime(gate,gate_raw,args.old_freeze,args.supplements)
    else:
        obj=build_freeze(gate,args.old_freeze,args.supplements,args.identity,args.root_device,args.root_inode)
    raw=canonical(obj)
    write_exclusive(args.output,raw)
    print(json.dumps({'operation':args.operation,'path':args.output,'bytes':len(raw),'sha256':sha256(raw)},sort_keys=True))


if __name__=='__main__':
    main()
