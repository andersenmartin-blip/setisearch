"""Independent transcript review, never a scientific CAS qualification.

Inputs are the externally pinned original scope plus complete visible connector
operation records. This checks their semantics, not hidden HTTP traffic or
authenticity against a hostile caller. Immutable Git readback is also required.
"""
import base64
import hashlib
import json
from pathlib import Path
import re

LABELS = ('branch_absence','branch_create','branch_initial_read','ledger_create',
          'ledger_commit_read','ledger_initial_read','interference_create',
          'interference_commit_read','ledger_after_interference_read',
          'branch_after_interference_read','ledger_update','ledger_update_commit_read',
          'stale_blob_update','branch_final_read','ledger_final_read',
          'interference_final_read','science_head_final_read')
TOOLS = tuple('mcp__codex_apps__github_'+('create_branch' if label=='branch_create'
    else 'create_file' if label in ('ledger_create','interference_create')
    else 'update_file' if label in ('ledger_update','stale_blob_update') else 'fetch')
    for label in LABELS)


def need(value, message):
    if not value:
        raise ValueError(message)


def pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def pinned_json(raw, expected):
    need(type(raw) is bytes and 0 < len(raw) <= 4*1024**2 and pin(raw)==expected,
         'independent raw pin differs')
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'duplicate JSON member'); result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))


def body(row):
    result=row['result']
    need(not result.get('isError') and not result.get('call_error'),'expected successful tool result')
    value=result['structuredContent']
    return json.loads(value['content']) if type(value.get('content')) is str and value.get('encoding')!='base64' else value


def returned_commit(row):
    value=body(row); got=value.get('commit_sha',value.get('sha'))
    need(type(got) is str and re.fullmatch('[0-9a-f]{40}',got),'returned Git commit differs')
    return got


def blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,
                      allow_nan=False).encode()+b'\n'


def review(scope_raw, scope_pin, terminal_raw, terminal_pin, *, expected_freeze_commit):
    scope=pinned_json(scope_raw,scope_pin); terminal=pinned_json(terminal_raw,terminal_pin)
    need(scope['domain']=='synthetic-service-probe-only' and scope['scientific_execution_authorized'] is False
         and terminal['scientific_execution_authorized'] is False
         and terminal['qualified_atomic_expected_revision_cas'] is False
         and terminal['complete_hosted_transport_qualified'] is False,
         'no scientific or complete service authority allowed')
    need(terminal['status']=='OBSERVED_FILE_BLOB_CAS_ONLY'
         and terminal['probe_identity']==scope['probe_identity']
         and terminal['probe_identity_permanently_spent'] is True
         and terminal['automatic_retry_or_resume'] is False,'closed observed probe required')
    rows=terminal['operations']; need(type(rows) is list and len(rows)==17,'complete seventeen operations required')
    need(terminal['visible_connector_calls']==17<=scope['max_visible_connector_calls'],'call count differs')
    need(type(terminal['elapsed_visible_milliseconds']) is int
         and 0<=terminal['elapsed_visible_milliseconds']<scope['admission_deadline_milliseconds'],
         'visible admission deadline exceeded')
    total=0; previous=0
    by={}
    for i,(row,label,tool) in enumerate(zip(rows,LABELS,TOOLS,strict=True)):
        need(row['ordinal']==i and row['label']==label and row['tool']==tool,'ordered unique operation differs')
        before,after=row['before_epoch_milliseconds'],row['after_epoch_milliseconds']
        need(type(before) is int and type(after) is int and previous<=before<=after,'nondecreasing integer clock required')
        count=len(json.dumps(row['result'],ensure_ascii=False,separators=(',',':')).encode('utf-16-le'))//2
        need(type(row['serialized_response_characters']) is int and row['serialized_response_characters']==count,
             'individual visible response accounting differs')
        previous=after;total+=count;by[label]=row
    need(total==terminal['serialized_response_characters']<=scope['serialized_response_ceiling_characters'],
         'visible response accounting differs')
    for label,status in (('branch_absence',404),('stale_blob_update',409)):
        result=by[label]['result']
        need(result.get('isError') is True or bool(result.get('call_error')),'expected error not observed')
        need(re.search(r'\b'+str(status)+r'\b',json.dumps(result)) is not None,'positive HTTP error status absent')
    repo,branch=scope['repository'],scope['branch']; api='https://api.github.com/repos/'+repo
    r0=returned_commit(by['ledger_create']);r1=returned_commit(by['interference_create']);r2=returned_commit(by['ledger_update'])
    need(len({scope['base_commit'],r0,r1,r2})==4,'distinct observed commit identities required')
    for label,revision,parent in (('ledger_commit_read',r0,scope['base_commit']),
            ('interference_commit_read',r1,r0),('ledger_update_commit_read',r2,r1)):
        row=by[label];value=body(row)
        need(row['args']=={'url':api+'/git/commits/'+revision} and value['sha']==revision
             and [p['sha'] for p in value['parents']]==[parent],'actual immutable commit graph differs')
    for label,revision in (('branch_initial_read',scope['base_commit']),('branch_after_interference_read',r1),('branch_final_read',r2)):
        row=by[label];need(row['args']=={'url':api+'/branches/'+branch}
            and body(row)['name']==branch and body(row)['commit']['sha']==revision,'observed branch differs')
    need(by['branch_create']['args']=={'repository_full_name':repo,'branch_name':branch,'sha':scope['base_commit']},
         'fresh branch seed differs')
    initial=scope['initial_record_raw'].encode(); initial_blob=blob(initial)
    update=canonical({'schema':'radio-contents-cas-probe-record-v1','domain':scope['domain'],
        'probe_identity':scope['probe_identity'],'revision':1,'expected_branch_revision':r0,
        'scientific_execution_authorized':False})
    rejected=canonical({'schema':'radio-contents-cas-probe-record-v1','domain':scope['domain'],
        'probe_identity':scope['probe_identity'],'revision':2,'expected_branch_revision':r2,
        'scientific_execution_authorized':False})
    path=scope['ledger_path']
    def contents(label,p,revision,raw):
        row=by[label];value=body(row)
        need(row['args']=={'url':api+'/contents/'+p+'?ref='+revision}
             and value['type']=='file' and value['path']==p and value['encoding']=='base64'
             and value['sha']==blob(raw) and value['size']==len(raw)
             and base64.b64decode(value['content'])==raw,'complete Git-pinned contents differ')
    contents('ledger_initial_read',path,r0,initial)
    contents('ledger_after_interference_read',path,r1,initial)
    contents('ledger_final_read',path,r2,update)
    contents('interference_final_read',scope['interference_path'],r2,scope['interference_raw'].encode())
    for label,raw,message in (('ledger_create',initial,'Create synthetic file-CAS probe initial record'),
            ('interference_create',scope['interference_raw'].encode(),'Advance synthetic probe branch without changing ledger file')):
        p=path if label=='ledger_create' else scope['interference_path']
        need(by[label]['args']=={'repository_full_name':repo,'branch':branch,'path':p,'content':raw.decode(),'message':message},
             'fixed creation request differs')
    for label,raw,message in (('ledger_update',update,'Probe current file blob with stale observed branch revision'),
            ('stale_blob_update',rejected,'Negative probe of stale file blob; expected conflict')):
        need(by[label]['args']=={'repository_full_name':repo,'branch':branch,'path':path,'sha':initial_blob,
             'content':raw.decode(),'message':message},'fixed file-blob update request differs')
    science=by['science_head_final_read']
    need(science['args']=={'url':api+'/branches/m43-support-qualification'}
         and body(science)['commit']['sha']==expected_freeze_commit,'primary branch moved during probe')
    return {'schema':'radio-contents-cas-transcript-review-v1','status':'TRANSCRIPT_COUNTEREXAMPLE_VERIFIED',
        'probe_identity':scope['probe_identity'],'observed_initial_commit':r0,'observed_interference_commit':r1,
        'observed_update_commit':r2,'stale_expected_branch_revision_accepted_in_content':r0,
        'actual_update_parent':r1,'initial_file_blob':initial_blob,'updated_file_blob':blob(update),
        'stale_file_blob_conflict_observed':True,'operations':17,'automatic_retry_or_resume':False,
        'qualified_atomic_expected_revision_cas':False,'complete_hosted_transport_qualified':False,
        'scientific_execution_authorized':False,'original_scientific_store_modified':False}
