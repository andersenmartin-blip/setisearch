"""Repository/Python/NumPy file closure for the live engineering publisher.

Covers repository source/scripts, stdlib source/extension files, NumPy package
files and ldd-resolved shared objects. This is a measured engineering runtime,
not the future Gaussian/physical/codec scientific executable protocol.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import sysconfig
import numpy as np
from .empty_null_radio import canonical
from .whole_cadence_reference_radio import digest


def sha_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def loaded_files():
    return {str(Path(p).resolve()) for m in tuple(sys.modules.values())
        if isinstance(p:=getattr(m,'__file__',None),str) and Path(p).is_file()}


def repository_inventory(root):
    root=Path(root)
    return sorted(str(p.relative_to(root)) for folder in ('src/seti_repeater','scripts') for p in (root/folder).rglob('*.py'))


def runtime_inventory():
    std=Path(sysconfig.get_path('stdlib'));numpy_root=Path(np.__file__).parent
    files={Path(sys.executable).resolve()}
    for p in std.rglob('*'):
        if 'site-packages' in p.relative_to(std).parts or '__pycache__' in p.parts:continue
        if p.is_file() and (p.suffix in ('.py','.so') or '.so.' in p.name):files.add(p.resolve())
    for folder in (numpy_root,numpy_root.parent/'numpy.libs'):
        if folder.exists():
            for p in folder.rglob('*'):
                if p.is_file() and (p.suffix in ('.py','.so') or '.so.' in p.name):files.add(p.resolve())
    # ldd also reports transitive ELF dependencies of the executable/extensions.
    dependencies=set();unavailable={};loaded=loaded_files()
    for p in sorted(files):
        if p.suffix=='.py':continue
        run=subprocess.run(['ldd',str(p)],capture_output=True,text=True,timeout=10)
        if run.returncode:raise ValueError('Uninspectable runtime ELF dependency: '+str(p))
        missing=[line.strip() for line in run.stdout.splitlines() if 'not found' in line]
        if missing:
            if str(p) in loaded:raise ValueError('Loaded extension has unresolved ELF dependency: '+str(p))
            # Installed optional extension is preserved and hash-pinned, but it
            # must not be represented as an available executable dependency.
            unavailable[str(p)]=missing
        for line in run.stdout.splitlines():
            m=re.search(r'(?:=>\s*)?(/\S+)\s+\(',line)
            if m:dependencies.add(Path(m.group(1)).resolve())
    files|=dependencies
    return sorted(str(p) for p in files),unavailable


def capture(root,input_paths):
    root=Path(root);code=repository_inventory(root);runtime,unavailable=runtime_inventory()
    return {'schema':'radio-whole-cadence-engineering-executable-files-v1','mode':'ENGINEERING_ONLY',
        'scientific_execution_authorized':False,'python':sys.version,'numpy':np.__version__,
        'repository_python_inventory':code,'code_sha256s':{p:sha_file(root/p) for p in code},
        'input_sha256s':{p:sha_file(root/p) for p in input_paths},
        'runtime_file_inventory':runtime,'runtime_sha256s':{p:sha_file(p) for p in runtime},
        'unavailable_unused_extensions':unavailable,
        'coverage':'repository source/scripts; Python stdlib source/extensions; NumPy source/extensions; ldd dependency closure',
        'not_a_scientific_gaussian_physical_or_codec_protocol':True}


class PublishedFreeze:
    def __init__(self,root,commit,path,expected_sha256):
        self.root=Path(root);self.commit=commit;self.path=path;self.expected=expected_sha256
        raw=subprocess.check_output(['git','show',commit+':'+path],cwd=root)
        if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('Published freeze bytes differ')
        self.freeze=json.loads(raw)
        if (self.freeze.get('mode')!='ENGINEERING_ONLY' or self.freeze.get('scientific_execution_authorized') is not False):
            raise ValueError('This verifier cannot activate scientific execution')
        self.freeze_identity=digest(self.freeze)
        pairs={**self.freeze['code_sha256s'],**self.freeze['input_sha256s']}
        # One local Git-object read process. The caller fetched/verified the exact
        # published commit before construction; mutable branch names are not used.
        paths=sorted(pairs);query=''.join(commit+':'+p+'\n' for p in paths).encode()
        output=subprocess.check_output(['git','cat-file','--batch'],cwd=root,input=query)
        offset=0
        for p in paths:
            end=output.index(b'\n',offset);header=output[offset:end].split();offset=end+1
            if len(header)!=3 or header[1]!=b'blob':raise ValueError('Published code/input is not a Git blob: '+p)
            size=int(header[2]);data=output[offset:offset+size];offset+=size+1
            if hashlib.sha256(data).hexdigest()!=pairs[p]:raise ValueError('Published dependency differs: '+p)
        if offset!=len(output):raise ValueError('Git object readback framing differs')
        self.published_files=len(paths)

    def verify(self,manifest):
        f=self.freeze
        if digest(f)!=self.freeze_identity or manifest['mode']!='engineering' or manifest['execution_binding_sha256']!=self.expected:
            raise ValueError('Execution/freeze binding changed')
        if repository_inventory(self.root)!=f['repository_python_inventory']:raise ValueError('Repository Python inventory changed')
        for p,h in {**f['code_sha256s'],**f['input_sha256s']}.items():
            if sha_file(self.root/p)!=h:raise ValueError('Local executable/input bytes changed: '+p)
        for p,h in f['runtime_sha256s'].items():
            if sha_file(p)!=h:raise ValueError('Runtime dependency bytes changed: '+p)
        if loaded_files() & set(f.get('unavailable_unused_extensions',{})):
            raise ValueError('An unavailable optional extension entered the runtime')
        if sys.version!=f['python'] or np.__version__!=f['numpy']:raise ValueError('Runtime versions changed')
        return {'freeze_sha256':self.expected,'published_commit':self.commit,'published_files':self.published_files,
            'runtime_files':len(f['runtime_sha256s']),'scientific_execution_authorized':False}
