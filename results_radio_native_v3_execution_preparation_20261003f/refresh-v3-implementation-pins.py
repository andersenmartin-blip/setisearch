#!/usr/bin/env python3
"""Explicitly refresh the complete acyclic F graph after all source edits freeze.

Default mode prints an in-memory proposal. --refresh writes only the five
implementation-pin owners; it must be requested before any F protected state.
The caller independently pins this helper and its fixed sibling reviewer.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import types

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = Path(__file__).resolve().with_name('review-v3-implementation-pins.py')


def replace_assignment(raw,name,value):
    source = raw.decode('utf-8'); lines = source.splitlines(keepends=True)
    nodes = [n for n in ast.parse(source).body if isinstance(n,ast.Assign)
        and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name]
    if len(nodes)!=1: raise ValueError('Unique reviewed pin assignment required: '+name)
    node=nodes[0]; lines[node.lineno-1:node.end_lineno]=[name+' = '+repr(value)+'\n']
    result=''.join(lines).encode();ast.parse(result);return result


def proposal(graph,raws):
    staged=dict(raws)
    def assign(owner,name,targets):
        value=graph.pin_bytes(staged[targets]) if isinstance(targets,str) else {
            path:graph.pin_bytes(staged[path]) for path in targets}
        staged[owner]=replace_assignment(staged[owner],name,value)
    assign(graph.WORKER,'PUBLIC_CLAIM_IMPLEMENTATION_PIN',graph.CLAIMS)
    assign(graph.WORKER,'SPENDING_IMPLEMENTATION_PIN',graph.SPENDING)
    for name,target in (
        ('WORKER_ADMISSION_IMPLEMENTATION_PIN',graph.WORKER),
        ('CONTROL_ACTIVATION_IMPLEMENTATION_PIN',graph.ACTIVATION),
        ('INVOCATION_SPENDING_IMPLEMENTATION_PIN',graph.SPENDING),
        ('HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN',graph.CUSTODY),
        ('ACTIVATION_ENVIRONMENT_IMPLEMENTATION_PIN',graph.ENVIRONMENT),
        ('PUBLIC_CLAIM_IMPLEMENTATION_PIN',graph.CLAIMS)):
        assign(graph.FIXTURE,name,target)
    assign(graph.SUPERVISOR,'BOOTSTRAP_SOURCE_PINS',(graph.WORKER,graph.FIXTURE))
    assign(graph.FINALIZER,'BOOTSTRAP_SOURCE_PINS',(graph.FIXTURE,graph.WORKER,graph.SUPERVISOR))
    assign(graph.LAUNCHER,'BOOTSTRAP_SOURCE_PINS',graph.LAUNCH_TARGETS)
    result=graph.review(ROOT,raws=staged,verify_readback=False)
    if not result['all_literal_pins_match']: raise ValueError('Proposed complete graph does not match')
    owners=(graph.WORKER,graph.FIXTURE,graph.SUPERVISOR,graph.FINALIZER,graph.LAUNCHER)
    return staged,owners,result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewer-sha256',required=True)
    parser.add_argument('--refresh',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{64}',args.reviewer_sha256):raise ValueError('Independent raw reviewer SHA256 required')
    reviewer_raw=REVIEWER.read_bytes()
    if hashlib.sha256(reviewer_raw).hexdigest()!=args.reviewer_sha256:raise ValueError('Fixed reviewer source pin differs')
    graph=types.ModuleType('held_F_graph_reviewer');graph.__file__=str(REVIEWER)
    exec(compile(reviewer_raw,str(REVIEWER),'exec'),graph.__dict__)
    if graph.read_regular(REVIEWER)!=reviewer_raw:raise ValueError('Reviewer changed during held load')
    if any(os.path.lexists(ROOT/path) for path in graph.F_PROTECTED):
        raise ValueError('F protected state must remain absent before pin proposal/refresh')
    original=graph.snapshot(ROOT);graph.review(ROOT,raws=original)
    staged,owners,modeled=proposal(graph,original)
    changed=[path for path in owners if staged[path]!=original[path]]
    for path,raw in original.items():
        if graph.read_regular(graph.source_path(ROOT,path),runtime=path==graph.GIT)!=raw:
            raise ValueError('Source changed before explicit pin refresh')
    if args.refresh:
        for path in changed:
            if graph.read_regular(ROOT/path)!=original[path]:raise ValueError('Pin owner changed before write')
            with (ROOT/path).open('wb') as destination:
                destination.write(staged[path]);destination.flush();os.fsync(destination.fileno())
        terminal=graph.review(ROOT)
        if not terminal['all_literal_pins_match']:raise ValueError('Actual terminal graph does not match')
    if graph.read_regular(REVIEWER)!=reviewer_raw:raise ValueError('Held reviewer changed through operation')
    output={'schema':'radio-native-v3-implementation-pin-refresh-v1',
        'status':'PASS_REFRESHED_EXACT_27_EDGE_GRAPH' if args.refresh else 'IN_MEMORY_27_EDGE_PROPOSAL_ONLY',
        'relationship_count':27,'source_write_operations':len(changed) if args.refresh else 0,
        'proposed_source_pins':{path:graph.pin_bytes(staged[path]) for path in owners},
        'before_source_pins':{path:graph.pin_bytes(original[path]) for path in owners},
        'execution_authorized':False,'scientific_execution_authorized':False,
        'private_journal_content_reads':0,'network_operations':0,'automatic_retry':False}
    print(json.dumps(output,sort_keys=True,separators=(',',':')))


if __name__=='__main__':main()
