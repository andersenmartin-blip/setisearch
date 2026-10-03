#!/usr/bin/env python3
"""Operator-only staging for the one prospective v3 f spending transition.

This helper is outside the material runner source/input selection. It performs
no network operation, dispatch, source generation, RNG or telescope read.
Nothing in its printed JSON is independently authenticated by printing it.

CLI, with a separately retained SHA256 of the raw input manifest:

  PRIMARY_PYTHON -I -S -B build_spending_bootstrap.py --record \
    --manifest /absolute/operator-input.json --manifest-sha256 RAW_SHA256
  PRIMARY_PYTHON -I -S -B build_spending_bootstrap.py --bootstrap \
    --manifest /absolute/operator-input-with-C-readbacks.json \
    --manifest-sha256 RAW_SHA256

Both modes are read-only. --record prints the exact registry record for the
operator to publish in C. --bootstrap requires actual independently pinned C
commit/root/config tree, registry bytes, fixed-ref readback and an explicit
trusted outer create-only attestation; it prints the three fixed bootstrap
files. It never manufactures successful connector provenance.

For the fixed, bounded outer guard use --guarded-preclaim with the same manifest
and an additional --helper-sha256 RAW_PUBLISHED_HELPER_SHA256. Its parent runs
under the ordinary security domain and exact frozen environment. It verifies
the helper/source pins and executes only this helper's --preclaim entry under
one inherited reviewed escape guard, observing wait4/ECHILD and bounded pipes.
It returns the actual child result and observation; it cannot authorize a retry.

The separate --preclaim mode is a protected mutation and must be explicitly
invoked only after public A admission. Invoke it under the frozen ten-value
environment, PRIMARY_PYTHON -I -S -B, and the same single inherited supervisor
escape guard as the future launcher. It verifies the actual marker checkout,
creates the original private 0700 ledger exclusively, and calls consume_once
with real checked activation/runtime admission. It writes only the private
spend record and two exclusive/fsynced operator output files named in the
externally pinned manifest. Any failure leaves existing private state spent;
there is no retry, adoption, reconstruction or cleanup route.

Manifest common fields: schema, repository_root, scope, source_pins, documents.
schema is INPUT_SCHEMA below. source_pins is exactly SOURCE_PATHS with raw
{bytes,sha256} pins. documents is exactly plan/complete_freeze/preread/
activation_readback; each descriptor has {path,bytes,sha256}. Those four paths
are repository-relative. --preclaim adds output_paths with absolute distinct
activation_receipt/local_witness destinations whose parent already exists.
--record adds activation_receipt/local_witness pinned file descriptors.
--bootstrap adds the same two descriptors plus public_origin, whose descriptors
are claim_commit/claim_root_tree/claim_config_tree/public_record/
claim_ref_readback/create_only_attestation. Those external readback descriptors
and the receipt/witness descriptors may be absolute operator paths.

Create-only attestation exact fields: schema, repository, branch, ref, commit,
operation, creation_succeeded, create_only_verified, immutable_record_readback,
ref_readback_verified. Values must describe the actually observed connector
operation. This supplied attestation remains an independent outer trust input;
the helper checks its bindings and declares origin checks structural only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import types

REPO = Path(__file__).resolve().parents[1]
SELF = str(Path(__file__).resolve())
INPUT_SCHEMA = 'radio-native-v3-spending-bootstrap-input-v1'
OUTPUT_SCHEMA = 'radio-native-v3-spending-bootstrap-staging-v1'
ORIGIN_SCHEMA = 'radio-native-v3-create-only-spent-origin-attestation-v1'
MAX_INPUT = 32*1024**2
MAX_SOURCE = 2*1024**2
ACTIVATION = 'scripts/radio_native_v3_control_activation.py'
SPENDER = 'scripts/radio_native_v3_prospective_spending.py'
CLAIMS = 'scripts/radio_native_v3_public_claim.py'
CUSTODY = 'scripts/radio_native_v3_custody_observation.py'
LAUNCHER = 'scripts/radio_native_v3_compact_control_launch.py'
FINALIZER = 'scripts/radio_native_v3_resource_finalization.py'
OBSERVER = 'scripts/radio_native_v3_engineering_observer.py'
SUPERVISOR = 'scripts/radio_native_v3_process_tree_supervisor.py'
ENVIRONMENT = 'scripts/radio_native_v3_activation_environment.py'
SOURCE_PATHS = frozenset((ACTIVATION,SPENDER,CLAIMS,CUSTODY,LAUNCHER,FINALIZER,OBSERVER,SUPERVISOR,ENVIRONMENT))
DOCUMENT_NAMES = frozenset(('plan','complete_freeze','preread','activation_readback'))
ORIGIN_NAMES = frozenset(('claim_commit','claim_root_tree','claim_config_tree',
    'public_record','claim_ref_readback','create_only_attestation'))
COMMON_FIELDS = frozenset(('schema','repository_root','scope','source_pins','documents'))
NONEXECUTION = {'dispatch_performed':False,'network_operations_performed':0,
    'source_generation_performed':False,'scientific_execution_authorized':False,
    'native_execution_authorized':False,'telescope_reads':0,'rng_draws':0,
    'automatic_retry':False,'origin_checked_structurally_only':True}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def raw_pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def blob_sha(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def _sha(value,width=64):
    if type(value) is not str or not re.fullmatch('[a-f0-9]{'+str(width)+'}',value):
        raise ValueError('Exact independently retained lowercase digest required')
    return value


def _relative(value):
    if (type(value) is not str or not value or value.startswith('/') or '\\' in value
            or re.search(r'[\x00-\x1f\x7f]',value) or len(value.encode())>4096
            or any(x in ('','.','..') for x in value.split('/'))):
        raise ValueError('Canonical repository-relative operator input required')
    return value


def _absolute(value):
    value=os.fspath(value)
    if (type(value) is not str or not value.startswith('/') or value=='/'
            or '\\' in value or re.search(r'[\x00-\x1f\x7f]',value)
            or len(value.encode())>4096 or any(x in ('','.','..') for x in value[1:].split('/'))):
        raise ValueError('Canonical absolute operator path required')
    return value


def _directory(path):
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in _absolute(path)[1:].split('/'):
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=child
        return fd
    except BaseException:os.close(fd);raise


def _identity(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_uid,
        info.st_gid,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def read_raw(path,expected=None,*,maximum=MAX_INPUT):
    path=_absolute(path);parent,name=path.rsplit('/',1);directory=_directory(parent);fd=None
    try:
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>maximum:
            raise ValueError('Bounded sole-link stable operator input required')
        chunks=[];count=0
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            count+=len(chunk)
            if count>maximum:raise ValueError('Operator input byte cap exceeded')
            chunks.append(chunk)
        raw=b''.join(chunks);after=os.fstat(fd)
        named=os.stat(name,dir_fd=directory,follow_symlinks=False)
        reopened=_directory(parent)
        try:
            if _identity(os.fstat(directory))[:2]!=_identity(os.fstat(reopened))[:2]:
                raise ValueError('Operator input parent replaced')
        finally:os.close(reopened)
        if _identity(before)!=_identity(after) or _identity(after)!=_identity(named) or count!=after.st_size:
            raise ValueError('Operator input changed during descriptor read')
        if expected is not None and raw_pin(raw)!=expected:
            raise ValueError('Operator input differs from external immutable pin')
        return raw
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)


def parse(raw,*,canonical_newline=False):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('Duplicate operator JSON key refused')
            value[key]=item
        return value
    value=json.loads(raw,object_pairs_hook=unique,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite operator JSON refused')))
    if type(value) is not dict:raise ValueError('Exact operator JSON object required')
    if canonical_newline and raw!=canonical(value)+b'\n':
        raise ValueError('Exact canonical metadata plus newline required')
    return value


def _pin(value,maximum=MAX_INPUT):
    if (type(value) is not dict or set(value)!={'bytes','sha256'}
            or type(value['bytes']) is not int or not 0<value['bytes']<=maximum):
        raise ValueError('Exact bounded nonempty operator input pin required')
    _sha(value['sha256']);return value


def descriptor(value,*,relative=False,canonical_newline=False):
    if type(value) is not dict or set(value)!={'path','bytes','sha256'}:
        raise ValueError('Exact pinned operator file descriptor required')
    pin=_pin({k:value[k] for k in ('bytes','sha256')})
    path=str(REPO/_relative(value['path'])) if relative else (
        _absolute(value['path']) if str(value['path']).startswith('/') else str(REPO/_relative(value['path'])))
    raw=read_raw(path,pin)
    return parse(raw,canonical_newline=canonical_newline),raw


def source(relative,pin):
    _pin(pin,MAX_SOURCE);raw=read_raw(REPO/relative,pin,maximum=MAX_SOURCE)
    module=types.ModuleType('operator_held_'+Path(relative).stem);module.__file__=str(REPO/relative)
    exec(compile(raw,module.__file__,'exec'),module.__dict__)
    return module


def load_common(manifest,mode):
    extras={'preclaim':{'output_paths'},'record':{'activation_receipt','local_witness'},
        'bootstrap':{'activation_receipt','local_witness','public_origin'}}[mode]
    if type(manifest) is not dict or set(manifest)!=COMMON_FIELDS|extras:
        raise ValueError('Exact stage-specific externally pinned operator manifest required')
    if manifest['schema']!=INPUT_SCHEMA or manifest['repository_root']!=str(REPO):
        raise ValueError('Fixed current operator repository root required')
    if type(manifest['source_pins']) is not dict or set(manifest['source_pins'])!=SOURCE_PATHS:
        raise ValueError('Exactly nine held operator source implementations required')
    if type(manifest['documents']) is not dict or set(manifest['documents'])!=DOCUMENT_NAMES:
        raise ValueError('Exactly four original activation documents required')
    documents={};raw_documents={}
    for name,entry in manifest['documents'].items():
        documents[name],raw_documents[name]=descriptor(entry,relative=True,canonical_newline=True)
    plan=documents['plan'];freeze=documents['complete_freeze'];preread=documents['preread']
    for path,pin in manifest['source_pins'].items():
        if canonical(plan.get('code_files',{}).get(path))!=canonical(pin):
            raise ValueError('Operator source differs from independently frozen plan: '+path)
    modules={p:source(p,pin) for p,pin in manifest['source_pins'].items()}
    observer=modules[OBSERVER];activation=modules[ACTIVATION];custody=modules[CUSTODY]
    scope=str(REPO/observer.SCOPE_NAME)
    if manifest['scope']!=scope:raise ValueError('Exact fresh current eight-input f scope required')
    custody.validate_root(plan,str(REPO),scope)
    readback=documents['activation_readback']
    expected_readback_keys={'schema','repository','branch','verified','activation_commit',
        'activation_tree','activation_parent','marker_path','marker_blob','marker_sha256'}
    if (set(readback)!=expected_readback_keys or readback['schema']!=activation.READBACK_SCHEMA
            or readback['repository']!=activation.REPOSITORY or readback['branch']!=activation.BRANCH
            or readback['verified'] is not True or readback['marker_path']!=activation.MARKER):
        raise ValueError('Exact independently retained actual A public readback required')
    for key in ('activation_commit','activation_tree','activation_parent','marker_blob'):_sha(readback[key],40)
    _sha(readback['marker_sha256'])
    marker_raw=read_raw(REPO/activation.MARKER,maximum=65536)
    if raw_pin(marker_raw)['sha256']!=readback['marker_sha256'] or blob_sha(marker_raw)!=readback['marker_blob']:
        raise ValueError('Actual A marker bytes differ from public readback')
    marker=parse(marker_raw,canonical_newline=True)
    for name,key in (('plan','plan_sha256'),('complete_freeze','complete_freeze_sha256'),('preread','execution_preread_sha256')):
        if marker.get(key)!=digest(documents[name]):raise ValueError('A marker frozen document binding differs')
    if marker.get('preread_commit')!=readback['activation_parent'] or marker.get('control_scope')!=scope:
        raise ValueError('Actual A marker predecessor or scope differs')
    return {'manifest':manifest,'modules':modules,'documents':documents,'raw_documents':raw_documents,
        'scope':scope,'marker':marker,'readback':readback}


def load_original_witness(context):
    manifest=context['manifest'];modules=context['modules'];documents=context['documents']
    receipt,_=descriptor(manifest['activation_receipt'],canonical_newline=True)
    witness,_=descriptor(manifest['local_witness'],canonical_newline=True)
    activation=modules[ACTIVATION];spender=modules[SPENDER]
    if activation.validate_worker_receipt(receipt,plan=documents['plan'],complete_freeze=documents['complete_freeze'],
            execution_preread=documents['preread'],repository_root=str(REPO),execution_scope=context['scope']) is not True:
        raise ValueError('Actual original activation receipt admission failed')
    for key in ('activation_commit','activation_tree','activation_parent','marker_blob','marker_sha256'):
        if receipt.get(key)!=context['readback'][key]:raise ValueError('Original receipt differs from actual A readback')
    if spender.verify_spend_witness(witness,receipt,execution_scope=context['scope'],
            ledger_root=spender.ledger_root_for_repository(str(REPO)),repository_root=str(REPO)) is not True:
        raise ValueError('Actual original private preclaim witness no longer exists unchanged')
    context['activation_receipt']=receipt;context['local_witness']=witness
    return witness


def build_record(context):
    claims=context['modules'][CLAIMS];documents=context['documents'];receipt=context['activation_receipt']
    witness=context['local_witness']
    record={'schema':claims.RECORD_SCHEMA,'namespace':claims.NAMESPACE,
        'repository':claims.REPOSITORY,'branch':claims.BRANCH,'state':'SPENT_BEFORE_DISPATCH',
        'marker_path':claims.MARKER,'repository_root':str(REPO),'control_scope':context['scope'],
        'historical_spent_activations':[list(x) for x in claims.SPENT_ACTIVATIONS],
        'rejected_prospective_identifiers':[list(x) for x in claims.REJECTED_PROSPECTIVE_IDENTIFIERS],
        'permanent_spent':True,'spent_before_dispatch':True,'one_control_invocation':True,
        'local_invocation_spending_sha256':digest(witness),
        'local_ledger_identity':json.loads(canonical(witness['ledger_identity'])),
        'local_record_identity':json.loads(canonical(witness['record_identity'])),
        **{name:receipt[name] for name in ('activation_commit','activation_tree','activation_parent','marker_blob','marker_sha256')},
        **{name:False for name in claims.DISABLED}}
    for name,key in (('plan','plan_sha256'),('complete_freeze','complete_freeze_sha256'),('preread','execution_preread_sha256')):
        record[key]=digest(documents[name])
    if set(record)!=claims.RECORD_FIELDS:raise ValueError('Operator built an unexpected public record schema')
    raw=canonical(record)+b'\n'
    if len(raw)>claims.MAX_CLAIM_BYTES:raise ValueError('Bounded public claim record exceeded')
    return record,raw


def _tree_sha(tree):
    if type(tree) is not dict or tree.get('truncated') is True or type(tree.get('tree')) is not list:
        raise ValueError('Complete actual nonrecursive Git tree readback required')
    rows=[];names=[]
    for item in tree['tree']:
        name=item.get('path');mode=item.get('mode');sha=item.get('sha')
        if (type(name) is not str or not name or '/' in name or '\0' in name
                or mode not in ('040000','100644','100755','120000','160000')):
            raise ValueError('Canonical complete Git tree entry required')
        _sha(sha,40);names.append(name)
        rows.append((('40000' if mode=='040000' else mode)+' '+name).encode()+b'\0'+bytes.fromhex(sha))
    if len(set(names))!=len(names):raise ValueError('Duplicate Git tree entry refused')
    raw=b''.join(rows);sha=hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if sha!=tree.get('sha'):raise ValueError('Actual Git tree raw object digest differs')
    return sha


def verify_origin(context,record,record_raw):
    origins=context['manifest']['public_origin'];claims=context['modules'][CLAIMS]
    if type(origins) is not dict or set(origins)!=ORIGIN_NAMES:
        raise ValueError('Six independently pinned actual C/ref/origin readbacks required')
    data={};raw={}
    for name,entry in origins.items():data[name],raw[name]=descriptor(entry)
    commit=data['claim_commit'];csha=_sha(commit.get('sha'),40)
    parents=commit.get('parents')
    if (type(parents) is not list or len(parents)!=1
            or parents[0].get('sha')!=record['activation_commit'] or csha==record['activation_commit']):
        raise ValueError('Actual C must be a distinct direct single-parent child of A')
    tree_sha=_tree_sha(data['claim_root_tree']);config_sha=_tree_sha(data['claim_config_tree'])
    if commit.get('tree',{}).get('sha')!=tree_sha:
        raise ValueError('Actual C tree differs from independently read root tree')
    config=[x for x in data['claim_root_tree']['tree'] if x['path']=='config']
    if len(config)!=1 or config[0]['mode']!='040000' or config[0]['sha']!=config_sha:
        raise ValueError('Actual C config tree is not rooted in the actual commit')
    registry=[x for x in data['claim_config_tree']['tree'] if x['path']==Path(claims.REGISTRY_PATH).name]
    if len(registry)!=1 or registry[0]['mode']!='100644' or registry[0]['sha']!=blob_sha(record_raw):
        raise ValueError('Actual C registry blob differs from the original witnessed public record')
    if raw['public_record']!=record_raw or canonical(data['public_record'])!=canonical(record):
        raise ValueError('Independently fetched actual registry bytes differ from locally witnessed record')
    ref=data['claim_ref_readback']
    if ref.get('ref')!=claims.CLAIM_REF or ref.get('object',{}).get('type')!='commit' or ref['object'].get('sha')!=csha:
        raise ValueError('Fixed create-only ref actual readback differs from C')
    expected_attestation={'schema':ORIGIN_SCHEMA,'repository':claims.REPOSITORY,'branch':claims.BRANCH,
        'ref':claims.CLAIM_REF,'commit':csha,'operation':'mcp__codex_apps__github_create_branch',
        'creation_succeeded':True,'create_only_verified':True,'immutable_record_readback':True,'ref_readback_verified':True}
    if canonical(data['create_only_attestation'])!=canonical(expected_attestation):
        raise ValueError('Explicit independent actual create-only connector origin attestation required')
    return {'repository':claims.REPOSITORY,'branch':claims.BRANCH,'path':claims.REGISTRY_PATH,
        'commit':csha,'tree':tree_sha,'parent':record['activation_commit'],'blob':blob_sha(record_raw),
        'sha256':hashlib.sha256(record_raw).hexdigest(),'public_readback_verified':data['create_only_attestation']['immutable_record_readback'],
        'create_only_ref':claims.CLAIM_REF,'ref_create_only_verified':data['create_only_attestation']['create_only_verified'],
        'ref_readback_commit':ref['object']['sha']}


def file_output(path,value):
    raw=canonical(value)+b'\n'
    return {'path':path,'content':raw.decode(),**raw_pin(raw),'canonical_object_sha256':digest(value),'git_blob_sha':blob_sha(raw)}


def bootstrap(context,record,record_raw):
    modules=context['modules'];claims=modules[CLAIMS];spender=modules[SPENDER]
    launcher=modules[LAUNCHER];observer=modules[OBSERVER];custody=modules[CUSTODY]
    registry_pin=verify_origin(context,record,record_raw)
    claim={'schema':claims.SCHEMA,'record':record,'registry_pin':registry_pin,
        'public_readback_verified':registry_pin['public_readback_verified']}
    claim_sha=digest(claim);documents=context['documents'];witness=context['local_witness']
    claim_receipt=claims.verify_public_claim(claim,expected_sha256=claim_sha,plan=documents['plan'],
        complete_freeze=documents['complete_freeze'],execution_preread=documents['preread'],
        execution_scope=context['scope'],repository_root=str(REPO),invocation_spending=witness)
    envelope={'schema':spender.SPENDING_BUNDLE_SCHEMA,'local_witness':witness,
        'public_claim':claim,'public_claim_sha256':claim_sha,'dispatch_witness':None}
    spender.validate_spending_bundle(envelope,require_dispatch=False)
    envelope_output=file_output(custody.CURRENT_PUBLIC_CLAIM_PATH,envelope)
    inputs={name:{k:entry[k] for k in ('path','bytes','sha256')}
        for name,entry in context['manifest']['documents'].items()}
    inputs['invocation_spending']={'path':custody.CURRENT_PUBLIC_CLAIM_PATH,
        'bytes':envelope_output['bytes'],'sha256':envelope_output['sha256'],'object_sha256':digest(envelope)}
    config={'schema':launcher.CONFIG_SCHEMA,'namespace':launcher.NAMESPACE,'mode':'PROSPECTIVE_NOT_EXECUTED',
        'repository_root':str(REPO),'scope':context['scope'],'inputs':inputs}
    launcher.validate_launch_config(config)
    config_output=file_output(launcher.CONFIG_PATH,config)
    freeze=documents['complete_freeze'];python=freeze['executables']['python']
    plan_python=documents['plan']['runtime_executables']['python']
    if python['resolved']!=plan_python['path'] or python['sha256']!=plan_python['sha256']:
        raise ValueError('Frozen Python identity differs from independently pinned plan executable')
    capsule={'schema':observer.CAPSULE_SCHEMA,'namespace':observer.NAMESPACE,'repository_root':str(REPO),
        'scope':context['scope'],'python':{'path':python['resolved'],'bytes':plan_python['bytes'],'sha256':python['sha256']},
        'environment':modules[ENVIRONMENT].expected_environment(documents['plan'],freeze),
        'source_pins':{path:context['manifest']['source_pins'][path] for path in observer.SOURCE_PATHS},
        'launch_config':{'path':launcher.CONFIG_PATH,'bytes':config_output['bytes'],'sha256':config_output['sha256']},
        'limits':observer.LIMITS,'authority':observer.AUTHORITY}
    observer.validate_capsule(capsule)
    capsule_output=file_output(observer.CAPSULE_PATH,capsule)
    outputs=[envelope_output,config_output,capsule_output]
    if {x['path'] for x in outputs}!=set(custody.CURRENT_PREDISPATCH_PATHS):
        raise ValueError('Exactly three fixed charged predispatch bootstrap paths required')
    return {'schema':OUTPUT_SCHEMA,'stage':'bootstrap','registry_commit':registry_pin['commit'],
        'public_claim_receipt':claim_receipt,'files':outputs,
        'observer_argv':[python['resolved'],'-I','-S','-B',str(REPO/OBSERVER),
            '--run','--capsule-sha256',capsule_output['sha256']],
        'protected_files_created':0,**NONEXECUTION}


def _write_exclusive(path,value):
    raw=canonical(value)+b'\n'
    if len(raw)>65536:raise ValueError('Bounded original operator witness output required')
    path=_absolute(path);parent,name=path.rsplit('/',1);directory=_directory(parent);fd=None
    try:
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400,dir_fd=directory)
        position=0
        while position<len(raw):
            count=os.write(fd,raw[position:])
            if count<=0:raise OSError('Incomplete durable operator witness output')
            position+=count
        os.fsync(fd);os.close(fd);fd=None;os.fsync(directory)
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)
    read_raw(path,raw_pin(raw),maximum=65536)
    return {'path':path,**raw_pin(raw)}


def preclaim_output_paths(context,spender):
    """Reject protected/historical outputs lexically before any directory read."""
    outputs=context['manifest']['output_paths']
    if type(outputs) is not dict or set(outputs)!={'activation_receipt','local_witness'}:
        raise ValueError('Two exclusive original operator receipt output paths required')
    paths=[_absolute(x) for x in outputs.values()]
    if len(set(paths))!=2:raise ValueError('Distinct original receipt/witness output paths required')
    ledger=spender.ledger_root_for_repository(str(REPO))
    custody=context['modules'][CUSTODY]
    protected=(ledger,context['scope'],custody.ORIGINAL_REPOSITORY_ROOT,
        *(str(REPO/path) for path in custody.HISTORICAL_RELATIVE_ROOTS))
    for path in paths:
        if any(path==root or path.startswith(root+'/') for root in protected):
            raise ValueError('Operator outputs cannot enter a current or historical ledger/scope/root')
    return paths,ledger


def preclaim(context,args):
    modules=context['modules'];documents=context['documents'];activation=modules[ACTIVATION];spender=modules[SPENDER]
    freeze=documents['complete_freeze'];python=freeze['executables']['python']['resolved']
    expected_argv=[python,'-I','-S','-B',SELF,'--preclaim','--manifest',args.manifest,'--manifest-sha256',args.manifest_sha256]
    if list(sys.orig_argv)!=expected_argv or str(Path(sys.executable).resolve())!=python:
        raise ValueError('Exact held primary -I -S -B preclaim argv required')
    environment=modules[ENVIRONMENT]
    if os.environ!=environment.expected_environment(documents['plan'],freeze):
        raise ValueError('Actual preclaim environment differs from the frozen ten values')
    environment.validate_platform(documents['plan']['activation_platform_contract'])
    paths,ledger=preclaim_output_paths(context,spender)
    outputs=context['manifest']['output_paths']
    for path in paths:
        parent,name=path.rsplit('/',1);fd=_directory(parent);os.close(fd)
        if os.path.lexists(path):raise ValueError('Original output path already exists; no retry/adoption')
    if os.path.lexists(ledger) or os.path.lexists(context['scope']):
        raise ValueError('Original f private ledger and future scope must both be absent')
    descriptors=context['manifest']['documents']
    receipt=activation.verify_marker_checkout(REPO,plan_path=descriptors['plan']['path'],
        freeze_path=descriptors['complete_freeze']['path'],preread_path=descriptors['preread']['path'],
        activation_readback_path=REPO/descriptors['activation_readback']['path'],
        activation_commit=context['readback']['activation_commit'],execution_scope=context['scope'])
    held_receipt=canonical(receipt)
    def trusted_validator(value):
        if canonical(value)!=held_receipt:raise ValueError('Actual held activation receipt changed before consume_once')
        return activation.validate_worker_receipt(value,plan=documents['plan'],complete_freeze=freeze,
            execution_preread=documents['preread'],repository_root=str(REPO),execution_scope=context['scope'])
    trusted_validator(receipt)
    parent_fd=_directory(str(REPO))
    try:
        os.mkdir(spender.LEDGER_DIRECTORY,0o700,dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:os.close(parent_fd)
    witness=spender.consume_once(receipt,execution_scope=context['scope'],ledger_root=ledger,
        repository_root=str(REPO),receipt_validator=trusted_validator)
    if spender.verify_spend_witness(witness,receipt,execution_scope=context['scope'],ledger_root=ledger,repository_root=str(REPO)) is not True:
        raise ValueError('New original spend witness failed its immediate read-only verification')
    receipt_output=_write_exclusive(outputs['activation_receipt'],receipt)
    witness_output=_write_exclusive(outputs['local_witness'],witness)
    return {'schema':OUTPUT_SCHEMA,'stage':'preclaim','activation_receipt':receipt,
        'local_witness':witness,'outputs':{'activation_receipt':receipt_output,'local_witness':witness_output},
        'protected_original_local_preclaim_created':True,'public_claim_created':False,**NONEXECUTION}


def guarded_preclaim(context,args):
    """One fixed held helper child; no arbitrary command or protected parent write."""
    modules=context['modules'];documents=context['documents'];freeze=documents['complete_freeze']
    python=freeze['executables']['python']['resolved']
    expected=[python,'-I','-S','-B',SELF,'--guarded-preclaim','--manifest',args.manifest,
        '--manifest-sha256',args.manifest_sha256,'--helper-sha256',args.helper_sha256]
    if list(sys.orig_argv)!=expected or str(Path(sys.executable).resolve())!=python:
        raise ValueError('Exact fixed guarded preclaim parent argv required')
    _sha(args.helper_sha256)
    helper_raw=read_raw(SELF,maximum=MAX_SOURCE);helper_pin=raw_pin(helper_raw)
    if helper_pin['sha256']!=args.helper_sha256:
        raise ValueError('Operator helper differs from independently published caller pin')
    environment=modules[ENVIRONMENT].expected_environment(documents['plan'],freeze)
    if os.environ!=environment:
        raise ValueError('Guarded preclaim parent must use the exact frozen ten values')
    argv=[python,'-I','-S','-B',SELF,'--preclaim','--manifest',args.manifest,
        '--manifest-sha256',args.manifest_sha256]
    observed,stdout,stderr=modules[OBSERVER].observe_child(argv,environment,
        deadline_monotonic_ns=time.monotonic_ns()+modules[OBSERVER].RUN_SECONDS*10**9,
        supervisor=modules[SUPERVISOR])
    if (observed['reason'] is not None or observed['exit_code']!=0 or stderr
            or observed['subreaper_scope_reaped_to_echild'] is not True):
        raise ValueError('Fixed guarded preclaim child failed; existing private state must remain spent')
    result=parse(stdout,canonical_newline=True)
    if (result.get('schema')!=OUTPUT_SCHEMA or result.get('stage')!='preclaim'
            or result.get('protected_original_local_preclaim_created') is not True
            or result.get('public_claim_created') is not False):
        raise ValueError('Exact original preclaim result required from the held child')
    read_raw(SELF,helper_pin,maximum=MAX_SOURCE)
    return {'schema':OUTPUT_SCHEMA,'stage':'guarded-preclaim','preclaim_result':result,
        'guarded_child_observation':observed,'helper_pin':helper_pin,
        'guarded_parent_protected_files_created':0,**NONEXECUTION}


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    modes=parser.add_mutually_exclusive_group(required=True)
    for mode in ('preclaim','guarded-preclaim','record','bootstrap'):modes.add_argument('--'+mode,action='store_true')
    parser.add_argument('--manifest',required=True);parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--helper-sha256')
    args=parser.parse_args();_sha(args.manifest_sha256)
    raw=read_raw(args.manifest,maximum=262144)
    if hashlib.sha256(raw).hexdigest()!=args.manifest_sha256:raise ValueError('Independent raw manifest SHA256 differs')
    manifest=parse(raw,canonical_newline=True)
    mode=next(mode for mode in ('preclaim','guarded-preclaim','record','bootstrap') if getattr(args,mode.replace('-','_')))
    if (mode=='guarded-preclaim')!=(args.helper_sha256 is not None):
        raise ValueError('Independent helper SHA256 belongs only to the fixed guarded preclaim parent')
    context=load_common(manifest,'preclaim' if mode=='guarded-preclaim' else mode)
    if mode=='preclaim':result=preclaim(context,args)
    elif mode=='guarded-preclaim':result=guarded_preclaim(context,args)
    else:
        load_original_witness(context);record,record_raw=build_record(context)
        if mode=='record':result={'schema':OUTPUT_SCHEMA,'stage':'record',
            'files':[file_output(context['modules'][CLAIMS].REGISTRY_PATH,record)],
            'protected_files_created':0,**NONEXECUTION}
        else:result=bootstrap(context,record,record_raw)
    print(canonical(result).decode())


if __name__=='__main__':main()
