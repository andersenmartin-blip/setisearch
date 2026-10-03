#!/usr/bin/env python3
"""Read-only complete public-pinned b/c histories and their existing journals.

Only retained engineering artifacts are read. No future control, journal,
marker, telescope input, process or network operation is created. The public
terminal c inventory independently identifies its eight empty case directories.
Observation ends before exclusive new evidence writes begin.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import traceback
import types

ROOT = Path('/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002')
HERE = ROOT / 'results_radio_native_v2_joint_history_20261003a'
PUBLIC_COMMIT = 'e72546711e78eb62a2ae9240f7420484a14b3612'
STORAGE_SOURCE = 'results_radio_native_v2_joint_history_20261003a/observation-held-storage-source.py'
STORAGE_PIN = {'bytes': 21869, 'sha256': '37d7225a9b24ee0de6002653d4676417b0b2befb5ce32cd071719fc01694d717'}
INPUT_PINS = {
 'results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json': {'bytes':81935,'sha256':'f49912dda98e557fce3991c141169bd207306e54317fffc07c107c8a99e14fb7'},
 'results_radio_native_v2_compact_control_20261002b/frozen-code/scripts/radio_native_v2_invocation_spending.py': {'bytes':20163,'sha256':'d6bba881e0001e61e332eb28b9b6377bcbd9e283641661a89e5360217319ce33'},
 'results_radio_native_v2_compact_control_20261002b/activation-receipt.json': {'bytes':1332,'sha256':'ba3533158ab34b0fe1bf3a71a879f508121e5126aadc197e2ccdc40327d78ee3'},
 'results_radio_native_v2_compact_control_20261002b/invocation-spending.json': {'bytes':1018,'sha256':'f7beaea6e4855f1439c3ae1ecceadf3a4335607fc6940b7b0d0ec1d0c8150f89'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-manifest.json': {'bytes':42900,'sha256':'6b3ce36a0e70169a4f97a57b60b6ef3abd4dbed06f90c83f8eb71baf71fea890'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-scope-observation.json': {'bytes':55112,'sha256':'02fdb297790aad0d049bb006b11bf1fa1471e09106fb5ac09cf6c178646034cd'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-manifest.json': {'bytes':778,'sha256':'f0281ae6b64015c7aaea5a634d58c69e123609f1d0bf26886f96f57d18267aee'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-observation.json': {'bytes':1200,'sha256':'c96bc568502bbf14e2fe3ad9946dddac258e20d047008d4c4f3ed494c53558e1'},
 'results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-ledger-spend-observation.json': {'bytes':1293,'sha256':'56a445db080250a7e39f17d18dd0f7b57a57d93f34664504410335abedfbbf05'},
 'results_radio_native_v2_control_activation_20261002c/closed-failure-publication-manifest.json': {'bytes':22816,'sha256':'c078c571ab0e57ed766b89dc0ebe2c9f8b2ef8720ccc05e174a9f1a82cf73827'},
 'results_radio_native_v2_control_activation_20261002c/terminal-scope-inventory.json': {'bytes':23482,'sha256':'98bcb0f744aa1fbdb69623e792b08c97fb0dbbc52723d946c8b76b33ae1143dc'},
 'results_radio_native_v2_compact_control_20261002c/frozen-code/scripts/radio_native_v2_prospective_spending.py': {'bytes':22296,'sha256':'189da9f870628573e85ae6943a63d79b1390fce0aee8a04e003318cc506e895f'},
 'results_radio_native_v2_compact_control_20261002c/activation-receipt.json': {'bytes':1332,'sha256':'0ebcfb6cc50183ef4635cf30c1e45a403dfc2f2334c98f939f7bfd5cbb498c85'},
 'results_radio_native_v2_compact_control_20261002c/invocation-spending.json': {'bytes':1028,'sha256':'647b91d67c73065399481ba1759e70775b65fc166551391699e617230b75af80'},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def value_pin(value):
    raw = canonical(value)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def read_pinned(relative, expected):
    path = ROOT / relative
    opened = []; chain = []
    identity = lambda i: (i.st_dev, i.st_ino, i.st_mode, i.st_nlink, i.st_uid,
        i.st_gid, i.st_size, i.st_mtime_ns, i.st_ctime_ns)
    ancestor = lambda i: (i.st_dev, i.st_ino, i.st_mode, i.st_uid, i.st_gid)
    try:
        directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened.append(directory); chain.append((directory, None, None, ancestor(os.fstat(directory))))
        for name in path.parts[1:-1]:
            parent = directory; named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISDIR(named.st_mode): raise ValueError('Ordinary pinned input ancestor required')
            directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            opened.append(directory)
            if ancestor(os.fstat(directory)) != ancestor(named): raise ValueError('Input ancestor replaced while opening')
            chain.append((directory, parent, name, ancestor(named)))
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        opened.append(fd); before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2*1024**2:
            raise ValueError('Bounded sole-link pinned input required')
        chunks = []; left = before.st_size + 1
        while left:
            chunk = os.read(fd, min(left, 65536))
            if not chunk: break
            chunks.append(chunk); left -= len(chunk)
        raw = b''.join(chunks)
        if (identity(before) != identity(os.fstat(fd))
                or identity(before) != identity(os.stat(path.name, dir_fd=directory, follow_symlinks=False))
                or len(raw) != before.st_size): raise ValueError('Pinned input changed while read')
        for fd, parent, name, before in chain:
            if ancestor(os.fstat(fd)) != before or (parent is not None and ancestor(os.stat(name, dir_fd=parent, follow_symlinks=False)) != before):
                raise ValueError('Pinned input ancestor binding changed')
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} != expected:
            raise ValueError('Pinned input raw bytes differ: '+relative)
        return raw
    finally:
        for fd in reversed(opened): os.close(fd)


def module(name, relative, raw):
    held = types.ModuleType(name); held.__file__ = str(ROOT / relative)
    exec(compile(raw, held.__file__, 'exec'), held.__dict__)
    return held


def write_new(name, value):
    raw = canonical(value) + b'\n'
    fd = os.open(HERE / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        offset = 0
        while offset < len(raw):
            amount = os.write(fd, raw[offset:])
            if amount <= 0: raise OSError('Short exclusive observation write')
            offset += amount
        os.fsync(fd)
    finally: os.close(fd)
    directory = os.open(HERE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def collect(storage, source, scope_relative, ledger_relative, expected_files, directories, receipt, witness, *, is_c):
    scope = str(ROOT/scope_relative); ledger = str(ROOT/ledger_relative)
    if receipt['control_scope'] != scope or witness['control_scope'] != scope or witness['ledger_root'] != ledger:
        raise ValueError('Independent original scope/journal witnesses required')
    def spend():
        args = dict(execution_scope=scope, ledger_root=ledger)
        if is_c: args['repository_root'] = str(ROOT)
        return source.observe_spend_storage(witness, receipt, **args)
    before = spend()
    rows = []
    for relative in sorted(directories | set(expected_files)):
        info = (ROOT/scope_relative/relative).lstat(); directory = relative in directories
        if (directory and not stat.S_ISDIR(info.st_mode)) or (not directory and not stat.S_ISREG(info.st_mode)):
            raise ValueError('Public historical path changed kind')
        row = {'path':relative,'kind':'directory' if directory else 'file','metadata':storage._metadata(info)}
        if not directory: row['raw_pin'] = expected_files[relative]
        rows.append(row)
    scope_manifest = {'schema':storage.MANIFEST_SCHEMA,'role':'historical_scope','scope':scope,'rows':rows}
    scope_observation = storage.observe_retained_scope(scope, scope_manifest, expected_manifest_pin=value_pin(scope_manifest))
    ledger_rows = []
    for observed in before['rows']:
        row = {'path':'.' if observed['kind']=='directory' else witness['record_name'],
            'kind':observed['kind'],'metadata':{field:observed[field] for field in storage.METADATA_FIELDS}}
        if row['kind']=='file': row['raw_pin']={'bytes':observed['bytes'],'sha256':witness['record_sha256']}
        ledger_rows.append(row)
    ledger_manifest={'schema':storage.MANIFEST_SCHEMA,'role':'historical_ledger','scope':ledger,
        'rows':sorted(ledger_rows,key=lambda row:row['path'])}
    ledger_observation=storage.observe_retained_scope(ledger,ledger_manifest,expected_manifest_pin=value_pin(ledger_manifest))
    after=spend()
    if before != after: raise ValueError('Historical journal changed between spend observations')
    if {row['path']:{field:row[field] for field in storage.METADATA_FIELDS} for row in ledger_observation['rows']} != {
            row['path']:{field:row[field] for field in storage.METADATA_FIELDS} for row in before['rows']}:
        raise ValueError('Independent retained and spend-ledger observers disagree')
    if storage.observe_retained_scope(scope,scope_manifest,expected_manifest_pin=value_pin(scope_manifest)) != scope_observation:
        raise ValueError('Complete retained scope changed between reads')
    return {'scope-manifest':scope_manifest,'scope-observation':scope_observation,
        'ledger-manifest':ledger_manifest,'ledger-observation':ledger_observation,
        'ledger-spend-observation':after}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()
    if not 1 <= args.attempt <= 1000000: raise ValueError('Bounded unique observation attempt required')
    prefix='observation-' if args.attempt==1 else f'observation-attempt-{args.attempt}-'
    state={'read_phase':True,'denied_mutation_process_network_events':[]}
    def audit(event,args):
        if not state['read_phase']:return
        denied=(event in ('os.remove','os.rename','os.mkdir','os.rmdir','os.link','os.symlink',
            'os.chmod','os.chown','os.truncate','os.utime','subprocess.Popen','os.system','os.posix_spawn','os.exec')
            or event.startswith('socket.'))
        if event=='open':
            mode=args[1] if len(args)>1 else None;flags=args[2] if len(args)>2 else 0
            denied=(type(mode)is str and any(c in mode for c in 'wax+')) or (type(flags)is int and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
        if denied:
            state['denied_mutation_process_network_events'].append(event)
            raise RuntimeError('Historical observation permits reads only: '+event)
    sys.addaudithook(audit)
    try:
        raw={p:read_pinned(p,pin) for p,pin in INPUT_PINS.items()}
        storage=module('historical_observation_held_storage',STORAGE_SOURCE,read_pinned(STORAGE_SOURCE,STORAGE_PIN))
        b='results_radio_native_v2_compact_control_20261002b';c='results_radio_native_v2_compact_control_20261002c'
        b_manifest=json.loads(raw['results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json'])
        b_files={r['path'][len(b)+1:]:{'bytes':r['bytes'],'sha256':r['sha256']} for r in b_manifest['actual_scope_files_retained'] if r['path'].startswith(b+'/')}
        b_dirs={'.'}
        for name in b_files:
            current=Path(name).parent
            while current.as_posix()!='.':b_dirs.add(current.as_posix());current=current.parent
        if len(b_files)!=107 or len(b_dirs)!=20 or sum(r['bytes'] for r in b_files.values())!=70168047:
            raise ValueError('Exact public b107files/20dirs/70168047 raw bytes required')
        c_public=json.loads(raw['results_radio_native_v2_control_activation_20261002c/closed-failure-publication-manifest.json'])
        terminal=json.loads(raw['results_radio_native_v2_control_activation_20261002c/terminal-scope-inventory.json'])
        c_files={r['path'][len(c)+1:]:{'bytes':r['bytes'],'sha256':r['sha256']} for r in c_public['files'] if r['path'].startswith(c+'/')}
        c_terminal_files={r['path'][len(c)+1:]:{'bytes':r['bytes'],'sha256':r['sha256']} for r in terminal['files']}
        c_dirs={'.' if r['path']==c else r['path'][len(c)+1:] for r in terminal['directories']}
        if (c_files!=c_terminal_files or len(c_files)!=68 or len(c_dirs)!=21
                or sum(r['bytes'] for r in c_files.values())!=3853729
                or terminal['all_eight_case_directories_empty'] is not True
                or c_public['permanently_spent'] is not True or c_public['status']!='CLOSED_FAILED'):
            raise ValueError('Exact public closed c68files/21dirs/3853729 raw bytes required')
        for row in terminal['directories']:
            if stat.S_IMODE((ROOT/row['path']).lstat().st_mode)!=int(row['mode'],8):
                raise ValueError('Public c directory mode changed')
        for i in range(8):
            case=f'cases/case{i:02d}'
            if case not in c_dirs or any(p.startswith(case+'/') for p in c_dirs|set(c_files)):
                raise ValueError('Every spent c case must remain empty and present')
        outputs={}
        for letter,scope,files,dirs,ledger,source_path in (
            ('b',b,b_files,b_dirs,'.radio-native-v2-invocation-ledger',b+'/frozen-code/scripts/radio_native_v2_invocation_spending.py'),
            ('c',c,c_files,c_dirs,'.radio-native-v2-invocation-ledger-20261002c',c+'/frozen-code/scripts/radio_native_v2_prospective_spending.py')):
            held=module('held_'+letter+'_historical_spender',source_path,raw[source_path])
            outputs[letter]=collect(storage,held,scope,ledger,files,dirs,json.loads(raw[scope+'/activation-receipt.json']),
                json.loads(raw[scope+'/invocation-spending.json']),is_c=letter=='c')
        old_prefix='results_radio_native_v2_historical_storage_20261002a/observation-attempt-2-historical-'
        for name,value in outputs['b'].items():
            if value!=json.loads(raw[old_prefix+name+'.json']):raise ValueError('Original b captured observation changed: '+name)
        inventories=[outputs[x][kind+'-observation'] for x in ('b','c') for kind in ('scope','ledger')]
        protected_before={f'historical_{letter}_{kind}':outputs[letter][kind+'-observation']
            for letter in ('b','c') for kind in ('scope','ledger')}
        protected_after={}
        for letter in ('b','c'):
            for kind in ('scope','ledger'):
                manifest=outputs[letter][kind+'-manifest']
                protected_after[f'historical_{letter}_{kind}']=storage.observe_retained_scope(
                    manifest['scope'],manifest,expected_manifest_pin=value_pin(manifest))
        if protected_before!=protected_after:
            raise ValueError('Complete four-component before/after inventories differ')
        roots=[value['scope'] for value in inventories];identities=set();entry_count=0
        for inventory in inventories:
            _,ids=storage._totals(inventory,inventory['scope'],raw_pins=True)
            if ids&identities:raise ValueError('Retained b/c inode alias rejected')
            identities.update(ids);entry_count+=inventory['entry_count']
        if any(a==b or a.startswith(b+'/') or b.startswith(a+'/') for i,a in enumerate(roots) for b in roots[i+1:]):
            raise ValueError('Retained b/c scope or journal roots overlap')
        logical=sum(v['logical_bytes'] for v in inventories);allocated=sum(v['allocated_bytes'] for v in inventories)
        if max(logical,allocated)>storage.MAX_STORAGE_BYTES or entry_count>storage.MAX_ENTRIES:
            raise ValueError('Retained b/c sum exceeds unchanged whole limits')
        for p,pin in INPUT_PINS.items():
            if read_pinned(p,pin)!=raw[p]:raise ValueError('Held public inputs changed between complete reads')
        state['read_phase']=False
    except BaseException as error:
        state['read_phase']=False
        write_new(prefix+'failure.json',{'schema':'radio-native-v2-joint-historical-read-only-failure-v1',
            'attempt':args.attempt,'status':'FAILED_OBSERVATION_RETAINED','error_type':type(error).__name__,
            'error':str(error),'traceback':traceback.format_exc(),'read_only_audit':state,
            'execution_authorized':False,'protected_control_invocations':0})
        raise
    output_pins={}
    for name,value in (('protected-before',protected_before),('protected-after',protected_after)):
        filename=prefix+name+'.json';output_pins[str((HERE/filename).relative_to(ROOT))]=write_new(filename,value)
    for letter,values in outputs.items():
        for name,value in values.items():
            filename=prefix+letter+'-'+name+'.json';output_pins[str((HERE/filename).relative_to(ROOT))]=write_new(filename,value)
    result={'schema':'radio-native-v2-joint-historical-read-only-capture-v1','attempt':args.attempt,
        'status':'B_AND_C_COMPLETE_RETAINED_STORAGE_VERIFIED_PREPARATION_ONLY',
        'public_input_commit':PUBLIC_COMMIT,'repository_root':str(ROOT),'storage_source_pin':STORAGE_PIN,
        'source_literals_checked_before_exec':True,'input_raw_pins':INPUT_PINS,'output_raw_pins':output_pins,
        'components':[{ 'role':'historical_'+letter+'_'+kind,'root':outputs[letter][kind+'-observation']['scope'],
            'file_count':sum(r['kind']=='file' for r in outputs[letter][kind+'-observation']['rows']),
            'directory_count':sum(r['kind']=='directory' for r in outputs[letter][kind+'-observation']['rows']),
            'raw_file_bytes':sum(r['bytes'] for r in outputs[letter][kind+'-observation']['rows'] if r['kind']=='file'),
            'logical_bytes':outputs[letter][kind+'-observation']['logical_bytes'],
            'allocated_bytes':outputs[letter][kind+'-observation']['allocated_bytes'],
            'value_pin':value_pin(outputs[letter][kind+'-observation'])}
            for letter in ('b','c') for kind in ('scope','ledger')],
        'logical_bytes':logical,'allocated_bytes':allocated,'entry_count':entry_count,
        'two_complete_scope_reads_match':True,'two_independent_ledger_observers_match':True,
        'complete_four_component_before_after_inventories_equal':True,
        'original_b_observations_equal':True,'eight_c_case_directories_present_and_empty':True,
        'retained_roots_disjoint':True,'cross_component_inode_aliases':0,
        'read_only_audit_guard_active_during_observation':True,'read_only_audit':state,
        'actual_argv':sys.orig_argv,'actual_environment_keys':sorted(os.environ),
        'actual_environment_sha256':hashlib.sha256(canonical(dict(os.environ))).hexdigest(),
        'isolated_no_site_no_bytecode':bool(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode),
        'execution_authorized':False,'protected_control_invocations':0,'new_project_marker_created':False,
        'new_project_journal_or_claim_created':False,'large_inputs_generated':False,'telescope_reads':0,
        'scientific_cases_run':0,'rng_draws':0,'future_lifetime_accounting_proved':False,
        'whole_control_qualified':False,'trust_boundary':'Immutable public engineering byte pins, fresh point-in-time directory metadata, local kernel/filesystem; access times excluded.'}
    write_new(prefix+'result.json',result)
    print(canonical(result).decode())


if __name__=='__main__':main()
