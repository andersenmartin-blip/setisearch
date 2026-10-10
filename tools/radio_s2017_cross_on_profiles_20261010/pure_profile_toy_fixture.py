#!/usr/bin/env python3
"""Prospective, root-run toy tests. Never imports the profile module or source data.

Only a SHA-pinned Python source file is read. Three geometry assignments, its
full-window bounds assertion, its cache-key expression, and its pure ndarray
kernel are AST-extracted. Everything else is unexecuted source text. NumPy is
used only for small fabricated 16 x 129 arrays. No HDF5, original NPZ, scope,
normalization JSON, detector, profile files, process locks or markers are read.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import time


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_fragments(path, expected_sha):
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_sha, 'Source SHA differs')
    tree = ast.parse(raw, filename=str(path))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    kernel = functions['profile_kernel']
    derive = functions['derive_geometry']
    require(not kernel.decorator_list and not kernel.args.defaults
            and [arg.arg for arg in kernel.args.args] == ['np', 'raw', 'row_medians', 'width'],
            'Kernel extraction interface changed')
    forbidden = {'open', 'exec', 'eval', 'compile', '__import__', 'os', 'Path', 'h5py',
                 'hdf5plugin', 'load_contract', 'compute', 'main', 'read_json', 'digest'}
    require(not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal))
                    or isinstance(node, ast.Name) and node.id in forbidden
                    or isinstance(node, ast.Attribute) and node.attr.startswith('__')
                    for node in ast.walk(kernel)), 'Kernel is not isolated pure ndarray math')
    assignments = {}
    for node in ast.walk(derive):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {'dt', 'base', 'centers', 'key'}:
                require(name not in assignments, 'Repeated geometry assignment')
                assignments[name] = node
    require(set(assignments) == {'dt', 'base', 'centers', 'key'}, 'Geometry expressions changed')
    bounds = [node for node in ast.walk(derive) if isinstance(node, ast.Expr)
              and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
              and node.value.func.id == 'require' and len(node.value.args) == 2
              and isinstance(node.value.args[1], ast.Constant)
              and node.value.args[1].value == 'Frozen profile exceeds retained chunk']
    require(len(bounds) == 1, 'Full-window source bound not found')
    # These statements cannot execute the fixed-count derive function or module.
    geometry_nodes = [assignments[name] for name in ('dt', 'base', 'centers')] + bounds
    allowed_names = {'np', 'headers', 's', 'anchor', 'TSAMP', 'k', 'SCANS', 'm',
                     'FCH1', 'DF', 'dt', 'base', 'centers', 'C0', 'COUNT', 'require'}
    require(all(not isinstance(node, ast.Name) or node.id in allowed_names
                for item in geometry_nodes for node in ast.walk(item)), 'Geometry extraction gained other names')
    key_names = {'key', 'scan', 'k', 'tuple', 'int', 'c', 'centers', 'i'}
    require(all(not isinstance(node, ast.Name) or node.id in key_names
                for node in ast.walk(assignments['key'])), 'Cache-key expression gained other names')
    require(any(isinstance(node, ast.Assign)
                and ast.dump(node.targets[0], include_attributes=False) ==
                ast.dump(ast.parse('times[j] = dt').body[0].targets[0], include_attributes=False)
                and isinstance(node.value, ast.Name) and node.value.id == 'dt'
                for node in ast.walk(derive)), 'Independent logical dt storage absent')
    fragments = {'kernel': ast.Module(body=[kernel], type_ignores=[]),
                 'geometry': ast.Module(body=geometry_nodes, type_ignores=[]),
                 'key': ast.Module(body=[assignments['key']], type_ignores=[])}
    codes = {name: compile(ast.fix_missing_locations(value), '<toy-extracted-' + name + '>', 'exec')
             for name, value in fragments.items()}
    ast_pins = {name: hashlib.sha256(ast.dump(value, include_attributes=False).encode()).hexdigest()
                for name, value in fragments.items()}
    return raw, codes, ast_pins


def run_toys(np, codes):
    completed = []
    ns = {'__builtins__': {}}
    exec(codes['kernel'], ns)
    kernel = ns['profile_kernel']

    def geometry(*, frequency=798.0, drift=1.0, reference=0.0, target_start=0.0,
                 fch1=1000.0, df=-2.0, tsamp=2.0, c0=0, count=100000):
        space = {'__builtins__': {}, 'np': np, 'require': require,
                 'm': {'original_reference_frequency_hz': frequency},
                 'k': {'reference_seconds_from_anchor': reference, 'drift_hz_s': drift},
                 'headers': {'toy_off': {'tstart': target_start}}, 'anchor': 0.0,
                 'SCANS': ('toy_off',), 'TSAMP': tsamp, 'FCH1': fch1, 'DF': df,
                 'C0': c0, 'COUNT': count}
        exec(codes['geometry'], space)
        return space['dt'], space['centers']

    def key(scan, width, centers):
        space = {'__builtins__': {'tuple': tuple, 'int': int}, 'scan': scan,
                 'k': {'width_channels': width}, 'centers': np.asarray([centers]), 'i': 0}
        exec(codes['key'], space)
        return space['key']

    def measured(raw, denominators, width=1):
        require(raw.dtype == np.dtype('<f4') and raw.shape == (16,129), 'Toy raw shape')
        result = kernel(np, raw, np.asarray(denominators, dtype='<f8'), width)
        require(all(np.isfinite(value).all() for value in result.values()), 'Toy nonfinite result')
        require(result['raw_width_mean'].dtype == result['mean_raw'].dtype == np.dtype('<f4'), 'Raw means dtype changed')
        require(all(result[name].dtype == np.dtype('<f8') for name in
                    ('center', 'flank', 'residual', 'mean_normalized', 'mean_residual')), 'Normalized dtype changed')
        return result

    # 1. Absolute ties-even differs from rounding the displacement then adding
    # an odd integer. Both drift polarities and negative reference dt matter.
    dt, plus = geometry(drift=1.0)
    _, minus = geometry(drift=-1.0)
    expected_plus = [100,100,98,98,96,96,94,94,92,92,90,90,88,88,86,86]
    expected_minus = [102,102,104,104,106,106,108,108,110,110,112,112,114,114,116,116]
    require(plus[0].tolist() == expected_plus and minus[0].tolist() == expected_minus, 'Absolute odd half ties')
    _, even = geometry(frequency=800.0)
    require(even[0].tolist() == [100,98,98,96,96,94,94,92,92,90,90,88,88,86,86,84], 'Absolute even half ties')
    _, negative_dt = geometry(reference=32.0)
    require(negative_dt[0].tolist() == list(reversed(expected_minus)), 'Negative reference dt')
    _, fractional_base = geometry(frequency=797.5)
    require(fractional_base[0].tolist() == list(range(101,85,-1)), 'Frequency-derived base was rounded early')
    require(int(plus[0,0]) != 101 + int(np.rint(-.5)), 'Fixture must distinguish wrong relative rounding')
    completed.append('absolute_frequency_base_ties_even_both_slopes_and_negative_dt')

    # 2. A target OFF integration midpoint is transported from each original
    # ON reference; a target self-reference or association midpoint is wrong.
    for reference, expected_first_dt, expected_first_center, expected_last_center in (
            (1.0,10800.0,27301,27294), (10801.0,0.0,30001,29994),
            (21601.0,-10800.0,32701,32694)):
        dt, centers = geometry(frequency=1000.0-2.0*30001, drift=.5,
                               reference=reference, target_start=.125)
        require(float(dt[0,0]) == expected_first_dt and float(dt[0,-1]) == expected_first_dt+30,
                'Original ON reference or integration midpoint differs')
        require(np.array_equal(np.diff(dt[0]), np.full(15,2.0))
                and int(centers[0,0]) == expected_first_center and int(centers[0,-1]) == expected_last_center,
                'OFF time transport differs')
    completed.append('target_OFF_times_keep_each_original_ON_reference')

    # 3. The entire 129-channel window is admitted inclusively, never trimmed.
    for base in (1064.0,1063.5,1064.5):
        _, centers = geometry(frequency=1000.0-2.0*base, drift=0.0, c0=1000, count=129)
        require(np.array_equal(centers, np.full((1,16),1064)), 'Full-window boundary/even tie')
    for base in (1063.0,1065.0):
        try:
            geometry(frequency=1000.0-2.0*base, drift=0.0, c0=1000, count=129)
        except AssertionError as error:
            require(str(error) == 'Frozen profile exceeds retained chunk', 'Unexpected bounds failure')
        else:
            raise AssertionError('Out-of-frame 129-channel window admitted')
    completed.append('full_129_channel_bounds_inclusive_and_fail_without_trimming')

    # 4. Zero and negative fixed-path residuals remain scientific outputs.
    result = measured(np.full((16,129),4.0,dtype='<f4'), np.full(16,2.0))
    require(np.array_equal(result['flank'],np.full(16,2.0)) and np.array_equal(result['residual'],np.zeros(16)), 'Constant baseline')
    require(np.count_nonzero(result['residual']>0) == 0, 'Strict positive rows')
    raw = np.full((16,129),6.0,dtype='<f4'); raw[:,64] = 2.0
    result = measured(raw,np.full(16,2.0))
    require(np.array_equal(result['residual'],np.full(16,-2.0)), 'Negative rows filtered or sign changed')
    completed.append('constant_background_zero_and_negative_residuals')

    # 5. Use all supplied row denominators before reduction; never replace
    # them with a synthetic aggregate denominator or remeasure a raw median.
    raw = np.full((16,129),8.0,dtype='<f4'); raw[:,64] = 12.0
    result = measured(raw,[2.0]*8+[4.0]*8)
    require(np.array_equal(result['residual'],np.asarray([2.0]*8+[1.0]*8))
            and float(result['mean_residual'][64]) == 1.5, 'Normalize-first varying row denominators')
    completed.append('provided_varying_denominators_normalize_each_row_first')

    # 6. Exactly 122 flanks exclude all seven offsets -3..3. Context at the
    # excluded positions is still retained, and the even flank median is taken
    # AFTER float64 normalization (the two orders differ by one last bit).
    offsets = np.arange(-64,65); flank = np.abs(offsets)>3
    require(int(np.count_nonzero(flank)) == 122, 'Hand fixture flank count')
    raw = np.full((16,129),6.0,dtype='<f4')
    raw[:,63:66] = [10.0,12.0,8.0]; raw[:,[61,62,66,67]] = 998.0
    one = measured(raw,np.full(16,2.0),1); three = measured(raw,np.full(16,2.0),3)
    require(np.array_equal(one['residual'],np.full(16,3.0))
            and np.array_equal(three['residual'],np.full(16,2.0)), 'Width1/3 center or flank changed')
    require(float(three['mean_residual'][61]) == 496.0 and float(three['mean_raw'][61]) == 998.0,
            'Excluded flank neighborhood was masked from saved context')
    raw = np.full((16,129),2.0,dtype='<f4'); raw[:,0] = 1000.0
    result = measured(raw,np.full(16,2.0))
    require(np.array_equal(result['flank'],np.full(16,1.0)), 'Flank mean substituted for median')
    raw = np.zeros((16,129),dtype='<f4'); raw[:,np.flatnonzero(flank)[:61]]=1.0; raw[:,np.flatnonzero(flank)[61:]]=4.0
    result = measured(raw,np.full(16,3.0))
    require(float(result['flank'][0]) == 0.8333333333333333
            and float(result['flank'][0]) != 2.5/3.0, 'Raw median divided after reduction')
    completed.append('fixed_122_flank_median_width1_width3_and_unmasked_context')

    # 7. Raw float32 means are descriptive raw outputs; they do not replace
    # normalized-first float64 center arithmetic.
    raw = np.zeros((16,129),dtype='<f4'); raw[:,63:66] = [2**24,2**24,2**24+2]
    result = measured(raw,np.ones(16),3)
    require(float(result['raw_width_mean'][0]) == float(2**24)
            and float(result['center'][0]) == float(2**24)+2.0/3.0,
            'Float32 raw mean and float64 normalized center conflated')
    completed.append('raw_float32_means_distinct_from_normalized_float64_center')

    # 8. Preserve mean(normalized - per-row baseline), including operation
    # order. Subtracting two huge aggregate means would lose small residuals.
    raw = np.ones((16,129),dtype='<f4'); raw[:8,:] = float(2**53)
    raw[:8,64] = float(2**53+2**30); raw[8:,64] = 3.0
    result = measured(raw,np.ones(16))
    require(float(result['mean_residual'][64]) == 536870913.0, 'Residual mean expression reassociated')
    completed.append('mean_of_rowwise_subtraction_preserves_small_residual_terms')

    # 9. Two logical members may share geometry but keep distinct dt. The
    # actual extracted key must distinguish scan, width and ordered centers.
    dt_a, centers_a = geometry(drift=0.0,reference=0.0)
    dt_b, centers_b = geometry(drift=0.0,reference=2.0)
    require(np.array_equal(centers_a,centers_b) and not np.array_equal(dt_a,dt_b), 'Alias time fixture not distinct')
    common = key('toy_off',1,centers_a[0])
    require(common == key('toy_off',1,centers_b[0]) and common != key('other_scan',1,centers_a[0])
            and common != key('toy_off',3,centers_a[0]), 'Scan/width alias identity')
    ordered = np.arange(100,116,dtype='<i8')
    require(key('toy_off',1,ordered) != key('toy_off',1,ordered[::-1]), 'Ordered centers became a set')
    completed.append('geometry_aliases_preserve_logical_dt_scan_width_and_center_order')
    require(len(completed) == 9, 'Fixture case inventory')
    return completed


def main():
    start_wall = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile-source',required=True)
    parser.add_argument('--expected-profile-source-sha256',required=True)
    parser.add_argument('--receipt',required=True)
    args = parser.parse_args()
    require(re.fullmatch(r'[0-9a-f]{64}',args.expected_profile_source_sha256) is not None, 'Expected source SHA required')
    source = Path(args.profile_source); receipt = Path(args.receipt)
    require(source.is_absolute() and source.resolve() == source and not source.is_symlink()
            and source.name == 'profile_saved.py', 'Only canonical profile Python source admitted')
    require(receipt.is_absolute() and receipt.parent.is_dir() and not receipt.exists(), 'New private toy receipt only')
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    resource.setrlimit(resource.RLIMIT_CPU,(10,12))
    resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824))
    signal.signal(signal.SIGALRM,lambda signum,frame: (_ for _ in ()).throw(TimeoutError('Toy wall cap')))
    signal.alarm(30)
    raw,codes,ast_pins = source_fragments(source,args.expected_profile_source_sha256)
    import numpy as np
    cases = run_toys(np,codes)
    require(source.read_bytes() == raw, 'Pinned source changed during toy fixture')
    use = {'process_CPU_seconds':time.process_time(),'wall_seconds':time.monotonic()-start_wall,
           'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    require(use['process_CPU_seconds'] <= 10 and use['wall_seconds'] <= 30 and use['peak_RSS_bytes'] <= 1073741824,
            'Toy fixture resource cap exceeded')
    value = {'status':'PASS_NINE_SOURCE_EXTRACTED_PURE_PROFILE_TOY_FIXTURES',
             'profile_source_sha256':args.expected_profile_source_sha256,'profile_source_bytes':len(raw),
             'fixture_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'extracted_AST_sha256':ast_pins,'passed_cases':cases,'case_count':9,
             'target_module_imported':False,'target_main_or_generator_called':False,
             'original_NPZ_H5_source_or_normalization_JSON_read':False,
             'real_profiles_or_medians_measured':False,'network_calls':0,
             'only_source_text_and_small_fabricated_16x129_arrays':True,
             'CPU_cap_s':10,'wall_cap_s':30,'memory_cap_bytes':1073741824,**use}
    with receipt.open('x',encoding='utf-8') as handle:
        json.dump(value,handle,indent=2,allow_nan=False);handle.write('\n')
    signal.alarm(0)
    print(json.dumps({'status':value['status'],'case_count':9,**use}))


if __name__ == '__main__':
    main()
