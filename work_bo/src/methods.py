"""Main-safe pinned method references for deterministic BO engineering only.

Imports do not create fixtures, draw random values, decode telescope arrays,
execute gates or load historical modules. Current vendor loading is explicit.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import math
import platform
import re
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VENDOR_PINS = {
    'vendor/current/kernel_v.py': '3367c20c93e4ba564b5abceb19e0939fb82fd364fbb400fe85e07f93f15b8999',
    'vendor/current/continuous_normalization_ac.py': '8953f595f1fa9e192c98fbb185b69800d046275552a9bcff6c41df40d558bf52',
    'vendor/legacy/search_pilot.py': '56b0800b972f02cc3d2e3f5795571b1ce95684bf37803ec5d007ed3dccbdb101',
    'vendor/legacy/run_pilot.py': '4c7e2f4a973b92b518f1134cba3d0529a313d0092bf67460d00ac6b119fb2c23',
}
LEGACY_FUNCTIONS = ('normalize', 'centered_boxcar', 'drift_grid', 'track_sum', 'ess_calibration')
WIDTHS = (1,3,9,33)
STRIDES = (1,1,2,8)
DT = 18.253611008
DF = -2.7939677238464355
RATE_INDICES = (0,209,419,629,838)
CONTROL_Q = (63,64,65,127,129)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json_exclusive(path, value):
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def verify_config(path):
    path = Path(path).resolve()
    config = read_json(path)
    require(config['schema'] == 'SETI_BO_ENGINEERING_PLAN_V1', 'Wrong BO plan schema')
    require(config['engineering_only'] is True
            and config['real_telescope_powers_authorized'] is False
            and config['rng_authorized'] is False
            and config['scientific_scores_authorized'] is False,
            'BO is deterministic software engineering only')
    runtime = config['runtime']
    require(platform.python_version() == runtime['python_version'] == '3.12.14', 'Python runtime differs')
    require(np.__version__ == runtime['numpy_version'] == '2.3.5', 'NumPy runtime differs')
    if 'python_executable_sha256' in runtime:
        require(file_sha(sys.executable) == runtime['python_executable_sha256'], 'Python executable bytes differ')
    pins = config['source_pins']
    require(isinstance(pins, list) and pins, 'Explicit source pin list required')
    seen = set()
    for pin in pins:
        relative = Path(pin['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Source pin must be BO-relative')
        candidate = (ROOT / relative).resolve()
        require(candidate.is_relative_to(ROOT) and candidate.is_file(), 'Source pin escapes BO or is missing')
        require(str(relative) not in seen, 'Duplicate source pin')
        seen.add(str(relative))
        require(re.fullmatch('[0-9a-f]{64}', pin['sha256']) is not None, 'Invalid source digest')
        require(candidate.stat().st_size == pin['bytes'] and file_sha(candidate) == pin['sha256'], 'Source bytes differ: '+str(relative))
    require('src/methods.py' in seen, 'Methods source must be pinned')
    return config


def verify_sources():
    for relative, digest in VENDOR_PINS.items():
        require(file_sha(ROOT / relative) == digest, 'Vendor source differs: '+relative)
    original = ast.parse((ROOT / 'vendor/legacy/search_pilot.py').read_text())
    adapted = ast.parse(Path(__file__).read_text())
    checks = []
    for name in LEGACY_FUNCTIONS:
        before = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == name)
        after = next(n for n in adapted.body if isinstance(n, ast.FunctionDef) and n.name == 'legacy_'+name)
        after.name = name
        require(ast.dump(before, include_attributes=False) == ast.dump(after, include_attributes=False), 'Legacy pure function differs: '+name)
        checks.append(name)
    return {'status':'PASS_EXACT_VENDOR_AND_LEGACY_FUNCTION_AST', 'vendor_sha256':dict(VENDOR_PINS), 'legacy_AST_equal_except_prefix':checks, 'historical_module_imported':False}


def load_current():
    verify_sources()
    modules = []
    for label, relative in [('kernel','vendor/current/kernel_v.py'), ('normalizer','vendor/current/continuous_normalization_ac.py')]:
        spec = importlib.util.spec_from_file_location('bo_exact_current_'+label, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return tuple(modules)


def current_calibration(sums):
    values = np.asarray(sums)
    median = float(np.median(values))
    scale = float(1.4826*np.median(np.abs(values-median)))
    require(math.isfinite(scale) and scale > 0, 'Nonpositive current calibration MAD')
    return median, scale


def resolve_e02(config):
    path = Path(config['gate_outputs']['E02']).resolve()
    require(path.is_relative_to(ROOT), 'E02 output escapes BO root')
    result = read_json(path / 'RESULT.json')
    require(result['gate'] == 'E02' and result['status'] == 'PASS', 'Closed E02 result required')
    manifest = read_json(path / 'FIXTURES.json')
    require(manifest['fixtures'] == result['fixtures'], 'E02 result/fixture binding differs')
    for fixture in result['fixtures']:
        for prefix in ['input','current_normalized','legacy_normalized']:
            array_path = Path(fixture[prefix+'_path']).resolve()
            require(array_path.is_relative_to(path) and file_sha(array_path) == fixture[prefix+'_sha256'], 'Changed E02 fixture')
    return path, result


def legacy_normalize(raw, block=4096):
    """Rowwise piecewise-constant spectral median/MAD; no time subtraction.

    Each row/block gets its own median and 1.4826 MAD. All stored columns,
    including halo, contribute to normalization; only the fixed core is searched.
    Invalid values/scales are fatal rather than silently losing trial coverage.
    """
    x=np.asarray(raw,dtype=np.float32)
    if x.ndim!=2 or x.shape[0]<2: raise ValueError('Require >=2 time rows and one frequency dimension')
    if not np.isfinite(x).all(): raise ValueError('Non-finite raw power')
    y=np.empty_like(x); rows=[]
    for lo in range(0,x.shape[1],block):
        hi=min(lo+block,x.shape[1]); a=x[:,lo:hi]
        med=np.median(a,axis=1)
        sig=np.median(np.abs(a-med[:,None]),axis=1)*np.float32(1.4826)
        if np.any(sig<=0) or not np.isfinite(sig).all(): raise ValueError('Non-positive spectral MAD scale')
        y[:,lo:hi]=(a-med[:,None])/sig[:,None]
        rows.append(dict(channel_lo=lo,channel_hi_exclusive=hi,median=med.tolist(),mad_scale=sig.tolist()))
    return y,rows

def legacy_centered_boxcar(y,width):
    if width==1: return y
    # Float64 cumulative sum avoids accumulating large float32 subtraction error.
    cs=np.cumsum(y,axis=1,dtype=np.float64)
    cs=np.concatenate((np.zeros((y.shape[0],1)),cs),axis=1)
    sums=cs[:,width:]-cs[:,:-width]
    out=np.zeros_like(y)
    h=width//2
    out[:,h:y.shape[1]-h]=sums.astype(np.float32)
    return out

def legacy_drift_grid(nrows,dt,df,maxdrift):
    exposure_span=nrows*dt
    nside=int(math.ceil(maxdrift*exposure_span/abs(df)))
    rates=np.linspace(-maxdrift,maxdrift,2*nside+1,dtype=np.float64)
    return rates

def legacy_track_sum(y,offsets,start,stop,stride):
    """Contiguous/strided slice accumulation; exact nearest-channel tracks."""
    n=(stop-start+stride-1)//stride
    out=np.zeros(n,dtype=np.float32)
    for row,off in zip(y,offsets):
        out += row[start+int(off):stop+int(off):stride]
    return out

def legacy_ess_calibration(sums):
    med=float(np.median(sums))
    scale=float(1.4826*np.median(np.abs(sums-med)))
    if not math.isfinite(scale) or scale<=0: raise ValueError('Non-positive track-sum MAD')
    return med,scale
