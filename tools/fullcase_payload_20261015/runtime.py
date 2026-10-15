"""Pin and import only the already tested transport and process guard."""
import hashlib
import importlib.util
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent.parent
GUARD_SHA = 'd02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492'


def load(name, path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Pinned engineering dependency differs: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = load('fullcase_pinned_guard', BASE / 'whole_child_guard_20261015/guard.py', GUARD_SHA)
# The hash is supplied from this checkout's immutable public base, not inferred
# from untrusted payload bytes. It is frozen in SOURCE_PINS.json before launch.
import json
pins = json.loads((Path(__file__).parent / 'SOURCE_PINS.json').read_text())
store = load('fullcase_pinned_transport', BASE / 'bounded_payload_20261015/payload_store.py',
             pins['prior_transport_sha256'])
