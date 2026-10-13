"""Create or verify/selectively extract a NEW2010 saved-data replay archive.

All declared payload hashes are streamed. Extraction writes only the selected
replay subset plus admission metadata, preserving relative paths. No NumPy or
HDF5 is imported. No source files or original outputs are modified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time
import zipfile

BASE='seti_burst_full'
CPU_CAP,WALL_CAP,MEMORY_CAP=600,900,2*1024**3
WORKSPACE_CAP=8*1024**3
ARCHIVE_CAP=1250*1024**2


def require(ok,message):
    if not ok:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
    return h.hexdigest()


def unique_pairs(items):
    result={}
    for k,v in items:
        require(k not in result,'Duplicate JSON key');result[k]=v
    return result


def decode(raw):
    return json.loads(raw,object_pairs_hook=unique_pairs,
                      parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def confined(root,name):
    p=Path(name)
    require(not p.is_absolute() and '..' not in p.parts,'Safe relative path required')
    path=root/p
    require(path.resolve().is_relative_to(root) and not path.is_symlink(),'Unconfined path')
    return path


def pin(root,path):
    return {'path':Path(path).relative_to(root).as_posix(),'bytes':Path(path).stat().st_size,'sha256':digest(path)}


def save(path,value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())


def allocated(root):
    seen=set();total=0
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in files:
            info=(Path(parent)/name).stat(follow_symlinks=False);key=(info.st_dev,info.st_ino)
            if key not in seen:seen.add(key);total+=info.st_blocks*512
    return total


def gates(root,args,action):
    go_path=confined(root,args.root_go)
    require(args.root_go_sha256 and digest(go_path)==args.root_go_sha256,'Exact package/extraction GO SHA required')
    go=decode(go_path.read_bytes())
    require(go['status']==action and go['package_sha256']==digest(Path(__file__).resolve())
            and (go['CPU_cap_s'],go['wall_cap_s'],go['memory_cap_bytes'])==(CPU_CAP,WALL_CAP,MEMORY_CAP),
            'Package/extraction source/resource GO differs')
    if action=='GO_PACKAGE_NEW2010_PORTABLE_REPLAY':
        scope_path=confined(root,BASE+'/REPLAY_SCOPE.json');freeze_path=confined(root,BASE+'/REPLAY_FREEZE.json')
        require(args.scope_sha256 and digest(scope_path)==args.scope_sha256==go['scope_sha256'],'Exact saved-replay scope required')
        require(args.freeze_sha256 and digest(freeze_path)==args.freeze_sha256==go['freeze_sha256'],'Exact public replay freeze required')
        freeze=decode(freeze_path.read_bytes())
        require(freeze['status']=='PASS_PUBLIC_FREEZE_SAVED_REPLAY_SCOPE_READBACK'
                and freeze['scope_sha256']==args.scope_sha256 and re.fullmatch('[0-9a-f]{40}',freeze['public_commit']),
                'Public replay readback freeze differs')
        return go,decode(scope_path.read_bytes())
    require(args.archive_sha256 and digest(args.archive)==args.archive_sha256==go['archive_sha256']
            and args.scope_sha256==go['scope_sha256'] and args.mode==go['mode'],'Exact archive/scope/mode extraction GO required')
    return go,None


def create(root,args):
    go,scope=gates(root,args,'GO_PACKAGE_NEW2010_PORTABLE_REPLAY')
    require(scope['package_sha256']==digest(Path(__file__).resolve()),'Scope package source differs')
    files={p['path']:p for p in scope['file_pins']}
    require(len(files)==len(scope['file_pins']),'Duplicate archive closure names')
    for name in ('REPLAY_SCOPE.json','REPLAY_FREEZE.json','REPLAY_ROOT_GO.json'):
        p=pin(root,confined(root,BASE+'/'+name));files[p['path']]=p
    extra=pin(root,confined(root,args.root_go));files[extra['path']]=extra
    extension=None
    if args.extras_manifest:
        extra_path=confined(root,args.extras_manifest)
        require(go.get('extras_manifest_sha256')==digest(extra_path), 'Exact extended delivery manifest GO binding required')
        extension=decode(extra_path.read_bytes())
        require(extension['schema']=='SETI_FULL_BURST_EXTENDED_DELIVERY_EXTRA_PINS_V1'
                and extension['status']=='READY_FULL_DELIVERY_EXTENSIONS'
                and extension['pilot_maps']==288, 'Extended full delivery declaration differs')
        seen=set()
        for declared in extension['files']:
            ep={k:declared[k] for k in ('path','bytes','sha256')};name=ep['path'];part=Path(name)
            require(name not in seen and part.parts[0] in ('seti_burst_on','seti_burst_full')
                    and part.suffix in ('.npz','.json','.py','.txt','.md','.csv','.png','.pdf','.jsonl')
                    and not any(x in ('__pycache__',) for x in part.parts),
                    'Extension outside reviewed full/pilot artifact allowlist')
            seen.add(name)
            require(name not in files or files[name]==ep, 'Extension conflicts with frozen replay closure')
            files[name]=ep
        extension_pin=pin(root,extra_path);files[extension_pin['path']]=extension_pin
        for epoch in (1,2,3):
            parent=f'seti_burst_on/results/on20170428_epoch{epoch}_HIP98505'
            mp=parent+'/MAPS.json'
            require(mp in files and pin(root,confined(root,mp))==files[mp], 'Pilot map manifest pin required')
            pilot=decode(confined(root,mp).read_bytes())
            require(len(pilot['records'])==96, 'Exact pilot96 maps perON required')
            for record in pilot['records']:
                for pp in ({k:record[k] for k in ('path','bytes','sha256')},record['normalization']):
                    require(files.get(pp['path'])==pp, 'Full delivery must include every288 pilot map/normalization pin')
        for name in ('seti_burst_on/qa.py','seti_burst_on/qa_results/QA_RECEIPT.json',
                     'seti_burst_on/context.py','seti_burst_on/context_qa.py',
                     'seti_burst_on/context_results/CONTEXT_PROFILES.json'):
            require(name in files, 'Pilot actual QA/context closure metadata missing: '+name)
    require(all(Path(n).suffix in ('.npz','.json','.py','.txt','.md','.csv','.png','.pdf','.jsonl') and not n.endswith('.h5') for n in files),
            'Archive closure must exclude all telescope HDF5 inputs')
    path=confined(root,args.output)
    require(not path.exists() and path.parent.exists(),'Fresh archive path required')
    manifest={'schema':('SETI_FULL_BURST_SAVED_REPLAY_PACKAGE_V1' if extension else 'SETI_NEW2010_SAVED_REPLAY_PACKAGE_V1'),'package_scope_sha256':args.scope_sha256,
              'replay_source_sha256':scope['replay_sha256'],'files':[files[n] for n in sorted(files)],
              'required_members':scope['required_members'],'required_bytes':scope['required_bytes'],
              'new_maps':2010,'pilot_maps_included':bool(extension),'pilot_maps':288 if extension else 0,
              'source_HDF5_files_included':False,
              'extended_delivery_manifest':extension,
              'portable_replay_scope':'NEW2010 scalar10050 and optional18DC frame remax only; full delivery extra artifacts are included and hashed but not replayed by saved_replay.py',
              'delivery_label':('Full new2010+pilot288 delivery with root-selected aggregate/context artifacts' if extension else 'New2010 saved-output closure only; full scientific delivery adds pilot288, aggregate and context.'),
              'stream_verification':'Every archive payload SHA256 and ZIP CRC; selective extraction avoids redundant map storage.'}
    require(allocated(root)+min(sum(p['bytes'] for p in files.values()),ARCHIVE_CAP)<WORKSPACE_CAP,
            'Conservative prospective archive workspace cap exceeded')
    with path.open('xb') as stream:
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as archive:
            for ordinal,name in enumerate(sorted(files),1):
                p=files[name];source=confined(root,name)
                require(pin(root,source)==p,'Archive source pin differs')
                with source.open('rb') as inp,archive.open(name,'w',force_zip64=True) as out:
                    h=hashlib.sha256();count=0
                    for part in iter(lambda:inp.read(1024**2),b''):
                        h.update(part);count+=len(part);out.write(part)
                    require(count==p['bytes'] and h.hexdigest()==p['sha256'],'Archive source changed while streaming')
                require(path.stat().st_size<ARCHIVE_CAP,'Archive output cap exceeded')
                if ordinal%128==0:require(allocated(root)<WORKSPACE_CAP,'Archive workspace cap exceeded')
                if ordinal%1000==0:print(json.dumps({'packaged_files':ordinal,'total':len(files)}),flush=True)
            archive.writestr('PACKAGE_MANIFEST.json',(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode())
        stream.flush();os.fsync(stream.fileno())
    verify_archive(path,manifest,None,set())
    save(path.with_suffix(path.suffix+'.receipt.json'),{'status':'PASS_NEW2010_ARCHIVE_STREAMED_ALL_PAYLOAD_SHA_AND_CRC',
         'archive':pin(root,path),'scope_sha256':args.scope_sha256,'source_HDF5_files_included':False,
         'file_count':len(files),'payload_bytes':sum(p['bytes'] for p in files.values()),
         'required_bytes':scope['required_bytes'],'pilot_maps_included':bool(extension),
         'extended_delivery':bool(extension)})
    print(json.dumps({'archive':pin(root,path),'required_bytes':scope['required_bytes']}))


def verify_archive(path,manifest,destination,selected):
    expected={p['path']:p for p in manifest['files']}
    require(len(expected)==len(manifest['files']),'Duplicate package names')
    with zipfile.ZipFile(path,'r') as archive:
        infos=archive.infolist();names=[i.filename for i in infos]
        require(len(names)==len(set(names)) and set(names)==set(expected)|{'PACKAGE_MANIFEST.json'},'Exact complete archive closure required')
        for name in sorted(expected):
            p=expected[name];info=archive.getinfo(name)
            require(info.file_size==p['bytes'] and not info.is_dir() and not name.endswith('.h5'), 'Archive declared size/type differs')
            h=hashlib.sha256();count=0;out=None
            if name in selected:
                require(destination is not None,'Destination required for extraction')
                target=confined(destination,name);target.parent.mkdir(parents=True,exist_ok=True);out=target.open('xb')
            try:
                with archive.open(info,'r') as inp:
                    for part in iter(lambda:inp.read(1024**2),b''):
                        h.update(part);count+=len(part)
                        if out is not None:out.write(part)
                require(count==p['bytes'] and h.hexdigest()==p['sha256'],'Archive payload SHA differs: '+name)
                if out is not None:out.flush();os.fsync(out.fileno())
            finally:
                if out is not None:out.close()
        # Opening and reading each entry to EOF also validates its ZIP CRC.


def extract(root,args):
    go,_=gates(root,args,'GO_VERIFY_EXTRACT_SAVED_REPLAY_ARCHIVE')
    with zipfile.ZipFile(args.archive,'r') as archive:
        manifest=decode(archive.read('PACKAGE_MANIFEST.json'))
        require(manifest['schema'] in ('SETI_NEW2010_SAVED_REPLAY_PACKAGE_V1','SETI_FULL_BURST_SAVED_REPLAY_PACKAGE_V1')
                and manifest['package_scope_sha256']==args.scope_sha256
                and manifest['source_HDF5_files_included'] is False,'Saved replay manifest differs')
        scope_bytes=archive.read(BASE+'/REPLAY_SCOPE.json')
        require(hashlib.sha256(scope_bytes).hexdigest()==args.scope_sha256,'Bundled replay scope SHA differs')
        scope=decode(scope_bytes)
        require(manifest['required_members']==scope['required_members'] and manifest['required_bytes']==scope['required_bytes'],
                'Manifest extraction subset differs from exact replay scope')
    destination=Path(args.output_root).resolve()
    require(destination.is_relative_to(root) and not destination.exists(),'Fresh extraction root under workspace required')
    selected=set(scope['required_members'][args.mode])
    selected.update(p['path'] for p in manifest['files'] if p['path'].startswith(BASE+'/REPLAY_') and p['path'].endswith(('.json','.md','.txt')))
    selected.update((BASE+'/saved_replay.py',BASE+'/package_replay.py'))
    expected={p['path']:p for p in manifest['files']}
    require(selected.issubset(expected),'Required extraction member missing from archive')
    needed=sum(expected[n]['bytes'] for n in selected)
    require(allocated(root)+needed<WORKSPACE_CAP,'Fresh extraction workspace bound exceeded')
    destination.mkdir(exist_ok=False)
    verify_archive(args.archive,manifest,destination,selected)
    save(destination/'EXTRACTION_RECEIPT.json',{'status':'PASS_ALL_ARCHIVE_PAYLOAD_SHA_CRC_STRICT_REPLAY_SUBSET_EXTRACTED',
         'archive_sha256':args.archive_sha256,'scope_sha256':args.scope_sha256,'mode':args.mode,
         'complete_archive_members_verified':len(expected),'extracted_members':len(selected),'extracted_bytes':needed,
         'source_HDF5_files_extracted':False,'all2010_map_payloads_extracted':False,
         'declared_partial_root':True,'selected_members':sorted(selected)})
    print(json.dumps({'status':'PASS_SELECTIVE_FRESH_REPLAY_EXTRACTION','output_root':str(destination),'extracted_bytes':needed}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--check-only',action='store_true')
    p.add_argument('--create',action='store_true');p.add_argument('--verify-extract',action='store_true')
    p.add_argument('--mode',choices=('scalar','full_dc'),default='scalar')
    p.add_argument('--archive',type=Path);p.add_argument('--archive-sha256')
    p.add_argument('--extras-manifest',help='Root-bound explicit full/pilot delivery file-pin allowlist JSON')
    p.add_argument('--output',default=BASE+'/NEW2010_PORTABLE_REPLAY.zip');p.add_argument('--output-root')
    p.add_argument('--root-go',default=BASE+'/REPLAY_PACKAGE_GO.json')
    for n in ('scope-sha256','freeze-sha256','root-go-sha256'):p.add_argument('--'+n)
    a=p.parse_args();root=a.root.resolve()
    if a.check_only:
        print(json.dumps({'status':'PASS_SOURCE_ONLY_PORTABLE_PACKAGE_INTERFACE','numerical_modules_imported':False,
                          'all_archive_payloads_stream_verified':True,'strict_mode_subset_extraction':True,
                          'source_HDF5_files_included':False,'extended_full_delivery_manifest_supported':True,'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,
                          'memory_cap_bytes':MEMORY_CAP,'archive_cap_bytes':ARCHIVE_CAP,'workspace_cap_bytes':WORKSPACE_CAP}));return
    require(a.create!=a.verify_extract,'Exactly create or verify-extract required')
    def alarm(signum,frame):raise TimeoutError('Portable package cap')
    signal.signal(signal.SIGALRM,alarm);signal.signal(signal.SIGXCPU,alarm)
    resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP+1));resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP));signal.alarm(WALL_CAP)
    try:
        if a.create:create(root,a)
        else:
            require(a.archive and a.output_root,'Archive and fresh output root required');extract(root,a)
    finally:signal.alarm(0)


if __name__=='__main__':main()
