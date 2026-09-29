#!/usr/bin/env python3
"""One fixed deterministic software comparison; never an experiment restart."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
import numpy as np
from seti_repeater import pipeline_radio as radio
from seti_repeater import transfer_m43g as native
from seti_repeater import search_v0p6 as core
from test_radio_receiver_batch import fixture

BASE='a5fcb1b36aa890916442a7c1b3a1dd7903358dca'
OUT=ROOT/'results_radio_receiver_batch_2026-09-29/profile01'


def main():
    started=time.monotonic(); OUT.mkdir(parents=True,exist_ok=False)
    source=subprocess.check_output(['git','show',BASE+':src/seti_repeater/pipeline_radio.py']).decode()
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='synthetic_signature')
    original=ast.get_source_segment(source,node)
    namespace=dict(radio.__dict__)
    exec(compile(original,'immutable-original-scalar-signature','exec'),namespace)
    scalar=namespace['synthetic_signature']
    paths=['scripts/radio_receiver_batch_profile.py','tests/test_radio_receiver_batch.py',
           'src/seti_repeater/pipeline_radio.py','src/seti_repeater/pipeline_receiver_radio.py',
           'src/seti_repeater/transfer_m43g.py','src/seti_repeater/receiver_v0p6.py',
           'src/seti_repeater/search_v0p6.py','src/seti_repeater/source_v0p6.py']
    scope={'namespace':'receiver-batch-software-profile-20260929f','mode':'deterministic-software-only',
           'baseline_commit':BASE,'original_scalar_sha256':hashlib.sha256(original.encode()).hexdigest(),
           'channels':65536,'rows':16,'templates':8,'widths':[1,129],
           'queries_per_width':1024,'unique_queries_per_width':256,
           'query_recipe':'tuple((t,q) for t in range(8) for q in range(0,64,2)) * 4',
           'source_recipe':'test_radio_receiver_batch.fixture(65536,8,40); no random generator',
           'limits':{'seconds':90,'rss_bytes':512*1024**2,'retained_output_bytes':8*1024**2},
           'code_sha256s':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
           'python':sys.version,'numpy':np.__version__,
           'scientific_qualification':False,'historical_values_used':False}
    (OUT/'fixed_before_measurement.json').write_bytes(core.canonical_json_bytes(scope))
    (OUT/'original_scalar.py.txt').write_text(original+'\n')
    def budget():
        if time.monotonic()-started>90:raise ValueError('Software-profile time cap exceeded')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>512*1024**2:raise ValueError('Software-profile RSS cap exceeded')
    try:
        src,grid,factors=fixture(65536,8,40)
        queries=tuple((t,q) for t in range(8) for q in range(0,64,2))*4
        rows=[]
        for width in scope['widths']:
            cache=native.build_synthetic_cache(src,factors,grid,width,bank_sha256='a'*64)
            budget();t=time.perf_counter();expected=[]
            for q in queries:expected.append(scalar(cache,*q));budget()
            scalar_seconds=time.perf_counter()-t
            t=time.perf_counter();actual=radio.synthetic_signatures_batch(cache,queries)
            batch_seconds=time.perf_counter()-t;budget()
            a=core.canonical_json_bytes(expected);b=core.canonical_json_bytes(actual)
            if a!=b:raise ValueError('Original scalar/batch output bytes differ')
            encoded=base64.b64encode(zlib.compress(a,9))
            (OUT/f'width{width}_identical_outputs.json.zlib.b64').write_bytes(encoded)
            row={'width':width,'queries':len(queries),'unique_queries':len(set(queries)),
                 'original_scalar_seconds':scalar_seconds,'batch_seconds':batch_seconds,
                 'observed_ratio':scalar_seconds/batch_seconds,'canonical_output_bytes':len(a),
                 'scalar_sha256':hashlib.sha256(a).hexdigest(),'batch_sha256':hashlib.sha256(b).hexdigest(),
                 'cache_identity':cache.identity,'payload_sha256':cache.payload_sha256,
                 'encoded_bytes':len(encoded),'encoded_sha256':hashlib.sha256(encoded).hexdigest()}
            rows.append(row);(OUT/'completed_widths.json').write_bytes(core.canonical_json_bytes(rows))
        budget()
        if sum(p.stat().st_size for p in OUT.iterdir())>8*1024**2:raise ValueError('Software-profile retained output cap exceeded')
        result={'status':'PASS_FIXED_SOFTWARE_EQUIVALENCE_PROFILE','measurements':rows,
                'whole_seconds':time.monotonic()-started,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                'new_random_values':0,'new_telescope_reads':0,'historical_experiments_reexecuted':False,
                'scientific_or_complete_native_chain_qualification':False,
                'limitation':'One scalar-first run per width; no confidence interval or whole-chain timing inference.'}
        (OUT/'result.json').write_bytes(core.canonical_json_bytes(result));print(json.dumps(result,indent=2))
    except BaseException as error:
        (OUT/'failure.json').write_bytes(core.canonical_json_bytes({'status':'FAILED_SOFTWARE_PROFILE',
            'error':repr(error),'elapsed_seconds':time.monotonic()-started}))
        raise


if __name__=='__main__':main()
