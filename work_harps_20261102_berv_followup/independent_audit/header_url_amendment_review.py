#!/usr/bin/env python3
"""Narrow offline audit of the literal-colon ESO header URL amendment.

No network entry point is run. Only the URL-validation loop is extracted from
the frozen fetcher and exercised with synthetic strings. No science arrays or
actual astronomical headers are read.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=HERE.parent/'header_acquisition'
NEW=HERE.parent/'header_acquisition_v2'
FILES=['header_tools.py','make_plan.py','fetch_headers.py','select_extremes.py']
checks=[]
sys.dont_write_bytecode=True


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def record(name,ok,detail=None): checks.append(dict(check=name,passed=bool(ok),detail=detail))


def load(name):
    spec=importlib.util.spec_from_file_location(name,NEW/(name+'.py'))
    obj=importlib.util.module_from_spec(spec); sys.modules[name]=obj; spec.loader.exec_module(obj)
    return obj


def rejected(fn):
    try: fn()
    except (ValueError,TypeError): return True
    return False


def main():
    old,new,freeze=read(OLD/'PLAN.json'),read(NEW/'PLAN.json'),read(NEW/'AMENDMENT_FREEZE.json')
    initial={str(p.relative_to(ROOT)):sha(p) for p in [OLD/'PLAN.json',OLD/'HEADER_RESULTS.json',NEW/'PLAN.json',NEW/'AMENDMENT_FREEZE.json']+[d/f for d in [OLD,NEW] for f in FILES]}
    record('frozen_plan_and_ancestor_hashes',freeze['plan_sha256']==sha(NEW/'PLAN.json') and freeze['original_plan_sha256']==sha(OLD/'PLAN.json'))
    record('old_and_new_code_hashes',all(sha(OLD/f)==freeze['old_code_hashes'][f]==old['code_hashes'][f]
        and sha(NEW/f)==freeze['new_code_hashes'][f]==new['code_hashes'][f] for f in FILES))
    record('scientific_parser_and_selector_byte_identical',all((OLD/f).read_bytes()==(NEW/f).read_bytes() for f in ['header_tools.py','select_extremes.py']))
    replacements={
        'make_plan.py':('"https://archive.eso.org/hdr?" + urlencode({"DpId": row["dp_id"]})','"https://archive.eso.org/hdr?DpId=" + row["dp_id"]'),
        'fetch_headers.py':('"https://archive.eso.org/hdr?" + urllib.parse.urlencode({"DpId": job["dp_id"]})','"https://archive.eso.org/hdr?DpId=" + job["dp_id"]'),
    }
    for name,(a,b) in replacements.items():
        before=(OLD/name).read_text(); after=(NEW/name).read_text()
        record(name+'_only_authorized_url_expression_changed',before.count(a)==1 and before.replace(a,b)==after)
    changed={k for k in set(old)|set(new) if old.get(k)!=new.get(k)}
    record('plan_changes_only_expected_fields',changed=={'created_utc','inputs','code_hashes','technical_amendment','jobs'},sorted(changed))
    record('original_metadata_inputs_preserved',new['inputs'][:len(old['inputs'])]==old['inputs'])
    record('every_bound_input_exists_matches_and_is_repo_relative',all(not Path(i['path']).is_absolute()
        and (ROOT/i['path']).resolve().is_relative_to(ROOT) and sha(ROOT/i['path'])==i['sha256'] for i in new['inputs']))
    without_url=lambda rows:[{k:v for k,v in row.items() if k!='url'} for row in rows]
    record('exact_two_jobs_all_metadata_unchanged',len(new['jobs'])==2 and without_url(new['jobs'])==without_url(old['jobs']))
    record('exact_id_order_target_and_month_preserved',[(j['dp_id'],j['target'],j['month_number']) for j in new['jobs']]==[
        ('ADP.2018-01-21T01:01:37.761','HD122640',1),('ADP.2017-05-23T01:01:52.459','HD122640',5)])
    record('limits_benchmarks_and_readiness_gate_unchanged',all(new[k]==old[k] for k in ['limits','existing_berv_benchmark','payload_readiness_gate','extreme_selection_rule','identity_tolerances','mode_eligibility']))
    tools=load('header_tools'); planner=load('make_plan')
    candidate_file=ROOT/new['inputs'][0]['path']; candidates=read(candidate_file)
    record('new_selection_reproduces_fixed_jobs',planner.select(candidates)==new['jobs'])
    docbody=(NEW/'docs/URL_BUILDER_RESPONSE.txt').read_bytes(); receipt=read(NEW/'docs/URL_BUILDER_RECEIPT.json')
    record('saved_official_debug_response_integrity',len(docbody)==receipt['bytes'] and hashlib.sha256(docbody).hexdigest()==receipt['sha256'])
    demo='https://archive.eso.org/hdr?DpId=ADP.2014-10-01T10:19:21.580'
    record('official_debug_literal_url_contract',docbody.decode().strip()==demo and receipt['http_status']==200
        and 'archive.eso.org/cgi-bin/tap_proxy?' in receipt['url'] and 'debug=debug' in receipt['url'])
    record('debug_receipt_explicitly_not_actual_header',receipt['target_header_requests']==0 and receipt['retrieval_scope']=='Official demo URL-only documentation; no actual product header requested.')
    record('both_urls_keep_named_parameter_and_literal_colons',all(j['url']=='https://archive.eso.org/hdr?DpId='+j['dp_id']
        and '%3A' not in j['url'] and urlsplit(j['url']).query=='DpId='+j['dp_id']
        and tools.ADP_RE.fullmatch(j['dp_id']) and j['dp_id'].isascii() for j in new['jobs']))

    tree=ast.parse((NEW/'fetch_headers.py').read_text())
    main_fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    loops=[n for n in main_fn.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='job'
        and isinstance(n.iter,ast.Name) and n.iter.id=='jobs'
        and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and c.func.attr=='fullmatch' for c in ast.walk(n))]
    record('one_pre_request_url_guard_loop',len(loops)==1)
    guard=compile(ast.fix_missing_locations(ast.Module(body=[loops[0]],type_ignores=[])),'isolated_frozen_url_guard','exec')
    calls=[n for n in ast.walk(loops[0]) if isinstance(n,ast.Call)]
    record('isolated_guard_has_no_network_calls',all(isinstance(n.func,ast.Name) and n.func.id=='ValueError'
        or isinstance(n.func,ast.Attribute) and n.func.attr=='fullmatch' for n in calls))
    def guard_job(dp,url):
        exec(guard,{'jobs':[dict(dp_id=dp,url=url)],'ADP_RE':tools.ADP_RE})
    for j in new['jobs']:
        record('fetch_guard_accepts_exact_'+str(j['job_index']),not rejected(lambda j=j:guard_job(j['dp_id'],j['url'])))
    valid=new['jobs'][0]['dp_id']
    invalid=[valid+'&x=1',valid+'#fragment',valid+'?other=1',valid+'%26x=1',valid.replace(':','%3A'),
        valid+'\r\nInjected: yes',valid+'\n',valid+'\t',valid+' ',valid+'/',valid+'\\',valid+"'",valid+'"',
        valid+';x=1','../'+valid,'https://example.invalid/?'+valid,valid+'.fits',valid.lower(),valid.replace('ADP.','HARPS.'),
        valid[:-1],valid+'0',None]
    for index,dp in enumerate(invalid):
        url='https://archive.eso.org/hdr?DpId='+str(dp)
        record('fetch_guard_rejects_invalid_or_injected_id_'+str(index),rejected(lambda dp=dp,url=url:guard_job(dp,url)))
        r=copy.deepcopy(candidates[0]);r['dp_id']=dp
        record('planner_rejects_invalid_or_injected_id_'+str(index),rejected(lambda r=r:planner.select([r])))
    wrongurls=['http://archive.eso.org/hdr?DpId='+valid,'https://evil.invalid/hdr?DpId='+valid,
        'https://archive.eso.org/hdr?'+valid,'https://archive.eso.org/hdr?DpId='+valid+'&extra=1',
        'https://archive.eso.org/hdr?DpId='+valid+'#x','https://archive.eso.org/hdr?DpId='+valid.replace(':','%3A'),
        'https://archive.eso.org/hdr?DpId='+valid+'&DpId='+valid]
    for index,url in enumerate(wrongurls):
        record('fetch_guard_rejects_nonexact_url_'+str(index),rejected(lambda url=url:guard_job(valid,url)))
    prior=read(OLD/'HEADER_RESULTS.json');amendment=new['technical_amendment']
    record('failed_original_canary_remains_stopped',prior['status']=='COMPLETE_WITH_STOP' and prior['requests_attempted']==1
        and prior['results'][0]['status']=='UNRECOGNIZED_HEADER_RESPONSE' and prior['results'][1]['status']=='NOT_REQUESTED_BATCH_STOPPED')
    failed_body=OLD/prior['results'][0]['body_path']
    record('failed_response_is_encoded_id_error_not_header',b'Invalid format for dp_id' in failed_body.read_bytes()
        and b'%3A' in failed_body.read_bytes() and sha(failed_body)==amendment['original_failure_body_sha256'])
    record('cumulative_request_and_byte_accounting',amendment['prior_target_header_requests']==prior['requests_attempted']==1
        and amendment['new_max_target_header_requests']==len(new['jobs'])==2 and amendment['cumulative_max_target_header_requests']==3
        and amendment['prior_response_bytes']==prior['response_bytes']==2639
        and amendment['new_effective_response_byte_ceiling']==2*524288
        and amendment['cumulative_response_byte_ceiling']==2639+2*524288)
    record('all_reviewed_files_unchanged_during_audit',all(sha(ROOT/p)==digest for p,digest in initial.items()))
    failed=[c['check'] for c in checks if not c['passed']]
    report={'schema':'INDEPENDENT_HARPS_HEADER_URL_AMENDMENT_REVIEW_V1','status':'PASS' if not failed else 'FAIL',
        'created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(Path(__file__)),
        'checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'failed_checks':failed,'checks':checks,
        'scope':dict(network_requests=0,target_header_requests=0,science_arrays_read=0,owner_files_mutated=0),
        'frozen_plan_sha256':sha(NEW/'PLAN.json'),'amendment_freeze_sha256':sha(NEW/'AMENDMENT_FREEZE.json'),
        'source_hashes':initial,
        'conclusions':[
            'Only URL construction/validation changes: keep the named DpId parameter and preserve literal colons after full ADP identifier matching. Exact frozen URLs admit no extra parameter, fragment, alternate host or encoded-identifier fallback.',
            'An intermediate draft missing DpId= was observed and reported before publication; the final reviewed plan and both code expressions retain the exact documented prefix.',
            'The official debug response is a URL-only contract example. Its HTTP200 response does not establish that either target header can be fetched, parsed or scientifically admitted.',
            'The previous encoded-colon response was an error document, not an astronomical header or BERV measurement. The second old job was never requested.',
            'Both selected HD122640 IDs, parser, selection, scientific criteria, bounds and planning gate are unchanged. No HD135204 job or spectral payload is added.',
            'The complete date syntax is checked by the inherited ADP regex, not by an astronomical identifier service. Only the two unchanged ASCII IDs from the hash-bound metadata plan are authorized.',
            'This offline amendment review does not execute or release the new plan. Exact root release/publication verification and a successful canary remain separate requirements.'
        ]}
    (HERE/'HEADER_URL_AMENDMENT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','checks_passed','checks_total','failed_checks','frozen_plan_sha256']}))
    return bool(failed)


if __name__=='__main__': raise SystemExit(main())
