#!/usr/bin/env python3
"""Read-only literal F terminal inventory, with exact qualified omissions.

No journal is opened. Only named terminal F files and independently pinned
verification/public-source-proof metadata are read. Stdout is canonical JSON;
no original/protected file, Git ref/index or artifact is modified.
"""
import argparse
import hashlib
import json
import os
import re
import stat

SCOPE = 'results_radio_native_v3_compact_eight_input_control_20261003f'
MAX_FILE = 8 * 1024 * 1024
LARGE = {'cases/case00/deterministic-source.bin':'payload',
    'cases/case00/store/items/request-000001/part':'wire',
    'cases/case00/caller-result.json':'partial'}


def sha(raw): return hashlib.sha256(raw).hexdigest()


def absolute(path):
    if (not isinstance(path,str) or not path.startswith('/') or path=='/' or '\\' in path
            or re.search(r'[\x00-\x1f\x7f]',path) or any(x in ('','.','..') for x in path[1:].split('/'))):
        raise ValueError('Canonical absolute path required')
    return path


def signature(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def directory(path,witnesses):
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);current=''
    try:
        for name in absolute(path)[1:].split('/'):
            child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child;current+='/'+name
            info=os.fstat(fd);identity=(info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid)
            if current in witnesses and witnesses[current]!=identity:raise ValueError('Named ancestry changed')
            witnesses[current]=identity
        return fd
    except BaseException:os.close(fd);raise


def raw_file(path,witnesses,expected=None):
    parent,name=path.rsplit('/',1);parent_fd=directory(parent,witnesses);fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent_fd)
    try:
        info=os.fstat(fd);before=signature(info)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>MAX_FILE:raise ValueError('Bounded sole-link regular literal required')
        chunks=[];count=0
        while True:
            raw=os.read(fd,min(65536,info.st_size+1-count))
            if not raw:break
            count+=len(raw)
            if count>info.st_size:raise ValueError('Literal grew during bounded read')
            chunks.append(raw)
        raw=b''.join(chunks)
        if count!=info.st_size or before!=signature(os.fstat(fd)) or before!=signature(os.stat(name,dir_fd=parent_fd,follow_symlinks=False)):raise ValueError('Literal changed during held read')
        if expected is not None and sha(raw)!=expected:raise ValueError('Independent metadata pin differs')
        return raw,info
    finally:os.close(fd);os.close(parent_fd)


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate inventory metadata key')
        result[key]=value
    return result


def snapshot(scope,witnesses):
    rows={};pending=[scope]
    while pending:
        path=pending.pop();fd=directory(path,witnesses)
        try:
            info=os.fstat(fd);relative=path[len(scope):].lstrip('/') or '.'
            rows[relative]=info
            for name in sorted(os.listdir(fd)):
                child=path+'/'+name;value=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if stat.S_ISDIR(value.st_mode):pending.append(child)
                elif stat.S_ISREG(value.st_mode) and value.st_nlink==1:rows[child[len(scope)+1:]]=value
                else:raise ValueError('Alias/nonregular terminal entry refused')
                if len(rows)+len(pending)>10000:raise ValueError('Terminal inventory entry cap')
        finally:os.close(fd)
    return rows


def inventory(root,verification,verification_sha256,source_proof,source_proof_sha256,expected_D_commit,expected_D_tree):
    root=absolute(root);scope=root+'/'+SCOPE;witnesses={}
    verification_raw,_=raw_file(absolute(verification),witnesses,verification_sha256)
    verified=json.loads(verification_raw,object_pairs_hook=unique)
    proof_raw,_=raw_file(absolute(source_proof),witnesses,source_proof_sha256)
    proof=json.loads(proof_raw,object_pairs_hook=unique)
    if (proof['status']!='PASS_SELECTED_FROZEN_BYTE_EQUIVALENCE' or proof['immutable_commit']!=expected_D_commit
            or proof['immutable_tree']!=expected_D_tree or proof['selected_unique_path_count']!=1004):raise ValueError('Exact independently retained public D proof required')
    public={row['path']:row for row in proof['files']}
    if len(public)!=1004:raise ValueError('Exact selected public D inventory required')
    plan_raw,_=raw_file(scope+'/plan.json',witnesses);plan=json.loads(plan_raw,object_pairs_hook=unique)
    if len(plan['code_files'])!=66:raise ValueError('Exact preserved F CODE66 required')
    comparisons={row['original']['path']:row for row in verified['direct_original_restored_comparisons']}
    if (verified['actual_full_offline_decoder_invocations']!=1 or not verified['all_original_content_and_identity_unchanged']
            or len(comparisons)!=3 or verified['originals_before']!=verified['originals_after']):raise ValueError('One exact original offline restoration qualification required')
    before=snapshot(scope,witnesses);literal=[];copies=[];replaced=[];directories=[]
    for relative,info in sorted(before.items()):
        row={'path':relative,'repository_path':SCOPE+('/'+relative if relative!='.' else ''),
            'kind':'directory' if stat.S_ISDIR(info.st_mode) else 'file','bytes':info.st_size,'allocated_bytes':info.st_blocks*512,
            'device':info.st_dev,'inode':info.st_ino,'mode':format(stat.S_IMODE(info.st_mode),'04o'),'nlink':info.st_nlink,
            'uid':info.st_uid,'gid':info.st_gid,'mtime_ns':info.st_mtime_ns,'ctime_ns':info.st_ctime_ns}
        if row['kind']=='directory':directories.append(row);continue
        path=scope+'/'+relative
        if relative in LARGE:
            comparison=comparisons[path];original=comparison['original']
            if (not comparison['byte_for_byte_equal'] or list(signature(info))!=original['identity']
                    or comparison['restored']['bytes']!=original['bytes'] or comparison['restored']['sha256']!=original['sha256']):raise ValueError('Qualified omission original identity differs')
            row.update({'sha256':original['sha256'],'publication':'REPLACED_LOSSLESSLY_ORIGINAL_CODEC_AND_BYTE_PROJECTION',
                'codec_input':LARGE[relative],'qualified_restored_bytes':original['bytes'],'qualified_restored_sha256':original['sha256'],
                'original_file_full_byte_compare_qualified':True,'raw_pin_from_independently_retained_direct_comparison':True})
            replaced.append(row);continue
        raw,observed=raw_file(path,witnesses)
        if signature(observed)!=signature(info):raise ValueError('Original changed between snapshot and byte read')
        row.update({'sha256':sha(raw),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()})
        prefix=next((prefix for prefix in ('frozen-code/','cases/case00/frozen-code/') if relative.startswith(prefix)),None)
        if prefix:
            original_path=relative[len(prefix):];pin=plan['code_files'].get(original_path);pub=public.get(original_path)
            if pin!={'bytes':len(raw),'sha256':sha(raw)} or pub is None or pub['bytes']!=len(raw) or pub['sha256']!=sha(raw) or pub['git_blob_sha']!=row['git_blob_sha1']:raise ValueError('Repeated frozen bytes differ from actual admitted public D source')
            row.update({'publication':'OMIT_REPEATED_FROZEN_COPY_WITH_IMMUTABLE_D_BYTE_PIN','original_repository_path':original_path,
                'immutable_D_commit':expected_D_commit,'immutable_D_tree':expected_D_tree,'immutable_D_blob':pub['git_blob_sha']})
            copies.append(row)
        else:
            raw.decode('utf8');row['publication']='FULL_LITERAL_ORIGINAL_UTF8_INCLUDING_ZERO_LENGTH'
            literal.append(row)
    after=snapshot(scope,witnesses)
    if set(before)!=set(after) or any(signature(before[name])!=signature(after[name]) for name in before):raise ValueError('Terminal files/directories changed during inventory')
    if (len(literal),len(copies),len(replaced),len(directories))!=(307,132,3,80):raise ValueError('Exact terminal F inventory cardinality differs')
    if not any(row['path']=='engineering-observer-stdout.log' and row['bytes']==0 for row in literal):raise ValueError('Actual zero observer stdout must remain literal')
    return {'schema':'radio-native-v3-terminal-f-lossless-publication-inventory-v1','status':'PASS_ORIGINAL_F_LITERAL_AND_QUALIFIED_LOSSLESS_SELECTION',
        'repository_root':root,'terminal_scope':scope,'terminal_state':'CLOSED_FAILED_PERMANENTLY_SPENT','completed_cases':0,'successful_source_reads':24,
        'original_file_count':442,'original_directory_count':80,'full_literal_file_count':307,'repeated_frozen_copy_omission_count':132,'losslessly_replaced_original_count':3,
        'full_literal_total_bytes':sum(row['bytes'] for row in literal),'full_literal_max_bytes':max(row['bytes'] for row in literal),
        'current_original_logical_bytes_including_directories':sum(row['bytes'] for row in literal+copies+replaced+directories),
        'current_original_allocated_bytes_including_directories':sum(row['allocated_bytes'] for row in literal+copies+replaced+directories),
        'full_literal_originals':literal,'omitted_repeated_frozen_code':copies,'losslessly_replaced_originals':replaced,'literal_current_storage_directories':directories,
        'offline_verification_raw_pin':{'bytes':len(verification_raw),'sha256':sha(verification_raw)},'public_D_source_proof_raw_pin':{'bytes':len(proof_raw),'sha256':sha(proof_raw)},
        'immutable_D_commit':expected_D_commit,'immutable_D_tree':expected_D_tree,'all_original_scope_content_and_identity_unchanged':True,
        'all_actual_zero_files_retained_literally':True,'unretained_inner_stderr_raw_bytes_recoverable':False,
        'unretained_inner_stderr_known_bytes':3000,'unretained_inner_stderr_sha256':'53e6fd2fddff5386ba544702f20cdf4870856ed4d1d452bec2a4f4151cc29875',
        'exact_failure_cause_proven':False,'private_journal_file_content_reads':0,'original_scope_writes':0,'Git_operations':0,
        'original_recipe_executions':0,'new_control_invocations':0,'scientific_cases_run':0,'native_case_executions':0,'rng_draws':0,'telescope_reads':0,
        'execution_authorized':False,'scientific_execution_authorized':False,'public_selection_includes_all_literal_originals_and_exact_pinned_omissions':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('root','verification','verification-sha256','source-proof','source-proof-sha256','expected-D-commit','expected-D-tree'):parser.add_argument('--'+name,required=True)
    result=inventory(**vars(parser.parse_args()))
    print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))


if __name__=='__main__':main()
