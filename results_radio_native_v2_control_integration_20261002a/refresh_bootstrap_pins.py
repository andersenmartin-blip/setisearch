import ast
import hashlib
import json
from pathlib import Path

repo=Path('/workspace/scratch/97e21f28a7b4/setisearch-repo-20261002')

def pin(relative):
    raw=(repo/relative).read_bytes()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def assignments(relative):
    source=(repo/relative).read_text()
    tree=ast.parse(source)
    return source,{node.targets[0].id:node for node in tree.body
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)}

def update(relative,values):
    source,nodes=assignments(relative); lines=source.splitlines(keepends=True)
    edits=[]
    for name,value in values.items():
        node=nodes[name]
        edits.append((node.lineno-1,node.end_lineno,name+' = '+repr(value)+'\n'))
    for start,end,text in sorted(edits,reverse=True): lines[start:end]=[text]
    (repo/relative).write_text(''.join(lines))

worker='scripts/radio_native_v2_worker_admission.py'
fixture='scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
supervisor='scripts/radio_native_v2_process_tree_supervisor.py'
finalizer='scripts/radio_native_v2_resource_finalization.py'
launcher='scripts/radio_native_v2_compact_control_launch.py'
activation='scripts/radio_native_v2_control_activation.py'
prospective='scripts/radio_native_v2_prospective_spending.py'
historical='scripts/radio_native_v2_historical_storage.py'
helper='scripts/radio_native_v2_historical_observation.py'
# Literal input pins in the historical helper remain independently fixed. This
# script changes only forward source edges after all source-owning edits cease.
update(worker,{'SPENDING_IMPLEMENTATION_PIN':pin(prospective)})
fixture_values={'WORKER_ADMISSION_IMPLEMENTATION_PIN':pin(worker),
    'CONTROL_ACTIVATION_IMPLEMENTATION_PIN':pin(activation),
    'INVOCATION_SPENDING_IMPLEMENTATION_PIN':pin(prospective)}
_,nodes=assignments(fixture)
for name in ('HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN',):
    if name in nodes: fixture_values[name]=pin(helper)
update(fixture,fixture_values)
update(supervisor,{'BOOTSTRAP_SOURCE_PINS':{r:pin(r) for r in (worker,fixture)}})
update(finalizer,{'BOOTSTRAP_SOURCE_PINS':{r:pin(r) for r in (fixture,worker,supervisor)}})
_,nodes=assignments(launcher)
old=ast.literal_eval(nodes['BOOTSTRAP_SOURCE_PINS'].value)
paths=set(old)-{'scripts/radio_native_v2_invocation_spending.py'}
paths.update((prospective,historical,helper))
update(launcher,{'BOOTSTRAP_SOURCE_PINS':{r:pin(r) for r in sorted(paths)}})
print(json.dumps({'status':'FORWARD_BOOTSTRAP_SOURCE_EDGES_REFRESHED',
    'paths':{r:pin(r) for r in (prospective,historical,helper,activation,worker,fixture,supervisor,finalizer,launcher)},
    'historical_input_literal_pins_refreshed':False,'execution_authorized':False},sort_keys=True,separators=(',',':')))
