#!/usr/bin/env python3
"""Refresh the acyclic reviewed v3 bootstrap graph; no controls or data reads."""
import ast
import hashlib
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def pin(relative):
    raw=(ROOT/relative).read_bytes()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def assignment(relative,name,value):
    path=ROOT/relative;source=path.read_text();lines=source.splitlines(keepends=True)
    nodes=[node for node in ast.parse(source).body if isinstance(node,ast.Assign)
        and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
        and node.targets[0].id==name]
    if len(nodes)!=1:raise ValueError('Unique reviewed pin assignment required: '+relative+':'+name)
    node=nodes[0]
    lines[node.lineno-1:node.end_lineno]=[name+' = '+repr(value)+'\n']
    path.write_text(''.join(lines))


def main():
    fixture='scripts/radio_native_v3_compact_eight_case_resource_fixture.py'
    worker='scripts/radio_native_v3_worker_admission.py'
    supervisor='scripts/radio_native_v3_process_tree_supervisor.py'
    finalizer='scripts/radio_native_v3_resource_finalization.py'
    launcher='scripts/radio_native_v3_compact_control_launch.py'
    assignment(fixture,'WORKER_ADMISSION_IMPLEMENTATION_PIN',pin(worker))
    assignment(fixture,'HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN',
        pin('scripts/radio_native_v3_custody_observation.py'))
    assignment(supervisor,'BOOTSTRAP_SOURCE_PINS',{path:pin(path) for path in (worker,fixture)})
    assignment(finalizer,'BOOTSTRAP_SOURCE_PINS',{path:pin(path) for path in (fixture,worker,supervisor)})
    source=(ROOT/launcher).read_text()
    node=next(node for node in ast.parse(source).body if isinstance(node,ast.Assign)
        and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='BOOTSTRAP_SOURCE_PINS')
    selected=ast.literal_eval(node.value)
    assignment(launcher,'BOOTSTRAP_SOURCE_PINS',{path:pin(path) for path in selected})
    print({path:pin(path) for path in (worker,fixture,supervisor,finalizer,launcher)})


if __name__=='__main__':main()
