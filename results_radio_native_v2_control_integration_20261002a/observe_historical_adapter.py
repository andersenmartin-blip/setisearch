#!/usr/bin/env python3
"""Read-only live b history through the freshly frozen integrated c adapter.

No prospective scope, c ledger, activation marker or source is created. The
prospective scope below is an absent path used solely for contract validation.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

REPO=Path(__file__).resolve().parents[1]
RESULTS=Path(__file__).parent
FREEZE=REPO/'config/radio_native_v2_control_integration_20261002a.runtime.json'
PLAN=REPO/'config/radio_native_v2_compact_eight_input_control_20261002r.plan.json'
HELPER=RESULTS/'prepare_snapshot.py'


def stable_read(path, maximum):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=maximum:
            raise ValueError('Bounded stable sole-link adapter bootstrap required')
        chunks=[];remaining=before.st_size+1
        while remaining:
            block=os.read(fd,min(65536,remaining))
            if not block: break
            chunks.append(block);remaining-=len(block)
        raw=b''.join(chunks)
        identity=lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if len(raw)!=before.st_size or identity(before)!=identity(os.fstat(fd)) or identity(before)!=identity(path.lstat()):
            raise ValueError('Adapter bootstrap changed during descriptor read')
        return raw
    finally:os.close(fd)


def main():
    frozen=json.loads(stable_read(FREEZE,16*1024**2))
    raw=stable_read(HELPER,2*1024**2)
    if hashlib.sha256(raw).hexdigest()!=frozen['input_sha256s'][str(HELPER.relative_to(REPO))]:
        raise ValueError('Integrated preparation helper differs before source execution')
    helper=types.ModuleType('integrated_historical_observation_bootstrap');helper.__file__=str(HELPER)
    exec(compile(raw,str(HELPER),'exec'),helper.__dict__)
    launcher_pin={'bytes':(REPO/helper.LAUNCHER).stat().st_size,'sha256':frozen['code_sha256s'][helper.LAUNCHER]}
    launcher,environment,_,_,proof=helper.bootstrap_exact_environment(launcher_pin)
    plan,_=environment.read_json(PLAN);freeze,_=environment.read_json(FREEZE)
    environment.validate(plan,freeze,dict(os.environ))
    relative='scripts/radio_native_v2_historical_observation.py'
    wanted=plan['code_files'][relative]
    if freeze['code_sha256s'].get(relative)!=wanted['sha256']:
        raise ValueError('Fresh freeze omits integrated historical observer source')
    _,source=launcher.read_pinned(REPO/relative,expected=wanted,maximum=2*1024**2,retain=True)
    adapter=types.ModuleType('pinned_integrated_historical_adapter');adapter.__file__=str(REPO/relative)
    exec(compile(source,adapter.__file__,'exec'),adapter.__dict__)
    scope=str(REPO/'results_radio_native_v2_control_integration_20261002a-not-invoked')
    ledger=REPO/'.radio-native-v2-invocation-ledger-20261002c'
    marker=REPO/'config/radio_native_v2_control_activation_20261002c.activate.json'
    if any(path.exists() for path in (Path(scope),ledger,marker)):
        raise ValueError('Read-only preparation requires prospective scope/journal/marker absent')
    audit_counts={'mutation_or_process_or_network_events':0}
    def read_only_audit(event,args):
        denied=event in ('os.mkdir','os.remove','os.rmdir','os.rename','os.chmod','os.chown','os.link','os.symlink','os.truncate','subprocess.Popen','os.system','os.posix_spawn','os.exec','socket.connect','socket.bind')
        if event=='open':
            mode=args[1] if len(args)>1 else None
            flags=args[2] if len(args)>2 else 0
            denied=(isinstance(mode,str) and any(letter in mode for letter in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
        if denied:
            audit_counts['mutation_or_process_or_network_events']+=1
            raise AssertionError('Live historical adapter observation must remain read-only')
    sys.addaudithook(read_only_audit)
    storage,historical_scope,historical_ledger=adapter.observe_historical_storage(str(REPO),
        plan=plan,freeze=freeze,repository_root=str(REPO),execution_scope=scope)
    result={'schema':'radio-native-v2-integrated-live-historical-adapter-observation-v1',
        'status':'LIVE_HISTORICAL_ADAPTER_VERIFIED_C_ABSENT',
        'source_pin':wanted,'bootstrap':proof,'actual_environment_keys':sorted(os.environ),
        'fresh_plan_pin':launcher.read_pinned(PLAN)[0],'fresh_freeze_pin':launcher.read_pinned(FREEZE)[0],
        'historical_scope_observation_pin':adapter.value_pin(historical_scope),
        'historical_ledger_observation_pin':adapter.value_pin(historical_ledger),
        'historical_scope_entries':historical_scope['entry_count'],
        'historical_ledger_entries':historical_ledger['entry_count'],
        'total_logical_bytes':historical_scope['logical_bytes']+historical_ledger['logical_bytes'],
        'total_allocated_bytes':historical_scope['allocated_bytes']+historical_ledger['allocated_bytes'],
        'read_only_audit':audit_counts,'execution_authorized':False,
        'live_prospective_three_component_join_performed':False,
        'c_scope_created':False,'c_journal_created_or_consumed':False,'activation_marker_created':False,
        'lifetime_accounting_proved':False,'protected_control_invocations':0,'telescope_reads':0}
    print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))


if __name__=='__main__':main()
