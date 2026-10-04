import base64
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_probe as r


def fixture():
    scope={'domain':'synthetic-service-probe-only','scientific_execution_authorized':False,
      'probe_identity':'a'*64,'repository':'andersenmartin-blip/setisearch',
      'branch':'radio-contents-cas-probe-20261004b','base_commit':'0'*40,
      'ledger_path':'synthetic_contents_cas_probe_20261004b/ledger.json','interference_path':'synthetic_contents_cas_probe_20261004b/interference.json',
      'initial_record_raw':'{"revision":0}\n','interference_raw':'{"interference":true}\n',
      'max_visible_connector_calls':18,'admission_deadline_milliseconds':180000,
      'serialized_response_ceiling_characters':2*1024**2,'repository_root':'/synthetic/probe',
      'scope_path':'/synthetic/probe/scope.json','python_executable':{'path':'/synthetic/python'},
      'code_pins':{'git_probe_readback.py':{'path':'/synthetic/probe/git_probe_readback.py'}}}
    api='https://api.github.com/repos/'+scope['repository']; branch=scope['branch']; repo=scope['repository']
    path=scope['ledger_path']
    def commit_bytes(parent):
        return ('tree '+('6'*40)+'\nparent '+parent+'\nauthor Fixture <fixture@example.invalid> 0 +0000\ncommitter Fixture <fixture@example.invalid> 0 +0000\n\nsynthetic fixture\n').encode()
    def commit_id(raw):return r.hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    c0=commit_bytes(scope['base_commit']);r0=commit_id(c0)
    c1=commit_bytes(r0);r1=commit_id(c1)
    c2=commit_bytes(r1);r2=commit_id(c2)
    initial=scope['initial_record_raw'].encode();b0=r.blob(initial)
    update=r.canonical({'schema':'radio-contents-cas-probe-record-v1','domain':scope['domain'],
        'probe_identity':scope['probe_identity'],'revision':1,'expected_branch_revision':r0,
        'scientific_execution_authorized':False}).decode()
    rejected=r.canonical({'schema':'radio-contents-cas-probe-record-v1','domain':scope['domain'],
        'probe_identity':scope['probe_identity'],'revision':2,'expected_branch_revision':r2,
        'scientific_execution_authorized':False}).decode()
    rows=[{'ordinal':i,'label':label,'tool':tool,'args':{},'before_epoch_milliseconds':100+i*2,
        'after_epoch_milliseconds':101+i*2,'result':{'structuredContent':{}},
        'serialized_response_characters':0} for i,(label,tool) in enumerate(zip(r.LABELS,r.TOOLS))]
    by={row['label']:row for row in rows}
    def data(label,value):by[label]['result']={'structuredContent':value}
    def get(label,url):by[label]['args']={'url':url}
    get('branch_absence',api+'/branches/'+branch)
    by['branch_absence']['result']={'isError':True,'content':[{'type':'text','text':'HTTP 404 Not Found'}]}
    by['branch_create']['args']={'repository_full_name':repo,'branch_name':branch,'sha':scope['base_commit']}
    for label,sha in (('branch_initial_read',scope['base_commit']),('branch_after_interference_read',r1),('branch_final_read',r2)):
        get(label,api+'/branches/'+branch);data(label,{'name':branch,'commit':{'sha':sha}})
    for label,sha,parent in (('ledger_commit_read',r0,scope['base_commit']),('interference_commit_read',r1,r0),('ledger_update_commit_read',r2,r1)):
        get(label,api+'/git/commits/'+sha);data(label,{'sha':sha,'parents':[{'sha':parent}]})
    for label,raw,message,sha,p in (
        ('ledger_create',scope['initial_record_raw'],'Create synthetic file-CAS probe initial record',r0,path),
        ('interference_create',scope['interference_raw'],'Advance synthetic probe branch without changing ledger file',r1,scope['interference_path'])):
        by[label]['args']={'repository_full_name':repo,'branch':branch,'path':p,'content':raw,'message':message}
        data(label,{'commit_sha':sha})
    for label,raw,message in (
        ('ledger_update',update,'Probe current file blob with stale observed branch revision'),
        ('stale_blob_update',rejected,'Negative probe of stale file blob; expected conflict')):
        by[label]['args']={'repository_full_name':repo,'branch':branch,'path':path,'sha':b0,'content':raw,'message':message}
    data('ledger_update',{'commit_sha':r2,'content_sha':r.blob(update.encode())})
    by['stale_blob_update']['result']={'isError':True,'content':[{'type':'text','text':'HTTP 409 Conflict'}]}
    for label,p,sha,raw in (('ledger_initial_read',path,r0,initial),('ledger_after_interference_read',path,r1,initial),
        ('ledger_final_read',path,r2,update.encode()),('interference_final_read',scope['interference_path'],r2,scope['interference_raw'].encode())):
        get(label,api+'/contents/'+p+'?ref='+sha)
        url=api+'/contents/'+p+'?ref='+sha
        data(label,{'url':url,'title':p.rsplit('/',1)[-1],'content':raw.decode(),'structuredContent':{'content':raw.decode(),'display_url':url}})
    get('science_head_final_read',api+'/branches/m43-support-qualification')
    data('science_head_final_read',{'commit':{'sha':'4'*40}})
    terminal={'status':'OBSERVED_FILE_BLOB_CAS_ONLY','probe_identity':scope['probe_identity'],
      'scientific_execution_authorized':False,'qualified_atomic_expected_revision_cas':False,
      'complete_hosted_transport_qualified':False,'probe_identity_permanently_spent':True,
      'automatic_retry_or_resume':False,'operations':rows,'visible_connector_calls':17,
      'elapsed_visible_milliseconds':34,'serialized_response_characters':0}
    terminal['git_readbacks']=[]
    for phase,revision,parent,commit_raw,files in (('initial',r0,scope['base_commit'],c0,{path:initial}),
        ('interference',r1,r0,c1,{path:initial,scope['interference_path']:scope['interference_raw'].encode()}),
        ('final',r2,r1,c2,{path:update.encode(),scope['interference_path']:scope['interference_raw'].encode()})):
        argv=[['git','fetch','--no-tags','https://github.com/andersenmartin-blip/setisearch.git','refs/heads/'+branch+':refs/remotes/origin/'+branch],
            ['git','rev-parse','refs/remotes/origin/'+branch],['git','cat-file','-p',revision],
            ['git','ls-tree','-r','--full-tree',revision,'--',path,scope['interference_path']],['git','cat-file','blob',revision+':'+path]]
        stdout=[b'',(revision+'\n').encode(),commit_raw, ''.join('100644 blob '+r.blob(raw)+'\t'+p+'\n' for p,raw in sorted(files.items())).encode(),files[path]]
        if phase!='initial':argv.append(['git','cat-file','blob',revision+':'+scope['interference_path']]);stdout.append(files[scope['interference_path']])
        operations=[{'argv':a,'returncode':0,'stdout':{**r.pin(raw),'base64':base64.b64encode(raw).decode()},'stderr':{**r.pin(b''),'base64':''}} for a,raw in zip(argv,stdout)]
        proof={'schema':'radio-contents-cas-native-readback-v1','status':'SELECTED_GIT_BYTES_VERIFIED','phase':phase,'expected_commit':revision,'expected_parent':parent,'actual_tree':'6'*40,
            'git_processes':len(operations),'operations':operations,'captured_output_bytes':sum(len(v) for v in stdout),
            'selected_files':{p:{'git_blob':r.blob(raw),**r.pin(raw),'raw_ascii':raw.decode()} for p,raw in files.items()},
            'scientific_execution_authorized':False,'qualified_atomic_expected_revision_cas':False,'complete_hosted_transport_qualified':False}
        sq=lambda value:"'"+value.replace("'","'\\''")+"'"
        command=' '.join(map(sq,(scope['python_executable']['path'],scope['code_pins']['git_probe_readback.py']['path'],scope['scope_path'],
            r.pin(r.canonical(scope))['sha256'],phase,revision,parent)))
        terminal['git_readbacks'].append({'phase':phase,'before_epoch_milliseconds':100,'after_epoch_milliseconds':101,
            'args':{'cmd':command,'workdir':scope['repository_root'],'max_output_tokens':20000,'yield_time_ms':30000},
            'response':{'exit_code':0,'output':json.dumps(proof)}})
    recount(terminal)
    return scope,terminal


def recount(terminal):
    total=0
    for row in terminal['operations']:
        row['serialized_response_characters']=len(json.dumps(row['result'],ensure_ascii=False,separators=(',',':')).encode('utf-16-le'))//2
        total+=row['serialized_response_characters']
    terminal['serialized_response_characters']=total


def verify(scope,terminal):
    a,b=r.canonical(scope),r.canonical(terminal)
    return r.review(a,r.pin(a),b,r.pin(b),expected_freeze_commit='4'*40)


class Tests(unittest.TestCase):
    def test_complete_fixture_is_a_counterexample_and_never_authority(self):
        scope,terminal=fixture();result=verify(scope,terminal)
        self.assertEqual(result['actual_update_parent'],r.returned_commit(terminal['operations'][6]))
        self.assertEqual(result['stale_expected_branch_revision_accepted_in_content'],r.returned_commit(terminal['operations'][3]))
        self.assertFalse(result['qualified_atomic_expected_revision_cas'])
        self.assertFalse(result['scientific_execution_authorized'])

    def test_omitting_interference_or_extra_retry_cannot_pass(self):
        for mutate in (lambda rows:rows.pop(6),lambda rows:rows.append(copy.deepcopy(rows[10]))):
            s,t=fixture();mutate(t['operations']);recount(t)
            with self.assertRaises(ValueError):verify(s,t)

    def test_wrong_commit_parent_cannot_hide_branch_change(self):
        s,t=fixture();t['operations'][11]['result']['structuredContent']['parents']=[{'sha':'1'*40}];recount(t)
        with self.assertRaises(ValueError):verify(s,t)

    def test_mutated_or_wrong_blob_payload_cannot_pass(self):
        for key,value in (('url','https://wrong.example.invalid'),('content','wrong')):
            s,t=fixture();t['operations'][14]['result']['structuredContent'][key]=value;recount(t)
            with self.assertRaises(ValueError):verify(s,t)

    def test_failed_update_cannot_be_counted_as_success(self):
        s,t=fixture();t['operations'][10]['result']={'isError':True,'content':[{'type':'text','text':'HTTP 409 Conflict'}]};recount(t)
        with self.assertRaises(ValueError):verify(s,t)

    def test_error_text_without_positive_error_or_409_cannot_pass(self):
        for result in ({'isError':False,'content':[{'type':'text','text':'HTTP 409 Conflict'}]},
                       {'isError':True,'content':[{'type':'text','text':'ambiguous network failure'}]}):
            s,t=fixture();t['operations'][12]['result']=result;recount(t)
            with self.assertRaises(ValueError):verify(s,t)

    def test_response_clock_and_tool_substitution_are_refused(self):
        for change in ('response','clock','tool'):
            s,t=fixture()
            if change=='response':t['operations'][4]['serialized_response_characters']+=1
            if change=='clock':t['operations'][4]['before_epoch_milliseconds']=True
            if change=='tool':t['operations'][10]['tool']='mcp__codex_apps__github_update_ref'
            with self.assertRaises(ValueError):verify(s,t)

    def test_authority_promotion_and_primary_branch_change_are_refused(self):
        for change in ('authority','head'):
            s,t=fixture()
            if change=='authority':t['scientific_execution_authorized']=True
            else:t['operations'][16]['result']['structuredContent']['commit']['sha']='f'*40;recount(t)
            with self.assertRaises(ValueError):verify(s,t)

    def test_raw_pin_mutation_is_refused(self):
        s,t=fixture();a,b=r.canonical(s),r.canonical(t)
        with self.assertRaises(ValueError):r.review(a+b' ',r.pin(a),b,r.pin(b),expected_freeze_commit='4'*40)

    def test_missing_native_proof_or_argv_substitution_cannot_pass(self):
        for change in ('missing','argv'):
            s,t=fixture()
            if change=='missing':t['git_readbacks'].pop()
            else:t['git_readbacks'][0]['args']['cmd']="arbitrary command"
            with self.assertRaises(ValueError):verify(s,t)

    def test_native_commit_hash_and_git_byte_mutations_are_refused(self):
        for change in ('commit','bytes'):
            s,t=fixture();proof=json.loads(t['git_readbacks'][0]['response']['output'])
            if change=='commit':proof['operations'][2]['stdout']={**r.pin(b'wrong'),'base64':base64.b64encode(b'wrong').decode()}
            else:proof['selected_files'][s['ledger_path']]['git_blob']='f'*40
            t['git_readbacks'][0]['response']['output']=json.dumps(proof)
            with self.assertRaises(ValueError):verify(s,t)


if __name__=='__main__':unittest.main()
