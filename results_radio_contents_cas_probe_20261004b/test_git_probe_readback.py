import base64
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import git_probe_readback as g


def setup(phase='initial',change=None):
    ledger='synthetic_contents_cas_probe_20261004b/ledger.json';marker='synthetic_contents_cas_probe_20261004b/interference.json'
    scope={'domain':'synthetic-service-probe-only','scientific_execution_authorized':False,
      'branch':'radio-contents-cas-probe-20261004b','repository':'andersenmartin-blip/setisearch',
      'repository_root':'/tmp','ledger_path':ledger,'interference_path':marker}
    raw=b'{"tiny":true}\n';m=b'{"marker":true}\n';parent='0'*40
    commit=('tree '+('6'*40)+'\nparent '+parent+'\n\nmessage\n').encode()
    r0=g.hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest()
    found={ledger:g.git_blob(raw)}
    if phase!='initial':found[marker]=g.git_blob(m)
    calls=[]
    def invoke(argv,**kw):
        calls.append(argv)
        if change=='timeout':raise subprocess.TimeoutExpired(argv,1,output=b'partial\0stdout',stderr=b'root-cause\xff')
        if argv[1]=='fetch':out=b''
        elif argv[1]=='rev-parse':out=((('f'*40) if change=='head' else r0)+'\n').encode()
        elif argv[1:3]==['cat-file','-p']:out=('tree '+('6'*40)+'\nparent '+(('f'*40) if change=='parent' else parent)+'\n\nmessage\n').encode()
        elif argv[1]=='ls-tree':
            values=dict(found)
            if change=='mode':out=('100755 blob '+found[ledger]+'\t'+ledger+'\n').encode()
            elif change=='missing':out=b''
            else:out=''.join('100644 blob '+sha+'\t'+p+'\n' for p,sha in sorted(values.items())).encode()
        elif argv[-1].endswith(ledger):out=b'wrong' if change=='bytes' else raw
        else:out=m
        return subprocess.CompletedProcess(argv,0,out,b'')
    return scope,r0,parent,invoke,calls,raw


class Tests(unittest.TestCase):
    def test_initial_and_later_exact_tiny_members_pass_without_authority(self):
        for phase,count in (('initial',5),('interference',6),('final',6)):
            s,c,p,f,calls,raw=setup(phase);result=g.read(s,phase,c,p,invoke=f)
            self.assertEqual(result['status'],'SELECTED_GIT_BYTES_VERIFIED',result.get('error'))
            self.assertEqual(result['git_processes'],count)
            self.assertEqual(result['selected_files'][s['ledger_path']]['git_blob'],g.git_blob(raw))
            self.assertFalse(result['scientific_execution_authorized'])

    def test_head_or_parent_change_closes_before_blob_admission(self):
        for change in ('head','parent'):
            s,c,p,f,calls,raw=setup(change=change);result=g.read(s,'initial',c,p,invoke=f)
            self.assertEqual(result['status'],'CLOSED_FAILED')
            self.assertLess(result['git_processes'],5)

    def test_mode_missing_member_and_blob_mutation_are_refused(self):
        for change in ('mode','missing','bytes'):
            s,c,p,f,calls,raw=setup(change=change);result=g.read(s,'initial',c,p,invoke=f)
            self.assertEqual(result['status'],'CLOSED_FAILED')

    def test_timeout_retains_exact_binary_partial_outputs(self):
        s,c,p,f,calls,raw=setup(change='timeout');result=g.read(s,'initial',c,p,invoke=f)
        self.assertEqual(result['status'],'CLOSED_FAILED')
        op=result['operations'][0];self.assertIsNone(op['returncode'])
        self.assertEqual(base64.b64decode(op['stdout']['base64']),b'partial\0stdout')
        self.assertEqual(base64.b64decode(op['stderr']['base64']),b'root-cause\xff')

    def test_non_synthetic_branch_or_path_cannot_start_processes(self):
        for field,value in (('domain','public-scientific-evidence'),('branch','m43-support-qualification'),
            ('ledger_path','../../old-ledger.json')):
            s,c,p,f,calls,raw=setup();s[field]=value
            with self.assertRaises(ValueError):g.read(s,'initial',c,p,invoke=f)
            self.assertEqual(calls,[])


if __name__=='__main__':unittest.main()
