#!/usr/bin/env python3
"""Inventory restored engineering bytes; preserve failed original identity gate.

Fresh metadata does not replace any historical witness or original manifest.
No result from this informational capture authorizes production integration.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types

ROOT=Path('/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002')
HERE=ROOT/'results_radio_native_v2_joint_history_20261003a'
HELPER='results_radio_native_v2_joint_history_20261003a/observation-capture.py'
HELPER_PIN={'bytes':19888,'sha256':'c59f08c9574fe3657899f60d83c3a9c94198937af3196477b70edee0576498f9'}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def main():
    # Verify the executed helper before using its literal input pins and strict
    # descriptor-relative reader. This initial sole-link read is independent
    # of any original spend witness and is repeated by the strict reader.
    fd=os.open(ROOT/HELPER,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size!=HELPER_PIN['bytes']:
            raise ValueError('Exact independently pinned helper required')
        raw=os.read(fd,HELPER_PIN['bytes']+1)
        if len(raw)!=HELPER_PIN['bytes'] or hashlib.sha256(raw).hexdigest()!=HELPER_PIN['sha256']:
            raise ValueError('Helper raw pin differs before execution')
        key=lambda i:(i.st_dev,i.st_ino,i.st_mode,i.st_nlink,i.st_size,i.st_mtime_ns,i.st_ctime_ns)
        if key(before)!=key(os.fstat(fd)) or key(before)!=key((ROOT/HELPER).lstat()):
            raise ValueError('Helper changed before execution')
    finally:os.close(fd)
    helper=types.ModuleType('held_archival_inventory_helper');helper.__file__=str(ROOT/HELPER)
    exec(compile(raw,helper.__file__,'exec'),helper.__dict__)
    state={'active':True,'denied_events':[]}
    def audit(event,args):
        if not state['active']:return
        denied=(event in ('os.remove','os.rename','os.mkdir','os.rmdir','os.link','os.symlink','os.chmod','os.chown',
            'os.truncate','os.utime','subprocess.Popen','os.system','os.posix_spawn','os.exec') or event.startswith('socket.'))
        if event=='open':
            mode=args[1] if len(args)>1 else None;flags=args[2] if len(args)>2 else 0
            denied=(type(mode)is str and any(c in mode for c in 'wax+')) or (type(flags)is int and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
        if denied:
            state['denied_events'].append(event);raise RuntimeError('Restored inventory permits reads only')
    sys.addaudithook(audit)
    try:
        if helper.read_pinned(HELPER,HELPER_PIN)!=raw:raise ValueError('Held helper path differs')
        inputs={p:helper.read_pinned(p,pin) for p,pin in helper.INPUT_PINS.items()}
        storage=helper.module('held_archive_storage',helper.STORAGE_SOURCE,helper.read_pinned(helper.STORAGE_SOURCE,helper.STORAGE_PIN))
        b='results_radio_native_v2_compact_control_20261002b';c='results_radio_native_v2_compact_control_20261002c'
        bp=json.loads(inputs['results_radio_native_v2_ledger_launch_20261002a/failed-control-publication-manifest.json'])
        cp=json.loads(inputs['results_radio_native_v2_control_activation_20261002c/closed-failure-publication-manifest.json'])
        ct=json.loads(inputs['results_radio_native_v2_control_activation_20261002c/terminal-scope-inventory.json'])
        files={
            'b':{r['path'][len(b)+1:]:{'bytes':r['bytes'],'sha256':r['sha256']} for r in bp['actual_scope_files_retained'] if r['path'].startswith(b+'/')},
            'c':{r['path'][len(c)+1:]:{'bytes':r['bytes'],'sha256':r['sha256']} for r in cp['files'] if r['path'].startswith(c+'/')}}
        c_terminal={r['path'][len(c)+1:]:{'bytes':r['bytes'],'sha256':r['sha256']} for r in ct['files']}
        if files['c']!=c_terminal:raise ValueError('Independent public c file pins disagree')
        dirs={'b':{'.'},'c':{'.' if r['path']==c else r['path'][len(c)+1:] for r in ct['directories']}}
        for name in files['b']:
            parent=Path(name).parent
            while parent.as_posix()!='.':dirs['b'].add(parent.as_posix());parent=parent.parent
        if (len(files['b']),len(dirs['b']),sum(p['bytes'] for p in files['b'].values()))!=(107,20,70168047):
            raise ValueError('Exact retained public b inventory required')
        if (len(files['c']),len(dirs['c']),sum(p['bytes'] for p in files['c'].values()))!=(68,21,3853729):
            raise ValueError('Exact retained public c inventory required')
        for i in range(8):
            case=f'cases/case{i:02d}'
            if case not in dirs['c'] or any(p.startswith(case+'/') for p in dirs['c']|set(files['c'])):
                raise ValueError('All eight original c case directories must remain empty')
        outputs={};mismatches=[];ledger_original_failures={}
        for letter,scope,ledger,spender in (
            ('b',b,'.radio-native-v2-invocation-ledger',b+'/frozen-code/scripts/radio_native_v2_invocation_spending.py'),
            ('c',c,'.radio-native-v2-invocation-ledger-20261002c',c+'/frozen-code/scripts/radio_native_v2_prospective_spending.py')):
            source=helper.module('held_restored_'+letter+'_spender',spender,inputs[spender])
            receipt=json.loads(inputs[scope+'/activation-receipt.json']);witness=json.loads(inputs[scope+'/invocation-spending.json'])
            original_scope=str(ROOT/scope);original_ledger=str(ROOT/ledger)
            if receipt['control_scope']!=original_scope or witness['control_scope']!=original_scope or witness['ledger_root']!=original_ledger:
                raise ValueError('Independent original path binding changed')
            identity,receipt_digest,record_name=source._receipt(receipt,original_scope)
            if (witness['activation_identity_sha256']!=identity or witness['activation_receipt_sha256']!=receipt_digest
                    or witness['record_name']!=record_name):raise ValueError('Original pure receipt/witness bindings differ')
            record_expected=source.canonical(source._record(receipt,original_scope,identity,receipt_digest))+b'\n'
            record_pin={'bytes':len(record_expected),'sha256':hashlib.sha256(record_expected).hexdigest()}
            if record_pin!={'bytes':witness['record_identity']['bytes'],'sha256':witness['record_sha256']}:
                raise ValueError('Original witness digest differs from canonical original receipt record')
            rows=[]
            for relative in sorted(dirs[letter]|set(files[letter])):
                info=(ROOT/scope/relative).lstat();directory=relative in dirs[letter]
                row={'path':relative,'kind':'directory' if directory else 'file','metadata':storage._metadata(info)}
                if not directory:row['raw_pin']=files[letter][relative]
                rows.append(row)
            manifest={'schema':storage.MANIFEST_SCHEMA,'role':'historical_scope','scope':original_scope,'rows':rows}
            scope_observation=storage.observe_retained_scope(original_scope,manifest,expected_manifest_pin=helper.value_pin(manifest))
            ledger_rows=[]
            for relative in ('.',record_name):
                info=(ROOT/ledger/relative).lstat();directory=relative=='.'
                row={'path':relative,'kind':'directory' if directory else 'file','metadata':storage._metadata(info)}
                if not directory:row['raw_pin']=record_pin
                ledger_rows.append(row)
                expected=witness['ledger_identity'] if directory else witness['record_identity']
                different={field:{'original':value,'current':row['metadata'][field]} for field,value in expected.items() if row['metadata'][field]!=value}
                if different:mismatches.append({'history':letter,'role':'journal_root' if directory else 'spend_record','path':str(ROOT/ledger/relative),'changed_fields':different})
            ledger_manifest={'schema':storage.MANIFEST_SCHEMA,'role':'historical_ledger','scope':original_ledger,'rows':sorted(ledger_rows,key=lambda row:row['path'])}
            ledger_observation=storage.observe_retained_scope(original_ledger,ledger_manifest,expected_manifest_pin=helper.value_pin(ledger_manifest))
            kwargs={'execution_scope':original_scope,'ledger_root':original_ledger}
            if letter=='c':kwargs['repository_root']=str(ROOT)
            try:source.observe_spend_storage(witness,receipt,**kwargs)
            except ValueError as error:ledger_original_failures[letter]={'type':type(error).__name__,'error':str(error)}
            else:raise ValueError('Original restored journal identity unexpectedly authenticated')
            outputs[letter]={'scope-manifest':manifest,'scope-observation':scope_observation,
                'ledger-manifest':ledger_manifest,'ledger-observation':ledger_observation}
        before={f'historical_{letter}_{kind}':outputs[letter][kind+'-observation'] for letter in ('b','c') for kind in ('scope','ledger')}
        after={}
        for letter in ('b','c'):
            for kind in ('scope','ledger'):
                manifest=outputs[letter][kind+'-manifest']
                after[f'historical_{letter}_{kind}']=storage.observe_retained_scope(manifest['scope'],manifest,expected_manifest_pin=helper.value_pin(manifest))
        if before!=after:raise ValueError('Restored complete inventories changed during observation')
        ids=set();roots=[];logical=allocated=entries=0
        for value in before.values():
            _,observed_ids=storage._totals(value,value['scope'],raw_pins=True)
            if observed_ids&ids:raise ValueError('Cross-history inode alias rejected')
            ids.update(observed_ids);roots.append(value['scope']);logical+=value['logical_bytes'];allocated+=value['allocated_bytes'];entries+=value['entry_count']
        if any(a==b or a.startswith(b+'/') or b.startswith(a+'/') for i,a in enumerate(roots) for b in roots[i+1:]):
            raise ValueError('Restored four-component roots overlap')
        if max(logical,allocated)>storage.MAX_STORAGE_BYTES or entries>storage.MAX_ENTRIES:
            raise ValueError('Restored inventory exceeds unchanged whole storage bounds')
        for path,pin in helper.INPUT_PINS.items():
            if helper.read_pinned(path,pin)!=inputs[path]:raise ValueError('Immutable public inputs changed')
        if helper.read_pinned(HELPER,HELPER_PIN)!=raw:raise ValueError('Executed helper changed')
        state['active']=False
    except BaseException:
        state['active']=False
        raise
    pins={}
    for letter,values in outputs.items():
        for name,value in values.items():
            filename='observation-restored-'+letter+'-'+name+'.json'
            pins[str((HERE/filename).relative_to(ROOT))]=helper.write_new(filename,value)
    for name,value in (('protected-before',before),('protected-after',after)):
        filename='observation-restored-'+name+'.json';pins[str((HERE/filename).relative_to(ROOT))]=helper.write_new(filename,value)
    result={'schema':'radio-native-v2-restored-historical-byte-inventory-v1',
        'status':'ARCHIVAL_BYTES_VERIFIED_ORIGINAL_IDENTITIES_REFUSED',
        'public_input_commit':helper.PUBLIC_COMMIT,'helper_pin':HELPER_PIN,'storage_source_pin':helper.STORAGE_PIN,
        'input_raw_pins':helper.INPUT_PINS,'output_raw_pins':pins,
        'original_journal_identity_mismatches':mismatches,'original_spend_observer_failures':ledger_original_failures,
        'original_spend_identities_authenticated':False,'original_manifests_replaced':False,
        'complete_before_after_inventories_equal':True,'all_public_scope_file_bytes_verified':True,
        'both_canonical_original_journal_payloads_verified':True,'restored_journal_rows_used_only_as_archival_inventory':True,
        'retained_roots_disjoint':True,'cross_component_inode_aliases':0,'logical_bytes':logical,
        'allocated_bytes':allocated,'entry_count':entries,
        'components':[{'role':name,'scope':value['scope'],'entry_count':value['entry_count'],
            'file_count':sum(row['kind']=='file' for row in value['rows']),
            'directory_count':sum(row['kind']=='directory' for row in value['rows']),
            'raw_file_bytes':sum(row['bytes'] for row in value['rows'] if row['kind']=='file'),
            'logical_bytes':value['logical_bytes'],'allocated_bytes':value['allocated_bytes']} for name,value in before.items()],
        'read_only_audit_guard_active_during_observation':True,'read_only_audit':state,
        'actual_environment_keys':sorted(os.environ),'isolated_no_site_no_bytecode':bool(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode),
        'historical_production_gate_satisfied':False,'continuous_custody_proved':False,'execution_authorized':False,
        'new_control_created':False,'new_journal_or_claim_created':False,'new_marker_created':False,
        'protected_control_invocations':0,'scientific_cases_run':0,'telescope_reads':0,'rng_draws':0,
        'trust_boundary':'Exact immutable public engineering payload bytes and fresh current metadata only; original inode/ctime continuity fails. Cause not established by this observation.'}
    helper.write_new('observation-restored-result.json',result)
    print(canonical(result).decode())


if __name__=='__main__':main()
