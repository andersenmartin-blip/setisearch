#!/usr/bin/env python3
"""Read-only static inventory. Never imports or executes inventoried targets."""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

BASE = Path(__file__).resolve().parent
SOURCE = BASE.parents[1] / 'previous/E/absolute_paths/workspace/scratch/da6462abff17/radio-runtime-metadata-capture-20261005e/native-metadata.json'
C_RETAINED = BASE.parents[1] / 'previous/C/absolute_paths'
meta_bytes = SOURCE.read_bytes()
meta = json.loads(meta_bytes)
runtime = Path(meta['process']['base_prefix'])
dirs = [runtime/'lib', Path('/usr/lib/x86_64-linux-gnu'), Path('/lib/x86_64-linux-gnu'), Path('/usr/lib64'), Path('/lib64'), Path('/usr/lib'), Path('/lib')]
roots = {}
prior = {}
for package, dist in meta['distributions_before'].items():
    for f in dist['declared_native_elf']:
        roots[f['path']] = 'E declared package ELF: ' + package
        prior[f['path']] = f
for f in meta['maps_after_plugin_and_inventory']['mapped_file_identities']:
    prior[f['path']] = f
    if f['path'].startswith('/usr/') or f['path'].startswith('/lib/'):
        roots[f['path']] = 'E observed mapped base ELF (scope seed, not new observation)'
roots[meta['process']['executable']] = 'exact C materialized venv interpreter'

nodes = {}
edges = []
errors = []
queue = collections.deque(roots)
aliases = collections.defaultdict(set)
for f in prior.values():
    aliases[Path(f['path']).name].add(f['path'])
    for soname in f.get('elf',{}).get('soname',[]): aliases[soname].add(f['path'])

def facts(path):
    s = path.stat()
    return {'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'links':s.st_nlink}

def ordinary_elf(path):
    try:
        return stat.S_ISREG(path.stat().st_mode) and path.open('rb').read(4) == b'\x7fELF'
    except OSError:
        return False

def parse_static(path):
    # readelf parses the file as data; neither the ELF target nor loader is run.
    result = subprocess.run(['/usr/bin/readelf','--wide','--dynamic','--program-headers',str(path)],capture_output=True,check=False)
    if result.returncode:
        raise ValueError('readelf failed: '+result.stderr.decode('utf-8','replace')[:500])
    raw = result.stdout
    evidence = BASE/'readelf'/ (hashlib.sha256(str(path).encode()).hexdigest()+'.txt')
    evidence.parent.mkdir(parents=True,exist_ok=True)
    evidence.write_bytes(raw)
    txt = raw.decode('utf-8','replace')
    dynamic = {}
    for tag,value in re.findall(r'\((NEEDED|RPATH|RUNPATH|SONAME)\).*?\[(.*?)\]',txt):
        dynamic.setdefault(tag,[]).append(value)
    interp = re.findall(r'\[Requesting program interpreter: (.*?)\]',txt)
    return {'needed':dynamic.get('NEEDED',[]),'rpath':dynamic.get('RPATH',[]),'runpath':dynamic.get('RUNPATH',[]),'soname':dynamic.get('SONAME',[]),'interpreter':interp,'readelf_evidence':str(evidence.relative_to(BASE.parent)),'readelf_evidence_sha256':hashlib.sha256(raw).hexdigest()}

def expanded(values,path):
    output=[]
    for value in values:
        for part in value.split(':'):
            part=part.replace('${ORIGIN}',str(path.parent)).replace('$ORIGIN',str(path.parent))
            if '$' in part or not part:
                errors.append({'path':str(path),'problem':'unsupported_or_empty_search_token','token':part})
            elif os.path.isabs(part): output.append(Path(part))
            else: errors.append({'path':str(path),'problem':'relative_search_directory_not_resolved','token':part})
    return output

while queue:
    spelling = queue.popleft()
    path = Path(spelling)
    if not ordinary_elf(path):
        errors.append({'path':spelling,'problem':'missing_or_nonordinary_ELF'})
        continue
    real = str(path.resolve())
    if real in nodes:
        if spelling not in nodes[real]['path_spellings']:nodes[real]['path_spellings'].append(spelling)
        continue
    before=facts(path)
    b=path.read_bytes()
    digest=hashlib.sha256(b).hexdigest()
    if facts(path)!=before: raise RuntimeError('file identity changed while read: '+spelling)
    retained=BASE/'files'/digest
    retained.parent.mkdir(parents=True,exist_ok=True)
    if not retained.exists(): retained.write_bytes(b)
    if hashlib.sha256(retained.read_bytes()).hexdigest()!=digest:raise RuntimeError('retained hash mismatch')
    elf=parse_static(path)
    if facts(path)!=before: raise RuntimeError('file identity changed during readelf: '+spelling)
    p=prior.get(spelling)
    node={'path':real,'path_spellings':[spelling],'bytes':len(b),'sha256':digest,'identity':before,'retained_file':str(retained.relative_to(BASE.parent)),'retained_sha256_verified':True,'elf':elf,'E_expected_sha256':p.get('sha256') if p else None,'E_pin_matches':p['sha256']==digest if p else None,'E_dynamic_fields_match':{key:p['elf'].get(key,[])==elf[key] for key in ['needed','rpath','runpath','soname']} if p and p.get('elf') else None,'root_reason':roots.get(spelling)}
    c_file=C_RETAINED/real.lstrip('/')
    node['C_retention']={'archive_member':'absolute_paths/'+real.lstrip('/'),'available_locally':c_file.is_file(),'hash_matches':hashlib.sha256(c_file.read_bytes()).hexdigest()==digest if c_file.is_file() else None}
    node['retained_file_scope']='scratch review intermediate; excluded from G publication/allocation; durable byte custody is C_retention when its hash_matches is true'
    nodes[real]=node
    own=expanded(elf['runpath'] or elf['rpath'],path)
    for name in elf['needed']+elf['interpreter']:
        role='PT_INTERP' if name in elf['interpreter'] else 'DT_NEEDED'
        tiers=[]
        if '/' in name: tiers=[('literal_path',[Path(name)])]
        else:
            tiers=[('object_RUNPATH' if elf['runpath'] else 'object_RPATH',[d/name for d in own]),('known_runtime_system_directories',[d/name for d in dirs]),('E_observed_name_fallback',[Path(x) for x in sorted(aliases[name])])]
        candidates=[]
        selected=None
        tier_selected=None
        for tier,choices in tiers:
            found={str(x.resolve()):str(x) for x in choices if ordinary_elf(x)}
            candidates.append({'tier':tier,'ordinary_candidates':[{'realpath':k,'spelling':v} for k,v in sorted(found.items())]})
            if selected is None and found:
                tier_selected=tier
                selected=sorted(found)[0] if len(found)==1 else None
                if len(found)>1:
                    errors.append({'from':real,'needed':name,'problem':'multiple_candidates_in_preferred_nonempty_tier','tier':tier,'candidates':sorted(found)})
                    break
        edge={'from':real,'name':name,'role':role,'candidates':candidates,'to':selected,'selected_tier':tier_selected,'status':'static_candidate_resolved' if selected else 'unresolved_or_ambiguous'}
        edges.append(edge)
        if selected: queue.append(selected)
        else:errors.append({'from':real,'needed':name,'problem':'unresolved_or_ambiguous_dependency'})

inventory={
 'schema':'seti-codec16-G-static-native-inventory-v1',
 'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'STATIC_INPUT_PINS_AND_CANDIDATE_DEPENDENCY_GRAPH_ONLY',
 'source_metadata':{'path':str(SOURCE),'sha256':hashlib.sha256(meta_bytes).hexdigest(),'bytes':len(meta_bytes)},
 'roots':[{'path':p,'reason':r} for p,r in sorted(roots.items())],
 'system_search_directories':[str(d) for d in dirs],
 'nodes':sorted(nodes.values(),key=lambda n:n['path']), 'edges':edges,'exceptions':errors,
 'counts':{'roots':len(roots),'retained_ordinary_elf_files':len(nodes),'retained_bytes':sum(n['bytes'] for n in nodes.values()),'edges':len(edges),'unresolved_or_ambiguous_edges':sum(e['to'] is None for e in edges),'E_pin_mismatches':sum(n['E_pin_matches'] is False for n in nodes.values())},
 'authority':{'target_executed':False,'native_target_executed':False,'ldd_or_loader_trace_used':False,'scientific_execution_authorized':False,'runtime_graph_certified_complete':False,'certificate_issued':False},
 'retention_policy':'native/files copies are scratch review intermediates, not G scientific runtime clones. C archive references supply prior durable byte custody where checked; missing C members must be separately retained before such custody is claimed.',
 'limitations':[
  'Static candidate resolution is not a dynamic-loader execution trace or a certified complete runtime graph.',
  'Own-object RUNPATH takes precedence over own-object RPATH; inherited RPATH context, LD_LIBRARY_PATH, ld.so.cache ordering, hwcaps directories, namespace reuse, interposition, and loader build-specific choices are not fully modeled.',
  'Known runtime/system directories are a declared static lookup tier, not a proof of effective glibc search precedence.',
  'E map observations describe the prior E process only, not G; no new executable was launched for this inventory.',
  'dlopen dependencies, plugin registrations, internal code paths, dynamic symbol/version compatibility and non-ELF runtime/source files are not established by DT_NEEDED recursion.',
  'All NumPy and h5py E-declared native modules and all twelve hdf5plugin ELF files are deliberately broader than a minimal bitshuffle control dependency set.',
  'E supervisor exec_seal.so is excluded because G uses a separately built control supervisor; G must independently pin that supervisor if executed.'
 ]
}
(BASE/'native-inventory.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n')
print(json.dumps(inventory['counts'],sort_keys=True))
